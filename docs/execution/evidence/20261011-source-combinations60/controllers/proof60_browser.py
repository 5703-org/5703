"""Owned real API/worker browser fixture with authored four-stage transport only."""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
from threading import Event, Thread
import time
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
import uvicorn

from app.cli import seed
from app.core.config import Settings
from app.main import create_app
from app.modules.answering import service
from app.modules.answering.models import Answer, AnswerRequest, Evidence, Job
from app.modules.learning_state.models import PrivateAnswerDraft
from app.worker import run_once
from generation import GenerationService, checked
from generation.local_repair import VERSION as REPAIR
from generation.source_evidence_combinations_v1 import VERSION as COMBINATIONS
from generation.source_relations_v2 import VERSION as RELATIONS
from tests.integration.conftest import disposable_postgres_url
from tests.integration.test_chat_runtime import corpus
from tests.integration.test_source_relation_correction_runtime import authored_unit_check, input_data
from tests.integration.test_source_evidence_combinations_runtime import (
    FINAL_PARTIAL_REASON, ORIGINAL_CLAIM, PARTIAL_REASON, PROTECTED_CLAIM,
    REPLACEMENT_CLAIM, SCHEMA, repair_data, select_exact_source,
)
from tests.unit.test_enhancement_generation import Script, answer

API_PORT = 18029
UI_PORT = 15199


def browser_environment(output_directory):
    """The browser child receives no database URLs or provider credentials."""
    allowed = (
        "SystemRoot", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "TEMP", "TMP", "TMPDIR",
        "LOCALAPPDATA", "APPDATA", "USERPROFILE", "NODE_PATH", "PROGRAMFILES",
        "PROGRAMFILES(X86)", "PROGRAMW6432", "SYSTEMDRIVE",
    )
    result = {name: os.environ[name] for name in allowed if name in os.environ}
    result["PROOF60_OUTPUT_DIR"] = str(Path(output_directory).resolve())
    return result


def _transport_case(negative, codec_inputs, stop):
    expected = {"negative": negative}

    def gap(messages):
        data = input_data(messages)
        value = authored_unit_check(messages)
        assert len(value["claims"]) == 2
        row = value["claims"][0]
        row["units"][0].update(status="partial", reason=PARTIAL_REASON)
        select_exact_source(value, data, 1, "Oxygen is released.")
        expected["claim_id"] = row["claim_id"]
        expected["selected"] = list(row["units"][0]["fragment_ids"])
        return value

    def local_patch(messages):
        data = repair_data(messages, codec_inputs)
        plan = data["source_evidence_combinations"]
        assert plan["version"] == COMBINATIONS and plan["candidate_only"]
        assert not plan["source_entailment_certified"] and not plan["publication_override"]
        assert data["original_claims"][0]["text"] == ORIGINAL_CLAIM
        assert [row["text"] for row in data["protected_exact_claims"]] == [PROTECTED_CLAIM]
        assert data["editable_claim_ids"] == [expected["claim_id"]]
        candidates = {row["fragment_id"]: row for row in data["source_repair_candidates"]}
        assert plan["candidate_fragment_ids"]
        assert any(
            "Light supplies energy to convert carbon dioxide and water into sugars."
            in candidates[identity]["exact_text"] for identity in plan["candidate_fragment_ids"]
        )
        expected["plan"] = deepcopy(plan)
        return {"edits": [{"claim_id": expected["claim_id"],
                           "replacement_text": REPLACEMENT_CLAIM}], "append_answer_text": ""}

    def final_check(messages):
        data = input_data(messages)
        value = authored_unit_check(messages)
        assert [row["text"] for row in data["CLAIMS"]] == [REPLACEMENT_CLAIM, PROTECTED_CLAIM]
        select_exact_source(value, data, 0,
                            "Light supplies energy to convert carbon dioxide and water into sugars.")
        select_exact_source(value, data, 1, "Oxygen is released.")
        if negative:
            # Finite authored delay gives the browser a normal pending job to observe.
            stop.wait(0.8)
            value["claims"][0]["units"][0].update(status="partial", reason=FINAL_PARTIAL_REASON)
        return value

    transport = Script([
        answer(ORIGINAL_CLAIM + " " + PROTECTED_CLAIM), gap, local_patch, final_check,
    ])
    return transport, expected


