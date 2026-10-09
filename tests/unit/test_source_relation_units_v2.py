"""Compact producer/gate regressions; all semantic judgments are authored fixtures."""

from copy import deepcopy
import json
import pytest
from generation import GenerationService, RequestBudget
from generation.local_repair import VERSION as REPAIR
from generation.source_relations_v2 import VERSION, syntactic_units, assess_source_relations
from generation.teaching_plan_v6 import freeze_generation_policy
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer
from test_source_relation_contract import check_input, mismatched_quote


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
    out = GenerationService(adapter).generate(
        req(source_relation_policy=VERSION, generation_policy=freeze_generation_policy())
    )
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
        req(source_relation_policy=VERSION), RequestBudget(max_calls=2)
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
        req(source_relation_policy=VERSION, repair_policy=REPAIR)
    )
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4
    assert out.response["answer_text"].startswith("Photosynthesis uses light energy. [ev_001]")
    assert out.checks[-1]["source_relation_assessment"]["accepted"]


def test_factual_body_and_short_answer_are_both_checked_in_v2():
    def rejected(messages):
        value = unit_checker(messages)
        value["claims"][-1]["units"][0]["conditions_preserved"] = False
        return value

    out = GenerationService(
        Script([answer(short_answer="Photosynthesis uses light energy. [ev_001]"), rejected])
    ).generate(req(source_relation_policy=VERSION), RequestBudget(max_calls=2))
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"


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
        req(source_relation_policy=VERSION), RequestBudget(max_calls=2)
    )
    assert out.response is None and "INSUFFICIENT_CONTEXT_FULL_COVERAGE" in json.dumps(out.checks)
