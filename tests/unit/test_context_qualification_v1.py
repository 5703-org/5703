"""Real pipeline integration with authored judgments, not model-quality scores."""

from copy import deepcopy
import json
import socket

import pytest

from generation import GenerationService, RequestBudget
from generation import ModelConfig, adapters
from generation.local_repair import VERSION as REPAIR
from generation.source_relations_v2 import QUALIFICATION_POLICY, VERSION
from retrieval.source_spans import text_hash
from test_enhancement_generation import Script, answer
from test_source_relation_contract import check_input
from test_source_relation_units_v2 import request_fixture, unit_checker


SOURCE = "Photosynthesis uses light energy. Carbon dioxide supplies carbon for sugar."


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Qualification integration controls cannot use network or DNS")

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)


def request(**changes):
    values = dict(
        source_relation_policy=VERSION,
        checker_schema_policy=QUALIFICATION_POLICY,
        teaching_context={"turn_role": "user_question", "teaching_mode": "direct", "help_level": 0},
    )
    values.update(changes)
    return request_fixture(**values)


def verdict(messages, *, status="clear", limitation=None):
    data = check_input(messages)
    value = unit_checker(messages)
    fragments = {f["fragment_id"]: f for f in data["SOURCE_FRAGMENTS"]}
    records = []
    for claim in value["claims"]:
        selected = claim["citations"][0]["fragment_ids"][0]
        source = fragments[selected]
        qualified = status == "needs_qualification"
        records.append(
            dict(
                claim_id=claim["claim_id"],
                citation_support_exists=True,
                context_status=status,
                supporting_quotes=[dict(fragment_id=selected, quote=source["exact_text"])],
                limiting_quotes=[
                    dict(fragment_id=limitation["fragment_id"], quote=limitation["exact_text"])
                ]
                if qualified
                else [],
                qualifiers=[
                    dict(dimension="conditions", restriction="Preserve the supplied condition.")
                ]
                if qualified
                else [],
                minimal_revision="Photosynthesis uses light energy. [ev_001]"
                if qualified
                else None,
                revision_supporting_quotes=[dict(fragment_id=selected, quote=source["exact_text"])]
                if qualified
                else [],
                revision_entailed=True if qualified else None,
                revision_context_status="clear" if qualified else None,
                reason="Authored source/context fixture, not independent science.",
            )
        )
    value["qualification_assessments"] = records
    return value


def source_request(text):
    value = request()
    value.evidence[0]["text"] = text
    value.evidence[0]["text_hash"] = text_hash(text)
    mapping = value.source_map["c1"]
    mapping.update(chunk_text=text, chunk_hash=text_hash(text))
    mapping["units"][0].update(cleaned_text=text, text_hash=text_hash(text))
    mapping["spans"][0].update(end=len(text), chunk_end=len(text))
    return value


def test_supported_precisely_qualified_answer_passes_one_joint_check():
    adapter = Script([answer(), verdict])
    value = request()
    before = deepcopy(value)
    out = GenerationService(adapter).generate(value)
    assert out.succeeded, out.error
    assert value == before
    assert [a["stage"] for a in out.attempts] == ["generation", "joint_check"]
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_context_qualification_v1"
    assert "qualification_assessments" in adapter.calls[1][1]["response_schema"]["properties"]
    assert out.checks[0]["qualification_assessment"]["accepted"]
    for row in out.checks[0]["qualification_assessment"]["claims"]:
        for quote in row["resolved_quotes"]:
            fragment = next(
                f for f in out.attribution["fragments"] if f["fragment_id"] == quote["fragment_id"]
            )
            unit = value.source_map[fragment["chunk_id"]]["units"][0]
            assert quote["quote"] == unit["cleaned_text"][quote["start"] : quote["end"]]
            assert quote["source_unit_id"] == unit["id"]
    assert not out.token_budget["context_qualification"]["scientific_correctness_locally_certified"]


