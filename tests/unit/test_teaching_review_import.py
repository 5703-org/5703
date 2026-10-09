"""Independent rating imports preserve missingness and applicability boundaries."""

import csv
import json

import pytest

from scripts.verify.teaching_contracts_live import import_reviews


FIELDS = [
    "blind_id",
    "factual_correctness_0_3",
    "source_support_0_3",
    "help_scope_0_3",
    "specific_usefulness_0_3",
    "attempt_feedback_0_3",
    "hint_leakage_yes_no",
    "notes",
]


@pytest.fixture
def study(tmp_path):
    target = tmp_path / "study"
    (target / "blind-review").mkdir(parents=True)
    packets = [
        {
            "blind_id": "R001",
            "outcome_available": True,
            "answer_mode": "textbook",
            "requested_help": "first_hint",
        },
        {
            "blind_id": "R002",
            "outcome_available": True,
            "answer_mode": "general_knowledge",
            "requested_help": "learner_attempt",
        },
        {
            "blind_id": "R003",
            "outcome_available": False,
            "answer_mode": "textbook",
            "requested_help": "direct",
        },
        {
            "blind_id": "R004",
            "outcome_available": True,
            "answer_mode": "textbook",
            "requested_help": "direct",
        },
    ]
    (target / "blind-review/review-packets.json").write_text(json.dumps(packets))
    (target / "frozen-study.json").write_text('{"study":"test-only"}')
    rows = [{field: "" for field in FIELDS} for _ in packets]
    for row, packet in zip(rows, packets, strict=True):
        row["blind_id"] = packet["blind_id"]
    return target, rows


def submit(target, rows, *, fields=FIELDS):
    form = target / "reviewer.csv"
    with form.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    result = target / "imported.json"
    import_reviews(target, [form], result)
    return json.loads(result.read_text())


def test_blank_review_preserves_nulls_and_zero_scores(study):
    target, rows = study
    result = submit(target, rows)
    reviewer = result["reviewers"][0]
    assert reviewer["scored_rows"] == 0
    assert len(reviewer["rows"]) == 4
    assert all(row["factual_correctness_0_3"] is None for row in reviewer["rows"])


def test_actual_zero_score_is_distinct_from_absent_score(study):
    target, rows = study
    rows[0]["factual_correctness_0_3"] = "0"
    rows[0]["source_support_0_3"] = "2"
    rows[0]["hint_leakage_yes_no"] = "yes"
    rows[1]["attempt_feedback_0_3"] = "3"
    result = submit(target, rows)["reviewers"][0]
    assert result["scored_rows"] == 2
    assert result["rows"][0]["factual_correctness_0_3"] == 0
    assert result["rows"][1]["source_support_0_3"] is None
    assert result["rows"][2]["factual_correctness_0_3"] is None


@pytest.mark.parametrize(
    ("row", "field", "value", "message"),
    [
        (0, "factual_correctness_0_3", "4", "integer 0-3"),
        (0, "factual_correctness_0_3", "2.0", "integer 0-3"),
        (0, "hint_leakage_yes_no", "maybe", "blank, yes or no"),
        (1, "source_support_0_3", "3", "not applicable in general knowledge"),
        (2, "factual_correctness_0_3", "0", "Absent responses"),
        (0, "attempt_feedback_0_3", "2", "only for learner-attempt"),
        (3, "hint_leakage_yes_no", "no", "not applicable to direct"),
    ],
)
def test_invalid_or_inapplicable_scores_reject_without_writing(study, row, field, value, message):
    target, rows = study
    rows[row][field] = value
    with pytest.raises(ValueError, match=message):
        submit(target, rows)
    assert not (target / "imported.json").exists()


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_exact_blind_id_coverage_is_required(study, mutation):
    target, rows = study
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows[-1]["blind_id"] = rows[0]["blind_id"]
    else:
        rows[-1]["blind_id"] = "R999"
    with pytest.raises(ValueError, match="exactly once"):
        submit(target, rows)


def test_columns_and_existing_imports_are_preserved(study):
    target, rows = study
    with pytest.raises(ValueError, match="columns differ"):
        submit(target, rows, fields=FIELDS[:-1])
    submit(target, rows)
    previous = (target / "imported.json").read_bytes()
    with pytest.raises(ValueError, match="Preserve previous"):
        submit(target, rows)
    assert (target / "imported.json").read_bytes() == previous
