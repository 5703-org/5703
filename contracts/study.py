"""Learning workspace contracts. Public practice views never contain grading keys."""

from typing import Annotated, Literal
from pydantic import Field, model_validator, field_validator
from contracts.models import Contract


PracticeKind = Literal["mcq", "multiselect", "short", "numeric", "step"]


class SourceLocator(Contract):
    release_id: str
    document_id: str
    processing_id: str
    source_unit_id: str
    text_hash: str
    start: int = Field(default=0, ge=0)
    end: int | None = Field(default=None, ge=1)


class BookOut(Contract):
    id: str
    title: str
    edition: str
    release_id: str
    document_version_id: str
    source_sha256: str
    processing_id: str
    source_url: str
    license: str
    section_count: int
    unit_count: int


class SectionOut(Contract):
    id: str
    title: str
    first_page: int
    last_page: int
    unit_count: int
    concepts: list[str]
    learning_objectives: list[str]
    related_section_ids: list[str]
    related_section_origin: Literal["adjacent_section_order"] = "adjacent_section_order"
    metadata_origin: Literal["published_section_structure"] = "published_section_structure"


class ReadingUnitOut(Contract):
    id: str
    sequence: int
    page: int
    section_id: str
    section: str
    text: str
    locator: SourceLocator
    source_url: str
    license: str
    representation: Literal["cleaned_source_unit"] = "cleaned_source_unit"


class ReadingPageOut(Contract):
    items: list[ReadingUnitOut]
    offset: int
    next_offset: int | None
    total: int


class ReadingPositionInput(Contract):
    source: SourceLocator
    char_offset: int = Field(default=0, ge=0)
    expected_version: int = Field(default=0, ge=0)


class ReadingPositionOut(Contract):
    id: str
    source: SourceLocator
    char_offset: int
    version: int
    updated_at: str


class GoalCreate(Contract):
    title: str = Field(min_length=1, max_length=200)
    document_id: str
    section_ids: list[str] = Field(min_length=1, max_length=24)
    depth: Literal["beginner", "intermediate", "advanced"] = "intermediate"


class GoalUpdate(Contract):
    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: Literal["active", "paused", "completed"] | None = None


class VersionInput(Contract):
    expected_version: int = Field(ge=1)


class GoalUnitOut(Contract):
    id: str
    section_id: str
    title: str
    concepts: list[str]
    prerequisite_unit_ids: list[str]
    prerequisite_origin: Literal["section_order_suggestion"] = "section_order_suggestion"
    read: bool
    attempts: int
    correct_attempts: int
    graded_attempts: int = 0
    pending_attempts: int = 0
    needs_review: bool
    status: Literal["not_started", "read", "practised", "needs_review"]
    recommended_action: Literal["read", "practise", "review", "try_related"] = "read"


ConceptRelationType = Literal["prerequisite", "related", "confusion"]


class ConceptRelationProposal(Contract):
    document_id: str
    from_section_id: str
    to_section_id: str
    from_concept: str = Field(min_length=1, max_length=200)
    to_concept: str = Field(min_length=1, max_length=200)
    relation_type: ConceptRelationType
    source: SourceLocator
    source_quote: str = Field(min_length=12, max_length=2000)
    reason: str = Field(min_length=20, max_length=2000)


class ConceptRelationReview(Contract):
    expected_version: int = Field(ge=1)
    decision: Literal["approve", "reject"]
    verified_source_support: bool
    review_note: str = Field(min_length=20, max_length=2000)


class ConceptRelationAdminOut(ConceptRelationProposal):
    id: str
    release_id: str
    source_quote_hash: str
    state: Literal["proposed", "approved", "rejected"]
    proposer_id: str
    reviewer_id: str | None
    reviewed_at: str | None
    review_note: str | None
    version: int


class GoalRelationOut(Contract):
    id: str
    relation_type: ConceptRelationType
    from_unit_id: str
    to_unit_id: str
    from_concept: str
    to_concept: str
    reason: str
    source: SourceLocator
    source_quote: str
    source_quote_hash: str
    source_book: str
    source_edition: str
    source_section: str
    source_page: int
    source_url: str
    reviewed_at: str
    provenance: Literal["administrator_reviewed_released_source"] = (
        "administrator_reviewed_released_source"
    )