def test_no_limiting_evidence_does_not_invent_restriction_or_reject_clear_support():
    adapter = Script([answer(), verdict])
    out = GenerationService(adapter).generate(request())
    assert out.succeeded
    assert all(
        not c["limiting_quotes"] for c in out.checks[0]["qualification_assessment"]["claims"]
    )
    assert len(adapter.calls) == 2


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "unknown_claim",
        "duplicate_claim",
        "invented_quote",
        "unknown_fragment",
        "model_offsets",
        "limiter_missing",
        "uncited_support",
        "candidate_conflict",
    ],
)
def test_malformed_qualification_fails_without_extra_checker_call(defect):
    def malformed(messages):
        value = verdict(messages)
        row = value["qualification_assessments"][0]
        if defect == "missing":
            value.pop("qualification_assessments")
        elif defect == "unknown_claim":
            row["claim_id"] = "foreign"
        elif defect == "duplicate_claim":
            value["qualification_assessments"].append(deepcopy(row))
        elif defect == "invented_quote":
            row["supporting_quotes"][0]["quote"] = "Not present in any supplied fragment."
        elif defect == "unknown_fragment":
            row["supporting_quotes"][0]["fragment_id"] = "F999"
        elif defect == "model_offsets":
            row["supporting_quotes"][0]["start"] = 0
        elif defect == "limiter_missing":
            row["context_status"] = "needs_qualification"
        elif defect == "uncited_support":
            data = check_input(messages)
            source = next(f for f in data["SOURCE_FRAGMENTS"] if f["fragment_id"] == "F002")
            row["supporting_quotes"][0]["fragment_id"] = "F002"
            row["supporting_quotes"][0]["quote"] = source["exact_text"]
        else:
            row.update(
                context_status="needs_qualification",
                limiting_quotes=deepcopy(row["supporting_quotes"]),
                qualifiers=[dict(dimension="time", restriction="Actual supplied limit")],
                minimal_revision="Candidate.",
                revision_supporting_quotes=deepcopy(row["supporting_quotes"]),
                revision_entailed=True,
                revision_context_status="conflict",
            )
        return value

    adapter = Script([answer(), malformed])
    value = (
        source_request(SOURCE + "\n\nIllumination provides the necessary condition.")
        if defect == "uncited_support"
        else request()
    )
    out = GenerationService(adapter).generate(value)
    assert not out.succeeded and out.response is None
    assert out.error["code"] == "QUALIFICATION_CONTRACT_INVALID"
    if defect == "uncited_support":
        assert "QUALIFICATION_SOURCE_BINDING_INVALID" in json.dumps(out.checks)
    assert len(adapter.calls) == 2
    assert not out.delivered_projection


def repair_case(final_negative=False, protected=True):
    original = "Photosynthesis uses light energy at all times. [ev_001]"
    correct = "Photosynthesis uses light energy. [ev_001]"
    unchanged = "Carbon dioxide supplies carbon for sugar. [ev_001]"
    text = SOURCE + "\n\nLight-dependent reactions require illumination."
    value = source_request(text)
    value.repair_policy = REPAIR
    value.teaching_context = {
        "turn_role": "user_question",
        "teaching_mode": "direct",
        "help_level": 0,
    }

    def check(messages):
        data = check_input(messages)
        limit = next(
            f for f in data["SOURCE_FRAGMENTS"] if "require illumination" in f["exact_text"]
        )
        result = verdict(messages)
        targets = {c["claim_id"] for c in data["CLAIMS"] if "at all times" in c["text"]}
        for row in result["qualification_assessments"]:
            if row["claim_id"] in targets or (final_negative and not targets):
                negative = verdict(messages, status="needs_qualification", limitation=limit)
                row.update(
                    next(
                        c
                        for c in negative["qualification_assessments"]
                        if c["claim_id"] == row["claim_id"]
                    )
                )
        return result

    def patch(messages):
        assert "CONTEXT QUALIFICATION REPAIR" in messages[-1]["content"]
        feedback = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        assert feedback["qualification_assessment"]["accepted"] is False
        good = feedback["protected_exact_claims"]
        assert [c["text"] for c in good] == ([unchanged] if protected else [])
        bad = next(c for c in feedback["original_claims"] if "at all times" in c["text"])
        assert bad["claim_id"] in feedback["editable_claim_ids"]
        assert all(row["status"] == "supported" for row in feedback["judgment"]["claims"])
        return dict(
            edits=[dict(claim_id=bad["claim_id"], replacement_text=correct)], append_answer_text=""
        )

    first = answer(original + ("\n\n" + unchanged if protected else ""))
    adapter = Script([first, check, patch, check])
    out = GenerationService(adapter).generate(value)
    assert len(adapter.calls) == 4
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert "qualification_assessments" in adapter.calls[3][1]["response_schema"]["properties"]
    if not final_negative:
        assert out.succeeded, out.error
        assert out.response["answer_text"] == correct + ("\n\n" + unchanged if protected else "")
        assert out.checks[1]["qualification_assessment"]["accepted"]
        if protected:
            assert len(out.checks[1]["qualification_assessment"]["claims"]) == 2
    else:
        assert not out.succeeded and out.response is None
        assert not out.delivered_projection
    return out


