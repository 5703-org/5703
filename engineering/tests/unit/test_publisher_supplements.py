"""Publisher alternatives retain original PDF observations and verified lineage."""

from copy import deepcopy
from hashlib import sha256

import pytest

from pipelines.supplements import apply_publisher_supplements


def fixture(tmp_path):
    alternative = "A labelled detector surrounds a thin foil."
    raw = ('<img src="/resources/figure-1" alt="' + alternative + '">').encode()
    original = tmp_path / "supplements" / "publisher.html"
    original.parent.mkdir()
    original.write_bytes(raw)
    entry = {
        "kind": "official_html_image_alt",
        "physical_page": 17,
        "pdf_sha256": "a" * 64,
        "source_url": "https://openstax.org/books/chemistry-2e/pages/preface",
        "storage_path": "supplements/publisher.html",
        "html_sha256": sha256(raw).hexdigest(),
        "image_resource": "figure-1",
        "text_sha256": sha256(alternative.encode()).hexdigest(),
        "review_evidence": "review/physical-0017.png",
        "review_scope": "Authored software fixture matching only this figure.",
    }
    unit = {
        "sequence": 1,
        "page": 17,
        "section": "Preface",
        "raw_text": "PDF figure labels",
        "cleaned_text": "PDF figure labels",
        "quality": "blocked",
        "issues": [
            {"code": "LOW_TEXT_IMAGE_PAGE", "severity": "blocking", "message": "Sparse native text"}
        ],
    }
    return entry, unit, alternative


def test_alternative_keeps_original_text_and_original_blocking_observation(tmp_path):
    entry, unit, alternative = fixture(tmp_path)
    original = deepcopy(unit)
    result = apply_publisher_supplements([unit], [entry], tmp_path, entry["pdf_sha256"])
    assert len(result) == 2
    native, supplied = result
    assert (
        native["raw_text"] == original["raw_text"]
        and native["cleaned_text"] == original["cleaned_text"]
    )
    assert native["quality"] == "supplemented" and native["issues"][0] == original["issues"][0]
    assert supplied["quality"] == "ready" and supplied["raw_text"] == alternative
    assert supplied["page"] == native["page"] == 17
    provenance = supplied["issues"][0]
    for key in (
        "pdf_sha256",
        "html_sha256",
        "physical_page",
        "source_url",
        "storage_path",
        "text_sha256",
        "review_scope",
    ):
        assert provenance[key] == entry[key]
    assert supplied["issues"][1]["code"] == "UNEXTRACTED_VISUAL_CONTENT"


def test_alternative_cannot_clear_unrelated_blocking_quality_issue(tmp_path):
    entry, unit, _ = fixture(tmp_path)
    unit["issues"].append(
        {"code": "UNREADABLE_TEXT", "severity": "blocking", "message": "Damaged reading order"}
    )
    result = apply_publisher_supplements([unit], [entry], tmp_path, entry["pdf_sha256"])
    assert result[0]["quality"] == "blocked"
    assert not any(issue["code"] == "PUBLISHER_ALTERNATIVE_LINKED" for issue in result[0]["issues"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("pdf_sha256", "b" * 64),
        ("html_sha256", "b" * 64),
        ("text_sha256", "b" * 64),
        ("source_url", "https://untrusted.example/books/chemistry-2e"),
        ("storage_path", "../outside.html"),
        ("physical_page", 18),
        ("review_scope", ""),
    ],
)
def test_unverified_or_mismatched_alternative_is_rejected(tmp_path, field, value):
    entry, unit, _ = fixture(tmp_path)
    expected_pdf = entry["pdf_sha256"]
    entry[field] = value
    with pytest.raises(ValueError):
        apply_publisher_supplements([unit], [entry], tmp_path, expected_pdf)


def test_duplicate_or_ambiguous_publisher_element_is_rejected(tmp_path):
    entry, unit, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="Duplicate"):
        apply_publisher_supplements([deepcopy(unit)], [entry, entry], tmp_path, entry["pdf_sha256"])
    path = tmp_path / entry["storage_path"]
    raw = path.read_bytes() * 2
    path.write_bytes(raw)
    entry["html_sha256"] = sha256(raw).hexdigest()
    with pytest.raises(ValueError, match="element/text"):
        apply_publisher_supplements([deepcopy(unit)], [entry], tmp_path, entry["pdf_sha256"])
