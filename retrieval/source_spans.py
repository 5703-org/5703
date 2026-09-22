"""Exact cleaned-source spans; local selection is not a support judgment."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata

VERSION = "cleaned_unit_offsets_v1"
ATOMIC = {"formula", "table", "caption", "image_transcription"}


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _range(start, end, length):
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= length:
        raise ValueError("SOURCE_SPAN_INVALID")


def _blocks(unit):
    text = unit["cleaned_text"]
    raw_boundaries = _raw_heading_boundaries(unit)
    explicit = unit.get("blocks")
    if explicit:
        previous = 0
        for block in explicit:
            _range(block["start"], block["end"], len(text))
            if block["start"] < previous:
                raise ValueError("SOURCE_BLOCK_OVERLAP")
            previous = block["end"]
            yield block["start"], block["end"], block.get("kind", "prose"), "explicit_block"
        return
    if unit.get("block_kind") in ATOMIC:
        yield 0, len(text), unit["block_kind"], "explicit_block"
        return
    for match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|$)", text, re.S):
        start, end = match.span()
        value = match.group()
        boundaries = [p for p in raw_boundaries if start < p < end]
        if boundaries and re.match(r"(?i)(?:figure\s+\d|answer\s*:)", value):
            boundary = boundaries[0]
            caption_end = boundary
            while caption_end > start and text[caption_end - 1].isspace():
                caption_end -= 1
            yield (
                start,
                caption_end,
                "caption" if value.lower().startswith("figure") else "answer_key",
                "raw_heading_boundary",
            )
            start, value = boundary, text[boundary:end]
        if re.search(r"(?im)^\s*(?:figure|table)\s+\d|\t|\|", value):
            yield start, end, "unresolved_atomic", "conservative_whole_block"
        else:
            # Boundaries avoid decimal points. Offsets always come from the exact text.
            for sentence in re.finditer(r"\S.*?(?:[.!?](?=\s+[A-Z]|$)|$)", value, re.S):
                a, b = sentence.span()
                # Flattened PDF paragraphs can contain prose, an inline equation
                # and more prose. An equals sign (including an etymology) must not
                # turn the entire page into one unusable atomic candidate.
                atomic = bool(re.search(r"[=→⇌∑]", sentence.group()))
                yield (
                    start + a,
                    start + b,
                    "unresolved_atomic" if atomic else "prose",
                    "conservative_sentence_block" if atomic else "sentence",
                )


def _raw_heading_boundaries(unit):
    """Corroborate a narrow caption/body seam using retained raw extraction lines.

    This is not font or PDF glyph inference. Ambiguous/changed normalization keeps
    the existing coarse fallback; it never guesses missing content or table rows.
    """
    if "raw_text" not in unit and "raw_text_hash" not in unit:
        return []
    raw = unit.get("raw_text")
    if not isinstance(raw, str) or text_hash(raw) != unit.get("raw_text_hash"):
        raise ValueError("SOURCE_RAW_TEXT_HASH_MISMATCH")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    boundaries = []
    for index, heading in enumerate(lines[1:-1], 1):
        words = re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", heading)
        if (
            not 1 <= len(words) <= 9
            or len(heading) > 90
            or not re.fullmatch(r"[A-Za-z][A-Za-z '’:\-]+", heading)
        ):
            continue
        if not all(
            word[0].isupper() or word.lower() in {"and", "of", "the", "in", "for", "to"}
            for word in words
        ):
            continue
        if any(word.upper() in {"FIGURE", "TABLE", "ANSWER"} for word in words):
            continue
        before, after = lines[index - 1], lines[index + 1]
        if not (re.search(r"[.!?]$", before) or re.match(r"(?i)^answer\s*:", before)):
            continue
        if not re.match(
            r"^(?:Recall|The|A|An|In|When|If|As|Most|Some|These|This|Consider|We)\b", after
        ):
            continue
        normalize = lambda value: " ".join(unicodedata.normalize("NFC", value).split())
        left = normalize(before[-90:])
        needle = left + " " + normalize(heading) + " " + normalize(after[:90])
        text = unit["cleaned_text"]
        position = text.find(needle)
        if position < 0 or text.find(needle, position + 1) >= 0:
            continue
        boundaries.append(position + len(left) + 1)
    return boundaries


def map_fragments(evidence, source_map):
    """Return exact candidates and explicit mapping limitations, without DB access."""
    result, issues = [], []
    for item in evidence:
        mapping = source_map.get(item["chunk_id"])
        if not mapping:
            raise ValueError("SOURCE_MAPPING_MISSING")
        text = mapping["chunk_text"]
        if text_hash(text) != mapping["chunk_hash"]:
            raise ValueError("SOURCE_CHUNK_HASH_MISMATCH")
        if (
            mapping["processing_id"] != item["processing_id"]
            or mapping["asset_id"] != item["asset_id"]
        ):
            raise ValueError("SOURCE_MAPPING_FOREIGN")
        if not mapping.get("document_version_id"):
            raise ValueError("SOURCE_VERSION_MISSING")
        offset = mapping.get("submitted_start", 0)
        finish = mapping.get("submitted_end", len(text))
        _range(offset, finish, len(text))
        if text[offset:finish] != item["text"] or text_hash(item["text"]) != item["text_hash"]:
            raise ValueError("SOURCE_SUBMITTED_TEXT_MISMATCH")
        units = {u["id"]: u for u in mapping["units"]}
        if len(units) != len(mapping["units"]):
            raise ValueError("SOURCE_UNIT_DUPLICATE")
        previous = 0
        for span in mapping["spans"]:
            unit = units.get(span["unit_id"])
            if unit is None or unit["page"] != span["page"]:
                raise ValueError("SOURCE_UNIT_MISMATCH")
            value = unit["cleaned_text"]
            if text_hash(value) != unit["text_hash"]:
                raise ValueError("SOURCE_UNIT_HASH_MISMATCH")
            a, b, ca, cb = (span[k] for k in ("start", "end", "chunk_start", "chunk_end"))
            _range(a, b, len(value))
            _range(ca, cb, len(text))
            if ca < previous or text[previous:ca].strip() or text[ca:cb] != value[a:b]:
                raise ValueError("SOURCE_SPAN_RECONSTRUCTION_MISMATCH")
            previous = cb
            lo, hi = max(a, a + offset - ca), min(b, a + finish - ca)
            if lo >= hi:
                continue
            for start, end, kind, quality in _blocks(unit):
                left, right = max(lo, start), min(hi, end)
                if left >= right:
                    continue
                complete = left == start and right == end
                if not complete:
                    issues.append(
                        {
                            "evidence_id": item["evidence_id"],
                            "source_unit_id": unit["id"],
                            "reason": "incomplete_atomic_block"
                            if kind != "prose"
                            else "clipped_source_sentence",
                            "block_kind": kind,
                        }
                    )
                    quality = "coarse_partial_block"
                exact = value[left:right]
                identity = json.dumps(
                    [
                        VERSION,
                        mapping["document_version_id"],
                        item["processing_id"],
                        item["chunk_id"],
                        unit["id"],
                        left,
                        right,
                        text_hash(exact),
                    ],
                    separators=(",", ":"),
                )
                result.append(
                    {
                        "fragment_id": "span_" + text_hash(identity)[:32],
                        "evidence_id": item["evidence_id"],
                        "chunk_id": item["chunk_id"],
                        "asset_id": item["asset_id"],
                        "document_version_id": mapping["document_version_id"],
                        "processing_id": item["processing_id"],
                        "source_unit_id": unit["id"],
                        "start": left,
                        "end": right,
                        "exact_text": exact,
                        "text_hash": text_hash(exact),
                        "chunk_start": ca + left - a,
                        "chunk_end": ca + right - a,
                        "page": unit["page"],
                        "block_kind": kind,
                        "mapping_quality": quality,
                        "complete_block": complete,
                        "offset_basis": "cleaned_source_unit_unicode",
                    }
                )
        if text[previous:].strip():
            raise ValueError("SOURCE_SPAN_TRAILING_TEXT")
    return result, issues


def select_before_generation(evidence, fragments, question):
    """Local exact-excerpt reference strategy, without an extra planning model call."""
    terms = set(re.findall(r"[a-z0-9]+", question.casefold())) - {
        "the",
        "a",
        "is",
        "what",
        "how",
        "and",
        "of",
        "to",
    }
    selected, ranges, excluded = [], {}, []
    for item in evidence:
        candidates = [
            f for f in fragments if f["evidence_id"] == item["evidence_id"] and f["complete_block"]
        ]
        if not candidates:
            excluded.append({"chunk_id": item["chunk_id"], "reason": "no_complete_source_block"})
            continue
        best = max(
            candidates,
            key=lambda f: (
                len(terms & set(re.findall(r"[a-z0-9]+", f["exact_text"].casefold()))),
                -f["chunk_start"],
            ),
        )
        selected.append({**item, "text": best["exact_text"], "text_hash": best["text_hash"]})
        ranges[item["chunk_id"]] = {
            "submitted_start": best["chunk_start"],
            "submitted_end": best["chunk_end"],
        }
    return selected, ranges, excluded


def evidence_ranges(evidence, source_map):
    return [
        {
            "evidence_id": item["evidence_id"],
            "chunk_id": item["chunk_id"],
            "chunk_text_hash": source_map[item["chunk_id"]]["chunk_hash"],
            "chunk_start": source_map[item["chunk_id"]].get("submitted_start", 0),
            "chunk_end": source_map[item["chunk_id"]].get(
                "submitted_end", len(source_map[item["chunk_id"]]["chunk_text"])
            ),
        }
        for item in evidence
    ]
