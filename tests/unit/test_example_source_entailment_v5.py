"""Authored native contract fixtures; verdicts are not model-accuracy measurements."""

import json

import pytest

from generation import GenerationService, RequestBudget
from generation.adapters import chat_value
from generation.checker_encoding import decode
from retrieval.source_spans import text_hash
from test_answer_core_v5 import checker
from test_enhancement_generation import Script, request

SOURCE = (
    "Photosynthesis captures light energy and stores chemical energy in sugars. "
    "Light supplies energy to convert carbon dioxide and water into sugars. Oxygen is released."
)
QUESTION = (
    "I prefer examples for photosynthesis. Explain how sunlight supplies energy "
    "for photosynthesis in the selected passage."
)
PARAPHRASE = "Sunshine provides the energy that turns carbon dioxide and water into sugars, storing chemical energy. [ev_001]"
REVERSED = "Light supplies energy to convert sugars into carbon dioxide and water, storing chemical energy. [ev_001]"
MECHANISM = "Light supplies energy to convert carbon dioxide and water into sugars by splitting water and using ATP. [ev_001]"
COMPOUND = "Light supplies energy to convert carbon dioxide and water into sugars; for example, green plants take in carbon dioxide through stomata. [ev_001]"
OUTSIDE = (
    "General knowledge, unverified by this passage: chlorophyll absorbs light in green leaves."
)


def source_request(*, general=False):
    value = request(
        question=QUESTION,
        reliability_policy="evidence_reliability_v5",
        joint_checker_policy="typed_joint_v5",
        checker_payload_policy="legacy_fragment_table_v1",
    )
    if general:
        value.answer_mode, value.evidence, value.source_map = "general_knowledge", [], {}
    else:
        value.evidence[0].update(text=SOURCE, text_hash=text_hash(SOURCE))
        mapping = value.source_map["c1"]
        mapping.update(chunk_text=SOURCE, chunk_hash=text_hash(SOURCE))
        mapping["units"][0].update(cleaned_text=SOURCE, text_hash=text_hash(SOURCE))
        mapping["spans"][0].update(end=len(SOURCE), chunk_end=len(SOURCE))
    assert len(SOURCE) == 165
    return value


def checker_data(messages):
    data = json.loads(messages[-1]["content"])
    if "CHECKER_INPUT_ENCODING" in data:
        data = decode(data)
    if "SOURCE_FRAGMENT_TABLE" in data:
        table = data["SOURCE_FRAGMENT_TABLE"]
        data["SOURCE_FRAGMENTS"] = [
            dict(zip(table["columns"], row, strict=True)) for row in table["rows"]
        ]
    return data


def judgment(*, status="supported", reason="Authored meaning-preserving entailment fixture."):
    def authored(messages):
        value = checker(messages)
        for claim in value["claims"]:
            if claim["basis"] in {"textbook", "general_knowledge"}:
                claim.update(status=status, reason=reason)
        value["body_ok"] = status == "supported"
        value["reason"] = "Authored contract verdict, not an independent semantic measurement."
        return value

    return authored


def run_native(sequence, *, general=False, calls=2):
    script = Script(sequence)
    outcome = GenerationService(adapter=script, checker_adapter=script).generate(
        source_request(general=general), RequestBudget(max_calls=calls, max_active_seconds=180)
    )
    return outcome, script


def draft(text, *, cited=True):
    value = chat_value("answer", text, citations=["ev_001"] if cited else [])
    value.update(tutor_question=None, learner_attempt_evaluation=None)
    return value


