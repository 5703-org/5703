"""Ordinary QA uses native gates; all controls are isolated and offline."""

from copy import deepcopy
import json

import pytest

from generation.ordinary_qa_v1 import Wire
from generation import GenerationService, RequestBudget
from scripts.dev import checker_fixture_runner as runner
from test_source_refs121 import plan, reply


def minimal(value):
    result = {key: deepcopy(value[key]) for key in Wire.model_fields if key not in {"source_interface_version", "answer_only"}}
    result["answer_only"] = value["tutor_question_ok"]
    result["source_interface_version"] = "ordinary_qa_v1"
    for row in result["qualification_assessments"]:
        for key in list(row):
            if key not in {"claim_id", "context_status", "supporting_quotes", "limiting_quotes", "reason"}:
                del row[key]
    return result


def prepared(extra=False):
    rich = plan(extra=extra)
    _, verdict = reply(rich["rows"][0])
    rich["source_transport"] = "ordinary_qa_v1"
    return runner.prepare(rich), minimal(verdict)


def execute(value, verdict, path):
    outer = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(verdict)}}],
             "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
    return runner.run(value, transport=lambda *args: runner.Response(runner.encoded(outer)), output=path)


def test_minimal_native_positive_and_program_inapplicability(tmp_path):
    value, verdict = prepared()
    result = execute(value, verdict, tmp_path / "actual")
    row = result["results"][0]
    assert row["technical_valid"] and row["semantic_accept"] is True
    notes = row["checker"]["qualification_decision_derivative"]
    assert notes["attempt_evaluation"] == "not_applicable"
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    assert packet["interface_version"] == "ordinary_qa_v1"
    assert "ATTEMPT_EVALUATION" not in packet
    assert "attempt_evaluation_ok" not in Wire.model_fields


def test_compiled_prompt_cannot_reintroduce_legacy_fragment_or_inactive_output_fields():
    value, _ = prepared()
    system = value["rows"][0]["body"]["messages"][0]["content"]
    assert "SOURCE RELATION CONTRACT V2" not in system
    assert '"fragment_ids"' not in system
    assert '"evidence_id"' not in system
    for key in ("attempt_evaluation_ok", "tutor_question_ok", "body_ok", "repair_fragment_ids"):
        assert key not in system
    schema = json.loads(system.split("Match this JSON schema:", 1)[1].strip())
    assert set(schema["properties"]) == set(Wire.model_fields)


def test_all_uncited_limiting_sources_retained(tmp_path):
    rich = plan(extra=True)
    old = json.loads(rich["rows"][0]["body"]["messages"][-1]["content"])
    rich["source_transport"] = "ordinary_qa_v1"
    value = runner.prepare(rich)
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    assert [r[-1] for r in packet["sources"]] == [r["exact_text"] for r in old["SOURCE_FRAGMENTS"]]
    assert {r[1] for r in packet["sources"]} == {"ev_001", "ev_002"}


def test_outside_actual_scope_is_independent_real_error(tmp_path):
    value, verdict = prepared(extra=True)
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    outside = next(r for r in packet["sources"] if r[1] == "ev_002")
    verdict["claims"][0]["citations"][0].update(source_id=outside[0], quote=outside[-1])
    result = execute(value, verdict, tmp_path / "actual")
    assert result["status"] == "STOPPED_NO_RETRY"
    assert result["results"][0]["correctness"] is None
    assert "SOURCE_REFERENCE_OUTSIDE_ACTUAL_CITATIONS" in json.dumps(result)


@pytest.mark.parametrize("field", ["attempt_evaluation_ok", "tutor_question_ok", "repair_sources"])
def test_inactive_model_fields_are_rejected(field):
    _, verdict = prepared()
    verdict[field] = True
    with pytest.raises(ValueError):
        Wire.model_validate(verdict)


def test_semantic_negative_is_valid_and_not_promoted(tmp_path):
    value, verdict = prepared()
    verdict["claims"][0]["status"] = "partial"
    verdict["claims"][0]["units"][0]["status"] = "partial"
    result = execute(value, verdict, tmp_path / "actual")
    assert result["results"][0]["technical_valid"]
    assert result["results"][0]["semantic_accept"] is False


def test_visible_answer_task_boundary_is_not_program_passed(tmp_path):
    value, verdict = prepared()
    verdict["answer_only"] = False
    result = execute(value, verdict, tmp_path / "actual")
    assert result["results"][0]["technical_valid"]
    assert result["results"][0]["semantic_accept"] is False


def test_bounded_diagnostic_prose_keeps_raw_and_active_decisions(tmp_path):
    value, verdict = prepared()
    verdict["claims"][0]["reason"] = "Long diagnostic prose. " * 60
    result = execute(value, verdict, tmp_path / "actual")
    row = result["results"][0]
    assert row["technical_valid"] and row["semantic_accept"] is True
    assert json.loads(row["checker"]["raw_text"]) == verdict
    notes = row["checker"]["qualification_decision_derivative"]
    assert notes["bounded_prose"][0]["decision_fields_changed"] is False


@pytest.mark.parametrize("change", ["attempt", "hint", "reading", "suggestions"])
def test_unsupported_task_rejected_before_generation(change):
    value, _ = prepared()
    request, label = runner.make_request(value["rows"][0], value, runner.preflight(value))
    if change == "attempt":
        request.teaching_context["learner_attempt"] = "An actual learner attempt."
    elif change == "hint":
        request.teaching_context.update(teaching_mode="hint", help_level=1)
    elif change == "reading":
        request.reading_context = {"assignment": "active"}
    else:
        request.teaching_context["check_suggestions"] = True
    budget = RequestBudget(max_calls=2)
    outcome = GenerationService(runner.FrozenGeneration(label["draft"])).generate(request, budget)
    assert outcome.error["code"] == "CHECKER_SCHEMA_SCOPE_INVALID"
    assert budget.consumed_calls == 0


def test_limiting_uncited_evidence_is_a_valid_negative_without_invented_repair(tmp_path):
    value, verdict = prepared(extra=True)
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    source = next(r for r in packet["sources"] if r[1] == "ev_002" and "restricted" in r[-1])
    verdict["qualification_assessments"][0].update(
        context_status="needs_qualification", limiting_quotes=[dict(source_id=source[0], quote=source[-1])])
    result = execute(value, verdict, tmp_path / "actual")
    assert result["results"][0]["technical_valid"]
    assert result["results"][0]["semantic_accept"] is False
