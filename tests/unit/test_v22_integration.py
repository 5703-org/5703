"""Pure opt-in dispatch and consumer controls without database execution.

Dispatch checks compile actual candidate AST expressions. Consumer checks load
canonical repository modules against authored data.
"""

from __future__ import annotations

import ast
import hashlib
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import pytest

import test_requirements_v8 as producer_tests

from conversation import query as historical_query, query_v21
from generation.coverage_v4 import assess_evidence_coverage
from generation.types import GenerationRequest, ModelConfig
from retrieval.complementary_spans import AXIS_ANCHOR_REVISION, _explicit_axis_terms, select_context


ROOT = Path(__file__).resolve().parents[2]
query_v22 = producer_tests.query_v22
SOURCE_SERVICE = ROOT / "backend/app/modules/answering/service.py"

from conversation import practice_context as practice
from generation import adapters, service as generation_service, unit_definition_plan_v1 as unit_plan


@pytest.fixture(autouse=True)
def forbid_provider_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Pure integration controls forbid provider transport")

    monkeypatch.setattr(adapters, "open_provider", forbidden)
    monkeypatch.setattr(adapters.LLMAdapter, "_call", forbidden)


def source_tree(path=SOURCE_SERVICE):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def function(tree, name):
    return next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
    )


def assignment(func, name):
    values = [
        node.value
        for node in ast.walk(func)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    ]
    assert len(values) == 1, f"Expected a unique actual source assignment for {name}"
    return values[0]


def evaluate(expression, namespace):
    code = compile(ast.Expression(body=expression), str(SOURCE_SERVICE), "eval")
    return eval(code, namespace)


def request_constructor(func):
    calls = [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "AnswerRequest"
    ]
    assert len(calls) == 1
    return calls[0]


def command_value(command, name):
    return next(
        value
        for key, value in zip(command.keys, command.values)
        if isinstance(key, ast.Constant) and key.value == name
    )


def dispatch_namespace(command, *, live_policy="anchored_reference_v22"):
    def tagged(name):
        def producer(*args, **kwargs):
            return {"producer": name, "args": args, "kwargs": kwargs}

        return producer

    namespace = {
        "req": SimpleNamespace(command=deepcopy(command), mode="interactive_chat"),
        "settings": SimpleNamespace(chat_query_preparation_policy=live_policy),
        "REQUIREMENTS_V4": "question_requirements_v4",
        "PREPARATION_VERSION": historical_query.VERSION,
        "LEGACY_VERSION": historical_query.LEGACY_VERSION,
        "prepare_query": tagged("historical_query"),
        "describe_requirements_v4": tagged("requirements_v4"),
        "describe_requirements": tagged("historical_requirements"),
        "describe_question": tagged("historical_understanding"),
        "practice_query": None,
        "current_core": True,
        "prepared": {"preparation_version": command["preparation_version"]},
        "selection_policy": {"version": "authored_selection"},
        "teaching_context": None,
        "question": "Explain photosynthesis.",
        "context": {"summary_text": None},
        "history": [{"role": "user", "content": "Authored old question"}],
        "restatement_query_history": lambda context, marker: ["owned_frozen_history"],
    }
    for number in range(14, 23):
        namespace[f"query_v{number}"] = SimpleNamespace(
            VERSION=f"conversation_preparer_v{number}",
            prepare_query=tagged(f"preparation_v{number}"),
            describe_requirements=tagged(f"requirements_via_v{number}"),
        )
    return namespace


def test_config_defaults_to_registered_v22_with_frozen_predecessors():
    tree = source_tree(ROOT / "backend/app/core/config.py")
    setting = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "chat_query_preparation_policy"
    )
    assert evaluate(setting.value, {}) == "anchored_reference_v22"
    annotation = evaluate(setting.annotation, {"Literal": Literal})
    assert "anchored_reference_v22" in annotation.__args__


