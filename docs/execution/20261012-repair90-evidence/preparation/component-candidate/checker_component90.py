"""One planned Repair90 checker-only Qwen contrast of a closed saved task.

Inert on import. No credential lookup, teacher replay, database or publication.
Root freezes a reviewed descriptor separately and supplies an in-memory key.
One physical POST uses Main's adapter; raw financial observations precede decoding.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from time import monotonic
from unittest.mock import patch
from urllib.error import HTTPError

import budget88 as budget
from normal_transport88 import (
    MAIN, MAX_RESPONSE, URL, NativeTransportStop, capture_normal_outcome,
    create, diagnostic_value, has_secret, number, require,
)

SCHEMA_SHA = "864212a5e636d2cadbc34328f431712a954c30130848a31e64e66e4bdedbc926"
SOURCE_VERSION = "369bba3c1ba0e0007b346142988ccc3a242e13505e22513a1a13166a2fe4b2fc"
RUNTIME = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-repair90-runtime")
QWEN_CONFIG_ID = "d78c2a1a-caac-4024-b5f5-2a652414cb0b"
QWEN_MODEL = "qwen/qwen3.8-flash"
QWEN_PROFILE = "qwen38_alibaba_v2"
KIND = "checker_only_same_input_qwen_contrast"
PURPOSE = "diagnostic_check"
SECONDS_CAP = 180
COMPONENT_BASES = {
    "component01qwen": "case01", "component08qwen": "case08", "component06qwen": "case06",
    "component_positiveqwen": None, "component_negativeqwen": None,
}
ARTIFACT_ROLES = {"scope", "checker_inputs", "checker_claim", "base_final", "base_api_closure", "base_journey"}


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _pin(path):
    path = Path(path).absolute()
    require(path.resolve() == path and path.is_file() and not path.is_symlink()
            and not getattr(path, "is_junction", lambda: False)(), "COMPONENT_PUBLIC_PATH_CHANGED")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime(runtime):
    runtime = Path(runtime).absolute()
    require(runtime == RUNTIME and runtime.resolve(strict=True) == runtime and runtime.is_dir()
            and not runtime.is_symlink() and not getattr(runtime, "is_junction", lambda: False)(),
            "COMPONENT_NEW_REPAIR90_RUNTIME_REQUIRED")
    return runtime


def _public(runtime, relative):
    relative = Path(relative)
    require(not relative.is_absolute() and not relative.drive and ".." not in relative.parts,
            "COMPONENT_PUBLIC_RELATIVE_PATH_REQUIRED")
    path = runtime / relative
    current = path
    while current != runtime:
        require(not current.is_symlink() and not getattr(current, "is_junction", lambda: False)(),
                "COMPONENT_PUBLIC_PATH_CHANGED")
        current = current.parent
    require(path.resolve(strict=True) == path and path.is_file(), "COMPONENT_PUBLIC_FILE_REQUIRED")
    return path


def _source_pins(pins):
    require(type(pins) is list and len(pins) == 16 and _digest(pins) == SOURCE_VERSION,
            "COMPONENT_EXACT_B16_SOURCE_VERSION_REQUIRED")
    seen = set()
    for row in pins:
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}
                and type(row["bytes"]) is int and row["bytes"] > 0, "COMPONENT_SOURCE_PIN_SHAPE")
        path = Path(row["path"])
        require(path.is_absolute() and path.resolve(strict=True).is_relative_to(MAIN.resolve(strict=True))
                and not path.is_symlink() and path not in seen
                and path.stat().st_size == row["bytes"] and _pin(path) == row["sha256"],
                "COMPONENT_MAIN_SOURCE_CHANGED")
        seen.add(path)


def _artifact_records(runtime, descriptor):
    pins = descriptor["actual_input_artifact_pins"]
    require(type(pins) is list and len(pins) == len(ARTIFACT_ROLES), "COMPONENT_ARTIFACT_PIN_SET_REQUIRED")
    records = {}
    for row in pins:
        require(type(row) is dict and set(row) == {"role", "relative_path", "bytes", "sha256"}
                and row["role"] in ARTIFACT_ROLES and row["role"] not in records,
                "COMPONENT_ARTIFACT_PIN_SHAPE")
        path = _public(runtime, row["relative_path"])
        require(type(row["bytes"]) is int and path.stat().st_size == row["bytes"]
                and _pin(path) == row["sha256"], "COMPONENT_ARTIFACT_CHANGED")
        records[row["role"]] = budget._read(path)
    require(set(records) == ARTIFACT_ROLES, "COMPONENT_ARTIFACT_PIN_SET_REQUIRED")
    return records


def _contrast_config(original):
    before = original.to_dict()
    changes = {"model": QWEN_MODEL, "openrouter_route_profile": QWEN_PROFILE,
               "configuration_id": QWEN_CONFIG_ID}
    after = {**before, **changes}
    delta = {key: {"before": before.get(key), "after": value} for key, value in changes.items()}
    return after, delta


def compile_task(runtime, descriptor):
    """Preserve the complete saved task; alter only the declared model configuration."""
    from generation import ModelConfig, providers
    from generation.lossless_unit_findings_v1 import PROVIDER_SCHEMA_NAME
    from generation.openrouter_routes import prepare_schema_wire
    from generation.reliability_v4 import compact_schema
    from generation.source_relations_v2 import ReliableUnitCheck

    runtime = _runtime(runtime)
    records = _artifact_records(runtime, descriptor)
    inputs, scope, claim = (records[role] for role in ("checker_inputs", "scope", "checker_claim"))
    _source_pins(scope["source_pins"])
    require(inputs["role"] == "checker" and inputs["question"] == scope["question_text"]
            and hashlib.sha256(inputs["question"].encode("utf-8")).hexdigest() == descriptor["question_sha256"]
            and scope["case_id"] == descriptor["base_case_id"]
            and scope["cohort_protocol_sha256"] == descriptor["protocol_sha256"],
            "COMPONENT_ORIGINAL_CHECKER_TASK_REQUIRED")
    messages = inputs["messages"]
    require(type(messages) is list and len(messages) == 2
            and [row.get("role") for row in messages] == ["system", "user"]
            and all(type(row) is dict and set(row) == {"role", "content"}
                    and type(row["content"]) is str for row in messages), "COMPONENT_MESSAGES_CHANGED")
    messages = [{"role": row["role"], "content": row["content"]} for row in messages]
    require(messages == inputs["messages"], "COMPONENT_MESSAGES_CHANGED")
    schema = compact_schema(ReliableUnitCheck)
    original = ModelConfig(**scope["expected_checker_config"])
    contrast_dict, delta = _contrast_config(original)
    contrast = ModelConfig(**contrast_dict)
    require(original.max_tokens == contrast.max_tokens == 8192
            and original.structured_output_mode == contrast.structured_output_mode == "json_object"
            and original.timeout_seconds == contrast.timeout_seconds == 45
            and original.provider == contrast.provider == "openai_compatible"
            and original.base_url == contrast.base_url == "https://openrouter.ai/api/v1"
            and original.reasoning_effort is contrast.reasoning_effort is None,
            "COMPONENT_EXACT_CONFIG_CHANGED")
    original_wire = providers.payload(original, messages, schema, PROVIDER_SCHEMA_NAME)
    original_wire, _ = prepare_schema_wire(original, original_wire, schema)
    contrast_wire = providers.payload(contrast, messages, schema, PROVIDER_SCHEMA_NAME)
    contrast_wire, _ = prepare_schema_wire(contrast, contrast_wire, schema)
    require(original_wire == inputs["normal_compiled_wire"]
            and hashlib.sha256(_bytes(original_wire)).hexdigest() == claim["wire_sha256"]
            and len(_bytes(original_wire)) == claim["wire_bytes"], "COMPONENT_ORIGINAL_WIRE_CHANGED")
    require(original_wire["messages"] == contrast_wire["messages"]
            and original_wire["response_format"] == contrast_wire["response_format"]
            and {key: value for key, value in original_wire.items() if key not in {"model", "provider", "reasoning"}}
                == {key: value for key, value in contrast_wire.items() if key not in {"model", "provider", "reasoning"}},
            "COMPONENT_TASK_OR_SCHEMA_CHANGED")
    route = contrast_wire["provider"]
    require(contrast_wire["model"] == QWEN_MODEL and route["order"] == ["alibaba"]
            and route["allow_fallbacks"] is False
            and Decimal(str(route["max_price"]["prompt"])) == Decimal("0.15")
            and Decimal(str(route["max_price"]["completion"])) == Decimal("0.47")
            and contrast_wire["reasoning"].get("enabled") is False
            and "effort" not in contrast_wire["reasoning"], "COMPONENT_QWEN_ROUTE_CHANGED")
    prepared = providers.prepare_checker_transport(contrast, messages, schema, PROVIDER_SCHEMA_NAME)
    original_prepared = providers.prepare_checker_transport(original, messages, schema, PROVIDER_SCHEMA_NAME)
    context = prepared["prepared"].context
    require(context.packet_json == original_prepared["prepared"].context.packet_json
            and context.descriptor() == original_prepared["prepared"].context.descriptor()
            and context.canonical_schema_sha256 == SCHEMA_SHA
            and context.packet["question"] == inputs["question"], "COMPONENT_FULL_PACKET_CHANGED")
    return inputs, scope, messages, schema, contrast, contrast_wire, context, original_wire, delta


def prepare_descriptor(runtime, instance_id, base_case_id, selected_checker_slot, review_binding):
    """Return public metadata only; Root alone freezes and admits each descriptor."""
    runtime = _runtime(runtime)
    require(instance_id in COMPONENT_BASES and base_case_id in {"case01", "case08", "case06"}
            and COMPONENT_BASES[instance_id] in {None, base_case_id}
            and type(selected_checker_slot) is int and 1 <= selected_checker_slot <= 4,
            "COMPONENT_FINITE_BASE_BINDING_REQUIRED")
    require(type(review_binding) is dict and bool(review_binding), "COMPONENT_EXPLICIT_REVIEW_BINDING_REQUIRED")
    slot = f"{selected_checker_slot:02d}"
    paths = {
        "scope": f"scope88-{base_case_id}.json",
        "checker_inputs": f"{base_case_id}/native-provider70/slot-{slot}-public-inputs.json",
        "checker_claim": f"{base_case_id}/native-provider70/slot-{slot}-claim.json",
        "base_final": f"{base_case_id}/native-provider70/final-receipt.json",
        "base_api_closure": f"{base_case_id}/api-closure77.json",
        "base_journey": f"{base_case_id}/journey-receipt88.json",
    }
    artifacts = [{"role": role, "relative_path": relative,
        "bytes": _public(runtime, relative).stat().st_size, "sha256": _pin(_public(runtime, relative))}
        for role, relative in paths.items()]
    scope = budget._read(_public(runtime, paths["scope"]))
    descriptor = {"schema": "repair90_checker_component_descriptor_v1", "authorization": budget.AUTHORIZATION,
        "instance_id": instance_id, "kind": KIND, "base_case_id": base_case_id,
        "protocol_sha256": scope["cohort_protocol_sha256"], "question_sha256": scope["question_sha256"],
        "selected_checker_slot": selected_checker_slot, "actual_input_artifact_pins": artifacts,
        "source_pins": scope["source_pins"], "review_binding": json.loads(json.dumps(review_binding, allow_nan=False)),
        "root_selected_authorized": True, "automatic_retry_or_reclaim": False}
    _, _, _, _, config, wire, context, original_wire, delta = compile_task(runtime, descriptor)
    descriptor.update(input_artifact_sha256=next(row["sha256"] for row in artifacts if row["role"] == "checker_inputs"),
        original_wire_sha256=hashlib.sha256(_bytes(original_wire)).hexdigest(),
        contrast_wire_sha256=hashlib.sha256(_bytes(wire)).hexdigest(), contrast_wire_bytes=len(_bytes(wire)),
        context_sha256=context.digest, model_config=config.to_dict(), model_config_sha256=_digest(config.to_dict()),
        model_config_delta=delta, controller_pins={name: _pin(_public(runtime, name)) for name in
            ("budget88.py", "normal_transport88.py", "checker_component90.py")})
    return descriptor


def assess(outcome, context, review_binding):
    """Apply original packet assessors; this is not the app publication validator."""
    from generation.parser import strict_json
    from generation.reliability_v4 import normalize_judgment
    from generation.reliability_v5 import assess_requirements
    from generation.source_relations_v2 import ReliableUnitCheck, assess_source_relations

    base = {"publication_exercised": False, "independent_quality_review_required": True,
            "review_binding": dict(review_binding), "full_input_context_sha256": context.digest}
    if outcome.error is not None:
        return {**base, "status": "NORMAL_ADAPTER_REJECTED", "normal_error": outcome.error,
                "schema_valid": False, "semantic_assessors_exercised": False}
    typed = strict_json(outcome.raw_text)
    ReliableUnitCheck.model_validate(typed, strict=True)
    packet = context.packet
    _, binding = normalize_judgment(typed, packet["ACTUAL_CITATION_BINDINGS"])
    relation_contract, relation_defects, relations = assess_source_relations(
        typed, packet["CLAIMS"], packet["ACTUAL_CITATION_BINDINGS"], packet["SOURCE_FRAGMENTS"])
    requirement_contract, requirement_defects, coverage = assess_requirements(
        typed, packet["CONTEXT_COVERAGE"], packet["SOURCE_FRAGMENTS"],
        answer_mode=packet["answer_mode"], teaching_mode=packet["POLICY"]["teaching_mode"])
    return {**base, "status": "PACKET_DIAGNOSTIC_COMPLETE_REVIEW_REQUIRED",
            "schema_valid": True, "semantic_assessors_exercised": True,
            "binding_issues": binding, "source_contract_issues": relation_contract,
            "source_semantic_defects": relation_defects,
            "requirement_contract_issues": requirement_contract,
            "requirement_semantic_defects": requirement_defects,
            "source_assessment": relations, "semantic_coverage": coverage,
            "actual_model_judgment": typed,
            "canonical_claim_count": len(typed["claims"]),
            "canonical_requirement_count": len(typed["requirements"])}


def run(runtime, instance_id, descriptor_sha256, *, api_key):
    """One physical POST through Main's adapter; same input, route contrast, no publication."""
    from generation import adapters

    runtime = _runtime(runtime)
    ledger = runtime / "cohort-ledger"
    require(runtime.resolve() == runtime and type(api_key) is str and len(api_key) >= 16,
            "COMPONENT_EXPLICIT_MEMORY_BOUNDARY_REQUIRED")
    require(budget.POST_CAP == 24 and budget.COST_CAP == Decimal("1.00")
            and budget.CASE_POST_CAP == 4 and budget.HOLD == Decimal("0.0714688"),
            "COMPONENT_EXACT_SHARED_REPAIR90_BUDGET_REQUIRED")
    descriptor = budget.validate_component(ledger, instance_id, descriptor_sha256, admission=True)
    require(Path(__file__).resolve() == _public(runtime, "checker_component90.py")
            and _pin(Path(__file__)) == descriptor["controller_pins"]["checker_component90.py"],
            "COMPONENT_LOADED_CONTROLLER_CHANGED")
    require(prepare_descriptor(runtime, instance_id, descriptor["base_case_id"],
        descriptor["selected_checker_slot"], descriptor["review_binding"]) == descriptor,
        "COMPONENT_FROZEN_PREFLIGHT_CHANGED")
    inputs, scope, messages, schema, config, wire, context, _, _ = compile_task(runtime, descriptor)
    for row in scope["source_pins"]:
        path = Path(row["path"])
        require(path.is_absolute() and path.resolve().is_relative_to(MAIN.resolve())
                and not path.is_symlink() and path.stat().st_size == row["bytes"]
                and _pin(path) == row["sha256"], "COMPONENT_MAIN_SOURCE_CHANGED")
    require(Path(adapters.__file__).resolve() == (MAIN / "generation/adapters.py").resolve(),
            "COMPONENT_LOADED_ADAPTER_CHANGED")
    expected = _bytes(wire)
    require(0 < len(expected) <= budget.MAX_WIRE_BYTES
            and len(expected) == descriptor["contrast_wire_bytes"]
            and hashlib.sha256(expected).hexdigest() == descriptor["contrast_wire_sha256"],
            "COMPONENT_EXACT_CONTRAST_WIRE_REQUIRED")
    require(not has_secret(wire, api_key), "AUTH_IN_PUBLIC_WIRE_WITHHELD")
    price_bound = Decimal(len(expected)) * Decimal("0.15") / 1000000 + Decimal(8192) * Decimal("0.47") / 1000000
    require(price_bound <= budget.HOLD, "COMPILED_BYTE_PRICE_BOUND_EXCEEDS_HOLD")
    output = runtime / instance_id
    require(not output.exists() and not output.is_symlink(), "COMPONENT_OUTPUT_REPLAY_FORBIDDEN")
    budget.claim_component(ledger, instance_id, descriptor_sha256)
    output.mkdir(exist_ok=False)
    create(output / "public-inputs.json", {**inputs, "purpose": PURPOSE,
           "normal_compiled_wire": wire, "component_descriptor_sha256": descriptor_sha256,
           "publication_exercised": False, "source_task_reused_unchanged": True})
    state = {"posts": 0, "global_slot": None, "stop": None}
    started = monotonic()
    original_open = adapters.open_provider

    def stop(code):
        state["stop"] = state["stop"] or code
        raise NativeTransportStop(state["stop"])

    def observe(raw, status):
        text = raw.decode("utf-8", errors="replace") if type(raw) is bytes and len(raw) <= MAX_RESPONSE else None
        safe = diagnostic_value({"raw_response_text": text, "http_status": status,
                                 "normal_adapter_parse_started": False, "auth_exported": False}, api_key)
        require(not has_secret(safe, api_key), "RAW_RESPONSE_SECRET_WITHHELD")
        create(output / "raw-response.json", safe)
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
        if text is not None:
            try:
                decoded = json.loads(text, object_pairs_hook=pairs)
            except (ValueError, UnicodeError, RecursionError):
                pass
        usage = decoded.get("usage") if type(decoded) is dict else None
        cost = number(usage.get("cost")) if type(usage) is dict and not duplicate else None
        protection = max([budget.HOLD, *numeric_fields, *([cost] if cost is not None else [])])
        safe_status = type(status) is int and 100 <= status <= 599
        safe_body = text is not None and not duplicate and not has_secret(decoded, api_key)
        safe_cost = cost is not None and protection == budget.HOLD
        create(output / "financial.json", {"numeric_gateway_cost_USD": str(cost) if cost is not None else None,
               "protection_USD": str(protection), "observed_before_adapter_parse": True,
               "duplicate_json_keys": duplicate, "http_status": status if safe_status else None})
        budget.settle_post(ledger, state["global_slot"], cost if safe_cost else protection if numeric_fields else None,
                           status_safe=safe_status and safe_body and safe_cost)
        if not (safe_status and safe_body and safe_cost):
            budget.stop_cohort(ledger, "UNSAFE_NORMAL_TRANSPORT")
            stop("COMPONENT_RESPONSE_UNSAFE_RETAIN_PROTECTION")

    class ObservedResponse:
        def __init__(self, original):
            self.original = original
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
            raw = self.original.read(size)
            observe(raw, self.status)
            return raw

    def guarded_open(envelope, *, timeout):
        require(state["posts"] == 0, "COMPONENT_ONE_PHYSICAL_POST_ONLY")
        require(envelope.full_url == URL and envelope.get_method() == "POST"
                and envelope.data == expected and envelope.get_header("Authorization") == "Bearer " + api_key
                and type(timeout) in (int, float) and 0 < timeout <= 45
                and monotonic() - started + timeout <= SECONDS_CAP, "COMPONENT_EXACT_WIRE_OR_DEADLINE_CHANGED")
        state["global_slot"] = budget.reserve_post(ledger, instance_id, "checker",
            hashlib.sha256(expected).hexdigest(), len(expected), purpose=PURPOSE)
        state["posts"] += 1
        create(output / "physical-claim.json", {"global_slot": state["global_slot"],
               "wire_sha256": descriptor["contrast_wire_sha256"], "wire_bytes": len(expected),
               "maximum_hold_USD": str(budget.HOLD), "conservative_byte_price_bound_USD": str(price_bound),
               "request_retries": 0, "auth_exported": False})
        try:
            return ObservedResponse(original_open(envelope, timeout=timeout))
        except HTTPError as exc:
            raw = exc.read(MAX_RESPONSE + 1)
            try:
                observe(raw, exc.code)
            finally:
                exc.close()
            exc.fp = BytesIO(raw)
            exc.read = exc.fp.read
            raise

    try:
        from generation.lossless_unit_findings_v1 import PROVIDER_SCHEMA_NAME
        adapter = adapters.LLMAdapter(config, api_key=api_key, retain_invalid_output=True)
        normal_started = monotonic()
        with patch.object(adapters, "open_provider", guarded_open):
            outcome = adapter.generate(messages, response_schema=schema,
                                       response_schema_name=PROVIDER_SCHEMA_NAME, timeout_seconds=config.timeout_seconds)
        normal_elapsed_ms = round((monotonic() - normal_started) * 1000)
        capture_normal_outcome(outcome, api_key, output / "normal-outcome.json", slot=1)
        result = assess(outcome, context, descriptor["review_binding"])
        result["normal_adapter_complete_ms"] = normal_elapsed_ms
        result["comparison_limitations"] = "Saved Gemini HIGH task then one new Qwen route; model, route, reasoning and price differ; n=1, order/cache uncontrolled; no pure-model causal or quality PASS claim."
        create(output / "diagnostic-result.json", diagnostic_value(result, api_key))
        return result
    except Exception as exc:
        state["stop"] = state["stop"] or getattr(exc, "code", "COMPONENT_LOCAL_FAILURE_RETAIN_RECORDS")
        raise
    finally:
        if state["global_slot"] is not None:
            _, _, _, settlements, exposures, _, _, _ = budget._scan(ledger)
            if state["global_slot"] not in settlements and state["global_slot"] not in exposures:
                budget.settle_post(ledger, state["global_slot"], None, status_safe=False)
                budget.stop_cohort(ledger, "UNSAFE_NORMAL_TRANSPORT")
                state["stop"] = state["stop"] or "COMPONENT_UNOBSERVED_RESPONSE_RETAIN_PROTECTION"
        create(output / "final-receipt.json", {"instance_id": instance_id,
               "physical_posts": state["posts"], "global_slot": state["global_slot"],
               "elapsed_ms": round((monotonic() - started) * 1000), "stop_code": state["stop"],
               "cohort": budget.snapshot(ledger), "publication_exercised": False,
               "independent_quality_review_required": True, "automatic_retry_or_reclaim": False,
               "auth_exported": False})
