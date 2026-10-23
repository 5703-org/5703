"""Private assertion/source transport; semantic support remains an independent gate."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Annotated, Literal

from pydantic import Field

from .reliability_v3 import Strict
from .reliability_v4 import (
    CalculationClaim,
    GeneralClaim,
    GivenClaim,
    GuidanceClaim,
    TextbookClaim,
)
from .reliability_v5 import OrdinaryQuestionCheckV5, TeachingDraftV5, response_claims
from .attempt_evaluation_contract_v1 import ordinary_question_without_attempt

POLICY = "assertion_source_v1"
DRAFT_SCHEMA = "teaching_assertion_draft_v1"
CHECK_SCHEMA = "joint_assertion_check_v1"
GENERATION_BANK_ENCODING = "assertion_source_tables_v1"
GENERATION_BANK_INSTRUCTIONS = (
    "ASSERTION_SOURCE_BANK and ASSERTION_SOURCE_LOCATORS use lossless source tables. "
    "A list of objects is already expanded; otherwise pair each row with its columns "
    "by position. Each bank row source_locator is a "
    "zero-based index into ASSERTION_SOURCE_LOCATORS rows; replace that index with "
    "the complete reconstructed locator object. Reconstruct every original bank "
    "field, exact complete source text, source_id, evidence_id, fragment_id and "
    "text_sha256. This encoding changes no source membership, citation selection, "
    "support requirement or publication rule."
)


class Assertion(Strict):
    assertion_id: str = Field(pattern=r"^[AS][0-9]{3}$")
    text: str = Field(min_length=1, max_length=4000)
    source_ids: list[str] = Field(max_length=12)


class AssertionDraft(TeachingDraftV5):
    answer_text: list[Assertion] = Field(min_length=1, max_length=16)
    short_answer: Assertion | None
    tutor_question: None
    learner_attempt_evaluation: None


class ProofAudit(Strict):
    all_predicates_entailed: bool
    actor_identity_preserved: bool
    conditions_preserved: bool
    causal_bridges_entailed: bool
    missing_predicates: list[
        Annotated[str, Field(min_length=1, max_length=400, pattern=r"(?s)^.*\S.*$")]
    ] = Field(max_length=8)
    reason: str = Field(min_length=1, max_length=800)


class AuditedTextbookClaim(TextbookClaim):
    proof_audit: ProofAudit


AuditedClaim = Annotated[
    AuditedTextbookClaim | GivenClaim | CalculationClaim | GuidanceClaim | GeneralClaim,
    Field(discriminator="basis"),
]


class AssertionCheck(OrdinaryQuestionCheckV5):
    claims: list[AuditedClaim] = Field(max_length=17)


def bind_checker_schema(schema, provenance):
    """Constrain output identity at the wire; keep every local support gate."""
    try:
        if provenance["version"] != POLICY:
            raise ValueError
        rows = provenance["assertions"]
        if not isinstance(rows, list) or len(rows) > 17:
            raise ValueError
        identities = [row["claim_id"] for row in rows]
        if any(not isinstance(cid, str) or not cid.strip() for cid in identities):
            raise ValueError
        if len(identities) != len(set(identities)):
            raise ValueError
        result = deepcopy(schema)
        claims = result["properties"]["claims"]
        variants = claims["items"]["anyOf"]
        if claims["type"] != "array" or not isinstance(variants, list) or not variants:
            raise ValueError
        references = set()
        for variant in variants:
            reference = variant["$ref"]
            if (
                set(variant) != {"$ref"}
                or not reference.startswith("#/$defs/")
                or reference in references
            ):
                raise ValueError
            references.add(reference)
            definition = result["$defs"][reference.removeprefix("#/$defs/")]
            identity = definition["properties"]["claim_id"]
            if identity["type"] != "string" or "claim_id" not in definition["required"]:
                raise ValueError
            if identities:
                if "enum" in identity and not set(identities) <= set(identity["enum"]):
                    raise ValueError
                if "const" in identity and identities != [identity["const"]]:
                    raise ValueError
                identity["enum"] = list(identities)
        claims["minItems"] = claims["maxItems"] = len(identities)
        return result
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ValueError("ASSERTION_CHECK_SCHEMA_BINDING_INVALID") from exc


def submission_fields(
    settings, *, answer_mode, teaching, reading_context, provider, checker_provider=None
):
    """Freeze the new private policy only on new ordinary direct textbook requests."""
    if (
        answer_mode == "textbook"
        and provider != "mock"
        and checker_provider != "mock"
        and not reading_context
        and teaching.get("teaching_mode", "direct") == "direct"
        and teaching.get("task_type", "process_reasoning") == "process_reasoning"
        and teaching.get("turn_role") != "learner_attempt"
        and not teaching.get("practice_context")
        and not teaching.get("pending_tutor_question")
        and not teaching.get("pending_tutor_question_id")
        and getattr(settings, "chat_joint_checker_policy", None) == "typed_joint_v5"
        and getattr(settings, "chat_source_relation_policy", "off") in {None, "off"}
        and getattr(settings, "chat_checker_schema_policy", None) is None
        and getattr(settings, "chat_checker_output_policy", None) is None
        and getattr(settings, "chat_qualification_source_transport", None) is None
        and ordinary_question_without_attempt(teaching)
    ):
        return {"assertion_source_policy": POLICY}
    return {}


def eligible(request, teaching):
    policy = getattr(request, "assertion_source_policy", None)
    if policy is None:
        return False
    if policy != POLICY:
        raise ValueError("ASSERTION_SOURCE_POLICY_UNKNOWN")
    context = request.teaching_context or {}
    if not (
        request.mode == "interactive_chat"
        and request.config.provider != "mock"
        and (request.checker_config or request.config).provider != "mock"
        and request.condition == "E1"
        and request.answer_mode == "textbook"
        and request.reliability_policy == "evidence_reliability_v5"
        and request.joint_checker_policy == "typed_joint_v5"
        and request.source_relation_policy is None
        and request.checker_schema_policy is None
        and request.checker_output_policy is None
        and request.reading_context is None
        and teaching["teaching_mode"] == "direct"
        and teaching["online_check"] is True
        and context.get("task_type", "process_reasoning") == "process_reasoning"
        and ordinary_question_without_attempt(context)
        and context.get("turn_role") != "learner_attempt"
        and not context.get("practice_context")
        and not context.get("pending_tutor_question")
        and not context.get("pending_tutor_question_id")
    ):
        raise ValueError("ASSERTION_SOURCE_POLICY_INCOMPATIBLE")
    return True


def source_bank(fragments, selected_evidence=None):
    """Bind request-local aliases to exact submitted blocks, never select more text."""
    selected = None
    if selected_evidence is not None:
        selected = {row["evidence_id"]: row for row in selected_evidence}
        if len(selected) != len(selected_evidence):
            raise ValueError("ASSERTION_EVIDENCE_IDENTITY_INVALID")
        for evidence in selected.values():
            text = evidence["text"]
            if (
                not isinstance(text, str)
                or not text
                or evidence["text_hash"] != hashlib.sha256(text.encode("utf-8")).hexdigest()
            ):
                raise ValueError("ASSERTION_EVIDENCE_HASH_MISMATCH")
    result = []
    identities = set()
    for number, fragment in enumerate(fragments, 1):
        identity = fragment["fragment_id"]
        text = fragment["exact_text"]
        if identity in identities or not isinstance(text, str) or not text:
            raise ValueError("ASSERTION_SOURCE_BANK_INVALID")
        identities.add(identity)
        if selected is not None:
            evidence = selected.get(fragment["evidence_id"])
            if evidence is None or text not in evidence["text"]:
                raise ValueError("ASSERTION_SOURCE_OUTSIDE_SUBMITTED_EVIDENCE")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if fragment.get("text_hash", digest) != digest:
            raise ValueError("ASSERTION_SOURCE_HASH_MISMATCH")
        locator = {
            key: deepcopy(fragment[key])
            for key in (
                "chunk_id",
                "asset_id",
                "document_version_id",
                "processing_id",
                "source_unit_id",
                "start",
                "end",
                "chunk_start",
                "chunk_end",
                "page",
                "offset_basis",
            )
            if key in fragment
        }
        for first, last in (("start", "end"), ("chunk_start", "chunk_end")):
            if first in locator or last in locator:
                if (
                    type(locator.get(first)) is not int
                    or type(locator.get(last)) is not int
                    or locator[first] < 0
                    or locator[last] - locator[first] != len(text)
                ):
                    raise ValueError("ASSERTION_SOURCE_COORDINATES_INVALID")
        result.append(
            {
                "source_id": f"F{number:03d}",
                "fragment_id": identity,
                "evidence_id": fragment["evidence_id"],
                "exact_text": text,
                "text_sha256": digest,
                "complete_block": fragment["complete_block"],
                "source_locator": locator,
            }
        )
    return result


def _generation_bank_table(value):
    """Validate table structure before the shared inverse can collapse columns."""
    from .checker_encoding import _untable

    if isinstance(value, list):
        if any(not isinstance(row, dict) for row in value):
            raise ValueError("ASSERTION_GENERATION_TABLE_INVALID")
    elif (
        not isinstance(value, dict)
        or set(value) != {"columns", "rows"}
        or not isinstance(value["columns"], list)
        or any(not isinstance(column, str) for column in value["columns"])
        or value["columns"] != sorted(set(value["columns"]))
        or not isinstance(value["rows"], list)
        or any(
            not isinstance(row, list) or len(row) != len(value["columns"]) for row in value["rows"]
        )
    ):
        raise ValueError("ASSERTION_GENERATION_TABLE_INVALID")
    return _untable(value)


def _generation_bank_rows(bank):
    """Reuse the canonical producer's identities, hashes and coordinate checks."""
    if not isinstance(bank, list):
        raise ValueError("ASSERTION_GENERATION_BANK_INVALID")
    fragments = []
    for row in bank:
        if (
            not isinstance(row, dict)
            or set(row)
            != {
                "source_id",
                "fragment_id",
                "evidence_id",
                "exact_text",
                "text_sha256",
                "complete_block",
                "source_locator",
            }
            or not isinstance(row["source_locator"], dict)
            or not isinstance(row["fragment_id"], str)
            or not row["fragment_id"]
            or not isinstance(row["evidence_id"], str)
            or not row["evidence_id"]
            or type(row["complete_block"]) is not bool
        ):
            raise ValueError("ASSERTION_GENERATION_BANK_INVALID")
        fragments.append(
            {
                **deepcopy(row["source_locator"]),
                "fragment_id": row["fragment_id"],
                "evidence_id": row["evidence_id"],
                "exact_text": row["exact_text"],
                "text_hash": row["text_sha256"],
                "complete_block": row["complete_block"],
            }
        )
    if _canonical_hash(source_bank(fragments)) != _canonical_hash(bank):
        raise ValueError("ASSERTION_GENERATION_BANK_CHANGED")


