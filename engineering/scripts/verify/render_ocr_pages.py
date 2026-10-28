"""Render only the 13 visually reviewed scientific pages for local OCR."""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import pymupdf
import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--page", action="append", default=[], help="Additional reviewed slug:physical-page"
    )
    parser.add_argument("--output", default="evidence/openstax/ocr/render-manifest.json")
    args = parser.parse_args()
    decisions = json.loads(
        Path("evidence/openstax/pdf-low-text-decisions.json").read_text(encoding="utf-8")
    )
    results = []
    for book in decisions["books"]:
        asset = json.loads(
            Path("evidence/openstax", book["slug"] + "-acquisition.json").read_text(
                encoding="utf-8"
            )
        )
        path = Path(asset["raw_path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != book["pdf_sha256"]:
            raise ValueError("Original PDF hash changed")
        pdf = pymupdf.open(path)
        selected = [
            page for page in book["pages"] if page["category"] == "substantive_visual_unextracted"
        ]
        if args.page:
            selected = [
                {
                    "physical_pdf_page": int(value.split(":", 1)[1]),
                    "review_evidence": f"evidence/openstax/{book['slug']}-quality.json",
                }
                for value in args.page
                if value.split(":", 1)[0] == book["slug"]
            ]
        for page in selected:
            number = page["physical_pdf_page"]
            output = Path("evidence/openstax/ocr", book["slug"], f"physical-{number:04}-300dpi.png")
            output.parent.mkdir(parents=True, exist_ok=True)
            pixmap = pdf[number - 1].get_pixmap(dpi=300, alpha=False)
            pixmap.save(output)
            row = {
                "slug": book["slug"],
                "physical_page": number,
                "pdf_sha256": book["pdf_sha256"],
                "image_path": output.as_posix(),
                "image_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "width": pixmap.width,
                "height": pixmap.height,
                "dpi": 300,
                "original_review": page["review_evidence"],
            }
            results.append(row)
            print(json.dumps(row), flush=True)
        pdf.close()
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "renderer": "PyMuPDF",
        "renderer_version": pymupdf.VersionBind,
        "pages": results,
    }
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
