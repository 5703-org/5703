"""Study boundaries for a paired, label-separated memory selector experiment."""

import json

import pytest

from evaluation.week09_continuation import memory_formal
from personalisation import memory_v2


def _entry(identity, scope="photosynthesis"):
    return {
        "id": identity,
        "version": 1,
        "category": "preference",
        "field_key": "examples",
        "scope": scope,
        "scope_topics": memory_v2.topics(scope),
        "content": f"When studying {scope}, please include an example.",
        "verification": "user_explicit",
        "source_message_id": f"source-{identity}",
        "source_event_sequence": 1,
        "expires_at": None,
    }


def _catalogue():
    return {
        "schema": memory_formal.VERSION,
        "label_provenance": "program_derived",
        "cases": [
            {
                "id": "pilot-one",
                "concept_group": "photosynthesis_new",
                "split": "pilot",
                "question": "Explain photosynthesis.",
                "entries": [_entry("pilot-memory")],
                "profile": {"profile": {"style": "concise"}},
                "expected_memory_ids": ["pilot-memory"],
                "forbidden_memory_ids": [],
            },
            {
                "id": "reserved-one",
                "concept_group": "ionic_bonding_new",
                "split": "reserved",
                "question": "Explain ionic bonding.",
                "entries": [_entry("reserved-memory")],
                "profile": {"profile": {"style": "concise"}},
                "expected_memory_ids": [],
                "forbidden_memory_ids": ["reserved-memory"],
            },
        ],
    }


def _freeze(tmp_path, catalogue=None):
    source = tmp_path / "cases.json"
    source.write_text(json.dumps(catalogue or _catalogue()), encoding="utf-8")
    prior = tmp_path / "prior.json"
    prior.write_text(json.dumps({"cases": [{"group": "previous_concept"}]}), encoding="utf-8")
    folder = tmp_path / "study"
    memory_formal.freeze(source, folder, prior_paths=(prior,))
    return folder


def test_private_labels_do_not_enter_runner_tasks_and_reserved_requires_pilot(tmp_path):
    folder = _freeze(tmp_path)
    manifest = memory_formal.read(folder / "manifest.json")
    assert "expected_memory_ids" not in manifest["tasks"]["pilot-one"]
    assert "forbidden_memory_ids" not in manifest["tasks"]["pilot-one"]
    with pytest.raises(FileNotFoundError):
        memory_formal.run(folder, split="reserved")
    assert memory_formal.run(folder, split="pilot")["total_terminal"] == 2
    assert memory_formal.pilot_decision(folder)["ready_for_reserved"] is True
    assert memory_formal.run(folder, split="reserved")["total_terminal"] == 2
    summary = memory_formal.summarize(folder)
    assert summary["paired"]["pilot"]["unchanged_exact_selection"] == 1
    assert summary["selection"]["reserved"]["previous_v2"]["correct_exclusion"] == 1
    assert summary["selection"]["reserved"]["candidate_v3_rules"]["correct_exclusion"] == 1
    assert summary["answer_preference_application"] is None


def test_prior_group_overlap_and_incomplete_label_partition_fail_before_freeze(tmp_path):
    catalogue = _catalogue()
    catalogue["cases"][0]["concept_group"] = "previous_concept"
    source = tmp_path / "cases.json"
    source.write_text(json.dumps(catalogue), encoding="utf-8")
    prior = tmp_path / "prior.json"
    prior.write_text(json.dumps({"cases": [{"group": "previous_concept"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="overlap"):
        memory_formal.freeze(source, tmp_path / "study", prior_paths=(prior,))
    assert not (tmp_path / "study").exists()

    catalogue["cases"][0]["concept_group"] = "photosynthesis_new"
    catalogue["cases"][0]["expected_memory_ids"] = []
    source.write_text(json.dumps(catalogue), encoding="utf-8")
    with pytest.raises(ValueError, match="partition"):
        memory_formal.freeze(source, tmp_path / "study", prior_paths=(prior,))


def test_freeze_detects_private_label_tamper(tmp_path):
    folder = _freeze(tmp_path)
    labels = memory_formal.read(folder / "private-labels.json")
    labels["pilot-one"]["expected_memory_ids"] = []
    (folder / "private-labels.json").write_text(json.dumps(labels), encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen memory study input changed"):
        memory_formal.run(folder, split="pilot")


def test_current_instruction_removes_saved_preference_in_both_arms():
    task = {
        "question": "Explain photosynthesis. For this answer, use no examples.",
        "entries": [_entry("saved-example")],
        "profile": {"profile": {}},
    }
    for arm in memory_formal.ARMS:
        observation = memory_formal.select(task, arm)
        assert observation["selected_memory_ids"] == []
        assert observation["answer_preference_application"] is None
