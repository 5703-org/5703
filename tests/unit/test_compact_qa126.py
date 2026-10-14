"""Compact citation coverage and transport failures through the full isolated runner."""

import hashlib
import json

import pytest

from scripts.dev import checker_fixture_runner as runner
from test_source_refs121 import plan, update_source


def positive(packet):
    selected = {key:group["allowed_sources"][0] for key,group in packet["citation_groups"].items()}
    quote_by_source = {row[1]:row[0] for row in reversed(packet["quote_pointers"]) if row[3]-row[2]<=600}
    claims = {}
    for key,claim in packet["claims"].items():
        numbers = [selected[g] for g,value in packet["citation_groups"].items() if value["claim"]==key]
        claims[key] = dict(d="S",u={u["unit_id"]:dict(d="S",f="RC",s=numbers) for u in claim["units"]},
                           k="OK",p=[quote_by_source[numbers[0]]],l=[])
    return dict(version="ordinary_qa_compact_v2",groups={g:dict(d="S",s=[n]) for g,n in selected.items()},
                claims=claims,requirements={key:dict(r="R",s="S",c=True,d="F",p=[quote_by_source[next(iter(selected.values()))]],g="",o="")
                    for key in packet["requirements"]},limits=False,answer_only=True)


def prepared(extra=False):
    value = plan(extra=extra)
    value["source_transport"] = "ordinary_qa_compact_v2"
    value = runner.prepare(value)
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    return value,packet,positive(packet)


def execute(value,verdict,path,*,length=False):
    outer = dict(choices=[dict(finish_reason="length" if length else "stop",message=dict(content=json.dumps(verdict)[:-5] if length else json.dumps(verdict)))],
                 usage=dict(prompt_tokens=1,completion_tokens=4096 if length else 1,total_tokens=4097 if length else 2))
    raw = runner.encoded(outer)
    final = runner.run(value,transport=lambda *args:runner.Response(raw),output=path)
    return final,raw


def test_every_actual_group_is_pre_enumerated_required_once_and_full_runner_accepts(tmp_path):
    value,packet,verdict = prepared()
    system = value["rows"][0]["body"]["messages"][0]["content"]
    schema = json.loads(system.split("Match this JSON schema:",1)[1].strip())
    assert set(schema["$defs"]["CitationGroups"]["required"])==set(packet["citation_groups"])
    assert schema["$defs"]["CitationGroups"]["additionalProperties"] is False
    assert '"reason"' not in system and '"quote"' not in system and '"source_id"' not in json.dumps(schema)
    final,_ = execute(value,verdict,tmp_path/"actual")
    assert final["results"][0]["technical_valid"] and final["results"][0]["semantic_accept"] is True
    assert final["results"][0]["checker"]["qualification_decision_derivative"]["citation_group_coverage"]=="complete"


@pytest.mark.parametrize("kind",["missing","unknown","extra"])
def test_missing_or_unassessed_group_is_incomplete_verification_never_false_rejection(tmp_path,kind):
    value,_,verdict = prepared()
    if kind=="missing":
        del verdict["groups"]["G1"]
    elif kind=="unknown":
        verdict["groups"]["G1"] = dict(d="U",s=[])
    else:
        verdict["groups"]["G99"] = dict(d="I",s=[])
    final,_ = execute(value,verdict,tmp_path/"actual")
    row = final["results"][0]
    assert not row["technical_valid"] and row["semantic_accept"] is None and row["false_reject"] is None
    assert "CITATION_GROUP_" in json.dumps(row)