class GoalOut(Contract):
    id: str
    title: str
    document_id: str
    release_id: str
    depth: str
    status: str
    version: int
    units: list[GoalUnitOut]
    reviewed_relations: list[GoalRelationOut] = Field(default_factory=list)


class Option(Contract):
    id: str = Field(min_length=1, max_length=30)
    text: str = Field(min_length=1, max_length=1000)


class KnowledgePoint(Contract):
    id: str = Field(min_length=1, max_length=60)
    terms: list[str] = Field(min_length=1, max_length=12)


class NumericKey(Contract):
    value: float
    unit: str = Field(max_length=30)
    absolute_tolerance: float = Field(default=0.0, ge=0)
    relative_tolerance: float = Field(default=0.0, ge=0, le=0.25)


class StepKey(Contract):
    id: str = Field(min_length=1, max_length=40)
    prompt: str = Field(min_length=1, max_length=2000)
    acceptable_answers: list[str] = Field(default_factory=list, max_length=20)
    required_points: list[KnowledgePoint] = Field(default_factory=list, max_length=20)
    numeric: NumericKey | None = None
    hints: list[str] = Field(default_factory=list, max_length=3)


class PracticeRubric(Contract):
    correct_option_ids: list[str] = Field(default_factory=list, max_length=10)
    required_points: list[KnowledgePoint] = Field(default_factory=list, max_length=20)
    forbidden_terms: list[str] = Field(default_factory=list, max_length=20)
    acceptable_answers: list[str] = Field(default_factory=list, max_length=20)
    numeric: NumericKey | None = None
    steps: list[StepKey] = Field(default_factory=list, max_length=12)
    hints: list[str] = Field(default_factory=list, max_length=3)
    explanation: str = Field(min_length=1, max_length=12000)
    common_errors: dict[str, str] = Field(default_factory=dict)


class SelectionTaskRef(Contract):
    field: Literal["recorded_step_goal.operation", "current_question"]
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    exact_quote: str = Field(min_length=1, max_length=8000)

    @model_validator(mode="after")
    def full_operation_span(self):
        if self.start != 0 or self.end != len(self.exact_quote):
            raise ValueError("SELECTION_TASK_ANCHOR_INVALID")
        return self


class SelectionCandidateSpan(Contract):
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    exact_quote: str = Field(min_length=1, max_length=12000)

    @model_validator(mode="after")
    def exact_span_length(self):
        if self.end <= self.start or self.end - self.start != len(self.exact_quote):
            raise ValueError("SELECTION_TASK_SOURCE_SPAN_MISMATCH")
        return self


class SelectionEvidenceRef(SelectionCandidateSpan):
    origin: Literal["evidence"]
    chunk_id: str = Field(min_length=1, max_length=200)


class SelectionInputRef(SelectionCandidateSpan):
    origin: Literal["task"]
    field: Literal["question", "current_problem", "practice_context.prompt"]


class SelectionOptionRef(SelectionCandidateSpan):
    origin: Literal["practice_option"]
    option_id: str = Field(min_length=1, max_length=30)


SelectionCandidateRef = Annotated[
    SelectionEvidenceRef | SelectionInputRef | SelectionOptionRef,
    Field(discriminator="origin"),
]


class SelectionTaskAnnotation(Contract):
    version: Literal["selection_task_v1"]
    current_step: int = Field(ge=1, le=12)
    task_ref: SelectionTaskRef
    candidate_presence: Literal["supplied", "absent"]
    candidate_refs: list[SelectionCandidateRef] = Field(max_length=8)


class SelectionCandidateInventory(Contract):
    """An explicit public task inventory; it contains no correctness label."""

    version: Literal["selection_candidates_v1"]
    current_step: int = Field(ge=1, le=12)
    task_ref: SelectionTaskRef
    candidate_refs: list[SelectionCandidateRef] = Field(max_length=8)

    @model_validator(mode="after")
    def unique_references(self):
        rows = [reference.model_dump_json() for reference in self.candidate_refs]
        if len(set(rows)) != len(rows):
            raise ValueError("SELECTION_TASK_REFERENCE_DUPLICATE")
        return self