def capture(record_property, name, outcome, script):
    assert (
        "In textbook mode, examples, analogies and paraphrases must preserve"
        in script.calls[0][0][0]["content"]
    )
    checker_calls = [
        row
        for row in script.calls
        if row[1]["request_context"]["purpose"] in {"joint_check", "joint_recheck"}
    ]
    assert checker_calls
    snapshots = []
    for messages, kwargs in checker_calls:
        assert "inspect every asserted predicate" in messages[0]["content"]
        assert kwargs["response_schema_name"] == "joint_check_v5"
        data = checker_data(messages)
        assert type(data["CLAIMS"]) is list and data["CLAIMS"]
        snapshots.append(
            {
                "purpose": kwargs["request_context"]["purpose"],
                "full_claims": data["CLAIMS"],
                "actual_citation_bindings": data["ACTUAL_CITATION_BINDINGS"],
                "complete_source_fragments": data["SOURCE_FRAGMENTS"],
            }
        )
    record_property(
        "authored_native_proof",
        json.dumps(
            {
                "control": name,
                "succeeded": outcome.succeeded,
                "error_code": (outcome.error or {}).get("code"),
                "native_stages": [
                    kwargs["request_context"]["purpose"] for _messages, kwargs in script.calls
                ],
                "captured_native_messages": [
                    {
                        "messages": messages,
                        "purpose": kwargs["request_context"]["purpose"],
                        "schema_name": kwargs["response_schema_name"],
                    }
                    for messages, kwargs in script.calls
                ],
                "immutable_checker_inputs": snapshots,
                "fixture_verdict_is_semantic_accuracy_evidence": False,
            }
        ),
    )


def test_meaning_preserving_example_paraphrase_succeeds_without_lexical_identity(record_property):
    out, script = run_native([draft(PARAPHRASE), judgment()])
    assert out.succeeded, out.error
    assert "Sunshine" not in SOURCE
    assert out.checks[-1]["accepted"] is True
    assert checker_data(script.calls[1][0])["CLAIMS"][0]["text"] == PARAPHRASE
    capture(record_property, "faithful_paraphrase", out, script)


@pytest.mark.parametrize(
    "text,reason,name",
    [
        (
            REVERSED,
            "Conversion direction is reversed although source words overlap.",
            "reversed_relation",
        ),
        (
            MECHANISM,
            "Water splitting and ATP require additional unprovided mechanistic evidence.",
            "added_mechanism",
        ),
    ],
)
def test_shared_words_do_not_establish_unsupported_relations_or_mechanisms(
    record_property, text, reason, name
):
    out, script = run_native([draft(text), judgment(status="unsupported", reason=reason)])
    assert not out.succeeded and out.response is None and not out.delivered_projection
    assert out.checks[0]["accepted"] is False
    assert checker_data(script.calls[1][0])["CLAIMS"][0]["text"] == text
    capture(record_property, name, out, script)


def test_compound_example_partial_verdict_causes_one_bounded_repair(record_property):
    out, script = run_native(
        [
            draft(COMPOUND),
            judgment(
                status="partial",
                reason="The conversion core is supported; the stomata intake example needs outside assumptions.",
            ),
            draft(PARAPHRASE),
            judgment(),
        ],
        calls=4,
    )
    assert out.succeeded, out.error
    assert [kwargs["request_context"]["purpose"] for _messages, kwargs in script.calls] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert checker_data(script.calls[1][0])["CLAIMS"][0]["text"] == COMPOUND
    assert out.checks[0]["accepted"] is False and out.checks[-1]["accepted"] is True
    assert out.checks[0]["semantic_sufficiency"]["status"] == "sufficient"
    assert all(
        not row["missing_information"]
        for row in out.checks[0]["semantic_sufficiency"]["requirements"]
    )
    assert "stomata" not in out.response["answer_text"]
    capture(record_property, "honest_compound_partial_repair", out, script)


def test_explicit_general_knowledge_uncited_has_no_textbook_certification(record_property):
    out, script = run_native([draft(OUTSIDE, cited=False), judgment()], general=True)
    assert out.succeeded, out.error
    assert out.response["citations"] == [] and out.delivered_projection["citation_views"] == []
    assert out.attribution["claims"][0]["support"]["basis"] == "general_knowledge"
    assert out.attribution["claims"][0]["support"]["general_knowledge_status"] == "supported"
    capture(record_property, "explicit_general_knowledge_not_grounded", out, script)


def test_same_external_fact_cannot_acquire_textbook_authority(record_property):
    text = OUTSIDE + " [ev_001]"
    out, script = run_native(
        [
            draft(text),
            judgment(
                status="unsupported",
                reason="The supplied passage does not establish chlorophyll or leaf absorption.",
            ),
        ]
    )
    assert not out.succeeded and out.response is None and not out.delivered_projection
    assert out.checks[0]["accepted"] is False
    assert checker_data(script.calls[1][0])["CLAIMS"][0]["text"] == text
    capture(record_property, "external_fact_misattributed_to_textbook", out, script)
