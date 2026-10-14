"""Owned leading conditions, exact historical policy replay, and writer contracts."""

from copy import deepcopy
import json

import pytest

from personalisation import memory_policy, memory_v2 as rules, memory_v3, memory_v4, memory_v5
from personalisation import memory_writer_v4, memory_writer_v5
from personalisation.compiler import compile_profile


SOURCE = "For biology questions, I prefer detailed explanations."


def record(text=SOURCE, *, scope="biology", identifier="scoped-detail", version=1):
    return {
        "id": identifier,
        "version": version,
        "category": "preference",
        "field_key": "detail_level",
        "content": text,
        "scope": scope,
        "scope_topics": rules.topics(scope),
        "verification": "explicit_user_statement",
        "source_message_id": identifier + "-source",
        "source_event_sequence": version,
        "status": "active",
        "provenance": {"source_quote": text, "source_hash": rules.digest(text)},
    }


def reader(text):
    def read(entry):
        return {
            "owned": True,
            "memory_id": entry["id"],
            "memory_version": entry["version"],
            "source_message_id": entry["source_message_id"],
            "source_hash": rules.digest(text),
            "content": text,
        }

    return read


class Counter:
    def count(self, text):
        return len(text.split())


def select(entries, question, source=SOURCE, **options):
    return memory_v5.select(
        entries,
        question,
        compile_profile({"style": "concise"}, turn_message=question),
        source_reader=options.pop("source_reader", reader(source)),
        counter=Counter(),
        **options,
    )


@pytest.mark.parametrize(
    "text,scope",
    [
        (SOURCE, "biology"),
        ("For chemistry questions, I prefer detailed explanations.", "chemistry"),
        ("In genetics, I prefer detailed explanations.", "genetics"),
        (
            "When studying cellular respiration, I learn best with detailed explanations.",
            "cellular respiration",
        ),
        ("Remember, for physiology questions, I prefer short explanations.", "physiology"),
        ("For biology, I no longer prefer detailed explanations.", "biology"),
    ],
)
def test_complete_known_leading_condition_retains_whole_source_span(text, scope):
    source = "  " + text + " Explain photosynthesis."
    actual = memory_v5.condition(text, source)
    assert actual == (scope, "exact_leading_topic_condition", [2, 2 + len(text)])
    assert source[slice(*actual[2])] == text


@pytest.mark.parametrize(
    "text",
    [
        "For biology and chemistry questions, I prefer detailed explanations.",
        "For botany questions, I prefer detailed explanations.",
        "For biology questions, my teacher prefers detailed explanations.",
        'For biology questions, "I prefer detailed explanations."',
        "For biology questions, I prefer detailed explanations unless I am revising.",
        "For biology questions, I prefer detailed explanations for chemistry.",
        "For biology questions, I prefer detailed or short explanations.",
        "For biology questions, I prefer detailed explanations, but only at exam time.",
        "For biology questions I prefer detailed explanations.",
        "For biology questions, use detailed explanations.",
        "For biology questions, delete my detailed preference.",
    ],
)
def test_unknown_compound_unattributed_quoted_and_unconfirmed_conditions_withheld(text):
    assert memory_v5.condition(text, text)[0] is None


def test_confirmed_leading_action_still_requires_known_unique_scope():
    text = "For biology, use detailed explanations."
    assert memory_v5.condition(text, text)[0] is None
    assert (
        memory_v5.condition(text, text, confirmed=True, confirmed_scope="biology")[0] == "biology"
    )
    unknown = "For botany, use detailed explanations."
    assert (
        memory_v5.condition(unknown, unknown, confirmed=True, confirmed_scope="botany")[0] is None
    )


@pytest.mark.parametrize(
    "quote,source",
    [
        (SOURCE, SOURCE + " " + SOURCE),
        ("I prefer detailed explanations.", SOURCE),
        ("For biology questions, I prefer detailed explanations.", SOURCE + " Only when revising."),
        ("For biology questions, I prefer detailed", SOURCE),
        (SOURCE, "My teacher says " + SOURCE),
        (SOURCE, 'He wrote "' + SOURCE + '"'),
    ],
)
def test_full_unique_owned_preference_cannot_drop_attached_condition_or_other_speaker(
    quote, source
):
    assert memory_v5.condition(quote, source)[0] is None


