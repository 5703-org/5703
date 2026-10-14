"""Typed public practice authoring, persistence and per-step tutor projection."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from contracts.study import PracticeDraft, PracticeOut
from generation.selection_task_contract import bind_selection_task
from test_selection_task_contract import (
    S11_GOAL,
    S11_SOURCE,
    G01_GOAL,
    G01_SOURCE,
    annotation,
    digest,
    evidence,
    inventory,
    plan,
)

PROBLEM = (
    "An ideal gas initially has pressure 100 kPa and volume 2 L. Its volume "
    "changes to 4 L at constant temperature and fixed amount of gas."
)
PRIVATE_ANSWER = "Private grading fixture only; never part of public task metadata."


def draft_payload(*, metadata=True):
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    payload = {
        "title": "Public selection task",
        "kind": "step",
        "prompt": PROBLEM,
        "concepts": ["relation selection"],
        "conditions": ["Fixed gas amount.", "Constant temperature."],
        "source": {
            "release_id": "public-release",
            "document_id": "public-document",
            "processing_id": "public-processing",
            "source_unit_id": "public-unit",
            "text_hash": digest(S11_SOURCE),
        },
        "rubric": {
            "steps": [{"id": "step-1", "prompt": S11_GOAL, "acceptable_answers": [PRIVATE_ANSWER]}],
            "explanation": PRIVATE_ANSWER,
        },
    }
    if metadata:
        payload.update(selection_task=value, selection_candidates=inventory(value))
    return payload


def visible_progress(step=1):
    return {
        "current_step": step,
        "current_step_prompt": S11_GOAL if step == 1 else G01_GOAL,
        "current_step_response_kind": "text",
        "expected_unit": None,
        "state": "awaiting_attempt",
        "help_level": 1,
        "hints": [],
        "full_explanation": None,
        "attempts": [],
    }


def test_actual_typed_draft_create_item_public_out_snapshot_and_binding(monkeypatch):
    from app.modules.learning_product import service, tutoring

    body = PracticeDraft.model_validate(draft_payload())
    actor = SimpleNamespace(id="public-author", workspace_id="public-workspace")
    checked_sources = []
    monkeypatch.setattr(service, "lock_owner", lambda db, owner: owner)
    monkeypatch.setattr(
        service.library,
        "validate_locator",
        lambda db, owner, source: checked_sources.append(source),
    )

    class FakeDB:
        def __init__(self):
            self.items = []

        def add(self, row):
            self.items.append(row)

        def flush(self):
            for row in self.items:
                row.id = "public-item"
                row.validation = {"status": "pending"}
                row.state = "draft"
                row.version = 1

    db = FakeDB()
    created = service.create_item(db, actor, body)
    public = PracticeOut.model_validate(created["item"])
    assert checked_sources == [body.source]
    assert public.selection_task == body.selection_task
    assert public.selection_candidates == body.selection_candidates
    assert PRIVATE_ANSWER not in public.model_dump_json()
    assert "rubric" not in db.items[0].public_payload
    monkeypatch.setattr(service, "progress_out", lambda *args: visible_progress())
    snapshot = tutoring.snapshot(
        db, actor, db.items[0], SimpleNamespace(id="public-progress", version=1)
    )
    assert snapshot["selection_task"] == body.selection_task.model_dump()
    assert snapshot["selection_candidates"] == body.selection_candidates.model_dump()
    assert PRIVATE_ANSWER not in str(snapshot)
    frozen = bind_selection_task(
        "Help with this step.",
        {"practice_context": snapshot},
        [evidence(S11_SOURCE)],
        plan(S11_GOAL),
    )
    assert frozen["candidate_presence"] == "supplied"
    assert frozen["candidate_presence_origin"] == "canonical_public_candidate_inventory"
    assert frozen["assessment_boundary"]["answer_key_used"] is False


def test_legacy_draft_optional_metadata_does_not_change_public_payload_or_fingerprint_input():
    original = draft_payload(metadata=False)
    legacy = PracticeDraft.model_validate(original)
    explicit_none = PracticeDraft.model_validate(
        {**original, "selection_task": None, "selection_candidates": None}
    )
    assert legacy.selection_task is None and legacy.selection_candidates is None
    assert legacy.model_dump() == explicit_none.model_dump()
    assert "selection_task" not in legacy.model_dump()
    assert "selection_candidates" not in legacy.model_dump()
    public = legacy.model_dump(exclude={"source", "rubric", "previous_item_id"})
    assert "selection_task" not in public and "selection_candidates" not in public


@pytest.mark.parametrize(
    "change",
    [
        "annotation_absent",
        "inventory_missing",
        "inventory_goal",
        "source_extra_gold",
        "typed_boolean_step",
    ],
)
def test_real_practice_draft_rejects_bad_public_metadata_before_persistence(change):
    value = draft_payload()
    if change == "annotation_absent":
        value["selection_task"]["candidate_presence"] = "absent"
        value["selection_task"]["candidate_refs"] = []
    elif change == "inventory_missing":
        del value["selection_candidates"]
    elif change == "inventory_goal":
        value["selection_candidates"]["task_ref"]["exact_quote"] = G01_GOAL
        value["selection_candidates"]["task_ref"]["end"] = len(G01_GOAL)
    elif change == "source_extra_gold":
        value["selection_candidates"]["candidate_refs"][0]["correct_answer"] = PRIVATE_ANSWER
    else:
        value["selection_candidates"]["current_step"] = True
    with pytest.raises(ValidationError):
        PracticeDraft.model_validate(value)


def test_real_practice_draft_cannot_make_g01_general_principle_a_candidate():
    value = draft_payload()
    value["rubric"]["steps"][0]["prompt"] = G01_GOAL
    absent = annotation(G01_GOAL, supplied=False)
    value["selection_candidates"] = inventory(absent)
    value["selection_task"] = annotation(G01_GOAL, supplied=True, source=G01_SOURCE)
    with pytest.raises(ValidationError, match="SELECTION_TASK_INVENTORY_MISMATCH"):
        PracticeDraft.model_validate(value)


def test_real_practice_draft_nonempty_public_options_conflict_with_empty_inventory():
    value = draft_payload()
    absent = annotation(S11_GOAL, supplied=False)
    value.update(selection_task=absent, selection_candidates=inventory(absent))
    value["options"] = [{"id": "public-option", "text": "Already supplied candidate."}]
    with pytest.raises(ValidationError, match="SELECTION_TASK_INVENTORY_OPTIONS_CONFLICT"):
        PracticeDraft.model_validate(value)


def test_real_practice_draft_full_step_anchor_is_checked_against_visible_prompt():
    value = draft_payload()
    value["rubric"]["steps"][0]["prompt"] = "A different publicly visible current step."
    with pytest.raises(ValidationError, match="SELECTION_TASK_ANCHOR_MISMATCH"):
        PracticeDraft.model_validate(value)


def test_step_advance_keeps_prior_step_metadata_out_of_current_snapshot(monkeypatch):
    from app.modules.learning_product import service, tutoring

    value = draft_payload()
    value["rubric"]["steps"].append(
        {
            "id": "step-2",
            "prompt": G01_GOAL,
            "acceptable_answers": [PRIVATE_ANSWER],
        }
    )
    item = SimpleNamespace(
        id="public-item",
        item_revision=1,
        source=value["source"],
        public_payload=PracticeDraft.model_validate(value).model_dump(
            exclude={"source", "rubric", "previous_item_id"}
        ),
    )
    monkeypatch.setattr(service, "progress_out", lambda *args: visible_progress(step=2))
    snapshot = tutoring.snapshot(None, None, item, SimpleNamespace(id="public-progress", version=2))
    assert snapshot["current_step"] == 2
    assert "selection_task" not in snapshot and "selection_candidates" not in snapshot
    second_plan = plan(G01_GOAL)
    second_plan["current_step"] = 2
    assert (
        bind_selection_task(
            "Help with step two.",
            {"practice_context": snapshot},
            [evidence(G01_SOURCE)],
            second_plan,
        )
        is None
    )
    assert item.public_payload["selection_task"]["current_step"] == 1
    assert item.public_payload["selection_candidates"]["candidate_refs"]


def test_directly_injected_prior_step_metadata_still_rejects():
    value = draft_payload()
    second_plan = plan(G01_GOAL)
    second_plan["current_step"] = 2
    with pytest.raises(ValueError, match="SELECTION_TASK_SCOPE_MISMATCH"):
        bind_selection_task(
            "Help with step two.",
            {
                "selection_task": value["selection_task"],
                "selection_candidates": value["selection_candidates"],
            },
            [evidence(S11_SOURCE)],
            second_plan,
        )


def test_public_snapshot_copies_inventory_without_modifying_persisted_metadata(monkeypatch):
    from app.modules.learning_product import service, tutoring

    value = draft_payload()
    public = PracticeDraft.model_validate(value).model_dump(
        exclude={"source", "rubric", "previous_item_id"}
    )
    item = SimpleNamespace(
        id="public-item", item_revision=1, source=value["source"], public_payload=deepcopy(public)
    )
    monkeypatch.setattr(service, "progress_out", lambda *args: visible_progress())
    snapshot = tutoring.snapshot(None, None, item, SimpleNamespace(id="public-progress", version=1))
    snapshot["selection_candidates"]["candidate_refs"].clear()
    assert item.public_payload["selection_candidates"]["candidate_refs"]