def test_actual_limiting_evidence_routes_local_patch_preserving_and_rechecking_correct_claim():
    out = repair_case()
    assert [c["accepted"] for c in out.checks] == [False, True]


def test_all_source_supported_but_unqualified_claim_can_patch_without_protected_claim():
    repair_case(protected=False)


def test_final_context_failure_blocks_publication_after_patch():
    repair_case(final_negative=True)


def test_default_schema_and_two_call_behavior_remain_unchanged():
    adapter = Script([answer(), unit_checker])
    out = GenerationService(adapter).generate(request_fixture(source_relation_policy=VERSION))
    assert out.succeeded, out.error
    assert "qualification_assessments" not in adapter.calls[1][1]["response_schema"]["properties"]
    assert "CONTEXT QUALIFICATION AUDIT" not in adapter.calls[1][0][0]["content"]
    assert "context_qualification" not in out.token_budget


def test_setting_freezes_new_policy_but_defaults_to_none():
    from backend.app.core.config import Settings
    from generation.source_relations_v2 import checker_schema_submission_fields

    settings = Settings(
        _env_file=None,
        chat_source_relation_policy=VERSION,
        chat_checker_schema_policy=QUALIFICATION_POLICY,
    )
    assert checker_schema_submission_fields(settings.chat_checker_schema_policy) == {
        "checker_schema_policy": QUALIFICATION_POLICY
    }
    assert Settings(_env_file=None).chat_checker_schema_policy is None


def test_actual_adapter_compiles_new_schema_once_before_full_pipeline_validation(monkeypatch):
    captured = []

    class FakeResponse:
        status = 200
        headers = {"x-request-id": "authored-qualification-adapter"}

        def __init__(self, raw):
            self.raw = raw

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return json.dumps(
                {
                    "choices": [{"message": {"content": self.raw}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 20, "total_tokens": 40},
                }
            ).encode()

    def fake_provider(envelope, timeout):
        body = json.loads(envelope.data)
        captured.append(body)
        return FakeResponse(json.dumps(verdict(body["messages"])))

    config = ModelConfig(
        provider="openai_compatible",
        model="deepseek-flash",
        base_url="https://api.deepseek.com/v1",
        thinking_enabled=False,
        structured_output_mode="json_object",
        window_tokens=65536,
        max_tokens=4096,
        tokenizer_provider="estimate",
    )
    monkeypatch.setattr(adapters, "open_provider", fake_provider)
    checker_adapter = adapters.LLMAdapter(config, api_key="synthetic-test-only-not-a-credential")
    out = GenerationService(Script([answer()]), checker_adapter=checker_adapter).generate(
        request(checker_config=config), RequestBudget(max_calls=2)
    )
    assert out.succeeded, out.error
    assert len(captured) == 1
    # DeepSeek's existing compiler preserves complete schema in trusted messages.
    assert "qualification_assessments" in captured[0]["messages"][0]["content"]
    assert captured[0]["response_format"]["type"] == "json_object"
    assert out.checks[0]["qualification_assessment"]["accepted"]


@pytest.mark.parametrize(
    "changes",
    [
        {"condition": "E0"},
        {"checker_output_policy": "single_selection_findings_v2"},
        {"answer_mode": "general_knowledge"},
    ],
)
def test_incompatible_opt_in_stops_before_generation(changes):
    value = request(**changes)
    adapter = Script([])
    out = GenerationService(adapter).generate(value)
    assert not out.succeeded and out.error["code"] in {
        "CHECKER_SCHEMA_SCOPE_INVALID",
        "CHECKER_OUTPUT_POLICY_INCOMPATIBLE",
    }
    assert not adapter.calls
