"""Authored offline fixtures for blinding, denominators and immutable human imports."""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from evaluation.enhancement.protocol import digest, freeze
from evaluation.memory_v2.protocol import freeze_study
from evaluation.memory_v2 import review


def tasks():
    """Synthetic packaging-safe records, unrelated to the private study questions."""
    return [
        {
            "id": f"fixture-Q{i:02}",
            "family": f"family-{i}",
            "task_type": "process",
            "question": f"Authored test question {i}?",
            "critical_answer": "Authored review fixture.",
            "source_requirement": {"book": f"book-{i // 6}"},
            "teaching_task": i < 12,
            "turns": ["First fixture hint", "Next fixture hint", "Last fixture hint"],
            "help_allowances": ["A bounded authored hint"] * 3,
        }
        for i in range(24)
    ]


def trajectories():
    return [
        {
            "id": f"fixture-M{i:02}",
            "family": f"memory-{i}",
            "statements": ["Authored test learner preference."],
            "profile": {},
            "probes": [
                {
                    "question_id": f"fixture-Q{i:02}",
                    "events": [{"kind": "statement", "index": 0}],
                    "use_profile": True,
                    "prefix": "",
                    "expected": {"human_rating": None},
                }
                for _ in range(3)
            ],
        }
        for i in range(12)
    ]


@pytest.fixture
def materials(tmp_path):
    source, run, memory, output = [
        tmp_path / name for name in ("source", "run", "memory", "review")
    ]
    bank, learners = tasks(), trajectories()
    freeze(source / "private-tasks.json", {"tasks": bank})
    freeze(
        source / "private-trajectories.json",
        {"trajectories": learners, "extraction_cases": [], "gating_pairs": []},
    )
    freeze_study(
        source / "study.json",
        bank,
        learners,
        {
            "source_hashes": {"fixture": "source"},
            "protocol_hashes": {"fixture": "protocol"},
            "model_config": {"provider": "mock"},
            "checker_config": {"provider": "mock"},
            "corpus": {"release_id": "fixture"},
            "retrieval_hashes": {"fixture": "retrieval"},
            "memory_extraction_sha256": digest([]),
            "memory_gating_sha256": digest([]),
        },
    )
    study = review.load(source / "study.json")
    freeze(
        run / "run-manifest.json",
        {
            "study_hash": digest(study),
            "source_directory": str(source),
            "studies": ["A", "B", "C", "T"],
        },
    )
    freeze(memory / "answer-manifest.json", {"study_hash": digest(study), "planned": 180})
    available = []
    for group, folder in (("A", run), ("T", run), ("M", memory)):
        item = next(r for r in study["schedule"] if r["study"] == group)
        response = {
            "response_type": "answer",
            "answer_text": "Authored answer. [ev_001]",
            "citations": ["ev_001"],
            "short_answer": None,
            "follow_up_questions": [],
        }
        exposure = {
            "response": response,
            "citation_views": [
                {
                    "evidence_id": "ev_001",
                    "title": "<script>not executable</script>",
                    "segments": [{"text": "Approved exact text", "highlight": True}],
                    "support": {"reason": "PRIVATE CHECK"},
                }
            ],
        }
        freeze(
            folder / "results" / (item["id"] + ".json"),
            {
                **item,
                "status": "answer",
                "outcome": {
                    "response": response,
                    "error": None,
                    "evidence": [
                        {
                            "evidence_id": "ev_001",
                            "text": "Authorised reference",
                            "text_hash": "fixture",
                        }
                    ],
                    "checks": [{"private": "PRIVATE CHECK"}],
                    "model": "SECRET ARM MODEL",
                },
                "exposure": exposure,
                "prior_exposure": [exposure],
                "memory_state_trace": {"content": "PRIVATE ARM STATE"},
            },
        )
        available.append(item)
    result = review.export_reviews(run, output, memory_run=memory)
    return source, run, memory, output, result, available


