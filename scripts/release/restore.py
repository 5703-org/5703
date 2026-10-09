"""Restore to a distinct empty database and verify source/answer identities."""

import argparse
import json
from pathlib import Path
import re
import shutil
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from app.core.config import Settings
from .common import execute, file_hash, fingerprint, postgres_command


def restore(manifest_path, target_database, target_storage, settings, postgres_container=None):
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") not in ("backup-v1", "backup-v2"):
        raise ValueError("Unsupported backup manifest.")
    source_url = make_url(settings.database_url)
    if (
        not re.fullmatch(r"[a-z][a-z0-9_]{2,62}", target_database)
        or target_database == source_url.database
    ):
        raise ValueError(
            "Use a distinct explicitly named target database with lowercase letters, digits and underscores."
        )
    root = Path(target_storage).resolve()
    if root == Path(settings.storage_root).resolve() or root.exists() and any(root.iterdir()):
        raise ValueError("The restored source directory must be distinct and empty.")
    base = manifest_path.parent
    entries = [manifest["database"], *manifest["sources"], *manifest.get("supplements", [])]
    for entry in entries:
        path = (base / entry["path"]).resolve()
        if (
            not path.is_relative_to(base)
            or not path.is_file()
            or file_hash(path) != entry["sha256"]
        ):
            raise ValueError("Backup path or hash validation failed.")
    for entry in manifest.get("supplements", []):
        if not (root / entry["storage_path"]).resolve().is_relative_to(root):
            raise ValueError("Restored extraction artifact path escapes target storage.")
    admin = create_engine(source_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    target_url = source_url.set(database=target_database)
    try:
        with admin.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname=:name"), {"name": target_database}
            )
            if exists:
                raise ValueError(
                    "Restore refuses an existing database. Choose a fresh target; no existing data will be overwritten."
                )
            connection.execute(text(f'CREATE DATABASE "{target_database}"'))
        command, environment = postgres_command("pg_restore", target_url, postgres_container)
        command += ["--no-owner", "--exit-on-error"]
        with (base / manifest["database"]["path"]).open("rb") as source:
            execute(command, environment, stdin=source, stdout=None)
        root.mkdir(parents=True, exist_ok=True)
        restored = create_engine(target_url)
        try:
            with restored.begin() as connection:
                for entry in manifest["sources"]:
                    target = root / entry["sha256"]
                    shutil.copyfile(base / entry["path"], target)
                    connection.execute(
                        text("UPDATE document_versions SET storage_path=:path WHERE id=:id"),
                        # Relative paths follow ingestion's STORAGE_ROOT contract
                        # and keep the restored corpus portable across OS/mounts.
                        {"path": entry["sha256"], "id": entry["version_id"]},
                    )
                for entry in manifest.get("supplements", []):
                    target = root / entry["storage_path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(base / entry["path"], target)
            with restored.connect() as connection:
                actual = fingerprint(
                    connection, include_identity=manifest["version"] == "backup-v2"
                )
            if actual != manifest["fingerprint"]:
                raise RuntimeError("Restore data fingerprint does not match the source snapshot.")
        finally:
            restored.dispose()
        result = {
            "status": "passed",
            "target_database": target_database,
            "target_storage": str(root),
            "fingerprint": actual,
            "sources_verified": len(manifest["sources"]),
            "supplements_verified": len(manifest.get("supplements", [])),
        }
        (base / ("restore-" + target_database + ".json")).write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result
    finally:
        admin.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--confirm-target",
        required=True,
        help="New PostgreSQL database name, distinct from the source database",
    )
    parser.add_argument("--storage", required=True, help="New restored source directory")
    parser.add_argument("--postgres-container")
    args = parser.parse_args()
    print(
        json.dumps(
            restore(
                args.manifest,
                args.confirm_target,
                args.storage,
                Settings(),
                args.postgres_container,
            )
        )
    )


if __name__ == "__main__":
    main()
