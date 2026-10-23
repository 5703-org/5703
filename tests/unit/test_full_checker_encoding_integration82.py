"""Actual full-checker integration with authored in-memory provider fixtures.

No model, database or authentication service is used. Local transport and gate
results are not semantic quality ratings or an answer-latency measurement.
"""

import ast
from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import generation
from generation import GenerationService, ModelConfig, RequestBudget
from generation import checker_encoding as legacy
from generation.checker_contract import SCHEMA_CORRECTIONS_POLICY
from generation.checker_encoding_v2 import VERSION, decode
from generation.checked import generate_checked
from app.modules.answering.qualification_transport import (
    submission_fields as qualification_transport_submission_fields,
)
from generation.coverage_query_policy_v1 import submission_fields
from generation.source_relations_v2 import checker_schema_submission_fields
from generation.teaching_plan_v10 import freeze_generation_policy
from test_answer_core_v5 import req
from test_enhancement_generation import Script, answer
from test_source_relation_units_v2 import unit_checker

MAIN = Path(generation.__file__).resolve().parents[1]
V1 = legacy.VERSION
SOURCE_POLICY = "source_relation_contract_v2"
BODY = " ".join(["Photosynthesis uses light energy. [ev_001]"] * 8)


def request_fixture(**changes):
    values = {
        "checker_payload_policy": VERSION,
        "joint_checker_policy": "typed_joint_v5",
        "source_relation_policy": SOURCE_POLICY,
        "checker_contract_policy": SCHEMA_CORRECTIONS_POLICY,
        "config": ModelConfig(window_tokens=65536, tokenizer_provider="estimate"),
    }
    values.update(changes)
    reliability = values.pop("reliability_policy", "evidence_reliability_v5")
    return replace(req(**values), reliability_policy=reliability)


def packet(messages):
    data = json.loads(messages[-1]["content"])
    if "CHECKER_INPUT_ENCODING" in data:
        data = (
            decode(data)
            if data["CHECKER_INPUT_ENCODING"]["version"] == VERSION
            else legacy.decode(data)
        )
    if "SOURCE_FRAGMENT_TABLE" in data:
        table = data.pop("SOURCE_FRAGMENT_TABLE")
        data["SOURCE_FRAGMENTS"] = [
            dict(zip(table["columns"], row, strict=True)) for row in table["rows"]
        ]
    return data


def full_judgment(messages):
    # The mock judges the reconstructed full packet through the existing authored
    # full v5/unit fixture, while the captured call retains the actual wire schema.
    return unit_checker([{"role": "user", "content": json.dumps(packet(messages))}])


def run(policy, callback=full_judgment, body=BODY):
    adapter = Script([answer(body), callback])
    outcome = GenerationService(adapter=adapter, checker_adapter=adapter).generate(
        request_fixture(checker_payload_policy=policy), RequestBudget(max_calls=2)
    )
    return outcome, adapter


def test_explicit_v2_keeps_complete_full_schema_and_exact_unencoded_validation_inputs():
    old, old_adapter = run(V1)
    new, new_adapter = run(VERSION)
    assert old.succeeded and new.succeeded, (old.error, new.error)
    assert new.response == old.response
    assert old.budget["consumed_calls"] == new.budget["consumed_calls"] == 2
    old_messages, old_kwargs = old_adapter.calls[1]
    new_messages, new_kwargs = new_adapter.calls[1]
    assert old_kwargs["response_schema"] == new_kwargs["response_schema"]
    assert (
        old_kwargs["response_schema_name"]
        == new_kwargs["response_schema_name"]
        == "joint_check_source_relations_v2"
    )
    assert old_messages[0] == new_messages[0]
    assert packet(old_messages) == packet(new_messages)
    assert new.checks[0]["actual_citation_bindings"] == old.checks[0]["actual_citation_bindings"]
    assert (
        new.checks[0]["source_relation_assessment"] == old.checks[0]["source_relation_assessment"]
    )
    assert "COMPACT_CONTRACT" not in packet(new_messages)
    for messages, kwargs in (old_adapter.calls[1], new_adapter.calls[1]):
        assert "attempt_evaluation_ok" in kwargs["response_schema"]["required"]
        assert len(packet(messages)["SOURCE_SYNTACTIC_UNITS"]) == 8
    report = new.token_budget["checker_payload_encodings"][0]
    actual_encoding = json.loads(new_messages[-1]["content"])["CHECKER_INPUT_ENCODING"]["version"]
    assert report["encoding"] == actual_encoding == VERSION
    assert report["saved_encoding_policy"] == VERSION
    assert report["local_semantic_support_certified"] is False


