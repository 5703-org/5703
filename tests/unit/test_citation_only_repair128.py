"""Citation-only preparation preserves text and still requires native validation."""

from copy import deepcopy
import json

import pytest

from generation.citation_only_repair_v1 import prepare_additions
from scripts.dev import checker_fixture_runner as runner
from test_compact_qa126 import execute, positive, prepared


def inputs(packet):
    claims = [dict(claim_id=cid, text=packet["answer"][c["answer_field"]][c["start"]:c["end"]], **c)
              for cid, c in packet["claims"].items()]
    sources = [dict(zip(packet["source_columns"], row)) for row in packet["sources"]]
    return claims, sources


def review(claim, sources):
    return {claim["claim_id"]: dict(status="supported", units={u["unit_id"]:dict(status="supported", source_ids=sources)
                                                               for u in claim["units"]})}


def repair_fixture():
    value, packet, _ = prepared(extra=True)
    row = value["rows"][0]
    label = next(l for l in value["labels"] if (l["case"], l["control"]) == (row["case"], row["control"]))
    claims, sources = inputs(packet)
    extra = next(s for s in sources if s["evidence_id"] == "ev_002")
    support = review(claims[0], [extra["source_id"]])
    return value, packet, label, claims, sources, support


def test_marker_only_candidate_is_detached_exact_retention_and_never_publishable():
    _, _, label, claims, sources, support = repair_fixture()
    before = deepcopy(label["draft"])
    fixed, receipt = prepare_additions(before, claims, sources, {claims[0]["claim_id"]:["ev_002"]}, support)
    assert before == label["draft"]
    assert fixed["answer_text"] == before["answer_text"] + " [ev_002]"
    assert fixed["short_answer"] == before["short_answer"]
    assert all(fixed[k] == v for k, v in before.items() if k not in {"answer_text", "citations"})
    assert receipt["original_text_retained"] and receipt["final_full_check_required"]
    assert receipt["rederive_claims_and_bindings_required"] and not receipt["old_verdict_reusable"]
    assert not receipt["publication_allowed"] and not receipt["semantic_support_locally_certified"]


def test_previously_uncited_proof_requires_displayed_citation_addition_and_fresh_native_check(tmp_path):
    value, packet, label, claims, sources, support = repair_fixture()
    verdict = positive(packet)
    extra_no = next(s["source_no"] for s in sources if s["evidence_id"] == "ev_002")
    quote = next(q[0] for q in packet["quote_pointers"] if q[1] == extra_no and q[3] - q[2] <= 600)
    verdict["claims"]["C1"]["p"] = [quote]
    blocked, _ = execute(value, verdict, tmp_path / "uncited")
    assert not blocked["results"][0]["technical_valid"]
    assert blocked["results"][0]["false_reject"] is None
    assert "SOURCE_REFERENCE_OUTSIDE_ACTUAL_CITATIONS" in json.dumps(blocked)
    fixed, _ = prepare_additions(label["draft"], claims, sources, {"C1":["ev_002"]}, support)
    label["draft"] = fixed
    fresh = runner.prepare(value)
    fresh_packet = json.loads(fresh["rows"][0]["body"]["messages"][-1]["content"])
    assert len(fresh_packet["citation_groups"]) == len(packet["citation_groups"]) + 1
    complete = positive(fresh_packet)
    accepted, _ = execute(fresh, complete, tmp_path / "rechecked")
    assert accepted["results"][0]["technical_valid"] and accepted["results"][0]["semantic_accept"]


@pytest.mark.parametrize("status", ["unsupported", "partial", "unknown"])
def test_incomplete_or_unsupported_content_is_not_a_citation_only_repair(status):
    _, _, label, claims, sources, support = repair_fixture()
    support["C1"]["units"][claims[0]["units"][0]["unit_id"]]["status"] = status
    with pytest.raises(ValueError, match="SUPPORT_INCOMPLETE_OR_NEGATIVE"):
        prepare_additions(label["draft"], claims, sources, {"C1":["ev_002"]}, support)


def test_out_of_result_citation_proof_cannot_admit_an_unrelated_added_marker():
    _, _, label, claims, sources, support = repair_fixture()
    outside = dict(sources[0], source_id="extra-source", evidence_id="ev_003")
    sources.append(outside)
    support["C1"]["units"][claims[0]["units"][0]["unit_id"]]["source_ids"] = ["extra-source"]
    with pytest.raises(ValueError, match="PROOF_OUTSIDE_RESULT_CITATIONS"):
        prepare_additions(label["draft"], claims, sources, {"C1":["ev_002"]}, support)


@pytest.mark.parametrize("fault", ["unretrieved", "duplicate", "already_cited", "stale_span", "missing_unit"])
def test_local_candidate_rejects_missing_provenance_or_stale_targets(fault):
    _, _, label, claims, sources, support = repair_fixture()
    ids = ["ev_002"]
    if fault == "unretrieved":
        ids = ["ev_999"]
    elif fault == "duplicate":
        ids *= 2
    elif fault == "already_cited":
        ids = ["ev_001"]
    elif fault == "stale_span":
        claims[0]["text"] = "Changed science."
    else:
        support["C1"]["units"] = {}
    with pytest.raises(ValueError):
        prepare_additions(label["draft"], claims, sources, {"C1":ids}, support)


def test_quote_role_limit_is_enforced_even_for_complete_in_scope_sources(tmp_path):
    value, packet, verdict = prepared(extra=True)
    # The source helper creates short blocks. Add a long bank block while retaining provenance.
    from test_source_refs121 import update_source
    update_source(value["source_bindings"]["cases"]["tiny"], "A" * 601 + " photosynthesis uses light energy. " + "B" * 600)
    value = runner.prepare(value)
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    verdict = positive(packet)
    source_no = verdict["groups"]["G1"]["s"][0]
    long_quote = next(q[0] for q in packet["quote_pointers"] if q[1] == source_no and q[3] - q[2] > 600)
    verdict["claims"]["C1"]["p"] = [long_quote]
    result, _ = execute(value, verdict, tmp_path / "long")
    assert not result["results"][0]["technical_valid"] and result["results"][0]["false_reject"] is None
    assert "SOURCE_QUOTE_POINTER_ROLE_INVALID" in json.dumps(result)


def test_complete_explicit_unsupported_assessment_stays_a_valid_negative(tmp_path):
    value, packet, verdict = prepared()
    verdict["claims"]["C1"]["d"] = "N"
    for unit in verdict["claims"]["C1"]["u"].values():
        unit["d"] = "N"
    result, _ = execute(value, verdict, tmp_path / "unsupported")
    row = result["results"][0]
    assert row["technical_valid"] and row["semantic_accept"] is False
    assert row["checker"]["qualification_decision_derivative"]["citation_group_coverage"] == "complete"


def test_short_answer_targets_are_explicitly_outside_body_only_v1():
    _, _, label, claims, sources, support = repair_fixture()
    draft = deepcopy(label["draft"])
    draft["short_answer"] = "Photosynthesis uses light energy. [ev_001]"
    claim = dict(claims[0], claim_id="short", answer_field="short_answer", start=0,
                 end=len(draft["short_answer"]), text=draft["short_answer"])
    claims.append(claim)
    support["short"] = deepcopy(support["C1"])
    with pytest.raises(ValueError, match="BODY_ADDITIONS_ONLY"):
        prepare_additions(draft, claims, sources, {"short":["ev_002"]}, support)
