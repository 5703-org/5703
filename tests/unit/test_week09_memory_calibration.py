"""Software checks for the authored offline memory cutoff protocol."""

import copy
import json

import pytest

from personalisation import memory_v2
from scripts.verify import week09_memory


def case(identity, group, split, question, expected):
    scope = "xylary flow"
    return {
        "id": identity,
        "group": group,
        "split": split,
        "question": question,
        "expected_selected": expected,
        "entry": {
            "id": f"memory-{identity}",
            "version": 1,
            "category": "preference",
            "field_key": "examples",
            "scope": scope,
            "scope_topics": memory_v2.topics(scope),
            "content": "I prefer an example for xylary flow.",
            "verification": "explicit_user_statement",
            "source_message_id": f"message-{identity}",
            "source_event_sequence": 1,
        },
    }


def catalogue():
    return {
        "version": "authored_unit_study_v1",
        "label_origin": "authored_applicability_fixture",
        "threshold_grid": [0.5, 0.85, 1.0],
        "cases": [
            case("d-positive", "dev-concept", "development", "Related hydraulic continuity?", True),
            case("d-negative", "dev-concept", "development", "Unrelated astronomy?", False),
            case("h-positive", "held-concept", "reserved", "Related hydraulic mechanics?", True),
            case("h-negative", "held-concept", "reserved", "Unrelated astronomy?", False),
        ],
    }


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda data: data["cases"][2].update(group="dev-concept"), "crosses splits"),
        (lambda data: data["cases"][2].update(id="d-positive"), "invalid"),
        (lambda data: data["cases"][2].update(expected_selected=1), "invalid"),
        (lambda data: data.update(threshold_grid=[0.5, float("nan")]), "Threshold grid"),
        (lambda data: data.update(label_origin="human"), "authored provenance"),
    ],
)
def test_freeze_rejects_invalid_or_leaking_catalogue_before_writing(tmp_path, change, match):
    data = copy.deepcopy(catalogue())
    change(data)
    path = tmp_path / "authored.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    output = tmp_path / "study"
    with pytest.raises(ValueError, match=match):
        week09_memory.freeze(output, path)
    assert not output.exists()


def test_cutoff_is_chosen_on_development_only_and_reports_held_out_counts(tmp_path, monkeypatch):
    path = tmp_path / "authored.json"
    path.write_text(json.dumps(catalogue()), encoding="utf-8")
    output = tmp_path / "study"
    week09_memory.freeze(output, path)
    seen = []

    def authored_score(question, scopes):
        seen.append(question)
        return [0.9 if "Related" in question else 0.1 for _ in scopes]

    monkeypatch.setattr(week09_memory.new, "scope_scores", authored_score)
    week09_memory.run(output)
    summary = json.loads((output / "public-summary.json").read_text())
    assert summary["selected_cutoff"] == 0.85
    assert summary["human_ratings"] == 0
    assert summary["answer_model_calls"] == 0
    assert summary["selection_counts"]["reserved"]["semantic"] == {
        "cases": 2,
        "correct_selection": 1,
        "false_selection": 0,
        "omission": 0,
        "correct_exclusion": 1,
    }
    assert "Related hydraulic mechanics?" not in seen[:2]
    assert seen
    with pytest.raises(ValueError, match="Preserve the first"):
        week09_memory.run(output)


def test_rule_false_selection_rejects_activation_but_preserves_holdout(tmp_path, monkeypatch):
    data = catalogue()
    data["cases"][1]["question"] = "Explain xylary flow."
    path = tmp_path / "authored.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    output = tmp_path / "study"
    week09_memory.freeze(output, path)
    monkeypatch.setattr(
        week09_memory.new,
        "scope_scores",
        lambda question, scopes: [0.9 if "Related" in question else 0.1 for _ in scopes],
    )
    week09_memory.run(output)
    summary = json.loads((output / "public-summary.json").read_text())
    assert summary["activation_decision"] == "rejected_development_false_selection"
    assert summary["cutoff_role"] == "diagnostic_only"
    assert summary["selection_counts"]["development"]["semantic"]["false_selection"] == 1
    assert summary["selection_counts"]["reserved"]["semantic"]["correct_selection"] == 1
    assert not (output / "experimental-policy.json").exists()
    assert (output / "diagnostic-policy-not-for-activation.json").exists()
