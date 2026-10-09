"""Fixed native SciQ prefixes: separate explicit-version OpenQA/MCQ comparisons.

Plan performs no inference. Freeze and execute require an explicit stable-source
confirmation. Private inputs/references stay outside public evidence exports.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from uuid import uuid4

from sqlalchemy import select

from app.modules.answering.models import AnswerRequest, Job
from app.modules.experiment.bridge import DatabaseAnswerBackend, create_backend
from app.modules.identity.models import User
from app.modules.knowledge.models import ActiveCorpus, CorpusRelease
from app.modules.knowledge.service import config_create, digest
from app.modules.model_settings.models import ModelConfiguration
from app.modules.model_settings.service import PREFIX, as_model_config
from evaluation.common import atomic_json, fingerprint, read_json
from evaluation.datasets.sciq import load_split, mcq_projection, normalize_choice
from evaluation.datasets.sciq_openqa import openqa_projection
from evaluation.metrics.paired import paired_analysis
from evaluation.metrics.scoring import aggregate, SCORER_VERSION
from evaluation.runner import EvaluationRun, validate_public, run_lock

ROOT = Path(__file__).resolve().parents[2]
REVISION = "2c94ad3e1aafab77146f384e23536f97a4849815"
MODEL_ID = "fababaa3-e482-47c4-b973-d940453354a2"
PRIVATE = ROOT / "artifacts/evaluator-private/sciq" / REVISION / "live_openqa_first64_20260913"
PUBLIC = ROOT / "evidence/sciq/live-openqa-first64-20260913"
SOURCE_HASHES = {
    "validation": "cf71bab38a36bdc7b6a81b6ebd20c0ab19d385b4abe1b833bd9b723ce90c1147",
    "test": "55a9ece0eb9f14379f91a59c5c4a6e46abb3fbf49f02781eb33c9945bd09e367",
}
TERMINAL = {"completed", "refused", "error", "cancelled", "invalid", "incomplete"}
PROTOCOL = "sciq_openqa"
MODE = "benchmark_openqa"
METRICS = ("em", "token_f1")


def select_protocol(protocol):
    """Choose isolated immutable study roots before any planning or execution."""
    global PROTOCOL, MODE, METRICS, PRIVATE, PUBLIC
    if protocol not in {"sciq_openqa", "sciq_mcq"}:
        raise ValueError("An explicit supported SciQ protocol is required.")
    PROTOCOL = protocol
    suffix = "openqa" if protocol == "sciq_openqa" else "mcq"
    MODE = "benchmark_" + suffix
    METRICS = ("em", "token_f1") if suffix == "openqa" else ("accuracy",)
    PRIVATE = (
        ROOT / "artifacts/evaluator-private/sciq" / REVISION / f"live_{suffix}_first64_20260913"
    )
    PUBLIC = ROOT / f"evidence/sciq/live-{suffix}-first64-20260913"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_snapshot():
    paths = []
    for folder in (
        "backend/app",
        "contracts",
        "conversation",
        "generation",
        "personalisation",
        "evaluation",
        "retrieval",
        "pipelines",
    ):
        paths.extend((ROOT / folder).rglob("*.py"))
    paths.extend((ROOT / "generation/prompts").glob("*.txt"))
    paths.append(Path(__file__).resolve())
    entries = [
        {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}
        for path in sorted(set(paths))
    ]
    return {"fingerprint": fingerprint(entries), "files": entries}


def runtime_backend(configuration_id=None):
    return create_backend(
        {
            "actor_email": "admin@example.com",
            "configuration_id": configuration_id,
            "inline_worker": False,
        }
    )


def plan():
    if (PUBLIC / "plan.json").exists() or (PRIVATE / "plan.json").exists():
        raise RuntimeError("Preserve the existing plan; selection cannot be replaced.")
    source_root = PRIVATE.parent / "derived/json_ascii_v1"
    splits, private_splits = [], []
    for split, expected in SOURCE_HASHES.items():
        source = source_root / (split + ".jsonl")
        if sha(source) != expected:
            raise RuntimeError("The complete pinned source file hash differs.")
        records, info = load_split(
            source, split=split, revision=REVISION, require_distinct_choices=False
        )
        lines = source.read_bytes().splitlines(keepends=True)
        if len(records) != 1000 or len(lines) != 1000:
            raise RuntimeError("The complete native split must contain exactly1000 records.")
        prefix = PRIVATE / (split + "-first64-exact.jsonl")
        prefix.parent.mkdir(parents=True, exist_ok=True)
        exact_prefix = b"".join(lines[:64])
        if prefix.exists():
            if prefix.read_bytes() != exact_prefix:
                raise RuntimeError(
                    "An earlier partial plan has different prefix bytes; preserve and reconcile it."
                )
        else:
            with prefix.open("xb") as stream:
                stream.write(exact_prefix)
        selected = records[:64]
        ids = [record.question_id for record in selected]
        for record in selected:
            if PROTOCOL == "sciq_mcq":
                if (
                    len(
                        {
                            normalize_choice(text)
                            for text in (record.correct_answer, *record.distractors)
                        }
                    )
                    != 4
                ):
                    raise RuntimeError(
                        "A selected native row has ambiguous choices; preserve this exact prefix and reconcile without substitution."
                    )
                command, _private = mcq_projection(
                    record, run_id="preflight", item_id=record.question_id, seed=5703
                )
            else:
                command, _private = openqa_projection(
                    record, run_id="preflight", item_id=record.question_id
                )
            validate_public(command)
            assert command["question_text"] == record.question
            assert not {"support", "gold", "correct_answer", "reference"}.intersection(command)
            assert ("options" in command) == (PROTOCOL == "sciq_mcq")
        descriptor = {
            "split": split,
            "full_count": 1000,
            "full_sha256": expected,
            "selected_count": 64,
            "selected_source_ordinals": {"first": 0, "last": 63},
            "prefix_sha256": sha(prefix),
            "question_ids_sha256": fingerprint(ids),
        }
        splits.append(descriptor)
        private_splits.append({**descriptor, "prefix_path": str(prefix), "question_ids": ids})
    backend = runtime_backend()
    with backend.factory() as db:
        model = db.get(ModelConfiguration, MODEL_ID)
        if model is None:
            raise RuntimeError("The required immutable managed model version is unavailable.")
        pointer = db.get(ActiveCorpus, 1)
        release = (
            db.get(CorpusRelease, pointer.release_id) if pointer and pointer.release_id else None
        )
        if release is None or release.state not in {"ready", "active"}:
            raise RuntimeError("A ready real active corpus is required for planning.")
        observation = {
            "observed_at": now(),
            "model_configuration_id": PREFIX + model.id,
            "model_public_config": as_model_config(model).to_dict(),
            "model_public_config_hash": model.config_hash,
            "corpus_release_id": release.id,
            "corpus_manifest_hash": digest(release.manifest),
            "embedding_configuration_hash": digest(release.configuration),
        }
    runs = [
        {"split": split, "condition": condition, "run_id": uuid4().hex}
        for split in SOURCE_HASHES
        for condition in ("E0", "E1")
    ]
    schedule = []
    for ordinal in range(64):
        for split_index, split in enumerate(SOURCE_HASHES):
            conditions = ("E0", "E1") if (ordinal + split_index) % 2 == 0 else ("E1", "E0")
            for condition in conditions:
                schedule.append(
                    {
                        "split": split,
                        "condition": condition,
                        "source_ordinal": ordinal,
                        "item_id": f"item_{ordinal:06}",
                    }
                )
    value = {
        "created_at": now(),
        "status": "prepared_not_frozen",
        "protocol_id": PROTOCOL,
        "dataset_revision": REVISION,
        "selection": "Exactly native source rows0–63 of validation and test, before this run's output inspection; no filtering, replacement or outcome-based selection.",
        "splits": splits,
        "paired_questions": 128,
        "scheduled_conditions": 256,
        "conditions": {"E0": "none", "E1": "R0"},
        "top_k": 5,
        "seed": 5703,
        "scorer_version": SCORER_VERSION,
        "model_configuration_id": PREFIX + MODEL_ID,
        "runs": runs,
        "execution_order": "For each source ordinal: validation and test; E0/E1 order counterbalanced by ordinal+split index parity. At most one condition in flight.",
        "schedule_hash": fingerprint(schedule),
        "observed_environment_not_frozen": observation,
        "provider_call_policy": {
            "scheduled_requests": 256,
            "max_calls_per_request": 4,
            "max_total_provider_calls": 1024,
            "actual_calls": None,
            "retries": "Existing shared finite retry/repair policy only; no manual repeat of failed/uncertain items.",
        },
        "statistics": {
            "metrics": ["conservative_compact_answer_em", "token_f1"]
            if PROTOCOL == "sciq_openqa"
            else ["label_selection_accuracy"],
            "paired_bootstrap_samples": 2000,
            "paired_seed": 5703,
            "binary_test": "exact_two_sided_McNemar_for_EM"
            if PROTOCOL == "sciq_openqa"
            else "exact_two_sided_McNemar_for_accuracy",
            "denominator_policy": "All scheduled conditions retained; refusal/error/invalid/cancelled/nonanswer score zero, unresolved items remain explicitly provisional.",
            "split_reports": "validation64/test64 plus descriptive pooled128; no parameter tuning on test and no model selection from these results.",
        },
        "provider_reported_cost": None,
        "human_review": None,
        "limits": [
            "Deterministic source prefixes are not representative random samples or full1000-item split benchmarks.",
            "Lexical EM/F1 do not establish semantic correctness, source entailment, educational value or teaching gains.",
            "SciQ native support, references and distractors remain evaluator-private and never enter answer commands or corpus ingestion.",
            "Native duplicate MCQ options are retained unchanged and do not filter stem-only OpenQA rows.",
            "No paired result, formal effectiveness or live inference is claimed at planning time.",
        ],
        "start_gate": "Do not freeze or call the provider until root confirms final prompt/runtime stabilization.",
    }
    if PROTOCOL == "sciq_mcq":
        value["limits"][1:4] = [
            "Label selection accuracy is separate from OpenQA EM/F1 and does not establish free-response correctness, source entailment or educational gains.",
            "Question and four unlabelled native candidates enter the command; correct labels, native support and private references never enter prompts or corpus ingestion.",
            "All exact prefix rows have four normalized-distinct choices; the full source's 48 anomalies remain unchanged. Any ambiguous selected row would halt this plan without filtering or replacement.",
        ]
        value["option_policy"] = (
            "Canonical text sort then deterministic question-ID/seed5703 permutation, independent of which candidate is gold; identical across E0/E1."
        )
    validate_public(value)
    atomic_json(
        PRIVATE / "plan.json",
        {**value, "private_splits": private_splits, "schedule": schedule},
        immutable=True,
    )
    atomic_json(PUBLIC / "plan.json", value, immutable=True)
    print(
        json.dumps(
            {
                "status": "prepared",
                "paired_questions": 128,
                "scheduled_conditions": 256,
                "provider_calls": 0,
                "plan": str(PUBLIC / "plan.json"),
            }
        )
    )


def verify_plan(value, frozen=None):
    public = read_json(PUBLIC / "plan.json")
    if public.get("protocol_id", PROTOCOL) != PROTOCOL:
        raise RuntimeError("The selected execution protocol differs from the immutable study.")
    if {key: value.get(key) for key in public} != public:
        raise RuntimeError("The private and public study plans differ.")
    if fingerprint(value["schedule"]) != public["schedule_hash"]:
        raise RuntimeError("The exact preregistered schedule changed.")
    for descriptor in public["splits"]:
        selected = [row for row in value["private_splits"] if row["split"] == descriptor["split"]]
        if (
            len(selected) != 1
            or {key: selected[0].get(key) for key in descriptor} != descriptor
            or fingerprint(selected[0]["question_ids"]) != descriptor["question_ids_sha256"]
        ):
            raise RuntimeError(
                "Private selected identities differ from the public dataset commitment."
            )
    expected = []
    for ordinal in range(64):
        for split_index, split in enumerate(SOURCE_HASHES):
            conditions = ("E0", "E1") if (ordinal + split_index) % 2 == 0 else ("E1", "E0")
            expected.extend(
                {
                    "split": split,
                    "condition": condition,
                    "source_ordinal": ordinal,
                    "item_id": f"item_{ordinal:06}",
                }
                for condition in conditions
            )
    if value["schedule"] != expected or len({row["run_id"] for row in value["runs"]}) != 4:
        raise RuntimeError("The complete ordered condition/run set differs from the fixed design.")
    if {(row["split"], row["condition"]) for row in value["runs"]} != {
        (split, condition) for split in SOURCE_HASHES for condition in ("E0", "E1")
    }:
        raise RuntimeError("Exactly four named split/condition runs are required.")
    if frozen is not None:
        if frozen["plan_sha256"] != sha(PUBLIC / "plan.json"):
            raise RuntimeError("The public plan changed after freeze.")
        if [
            {key: row[key] for key in ("split", "condition", "run_id")} for row in frozen["runs"]
        ] != value["runs"]:
            raise RuntimeError("Frozen run identities differ from the public plan.")


def verify_selection(value):
    for split in value["private_splits"]:
        source = PRIVATE.parent / "derived/json_ascii_v1" / (split["split"] + ".jsonl")
        prefix = Path(split["prefix_path"])
        if sha(source) != split["full_sha256"] or sha(prefix) != split["prefix_sha256"]:
            raise RuntimeError("Frozen dataset bytes changed.")
        if prefix.read_bytes() != b"".join(source.read_bytes().splitlines(keepends=True)[:64]):
            raise RuntimeError("Selection is no longer the exact source prefix.")


def freeze():
    value = read_json(PRIVATE / "plan.json")
    verify_plan(value)
    verify_selection(value)
    if (PUBLIC / "frozen.json").exists():
        raise RuntimeError("This run is already frozen; use execute to resume.")
    before = code_snapshot()
    base = runtime_backend()
    with base.factory() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        model = db.get(ModelConfiguration, MODEL_ID)
        if not model or model.workspace_id != actor.workspace_id:
            raise RuntimeError("The exact managed model is unavailable to the administrator.")
        config = config_create(
            db,
            "evaluation",
            f"SciQ {PROTOCOL} fixed first64 validation/test E0-E1 live20260913",
            {"model_configuration_id": PREFIX + MODEL_ID, "top_k": 5},
        )
        configuration_id = config.id
        db.commit()
    backend = runtime_backend(configuration_id)
    actual = backend.environment()
    observed = value["observed_environment_not_frozen"]
    if (
        actual["model_mode"] != "live"
        or actual["corpus_release_id"] != observed["corpus_release_id"]
        or actual["corpus_manifest_hash"] != observed["corpus_manifest_hash"]
    ):
        raise RuntimeError("The planned real corpus/model identity changed; reconcile explicitly.")
    frozen_runs = []
    for spec in value["runs"]:
        split = next(row for row in value["private_splits"] if row["split"] == spec["split"])
        config = {
            "protocol_id": PROTOCOL,
            "run_id": spec["run_id"],
            "condition": spec["condition"],
            "dataset_path": split["prefix_path"],
            "dataset_revision": REVISION,
            "split": spec["split"],
            "expected_count": 64,
            "expected_dataset_sha256": split["prefix_sha256"],
            "private_root": str(PRIVATE / "runs"),
            "backend_factory": "app.modules.experiment.bridge:create_backend",
            "backend_options": {
                "actor_email": "admin@example.com",
                "configuration_id": configuration_id,
                "inline_worker": False,
            },
            "configuration": {
                "top_k": 5,
                "retrieval_variant": "none" if spec["condition"] == "E0" else "R0",
            },
            "seed": 5703,
            "full_response_review_count": 20,
            "code_revision": "source-sha256:" + before["fingerprint"],
        }
        directory = PRIVATE / "runs" / spec["run_id"]
        run = (
            EvaluationRun(directory)
            if directory.exists()
            else EvaluationRun.freeze(config, backend, allow_live=True)
        )
        if (
            run.manifest["environment"] != actual
            or run.manifest["code_revision"] != config["code_revision"]
        ):
            raise RuntimeError("Partial frozen run differs; preserve and reconcile it.")
        frozen_runs.append(
            {
                **spec,
                "manifest_hash": run.manifest["manifest_hash"],
                "directory": str(run.directory),
            }
        )
    if before != code_snapshot():
        raise RuntimeError("Source changed during freeze; no inference may start.")
    for row in frozen_runs:
        backend.register_run(EvaluationRun(row["directory"]).manifest)
    result = {
        "frozen_at": now(),
        "status": "frozen_not_executed",
        "plan_sha256": sha(PUBLIC / "plan.json"),
        "configuration_id": configuration_id,
        "environment": actual,
        "source_snapshot": before,
        "runs": frozen_runs,
        "scheduled_conditions": 256,
        "provider_calls": 0,
    }
    atomic_json(PUBLIC / "frozen.json", result, immutable=True)
    print(json.dumps({"status": "frozen", "scheduled_conditions": 256, "provider_calls": 0}))


def summarize(runs, frozen, backend=None):
    rows = []
    for spec, run in runs:
        for item in run.state["items"]:
            outcome = item.get("outcome") or {}
            scores = item.get("scores") or {}
            rows.append(
                {
                    "split": spec["split"],
                    "condition": spec["condition"],
                    "run_id": spec["run_id"],
                    "item_id": item["item_id"],
                    "question_id": item["question_id"],
                    "status": item["status"],
                    "scores": scores,
                    "receipt": item.get("receipt"),
                    "model_mode": outcome.get("model_mode"),
                    "error_code": (outcome.get("error") or {}).get("code"),
                    "outcome": {
                        "timings": outcome.get("timings", {}),
                        "usage": {**(outcome.get("usage") or {}), "cost": None},
                    },
                }
            )
    if backend is not None:
        # Error outcomes omit usage in the public bridge projection. Read their
        # persisted numeric accounting as well; do not silently lose failed-call
        # usage or alter private evaluator state/results to fill that gap.
        with backend.factory() as db:
            for row in rows:
                receipt = row["receipt"] or {}
                request = (
                    db.get(AnswerRequest, receipt.get("request_id"))
                    if receipt.get("request_id")
                    else None
                )
                if request:
                    usage = request.trace.get("usage") or {}
                    row["outcome"]["usage"] = {
                        key: usage.get(key)
                        for key in (
                            "input_tokens",
                            "output_tokens",
                            "total_tokens",
                            "reasoning_tokens",
                        )
                    }
                    row["outcome"]["usage"]["cost"] = None
                    row["model_mode"] = (
                        "mock" if request.command["model_config"]["provider"] == "mock" else "live"
                    )
    complete = all(row["status"] in TERMINAL for row in rows)
    reports = {}
    for split in ("validation", "test", "pooled"):
        selected = [row for row in rows if split == "pooled" or row["split"] == split]
        old = sorted(
            (r for r in selected if r["condition"] == "E0"),
            key=lambda r: (r["split"], r["item_id"]),
        )
        new = sorted(
            (r for r in selected if r["condition"] == "E1"),
            key=lambda r: (r["split"], r["item_id"]),
        )
        assert [(r["split"], r["question_id"]) for r in old] == [
            (r["split"], r["question_id"]) for r in new
        ]
        reports[split] = {
            "paired_questions": len(old),
            "E0": aggregate(MODE, old),
            "E1": aggregate(MODE, new),
            "paired": {
                name: paired_analysis(
                    [r["scores"].get(name, 0) for r in old],
                    [r["scores"].get(name, 0) for r in new],
                    binary=name in {"em", "accuracy"},
                    seed=5703,
                    bootstrap_samples=2000,
                )
                for name in METRICS
            }
            if complete
            else None,
        }
    return {
        "recorded_at": now(),
        "status": "completed" if complete else "provisional",
        "protocol_id": PROTOCOL,
        "frozen_sha256": sha(PUBLIC / "frozen.json"),
        "scheduled_conditions": 256,
        "paired_questions": 128,
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "reports": reports,
        "rows": rows,
        "provider_reported_cost": None,
        "human_review": None,
        "limits": read_json(PUBLIC / "plan.json")["limits"][:-1],
    }


def execute():
    plan_value, frozen = read_json(PRIVATE / "plan.json"), read_json(PUBLIC / "frozen.json")
    verify_plan(plan_value, frozen)
    if (PUBLIC / "results.json").exists():
        previous = read_json(PUBLIC / "results.json")
        if previous["frozen_sha256"] != sha(PUBLIC / "frozen.json"):
            raise RuntimeError("The existing result belongs to a different frozen study.")
        print(
            json.dumps(
                {
                    "status": "existing_results_retained",
                    "scheduled_conditions": previous["scheduled_conditions"],
                    "new_provider_calls": 0,
                }
            )
        )
        return
    verify_selection(plan_value)
    if code_snapshot() != frozen["source_snapshot"]:
        raise RuntimeError("Runtime source/prompt identities changed after freeze.")
    backend = runtime_backend(frozen["configuration_id"])
    if backend.environment() != frozen["environment"]:
        raise RuntimeError("Frozen evaluation environment changed.")
    runs = [(spec, EvaluationRun(spec["directory"])) for spec in frozen["runs"]]
    indexed = {(spec["split"], spec["condition"]): run for spec, run in runs}
    for scheduled in plan_value["schedule"]:
        run = indexed[(scheduled["split"], scheduled["condition"])]
        item = next(row for row in run.state["items"] if row["item_id"] == scheduled["item_id"])
        if item["status"] in TERMINAL:
            continue
        if code_snapshot() != frozen["source_snapshot"]:
            raise RuntimeError("Source changed; preserve prior outcomes and stop new calls.")
        started = time.monotonic()
        while item["status"] not in TERMINAL:
            if time.monotonic() - started > 600:
                atomic_json(PUBLIC / "progress.json", summarize(runs, frozen))
                raise RuntimeError(
                    "The pending durable item requires operator reconciliation; no repeat issued."
                )
            run.advance(
                backend,
                max_new_submissions=1 if item["status"] == "pending" else 0,
                allow_live=True,
            )
            item = next(row for row in run.state["items"] if row["item_id"] == scheduled["item_id"])
            if run.state["status"] in {"environment_changed", "needs_reconciliation", "cancelled"}:
                atomic_json(PUBLIC / "progress.json", summarize(runs, frozen))
                raise RuntimeError(
                    "A frozen run requires explicit reconciliation; all outcomes retained."
                )
            if item["status"] not in TERMINAL:
                time.sleep(0.5)
        progress = {
            "recorded_at": now(),
            "scheduled_conditions": 256,
            "terminal_conditions": sum(
                item["status"] in TERMINAL
                for _, candidate in runs
                for item in candidate.state["items"]
            ),
            "latest": {**scheduled, "status": item["status"]},
        }
        atomic_json(PUBLIC / "progress.json", progress)
        print(json.dumps(progress), flush=True)
    for _spec, run in runs:
        run.export(PRIVATE / "exports")
    result = summarize(runs, frozen, backend)
    with backend.factory() as db:
        accounting = []
        for row in result["rows"]:
            receipt = row["receipt"] or {}
            request = (
                db.get(AnswerRequest, receipt.get("request_id"))
                if receipt.get("request_id")
                else None
            )
            if request:
                validate_public(request.command)
                assert request.command["model_config"]["configuration_id"] == PREFIX + MODEL_ID
                assert (
                    request.session_id
                    is request.context_snapshot_id
                    is request.profile_snapshot_id
                    is None
                )
                assert (request.release_id is None) == (row["condition"] == "E0")
                accounting.append(
                    {
                        "run_id": row["run_id"],
                        "item_id": row["item_id"],
                        "request_id": request.id,
                        "budget": request.budget,
                        "retrieval_candidates": len(request.trace.get("retrieval_candidates", [])),
                        "model_configuration_id": request.command["model_config"][
                            "configuration_id"
                        ],
                    }
                )
        result["execution_accounting"] = accounting
        result["actual_provider_calls"] = sum(row["budget"]["consumed_calls"] for row in accounting)
        result["actual_provider_calls_scope"] = (
            "Durable consumed-call reservations, including retries and any uncertain attempts; not a provider billing statement."
        )
    validate_public(result)
    atomic_json(PUBLIC / "results.json", result, immutable=True)
    print(
        json.dumps(
            {
                "status": result["status"],
                "scheduled_conditions": 256,
                "outcomes": result["status_counts"],
                "actual_provider_calls": result["actual_provider_calls"],
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "freeze", "execute"))
    parser.add_argument("--protocol", choices=("sciq_openqa", "sciq_mcq"), default="sciq_openqa")
    parser.add_argument("--confirm-stable", action="store_true")
    args = parser.parse_args()
    select_protocol(args.protocol)
    if args.action != "plan" and not args.confirm_stable:
        raise SystemExit(
            "Freeze/execute require confirmed stable source and explicit authorization."
        )
    if args.action == "plan":
        plan()
    else:
        with run_lock(PRIVATE):
            {"freeze": freeze, "execute": execute}[args.action]()


if __name__ == "__main__":
    main()