def test_small_v2_candidate_reports_actual_legacy_fallback_instead_of_relabeling():
    out, adapter = run(VERSION, body="Photosynthesis uses light energy. [ev_001]")
    assert out.succeeded, out.error
    report = out.token_budget["checker_payload_encodings"][0]
    raw = json.loads(adapter.calls[1][0][-1]["content"])
    actual = raw.get("CHECKER_INPUT_ENCODING", {}).get(
        "version",
        "lossless_fragment_table" if "SOURCE_FRAGMENT_TABLE" in raw else "fragment_objects",
    )
    assert report["encoding"] == actual
    assert report["encoding"] != VERSION
    assert report["saved_encoding_policy"] == VERSION


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_v2_round_trip_does_not_promote_valid_negative_unit_or_fill_its_sources(status):
    reason = "Authored missing-condition fixture; preserve this exact reason."

    def rejected(messages):
        judgment = full_judgment(messages)
        judgment["claims"][0]["units"][0].update(status=status, fragment_ids=[], reason=reason)
        return judgment

    out, adapter = run(VERSION, rejected)
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.response is None and not out.delivered_projection
    assessment = out.checks[0]["source_relation_assessment"]
    assert not assessment["accepted"]
    unit = assessment["claims"][0]["obligations"][0]
    assert unit["status"] == status and unit["reason"] == reason
    assert unit["fragment_ids"] == [] and unit["source_quotes"] == []


@pytest.mark.parametrize(
    "fault", ["missing_unit", "foreign_unit", "foreign_source", "unsupported_optimistic_unit"]
)
def test_v2_reference_reconstruction_never_overrides_invalid_or_negative_checker_output(fault):
    def rejected(messages):
        value = full_judgment(messages)
        row = value["claims"][0]
        if fault == "missing_unit":
            row["units"] = []
        elif fault == "foreign_unit":
            row["units"][0]["unit_id"] = "U999"
        elif fault == "foreign_source":
            row["units"][0]["fragment_ids"] = ["F999"]
        else:
            row["units"][0].update(status="unsupported", relation_preserved=False)
        assert row["status"] == "supported" and value["body_ok"] is True
        return value

    out, adapter = run(VERSION, rejected)
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert out.response is None and not out.delivered_projection
    assert out.error["code"] == (
        "SEMANTIC_CHECK_FAILED"
        if fault == "unsupported_optimistic_unit"
        else "CHECKER_INCONSISTENT"
    )
    assert out.checks[0]["accepted"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"joint_checker_policy": "scoped_compact_v6"},
        {"joint_checker_policy": "typed_joint_v10"},
        {"source_relation_policy": None},
        {"source_relation_policy": "source_relation_contract_v1"},
        {"source_relation_policy": "future_source_contract"},
        {"reliability_policy": "evidence_reliability_v4"},
        {"reliability_policy": "legacy_joint_v1"},
    ],
)
def test_incompatible_v2_full_requests_fail_before_any_scripted_provider_call(changes):
    adapter = Script([])
    out = GenerationService(adapter=adapter, checker_adapter=adapter).generate(
        request_fixture(**changes), RequestBudget(max_calls=4)
    )
    assert out.error["code"] == "CHECKER_PAYLOAD_POLICY_INCOMPATIBLE"
    assert out.budget["consumed_calls"] == 0 and adapter.calls == []
    assert out.response is None and not out.attempts


@pytest.mark.parametrize("changes", [{"enhancement_version": None}, {"mode": "benchmark_mcq"}])
def test_v2_cannot_bypass_the_checked_lane_by_selecting_legacy_dispatch(changes):
    adapter = Script([])
    out = GenerationService(adapter=adapter).generate(
        request_fixture(**changes), RequestBudget(max_calls=4)
    )
    assert out.error["code"] == "CHECKER_PAYLOAD_POLICY_INCOMPATIBLE"
    assert out.budget["consumed_calls"] == 0 and adapter.calls == []


def test_foreign_payload_policy_preserves_old_fail_closed_zero_call_behavior():
    adapter = Script([])
    out = GenerationService(adapter=adapter).generate(
        request_fixture(checker_payload_policy="future_full_encoding"), RequestBudget(max_calls=4)
    )
    assert out.error and out.response is None
    assert out.budget["consumed_calls"] == 0 and adapter.calls == []


def test_v2_full_input_rejects_research_unchecked_and_compact_wire_at_checked_entry():
    config = ModelConfig(
        provider="openai_compatible",
        model="google/gemini-3.5-flash-lite",
        base_url="https://openrouter.ai/api/v1",
        openrouter_route_profile="gemini35_google_vertex_compact_checker_v3",
        temperature=None,
        reasoning_effort="low",
    )
    for changes, research in (({}, True), ({"checker_config": config}, False)):
        adapter = Script([])
        out = generate_checked(
            GenerationService(adapter=adapter),
            request_fixture(**changes),
            RequestBudget(max_calls=4),
            research_unchecked=research,
        )
        assert out.error["code"] == "CHECKER_PAYLOAD_POLICY_INCOMPATIBLE"
        assert out.budget["consumed_calls"] == 0 and adapter.calls == []


