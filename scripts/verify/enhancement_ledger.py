"""Append scoped enhancement observations without rewriting original task history."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconcile(gate: Path, output: Path):
    if output.exists():
        raise ValueError("Keep the prior reconciliation evidence")
    record = json.loads((gate / "software_gate.json").read_text(encoding="utf-8"))
    suite = ET.parse(gate / "pytest.xml").getroot()
    passed = set()
    for node in suite.iter("testcase"):
        if not any(node.find(kind) is not None for kind in ("failure", "error", "skipped")):
            passed.add(
                node.attrib.get("classname", "").replace(".", "/") + ".py::" + node.attrib["name"]
            )
    refs = [
        str((gate / name).relative_to(ROOT)).replace("\\", "/")
        for name in ("software_gate.json", "pytest.xml", "source_snapshot.json")
    ]
    now = datetime.now(timezone.utc).isoformat()
    checkpoint = "week08-enhancement-20260920"
    outputs = []
    review_rows = []
    for filename, key, id_key, expected in (
        ("tasks.json", "tasks", "task_id", 108),
        ("acceptance.json", "checks", "check_id", 60),
        ("ui_acceptance.json", "checks", "check_id", 12),
    ):
        path = ROOT / "docs/execution" / filename
        source = json.loads(path.read_text(encoding="utf-8"))
        original_ids = [r[id_key] for r in source[key]]
        if len(original_ids) != expected or len(set(original_ids)) != expected:
            raise ValueError("Original task/check registry identities differ")
        before = digest(path)
        for row in source[key]:
            previous_nodes = row.get("current_test_nodes", [])
            matched = sorted(set(previous_nodes) & passed)
            absent = sorted(set(previous_nodes) - passed)
            observation = {
                "checkpoint": checkpoint,
                "observed_at": now,
                "original_id": row[id_key],
                "status": "MOCK_TEST_PASSED" if matched else "IMPLEMENTED_UNVERIFIED",
                "retained_requirement_status": row["status"],
                "passed_previously_mapped_nodes": matched,
                "previously_mapped_nodes_without_current_pass": absent,
                "evidence_paths": refs
                if matched
                else ["docs/execution/week08-enhancement-20260920.md"],
                "scope": "Current software re-execution of the explicitly mapped nodes. Each original requirement retains its complete clause, historical evidence and remaining acceptance scope. Browser, real-model, source-identity and human outcomes have separate enhancement evidence.",
                "unmapped_scope": "No mapped current Python result is promoted to full requirement acceptance; frontend/manual/documentation scope is reviewed separately."
                if not matched
                else None,
                "human_review": "WAITING_EXTERNAL",
            }
            history = row.setdefault("enhancement_observations", [])
            if any(r.get("checkpoint") == checkpoint for r in history):
                raise ValueError(
                    "Preserve the existing enhancement observation; use a new dated revision"
                )
            history.append(observation)
            review_rows.append(
                (row[id_key], observation["status"], row["status"], len(matched), len(absent))
            )
        source["week08_enhancement_checkpoint"] = {
            "id": checkpoint,
            "reconciled_at": now,
            "original_ids_preserved": True,
            "project_complete": False,
            "evidence": refs,
            "software_gate_state": record.get("passed", record.get("status")),
            "scope": "Three integrated modules, frozen real automatic studies and current software/CPU/browser checks. Independent human scores remain open.",
        }
        if [r[id_key] for r in source[key]] != original_ids:
            raise AssertionError("Registry order or identity changed")
        path.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        outputs.append(
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "original_count": expected,
                "original_ids": original_ids,
                "before_sha256": before,
                "after_sha256": digest(path),
                "original_ids_preserved": True,
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "checkpoint": checkpoint,
                "recorded_at": now,
                "registries": outputs,
                "current_passed_python_nodes": len(passed),
                "evidence": refs,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Week 8 enhancement registry review",
        "",
        "Every original identifier is retained. The current software observation reports only previously mapped Python nodes rerun at this checkpoint. Complete requirement clauses and older evidence remain in the canonical JSON registries. Fresh source, CPU, HTTP and browser flows are linked in the enhancement execution record; independent human and physical-device acceptance retain their own scope.",
        "",
        "| Original ID | Current mapped software scope | Retained requirement status | Passing mapped nodes | Previously mapped nodes without current pass |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    lines.extend(
        f"| {identity} | {state} | {prior} | {matches} | {missing} |"
        for identity, state, prior, matches, missing in review_rows
    )
    (ROOT / "docs/execution/week08-enhancement-ledger.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return {
        "registries": 3,
        "original_tasks": 108,
        "original_checks": 60,
        "responsive_subchecks": 12,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.gate.resolve(), args.output.resolve())))


if __name__ == "__main__":
    main()
