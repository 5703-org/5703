"""Exact source validation and one publication projection for every learner route."""

import copy
import hashlib
from sqlalchemy import select
from contracts.learning import CitationView, PresentationOut
from app.core.exceptions import AppError
from app.modules.answering.models import Answer, AnswerRequest, Evidence
from app.modules.knowledge.models import Chunk, Document, ProcessingRun, SourceUnit, ReleaseChunk
from .models import (
    SourceFragment,
    AnswerAttribution,
    AnswerPresentation,
    LearningExposure,
    PrivateAnswerDraft,
    LearningTask,
)
from .memory import digest


def source_map(db, req, evidence):
    result = {}
    for ev in evidence:
        chunk = db.get(Chunk, ev["chunk_id"], populate_existing=True)
        doc = db.get(Document, ev["asset_id"], populate_existing=True)
        run = db.get(ProcessingRun, ev["processing_id"], populate_existing=True)
        if (
            not chunk
            or not doc
            or not doc.active
            or doc.revoked
            or not run
            or chunk.processing_id != run.id
            or chunk.document_id != doc.id
            or not db.get(ReleaseChunk, (req.release_id, chunk.id))
        ):
            raise AppError("EVIDENCE_UNAVAILABLE")
        units = []
        for uid in dict.fromkeys(span["unit_id"] for span in chunk.spans):
            unit = db.get(SourceUnit, uid, populate_existing=True)
            if not unit or unit.processing_id != run.id or unit.quality != "ready":
                raise AppError("EVIDENCE_UNAVAILABLE")
            recorded = run.counts.get("source_unit_hashes", {}).get(uid)
            if recorded and (
                hashlib.sha256(unit.raw_text.encode()).hexdigest() != recorded["raw_hash"]
                or hashlib.sha256(unit.cleaned_text.encode()).hexdigest()
                != recorded["cleaned_hash"]
            ):
                raise AppError("EVIDENCE_UNAVAILABLE", "A selected source unit changed.")
            units.append(
                {
                    "id": unit.id,
                    "page": unit.page,
                    "cleaned_text": unit.cleaned_text,
                    "text_hash": hashlib.sha256(unit.cleaned_text.encode()).hexdigest(),
                    "raw_text": unit.raw_text,
                    "raw_text_hash": hashlib.sha256(unit.raw_text.encode()).hexdigest(),
                }
            )
        mapping = {
            "document_version_id": run.document_version_id,
            "processing_id": run.id,
            "asset_id": doc.id,
            "chunk_text": chunk.text,
            "chunk_hash": chunk.text_hash,
            "spans": copy.deepcopy(chunk.spans),
            "units": units,
        }
        if ev.get("chunk_start") is not None:
            mapping.update(submitted_start=ev["chunk_start"], submitted_end=ev["chunk_end"])
        result[chunk.id] = mapping
    return result


def exact_evidence(chunk, item):
    if not chunk or hashlib.sha256(item["text"].encode()).hexdigest() != item["text_hash"]:
        return False
    if item.get("chunk_start") is None:
        return chunk.text == item["text"] and chunk.text_hash == item["text_hash"]
    a, b = item.get("chunk_start"), item.get("chunk_end")
    return (
        type(a) is int
        and type(b) is int
        and 0 <= a < b <= len(chunk.text)
        and item.get("chunk_text_hash") == chunk.text_hash
        and chunk.text[a:b] == item["text"]
    )


