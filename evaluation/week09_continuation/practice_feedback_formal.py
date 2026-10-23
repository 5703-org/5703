"""Source-bound HTTP practice-feedback study on a disposable isolated installation.

The catalogue and learner credentials are private. This runner checks actual API
publication, key isolation and deterministic feedback; it does not assign human
solvability or pedagogical-quality scores. A reservation is written before each
mutating request and an interrupted run is never automatically replayed.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import time
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from .protocol import OFFICIAL_BOOKS

SCHEMA = "week09_practice_feedback_catalogue_v1"
FREEZE_SCHEMA = "week09_practice_feedback_freeze_v2"
RUN_SCHEMA = "week09_practice_feedback_http_run_v2"
EXECUTION_POLICY = "zero_provider_rule_grades_v2"
SUPPORTED_KINDS = {"mcq", "multiselect", "short", "numeric", "step"}
ALLOWED_SPLITS = {"pilot", "reserved"}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def exclusive_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(stable_json(value))


def load_catalogue(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or not isinstance(data.get("cases"), list):
        raise ValueError("Unsupported or empty practice-feedback catalogue")
    if not data["cases"]:
        raise ValueError("Practice-feedback catalogue has no cases")
    ids: set[str] = set()
    group_splits: dict[str, str] = {}
    for case in data["cases"]:
        identity, split, group = (
            case.get("id"),
            case.get("split"),
            case.get("concept_group"),
        )
        if not identity or identity in ids or split not in ALLOWED_SPLITS or not group:
            raise ValueError("Cases require distinct IDs, valid splits and concept groups")
        ids.add(identity)
        if group in group_splits and group_splits[group] != split:
            raise ValueError(f"Concept group crosses pilot and reserved: {group}")
        group_splits[group] = split
        if case.get("family") != "practice_feedback":
            raise ValueError("Only practice-feedback cases may enter this runner")
        source, draft, attempts = (
            case.get("source"),
            case.get("draft"),
            case.get("attempts"),
        )
        if (
            not isinstance(source, dict)
            or not isinstance(draft, dict)
            or not isinstance(attempts, list)
        ):
            raise ValueError(f"Incomplete practice case {identity}")
        if draft.get("kind") not in SUPPORTED_KINDS or draft.get("source") != source.get("locator"):
            raise ValueError(f"Practice source or kind is invalid in {identity}")
        if source.get("title") not in OFFICIAL_BOOKS or not source.get("support_quote"):
            raise ValueError(f"Official source support is missing in {identity}")
        if not isinstance(source.get("physical_pdf_page"), int) or source["physical_pdf_page"] <= 0:
            raise ValueError(f"A physical PDF page is required in {identity}")
        if not attempts or attempts[-1].get("expected_rule_outcome") != "correct":
            raise ValueError(f"A paired correction sequence is required in {identity}")
        if attempts[0].get("expected_rule_outcome") == "correct":
            raise ValueError(
                f"The first probe must check an incorrect or partial attempt in {identity}"
            )
        if any(
            not isinstance(a.get("response"), dict)
            or a.get("expected_rule_outcome")
            not in {"correct", "partial", "incorrect", "insufficient", "irrelevant"}
            for a in attempts
        ):
            raise ValueError(f"Attempt contract is invalid in {identity}")
        if draft["kind"] == "step" and any(
            a.get("step") != a["response"].get("step") for a in attempts
        ):
            raise ValueError(f"Step number mismatch in {identity}")
    return data


class ZeroProviderPreflightBlocked(ValueError):
    """No API was initialized; callers may retain this accurate blocked receipt."""

    def __init__(self, blocked_ids, scheduled_cases):
        self.receipt = {
            "status": "blocked",
            "execution_policy": EXECUTION_POLICY,
            "scheduled_cases": scheduled_cases,
            "blocked_case_ids": blocked_ids,
            "submitted_http_requests": 0,
            "provider_calls": None,
            "provider_cost_usd": None,
        }
        super().__init__(
            "Zero-provider study rejects model-assessed or unverified text cases: "
            + ", ".join(blocked_ids)
            + ". Create a new source-pinned study for the current assessor flow; "
            "do not rewrite historical freezes or receipts."
        )


def require_zero_provider_catalogue(catalogue):
    """Reject every model-assessed lane before API login or any mutable request."""
    blocked = []
    for case in catalogue["cases"]:
        draft = case["draft"]
        if draft["kind"] == "short":
            blocked.append(case["id"])
        elif draft["kind"] == "step":
            rubric = draft.get("rubric")
            steps = rubric.get("steps") if isinstance(rubric, dict) else None
            if (
                not isinstance(steps, list)
                or not steps
                or any(
                    not isinstance(step, dict)
                    or not isinstance(step.get("numeric"), dict)
                    or not step["numeric"]
                    for step in steps
                )
            ):
                blocked.append(case["id"])
    if blocked:
        raise ZeroProviderPreflightBlocked(blocked, len(catalogue["cases"]))


class Api:
    def __init__(self, base_url: str, email: str, password: str):
        self.client = httpx.Client(base_url=base_url.rstrip("/") + "/api/v1", timeout=45)
        response = self.client.post("/auth/login", json={"email": email, "password": password})
        response.raise_for_status()
        self.client.headers["Authorization"] = "Bearer " + response.json()["data"]["access_token"]

    def close(self) -> None:
        self.client.close()

    def request(
        self, method: str, path: str, body: dict | None = None, expected: int = 200
    ) -> dict:
        response = self.client.request(method, path, json=body)
        if response.status_code != expected:
            raise RuntimeError(
                f"{method} {path}: HTTP {response.status_code}; code={self._error_code(response)}"
            )
        return response.json()["data"]

    @staticmethod
    def _error_code(response: httpx.Response) -> str:
        try:
            return str(response.json().get("error", {}).get("code", "unknown"))
        except (json.JSONDecodeError, TypeError, AttributeError):
            return "unparseable_response"


def official_source_audit(admin: Api, catalogue: dict) -> dict:
    books = {row["title"]: row for row in admin.request("GET", "/learning/library")}
    observed_release_ids: set[str] = set()
    source_rows = []
    for case in catalogue["cases"]:
        source = case["source"]
        book = books.get(source["title"])
        if book is None or book["source_sha256"] != OFFICIAL_BOOKS[source["title"]]:
            raise ValueError(f"Official PDF hash mismatch in {case['id']}")
        if (
            book["id"] != source["locator"]["document_id"]
            or book["release_id"] != source["locator"]["release_id"]
        ):
            raise ValueError(f"Released book identity mismatch in {case['id']}")
        url = urlsplit(book["source_url"])
        if url.scheme != "https" or url.hostname != "assets.openstax.org":
            raise ValueError(f"Official URL mismatch in {case['id']}")
        if not book["license"] or book["license"] == "Not specified":
            raise ValueError(f"Book license absent in {case['id']}")
        unit_id = source["locator"]["source_unit_id"]
        page = admin.request(
            "GET",
            f"/learning/library/{book['id']}/units?source_unit_id={unit_id}&limit=1",
        )
        unit = next((row for row in page["items"] if row["id"] == unit_id), None)
        if unit is None or unit["locator"] != source["locator"]:
            raise ValueError(f"Released source unit is unavailable in {case['id']}")
        if (
            unit["page"] != source["physical_pdf_page"]
            or unit["section"] != source["section"]
            or sha256(unit["text"].encode("utf-8")) != source["locator"]["text_hash"]
            or source["support_quote"].casefold() not in unit["text"].casefold()
        ):
            raise ValueError(f"Source text, page or quote mismatch in {case['id']}")
        observed_release_ids.add(book["release_id"])
        source_rows.append(
            {
                "id": case["id"],
                "title": book["title"],
                "edition": book["edition"],
                "source_url": book["source_url"],
                "license": book["license"],
                "original_pdf_sha256": book["source_sha256"],
                "source_unit_id": unit_id,
                "unit_text_sha256": source["locator"]["text_hash"],
                "physical_pdf_page": unit["page"],
                "section": unit["section"],
            }
        )
    if len(observed_release_ids) != 1:
        raise ValueError("All cases must use one published corpus release")
    return {
        "release_id": observed_release_ids.pop(),
        "verified_source_units": len(source_rows),
        "sources": source_rows,
    }


def freeze(
    catalogue_path: Path,
    output: Path,
    base_url: str,
    admin_email: str,
    admin_password: str,
    package_zip: Path,
) -> dict:
    if output.exists():
        raise FileExistsError("A frozen practice study cannot be overwritten")
    catalogue = load_catalogue(catalogue_path)
    require_zero_provider_catalogue(catalogue)
    admin = Api(base_url, admin_email, admin_password)
    try:
        audit = official_source_audit(admin, catalogue)
    finally:
        admin.close()
    if not package_zip.is_file():
        raise FileNotFoundError("The exact runnable package archive is required")
    manifest = {
        "schema": FREEZE_SCHEMA,
        "execution_policy": EXECUTION_POLICY,
        "frozen_at_utc": timestamp(),
        "catalogue_sha256": sha256(catalogue_path.read_bytes()),
        "runner_sha256": sha256(Path(__file__).read_bytes()),
        "package_archive_name": package_zip.name,
        "package_archive_sha256": sha256_file(package_zip),
        "source_audit": audit,
        "planned": {
            split: {
                "cases": sum(c["split"] == split for c in catalogue["cases"]),
                "attempts": sum(
                    len(c["attempts"]) for c in catalogue["cases"] if c["split"] == split
                ),
            }
            for split in sorted(ALLOWED_SPLITS)
        },
        "pilot_gate": {
            "publication_and_source": "all_cases",
            "answer_key_isolation": "all_cases",
            "rule_concordance": "all_attempts",
            "unresolved_http_failures": 0,
        },
        "semantic_solvability_status": "author_review_only;independent_human_review_pending",
        "provider_calls_budget": 0,
        "cost_usd_expected": 0,
    }
    output.mkdir(parents=True)
    (output / "catalogue.json").write_bytes(catalogue_path.read_bytes())
    exclusive_write(output / "manifest.json", manifest)
    return manifest


def _mutate_with_reservation(
    api: Api,
    run_dir: Path,
    request_id: str,
    method: str,
    path: str,
    body: dict,
    expected: int = 200,
) -> tuple[dict, float]:
    reservation = run_dir / "reservations" / f"{request_id}.json"
    exclusive_write(
        reservation,
        {
            "request_id": request_id,
            "method": method,
            "path": path,
            "body_sha256": sha256(stable_json(body)),
            "reserved_at_utc": timestamp(),
        },
    )
    started = time.perf_counter()
    result = api.request(method, path, body, expected)
    elapsed = time.perf_counter() - started
    exclusive_write(
        run_dir / "terminals" / f"{request_id}.json",
        {
            "request_id": request_id,
            "status": "succeeded",
            "completed_at_utc": timestamp(),
            "elapsed_s": round(elapsed, 6),
        },
    )
    return result, elapsed


def _assert_no_key(public: dict, admin_item: dict) -> None:
    exposed = json.dumps(public, ensure_ascii=False, sort_keys=True)
    if "correct_option_ids" in exposed or "rubric" in exposed or "acceptable_answers" in exposed:
        raise ValueError("A learner-facing item contains grading-key fields")
    explanation = admin_item["rubric"]["explanation"]
    if explanation in exposed:
        raise ValueError("A learner-facing item contains the private explanation")


def pilot_go_decision(run: dict, manifest: dict) -> bool:
    pilot = manifest["planned"]["pilot"]
    return (
        run["split"] == "pilot"
        and run["terminal_cases"] == pilot["cases"]
        and run["terminal_attempts"] == pilot["attempts"]
        and run["source_and_publication_passed"] == pilot["cases"]
        and run["answer_key_isolation_passed"] == pilot["cases"]
        and run["rule_concordant_attempts"] == pilot["attempts"]
        and run["http_failures"] == 0
    )


def execute(
    frozen_dir: Path,
    split: str,
    run_dir: Path,
    base_url: str,
    admin_email: str,
    admin_password: str,
    *,
    pilot_run_path: Path | None = None,
) -> dict:
    if split not in ALLOWED_SPLITS or run_dir.exists():
        raise ValueError("Choose a fresh run directory and a registered split")
    manifest_path, catalogue_path = (
        frozen_dir / "manifest.json",
        frozen_dir / "catalogue.json",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema") != FREEZE_SCHEMA
        or manifest.get("execution_policy") != EXECUTION_POLICY
    ):
        raise ValueError(
            "Unsupported legacy practice freeze. Create a new v2 zero-provider study; "
            "do not rewrite historical freezes or receipts."
        )
    if (
        sha256(catalogue_path.read_bytes()) != manifest["catalogue_sha256"]
        or sha256(Path(__file__).read_bytes()) != manifest["runner_sha256"]
    ):
        raise ValueError("Practice freeze, catalogue or runner has changed")
    catalogue = load_catalogue(catalogue_path)
    require_zero_provider_catalogue(catalogue)
    selected = [row for row in catalogue["cases"] if row["split"] == split]
    if len(selected) != manifest["planned"][split]["cases"]:
        raise ValueError("Frozen planned case count changed")
    if split == "reserved":
        if pilot_run_path is None:
            raise ValueError("A terminal pilot is required before reserved execution")
        pilot_run = json.loads(pilot_run_path.read_text(encoding="utf-8"))
        pilot_identity = {
            "schema": RUN_SCHEMA,
            "execution_policy": EXECUTION_POLICY,
            "frozen_manifest_sha256": sha256(manifest_path.read_bytes()),
            "catalogue_sha256": manifest["catalogue_sha256"],
            "candidate_archive_sha256": manifest["package_archive_sha256"],
        }
        if not isinstance(pilot_run, dict) or any(
            pilot_run.get(field) != expected for field, expected in pilot_identity.items()
        ):
            raise ValueError(
                "Pilot receipt lineage does not match this v2 frozen study. "
                "Complete its own pilot; do not reuse or rewrite historical receipts."
            )
        if not pilot_go_decision(pilot_run, manifest):
            raise ValueError("The preregistered pilot gate did not pass")
    run_dir.mkdir(parents=True)
    exclusive_write(
        run_dir / "run-start.json",
        {
            "schema": RUN_SCHEMA,
            "split": split,
            "manifest_sha256": sha256(manifest_path.read_bytes()),
            "started_at_utc": timestamp(),
        },
    )
    admin = Api(base_url, admin_email, admin_password)
    student: Api | None = None
    student_id: str | None = None
    student_version: int | None = None
    published: dict[str, int] = {}
    outcomes: list[dict] = []
    fatal: str | None = None
    try:
        fresh_audit = official_source_audit(admin, catalogue)
        if fresh_audit != manifest["source_audit"]:
            raise ValueError("Published official-source identity changed after freeze")
        email = f"practice-study-{split}-{uuid4().hex[:12]}@example.com"
        password = secrets.token_urlsafe(30)
        account, _ = _mutate_with_reservation(
            admin,
            run_dir,
            "student-create",
            "POST",
            "/admin/users",
            {
                "email": email,
                "full_name": "Isolated Practice Study Student",
                "password": password,
                "role": "student",
            },
            201,
        )
        student_id, student_version = account["id"], account["version"]
        student = Api(base_url, email, password)
        for case in selected:
            cid = case["id"]
            item_id = None
            case_record: dict[str, Any] = {
                "id": cid,
                "kind": case["draft"]["kind"],
                "concept_group": case["concept_group"],
                "physical_pdf_page": case["source"]["physical_pdf_page"],
                "source_title": case["source"]["title"],
                "attempts": [],
                "publication_ok": False,
                "key_isolated": False,
            }
            outcomes.append(case_record)
            created, create_s = _mutate_with_reservation(
                admin,
                run_dir,
                cid + "-draft",
                "POST",
                "/admin/learning/practice",
                case["draft"],
                201,
            )
            item_id = created["item"]["id"]
            validated, validate_s = _mutate_with_reservation(
                admin,
                run_dir,
                cid + "-validate",
                "POST",
                f"/admin/learning/practice/{item_id}/validate",
                {},
            )
            if validated["state"] != "validated":
                raise ValueError(
                    f"Study item failed structural validation: {cid}: {validated['validation_details'].get('issues')}"
                )
            published_item, publish_s = _mutate_with_reservation(
                admin,
                run_dir,
                cid + "-publish",
                "POST",
                f"/admin/learning/practice/{item_id}/publish",
                {
                    "expected_version": validated["version"],
                    "confirm_source_and_solvability": True,
                },
            )
            if published_item["state"] != "published":
                raise ValueError(f"Study item failed publication: {cid}")
            published[item_id] = published_item["version"]
            case_record["publication_ok"] = True
            case_record["admin_latency_s"] = round(create_s + validate_s + publish_s, 6)
            public = student.request("GET", f"/learning/practice/{item_id}")
            _assert_no_key(public, published_item)
            case_record["key_isolated"] = True
            if public["source"] != case["source"]["locator"]:
                raise ValueError(f"Public source locator changed: {cid}")
            for ordinal, test in enumerate(case["attempts"], 1):
                progress = student.request("GET", f"/learning/practice/{item_id}/progress")
                payload = {
                    "idempotency_key": str(uuid4()),
                    "expected_version": progress["version"],
                    "response": test["response"],
                }
                result, elapsed = _mutate_with_reservation(
                    student,
                    run_dir,
                    f"{cid}-attempt-{ordinal}",
                    "POST",
                    f"/learning/practice/{item_id}/attempts",
                    payload,
                )
                feedback = result["feedback"]
                case_record["attempts"].append(
                    {
                        "ordinal": ordinal,
                        "expected_rule_outcome": test["expected_rule_outcome"],
                        "observed_outcome": feedback["outcome"],
                        "rule_concordant": feedback["outcome"] == test["expected_rule_outcome"],
                        "feedback": feedback,
                        "response": test["response"],
                        "elapsed_s": round(elapsed, 6),
                        "step_before": progress["current_step"],
                        "step_after": student.request(
                            "GET", f"/learning/practice/{item_id}/progress"
                        )["current_step"],
                        "grading_method": feedback.get("grading_method"),
                        "probe": test.get("probe", "paired"),
                    }
                )
            final_progress = student.request("GET", f"/learning/practice/{item_id}/progress")
            case_record["completed"] = final_progress["state"] == "completed"
            case_record["review_created_after_incorrect"] = any(
                row["item_id"] == item_id
                for row in student.request("GET", "/learning/review?due_only=false")
            )
            retired, _ = _mutate_with_reservation(
                admin,
                run_dir,
                cid + "-retire",
                "POST",
                f"/admin/learning/practice/{item_id}/retire",
                {"expected_version": published[item_id]},
            )
            if retired["state"] != "retired":
                raise ValueError(f"Published practice item was not retired: {cid}")
            del published[item_id]
            exclusive_write(run_dir / "case-terminals" / f"{cid}.json", case_record)
    except Exception as exc:
        fatal = f"{type(exc).__name__}: {exc}"
    finally:
        for item_id, version in list(published.items()):
            try:
                admin.request(
                    "POST",
                    f"/admin/learning/practice/{item_id}/retire",
                    {"expected_version": version},
                )
                del published[item_id]
            except Exception:
                pass
        if student is not None:
            student.close()
        if student_id is not None and student_version is not None:
            try:
                admin.request(
                    "PATCH",
                    f"/admin/users/{student_id}",
                    {"version": student_version, "status": "deactivated"},
                )
            except Exception:
                if fatal is None:
                    fatal = "Dedicated study student could not be deactivated"
        admin.close()
    summary = {
        "schema": RUN_SCHEMA,
        "split": split,
        "frozen_manifest_sha256": sha256(manifest_path.read_bytes()),
        "catalogue_sha256": manifest["catalogue_sha256"],
        "candidate_archive_sha256": manifest["package_archive_sha256"],
        "corpus_release_id": manifest["source_audit"]["release_id"],
        "scheduled_cases": len(selected),
        "terminal_cases": sum(
            (run_dir / "case-terminals" / f"{c['id']}.json").is_file() for c in selected
        ),
        "scheduled_attempts": sum(len(c["attempts"]) for c in selected),
        "terminal_attempts": sum(len(row["attempts"]) for row in outcomes),
        "source_and_publication_passed": sum(bool(row["publication_ok"]) for row in outcomes),
        "answer_key_isolation_passed": sum(bool(row["key_isolated"]) for row in outcomes),
        "rule_concordant_attempts": sum(
            sum(a["rule_concordant"] for a in row["attempts"]) for row in outcomes
        ),
        "completed_practice_items": sum(bool(row.get("completed")) for row in outcomes),
        "review_entries_created": sum(
            bool(row.get("review_created_after_incorrect")) for row in outcomes
        ),
        "outcomes": dict(
            Counter(a["observed_outcome"] for row in outcomes for a in row["attempts"])
        ),
        "kinds": dict(Counter(row["kind"] for row in outcomes)),
        "unretired_item_count": len(published),
        "http_failures": 1 if fatal else 0,
        "fatal_error": fatal,
        "execution_policy": EXECUTION_POLICY,
        "provider_calls": None,
        "provider_cost_usd": None,
        "provider_usage_status": "backend_transport_not_observed",
        "human_reviews_completed": 0,
        "semantic_solvability_verified_independently": False,
        "educational_effect_measured": False,
        "case_records": outcomes,
        "finished_at_utc": timestamp(),
    }
    exclusive_write(run_dir / "summary.json", summary)
    return summary
