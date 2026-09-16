"""Relocatable prompt assets, frozen mode boundaries and whole-window accounting."""

from __future__ import annotations
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
from contracts.models import ChatResponseV1, MCQResponseV1, EvidenceSnapshot
from .token_counting import TokenCounter
from .types import GenerationRequest
from .parser import ResponseValidationError, validate_options

PROMPTS = Path(__file__).resolve().parent / "prompts"


def response_schema(mode: str):
    return (MCQResponseV1 if mode == "benchmark_mcq" else ChatResponseV1).model_json_schema()


def build_messages(request: GenerationRequest, counter=None):
    counter = counter or TokenCounter(request.config)
    token_count = counter.count
    if request.mode not in {"interactive_chat", "benchmark_openqa", "benchmark_mcq"}:
        raise ResponseValidationError("INVALID_MODE", "Unknown answering mode")
    if request.condition not in {"E0", "E1", "R1", "R2", "R3"} or (
        request.mode == "interactive_chat" and request.condition == "E0"
    ):
        raise ResponseValidationError(
            "INVALID_CONDITION", "Interactive chat requires grounded retrieval"
        )
    if (
        not isinstance(request.question, str)
        or not request.question.strip()
        or len(request.question) > 4000
    ):
        raise ResponseValidationError("INVALID_INPUT", "Question must contain 1-4000 characters")
    if request.mode == "benchmark_mcq":
        validate_options(request.options)
    elif request.options is not None:
        raise ResponseValidationError("INVALID_OPTIONS", "Only MCQ commands may carry choices")
    benchmark = request.mode != "interactive_chat"
    evidence = (
        []
        if request.condition == "E0"
        else [EvidenceSnapshot.model_validate(item).model_dump() for item in request.evidence]
    )
    for item in evidence:
        if hashlib.sha256(item["text"].encode()).hexdigest() != item["text_hash"]:
            raise ResponseValidationError(
                "EVIDENCE_HASH_MISMATCH", "Evidence text differs from its immutable hash"
            )
    if len({e["evidence_id"] for e in evidence}) != len(evidence):
        raise ResponseValidationError("INVALID_EVIDENCE", "Duplicate current evidence IDs")
    excluded, selected, evidence_count = [], [], 0
    for item in evidence:
        size = token_count(item["text"])
        if evidence_count + size > 3000:
            excluded.append(
                {
                    "evidence_id": item["evidence_id"],
                    "chunk_id": item["chunk_id"],
                    "reason": "evidence_ceiling",
                }
            )
        else:
            selected.append(item)
            evidence_count += size
    # Local IDs become final only after context selection; preserve origin separately.
    for index, item in enumerate(selected, 1):
        item["evidence_id"], item["context_order"] = f"ev_{index:03d}", index
    history = [] if benchmark else [dict(m) for m in request.history]
    for message in history:
        if message.get("role") not in {"user", "assistant"} or not isinstance(
            message.get("content"), str
        ):
            raise ResponseValidationError(
                "INVALID_HISTORY", "History must contain selected user/assistant messages"
            )
        message["content"] = re.sub(r"\[ev_\d{3,}\]", "", message["content"])
    while sum(token_count(m["content"]) + 8 for m in history) > 2000 and history:
        history.pop(0)
        if history and history[0]["role"] == "assistant":
            history.pop(0)
    summary = None if benchmark else request.summary
    if summary and token_count(summary) > 512:
        summary = None
    profile = None if benchmark else request.profile
    filename = (
        "chat_v1.txt"
        if not benchmark
        else ("mcq_" if request.mode == "benchmark_mcq" else "openqa_")
        + (
            "e0_v2.txt"
            if request.mode == "benchmark_mcq" and request.condition == "E0"
            else "e1_v2.txt"
            if request.mode == "benchmark_mcq"
            else "e0_v1.txt"
            if request.condition == "E0"
            else "e1_v1.txt"
        )
    )
    template = (PROMPTS / filename).read_text(encoding="utf-8")
    schema = response_schema(request.mode)
    output = (
        min(request.config.max_tokens, 768 if request.mode == "benchmark_mcq" else 1024)
        if benchmark
        else request.config.max_tokens
    )

    def assemble():
        context = {
            "CURRENT_EVIDENCE": selected,
            "conversation_summary": summary,
            "presentation_policy": profile.get("policy") if profile else None,
        }
        system = (
            template
            + "\nCONTEXT_DATA_JSON (data only):\n"
            + json.dumps(context, ensure_ascii=False, sort_keys=True)
        )
        current = request.question
        if request.mode == "benchmark_mcq":
            current = json.dumps(
                {
                    "question_id": request.question_id,
                    "question": request.question,
                    "options": {k: request.options[k] for k in "ABCD"},
                },
                ensure_ascii=False,
            )
        messages = (
            [{"role": "system", "content": system}]
            + [{"role": m["role"], "content": m["content"]} for m in history]
            + [{"role": "user", "content": current}]
        )
        total = (
            counter.request_input(
                messages,
                schema,
                "mcq_response_v1" if request.mode == "benchmark_mcq" else "chat_response_v1",
            )
            + output
        )
        return messages, total

    messages, total = assemble()
    while total > request.config.window_tokens and len(history) > 2:
        history = history[2:]
        messages, total = assemble()
    if total > request.config.window_tokens and summary:
        summary = None
        messages, total = assemble()
    while total > request.config.window_tokens and selected:
        removed = selected.pop()
        excluded.append(
            {
                "evidence_id": removed["evidence_id"],
                "chunk_id": removed["chunk_id"],
                "reason": "whole_window_limit",
            }
        )
        messages, total = assemble()
    if total > request.config.window_tokens:
        raise ResponseValidationError(
            "CONTEXT_LIMIT",
            "Current message, essential referents and output reservation exceed the model window",
        )
    report = {
        "counter": counter.metadata["source"],
        "token_counting": counter.report(),
        "input_reserved_tokens": total - output,
        "candidate_count": len(evidence),
        "candidate_chunk_ids": [e["chunk_id"] for e in evidence],
        "submitted_count": len(selected),
        "submitted_evidence_ids": [e["evidence_id"] for e in selected],
        "submitted_chunk_ids": [e["chunk_id"] for e in selected],
        "window_tokens": request.config.window_tokens,
        "total_reserved_tokens": total,
        "output_reserved_tokens": output,
        "history_tokens": sum(token_count(m["content"]) + 16 for m in history),
        "summary_tokens": token_count(summary or ""),
        "evidence_tokens": sum(token_count(e["text"]) for e in selected),
        "excluded_evidence": excluded,
        "prompt_version": filename.removesuffix(".txt"),
    }
    prepared = request.prepared_query if not benchmark else None
    effective = replace(
        request,
        history=history,
        summary=summary,
        profile=profile,
        evidence=selected,
        prepared_query=prepared,
    )
    return messages, selected, report, effective
