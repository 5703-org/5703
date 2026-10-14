"""Immutable visual catalog coexistence and explicit independent-review gates.

This registry does not write legacy visual regions, select a default reader
catalog, publish a corpus, or admit any candidate to answer retrieval.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.exceptions import AppError
from app.db.base import AuditMixin, Base, utcnow
from app.modules.identity.models import User
from app.modules.knowledge.models import Document, DocumentVersion, VisualRegion
from pipelines.visual_regions import _identity
from pipelines.visual_candidate_boundaries import (
    is_inline_reference,
    rectangular_table_body,
    validate_reference_record,
    validate_reference_targets,
    validate_v4_source_geometry,
    validate_v3_parent_lineage,
    validate_v4_parent_lineage,
)
from pipelines.native_formula_context_v1 import (
    CONTEXT_CONFIGURATION,
    validate_formula_context,
    validate_formula_context_against_page,
)
from pipelines.native_tables_v2 import RECOVERY_CONFIGURATION as TABLE_CONFIGURATION

CATALOG_SCHEMA = "native_visual_catalog_version_v1"
REVIEW_CHECKS = (
    "source_page_match",
    "geometry_correct",
    "native_text_correct",
    "reading_order_correct",
    "content_correct",
    "notation_units_correct",
)
KINDS = {"figure_image", "table_candidate", "formula_candidate"}
MAX_LINE_BYTES = 8 * 1024 * 1024
MAX_CATALOG_BYTES = 256 * 1024 * 1024
MAX_REGIONS = 100000


class VisualCatalogVersion(Base, AuditMixin):
    __tablename__ = "visual_catalog_versions"
    __table_args__ = (
        UniqueConstraint("document_version_id", "extractor_revision", "catalog_sha256"),
        CheckConstraint(
            "state IN ('staged','under_review','active','withdrawn')",
            name="ck_visual_catalog_state",
        ),
    )
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), index=True)
    importer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    source_sha256: Mapped[str] = mapped_column(String(64))
    catalog_sha256: Mapped[str] = mapped_column(String(64))
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    previous_catalog_sha256: Mapped[str] = mapped_column(String(64))
    extractor_revision: Mapped[str] = mapped_column(String(80))
    catalog_schema: Mapped[str] = mapped_column(String(80))
    configuration_sha256: Mapped[str] = mapped_column(String(64))
    artifact_manifest: Mapped[dict] = mapped_column(JSON)
    counts: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(20), default="staged")


class VisualCatalogCandidate(Base, AuditMixin):
    __tablename__ = "visual_catalog_candidates"
    __table_args__ = (
        UniqueConstraint("catalog_id", "region_id"),
        UniqueConstraint("catalog_id", "previous_region_id"),
    )
    catalog_id: Mapped[str] = mapped_column(ForeignKey("visual_catalog_versions.id"), index=True)
    region_id: Mapped[str] = mapped_column(String(64), index=True)
    previous_region_id: Mapped[str] = mapped_column(ForeignKey("visual_regions.id"), index=True)
    physical_page: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    candidate_status: Mapped[str] = mapped_column(String(40))
    payload_sha256: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict] = mapped_column(JSON)


class VisualCatalogReview(Base, AuditMixin):
    __tablename__ = "visual_catalog_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('accepted','rejected','needs_more')",
            name="ck_visual_catalog_review_decision",
        ),
        CheckConstraint("method = 'independent_human'", name="ck_visual_catalog_review_method"),
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("visual_catalog_candidates.id"), index=True
    )
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    previous_review_id: Mapped[str | None] = mapped_column(
        ForeignKey("visual_catalog_reviews.id"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(20))
    method: Mapped[str] = mapped_column(String(30))
    checks: Mapped[dict] = mapped_column(JSON)
    evidence: Mapped[str] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def _immutable(_mapper, _connection, _target):
    raise ValueError("Visual candidate and review records are immutable.")


def _version_update(_mapper, _connection, target):
    for attribute in inspect(target).attrs:
        if (
            attribute.key not in {"state", "version", "updated_at"}
            and attribute.history.has_changes()
        ):
            raise ValueError("Visual catalog identity and source content are immutable.")


event.listen(VisualCatalogVersion, "before_update", _version_update)
event.listen(VisualCatalogVersion, "before_delete", _immutable)
for _model in (VisualCatalogCandidate, VisualCatalogReview):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _immutable)


def payload_hash(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fail(reason: str):
    raise AppError("VALIDATION_FAILED", detail=reason)


def _hash(value) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        _fail("A lowercase SHA-256 identity is required.")
    return value


def _admin(db: Session, actor: User) -> User:
    current = db.get(User, actor.id)
    if current is None or current.status != "active" or current.role.name != "admin":
        raise AppError("FORBIDDEN")
    return current


def _source(db: Session, actor: User, version: DocumentVersion, *, visible=True):
    document = db.scalar(
        select(Document)
        .where(Document.id == version.document_id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    owner = db.get(User, document.owner_id) if document else None
    if owner is None or owner.workspace_id != actor.workspace_id:
        raise AppError("NOT_FOUND")
    if visible and (not document.active or document.revoked):
        raise AppError("SOURCE_UNAVAILABLE")
    return document


def _original(version: DocumentVersion, storage_root: Path):
    root = storage_root.resolve()
    path = (root / version.storage_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise AppError("SOURCE_UNAVAILABLE")
    if path.stat().st_size != version.size_bytes or file_hash(path) != version.raw_hash:
        raise AppError("SOURCE_UNAVAILABLE")
    return path


def _rectangular(item: dict) -> bool:
    return rectangular_table_body(item)


def _validate_item(item: dict, book: dict, revision: str):
    if not isinstance(item, dict) or not isinstance(item.get("details"), dict):
        _fail("Malformed visual candidate.")
    page = item.get("physical_pdf_page")
    box = item.get("bbox_points")
    if (
        item.get("extractor_revision") != revision
        or item.get("source_sha256") != book["source_sha256"]
        or item.get("book") != book["book"]
        or item.get("kind") not in KINDS
        or not isinstance(item.get("native_text"), str)
        or not isinstance(page, int)
        or isinstance(page, bool)
        or not 1 <= page <= book["physical_pages"]
        or not isinstance(box, list)
        or len(box) != 4
        or any(
            not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v)
            for v in box
        )
        or not 0 <= box[0] < box[2]
        or not 0 <= box[1] < box[3]
        or item.get("status")
        != {
            "figure_image": "needs_visual_review",
            "table_candidate": "needs_structure_review",
            "formula_candidate": "needs_formula_review",
        }.get(item.get("kind"))
        or item["details"].get("answer_evidence_eligible", False) is not False
        or item.get("region_id") != _identity(item)
    ):
        _fail("Candidate identity, locator or unreviewed state is invalid.")
    _hash(item["region_id"])
    _hash(item["details"].get("previous_region_id"))
    if revision in {"pymupdf_visual_regions_v4", "pymupdf_visual_regions_v5"}:
        _hash(item["details"].get("previous_candidate_region_id"))
        if item["details"].get(
            "previous_candidate_extractor_revision"
        ) != "pymupdf_visual_regions_v3" or (
            item["kind"] == "table_candidate"
            and item["details"].get("record_role")
            not in {"table_body_candidate", "inline_table_reference"}
        ):
            _fail("V4 requires explicit V3 candidate provenance and table record roles.")
    if revision == "pymupdf_visual_regions_v5":
        _hash(item["details"].get("previous_version_region_id"))
        try:
            validate_formula_context(item)
        except ValueError as error:
            _fail(str(error))
    payload_hash(item)
    try:
        validate_reference_record(item, physical_pages=book["physical_pages"])
    except ValueError as error:
        _fail(str(error))


def load_bundle(
    directory: Path, *, expected_manifest_sha256: str
) -> tuple[dict, list[tuple[dict, list[dict]]]]:
    """Validate the complete portable reviewer bundle; no database or labels."""
    root = directory.resolve()
    manifest_path = root / "SOURCE_MANIFEST.json"
    if file_hash(manifest_path) != _hash(expected_manifest_sha256):
        _fail("The source manifest changed.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema")
        not in {
            "official_native_table_review_sources_v1",
            "official_native_table_review_sources_v2",
            "official_native_visual_review_sources_v3",
        }
        or len(manifest.get("books", [])) != 4
    ):
        _fail("A complete four-book native source manifest is required.")
    if any(
        manifest.get(key) != 0
        for key in (
            "human_ratings",
            "semantic_approvals",
            "answer_evidence_eligible_candidates",
            "published_candidates",
        )
    ):
        _fail("Import accepts unreviewed source candidates only.")
    revision = manifest["candidate_revision"]
    if (manifest["schema"], revision) not in {
        ("official_native_table_review_sources_v1", "pymupdf_visual_regions_v3"),
        ("official_native_table_review_sources_v2", "pymupdf_visual_regions_v4"),
        ("official_native_visual_review_sources_v3", "pymupdf_visual_regions_v5"),
    }:
        _fail("The source schema must match its explicit candidate revision.")
    if revision == "pymupdf_visual_regions_v5" and (
        manifest.get("recovery_revision") != "native_visual_context_v5"
        or payload_hash(manifest.get("frozen_configuration"))
        != payload_hash(
            {"table_recovery": TABLE_CONFIGURATION, "formula_context": CONTEXT_CONFIGURATION}
        )
        or any(
            type(manifest.get(key)) is not int or manifest[key] != 0
            for key in (
                "human_ratings",
                "semantic_approvals",
                "answer_evidence_eligible_candidates",
                "published_candidates",
            )
        )
    ):
        _fail("V5 requires the frozen native-context recovery configuration.")
    books, source_ids, source_slugs = [], set(), set()
    totals = Counter()
    for book in manifest["books"]:
        if revision == "pymupdf_visual_regions_v5":
            if (
                book.get("slug")
                not in {
                    "anatomy-and-physiology-2e",
                    "biology-2e",
                    "chemistry-2e",
                    "concepts-biology",
                }
                or book["slug"] in source_slugs
                or any(
                    type(book.get(key)) is not int or book[key] <= 0
                    for key in ("physical_pages", "source_size_bytes")
                )
                or type(book.get("all_old_region_lineages_preserved")) is not int
                or book["all_old_region_lineages_preserved"] < 0
            ):
                _fail("V5 requires four unique official slugs and integer source counters.")
            source_slugs.add(book["slug"])
        for key in ("source_sha256", "catalog_sha256", "previous_catalog_sha256"):
            _hash(book.get(key))
        if book["source_sha256"] in source_ids:
            _fail("The source manifest repeats a textbook.")
        source_ids.add(book["source_sha256"])
        if revision == "pymupdf_visual_regions_v5":
            filename = book.get("catalog_file")
            if (
                not isinstance(filename, str)
                or Path(filename).name != filename
                or "/" in filename
                or "\\" in filename
                or ":" in filename
                or (root / filename).is_symlink()
            ):
                _fail("The V5 catalog must use a confined regular-file basename.")
        path = (root / book["catalog_file"]).resolve()
        if not path.is_relative_to(root) or file_hash(path) != book["catalog_sha256"]:
            _fail("Catalog location or hash is invalid.")
        items, ids, previous_ids, size = [], set(), set(), 0
        with gzip.open(path, "rb") as stream:
            while line := stream.readline(MAX_LINE_BYTES + 1):
                size += len(line)
                if (
                    len(line) > MAX_LINE_BYTES
                    or size > MAX_CATALOG_BYTES
                    or len(items) >= MAX_REGIONS
                ):
                    _fail("Candidate catalog exceeds bounded import limits.")
                item = json.loads(line)
                _validate_item(item, book, revision)
                previous = item["details"]["previous_region_id"]
                if item["region_id"] in ids or previous in previous_ids:
                    _fail("Duplicate region or source lineage in candidate catalog.")
                ids.add(item["region_id"])
                previous_ids.add(previous)
                totals[item["kind"]] += 1
                if item["kind"] == "table_candidate":
                    totals["rectangular"] += int(_rectangular(item))
                    totals["unresolved"] += int(
                        not _rectangular(item) and not is_inline_reference(item)
                    )
                    totals["references"] += int(is_inline_reference(item))
                    totals["linked_references"] += int(
                        is_inline_reference(item)
                        and item["details"].get("reference_resolution_state") == "linked_candidate"
                    )
                    for cell in item["details"].get("cells_with_native_layout", []):
                        required = {
                            "raw_table_extract_text",
                            "native_textbox_text",
                            "native_glyphs",
                            "position_ordered_text_candidate",
                        }
                        if not required.issubset(cell):
                            _fail("Native cell provenance fields are missing.")
                        for glyph in cell["native_glyphs"]:
                            if not {
                                "character",
                                "bbox_points",
                                "origin_points",
                                "font_size",
                                "font_flags",
                                "native_order",
                            }.issubset(glyph):
                                _fail("Native glyph provenance fields are missing.")
                            totals["native_glyphs"] += 1
                items.append(item)
        if len(items) != book["all_old_region_lineages_preserved"]:
            _fail("The catalog does not preserve every declared legacy lineage.")
        if revision in {"pymupdf_visual_regions_v4", "pymupdf_visual_regions_v5"}:
            try:
                validate_reference_targets(items)
            except ValueError as error:
                _fail(str(error))
            parent_name = book.get("parent_candidate_catalog_file")
            if not isinstance(parent_name, str) or Path(parent_name).name != parent_name:
                _fail("The V3 parent catalog must use a confined bundle basename.")
            if revision == "pymupdf_visual_regions_v5" and (
                "/" in parent_name
                or "\\" in parent_name
                or ":" in parent_name
                or (root / parent_name).is_symlink()
            ):
                _fail("V5 parent sidecars must use confined regular-file basenames.")
            parent_path = (root / parent_name).resolve()
            parent_hash = _hash(book.get("parent_candidate_catalog_sha256"))
            if not parent_path.is_relative_to(root) or file_hash(parent_path) != parent_hash:
                _fail("The immutable V3 parent catalog hash or location changed.")
            parents, parent_size = [], 0
            with gzip.open(parent_path, "rb") as stream:
                while line := stream.readline(MAX_LINE_BYTES + 1):
                    parent_size += len(line)
                    if (
                        len(line) > MAX_LINE_BYTES
                        or parent_size > MAX_CATALOG_BYTES
                        or len(parents) >= MAX_REGIONS
                    ):
                        _fail("The V3 parent catalog exceeds bounded import limits.")
                    parent = json.loads(line)
                    _validate_item(parent, book, "pymupdf_visual_regions_v3")
                    parents.append(parent)
            try:
                validate_v3_parent_lineage(items, parents)
            except ValueError as error:
                _fail(str(error))
        if revision == "pymupdf_visual_regions_v5":
            parent_name = book.get("previous_version_catalog_file")
            if not isinstance(parent_name, str) or Path(parent_name).name != parent_name:
                _fail("The V4 parent catalog must use a confined bundle basename.")
            if revision == "pymupdf_visual_regions_v5" and (
                "/" in parent_name
                or "\\" in parent_name
                or ":" in parent_name
                or (root / parent_name).is_symlink()
            ):
                _fail("V5 parent sidecars must use confined regular-file basenames.")
            parent_path = (root / parent_name).resolve()
            parent_hash = _hash(book.get("previous_version_catalog_sha256"))
            if not parent_path.is_relative_to(root) or file_hash(parent_path) != parent_hash:
                _fail("The immutable V4 parent catalog hash or location changed.")
            v4_parents, parent_size = [], 0
            with gzip.open(parent_path, "rb") as stream:
                while line := stream.readline(MAX_LINE_BYTES + 1):
                    parent_size += len(line)
                    if (
                        len(line) > MAX_LINE_BYTES
                        or parent_size > MAX_CATALOG_BYTES
                        or len(v4_parents) >= MAX_REGIONS
                    ):
                        _fail("The V4 parent catalog exceeds bounded import limits.")
                    parent = json.loads(line)
                    _validate_item(parent, book, "pymupdf_visual_regions_v4")
                    v4_parents.append(parent)
            try:
                validate_reference_targets(v4_parents)
                validate_v3_parent_lineage(v4_parents, parents)
                validate_v4_parent_lineage(items, v4_parents)
            except ValueError as error:
                _fail(str(error))
            formulas = [item for item in items if item["kind"] == "formula_candidate"]
            totals["formula_contexts"] += len(formulas)
            totals["unresolved_formula_contexts"] += sum(
                item["details"]["formula_context"]["anchor_state"] == "unresolved_native_anchor"
                for item in formulas
            )
            totals["formula_context_glyphs"] += sum(
                len(line["native_glyphs"])
                for item in formulas
                for line in item["details"]["formula_context"]["lines"]
            )
        books.append((book, items))
    expected = {
        "region_count": sum(totals[k] for k in KINDS),
        "table_count": totals["table_candidate"],
        "candidate_rectangular_grids": totals["rectangular"],
        "retained_unresolved_tables": totals["unresolved"],
        "native_glyph_records_in_table_candidates": totals["native_glyphs"],
    }
    if revision in {"pymupdf_visual_regions_v4", "pymupdf_visual_regions_v5"}:
        expected["inline_table_reference_count"] = totals["references"]
        expected["linked_table_reference_count"] = totals["linked_references"]
    if revision == "pymupdf_visual_regions_v5":
        expected["formula_context_count"] = totals["formula_contexts"]
        expected["unresolved_formula_context_count"] = totals["unresolved_formula_contexts"]
        expected["native_glyph_records_in_formula_context_candidates"] = totals[
            "formula_context_glyphs"
        ]
    if revision == "pymupdf_visual_regions_v5" and any(
        type(manifest.get(key)) is not int for key in expected
    ):
        _fail("V5 manifest counters must be integers, not boolean or numeric aliases.")
    if any(manifest.get(key) != value for key, value in expected.items()):
        _fail("The source manifest counters differ from the complete catalog.")
    return manifest, books


def stage_catalogs(
    db: Session, actor: User, directory: Path, *, expected_manifest_sha256: str, storage_root: Path
) -> list[dict]:
    """Atomically stage all four catalogs inside the caller's transaction."""
    actor = _admin(db, actor)
    manifest, books = load_bundle(directory, expected_manifest_sha256=expected_manifest_sha256)
    result = []
    with db.begin_nested():
        for book, items in books:
            version = db.scalar(
                select(DocumentVersion)
                .where(DocumentVersion.raw_hash == book["source_sha256"])
                .with_for_update()
            )
            if version is None:
                raise AppError("SOURCE_UNAVAILABLE")
            _source(db, actor, version)
            original = _original(version, storage_root)
            if version.size_bytes != book["source_size_bytes"]:
                _fail("The registered original size differs from the manifest.")
            import pymupdf

            with pymupdf.open(original) as pdf:
                if len(pdf) != book["physical_pages"]:
                    _fail("The physical page count differs from the pinned original.")
                if manifest["candidate_revision"] in {
                    "pymupdf_visual_regions_v4",
                    "pymupdf_visual_regions_v5",
                }:
                    for item in items:
                        try:
                            validate_v4_source_geometry(item)
                        except ValueError as error:
                            _fail(str(error))
                        page = pdf[item["physical_pdf_page"] - 1]
                        if item["details"]["page_size_points"] != [
                            page.rect.width,
                            page.rect.height,
                        ]:
                            _fail("V4 source dimensions differ from the pinned original page.")
                        if (
                            manifest["candidate_revision"] == "pymupdf_visual_regions_v5"
                            and item["kind"] == "formula_candidate"
                        ):
                            try:
                                validate_formula_context_against_page(item, page)
                            except ValueError as error:
                                _fail(str(error))
                        if (
                            is_inline_reference(item)
                            and item["details"].get("reference_resolution_state")
                            == "linked_candidate"
                        ):
                            locator = item["details"]["reference_target_locator"]
                            target = pdf[locator["physical_pdf_page"] - 1]
                            if locator["page_size_points"] != [
                                target.rect.width,
                                target.rect.height,
                            ]:
                                _fail("V4 target dimensions differ from the pinned original page.")
            legacy = {
                row.id: row
                for row in db.scalars(
                    select(VisualRegion).where(VisualRegion.document_version_id == version.id)
                )
            }
            if len(legacy) != len(items) or any(
                row.catalog_sha256 != book["previous_catalog_sha256"] for row in legacy.values()
            ):
                _fail("The complete pinned legacy catalog is required for coexistence.")
            for item in items:
                previous = legacy.get(item["details"]["previous_region_id"])
                if (
                    previous is None
                    or previous.physical_page != item["physical_pdf_page"]
                    or previous.kind != item["kind"]
                ):
                    _fail("Candidate lineage does not match its registered legacy source.")
            identity = dict(
                workspace_id=actor.workspace_id,
                document_version_id=version.id,
                source_sha256=version.raw_hash,
                catalog_sha256=book["catalog_sha256"],
                manifest_sha256=expected_manifest_sha256,
                previous_catalog_sha256=book["previous_catalog_sha256"],
                extractor_revision=manifest["candidate_revision"],
                catalog_schema=CATALOG_SCHEMA,
                configuration_sha256=payload_hash(manifest["frozen_configuration"]),
            )
            counts = dict(Counter(item["kind"] for item in items))
            counts.update(
                total=len(items),
                rectangular_tables=sum(
                    _rectangular(item) for item in items if item["kind"] == "table_candidate"
                ),
                unresolved_tables=sum(
                    not _rectangular(item) and not is_inline_reference(item)
                    for item in items
                    if item["kind"] == "table_candidate"
                ),
            )
            if manifest["candidate_revision"] in {
                "pymupdf_visual_regions_v4",
                "pymupdf_visual_regions_v5",
            }:
                counts["inline_table_references"] = sum(is_inline_reference(item) for item in items)
            artifact = {
                "book": book,
                "configuration": manifest["frozen_configuration"],
                "freeze_sha256": manifest["freeze_sha256"],
                "source_files": manifest["frozen_source_files"],
                "pymupdf_version": manifest["pymupdf_version"],
                "recovery_revision": manifest["recovery_revision"],
            }
            existing = db.scalar(
                select(VisualCatalogVersion).where(
                    VisualCatalogVersion.document_version_id == version.id,
                    VisualCatalogVersion.extractor_revision == manifest["candidate_revision"],
                    VisualCatalogVersion.catalog_sha256 == book["catalog_sha256"],
                )
            )
            if existing:
                if (
                    any(getattr(existing, key) != value for key, value in identity.items())
                    or existing.counts != counts
                    or existing.artifact_manifest != artifact
                ):
                    raise AppError(
                        "CONFLICT",
                        detail="The immutable catalog identity already has different metadata.",
                    )
                recorded = {
                    row.region_id: row
                    for row in db.scalars(
                        select(VisualCatalogCandidate).where(
                            VisualCatalogCandidate.catalog_id == existing.id
                        )
                    )
                }
                if len(recorded) != len(items) or any(
                    item["region_id"] not in recorded
                    or recorded[item["region_id"]].payload_sha256 != payload_hash(item)
                    or recorded[item["region_id"]].raw_payload != item
                    for item in items
                ):
                    raise AppError("CONFLICT", detail="The immutable catalog contents differ.")
                catalog, added = existing, 0
            else:
                catalog = VisualCatalogVersion(
                    **identity,
                    importer_id=actor.id,
                    artifact_manifest=artifact,
                    counts=counts,
                    state="staged",
                )
                db.add(catalog)
                db.flush()
                db.add_all(
                    [
                        VisualCatalogCandidate(
                            catalog_id=catalog.id,
                            region_id=item["region_id"],
                            previous_region_id=item["details"]["previous_region_id"],
                            physical_page=item["physical_pdf_page"],
                            kind=item["kind"],
                            candidate_status=item["status"],
                            payload_sha256=payload_hash(item),
                            raw_payload=item,
                        )
                        for item in items
                    ]
                )
                db.flush()
                added = len(items)
            result.append(
                {
                    "catalog_id": catalog.id,
                    "source_sha256": catalog.source_sha256,
                    "catalog_sha256": catalog.catalog_sha256,
                    "state": catalog.state,
                    "counts": catalog.counts,
                    "added": added,
                    "answer_evidence_eligible": False,
                }
            )
    return result


