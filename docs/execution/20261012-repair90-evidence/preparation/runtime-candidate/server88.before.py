"""One normal isolated API with exact-response dispatch; no browser subprocess."""
import contextlib
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
STAGE = sys.argv[1]
if not re.fullmatch(r"(?:case01|case0[3-9]|case01r|case03r|case04r|case05r|case10|case10b|case10c)", STAGE):
    raise SystemExit("FIXED_STAGE_REQUIRED")
HERE = BASE / STAGE
PREVIOUS = BASE.parent / "5703-native76-preparation"
MAIN = Path(r"E:\5703\learning-assistant")
OBSERVER_SOURCE = BASE.parent / "5703-checker86-adapter-observer" / "capture_observer86.py"
OBSERVER_SHA256 = "89e9c0bda4511d8c5bed61d37362adba1beb4154c7cd74db98b28806be20c90c"
sys.path[:0] = [str(PREVIOUS), str(MAIN / "backend"), str(MAIN)]
for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
    os.environ[name] = "1"
for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[name] = "4"
logging.disable(logging.CRITICAL)
from bootstrap_native70 import memory_inputs, readonly_metadata, DiscardOutput
from targeted_answer88 import validate_scope, verify_source_pins, execute_targeted_answer, require
from run_native70 import old_metadata, unchanged_old_metadata, finish_guard_lifecycle
from budget88 import snapshot, stop_cohort
from normal_transport88 import shared_risk


