"""Maintenance plans protect referenced and changed source files."""

from pathlib import Path
from uuid import uuid4
import hashlib
import os
import time
import subprocess
import sys
import json
import pytest
from app.core.exceptions import AppError
from app.operations import cleanup_plan, apply_cleanup
from .test_chat_runtime import corpus


def test_cleanup_dry_run_and_apply_preserve_referenced_bytes(runtime):
    rt = runtime
    corpus(rt)
    root = Path(rt.settings.storage_root)
    raw = ("orphan " + uuid4().hex).encode()
    path = root / "originals" / (hashlib.sha256(raw).hexdigest() + ".txt")
    path.write_bytes(raw)
    old = time.time() - 7200
    os.utime(path, (old, old))
    referenced = [p for p in (root / "originals").iterdir() if p != path]
    for source in referenced:
        os.utime(source, (old, old))
    with rt.db() as db:
        plan = cleanup_plan(db, rt.settings)
        assert len(plan["candidates"]) == 1 and path.exists()
        assert apply_cleanup(db, rt.settings, plan)["removed"] == 1
    assert not path.exists() and all(source.exists() for source in referenced)


def test_cleanup_rejects_changed_file_and_root_escape(runtime):
    rt = runtime
    root = Path(rt.settings.storage_root) / "originals"
    root.mkdir(parents=True)
    raw = b"old unreferenced bytes"
    path = root / (hashlib.sha256(raw).hexdigest() + ".txt")
    path.write_bytes(raw)
    old = time.time() - 7200
    os.utime(path, (old, old))
    with rt.db() as db:
        plan = cleanup_plan(db, rt.settings)
        path.write_bytes(b"changed content")
        os.utime(path, (old, old))
        with pytest.raises(AppError, match="changed"):
            apply_cleanup(db, rt.settings, plan)
        db.rollback()
        plan["storage_root"] = str(root.parent.parent)
        with pytest.raises(AppError):
            apply_cleanup(db, rt.settings, plan)
    assert path.exists()


def test_operator_cli_uses_real_database_and_secret_environment(runtime, tmp_path):
    rt = runtime
    environment = {
        **os.environ,
        "DATABASE_URL": rt.settings.database_url,
        "STORAGE_ROOT": rt.settings.storage_root,
        "APP_ENV": "test",
        "CS30_NEW_PASSWORD": "Disposable-password-123!",
    }

    def cli(*args):
        result = subprocess.run(
            [sys.executable, "-m", "app.cli", *args],
            capture_output=True,
            text=True,
            env=environment,
            timeout=20,
        )
        assert result.returncode == 0, result.stderr
        assert environment["CS30_NEW_PASSWORD"] not in result.stdout + result.stderr
        return json.loads(result.stdout)

    email = uuid4().hex + "@example.com"
    created = cli("account-create", "--email", email, "--name", "CLI fixture")
    assert created["email"] == email
    disabled = cli(
        "account-update",
        "--email",
        email,
        "--version",
        str(created["version"]),
        "--status",
        "deactivated",
    )
    assert disabled["status"] == "deactivated"
    cfg = tmp_path / "configuration.json"
    cfg.write_text(
        json.dumps({"kind": "evaluation", "name": "CLI immutable fixture", "values": {"top_k": 3}})
    )
    first = cli("configuration-create", "--file", str(cfg))
    assert cli("configuration-create", "--file", str(cfg))["id"] == first["id"]
    plan = tmp_path / "cleanup.json"
    assert cli("cleanup", "--plan", str(plan))["dry_run"] is True
    assert cli("cleanup", "--apply-manifest", str(plan))["removed"] == 0
    assert isinstance(cli("jobs"), list)
