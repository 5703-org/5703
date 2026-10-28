"""Preserve official Anatomy source pages for matched visual-page alternatives."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import httpx
from pipelines.supplements import PublisherImages

ROOT = Path(__file__).resolve().parents[2]
PAGES = [
    (604, "14-3-motor-responses"),
    (756, "18-3-erythrocytes"),
    (935, "21-1-anatomy-of-the-lymphatic-and-immune-systems"),
]


def acquire(pair):
    page, slug = pair
    url = "https://openstax.org/books/anatomy-and-physiology-2e/pages/" + slug
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        response = client.get(url)
        response.raise_for_status()
    raw = response.content
    sha = hashlib.sha256(raw).hexdigest()
    original = ROOT / f"artifacts/openstax/official-html/anatomy-{slug}-{sha}.html"
    stored = ROOT / f"artifacts/storage/supplements/{sha}.html"
    for target in (original, stored):
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(raw)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == sha
    parser = PublisherImages()
    parser.feed(raw.decode("utf-8"))
    result = {
        "requested_url": url,
        "final_url": str(response.url),
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "html_sha256": sha,
        "html_size_bytes": len(raw),
        "physical_page": page,
        "original_path": original.relative_to(ROOT).as_posix(),
        "storage_path": stored.relative_to(ROOT / "artifacts/storage").as_posix(),
        "images": parser.images,
    }
    (ROOT / f"evidence/openstax/anatomy-html-{page}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "page": page,
                "sha256": sha,
                "images": [
                    {"src": image["src"][:150], "alt": image["alt"][:170]}
                    for image in parser.images
                    if "/resources/" in image["src"]
                ],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(acquire, PAGES))
