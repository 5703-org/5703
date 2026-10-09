"""Aggregate actual validated ratings for the final delivered Week 9 responses.

Coordinator-only output joins blinded forms to a frozen study. No ratings are
invented, and rejected drafts retain their separate checker-agreement metrics.
"""

import argparse
import hashlib
import json
from pathlib import Path

from evaluation.week09.diagnostics import draft_observations
from evaluation.week09.review import import_reviews


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def projection_hash(value):
    return hashlib.sha256(
        json.dumps(
            {k: v for k, v in value.items() if k != "content_hash"},
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def outcome_type(record):
    outcome = record.get("outcome") or {}
    if record.get("error") or outcome.get("error"):
        return "execution_failure"
    response = outcome.get("response")
    if response is None:
        return "missing_response"
    kind = response.get("response_type")
    return (
        kind
        if kind in {"answer", "refusal", "clarification", "social"}
        else "unclassified_response"
    )


def final_binding(record, observations):
    """A delivery flag alone cannot establish which exact draft humans saw."""
    outcome = record.get("outcome") or {}
    if outcome_type(record) != "answer":
        return False, None
    delivered = outcome.get("delivered_projection") or {}
    actual = projection_hash(delivered)
    if (
        not delivered
        or delivered.get("response") != outcome["response"]
        or delivered.get("content_hash") != actual
    ):
        return True, None
    matches = [
        observation
        for observation in observations
        if observation["draft"].get("response") == outcome["response"]
        and observation["projection_hash"] == actual
        and observation["projection_binding"] == "matched"
        and (observation["checker"] or {}).get("accepted") is True
        and (observation["checker"] or {}).get("delivered_projection_hash") == actual
    ]
    if not matches:
        return True, None
    return True, max(matches, key=lambda item: item["revision"])


def dimension(rows, scheduled, terminal, published, key, *, allow_na=False):
    values = [row.get(key, "") if row else "" for row in rows]
    known = {"yes", "no", "partial"} | ({"not_applicable"} if allow_na else set())
    complete = terminal == scheduled and published > 0 and all(value in known for value in values)
    applicable = sum(value in {"yes", "no", "partial"} for value in values)
    positive = values.count("yes")
    return {
        "required_final_ratings": published,
        "determinate_final_ratings": sum(value in known for value in values),
        "unresolved_final_ratings": sum(value not in known for value in values),
        "not_applicable_final_ratings": values.count("not_applicable") if allow_na else 0,
        "applicable_rated_final_responses": applicable,
        "positive_final_responses": positive,
        "all_required_final_labels_complete": complete,
        "rate_among_applicable_published": positive / applicable
        if complete and applicable
        else None,
        "positive_deliveries_per_scheduled_request": positive / scheduled
        if complete and scheduled
        else None,
    }


def primary_metric(rows, scheduled, terminal, published):
    required = ("draft_correct", "useful", "within_step", "citation_support", "cumulative_leak")
    determinate = []
    qualified = []
    for row in rows:
        row = row or {}
        known = all(
            row.get(key)
            in (
                {"yes", "no", "partial", "not_applicable"}
                if key == "citation_support"
                else {"yes", "no", "partial"}
            )
            for key in required
        )
        determinate.append(known)
        qualified.append(
            known
            and all(row[key] == "yes" for key in ("draft_correct", "useful", "within_step"))
            and row["citation_support"] in {"yes", "not_applicable"}
            and row["cumulative_leak"] == "no"
        )
    complete = terminal == scheduled and published > 0 and all(determinate)
    count = sum(qualified)
    return {
        "definition": "A delivered hint rated correct, useful and within its current step, with supported or explicitly inapplicable citations and no cumulative leakage.",
        "required_final_ratings": published,
        "determinate_final_ratings": sum(determinate),
        "unresolved_final_ratings": len(rows) - sum(determinate),
        "all_required_final_labels_complete": complete,
        "qualified_delivered_hints": count,
        "rate_among_published_hints": count / published if complete else None,
        "qualified_deliveries_per_scheduled_request": count / scheduled
        if complete and scheduled
        else None,
    }


def summarize(study: Path, review: Path, forms: list[Path]):
    manifest_path = study / "frozen-study.json"
    manifest = read(manifest_path)
    if sha(manifest_path) != read(study / "freeze-receipt.json")["frozen_study_sha256"]:
        raise ValueError("Frozen study identity changed")
    schedule = {item["id"]: item for item in manifest["schedule"]}
    if len(schedule) != len(manifest["schedule"]):
        raise ValueError("Duplicate scheduled request")
    if any(
        item.get("stage") not in {"first_hint", "learner_attempt"} for item in schedule.values()
    ):
        raise ValueError("This primary human metric requires the registered hint stages")
    imported = import_reviews(review, forms)
    mapping = read(review / "coordinator-only/mapping.json")["rows"]
    observations = {}
    records = {}
    for identity, item in schedule.items():
        path = study / "outcomes" / (identity + ".json")
        if path.exists():
            record = read(path)
            if record.get("schedule") != item:
                raise ValueError("Outcome differs from frozen schedule")
            records[identity] = record
            observations[identity] = draft_observations(record)
    by_revision = {}
    for row in mapping:
        item = row["schedule"]
        identity = item["id"]
        if schedule.get(identity) != item or identity not in observations:
            raise ValueError("Review mapping differs from frozen study")
        matches = [o for o in observations[identity] if o["revision"] == row["revision"]]
        if (
            len(matches) != 1
            or matches[0]["projection_hash"] != row["projection_hash"]
            or matches[0]["projection_binding"] == "mismatch"
        ):
            raise ValueError("Review mapping differs from actual draft projection")
        if (matches[0]["checker"] or {}).get("accepted") != row["checker_accepted"]:
            raise ValueError("Review mapping differs from checker record")
        key = (identity, row["revision"])
        if key in by_revision:
            raise ValueError("Duplicate mapped draft revision")
        by_revision[key] = row["blind_id"]
    ratings = {(row["reviewer_id"], row["blind_id"]): row for row in imported["rows"]}
    binding = {
        identity: final_binding(row, observations[identity]) for identity, row in records.items()
    }
    results = {}
    for arm in sorted({item["arm"] for item in schedule.values()}):
        selected = [identity for identity, item in schedule.items() if item["arm"] == arm]
        terminal = sum(identity in records for identity in selected)
        kinds = [outcome_type(records[identity]) for identity in selected if identity in records]
        responses = sum(kind not in {"execution_failure", "missing_response"} for kind in kinds)
        published_ids = [
            identity for identity in selected if binding.get(identity, (False, None))[0]
        ]
        bound = {
            identity: by_revision.get((identity, binding[identity][1]["revision"]))
            if binding[identity][1]
            else None
            for identity in published_ids
        }
        reviewers = {}
        for reviewer in imported["reviewers_submitted"]:
            rows = [
                ratings.get((reviewer, bound[identity])) if bound[identity] else None
                for identity in published_ids
            ]
            reviewers[reviewer] = {
                "scheduled_requests": len(selected),
                "published_requests": len(published_ids),
                "answer_hint_deliveries": len(published_ids),
                "published_final_drafts_with_any_rating": sum(
                    bool(row and row["scored"]) for row in rows
                ),
                "correctness": dimension(
                    rows, len(selected), terminal, len(published_ids), "draft_correct"
                ),
                "citation_support": dimension(
                    rows,
                    len(selected),
                    terminal,
                    len(published_ids),
                    "citation_support",
                    allow_na=True,
                ),
                "coverage": dimension(
                    rows, len(selected), terminal, len(published_ids), "coverage_complete"
                ),
                "useful_supported_within_step_without_leakage": primary_metric(
                    rows, len(selected), terminal, len(published_ids)
                ),
            }
        results[arm] = {
            "scheduled_requests": len(selected),
            "terminal_requests": terminal,
            "unstarted_requests": len(selected) - terminal,
            "published_requests": len(published_ids),
            "answer_hint_deliveries": len(published_ids),
            "terminal_response_requests": responses,
            "refusal_responses": kinds.count("refusal"),
            "clarification_responses": kinds.count("clarification"),
            "social_responses": kinds.count("social"),
            "unclassified_responses": kinds.count("unclassified_response"),
            "failed_requests": kinds.count("execution_failure") + kinds.count("missing_response"),
            "operational_delivery_rate": len(published_ids) / len(selected) if selected else None,
            "published_final_review_bindings": sum(value is not None for value in bound.values()),
            "published_final_review_binding_unavailable": sum(
                value is None for value in bound.values()
            ),
            "reviewers": reviewers,
        }
    return {
        "schema": "week09_final_response_human_results_v2",
        "distribution": "Coordinator only; arm identities are unblinded.",
        "frozen_study_sha256": sha(manifest_path),
        "review_integrity_sha256": sha(review / "review-integrity.json"),
        "form_sha256": {
            path.name + ":" + str(number): sha(path) for number, path in enumerate(forms)
        },
        "outcome_sha256": {
            identity: sha(study / "outcomes" / (identity + ".json")) for identity in records
        },
        "human_scored_draft_rows": imported["scored_rows"],
        "raw_mapping_published_flag_used_as_delivery": False,
        "by_arm": results,
        "draft_level_checker_agreement": {
            key: imported[key]
            for key in (
                "comparable_ratings",
                "human_publishable_ratings",
                "human_unpublishable_ratings",
                "false_block_rate",
                "false_release_rate",
            )
        },
        "interpretation": [
            "Each reviewer has a separate result; no adjudication or cross-reviewer averaging is inferred.",
            "Blank and unsure final ratings keep the affected rate null. Partial is a determinate failure of the strict positive criterion.",
            "Citation not_applicable is accepted only as the reviewer's explicit judgment with a reason; it is excluded from the standalone applicable-citation denominator and neutral in the hint composite.",
            "Failed or draft-free requests count as nondelivery. No semantic incorrectness is assigned to them.",
            "published_requests is an alias for answer_hint_deliveries in this v2 report. Programmed refusal, clarification and social responses remain separate terminal responses and require no invented draft labels.",
            "Positive delivery rates use scheduled requests; semantic rates among published responses require all final labels for that metric and all scheduled outcomes to be terminal.",
            "Only an exact response and projection match to the accepted final check can use a human draft rating. Draft published flags alone are insufficient.",
            "The raw mapping.published flag describes the stored draft flag, which remains false in this offline generator. Delivery here is derived from the terminal outcome and verified final response/projection.",
            "These response judgments do not measure independent learning or delayed transfer.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--forms", required=True, type=Path, nargs="+")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or not {"private", "coordinator-only"}.intersection(args.output.parts):
        raise ValueError("Use a new private or coordinator-only output path")
    result = summarize(args.study, args.review, args.forms)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "written",
                "human_scored_draft_rows": result["human_scored_draft_rows"],
                "arms": len(result["by_arm"]),
            }
        )
    )


if __name__ == "__main__":
    main()
