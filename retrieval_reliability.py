"""Read-only real CPU retrieval checks; writes evidence, never corpus/application rows."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time


CASES = [
    ("development", True, "What is photosynthesis?"),
    ("development", True, "How does osmosis work?"),
    ("development", True, "What is the ideal gas law?"),
    ("development", True, "How do enzymes affect activation energy?"),
    ("development", True, "How does ragweed pollen cause an allergic reaction?"),
    (
        "development",
        False,
        "What is Retrieval-Augmented Generation (RAG) in artificial intelligence?",
    ),
    ("development", False, "How do I configure a Kubernetes deployment?"),
    ("development", False, "Who won the 2026 football World Cup?"),
    ("holdout", True, "How does ATP provide energy for cellular work?"),
    ("holdout", True, "Compare DNA and RNA."),
    ("holdout", True, "How do acids and bases differ?"),
    ("holdout", True, "Why do some people sneeze after breathing ragweed pollen?"),
    ("holdout", True, "How are the light reactions and Calvin cycle connected?"),
    ("holdout", False, "How does BERT pretraining use masked language modeling?"),
    ("holdout", False, "Explain transformer neural networks for language generation."),
    ("holdout", False, "How can I generate an API key for DeepSeek?"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import torch
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from app.core.config import Settings
    from app.modules.knowledge.models import ActiveCorpus, CorpusRelease
    from app.modules.knowledge.service import retrieve, digest
    from conversation.query import prepare_query
    from retrieval.embedding import make_embedding
    from retrieval.chat import load_policy, rerank_candidates, _reranker
    from retrieval.relevance import freeze_policy, screen

    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if not output.is_relative_to(root / "evidence"):
        raise ValueError("Output must be inside project evidence")
    torch.set_num_threads(2)
    settings = Settings()
    engine = create_engine(settings.database_url)
    policy = load_policy(root / "configs/retrieval/chat_hybrid_minilm.json")
    gate = freeze_policy(policy)
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "torch": torch.__version__,
        "execution_device": "cpu",
        "database_mode": "READ ONLY",
        "answer_model_calls": 0,
        "gate_policy": gate,
        "cases": [],
        "scope": "Development and held-out topic screening examples; not independent qrels, answer quality or a learning-outcome study",
    }
    with Session(engine) as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        release_id = db.get(ActiveCorpus, 1).release_id
        release = db.get(CorpusRelease, release_id)
        before = digest({"configuration": release.configuration, "manifest": release.manifest})
        count_before = db.execute(
            text(
                "SELECT count(*), min(dimension), max(dimension) FROM release_chunks WHERE release_id=:id"
            ),
            {"id": release_id},
        ).one()
        report.update(
            release_id=release_id,
            release_fingerprint_before=before,
            recorded_embedding_device=release.configuration.get("embedding_device"),
            vector_count=count_before[0],
            dimension_range=list(count_before[1:]),
            embedding_model=release.configuration.get("embedding_model"),
            embedding_revision=release.configuration.get("embedding_revision"),
        )
        for split, expected, question in CASES:
            prepared = prepare_query(question)
            query = prepared.standalone_query
            start = time.perf_counter()
            rows = retrieve(db, query, release_id, variant="R2", top_k=20, runtime_device="cpu")
            ranked, trace = rerank_candidates(query, rows, policy, runtime_device="cpu")
            accepted, screened = screen(query, ranked, gate)
            for row in ranked:
                assert hashlib.sha256(row["text"].encode()).hexdigest() == row["text_hash"]
            result = {
                "split": split,
                "question": question,
                "prepared": prepared.model_dump(),
                "expected_topic_evidence": expected,
                "has_accepted_evidence": bool(accepted),
                "expectation_met": bool(accepted) == expected,
                "seconds": round(time.perf_counter() - start, 3),
                "retrieval": trace,
                "relevance": screened,
                "ranked_scores": [{"chunk_id": r["chunk_id"], "score": r["score"]} for r in ranked],
                "top_passages": [
                    {
                        k: r[k]
                        for k in (
                            "chunk_id",
                            "source_title",
                            "source_url",
                            "section",
                            "pages",
                            "locator",
                            "text",
                            "text_hash",
                            "score",
                            "quality_warnings",
                        )
                    }
                    for r in ranked[:3]
                ],
            }
            report["cases"].append(result)
            print(
                json.dumps(
                    {k: result[k] for k in ("question", "expectation_met", "seconds")}
                    | {
                        "accepted": len(accepted),
                        "top_logit": ranked[0]["score"] if ranked else None,
                    }
                ),
                flush=True,
            )
        embedder = make_embedding(release.configuration, runtime_device="cpu")
        ranker = _reranker(
            policy["reranker_model"],
            policy["reranker_revision"],
            "cpu",
            policy["reranker_cache_folder"],
        )
        report["actual_embedding_device"] = str(embedder.model.device)
        report["actual_reranker_device"] = str(ranker.model.model.device)
        assert report["actual_embedding_device"] == report["actual_reranker_device"] == "cpu"
        db.expire(release)
        after = digest({"configuration": release.configuration, "manifest": release.manifest})
        report.update(
            release_fingerprint_after=after,
            release_unchanged=before == after,
            all_screening_expectations_met=all(c["expectation_met"] for c in report["cases"]),
        )
        assert before == after
    engine.dispose()
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Evidence written:", output)


if __name__ == "__main__":
    main()
