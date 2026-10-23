"""Local eligibility preserves text, ambiguity, frozen dispatch and evidence gates."""

from copy import deepcopy
import pytest
from conversation import query_v25, query_v26
from conversation.query import evidence_strategy

R1 = "A student gives one group of seedlings extra light and fertilizer, but gives the comparison group neither. The first group grows faster. Can this comparison isolate the effect of fertilizer? Explain what a control group should retain and describe a comparison that changes only fertilizer."
R2 = "Glucose is more concentrated outside a cell than inside. Explain why it may still need a membrane protein to enter, and compare that movement with the sodium-potassium pump. Include concentration direction, the role of ATP, and the numbers and directions of sodium and potassium ions moved per ATP."
HISTORY = [
    {"role": "user", "content": "Compare diffusion and osmosis.", "message_id": "old-u"},
    {"role": "assistant", "content": "They are different processes.", "message_id": "old-a"},
]


@pytest.mark.parametrize(
    "question",
    [
        R1,
        R2,
        "A report describes one comparison. Can this comparison isolate pressure?",
        'A report describes one comparison. "It is invalid." Can this comparison isolate pressure?',
        "Explain a valve that controls pressure.",
        "Explain a valve that does not control pressure.",
        "Xenon is less concentrated outside a vessel than inside. Explain why it may need an opening to escape, and compare that escape with the sealed vessel.",
        "Xenon is not concentrated outside a vessel. Explain why it does not move.",
    ],
)
@pytest.mark.parametrize("history", [[], HISTORY])
def test_current_reference_keeps_complete_text_and_exact_span_audit(question, history):
    audit = query_v26.local_reference_audit(question)
    assert audit is not None
    for span in audit["referent_spans"]:
        assert question[span["start"] : span["end"]] == span["text"]
        assert question[span["owner_start"] : span["owner_end"]] == span["owner_text"]
    prepared = query_v26.prepare_query(question, history).model_dump()
    assert not prepared["needs_clarification"]
    assert prepared["standalone_query"] == question
    assert prepared["referenced_message_ids"] == []
    assert evidence_strategy(question, prepared) == "retrieve"
    requirements = query_v26.describe_requirements(question, prepared, history)
    assert requirements["requirement_source_text"] == question
    assert requirements["rewrite_audit"]["missing"] == []
    assert requirements["preparation_dependency"]["frozen_preparation_version"] == query_v26.VERSION


@pytest.mark.parametrize(
    "question",
    [
        "What does it do?",
        "Explain that.",
        "A sensor and a monitor are active. Explain why it fails.",
        "One comparison changes temperature. Another comparison changes pressure. Can this comparison isolate pressure?",
        "No comparison was performed. Can this comparison isolate pressure?",
        '"A report describes one comparison." Can this comparison isolate pressure?',
        "```A report describes one comparison.``` Can this comparison isolate pressure?",
        "A report describes one comparison. Can this comparison explain that?",
        "Can this comparison isolate pressure?",
    ],
)
def test_missing_or_multiple_antecedents_still_clarify(question):
    assert query_v26.local_reference_audit(question) is None
    result = query_v26.prepare_query(question).model_dump()
    assert result["needs_clarification"]
    assert evidence_strategy(question, result) == "none"


@pytest.mark.parametrize(
    "question",
    [
        "A sensor is beside a monitor. Explain why it fails.",
        "A sensor is larger than a monitor. Explain why it fails.",
        "A sensor is sensitive. Explain why it fails and compare it with a monitor.",
        "A sensor is sensitive. Explain why it may need a filter to operate and a tube to drain, and compare that operation with a monitor.",
        "Explain the previous valve that controls pressure.",
        '"A sensor is sensitive." Explain why it fails.',
        "Explain a sensor and a monitor, including how it works.",
        "What is osmosis?",
        "Hello!",
    ],
)
@pytest.mark.parametrize("history", [[], HISTORY])
def test_unmatched_rules_preserve_v25_not_a_general_coreference_claim(question, history):
    assert query_v26.local_reference_audit(question) is None
    before = query_v25.prepare_query(question, history).model_dump()
    assert query_v26.prepare_query(question, history).model_dump() == {
        **before,
        "preparation_version": query_v26.VERSION,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("standalone_query", "Changed"),
        ("referenced_message_ids", ["foreign"]),
        ("needs_clarification", True),
        ("topic_relation", "same_topic"),
        ("intent", "factual"),
    ],
)
def test_requirement_audit_rejects_tampering(field, value):
    prepared = query_v26.prepare_query(R1).model_dump()
    prepared[field] = value
    with pytest.raises(ValueError, match="audit is unavailable"):
        query_v26.describe_requirements(R1, prepared)


def test_frozen_v25_stays_failed_baseline_and_versions_are_not_interchangeable():
    for question in [R1, R2]:
        assert query_v25.prepare_query(question).needs_clarification
    with pytest.raises(ValueError, match="Unsupported"):
        query_v26.prepare_query(R1, version=query_v25.VERSION)
    prepared = query_v26.prepare_query(R1).model_dump()
    changed = deepcopy(prepared)
    changed["preparation_version"] = query_v25.VERSION
    with pytest.raises(ValueError, match="Unsupported"):
        query_v26.describe_requirements(R1, changed)
