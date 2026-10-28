"""Verified publisher alternatives supplement, but never overwrite, PDF extraction."""

import hashlib
from html.parser import HTMLParser
from pathlib import Path

from .clean import clean_source_text


class PublisherImages(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            values = dict(attrs)
            if values.get("src") and values.get("alt"):
                self.images.append(values)


def apply_page_reviews(units, entries, pdf_hash):
    """Apply exact source-bound page decisions, preserving every original unit."""
    seen = set()
    for item in entries:
        page = item["physical_page"]
        if page in seen or item["pdf_sha256"] != pdf_hash:
            raise ValueError("Page review is duplicated or belongs to different PDF bytes")
        seen.add(page)
        matching = [unit for unit in units if unit["page"] == page]
        if not matching or not item.get("reason") or not item.get("review_evidence"):
            raise ValueError("Page review lacks a current page or inspection evidence")
        actual = " ".join("".join(unit["raw_text"] for unit in matching).split())
        if hashlib.sha256(actual.encode()).hexdigest() != item["normalized_native_text_sha256"]:
            raise ValueError(
                f"Page review no longer matches native extraction on physical page {page}"
            )
        category = item["category"]
        if category not in ("cover_art", "blank_page", "furniture_only", "substantive_short_text"):
            raise ValueError("Substantive visual content cannot be discarded through a page review")
        for unit in matching:
            if category == "substantive_short_text":
                unresolved = [
                    issue
                    for issue in unit["issues"]
                    if issue["severity"] == "blocking" and issue["code"] != "LOW_TEXT_IMAGE_PAGE"
                ]
                if unresolved:
                    raise ValueError(
                        "A short-text review cannot resolve a different extraction failure"
                    )
                unit["quality"] = "ready"
            else:
                unit["quality"] = "excluded"
            unit["issues"].append(
                {
                    "code": "SOURCE_PAGE_REVIEW",
                    "severity": "resolved" if category == "substantive_short_text" else "excluded",
                    "message": item["reason"],
                    **item,
                }
            )
    return units


def apply_publisher_supplements(units, entries, storage_root, pdf_hash):
    if not entries:
        return units
    root = Path(storage_root).resolve()
    additions = []
    seen = set()
    for item in entries:
        key = (item["physical_page"], item["image_resource"])
        if key in seen:
            raise ValueError("Duplicate publisher supplement")
        seen.add(key)
        if item["pdf_sha256"] != pdf_hash or item.get("kind") != "official_html_image_alt":
            raise ValueError("Publisher supplement does not match the registered PDF")
        if not item["source_url"].startswith("https://openstax.org/books/"):
            raise ValueError("Publisher supplement must retain its official book URL")
        source = (root / item["storage_path"]).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError("Publisher original is missing or outside source storage")
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["html_sha256"]:
            raise ValueError("Publisher original hash mismatch")
        parser = PublisherImages()
        parser.feed(raw.decode("utf-8"))
        matches = [
            image["alt"]
            for image in parser.images
            if image["src"].endswith("/" + item["image_resource"])
        ]
        if (
            len(matches) != 1
            or hashlib.sha256(matches[0].encode()).hexdigest() != item["text_sha256"]
        ):
            raise ValueError("The pinned publisher element/text does not verify")
        if not item.get("review_evidence") or not item.get("review_scope"):
            raise ValueError("Publisher alternatives need an explicit source matching review")
        page_units = [unit for unit in units if unit["page"] == item["physical_page"]]
        if not page_units:
            raise ValueError("Publisher supplement has no matching PDF physical page")
        provenance = {
            name: item[name]
            for name in (
                "source_url",
                "html_sha256",
                "pdf_sha256",
                "physical_page",
                "image_resource",
                "text_sha256",
                "review_evidence",
                "review_scope",
                "storage_path",
            )
        }
        for unit in page_units:
            if unit["quality"] == "blocked" and all(
                issue["code"] == "LOW_TEXT_IMAGE_PAGE" or issue["severity"] != "blocking"
                for issue in unit["issues"]
            ):
                # The raw PDF unit, including the original blocking observation,
                # remains visible and hashed; it is never passed to the chunker.
                unit["quality"] = "supplemented"
                unit["issues"].append(
                    {
                        "code": "PUBLISHER_ALTERNATIVE_LINKED",
                        "severity": "resolved",
                        "message": "A separately attributed publisher description supplies searchable text for this page. Other visual details remain unextracted.",
                        **provenance,
                    }
                )
        additions.append(
            {
                "page": item["physical_page"],
                "section": page_units[0]["section"] + " — Publisher image description",
                "raw_text": matches[0],
                "cleaned_text": clean_source_text(matches[0], set()),
                "quality": "ready",
                "issues": [
                    {
                        "code": "PUBLISHER_ALTERNATIVE_TEXT",
                        "severity": "warning",
                        "message": "Exact official HTML image alternative text, matched to this PDF page; not PDF-native extraction and not complete visual recovery.",
                        **provenance,
                    },
                    {
                        "code": "UNEXTRACTED_VISUAL_CONTENT",
                        "severity": "warning",
                        "message": "The alternative describes a selected figure. Other figures, formulas and spatial details still require the original PDF.",
                    },
                ],
            }
        )
    result = sorted([*units, *additions], key=lambda unit: unit["page"])
    for index, unit in enumerate(result, 1):
        unit["sequence"] = index
    return result
