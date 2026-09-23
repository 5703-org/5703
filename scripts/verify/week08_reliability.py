"""Freeze source-bound cases and record real HTTP reliability outcomes without labels."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text

from app.core.config import Settings
from evaluation.reliability.catalogue import inventory, validate_frozen_plan


ROOT = Path(__file__).resolve().parents[2]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def freeze(path):
    if path.exists():
        raise ValueError("Preserve the frozen question set; select a new path")
    catalogue = inventory()
    topics, sections = catalogue["topics"], catalogue["sections"]
    engine = create_engine(Settings().database_url)
    with engine.connect() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        release = db.execute(text("SELECT release_id FROM active_corpus WHERE id=1")).scalar_one()
        corpus = (
            db.execute(
                text(
                    "SELECT c.id,c.processing_id,c.text,c.text_hash,c.section,c.pages,c.spans,d.title,d.source_url,d.edition,d.license FROM release_chunks r JOIN chunks c ON c.id=r.chunk_id JOIN documents d ON d.id=c.document_id WHERE r.release_id=:id ORDER BY c.id"
                ),
                {"id": release},
            )
            .mappings()
            .all()
        )
        anchors = {}
        for key, book, anchor, question, point, forbidden in topics:
            matching = [
                r
                for r in corpus
                if r["title"] == book and any(section in r["section"] for section in sections[key])
            ]
            if not matching:
                raise ValueError("Source anchor unavailable: " + key)
            terms = set(re.findall(r"[a-z]{4,}", (question + " " + point).lower())) - {
                "what",
                "does",
                "that",
                "with",
                "from",
                "when",
                "have",
            }
            matching.sort(
                key=lambda r: (
                    -len(terms & set(re.findall(r"[a-z]{4,}", r["text"].lower())))
                    + (4 if "LEARNING OBJECTIVES" in r["text"] else 0),
                    r["id"],
                )
            )
            selected = matching[:2]
            for row in selected:
                if sha(row["text"]) != row["text_hash"] or not row["pages"]:
                    raise ValueError("Source identity or page locator invalid")
            anchors[key] = {
                "anchor_phrase": anchor,
                "required_point": point,
                "forbidden_inference": forbidden,
                "section_constraints": sections[key],
                "source_binding_method": "explicit textbook section, ranked by question and required-point terms; AI-authored review target",
                "independent_relevance_review": None,
                "passages": [dict(row) for row in selected],
            }
        rows = catalogue["cases"]
        for row in rows:
            row["source_topics"] = row.pop("topics")
            row["source_requirement"] = (
                "review_bound_passages"
                if row["source_topics"]
                else "no_positive_textbook_anchor_expected"
            )
        result = {
            "version": "week08-reliability-120-v3",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "corpus_release_id": release,
            "active_vectors": len(corpus),
            "author": "Codex",
            "independent_reviewer": None,
            "split_policy": "SHA256 knowledge group modulo 3; related variants share a group and split before scoring",
            "scope": "Prespecified developer cases and source review targets; no independent qrels or human ratings are inferred",
            "counts": dict(Counter(r["category"] for r in rows)),
            "split_counts": dict(Counter(r["split"] for r in rows)),
            "source_topics": anchors,
            "cases": rows,
        }
        validate_frozen_plan(result)
        save(path, result)
    engine.dispose()
    print(
        json.dumps(
            {
                "path": str(path),
                "cases": len(rows),
                "source_topics": len(anchors),
                "counts": result["counts"],
            }
        )
    )


def teaching_cases():
    rows = []
    for topic, question in [
        ("photosynthesis", "How do the light reactions and Calvin cycle work together?"),
        ("buffers", "Why does a buffer resist a small addition of acid?"),
        ("neurons", "Explain how ion channels produce an action potential."),
    ]:
        for level in ("beginner", "intermediate", "advanced"):
            rows.append({"question": question, "topic": topic, "level": level, "style": "detailed"})
    for topic, question, style in [
        (
            "gases",
            "Give me only one first hint, without solving: an ideal gas doubles its absolute temperature at constant volume; what happens to pressure?",
            "concise",
        ),
        (
            "enzymes",
            "Give me one hint to explain why an enzyme speeds up a reaction. Do not give the complete answer yet.",
            "concise",
        ),
        (
            "enzymes",
            "Why do enzymes increase the activation energy needed for a reaction?",
            "detailed",
        ),
        ("heart", "Why does every artery carry oxygen-rich blood?", "detailed"),
        (
            "osmosis",
            "Explain osmosis in detail with membrane permeability, water and solute gradients, conditions and one cell example.",
            "detailed",
        ),
    ]:
        rows.append({"question": question, "topic": topic, "level": "beginner", "style": style})
    return [
        {
            "id": f"W8-T{i:02}",
            "category": "teaching",
            "split": "review",
            "history": [],
            "expected_behavior": "answer",
            **row,
        }
        for i, row in enumerate(rows, 1)
    ]


def robustness_cases():
    questions = [
        "How does photosyntehsis turn light into stored chemical energy?",
        "How do enzimes lower the activation barrier?",
        "What is osmozis across a selectively permeable membrane?",
        "At constant temperature, why does doubling pressure NOT double an ideal gas's volume?",
        "Compare DNA and RNA; focus on their sugars rather than protein synthesis.",
        "Explain why an enzyme changes the rate but not the reaction's overall free-energy change.",
    ]
    return [
        {
            "id": f"W8-X{i:02}",
            "category": "wording_constraints",
            "split": "review",
            "history": [],
            "question": question,
            "expected_behavior": "answer",
        }
        for i, question in enumerate(questions, 1)
    ]


def run(path, output, base_url, limit=None, teaching=False, robustness=False):
    if output.exists():
        raise ValueError("Preserve earlier results; select a new output path")
    plan = json.loads(path.read_text(encoding="utf-8"))
    report = {
        "version": "week08-http-reliability-v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "plan_version": plan["version"],
        "scope": "Actual HTTP, durable worker and configured model; checks are structural/provenance/expected state. Correctness, citation support and teaching ratings require separate review.",
        "independent_review": None,
        "cases": [],
        "status": "running",
    }
    engine = create_engine(Settings().database_url)
    client = httpx.Client(base_url=base_url, timeout=75)

    def call(method, route, **kwargs):
        response = client.request(method, route, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"API {method} {route}: HTTP {response.status_code}")
        return response.json()["data"]

    def ask(session, question, answer_mode="textbook"):
        start = time.monotonic()
        receipt = call(
            "POST",
            f"/sessions/{session}/messages",
            json={"content": question, "use_profile": True, "answer_mode": answer_mode},
            headers={"Idempotency-Key": uuid4().hex},
        )
        until = time.monotonic() + 240
        while True:
            job = call("GET", "/jobs/" + receipt["job_id"])
            if job["state"] in {"succeeded", "failed", "cancelled"} or time.monotonic() >= until:
                break
            time.sleep(0.5)
        value = {"receipt": receipt, "job": job, "seconds": round(time.monotonic() - start, 3)}
        if job.get("answer_id"):
            answer = call("GET", "/answers/" + job["answer_id"])
            value["answer"] = answer
            sources = []
            for eid in answer["response"]["citations"]:
                source = call("GET", f"/answers/{answer['id']}/evidence/{eid}")
                sources.append(source)
            value["cited_sources"] = sources
        with engine.connect() as db:
            stored = (
                db.execute(
                    text("SELECT trace,budget,release_id FROM answer_requests WHERE id=:id"),
                    {"id": receipt["request_id"]},
                )
                .mappings()
                .one()
            )
            value["trace"] = {
                k: v
                for k, v in stored["trace"].items()
                if k
                in {
                    "prepared_query",
                    "understanding",
                    "evidence_selection",
                    "token_budget",
                    "generation_token_budget",
                    "retrieval_candidates",
                    "relevance",
                    "retrieval_runtime",
                    "evidence_coverage",
                    "citation_audit",
                    "teaching_plan",
                    "retrieval_trace",
                    "retrieval_execution",
                    "evidence_strategy",
                    "local_model_device",
                    "relevance_screening",
                    "answer_mode",
                    "answer_provenance",
                    "source_provenance",
                    "facet_fallback",
                }
            }
            value["budget"] = stored["budget"]
            value["release_id"] = stored["release_id"]
        return value

    try:
        token = call(
            "POST", "/auth/login", json={"email": "admin@example.com", "password": "Passw0rd!"}
        )["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        state = call("GET", "/admin/model-configurations")
        active = next(
            (r for r in state["items"] if r["id"] == state["active_configuration_id"]), None
        )
        if not active or active["config"]["provider"] == "mock":
            raise ValueError("An enabled live provider is required")
        report["active_model"] = active
        email, password = "week08-" + uuid4().hex[:12] + "@example.com", uuid4().hex
        call(
            "POST",
            "/admin/users",
            json={
                "email": email,
                "full_name": "Week 8 verification learner",
                "password": password,
                "role": "student",
            },
        )
        token = call("POST", "/auth/login", json={"email": email, "password": password})[
            "access_token"
        ]
        client.headers["Authorization"] = "Bearer " + token
        scheduled = (
            teaching_cases()
            if teaching
            else [c for c in plan["cases"] if c.get("execution") != "isolated_fault_test"]
        )
        if robustness:
            scheduled = robustness_cases()
        if limit:
            scheduled = scheduled[:limit]
        report["scheduled_ids"] = [r["id"] for r in scheduled]
        if teaching:
            report["teaching_plan"] = scheduled
        if robustness:
            report["robustness_plan"] = scheduled
        report["isolated_fault_ids"] = [
            r["id"] for r in plan["cases"] if r.get("execution") == "isolated_fault_test"
        ]
        save(output, report)
        for case in scheduled:
            row = {
                "id": case["id"],
                "category": case["category"],
                "split": case["split"],
                "question": case["question"],
                "expected": case["expected_behavior"],
                "history_runs": [],
                "human_ratings": None,
            }
            report["cases"].append(row)
            try:
                if teaching:
                    current = call("GET", "/profiles/me")
                    profile = {
                        "version": current["version"],
                        "level": case["level"],
                        "style": case["style"],
                        "language": "en",
                        "topics": [],
                    }
                    row["configured_profile"] = call("PUT", "/profiles/me", json=profile)
                session = call("POST", "/sessions", json={"title": "Week 8 " + case["id"]})["id"]
                for prior in case["history"]:
                    if prior["role"] == "user":
                        row["history_runs"].append(ask(session, prior["content"]))
                row.update(ask(session, case["question"], case.get("answer_mode", "textbook")))
                response = row.get("answer", {}).get("response", {})
                actual = response.get("response_type")
                row["checks"] = {
                    "terminal_success": row["job"]["state"] == "succeeded",
                    "expected_response_type": actual
                    == ("answer" if row["expected"] == "partial_answer" else row["expected"]),
                    "live_configuration": row.get("answer", {}).get("model_mode") == "live",
                    "source_hashes": all(
                        sha(s["text"]) == s["text_hash"] and bool(s["pages"])
                        for s in row.get("cited_sources", [])
                    ),
                    "release_matches_plan": row.get("release_id") == plan["corpus_release_id"],
                }
                row["passed_automated_checks"] = all(row["checks"].values())
                row["review_required"] = [
                    "factual_correctness",
                    "coverage",
                    "citation_support",
                    "teaching_quality",
                ]
                if row["expected"] == "partial_answer":
                    row["review_required"].append("explicit_uncovered_part")
            except Exception as exc:
                row["error"] = {"type": type(exc).__name__, "message": str(exc)[:300]}
                row["passed_automated_checks"] = False
            save(output, report)
            print(
                json.dumps(
                    {
                        "id": row["id"],
                        "expected": row["expected"],
                        "actual": row.get("answer", {}).get("response", {}).get("response_type"),
                        "passed": row["passed_automated_checks"],
                        "seconds": row.get("seconds"),
                    }
                ),
                flush=True,
            )
        report["status"] = "completed"
        report["automated_passed"] = sum(r["passed_automated_checks"] for r in report["cases"])
        report["automated_failed"] = len(report["cases"]) - report["automated_passed"]
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save(output, report)
    finally:
        client.close()
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["freeze", "run", "teaching", "robustness"])
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.mode == "freeze":
        freeze(args.plan)
    elif args.output:
        run(
            args.plan,
            args.output,
            args.base_url,
            args.limit,
            args.mode == "teaching",
            args.mode == "robustness",
        )
    else:
        parser.error("run requires --output")


if __name__ == "__main__":
    main()
