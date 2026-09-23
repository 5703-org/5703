"""Synthetic review/import fixtures only; no participant or study measurements."""

from copy import deepcopy
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from evaluation.enhancement import highlight
from evaluation.enhancement.analysis import analyse, cost_estimate
from evaluation.enhancement.protocol import digest, freeze
from evaluation.enhancement.review import export_reviews


def written(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def materials(tmp_path):
    text = "A source sentence. Another sentence."
    fragment = {
        "fragment_id": "f1",
        "start": 0,
        "end": 18,
        "exact_text": text[:18],
        "text_hash": highlight.sha(text[:18]),
    }
    data = {
        "version": "highlight_review_input_v1",
        "review_version": "synthetic-review",
        "seed": 20260920,
        "items": [
            {
                "id": "synthetic-item",
                "question": "Synthetic question",
                "answer_text": "A source sentence. [ev_001]",
                "claim": {
                    "claim_id": "c1",
                    "start": 0,
                    "end": 27,
                    "text": "A source sentence. [ev_001]",
                },
                "evidence": [
                    {
                        "evidence_id": "ev_001:u1",
                        "source_title": "Authored fixture",
                        "locator": "Synthetic page 1",
                        "text": text,
                        "text_sha256": highlight.sha(text),
                        "segments": highlight.segments(text, [fragment]),
                    }
                ],
            }
        ],
    }
    path = written(tmp_path / "materials" / "participant-input.json", data)
    schedule, mapping, hash_ = highlight.browser_schedule(data, "synthetic-A")
    shared = {
        "tool_version": highlight.TOOL_VERSION,
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "review_version": data["review_version"],
        "participant_id": "synthetic-A",
        "seed": data["seed"],
        "schedule_sha256": hash_,
    }
    key = {
        "version": "highlight_review_key_v1",
        **shared,
        "presentation_mapping": mapping,
        "schedule": schedule,
    }
    start = datetime.now(timezone.utc) - timedelta(seconds=20)
    attempts = [
        {
            **{k: row[k] for k in ("item_id", "claim_id", "schedule_index", "presentation_code")},
            "attempt": 1,
            "reopened": False,
            "started_at": (start + timedelta(seconds=index * 2)).isoformat(),
            "completed_at": (start + timedelta(seconds=index * 2 + 1)).isoformat(),
            "elapsed_wall_ms": 1000,
            "active_visible_ms": 800 + index,
            "support": "supported",
            "comment": "Synthetic importer fixture only",
            "events": [],
        }
        for index, row in enumerate(schedule)
    ]
    observed = {
        "version": "highlight_review_results_v1",
        **shared,
        "planned_presentations": 2,
        "completed_presentations": 2,
        "remaining_presentations": 0,
        "attempts": attempts,
    }
    return path.parent, observed, key


def submit(tmp_path, observed, key):
    return highlight.import_highlight(
        tmp_path / "materials",
        written(tmp_path / "observations.json", observed),
        written(tmp_path / "key.json", key),
    )


def test_python_schedule_matches_actual_browser_javascript_fixed_vector():
    data = {
        "review_version": "synthetic-review",
        "seed": 20260920,
        "items": [{"id": str(i), "claim": {"claim_id": "c" + str(i)}} for i in range(4)],
    }
    schedule, mapping, hash_ = highlight.browser_schedule(data, "synthetic-A")
    assert mapping == {"A": "paragraph", "B": "highlight"}
    assert [row["item_id"] for row in schedule] == ["1", "0", "2", "3", "1", "0", "3", "2"]
    assert hash_ == "f4a6a8e4b8f7c82333a1ad2f0819c8b24827c786d7b7718c7554ccc06ce86f67"


def test_first_attempts_and_reopens_keep_complete_denominator(tmp_path):
    folder, observed, key = materials(tmp_path)
    repeat = {**observed["attempts"][-1], "attempt": 2, "reopened": True, "active_visible_ms": 999}
    observed["attempts"].append(repeat)
    imported = submit(tmp_path, observed, key)
    assert imported["first_completed"] == 2
    report = highlight.summarise(folder)
    assert (
        report["actual_participants"] == 1
        and report["first_completed"] == report["planned_presentations"] == 2
    )
    assert report["paired_presentations"] == 1 and report["missing_presentations"] == 0
    assert report["expert_reference_count"] == 0
    assert all(v["correctness_denominator"] == 0 for v in report["conditions"].values())


@pytest.mark.parametrize(
    "mutation",
    [
        "flipped_condition",
        "duplicate_schedule",
        "false_hash",
        "changed_seed",
        "boolean_attempt",
        "nan_time",
        "wrong_claim",
        "false_count",
        "repeat_primary",
    ],
)
def test_import_rejects_forged_schedule_types_or_counts(tmp_path, mutation):
    _, observed, key = materials(tmp_path)
    if mutation == "flipped_condition":
        key["schedule"][0]["condition"] = key["schedule"][1]["condition"]
    elif mutation == "duplicate_schedule":
        key["schedule"].append(deepcopy(key["schedule"][0]))
    elif mutation == "false_hash":
        observed["schedule_sha256"] = key["schedule_sha256"] = "0" * 64
    elif mutation == "changed_seed":
        observed["seed"] = key["seed"] = 123
    elif mutation == "boolean_attempt":
        observed["attempts"][0]["attempt"] = True
    elif mutation == "nan_time":
        observed["attempts"][0]["active_visible_ms"] = float("nan")
    elif mutation == "wrong_claim":
        observed["attempts"][0]["claim_id"] = "other"
    elif mutation == "false_count":
        observed["completed_presentations"] = 1
    else:
        observed["attempts"].append(deepcopy(observed["attempts"][0]))
    with pytest.raises(ValueError):
        submit(tmp_path, observed, key)
    assert not (tmp_path / "materials" / "observation-imports").exists()


def test_partial_observation_retains_missing_and_no_pair(tmp_path):
    folder, observed, key = materials(tmp_path)
    observed.update(completed_presentations=1, remaining_presentations=1)
    observed["attempts"] = observed["attempts"][:1]
    submit(tmp_path, observed, key)
    report = highlight.summarise(folder)
    assert (
        report["first_completed"] == 1
        and report["missing_presentations"] == 1
        and report["paired_presentations"] == 0
    )
    assert report["mean_paired_visible_ms_difference"] is None


def test_actual_reference_import_is_dataset_bound_and_does_not_fill_missing_ratings(tmp_path):
    folder, observed, key = materials(tmp_path)
    submit(tmp_path, observed, key)
    grades = tmp_path / "synthetic-expert.csv"
    with grades.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["item_id", "expert_id", "grade", "reason", "completed_at"]
        )
        writer.writeheader()
        writer.writerow(
            {
                "item_id": "synthetic-item",
                "expert_id": "synthetic-expert",
                "grade": "supported",
                "reason": "Synthetic test only",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    from pathlib import Path

    reference = Path(highlight.import_reference(folder, grades)["artifact"])
    assert all(
        v["correctness_denominator"] == 1 and v["correct"] == 1
        for v in highlight.summarise(folder, reference)["conditions"].values()
    )
    foreign = freeze(tmp_path / "foreign.json", {"dataset_sha256": "0" * 64, "ratings": []})
    assert foreign
    with pytest.raises(ValueError, match="different frozen dataset"):
        highlight.summarise(folder, tmp_path / "foreign.json")


def study_run(tmp_path, *, uncited=False, foreign_fragment=False):
    source, run = tmp_path / "sources", tmp_path / "run"
    source_manifest = freeze(source / "manifest.json", {"type": "synthetic source fixture"})
    text = "A source sentence. Another sentence."
    answer = "A source sentence. [ev_001]"
    fragment = {
        "fragment_id": "f1",
        "evidence_id": "ev_001",
        "chunk_id": "chunk1",
        "asset_id": "asset1",
        "processing_id": "process1",
        "document_version_id": "version1",
        "source_unit_id": "unit1",
        "start": 0,
        "end": 18,
        "chunk_start": 0,
        "chunk_end": 18,
        "exact_text": text[:18],
        "text_hash": highlight.sha(text[:18]),
        "page": 1,
        "offset_basis": "cleaned_source_unit_unicode",
    }
    if foreign_fragment:
        fragment["processing_id"] = "foreign-processing-version"
    evidence = {
        "evidence_id": "ev_001",
        "chunk_id": "chunk1",
        "asset_id": "asset1",
        "processing_id": "process1",
        "source_title": "Authored fixture",
        "section": "Synthetic section",
        "pages": [1],
        "locator": "PDF physical page 1",
        "text": text,
        "text_hash": highlight.sha(text),
        "display_strategy": "DO_NOT_LEAK_METHOD",
    }
    unit = {"id": "unit1", "page": 1, "cleaned_text": text, "text_hash": highlight.sha(text)}
    material = {
        "source_map": {
            "chunk1": {
                "asset_id": "asset1",
                "processing_id": "process1",
                "document_version_id": "version1",
                "chunk_text": text,
                "chunk_hash": highlight.sha(text),
                "units": [unit],
                "spans": [{"unit_id": "unit1", "start": 0, "end": len(text), "chunk_start": 0}],
            }
        }
    }
    task = {
        "id": "task1",
        "question": "Synthetic question",
        "turns": ["Give a hint"],
        "critical_answer": "Private reference fixture",
        "help_allowances": ["HINT ONLY SECRET LIMIT"],
    }
    freeze(source / "private-tasks.json", {"tasks": [task]})
    freeze(source / "retrieval/task1.json", material)
    planned = [
        {"id": "item" + str(i), "task_id": "task1", "condition": "posthoc_spans", "turn": 1}
        for i in range(3)
    ]
    manifest = {
        "source_directory": str(source),
        "source_manifest_sha256": source_manifest["content_sha256"],
        "experiment": "citations",
        "planned": planned,
        "model_config": {"model": "mock", "base_url": None},
        "split": "development",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    freeze(run / "run-manifest.json", manifest)
    claim = {
        "claim_id": "claim1",
        "answer_field": "answer_text",
        "text": answer,
        "start": 0,
        "end": len(answer),
        "fragment_ids": ["f1"],
        "evidence_ids": [] if uncited else ["ev_001"],
        "support": {"status": "supported"},
    }
    result = {
        **planned[0],
        "retrieval_sha256": digest(material),
        "exposure": {"response": {"answer_text": answer}, "citation_views": []},
        "outcome": {
            "evidence": [evidence],
            "response": {"response_type": "answer", "citations": ["ev_001"]},
            "attribution": {"fragments": [fragment], "claims": [claim]},
        },
        "wall_seconds": 1,
    }
    freeze(run / "results/item0.json", result)
    freeze(
        run / "results/item1.json",
        {**planned[1], "outcome": {"error": {"code": "TIMEOUT"}}, "exposure": None},
    )
    return run, result


def test_real_data_export_path_preserves_exclusions_identity_and_blinding(tmp_path):
    run, _ = study_run(tmp_path)
    output = tmp_path / "scratch"
    result = highlight.export_highlight(run, output)
    assert (
        result["planned_task_answers"] == 3
        and result["eligible_task_answers"] == 1
        and result["excluded_task_answers"] == 2
    )
    assert result["claims"] == 1 and result["human_observations"] == 0
    participant = json.loads((output / "participant-input.json").read_text())
    assert participant["review_version"] == "week08-development-source-display-v1"
    assert "automatic_support" not in json.dumps(participant) and "posthoc_spans" not in json.dumps(
        participant
    )
    assert "Private reference fixture" not in json.dumps(participant)
    source = participant["items"][0]["evidence"][0]
    assert "PDF physical page" in source["locator"]
    assert "".join(s["text"] for s in source["segments"]) == source["text"]
    assert result["highlighted_characters"] == 18 < result["displayed_characters"]
    with pytest.raises(ValueError, match="existing"):
        highlight.export_highlight(run, output)


def test_export_retains_uncited_linked_claim_for_completeness_review(tmp_path):
    run, _ = study_run(tmp_path, uncited=True)
    result = highlight.export_highlight(run, tmp_path / "scratch")
    assert result["claims"] == result["linked_claims_without_inline_citations"] == 1
    assert result["eligible_task_answers"] == 1 and result["excluded_task_answers"] == 2


def test_export_rejects_fragment_from_foreign_processing_version(tmp_path):
    run, _ = study_run(tmp_path, foreign_fragment=True)
    with pytest.raises(ValueError, match="source identity"):
        highlight.export_highlight(run, tmp_path / "scratch")
    assert not (tmp_path / "scratch").exists()


def test_segments_reject_python_negative_slice_even_if_text_hash_matches():
    with pytest.raises(ValueError, match="immutable"):
        highlight.segments(
            "prefix tail",
            [
                {
                    "fragment_id": "f",
                    "start": -4,
                    "end": 11,
                    "exact_text": "tail",
                    "text_hash": highlight.sha("tail"),
                }
            ],
        )


def test_direct_review_does_not_supply_hint_allowance_or_method_metadata(tmp_path):
    run, _ = study_run(tmp_path)
    output = tmp_path / "reviews"
    result = export_reviews(run, output)
    payload = (output / "reviewer-1/review-material.json").read_text()
    assert result["items"] == 3 and result["ratings_completed"] == 0
    assert "HINT ONLY SECRET LIMIT" not in payload and "DO_NOT_LEAK_METHOD" not in payload
    assert "complete direct explanation" in payload and "verification references" in payload


def test_analysis_does_not_count_stale_positive_judge_flag_for_failed_answer(tmp_path):
    run, _ = study_run(tmp_path)
    verdict = {
        "supported": 1,
        "specific_help": 1,
        "within_scope": 1,
        "fact_error": 0,
        "citation_complete": 1,
        "complete_answer": 1,
    }
    freeze(
        run / "judgments/item1.json",
        {"id": "item1", "state": "judged", "judgment": verdict, "valid_hint": True},
    )
    summary = analyse(run)
    assert summary["items"][1]["valid_hint"] is False
    assert summary["metrics"]["posthoc_spans"]["complete_supported_answer_rate_all_planned"] == 0
    assert summary["metrics"]["posthoc_spans"]["requests_with_unknown_call_count"] == 3


def test_tariff_estimate_rejects_lookalike_endpoint_and_naive_time():
    usage = {"cache_hit_input_tokens": 1, "cache_miss_input_tokens": 1, "output_tokens": 1}
    assert (
        cost_estimate(
            usage,
            "2026-09-20T00:00:00Z",
            model="deepseek-flash",
            base_url="https://api.deepseek.com.evil.invalid",
        )
        is None
    )
    assert (
        cost_estimate(
            usage,
            "2026-09-20T00:00:00",
            model="deepseek-flash",
            base_url="https://api.deepseek.com",
        )
        is None
    )
