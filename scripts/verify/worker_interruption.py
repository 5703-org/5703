"""Kill only an owned mock worker and recover its real PostgreSQL claim.

The generated database is isolated from the application's configured database.
The delayed child instruments only its local mock transport; all claim, budget,
publication, recovery and retry logic comes from the actual runtime.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "backend"))
STALE_SECONDS = 181  # The real Settings minimum; no backdated timestamps.
MOCK_DELAY_SECONDS = 30


def delayed_worker() -> None:
    from app.core.config import Settings
    from app.worker import main as worker_main
    from generation.adapters import LLMAdapter

    settings = Settings()
    database = make_url(settings.database_url).database or ""
    if (
        not re.fullmatch(r"cs30_drill_[0-9a-f]{12}", database)
        or settings.env != "test"
        or settings.model_mode != "mock"
        or settings.llm_provider != "mock"
    ):
        raise SystemExit("Delayed worker requires an isolated drill database and explicit mock.")
    original = LLMAdapter.generate

    def delayed(self, *args, **kwargs):
        assert self.config.provider == "mock"
        print("Entered local mock transport after persisted call reservation", flush=True)
        time.sleep(MOCK_DELAY_SECONDS)
        return original(self, *args, **kwargs)

    LLMAdapter.generate = delayed
    sys.argv = ["app.worker", "--once"]
    worker_main()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delayed-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.delayed_worker:
        delayed_worker()
        return

    from fastapi.testclient import TestClient
    from app.cli import seed
    from app.core.config import Settings
    from app.main import create_app
    from app.modules.answering.models import Answer, AnswerRequest, Attempt, Job, Message, Snapshot

    stamp = datetime.now(timezone.utc)
    output = (
        args.output
        or ROOT / "evidence/operations/worker-interruption" / stamp.strftime("%Y%m%dT%H%M%SZ")
    ).resolve()
    output.relative_to(ROOT / "evidence")
    output.mkdir(parents=True, exist_ok=False)
    storage = output / "storage"
    storage.mkdir()
    database = "cs30_drill_" + uuid4().hex[:12]
    server = make_url(
        os.environ.get(
            "TEST_DATABASE_SERVER",
            "postgresql+psycopg://learning:local-dev-database-only@127.0.0.1:55432",
        )
    )
    assert server.get_backend_name() == "postgresql"
    admin = create_engine(server.set(database="postgres"), isolation_level="AUTOCOMMIT")
    url = server.set(database=database).render_as_string(hide_password=False)
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(ROOT), str(ROOT / "backend")]),
        "PYTHONUNBUFFERED": "1",
        "APP_ENV": "test",
        "DATABASE_URL": url,
        "STORAGE_ROOT": str(storage),
        "MODEL_MODE": "mock",
        "LLM_PROVIDER": "mock",
        "LLM_API_BASE": "",
        "LLM_API_KEY": "",
        "LLM_MODEL": "authored-extractive-v1",
        "EMBEDDING_PROVIDER": "mock",
        "MOCK_DELAY_SECONDS": "0",
        "WORKER_STALE_SECONDS": str(STALE_SECONDS),
        "SECRET_KEY": "isolated-worker-drill-test-secret-at-least-thirty-two-characters",
    }
    report = {
        "status": "running",
        "started_at": stamp.isoformat(),
        "database": database,
        "model_mode": "mock",
        "external_provider_calls": 0,
        "stale_seconds": STALE_SECONDS,
        "injected_local_mock_transport_delay_seconds": MOCK_DELAY_SECONDS,
        "timestamp_backdating": False,
        "scope": "Actual separate worker processes and PostgreSQL; API requests use the actual ASGI app through TestClient. No main worker, corpus, database, Docker daemon or volume is modified.",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "commands": [],
    }

    def save(name, value):
        (output / name).write_text(
            json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8"
        )

    def run(label, arguments, timeout=45):
        command = [sys.executable, *arguments]
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
        (output / (label + ".log")).write_text(result.stdout, encoding="utf-8")
        report["commands"].append(
            {"label": label, "arguments": arguments, "exit_code": result.returncode}
        )
        assert result.returncode == 0, (label, result.returncode, result.stdout)
        return result.stdout

    app = client = child = child_log = None
    created = False
    try:
        with admin.connect() as db:
            db.execute(text(f"CREATE DATABASE {database}"))
        created = True
        run("migration", ["-m", "app.cli", "migrate"])
        settings = Settings(
            env="test",
            database_url=url,
            storage_root=str(storage),
            jwt_secret=environment["SECRET_KEY"],
            model_mode="mock",
            llm_provider="mock",
            mock_delay_seconds=0,
            worker_stale_seconds=STALE_SECONDS,
        )
        app = create_app(settings)
        factory = sessionmaker(bind=app.state.engine, expire_on_commit=False)
        with factory() as db:
            seed(db)
        client = TestClient(app)
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "student@example.com", "password": "Passw0rd!"},
        )
        assert login.status_code == 200
        headers = {"Authorization": "Bearer " + login.json()["data"]["access_token"]}

        def call(method, path, body=None, idempotent=False):
            extra = {"Idempotency-Key": str(uuid4())} if idempotent else {}
            response = client.request(
                method, "/api/v1" + path, json=body, headers={**headers, **extra}
            )
            assert response.is_success, (path, response.status_code, response.text)
            return response.json()["data"]

        def rows(db, model, condition):
            return [
                {column.name: getattr(row, column.name) for column in model.__table__.columns}
                for row in db.scalars(select(model).where(condition))
            ]

        session = call("POST", "/sessions", {"title": "Disposable process interruption drill"})
        first = call("POST", f"/sessions/{session['id']}/messages", {"content": "Hello"}, True)
        run("baseline_worker", ["-m", "app.worker", "--once"])
        assert call("GET", "/jobs/" + first["job_id"])["state"] == "succeeded"
        with factory() as db:
            prior_messages = rows(db, Message, Message.session_id == session["id"])
            prior_answers = rows(db, Answer, Answer.request_id == first["request_id"])

        receipt = call("POST", f"/sessions/{session['id']}/messages", {"content": "Hello"}, True)
        request_id, job_id = receipt["request_id"], receipt["job_id"]
        report.update({"session_id": session["id"], "request_id": request_id, "job_id": job_id})
        child_log = (output / "interrupted_worker.log").open("w", encoding="utf-8")
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--delayed-worker"],
            cwd=ROOT,
            env=environment,
            stdout=child_log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        report["owned_interrupted_worker_pid"] = child.pid
        deadline = time.monotonic() + 40
        while True:
            assert child.poll() is None, "Owned delayed worker exited before interception"
            with factory() as db:
                job = db.get(Job, job_id)
                request = db.get(AnswerRequest, request_id)
                attempts = rows(db, Attempt, Attempt.job_id == job_id)
                if job.state == "running" and attempts:
                    assert job.stage == "generating" and job.attempts == 1
                    assert request.budget["consumed_calls"] == 1
                    assert [a["payload"]["phase"] for a in attempts] == ["start"]
                    before = {
                        "job": rows(db, Job, Job.id == job_id)[0],
                        "request": rows(db, AnswerRequest, AnswerRequest.id == request_id)[0],
                        "attempts": attempts,
                        "snapshots": rows(db, Snapshot, Snapshot.session_id == session["id"]),
                    }
                    updated_at = job.updated_at
                    break
            assert time.monotonic() < deadline, "No persisted call reservation observed"
            time.sleep(0.05)
        save("before_interruption.json", before)
        # This Popen object is the only process this verifier may terminate.
        child.terminate()
        report["owned_worker_termination_exit_code"] = child.wait(timeout=10)
        report["terminated_at"] = datetime.now(timezone.utc).isoformat()
        child_log.close()
        child_log = None
        print(
            f"Owned worker {child.pid} terminated after one persisted mock call reservation.",
            flush=True,
        )
        assert child.poll() is not None
        run("operator_stuck_job_inspect", ["-m", "app.cli", "job-inspect", "--job", job_id])
        run("operator_jobs_before_recovery", ["-m", "app.cli", "jobs"])
        run(
            "operator_cleanup_dry_run",
            ["-m", "app.cli", "cleanup", "--plan", str(output / "cleanup-plan.json")],
        )
        wait_started = time.monotonic()
        while True:
            age = (datetime.now(timezone.utc) - updated_at).total_seconds()
            remaining = STALE_SECONDS + 1 - age
            if remaining <= 0:
                break
            print(f"Waiting for real stale threshold: {remaining:.1f} seconds remain.", flush=True)
            time.sleep(min(30, remaining))
        report["actual_stale_wait_seconds"] = round(time.monotonic() - wait_started, 3)
        report["claim_age_seconds_at_recovery"] = round(
            (datetime.now(timezone.utc) - updated_at).total_seconds(), 3
        )
        recovery = run("recovery_worker", ["-m", "app.worker", "--recover-stale", "--once"])
        assert "Recovered 1 stale jobs" in recovery
        failed = call("GET", "/jobs/" + job_id)
        assert failed["state"] == "failed" and failed["can_retry"] is True
        assert failed["error"]["code"] == "WORKER_INTERRUPTED"
        assert failed["error"]["details"]["uncertain_external_execution"] is True
        with factory() as db:
            after = {
                "job": rows(db, Job, Job.id == job_id)[0],
                "request": rows(db, AnswerRequest, AnswerRequest.id == request_id)[0],
                "attempts": rows(db, Attempt, Attempt.job_id == job_id),
                "snapshots": rows(db, Snapshot, Snapshot.session_id == session["id"]),
            }
            assert not rows(db, Answer, Answer.request_id == request_id)
            assert after["job"]["execution_token"] is None
            assert after["job"]["attempts"] == before["job"]["attempts"]
            assert after["request"]["budget"] == before["request"]["budget"]
            assert after["attempts"] == before["attempts"]
            assert after["snapshots"] == before["snapshots"]
            assert rows(db, Answer, Answer.request_id == first["request_id"]) == prior_answers
            current = rows(db, Message, Message.session_id == session["id"])
            assert [
                r for r in current if r["id"] in {m["id"] for m in prior_messages}
            ] == prior_messages
            assert len(current) == len(prior_messages) + 1
        save("after_recovery.json", after)
        run("operator_recovered_job_inspect", ["-m", "app.cli", "job-inspect", "--job", job_id])
        retried = call("POST", "/answer-requests/" + request_id + "/retry", {}, True)
        assert retried["request_id"] == request_id and retried["job_id"] != job_id
        run("explicit_retry_worker", ["-m", "app.worker", "--once"])
        succeeded = call("GET", "/jobs/" + retried["job_id"])
        assert succeeded["state"] == "succeeded"
        with factory() as db:
            request = db.get(AnswerRequest, request_id)
            assert request.budget["consumed_calls"] == 2
            assert request.budget["active_seconds"] >= before["request"]["budget"]["active_seconds"]
            assert request.body_hash == before["request"]["body_hash"]
            assert request.context_snapshot_id == before["request"]["context_snapshot_id"]
            assert rows(db, Attempt, Attempt.job_id == job_id) == before["attempts"]
            assert db.get(Job, job_id).state == "failed"
            assert len(rows(db, Answer, Answer.request_id == request_id)) == 1
            assert (
                len(rows(db, Message, Message.session_id == session["id"]))
                == len(prior_messages) + 2
            )
            final = {
                "jobs": rows(db, Job, Job.request_id == request_id),
                "request": rows(db, AnswerRequest, AnswerRequest.id == request_id)[0],
                "attempts": rows(db, Attempt, Attempt.job_id.in_([job_id, retried["job_id"]])),
                "messages": rows(db, Message, Message.session_id == session["id"]),
                "answers": rows(
                    db, Answer, Answer.request_id.in_([request_id, first["request_id"]])
                ),
                "snapshots": rows(db, Snapshot, Snapshot.session_id == session["id"]),
            }
        save("after_explicit_retry.json", final)
        report.update(
            status="passed",
            retry_job_id=retried["job_id"],
            assertions={
                "actual_owned_process_terminated": True,
                "charged_start_attempt_persisted": True,
                "actual_wall_clock_stale_threshold_elapsed": True,
                "real_worker_recovery_terminal_interrupted_and_uncertain": True,
                "no_answer_before_explicit_retry": True,
                "original_history_snapshots_and_counters_retained": True,
                "old_failed_job_and_uncertain_attempt_retained": True,
                "explicit_same_request_retry_one_answer_two_total_calls": True,
                "operator_job_inspect_and_cleanup_plan_executed": True,
            },
            limits="The delayed transport is a process-local mock test wrapper. No live provider, teaching/release kill drill or scientific correctness claim. Older branch-specific PostgreSQL tests cover additional cancellation/recovery paths. The cleanup command generated a plan only.",
        )
    except BaseException as exc:
        report.update(status="failed", failure_type=type(exc).__name__, failure_detail=str(exc))
        raise
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(timeout=10)
        if child_log is not None:
            child_log.close()
        if client is not None:
            client.close()
        if app is not None:
            app.state.engine.dispose()
        if created:
            assert re.fullmatch(r"cs30_drill_[0-9a-f]{12}", database)
            with admin.connect() as db:
                db.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"
                    ),
                    {"name": database},
                )
                db.execute(text(f"DROP DATABASE {database}"))
            report["disposable_database_removed"] = True
        admin.dispose()
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save("verification.json", report)
        print(json.dumps({"status": report["status"], "evidence": str(output)}), flush=True)


if __name__ == "__main__":
    main()
