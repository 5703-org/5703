"""Bounded offline controls and prospective descriptor; no ledger/service writes."""
import ast
import copy
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal

W = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
P = W / "5703-repair90-preparation/budget-forward-candidate"
R = W / "5703-repair90-runtime"
MAIN = Path(r"E:\5703\learning-assistant")
sys.path.insert(0, str(R))
sys.path.insert(0, str(MAIN))
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value
budget = module("budget88", P / "budget88.py")
for name in ("generation", "contracts"):
    value = types.ModuleType(name)
    value.__path__ = [str(MAIN / name)]
    sys.modules[name] = value
from generation.types import ModelConfig
sys.modules["generation"].ModelConfig = ModelConfig
component = module("checker_component90", P / "checker_component90.py")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
review = {"purpose": "Root selected same saved Phase90 checker input after three closed BASE cases",
    "current_public_model_config_sha256": budget.QWEN_PUBLIC_SNAPSHOT_SHA256,
    "current_qwen_configuration": {"configuration_id": budget.QWEN_ID, "revision": 1,
        "config_hash": budget.QWEN_CONFIG_HASH, "stored_max_tokens": 2048,
        "stored_structured_output_mode": "json_schema", "comparison_max_tokens": 8192,
        "comparison_structured_output_mode": "json_object"},
    "quality_certification_from_decode_pass": False, "model_only_causal_comparison": False,
    "reasoning_profile_delta": "Gemini HIGH to Qwen disabled"}
base, slot, instance = "case01", 2, "component01qwen"
paths = {"scope": f"scope88-{base}.json", "checker_inputs": f"{base}/native-provider70/slot-{slot:02d}-public-inputs.json",
    "checker_claim": f"{base}/native-provider70/slot-{slot:02d}-claim.json",
    "base_final": f"{base}/native-provider70/final-receipt.json", "base_api_closure": f"{base}/api-closure77.json",
    "base_journey": f"{base}/journey-receipt88.json"}
pins = [{"role": role, "relative_path": rel, "bytes": (R/rel).stat().st_size, "sha256": sha(R/rel)} for role, rel in paths.items()]
scope = budget._read(R / paths["scope"])
descriptor = {"schema": "repair90_checker_component_descriptor_v1", "authorization": budget.AUTHORIZATION,
    "instance_id": instance, "kind": component.KIND, "base_case_id": base,
    "protocol_sha256": scope["cohort_protocol_sha256"], "question_sha256": scope["question_sha256"],
    "selected_checker_slot": slot, "actual_input_artifact_pins": pins, "source_pins": scope["source_pins"],
    "review_binding": review, "root_selected_authorized": True, "automatic_retry_or_reclaim": False}
inputs, _, messages, schema, config, wire, context, original_wire, delta = component.compile_task(R, descriptor)
descriptor.update(input_artifact_sha256=next(row["sha256"] for row in pins if row["role"] == "checker_inputs"),
    original_wire_sha256=hashlib.sha256(component._bytes(original_wire)).hexdigest(),
    contrast_wire_sha256=hashlib.sha256(component._bytes(wire)).hexdigest(), contrast_wire_bytes=len(component._bytes(wire)),
    context_sha256=context.digest, model_config=config.to_dict(), model_config_sha256=budget.public_digest(config.to_dict()),
    model_config_delta=delta, controller_pins={"budget88.py": sha(P/"budget88.py"),
    "normal_transport88.py": sha(R/"normal_transport88.py"), "checker_component90.py": sha(P/"checker_component90.py")})
target = P / f"{instance}-descriptor90-candidate.json"
with target.open("x", encoding="utf-8", newline="\n") as f:
    json.dump(descriptor, f, indent=2, ensure_ascii=False, allow_nan=False)
    f.write("\n")
pin = sha(target)
record_reader = budget._pinned_record
byte_reader = budget._pinned_record_bytes
def prospective_reader(path, expected_pin=None):
    if Path(path) == R / f"{instance}-descriptor90.json":
        return record_reader(target, expected_pin)
    return record_reader(path, expected_pin)
def prospective_bytes(path, expected_pin):
    name = Path(path).name
    if Path(path) == R / name and name in {"budget88.py", "checker_component90.py"}:
        return byte_reader(P / name, expected_pin)
    return byte_reader(path, expected_pin)
controls = []
def ok(name, action):
    action()
    controls.append({"control": name, "status": "PASS"})
def denied(name, action, expected):
    try:
        action()
    except budget.BudgetError as exc:
        assert exc.code == expected, (name, exc.code, expected)
    else:
        raise AssertionError(name)
    controls.append({"control": name, "status": "PASS", "expected_code": expected})
