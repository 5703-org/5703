"""Freeze real read-only CPU retrieval for protected grouped study questions."""

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.modules.knowledge import service
from app.modules.model_settings.models import ModelConfiguration
from app.modules.model_settings.service import as_model_config, resolve_active_checker_model_config
from conversation.query import prepare_query
from evaluation.enhancement.sources import corpus_fingerprint, source_map
from retrieval.chat import load_policy, rerank_candidates
from retrieval.relevance import freeze_policy, screen
from .review import write

ROOT = Path(__file__).resolve().parents[2]


def prepare(catalogue: Path, connection_file: Path, output: Path):
    if output.exists():
        raise ValueError("Use a new preparation directory")
    inventory = json.loads(catalogue.read_text(encoding="utf-8"))
    rows = inventory["cases"]
    if len({row["id"] for row in rows}) != len(rows) or len({row["family"] for row in rows}) != len(
        rows
    ):
        raise ValueError("Every knowledge group must have one unique catalogue identity")
    connection = json.loads(connection_file.read_text(encoding="utf-8"))
    engine = create_engine(
        connection["database_url"], hide_parameters=True, connect_args={"connect_timeout": 10}
    )
    del connection
    output.mkdir(parents=True)
    policy = load_policy(ROOT / "configs/retrieval/chat_hybrid_minilm.json")
    relevance = freeze_policy(policy)
    import torch

    torch.set_num_threads(16)
    records = []
    try:
        with Session(engine) as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            if db.scalar(text("SHOW transaction_read_only")) != "on":
                raise ValueError("Preparation requires read-only PostgreSQL")
            release_id = db.scalar(text("select release_id from active_corpus where id=1"))
            before = corpus_fingerprint(db, release_id)
            active = db.execute(
                text(
                    "select workspace_id, configuration_id from active_model_configurations where configuration_id is not null order by workspace_id"
                )
            ).one()
            model = as_model_config(
                db.scalar(
                    select(ModelConfiguration).where(
                        ModelConfiguration.id == active.configuration_id
                    )
                )
            )
            checker = resolve_active_checker_model_config(db, None, active.workspace_id) or replace(
                model, max_tokens=max(4096, model.max_tokens)
            )
            for case in rows:
                start = time.perf_counter()
                query = prepare_query(case["question"], [])
                trace = {}
                candidates = service.retrieve(
                    db,
                    query.standalone_query or case["question"],
                    release_id,
                    variant="R2",
                    top_k=20,
                    runtime_device="cpu",
                    cache_scope="week09-research",
                    execution_trace=trace,
                )
                ranked, ranking = rerank_candidates(
                    query.standalone_query or case["question"],
                    candidates,
                    policy,
                    runtime_device="cpu",
                )
                accepted, filtering = screen(
                    query.standalone_query or case["question"], ranked, relevance
                )
                evidence = [
                    {**item, "evidence_id": f"ev_{index:03d}"}
                    for index, item in enumerate(accepted, 1)
                ]
                mapping = source_map(db, evidence)
                for item in evidence:
                    if hashlib.sha256(item["text"].encode()).hexdigest() != item["text_hash"]:
                        raise ValueError("Official evidence content hash changed")
                    if mapping[item["chunk_id"]]["chunk_text"] != item["text"]:
                        raise ValueError("Retrieval text differs from official stored chunk")
                retrieval = {
                    "evidence": evidence,
                    "source_map": mapping,
                    "prepared_query": query.model_dump(),
                    "candidates": ranked,
                    "retrieval_trace": trace,
                    "reranking_trace": ranking,
                    "filter_trace": filtering,
                    "elapsed_ms": (time.perf_counter() - start) * 1000,
                    "runtime_device": "cpu",
                }
                write(output / "retrieval" / (case["id"] + ".json"), retrieval)
                record = {
                    **case,
                    "retrieval": retrieval,
                    "source_anchors": [
                        {
                            "chunk_id": ev["chunk_id"],
                            "asset_id": ev["asset_id"],
                            "pages": ev.get("pages"),
                            "title": ev.get("source_title"),
                            "section": ev.get("section"),
                            "text_hash": ev["text_hash"],
                            "status": "Retrieved official source; independent relevance and sufficiency labels unfilled",
                        }
                        for ev in evidence
                    ],
                }
                records.append(record)
                print(
                    json.dumps(
                        {
                            "case": case["id"],
                            "split": case["split"],
                            "accepted_chunks": len(evidence),
                            "elapsed_ms": round(retrieval["elapsed_ms"], 1),
                        }
                    ),
                    flush=True,
                )
            after = corpus_fingerprint(db, release_id)
            if before != after:
                raise ValueError("Corpus changed during preparation")
        receipt = {
            "schema": "week09_real_source_preparation_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "catalogue_sha256": hashlib.sha256(catalogue.read_bytes()).hexdigest(),
            "cases": records,
            "corpus": before,
            "corpus_unchanged": True,
            "model_config": model.to_dict(),
            "checker_config": checker.to_dict(),
            "runtime_device": "cpu",
            "torch_threads": torch.get_num_threads(),
            "provider_calls": 0,
            "labels_sent_to_retrieval": False,
            "independent_human_labels": 0,
        }
        write(output / "preparation.json", receipt)
        return receipt
    finally:
        engine.dispose()
