"""Exact saved71 public-wire replay; imported diagnostics are never model labels."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

MAIN = Path(r"E:\5703\learning-assistant")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(MAIN))
from generation.checker_encoding import decode
from generation.source_evidence_combinations_v1 import plan_source_combinations
from generation.source_relations_v2 import assess_source_relations

BASE = MAIN / "docs/execution/evidence/20261011-checker-recovery58-59/capacity59"
paths = {
    "wire59": (BASE / "wire59-PREPARED-UNVERIFIED.json", "c14a0748a60e981f03d5f2d5731ba87048909514ac45d4e3d28828e656913b40"),
    "result59": (BASE / "actual59/result59.json", "230de5d6ff787f79cddd7161ebbcddbdc40c173af442de1e3081b3bf558e082b"),
    "taxonomy60": (HERE.parent / "5703-proof60-diagnosis/saved59-gap-taxonomy.json", "57e26c4b924846d078d827eb20bff12ac926d3c3c1e963ea3522c29ef4702dd0"),
    "helper60": (MAIN / "generation/source_evidence_combinations_v1.py", "ab69de76304a08370acd9483866fbc84ea364e77caab36c723796f1e40bc4f8a"),
}
loaded, pins = {}, {}
for key, (path, expected) in paths.items():
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected
    pins[key] = dict(path=str(path), bytes=len(data), sha256=expected)
    if path.suffix == ".json":
        loaded[key] = json.loads(data)
wire = loaded["wire59"]
data = decode(json.loads(wire["messages"][1]["content"]))
claims, bindings, fragments = (data[key] for key in ("CLAIMS", "ACTUAL_CITATION_BINDINGS", "SOURCE_FRAGMENTS"))
assert len(claims) == 10 and len(fragments) == 71
typed_original = json.loads(loaded["result59"]["provider_result"]["raw_text"])
assessment = loaded["result59"]["validation"]["original_full_local_checker_result"]["assessment"]
all_original_units = {(claim["claim_id"], unit["unit_id"]): unit
                      for claim in assessment["claims"] for unit in claim["obligations"]}
assert len(all_original_units) == 19
assert all(row["status"] == "supported" and row["relation_preserved"] is True
           and row["conditions_preserved"] is True for row in all_original_units.values())
before = deepcopy((claims, bindings, fragments, typed_original, assessment))
actual_plan = plan_source_combinations(claims, bindings, fragments, assessment)
assert actual_plan["proposals"] == actual_plan["candidate_fragment_ids"] == []
definite = [row for row in loaded["taxonomy60"]["cases"]
            if row["independent59_classification"]["compatible"] == "partial"]
assert len(definite) == 5
typed_imported = deepcopy(typed_original)
for case in definite:
    target = next(row for row in typed_imported["claims"] if row["claim_id"] == case["claim_id"])
    unit = next(row for row in target["units"] if row["unit_id"] == case["unit_id"])
    unit["status"] = "partial"
    unit["reason"] = "Imported exposed independent59 diagnostic, not a provider judgment: " + "; ".join(case["missing_selected_proof"])
contract, semantic, imported_assessment = assess_source_relations(typed_imported, claims, bindings, fragments)
assert contract == [] and not imported_assessment["accepted"]
plan = plan_source_combinations(claims, bindings, fragments, imported_assessment)
by_unit = {(row["claim_id"], row["unit_id"]): row for row in plan["proposals"]}
cases = []
for case in definite:
    proposal = by_unit.get((case["claim_id"], case["unit_id"]))
    new_ids = proposal["supplement_fragment_ids"] if proposal else []
    combined = list(dict.fromkeys([*case["current_selected_fragment_ids"], *new_ids]))
    groups = [row["fragment_ids"] for row in case["legal_candidate_groups"]]
    inventory = [group for group in groups if set(group) <= set(combined)]
    cases.append(dict(case_id=case["case_id"], claim_id=case["claim_id"], unit_id=case["unit_id"],
                      original_selected=case["current_selected_fragment_ids"], supplement_ids=new_ids,
                      combined_ids=combined, needed_candidate_groups=groups,
                      complete_previously_identified_candidate_group_present=bool(inventory),
                      covered_candidate_groups=inventory, proposal_present=proposal is not None,
                      lexical_inventory_only=True, semantic_support_certified=False))
negative_ids = {(case["claim_id"], case["unit_id"]) for case in definite}
normal = [(row["claim_id"], unit["unit_id"])
          for row in imported_assessment["claims"] for unit in row["obligations"]
          if (row["claim_id"], unit["unit_id"]) not in negative_ids]
assert len(normal) == 14 and all(identity not in by_unit for identity in normal)
assert before == (claims, bindings, fragments, typed_original, assessment)
report = dict(status="COMPLETED_OFFLINE_PUBLIC_WIRE_REPLAY", at_UTC=datetime.now(timezone.utc).isoformat(),
              input_pins=pins, original_labels="19 supported; exact original model result unchanged",
              actual_original_result_plan=actual_plan, original_live_result_triggers_repair=False,
              imported_negative_source="Five partial labels imported from exposed independent59 diagnosis; not a new model observation",
              imported_assessment_accepted=imported_assessment["accepted"], imported_contract_issues=contract,
              imported_semantic_defects=semantic, imported_plan=plan, cases=cases,
              candidate_inventory_coverage=sum(row["complete_previously_identified_candidate_group_present"] for row in cases),
              candidate_inventory_denominator=5, semantic_support_certified=False,
              normal_supported_units_unmodified=14, normal_units_receive_no_proposal=True,
              fragment_identity_namespace="Original saved wire F001-F071 aliases; no invented canonical DB identity/parent span or mapping metadata",
              normal_semantic_noninferiority_measured=False, new_model_requests=0, prior_inputs_unchanged=True)
for name, value in (("offline-replay61.json", report), ("imported-negative-assessment61.json", imported_assessment)):
    with (HERE / name).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
for key, (path, expected) in paths.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
print(json.dumps({key: report[key] for key in ("status", "original_live_result_triggers_repair", "candidate_inventory_coverage", "candidate_inventory_denominator", "normal_supported_units_unmodified", "new_model_requests")}, indent=2))
print(json.dumps(cases, ensure_ascii=False, indent=2))
