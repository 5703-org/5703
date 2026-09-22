"""Typed memory decisions and bounded query-conditioned learner state.

This deterministic engine never infers mastery. The v1 extractor remains separate
so frozen M2 requests and studies can retain their original policy.
"""

import hashlib
import json
import re
from datetime import datetime

WRITER_VERSION = "typed_memory_v2"
SELECTOR_VERSION = "query_conditioned_memory_v2"
TOPIC_VERSION = "science_topic_aliases_v1"
MEMORY_TOKEN_LIMIT = 768


class MemoryPreparationUnavailable(Exception):
    def __init__(self, code="MEMORY_PREPARATION_UNAVAILABLE"):
        self.code = code
        super().__init__(
            "Learning memory could not be prepared; current instructions remain available."
        )


FIELDS = {
    "detail_level": "preference",
    "explanation_order": "preference",
    "examples": "preference",
    "analogies": "preference",
    "terminology": "preference",
    "format": "preference",
    "learning_goal": "goal",
    "course": "course_context",
    "difficulty": "self_reported_observation",
    "confidence": "self_reported_observation",
    "assessment_result": "assessment_performance",
}
ALIASES = {
    "detail": "detail_level",
    "length": "detail_level",
    "verbosity": "detail_level",
    "explanation_style": "detail_level",
    "example_order": "explanation_order",
    "analogy": "analogies",
    "study_goal": "learning_goal",
    "goal": "learning_goal",
    "course_context": "course",
    "self_reported_difficulty": "difficulty",
}
TOPICS = {
    "biology": {
        "biology",
        "biological",
        "photosynthesis",
        "chloroplast",
        "calvin",
        "atp",
        "mitochondria",
        "mitochondrion",
        "osmosis",
        "diffusion",
        "dna",
        "rna",
        "gene",
        "genetics",
        "enzyme",
        "enzymes",
        "cell",
        "cells",
        "respiration",
        "ecology",
        "plant",
        "plants",
    },
    "chemistry": {
        "chemistry",
        "chemical",
        "acid",
        "base",
        "buffer",
        "buffers",
        "ph",
        "mole",
        "moles",
        "stoichiometry",
        "equilibrium",
        "enthalpy",
        "bond",
        "bonds",
        "orbital",
        "oxidation",
        "titration",
        "molarity",
        "gas",
        "pressure",
    },
    "anatomy": {
        "anatomy",
        "physiology",
        "heart",
        "artery",
        "arteries",
        "vein",
        "neuron",
        "neurons",
        "refractory",
        "muscle",
        "kidney",
        "nephron",
        "lung",
        "lungs",
        "hormone",
        "endocrine",
        "nerve",
    },
    "cellular_energy": {
        "atp",
        "mitochondria",
        "mitochondrion",
        "photosynthesis",
        "chloroplast",
        "calvin",
        "respiration",
        "glycolysis",
        "electron",
        "chemiosmosis",
    },
    "genetics": {
        "dna",
        "rna",
        "gene",
        "genes",
        "genetics",
        "transcription",
        "translation",
        "chromosome",
        "meiosis",
        "mitosis",
    },
    "acid_base": {"acid", "base", "buffer", "buffers", "ph", "titration", "hydrogen", "hydroxide"},
}
# Domain vocabulary extends beyond literal course names; these are transparent
# aliases, not a learned semantic or mastery classifier.
TOPICS["biology"].update(
    {
        "splicing",
        "exon",
        "exons",
        "operon",
        "lactose",
        "auxin",
        "angiosperm",
        "fertilization",
        "endosperm",
        "speciation",
        "fungi",
        "fungal",
        "cnidarian",
        "amniotic",
        "succession",
        "niche",
        "bacteriophage",
    }
)
TOPICS["chemistry"].update(
    {
        "isotope",
        "isotopes",
        "atomic",
        "electrolysis",
        "copper",
        "cubic",
        "crystal",
        "colligative",
        "oxidizing",
        "reducing",
        "molecular",
    }
)
TOPICS["anatomy"].update(
    {
        "epithelial",
        "connective",
        "ossification",
        "lymphatic",
        "cochlear",
        "tympanic",
        "blood",
        "hematocrit",
        "antigens",
    }
)
TEMPORARY = re.compile(
    r"\b(?:this time|for this (?:turn|answer|response)|just this once|only (?:today|this time))\b",
    re.I,
)
CORRECTION = re.compile(
    r"\b(?:actually|instead|no longer|from now on|change my|correct(?:ion)?|rather than)\b", re.I
)
DELETE = re.compile(
    r"\b(?:forget|delete|erase|remove)\b.{0,30}\b(?:my|that|saved|preference|goal|memory)\b", re.I
)
DURABLE = re.compile(
    r"\b(?:i prefer|i learn best|from now on|always|remember|my (?:goal|course)|i(?:'m| am) (?:studying|taking|revising|preparing)|i want to learn|i struggle|i find|i have difficulty|i have trouble|i don't understand|i do not understand|i feel|i am confident)\b",
    re.I,
)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def topics(text):
    terms = words(text)
    found = {name for name, aliases in TOPICS.items() if terms & aliases}
    if "cellular_energy" in found or "genetics" in found:
        found.add("biology")
    if "acid_base" in found:
        found.add("chemistry")
    return sorted(found)