def _validate_selection_metadata(task, inventory, options):
    if task is None and inventory is None:
        return
    if task is None or inventory is None:
        raise ValueError("SELECTION_TASK_INVENTORY_MISSING")
    presence = "supplied" if inventory.candidate_refs else "absent"
    if (
        task.current_step != inventory.current_step
        or task.task_ref != inventory.task_ref
        or task.candidate_refs != inventory.candidate_refs
        or task.candidate_presence != presence
    ):
        raise ValueError("SELECTION_TASK_INVENTORY_MISMATCH")
    if options:
        option_ids = {option.id for option in options}
        candidate_option_ids = {
            reference.option_id
            for reference in inventory.candidate_refs
            if isinstance(reference, SelectionOptionRef)
        }
        if candidate_option_ids != option_ids:
            raise ValueError("SELECTION_TASK_INVENTORY_OPTIONS_CONFLICT")


class PracticeDraft(Contract):
    title: str = Field(min_length=1, max_length=200)
    kind: PracticeKind
    prompt: str = Field(min_length=1, max_length=8000)
    options: list[Option] = Field(default_factory=list, max_length=10)
    concepts: list[str] = Field(min_length=1, max_length=20)
    conditions: list[str] = Field(default_factory=list, max_length=20)
    source: SourceLocator
    rubric: PracticeRubric
    previous_item_id: str | None = None
    selection_task: SelectionTaskAnnotation | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    selection_candidates: SelectionCandidateInventory | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def public_selection_metadata(self):
        _validate_selection_metadata(self.selection_task, self.selection_candidates, self.options)
        if self.selection_task is not None:
            task_ref = self.selection_task.task_ref
            if task_ref.field == "recorded_step_goal.operation":
                # Step prompts are learner-visible; grading answers are not consulted.
                step = self.selection_task.current_step
                if (
                    step > len(self.rubric.steps)
                    or self.rubric.steps[step - 1].prompt != task_ref.exact_quote
                ):
                    raise ValueError("SELECTION_TASK_ANCHOR_MISMATCH")
            elif task_ref.exact_quote != self.prompt:
                raise ValueError("SELECTION_TASK_ANCHOR_MISMATCH")
        return self


class PracticeProposalInput(Contract):
    source: SourceLocator
    kind: PracticeKind
    concepts: list[str] = Field(min_length=1, max_length=20)
    conditions: list[str] = Field(default_factory=list, max_length=20)


class PublishInput(Contract):
    expected_version: int = Field(ge=1)
    confirm_source_and_solvability: bool


class PracticeOut(Contract):
    id: str
    title: str
    kind: PracticeKind
    prompt: str
    options: list[Option]
    concepts: list[str]
    conditions: list[str]
    source: SourceLocator
    item_revision: int
    validation: dict
    selection_task: SelectionTaskAnnotation | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    selection_candidates: SelectionCandidateInventory | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def public_selection_metadata(self):
        _validate_selection_metadata(self.selection_task, self.selection_candidates, self.options)
        return self


class PracticeAdminOut(Contract):
    item: PracticeOut
    state: str
    version: int
    rubric: PracticeRubric
    validation_details: dict = Field(default_factory=dict)


class PracticeResponse(Contract):
    selection: list[str] = Field(default_factory=list, max_length=10)
    text: str = Field(default="", max_length=8000)
    value: float | None = None
    unit: str = Field(default="", max_length=30)
    step: int | None = Field(default=None, ge=1, le=12)


class AttemptInput(Contract):
    idempotency_key: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=0)
    response: PracticeResponse
    goal_id: str | None = None


class PracticeFeedback(Contract):
    outcome: Literal[
        "correct", "partial", "incorrect", "insufficient", "irrelevant", "pending_review"
    ]
    message: str
    covered_point_ids: list[str] = Field(default_factory=list)
    missing_point_ids: list[str] = Field(default_factory=list)
    error_categories: list[str] = Field(default_factory=list)
    grading_method: Literal[
        "deterministic_rules_v1",
        "deterministic_rules_v2",
        "pending_model_assessment_v1",
        "model_assessment_v1",
    ] = "deterministic_rules_v2"
    semantic_correctness_verified: bool | None = None