def create(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def stop_existing_cohort(code):
    """Stop for an actual shared risk; known local failures remain per case."""
    journal = BASE / "cohort-ledger"
    if not (journal / "cohort-claim.json").exists():
        return
    state = snapshot(journal)
    if shared_risk(code, state["unknown_full_hold_USD"]):
        stop_cohort(journal, "UNSAFE_LOCAL_CONTROLLER")


def main():
    require(Path.cwd().resolve() == MAIN.resolve(), "MAIN_CACHE_WORKDIR_REQUIRED")
    require(not (HERE / "api-claim77.json").exists(), "PRESERVE_PRIOR_API_SCOPE")
    freeze_path = BASE / "runtime-freeze88.json"
    pin_path = BASE / f"scope88-{STAGE}-pin.json"
    scope_path = BASE / f"scope88-{STAGE}.json"
    protocol_path = BASE / "protocol88.json"
    require(all(not path.is_symlink() for path in (freeze_path, pin_path, scope_path, protocol_path)),
            "FROZEN_CASE_BINDING_REDIRECTED")
    freeze = json.loads(freeze_path.read_bytes())
    case_pin = json.loads(pin_path.read_bytes())
    require(type(case_pin) is dict and case_pin.get("case_id") == STAGE,
            "INDEPENDENT_CASE_PIN_REQUIRED")
    protocol_raw = protocol_path.read_bytes()
    protocol_pin = freeze.get("protocol_sha256")
    require(type(protocol_pin) is str and re.fullmatch(r"[0-9a-f]{64}", protocol_pin),
            "ROOT_FROZEN_PHASE88_PROTOCOL_PIN_REQUIRED")
    require(hashlib.sha256(protocol_raw).hexdigest()
            == case_pin.get("protocol_sha256") == protocol_pin,
            "FROZEN_PROTOCOL_CHANGED")
    protocol = json.loads(protocol_raw)
    require(type(protocol) is dict and protocol.get("maximum_physical_posts") == 32
            and protocol.get("per_request_provider_calls_maximum") == 4,
            "ROOT_INITIAL_RUNNABLE_CASE_BINDING_REQUIRED")
    raw_scope = scope_path.read_bytes()
    require(hashlib.sha256(raw_scope).hexdigest() == case_pin.get("scope_sha256"),
            "FROZEN_BASE_SCOPE_CHANGED")
    scope = json.loads(raw_scope)
    boundary_path = BASE.parent / "5703-checker85-runtime" / "public-source-boundary85.json"
    require(not boundary_path.is_symlink(), "PUBLIC_BOUNDARY_REDIRECTED")
    boundary_raw = boundary_path.read_bytes()
    require(hashlib.sha256(boundary_raw).hexdigest() == freeze["shared_public_source_boundary_sha256"]
            == case_pin.get("shared_public_source_boundary_sha256")
            == scope.get("public_source_boundary_sha256"), "FROZEN_PUBLIC_BOUNDARY_CHANGED")
    scope.update(json.loads(boundary_raw))
    from normal_transport88 import validate_case_scope
    require(scope.get("case_id") == STAGE, "EXACT_PHASE88_CASE_REQUIRED")
    validate_case_scope(scope)
    verify_source_pins(scope)
    if STAGE in {"case10", "case10b", "case10c"}:
        from page_admission89 import validate_page
        validate_page(BASE, STAGE, case_pin["scope_sha256"], protocol_pin, require_empty=False)
    require(not OBSERVER_SOURCE.is_symlink(), "OBSERVER_SOURCE_REDIRECTED")
    require(hashlib.sha256(OBSERVER_SOURCE.read_bytes()).hexdigest() == OBSERVER_SHA256,
            "APPROVED_OBSERVER_SOURCE_CHANGED")
    sys.path.insert(0, str(OBSERVER_SOURCE.parent))
    from capture_observer86 import observed_decode
    require(Path(observed_decode.__code__.co_filename).resolve() == OBSERVER_SOURCE.resolve(),
            "LOADED_OBSERVER_SOURCE_MISMATCH")
    with contextlib.redirect_stdout(DiscardOutput()), contextlib.redirect_stderr(DiscardOutput()):
        original, owner_id, login, key = memory_inputs()
        readonly_metadata(original, owner_id)
        from app.core.config import Settings
        scope["started_at_UTC"] = datetime.now(timezone.utc).isoformat()
        scope["expected_settings"]["storage_root"] = str(HERE / "storage")
        scope["expected_settings"]["visual_catalog_staging_root"] = str(HERE / "visual-staging")
        settings = Settings(_env_file=None, **{**original.model_dump(), **scope["expected_settings"], "llm_api_key": None})
        validate_scope(scope, settings)
        verify_source_pins(scope)
        for row in scope["source_pins"]:
            pinned = Path(row["path"])
            require(pinned.resolve().is_relative_to(MAIN.resolve()) and not pinned.is_symlink(), "MAIN_PUBLIC_PIN_REDIRECTED")
            data = pinned.read_bytes()
            require(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"], "CURRENT_MAIN_PUBLIC_PIN_CHANGED")
        from app.core import config
        config.get_settings = lambda: settings
        from app.main import app as imported_app, create_app
        app = create_app(settings)
        if imported_app.state.engine is not app.state.engine:
            imported_app.state.engine.dispose()
    del login
    import uvicorn
    from generation.types import ModelConfig
    from app.modules.model_settings import service as model_service
    from app.modules.model_settings.models import ModelConfiguration
    from app.modules.knowledge.models import ActiveCorpus, Chunk, CorpusRelease, Document, ReleaseChunk
    from sqlalchemy import select, text
    from sqlalchemy.orm import Session
    from normal_transport88 import normal_transport88
    engine = app.state.engine
    require(engine.url.host == "127.0.0.1" and engine.url.port == 15433
            and engine.url.database == "cs30_week10_pair_b_20261009_01", "ISOLATED_ORIGINAL_DB_REQUIRED")
    lock = engine.connect()
    require(lock.execute(text("SELECT pg_try_advisory_lock(5703001)")).scalar_one() is True,
            "INTERACTIVE_WORKER_ALREADY_ACTIVE")
    lock.commit()
    before = old_metadata(engine)
    abort = Event()
    workers = []
    result = {"session_id": None, "accepted": None, "worker": None, "route_stops": [],
              "model_calls_limit": 4, "same_period_cap_USD": "2.00", "old_queue_consumed": False,
              "auth_exported": False, "source_scope": "Independent DEV89 public case; normal teacher/checker/repair/recheck within four calls; shared cohort32/$2 cap; bound public question, sources, model route and privacy envelope"}
    create(HERE / "api-claim77.json", {"started_utc": scope["started_at_UTC"],
        "new_questions_max": 1, "original_database_only": True, "old_claims_reopened": 0,
        "case_id": scope["case_id"], "scope_sha256": case_pin["scope_sha256"],
        "supplement_descriptor_sha256": scope.get("supplement_descriptor_sha256"),
        "fresh_validation_descriptor_sha256": scope.get("fresh_validation_descriptor_sha256"),
        "question_id": scope["question_id"], "question_sha256": hashlib.sha256(scope["question_text"].encode()).hexdigest()})

    def selector(which):
        def resolve(db, current_settings, workspace_id):
            require(current_settings is settings and workspace_id == scope["fixed_workspace_id"], "EXACT_WORKSPACE_REQUIRED")
            row = db.get(ModelConfiguration, "74c8201e-aca0-400d-bcc5-5785e24c1c11")
            require(row and row.revision == 1 and row.config_hash == "703c94a357ddd4b826d8b5fe25d503198d3d56e1e9130f6a37ed9e9c3396aa4a", "BASELINE_CHANGED")
            return ModelConfig.from_dict(scope[which])
        return resolve

    def boundary(request_context):
        require(type(request_context) is dict, "NORMAL_CONTEXT_REQUIRED")
        allowed = {row["chunk_id"]: row for row in scope["current_public_sources"]}
        documents = {row["id"]: row for row in scope["current_public_documents"]}
        observed = []
        with Session(engine) as db:
            require(db.scalar(select(ActiveCorpus.release_id).where(ActiveCorpus.id == 1))
                    == scope["expected_release_id"], "ACTIVE_CORPUS_CHANGED")
            require(db.scalar(select(CorpusRelease.state).where(CorpusRelease.id == scope["expected_release_id"]))
                    == "active", "RELEASE_NOT_ACTIVE")
            for row in request_context.get("evidence", []):
                pair = db.execute(select(Chunk, Document).join(Document, Document.id == Chunk.document_id)
                    .join(ReleaseChunk, ReleaseChunk.chunk_id == Chunk.id).where(Chunk.id == row["chunk_id"],
                    ReleaseChunk.release_id == scope["expected_release_id"],
                    Document.active.is_(True), Document.revoked.is_(False))).one_or_none()
                require(pair is not None, "PUBLIC_SOURCE_UNAVAILABLE")
                chunk, document = pair
                full_sha = hashlib.sha256(chunk.text.encode()).hexdigest()
                pin = allowed.get(chunk.id, {})
                require(full_sha == chunk.text_hash == pin.get("text_sha256")
                    and row["asset_id"] == document.id == pin.get("document_id")
                    and document.source_url == pin.get("source_url") == documents.get(document.id, {}).get("source_url"),
                    "UNBOUND_PUBLIC_SOURCE")
                value = {"chunk_id": chunk.id, "text_sha256": hashlib.sha256(row["text"].encode()).hexdigest()}
                if value["text_sha256"] != full_sha:
                    start = chunk.text.find(row["text"])
                    require(start >= 0 and chunk.text.find(row["text"], start + 1) < 0, "NONLITERAL_SOURCE_SPAN")
                    value.update(source_span_verified=True, source_text_sha256=full_sha,
                                 source_span_start=start, source_span_end=start + len(row["text"]))
                observed.append(value)
        return {"current_public_boundary_verified": True, "release_id": scope["expected_release_id"], "evidence": observed}

    def execute(receipt):
        try:
            def claim(value):
                create(HERE / "target-claim77.json", value)
                return {"durably_recorded": True}
            result["worker"] = execute_targeted_answer(engine, settings, scope=scope,
                browser_receipt=receipt, session_id=result["session_id"], owner_id=owner_id,
                claim_writer=claim, owned_lock_connection=lock)
            if result["worker"].get("status") == "STOPPED_PRESERVE_NEW_ROWS":
                stop_existing_cohort(result["worker"].get("stop_code", "LOCAL_TARGET_FAILED"))
        except Exception as error:
            stop_existing_cohort(getattr(error, "code", "LOCAL_TARGET_FAILED"))
            result["worker"] = {"status": "STOPPED", "error_class": type(error).__name__,
                                "code": getattr(error, "code", "TARGET_STOPPED")}
        print(json.dumps({"event": "EXACT_TARGET_FINISHED", "result": result["worker"]}), flush=True)

    class SingleTurnGate:
        def __init__(self, wrapped):
            self.wrapped = wrapped
            self.posts = {"login": 0, "session": 0, "message": 0}

        async def __call__(self, request, receive, send):
            if request["type"] != "http":
                return await self.wrapped(request, receive, send)
            name, method = request["path"], request["method"]
            if name == "/native77/close" and method == "POST":
                idle = all(not worker.is_alive() for worker in workers)
                await send({"type": "http.response.start", "status": 200 if idle else 409, "headers": []})
                await send({"type": "http.response.body", "body": b"idle" if idle else b"busy"})
                if idle:
                    server.should_exit = True
                return
            accepted = method in ("GET", "HEAD", "OPTIONS")
            if method == "POST":
                field = ("login" if name == "/api/v1/auth/login" else "session" if name == "/api/v1/sessions"
                         else "message" if result["session_id"] and name == f"/api/v1/sessions/{result['session_id']}/messages" else None)
                if field and self.posts[field] == 0:
                    self.posts[field] += 1
                    accepted = True
                elif re.fullmatch(r"/api/v1/answers/[0-9a-f-]{36}/(?:exposures|readings)", name) and result["accepted"]:
                    with Session(engine) as db:
                        from app.modules.answering.models import Answer
                        answer = db.get(Answer, name.split("/")[4])
                        accepted = bool(answer and answer.request_id == result["accepted"]["request_id"])
            if not accepted:
                result["route_stops"].append({"method": method, "path": name})
                await send({"type": "http.response.start", "status": 403, "headers": []})
                return await send({"type": "http.response.body", "body": b"single-turn boundary"})
            body = []; status = None
            async def capture(message):
                nonlocal status
                if message["type"] == "http.response.start":
                    status = message["status"]
                if message["type"] == "http.response.body" and method == "POST":
                    body.append(message.get("body", b""))
                await send(message)
                if message["type"] == "http.response.body" and not message.get("more_body") and method == "POST":
                    if name == "/api/v1/sessions" and status == 200:
                        result["session_id"] = json.loads(b"".join(body))["data"]["id"]
                        print(json.dumps({"event": "FRESH_SESSION_CREATED", "session_id": result["session_id"]}), flush=True)
                    elif name.endswith("/messages") and status == 202:
                        require(result["accepted"] is None, "ONE_TARGET_ONLY")
                        result["accepted"] = json.loads(b"".join(body))["data"]
                        worker = Thread(target=execute, args=(result["accepted"],), name="native77-one-target")
                        workers.append(worker)
                        worker.start()
            return await self.wrapped(request, receive, capture)

    server = uvicorn.Server(uvicorn.Config(SingleTurnGate(app), host="127.0.0.1", port=18029,
                           access_log=False, log_level="critical", timeout_graceful_shutdown=5))
    stack = contextlib.ExitStack()
    ledger = None
    try:
        stack.enter_context(patch.object(model_service, "resolve_active_model_config", selector("expected_model_config")))
        stack.enter_context(patch.object(model_service, "resolve_active_checker_model_config", selector("expected_checker_config")))
        if settings.chat_checker_output_policy == "single_selection_findings_v2":
            require(STAGE in {"case01", "case03", "case04", "case05", "case06", "case07", "case08", "case09", "case01r", "case03r", "case04r", "case05r", "case10", "case10b", "case10c"}
                    and scope["expected_settings"].get("chat_checker_output_policy")
                    == "single_selection_findings_v2",
                    "EXPLICIT_SINGLE_SELECTION_CASE_SCOPE_REQUIRED")
            from generation import single_selection_findings_v2 as lossless_core, parser
            require(lossless_core.VERSION == "single_selection_findings_v2"
                    and lossless_core.PROVIDER_SCHEMA_NAME
                    == "joint_check_source_relations_v2_single_selection_output_v2"
                    and Path(lossless_core.__file__).resolve()
                    == (MAIN / "generation/single_selection_findings_v2.py").resolve()
                    and Path(lossless_core.decode.__code__.co_filename).resolve()
                    == (MAIN / "generation/single_selection_findings_v2.py").resolve(),
                    "LOADED_SINGLE_SELECTION_CORE_CHANGED")
        else:
            from generation import lossless_unit_findings_v1 as lossless_core, parser
        observer_state = {"view": None}

        def current_observer(original, path, stage):
            def call(*args, **kwargs):
                view = observer_state["view"]
                slot = view.get("provider_post_count", 0) if type(view) is dict else 0
                if type(slot) is not int or not 1 <= slot <= 4:
                    return original(*args, **kwargs)
                return observed_decode(original, key, path, stage=stage, slot=slot)(*args, **kwargs)
            return call

        stack.enter_context(patch.object(lossless_core, "decode", current_observer(
            lossless_core.decode, HERE / "checker-decode-error88.json", "lossless_decode")))
        stack.enter_context(patch.object(parser, "strict_json", current_observer(
            parser.strict_json, HERE / "strict-json-error88.json", "strict_json")))
        if settings.chat_checker_payload_policy == "lossless_full_checker_tables_v2":
            from generation import checked as checked_module
            original_selector = checked_module.select_full_checker_encoding
            encoding_observations = []

            def audited_encoding(*args, **kwargs):
                messages, observation = original_selector(*args, **kwargs)
                require(observation.get("encoding") == "lossless_full_checker_tables_v2",
                        "ACTUAL_V2_ENCODING_REQUIRED_FOR_TREATMENT")
                require(observation.get("original_data_sha256")
                        == observation.get("decoded_data_sha256"), "V2_ROUND_TRIP_CHANGED")
                number = len(encoding_observations) + 1
                create(HERE / f"encoding-{number:02d}-audit88.json", observation)
                encoding_observations.append(observation)
                return messages, observation

            stack.enter_context(patch.object(checked_module, "select_full_checker_encoding", audited_encoding))
        from app.modules.knowledge.service import prewarm_active_retrieval_cache
        import time
        warm_started = time.perf_counter()
        with Session(engine) as warm_db:
            try:
                warm_db.execute(text("SET TRANSACTION READ ONLY"))
                warm = prewarm_active_retrieval_cache(
                    warm_db, prepare_embedding_model=True,
                    requested_device=settings.local_model_device,
                )
            finally:
                warm_db.rollback()
        require(warm.get("status") == "ready" and warm.get("embedding_model_prepared") is True,
                "IDENTICAL_STARTUP_PREPARATION_REQUIRED")
        warm["startup_prepare_ms"] = round((time.perf_counter() - warm_started) * 1000, 3)
        warm["query_encoded"] = False
        warm["timing_boundary"] = "before normal API listener and Send"
        create(HERE / "startup-prewarm88.json", warm)
        ledger = stack.enter_context(normal_transport88(scope, HERE, key, assert_boundary=boundary, abort_event=abort))
        observer_state["view"] = ledger
        print(json.dumps({"event": "NORMAL_ISOLATED_API_STARTING", "port": 18029, "provider_limit": 4,
            "pid": os.getpid(), "parent_pid": os.getppid(), "case_id": STAGE,
            "scope_sha256": case_pin["scope_sha256"],
            "server_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}), flush=True)
        server.run()
    finally:
        abort.set()
        for worker in workers:
            worker.join(190)
        finish_guard_lifecycle(stack, owned_threads=workers, abort_event=abort, provider_state=ledger,
            write_closure=lambda value: create(HERE / "unclosed-worker77.json", value))
        result["owned_threads_closed"] = all(not worker.is_alive() for worker in workers)
        result["old_metadata_unchanged"] = unchanged_old_metadata(before, old_metadata(engine))
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        create(HERE / "api-closure77.json", result)
        lock.execute(text("SELECT pg_advisory_unlock(5703001)"))
        lock.commit()
        lock.close()
        engine.dispose()
        print(json.dumps({"event": "API_CLOSED", "threads_closed": result["owned_threads_closed"],
                          "old_metadata_unchanged": result["old_metadata_unchanged"]}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        stop_existing_cohort(getattr(error, "code", "LOCAL_SERVER_FAILED"))
        print(json.dumps({"event": "SERVER_STOP", "error_class": type(error).__name__,
                          "code": getattr(error, "code", "LOCAL_SERVER_START_FAILED"),
                          "missing_module": getattr(error, "name", None) if isinstance(error, ModuleNotFoundError) else None}), flush=True)
        raise SystemExit(1)
