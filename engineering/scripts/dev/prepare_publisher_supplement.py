"""Pin an inspected official Rutherford illustration alternative to Chemistry PDF17."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from pipelines.supplements import PublisherImages

ROOT = Path(__file__).resolve().parents[2]
source = (
    ROOT
    / "artifacts/openstax/official-html/chemistry-2e-preface-8bf10b148e068b4ff9460ecd56bc1391589876737e81c449b2bc9e35081bbc8e.html"
)
raw = source.read_bytes()
html_hash = hashlib.sha256(raw).hexdigest()
resource = "2b721b0944b10dcfed1a88cb056a233b350838a9"
parser = PublisherImages()
parser.feed(raw.decode("utf-8"))
matches = [image for image in parser.images if image["src"].endswith("/" + resource)]
assert len(matches) == 1
target = ROOT / "artifacts/storage/supplements" / (html_hash + ".html")
target.parent.mkdir(parents=True, exist_ok=True)
if not target.exists():
    with target.open("xb") as stream:
        stream.write(raw)
assert hashlib.sha256(target.read_bytes()).hexdigest() == html_hash
entry = {
    "kind": "official_html_image_alt",
    "physical_page": 17,
    "pdf_sha256": "fd89db1b8a1fee06b8ad3e8982f4f4b34bde4e93654a4ce28b724f8c0efe98d6",
    "source_url": "https://openstax.org/books/chemistry-2e/pages/preface",
    "acquired_at": datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat(),
    "acquisition_time_basis": "Original downloaded file creation/write observation; HTTP request completed in this run",
    "html_sha256": html_hash,
    "html_size_bytes": len(raw),
    "image_resource": resource,
    "image_url": "https://openstax.org" + matches[0]["src"],
    "text_sha256": hashlib.sha256(matches[0]["alt"].encode()).hexdigest(),
    "storage_path": target.relative_to(ROOT / "artifacts/storage").as_posix(),
    "original_path": source.relative_to(ROOT).as_posix(),
    "review_evidence": "evidence/openstax/inspection/chemistry-2e/physical-0017.png",
    "review_scope": "Agent visually matched the radium source, alpha-particle beam, thin gold foil, surrounding luminescent screen and three scattering paths to the official alternative. This is source matching, not independent human scientific review.",
    "remaining_limits": "Only the Rutherford panel is supplemented. Other image descriptions were not accepted as exact matches: HCl alternative has a state-label discrepancy and d-orbital alternative ordering differs from PDF labels. Those visual details remain unextracted and inspectable in the original.",
    "license": "Official page states CC BY-NC-SA 4.0 with OpenStax/Rice University attribution; original HTML and PDF terms retained.",
}
result = {
    "prepared_at": datetime.now(timezone.utc).isoformat(),
    "entries": [entry],
    "exact_publisher_text": matches[0]["alt"],
}
output = ROOT / "evidence/openstax/chemistry-publisher-supplement.json"
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "output": str(output),
            "text_sha256": entry["text_sha256"],
            "characters": len(matches[0]["alt"]),
        }
    )
)
