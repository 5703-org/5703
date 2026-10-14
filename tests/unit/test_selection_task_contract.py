"""Public candidate bindings and opposite H1 branches; no semantic ratings."""

from copy import deepcopy
import hashlib
from types import SimpleNamespace

import pytest

from contracts.models import EvidenceSnapshot
from generation.selection_task_contract import bind_selection_task
from generation.teaching_plan_v10 import with_selection_task

S11_GOAL = "Choose the supplied pressure-volume relation before substituting values."
S11_SOURCE = "For a fixed amount of ideal gas at constant temperature, P1 * V1 = P2 * V2."
G01_GOAL = "Choose the first inverse operation before calculating."
G01_SOURCE = "Performing the same operation on both sides of an equation preserves equality."


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan(goal):
    return {
        "current_step": 1,
        "recorded_step_goal": {"operation": goal, "answer_key_used": False},
        "current_question": goal,
        "hint_stage": {"level": 1},
        "hint_task": {"operation_ref": "recorded_step_goal.operation"},
        "policy_flags": {"version": "generation_controls_v10", "arm": "D"},
    }


def evidence(text, chunk_id="chunk-public"):
    return EvidenceSnapshot.model_validate(
        {
            "chunk_id": chunk_id,
            "evidence_id": "ev_001",
            "asset_id": "asset-public",
            "processing_id": "processing-public",
            "source_title": "Public test source",
            "section": "Selection context",
            "pages": [1],
            "locator": "Public source line 1",
            "text": text,
            "text_hash": digest(text),
            "context_order": 1,
        }
    ).model_dump()


def annotation(goal, *, supplied, source=None):
    refs = (
        [
            {
                "origin": "evidence",
                "chunk_id": "chunk-public",
                "text_sha256": digest(source),
                "start": 0,
                "end": len(source),
                "exact_quote": source,
            }
        ]
        if supplied
        else []
    )
    return {
        "version": "selection_task_v1",
        "current_step": 1,
        "task_ref": {
            "field": "recorded_step_goal.operation",
            "start": 0,
            "end": len(goal),
            "exact_quote": goal,
        },
        "candidate_presence": "supplied" if supplied else "absent",
        "candidate_refs": refs,
    }


def inventory(value):
    return {
        "version": "selection_candidates_v1",
        "current_step": value["current_step"],
        "task_ref": deepcopy(value["task_ref"]),
        "candidate_refs": deepcopy(value["candidate_refs"]),
    }


def public_context(value):
    return {"selection_task": value, "selection_candidates": inventory(value)}


def test_task_linked_s11_evidence_supplies_a_candidate_without_candidate_field():
    public = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    candidate = "P1 * V1 = P2 * V2"
    public["candidate_refs"][0].update(
        start=S11_SOURCE.index(candidate),
        end=S11_SOURCE.index(candidate) + len(candidate),
        exact_quote=candidate,
    )
    context = {"practice_context": {**public_context(public), "conditions": ["Fixed gas amount."]}}
    frozen = bind_selection_task(
        "Help with this step.", context, [evidence(S11_SOURCE)], plan(S11_GOAL)
    )
    assert "candidate" not in context["practice_context"]
    assert frozen["candidate_presence"] == "supplied"
    assert frozen["candidate_refs"][0]["exact_quote"] == candidate
    assert frozen["candidate_refs"][0]["evidence_id"] == "ev_001"
    assert frozen["learner_action"]["branch"] == "supplied_candidate_fit"
    assert frozen["learner_action"]["basis_required"] is True
    assert frozen["learner_action"]["why_check_before_use_required"] is True
    assert frozen["display_policy"]["candidate_expression_allowed"] is False
    assert frozen["display_policy"]["candidate_name_or_operation_class_allowed"] is False
    assert frozen["display_policy"]["source_support_overrides_hint_scope"] is False
    assert frozen["assessment_boundary"]["candidate_fit_is_asserted"] is False


