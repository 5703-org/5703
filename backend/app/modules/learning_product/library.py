"""Browse exact released source units and freeze reading selections before retrieval."""

import hashlib
import json
import re
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import load_only
from app.core.exceptions import AppError
from app.modules.identity.models import User
from app.modules.knowledge.models import (
    ActiveCorpus,
    CorpusRelease,
    ReleaseChunk,
    Chunk,
    Document,
    DocumentVersion,
    ProcessingRun,
    SourceUnit,
)


def text_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fingerprint(value):
    return text_hash(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def section_id(processing_id, section):
    return text_hash(processing_id + "\n" + section)


def released_rows(db, actor, release_id=None, document_id=None):
    if release_id is None:
        pointer = db.get(ActiveCorpus, 1)
        release_id = pointer.release_id if pointer else None
    release = db.get(CorpusRelease, release_id) if release_id else None
    if release is None or release.state not in ("active", "validated", "retired"):
        raise AppError("SOURCE_UNAVAILABLE", detail="A ready published corpus is required.")
    query = (
        select(Chunk, Document, ProcessingRun, DocumentVersion)
        .join(ReleaseChunk, ReleaseChunk.chunk_id == Chunk.id)
        .join(Document, Document.id == Chunk.document_id)
        .join(ProcessingRun, ProcessingRun.id == Chunk.processing_id)
        .join(DocumentVersion, DocumentVersion.id == ProcessingRun.document_version_id)
        .join(User, User.id == Document.owner_id)
        .where(
            ReleaseChunk.release_id == release_id,
            Document.active.is_(True),
            Document.revoked.is_(False),
            User.workspace_id == actor.workspace_id,
        )
        # A library index or reading scope needs identity, membership and
        # provenance first. Loading every chunk's full text and every run's
        # processing metadata for the four-book release made the library
        # index block the browser for tens of seconds. Exact text is fetched
        # lazily only for chunks actually selected as evidence.
        .options(
            load_only(
                Chunk.id,
                Chunk.processing_id,
                Chunk.document_id,
                Chunk.section,
                Chunk.spans,
            ),
            load_only(
                Document.id,
                Document.title,
                Document.edition,
                Document.source_url,
                Document.license,
                Document.active,
                Document.revoked,
                Document.owner_id,
            ),
            load_only(ProcessingRun.id, ProcessingRun.document_version_id),
            load_only(
                DocumentVersion.id,
                DocumentVersion.raw_hash,
                DocumentVersion.media_type,
            ),
        )
        .order_by(Document.title, Chunk.id)
        .execution_options(populate_existing=True)
    )
    if document_id:
        query = query.where(Document.id == document_id)
    rows = list(db.execute(query))
    return release, rows


def book_data(db, actor, document_id, release_id=None):
    release, rows = released_rows(db, actor, release_id, document_id)
    if not rows:
        raise AppError(
            "EVIDENCE_UNAVAILABLE", detail="The textbook is not visible in this release."
        )
    runs = {row[2].id for row in rows}
    if len(runs) != 1:
        raise AppError(
            "SOURCE_UNAVAILABLE", detail="The textbook has ambiguous processing membership."
        )
    allowed_units = {s["unit_id"] for row in rows for s in row[0].spans if "unit_id" in s}
    units = list(
        db.scalars(
            select(SourceUnit)
            .where(SourceUnit.id.in_(allowed_units), SourceUnit.processing_id.in_(runs))
            .order_by(SourceUnit.sequence, SourceUnit.id)
        )
    )
    if len(units) != len(allowed_units):
        raise AppError(
            "EVIDENCE_UNAVAILABLE", detail="Released source-unit membership is incomplete."
        )
    return release, rows, units


def books(db, actor):
    release, rows = released_rows(db, actor)
    groups: dict[str, list[Any]] = {}
    for row in rows:
        groups.setdefault(row[1].id, []).append(row)
    out = []
    for document_id, group in groups.items():
        _, document, run, version = group[0]
        if len({r[2].id for r in group}) != 1:
            raise AppError("SOURCE_UNAVAILABLE", detail="Ambiguous textbook version in release.")
        unit_ids = {s["unit_id"] for r in group for s in r[0].spans if "unit_id" in s}
        sections = set(db.scalars(select(SourceUnit.section).where(SourceUnit.id.in_(unit_ids))))
        out.append(
            dict(
                id=document_id,
                title=document.title,
                edition=document.edition,
                release_id=release.id,
                document_version_id=version.id,
                source_sha256=version.raw_hash,
                processing_id=run.id,
                source_url=document.source_url,
                license=document.license,
                section_count=len(sections),
                unit_count=len(unit_ids),
            )
        )
    return out


def sections(db, actor, document_id, query=None, release_id=None):
    _, _, units = book_data(db, actor, document_id, release_id)
    groups: dict[str, list[SourceUnit]] = {}
    for unit in units:
        groups.setdefault(section_id(unit.processing_id, unit.section), []).append(unit)
    ids = list(groups)
    result = []
    for index, (key, group) in enumerate(groups.items()):
        title = group[0].section or "Untitled source section"
        if query and query.casefold() not in title.casefold():
            continue
        objectives = []
        for unit in group:
            for objective in published_objectives(unit.raw_text, unit.cleaned_text):
                if objective not in objectives:
                    objectives.append(objective)
        # Only publisher-labelled objectives; no inferred semantic prerequisites.
        result.append(
            dict(
                id=key,
                title=title,
                first_page=min(u.page for u in group),
                last_page=max(u.page for u in group),
                unit_count=len(group),
                concepts=[title],
                learning_objectives=objectives[:20],
                related_section_ids=ids[max(0, index - 1) : index] + ids[index + 1 : index + 2],
            )
        )
    return result


def published_objectives(raw_text, cleaned_text):
    """Extract a bounded explicitly labelled objective list, preserving source words."""
    lines = raw_text.splitlines()
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if re.fullmatch(
                r"\s*(?:LEARNING OBJECTIVES|By the end of this section, you will be able to:)\s*",
                line,
                re.I,
            )
        ),
        None,
    )
    if start is None:
        return []
    result: list[str] = []
    pending: list[str] = []
    cleaned = " ".join(cleaned_text.split())

    def finish():
        if pending:
            text = " ".join(pending).strip()
            if len(text) <= 1000 and text in cleaned:
                result.append(text)
            pending.clear()

    for line in lines[start + 1 : start + 42]:
        line = line.strip()
        if re.match(r"^By the end of this section", line, re.I):
            continue
        bullet = re.match(r"^[•●▪]\s*(.+)$", line)
        if bullet:
            finish()
            pending.append(bullet[1])
        elif pending and line:
            pending.append(line)
        elif pending:
            finish()
            break
        elif not line:
            continue
        else:
            break
    finish()
    return result[:20]


