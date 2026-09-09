"""PDF/TXT parser ports preserving physical locators and original source text."""

from pathlib import Path
from collections import Counter
import math
import re
from pypdf import PdfReader
from .clean import clean_source_text
from .pdf_structure import outline_destinations, split_bookmarked_page, has_visual_content


CURRENT_PARSER_REVISION = "pypdf_bookmarks_v5"


def parse(
    path: Path, media_type: str, *, parser_revision: str = CURRENT_PARSER_REVISION
) -> list[dict]:
    destinations, visual_pages, page_warnings = {}, set(), {}
    if media_type == "application/pdf":
        reader = PdfReader(path, strict=True)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are unsupported")
        destinations = outline_destinations(reader)
        pages = []
        for index in range(len(reader.pages)):
            try:
                page = reader.pages[index]
                raw = page.extract_text() or ""
            except Exception as exc:
                # A damaged page is a blocking, inspectable unit. Other pages
                # retain their physical positions and original extracted text.
                pages.append(
                    (
                        index + 1,
                        "",
                        {
                            "code": "PDF_PAGE_EXTRACTION_FAILED",
                            "severity": "blocking",
                            "error_type": type(exc).__name__,
                            "message": f"Text extraction failed for PDF physical page {index + 1}: {str(exc)[:500]}",
                        },
                    )
                )
                continue
            pages.append((index + 1, raw, None))
            try:
                if has_visual_content(page):
                    visual_pages.add(index + 1)
            except Exception as exc:
                page_warnings[index + 1] = [
                    {
                        "code": "PDF_VISUAL_INSPECTION_FAILED",
                        "severity": "blocking",
                        "message": f"Visual-operation inspection failed on PDF physical page {index + 1}: {type(exc).__name__}.",
                    }
                ]
    elif media_type == "text/plain":
        pages = [(1, path.read_text(encoding="utf-8-sig"), None)]
    else:
        raise ValueError("Unsupported source type")
    units = []
    # Repeated short page-edge furniture can be removed from cleaned text while
    # raw units and physical page identity remain inspectable.
    edge_counts = Counter()
    for _, raw, _ in pages:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if len(lines) >= 5:
            edge_counts.update(
                set(
                    line
                    for line in [*lines[:2], *lines[-2:]]
                    if len(line) < 100 and not re.match(r"^(?:#{1,6}\s|\d+(?:\.\d+)+\s)", line)
                )
            )
    furniture = {
        line for line, count in edge_counts.items() if count >= max(3, math.ceil(len(pages) * 0.6))
    }
    carried_section = None
    for page_number, raw, extraction_error in pages:
        if extraction_error:
            units.append(
                {
                    "sequence": len(units) + 1,
                    "page": page_number,
                    "section": f"PDF physical page {page_number}",
                    "raw_text": "",
                    "cleaned_text": "",
                    "quality": "blocked",
                    "issues": [extraction_error],
                }
            )
            carried_section = None
            continue
        if destinations:
            segments, carried_section = split_bookmarked_page(
                raw,
                page_number,
                destinations,
                carried_section,
                legacy_synthetic_carry=parser_revision != CURRENT_PARSER_REVISION,
            )
        else:
            pieces = re.split(r"(?m)^(#{1,6}\s+[^\n]+|\d+(?:\.\d+)+\s+[A-Z][^\n]{0,160})\s*$", raw)
            section = carried_section or (
                f"Page {page_number}" if media_type == "application/pdf" else "Text source"
            )
            segments = []
            for index, piece in enumerate(pieces):
                if index % 2:
                    section = piece.lstrip("#").strip()
                    carried_section = section
                elif piece.strip() or len(pieces) == 1:
                    segments.append((section, piece, []))
        page_furniture = set(furniture)
        if destinations:
            # These observed OpenStax footer forms are recognized only at page
            # edges. TOC rows inside the page remain part of the original content.
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            for line in lines[-2:]:
                if (
                    re.fullmatch(
                        r"(?:\d+\s+.+\s+•\s+.+|.+\s+•\s+.+\s+\d+|(?:Preface|Index)\s+\d+|Access for free at .+)",
                        line,
                    )
                    and len(line) < 220
                ):
                    page_furniture.add(line)
        for section, piece, structural_issues in segments:
            clean = clean_source_text(piece, page_furniture)
            issues = [*structural_issues, *page_warnings.get(page_number, [])]
            if page_number in visual_pages:
                issues.append(
                    {
                        "code": "UNEXTRACTED_VISUAL_CONTENT",
                        "severity": "warning",
                        "page": page_number,
                        "message": "This PDF page includes image or drawing operations. Figures or formulas may require viewing the original PDF; native text extraction does not reproduce their visual content.",
                    }
                )
                if len(re.sub(r"\s+", "", raw)) < 100:
                    issues.append(
                        {
                            "code": "LOW_TEXT_IMAGE_PAGE",
                            "severity": "blocking",
                            "page": page_number,
                            "message": "This PDF page has fewer than 100 non-whitespace extracted characters and visual content. Inspect the original page and record a source-specific decision; it is not automatically a blank page.",
                        }
                    )
            if re.search(r"(?<=\w)-\r?\n(?=\w)", piece):
                issues.append(
                    {
                        "code": "HYPHENATION_REVIEW",
                        "severity": "warning",
                        "message": "A line-end hard hyphen was retained because its intended spelling requires source review.",
                    }
                )
            if any(line.strip() in page_furniture for line in piece.splitlines()):
                issues.append(
                    {
                        "code": "REPEATED_FURNITURE_REMOVED",
                        "severity": "warning",
                        "message": "Repeated page-edge text was removed from cleaned text; inspect the retained raw source.",
                    }
                )
            furniture_only = bool(piece.strip()) and all(
                line.strip() in page_furniture or line.strip() == "OpenStax Biology 2e"
                for line in piece.splitlines()
                if line.strip()
            )
            if not clean.strip() and not furniture_only:
                issues.append(
                    {
                        "code": "EMPTY_UNIT",
                        "severity": "blocking",
                        "message": "No readable text was extracted.",
                    }
                )
            elif furniture_only:
                issues.append(
                    {
                        "code": "FURNITURE_ONLY",
                        "severity": "warning",
                        "message": "This raw segment contains only recognized page furniture and produces no chunk.",
                    }
                )
            if "\ufffd" in clean or any(ord(c) < 32 and c not in "\n\r\t" for c in clean):
                issues.append(
                    {
                        "code": "UNREADABLE_TEXT",
                        "severity": "blocking",
                        "message": "Replacement or control characters need review.",
                    }
                )
            if clean and len(clean) < 30:
                issues.append(
                    {
                        "code": "SHORT_UNIT",
                        "severity": "warning",
                        "message": "Inspect this unusually short unit.",
                    }
                )
            units.append(
                {
                    "sequence": len(units) + 1,
                    "page": page_number,
                    "section": section,
                    "raw_text": piece,
                    "cleaned_text": clean,
                    "quality": "blocked"
                    if any(i["severity"] == "blocking" for i in issues)
                    else "ready",
                    "issues": issues,
                }
            )
    return units