def settings(values=None):
    path = MAIN / "backend/app/core/config.py"
    spec = importlib.util.spec_from_file_location("checker82_no_environment_settings", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Run the actual Pydantic defaults and validators without BaseSettings' env,
    # dotenv, file-secret or other configuration sources.
    instance = module.Settings.__new__(module.Settings)
    return module.Settings.__pydantic_validator__.validate_python(
        values or {}, self_instance=instance
    )


def test_backend_default_and_request_legacy_default_are_retained():
    assert settings().chat_checker_payload_policy == V1
    assert req().checker_payload_policy == legacy.LEGACY
    old, adapter = run(legacy.LEGACY)
    assert old.succeeded, old.error
    assert old.token_budget["checker_payload_policy"] == legacy.LEGACY
    assert old.token_budget["checker_payload_encodings"][0]["encoding"] == "fragment_objects"
    assert "CHECKER_INPUT_ENCODING" not in json.loads(adapter.calls[1][0][-1]["content"])


@pytest.mark.parametrize(
    "values",
    [
        {"chat_checker_payload_policy": VERSION},
        {
            "chat_checker_payload_policy": VERSION,
            "chat_source_relation_policy": "source_relation_contract_v1",
        },
        {
            "chat_checker_payload_policy": VERSION,
            "chat_source_relation_policy": SOURCE_POLICY,
            "chat_joint_checker_policy": "typed_joint_v10",
        },
        {"chat_checker_payload_policy": "future_full_encoding"},
    ],
)
def test_settings_reject_foreign_encoding_or_incompatible_full_policy(values):
    with pytest.raises(ValueError):
        settings(values)


def frozen_submission_command(current_settings):
    # Evaluate the actual submit_chat command expression, with every dependency
    # supplied in memory. This tests policy freezing with pure service helpers but no
    # database, model configuration, profile or memory/authentication access.
    tree = ast.parse(
        (MAIN / "backend/app/modules/answering/service.py").read_text(encoding="utf-8")
    )
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "submit_chat"
    )
    request_call = next(
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "AnswerRequest"
    )
    expression = next(
        keyword.value for keyword in request_call.keywords if keyword.arg == "command"
    )
    from generation.checker_encoding_assertions_v3 import (
        submission_policy as assertion_checker_submission_policy,
    )
    from app.modules.answering import service as submission

    ns = {
        "assertion_fields": {},
        "assertion_checker_submission_policy": assertion_checker_submission_policy,
        "checker_claim_policy": None,
        "verification_mode": "verified",
        "verification_policy": "ordinary_checkbox_v1",
        **{
            name: getattr(submission, name)
            for name in (
                "completeness_submission_fields",
                "_provider_output_submission_policy",
                "_repair_submission_policy",
            )
        },
        "settings": current_settings,
        "body": SimpleNamespace(
            content="An authored question.",
            use_profile=False,
            answer_mode="textbook",
            check_answer=True,
        ),
        "teaching": None,
        "reading_context": None,
        "memory_snapshot": None,
        "memory_policy_version": "disabled_fixture",
        "memory_selection_policy": {},
        "memory_stage": {"status": "disabled"},
        "checker_config": ModelConfig(),
        "selected_config": ModelConfig(),
        "retrieval_policy": None,
        "teaching_plan_v10": SimpleNamespace(freeze_generation_policy=freeze_generation_policy),
        "coverage_query_submission_fields": submission_fields,
        "checker_schema_submission_fields": checker_schema_submission_fields,
        "qualification_transport_submission_fields": qualification_transport_submission_fields,
        "freeze_practice_query": lambda value: None,
        "freeze_restatement_context": lambda *args: {},
        "freeze_selection": lambda value: {},
        "freeze_relevance_policy": lambda value: {},
        "freeze_facet_fallback": lambda value: {},
        "db": None,
        "actor": None,
        "session_id": "fixture",
        "rows": [],
        "context": {},
        "cs": SimpleNamespace(content_hash="fixture"),
        "REQUIREMENTS_V4": "question_requirements_v4",
        "PREPARATION_VERSION": "fixture",
    }
    ns.update(
        {
            f"query_v{version}": SimpleNamespace(VERSION=f"query_v{version}")
            for version in range(14, 27)
        }
    )
    return eval(compile(ast.Expression(expression), "actual_submit_chat_command", "eval"), ns)


def test_actual_submit_command_freezes_explicit_setting_without_changing_other_fields():
    v1_settings = settings({"chat_source_relation_policy": SOURCE_POLICY})
    v2_settings = settings(
        {"chat_checker_payload_policy": VERSION, "chat_source_relation_policy": SOURCE_POLICY}
    )
    old = frozen_submission_command(v1_settings)
    new = frozen_submission_command(v2_settings)
    assert old["checker_payload_policy"] == V1 and new["checker_payload_policy"] == VERSION
    assert {key: value for key, value in old.items() if key != "checker_payload_policy"} == {
        key: value for key, value in new.items() if key != "checker_payload_policy"
    }
    v2_settings.chat_checker_payload_policy = V1
    assert new["checker_payload_policy"] == VERSION
    assert frozen_submission_command(v2_settings)["checker_payload_policy"] == V1
