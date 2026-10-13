"""Opt-in structural output codec; decoded judgments still need every checker gate.

This candidate does not select evidence, establish entailment, supply judgments,
alter output limits, or replace the canonical schema and semantic validators.
The model selects fixed original-text IDs; local offsets never come from it.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass

from generation.reliability_v4 import compact_schema
from generation.source_relations_v2 import ReliableUnitCheck, scoped_syntactic_units

SCHEMA_NAME = "lossless_unit_findings_v1"
VERSION = SCHEMA_NAME
PROVIDER_SCHEMA_NAME = "joint_check_source_relations_v2_lossless_output_v1"

# A bijection, including every field in today's canonical ReliableUnitCheck.
KEYS = {
    "claims": "cs",
    "body_ok": "bo",
    "specific_help": "sh",
    "scope_ok": "so",
    "suggestions_ok": "sg",
    "evidence_display_ok": "ed",
    "cumulative_ok": "cu",
    "complete_answer": "ca",
    "coverage": "cv",
    "missing_facets": "mf",
    "limitations_explicit": "le",
    "reason": "r",
    "repair_fragment_ids": "rf",
    "attempt_evaluation_ok": "ae",
    "tutor_question_ok": "tq",
    "requirements": "rs",
    "non_repetitive_next_action": "nr",
    "claim_id": "c",
    "basis": "b",
    "status": "s",
    "citations": "ci",
    "units": "us",
    "unit_id": "u",
    "fragment_ids": "fs",
    "relation_preserved": "rp",
    "conditions_preserved": "cp",
    "evidence_id": "e",
    "relation": "rl",
    "problem_quote": "pq",
    "derivation": "d",
    "formula_basis": "fb",
    "formula_fragment_id": "ff",
    "formula_quote": "fq",
    "expression": "x",
    "inputs": "ins",
    "result": "res",
    "result_quote": "rq",
    "result_unit": "ru",
    "units_consistent": "uc",
    "formula_applicable": "fa",
    "name": "n",
    "value": "val",
    "unit": "un",
    "quote": "q",
    "origin": "o",
    "fragment_id": "f",
    "requirement_id": "k",
    "relevance": "rv",
    "sufficiency": "sf",
    "evidence": "ev",
    "response_coverage": "rc",
    "missing_information": "mi",
}
REVERSE_KEYS = {value: key for key, value in KEYS.items()}
QUOTE_REFERENCE_SPEC = {
    "representation": "fixed_original_text_id_v1",
    "whole_fragment_max_characters": 1200,
    "long_blocks": "maximal_consecutive_complete_sentences_from_each_sentence_start",
    "overlong_sentence": "no_selectable_quote_id; original_source_remains_unchanged",
    "partial_quote_fallback": False,
}


def _json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _fail(message):
    raise ValueError(message)


def _rows(value, label):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        _fail(f"Malformed {label}")
    return value


def _unique(values, label):
    if not isinstance(values, list):
        _fail(f"Malformed {label} list")
    if any(not isinstance(value, str) or not value for value in values):
        _fail(f"Malformed {label}")
    if len(set(values)) != len(values):
        _fail(f"Duplicate {label}")
    return values


def _exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        _fail(f"Missing or extra {label} keys")


def _quote_catalogue(packet):
    """Finite exact source ranges, never summarized or certified as sufficient."""
    catalogue = {}
    unavailable = []
    source_ids = {row["fragment_id"] for row in packet["SOURCE_FRAGMENTS"]}
    next_block_id = 1
    for fragment in packet["SOURCE_FRAGMENTS"]:
        text, fid = fragment["exact_text"], fragment["fragment_id"]
        if not text or fragment["complete_block"] is not True:
            continue
        if len(text) <= 1200:
            catalogue[fid] = {
                "fragment_id": fid,
                "start": 0,
                "end": len(text),
                "sentence_start": None,
                "sentence_end": None,
            }
            continue
        boundaries = [0] + [
            match.end() for match in re.finditer(r"(?<=[.!?。！？])\s+|\n[ \t]*\n", text)
        ]
        if boundaries[-1] != len(text):
            boundaries.append(len(text))
        for i, start in enumerate(boundaries[:-1]):
            if boundaries[i + 1] - start > 1200:
                unavailable.append([fid, i + 1, start, boundaries[i + 1]])
                continue
            j = i + 1
            while j + 1 < len(boundaries) and boundaries[j + 1] - start <= 1200:
                j += 1
            while f"Q{next_block_id:06d}" in source_ids:
                next_block_id += 1
            quote_id = f"Q{next_block_id:06d}"
            next_block_id += 1
            catalogue[quote_id] = {
                "fragment_id": fid,
                "start": start,
                "end": boundaries[j],
                "sentence_start": i + 1,
                "sentence_end": j,
            }
    return catalogue, unavailable


def _wire_fingerprint(packet):
    catalogue, unavailable = _quote_catalogue(packet)
    spec = {
        "quote_reference_spec": QUOTE_REFERENCE_SPEC,
        "field_aliases": KEYS,
        "quote_catalogue": catalogue,
        "unselectable_sentence_ranges": unavailable,
    }
    return hashlib.sha256(_json(spec).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OutputContext:
    """The packet is frozen by value; no mutable references to caller input."""

    packet_json: str
    digest: str
    canonical_schema_sha256: str
    wire_codec_fingerprint: str

    @property
    def packet(self):
        return json.loads(self.packet_json)

    def descriptor(self):
        packet, claims, requirements, fragments = _tables(self)
        return {
            "version": VERSION,
            "context_sha256": self.digest,
            "canonical_schema_sha256": self.canonical_schema_sha256,
            "wire_codec_fingerprint": self.wire_codec_fingerprint,
            "claim_count": len(claims),
            "requirement_count": len(requirements),
            "fragment_count": len(fragments),
            "unit_count": sum(len(row["units"]) for row in packet["SOURCE_SYNTACTIC_UNITS"]),
            "structural_projection_only": True,
            "source_entailment_certified": False,
            "original_full_validators_required": True,
        }


def _build_context(packet):
    if not isinstance(packet, dict):
        _fail("Checker packet must be an object")
    packet = deepcopy(packet)
    if packet.get("SOURCE_RELATION_POLICY") != "source_relation_contract_v2":
        _fail("The output projection requires the V2 canonical source packet")
    claims = _rows(packet.get("CLAIMS"), "claims")
    claim_ids = _unique([row.get("claim_id") for row in claims], "claim IDs")
    requirements = _rows(packet.get("CONTEXT_COVERAGE", {}).get("requirements"), "requirements")
    _unique([row.get("id") for row in requirements], "requirement IDs")
    fragments = _rows(packet.get("SOURCE_FRAGMENTS"), "fragments")
    fragment_ids = _unique([row.get("fragment_id") for row in fragments], "fragment IDs")
    by_fragment = dict(zip(fragment_ids, fragments, strict=True))
    for fragment in fragments:
        if (
            not isinstance(fragment.get("exact_text"), str)
            or not isinstance(fragment.get("evidence_id"), str)
            or type(fragment.get("complete_block")) is not bool
        ):
            _fail("Malformed immutable fragment")
    bindings = _rows(packet.get("ACTUAL_CITATION_BINDINGS"), "bindings")
    bound_ids = _unique([row.get("claim_id") for row in bindings], "binding IDs")
    if set(bound_ids) != set(claim_ids):
        _fail("Binding claim scope differs")
    for binding in bindings:
        citations = _rows(binding.get("citations"), "binding citations")
        _unique([row.get("evidence_id") for row in citations], "binding evidence IDs")
        for citation in citations:
            allowed = _unique(citation.get("allowed_fragment_ids", []), "allowed fragments")
            for fid in allowed:
                if (
                    fid not in by_fragment
                    or by_fragment[fid]["evidence_id"] != citation["evidence_id"]
                ):
                    _fail("Binding refers to a foreign evidence fragment")
    units = _rows(packet.get("SOURCE_SYNTACTIC_UNITS"), "source units")
    unit_claim_ids = _unique([row.get("claim_id") for row in units], "unit parent IDs")
    if set(unit_claim_ids) != set(claim_ids):
        _fail("Unit parent claim scope differs")
    claim_map = {row["claim_id"]: row for row in claims}
    binding_map = {row["claim_id"]: row for row in bindings}
    for parent in units:
        claim = claim_map[parent["claim_id"]]
        if (
            parent.get("full_claim") != claim["text"]
            or parent.get("actual_citation_scope") != binding_map[claim["claim_id"]]["citations"]
        ):
            _fail("Changed parent text or citation scope")
        rows = _rows(parent.get("units"), "units")
        _unique([row.get("unit_id") for row in rows], "unit IDs")
        for unit in rows:
            start, end = unit.get("start"), unit.get("end")
            if (
                type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(claim["text"])
                or unit.get("text") != claim["text"][start:end]
                or unit.get("text_hash") != hashlib.sha256(unit["text"].encode("utf-8")).hexdigest()
            ):
                _fail("Invalid original unit span or hash")
    if _json(units) != _json(scoped_syntactic_units(claims, bindings, fragments)):
        _fail("Original source-unit catalogue differs from the complete canonical input")
    frozen = _json(packet)
    schema_sha = hashlib.sha256(
        _json(compact_schema(ReliableUnitCheck)).encode("utf-8")
    ).hexdigest()
    fingerprint = _wire_fingerprint(packet)
    bound = _json(
        {
            "packet": packet,
            "canonical_schema_sha256": schema_sha,
            "wire_codec_fingerprint": fingerprint,
        }
    )
    return OutputContext(
        frozen, hashlib.sha256(bound.encode("utf-8")).hexdigest(), schema_sha, fingerprint
    )


def build_context(packet):
    try:
        return _build_context(packet)
    except ValueError:
        raise
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError("Malformed immutable checker context") from exc


def _tables(context):
    if not isinstance(context, OutputContext):
        _fail("Missing immutable output context")
    schema_sha = hashlib.sha256(
        _json(compact_schema(ReliableUnitCheck)).encode("utf-8")
    ).hexdigest()
    fingerprint = _wire_fingerprint(context.packet)
    bound = _json(
        {
            "packet": context.packet,
            "canonical_schema_sha256": schema_sha,
            "wire_codec_fingerprint": fingerprint,
        }
    )
    if (
        schema_sha != context.canonical_schema_sha256
        or fingerprint != context.wire_codec_fingerprint
        or hashlib.sha256(bound.encode("utf-8")).hexdigest() != context.digest
    ):
        _fail("Changed output context digest")
    packet = context.packet
    claims = {f"C{i:03d}": row["claim_id"] for i, row in enumerate(packet["CLAIMS"], 1)}
    requirements = {
        f"R{i:03d}": row["id"]
        for i, row in enumerate(packet["CONTEXT_COVERAGE"]["requirements"], 1)
    }
    fragments = {row["fragment_id"]: row for row in packet["SOURCE_FRAGMENTS"]}
    return packet, claims, requirements, fragments


def reference_instructions(context):
    packet, claims, requirements, _ = _tables(context)
    catalogue, unavailable = _quote_catalogue(packet)
    codebook = {
        "version": VERSION,
        "context_sha256": context.digest,
        "wire_codec_fingerprint": context.wire_codec_fingerprint,
        "field_aliases": KEYS,
        "claim_aliases": claims,
        "requirement_aliases": requirements,
        "whole_fragment_quote_ids": [
            qid for qid, row in catalogue.items() if row["sentence_start"] is None
        ],
        "long_quote_columns": [
            "quote_id",
            "fragment_id",
            "first_sentence",
            "last_sentence",
            "original_start",
            "original_end",
        ],
        "long_quote_rows": [
            [
                qid,
                row["fragment_id"],
                row["sentence_start"],
                row["sentence_end"],
                row["start"],
                row["end"],
            ]
            for qid, row in catalogue.items()
            if row["sentence_start"] is not None
        ],
        "unselectable_over_cap_sentence_ranges": unavailable,
    }
    return (
        "Return the lossless_unit_findings_v1 schema. This overrides only any "
        "input-encoding instruction to use the original output shape; the complete "
        "canonical shape is restored after strict decoding. Abbreviated fields mean the "
        "same canonical fields; supply every judgment, reason, boolean and reference "
        "yourself. Return one complete valid JSON object: array contents must be explicit "
        "JSON records, never bare ellipses, comments or placeholders for omitted records. "
        "For each textbook claim, return every unit_id from that same parent's supplied "
        "SOURCE_SYNTACTIC_UNITS exactly once in us; copy the actual IDs literally. "
        "Keep partial/unsupported unit records and their honest flags; shorten reasons, "
        "never omit records. Every factual parent must independently emit its required "
        "s (canonical status); unit statuses do not supply the parent's status. "
        "Emit c/k as the claim_aliases/requirement_aliases KEYS (Cnnn/Rnnn), not their "
        "original-ID values. Return every claim and requirement, with every required field, "
        "including honest negative judgments. Copy these exact metadata fields into the "
        "output root: " + _json({"v": VERSION, "h": context.digest})
        + ". Claim/requirement aliases identify only their original records. "
        "In requirement evidence, p is one fixed quote ID from this codebook, never "
        "coordinates. A whole-fragment ID equals f and restores that complete "
        "original SOURCE_FRAGMENTS text. Long Q IDs identify the listed consecutive "
        "original sentences; original ranges are local metadata, not numbers to "
        "calculate or emit. Explicitly select all needed passages, including their "
        "conditions and negations; no ID is a default or a proof of sufficiency. "
        "Do not infer support from a fixed ID, reuse "
        "another parent claim's citation selection, or omit a judgment. Given and "
        "calculation quotes remain literal. Use concise decisive reasons without "
        "omitting a judgment or necessary gap. Codebook: " + _json(codebook)
    )


def wire_schema(context):
    packet, claims, requirements, _ = _tables(context)
    catalogue, _ = _quote_catalogue(packet)
    canonical = compact_schema(ReliableUnitCheck)

    def rename(node):
        if isinstance(node, list):
            return [rename(item) for item in node]
        if not isinstance(node, dict):
            return node
        result = {
            key: rename(value)
            for key, value in node.items()
            if key not in {"properties", "required"}
        }
        if "properties" in node:
            unknown = set(node["properties"]) - set(KEYS)
            if unknown:
                _fail(f"Unmapped canonical schema fields: {sorted(unknown)}")
            result["properties"] = {
                KEYS[key]: rename(value) for key, value in node["properties"].items()
            }
        if "required" in node:
            result["required"] = [KEYS[key] for key in node["required"]]
        return result

    schema = rename(canonical)
    defs = schema["$defs"]
    for definition in defs.values():
        properties = definition.get("properties", {})
        if "c" in properties and claims:
            properties["c"] = {"type": "string", "enum": list(claims)}
        if "k" in properties and requirements:
            properties["k"] = {"type": "string", "enum": list(requirements)}
    quote = defs["RequirementEvidence"]["properties"].pop("q")
    defs["RequirementEvidence"]["properties"]["p"] = {
        "type": "string",
        "description": "One fixed original-text ID in the codebook, owned by the same f; "
        f"decoded quote length {quote['minLength']}..{quote['maxLength']}.",
    }
    if catalogue:
        defs["RequirementEvidence"]["properties"]["p"]["enum"] = list(catalogue)
    defs["RequirementEvidence"]["required"] = [
        "p" if key == "q" else key for key in defs["RequirementEvidence"]["required"]
    ]
    schema["properties"].update(
        {
            "v": {"type": "string", "const": VERSION},
            "h": {"type": "string", "const": context.digest},
        }
    )
    schema["required"] += ["v", "h"]
    # The canonical fields and constraints are otherwise unchanged. Empty aliases
    # are legal only for genuinely empty request arrays, not fabricated records.
    return schema


def _walk(value, *, encoding):
    mapping = KEYS if encoding else REVERSE_KEYS
    if isinstance(value, list):
        return [_walk(item, encoding=encoding) for item in value]
    if not isinstance(value, dict):
        return value
    if set(value) - set(mapping):
        _fail("Unknown full or projected field key")
    return {mapping[key]: _walk(item, encoding=encoding) for key, item in value.items()}


def _validate_original_fields(full, context):
    """Structural contract only: negative judgments remain negative judgments."""
    canonical_schema = compact_schema(ReliableUnitCheck)
    _exact_keys(full, canonical_schema["properties"], "canonical root")
    # Pydantic must receive actual model fields: no defaults may fill missing ones.
    defs = canonical_schema["$defs"]

    def require_fields(value, schema):
        if "$ref" in schema:
            return require_fields(value, defs[schema["$ref"].split("/")[-1]])
        if "anyOf" in schema:
            if isinstance(value, dict) and "basis" in value:
                candidates = [
                    part
                    for part in schema["anyOf"]
                    if "$ref" in part
                    and value["basis"]
                    in (
                        [defs[part["$ref"].split("/")[-1]]["properties"]["basis"].get("const")]
                        + defs[part["$ref"].split("/")[-1]]["properties"]["basis"].get("enum", [])
                    )
                ]
                if len(candidates) != 1:
                    _fail("Unknown or ambiguous canonical claim basis")
                return require_fields(value, candidates[0])
            return  # primitive string/null union, checked strictly by Pydantic
        if schema.get("type") == "object":
            _exact_keys(value, schema["properties"], "canonical object")
            for key, item in value.items():
                require_fields(item, schema["properties"][key])
        elif schema.get("type") == "array":
            if not isinstance(value, list):
                _fail("Canonical array is not a list")
            for item in value:
                require_fields(item, schema["items"])

    require_fields(full, canonical_schema)
    ReliableUnitCheck.model_validate(full, strict=True)
    packet, aliases, requirement_aliases, fragments = _tables(context)
    rows = full["claims"]
    ids = _unique([row["claim_id"] for row in rows], "output claim IDs")
    if set(ids) != set(aliases.values()):
        _fail("Missing, unknown or stale output claim")
    req_ids = _unique(
        [row["requirement_id"] for row in full["requirements"]],
        "output requirement IDs",
    )
    if set(req_ids) != set(requirement_aliases.values()):
        _fail("Missing, unknown or stale output requirement")
    bindings = {
        row["claim_id"]: {
            c["evidence_id"]: set(c["allowed_fragment_ids"]) for c in row["citations"]
        }
        for row in packet["ACTUAL_CITATION_BINDINGS"]
    }
    units = {
        row["claim_id"]: {unit["unit_id"] for unit in row["units"]}
        for row in packet["SOURCE_SYNTACTIC_UNITS"]
    }
    for row in rows:
        citations = row.get("citations", [])
        evidence_ids = _unique([c["evidence_id"] for c in citations], "citation evidence IDs")
        own = bindings[row["claim_id"]]
        if citations and set(evidence_ids) != set(own):
            _fail("Missing or foreign parent citation assessment")
        if row["basis"] in {"textbook", "derived_calculation"} and set(evidence_ids) != set(own):
            _fail("Missing parent citation assessment")
        selected = set()
        for citation in citations:
            fids = _unique(citation["fragment_ids"], "citation fragment IDs")
            if not set(fids) <= own.get(citation["evidence_id"], set()):
                _fail("Foreign parent citation fragment")
            selected.update(fids)
        if "units" in row:
            actual = _unique([u["unit_id"] for u in row["units"]], "output unit IDs")
            if set(actual) != units[row["claim_id"]]:
                _fail("Missing, duplicate or foreign parent unit")
            for unit in row["units"]:
                fids = _unique(unit["fragment_ids"], "unit fragment IDs")
                if not set(fids) <= selected:
                    _fail("Unit evidence was not selected by its own parent")
                if any(not fragments[fid]["complete_block"] for fid in fids):
                    _fail("Unit selects an incomplete source fragment")
        if "derivation" in row:
            derivation = row["derivation"]
            references = [(derivation["formula_basis"], derivation["formula_fragment_id"])]
            references += [
                (value["origin"], value["fragment_id"]) for value in derivation["inputs"]
            ]
            for basis, fid in references:
                if basis == "textbook" and fid is not None and fid not in selected:
                    _fail("Calculation refers to a source not selected by its own parent")
                if basis == "problem_input" and fid is not None:
                    _fail("Learner calculation input has a source fragment reference")
    for requirement in full["requirements"]:
        pointers = []
        for evidence in requirement["evidence"]:
            fid = evidence["fragment_id"]
            if (
                fid not in fragments
                or fragments[fid]["evidence_id"] != evidence["evidence_id"]
                or not fragments[fid]["complete_block"]
            ):
                _fail("Requirement selects a foreign or incomplete source fragment")
            quote = evidence["quote"]
            start = fragments[fid]["exact_text"].find(quote)
            if start < 0:
                _fail("Requirement quote differs from original fragment")
            pointers.append((fid, start, start + len(quote)))
        if len(set(pointers)) != len(pointers):
            _fail("Duplicate requirement span pointer")
    repairs = _unique(full["repair_fragment_ids"], "repair fragment IDs")
    if not set(repairs) <= set(fragments):
        _fail("Unknown repair fragment")
    return full


def encode_findings(full, context):
    """Offline roundtrip utility, not a source of model verdicts."""
    full = deepcopy(full)
    _validate_original_fields(full, context)
    _, aliases, requirements, fragments = _tables(context)
    catalogue, _ = _quote_catalogue(context.packet)
    reverse_claims = {original: alias for alias, original in aliases.items()}
    reverse_requirements = {original: alias for alias, original in requirements.items()}
    projected = _walk(full, encoding=True)
    for claim in projected["cs"]:
        claim["c"] = reverse_claims[claim["c"]]
    for requirement in projected["rs"]:
        requirement["k"] = reverse_requirements[requirement["k"]]
        for evidence in requirement["ev"]:
            quote = evidence.pop("q")
            candidates = [
                qid
                for qid, row in catalogue.items()
                if row["fragment_id"] == evidence["f"]
                and fragments[evidence["f"]]["exact_text"][row["start"] : row["end"]] == quote
            ]
            if not candidates:
                _fail("Exact canonical quote is not represented by a fixed ID; no widening allowed")
            evidence["p"] = candidates[0]
    projected.update(v=VERSION, h=context.digest)
    return projected


def _hydrate_findings(projected, context):
    """Decode structural transport only; callers must run original validators."""
    if not isinstance(projected, dict):
        _fail("Projected checker output must be an object")
    projected = deepcopy(projected)
    _, aliases, requirements, fragments = _tables(context)
    catalogue, _ = _quote_catalogue(context.packet)
    if projected.pop("v", None) != VERSION or projected.pop("h", None) != context.digest:
        _fail("Missing, unknown or stale projection metadata")
    for claim in _rows(projected.get("cs"), "projected claims"):
        if claim.get("c") not in aliases:
            _fail("Unknown claim alias")
        claim["c"] = aliases[claim["c"]]
    for requirement in _rows(projected.get("rs"), "projected requirements"):
        if requirement.get("k") not in requirements:
            _fail("Unknown requirement alias")
        requirement["k"] = requirements[requirement["k"]]
        for evidence in _rows(requirement.get("ev"), "projected requirement evidence"):
            _exact_keys(evidence, {"e", "f", "p"}, "projected requirement evidence")
            fid, quote_id = evidence["f"], evidence["p"]
            if fid not in fragments or fragments[fid]["evidence_id"] != evidence["e"]:
                _fail("Foreign requirement evidence pointer")
            if not isinstance(quote_id, str) or quote_id not in catalogue:
                _fail("Unknown or malformed fixed quote ID")
            reference = catalogue[quote_id]
            if reference["fragment_id"] != fid:
                _fail("Fixed quote ID belongs to another fragment")
            start, end = reference["start"], reference["end"]
            text = fragments[fid]["exact_text"]
            if not 0 <= start < end <= len(text) or end - start > 1200:
                _fail("Requirement span is empty, out of bounds or exceeds original quote cap")
            quote = text[start:end]
            evidence.pop("p")
            evidence["q"] = quote
    full = _walk(projected, encoding=False)
    return _validate_original_fields(full, context)


def hydrate_findings(projected, context):
    """Fail closed on malformed transport, with no recovery or field defaults."""
    try:
        return _hydrate_findings(projected, context)
    except ValueError:
        raise
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError("Malformed lossless checker output projection") from exc


def canonical(value):
    return _json(value)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


encode_full = encode_findings
decode = hydrate_findings


def validate_request(request, *, research_unchecked=False):
    """Explicit, default-off, ordinary enhanced V2 lane; no route mutation."""
    if getattr(request, "checker_output_policy", None) is None:
        return
    try:
        from generation.attempt_evaluation_contract_v1 import (
            ordinary_question_without_attempt,
        )
        from generation.openrouter_routes import resolve
        from generation.providers import checker_transport_enabled

        config = request.checker_config or request.config
        route = resolve(config)
        if (
            request.checker_output_policy != VERSION
            or research_unchecked
            or request.enhancement_version is None
            or request.mode != "interactive_chat"
            or request.condition != "E1"
            or request.answer_mode != "textbook"
            or request.source_relation_policy != "source_relation_contract_v2"
            or request.reliability_policy != "evidence_reliability_v5"
            or request.joint_checker_policy != "typed_joint_v5"
            or getattr(request, "checker_schema_policy", None) is not None
            or not ordinary_question_without_attempt(request.teaching_context)
            or config.structured_output_mode not in {"json_schema", "json_object"}
            or checker_transport_enabled(config)
            or (
                route is not None
                and route.schema_transport is not None
                and config.structured_output_mode == "json_schema"
            )
        ):
            _fail("CHECKER_OUTPUT_POLICY_INCOMPATIBLE")
    except ValueError:
        raise
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError("CHECKER_OUTPUT_POLICY_INCOMPATIBLE") from exc


@dataclass(frozen=True)
class PreparedOutput:
    messages: list[dict]
    schema: dict
    context: OutputContext


def prepare(messages, schema):
    """Pure provider compiler; schema/payload accounting uses this same result."""
    if schema != compact_schema(ReliableUnitCheck):
        _fail("LOSSLESS_OUTPUT_CANONICAL_V2_SCHEMA_CHANGED")
    try:
        from generation import checker_encoding, checker_encoding_v2
        from generation.attempt_evaluation_contract_v1 import (
            ordinary_question_without_attempt,
        )
        from generation.parser import strict_json

        prepared_messages = deepcopy(messages)
        if (
            not isinstance(prepared_messages, list)
            or not prepared_messages
            or any(not isinstance(row, dict) for row in prepared_messages)
        ):
            _fail("LOSSLESS_OUTPUT_CHECKER_PACKET_MISSING")
        packet_keys = {
            "CHECKER_INPUT_ENCODING",
            "SOURCE_RELATION_POLICY",
            "CLAIMS",
            "ACTUAL_CITATION_BINDINGS",
            "SOURCE_SYNTACTIC_UNITS",
            "SOURCE_FRAGMENTS",
            "SOURCE_FRAGMENT_TABLE",
            "CONTEXT_COVERAGE",
        }
        packets = []
        for row in prepared_messages:
            if row.get("role") != "user":
                continue
            content = row.get("content")
            if not isinstance(content, str):
                _fail("LOSSLESS_OUTPUT_CHECKER_PACKET_MISSING")
            has_packet_marker = any(re.search(rf'"{key}"\s*:', content) for key in packet_keys)
            if not content.lstrip().startswith("{") and not has_packet_marker:
                continue
            try:
                candidate = strict_json(content)
            except ValueError as exc:
                raise ValueError("LOSSLESS_OUTPUT_BAD_PACKET_USER_MESSAGE") from exc
            if packet_keys.intersection(candidate):
                packets.append(candidate)
            elif has_packet_marker:
                _fail("LOSSLESS_OUTPUT_BAD_PACKET_USER_MESSAGE")
        if not packets:
            _fail("LOSSLESS_OUTPUT_CHECKER_PACKET_MISSING")
        if len(packets) != 1:
            _fail("LOSSLESS_OUTPUT_CHECKER_PACKET_AMBIGUOUS")
        packet = packets[0]
        metadata = packet.get("CHECKER_INPUT_ENCODING")
        if metadata is not None:
            if not isinstance(metadata, dict):
                _fail("LOSSLESS_OUTPUT_BAD_INPUT_ENCODING")
            version = metadata.get("version")
            if version == checker_encoding.VERSION:
                original = packet
                packet = checker_encoding.decode(packet)
                if checker_encoding.encode(packet) != original:
                    _fail("LOSSLESS_OUTPUT_INPUT_ROUNDTRIP_MISMATCH")
            elif version == checker_encoding_v2.VERSION:
                packet = checker_encoding_v2.decode(packet)
            else:
                _fail("LOSSLESS_OUTPUT_UNKNOWN_INPUT_ENCODING")
        elif "SOURCE_FRAGMENT_TABLE" in packet:
            table = packet.pop("SOURCE_FRAGMENT_TABLE")
            if (
                not isinstance(table, dict)
                or set(table) != {"columns", "rows"}
                or table["columns"]
                != [
                    "fragment_id",
                    "evidence_id",
                    "block_kind",
                    "complete_block",
                    "exact_text",
                ]
            ):
                _fail("LOSSLESS_OUTPUT_BAD_FRAGMENT_TABLE")
            packet["SOURCE_FRAGMENTS"] = [
                dict(zip(table["columns"], row, strict=True)) for row in table["rows"]
            ]
        if (
            packet.get("answer_mode") != "textbook"
            or packet.get("TUTOR_QUESTION") is not None
            or not ordinary_question_without_attempt(
                packet.get("LEARNER_TURN"), packet.get("ATTEMPT_EVALUATION")
            )
        ):
            _fail("LOSSLESS_OUTPUT_REVISION_OUTSIDE_SCOPE")
        context = build_context(packet)
        instructions = reference_instructions(context)
        system = next((row for row in prepared_messages if row.get("role") == "system"), None)
        if system is None or not isinstance(system.get("content"), str):
            _fail("LOSSLESS_OUTPUT_SYSTEM_INSTRUCTIONS_MISSING")
        system["content"] += "\n\n" + instructions
        return PreparedOutput(prepared_messages, wire_schema(context), context)
    except ValueError:
        raise
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError("Malformed lossless checker output prepare request") from exc
