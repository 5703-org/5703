"""Exposed per-assertion selection diagnostic; never a production source override."""
import argparse
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "selection54.py"
BASE_SHA = "fbe037d1165f3941c8bcc3e2d897a2107c775b823af3dcdf59e7fa276a39e35a"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA:
    raise ValueError("IMMUTABLE_BASE_REQUIRED_BEFORE_IMPORT")
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE.parent))
import selection54 as unit

PRIOR_PINS = [
    (HERE.parent / "actual54/result54.json", "900227ca70d946431a0a39aaa1ad1f0a4d74a9d2bf5d3c4fae88c4894b773b0f", "TWO_OBSERVATIONS_CLOSED", Decimal("0.03824756")),
    (HERE.parent / "guided55/actual54/result54.json", "fd1496cfdfa3fdada4b15bfa264deb896cdd44d5eb9b51e9e955ec6c99ae199d", "STOPPED_RETAINED", Decimal("0.05046320")),
]
PRIOR_COST = Decimal("0.08871076")
PRIOR_SLOTS = 4
AUTH = "允许将同一71段教材、测试问题及已有回答发送到OpenRouter Gemini/Vertex，最多再8次、总额0.36美元，用于选证修复测试"
PLANS = [
    {"claim_id": "claim_9dd7ed3c15bfc4ae4368ad47_1", "unit_id": "U01", "assertion_hypotheses": [
        {"asserted_part": "Calvin-cycle scope and RuBP identity", "candidate_fragment_ids": ["F054"]},
        {"asserted_part": "RuBP is a five-carbon molecule with phosphate groups on both ends", "candidate_fragment_ids": ["F055"]},
        {"asserted_part": "RuBisCO combines CO2 with RuBP", "candidate_fragment_ids": ["F056"]},
        {"asserted_part": "the process is classified as carbon fixation", "candidate_fragment_ids": ["F056", "F057"]}
    ]},
    {"claim_id": "claim_9e6350bf8c8ac897dd6ce681_1", "unit_id": "U01", "assertion_hypotheses": [
        {"asserted_part": "the resulting six-carbon compound is immediately converted into two three-carbon compounds", "candidate_fragment_ids": ["F056"]},
        {"asserted_part": "the named three-carbon product is 3-PGA", "candidate_fragment_ids": ["F056", "F058"]}
    ]},
    {"claim_id": "claim_b85b9fa953bffc184b48ae2d_1", "unit_id": "U03", "assertion_hypotheses": [
        {"asserted_part": "ATP and NADPH jointly support the contextualized 3-PGA-to-G3P conversion", "candidate_fragment_ids": ["F058"]},
        {"asserted_part": "if the shared reduction predicate belongs to this unit, its scientific classification also needs proof", "candidate_fragment_ids": ["F058", "F059"]}
    ], "ownership_qualification": "Do not reinterpret ATP alone as a reducing agent or electron donor. Preserve the original unit text and full-claim joint predicate; do not invent an ownership convention."},
    {"claim_id": "claim_b85b9fa953bffc184b48ae2d_1", "unit_id": "U04", "assertion_hypotheses": [
        {"asserted_part": "the contextualized conversion uses ATP and NADPH to convert 3-PGA to G3P", "candidate_fragment_ids": ["F058"]},
        {"asserted_part": "that conversion is explicitly classified as reduction", "candidate_fragment_ids": ["F058", "F059"]}
    ]},
    {"claim_id": "claim_4bbb28fe7a90b6a3f87b6b75_1", "unit_id": "U02", "assertion_hypotheses": [
        {"asserted_part": "one G3P leaves the Calvin cycle", "candidate_fragment_ids": ["F009"]},
        {"asserted_part": "one net G3P is exported per three turns", "candidate_fragment_ids": ["F011"]},
        {"asserted_part": "exported G3P contributes specifically to carbohydrate formation", "candidate_fragment_ids": ["F019", "F020"]}
    ], "source_qualification": "F009 says other compounds, not carbohydrates. F019 ends with an unfinished become-a relation; separately select F020 for its object. Reread both original blocks including layout noise. Do not fabricate a joined quote or infer a continuation from adjacency alone."}
]
INSTRUCTION = """PROPOSED_ASSERTION_REPAIR_PLANS are exposed same-case development hypotheses, not Gold, source evidence, binding overrides or preapproved truth. Independently compare every proposed asserted part with its exact original full unit and the same complete permitted source blocks; reject a proposal that changes the claim or is not entailed. For each supported unit, explicitly select the union of its actually necessary proof fragments for all asserted parts, including named classifications and specific purposes. A source describing other compounds cannot establish a carbohydrate purpose; reaction inputs/products alone cannot establish a scientific classification. A candidate, sibling unit, reason or claim-wide citation union is not proof selected by this unit. Preserve any shared-predicate ownership uncertainty instead of claiming ATP independently donates electrons. Give a compact actual-part:actual-FID reason; distinguish classification from purpose. Before serializing, independently check that every selected unit fragment has an assessment in this SAME claim's citations under the fragment's actual owning evidence_id. This is an instruction to produce valid explicit source assessments, not authorization for a client to autofill or repair citations. If full proof is unavailable, use partial/unsupported and name the missing asserted part. Audit all 19 units, not only proposed plans. Keep all original fields, conditions, spans, bindings and publication gates. Return one complete minified JSON object."""