def scope_name(value):
    value = " ".join(re.findall(r"[a-z0-9]+", str(value).casefold()))
    if not value or len(value) > 200:
        raise ValueError("Invalid memory scope")
    return value


def field_key(value):
    value = value.strip().casefold().replace(" ", "_")
    value = ALIASES.get(value, value)
    if value not in FIELDS:
        raise ValueError("Unrecognised memory field")
    return value


def canonical(category, field, scope):
    field = field_key(field)
    if FIELDS[field] != category:
        raise ValueError("Memory field/category mismatch")
    return digest([WRITER_VERSION, category, field, scope_name(scope)])


def eligible(text):
    return any(
        bool(DURABLE.search(clause) or DELETE.search(clause) or CORRECTION.search(clause))
        and not TEMPORARY.search(clause)
        for clause in re.findall(r"[^.!?;\n]+[.!?;]?", text)
    )


def infer_field(text):
    text = text.casefold()
    if re.search(
        r"\b(?:i\b.{0,80}\b(?:struggle|difficult|difficulty|confus|don't understand|do not understand)|my difficulty)\w*",
        text,
    ):
        return "difficulty"
    if re.search(r"\b(?:i\b.{0,50}\bconfiden|my confidence)\w*", text):
        return "confidence"
    if re.search(
        r"\b(?:my (?:learning )?goal|i want to learn|i am (?:studying|revising|preparing))\b", text
    ):
        return "learning_goal"
    if re.search(r"\b(?:my course|i am taking|i am enrolled)\b", text):
        return "course"
    if re.search(r"\b(?:analogy|analogies)\b", text):
        return "analogies"
    if re.search(
        r"(?:examples?.{0,35}(?:before|after)|(?:formulas?|equations?).{0,35}(?:first|before))",
        text,
    ):
        return "explanation_order"
    if re.search(
        r"\b(?:concise|brief|shorter|detailed|detail|short (?:answers?|explanations?)|long (?:answers?|explanations?)|simpler|simply)\b",
        text,
    ):
        return "detail_level"
    if re.search(r"\b(?:terminology|technical terms|plain language)\b", text):
        return "terminology"
    if re.search(r"\b(?:examples?|worked problems?)\b", text):
        return "examples"
    if re.search(r"\b(?:bullet|numbered|format)\b", text):
        return "format"
    if re.search(
        r"\b(?:struggle|difficulty|difficult|confus|don't understand|do not understand)\w*", text
    ):
        return "difficulty"
    if re.search(r"\bconfiden\w*", text):
        return "confidence"
    if re.search(r"\b(?:course|class|enrolled|taking)\b", text):
        return "course"
    if re.search(r"\b(?:goal|studying|revising|preparing|want to learn)\b", text):
        return "learning_goal"
    return None


def explicit_scope(text):
    match = re.search(
        r"\b(?:for|in|when (?:studying|learning))\s+(biology|chemistry|anatomy|physiology|genetics|acid.base|cellular energy)\b",
        text,
        re.I,
    )
    if match:
        return scope_name(match.group(1))
    return "global"


def deterministic_operations(text, *, current_turn=False):
    """Recognise explicit statements only; unmatched statements go to extraction."""
    if not current_turn and not eligible(text):
        return []
    output = []
    for match in re.finditer(r"[^.!?;\n]+[.!?;]?", text):
        quote = match.group().strip()
        if not quote:
            continue
        if not current_turn and TEMPORARY.search(quote):
            continue
        durable = bool(DURABLE.search(quote) or CORRECTION.search(quote) or DELETE.search(quote))
        if not durable and not (
            current_turn
            and (
                TEMPORARY.search(text)
                or re.search(r"\b(?:answer|explain|use|give|make)\b", quote, re.I)
            )
        ):
            continue
        field = infer_field(quote)
        if field is None:
            continue
        category = FIELDS[field]
        if category != "preference" and not durable:
            continue
        if category == "self_reported_observation" and not re.search(r"\b(?:I|my)\b", quote, re.I):
            continue
        scope = explicit_scope(quote)
        if category != "preference" and scope == "global":
            found = topics(quote)
            scope = found[0] if found else "global"
        output.append(
            {
                "operation": "DELETE"
                if DELETE.search(quote)
                else "UPDATE"
                if CORRECTION.search(quote)
                else "ADD",
                "category": category,
                "field_key": field,
                "scope": scope,
                "content": quote,
                "source_quote": quote,
                "expires_at": None,
            }
        )
    return output[:5]