@pytest.mark.parametrize(
    "policy,expected_preparation,expected_requirements",
    [
        ("anchored_reference_v21", "conversation_preparer_v21", "question_requirements_v7"),
        ("anchored_reference_v22", "conversation_preparer_v22", "question_requirements_v8"),
        ("anchored_reference_v20", "conversation_preparer_v20", "question_requirements_v6"),
        ("anchored_reference_v17", "conversation_preparer_v17", "question_requirements_v5"),
        ("recorded", historical_query.VERSION, "question_requirements_v4"),
    ],
)
def test_actual_submission_expression_freezes_matching_version_pair(
    policy, expected_preparation, expected_requirements
):
    submit = function(source_tree(), "submit_chat")
    command = next(
        keyword.value
        for keyword in request_constructor(submit).keywords
        if keyword.arg == "command"
    )
    namespace = dispatch_namespace(
        {"preparation_version": expected_preparation}, live_policy=policy
    )
    assert (
        evaluate(command_value(command, "preparation_version"), namespace) == expected_preparation
    )
    assert (
        evaluate(command_value(command, "requirements_version"), namespace) == expected_requirements
    )


@pytest.mark.parametrize(
    "policy,expected",
    [
        ("anchored_reference_v21", True),
        ("anchored_reference_v22", True),
        ("recorded", False),
    ],
)
def test_actual_submission_restatement_snapshot_remains_available_for_opt_in(policy, expected):
    submit = function(source_tree(), "submit_chat")
    command = next(
        keyword.value
        for keyword in request_constructor(submit).keywords
        if keyword.arg == "command"
    )
    restatement = next(
        value
        for key, value in zip(command.keys, command.values)
        if key is None
        and isinstance(value, ast.IfExp)
        and isinstance(value.body, ast.Dict)
        and any(
            isinstance(inner, ast.Constant) and inner.value == "restatement_context"
            for inner in value.body.keys
        )
    )
    namespace = {"settings": SimpleNamespace(chat_query_preparation_policy=policy)}
    namespace.update({name: object() for name in ("db", "actor", "session_id", "rows", "context")})
    namespace["cs"] = SimpleNamespace(content_hash="authored_frozen_hash")
    namespace["freeze_restatement_context"] = lambda *args: {"context_hash": args[-1]}
    result = evaluate(restatement, namespace)
    assert bool(result) is expected
    if expected:
        assert result == {"restatement_context": {"context_hash": "authored_frozen_hash"}}


@pytest.mark.parametrize(
    "number,requirements",
    [
        (14, "question_requirements_v4"),
        (16, "question_requirements_v4"),
        (17, "question_requirements_v5"),
        (18, "question_requirements_v5"),
        (19, "question_requirements_v5"),
        (20, "question_requirements_v6"),
        (21, "question_requirements_v7"),
        (22, "question_requirements_v8"),
    ],
)
@pytest.mark.parametrize("live_policy", ["anchored_reference_v21", "anchored_reference_v22"])
def test_execution_uses_saved_pair_even_after_live_setting_changes(
    number, requirements, live_policy
):
    command = {
        "preparation_version": f"conversation_preparer_v{number}",
        "requirements_version": requirements,
    }
    namespace = dispatch_namespace(command, live_policy=live_policy)
    execute = function(source_tree(), "execute_answer")
    selected = evaluate(assignment(execute, "active_query_preparer"), namespace)
    assert selected is namespace[f"query_v{number}"].prepare_query
    understanding = evaluate(assignment(execute, "understanding"), namespace)
    assert understanding["producer"] == f"requirements_via_v{number}"
    assert understanding["args"][0] == "Explain photosynthesis."
    assert namespace["req"].command == command


@pytest.mark.parametrize(
    "preparation,requirements",
    [
        ("conversation_preparer_v21", "question_requirements_v8"),
        ("conversation_preparer_v22", "question_requirements_v7"),
    ],
)
def test_mismatched_saved_pairs_cannot_accidentally_select_v22_requirements(
    preparation, requirements
):
    namespace = dispatch_namespace(
        {"preparation_version": preparation, "requirements_version": requirements}
    )
    understanding = evaluate(
        assignment(function(source_tree(), "execute_answer"), "understanding"), namespace
    )
    assert understanding["producer"] != "requirements_via_v22"


