"""Import the supplied specification and audit original files without mutating them.

This is a one-time foundation helper. Existing task/check ledgers are protected
from replacement so subsequent evidence cannot be lost by rerunning it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_FILES: dict[str, str] = {}
STDOUT_ONLY = False


def write_text(path: Path, value: str) -> None:
    if STDOUT_ONLY:
        OUTPUT_FILES[path.name] = value
    else:
        path.write_text(value, encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    global STDOUT_ONLY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--stdout-json", action="store_true", help="Emit file contents for native shell creation when Python filesystem writes are unavailable")
    args = parser.parse_args()
    STDOUT_ONLY = args.stdout_json
    inputs = args.inputs.resolve()
    target = Path(__file__).resolve().parent
    package = inputs / "CS30-1_Full_Project_v5"
    for name in ("tasks.json", "acceptance.json", "reporting_plan.json"):
        if (target / name).exists():
            raise SystemExit(f"Refusing to replace an existing execution ledger: {name}")
    now = datetime.now(timezone.utc).isoformat()
    tasks = read_json(package / "TASKS_V5.json")
    acceptance = read_json(package / "ACCEPTANCE_V5.json")
    reporting = read_json(package / "REPORTING_PLAN_V5.json")
    order = read_json(package / "EXECUTION_ORDER_V5.json")
    rows = tasks["tasks"]
    identifiers = {row["task_id"] for row in rows}
    check_ids = {row["check_id"] for row in acceptance["checks"]}
    assert len(rows) == len(identifiers) == 108
    assert len(acceptance["checks"]) == len(check_ids) == 60
    assert check_ids == {f"AC-{n:02}" for n in range(1, 49)} | {f"HC-{n:02}" for n in range(1, 13)}
    assert set(order["task_ids"]) == identifiers and len(order["task_ids"]) == 108
    positions = {value: index for index, value in enumerate(order["task_ids"])}
    for row in rows:
        assert set(row["dependencies"]) <= identifiers
        assert set(row["acceptance_ids"]) <= check_ids
        assert all(positions[d] < positions[row["task_id"]] for d in row["dependencies"])
        row["imported_source_status"] = row["status"]
        row["status"] = "NOT_STARTED"
        row["implementation_status"] = "NOT_STARTED"
        row["verification_status"] = "NOT_RUN_FOR_V5"
        row["research_status"] = "NOT_ASSESSED"
        row["human_review_status"] = "PENDING"
        row["actual_executor"] = None
        row["actual_commands"] = []
        row["evidence_paths"] = []
        row["actual_started_at"] = None
        row["actual_completed_at"] = None
        row["lean_references"] = ["L01", "L09"]
        prefix = row["task_id"].split("-")[0]
        scopes = {
            "INT": ("Foundation, verification and release commands", "Integration", "Configurations and execution ledgers", "All module contracts and final delivery"),
            "DAT": ("Administrator corpus routes and ingestion/build CLI", "Corpus processing", "Assets, versions, processing runs, source units, chunks, releases", "Retrieval and source viewer"),
            "RET": ("Shared answer service and evaluation runner", "Retrieval and query preparation", "Release vectors and immutable retrieval/evidence snapshots", "Generation prompts and evidence viewer"),
            "GEN": ("Shared answer service through worker or offline runner", "GenerationService", "Attempts, prompt metadata and typed response/evidence snapshots", "Chat renderer and evaluation scorer"),
            "PER": ("Profile API/UI and offline matched study runner", "ProfileCompiler", "Profile revisions, per-turn snapshots and separate study items", "Main generation prompt and study reports"),
            "BE": ("Versioned API and operator CLI", "Application services and worker", "Relational entities and publication transactions", "Typed frontend, admin CLI and evaluator"),
            "FE": ("Browser routes and accessible controls", "Typed API client and feature views", "Server-owned session/job/answer/profile/corpus/experiment records", "Learner and administrator workflows"),
            "QA": ("Verification commands, scenarios and evaluator runner", "Acceptance and evaluation", "Frozen run items, private references, observations and ratings", "Technical audit and separate scientific reports"),
            "CHAT": ("Chat routes, shared answering and conversation tests", "Conversation services", "Messages, active revisions, context/summary/profile/evidence snapshots", "Real multi-turn chat and independent OpenQA protocol"),
        }
        entry, service, data, consumer = scopes[prefix]
        row["implementation_trace"] = {
            "designed_entry": entry,
            "service_boundary": service,
            "persisted_effect": data,
            "consumer": consumer,
            "checks": row["acceptance_ids"],
            "concrete_code_paths": [],
            "concrete_test_paths": [],
            "mapping_status": "DESIGNED_NOT_IMPLEMENTED",
        }
    tasks["execution_scope"] = "ENTIRE_PROJECT"
    tasks["imported_at"] = now
    tasks["source_registry_sha256"] = digest(package / "TASKS_V5.json")
    tasks["status_note"] = "Source histories preserved; no v5 task is complete at initial import."
    for check in acceptance["checks"]:
        assert set(check["task_ids"]) <= identifiers
        check.update(actual_commands=[], evidence_paths=[], executed_at=None, actual=None)
    acceptance["imported_at"] = now
    acceptance["source_registry_sha256"] = digest(package / "ACCEPTANCE_V5.json")
    for row in reporting["weekly_work_packages"]:
        assert set(row["task_ids"]) <= identifiers
    assert len(reporting["weekly_work_packages"]) == 56
    write_json(target / "tasks.json", tasks)
    write_json(target / "acceptance.json", acceptance)
    write_json(target / "reporting_plan.json", reporting)
    write_json(target / "execution_order.json", order)

    ui_requirements = [
        ("No shell overflow, overlapping prose or unreachable controls at the named widths.", ["FE-12", "QA-12"], ["AC-44"]),
        ("Resize loaded chat across widths and breakpoint edges without reload, lost draft/session/job or duplicate submission.", ["FE-04", "FE-08"], ["AC-16", "AC-43", "AC-44"]),
        ("Actual browser/text enlargement and 320 CSS-pixel reflow preserve reading and operations.", ["FE-12"], ["AC-44"]),
        ("Long text wraps or scrolls locally without clipping or page-width overflow.", ["FE-05", "FE-06", "FE-10", "FE-11"], ["AC-44"]),
        ("Keyboard and low-height/orientation cases preserve composer/transcript/Close; record unavailable physical testing.", ["FE-03", "FE-12"], ["AC-44"]),
        ("Drawers open/scroll/close, restore focus and show readable full-screen evidence on narrow screens.", ["FE-06", "FE-08"], ["AC-16", "AC-44"]),
        ("Resize during generation/failure/re-login preserves durable state; failed regeneration retains prior revision.", ["FE-04", "FE-08", "CHAT-08"], ["AC-16", "AC-43", "AC-45"]),
        ("Older-message reading is not interrupted; Jump to latest and panel closure preserve position.", ["FE-08"], ["AC-44"]),
        ("Keyboard, IME, touch and visible focus work; essential controls are not hover-only.", ["FE-03", "FE-12"], ["AC-44"]),
        ("Login/profile/corpus/experiments fit with accessible errors, required fields and pagination.", ["FE-02", "FE-07", "FE-10", "FE-11", "FE-12"], []),
        ("Sources, applied profiles, mock/live and error feedback remain correct and discoverable.", ["FE-05", "FE-06", "FE-07"], ["AC-16", "AC-37", "AC-44"]),
        ("Review screenshots with bounds, real clicks and persisted state; rerun the complete no-SciQ journey.", ["CHAT-06", "QA-12"], ["AC-37", "AC-44"]),
    ]
    ui = {"kind": "subchecks_of_existing_acceptance", "top_level_task_count_unchanged": 108, "top_level_check_count_unchanged": 60, "checks": []}
    for index, (expected, task_ids, parents) in enumerate(ui_requirements, 1):
        ui["checks"].append({"check_id": f"UI-{index:02}", "expected": expected, "task_ids": task_ids, "parent_acceptance_ids": parents, "status": "NOT_RUN", "actual": None, "actual_commands": [], "evidence_paths": []})
    write_json(target / "ui_acceptance.json", ui)

    manifest_results = []
    for line in (package / "MANIFEST_SHA256.txt").read_text(encoding="utf-8-sig").splitlines():
        expected, relative = line.split(None, 1)
        path = package / relative.strip()
        actual = digest(path) if path.is_file() else None
        manifest_results.append({"path": relative.strip(), "expected_sha256": expected, "actual_sha256": actual, "matches": actual == expected})
    generation = inputs / "sources" / "CS30-1_Sijin_Lu_Generation_Handover_2026-09-08"
    generation_manifests = {}
    for name in ("PACKAGE_MANIFEST.json", "SOURCE_MANIFEST.json"):
        records = []
        for entry in read_json(generation / name)["files"]:
            path = generation / entry["path"]
            actual = digest(path) if path.is_file() else None
            records.append({"path": entry["path"], "expected_sha256": entry["sha256"], "actual_sha256": actual, "matches": actual == entry["sha256"]})
        generation_manifests[name] = records
    inventory = []
    for path in sorted(inputs.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            inventory.append({"path": path.relative_to(inputs).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path), "classification": "derived_extraction" if "extracted" in path.parts else "supplied_source_copy", "review_status": "INVENTORIED_NOT_AUTOMATICALLY_CONTENT_APPROVED"})
    write_json(target / "source_files.json", {"generated_at": now, "source_root": "../development_inputs relative to repository parent", "files": inventory})
    audit = {"generated_at": now, "python": platform.python_version(), "scope": "Current file integrity and registry structure only; not application verification", "task_count": len(rows), "check_count": len(acceptance["checks"]), "reporting_packages": 56, "owner_counts": dict(Counter(r["accountable_owner"] for r in rows)), "dependency_dag_and_order_valid": True, "package_manifest": manifest_results, "generation_manifests": generation_manifests, "all_hashes_match": all(r["matches"] for r in manifest_results) and all(r["matches"] for values in generation_manifests.values() for r in values), "application_tests_run": False, "live_calls": 0, "human_reviews": 0}
    write_json(target / "initial_inventory_audit.json", audit)
    if not audit["all_hashes_match"]:
        raise SystemExit("At least one source manifest hash differs; inspect initial_inventory_audit.json")

    lines = ["# Owner and course-week reporting view", "", "Imported allocation is a reporting view only. No row is an actual completion, authorization gate or date deadline. Week 3 is project week 1; no project work is fabricated for weeks 1–2. Week 13 is optional real follow-up only.", "", "Canonical plan: `reporting_plan.json`; actual task state: `tasks.json`. The same implementation will be exported to `docs/delivery/by_owner/` and `docs/delivery/by_week/` during INT-10/CHAT-12/QA-14. Actual executor, completion timestamp, commands and evidence remain separate from suggested weeks.", ""]
    for row in reporting["weekly_work_packages"]:
        lines.extend([f"## Course week {row['course_week']} / project week {row['project_week']} — {row['accountable_owner']}", "", f"Tasks: {', '.join(row['task_ids'])}.", "", row["work"], "", f"Deliverables: {', '.join(row['deliverables'])}.", "", f"Acceptance: {row['acceptance']}", "", "Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.", ""])
    write_text(target / "weekly_plan.md", "\n".join(lines))
    summary = {"tasks": len(rows), "checks": len(acceptance["checks"]), "ui_subchecks": 12, "reporting_packages": 56, "source_files": len(inventory), "package_manifest_files": len(manifest_results), "generation_manifest_files": {k: len(v) for k, v in generation_manifests.items()}, "all_hashes_match": True, "task_completion_claims": 0}
    print(json.dumps({"files": OUTPUT_FILES, "summary": summary} if STDOUT_ONLY else summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
