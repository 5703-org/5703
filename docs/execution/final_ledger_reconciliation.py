"""Verify preserved original scope and current evidence without running application tests."""

import ast
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT.parent / "development_inputs/CS30-1_Full_Project_v5"
OUTPUT = ROOT / "evidence/source_audit/final-ledger-reconciliation.json"
STATES = {"NOT_IMPLEMENTED", "IMPLEMENTED_UNVERIFIED", "MOCK_TEST_PASSED", "REAL_FLOW_VERIFIED", "WAITING_EXTERNAL"}


def read(path):
    return json.loads(path.read_text("utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output
    if output.exists():
        raise RuntimeError("Preserve previous audit results; choose a new checkpoint path")
    source_tasks = read(INPUT / "TASKS_V5.json")["tasks"]
    source_checks = read(INPUT / "ACCEPTANCE_V5.json")["checks"]
    tasks = read(ROOT / "docs/execution/tasks.json")["tasks"]
    checks = read(ROOT / "docs/execution/acceptance.json")["checks"]
    ui = read(ROOT / "docs/execution/ui_acceptance.json")["checks"]
    assert len(tasks) == len({r["task_id"] for r in tasks}) == 108
    assert len(checks) == len({r["check_id"] for r in checks}) == 60
    assert len(ui) == len({r["check_id"] for r in ui}) == 12
    original_tasks = {r["task_id"]: r for r in source_tasks}
    original_checks = {r["check_id"]: r for r in source_checks}
    assert set(original_tasks) == {r["task_id"] for r in tasks}
    assert set(original_checks) == {r["check_id"] for r in checks}
    for row in tasks:
        for key in ("implementation", "dependencies", "acceptance_ids", "local_acceptance", "artifact_dependencies", "accountable_owner", "reference_execution_order"):
            assert row[key] == original_tasks[row["task_id"]][key], (row["task_id"], key)
    for row in checks:
        for key in ("expected", "task_ids"):
            assert row[key] == original_checks[row["check_id"]][key], (row["check_id"], key)

    # These twelve IDs were the initial mapping of the supplied responsive MD,
    # not an invented extension to the original 108/60 top-level scope.
    initializer = ROOT / "docs/execution/initialize_ledgers.py"
    tree = ast.parse(initializer.read_text("utf-8"))
    assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ui_requirements" for t in n.targets))
    original_ui = ast.literal_eval(assignment.value)
    assert [r["check_id"] for r in ui] == [f"UI-{n:02}" for n in range(1, 13)]
    for row, (expected, task_ids, parents) in zip(ui, original_ui, strict=True):
        assert (row["expected"], row["task_ids"], row["parent_acceptance_ids"]) == (expected, task_ids, parents)

    order = read(ROOT / "docs/execution/execution_order.json")["task_ids"]
    positions = {value: index for index, value in enumerate(order)}
    assert len(order) == 108 and set(order) == set(original_tasks)
    for row in tasks:
        assert all(positions[d] < positions[row["task_id"]] for d in row["dependencies"])

    gate_path = ROOT / "evidence/final/software_gate.json"
    gate = read(gate_path)
    assert gate["status"] == "passed" and gate["source_files_unchanged"]
    sys.path.insert(0, str(ROOT))
    from scripts.verify.all import source_snapshot
    saved_snapshot = read(ROOT / gate["source_snapshot"])
    assert source_snapshot() == saved_snapshot["after"], "Current executable files differ from the final gate"
    cases = list(ET.parse(ROOT / "evidence/final/pytest.xml").getroot().iter("testcase"))
    nodes = {r.attrib["classname"] + "::" + r.attrib["name"] for r in cases if not any(r.find(tag) is not None for tag in ("failure", "error", "skipped"))}

    path_index = {}
    observations = []
    for group, rows, identity in (("task", tasks, "task_id"), ("acceptance", checks, "check_id"), ("responsive", ui, "check_id")):
        for row in rows:
            assert row["status"] in STATES, (row[identity], row["status"])
            paths = set(row.get("evidence_paths", []))
            trace = row.get("implementation_trace", {})
            paths.update(trace.get("concrete_code_paths", []))
            paths.update(trace.get("concrete_test_paths", []))
            assert paths, "No current evidence path: " + row[identity]
            missing = [p for p in paths if not (ROOT / p).exists()]
            assert not missing, (row[identity], missing)
            for relative in sorted(paths):
                path = ROOT / relative
                path_index[relative] = {"kind": "file" if path.is_file() else "directory", "sha256": digest(path) if path.is_file() else None}
            cited_nodes = row.get("current_test_nodes", row.get("test_nodes", []))
            # Some acceptance rows preserve an exact pytest path::name spelling.
            canonical_nodes = set()
            for node in cited_nodes:
                module, separator, test_name = node.partition("::")
                module = module.removesuffix(".py").replace("/", ".").replace("\\", ".")
                canonical_nodes.add(module + separator + test_name)
            resolved_nodes = set()
            for cited in canonical_nodes:
                matches = {node for node in nodes if node == cited or node.split("[")[0] == cited}
                assert matches, (row[identity], cited)
                resolved_nodes.update(matches)
            canonical_nodes = resolved_nodes
            observations.append({"id": row[identity], "kind": group, "status": row["status"], "completion_claim": row.get("completion_claim", False), "evidence_paths": sorted(paths), "passing_current_test_nodes": sorted(canonical_nodes), "remaining_scope": row.get("remaining_scope", "See the recorded responsive observation and explicit device limits.")})

    corpus_path = ROOT / "evidence/openstax/corpus-report.json"
    corpus = read(corpus_path)
    assert corpus["release_id"] == "4f11bd70-a486-4d16-b216-78cfe499530a"
    counts = [b["database_vectors"]["vectors"] for b in corpus["books"]]
    assert sorted(counts) == sorted([3281, 3534, 2373, 1406])
    source_manifest = read(ROOT / "evidence/source_audit/source_read_manifest.json")
    for entry in source_manifest["documents"] + source_manifest["visual_sources"]:
        assert digest(Path(entry["path"])) == entry["sha256"], entry["path"]
    result = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "audit_kind": "Original-scope and current-artifact reconciliation; no application tests rerun or historical results relabelled.",
        "task_count": 108, "acceptance_count": 60, "responsive_subcheck_count": 12,
        "original_id_sets_preserved": True, "original_requirement_text_and_dependencies_preserved": True,
        "responsive_original_mapping_preserved": True, "dependencies_acyclic": True,
        "source_files_unchanged": True,
        "source_registry_sha256": {p.name: digest(p) for p in [INPUT / "TASKS_V5.json", INPUT / "ACCEPTANCE_V5.json"]},
        "source_read_manifest": "evidence/source_audit/source_read_manifest.json",
        "original_architecture": {"file": "development_inputs/sources/COMP5703/CS30-1_Project_Framework_and_Delivery_Workflow.pdf", "figure": 1, "physical_page": 1, "printed_page": 1, "actual_visual_evidence": "evidence/source_audit/original-framework-page-1.png", "module_and_connection_audit": "docs/execution/source-architecture-audit.md"},
        "historical_first_pass": "evidence/source_audit/ledger_reconciliation.json",
        "canonical_ledger_sha256": {name: digest(ROOT / "docs/execution" / name) for name in ("tasks.json", "acceptance.json", "ui_acceptance.json")},
        "software_gate": {"path": "evidence/final/software_gate.json", "sha256": digest(gate_path), "executed_at": gate["executed_at"], "passing_python_tests": len(nodes), "source_files_unchanged": True},
        "current_corpus": {"release_id": corpus["release_id"], "parser_revision": corpus["parser_revision"], "books": 4, "physical_pages": 4638, "real_vectors": sum(counts), "dimension": 384, "report": "evidence/openstax/corpus-report.json", "sha256": digest(corpus_path), "evidence_directory": corpus["evidence_directory"]},
        "answering_mode": "mock",
        "real_answer_quality_validated": False, "independent_human_acceptance_complete": False,
        "status_counts": {"tasks": dict(Counter(r["status"] for r in tasks)), "acceptance": dict(Counter(r["status"] for r in checks)), "responsive": dict(Counter(r["status"] for r in ui))},
        "no_overall_completion_percentage": True,
        "cited_existing_paths": path_index,
        "observations": observations,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(json.dumps({"status": "passed", "tasks": 108, "acceptance": 60, "responsive": 12, "paths": len(path_index), "current_python_tests": len(nodes)}))


if __name__ == "__main__":
    main()