def filled(output, path, reviewer, slot, *, score="1", row_id=None):
    data = review.load(output / f"reviewer-{slot}" / "review-material.json")
    item = (
        next(r for r in data["items"] if r["review_id"] == row_id)
        if row_id
        else next(r for r in data["items"] if r["execution_status"] == "delivered")
    )
    row = {
        "review_id": item["review_id"],
        "reviewer_id": reviewer,
        "rubric_version": review.VERSION,
        "reason": "Authored test rating, never a project human result.",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    row.update({k: score if k in item["applicable_fields"] else "NA" for k in review.SCORES})
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=review.FIELDS)
        writer.writeheader()
        writer.writerow(row)
    return item["review_id"]


def test_export_retains_552_denominator_blank_scores_and_condition_blinding(materials):
    _, _, _, output, result, _ = materials
    assert result == {"planned": 552, "recorded": 3, "reviewers": 2, "ratings_completed": 0}
    orders = []
    for slot in (1, 2):
        data = review.load(output / f"reviewer-{slot}" / "review-material.json")
        orders.append([r["review_id"] for r in data["items"]])
        body = json.dumps(data)
        assert all(
            s not in body
            for s in (
                "PRIVATE CHECK",
                "SECRET ARM MODEL",
                "PRIVATE ARM STATE",
                '"arm"',
                '"condition"',
            )
        )
        assert "Approved exact text" in body and "Authorised reference" in body
        assert sum(r["execution_status"] == "no_delivered_answer" for r in data["items"]) == 549
        with (output / f"reviewer-{slot}" / "ratings.csv").open(encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 552 and all(
            not r[k]
            for r in rows
            for k in (*review.SCORES, "reviewer_id", "reason", "completed_at")
        )
        page = (output / f"reviewer-{slot}" / "review.html").read_text(encoding="utf-8")
        assert "<script>" not in page and "&lt;script&gt;" in page
    assert orders[0] != orders[1] and set(orders[0]) == set(orders[1])
    assert review.agreement(output)["ratings_imported"] == 0


def test_import_requires_actual_attestation_applicability_and_distinct_slots(materials, tmp_path):
    output = materials[3]
    p = tmp_path / "ratings.csv"
    identity = filled(output, p, "fixture-person-1", 1)
    with pytest.raises(ValueError, match="attestation"):
        review.import_review(output, p, "fixture-person-1", slot=1)
    receipt = review.import_review(output, p, "fixture-person-1", slot=1, independent_human=True)
    assert receipt["ratings_imported"] == 1
    assert review.import_review(output, p, "fixture-person-1", slot=1, independent_human=True)[
        "idempotent"
    ]
    with pytest.raises(ValueError, match="distinct"):
        review.import_review(output, p, "fixture-person-1", slot=2, independent_human=True)
    filled(output, p, "fixture-person-2", 2, row_id=identity)
    review.import_review(output, p, "fixture-person-2", slot=2, independent_human=True)
    with pytest.raises(ValueError, match="distinct"):
        filled(output, p, "third-person", 2, row_id=identity)
        review.import_review(output, p, "third-person", slot=2, independent_human=True)
    report = review.agreement(output)
    assert report["paired_items"] == 1 and report["not_paired"] == 551
    assert report["identity_authenticated"] is False


def test_revisions_and_adjudication_preserve_originals(materials, tmp_path):
    output = materials[3]
    a, b, c = [tmp_path / f"{x}.csv" for x in "abc"]
    rid = filled(output, a, "person-one", 1)
    first = review.import_review(output, a, "person-one", slot=1, independent_human=True)
    old_bytes = Path(first["artifact"]).read_bytes()
    filled(output, b, "person-two", 2, score="0", row_id=rid)
    review.import_review(output, b, "person-two", slot=2, independent_human=True)
    assert len(review.agreement(output)["disagreements"]) == 1
    filled(output, c, "discussion-chair", 1, row_id=rid)
    decided = review.import_adjudication(output, c, "discussion-chair", human_attestation=True)
    assert decided["adjudicated"] == 1
    assert len(review.agreement(output)["disagreements"]) == 1
    filled(output, c, "person-one", 1, score="0", row_id=rid)
    review.import_review(output, c, "person-one", slot=1, independent_human=True)
    report = review.agreement(output)
    assert report["disagreements"] == [] and len(report["adjudications"]) == 1
    assert report["ratings_imported"] == 2 and Path(first["artifact"]).read_bytes() == old_bytes
    assert len(list((output / "imports").glob("*.json"))) == 3


def test_changed_material_wrong_result_and_duplicate_run_rejected(materials, tmp_path):
    source, run, memory, output, _, available = materials
    p = tmp_path / "rating.csv"
    filled(output, p, "person-one", 1)
    material_path = output / "reviewer-1/review-material.json"
    changed = review.load(material_path)
    changed["items"][0]["question"] = "modified"
    material_path.write_text(
        json.dumps({**changed, "content_sha256": digest(changed)}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="modified"):
        review.import_review(output, p, "person-one", slot=1, independent_human=True)
    item = available[0]
    target = memory / "results" / (item["id"] + ".json")
    target.write_bytes((run / "results" / target.name).read_bytes())
    with pytest.raises(ValueError, match="more than one"):
        review.export_reviews(run, tmp_path / "other", memory_run=memory)


@pytest.mark.parametrize(
    "change", ["blank", "bad_applicability", "duplicate", "future", "automatic"]
)
def test_invalid_rating_rows_do_not_create_imports(materials, tmp_path, change):
    output = materials[3]
    path = tmp_path / "bad.csv"
    name = "Codex" if change == "automatic" else "person-one"
    filled(output, path, name, 1)
    with path.open(encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if change == "blank":
        for key in (*review.SCORES, "reviewer_id", "reason", "completed_at"):
            rows[0][key] = ""
    elif change == "bad_applicability":
        rows[0]["factual_correct"] = "NA"
    elif change == "duplicate":
        rows += rows
    elif change == "future":
        rows[0]["completed_at"] = "2999-01-01T00:00:00+00:00"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=review.FIELDS)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(ValueError):
        review.import_review(output, path, name, slot=1, independent_human=True)
    assert not list((output / "imports").glob("*.json"))


def test_oracle_import_exact_hash_person_time_coverage_and_immutable_write(materials, tmp_path):
    source = materials[0]
    identity = tasks()[0]["id"]
    text = "Authored source fixture, not real oracle evidence."
    sha = hashlib.sha256(text.encode()).hexdigest()
    retrieval = {
        "id": identity,
        "question": tasks()[0]["question"],
        "evidence": [
            {
                "evidence_id": "ev_001",
                "chunk_id": "chunk",
                "text": text,
                "text_hash": sha,
                "processing_id": "processing",
                "asset_id": "asset",
            }
        ],
        "source_map": {
            "chunk": {
                "chunk_text": text,
                "chunk_hash": sha,
                "processing_id": "processing",
                "asset_id": "asset",
                "document_version_id": "version",
                "units": [{"id": "unit", "cleaned_text": text, "text_hash": sha}],
            }
        },
    }
    rp, ap = tmp_path / "retrieval.json", tmp_path / "attestation.json"
    freeze(rp, retrieval)
    attestation = {
        "reviewer_id": "fixture-person",
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "sufficient": True,
        "evidence_sha256": digest(retrieval),
        "coverage": {"required point": ["ev_001"]},
    }
    ap.write_text(json.dumps({**attestation, "evidence_sha256": "wrong"}), encoding="utf-8")
    with pytest.raises(ValueError, match="identify"):
        review.confirm_oracle(source, identity, rp, ap)
    ap.write_text(json.dumps({**attestation, "reviewer_id": "Codex"}), encoding="utf-8")
    with pytest.raises(ValueError):
        review.confirm_oracle(source, identity, rp, ap)
    ap.write_text(json.dumps(attestation), encoding="utf-8")
    result = review.confirm_oracle(source, identity, rp, ap)
    assert not result["human_identity_authenticated"]
    assert review.load(Path(result["artifact"]))["oracle_confirmation"] == attestation
    before = Path(result["artifact"]).read_bytes()
    review.confirm_oracle(source, identity, rp, ap)
    ap.write_text(json.dumps({**attestation, "reviewer_id": "different-person"}), encoding="utf-8")
    with pytest.raises(ValueError, match="different"):
        review.confirm_oracle(source, identity, rp, ap)
    assert Path(result["artifact"]).read_bytes() == before
