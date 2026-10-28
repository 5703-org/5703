"""Structure from actual PDF destinations; native text has explicit visual limits."""

import re


def outline_destinations(reader):
    destinations = {}

    def visit(items, ancestors=()):
        parent = None
        for item in items:
            if isinstance(item, list):
                visit(item, (*ancestors, parent) if parent else ancestors)
                continue
            title = str(item.title).strip()
            parent = title
            if title in ("Introduction", "Chapter Outline", "Chapter Objectives"):
                # These are retained within their chapter. In the supplied PDFs,
                # their stream text may precede the visually earlier chapter title.
                continue
            page = reader.get_destination_page_number(item)
            if page is None or not title:
                continue
            chapter = next((a for a in ancestors if a.lower().startswith("chapter ")), None)
            scope = f"{chapter or ancestors[0]} / {title}" if ancestors else title
            top = item.get("/Top")
            destinations.setdefault(page + 1, []).append(
                {
                    "title": title,
                    "section": scope,
                    "top": float(top) if top is not None else None,
                    "top_level": not ancestors,
                }
            )

    visit(getattr(reader, "outline", []))
    return destinations


def split_bookmarked_page(raw, page, destinations, carried, *, legacy_synthetic_carry=False):
    """Keep every extracted character, including pre-heading continuation text."""
    events, warnings = [], []
    for entry in destinations.get(page, []):
        title = entry["title"]
        expression = (
            r"(?m)^[ \t]*"
            + r"\s+".join(re.escape(part) for part in title.split())
            + r"[ \t]*(?=\r?$)"
        )
        matches = list(re.finditer(expression, raw, re.I))
        if entry["top_level"] and entry["top"] is not None and entry["top"] >= 700:
            # The PDF destination itself explicitly starts a top-level scope at
            # the page top, even when PDF stream ordering moves a label earlier.
            position = 0
        elif matches:
            # Chapter opening outlines can repeat the section title before its
            # real heading. Prefer the instance followed by learning objectives;
            # otherwise retain an explicit ambiguity warning and use the last.
            teaching = [
                m for m in matches if re.match(r"\s*LEARNING OBJECTIVES\b", raw[m.end() :], re.I)
            ]
            selected = teaching[-1] if teaching else matches[-1]
            position = selected.start()
            if len(matches) > 1 and not teaching:
                warnings.append(
                    {
                        "code": "PDF_HEADING_ALIGNMENT_REVIEW",
                        "severity": "warning",
                        "message": f"Bookmark heading {title!r} appears more than once on PDF physical page {page}; the last exact heading was selected.",
                    }
                )
        else:
            warnings.append(
                {
                    "code": "PDF_HEADING_ALIGNMENT_REVIEW",
                    "severity": "warning",
                    "message": f"Bookmark {title!r} targets PDF physical page {page}, but no exact text heading could be aligned; inspect the original destination.",
                }
            )
            continue
        events.append((position, entry["section"]))
    current = carried or f"PDF physical page {page}"
    pieces, cursor = [], 0
    for position, section in sorted(events, key=lambda e: e[0]):
        if position > cursor:
            pieces.append((current, raw[cursor:position], warnings))
        current, cursor = section, position
    if cursor < len(raw) or not pieces:
        pieces.append((current, raw[cursor:], warnings))
    # A physical-page fallback describes only this page. Keep it out of the
    # bookmark state, or an unbookmarked prefix would inherit page1 indefinitely.
    # Explicit v4 reprocessing retains the historical behavior and identity.
    return pieces, current if events or legacy_synthetic_carry else carried


def has_visual_content(page):
    """Detect image/form drawing or vector paint operations without decoding images."""
    if not hasattr(page, "get_contents"):
        return False
    contents = page.get_contents()
    if contents is None:
        return False
    return any(
        operator
        in (b"Do", b"INLINE IMAGE", b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*")
        for _, operator in contents.operations
    )
