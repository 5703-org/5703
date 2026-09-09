"""Versioned public payloads. Evaluator references never enter answer commands."""

from __future__ import annotations

from typing import Annotated, Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ExactText = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Level = Literal["beginner", "intermediate", "advanced"]
Mode = Literal["interactive_chat", "benchmark_openqa", "benchmark_mcq"]
Reason = Literal["NO_EVIDENCE", "INSUFFICIENT_EVIDENCE", "CONFLICTING_EVIDENCE", "OUT_OF_SCOPE"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class ChatMessageCreate(Contract):
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    use_profile: bool = True


class ChatResponseV1(Contract):
    schema_version: Literal["chat_response_v1"]
    response_type: Literal["answer", "clarification", "refusal", "social"]
    answer_text: Text
    short_answer: Text | None
    citations: list[Text]
    refusal_reason: Reason | None
    follow_up_questions: list[Text] = Field(max_length=3)
    confidence: float | None = Field(ge=0, le=1)

    @model_validator(mode="after")
    def invariants(self):
        if len(self.citations) != len(set(self.citations)):
            raise ValueError("Citations must be unique")
        if self.response_type == "refusal":
            if (
                self.refusal_reason is None
                or self.short_answer is not None
                or self.citations
                or self.follow_up_questions
                or self.confidence is not None
            ):
                raise ValueError("Refusal fields are inconsistent")
        elif self.refusal_reason is not None:
            raise ValueError("Only refusals have refusal_reason")
        if self.response_type in ("social", "clarification") and self.short_answer is not None:
            raise ValueError("Social and clarification responses have no short_answer")
        return self


class MCQResponseV1(Contract):
    question_id: Text
    answer: Literal["A", "B", "C", "D"] | None
    answer_text: ExactText | None
    citations: list[Text]
    confidence: float | None = Field(ge=0, le=1)
    refused: bool
    refusal_reason: (
        Literal[
            "NO_EVIDENCE",
            "INSUFFICIENT_EVIDENCE",
            "IRRELEVANT_EVIDENCE",
            "CONFLICTING_EVIDENCE",
            "UNSUPPORTED_ANSWER",
            "INVALID_CITATION",
        ]
        | None
    )
    short_explanation: str | None

    @model_validator(mode="after")
    def invariants(self):
        if self.refused:
            if (
                self.answer is not None
                or self.answer_text is not None
                or self.confidence is not None
                or self.citations
                or self.refusal_reason is None
            ):
                raise ValueError("MCQ refusal fields are inconsistent")
        elif self.answer is None or self.answer_text is None or self.refusal_reason is not None:
            raise ValueError("MCQ selection fields are inconsistent")
        return self


class Profile(Contract):
    level: Level = "intermediate"
    style: Literal["concise", "detailed", "socratic"] = "concise"
    language: Literal["en"] = "en"
    topics: list[
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    ] = Field(default_factory=list, max_length=20)
    version: int = Field(default=1, ge=1)


class ProfileUpdate(Profile):
    version: int = Field(ge=1)


class RevisionInput(Contract):
    version: int = Field(ge=1)


class PreparedQuery(Contract):
    original_message: Text
    standalone_query: Text | None
    intent: Literal[
        "factual",
        "follow_up",
        "reexplain",
        "comparison",
        "source_request",
        "social",
        "clarification",
    ]
    topic_relation: Literal["same_topic", "new_topic", "unclear"]
    referenced_message_ids: list[str]
    needs_clarification: bool
    preparation_version: Text
    fallback_reason: str | None


class MessageRef(Contract):
    message_id: str
    sequence: int
    answer_id: str | None
    role: Literal["user", "assistant"]
    content: str
    content_hash: str


class ConversationSnapshot(Contract):
    session_id: str
    cutoff_sequence: int
    messages: list[MessageRef]
    summary_id: str | None
    summary_hash: str | None
    covered_until_sequence: int | None
    summary_text: str | None
    profile_snapshot_id: str | None
    token_budget: dict
    exclusions: list[dict]


class EvidenceOrigin(Contract):
    request_id: str
    evidence_id: str


class EvidenceSnapshot(Contract):
    evidence_id: Annotated[str, StringConstraints(pattern=r"^ev_[0-9]{3,}$")]
    chunk_id: str
    asset_id: str
    processing_id: str
    source_title: Text
    source_url: str | None = None
    license: str | None = None
    section: str
    pages: list[int]
    locator: Text
    text: ExactText
    text_hash: str
    context_order: int
    inherited_from: EvidenceOrigin | None = None


class InteractiveChatCommand(Contract):
    mode: Literal["interactive_chat"]
    session_id: str
    user_message_id: str
    conversation_snapshot_id: str
    profile_snapshot_id: str | None


class OpenQACommand(Contract):
    mode: Literal["benchmark_openqa"]
    run_id: str
    item_id: str
    question_id: str
    question_text: Text


class MCQCommand(Contract):
    mode: Literal["benchmark_mcq"]
    run_id: str
    item_id: str
    question_id: str
    question_text: Text
    options: dict[Literal["A", "B", "C", "D"], ExactText]

    @field_validator("options")
    @classmethod
    def options_valid(cls, value):
        import unicodedata

        normalized = {
            " ".join(unicodedata.normalize("NFKC", text).casefold().split())
            for text in value.values()
        }
        if set(value) != {"A", "B", "C", "D"} or len(normalized) != 4:
            raise ValueError("Exactly four distinct A-D options are required")
        return value


AnswerCommand = Annotated[
    InteractiveChatCommand | OpenQACommand | MCQCommand, Field(discriminator="mode")
]


class TeachingStudyCommand(Contract):
    run_id: str
    item_id: str
    condition: Literal["C0", "C1", "C2"]
    target_level: Level
    base_answer_id: str
    evidence_snapshot_ids: list[str]
    model_configuration_id: str
    prompt_configuration_id: str
    profile_rule_version: str


class TeachingStudyResponseV1(Contract):
    schema_version: Literal["teaching_study_response_v1"]
    explanation: Text
    citations: list[Text]
    learning_check: Text | None
    invariant_check: dict


class ExperimentSpec(Contract):
    protocol_id: Text
    mode: Literal["benchmark_openqa", "benchmark_mcq"]
    condition: Literal["E0", "E1", "R1", "R2", "R3"]
    dataset: Text
    dataset_revision: Text
    split: Literal["train", "validation", "test", "authored"]
    seed: int
    configuration_id: str
    scheduled_count: int = Field(ge=1, le=10000)
    scorer_version: str = "conservative-v1"
    rubric_version: str = "review-v1"


class FeedbackInput(Contract):
    helpful: bool | None
    comment: str = Field(default="", max_length=2000)


class ErrorData(Contract):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class JobReceipt(Contract):
    request_id: str
    job_id: str
    user_message_id: str | None
    poll_url: str


class JobOut(Contract):
    id: str
    request_id: str
    state: Literal["queued", "running", "retry_wait", "succeeded", "failed", "cancelled"]
    stage: str
    error: ErrorData | None
    answer_id: str | None
    can_retry: bool
    created_at: str
    updated_at: str


class AnswerOut(Contract):
    id: str
    request_id: str
    job_id: str
    message_id: str | None
    mode: Mode
    response_schema: Literal["chat_response_v1", "mcq_response_v1"]
    status: Literal["answered", "clarification", "refused"]
    model_mode: Literal["mock", "live"]
    response: ChatResponseV1 | MCQResponseV1
    evidence: list[EvidenceSnapshot]
    profile_snapshot: dict | None
    conversation_snapshot: ConversationSnapshot | None
    timing: dict
    can_regenerate: bool


class MessageOut(Contract):
    id: str
    session_id: str
    sequence: int
    role: Literal["user", "assistant"]
    content: str
    state: str
    active_answer_id: str | None
    answer: AnswerOut | None
    request_id: str | None
    created_at: str


class MessagePage(Contract):
    items: list[MessageOut]
    next_after_sequence: int | None
    active_job_id: str | None
    latest_job_id: str | None
