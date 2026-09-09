"""Read immutable acquired PDFs and save bounded source-inspection evidence.

This is a source audit helper, not document ingestion or whole-book quality QA.
"""

from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "evidence/openstax/inspection"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug")
    parser.add_argument("--pages", help="Comma-separated one-based physical PDF pages")
    parser.add_argument(
        "--renderer", help="Poppler pdftoppm executable; render selected pages when supplied"
    )
    parser.add_argument(
        "--scan-low-text",
        action="store_true",
        help="Count native pypdf text on every physical page; save all pages below 100 characters",
    )
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for acquisition_path in sorted((ROOT / "evidence/openstax").glob("*-acquisition.json")):
        acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
        slug = acquisition["slug"]
        if args.slug and slug != args.slug:
            continue
        raw = ROOT / acquisition["raw_path"]
        document = pdfium.PdfDocument(raw)
        target = OUTPUT / slug
        target.mkdir(exist_ok=True)
        if args.scan_low_text:
            from pypdf import PdfReader

            reader = PdfReader(raw)
            counts = []
            short = []
            for physical, pdf_page in enumerate(reader.pages, 1):
                try:
                    native = pdf_page.extract_text() or ""
                    record = {
                        "physical_pdf_page": physical,
                        "characters": len(native.strip()),
                        "error": None,
                    }
                except Exception as exc:
                    native = ""
                    record = {
                        "physical_pdf_page": physical,
                        "characters": 0,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                counts.append(record)
                if record["characters"] < 100:
                    short.append({**record, "text": native})
            scan = {
                "slug": slug,
                "sha256": acquisition["sha256"],
                "extractor": "pypdf native extract_text; stripped character count",
                "physical_page_count": len(reader.pages),
                "threshold": 100,
                "pages": counts,
                "low_text_pages": short,
                "scope_limit": "Character counts only, not whole-book extraction fidelity or semantic quality",
            }
            (OUTPUT / f"{slug}-low-text-scan.json").write_text(
                json.dumps(scan, indent=2), encoding="utf-8"
            )
            print(
                json.dumps(
                    {"slug": slug, "page_count": len(reader.pages), "low_text": short}, indent=2
                )
            )
            document.close()
            continue
        pages = (
            [int(value) for value in args.pages.split(",")]
            if args.pages
            else list(range(1, min(31, len(document) + 1)))
        )
        records = []
        for physical in pages:
            page = document[physical - 1]
            textpage = page.get_textpage()
            extracted = textpage.get_text_range()
            text_path = target / f"physical-{physical:04}.txt"
            text_path.write_text(extracted, encoding="utf-8")
            if args.renderer:
                prefix = target / f"physical-{physical:04}"
                subprocess.run(
                    [
                        args.renderer,
                        "-f",
                        str(physical),
                        "-l",
                        str(physical),
                        "-scale-to",
                        "1400",
                        "-png",
                        "-singlefile",
                        str(raw),
                        str(prefix),
                    ],
                    check=True,
                    capture_output=True,
                )
            records.append(
                {
                    "physical_pdf_page": physical,
                    "size_points": list(page.get_size()),
                    "extracted_characters": len(extracted),
                    "text_path": text_path.relative_to(ROOT).as_posix(),
                    "first_lines": extracted.splitlines()[:8],
                    "last_lines": extracted.splitlines()[-4:],
                }
            )
            textpage.close()
            page.close()
        manifest.append(
            {
                "slug": slug,
                "title": acquisition["title"],
                "sha256": acquisition["sha256"],
                "file_size_bytes": raw.stat().st_size,
                "physical_page_count": len(document),
                "raw_path": acquisition["raw_path"],
                "inspected_text_pages": records,
            }
        )
        document.close()
    if args.scan_low_text:
        return
    name = (
        "frontmatter-extraction.json" if not args.slug else f"{args.slug}-selected-extraction.json"
    )
    previous = OUTPUT / name
    if args.slug and previous.exists():
        old = json.loads(previous.read_text(encoding="utf-8"))
        for row in manifest:
            earlier = next((item for item in old if item["slug"] == row["slug"]), {})
            combined = {
                item["physical_pdf_page"]: item for item in earlier.get("inspected_text_pages", [])
            }
            combined.update(
                {item["physical_pdf_page"]: item for item in row["inspected_text_pages"]}
            )
            row["inspected_text_pages"] = [combined[key] for key in sorted(combined)]
    (OUTPUT / name).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            [
                {
                    "slug": row["slug"],
                    "physical_page_count": row["physical_page_count"],
                    "selected": [item["physical_pdf_page"] for item in row["inspected_text_pages"]],
                    "manifest": str(OUTPUT / name),
                }
                for row in manifest
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