def _generation_bank_packet(bank):
    from .checker_encoding import _table

    return {
        "ASSERTION_SOURCE_BANK": _table(
            [{**deepcopy(row), "source_locator": index} for index, row in enumerate(bank)]
        ),
        "ASSERTION_SOURCE_LOCATORS": _table([deepcopy(row["source_locator"]) for row in bank]),
        "GENERATION_INPUT_ENCODING": {
            "version": GENERATION_BANK_ENCODING,
            "instructions": GENERATION_BANK_INSTRUCTIONS,
            "original_bank_sha256": _canonical_hash(bank),
        },
    }


def encode_generation_source_bank(bank):
    """Encode all generator source fields; retain the canonical server bank."""
    _generation_bank_rows(bank)
    packet = _generation_bank_packet(bank)
    decode_generation_source_bank(packet, expected_bank=bank)
    return packet


def decode_generation_source_bank(packet, *, expected_bank=None):
    """Exact inverse for boundary checks; its checksum certifies no semantics."""
    if not isinstance(packet, dict) or set(packet) != {
        "ASSERTION_SOURCE_BANK",
        "ASSERTION_SOURCE_LOCATORS",
        "GENERATION_INPUT_ENCODING",
    }:
        raise ValueError("ASSERTION_GENERATION_ENCODING_INVALID")
    metadata = packet["GENERATION_INPUT_ENCODING"]
    if (
        not isinstance(metadata, dict)
        or set(metadata) != {"version", "instructions", "original_bank_sha256"}
        or metadata["version"] != GENERATION_BANK_ENCODING
        or metadata["instructions"] != GENERATION_BANK_INSTRUCTIONS
    ):
        raise ValueError("ASSERTION_GENERATION_ENCODING_INVALID")
    rows = _generation_bank_table(packet["ASSERTION_SOURCE_BANK"])
    locators = _generation_bank_table(packet["ASSERTION_SOURCE_LOCATORS"])
    if len(rows) != len(locators) or any(
        type(row.get("source_locator")) is not int or row["source_locator"] != index
        for index, row in enumerate(rows)
    ):
        raise ValueError("ASSERTION_GENERATION_LOCATOR_REFERENCE_INVALID")
    bank = [{**row, "source_locator": deepcopy(locators[index])} for index, row in enumerate(rows)]
    _generation_bank_rows(bank)
    if (
        metadata["original_bank_sha256"] != _canonical_hash(bank)
        or _canonical_hash(packet) != _canonical_hash(_generation_bank_packet(bank))
        or (expected_bank is not None and _canonical_hash(expected_bank) != _canonical_hash(bank))
    ):
        raise ValueError("ASSERTION_GENERATION_BANK_CHANGED")
    return bank


