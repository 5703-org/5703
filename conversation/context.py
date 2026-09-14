"""Select completed owned exchanges and preserve exact revision references."""

from __future__ import annotations
import hashlib
from contracts.models import ConversationSnapshot, MessageRef
from .summary import summarize, token_count

FAILED = {"failed", "error", "cancelled", "queued", "pending", "processing", "running", "partial"}


def select_context(
    session_id: str,
    messages: list[dict],
    cutoff_sequence: int,
    profile_snapshot_id: str | None = None,
    max_exchanges: int = 6,
    history_tokens: int = 2000,
    summary_tokens: int = 512,
    counter=None,
) -> ConversationSnapshot:
    count_tokens = counter.count if counter else token_count
    eligible, exclusions = [], []
    for item in sorted(messages, key=lambda m: m.get("sequence", 0)):
        mid = str(item.get("message_id", item.get("id", "")))
        reason = None
        if item.get("session_id", session_id) != session_id:
            reason = "foreign_session"
        elif item.get("sequence", 0) > cutoff_sequence:
            reason = "after_cutoff"
        elif item.get("state") in FAILED:
            reason = "incomplete_or_failed"
        elif item.get("role") not in {"user", "assistant"}:
            reason = "unsupported_role"
        if reason:
            exclusions.append({"message_id": mid, "reason": reason})
        else:
            eligible.append(item)
    pairs, pending = [], None
    for item in eligible:
        if item["role"] == "user":
            if pending:
                exclusions.append(
                    {
                        "message_id": str(pending.get("id", pending.get("message_id"))),
                        "reason": "unanswered_user_turn",
                    }
                )
            pending = item
        elif pending:
            pairs.append([pending, item])
            pending = None
    if pending:
        exclusions.append(
            {
                "message_id": str(pending.get("id", pending.get("message_id"))),
                "reason": "unanswered_user_turn",
            }
        )
    chosen, used = [], 0
    for pair in reversed(pairs):
        size = sum(count_tokens(m.get("content", "")) + 8 for m in pair)
        if len(chosen) >= max_exchanges or used + size > history_tokens:
            break
        chosen.insert(0, pair)
        used += size
    selected = [m for pair in chosen for m in pair]
    selected_ids = {str(m.get("message_id", m.get("id", ""))) for m in selected}
    first_sequence = min((m.get("sequence", 0) for m in selected), default=cutoff_sequence + 1)
    prefix = [m for pair in pairs for m in pair if m.get("sequence", 0) < first_sequence]
    summary, summary_warning = None, None
    if prefix:
        try:
            summary = summarize(
                prefix, first_sequence - 1, summary_tokens, session_id, count_tokens=count_tokens
            )
        except Exception as exc:
            # A failed optional summary never erases the bounded recent context
            # or pretends that omitted older turns remain available.
            summary_warning = {"code": "SUMMARY_UNAVAILABLE", "error_type": type(exc).__name__}
    for item in prefix:
        exclusions.append(
            {
                "message_id": str(item.get("message_id", item.get("id", ""))),
                "reason": "summary_unavailable" if summary_warning else "compressed_prefix",
            }
        )
    refs = [
        MessageRef(
            message_id=str(m.get("message_id", m.get("id", ""))),
            sequence=m.get("sequence", 0),
            answer_id=m.get("active_answer_id", m.get("answer_id")),
            role=m["role"],
            content=m.get("content", ""),
            content_hash=hashlib.sha256(m.get("content", "").encode()).hexdigest(),
        )
        for m in selected
    ]
    return ConversationSnapshot(
        session_id=session_id,
        cutoff_sequence=cutoff_sequence,
        messages=refs,
        summary_id=summary["id"] if summary and summary["summary_text"] else None,
        summary_hash=summary["text_hash"] if summary and summary["summary_text"] else None,
        covered_until_sequence=summary["covered_until_sequence"]
        if summary and summary["summary_text"]
        else None,
        summary_text=summary["summary_text"] if summary and summary["summary_text"] else None,
        profile_snapshot_id=profile_snapshot_id,
        token_budget={
            "history_tokens": used,
            "summary_tokens": summary["token_count"] if summary else 0,
            "counter": counter.metadata["source"] if counter else "unicode_character_estimate_v1",
            "token_counting": counter.report() if counter else {"is_estimate": True},
            "max_exchanges": max_exchanges,
            "summary_warning": summary_warning,
            "summary_source_message_ids": summary["source_message_ids"] if summary else [],
            "summary_covered_message_hashes": summary["covered_message_hashes"] if summary else {},
        },
        exclusions=exclusions,
    )
