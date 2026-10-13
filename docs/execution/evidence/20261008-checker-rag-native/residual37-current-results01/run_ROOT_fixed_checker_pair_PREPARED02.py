"""PREPARED: ROOT alone releases the unstarted concise original slot2 once.

No retry, generation, repair, activation, source adoption or native publication.
The preparer must never run main: ROOT supplies the existing encrypted fixture
key in its owned child's memory and releases exact budget/reservation pins.
"""

import argparse
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
import types

W = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
E = Path(r"E:\5703\learning-assistant")
R = W / "5703-failure-strata-checker-pair-20261008-02"
P = W / "5703-checker-schema-compact-repair-20261008-01"
PAIR = P / "round2-latency-pair-preparation02"
DB = "postgresql+psycopg://cs30_fixture:cs30-fixture-20261006-01-public@127.0.0.1:15433/cs30_fixture_20261006_01"
CONFIG_ID = "74c8201e-aca0-400d-bcc5-5785e24c1c11"
CONFIG_HASH = "703c94a357ddd4b826d8b5fe25d503198d3d56e1e9130f6a37ed9e9c3396aa4a"
CHECKER_PROJECT_ID = "bd1bbe8c-8b6f-4f91-a44b-56cd38886a69"
URL = "https://openrouter.ai/api/v1/chat/completions"
BOUND = Decimal("0.04956160")
FROZEN = {
    "baseline": (PAIR / "frozen-baseline-checker01.json", 44224, "8d1abfd25c7f5630f8bca50d11c4e433842d10c6af3831faeed9b506d5d63148"),
    "concise": (PAIR / "frozen-concise-checker01.json", 45575, "11faafbb217f405e2d578416b45dbcf4e837e17f988c82fbb32d3c20c2c38b78"),
}
ROUTE = {"order": ["google-vertex/global"], "only": ["google-vertex/global"], "allow_fallbacks": False, "require_parameters": True, "max_price": {"prompt": 0.3, "completion": 2.5}}
FLAGS = ("body_ok", "specific_help", "scope_ok", "suggestions_ok", "evidence_display_ok", "cumulative_ok", "complete_answer", "limitations_explicit", "attempt_evaluation_ok", "tutor_question_ok", "non_repetitive_next_action")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def ordinary(value, root=W):
    path = Path(os.path.abspath(value))
    if not path.is_relative_to(root) or any(part.casefold() in {".codex", ".agents", ".aws", ".secrets", "eval-private", "week09-private-db"} for part in path.parts):
        raise ValueError("Exact public owned root required")
    for item in (path, *path.parents):
        if item.exists() and getattr(item.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400:
            raise ValueError("Reparse control path refused")
        if item == root:
            break
    return path


def read_pin(pin, root=W, maximum_bytes=4_000_000):
    path = ordinary(pin["path"], root)
    raw = path.read_bytes()
    if len(raw) > maximum_bytes or len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise ValueError("Exact public pin changed")
    return json.loads(raw)


def cli_pin(path, expected_sha):
    path = ordinary(path)
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise ValueError("SHA-256 argument required")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": expected_sha}


def save_new(path, value):
    ordinary(path, R)
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def check_sources(release):
    manifest = read_pin(release["current_source_manifest_pin"])
    source17 = manifest["source_pins"]
    if len(source17) != 17 or manifest["status"] != "EXACT_CURRENT_PUBLIC_SOURCE17_PINS_READ_ONLY":
        raise ValueError("Exact current17 manifest required")
    validator_pins = read_pin(release["validator_replay_evidence_pin"])["source_pins"]
    if len(validator_pins) != 10:
        raise ValueError("Exact original-validator source pins required")
    result = {}
    for pin in source17 + validator_pins:
        path = ordinary(pin["path"], E)
        if path.suffix != ".py":
            raise ValueError("Only pinned public source files required")
        raw = path.read_bytes()
        if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
            raise ValueError("Frozen normal source changed")
        result[path.relative_to(E).as_posix()] = pin["sha256"]
    return result


def validate_output(raw, data):
    """Use unchanged pure product validators; never repair/replace a verdict.

    The remaining applicable surface/basis gates below follow checked.py's
    final gates. This validates returned model judgments and provenance only;
    it does not independently rejudge scientific entailment or publish.
    """
    from pydantic import ValidationError
    from generation.parser import strict_json
    from generation.checker_contract import schema_issue
    from generation.reliability_v4 import (
        normalize_judgment, checker_inconsistencies, repairable_verdict_inconsistencies,
        given_matches, validate_derivation,
    )
    from generation.reliability_v5 import ReliableCheckV5, assess_requirements

    result = {"typed_valid": False, "accepted_by_named_local_gates": False, "human_rating": None, "independent_scientific_evaluation": False}
    try:
        typed = ReliableCheckV5.model_validate(strict_json(raw)).model_dump()
    except (ValidationError, ValueError, TypeError) as exc:
        result["schema_issues"] = schema_issue(exc)
        return result
    normalized, binding_issues = normalize_judgment(typed, data["ACTUAL_CITATION_BINDINGS"])
    requirement_contract, requirement_defects, summary = assess_requirements(
        typed, data["CONTEXT_COVERAGE"], data["SOURCE_FRAGMENTS"],
        answer_mode=data["answer_mode"], teaching_mode=data["POLICY"]["teaching_mode"],
    )
    coherence = checker_inconsistencies(normalized, answer_mode=data["answer_mode"], bindings=data["ACTUAL_CITATION_BINDINGS"])
    optimism = repairable_verdict_inconsistencies(normalized)
    expected = {row["claim_id"]: row for row in data["CLAIMS"]}
    returned = [row["claim_id"] for row in normalized["claims"]]
    identity_issues = []
    if len(returned) != len(expected) or set(returned) != set(expected):
        identity_issues.append({"code": "CLAIM_IDENTITY_MISMATCH"})
    available = {row["fragment_id"]: row for row in data["SOURCE_FRAGMENTS"]}
    basis_issues, proofs, support_gates = [], [], []
    for claim in normalized["claims"]:
        original = expected.get(claim["claim_id"])
        if original is None:
            continue
        ids = claim["fragment_ids"]
        basis = claim["basis"]
        if len(ids) != len(set(ids)) or any(fid not in available for fid in ids):
            identity_issues.append({"code": "FRAGMENT_IDENTITY_MISMATCH", "claim_id": claim["claim_id"]})
            continue
        if any(not available[fid]["complete_block"] and available[fid]["block_kind"] != "prose" for fid in ids):
            basis_issues.append({"code": "CHECK_INCOMPLETE_ATOMIC_BLOCK", "claim_id": claim["claim_id"]})
        if basis == "derived_calculation":
            proof = claim["derivation"]
            verified = validate_derivation(proof, original["text"], available, [data["question"], data["current_problem"]])
            proofs.append({"claim_id": claim["claim_id"], "validation": verified})
            proof_ids = ({proof["formula_fragment_id"]} if proof["formula_fragment_id"] is not None else set()) | {item["fragment_id"] for item in proof["inputs"] if item["origin"] == "textbook"}
            if not verified["valid"] or not proof_ids <= set(ids):
                basis_issues.append({"code": "CHECK_DERIVATION_INVALID", "claim_id": claim["claim_id"], "reason_code": verified.get("code")})
            support_gates.append(claim["status"] == "supported" and verified["valid"] is True)
        elif basis == "problem_input":
            quote = claim["problem_quote"]
            valid_given = bool(quote and (quote in data["question"] or quote in data["current_problem"]) and not ids and not original["evidence_ids"] and given_matches(original["text"], quote, [data["question"], data["current_problem"]]))
            if not valid_given:
                basis_issues.append({"code": "CHECK_PROBLEM_QUOTE_MISMATCH", "claim_id": claim["claim_id"]})
            support_gates.append(claim["status"] == "supported" and valid_given)
        elif basis == "general_knowledge":
            legal = data["answer_mode"] == "general_knowledge" and not ids and not original["evidence_ids"]
            if not legal:
                basis_issues.append({"code": "CHECK_GENERAL_KNOWLEDGE_BASIS_INVALID", "claim_id": claim["claim_id"]})
            support_gates.append(claim["status"] == "supported" and legal)
        elif basis == "evidence_limitation":
            if ids or original["evidence_ids"] or claim["factual"]:
                basis_issues.append({"code": "CHECK_LIMITATION_BASIS_INVALID", "claim_id": claim["claim_id"]})
            support_gates.append(not claim["factual"])
        elif claim["factual"]:
            if basis != "textbook" or (claim["status"] == "supported" and not ids):
                basis_issues.append({"code": "CHECK_SUPPORT_WITHOUT_SOURCE", "claim_id": claim["claim_id"]})
            support_gates.append(claim["status"] == "supported" and basis == "textbook" and bool(ids))
        else:
            support_gates.append(True)
    policy = data["POLICY"]
    hint = policy["teaching_mode"] == "hint"
    response = data["PROPOSED_DELIVERY"]["response"]
    gates = {
        "effective_body_ok": typed["body_ok"] and not optimism,
        "all_factual_support": bool(support_gates) and all(support_gates),
        "attempt_evaluation_ok": typed["attempt_evaluation_ok"],
        "tutor_question_ok": typed["tutor_question_ok"],
        "permitted_help": (typed["specific_help"] and typed["scope_ok"] and response.get("short_answer") is None) if hint else (typed["complete_answer"] and typed["coverage"] != "none" and (typed["coverage"] != "supported_partial" or typed["limitations_explicit"])),
        "enabled_suggestions": not (hint and policy["check_suggestions"]) or typed["suggestions_ok"],
        "enabled_evidence_display": not (hint and policy["control_evidence"]) or typed["evidence_display_ok"],
        "enabled_cumulative": not (hint and policy["check_cumulative"]) or typed["cumulative_ok"],
    }
    issues = binding_issues + requirement_contract + requirement_defects + coherence + identity_issues + basis_issues
    result.update(typed_valid=True, typed_judgment=typed, all_eleven_independent_flags={field: typed[field] for field in FLAGS}, exact_claim_count=len(expected), returned_claim_count=len(returned), binding_issues=binding_issues, requirement_contract_issues=requirement_contract, requirement_defects=requirement_defects, coherence_issues=coherence, identity_issues=identity_issues, basis_issues=basis_issues, optimistic_body_diagnostics=optimism, derivation_validations=proofs, original_applicable_surface_gates=gates, semantic_requirement_summary=summary, accepted_by_named_local_gates=not issues and all(gates.values()))
    return result


class TransportGuard:
    def __init__(self, out):
        self.out, self.plan, self.count, self.total = out, None, 0, 0
        self.numeric_ip, self.connect_count = None, 0
        sys.addaudithook(self.audit)

    def pinned_origin(self, event):
        caller = sys._getframe(2)
        if event == "socket.getaddrinfo" and caller.f_code is socket.getaddrinfo.__code__:
            caller = caller.f_back
        module = sys.modules.get("generation.adapters")
        outer = getattr(module, "_pinned_connection", None)
        code = getattr(outer, "__code__", None)
        if code is None or Path(code.co_filename) != E / "generation/adapters.py":
            raise PermissionError("Only the unchanged product pinned connection allowed")
        nested = [item for item in code.co_consts
                  if isinstance(item, types.CodeType) and item.co_name == "connect_to_pinned_ip"]
        if caller is None or caller.f_code is not socket.create_connection.__code__ or caller.f_back is None or len(nested) != 1 or caller.f_back.f_code is not nested[0]:
            raise PermissionError("Only product pinned stdlib connection origin allowed")
        selected = caller.f_back.f_locals.get("address")
        if not isinstance(selected, str) or caller.f_locals.get("host") != selected or caller.f_locals.get("port") != 443:
            raise PermissionError("Pinned connection address/port changed")
        return selected, caller

    def audit(self, event, values):
        if event in {"subprocess.Popen", "os.system", "os.spawn", "os.posix_spawn"}:
            raise PermissionError("Pair runner cannot launch external processes")
        if event == "open" and isinstance(values[0], (str, bytes)):
            path = Path(values[0]).absolute()
            if ".secrets" in [part.casefold() for part in path.parts] or path.name.casefold().startswith(".env") or path.name == "UNUSED_NO_KEY_FILE":
                raise PermissionError("Credential files are not admitted")
            mode, flags = values[1], values[2]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            if writing and path.is_relative_to(E):
                raise PermissionError("E writes are not admitted")
        if event == "socket.getaddrinfo":
            host = values[0]
            if host in {"127.0.0.1", "localhost"}:
                pass
            elif host == "openrouter.ai":
                if self.plan is None or self.count != 0 or len(values) < 2 or values[1] != 443:
                    raise PermissionError("Only the armed exact provider DNS query allowed")
            else:
                if self.plan is None or self.count != 1 or self.numeric_ip is not None or not isinstance(host, str) or len(values) < 4 or values[1] != 443 or values[3] != socket.SOCK_STREAM:
                    raise PermissionError("Only one post-audited pinned numeric resolution allowed")
                try:
                    address = ipaddress.ip_address(host)
                except ValueError as exc:
                    raise PermissionError("Numeric pinned address required") from exc
                if not address.is_global or (isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None) or str(address) != host or "%" in host:
                    raise PermissionError("Only canonical global nonmapped pinned IP allowed")
                selected, _caller = self.pinned_origin(event)
                if selected != host:
                    raise PermissionError("Numeric resolution does not match product selected IP")
                self.numeric_ip = host
        if event == "socket.connect":
            address = values[1]
            if isinstance(address, tuple) and address[:2] == ("127.0.0.1", 15433):
                return
            if self.plan is None or self.count != 1 or self.numeric_ip is None or self.connect_count or not isinstance(address, tuple) or len(address) not in (2, 4) or address[:2] != (self.numeric_ip, 443) or (len(address) == 4 and address[2:] != (0, 0)):
                raise PermissionError("Only one connection to the just-approved pinned IP443 allowed")
            selected, caller = self.pinned_origin(event)
            sock = values[0]
            expected_family = socket.AF_INET if ipaddress.ip_address(self.numeric_ip).version == 4 else socket.AF_INET6
            if selected != self.numeric_ip or caller.f_locals.get("sock") is not sock or sock.family != expected_family or sock.type != socket.SOCK_STREAM or sock.proto not in (0, 6):
                raise PermissionError("Pinned connection socket/origin changed")
            self.connect_count = 1
        if event != "urllib.Request":
            return
        url, raw, _headers, method = values
        if self.plan is None or self.count or self.total >= 1 or url != URL or method != "POST":
            raise PermissionError("Only the single original concise slot2 request allowed")
        body = json.loads(raw)
        if sha(raw) != self.plan["wire_sha256"] or len(raw) != self.plan["wire_bytes"] or body.get("model") != "google/gemini-3.5-flash-lite" or body.get("max_tokens") != 4096 or body.get("response_format") != {"type": "json_object"} or body.get("reasoning") != {"effort": "low"} or body.get("provider") != ROUTE:
            raise PermissionError("Exact fixed public wire/route changed")
        self.count, self.total = 1, self.total + 1
        save_new(self.out / (self.plan["arm"] + "-wire-observed01.json"), {"at_UTC": now(), "arm": self.plan["arm"], "physical_POST_observed_before_transport": True, "wire_sha256": sha(raw), "wire_bytes": len(raw), "output_cap": 4096, "response_format": "json_object", "raw_headers_exported": False})


def scrub(value, secret):
    if isinstance(value, str):
        return value.replace(secret, "[redacted]") if secret else value
    if isinstance(value, dict):
        return {key: scrub(item, secret) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item, secret) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser()
    for name in ("release", "budget", "reservation"):
        parser.add_argument("--" + name, type=Path, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute or not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise ValueError("Explicit ROOT -I -S -B --execute release required")
    release_pin, budget_pin, reservation_pin = (cli_pin(getattr(args, key), getattr(args, key + "_sha256")) for key in ("release", "budget", "reservation"))
    release = read_pin(release_pin, R)
    budget = read_pin(budget_pin, R)
    if budget.get("schema") != "5703_residual37_bounded_allocation_v1" or budget.get("status") != "PREPARED_RESIDUAL37_REQUIRES_ROOT_RELEASE_NOT_EXECUTION":
        raise ValueError("Exact residual37 allocation required")
    read_pin(reservation_pin)
    if release.get("schema") != "5703_successor38_group_release_v1" or release.get("status") != "ROOT_FROZEN_SUCCESSOR38_RELEASE" or release.get("group") != "checker_pair" or release["budget_pin"] != budget_pin or release["reservation_pin"] != reservation_pin or release["executable_pin"]["sha256"] != sha(Path(__file__).read_bytes()) or Path(release["executable_pin"]["path"]) != Path(__file__).absolute() or release.get("baseline_configuration_id") != CONFIG_ID or release.get("baseline_public_config_hash") != CONFIG_HASH or release.get("checker_project_test_id") != CHECKER_PROJECT_ID:
        raise ValueError("Exact ROOT checker pair release required")
    if release.get("residual37_provenance") != "ONLY_ORIGINAL38_UNSTARTED37_NO_BASELINE_RETRY":
        raise ValueError("Only original unstarted residual cells permitted")
    allowed = release.get("allowed_cells")
    if not isinstance(allowed, list) or len(allowed) != 1 or allowed[0].get("group") != "checker_pair" or allowed[0].get("slot") != 2:
        raise ValueError("Only unstarted original concise slot2 permitted")
    for name in ("residual37_transfer_pin", "prior_journal20_pin", "prior_finance20_pin", "old38_budget_pin"):
        read_pin(release[name], R if name != "prior_journal20_pin" else W)
    predecessor = read_pin(release["predecessor_failed_baseline_receipt_pin"], R)
    if predecessor.get("slot") != 1 or predecessor.get("arm") != "baseline" or predecessor.get("outcome") != "STOP_TRANSPORT_OR_UNKNOWN" or predecessor.get("HTTP_status") is not None or predecessor.get("usage", {}).get("cost") is not None:
        raise ValueError("Exact failed UNKNOWN predecessor baseline required; never replay it")
    nonce = release["execution_nonce"]
    if not re.fullmatch(r"[a-z0-9_-]{12,64}", nonce):
        raise ValueError("Fresh ROOT nonce required")
    frozen = {arm: read_pin({"path": str(path), "bytes": size, "sha256": digest}) for arm, (path, size, digest) in FROZEN.items()}
    if frozen["baseline"]["schema_name"] != "joint_check_v5" or frozen["concise"]["schema"] != frozen["baseline"]["schema"] or frozen["concise"]["configuration"] != frozen["baseline"]["configuration"] or frozen["concise"]["messages"][1:] != frozen["baseline"]["messages"][1:] or not frozen["concise"]["messages"][0]["content"].startswith(frozen["baseline"]["messages"][0]["content"] + "\n\n"):
        raise ValueError("Only the frozen append-only system candidate permitted")
    before = check_sources(release)
    helper_raw = ordinary(release["helper_pin"]["path"], R).read_bytes()
    if len(helper_raw) != release["helper_pin"]["bytes"] or sha(helper_raw) != release["helper_pin"]["sha256"]:
        raise ValueError("Exact shared guard helper required")
    helper = types.ModuleType("root_released_shared_successor_guard")
    helper.__file__ = release["helper_pin"]["path"]
    sys.modules[helper.__name__] = helper
    exec(compile(helper_raw, helper.__file__, "exec"), helper.__dict__)
    guard = helper.Guard(args.budget, args.budget_sha256, args.release, args.release_sha256)
    out = ordinary(R / ("actual-checker-pair-" + nonce), R)
    if out.exists():
        raise ValueError("Never replay an existing/unknown pair execution")
    out.mkdir()
    report = {"status": "ROOT_RESIDUAL_CONCISE_SLOT2_STARTED_NOT_QUALIFICATION", "at_UTC": now(), "planned_physical_requests": 1, "physical_requests": 0, "claimed_slots": [], "rows": [], "known_cost_USD": "0", "unknown_holds_USD": "0", "release_pin": release_pin, "budget_pin": budget_pin, "reservation_pin": reservation_pin, "source_pins": before, "schema_provenance": "Recorded actual schema name; complete schema reconstructed from pinned current ReliableCheckV5", "retry_calls": 0, "contract_repair_calls": 0, "generation_calls": 0, "native_publications": 0, "database_mutations": 0, "Gold_reads": 0, "E_writes": 0, "fresh_role_or_course_qualification": False, "residual37_provenance": release["residual37_provenance"], "execution_allowed_original_slots": [2], "baseline_not_replayed": True, "predecessor_failed_baseline_receipt_pin": release["predecessor_failed_baseline_receipt_pin"], "valid_paired_latency_comparison": False}
    save_new(out / "intent01.json", report)
    engine = settings = adapter = secret = None
    cleanup_errors = []
    starts = []
    engine_disposed = False
    code, known, unknown = 1, Decimal(0), Decimal(0)
    physical = TransportGuard(out)
    try:
        memory_key = os.environ.pop("MODEL_CONFIG_ENCRYPTION_KEY", None)
        if not memory_key or not re.fullmatch(r"[A-Za-z0-9_-]{43}=", memory_key):
            raise ValueError("ROOT child memory-only fixture encryption key required")
        os.environ.clear()
        os.environ.update(SystemRoot=r"C:\Windows", WINDIR=r"C:\Windows", PATH=r"D:\Python;C:\Windows\System32", APP_ENV="test", DATABASE_URL=DB, MODEL_CONFIG_ENCRYPTION_KEY=memory_key, MODEL_CONFIG_KEY_FILE=str(out / "UNUSED_NO_KEY_FILE"), MODEL_MODE="mock", LLM_PROVIDER="mock", PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TORCH_DEVICE_BACKEND_AUTOLOAD="0", TEMP=str(out), TMP=str(out))
        memory_key = None
        os.chdir(out)
        sys.path[:] = [str(E), str(E / "backend"), str(E / ".venv/Lib/site-packages"), str(W / "5703-complete-isolated-install-runtime-1994dfe8a40b/project/.venv/Lib/site-packages"), r"D:\Python\python313.zip", r"D:\Python\DLLs", r"D:\Python\Lib"]
        from app.core.config import Settings
        from app.db import models as registered_models
        from app.db.session import init_engine
        from app.modules.identity.models import User
        from app.modules.model_settings import service, compatibility
        from generation.adapters import LLMAdapter
        from generation.providers import payload, checker_transport_enabled
        from generation.parser import strict_json
        from generation.checker_encoding import decode
        from generation.reliability_v4 import compact_schema
        from generation.reliability_v5 import ReliableCheckV5
        from generation.token_counting import TokenCounter
        from generation.provider_diagnostics import safe_usage
        from sqlalchemy.orm import Session
        settings = Settings(_env_file=None)
        os.environ.pop("MODEL_CONFIG_ENCRYPTION_KEY", None)
        if settings.database_url != DB or not settings.model_config_encryption_key:
            raise ValueError("Only the retained owned synthetic fixture allowed")
        engine = init_engine(DB)
        with Session(engine) as db:
            db.connection().exec_driver_sql("SET TRANSACTION READ ONLY")
            actor = db.get(User, release["actor_id"])
            if not actor or actor.status != "active" or actor.role.name != "admin":
                raise ValueError("Exact active owned fixture actor required")
            row = service.owned(db, CONFIG_ID, actor)
            latest = compatibility.latest(db, row.id, "checker")
            compatibility.require_project_pass(db, row, latest.id if latest else None, "checker")
            if row.config_hash != CONFIG_HASH or not latest or latest.id != CHECKER_PROJECT_ID:
                raise ValueError("Exact current saved PROJECT-only baseline required")
            config = replace(service.as_model_config(row), max_tokens=4096, structured_output_mode="json_object")
            if config.to_dict() != frozen["baseline"]["configuration"] or config.window_tokens != 131072 or config.timeout_seconds != 45 or config.tokenizer_provider != "estimate" or checker_transport_enabled(config):
                raise ValueError("Exact frozen full-V5/json_object baseline required")
            if compact_schema(ReliableCheckV5) != frozen["baseline"]["schema"]:
                raise ValueError("Current complete typed schema changed")
            plans = []
            for slot, arm in enumerate(("baseline", "concise"), 1):
                item = frozen[arm]
                body = payload(config, item["messages"], item["schema"], item["schema_name"])
                if body.get("provider") != ROUTE or body.get("reasoning") != {"effort": "low"} or body.get("response_format") != {"type": "json_object"} or body.get("max_tokens") != 4096:
                    raise ValueError("Normal unchanged route/format/output required")
                raw_wire = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
                counter = TokenCounter(config)
                input_bound = counter.request_input(item["messages"], item["schema"], item["schema_name"])
                if input_bound + 4096 > 131072:
                    raise ValueError("Complete request plus output does not fit")
                plans.append({"slot": slot, "arm": arm, "wire_sha256": sha(raw_wire), "wire_bytes": len(raw_wire), "input_tokens_bound": input_bound, "token_counting": counter.metadata, "frozen_file_sha256": FROZEN[arm][2]})
            plans = [plan for plan in plans if plan["arm"] == "concise" and plan["slot"] == 2]
            if len(plans) != 1 or allowed != [{"group": "checker_pair", "slot": 2, "wire_sha256": plans[0]["wire_sha256"], "wire_bytes": plans[0]["wire_bytes"], "output_cap": 4096, "input_tokens_bound": plans[0]["input_tokens_bound"]}]:
                raise ValueError("Exact original concise wire/cap/input release required")
            secret = service.resolve_secret(db, settings, config.configuration_id)
            db.rollback()
        if not isinstance(secret, str) or not secret:
            raise ValueError("Existing normal encrypted credential unavailable")
        settings.model_config_encryption_key = None
        adapter = LLMAdapter(config, api_key=secret, retain_invalid_output=True)
        secret = None
        data = decode(strict_json(frozen["baseline"]["messages"][-1]["content"]))
        save_new(out / "frozen-pair-wire-bindings01.json", {"plans": plans, "configuration_id": CONFIG_ID, "existing_checker_PROJECT_test_id": CHECKER_PROJECT_ID, "course_BASIC_STRUCTURED_coverage": False, "new_prompt_not_previously_role_qualified": True})
        for plan in plans:
            if check_sources(release) != before:
                raise ValueError("Frozen source changed before pair transport")
            start = guard.claim("checker_pair", plan["slot"], nonce, wire_sha256=plan["wire_sha256"], wire_bytes=plan["wire_bytes"], output_cap=4096, input_tokens_bound=plan["input_tokens_bound"])
            starts.append(start)
            report["claimed_slots"].append(plan["slot"])
            unknown += BOUND
            report["unknown_holds_USD"] = str(unknown)
            save_new(out / (plan["arm"] + "-started01.json"), start)
            physical.plan, physical.count, physical.numeric_ip, physical.connect_count = plan, 0, None, 0
            began = time.perf_counter_ns()
            result = adapter.generate(frozen[plan["arm"]]["messages"], response_schema=frozen[plan["arm"]]["schema"], response_schema_name="joint_check_v5", timeout_seconds=45)
            physical.plan = None
            duration_ms = (time.perf_counter_ns() - began) / 1_000_000
            usage = safe_usage(result.usage or {})
            cost = usage.get("cost")
            settled = False
            cost_valid = False
            try:
                actual = Decimal(str(cost)) if cost is not None else None
                cost_valid = actual is not None and actual.is_finite() and actual >= Decimal(0)
                settled = cost_valid and actual <= BOUND
            except (InvalidOperation, ValueError, TypeError):
                actual = None
            public_raw = result.raw_text
            if adapter._api_key and (adapter._api_key in public_raw or json.dumps(adapter._api_key)[1:-1] in public_raw):
                public_raw = None
            validation = validate_output(public_raw, data) if public_raw is not None and not result.error and result.finish_reason == "stop" else None
            transport_ok = physical.count == 1 and result.request_submitted is True and not result.error and result.finish_reason == "stop" and result.diagnostic.get("http_status") == 200 and public_raw is not None
            outcome = "STOP_TRANSPORT_OR_UNKNOWN" if not transport_ok or not settled else "LOCAL_RETURNED_JUDGMENT_VALID" if validation["accepted_by_named_local_gates"] else "RETURNED_JUDGMENT_INVALID"
            record = {**plan, "at_UTC": now(), "outcome": outcome, "physical_POSTs": physical.count, "request_submitted": result.request_submitted, "observed_adapter_duration_ms": duration_ms, "reported_adapter_latency_ms": result.latency_ms, "finish_reason": result.finish_reason, "HTTP_status": result.diagnostic.get("http_status"), "provider_diagnostic": scrub(result.diagnostic, adapter._api_key), "provider_error": scrub(result.error, adapter._api_key), "usage": scrub(usage, adapter._api_key), "observed_cost_within_reserved_upper": settled, "raw_text": public_raw, "raw_text_sha256": sha(public_raw.encode()) if public_raw is not None and public_raw == result.raw_text else None, "validation": validation, "independent_scientific_evaluation": False, "native_publication": False}
            save_new(out / (plan["arm"] + "-finished01.json"), record)
            report["rows"].append(record)
            shared_finish = guard.finish(start, known_cost_USD=str(actual) if cost_valid else None, outcome=outcome, usage=scrub(usage, adapter._api_key))
            if settled:
                known += actual
                unknown -= BOUND
            report["physical_requests"] = physical.total
            report["known_cost_USD"], report["unknown_holds_USD"] = str(known), str(unknown)
            print(json.dumps({"arm": plan["arm"], "outcome": outcome, "physical_POSTs": physical.count, "known_cost_USD": str(known), "unknown_holds_USD": str(unknown)}), flush=True)
            if not transport_ok or not settled or shared_finish.get("must_stop") is True:
                raise ValueError("Stop without retry, repair or next arm")
        report["status"] = "ACTUAL_RESIDUAL_CONCISE_SLOT2_COMPLETE_DIAGNOSTIC_NOT_VALID_PAIR_COMPARISON"
        code = 0
    except BaseException as exc:
        report["status"] = "ACTUAL_RESIDUAL_CONCISE_SLOT2_STOPPED"
        report["exception_type"] = type(exc).__name__
        try:
            guard.stop("checker_pair stopped: " + type(exc).__name__)
        except BaseException as stop_exc:
            cleanup_errors.append("shared_stop:" + type(stop_exc).__name__)
    finally:
        physical.plan = None
        report["physical_requests"] = physical.total
        if adapter is not None:
            adapter._api_key = None
        secret = None
        if settings is not None:
            settings.model_config_encryption_key = None
        os.environ.pop("MODEL_CONFIG_ENCRYPTION_KEY", None)
        if engine is not None:
            try:
                engine.dispose()
                engine_disposed = True
            except BaseException as cleanup_exc:
                cleanup_errors.append("engine_dispose:" + type(cleanup_exc).__name__)
                code = 1
        try:
            report["focused_source_unchanged"] = check_sources(release) == before
            if not report["focused_source_unchanged"]:
                code = 1
        except BaseException as exc:
            report["source_readback_blocker_type"] = type(exc).__name__
            code = 1
        if code:
            report["status"] = "ACTUAL_RESIDUAL_CONCISE_SLOT2_STOPPED"
            try:
                guard.stop("checker_pair terminal or cleanup failure")
            except BaseException as stop_exc:
                cleanup_errors.append("terminal_shared_stop:" + type(stop_exc).__name__)
        # Started slots remain consumed even if the adapter or local receipt
        # fails. Reconcile only these two exact shared immutable finish paths.
        closed_known, remaining_holds = Decimal(0), Decimal(0)
        shared_receipts, inflight_unknown = [], []
        for start in starts:
            path = ordinary(start["started_pin"]["path"], R).with_name(f"slot-{start['slot']:02d}-finished01.json")
            try:
                if not path.exists():
                    raise FileNotFoundError("No shared immutable finish")
                raw = path.read_bytes()
                finish = json.loads(raw)
                if finish.get("started_pin") != start["started_pin"]:
                    raise ValueError("Shared finish ownership changed")
                status = finish["status"]
                if status not in {"UNKNOWN_FULL_HOLD_STOP", "KNOWN_COST_EXCEEDS_BOUND_STOP", "KNOWN_COST_RECORDED"}:
                    raise ValueError("Invalid shared finish status")
                cost = finish.get("known_API_cost_USD")
                if cost is None:
                    if status != "UNKNOWN_FULL_HOLD_STOP":
                        raise ValueError("Shared finish lacks its known cost")
                    remaining_holds += BOUND
                    inflight_unknown.append(start["slot"])
                else:
                    amount = Decimal(str(cost))
                    if not amount.is_finite() or amount < 0:
                        raise ValueError("Invalid shared known cost")
                    closed_known += amount
                shared_receipts.append({"slot": start["slot"], "pin": {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}, "status": status, "known_API_cost_USD": cost})
            except BaseException as receipt_exc:
                remaining_holds += BOUND
                inflight_unknown.append(start["slot"])
                cleanup_errors.append("shared_finish_readback:" + type(receipt_exc).__name__)
                code = 1
        report["known_cost_USD"], report["unknown_holds_USD"] = str(closed_known), str(remaining_holds)
        if code:
            report["status"] = "ACTUAL_RESIDUAL_CONCISE_SLOT2_STOPPED"
            try:
                guard.stop("checker_pair terminal receipt reconciliation failure")
            except BaseException as stop_exc:
                cleanup_errors.append("reconciled_shared_stop:" + type(stop_exc).__name__)
        report.update(engine_disposed=engine_disposed, cleanup_errors=cleanup_errors, shared_finished_receipts=shared_receipts, in_flight_or_UNKNOWN_slots=inflight_unknown, known_costs_within_unresolved_holds_not_added_twice=True, memory_key_references_cleared=True, unstarted_count=1-len(starts), response_rows_missing=len(starts)-len(report["rows"]), finished_at_UTC=now(), exit_code=code)
        save_new(out / "terminal-receipt01.json", report)
        print(json.dumps({"status": report["status"], "receipt": str(out / "terminal-receipt01.json"), "exit_code": code}), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
