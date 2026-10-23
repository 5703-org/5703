"""Offline stage-window accounting and safe diagnostics; no answer-quality claims.

Both model roles use authored adapters. Every test fails closed on real transport.
These fixtures establish admission and validation mechanics only.
"""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import socket

import pytest

from app.modules.model_settings.schemas import ModelValues
from app.modules.model_settings.service import presets
from generation import ModelConfig, RequestBudget, teaching_plan_v10
from generation.capabilities import VERSION as CAPABILITY_VERSION, defaults as capability_defaults
from generation.openrouter_routes import BASE_URL, PROFILES, prepare_schema_wire
from generation.providers import payload
from generation.service import GenerationService
from generation.stage_budget_v1 import public_model, window_failure
from generation.token_counting import TokenCounter
from generation.types import ProviderResult, failure
from test_answer_core_v5 import checker as authored_checker
from test_enhancement_generation import answer, request

TEXT = (
    "Photosynthesis is the process in which organisms use light energy to convert carbon dioxide "
    "and water into sugars. It stores energy in chemical bonds and releases oxygen."
)


@pytest.fixture(autouse=True)
def forbid_external_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("OFFLINE_STAGE_BUDGET_TRANSPORT_FORBIDDEN")

    from generation import adapters

    for name in ("getaddrinfo", "create_connection"):
        monkeypatch.setattr(socket, name, forbidden)
    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    monkeypatch.setattr(adapters, "open_provider", forbidden)
    monkeypatch.setattr(adapters.LLMAdapter, "_call", forbidden)
    monkeypatch.setattr(adapters.http, "urlopen", forbidden)


class OfflineAdapter:
    def __init__(self, draft_text=TEXT.replace("sugars.", "sugars. [ev_001]") + " [ev_001]"):
        self.calls = []
        self.draft_text = draft_text

    def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if len(self.calls) == 1:
            return ProviderResult(
                raw_text=json.dumps(answer(self.draft_text)),
                finish_reason="stop",
                provider="offline_authored_fixture",
                model="fixture",
                request_submitted=False,
            )
        return ProviderResult(
            provider="offline_capture",
            model="fixture",
            request_submitted=False,
            error=failure(
                "OFFLINE_CHECK_CAPTURE_STOP", "Reached full checker without provider dispatch"
            ),
        )


class AuthoredGateAdapter(OfflineAdapter):
    def generate(self, messages, **kwargs):
        if not self.calls:
            return super().generate(messages, **kwargs)
        self.calls.append((messages, kwargs))
        judgment = authored_checker(messages)
        if kwargs["response_schema_name"] == "joint_check_v5_ordinary_question_v1":
            judgment["attempt_evaluation_ok"] = "not_applicable"
        return ProviderResult(
            raw_text=json.dumps(judgment),
            provider="offline_authored_checker",
            model="fixture",
            finish_reason="stop",
            request_submitted=False,
        )


def first_request(config=None, teaching_context=None):
    cfg = config or ModelConfig(
        provider="openai_compatible",
        model="openai/gpt-6-luna",
        base_url="https://openrouter.ai/api/v1",
        openrouter_route_profile="openai_luna_v2",
        window_tokens=65536,
        max_tokens=2048,
        temperature=None,
        tokenizer_provider="estimate",
        configuration_id="offline-package-default",
    )
    command = request(
        question="What is photosynthesis?",
        config=cfg,
        checker_config=replace(cfg, max_tokens=max(cfg.max_tokens, 4096)),
        reliability_policy="evidence_reliability_v5",
        generation_policy=teaching_plan_v10.freeze_generation_policy(),
        generation_context_policy="complementary_context_v2",
        source_block_policy="raw_definition_block_partition_v2",
        repair_policy="claim_patch_repair_v3",
        provider_output_policy="json_field_contract_v2",
        joint_checker_policy="typed_joint_v5",
        checker_payload_policy="lossless_checker_tables_v1",
        history=[],
        summary=None,
        memory_context=None,
        teaching_context=teaching_context,
    )
    digest = hashlib.sha256(TEXT.encode()).hexdigest()
    command.evidence[0].update(text=TEXT, text_hash=digest)
    mapping = command.source_map["c1"]
    mapping.update(chunk_text=TEXT, chunk_hash=digest)
    mapping["units"][0].update(cleaned_text=TEXT, text_hash=digest)
    mapping["spans"][0].update(end=len(TEXT), chunk_end=len(TEXT))
    return command


def run(command):
    adapter = OfflineAdapter()
    result = GenerationService(adapter=adapter, checker_adapter=adapter).generate(
        command, RequestBudget()
    )
    return result, adapter


