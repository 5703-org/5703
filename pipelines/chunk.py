"""Deterministic section chunks with measured tokens and reconstructable spans."""

import hashlib
import json
import re


def _fixture_tokens(text):
    """The actual lexical MockEmbedding tokenizer; this is not E5."""
    return re.findall(r"[a-z0-9]+", text.casefold())


def chunks(
    units: list[dict],
    processing_id: str,
    *,
    target=320,
    cap=448,
    overlap=48,
    strategy="structure",
    tokenizer=None,
    model_window=512,
    prefix="passage: ",
) -> list[dict]:
    """Measure body and heading/prefix with an injected tokenizer or local fixture tokenizer."""
    if (
        any(type(v) is not int for v in (target, cap, overlap, model_window))
        or not 0 <= overlap < target <= cap <= 448
        or model_window <= 0
    ):
        raise ValueError(
            "Require integer 0 <= overlap < target <= cap <= 448 and a positive model window"
        )
    if strategy not in ("structure", "fixed"):
        raise ValueError("Unknown chunk strategy")
    tokenize = tokenizer or _fixture_tokens

    def count(value):
        result = tokenize(value)
        return result if isinstance(result, int) else len(result)

    result, groups, previous_sequence = [], [], None
    for unit in units:
        if unit["quality"] != "ready":
            previous_sequence = None
            continue
        if not unit["cleaned_text"].strip():
            previous_sequence = unit.get("sequence", (previous_sequence or 0) + 1)
            continue
        adjacent = (
            previous_sequence is not None
            and unit.get("sequence", previous_sequence + 1) == previous_sequence + 1
        )
        if (
            strategy == "structure"
            and groups
            and adjacent
            and groups[-1][0]["section"] == unit["section"]
        ):
            groups[-1].append(unit)
        else:
            groups.append([unit])
        previous_sequence = unit.get("sequence", (previous_sequence or 0) + 1)
    for group in groups:
        text, source_spans = "", []
        for index, unit in enumerate(group):
            if index:
                text += "\n\n"
            start = len(text)
            text += unit["cleaned_text"]
            source_spans.append((start, len(text), unit))
        section = group[0]["section"]
        if count(prefix + section + "\n") >= model_window:
            raise ValueError("Section heading and embedding prefix exhaust the model window")
        identity_base = json.dumps(
            [processing_id, section, [u["id"] for u in group], strategy, target, cap, overlap],
            separators=(",", ":"),
        )
        cursor = 0
        while cursor < len(text):
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            if cursor == len(text):
                break
            low, high, fitted = cursor + 1, min(len(text), cursor + target * 8), cursor
            while (
                high < len(text)
                and count(text[cursor:high]) <= target
                and count(prefix + section + "\n" + text[cursor:high]) <= model_window
            ):
                high = min(len(text), cursor + (high - cursor) * 2)
            while low <= high:
                end = (low + high) // 2
                body = text[cursor:end]
                if count(body) <= target and count(prefix + section + "\n" + body) <= model_window:
                    fitted, low = end, end + 1
                else:
                    high = end - 1
            if fitted == cursor:
                raise ValueError("No source character fits the configured tokenizer window")
            end = fitted
            if end < len(text):
                paragraph_end = text.rfind("\n\n", cursor, end)
                if (
                    strategy == "structure"
                    and paragraph_end > cursor
                    and count(text[cursor:paragraph_end]) >= max(1, target // 2)
                ):
                    end = paragraph_end
                else:
                    boundary = max(text.rfind(" ", cursor, end), text.rfind("\n", cursor, end))
                    if boundary > cursor:
                        end = boundary
            while end > cursor and text[end - 1].isspace():
                end -= 1
            value = text[cursor:end]
            body_tokens = count(value)
            if (
                not value
                or body_tokens > cap
                or count(prefix + section + "\n" + value) > model_window
            ):
                raise ValueError("Final chunk exceeds the measured model input boundary")
            mapped = [
                {
                    "unit_id": unit["id"],
                    "start": max(cursor, start) - start,
                    "end": min(end, finish) - start,
                    "chunk_start": max(cursor, start) - cursor,
                    "chunk_end": min(end, finish) - cursor,
                    "page": unit["page"],
                }
                for start, finish, unit in source_spans
                if cursor < finish and end > start
            ]
            identity = hashlib.sha256(
                f"{identity_base}:{cursor}:{end}:{value}".encode()
            ).hexdigest()[:36]
            result.append(
                {
                    "id": identity,
                    "text": value,
                    "text_hash": hashlib.sha256(value.encode()).hexdigest(),
                    "section": section,
                    "pages": sorted({span["page"] for span in mapped}),
                    "spans": mapped,
                    "tokens": body_tokens,
                }
            )
            if end == len(text):
                break
            if overlap == 0:
                cursor = end
                continue
            next_cursor = end
            for match in reversed(list(re.finditer(r"\S+", text[cursor:end]))):
                absolute = cursor + match.start()
                if absolute <= cursor:
                    break
                if count(text[absolute:end]) <= overlap:
                    next_cursor = absolute
                else:
                    break
            cursor = max(cursor + 1, next_cursor)
    return result
