"""Default memory scope precision and frozen legacy policy behavior."""

import copy

from personalisation import memory_v2, memory_v3


class Counter:
    def count(self, value):
        return (len(value.encode()) + 2) // 3


def entry(scope, identity="saved", field="detail_level"):
    return {
        "id": identity,
        "version": 1,
        "category": "preference",
        "field_key": field,
        "scope": scope,
        "scope_topics": memory_v2.topics(scope),
        "content": f"For {scope}, please give a detailed explanation.",
        "verification": "user_explicit",
        "source_message_id": f"source-{identity}",
        "source_event_sequence": 1,
    }


def selected(rows, question, context=None, policy=None):
    return memory_v3.select(
        rows,
        question,
        {"profile": {"style": "concise"}},
        context,
        policy=policy,
        counter=Counter(),
    )


def test_specific_scopes_do_not_leak_to_another_topic_in_same_discipline():
    saved = entry("photosynthesis")
    before = copy.deepcopy(saved)
    result = selected([saved], "Explain cellular respiration.")
    assert result.state["entries"] == []
    assert result.state["excluded"][0]["reason"] == "specific_scope_not_named"
    assert saved == before
    assert result.trace["rule_scope_version"] == memory_v3.RULE_SCOPE_VERSION


def test_exact_specific_scope_and_anaphoric_followup_select_saved_preference():
    saved = entry("photosynthesis")
    direct = selected([saved], "Explain photosynthesis.")
    followup = selected(
        [saved],
        "Can you explain it further?",
        {"recent_messages": [{"role": "user", "content": "Explain photosynthesis."}]},
    )
    assert direct.trace["selected_ids"] == ["saved"]
    assert followup.trace["selected_ids"] == ["saved"]


def test_explicit_new_topic_and_current_instruction_keep_precedence():
    saved = entry("photosynthesis")
    switched = selected(
        [saved],
        "Explain cellular respiration.",
        {"recent_messages": [{"role": "user", "content": "Explain photosynthesis."}]},
    )
    concise = selected([saved], "Explain photosynthesis. For this answer, be concise.")
    assert switched.trace["selected_ids"] == []
    assert concise.trace["selected_ids"] == []
    assert concise.state["fields"][0]["verification"] == "current_user_instruction"


def test_discipline_scope_still_applies_and_old_frozen_policy_is_replayable():
    broad = entry("biology")
    assert selected([broad], "Explain photosynthesis.").trace["selected_ids"] == ["saved"]
    old_specific = entry("photosynthesis")
    policy = memory_v3.freeze_policy()
    policy["version"] = memory_v3.LEGACY_POLICY_VERSION
    del policy["rule_scope_version"]
    previous = selected([old_specific], "Explain cellular respiration.", policy=policy)
    assert previous.trace["selected_ids"] == ["saved"]
    assert previous.trace["version"] == memory_v3.LEGACY_POLICY_VERSION
