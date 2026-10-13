"""ROOT-only matched OpenQA36: public freeze or normal saved-answer execution.

Freeze performs public serialization only. Execute uses the separate successor38
claim helper and normal readonly fixture saved configuration/credential resolution.
No scorer, references, choices, retry, model download or E write is present.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import types
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

W = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
R = W / "5703-failure-strata-checker-pair-20261008-02"
P = W / "5703-checker-schema-compact-repair-20261008-01"
FP = W / "5703-round2-old128-public-strata-preparation-20261008-01"
E = Path(r"E:\5703\learning-assistant")
SITE = W / "5703-complete-isolated-install-runtime-1994dfe8a40b/project/.venv/Lib/site-packages"
DB = "postgresql+psycopg://cs30_fixture:cs30-fixture-20261006-01-public@127.0.0.1:15433/cs30_fixture_20261006_01"
BOUND = Decimal("0.0412416")
INPUT_CONTEXT = 131072
OUTPUT_CAP = 768
CONFIG_ID = "74c8201e-aca0-400d-bcc5-5785e24c1c11"
CONFIG_HASH = "703c94a357ddd4b826d8b5fe25d503198d3d56e1e9130f6a37ed9e9c3396aa4a"
PROJECTION = FP / "candidate12-openqa-generation-public-only02.json"
PROJECTION_SHA = "b1848e0bcd9d2257047704288fa5e081bc7e70e83bf1ba9643cd26c18aa7c85c"
PRIOR = P / "public-matched-quality19-frozen-inputs01.json"
PRIOR_SHA = "a76304e5af9b4a86bb34b16f490930c3f9c0d90b22e39c69b85f09b085c76c74"
ARMS = ("E0_none", "E1_dense", "hybrid_plus_rerank")
DENIED_PARTS = {".codex", ".secrets", ".env", "eval-private", "evaluator-private", "private_runs", "week09-private-db", "sessions"}
SOURCE_FILES = (
    "generation/compact_findings_v3.py", "generation/providers.py",
    "generation/google_schema_compiler04.py", "generation/probes.py",
    "generation/types.py", "generation/capabilities.py", "generation/openrouter_routes.py",
    "backend/app/modules/model_settings/service.py", "backend/app/modules/model_settings/compatibility.py",
    "generation/adapters.py", "generation/network_policy.py", "generation/provider_diagnostics.py", "generation/parser.py",
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def public_path(path, root=W):
    path = Path(path)
    if not path.is_absolute() or not path.resolve().is_relative_to(root.resolve()) or any(part.casefold() in DENIED_PARTS for part in path.parts):
        raise ValueError("Exact authorized public workspace path required")
    return path


def read_pin(pin, root=W):
    path = public_path(pin["path"], root)
    raw = path.read_bytes()
    if len(raw) > 8_388_608 or len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise ValueError("Public input pin changed")
    return json.loads(raw)


def make_pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def focused(pins):
    if not pins or len(pins) > 30:
        raise ValueError("Focused source pins required")
    for pin in pins:
        path = Path(pin["path"])
        if not path.is_absolute() or not path.resolve().is_relative_to(E.resolve()) or any(part.casefold() in DENIED_PARTS for part in path.parts):
            raise ValueError("Exact public E source pin required")
        raw = path.read_bytes()
        if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
            raise ValueError("Focused source changed")


def public_imports(with_dependencies=False):
    # generation.__init__ imports its ordinary service and pydantic transitively.
    # Explicit W dependencies are required even for public payload serialization;
    # -S still prevents implicit site/.pth startup.
    roots = [str(E), str(E / "backend"), str(SITE)]
    sys.path[:] = roots + [r"D:\Python\python313.zip", r"D:\Python\DLLs", r"D:\Python\Lib"]


def prior_and_questions():
    prior = read_pin({"path": str(PRIOR), "bytes": 130892, "sha256": PRIOR_SHA})
    projection = read_pin({"path": str(PROJECTION), "bytes": 2535, "sha256": PROJECTION_SHA})
    questions = projection["questions"]
    if projection.get("protocol") != "openqa" or len(questions) != 12 or len({q["question_id"] for q in questions}) != 12 or any(set(q) != {"question_id", "question_text"} for q in questions):
        raise ValueError("Exact twelve public OpenQA stems required")
    if any(not isinstance(q["question_text"], str) or not q["question_text"].strip() for q in questions):
        raise ValueError("Exact nonempty question stems required")
    originals = [plan for plan in prior["plans"] if plan["protocol"] == "openqa"]
    systems = {plan["messages"][0]["content"] for plan in originals}
    if len(systems) != 1 or prior["model_config"]["max_tokens"] != OUTPUT_CAP or prior["model_config"]["configuration_id"] != "model-settings:" + CONFIG_ID:
        raise ValueError("Prior matched OpenQA identity changed")
    return prior, questions, systems.pop()


def evidence_projection(rows):
    if type(rows) is not list or len(rows) != 5:
        raise ValueError("Every retrieval arm requires all five frozen passages")
    result = []
    for row in rows:
        if type(row) is not dict or not all(key in row for key in ("chunk_id", "source_title", "locator", "text", "text_hash")):
            raise ValueError("Frozen normal public evidence fields missing")
        if not isinstance(row["text"], str) or not row["text"].strip() or sha(row["text"].encode("utf-8")) != row["text_hash"]:
            raise ValueError("Exact full public evidence text/hash required")
        result.append({key: row[key] for key in ("chunk_id", "source_title", "locator", "text")})
    if len({row["chunk_id"] for row in result}) != 5:
        raise ValueError("Duplicate frozen top-five chunk")
    return result


def validate_pool(pool, pool_pin, receipt_pin, questions):
    ids = {question["question_id"] for question in questions}
    receipt = read_pin(receipt_pin, R)
    if pool.get("status") != "ACTUAL_READONLY_PUBLIC12_LOCAL_RETRIEVAL_COMPLETE" or set(pool.get("questions", {})) != ids or pool.get("questions_projection_sha256") != PROJECTION_SHA:
        raise ValueError("Exact complete twelve-question native retrieval pool required")
    if any(pool.get(field) != 0 for field in ("provider_calls", "DB_mutations", "E_writes")) or pool.get("Gold_read") is not False:
        raise ValueError("Pool must attest readonly public evidence with zero provider calls")
    if receipt.get("status") != "ACTUAL_PUBLIC12_READONLY_LOCAL_RETRIEVAL_PASS" or receipt.get("pool_pin") != pool_pin or receipt.get("question_count") != 12 or set(receipt.get("completed_questions", [])) != ids or len(receipt.get("completed_questions", [])) != 12 or receipt.get("input_pin", {}).get("sha256") != PROJECTION_SHA:
        raise ValueError("Actual terminal retrieval receipt and pool pin must match")
    if any(receipt.get(field) != 0 for field in ("provider_calls", "DB_mutations", "credentials_read", "Gold_reads", "E_writes", "process_exit_code")) or receipt.get("source_inputs_unchanged") is not True or receipt.get("resource_close_errors") != []:
        raise ValueError("Closed successful readonly retrieval receipt required")


def freeze(pool_path, pool_sha, receipt_path, receipt_sha, output):
    output = public_path(output, R)
    if output.exists():
        raise ValueError("Fresh frozen output required")
    prior, questions, system = prior_and_questions()
    pool_pin = make_pin(public_path(pool_path, R))
    if pool_pin["sha256"] != pool_sha:
        raise ValueError("Actual retrieval pool SHA changed")
    pool = read_pin(pool_pin, R)
    receipt_pin = make_pin(public_path(receipt_path, R))
    if receipt_pin["sha256"] != receipt_sha:
        raise ValueError("Actual retrieval receipt SHA changed")
    validate_pool(pool, pool_pin, receipt_pin, questions)
    source_pins = [make_pin(E / relative) for relative in SOURCE_FILES]
    focused(source_pins)
    os.environ.clear()
    os.environ.update(SystemRoot=r"C:\Windows", WINDIR=r"C:\Windows", PATH=r"D:\Python;C:\Windows\System32", APP_ENV="test", MODEL_MODE="mock", LLM_PROVIDER="mock", MODEL_CONFIG_KEY_FILE=str(R / "PURE_FREEZE_UNUSED_NO_KEY_FILE"), TEMP=str(R), TMP=str(R), PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TORCH_DEVICE_BACKEND_AUTOLOAD="0")
    os.chdir(R)
    public_imports()
    from generation.types import ModelConfig
    from generation.providers import payload
    config = ModelConfig.from_dict(prior["model_config"])
    schema = prior["schemas"]["openqa"]
    plans = []
    for index, question in enumerate(questions):
        qid = question["question_id"]
        saved = pool["questions"][qid]
        if saved.get("question_id", qid) != qid or saved.get("question_text") != question["question_text"]:
            raise ValueError("Pool question stem changed")
        evidence = {"E0_none": [], "E1_dense": evidence_projection(saved["dense_top5"]), "hybrid_plus_rerank": evidence_projection(saved["hybrid_rerank_top5"])}
        order = ARMS[index % 3:] + ARMS[:index % 3]
        for arm in order:
            messages = [{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"QUESTION": question["question_text"], "CURRENT_EVIDENCE": evidence[arm]}, ensure_ascii=False, separators=(",", ":"))}]
            wire = encoded(payload(config, messages, schema, "matched_openqa_v1"))
            allowance = len(wire) + 512
            if allowance + OUTPUT_CAP > INPUT_CONTEXT:
                raise ValueError("Full untruncated evidence exceeds frozen context protection")
            plans.append({"slot": len(plans) + 1, "protocol": "openqa", "question_id": qid, "arm": arm, "messages": messages, "source_chunk_ids": [row["chunk_id"] for row in evidence[arm]], "wire_sha256": sha(wire), "wire_bytes": len(wire), "estimated_input_allowance": allowance, "financial_input_context_limit": INPUT_CONTEXT})
    focused(source_pins)
    result = {"status": "PUBLIC_MATCHED_OPENQA36_FROZEN_NO_CREDENTIALS", "planned_count": 36, "question_count": 12, "conditions": list(ARMS), "protocol": "openqa", "model_config": prior["model_config"], "schemas": {"openqa": schema}, "plans": plans, "projection_pin": make_pin(PROJECTION), "pool_pin": pool_pin, "pool_receipt_pin": receipt_pin, "prior_inputs_pin": make_pin(PRIOR), "source_pins": source_pins, "history": [], "use_profile": False, "choices_included": False, "model_messages_contain_only_stem_and_public_evidence": True, "Gold_reads": 0, "provider_calls": 0, "credential_reads": 0, "DB_calls": 0, "retrieval_execution_by_freeze": False, "same_prior_openqa_policy_schema_model_except_stems_evidence": True, "created_at_UTC": now()}
    save(output, result)
    print(json.dumps({"status": result["status"], "frozen_inputs_pin": make_pin(output), "planned_count": 36}), flush=True)
    return 0


def validate_inputs(inputs, config, provider_payload):
    prior, questions, system = prior_and_questions()
    if inputs.get("status") != "PUBLIC_MATCHED_OPENQA36_FROZEN_NO_CREDENTIALS" or inputs["model_config"] != prior["model_config"] or config.to_dict() != prior["model_config"] or inputs["schemas"] != {"openqa": prior["schemas"]["openqa"]}:
        raise ValueError("Same prior model/schema required")
    pool = read_pin(inputs["pool_pin"], R)
    validate_pool(pool, inputs["pool_pin"], inputs["pool_receipt_pin"], questions)
    if inputs["projection_pin"] != make_pin(PROJECTION) or inputs["prior_inputs_pin"] != make_pin(PRIOR) or len(inputs["plans"]) != 36:
        raise ValueError("Frozen public source identity changed")
    slot = 0
    for index, question in enumerate(questions):
        saved = pool["questions"][question["question_id"]]
        if saved.get("question_text") != question["question_text"]:
            raise ValueError("Pool stem identity changed")
        sources = {"E0_none": [], "E1_dense": evidence_projection(saved["dense_top5"]), "hybrid_plus_rerank": evidence_projection(saved["hybrid_rerank_top5"])}
        for arm in ARMS[index % 3:] + ARMS[:index % 3]:
            plan = inputs["plans"][slot]
            expected_messages = [{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"QUESTION": question["question_text"], "CURRENT_EVIDENCE": sources[arm]}, ensure_ascii=False, separators=(",", ":"))}]
            slot += 1
            if plan["slot"] != slot or plan["protocol"] != "openqa" or plan["question_id"] != question["question_id"] or plan["arm"] != arm or plan["messages"] != expected_messages or plan["source_chunk_ids"] != [row["chunk_id"] for row in sources[arm]]:
                raise ValueError("Exact public balanced slot changed")
            wire = encoded(provider_payload(config, plan["messages"], inputs["schemas"]["openqa"], "matched_openqa_v1"))
            if sha(wire) != plan["wire_sha256"] or len(wire) != plan["wire_bytes"] or plan["estimated_input_allowance"] != len(wire) + 512 or len(wire) + 512 + OUTPUT_CAP > INPUT_CONTEXT:
                raise ValueError("All frozen normal provider wires must match before credentials")


class PhysicalGuard:
    def __init__(self, output, source_pins):
        self.output, self.source_pins = output, source_pins
        self.plan, self.count = None, 0
        sys.addaudithook(self.audit)

    def audit(self, event, args):
        if event != "urllib.Request":
            return
        url, raw, _headers, method = args
        if self.plan is None or self.count or url != "https://openrouter.ai/api/v1/chat/completions" or method != "POST":
            raise PermissionError("Unclaimed or repeated model POST")
        focused(self.source_pins)
        data = json.loads(raw)
        if sha(raw) != self.plan["wire_sha256"] or len(raw) != self.plan["wire_bytes"] or data.get("max_tokens") != OUTPUT_CAP or data.get("response_format") != {"type": "json_object"} or data.get("reasoning") != {"effort": "low"} or data.get("provider") != {"order": ["google-vertex/global"], "only": ["google-vertex/global"], "allow_fallbacks": False, "require_parameters": True, "max_price": {"prompt": 0.3, "completion": 2.5}}:
            raise PermissionError("Frozen wire, route or cap changed")
        self.count = 1
        save(self.output / f"slot-{self.plan['slot']:02d}-wire-observed01.json", {"slot": self.plan["slot"], "at_UTC": now(), "physical_POST_observed_before_transport": True, "wire_sha256": sha(raw), "wire_bytes": len(raw), "header_or_payload_exported": False})


def validate_response(value):
    if type(value) is not dict or set(value) != {"response_type", "short_answer"} or value["response_type"] not in {"answer", "refusal"}:
        raise ValueError("OpenQA output shape invalid")
    if value["response_type"] == "refusal" and value["short_answer"] is not None:
        raise ValueError("Refusal short answer invalid")
    if value["response_type"] == "answer" and (type(value["short_answer"]) is not str or not value["short_answer"].strip()):
        raise ValueError("Standalone short answer missing")


def execute(release_path, release_sha):
    release_pin = make_pin(public_path(release_path, R))
    if release_pin["sha256"] != release_sha:
        raise ValueError("ROOT release pin changed")
    release = read_pin(release_pin, R)
    if release.get("schema") != "5703_successor38_group_release_v1" or release.get("status") != "ROOT_FROZEN_SUCCESSOR38_RELEASE" or release.get("group") != "quality_openqa" or release["executable_pin"] != make_pin(Path(__file__)) or release.get("answer_configuration_id") != CONFIG_ID or release.get("answer_config_hash") != CONFIG_HASH:
        raise ValueError("Exact ROOT quality_openqa release required")
    nonce = release["execution_nonce"]
    if not re.fullmatch(r"[a-z0-9_-]{12,64}", nonce):
        raise ValueError("Fresh ROOT nonce required")
    inputs = read_pin(release["inputs_pin"], R)
    read_pin(release["budget_pin"], R)
    helper_path = public_path(release["helper_pin"]["path"], R)
    helper_raw = helper_path.read_bytes()
    if len(helper_raw) != release["helper_pin"]["bytes"] or sha(helper_raw) != release["helper_pin"]["sha256"]:
        raise ValueError("Exact shared successor38 helper required")
    focused(inputs["source_pins"])
    public_imports()
    from generation.types import ModelConfig
    from generation.providers import payload
    frozen_config = ModelConfig.from_dict(inputs["model_config"])
    validate_inputs(inputs, frozen_config, payload)
    output = R / ("actual-public-openqa36-" + nonce)
    if output.exists():
        raise ValueError("Fresh execution only; never replay a previous attempt")
    output.mkdir()
    blank, cache = output / "blank", output / "cache"
    blank.mkdir()
    cache.mkdir()
    report = {"status": "STARTED_NOT_ACCEPTANCE", "planned_count": 36, "question_count": 12, "protocol": "openqa", "rows": [{key: plan[key] for key in ("slot", "protocol", "question_id", "arm", "source_chunk_ids", "wire_sha256", "wire_bytes")} | {"status": "not_started"} for plan in inputs["plans"]], "known_cost_USD": "0", "unknown_holds_USD": "0", "physical_calls": 0, "Gold_reads": 0, "DB_mutations": 0, "activation_posts": 0, "retries": 0, "adapter_only_not_native_full_HTTP": True, "inputs_pin": release["inputs_pin"], "release_pin": release_pin, "scoring_performed": False, "started_at_UTC": now()}
    save(output / "scheduled-slots01.json", report)
    engine = settings = adapter = secret = budget_guard = physical = None
    budget_stop_recorded = False
    known, unknown, code = Decimal(0), Decimal(0), 1
    key = None
    try:
        # Validate the shared immutable release before normal credential work.
        helper = types.ModuleType("successor38_claim_guard")
        helper.__file__ = str(helper_path)
        sys.modules[helper.__name__] = helper
        exec(compile(helper_raw, str(helper_path), "exec"), helper.__dict__)
        budget_guard = helper.Guard(Path(release["budget_pin"]["path"]), release["budget_pin"]["sha256"], Path(release_path), release_sha)
        # No memory credential is touched until all 36 normal wires passed above.
        key = os.environ.pop("MODEL_CONFIG_ENCRYPTION_KEY", None)
        if not key or not re.fullmatch(r"[A-Za-z0-9_-]{43}=", key):
            raise ValueError("ROOT memory fixture encryption key required")
        os.environ.clear()
        os.environ.update(SystemRoot=r"C:\Windows", WINDIR=r"C:\Windows", PATH=r"D:\Python;C:\Windows\System32", APP_ENV="test", DATABASE_URL=DB, MODEL_MODE="mock", LLM_PROVIDER="mock", MODEL_CONFIG_ENCRYPTION_KEY=key, MODEL_CONFIG_KEY_FILE=str(output / "UNUSED_NO_KEY_FILE"), TEMP=str(cache), TMP=str(cache), PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TORCH_DEVICE_BACKEND_AUTOLOAD="0")
        key = None
        os.chdir(blank)
        public_imports(with_dependencies=True)
        from app.core.config import Settings
        from app.db import models as registered_models
        from app.db.session import init_engine
        from app.modules.model_settings import service
        from generation.adapters import LLMAdapter
        from generation.parser import strict_json
        from sqlalchemy.orm import Session
        settings = Settings(_env_file=None)
        engine = init_engine(DB)
        with Session(engine) as db:
            db.connection().exec_driver_sql("SET TRANSACTION READ ONLY")
            if db.connection().exec_driver_sql("SHOW transaction_read_only").scalar_one() != "on":
                raise ValueError("Readonly fixture transaction required")
            saved = db.get(service.ModelConfiguration, CONFIG_ID)
            if saved is None or saved.config_hash != CONFIG_HASH:
                raise ValueError("Exact saved normal answer configuration required")
            config = replace(service.as_model_config(saved), max_tokens=OUTPUT_CAP, structured_output_mode="json_object")
            validate_inputs(inputs, config, payload)
            focused(inputs["source_pins"])
            secret = service.resolve_secret(db, settings, config.configuration_id)
        if not secret:
            raise ValueError("Normal saved fixture credential unavailable")
        adapter = LLMAdapter(config, api_key=secret)
        secret = None
        physical = PhysicalGuard(output, inputs["source_pins"])
        save(output / "frozen-inputs-binding01.json", {"inputs_pin": release["inputs_pin"], "pool_pin": inputs["pool_pin"], "all_36_wire_matches_before_memory_key": True, "all_36_wire_matches_again_before_resolve_secret": True, "same_prior_openqa_policy_schema_model_except_stems_evidence": True, "Gold_reads": 0})
        for plan in inputs["plans"]:
            focused(inputs["source_pins"])
            start = budget_guard.claim("quality_openqa", plan["slot"], nonce, wire_sha256=plan["wire_sha256"], wire_bytes=plan["wire_bytes"], output_cap=OUTPUT_CAP, input_tokens_bound=plan["estimated_input_allowance"])
            unknown += BOUND
            report["unknown_holds_USD"] = str(unknown)
            report["rows"][plan["slot"] - 1]["status"] = "started_may_be_submitted"
            save(output / f"slot-{plan['slot']:02d}-started01.json", start)
            physical.plan, physical.count = plan, 0
            began = time.perf_counter()
            result = adapter.generate(plan["messages"], response_schema=inputs["schemas"]["openqa"], response_schema_name="matched_openqa_v1", timeout_seconds=config.timeout_seconds)
            physical.plan = None
            duration = (time.perf_counter() - began) * 1000
            usage = result.usage or {}
            cost = usage.get("cost")
            actual = None
            if cost is not None:
                try:
                    parsed = Decimal(str(cost))
                    if parsed.is_finite() and parsed >= 0:
                        actual = parsed
                except Exception:
                    pass
            raw = result.raw_text if type(result.raw_text) is str else ""
            public_raw = None if adapter._api_key and adapter._api_key in raw else raw
            safe_usage = {name: usage.get(name) if type(usage.get(name)) is int and usage[name] >= 0 else None for name in ("input_tokens", "output_tokens", "total_tokens")}
            safe_usage["cost"] = None if actual is None else str(actual)
            record = {key: plan[key] for key in ("slot", "protocol", "question_id", "arm", "source_chunk_ids", "wire_sha256", "wire_bytes")}
            record.update(observed_duration_ms=duration, request_submitted=result.request_submitted, physical_POSTs=physical.count, usage=safe_usage, finish_reason=result.finish_reason, raw_text=public_raw, raw_text_sha256=None if public_raw is None else sha(raw.encode("utf-8")), http_status=result.diagnostic.get("http_status"), status="failed", diagnostic_code=(result.error or {}).get("code"), financial_input_context_limit=INPUT_CONTEXT)
            if not result.error and public_raw is not None:
                try:
                    value = strict_json(public_raw)
                    validate_response(value)
                    if result.finish_reason != "stop":
                        raise ValueError("Non-stop finish is invalid")
                    record.update(status="completed", response=value)
                except (ValueError, TypeError, KeyError):
                    record["status"] = "invalid_response"
            stop_reason = None
            if public_raw is None:
                stop_reason = "STOP_CREDENTIAL_BEARING_RESPONSE"
            elif physical.count != 1 or not result.request_submitted or result.error:
                stop_reason = "STOP_TRANSPORT_FAILURE_OR_UNCERTAINTY"
            elif actual is None:
                stop_reason = "STOP_UNKNOWN_COST"
            elif actual > BOUND:
                stop_reason = "STOP_COST_BOUND_EXCEEDED"
            elif type(usage.get("input_tokens")) is not int or type(usage.get("output_tokens")) is not int or usage["input_tokens"] < 0 or usage["output_tokens"] < 0:
                stop_reason = "STOP_UNKNOWN_TOKEN_USAGE"
            elif usage["input_tokens"] > plan["estimated_input_allowance"] or usage["output_tokens"] > OUTPUT_CAP:
                stop_reason = "STOP_TOKEN_BOUND_EXCEEDED"
            if actual is not None:
                known += actual
                unknown -= BOUND
            report["rows"][plan["slot"] - 1] = record
            report["physical_calls"] += physical.count
            report["known_cost_USD"], report["unknown_holds_USD"] = str(known), str(unknown)
            save(output / f"slot-{plan['slot']:02d}-finished01.json", record)
            budget_guard.finish(start, known_cost_USD=None if actual is None else str(actual), outcome=stop_reason or record["status"], usage=record["usage"])
            budget_stop_recorded = stop_reason is not None or actual is None
            print(json.dumps({"slot": plan["slot"], "status": record["status"], "physical_POSTs": physical.count, "known_cost_USD": str(known), "unknown_holds_USD": str(unknown)}), flush=True)
            if stop_reason:
                raise ValueError(stop_reason)
        report["status"], code = "ACTUAL_PUBLIC_MATCHED_OPENQA36_TERMINAL", 0
    except BaseException as exc:
        report["status"] = "ACTUAL_PUBLIC_MATCHED_OPENQA36_STOPPED"
        report["exception_type"] = type(exc).__name__
        if budget_guard is not None and not budget_stop_recorded:
            try:
                budget_guard.stop("STOP_RUNNER_EXCEPTION_NO_AUTORETRY")
            except BaseException:
                report["budget_stop_record_error"] = True
    finally:
        if physical is not None:
            physical.plan = None
        report["physical_calls"] = len(list(output.glob("slot-*-wire-observed01.json")))
        if adapter is not None:
            adapter._api_key = None
        secret = None
        key = None
        if settings is not None:
            settings.model_config_encryption_key = None
        os.environ.pop("MODEL_CONFIG_ENCRYPTION_KEY", None)
        if engine is not None:
            engine.dispose()
        report.update(engine_disposed=engine is not None, memory_key_references_cleared=True, finished_at_UTC=now(), exit_code=code, unstarted_count=sum(row["status"] == "not_started" for row in report["rows"]))
        save(output / "terminal-receipt01.json", report)
        print(json.dumps({"status": report["status"], "receipt": str(output / "terminal-receipt01.json"), "exit_code": code}), flush=True)
    return code


def main():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument("--pool", type=Path)
    parser.add_argument("--pool-sha256")
    parser.add_argument("--pool-receipt", type=Path)
    parser.add_argument("--pool-receipt-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--release-sha256")
    args = parser.parse_args()
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise SystemExit("Explicit ROOT -I -B -S required")
    if args.freeze:
        if not all((args.pool, args.pool_sha256, args.pool_receipt, args.pool_receipt_sha256, args.output)) or args.release:
            raise ValueError("Free freeze needs actual public pool and terminal receipt, their SHAs and fresh output only")
        return freeze(args.pool, args.pool_sha256, args.pool_receipt, args.pool_receipt_sha256, args.output)
    if not all((args.release, args.release_sha256)) or args.pool or args.pool_receipt or args.output:
        raise ValueError("Paid execution needs exact ROOT release only")
    return execute(args.release, args.release_sha256)


if __name__ == "__main__":
    raise SystemExit(main())