class PracticeAssessmentOut(Contract):
    id: str
    status: Literal["applied", "pending_review", "superseded"]
    method: Literal["model_assessment_v1"] = "model_assessment_v1"
    feedback: PracticeFeedback
    applied_progress_version: int | None = None


class AttemptOut(Contract):
    id: str
    item_id: str
    item_revision: int
    response: PracticeResponse
    feedback: PracticeFeedback
    created_at: str
    progress_version: int
    assessment: PracticeAssessmentOut | None = None


class PracticeProgressOut(Contract):
    item_id: str
    tutor_session_id: str | None = None
    tutor_task_id: str | None = None
    version: int
    current_step: int
    current_step_prompt: str | None
    current_step_response_kind: Literal["text", "numeric"] | None = None
    expected_unit: str | None = None
    total_steps: int
    help_level: int
    state: Literal["awaiting_attempt", "completed"]
    attempts: list[AttemptOut]
    hints: list[str]
    full_explanation: str | None


class HelpInput(Contract):
    action: Literal["hint", "full_explanation"]
    expected_version: int = Field(ge=0)


class PracticeTutorInput(Contract):
    expected_version: int = Field(ge=0)
    goal_id: str | None = Field(default=None, min_length=1, max_length=36)


class PracticeTutorOut(Contract):
    session_id: str
    task_id: str
    task_version: int
    practice_progress_version: int
    teaching_mode: Literal["direct", "hint"]
    source: SourceLocator
    goal_id: str | None = None


class ReviewOut(Contract):
    id: str
    target_type: Literal["practice_item", "personal_review_card"]
    item_id: str | None
    note_id: str | None
    card_content: str | None = None
    card_source: SourceLocator | None = None
    title: str
    concepts: list[str]
    due_at: str
    error_categories: list[str]
    attempt_count: int
    correct_count: int = Field(
        description="Graded correct attempts for practice; self-reported recalls for personal cards."
    )
    graded_count: int = 0
    pending_count: int = 0
    suggested_item_id: str | None
    scheduling_reason: str
    version: int
    recent_attempt_count: int = 0
    recent_graded_count: int = Field(
        default=0,
        description="Number of the latest three graded practice attempts used for recent_error_counts.",
    )
    recent_pending_count: int = Field(
        default=0,
        description="Pending attempts among the latest three recorded practice attempts; a separate activity window.",
    )
    recent_error_counts: dict[str, int] = Field(default_factory=dict)


class ReviewSchedule(Contract):
    expected_version: int = Field(ge=1)
    days: int = Field(ge=0, le=30)


class ReviewCardAction(Contract):
    expected_version: int = Field(ge=1)
    outcome: Literal["recalled", "needs_review"]


class NoteCreate(Contract):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=12000)
    kind: Literal["note", "bookmark", "review_card"] = "note"
    source: SourceLocator | None = None
    answer_id: str | None = None
    goal_id: str | None = None
    concepts: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("title", "content")
    @classmethod
    def exportable_text(cls, value):
        if any(
            ord(c) < 32
            and c not in "\t\r\n"
            or 0xD800 <= ord(c) <= 0xDFFF
            or ord(c) in (0xFFFE, 0xFFFF)
            for c in value
        ):
            raise ValueError("Use valid plain text without control characters")
        return value

    @model_validator(mode="after")
    def bookmark_has_source(self):
        if self.kind == "bookmark" and self.source is None and self.answer_id is None:
            raise ValueError("A bookmark requires a source or an owned answer")
        return self


class NoteUpdate(Contract):
    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=12000)
    concepts: list[str] | None = Field(default=None, max_length=20)

    @field_validator("title", "content")
    @classmethod
    def exportable_text(cls, value):
        return NoteCreate.exportable_text(value) if value is not None else value


class NoteSourceMetadata(Contract):
    book_title: str
    section_title: str
    physical_page: int
    source_url: str


class NoteOut(NoteCreate):
    id: str
    version: int
    created_at: str
    updated_at: str
    source_type: Literal["personal_note"] = "personal_note"
    source_metadata: NoteSourceMetadata | None = None


class LearningRecordOut(Contract):
    id: str
    kind: str
    object_id: str
    details: dict
    created_at: str


class NotesExportOut(Contract):
    markdown: str
