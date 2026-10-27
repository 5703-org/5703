"""New subject-condition cases; no model or hidden changes to historical policies."""

from copy import deepcopy
import pytest
from personalisation import memory_v5, memory_v6, memory_writer_v5, memory_writer_v6, memory_policy
from test_memory_v5 import record, reader, Counter
from personalisation.compiler import compile_profile


@pytest.mark.parametrize(
    "text,scope",
    [
        ("From now on, I prefer concise chemistry explanations.", "chemistry"),
        ("I prefer detailed biology explanations.", "biology"),
        ("I prefer genetics concise answers.", "genetics"),
        ("I prefer short cellular respiration explanations.", "cellular respiration"),
        ("I prefer brief anatomy answers.", "anatomy"),
        ("I prefer brief physiology explanations.", "physiology"),
        ("I prefer concise explanations.", "global"),
        ("I prefer detailed explanations for biology.", "biology"),
        ("For chemistry, I prefer concise explanations.", "chemistry"),
    ],
)
def test_supported_whole_clause_scope_is_exact(text, scope):
    plan = memory_writer_v6.prepare_operations(text)
    assert len(plan["operations"]) == 1 and not plan["withheld"]
    op = plan["operations"][0]
    assert op["content"] == op["source_quote"] == text and op["scope"] == scope


@pytest.mark.parametrize(
    "text",
    [
        "I prefer concise economics explanations.",
        "I prefer biology and chemistry explanations.",
        "I prefer chemistry analogies.",
        "I prefer concise explanations, such as biology examples.",
        "My tutor said: I prefer concise biology explanations.",
        "I prefer concise chemistry explanations unless the topic is anatomy.",
    ],
)
def test_ambiguous_or_unattributed_conditions_never_become_global(text):
    plan = memory_writer_v6.prepare_operations(text)
    assert not plan["operations"]
    if memory_writer_v5.legacy.infer_field(text) is not None:
        assert plan["withheld"]


def test_old_frozen_policy_and_writer_keep_original_scope():
    text = "From now on, I prefer concise chemistry explanations."
    before = memory_v5.freeze_policy()
    assert memory_writer_v5.prepare_operations(text)["operations"][0]["scope"] == "global"
    assert memory_policy.selector_for_policy(before) is memory_v5
    assert memory_policy.selector_for_policy(memory_v6.freeze_policy()) is memory_v6
    assert memory_v5.freeze_policy() == before


def test_new_selector_applies_subject_even_for_old_misscoped_record_without_mutation():
    text = "I prefer detailed biology explanations."
    entry = record(text, scope="global")
    before = deepcopy(entry)

    def selected(question):
        return memory_v6.select(
            [entry],
            question,
            compile_profile({"style": "concise"}, turn_message=question),
            source_reader=reader(text),
            counter=Counter(),
        ).state

    assert [x["id"] for x in selected("Explain photosynthesis in biology.")["entries"]] == [
        entry["id"]
    ]
    assert selected("Explain acid chemistry.")["entries"] == []
    assert entry == before


def test_user_scope_and_owned_source_binding_remain_required():
    text = "I prefer detailed biology explanations."
    entry = record(text, scope="biology")
    invalid = reader(text)(entry)
    invalid["owned"] = False
    result = memory_v6.select(
        [entry], "Explain photosynthesis.", source_reader=lambda e: invalid, counter=Counter()
    )
    assert not result.state["entries"]
    drift = memory_v6.freeze_policy()
    drift["known_scopes_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        memory_v6.select([], "Explain biology.", policy=drift)


@pytest.mark.parametrize(
    "text",
    [
        "For this answer, use concise biology explanations.",
        "Please explain why chemistry explanations should be concise.",
    ],
)
def test_temporary_or_question_alone_has_no_durable_write(text):
    assert not memory_writer_v6.prepare_operations(text)["operations"]


def test_erasure_is_not_blocked_by_embedded_subject_guard():
    text = "Forget my preference for concise chemistry explanations."
    assert memory_writer_v6.prepare_operations(text) == {
        **memory_writer_v5.prepare_operations(text),
        "version": memory_writer_v6.WRITER_VERSION,
    }


def test_unrecognised_field_does_not_invent_a_preference():
    # Subject syntax alone cannot create a new supported preference field.
    assert not memory_writer_v6.prepare_operations(
        "I prefer step-by-step physiology explanations."
    )["operations"]


@pytest.mark.parametrize("writer", [memory_writer_v5, memory_writer_v6])
@pytest.mark.parametrize(
    "text",
    [
        "I prefer concise explanations.",
        "I prefer concise explanations; do not delete my preference.",
        "My tutor said: delete my concise preference.",
    ],
)
def test_model_operation_label_cannot_authorise_erasure(writer, text):
    proposal = {
        "operation": "DELETE",
        "category": "preference",
        "field_key": "detail_level",
        "content": text,
        "source_quote": text,
        "scope": "global",
        "expires_at": None,
    }
    plan = writer.prepare_operations(text, [proposal])
    assert not plan["operations"] and plan["withheld"]


@pytest.mark.parametrize("writer", [memory_writer_v5, memory_writer_v6])
def test_explicit_owned_erasure_still_admitted(writer):
    text = "Please delete my concise preference."
    plan = writer.prepare_operations(text)
    assert len(plan["operations"]) == 1 and plan["operations"][0]["operation"] == "DELETE"
