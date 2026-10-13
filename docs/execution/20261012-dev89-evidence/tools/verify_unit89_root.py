"""Reuse the unchanged isolation guard with a finite test selection and sys capture."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import time

W = Path(__file__).resolve().parent
RUNNER = W / "run-unit88-root.py"
RUNNER_SHA = "2ca132717a54ae107f820f2ee16a95647f2b1199eca8347e9580dc9dcdafa1b8"
CODEC_SHA = "8c830694093b41e9f6250939de2cf9f72b24726bddbc1cba0141a6b8cb9efa56"
FILES = (
    "test_lossless_output_integration84.py", "test_single_selection_findings_v2.py",
    "test_single_selection_output_integration.py", "test_single_selection_teacher_contract.py",
    "test_single_selection_wire_contract.py", "test_source_relation_audit27.py",
    "test_source_relation_contract.py", "test_source_relation_correction_feedback.py",
    "test_source_relation_protection27.py", "test_source_relation_units_v2.py",
)

def load_runner():
    assert hashlib.sha256(RUNNER.read_bytes()).hexdigest() == RUNNER_SHA
    spec = importlib.util.spec_from_file_location("unit89_original_guard", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PINS["generation/lossless_unit_findings_v1.py"] = CODEC_SHA
    return module

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--selection", choices=("contracts", "full"), required=True)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    runner = load_runner()
    output = runner.output_path(args.output)
    if args.child:
        import pytest
        original = pytest.main
        def selected(original_args):
            target = str(runner.MAIN / "tests/unit")
            assert original_args.count(target) == 1 and not any(item.startswith("--capture") for item in original_args)
            new_args = []
            for item in original_args:
                if item == target and args.selection == "contracts":
                    new_args.extend(str(runner.MAIN / "tests/unit" / name) for name in FILES)
                else:
                    new_args.append(item)
            new_args.append("--capture=sys")
            print("FINITE_SELECTION " + json.dumps({"selection": args.selection, "capture": "sys", "files": list(FILES) if args.selection == "contracts" else "all234"}), flush=True)
            return original(new_args)
        pytest.main = selected
        return runner.child(output)
    before = runner.hashes()
    assert before == runner.PINS
    output.mkdir(exist_ok=False)
    (output / "temp").mkdir()
    (output / "tiktoken").mkdir()
    for name, expected in runner.TOKEN_CACHE.items():
        raw = (runner.MAIN / "artifacts/tiktoken" / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        with (output / "tiktoken" / name).open("xb") as out:
            out.write(raw)
    command = [str(runner.PYTHON), "-B", "-X", "utf8", str(Path(__file__).resolve()), "--child", "--selection", args.selection, "--output", str(output)]
    started = time.perf_counter()
    with (output / "pytest.log").open("x", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=runner.MAIN, env=runner.environment(output), stdout=log, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        timed_out = False
        try:
            code = process.wait(timeout=240)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            code = process.wait(timeout=3)
    after = runner.hashes()
    receipt = {"schema": "dev89_existing_guard_finite_selection_v1", "exit_code": code, "timed_out": timed_out,
        "timeout_seconds": 240, "elapsed_seconds": time.perf_counter()-started, "owned_pid": process.pid,
        "terminated_only_owned_child": timed_out, "full_suite_run": args.selection == "full", "selection": args.selection,
        "capture": "sys", "original_isolation_guard_sha256": RUNNER_SHA, "original_guard_changed": False,
        "selected_files": list(FILES) if args.selection == "contracts" else "all234",
        "source_pins_before": before, "source_pins_after": after, "current_B_six_pins_unchanged": before == after == runner.PINS,
        "all_test_outputs_in": str(output), "paid_network_and_real_PostgreSQL_allowed": False}
    with (output / "receipt.json").open("x", encoding="utf-8") as out:
        json.dump(receipt, out, indent=2)
    print(json.dumps({key: receipt[key] for key in ("exit_code", "timed_out", "elapsed_seconds", "selection", "capture", "current_B_six_pins_unchanged")}))
    return code if before == after == runner.PINS and not timed_out else 2

if __name__ == "__main__":
    raise SystemExit(main())
