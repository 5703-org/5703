"""Offline relocation regression for two opt-in loaders, without app/provider imports.

Only four public source files are copied to a fresh work path containing spaces.
The real codec path/hash gate runs, then its first downstream import is stopped
deliberately. The actual pinned calculator AST runs. No compile_saved call runs.
"""

from __future__ import annotations

import argparse
import builtins
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


PINNED = {
    "generation/experimental_fixed_id_checker_v1.py": "7e5f63aff032ea1129dfa69471666519d03dad555fe0a3c04a053ec933071870",
    "generation/scoped_support_contract_v1.py": "5537670c0215b6eb2470181c7141eda936329a83c7f6a4c7a2c9bce2ab8f0a52",
    "generation/lossless_unit_findings_v1.py": "8c830694093b41e9f6250939de2cf9f72b24726bddbc1cba0141a6b8cb9efa56",
    "generation/reliability_v3.py": "33d72113ee45fa489adaaf274dbfa8f1b342d8cd0834cbb8188713f6c3254fa2",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, message):
    if not value:
        raise AssertionError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, work, output = args.source_root.resolve(), args.work.absolute(), args.output.absolute()
    require(not work.exists() and work.resolve() == work and " " in str(work), "Use a fresh real work path containing spaces")
    require(not work.is_relative_to(source) and not source.is_relative_to(work), "Work must be separate from the source installation")
    require(output.parent.is_dir() and not output.exists(), "Use a new receipt in an existing evidence directory")
    source_before = {}
    for relative, expected in PINNED.items():
        raw = (source / relative).read_bytes()
        require(len(raw) < 1_000_000 and sha(raw) == expected, "Source pin mismatch: " + relative)
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(raw)
        source_before[relative] = sha(raw)
    record = {"schema": "phase182_offline_relocated_loader_v1", "utc": datetime.now(timezone.utc).isoformat(), "helper_sha256": sha(Path(__file__).read_bytes()), "source_root": str(source), "work": str(work), "source_pins": source_before, "cases": [], "network_attempts": [], "forbidden_imports": [], "intentional_codec_import_stops": 0, "compile_saved_calls": 0}

    def audit(event, values):
        if event.startswith("socket.") or event.startswith("http.client.") or event == "urllib.Request":
            record["network_attempts"].append(event)
            raise AssertionError("Network use is forbidden")

    class CodecBoundary(Exception):
        pass

    original_import = builtins.__import__

    def guarded_import(name, *values, **options):
        if name == "generation.lossless_unit_findings_v1":
            record["intentional_codec_import_stops"] += 1
            raise CodecBoundary("Real pinned codec path/hash validation completed; downstream compiler intentionally not imported")
        if any(name == prefix or name.startswith(prefix + ".") for prefix in ("app", "sqlalchemy", "psycopg", "httpx", "requests", "generation.adapters", "generation.provider_transport", "generation.service", "generation.checked")):
            record["forbidden_imports"].append(name)
            raise AssertionError("Application/provider import is forbidden: " + name)
        return original_import(name, *values, **options)

    sys.addaudithook(audit)
    builtins.__import__ = guarded_import
    try:
        fixed = load("relocated_fixed182", work / "generation/experimental_fixed_id_checker_v1.py")
        scoped = load("relocated_scoped182", work / "generation/scoped_support_contract_v1.py")

        def case(name, callback):
            try:
                callback()
                record["cases"].append({"name": name, "status": "PASS"})
            except Exception as error:
                record["cases"].append({"name": name, "status": "FAIL", "type": type(error).__name__, "message": str(error)[:500]})

        def root_case():
            require(fixed.MAIN == work, "Experiment still resolves a developer-host root")
            require(fixed.CODEC_SHA == PINNED["generation/lossless_unit_findings_v1.py"], "Codec pin changed")
            try:
                fixed._context({"messages": []})
            except CodecBoundary:
                return
            raise AssertionError("The real codec hash gate did not reach its deliberate downstream boundary")

        def codec_hash_case():
            path = work / "generation/lossless_unit_findings_v1.py"
            raw = path.read_bytes()
            try:
                path.write_bytes(raw + b"\n# isolated changed-pin negative case\n")
                try:
                    fixed._context({"messages": []})
                except ValueError as error:
                    require(str(error) == "CURRENT_B_CODEC_CHANGED", "Codec mismatch failed for an unexpected reason")
                    return
                raise AssertionError("Changed codec bytes passed the pin")
            finally:
                path.write_bytes(raw)

        def arithmetic_case():
            require(scoped.CALCULATOR_SOURCE_SHA == PINNED["generation/reliability_v3.py"], "Calculator pin changed")
            calculate = scoped._calculator()
            require(calculate("x * 2 + 1", {"x": Decimal("3")}) == Decimal("7"), "Pinned calculator arithmetic changed")

        def missing_case():
            path = work / "generation/reliability_v3.py"
            backup = path.with_suffix(".py.missing182")
            require(not backup.exists() and path.parent == work / "generation", "Missing-file fixture is not confined")
            path.rename(backup)
            scoped._calculator.cache_clear()
            try:
                try:
                    scoped._calculator()
                except scoped.ContractIssue as error:
                    require(error.code == "CALCULATOR_SOURCE_MISSING" and error.unresolved is True, "Missing source did not fail closed with its explicit unresolved code")
                    return
                raise AssertionError("Missing sibling used a host fallback")
            finally:
                backup.rename(path)
                scoped._calculator.cache_clear()

        def calculator_hash_case():
            path = work / "generation/reliability_v3.py"
            raw = path.read_bytes()
            scoped._calculator.cache_clear()
            try:
                path.write_bytes(raw + b"\n# isolated changed-pin negative case\n")
                try:
                    scoped._calculator()
                except scoped.ContractIssue as error:
                    require(error.code == "CALCULATOR_PIN_CHANGED" and error.unresolved is True, "Changed calculator pin failed for an unexpected reason")
                    return
                raise AssertionError("Changed calculator bytes passed the pin")
            finally:
                path.write_bytes(raw)
                scoped._calculator.cache_clear()

        for name, callback in (("relocated_root_and_real_codec_hash_gate", root_case), ("changed_codec_pin_rejected", codec_hash_case), ("relocated_actual_calculator_arithmetic", arithmetic_case), ("missing_sibling_fails_closed_without_host_fallback", missing_case), ("changed_calculator_pin_rejected", calculator_hash_case)):
            case(name, callback)
    finally:
        builtins.__import__ = original_import
    record["source_inputs_unchanged"] = all(sha((source / relative).read_bytes()) == expected for relative, expected in source_before.items())
    record["work_source_copies_restored"] = all(sha((work / relative).read_bytes()) == expected for relative, expected in source_before.items())
    record["status"] = "PASS" if len(record["cases"]) == 5 and all(row["status"] == "PASS" for row in record["cases"]) and not record["network_attempts"] and not record["forbidden_imports"] and record["source_inputs_unchanged"] and record["work_source_copies_restored"] else "FAIL"
    record["limits"] = "Codec path/hash gate and actual pinned calculator only; codec/compiler downstream import intentionally stopped; no semantic, provider, application or database acceptance."
    raw = (json.dumps(record, indent=2) + "\n").encode()
    with output.open("xb") as handle:
        handle.write(raw)
    print(json.dumps({"status": record["status"], "cases": len(record["cases"]), "receipt": str(output), "sha256": sha(raw)}))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
