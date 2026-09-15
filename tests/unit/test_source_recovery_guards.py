"""Source recovery cannot erase native evidence or accept changed/unreviewed assets."""

from copy import deepcopy
import hashlib
import json
import pytest
from pipelines.supplements import apply_page_reviews
from pipelines.image_transcriptions import apply_image_transcriptions


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def source(code="LOW_TEXT_IMAGE_PAGE"):
    return {
        "sequence": 1,
        "page": 17,
        "section": "Preface",
        "raw_text": "Preface 3",
        "cleaned_text": "Preface 3",
        "quality": "blocked",
        "issues": [
            {"code": code, "severity": "blocking", "message": "Original source observation"}
        ],
    }


def review(category="substantive_short_text"):
    return {
        "physical_page": 17,
        "pdf_sha256": sha("authored PDF"),
        "normalized_native_text_sha256": sha("Preface 3"),
        "category": category,
        "reason": "Exact authored page inspected for this test",
        "review_evidence": "authored-review.json",
    }


def test_page_review_retains_original_issues_and_only_resolves_its_verified_scope():
    units = [source()]
    result = apply_page_reviews(units, [review()], sha("authored PDF"))
    assert result[0]["quality"] == "ready"
    assert result[0]["raw_text"] == "Preface 3"
    assert result[0]["issues"][0]["severity"] == "blocking"
    assert result[0]["issues"][-1]["code"] == "SOURCE_PAGE_REVIEW"
    excluded = apply_page_reviews(
        [source("EMPTY_UNIT")], [review("blank_page")], sha("authored PDF")
    )
    assert excluded[0]["quality"] == "excluded" and excluded[0]["raw_text"] == "Preface 3"
    with pytest.raises(ValueError, match="different extraction"):
        apply_page_reviews([source("PDF_PAGE_EXTRACTION_FAILED")], [review()], sha("authored PDF"))


@pytest.mark.parametrize(
    "change,match",
    [
        ({"pdf_sha256": sha("other PDF")}, "different PDF"),
        ({"normalized_native_text_sha256": sha("changed")}, "native extraction"),
        ({"physical_page": 99}, "current page"),
        ({"category": "substantive_visual_unextracted"}, "cannot be discarded"),
        ({"review_evidence": ""}, "inspection evidence"),
    ],
)
def test_page_review_rejects_wrong_source_location_hash_and_unsupported_discard(change, match):
    with pytest.raises(ValueError, match=match):
        apply_page_reviews([source()], [{**review(), **change}], sha("authored PDF"))


def artifact_fixture(tmp_path, changes=None):
    image = b"Authored image artifact bytes; this test validates lineage, not OCR recognition."
    raw_ocr = json.dumps(
        {
            "lines": [
                {
                    "text": "A visible label",
                    "confidence": 0.95,
                    "box": [[0, 0], [1, 0], [1, 1], [0, 1]],
                }
            ]
        }
    ).encode()
    (tmp_path / "page.png").write_bytes(image)
    (tmp_path / "raw-ocr.json").write_bytes(raw_ocr)
    transcript = "A visible label"
    artifact = {
        "pdf_sha256": sha("authored PDF"),
        "physical_page": 17,
        "transcript": transcript,
        "render_storage_path": "page.png",
        "render_sha256": sha(image),
        "ocr_storage_path": "raw-ocr.json",
        "ocr_sha256": sha(raw_ocr),
        "normalized_native_text_sha256": sha("Preface 3"),
        "review_status": "agent_source_verified",
        "ocr_model": {"name": "authored-test-model"},
        "review_method": "Authored guard fixture",
        "review_limits": "No geometry claim",
        **(changes or {}),
    }
    raw = json.dumps(artifact).encode()
    (tmp_path / "reviewed.json").write_bytes(raw)
    entry = {
        "kind": "pdf_image_transcription",
        "pdf_sha256": sha("authored PDF"),
        "physical_page": 17,
        "storage_path": "reviewed.json",
        "artifact_sha256": sha(raw),
        "text_sha256": sha(artifact["transcript"]),
    }
    return entry


