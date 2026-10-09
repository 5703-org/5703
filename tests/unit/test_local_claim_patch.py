"""Local edits retain accepted science and still require complete final checks."""

from copy import deepcopy
import json

import pytest

from generation import GenerationService, RequestBudget
from generation.local_repair import VERSION, apply_claim_patch
from generation.parser import ResponseValidationError
from generation.reliability_v5 import response_claims
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer


def initial():
    return answer(
        "Photosynthesis uses light energy. [ev_001] Plants create matter from nothing. [ev_001]",
        short_answer="Photosynthesis uses light energy.",
    )


def rejected(messages):
    value = checker(messages, body_ok=False)
    value["claims"][1]["status"] = "unsupported"
    value["claims"][2].update(basis="textbook", status="partial", citations=[])
    return value


def patch(messages):
    data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
    return {
        "edits": [
            {
                "claim_id": row["claim_id"],
                "replacement_text": (
                    "Carbon dioxide supplies carbon for sugar. [ev_001]"
                    if row["answer_field"] == "answer_text"
                    else "Photosynthesis uses light energy. [ev_001]"
                ),
            }
            for row in data["original_claims"]
            if row["claim_id"] not in {kept["claim_id"] for kept in data["protected_exact_claims"]}
        ],
        "append_answer_text": "",
    }


def test_body_and_summary_repair_retain_exact_approved_span_and_receive_final_check():
    adapter = Script([initial(), rejected, patch, checker])
    out = GenerationService(adapter).generate(req(repair_policy=VERSION))
    assert out.succeeded, out.error
    assert out.response["answer_text"].startswith("Photosynthesis uses light energy. [ev_001]")
    assert out.response["short_answer"] == "Photosynthesis uses light energy. [ev_001]"
    assert out.budget["consumed_calls"] == 4 and len(out.checks) == 2
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert out.drafts[1]["precheck_transformations"][0]["requires_full_check"] is True
    assert "replacement_text" in out.drafts[1]["raw_model_output"]
    assert "LOCAL CLAIM BINDING V1" in adapter.calls[0][0][0]["content"]
    assert "STRICT CLAIM RECORD EXAMPLES" in adapter.calls[1][0][0]["content"]
    assert "CONSISTENT SUPPORT AND COVERAGE V1" in adapter.calls[1][0][0]["content"]


@pytest.mark.parametrize("violation", ["approved", "unknown", "duplicate", "unknown_source"])
def test_illegal_patch_is_blocked_before_final_check(violation):
    def malicious(messages):
        value = patch(messages)
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
        if violation == "approved":
            value["edits"][0]["claim_id"] = data["protected_exact_claims"][0]["claim_id"]
        elif violation == "unknown":
            value["edits"][0]["claim_id"] = "not-an-original-claim"
        elif violation == "duplicate":
            value["edits"].append(value["edits"][0])
        else:
            value["edits"][0]["replacement_text"] = "A source assertion [ev_999]."
        return value

    out = GenerationService(Script([initial(), rejected, malicious])).generate(
        req(repair_policy=VERSION)
    )
    assert out.response is None
    assert out.error["code"].startswith("CLAIM_PATCH_")
    assert out.budget["consumed_calls"] == 3 and len(out.checks) == 1


def test_appended_unsupported_science_cannot_bypass_complete_final_gate():
    def added(messages):
        value = patch(messages)
        value["append_answer_text"] = "Plants create matter from nothing. [ev_001]"
        return value

    def final_reject(messages):
        value = checker(messages, body_ok=False)
        value["claims"][2]["status"] = "unsupported"
        return value

    out = GenerationService(Script([initial(), rejected, added, final_reject])).generate(
        req(repair_policy=VERSION)
    )
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 4 and len(out.checks) == 2


def test_original_overlap_and_changed_protected_span_fail_closed():
    draft = initial()
    claims = response_claims(draft)
    proposal = {"edits": [{"claim_id": claims[1]["claim_id"], "replacement_text": ""}]}
    bad = deepcopy(claims)
    bad[1]["start"] = bad[0]["start"]
    bad[1]["end"] = bad[0]["end"]
    bad[1]["text"] = bad[0]["text"]
    with pytest.raises(ResponseValidationError, match="Original spans overlap"):
        apply_claim_patch(draft, bad, [], proposal, ["ev_001"])
    kept = deepcopy(claims[:1])
    kept[0]["text"] += " Changed."
    with pytest.raises(ResponseValidationError, match="Invalid approved spans"):
        apply_claim_patch(draft, claims, kept, proposal, ["ev_001"])


def test_conditions_negation_numbers_and_approved_source_binding_are_retained_verbatim():
    draft = answer(
        "At 2.5 kPa without heating, the pressure does not change [ev_001]. Extra. [ev_001]"
    )
    claims = response_claims(draft)
    final, _ = apply_claim_patch(
        draft,
        claims,
        claims[:1],
        {
            "edits": [{"claim_id": claims[1]["claim_id"], "replacement_text": ""}],
        },
        ["ev_001"],
    )
    assert final["answer_text"] == draft["answer_text"][: claims[1]["start"]]
    assert final["citations"] == ["ev_001"]


def test_legacy_full_repair_keeps_the_previous_protected_content_rejection():
    def old_rejected(messages):
        value = checker(messages, body_ok=False)
        value["claims"][1]["status"] = "unsupported"
        return value

    original = answer(
        "Photosynthesis uses light energy. [ev_001] Plants create matter from nothing. [ev_001]"
    )
    changed = answer(
        "Light powers photosynthesis. [ev_001] Carbon dioxide supplies carbon for sugar. [ev_001]"
    )
    adapter = Script([original, old_rejected, changed])
    out = GenerationService(adapter).generate(
        req(repair_policy="cause_specific_repair_v2"), RequestBudget(max_calls=4)
    )
    assert out.response is None and out.error["code"] == "REPAIR_CHANGED_APPROVED_CONTENT"
    assert "LOCAL CLAIM BINDING V1" not in adapter.calls[0][0][0]["content"]
    assert "CONSISTENT SUPPORT AND COVERAGE V1" not in adapter.calls[1][0][0]["content"]