ledger = R / "cohort-ledger"
with patch.object(budget, "_pinned_record", prospective_reader), patch.object(budget, "_pinned_record_bytes", prospective_bytes):
    ok("actual closed Phase90 task / prospective descriptor admission", lambda: budget.validate_component(ledger, instance, pin))
    denied("other prospective diagnostic remains disabled", lambda: budget.validate_component(ledger, "component06qwen", pin), "EXACT_NEW_COMPONENT_LEDGER_REQUIRED")
    denied("ordinary claim refuses component", lambda: budget.claim_case(ledger, instance, descriptor["question_sha256"], descriptor["protocol_sha256"]), "FUTURE_COMPONENT_REQUIRES_SEPARATE_FROZEN_CONTROLLER")
    current = budget._scan(ledger)
    marker, cases, claims, settlements, exposures, counts, known, unknown = current
    captured = []
    record = {"schema": "repair90_checker_component_claim_v1", "authorization": budget.AUTHORIZATION,
        "protocol_sha256": descriptor["protocol_sha256"], "case_id": instance,
        "question_sha256": descriptor["question_sha256"], "physical_posts_maximum": 1,
        "component_descriptor_sha256": pin, "automatic_retry_or_reclaim": False}
    augmented = (marker, {**cases, instance: record}, claims, settlements, exposures, {**counts, instance: 0}, known, unknown)
    with patch.object(budget, "_scan", return_value=augmented), patch.object(budget, "_create", side_effect=lambda p,v,c: captured.append((str(p),v,c))):
        args = (ledger, instance, "checker", descriptor["contrast_wire_sha256"], descriptor["contrast_wire_bytes"])
        ok("one checker diagnostic reserves next global slot in memory only", lambda: budget.reserve_post(*args, purpose="diagnostic_check"))
        assert len(captured) == 1 and captured[0][1]["global_slot"] == len(claims) + 1
        denied("teacher forbidden", lambda: budget.reserve_post(ledger, instance, "teacher", args[3], args[4], purpose="diagnostic_check"), "COMPONENT_SINGLE_CHECKER_DIAGNOSTIC_ONLY")
        denied("wrong purpose forbidden", lambda: budget.reserve_post(*args, purpose="joint_check"), "COMPONENT_SINGLE_CHECKER_DIAGNOSTIC_ONLY")
        denied("wire mismatch forbidden", lambda: budget.reserve_post(ledger, instance, "checker", "0"*64, args[4], purpose="diagnostic_check"), "COMPONENT_RESERVED_WIRE_CHANGED")
        with patch.object(budget, "_scan", return_value=(*augmented[:5], {**counts, instance: 1}, known, unknown)):
            denied("second physical request forbidden", lambda: budget.reserve_post(*args, purpose="diagnostic_check"), "CASE_POST_LIMIT")
        with patch.object(budget, "_scan", return_value=(*augmented[:7], budget.HOLD)):
            denied("UNKNOWN blocks reservation", lambda: budget.reserve_post(*args, purpose="diagnostic_check"), "UNSETTLED_PROTECTION_BLOCKS_POSTS")
        with patch.object(budget, "_scan", return_value=(*augmented[:6], budget.COST_CAP, unknown)):
            denied("shared dollar cap retained", lambda: budget.reserve_post(*args, purpose="diagnostic_check"), "COHORT_BUDGET_EXHAUSTED")
    before_ast = ast.parse((R/"budget88.py").read_text(encoding="utf-8"))
    after_ast = ast.parse((P/"budget88.py").read_text(encoding="utf-8"))
    functions = lambda tree: {n.name: ast.dump(n, include_attributes=False) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    old, new = functions(before_ast), functions(after_ast)
    for name in ("settle_post", "stop_cohort", "_create", "_amount", "_next_steps", "next_step_allowed", "claim_case", "validate_protocol", "initialize_cohort"):
        assert old[name] == new[name], name
    controls.append({"control": "9 existing financial / normal / protocol core ASTs unchanged", "status": "PASS"})
result = {"schema": "repair90_prospective_component_pure_controls_v1", "status": "PASS", "controls": controls,
    "actual_runtime_modified": False, "actual_ledger_modified": False, "auth_read": False, "database_access": False,
    "network_or_model_calls": 0, "controller_run_invoked": False, "main_writes": False,
    "prospective_path_remapping_only": ["descriptor W candidate", "budget/controller W source pin candidates"],
    "base_input_public_sha256": descriptor["input_artifact_sha256"], "source_version_sha256": component.SOURCE_VERSION,
    "descriptor_candidate_sha256": pin, "compiled_wire_bytes": descriptor["contrast_wire_bytes"],
    "full_context_sha256": context.digest, "full_task_messages_unchanged": True,
    "canonical_schema_unchanged": context.canonical_schema_sha256,
    "packet_counts": {name: len(context.packet[name]) for name in ("CLAIMS", "SOURCE_FRAGMENTS", "CONTEXT_COVERAGE")},
    "config_delta": delta, "wire_delta_keys": [key for key in wire if wire[key] != original_wire.get(key)],
    "snapshot_before": budget.snapshot(ledger), "quality_certification": False}
with (P/"proof-forward90.json").open("x", encoding="utf-8", newline="\n") as f:
    json.dump(result, f, indent=2, ensure_ascii=False, allow_nan=False)
    f.write("\n")
print(json.dumps({"status": result["status"], "controls": len(controls), "descriptor_sha256": pin,
    "proof_sha256": sha(P/"proof-forward90.json"), "wire_bytes": result["compiled_wire_bytes"]}))
