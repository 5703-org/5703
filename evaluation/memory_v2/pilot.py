"""Retained-family development probes; excluded from independent final claims."""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from evaluation.enhancement.protocol import digest, freeze
from evaluation.enhancement.runner import append_event, live_config, public_exposure
from evaluation.enhancement.sources import corpus_fingerprint, retrieve_task
from evaluation.memory_v2.runner import make_request, update_stop_state, resolve_frozen_credentials
from generation.service import GenerationService
from generation.types import RequestBudget
from scripts.verify.all import source_snapshot


CASES = [
    ("P01", "process", "How does ATP provide energy for cellular processes?", False),
    (
        "P02",
        "process",
        "Explain how osmosis moves water across a selectively permeable membrane.",
        False,
    ),
    ("P03", "comparison", "Compare DNA and RNA in their sugars, bases and usual structure.", False),
    (
        "P04",
        "calculation",
        "One mole of an ideal gas is at 300 K in 0.0250 m3. Given P=nRT/V and R=8.314 Pa m3 mol^-1 K^-1, calculate P in Pa and show the substitution.",
        False,
    ),
    ("P05", "comparison", "Compare DNA and RNA in their sugars, bases and usual structure.", True),
    (
        "P06",
        "process",
        "Explain the relationship between the light reactions and the Calvin cycle.",
        False,
    ),
]


def run_pilot(output: Path, *, allow_live=False):
    if not allow_live or output.exists():
        raise ValueError("A live pilot needs explicit execution and a fresh output directory")
    output.mkdir(parents=True)
    config, key = live_config()
    if "deepseek" not in (config.base_url or "").casefold():
        raise ValueError("This authorised development pilot is bound to DeepSeek")
    checker = replace(config, max_tokens=max(4096, config.max_tokens))
    checker_key = resolve_frozen_credentials(checker)
    checkpoint = {"model_config": config.to_dict(), "checker_config": checker.to_dict()}
    frozen = freeze(
        output / "pilot.json",
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "development only; retained concept families excluded from independent claims",
            "cases": CASES,
            "checkpoint": checkpoint,
            "source_hashes": source_snapshot(),
            "maximum_requests": 6,
            "maximum_external_calls": 24,
            "retries": 0,
        },
    )
    settings = Settings()
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 10})
    streaks, halted, counts = {}, None, {}
    try:
        with Session(engine) as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            release = db.execute(
                text("select release_id from active_corpus where id=1")
            ).scalar_one()
            before = corpus_fingerprint(db, release)
            for identity, kind, question, hint in CASES:
                task = {
                    "id": identity,
                    "question": question,
                    "turns": ["Give me one first hint without the final answer."],
                    "task_type": kind,
                }
                row = {
                    "id": identity,
                    "case_id": identity,
                    "study": "T" if hint else "B",
                    "turn": 1,
                    "arm": "T2" if hint else "B2",
                }
                record = {**row, "status": "not_run", "reason": halted, "outcome": None}
                if not halted:
                    started = time.monotonic()
                    retrieved = retrieve_task(db, {"question": question}, release)
                    freeze(output / "retrieval" / f"{identity}.json", retrieved)
                    request = make_request(row, task, retrieved, checkpoint, [], [])
                    events = output / "events" / f"{identity}.jsonl"
                    events.parent.mkdir(parents=True, exist_ok=True)
                    freeze(
                        output / "reservations" / f"{identity}.json",
                        {"id": identity, "pilot_sha256": digest(frozen)},
                    )
                    outcome = (
                        GenerationService(api_key=key, checker_api_key=checker_key)
                        .generate(
                            request, RequestBudget(), lambda event: append_event(events, event)
                        )
                        .to_dict()
                    )
                    record.update(
                        outcome=outcome,
                        exposure=public_exposure(outcome),
                        prior_exposure=[],
                        status="failed"
                        if outcome.get("error")
                        else (outcome.get("response") or {}).get("response_type", "failed"),
                        wall_seconds=time.monotonic() - started,
                        source_hashes=source_snapshot(),
                    )
                freeze(output / "results" / f"{identity}.json", record)
                halted = update_stop_state(record, streaks, halted)
                counts[record["status"]] = counts.get(record["status"], 0) + 1
                print(
                    f"{identity}: {record['status']} {(record.get('outcome') or {}).get('error') and record['outcome']['error'].get('code')}",
                    flush=True,
                )
            after = corpus_fingerprint(db, release)
            if before != after:
                raise ValueError("Original corpus changed")
            return freeze(
                output / "summary.json",
                {
                    "status_counts": counts,
                    "corpus": after,
                    "corpus_unchanged": True,
                    "halted": halted,
                    "independent_formal_results": False,
                },
            )
    finally:
        engine.dispose()
        key = checker_key = None
