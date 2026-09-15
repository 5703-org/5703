"""Attach reviewed real PDF image extraction with immutable source lineage."""

import hashlib
import json
from pathlib import Path

from .clean import clean_source_text


def apply_image_transcriptions(units, entries, storage_root, pdf_hash):
    root = Path(storage_root).resolve()

    def verified(relative, expected):
        file = (root / relative).resolve()
        if not file.is_relative_to(root) or not file.is_file():
            raise ValueError(
                "A required image extraction artifact is missing or outside source storage"
            )
        raw = file.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Image extraction artifact hash mismatch")
        return raw

    additions, seen = [], set()
    for item in entries:
        if item.get("kind") != "pdf_image_transcription" or item["pdf_sha256"] != pdf_hash:
            raise ValueError("Image extraction belongs to different PDF bytes")
        page = item["physical_page"]
        if page in seen:
            raise ValueError("Duplicate image transcription for one page")
        seen.add(page)
        artifact = json.loads(
            verified(item["storage_path"], item["artifact_sha256"]).decode("utf-8")
        )
        if artifact["pdf_sha256"] != pdf_hash or artifact["physical_page"] != page:
            raise ValueError("Image extraction metadata does not match its source")
        verified(artifact["render_storage_path"], artifact["render_sha256"])
        verified(artifact["ocr_storage_path"], artifact["ocr_sha256"])
        transcript = artifact["transcript"]
        if (
            not transcript.strip()
            or hashlib.sha256(transcript.encode()).hexdigest() != item["text_sha256"]
        ):
            raise ValueError("Image transcription text does not verify")
        if (
            artifact["review_status"] != "agent_source_verified"
            or not artifact.get("ocr_model")
            or not artifact.get("review_method")
            or not artifact.get("review_limits")
        ):
            raise ValueError(
                "Real image extraction and an explicit bounded source review are required"
            )
        matching = [unit for unit in units if unit["page"] == page]
        if not matching:
            raise ValueError("No original PDF unit corresponds to this transcription")
        native = " ".join("".join(unit["raw_text"] for unit in matching).split())
        if hashlib.sha256(native.encode()).hexdigest() != artifact["normalized_native_text_sha256"]:
            raise ValueError("Image transcription review no longer matches PDF-native extraction")
        metadata = {
            **item,
            "ocr_model": artifact["ocr_model"],
            "review_method": artifact["review_method"],
            "review_limits": artifact["review_limits"],
            "render_sha256": artifact["render_sha256"],
            "ocr_sha256": artifact["ocr_sha256"],
        }
        for unit in matching:
            unresolved = [
                issue
                for issue in unit["issues"]
                if issue["severity"] == "blocking"
                and issue["code"] not in ("LOW_TEXT_IMAGE_PAGE", "EMPTY_UNIT")
            ]
            if unresolved:
                raise ValueError("Image transcription cannot clear an unrelated source failure")
            unit["quality"] = "supplemented"
            unit["issues"].append(
                {
                    "code": "PDF_IMAGE_TRANSCRIPTION_LINKED",
                    "severity": "resolved",
                    "message": "Original native extraction retained; a separate source-verified image transcription supplies searchable content.",
                    **metadata,
                }
            )
        additions.append(
            {
                "page": page,
                "section": matching[0]["section"] + " — Image text transcription",
                "raw_text": transcript,
                "cleaned_text": clean_source_text(transcript.replace("\n", "\n\n"), set()),
                "quality": "ready",
                "issues": [
                    {
                        "code": "PDF_IMAGE_TRANSCRIPTION",
                        "severity": "warning",
                        "message": "Real local OCR with bounded agent verification against the original page. This is image-derived text, not PDF-native text or independent human review.",
                        **metadata,
                    },
                    {
                        "code": "UNEXTRACTED_VISUAL_CONTENT",
                        "severity": "warning",
                        "message": artifact["review_limits"],
                    },
                ],
            }
        )
    result = sorted([*units, *additions], key=lambda unit: unit["page"])
    for index, unit in enumerate(result, 1):
        unit["sequence"] = index
    return result