def persist_result(db, req, answer, result):
    """Validate model-selected identities before publishing any new source interface."""
    if not req.command.get("enhancement_version"):
        return
    from retrieval.source_spans import map_fragments
    from retrieval.source_spans_v2 import VERSION as raw_policy, map_fragments as raw_mapper

    policy = req.command.get("source_block_policy", "legacy_source_blocks_v1")
    if policy == raw_policy:
        mapper = raw_mapper
    elif policy == "legacy_source_blocks_v1":
        mapper = map_fragments
    else:
        raise AppError("VALIDATION_FAILED", "The frozen source block policy is unsupported.")
    mapping = source_map(db, req, result.evidence) if result.evidence else {}
    ranges = {r["evidence_id"]: r for r in result.attribution.get("evidence_ranges", [])}
    for ev in result.evidence:
        selected = ranges.get(ev["evidence_id"])
        if selected:
            ev.update({k: selected[k] for k in ("chunk_text_hash", "chunk_start", "chunk_end")})
            mapping[ev["chunk_id"]].update(
                submitted_start=ev["chunk_start"], submitted_end=ev["chunk_end"]
            )
        if not exact_evidence(db.get(Chunk, ev["chunk_id"]), ev):
            raise AppError(
                "VALIDATION_FAILED", "Selected source range does not match the frozen corpus."
            )
    candidates, _ = mapper(result.evidence, mapping) if result.evidence else ([], [])
    allowed = {(f["fragment_id"], f["evidence_id"]): f for f in candidates}
    attribution = copy.deepcopy(result.attribution)
    fragments = attribution.get("fragments", [])
    for fragment in fragments:
        expected = allowed.get((fragment["fragment_id"], fragment["evidence_id"]))
        keys = (
            "source_unit_id",
            "processing_id",
            "document_version_id",
            "start",
            "end",
            "exact_text",
            "text_hash",
            "chunk_start",
            "chunk_end",
            "evidence_id",
        )
        if not expected or any(fragment.get(k) != expected.get(k) for k in keys):
            raise AppError(
                "VALIDATION_FAILED", "A selected source fragment failed structural validation."
            )
        row = db.get(SourceFragment, fragment["fragment_id"])
        if row is None:
            db.add(
                SourceFragment(
                    id=fragment["fragment_id"],
                    processing_id=fragment["processing_id"],
                    source_unit_id=fragment["source_unit_id"],
                    document_version_id=fragment["document_version_id"],
                    start=fragment["start"],
                    end=fragment["end"],
                    text=fragment["exact_text"],
                    text_hash=fragment["text_hash"],
                    block_kind=fragment.get("block_kind", "prose"),
                    mapping_quality=fragment.get("mapping_quality", "exact_cleaned_text"),
                )
            )
        elif row.text != fragment["exact_text"] or row.text_hash != fragment["text_hash"]:
            raise AppError("VALIDATION_FAILED", "Source fragment identity collision.")
    fragment_ids = {f["fragment_id"] for f in fragments}
    for claim in attribution.get("claims", []):
        text = result.response.get(claim.get("answer_field", "answer_text")) or ""
        a, b = claim.get("start"), claim.get("end")
        if (
            type(a) is not int
            or type(b) is not int
            or not 0 <= a < b <= len(text)
            or text[a:b] != claim.get("text")
            or not set(claim.get("fragment_ids", [])) <= fragment_ids
        ):
            raise AppError("VALIDATION_FAILED", "Claim offsets or source associations are invalid.")
    context = req.command.get("teaching_context") or {}
    projection = copy.deepcopy(result.delivered_projection or {})
    if projection.get("response", result.response) != result.response:
        raise AppError(
            "VALIDATION_FAILED", "Published response differs from the checked projection."
        )
    projection["response"] = result.response
    projection["teaching_mode"] = context.get("teaching_mode", "direct")
    projection["help_level"] = context.get("help_level", 0)
    views = []
    evs = {ev["evidence_id"]: ev for ev in result.evidence}
    for raw in projection.get("citation_views", []):
        view = CitationView.model_validate(
            {k: v for k, v in raw.items() if k in CitationView.model_fields}
        ).model_dump()
        ev = evs.get(view["evidence_id"])
        if not ev or view["evidence_id"] not in result.response.get("citations", []):
            raise AppError("VALIDATION_FAILED", "A source view is not an actual answer citation.")
        for segment in view["segments"]:
            if (
                segment["text"]
                and segment["text"] not in ev["text"]
                and not (
                    segment["text"] == "\n…\n"
                    and not segment["fragment_ids"]
                    and not segment["highlight"]
                )
            ):
                raise AppError(
                    "VALIDATION_FAILED", "Source preview includes text outside submitted evidence."
                )
            if not set(segment["fragment_ids"]) <= fragment_ids:
                raise AppError(
                    "VALIDATION_FAILED", "Source preview references an unknown fragment."
                )
            for fid in segment["fragment_ids"]:
                bound = next(
                    (
                        f
                        for f in fragments
                        if f["fragment_id"] == fid and f["evidence_id"] == view["evidence_id"]
                    ),
                    None,
                )
                if not bound or bound["exact_text"] not in segment["text"]:
                    raise AppError(
                        "VALIDATION_FAILED",
                        "Source preview fragment does not match its displayed text and evidence.",
                    )
        # Explicit expansion is required for source URLs on all controlled hint conditions.
        if context.get("teaching_mode") == "hint":
            view["source_url"] = None
        else:
            view["source_url"] = ev.get("source_url")
        view["license"] = ev.get("license")
        view["available_actions"] = ["citation_opened", "full_source_requested"]
        views.append(view)
    projection["checked_projection"] = copy.deepcopy(result.delivered_projection)
    projection["citation_views"] = views
    db.add(
        AnswerAttribution(
            answer_id=answer.id,
            strategy=req.command.get("attribution_strategy", "posthoc_spans"),
            payload=attribution,
        )
    )
    presentation = AnswerPresentation(
        answer_id=answer.id,
        task_id=context.get("task_id"),
        payload=projection,
        content_hash=digest(projection),
        policy_version=projection.get("policy_version", "learning_enhancement_v1"),
    )
    db.add(presentation)
    db.flush()
    db.add(
        LearningExposure(
            owner_id=req.owner_id,
            task_id=presentation.task_id,
            answer_id=answer.id,
            presentation_id=presentation.id,
            kind="delivered",
            idempotency_key="delivered:" + answer.id,
            payload={
                "content_hash": presentation.content_hash,
                "help_level": context.get("help_level", 0),
            },
        )
    )


