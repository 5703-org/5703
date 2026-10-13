"""Actual-claim checks plus separately assessed question-level sufficiency."""

from typing import Literal
import hashlib
import re
from pydantic import Field

from .reliability_v3 import Strict
from .reliability_v4 import ReliableCheckV4, TeachingDraftV4, coverage_context as legacy_coverage
from .reliability_v4 import protected_claims as legacy_protected_claims

VERSION = "evidence_reliability_v5"


def pessimistic_body_contract_issues(judgment):
    """Recheck a negative aggregate verdict with no named factual defect.

    This is a contract diagnostic, not a support override. A fresh judgment of
    the unchanged draft must either identify the defective claim or confirm
    body support before publication can proceed.
    """
    factual = [claim for claim in judgment["claims"] if claim["factual"]]
    if (
        judgment["body_ok"]
        or not factual
        or any(claim["status"] != "supported" for claim in factual)
    ):
        return []
    return [
        {
            "code": "BODY_REJECTED_WITH_ALL_FACTS_SUPPORTED",
            "claim_ids": [claim["claim_id"] for claim in factual],
            "feedback_version": "pessimistic_body_contract_v1",
            "route": "unchanged_draft_checker_recheck",
            "publication_override": False,
        }
    ]


def response_claims(response):
    """Keep unchanged factual spans identifiable when neighboring claims are repaired."""
    from .joint_policy import response_claims as extract

    rows = extract(response)
    occurrences: dict[str, int] = {}
    for row in rows:
        factual_text = re.sub(r"\s*\[ev_\d{3,}\]", "", row["text"]).strip()
        identity = hashlib.sha256((row["answer_field"] + "\0" + factual_text).encode()).hexdigest()[
            :24
        ]
        occurrences[identity] = occurrences.get(identity, 0) + 1
        row["claim_id"] = f"claim_{identity}_{occurrences[identity]}"
    return rows


def protected_claims(claims, judgment, issues):
    protected = legacy_protected_claims(claims, judgment, issues)
    if judgment.get("non_repetitive_next_action") is False:
        factual = {row["claim_id"] for row in judgment["claims"] if row["factual"]}
        protected = [row for row in protected if row["claim_id"] in factual]
    return protected


class RequirementEvidence(Strict):
    evidence_id: str
    fragment_id: str
    quote: str = Field(min_length=1, max_length=1200)


class RequirementCheck(Strict):
    requirement_id: str
    relevance: Literal["related", "unrelated"]
    sufficiency: Literal["sufficient", "partial", "absent", "conflicting", "not_applicable"]
    evidence: list[RequirementEvidence] = Field(max_length=8)
    conditions_preserved: bool
    response_coverage: Literal[
        "covered", "partial", "not_addressed", "deferred_for_hint", "limitation"
    ]
    missing_information: str = Field(max_length=1000)
    reason: str = Field(min_length=1, max_length=1200)


class ReliableCheckV5(ReliableCheckV4):
    requirements: list[RequirementCheck] = Field(max_length=8)
    non_repetitive_next_action: bool


class OrdinaryQuestionCheckV5(ReliableCheckV5):
    """Full V5 with explicit inapplicability only for a server-bound question."""

    attempt_evaluation_ok: bool | Literal["not_applicable"]  # type: ignore[assignment]


class AttemptEvaluationV5(Strict):
    status: Literal["correct", "incorrect", "partial", "unclear", "unrelated"]
    feedback: str = Field(min_length=1, max_length=2000)


class TeachingDraftV5(TeachingDraftV4):
    learner_attempt_evaluation: AttemptEvaluationV5 | None = None  # type: ignore[assignment]


def coverage_context(report):
    compact = legacy_coverage(report)
    source = {
        r["id"]: r
        for r in (report["packed_coverage"] or report["candidate_coverage"])["requirements"]
    }
    for row in compact["requirements"]:
        point = source[row["id"]]
        row.update(
            {
                key: point[key]
                for key in ("intent", "objects", "relation", "conditions")
                if key in point
            }
        )
    compact["semantic_evaluation_required"] = True
    return compact


