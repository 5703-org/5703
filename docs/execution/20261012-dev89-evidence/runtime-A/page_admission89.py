"""Public-only finite DEV89 page admission; no authentication or process calls."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re

AUTHORIZATION = "parent_dev89_independent32posts_2USD_quality_pages_20261012"
BASE_CASES = frozenset({"case01", "case03", "case04", "case05", "case06", "case07", "case08", "case09",
                        "case01r", "case03r", "case04r", "case05r"})
PAGE_CASES = frozenset({"case10", "case10b", "case10c"})
MAIN = Path(r"E:\5703\learning-assistant")
DESCRIPTOR_KEYS = frozenset({
    "schema", "authorization", "instance_id", "kind", "base_case_id", "protocol_sha256",
    "question_id", "question_sha256", "base_scope_sha256", "base_source_version_sha256",
    "instance_source_version_sha256", "base_final_receipt_sha256", "base_api_closure_sha256",
    "qa_receipt_path", "qa_receipt_sha256", "actual_answer_sha256", "root_selected_authorized",
    "automatic_replay_or_reclaim", "repair_review_path", "repair_review_sha256", "base_journey_receipt_sha256",
})
QA_FLAGS = frozenset({"scientific_correctness", "coverage_complete", "citations_valid",
    "own_parent_sources_valid", "full_source_packet_reviewed", "no_scientific_critical_error"})
QA_KEYS = frozenset({"schema", "status", "independent_answer_QA", "case_id", "question_sha256",
    "scope_sha256", "source_version_sha256", "teacher_config_sha256", "checker_config_sha256",
    "output_policy", "actual_ids", "actual_journey_sha256", "raw_public_DTO_sha256",
    "answer_text_sha256_UTF8", "clock", "flags", "actual_page_response_requires_independent_review_again",
    "actual_page_latency_sample_qualified"})
OLD_METADATA_GROUPS = frozenset({"sessions", "jobs", "answer_requests", "answers", "active_model_configurations"})


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8"))


def pairs(values):
    result = {}
    for key, value in values:
        require(key not in result, "DUPLICATE_PUBLIC_JSON_KEY")
        result[key] = value
    return result


def public_path(root, relative, *, exists=True):
    root = Path(os.path.abspath(root))
    require(root.resolve(strict=True) == root and not root.is_symlink(), "PUBLIC_RUNTIME_REDIRECTED")
    relative = Path(relative)
    require(not relative.is_absolute() and not relative.drive and ".." not in relative.parts,
            "PUBLIC_METADATA_PATH_FORBIDDEN")
    path = root / relative
    current = path
    while current != root:
        require(not current.is_symlink() and not getattr(current, "is_junction", lambda: False)(),
                "PUBLIC_METADATA_PATH_REDIRECTED")
        current = current.parent
    require(path.resolve(strict=exists) == path, "PUBLIC_METADATA_PATH_REDIRECTED")
    return path


def read_public(root, relative, *, max_bytes=2_000_000):
    path = public_path(root, relative)
    require(path.is_file() and path.stat().st_size <= max_bytes, "PUBLIC_METADATA_SIZE_OR_TYPE")
    raw = path.read_bytes()
    require(len(raw) <= max_bytes, "PUBLIC_METADATA_SIZE_OR_TYPE")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError("NONFINITE_PUBLIC_METADATA")))
    require(type(value) is dict, "PUBLIC_METADATA_OBJECT_REQUIRED")
    return value, sha(raw)


def same_product_settings(runtime, base, page):
    left, right = base.get("expected_settings"), page.get("expected_settings")
    if type(left) is not dict or type(right) is not dict:
        return False
    left, right = dict(left), dict(right)
    for key, leaf in (("storage_root", "storage"), ("visual_catalog_staging_root", "visual-staging")):
        if left.pop(key, None) != str(runtime / base["case_id"] / leaf):
            return False
        if right.pop(key, None) != str(runtime / page["case_id"] / leaf):
            return False
    return left == right


def verify_main_version(source_pins):
    require(type(source_pins) is list and bool(source_pins), "EXACT_MAIN_VERSION_REQUIRED")
    seen = set()
    for row in source_pins:
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "MAIN_PIN_SHAPE")
        path = Path(row["path"])
        require(path.resolve(strict=True).is_relative_to(MAIN.resolve(strict=True))
                and not path.is_symlink() and path not in seen, "MAIN_PIN_PATH_OR_DUPLICATE")
        seen.add(path)
        raw = path.read_bytes()
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "CURRENT_MAIN_VERSION_CHANGED")


def frozen_profile(protocol, scope):
    teacher, checker = protocol["expected_model_config"], protocol["expected_checker_config"]
    settings = protocol["frozen_settings"]
    require(type(settings) is dict and "storage_root" not in settings
            and "visual_catalog_staging_root" not in settings, "FROZEN_SETTINGS_REQUIRED")
    profile_sha = digest({"teacher": teacher, "checker": checker, "settings": settings})
    scope_settings = dict(scope["expected_settings"])
    scope_settings.pop("storage_root", None)
    scope_settings.pop("visual_catalog_staging_root", None)
    require(profile_sha == protocol["base_config_sha256"] == scope["phase89_frozen_profile_sha256"]
            and scope["expected_model_config"] == teacher and scope["expected_checker_config"] == checker
            and scope_settings == settings, "FROZEN_PRODUCT_PROFILE_CHANGED")


def validate_page(runtime, instance_id, expected_scope_sha, expected_protocol_sha, *, require_empty=True):
    """Read one new page's public descriptor and exact independently reviewed base."""
    runtime = Path(os.path.abspath(runtime))
    require(runtime.name == "5703-dev89-runtime" and instance_id in PAGE_CASES,
            "NEW_FINITE_DEV89_PAGE_REQUIRED")
    require(all(type(pin) is str and re.fullmatch(r"[0-9a-f]{64}", pin)
                for pin in (expected_scope_sha, expected_protocol_sha)), "EXPLICIT_PAGE_PINS_REQUIRED")
    case = public_path(runtime, instance_id)
    require(case.is_dir() and (not require_empty or not any(case.iterdir())), "PRESERVE_PRIOR_PAGE_ARTIFACTS")
    freeze, _ = read_public(runtime, "runtime-freeze88.json")
    protocol, protocol_sha = read_public(runtime, "protocol88.json")
    pin, _ = read_public(runtime, f"scope88-{instance_id}-pin.json")
    scope, scope_sha = read_public(runtime, f"scope88-{instance_id}.json", max_bytes=256_000)
    descriptor, descriptor_sha = read_public(runtime, f"supplement88-{instance_id}.json")
    require(protocol_sha == expected_protocol_sha == freeze.get("protocol_sha256")
            == pin.get("protocol_sha256") == scope.get("cohort_protocol_sha256")
            == descriptor.get("protocol_sha256")
            and protocol.get("schema") == "dev89_bound_development_validation_v1"
            and protocol.get("authorization") == AUTHORIZATION
            and protocol.get("maximum_physical_posts") == 32 and protocol.get("cost_cap_USD") == "2.00"
            and protocol.get("per_request_provider_calls_maximum") == 4, "EXACT_DEV89_PROTOCOL_REQUIRED")
    plan = protocol.get("planned_instances")
    require(type(plan) is list and all(type(row) is dict and set(row) ==
        {"instance_id", "kind", "base_case_id", "maximum_posts"} for row in plan), "FINITE_INSTANCE_PLAN_REQUIRED")
    selected = [row for row in plan if row["instance_id"] == instance_id]
    require(len(selected) == 1 and selected[0]["kind"] == "page" and selected[0]["base_case_id"] is None
            and selected[0]["maximum_posts"] == 4, "PLANNED_PAGE_ONLY")
    require(set(descriptor) == DESCRIPTOR_KEYS
            and descriptor.get("schema") == "dev89_planned_instance_descriptor_v1"
            and descriptor.get("authorization") == AUTHORIZATION and descriptor.get("instance_id") == instance_id
            and descriptor.get("kind") == "quality_qualified_page" and descriptor.get("base_case_id") in BASE_CASES
            and descriptor.get("repair_review_path") is None and descriptor.get("repair_review_sha256") is None
            and descriptor.get("root_selected_authorized") is True
            and descriptor.get("automatic_replay_or_reclaim") is False, "STRICT_PLANNED_PAGE_DESCRIPTOR_REQUIRED")
    require(scope_sha == expected_scope_sha == pin.get("scope_sha256")
            and pin.get("case_id") == scope.get("case_id") == instance_id
            and scope.get("phase88_authorization") == AUTHORIZATION
            and scope.get("phase88_case_execution_authorized") is True
            and scope.get("continuation_phase") == "dev89" and scope.get("phase89_planned_kind") == "page"
            and scope.get("page_answer_requires_independent_quality_review") is True
            and scope.get("supplement_descriptor_sha256") == descriptor_sha, "EXACT_NEW_PAGE_SCOPE_REQUIRED")
    question = scope.get("question_text")
    require(type(question) is str and 1 <= len(question) <= 7200
            and sha(question.encode("utf-8")) == scope.get("question_sha256") == descriptor.get("question_sha256")
            and scope.get("question_id") == descriptor.get("question_id"), "PUBLIC_QUESTION_BINDING_REQUIRED")
    base_id = descriptor["base_case_id"]
    base, base_sha = read_public(runtime, f"scope88-{base_id}.json", max_bytes=256_000)
    journey, journey_sha = read_public(runtime, f"{base_id}/journey-receipt88.json")
    final, final_sha = read_public(runtime, f"{base_id}/native-provider70/final-receipt.json")
    closure, closure_sha = read_public(runtime, f"{base_id}/api-closure77.json")
    version = digest(scope.get("source_pins"))
    require(base_sha == descriptor["base_scope_sha256"] and base.get("case_id") == base_id
            and base.get("question_text") == question and base.get("question_sha256") == scope["question_sha256"]
            and base.get("source_pins") == scope.get("source_pins")
            and version == descriptor["base_source_version_sha256"] == descriptor["instance_source_version_sha256"]
            and base.get("expected_model_config") == scope.get("expected_model_config")
            and base.get("expected_checker_config") == scope.get("expected_checker_config")
            and same_product_settings(runtime, base, scope)
            and scope.get("page_base_teacher_config_sha256") == digest(base["expected_model_config"])
            and scope.get("page_base_checker_config_sha256") == digest(base["expected_checker_config"]),
            "EXACT_QUALIFIED_BASE_VERSION_REQUIRED")
    frozen_profile(protocol, scope)
    require(final_sha == descriptor["base_final_receipt_sha256"]
            and closure_sha == descriptor["base_api_closure_sha256"]
            and journey_sha == descriptor["base_journey_receipt_sha256"]
            and final.get("case_id") == base_id and final.get("closure_status") == "CLOSED_NUMERIC_NO_UNKNOWN"
            and type(final.get("actual_posts")) is int and 1 <= final["actual_posts"] <= 4
            and type(final.get("settled_numeric_cost_observations")) is int
            and final.get("settled_numeric_cost_observations") == final["actual_posts"]
            and closure.get("owned_threads_closed") is True
            and type(closure.get("old_metadata_unchanged")) is dict
            and set(closure["old_metadata_unchanged"]) == OLD_METADATA_GROUPS
            and all(value is True for value in closure["old_metadata_unchanged"].values()), "CLOSED_NUMERIC_BASE_REQUIRED")
    known = Decimal(str(final.get("native_settled_known_cost_USD")))
    unknown = Decimal(str(final.get("native_unresolved_full_protection_USD")))
    require(known.is_finite() and known >= 0 and unknown.is_finite() and unknown == 0,
            "NUMERIC_BASE_COST_WITH_NO_UNKNOWN_REQUIRED")
    response = journey.get("response")
    require(journey.get("status") == "API_COMPLETED" and type(journey.get("API_n")) is int
            and type(journey.get("completed_answer_n")) is int
            and journey.get("API_n") == journey.get("completed_answer_n") == 1
            and journey.get("case_id") == base_id and journey.get("question_sha256") == scope["question_sha256"]
            and journey.get("scope_sha256") == base_sha and type(response) is dict
            and response.get("response_type") == "answer" and type(response.get("answer_text")) is str
            and bool(response["answer_text"].strip()) and digest(response) == descriptor["actual_answer_sha256"]
            == scope.get("page_base_public_DTO_sha256"),
            "ACTUAL_COMPLETE_BASE_ANSWER_REQUIRED")
    qa, qa_sha = read_public(runtime, descriptor["qa_receipt_path"])
    actual_ids = {"session_id": journey.get("session_id"), "answer_id": journey.get("answer_id"),
        **{key: journey.get("accepted", {}).get(key) for key in ("request_id", "job_id", "user_message_id")}}
    expected_clock = {key: journey.get(key) for key in ("started_utc", "finished_utc", "api_send_to_complete_response_ms")}
    require(set(qa) == QA_KEYS and qa_sha == descriptor["qa_receipt_sha256"]
            and qa.get("schema") == "dev89_independent_actual_answer_eligibility_v1"
            and qa.get("status") == qa.get("independent_answer_QA") == "PASS" and qa.get("case_id") == base_id
            and qa.get("question_sha256") == scope["question_sha256"] and qa.get("scope_sha256") == base_sha
            and qa.get("source_version_sha256") == version
            and qa.get("teacher_config_sha256") == digest(base["expected_model_config"])
            and qa.get("checker_config_sha256") == digest(base["expected_checker_config"])
            and qa.get("output_policy") == base["expected_settings"]["chat_checker_output_policy"]
            and qa.get("actual_ids") == actual_ids and all(type(value) is str and bool(value) for value in actual_ids.values())
            and qa.get("actual_journey_sha256") == journey_sha
            and qa.get("raw_public_DTO_sha256") == digest(response)
            and qa.get("answer_text_sha256_UTF8") == sha(response["answer_text"].encode("utf-8"))
            and qa.get("clock") == expected_clock and type(qa.get("clock")) is dict
            and type(qa["clock"].get("api_send_to_complete_response_ms"))
                is type(expected_clock["api_send_to_complete_response_ms"])
            and type(qa.get("flags")) is dict
            and set(qa["flags"]) == QA_FLAGS and all(value is True for value in qa["flags"].values())
            and qa.get("actual_page_response_requires_independent_review_again") is True
            and qa.get("actual_page_latency_sample_qualified") is False, "INDEPENDENT_EXACT_BASE_ANSWER_QA_REQUIRED")
    duration = expected_clock["api_send_to_complete_response_ms"]
    require(type(duration) in (int, float) and math.isfinite(duration) and duration > 0,
            "COMPLETE_BASE_API_CLOCK_REQUIRED")
    times = [datetime.fromisoformat(expected_clock[key].replace("Z", "+00:00"))
             for key in ("started_utc", "finished_utc")]
    require(all(value.tzinfo is not None for value in times) and times[1] >= times[0], "BASE_CLOCK_ORDER_REQUIRED")
    verify_main_version(scope["source_pins"])
    runtime_pins = {}
    for filename in ("server88.py", "normal_transport88.py", "targeted_answer88.py", "budget88.py",
                     "journey88.cjs", "completion-observer88.cjs", "vite.config88.mjs", "page_admission89.py"):
        runtime_pins[filename] = sha(public_path(runtime, filename).read_bytes())
    return {"case": case, "scope": scope, "descriptor": descriptor, "scope_sha256": scope_sha,
            "descriptor_sha256": descriptor_sha, "qa_sha256": qa_sha, "runtime_pins": runtime_pins,
            "protocol_sha256": protocol_sha}
