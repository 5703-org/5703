"""Read-only paired PostgreSQL retrieval/cache comparison on the frozen CPU query groups."""

import argparse
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time
from unittest.mock import patch
import zipfile

from scripts.verify.cpu_backend_replay import dump, process_memory
from retrieval.cpu_backend import file_hash


def canonical(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def source_fingerprints(db, release_id):
    from sqlalchemy import text
    from app.core.config import Settings

    storage = Path(Settings().storage_root).resolve()

    result = {}
    for name, statement in {
        "documents": "SELECT id, title, edition, source_url, license, active, revoked FROM documents ORDER BY id",
        "source_assets": "SELECT id, document_id, raw_hash, storage_path FROM document_versions ORDER BY id",
        "release": "SELECT id, state, configuration, manifest FROM corpus_releases WHERE id=:release_id",
        "epoch": "SELECT token FROM retrieval_epochs WHERE id=1",
        "active_release": "SELECT id, release_id FROM active_corpus ORDER BY id",
    }.items():
        values = [
            dict(row) for row in db.execute(text(statement), {"release_id": release_id}).mappings()
        ]
        result[name] = canonical(values)
        if name == "source_assets":
            result["original_files"] = {
                row["id"]: {
                    "recorded": row["raw_hash"],
                    "actual": file_hash(storage / row["storage_path"]),
                }
                for row in values
            }
            if any(v["recorded"] != v["actual"] for v in result["original_files"].values()):
                raise ValueError("Original source asset hash mismatch")
    statement = text("""
        SELECT count(*) AS vector_count, min(dimension) AS minimum_dimension,
          max(dimension) AS maximum_dimension,
          md5(string_agg(chunk_id || ':' || embedding::text || ':' || dimension::text || ':' || model_revision,
              '|' ORDER BY chunk_id)) AS vector_fingerprint
        FROM release_chunks WHERE release_id=:release_id
    """)
    result["vectors"] = dict(db.execute(statement, {"release_id": release_id}).mappings().one())
    chunks = [
        dict(row)
        for row in db.execute(
            text("""
        SELECT c.id,c.document_id,c.processing_id,c.text,c.text_hash,c.section,c.pages,c.spans,c.tokens
        FROM chunks c JOIN release_chunks r ON r.chunk_id=c.id
        WHERE r.release_id=:release_id ORDER BY c.id
    """),
            {"release_id": release_id},
        ).mappings()
    ]
    result["chunk_content"] = canonical(chunks)
    result["chunk_count"] = len(chunks)
    return result


@contextmanager
def measured_functions(service, query_cache, timing):
    """Observe existing execution without changing inputs, outputs or cached values."""
    original_release, original_bm25 = service._release_rows, service.bm25
    service_factory, cache_factory = service.make_embedding, query_cache.make_embedding

    def timed(name, function, *args, **kwargs):
        started = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            timing[name] += (time.perf_counter() - started) * 1000

    class Embedding:
        def __init__(self, value):
            self.value = value

        def encode(self, *args, **kwargs):
            return timed("query_encoding_ms", self.value.encode, *args, **kwargs)

    def factory(original, *args, **kwargs):
        return Embedding(timed("embedding_model_lookup_ms", original, *args, **kwargs))

    with (
        patch.object(
            service,
            "_release_rows",
            lambda *a, **k: timed("complete_validation_ms", original_release, *a, **k),
        ),
        patch.object(
            service, "bm25", lambda *a, **k: timed("reference_lexical_ms", original_bm25, *a, **k)
        ),
        patch.object(service, "make_embedding", lambda *a, **k: factory(service_factory, *a, **k)),
        patch.object(
            query_cache, "make_embedding", lambda *a, **k: factory(cache_factory, *a, **k)
        ),
    ):
        yield


def normalized(rows):
    return [{key: value for key, value in row.items() if key != "rerank_ms"} for row in rows]


def summary(values):
    import numpy as np

    return {
        "n": len(values),
        "median": statistics.median(values) if values else None,
        "p95": float(np.percentile(values, 95)) if values else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connection-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if args.output.exists() or not 2 <= args.repeats <= 3:
        raise ValueError("Use a new evidence directory and two or three repetitions")
    args.output.mkdir(parents=True)
    import torch
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.orm import Session
    from app.modules.knowledge import cache, service
    from app.modules.knowledge.models import ActiveCorpus
    from retrieval import query_cache
    from retrieval.embedding import _e5_model
    from retrieval.chat import _reranker, load_policy, rerank_candidates

    connection = json.loads(args.connection_file.read_text(encoding="utf-8"))
    engine = create_engine(connection["database_url"], hide_parameters=True)
    del connection
    active_sql = {"timing": None}

    @event.listens_for(engine, "before_cursor_execute")
    def before_sql(conn, cursor, statement, parameters, context, executemany):
        context._performance_start = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after_sql(conn, cursor, statement, parameters, context, executemany):
        timing = active_sql["timing"]
        if timing is not None:
            elapsed = (time.perf_counter() - context._performance_start) * 1000
            timing["sql_ms"] += elapsed
            timing["sql_count"] += 1
            if "<=>" in statement:
                timing["dense_sql_ms"] += elapsed

    def readonly():
        db = Session(engine)
        db.execute(text("SET TRANSACTION READ ONLY"))
        if db.scalar(text("SHOW transaction_read_only")) != "on":
            db.close()
            raise ValueError("The performance study requires a read-only transaction")
        return db

    with readonly() as db:
        release_id = db.get(ActiveCorpus, 1).release_id
        before = source_fingerprints(db, release_id)
    cases_path = Path("configs/retrieval/cpu_replay_cases_20260926.json")
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    policy = load_policy("configs/retrieval/chat_hybrid_minilm.json")
    sources = [
        "backend/app/modules/knowledge/service.py",
        "backend/app/modules/knowledge/cache.py",
        "retrieval/lexical.py",
        "retrieval/query_cache.py",
        "retrieval/chat.py",
        "retrieval/embedding.py",
        "retrieval/ranking.py",
        "scripts/verify/pg_retrieval_performance.py",
    ]
    with zipfile.ZipFile(args.output / "source-snapshot.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            archive.write(source, source)
    frozen = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": {p: file_hash(p) for p in sources},
        "source_snapshot_sha256": file_hash(args.output / "source-snapshot.zip"),
        "case_sha256": file_hash(cases_path),
        "cases": cases,
        "warm_repeats": args.repeats,
        "model_policy": policy,
        "torch": torch.__version__,
        "torch_threads": torch.get_num_threads(),
        "database": "isolated PostgreSQL/pgvector at localhost:18532",
        "transaction_mode": "READ ONLY",
        "scope": "Local retrieval plus reranking; excludes HTTP queue, generation/checking, publication and browser display",
        "cold_definition": "Cleared process-local model/release/query caches; OS file cache and imported libraries remain warm",
        "answer_model_calls": 0,
        "fingerprints_before": before,
    }
    dump(args.output / "frozen-input.json", frozen)
    all_rows, pair_checks = [], []

    def execute(case, arm, phase, repeat):
        timing, trace = defaultdict(float), {}
        observation = {
            "case_id": case["id"],
            "split": case["split"],
            "query": case["query"],
            "arm": arm,
            "phase": phase,
            "repeat": repeat,
        }
        result = None
        started = time.perf_counter()
        try:
            with readonly() as db:
                active_sql["timing"] = timing
                at = time.perf_counter()
                with measured_functions(service, query_cache, timing):
                    candidates = service.retrieve(
                        db,
                        case["query"],
                        release_id,
                        variant="R2",
                        top_k=20,
                        runtime_device="cpu",
                        cache_scope="performance-fixture" if arm == "validated_cache" else None,
                        execution_trace=trace,
                    )
                timing["retrieval_ms"] = (time.perf_counter() - at) * 1000
                for name in ("query_embedding_ms", "dense_ms", "lexical_ms"):
                    if name in trace:
                        timing["cached_" + name] = trace[name]
                if "release_cache" in trace:
                    timing["cached_release_validation_ms"] = trace["release_cache"]["validation_ms"]
                at = time.perf_counter()
                ranked, ranking_trace = rerank_candidates(
                    case["query"], candidates, policy, runtime_device="cpu"
                )
                timing["reranking_ms"] = (time.perf_counter() - at) * 1000
                if db.new or db.dirty or db.deleted:
                    raise AssertionError("Read-only retrieval created ORM mutations")
                result = {"candidates": normalized(candidates), "ranked": normalized(ranked)}
                observation.update(
                    status="completed",
                    candidate_ids=[r["chunk_id"] for r in candidates],
                    ranked_ids=[r["chunk_id"] for r in ranked],
                    candidate_sha256=canonical(result["candidates"]),
                    ranked_sha256=canonical(result["ranked"]),
                    retrieval_trace=trace,
                    rerank_model_ms=ranking_trace["rerank_ms"],
                    passage_samples=normalized(ranked[:3]),
                )
        except Exception as exc:
            # Keep raw connection exception strings out of public evidence.
            observation.update(
                status="failed",
                error_type=type(exc).__name__,
                error_code=getattr(exc, "code", None),
            )
        finally:
            active_sql["timing"] = None
            timing["local_total_ms"] = (time.perf_counter() - started) * 1000
            observation["timing"] = dict(timing)
            observation["memory"] = process_memory()
            all_rows.append(observation)
            dump(args.output / f"{phase}-{case['id']}-{repeat}-{arm}.json", observation)
            print(
                json.dumps(
                    {k: observation[k] for k in ("case_id", "arm", "phase", "repeat", "status")}
                    | {"local_ms": round(timing["local_total_ms"], 2)}
                ),
                flush=True,
            )
        return result

    for arm in ("reference", "validated_cache"):
        cache.clear()
        with query_cache._LOCK:
            query_cache._ITEMS.clear()
        _e5_model.cache_clear()
        _reranker.cache_clear()
        gc.collect()
        execute(cases[0], arm, "cold_local_models", 0)
    # Retain the built release index and models; measure a new query and repeat separately.
    with query_cache._LOCK:
        query_cache._ITEMS.clear()
    for index, case in enumerate(cases):
        for repeat in range(args.repeats):
            order = (
                ("reference", "validated_cache")
                if (index + repeat) % 2 == 0
                else ("validated_cache", "reference")
            )
            paired = {arm: execute(case, arm, "warm", repeat) for arm in order}
            comparable = all(paired.values())
            check = {
                "case_id": case["id"],
                "repeat": repeat,
                "comparable": comparable,
                "candidate_exact": comparable
                and paired["reference"]["candidates"] == paired["validated_cache"]["candidates"],
                "reranked_exact": comparable
                and paired["reference"]["ranked"] == paired["validated_cache"]["ranked"],
            }
            pair_checks.append(check)
            dump(args.output / "pair-checks.json", pair_checks)
    with readonly() as db:
        after = source_fingerprints(db, release_id)
    report = {
        "scheduled_warm": len(cases) * args.repeats * 2,
        "scheduled_cold": 2,
        "outcomes": {
            status: sum(row["status"] == status for row in all_rows)
            for status in ("completed", "failed")
        },
        "warm_pairs": len(pair_checks),
        "candidate_exact_pairs": sum(x["candidate_exact"] for x in pair_checks),
        "reranked_exact_pairs": sum(x["reranked_exact"] for x in pair_checks),
        "fingerprints_unchanged": before == after,
        "fingerprints_after": after,
        "source_unchanged_during_run": all(
            file_hash(p) == h for p, h in frozen["source_sha256"].items()
        ),
        "arms": {},
        "scope": frozen["scope"],
        "answer_model_calls": 0,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    for arm in ("reference", "validated_cache"):
        selected = [row for row in all_rows if row["arm"] == arm and row["phase"] == "warm"]
        timings = {
            name: summary([row["timing"][name] for row in selected if name in row["timing"]])
            for name in sorted(
                {key for row in selected for key in row["timing"] if key.endswith("_ms")}
            )
        }
        report["arms"][arm] = {
            "scheduled": len(cases) * args.repeats,
            "recorded": len(selected),
            "completed": sum(row["status"] == "completed" for row in selected),
            "all_stage_ms": timings,
            "sql_statement_count": summary([row["timing"].get("sql_count", 0) for row in selected]),
            "successful_local_total_ms": summary(
                [
                    row["timing"]["local_total_ms"]
                    for row in selected
                    if row["status"] == "completed"
                ]
            ),
            "failed_local_total_ms": summary(
                [row["timing"]["local_total_ms"] for row in selected if row["status"] == "failed"]
            ),
            "release_cache_hits": sum(
                row.get("retrieval_trace", {}).get("release_cache", {}).get("hit", False)
                for row in selected
            ),
            "query_cache_hits": sum(
                row.get("retrieval_trace", {}).get("query_vector_cache_hit", False)
                for row in selected
            ),
        }
    reference_p95 = report["arms"]["reference"]["all_stage_ms"]["local_total_ms"]["p95"]
    cached_p95 = report["arms"]["validated_cache"]["all_stage_ms"]["local_total_ms"]["p95"]
    report["warm_local_p95_reduction"] = 1 - cached_p95 / reference_p95
    dump(args.output / "summary.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "outcomes",
                    "candidate_exact_pairs",
                    "reranked_exact_pairs",
                    "fingerprints_unchanged",
                    "warm_local_p95_reduction",
                )
            },
            indent=2,
        )
    )
    engine.dispose()


if __name__ == "__main__":
    main()
