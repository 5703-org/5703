"""Run a bounded, credential-safe live question against a local API clone.

The credentials file belongs outside the project and is never included in the
written evidence. This development probe is not a formal answer-quality score.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


QUESTION = "How does osmosis move water across a selectively permeable membrane?"


def request(base: str, method: str, route: str, *, token: str | None = None, body=None, key=None):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if key:
        headers["Idempotency-Key"] = key
    payload = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + route, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            response = json.load(exc)
        except ValueError:
            response = {}
        return exc.code, response


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18830")
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    credentials = json.loads(args.credentials.read_text(encoding="utf-8"))["admin"]
    evidence = {
        "version": "week09_live_development_probe_v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "question": QUESTION,
        "formal_evaluation": False,
        "stages": [],
    }

    def stage(name: str, status: int, data: dict) -> None:
        entry = {"name": name, "http_status": status}
        if status >= 400:
            error = data.get("error") or {}
            entry["error_code"] = error.get("code") if isinstance(error, dict) else None
        evidence["stages"].append(entry)

    try:
        status, response = request(args.base_url, "POST", "/api/v1/auth/login", body=credentials)
        stage("login", status, response)
        if status != 200:
            return
        token = response["data"]["access_token"]
        status, response = request(
            args.base_url,
            "POST",
            "/api/v1/sessions",
            token=token,
            body={"title": "Week 9 isolated live development probe"},
        )
        stage("create_session", status, response)
        if status != 200:
            return
        session_id = response["data"]["id"]
        evidence["session_id"] = session_id
        status, response = request(
            args.base_url,
            "POST",
            f"/api/v1/sessions/{session_id}/messages",
            token=token,
            body={"content": QUESTION, "answer_mode": "textbook", "teaching_mode": "direct"},
            key=str(uuid.uuid4()),
        )
        stage("submit", status, response)
        if status != 202:
            return
        job_id = response["data"]["job_id"]
        evidence["job_id"] = job_id
        started = time.monotonic()
        while time.monotonic() - started < args.timeout_seconds:
            time.sleep(2)
            status, response = request(args.base_url, "GET", f"/api/v1/jobs/{job_id}", token=token)
            if status != 200:
                stage("poll", status, response)
                return
            job = response["data"]
            if job["state"] in {"succeeded", "failed", "cancelled"}:
                evidence["job"] = {
                    "state": job["state"],
                    "stage": job["stage"],
                    "error_code": (job.get("error") or {}).get("code"),
                    "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
                }
                break
        else:
            evidence["job"] = {"state": "timeout", "elapsed_ms": args.timeout_seconds * 1000}
            return
        if evidence["job"]["state"] != "succeeded":
            return
        answer_id = job.get("answer_id")
        evidence["answer_id"] = answer_id
        status, response = request(
            args.base_url, "GET", f"/api/v1/answers/{answer_id}", token=token
        )
        stage("read_answer", status, response)
        if status != 200:
            return
        answer = response["data"]
        result = answer.get("response") or {}
        evidence["answer"] = {
            "status": answer.get("status"),
            "model_mode": answer.get("model_mode"),
            "response_type": result.get("response_type"),
            "text": result.get("answer_text"),
            "citations": result.get("citations"),
            "evidence_count": len(answer.get("evidence") or []),
            "timing": answer.get("timing"),
        }
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            json.dumps(
                {
                    "stages": evidence["stages"],
                    "job": evidence.get("job"),
                    "answer_status": evidence.get("answer", {}).get("status"),
                    "model_mode": evidence.get("answer", {}).get("model_mode"),
                    "evidence_file": str(args.output),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