def test_legal_longer_draft_and_multiturn_context_fit_known_working_window():
    context = {
        "turn_role": "user_question",
        "current_step": 1,
        "learner_attempt": None,
        "attempt_history": [],
    }
    command = first_request(teaching_context=context)
    history = [
        {
            "role": role,
            "content": f"Earlier photosynthesis discussion {index}. " + "Context details. " * 7,
        }
        for index in range(5)
        for role in ("user", "assistant")
    ]
    command = replace(command, history=history, summary="Previous photosynthesis discussion. " * 10)
    draft = (TEXT.replace("sugars.", "sugars. [ev_001]") + " [ev_001] ") * 3
    assert TokenCounter(command.config).count(json.dumps(answer(draft))) < command.config.max_tokens
    adapter = OfflineAdapter(draft)
    result = GenerationService(adapter=adapter, checker_adapter=adapter).generate(
        command, RequestBudget()
    )
    assert result.error["code"] == "OFFLINE_CHECK_CAPTURE_STOP", result.error
    assert len(adapter.calls) == 2 and command.history == history
    assert all(
        row["input_reserved_tokens"] + row["output_reserved_tokens"] <= row["window_tokens"]
        for row in result.token_budget["stage_token_budgets"]
    )


def test_native_fresh_task_with_known_direct_luna_working_cap_passes_authored_typed_gate():
    context = {
        "task_id": "00000000-0000-4000-8000-000000000159",
        "task_version": 1,
        "task_revision": 1,
        "exposure_epoch": 0,
        "task_type": "process_reasoning",
        "question": "What is photosynthesis?",
        "current_problem": "What is photosynthesis?",
        "current_request": "What is photosynthesis?",
        "teaching_mode": "direct",
        "help_level": 0,
        "turn_role": "user_question",
        "pending_tutor_question_id": None,
        "pending_tutor_question": None,
        "pending_tutor_question_version": 0,
        "pending_validation_id": None,
        "pending_validation_version": 0,
        "expected_response_kind": None,
        "current_step": 1,
        "learner_attempt": None,
        "last_attempt_evaluation": None,
        "requested_help": "auto",
        "continuing": False,
        "requirements": {"original_question": "What is photosynthesis?"},
        "delivered_turns": [],
        "disclosure_events": [],
        "policy_version": "learning_task_v3",
        "attempt_history": [],
    }
    cfg = ModelConfig(
        provider="openai",
        model="gpt-6-luna",
        base_url="https://api.openai.com/v1",
        window_tokens=65536,
        max_tokens=1024,
        tokenizer_provider="estimate",
    )
    command = first_request(cfg, context)
    adapter = AuthoredGateAdapter()
    result = GenerationService(adapter=adapter, checker_adapter=adapter).generate(
        command, RequestBudget()
    )
    assert result.succeeded, result.error
    assert len(adapter.calls) == 2 and result.checks[-1]["accepted"] is True
    assert result.token_budget["stage_token_budgets"][-1]["output_reserved_tokens"] == 4096


def test_legal_three_thousand_token_evidence_enters_complete_stage_budget():
    command = first_request()
    text = "Photosynthesis uses light energy. " + "a" * (
        1800 - len("Photosynthesis uses light energy. ")
    )
    evidence = []
    source_map = {}
    for index in range(5):
        block = text[:-1] + str(index)
        digest = hashlib.sha256(block.encode()).hexdigest()
        chunk = f"budget-chunk-{index}"
        item = {
            **command.evidence[0],
            "evidence_id": f"ev_{index + 1:03d}",
            "chunk_id": chunk,
            "text": block,
            "text_hash": digest,
            "context_order": index + 1,
        }
        evidence.append(item)
        source_map[chunk] = {
            **command.source_map["c1"],
            "chunk_text": block,
            "chunk_hash": digest,
            "units": [
                {"id": f"unit-{index}", "page": 7, "cleaned_text": block, "text_hash": digest}
            ],
            "spans": [
                {
                    "unit_id": f"unit-{index}",
                    "page": 7,
                    "start": 0,
                    "end": len(block),
                    "chunk_start": 0,
                    "chunk_end": len(block),
                }
            ],
        }
    command = replace(
        command,
        evidence=evidence,
        source_map=source_map,
        generation_context_policy="legacy_context_v1",
    )
    result, adapter = run(command)
    assert result.error["code"] == "OFFLINE_CHECK_CAPTURE_STOP", result.error
    assert len(adapter.calls) == 2
    assert result.token_budget["evidence_tokens"] == 3000
    assert all(item["text"] in json.dumps(adapter.calls[0][0]) for item in evidence)
    assert (
        result.token_budget["submitted_count"] == 0
    )  # The authored seam records no actual provider submission.
    assert all(
        row["input_reserved_tokens"] + row["output_reserved_tokens"] <= row["window_tokens"]
        for row in result.token_budget["stage_token_budgets"]
    )


