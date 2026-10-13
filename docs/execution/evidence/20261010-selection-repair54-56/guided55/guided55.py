"""Two explicitly guided source-selection diagnostics within the same new grant."""
import argparse
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import selection54 as unit

PRIOR = HERE.parent / "actual54/result54.json"
PRIOR_SHA = "900227ca70d946431a0a39aaa1ad1f0a4d74a9d2bf5d3c4fae88c4894b773b0f"
PRIOR_COST = Decimal("0.03824756")
PRIOR_SLOTS = 2
PLANS = [
    {"claim_id": "claim_9dd7ed3c15bfc4ae4368ad47_1", "unit_id": "U01", "proposed_fragment_ids": ["F054", "F055", "F056", "F057", "F064"],
     "verification_focus": "Verify cycle scope, RuBP identity, five-carbon identity and both-end phosphate attributes independently; references in a claim's citation union are not a unit's selected proof."},
    {"claim_id": "claim_9e6350bf8c8ac897dd6ce681_1", "unit_id": "U01", "proposed_fragment_ids": ["F056", "F058"],
     "verification_focus": "Verify the exact 3-PGA product identity as well as reaction participants and quantities; an unnamed three-carbon result alone does not establish its scientific name."},
    {"claim_id": "claim_b85b9fa953bffc184b48ae2d_1", "unit_id": "U03", "proposed_fragment_ids": ["F058", "F059"],
     "verification_focus": "Read the shared ATP/NADPH predicate jointly with the full claim. Verify actual roles and reduction classification without attributing electron donation or an independent reducing role to ATP."},
    {"claim_id": "claim_b85b9fa953bffc184b48ae2d_1", "unit_id": "U04", "proposed_fragment_ids": ["F058", "F059"],
     "verification_focus": "Verify the demonstrative's reaction referent and its explicit reduction classification. A conversion description alone is not source proof of that classification."},
    {"claim_id": "claim_4bbb28fe7a90b6a3f87b6b75_1", "unit_id": "U02", "proposed_fragment_ids": ["F009", "F010", "F011", "F019", "F020"],
     "verification_focus": "Verify three turns, one exported G3P and carbohydrate purpose. Read the separate purpose continuation despite layout noise; do not fabricate a joined quote or infer continuation from adjacency alone."}
]
INSTRUCTION = """PROPOSED_SOURCE_REPAIR_PLANS are exposed development hypotheses, not selected evidence, truth labels or binding overrides. Independently reread the same original complete source blocks and the full contextualized units. Accept only a candidate that establishes the asserted part; reject any unsupported proposal and state the exact gap. For each supported unit, explicitly select every necessary own-claim source ID and include it in the owning citation assessment. Do not infer a scientific classification solely from inputs/products or outside knowledge. Do not treat an unnamed product as a named substance or an unfinished relation as its complete object. In the existing reason use a compact literal part:actual-FID map, such as scope:ID;identity:ID;action:ID;quantity:ID;purpose:ID, replacing ID with only actually selected IDs and including only applicable asserted parts. All 19 units, all original fields, all conditions and all publication gates remain mandatory. Plans neither autofill output IDs nor permit optimistic supported labels. Return one complete minified JSON object."""

base_prepare = unit.prepared
base_save = unit.save_new
unit.HERE = HERE
unit.GROUP_CAP = Decimal("0.36") - PRIOR_COST

def prepare_guided():
    unit.require(unit.sha(PRIOR.read_bytes()) == PRIOR_SHA, "PRIOR_NEW_GRANT_RESULT_CHANGED")
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    unit.require(prior["status"] == "TWO_OBSERVATIONS_CLOSED" and prior["submission_slots"] == PRIOR_SLOTS and
        Decimal(prior["known_cost_USD"]) == PRIOR_COST and Decimal(prior["UNKNOWN_hold_USD"]) == 0, "SETTLED_PRIOR_WITHIN_NEW_GRANT_REQUIRED")
    body, old_wire, review = base_prepare()
    original_data = json.loads(body["messages"][1]["content"])
    data = deepcopy(original_data)
    by_claim = {row["claim_id"]: row for row in data["SOURCE_SYNTACTIC_UNITS"]}
    for plan in PLANS:
        claim = by_claim[plan["claim_id"]]
        allowed = {fid for entry in claim["actual_citation_scope"] for fid in entry["allowed_fragment_ids"]}
        unit.require(plan["unit_id"] in {row["unit_id"] for row in claim["units"]} and
            set(plan["proposed_fragment_ids"]) <= allowed and len(plan["proposed_fragment_ids"]) <= 12, "LEGAL_OWN_CLAIM_PROPOSAL_REQUIRED")
    data["PROPOSED_SOURCE_REPAIR_PLANS"] = PLANS
    restored = deepcopy(data)
    restored.pop("PROPOSED_SOURCE_REPAIR_PLANS")
    unit.require(restored == original_data, "ORIGINAL_71_QUESTION_ANSWER_DATA_CHANGED")
    body["messages"][1]["content"] = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    body["messages"][0]["content"] += "\n" + INSTRUCTION
    wire = json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    bound = (Decimal(len(wire) + 4096) * Decimal("0.3") + Decimal(8192) * Decimal("2.5")) / Decimal(1000000)
    unit.require(len(wire) <= 98304 and bound <= unit.PER, "GUIDED_WIRE_AND_FULL_RESERVE_CAP_REQUIRED")
    review.update(work_unit="Guided exposed-case diagnostic within the same new grant", grant_max_USD="0.36",
        grant_used_requests=PRIOR_SLOTS, grant_used_USD=str(PRIOR_COST), prior_result_pin=unit.pin(PRIOR),
        implementation_pin=unit.pin(Path(__file__)), reused_implementation_pin=unit.pin(HERE.parent / "selection54.py"),
        wire_bytes=len(wire), wire_sha256=unit.sha(wire), conservative_wire_price_bound_USD=str(bound),
        instruction_sha256=unit.sha(INSTRUCTION.encode()), current_work_unit_max_requests=2,
        only_outbound_delta="Add five exposed-case source-selection hypotheses and generic verification instructions; original question, saved answer, 71 original fragments, claims/units, bindings, schema, route and high/8192 settings unchanged",
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
    (HERE / "wire55.json").write_bytes(wire)
    print(json.dumps({"status": review["status"], "wire_bytes": len(wire), "wire_sha256": unit.sha(wire), "prior_cost": str(PRIOR_COST), "planned_requests": 2}))
