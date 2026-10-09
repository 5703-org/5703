"""PostgreSQL client invocation and independent integrity fingerprints."""

from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(connection, include_identity=True):
    counts = {
        table: connection.scalar(text(f'SELECT count(*) FROM "{table}"'))
        for table in sorted(inspect(connection).get_table_names())
    }
    values = {}
    for table, columns, order in (
        ("answers", "id, request_id, response, model_mode", "id"),
        ("evidence_snapshots", "id, answer_id, evidence_id, document_id, payload", "id"),
        ("active_corpus", "id, release_id", "id"),
        ("documents", "id, active, revoked", "id"),
        ("document_versions", "id, document_id, raw_hash", "id"),
    ):
        values[table] = [
            dict(row)
            for row in connection.execute(
                text(f"SELECT {columns} FROM {table} ORDER BY {order}")
            ).mappings()
        ]
    result = {
        "counts": counts,
        "preserved_data_sha256": hashlib.sha256(
            json.dumps(values, sort_keys=True, ensure_ascii=False, default=str).encode()
        ).hexdigest(),
        "active_release": values["active_corpus"],
    }
    if include_identity:
        identities = {
            table: [
                dict(row)
                for row in connection.execute(text(f"SELECT * FROM {table} ORDER BY id")).mappings()
            ]
            for table in ("users", "roles", "workspaces", "student_profiles")
        }
        result["identity_profiles_sha256"] = hashlib.sha256(
            json.dumps(identities, sort_keys=True, ensure_ascii=False, default=str).encode()
        ).hexdigest()
        corpus_digest = hashlib.sha256()
        for table in (
            "configurations",
            "processing_runs",
            "source_units",
            "chunks",
            "corpus_releases",
            "release_chunks",
        ):
            order = "release_id, chunk_id" if table == "release_chunks" else "id"
            corpus_digest.update(table.encode())
            for row in connection.execute(
                text(f"SELECT * FROM {table} ORDER BY {order}")
            ).mappings():
                corpus_digest.update(
                    json.dumps(dict(row), sort_keys=True, ensure_ascii=False, default=str).encode()
                )
                corpus_digest.update(b"\n")
        result["complete_corpus_sha256"] = corpus_digest.hexdigest()
    return result


def postgres_command(tool, database_url, container=None):
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        raise ValueError("This backup interface requires PostgreSQL.")
    environment = os.environ.copy()
    if container:
        # Docker uses the database container's local socket and its configured
        # operating role. No password is printed or placed in command arguments.
        command = [
            "docker",
            "exec",
            "-i",
            container,
            tool,
            "--username",
            url.username or "postgres",
            "--dbname",
            url.database,
        ]
    else:
        if not shutil.which(tool):
            raise ValueError(
                f"{tool} is not installed; provide --postgres-container for the local Compose database."
            )
        command = [
            tool,
            "--host",
            url.host or "localhost",
            "--port",
            str(url.port or 5432),
            "--username",
            url.username or "postgres",
            "--dbname",
            url.database,
        ]
        environment["PGPASSWORD"] = url.password or ""
    return command, environment


def execute(command, environment, **kwargs):
    result = subprocess.run(command, env=environment, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        # Client diagnostics should not print credentials or database URLs.
        raise RuntimeError(
            f"{command[-1].split('=')[0]} failed with exit {result.returncode}: "
            + result.stderr.decode("utf-8", errors="replace")[-1500:]
        )
    return result