@contextmanager
def proof60_runtime(server_url, output_directory):
    """Use only the parent-supplied original isolated-PG server; never load auth files."""
    address = make_url(server_url + "/postgres")
    if address.host != "127.0.0.1" or address.port != 15433 or address.database != "postgres":
        raise ValueError("EXPECTED_OWNED_PG_SERVER_15433")
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with ExitStack() as stack:
        previous = os.environ.get("TEST_DATABASE_SERVER")
        try:
            os.environ["TEST_DATABASE_SERVER"] = server_url
            url = stack.enter_context(disposable_postgres_url())
        finally:
            if previous is None:
                os.environ.pop("TEST_DATABASE_SERVER", None)
            else:
                os.environ["TEST_DATABASE_SERVER"] = previous
        if not re.fullmatch(r"cs30_test_[0-9a-f]{12}", make_url(url).database or ""):
            raise ValueError("EXPECTED_NEW_DISPOSABLE_DATABASE")
        settings = Settings(
            _env_file=None, env="test", database_url=url, model_mode="mock",
            llm_provider="mock", llm_api_key=None, embedding_provider="mock",
            local_model_device="recorded", mock_delay_seconds=0,
            jwt_secret="proof60-authored-fixture-only-at-least-thirty-two-characters",
            storage_root=str(output / "storage"), chat_relevance_gate=False,
            chat_retrieval_cache=False, chat_query_preparation_policy="anchored_reference_v14",
            chat_source_relation_policy=RELATIONS, model_window_tokens=32768,
            max_provider_calls=4,
        )
        app = create_app(settings)
        stack.callback(app.state.engine.dispose)
        factory = sessionmaker(bind=app.state.engine, expire_on_commit=False)
        with factory() as db:
            seed(db)
        client = TestClient(app)
        stack.callback(client.close)

        def headers(email="student@example.com"):
            response = client.post("/api/v1/auth/login", json={
                "email": email, "password": "Passw0rd!",
            })
            assert response.status_code == 200
            return {"Authorization": "Bearer " + response.json()["data"]["access_token"]}

        runtime = SimpleNamespace(
            client=client, db=factory, settings=settings, engine=app.state.engine,
            headers=headers, work=lambda: run_once(app.state.engine, settings),
            output_directory=output, cases=[],
        )
        document, release = corpus(runtime)
        runtime.document_id, runtime.release_id = document["id"], release["release_id"]
        stop, codec_inputs, failures = Event(), {}, []
        encoder = checked.encode_claim_feedback

        def observe_encoder(feedback, **kwargs):
            codec_inputs.clear()
            codec_inputs.update(deepcopy(kwargs))
            return encoder(feedback, **kwargs)

        def generation_factory(**kwargs):
            assert len(runtime.cases) < 2, "UNEXPECTED_EXTRA_GENERATION_OR_AUTO_RETRY"
            assert kwargs.get("api_key") is None and kwargs.get("checker_api_key") is None
            transport, expected = _transport_case(len(runtime.cases) == 1, codec_inputs, stop)
            runtime.cases.append((transport, expected))
            return GenerationService(transport, checker_adapter=transport, **kwargs)

        stack.enter_context(patch.object(checked, "encode_claim_feedback", observe_encoder))
        stack.enter_context(patch.object(service, "GenerationService", generation_factory))
        server = uvicorn.Server(uvicorn.Config(
            app, host="127.0.0.1", port=API_PORT, log_level="warning", access_log=False,
            timeout_graceful_shutdown=5,
        ))

        def api_loop():
            try:
                server.run()
            except BaseException as exc:
                failures.append(type(exc).__name__)
                stop.set()

        def worker_loop():
            try:
                while not stop.is_set():
                    assert settings.model_mode == "mock" and settings.llm_provider == "mock"
                    if not run_once(app.state.engine, settings, queue="interactive"):
                        stop.wait(0.1)
            except BaseException as exc:
                failures.append(type(exc).__name__)
                stop.set()
                server.should_exit = True

        api_thread = Thread(target=api_loop, name="proof60-api")
        worker_thread = Thread(target=worker_loop, name="proof60-worker")
        api_thread.start()
        worker_thread.start()
        try:
            deadline = time.monotonic() + 15
            while not server.started and not failures and time.monotonic() < deadline:
                stop.wait(0.05)
            if not server.started or failures:
                raise RuntimeError("PROOF60_LOCAL_START_FAILED")
            yield runtime
            if failures:
                raise RuntimeError("PROOF60_LOCAL_THREAD_FAILED")
        finally:
            stop.set()
            server.should_exit = True
            api_thread.join(10)
            worker_thread.join(10)
            if api_thread.is_alive() or worker_thread.is_alive():
                raise RuntimeError("PROOF60_OWNED_THREAD_STOP_INCOMPLETE")


