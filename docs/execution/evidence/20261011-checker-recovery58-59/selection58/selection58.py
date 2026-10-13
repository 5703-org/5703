"""Root-reviewed preparation / one correction POST. No automatic retries."""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
W = HERE.parent
MAIN = Path(r"E:\5703\learning-assistant")
OLD = W / "5703-selection54"
URL = "https://openrouter.ai/api/v1/chat/completions"
SCHEMA = "joint_check_source_relations_v2"
PER = Decimal("0.055")
CAP = Decimal("0.36")
AUTH = "允许将同一71段教材、测试问题及已有回答发送到OpenRouter Gemini/Vertex，最多再8次、总额0.36美元，用于选证修复测试"
PINS = {
    "base_wire": (OLD / "wire54.json", "0e5a761599e224f50a800718f19216198680923e8c8ac617b4f9b5c384c0344c"),
    "seed": (OLD / "guided56/actual54/selection54_1-result.json", "d6b5fc6738107b9ec5b1ca08015a53d22e1264573c188eac95dde93afee8a274"),
    "index": (OLD / "index54-56.json", "222605cf218df37788814f8f467eecfbafc66231d875135273273204c1b872b9"),
    "prior54": (OLD / "actual54/result54.json", "900227ca70d946431a0a39aaa1ad1f0a4d74a9d2bf5d3c4fae88c4894b773b0f"),
    "prior55": (OLD / "guided55/actual54/result54.json", "fd1496cfdfa3fdada4b15bfa264deb896cdd44d5eb9b51e9e955ec6c99ae199d"),
    "prior56": (OLD / "guided56/actual54/result54.json", "165ffa49e52c54ea5b044515c43a0c78dff3f4be1d94bc119d180a6ab2d2edac"),
    "checked": (MAIN / "generation/checked.py", "b4e0cfddbac5ccc96e15aa217f3e26f649782d7bf545bb8dedc6d667b8b5e770"),
    "relations": (MAIN / "generation/source_relations_v2.py", "ab22171c03566ed1f8b97e67bb1d0d5f4b276e0ab0bcc40be487f3b296ceeb11"),
    "legacy": (W / "5703-unit-proof-high50-replay-candidate/run_checker_compatible43_CANDIDATE.py", "805d042d61f265d305bda0d29ae7114a7d58f3fc6ac72f32d855c701f0d624ac"),
}
_LEGACY = None


def require(ok, code):
    if not ok:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(name):
    path, digest = PINS[name]
    raw = path.read_bytes()
    require(sha(raw) == digest, "PIN_CHANGED:" + name)
    return raw


def save(path, value):
    require(path.resolve().is_relative_to(HERE) and not path.is_symlink(), "OWNED_NEW_OUTPUT_REQUIRED")
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def legacy_module():
    global _LEGACY
    read("legacy")
    if _LEGACY is not None:
        return _LEGACY
    spec = importlib.util.spec_from_file_location("selection58_reused_public", PINS["legacy"][0])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.install_public_implementation()  # Existing reviewed route components; no auth here.
    module.load_source("root_pure_compatible_schema50", module.PINS["validator"])
    _LEGACY = module
    return module


def production_feedback(issues):
    """Evaluate only the pinned production append expression, never the generation loop."""
    from generation.checked import _json

    tree = ast.parse(read("checked").decode("utf-8"))
    matches = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "check_messages" for t in node.targets)
               and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add)
               and isinstance(node.value.left, ast.Name) and node.value.left.id == "check_messages"]
    require(len(matches) == 1, "EXACT_PRODUCTION_APPEND_REQUIRED")
    record = matches[0].value.right.elts[0]
    content = next(v for k, v in zip(record.keys, record.values) if k.value == "content")
    allowed = (ast.Constant, ast.BinOp, ast.Add, ast.Name, ast.Load, ast.IfExp,
               ast.JoinedStr, ast.FormattedValue, ast.Call)
    require(all(isinstance(n, allowed) for n in ast.walk(content)), "BOUNDED_APPEND_AST_REQUIRED")
    require(all(isinstance(n.func, ast.Name) and n.func.id == "transport_json"
                for n in ast.walk(content) if isinstance(n, ast.Call)), "SOLE_SERIALIZER_REQUIRED")
    env = dict(contract_feedback="", compact_joint=False, pending_action_gate=False,
               checker_schema_name=SCHEMA, inconsistencies=issues, transport_json=_json)
    text = eval(compile(ast.Expression(content), str(PINS["checked"][0]), "eval"),
                {"__builtins__": {}}, env)
    require("Return the complete " + SCHEMA + " schema." in text, "CURRENT_SCHEMA_NAME_REQUIRED")
    return {"role": "user", "content": text}, [matches[0].lineno, matches[0].end_lineno]


