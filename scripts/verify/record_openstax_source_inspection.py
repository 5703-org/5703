"""Assemble immutable-source identity and explicitly bounded visual inspection evidence."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "evidence/openstax"
BOOKS = {
    "anatomy-and-physiology-2e": {
        "year": 2022,
        "toc": [7, 16],
        "preface": 17,
        "offset": 16,
        "samples": [
            (
                13,
                None,
                "TOC continuation contains Chapter20/21/22 entries with target printed pages833/917/973. These are not actual body section starts.",
            ),
            (
                17,
                "1",
                "Two-column Preface. Reading order must remain column-aware; this sample establishes layout complexity, not a proved order failure.",
            ),
            (
                23,
                None,
                "Actual Chapter1 opener: title, full-width image, Chapter Objectives, INTRODUCTION. Printed7 is inferred from TOC/offset; there is no visible page number on this opener.",
            ),
            (
                861,
                "845",
                "Running header20.2 appears on a page beginning with earlier20.1 interactive links; actual20.2 heading occurs midpage.",
            ),
            (
                1012,
                "996",
                "Sleep-apnea boxed discussion precedes actual22.4 Gas Exchange heading near the bottom; page-level labels cannot identify every preceding block.",
            ),
            (
                1210,
                "1194",
                "Thirst-regulation diagram contains labeled boxes and causal arrows absent from native text, although Figure26.10 caption and body prose are present.",
            ),
        ],
    },
    "biology-2e": {
        "year": 2018,
        "toc": [7, 20],
        "preface": 21,
        "offset": 20,
        "samples": [
            (21, "1", "Preface identifies second-edition textbook context."),
            (
                29,
                None,
                "Chapter1 opener has chapter outline before introduction and actual1.1 heading. Printed9 is inferred from TOC/offset, not a visible label.",
            ),
            (
                225,
                "205",
                "Running header7.6 occurs before earlier7.5 text/images and actual7.6 heading midpage.",
            ),
            (
                226,
                "206",
                "Metabolic pathway illustration has internal labels and arrows separate from native caption/prose.",
            ),
            (
                229,
                "209",
                "Glycolysis pathway has ATP/NAD and molecular annotations that native text does not fully reproduce.",
            ),
        ],
    },
    "chemistry-2e": {
        "year": 2019,
        "toc": [7, 13],
        "preface": 15,
        "offset": 14,
        "samples": [
            (
                17,
                "3",
                "Three science panels have only nine native characters; detailed low-text decision and rejected/accepted publisher matches recorded separately.",
            ),
            (
                170,
                "156",
                "Chemical equation graphics and subscript labels coexist with body text/captions; preserving prose alone cannot establish equation completeness.",
            ),
            (
                189,
                "175",
                "Displayed redox equations and Check Your Learning answer are visible in the image but missing from native text; table/prose survives. Actual4.3 begins midpage.",
            ),
            (
                694,
                "680",
                "Acid/base molecular illustrations, H+ notation and prose need symbol/diagram fidelity checks; extraction may separate superscripts across lines.",
            ),
            (
                708,
                "694",
                "Large experiment photograph, caption and worked-example equation share one page; a character count cannot test scientific layout completeness.",
            ),
        ],
    },
    "concepts-biology": {
        "year": 2013,
        "toc": [7, 13],
        "preface": 15,
        "offset": 14,
        "samples": [
            (
                131,
                None,
                "Chapter5 Photosynthesis opener has Chapter Outline entries5.1-5.3 before actual5.1. Printed117 inferred from TOC/offset; no visible number on opener.",
            ),
            (132, "118", "Photosynthesis image/caption and introductory prose share page."),
            (
                136,
                "122",
                "Actual5.2 heading, image labels, caption and Link to Learning callout require separate block roles.",
            ),
            (
                138,
                "124",
                "Light-dependent-reaction prose and illustration coexist; H2/H+ scientific notation needs faithful extraction.",
            ),
            (
                141,
                "127",
                "Calvin-cycle diagram contains stage labels and arrows beyond caption/prose. Original visual remains essential when text misses internal relationships.",
            ),
        ],
    },
}


def main():
    books = []
    for slug, details in BOOKS.items():
        a = json.loads((E / f"{slug}-acquisition.json").read_text(encoding="utf-8"))
        source = ROOT / a["raw_path"]
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        assert digest == a["sha256"], "Immutable source hash changed: " + slug
        scan = json.loads(
            (E / "inspection" / f"{slug}-low-text-scan.json").read_text(encoding="utf-8")
        )
        quality_path = E / f"{slug}-quality.json"
        quality = (
            json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else None
        )
        sample_records = []
        for page, printed, note in details["samples"]:
            png = f"evidence/openstax/inspection/{slug}/physical-{page:04}.png"
            assert (ROOT / png).exists(), png
            native_path = None
            if quality:
                units = [u for u in quality["units"] if u["page"] == page]
                native_path = (
                    f"evidence/openstax/inspection/{slug}/physical-{page:04}-pipeline-native.txt"
                )
                (ROOT / native_path).write_text(
                    "\n\n".join(u["raw_text"] for u in units), encoding="utf-8"
                )
            sample_records.append(
                {
                    "physical_pdf_page": page,
                    "visible_printed_page_label": printed,
                    "observation": note,
                    "review_evidence": png,
                    "pdfium_text": f"evidence/openstax/inspection/{slug}/physical-{page:04}.txt",
                    "initial_pypdf_pipeline_text": native_path,
                }
            )
        books.append(
            {
                "slug": slug,
                "title": a["title"],
                "raw_path": a["raw_path"],
                "source_url": a["pdf_url"],
                "catalog_source": a["catalog_api"],
                "details_url": a["details_url"],
                "acquisition_evidence": f"evidence/openstax/{slug}-acquisition.json",
                "acquired_at": a["acquired_at"],
                "download_last_modified": a["response_last_modified"],
                "sha256": digest,
                "independently_rehashed_in_this_inspection": True,
                "file_size_bytes": source.stat().st_size,
                "physical_page_count": scan["physical_page_count"],
                "title_edition_physical_page": 3,
                "title_render": f"evidence/openstax/inspection/{slug}/physical-0003.png",
                "original_publication_year_embedded": details["year"],
                "digital_isbn13": a["digital_isbn_13"],
                "license": {
                    "physical_pdf_page": 4,
                    "printed_page_label": None,
                    "copyright": "2026 Rice University",
                    "identifier": "CC BY-NC-SA 4.0",
                    "short_exact_excerpt": "Attribution Non-Commercial ShareAlike 4.0 International License (CC BY-NC-SA 4.0).",
                    "attribution_excerpt": "Access for free at openstax.org.",
                    "source_url": a["pdf_url"],
                    "render": f"evidence/openstax/inspection/{slug}/physical-0004.png",
                    "text": f"evidence/openstax/inspection/{slug}/physical-0004.txt",
                    "observed_terms": [
                        "Noncommercial use",
                        "Same type of license for adaptations",
                        "Attribution retained on distributed digital page views and printed pages",
                        "Named trademarks, logos and covers are outside the textbook-content license",
                    ],
                    "scope": "Embedded source text observation; original publication year differs from current copyright/download date. No legal interpretation beyond reporting the source wording.",
                },
                "table_of_contents": {
                    "physical_start": details["toc"][0],
                    "physical_end": details["toc"][1],
                    "range_basis": "Native frontmatter text inspection plus visually inspected first TOC page and selected continuation",
                    "first_render": f"evidence/openstax/inspection/{slug}/physical-0007.png",
                    "warning": "TOC target numbers are printed page references, not physical PDF page numbers or body section starts.",
                },
                "page_numbering": {
                    "preface_printed_page_1_physical_page": details["preface"],
                    "observed_body_offset": details["offset"],
                    "limitation": "Offset describes inspected numbered body pages. Do not invent a printed label on unnumbered covers/frontmatter/chapter openers; physical locators remain authoritative.",
                },
                "low_text_scan": {
                    "path": f"evidence/openstax/inspection/{slug}-low-text-scan.json",
                    "pages_scanned": len(scan["pages"]),
                    "extraction_error_count": sum(p["error"] is not None for p in scan["pages"]),
                    "flagged_page_count": len(scan["low_text_pages"]),
                },
                "visual_samples": sample_records,
            }
        )
    result = {
        "inspected_at": datetime.now(timezone.utc).isoformat(),
        "status": "bounded_source_inspection_complete_extraction_limits_open",
        "scope": "All four source identities/embedded license-title pages and first TOC pages checked visually. Native character count covers all4638 physical pages; all91 low-text pages were rendered and visually screened. Representative difficult body pages were inspected. This is not a full-book equation, diagram, reading-order or semantic fidelity certification.",
        "reviewer_kind": "agent_visual_source_review",
        "independent_human_scientific_review": False,
        "originals_modified": False,
        "database_modified": False,
        "renderer": "Poppler pdftoppm; original 1400-pixel longest-edge PNG review files. Separate later OCR rendering has its own provenance.",
        "low_text_decisions": "evidence/openstax/pdf-low-text-decisions.json",
        "publisher_supplement_review": "evidence/openstax/chemistry-additional-supplements.json",
        "historical_concepts_sha_match": {
            "sha256": books[-1]["sha256"],
            "basis": "Current independently rehashed official PDF matches the historical pilot identity supplied by root. Physical1 is cover, physical2 blank; those pilot quarantines are accounted with explicit visual decisions.",
        },
        "books": books,
        "open_quality_risks": [
            "Native text may omit entire scientific tables/diagrams and displayed equations despite retaining nearby prose.",
            "All13 low-text substantive visual pages remain retained and require reviewed supplementary extraction or explicit unresolved limitation.",
            "Publisher accessible descriptions contain actual mismatches; source authority alone does not certify image-alt fidelity.",
            "TOC/chapter-outline entries and running headers must not create premature body section state.",
            "Some pages span two body sections or multiple columns; coarse page metadata alone cannot provide exact reading order.",
            "No claims about every scientific equation, element value or diagram label outside inspected samples are justified.",
        ],
    }
    transcript_paths = sorted((E / "transcriptions").glob("chemistry-2e-*.json"))
    if transcript_paths:
        result["reviewed_transcription_addendum"] = {
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Seven Chemistry pages were subsequently reviewed against original-resolution300dpi PNGs and raw RapidOCR output. Original scan/91 decisions above remain a preserved earlier measurement, not a total count of every scientific extraction defect.",
            "additional_residual_detector_pages": [
                {
                    "slug": "anatomy-and-physiology-2e",
                    "physical_page": 470,
                    "original_native_characters": 104,
                    "review_owner": "root; separate anatomy transcription evidence",
                },
                {
                    "slug": "chemistry-2e",
                    "physical_page": 1195,
                    "original_native_characters": 125,
                    "review_owner": "frontend agent",
                    "reason": "Short scientific answer contains visible multiplication signs and exponents missing or malformed in native/OCR extraction.",
                },
            ],
            "transcriptions": [
                {
                    "path": p.relative_to(ROOT).as_posix(),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "physical_page": json.loads(p.read_text(encoding="utf-8"))["physical_page"],
                }
                for p in transcript_paths
            ],
            "status": "agent_source_verified_for_included_transcription_text_only",
            "limits": "No independent human scientific review. Source PNG retains geometry, color placement and graphical semantics outside included text. Source189 displayed equations and other unscreened high-text figures remain outside these seven transcription reviews. Processing/publication status belongs to root's pipeline evidence, not this report.",
        }
    path = E / "pdf-source-inspection.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(path),
                "books": len(books),
                "physical_pages": sum(b["physical_page_count"] for b in books),
                "hashes_match": True,
            }
        )
    )


if __name__ == "__main__":
    main()
