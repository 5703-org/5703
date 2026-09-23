import hashlib

import pytest

from evaluation.reliability.calibration import calibrate, validate_pool_review
from evaluation.reliability.catalogue import validate_frozen_plan


def synthetic_plan():
    """Authored software data; no actual textbook passage or heldout reference."""
    books = ["Biology 2e", "Chemistry 2e", "Concepts of Biology", "Anatomy and Physiology 2e"]
    return {
        "cases": [
            {
                "id": f"fixture-{i}",
                "group": f"family-{i // 2}",
                "split": "holdout" if (i // 2) % 3 == 0 else "development",
                "independent_review": None,
                "source_topics": [f"topic-{i % 4}"],
            }
            for i in range(120)
        ],
        "source_topics": {
            f"topic-{i}": {
                "passages": [
                    {
                        "title": book,
                        "text": "Authored source fixture, not textbook content.",
                        "text_hash": hashlib.sha256(
                            b"Authored source fixture, not textbook content."
                        ).hexdigest(),
                        "pages": [1],
                        "source_url": "https://assets.openstax.org/fixture-only-not-an-acquisition.pdf",
                    }
                ]
            }
            for i, book in enumerate(books)
        },
    }


def test_frozen_plan_validation_with_independent_synthetic_sources():
    plan = synthetic_plan()
    assert validate_frozen_plan(plan) is plan


@pytest.mark.parametrize(
    "change", ["count", "duplicate", "split", "review", "source", "hash", "pages", "url", "book"]
)
def test_frozen_plan_rejects_family_and_source_identity_corruption(change):
    plan = synthetic_plan()
    row = plan["cases"][1]
    passage = plan["source_topics"]["topic-0"]["passages"][0]
    if change == "count":
        plan["cases"].pop()
    elif change == "duplicate":
        row["id"] = plan["cases"][0]["id"]
    elif change == "split":
        row["split"] = "development"
    elif change == "review":
        row["independent_review"] = "invented"
    elif change == "source":
        row["source_topics"] = ["missing"]
    elif change == "hash":
        passage["text"] += " altered"
    elif change == "pages":
        passage["pages"] = []
    elif change == "url":
        passage["source_url"] = "https://example.com/unverified"
    else:
        passage["title"] = "Different book"
    with pytest.raises(ValueError):
        validate_frozen_plan(plan)


def judged_rows():
    return [
        {
            "question_id": str(i),
            "chunk_id": str(i),
            "group": str(i),
            "split": split,
            "score": score,
            "label": label,
            "model": "test-model",
            "revision": "a" * 40,
            "reviewer_id": "test-reviewer",
            "reviewed_at": "2026-09-16",
        }
        for i, (split, score, label) in enumerate(
            [
                ("development", -2.0, 0),
                ("development", 2.0, 1),
                ("holdout", -20.0, 1),
                ("holdout", 20.0, 0),
            ]
        )
    ]


def test_calibration_never_tunes_to_holdout_or_activates_proposal():
    report = calibrate(judged_rows(), model="test-model", revision="a" * 40)
    assert report["threshold"] == 0.0
    assert report["development"]["balanced_accuracy"] == 1
    assert report["holdout"]["balanced_accuracy"] == 0
    assert report["activated"] is False


@pytest.mark.parametrize("change", ["unreviewed", "mixed_model", "leaked_group", "duplicate"])
def test_calibration_rejects_invalid_judgment_pools(change):
    rows = judged_rows()
    if change == "unreviewed":
        rows[0]["reviewer_id"] = None
    elif change == "mixed_model":
        rows[0]["revision"] = "b" * 40
    elif change == "leaked_group":
        rows[2]["group"] = rows[0]["group"]
    else:
        rows.append(dict(rows[0]))
    with pytest.raises(ValueError):
        calibrate(rows, model="test-model", revision="a" * 40)


@pytest.mark.parametrize("change", ["missing_pair", "changed_score", "changed_source"])
def test_calibration_review_must_cover_the_exact_frozen_pool(change):
    from copy import deepcopy

    rows = judged_rows()
    for row in rows:
        row.update(
            question="Fixture question",
            processing_id="fixture-run",
            text="Fixture source",
            text_hash=hashlib.sha256(b"Fixture source").hexdigest(),
            source_title="Isolated fixture",
            source_url=None,
            section="Fixture",
            pages=[1],
        )
    pool = {
        "plan_sha256": "a" * 64,
        "corpus_release_id": "fixture-release",
        "model": "test-model",
        "revision": "a" * 40,
        "rows": rows,
    }
    assert validate_pool_review(pool, deepcopy(pool)) == rows
    reviewed = deepcopy(pool)
    if change == "missing_pair":
        reviewed["rows"].pop()
    elif change == "changed_score":
        reviewed["rows"][0]["score"] = 100.0
    else:
        reviewed["rows"][0]["text"] = "Changed fixture source"
        reviewed["rows"][0]["text_hash"] = hashlib.sha256(b"Changed fixture source").hexdigest()
    with pytest.raises(ValueError):
        validate_pool_review(pool, reviewed)
