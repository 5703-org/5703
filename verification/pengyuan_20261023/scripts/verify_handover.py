"""Offline handover integrity and bounded component verification.

Publication adaptation (23 October 2026): input/output paths are CLI arguments;
the original checks are retained. Requires the original package snapshots.
The report_date_sydney field labels the original reporting date, not a rerun date.

This does NOT verify the 22 October matching full release: it is absent locally.
The current supplied module is loaded first; absent contracts/generation imports
come from the labelled 19 October snapshot. No source file is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
import traceback
import zipfile
from datetime import datetime, timezone

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True, help="Extracted handover root containing MODULE-INDEX.json and learning-assistant/")
parser.add_argument("--old-full", type=Path, required=True, help="19 October complete learning-assistant directory")
parser.add_argument("--old-owner", type=Path, required=True, help="19 October owner learning-assistant directory")
parser.add_argument("--old-zip", type=Path, required=True, help="Original 19 October complete application ZIP")
parser.add_argument("--output", type=Path, required=True, help="New local JSON path; existing files will not be overwritten")
args = parser.parse_args()
SOURCE = args.source.resolve()
OWNER = SOURCE / "learning-assistant"
OLD_FULL = args.old_full.resolve()
OLD_OWNER = args.old_owner.resolve()
OLD_ZIP = args.old_zip.resolve()
OUTPUT = args.output.resolve()
if OUTPUT.exists():
    parser.error("Output already exists; choose a new local file to preserve archived evidence.")
sys.dont_write_bytecode = True
network_attempts = []

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def block_network(*args, **kwargs):
    network_attempts.append("blocked")
    raise RuntimeError("Network disabled for offline handover verification")

socket.create_connection = block_network
socket.socket.connect = block_network
socket.socket.connect_ex = block_network

index = json.loads((SOURCE / "MODULE-INDEX.json").read_text(encoding="utf-8"))
with zipfile.ZipFile(OLD_ZIP) as archived:
    old_archive_profile_tests = [name for name in archived.namelist() if name.replace("\\", "/").endswith("/tests/unit/test_profiles.py")]
files = []
for item in index["member"]["files"]:
    rel = item["path"]
    file = OWNER / rel
    old_full = OLD_FULL / rel
    old_owner = OLD_OWNER / rel
    actual = digest(file)
    files.append({
        "path": rel,
        "bytes": file.stat().st_size,
        "sha256": actual,
        "matches_index_hash": actual == item["sha256"],
        "matches_index_size": file.stat().st_size == item["bytes"],
        "present_in_19_oct_complete": old_full.is_file(),
        "matches_19_oct_complete": digest(old_full) == actual if old_full.is_file() else None,
        "present_in_19_oct_owner": old_owner.is_file(),
        "matches_19_oct_owner": digest(old_owner) == actual if old_owner.is_file() else None,
    })
assert len(files) == 14
assert all(f["matches_index_hash"] and f["matches_index_size"] for f in files)

# Explicitly labelled compatibility harness: use current personalisation source,
# older supporting contracts/generation modules, and no repository conftest.
sys.path.insert(0, str(OLD_FULL))
sys.path.insert(0, str(OWNER))
test_file = OWNER / "tests/unit/test_profiles.py"
spec = importlib.util.spec_from_file_location("handover_component_tests", test_file)
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
from personalisation.compiler import turn_override
from generation.adapters import LLMAdapter
original_generate = LLMAdapter.generate
mock_calls = []

def mock_only_generate(self, *args, **kwargs):
    if self.config.provider != "mock":
        raise RuntimeError("Only the built-in authored mock adapter is permitted")
    mock_calls.append(self.config.provider)
    return original_generate(self, *args, **kwargs)

LLMAdapter.generate = mock_only_generate
test_results = []
for name in sorted(n for n in vars(tests) if n.startswith("test_")):
    try:
        getattr(tests, name)()
        test_results.append({"name": name, "status": "passed"})
    except Exception as exc:
        test_results.append({"name": name, "status": "failed", "error": str(exc), "traceback": traceback.format_exc()})

negative_probes = []
for message in ("Do not simplify; keep advanced terminology.", "Please do not give more detail."):
    observed = turn_override(message)
    negative_probes.append({
        "message": message,
        "expected": None,
        "observed": observed,
        "negation_mismatch_reproduced": observed is not None,
    })

imports = []
for name, module in sorted(sys.modules.items()):
    file = getattr(module, "__file__", None)
    if file:
        path = Path(file).resolve()
        if path.is_file() and (path.is_relative_to(OLD_FULL) or path.is_relative_to(OWNER)):
            imports.append({"module": name, "path": str(path), "sha256": digest(path), "source": "current_handover" if path.is_relative_to(OWNER) else "older_19_oct_complete_dependency"})

source_unchanged = all(digest(OWNER / f["path"]) == f["sha256"] for f in files)
result = {
    "schema": "handover_offline_component_receipt_v1",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "report_date_sydney": "2026-10-23",
    "python_executable": sys.executable,
    "scope": "Integrity comparison and isolated current-module tests with explicitly older shared dependency snapshot, not full release acceptance.",
    "matching_full_application_required": "CS30-1_20261022_Prompt_Contract_Complete_Application.zip",
    "matching_full_archive_sha256_from_index": index["complete_archive_sha256"],
    "matching_full_release_verified_by_this_run": False,
    "files": files,
    "old_archive_test_file_check": {"archive": str(OLD_ZIP), "matching_entries": old_archive_profile_tests, "interpretation": "The test file is newly included relative to the supplied 19 October package; this does not establish its original authoring date or personal authorship."},
    "summary": {
        "indexed_files": len(files),
        "hashes_and_sizes_matching_index": sum(f["matches_index_hash"] and f["matches_index_size"] for f in files),
        "identical_to_19_oct_complete": sum(f["matches_19_oct_complete"] is True for f in files),
        "identical_to_19_oct_owner": sum(f["matches_19_oct_owner"] is True for f in files),
        "absent_from_19_oct_complete": [f["path"] for f in files if not f["present_in_19_oct_complete"]],
        "absent_from_19_oct_owner": [f["path"] for f in files if not f["present_in_19_oct_owner"]],
        "included_test_functions": len(test_results),
        "included_test_functions_passed": sum(t["status"] == "passed" for t in test_results),
        "built_in_mock_calls": len(mock_calls),
        "external_model_calls": 0,
        "network_attempts": len(network_attempts),
        "negative_probes_checked_separately": len(negative_probes),
        "negative_probe_mismatches": sum(n["negation_mismatch_reproduced"] for n in negative_probes),
        "source_files_unchanged": source_unchanged,
    },
    "tests": test_results,
    "negative_probes": negative_probes,
    "imports_with_provenance": imports,
    "shared_prompt_dependency": {"path": str(OLD_FULL / "generation/prompts/teaching_v1.txt"), "sha256": digest(OLD_FULL / "generation/prompts/teaching_v1.txt"), "source": "older_19_oct_complete_dependency"},
    "limitations": [
        "The owner partition does not include the matching contracts, generation, API, database or UI.",
        "Supporting modules came from 19 October, not the specified 22 October complete release.",
        "The included test file contains four test functions; its three-by-three study is authored mock output, not independent ratings or measured learning benefit.",
        "No database, UI, live model, external provider or matching full-release integration was tested.",
        "Two negative-instruction failures are separate from the four included tests and are not counted as successful behaviour.",
        "The README states ownership partition rather than personal authorship; no human approval is established by file inclusion.",
    ],
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"receipt": str(OUTPUT), **result["summary"], "tests": test_results}, ensure_ascii=True, indent=2))