def compile_draft(value, fragments):
    """Render explicit assertion bindings before any check; do not infer citations."""
    import re

    draft = AssertionDraft.model_validate(value).model_dump()
    bank = {row["source_id"]: row for row in source_bank(fragments)}
    public = deepcopy(draft)
    ledger = []
    body_evidence_ids = []
    assertion_ids = set()
    for field in ("answer_text", "short_answer"):
        rows = (
            draft[field]
            if field == "answer_text"
            else ([draft[field]] if draft[field] is not None else [])
        )
        rendered_rows = []
        for number, row in enumerate(rows, 1):
            identity = row["assertion_id"]
            expected = f"{'A' if field == 'answer_text' else 'S'}{number:03d}"
            if identity != expected or identity in assertion_ids:
                raise ValueError("ASSERTION_IDENTITY_INVALID")
            assertion_ids.add(identity)
            text = row["text"]
            if text != text.strip() or not text.strip() or re.search(r"\[ev_[0-9]+\]", text):
                raise ValueError("ASSERTION_TEXT_INVALID")
            selected = row["source_ids"]
            if draft["response_type"] == "answer" and not selected:
                raise ValueError("ASSERTION_SOURCE_SELECTION_REQUIRED")
            if len(selected) != len(set(selected)):
                raise ValueError("ASSERTION_SOURCE_DUPLICATE")
            sources = []
            for source_id in selected:
                source = bank.get(source_id)
                if source is None or source["complete_block"] is not True:
                    raise ValueError("ASSERTION_SOURCE_UNKNOWN_OR_INCOMPLETE")
                sources.append(deepcopy(source))
            local_evidence = list(dict.fromkeys(source["evidence_id"] for source in sources))
            rendered = text + "".join(f" [{eid}]" for eid in local_evidence)
            # The existing extractor owns the complete assertion boundary. Multiple
            # sentences or hidden unparsed prefixes cannot share one source binding.
            extracted = response_claims({field: rendered})
            if len(extracted) != 1 or extracted[0]["text"] != rendered:
                raise ValueError("ASSERTION_COMPLETE_CLAIM_REQUIRED")
            rendered_rows.append(rendered)
            ledger.append(
                {
                    "assertion_id": identity,
                    "answer_field": field,
                    "assertion_text": text,
                    "rendered_text": rendered,
                    "sources": sources,
                }
            )
            if field == "answer_text":
                body_evidence_ids.extend(local_evidence)
            elif not set(local_evidence) <= set(body_evidence_ids):
                raise ValueError("ASSERTION_SHORT_CITATION_OUTSIDE_BODY")
        public[field] = (
            "\n\n".join(rendered_rows)
            if field == "answer_text"
            else (rendered_rows[0] if rendered_rows else None)
        )
    expected_citations = list(dict.fromkeys(body_evidence_ids))
    if draft["citations"] != expected_citations:
        raise ValueError("ASSERTION_CITATIONS_MISMATCH")
    if draft["response_type"] != "answer" and any(row["sources"] for row in ledger):
        raise ValueError("ASSERTION_NONANSWER_SOURCE_INVALID")
    # Validate unchanged public types before exposing a compiled draft downstream.
    public = TeachingDraftV5.model_validate(public).model_dump()
    claims = response_claims(public)
    if len(claims) != len(ledger):
        raise ValueError("ASSERTION_CLAIM_COVERAGE_INVALID")
    for row, claim in zip(ledger, claims):
        if row["rendered_text"] != claim["text"] or row["answer_field"] != claim["answer_field"]:
            raise ValueError("ASSERTION_CLAIM_IDENTITY_INVALID")
        row.update(
            {
                "claim_id": claim["claim_id"],
                "start": claim["start"],
                "end": claim["end"],
                "assertion_sha256": hashlib.sha256(
                    row["assertion_text"].encode("utf-8")
                ).hexdigest(),
                "evidence_ids": deepcopy(claim["evidence_ids"]),
            }
        )
    return public, {
        "version": POLICY,
        "assertions": ledger,
        "public_response_sha256": _canonical_hash(public),
        "semantic_support_certified": False,
    }


