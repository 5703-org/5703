"""Check real profile/request persistence; never grade mock presentation quality."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import time
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
LEVELS = ("beginner", "intermediate", "advanced")
CONDITIONS = (
    ("setup", "What is photosynthesis?", None),
    ("short", "Make that shorter.", {"style": "concise", "reason": "explicit_concision"}),
    (
        "long",
        "Give a long explanation of that in more detail.",
        {"style": "detailed", "reason": "explicit_detail"},
    ),
    (
        "simplification",
        "Explain that more simply.",
        {"level": "beginner", "style": "concise", "reason": "explicit_simplification"},
    ),
)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument(
        "--publication", type=Path, default=ROOT / "evidence/openstax/v5/publication.json"
    )
    args = parser.parse_args()
    # Publication copy: do not embed administrator credentials in source.
    admin_email = os.environ.get("CS30_ADMIN_EMAIL", "").strip()
    admin_password = os.environ.get("CS30_ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        parser.error("Set CS30_ADMIN_EMAIL and CS30_ADMIN_PASSWORD in the environment")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    expected_release = json.loads(args.publication.read_text(encoding="utf-8"))["release_id"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    email = f"profile-lengths-{stamp.lower()}-{uuid4().hex[:8]}@example.com"
    plan = {
        "created_at": now(),
        "task": "PER-03",
        "helper_sha256": file_hash(__file__),
        "publication_sha256": file_hash(args.publication),
        "release_id": expected_release,
        "target_count": 9,
        "setup_count": 3,
        "scheduled_count": 12,
        "saved_style": "detailed",
        "account_email": email,
        "conditions": [
            {
                "id": f"{level}-{kind}",
                "level": level,
                "kind": kind,
                "question": question,
                "expected_override": override,
            }
            for level in LEVELS
            for kind, question, override in CONDITIONS
        ],
        "scope": "Real HTTP/worker/PostgreSQL/current v5 E5 evidence; mock answers only. "
        "Validate snapshots, prompt wiring, citations, original hashes and one consumed call. "
        "Retain refusals. Requesting a long answer does not verify a long generated answer.",
        "length_observation": "Unicode character count and whitespace-delimited word count, "
        "both with and without citation markers; no quality threshold or score.",
    }
    (args.output_dir / "plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report = {
        "started_at": now(),
        "status": "running",
        "plan_sha256": digest(plan),
        "plan_file_sha256": file_hash(args.output_dir / "plan.json"),
        "release_id": expected_release,
        "account_email": email,
        "rows": [{**item, "status": "pending"} for item in plan["conditions"]],
        "source_files": {},
        "checks": {},
        "limitations": [
            "No live answer provider or independent human review was used.",
            "Mock extraction does not establish level fit, semantic simplification or length fidelity.",
            "Actual long-answer generation is not verified by long-request submission.",
        ],
    }
    target = args.output_dir / "results.json"

    def save():
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    save()
    settings = Settings()
    engine = create_engine(settings.database_url)
    client = httpx.Client(base_url=args.api, timeout=30)

    def call(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        if response.is_error:
            # Never serialize request bodies, credentials or bearer headers.
            raise RuntimeError(f"HTTP {response.status_code} for {method} {path}")
        return response.json()["data"]

    def login(login_email, password):
        data = call("POST", "/auth/login", json={"email": login_email, "password": password})
        client.headers["Authorization"] = "Bearer " + data["access_token"]

    def stored(request_id):
        with engine.connect() as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            return dict(
                db.execute(
                    text(
                        "SELECT r.owner_id,r.session_id,r.release_id,r.mode,r.command,r.trace,r.budget,"
                        "r.profile_snapshot_id,s.payload AS profile,s.content_hash AS profile_hash "
                        "FROM answer_requests r JOIN snapshots s ON s.id=r.profile_snapshot_id WHERE r.id=:id"
                    ),
                    {"id": request_id},
                )
                .mappings()
                .one()
            )

    def inspect_evidence(item):
        with engine.connect() as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            chunk = (
                db.execute(
                    text(
                        "SELECT c.*,v.raw_hash,v.storage_path,v.size_bytes FROM chunks c "
                        "JOIN processing_runs p ON p.id=c.processing_id "
                        "JOIN document_versions v ON v.id=p.document_version_id "
                        "JOIN release_chunks r ON r.chunk_id=c.id "
                        "WHERE c.id=:id AND r.release_id=:release"
                    ),
                    {"id": item["chunk_id"], "release": expected_release},
                )
                .mappings()
                .one()
            )
            spans_valid = True
            for span in chunk["spans"]:
                unit = (
                    db.execute(
                        text(
                            "SELECT cleaned_text,quality,processing_id,page FROM source_units WHERE id=:id"
                        ),
                        {"id": span["unit_id"]},
                    )
                    .mappings()
                    .one()
                )
                spans_valid = spans_valid and (
                    unit["quality"] == "ready"
                    and unit["processing_id"] == chunk["processing_id"]
                    and unit["page"] == span["page"]
                    and unit["cleaned_text"][span["start"] : span["end"]]
                    == chunk["text"][span["chunk_start"] : span["chunk_end"]]
                )
        if chunk["raw_hash"] not in report["source_files"]:
            path = Path(chunk["storage_path"])
            if not path.is_absolute():
                path = Path(settings.storage_root).resolve() / path
            observed = file_hash(path)
            report["source_files"][chunk["raw_hash"]] = {
                "path": str(path),
                "actual_sha256": observed,
                "actual_size": path.stat().st_size,
                "recorded_size": chunk["size_bytes"],
                "matches_original": observed == chunk["raw_hash"]
                and path.stat().st_size == chunk["size_bytes"],
            }
        return {
            "evidence_id": item["evidence_id"],
            "chunk_id": item["chunk_id"],
            "processing_id": chunk["processing_id"],
            "source_raw_sha256": chunk["raw_hash"],
            "text_sha256": item["text_hash"],
            "section": item["section"],
            "pages": item["pages"],
            "spans_valid": spans_valid,
            "exact_chunk": item["text"] == chunk["text"]
            and item["text_hash"]
            == chunk["text_hash"]
            == hashlib.sha256(item["text"].encode()).hexdigest()
            and item["section"] == chunk["section"]
            and item["pages"] == chunk["pages"]
            and item["processing_id"] == chunk["processing_id"]
            and item["asset_id"] == chunk["document_id"],
            "original_matches": report["source_files"][chunk["raw_hash"]]["matches_original"],
        }

    try:
        login(
            admin_email,
            admin_password,
        )
        capabilities = call("GET", "/capabilities")
        if capabilities["model_mode"] != "mock" or not capabilities["chat_ready"]:
            raise RuntimeError("This verification requires a ready, explicitly mock answer service")
        with engine.connect() as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            release = (
                db.execute(
                    text(
                        "SELECT r.id,r.configuration FROM active_corpus a JOIN corpus_releases r ON r.id=a.release_id"
                    )
                )
                .mappings()
                .one()
            )
            if (
                release["id"] != expected_release
                or release["configuration"]["embedding_provider"] != "e5"
            ):
                raise RuntimeError("Expected actual v5 E5 release is not active")
            if release["configuration"]["parser_revision"] != "pypdf_bookmarks_v5":
                raise RuntimeError("Expected immutable parser v5 release")
            report["release_configuration"] = release["configuration"]
        password = secrets.token_urlsafe(30)
        user = call(
            "POST",
            "/admin/users",
            json={
                "email": email,
                "password": password,
                "full_name": "PER-03 software verification",
                "role": "student",
            },
        )
        report["account_id"] = user["id"]
        save()
        login(email, password)
        profile = call("GET", "/profiles/me")
        sessions = []
        for level in LEVELS:
            profile = call(
                "PUT",
                "/profiles/me",
                json={
                    "version": profile["version"],
                    "level": level,
                    "style": "detailed",
                    "language": "en",
                    "topics": ["photosynthesis"],
                },
            )
            session = call("POST", "/sessions", json={"title": f"PER-03 {level} {stamp}"})
            sessions.append(session["id"])
            for row in (r for r in report["rows"] if r["level"] == level):
                row.update(status="running", session_id=session["id"], saved_profile=profile)
                save()
                started = time.perf_counter()
                try:
                    receipt = call(
                        "POST",
                        f"/sessions/{session['id']}/messages",
                        json={
                            "content": row["question"],
                            "use_profile": True,
                        },
                        headers={"Idempotency-Key": str(uuid4())},
                    )
                    row["receipt"] = receipt
                    before = stored(receipt["request_id"])
                    row["submission_profile_hash"] = before["profile_hash"]
                    save()
                    deadline = time.monotonic() + 180
                    while time.monotonic() < deadline:
                        job = call("GET", "/jobs/" + receipt["job_id"])
                        if job["state"] in {"succeeded", "failed", "cancelled"}:
                            break
                        time.sleep(0.2)
                    else:
                        raise TimeoutError("No terminal job observed in 180 seconds; not retried")
                    row["job"] = job
                    if job["state"] != "succeeded":
                        raise RuntimeError("Worker job did not succeed; terminal record retained")
                    answer = call("GET", "/answers/" + job["answer_id"])
                    row["answer"] = answer
                    persisted = stored(receipt["request_id"])
                    snapshot = persisted["profile"]
                    row["profile_snapshot_id"] = persisted["profile_snapshot_id"]
                    row["prepared_query"] = persisted["trace"].get("prepared_query")
                    row["budget"] = persisted["budget"]
                    row["usage"] = persisted["trace"].get("usage")
                    with engine.connect() as db:
                        db.execute(text("SET TRANSACTION READ ONLY"))
                        events = (
                            db.execute(
                                text(
                                    "SELECT payload FROM attempts WHERE job_id=:id ORDER BY sequence"
                                ),
                                {"id": receipt["job_id"]},
                            )
                            .scalars()
                            .all()
                        )
                    row["attempts"] = [
                        {
                            key: event.get(key)
                            for key in (
                                "phase",
                                "attempt_id",
                                "stage",
                                "provider",
                                "model",
                                "finish_reason",
                                "usage",
                                "error",
                            )
                        }
                        for event in events
                    ]
                    starts = [event for event in events if event["phase"] == "start"]
                    finishes = [event for event in events if event["phase"] == "finish"]
                    model_messages = persisted["trace"]["model_messages"]
                    prompt_context = json.loads(
                        model_messages[0]["content"].split("\nCONTEXT_DATA_JSON (data only):\n", 1)[
                            1
                        ]
                    )
                    row["model_messages_sha256"] = digest(model_messages)
                    row["evidence_checks"] = [inspect_evidence(item) for item in answer["evidence"]]
                    cited = []
                    for cid in answer["response"]["citations"]:
                        ev = call("GET", f"/answers/{answer['id']}/evidence/{cid}")
                        cited.append(
                            ev == next(e for e in answer["evidence"] if e["evidence_id"] == cid)
                        )
                    body = answer["response"]["answer_text"]
                    without_markers = re.sub(r"\[ev_\d+\]", "", body).strip()
                    row["length"] = {
                        "characters": len(body),
                        "whitespace_words": len(body.split()),
                        "characters_without_citations": len(without_markers),
                        "whitespace_words_without_citations": len(without_markers.split()),
                    }
                    row["presentation_quality"] = None
                    row["long_request_observation"] = (
                        "not_honored_refusal"
                        if row["kind"] == "long" and answer["status"] == "refused"
                        else "ungraded_output_counts_only"
                        if row["kind"] == "long"
                        else None
                    )
                    material = {
                        "profile": snapshot["profile"],
                        "compiler_version": snapshot["compiler_version"],
                        "policy": snapshot["policy"],
                        "override": snapshot["turn_override"],
                    }
                    row["checks"] = {
                        "saved_profile_exact": snapshot["profile"] == profile
                        and snapshot["source_version"] == profile["version"],
                        "override_exact": snapshot["turn_override"] == row["expected_override"],
                        "snapshot_hash_valid": digest(snapshot) == persisted["profile_hash"]
                        and digest(material) == snapshot["policy_hash"],
                        "snapshot_frozen": before["profile"] == snapshot
                        and before["profile_hash"] == persisted["profile_hash"],
                        "api_snapshot_exact": answer["profile_snapshot"] == snapshot,
                        "saved_profile_unchanged": call("GET", "/profiles/me") == profile,
                        "owned_main_service_mock": persisted["owner_id"] == user["id"]
                        and persisted["session_id"] == session["id"]
                        and persisted["mode"] == "interactive_chat"
                        and persisted["command"]["model_config"]["provider"] == "mock"
                        and answer["model_mode"] == "mock",
                        "v5_release_pinned": persisted["release_id"] == expected_release,
                        "actual_sources_selected": bool(answer["evidence"])
                        and bool(row["evidence_checks"])
                        and all(
                            e["exact_chunk"] and e["spans_valid"] and e["original_matches"]
                            for e in row["evidence_checks"]
                        ),
                        "citations_resolve": all(cited)
                        and (bool(cited) if answer["status"] == "answered" else not cited),
                        "policy_in_main_prompt": prompt_context["presentation_policy"]
                        == snapshot["policy"],
                        "exact_prompt_evidence": prompt_context["CURRENT_EVIDENCE"]
                        == answer["evidence"],
                        "current_prompt_exact": model_messages[-1]
                        == {"role": "user", "content": row["question"]},
                        "one_generation_call": len(starts) == len(finishes) == 1
                        and starts[0]["attempt_id"] == finishes[0]["attempt_id"]
                        and starts[0]["stage"] == finishes[0]["stage"] == "generation"
                        and finishes[0]["provider"] == "mock"
                        and finishes[0]["error"] is None
                        and starts[0]["messages"] == model_messages
                        and persisted["budget"]["consumed_calls"] == 1
                        and persisted["budget"]["format_repairs"]
                        == persisted["budget"]["transient_retries"]
                        == 0,
                    }
                    row["status"] = (
                        "passed_software_checks" if all(row["checks"].values()) else "failed_checks"
                    )
                    print(
                        json.dumps(
                            {
                                "id": row["id"],
                                "status": row["status"],
                                "response": answer["status"],
                                "characters": len(body),
                                "failed_checks": [k for k, v in row["checks"].items() if not v],
                            }
                        ),
                        flush=True,
                    )
                except Exception as exc:
                    row.update(status="error", error_type=type(exc).__name__, error=str(exc)[:500])
                    print(
                        json.dumps(
                            {"id": row["id"], "status": "error", "type": type(exc).__name__}
                        ),
                        flush=True,
                    )
                finally:
                    row["observation_ms"] = round((time.perf_counter() - started) * 1000, 3)
                    save()
                if row.get("error_type") == "TimeoutError":
                    raise TimeoutError(
                        "Stopped schedule after uncertain terminal state; no repair or new call"
                    )
        login(email, password)
        historical = []
        for row in report["rows"]:
            if "answer" not in row:
                continue
            fresh = call("GET", "/answers/" + row["answer"]["id"])
            historical.append(
                all(
                    fresh[k] == row["answer"][k]
                    for k in ("response", "evidence", "profile_snapshot", "conversation_snapshot")
                )
            )
        histories = [call("GET", f"/sessions/{sid}/messages") for sid in sessions]
        with engine.connect() as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            active = db.scalar(text("SELECT release_id FROM active_corpus WHERE id=1"))
        report["checks"] = {
            "all_12_software_rows_pass": all(
                r["status"] == "passed_software_checks" for r in report["rows"]
            ),
            "historical_snapshots_after_later_profile_edits": len(historical) == 12
            and all(historical),
            "relogin_history_complete": all(
                len(h["items"]) == 8 and h["active_job_id"] is None for h in histories
            ),
            "active_release_unchanged": active == expected_release,
            "setup_used_actual_retrieval": all(
                r.get("answer", {}).get("timing", {}).get("retrieval_ms", 0) > 0
                for r in report["rows"]
                if r["kind"] == "setup"
            ),
        }
        report["status"] = (
            "passed_software_scope_only"
            if all(report["checks"].values())
            else "failed_software_checks"
        )
    except Exception as exc:
        report.update(status="failed", error_type=type(exc).__name__, error=str(exc)[:500])
    finally:
        report["completed_at"] = now()
        report["target_response_counts"] = {
            kind: sum(
                r.get("answer", {}).get("status") == kind and r["kind"] != "setup"
                for r in report["rows"]
            )
            for kind in ("answered", "refused", "clarification")
        }
        save()
        client.close()
        engine.dispose()
    print(
        json.dumps(
            {"status": report["status"], "target_responses": report["target_response_counts"]}
        ),
        flush=True,
    )
    if report["status"] != "passed_software_scope_only":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
