"""Fresh CPU replay from an integrity-checked official corpus bundle; no database writes."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import statistics
import sys
import time

from retrieval.adaptive import choose_budget, fit_policy, fingerprint, verify_group_holdout
from retrieval.chat import load_policy, rerank_candidates
from retrieval.cpu_backend import file_hash, torch_runtime, torch_threads


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def process_memory():
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "PeakWorkingSetSize",
                    "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage",
                    "PagefileUsage",
                    "PeakPagefileUsage",
                )
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        if not psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return {
            "working_set_bytes": counters.WorkingSetSize,
            "peak_working_set_bytes": counters.PeakWorkingSetSize,
        }
    return {
        "working_set_bytes": None,
        "peak_working_set_bytes": None,
        "reason": "Working-set sampler currently implemented for Windows",
    }


def corpus(bundle):
    manifest_path = bundle / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = bundle / manifest["data"]["path"]
    if file_hash(data) != manifest["data"]["sha256"]:
        raise ValueError("Official bundle data hash mismatch")
    books, chunks, vectors, release = {}, {}, {}, None
    with gzip.open(data, "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            table, row = item["table"], item["row"]
            if table == "documents":
                books[row["id"]] = row
            elif table == "chunks":
                chunks[row["id"]] = row
            elif table == "corpus_releases" and row["id"] == manifest["active_release_id"]:
                release = row
            elif table == "release_chunks" and row["release_id"] == manifest["active_release_id"]:
                vectors[row["chunk_id"]] = row["embedding"]
    if release is None or len(vectors) != manifest["active_vector_count"]:
        raise ValueError("Official bundle release membership mismatch")
    rows = []
    for cid in sorted(vectors):
        chunk = chunks[cid]
        book = books[chunk["document_id"]]
        if hashlib.sha256(chunk["text"].encode()).hexdigest() != chunk["text_hash"]:
            raise ValueError("Official chunk text hash mismatch")
        if len(vectors[cid]) != manifest["dimension"]:
            raise ValueError("Official vector dimension mismatch")
        rows.append(
            {
                "chunk_id": cid,
                "text": chunk["text"],
                "text_hash": chunk["text_hash"],
                "source_title": book["title"],
                "section": chunk["section"],
                "pages": chunk["pages"],
                "asset_id": book["id"],
                "source_url": book["source_url"],
            }
        )
    identity = {
        "release_id": release["id"],
        "bundle_sha256": file_hash(manifest_path),
        "data_sha256": manifest["data"]["sha256"],
        "vectors": len(vectors),
        "dimension": manifest["dimension"],
        "configuration": release["configuration"],
        "release_sha256": fingerprint(release),
        "book_count": len(books),
    }
    return rows, [vectors[row["chunk_id"]] for row in rows], identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if args.output.exists() or not 1 <= args.repeats <= 10:
        raise ValueError("Use a new evidence directory and one to ten warm repeats")
    args.output.mkdir(parents=True)
    import numpy as np
    import torch
    from retrieval.embedding import make_embedding
    from retrieval.lexical import LexicalIndex
    from retrieval.ranking import bm25, rrf

    cases_path = Path("configs/retrieval/cpu_replay_cases_20260926.json")
    cases = json.loads(cases_path.read_text())["cases"]
    policy = load_policy("configs/retrieval/chat_hybrid_minilm.json")
    artifact_sha = file_hash(args.artifact)
    started = time.perf_counter()
    rows, vectors, identity = corpus(args.bundle)
    manifest = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "case_sha256": file_hash(cases_path),
        "cases": cases,
        "corpus": identity,
        "model_policy": policy,
        "onnx_manifest_sha256": artifact_sha,
        "scope": "Offline official-bundle replay with fresh E5 CPU encoding and MiniLM scoring. No PostgreSQL query, live visibility check, answering call, support label or end-to-end product measurement.",
        "answer_model_calls": 0,
        "independent_human_labels": 0,
        "default_backend_changed": False,
        "warm_repeats": args.repeats,
        "libraries": {
            n: importlib.metadata.version(n)
            for n in ["torch", "numpy", "onnxruntime", "sentence-transformers"]
        },
    }
    dump(args.output / "frozen-input.json", manifest)
    matrix = np.asarray(vectors, dtype=np.float64)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    start = time.perf_counter()
    index = LexicalIndex(rows)
    manifest["lexical_build_ms"] = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    with torch_threads(2):
        embedder = make_embedding(identity["configuration"], runtime_device="cpu")
    manifest["embedding_load_ms"] = (time.perf_counter() - start) * 1000
    runtimes = {"torch_16": torch_runtime(16), "torch_2": torch_runtime(2)}
    for backend in ("onnx_fp32", "onnx_int8"):
        runtimes[backend] = torch_runtime(2) | {
            "backend": backend,
            "artifact_path": str(args.artifact),
            "artifact_sha256": artifact_sha,
        }
    observations, dev, fitted = [], [], None
    for case in cases:
        if case["split"] == "holdout" and fitted is None:
            dump(args.output / "development-fit-input.json", dev)
            fitted = fit_policy(dev)
            verify_group_holdout(fitted, [row for row in cases if row["split"] == "holdout"])
            dump(args.output / "frozen-adaptive-policy.json", fitted)
        query = case["query"]
        start = time.perf_counter()
        with torch_threads(2):
            encoded = np.asarray(embedder.encode([query], kind="query")[0], dtype=np.float64)
        embedding_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        scores = matrix @ (encoded / np.linalg.norm(encoded))
        dense_indices = sorted(range(len(rows)), key=lambda i: (-scores[i], rows[i]["chunk_id"]))[
            :50
        ]
        dense = [
            {**rows[i], "score": float(scores[i]), "score_type": "cosine"} for i in dense_indices
        ]
        dense_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        lexical = index.search(query, 50)
        lexical_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        reference_lexical = bm25(query, rows, 50)
        lexical_reference_ms = (time.perf_counter() - start) * 1000
        if [(x["chunk_id"], x["score"]) for x in lexical] != [
            (x["chunk_id"], x["score"]) for x in reference_lexical
        ]:
            raise AssertionError("Reference lexical IDs/scores changed")
        candidates = rrf([dense, lexical], k=20)
        result = dict(
            case,
            embedding_ms=embedding_ms,
            dense_ms=dense_ms,
            lexical_ms=lexical_ms,
            lexical_reference_ms=lexical_reference_ms,
            lexical_exact=True,
            candidate_ids=[x["chunk_id"] for x in candidates],
            backends={},
        )
        for backend, runtime in runtimes.items():
            candidate_policy = dict(
                policy,
                version="chat_hybrid_rerank_v2",
                reranker_device="cpu",
                reranker_runtime=runtime,
                adaptive_policy=None,
            )
            repetitions = []
            try:
                for repeat in range(args.repeats + 1):
                    start = time.perf_counter()
                    ranked, trace = rerank_candidates(query, candidates, candidate_policy)
                    repetitions.append(
                        {
                            "phase": "first_observation"
                            if not observations and repeat == 0
                            else "warm",
                            "elapsed_ms": (time.perf_counter() - start) * 1000,
                            "model_ms": trace["rerank_ms"],
                        }
                    )
                result["backends"][backend] = {
                    "status": "completed",
                    "runtime": runtime,
                    "measurements": repetitions,
                    "ordered_ids": [x["chunk_id"] for x in ranked],
                    "scores": {x["chunk_id"]: x["score"] for x in ranked},
                }
            except Exception as exc:
                result["backends"][backend] = {
                    "status": "failed",
                    "error": type(exc).__name__,
                    "detail": str(exc),
                    "measurements": repetitions,
                }
        reference = result["backends"]["torch_2"]
        if reference["status"] != "completed":
            dump(args.output / f"{case['id']}.json", result)
            raise RuntimeError("Reference reranking failed; cannot fit a budget")
        reference_ids = reference["ordered_ids"][:5]
        if case["split"] == "development":
            dev.append(dict(case, candidates=candidates, reference_ids=reference_ids))
        for backend, value in result["backends"].items():
            if value["status"] != "completed":
                continue
            value["top5_order_equal"] = value["ordered_ids"][:5] == reference_ids
            value["top5_retained_count"] = len(set(value["ordered_ids"][:5]) & set(reference_ids))
            value["maximum_absolute_logit_difference"] = max(
                abs(value["scores"][cid] - reference["scores"][cid]) for cid in reference["scores"]
            )
            value["provisional_threshold_crossings"] = sum(
                (value["scores"][cid] >= -4) != (reference["scores"][cid] >= -4)
                for cid in reference["scores"]
            )
        if fitted is not None:
            budget, decision = choose_budget(query, candidates, fitted)
            proposed = {x["chunk_id"] for x in candidates[:budget]}
            result["adaptive_shadow"] = decision | {
                "executed_budget": 20,
                "reference_top5_retained": set(reference_ids).issubset(proposed),
                "reference_top5_retained_count": len(set(reference_ids) & proposed),
            }
        result["reference_top_passages"] = [
            next(row for row in candidates if row["chunk_id"] == cid) for cid in reference_ids
        ]
        result["process_memory"] = process_memory()
        observations.append(result)
        dump(args.output / f"{case['id']}.json", result)
        print(
            json.dumps(
                {
                    "id": case["id"],
                    "split": case["split"],
                    "backends": {k: v["status"] for k, v in result["backends"].items()},
                }
            ),
            flush=True,
        )
    summary = {
        "scheduled_cases": len(cases),
        "completed_cases": len(observations),
        "backends": {},
        "lexical_exact_cases": sum(x["lexical_exact"] for x in observations),
        "quality_gate": "Experimental only: no supported-answer or independent relevance labels",
        "adaptive_policy": fitted,
        "human_review_count": 0,
        "corpus_data_hash_unchanged": file_hash(args.bundle / "corpus.jsonl.gz")
        == identity["data_sha256"],
        "total_seconds": time.perf_counter() - started,
    }
    for backend in runtimes:
        values = [x["backends"][backend] for x in observations]
        warm = [m["elapsed_ms"] for v in values for m in v["measurements"] if m["phase"] == "warm"]
        summary["backends"][backend] = {
            "scheduled": len(values),
            "completed": sum(v["status"] == "completed" for v in values),
            "warm_n": len(warm),
            "warm_median_ms": statistics.median(warm) if warm else None,
            "warm_p95_ms": float(np.percentile(warm, 95)) if warm else None,
            "top5_order_equal": sum(v.get("top5_order_equal", False) for v in values),
            "top5_retained_mean": statistics.mean(
                v["top5_retained_count"] / 5 for v in values if v["status"] == "completed"
            ),
            "provisional_threshold_crossings": sum(
                v.get("provisional_threshold_crossings", 0) for v in values
            ),
        }
    held = [x["adaptive_shadow"] for x in observations if "adaptive_shadow" in x]
    summary["adaptive_shadow"] = {
        "heldout_n": len(held),
        "reference_top5_complete": sum(x["reference_top5_retained"] for x in held),
        "proposed_budgets": [x["proposed_budget"] for x in held],
        "executed_budget": 20,
    }
    dump(args.output / "summary.json", summary)
    dump(
        args.output / "runtime.json",
        manifest | {"finished_at": datetime.now(timezone.utc).isoformat()},
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