def prepare():
    for name in PINS:
        read(name)
    prior = [json.loads(read(n)) for n in ("prior54", "prior55", "prior56")]
    slots = sum(p["submission_slots"] for p in prior)
    known = sum((Decimal(p["known_cost_USD"]) for p in prior), Decimal(0))
    hold = sum((Decimal(p["UNKNOWN_hold_USD"]) for p in prior), Decimal(0))
    require(slots == 5 and known == Decimal("0.11072166") and hold == 0, "SETTLED_SAME_GRANT_REQUIRED")
    require(slots + 1 <= 8 and known + hold + PER <= CAP, "AGGREGATE_BUDGET_REQUIRED")
    legacy = legacy_module()
    from generation.checker_encoding import decode
    from generation.source_relations_v2 import assess_source_relations
    from generation import source_relations_v2, checked
    require(Path(source_relations_v2.__file__) == PINS["relations"][0]
            and Path(checked.__file__) == PINS["checked"][0], "ACTUAL_CURRENT_MAIN_REQUIRED")
    body = json.loads(read("base_wire"))
    original_messages = deepcopy(body["messages"])
    data = decode(json.loads(body["messages"][1]["content"]))
    seed = json.loads(read("seed"))
    validation = legacy.validate_output(seed["provider_result"]["raw_text"], data)
    local = validation["original_full_local_checker_result"]
    issues, defects, _ = assess_source_relations(local["typed"], data["CLAIMS"],
                                              data["ACTUAL_CITATION_BINDINGS"], data["SOURCE_FRAGMENTS"])
    expected = [{"code": "RELATION_ASSESSED_FRAGMENT_MISMATCH",
                 "claim_id": "claim_4bbb28fe7a90b6a3f87b6b75_1", "unit_id": "U02",
                 "fragment_id": "F011", "evidence_id": "ev_002"}]
    require(issues == expected and not defects and not local["binding_issues"]
            and not local["consistency_issues"], "EXACT_RETAINED_MISMATCH_REQUIRED")
    feedback, location = production_feedback(issues)
    body["messages"].append(feedback)
    require(body["messages"][:-1] == original_messages and len(body["messages"]) == 3,
            "ONLY_CORRECTION_APPEND_REQUIRED")
    require(len(data["SOURCE_FRAGMENTS"]) == 71 and len(data["CLAIMS"]) == 10
            and sum(len(r["units"]) for r in data["SOURCE_SYNTACTIC_UNITS"]) == 19,
            "ORIGINAL_71_10_19_REQUIRED")
    from generation.types import ModelConfig
    from generation.providers import endpoint, payload
    from generation.openrouter_routes import prepare_schema_wire
    cfg = ModelConfig(provider="openai_compatible", model=body["model"],
                      base_url="https://openrouter.ai/api/v1", window_tokens=131072, max_tokens=8192,
                      temperature=None, timeout_seconds=60.0, structured_output_mode="json_schema",
                      reasoning_effort=None, configuration_id="model-settings:74c8201e-aca0-400d-bcc5-5785e24c1c11",
                      openrouter_route_profile="gemini35_google_vertex_high_research_v1")
    cfg.validate()
    schema = body["response_format"]["json_schema"]["schema"]
    actual, transport = prepare_schema_wire(cfg, payload(cfg, body["messages"], schema, SCHEMA), schema)
    require(actual == body and transport == {} and endpoint(cfg) == URL, "UNCHANGED_REAL_ROUTE_WIRE_REQUIRED")
    wire = json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    bound = (Decimal(len(wire) + 4096) * Decimal("0.3") + Decimal(8192) * Decimal("2.5")) / Decimal(1000000)
    require(len(wire) <= 98304 and bound <= PER, "COMPLETE_WIRE_HOLD_REQUIRED")
    review = dict(status="PREPARED_NOT_EXECUTED", direct_user_quote=AUTH,
                  repeated_quote_creates_new_grant=False, prior_slots=slots, prior_known_USD=str(known),
                  prior_new_UNKNOWN_USD=str(hold), grant_cap_USD=str(CAP), max_new_POSTs=1,
                  complete_single_request_hold_USD=str(PER), conservative_price_bound_USD=str(bound),
                  remaining_slots_before=3, remaining_USD_before="0.24927834", automatic_retries=0,
                  wire_bytes=len(wire), wire_sha256=sha(wire), recipient=URL,
                  input_pins={n: {"path": str(p), "sha256": h} for n, (p, h) in PINS.items()},
                  controller_sha256=sha(Path(__file__).read_bytes()), correction_source_lines=location,
                  correction_feedback=feedback, original_DATA_unchanged=True,
                  prior_checker_JSON_outbound=False, exposed_plans_outbound=False,
                  source_fragments=71, claims=10, syntactic_units=19,
                  historical_grants_UNKNOWN_and_ledgers="Unmodified; not settled or reused by this child",
                  free_prepare_auth_DB_network_operations=0, semantic_acceptance="PENDING_INDEPENDENT_REVIEW",
                  limitation="One diagnostic correction; not native integration, held-out quality, RAG or full-DOM timing")
    return body, wire, review, cfg, data, legacy