def test_image_transcription_preserves_native_unit_and_links_separate_reviewed_text(tmp_path):
    entry = artifact_fixture(tmp_path)
    original = source()
    before = deepcopy(original)
    result = apply_image_transcriptions([original], [entry], tmp_path, sha("authored PDF"))
    assert len(result) == 2 and [u["sequence"] for u in result] == [1, 2]
    assert result[0]["quality"] == "supplemented" and result[0]["raw_text"] == before["raw_text"]
    assert result[0]["issues"][0] == before["issues"][0]
    assert result[1]["quality"] == "ready" and result[1]["raw_text"] == "A visible label"
    assert result[1]["page"] == 17 and "Image text transcription" in result[1]["section"]
    assert result[1]["issues"][0]["ocr_sha256"]
    assert result[1]["issues"][-1]["code"] == "UNEXTRACTED_VISUAL_CONTENT"


@pytest.mark.parametrize("filename", ["page.png", "raw-ocr.json", "reviewed.json"])
def test_image_transcription_rejects_tampered_render_ocr_and_review_bytes(tmp_path, filename):
    entry = artifact_fixture(tmp_path)
    path = tmp_path / filename
    path.write_bytes(path.read_bytes() + b" changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        apply_image_transcriptions([source()], [entry], tmp_path, sha("authored PDF"))


@pytest.mark.parametrize(
    "changes,match",
    [
        ({"review_status": "unreviewed"}, "explicit bounded source review"),
        ({"physical_page": 18}, "metadata does not match"),
        ({"normalized_native_text_sha256": sha("different native")}, "native extraction"),
        ({"transcript": ""}, "text does not verify"),
        ({"review_limits": ""}, "explicit bounded source review"),
        ({"render_storage_path": "../outside.png"}, "outside source storage"),
    ],
)
def test_image_transcription_rejects_unreviewed_misaligned_or_outside_artifacts(
    tmp_path, changes, match
):
    entry = artifact_fixture(tmp_path, changes)
    with pytest.raises(ValueError, match=match):
        apply_image_transcriptions([source()], [entry], tmp_path, sha("authored PDF"))


def test_image_transcription_rejects_wrong_pdf_duplicate_page_and_unrelated_blocker(tmp_path):
    entry = artifact_fixture(tmp_path)
    with pytest.raises(ValueError, match="different PDF"):
        apply_image_transcriptions([source()], [entry], tmp_path, sha("other PDF"))
    with pytest.raises(ValueError, match="Duplicate"):
        apply_image_transcriptions([source()], [entry, entry], tmp_path, sha("authored PDF"))
    with pytest.raises(ValueError, match="unrelated source failure"):
        apply_image_transcriptions(
            [source("UNREADABLE_TEXT")], [entry], tmp_path, sha("authored PDF")
        )


def test_image_transcription_native_rewrapping_is_explicit_but_reordered_text_fails(tmp_path):
    entry = artifact_fixture(tmp_path)
    wrapped = source()
    wrapped["raw_text"] = "Preface\n  3"
    accepted = apply_image_transcriptions([wrapped], [entry], tmp_path, sha("authored PDF"))
    assert accepted[0]["raw_text"] == "Preface\n  3"
    reordered = source()
    reordered["raw_text"] = "3 Preface"
    with pytest.raises(ValueError, match="native extraction"):
        apply_image_transcriptions([reordered], [entry], tmp_path, sha("authored PDF"))


def test_image_transcription_paragraph_order_is_part_of_pinned_text_identity(tmp_path):
    entry = artifact_fixture(tmp_path, {"transcript": "Visible row A\nVisible row B"})
    artifact = json.loads((tmp_path / "reviewed.json").read_text())
    artifact["transcript"] = "Visible row B\nVisible row A"
    altered = json.dumps(artifact).encode()
    (tmp_path / "reviewed.json").write_bytes(altered)
    entry["artifact_sha256"] = sha(altered)
    with pytest.raises(ValueError, match="text does not verify"):
        apply_image_transcriptions([source()], [entry], tmp_path, sha("authored PDF"))