def verify_browser_receipt(runtime, receipt_path):
    """Join actual browser requests with private checks and this fixture's own rows."""
    receipt_file = Path(receipt_path).resolve()
    receipt_file.relative_to(runtime.output_directory)
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert receipt["automatic_retry_posts"] == 0 and receipt["message_posts"] == 2
    assert receipt["unexpected_origins"] == [] and len(runtime.cases) == 2
    summaries = []
    with runtime.db() as db:
        for case_name, case_index in (("success", 0), ("partial", 1)):
            observed = receipt[case_name]
            transport, expected = runtime.cases[case_index]
            request = db.get(AnswerRequest, observed["request_id"])
            job = db.get(Job, observed["job_id"])
            assert request.session_id == receipt["session_id"]
            assert request.release_id == runtime.release_id
            assert request.command["model_config"]["provider"] == "mock"
            assert request.command["repair_policy"] == REPAIR
            assert request.command["source_relation_policy"] == RELATIONS
            assert request.budget["consumed_calls"] == request.budget["max_calls"] == 4
            assert [call[1]["request_context"]["purpose"] for call in transport.calls] == [
                "generation", "joint_check", "semantic_repair", "joint_recheck",
            ]
            assert transport.calls[1][1]["response_schema_name"] == SCHEMA
            assert transport.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
            assert transport.calls[3][1]["response_schema_name"] == SCHEMA
            records = list(db.scalars(select(PrivateAnswerDraft).where(
                PrivateAnswerDraft.request_id == request.id,
                PrivateAnswerDraft.phase == "online_check",
            )))
            checks = sorted((row.payload for row in records), key=lambda payload: payload["revision"])
            assert [row["revision"] for row in checks] == [0, 1]
            assert [row["checker_contract_revision"] for row in checks] == [0, 0]
            assert checks[0]["source_evidence_combinations"] == expected["plan"]
            assert checks[0]["typed_judgment_raw_aliases"]["claims"][0]["units"][0]["status"] == "partial"
            if case_name == "partial":
                assert job.state == "failed" and job.answer_id is None
                assert job.error["code"] == "SEMANTIC_CHECK_FAILED" and request.state == "error"
                assert db.scalar(select(func.count()).select_from(Answer).where(
                    Answer.request_id == request.id,
                )) == 0
                assert not checks[1]["source_relation_assessment"]["accepted"]
                assert checks[1]["publication_block"]["stop_reason"] == "final_recheck_rejected"
            else:
                published = db.get(Answer, observed["answer_id"])
                assert published and published.model_mode == "mock" and job.state == "succeeded"
                assert published.request_id == request.id and job.answer_id == published.id
                assert published.response == observed["response"]
                assert published.response["answer_text"] == REPLACEMENT_CLAIM + " " + PROTECTED_CLAIM
                assert checks[1]["source_relation_assessment"]["accepted"]
                by_id = {row.evidence_id: row for row in db.scalars(select(Evidence).where(
                    Evidence.answer_id == published.id,
                ))}
                assert observed["cited_evidence_ids"] == published.response["citations"]
                for identity in observed["cited_evidence_ids"]:
                    evidence = by_id[identity]
                    assert evidence.document_id == runtime.document_id
                    digest = hashlib.sha256(evidence.payload["text"].encode("utf-8")).hexdigest()
                    assert digest == evidence.payload["text_hash"] == observed["evidence_hashes"][identity]
            summaries.append({
                "case": case_name, "request_id": str(request.id), "job_id": str(job.id),
                "four_real_pipeline_stages": True, "check_revisions": [0, 1],
                "checker_contract_revisions": [0, 0], "database_rows_match_browser": True,
                "new_source_candidate_count": len(expected["plan"]["candidate_fragment_ids"]),
            })
    return {
        "cases": summaries, "session_id": receipt["session_id"], "model_mode": "mock",
        "actual_browser_api_worker": True, "provider_requests": 0,
        "scientific_quality_claim": False, "live_model_t_full_ms": None,
        "mock_send_to_complete_dom_ms": receipt["success"]["mock_send_to_complete_dom_ms"],
        "old_answer_survived_partial_and_reload": True, "automatic_retry_posts": 0,
    }