def test_counter_counts_the_exact_compact_adapter_payload_and_full_schema():
    cfg = first_request().config
    counter = TokenCounter(cfg)
    counted = []
    counter._count = lambda value: counted.append(value) or len(value)
    messages = [
        {"role": "system", "content": "Full instructions"},
        {"role": "user", "content": "Question"},
    ]
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }
    body = payload(cfg, messages, schema, "complete_schema")
    wire = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    assert counter.request_input(messages, schema, "complete_schema") == len(wire) + 128
    assert counted == [wire]
    assert body["response_format"]["json_schema"]["schema"]
    assert cfg.window_tokens == 65536 and cfg.max_tokens == 2048


def test_counter_counts_transformed_schema_exactly_as_the_adapter_wire():
    profile = "haiku55_google_vertex_low_v1"
    cfg = replace(
        first_request().config,
        model=PROFILES[profile].model,
        base_url=BASE_URL,
        openrouter_route_profile=profile,
    )
    counter = TokenCounter(cfg)
    counted = []
    counter._count = lambda value: counted.append(value) or len(value)
    messages = [{"role": "user", "content": "Authored wire count fixture."}]
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string", "minLength": 1, "maxLength": 20}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    original_schema = deepcopy(schema)
    body = payload(cfg, messages, schema, "authored_complete_schema")
    original_body = deepcopy(body)
    wire_body, metadata = prepare_schema_wire(cfg, body, schema)
    wire = json.dumps(wire_body, ensure_ascii=False, separators=(",", ":"))
    assert metadata["removed_bound_count"] == 2
    assert wire_body != body and body == original_body and schema == original_schema
    assert (
        "maxLength=20"
        in wire_body["response_format"]["json_schema"]["schema"]["properties"]["answer"][
            "description"
        ]
    )
    assert counter.request_input(messages, schema, "authored_complete_schema") == len(wire) + 128
    assert counted == [wire]