def validate_operation(item, source):
    required = {
        "operation",
        "category",
        "field_key",
        "scope",
        "content",
        "source_quote",
        "expires_at",
    }
    if not isinstance(item, dict) or set(item) != required:
        raise ValueError("Invalid memory operation fields")
    if item["operation"] not in {"ADD", "UPDATE", "DELETE", "NO_OP"}:
        raise ValueError("Invalid memory operation")
    value = dict(item)
    value["field_key"] = field_key(item["field_key"])
    value["scope"] = scope_name(item["scope"])
    canonical(item["category"], value["field_key"], value["scope"])
    if item["category"] == "assessment_performance":
        raise ValueError("Assessments require the separately validated evidence API")
    quote = item["source_quote"]
    if not isinstance(quote, str) or not quote.strip() or quote not in source:
        raise ValueError("Memory source quote is not exact")
    if not isinstance(item["content"], str) or not 1 <= len(item["content"].strip()) <= 2000:
        raise ValueError("Invalid memory content")
    if item["content"] != quote:
        raise ValueError("Memory content must preserve the exact attributable statement")
    recognized = infer_field(quote)
    if recognized and recognized != value["field_key"]:
        raise ValueError("Memory field contradicts the explicit source statement")
    expiry = item["expires_at"]
    if expiry is not None:
        if not isinstance(expiry, str):
            raise ValueError("Memory expiry must be an explicit ISO date")
        try:
            datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Invalid memory expiry") from exc
        if expiry[:10] not in quote:
            raise ValueError("Memory expiry date is absent from its source")
    if value["scope"] != "global" and not (
        words(value["scope"]) <= words(source) or set(topics(value["scope"])) & set(topics(source))
    ):
        raise ValueError("Memory scope is absent from its source")
    if TEMPORARY.search(quote) or not (
        DURABLE.search(quote) or CORRECTION.search(quote) or DELETE.search(quote)
    ):
        raise ValueError("Memory lacks an explicit durable source")
    if item["category"] == "self_reported_observation" and not re.search(
        r"\b(?:I|my)\b", quote, re.I
    ):
        raise ValueError("Observation is not self-reported")
    if re.search(r"\b(?:mastered|mastery|proficient|diagnosed)\b", item["content"], re.I):
        raise ValueError("Unsupported learner inference")
    return value


def query_topics(question, context=None):
    found = topics(question)
    if not found and re.search(r"\b(?:it|that|this|more|again)\b", question, re.I):
        messages = (context or {}).get("recent_messages", (context or {}).get("messages", []))
        for message in reversed(messages[-6:]):
            if message.get("role") == "user":
                found = topics(message.get("content", ""))
                if found:
                    break
    return found


