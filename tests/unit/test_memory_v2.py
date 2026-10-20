"""Deterministic field, evidence, precedence and bounded-extraction regressions."""

import json
import pytest
from generation.types import ModelConfig, ProviderResult
from personalisation import memory_v2 as memory
from personalisation.memory_extraction import extract_operations


class Counter:
    def count(self, value):
        return (len(value.encode()) + 2) // 3


def test_extraction_cannot_relabel_an_explicit_preference_or_invent_expiry():
    quote = "I prefer analogies."
    item = memory.deterministic_operations(quote)[0]
    with pytest.raises(ValueError, match="contradicts"):
        memory.validate_operation(
            {**item, "field_key": "difficulty", "category": "self_reported_observation"}, quote
        )
    with pytest.raises(ValueError, match="absent"):
        memory.validate_operation({**item, "expires_at": "2027-01-01T00:00:00Z"}, quote)


def test_observation_and_goal_intent_win_over_embedded_presentation_words():
    assert (
        memory.deterministic_operations("I struggle with analogies in biology.")[0]["category"]
        == "self_reported_observation"
    )
    assert (
        memory.deterministic_operations("My goal is to understand detailed chemistry examples.")[0][
            "category"
        ]
        == "goal"
    )
    assert memory.deterministic_operations("Explain the goal of a course.", current_turn=True) == []


def test_temporary_clause_does_not_discard_a_separate_explicit_lasting_statement():
    text = "I prefer analogies for biology. For this turn, explain without analogies."
    stored = memory.deterministic_operations(text)
    assert len(stored) == 1 and stored[0]["content"] == "I prefer analogies for biology."
    current = memory.deterministic_operations(text, current_turn=True)
    assert current[-1]["content"] == "For this turn, explain without analogies."
    state = memory.learner_state([], text, counter=Counter())
    assert len(state["fields"]) == 1 and state["fields"][0]["content"] == current[-1]["content"]


def entry(identity, field="detail_level", scope="global", **extra):
    return {
        "id": identity,
        "version": 1,
        "category": memory.FIELDS[field],
        "field_key": field,
        "scope": scope,
        "scope_topics": memory.topics(scope),
        "content": "I prefer detailed explanations.",
        "verification": "explicit_user_statement",
        "source_event_sequence": 1,
        **extra,
    }


def select(entries, question, **kwargs):
    return memory.learner_state(entries, question, counter=Counter(), **kwargs)


def test_canonical_aliases_are_stable_and_scopes_remain_distinct():
    assert memory.canonical("preference", "verbosity", "BIOLOGY") == memory.canonical(
        "preference", "detail_level", "biology"
    )
    assert memory.canonical("preference", "detail_level", "global") != memory.canonical(
        "preference", "detail_level", "biology"
    )
    with pytest.raises(ValueError):
        memory.canonical("goal", "detail_level", "global")


def test_atp_topic_resolves_biology_without_literal_subject_word():
    rows = [entry("bio", scope="biology"), entry("chem", scope="chemistry")]
    data = select(rows, "What does ATP do inside a cell?")
    assert [e["id"] for e in data["entries"]] == ["bio"]
    assert {e["id"]: e["reason"] for e in data["excluded"]}["chem"] == "scope_not_relevant"


def test_m3_m4_change_only_selection_on_identical_typed_records():
    rows = [entry("bio", scope="biology"), entry("chem", scope="chemistry")]
    assert {e["id"] for e in select(rows, "What does ATP do?", conditioned=False)["entries"]} == {
        "bio",
        "chem",
    }
    assert {e["id"] for e in select(rows, "What does ATP do?", conditioned=True)["entries"]} == {
        "bio"
    }
    assert rows[0]["version"] == 1


def test_scoped_preference_overrides_global_setting_and_current_instruction_wins():
    rows = [entry("global"), entry("scoped", scope="biology")]
    profile = {"profile": {"style": "concise", "level": "intermediate"}}
    selected = select(rows, "Explain ATP.", profile=profile)
    assert [e["id"] for e in selected["entries"]] == ["scoped"]
    corrected = select(
        rows,
        "For this answer, give a short explanation of ATP.",
        profile=profile,
        current_message_id="current",
    )
    assert corrected["entries"] == []
    assert corrected["fields"][0]["source"] == {"message_id": "current"}
    assert not memory.eligible("For this answer, give a short explanation of ATP.")


