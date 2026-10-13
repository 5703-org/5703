"""Independent Phase89 32-POST/$2 ledger; historical instance admissions are forbidden."""
from __future__ import annotations
import hashlib
import json
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from datetime import datetime
AUTHORIZATION = 'parent_dev89_independent32posts_2USD_quality_pages_20261012'
POST_CAP = 32
CASE_CAP = 8
CASE_POST_CAP = 4
NONPAGE_POST_CAP = 24
MAX_WIRE_BYTES = 200000
MARKER = 'cohort-claim.json'
STOP_MARKER = 'cohort-stop.json'
BASE_CASES = {'case07', 'case03', 'case08', 'case05', 'case09', 'case01', 'case06', 'case04'}
AUX_CASES = {'case05r', 'case04r', 'case01r', 'case03r'}
PAGE_CASES = {'case10', 'case10b', 'case10c'}
ALL_CASES = {'case10c', 'case07', 'case03r', 'case03', 'case08', 'case05', 'case09', 'case01', 'case06', 'case04r', 'case10b', 'case05r', 'case04', 'case01r', 'case10'}
_SUPPLEMENTS = {'case05r', 'case10c', 'case10b', 'case01r', 'case03r', 'case10', 'case04r'}
FRESH_CASES = set()
FRESH_PUBLIC_PINS = {}
FROZEN_BASE_SOURCE_VERSION_SHA256 = 'f7f03e32b3bab3f539002e53798cc5abdfc0f7816d37d78d85401eff8e1ce5d2'
FROZEN_TEACHER_CONFIG_SHA256 = '65a9f21eee75556b2dc8f34ba7cb90c7caf2f1946e6f5cc3afd7b30d7cdff013'
FROZEN_CHECKER_CONFIG_SHA256 = '03689510a0090504979274424c800a4f20eb6b159236dabdb00ad9a0eac0f09c'
FROZEN_SETTINGS_SHA256 = '2253514d03713fdadf3637fb5ba5058b9848af6af21531de7e77dd7c84d968de'
_OLD_METADATA_KEYS = {'active_model_configurations', 'sessions', 'jobs', 'answer_requests', 'answers'}
STOP_CODES = {'UNSAFE_LOCAL_CONTROLLER', 'ROOT_QA_COHORT_STOP', 'UNSAFE_NORMAL_TRANSPORT', 'ROOT_QA_CRITICAL_UNSUPPORTED_FACT', 'UNSAFE_NORMAL_TARGET'}
_QUALITY_STOP_CODES = {'ROOT_QA_COHORT_STOP', 'ROOT_QA_CRITICAL_UNSUPPORTED_FACT'}
HOLD = Decimal("0.0714688")
COST_CAP = Decimal("2.00")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_POST_FILE = re.compile(r"post-(0[1-9]|[12][0-9]|3[0-2])-(claim|settlement|exposure)\.json\Z")

_NEXT_STEPS = {
    None: frozenset({("teacher", "generation")}),
    ("teacher", "generation"): frozenset({
        ("teacher", "generation_format_repair"), ("checker", "joint_check"),
    }),
    ("teacher", "generation_format_repair"): frozenset({("checker", "joint_check")}),
    ("checker", "joint_check"): frozenset({
        ("checker", "checker_contract_repair"), ("teacher", "semantic_repair"),
    }),
    ("checker", "checker_contract_repair"): frozenset({("teacher", "semantic_repair")}),
    ("teacher", "semantic_repair"): frozenset({
        ("teacher", "generation_format_repair"), ("checker", "joint_recheck"),
    }),
    ("checker", "joint_recheck"): frozenset(),
}


def _next_steps(previous, semantic_repair_seen):
    if previous == ("teacher", "generation_format_repair"):
        purpose = "joint_recheck" if semantic_repair_seen else "joint_check"
        return frozenset({("checker", purpose)})
    return _NEXT_STEPS[previous]


def next_step_allowed(steps, role, purpose):
    """Validate the existing role/purpose path and one bounded next Main call."""
    if (type(steps) is not list or len(steps) >= CASE_POST_CAP
            or type(role) is not str or type(purpose) is not str):
        return False
    previous, semantic_repair_seen = None, False
    for step in steps:
        if (type(step) is not dict or set(step) != {"role", "purpose"}
                or type(step["role"]) is not str or type(step["purpose"]) is not str):
            return False
        current = (step["role"], step["purpose"])
        if current not in _next_steps(previous, semantic_repair_seen):
            return False
        previous = current
        semantic_repair_seen = semantic_repair_seen or current == ("teacher", "semantic_repair")
    return (role, purpose) in _next_steps(previous, semantic_repair_seen)


