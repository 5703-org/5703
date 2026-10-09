"""Administrator contracts for immutable, independently reviewed visual versions."""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints, field_validator

from contracts.models import Contract

Sha256 = Annotated[str, StringConstraints(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[
    str,
    StringConstraints(
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    ),
]
CatalogState = Literal["staged", "under_review", "active", "withdrawn"]
CandidateKind = Literal["table_candidate", "figure_image", "formula_candidate"]
ReviewDecision = Literal["accepted", "rejected", "needs_more"]


class CatalogImportInput(Contract):
    bundle_name: str = Field(min_length=1, max_length=80)
    expected_manifest_sha256: Sha256

    @field_validator("bundle_name")
    @classmethod
    def basename_only(cls, value: str) -> str:
        if ".." in value or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", value) is None:
            raise ValueError("A single safe bundle directory name is required")
        return value


class CatalogTransitionInput(Contract):
    expected_version: int = Field(ge=1)
    state: Literal["under_review", "active", "withdrawn"]


class CatalogReviewChecks(Contract):
    source_page_match: bool
    geometry_correct: bool
    native_text_correct: bool
    reading_order_correct: bool
    content_correct: bool
    notation_units_correct: bool


class CatalogReviewInput(Contract):
    previous_review_id: Identifier | None
    decision: ReviewDecision
    checks: CatalogReviewChecks
    evidence: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=12, max_length=2000)
    ]


class CatalogCounts(Contract):
    total: int = Field(ge=0)
    table_candidate: int = Field(default=0, ge=0)
    figure_image: int = Field(default=0, ge=0)
    formula_candidate: int = Field(default=0, ge=0)
    rectangular_tables: int = Field(ge=0)
    unresolved_tables: int = Field(ge=0)
    inline_table_references: int = Field(default=0, ge=0)


class CatalogReviewHistoryCounts(Contract):
    accepted: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    needs_more: int = Field(default=0, ge=0)


class CatalogSummaryOut(Contract):
    id: Identifier
    document_id: Identifier
    document_version_id: Identifier
    document_title: str
    book: str
    importer_id: Identifier
    source_active: bool
    source_sha256: Sha256
    catalog_sha256: Sha256
    manifest_sha256: Sha256
    previous_catalog_sha256: Sha256
    extractor_revision: str
    catalog_schema: str
    configuration_sha256: Sha256
    state: CatalogState
    version: int = Field(ge=1)
    counts: CatalogCounts
    review_history_counts: CatalogReviewHistoryCounts
    answer_evidence_eligible: Literal[False] = False
    published: Literal[False] = False


class CatalogVersionPageOut(Contract):
    items: list[CatalogSummaryOut]
    next_offset: int | None


class CatalogImportItemOut(CatalogSummaryOut):
    added: int = Field(ge=0)


class CatalogImportOut(Contract):
    items: list[CatalogImportItemOut]
    added_candidates: int = Field(ge=0)


class CatalogCandidateOut(Contract):
    id: Identifier
    region_id: Sha256
    previous_region_id: Sha256
    physical_pdf_page: int = Field(ge=1)
    kind: CandidateKind
    candidate_status: Literal[
        "needs_structure_review", "needs_visual_review", "needs_formula_review"
    ]
    payload_sha256: Sha256
    bbox_points: list[float] = Field(min_length=4, max_length=4)
    answer_evidence_eligible: Literal[False] = False


class CatalogCandidatePageOut(Contract):
    items: list[CatalogCandidateOut]
    next_offset: int | None


class CatalogReviewOut(Contract):
    id: Identifier
    previous_review_id: Identifier | None
    reviewer_id: Identifier
    decision: ReviewDecision
    method: Literal["independent_human"]
    checks: CatalogReviewChecks
    evidence: str
    payload_sha256: Sha256
    reviewed_at: str


class CatalogCandidateDetailOut(Contract):
    catalog_id: Identifier
    region_id: Sha256
    previous_region_id: Sha256
    payload_sha256: Sha256
    candidate_status: Literal[
        "needs_structure_review", "needs_visual_review", "needs_formula_review"
    ]
    raw_payload: dict[str, Any]
    latest_review: CatalogReviewOut | None
    answer_evidence_eligible: Literal[False] = False


class CatalogReviewResultOut(Contract):
    review_id: Identifier
    catalog_version: CatalogSummaryOut
