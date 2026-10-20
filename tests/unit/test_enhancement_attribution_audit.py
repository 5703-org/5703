"""Authored synthetic checks, isolated from the formal study and private labels."""

import copy
import json

import pytest

from evaluation.enhancement.attribution_audit import (
    audit,
    digest,
    direct_primary,
    inspect_outcome,
    sha,
    union_length,
    verify_fragment,
    verify_mapping,
)
from evaluation.enhancement.judge import judge_input


def fixture():
    text = "α water. Ice floats."
    unit = {"id": "u", "page": 7, "cleaned_text": text, "text_hash": sha(text)}
    mapping = {
        "document_version_id": "v",
        "processing_id": "p",
        "asset_id": "a",
        "chunk_text": text,
        "chunk_hash": sha(text),
        "units": [unit],
        "spans": [
            {
                "unit_id": "u",
                "page": 7,
                "start": 0,
                "end": len(text),
                "chunk_start": 0,
                "chunk_end": len(text),
            }
        ],
    }
    exact = text[9:]
    identity = ["cleaned_unit_offsets_v1", "v", "p", "c", "u", 9, len(text), sha(exact)]
    fragment = {
        "fragment_id": "span_" + sha(json.dumps(identity, separators=(",", ":")))[:32],
        "evidence_id": "ev_001",
        "chunk_id": "c",
        "asset_id": "a",
        "processing_id": "p",
        "document_version_id": "v",
        "source_unit_id": "u",
        "start": 9,
        "end": len(text),
        "exact_text": exact,
        "text_hash": sha(exact),
        "chunk_start": 9,
        "chunk_end": len(text),
        "page": 7,
        "offset_basis": "cleaned_source_unit_unicode",
        "mapping_quality": "sentence",
        "block_kind": "prose",
        "complete_block": True,
    }
    evidence = {
        "evidence_id": "ev_001",
        "chunk_id": "c",
        "asset_id": "a",
        "processing_id": "p",
        "text": exact,
        "text_hash": sha(exact),
        "source_title": "Synthetic book",
        "section": "1",
        "pages": [7],
    }
    claim = {
        "claim_id": "claim_1",
        "answer_field": "answer_text",
        "start": 0,
        "end": 21,
        "text": "Ice floats. [ev_001]",
        "evidence_ids": ["ev_001"],
        "fragment_ids": [fragment["fragment_id"]],
    }
    claim["end"] = len(claim["text"])
    response = {
        "response_type": "answer",
        "answer_text": claim["text"],
        "short_answer": "Ice floats.",
        "citations": ["ev_001"],
    }
    projection = {
        "version": "test",
        "response": response,
        "citation_views": [
            {
                "evidence_id": "ev_001",
                "source_title": "Synthetic book",
                "section": "1",
                "pages": [7],
                "preview": exact,
                "segments": [
                    {"text": exact, "highlight": True, "fragment_ids": [fragment["fragment_id"]]}
                ],
            }
        ],
    }
    projection["content_hash"] = sha(json.dumps(projection, sort_keys=True, ensure_ascii=False))
    outcome = {
        "response": response,
        "evidence": [evidence],
        "error": None,
        "attribution": {
            "fragments": [fragment],
            "claims": [claim],
            "evidence_ranges": [
                {
                    "evidence_id": "ev_001",
                    "chunk_id": "c",
                    "chunk_text_hash": sha(text),
                    "chunk_start": 9,
                    "chunk_end": len(text),
                }
            ],
        },
        "delivered_projection": projection,
        "checks": [{"accepted": True, "projection_hash": projection["content_hash"]}],
    }
    return mapping, fragment, evidence, outcome


def test_unicode_cleaned_spans_and_preselected_subrange_are_exact():
    mapping, fragment, evidence, outcome = fixture()
    units = verify_mapping(mapping)
    verify_fragment(fragment, evidence, mapping, units)
    result = inspect_outcome(outcome, {"source_map": {"c": mapping}})
    assert result["structural_issues"] == []
    assert result["lengths"]["submitted_evidence_characters"] == len(evidence["text"])
    assert result["lengths"]["full_cleaned_selected_source_unit_characters"] > len(evidence["text"])


@pytest.mark.parametrize(
    "change", ["unit_hash", "identity", "offset", "span_gap", "preview", "range"]
)
def test_independent_checks_catch_source_or_projection_corruption(change):
    mapping, fragment, evidence, outcome = fixture()
    if change == "unit_hash":
        mapping["units"][0]["text_hash"] = "wrong"
    elif change == "identity":
        fragment["processing_id"] = "wrong"
    elif change == "offset":
        fragment["start"] += 1
    elif change == "span_gap":
        mapping["spans"][0]["chunk_start"] = 1
    elif change == "preview":
        outcome["delivered_projection"]["citation_views"][0]["preview"] = "Invented."
    else:
        outcome["attribution"]["evidence_ranges"][0]["chunk_start"] = 0
    result = inspect_outcome(outcome, {"source_map": {"c": mapping}})
    assert result["structural_issues"]