def locator(release_id, document_id, unit):
    return dict(
        release_id=release_id,
        document_id=document_id,
        processing_id=unit.processing_id,
        source_unit_id=unit.id,
        text_hash=text_hash(unit.cleaned_text),
        start=0,
        end=len(unit.cleaned_text),
    )


def reading_page(db, actor, document_id, section=None, offset=0, limit=20, source_unit_id=None):
    release, rows, units = book_data(db, actor, document_id)
    if section:
        units = [u for u in units if section_id(u.processing_id, u.section) == section]
    if source_unit_id:
        position = next((i for i, u in enumerate(units) if u.id == source_unit_id), None)
        if position is None:
            raise AppError("EVIDENCE_UNAVAILABLE")
        offset = (position // limit) * limit
    document = rows[0][1]
    selected = units[offset : offset + limit]
    return dict(
        items=[
            dict(
                id=u.id,
                sequence=u.sequence,
                page=u.page,
                section_id=section_id(u.processing_id, u.section),
                section=u.section,
                text=u.cleaned_text,
                locator=locator(release.id, document_id, u),
                source_url=document.source_url,
                license=document.license,
            )
            for u in selected
        ],
        offset=offset,
        next_offset=offset + limit if offset + limit < len(units) else None,
        total=len(units),
    )


def validate_locator(db, actor, source):
    value = source.model_dump() if hasattr(source, "model_dump") else source
    release, rows, units = book_data(db, actor, value["document_id"], value["release_id"])
    unit = next((u for u in units if u.id == value["source_unit_id"]), None)
    if (
        unit is None
        or unit.processing_id != value["processing_id"]
        or text_hash(unit.cleaned_text) != value["text_hash"]
    ):
        raise AppError("EVIDENCE_UNAVAILABLE", detail="The exact source unit is unavailable.")
    end = value.get("end") if value.get("end") is not None else len(unit.cleaned_text)
    start = value.get("start", 0)
    if (
        type(start) is not int
        or type(end) is not int
        or not 0 <= start < end <= len(unit.cleaned_text)
    ):
        raise AppError("VALIDATION_FAILED", detail="The source range is invalid.")
    return release, rows, unit


def freeze_reading_context(db, actor, context):
    context = context.model_dump() if hasattr(context, "model_dump") else dict(context)
    scope = context.get("scope", "chapter")
    if scope not in ("chapter", "textbook", "all"):
        raise AppError("VALIDATION_FAILED", detail="Unknown reading scope.")
    release, rows = released_rows(db, actor)
    document_id = context.get("document_id")
    unit_id = context.get("source_unit_id")
    if not document_id and scope != "all":
        raise AppError("VALIDATION_FAILED", detail="This reading scope requires a textbook.")
    unit, selection, processing_id, section, section_key = None, None, None, None, None
    if document_id:
        _, book_rows, units = book_data(db, actor, document_id, release.id)
        processing_id = book_rows[0][2].id
        if unit_id:
            unit = next((u for u in units if u.id == unit_id), None)
            if unit is None:
                raise AppError("EVIDENCE_UNAVAILABLE")
            section, section_key = unit.section, section_id(unit.processing_id, unit.section)
    elif unit_id or context.get("selection"):
        raise AppError("VALIDATION_FAILED", detail="A selected unit requires its textbook.")
    if scope == "chapter" and unit is None:
        raise AppError("VALIDATION_FAILED", detail="Chapter scope requires an exact source unit.")
    selected = context.get("selection")
    if selected:
        if unit is None:
            raise AppError(
                "VALIDATION_FAILED", detail="A paragraph selection requires its source unit."
            )
        selected = selected.model_dump() if hasattr(selected, "model_dump") else selected
        start, end = selected["start"], selected["end"]
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(unit.cleaned_text)
        ):
            raise AppError("VALIDATION_FAILED", detail="The selected paragraph range is invalid.")
        exact = unit.cleaned_text[start:end]
        if exact != selected["text"] or len(exact) > 8000:
            raise AppError(
                "VALIDATION_FAILED", detail="The paragraph must match the exact source range."
            )
        selection = dict(
            start=start,
            end=end,
            text=exact,
            text_hash=text_hash(exact),
            unit_text_hash=text_hash(unit.cleaned_text),
        )
    allowed = sorted(
        row[0].id
        for row in rows
        if scope == "all"
        or (
            row[1].id == document_id
            and row[2].id == processing_id
            and (scope == "textbook" or row[0].section == section)
        )
    )
    if not allowed:
        raise AppError("EVIDENCE_UNAVAILABLE", detail="No released passages match this scope.")
    selected_chunks = []
    if selection:
        if unit is None:
            raise AppError("EVIDENCE_UNAVAILABLE")
        for row in rows:
            chunk = row[0]
            if chunk.id not in allowed or chunk.processing_id != processing_id:
                continue
            for span in chunk.spans:
                if span.get("unit_id") != unit.id:
                    continue
                start, end = span.get("start"), span.get("end")
                local_start, local_end = span.get("chunk_start"), span.get("chunk_end")
                if (
                    type(start) is not int
                    or type(end) is not int
                    or type(local_start) is not int
                    or type(local_end) is not int
                    or not 0 <= start < end <= len(unit.cleaned_text)
                    or not 0 <= local_start < local_end <= len(chunk.text)
                    or unit.cleaned_text[start:end] != chunk.text[local_start:local_end]
                    or text_hash(chunk.text) != chunk.text_hash
                ):
                    raise AppError(
                        "EVIDENCE_UNAVAILABLE", detail="The selected chunk mapping is invalid."
                    )
                if start < selection["end"] and end > selection["start"]:
                    selected_chunks.append(chunk.id)
                    break
        if not selected_chunks:
            raise AppError(
                "EVIDENCE_UNAVAILABLE", detail="The selected text has no released chunk mapping."
            )
    result = dict(
        version="reading_scope_v1",
        release_id=release.id,
        scope=scope,
        document_id=document_id,
        processing_id=processing_id,
        source_unit_id=unit_id,
        section=section,
        section_id=section_key,
        selection=selection,
        allowed_chunk_ids=allowed,
        selected_chunk_ids=sorted(set(selected_chunks)),
    )
    result["scope_hash"] = fingerprint(result)
    return result


