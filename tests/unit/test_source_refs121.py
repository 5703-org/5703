"""Source-interface boundaries through the real offline runner, not science scores."""

from copy import deepcopy
import hashlib
import json

import pytest

from generation.qualification_v1 import ReliableQualificationSourceWire
from scripts.dev import checker_fixture_runner as runner
from test_requirement_summary_runner119 import fixture_plan, full_reply


def plan(*, extra=False, repeated=False):
    value = fixture_plan(1)
    value["source_transport"] = "source_refs_v3"
    source = value["source_bindings"]["cases"]["tiny"]
    if repeated:
        text = "Photosynthesis uses light energy and uses light energy. Carbon dioxide supplies carbon for sugar."
        update_source(source, text)
    if extra:
        evidence = deepcopy(source["evidence"][0])
        evidence.update(evidence_id="ev_002", chunk_id="c2")
        source["evidence"].append(evidence)
        source["original_mapping"]["c2"] = deepcopy(source["original_mapping"]["c1"])
        extra_text = "Photosynthesis uses light energy. The authored claim is restricted to the supplied condition."
        extra_hash = hashlib.sha256(extra_text.encode()).hexdigest()
        evidence.update(asset_id="d2", processing_id="p2", text=extra_text, text_hash=extra_hash)
        mapping = source["original_mapping"]["c2"]
        mapping.update(
            asset_id="d2",
            processing_id="p2",
            document_version_id="v2",
            chunk_text=extra_text,
            chunk_hash=extra_hash,
        )
        mapping["units"][0].update(id="u2", cleaned_text=extra_text, text_hash=extra_hash)
        mapping["spans"][0].update(unit_id="u2", end=len(extra_text), chunk_end=len(extra_text))
    return runner.prepare(value)


def update_source(source, text):
    hashed = hashlib.sha256(text.encode()).hexdigest()
    source["evidence"][0].update(text=text, text_hash=hashed)
    mapping = source["original_mapping"]["c1"]
    mapping.update(chunk_text=text, chunk_hash=hashed)
    mapping["units"][0].update(cleaned_text=text, text_hash=hashed)
    mapping["spans"][0].update(end=len(text), chunk_end=len(text))


def reply(row):
    """Author a new-wire control only from already correctly bound old fixtures."""
    packet = json.loads(row["body"]["messages"][-1]["content"])
    sources = {s["fragment_id"]: s for s in packet["SOURCE_FRAGMENTS"]}
    outer = json.loads(full_reply(row))
    value = json.loads(outer["choices"][0]["message"]["content"])

    def ref(fid, quote=None):
        source = sources[fid]
        return dict(source_id=source["source_id"], quote=quote or source["exact_text"])

    for claim in value["claims"]:
        old = claim["citations"]
        claim["citations"] = []
        for citation in old:
            for fid in citation["fragment_ids"]:
                assert citation["evidence_id"] == sources[fid]["evidence_id"]
                claim["citations"].append({**ref(fid), "relation": citation["relation"]})
        for unit in claim["units"]:
            unit["sources"] = [ref(fid) for fid in unit.pop("fragment_ids")]
    for requirement in value["requirements"]:
        old = requirement["evidence"]
        requirement["evidence"] = []
        for evidence in old:
            assert evidence["evidence_id"] == sources[evidence["fragment_id"]]["evidence_id"]
            requirement["evidence"].append(ref(evidence["fragment_id"], evidence["quote"]))
    for record in value["qualification_assessments"]:
        selected = next(c for c in value["claims"] if c["claim_id"] == record["claim_id"])[
            "citations"
        ]
        for role in ("supporting_quotes", "limiting_quotes", "revision_supporting_quotes"):
            record[role] = [
                dict(
                    source_id=next(c["source_id"] for c in selected if q["quote"] in c["quote"]),
                    quote=q["quote"],
                )
                for q in record[role]
            ]
    value["source_interface_version"] = "source_refs_v3"
    value["repair_sources"] = [ref(fid) for fid in value.pop("repair_fragment_ids")]
    return outer, value


def run(value, judgment, tmp_path):
    outer, _ = reply(value["rows"][0])
    outer["choices"][0]["message"]["content"] = json.dumps(judgment)
    return runner.run(
        value,
        transport=lambda *args: runner.Response(runner.encoded(outer)),
        output=tmp_path / "actual",
    )


def test_new_wire_removes_all_model_origin_fields_and_offsets():
    schema = ReliableQualificationSourceWire.model_json_schema()
    assert set(schema["$defs"]["SourceQuote"]["properties"]) == {"source_id", "quote"}
    assert set(schema["$defs"]["SourceCitation"]["properties"]) == {
        "source_id",
        "quote",
        "relation",
    }
    properties = schema["$defs"]["SourceUnitAssessment"]["properties"]
    assert "unit_id" in properties and "sources" in properties and "fragment_ids" not in properties
    serialized = json.dumps(schema)
    assert '"repair_fragment_ids"' not in serialized
    for field in (
        '"evidence_id"',
        '"fragment_id"',
        '"fragment_ids"',
        '"source_unit_id"',
        '"start"',
        '"end"',
    ):
        assert field not in serialized