def _canonical_hash(value):
    import json

    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def checker_bindings(claims, provenance, fragments):
    """Limit each claim to its original generator-selected exact source union."""
    if provenance.get("version") != POLICY:
        raise ValueError("ASSERTION_PROVENANCE_VERSION_INVALID")
    bank = {row["source_id"]: row for row in source_bank(fragments)}
    rows = provenance["assertions"]
    if len(rows) != len(claims):
        raise ValueError("ASSERTION_CLAIM_COVERAGE_INVALID")
    result = []
    for row, claim in zip(rows, claims):
        if (
            row["claim_id"] != claim["claim_id"]
            or row["rendered_text"] != claim["text"]
            or row["answer_field"] != claim["answer_field"]
            or row["start"] != claim["start"]
            or row["end"] != claim["end"]
            or row["evidence_ids"] != claim["evidence_ids"]
            or row["assertion_sha256"]
            != hashlib.sha256(row["assertion_text"].encode("utf-8")).hexdigest()
        ):
            raise ValueError("ASSERTION_CLAIM_IDENTITY_INVALID")
        grouped = {}
        source_ids = [source["source_id"] for source in row["sources"]]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("ASSERTION_SOURCE_DUPLICATE")
        for selected in row["sources"]:
            current = bank.get(selected["source_id"])
            if current != selected:
                raise ValueError("ASSERTION_SOURCE_BINDING_CHANGED")
            grouped.setdefault(selected["evidence_id"], []).append(selected["source_id"])
        if row["rendered_text"] != row["assertion_text"] + "".join(f" [{eid}]" for eid in grouped):
            raise ValueError("ASSERTION_CLAIM_IDENTITY_INVALID")
        if list(grouped) != claim["evidence_ids"]:
            raise ValueError("ASSERTION_CITATIONS_MISMATCH")
        result.append(
            {
                "claim_id": claim["claim_id"],
                "citations": [
                    {"evidence_id": eid, "allowed_fragment_ids": ids}
                    for eid, ids in grouped.items()
                ],
            }
        )
    return result