def execute(review_sha):
    # Root must receive approval of this exact execution action. This flag is not approval.
    body, wire, review, cfg, data, legacy = prepare()
    require(sha((HERE / "review58.json").read_bytes()) == review_sha, "ROOT_REVIEW_CHANGED")
    require(json.loads((HERE / "review58.json").read_bytes()) == review
            and (HERE / "wire58-PREPARED-UNVERIFIED.json").read_bytes() == wire, "FROZEN_REVIEW_WIRE_REQUIRED")
    out = HERE / "actual58"
    out.mkdir()  # Exclusive child scope: rerunning this execution is forbidden.
    report = dict(status="STARTED_NOT_POSTED", post_attempts=0, known_cost_USD="0", UNKNOWN_hold_USD="0",
                  prior_slots=5, prior_known_USD="0.11072166", prior_new_UNKNOWN_USD="0",
                  max_new_POSTs=1, automatic_retries=0, started_UTC=datetime.now(timezone.utc).isoformat(),
                  old_ledgers_written=False, credentials_exported=False, native_publication=False,
                  raw_receipt_pins=[],
                  source_entailment_certified=False, quality_acceptance="PENDING_INDEPENDENT_REVIEW")
    save(out / "intent.json", {**report, "review_sha256": review_sha, "wire_sha256": sha(wire)})
    adapter = key = redactor = None
    original_open = None
    try:
        for p in (MAIN, MAIN / "backend"):
            if str(p) not in sys.path:
                sys.path.append(str(p))
        helper = legacy.load_source("selection58_original_approved_credential", legacy.PINS["credential_helper"])
        require(helper.TARGET_DB == "cs30_week10_pair_b_20261009_01", "SOLE_ISOLATED_CREDENTIAL_DB_REQUIRED")
        key = helper.approved_credential(helper.WORKSPACE_ID)  # Existing consumer, same DB; no fallback.
        require(isinstance(key, str) and bool(key), "ORIGINAL_CREDENTIAL_UNAVAILABLE")
        diagnostics = legacy.load_source("selection58_original_diagnostics", legacy.PINS["diagnostics"])
        redactor = diagnostics.Redactor((key,))
        from generation.adapters import LLMAdapter
        from generation import adapters as module
        adapter = LLMAdapter(cfg, api_key=key, retain_invalid_output=True)
        key = None
        original_open = module.open_provider

        def single_post(envelope, timeout):
            require(report["post_attempts"] == 0 and envelope.full_url == URL
                    and envelope.get_method() == "POST" and envelope.data == wire, "ONE_EXACT_POST_REQUIRED")
            fresh = prepare()
            require(fresh[1] == wire and fresh[2] == review, "FROZEN_AGGREGATE_AND_INPUT_REQUIRED")
            report.update(post_attempts=1, UNKNOWN_hold_USD=str(PER), status="SUBMITTED_UNKNOWN")
            save(out / "submitted-UNKNOWN.json", {"wire_sha256": sha(wire), "hold_USD": str(PER),
                                                    "at_UTC": datetime.now(timezone.utc).isoformat()})
            try:
                return diagnostics.wrap_provider_response(original_open(envelope, timeout=timeout),
                           path_prefix=out / "raw-provider", redactor=redactor,
                           on_saved=report["raw_receipt_pins"].append)
            except legacy.urlerror.HTTPError as exc:
                diagnostics.retain_http_error_reads(exc, path_prefix=out / "raw-provider", redactor=redactor,
                                                     on_saved=report["raw_receipt_pins"].append)
                raise

        module.open_provider = single_post
        start = time.perf_counter_ns()
        result = adapter.generate(body["messages"], response_schema=body["response_format"]["json_schema"]["schema"],
                                  response_schema_name=SCHEMA, request_context={"purpose": "joint_check", "request_id": "selection58_1"},
                                  timeout_seconds=60)
        # Preserve the received observation before any local gate can raise.
        report["provider_result"] = asdict(result)
        report["provider_reports_request_submitted"] = result.request_submitted
        report["complete_adapter_return_ms"] = (time.perf_counter_ns() - start) / 1e6
        value = result.usage.get("cost") if isinstance(result.usage, dict) else None
        cost = Decimal(str(value)) if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
        uncertain = bool(result.error and (result.error.get("code") == "PROVIDER_ROUTE_MODEL_MISMATCH"
                         or result.error.get("details", {}).get("uncertain")))
        report["observed_reported_cost_USD"] = str(cost) if cost is not None else None
        settled = report["post_attempts"] == 1 and cost is not None and not uncertain
        if settled:
            report.update(known_cost_USD=str(cost), UNKNOWN_hold_USD="0",
                          status="OBSERVATION_RETAINED" if cost <= PER else "STOPPED_PRICE_OVERRUN")
        else:
            if report["post_attempts"]:
                report["UNKNOWN_hold_USD"] = str(max(PER, cost if cost is not None else PER))
            report["status"] = "STOPPED_UNKNOWN" if report["post_attempts"] else "STOPPED_BEFORE_POST"
        report["fully_settled"] = settled
        save(out / "provider-result.json", redactor.value(report["provider_result"]))
        try:
            report["validation"] = legacy.validate_output(result.raw_text, data) if result.raw_text else None
        except Exception as exc:
            report["validation_error_type"] = type(exc).__name__
            if report["status"] == "OBSERVATION_RETAINED":
                report["status"] = "STOPPED_LOCAL_VALIDATION_RETAINED"
    except BaseException as exc:
        report["status"] = ("STOPPED_RETAINED" if report.get("fully_settled")
                            else "STOPPED_UNKNOWN" if report["post_attempts"] else "STOPPED_BEFORE_POST")
        chain = []
        current = exc
        while current is not None:
            chain.append(dict(type=type(current).__name__, errno=getattr(current, "errno", None),
                              winerror=getattr(current, "winerror", None)))
            current = current.__cause__ or current.__context__
        report["error_types_codes"] = chain  # Never write auth-bearing exception text.
    finally:
        key = None
        if adapter is not None:
            adapter._api_key = None
        if original_open is not None:
            module.open_provider = original_open
        total_known = Decimal("0.11072166") + Decimal(report["known_cost_USD"])
        report.update(closed_UTC=datetime.now(timezone.utc).isoformat(), grant_aggregate_slots=5 + report["post_attempts"],
                      grant_aggregate_known_USD=str(total_known), grant_aggregate_new_UNKNOWN_USD=report["UNKNOWN_hold_USD"],
                      remaining_slots=3 - report["post_attempts"],
                      remaining_USD=str(CAP - total_known - Decimal(report["UNKNOWN_hold_USD"])))
        save(out / "result58.json", redactor.value(report) if redactor else report)
    print(json.dumps({k: report[k] for k in ("status", "post_attempts", "known_cost_USD", "UNKNOWN_hold_USD")}))
    return 0 if report["status"] == "OBSERVATION_RETAINED" else 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--review-sha256")
    args = parser.parse_args()
    if args.execute:
        require(args.review_sha256 is not None, "ROOT_REVIEW_SHA_REQUIRED")
        raise SystemExit(execute(args.review_sha256))
    body, wire, review, *_ = prepare()
    require((HERE / "wire58-PREPARED-UNVERIFIED.json").read_bytes() == wire, "PREPARED_WIRE_MUST_MATCH_REAL_COMPONENTS")
    save(HERE / "review58.json", review)
    print(json.dumps({"status": review["status"], "wire_sha256": review["wire_sha256"], "max_new_POSTs": 1}))
