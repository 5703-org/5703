"""Review validity and missing-data checks for accepted and rejected drafts."""

import csv
import hashlib
import json

import pytest

from evaluation.week09.diagnostics import diagnose, draft_observations, summarize
from evaluation.week09.review import export, import_reviews, submitted_evidence_scope, GUIDE


def example(accepted=False):
    projection = {
        "citation_views": [],
        "response": {"explanation": "Identify the known quantities."},
    }
    signature = hashlib.sha256(
        json.dumps(projection, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return {
        "schedule": {"id": "dev-1", "case_id": "case-1", "arm": "hidden-arm"},
        "request": {
            "question": "Give one hint.",
            "answer_mode": "textbook",
            "teaching_context": {"teaching_mode": "hint"},
        },
        "outcome": {
            "response": projection["response"] if accepted else None,
            "error": None if accepted else {"code": "SEMANTIC_CHECK_FAILED"},
            "drafts": [
                {"revision": 0, "response": projection["response"], "projection": projection}
            ],
            "checks": [
                {
                    "revision": 0,
                    "checker_contract_revision": 0,
                    "accepted": accepted,
                    "projection_hash": signature,
                }
            ],
        },
    }


def test_rejection_does_not_become_a_correctness_label():
    row = diagnose(example())
    assert row["checker_false_block_human"] is None
    assert row["context_sufficient_human"] is None
    report = summarize([example(), example(True)])
    assert report["published"] == 1
    assert report["error_codes"] == {"SEMANTIC_CHECK_FAILED": 1}
    assert report["checker_false_block_rate"] is None


def test_review_uses_matching_draft_revision_and_last_contract_check():
    row = example()
    later = {**row["outcome"]["checks"][0], "checker_contract_revision": 1, "accepted": True}
    row["outcome"]["checks"].append(later)
    observed = draft_observations(row)[0]
    assert observed["checker"] == later
    assert observed["projection_binding"] == "matched"


def test_tampered_draft_cannot_be_exported_as_checked(tmp_path):
    row = example()
    row["outcome"]["drafts"][0]["projection"]["response"]["explanation"] = "Altered answer"
    with pytest.raises(ValueError, match="projection mismatch"):
        export([row], [], tmp_path / "review")


def test_blind_export_keeps_rejected_draft_and_missing_ratings(tmp_path):
    target = tmp_path / "review"
    assert export([example()], [], target)["blank_rows"] == 2
    packet_text = (target / "reviewer-1/packets.json").read_text(encoding="utf-8")
    assert "Identify the known quantities" in packet_text
    assert "checker_accepted" not in packet_text
    assert "hidden-arm" not in packet_text
    report = import_reviews(
        target, [target / "reviewer-1/ratings.csv", target / "reviewer-2/ratings.csv"]
    )
    assert report["scored_rows"] == 0
    assert report["false_block_rate"] is None
    assert report["false_release_rate"] is None


def test_import_rejects_duplicate_or_unattributed_ratings(tmp_path):
    target = tmp_path / "review"
    export([example()], [], target)
    form = target / "reviewer-1/ratings.csv"
    with pytest.raises(ValueError, match="duplicate reviewer"):
        import_reviews(target, [form, form])
    with form.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows[0]["draft_correct"] = "yes"
    with form.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="reviewer name"):
        import_reviews(target, [form])


def test_retrieved_candidates_do_not_become_submitted_model_evidence(tmp_path):
    row = example()
    row["request"]["evidence"] = [
        {"evidence_id": "ev_001", "text": "Packed."},
        {"evidence_id": "ev_002", "text": "Removed."},
    ]
    row["outcome"]["evidence"] = row["request"]["evidence"][:1]
    target = tmp_path / "review"
    export([row], [], target)
    packet = json.loads((target / "reviewer-1/packets.json").read_text(encoding="utf-8"))[
        "packets"
    ][0]
    assert len(packet["retrieved_candidates"]) == 2
    assert packet["model_input_evidence"]["evidence"] == row["outcome"]["evidence"]
    assert packet["model_input_evidence"]["scope"] == "request_level_submitted_evidence"
    assert not packet["model_input_evidence"]["per_revision_verified"]
    assert "available_evidence" not in packet


def test_matching_transport_recovers_exact_initial_input_but_not_later_revision():
    row = example()
    source = [{"evidence_id": "ev_001", "text": "Actual submitted source."}]
    messages = [
        {
            "role": "system",
            "content": "CONTEXT_DATA_JSON:\n" + json.dumps({"CURRENT_EVIDENCE": source}),
        }
    ]
    row["outcome"].update(
        messages=messages,
        evidence=source,
        attempts=[
            {
                "stage": "generation",
                "request_submitted": True,
                "prompt_hash": hashlib.sha256(
                    json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest(),
            }
        ],
    )
    observation = draft_observations(row)[0]
    exact = submitted_evidence_scope(row, observation)
    assert exact["evidence"] == source and exact["per_revision_verified"]
    later = {**observation, "draft": {**observation["draft"], "revision": 1}}
    assert not submitted_evidence_scope(row, later)["per_revision_verified"]
    row["outcome"]["attempts"].append(
        {"stage": "generation_format_repair", "request_submitted": True, "prompt_hash": "different"}
    )
    assert not submitted_evidence_scope(row, observation)["per_revision_verified"]
    row["outcome"]["attempts"].pop()
    row["outcome"]["attempts"][0]["prompt_hash"] = "0" * 64
    assert not submitted_evidence_scope(row, observation)["per_revision_verified"]


def test_missing_submitted_receipt_preserves_uncertainty_instead_of_candidate_fallback():
    row = example()
    row["request"]["evidence"] = [{"evidence_id": "ev_001", "text": "Only retrieved."}]
    value = submitted_evidence_scope(row, draft_observations(row)[0])
    assert value["scope"] == "unavailable" and not value["evidence"]
    assert "unsure" in value["uncertainty"]
    assert "actually submitted" in GUIDE and "do not count" in GUIDE
