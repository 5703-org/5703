"""Prepare / one explicitly reviewed capacity observation; never automatic retry."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, replace
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
BASE = W / "5703-selection58-candidate/selection58.py"
BASE_SHA = "b5aabe0cabfc730826c9e13e76032c6ec0b1706da1c296f5fc38c80c402164a0"
PRIOR = W / "5703-selection58-candidate/actual58/result58.json"
PRIOR_SHA = "889a99609fa9d9a1fccf67711eeecb939047b44847ca756a7425050bfff02476"
OLD_WIRE = W / "5703-selection58-candidate/wire58-PREPARED-UNVERIFIED.json"
OLD_WIRE_SHA = "53a0c9f1e922496fd3f662e103db0f5a2f91885ef43398586febe2989126a586"
PER = Decimal("0.075")
PRIOR_KNOWN = Decimal("0.13923046")
CAP = Decimal("0.36")
_BASE = None


def require(ok, code):
    if not ok:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, digest):
    raw = path.read_bytes()
    require(sha(raw) == digest, "PIN_CHANGED:" + path.name)
    return raw


def save(path, value):
    require(path.resolve().is_relative_to(HERE) and not path.is_symlink(), "OWNED_NEW_OUTPUT_REQUIRED")
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def base_module():
    global _BASE
    pinned(BASE, BASE_SHA)
    if _BASE is None:
        spec = importlib.util.spec_from_file_location("capacity59_public_base58", BASE)
        _BASE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_BASE)
    return _BASE


def prepare():
    base = base_module()
    body58, wire58, review58, cfg58, data, legacy = base.prepare()  # Pure, no auth/DB/network.
    require(wire58 == pinned(OLD_WIRE, OLD_WIRE_SHA), "ACTUAL58_WIRE_REQUIRED")
    prior = json.loads(pinned(PRIOR, PRIOR_SHA))
    require(prior["status"] == "OBSERVATION_RETAINED" and prior["post_attempts"] == 1
            and prior["fully_settled"] is True and Decimal(prior["known_cost_USD"]) == Decimal("0.0285088")
            and Decimal(prior["UNKNOWN_hold_USD"]) == 0 and prior["grant_aggregate_slots"] == 6
            and Decimal(prior["grant_aggregate_known_USD"]) == PRIOR_KNOWN,
            "SAME_GRANT_SIX_SETTLED_REQUIRED")
    require(6 + 1 <= 8 and PRIOR_KNOWN + PER <= CAP, "AGGREGATE_CAPACITY_BUDGET_REQUIRED")
    require(body58["max_tokens"] == 8192 and cfg58.window_tokens == 131072, "ORIGINAL58_CAPACITY_REQUIRED")
    body = deepcopy(body58)
    body["max_tokens"] = 16384
    cfg = replace(cfg58, max_tokens=16384)
    cfg.validate()
    from generation.capabilities import validate as validate_capabilities
    from generation.openrouter_routes import resolve, prepare_schema_wire
    from generation.providers import endpoint, payload
    validate_capabilities(cfg, basic=False)
    route = resolve(cfg)
    require(route.profile_id == "gemini35_google_vertex_high_research_v1"
            and route.reasoning_effort == "high", "UNCHANGED_EXISTING_HIGH_ROUTE_REQUIRED")
    schema = body["response_format"]["json_schema"]["schema"]
    actual, transport = prepare_schema_wire(cfg, payload(cfg, body["messages"], schema, base.SCHEMA), schema)
    require(actual == body and transport == {} and endpoint(cfg) == base.URL, "EXACT_REAL_CAPACITY_PAYLOAD_REQUIRED")
    restored = deepcopy(body)
    restored["max_tokens"] = 8192
    require(restored == body58 and cfg.reasoning_effort is None and cfg.thinking_enabled is None,
            "MAX_TOKENS_IS_SOLE_CHANGE_REQUIRED")
    wire = json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    require(len(wire) == 88704 and len(wire) == len(wire58) + 1, "EXACT_CAPACITY_WIRE_SIZE_REQUIRED")
    bound = (Decimal(len(wire) + 4096) * Decimal("0.3") + Decimal(16384) * Decimal("2.5")) / Decimal(1000000)
    require(bound == Decimal("0.0688") and bound <= PER, "COMPLETE_CAPACITY_PRICE_HOLD_REQUIRED")
    review = dict(status="PREPARED_NOT_EXECUTED", direct_user_quote=base.AUTH,
                  same_existing_grant=True, prior_slots=6, prior_known_USD=str(PRIOR_KNOWN), prior_new_UNKNOWN_USD="0",
                  remaining_slots_before=2, remaining_USD_before="0.22076954", grant_cap_USD=str(CAP),
                  max_new_POSTs=1, complete_single_request_hold_USD=str(PER), conservative_price_bound_USD=str(bound),
                  maximum_aggregate_reserved_USD=str(PRIOR_KNOWN + PER), maximum_aggregate_slots=7,
                  wire_bytes=len(wire), wire_sha256=sha(wire), recipient=base.URL,
                  base_code_sha256=BASE_SHA, prior58_result_sha256=PRIOR_SHA, original58_wire_sha256=OLD_WIRE_SHA,
                  original58_public_input_pins=review58["input_pins"], controller_sha256=sha(Path(__file__).read_bytes()),
                  only_outbound_change="max_tokens: 8192 -> 16384",
                  system_DATA_schema_correction_route_high_timeout_unchanged=True,
                  source_fragments=71, claims=10, syntactic_units=19, automatic_retries=0,
                  prior_truncation_preserved=True, historical_grants_UNKNOWN_and_ledgers_unmodified=True,
                  free_prepare_auth_DB_network_operations=0, native_publication=False,
                  source_entailment_certified=False, semantic_acceptance="PENDING_INDEPENDENT_REVIEW",
                  scientific_scope="Single capacity completeness observation; honest negatives remain valid; no Gold, causal quality, p95, native/RAG or production-profile adoption")
    return body, wire, review, cfg, data, legacy, base


def execute(review_sha):
    # Root must obtain approval of this concrete action; this flag cannot waive a refusal.
    body, wire, review, cfg, data, legacy, base = prepare()
    require(sha((HERE / "review59.json").read_bytes()) == review_sha
            and json.loads((HERE / "review59.json").read_bytes()) == review
            and (HERE / "wire59-PREPARED-UNVERIFIED.json").read_bytes() == wire, "FROZEN_ROOT_REVIEW_REQUIRED")
    out = HERE / "actual59"
    out.mkdir()  # Exclusive child; no repeat, substitute route or last-slot consumption.
    report = dict(status="STARTED_NOT_POSTED", post_attempts=0, known_cost_USD="0", UNKNOWN_hold_USD="0",
                  prior_slots=6, prior_known_USD=str(PRIOR_KNOWN), max_new_POSTs=1, automatic_retries=0,
                  old_ledgers_written=False, credentials_exported=False, native_publication=False,
                  source_entailment_certified=False, raw_receipt_pins=[], quality_acceptance="PENDING_INDEPENDENT_REVIEW",
                  started_UTC=datetime.now(timezone.utc).isoformat())
    save(out / "intent.json", {**report, "review_sha256": review_sha, "wire_sha256": sha(wire)})
    adapter = key = redactor = original_open = None
    try:
        for p in (base.MAIN, base.MAIN / "backend"):
            if str(p) not in sys.path:
                sys.path.append(str(p))
        helper = legacy.load_source("capacity59_original_approved_credential", legacy.PINS["credential_helper"])
        require(helper.TARGET_DB == "cs30_week10_pair_b_20261009_01", "SOLE_ISOLATED_CREDENTIAL_DB_REQUIRED")
        key = helper.approved_credential(helper.WORKSPACE_ID)  # Existing consumer only, key stays in memory.
        require(isinstance(key, str) and bool(key), "ORIGINAL_CREDENTIAL_UNAVAILABLE")
        diagnostics = legacy.load_source("capacity59_original_diagnostics", legacy.PINS["diagnostics"])
        redactor = diagnostics.Redactor((key,))
        from generation.adapters import LLMAdapter
        from generation import adapters as module
        adapter = LLMAdapter(cfg, api_key=key, retain_invalid_output=True)
        key = None
        original_open = module.open_provider

        def single_post(envelope, timeout):
            require(report["post_attempts"] == 0 and envelope.full_url == base.URL
                    and envelope.get_method() == "POST" and envelope.data == wire, "ONE_EXACT_POST_REQUIRED")
            fresh = prepare()
            require(fresh[1] == wire and fresh[2] == review, "FROZEN_INPUT_AND_TOTAL_GRANT_REQUIRED")
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
                                  response_schema_name=base.SCHEMA,
                                  request_context={"purpose": "joint_check", "request_id": "capacity59_1"}, timeout_seconds=60)
        report["complete_adapter_return_ms"] = (time.perf_counter_ns() - start) / 1e6
        report["provider_result"] = asdict(result)
        report["provider_reports_request_submitted"] = result.request_submitted
        value = result.usage.get("cost") if isinstance(result.usage, dict) else None
        cost = Decimal(str(value)) if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
        uncertain = bool(result.error and (result.error.get("code") == "PROVIDER_ROUTE_MODEL_MISMATCH"
                         or result.error.get("details", {}).get("uncertain")))
        settled = report["post_attempts"] == 1 and cost is not None and not uncertain
        report.update(observed_reported_cost_USD=str(cost) if cost is not None else None, fully_settled=settled)
        if settled:
            report.update(known_cost_USD=str(cost), UNKNOWN_hold_USD="0",
                          status="OBSERVATION_RETAINED" if cost <= PER else "STOPPED_PRICE_OVERRUN")
        else:
            if report["post_attempts"]:
                report["UNKNOWN_hold_USD"] = str(max(PER, cost if cost is not None else PER))
            report["status"] = "STOPPED_UNKNOWN" if report["post_attempts"] else "STOPPED_BEFORE_POST"
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
        report["error_types_codes"] = chain
    finally:
        key = None
        if adapter is not None:
            adapter._api_key = None
        if original_open is not None:
            module.open_provider = original_open
        total_known = PRIOR_KNOWN + Decimal(report["known_cost_USD"])
        report.update(closed_UTC=datetime.now(timezone.utc).isoformat(), grant_aggregate_slots=6 + report["post_attempts"],
                      grant_aggregate_known_USD=str(total_known), grant_aggregate_new_UNKNOWN_USD=report["UNKNOWN_hold_USD"],
                      remaining_slots=2 - report["post_attempts"],
                      remaining_USD=str(CAP - total_known - Decimal(report["UNKNOWN_hold_USD"])))
        save(out / "result59.json", redactor.value(report) if redactor else report)
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
    _, wire, review, *_ = prepare()
    require((HERE / "wire59-PREPARED-UNVERIFIED.json").read_bytes() == wire, "EXACT_PREPARED_WIRE_REQUIRED")
    save(HERE / "review59.json", review)
    print(json.dumps({"status": review["status"], "wire_sha256": review["wire_sha256"], "max_new_POSTs": 1}))