def assess_requirements(judgment, coverage, fragments, *, answer_mode, teaching_mode):
    """Check assessment identities/quotes and enforce honest partial publication.

    Exact matching validates provenance, never entailment. The model remains the
    author of semantic judgments, distinct from independent evaluation labels.
    """
    expected = {r["id"] for r in coverage["requirements"]}
    rows = judgment["requirements"]
    returned = [r["requirement_id"] for r in rows]
    contract, defects = [], []
    if len(returned) != len(expected) or set(returned) != expected:
        contract.append({"code": "REQUIREMENT_IDENTITY_MISMATCH"})
    available = {f["fragment_id"]: f for f in fragments}
    for row in rows:
        rid = row["requirement_id"]
        for support in row["evidence"]:
            fragment = available.get(support["fragment_id"])
            if (
                not fragment
                or fragment["evidence_id"] != support["evidence_id"]
                or support["quote"] not in fragment["exact_text"]
                or not fragment["complete_block"]
            ):
                contract.append({"code": "REQUIREMENT_SOURCE_QUOTE_INVALID", "requirement_id": rid})
        if answer_mode == "general_knowledge":
            if row["sufficiency"] != "not_applicable" or row["evidence"]:
                contract.append(
                    {"code": "GENERAL_REQUIREMENT_TEXTBOOK_CERTIFICATION", "requirement_id": rid}
                )
        elif row["sufficiency"] == "not_applicable":
            contract.append({"code": "TEXTBOOK_REQUIREMENT_UNASSESSED", "requirement_id": rid})
        elif row["sufficiency"] in {"sufficient", "partial", "conflicting"} and not row["evidence"]:
            contract.append({"code": "REQUIREMENT_EVIDENCE_MISSING", "requirement_id": rid})
        if row["sufficiency"] == "sufficient" and (
            row["relevance"] != "related" or row["missing_information"]
        ):
            contract.append(
                {"code": "REQUIREMENT_SUFFICIENCY_CONTRADICTION", "requirement_id": rid}
            )
        if not row["conditions_preserved"]:
            defects.append({"code": "REQUIREMENT_CONDITION_LOST", "requirement_id": rid})
        if teaching_mode == "direct":
            if row["response_coverage"] in {"not_addressed", "deferred_for_hint"}:
                defects.append({"code": "REQUIRED_CONTENT_OMITTED", "requirement_id": rid})
            if row["sufficiency"] == "sufficient" and row["response_coverage"] != "covered":
                defects.append({"code": "SUFFICIENT_CONTEXT_UNDERUSED", "requirement_id": rid})
        if row["sufficiency"] in {"partial", "absent", "conflicting"}:
            if not row["missing_information"]:
                contract.append({"code": "REQUIREMENT_GAP_UNSPECIFIED", "requirement_id": rid})
            if row["response_coverage"] == "covered":
                defects.append(
                    {"code": "INSUFFICIENT_CONTEXT_FULL_COVERAGE", "requirement_id": rid}
                )
            if (
                row["response_coverage"] != "deferred_for_hint"
                and not judgment["limitations_explicit"]
            ):
                defects.append({"code": "REQUIREMENT_LIMITATION_MISSING", "requirement_id": rid})
    if teaching_mode == "hint" and not judgment["non_repetitive_next_action"]:
        defects.append({"code": "TUTOR_ACTION_REPEATS_DISCLOSED_ANSWER"})
    statuses = {r["sufficiency"] for r in rows}
    if answer_mode == "textbook" and teaching_mode == "direct" and rows:
        has_named_gap = any(
            row["sufficiency"] in {"partial", "absent", "conflicting"} for row in rows
        )
        if judgment["coverage"] == "full" and has_named_gap:
            contract.append({"code": "FULL_COVERAGE_WITH_REQUIREMENT_GAP"})
    overall = (
        "not_applicable"
        if answer_mode == "general_knowledge"
        else "sufficient"
        if statuses == {"sufficient"}
        else "conflicting"
        if "conflicting" in statuses
        else "absent"
        if statuses == {"absent"}
        else "partial"
    )
    return (
        contract,
        defects,
        {
            "version": "semantic_requirements_v1",
            "method": "online_checker_model",
            "status": overall,
            "requirements": rows,
            "human_rating": None,
            "independent_evaluation": False,
        },
    )


"""Narrow negative identifier consistency; never certify source entailment."""

