"""Four-book development probe for frozen E0/E1 and interactive retrieval.

This module never calls a generation model. Anchor presence is a mechanical
retrieval observation, not an answer-quality or source-sufficiency label.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from .protocol import OFFICIAL_BOOKS, canonical, digest_bytes, validate_catalogue

SCHEMA = "week09_qa_retrieval_pilot_v1"
ARMS = ("E0", "E1", "interactive_first_pass")
TARGET_95_HALF_WIDTH = 0.10


def freeze(
    catalogue_path: Path,
    reserved_catalogue_path: Path,
    policy_path: Path,
    output: Path,
    *,
    root: Path,
) -> dict:
    """Freeze a tiny exposed pilot, retaining source text only in private storage."""
    if output.exists():
        raise ValueError("Preserve the existing pilot freeze")
    source_bytes = catalogue_path.read_bytes()
    reserved_bytes = reserved_catalogue_path.read_bytes()
    catalogue = json.loads(source_bytes)
    reserved = json.loads(reserved_bytes)
    validate_catalogue(catalogue)
    validate_catalogue(reserved)
    selected = [
        case
        for case in catalogue["cases"]
        if case["family"] == "textbook_qa" and case["split"] == "pilot"
    ]
    groups = {case["concept_group"] for case in selected}
    reserved_groups = {case["concept_group"] for case in reserved["cases"]}
    if len(selected) != 4 or len(groups) != 4 or groups & reserved_groups:
        raise ValueError("The four pilot knowledge concepts must be disjoint from reserved groups")
    books = {anchor["source_title"] for case in selected for anchor in case["source_anchors"]}
    if books != set(OFFICIAL_BOOKS):
        raise ValueError("The pilot must represent each of the four official books")
    for case in selected:
        if not case["required_points"] or not case["source_anchors"]:
            raise ValueError("Each question needs authored points and official anchors")
        for anchor in case["source_anchors"]:
            if digest_bytes(anchor["text"].encode("utf-8")) != anchor["text_hash"]:
                raise ValueError("Frozen source excerpt differs from its hash")
    from retrieval.chat import validate_policy
    from conversation.query import VERSION as PREPARATION_VERSION

    policy = validate_policy(json.loads(policy_path.read_text(encoding="utf-8")))
    policy_bytes = policy_path.read_bytes()
    source_paths = (
        "backend/app/modules/knowledge/service.py",
        "conversation/query.py",
        "retrieval/chat.py",
        "retrieval/relevance.py",
    )
    hashes = {relative: digest_bytes((root / relative).read_bytes()) for relative in source_paths}
    releases = {anchor["release_id"] for case in selected for anchor in case["source_anchors"]}
    if len(releases) != 1:
        raise ValueError("Pilot source anchors must share one corpus release")
    manifest = {
        "schema": SCHEMA + "_manifest",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": "development_pilot_exposed",
        "source_catalogue_sha256": digest_bytes(source_bytes),
        "reserved_catalogue_sha256": digest_bytes(reserved_bytes),
        "policy_sha256": digest_bytes(policy_bytes),
        "source_code_sha256": hashes,
        "corpus_release_id": releases.pop(),
        "arms": {
            "E0": {"retrieval": "none", "top_k": 0},
            "E1": {"retrieval": "R0_dense", "top_k": 5},
            "interactive_first_pass": {
                "retrieval": "R2_BM25_dense_RRF_then_MiniLM_then_topic_screen",
                "candidate_count": policy["candidate_count"],
                "preparation_version": PREPARATION_VERSION,
                "policy": policy,
                "scope": "fresh single-turn first pass; no inherited evidence, facet fallback, targeted supplement, generation or publication",
            },
        },
        "target_95_half_width_for_future_anchor_hit_difference": TARGET_95_HALF_WIDTH,
        "cases": [
            {
                "id": case["id"],
                "concept_group": case["concept_group"],
                "question": case["task"]["question"],
                "required_points": case["required_points"],
                "unsupported_conclusions": case["unsupported_conclusions"],
                "annotation_origin": case.get("annotation_origin"),
                "independent_reference_review": None,
                "source_anchors": case["source_anchors"],
            }
            for case in selected
        ],
        "schedule": [{"case_id": case["id"], "arm": arm} for case in selected for arm in ARMS],
        "planned": len(selected) * len(ARMS),
        "independent_semantic_labels": 0,
        "model_provider_calls": 0,
    }
    output.mkdir(parents=True)
    (output / "manifest.json").write_bytes(canonical(manifest))
    (output / "blind-human-ratings.json").write_bytes(
        canonical(
            {
                "schema": SCHEMA + "_human_ratings_blank",
                "manifest_sha256": digest_bytes((output / "manifest.json").read_bytes()),
                "ratings": [],
                "note": "No independent human source-sufficiency, point coverage or answer-quality labels have been submitted.",
            }
        )
    )
    return {
        "schema": SCHEMA + "_freeze_receipt",
        "manifest_sha256": digest_bytes((output / "manifest.json").read_bytes()),
        "case_count": len(selected),
        "book_count": len(books),
        "concept_groups": len(groups),
        "reserved_concept_overlap": 0,
        "planned": manifest["planned"],
        "arms": list(ARMS),
        "independent_semantic_labels": 0,
        "provider_calls": 0,
    }


def _hit(row: dict) -> dict:
    if hashlib.sha256(row["text"].encode("utf-8")).hexdigest() != row["text_hash"]:
        raise ValueError("Retrieved text hash differs from its source")
    return {
        "chunk_id": row["chunk_id"],
        "source_title": row["source_title"],
        "source_url": row["source_url"],
        "section": row["section"],
        "pages": row["pages"],
        "text_hash": row["text_hash"],
        "score": row.get("score"),
        "score_type": row.get("score_type"),
    }


def _one_case(db, case: dict, arm: str, manifest: dict) -> dict:
    from app.modules.knowledge.service import retrieve
    from conversation.query import prepare_query
    from retrieval.chat import rerank_candidates
    from retrieval.relevance import freeze_policy, screen

    anchor_ids = {a["chunk_id"] for a in case["source_anchors"]}
    if arm == "E0":
        return {
            "status": "completed_no_retrieval_by_definition",
            "retrieval_calls": 0,
            "hits": [],
            "anchor_hit": None,
            "semantic_ratings": None,
        }
    start = time.perf_counter()
    question = case["question"]
    trace: dict = {}
    if arm == "E1":
        rows = retrieve(
            db,
            question,
            manifest["corpus_release_id"],
            variant="R0",
            top_k=5,
            runtime_device="cpu",
        )
        trace = {"variant": "R0", "screening": "none"}
    elif arm == "interactive_first_pass":
        prepared = prepare_query(
            question, [], version=manifest["arms"][arm]["preparation_version"]
        ).model_dump()
        if prepared["needs_clarification"]:
            return {
                "status": "completed_clarification_before_retrieval",
                "retrieval_calls": 0,
                "prepared_query": prepared["standalone_query"],
                "hits": [],
                "anchor_hit": None,
                "semantic_ratings": None,
            }
        query = prepared["standalone_query"]
        policy = manifest["arms"][arm]["policy"]
        stage_trace: dict = {}
        rows = retrieve(
            db,
            query,
            manifest["corpus_release_id"],
            variant="R2",
            top_k=policy["candidate_count"],
            runtime_device="cpu",
            cache_scope="week09-qa-retrieval-pilot-readonly",
            execution_trace=stage_trace,
        )
        rows, ranking = rerank_candidates(query, rows, policy, runtime_device="cpu")
        rows, screening = screen(query, rows, freeze_policy(policy))
        trace = {
            "variant": "R2_plus_local_rerank_and_topic_screen",
            "prepared_query": query,
            "candidate_count": len(ranking["candidate_ids"]),
            "screened_out_count": len(screening["excluded"]),
            "screened_out_reasons": Counter(x["reason"] for x in screening["excluded"]),
            "retrieval_stages": stage_trace,
        }
    else:
        raise ValueError("Unknown arm")
    hit_ids = [row["chunk_id"] for row in rows]
    return {
        "status": "completed_retrieval",
        "retrieval_calls": 1,
        "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
        "hits": [_hit(row) for row in rows],
        "anchor_hit": bool(anchor_ids & set(hit_ids)),
        "anchor_rank": min(
            (i for i, chunk_id in enumerate(hit_ids, 1) if chunk_id in anchor_ids),
            default=None,
        ),
        "trace": trace,
        "semantic_ratings": None,
    }


def summarize(manifest: dict, rows: list[dict]) -> dict:
    if len(rows) != manifest["planned"]:
        raise ValueError("Every scheduled arm needs one terminal record")
    if {(r["case_id"], r["arm"]) for r in rows} != {
        (r["case_id"], r["arm"]) for r in manifest["schedule"]
    }:
        raise ValueError("Result schedule differs from freeze")
    counts = Counter(row["status"] for row in rows)
    by_case = {(row["case_id"], row["arm"]): row for row in rows}
    pairs = []
    for case in manifest["cases"]:
        e1 = by_case[(case["id"], "E1")]
        interactive = by_case[(case["id"], "interactive_first_pass")]
        if e1["status"] == interactive["status"] == "completed_retrieval":
            pairs.append(int(interactive["anchor_hit"]) - int(e1["anchor_hit"]))
    variation = None
    if len(pairs) >= 2:
        sd = statistics.stdev(pairs)
        conservative_sd = max(sd, 0.25)
        variation = {
            "paired_concept_groups": len(pairs),
            "anchor_hit_difference_interactive_minus_E1": statistics.mean(pairs),
            "paired_difference_sd": sd,
            "variance_floor_sd": 0.25,
            "exploratory_groups_for_95_half_width": max(
                16, math.ceil((1.96 * conservative_sd / TARGET_95_HALF_WIDTH) ** 2)
            ),
            "target_95_half_width": TARGET_95_HALF_WIDTH,
            "method": "normal approximation on concept-level paired anchor-hit indicators; development-only, not a formal sample-size decision",
        }
    return {
        "schema": SCHEMA + "_summary",
        "planned": manifest["planned"],
        "terminal_records": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "retrieval_completed": counts["completed_retrieval"],
        "paired_anchor_hit_variation": variation,
        "answer_correctness": None,
        "source_sufficiency": None,
        "required_point_coverage": None,
        "citation_support": None,
        "independent_human_ratings": 0,
        "provider_calls": 0,
        "interpretation": "Anchor presence and rank are mechanical. No answer was generated or independently graded.",
    }


def execute(study: Path, dotenv_path: Path, output: Path) -> dict:
    """Run all arms on an explicitly supplied isolated PostgreSQL stage."""
    if output.exists():
        raise ValueError("Preserve prior terminal results")
    from dotenv import dotenv_values
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    manifest_bytes = (study / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema") != SCHEMA + "_manifest":
        raise ValueError("Unsupported QA retrieval pilot freeze")
    root = Path(__file__).resolve().parents[2]
    for relative, expected in manifest["source_code_sha256"].items():
        if digest_bytes((root / relative).read_bytes()) != expected:
            raise ValueError("Current retrieval source differs from the pilot freeze")
    if (
        digest_bytes((root / "configs/retrieval/chat_hybrid_minilm.json").read_bytes())
        != manifest["policy_sha256"]
    ):
        raise ValueError("Current interactive policy differs from the pilot freeze")
    url = dotenv_values(dotenv_path).get("DATABASE_URL")
    if not isinstance(url, str) or not url.startswith("postgresql+"):
        raise ValueError("An isolated PostgreSQL stage .env is required")
    # This runner intentionally has no fallback to the main development URL.
    if "127.0.0.1:16547" not in url and "localhost:16547" not in url:
        raise ValueError("This frozen pilot requires the isolated 16547 stage")
    rows = []
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5})
    try:
        with Session(engine) as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            if db.scalar(text("SHOW transaction_read_only")) != "on":
                raise ValueError("Stage transaction is not read-only")
            active = db.scalar(text("SELECT release_id FROM active_corpus WHERE id=1"))
            if active != manifest["corpus_release_id"]:
                raise ValueError("Stage corpus release differs from pilot freeze")
            vector_count = db.scalar(
                text("SELECT count(*) FROM release_chunks WHERE release_id=:r"),
                {"r": active},
            )
            dimensions = [
                row[0]
                for row in db.execute(
                    text(
                        "SELECT DISTINCT vector_dims(embedding) FROM release_chunks WHERE release_id=:r"
                    ),
                    {"r": active},
                )
            ]
            if vector_count != 10594 or dimensions != [384]:
                raise ValueError("Stage vector identity differs from the released four-book corpus")
            for case in manifest["cases"]:
                for anchor in case["source_anchors"]:
                    observed = db.execute(
                        text("""
                        SELECT c.text, c.text_hash, c.pages, c.section, d.title,
                               d.source_url, dv.raw_hash
                        FROM release_chunks rc JOIN chunks c ON c.id=rc.chunk_id
                        JOIN documents d ON d.id=c.document_id
                        JOIN processing_runs pr ON pr.id=c.processing_id
                        JOIN document_versions dv ON dv.id=pr.document_version_id
                        WHERE rc.release_id=:r AND rc.chunk_id=:c
                        """),
                        {"r": active, "c": anchor["chunk_id"]},
                    ).one_or_none()
                    if observed is None or (
                        observed.text != anchor["text"]
                        or observed.text_hash != anchor["text_hash"]
                        or list(observed.pages) != anchor["pages"]
                        or observed.section != anchor["section"]
                        or observed.title != anchor["source_title"]
                        or observed.source_url != anchor["source_url"]
                        or observed.raw_hash != anchor["original_sha256"]
                    ):
                        raise ValueError("Stage official source anchor differs from freeze")
            for item in manifest["schedule"]:
                case = next(c for c in manifest["cases"] if c["id"] == item["case_id"])
                try:
                    observation = _one_case(db, case, item["arm"], manifest)
                except Exception as exc:  # Preserve the failed scheduled case.
                    observation = {
                        "status": "execution_error",
                        "error_type": type(exc).__name__,
                        "semantic_ratings": None,
                    }
                rows.append({**item, **observation})
            db.rollback()
    finally:
        engine.dispose()
    result = {
        "schema": SCHEMA + "_results",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": digest_bytes(manifest_bytes),
        "database": "isolated_published_stage_port_16547",
        "database_read_only": True,
        "release_id": manifest["corpus_release_id"],
        "vector_count": vector_count,
        "vector_dimension": 384,
        "source_anchors_verified": sum(len(c["source_anchors"]) for c in manifest["cases"]),
        "rows": rows,
        "summary": summarize(manifest, rows),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(result))
    return {
        "result_sha256": digest_bytes(output.read_bytes()),
        **result["summary"],
        "source_anchors_verified": result["source_anchors_verified"],
        "database_read_only": True,
        "release_id": result["release_id"],
        "vector_count": vector_count,
        "vector_dimension": 384,
    }
