"""Offline source-audit selection, identity and quote-boundary checks."""

import copy
import json

import pytest

from scripts.verify import source_sufficiency_ai_pilot as pilot
from scripts.verify import source_sufficiency_development_audit as audit


def _case(group, book, family, present, *, text="source text", suffix=""):
    return {
        "concept_group": group,
        "book": book,
        "family": family,
        "declared_anchor_set_present_in_accepted_evidence": present,
        "case_id": f"{group}-{family}{suffix}",
        "accepted_evidence": [{"text": text}],
    }


def test_selection_is_concept_distinct_balanced_and_independent_of_input_order():
    missing = [
        _case(group, "Biology 2e", family, False)
        for group in ("a", "b", "c")
        for family in ("textbook_qa", "joint_tutoring")
    ]
    missing += [
        _case("d", "Concepts of Biology", family, False)
        for family in ("textbook_qa", "joint_tutoring")
    ]
    present = [
        _case("ap_short", "Anatomy and Physiology 2e", "textbook_qa", True, text="short"),
        _case("ap_long", "Anatomy and Physiology 2e", "textbook_qa", True, text="much longer text"),
        _case("bio", "Biology 2e", "joint_tutoring", True),
        _case("chem", "Chemistry 2e", "textbook_qa", True),
        _case("con", "Concepts of Biology", "joint_tutoring", True),
    ]
    cases = missing + present
    first = [case["case_id"] for case in pilot.selection(cases)]
    reversed_input = [case["case_id"] for case in pilot.selection(list(reversed(cases)))]
    assert first == reversed_input
    assert first == [
        "a-textbook_qa",
        "b-joint_tutoring",
        "c-textbook_qa",
        "d-joint_tutoring",
        "ap_short-textbook_qa",
        "bio-joint_tutoring",
        "chem-textbook_qa",
        "con-joint_tutoring",
    ]


def test_quote_binding_rejects_paraphrases_and_unsubmitted_sources():
    source = "The selectively permeable membrane controls the movement of water."
    request = {
        "item_id": "SC-001",
        "messages": [
            {"role": "system", "content": "Judge source sufficiency."},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "required_points": [{"point_id": "P1", "text": "Membrane permeability"}],
                        "accepted_sources": [{"source_id": "S1", "text": source}],
                    }
                ),
            },
        ],
    }
    rating = {
        "item_id": "SC-001",
        "overall": "sufficient",
        "reason": "The passage supports the point.",
        "points": [
            {
                "point_id": "P1",
                "status": "supported",
                "evidence": [{"source_id": "S1", "quote": "controls the movement of water"}],
                "reason": "The quoted passage states the mechanism.",
            }
        ],
    }
    assert pilot.validate_rating(rating, request) == rating
    paraphrase = copy.deepcopy(rating)
    paraphrase["points"][0]["evidence"][0]["quote"] = "all water moves freely"
    with pytest.raises(ValueError, match="exact substring"):
        pilot.validate_rating(paraphrase, request)
    unsubmitted = copy.deepcopy(rating)
    unsubmitted["points"][0]["evidence"][0]["source_id"] = "S2"
    with pytest.raises(ValueError, match="Unknown source"):
        pilot.validate_rating(unsubmitted, request)


def test_full_sufficiency_cannot_override_unjudged_required_point():
    request = {
        "item_id": "SC-002",
        "messages": [
            {"role": "system", "content": "Judge source sufficiency."},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "required_points": [{"point_id": "P2", "text": "Missing condition"}],
                        "accepted_sources": [{"source_id": "S1", "text": "A related topic."}],
                    }
                ),
            },
        ],
    }
    rating = {
        "item_id": "SC-002",
        "overall": "sufficient",
        "reason": "This conclusion conflicts with the point.",
        "points": [
            {
                "point_id": "P2",
                "status": "uncertain",
                "evidence": [],
                "reason": "The required condition is unclear.",
            }
        ],
    }
    with pytest.raises(ValueError, match="conflicts"):
        pilot.validate_rating(rating, request)


def test_official_anchor_rejects_changed_pdf_identity_and_changed_excerpt():
    text = "The source statement is traceable."
    source = {
        "source_kind": "official_openstax",
        "release_id": "release-1",
        "source_title": "Biology 2e",
        "original_sha256": "a" * 64,
        "source_url": "https://assets.openstax.org/original.pdf",
        "text": text,
        "text_hash": audit.sha256_text(text),
        "pages": [19],
    }
    audit.official_source(source, raw_hashes={"Biology 2e": "a" * 64}, release_id="release-1")
    altered_pdf = dict(source, original_sha256="b" * 64)
    with pytest.raises(ValueError, match="PDF hash"):
        audit.official_source(
            altered_pdf, raw_hashes={"Biology 2e": "a" * 64}, release_id="release-1"
        )
    altered_text = dict(source, text="A changed statement.")
    with pytest.raises(ValueError, match="text hash"):
        audit.official_source(
            altered_text, raw_hashes={"Biology 2e": "a" * 64}, release_id="release-1"
        )


def test_unknown_usage_has_no_cost_estimate():
    rates = {"cached": 0.003, "uncached": 0.15, "output": 0.6}
    assert pilot.estimated_cost(
        {"input_tokens": 100, "output_tokens": 20, "cache_hit_input_tokens": 40},
        rates,
    ) == pytest.approx((40 * 0.003 + 60 * 0.15 + 20 * 0.6) / 1_000_000)
    assert (
        pilot.estimated_cost(
            {"input_tokens": 100, "output_tokens": None, "cache_hit_input_tokens": 40},
            rates,
        )
        is None
    )