def test_failed_draft_mapping_is_preserved_but_not_published_length():
    mapping, _, _, outcome = fixture()
    outcome["drafts"] = [{"response": outcome.pop("response")}]
    outcome["error"] = {"code": "SEMANTIC_CHECK_FAILED"}
    result = inspect_outcome(outcome, {"source_map": {"c": mapping}})
    assert not result["published_answer"]
    assert result["claim_text_scope"] == "retained_private_draft"
    assert result["structural_issues"] == []
    assert result["lengths"]["delivered_source_characters"] is None


def test_overlap_counts_unicode_source_characters_once():
    _, f, _, _ = fixture()
    overlap = {**f, "start": f["start"] + 1}
    assert union_length([f, overlap]) == f["end"] - f["start"]


def test_direct_primary_excludes_hint_scope_but_requires_success_and_support():
    verdict = {
        "supported": 1,
        "complete_answer": 1,
        "fact_error": 0,
        "within_scope": 0,
        "specific_help": 0,
    }
    assert direct_primary({"response_type": "answer"}, None, verdict)
    assert not direct_primary({"response_type": "answer"}, {"code": "failure"}, verdict)
    assert not direct_primary({"response_type": "answer"}, None, {**verdict, "supported": 0})


def test_corrected_direct_judge_input_cannot_carry_hint_allowance():
    task = {
        "question": "Authored synthetic question",
        "turns": ["hint"],
        "critical_answer": "Private synthetic reference",
        "help_allowances": ["SECRET_HINT_ONLY_LIMIT"],
    }
    result = {
        "turn": 1,
        "experiment": "citations",
        "outcome": {},
        "exposure": None,
        "prior_exposure": [],
    }
    direct = judge_input(task, result)
    assert "SECRET_HINT_ONLY_LIMIT" not in json.dumps(direct)
    assert "Complete direct answer" in direct["permitted_help"]
    hint = judge_input(task, {**copy.deepcopy(result), "experiment": "hints"})
    assert hint["permitted_help"] == task["help_allowances"][0]


def test_all_planned_denominator_includes_missing_and_failed_results(tmp_path):
    def freeze(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**value, "content_sha256": digest(value)}), encoding="utf-8")

    run = tmp_path / "run"
    source = tmp_path / "source"
    dataset = {"tasks": [{"id": "synthetic"}]}
    freeze(source / "private-tasks.json", dataset)
    sm = {"dataset_sha256": digest(dataset)}
    freeze(source / "manifest.json", sm)
    mapping, _, _, outcome = fixture()
    retrieval = {"source_map": {"c": mapping}}
    freeze(source / "retrieval/synthetic.json", retrieval)
    planned = [
        {"id": s, "task_id": "synthetic", "condition": s, "turn": 1}
        for s in ("paragraph", "posthoc_spans", "preselected_spans")
    ]
    manifest = {
        "experiment": "citations",
        "planned": planned,
        "planned_count": 3,
        "source_directory": str(source),
        "source_manifest_sha256": digest(sm),
        "dataset_sha256": digest(dataset),
        "retrieval_hashes": {"synthetic": digest(retrieval)},
    }
    freeze(run / "run-manifest.json", manifest)
    freeze(run / "judge-manifest.json", {"run_manifest_sha256": digest(manifest)})
    freeze(
        run / "analysis.json",
        {
            "run_manifest_sha256": digest(manifest),
            "metrics": {
                s: {"complete_supported_answer_rate_all_planned": 0}
                for s in ("paragraph", "posthoc_spans", "preselected_spans")
            },
        },
    )
    failed = {
        **outcome,
        "response": None,
        "error": {"code": "SEMANTIC_CHECK_FAILED"},
        "drafts": [{"response": outcome["response"], "revision": 0}],
    }
    freeze(
        run / "results/paragraph.json",
        {**planned[0], "outcome": failed, "retrieval_sha256": digest(retrieval)},
    )
    report = audit(run, expected_tasks=1)
    assert report["planned"] == 3
    assert len(report["items"]) == 3
    assert sum(s["missing_results"] for s in report["strategies"].values()) == 2
    assert report["strategies"]["paragraph"]["errors"] == {"SEMANTIC_CHECK_FAILED": 1}
    assert all(s["direct_primary_positive"] == 0 for s in report["strategies"].values())
    assert report["source_files_unchanged"]