def validate_reading_context(db, actor, frozen):
    """Recheck the pinned scope and visibility without following a changed active pointer."""
    payload = dict(frozen)
    expected = payload.pop("scope_hash", None)
    if expected != fingerprint(payload) or payload.get("version") != "reading_scope_v1":
        raise AppError("EVIDENCE_UNAVAILABLE", detail="Reading scope identity changed.")
    allowed = payload.get("allowed_chunk_ids")
    selected_ids = payload.get("selected_chunk_ids") or []
    if (
        not isinstance(allowed, list)
        or not allowed
        or len(set(allowed)) != len(allowed)
        or not set(selected_ids) <= set(allowed)
    ):
        raise AppError("EVIDENCE_UNAVAILABLE", detail="Reading scope membership changed.")
    _, rows = released_rows(db, actor, payload["release_id"])
    current = {row[0].id: row for row in rows}
    for chunk_id in payload.get("allowed_chunk_ids") or []:
        row = current.get(chunk_id)
        if row is None or (
            payload["scope"] != "all"
            and (row[1].id != payload["document_id"] or row[2].id != payload["processing_id"])
        ):
            raise AppError(
                "EVIDENCE_UNAVAILABLE", detail="A scoped passage is no longer available."
            )
        if payload["scope"] == "chapter" and row[0].section != payload["section"]:
            raise AppError("EVIDENCE_UNAVAILABLE", detail="Scoped section identity changed.")
    if payload.get("source_unit_id"):
        _, _, units = book_data(db, actor, payload["document_id"], payload["release_id"])
        unit = next((u for u in units if u.id == payload["source_unit_id"]), None)
        if unit is None or unit.processing_id != payload["processing_id"]:
            raise AppError("EVIDENCE_UNAVAILABLE")
        selected = payload.get("selection")
        if selected and (
            text_hash(unit.cleaned_text) != selected["unit_text_hash"]
            or unit.cleaned_text[selected["start"] : selected["end"]] != selected["text"]
        ):
            raise AppError("EVIDENCE_UNAVAILABLE", detail="Selected paragraph identity changed.")
    return frozen


def selected_reading_evidence(db, actor, frozen):
    """Admit selected exact source chunks without another search or embedding call."""
    validate_reading_context(db, actor, frozen)
    from app.modules.knowledge.service import _retrieval_row

    _, rows = released_rows(db, actor, frozen["release_id"])
    ids = set(frozen.get("selected_chunk_ids") or [])
    selected = [r for r in rows if r[0].id in ids]
    if len(selected) != len(ids):
        raise AppError("EVIDENCE_UNAVAILABLE")
    units = list(
        db.scalars(
            select(SourceUnit).where(SourceUnit.processing_id.in_({r[2].id for r in selected}))
        )
    )
    provenance = {
        "media_types": {r[2].id: r[3].media_type for r in selected},
        "visual_pages": {
            (u.processing_id, u.page)
            for u in units
            if any(i.get("code") == "UNEXTRACTED_VISUAL_CONTENT" for i in u.issues)
        },
    }
    return [_retrieval_row((None, r[0], r[1]), provenance) for r in selected]
