"""Actual teacher/checker adapters with a socket-free authored provider boundary.

The source runner selects the candidate. These controls check schema enforcement
and unchanged original publication gates; they do not rate model source judgment.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import sys

import pytest

import generation
from generation import ModelConfig, RequestBudget, adapters, checked
from generation import lossless_unit_findings_v1 as old
from generation import single_selection_findings_v2 as new
from generation.openrouter_routes import prepare_schema_wire
from generation.providers import payload
from generation.reliability_v4 import compact_schema

sys.path.insert(0, str(Path(generation.__file__).resolve().parents[1] / "tests" / "unit"))
from test_enhancement_generation import answer
from test_full_checker_encoding_integration82 import BODY, full_judgment, packet
from test_lossless_output_integration84 import fixture_request, vertex_config


@pytest.fixture(autouse=True)
def isolate_network_and_clock(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Offline schema controls cannot use sockets or DNS")

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)

    class FixtureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2026, 10, 11, 0, 0, tzinfo=timezone.utc)
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(checked, "datetime", FixtureClock)


def haiku():
    return ModelConfig(
        provider="openai_compatible",
        model="anthropic/claude-haiku-5.5",
        base_url="https://openrouter.ai/api/v1",
        openrouter_route_profile="haiku55_google_vertex_low_v1",
        structured_output_mode="json_schema",
        temperature=None,
        reasoning_effort=None,
        window_tokens=65536,
        tokenizer_provider="estimate",
        configuration_id="authored-teacher-contract88",
    )


class FakeResponse:
    status = 200

    def __init__(self, raw, finish="stop"):
        self.raw, self.finish = raw, finish
        self.headers = {"x-request-id": "authored-teacher-contract88"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return json.dumps(
            {
                "choices": [{"message": {"content": self.raw}, "finish_reason": self.finish}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 20, "total_tokens": 40},
            }
        ).encode("utf-8")


def execute(
    monkeypatch,
    policy,
    *,
    short_answer=None,
    negative=False,
    hint=False,
    general=False,
    teacher_only=False,
):
    changes = {"config": haiku(), "checker_config": vertex_config()}
    if hint:
        changes["teaching_context"] = {
            "teaching_mode": "hint",
            "turn_role": "user_question",
            "current_problem": "What does photosynthesis use?",
        }
    if general:
        changes.update(
            answer_mode="general_knowledge",
            source_relation_policy=None,
            checker_payload_policy="legacy_fragment_table_v1",
            condition="E1",
            evidence=[],
            source_map={},
        )
    request = fixture_request(policy, **changes)
    compiled, schemas, teacher_results = [], [], []

    def fake_provider(envelope, timeout):
        body = json.loads(envelope.data)
        compiled.append(body)
        if body["model"] == request.config.model:
            return FakeResponse(
                json.dumps(answer(BODY, short_answer=short_answer)),
                "length" if teacher_only else "stop",
            )
        findings = full_judgment(body["messages"])
        if negative:
            findings["claims"][0]["units"][0].update(
                status="unsupported",
                fragment_ids=[],
                relation_preserved=False,
                conditions_preserved=False,
                reason="Authored missing condition; retain negative flags.",
            )
        codec = new if policy == new.VERSION else old if policy == old.VERSION else None
        raw = (
            codec.canonical(
                codec.encode_full(findings, codec.build_context(packet(body["messages"])))
            )
            if codec
            else json.dumps(findings)
        )
        return FakeResponse(raw)

    monkeypatch.setattr(adapters, "open_provider", fake_provider)
    teacher = adapters.LLMAdapter(
        request.config, api_key="synthetic-test-only", retain_invalid_output=True
    )
    original_generate = teacher.generate

    def observe(*args, **kwargs):
        schemas.append(kwargs["response_schema"])
        result = original_generate(*args, **kwargs)
        teacher_results.append(result)
        return result

    teacher.generate = observe
    checker = adapters.LLMAdapter(request.checker_config, api_key="synthetic-test-only")
    outcome = generation.GenerationService(adapter=teacher, checker_adapter=checker).generate(
        request, RequestBudget(max_calls=2)
    )
    return outcome, request, compiled, schemas, teacher_results


@pytest.mark.parametrize("policy", [None, old.VERSION, new.VERSION])
def test_direct_schema_and_provider_wire_keep_complete_answer_and_full_gates(monkeypatch, policy):
    outcome, request, compiled, schemas, _ = execute(monkeypatch, policy)
    assert outcome.succeeded, outcome.error
    assert len(compiled) == 2 and len(schemas) == 1
    expected = compact_schema(checked.TeachingDraftV4)
    if policy is not None:
        expected["properties"]["short_answer"] = {"type": "null"}
    assert schemas[0] == expected
    assert {"answer_text", "short_answer"}.issubset(expected["required"])
    assert outcome.response["answer_text"] == BODY and outcome.response["short_answer"] is None
    assert outcome.response["citations"] == ["ev_001"]
    assert outcome.checks[0]["accepted"] is True
    assert outcome.checks[0]["source_relation_assessment"]["accepted"] is True
    assert outcome.checks[0]["checker_inconsistencies"] == []
    actual = compiled[0]["response_format"]["json_schema"]["schema"]
    projected, metadata = prepare_schema_wire(
        request.config, payload(request.config, [], expected, "teaching_draft_v4"), expected
    )
    assert actual == projected["response_format"]["json_schema"]["schema"]
    assert metadata["policy_id"] == "anthropic_structured_bounds_v1"
    if policy is not None:
        assert actual["properties"]["short_answer"] == {"type": "null"}
    else:
        assert {"type": "null"} in actual["properties"]["short_answer"]["anyOf"]


@pytest.mark.parametrize("policy", [old.VERSION, new.VERSION])
def test_explicit_non_null_draft_is_rejected_without_dropping_it_or_calling_checker(
    monkeypatch, policy
):
    outcome, _, compiled, schemas, results = execute(monkeypatch, policy, short_answer=BODY)
    assert not outcome.succeeded and outcome.response is None
    assert len(compiled) == len(schemas) == len(results) == 1
    assert schemas[0]["properties"]["short_answer"] == {"type": "null"}
    assert json.loads(results[0].raw_text)["short_answer"] == BODY
    assert outcome.budget["consumed_calls"] == 1
    assert outcome.error["code"] == "SCHEMA_VALIDATION"


def test_default_still_accepts_the_original_non_null_field(monkeypatch):
    outcome, _, compiled, schemas, _ = execute(monkeypatch, None, short_answer=BODY)
    assert outcome.succeeded, outcome.error
    assert len(compiled) == 2
    assert schemas[0] == compact_schema(checked.TeachingDraftV4)
    assert outcome.response["short_answer"] == BODY


@pytest.mark.parametrize("policy", [old.VERSION, new.VERSION])
def test_null_draft_does_not_upgrade_unsupported_relation_or_condition_flags(monkeypatch, policy):
    baseline, _, _, _, _ = execute(monkeypatch, None, negative=True)
    outcome, _, compiled, _, _ = execute(monkeypatch, policy, negative=True)
    assert len(compiled) == outcome.budget["consumed_calls"] == 2
    assert outcome.error["code"] == baseline.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert outcome.response is baseline.response is None
    assert not outcome.delivered_projection
    assert (
        outcome.checks[0]["source_relation_assessment"]
        == baseline.checks[0]["source_relation_assessment"]
    )
    unit = outcome.checks[0]["source_relation_assessment"]["claims"][0]["obligations"][0]
    assert unit["status"] == "unsupported" and unit["fragment_ids"] == []
    assert unit["relation_preserved"] is unit["conditions_preserved"] is False


@pytest.mark.parametrize("policy", [old.VERSION, new.VERSION])
def test_non_direct_teacher_schema_remains_unchanged(monkeypatch, policy):
    outcome, _, compiled, schemas, _ = execute(monkeypatch, policy, hint=True, teacher_only=True)
    assert len(compiled) == len(schemas) == 1
    assert schemas[0] == compact_schema(checked.TeachingDraftV4)
    assert not outcome.succeeded


def test_general_default_schema_and_both_explicit_general_refusals_remain_unchanged(monkeypatch):
    _, _, compiled, schemas, _ = execute(monkeypatch, None, general=True, teacher_only=True)
    assert len(compiled) == len(schemas) == 1
    assert schemas[0] == compact_schema(checked.TeachingDraftV4)
    for policy in (old.VERSION, new.VERSION):
        outcome, _, compiled, schemas, _ = execute(monkeypatch, policy, general=True)
        assert outcome.error["code"] == "CHECKER_OUTPUT_POLICY_INCOMPATIBLE"
        assert compiled == schemas == [] and outcome.budget["consumed_calls"] == 0