def test_correctly_bound_full_runner_derives_owned_provenance_and_preserves_judgments(tmp_path):
    value = plan()
    _, judgment = reply(value["rows"][0])
    final = run(value, judgment, tmp_path)
    record = final["results"][0]
    assert final["status"] == "COMPLETED_ALL_UNITS" and record["technical_valid"]
    assert record["semantic_accept"] is True
    notes = record["checker"]["qualification_decision_derivative"]
    assert notes["source_interface_version"] == "source_refs_v3" and notes["provenance_derived"]
    assert notes["semantic_judgments_changed"] is False
    assert all(
        r["evidence_id"] == "ev_001" and r["start"] < r["end"]
        for r in notes["resolved_source_references"]
    )
    assert json.loads(record["checker"]["raw_text"]) == judgment


@pytest.mark.parametrize("field", ["evidence_id", "fragment_id", "source_unit_id", "start"])
def test_wrong_or_redundant_origin_field_cannot_be_ignored_or_remapped(tmp_path, field):
    value = plan()
    _, judgment = reply(value["rows"][0])
    judgment["claims"][0]["citations"][0][field] = "wrong-origin"
    final = run(value, judgment, tmp_path)
    assert final["status"] == "STOPPED_NO_RETRY" and final["results"][0]["correctness"] is None
    assert final["results"][0]["pipeline_error"]["code"] == "QUALIFICATION_CONTRACT_INVALID"
    assert json.loads(final["results"][0]["checker"]["raw_text"]) == judgment


@pytest.mark.parametrize("kind", ["duplicate_selection", "repeated_occurrence"])
def test_duplicate_quote_or_selected_identity_is_invalid_through_runner(tmp_path, kind):
    value = plan(repeated=kind == "repeated_occurrence")
    _, judgment = reply(value["rows"][0])
    if kind == "duplicate_selection":
        judgment["claims"][0]["citations"].append(deepcopy(judgment["claims"][0]["citations"][0]))
    else:
        judgment["claims"][0]["citations"][0]["quote"] = "uses light energy"
    final = run(value, judgment, tmp_path)
    assert final["status"] == "STOPPED_NO_RETRY" and final["results"][0]["correctness"] is None


@pytest.mark.parametrize(
    "role", ["citations", "unit", "supporting_quotes", "revision_supporting_quotes"]
)
def test_positive_proof_from_an_uncited_bank_source_never_borrows_scope(tmp_path, role):
    value = plan(extra=True)
    _, judgment = reply(value["rows"][0])
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    source = next(s for s in packet["SOURCE_FRAGMENTS"] if s["evidence_id"] == "ev_002")
    ref = dict(source_id=source["source_id"], quote=source["exact_text"])
    if role == "citations":
        judgment["claims"][0]["citations"][0].update(ref)
    elif role == "unit":
        judgment["claims"][0]["units"][0]["sources"] = [ref]
    elif role == "supporting_quotes":
        judgment["qualification_assessments"][0][role] = [ref]
    else:
        record = judgment["qualification_assessments"][0]
        record.update(
            context_status="needs_qualification",
            limiting_quotes=[ref],
            qualifiers=[dict(dimension="conditions", restriction="Authored condition.")],
            minimal_revision="Authored precise statement.",
            revision_supporting_quotes=[ref],
            revision_entailed=True,
            revision_context_status="clear",
        )
    final = run(value, judgment, tmp_path)
    assert final["status"] == "STOPPED_NO_RETRY" and final["results"][0]["correctness"] is None
    assert final["results"][0]["pipeline_error"]["code"] == "QUALIFICATION_CONTRACT_INVALID"


def test_duplicate_bank_quote_is_disambiguated_and_uncited_context_limitation_has_separate_role(
    tmp_path,
):
    value = plan(extra=True)
    _, judgment = reply(value["rows"][0])
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    source = next(s for s in packet["SOURCE_FRAGMENTS"] if s["evidence_id"] == "ev_002")
    judgment["qualification_assessments"][0].update(
        context_status="conflict",
        limiting_quotes=[dict(source_id=source["source_id"], quote=source["exact_text"])],
    )
    final = run(value, judgment, tmp_path)
    record = final["results"][0]
    assert record["technical_valid"] is True and record["semantic_accept"] is False
    assert final["status"] == "COMPLETED_ALL_UNITS"
    resolved = record["checker"]["qualification_assessment_raw_aliases"]["claims"][0][
        "resolved_quotes"
    ]
    assert any(q["role"] == "limiting_quotes" and q["evidence_id"] == "ev_002" for q in resolved)
    assert all(q["evidence_id"] == "ev_001" for q in resolved if q["role"] == "supporting_quotes")


