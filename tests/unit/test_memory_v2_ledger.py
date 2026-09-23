"""Current registry reconciliation preserves every original requirement and ID."""

import json

import pytest

from scripts.verify.memory_v2_ledger import REGISTRIES, reconcile


def setup(root):
    base = root / "docs/execution"
    base.mkdir(parents=True)
    originals = {}
    for filename, key, id_key, count in REGISTRIES:
        value = {
            key: [
                {
                    id_key: f"{key}-{i}",
                    "status": "WAITING_EXTERNAL",
                    "expected": f"Original requirement {i}",
                    "current_test_nodes": ["tests/unit/test_fixture.py::test_case"]
                    if i == 0
                    else [],
                    "prior_observations": [{"scope": "Retained dated proof"}],
                }
                for i in range(count)
            ]
        }
        path = base / filename
        path.write_text(json.dumps(value), encoding="utf-8")
        originals[filename] = path.read_bytes()
    gate = root / "evidence/gate"
    gate.mkdir(parents=True)
    (gate / "software_gate.json").write_text('{"status":"passed"}', encoding="utf-8")
    (gate / "source_snapshot.json").write_text(
        json.dumps({"before": {"source": "hash"}, "after": {"source": "hash"}}), encoding="utf-8"
    )
    (gate / "pytest.xml").write_text(
        '<testsuites><testsuite><testcase classname="tests.unit.test_fixture" name="test_case"/></testsuite></testsuites>',
        encoding="utf-8",
    )
    return gate, originals


def test_all_original_entries_and_exact_history_survive(tmp_path):
    gate, originals = setup(tmp_path)
    output = tmp_path / "evidence/ledger"
    result = reconcile(gate, output, root=tmp_path, runtime_snapshot={"source": "hash"})
    assert result == {
        "tasks": 108,
        "acceptance_checks": 60,
        "responsive_subchecks": 12,
        "current_passed_python_nodes": 1,
    }
    for filename, key, id_key, count in REGISTRIES:
        current = json.loads((tmp_path / "docs/execution" / filename).read_text(encoding="utf-8"))[
            key
        ]
        previous = json.loads(originals[filename])[key]
        assert len(current) == count
        for before, after in zip(previous, current):
            assert all(after[k] == v for k, v in before.items())
            assert len(after["memory_v2_observations"]) == 1
        assert current[0]["memory_v2_observations"][0]["status"] == "MOCK_TEST_PASSED"
        assert current[1]["memory_v2_observations"][0]["status"] == "IMPLEMENTED_UNVERIFIED"
        assert (output / "registry-before" / filename).read_bytes() == originals[filename]
    with pytest.raises(ValueError, match="already exists"):
        reconcile(
            gate, tmp_path / "evidence/again", root=tmp_path, runtime_snapshot={"source": "hash"}
        )


def test_invalid_later_registry_or_changed_source_never_partially_writes(tmp_path):
    gate, originals = setup(tmp_path)
    output = tmp_path / "evidence/ledger"
    with pytest.raises(ValueError, match="current executable"):
        reconcile(gate, output, root=tmp_path, runtime_snapshot={"source": "changed"})
    path = tmp_path / "docs/execution/ui_acceptance.json"
    path.write_text('{"checks":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="registry count"):
        reconcile(gate, output, root=tmp_path, runtime_snapshot={"source": "hash"})
    assert not output.exists()
    assert (tmp_path / "docs/execution/tasks.json").read_bytes() == originals["tasks.json"]
    assert (tmp_path / "docs/execution/acceptance.json").read_bytes() == originals[
        "acceptance.json"
    ]
