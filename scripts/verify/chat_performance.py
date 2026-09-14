"""Measure a small scheduled two-session chat workload with the real local corpus."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
from threading import Barrier
import time
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text
from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = (
    (
        "What is photosynthesis?",
        "Why does it need light?",
        "Explain that more simply",
        "What is osmosis?",
    ),
    (
        "What is an atom?",
        "What is a chemical bond?",
        "What is an acid?",
        "What is a catalyst?",
    ),
)


def distribution(values):
    values = sorted(values)
    if not values:
        return {"n": 0, "p50": None, "p95": None}

    def percentile(fraction):
        position = (len(values) - 1) * fraction
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 3)

    return {
        "n": len(values),
        "p50": percentile(0.5),
        "p95": percentile(0.95),
        "min": min(values),
        "max": max(values),
    }


def resources():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        gpu = result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        gpu = None
    return {"observed_at": datetime.now(timezone.utc).isoformat(), "gpu_csv": gpu}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("Choose a new result path and preserve earlier attempts")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(Settings().database_url)
    with engine.connect() as db:
        release = db.scalar(text("SELECT release_id FROM active_corpus WHERE id=1"))
        count = db.scalar(
            text("SELECT count(*) FROM release_chunks WHERE release_id=:release"),
            {"release": release},
        )
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "scope": "Actual HTTP/worker/E5/PostgreSQL chat workload; explicitly mock answers; descriptive local measurements, not a service SLA or semantic evaluation.",
        "corpus_release_id": release,
        "release_vector_count": count,
        "answer_model_mode": "mock",
        "concurrent_sessions": 2,
        "answer_workers": 1,
        "scheduled_count": 8,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "resources_before": resources(),
        "rows": [
            {
                "session_index": session,
                "turn_index": turn,
                "question": question,
                "status": "pending",
            }
            for turn in range(4)
            for session, questions in enumerate(QUESTIONS)
            for question in [questions[turn]]
        ],
        "cost": None,
        "cost_reason": "No paid answering provider invoked; local hardware cost not measured.",
        "percentiles": "Linear interpolation between ordered observations; all successful terminal response types retained, including refusals.",
        "timing_definitions": {
            "preparation_ms": "Worker loading, deterministic query preparation and evidence assembly before generation, excluding actual retrieval; excludes enqueue/HTTP time.",
            "query_preparation_ms": "Measured deterministic query preparation subset of preparation_ms.",
            "retrieval_ms": "Actual RetrieverPort duration including source integrity checks, local query encoding and PostgreSQL search; zero when intentionally bypassed or evidence reused.",
            "generation_wall_ms": "Measured generation-service wall duration including local mock delay, prompt formatting, callbacks and validation.",
            "generation_ms": "Sum of adapter-measured attempt computation durations; the local mock observations are 0-1 ms. This excludes generation-service work outside the adapter and is not provider token usage.",
            "total_ms": "Worker execution through the start of answer insertion; final commit and queue wait excluded.",
            "end_to_end_ms": "Before submission through observed terminal job and answer fetch, including queue wait and 200ms polling resolution.",
        },
    }

    def save():
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")

    save()
    clients = []
    sessions = []
    for index in range(2):
        client = httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=30)
        login = client.post(
            "/auth/login", json={"email": "student2@example.com", "password": "Passw0rd!"}
        )
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["data"]["access_token"]
        created = client.post(
            "/sessions", json={"title": f"Two-session timing observation {index + 1}"}
        )
        created.raise_for_status()
        sessions.append(created.json()["data"]["id"])
        clients.append(client)

    def run(row, barrier):
        client = clients[row["session_index"]]
        barrier.wait(timeout=10)
        started = time.perf_counter()
        try:
            response = client.post(
                f"/sessions/{sessions[row['session_index']]}/messages",
                json={"content": row["question"], "use_profile": False},
                headers={"Idempotency-Key": str(uuid4())},
            )
            response.raise_for_status()
            receipt = response.json()["data"]
            row["receipt"] = receipt
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                response = client.get("/jobs/" + receipt["job_id"])
                response.raise_for_status()
                job = response.json()["data"]
                if job["state"] in ("succeeded", "failed", "cancelled"):
                    break
                time.sleep(0.2)
            else:
                raise TimeoutError("No terminal job observed within 180 seconds")
            row["job_state"] = job["state"]
            if job["state"] != "succeeded":
                row.update(status="error", error=job.get("error"))
                return row
            response = client.get("/answers/" + job["answer_id"])
            response.raise_for_status()
            answer = response.json()["data"]
            row["end_to_end_ms"] = round((time.perf_counter() - started) * 1000, 3)
            with engine.connect() as db:
                persisted = (
                    db.execute(
                        text("SELECT release_id, trace FROM answer_requests WHERE id=:id"),
                        {"id": receipt["request_id"]},
                    )
                    .mappings()
                    .one()
                )
            if persisted["release_id"] != release or answer["model_mode"] != "mock":
                raise RuntimeError("Workload environment changed")
            if answer["timing"].get("timing_scope") != "worker_execution_before_answer_insert_v1":
                raise RuntimeError("Current measured stage timings are not available")
            row.update(
                status="succeeded",
                answer_id=answer["id"],
                response_type=answer["response"]["response_type"],
                answer_text_sha256=hashlib.sha256(
                    answer["response"]["answer_text"].encode()
                ).hexdigest(),
                timing=answer["timing"],
                usage=persisted["trace"].get("usage"),
            )
        except Exception as exc:
            row.update(status="error", error_type=type(exc).__name__)
        finally:
            row["observed_duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return row

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            for turn in range(4):
                barrier = Barrier(2)
                futures = [
                    pool.submit(run, row, barrier)
                    for row in report["rows"]
                    if row["turn_index"] == turn
                ]
                for future in futures:
                    future.result()
                save()
                print(f"Finished scheduled round {turn + 1}/4", flush=True)
        successful = [row for row in report["rows"] if row["status"] == "succeeded"]
        report["succeeded"] = len(successful)
        report["failed"] = len(report["rows"]) - len(successful)
        report["stage_ms"] = {
            name: distribution([row["timing"][name] for row in successful])
            for name in (
                "preparation_ms",
                "query_preparation_ms",
                "retrieval_ms",
                "generation_wall_ms",
                "generation_ms",
                "total_ms",
            )
        }
        report["end_to_end_ms"] = distribution([row["end_to_end_ms"] for row in successful])
        report["status"] = "completed" if len(successful) == 8 else "completed_with_errors"
    finally:
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        report["resources_after"] = resources()
        save()
        for client in clients:
            client.close()
        engine.dispose()
    print(
        json.dumps(
            {"status": report["status"], "scheduled": 8, "succeeded": report.get("succeeded")}
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
