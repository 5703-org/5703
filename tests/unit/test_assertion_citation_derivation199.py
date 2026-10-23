"""Explicit citation construction is mechanical; authored CHECK labels prove no quality."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from generation import GenerationService, RequestBudget, checked
from generation import assertion_citation_derivation_v1 as derived
from generation import assertion_provenance_v1 as legacy
from generation.openrouter_routes import prepare_schema_wire
from generation.providers import payload
from generation.reliability_v5 import response_claims
from generation.token_counting import TokenCounter

from test_assertion_provenance161 import (
    ScriptedTransport,
    authored_full_checker,
    mapped_request,
    no_external_io as no_external_io,
    private_draft,
    sources,
)

ROOT = Path(__file__).parents[2]
CAPTURE = json.loads(
    (ROOT / "tests/fixtures/assertion199/q4-off-citations.json").read_text(encoding="utf-8")
)


def reduced(value=None):
    result = deepcopy(private_draft() if value is None else value)
    result.pop("citations")
    return result


def fragments(bank):
    return [
        {
            **row["source_locator"],
            "fragment_id": row["fragment_id"],
            "evidence_id": row["evidence_id"],
            "exact_text": row["exact_text"],
            "text_hash": row["text_sha256"],
            "complete_block": row["complete_block"],
        }
        for row in bank
    ]


def run(request, draft, monkeypatch, *, before=None, negative=False):
    values = [draft]
    if request.verification_mode != "fast":
        values.append(
            lambda messages: authored_full_checker(
                messages, "negative_status" if negative else None
            )
        )
    adapter = ScriptedTransport(values)
    with monkeypatch.context() as patch:
        if before is not None:
            patch.setattr(checked, "generate_checked", before.generate_checked)
        result = GenerationService(adapter, checker_adapter=adapter).generate(
            request, RequestBudget(max_calls=2)
        )
    return result, adapter


@pytest.fixture(scope="module")
def before_checked():
    path = ROOT / "tests/fixtures/assertion199/checked-before199.py"
    spec = importlib.util.spec_from_file_location("generation._before_citations199", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(spec.name)


def wire(call, config):
    messages, options = call
    body = payload(config, messages, options["response_schema"], options["response_schema_name"])
    body, _ = prepare_schema_wire(config, body, options["response_schema"])
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()


def test_saved_q4_strict_rejection_and_explicit_new_projection_keep_all_source_choices():
    original = deepcopy(CAPTURE)
    rows = fragments(CAPTURE["canonical_bank"])
    assert legacy.source_bank(rows, CAPTURE["selected_evidence"]) == CAPTURE["canonical_bank"]
    with pytest.raises(ValueError, match="ASSERTION_CITATIONS_MISMATCH"):
        legacy.compile_draft(CAPTURE["raw_draft"], rows)
    raw = reduced(CAPTURE["raw_draft"])
    public, proof = derived.compile_draft(raw, rows, CAPTURE["selected_evidence"])
    expected = ["ev_004", "ev_010", "ev_008", "ev_007", "ev_009"]
    assert public["citations"] == expected
    assert proof["assertions"][6]["sources"][0]["source_id"] == "F036"
    assert proof["assertions"][6]["evidence_ids"] == ["ev_009"]
    assert proof["assertions"][6]["rendered_text"].endswith(" [ev_009]")
    enriched = {**raw, "citations": expected}
    old_public, old_proof = legacy.compile_draft(enriched, rows)
    assert public == old_public
    construction = proof.pop("citation_construction")
    assert proof == old_proof and construction["semantic_support_certified"] is False
    assert construction["source_bank_sha256"] == legacy._canonical_hash(CAPTURE["canonical_bank"])
    bindings = legacy.checker_bindings(response_claims(public), proof, rows)
    assert bindings[6]["citations"] == [{"evidence_id": "ev_009", "allowed_fragment_ids": ["F036"]}]
    assert CAPTURE == original


def test_new_schema_never_silently_repairs_or_accepts_an_authored_global_citation_field():
    with pytest.raises(ValidationError, match="Extra inputs"):
        derived.compile_draft(private_draft(), sources(), [])


@pytest.mark.parametrize(
    "defect",
    [
        "unknown",
        "duplicate",
        "empty",
        "incomplete",
        "hash",
        "coordinates",
        "duplicate_fragment",
        "excluded_evidence",
        "short_new_evidence",
        "inline_marker",
        "multiple_claims",
        "nonanswer_sources",
    ],
)
def test_invalid_or_incomplete_binding_cannot_construct_display_citations(defect):
    request = mapped_request()
    rows = checked.map_fragments(request.evidence, request.source_map)[0]
    draft = reduced()
    if defect == "unknown":
        draft["answer_text"][0]["source_ids"] = ["F999"]
    elif defect == "duplicate":
        draft["answer_text"][0]["source_ids"] = ["F001", "F001"]
    elif defect == "empty":
        draft["answer_text"][0]["source_ids"] = []
    elif defect == "incomplete":
        rows[0]["complete_block"] = False
    elif defect == "hash":
        rows[0]["text_hash"] = "0" * 64
    elif defect == "coordinates":
        rows[0]["end"] += 1
    elif defect == "duplicate_fragment":
        rows[1]["fragment_id"] = rows[0]["fragment_id"]
    elif defect == "excluded_evidence":
        request.evidence = request.evidence[1:]
    elif defect == "short_new_evidence":
        draft["short_answer"] = {
            "assertion_id": "S001",
            "text": "A symporter carries two substances in the same direction.",
            "source_ids": ["F003"],
        }
    elif defect == "inline_marker":
        draft["answer_text"][0]["text"] += " [ev_001]"
    elif defect == "multiple_claims":
        draft["answer_text"][0]["text"] += " A second complete assertion follows."
    elif defect == "nonanswer_sources":
        draft.update(response_type="social", short_answer=None)
    with pytest.raises((ValueError, ValidationError)):
        derived.compile_draft(draft, rows, request.evidence)


def test_a_later_changed_locator_cannot_rebind_a_compiled_assertion():
    request = mapped_request()
    rows = checked.map_fragments(request.evidence, request.source_map)[0]
    public, proof = derived.compile_draft(reduced(), rows, request.evidence)
    rows[0]["start"] += 1
    rows[0]["end"] += 1
    with pytest.raises(ValueError, match="ASSERTION_SOURCE_BINDING_CHANGED"):
        legacy.checker_bindings(response_claims(public), proof, rows)


@pytest.mark.parametrize("verification", ["fast", "verified"])
def test_real_pipeline_uses_same_reduced_schema_counter_compiler_and_truthful_semantics(
    monkeypatch, verification
):
    request = mapped_request(provider_output_policy=derived.POLICY, verification_mode=verification)
    request.checker_config = replace(request.config, max_tokens=4096)
    outcome, adapter = run(request, reduced(), monkeypatch)
    assert outcome.succeeded, outcome.error
    first = adapter.calls[0]
    assert first[1]["response_schema_name"] == derived.DRAFT_SCHEMA
    assert "citations" not in first[1]["response_schema"]["properties"]
    assert "Do not emit a citations field." in first[0][0]["content"]
    assert "set citations=[]" not in first[0][0]["content"]
    assert "short_answer, citations, refusal_reason" not in first[0][0]["content"]
    assert "empty citations, null short_answer" not in first[0][0]["content"]
    count = TokenCounter(request.config).request_input(
        first[0], first[1]["response_schema"], derived.DRAFT_SCHEMA
    )
    assert outcome.token_budget["final_generation_input_tokens"] == count
    assert outcome.token_budget["stage_token_budgets"][0]["input_reserved_tokens"] == count
    receipt = outcome.token_budget["semantic_verification"]
    assert receipt["check_executed"] is (verification == "verified")
    if verification == "fast":
        assert receipt["status"] == "not_requested" and len(adapter.calls) == 1
    else:
        assert len(adapter.calls) == 2
    assert outcome.drafts[0]["assertion_provenance"]["semantic_support_certified"] is False


def test_a_new_display_list_does_not_promote_a_negative_checker_or_publish(monkeypatch):
    request = mapped_request(provider_output_policy=derived.POLICY)
    request.checker_config = replace(request.config, max_tokens=4096)
    outcome, adapter = run(request, reduced(), monkeypatch, negative=True)
    assert not outcome.succeeded and outcome.response is None and len(adapter.calls) == 2
    assert outcome.token_budget["semantic_verification"]["check_executed"] is True
    assert outcome.token_budget["semantic_verification"]["status"] != "passed"


@pytest.mark.parametrize(
    "change",
    [
        {"assertion_source_policy": None},
        {"enhancement_version": None},
        {"mode": "benchmark_openqa"},
        {"reading_context": {"section": "owned"}},
        {
            "teaching_context": {
                "teaching_mode": "direct",
                "practice_context": {"practice_item_id": "owned"},
            }
        },
        {"teaching_context": {"teaching_mode": "direct", "pending_tutor_question_id": "owned"}},
    ],
)
def test_new_policy_cannot_activate_an_unsupported_route_or_dispatch(monkeypatch, change):
    request = mapped_request(provider_output_policy=derived.POLICY, **change)
    outcome, adapter = run(request, reduced(), monkeypatch)
    assert not outcome.succeeded and not adapter.calls


@pytest.mark.parametrize("policy", ["strict_v1", "json_field_contract_v2"])
@pytest.mark.parametrize("verification", ["fast", "verified"])
def test_legacy_default_wire_and_public_result_are_unchanged(
    before_checked, monkeypatch, policy, verification
):
    request = mapped_request(provider_output_policy=policy, verification_mode=verification)
    request.checker_config = replace(request.config, max_tokens=4096)
    old, old_adapter = run(request, private_draft(), monkeypatch, before=before_checked)
    new, new_adapter = run(request, private_draft(), monkeypatch)
    assert old.succeeded and new.succeeded
    assert old.response == new.response and old.evidence == new.evidence
    for index, (left, right) in enumerate(zip(old_adapter.calls, new_adapter.calls, strict=True)):
        assert wire(left, request.config if index == 0 else request.checker_config) == wire(
            right, request.config if index == 0 else request.checker_config
        )


def test_canonical_default_remains_compatible_with_frozen_pre_boundary_compiler():
    assert Path(checked.__file__).resolve().is_relative_to(ROOT)
    assert Path(derived.__file__).resolve().is_relative_to(ROOT)
    assert Path(legacy.__file__).resolve().is_relative_to(ROOT)
    assert (
        hashlib.sha256(Path(legacy.__file__).read_bytes()).hexdigest()
        == "87b42382861bda96037b760678a5227440116f4169ee8c35c6c3e6bdde8a44ca"
    )

    # Frozen source is retained. Admission and the private Checker prompt changed;
    # every other function, including citation compilation and validation, is exact.
    previous = ROOT / "tests/fixtures/assertion199/provenance-before-task-scope.py"
    assert (
        hashlib.sha256(previous.read_bytes()).hexdigest()
        == "0be2bc003bf25ede93147def0d0cd325cd8cb5e1021294232ab8faf15e91b08d"
    )
    import ast

    old_tree = ast.parse(previous.read_text(encoding="utf-8"))
    new_tree = ast.parse(Path(legacy.__file__).read_text(encoding="utf-8"))
    old_functions = {
        node.name: ast.dump(node, include_attributes=False)
        for node in old_tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    }
    new_functions = {
        node.name: ast.dump(node, include_attributes=False)
        for node in new_tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    }
    assert old_functions.keys() == new_functions.keys()
    assert {name for name in old_functions if old_functions[name] != new_functions[name]} == {
        "submission_fields",
        "eligible",
        "checker_template",
    }

    frozen_path = ROOT / "tests/fixtures/assertion199/provenance-before-boundary.py"
    assert (
        hashlib.sha256(frozen_path.read_bytes()).hexdigest()
        == "a12cae892f08b8f4d022a8b5965c748811d0ea46c3128fceefd1e41de9740b0e"
    )
    spec = importlib.util.spec_from_file_location("generation._pre_boundary_compat", frozen_path)
    frozen = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = frozen
    try:
        spec.loader.exec_module(frozen)
        for draft in (
            private_draft(),
            private_draft(extra=True),
            private_draft(short=True),
            private_draft(extra=True, short=True),
        ):
            assert legacy.compile_draft(draft, sources()) == frozen.compile_draft(draft, sources())
    finally:
        sys.modules.pop(spec.name, None)


def test_native_settings_freeze_the_explicit_new_policy_without_changing_default():
    from app.core.config import Settings

    assert Settings(_env_file=None).chat_provider_output_policy == "json_field_contract_v2"
    assert (
        Settings(
            _env_file=None, chat_provider_output_policy=derived.POLICY
        ).chat_provider_output_policy
        == derived.POLICY
    )


@pytest.mark.parametrize("kind", ["ordinary", "protected", "general", "mock"])
def test_new_admission_uses_actual_assertion_eligibility_without_breaking_other_routes(kind):
    settings = SimpleNamespace(chat_joint_checker_policy="typed_joint_v5")
    arguments = dict(
        answer_mode="textbook",
        teaching={"teaching_mode": "direct", "turn_role": "user_question", "help_level": 0},
        reading_context=None,
        provider="openai_compatible",
        checker_provider="openai_compatible",
    )
    if kind == "protected":
        arguments["teaching"] = {"teaching_mode": "hint", "practice_context": {"item": "owned"}}
    elif kind == "general":
        arguments["answer_mode"] = "general_knowledge"
    elif kind == "mock":
        arguments.update(provider="mock", checker_provider="mock")
    fields = legacy.submission_fields(settings, **arguments)
    assert derived.submission_policy(derived.POLICY, fields) == (
        derived.POLICY if kind == "ordinary" else "json_field_contract_v2"
    )


@pytest.mark.parametrize(
    "configured", ["strict_v1", "json_example_once_v1", "json_field_contract_v2"]
)
def test_old_admission_output_policies_are_preserved_exactly(configured):
    assert derived.submission_policy(configured, {}) == configured
    assert (
        derived.submission_policy(configured, {"assertion_source_policy": legacy.POLICY})
        == configured
    )


def test_admission_rejects_unknown_configuration_instead_of_falling_back():
    with pytest.raises(ValueError, match="UNKNOWN_PROVIDER_OUTPUT_POLICY"):
        derived.submission_policy("unknown", {})