def test_original_spaced_count_reproduces_old_cap_failure_then_known_working_window_fits(
    monkeypatch,
):
    normal = first_request()
    command = replace(
        normal,
        config=replace(normal.config, window_tokens=16384),
        checker_config=replace(normal.checker_config, window_tokens=16384),
    )
    exact_method = TokenCounter.request_input

    def old_input(self, messages, schema, schema_name="chat_response_v1"):
        return (
            self.count(
                json.dumps(
                    payload(self.config, messages, schema, schema_name),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            + 128
        )

    monkeypatch.setattr(TokenCounter, "request_input", old_input)
    before, before_adapter = run(command)
    assert (
        before.error["code"] == "CONTEXT_LIMIT"
        and before.error["details"]["stage"] == "joint_check"
    )
    assert len(before_adapter.calls) == 1
    monkeypatch.setattr(TokenCounter, "request_input", exact_method)
    after, after_adapter = run(first_request())
    assert after.error["code"] == "OFFLINE_CHECK_CAPTURE_STOP", after.error
    assert len(after_adapter.calls) == 2
    check = after.token_budget["stage_token_budgets"][-1]
    assert check["stage"] == "joint_check"
    assert (
        check["input_reserved_tokens"] + check["output_reserved_tokens"] <= check["window_tokens"]
    )
    assert check["window_tokens"] == 65536 and check["output_reserved_tokens"] == 4096


@pytest.mark.parametrize(
    "teaching_context",
    [
        None,
        {
            "turn_role": "user_question",
            "current_step": 1,
            "learner_attempt": None,
            "attempt_history": [],
        },
    ],
)
def test_fresh_session_normal_configuration_reaches_required_checker(teaching_context):
    result, adapter = run(first_request(teaching_context=teaching_context))
    assert result.error["code"] == "OFFLINE_CHECK_CAPTURE_STOP", result.error
    assert result.response is None and len(adapter.calls) == 2
    assert not result.delivered_projection


def test_genuine_one_token_oversize_blocks_checker_before_its_dispatch():
    normal, _ = run(first_request())
    check = normal.token_budget["stage_token_budgets"][-1]
    boundary = check["input_reserved_tokens"] + check["output_reserved_tokens"]
    command = first_request()
    command = replace(
        command, checker_config=replace(command.checker_config, window_tokens=boundary - 1)
    )
    result, adapter = run(command)
    assert result.error["code"] == "CONTEXT_LIMIT" and len(adapter.calls) == 1
    details = result.error["details"]
    assert (
        details["input_reserved_tokens"] + details["output_reserved_tokens"]
        > details["window_tokens"]
    )
    assert (
        details["blocked_attempt_request_submitted"] is False and details["stage"] == "joint_check"
    )
    assert details["overflow_tokens"] >= 1
    assert result.budget["consumed_calls"] == 1
    assert not result.checks and result.response is None


@pytest.mark.parametrize(
    "model",
    [
        "sk-private-key",
        "Bearer private",
        "https://private.example/endpoint",
        "private\nrequest",
        "api-key=value",
    ],
)
def test_error_diagnostics_redact_nonpublic_model_identities(model):
    cfg = replace(first_request().config, model=model)
    details = window_failure("joint_check", cfg, 15000)["details"]
    assert details["model"] == "redacted"
    assert model not in json.dumps(details)
    assert set(details) == {
        "diagnostic_version",
        "stage",
        "provider",
        "model",
        "input_reserved_tokens",
        "output_reserved_tokens",
        "window_tokens",
        "total_reserved_tokens",
        "overflow_tokens",
        "count_source",
        "blocked_attempt_request_submitted",
    }


def test_public_diagnostic_schema_crosses_existing_job_dto_without_private_text():
    from contracts.models import JobOut

    internal_error = window_failure("semantic_repair", first_request().config, 15000)
    error = {key: internal_error[key] for key in ("code", "message", "details")}
    data = JobOut.model_validate(
        {
            "id": "job",
            "request_id": "request",
            "state": "failed",
            "stage": "failed",
            "error": error,
            "answer_id": None,
            "can_retry": False,
            "created_at": "",
            "updated_at": "",
        }
    ).model_dump()
    assert data["error"]["details"] == error["details"]
    assert public_model("openai/gpt-6-luna") == "openai/gpt-6-luna"


def test_source_backed_known_luna_preset_keeps_custom_and_other_defaults():
    rows = {item["id"]: item for item in presets()}
    luna = rows.pop("openai_luna")["config"]
    assert luna["model"] == "gpt-6-luna" and luna["provider"] == "openai"
    assert luna["window_tokens"] == 65536 < 1050000 and luna["max_tokens"] == 1024
    assert luna["temperature"] is None
    assert luna["token_limit_parameter"] == "max_completion_tokens"
    assert luna["reasoning_effort"] == "none"
    # Exercise the same public-DTO/capability materialization used by save(),
    # without creating a database, credentials or model connection.
    values = ModelValues.model_validate(luna).model_dump()
    values["capability_version"] = CAPABILITY_VERSION
    values["capabilities"] = capability_defaults(
        values["provider"], values["model"], values["base_url"]
    )
    frozen = ModelConfig.from_dict(values)
    frozen.validate()
    wire = payload(frozen, [{"role": "user", "content": "Authored preset fixture."}], {}, "fixture")
    assert wire["max_completion_tokens"] == 1024 and "max_tokens" not in wire
    assert wire["reasoning_effort"] == "none" and "temperature" not in wire
    assert frozen.window_tokens == 65536
    assert rows.pop("deepseek")["config"]["window_tokens"] == 32768
    assert all(item["config"]["window_tokens"] == 16384 for item in rows.values())
    assert len(rows) == 7
    # A named preset never silently migrates existing/custom configurations.
    assert ModelConfig().window_tokens == 16384 and ModelConfig().max_tokens == 1024
    custom = ModelValues(
        provider="openai_compatible",
        model="authored-custom",
        base_url="https://openrouter.ai/api/v1",
    )
    assert custom.window_tokens == 16384 and custom.max_tokens == 1024
    saved = ModelValues(
        provider="openai",
        model="gpt-6-luna",
        base_url="https://api.openai.com/v1",
        window_tokens=16384,
    )
    assert saved.window_tokens == 16384


def test_full_three_thousand_token_evidence_and_output_reservation_fit_working_cap():
    cfg = first_request().config
    counter = TokenCounter(cfg)
    evidence = "a" * 9000
    draft = "b" * (3 * cfg.max_tokens)
    assert counter.count(evidence) == 3000 and counter.count(draft) == cfg.max_tokens
    # Count the actual full CHECK system/schema captured from the ordinary pipeline,
    # then add an authored complete evidence and bounded draft stress packet.
    result, adapter = run(
        first_request(teaching_context={"turn_role": "user_question", "attempt_history": []})
    )
    assert result.error["code"] == "OFFLINE_CHECK_CAPTURE_STOP"
    messages, kwargs = adapter.calls[1]
    packet = json.loads(messages[-1]["content"])
    packet["AUTHORED_MAXIMUM_EVIDENCE_BUDGET_STRESS"] = evidence
    packet["AUTHORED_MAXIMUM_DRAFT_BUDGET_STRESS"] = draft
    stressed = [
        *messages[:-1],
        {"role": "user", "content": json.dumps(packet, separators=(",", ":"))},
    ]
    checker = first_request().checker_config
    total = (
        TokenCounter(checker).request_input(
            stressed, kwargs["response_schema"], kwargs["response_schema_name"]
        )
        + checker.max_tokens
    )
    assert total < checker.window_tokens == 65536
    assert checker.max_tokens == 4096