def learner_state(
    entries,
    question,
    profile=None,
    context=None,
    *,
    conditioned=True,
    current_message_id=None,
    character_limit=4800,
    counter=None,
):
    """Select attributable fields; M3 and M4 differ only in query selection."""
    wanted_topics = query_topics(question, context)
    query_words = words(question)
    overlay = list(
        {
            item["field_key"]: item
            for item in deterministic_operations(question, current_turn=True)
        }.values()
    )
    current_fields = {x["field_key"] for x in overlay}
    winners, excluded = {}, []
    profile_value = (profile or {}).get("profile") or {}
    for entry in entries:
        field = entry.get("field_key")
        if not field:
            # The v1 path remains intact; V2 asks for confirmation before interpreting
            # a free-form historical key as a typed current learner fact.
            excluded.append({"id": entry["id"], "reason": "legacy_requires_confirmation"})
            continue
        scope = scope_name(entry["scope"])
        relevant = (
            scope == "global"
            or bool(set(entry.get("scope_topics") or topics(scope)) & set(wanted_topics))
            or bool(words(scope) & query_words)
        )
        if conditioned and not relevant:
            excluded.append({"id": entry["id"], "reason": "scope_not_relevant"})
            continue
        if field in current_fields:
            excluded.append({"id": entry["id"], "reason": "current_instruction"})
            continue
        if entry["category"] == "confirmed_observation" or entry.get("verification") in {
            "unsupported",
            "recorded_unconfirmed",
            "legacy_unverified",
        }:
            excluded.append({"id": entry["id"], "reason": "evidence_unverified"})
            continue
        if scope == "global" and field == "detail_level" and profile_value.get("style"):
            excluded.append({"id": entry["id"], "reason": "saved_profile_default"})
            continue
        # M3 retains the same conflict rules; its candidate view lacks query filtering.
        key = field if relevant else field + ":" + scope
        if entry["category"] == "assessment_performance":
            key = field + ":" + entry["id"]
        priority = (
            1 if scope != "global" else 0,
            entry.get("source_event_sequence") or 0,
            entry.get("version", 0),
            entry["id"],
        )
        if key not in winners or priority > winners[key][0]:
            if key in winners:
                excluded.append({"id": winners[key][1]["id"], "reason": "field_superseded"})
            winners[key] = (priority, entry)
        else:
            excluded.append({"id": entry["id"], "reason": "field_superseded"})
    selected, used = [], 0
    for _, entry in sorted(winners.values(), key=lambda pair: pair[0], reverse=True):
        size = len(json.dumps(entry, ensure_ascii=False))
        if used + size > character_limit or len(selected) >= 10:
            excluded.append({"id": entry["id"], "reason": "memory_budget"})
            continue
        selected.append(entry)
        used += size
    # Prompt snapshots contain exact selected values and source references, not
    # full assessment rubrics, source messages or revision bodies.
    selected = [
        {
            k: e[k]
            for k in (
                "id",
                "version",
                "category",
                "content",
                "scope",
                "field_key",
                "verification",
                "source_message_id",
                "expires_at",
            )
            if k in e
        }
        for e in selected
    ]
    fields = [
        {
            "field_key": e.get("field_key") or "legacy",
            "scope": e["scope"],
            "verification": e.get("verification", "legacy_unverified"),
            "source": {"memory_id": e["id"], "version": e["version"]},
        }
        for e in selected
    ]
    for operation in overlay:
        fields.append(
            {
                "field_key": operation["field_key"],
                "content": operation["content"],
                "scope": operation["scope"],
                "verification": "current_user_instruction",
                "source": {"message_id": current_message_id},
                "operation": operation["operation"],
            }
        )
    payload = {
        "version": SELECTOR_VERSION if conditioned else WRITER_VERSION,
        "entries": selected,
        "fields": fields,
        "query_topics": wanted_topics,
        "query_hash": digest(question),
        "topic_policy": TOPIC_VERSION,
        "excluded": excluded[:20],
        "excluded_count": len(excluded),
        "saved_profile_defaults": {
            k: profile_value[k] for k in ("level", "style") if k in profile_value
        },
        "precedence": [
            "current_instruction",
            "relevant_scoped_preference",
            "saved_profile_default",
            "global_preference",
            "evidence_gated_observation",
        ],
    }
    count = counter.count if counter is not None else lambda value: len(value.encode("utf-8"))
    payload["token_counting"] = (
        "configured_tokenizer" if counter is not None else "utf8_byte_upper_bound"
    )
    payload["token_limit"] = MEMORY_TOKEN_LIMIT
    # Decisions remain attributable in source events; only a bounded diagnostic
    # sample belongs in the generation context.
    try:
        # Leave room for the snapshot identity and read-time revocation metadata.
        while count(json.dumps(payload, ensure_ascii=False)) > MEMORY_TOKEN_LIMIT - 96:
            if payload["excluded"]:
                payload["excluded"].pop()
            elif payload["entries"]:
                removed = payload["entries"].pop()
                payload["fields"] = [
                    f for f in payload["fields"] if f["source"].get("memory_id") != removed["id"]
                ]
                payload["excluded_count"] += 1
            elif any("content" in field for field in payload["fields"]):
                # The current question is already a first-class model input.
                # Preserve the overriding field/source identity if its duplicate
                # quotation cannot fit this optional context budget.
                for field in payload["fields"]:
                    field.pop("content", None)
            else:
                raise MemoryPreparationUnavailable("MEMORY_CONTEXT_BUDGET_EXCEEDED")
        payload["token_count"] = count(json.dumps(payload, ensure_ascii=False))
    except MemoryPreparationUnavailable:
        raise
    except Exception as exc:
        raise MemoryPreparationUnavailable() from exc
    return payload
