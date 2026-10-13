"""Independent Repair90 frozen-profile normal adapter boundary; inert on import."""

from __future__ import annotations


import hashlib


import json


import os


import re


from contextlib import contextmanager


from contextvars import ContextVar


from decimal import Decimal, InvalidOperation


from pathlib import Path


from unittest.mock import patch


from urllib.error import HTTPError
from io import BytesIO


from time import monotonic


URL = "https://openrouter.ai/api/v1/chat/completions"


RELEASE_ID = "4f11bd70-a486-4d16-b216-78cfe499530a"


_DISABLED_PROFILE_MATERIAL = {
    "profile": None, "compiler_version": "profile_rules_v1", "policy": "", "override": None,
}


DISABLED_PROFILE = {
    "use_profile": False, "profile": None, "source_version": None,
    "compiler_version": "profile_rules_v1", "policy": "",
    "policy_hash": hashlib.sha256(json.dumps(
        _DISABLED_PROFILE_MATERIAL, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode()).hexdigest(),
    "fallback_reason": None, "turn_override": None,
}


HOLD = Decimal("0.0714688")


MAX_WIRE = 200000


MAX_RESPONSE = 4000000


ROLE_LIMITS = {
    "teacher": ("anthropic/claude-haiku-5.5", "haiku55_google_vertex_low_v1", 4096),
    "checker": ("google/gemini-3.5-flash-lite", "gemini35_google_vertex_high_research_v1", 8192),
}

CHECKER_HIGH_PROFILE = "gemini35_google_vertex_high_research_v1"
CHECKER_8192_CASES = {'case01', 'case08', 'case06', 'case01r', 'case08r', 'case06r'}
CHECKER_8192_WIRE_LIMIT = 160000
FRESH_PUBLIC_SHA256 = "827df6bdc2b965bf9212eedf5801ef2da34b0a5cd370696032094ff4cee99bcb"


MAIN = Path("E:/5703/learning-assistant")


TRANSPORT_PATHS = ('generation/adapters.py', 'generation/lossless_unit_findings_v1.py', 'generation/network_policy.py', 'generation/openrouter_routes.py', 'generation/prompts/source_relation_check_v2.txt', 'generation/prompts/source_relation_generation_v2.txt', 'generation/providers.py', 'generation/types.py', 'personalisation/compiler.py', 'generation/service.py', 'generation/single_selection_findings_v2.py')


PURPOSES = {
    "generation", "joint_check", "semantic_repair", "joint_recheck",
    "generation_format_repair", "checker_contract_repair",
}


class NativeTransportStop(RuntimeError):
    """Static local code only. The normal adapter does not catch RuntimeError."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise NativeTransportStop(code)


def number(value):
    if type(value) not in (int, float):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return amount if amount.is_finite() and amount >= 0 else None


def create(path, value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    with Path(path).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def has_secret(value, key, *, depth=0):
    """Scan all decoded JSON strings/keys, including nested escaped JSON strings."""
    if depth > 40:
        return True
    if isinstance(value, str):
        if key in value:
            return True
        expanded = value
        for _ in range(4):
            decoded_escapes = re.sub(
                r"\\u([0-9a-fA-F]{4})",
                lambda match: chr(int(match.group(1), 16)), expanded,
            ).replace(r"\/", "/").replace(r"\\", "\\")
            if key in decoded_escapes:
                return True
            if decoded_escapes == expanded:
                break
            expanded = decoded_escapes
        if value.lstrip().startswith(("{", "[", '"')):
            try:
                nested = json.loads(value)
            except (ValueError, RecursionError):
                return False
            return has_secret(nested, key, depth=depth + 1)
        return False
    if isinstance(value, dict):
        return any(has_secret(name, key, depth=depth + 1) or has_secret(item, key, depth=depth + 1)
                   for name, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(has_secret(item, key, depth=depth + 1) for item in value)
    return False


ACTIVE_SECONDS_CAP = 180


ROLE_PURPOSES = {"teacher": "generation", "checker": "joint_check"}


CHECKER_SCHEMA_NAME = "joint_check_source_relations_v2_lossless_output_v1"


CHECKER_OUTPUT_POLICY = "lossless_unit_findings_v1"
V2_OUTPUT_POLICY = "single_selection_findings_v2"
V2_SCHEMA_NAME = "joint_check_source_relations_v2_single_selection_output_v2"
V2_TRANSPORT_PATHS = TRANSPORT_PATHS


def checker_variant(scope):
    """Select the explicitly bound output policy for this new phase88 case."""
    settings = scope.get("expected_settings")
    require(type(settings) is dict, "PHASE88_CHECKER_OUTPUT_VARIANT_CHANGED")
    policy = settings.get("chat_checker_output_policy")
    variant = scope.get("phase88_checker_output_variant")
    if policy == V2_OUTPUT_POLICY:
        require(scope.get("case_id") in {'case01', 'case08', 'case06', 'case01r', 'case08r', 'case06r'}
                and variant == V2_OUTPUT_POLICY and scope.get("phase88_v2_execution_authorized") is True,
                "EXPLICIT_PHASE88_V2_CASE_REQUIRED")
        return V2_OUTPUT_POLICY, V2_SCHEMA_NAME, V2_TRANSPORT_PATHS
    require(policy == CHECKER_OUTPUT_POLICY and variant in (None, CHECKER_OUTPUT_POLICY)
            and scope.get("phase88_v2_execution_authorized") in (None, False),
            "PHASE88_CHECKER_OUTPUT_VARIANT_CHANGED")
    return CHECKER_OUTPUT_POLICY, CHECKER_SCHEMA_NAME, TRANSPORT_PATHS


def diagnostic_value(value, key, *, depth=0):
    """Sanitize known memory credentials before writing bounded public diagnostics."""
    if depth > 40:
        return "[WITHHELD_DEPTH]"
    if isinstance(value, str):
        return "[WITHHELD_SECRET_MATCH]" if has_secret(value, key) else value
    if isinstance(value, dict):
        result = {}
        for name, item in value.items():
            if not isinstance(name, str) or has_secret(name, key):
                continue
            if name.lower() in {"authorization", "api_key", "password", "access_token", "refresh_token", "cookie", "set-cookie"}:
                result[name] = "[WITHHELD_CREDENTIAL_FIELD]"
            else:
                result[name] = diagnostic_value(item, key, depth=depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [diagnostic_value(item, key, depth=depth + 1) for item in value]
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float:
        return value if value == value and abs(value) != float("inf") else None
    return None


def capture_normal_outcome(result, api_key, outpath, *, slot=2):
    """Capture the returned normal outcome before caller failure handling; no retry."""
    value = {"schema": "phase88_redacted_normal_outcome_v1",
             "error": getattr(result, "error", None), "diagnostic": getattr(result, "diagnostic", None),
             "finish_reason": getattr(result, "finish_reason", None), "usage": getattr(result, "usage", None),
             "transport_raw_text": getattr(result, "transport_raw_text", None),
             "raw_text": getattr(result, "raw_text", None), "auth_exported": False}
    safe = diagnostic_value(value, api_key)
    require(not has_secret(safe, api_key), "NORMAL_OUTCOME_SECRET_WITHHELD")
    create(Path(outpath), safe)


SHARED_GUARD_CODES = frozenset({
    "NORMAL_TRANSPORT_SOURCE_REDIRECTED", "NORMAL_TRANSPORT_SOURCE_CHANGED",
    "LOADED_NORMAL_TRANSPORT_SOURCE_CHANGED", "EXACT_NORMAL_TRANSPORT_PINS_REQUIRED",
    "FROZEN_COHORT_PROTOCOL_CHANGED", "CURRENT_PUBLIC_SCOPE_MISMATCH",
    "NORMAL_GENERATE_BOUNDARY_REQUIRED", "NORMAL_WIRE_BOUNDARY_CHANGED",
    "ORIGINAL_AUTH_BOUNDARY_CHANGED", "NORMAL_PAYLOAD_COMPILER_BYTES_CHANGED",
    "EXACT_MODEL_ROUTE_OR_CAP_CHANGED", "NORMAL_ROLE_OR_MEMORY_AUTH_CHANGED",
    "EXACT_ROLE_BINDING_REQUIRED", "EXACT_LOSSLESS_OUTPUT_SETTINGS_REQUIRED",
    "EXPLICIT_PHASE88_V2_CASE_REQUIRED", "PHASE88_CHECKER_OUTPUT_VARIANT_CHANGED",
    "SUPPLEMENT_ON_ORIGINAL_CASE_FORBIDDEN",
    "CHECKER_HIGH_MANIFEST_PIN_REQUIRED", "ROOT_CHECKER_HIGH_MANIFEST_REQUIRED",
    "CHECKER_HIGH_MANIFEST_CHANGED", "EXACT_ROOT_CHECKER_HIGH_MANIFEST_REQUIRED",
    "KNOWN_HIGH_CONFIG_REQUIRED",
    "EXPLICIT_CHECKER_8192_SCOPE_REQUIRED", "CHECKER_8192_MANIFEST_PIN_REQUIRED",
    "ROOT_CHECKER_8192_MANIFEST_REQUIRED", "CHECKER_8192_MANIFEST_CHANGED",
    "EXACT_ROOT_CHECKER_8192_MANIFEST_REQUIRED", "CHECKER_8192_WIRE_LIMIT_EXCEEDED",
    "FRESH_VALIDATION_DESCRIPTOR_PIN_REQUIRED", "FRESH_VALIDATION_ON_OTHER_CASE_FORBIDDEN",
    "CURRENT_PUBLIC_SOURCE_ALLOWLIST_REQUIRED", "SOURCE_ALLOWLIST_INVALID",
    "CURRENT_EVIDENCE_OUTSIDE_PUBLIC_ALLOWLIST", "SOURCE_BOUNDARY_NOT_CURRENT_PUBLIC",
    "PROVIDER_SECRET_ECHO_WITHHELD", "AUTH_IN_PUBLIC_WIRE_WITHHELD",
    "AUTH_IN_NORMAL_COMPILED_PAYLOAD_WITHHELD", "NORMAL_ADAPTER_SECRET_ECHO_WITHHELD",
    "NORMAL_OUTCOME_SECRET_WITHHELD", "RAW_RESPONSE_SECRET_WITHHELD",
    "COHORT_BUDGET_EXHAUSTED", "UNSETTLED_PROTECTION_BLOCKS_POSTS",
    "COMPILED_BYTE_PRICE_BOUND_EXCEEDS_HOLD",
    "COHORT_BINDING_CHANGED", "COHORT_PERMANENTLY_STOPPED", "CASE_POST_LIMIT",
    "ONLY_TEACHER_THEN_LOSSLESS_CHECKER_ALLOWED", "TEACHER_THEN_CHECKER_REQUIRED",
    "POST_SLOT_COLLISION", "JOURNAL_WRITE_FAILED", "SETTLEMENT_BINDING_CHANGED",
    "POST_BINDING_CHANGED", "CASE_BINDING_CHANGED", "COHORT_SAFE_SETTLEMENT_REQUIRED",
})


def shared_risk(code, unknown_full_hold):
    return Decimal(str(unknown_full_hold)) > 0 or code in SHARED_GUARD_CODES


def require_role_step(state, role, purpose, schema_name, *, checker_schema_name=CHECKER_SCHEMA_NAME):
    require(type(state.get("attempts")) is int and 0 <= state["attempts"] < 4
            and next_step_allowed(state.get("steps", []), role, purpose)
            and (role != "checker" or schema_name == checker_schema_name),
            "ONLY_NORMAL_GENERATION_REPAIR_CHECKER_STEPS_ALLOWED")


def require_active_deadline(deadline, timeout=None):
    remaining = deadline - monotonic()
    require(remaining > 0 and (timeout is None or 0 < timeout <= remaining),
            "ACTIVE_180_SECONDS_EXHAUSTED")


from budget88 import initialize_cohort, claim_case, reserve_post, settle_post, snapshot, stop_cohort, BudgetError, next_step_allowed, validate_supplement, validate_protocol, public_digest, BASE_CASES, AUX_CASES, PAGE_CASES, ALL_CASES

STAGE_REQUEST_CAP = 4
BATCH_ID = "5703_repair90_bound_development_validation"
COHORT_ROOT = Path(__file__).resolve().parent
COHORT_LEDGER = COHORT_ROOT / "cohort-ledger"
COHORT_AUTHORIZATION = "parent_repair90_independent24posts_1USD_same_input_validation_20261012"
EXCLUDED_CALVIN_QUESTION_SHA256 = "1aba6b3d61922f14c26d0a1dfb3ba1df80f46c43d2f59e2ce9502eccc63e0baf"


def expected_checker_config(scope, protocol):
    """Only the exact frozen stable HIGH8192 configuration is eligible in this cohort."""
    try:
        validate_protocol(protocol)
    except BudgetError as exc:
        raise NativeTransportStop(exc.code) from None
    require(scope.get("phase90_frozen_profile_sha256") == protocol["base_config_sha256"]
            and scope.get("checker_high_manifest_sha256") is None
            and scope.get("checker_high8192_manifest_sha256") is None,
            "FROZEN_REPAIR90_PROFILE_BINDING_CHANGED")
    return protocol["expected_checker_config"]


def wire_binding_matches(wire, config, role):
    effort = "high" if role == "checker" and config["openrouter_route_profile"] == CHECKER_HIGH_PROFILE else "low"
    return (wire.get("model") == config["model"] and wire.get("max_tokens") == config["max_tokens"]
            and wire.get("reasoning") == {"effort": effort} and wire.get("provider") == {
                "order": ["google-vertex/global"], "only": ["google-vertex/global"],
                "allow_fallbacks": False, "require_parameters": True,
                "max_price": {"prompt": 0.3, "completion": 2.5},
            })


def checker_wire_limit(scope, role):
    return CHECKER_8192_WIRE_LIMIT if role == "checker" else MAX_WIRE


def require_wire_capacity(data, scope, role):
    require(len(data) <= checker_wire_limit(scope, role), "CHECKER_8192_WIRE_LIMIT_EXCEEDED")


def validate_case_scope(scope):
    """Bind one planned public question, exact source version and unchanged frozen profile."""
    require(type(scope) is dict and scope.get("phase88_authorization") == COHORT_AUTHORIZATION
            and scope.get("phase88_case_execution_authorized") is True, "EXPLICIT_REPAIR90_AUTHORIZATION_REQUIRED")
    case_id = scope.get("case_id")
    require(case_id in ALL_CASES, "FIXED_REPAIR90_CASE_REQUIRED")
    path = COHORT_ROOT / "protocol88.json"
    require(path.is_file() and not path.is_symlink(), "ROOT_FROZEN_PUBLIC_PROTOCOL_REQUIRED")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == scope.get("cohort_protocol_sha256"), "FROZEN_COHORT_PROTOCOL_CHANGED")
    try:
        protocol = validate_protocol(json.loads(raw))
    except BudgetError as exc:
        raise NativeTransportStop(exc.code) from None
    require(scope.get("public_source_boundary_sha256") == protocol["public_source_boundary_sha256"],
            "CURRENT_PUBLIC_BOUNDARY_CHANGED")
    planned = next((row for row in protocol["planned_instances"] if row["instance_id"] == case_id), None)
    require(planned is not None and scope.get("phase90_planned_kind") == planned["kind"], "FROZEN_INSTANCE_PLAN_CHANGED")
    require(scope.get("fresh_validation_descriptor_sha256") is None
            and scope.get("phase88_fresh_validation_authorized") in (None, False)
            and scope.get("zero_post_reconciliation_path") is None
            and scope.get("zero_post_reconciliation_sha256") is None,
            "OLD_SPECIAL_METADATA_FORBIDDEN_IN_REPAIR90")
    if case_id in BASE_CASES:
        require(scope.get("supplement_descriptor_sha256") is None, "SUPPLEMENT_ON_ORIGINAL_CASE_FORBIDDEN")
        case = next(row for row in protocol["cases"] if row["case_id"] == case_id)
        require(public_digest(scope.get("source_pins")) == protocol["source_version_sha256"]
                and scope.get("source_pins") == protocol["source_pins"], "BASELINE_SOURCE_VERSION_CHANGED")
    else:
        try:
            descriptor = validate_supplement(COHORT_LEDGER, case_id, scope.get("supplement_descriptor_sha256"))
        except BudgetError as exc:
            raise NativeTransportStop(exc.code) from None
        case = {"case_id": case_id, "question_id": descriptor["question_id"],
                "question_text": scope["question_text"], "question_sha256": descriptor["question_sha256"]}
    require(scope.get("question_text") == case["question_text"] and scope.get("question_id") == case["question_id"]
            and scope.get("question_sha256") == case["question_sha256"], "CURRENT_PUBLIC_SCOPE_MISMATCH")
    require(public_digest(scope.get("expected_model_config")) == public_digest(protocol["expected_model_config"])
            and public_digest(scope.get("expected_checker_config")) == public_digest(expected_checker_config(scope, protocol)),
            "EXACT_FROZEN_MODEL_CONFIG_REQUIRED")
    settings = scope.get("expected_settings")
    require(type(settings) is dict and public_digest({k:v for k,v in settings.items()
                if k not in {"storage_root", "visual_catalog_staging_root"}}) == public_digest(protocol["frozen_settings"])
            and settings.get("storage_root") == str(COHORT_ROOT / case_id / "storage")
            and settings.get("visual_catalog_staging_root") == str(COHORT_ROOT / case_id / "visual-staging"),
            "ONLY_OWNED_STORAGE_REBASE_ALLOWED")
    checker_variant(scope)
    return case


def require_next_case_post(state):
    require(type(state["attempts"]) is int and 0 <= state["attempts"] < 4
            and state["stop"] is None and state["unknown"] == 0,
            "FOUR_POST_CASE_OR_UNKNOWN_STOP")

@contextmanager
def normal_transport88(scope, output, api_key, *, assert_boundary, abort_event=None, capture_outcome=capture_normal_outcome):
    """Patch only this dedicated fixture process's normal adapter entry points.

    assert_boundary(context) must validate the actual current public source text,
    and return {current_public_boundary_verified: True, release_id: RELEASE_ID,
    evidence: [{chunk_id, text_sha256}, ...]}. Every returned submitted-text hash
    must also appear in scope.current_public_sources. This is independent of the
    historical 71-source experiment; no historical count is assumed here.
    """
    require(type(scope) is dict and scope.get("status") == "READY_BOUND_FOR_SINGLE_NEW_NATIVE_JOURNEY",
            "ROOT_NATIVE_SCOPE_BINDING_REQUIRED")
    require(scope.get("transport_guard_verified") is True and callable(assert_boundary),
            "ROOT_PUBLIC_BOUNDARY_BINDING_REQUIRED")
    require(type(api_key) is str and len(api_key) >= 16, "ORIGINAL_MEMORY_CREDENTIAL_REQUIRED")
    case = validate_case_scope(scope)
    question = case["question_text"]
    case_id = scope["case_id"]
    output_policy, checker_schema_name, transport_paths = checker_variant(scope)
    expected_settings = scope.get("expected_settings")
    require(type(expected_settings) is dict
            and expected_settings.get("chat_checker_output_policy") == output_policy
            and expected_settings.get("chat_checker_payload_policy") == "lossless_full_checker_tables_v2"
            and expected_settings.get("chat_source_relation_policy") == "source_relation_contract_v2"
            and expected_settings.get("chat_joint_checker_policy") == "typed_joint_v5"
            and expected_settings.get("chat_checker_schema_policy") is None
            and expected_settings.get("max_provider_calls") == STAGE_REQUEST_CAP
            and expected_settings.get("request_timeout_seconds") == ACTIVE_SECONDS_CAP,
            "EXACT_LOSSLESS_OUTPUT_SETTINGS_REQUIRED")
    require(scope.get("question_text") == question and scope.get("expected_release_id") == RELEASE_ID,
            "CURRENT_PUBLIC_SCOPE_MISMATCH")
    pinned_transport = {}
    for row in scope.get("source_pins", []):
        public = Path(row["path"])
        require(public.is_absolute() and public.resolve().is_relative_to(MAIN.resolve())
                and not public.is_symlink(), "NORMAL_TRANSPORT_SOURCE_REDIRECTED")
        relative = public.resolve().relative_to(MAIN.resolve()).as_posix()
        if relative in transport_paths:
            require(relative not in pinned_transport, "DUPLICATE_NORMAL_TRANSPORT_PIN")
            pinned_transport[relative] = row
    require(set(pinned_transport) == set(transport_paths), "EXACT_NORMAL_TRANSPORT_PINS_REQUIRED")
    for relative, row in pinned_transport.items():
        data = (MAIN / relative).read_bytes()
        require(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                "NORMAL_TRANSPORT_SOURCE_CHANGED")
    sources = scope.get("current_public_sources")
    require(type(sources) is list and sources, "CURRENT_PUBLIC_SOURCE_ALLOWLIST_REQUIRED")
    allowed = set()
    for row in sources:
        require(type(row) is dict and type(row.get("chunk_id")) is str
                and type(row.get("text_sha256")) is str
                and re.fullmatch(r"[0-9a-f]{64}", row["text_sha256"]), "SOURCE_ALLOWLIST_INVALID")
        allowed.add((row["chunk_id"], row["text_sha256"]))
    expected = {}
    for role, (model, route, limit) in ROLE_LIMITS.items():
        config = scope.get("expected_model_config" if role == "teacher" else "expected_checker_config")
        if role == "checker" and scope.get("checker_high_manifest_sha256") is not None:
            route = CHECKER_HIGH_PROFILE
        if role == "checker" and scope.get("checker_high8192_manifest_sha256") is not None:
            route, limit = CHECKER_HIGH_PROFILE, 8192
        require(type(config) is dict and config.get("provider") == "openai_compatible"
                and config.get("model") == model and config.get("openrouter_route_profile") == route
                and config.get("base_url") == "https://openrouter.ai/api/v1"
                and config.get("max_tokens") == limit and config.get("api_key_env") is None,
                "EXACT_ROLE_BINDING_REQUIRED")
        expected[role] = config
    root = Path(output)
    require(root.is_dir() and not root.is_symlink(), "ISOLATED_EXISTING_OUTPUT_REQUIRED")
    require(root.absolute() == COHORT_ROOT / case_id and root.resolve() == root.absolute(),
            "FIXED_NEW_CASE_OUTPUT_REQUIRED")
    initialize_cohort(COHORT_LEDGER, scope["cohort_protocol_sha256"])
    claim_case(COHORT_LEDGER, case_id, case["question_sha256"], scope["cohort_protocol_sha256"],
               remaining_case_execution_authorized=scope.get("phase88_case_execution_authorized") is True,
               supplement_descriptor_sha256=scope.get("supplement_descriptor_sha256"),
               fresh_validation_descriptor_sha256=scope.get("fresh_validation_descriptor_sha256"))
    ledger = root / "native-provider70"
    ledger.mkdir(exist_ok=False)
    create(ledger / "scope-claim.json", {
        "schema": "5703_repair90_case_normal_transport_scope_v1", "batch_id": BATCH_ID,
        "case_id": case_id, "question_sha256": case["question_sha256"],
        "checker_output_policy": output_policy, "checker_schema_name": checker_schema_name,
        "supplement_descriptor_sha256": scope.get("supplement_descriptor_sha256"),
        "checker_high_manifest_sha256": scope.get("checker_high_manifest_sha256"),
        "checker_high8192_manifest_sha256": scope.get("checker_high8192_manifest_sha256"),
        "fresh_validation_descriptor_sha256": scope.get("fresh_validation_descriptor_sha256"),
        "planned_maximum": 4, "cohort_maximum": 24, "cohort_cost_cap_USD": "1.00",
        "full_per_request_protection_USD": str(HOLD), "whole_case_seconds_cap": 180,
        "cohort_protocol_sha256": scope["cohort_protocol_sha256"], "request_retries": 0,
        "authorization": COHORT_AUTHORIZATION, "original_auth_exported": False,
        "old_closed12_occupancy_in_new_budget": 0, "old85_86_occupancy_in_new_budget": 0,
    })
    deadline = monotonic() + ACTIVE_SECONDS_CAP
    state = {"attempts": 0, "settled": 0, "known": Decimal(0), "unknown": Decimal(0), "stop": None, "cohort_slots": {}, "roles": {}, "purposes": {}, "steps": [], "normal_adapter_error_observed": False}
    view = {}

    def sync():
        cohort = snapshot(COHORT_LEDGER)
        view.update(provider_post_count=state["attempts"], known_cost_USD=str(state["known"]),
                    unknown_full_hold_USD=str(state["unknown"]),
                    stopped=state["stop"] is not None or cohort["cohort_stopped"],
                    stop_code=state["stop"], batch_id=BATCH_ID, case_id=case_id, normal_adapter_error_observed=state["normal_adapter_error_observed"],
                    cohort_claimed_posts=cohort["claimed_physical_posts"],
                    cohort_known_cost_USD=cohort["known_cost_USD"],
                    cohort_unknown_full_hold_USD=cohort["unknown_full_hold_USD"],
                    cohort_permanently_stopped=cohort["cohort_stopped"],
                    cohort_post_cap=24, cohort_cost_cap_USD="1.00",
                    status="STOPPED_RETAIN_ALL_RECORDS"
                        if state["stop"] or cohort["cohort_stopped"] else "BOUNDED_NORMAL_TRANSPORT_ACTIVE")

    sync()
    current = ContextVar("native70-current-normal-adapter", default=None)

    # No convenience package exports, alternate provider client, or direct HTTP.
    from generation import adapters, providers
    from generation.openrouter_routes import prepare_schema_wire

    original_open, original_generate = adapters.open_provider, adapters.LLMAdapter.generate
    require(Path(adapters.__file__).resolve() == (MAIN / "generation/adapters.py").resolve()
            and Path(original_open.__code__.co_filename).resolve() == (MAIN / "generation/adapters.py").resolve()
            and Path(original_generate.__code__.co_filename).resolve() == (MAIN / "generation/adapters.py").resolve(),
            "LOADED_NORMAL_TRANSPORT_SOURCE_CHANGED")

    def stop(code):
        state["stop"] = state["stop"] or code
        cohort = snapshot(COHORT_LEDGER)
        if shared_risk(code, cohort["unknown_full_hold_USD"]):
            stop_cohort(COHORT_LEDGER, "UNSAFE_NORMAL_TRANSPORT")
        sync()
        raise NativeTransportStop(state["stop"])

    def observe(slot, raw, status):
        # Persist a bounded redacted response before financial or adapter parsing.
        text = raw.decode("utf-8", errors="replace") if type(raw) is bytes and len(raw) <= MAX_RESPONSE else None
        raw_record = diagnostic_value({"schema": "phase88_redacted_http_before_parse_v1",
            "slot": slot, "role": state["roles"].get(slot),
            "stage": state["purposes"].get(slot),
            "http_status": status if type(status) is int and 100 <= status <= 599 else None,
            "raw_response_text": text, "raw_response_bytes": len(raw) if type(raw) is bytes else None,
            "response_withheld_or_oversize": text is None,
            "normal_adapter_parse_started": False, "auth_exported": False}, api_key)
        require(not has_secret(raw_record, api_key), "RAW_RESPONSE_SECRET_WITHHELD")
        create(ledger / f"slot-{slot:02d}-raw-response.json", raw_record)
        duplicate, numeric_fields = False, []

        def pairs(items):
            nonlocal duplicate
            value = {}
            for name, item in items:
                duplicate |= name in value
                if name == "cost" and number(item) is not None:
                    numeric_fields.append(number(item))
                value[name] = item
            return value

        decoded = None
        if type(raw) is bytes and len(raw) <= MAX_RESPONSE:
            try:
                decoded = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
            except (ValueError, UnicodeError, RecursionError):
                decoded = None
        usage = decoded.get("usage") if isinstance(decoded, dict) else None
        cost = number(usage.get("cost")) if isinstance(usage, dict) and not duplicate else None
        protection = max([HOLD, *numeric_fields, *([cost] if cost is not None else [])])
        create(ledger / f"slot-{slot:02d}-financial.json", {
            "schema": "5703_native70_financial_observation_v1", "slot": slot,
            "numeric_gateway_credit_cost_USD": str(cost) if cost is not None else None,
            "unresolved_protection_USD": str(protection), "original_hold_USD": str(HOLD),
            "http_status": status if type(status) is int and 100 <= status <= 599 else None,
            "provider_semantic_processing_started": False, "raw_response_exported": False,
            "duplicate_json_keys_observed": duplicate,
        })
        if protection > HOLD:
            settle_post(COHORT_LEDGER, state["cohort_slots"][slot], protection, status_safe=False)
        state["unknown"] += protection - HOLD
        sync()
        if type(raw) is not bytes or len(raw) > MAX_RESPONSE:
            stop("PROVIDER_RESPONSE_SIZE_INVALID")
        if api_key.encode("utf-8") in raw or has_secret(decoded, api_key):
            stop("PROVIDER_SECRET_ECHO_WITHHELD")
        if type(status) is not int or not 100 <= status <= 599:
            stop("PROVIDER_HTTP_STATUS_UNTRUSTED")
        if duplicate:
            stop("PROVIDER_JSON_DUPLICATE_KEYS")
        if cost is None:
            stop("PROVIDER_COST_UNKNOWN_RETAIN_FULL_HOLD")
        if cost > HOLD:
            stop("PROVIDER_COST_EXCEEDS_FULL_HOLD")
        create(ledger / f"slot-{slot:02d}-settlement.json", {
            "schema": "5703_native70_financial_settlement_v1", "slot": slot,
            "numeric_gateway_credit_cost_USD": str(cost), "released_own_protection_USD": str(protection),
            "historical_unknowns_released": 0, "trusted_numeric_cost_before_normal_adapter_parse": True,
        })
        settled = settle_post(COHORT_LEDGER, state["cohort_slots"][slot], cost, status_safe=True)
        require(settled["settled"] is True, "COHORT_SAFE_SETTLEMENT_REQUIRED")
        state["known"] += cost
        state["unknown"] -= protection
        state["settled"] += 1
        sync()

    class ObservedResponse:
        def __init__(self, original, slot):
            self.original, self.slot = original, slot
            self.status = getattr(original, "status", None)
            self.headers = {}
            self.consumed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.original.close()

        def read(self, size):
            require(not self.consumed and size == MAX_RESPONSE + 1, "NORMAL_RESPONSE_READ_CHANGED")
            self.consumed = True
            try:
                raw = self.original.read(size)
            except Exception:  # noqa: BLE001 - close only this claimed attempt and retain its hold.
                stop("PROVIDER_READ_FAILED_RETAIN_FULL_HOLD")
            observe(self.slot, raw, self.status)
            return raw

    def guarded_open(envelope, *, timeout):
        if abort_event is not None and abort_event.is_set():
            stop("OWNED_SCOPE_CLOSURE_DENIES_FURTHER_POSTS")
        bound = current.get()
        require(bound is not None, "NORMAL_GENERATE_BOUNDARY_REQUIRED")
        if state["stop"]:
            stop(state["stop"])
        data = envelope.data
        require(envelope.full_url == URL and envelope.get_method() == "POST"
                and type(data) is bytes and 0 < len(data) <= MAX_WIRE
                and type(timeout) in (int, float) and 0 < timeout <= 60,
                "NORMAL_WIRE_BOUNDARY_CHANGED")
        require(envelope.get_header("Authorization") == "Bearer " + api_key, "ORIGINAL_AUTH_BOUNDARY_CHANGED")
        try:
            wire = json.loads(data)
        except (ValueError, UnicodeError):
            stop("NORMAL_WIRE_JSON_INVALID")
        require(not has_secret(wire, api_key), "AUTH_IN_PUBLIC_WIRE_WITHHELD")
        role, config, expected_wire, purpose = bound
        require_wire_capacity(data, scope, role)
        require(data == expected_wire, "NORMAL_PAYLOAD_COMPILER_BYTES_CHANGED")
        require(wire_binding_matches(wire, config, role), "EXACT_MODEL_ROUTE_OR_CAP_CHANGED")
        price_bound = Decimal(len(data)) * Decimal("0.3") / Decimal(1000000) + Decimal(config["max_tokens"]) * Decimal("2.5") / Decimal(1000000)
        require(price_bound <= HOLD, "COMPILED_BYTE_PRICE_BOUND_EXCEEDS_HOLD")
        require_active_deadline(deadline, timeout)
        require_role_step(state, role, purpose, checker_schema_name, checker_schema_name=checker_schema_name)
        require_next_case_post(state)
        slot = state["attempts"] + 1
        cohort_slot = reserve_post(COHORT_LEDGER, case_id, role, hashlib.sha256(data).hexdigest(), len(data), purpose=purpose)
        state["cohort_slots"][slot] = cohort_slot
        state["roles"][slot] = role
        state["purposes"][slot] = purpose
        state["steps"].append({"role": role, "purpose": purpose})
        create(ledger / f"slot-{slot:02d}-claim.json", {
            "schema": "5703_native70_normal_post_claim_v1", "slot": slot, "role": role, "purpose": purpose,
            "wire_bytes": len(data), "wire_sha256": hashlib.sha256(data).hexdigest(),
            "maximum_hold_USD": str(HOLD), "original_auth_exported": False,
            "compiled_wire_bytes_as_conservative_input_token_bound": len(data),
            "output_token_upper_bound": config["max_tokens"], "route_prompt_price_per_million_USD": "0.3",
            "route_completion_price_per_million_USD": "2.5", "compiled_byte_price_bound_USD": str(price_bound),
            "token_bound_is_provider_tokenizer_verified": False,
            "normal_transport_used": True, "cohort_slot": cohort_slot,
        })
        state["attempts"] += 1
        state["unknown"] += HOLD
        sync()
        try:
            response = original_open(envelope, timeout=timeout)
        except HTTPError as exc:
            raw = exc.read(65537)
            observe(slot, raw, exc.code)
            # Replay only this already received body to the normal adapter catch.
            # Raising the same HTTPError does not issue a second HTTP request.
            exc.close()
            exc.fp = BytesIO(raw)
            exc.read = exc.fp.read
            raise
        except Exception:  # noqa: BLE001 - no alternate transport or retry.
            stop("PROVIDER_TRANSPORT_FAILED_RETAIN_FULL_HOLD")
        return ObservedResponse(response, slot)

    def generate_impl(adapter, messages, **kwargs):
        if state["stop"]:
            stop(state["stop"])
        config = adapter.config.to_dict()
        role = next((name for name, value in expected.items() if value == config), None)
        require(role is not None and adapter._api_key == api_key, "NORMAL_ROLE_OR_MEMORY_AUTH_CHANGED")
        context = kwargs.get("request_context")
        require(type(context) is dict and context.get("question") == question
                and context.get("mode") == "interactive_chat" and context.get("answer_mode") == "textbook"
                and context.get("options") is None and context.get("history") == []
                and context.get("summary") is None and context.get("purpose") in PURPOSES,
                "NORMAL_CURRENT_QUESTION_CONTEXT_CHANGED")
        require_active_deadline(deadline)
        require_role_step(state, role, context["purpose"], kwargs.get("response_schema_name"), checker_schema_name=checker_schema_name)
        profile = context.get("profile")
        require(type(profile) is dict and profile == DISABLED_PROFILE,
                "PRIVATE_PROFILE_CONTEXT_FORBIDDEN")
        require(not has_secret(messages, api_key) and not has_secret(context, api_key),
                "AUTH_IN_GENERATION_CONTEXT_WITHHELD")
        verified = assert_boundary(context)
        evidence = context.get("evidence")
        require(type(evidence) is list and type(verified) is dict
                and verified.get("current_public_boundary_verified") is True
                and verified.get("release_id") == RELEASE_ID, "CURRENT_PUBLIC_EVIDENCE_NOT_VERIFIED")
        proof = verified.get("evidence")
        require(type(proof) is list and len(proof) == len(evidence), "CURRENT_PUBLIC_EVIDENCE_PROOF_CHANGED")
        actual = []
        for index, row in enumerate(evidence):
            require(type(row) is dict and type(row.get("chunk_id")) is str and type(row.get("text")) is str,
                    "CURRENT_EVIDENCE_INVALID")
            pair = (row["chunk_id"], hashlib.sha256(row["text"].encode("utf-8")).hexdigest())
            item = proof[index]
            require(type(item) is dict and item.get("chunk_id") == pair[0]
                    and item.get("text_sha256") == pair[1], "CURRENT_PUBLIC_EVIDENCE_PROOF_CHANGED")
            require(pair in allowed or item.get("source_span_verified") is True
                    and (pair[0], item.get("source_text_sha256")) in allowed,
                    "CURRENT_EVIDENCE_OUTSIDE_PUBLIC_ALLOWLIST")
            actual.append({"chunk_id": pair[0], "text_sha256": pair[1]})
        compiled = providers.payload(adapter.config, messages, kwargs["response_schema"], kwargs["response_schema_name"])
        compiled, _ = prepare_schema_wire(adapter.config, compiled, kwargs["response_schema"])
        require(role != "checker" or compiled.get("response_format") == {"type": "json_object"},
                "EXACT_CHECKER_JSON_OBJECT_WIRE_REQUIRED")
        require(not has_secret(compiled, api_key), "AUTH_IN_NORMAL_COMPILED_PAYLOAD_WITHHELD")
        expected_wire = json.dumps(compiled, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        require(len(expected_wire) <= MAX_WIRE, "NORMAL_INPUT_WIRE_TOO_LARGE")
        slot = state["attempts"] + 1
        create(ledger / f"slot-{slot:02d}-public-inputs.json", {
            "schema": "5703_native70_normal_generation_public_inputs_v1", "role": role,
            "purpose": context["purpose"], "question": question, "history": [], "use_profile": False,
            "current_evidence_count": len(actual), "current_evidence": actual, "messages": messages,
            "current_source_proof": proof, "normal_compiled_wire": compiled,
            "release_id": RELEASE_ID, "headers_or_auth_exported": False,
        })
        marker = current.set((role, config, expected_wire, context["purpose"]))
        try:
            outcome = original_generate(adapter, messages, **kwargs)
            capture_outcome(outcome, api_key, ledger / f"slot-{slot:02d}-normal-outcome.json", slot=state["attempts"])
            require_active_deadline(deadline)
            if outcome.error is not None:
                require(state["settled"] == state["attempts"] and state["unknown"] == 0,
                        "NORMAL_ERROR_REQUIRES_KNOWN_SETTLEMENT")
                state["normal_adapter_error_observed"] = True
                outcome.error = {**outcome.error, "retryable": False}
                create(ledger / f"slot-{slot:02d}-normal-error.json", {
                    "status": "CASE_FAILED_KNOWN_SETTLED_NORMAL_ERROR", "raw_error_exported": False,
                    "other_independent_cases_disabled": False,
                })
                # Return to the ordinary Main gate/fail_job path, preserving failure.
                sync()
            if has_secret(outcome.raw_text, api_key):
                stop("NORMAL_ADAPTER_SECRET_ECHO_WITHHELD")
            return outcome
        finally:
            current.reset(marker)

    def guarded_generate(adapter, messages, **kwargs):
        if abort_event is not None and abort_event.is_set():
            stop("OWNED_SCOPE_CLOSURE_DENIES_FURTHER_POSTS")
        try:
            return generate_impl(adapter, messages, **kwargs)
        except NativeTransportStop as exc:
            stop(exc.code)
        except BudgetError as exc:
            stop(exc.code)
        except Exception:  # noqa: BLE001 - no private exception detail or continued provider execution.
            stop("NORMAL_GENERATE_BOUNDARY_FAILED")

    try:
        with patch.object(adapters, "open_provider", guarded_open), patch.object(
            adapters.LLMAdapter, "generate", guarded_generate
        ):
            yield view
    except Exception as exc:
        state["stop"] = state["stop"] or getattr(exc, "code", "NORMAL_CONTEXT_FAILED")
        cohort = snapshot(COHORT_LEDGER)
        if shared_risk(state["stop"], cohort["unknown_full_hold_USD"]):
            stop_cohort(COHORT_LEDGER, "UNSAFE_NORMAL_TRANSPORT")
        raise
    finally:
        sync()
        if not state["stop"] and state["unknown"] == 0 and not view["cohort_permanently_stopped"]:
            view["status"] = "BOUNDED_NORMAL_TRANSPORT_CLOSED"
        cohort = snapshot(COHORT_LEDGER)
        create(ledger / "final-receipt.json", {
            "schema": "5703_repair90_case_normal_transport_final_v1", "batch_id": BATCH_ID,
            "case_id": case_id, "question_sha256": case["question_sha256"],
        "checker_output_policy": output_policy, "checker_schema_name": checker_schema_name,
        "supplement_descriptor_sha256": scope.get("supplement_descriptor_sha256"),
        "checker_high_manifest_sha256": scope.get("checker_high_manifest_sha256"),
        "checker_high8192_manifest_sha256": scope.get("checker_high8192_manifest_sha256"),
        "fresh_validation_descriptor_sha256": scope.get("fresh_validation_descriptor_sha256"),
            "actual_posts": state["attempts"], "settled_numeric_cost_observations": state["settled"],
            "native_settled_known_cost_USD": str(state["known"]),
            "native_unresolved_full_protection_USD": str(state["unknown"]), "stop_code": state["stop"],
            "cohort_claimed_posts": cohort["claimed_physical_posts"], "cohort_known_cost_USD": cohort["known_cost_USD"],
            "cohort_unknown_full_hold_USD": cohort["unknown_full_hold_USD"],
            "cohort_request_cap": 24, "cohort_cost_cap_USD": "1.00", "case_request_cap": 4,
            "cohort_permanently_stopped": cohort["cohort_stopped"],
            "cohort_protocol_sha256": scope["cohort_protocol_sha256"], "authorization": COHORT_AUTHORIZATION,
            "old_closed12_occupancy_in_new_budget": 0, "old85_86_occupancy_in_new_budget": 0, "whole_case_seconds_cap": 180,
            "deadline_anchor": "normal transport case claim after startup prewarm before listener",
            "closure_status": "CLOSED_NUMERIC_NO_UNKNOWN"
                if state["settled"] == state["attempts"] and state["unknown"] == 0
                and Decimal(cohort["unknown_full_hold_USD"]) == 0
                else "UNRESOLVED_RETAIN_PROTECTION",
            "normal_adapter_error_observed": state["normal_adapter_error_observed"], "automatic_retries": 0, "auth_exported": False,
        })