def checker_packet(provenance):
    return {
        "version": POLICY,
        "semantic_support_certified": False,
        "assertions": [
            {
                "assertion_id": row["assertion_id"],
                "claim_id": row["claim_id"],
                "answer_field": row["answer_field"],
                "full_assertion": row["assertion_text"],
                "assertion_sha256": row["assertion_sha256"],
                "evidence_ids": deepcopy(row["evidence_ids"]),
                "selected_source_union": [
                    {
                        "fragment_id": source["source_id"],
                        "evidence_id": source["evidence_id"],
                        "exact_text": source["exact_text"],
                        "text_sha256": source["text_sha256"],
                        "source_locator": deepcopy(source["source_locator"]),
                    }
                    for source in row["sources"]
                ],
            }
            for row in provenance["assertions"]
        ],
    }


def assess_judgment(typed, provenance):
    """Validate frozen references and independent audit results, never change verdicts."""
    expected = {row["claim_id"]: row for row in provenance["assertions"]}
    returned = [row["claim_id"] for row in typed["claims"]]
    if set(returned) != set(expected) or len(returned) != len(expected):
        return [{"code": "ASSERTION_CHECK_COVERAGE_INVALID"}]
    issues = []
    for checked in typed["claims"]:
        cid = checked["claim_id"]
        target = expected[cid]
        selected = {}
        for source in target["sources"]:
            selected.setdefault(source["evidence_id"], []).append(source["source_id"])
        if checked["basis"] != "textbook":
            if selected:
                issues.append({"code": "ASSERTION_CHECK_BASIS_INVALID", "claim_id": cid})
            continue
        actual = checked["citations"]
        actual_by_evidence = {row["evidence_id"]: row["fragment_ids"] for row in actual}
        if len(actual_by_evidence) != len(actual) or actual_by_evidence != selected:
            issues.append({"code": "ASSERTION_CHECK_SOURCE_UNION_CHANGED", "claim_id": cid})
        audit = checked["proof_audit"]
        if checked["status"] != "supported" and (
            all(
                audit[field] is True
                for field in (
                    "all_predicates_entailed",
                    "actor_identity_preserved",
                    "conditions_preserved",
                    "causal_bridges_entailed",
                )
            )
            or not audit["missing_predicates"]
        ):
            issues.append({"code": "ASSERTION_CHECK_AUDIT_INCONSISTENT", "claim_id": cid})
        if checked["status"] == "supported" and (
            any(
                audit[field] is not True
                for field in (
                    "all_predicates_entailed",
                    "actor_identity_preserved",
                    "conditions_preserved",
                    "causal_bridges_entailed",
                )
            )
            or audit["missing_predicates"]
        ):
            issues.append({"code": "ASSERTION_PROOF_AUDIT_FAILED", "claim_id": cid})
    return issues


