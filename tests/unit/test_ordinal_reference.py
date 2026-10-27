"""Ordinal context routing does not resolve scientific values or repair citations."""

from copy import deepcopy
import pytest
from conversation import ordinal_reference as rule, query_v25
from conversation.context import select_context

FOLLOW = "Explain why the second listed value is higher, limited to the supplied observations."
PAIRS = [
    (
        "Compare water vapor pressure at 18 degrees Celsius and 28 degrees Celsius.",
        "18 degrees Celsius: 15.5 torr; 28 degrees Celsius: 28.3 torr [ev_001]",
    ),
    ("Compare a circuit measured at 3 V and 5 V.", "First: 0.2 A; second: 0.4 A [ev_001]"),
    ("Compare plant growth after 7 days and 14 days.", "7 days: 2 cm; 14 days: 5 cm [ev_002]"),
]


def history(pair=PAIRS[0]):
    return [
        {"message_id": "u", "role": "user", "content": pair[0]},
        {"message_id": "a", "role": "assistant", "content": pair[1]},
    ]


def run(question=FOLLOW, rows=None, policy=rule.POLICY):
    rows = history() if rows is None else rows
    base = query_v25.prepare_query(question, rows).model_dump()
    before = deepcopy(base)
    result, audit = rule.apply(base, rows, policy)
    assert base == before
    return result, audit


@pytest.mark.parametrize("pair", PAIRS)
@pytest.mark.parametrize("ordinal", ["first", "second", "third", "last"])
def test_followup_preserves_question_and_binds_only_latest_exchange(pair, ordinal):
    q = FOLLOW.replace("second", ordinal)
    p, a = run(q, history(pair))
    assert p["intent"] == "follow_up" and p["topic_relation"] == "same_topic"
    assert (
        p["original_message"] == q
        and p["standalone_query"] == q + " Prior learner question: " + pair[0]
    )
    assert p["referenced_message_ids"] == ["u", "a"]
    assert not a["exact_value_resolved"] and not a["source_sufficiency_verified"]


@pytest.mark.parametrize(
    "rows",
    [
        [],
        history()[:1],
        history()[1:],
        history(("Why does it expand?", "Two quantities: 3 and 5.")),
        history(("Explain rainfall.", "Rain is water.")),
        history(("Compare circuit readings.", "List: 3, 5.\n\nAnother list: 6, 8.")),
        history() + [{"message_id": "new", "role": "user", "content": "Explain rocks."}],
        history()[:1] + [{**history()[1], "state": "failed"}],
    ],
)
def test_absent_incomplete_or_ambiguous_context_clarifies(rows):
    p, a = run(rows=rows)
    assert p["needs_clarification"] and p["standalone_query"] is None
    assert not p["referenced_message_ids"] and not a["eligible"]


@pytest.mark.parametrize(
    "q",
    [
        "Explain second ionization energy.",
        'Explain the phrase "the second listed value".',
        "A circuit has readings: 3 V; 5 V. Compare the first listed value and the second listed value.",
    ],
)
def test_current_explicit_question_and_quoted_phrase_do_not_consult_history(q):
    base = query_v25.prepare_query(q, history()).model_dump()
    assert rule.apply(base, history(), rule.POLICY) == (base, None)


def test_no_scan_into_older_topic_or_summary():
    p, _ = run(
        rows=history()
        + [
            {"message_id": "n1", "role": "user", "content": "Explain rocks."},
            {"message_id": "n2", "role": "assistant", "content": "Rocks are aggregates."},
        ]
    )
    assert p["needs_clarification"]
    assert run(FOLLOW + " Use another session.")[0]["needs_clarification"]


def test_absent_frozen_policy_preserves_historical_behavior():
    p, a = run(policy=None)
    assert p == query_v25.prepare_query(FOLLOW, history()).model_dump() and a is None


def test_context_selector_excludes_other_sessions_future_and_failed_turns():
    rows = [
        {**m, "session_id": "owned", "sequence": i + 1, "state": "answered"}
        for i, m in enumerate(history())
    ]
    rows += [
        {**m, "message_id": "foreign-" + m["message_id"], "session_id": "other", "sequence": i + 3}
        for i, m in enumerate(history(PAIRS[1]))
    ]
    selected = select_context("owned", rows, 2).model_dump()["messages"]
    p, _ = run(rows=selected)
    assert p["referenced_message_ids"] == ["u", "a"] and "circuit" not in p["standalone_query"]


@pytest.mark.parametrize(
    "extra",
    [
        {"teaching_mode": "hint"},
        {"turn_role": "learner_attempt"},
        {"practice_context": {"item_id": "i"}},
        {"pending_tutor_question_id": "p"},
    ],
)
def test_protected_task_owners_remain_unchanged(extra):
    assert not rule.eligible_context(
        {"teaching_mode": "direct", "turn_role": "user_question", **extra}, None
    )


def test_direct_continuation_is_eligible_but_reading_is_not():
    task = {"teaching_mode": "direct", "turn_role": "user_question", "continuing": True}
    assert rule.eligible_context(task, None)
    assert not rule.eligible_context(task, {"source": "s"})


def test_later_excluded_turn_prevents_older_context_reuse():
    rows = [{**m, "sequence": i + 1} for i, m in enumerate(history())]
    assert rule.selected_history({"messages": rows, "cutoff_sequence": 2}) == rows
    assert rule.selected_history({"messages": rows, "cutoff_sequence": 3}) == []
    assert rule.selected_history({"messages": rows}) == []
