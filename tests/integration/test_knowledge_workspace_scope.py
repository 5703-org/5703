"""Real source-management APIs isolate workspace administrators and raw-hash deduplication."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.core.exceptions import AppError
from app.core.security import hash_password
from app.modules.identity.models import User, Workspace
from app.modules.knowledge import service
from app.modules.knowledge.models import DocumentVersion

from .test_chat_runtime import call, corpus


@pytest.fixture
def source_admins(runtime):
    with runtime.db() as db:
        owner = db.scalar(select(User).where(User.email == "admin@example.com"))
        other_workspace = Workspace(name="Source isolation fixture", slug=uuid4().hex)
        db.add(other_workspace)
        db.flush()
        other = User(
            email=uuid4().hex + "@example.com",
            full_name="Other workspace administrator",
            hashed_password=hash_password("Passw0rd!"),
            role_id=owner.role_id,
            workspace_id=other_workspace.id,
        )
        peer = User(
            email=uuid4().hex + "@example.com",
            full_name="Same workspace administrator",
            hashed_password=hash_password("Passw0rd!"),
            role_id=owner.role_id,
            workspace_id=owner.workspace_id,
        )
        db.add_all([other, peer])
        db.commit()
        ids = {"owner": owner.id, "other": other.id, "peer": peer.id}
        emails = {"owner": owner.email, "other": other.email, "peer": peer.email}
    return {
        "ids": ids,
        "emails": emails,
        "headers": {name: runtime.headers(email) for name, email in emails.items()},
        "student": runtime.headers(),
    }


def _upload(runtime, headers, raw):
    response = runtime.client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Private authored source " + uuid4().hex},
        files={"file": (uuid4().hex + ".txt", raw, "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _processed_source(runtime, headers, raw, configuration=None):
    source = _upload(runtime, headers, raw)
    queued = call(
        runtime,
        "POST",
        f"/documents/{source['document']['id']}/process",
        {"configuration": configuration or {}},
        headers,
        202,
    )
    assert runtime.work()
    job = call(runtime, "GET", "/jobs/" + queued["job_id"], headers=headers)
    assert job["state"] == "succeeded", job
    return source, queued


def _snapshot(runtime):
    """All persisted table rows are hashed on PostgreSQL; fixture files are byte-hashed."""
    with runtime.db() as db:
        tables = list(
            db.scalars(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            )
        )
        rows = {
            name: list(
                db.scalars(
                    text(
                        "SELECT encode(sha256(convert_to(row_to_json(t)::text,'UTF8')),'hex') "
                        f'FROM public."{name}" t ORDER BY 1'
                    )
                )
            )
            for name in tables
        }
    root = Path(runtime.settings.storage_root)
    files = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }
    return {"rows": rows, "files": files}


def test_admin_source_reads_and_processing_exports_are_workspace_scoped(runtime, source_admins):
    owner = source_admins["headers"]["owner"]
    peer = source_admins["headers"]["peer"]
    other = source_admins["headers"]["other"]
    marker = "WORKSPACE_PRIVATE_CANARY_" + uuid4().hex
    raw = ("# Membranes\nAn authored membrane example. " + marker).encode()
    source, first = _processed_source(runtime, owner, raw)
    second = call(
        runtime,
        "POST",
        f"/documents/{source['document']['id']}/process",
        {"configuration": {"target": 160, "overlap": 20}},
        owner,
        202,
    )
    assert runtime.work()
    foreign_source, foreign_run = _processed_source(
        runtime, other, ("# Foreign source\nAn unrelated authored source. " + uuid4().hex).encode()
    )
    doc_id = source["document"]["id"]
    paths = [
        f"/documents/{doc_id}",
        f"/processing-runs/{first['processing_id']}/quality",
        f"/processing-runs/{first['processing_id']}/diff/{second['processing_id']}",
    ]
    before = _snapshot(runtime)
    for path in paths:
        response = runtime.client.get("/api/v1" + path, headers=other)
        assert response.status_code == 404, response.text
        assert marker not in response.text and doc_id not in response.text
        assert source["document"]["title"] not in response.text
        assert runtime.client.get("/api/v1" + path, headers=peer).status_code == 200
    for before_id, after_id in [
        (first["processing_id"], foreign_run["processing_id"]),
        (foreign_run["processing_id"], first["processing_id"]),
    ]:
        response = runtime.client.get(
            f"/api/v1/processing-runs/{before_id}/diff/{after_id}", headers=owner
        )
        assert response.status_code == 404, response.text
    listed = call(runtime, "GET", "/documents", headers=other)
    assert doc_id not in {item["id"] for item in listed}
    assert foreign_source["document"]["id"] in {item["id"] for item in listed}
    listed = call(runtime, "GET", "/documents", headers=peer)
    assert doc_id in {item["id"] for item in listed}
    assert foreign_source["document"]["id"] not in {item["id"] for item in listed}
    assert _snapshot(runtime) == before


@pytest.mark.parametrize("operation", ["process", "deactivate", "restore", "revoke", "release"])
def test_foreign_admin_source_mutations_do_not_change_any_rows_or_files(
    runtime, source_admins, operation
):
    owner = source_admins["headers"]["owner"]
    other = source_admins["headers"]["other"]
    source, run = _processed_source(
        runtime, owner, ("# Isolated source\nAuthored source facts. " + uuid4().hex).encode()
    )
    path = f"/documents/{source['document']['id']}/{operation}"
    body = {}
    if operation == "release":
        path = "/corpus/releases"
        body = {"processing_run_ids": [run["processing_id"]]}
    before = _snapshot(runtime)
    result = runtime.client.post("/api/v1" + path, json=body, headers=other)
    assert result.status_code == 404, result.text
    assert source["document"]["id"] not in result.text
    assert source["document"]["title"] not in result.text
    assert _snapshot(runtime) == before


def test_same_workspace_peer_can_process_and_change_visibility_and_revocation_stays_final(
    runtime, source_admins
):
    owner = source_admins["headers"]["owner"]
    peer = source_admins["headers"]["peer"]
    source = _upload(runtime, owner, ("# Peer source\nAn authored fact. " + uuid4().hex).encode())
    doc_id = source["document"]["id"]
    queued = call(runtime, "POST", f"/documents/{doc_id}/process", {}, peer, 202)
    assert runtime.work()
    assert call(runtime, "GET", "/jobs/" + queued["job_id"], headers=peer)["state"] == "succeeded"
    released = call(
        runtime,
        "POST",
        "/corpus/releases",
        {"processing_run_ids": [queued["processing_id"]]},
        peer,
        202,
    )
    assert runtime.work()
    assert call(runtime, "GET", "/jobs/" + released["job_id"], headers=peer)["state"] == "succeeded"
    assert call(runtime, "POST", f"/documents/{doc_id}/deactivate", {}, peer)["active"] is False
    assert call(runtime, "POST", f"/documents/{doc_id}/restore", {}, peer)["active"] is True
    assert call(runtime, "POST", f"/documents/{doc_id}/revoke", {}, peer)["revoked"] is True
    before = _snapshot(runtime)
    call(runtime, "POST", f"/documents/{doc_id}/restore", {}, peer, 409)
    assert _snapshot(runtime) == before


def test_raw_hash_dedup_never_returns_foreign_workspace_metadata(runtime, source_admins):
    raw = ("An authored deduplication fixture. " + uuid4().hex).encode()
    source = _upload(runtime, source_admins["headers"]["owner"], raw)
    before = _snapshot(runtime)
    response = runtime.client.post(
        "/api/v1/documents",
        headers=source_admins["headers"]["other"],
        data={"title": "Foreign duplicate"},
        files={"file": ("same.txt", raw, "text/plain")},
    )
    assert response.status_code == 404, response.text
    assert source["document"]["id"] not in response.text
    assert source["document"]["title"] not in response.text
    assert _snapshot(runtime) == before
    same = _upload(runtime, source_admins["headers"]["peer"], raw)
    assert same["duplicate"] is True
    assert same["version"]["id"] == source["version"]["id"]
    assert same["document"]["id"] == source["document"]["id"]
    assert _snapshot(runtime) == before


@pytest.mark.parametrize("actor", ["other", "peer"])
def test_under_lock_dedup_recheck_enforces_the_same_workspace_policy(runtime, source_admins, actor):
    raw = ("Authored simultaneous registration fixture. " + uuid4().hex).encode()
    source = _upload(runtime, source_admins["headers"]["owner"], raw)
    before = _snapshot(runtime)
    with runtime.db() as db:
        scalar = db.scalar
        lookups = []

        def first_lookup_misses(statement, *args, **kwargs):
            descriptions = getattr(statement, "column_descriptions", [])
            if descriptions and descriptions[0].get("entity") is DocumentVersion:
                lookups.append(statement)
                if len(lookups) == 1:
                    return None
            return scalar(statement, *args, **kwargs)

        # The first lookup is the deterministic race seam; the protected recheck
        # and workspace authorization both read the actual migrated PostgreSQL DB.
        with patch.object(db, "scalar", side_effect=first_lookup_misses):
            if actor == "other":
                with pytest.raises(AppError) as error:
                    service.ingest(
                        db,
                        runtime.settings,
                        source_admins["ids"][actor],
                        "same.txt",
                        raw,
                        "Race fixture",
                        "",
                        "",
                        "Authored fixture",
                    )
                assert error.value.code == "NOT_FOUND"
            else:
                doc, version, duplicate = service.ingest(
                    db,
                    runtime.settings,
                    source_admins["ids"][actor],
                    "same.txt",
                    raw,
                    "Race fixture",
                    "",
                    "",
                    "Authored fixture",
                )
                assert duplicate and doc.id == source["document"]["id"]
                assert version.id == source["version"]["id"]
        assert len(lookups) == 2
        db.rollback()
    assert _snapshot(runtime) == before


def test_student_cannot_use_source_administration_routes(runtime, source_admins):
    source, run = _processed_source(
        runtime,
        source_admins["headers"]["owner"],
        ("# Authorization source\nAn authored fact. " + uuid4().hex).encode(),
    )
    doc_id = source["document"]["id"]
    actions = [
        ("GET", "/documents", None),
        ("GET", f"/documents/{doc_id}", None),
        ("GET", f"/processing-runs/{run['processing_id']}/quality", None),
        ("POST", f"/documents/{doc_id}/process", {}),
        ("POST", f"/documents/{doc_id}/deactivate", {}),
        ("POST", f"/documents/{doc_id}/restore", {}),
        ("POST", f"/documents/{doc_id}/revoke", {}),
        ("POST", "/corpus/releases", {"processing_run_ids": [run["processing_id"]]}),
    ]
    before = _snapshot(runtime)
    for method, path, body in actions:
        response = runtime.client.request(
            method, "/api/v1" + path, headers=source_admins["student"], json=body
        )
        assert response.status_code == 403, response.text
    assert _snapshot(runtime) == before


def test_visibility_cli_uses_the_verified_admin_workspace(runtime, source_admins, tmp_path):
    source = _upload(
        runtime, source_admins["headers"]["owner"], ("CLI authored source. " + uuid4().hex).encode()
    )
    root = Path(__file__).resolve().parents[2]
    environment = {
        **os.environ,
        "DATABASE_URL": runtime.settings.database_url,
        "STORAGE_ROOT": runtime.settings.storage_root,
        "APP_ENV": "test",
        "MODEL_MODE": "mock",
        "LLM_PROVIDER": "mock",
        "LLM_API_KEY": "",
        "PYTHONPATH": os.pathsep.join([str(root / "backend"), str(root)]),
    }

    def execute(actor):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "app.cli",
                "source-visibility",
                "--admin",
                source_admins["emails"][actor],
                "--document",
                source["document"]["id"],
                "--action",
                "deactivate",
            ],
            env=environment,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=20,
        )

    same = execute("peer")
    assert same.returncode == 0, same.stderr
    assert json.loads(same.stdout)["active"] is False
    before = _snapshot(runtime)
    other = execute("other")
    assert other.returncode != 0
    assert source["document"]["title"] not in other.stdout + other.stderr
    assert _snapshot(runtime) == before


def test_shared_published_corpus_retrieval_keeps_its_global_identity(runtime, source_admins):
    document, release = corpus(runtime)
    before = _snapshot(runtime)
    foreign = runtime.client.get(
        "/api/v1/documents/" + document["id"], headers=source_admins["headers"]["other"]
    )
    assert foreign.status_code == 404
    with runtime.db() as db:
        evidence = service.retrieve(db, "What is photosynthesis?", release["release_id"], "R0")
        assert evidence and document["id"] in {item["asset_id"] for item in evidence}
    assert _snapshot(runtime) == before
