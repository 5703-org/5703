"""Resumable real-model experiments using the product's checked generator.

Reference answers and help allowances never enter generation or retrieval. Each
request reserves a durable record before its first call; interrupted reservations
are preserved for explicit diagnosis instead of automatically repeating charges.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import threading
import time

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.model_settings.service import as_model_config, resolve_secret
from app.modules.model_settings.models import ModelConfiguration
from contracts.models import EvidenceSnapshot
from evaluation.enhancement.protocol import (
    CITATION_CONDITIONS,
    PROTOCOL_VERSION,
    digest,
    freeze,
    generation_task,
    verify_frozen,
)
from generation.joint_policy import VERSION
from generation.service import GenerationService
from generation.token_counting import TokenCounter
from generation.types import GenerationRequest, RequestBudget

TASK_TYPES = {
    "comparison": "concept_comparison",
    "process": "process_reasoning",
    "calculation": "simple_calculation",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def runtime_sources():
    root = Path(__file__).resolve().parents[2]
    paths = set()
    for name in ("generation", "conversation", "retrieval", "contracts"):
        paths.update((root / name).rglob("*.py"))
    paths.update((root / "generation/prompts").glob("*.txt"))
    paths.update(
        root / name
        for name in (
            "personalisation/compiler.py",
            "evaluation/enhancement/runner.py",
            "evaluation/enhancement/protocol.py",
            "evaluation/enhancement/sources.py",
        )
    )
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def recovered_attempts(events):
    values = (
        [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
        if events.exists()
        else []
    )
    starts = {e.get("attempt_id", e.get("sequence")): e for e in values if e["phase"] == "start"}
    finishes = {e.get("attempt_id", e.get("sequence")): e for e in values if e["phase"] == "finish"}
    attempts = []
    for identity, event in starts.items():
        finished = finishes.get(identity)
        attempts.append(
            {
                k: v
                for k, v in (
                    finished
                    or {**event, "usage": {}, "error": {"code": "UNCERTAIN_EXTERNAL_COMPLETION"}}
                ).items()
                if k not in {"messages", "raw_text", "phase"}
            }
        )
    return attempts


def load(path: Path, *, frozen=True):
    value = json.loads(path.read_text(encoding="utf-8"))
    return verify_frozen(value) if frozen else value


def resolve_source(run: Path, manifest: dict) -> Path:
    """Locate packaged study inputs and require their original frozen identity."""
    original = Path(manifest["source_directory"])
    for candidate in (original, run.parent / original.name, run.parent / "sources" / original.name):
        path = candidate / "manifest.json"
        if path.exists() and digest(load(path)) == manifest["source_manifest_sha256"]:
            return candidate
    raise ValueError("Matching frozen study sources are unavailable")


def live_config():
    """Resolve credentials in memory; only public configuration leaves this scope."""
    settings = Settings()
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 10})
    try:
        with Session(engine) as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            identity = db.execute(
                text(
                    "select configuration_id from active_model_configurations where configuration_id is not null order by workspace_id limit 1"
                )
            ).scalar_one()
            row = db.scalar(select(ModelConfiguration).where(ModelConfiguration.id == identity))
            config = as_model_config(row)
            secret = resolve_secret(db, settings, config.configuration_id)
            if config.provider == "mock" or not secret:
                raise ValueError("A configured real model and local credential are required")
            config.validate()
            return config, secret
    finally:
        engine.dispose()


def append_event(path, event):
    # The supplied callbacks include model prompts/results but never credentials.
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"recorded_at": now(), **event}, ensure_ascii=False) + "\n")
        stream.flush()


def public_exposure(outcome):
    """Exact same projection consumed by the user-facing citation endpoints."""
    projection = outcome.get("delivered_projection") or {}
    if not outcome.get("response") or outcome.get("error"):
        return None
    return {
        "response": projection.get("response", outcome["response"]),
        "citation_views": projection.get("citation_views", []),
        "content_hash": projection.get("content_hash"),
        "exposure_assumption": "All ordinarily accessible citation views opened after this turn; DOM rendering is tested separately.",
    }


def run(
    source: Path, output: Path, *, experiment="hints", task_ids=None, conditions=None, workers=4
):
    dataset = load(source / "private-tasks.json")
    source_manifest = load(source / "manifest.json")
    if source_manifest["dataset_sha256"] != digest(dataset):
        raise ValueError("Source manifest does not identify this exact private dataset")
    tasks = [t for t in dataset["tasks"] if not task_ids or t["id"] in task_ids]
    if not tasks or (task_ids and set(task_ids) != {t["id"] for t in tasks}):
        raise ValueError("Requested task identities differ from frozen input")
    if experiment not in {"hints", "citations"} or not 1 <= workers <= 12:
        raise ValueError("Unknown experiment or invalid concurrency")
    if dataset["split"] == "formal" and (task_ids or conditions):
        raise ValueError("Formal runs must schedule every task and condition")
    config, secret = live_config()
    conditions = tuple(
        conditions
        or (("T0", "T1", "T2", "T3", "T4") if experiment == "hints" else CITATION_CONDITIONS)
    )
    valid = {"T0", "T1", "T2", "T3", "T4"} if experiment == "hints" else set(CITATION_CONDITIONS)
    if not conditions or set(conditions) - valid:
        raise ValueError("Unknown condition")
    # Checker response can contain one verdict per sentence. The active configuration
    # remains unchanged; this explicit experiment-stage reservation is frozen below.
    checker = replace(config, max_tokens=max(config.max_tokens, 4096))
    # Initialize optional tokenizer libraries once before concurrent requests.
    TokenCounter(config)
    TokenCounter(checker)
    source_hashes = runtime_sources()
    retrieval_hashes = {
        task["id"]: digest(load(source / "retrieval" / (task["id"] + ".json"))) for task in tasks
    }
    groups = []
    planned = []
    for task in sorted(tasks, key=lambda t: digest({"seed": 20260920, "id": t["id"]})):
        shift = int(digest(task["id"])[:8], 16) % len(conditions)
        for condition in conditions[shift:] + conditions[:shift]:
            groups.append((task, condition))
            for turn in range(1, 4 if experiment == "hints" else 2):
                planned.append(
                    {
                        "id": f"{task['id']}-{condition}-H{turn}",
                        "task_id": task["id"],
                        "condition": condition,
                        "turn": turn,
                    }
                )
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "run-manifest.json"
    if manifest_path.exists():
        old = load(manifest_path)
        created = old["created_at"]
    else:
        created = now()
    freeze(
        manifest_path,
        {
            "protocol": PROTOCOL_VERSION,
            "created_at": created,
            "experiment": experiment,
            "split": dataset["split"],
            "source_manifest_sha256": digest(source_manifest),
            "source_directory": str(source),
            "model_config": config.to_dict(),
            "checker_config": checker.to_dict(),
            "runtime_source_hashes": source_hashes,
            "retrieval_hashes": retrieval_hashes,
            "dataset_sha256": digest(dataset),
            "memory_snapshot": None,
            "planned": planned,
            "planned_count": len(planned),
            "task_metadata": {
                t["id"]: {k: t[k] for k in ("subject", "task_type", "family")} for t in tasks
            },
            "concurrency": workers,
            "generation_reference_fields": [],
            "source_open_policy": "ordinary citation views opened every turn",
            "product_path": "GenerationService.generate with exact delivered_projection; HTTP lifecycle tested separately",
        },
    )
    print_lock = threading.Lock()

    def execute_group(task, condition):
        private_input = load(source / "retrieval" / (task["id"] + ".json"))
        if digest(private_input) != retrieval_hashes[task["id"]]:
            raise ValueError("Frozen task retrieval changed")
        clean = generation_task(task)
        prior = []
        history = []
        results = []
        for turn in range(1, 4 if experiment == "hints" else 2):
            identity = f"{task['id']}-{condition}-H{turn}"
            destination = output / "results" / (identity + ".json")
            if destination.exists():
                result = load(destination)
            else:
                if runtime_sources() != source_hashes:
                    raise ValueError("Runtime sources changed after this experiment was frozen")
                reservation = output / "reservations" / (identity + ".json")
                if reservation.exists():
                    with print_lock:
                        print(
                            json.dumps(
                                {"id": identity, "status": "interrupted_reservation_preserved"}
                            ),
                            flush=True,
                        )
                    break
                freeze(
                    reservation,
                    {
                        "id": identity,
                        "reserved_at": now(),
                        "config_sha256": digest(config.to_dict()),
                        "previous_exposure_sha256": digest(prior),
                    },
                )
                events = output / "events" / (identity + ".jsonl")
                events.parent.mkdir(parents=True, exist_ok=True)
                hint = experiment == "hints"
                question = clean["question"] + ("\n" + clean["turns"][turn - 1] if hint else "")
                prepared = dict(private_input.get("prepared_query") or {})
                # Retrieval is fixed across conditions. Its preparation result and full
                # original task stay identical; only the explicit help request changes.
                context = {
                    "task_id": task["id"],
                    "task_version": turn,
                    "task_type": TASK_TYPES[task["task_type"]],
                    "teaching_mode": "hint" if hint else "direct",
                    "help_level": turn if hint else 1,
                    "requested_help": clean["turns"][:turn] if hint else ["Complete explanation"],
                    "current_problem": clean["question"],
                    "delivered_turns": prior,
                    "disclosure_events": [],
                    "policy_version": VERSION,
                }
                req = GenerationRequest(
                    request_id=identity,
                    mode="interactive_chat",
                    condition="R2",
                    question=question,
                    evidence=[
                        {
                            k: v
                            for k, v in {**item, "context_order": i}.items()
                            if k in EvidenceSnapshot.model_fields
                        }
                        for i, item in enumerate(private_input["evidence"], 1)
                    ],
                    prepared_query=prepared or None,
                    history=history,
                    config=config,
                    checker_config=checker,
                    enhancement_version=VERSION,
                    attribution_strategy="posthoc_spans" if hint else condition,
                    teaching_condition=condition if hint else "T2",
                    teaching_context=context,
                    memory_context=None,
                    source_map=private_input["source_map"],
                )
                started = time.monotonic()
                try:
                    outcome = (
                        GenerationService(api_key=secret, checker_api_key=secret)
                        .generate(req, RequestBudget(), lambda event: append_event(events, event))
                        .to_dict()
                    )
                except Exception as exc:
                    # Do not leak transport objects or credentials from exception text.
                    outcome = {
                        "response": None,
                        "error": {
                            "code": "EXPERIMENT_EXCEPTION",
                            "exception_type": type(exc).__name__,
                        },
                    }
                    recovered = recovered_attempts(events)
                    outcome.update(
                        attempts=recovered,
                        budget={"consumed_calls": len(recovered)},
                        usage_recovered_from_durable_events=True,
                    )
                if runtime_sources() != source_hashes:
                    outcome["error"] = {"code": "RUNTIME_CHANGED_DURING_REQUEST"}
                    outcome["response"] = None
                result = {
                    "id": identity,
                    "task_id": task["id"],
                    "condition": condition,
                    "turn": turn,
                    "experiment": experiment,
                    "completed_at": now(),
                    "wall_seconds": time.monotonic() - started,
                    "retrieval_sha256": digest(private_input),
                    "generation_input_fields": list(clean),
                    "prior_exposure": prior.copy(),
                    "outcome": outcome,
                }
                result["exposure"] = public_exposure(outcome)
                freeze(destination, result)
            exposure = result.get("exposure")
            if exposure:
                prior.append(exposure)
                history.extend(
                    [
                        {
                            "role": "user",
                            "content": clean["question"]
                            + ("\n" + clean["turns"][turn - 1] if experiment == "hints" else ""),
                        },
                        {
                            "role": "assistant",
                            "content": exposure["response"].get("answer_text", ""),
                        },
                    ]
                )
            results.append(result)
            with print_lock:
                out = result["outcome"]
                print(
                    json.dumps(
                        {
                            "id": identity,
                            "status": (out.get("error") or {}).get(
                                "code", (out.get("response") or {}).get("response_type", "missing")
                            ),
                            "calls": out.get("budget", {}).get("consumed_calls", 0),
                        }
                    ),
                    flush=True,
                )
        return results

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(execute_group, *group) for group in groups]
        for future in as_completed(futures):
            future.result()
    return {"planned": len(planned), "completed": len(list((output / "results").glob("*.json")))}