def test_genuinely_irrelevant_original_citation_is_assessed_semantic_negative(tmp_path):
    value = plan(extra=True)
    source = value["source_bindings"]["cases"]["tiny"]
    text = "Earth orbits the Sun."
    hashed = hashlib.sha256(text.encode()).hexdigest()
    source["evidence"][1].update(text=text,text_hash=hashed)
    mapping = source["original_mapping"]["c2"]
    mapping.update(chunk_text=text,chunk_hash=hashed)
    mapping["units"][0].update(cleaned_text=text,text_hash=hashed)
    mapping["spans"][0].update(end=len(text),chunk_end=len(text))
    for label in value["labels"]:
        label["draft"]["answer_text"] += " [ev_002]"
        label["draft"]["citations"].append("ev_002")
    value["rows"][0]["control"] = "negative"
    value["source_transport"] = "ordinary_qa_compact_v2"
    value = runner.prepare(value)
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    verdict = positive(packet)
    group = next(g for g,v in packet["citation_groups"].items() if v["evidence_id"]=="ev_002")
    excluded = set(verdict["groups"][group]["s"])
    verdict["groups"][group] = dict(d="I",s=[])
    for c in verdict["claims"].values():
        for u in c["u"].values():
            u["s"] = [s for s in u["s"] if s not in excluded]
    final,_ = execute(value,verdict,tmp_path/"actual")
    row = final["results"][0]
    assert row["technical_valid"] and row["semantic_accept"] is False and row["correctness"] is True
    assert "ACTUAL_CITATION_IRRELEVANT" in json.dumps(row)
    assert "ACTUAL_CITATION_ASSESSMENT_MISSING" not in json.dumps(row)


def test_max_output_truncation_retains_raw_and_financial_receipt_without_scoring(tmp_path):
    value,_,verdict = prepared()
    final,raw = execute(value,verdict,tmp_path/"actual",length=True)
    row = final["results"][0]
    assert final["status"]=="STOPPED_NO_RETRY" and row["semantic_accept"] is None
    assert row.get("false_reject") is None and row["reason"]=="PROVIDER_RESPONSE_CONTRACT_INVALID"
    assert (tmp_path/"actual/unit_0-raw-response.json").read_bytes()==raw
    assert (tmp_path/"actual/unit_0-settlement.json").exists()


def test_source_pointer_cannot_borrow_uncited_source(tmp_path):
    value,packet,verdict = prepared(extra=True)
    outside = next(row[0] for row in packet["sources"] if row[2]=="ev_002")
    verdict["groups"]["G1"]["s"] = [outside]
    final,_ = execute(value,verdict,tmp_path/"actual")
    assert "SOURCE_REFERENCE_OUTSIDE_ACTUAL_CITATIONS" in json.dumps(final)
    assert final["results"][0]["semantic_accept"] is None


def test_unassessed_context_is_incomplete_not_a_semantic_rejection(tmp_path):
    value,_,verdict = prepared()
    verdict["claims"]["C1"]["k"] = "U"
    final,_ = execute(value,verdict,tmp_path/"actual")
    assert final["results"][0]["semantic_accept"] is None
    assert final["results"][0]["false_reject"] is None
    assert "COMPACT_CONTEXT_UNASSESSED" in json.dumps(final)


def test_overlapping_quote_occurrences_reject_instead_of_counting_nonoverlap(tmp_path):
    value = plan()
    update_source(value["source_bindings"]["cases"]["tiny"],"a"*601)
    value["source_transport"] = "ordinary_qa_compact_v2"
    value = runner.prepare(value)
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    verdict = positive(packet)
    final,_ = execute(value,verdict,tmp_path/"actual")
    assert final["results"][0]["semantic_accept"] is None
    assert "SOURCE_REFERENCE_QUOTE_NOT_UNIQUE" in json.dumps(final)


def test_overlapping_windows_retain_boundary_context_and_no_tiny_tail():
    from generation.ordinary_qa_compact_v2 import quote_table
    text = "a"*301+"only under the stated condition"+"b"*800
    windows = list(quote_table([dict(exact_text=text)]).values())
    assert any(start<=301 and end>=330 and end-start==600 for _,start,end in windows)
    assert all(end-start>=600 for _,start,end in windows)
    assert any(start==0 and end==len(text) for _,start,end in windows)


def test_compact_more_than_eight_requirement_proofs_reaches_full_native_runner(tmp_path):
    value = plan()
    text = "Photosynthesis uses light energy. " + " ".join(f"Authored context marker number {i}." for i in range(12))
    update_source(value["source_bindings"]["cases"]["tiny"],text)
    value["source_transport"] = "ordinary_qa_compact_v2"
    value = runner.prepare(value)
    packet = json.loads(value["rows"][0]["body"]["messages"][-1]["content"])
    verdict = positive(packet)
    proofs = [row[0] for row in packet["quote_pointers"][:9]]
    assert len(proofs)==9
    verdict["requirements"]["R1"]["p"] = proofs
    final,_ = execute(value,verdict,tmp_path/"actual")
    assert final["results"][0]["technical_valid"] and final["results"][0]["semantic_accept"] is True
