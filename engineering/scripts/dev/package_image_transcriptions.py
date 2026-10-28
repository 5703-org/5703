"""Freeze reviewed real-OCR derivatives and source matching into corpus configuration."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/openstax"
STORAGE = ROOT / "artifacts/storage"


def freeze(raw, suffix):
    sha = hashlib.sha256(raw).hexdigest()
    relative = f"supplements/{sha}{suffix}"
    path = STORAGE / relative
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        with path.open("xb") as stream:
            stream.write(raw)
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise RuntimeError("Immutable extraction artifact failed verification")
    return relative, sha


def main():
    runtime_raw = (EVIDENCE / "ocr/runtime.json").read_bytes()
    runtime = json.loads(runtime_raw)
    assets = {
        json.loads(file.read_text())["slug"]: json.loads(file.read_text())
        for file in EVIDENCE.glob("*-acquisition.json")
    }
    readers, entries = {}, []
    for review_path in sorted((EVIDENCE / "transcriptions").glob("*.json")):
        reviewed = json.loads(review_path.read_text(encoding="utf-8"))
        if "transcript" not in reviewed:
            continue
        page = reviewed["physical_page"]
        slug = next(
            key for key, asset in assets.items() if asset["sha256"] == reviewed["pdf_sha256"]
        )
        if reviewed["review_status"] != "agent_source_verified":
            raise RuntimeError(f"Image review is incomplete: {review_path.name}")
        ocr_path = EVIDENCE / f"ocr/{slug}/physical-{page:04}-300dpi.ocr.json"
        ocr_raw = ocr_path.read_bytes()
        ocr = json.loads(ocr_raw)
        if ocr["physical_page"] != page or ocr["pdf_sha256"] != reviewed["pdf_sha256"]:
            raise RuntimeError("OCR and source review refer to different originals")
        image_raw = (ROOT / ocr["image_path"]).read_bytes()
        render_path, render_hash = freeze(image_raw, ".png")
        if render_hash != ocr["image_sha256"]:
            raise RuntimeError("Reviewed OCR rendering has changed")
        ocr_storage, ocr_hash = freeze(ocr_raw, ".json")
        reader = (
            readers.setdefault(slug, PdfReader(ROOT / assets[slug]["raw_path"]))
            if slug not in readers
            else readers[slug]
        )
        native = " ".join((reader.pages[page - 1].extract_text() or "").split())
        artifact = {
            "schema_version": "pdf-image-transcription-v1",
            **reviewed,
            "normalized_native_text_sha256": hashlib.sha256(native.encode()).hexdigest(),
            "render_storage_path": render_path,
            "render_sha256": render_hash,
            "ocr_storage_path": ocr_storage,
            "ocr_sha256": ocr_hash,
            "ocr_model": runtime,
            "ocr_runtime_manifest_sha256": hashlib.sha256(runtime_raw).hexdigest(),
            "review_evidence": review_path.relative_to(ROOT).as_posix(),
            "source_url": assets[slug]["final_url"],
            "render_dpi": ocr["dpi"],
            "attribution": "OpenStax / Rice University. Access for free at openstax.org. Source PDF: CC BY-NC-SA 4.0.",
        }
        raw = (json.dumps(artifact, indent=2, ensure_ascii=False) + "\n").encode()
        path, sha = freeze(raw, ".json")
        entries.append(
            {
                "kind": "pdf_image_transcription",
                "physical_page": page,
                "pdf_sha256": reviewed["pdf_sha256"],
                "storage_path": path,
                "artifact_sha256": sha,
                "text_sha256": hashlib.sha256(reviewed["transcript"].encode()).hexdigest(),
                "review_evidence": review_path.relative_to(ROOT).as_posix(),
            }
        )
    # A portrait has no body text for OCR to recover. The exact publisher photo
    # description, also supported by the adjacent PDF caption, is separately cited.
    portrait = json.loads((EVIDENCE / "anatomy-html-604.json").read_text())
    resource = "f832b04d5817cad33bb7431bb7e3890e802fa1e1"
    matched = [image for image in portrait["images"] if image["src"].endswith("/" + resource)]
    if len(matched) != 1:
        raise RuntimeError("Exact publisher portrait description is unavailable")
    entries.append(
        {
            "kind": "official_html_image_alt",
            "physical_page": 604,
            "pdf_sha256": assets["anatomy-and-physiology-2e"]["sha256"],
            "source_url": portrait["final_url"],
            "html_sha256": portrait["html_sha256"],
            "storage_path": portrait["storage_path"],
            "image_resource": resource,
            "text_sha256": hashlib.sha256(matched[0]["alt"].encode()).hexdigest(),
            "review_evidence": "evidence/openstax/inspection/anatomy-and-physiology-2e/physical-0604.png",
            "review_scope": "Actual portrait matched to the official figure14.27 photo alternative and the native PDF caption on physical605. OCR correctly produced no portrait identity; identity comes from the publisher caption/alternative, not face recognition or inferred OCR.",
            "remaining_limits": "Photo pixels and appearance are not recreated by the short text description; independent human scientific review remains pending.",
        }
    )
    expected = {
        (book["pdf_sha256"], page["physical_pdf_page"])
        for book in json.loads(
            (EVIDENCE / "pdf-low-text-decisions.json").read_text(encoding="utf-8")
        )["books"]
        for page in book["pages"]
        if page["category"] == "substantive_visual_unextracted"
    }
    expected.update(
        {
            (assets["anatomy-and-physiology-2e"]["sha256"], 470),
            (assets["chemistry-2e"]["sha256"], 1195),
        }
    )
    actual = {(item["pdf_sha256"], item["physical_page"]) for item in entries}
    if actual != expected or len(actual) != len(entries):
        raise RuntimeError(
            f"Image-source coverage differs from the actual diagnosed page set: missing={expected - actual}, extra={actual - expected}"
        )
    manifest = {
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
        "scope": "Exact source-derived OCR transcriptions with bounded agent review, plus one exact publisher portrait alternative. Originals/raw OCR retained; not mock source content and not independent human validation.",
    }
    (EVIDENCE / "image-transcription-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "entries": len(entries),
                "transcribed_pages": len(entries) - 1,
                "publisher_description_pages": 1,
            }
        )
    )


if __name__ == "__main__":
    main()
