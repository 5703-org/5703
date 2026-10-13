"""ROOT creates a reviewed original-cell continuation; never sends a request."""
import argparse
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
import types

R = Path(__file__).resolve().parent
W = R.parent
EXPECTED = {
    "ROOT-residual37-budget01.json": "a14c5a9c37429bb6597365cfa79d84d92b899f699bb00f5b8447ff3077a1b8e8",
    "shared_residual37_claim_guard_PREPARED01.py": "bc63d57d84f56e1a44a8b454de6e65321196d77da5191bf5341dfafe4cbe28ec",
    "ROOT-prior38-unstarted37-transfer01.json": "328aef96e1c80dac73945f132d6ae612e17590f688b815649cfa3db1d56c03ce",
    "run_ROOT_fixed_checker_pair_PREPARED02.py": "29df6f6ce3977499998a937131e3b64b798a6319be6115106069e3754237a2b0",
    "run_public_openqa36_PREPARED01.py": "2fea524f7b9f932d863dde0760f65a95c5d44a6c7e42a15bb2b652a0d2522bfe",
    "public12-openqa36-frozen-inputs01.json": "17d0135cc0e348e3336c39b878078808ab9dfea0178f29f5a247335830e80e3e",
    "ROOT-checker_pair-release02.json": "ec08c7e395a5b54b240e0b1ff35a415ca22abe2f12d9c6d74923e34ba1631c14",
    "ROOT-quality_openqa-release01.json": "5148e2add1fc4c77f2562bd8bd81cf34642e41fd695be69de4a31cd7925fe86b",
}

def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

def load(path):
    assert path.is_relative_to(W) and not path.is_symlink()
    return json.loads(path.read_bytes())

