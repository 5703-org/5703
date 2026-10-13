"""One bounded selection-repair work unit; reuse existing adapter and strict gates."""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import ipaddress
import json
import math
import msvcrt
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
W = HERE.parent
MAIN = Path(r"E:\5703\learning-assistant")
LEGACY = W / "5703-unit-proof-high50-replay-candidate/run_checker_compatible43_CANDIDATE.py"
LEGACY_SHA = "805d042d61f265d305bda0d29ae7114a7d58f3fc6ac72f32d855c701f0d624ac"
WIRE = W / "5703-unit-proof-high50-replay-candidate/UNIT_PROOF_HIGH50_EXACT_WIRE.json"
WIRE_SHA = "12814f5a901648b8d05def4739bfdce19ecf55c562b673d0606fe0c4fd366115"
PLAN = W / "5703-unit-proof-plan49-candidate/UNIT_PROOF_PLAN49_EXACT.txt"
PLAN_SHA = "082b4adcac9ed9b75edaf32b96869aea871f97a73ba0cf964926d5b430fd23ad"
CHECKED_SHA = "567c6809fa4edd1afb5faf1584f86965291d825499985db4ed9d8de21c0c1b5b"
URL = "https://openrouter.ai/api/v1/chat/completions"
GROUP_CAP = Decimal("0.36")
PER = Decimal("0.055")
UNIT_CAP = Decimal("0.11")
AUTH = "允许将同一71段教材、测试问题及已有回答发送到OpenRouter Gemini/Vertex，最多再8次、总额0.36美元，用于选证修复测试"
AUDIT = """Before emitting the final record, audit each unit's selected proof against every asserted operation or classification, quantity, purpose, condition and named entity in its full contextualized claim. Explicitly select each permitted same-claim block needed to establish these parts, including a demonstrative's antecedent or an unfinished relation's semantic completion. Include every selected ID in that claim's citations under its owning evidence_id. A generic conversion does not establish its classification; an unfinished source relation does not establish its missing object. Briefly map asserted parts to their selected IDs in the existing reason (max 200 characters). If any part remains unproved, return partial/unsupported and name the gap. Citation unions, sibling units, lookup hints and reason assertions provide no implicit proof. Keep all original fields, records, conditions and publication gates. Add no output fields or quotations.
Final schema audit: copy property names verbatim, including evidence_id, without added whitespace in keys. Keep every required field. Emit complete minified JSON and preserve all string meanings."""

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def require(value, code):
    if not value:
        raise ValueError(code)

def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}

def save_new(path, value):
    require(path.resolve().is_relative_to(HERE), "OWNED_OUTPUT_REQUIRED")
    require(not path.is_symlink(), "OUTPUT_SYMLINK_FORBIDDEN")
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")

