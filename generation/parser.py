"""Strict JSON decoding plus request-dependent response semantics."""

from __future__ import annotations
import json
import re
import unicodedata
from pydantic import ValidationError
from contracts.models import ChatResponseV1, MCQResponseV1, TeachingStudyResponseV1


class ResponseValidationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ResponseValidationError("DUPLICATE_JSON_KEY", "Duplicate JSON object key")
        result[key] = value
    return result


def strict_json(raw: str) -> dict:
    if not isinstance(raw, str):
        raise ResponseValidationError("INVALID_JSON", "Response must be JSON text")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite constant")),
        )
    except ResponseValidationError:
        raise
    except (ValueError, TypeError) as exc:
        raise ResponseValidationError(
            "INVALID_JSON", "Expected exactly one strict JSON object"
        ) from exc
    if not isinstance(value, dict):
        raise ResponseValidationError("INVALID_JSON", "Response must be an object")
    return value


def validate_options(options: dict | None):
    if not isinstance(options, dict) or set(options) != {"A", "B", "C", "D"}:
        raise ResponseValidationError("INVALID_OPTIONS", "MCQ requires exactly A-D options")
    if any(not isinstance(v, str) or not v.strip() for v in options.values()):
        raise ResponseValidationError("INVALID_OPTIONS", "Options must be nonblank text")
    normalized = [
        " ".join(unicodedata.normalize("NFKC", v).split()).casefold() for v in options.values()
    ]
    if len(set(normalized)) != 4:
        raise ResponseValidationError(
            "INVALID_OPTIONS", "Options must be distinct after normalization"
        )


def parse_response(
    raw: str,
    *,
    mode: str,
    condition: str,
    evidence_ids: list[str],
    question_id: str = "",
    options: dict | None = None,
) -> dict:
    value = strict_json(raw)
    model = MCQResponseV1 if mode == "benchmark_mcq" else ChatResponseV1
    if mode not in {"interactive_chat", "benchmark_openqa", "benchmark_mcq"}:
        raise ResponseValidationError("INVALID_MODE", "Unknown answer mode")
    try:
        parsed = model.model_validate(value).model_dump()
    except ValidationError as exc:
        raise ResponseValidationError(
            "SCHEMA_VALIDATION", "Response fields violate the selected schema"
        ) from exc
    citations = parsed["citations"]
    if len(citations) != len(set(citations)) or not set(citations) <= set(evidence_ids):
        raise ResponseValidationError(
            "INVALID_CITATIONS", "Citations must be unique selected evidence IDs"
        )
    if condition == "E0" and citations:
        raise ResponseValidationError("INVALID_CITATIONS", "E0 cannot cite evidence")
    if mode == "benchmark_mcq":
        validate_options(options)
        if parsed["question_id"] != question_id:
            raise ResponseValidationError("QUESTION_ID_MISMATCH", "Question identity differs")
        if not parsed["refused"] and parsed["answer_text"] != options[parsed["answer"]]:
            raise ResponseValidationError(
                "OPTION_TEXT_MISMATCH", "Selected option text must match exactly"
            )
        if condition == "E0" and parsed["refused"]:
            raise ResponseValidationError(
                "E0_MCQ_REFUSAL", "The frozen MCQ E0 policy requires selection"
            )
        factual = not parsed["refused"]
    else:
        markers = set(re.findall(r"\[(ev_\d{3,})\]", parsed["answer_text"]))
        if markers != set(citations):
            raise ResponseValidationError(
                "CITATION_MARKER_MISMATCH", "Inline markers and citations must agree"
            )
        factual = parsed["response_type"] == "answer"
    if factual and condition != "E0" and not citations:
        raise ResponseValidationError(
            "MISSING_CITATIONS", "A factual RAG answer requires selected evidence"
        )
    return parsed


def parse_teaching(raw: str, evidence_ids: list[str]):
    try:
        value = TeachingStudyResponseV1.model_validate(strict_json(raw)).model_dump()
    except ValidationError as exc:
        raise ResponseValidationError(
            "SCHEMA_VALIDATION", "Invalid teaching-study response"
        ) from exc
    if not set(value["citations"]) <= set(evidence_ids) or len(set(value["citations"])) != len(
        value["citations"]
    ):
        raise ResponseValidationError(
            "INVALID_CITATIONS", "Teaching output cites unapproved evidence"
        )
    if set(re.findall(r"\[(ev_\d{3,})\]", value["explanation"])) != set(value["citations"]):
        raise ResponseValidationError(
            "CITATION_MARKER_MISMATCH", "Teaching markers must match citations"
        )
    value["invariant_check"] = {
        "structural_valid": True,
        "human_review_status": "pending",
        "semantic_preservation": None,
    }
    return value
