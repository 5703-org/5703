"""Compact producer/gate regressions; all semantic judgments are authored fixtures."""

from copy import deepcopy
import hashlib
import json
import pytest
from generation import GenerationService, ModelConfig, RequestBudget
from generation.local_repair import VERSION as REPAIR
from generation.source_relations_v2 import VERSION, syntactic_units, assess_source_relations
from generation.teaching_plan_v6 import freeze_generation_policy
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer
from test_source_relation_contract import check_input, mismatched_quote


def request_fixture(**values):
    """Keep source-gate fixtures within a fixed finite 32K test window."""
    return req(config=ModelConfig(window_tokens=32768, tokenizer_provider="estimate"), **values)


def unit_checker(messages, **updates):
    data = check_input(messages)
    value = checker(messages, **updates)
    units = {row["claim_id"]: row["units"] for row in data["SOURCE_SYNTACTIC_UNITS"]}
    for row in value["claims"]:
        if row["basis"] == "textbook":
            row["units"] = [
                {
                    "unit_id": unit["unit_id"],
                    "status": "supported",
                    "fragment_ids": [
                        fid for citation in row["citations"] for fid in citation["fragment_ids"]
                    ],
                    "relation_preserved": True,
                    "conditions_preserved": True,
                    "reason": "Authored fixture, not semantic accuracy.",
                }
                for unit in units[row["claim_id"]]
            ]
    return value


def assert_assessed_sources_are_canonical(out, request, check_index=0):
    """Join stored unit selections to the exact immutable source-unit slices."""
    check = out.checks[check_index]
    stored = check["source_relation_assessment"]
    originals = {
        row["claim_id"]: row
        for row in check["source_relation_assessment_raw_aliases"]["claims"]
    }
    raw_claims = {row["claim_id"]: row for row in check["typed_judgment_raw_aliases"]["claims"]}
    fragments = {row["fragment_id"]: row for row in out.attribution["fragments"]}
    assert not stored["source_entailment_locally_certified"]
    for claim in stored["claims"]:
        original = originals[claim["claim_id"]]
        raw_units = {row["unit_id"]: row for row in raw_claims[claim["claim_id"]]["units"]}
        for unit, raw in zip(claim["obligations"], original["obligations"], strict=True):
            assert unit["fragment_ids"] == [row["fragment_id"] for row in unit["source_quotes"]]
            assert raw["fragment_ids"] == raw_units[unit["unit_id"]]["fragment_ids"]
            assert all(fid.startswith("F") for fid in raw["fragment_ids"])
            for field in ("status", "relation_preserved", "conditions_preserved", "reason"):
                assert unit[field] == raw[field]
            for quote in unit["source_quotes"]:
                fragment = fragments[quote["fragment_id"]]
                assert (quote["evidence_id"], quote["quote"]) == (
                    fragment["evidence_id"], fragment["exact_text"]
                )
                source_unit = next(
                    row for row in request.source_map[fragment["chunk_id"]]["units"]
                    if row["id"] == fragment["source_unit_id"]
                )
                exact = source_unit["cleaned_text"][fragment["start"] : fragment["end"]]
                assert exact == quote["quote"]
                assert fragment["text_hash"] == hashlib.sha256(exact.encode("utf-8")).hexdigest()
                assert fragment["offset_basis"] == "cleaned_source_unit_unicode"


@pytest.mark.parametrize(
    "text",
    [
        "Under condition A, starch is converted into sucrose; sucrose is stored as starch [ev_001].",
        "At −2.5 °C, x ≤ 3 and y → z without heating [ev_001].",
        "Water does not move from X to Y unless condition A holds [ev_001].",
        "DNA and RNA differ in bases or sugars, which have different roles [ev_001].",
        "A **qualified** relation (a/b) holds; ΔG = −RT ln(K) [ev_001].",
    ],
)
def test_server_partition_retains_every_exact_character_and_full_claim_context(text):
    rows = syntactic_units([{"claim_id": "c", "text": text}])
    assert rows[0]["full_claim"] == text
    assert "".join(unit["text"] for unit in rows[0]["units"]) == text
    assert len({unit["unit_id"] for unit in rows[0]["units"]}) == len(rows[0]["units"])
    for unit in rows[0]["units"]:
        assert unit["text"] == text[unit["start"] : unit["end"]]