def save(path, value):
    with path.open("xb") as f:
        f.write((json.dumps(value, indent=2) + "\n").encode())
        f.flush()
        os.fsync(f.fileno())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", choices=("checker_pair", "quality_openqa"), required=True)
    a = ap.parse_args()
    for name, expected in EXPECTED.items():
        assert pin(R / name)["sha256"] == expected, name
    budget_path = R / "ROOT-residual37-budget01.json"
    budget = load(budget_path)
    helper_path = R / "shared_residual37_claim_guard_PREPARED01.py"
    old_path = R / ("ROOT-checker_pair-release02.json" if a.group == "checker_pair" else "ROOT-quality_openqa-release01.json")
    old = load(old_path)
    release = deepcopy(old)
    runner_path = R / ("run_ROOT_fixed_checker_pair_PREPARED02.py" if a.group == "checker_pair" else "run_public_openqa36_PREPARED01.py")
    release.update(budget_pin=pin(budget_path), helper_pin=pin(helper_path), executable_pin=pin(runner_path),
                   execution_nonce="root-residual-" + ("checker" if a.group == "checker_pair" else "quality") + "-20261008-01",
                   residual37_provenance="ONLY_ORIGINAL38_UNSTARTED37_NO_BASELINE_RETRY",
                   old_workers_closure_checks=budget["required_old_worker_closure_checks"],
                   ROOT_review="Explicit 01:05 user disclosure authority for the original two checker and36 matched-answer requests is retained. This release continues only unstarted original cells; failed baseline is consumed and its full UNKNOWN hold/STOP/records remain protected. No new call entitlement, baseline retry, private DB export or budget expansion. Same frozen wires, Google Vertex global route, LOW, price/input/output bounds. Missing shared or above-bound cost requires STOP and ROOT max(local actual, full bound) reconciliation before any later group.")
    for key in ("residual37_transfer_pin", "prior_journal20_pin", "prior_finance20_pin", "old38_budget_pin", "predecessor_failed_baseline_receipt_pin"):
        release[key] = budget[key]
    release["residual37_parent_release_pin"] = pin(old_path)
    extra = [pin(old_path), pin(budget_path), pin(helper_path), *[budget[key] for key in ("residual37_transfer_pin", "prior_journal20_pin", "prior_finance20_pin", "old38_budget_pin", "predecessor_failed_baseline_receipt_pin", "prior38_STOP_pin")]]
    if a.group == "checker_pair":
        binding_path = R / "actual-checker-pair-root-checker-pair-20261008-02/frozen-pair-wire-bindings01.json"
        binding = load(binding_path)
        plan = [p for p in binding["plans"] if p["slot"] == 2 and p["arm"] == "concise"]
        assert len(plan) == 1
        plan = plan[0]
        release["allowed_cells"] = [{"group": a.group, "slot": 2, "wire_sha256": plan["wire_sha256"], "wire_bytes": plan["wire_bytes"], "output_cap": 4096, "input_tokens_bound": plan["input_tokens_bound"]}]
        extra.append(pin(binding_path))
        name = "ROOT-checker_pair-release03.json"
    else:
        close_path = R / "ROOT-owned-root-residual-checker-20261008-01/closure.json"
        close = load(close_path)
        assert close["exit_code"] == 0 and close["cleanup_errors"] == []
        assert all(close[k] is True for k in ("own_job_active_zero_verified", "process_handle_closed", "job_handle_closed", "memory_key_cleared"))
        terminal_path = R / "actual-checker-pair-root-residual-checker-20261008-01/terminal-receipt01.json"
        terminal = load(terminal_path)
        assert terminal["exit_code"] == 0 and terminal["physical_requests"] == 1 and Decimal(terminal["unknown_holds_USD"]) == 0
        shared_path = R / "new-residual37-claims/checker_pair/slot-02-finished01.json"
        shared = load(shared_path)
        assert shared["status"] == "KNOWN_COST_RECORDED"
        row = terminal["rows"][0]
        assert Decimal(str(shared["known_API_cost_USD"])) == Decimal(str(row["usage"]["cost"])) <= Decimal("0.04956160")
        assert not (R / "new-residual37-claims/STOP-before-any-next-submission01.json").exists()
        release["old_workers_closure_checks"] = [*release["old_workers_closure_checks"], {"pin": pin(close_path), "active_count_key": "own_job_active_zero_verified", "expected_type": "bool", "expected_value": True, "required_true_keys": ["process_handle_closed", "job_handle_closed", "memory_key_cleared"], "required_empty_keys": ["cleanup_errors"]}]
        inputs = load(R / "public12-openqa36-frozen-inputs01.json")
        release["allowed_cells"] = [{"group": a.group, "slot": p["slot"], "wire_sha256": p["wire_sha256"], "wire_bytes": p["wire_bytes"], "output_cap": 768, "input_tokens_bound": p["estimated_input_allowance"]} for p in inputs["plans"]]
        assert len(release["allowed_cells"]) == 36
        extra.extend([pin(close_path), pin(terminal_path), pin(shared_path)])
        name = "ROOT-quality_openqa-release02.json"
    for p in extra:
        if p not in release["source_pins"]:
            release["source_pins"].append(p)
    out = R / name
    save(out, release)
    helper = types.ModuleType("root_residual37_preflight")
    helper.__file__ = str(helper_path)
    sys.modules[helper.__name__] = helper
    exec(compile(helper_path.read_bytes(), str(helper_path), "exec"), helper.__dict__)
    sys.argv[0] = str(runner_path)
    guard = helper.Guard(budget_path, pin(budget_path)["sha256"], out, pin(out)["sha256"])
    guard._verify_prior()
    tally = guard._tally()
    save(R / ("ROOT-residual37-" + a.group + "-preflight01.json"), {"status": "ROOT_GROUP_RELEASE_READONLY_PREFLIGHT_PASS", "release_pin": pin(out), "tally": tally, "provider_calls": 0, "credentials_read": 0, "DB_calls": 0, "claims_created": 0, "historical_files_written": 0})
    print(json.dumps({"status": "ROOT_GROUP_RELEASE_READONLY_PREFLIGHT_PASS", "release_pin": pin(out), "allowed_original_cells": len(release["allowed_cells"]), "new_phase_upper_USD": budget["maximum_new_submitted_upper_USD"]}))

if __name__ == "__main__":
    main()