def test_g01_general_equality_source_does_not_supply_an_operation_candidate():
    context = public_context(annotation(G01_GOAL, supplied=False))
    frozen = bind_selection_task(
        "Help with this step.", context, [evidence(G01_SOURCE)], plan(G01_GOAL)
    )
    assert frozen["candidate_presence"] == "absent"
    assert frozen["candidate_refs"] == []
    assert frozen["learner_action"]["branch"] == "whole_structure_and_order"
    assert frozen["display_policy"]["allowed_candidate_reference"] is None
    assert frozen["assessment_boundary"]["answer_key_used"] is False


@pytest.mark.parametrize("canonical_hash", [None, "not-the-actual-source-hash"])
def test_selected_source_requires_canonical_hash_despite_a_correct_similar_field(canonical_hash):
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    row = evidence(S11_SOURCE)
    assert "text_hash" in row and "text_sha256" not in row
    row["text_sha256"] = digest(S11_SOURCE)
    row["text_hash"] = canonical_hash
    with pytest.raises(ValueError, match="SELECTION_TASK_SOURCE_HASH_MISMATCH"):
        bind_selection_task("Help.", public_context(value), [row], plan(S11_GOAL))


@pytest.mark.parametrize("source", [S11_SOURCE, G01_SOURCE, "a = b; c = d", "No expression here."])
def test_legacy_unannotated_input_remains_unknown_regardless_of_source_notation(source):
    assert bind_selection_task("Help.", {}, [evidence(source)], plan(S11_GOAL)) is None
    assert (
        bind_selection_task("Help.", {"practice_context": {}}, [evidence(source)], plan(G01_GOAL))
        is None
    )


@pytest.mark.parametrize("goal", ["Choose a candidate relation.", "Choose the first operation."])
def test_task_category_alone_cannot_create_supplied_candidate(goal):
    value = annotation(goal, supplied=True, source=S11_SOURCE)
    value["candidate_refs"] = []
    with pytest.raises(ValueError, match="SELECTION_TASK_PRESENCE_INVALID"):
        bind_selection_task("Help.", public_context(value), [evidence(S11_SOURCE)], plan(goal))


def test_absent_branch_rejects_candidate_reference_instead_of_ignoring_it():
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    value["candidate_presence"] = "absent"
    with pytest.raises(ValueError, match="SELECTION_TASK_PRESENCE_INVALID"):
        bind_selection_task("Help.", public_context(value), [evidence(S11_SOURCE)], plan(S11_GOAL))


@pytest.mark.parametrize(
    "failure", ["excluded", "wrong_chunk", "changed_text", "changed_span", "duplicate"]
)
def test_supplied_binding_failure_is_explicit_and_never_switches_to_absent(failure):
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    rows = [evidence(S11_SOURCE)]
    expected = "SELECTION_TASK_CANDIDATE_UNAVAILABLE"
    if failure == "excluded":
        rows = []
    elif failure == "wrong_chunk":
        rows = [evidence(S11_SOURCE, "different-public-chunk")]
    elif failure == "changed_text":
        rows = [evidence(S11_SOURCE + " Another sentence.")]
        expected = "SELECTION_TASK_SOURCE_HASH_MISMATCH"
    elif failure == "changed_span":
        value["candidate_refs"][0]["end"] -= 1
        expected = "SELECTION_TASK_SOURCE_SPAN_MISMATCH"
    else:
        rows *= 2
    with pytest.raises(ValueError, match=expected):
        bind_selection_task("Help.", public_context(value), rows, plan(S11_GOAL))


def test_same_top_level_and_owned_annotation_bind_but_conflicting_values_reject():
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    context = {**public_context(value), "practice_context": deepcopy(public_context(value))}
    first = bind_selection_task("Help.", context, [evidence(S11_SOURCE)], plan(S11_GOAL))
    context["practice_context"]["selection_task"]["current_step"] = 2
    with pytest.raises(ValueError, match="SELECTION_TASK_ANNOTATION_CONFLICT"):
        bind_selection_task("Help.", context, [evidence(S11_SOURCE)], plan(S11_GOAL))
    assert first["current_step"] == 1