def local_fixture():
    claims = [
        {
            "claim_id": "c",
            "text": "Starch is converted into sucrose and sucrose is stored as a polymer [ev_001].",
        }
    ]
    units = syntactic_units(claims)[0]["units"]
    typed = {
        "claims": [
            {
                "claim_id": "c",
                "basis": "textbook",
                "status": "supported",
                "citations": [
                    {"evidence_id": "ev_001", "fragment_ids": ["F001"], "relation": "supporting"}
                ],
                "units": [
                    {
                        "unit_id": unit["unit_id"],
                        "status": "supported",
                        "fragment_ids": ["F001"],
                        "relation_preserved": True,
                        "conditions_preserved": True,
                        "reason": "Authored fixture.",
                    }
                    for unit in units
                ],
            }
        ]
    }
    binding = [
        {
            "claim_id": "c",
            "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": ["F001", "F002"]}],
        }
    ]
    source = [
        {
            "fragment_id": "F001",
            "evidence_id": "ev_001",
            "complete_block": True,
            "exact_text": "Stored starch is converted into sucrose.",
        },
        {
            "fragment_id": "F002",
            "evidence_id": "ev_001",
            "complete_block": True,
            "exact_text": "Photosynthesis products are sugars such as sucrose.",
        },
    ]
    return typed, claims, binding, source


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "duplicate",
        "foreign",
        "unassessed_fragment",
        "unknown_fragment",
        "incomplete",
        "duplicate_fragment",
        "contradictory_citation",
    ],
)
def test_invalid_unit_or_actual_assessed_fragment_never_establishes_support(defect):
    values = local_fixture()
    claim = values[0]["claims"][0]
    if defect == "missing":
        claim["units"].pop()
    elif defect == "duplicate":
        claim["units"].append(deepcopy(claim["units"][0]))
    elif defect == "foreign":
        claim["units"][0]["unit_id"] = "U999"
    elif defect == "unassessed_fragment":
        claim["units"][0]["fragment_ids"] = ["F002"]
    elif defect == "unknown_fragment":
        claim["units"][0]["fragment_ids"] = ["F999"]
    elif defect == "incomplete":
        values[3][0]["complete_block"] = False
    elif defect == "duplicate_fragment":
        claim["units"][0]["fragment_ids"] = ["F001", "F001"]
    else:
        claim["citations"][0]["relation"] = "contradictory"
    contract, _, report = assess_source_relations(*values)
    assert contract and not report["accepted"]


def test_starch_sucrose_relation_defect_rejects_even_an_optimistic_compound_aggregate():
    values = local_fixture()
    values[0]["claims"][0]["units"][1].update(status="unsupported", relation_preserved=False)
    contract, defects, report = assess_source_relations(*values)
    assert not contract
    assert {row["code"] for row in defects} == {
        "SOURCE_RELATION_UNSUPPORTED",
        "SOURCE_RELATION_CHANGED",
    }
    assert report["claims"][0]["checker_claim_status"] == "supported" and not report["accepted"]
    assert not report["semantic_atomicity_locally_certified"]


@pytest.mark.parametrize("field", ["relation_preserved", "conditions_preserved"])
def test_lost_direction_condition_negation_or_signed_formula_routes_to_semantic_repair(field):
    values = local_fixture()
    values[0]["claims"][0]["units"][0][field] = False
    contract, defects, _ = assess_source_relations(*values)
    assert not contract and defects


def test_pipeline_reconstructs_exact_claim_and_sources_and_uses_matching_final_highlight():
    adapter = Script([answer(), unit_checker])
    request = request_fixture(
        source_relation_policy=VERSION, generation_policy=freeze_generation_policy()
    )
    out = GenerationService(adapter).generate(request)
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 2
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_source_relations_v2"
    assert out.token_budget["context_coverage"]["version"] == "context_coverage_v4"
    raw = out.checks[0]["typed_judgment_raw_aliases"]["claims"][0]
    assert "units" in raw and "obligations" not in raw
    assert "claim_quote" not in raw["units"][0] and "source_quotes" not in raw["units"][0]
    unit = out.checks[0]["source_relation_assessment"]["claims"][0]["obligations"][0]
    assert unit["claim_quote"] == out.response["answer_text"]
    ids = {q["fragment_id"] for q in unit["source_quotes"]}
    assert ids == set(out.delivered_projection["citation_views"][0]["fragment_ids"])
    assert set(unit["fragment_ids"]) == ids
    assert_assessed_sources_are_canonical(out, request)


@pytest.mark.parametrize(
    "text,short_answer",
    [
        ("Light energy is used by photosynthesis. [ev_001]", None),
        (
            "Photosynthesis uses light energy and carbon dioxide supplies carbon. [ev_001]",
            "Photosynthesis uses light energy. [ev_001]",
        ),
    ],
)
def test_pipeline_source_unit_trace_covers_reworded_compound_and_short_answer(text, short_answer):
    request = request_fixture(source_relation_policy=VERSION)
    out = GenerationService(Script([answer(text, short_answer=short_answer), unit_checker])).generate(
        request
    )
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 2
    assert_assessed_sources_are_canonical(out, request)


