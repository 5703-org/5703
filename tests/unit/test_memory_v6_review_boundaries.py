"""Independent-review counterexamples; no provider or database required."""

import pytest
from personalisation import memory_v6, memory_writer_v6
from personalisation import memory_source_selection_v1 as selection, memory_extraction


@pytest.mark.parametrize(
    "text",
    [
        "I prefer concise botany examples.",
        "I prefer concise economics summaries.",
        "I prefer concise botany explanations please.",
        "I prefer brief astronomy responses.",
        "I prefer concise geological poems.",
        "I prefer concise explanations with astronomy metaphors.",
    ],
)
def test_unknown_or_unparsed_modifiers_are_not_global(text):
    plan = memory_writer_v6.prepare_operations(text)
    assert not plan["operations"] and plan["withheld"]


@pytest.mark.parametrize(
    "text",
    [
        "I prefer concise explanations.",
        "I prefer detailed examples please.",
        "I prefer diagrams.",
        "I prefer bullet points.",
        "I prefer explanations that use compact language.",
    ],
)
def test_bounded_domain_free_preferences_remain_global(text):
    scope, _, _ = memory_v6.condition(text, text)
    assert scope == "global"


@pytest.mark.parametrize("empty", [False, True])
def test_decoder_rechecks_text_against_frozen_reference(empty):
    old = "I prefer detailed biology explanations."
    new = "I prefer detailed chemistry explanations."
    schema, _, reference = selection.prepare(old, memory_extraction.SCHEMA)
    rows = (
        []
        if empty
        else [
            {
                "operation": "ADD",
                "category": "preference",
                "field_key": "detail_level",
                "source_ref": reference,
                "expires_at": None,
            }
        ]
    )
    with pytest.raises(ValueError, match="MEMORY_SOURCE_SELECTION_IDENTITY"):
        selection.decode({"operations": rows}, new, schema)


def test_complete_statement_size_includes_padding():
    with pytest.raises(ValueError, match="MEMORY_SOURCE_SELECTION_SIZE"):
        selection.prepare(" " * 2001 + "I prefer diagrams.", memory_extraction.SCHEMA)


@pytest.mark.parametrize(
    "text",
    [
        "I prefer analogies.",
        "I prefer plain language.",
        "I prefer examples before formulas.",
    ],
)
def test_unrecognised_global_form_requires_confirmation(text):
    scope, reason, _ = memory_v6.condition(text, text)
    assert scope is None and reason == "memory_scope_requires_confirmation"
