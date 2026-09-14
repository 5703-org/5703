"""Attributable extractive summaries using a conservative token upper bound."""

import hashlib
import json


def token_count(text: str) -> int:
    """Explicit character estimate for callers without an answer-model tokenizer."""
    from generation.token_counting import estimate_tokens

    return estimate_tokens(text)


def summarize(
    messages: list[dict],
    cutoff_sequence: int | None = None,
    max_tokens: int = 512,
    session_id: str = "",
    count_tokens=None,
) -> dict:
    count_tokens = count_tokens or token_count
    cutoff = (
        cutoff_sequence
        if cutoff_sequence is not None
        else max((m.get("sequence", 0) for m in messages), default=0)
    )
    lines, source_ids = [], []
    for message in messages:
        if message.get("sequence", 0) > cutoff or message.get("role") != "user":
            continue
        content = message.get("content", "").strip()
        mid = str(message.get("message_id", message.get("id", "")))
        if not content or not mid:
            continue
        line = f"[{mid}] {content}"
        if count_tokens("\n".join([*lines, line])) > max_tokens:
            continue
        lines.append(line)
        source_ids.append(mid)
    text = "\n".join(lines)
    fingerprints = {
        str(m.get("message_id", m.get("id", ""))): hashlib.sha256(
            (m.get("content", "") + str(m.get("active_answer_id", m.get("answer_id", "")))).encode()
        ).hexdigest()
        for m in messages
        if m.get("sequence", 0) <= cutoff
    }
    digest = hashlib.sha256(
        (session_id + str(cutoff) + text + json.dumps(fingerprints, sort_keys=True)).encode()
    ).hexdigest()
    return {
        "id": "sum_" + digest[:24],
        "session_id": session_id,
        "covered_until_sequence": cutoff,
        "source_message_ids": source_ids,
        "summary_text": text,
        "method": "extractive_user_topics_v1",
        "version": 1,
        "token_count": count_tokens(text),
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
        "covered_message_hashes": fingerprints,
    }


def summary_is_valid(summary: dict, messages: list[dict], cutoff_sequence: int) -> bool:
    if summary.get("covered_until_sequence", 0) > cutoff_sequence:
        return False
    available = {
        str(m.get("message_id", m.get("id", "")))
        for m in messages
        if m.get("sequence", 0) <= cutoff_sequence
    }
    fingerprints = {
        str(m.get("message_id", m.get("id", ""))): hashlib.sha256(
            (m.get("content", "") + str(m.get("active_answer_id", m.get("answer_id", "")))).encode()
        ).hexdigest()
        for m in messages
    }
    return (
        set(summary.get("source_message_ids", [])) <= available
        and all(
            fingerprints.get(mid) == digest
            for mid, digest in summary.get("covered_message_hashes", {}).items()
        )
        and summary.get("text_hash")
        == hashlib.sha256(summary.get("summary_text", "").encode()).hexdigest()
    )
