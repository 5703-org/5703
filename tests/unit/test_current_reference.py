"""Authored cross-domain grammar probes, not independent model evaluation."""

from copy import deepcopy
import pytest

from conversation import current_reference as cr, query_v25

POSITIVE = [
    "Give both speeds with their units. Pair each speed with its timestamp. These are measured speeds, not predictions.",
    "List both salaries with their currencies. Pair each salary with its year. These are annual salaries, not bonuses.",
    "Report both voltages with their uncertainties. Pair each voltage with its frequency.",
    "Give all distances with their units. Pair every distance with its direction.",
    "Explain osmosis. Why is it important?",
    "Describe photosynthesis. Explain its limitations.",
    "A sample is heated. Why does it expand?",
    "The circuit is disconnected. Explain why it does not conduct.",
    "The mixture is not heated. Why is it stable?",
    "Compare evaporation and condensation. Explain their differences.",
    "Compare encryption and compression. Why are they useful?",
    "Using Geography Table 3.1, compare rainfall. State the conditions in its footnote.",
    "Using Finance Figure 2.2, explain the convention in its caption.",
]
NEGATIVE = [
    "'Give both speeds with their units.'",
    "Explain osmosis. Why is it slower than diffusion? Why is it important?",
    "Compare copper and aluminium. Compare them with iron. Why are they denser?",
    "Give each speed with their units.",
    "Give both salaries with its currency.",
    "Give both speeds with their units. Why does it increase?",
    "Give both speeds with their units. These are unrelated values.",
    "Explain osmosis. Compare it with a membrane. Why is it selective?",
    "Compare evaporation and condensation. Why is it faster?",
    "Compare encryption and compression. Explain its limitations.",
    "A car follows a bus. Why is it slower?",
    "A sample is heated. A container is cooled. Why does it expand?",
    "The first is heated. Why does it expand?",
    "This causes a problem. Why is it important?",
    "Why does it expand?",
    "Give their units.",
    "Explain the previous question. Why is it important?",
    "Using Table 3.1 and Table 3.2, explain its note.",
    "Using Table 3.1, a figure illustrates the trend. Explain its caption.",
    "Using Table 3.1, explain its numerical value.",
    'Explain "A sample is heated." Why does it expand?',
    "Explain osmosis. Explain that again.",
    "Explain the attached diagram. Why is it important?",
    "Give both speeds with their units. These cause it.",
]


@pytest.mark.parametrize("question", POSITIVE)
def test_all_refs_have_exact_current_spans(question):
    result = cr.audit(question)
    assert result and result["eligible"]
    assert len(result["bindings"]) == len(list(cr.REF.finditer(question)))
    assert result["history_consulted"] is False
    for binding in result["bindings"]:
        for key in ("reference", "owner"):
            span = binding[key]
            assert question[span["start"] : span["end"]] == span["text"]
        assert binding["owner"]["end"] < binding["reference"]["start"]


@pytest.mark.parametrize("question", NEGATIVE)
def test_unresolved_is_not_licensed(question):
    result = cr.audit(question)
    assert result is None or result["eligible"] is False


@pytest.mark.parametrize("question", POSITIVE + NEGATIVE)
def test_absent_policy_is_identical_base(question):
    base = query_v25.prepare_query(question).model_dump()
    snapshot = deepcopy(base)
    assert cr.apply(base, None) == (base, None)
    assert base == snapshot


@pytest.mark.parametrize("question", POSITIVE)
def test_unrelated_history_cannot_replace_local_question(question):
    history = [{"id": "unrelated", "role": "user", "content": "Explain ocean tides."}]
    base = query_v25.prepare_query(question, history).model_dump()
    prepared, audit = cr.apply(base, cr.POLICY)
    assert prepared["standalone_query"] == question
    assert not prepared["referenced_message_ids"]
    assert not prepared["needs_clarification"]
    understanding = query_v25.describe_requirements(question, prepared, history)
    attached = cr.attach_requirements(understanding, prepared, audit)
    assert attached["requirement_source_text"] == question


def test_multiple_current_actors_do_not_select_history():
    question = "Compare copper and aluminium. Why is it denser?"
    base = query_v25.prepare_query(
        question, [{"id": "old", "role": "user", "content": "Explain iron."}]
    ).model_dump()
    prepared, _ = cr.apply(base, cr.POLICY)
    assert prepared["needs_clarification"] and prepared["standalone_query"] is None
    assert prepared["referenced_message_ids"] == []


def test_policy_and_audit_tampering_fail_closed():
    question = POSITIVE[0]
    base = query_v25.prepare_query(question).model_dump()
    with pytest.raises(ValueError):
        cr.apply(base, "invented")
    prepared, audit = cr.apply(base, cr.POLICY)
    audit["bindings"][0]["owner"]["text"] = "invented"
    with pytest.raises(ValueError):
        cr.attach_requirements({}, prepared, audit)


@pytest.mark.parametrize(
    "reason", ["ambiguous_abbreviation", "ambiguous_topic", "unsupported_intent"]
)
def test_does_not_override_unrelated_clarification_guards(reason):
    base = query_v25.prepare_query(POSITIVE[0]).model_dump()
    base.update(needs_clarification=True, standalone_query=None, fallback_reason=reason)
    assert cr.apply(base, cr.POLICY) == (base, None)


@pytest.mark.parametrize(
    "teaching,reading,expected",
    [
        (None, None, True),
        ({"continuing": False, "turn_role": "user_question"}, None, True),
        ({"continuing": True}, None, False),
        ({"turn_role": "learner_attempt"}, None, False),
        ({"practice_context": {"item_id": "synthetic"}}, None, False),
        (None, {"selection": "synthetic"}, False),
    ],
)
def test_context_ownership(teaching, reading, expected):
    assert cr.ordinary_context(teaching, reading) is expected
