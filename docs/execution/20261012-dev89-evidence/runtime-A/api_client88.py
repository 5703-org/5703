"""Root-invoked, one-case API client. Import is inert; credentials stay in memory."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parent / "5703-dev89-runtime"
ORIGIN = "http://127.0.0.1:18029"
MAX_PUBLIC_BYTES = 2_000_000
MAX_SCOPE_BYTES = 6_000_000
RESPONSE_KEYS = {
    "schema_version",
    "response_type",
    "answer_text",
    "short_answer",
    "citations",
    "refusal_reason",
    "follow_up_questions",
    "confidence",
}
TIMING_KEYS = {
    "total_ms",
    "generation_ms",
    "checking_ms",
    "token_count_ms",
    "model_total_ms",
    "attempts",
    "preparation_ms",
    "query_preparation_ms",
    "retrieval_ms",
    "teaching_plan_ms",
    "submission_to_worker_start_ms",
    "generation_wall_ms",
    "publication_before_commit_ms",
    "worker_before_commit_ms",
    "timing_scope",
}
PRIVATE_KEYS = {
    "owner_id",
    "learner_id",
    "user_id",
    "email",
    "password",
    "hashed_password",
    "authorization",
    "api_key",
    "database_url",
    "dsn",
    "access_token",
    "profile_snapshot",
    "conversation_snapshot",
}


class ClientStop(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise ClientStop(code)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def strict_json(data, *, max_bytes=MAX_PUBLIC_BYTES):
    require(type(data) is bytes and len(data) <= max_bytes, "JSON_SIZE_LIMIT")
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ClientStop("NONFINITE_JSON")
            ),
        )
    except (UnicodeError, json.JSONDecodeError):
        raise ClientStop("INVALID_JSON") from None


def uuid_text(value):
    require(type(value) is str, "EXACT_UUID_REQUIRED")
    try:
        require(str(UUID(value)) == value, "EXACT_UUID_REQUIRED")
    except ValueError:
        raise ClientStop("EXACT_UUID_REQUIRED") from None
    return value


def privacy(value, markers=(), depth=0):
    require(depth <= 40, "PUBLIC_SHAPE_LIMIT")
    if type(value) is dict:
        for key, item in value.items():
            require(
                type(key) is str and key.casefold() not in PRIVATE_KEYS,
                "PRIVATE_FIELD_IN_RECEIPT",
            )
            privacy(key, markers, depth + 1)
            privacy(item, markers, depth + 1)
    elif type(value) is list:
        for item in value:
            privacy(item, markers, depth + 1)
    elif type(value) is str:
        require(
            not any(marker and marker in value for marker in markers),
            "PRIVATE_MARKER_IN_RECEIPT",
        )
        require(
            re.search(r"Bearer\s+\S+", value, re.IGNORECASE) is None
            and re.search(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", value)
            is None,
            "TOKEN_IN_RECEIPT",
        )
    elif type(value) is float:
        require(math.isfinite(value), "NONFINITE_RECEIPT")


def checked_case(case_dir, scope_file, scope_sha256, runtime=RUNTIME):
    """Pin public scope and ownership claim before any login or close request."""
    case_dir, scope_file, runtime = Path(case_dir), Path(scope_file), Path(runtime)
    require(
        not case_dir.is_symlink()
        and not scope_file.is_symlink()
        and not runtime.is_symlink(),
        "CASE_PATH_REDIRECTED",
    )
    runtime = runtime.resolve(strict=True)
    case_dir = case_dir.resolve(strict=True)
    scope_file = scope_file.resolve(strict=True)
    require(
        case_dir.parent == runtime
        and re.fullmatch(r"case(?:01|0[3-9]|01r|03r|04r|05r|10|10b|10c)", case_dir.name)
        and case_dir.is_dir()
        and scope_file.parent == runtime
        and scope_file.name == f"scope88-{case_dir.name}.json",
        "EXACT_CASE_SCOPE_REQUIRED",
    )
    require(
        type(scope_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", scope_sha256),
        "SCOPE_PIN_REQUIRED",
    )
    raw = scope_file.read_bytes()
    require(sha(raw) == scope_sha256, "FROZEN_CASE_SCOPE_CHANGED")
    scope = strict_json(raw, max_bytes=MAX_SCOPE_BYTES)
    require(
        type(scope) is dict and scope.get("case_id") == case_dir.name,
        "SCOPE_CASE_MISMATCH",
    )
    question, question_id = scope.get("question_text"), scope.get("question_id")
    require(
        type(question) is str
        and 1 <= len(question) <= 7200
        and type(question_id) is str
        and 1 <= len(question_id) <= 120,
        "PUBLIC_QUESTION_REQUIRED",
    )
    claim_path = case_dir / "api-claim77.json"
    require(
        claim_path.is_file() and not claim_path.is_symlink(), "OWNED_API_CLAIM_REQUIRED"
    )
    claim_bytes = claim_path.read_bytes()
    claim = strict_json(claim_bytes)
    require(
        type(claim) is dict
        and claim.get("case_id") == case_dir.name
        and claim.get("question_id") == question_id
        and claim.get("question_sha256") == sha(question.encode())
        and claim.get("scope_sha256") == scope_sha256,
        "OWNED_API_SCOPE_MISMATCH",
    )
    return (
        case_dir,
        scope,
        {
            "scope_bytes": len(raw),
            "scope_sha256": scope_sha256,
            "api_claim_sha256": sha(claim_bytes),
        },
    )


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ClientStop("API_REDIRECT_FORBIDDEN")


class LocalTransport:
    """No proxy, redirects, or retries. Only the fixed owned loopback API."""

    def __init__(self):
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def __call__(self, method, path, body, token, timeout, *, idempotency_key=None):
        require(
            method in {"GET", "POST"}
            and path.startswith("/")
            and not path.startswith("//")
            and ":" not in path
            and "#" not in path,
            "LOCAL_API_PATH_REQUIRED",
        )
        headers = {"Accept": "application/json"}
        if idempotency_key is not None:
            require(
                method == "POST"
                and re.fullmatch(r"/api/v1/sessions/[0-9a-f-]{36}/messages", path)
                and type(idempotency_key) is str
                and re.fullmatch(r"checker88-[0-9a-f]{64}", idempotency_key),
                "EXACT_MESSAGE_IDEMPOTENCY_KEY_REQUIRED",
            )
            headers["Idempotency-Key"] = idempotency_key
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            headers["Content-Type"] = "application/json"
        request = Request(ORIGIN + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=timeout) as response:
                return response.status, response.read(MAX_PUBLIC_BYTES + 1)
        except HTTPError as error:
            return error.code, error.read(MAX_PUBLIC_BYTES + 1)
        except (URLError, TimeoutError, OSError):
            raise ClientStop("LOCAL_API_TRANSPORT_FAILED") from None


def run_case(
    case_dir,
    scope_file,
    scope_sha256,
    *,
    login,
    transport=None,
    clock=time.monotonic,
    sleep=time.sleep,
    runtime=RUNTIME,
):
    """Run exactly one normal login/session/message; Root supplies synthetic login.

    No bootstrap, credential-file reads, database imports, or model SDK imports.
    Returns a public receipt and preserves all new rows on failure. The finite
    210-second work deadline starts before message submission; idle close has
    an additional finite 15-second settlement window and never force-stops work.
    """
    case_dir, scope, pins = checked_case(case_dir, scope_file, scope_sha256, runtime)
    out = case_dir / "journey-receipt88.json"
    claim_path = case_dir / "api-client-claim88.json"
    require(not out.exists() and not out.is_symlink(), "PRESERVE_PRIOR_CLIENT_RECEIPT")
    require(
        type(login) is dict
        and set(login) == {"email", "password"}
        and all(type(v) is str and bool(v) for v in login.values()),
        "MEMORY_ONLY_SYNTHETIC_LOGIN_REQUIRED",
    )
    private_values = [login["email"], login["password"]]
    transport = LocalTransport() if transport is None else transport
    receipt = {
        "schema": "5703_checker88_api_client_v1",
        "started_utc": utc(),
        "case_id": case_dir.name,
        "question_id": scope["question_id"],
        "question_sha256": sha(scope["question_text"].encode()),
        **pins,
        "status": "STARTED",
        "stage": "NORMAL_LOGIN",
        "new_message_submissions": 0,
        "message_post_attempts": 0,
        "automatic_retries": 0,
        "n": 0,
        "API_n": 0,
        "completed_answer_n": 0,
        "valid_page_latency_sample": False,
        "send_to_first_prose_ms": None,
        "send_to_complete_dom_ms": None,
        "TTFT_ms": None,
        "stable_p95_ms": None,
        "auth_exported": False,
        "normal_activation_qualified": False,
        "browser_used": False,
        "use_profile": False,
        "history_used": False,
        "route_stops": [],
        "poll_count": 0,
        "api_close_attempts": 0,
    }
    # Durable one-client admission: even an interrupted run cannot post twice.
    with claim_path.open("xb") as stream:
        stream.write(
            (
                json.dumps(
                    {
                        "case_id": case_dir.name,
                        **pins,
                        "started_utc": utc(),
                        "auth_exported": False,
                    },
                    sort_keys=True,
                )
                + "\n"
            ).encode()
        )
        stream.flush()
        os.fsync(stream.fileno())
    token = None

    def raw_call(method, path, body=None, timeout=10, *, idempotency_key=None):
        kwargs = {} if idempotency_key is None else {"idempotency_key": idempotency_key}
        status, data = transport(method, path, body, token, timeout, **kwargs)
        require(
            type(status) is int
            and 100 <= status <= 599
            and type(data) is bytes
            and len(data) <= MAX_PUBLIC_BYTES,
            "LOCAL_API_RESPONSE_SHAPE",
        )
        return status, data

    def call(
        method, path, body=None, expected=200, timeout=10, *, idempotency_key=None
    ):
        status, data = raw_call(
            method, path, body, timeout, idempotency_key=idempotency_key
        )
        if status != expected:
            receipt["failed_http_status"] = status
            receipt["failed_http_method"] = method
            receipt["failed_http_path"] = path
        require(status == expected, "LOCAL_API_HTTP_STATUS")
        envelope = strict_json(data)
        require(type(envelope) is dict and "data" in envelope, "API_ENVELOPE_REQUIRED")
        return envelope["data"]

    try:
        logged_in = call("POST", "/api/v1/auth/login", dict(login))
        require(
            type(logged_in) is dict
            and type(logged_in.get("access_token")) is str
            and bool(logged_in["access_token"])
            and logged_in.get("token_type", "bearer") == "bearer",
            "LOCAL_LOGIN_TOKEN_REQUIRED",
        )
        token = logged_in["access_token"]
        private_values.append(token)
        logged_in = None
        receipt["stage"] = "ONE_FRESH_SESSION"
        session = call("POST", "/api/v1/sessions", {})
        require(type(session) is dict, "FRESH_SESSION_REQUIRED")
        session_id = uuid_text(session.get("id"))
        receipt["session_id"] = session_id
        history = call("GET", f"/api/v1/sessions/{session_id}/messages?limit=100")
        require(
            type(history) is dict and history.get("items") == [],
            "FRESH_EMPTY_SESSION_REQUIRED",
        )
        receipt["stage"] = "SINGLE_SEND"
        submitted_at = clock()
        deadline = submitted_at + 210
        # Bind one normal submission to its frozen case and fresh session.
        idempotency_key = "checker88-" + sha(
            f"{case_dir.name}|{scope_sha256}|{session_id}".encode()
        )
        receipt["message_idempotency_key_sha256"] = sha(idempotency_key.encode("utf-8"))
        receipt["message_post_attempts"] = 1
        accepted = call(
            "POST",
            f"/api/v1/sessions/{session_id}/messages",
            {
                "content": scope["question_text"],
                "use_profile": False,
                "answer_mode": "textbook",
                "teaching_mode": "direct",
            },
            expected=202,
            timeout=10,
            idempotency_key=idempotency_key,
        )
        require(
            type(accepted) is dict
            and set(accepted)
            <= {"request_id", "job_id", "user_message_id", "poll_url"},
            "ACCEPTED_JOB_SHAPE",
        )
        job_id, request_id = (
            uuid_text(accepted.get("job_id")),
            uuid_text(accepted.get("request_id")),
        )
        if accepted.get("user_message_id") is not None:
            uuid_text(accepted["user_message_id"])
        require(
            accepted.get("poll_url") == f"/api/v1/jobs/{job_id}",
            "EXACT_JOB_POLL_URL_REQUIRED",
        )
        receipt["accepted"] = accepted
        receipt["new_message_submissions"] = 1
        receipt["stage"] = "POLL_EXACT_JOB"
        while True:
            remaining = deadline - clock()
            require(remaining > 0, "FINITE_JOB_POLL_DEADLINE")
            job = call("GET", f"/api/v1/jobs/{job_id}", timeout=min(10, remaining))
            receipt["poll_count"] += 1
            require(
                type(job) is dict
                and job.get("id") == job_id
                and job.get("request_id") == request_id
                and job.get("state")
                in {"queued", "running", "succeeded", "failed", "cancelled"},
                "EXACT_JOB_POLL_TARGET",
            )
            state = job["state"]
            if state in {"succeeded", "failed", "cancelled"}:
                receipt["job_state"] = state
                receipt["api_send_to_terminal_ms"] = (clock() - submitted_at) * 1000
                break
            sleep(min(0.25, max(0, deadline - clock())))
        if state != "succeeded":
            require(job.get("answer_id") is None, "FAILED_JOB_MUST_NOT_PUBLISH")
            receipt["answer_id"] = None
            receipt["status"] = "API_FAILED"
            receipt["error"] = {
                "code": "TERMINAL_WORKER_FAILED"
                if state == "failed"
                else "TERMINAL_WORKER_CANCELLED"
            }
        else:
            receipt["stage"] = "PERSISTED_PUBLIC_ANSWER"
            answer_id = uuid_text(job.get("answer_id"))
            answer = call("GET", f"/api/v1/answers/{answer_id}")
            require(
                type(answer) is dict
                and answer.get("id") == answer_id
                and answer.get("request_id") == request_id
                and answer.get("job_id") == job_id
                and answer.get("model_mode") == "live"
                and answer.get("response_schema") == "chat_response_v1",
                "PERSISTED_ANSWER_JOIN_FAILED",
            )
            response = answer.get("response")
            require(
                type(response) is dict
                and set(response) <= RESPONSE_KEYS
                and response.get("schema_version") == "chat_response_v1"
                and response.get("response_type")
                in {"answer", "refusal", "clarification", "social"}
                and type(response.get("answer_text")) is str
                and bool(response["answer_text"].strip()),
                "PUBLIC_COMPLETE_RESPONSE_REQUIRED",
            )
            timing = answer.get("timing") or {}
            require(type(timing) is dict, "PUBLIC_ANSWER_TIMING_REQUIRED")
            receipt["answer_id"] = answer_id
            receipt["response"] = response
            receipt["answer_timing"] = {
                key: value for key, value in timing.items() if key in TIMING_KEYS
            }
            receipt["answer_completeness"] = answer.get("answer_completeness")
            history = call("GET", f"/api/v1/sessions/{session_id}/messages?limit=100")
            require(
                type(history) is dict
                and type(history.get("items")) is list
                and len(history["items"]) == 2,
                "PERSISTED_FRESH_SESSION_JOIN_FAILED",
            )
            receipt["api_send_to_complete_response_ms"] = (
                clock() - submitted_at
            ) * 1000
            receipt["status"] = "API_COMPLETED"
            receipt["API_n"] = 1
            receipt["completed_answer_n"] = 1
            receipt["quality_pass_claimed"] = False
    except Exception as error:  # noqa: BLE001 - preserve receipt without exporting private exception text.
        receipt["status"] = "STOPPED_PRESERVE_NEW_ROWS"
        receipt["error"] = {
            "code": error.code
            if isinstance(error, ClientStop)
            else "CLIENT_EXECUTION_STOPPED",
            "raw_exception_exported": False,
        }
    finally:
        receipt["stage_at_close"] = receipt["stage"]
        close_deadline = clock() + 15
        while clock() < close_deadline:
            try:
                receipt["api_close_attempts"] += 1
                status, _ = raw_call(
                    "POST", "/native77/close", timeout=min(5, close_deadline - clock())
                )
                receipt["api_close_status"] = status
                if status == 200:
                    break
                require(status == 409, "OWNED_API_CLOSE_STATUS")
                sleep(min(0.25, max(0, close_deadline - clock())))
            except Exception as error:  # noqa: BLE001 - owned close failures cannot leak private text.
                receipt["api_close_error"] = {
                    "code": error.code
                    if isinstance(error, ClientStop)
                    else "OWNED_API_CLOSE_FAILED"
                }
                break
        if receipt.get("api_close_status") != 200:
            receipt["observed_api_status"] = receipt["status"]
            receipt["status"] = "STOPPED_PRESERVE_NEW_ROWS"
        token = None
        receipt["finished_utc"] = utc()
        try:
            privacy(receipt, private_values)
        except ClientStop as error:
            # Do not publish a partially redacted scientific answer as evidence.
            receipt = {
                "schema": "5703_checker88_api_client_v1",
                "case_id": case_dir.name,
                "status": "PUBLIC_RECEIPT_BLOCKED",
                "code": error.code,
                "auth_exported": False,
                "n": 0,
                "valid_page_latency_sample": False,
                "finished_utc": utc(),
            }
        data = (
            json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        ).encode()
        require(len(data) <= MAX_PUBLIC_BYTES, "PUBLIC_RECEIPT_SIZE_LIMIT")
        with out.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        private_values = None
    return receipt
