"""Selection policy and lifecycle guards; score fixtures are unit-only."""

import copy
import pytest
from personalisation import memory_v2 as old, memory_v3 as new


class Counter:
    def count(self, value):
        return (len(value.encode()) + 2) // 3


def entry(scope="global", **overrides):
    return {
        "id": "memory-1",
        "version": 1,
        "category": "preference",
        "field_key": "detail_level",
        "scope": scope,
        "scope_topics": old.topics(scope),
        "content": "I prefer detailed explanations.",
        "verification": "explicit_user_statement",
        "source_event_sequence": 1,
        "source_message_id": "source-1",
        **overrides,
    }


def owned(row):
    return {
        "owned": True,
        "memory_id": row["id"],
        "memory_version": row["version"],
        "source_message_id": row["source_message_id"],
        "content": row["content"],
        "source_hash": old.digest(row["content"]),
    }


def policy():
    return new.freeze_policy(enabled=True, threshold=0.85, calibration_id="a" * 64)


@pytest.mark.parametrize(
    "question",
    [
        "How does photosynthesis work?",
        "Explain atomic orbitals.",
        "Tell me more about it.",
        "For this answer, keep it short.",
        "What is mitosis?",
        "What causes high blood pressure?",
    ],
)
def test_disabled_selector_preserves_frozen_v2_choices_exactly(question):
    entries = [entry(), entry("biology", id="b"), entry("chemistry", id="c")]
    context = {"messages": [{"role": "user", "content": "Explain cellular respiration."}]}
    args = (entries, question, {"profile": {"style": "concise"}}, context)
    legacy = old.learner_state(*args, counter=Counter())
    selected = new.select(*args, counter=Counter()).state
    selected["version"] = old.SELECTOR_VERSION
    assert selected == legacy


def test_semantic_selection_supplements_scope_and_retains_profile_precedence():
    row = entry("botany")
    before = copy.deepcopy(row)
    result = new.select(
        [row],
        "How do stomata respond to drought?",
        {"profile": {"style": "concise"}},
        policy=policy(),
        scorer=lambda q, s: [0.91],
        counter=Counter(),
    )
    assert result.state["entries"][0]["scope"] == "botany"
    assert result.trace["status"] == "semantic_supplement"
    assert row == before


def test_per_entry_decline_prevents_semantic_scoring_but_explicit_scope_still_applies():
    def forbidden(*args):
        pytest.fail("Declined semantic match must not encode this scope")

    row = entry("botany", match_policy="rules_only")
    declined = new.select(
        [row],
        "How do stomata respond to drought?",
        policy=policy(),
        scorer=forbidden,
        counter=Counter(),
    )
    assert declined.state["entries"] == []
    assert declined.state["excluded"][0]["reason"] == "semantic_match_declined"
    explicit = new.select(
        [row], "Explain botany.", policy=policy(), scorer=forbidden, counter=Counter()
    )
    assert explicit.state["entries"][0]["id"] == row["id"]
    opted_in = new.select(
        [{**row, "match_policy": "calibrated_semantic"}],
        "How do stomata respond?",
        policy=policy(),
        scorer=lambda q, s: [0.95],
        counter=Counter(),
    )
    assert opted_in.state["entries"][0]["id"] == row["id"]


def test_paused_memory_never_scores_or_applies_when_semantic_selector_is_active():
    def forbidden(*args):
        pytest.fail("Paused memory must not encode a scope")

    selected = new.select(
        [entry("botany", status="paused")],
        "Explain stomata.",
        policy=policy(),
        scorer=forbidden,
        counter=Counter(),
    )
    assert selected.state["entries"] == []
    assert selected.state["excluded"][0]["reason"] == "memory_inactive"


def test_current_override_and_unsupported_observation_never_invoke_scorer():
    def forbidden(*args):
        pytest.fail("No semantic call expected")

    for row, question in [
        (entry("botany"), "For this answer, be concise."),
        (entry("botany", verification="unsupported"), "Explain stomata."),
    ]:
        result = new.select([row], question, policy=policy(), scorer=forbidden, counter=Counter())
        assert result.state["entries"] == []


def test_owned_conditional_source_recovers_scope_without_changing_record():
    row = entry(content="For botany, I prefer detailed explanations.")
    result = new.select(
        [row],
        "How do stomata respond?",
        policy=policy(),
        source_reader=owned,
        scorer=lambda q, s: [0.93],
        counter=Counter(),
    )
    assert result.state["entries"][0]["scope"] == "botany"
    assert row["scope"] == "global"
    assert result.trace["source_rereads"] == [{"id": row["id"], "reason": "owned_source_reread"}]


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"owned": False}, "conditional_source_invalid"),
        ({"memory_version": 2}, "conditional_source_invalid"),
        ({"content": "different source"}, "conditional_source_invalid"),
        ({"source_message_id": "other-user"}, "conditional_source_invalid"),
    ],
)
def test_foreign_changed_or_stale_conditional_source_is_excluded(change, reason):
    row = entry(content="For botany, I prefer detailed explanations.")
    result = new.select(
        [row],
        "Explain stomata.",
        policy=policy(),
        source_reader=lambda e: {**owned(e), **change},
        counter=Counter(),
    )
    assert result.state["entries"] == []
    assert result.trace["source_rereads"][0]["reason"] == reason


def test_exception_condition_does_not_become_a_global_preference():
    row = entry(content="I prefer detailed explanations except for botany.")
    result = new.select(
        [row], "Explain stomata.", policy=policy(), source_reader=owned, counter=Counter()
    )
    assert result.state["entries"] == []
    assert result.trace["source_rereads"][0]["reason"] == "conditional_scope_requires_clarification"


def test_model_failure_is_recorded_and_known_rules_remain_available():
    def unavailable(*args):
        raise RuntimeError("Private implementation detail")

    result = new.select(
        [entry("botany"), entry("biology", id="bio")],
        "Explain a chloroplast.",
        policy=policy(),
        scorer=unavailable,
        counter=Counter(),
    )
    assert [e["id"] for e in result.state["entries"]] == ["bio"]
    assert result.trace["status"] == "semantic_unavailable_rules_fallback"
    assert result.trace["fallback_reason"] == "RuntimeError"
    assert "Private implementation detail" not in str(result)


@pytest.mark.parametrize("threshold", [None, True, float("nan"), -0.01, 1.01])
def test_activation_requires_explicit_finite_calibration(threshold):
    with pytest.raises(ValueError):
        new.freeze_policy(enabled=True, threshold=threshold, calibration_id="a" * 64)


def test_model_device_and_revision_cannot_drift():
    value = policy()
    value["embedding"]["embedding_device"] = "cuda"
    with pytest.raises(ValueError, match="identity"):
        new.validate_policy(value)


@pytest.mark.parametrize("value", [[], "policy", 1, False])
def test_invalid_policy_shape_has_a_bounded_configuration_error(value):
    with pytest.raises(ValueError, match="object"):
        new.validate_policy(value)


def test_disabled_diagnostics_count_actual_selected_memories():
    result = new.select([entry("biology")], "Explain photosynthesis.", counter=Counter())
    assert result.trace["selected_ids"] == ["memory-1"]


def test_candidate_budget_and_private_trace_do_not_expand_prompt():
    rows = [entry("unrecognized scope " + str(i), id=str(i)) for i in range(30)]
    seen = []
    result = new.select(
        rows,
        "Explain meteorites.",
        policy=policy(),
        scorer=lambda q, s: seen.append(len(s)) or [0.1] * len(s),
        counter=Counter(),
    )
    assert seen == [24]
    assert result.state["token_count"] <= 768
    assert "selection_trace" not in result.state
