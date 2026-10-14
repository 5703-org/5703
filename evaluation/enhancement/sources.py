"""Freeze real retrieval and exact source-unit mappings in a read-only transaction."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import select, text

from app.modules.knowledge.models import Chunk, ProcessingRun, SourceUnit
from app.modules.knowledge.service import retrieve
from conversation.query import prepare_query
from retrieval.chat import load_policy, rerank_candidates
from retrieval.relevance import freeze_policy, screen

ROOT = Path(__file__).resolve().parents[2]


def source_map(db, evidence: list[dict]) -> dict:
    mappings = {}
    for item in evidence:
        chunk = db.get(Chunk, item["chunk_id"])
        if chunk is None or chunk.processing_id != item["processing_id"]:
            raise ValueError("Retrieval source identity differs")
        run = db.get(ProcessingRun, chunk.processing_id)
        unit_ids = sorted({span["unit_id"] for span in chunk.spans})
        units = db.scalars(select(SourceUnit).where(SourceUnit.id.in_(unit_ids))).all()
        if {u.id for u in units} != set(unit_ids):
            raise ValueError("Source mapping is incomplete")
        mappings[chunk.id] = {
            "document_version_id": run.document_version_id,
            "processing_id": chunk.processing_id,
            "asset_id": chunk.document_id,
            "chunk_text": chunk.text,
            "chunk_hash": chunk.text_hash,
            "spans": chunk.spans,
            "units": [
                {
                    "id": u.id,
                    "page": u.page,
                    "cleaned_text": u.cleaned_text,
                    "text_hash": hashlib.sha256(u.cleaned_text.encode()).hexdigest(),
                    "raw_text": u.raw_text,
                    "raw_text_hash": hashlib.sha256(u.raw_text.encode()).hexdigest(),
                }
                for u in sorted(units, key=lambda u: (u.sequence, u.id))
            ],
        }
    return mappings


def retrieve_task(db, task: dict, release_id: str) -> dict:
    """Only the user question is used to retrieve; source labels do not steer it."""
    import torch

    torch.set_num_threads(2)
    policy = load_policy(ROOT / "configs/retrieval/chat_hybrid_minilm.json")
    relevance_policy = freeze_policy(policy)
    question = task["question"]
    prepared = prepare_query(question, [])
    if prepared.needs_clarification:
        return {
            "question": question,
            "prepared_query": prepared.model_dump(),
            "candidates": [],
            "evidence": [],
            "source_map": {},
            "status": "clarification",
        }
    query = prepared.standalone_query or question
    candidates = retrieve(db, query, release_id, variant="R2", top_k=20, runtime_device="cpu")
    ranked, trace = rerank_candidates(query, candidates, policy, runtime_device="cpu")
    accepted, filtering = screen(query, ranked, relevance_policy)
    evidence = [{**row, "evidence_id": f"ev_{i:03d}"} for i, row in enumerate(accepted, 1)]
    return {
        "question": question,
        "query": query,
        "prepared_query": prepared.model_dump(),
        "candidates": ranked,
        "evidence": evidence,
        "source_map": source_map(db, evidence),
        "retrieval_policy": policy,
        "relevance_policy": relevance_policy,
        "retrieval_trace": trace,
        "filter_trace": filtering,
        "runtime_device": "cpu",
        "status": "retrieved" if evidence else "no_evidence",
    }


def corpus_fingerprint(db, release_id: str) -> dict:
    row = db.execute(
        text(
            "select count(*), min(dimension), max(dimension), md5(string_agg(chunk_id || ':' || embedding::text, '' order by chunk_id)) from release_chunks where release_id=:id"
        ),
        {"id": release_id},
    ).one()
    return {
        "release_id": release_id,
        "vectors": row[0],
        "dimension_min": row[1],
        "dimension_max": row[2],
        "vector_md5": row[3],
    }