def test_new_writer_persists_exact_leading_source_while_historical_writer_withholds():
    assert memory_writer_v4.prepare_operations(SOURCE)["operations"] == []
    plan = memory_writer_v5.prepare_operations(SOURCE)
    assert plan["version"] == "typed_memory_v5" and len(plan["operations"]) == 1
    operation = plan["operations"][0]
    assert (
        operation["scope"] == "biology"
        and operation["content"] == operation["source_quote"] == SOURCE
    )
    assert operation["field_key"] == "detail_level" and operation["operation"] == "ADD"
    assert not plan["withheld"]


def test_old_v4_policy_and_recorded_behavior_replay_without_new_recognition(tmp_path):
    assert memory_v4.condition(SOURCE, SOURCE)[0] is None
    path = tmp_path / "recorded-v4.json"
    path.write_text(json.dumps(memory_v4.freeze_policy()), encoding="utf-8")
    assert memory_policy.selector_for_policy(memory_policy.load_policy(path)) is memory_v4
    assert memory_policy.selector_for_policy(memory_v3.freeze_policy()) is memory_v3
    assert memory_policy.selector_for_policy(memory_policy.load_policy()) is memory_v5
    assert memory_v5.freeze_policy()["writer_version"] == memory_writer_v5.WRITER_VERSION


@pytest.mark.parametrize(
    "field,value",
    [
        ("writer_version", "typed_memory_v4"),
        ("selector_version", "query_conditioned_memory_v4"),
        ("max_source_bytes", 1),
        ("version", "owned_preference_conditions_v999"),
    ],
)
def test_new_policy_identity_tampering_never_falls_back_to_an_old_selector(field, value):
    policy = memory_v5.freeze_policy()
    policy[field] = value
    with pytest.raises(ValueError):
        memory_policy.selector_for_policy(policy)


def test_saved_subject_overrides_concise_profile_and_current_instruction_overrides_saved_subject():
    entry = record()
    before = deepcopy(entry)
    result = select([entry], "Explain how photosynthesis stores energy in biology.")
    assert result.state["version"] == "query_conditioned_memory_v5"
    assert [e["id"] for e in result.state["entries"]] == [entry["id"]]
    fields = {e["field_key"]: e for e in result.state["fields"]}
    assert fields["detail_level"]["scope"] == "biology"
    assert fields["detail_level"]["source"] == {"memory_id": entry["id"], "version": 1}
    assert result.state["entries"][0]["content"] == SOURCE
    short = select([entry], "Explain photosynthesis. Give a short explanation.")
    assert short.state["fields"][0]["verification"] == "current_user_instruction"
    assert entry == before
    assert not select([entry], "Explain sodium orbitals in chemistry.").state["entries"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("owned", False),
        ("source_hash", "0" * 64),
        ("memory_version", 9),
        ("source_message_id", "foreign"),
    ],
)
def test_source_identity_mismatch_withholds_even_when_topic_matches(field, value):
    entry = record()
    original = reader(SOURCE)(entry)
    original[field] = value
    assert not select([entry], "Explain photosynthesis.", source_reader=lambda _: original).state[
        "entries"
    ]


@pytest.mark.parametrize("status", ["paused", "deleted"])
def test_pause_or_erasure_removes_the_selected_source(status):
    entry = record()
    entry["status"] = status
    assert not select([entry], "Explain photosynthesis.").state["entries"]


def test_new_writer_does_not_reinterpret_erasure_or_conditional_delete():
    text = "Delete my detailed explanations for biology."
    old = memory_writer_v4.prepare_operations(text)
    new = memory_writer_v5.prepare_operations(text)
    assert new["operations"] == old["operations"]
    conditional = "For biology, delete my detailed explanations."
    assert memory_writer_v5.prepare_operations(conditional)["operations"] == []


@pytest.mark.parametrize(
    "mutation", [None, "foreign_actor", "missing_revision", "wrong_scope", "wrong_canonical"]
)
def test_owned_correction_chain_is_still_independent_of_the_original_chat(mutation):
    from tests.unit.test_memory_v4 import correction_fixture

    entry, revisions, events, key = correction_fixture(controls=2)
    if mutation == "foreign_actor":
        events[entry["version"]]["owner_id"] = "someone-else"
    elif mutation == "missing_revision":
        revisions.pop(1)
    elif mutation == "wrong_scope":
        revisions[-1]["details"]["scope"] = "chemistry"
    elif mutation == "wrong_canonical":
        key = rules.canonical(entry["category"], entry["field_key"], "chemistry")
    actual = memory_v5.correction_source(entry, "author-owner", revisions, events, key)
    assert (actual is not None) is (mutation is None)
    if actual:
        assert actual["content"] == entry["content"] and actual["source_kind"] == "user_correction"
        assert actual["verified_scope"] == "biology" and actual["revision_version"] == 2
