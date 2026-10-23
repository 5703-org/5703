"""Source-part eligibility never certifies source existence or scientific support."""

import pytest
from conversation import query_v27, query_v28

POSITIVE = [
    "Using Table 7.3, compare the recorded speeds. State the measurement conditions specified in its footnote.",
    "Using Ecology Figure 8.4, describe the plotted trend. Explain the uncertainty convention mentioned in its caption.",
    "Using Table 7.3, compare the recorded speeds and state the units from its footnote.",
    "Using Ecology Figure 8.4, describe the plotted trend and explain its caption.",
    "Using Physics Chapter 9, name the topic given by its title.",
    "Using Statistics Section 3.2, identify the assumptions stated in its note.",
]


@pytest.mark.parametrize("question", POSITIVE)
@pytest.mark.parametrize(
    "history",
    [
        [],
        [
            {
                "role": "user",
                "content": "Explain the boiling point of ethanol.",
                "message_id": "unrelated",
            }
        ],
    ],
)
def test_numbered_source_and_structural_possessive_remain_verbatim(question, history):
    result = query_v28.prepare_query(question, history)
    assert not result.needs_clarification
    assert result.standalone_query == question and result.referenced_message_ids == []
    audit = query_v28.source_reference_audit(question)
    assert audit and audit["eligibility_only"] and not audit["source_existence_verified"]
    for span in audit["referent_spans"]:
        assert question[span["owner_start"] : span["owner_end"]] == span["owner_text"]
        assert question[span["start"] : span["end"]] == "its"
    req = query_v28.describe_requirements(question, result.model_dump(), history)
    assert req["preparation_dependency"]["frozen_preparation_version"] == query_v28.VERSION


NEGATIVE = [
    "Using Table 2.1 and Table 2.2, explain its note.",
    "Using Table 2.1 and a figure, explain its caption.",
    "Using Table 2.1, explain that and its note.",
    "Using Table 2.1, explain its rate.",
    "Using Table 2.1, do not use its note.",
    "Without Table 2.1, explain its note.",
    "Using the previous Table 2.1, explain its note.",
    'Using Table 2.1, explain "its note" and its meaning.',
    "Using Table 2.1, explain its note and their units.",
    "Explain its note using Table 2.1.",
    "Using a table, explain its note.",
    "Using Table 2.1, a caption and a footnote are inconsistent. Explain its title.",
    "Using Table 2.1, compare another table with its note.",
    "Using Table 2.1, ignore the figure and explain its note.",
]


@pytest.mark.parametrize("question", NEGATIVE)
def test_competing_quoted_negative_external_or_nonstructural_references_remain_frozen(
    question,
):
    assert query_v28.source_reference_audit(question) is None
    before = query_v27.prepare_query(question).model_dump()
    after = query_v28.prepare_query(question).model_dump()
    after["preparation_version"] = before["preparation_version"]
    assert after == before


def test_old_policy_and_saved_versions_unchanged():
    for question in [
        "Explain osmosis.",
        "Why does it do that?",
        "For a confined gas, what happens to its volume?",
    ]:
        before = query_v27.prepare_query(question).model_dump()
        after = query_v28.prepare_query(question).model_dump()
        after["preparation_version"] = before["preparation_version"]
        assert before == after
    with pytest.raises(ValueError):
        query_v28.prepare_query(POSITIVE[0], version=query_v27.VERSION)