def test_changed_public_conditions_change_binding_identity_without_deciding_fit():
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    context = {"practice_context": {**public_context(value), "conditions": ["Fixed amount."]}}
    first = bind_selection_task("Help.", context, [evidence(S11_SOURCE)], plan(S11_GOAL))
    context["practice_context"]["conditions"] = ["The amount is not stated."]
    second = bind_selection_task("Help.", context, [evidence(S11_SOURCE)], plan(S11_GOAL))
    assert first["candidate_presence"] == second["candidate_presence"] == "supplied"
    assert first["task_input_sha256"] != second["task_input_sha256"]
    assert first["binding_sha256"] != second["binding_sha256"]
    assert second["assessment_boundary"]["candidate_fit_is_asserted"] is False


@pytest.mark.parametrize(
    "field", ["current_step", "task_quote", "task_partial", "goal_changed", "level"]
)
def test_stale_or_partial_task_anchor_and_changed_help_scope_reject(field):
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    current_plan = plan(S11_GOAL)
    expected = "SELECTION_TASK_ANCHOR_MISMATCH"
    if field == "current_step":
        value["current_step"] = 2
        expected = "SELECTION_TASK_SCOPE_MISMATCH"
    elif field == "task_quote":
        value["task_ref"]["exact_quote"] = "A different step."
    elif field == "task_partial":
        value["task_ref"].update(end=6, exact_quote="Choose")
    elif field == "goal_changed":
        current_plan["recorded_step_goal"]["operation"] = G01_GOAL
    else:
        current_plan["hint_stage"]["level"] = 2
        expected = "SELECTION_TASK_SCOPE_MISMATCH"
    with pytest.raises(ValueError, match=expected):
        bind_selection_task("Help.", public_context(value), [evidence(S11_SOURCE)], current_plan)


@pytest.mark.parametrize(
    "extra", ["correct_answer", "expected_fit", "gold_label", "selected_operation"]
)
def test_annotation_does_not_accept_correctness_or_hidden_answer_fields(extra):
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    value[extra] = True
    with pytest.raises(ValueError, match="SELECTION_TASK_ANNOTATION_INVALID"):
        bind_selection_task("Help.", public_context(value), [evidence(S11_SOURCE)], plan(S11_GOAL))


@pytest.mark.parametrize("supplied", [True, False])
def test_attached_plan_preserves_frozen_policy_and_allows_only_its_bound_branch(supplied):
    goal = S11_GOAL if supplied else G01_GOAL
    source = S11_SOURCE if supplied else G01_SOURCE
    original = plan(goal)
    context = public_context(annotation(goal, supplied=supplied, source=source))
    frozen = bind_selection_task("Help.", context, [evidence(source)], original)
    attached = with_selection_task(original, frozen)
    assert attached["policy_flags"] == original["policy_flags"]
    assert attached["selection_task_contract"] == frozen
    assert attached["hint_task"]["candidate_presence"] == ("supplied" if supplied else "absent")
    assert "selection_task_contract" not in original
    assert source not in attached["action_instruction"]
    attached["selection_task_contract"]["candidate_refs"].append({"changed": True})
    assert frozen["candidate_refs"] != attached["selection_task_contract"]["candidate_refs"]


def test_public_practice_option_can_bind_without_reading_a_grading_answer():
    text = "A publicly supplied operation candidate."
    value = annotation(G01_GOAL, supplied=False)
    value["candidate_presence"] = "supplied"
    value["candidate_refs"] = [
        {
            "origin": "practice_option",
            "option_id": "option-public",
            "text_sha256": digest(text),
            "start": 0,
            "end": len(text),
            "exact_quote": text,
        }
    ]
    context = {
        "practice_context": {
            **public_context(value),
            "options": [{"id": "option-public", "text": text}],
        }
    }
    frozen = bind_selection_task("Help.", context, [], plan(G01_GOAL))
    assert frozen["candidate_presence"] == "supplied"
    assert frozen["candidate_refs"][0]["option_id"] == "option-public"


