"""Local operator functions with explicit targets and inspectable cleanup plans."""

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
import time
from sqlalchemy import select
from app.core.exceptions import AppError
from app.modules.identity import repository
from app.modules.knowledge.models import DocumentVersion
from app.modules.knowledge.service import digest


def admin_user(db, email):
    actor = repository.get_user_by_email(db, email)
    if not actor or actor.status != "active" or actor.role.name != "admin":
        raise AppError("FORBIDDEN", detail="An existing active local administrator is required.")
    return actor


def password_from_env(name):
    value = os.environ.get(name)
    if not value:
        raise AppError(
            "VALIDATION_FAILED",
            detail=f"Set {name} in the local process environment; passwords are not accepted on the command line.",
        )
    return value


def cleanup_plan(db, settings, min_age_seconds=3600):
    root = Path(settings.storage_root).resolve()
    referenced = set()
    for value in db.scalars(select(DocumentVersion.storage_path)):
        path = Path(value)
        referenced.add((path if path.is_absolute() else root / path).resolve())
    candidates = []
    originals = root / "originals"
    for path in sorted(originals.glob("*")) if originals.exists() else []:
        resolved = path.resolve()
        if (
            not re.fullmatch(r"[0-9a-f]{64}\.(txt|pdf)", path.name)
            or path.is_symlink()
            or not resolved.is_relative_to(root)
            or not path.is_file()
            or resolved in referenced
        ):
            continue
        if time.time() - path.stat().st_mtime < min_age_seconds:
            continue
        candidates.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
        )
    return {
        "version": "orphan-cleanup-v1",
        "storage_root": str(root),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "min_age_seconds": min_age_seconds,
        "candidates": candidates,
        "plan_hash": digest(candidates),
    }


def apply_cleanup(db, settings, plan):
    root = Path(settings.storage_root).resolve()
    if (
        plan.get("version") != "orphan-cleanup-v1"
        or plan.get("storage_root") != str(root)
        or digest(plan.get("candidates")) != plan.get("plan_hash")
    ):
        raise AppError("VALIDATION_FAILED", detail="Cleanup plan identity or integrity is invalid.")
    # Hold a short shared lock while rechecking references and deleting exact
    # immutable orphan files. Uploads only add references after writing bytes;
    # the age guard excludes fresh/in-progress uploads.
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text

        db.execute(text("SELECT pg_advisory_xact_lock(5703002)"))
    current = cleanup_plan(db, settings, max(3600, int(plan.get("min_age_seconds", 3600))))
    eligible = {item["path"]: item for item in current["candidates"]}
    for item in plan["candidates"]:
        if eligible.get(item["path"]) != item:
            raise AppError(
                "CONFLICT",
                detail="A cleanup candidate changed or became referenced; create a fresh plan.",
            )
    for item in plan["candidates"]:
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root) or path == root:
            raise AppError("VALIDATION_FAILED")
        path.unlink()
    db.commit()
    return {
        "removed": len(plan["candidates"]),
        "bytes_removed": sum(item["size"] for item in plan["candidates"]),
        "plan_hash": plan["plan_hash"],
    }