def test_regenerate_actual_expression_copies_frozen_command_and_preserves_versions():
    old_command = {
        "question": producer_tests.QUESTION,
        "preparation_version": query_v21.VERSION,
        "requirements_version": "question_requirements_v7",
        "reading_context": {"section": "Authored frozen photosynthesis"},
        "generation_policy": {"version": "generation_controls_v6"},
    }
    before = deepcopy(old_command)
    regenerate = function(source_tree(), "regenerate")
    frozen = evaluate(
        assignment(regenerate, "frozen_command"), {"old": SimpleNamespace(command=old_command)}
    )
    assert frozen == before and frozen is not old_command
    command_keyword = next(
        keyword.value
        for keyword in request_constructor(regenerate).keywords
        if keyword.arg == "command"
    )
    assert evaluate(command_keyword, {"frozen_command": frozen}) is frozen
    assert old_command == before
    assert frozen["preparation_version"] == query_v21.VERSION
    assert frozen["requirements_version"] == "question_requirements_v7"


def teaching_context():
    return {
        "turn_role": "user_question",
        "practice_context": {
            "version": "practice_tutor_context_v1",
            "item_id": "authored_opt_in_step",
            "progress_version": 2,
            "current_step": 1,
            "prompt": "Explain the energy used in photosynthesis.",
            "current_step_prompt": "Identify the stated photosynthesis energy input.",
            "conditions": ["Assume 25 C and no added artificial illumination."],
            "concepts": ["photosynthesis"],
            "source": {"source_unit_id": "authored_public_source"},
            "private_rubric": {"answer_key": "PRIVATE_OPT_IN_CANARY"},
        },
    }


@pytest.mark.parametrize(
    "module,expected",
    [(query_v21, "question_requirements_v7"), (query_v22, "question_requirements_v8")],
)
@pytest.mark.parametrize(
    "question,role",
    [
        (
            "Help me with the current practice step without giving the answer.",
            "teaching_instruction",
        ),
        ("Which energy input is used by photosynthesis?", "knowledge_request"),
    ],
)
def test_actual_practice_consumer_dispatches_saved_producer_and_public_context(
    module, expected, question, role
):
    teaching = teaching_context()
    before = deepcopy(teaching)
    prepared = module.prepare_query(question).model_dump()
    contextual, requirements = practice.resolve(
        question,
        prepared,
        teaching,
        policy=practice.VERSION,
        preparation_version=module.VERSION,
    )
    assert teaching == before
    assert contextual["preparation_version"] == module.VERSION
    assert requirements["version"] == expected
    assert requirements["preparation_dependency"]["frozen_preparation_version"] == module.VERSION
    assert contextual["original_message"] == question
    assert "25 C and no added artificial illumination" in contextual["standalone_query"]
    assert "PRIVATE_OPT_IN_CANARY" not in repr((contextual, requirements))
    assert requirements["practice_reference_resolution"]["request_role"] == role
    if role == "teaching_instruction":
        assert all("Help me" not in row["request"] for row in requirements["required_knowledge"])
    else:
        assert any(
            question.rstrip("?") in row["request"] for row in requirements["required_knowledge"]
        )


def reader_context(question, *, module=query_v22):
    prepared, understanding = producer_tests.extract(question, module=module, reader=True)
    return {
        "question": question,
        "prepared_query": prepared,
        "understanding": understanding,
        "mode": "interactive_chat",
        "condition": "E1",
        "evidence": [
            {
                "evidence_id": "ev_authored",
                "chunk_id": "authored_reader",
                "text": "Photosynthesis converts sunlight into chemical energy.",
            }
        ],
    }


def test_v8_metadata_alias_preserves_supported_native_reader_definition():
    context = reader_context("What is photosynthesis in this selected passage?")
    assert context["understanding"]["version"] == "question_requirements_v8"
    assert "Textbook section" in context["prepared_query"]["standalone_query"]
    assert "Textbook section" not in context["understanding"]["standalone_query"]
    assert (
        adapters.mock_excerpt(context["prepared_query"]["standalone_query"], context["evidence"])
        is None
    )
    response = adapters.mock_payload(context)
    assert response["response_type"] == "answer"
    assert response["answer_text"] == context["evidence"][0]["text"] + " [ev_authored]"
    assert response["citations"] == ["ev_authored"]


def test_v8_reader_alias_does_not_relax_original_preference_or_synonym_matching():
    context = reader_context(producer_tests.QUESTION)
    context["evidence"][0]["text"] = "Light supplies energy for photosynthesis."
    response = adapters.mock_payload(context)
    assert len(context["understanding"]["required_knowledge"]) == 1
    assert context["understanding"]["standalone_query"].startswith("I prefer examples")
    assert response["response_type"] == "refusal"
    assert response["refusal_reason"] == "INSUFFICIENT_EVIDENCE"
    assert response["citations"] == []