def test_public_task_expression_can_bind_to_its_exact_input_span():
    problem = "Consider the already supplied option: a = b."
    value = annotation(G01_GOAL, supplied=False)
    value["candidate_presence"] = "supplied"
    value["candidate_refs"] = [
        {
            "origin": "task",
            "field": "current_problem",
            "text_sha256": digest(problem),
            "start": problem.index("a = b"),
            "end": problem.index("a = b") + 5,
            "exact_quote": "a = b",
        }
    ]
    frozen = bind_selection_task(
        "Help.", {"current_problem": problem, **public_context(value)}, [], plan(G01_GOAL)
    )
    assert frozen["candidate_refs"][0]["exact_quote"] == "a = b"
    assert frozen["display_policy"]["candidate_expression_allowed"] is False


def test_owned_snapshot_projects_only_public_annotation(monkeypatch):
    from app.modules.learning_product import service, tutoring

    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    visible = {
        "current_step": 1,
        "current_step_prompt": S11_GOAL,
        "current_step_response_kind": "text",
        "expected_unit": None,
        "state": "awaiting_attempt",
        "help_level": 1,
        "hints": [],
        "full_explanation": None,
        "attempts": [],
    }
    monkeypatch.setattr(service, "progress_out", lambda *args: deepcopy(visible))

    class PublicItem:
        id = "public-item"
        item_revision = 1
        source = {"source_unit_id": "public-unit"}
        public_payload = {"prompt": "Public gas task.", "kind": "step", **public_context(value)}

        @property
        def private_rubric(self):
            raise AssertionError("The snapshot must not read grading material.")

    snapshot = tutoring.snapshot(
        None, None, PublicItem(), SimpleNamespace(id="public-progress", version=1)
    )
    assert snapshot["selection_task"] == value
    assert snapshot["selection_candidates"] == inventory(value)
    snapshot["selection_task"]["candidate_refs"].clear()
    assert value["candidate_refs"]


def test_annotation_without_independent_public_inventory_is_an_explicit_failure():
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    with pytest.raises(ValueError, match="SELECTION_TASK_INVENTORY_MISSING"):
        bind_selection_task(
            "Help.", {"selection_task": value}, [evidence(S11_SOURCE)], plan(S11_GOAL)
        )


def test_s11_annotation_cannot_turn_a_retained_public_candidate_inventory_into_absent():
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    context = public_context(value)
    context["selection_task"]["candidate_presence"] = "absent"
    context["selection_task"]["candidate_refs"] = []
    with pytest.raises(ValueError, match="SELECTION_TASK_INVENTORY_MISMATCH"):
        bind_selection_task("Help.", context, [evidence(S11_SOURCE)], plan(S11_GOAL))


def test_g01_annotation_cannot_invent_a_candidate_from_a_general_principle():
    value = annotation(G01_GOAL, supplied=False)
    context = public_context(value)
    context["selection_task"] = annotation(G01_GOAL, supplied=True, source=G01_SOURCE)
    with pytest.raises(ValueError, match="SELECTION_TASK_INVENTORY_MISMATCH"):
        bind_selection_task("Help.", context, [evidence(G01_SOURCE)], plan(G01_GOAL))


def test_visible_practice_options_cannot_be_omitted_from_absent_inventory():
    context = {
        "practice_context": {
            **public_context(annotation(G01_GOAL, supplied=False)),
            "options": [{"id": "public-option", "text": "A visibly provided option."}],
        }
    }
    with pytest.raises(ValueError, match="SELECTION_TASK_INVENTORY_OPTIONS_CONFLICT"):
        bind_selection_task("Help.", context, [], plan(G01_GOAL))


def test_conflicting_top_level_and_owned_candidate_inventory_rejects():
    value = annotation(S11_GOAL, supplied=True, source=S11_SOURCE)
    context = {**public_context(value), "practice_context": deepcopy(public_context(value))}
    context["practice_context"]["selection_candidates"]["candidate_refs"] = []
    with pytest.raises(ValueError, match="SELECTION_TASK_INVENTORY_CONFLICT"):
        bind_selection_task("Help.", context, [evidence(S11_SOURCE)], plan(S11_GOAL))
