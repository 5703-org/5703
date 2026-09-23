"""Run the frozen question set on real CPU retrieval and export a review pool."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.knowledge.models import CorpusRelease
from app.modules.knowledge.service import retrieve, digest
from conversation.query import prepare_query
from retrieval.chat import load_policy, rerank_candidates
from retrieval.relevance import freeze_policy, screen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve previous retrieval pools")
    import torch

    torch.set_num_threads(2)
    root = Path(__file__).resolve().parents[2]
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    policy = load_policy(root / "configs/retrieval/chat_hybrid_minilm.json")
    relevance = freeze_policy(policy)
    report = {
        "version": "week08-source-review-pool-v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
        "model": policy["reranker_model"],
        "revision": policy["reranker_revision"],
        "relevance_policy": relevance,
        "device": "cpu",
        "model_calls": 0,
        "scope": "Actual frozen-case retrieval; expected topical availability is developer-authored. Pair labels remain blank for independent review; no formal threshold is fitted.",
        "cases": [],
        "rows": [],
    }
    engine = create_engine(Settings().database_url)

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    with Session(engine) as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        release = db.get(CorpusRelease, plan["corpus_release_id"])
        before = digest({"configuration": release.configuration, "manifest": release.manifest})
        report["corpus_release_id"] = release.id
        report["release_fingerprint_before"] = before
        for case in plan["cases"]:
            if case.get("execution") == "isolated_fault_test":
                continue
            started = time.monotonic()
            history = [
                {
                    "id": f"history-{i}",
                    "role": r["role"],
                    "content": r["content"],
                    "sequence": i + 1,
                    "state": "completed",
                }
                for i, r in enumerate(case["history"])
            ]
            prepared = prepare_query(case["question"], history)
            row = {
                "id": case["id"],
                "category": case["category"],
                "split": case["split"],
                "group": case["group"],
                "expected_behavior": case["expected_behavior"],
                "prepared": prepared.model_dump(),
            }
            report["cases"].append(row)
            try:
                if prepared.needs_clarification or not prepared.standalone_query:
                    row["status"] = "clarification"
                    row["accepted_count"] = 0
                else:
                    query = prepared.standalone_query
                    found = retrieve(
                        db, query, release.id, variant="R2", top_k=20, runtime_device="cpu"
                    )
                    ranked, trace = rerank_candidates(query, found, policy, runtime_device="cpu")
                    accepted, screening = screen(query, ranked, relevance)
                    row.update(
                        status="retrieved",
                        accepted_count=len(accepted),
                        relevance=screening,
                        retrieval=trace,
                    )
                    bound = [
                        p
                        for key in case["source_topics"]
                        for p in plan["source_topics"][key]["passages"]
                    ]
                    ids = {p["id"] for p in bound}
                    row["bound_anchor_retrieved"] = (
                        bool(ids & {r["chunk_id"] for r in ranked}) if ids else None
                    )
                    row["bound_anchor_retained"] = (
                        bool(ids & {r["chunk_id"] for r in accepted}) if ids else None
                    )
                    for item in ranked:
                        if hashlib.sha256(item["text"].encode()).hexdigest() != item["text_hash"]:
                            raise ValueError("Candidate source hash differs")
                        report["rows"].append(
                            {
                                "question_id": case["id"],
                                "question": case["question"],
                                "group": case["group"],
                                "split": case["split"],
                                "model": policy["reranker_model"],
                                "revision": policy["reranker_revision"],
                                "label": None,
                                "reviewer_id": None,
                                "reviewed_at": None,
                                "source_anchor_candidate": item["chunk_id"] in ids,
                                **{
                                    k: item[k]
                                    for k in (
                                        "chunk_id",
                                        "processing_id",
                                        "text",
                                        "text_hash",
                                        "source_title",
                                        "source_url",
                                        "section",
                                        "pages",
                                        "score",
                                    )
                                },
                            }
                        )
                expected = case["expected_behavior"]
                row["developer_expectation_met"] = (
                    (row["status"] == "clarification")
                    if expected == "clarification"
                    else (
                        row["accepted_count"] > 0
                        if expected in {"answer", "partial_answer"}
                        else row["accepted_count"] == 0
                    )
                )
            except Exception as exc:
                row.update(
                    status="error",
                    error={"type": type(exc).__name__, "message": str(exc)[:300]},
                    developer_expectation_met=False,
                )
            row["seconds"] = round(time.monotonic() - started, 3)
            save()
            print(
                json.dumps(
                    {
                        "id": row["id"],
                        "status": row["status"],
                        "accepted": row.get("accepted_count"),
                        "met": row["developer_expectation_met"],
                    }
                ),
                flush=True,
            )
        db.expire(release)
        after = digest({"configuration": release.configuration, "manifest": release.manifest})
        report["release_fingerprint_after"] = after
        report["corpus_unchanged"] = before == after
        assert before == after
    engine.dispose()
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["status_counts"] = dict(Counter(r["status"] for r in report["cases"]))
    report["developer_expectations_met"] = sum(
        r["developer_expectation_met"] for r in report["cases"]
    )
    report["independent_labels"] = 0
    save()


if __name__ == "__main__":
    main()