@pytest.mark.parametrize("defect", ["missing", "duplicate", "foreign", "unassessed"])
def test_pipeline_missing_duplicate_foreign_unit_or_unassessed_source_is_not_published(defect):
    def invalid(messages):
        data = check_input(messages)
        value = unit_checker(messages)
        row = value["claims"][0]
        if defect == "missing":
            row["units"] = []
        elif defect == "duplicate":
            row["units"].append(deepcopy(row["units"][0]))
        elif defect == "foreign":
            row["units"][0]["unit_id"] = "U999"
        else:
            selected = set(row["citations"][0]["fragment_ids"])
            row["units"][0]["fragment_ids"] = [
                next(
                    f["fragment_id"]
                    for f in data["SOURCE_FRAGMENTS"]
                    if f["fragment_id"] not in selected
                )
            ]
        return value

    out = GenerationService(Script([answer(), invalid])).generate(
        request_fixture(source_relation_policy=VERSION), RequestBudget(max_calls=2)
    )
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"


def test_negative_units_repair_only_defective_claims_and_receive_complete_final_check():
    original = answer(
        "Photosynthesis uses light energy. [ev_001] Carbon dioxide supplies carbon and makes matter from nothing. [ev_001]"
    )

    def rejected(messages):
        value = unit_checker(messages)
        value["claims"][1]["units"][-1].update(status="unsupported", relation_preserved=False)
        return value

    def patch(messages):
        assert "SOURCE RELATION REPAIR V2" in messages[-1]["content"]
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
        for claim in data["source_relation_assessment"]["claims"]:
            for unit in claim["obligations"]:
                assert unit["fragment_ids"] == [
                    quote["fragment_id"] for quote in unit["source_quotes"]
                ]
                assert all(fid.startswith("span_") for fid in unit["fragment_ids"])
        protected = {row["claim_id"] for row in data["protected_exact_claims"]}
        return {
            "edits": [
                {
                    "claim_id": row["claim_id"],
                    "replacement_text": "Carbon dioxide supplies carbon for sugar. [ev_001]",
                }
                for row in data["original_claims"]
                if row["claim_id"] not in protected
            ],
            "append_answer_text": "",
        }

    out = GenerationService(Script([original, rejected, patch, unit_checker])).generate(
        request_fixture(source_relation_policy=VERSION, repair_policy=REPAIR)
    )
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4
    assert out.response["answer_text"].startswith("Photosynthesis uses light energy. [ev_001]")
    assert out.checks[-1]["source_relation_assessment"]["accepted"]


@pytest.mark.parametrize("answer_field", ["answer_text", "short_answer"])
def test_factual_body_and_short_answer_are_both_checked_in_v2(answer_field):
    def rejected(messages):
        data = check_input(messages)
        value = unit_checker(messages)
        cid = next(row["claim_id"] for row in data["CLAIMS"] if row["answer_field"] == answer_field)
        row = next(row for row in value["claims"] if row["claim_id"] == cid)
        row["units"][0]["conditions_preserved"] = False
        return value

    request = request_fixture(source_relation_policy=VERSION)
    out = GenerationService(
        Script([answer(short_answer="Photosynthesis uses light energy. [ev_001]"), rejected])
    ).generate(request, RequestBudget(max_calls=2))
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 2
    assert "SOURCE_CONDITION_CHANGED" in out.checks[0]["source_relation_assessment"]["semantic_defect_codes"]
    assert_assessed_sources_are_canonical(out, request)


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_negative_unit_source_trace_never_fills_empty_selection_or_rewrites_reason(status):
    reason = "Authored F001 reason; preserve literally."

    def rejected(messages):
        value = unit_checker(messages)
        unit = value["claims"][0]["units"][0]
        unit.update(status=status, reason=reason)
        if status == "unsupported":
            unit["fragment_ids"] = []
        return value

    request = request_fixture(source_relation_policy=VERSION)
    out = GenerationService(Script([answer(), rejected])).generate(request, RequestBudget(max_calls=2))
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 2
    assessment = out.checks[0]["source_relation_assessment"]
    assert not assessment["accepted"]
    assert "SOURCE_RELATION_" + status.upper() in assessment["semantic_defect_codes"]
    claim = assessment["claims"][0]
    assert claim["checker_claim_status"] == "supported"
    unit = claim["obligations"][0]
    assert unit["status"] == status and unit["reason"] == reason
    if status == "unsupported":
        assert unit["fragment_ids"] == [] and unit["source_quotes"] == []
    else:
        assert unit["fragment_ids"]
    assert_assessed_sources_are_canonical(out, request)


