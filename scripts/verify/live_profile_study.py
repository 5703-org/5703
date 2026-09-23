"""Prespecify three neutral bases and 27 independent live presentation outputs.

Plan reads the retained suite only. Execute requires a confirmed source freeze;
HTTP creates new owned sessions and independent teaching jobs. No ratings are
inferred, unsuccessful bases are never replaced, and uncertain mutations stop.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
from pathlib import Path
import time
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text

from app.core.config import Settings
from evaluation.annotations.blind import blank_ratings_csv, create_blind_package
from evaluation.common import atomic_json, fingerprint, read_json, utc_now
from evaluation.runner import run_lock, validate_public

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "evidence/personalisation/live-three-question-20260913"
PRIVATE = ROOT / "artifacts/evaluator-private/profile/live-three-question-20260913"
SUITE = ROOT / "evidence/answering-upgrade/20260913/live-suite-attempt2.json"
MODEL = "fababaa3-e482-47c4-b973-d940453354a2"
RELEASE = "4f11bd70-a486-4d16-b216-78cfe499530a"
QUESTIONS = (
    (
        "biology",
        "What is photosynthesis, and how do the light-dependent reactions and Calvin cycle work together?",
    ),
    ("chemistry", "Why does a buffer resist a pH change after a small amount of acid is added?"),
    ("anatomy", "How do the kidneys help maintain blood volume and blood pressure?"),
)
LEVELS = ("beginner", "intermediate", "advanced")
CONDITIONS = ("C0", "C1", "C2")
TERMINAL = {"completed", "refused", "error", "cancelled", "invalid", "incomplete"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def retain_json(path, value):
    """Resume artifact export only when the already saved bytes mean the same data."""
    if Path(path).exists():
        if read_json(path) != value:
            raise RuntimeError("Preserve the differing existing artifact: " + str(path))
    else:
        atomic_json(path, value, immutable=True)


def source_snapshot():
    paths = []
    for folder in (
        "backend/app",
        "contracts",
        "generation",
        "conversation",
        "retrieval",
        "personalisation",
        "evaluation",
        "pipelines",
    ):
        paths.extend((ROOT / folder).rglob("*.py"))
    paths.extend((ROOT / "generation/prompts").glob("*.txt"))
    paths.append(Path(__file__).resolve())
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(paths))}


def plan():
    if (PUBLIC / "plan.json").exists() or (PRIVATE / "prior-suite-references.json").exists():
        raise RuntimeError("Preserve the existing plan and fixed question selection.")
    suite = read_json(SUITE)
    selected, descriptors = [], []
    for domain, question in QUESTIONS:
        matches = [r for r in suite["cases"] if r["question"] == question and r["group"] == "core"]
        if len(matches) != 1:
            raise RuntimeError("The exact prior question identity is unavailable.")
        row = matches[0]
        selected.append(row)
        descriptors.append(
            {
                "domain": domain,
                "question": question,
                "prior_request_id": row["receipt"]["request_id"],
                "prior_answer_id": row["answer"]["id"],
                "prior_response_hash": fingerprint(row["answer"]["response"]),
                "prior_evidence_hash": fingerprint(row["answer"]["evidence"]),
                "prior_use_profile": row["answer"]["profile_snapshot"]["use_profile"],
            }
        )
    value = {
        "schema": "prespecified_live_profile_study_v1",
        "created_at": utc_now(),
        "status": "prepared_not_executed",
        "protocol_id": "profile_study",
        "selection": "Three named prior-suite questions chosen before any new neutral base or study output; no replacements based on outcome.",
        "prior_suite": SUITE.relative_to(ROOT).as_posix(),
        "prior_suite_sha256": sha(SUITE),
        "questions": descriptors,
        "seed": 5703,
        "model_configuration_id": "model-settings:" + MODEL,
        "corpus_release_id": RELEASE,
        "neutral_base_count": 3,
        "neutral_base_policy": "One fresh session/question, use_profile=false, empty history; retain every terminal outcome and exact request/response/source snapshots. Prior profile-on answers are references only and are not passed off as neutral bases.",
        "conditions": {
            "C0": "No presentation policy",
            "C1": "One-line target learner level",
            "C2": "Existing compiled structured level policy",
        },
        "levels": list(LEVELS),
        "scheduled_study_outputs": 27,
        "planned_items": [
            {"domain": d, "target_level": level, "condition": condition}
            for d, _ in QUESTIONS
            for level in LEVELS
            for condition in CONDITIONS
        ],
        "call_policy": {
            "base_requests": 3,
            "base_call_cap_each": 4,
            "study_call_cap_each": 1,
            "maximum_provider_calls": 39,
            "automatic_success_or_failed_output_repeats": False,
        },
        "missing_base_policy": "Generate all three once-only bases. If any is not a completed grounded neutral answer, retain its outcome and all27 planned study items as not_started_missing_base; do not choose easier questions or silently reduce the study.",
        "matching": "All nine outputs/question share the exact saved base, submitted evidence and managed model; only existing condition and target level vary.",
        "queue_order": "Existing teaching API preregisters27 records and shuffles them with seed5703 before enqueueing. One existing durable worker executes them.",
        "preservation": "Original suite file/references remain immutable; new base Answer/AnswerRequest/profile/context records are fingerprinted before and after the independent study.",
        "review": {
            "rubric": "profile_rating_v1",
            "condition_blind": True,
            "actual_independent_ratings": 0,
            "ratings": None,
            "private_condition_key": "Excluded evaluator-private directory only",
            "public_material": "Opaque reviewer IDs, target level, question, output/source text and status; ratings template cells remain blank.",
        },
        "limits": [
            "Three purposively selected supported topics are not a representative benchmark.",
            "A generated neutral base is not a gold answer; correctness and source support need independent review.",
            "No semantic preservation, level fit or learning-gain conclusion follows from successful calls or valid JSON.",
            "No SciQ gold/support/choices are used or copied into the study.",
            "The remote model alias and local tokenizer retain their recorded reproducibility limits.",
            "The existing worker is shared with the root chat suite and separate SciQ workloads. Queue contention is observed; no isolated latency or SLA claim is supported.",
        ],
        "execution_gate": "Explicit root source-freeze confirmation required before execute; plan makes no model or database calls.",
    }
    validate_public(value)
    atomic_json(PRIVATE / "prior-suite-references.json", selected, immutable=True)
    atomic_json(PUBLIC / "plan.json", value, immutable=True)
    print({"status": value["status"], "bases": 3, "study_outputs": 27, "provider_calls": 0})


class API:
    def __init__(self, base_url, email, password):
        self.client = httpx.Client(base_url=base_url, timeout=90)
        identity = self.call("POST", "/auth/login", json={"email": email, "password": password})
        self.client.headers["Authorization"] = "Bearer " + identity["access_token"]

    def call(self, method, path, **kwargs):
        response = self.client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"API {method} {path}: HTTP {response.status_code}")
        return response.json()["data"]


def records(engine, ids):
    captured = []
    with engine.connect() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        for identity in ids:
            answer = db.execute(
                text("SELECT row_to_json(a) FROM answers a WHERE id=:id"), {"id": identity}
            ).scalar_one()
            request = db.execute(
                text("SELECT row_to_json(r) FROM answer_requests r WHERE id=:id"),
                {"id": answer["request_id"]},
            ).scalar_one()
            snapshots = [
                db.execute(
                    text("SELECT row_to_json(s) FROM snapshots s WHERE id=:id"),
                    {"id": request[key]},
                ).scalar_one()
                for key in ("profile_snapshot_id", "context_snapshot_id")
                if request.get(key)
            ]
            evidence = list(
                db.execute(
                    text(
                        "SELECT row_to_json(e) FROM evidence_snapshots e WHERE answer_id=:id ORDER BY evidence_id"
                    ),
                    {"id": identity},
                ).scalars()
            )
            citations = list(
                db.execute(
                    text(
                        "SELECT row_to_json(c) FROM citations c WHERE answer_id=:id ORDER BY evidence_id"
                    ),
                    {"id": identity},
                ).scalars()
            )
            captured.append(
                {
                    "answer": answer,
                    "request": request,
                    "snapshots": snapshots,
                    "evidence": evidence,
                    "citations": citations,
                }
            )
    return captured


def execute(args):
    blueprint = read_json(PUBLIC / "plan.json")
    if blueprint["prior_suite_sha256"] != sha(SUITE) or [
        (r["domain"], r["question"]) for r in blueprint["questions"]
    ] != list(QUESTIONS):
        raise RuntimeError("The fixed source/question plan changed.")
    state_path = PRIVATE / "state.json"
    if state_path.exists():
        state = read_json(state_path)
        if (
            state["plan_sha256"] != sha(PUBLIC / "plan.json")
            or state["source_snapshot"] != source_snapshot()
        ):
            raise RuntimeError("Frozen study source/plan changed; retain prior outcomes.")
    else:
        state = {
            "created_at": utc_now(),
            "plan_sha256": sha(PUBLIC / "plan.json"),
            "source_snapshot": source_snapshot(),
            "status": "ready",
            "bases": [
                {"domain": d, "question": q, "idempotency_key": str(uuid4()), "state": "pending"}
                for d, q in QUESTIONS
            ],
        }
        atomic_json(state_path, state, immutable=True)
    if state["status"] in {"completed", "base_ineligible"} or (PUBLIC / "results.json").exists():
        print({"status": state["status"], "new_provider_calls": 0})
        return
    password = os.environ.get(args.password_env)
    if not password:
        raise RuntimeError(
            "Provide the authorized account password through the named environment variable."
        )
    api = API(args.base_url, args.email, password)
    engine = create_engine(Settings().database_url)

    def save():
        atomic_json(state_path, state)

    def unchanged():
        if source_snapshot() != state["source_snapshot"]:
            raise RuntimeError("Runtime source changed; no new study submission is allowed.")
        model = api.call("GET", "/admin/model-configurations")
        releases = api.call("GET", "/corpus/releases")
        if model["active_configuration_id"] != MODEL or [
            r["id"] for r in releases if r["state"] == "active"
        ] != [RELEASE]:
            raise RuntimeError("Expected model/corpus pointer changed; preserve current outcomes.")

    try:
        unchanged()
        for row in state["bases"]:
            if row["state"] == "terminal":
                continue
            if row["state"] == "creating_session":
                raise RuntimeError(
                    "An unconfirmed session creation requires explicit reconciliation; no duplicate mutation issued."
                )
            if not row.get("session_id"):
                row["state"] = "creating_session"
                save()
                row["session_id"] = api.call(
                    "POST",
                    "/sessions",
                    json={"title": "Fixed profile-study neutral base: " + row["domain"]},
                )["id"]
                row["state"] = "session_created"
                save()
            if not row.get("receipt"):
                unchanged()
                row["state"] = "submitting"
                save()
                # The same body/key reconciles a lost HTTP receipt through the
                # application's existing durable idempotency contract.
                row["receipt"] = api.call(
                    "POST",
                    f"/sessions/{row['session_id']}/messages",
                    json={"content": row["question"], "use_profile": False},
                    headers={"Idempotency-Key": row["idempotency_key"]},
                )
                row["state"] = "submitted"
                save()
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                job = api.call("GET", "/jobs/" + row["receipt"]["job_id"])
                if job["state"] in {"succeeded", "failed", "cancelled"}:
                    break
                time.sleep(1)
            else:
                raise RuntimeError(
                    "Pending base job needs reconciliation; no replacement is submitted."
                )
            row["job"] = job
            row["answer"] = (
                api.call("GET", "/answers/" + job["answer_id"]) if job.get("answer_id") else None
            )
            answer = row["answer"] or {}
            row["eligible"] = bool(
                job["state"] == "succeeded"
                and answer.get("model_mode") == "live"
                and answer.get("response", {}).get("response_type") == "answer"
                and answer.get("response", {}).get("citations")
                and (answer.get("profile_snapshot") or {}).get("use_profile") is False
            )
            row["state"] = "terminal"
            save()
            print(
                {
                    "domain": row["domain"],
                    "state": job["state"],
                    "eligible_neutral_base": row["eligible"],
                },
                flush=True,
            )
        if not all(row["eligible"] for row in state["bases"]):
            state["status"] = "base_ineligible"
            save()
            atomic_json(
                PUBLIC / "results.json",
                {
                    "status": "base_ineligible",
                    "plan_sha256": sha(PUBLIC / "plan.json"),
                    "planned_outputs": 27,
                    "not_started_missing_base": 27,
                    "planned_items": [
                        {**item, "status": "not_started_missing_base"}
                        for item in blueprint["planned_items"]
                    ],
                    "base_outcomes": [
                        {
                            "domain": row["domain"],
                            "state": row["job"]["state"],
                            "response_type": (row["answer"] or {})
                            .get("response", {})
                            .get("response_type"),
                            "eligible": row["eligible"],
                        }
                        for row in state["bases"]
                    ],
                    "human_review": None,
                    "metrics": None,
                },
                immutable=True,
            )
            return
        ids = [row["answer"]["id"] for row in state["bases"]]
        captured_path = PRIVATE / "base-records-before.json"
        if not captured_path.exists():
            atomic_json(captured_path, records(engine, ids), immutable=True)
        captured = read_json(captured_path)
        if fingerprint(captured) != fingerprint(records(engine, ids)):
            raise RuntimeError("A saved base record changed; do not start matched study work.")
        for row in captured:
            if (
                row["request"]["release_id"] != RELEASE
                or row["request"]["command"]["model_config"]["configuration_id"]
                != "model-settings:" + MODEL
            ):
                raise RuntimeError("A neutral base used a different source/model configuration.")
            for evidence in row["evidence"]:
                payload = evidence["payload"]
                if hashlib.sha256(payload["text"].encode()).hexdigest() != payload["text_hash"]:
                    raise RuntimeError("A saved base passage fails exact text identity.")
        if not state.get("configuration_id"):
            config = api.call(
                "POST",
                "/configurations",
                json={
                    "kind": "evaluation",
                    "name": "Fixed three-question live profile study",
                    "values": {"model_configuration_id": "model-settings:" + MODEL, "top_k": 5},
                },
            )
            state["configuration_id"] = config["id"]
            save()
        if state.get("study_state") == "creating":
            raise RuntimeError(
                "An unconfirmed teaching-study creation needs explicit reconciliation; no second run is created."
            )
        if not state.get("run_id"):
            unchanged()
            state["study_state"] = "creating"
            save()
            created = api.call(
                "POST",
                "/teaching-studies",
                json={
                    "base_answer_ids": ids,
                    "configuration_id": state["configuration_id"],
                    "seed": blueprint["seed"],
                },
            )
            state["run_id"] = created["id"]
            state["study_state"] = "frozen"
            save()
            atomic_json(PRIVATE / "frozen-study.json", created, immutable=True)
        frozen = read_json(PRIVATE / "frozen-study.json")
        manifest = frozen["manifest"]
        expected = {
            (id, level, condition) for id in ids for level in LEVELS for condition in CONDITIONS
        }
        if (
            frozen["scheduled_count"] != 27
            or frozen["model_mode"] != "live"
            or manifest["evidence_class"] != "live_model_run"
            or {(r["base_answer_id"], r["target_level"], r["condition"]) for r in frozen["items"]}
            != expected
        ):
            raise RuntimeError("Frozen study does not match the complete live27-output design.")
        if state["study_state"] == "frozen":
            unchanged()
            api.call("POST", f"/experiments/{state['run_id']}/start")
            state["study_state"] = "started"
            save()
        deadline = time.monotonic() + 2400
        while time.monotonic() < deadline:
            result = api.call("GET", f"/experiments/{state['run_id']}/results")
            atomic_json(PRIVATE / "progress.json", result)
            if len(result["items"]) == 27 and all(
                row["status"] in TERMINAL for row in result["items"]
            ):
                break
            if result["status"] == "environment_changed":
                raise RuntimeError(
                    "Frozen teaching environment changed; all prior outputs retained."
                )
            time.sleep(2)
        else:
            raise RuntimeError(
                "Pending study requires reconciliation; no repeated provider work issued."
            )
        after = records(engine, ids)
        retain_json(PRIVATE / "base-records-after.json", after)
        if fingerprint(after) != fingerprint(captured):
            raise RuntimeError("Independent study mutated a base record.")
        if (
            len(result["items"]) != 27
            or result["scheduled_count"] != 27
            or result["human_review"] is not None
            or result["metrics"] is not None
        ):
            raise RuntimeError("Study denominator or unrated result contract changed.")
        retain_json(PRIVATE / "outputs.json", result)
        package = create_blind_package(result["items"], seed=blueprint["seed"])
        retain_json(PRIVATE / "private-review-package.json", package)
        reviewer = {"rubric": package["rubric"], "review_items": package["review_items"]}
        if any(
            set(item) & {"condition", "item_id", "question_id", "model_configuration_hash"}
            for item in reviewer["review_items"]
        ):
            raise RuntimeError("Review material exposes condition identity.")
        retain_json(PUBLIC / "review-items.json", reviewer)
        ratings = blank_ratings_csv(package)
        rows = list(csv.DictReader(io.StringIO(ratings)))
        assert len(rows) == 27 and all(
            not value for row in rows for key, value in row.items() if key != "blind_id"
        )
        ratings_path = PUBLIC / "ratings-template.csv"
        if not ratings_path.exists():
            with ratings_path.open("x", encoding="utf-8", newline="") as output:
                output.write(ratings)
        elif ratings_path.read_text(encoding="utf-8") != ratings.replace("\r\n", "\n"):
            raise RuntimeError("Retain existing rating edits; never replace actual review input.")
        retain_json(
            PUBLIC / "ratings-template.json",
            {
                "ratings": [{key: value or None for key, value in row.items()} for row in rows],
                "actual_independent_ratings": 0,
            },
        )
        summary = {
            "recorded_at": utc_now(),
            "status": "terminal_outputs_recorded",
            "run_id": state["run_id"],
            "plan_sha256": sha(PUBLIC / "plan.json"),
            "model_mode": result["model_mode"],
            "scheduled_count": 27,
            "outcome_counts": result["outcome_counts"],
            "neutral_base_count": len(ids),
            "base_records_unchanged": True,
            "base_records_sha256": fingerprint(captured),
            "private_output_sha256": fingerprint(result),
            "study_consumed_calls": sum(row["budget"]["consumed_calls"] for row in result["items"]),
            "base_consumed_calls": sum(
                row["request"]["budget"]["consumed_calls"] for row in captured
            ),
            "human_review": None,
            "metrics": None,
            "cost": None,
            "limits": blueprint["limits"],
            "review_files": ["review-items.json", "ratings-template.csv", "ratings-template.json"],
            "private_key_exported": False,
        }
        validate_public(summary)
        atomic_json(PUBLIC / "results.json", summary, immutable=True)
        state["status"] = "completed"
        save()
        print(
            {
                "status": summary["status"],
                "outcomes": summary["outcome_counts"],
                "actual_independent_ratings": 0,
            }
        )
    finally:
        api.client.close()
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "execute"))
    parser.add_argument("--confirm-stable", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password-env", default="CS30_STUDY_PASSWORD")
    args = parser.parse_args()
    if args.action == "plan":
        plan()
        return
    if not args.confirm_stable:
        raise SystemExit("Execute requires explicit confirmed source freeze and run authorization.")
    with run_lock(PRIVATE):
        execute(args)


if __name__ == "__main__":
    main()