base_prepare = unit.prepared
base_save = unit.save_new
unit.HERE = HERE
unit.GROUP_CAP = Decimal("0.36") - PRIOR_COST

def prepare_guided():
    unit.require(unit.sha(BASE.read_bytes()) == BASE_SHA, "IMMUTABLE_REUSED_BASE_REQUIRED")
    for path, digest, expected_status, cost in PRIOR_PINS:
        unit.require(unit.sha(path.read_bytes()) == digest, "PRIOR_CLOSED_RESULT_CHANGED")
        prior = json.loads(path.read_text(encoding="utf-8"))
        unit.require(prior["status"] == expected_status and prior["submission_slots"] == 2 and
            Decimal(prior["known_cost_USD"]) == cost and Decimal(prior["UNKNOWN_hold_USD"]) == 0,
            "SETTLED_PINNED_PRIOR_REQUIRED")
    unit.require(sum(cost for _, _, _, cost in PRIOR_PINS) == PRIOR_COST, "PRIOR_COST_SUM_REQUIRED")
    body, old_wire, review = base_prepare()
    original_data = json.loads(body["messages"][1]["content"])
    data = deepcopy(original_data)
    by_claim = {row["claim_id"]: row for row in data["SOURCE_SYNTACTIC_UNITS"]}
    for plan in PLANS:
        claim = by_claim[plan["claim_id"]]
        allowed = {fid for entry in claim["actual_citation_scope"] for fid in entry["allowed_fragment_ids"]}
        proposed = {fid for part in plan["assertion_hypotheses"] for fid in part["candidate_fragment_ids"]}
        unit.require(plan["unit_id"] in {row["unit_id"] for row in claim["units"]} and
            proposed <= allowed and len(proposed) <= 12, "LEGAL_OWN_CLAIM_HYPOTHESES_REQUIRED")
    data["PROPOSED_ASSERTION_REPAIR_PLANS"] = PLANS
    restored = deepcopy(data)
    restored.pop("PROPOSED_ASSERTION_REPAIR_PLANS")
    unit.require(restored == original_data, "ORIGINAL_71_QUESTION_ANSWER_DATA_CHANGED")
    body["messages"][1]["content"] = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    body["messages"][0]["content"] += "\n" + INSTRUCTION
    wire = json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    bound = (Decimal(len(wire) + 4096) * Decimal("0.3") + Decimal(8192) * Decimal("2.5")) / Decimal(1000000)
    unit.require(len(wire) <= 98304 and bound <= unit.PER, "WIRE_AND_FULL_RESERVE_CAP_REQUIRED")
    review.update(work_unit="Exposed per-assertion hypothesis diagnostic within the same new grant",
        direct_user_quote=AUTH, grant_max_USD="0.36", grant_used_requests=PRIOR_SLOTS,
        grant_used_USD=str(PRIOR_COST), grant_remaining_requests=4, grant_remaining_USD="0.27128924",
        prior_result_pins=[unit.pin(path) for path, _, _, _ in PRIOR_PINS],
        implementation_pin=unit.pin(Path(__file__)), reused_implementation_pin=unit.pin(BASE),
        reused_implementation_verified_before_import=True,
        wire_bytes=len(wire), wire_sha256=unit.sha(wire), conservative_wire_price_bound_USD=str(bound),
        instruction_sha256=unit.sha(INSTRUCTION.encode()), current_work_unit_max_requests=2,
        only_outbound_delta="Five exposed per-assertion hypothesis plans and generic output citation audit; original 71 blocks, question, saved answer, claims/units/spans/bindings, schema, route and high/8192 settings unchanged",
        proposed_plans=PLANS, independent_held_out_or_causal_effect=False, production_hardcoding=False)
    return body, wire, review

def save_guided(path, value):
    if path.name == "result54.json":
        value.update(prior_grant_slots=PRIOR_SLOTS, prior_grant_known_USD=str(PRIOR_COST),
            grant_aggregate_slots=PRIOR_SLOTS + value["submission_slots"], new_grant_cap_USD="0.36",
            remaining_grant_slots=8 - PRIOR_SLOTS - value["submission_slots"],
            grant_aggregate_known_USD=str(PRIOR_COST + Decimal(value["known_cost_USD"])),
            exposed_case_guidance=True, general_source_selection_accuracy_proven=False)
    base_save(path, value)

unit.prepared = prepare_guided
unit.save_new = save_guided
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--review-sha256")
    args = parser.parse_args()
    if args.execute:
        raise SystemExit(unit.execute(args.review_sha256))
    body, wire, review = prepare_guided()
    unit.require(not (HERE / "actual54").exists(), "EXECUTED_REVIEW_IMMUTABLE")
    (HERE / "review54.json").write_bytes((json.dumps(review, ensure_ascii=False, indent=2) + "\n").encode())
    (HERE / "wire56.json").write_bytes(wire)
    print(json.dumps({"status": review["status"], "wire_bytes": len(wire), "wire_sha256": unit.sha(wire), "prior_cost": str(PRIOR_COST), "planned_requests": 2}))