GENERATION_INSTRUCTIONS = """PRIVATE ASSERTION TRANSPORT V1:
Use the supplied teaching_assertion_draft_v1 schema. answer_text is an ordered array of assertions, not a string; short_answer is one assertion or null. This private transport replaces only the old prose/citation serialization instruction. Each row has assertion_id A001,A002,... (body) or S001 (short answer), text, and source_ids. Keep one complete sentence or compound sentence in each row and retain every predicate, actor, condition, number, relation and requested explanation. Do not put inline citation markers in text: the server renders markers from that row's explicitly selected source_ids. Copy Fxxx IDs from ASSERTION_SOURCE_BANK. Every answer assertion must have at least one explicit source_id. Select every exact block needed to support that complete assertion, including identifying antecedents and complementary causal steps; another row's sources do not support this row. A source choice is a proposal, not an approval. Do not assert an actor identity, causal bridge, direction or removed condition merely because a generic definition uses related words. Omit optional unsupported additions; retain required supported content and state genuine missing evidence precisely. citations lists the unique evidence_ids associated with BODY source_ids in first-use order. A short answer selects its own independently supporting blocks, but their evidence_ids must already occur in the body; it cannot introduce a new body citation. No source selection for a social, clarification or refusal response. All original teaching restraint and response-type rules remain. Return only complete minified JSON under the supplied private schema; never return the old string answer_text transport."""