@pytest.mark.parametrize(
    "question",
    [
        "What is photosynthesis without sunlight in this selected passage?",
        "What is photosynthesis at 2031 kelvin in this selected passage?",
    ],
)
def test_native_reader_numeric_and_negation_matching_remain_strict(question):
    context = reader_context(question)
    response = adapters.mock_payload(context)
    assert response["response_type"] == "refusal"
    assert response["refusal_reason"] == "INSUFFICIENT_EVIDENCE"
    assert response["citations"] == []
    assert context["understanding"]["preserved_constraints"]


def test_preserved_v21_reader_response():
    context = reader_context("What is photosynthesis in this selected passage?", module=query_v21)
    response = adapters.mock_payload(context)
    assert response["response_type"] == "answer"
    assert response["citations"] == ["ev_authored"]
    assert response["answer_text"] == context["evidence"][0]["text"] + " [ev_authored]"


def test_v22_clarification_consumer_uses_zero_generator_calls():
    class ForbiddenAdapter:
        def generate(self, *args, **kwargs):
            pytest.fail("Clarification must not invoke a generator")

    question = "Explain it more simply."
    prepared, understanding = producer_tests.extract(question, module=query_v22)
    assert prepared["needs_clarification"]
    result = generation_service.GenerationService(adapter=ForbiddenAdapter()).generate(
        GenerationRequest(
            request_id="authored_opt_in_clarification",
            mode="interactive_chat",
            condition="E1",
            question=question,
            prepared_query=prepared,
            understanding=understanding,
            config=ModelConfig(provider="mock", tokenizer_provider="estimate"),
            evidence=[],
        )
    )
    assert result.succeeded
    assert result.response["response_type"] == "clarification"
    assert result.budget["consumed_calls"] == 0


@pytest.mark.parametrize(
    "question,expected",
    [
        (
            "Which units describe energy equal to 2.5 J without heating?",
            "planned_auxiliary_unit_definitions",
        ),
        ("Which pressure units match 2 pa?", "unknown_unit_token"),
        ("Which units apply to the variable N?", "no_unambiguous_named_unit"),
    ],
)
def test_v8_unit_lookup_alias_keeps_native_boundaries_and_constraints(question, expected):
    _, understanding = producer_tests.extract(question, module=query_v22)
    report = assess_evidence_coverage(question, [], understanding)
    before = deepcopy((understanding, report))
    result = unit_plan.plan(question, report, understanding)
    old_identity = {**understanding, "version": "question_requirements_v7"}
    assert result == unit_plan.plan(question, report, old_identity)
    assert result["status"] == expected
    assert (understanding, report) == before
    assert result["semantic_sufficiency"] is None
    assert result["source_relation_verified"] is None
    if expected == "planned_auxiliary_unit_definitions":
        assert result["query"] == "SI unit definitions for joule. Units of energy."
        assert understanding["preserved_constraints"]["negation"]


def test_v8_unit_lookup_rejects_coordinate_tampering():
    question = "Which units describe energy of 2 J?"
    _, understanding = producer_tests.extract(question, module=query_v22)
    understanding["required_knowledge"][0]["request_span"]["start"] = True
    report = assess_evidence_coverage(question, [], understanding)
    result = unit_plan.plan(question, report, understanding)
    assert result["status"] == "unverified_current_requirement_coordinates"
    assert result["query"] is None


def test_v8_unit_lookup_keeps_the_retained_sparse_science_id():
    question = "I prefer examples for photosynthesis. Explain which energy units apply to photosynthesis at 2 J."
    _, understanding = producer_tests.extract(question, module=query_v22)
    assert [row["id"] for row in understanding["required_knowledge"]] == ["requirement_02"]
    report = assess_evidence_coverage(question, [], understanding)
    result = unit_plan.plan(question, report, understanding)
    assert result["status"] == "planned_auxiliary_unit_definitions"
    assert result["requirement_id"] == "requirement_02"
    assert result["query"] == "SI unit definitions for joule. Units of energy."
    assert result["verbatim_request"] == understanding["required_knowledge"][0]["request"]


COMPARISON = "Compare diffusion and osmosis in their rates."


