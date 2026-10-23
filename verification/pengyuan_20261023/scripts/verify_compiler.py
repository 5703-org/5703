"""Offline compiler-only checks for presentation evidence.

Publication adaptation (23 October 2026): input/output paths are CLI arguments;
the original checks are retained. Requires the original package snapshots.
Historical receipts are archived separately; reruns must use a new output path.

This is a bounded probe, not an application integration or learning study.
It loads the current owner compiler with the matching current complete-package contracts.
No source code is modified and no LLM, database or network calls are made.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
from datetime import datetime, timezone

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--owner", type=Path, required=True, help="19 October owner learning-assistant directory, including RELEASE_MANIFEST.json")
parser.add_argument("--complete", type=Path, required=True, help="19 October complete learning-assistant directory, including PACKAGE_MANIFEST.json")
parser.add_argument("--output", type=Path, required=True, help="New local JSON path; existing files will not be overwritten")
args = parser.parse_args()
OWNER = args.owner.resolve()
COMPLETE = args.complete.resolve()
OUTPUT = args.output.resolve()
if OUTPUT.exists():
    parser.error("Output already exists; choose a new local file to preserve archived evidence.")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def forbid_network(*args, **kwargs):
    raise RuntimeError("Network access is prohibited in this offline probe")


socket.create_connection = forbid_network
socket.socket.connect = forbid_network
socket.socket.connect_ex = forbid_network
sys.dont_write_bytecode = True
sys.path.insert(0, str(COMPLETE))

compiler_path = OWNER / "personalisation/compiler.py"
spec = importlib.util.spec_from_file_location("current_owner_compiler", compiler_path)
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)

owner_manifest = json.loads((OWNER / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
complete_manifest = json.loads((COMPLETE / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
owner_files = {entry["path"]: entry for entry in owner_manifest["files"]}
complete_files = {entry["path"]: entry for entry in complete_manifest["files"]}
dependency_path = COMPLETE / "contracts/models.py"
compiler_hash = sha256(compiler_path)
dependency_hash = sha256(dependency_path)
owner_to_complete = []
for entry in owner_manifest["files"]:
    if entry["kind"] != "current_assigned_source":
        continue
    path = entry["path"]
    owner_hash = sha256(OWNER / path)
    complete_hash = sha256(COMPLETE / path)
    owner_to_complete.append({
        "path": path,
        "owner_sha256": owner_hash,
        "complete_sha256": complete_hash,
        "matches_owner_manifest": owner_hash == entry["sha256"],
        "matches_complete_manifest": complete_hash == complete_files[path]["sha256"],
        "owner_and_complete_identical": owner_hash == complete_hash,
    })

provenance = {
    "compiler": {
        "path": str(compiler_path),
        "sha256": compiler_hash,
        "owner_manifest_sha256": owner_files["personalisation/compiler.py"]["sha256"],
        "matches_owner_manifest": compiler_hash == owner_files["personalisation/compiler.py"]["sha256"],
        "matches_current_complete_package_compiler": compiler_hash == sha256(COMPLETE / "personalisation/compiler.py"),
    },
    "contracts_dependency": {
        "path": str(dependency_path),
        "sha256": dependency_hash,
        "current_complete_manifest_sha256": complete_files["contracts/models.py"]["sha256"],
        "matches_current_complete_manifest": dependency_hash == complete_files["contracts/models.py"]["sha256"],
        "present_in_owner_package": "contracts/models.py" in owner_files,
        "dependency_boundary": "Taken from the matching CS30-1_Current_20261019 complete package; the owner archive does not contain contracts/models.py. This does not verify full-application deployment.",
    },
    "current_complete_release_id": complete_manifest["release_id"],
    "owner_to_current_complete_comparison": owner_to_complete,
}
assert provenance["compiler"]["matches_owner_manifest"]
assert provenance["compiler"]["matches_current_complete_package_compiler"]
assert provenance["contracts_dependency"]["matches_current_complete_manifest"]
assert len(owner_to_complete) == 13
assert all(row["matches_owner_manifest"] and row["matches_complete_manifest"] and row["owner_and_complete_identical"] for row in owner_to_complete)

positive_controls = []
for level in ("beginner", "intermediate", "advanced"):
    for style in ("concise", "detailed", "socratic"):
        supplied = {"level": level, "style": style, "topics": ["biology"], "version": 2}
        first = compiler.compile_profile(supplied)
        repeated = compiler.compile_profile(supplied)
        checks = {
            "normalizes_profile": first["profile"] == {**supplied, "language": "en"},
            "includes_level_rule": compiler.LEVEL_RULES[level] in first["policy"],
            "includes_style_rule": compiler.STYLE_RULES[style] in first["policy"],
            "includes_evidence_guardrail": "presentation preferences never override correctness" in first["policy"],
            "preserves_revision": first["source_version"] == 2,
            "repeated_output_identical": first == repeated,
            "hash_is_sha256": len(first["policy_hash"]) == 64,
        }
        positive_controls.append({
            "case": f"{level}/{style}",
            "passed": all(checks.values()),
            "checks": checks,
            "normalized_profile": first["profile"],
            "policy_hash": first["policy_hash"],
        })

detail_message = "Please explain this in detail."
detail = compiler.compile_profile({"level": "intermediate", "style": "concise"}, turn_message=detail_message)
positive_controls.append({
    "case": "explicit_current_turn_detail_request",
    "input": detail_message,
    "passed": detail["turn_override"] == {"style": "detailed", "reason": "explicit_detail"}
        and "For this response only" in detail["policy"],
    "observed_override": detail["turn_override"],
})

off = compiler.compile_profile({"level": "advanced", "style": "detailed"}, use_profile=False)
positive_controls.append({
    "case": "saved_profile_off_without_turn_override",
    "passed": off["profile"] is None and off["policy"] == "" and off["turn_override"] is None,
    "observed": {key: off[key] for key in ("use_profile", "profile", "policy", "turn_override")},
})

known_limitations = []
for message in (
    "Do not simplify; keep advanced terminology.",
    "Please do not give more detail.",
):
    observed = compiler.turn_override(message)
    known_limitations.append({
        "input": message,
        "expected_behaviour": "Do not create a positive override for the explicitly negated request.",
        "expected_override": None,
        "observed_override": observed,
        "mismatch_reproduced": observed is not None,
        "interpretation": "Keyword matching ignores negation in this example; this is a limitation, not a successful adaptation.",
    })

result = {
    "schema": "personalisation_presentation_compiler_probe_v1",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "command": str(Path(__file__).resolve()),
    "python_executable": sys.executable,
    "scope": "Fresh software-only compiler probe with current owner compiler and the matching current complete-package contracts.",
    "no_llm_calls": True,
    "no_database_calls": True,
    "network_connections_blocked": True,
    "project_sources_modified": False,
    "provenance": provenance,
    "positive_controls": positive_controls,
    "known_limitations": known_limitations,
    "summary": {
        "assigned_source_files_compared_to_current_complete": len(owner_to_complete),
        "assigned_source_files_identical": sum(row["owner_and_complete_identical"] for row in owner_to_complete),
        "profile_combinations_checked": 9,
        "positive_controls_checked": len(positive_controls),
        "positive_controls_passed": sum(item["passed"] for item in positive_controls),
        "negation_examples_checked_separately": len(known_limitations),
        "negation_mismatches_reproduced": sum(item["mismatch_reproduced"] for item in known_limitations),
        "aggregate_pass_percentage": None,
    },
    "claim_boundary": [
        "Checks configuration normalization, fixed rule inclusion and output repeatability only.",
        "Does not test generated answer quality, student understanding or learning gains.",
        "Does not verify database persistence, end-to-end UI or latest full-application deployment.",
        "Known negation mismatches are reported separately, not counted as passing behaviour.",
    ],
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence_file": str(OUTPUT), **result["summary"]}, ensure_ascii=True, indent=2))