def test_explicit_current_correction_masks_conflicting_old_value_before_async_work():
    data = select(
        [entry("old", field="analogies")],
        "Actually, I no longer want analogies.",
        current_message_id="new",
    )
    assert data["entries"] == []
    assert data["fields"][0]["field_key"] == "analogies"
    assert data["fields"][0]["source"]["message_id"] == "new"


def test_question_alone_is_not_observation_but_self_report_is_attributable():
    assert memory.deterministic_operations("Why does ATP release energy?") == []
    value = memory.deterministic_operations("I struggle with ATP and respiration.")[0]
    assert value["category"] == "self_reported_observation"
    assert (
        memory.validate_operation(value, value["source_quote"])["content"] == value["source_quote"]
    )


def test_exact_source_does_not_license_invented_scope_or_mastery():
    text = "I prefer clear examples."
    item = memory.deterministic_operations(text)[0]
    with pytest.raises(ValueError):
        memory.validate_operation({**item, "scope": "astronomy"}, text)
    with pytest.raises(ValueError):
        memory.validate_operation({**item, "content": "Learner has mastered biology."}, text)
    with pytest.raises(ValueError):
        memory.validate_operation(
            {**item, "category": "assessment_performance", "field_key": "assessment_result"}, text
        )


def test_unconfirmed_assessment_and_legacy_observations_are_never_promoted():
    rows = [
        entry("claimed", field="assessment_result", verification="recorded_unconfirmed"),
        entry("legacy", field_key=None),
    ]
    data = select(rows, "Explain ATP.")
    assert data["entries"] == []
    assert {x["reason"] for x in data["excluded"]} == {
        "evidence_unverified",
        "legacy_requires_confirmation",
    }


def test_performance_instances_remain_separate_and_never_become_mastery():
    rows = [
        entry("one", field="assessment_result", verification="automatic_rubric_evaluated"),
        entry("two", field="assessment_result", verification="human_attested"),
    ]
    result = select(rows, "Explain ATP.")
    assert {e["id"] for e in result["entries"]} == {"one", "two"}
    assert not any(f["field_key"] == "mastery" for f in result["fields"])


def test_followup_topic_uses_recent_owned_context_but_explicit_new_subject_wins():
    context = {"messages": [{"role": "user", "content": "Explain ATP."}]}
    assert "biology" in memory.query_topics("Explain that more simply.", context)
    assert "biology" not in memory.query_topics("Explain acid buffers instead.", context)


def test_full_memory_payload_is_bounded_and_has_no_source_body_copies():
    rows = [
        entry(
            str(i),
            field="assessment_result",
            verification="automatic_rubric_evaluated",
            content="X" * 1800,
            provenance={"rubric": "PRIVATE" * 1000},
        )
        for i in range(10)
    ]
    payload = select(rows, "Explain ATP.")
    assert Counter().count(json.dumps(payload)) <= memory.MEMORY_TOKEN_LIMIT
    assert "PRIVATE" not in json.dumps(payload)


class Transport:
    def __init__(self, payload):
        self.payload, self.calls = payload, 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        return ProviderResult(raw_text=json.dumps(self.payload), usage={"total_tokens": 12})


def test_invalid_extraction_has_one_repair_and_retains_both_usage_records():
    transport = Transport({"operations": [{"operation": "UPDATE"}]})
    result = extract_operations("I prefer examples.", ModelConfig(), adapter=transport)
    assert result["error"]["code"] == "MEMORY_EXTRACTION_INVALID"
    assert transport.calls == 2 and len(result["usage"]) == 2


def test_valid_but_late_extraction_never_publishes(monkeypatch):
    item = memory.deterministic_operations("I prefer examples.")[0]
    transport = Transport({"operations": [item]})
    clock = {"time": 0.0}
    import personalisation.memory_extraction as extraction

    monkeypatch.setattr(extraction.time, "monotonic", lambda: clock["time"])
    original = transport.generate

    def late(*args, **kwargs):
        clock["time"] = 91.0
        return original(*args, **kwargs)

    transport.generate = late
    result = extract_operations("I prefer examples.", ModelConfig(), adapter=transport)
    assert result["operations"] == [] and result["error"]["code"] == "MEMORY_DEADLINE_EXCEEDED"
    assert transport.calls == 1 and len(result["usage"]) == 1