CHECKER_INSTRUCTIONS = """IMMUTABLE ASSERTION PROOF AUDIT V1:
ASSERTION_PROOFS is the exact same assertion/source selection supplied by the generator, compiled before this check. The generator's source choices and assertion IDs certify no semantic support. Assess each complete original assertion independently from its own selected_source_union. Copy its claim_id and every selected citation/fragment reference exactly, even when its relation is irrelevant or contradictory; never substitute, drop or add a fragment. The full source bank may support requirements analysis but cannot rescue another assertion's missing proof.
Judge the union of all this assertion's selected passages. Complementary statements may establish a relation across sentences: resolve explicit pronouns and antecedents within that union, combine a stated mechanism with its stated energy source, and accept a meaning-preserving necessary inference when the selected text establishes every link. A causal account need not use the draft's exact words in one sentence. Do not reject merely because its premise and conclusion occur in different selected sentences. Conversely, a generic class definition does not identify the particular actors, and a step described for an unnamed carrier does not establish the named actor unless this same union contains its identifying bridge. A missing necessary condition, negation, quantity role or causal link remains a real defect.
For each textbook claim, return proof_audit: all_predicates_entailed, actor_identity_preserved, conditions_preserved, causal_bridges_entailed, missing_predicates, reason. Audit the complete compound assertion, including inherited referents. Set all booleans true and missing_predicates empty only when that union entails every asserted predicate; otherwise retain partial/unsupported and name the precise missing predicate. An absent causal assertion has causal_bridges_entailed=true only because no bridge is claimed, not because a missing bridge is waived. These are your independent semantic judgments, never a forced pass. Return only complete minified JSON under the supplied joint_assertion_check_v1 schema. All original body, coverage, requirement, citation, response-type and publication gates remain."""


def generation_template(template):
    """Change private serialization directives, retaining the semantic rules."""
    import re

    template = template.replace("chat_response_teaching_v5", DRAFT_SCHEMA)
    # A procedural-hint string-shape example belongs to the legacy hint route.
    template = "\n".join(
        line
        for line in template.split("\n")
        if not line.startswith("Legal JSON shape example for a procedural hint")
    )
    template = re.sub(
        r'(?:Procedural hint|Genuine refusal) shape: \{.*?"learner_attempt_evaluation":null\}',
        "",
        template,
    )
    template = re.sub(
        r"CITATION TOKEN FORMAT:.*?DIRECT SINGLE-DEFINITION SCOPE:",
        "PRIVATE CITATION FORMAT: Select each assertion's actual source_ids; the server "
        "renders its adjacent evidence markers before checking. citations contains body "
        "evidence IDs only; a short answer needs its own source_ids with evidence IDs "
        "already used in the body. DIRECT SINGLE-DEFINITION SCOPE:",
        template,
    )
    for before, after in (
        (
            "an adjacent inline [ev_NNN] marker",
            "an explicit source_ids selection on that assertion",
        ),
        (
            "The unique marker set must exactly match citations.",
            "The body's unique selected evidence IDs must exactly match citations.",
        ),
        (
            "cite exact current [ev_NNN] IDs",
            "select exact current Fxxx IDs from ASSERTION_SOURCE_BANK",
        ),
        ("own adjacent markers", "own explicit source_ids selections"),
        ("own adjacent actual [ev_NNN] markers", "own explicit source_ids selections"),
        ("with citations=[] and no markers", "with citations=[] and no source_ids"),
    ):
        template = template.replace(before, after)
    return template + "\n" + GENERATION_INSTRUCTIONS


def checker_template(template):
    """Declare the actual private checker schema without changing older templates."""
    return template.replace("joint_check_v5", CHECK_SCHEMA) + "\n" + CHECKER_INSTRUCTIONS
