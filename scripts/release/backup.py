"""Back up one PostgreSQL snapshot and every referenced immutable source file."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from sqlalchemy import create_engine, text
from app.core.config import Settings
from .common import execute, file_hash, fingerprint, postgres_command


def backup(destination, settings, postgres_container=None):
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Choose a new or empty backup destination.")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "sources").mkdir(exist_ok=True)
    engine = create_engine(settings.database_url)
    try:
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            transaction = connection.begin()
            snapshot = connection.scalar(text("SELECT pg_export_snapshot()"))
            before = fingerprint(connection)
            rows = list(
                connection.execute(
                    text("SELECT id, raw_hash, storage_path FROM document_versions")
                ).mappings()
            )
            configurations = list(
                connection.execute(text("SELECT configuration FROM processing_runs")).scalars()
            )
            command, environment = postgres_command(
                "pg_dump", settings.database_url, postgres_container
            )
            command += ["--format=custom", "--no-owner", "--snapshot=" + snapshot]
            dump = destination / "database.dump"
            with dump.open("wb") as output:
                execute(command, environment, stdout=output)
            sources = []
            root = Path(settings.storage_root).resolve()
            for row in rows:
                stored = Path(row["storage_path"])
                source = (stored if stored.is_absolute() else root / stored).resolve()
                if not source.is_relative_to(root) or not source.is_file():
                    raise ValueError(
                        "A referenced source is outside STORAGE_ROOT or missing: " + row["id"]
                    )
                if file_hash(source) != row["raw_hash"]:
                    raise ValueError("Referenced source hash mismatch: " + row["id"])
                relative = "sources/" + row["raw_hash"]
                shutil.copyfile(source, destination / relative)
                sources.append(
                    {"version_id": row["id"], "sha256": row["raw_hash"], "path": relative}
                )
            supplements = {}

            def copy_supplement(relative, expected):
                source = (root / relative).resolve()
                if (
                    not source.is_relative_to(root)
                    or not source.is_file()
                    or file_hash(source) != expected
                ):
                    raise ValueError(
                        "A referenced extraction artifact is missing or its hash differs."
                    )
                relative = source.relative_to(root).as_posix()
                existing = supplements.get(relative)
                if existing and existing["sha256"] != expected:
                    raise ValueError("Conflicting hashes reference the same extraction artifact.")
                destination_path = "sources/" + expected
                if not existing:
                    shutil.copyfile(source, destination / destination_path)
                    supplements[relative] = {
                        "storage_path": relative,
                        "sha256": expected,
                        "path": destination_path,
                    }
                return source

            for configuration in configurations:
                for item in configuration.get("source_supplements", []):
                    source = copy_supplement(
                        item["storage_path"], item.get("html_sha256") or item["artifact_sha256"]
                    )
                    if item["kind"] == "pdf_image_transcription":
                        artifact = json.loads(source.read_text(encoding="utf-8"))
                        copy_supplement(artifact["render_storage_path"], artifact["render_sha256"])
                        copy_supplement(artifact["ocr_storage_path"], artifact["ocr_sha256"])
            transaction.commit()
        manifest = {
            "version": "backup-v2",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database": {"path": "database.dump", "sha256": file_hash(dump)},
            "sources": sources,
            "supplements": list(supplements.values()),
            "fingerprint": before,
            "consistency": "single PostgreSQL exported snapshot plus hash-verified immutable originals, publisher/OCR artifacts and complete identity/profile fingerprints",
        }
        path = destination / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return path
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--postgres-container")
    args = parser.parse_args()
    print(backup(args.destination, Settings(), args.postgres_container))


if __name__ == "__main__":
    main()
