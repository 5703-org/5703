"""Record visual review decisions; never ingest, modify, or publish source PDFs."""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/openstax"
VISUAL = {
    "anatomy-and-physiology-2e": {
        604: "Historical portrait of a man holding a rod; no native image caption on this page. Preserve the image and use surrounding publisher context before identifying the person.",
        756: "Blood-cell comparison table with formed element, microscopic appearance, counts, nuclei, functions and comments. Table content is rendered as an image and absent from native extracted text.",
        935: "Labeled anatomical overview of the lymphatic system, including thymus inset, lymph vessels and nodes, spleen, tonsil and bone marrow. Native extraction retains only the running header.",
    },
    "biology-2e": {
        1453: "Appendix A periodic table: element cells, symbols, numbers and legend are visual content; native text retains only appendix heading and figure label.",
        1455: "Appendix B geological time clock: circular intervals, boundary labels and event annotations are visual content; native extraction retains only heading and figure caption.",
    },
    "chemistry-2e": {
        17: "Three science image panels: Rutherford alpha scattering, HCl/water molecular reaction diagrams and five d-orbital shapes. Native text is only 'Preface 3'; this is not a blank page.",
        475: "Six gas-law/nonideal-gas plots labeled Gas A through Gas F, plus exercise 100. Plot labels, axes, curve shapes and conditions are not in native extracted text.",
        1008: "Organic functional-group table: ten compound classes, structural formulas, molecular models, example formulas and names. Native extraction retains only page furniture.",
        1071: "Appendix A periodic table with element cells and legend. Native extraction retains only the appendix heading and figure label.",
        1079: "Essential mathematics page with a small x/y table and quadratic plot y=x squared+2. Native text retains table values but not the plotted relationship and axes.",
        1160: "Answer-key carbon phase diagrams with Carbon (liquid), Carbon vapor (gas) and Graphite labels, axes, boundaries and shaded phase regions. Native text retains panel letters and running furniture only. Full-size review corrected the earlier contact-sheet description that incorrectly mentioned water.",
    },
    "concepts-biology": {
        601: "Appendix A periodic table: element cells, symbols, numbers and legend are visual content; native text retains only appendix heading and figure label.",
        603: "Appendix B geological time clock: circular intervals, boundary labels and event annotations are visual content; native extraction retains only heading and figure caption.",
    },
}
SHORT = {
    "anatomy-and-physiology-2e": {
        1347: "Last index page has two real index entries ('bone' and 'zygote') with page references; retain these despite low character count."
    },
    "biology-2e": {
        201: "A genuine continuation sentence about ATP production remains at the top of an otherwise blank body.",
        616: "A genuine critical-thinking question continuation ('this occur?') remains in the body.",
    },
    "chemistry-2e": {
        319: "Exercise 86 asks about aluminum's group; this is substantive question text.",
        971: "A genuine exercise continuation asks about larger crystal-field splitting.",
    },
    "concepts-biology": {},
}
OFFSETS = {
    "anatomy-and-physiology-2e": 16,
    "biology-2e": 20,
    "chemistry-2e": 14,
    "concepts-biology": 14,
}


def main():
    books = []
    for path in sorted((EVIDENCE / "inspection").glob("*-low-text-scan.json")):
        scan = json.loads(path.read_text(encoding="utf-8"))
        slug = scan["slug"]
        rows = []
        for item in scan["low_text_pages"]:
            page = item["physical_pdf_page"]
            if page == 1:
                category, decision = "cover_art", "eligible_for_explicit_exclusion"
                reason = "Rendered page is the designed OpenStax book cover with title/logo; no textbook teaching body. Native text is empty. Preserve original cover and source identity."
            elif page == 2:
                category, decision = "blank_page", "eligible_for_explicit_exclusion"
                reason = "Rendered physical page is entirely white, with no visible text, teaching illustration or page furniture."
            elif page in VISUAL[slug]:
                category, decision = (
                    "substantive_visual_unextracted",
                    "retain_and_flag_text_incomplete",
                )
                reason = VISUAL[slug][page]
            elif page in SHORT[slug]:
                category, decision = "substantive_short_text", "retain_native_text"
                reason = SHORT[slug][page]
            else:
                category, decision = "furniture_only", "eligible_for_explicit_exclusion"
                reason = "Visual review shows blank body space with only running header/page number and/or OpenStax attribution footer. No substantive teaching text or illustration is visible."
            png = f"evidence/openstax/inspection/{slug}/physical-{page:04}.png"
            assert (ROOT / png).is_file(), png
            rows.append(
                {
                    **item,
                    "printed_page": str(page - OFFSETS[slug]) if page > OFFSETS[slug] else None,
                    "printed_page_basis": "Visible running page label in reviewed rendering"
                    if page > OFFSETS[slug]
                    else "Front matter has no printed Arabic page label",
                    "category": category,
                    "decision": decision,
                    "reason": reason,
                    "review_evidence": png,
                    "review_method": "Agent visual review of Poppler page rendering/contact sheet; bounded source audit, not independent human scientific review",
                    "exclusion_applied": False,
                }
            )
        books.append(
            {
                "slug": slug,
                "pdf_sha256": scan["sha256"],
                "physical_page_count": scan["physical_page_count"],
                "scan_path": path.relative_to(ROOT).as_posix(),
                "low_text_page_count": len(rows),
                "non_cover_low_text_page_count": len(
                    [r for r in rows if r["physical_pdf_page"] > 2]
                ),
                "category_counts": dict(Counter(r["category"] for r in rows)),
                "pages": rows,
            }
        )
    result = {
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "status": "all_flagged_pages_visually_screened",
        "scope": "Native pypdf text character scan across every physical page of four acquired official PDFs; visual review of all pages below 100 stripped characters. This does not assess extraction fidelity of every other page.",
        "total_physical_pages_scanned": sum(b["physical_page_count"] for b in books),
        "total_low_text_pages_reviewed": sum(b["low_text_page_count"] for b in books),
        "non_cover_low_text_pages_reviewed": sum(b["non_cover_low_text_page_count"] for b in books),
        "policy": "Decisions are evidence-backed recommendations only. No DB processing/exclusion/publication or original-file edits were performed. Never exclude substantive images as blank. An exclusion must preserve physical page identity and explicit reason in a new processing run.",
        "category_counts": dict(Counter(r["category"] for b in books for r in b["pages"])),
        "books": books,
    }
    out = EVIDENCE / "pdf-low-text-decisions.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(out),
                "category_counts": result["category_counts"],
                "reviewed": result["total_low_text_pages_reviewed"],
            }
        )
    )


if __name__ == "__main__":
    main()
