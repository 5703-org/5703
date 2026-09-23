"""Public learning-memory and controlled source presentation contracts."""

from typing import Literal
from pydantic import Field
from contracts.models import Contract


class MemorySettingsOut(Contract):
    enabled: bool
    version: int
    revocation_epoch: int


class MemorySettingsUpdate(Contract):
    enabled: bool
    version: int = Field(ge=1)


class MemoryOut(Contract):
    id: str
    category: Literal[
        "preference",
        "goal",
        "confirmed_observation",
        "course_context",
        "self_reported_observation",
        "assessment_performance",
    ]
    content: str | None
    scope: str
    source_message_id: str | None
    status: Literal["active", "expired", "deleted"]
    version: int
    updated_at: str
    expires_at: str | None
    field_key: str | None = None
    scope_topics: list[str] = Field(default_factory=list)
    verification: str = "legacy_unverified"
    writer_version: str = "explicit_learning_memory_v1"
    effective_at: str | None = None
    source_event_sequence: int | None = None
    provenance: dict = Field(default_factory=dict)


class MemoryEdit(Contract):
    version: int = Field(ge=1)
    content: str = Field(min_length=1, max_length=2000)
    scope: str = Field(default="global", min_length=1, max_length=200)
    expires_at: str | None = None
    field_key: str | None = Field(default=None, max_length=120)


class MemoryDelete(Contract):
    version: int = Field(ge=1)


class MemoryRecordCreate(Contract):
    category: Literal["preference", "goal", "course_context", "self_reported_observation"]
    field_key: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=2000)
    scope: str = Field(default="global", min_length=1, max_length=200)
    source_message_id: str
    source_quote: str = Field(min_length=1, max_length=4000)
    expires_at: str | None = None


class MemoryAssessmentCreate(Contract):
    owner_id: str | None = None
    question_message_id: str
    response_message_id: str
    question_quote: str = Field(min_length=1, max_length=4000)
    response_quote: str = Field(min_length=1, max_length=4000)
    scope: str = Field(min_length=1, max_length=200)
    scoring_basis: str = Field(min_length=1, max_length=4000)
    evaluator_id: str = Field(min_length=1, max_length=120)
    evaluator_version: str = Field(min_length=1, max_length=120)
    score: float | None = Field(default=None, ge=0, le=1)
    confirmation: Literal["self_reported", "automatic", "human"] = "self_reported"
    rubric_kind: Literal["recorded", "exact_text", "numeric"] = "recorded"
    expected_answer: str | None = Field(default=None, max_length=2000)
    tolerance: float = Field(default=0.0, ge=0)
    reviewer_attestation: bool = False


class MemorySummaryOut(Contract):
    enabled: bool
    version: str
    active_count: int
    summary: str
    items: list[MemoryOut]
    limitations: list[str]


class MemoryProcessingOut(Contract):
    event_id: str
    source_message_id: str | None
    sequence: int
    status: str
    operations: list[dict]
    error: dict | None
    created_at: str


class LearnerStatePreview(Contract):
    question: str = Field(min_length=1, max_length=4000)
    use_profile: bool = True


class LearnerStateOut(Contract):
    enabled: bool
    policy_version: str
    snapshot_id: str | None = None
    fields: list[dict] = Field(default_factory=list)
    entries: list[dict] = Field(default_factory=list)
    query_topics: list[str] = Field(default_factory=list)
    excluded: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class TaskOut(Contract):
    id: str
    session_id: str
    question: str
    task_type: str
    teaching_mode: Literal["direct", "hint"]
    help_level: int
    state: str
    version: int


class ExposureInput(Contract):
    kind: Literal["rendered", "citation_opened", "full_source_requested"]
    presentation_id: str
    evidence_id: str | None = None
    claim_id: str | None = None
    surface: Literal["answer", "citation", "full_source"] = "answer"
    parent_exposure_id: str | None = None


class TextSegment(Contract):
    text: str
    highlight: bool = False
    fragment_ids: list[str] = Field(default_factory=list)


class CitationView(Contract):
    evidence_id: str
    claim_ids: list[str] = Field(default_factory=list)
    title: str
    source_title: str | None = None
    section: str | None = None
    pages: list[int] = Field(default_factory=list)
    segments: list[TextSegment]
    available_actions: list[str] = Field(default_factory=list)
    source_url: str | None = None
    license: str | None = None


class ExposureOut(Contract):
    id: str
    kind: str
    presentation_id: str
    citation_view: CitationView | None = None


class PresentationOut(Contract):
    id: str
    task_id: str | None
    teaching_mode: Literal["direct", "hint"]
    help_level: int
    policy_version: str
    content_hash: str
    citation_views: list[CitationView]


class DerivationValidationOut(Contract):
    arithmetic_checked: bool
    formula_basis: Literal["textbook", "problem_input"] = "textbook"
    conditional_on_given_rule: bool = False
    scope: Literal["arithmetic_and_exact_quotes_only"] = "arithmetic_and_exact_quotes_only"
    formula_and_units: Literal["model_judgment_not_independent"] = "model_judgment_not_independent"
    human_rating: None = None


class ClaimSupportOut(Contract):
    status: Literal["supported", "partial", "unsupported"] | None = None
    basis: (
        Literal[
            "textbook", "problem_input", "derived_calculation", "nonfactual", "evidence_limitation"
        ]
        | None
    ) = None
    checker_configuration_id: str | None = None
    checker_model: str | None = None
    strategy: str | None = None
    checked_at: str | None = None
    problem_quote: str | None = None
    check_state: str | None = None
    derivation_validation: DerivationValidationOut | None = None
    human_rating: None = None