def test_genuine_partial_context_guard_remains_active_in_v2():
    def contradictory(messages):
        value = unit_checker(messages, coverage="supported_partial", missing_facets=["direction"])
        value["requirements"][0].update(
            sufficiency="partial",
            response_coverage="covered",
            missing_information="Requested direction absent.",
        )
        return value

    out = GenerationService(Script([answer(), contradictory])).generate(
        request_fixture(source_relation_policy=VERSION), RequestBudget(max_calls=2)
    )
    assert out.response is None and "INSUFFICIENT_CONTEXT_FULL_COVERAGE" in json.dumps(out.checks)


def _ordinary_source_only_local_patch_case(final_axis=None):
    """Existing service/codec with authored adapters; not model-quality evidence."""
    value = request_fixture(
        source_relation_policy=VERSION,
        repair_policy=REPAIR,
        joint_checker_policy="typed_joint_v5",
        answer_mode="textbook",
        teaching_context={"turn_role": "user_question", "teaching_mode": "direct", "help_level": 0},
    )
    before = deepcopy(value)
    original = "Photosynthesis creates light energy. [ev_001]"
    corrected = "Photosynthesis uses light energy. [ev_001]"

    def rejected(messages):
        verdict = unit_checker(messages, body_ok=False)
        for row in verdict["claims"]:
            row.update(status="partial", reason="Authored source-only predicate defect.")
            for unit in row["units"]:
                unit.update(status="partial", relation_preserved=False,
                            reason="Authored source-only predicate defect.")
        return verdict

    def patch(messages):
        feedback = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        assert feedback["protected_exact_claims"] == []
        assert len(feedback["original_claims"]) == 1
        assert feedback["original_claims"][0]["text"] == original
        return {
            "edits": [{"claim_id": feedback["original_claims"][0]["claim_id"],
                       "replacement_text": corrected}],
            "append_answer_text": "",
        }

    def final_check(messages):
        verdict = unit_checker(messages)
        if final_axis == "population":
            verdict["body_ok"] = False
            for row in verdict["claims"]:
                row.update(status="partial", reason="Authored unresolved population support.")
                for unit in row["units"]:
                    unit["status"] = "partial"
        elif final_axis == "operation":
            for row in verdict["claims"]:
                for unit in row["units"]:
                    unit["relation_preserved"] = False
        elif final_axis == "quantity_requirement":
            verdict["requirements"][0]["conditions_preserved"] = False
        elif final_axis == "conditions":
            for row in verdict["claims"]:
                for unit in row["units"]:
                    unit["conditions_preserved"] = False
        return verdict

    adapter = Script([answer(original), rejected, patch, final_check])
    outcome = GenerationService(adapter, checker_adapter=adapter).generate(value)
    assert value == before
    assert len(adapter.calls) == outcome.budget["consumed_calls"] == 4
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert adapter.calls[3][1]["request_context"]["purpose"] == "joint_recheck"
    assert [attempt["stage"] for attempt in outcome.attempts] == [
        "generation", "joint_check", "semantic_repair", "joint_recheck",
    ]
    assert outcome.drafts[1]["precheck_transformations"][0]["requires_full_check"] is True
    assert "replacement_text" in outcome.drafts[1]["raw_model_output"]
    for field in ("tutor_question", "learner_attempt_evaluation"):
        assert outcome.drafts[0][field] == outcome.drafts[1][field] is None
    for key in outcome.drafts[0]["response"]:
        if key not in {"answer_text", "citations"}:
            assert outcome.drafts[0]["response"][key] == outcome.drafts[1]["response"][key]
    return outcome, corrected


def test_ordinary_source_only_unapproved_claim_uses_existing_patch_and_full_recheck():
    outcome, corrected = _ordinary_source_only_local_patch_case()
    assert outcome.succeeded, outcome.error
    assert outcome.response["answer_text"] == corrected
    assert [check["accepted"] for check in outcome.checks] == [False, True]
    assert outcome.delivered_projection["response"] == outcome.response


@pytest.mark.parametrize("axis", ["population", "operation", "quantity_requirement", "conditions"])
def test_ordinary_source_only_patch_cannot_override_failed_final_axis(axis):
    outcome, _ = _ordinary_source_only_local_patch_case(axis)
    assert not outcome.succeeded and outcome.response is None
    assert outcome.error is not None and outcome.delivered_projection == {}
    assert [check["accepted"] for check in outcome.checks] == [False, False]
    assert all(not draft["published"] for draft in outcome.drafts)
