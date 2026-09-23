"""Append current scoped observations to all 180 original registry entries."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.verify.all import ROOT, source_snapshot

CHECKPOINT = "week08-memory-v2-20260921"
RECORD = "docs/execution/week08-memory-v2-20260921.md"
REGISTRIES = (
    ("tasks.json", "tasks", "task_id", 108),
    ("acceptance.json", "checks", "check_id", 60),
    ("ui_acceptance.json", "checks", "check_id", 12),
)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def reconcile(gate: Path, output: Path, *, root: Path = ROOT, runtime_snapshot=None):
    if output.exists():
        raise ValueError("Use a new reconciliation directory")
    gate_record = json.loads((gate / "software_gate.json").read_text(encoding="utf-8"))
    if gate_record.get("status") != "passed":
        raise ValueError("Current complete software gate must pass")
    frozen = json.loads((gate / "source_snapshot.json").read_text(encoding="utf-8"))
    current = source_snapshot() if runtime_snapshot is None else runtime_snapshot
    # The software gate stores before/after maps; both bind this observation.
    if frozen.get("before") != current or frozen.get("after") != current:
        raise ValueError("Software gate does not identify the current executable sources")
    suite = ET.parse(gate / "pytest.xml").getroot()
    passed = set()
    for node in suite.iter("testcase"):
        if not any(node.find(kind) is not None for kind in ("failure", "error", "skipped")):
            passed.add(
                node.attrib.get("classname", "").replace(".", "/") + ".py::" + node.attrib["name"]
            )
    if not passed:
        raise ValueError("Gate has no passing Python tests")
    refs = [
        (gate / name).relative_to(root).as_posix()
        for name in ("software_gate.json", "pytest.xml", "source_snapshot.json")
    ]
    now = datetime.now(timezone.utc).isoformat()
    prepared, rows = [], []
    for filename, key, id_key, count in REGISTRIES:
        path = root / "docs/execution" / filename
        before = path.read_bytes()
        value = json.loads(before)
        items = value[key]
        identities = [item[id_key] for item in items]
        if len(identities) != count or len(set(identities)) != count:
            raise ValueError("Original registry count or identity differs")
        for item in items:
            history = item.setdefault("memory_v2_observations", [])
            if any(entry.get("checkpoint") == CHECKPOINT for entry in history):
                raise ValueError("This dated observation already exists")
            mapped = set(item.get("current_test_nodes", []))
            matches, missing = sorted(mapped & passed), sorted(mapped - passed)
            observation = {
                "checkpoint": CHECKPOINT,
                "observed_at": now,
                "original_id": item[id_key],
                "status": "MOCK_TEST_PASSED" if matches else "IMPLEMENTED_UNVERIFIED",
                "retained_requirement_status": item["status"],
                "passed_previously_mapped_nodes": matches,
                "previously_mapped_nodes_without_current_pass": missing,
                "evidence_paths": refs if matches else [RECORD],
                "scope": "Current software execution of explicitly mapped Python checks. Full requirement clauses and prior observations remain unchanged. Current real-source, model, CPU, browser and study evidence has its own scope in the implementation record.",
                "remaining_verification": "Full-clause acceptance requires the matching runtime, semantic, device and human evidence; a passing mapped test alone does not establish it.",
            }
            history.append(observation)
            rows.append(
                (item[id_key], observation["status"], item["status"], len(matches), len(missing))
            )
        value["week08_memory_v2_checkpoint"] = {
            "id": CHECKPOINT,
            "reconciled_at": now,
            "original_ids_preserved": True,
            "evidence": refs,
            "implementation_record": RECORD,
            "scope": "Current software observations appended to all original entries; research and human review retain separate evidence.",
        }
        if [item[id_key] for item in items] != identities:
            raise AssertionError("Original identities changed")
        content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        prepared.append((path, before, content, identities))
    # Validate every registry before any mutation, and preserve exact originals.
    output.mkdir(parents=True, exist_ok=False)
    (output / "registry-before").mkdir()
    records = []
    for path, before, content, identities in prepared:
        (output / "registry-before" / path.name).write_bytes(before)
        path.write_bytes(content)
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "original_count": len(identities),
                "original_ids": identities,
                "before_sha256": sha(before),
                "after_sha256": sha(content),
            }
        )
    summary = {
        "checkpoint": CHECKPOINT,
        "recorded_at": now,
        "registries": records,
        "current_passed_python_nodes": len(passed),
        "evidence": refs,
        "tasks": 108,
        "acceptance_checks": 60,
        "responsive_subchecks": 12,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Week 8 Memory V2 original registry review",
        "",
        "All original identifiers and requirement text remain intact. Each current observation covers only its mapped software checks. The current implementation record links the separate real-source, answer, memory, browser and installation evidence. Human review and physical-device acceptance retain their recorded scope.",
        "",
        "| Original ID | Current mapped software scope | Retained requirement status | Passing nodes | Missing current pass |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    lines.extend(
        f"| {i} | {state} | {prior} | {ok} | {missing} |" for i, state, prior, ok, missing in rows
    )
    (root / "docs/execution/week08-memory-v2-ledger.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return {
        k: summary[k]
        for k in (
            "tasks",
            "acceptance_checks",
            "responsive_subchecks",
            "current_passed_python_nodes",
        )
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.gate.resolve(), args.output.resolve())))


if __name__ == "__main__":
    main()
