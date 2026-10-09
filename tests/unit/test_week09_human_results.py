"""Authored fixtures validate denominator and final-response joins; no real ratings."""

import copy
import csv
import hashlib
import json

import pytest

from evaluation.week09.review import export
from scripts.verify.week09_human_results import projection_hash, summarize
from tests.unit.test_week09_review import example


def setup(tmp_path, *, failed=False, previous_draft=False):
    row = example(True)
    row["schedule"].update(arm="A", stage="first_hint")
    outcome = row["outcome"]
    outcome["response"]["response_type"] = "answer"
    projection = copy.deepcopy(outcome["drafts"][0]["projection"])
    signature = projection_hash(projection)
    projection["content_hash"] = signature
    outcome["drafts"][0].update(projection=projection, published=False)
    outcome["checks"][0]["delivered_projection_hash"] = signature
    outcome["checks"][0]["projection_hash"] = signature
    outcome["delivered_projection"] = copy.deepcopy(projection)
    if previous_draft:
        old = copy.deepcopy(outcome["drafts"][0])
        old["revision"] = 0
        outcome["drafts"][0]["revision"] = 1
        outcome["checks"][0]["revision"] = 1
        old["response"] = {"explanation": "Earlier answer."}
        old["projection"] = {"citation_views": [], "response": old["response"]}
        outcome["drafts"].insert(0, old)
    rows = [row]
    if failed:
        missing = copy.deepcopy(row)
        missing["schedule"]["id"] = "dev-2"
        missing["outcome"] = {
            "response": None,
            "error": {"code": "TIMEOUT"},
            "drafts": [],
            "checks": [],
        }
        rows.append(missing)
    study = tmp_path / "study"
    (study / "outcomes").mkdir(parents=True)
    manifest = {"schedule": [r["schedule"] for r in rows]}
    path = study / "frozen-study.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    (study / "freeze-receipt.json").write_text(
        json.dumps({"frozen_study_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}),
        encoding="utf-8",
    )
    for record in rows:
        (study / "outcomes" / (record["schedule"]["id"] + ".json")).write_text(
            json.dumps(record), encoding="utf-8"
        )
    review = tmp_path / "review"
    export(rows, [], review)
    return study, review, [review / "reviewer-1/ratings.csv", review / "reviewer-2/ratings.csv"]


def score(form, **overrides):
    with form.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        row.update(
            {
                "reviewer_name": "Reviewer One"
                if row["reviewer_id"] == "reviewer-1"
                else "Reviewer Two",
                "reason": "Synthetic unit fixture.",
                "draft_correct": "yes",
                "useful": "yes",
                "within_step": "yes",
                "citation_support": "yes",
                "coverage_complete": "yes",
                "cumulative_leak": "no",
                "publication_appropriate": "yes",
                **overrides,
            }
        )
    with form.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def result(study, review, forms):
    return summarize(study, review, forms)["by_arm"]["A"]


def test_blank_final_labels_are_null_even_when_delivered(tmp_path):
    study, review, forms = setup(tmp_path)
    actual = result(study, review, forms)
    assert actual["published_requests"] == actual["published_final_review_bindings"] == 1
    for reviewer in actual["reviewers"].values():
        assert reviewer["correctness"]["rate_among_applicable_published"] is None
        assert (
            reviewer["useful_supported_within_step_without_leakage"][
                "qualified_deliveries_per_scheduled_request"
            ]
            is None
        )


def test_false_raw_flag_scores_exact_final_and_failure_is_nondelivery(tmp_path):
    study, review, forms = setup(tmp_path, failed=True)
    for form in forms:
        score(form)
    actual = result(study, review, forms)
    assert actual["scheduled_requests"] == 2 and actual["failed_requests"] == 1
    assert actual["operational_delivery_rate"] == 0.5
    for reviewer in actual["reviewers"].values():
        assert reviewer["correctness"]["rate_among_applicable_published"] == 1.0
        assert reviewer["correctness"]["positive_deliveries_per_scheduled_request"] == 0.5
        assert (
            reviewer["useful_supported_within_step_without_leakage"][
                "qualified_deliveries_per_scheduled_request"
            ]
            == 0.5
        )


def test_unsure_is_null_and_partial_is_determinate_nonpositive(tmp_path):
    study, review, forms = setup(tmp_path)
    score(forms[0], draft_correct="unsure")
    score(forms[1], draft_correct="partial")
    actual = result(study, review, forms)["reviewers"]
    assert actual["reviewer-1"]["correctness"]["rate_among_applicable_published"] is None
    assert actual["reviewer-2"]["correctness"]["rate_among_applicable_published"] == 0.0


def test_missing_exact_final_projection_keeps_semantic_rate_null(tmp_path):
    study, review, forms = setup(tmp_path)
    for form in forms:
        score(form)
    path = study / "outcomes/dev-1.json"
    row = json.loads(path.read_text())
    row["outcome"]["delivered_projection"]["response"] = {"explanation": "Changed after check."}
    path.write_text(json.dumps(row), encoding="utf-8")
    actual = result(study, review, forms)
    assert actual["published_requests"] == actual["published_final_review_binding_unavailable"] == 1
    assert (
        actual["reviewers"]["reviewer-1"]["correctness"]["rate_among_applicable_published"] is None
    )


def test_only_final_revision_ratings_count(tmp_path):
    study, review, forms = setup(tmp_path, previous_draft=True)
    for form in forms:
        score(form)
    actual = result(study, review, forms)
    assert actual["published_requests"] == 1
    assert actual["reviewers"]["reviewer-1"]["correctness"]["required_final_ratings"] == 1


def test_explicit_inapplicable_citation_excluded_from_its_denominator(tmp_path):
    study, review, forms = setup(tmp_path)
    for form in forms:
        score(form, citation_support="not_applicable")
    reviewer = result(study, review, forms)["reviewers"]["reviewer-1"]
    assert reviewer["citation_support"]["rate_among_applicable_published"] is None
    assert reviewer["citation_support"]["applicable_rated_final_responses"] == 0
    assert (
        reviewer["useful_supported_within_step_without_leakage"][
            "qualified_deliveries_per_scheduled_request"
        ]
        == 1.0
    )


def test_changed_outcome_schedule_is_rejected(tmp_path):
    study, review, forms = setup(tmp_path)
    path = study / "outcomes/dev-1.json"
    row = json.loads(path.read_text())
    row["schedule"]["arm"] = "D"
    path.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen schedule"):
        result(study, review, forms)


def test_unstarted_request_keeps_quality_rate_null(tmp_path):
    study, review, forms = setup(tmp_path, failed=True)
    (study / "outcomes/dev-2.json").unlink()
    for form in forms:
        score(form)
    actual = result(study, review, forms)
    assert actual["unstarted_requests"] == 1 and actual["failed_requests"] == 0
    assert (
        actual["reviewers"]["reviewer-1"]["correctness"]["rate_among_applicable_published"] is None
    )


@pytest.mark.parametrize("kind", ["refusal", "clarification", "social"])
def test_programmed_nonanswer_keeps_scheduled_denominator_without_missing_draft_labels(
    tmp_path, kind
):
    study, review, forms = setup(tmp_path, failed=True)
    path = study / "outcomes/dev-2.json"
    record = json.loads(path.read_text())
    record["outcome"] = {
        "response": {"response_type": kind, "answer_text": "Authored nonanswer fixture."},
        "error": None,
        "drafts": [],
        "checks": [],
        "attempts": [],
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    for form in forms:
        score(form)
    actual = result(study, review, forms)
    assert actual["terminal_response_requests"] == 2
    assert actual["answer_hint_deliveries"] == 1
    assert actual[kind + "_responses"] == 1 and actual["failed_requests"] == 0
    assert actual["published_final_review_binding_unavailable"] == 0
    metric = actual["reviewers"]["reviewer-1"]["useful_supported_within_step_without_leakage"]
    assert metric["required_final_ratings"] == 1
    assert metric["qualified_deliveries_per_scheduled_request"] == 0.5
