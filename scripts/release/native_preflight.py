"""Bounded native-wheel imports before Windows migration, imports or service startup.

This checks installed torch/PyMuPDF libraries, including on CPU. It does not
load model weights, probe a provider, inspect application settings or install DLLs.
"""

from __future__ import annotations

import argparse
import importlib
from importlib import metadata
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys

MODULES = ("torch", "pymupdf")
DEFAULT_TIMEOUT_SECONDS = 20.0
VC_RUNTIME_HELP = "https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist"
PROTOCOL = "windows_native_import_v1"


def _identifier(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,79}", value) else None


def _failure(module, code, kind, *, winerror=None, dependency=None, native_file=None):
    result = {"schema": PROTOCOL, "module": module, "status": "failed", "code": code,
              "exception_class": kind, "winerror": winerror, "dependency": dependency,
              "native_file": native_file}
    if code == "NATIVE_MODULE_MISSING":
        message = f"{module} is not installed in this Python environment; install the application's locked dependencies."
    elif code == "NATIVE_DEPENDENCY_MISSING":
        message = f"{module} cannot import dependency {dependency or 'not identified'}; install the application's locked dependencies."
    elif code == "NATIVE_IMPORT_TIMEOUT":
        message = f"{module} did not finish its native import within the stated timeout; startup was stopped."
    elif code == "NATIVE_LIBRARY_LOAD_FAILED":
        detail = f"; WinError {winerror}" if winerror is not None else ""
        detail += f"; {native_file}" if native_file else ""
        detail += f"; component {dependency}" if dependency else ""
        message = (f"{module} could not load a native dependency ({kind}{detail}). "
                   "Check the Python/wheel architecture and Microsoft Visual C++ v14 Redistributable. "
                   "Another dependent DLL can also cause this error; do not copy loose DLLs into the application.")
        result["official_runtime_help"] = VC_RUNTIME_HELP
    else:
        message = f"{module} native-import check failed ({kind}); inspect the selected environment before startup."
    result["message"] = message
    return result


def probe_in_process(module, *, importer=importlib.import_module):
    """Run only in the dedicated child; expose typed observations, never raw stderr."""
    try:
        importer(module)
    except (ImportError, OSError) as error:
        files = re.findall(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]{1,100}\.(?:dll|pyd))\b", str(error), re.I)
        winerror = getattr(error, "winerror", None)
        winerror = winerror if type(winerror) is int else None
        if isinstance(error, ModuleNotFoundError):
            code = "NATIVE_MODULE_MISSING" if getattr(error, "name", None) == module else "NATIVE_DEPENDENCY_MISSING"
        else:
            code = "NATIVE_LIBRARY_LOAD_FAILED" if isinstance(error, OSError) or "dll" in str(error).lower() else "NATIVE_IMPORT_FAILED"
        return _failure(module, code,
                        type(error).__name__, winerror=winerror, dependency=_identifier(getattr(error, "name", None)),
                        native_file=files[0] if files else None)
    except Exception as error:
        return _failure(module, "NATIVE_IMPORT_FAILED", type(error).__name__)
    try:
        version = metadata.version(module)
    except metadata.PackageNotFoundError:
        version = None
    return {"schema": PROTOCOL, "module": module, "status": "passed", "version": version,
            "python_bits": struct.calcsize("P") * 8}


def check_native_imports(*, timeout_seconds=DEFAULT_TIMEOUT_SECONDS, runner=subprocess.run):
    if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 30:
        raise ValueError("Native import timeout must be greater than zero and at most 30 seconds per module")
    rows = []
    for module in MODULES:
        argv = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child", module]
        try:
            completed = runner(argv, capture_output=True, timeout=timeout_seconds,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            row = _failure(module, "NATIVE_IMPORT_TIMEOUT", "TimeoutExpired")
        except OSError as error:
            row = _failure(module, "NATIVE_IMPORT_PROCESS_FAILED", type(error).__name__)
        else:
            try:
                value = json.loads(completed.stdout)
                if (value.get("schema") != PROTOCOL or value.get("module") != module or
                    value.get("status") not in {"passed", "failed"} or
                    (completed.returncode == 0) != (value["status"] == "passed") or
                    (value["status"] == "passed" and value.get("python_bits") != struct.calcsize("P") * 8)):
                    raise ValueError("Invalid native child result")
                # Preserve only the child protocol fields; echoed settings, paths
                # or third-party output cannot become a successful public report.
                row = {k: value[k] for k in ("schema", "module", "status", "version", "python_bits", "code",
                       "exception_class", "winerror", "dependency", "native_file", "official_runtime_help", "message") if k in value}
            except (ValueError, TypeError, AttributeError):
                row = _failure(module, "NATIVE_IMPORT_PROCESS_FAILED", "InvalidChildResult")
            row["exit_code"] = completed.returncode
        row["timeout_seconds"] = timeout_seconds
        rows.append(row)
    return {"schema": "windows_native_dependency_preflight_v1",
            "status": "PASS_NATIVE_IMPORTS" if all(r["status"] == "passed" for r in rows) else "NATIVE_DEPENDENCY_PREFLIGHT_FAILED",
            "python_bits": struct.calcsize("P") * 8, "checks": rows,
            "scope": "Installed native imports only; model weights, retrieval readiness and provider compatibility are not checked.",
            "database_or_service_actions": 0, "dependency_installations": 0, "model_or_provider_calls": 0}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    p.add_argument("--child", choices=MODULES, help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    result = probe_in_process(a.child) if a.child else check_native_imports(timeout_seconds=a.timeout_seconds)
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] in {"passed", "PASS_NATIVE_IMPORTS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
