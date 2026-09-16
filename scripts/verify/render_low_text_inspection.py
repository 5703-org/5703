"""Render every page flagged by the bounded native-text source audit."""

import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
INSPECTION = ROOT / "evidence/openstax/inspection"
RENDERER = Path(
    r"C:\Users\PC\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe"
)

for scan_path in sorted(INSPECTION.glob("*-low-text-scan.json")):
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    acquisition = json.loads(
        (ROOT / f"evidence/openstax/{scan['slug']}-acquisition.json").read_text(encoding="utf-8")
    )
    original = ROOT / acquisition["raw_path"]
    folder = INSPECTION / scan["slug"]
    for item in scan["low_text_pages"]:
        physical = item["physical_pdf_page"]
        prefix = folder / f"physical-{physical:04}"
        if not prefix.with_suffix(".png").exists():
            subprocess.run(
                [
                    str(RENDERER),
                    "-f",
                    str(physical),
                    "-l",
                    str(physical),
                    "-scale-to",
                    "1400",
                    "-png",
                    "-singlefile",
                    str(original),
                    str(prefix),
                ],
                capture_output=True,
                check=True,
            )
    for start in range(0, len(scan["low_text_pages"]), 16):
        group = scan["low_text_pages"][start : start + 16]
        sheet = Image.new("RGB", (1120, ((len(group) + 3) // 4) * 390), "#dddddd")
        draw = ImageDraw.Draw(sheet)
        for position, item in enumerate(group):
            physical = item["physical_pdf_page"]
            source = Image.open(folder / f"physical-{physical:04}.png").convert("RGB")
            source.thumbnail((270, 350))
            x, y = (position % 4) * 280 + 5, (position // 4) * 390 + 27
            sheet.paste(source, (x, y))
            draw.text((x, y - 21), f"PDF {physical} | {item['characters']} chars", fill="black")
        sheet.save(folder / f"low-text-contact-{start // 16 + 1}.png")
    print(
        json.dumps(
            {"slug": scan["slug"], "low_text_pages": len(scan["low_text_pages"]), "rendered": True}
        ),
        flush=True,
    )
