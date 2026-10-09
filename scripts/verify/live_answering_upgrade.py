"""Record live HTTP/worker questions against the active official corpus and model."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text

from app.core.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve previous evidence; select a new output path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(Settings().database_url)
    client = httpx.Client(base_url=args.base_url, timeout=75)
    result = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "scope": "Live model, real HTTP and durable worker, real four-book E5/pgvector retrieval. Automated checks cover response state, provenance and accounting; semantic correctness requires separate review.",
        "cases": [],
    }

    def save():
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
        )

    def call(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"API {method} {path}: HTTP {response.status_code}")
        return response.json()["data"]

    def login(email, password):
        token = call("POST", "/auth/login", json={"email": email, "password": password})[
            "access_token"
        ]
        client.headers["Authorization"] = "Bearer " + token

    def ask(question, expected="answer", session=None, group="core", use_profile=True):
        if session is None:
            session = call("POST", "/sessions", json={"title": "Live verification: " + group})["id"]
        started = time.monotonic()
        row = {
            "question": question,
            "expected_response_type": expected,
            "group": group,
            "session_id": session,
            "checks": {},
        }
        result["cases"].append(row)
        receipt = call(
            "POST",
            f"/sessions/{session}/messages",
            json={"content": question, "use_profile": use_profile},
            headers={"Idempotency-Key": uuid4().hex},
        )
        row["receipt"] = receipt
        save()
        deadline = time.monotonic() + 210
        while time.monotonic() < deadline:
            job = call("GET", "/jobs/" + receipt["job_id"])
            if job["state"] in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(0.4)
        row["job"] = job
        row["elapsed_seconds"] = round(time.monotonic() - started, 3)
        row["checks"]["job_succeeded"] = job["state"] == "succeeded"
        if job.get("answer_id"):
            answer = call("GET", "/answers/" + job["answer_id"])
            row["answer"] = answer
            row["checks"]["live_mode"] = answer["model_mode"] == "live"
            row["checks"]["expected_response_type"] = (
                answer["response"]["response_type"] == expected
            )
            cited = []
            for evidence_id in answer["response"]["citations"]:
                evidence = call("GET", f"/answers/{answer['id']}/evidence/{evidence_id}")
                with engine.connect() as db:
                    stored = (
                        db.execute(
                            text(
                                "SELECT c.text,c.text_hash,c.pages,c.section,d.title FROM chunks c JOIN documents d ON d.id=c.document_id WHERE c.id=:id"
                            ),
                            {"id": evidence["chunk_id"]},
                        )
                        .mappings()
                        .one()
                    )
                checks = {
                    "text_hash_matches": hashlib.sha256(evidence["text"].encode()).hexdigest()
                    == evidence["text_hash"],
                    "matches_stored_original_chunk": evidence["text"] == stored["text"]
                    and evidence["text_hash"] == stored["text_hash"],
                    "official_source": evidence["source_url"].startswith(
                        "https://assets.openstax.org/"
                    ),
                    "pages_match_chunk": evidence["pages"] == stored["pages"]
                    and bool(evidence["pages"]),
                }
                cited.append({"evidence": evidence, "checks": checks})
            row["cited_sources"] = cited
            row["checks"]["citation_provenance"] = all(all(v["checks"].values()) for v in cited)
            row["checks"]["answer_has_actual_citation"] = (
                bool(cited) if expected == "answer" else True
            )
        with engine.connect() as db:
            stored = (
                db.execute(
                    text(
                        "SELECT trace,budget,command,release_id FROM answer_requests WHERE id=:id"
                    ),
                    {"id": receipt["request_id"]},
                )
                .mappings()
                .one()
            )
            row["trace"] = {
                k: v
                for k, v in stored["trace"].items()
                if k
                in {
                    "prepared_query",
                    "evidence_selection",
                    "token_budget",
                    "retrieval_candidates",
                    "generation_token_budget",
                }
            }
            row["budget"] = stored["budget"]
            row["model_configuration"] = stored["command"].get("model_config")
            row["release_id"] = stored["release_id"]
            attempts = db.execute(
                text(
                    "SELECT a.payload FROM attempts a JOIN jobs j ON j.id=a.job_id WHERE j.request_id=:id ORDER BY a.sequence"
                ),
                {"id": receipt["request_id"]},
            ).scalars()
            row["provider_attempts"] = [
                {
                    k: v
                    for k, v in item.items()
                    if k
                    in {
                        "stage",
                        "phase",
                        "latency_ms",
                        "usage",
                        "error",
                        "http_status",
                        "finish_reason",
                    }
                }
                for item in attempts
            ]
        row["passed_automated_checks"] = all(row["checks"].values())
        save()
        print(
            json.dumps(
                {
                    "question": question,
                    "state": job["state"],
                    "response_type": row.get("answer", {}).get("response", {}).get("response_type"),
                    "counts": row["trace"].get("evidence_selection"),
                    "passed": row["passed_automated_checks"],
                }
            ),
            flush=True,
        )
        return session

    try:
        login("admin@example.com", "Passw0rd!")
        state = call("GET", "/admin/model-configurations")
        active = next(
            (x for x in state["items"] if x["id"] == state["active_configuration_id"]), None
        )
        if not active or active["config"]["provider"] == "mock":
            raise ValueError("Activate a tested live model before this verifier")
        result["active_model"] = active
        email = "live-check-" + uuid4().hex[:12] + "@example.com"
        password = uuid4().hex
        user = call(
            "POST",
            "/admin/users",
            json={
                "email": email,
                "full_name": "Live verification learner",
                "password": password,
                "role": "student",
            },
        )
        result["isolated_learner_id"] = user["id"]
        login(email, password)
        photosynthesis = ask(
            "What is photosynthesis, and how do the light-dependent reactions and Calvin cycle work together?"
        )
        if not args.smoke:
            ask(
                "Why does it need water, and where does the released oxygen come from?",
                session=photosynthesis,
                group="follow_up",
                use_profile=False,
            )
            ask("Explain that more simply.", session=photosynthesis, group="simplification")
            ask(
                "Give an example of how the plant uses the sugar it produces.",
                session=photosynthesis,
                group="expansion",
            )
            for question in [
                "How are diffusion, osmosis and active transport different? Explain the role of a membrane and energy.",
                "How do enzymes speed up reactions without changing the overall free-energy change?",
                "What happens to gas pressure when volume decreases at constant temperature, and why?",
                "Why does a buffer resist a pH change after a small amount of acid is added?",
                "How do the kidneys help maintain blood volume and blood pressure?",
                "How do the nervous and endocrine systems work together to maintain homeostasis?",
                "How do mitosis and meiosis differ in chromosome number and biological purpose?",
                "How does natural selection change a population over generations?",
            ]:
                ask(question)
            for question, expected in [
                ("How do I configure Kubernetes ingress TLS certificates?", "refusal"),
                ("What is today's exchange rate between the yen and the euro?", "refusal"),
                ("Why does it do that?", "clarification"),
                ("Hello", "social"),
            ]:
                ask(question, expected, group="negative_and_ambiguity")
            for level, style in [
                ("beginner", "concise"),
                ("intermediate", "detailed"),
                ("advanced", "detailed"),
            ]:
                current = call("GET", "/profiles/me")
                call(
                    "PUT",
                    "/profiles/me",
                    json={
                        "version": current["version"],
                        "level": level,
                        "style": style,
                        "language": "en",
                        "topics": [],
                    },
                )
                ask(
                    "Explain how a buffer resists changes in pH.",
                    group="profile_" + level + "_" + style,
                )
            ask(
                "Explain osmosis in detail, including membrane permeability, concentration gradients, and an example involving a cell.",
                group="detailed_request",
            )
        result["automated_passed"] = sum(x["passed_automated_checks"] for x in result["cases"])
        result["planned_cases"] = 1 if args.smoke else 20
        result["status"] = (
            "passed_automated_checks"
            if result["automated_passed"] == len(result["cases"]) == result["planned_cases"]
            else "failed_or_partial"
        )
        result["independent_human_review"] = "Not performed; these records are review inputs."
        save()
    except Exception as exc:
        result["status"] = "execution_failed"
        result["failure"] = {"type": type(exc).__name__, "message": str(exc)[:300]}
        save()
        raise
    finally:
        client.close()
        engine.dispose()
    if result["status"] != "passed_automated_checks":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