def persist_private_records(db, req, result):
    for phase, records in (("generated_draft", result.drafts), ("online_check", result.checks)):
        for record in records:
            db.add(
                PrivateAnswerDraft(
                    request_id=req.id,
                    memory_snapshot_id=req.command.get("memory_snapshot_id"),
                    phase=phase,
                    payload=record,
                )
            )


def presentation_for(db, answer_id):
    return db.scalar(select(AnswerPresentation).where(AnswerPresentation.answer_id == answer_id))


def visible_views(db, presentation):
    rows = {
        r.evidence_id: r
        for r in db.scalars(select(Evidence).where(Evidence.answer_id == presentation.answer_id))
    }
    result = []
    for view in presentation.payload.get("citation_views", []):
        ev = rows.get(view["evidence_id"])
        doc = db.get(Document, ev.document_id) if ev else None
        if doc and not doc.revoked:
            result.append(view)
    return result


def presentation_out(db, row):
    return PresentationOut(
        id=row.id,
        task_id=row.task_id,
        teaching_mode=row.payload.get("teaching_mode", "direct"),
        help_level=row.payload.get("help_level", 0),
        policy_version=row.policy_version,
        content_hash=row.content_hash,
        citation_views=visible_views(db, row),
    ).model_dump()


def public_support(support):
    """Expose typed published metadata, never private derivation inputs or rationale."""
    from contracts.learning import ClaimSupportOut

    safe = {
        k: v
        for k, v in support.items()
        if k
        in {
            "status",
            "checker_configuration_id",
            "checker_model",
            "strategy",
            "checked_at",
            "basis",
            "problem_quote",
            "human_rating",
            "check_state",
            "general_knowledge_status",
        }
    }
    validation = support.get("derivation_validation")
    if support.get("basis") == "derived_calculation" and isinstance(validation, dict):
        safe["derivation_validation"] = {
            "arithmetic_checked": validation.get("valid") is True,
            "formula_basis": validation.get("formula_basis", "textbook"),
            "conditional_on_given_rule": validation.get("conditional_on_given_rule") is True,
            "scope": "arithmetic_and_exact_quotes_only",
            "formula_and_units": "model_judgment_not_independent",
            "human_rating": None,
        }
    else:
        safe["derivation_validation"] = None
    return ClaimSupportOut.model_validate(safe).model_dump(exclude_unset=True)


def public_attribution(db, presentation):
    row = db.scalar(
        select(AnswerAttribution).where(AnswerAttribution.answer_id == presentation.answer_id)
    )
    if not row:
        return None
    allowed = {
        fid
        for view in visible_views(db, presentation)
        for segment in view["segments"]
        for fid in segment.get("fragment_ids", [])
    }
    payload = row.payload
    return {
        "strategy": row.strategy,
        "claims": [
            {
                **{
                    k: claim[k]
                    for k in ("claim_id", "answer_field", "start", "end", "text", "fragment_ids")
                },
                "support": public_support(claim.get("support", {})),
            }
            for claim in payload.get("claims", [])
        ],
        "fragments": [f for f in payload.get("fragments", []) if f["fragment_id"] in allowed],
    }