def test_missing_new_version_does_not_fall_back_to_legacy_parser(tmp_path):
    value = plan()
    _, judgment = reply(value["rows"][0])
    judgment.pop("source_interface_version")
    final = run(value, judgment, tmp_path)
    assert final["status"] == "STOPPED_NO_RETRY" and final["results"][0]["correctness"] is None


def test_wrong_source_id_never_searches_another_unit_for_matching_quote(tmp_path):
    value = plan()
    _, judgment = reply(value["rows"][0])
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    original = judgment["claims"][0]["citations"][0]
    other = next(
        source
        for source in packet["SOURCE_FRAGMENTS"]
        if source["source_id"] != original["source_id"]
    )
    original["source_id"] = other["source_id"]
    final = run(value, judgment, tmp_path)
    assert final["status"] == "STOPPED_NO_RETRY" and final["results"][0]["correctness"] is None
    assert json.loads(final["results"][0]["checker"]["raw_text"]) == judgment


def test_duplicate_bank_text_allows_positive_proof_only_under_selected_opaque_origin(tmp_path):
    value = plan(extra=True)
    _, judgment = reply(value["rows"][0])
    final = run(value, judgment, tmp_path)
    assert final["results"][0]["technical_valid"] is True
    assert final["results"][0]["semantic_accept"] is True


def test_valid_contextual_restriction_from_other_supplied_evidence_is_not_positive_proof(tmp_path):
    value = plan(extra=True)
    _, judgment = reply(value["rows"][0])
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    source = next(s for s in packet["SOURCE_FRAGMENTS"] if "restricted" in s["exact_text"])
    record = judgment["qualification_assessments"][0]
    record.update(
        context_status="conflict",
        limiting_quotes=[dict(source_id=source["source_id"], quote=source["exact_text"])],
    )
    final = run(value, judgment, tmp_path)
    assert (
        final["results"][0]["technical_valid"] and final["results"][0]["semantic_accept"] is False
    )
    assert final["results"][0]["checker"]["gate_decisions"]["source_relation_accepted"] is True


def test_same_unit_can_supply_two_distinct_unique_context_quotes(tmp_path):
    value = plan()
    _, judgment = reply(value["rows"][0])
    ref = judgment["qualification_assessments"][0]["supporting_quotes"][0]
    judgment["qualification_assessments"][0]["supporting_quotes"] = [
        {**ref, "quote": "Photosynthesis"},
        {**ref, "quote": "uses light energy"},
    ]
    final = run(value, judgment, tmp_path)
    assert final["results"][0]["technical_valid"] and final["results"][0]["semantic_accept"] is True


@pytest.mark.parametrize("kind", ["valid", "wrong_origin", "uncited", "legacy_field"])
def test_repair_source_hints_use_the_same_guarded_interface_without_legacy_origin_fields(
    tmp_path, kind
):
    value = plan(extra=True)
    _, judgment = reply(value["rows"][0])
    ref = deepcopy(judgment["claims"][0]["units"][0]["sources"][0])
    if kind == "wrong_origin":
        ref["evidence_id"] = "ev_002"
    if kind == "uncited":
        packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
        source = next(s for s in packet["SOURCE_FRAGMENTS"] if s["evidence_id"] == "ev_002")
        ref = dict(source_id=source["source_id"], quote=source["exact_text"])
    judgment["repair_sources"] = [ref]
    if kind == "legacy_field":
        judgment["repair_fragment_ids"] = ["F001"]
    final = run(value, judgment, tmp_path)
    assert (final["status"] == "COMPLETED_ALL_UNITS") is (kind == "valid")


@pytest.mark.parametrize(
    "policy,transport",
    [
        (None, "source_refs_v3"),
        ("textbook_checker_schema_research_v1", "source_refs_v3"),
        (None, "unknown"),
        (None, None),
        (None, {}),
    ],
)
def test_explicit_source_interface_never_falls_back_or_reaches_a_generation_stage(
    policy, transport
):
    from generation import GenerationService
    from test_enhancement_generation import Script, answer
    from test_context_qualification_v1 import request

    adapter = Script([answer()])
    value = request(checker_schema_policy=policy, qualification_source_transport=transport)
    out = GenerationService(adapter).generate(value)
    assert not out.succeeded and adapter.calls == []


def test_prompt_has_no_obsolete_model_origin_shape():
    from pathlib import Path

    prompts = Path(__file__).parents[2] / "generation/prompts"
    text = (prompts / "qualification_joint_v3.txt").read_text()
    assert "exactly three keys: evidence_id" not in text
    assert "citations[j].fragment_ids" not in text and "repair_fragment_ids" not in text