def authored_comparison_source():
    sentences = [
        "The rates change only if the boundary remains sealed.",
        "This condition qualifies the preceding rate statement.",
        *[f"Neutral connecting source block {i}." for i in range(8)],
        "Diffusion and osmosis have different rates.",
        "The final source qualification remains recorded.",
    ]
    text = "\n".join(sentences)
    evidence = [
        {
            "evidence_id": "ev_axis",
            "chunk_id": "authored_axis",
            "text": text,
            "text_hash": hashlib.sha256(text.encode()).hexdigest(),
            "source_title": "Authored comparison context",
        }
    ]
    fragments, cursor = [], 0
    for index, sentence in enumerate(sentences):
        fragments.append(
            {
                "evidence_id": "ev_axis",
                "fragment_id": f"axis_{index}",
                "complete_block": True,
                "chunk_start": cursor,
                "chunk_end": cursor + len(sentence),
                "exact_text": sentence,
            }
        )
        cursor += len(sentence) + 1
    return evidence, fragments, sentences


@pytest.mark.parametrize(
    "question,expected_id",
    [
        (COMPARISON, "requirement_01"),
        ("I prefer examples for diffusion. " + COMPARISON, "requirement_02"),
    ],
)
def test_v22_comparison_retains_literal_rate_axis_and_qualified_contiguous_source(
    question, expected_id
):
    _, understanding = producer_tests.extract(question, module=query_v22)
    point = understanding["required_knowledge"][0]
    assert understanding["version"] == "question_requirements_v8"
    assert point["id"] == expected_id
    assert point["requested_axes"] == ["rates"]
    assert _explicit_axis_terms(understanding) == {"rate"}
    evidence, fragments, sentences = authored_comparison_source()
    before = deepcopy((understanding, evidence, fragments))
    selected, ranges, excluded, trace = select_context(evidence, fragments, question, understanding)
    assert (understanding, evidence, fragments) == before
    assert sentences[0] in selected[0]["text"]
    assert sentences[1] in selected[0]["text"]
    assert sentences[10] in selected[0]["text"]
    span = ranges["authored_axis"]
    assert (
        selected[0]["text"] == evidence[0]["text"][span["submitted_start"] : span["submitted_end"]]
    )
    assert selected[0]["text_hash"] == hashlib.sha256(selected[0]["text"].encode()).hexdigest()
    assert len(selected[0]["text"]) <= len(evidence[0]["text"])
    assert excluded == []
    assert trace["axis_anchor_revision"] == AXIS_ANCHOR_REVISION
    assert {"axis_0", "axis_10"} <= set(trace["decisions"][0]["axis_anchor_fragment_ids"])
    assert trace["decisions"][0]["semantic_sufficiency"] is None
    unregistered = deepcopy(understanding)
    unregistered["version"] = "unregistered_requirements_identity"
    old_selected, _, _, old_trace = select_context(evidence, fragments, question, unregistered)
    assert sentences[0] not in old_selected[0]["text"]
    assert "axis_anchor_revision" not in old_trace


@pytest.mark.parametrize(
    "change",
    [
        "coordinate_space",
        "bool_start",
        "past_end",
        "verbatim",
        "relation",
        "axes_none",
        "axes_string",
        "axes_empty",
        "axes_mixed",
    ],
)
def test_v8_comparison_rejects_unverified_axis_coordinates_and_types(change):
    _, understanding = producer_tests.extract(COMPARISON, module=query_v22)
    point = understanding["required_knowledge"][0]
    if change == "coordinate_space":
        point["request_span"]["coordinate_space"] = "unverified_query"
    elif change == "bool_start":
        point["request_span"]["start"] = False
    elif change == "past_end":
        point["request_span"]["end"] = len(understanding["requirement_source_text"]) + 1
    elif change == "verbatim":
        point["verbatim_request"] = "An unrelated comparison"
    elif change == "relation":
        point["relation"] = "causal_explanation"
    else:
        point["requested_axes"] = {
            "axes_none": None,
            "axes_string": "rates",
            "axes_empty": [],
            "axes_mixed": ["rates", 3],
        }[change]
    assert _explicit_axis_terms(understanding) == set()
    evidence, fragments, sentences = authored_comparison_source()
    selected, _, _, trace = select_context(evidence, fragments, COMPARISON, understanding)
    assert sentences[0] not in selected[0]["text"]
    assert "axis_anchor_revision" not in trace