def citation_view(db, presentation, evidence_id, claim_id=None):
    for view in visible_views(db, presentation):
        if view["evidence_id"] == evidence_id and (
            claim_id is None or claim_id in view["claim_ids"]
        ):
            result = copy.deepcopy(view)
            if claim_id:
                attribution = db.scalar(
                    select(AnswerAttribution).where(
                        AnswerAttribution.answer_id == presentation.answer_id
                    )
                )
                claim = (
                    next(
                        (
                            c
                            for c in attribution.payload.get("claims", [])
                            if c["claim_id"] == claim_id
                        ),
                        None,
                    )
                    if attribution
                    else None
                )
                if not claim:
                    raise AppError("NOT_FOUND")
                allowed = set(claim.get("fragment_ids", []))
                result["claim_ids"] = [claim_id]
                for segment in result["segments"]:
                    segment["highlight"] = bool(
                        segment["highlight"] and allowed.intersection(segment["fragment_ids"])
                    )
                    segment["fragment_ids"] = [
                        fid for fid in segment["fragment_ids"] if fid in allowed
                    ]
            return result
    ev = db.scalar(
        select(Evidence).where(
            Evidence.answer_id == presentation.answer_id, Evidence.evidence_id == evidence_id
        )
    )
    if ev and (not db.get(Document, ev.document_id) or db.get(Document, ev.document_id).revoked):
        raise AppError("EVIDENCE_UNAVAILABLE")
    raise AppError("NOT_FOUND")


def record_exposure(db, actor, answer, body, key):
    from app.modules.answering.service import owned_session

    req = db.get(AnswerRequest, answer.request_id)
    if req.owner_id != actor.id:
        raise AppError("NOT_FOUND")
    owned_session(db, req.session_id, actor, lock=True)
    presentation = presentation_for(db, answer.id)
    if not presentation or presentation.id != body.presentation_id:
        raise AppError("CONFLICT", "The presentation changed. Reload the saved answer.")
    if not key or len(key) > 128 or not key.isascii():
        raise AppError("VALIDATION_FAILED", "Use a bounded ASCII idempotency key.")
    material = {"answer_id": answer.id, **body.model_dump()}
    prior = db.scalar(
        select(LearningExposure).where(
            LearningExposure.owner_id == actor.id, LearningExposure.idempotency_key == key
        )
    )
    if prior:
        if prior.payload.get("request_hash") != digest(material):
            raise AppError("IDEMPOTENCY_CONFLICT")
        view = prior.payload.get("citation_view")
        if view:
            citation_view(db, presentation, view["evidence_id"], body.claim_id)
        return {
            "id": prior.id,
            "kind": prior.kind,
            "presentation_id": presentation.id,
            "citation_view": view,
        }
    view = None
    if body.kind in {"citation_opened", "full_source_requested"}:
        if not body.evidence_id:
            raise AppError("VALIDATION_FAILED", "Select a source passage.")
        view = citation_view(db, presentation, body.evidence_id, body.claim_id)
        if body.kind == "full_source_requested":
            ev = db.scalar(
                select(Evidence).where(
                    Evidence.answer_id == answer.id, Evidence.evidence_id == body.evidence_id
                )
            )
            # Explicit action returns the exact submitted snapshot, never a newer corpus version.
            view.update(
                title=ev.payload["source_title"],
                source_title=ev.payload["source_title"],
                section=ev.payload["section"],
                pages=ev.payload["pages"],
                source_url=ev.payload.get("source_url"),
                segments=[{"text": ev.payload["text"], "highlight": False, "fragment_ids": []}],
            )
    elif body.kind == "rendered" and body.surface != "answer":
        parent = (
            db.get(LearningExposure, body.parent_exposure_id) if body.parent_exposure_id else None
        )
        expected = "full_source_requested" if body.surface == "full_source" else "citation_opened"
        if (
            not parent
            or parent.owner_id != actor.id
            or parent.presentation_id != presentation.id
            or parent.kind != expected
            or parent.payload.get("evidence_id") != body.evidence_id
        ):
            raise AppError(
                "VALIDATION_FAILED",
                "Rendered source events require their actual preceding disclosure receipt.",
            )
    task = db.get(LearningTask, presentation.task_id) if presentation.task_id else None
    if task:
        task.exposure_epoch += 1
    event = LearningExposure(
        owner_id=actor.id,
        task_id=presentation.task_id,
        answer_id=answer.id,
        presentation_id=presentation.id,
        kind=body.kind,
        idempotency_key=key,
        payload={**material, "request_hash": digest(material), "citation_view": view},
    )
    db.add(event)
    db.flush()
    db.commit()
    return {
        "id": event.id,
        "kind": event.kind,
        "presentation_id": presentation.id,
        "citation_view": view,
    }