class BudgetError(RuntimeError):
    """Expose a finite code rather than raw filesystem or caller data."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise BudgetError(code)


def _sha(value):
    _require(type(value) is str and _SHA.fullmatch(value), "SHA256_REQUIRED")
    return value


def _case(value):
    _require(type(value) is str and value in ALL_CASES, "FIXED_DEV89_INSTANCE_REQUIRED")
    return value

def public_digest(value):
    """Canonical digest for public source versions and complete answer objects."""
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError, OverflowError):
        raise BudgetError("PUBLIC_DIGEST_VALUE_INVALID") from None
    return hashlib.sha256(raw).hexdigest()

def _stopped(root):
    path = Path(root) / STOP_MARKER
    return path.exists() or path.is_symlink()

def _require_running(root):
    _require(not _stopped(root), "COHORT_PERMANENTLY_STOPPED")

def _amount(value):
    if type(value) not in (str, int, float, Decimal):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return amount if amount.is_finite() and amount >= 0 else None

def _root(root, *, create=False):
    root = Path(root).absolute()
    _require(root.resolve() == root and not root.is_symlink()
             and not getattr(root, "is_junction", lambda: False)(), "JOURNAL_PATH_REDIRECTED")
    if create:
        _require(root.parent.is_dir(), "JOURNAL_PARENT_REQUIRED")
        try:
            root.mkdir(exist_ok=True)
        except OSError:
            raise BudgetError("JOURNAL_DIRECTORY_UNAVAILABLE") from None
    _require(root.is_dir(), "COHORT_NOT_INITIALIZED")
    return root

def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "JOURNAL_DUPLICATE_JSON_KEY")
        result[key] = value
    return result

def _bad_constant(_value):
    raise BudgetError("JOURNAL_NONFINITE_JSON")

def _read(path):
    _require(path.is_file() and not path.is_symlink()
             and not getattr(path, "is_junction", lambda: False)(), "JOURNAL_RECORD_REQUIRED")
    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except (OSError, ValueError, UnicodeError):
        raise BudgetError("JOURNAL_RECORD_INVALID") from None
    _require(type(value) is dict, "JOURNAL_RECORD_INVALID")
    return value

def _exact(actual, expected):
    try:
        return json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(
            expected, sort_keys=True, allow_nan=False
        )
    except (TypeError, ValueError):
        return False

def _pinned_record(path, expected_pin=None):
    path = Path(path).absolute()
    _require(path.resolve() == path and path.is_file() and not path.is_symlink()
             and not getattr(path, "is_junction", lambda: False)(), "SUPPLEMENT_PUBLIC_RECORD_REQUIRED")
    try:
        raw = path.read_bytes()
    except OSError:
        raise BudgetError("SUPPLEMENT_PUBLIC_RECORD_REQUIRED") from None
    pin = hashlib.sha256(raw).hexdigest()
    if expected_pin is not None:
        _require(pin == _sha(expected_pin), "SUPPLEMENT_PUBLIC_PIN_CHANGED")
    try:
        record = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except (ValueError, UnicodeError):
        raise BudgetError("SUPPLEMENT_PUBLIC_RECORD_INVALID") from None
    _require(type(record) is dict, "SUPPLEMENT_PUBLIC_RECORD_INVALID")
    return record, pin

def _scope_binding(scope, case_id, descriptor):
    text = scope.get("question_text")
    pins = scope.get("source_pins")
    _require(scope.get("case_id") == case_id
             and scope.get("phase88_authorization") == AUTHORIZATION
             and scope.get("phase88_case_execution_authorized") is True
             and scope.get("cohort_protocol_sha256") == descriptor["protocol_sha256"]
             and scope.get("question_id") == descriptor["question_id"]
             and scope.get("question_sha256") == descriptor["question_sha256"]
             and type(text) is str and bool(text.strip())
             and hashlib.sha256(text.encode()).hexdigest() == descriptor["question_sha256"]
             and type(pins) is list and len(pins) == 16
             and all(type(row) is dict and set(row) == {"path", "bytes", "sha256"}
                     and type(row["path"]) is str and bool(row["path"])
                     and type(row["bytes"]) is int and row["bytes"] > 0
                     and type(row["sha256"]) is str and _SHA.fullmatch(row["sha256"])
                     for row in pins)
             and len({row["path"] for row in pins}) == len(pins), "SUPPLEMENT_SCOPE_BINDING_CHANGED")
    return public_digest(pins)

def _source_pins(pins):
    _require(type(pins) is list and len(pins) == 16
             and all(type(row) is dict and set(row) == {"path", "bytes", "sha256"}
                     and type(row["path"]) is str and bool(row["path"])
                     and type(row["bytes"]) is int and row["bytes"] > 0
                     and type(row["sha256"]) is str and _SHA.fullmatch(row["sha256"])
                     for row in pins)
             and len({row["path"] for row in pins}) == 16, "EXACT_SOURCE_VERSION_REQUIRED")
    return public_digest(pins)


def validate_protocol(protocol):
    """Validate the new frozen public manifest, without accepting old cohort metadata."""
    _require(type(protocol) is dict
             and protocol.get("schema") == "dev89_bound_development_validation_v1"
             and protocol.get("status") == "READY_FROZEN_PUBLIC_CASES"
             and protocol.get("authorization") == AUTHORIZATION
             and protocol.get("maximum_physical_posts") == POST_CAP
             and protocol.get("cost_cap_USD") == str(COST_CAP)
             and protocol.get("per_request_provider_calls_maximum") == CASE_POST_CAP
             and protocol.get("whole_case_seconds_cap") == 180
             and protocol.get("http_automatic_retries") is False
             and protocol.get("automatic_case_replay_or_reclaim") is False,
             "EXACT_FROZEN_DEV89_PROTOCOL_REQUIRED")
    cases = protocol.get("cases")
    case_keys = {"case_id", "question_id", "question_text", "question_sha256", "purpose", "classification"}
    _require(type(cases) is list and len(cases) == 8
             and all(type(row) is dict and set(row) == case_keys
                     and row.get("case_id") in BASE_CASES
                     and type(row.get("question_id")) is str and bool(row["question_id"].strip())
                     and type(row.get("question_text")) is str and bool(row["question_text"].strip())
                     and hashlib.sha256(row["question_text"].encode()).hexdigest() == row.get("question_sha256")
                     and row.get("purpose") == "baseline_dev"
                     and row.get("classification") in {"recurrent_error", "new_topic"} for row in cases)
             and {row["case_id"] for row in cases} == BASE_CASES
             and len({row["question_id"] for row in cases}) == 8
             and len({row["question_sha256"] for row in cases}) == 8,
             "EXACT_EIGHT_PUBLIC_DEVELOPMENT_CASES_REQUIRED")
    planned = protocol.get("planned_instances")
    _require(type(planned) is list and 10 <= len(planned) <= 15
             and all(type(row) is dict and set(row) == {"instance_id", "kind", "base_case_id", "maximum_posts"}
                     and row.get("instance_id") in ALL_CASES
                     and row.get("maximum_posts") == CASE_POST_CAP
                     and row.get("base_case_id") is None
                     and row.get("kind") == ("base" if row["instance_id"] in BASE_CASES
                         else "affected_or_control" if row["instance_id"] in AUX_CASES else "page") for row in planned)
             and len({row["instance_id"] for row in planned}) == len(planned)
             and BASE_CASES | {"case10", "case10b"} <= {row["instance_id"] for row in planned},
             "EXACT_FINITE_PLANNED_INSTANCES_REQUIRED")
    _require(_source_pins(protocol.get("source_pins")) == protocol.get("source_version_sha256")
             == FROZEN_BASE_SOURCE_VERSION_SHA256, "BASELINE_MAIN_SOURCE_VERSION_CHANGED")
    teacher, checker, settings = (protocol.get(key) for key in
        ("expected_model_config", "expected_checker_config", "frozen_settings"))
    _require(type(teacher) is dict and type(checker) is dict and type(settings) is dict
             and public_digest(teacher) == FROZEN_TEACHER_CONFIG_SHA256
             and public_digest(checker) == FROZEN_CHECKER_CONFIG_SHA256
             and public_digest(settings) == FROZEN_SETTINGS_SHA256
             and public_digest({"teacher": teacher, "checker": checker, "settings": settings})
                 == protocol.get("base_config_sha256")
             and protocol.get("default_output_policy") == settings.get("chat_checker_output_policy")
             and protocol.get("explicit_v2_allowed") is True,
             "EXACT_FROZEN_MODEL_AND_SETTINGS_REQUIRED")
    _sha(protocol.get("public_source_boundary_sha256"))
    return protocol


def _protocol_records(root, protocol_pin):
    protocol, _ = _pinned_record(Path(root).parent / "protocol88.json", protocol_pin)
    return validate_protocol(protocol)


def _planned(protocol, instance_id):
    rows = [row for row in protocol["planned_instances"] if row["instance_id"] == instance_id]
    _require(len(rows) == 1, "INSTANCE_NOT_IN_FROZEN_PLAN")
    return rows[0]


def _public_relative(runtime, relative):
    _require(type(relative) is str and bool(relative), "PUBLIC_REVIEW_PATH_REQUIRED")
    path = Path(relative)
    _require(not path.is_absolute() and not path.drive and ".." not in path.parts
             and (runtime / path).absolute().resolve().is_relative_to(runtime.resolve()),
             "PUBLIC_REVIEW_PATH_FORBIDDEN")
    return runtime / path


def _settings_match(scope, protocol, runtime, instance_id):
    actual = scope.get("expected_settings")
    _require(type(actual) is dict, "FROZEN_SETTINGS_REQUIRED")
    path_fields = {"storage_root": "storage", "visual_catalog_staging_root": "visual-staging"}
    _require(_exact({key: value for key, value in actual.items() if key not in path_fields},
                    protocol["frozen_settings"])
             and all(actual.get(key) == str(runtime / instance_id / suffix)
                     for key, suffix in path_fields.items()), "ONLY_OWNED_STORAGE_REBASE_ALLOWED")


def _fix_plan(root, protocol, protocol_pin):
    """One immutable, Root-selected common fix; original baseline source never changes."""
    plan, pin = _pinned_record(Path(root).parent / "common-fix-plan89.json")
    keys = {"schema", "authorization", "protocol_sha256", "root_selected_authorized",
            "single_common_fix", "full_batch_replay_authorized", "source_pins_before", "source_pins_after",
            "source_version_before_sha256", "source_version_after_sha256", "selected_source_paths",
            "cause_review_sha256", "instances"}
    _require(set(plan) == keys and plan.get("schema") == "dev89_single_common_fix_plan_v1"
             and plan.get("authorization") == AUTHORIZATION
             and plan.get("protocol_sha256") == protocol_pin
             and plan.get("root_selected_authorized") is True and plan.get("single_common_fix") is True
             and plan.get("full_batch_replay_authorized") is False
             and _exact(plan.get("source_pins_before"), protocol["source_pins"])
             and plan.get("source_version_before_sha256") == protocol["source_version_sha256"],
             "SINGLE_COMMON_FIX_PLAN_REQUIRED")
    _sha(plan.get("cause_review_sha256"))
    _require(_source_pins(plan.get("source_pins_after")) == plan.get("source_version_after_sha256")
             and plan["source_version_after_sha256"] != protocol["source_version_sha256"],
             "COMMON_FIX_SOURCE_VERSION_REQUIRED")
    before = {row["path"]: row for row in plan["source_pins_before"]}
    after = {row["path"]: row for row in plan["source_pins_after"]}
    changed = {path for path in before if path in after and not _exact(before[path], after[path])}
    selected = plan.get("selected_source_paths")
    _require(set(before) == set(after) and type(selected) is list and bool(selected)
             and all(type(path) is str for path in selected)
             and len(selected) == len(set(selected)) and set(selected) == changed,
             "COMMON_FIX_CHANGED_PRODUCTION_PATHS_REQUIRED")
    rows = plan.get("instances")
    _require(type(rows) is list and 2 <= len(rows) <= 4
             and all(type(row) is dict and set(row) == {"instance_id", "kind", "base_case_id", "question_sha256"}
                     and row.get("instance_id") in AUX_CASES and row.get("kind") in {"affected", "control"}
                     and row.get("base_case_id") in BASE_CASES for row in rows)
             and len({row["instance_id"] for row in rows}) == len(rows)
             and len({row["base_case_id"] for row in rows}) == len(rows)
             and any(row["kind"] == "affected" for row in rows)
             and sum(row["kind"] == "control" for row in rows) == 1, "FINITE_AFFECTED_CONTROL_PLAN_REQUIRED")
    for row in rows:
        _planned(protocol, row["instance_id"])
        base = next(case for case in protocol["cases"] if case["case_id"] == row["base_case_id"])
        _require(row["question_sha256"] == base["question_sha256"], "COMMON_FIX_QUESTION_CHANGED")
    return plan, pin


def page_quality_matches(qa, base_scope, response, *, base_scope_sha256, source_version_sha256,
                         journey, journey_sha256):
    """Bind independent scientific review to the exact saved actual API answer, not a template."""
    if not all(type(value) is dict for value in (qa, base_scope, response, journey)):
        return False
    expected_keys = {"schema", "status", "independent_answer_QA", "case_id", "question_sha256",
        "scope_sha256", "source_version_sha256", "teacher_config_sha256", "checker_config_sha256",
        "output_policy", "actual_ids", "actual_journey_sha256", "raw_public_DTO_sha256",
        "answer_text_sha256_UTF8", "clock", "flags", "actual_page_response_requires_independent_review_again",
        "actual_page_latency_sample_qualified"}
    text, accepted = response.get("answer_text"), journey.get("accepted")
    if type(text) is not str or not text.strip() or type(accepted) is not dict:
        return False
    ids = {"session_id": journey.get("session_id"), "answer_id": journey.get("answer_id"),
           **{key: accepted.get(key) for key in ("request_id", "job_id", "user_message_id")}}
    clock = {key: journey.get(key) for key in ("started_utc", "finished_utc", "api_send_to_complete_response_ms")}
    flags = {key: True for key in ("scientific_correctness", "coverage_complete", "citations_valid",
                                 "own_parent_sources_valid", "full_source_packet_reviewed", "no_scientific_critical_error")}
    try:
        started = datetime.fromisoformat(clock["started_utc"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(clock["finished_utc"].replace("Z", "+00:00"))
        return (set(qa) == expected_keys
            and qa.get("schema") == "dev89_independent_actual_answer_eligibility_v1"
            and qa.get("status") == qa.get("independent_answer_QA") == "PASS"
            and qa.get("case_id") == base_scope.get("case_id") == journey.get("case_id")
            and qa.get("question_sha256") == base_scope.get("question_sha256") == journey.get("question_sha256")
            and qa.get("scope_sha256") == base_scope_sha256 == journey.get("scope_sha256")
            and qa.get("source_version_sha256") == source_version_sha256
            and qa.get("teacher_config_sha256") == public_digest(base_scope.get("expected_model_config"))
            and qa.get("checker_config_sha256") == public_digest(base_scope.get("expected_checker_config"))
            and qa.get("output_policy") == base_scope["expected_settings"]["chat_checker_output_policy"]
            and qa.get("actual_journey_sha256") == journey_sha256
            and qa.get("raw_public_DTO_sha256") == public_digest(response)
            and qa.get("answer_text_sha256_UTF8") == hashlib.sha256(text.encode()).hexdigest()
            and all(type(value) is str and bool(value) for value in ids.values())
            and _exact(qa.get("actual_ids"), ids) and _exact(qa.get("clock"), clock)
            and type(clock["started_utc"]) is str and bool(clock["started_utc"])
            and type(clock["finished_utc"]) is str and bool(clock["finished_utc"])
            and type(clock["api_send_to_complete_response_ms"]) in (int, float)
            and _amount(clock["api_send_to_complete_response_ms"]) is not None
            and clock["api_send_to_complete_response_ms"] > 0
            and started.tzinfo is not None and finished.tzinfo is not None and finished >= started
            and _exact(qa.get("flags"), flags)
            and qa.get("actual_page_response_requires_independent_review_again") is True
            and qa.get("actual_page_latency_sample_qualified") is False)
    except (KeyError, TypeError, ValueError, AttributeError, BudgetError):
        return False


def _supplement_records(root, instance_id, descriptor_pin, marker, cases):
    _require(instance_id in _SUPPLEMENTS, "FIXED_SUPPLEMENT_INSTANCE_REQUIRED")
    runtime = root.parent
    protocol = _protocol_records(root, marker["protocol_sha256"])
    planned = _planned(protocol, instance_id)
    descriptor, pin = _pinned_record(runtime / f"supplement88-{instance_id}.json", descriptor_pin)
    expected_keys = {"schema", "authorization", "instance_id", "kind", "base_case_id", "protocol_sha256",
        "question_id", "question_sha256", "base_scope_sha256", "base_source_version_sha256",
        "instance_source_version_sha256", "base_final_receipt_sha256", "base_api_closure_sha256",
        "qa_receipt_path", "qa_receipt_sha256", "actual_answer_sha256", "root_selected_authorized",
        "automatic_replay_or_reclaim", "repair_review_path", "repair_review_sha256", "base_journey_receipt_sha256"}
    _require(set(descriptor) == expected_keys
             and descriptor.get("schema") == "dev89_planned_instance_descriptor_v1"
             and descriptor.get("authorization") == AUTHORIZATION
             and descriptor.get("instance_id") == instance_id
             and descriptor.get("root_selected_authorized") is True
             and descriptor.get("automatic_replay_or_reclaim") is False
             and type(descriptor.get("question_id")) is str and bool(descriptor["question_id"].strip())
             and descriptor.get("protocol_sha256") == marker["protocol_sha256"], "SUPPLEMENT_DESCRIPTOR_BINDING_CHANGED")
    for field in ("question_sha256", "base_scope_sha256", "base_source_version_sha256",
                  "instance_source_version_sha256", "base_final_receipt_sha256", "base_api_closure_sha256",
                  "base_journey_receipt_sha256"):
        _sha(descriptor[field])
    base_id = descriptor["base_case_id"]
    _require(type(base_id) is str and base_id in cases and base_id in BASE_CASES | AUX_CASES
             and base_id != instance_id, "SUPPLEMENT_CLOSED_BASE_CLAIM_REQUIRED")
    _require(cases[base_id]["question_sha256"] == descriptor["question_sha256"], "SUPPLEMENT_QUESTION_CHANGED")
    base_scope, _ = _pinned_record(runtime / f"scope88-{base_id}.json", descriptor["base_scope_sha256"])
    instance_scope, _ = _pinned_record(runtime / f"scope88-{instance_id}.json")
    base_version = _scope_binding(base_scope, base_id, descriptor)
    instance_version = _scope_binding(instance_scope, instance_id, descriptor)
    _require(instance_scope.get("supplement_descriptor_sha256") == pin
             and instance_scope.get("question_text") == base_scope.get("question_text")
             and base_version == descriptor["base_source_version_sha256"]
             and instance_version == descriptor["instance_source_version_sha256"], "SUPPLEMENT_SOURCE_VERSION_CHANGED")
    for scope, ident in ((base_scope, base_id), (instance_scope, instance_id)):
        _require(_exact(scope.get("expected_model_config"), protocol["expected_model_config"])
                 and _exact(scope.get("expected_checker_config"), protocol["expected_checker_config"])
                 and scope.get("phase89_frozen_profile_sha256") == protocol["base_config_sha256"],
                 "QUALITY_PAGE_MODEL_OR_POLICY_CHANGED")
        _settings_match(scope, protocol, runtime, ident)
    journey, journey_pin = _pinned_record(runtime / base_id / "journey-receipt88.json",
                                         descriptor["base_journey_receipt_sha256"])
    _require(journey.get("case_id") == base_id and journey.get("scope_sha256") == descriptor["base_scope_sha256"]
             and journey.get("question_sha256") == descriptor["question_sha256"], "BASE_ACTUAL_JOURNEY_BINDING_CHANGED")
    if instance_id in AUX_CASES:
        _require(planned["kind"] == "affected_or_control" and descriptor["kind"] in {"affected", "control"}
                 and base_id in BASE_CASES
                 and all(descriptor[field] is None for field in ("qa_receipt_path", "qa_receipt_sha256", "actual_answer_sha256"))
                 and descriptor["repair_review_path"] == "common-fix-plan89.json", "AFFECTED_CONTROL_DESCRIPTOR_REQUIRED")
        plan, plan_pin = _fix_plan(root, protocol, marker["protocol_sha256"])
        _require(plan_pin == descriptor["repair_review_sha256"]
                 and base_version == plan["source_version_before_sha256"]
                 and instance_version == plan["source_version_after_sha256"]
                 and _exact(instance_scope["source_pins"], plan["source_pins_after"])
                 and {"instance_id": instance_id, "kind": descriptor["kind"], "base_case_id": base_id,
                      "question_sha256": descriptor["question_sha256"]} in plan["instances"],
                 "COMMON_FIX_INSTANCE_BINDING_CHANGED")
    else:
        _require(planned["kind"] == "page" and descriptor["kind"] == "quality_qualified_page"
                 and base_version == instance_version
                 and descriptor["repair_review_path"] is descriptor["repair_review_sha256"] is None
                 and instance_scope.get("page_answer_requires_independent_quality_review") is True
                 and instance_scope.get("page_base_checker_config_sha256") == public_digest(base_scope["expected_checker_config"]),
                 "QUALITY_PAGE_DESCRIPTOR_REQUIRED")
        version = protocol["source_version_sha256"]
        if (runtime / "common-fix-plan89.json").exists():
            plan, _ = _fix_plan(root, protocol, marker["protocol_sha256"])
            version = plan["source_version_after_sha256"]
        _require(instance_version == version, "QUALITY_PAGE_CURRENT_SOURCE_VERSION_REQUIRED")
        response = journey.get("response")
        _require(journey.get("status") == "API_COMPLETED"
                 and type(journey.get("API_n")) is int and journey["API_n"] == 1
                 and type(journey.get("completed_answer_n")) is int and journey["completed_answer_n"] == 1
                 and type(response) is dict and response.get("response_type") == "answer"
                 and public_digest(response) == _sha(descriptor["actual_answer_sha256"]),
                 "QUALITY_PAGE_COMPLETED_ANSWER_REQUIRED")
        _require(instance_scope.get("page_base_teacher_config_sha256") == public_digest(base_scope["expected_model_config"])
                 and instance_scope.get("page_base_public_DTO_sha256") == public_digest(response),
                 "QUALITY_PAGE_PYTHON_NUMERIC_DOMAIN_BINDING_CHANGED")
        qa, _ = _pinned_record(_public_relative(runtime, descriptor["qa_receipt_path"]), descriptor["qa_receipt_sha256"])
        _require(page_quality_matches(qa, base_scope, response, base_scope_sha256=descriptor["base_scope_sha256"],
                     source_version_sha256=instance_version, journey=journey, journey_sha256=journey_pin),
                 "QUALITY_PAGE_ACTUAL_ANSWER_QA_REQUIRED")
    final, _ = _pinned_record(runtime / base_id / "native-provider70" / "final-receipt.json",
                              descriptor["base_final_receipt_sha256"])
    posts = final.get("actual_posts")
    _require(final.get("case_id") == base_id and final.get("question_sha256") == descriptor["question_sha256"]
             and final.get("closure_status") == "CLOSED_NUMERIC_NO_UNKNOWN"
             and type(posts) is int and 0 < posts <= CASE_POST_CAP
             and type(final.get("settled_numeric_cost_observations")) is int
             and final["settled_numeric_cost_observations"] == posts
             and _amount(final.get("native_unresolved_full_protection_USD")) == Decimal(0)
             and _amount(final.get("native_settled_known_cost_USD")) is not None,
             "SUPPLEMENT_BASE_NOT_NUMERICALLY_CLOSED")
    closure, _ = _pinned_record(runtime / base_id / "api-closure77.json", descriptor["base_api_closure_sha256"])
    metadata = closure.get("old_metadata_unchanged")
    _require(closure.get("owned_threads_closed") is True and type(metadata) is dict
             and set(metadata) == _OLD_METADATA_KEYS and all(value is True for value in metadata.values()),
             "SUPPLEMENT_BASE_API_NOT_CLOSED")
    return descriptor, final


def validate_supplement(root, instance_id, descriptor_sha256=None, *, admission=True):
    """Exact generic instance binding; admission gates never masquerade as model failures."""
    _require(type(admission) is bool, "EXPLICIT_ADMISSION_MODE_REQUIRED")
    root = _root(root)
    if admission:
        _require_running(root)
    marker, cases, claims, settlements, exposures, _, known, unknown = _scan(root)
    descriptor, final = _supplement_records(root, instance_id, descriptor_sha256, marker, cases)
    _closed_base_journal(descriptor, final, cases, claims, settlements, exposures)
    if admission:
        _require(unknown == 0, "UNSETTLED_PROTECTION_BLOCKS_POSTS")
        _require(not any(row["case_id"] == instance_id for row in claims.values()), "INSTANCE_EXECUTION_ALREADY_STARTED")
        if instance_id in PAGE_CASES:
            _require(len(claims) + CASE_POST_CAP <= POST_CAP and known + HOLD * CASE_POST_CAP <= COST_CAP,
                     "BOUND_LOCAL_BUDGET")
            page_questions = {row["question_sha256"] for key, row in cases.items() if key in PAGE_CASES and key != instance_id}
            _require(descriptor["question_sha256"] not in page_questions, "DUPLICATE_PAGE_QUESTION_FORBIDDEN")
            if instance_id == "case10c":
                _require({"case10", "case10b"} <= set(cases), "THIRD_PAGE_REQUIRES_TWO_PRIOR_INSTANCES")
                for prior_id in ("case10", "case10b"):
                    prior, _ = _pinned_record(root.parent / prior_id / "native-provider70" / "final-receipt.json")
                    prior_close, _ = _pinned_record(root.parent / prior_id / "api-closure77.json")
                    metadata = prior_close.get("old_metadata_unchanged")
                    _require(prior.get("case_id") == prior_id and type(prior.get("actual_posts")) is int
                             and 0 <= prior["actual_posts"] <= CASE_POST_CAP
                             and prior.get("question_sha256") == cases[prior_id]["question_sha256"]
                             and prior.get("closure_status") == "CLOSED_NUMERIC_NO_UNKNOWN"
                             and type(prior.get("settled_numeric_cost_observations")) is int
                             and prior["settled_numeric_cost_observations"] == prior["actual_posts"]
                             and _amount(prior.get("native_unresolved_full_protection_USD")) == Decimal(0)
                             and prior_close.get("owned_threads_closed") is True
                             and type(metadata) is dict and set(metadata) == _OLD_METADATA_KEYS
                             and all(value is True for value in metadata.values()),
                             "THIRD_PAGE_REQUIRES_TWO_CLOSED_INSTANCES")
                    _closed_base_journal({"base_case_id": prior_id}, prior, cases, claims, settlements, exposures)
        else:
            nonpage = sum(row["case_id"] not in PAGE_CASES for row in claims.values())
            _require(nonpage + CASE_POST_CAP <= NONPAGE_POST_CAP
                     and known + HOLD * CASE_POST_CAP <= COST_CAP, "BOUND_LOCAL_BUDGET")
    return descriptor


def validate_fresh_validation(*_args, **_kwargs):
    raise BudgetError("OLD_SPECIAL_VALIDATION_FORBIDDEN_IN_DEV89")


def claim_component(*_args, **_kwargs):
    raise BudgetError("CHECKER_LOW_COMPONENT_FORBIDDEN_IN_DEV89")


def _closed_base_journal(descriptor, final, cases, claims, settlements, exposures):
    base = descriptor["base_case_id"]
    _require(base in cases, "SUPPLEMENT_CLOSED_BASE_CLAIM_REQUIRED")
    slots = {slot for slot, claim in claims.items() if claim["case_id"] == base}
    _require(len(slots) == final["actual_posts"] and slots <= set(settlements)
             and not slots & set(exposures), "SUPPLEMENT_BASE_JOURNAL_NOT_CLOSED")
    known = sum((_amount(settlements[slot]["known_cost_USD"]) for slot in slots), Decimal(0))
    _require(known == _amount(final["native_settled_known_cost_USD"]),
             "SUPPLEMENT_BASE_JOURNAL_COST_CHANGED")

def _create(path, value, replay_code):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()
    try:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        raise BudgetError(replay_code) from None
    except OSError:
        # A partially written claim remains terminal; never unlink or retry it.
        raise BudgetError("JOURNAL_WRITE_FAILED") from None

def _marker(protocol_pin):
    return {"schema": "dev89_cohort_claim_v1", "authorization": AUTHORIZATION,
            "protocol_sha256": _sha(protocol_pin), "physical_posts_maximum": POST_CAP,
            "cost_cap_USD": str(COST_CAP), "per_post_full_hold_USD": str(HOLD),
            "cases_maximum": CASE_CAP, "per_case_posts_maximum": CASE_POST_CAP,
            "reserved_extra_posts_authorized": False, "automatic_retry_or_reclaim": False}

def initialize_cohort(root, protocol_pin):
    """Create the cohort marker once, or validate the existing exact binding."""
    expected = _marker(protocol_pin)
    root = _root(root, create=True)
    path = root / MARKER
    if not path.exists():
        try:
            _create(path, expected, "COHORT_MARKER_EXISTS")
        except BudgetError as exc:
            if exc.code != "COHORT_MARKER_EXISTS":
                raise
    _require(_exact(_read(path), expected), "COHORT_BINDING_CHANGED")
    return snapshot(root)

def _stop_record(protocol_pin, finite_code, review_sha256):
    _require(type(finite_code) is str and finite_code in STOP_CODES,
             "FINITE_COHORT_STOP_CODE_REQUIRED")
    _require(finite_code not in _QUALITY_STOP_CODES
             or (type(review_sha256) is str and _SHA.fullmatch(review_sha256)),
             "QUALITY_REVIEW_SHA256_REQUIRED")
    if review_sha256 is not None:
        review_sha256 = _sha(review_sha256)
    return {"schema": "dev89_permanent_cohort_stop_v1", "protocol_sha256": _sha(protocol_pin),
            "finite_code": finite_code, "review_sha256": review_sha256}

def stop_cohort(root, finite_code, review_sha256=None):
    """Permanently stop new work, preserving the first exact marker and all money records.

    Quality stops require an immutable review pin. A concurrent or repeated stop
    returns the first validated marker; malformed existing bytes are never replaced.
    Existing in-flight posts may still settle through ``settle_post``.
    """
    root = _root(root)
    marker = _read(root / MARKER)
    _require(_exact(marker, _marker(marker.get("protocol_sha256"))), "COHORT_BINDING_CHANGED")
    expected = _stop_record(marker["protocol_sha256"], finite_code, review_sha256)
    path = root / STOP_MARKER
    if not _stopped(root):
        try:
            _create(path, expected, "COHORT_STOP_MARKER_EXISTS")
        except BudgetError as exc:
            if exc.code != "COHORT_STOP_MARKER_EXISTS":
                raise
    record = _read(path)
    original = _stop_record(marker["protocol_sha256"], record.get("finite_code"),
                            record.get("review_sha256"))
    _require(_exact(record, original), "COHORT_STOP_BINDING_CHANGED")
    return record

def _scan(root):
    root = _root(root)
    marker = _read(root / MARKER)
    _require(_exact(marker, _marker(marker.get("protocol_sha256"))), "COHORT_BINDING_CHANGED")
    protocol = _protocol_records(root, marker["protocol_sha256"])
    cases, claims, settlements, exposures = {}, {}, {}, {}
    for path in root.iterdir():
        name = path.name
        if name in (MARKER, STOP_MARKER):
            continue
        if name.endswith("-claim.json") and name.removesuffix("-claim.json") in ALL_CASES:
            case_id = name.removesuffix("-claim.json")
            record = _read(path)
            expected = {"schema": "dev89_case_claim_v1", "authorization": AUTHORIZATION,
                        "protocol_sha256": marker["protocol_sha256"], "case_id": case_id,
                        "question_sha256": _sha(record.get("question_sha256")),
                        "physical_posts_maximum": CASE_POST_CAP, "automatic_retry_or_reclaim": False}
            planned = _planned(protocol, case_id)
            if case_id in _SUPPLEMENTS:
                expected["schema"] = "dev89_supplement_case_claim_v1"
                expected["supplement_descriptor_sha256"] = _sha(record.get("supplement_descriptor_sha256"))
            else:
                _require(planned["kind"] == "base", "ORDINARY_INSTANCE_PLAN_CHANGED")
                question = next(row for row in protocol["cases"] if row["case_id"] == case_id)
                _require(record["question_sha256"] == question["question_sha256"], "BASE_QUESTION_CHANGED")
            _require(_exact(record, expected), "CASE_BINDING_CHANGED")
            cases[case_id] = record
            continue
        matched = _POST_FILE.fullmatch(name)
        _require(matched is not None, "UNEXPECTED_JOURNAL_ENTRY")
        slot, kind = int(matched[1]), matched[2]
        {"claim": claims, "settlement": settlements, "exposure": exposures}[kind][slot] = _read(path)
    ordinary_cases = {case_id: row for case_id, row in cases.items() if case_id in BASE_CASES}
    _require(len(ordinary_cases) <= CASE_CAP
             and len({row["question_sha256"] for row in ordinary_cases.values()}) == len(ordinary_cases),
             "DUPLICATE_QUESTION_CLAIM")
    supplements = [_supplement_records(root, case_id, row["supplement_descriptor_sha256"], marker, cases)
                   for case_id, row in cases.items() if case_id in _SUPPLEMENTS]
    _require(sorted(claims) == list(range(1, len(claims) + 1)) and len(claims) <= POST_CAP,
             "POST_SLOTS_NOT_CONTIGUOUS")
    _require(set(settlements) <= set(claims) and set(exposures) <= set(claims)
             and not set(settlements) & set(exposures), "POST_RECORD_LINEAGE_INVALID")
    case_posts = {case_id: 0 for case_id in cases}
    case_steps = {case_id: [] for case_id in cases}
    known, unknown = Decimal(0), Decimal(0)
    for slot in sorted(claims):
        claim = claims[slot]
        case_id = _case(claim.get("case_id"))
        _require(case_id in cases, "CASE_CLAIM_REQUIRED")
        index = case_posts[case_id]
        _require(index < CASE_POST_CAP, "CASE_POST_LIMIT")
        wire_bytes = claim.get("wire_bytes")
        _require(type(wire_bytes) is int and 0 < wire_bytes <= MAX_WIRE_BYTES, "WIRE_BYTES_INVALID")
        role, purpose = claim.get("role"), claim.get("purpose")
        _require(next_step_allowed(case_steps[case_id], role, purpose), "ROLE_PURPOSE_SEQUENCE_INVALID")
        expected = {"schema": "dev89_post_claim_v1", "authorization": AUTHORIZATION,
                    "protocol_sha256": marker["protocol_sha256"], "global_slot": slot,
                    "case_id": case_id, "case_post_index": index + 1,
                    "role": role, "purpose": purpose,
                    "wire_sha256": _sha(claim.get("wire_sha256")), "wire_bytes": wire_bytes,
                    "full_hold_USD": str(HOLD)}
        _require(_exact(claim, expected), "POST_BINDING_CHANGED")
        case_posts[case_id] += 1
        case_steps[case_id].append({"role": role, "purpose": purpose})
        binding = {"global_slot": slot, "case_id": case_id, "role": claim["role"],
                   "protocol_sha256": marker["protocol_sha256"]}
        if slot in settlements:
            record = settlements[slot]
            cost = _amount(record.get("known_cost_USD"))
            _require(cost is not None and cost <= HOLD, "SETTLEMENT_COST_INVALID")
            expected = {"schema": "dev89_post_settlement_v1", **binding,
                        "known_cost_USD": str(cost), "released_own_protection_USD": str(HOLD)}
            _require(_exact(record, expected), "SETTLEMENT_BINDING_CHANGED")
            known += cost
        elif slot in exposures:
            record = exposures[slot]
            raw_cost = record.get("observed_cost_USD")
            cost = _amount(raw_cost)
            _require(raw_cost is None or cost is not None, "EXPOSURE_COST_INVALID")
            protection = max(HOLD, cost) if cost is not None else HOLD
            expected = {"schema": "dev89_terminal_exposure_v1", **binding,
                        "observed_cost_USD": str(cost) if cost is not None else None,
                        "unknown_protection_USD": str(protection), "terminal": True}
            _require(_exact(record, expected), "EXPOSURE_BINDING_CHANGED")
            unknown += protection
        else:
            unknown += HOLD
    for descriptor, final in supplements:
        _closed_base_journal(descriptor, final, cases, claims, settlements, exposures)
    _require(sum(row["case_id"] not in PAGE_CASES for row in claims.values()) <= NONPAGE_POST_CAP,
             "BOUND_LOCAL_BUDGET")
    return marker, cases, claims, settlements, exposures, case_posts, known, unknown

def snapshot(root):
    """Derive all occupancy from the flat journal; never mutate or clear records."""
    marker, cases, claims, settlements, exposures, case_posts, known, unknown = _scan(root)
    return {"authorization": AUTHORIZATION, "protocol_sha256": marker["protocol_sha256"],
            "cases_claimed": len(cases), "case_posts": case_posts,
            "claimed_physical_posts": len(claims), "settled_posts": len(settlements),
            "terminal_exposures": len(exposures), "known_cost_USD": str(known),
            "unknown_full_hold_USD": str(unknown), "physical_posts_maximum": POST_CAP,
            "cost_cap_USD": str(COST_CAP), "reserved_extra_posts_authorized": False,
            "ordinary_cases_claimed": sum(case_id in BASE_CASES for case_id in cases),
            "diagnostic_components_claimed": 0,
            "supplemental_cases_claimed": sum(case_id in _SUPPLEMENTS for case_id in cases),
            "auxiliary_cases_claimed": sum(case_id in AUX_CASES for case_id in cases),
             "page_cases_claimed": sum(case_id in PAGE_CASES for case_id in cases),
             "nonpage_posts_cap": NONPAGE_POST_CAP, "page_posts_reserved_from_nonpage": 8,
             "cohort_stopped": _stopped(root)}

def claim_case(root, case_id, question_sha256, protocol_pin, *, remaining_case_execution_authorized=False,
               supplement_descriptor_sha256=None, fresh_validation_descriptor_sha256=None):
    """One-shot finite instance claim; local budget deferral does not change the planned denominator."""
    _require_running(root)
    case_id, question_sha256 = _case(case_id), _sha(question_sha256)
    _require(fresh_validation_descriptor_sha256 is None, "OLD_SPECIAL_VALIDATION_FORBIDDEN_IN_DEV89")
    initialize_cohort(root, protocol_pin)
    marker, cases, claims, _, _, _, known, unknown = _scan(root)
    _require(case_id not in cases, "CASE_REPLAY_FORBIDDEN")
    protocol = _protocol_records(root, protocol_pin)
    _planned(protocol, case_id)
    if case_id in _SUPPLEMENTS:
        _require(supplement_descriptor_sha256 is not None, "SUPPLEMENT_DESCRIPTOR_PIN_REQUIRED")
        descriptor = validate_supplement(root, case_id, supplement_descriptor_sha256)
        _require(descriptor["question_sha256"] == question_sha256, "SUPPLEMENT_QUESTION_CHANGED")
    else:
        _require(supplement_descriptor_sha256 is None, "ORDINARY_CASE_SUPPLEMENT_FORBIDDEN")
        row = next(row for row in protocol["cases"] if row["case_id"] == case_id)
        _require(row["question_sha256"] == question_sha256, "BASE_QUESTION_CHANGED")
        _require(sum(key in BASE_CASES for key in cases) < CASE_CAP, "ORDINARY_CASE_LIMIT")
        _require(question_sha256 not in {row["question_sha256"] for key, row in cases.items() if key in BASE_CASES},
                 "DUPLICATE_QUESTION_CLAIM")
        nonpage = sum(row["case_id"] not in PAGE_CASES for row in claims.values())
        _require(nonpage + 2 <= NONPAGE_POST_CAP and known + HOLD * 2 <= COST_CAP, "BOUND_LOCAL_BUDGET")
    _require(unknown == 0, "UNSETTLED_PROTECTION_BLOCKS_POSTS")
    record = {"schema": "dev89_case_claim_v1", "authorization": AUTHORIZATION,
        "protocol_sha256": marker["protocol_sha256"], "case_id": case_id, "question_sha256": question_sha256,
        "physical_posts_maximum": CASE_POST_CAP, "automatic_retry_or_reclaim": False}
    if case_id in _SUPPLEMENTS:
        record["schema"] = "dev89_supplement_case_claim_v1"
        record["supplement_descriptor_sha256"] = _sha(supplement_descriptor_sha256)
    _create(_root(root) / f"{case_id}-claim.json", record, "CASE_REPLAY_FORBIDDEN")
    return snapshot(root)

def reserve_post(root, case_id, role, wire_sha256, wire_bytes, *, purpose):
    """Durably reserve one serial attempt before the caller opens transport."""
    _require_running(root)
    case_id, wire_sha256 = _case(case_id), _sha(wire_sha256)
    _require(type(wire_bytes) is int and 0 < wire_bytes <= MAX_WIRE_BYTES, "WIRE_BYTES_INVALID")
    marker, cases, claims, _, _, case_posts, known, unknown = _scan(root)
    _require(case_id in cases, "CASE_CLAIM_REQUIRED")
    _require(unknown == 0, "UNSETTLED_PROTECTION_BLOCKS_POSTS")
    index = case_posts[case_id]
    _require(index < CASE_POST_CAP, "CASE_POST_LIMIT")
    steps = [{"role": row["role"], "purpose": row["purpose"]}
             for _, row in sorted(claims.items()) if row["case_id"] == case_id]
    _require(next_step_allowed(steps, role, purpose), "ROLE_PURPOSE_SEQUENCE_INVALID")
    if case_id not in PAGE_CASES:
        _require(sum(row["case_id"] not in PAGE_CASES for row in claims.values()) < NONPAGE_POST_CAP,
                 "BOUND_LOCAL_BUDGET")
    # A fresh teacher needs headroom for its checker; this does not book a second hold.
    required_headroom = HOLD * (2 if role == "teacher" else 1)
    _require(len(claims) < POST_CAP and known + required_headroom <= COST_CAP,
             "COHORT_BUDGET_EXHAUSTED")
    slot = len(claims) + 1
    _create(_root(root) / f"post-{slot:02d}-claim.json", {
        "schema": "dev89_post_claim_v1", "authorization": AUTHORIZATION,
        "protocol_sha256": marker["protocol_sha256"], "global_slot": slot,
        "case_id": case_id, "case_post_index": index + 1, "role": role, "purpose": purpose,
        "wire_sha256": wire_sha256, "wire_bytes": wire_bytes, "full_hold_USD": str(HOLD),
    }, "POST_SLOT_COLLISION")
    return slot

def settle_post(root, global_slot, cost, *, status_safe):
    """Settle a validated response once; unsafe exposure remains terminal."""
    _require(type(global_slot) is int and 1 <= global_slot <= POST_CAP, "POST_SLOT_REQUIRED")
    _require(type(status_safe) is bool, "EXPLICIT_SAFE_STATUS_REQUIRED")
    marker, _, claims, settlements, exposures, _, _, _ = _scan(root)
    _require(global_slot in claims, "POST_CLAIM_REQUIRED")
    _require(global_slot not in settlements, "SETTLEMENT_REPLAY_FORBIDDEN")
    _require(global_slot not in exposures, "TERMINAL_EXPOSURE_CANNOT_SETTLE")
    claim = claims[global_slot]
    binding = {"global_slot": global_slot, "case_id": claim["case_id"], "role": claim["role"],
               "protocol_sha256": marker["protocol_sha256"]}
    amount = _amount(cost)
    safe = status_safe and amount is not None and amount <= HOLD
    if safe:
        _create(_root(root) / f"post-{global_slot:02d}-settlement.json", {
            "schema": "dev89_post_settlement_v1", **binding,
            "known_cost_USD": str(amount), "released_own_protection_USD": str(HOLD),
        }, "SETTLEMENT_REPLAY_FORBIDDEN")
    else:
        protection = max(HOLD, amount) if amount is not None else HOLD
        _create(_root(root) / f"post-{global_slot:02d}-exposure.json", {
            "schema": "dev89_terminal_exposure_v1", **binding,
            "observed_cost_USD": str(amount) if amount is not None else None,
            "unknown_protection_USD": str(protection), "terminal": True,
        }, "TERMINAL_EXPOSURE_CANNOT_SETTLE")
    return {"settled": safe, **snapshot(root)}