def load_legacy():
    require(sha(LEGACY.read_bytes()) == LEGACY_SHA, "UNCHANGED_REUSED_RUNNER_REQUIRED")
    spec = importlib.util.spec_from_file_location("selection54_legacy", LEGACY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def prepared():
    require(sha(WIRE.read_bytes()) == WIRE_SHA, "ORIGINAL_71_WIRE_CHANGED")
    require(sha(PLAN.read_bytes()) == PLAN_SHA, "ORIGINAL_PLAN_CHANGED")
    require(sha((MAIN / "generation/checked.py").read_bytes()) == CHECKED_SHA, "CURRENT_MAIN_CHANGED")
    old = json.loads(WIRE.read_text(encoding="utf-8"))
    new = deepcopy(old)
    suffix = PLAN.read_text(encoding="utf-8")
    system = new["messages"][0]["content"]
    require(system.count(suffix) == 1, "EXACT_SINGLE_OLD_PLAN_REQUIRED")
    position = system.index(suffix)
    final_audit = AUDIT[AUDIT.index("\nFinal schema audit:"):]
    require(system[position + len(suffix):] == final_audit, "UNCHANGED_FINAL_SCHEMA_AUDIT_REQUIRED")
    new["messages"][0]["content"] = system[:position] + "\n" + AUDIT
    require(new["messages"][1:] == old["messages"][1:], "QUESTION_ANSWER_71_DATA_CHANGED")
    require({k: v for k, v in new.items() if k != "messages"} ==
            {k: v for k, v in old.items() if k != "messages"}, "ROUTE_SCHEMA_PROFILE_CHANGED")
    raw = json.dumps(new, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    require(len(raw) <= 98304, "WIRE_CAP_EXCEEDED")
    bound = (Decimal(len(raw) + 4096) * Decimal("0.3") + Decimal(8192) * Decimal("2.5")) / Decimal(1000000)
    require(bound <= PER, "COMPLETE_WIRE_PRICE_RESERVE_EXCEEDED")
    data = json.loads(new["messages"][1]["content"])
    require(len(data["SOURCE_FRAGMENTS"]["rows"]) == 71, "71_FRAGMENTS_REQUIRED")
    require(len(data["CLAIMS"]["rows"]) == 10, "10_CLAIMS_REQUIRED")
    require(sum(len(row["units"]) for row in data["SOURCE_SYNTACTIC_UNITS"]) == 19, "19_UNITS_REQUIRED")
    # Offline witnesses are never inserted into the outbound data or instruction.
    for token in ("F058", "F059", "F011", "F019", "F020", "Calvin", "G3P"):
        require(token not in AUDIT, "CASE_SPECIFIC_AUDIT_FORBIDDEN")
    return new, raw, {"status": "PUBLIC_INPUTS_READY_NOT_EXECUTED", "created_at_UTC": now(),
        "direct_user_quote": AUTH, "new_independent_grant": True,
        "grant_max_requests": 8, "grant_max_USD": str(GROUP_CAP), "grant_used_requests": 0,
        "grant_used_USD": "0", "current_work_unit_max_requests": 2,
        "current_work_unit_reserve_USD": str(UNIT_CAP), "complete_single_request_hold_USD": str(PER),
        "conservative_wire_price_bound_USD": str(bound), "wire_bytes": len(raw), "wire_sha256": sha(raw),
        "instruction_sha256": sha(AUDIT.encode()), "original_wire": pin(WIRE),
        "reused_runner": pin(LEGACY), "implementation_pin": pin(Path(__file__)),
        "current_main_checked": pin(MAIN / "generation/checked.py"),
        "source_fragments": 71, "claims": 10, "units": 19,
        "only_outbound_delta": "Replace the old generic unit proof plan suffix with a shorter generic omission audit; all original DATA bytes, rubric, schema, model, high/8192 profile and Vertex-only route remain equal",
        "recipient": URL, "automatic_retries": 0, "credential_export": False,
        "credential_preparation": "Existing approved read-only consumer of cs30_week10_pair_b_20261009_01 on 127.0.0.1:15433; credential stays in memory",
        "old_grants_results_unknown_holds_reused_or_rewritten": False,
        "quality_acceptance": "Independent assessment of every unit's actually selected own-claim source fragments; structural PASS and model supported labels alone are insufficient",
        "browser_and_teacher_calls": 0, "production_adoption": False}

def execute(review_sha):
    body, wire, review = prepared()
    reviewed = HERE / "review54.json"
    require(sha(reviewed.read_bytes()) == review_sha, "REVIEW_CHANGED")
    frozen = json.loads(reviewed.read_text(encoding="utf-8"))
    for key in ("wire_sha256", "instruction_sha256", "original_wire", "reused_runner", "implementation_pin", "current_main_checked"):
        require(frozen[key] == review[key], "REVIEW_INPUT_CHANGED")
    out = HERE / "actual54"
    require(not out.exists(), "WRITE_ONCE_OUTPUT_REQUIRED")
    out.mkdir()
    report = {"status": "STARTED", "started_at_UTC": now(), "submission_slots": 0,
        "known_cost_USD": "0", "UNKNOWN_hold_USD": "0", "arms": [], "model_requests": 0,
        "credential_preparation_legs": 0, "automatic_retries": 0, "historical_records_changed": False}
    save_new(out / "intent.json", {**report, "review_sha256": review_sha})
    adapter = None
    key = None
    lock = None
    lock_acquired = False
    legacy = None
    redactor = None
    original_open = original_pin = None
    submitted = False
    try:
        legacy = load_legacy()
        legacy.install_public_implementation()
        legacy.load_source("root_pure_compatible_schema50", legacy.PINS["validator"])
        from generation.checker_encoding import decode
        original = decode(legacy.read_json(legacy.PINS["original_initial36"])["check_data"])
        from generation.types import ModelConfig
        from generation.adapters import LLMAdapter
        from generation import adapters as adapter_module
        from generation.providers import endpoint, payload
        from generation.openrouter_routes import prepare_schema_wire
        cfg = ModelConfig(provider="openai_compatible", model=body["model"],
            base_url="https://openrouter.ai/api/v1", window_tokens=131072, max_tokens=8192,
            temperature=None, timeout_seconds=60.0, structured_output_mode="json_schema",
            reasoning_effort=None, configuration_id="model-settings:74c8201e-aca0-400d-bcc5-5785e24c1c11",
            openrouter_route_profile="gemini35_google_vertex_high_research_v1")
        cfg.validate()
        schema = body["response_format"]["json_schema"]["schema"]
        actual, transport = prepare_schema_wire(cfg, payload(cfg, body["messages"], schema, legacy.SCHEMA_NAME), schema)
        require(actual == body and transport == {} and endpoint(cfg) == URL, "REAL_ADAPTER_WIRE_CHANGED")
        helper = legacy.load_source("selection54_original_approved_credential", legacy.PINS["credential_helper"])
        require(helper.TARGET_DB == "cs30_week10_pair_b_20261009_01", "SOLE_ISOLATED_CREDENTIAL_DB_REQUIRED")
        report["credential_preparation_legs"] = 1
        for path in (MAIN, MAIN / "backend"):
            if str(path) not in sys.path:
                sys.path.append(str(path))
        key = helper.approved_credential(helper.WORKSPACE_ID)
        require(isinstance(key, str) and key, "ORIGINAL_CREDENTIAL_UNAVAILABLE")
        diagnostics = legacy.load_source("selection54_original_diagnostics", legacy.PINS["diagnostics"])
        redactor = diagnostics.Redactor((key,))
        adapter = LLMAdapter(cfg, api_key=key, retain_invalid_output=True)
        key = None
        lock = (out / "budget.lock").open("xb+")
        lock.write(b"0"); lock.flush(); lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        lock_acquired = True
        original_open, original_pin = adapter_module.open_provider, adapter_module.pinned_address
        known = Decimal("0")
        unknown = Decimal("0")
        active = None
        stopped = False

        def pin_guard(url):
            require(active is not None and submitted and url == URL, "EXACT_ACTIVE_PROVIDER_REQUIRED")
            active["resolving"] = True
            try:
                address = original_pin(url)
            finally:
                active["resolving"] = False
            parsed = ipaddress.ip_address(address)
            require(parsed.is_global and not (isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped), "PUBLIC_PROVIDER_IP_REQUIRED")
            active["ip"] = address
            return address

        def open_guard(envelope, timeout):
            nonlocal submitted
            require(not submitted and envelope.full_url == URL and envelope.get_method() == "POST", "EXACT_SINGLE_POST_REQUIRED")
            require(envelope.data == wire, "FROZEN_ACTUAL_WIRE_REQUIRED")
            require(report["submission_slots"] < 2 and report["submission_slots"] < 8 and
                    known + unknown + PER <= UNIT_CAP and known + unknown + PER <= GROUP_CAP, "BUDGET_CLOSED")
            submitted = True
            report["submission_slots"] += 1
            save_new(out / (active["arm"] + "-submitted-UNKNOWN.json"), {"wire_sha256": sha(wire), "complete_hold_USD": str(PER), "at_UTC": now()})
            try:
                return diagnostics.wrap_provider_response(original_open(envelope, timeout=timeout),
                    path_prefix=out / (active["arm"] + "-raw-provider"), redactor=redactor,
                    on_saved=lambda receipt: active["raw_receipts"].append(receipt))
            except BaseException as exc:
                if isinstance(exc, legacy.urlerror.HTTPError):
                    diagnostics.retain_http_error_reads(exc, path_prefix=out / (active["arm"] + "-raw-provider"),
                        redactor=redactor, on_saved=lambda receipt: active["raw_receipts"].append(receipt))
                raise

        adapter_module.open_provider, adapter_module.pinned_address = open_guard, pin_guard
        def audit(event, values):
            if event in {"subprocess.Popen", "os.system", "os.exec", "os.spawn", "socket.bind", "socket.sendto"}:
                raise PermissionError("FORBIDDEN_COMPONENT_OPERATION")
            if event == "socket.getaddrinfo":
                require(active is not None and submitted and len(values) > 1 and values[1] == 443 and
                    (active["resolving"] and values[0] == "openrouter.ai" or values[0] == active["ip"]), "EXACT_PROVIDER_DNS_REQUIRED")
            if event == "socket.connect":
                address = values[1]
                require(active is not None and isinstance(address, tuple) and address[0] == active["ip"] and address[1] == 443, "PINNED_PROVIDER_CONNECT_REQUIRED")
            if event == "open" and values and not isinstance(values[0], int):
                path = Path(os.path.abspath(os.fsdecode(values[0])))
                require(not any(part.casefold() in {".codex", "week09-private-db"} for part in path.parts), "PROTECTED_READ_FORBIDDEN")
                require(path.name not in {"run_ROOT_finite_rag_imports08_PREPARED.py", "run_matched_component_generation08e.py", "native_checker_json_object_override_PREPARED01.py"}, "PREVIOUSLY_DENIED_READ_FORBIDDEN")
                flags = values[2] if len(values) > 2 else 0
                mode = values[1] if len(values) > 1 else "r"
                write = isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                write = write or isinstance(mode, str) and any(char in mode for char in "wax+")
                if write:
                    require(path.parent == out, "ONLY_ACTUAL_OUTPUT_WRITES_ALLOWED")
        sys.addaudithook(audit)
        for number in (1, 2):
            if stopped:
                report["arms"].append({"arm": number, "status": "NOT_RUN_GLOBAL_STOP"})
                continue
            prepared()  # Recheck exact immutable public inputs immediately before submission.
            active = {"arm": f"selection54_{number}", "ip": None, "resolving": False, "raw_receipts": []}
            submitted = False
            start = time.perf_counter_ns()
            result = adapter.generate(body["messages"], response_schema=schema, response_schema_name=legacy.SCHEMA_NAME,
                request_context={"purpose": "joint_check", "request_id": active["arm"]}, timeout_seconds=60)
            elapsed = (time.perf_counter_ns() - start) / 1e6
            value = result.usage.get("cost") if isinstance(result.usage, dict) else None
            cost_ok = type(value) in (int, float) and math.isfinite(value) and value >= 0
            cost = Decimal(str(value)) if cost_ok else None
            route_bad = bool(result.error and result.error.get("code") == "PROVIDER_ROUTE_MODEL_MISMATCH")
            uncertain = bool(result.error and result.error.get("details", {}).get("uncertain"))
            settled = submitted and cost is not None and cost <= PER and not route_bad and not uncertain
            if submitted:
                if settled:
                    known += cost
                else:
                    unknown += PER
                    stopped = True
            attempt_submitted = submitted
            submitted = False  # The received result is now settled or explicitly held.
            report.update(known_cost_USD=str(known), UNKNOWN_hold_USD=str(unknown))
            validation = legacy.validate_output(result.raw_text, original) if result.raw_text else {"repeat_structure_gate_PASS": False}
            row = {"arm": active["arm"], "status": "OBSERVED" if attempt_submitted else "LOCAL_STOP", "fully_settled": settled,
                "reported_cost_USD": str(cost) if cost is not None else None, "latency_ms": elapsed,
                "timing_boundary": "LLMAdapter.generate invocation to complete return", "provider_result": asdict(result),
                "validation": validation, "raw_receipt_pins": active["raw_receipts"], "independent_source_quality": "PENDING_REVIEW"}
            save_new(out / (active["arm"] + "-result.json"), redactor.value(row))
            report["arms"].append(row)
            if not settled or not validation.get("repeat_structure_gate_PASS", False) or result.error:
                stopped = True
        report["status"] = "TWO_OBSERVATIONS_CLOSED" if len(report["arms"]) == 2 and not stopped else "STOPPED_RETAINED"
    except BaseException as exc:
        if submitted:
            report["UNKNOWN_hold_USD"] = str(Decimal(report["UNKNOWN_hold_USD"]) + PER)
        chain = []
        current = exc
        while current is not None:
            chain.append({"type": type(current).__name__, "errno": getattr(current, "errno", None), "winerror": getattr(current, "winerror", None)})
            current = current.__cause__ or current.__context__
        report.update(status="STOPPED_BEFORE_POST" if report["submission_slots"] == 0 else "STOPPED_RETAINED", error_chain_types_codes=chain)
    finally:
        key = None
        if adapter is not None:
            adapter._api_key = None
        if original_open is not None:
            adapter_module.open_provider, adapter_module.pinned_address = original_open, original_pin
        if lock is not None:
            if lock_acquired:
                lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            lock.close()
        report.update(closed_at_UTC=now(), credentials_exported=False, production_adoption=False, model_requests=report["submission_slots"],
            remaining_grant_slots=8-report["submission_slots"], new_grant_cap_USD=str(GROUP_CAP),
            remaining_money_before_future_holds_USD=str(GROUP_CAP-Decimal(report["known_cost_USD"])-Decimal(report["UNKNOWN_hold_USD"])))
        save_new(out / "result54.json", redactor.value(report) if redactor else report)
    print(json.dumps({k: report[k] for k in ("status", "submission_slots", "known_cost_USD", "UNKNOWN_hold_USD")}, ensure_ascii=False))
    return 0 if report["status"] == "TWO_OBSERVATIONS_CLOSED" else 1

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--review-sha256")
    args = parser.parse_args()
    if args.execute:
        raise SystemExit(execute(args.review_sha256))
    body, wire, review = prepared()
    require(not (HERE / "actual54").exists(), "EXECUTED_REVIEW_IMMUTABLE")
    (HERE / "review54.json").write_bytes((json.dumps(review, ensure_ascii=False, indent=2) + "\n").encode())
    for path, raw in ((HERE / "wire54.json", wire), (HERE / "audit54.txt", AUDIT.encode())):
        if path.exists():
            require(path.read_text(encoding="utf-8") == AUDIT if path.name == "audit54.txt" else path.read_bytes() == raw,
                "EXISTING_PREPARED_PAYLOAD_CHANGED")
        else:
            with path.open("xb") as handle:
                handle.write(raw)
    print(json.dumps(review, ensure_ascii=False))