def evaluate_technical_entity_bindings(typed, claims, bindings, fragments):
    """Flag a selected-source near-name collision, without rewriting judgments.

    The caller must first validate schema and actual citation identities. This
    detects only ASCII uppercase technical-looking identifiers (3..16 chars,
    at least three letters). It intentionally makes no positive support claim.
    Selected literal aliases clear this diagnostic; unexpressed semantic aliases
    and full names remain outside this lexical rule's guarantees.
    """
    import re

    pattern = re.compile(r"(?<![A-Za-z0-9_])[A-Z][A-Z0-9]{2,15}(?![A-Za-z0-9_])")

    def symbols(text):
        return {
            match.group() for match in pattern.finditer(text)
            if sum('A' <= char <= 'Z' for char in match.group()) >= 3
        }

    def one_edit(first, second):
        if first == second or abs(len(first) - len(second)) > 1:
            return False
        if len(first) == len(second):
            return sum(a != b for a, b in zip(first, second)) == 1
        short, long = (first, second) if len(first) < len(second) else (second, first)
        index = 0
        while index < len(short) and short[index] == long[index]:
            index += 1
        return short[index:] == long[index + 1:]

    def same_proposition_slot(claim_text, source_text, target, nearby):
        # A neighbouring identifier in another role or a full-name paraphrase
        # cannot trigger this narrow copied-proposition consistency check.
        def words(text):
            text = re.sub(r"\[ev_\d{3,}\]", "", text)
            return [word.lower() for word in re.findall(r"[A-Za-z0-9_]+", text)]
        claimed, supplied = words(claim_text), words(source_text)
        if len(claimed) < 4 or claimed.count(target.lower()) != 1:
            return False
        expected = [nearby.lower() if word == target.lower() else word for word in claimed]
        return any(supplied[start:start + len(expected)] == expected
                   for start in range(len(supplied) - len(expected) + 1))

    actual = {row['claim_id']: row for row in claims}
    bound = {row['claim_id']: row for row in bindings}
    source = {row['fragment_id']: row for row in fragments}
    rows = typed['claims']
    if (len(actual) != len(claims) or len(bound) != len(bindings)
            or len(source) != len(fragments)
            or {row['claim_id'] for row in rows} != set(actual)
            or len(rows) != len(actual) or set(bound) != set(actual)):
        return []  # Existing identity validation owns these failures.
    issues = []
    for row in rows:
        if row['basis'] != 'textbook' or row['status'] != 'supported':
            continue
        cid = row['claim_id']
        allowed = {item['evidence_id']: set(item['allowed_fragment_ids'])
                   for item in bound[cid]['citations']}
        selected = {}
        for citation in row['citations']:
            if citation['relation'] != 'supporting':
                continue
            for fid in citation['fragment_ids']:
                fragment = source.get(fid)
                if (fragment is not None
                        and fid in allowed.get(citation['evidence_id'], set())
                        and fragment['evidence_id'] == citation['evidence_id']):
                    selected[fid] = fragment
        source_symbols = set().union(*(symbols(f['exact_text']) for f in selected.values()))
        # A model reason cannot supply an identifier absent from selected source text.
        missing = symbols(actual[cid]['text']) - source_symbols
        for target in sorted(missing):
            nearby = sorted(s for s in source_symbols
                            if one_edit(target, s) and any(
                                same_proposition_slot(actual[cid]['text'], f['exact_text'], target, s)
                                for f in selected.values()))
            if nearby:
                issues.append({
                    'code': 'UNRESOLVED_TECHNICAL_ENTITY_COLLISION', 'claim_id': cid,
                    'claimed_identifier': target, 'source_identifiers': nearby,
                    # Preserve the legacy consumer key; it names selected source IDs, not reason text.
                    'reason_source_identifiers': nearby,
                    'selected_fragment_ids': sorted(fid for fid, f in selected.items()
                                                    if symbols(f['exact_text']) & set(nearby)),
                    'reason': 'The claimed identifier is absent from its selected supporting union; a model reason cannot establish a source alias. A selected source supplies the same proposition with a one-edit different identifier in that slot. The model reason cannot exempt this source-binding conflict. Resolve this binding before publication; this is not a scientific falsehood verdict or an entailment certificate.',
                    'source_entailment_certified': False, 'publication_override': False,
                })
    return issues
