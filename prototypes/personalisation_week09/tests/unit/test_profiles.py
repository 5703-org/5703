"""Explicit profiles, immutable rules, independent teaching and missing ratings."""

from copy import deepcopy
import hashlib
import pytest
from pydantic import ValidationError
from personalisation import compile_profile
from personalisation.study import TeachingStudyService
from personalisation.rubric import rating_template, validate_rating


def test_profile_compiler_stable_distinct_and_explicit_invalid_values_fail():
    outputs = [
        compile_profile({"level": level}) for level in ("beginner", "intermediate", "advanced")
    ]
    assert len({p["policy_hash"] for p in outputs}) == 3
    assert compile_profile({"level": "beginner"}) == outputs[0]
    assert outputs[0]["compiler_version"] == "profile_rules_v1"
    assert outputs[0]["source_version"] == 1
    assert compile_profile(None)["fallback_reason"] == "missing_legacy_profile"
    with pytest.raises(ValidationError):
        compile_profile({"level": "expert"})
    with pytest.raises(ValidationError):
        compile_profile({"language": "fr"})


def test_temporary_override_does_not_mutate_saved_profile_and_off_keeps_no_profile_policy():
    saved = {"level": "advanced", "style": "detailed", "version": 3}
    before = deepcopy(saved)
    compiled = compile_profile(saved, turn_message="Explain it more simply")
    assert saved == before and compiled["profile"]["level"] == "advanced"
    assert compiled["turn_override"]["level"] == "beginner"
    assert compiled["source_version"] == 3
    disabled = compile_profile(saved, use_profile=False)
    assert disabled["profile"] is None and disabled["policy"] == ""


def test_three_by_three_study_freezes_base_and_evidence_and_c0_hides_level():
    text = "Photosynthesis converts light energy to chemical energy."
    evidence = [
        {
            "evidence_id": "ev_001",
            "chunk_id": "c1",
            "asset_id": "a1",
            "processing_id": "p1",
            "source_title": "Authored fixture",
            "section": "Science",
            "pages": [1],
            "locator": "page 1",
            "text": text,
            "text_hash": hashlib.sha256(text.encode()).hexdigest(),
            "context_order": 1,
        }
    ]
    base = {"response_type": "answer", "answer_text": text + " [ev_001]", "citations": ["ev_001"]}
    original = deepcopy(base)
    rows = TeachingStudyService().matrix(run_id="r1", base_answer=base, evidence=evidence)
    assert len(rows) == 9 and all(row["state"] == "succeeded" for row in rows)
    assert base == original and len({row["base_hash"] for row in rows}) == 1
    c0 = [row for row in rows if row["condition"] == "C0"]
    assert c0[0]["messages"] == c0[1]["messages"] == c0[2]["messages"]
    assert all(
        row["response"]["invariant_check"]["human_review_status"] == "pending" for row in rows
    )
    assert all(row["budget"]["consumed_calls"] == 1 for row in rows)


def test_missing_independent_ratings_are_not_zero_or_passed():
    sheet = rating_template("item", "rater")
    assert validate_rating(sheet) == {"complete": False, "gates_passed": None}
    sheet["ratings"] = {name: 2 for name in sheet["ratings"]}
    assert validate_rating(sheet) == {"complete": True, "gates_passed": True}
    sheet["ratings"]["correctness"] = 0
    assert validate_rating(sheet)["gates_passed"] is False
