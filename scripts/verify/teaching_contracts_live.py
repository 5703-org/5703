"""Frozen v2/v3 live contract comparison with exact official-source snapshots.

This evaluator-only command never creates learner sessions or changes corpus data.
Its automatic endpoints measure delivery/contracts; semantic quality needs reviewers.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random
import statistics
import time
from uuid import uuid4

from app.core.config import Settings
from contracts.models import EvidenceSnapshot
from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget
from generation.adapters import chat_value
from generation.token_counting import TokenCounter

ROOT = Path(__file__).resolve().parents[2]
CASE_IDS = [
    "W8V2-Q01",
    "W8V2-Q03",
    "W8V2-Q07",
    "W8V2-Q08",
    "W8V2-Q13",
    "W8V2-Q16",
    "W8V2-Q19",
    "W8V2-Q22",
]
ATTEMPTS = {
    "W8V2-Q01": (
        "Which comparison dimension is mentioned after cell packing?",
        "The amount of extracellular matrix.",
        "concept",
    ),
    "W8V2-Q03": (
        "What fluid does the problem ask you to trace?",
        "Excess interstitial fluid.",
        "concept",
    ),
    "W8V2-Q07": (
        "Which availability is held low in this problem?",
        "Glucose availability.",
        "concept",
    ),
    "W8V2-Q08": (
        "Does the question allow the DNA sequence itself to change?",
        "No, it stays the same.",
        "choice",
    ),
    "W8V2-Q13": (
        "What percentage abundance is assigned to the 10.0 u isotope?",
        "20.0%.",
        "numeric",
    ),
    "W8V2-Q16": ("Which two molecules are you comparing?", "CH4 and H2O.", "concept"),
    "W8V2-Q19": (
        "Which process does the question ask you to consider in fungi?",
        "Extracellular digestion.",
        "concept",
    ),
    "W8V2-Q22": (
        "Which succession begins on newly exposed rock?",
        "Primary succession.",
        "concept",
    ),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_snapshot():
    paths = [
        p
        for p in (ROOT / "generation").rglob("*")
        if p.is_file() and p.suffix in {".py", ".txt"} and "__pycache__" not in p.parts
    ]
    paths += [
        ROOT / name
        for name in [
            "contracts/models.py",
            "conversation/query.py",
            "conversation/understanding.py",
            "conversation/context.py",
            "personalisation/compiler.py",
            "retrieval/source_spans.py",
            "retrieval/complementary_spans.py",
            "scripts/verify/teaching_contracts_live.py",
        ]
        if (ROOT / name).is_file()
    ]
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(paths)}


def validate_official_sources(bundle, cases):
    manifest = read(bundle / "MANIFEST.json")
    data = bundle / manifest["data"]["path"]
    if sha(data.read_bytes()) != manifest["data"]["sha256"]:
        raise ValueError("Official corpus data hash mismatch")
    required_chunks = {ev["chunk_id"] for c in cases for ev in c["retrieval"]["evidence"]}
    required_units = {
        u["id"] for c in cases for m in c["retrieval"]["source_map"].values() for u in m["units"]
    }
    chunks, units, releases, documents = {}, {}, {}, {}
    with gzip.open(data, "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            table, row = item["table"], item["row"]
            if table == "chunks" and row["id"] in required_chunks:
                chunks[row["id"]] = row
            elif table == "source_units" and row["id"] in required_units:
                units[row["id"]] = row
            elif (
                table == "release_chunks"
                and row["release_id"] == manifest["active_release_id"]
                and row["chunk_id"] in required_chunks
            ):
                releases[row["chunk_id"]] = row
            elif table == "documents":
                documents[row["id"]] = row
    for case in cases:
        for ev in case["retrieval"]["evidence"]:
            chunk = chunks[ev["chunk_id"]]
            mapping = case["retrieval"]["source_map"][ev["chunk_id"]]
            assert ev["chunk_id"] in releases
            assert sha(chunk["text"].encode()) == chunk["text_hash"] == ev["text_hash"]
            assert ev["text"] == chunk["text"] == mapping["chunk_text"]
            assert ev["source_title"] == documents[chunk["document_id"]]["title"]
            assert ev["pages"] == chunk["pages"] and ev["section"] == chunk["section"]
            assert mapping["spans"] == chunk["spans"]
            for unit in mapping["units"]:
                original = units[unit["id"]]
                assert unit["cleaned_text"] == original["cleaned_text"]
                assert unit["text_hash"] == sha(original["cleaned_text"].encode())
                assert unit["page"] == original["page"]
                if "raw_text" in unit:
                    assert unit["raw_text"] == original["raw_text"]
    return {
        "release_id": manifest["active_release_id"],
        "vector_count": manifest["active_vector_count"],
        "dimension": manifest["dimension"],
        "bundle_manifest_sha256": sha((bundle / "MANIFEST.json").read_bytes()),
        "data_sha256": manifest["data"]["sha256"],
        "verified_chunks": len(chunks),
        "verified_source_units": len(units),
        "verification": "Exact retained retrieval input, current official-bundle text/hash/page/span/source-unit equality. No new retrieval run or live visibility claim.",
    }


def freeze(source, bundle, output):
    if output.exists():
        raise ValueError("Use a new study directory; preserve previous records")
    previous = read(source / "study.json")
    tasks = {t["id"]: t for t in read(source / "private-tasks.json")["tasks"]}
    cases = []
    for cid in CASE_IDS:
        task = tasks[cid]
        cases.append(
            {
                "id": cid,
                "family": task["family"],
                "book": task["source_anchors"][0]["book"],
                "question": task["question"],
                "task_type": {
                    "comparison": "concept_comparison",
                    "process": "process_reasoning",
                    "calculation": "simple_calculation",
                }[task["task_type"]],
                "pending_question": ATTEMPTS[cid][0],
                "attempt": ATTEMPTS[cid][1],
                "expected_response_kind": ATTEMPTS[cid][2],
                "source_anchors": task["source_anchors"],
                "required_points": task["required_points"],
                "forbidden_inferences": task["forbidden_inferences"],
                "retrieval": read(source / "retrieval" / f"{cid}.json"),
            }
        )
    corpus = validate_official_sources(bundle, cases)
    cfgs = {k: previous["checkpoint"][k] for k in ["model_config", "checker_config"]}
    for cfg in cfgs.values():
        ModelConfig.from_dict(cfg).validate()
        assert cfg["provider"] == "openai_compatible" and cfg["model"] == "deepseek-flash"
        assert cfg["base_url"] == "https://api.deepseek.com/v1"
        counter = TokenCounter(ModelConfig.from_dict(cfg))
        assert counter.count("Source-bound teaching check") > 0
    schedule = []
    for case in cases:
        for mode in ["textbook", "general_knowledge"]:
            for stage in ["direct", "first_hint", "another_hint", "learner_attempt"]:
                for policy in ["evidence_reliability_v2", "evidence_reliability_v3"]:
                    schedule.append(
                        {
                            "id": f"C{len(schedule) + 1:03}",
                            "case_id": case["id"],
                            "family": case["family"],
                            "book": case["book"],
                            "answer_mode": mode,
                            "stage": stage,
                            "policy": policy,
                        }
                    )
    random.Random(570326).shuffle(schedule)
    manifest = {
        "schema": "teaching_contract_live_comparison_v1",
        "frozen_at": now(),
        "seed": 570326,
        "planned_outcomes": len(schedule),
        "schedule": schedule,
        "cases": cases,
        "corpus": corpus,
        **cfgs,
        "source_hashes": source_snapshot(),
        "concurrency": 2,
        "budget": {"max_calls": 4, "max_active_seconds": 180},
        "design": "Eight existing developer-authored task families, two per original book; two answer modes and four independent fixed contexts crossed with frozen v2/v3. Another-hint and learner-attempt contexts use identical labelled authored prior tutor questions, not outputs generated by another arm. Original selected evidence is exact official text, identical between policy arms; general mode has no evidence. This is a generation contract comparison, not retrieval/end-to-end latency or a new independent semantic benchmark.",
        "automatic_endpoints": [
            "published answer",
            "checked hint short_answer null",
            "mode-correct citation metadata",
            "learner-attempt visible checked evaluation and unchanged help level",
        ],
        "interpretation": "Online checker acceptance is operational, not independent quality truth. All scheduled failures stay in denominators. v2 has no typed learner-attempt evaluation contract; its absence is separately reported, not a fabricated correctness error. No model tuning or default backend promotion follows from this study.",
        "human_ratings": 0,
        "monetary_cost": None,
        "cost_scope": "Provider token/cache usage is measured. No provider billing receipt is available; no tariff or invoice amount is fabricated.",
    }
    for item in manifest["schedule"]:
        prepared = build_request(item, manifest)
        for evidence in prepared.evidence:
            EvidenceSnapshot.model_validate(evidence)
    write(output / "frozen-study.json", manifest)
    for relative in manifest["source_hashes"]:
        target = output / "frozen-source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    write(
        output / "freeze-receipt.json",
        {
            "frozen_study_sha256": sha((output / "frozen-study.json").read_bytes()),
            "source_files": len(manifest["source_hashes"]),
            "planned": len(schedule),
            "created_at": now(),
        },
    )
    print(
        json.dumps(
            {
                "status": "frozen",
                "planned": len(schedule),
                "books": dict(Counter(c["book"] for c in cases)),
                "verified_chunks": corpus["verified_chunks"],
            }
        ),
        flush=True,
    )


def build_request(item, manifest):
    case = next(c for c in manifest["cases"] if c["id"] == item["case_id"])
    retrieval = case["retrieval"]
    stage = item["stage"]
    hint = stage != "direct"
    question = case["question"]
    prior = "Consider one part of the problem first. " + case["pending_question"]
    history = []
    delivered = []
    if stage == "first_hint":
        question += " Give me one first hint, leaving the final answer for me."
    elif stage in {"another_hint", "learner_attempt"}:
        question = (
            "Give me one more hint for this same problem."
            if stage == "another_hint"
            else case["attempt"]
        )
        history = [
            {"role": "user", "content": case["question"]},
            {"role": "assistant", "content": prior},
        ]
        delivered = [
            {
                "response": chat_value("answer", prior),
                "citation_views": [],
                "help_level": 1,
                "origin": "authored_fixed_context",
            }
        ]
    context = {
        "teaching_mode": "hint" if hint else "direct",
        "help_level": 2 if stage == "another_hint" else 1 if hint else 0,
        "task_type": case["task_type"],
        "current_problem": case["question"],
        "delivered_turns": delivered,
        "disclosure_events": [],
        "requested_help": [
            {"action": stage, "help_level": 2 if stage == "another_hint" else 1 if hint else 0}
        ],
    }
    if stage == "learner_attempt":
        context.update(
            turn_role="learner_attempt",
            pending_tutor_question_id="authored-question-" + case["id"],
            pending_tutor_question=case["pending_question"],
            expected_response_kind=case["expected_response_kind"],
            current_step=0,
        )
    return GenerationRequest(
        request_id=item["id"],
        mode="interactive_chat",
        condition="E1",
        question=question,
        evidence=[
            EvidenceSnapshot.model_validate(
                {
                    **{
                        key: value
                        for key, value in evidence.items()
                        if key in EvidenceSnapshot.model_fields
                    },
                    "context_order": index,
                }
            ).model_dump()
            for index, evidence in enumerate(retrieval["evidence"], 1)
        ]
        if item["answer_mode"] == "textbook"
        else [],
        source_map=retrieval["source_map"] if item["answer_mode"] == "textbook" else {},
        history=history,
        prepared_query={
            **retrieval["prepared_query"],
            "original_message": question,
            "needs_clarification": False,
        },
        answer_mode=item["answer_mode"],
        config=ModelConfig.from_dict(manifest["model_config"]),
        checker_config=ModelConfig.from_dict(manifest["checker_config"]),
        enhancement_version="learning_enhancement_v1",
        attribution_strategy="posthoc_spans",
        teaching_condition="T2",
        teaching_context=context,
        reliability_policy=item["policy"],
        generation_context_policy="complementary_context_v2",
        repair_policy="cause_specific_repair_v2",
    )


def run_one(item, manifest, output, key):
    path = output / "outcomes" / f"{item['id']}.json"
    if path.exists():
        return read(path)
    if source_snapshot() != manifest["source_hashes"]:
        raise ValueError("Frozen generation sources changed before execution")
    event_path = output / "attempt-events" / f"{item['id']}.jsonl"
    if event_path.exists():
        record = {
            "schedule": item,
            "started_at": now(),
            "outcome": None,
            "error": "INTERRUPTED_ATTEMPT_REQUIRES_RECONCILIATION",
            "paid_call_status": "unknown_preserved_events",
            "elapsed_ms": None,
        }
        write(path, record)
        return record
    event_path.parent.mkdir(parents=True, exist_ok=True)
    request = build_request(item, manifest)
    start = time.perf_counter()
    started = now()

    def event(value):
        with event_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"recorded_at": now(), **value}, ensure_ascii=False) + "\n")
            stream.flush()

    try:
        outcome = GenerationService(api_key=key, checker_api_key=key).generate(
            request, RequestBudget(**manifest["budget"]), on_attempt=event
        )
        record = {
            "schedule": item,
            "started_at": started,
            "request": asdict(request),
            "outcome": outcome.to_dict(),
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
            "error": None,
            "source_unchanged": source_snapshot() == manifest["source_hashes"],
        }
    except Exception as exc:
        record = {
            "schedule": item,
            "started_at": started,
            "outcome": None,
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
            "error": type(exc).__name__,
            "source_unchanged": source_snapshot() == manifest["source_hashes"],
        }
    write(path, record)
    print(
        json.dumps(
            {
                "id": item["id"],
                "policy": item["policy"],
                "stage": item["stage"],
                "published": bool((record.get("outcome") or {}).get("response")),
                "error": record["error"]
                or ((record.get("outcome") or {}).get("error") or {}).get("code"),
            }
        ),
        flush=True,
    )
    return record


def execute(output):
    manifest = read(output / "frozen-study.json")
    receipt = read(output / "freeze-receipt.json")
    if sha((output / "frozen-study.json").read_bytes()) != receipt["frozen_study_sha256"]:
        raise ValueError("Frozen study changed")
    settings = Settings()
    if not settings.llm_api_key:
        raise ValueError("Configured local LLM_API_KEY is unavailable")
    key = settings.llm_api_key
    with ThreadPoolExecutor(max_workers=manifest["concurrency"]) as pool:
        pending = [
            pool.submit(run_one, item, manifest, output, key) for item in manifest["schedule"]
        ]
        for future in as_completed(pending):
            future.result()
    summarize(output)


def distribution(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return {"n": 0, "p50_ms": None, "p95_ms": None}
    position = (len(values) - 1) * 0.95
    a = int(position)
    return {
        "n": len(values),
        "p50_ms": statistics.median(values),
        "p95_ms": values[a] + (values[min(a + 1, len(values) - 1)] - values[a]) * (position - a),
    }


def endpoints(record):
    item, outcome = record["schedule"], record.get("outcome") or {}
    response = outcome.get("response") or {}
    published = bool(response) and not outcome.get("error") and not record.get("error")
    answered = published and response.get("response_type") == "answer"
    mode_ok = (
        (
            not response.get("citations")
            and all(
                c.get("support", {}).get("status") is None
                for c in outcome.get("attribution", {}).get("claims", [])
            )
        )
        if item["answer_mode"] == "general_knowledge"
        else True
    )
    hint_ok = not response.get("short_answer") if item["stage"] != "direct" else True
    evaluation = outcome.get("teaching_context", {}).get("learner_attempt_evaluation")
    attempt = (
        bool(
            evaluation
            and evaluation["feedback"] in response.get("answer_text", "")
            and outcome.get("teaching_context", {}).get("help_level") == 1
        )
        if item["stage"] == "learner_attempt"
        else None
    )
    return {
        "published": published,
        "answered": answered,
        "mode_metadata_ok": bool(published and mode_ok),
        "hint_shape_ok": bool(published and hint_ok),
        "attempt_workflow_supported": attempt,
        "automatic_contract_success": bool(
            answered and mode_ok and hint_ok and (attempt if attempt is not None else True)
        ),
    }


def summarize(output):
    manifest = read(output / "frozen-study.json")
    records = [
        read(output / "outcomes" / f"{item['id']}.json")
        for item in manifest["schedule"]
        if (output / "outcomes" / f"{item['id']}.json").exists()
    ]
    aggregate = []
    for policy in ["evidence_reliability_v2", "evidence_reliability_v3"]:
        for mode in ["textbook", "general_knowledge"]:
            for stage in ["direct", "first_hint", "another_hint", "learner_attempt"]:
                rows = [
                    r
                    for r in records
                    if r["schedule"]["policy"] == policy
                    and r["schedule"]["answer_mode"] == mode
                    and r["schedule"]["stage"] == stage
                ]
                aggregate.append(
                    {
                        "policy": policy,
                        "answer_mode": mode,
                        "stage": stage,
                        "planned": 8,
                        "terminal": len(rows),
                        **{
                            k: sum(bool(endpoints(r)[k]) for r in rows)
                            for k in [
                                "published",
                                "answered",
                                "mode_metadata_ok",
                                "hint_shape_ok",
                                "attempt_workflow_supported",
                                "automatic_contract_success",
                            ]
                        },
                        "latency_all": distribution([r["elapsed_ms"] for r in rows]),
                        "latency_published": distribution(
                            [r["elapsed_ms"] for r in rows if endpoints(r)["published"]]
                        ),
                        "latency_failed": distribution(
                            [r["elapsed_ms"] for r in rows if not endpoints(r)["published"]]
                        ),
                    }
                )
    attempts = [a for r in records for a in (r.get("outcome") or {}).get("attempts", [])]
    token_names = [
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cache_hit_input_tokens",
        "cache_miss_input_tokens",
    ]
    report = {
        "schema": "teaching_contract_public_results_v1",
        "created_at": now(),
        "frozen_study_sha256": sha((output / "frozen-study.json").read_bytes()),
        "planned": len(manifest["schedule"]),
        "terminal": len(records),
        "groups": aggregate,
        "errors": dict(
            Counter(
                r.get("error") or ((r.get("outcome") or {}).get("error") or {}).get("code", "none")
                for r in records
            )
        ),
        "attempt_count": len(attempts),
        "request_submitted": dict(Counter(str(a.get("request_submitted")) for a in attempts)),
        "usage": {
            name: {
                "known_sum": sum(a.get("usage", {}).get(name) or 0 for a in attempts),
                "missing_attempts": sum(a.get("usage", {}).get(name) is None for a in attempts),
            }
            for name in token_names
        },
        "generation_source_unchanged": all(r.get("source_unchanged", False) for r in records),
        "human_ratings": 0,
        "monetary_cost": None,
        "interpretation": manifest["interpretation"],
        "latency_scope": "Direct generation/check/repair wall time including local prompt/tokenization/source mapping, excluding retrieval, database, queue, publication and browser. Calls run with concurrency two; no product end-to-end speedup inference.",
        "cost_scope": manifest["cost_scope"],
    }
    write(output / "public-results.json", report)
    export_reviews(output, manifest, records)
    print(
        json.dumps(
            {
                "status": "terminal",
                "planned": report["planned"],
                "terminal": report["terminal"],
                "attempts": len(attempts),
                "errors": report["errors"],
            }
        ),
        flush=True,
    )


def export_reviews(output, manifest, records):
    target = output / "blind-review"
    if target.exists():
        return
    target.mkdir()
    ordered = list(records)
    random.Random(570327).shuffle(ordered)
    mapping, packets, blanks = [], [], []
    for n, record in enumerate(ordered, 1):
        blind_id = f"R{n:03}"
        item = record["schedule"]
        case = next(c for c in manifest["cases"] if c["id"] == item["case_id"])
        outcome = record.get("outcome") or {}
        mapping.append({"blind_id": blind_id, "condition": item})
        packets.append(
            {
                "blind_id": blind_id,
                "question": case["question"],
                "learner_turn": build_request(item, manifest).question,
                "answer_mode": item["answer_mode"],
                "requested_help": item["stage"],
                "fixed_prior_question": case["pending_question"]
                if item["stage"] in {"another_hint", "learner_attempt"}
                else None,
                "response": outcome.get("response"),
                "delivered_projection": outcome.get("delivered_projection"),
                "reference_source_anchors": case["source_anchors"],
                "required_points": case["required_points"],
                "forbidden_inferences": case["forbidden_inferences"],
                "outcome_available": endpoints(record)["published"],
            }
        )
        blanks.append(
            {
                "blind_id": blind_id,
                "factual_correctness_0_3": "",
                "source_support_0_3": "",
                "help_scope_0_3": "",
                "specific_usefulness_0_3": "",
                "attempt_feedback_0_3": "",
                "hint_leakage_yes_no": "",
                "notes": "",
            }
        )
    write(target / "coordinator-mapping-private.json", mapping)
    write(target / "review-packets.json", packets)
    for reviewer in ["reviewer-1", "reviewer-2"]:
        with (target / f"{reviewer}.csv").open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(blanks[0]))
            writer.writeheader()
            writer.writerows(blanks)
    (target / "SCORING_GUIDE.md").write_text(
        "# Independent blind review\n\nUse only review-packets.json and your assigned blank CSV. Keep the coordinator mapping private until both reviews are submitted. Rate each delivered response: 0 = incorrect or unusable; 1 = major omissions/errors; 2 = mostly adequate with a material limitation; 3 = fully appropriate for this exact request. Source support concerns textbook claims; leave it blank for general knowledge and describe this in notes. Evaluate hint scope from the visible answer and citation view together with fixed prior content. Mark hint leakage yes/no only for hints. Rate attempt feedback only for learner-attempt turns. Leave absent-response scores blank and note no delivered response. Do not turn a provider failure into a semantic score. These are independent human assessments; the online checker is not the reviewer. Preserve all rows and blind IDs. The study has no measured learning-gain endpoint.\n",
        encoding="utf-8",
    )


def import_reviews(output, reviews, result_path):
    """Validate actual submitted ratings without manufacturing missing scores."""
    if result_path.exists():
        raise ValueError("Preserve previous rating imports; choose a new result path")
    packets = {r["blind_id"]: r for r in read(output / "blind-review/review-packets.json")}
    dimensions = [
        "factual_correctness_0_3",
        "source_support_0_3",
        "help_scope_0_3",
        "specific_usefulness_0_3",
        "attempt_feedback_0_3",
    ]
    fields = ["blind_id", *dimensions, "hint_leakage_yes_no", "notes"]
    imported = []
    for path in reviews:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != fields:
                raise ValueError("Review columns differ from the blank form")
            rows = list(reader)
        if len(rows) != len(packets) or {r["blind_id"] for r in rows} != set(packets):
            raise ValueError("Every blinded ID must occur exactly once")
        for row in rows:
            packet = packets[row["blind_id"]]
            for dim in dimensions:
                if row[dim] not in {"", "0", "1", "2", "3"}:
                    raise ValueError("Scores must be blank or integer 0-3")
            if row["hint_leakage_yes_no"] not in {"", "yes", "no"}:
                raise ValueError("Hint leakage must be blank, yes or no")
            if not packet["outcome_available"] and any(
                row[d] for d in dimensions + ["hint_leakage_yes_no"]
            ):
                raise ValueError("Absent responses retain blank semantic scores")
            if packet["answer_mode"] == "general_knowledge" and row["source_support_0_3"]:
                raise ValueError("Textbook support is not applicable in general knowledge")
            if packet["requested_help"] != "learner_attempt" and row["attempt_feedback_0_3"]:
                raise ValueError("Attempt feedback score is only for learner-attempt rows")
            if packet["requested_help"] == "direct" and row["hint_leakage_yes_no"]:
                raise ValueError("Hint leakage is not applicable to direct answers")
        imported.append(
            {
                "reviewer_file": path.name,
                "sha256": sha(path.read_bytes()),
                "scored_rows": sum(any(row[d] for d in dimensions) for row in rows),
                "rows": [
                    {
                        k: (int(v) if k in dimensions and v else None if k in dimensions else v)
                        for k, v in row.items()
                    }
                    for row in rows
                ],
            }
        )
    write(
        result_path,
        {
            "schema": "independent_teaching_contract_review_import_v1",
            "imported_at": now(),
            "frozen_study_sha256": sha((output / "frozen-study.json").read_bytes()),
            "reviewers": imported,
            "interpretation": "Only actual nonblank submitted scores are counted; this import does not change automatic results or fill missing ratings.",
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "run", "summarize", "import-reviews"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--reviews", type=Path, nargs="+")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        if not args.source or not args.bundle:
            raise ValueError("Freeze requires source and official bundle")
        freeze(args.source, args.bundle, args.output)
    elif args.action == "run":
        execute(args.output)
    elif args.action == "summarize":
        summarize(args.output)
    else:
        if not args.reviews or not args.result:
            raise ValueError("Review import requires --reviews and a new --result file")
        import_reviews(args.output, args.reviews, args.result)


if __name__ == "__main__":
    main()
