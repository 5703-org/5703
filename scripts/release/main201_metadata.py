"""Native upgrade metadata and migration only; never inspect learner text or credentials."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, default=str).encode()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("inspect", "migrate"))
    p.add_argument("--project", required=True, type=Path)
    p.add_argument("--database-host", required=True)
    p.add_argument("--database-port", required=True, type=int)
    p.add_argument("--database-name", required=True)
    p.add_argument("--target-head")
    p.add_argument("--allowed-head", action="append", default=[])
    args = p.parse_args()
    project = args.project.resolve()
    os.chdir(project)
    sys.path[:0] = [str(project / "backend"), str(project)]
    from dotenv import dotenv_values
    from app.core.config import Settings
    values = dotenv_values(project / ".env", encoding="utf-8-sig")
    for name, field in Settings.model_fields.items():
        aliases = getattr(field.validation_alias, "choices", [field.validation_alias])
        for alias in [name, name.upper(), *aliases]:
            if isinstance(alias, str):
                os.environ.pop(alias, None)
    os.environ.pop("MODEL_CONFIG_ENCRYPTION_KEY", None)
    os.environ.update({key: value for key, value in values.items() if value is not None})
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    settings = Settings()
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    url = make_url(settings.database_url)
    if (url.drivername != "postgresql+psycopg"
            or (url.host, url.port or 5432, url.database)
            != (args.database_host, args.database_port, args.database_name)):
        raise RuntimeError("EXPLICIT_EXISTING_DATABASE_IDENTITY_MISMATCH")
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            connection.exec_driver_sql("SET LOCAL statement_timeout=5000")
            connection.exec_driver_sql("SET LOCAL lock_timeout=1000")
            head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            jobs = connection.execute(text("SELECT count(*) FROM jobs WHERE state NOT IN ('succeeded','failed','cancelled')")).scalar_one()
            requests = connection.execute(text("SELECT count(*) FROM answer_requests WHERE state NOT IN ('answered','refused','clarification','error','cancelled')")).scalar_one()
            selection = connection.execute(text("SELECT a.workspace_id,a.version,a.configuration_id,a.checker_configuration_id,g.config_hash AS generation_hash,c.config_hash AS checker_hash FROM active_model_configurations a JOIN model_configurations g ON g.id=a.configuration_id LEFT JOIN model_configurations c ON c.id=a.checker_configuration_id ORDER BY a.workspace_id")).mappings().all()
            corpus = connection.execute(text("SELECT a.release_id,c.configuration,c.manifest FROM active_corpus a JOIN corpus_releases c ON c.id=a.release_id WHERE a.id=1")).mappings().all()
            epoch = connection.execute(text("SELECT token FROM retrieval_epochs WHERE id=1")).scalar_one()
            namespace = connection.execute(text("SELECT current_schema() || ':' || current_setting('search_path')")).scalar_one()
            locks = connection.execute(text("SELECT pid AS pg_backend_pid,objid::bigint AS lock_id,mode FROM pg_locks WHERE locktype='advisory' AND granted AND classid=0 AND objsubid=1 AND database=(SELECT oid FROM pg_database WHERE datname=current_database()) AND objid IN (5703001,5703002,5703003) ORDER BY objid,pid")).mappings().all()
            scoped = connection.execute(text("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='active_model_configurations' AND column_name='activation_scope')")).scalar_one()
            answer_only = connection.execute(text("SELECT count(*) FROM active_model_configurations WHERE activation_scope='answer_only'")).scalar_one() if scoped else 0
            connection.rollback()
        if args.mode == "migrate":
            if head not in args.allowed_head or jobs or requests or locks or not args.target_head:
                raise RuntimeError("IDLE_REVIEWED_MIGRATION_PRECONDITIONS_REQUIRED")
            from alembic.config import Config
            from alembic import command
            command.upgrade(Config(str(project / "backend/alembic.ini")), args.target_head)
            with engine.connect() as connection:
                head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if head != args.target_head:
                raise RuntimeError("TARGET_MIGRATION_HEAD_NOT_REACHED")
        result = {"status": "PASS_NATIVE_MIGRATION" if args.mode == "migrate" else "PASS_NATIVE_METADATA",
                  "head": head, "pending_jobs": jobs, "pending_requests": requests,
                  "active_selection_sha256": digest([dict(row) for row in selection]),
                  "active_corpus_sha256": digest([dict(row) for row in corpus]),
                  "epoch_sha256": digest(epoch), "namespace_sha256": digest(namespace),
                  "worker_locks": [dict(row) for row in locks],
                  "answer_only_active_count": answer_only,
                  "database_identity": {"host": args.database_host, "port": args.database_port, "database": args.database_name},
                  "storage_root": str(Path(settings.storage_root).resolve()),
                  "key_file": str(Path(settings.model_config_key_file).resolve()),
                  "database_fingerprint": __import__("app.platform_core.retrieval_warmup", fromlist=["database_fingerprint"]).database_fingerprint(engine),
                  "credential_or_learner_text_columns_selected": False}
        print(json.dumps(result))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "STOP_PRESERVE_STATE", "safe_code": str(error) if isinstance(error, RuntimeError)
                          else "NATIVE_METADATA_OR_MIGRATION_FAILED_PRIVATE_DETAILS_NOT_EXPORTED"}))
        raise SystemExit(2)