def owned_catalog(
    db: Session, actor: User, catalog_id: str, *, lock=False, visible=True
) -> VisualCatalogVersion:
    actor = _admin(db, actor)
    query = select(VisualCatalogVersion).where(
        VisualCatalogVersion.id == catalog_id,
        VisualCatalogVersion.workspace_id == actor.workspace_id,
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AppError("NOT_FOUND")
    version = db.get(DocumentVersion, row.document_version_id)
    if version is None or version.raw_hash != row.source_sha256:
        raise AppError("SOURCE_UNAVAILABLE")
    _source(db, actor, version, visible=visible)
    return row


def transition_catalog(
    db: Session,
    actor: User,
    catalog_id: str,
    *,
    expected_version: int,
    state: str,
    storage_root: Path,
) -> VisualCatalogVersion:
    row = owned_catalog(db, actor, catalog_id, lock=True, visible=state != "withdrawn")
    if row.version != expected_version:
        raise AppError("CONFLICT", detail="The catalog state changed; reload its current version.")
    allowed = {
        "staged": {"under_review", "withdrawn"},
        "under_review": {"active", "withdrawn"},
        "active": {"withdrawn"},
        "withdrawn": set(),
    }
    if state not in allowed[row.state]:
        _fail("The requested catalog transition is not allowed.")
    if state != "withdrawn":
        _original(db.get(DocumentVersion, row.document_version_id), storage_root)
    if state == "active":
        candidates = list(
            db.scalars(
                select(VisualCatalogCandidate).where(VisualCatalogCandidate.catalog_id == row.id)
            )
        )
        if not any(_approved(db, row, candidate) for candidate in candidates):
            _fail(
                "Activation requires independently accepted content; unreviewed records remain excluded."
            )
    row.state = state
    row.version += 1
    db.flush()
    return row


def _latest(db: Session, candidate_id: str) -> VisualCatalogReview | None:
    return db.scalar(
        select(VisualCatalogReview)
        .where(VisualCatalogReview.candidate_id == candidate_id)
        .order_by(VisualCatalogReview.reviewed_at.desc(), VisualCatalogReview.id.desc())
        .limit(1)
    )


def _approved(
    db: Session, catalog: VisualCatalogVersion, candidate: VisualCatalogCandidate
) -> bool:
    review = _latest(db, candidate.id)
    return bool(
        review
        and review.decision == "accepted"
        and review.method == "independent_human"
        and review.reviewer_id != catalog.importer_id
        and review.payload_sha256 == candidate.payload_sha256
        and set(review.checks) == set(REVIEW_CHECKS)
        and all(value is True for value in review.checks.values())
    )


def review_candidate(
    db: Session,
    actor: User,
    catalog_id: str,
    region_id: str,
    *,
    previous_review_id: str | None,
    decision: str,
    checks: dict,
    evidence: str,
    storage_root: Path,
) -> VisualCatalogReview:
    catalog = owned_catalog(db, actor, catalog_id, lock=True)
    if catalog.state != "under_review":
        _fail("The catalog must be under review before a decision is recorded.")
    if actor.id == catalog.importer_id:
        raise AppError(
            "FORBIDDEN", detail="A distinct independent reviewer must record the decision."
        )
    _original(db.get(DocumentVersion, catalog.document_version_id), storage_root)
    candidate = db.scalar(
        select(VisualCatalogCandidate).where(
            VisualCatalogCandidate.catalog_id == catalog.id,
            VisualCatalogCandidate.region_id == region_id,
        )
    )
    if candidate is None:
        raise AppError("NOT_FOUND")
    latest = _latest(db, candidate.id)
    if previous_review_id != (latest.id if latest else None):
        raise AppError(
            "CONFLICT", detail="The candidate review changed; reload its current decision."
        )
    if (
        decision not in {"accepted", "rejected", "needs_more"}
        or set(checks) != set(REVIEW_CHECKS)
        or any(type(value) is not bool for value in checks.values())
        or not isinstance(evidence, str)
        or not 12 <= len(evidence.strip()) <= 2000
    ):
        _fail("An explicit independent source review and all applicable checks are required.")
    if decision == "accepted" and (
        not all(checks.values())
        or (candidate.kind == "table_candidate" and not _rectangular(candidate.raw_payload))
    ):
        _fail("Acceptance requires all source checks and a complete candidate table structure.")
    review = VisualCatalogReview(
        candidate_id=candidate.id,
        reviewer_id=actor.id,
        previous_review_id=previous_review_id,
        decision=decision,
        method="independent_human",
        checks=checks,
        evidence=evidence.strip(),
        payload_sha256=candidate.payload_sha256,
    )
    db.add(review)
    catalog.version += 1
    db.flush()
    return review


def candidate_publication_state(
    db: Session, actor: User, catalog_id: str, region_id: str, *, storage_root: Path
) -> dict:
    """Return eligibility for a future validated publication, never corpus access."""
    catalog = owned_catalog(db, actor, catalog_id, visible=False)
    candidate = db.scalar(
        select(VisualCatalogCandidate).where(
            VisualCatalogCandidate.catalog_id == catalog.id,
            VisualCatalogCandidate.region_id == region_id,
        )
    )
    if candidate is None:
        raise AppError("NOT_FOUND")
    version = db.get(DocumentVersion, catalog.document_version_id)
    document = db.get(Document, version.document_id)
    eligible = bool(
        document.active
        and not document.revoked
        and catalog.state == "active"
        and not is_inline_reference(candidate.raw_payload)
        and _approved(db, catalog, candidate)
    )
    if eligible:
        _original(version, storage_root)
    return {
        "catalog_id": catalog.id,
        "region_id": candidate.region_id,
        "source_sha256": catalog.source_sha256,
        "candidate_payload_sha256": candidate.payload_sha256,
        "candidate_status": candidate.candidate_status,
        "eligible_for_separate_publication": eligible,
        "answer_evidence_eligible": False,
        "published": False,
    }


def catalog_summary(db: Session, actor: User, catalog_id: str) -> dict:
    row = owned_catalog(db, actor, catalog_id, visible=False)
    decisions = Counter(
        review.decision
        for review in db.scalars(
            select(VisualCatalogReview)
            .join(
                VisualCatalogCandidate,
                VisualCatalogCandidate.id == VisualCatalogReview.candidate_id,
            )
            .where(VisualCatalogCandidate.catalog_id == row.id)
        )
    )
    return {
        "id": row.id,
        "document_version_id": row.document_version_id,
        "source_sha256": row.source_sha256,
        "catalog_sha256": row.catalog_sha256,
        "manifest_sha256": row.manifest_sha256,
        "previous_catalog_sha256": row.previous_catalog_sha256,
        "extractor_revision": row.extractor_revision,
        "catalog_schema": row.catalog_schema,
        "configuration_sha256": row.configuration_sha256,
        "state": row.state,
        "version": row.version,
        "counts": row.counts,
        "review_history_counts": dict(decisions),
        "answer_evidence_eligible": False,
        "published": False,
    }


def list_candidates(db: Session, actor: User, catalog_id: str, *, offset=0, limit=30) -> list[dict]:
    owned_catalog(db, actor, catalog_id, visible=False)
    if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 100:
        _fail("Candidate pagination is invalid.")
    rows = db.scalars(
        select(VisualCatalogCandidate)
        .where(VisualCatalogCandidate.catalog_id == catalog_id)
        .order_by(VisualCatalogCandidate.physical_page, VisualCatalogCandidate.region_id)
        .offset(offset)
        .limit(limit)
    )
    return [
        {
            "id": row.id,
            "region_id": row.region_id,
            "previous_region_id": row.previous_region_id,
            "physical_pdf_page": row.physical_page,
            "kind": row.kind,
            "candidate_status": row.candidate_status,
            "payload_sha256": row.payload_sha256,
            "bbox_points": row.raw_payload["bbox_points"],
            "answer_evidence_eligible": False,
        }
        for row in rows
    ]


def candidate_detail(db: Session, actor: User, catalog_id: str, region_id: str) -> dict:
    owned_catalog(db, actor, catalog_id, visible=False)
    row = db.scalar(
        select(VisualCatalogCandidate).where(
            VisualCatalogCandidate.catalog_id == catalog_id,
            VisualCatalogCandidate.region_id == region_id,
        )
    )
    if row is None:
        raise AppError("NOT_FOUND")
    return {
        "catalog_id": row.catalog_id,
        "region_id": row.region_id,
        "previous_region_id": row.previous_region_id,
        "payload_sha256": row.payload_sha256,
        "candidate_status": row.candidate_status,
        "raw_payload": row.raw_payload,
        "answer_evidence_eligible": False,
    }
