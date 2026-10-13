"""Adopt one reviewed input-only codec repair after all actual A runs have closed."""
from pathlib import Path
import ast
import hashlib
import json
from datetime import datetime, timezone

W = Path(__file__).resolve().parent
R = W / "5703-dev89-runtime"
P = W / "5703-dev89-preparation"
C = P / "selection-index-candidate"
MAIN = Path(r"E:\5703\learning-assistant")
target = MAIN / "generation/lossless_unit_findings_v1.py"
sha = lambda raw: hashlib.sha256(raw).hexdigest()
canonical = lambda obj: json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
assert sha((C / "release-selection-index89.json").read_bytes()) == "380c30ccabb4dd5f061edba2094eee76bbf287dc9e4be7f492de19e3cdb00424"
assert sha((C / "control-selection-index89-frozen.json").read_bytes()) == "fdbaf8f15b940263a3216216c91faae7804bcd27597b83975507afbe2a994633"
candidate = (C / target.name).read_bytes()
assert sha(candidate) == "8c830694093b41e9f6250939de2cf9f72b24726bddbc1cba0141a6b8cb9efa56"
protocol = json.loads((R / "protocol88.json").read_bytes())
before = protocol["source_pins"]
assert sha(canonical(before)) == "f7f03e32b3bab3f539002e53798cc5abdfc0f7816d37d78d85401eff8e1ce5d2"
for pin in before:
    raw = Path(pin["path"]).read_bytes()
    assert sha(raw) == pin["sha256"] and len(raw) == pin["bytes"], pin["path"]
assert target.resolve(strict=True) == target and not target.is_symlink()
original = target.read_bytes()
assert sha(original) == "81045fec9ddc851eda6f445bdd99b20c056de07c36a8acb7264fdbc5c2f5d459"
old_tree, new_tree = ast.parse(original), ast.parse(candidate)
def other_nodes(tree):
    return [ast.dump(node, include_attributes=False) for node in tree.body
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            or node.name not in {"reference_instructions", "_selection_index"}]
assert other_nodes(old_tree) == other_nodes(new_tree), "INPUT_ONLY_CHANGE_BOUNDARY"
cases = [item["case_id"] for item in protocol["cases"]] + ["case10", "case10b"]
total_posts, settled = 0, 0
from decimal import Decimal
cost = Decimal(0)
actual_pins = []
for case in cases:
    directory = R / case
    for relative in ("native-provider70/final-receipt.json", "api-closure77.json"):
        raw = (directory / relative).read_bytes()
        actual_pins.append({"path": str(directory / relative), "bytes": len(raw), "sha256": sha(raw)})
    final = json.loads((directory / "native-provider70/final-receipt.json").read_bytes())
    closure = json.loads((directory / "api-closure77.json").read_bytes())
    assert final["closure_status"] == "CLOSED_NUMERIC_NO_UNKNOWN" and not final["cohort_permanently_stopped"]
    assert Decimal(final["cohort_unknown_full_hold_USD"]) == 0
    assert final["settled_numeric_cost_observations"] == final["actual_posts"]
    assert closure["owned_threads_closed"] and all(closure["old_metadata_unchanged"].values())
    total_posts += final["actual_posts"]
    settled += final["settled_numeric_cost_observations"]
    cost += Decimal(final["native_settled_known_cost_USD"])
assert total_posts == settled == 28 and cost == Decimal("0.4056684")
for page in ("case10", "case10b"):
    terminal = json.loads((R / page / "root-page-terminal88.json").read_bytes())
    assert all(item["closed"] and item["reader_closed"] for item in terminal["owned_process_cleanup"].values())
with (W / "phase89-codec-preimage.py").open("xb") as out:
    out.write(original)
target.write_bytes(candidate)
after = []
for pin in before:
    raw = Path(pin["path"]).read_bytes()
    new_pin = {**pin, "bytes": len(raw), "sha256": sha(raw)}
    if Path(pin["path"]) != target:
        assert new_pin == pin
    after.append(new_pin)
assert target.read_bytes() == candidate
record = {"schema": "dev89_one_input_only_common_repair_adoption_v1", "status": "ADOPTED_FREE_VERIFICATION_PENDING",
    "created_utc": datetime.now(timezone.utc).isoformat(), "target": str(target),
    "before_sha256": sha(original), "after_sha256": sha(candidate),
    "source_pins_before": before, "source_pins_after": after,
    "source_version_before_sha256": sha(canonical(before)), "source_version_after_sha256": sha(canonical(after)),
    "other15_source_files_unchanged": True, "all_actual_A_runs_closed_before_B": True,
    "actual_A_closure_pins": actual_pins, "actual_A_POSTs": total_posts, "actual_A_cost_USD": str(cost),
    "actual_B_POSTs": 0, "model_quality_or_latency_improvement_certified": False,
    "actual_B_retest_blocker": "Frozen NONPAGE_POST_CAP=24 already consumed by BASE; AUX needs nonpage+4<=24. No missing authorization or cash-budget exhaustion.",
    "decoder_and_schema_AST_unchanged": True, "new_default_activation": False,
    "original_preserved_path": str(W / "phase89-codec-preimage.py")}
with (P / "common-repair-adoption89-root.json").open("xb") as out:
    out.write((json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode())
print(json.dumps({key: record[key] for key in ("status", "before_sha256", "after_sha256", "source_version_after_sha256", "actual_B_POSTs")}))
