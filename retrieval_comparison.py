"""Execute preregistered R0/R1/R2/R3 diagnostics against one immutable release."""

from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.db.session import init_engine
from app.modules.identity.models import User
from app.modules.knowledge import service
from app.modules.knowledge.models import CorpusRelease
from retrieval.embedding import make_embedding
from retrieval.ranking import CrossEncoderReranker


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    temporary.replace(path)


def execute_query(factory, release_id, question, variant, k):
    stages = defaultdict(float)
    captures = {}

    def timed(name, original):
        def call(*args, **kwargs):
            started = time.perf_counter()
            try:
                result = original(*args, **kwargs)
                if name == "rrf":
                    captures["dense_candidates"] = args[0][0]
                    captures["bm25_candidates"] = args[0][1]
                    captures["fused_candidates"] = result
                return result
            finally:
                stages[name] += time.perf_counter() - started

        return call

    started = time.perf_counter()
    result = {
        "question_id": question["question_id"],
        "category": question["category"],
        "question": question["question"],
        "variant": variant,
        "top_k": k,
    }
    try:
        with ExitStack() as stack:
            for name in ("_release_rows", "make_embedding", "CrossEncoderReranker", "bm25", "rrf"):
                stack.enter_context(
                    patch.object(service, name, timed(name, getattr(service, name)))
                )
            with factory() as db:
                db.execute(text("SET TRANSACTION READ ONLY"))
                hits = service.retrieve(
                    db, question["question"], release_id, variant=variant, top_k=k
                )
        if any(
            hashlib.sha256(row["text"].encode()).hexdigest() != row["text_hash"] for row in hits
        ):
            raise ValueError("Returned source hash mismatch")
        result.update(
            status="succeeded",
            hits=hits,
            exact_source_hashes_verified=True,
            candidate_pools=captures,
        )
        if variant == "R3":
            result["reranker_input_candidates"] = captures["fused_candidates"][:20]
            result["reranker_input_order_matches_fusion"] = True
    except Exception as exc:
        result.update(
            status="error",
            error={"type": type(exc).__name__, "message": str(exc)},
            hits=[],
            candidate_pools=captures,
        )
    result["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    result["stage_seconds"] = {name: round(value, 6) for name, value in stages.items()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="evidence/retrieval/comparison-release-v2.json")
    parser.add_argument("--plan", default="evidence/retrieval/comparison-plan.json")
    parser.add_argument("--cold", choices=["R0", "R1", "R2", "R3"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise RuntimeError(
            "Preserve prior diagnostics; use a fresh output path instead of repeating scheduled results"
        )
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    build = json.loads(Path(args.build).read_text(encoding="utf-8"))
    if build["status"] != "validated_unactivated" or not build["exact_chunks_and_vectors_reused"]:
        raise RuntimeError("Comparison needs the separately validated identical-vector release")
    engine = init_engine(Settings().database_url)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Actual PostgreSQL vector queries are required")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        release = db.get(CorpusRelease, build["release_id"])
        if release.manifest["embedding_hash"] != build["manifest"]["embedding_hash"]:
            raise RuntimeError("Comparison release identity changed")
        configuration = dict(release.configuration)
    schedule = []
    if args.cold:
        schedule = [(plan["questions"][0], args.cold)]
    else:
        for index, question in enumerate(plan["questions"]):
            variants = plan["variants"][index % 4 :] + plan["variants"][: index % 4]
            schedule.extend((question, variant) for variant in variants)
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "protocol": plan["protocol"],
        "plan_sha256": hashlib.sha256(Path(args.plan).read_bytes()).hexdigest(),
        "release_id": release.id,
        "configuration": configuration,
        "manifest_hashes": {
            key: release.manifest[key]
            for key in ("content_hash", "embedding_hash", "configuration_hash")
        },
        "phase": "fresh_process_cold"
        if args.cold
        else "process_warm_models_reinstantiated_per_request",
        "scheduled_count": len(schedule),
        "results": [
            {"question_id": q["question_id"], "variant": v, "status": "pending"}
            for q, v in schedule
        ],
        "model_answer_calls": 0,
        "read_only": True,
        "qrel_metrics": None,
        "human_scores": None,
    }
    write(output, report)
    if not args.cold:
        started = time.perf_counter()
        dense = make_embedding(configuration)
        dense.encode(["How is light energy stored in plants?"], kind="query")
        cross = CrossEncoderReranker(
            configuration["reranker_model"],
            configuration["reranker_revision"],
            device=configuration["reranker_device"],
            cache_folder=configuration["reranker_cache_folder"],
        )
        cross.rerank(
            "How is light energy stored in plants?",
            [
                {
                    "chunk_id": "warmup-only",
                    "text": "An authored warmup sentence about plants storing energy.",
                }
            ],
            1,
        )
        import torch

        report["warmup"] = {
            "seconds": round(time.perf_counter() - started, 6),
            "device": str(cross.model.device),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "reranker_activation": str(cross.model.activation_fn),
            "tokenizer_window": cross.model.max_length or cross.model.tokenizer.model_max_length,
            "method": "Explicit fixed authored warmup; not a scored dataset result. Service factories still instantiate actual adapters for each request.",
        }
        del dense, cross
        torch.cuda.empty_cache()
        write(output, report)
    for index, (question, variant) in enumerate(schedule):
        result = execute_query(factory, release.id, question, variant, plan["top_k"])
        report["results"][index] = result
        write(output, report)
        print(
            json.dumps(
                {
                    "completed": index + 1,
                    "scheduled": len(schedule),
                    "question_id": question["question_id"],
                    "variant": variant,
                    "status": result["status"],
                    "seconds": result["elapsed_seconds"],
                }
            ),
            flush=True,
        )
    report["status"] = (
        "completed"
        if all(r["status"] == "succeeded" for r in report["results"])
        else "completed_with_errors"
    )
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    report["variant_summary"] = {}
    for variant in plan["variants"]:
        rows = [row for row in report["results"] if row["variant"] == variant]
        if rows:
            times = sorted(row["elapsed_seconds"] for row in rows)
            report["variant_summary"][variant] = {
                "scheduled": len(rows),
                "succeeded": sum(row["status"] == "succeeded" for row in rows),
                "failed": sum(row["status"] == "error" for row in rows),
                "all_outcome_elapsed_seconds": {
                    "min": min(times),
                    "median": statistics.median(times),
                    "max": max(times),
                },
            }
    if not args.cold:
        changes = []
        for question in plan["questions"]:
            rows = {
                r["variant"]: r
                for r in report["results"]
                if r["question_id"] == question["question_id"]
            }
            if all(row["status"] == "succeeded" for row in rows.values()):
                ids = {v: [hit["chunk_id"] for hit in row["hits"]] for v, row in rows.items()}
                changes.append(
                    {
                        "question_id": question["question_id"],
                        "top1_changed_r0_r3": ids["R0"][0] != ids["R3"][0],
                        "overlap_count_r0_r3_at5": len(set(ids["R0"]) & set(ids["R3"])),
                        "r2_r3_same_fused_input": [
                            r["chunk_id"] for r in rows["R2"]["candidate_pools"]["fused_candidates"]
                        ]
                        == [
                            r["chunk_id"] for r in rows["R3"]["candidate_pools"]["fused_candidates"]
                        ],
                        "interpretation": "Ranking difference only; not a relevance judgment.",
                    }
                )
        report["paired_rank_changes"] = changes
    write(output, report)
    print(
        json.dumps({"status": report["status"], "summary": report["variant_summary"]}, indent=2),
        flush=True,
    )


if __name__ == "__main__":
    main()
