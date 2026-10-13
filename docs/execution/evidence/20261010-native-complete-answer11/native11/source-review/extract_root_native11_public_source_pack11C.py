"""Read fixed public native11 artifacts and retain exact selected-source evidence.

Stdlib only. No network, database, browser, credential, private binding or Main access.
This verifies evidence identity and geometry, not semantic entailment.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path


BATCH = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-week10-native-pair-20261009-01")
SCOPE = BATCH / "scientific-native-closure11"
DIAG = SCOPE / "runtime" / "retained-provider-diagnostics"
OUT = Path(__file__).resolve().parent
PINS = []


def read_public(path: Path):
    data = path.read_bytes()
    PINS.append({"path_relative_to_batch": str(path.relative_to(BATCH)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return json.loads(data.decode("utf-8-sig"))


def require(value, message):
    if not value:
        raise ValueError(message)


def digest_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    browser = read_public(SCOPE / "browser" / "real-browser-live-qa-receipt01.json")
    budget = read_public(SCOPE / "runtime" / "budget-status-public01.json")
    outcome = read_public(DIAG / "native-generation-outcome01.json")
    model = read_public(DIAG / "slot-04-model-output01.json")
    reads = [
        read_public(DIAG / "slot-01-generation-read01.json"),
        read_public(DIAG / "slot-02-joint_check-read01.json"),
        read_public(DIAG / "slot-03-semantic_repair-read01.json"),
        read_public(DIAG / "slot-04-joint_recheck-read01.json"),
    ]
    question = browser["questions"][0]
    final = outcome["per_check_diagnostics"][-1]
    response = outcome["drafts"][-1]["response"]
    check = outcome["checks"][-1]
    raw = json.loads(model["raw"]["retained_raw_text"])
    require(outcome["actual_succeeded"] is True, "Actual final generation did not succeed")
    require(question["status"] == "PASS", "Q2 child receipt is not PASS")
    require(question["answer_text"] == response["answer_text"], "Published answer differs from actual final draft")
    require(question["answer_text_sha256"] == digest_text(response["answer_text"]), "Answer text digest mismatch")
    require(question["refresh_persisted"] is True, "Refresh persistence not observed")
    require(question["pre_refresh_prose_sha256"] == question["refreshed_prose_sha256"], "Reload prose changed")
    require(final["question"] == question["question"], "Question identity mismatch")
    require(final["parsed_original"] == raw, "Provider raw and diagnostic parsed JSON differ")
    require(check["accepted"] is True, "Final checker was not accepted")
    require(budget["provider_post_count"] == 4 and budget["unknown_cost_count"] == 0, "Budget observation mismatch")
    require(Decimal(budget["known_API_cost_USD"]) == Decimal("0.0173608"), "Budget known cost mismatch")
    require(budget["fully_settled"] is True and budget["open_claims"] == 0, "Provider scope not settled")

    physical_receipts = []
    total_cost = Decimal(0)
    for slot, receipt in enumerate(reads, 1):
        body = receipt["parsed_JSON_when_possible"]
        require(receipt["http_status"] == 200, "Non-200 physical response")
        require(receipt["redaction_changed_body"] is False, "Physical response body was changed")
        require(receipt["original_body_sha256"] == receipt["retained_body_sha256"], "Physical response digest mismatch")
        require(body["choices"][0]["finish_reason"] == "stop", "Non-stop physical response")
        cost = Decimal(str(body["usage"]["cost"]))
        total_cost += cost
        physical_receipts.append({"slot": slot, "http_status": 200, "finish_reason": "stop", "provider_request_id": body.get("id"), "model": body.get("model"), "known_API_cost_USD": str(cost), "retained_body_sha256": receipt["retained_body_sha256"]})
    require(total_cost == Decimal(budget["known_API_cost_USD"]), "Four physical response costs do not equal budget")
    require(reads[-1]["parsed_JSON_when_possible"]["choices"][0]["message"]["content"] == model["raw"]["retained_raw_text"], "Final physical message differs from retained model raw")

    table = model["check_data"]["SOURCE_FRAGMENTS"]
    fragments = {}
    for row in table["rows"]:
        item = dict(zip(table["columns"], row, strict=True))
        key = (item["evidence_id"], item["fragment_id"])
        require(key not in fragments, "Duplicate source alias")
        fragments[key] = item
    require(len(fragments) == 67, "Unexpected final checker fragment denominator")
    real_fragments = {item["fragment_id"]: item for item in outcome["attribution"]["fragments"]}
    real_claims = {item["claim_id"]: item for item in outcome["attribution"]["claims"]}
    checker_claims = {item["claim_id"]: item for item in raw["claims"]}
    require(len(checker_claims) == len(raw["claims"]) == len(final["claims"]) == 8, "Unexpected or duplicate claim denominator")
    selected_claims = []
    for index, claim in enumerate(final["claims"], 1):
        raw_claim = checker_claims[claim["claim_id"]]
        require(claim["text"] == response[claim["answer_field"]][claim["start"]:claim["end"]], "Actual claim geometry mismatch")
        require(claim["checker_citation_assessments"] == raw_claim["citations"], "Actual selected citations differ from raw checker")
        allowed = {item["evidence_id"]: set(item["allowed_fragment_ids"]) for item in claim["actual_citation_binding"]["citations"]}
        selected = []
        selected_real_ids = []
        for citation in raw_claim["citations"]:
            evidence_id = citation["evidence_id"]
            require(evidence_id in allowed, "Selected evidence not bound to claim")
            for alias in citation["fragment_ids"]:
                require(alias in allowed[evidence_id], "Selected fragment not allowed for claim")
                source = fragments[(evidence_id, alias)]
                real_id = check["fragment_aliases"][alias]
                provenance = real_fragments[real_id]
                require(provenance["evidence_id"] == evidence_id, "Source identity mismatch")
                require(provenance["exact_text"] == source["exact_text"], "Selected source text differs from checker input")
                require(provenance["text_hash"] == digest_text(source["exact_text"]), "Selected source text hash mismatch")
                selected.append({"evidence_id": evidence_id, "fragment_alias": alias, "relation": citation["relation"], "exact_text": source["exact_text"], "checker_input_complete_block": source["complete_block"], "provenance": provenance})
                selected_real_ids.append(real_id)
        require(set(selected_real_ids) == set(claim["normalized_claim"]["fragment_ids"]) == set(real_claims[claim["claim_id"]]["fragment_ids"]), "Normalized or published selected fragment set mismatch")
        selected_claims.append({"ordinal": index, "claim_id": claim["claim_id"], "answer_field": claim["answer_field"], "start": claim["start"], "end": claim["end"], "text": claim["text"], "actual_model_status": raw_claim["status"], "actual_model_reason": raw_claim["reason"], "selected_union": selected})

    pack = {
        "status": "PUBLIC_ACTUAL11_SOURCE_IDENTITY_AND_GEOMETRY_VERIFIED_NOT_ENTAILMENT",
        "input_pins": PINS,
        "actual_question": question["question"],
        "answer_id": question["answer_id"],
        "request_id": question["request_id"],
        "job_id": question["job_id"],
        "final_response": response,
        "actual_final_claim_denominator": len(selected_claims),
        "actual_checker_input_fragment_denominator": len(fragments),
        "actual_claims": selected_claims,
        "provider_scope": {"physical_POST_count": 4, "known_API_cost_USD": str(total_cost), "new_UNKNOWN_count": 0, "open_claims": 0, "fully_settled": True, "final_budget_status": budget["status"], "stop_exists": budget["stop_exists"], "historical_unknown_hold_USD": budget["campaign_prior_UNKNOWN_hold_USD"], "physical_response_receipts": physical_receipts},
        "raw_and_typed": {"raw_attempt_evaluation_ok_present": "attempt_evaluation_ok" in raw, "raw_attempt_evaluation_ok": raw.get("attempt_evaluation_ok"), "typed_attempt_evaluation_ok": final["typed_after_conditional_normalization"].get("attempt_evaluation_ok"), "server_not_applicable_predicate": final["attempt_not_applicable_server_predicate"], "strict_json_PASS": final["strict_json_PASS"], "conditional_full_Pydantic_PASS": final["conditional_full_Pydantic_PASS"], "actual_final_business_PASS": final["final_business_PASS"], "actual_final_pipeline_issues": final["all_actual_pipeline_issues"], "actual_first_check_accepted": outcome["checks"][0]["accepted"], "actual_final_check_accepted": check["accepted"], "native_stages": outcome["native_stages"]},
        "native_observations": {"Q2_child_status": question["status"], "Send_to_full_painted_cited_DOM_ms": question["tfull_ms"], "refresh_persisted": question["refresh_persisted"], "overall_browser_status": browser["status"], "overall_regression_status": browser["regression_question"]["status"], "failure_code": browser.get("failure_code"), "failure_exception_class": browser.get("failure_exception_class"), "source_assessment_is_separate": True},
        "source_verification_limit": "Directly verified retained checker-input table, provider physical response, exact selected aliases, public attribution identities/hashes and claim spans. No new original-book, database, wire-request transmission, source truth or human-Gold certification is claimed.",
        "reviewer_operations": {"API": 0, "database": 0, "browser": 0, "model": 0, "private_auth_binding_reads": 0, "main_writes": 0},
    }
    target = OUT / "ACTUAL_NATIVE11_SELECTED_SOURCE_PACK.json"
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(pack, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    result = target.read_bytes()
    print(json.dumps({"status": pack["status"], "actual_claim_count": len(selected_claims), "selected_source_pack_bytes": len(result), "selected_source_pack_sha256": hashlib.sha256(result).hexdigest(), "physical_POST_count": 4, "known_API_cost_USD": str(total_cost), "new_UNKNOWN_count": 0}, ensure_ascii=True))


if __name__ == "__main__":
    main()
