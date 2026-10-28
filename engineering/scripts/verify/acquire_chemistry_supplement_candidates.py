"""Pin official HTML source bytes for bounded, visually reviewed supplements."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
PAGES = sys.argv[1:] or [
    "9-exercises",
    "a-the-periodic-table",
    "b-essential-mathematics",
    "chapter-10",
    "chapter-11",
    "20-introduction",
    "20-1-hydrocarbons",
]


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            values = dict(attrs)
            if "resources/" in values.get("src", ""):
                self.images.append(values)


def acquire(page):
    url = f"https://openstax.org/books/chemistry-2e/pages/{page}"
    started = datetime.now(timezone.utc).isoformat()
    with urlopen(
        Request(
            url,
            headers={"User-Agent": "OpenStax source audit; immutable educational source evidence"},
        ),
        timeout=45,
    ) as response:
        raw = response.read()
        metadata = {
            "http_status": response.status,
            "final_url": response.url,
            "content_type": response.headers.get("Content-Type"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }
    digest = hashlib.sha256(raw).hexdigest()
    path = ROOT / "artifacts/openstax/official-html" / f"chemistry-2e-{page}-{digest}.html"
    if not path.exists():
        with path.open("xb") as output:
            output.write(raw)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    parser = Images()
    parser.feed(raw.decode("utf-8"))
    result = {
        "page_slug": page,
        "requested_url": url,
        "acquisition_started_at": started,
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        **metadata,
        "html_sha256": digest,
        "html_size_bytes": len(raw),
        "original_path": path.relative_to(ROOT).as_posix(),
        "candidate_images": parser.images,
        "status": "candidate_source_only_requires_visual_matching",
    }
    print(
        json.dumps(
            {
                "page": page,
                "images": [
                    {"resource": i["src"].rsplit("/", 1)[-1], "alt": i.get("alt", "")}
                    for i in parser.images
                ],
            },
            ensure_ascii=False,
        )
    )
    return result


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(acquire, PAGES))
    path = ROOT / "evidence/openstax/chemistry-supplement-candidate-acquisitions.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        records = old + [
            r for r in records if not any(x["html_sha256"] == r["html_sha256"] for x in old)
        ]
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
