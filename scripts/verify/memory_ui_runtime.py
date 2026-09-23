"""Owned mock-only HTTP runtime for a disposable Memory V2 browser check."""

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import uvicorn

from app.core.config import Settings
from app.cli import seed
from app.main import create_app
from scripts.verify.all import source_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()
    base = os.environ.get("TEST_DATABASE_SERVER")
    if not base or args.proof.exists():
        raise ValueError("Supply the authorized local test server and a new proof path")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))
    name = "cs30_memory_study_ui_" + uuid4().hex[:12]
    admin = create_engine(base + "/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as db:
        db.execute(text(f"CREATE DATABASE {name}"))
    admin.dispose()
    url = base + "/" + name
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.upgrade(Config("backend/alembic.ini"), "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
    settings = Settings(
        _env_file=None,
        env="test",
        database_url=url,
        model_mode="mock",
        llm_provider="mock",
        llm_model="authored-extractive-v1",
        llm_api_key=None,
        model_config_encryption_key=None,
        jwt_secret=secrets.token_urlsafe(48),
        storage_root=str(args.proof.parent / "storage"),
        local_model_device="recorded",
        chat_relevance_gate=False,
    )
    app = create_app(settings)
    with Session(app.state.engine) as db:
        seed(db)
        assert db.execute(text("select current_database()")).scalar_one() == name
    proof = {
        "database_name": name,
        "port": args.port,
        "model_mode": "mock",
        "provider_key_present": False,
        "worker_started": False,
        "source_hashes": source_snapshot(),
        "scope": "New disposable database; authored browser statements only; no original users, history, model settings or corpus copied",
    }
    args.proof.parent.mkdir(parents=True, exist_ok=True)
    with args.proof.open("x", encoding="utf-8") as stream:
        json.dump(proof, stream, indent=2)
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
