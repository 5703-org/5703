"""Frozen M0–M4 preparation and answer execution in a distinct disposable DB.

Typed extraction is performed once per authored input, then the exact candidates
feed one writer state read by both M3 and M4. M2 invokes the original production
extractor/worker and reader explicitly. Every reservation survives an exception.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import timedelta
import json
import os
from pathlib import Path
import time
from uuid import uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import utcnow
from app.modules.answering.models import Attempt, Job, Message
from app.modules.answering.service import ExecutionCancelled
from app.modules.learning_state import memory, memory_v2
from app.modules.learning_state.models import MemoryEntry, MemoryWriteEvent
from contracts.learning import MemorySettingsUpdate
from evaluation.enhancement.memory_study import (
    Structured,
    update_summary,
    validate_target,
    attempt_accounting,
)
from evaluation.enhancement.protocol import digest, freeze
from evaluation.enhancement.runner import append_event, public_exposure, recovered_attempts
from evaluation.memory_v2.memory_catalogue import VERSION
from evaluation.memory_v2.runner import (
    load,
    make_request,
    now,
    resolve_frozen_credentials,
    update_stop_state,
)
from generation.service import GenerationService
from generation.token_counting import TokenCounter
from generation.types import ModelConfig, RequestBudget
from personalisation.compiler import compile_profile
from personalisation.memory_extraction import extract_operations
from scripts.verify.all import source_snapshot


def assert_sources(manifest):
    if source_snapshot() != manifest["checkpoint"]["source_hashes"]:
        raise ValueError("Memory study executable sources changed")


def replay_prior_stops(output, *, include_states=False):
    streaks, halted = {}, None
    for path in sorted((output / "extraction").glob("*.json")):
        halted = update_stop_state({"outcome": load(path)}, streaks, halted)
    if include_states:
        for path in sorted((output / "states").glob("*.json")):
            for outcome in load(path).get("provider_outcomes", []):
                halted = update_stop_state({"outcome": outcome}, streaks, halted)
    return streaks, halted


def read_inputs(source):
    manifest = load(source / "study.json")
    memory_inputs = load(source / "private-trajectories.json")
    trajectories = memory_inputs["trajectories"]
    tasks = load(source / "private-tasks.json")["tasks"]
    if (
        digest(trajectories) != manifest["trajectories_sha256"]
        or digest(tasks) != manifest["tasks_sha256"]
    ):
        raise ValueError("Memory catalogue differs from study freeze")
    if len(trajectories) != 12 or any(
        len(t["probes"]) != 3 or len(t["statements"]) != 2 for t in trajectories
    ):
        raise ValueError("Memory inventory differs from 12 trajectories / 36 probes")
    for key, expected_count, checkpoint_key in (
        ("extraction_cases", 24, "memory_extraction_sha256"),
        ("gating_pairs", 12, "memory_gating_sha256"),
    ):
        rows = memory_inputs.get(key)
        if (
            not isinstance(rows, list)
            or len(rows) != expected_count
            or len({row["id"] for row in rows}) != expected_count
            or digest(rows) != manifest["checkpoint"].get(checkpoint_key)
        ):
            raise ValueError("Frozen memory " + key + " differ from the study checkpoint")
    assert_sources(manifest)
    return manifest, trajectories, {t["id"]: t for t in tasks}


def typed_candidates(source, output, *, allow_live=False):
    """Exactly 24 scheduled extraction inputs, including gated zero-call inputs."""
    if not allow_live:
        raise ValueError("Explicit allow_live is required")
    manifest, trajectories, _ = read_inputs(source)
    config = ModelConfig.from_dict(manifest["checkpoint"]["model_config"])
    secret = resolve_frozen_credentials(config)
    freeze(
        output / "extraction-manifest.json",
        {
            "version": VERSION,
            "study_hash": digest(manifest),
            "configuration": config.to_dict(),
            "planned": 24,
        },
    )
    result = []
    halted, streaks = None, {}
    for trajectory in trajectories:
        for index, message in enumerate(trajectory["statements"]):
            identity = f"{trajectory['id']}-E{index + 1}"
            destination = output / "extraction" / f"{identity}.json"
            reservation = output / "reservations" / f"{identity}.json"
            events = output / "events" / f"{identity}.jsonl"
            if destination.exists():
                record = load(destination)
                if record["source_hash"] != digest(message):
                    raise ValueError("Frozen extraction input changed")
            else:
                record = {
                    "id": identity,
                    "source_hash": digest(message),
                    "configuration": config.to_dict(),
                    "operations": [],
                    "error": None,
                }
                if reservation.exists():
                    record["error"] = {"code": "UNCERTAIN_PRIOR_EXTRACTION"}
                    record["recovered_attempts"] = recovered_attempts(events)
                elif halted:
                    record["error"] = {"code": "NOT_RUN_PROVIDER_UNAVAILABLE"}
                else:
                    assert_sources(manifest)
                    freeze(
                        reservation,
                        {
                            "id": identity,
                            "source_hash": digest(message),
                            "study_hash": digest(manifest),
                            "reserved_at": now(),
                        },
                    )
                    events.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        record.update(
                            extract_operations(
                                message,
                                config,
                                on_attempt=lambda event: append_event(events, event),
                                api_key=secret,
                            )
                        )
                    except Exception as exc:
                        record["error"] = {
                            "code": "EXTRACTION_EXCEPTION",
                            "exception_type": type(exc).__name__,
                        }
                        record["recovered_attempts"] = recovered_attempts(events)
                    assert_sources(manifest)
                    record["attempts"] = recovered_attempts(events)
                freeze(destination, {**record, "completed_at": now(), "human_rating": None})
            result.append(record)
            halted = update_stop_state({"outcome": record}, streaks, halted)
    secret = None
    summary = extraction_metrics(
        result, load(source / "private-trajectories.json")["extraction_cases"]
    )
    summary["errors"] = sum(bool(r["error"]) for r in result)
    freeze(output / "extraction-summary.json", summary)
    return summary


class StatePair:
    """One legacy writer and one shared typed writer for a synthetic trajectory."""

    def __init__(self, engine, settings, config, identity):
        self.engine, self.settings, self.config = engine, settings, config
        self.db = sessionmaker(bind=engine, expire_on_commit=False)
        self.legacy = Structured(engine, settings, config, identity + ":M2")
        self.typed = Structured(engine, settings, config, identity + ":M3-M4")
        self.staged = []
        self.sequence = {"M2": 0, "typed": 0}
        self.operations = []
        self.provider_outcomes = []

    def create_source(self, arm, value):
        owner = self.legacy if arm == "M2" else self.typed
        self.sequence[arm] += 1
        with self.db() as db:
            row = Message(
                session_id=owner.session_id,
                sequence=self.sequence[arm],
                role="user",
                content=value,
                state="complete",
            )
            db.add(row)
            db.flush()
            if arm == "M2":
                memory.enqueue_extraction(
                    db,
                    owner.owner_id,
                    row,
                    self.config.to_dict(),
                    True,
                    policy_version="explicit_learning_memory_v1",
                )
                db.flush()
                job = db.scalar(
                    select(Job).where(
                        Job.owner_id == owner.owner_id,
                        Job.kind == "memory",
                        Job.payload["source_message_id"].as_string() == row.id,
                    )
                )
                target = job.id if job else None
            else:
                target = memory_v2.source_event(db, owner.owner_id, row.id).id
            db.commit()
            return {"arm": arm, "target": target, "source_message_id": row.id}

    def complete(self, staged, candidates):
        if not staged["target"]:
            return
        if staged["arm"] == "M2":
            with self.db() as db:
                job = db.get(Job, staged["target"])
                if job.state == "cancelled":
                    self.operations.append({**staged, "status": "cancelled"})
                    return
                token = str(uuid4())
                job.state, job.execution_token = "running", token
                db.commit()
            try:
                memory.execute_memory(self.engine, self.settings, staged["target"], token)
            except ExecutionCancelled:
                self.operations.append({**staged, "status": "cancelled"})
                return
            with self.db() as db:
                job = db.get(Job, staged["target"])
                self.operations.append(
                    {
                        **staged,
                        "status": job.state,
                        "error": job.error,
                        "saved": job.payload.get("saved", []),
                    }
                )
                attempts = [
                    {**a.payload, "provider": self.config.provider}
                    for a in db.scalars(
                        select(Attempt).where(Attempt.job_id == job.id).order_by(Attempt.sequence)
                    )
                    if a.payload.get("phase") in {"finish", "finished"}
                ]
                if attempts and job.error:
                    attempts[-1]["error"] = job.error
                self.provider_outcomes.append(
                    {"error": job.error, "provider": self.config.provider, "attempts": attempts}
                )
        else:
            with self.db() as db:
                event = db.get(MemoryWriteEvent, staged["target"])
                if candidates.get("error"):
                    event.status, event.error = "failed", candidates["error"]
                    receipts = []
                else:
                    receipts = memory_v2.apply_operations(
                        db, self.typed.owner_id, event, candidates["operations"]
                    )
                db.commit()
                self.operations.append(
                    {
                        **staged,
                        "status": event.status,
                        "receipts": receipts,
                        "candidate_hash": digest(candidates),
                    }
                )

    def statement(self, value, candidates, *, delayed=False, enabled=True):
        if not enabled:
            return
        for arm in ("M2", "typed"):
            pending = self.create_source(arm, value)
            if delayed:
                self.staged.append((pending, candidates))
            else:
                self.complete(pending, candidates)

    def control(self, event):
        if event["kind"] == "complete_staged":
            for pending, candidates in self.staged:
                self.complete(pending, candidates)
            self.staged.clear()
            return
        for owner in (self.legacy, self.typed):
            with self.db() as db:
                if event["kind"] == "enabled":
                    state = memory.settings_for(db, owner.owner_id)
                    memory.update_settings(
                        db,
                        owner.owner_id,
                        MemorySettingsUpdate(enabled=event["value"], version=state.version),
                    )
                    continue
                rows = list(
                    db.scalars(
                        select(MemoryEntry).where(
                            MemoryEntry.owner_id == owner.owner_id, MemoryEntry.status == "active"
                        )
                    )
                )
                affected = []
                for row in rows:
                    # Historical attributes can vary; record exact targeting decisions.
                    from personalisation.memory_v2 import infer_field

                    recognized = row.field_key or infer_field(row.content or "")
                    if recognized != event["field"]:
                        continue
                    affected.append(row.id)
                    if event["kind"] == "delete":
                        memory.delete_entry(db, owner.owner_id, row.id, row.version)
                    elif event["kind"] == "expire":
                        # This fixture advances the recorded expiry, exercising the
                        # actual reader's wall-clock guard without waiting a day.
                        row.expires_at = utcnow() - timedelta(seconds=1)
                db.commit()
                self.operations.append(
                    {
                        "arm": "M2" if owner is self.legacy else "typed",
                        "control": event,
                        "affected_entry_ids": affected,
                    }
                )

    def contexts(self, question, profile, use_profile):
        result = {}
        for arm, owner, policy in (
            ("M2", self.legacy, "explicit_learning_memory_v1"),
            ("M3", self.typed, "typed_memory_v2"),
            ("M4", self.typed, "query_conditioned_memory_v2"),
        ):
            with self.db() as db:
                snap = memory.freeze_memory(
                    db,
                    owner.owner_id,
                    question,
                    use_profile,
                    policy_version=policy,
                    profile=profile,
                    counter=TokenCounter(self.config),
                )
                context = memory.read_snapshot(db, owner.owner_id, snap.id) if snap else None
                rows = [
                    memory.entry_out(r)
                    for r in db.scalars(
                        select(MemoryEntry).where(MemoryEntry.owner_id == owner.owner_id)
                    )
                ]
                db.commit()
                result[arm] = {
                    "memory_context": context,
                    "summary": None,
                    "writer_entries": rows,
                    "operations": list(self.operations),
                    "owner_id": owner.owner_id,
                }
        if digest(result["M3"]["writer_entries"]) != digest(result["M4"]["writer_entries"]):
            raise ValueError("M3 and M4 no longer share identical writer state")
        return result


def state_checks(state, expected):
    context = state.get("memory_context") or {}
    entries = context.get("entries", [])
    if context.get("version") == "explicit_learning_memory_v1":
        return [
            {
                "name": "typed_field_scoring",
                "passed": None,
                "status": "not_applicable",
                "reason": "Historical M2 stores a hashed free-form attribute; no typed-field reconstruction is invented.",
            },
            {
                "name": "source_versions_present",
                "passed": all(
                    e.get("id") and e.get("version") and e.get("source_message_id") for e in entries
                ),
            },
        ]
    fields = {e.get("field_key") for e in entries}
    checks = []
    for key in expected.get("selected_fields", []):
        checks.append({"name": "selected:" + key, "passed": key in fields})
    for key in expected.get("excluded_fields", []):
        checks.append({"name": "excluded:" + key, "passed": key not in fields})
    for key, value in expected.get("exact_values", {}).items():
        checks.append(
            {
                "name": "exact_value:" + key,
                "passed": any(
                    e.get("field_key") == key and e.get("content") == value for e in entries
                ),
            }
        )
    checks.append(
        {
            "name": "source_versions_present",
            "passed": all(
                e.get("id") and e.get("version") and e.get("source_message_id") for e in entries
            ),
        }
    )
    return checks


def extraction_metrics(records, expected_cases):
    """Exact authored-label agreement; failures remain in the 24-input denominator."""
    indexed = {row["id"]: row for row in records}
    if len(indexed) != len(records) or set(indexed) - {row["id"] for row in expected_cases}:
        raise ValueError("Duplicate or unknown extraction result")
    scored = []
    for case in expected_cases:
        record = indexed.get(case["id"])
        operations = (record or {}).get("operations", [])
        actual = {
            (r["operation"], r["field_key"], r["scope"])
            for r in operations
            if r["operation"] != "NO_OP"
        }
        expected = {
            (r["operation"], r["field_key"], r["scope"]) for r in case["expected_operations"]
        }
        valid = record is not None and not record.get("error")
        scored.append(
            {
                "id": case["id"],
                "recorded": record is not None,
                "valid": valid,
                "exact_operations": valid and actual == expected,
                "true_positive": len(actual & expected) if valid else 0,
                "false_positive": len(actual - expected) if valid else 0,
                "false_negative": len(expected - actual) if valid else len(expected),
                "source_supported": valid
                and all(
                    r.get("source_quote") in case["text"]
                    and r.get("content") == r.get("source_quote")
                    for r in operations
                ),
            }
        )
    return {
        "planned": len(expected_cases),
        "recorded": len(records),
        "exact_operations": sum(r["exact_operations"] for r in scored),
        "records": scored,
        "scope": "Exact agreement with Codex-authored operation/field/scope labels and source substrings; independent human annotations remain blank",
    }


def prepare_states(source, output, *, database_env, allow_live=False):
    if not allow_live:
        raise ValueError("Explicit allow_live is required")
    manifest, trajectories, tasks = read_inputs(source)
    settings = Settings()
    target = os.environ.get(database_env, "")
    name = validate_target(target, settings.database_url)
    config = ModelConfig.from_dict(manifest["checkpoint"]["model_config"])
    secret = resolve_frozen_credentials(config)
    worker_config = replace(
        config, configuration_id="memory-study-v2:" + digest(config.to_dict())[:24]
    )
    worker_settings = settings.model_copy(update={"database_url": target, "llm_api_key": secret})
    engine = create_engine(target, connect_args={"connect_timeout": 10})
    manifest_path = output / "state-manifest.json"
    try:
        with engine.connect() as lock:
            if (
                lock.execute(text("select current_database()")).scalar_one() != name
                or not lock.execute(text("select pg_try_advisory_lock(20260921, 301)")).scalar_one()
            ):
                raise ValueError("Study DB identity or exclusive lock failed")
            if (
                not manifest_path.exists()
                and lock.execute(text("select count(*) from users")).scalar_one() != 0
            ):
                raise ValueError("First preparation requires an empty migrated study database")
            freeze(
                manifest_path,
                {
                    "version": VERSION,
                    "study_hash": digest(manifest),
                    "database_name": name,
                    "worker_alias": worker_config.to_dict(),
                    "credential_policy": "in-process only; no credential rows copied",
                },
            )
            streaks, halted = replay_prior_stops(output)
            for trajectory in trajectories:
                identity = trajectory["id"]
                destination = output / "states" / f"{identity}.json"
                if destination.exists():
                    for outcome in load(destination).get("provider_outcomes", []):
                        halted = update_stop_state({"outcome": outcome}, streaks, halted)
                    continue
                if halted:
                    freeze(
                        destination,
                        {
                            "id": identity,
                            "status": "not_run",
                            "error": {"code": halted},
                            "probes": [],
                            "provider_outcomes": [],
                        },
                    )
                    continue
                reservation = output / "reservations" / f"{identity}-state.json"
                if reservation.exists():
                    freeze(
                        destination,
                        {
                            "id": identity,
                            "status": "failed",
                            "error": {"code": "UNCERTAIN_STATE_PREPARATION"},
                            "probes": [],
                        },
                    )
                    continue
                assert_sources(manifest)
                freeze(
                    reservation,
                    {"id": identity, "reserved_at": now(), "study_hash": digest(manifest)},
                )
                event_path = output / "events" / f"{identity}-state.jsonl"
                event_path.parent.mkdir(parents=True, exist_ok=True)
                pair = None
                record = {
                    "id": identity,
                    "status": "complete",
                    "probes": [],
                    "error": None,
                    "provider_outcomes": [],
                }
                try:
                    pair = StatePair(engine, worker_settings, worker_config, identity)
                    freeze(
                        output / "identities" / f"{identity}.json",
                        {"legacy_owner": pair.legacy.owner_id, "typed_owner": pair.typed.owner_id},
                    )
                    summary, enabled = "", True
                    observed = 0
                    for turn, probe in enumerate(trajectory["probes"], 1):
                        assert_sources(manifest)
                        for event in probe["events"]:
                            if event["kind"] in {"statement", "stage"}:
                                value = trajectory["statements"][event["index"]]
                                candidates = load(
                                    output / "extraction" / f"{identity}-E{event['index'] + 1}.json"
                                )
                                pair.statement(
                                    value,
                                    candidates,
                                    delayed=event["kind"] == "stage",
                                    enabled=enabled and probe["use_profile"],
                                )
                                for outcome in pair.provider_outcomes[observed:]:
                                    record["provider_outcomes"].append(outcome)
                                    halted = update_stop_state(
                                        {"outcome": outcome}, streaks, halted
                                    )
                                observed = len(pair.provider_outcomes)
                                if halted:
                                    raise RuntimeError("Provider stopping rule")
                                if enabled and probe["use_profile"]:
                                    result = update_summary(
                                        summary,
                                        value,
                                        config,
                                        secret,
                                        lambda data: append_event(event_path, data),
                                    )
                                    summary = result["summary"]
                                    record.setdefault("summary_updates", []).append(result)
                                    outcome = {
                                        "error": result.get("error"),
                                        "provider": config.provider,
                                        "attempts": [
                                            {
                                                "provider": config.provider,
                                                "error": result.get("error"),
                                                "usage": usage,
                                            }
                                            for usage in result.get("usage", [])
                                        ],
                                    }
                                    record["provider_outcomes"].append(outcome)
                                    halted = update_stop_state(
                                        {"outcome": outcome}, streaks, halted
                                    )
                                    if halted:
                                        raise RuntimeError("Provider stopping rule")
                            else:
                                pair.control(event)
                                for outcome in pair.provider_outcomes[observed:]:
                                    record["provider_outcomes"].append(outcome)
                                    halted = update_stop_state(
                                        {"outcome": outcome}, streaks, halted
                                    )
                                observed = len(pair.provider_outcomes)
                                if halted:
                                    raise RuntimeError("Provider stopping rule")
                                if event["kind"] == "enabled":
                                    enabled = event["value"]
                                elif event["kind"] in {"delete", "expire"}:
                                    summary = ""
                        question = probe["prefix"] + tasks[probe["question_id"]]["question"]
                        profile = compile_profile(
                            trajectory["profile"], probe["use_profile"], question
                        )
                        states = pair.contexts(question, profile, probe["use_profile"])
                        states["M0"] = {"memory_context": None, "summary": None}
                        states["M1"] = {
                            "memory_context": None,
                            "summary": summary if enabled and probe["use_profile"] else None,
                            "control_policy": "delete/expiry clear summary; disabled/profile-off suppress update and use",
                        }
                        record["probes"].append(
                            {
                                "turn": turn,
                                "question_id": probe["question_id"],
                                "question": question,
                                "profile": profile,
                                "states": states,
                                "expected": probe["expected"],
                                "checks": {
                                    arm: state_checks(states[arm], probe["expected"])
                                    for arm in ("M2", "M3", "M4")
                                },
                            }
                        )
                        assert_sources(manifest)
                except Exception as exc:
                    record.update(
                        status="failed",
                        error={
                            "code": "STATE_PREPARATION_EXCEPTION",
                            "exception_type": type(exc).__name__,
                        },
                    )
                record["accounting"] = {
                    "summary": attempt_accounting(event_path),
                    "M2": attempt_accounting(
                        output / "events" / f"{identity}-legacy.jsonl", engine, pair.legacy.owner_id
                    )
                    if pair
                    else None,
                }
                record["source_unchanged_after"] = (
                    source_snapshot() == manifest["checkpoint"]["source_hashes"]
                )
                if not record["source_unchanged_after"]:
                    record.update(
                        status="failed", error={"code": "SOURCE_CHANGED_DURING_PREPARATION"}
                    )
                freeze(destination, {**record, "completed_at": now(), "human_rating": None})
                if not record["source_unchanged_after"]:
                    raise ValueError("Source changed; further state preparation stopped")
    finally:
        secret = None
        engine.dispose()


def run(source, output, *, allow_live=False):
    if not allow_live:
        raise ValueError("Explicit allow_live is required")
    manifest, trajectories, tasks = read_inputs(source)
    answer_key = resolve_frozen_credentials(
        ModelConfig.from_dict(manifest["checkpoint"]["model_config"])
    )
    checker_key = resolve_frozen_credentials(
        ModelConfig.from_dict(manifest["checkpoint"]["checker_config"])
    )
    indexed = {t["id"]: t for t in trajectories}
    freeze(
        output / "answer-manifest.json",
        {"study_hash": digest(manifest), "version": VERSION, "planned": 180, "human_ratings": 0},
    )
    streaks, halted = replay_prior_stops(output, include_states=True)
    for row in manifest["schedule"]:
        if row["study"] != "M":
            continue
        identity = row["id"]
        destination = output / "results" / f"{identity}.json"
        if destination.exists():
            halted = update_stop_state(load(destination), streaks, halted)
            continue
        assert_sources(manifest)
        bank = load(output / "states" / f"{row['case_id']}.json")
        probe = indexed[row["case_id"]]["probes"][row["turn"] - 1]
        material = load(source / "retrieval" / f"{probe['question_id']}.json")
        if digest(material) != manifest["checkpoint"]["retrieval_hashes"][probe["question_id"]]:
            raise ValueError("Matched retrieval changed")
        events = output / "events" / f"{identity}.jsonl"
        reservation = output / "reservations" / f"{identity}.json"
        record = {
            **row,
            "outcome": None,
            "exposure": None,
            "prior_exposure": [],
            "exact_retrieval_hash": digest(material),
            "memory_expected": probe["expected"],
            "memory_state_trace": None,
        }
        if reservation.exists():
            record.update(
                status="failed",
                reason="uncertain_external_completion_preserved",
                recovered_attempts=recovered_attempts(events),
            )
        elif halted or bank["status"] != "complete":
            record.update(status="not_run", reason=halted or "state_preparation_failed")
        else:
            prepared = bank["probes"][row["turn"] - 1]
            state = prepared["states"][row["arm"]]
            request = make_request(
                row, tasks[probe["question_id"]], material, manifest["checkpoint"], [], []
            )
            request.question = prepared["question"]
            request.profile, request.summary, request.memory_context = (
                prepared["profile"],
                state.get("summary"),
                state.get("memory_context"),
            )
            request.teaching_context["current_problem"] = request.question
            record["memory_state_trace"] = state
            freeze(
                reservation,
                {
                    "id": identity,
                    "study_hash": digest(manifest),
                    "input_hash": digest(asdict(request)),
                    "reserved_at": now(),
                },
            )
            events.parent.mkdir(parents=True, exist_ok=True)
            started = time.monotonic()
            try:
                outcome = (
                    GenerationService(api_key=answer_key, checker_api_key=checker_key)
                    .generate(request, RequestBudget(), lambda event: append_event(events, event))
                    .to_dict()
                )
            except Exception as exc:
                outcome = {
                    "response": None,
                    "error": {
                        "code": "MEMORY_ANSWER_EXCEPTION",
                        "exception_type": type(exc).__name__,
                    },
                    "attempts": recovered_attempts(events),
                }
            if source_snapshot() != manifest["checkpoint"]["source_hashes"]:
                outcome.update(response=None, error={"code": "SOURCE_CHANGED_DURING_ANSWER"})
                halted = "source_changed"
            error = outcome.get("error") or {}
            record.update(
                outcome=outcome,
                exposure=public_exposure(outcome),
                status="failed"
                if error
                else (outcome.get("response") or {}).get("response_type", "failed"),
                wall_seconds=time.monotonic() - started,
            )
        halted = update_stop_state(record, streaks, halted)
        freeze(destination, {**record, "completed_at": now(), "human_rating": None})
        print(json.dumps({"id": identity, "status": record["status"]}), flush=True)
    answer_key = checker_key = None
    return {
        "planned": 180,
        "recorded": len(list((output / "results").glob("*-M[0-4]-*.json"))),
        "halted": halted,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("extract", "prepare", "run", "gates"))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--database-env", default="MEMORY_V2_STUDY_DATABASE_URL")
    parser.add_argument("--allow-live", action="store_true")
    args = parser.parse_args()
    if args.command == "gates":
        from evaluation.memory_v2.memory_gates import execute

        manifest, _, _ = read_inputs(args.source)
        settings = Settings()
        target = os.environ.get(args.database_env, "")
        name = validate_target(target, settings.database_url)
        engine = create_engine(target, connect_args={"connect_timeout": 10})
        try:
            with engine.connect() as lock:
                if (
                    lock.execute(text("select current_database()")).scalar_one() != name
                    or not lock.execute(
                        text("select pg_try_advisory_lock(20260921, 301)")
                    ).scalar_one()
                ):
                    raise ValueError("Study DB identity or lock failed")
                result = execute(
                    engine,
                    settings,
                    ModelConfig.from_dict(manifest["checkpoint"]["model_config"]),
                    args.output / "observation-gates.json",
                    cases=load(args.source / "private-trajectories.json")["gating_pairs"],
                )
                assert_sources(manifest)
        finally:
            engine.dispose()
    elif args.command == "extract":
        result = typed_candidates(args.source, args.output, allow_live=args.allow_live)
    elif args.command == "prepare":
        result = prepare_states(
            args.source, args.output, database_env=args.database_env, allow_live=args.allow_live
        )
    else:
        result = run(args.source, args.output, allow_live=args.allow_live)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
