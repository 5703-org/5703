"""Operator entry points must keep the same live-corpus policy as HTTP/worker."""

from contextlib import nullcontext
from types import SimpleNamespace
import json
import sys
import pytest
from app import cli, operations
from app.modules.knowledge import service
from app.core.exceptions import AppError


@pytest.mark.parametrize(
    "command", ["corpus-build", "corpus-activate", "corpus-rollback", "configuration-create"]
)
def test_operator_runtime_policy_is_not_lost(monkeypatch, tmp_path, command):
    settings = SimpleNamespace(database_url="unused", env="test", model_mode="live")
    db = SimpleNamespace()
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(cli, "init_engine", lambda url: object())
    monkeypatch.setattr(cli, "sessionmaker", lambda **kw: lambda: nullcontext(db))
    seen_admin = []
    monkeypatch.setattr(
        operations,
        "admin_user",
        lambda db, email: seen_admin.append(email) or SimpleNamespace(id="owner"),
    )
    if command == "corpus-build":
        target = tmp_path / "config.json"
        target.write_text(json.dumps({"processing_run_ids": ["run"]}))
        argv = [command, "--config", str(target), "--admin", "existing-operator@example.invalid"]
    elif command == "configuration-create":
        target = tmp_path / "config.json"
        target.write_text(
            json.dumps(
                {
                    "kind": "retrieval",
                    "name": "Policy check",
                    "values": {"embedding_provider": "mock"},
                }
            )
        )
        argv = [command, "--file", str(target), "--admin", "existing-operator@example.invalid"]
    else:
        argv = [command, "--release", "release"]
        db.get = lambda model, identity: SimpleNamespace(
            configuration={"embedding_provider": "mock"}
        )
    monkeypatch.setattr(sys, "argv", ["operator", *argv])
    with pytest.raises(AppError) as exc:
        cli.main()
    assert exc.value.code == "VALIDATION_FAILED"
    if command in {"corpus-build", "configuration-create"}:
        assert seen_admin == ["existing-operator@example.invalid"]
