"""Denominator and boundary checks for the seven-family receipt audit."""

import json

import pytest

from scripts.verify import week09_family_scope as scope


def fixture_files(tmp_path):
    pilot = {
        "scheduled_outcomes": 7,
        "terminal_outcomes": 7,
        "human_ratings": 0,
        "families": {
            family: {
                "candidate" if family != "joint_tutoring" else "A": {"planned": 1, "terminal": 1}
            }
            for family in scope.FAMILIES
        },
    }
    formal = {
        "scheduled_outcomes": 2,
        "terminal_outcomes": 2,
        "study_scope": "conditional_automatic",
        "human_review": {"human_ratings": 0},
        "family_arm_results": {
            "textbook_qa": {"candidate": {"planned": 1, "terminal": 1}},
            "joint_tutoring": {"A": {"planned": 1, "terminal": 1}},
        },
    }
    memory = {
        "selection_counts": {"development": {}, "reserved": {}},
        "label_origin": "authored_applicability_fixture",
        "activation_decision": "rejected_development_false_selection",
        "real_cpu_e5_batches": 23,
        "answer_model_calls": 0,
        "human_ratings": 0,
    }
    paths = [tmp_path / name for name in ("pilot.json", "formal.json", "memory.json")]
    for path, data in zip(paths, (pilot, formal, memory), strict=True):
        path.write_text(json.dumps(data), encoding="utf-8")
    return paths


def test_audit_preserves_seven_pilot_and_two_formal_denominators(tmp_path):
    paths = fixture_files(tmp_path)
    result = scope.audit(*paths)
    assert result["pilot"]["scheduled"] == 7
    assert result["formal"]["scheduled"] == 2
    assert len(result["formal"]["families_without_formal_outcomes"]) == 5
    assert result["memory_selector_addendum"]["not_a_formal_family_result"] is True
    assert result["formal"]["human_ratings"] == 0


def test_audit_rejects_changed_denominator(tmp_path):
    paths = fixture_files(tmp_path)
    pilot = json.loads(paths[0].read_text())
    pilot["scheduled_outcomes"] = 8
    paths[0].write_text(json.dumps(pilot), encoding="utf-8")
    with pytest.raises(ValueError, match="schedule"):
        scope.audit(*paths)


def test_audit_rejects_pilot_human_boundary_change(tmp_path):
    paths = fixture_files(tmp_path)
    pilot = json.loads(paths[0].read_text())
    pilot["human_ratings"] = 1
    paths[0].write_text(json.dumps(pilot), encoding="utf-8")
    with pytest.raises(ValueError, match="human-score"):
        scope.audit(*paths)
