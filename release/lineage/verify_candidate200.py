"""Verify this candidate's declared public files without changing runtime state."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat


def need(condition: bool, code: str, path: str = "") -> None:
    if not condition:
        raise ValueError(code + (": " + path if path else ""))


def public_path(root: Path, value: str) -> Path:
    need(isinstance(value, str) and bool(value), "INVALID_PUBLIC_PATH")
    relative = PurePosixPath(value)
    need(
        not relative.is_absolute()
        and relative.as_posix() == value
        and "\\" not in value
        and ":" not in value
        and all(part not in {"", ".", ".."} for part in relative.parts),
        "INVALID_PUBLIC_PATH",
    )
    for part in relative.parts:
        need(
            part.rstrip(" .") == part
            and not any(ord(char) < 32 for char in part)
            and part.casefold() not in {".secrets", ".git", ".aws", ".codex", "node_modules", ".venv", "evaluator-private"}
            and (not part.casefold().startswith(".env") or value == ".env.example"),
            "PRIVATE_OR_RUNTIME_PATH_REFUSED",
        )
    need(relative.suffix.casefold() not in {".key", ".pem", ".db", ".dump", ".sqlite", ".sqlite3"}, "PRIVATE_OR_RUNTIME_PATH_REFUSED")
    target = root.joinpath(*relative.parts)
    need(target.resolve().is_relative_to(root), "PUBLIC_PATH_ESCAPED")
    for item in [target, *target.parents]:
        if item == root.parent:
            break
        metadata = item.lstat()
        need(
            not stat.S_ISLNK(metadata.st_mode)
            and not (getattr(metadata, "st_file_attributes", 0) & 0x400),
            "REPARSE_OR_SYMLINK_REFUSED",
            value,
        )
    need(target.is_file(), "PUBLIC_FILE_REQUIRED", value)
    return target


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(root: Path) -> dict:
    root = root.resolve(strict=True)
    manifest_path = public_path(root, "PACKAGE_MANIFEST.json")
    manifest = json.loads(manifest_path.read_bytes())
    need(manifest.get("schema") == "cs30_complete_candidate200_v1", "UNSUPPORTED_PACKAGE_MANIFEST")
    rows = manifest.get("files")
    need(isinstance(rows, list) and bool(rows), "PUBLIC_FILE_ROWS_REQUIRED")
    seen = set()
    total = 0
    for row in rows:
        need(isinstance(row, dict), "INVALID_PUBLIC_FILE_ROW")
        value = row.get("path")
        need(isinstance(value, str), "INVALID_PUBLIC_PATH")
        need(value != "PACKAGE_MANIFEST.json" and value.casefold() not in seen, "DUPLICATE_OR_SELF_MANIFEST_PATH")
        seen.add(value.casefold())
        need(type(row.get("bytes")) is int and row["bytes"] >= 0, "INVALID_PUBLIC_FILE_SIZE", value)
        need(isinstance(row.get("sha256"), str) and re.fullmatch("[0-9a-f]{64}", row["sha256"]) is not None, "INVALID_PUBLIC_FILE_HASH", value)
        path = public_path(root, value)
        need(path.stat().st_size == row["bytes"] and file_hash(path) == row["sha256"], "PUBLIC_FILE_HASH_MISMATCH", value)
        total += row["bytes"]
    need(len(rows) == manifest.get("file_count"), "PUBLIC_FILE_COUNT_MISMATCH")
    need(total == manifest.get("file_bytes"), "PUBLIC_FILE_BYTES_MISMATCH")
    return {
        "status": "COMPLETE_CANDIDATE_PUBLIC_FILES_VERIFY_PASS",
        "manifest_status": manifest.get("status"),
        "manifest_sha256": file_hash(manifest_path),
        "public_files_verified": len(rows),
        "public_bytes_verified": total,
        "runtime_cache_dependency_or_database_checks": "NOT_PERFORMED",
        "files_written_or_services_started": 0,
        "provider_network_or_database_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.project_root)))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "COMPLETE_CANDIDATE_PUBLIC_FILES_VERIFY_FAILED", "reason": str(error)}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
