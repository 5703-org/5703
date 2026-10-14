"""Read-only real CPU retrieval followed by an explicit executable study freeze."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import time

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.model_settings.models import ModelConfiguration
from app.modules.model_settings.service import as_model_config, resolve_active_checker_model_config
from evaluation.enhancement.protocol import digest, freeze
from evaluation.enhancement.sources import corpus_fingerprint, retrieve_task
from evaluation.memory_v2.catalogue import tasks
from evaluation.memory_v2.memory_catalogue import trajectories, extraction_cases, gating_pairs
from evaluation.memory_v2.protocol import freeze_study
from evaluation.memory_v2.runner import load
from scripts.verify.all import ROOT, source_snapshot


def prepare(output: Path, *, task_rows=None):
    """Retrieve only public questions; never guide retrieval with reference labels."""
    if output.exists():
        raise ValueError("Preserve prior preparation; select a new directory")
    output.mkdir(parents=True)
    rows = tasks() if task_rows is None else task_rows
    freeze(output / "private-tasks.json", {"tasks": rows, "author": "Codex", "human_ratings": 0})
    freeze(
        output / "private-trajectories.json",
        {
            "trajectories": trajectories(),
            "extraction_cases": extraction_cases(),
            "gating_pairs": gating_pairs(),
        },
    )
    settings = Settings()
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 10})
    before = source_snapshot()
    retrieval_hashes = {}
    try:
        with Session(engine) as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            release = db.execute(
                text("select release_id from active_corpus where id=1")
            ).scalar_one()
            corpus = corpus_fingerprint(db, release)
            for task in rows:
                started = time.monotonic()
                result = {
                    "id": task["id"],
                    **retrieve_task(db, {"question": task["question"]}, release),
                }
                result["retrieval_seconds"] = time.monotonic() - started
                freeze(output / "retrieval" / (task["id"] + ".json"), result)
                retrieval_hashes[task["id"]] = digest(result)
                print(
                    f"{task['id']}: {len(result['evidence'])} accepted real CPU passages",
                    flush=True,
                )
            if corpus != corpus_fingerprint(db, release):
                raise ValueError("Original corpus changed during retrieval")
            return freeze(
                output / "preparation.json",
                {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "corpus": corpus,
                    "retrieval_hashes": retrieval_hashes,
                    "source_hashes": before,
                    "source_unchanged": before == source_snapshot(),
                    "generator_calls": 0,
                    "references_sent_to_retrieval": False,
                },
            )
    finally:
        engine.dispose()


def finalize(source: Path):
    """Freeze only after code, pilot review and independent catalogue checks finish."""
    preparation = load(source / "preparation.json")
    task_rows = load(source / "private-tasks.json")["tasks"]
    memory_inputs = load(source / "private-trajectories.json")
    learner_rows = memory_inputs["trajectories"]
    if (
        task_rows != tasks()
        or learner_rows != trajectories()
        or memory_inputs["extraction_cases"] != extraction_cases()
        or memory_inputs["gating_pairs"] != gating_pairs()
    ):
        raise ValueError("Authored inputs changed after real retrieval preparation")
    for identity, expected in preparation["retrieval_hashes"].items():
        if digest(load(source / "retrieval" / (identity + ".json"))) != expected:
            raise ValueError("Prepared retrieval identity changed")
    current = source_snapshot()
    # UI/test evolution can continue after retrieval; executable retrieval dependencies cannot.
    relevant = (
        "retrieval/",
        "conversation/",
        "backend/app/modules/knowledge/",
        "evaluation/enhancement/sources.py",
        "configs/retrieval/",
    )
    old_retrieval = {
        k: v for k, v in preparation["source_hashes"].items() if k.startswith(relevant)
    }
    new_retrieval = {k: v for k, v in current.items() if k.startswith(relevant)}
    if old_retrieval != new_retrieval:
        raise ValueError("Retrieval implementation changed; prepare a new source version")
    settings = Settings()
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 10})
    try:
        with Session(engine) as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            active = db.execute(
                text(
                    "select workspace_id,configuration_id from active_model_configurations where configuration_id is not null order by workspace_id"
                )
            ).one()
            stored = db.scalar(
                select(ModelConfiguration).where(ModelConfiguration.id == active.configuration_id)
            )
            model = as_model_config(stored)
            checker = resolve_active_checker_model_config(
                db, settings, active.workspace_id
            ) or replace(model, max_tokens=max(4096, model.max_tokens))
            model.validate()
            checker.validate()
            if model.provider == "mock" or checker.provider == "mock":
                raise ValueError("Formal studies require real answer and checker configurations")
            if corpus_fingerprint(db, preparation["corpus"]["release_id"]) != preparation["corpus"]:
                raise ValueError("Prepared real corpus identity changed")
            paths = sorted((ROOT / "docs/execution").glob("week08-memory-v2-protocol*.md"))
            if not paths:
                raise ValueError("Registered protocol is unavailable")
            hashes = {
                p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in paths
            }
            for path in paths:
                target = source / "protocol" / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and target.read_bytes() != path.read_bytes():
                    raise ValueError("Never overwrite a registered protocol copy")
                if not target.exists():
                    target.write_bytes(path.read_bytes())
            return freeze_study(
                source / "study.json",
                task_rows,
                learner_rows,
                {
                    "source_hashes": current,
                    "protocol_hashes": hashes,
                    "model_config": model.to_dict(),
                    "checker_config": checker.to_dict(),
                    "corpus": preparation["corpus"],
                    "retrieval_hashes": preparation["retrieval_hashes"],
                    "memory_extraction_sha256": digest(memory_inputs["extraction_cases"]),
                    "memory_gating_sha256": digest(memory_inputs["gating_pairs"]),
                },
            )
    finally:
        engine.dispose()
