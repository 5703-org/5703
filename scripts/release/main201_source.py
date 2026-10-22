"""Exact Main201 public-file operations; runtime is owned by upgrade_main201.py."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile

PUBLIC_ROOTS = {"backend", "configs", "contracts", "conversation", "docs", "evidence", "frontend", "generation", "personalisation", "pipelines", "retrieval", "tests", "scripts"}
SUPPORT = ("backend/alembic.ini", "requirements.lock", "backend/requirements.txt")

def require(value, code):
    if not value:
        raise RuntimeError(code)


def pin(path):
    data = Path(path).read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def public_path(name):
    p = PurePosixPath(name)
    parts = p.parts
    require(parts and not p.is_absolute() and ".." not in parts and "\\" not in name
            and ":" not in name and "\x00" not in name,
            "UNSAFE_SOURCE_PATH")
    require(name == p.as_posix() and all(x and x == x.rstrip(" .") and not any(ord(c) < 32 for c in x)
            and x.split(".")[0].upper() not in {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)}, *{f"LPT{i}" for i in range(1, 10)}}
            for x in parts), "WINDOWS_AMBIGUOUS_SOURCE_PATH_REFUSED")
    require(parts[0] in PUBLIC_ROOTS or name in {"pyproject.toml", "start_project.ps1", "start_candidate.ps1", *SUPPORT}, "NOT_ALLOWLISTED_PUBLIC_SOURCE")
    require(not any(x.lower() in {".secrets", ".venv", "node_modules", "storage", "__pycache__", "runtime", "private", "private_runs", "browser-profiles"}
                    or x.lower().startswith(".env") for x in parts), "PRIVATE_OR_DEPENDENCY_PATH_REFUSED")
    require(not name.lower().endswith((".db", ".dump", ".key", ".pem", ".pyc")), "PRIVATE_FILE_REFUSED")
    return p


def regular(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.exists():
            require(not item.is_symlink() and not (item.stat().st_file_attributes & 0x400
                    if os.name == "nt" else False), "REPARSE_PATH_REFUSED")
    return path.resolve()


def independent(path, workspace, protected):
    path, workspace = regular(path), regular(workspace)
    require(path != workspace and path.is_relative_to(workspace), "TARGET_MUST_BE_INSIDE_EXPLICIT_WORKSPACE")
    require(protected, "EXPLICIT_PROTECTED_ROOT_REQUIRED")
    for root in protected:
        root = regular(root)
        require(path != root and not path.is_relative_to(root) and not root.is_relative_to(path),
                "PROTECTED_ROOT_OVERLAP_REFUSED")
    return path


def atomic_source(path, data):
    path = regular(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".up-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def protected_pins(root):
    # Hash only these existing files; never copy, parse, print or change their contents.
    result = []
    for name in (".env", ".secrets/model-config.key"):
        path = regular(root / name)
        if path.is_file():
            result.append(pin(path))
    return result


def upgrade(instance_plan, legacy_root, backup, services_stopped=False):
    require(services_stopped, "EXPLICIT_TARGET_SERVICES_STOPPED_ACK_REQUIRED")
    _, plan, rows = preflight(instance_plan, legacy_root)
    target = regular(legacy_root)
    backup = independent(backup, plan["workspace_root"], plan["protected_roots"])
    require(not backup.exists() and not backup.is_relative_to(target) and not target.is_relative_to(backup),
            "FRESH_SEPARATE_BACKUP_REQUIRED")
    payload = regular(plan["source_root"])
    require(not backup.is_relative_to(payload) and not payload.is_relative_to(backup), "BACKUP_PAYLOAD_OVERLAP_REFUSED")
    protected = protected_pins(target)
    changed = [r for r in rows if r["before"] != r["after"]]
    backup.mkdir(parents=True)
    journal = {"schema": "main201_direct_source_journal_v1", "status": "APPLYING",
               "target": str(target), "payload_plan": pin(Path(instance_plan)), "rows": changed,
               "workspace_root": plan["workspace_root"], "protected_roots": plan["protected_roots"],
               "installed": [], "protected_files": protected, "database_actions": 0,
               "credential_contents_exported": False}
    journal_path = backup / "journal.json"
    write_new(journal_path, journal)
    for row in changed:
        path = target / row["path"]
        if row["before"] is not None:
            dest = backup / "public-preimages" / row["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as stream:
                stream.write(path.read_bytes())
        # Recheck ownership immediately before the atomic source swap.
        require(not path.exists() if row["before"] is None else pin(path)["sha256"] == row["before"]["sha256"],
                "TARGET_CHANGED_DURING_UPGRADE")
        source = next(r["source"] for r in plan["source_files"] if r["path"] == row["path"])
        data = regular(source).read_bytes()
        require(hashlib.sha256(data).hexdigest() == row["after"]["sha256"], "PAYLOAD_CHANGED_DURING_UPGRADE")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, stage_name = tempfile.mkstemp(prefix=".up-", suffix=".tmp", dir=path.parent)
        stage = Path(stage_name)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        journal["pending"] = {"path": row["path"], "stage": str(stage)}
        atomic_source(journal_path, (json.dumps(journal, indent=2) + "\n").encode())
        if row["before"] is None:
            if os.name == "nt":
                os.rename(stage, path)  # Windows refuses an existing destination.
            else:
                os.link(stage, path); stage.unlink()  # Atomic no-replace creation.
        else:
            os.replace(stage, path)
        journal["installed"].append(row["path"])
        journal.pop("pending")
        atomic_source(journal_path, (json.dumps(journal, indent=2) + "\n").encode())
    require(protected_pins(target) == protected, "PROTECTED_FILE_DRIFT")
    require(all(pin(target / r["path"])["sha256"] == r["after"]["sha256"] for r in rows),
            "POST_APPLY_PROJECTION_DRIFT")
    journal["status"] = "APPLIED_PUBLIC_SOURCE_ONLY_DB_MIGRATION_NOT_RUN"
    atomic_source(journal_path, (json.dumps(journal, indent=2) + "\n").encode())
    return {"status": journal["status"], "journal": pin(journal_path), "changed_public_files": len(changed),
            "unchanged_public_files": len(rows) - len(changed), "protected_files_identical": True,
            "database_actions": 0, "provider_calls": 0}


def rollback(journal_path):
    journal_path = regular(journal_path)
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    require(journal["schema"] == "main201_direct_source_journal_v1", "UPGRADE_JOURNAL_REQUIRED")
    target = independent(journal["target"], journal["workspace_root"], journal["protected_roots"])
    backup = independent(journal_path.parent, journal["workspace_root"], journal["protected_roots"])
    require(not backup.is_relative_to(target) and not target.is_relative_to(backup),
            "INDEPENDENT_ROLLBACK_REQUIRED")
    require(protected_pins(target) == journal["protected_files"], "PROTECTED_FILE_DRIFT")
    owned = set(journal["installed"])
    if journal.get("pending"):
        row = next(r for r in journal["rows"] if r["path"] == journal["pending"]["path"])
        path = regular(target / row["path"])
        stage = regular(journal["pending"]["stage"])
        require(stage.parent == path.parent and stage.name.startswith(".up-"), "OWNED_STAGE_PATH_REQUIRED")
        if not stage.exists() and path.exists() and pin(path)["sha256"] == row["after"]["sha256"]:
            owned.add(row["path"])
        elif stage.exists():
            require(pin(stage)["sha256"] == row["after"]["sha256"], "OWNED_STAGE_DRIFT")
            require(not path.exists() if row["before"] is None else pin(path)["sha256"] == row["before"]["sha256"],
                    "AMBIGUOUS_PENDING_SWAP_REFUSED")
    # Validate the complete rollback before restoring any source file.
    for row in journal["rows"]:
        public_path(row["path"])
        if row["path"] in owned:
            require(pin(regular(target / row["path"]))["sha256"] == row["after"]["sha256"],
                    "ROLLBACK_EXTERNAL_CHANGE_REFUSED")
            if row["before"] is not None:
                require(pin(regular(backup / "public-preimages" / row["path"]))["sha256"] == row["before"]["sha256"],
                        "PREIMAGE_DRIFT")
    for row in reversed(journal["rows"]):
        if row["path"] not in owned:
            continue
        public_path(row["path"])
        path = regular(target / row["path"])
        require(pin(path)["sha256"] == row["after"]["sha256"], "ROLLBACK_EXTERNAL_CHANGE_REFUSED")
        if row["before"] is None:
            path.unlink()  # Only a journal-owned exact newly installed file.
        else:
            preimage = regular(backup / "public-preimages" / row["path"])
            require(pin(preimage)["sha256"] == row["before"]["sha256"], "PREIMAGE_DRIFT")
            atomic_source(path, preimage.read_bytes())
    if journal.get("pending") and Path(journal["pending"]["stage"]).exists():
        Path(journal["pending"]["stage"]).unlink()
    require(protected_pins(target) == journal["protected_files"], "PROTECTED_FILE_DRIFT")
    result = {"status": "ROLLED_BACK_PUBLIC_SOURCE_ONLY", "restored_files": len(owned),
              "protected_files_identical": True, "database_actions": 0}
    write_new(backup / "rollback-result.json", result)
    return result


def normalized(row):
    return {key: row[key] for key in ("path", "bytes", "sha256")}


def inventory_hash(rows):
    return hashlib.sha256(json.dumps(sorted([normalized(row) for row in rows], key=lambda row: row["path"]),
                                    sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def release_rows(value):
    """Validate a complete installed-source manifest without following its authority path."""
    require(value["schema"] == "direct_native_upgrade_release_v1", "INSTALLED_RELEASE_SCHEMA_REQUIRED")
    rows = value["source_rows"]
    require(isinstance(rows, list) and 0 < len(rows) <= 20000
            and type(value["source_row_count"]) is int and value["source_row_count"] == len(rows),
            "COMPLETE_INSTALLED_SOURCE_COUNT_REQUIRED")
    seen = set()
    for row in rows:
        public_path(row["path"])
        require(row["path"].casefold() not in seen and type(row["bytes"]) is int and row["bytes"] >= 0
                and isinstance(row["sha256"], str) and len(row["sha256"]) == 64
                and all(c in "0123456789abcdef" for c in row["sha256"]), "UNIQUE_VALID_INSTALLED_SOURCE_ROWS_REQUIRED")
        seen.add(row["path"].casefold())
    require(inventory_hash(rows) == value["source_inventory_sha256"], "EXACT_INSTALLED_SOURCE_INVENTORY_REQUIRED")
    sha = value["source_authority_sha256"]
    require(isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)
            and sha == value["source_authority"]["sha256"], "EXACT_INSTALLED_SOURCE_AUTHORITY_REQUIRED")
    return [normalized(row) for row in rows]


def read_installed_baseline(project, expected_path, expected_sha256):
    """Match an existing release to the delivery's pinned, complete predecessor."""
    expected_path = regular(expected_path)
    require(pin(expected_path)["sha256"] == expected_sha256, "PINNED_INSTALLED_BASELINE_REQUIRED")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected_rows = release_rows(expected)
    actual_path = regular(Path(project) / "UPGRADE_MANIFEST.json")
    actual_pin = pin(actual_path)
    actual = json.loads(actual_path.read_text(encoding="utf-8"))
    actual_rows = release_rows(actual)
    require(actual["source_authority_sha256"] == expected["source_authority_sha256"]
            and actual["migration_head"] == expected["migration_head"]
            and sorted(actual_rows, key=lambda row: row["path"]) == sorted(expected_rows, key=lambda row: row["path"]),
            "EXACT_REVIEWED_INSTALLED_BASELINE_REQUIRED")
    for row in actual_rows:
        current = pin(regular(Path(project) / row["path"]))
        require(all(current[key] == row[key] for key in ("bytes", "sha256")), "INSTALLED_BASELINE_SOURCE_DRIFT")
    require(pin(actual_path) == actual_pin, "INSTALLED_MANIFEST_CHANGED_DURING_PLAN")
    return actual, actual_pin


def install_release(project, release, backup, before=None):
    """Journal and preserve an exact prior runtime manifest before replacing it."""
    project, backup = regular(project), regular(backup)
    require(not backup.is_relative_to(project) and not project.is_relative_to(backup), "SEPARATE_RELEASE_BACKUP_REQUIRED")
    path = regular(project / "UPGRADE_MANIFEST.json")
    release_rows(release)
    if before is None:
        require(not path.exists(), "PRESERVE_UNOWNED_UPGRADE_RELEASE_MANIFEST")
    else:
        require(regular(before["path"]) == path and pin(path) == before, "EXACT_PREVIOUS_RELEASE_METADATA_REQUIRED")
    raw = (json.dumps(release, indent=2) + "\n").encode()
    after = {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    record = {"schema": "direct_native_release_replacement_v1", "status": "PREPARED_RELEASE_METADATA_REPLACEMENT",
              "project": str(project), "before": before, "after": after, "before_backup": None}
    if before is not None:
        previous = backup / "release-preimage.json"
        with previous.open("xb") as stream:
            stream.write(path.read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
        record["before_backup"] = pin(previous)
        require(all(record["before_backup"][key] == before[key] for key in ("bytes", "sha256")), "RELEASE_PREIMAGE_DRIFT")
    journal = backup / "release-update.json"
    with journal.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    require(not path.exists() if before is None else pin(path) == before, "RELEASE_CHANGED_BEFORE_REPLACEMENT")
    if before is None:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    else:
        atomic_source(path, raw)
    require(pin(path) == after, "RELEASE_METADATA_REPLACEMENT_DRIFT")
    record["status"] = "APPLIED_RELEASE_METADATA_REPLACEMENT"
    atomic_source(journal, (json.dumps(record, indent=2) + "\n").encode())
    return {"status": record["status"], "journal": pin(journal), "before": before, "after": after}


def restore_previous_release(project, backup, *, verify_only=False):
    """Validate metadata rollback before any source rollback; retain legacy no-preimage behavior."""
    project, backup = regular(project), regular(backup)
    journal = regular(backup / "release-update.json")
    require(not backup.is_relative_to(project) and not project.is_relative_to(backup), "SEPARATE_RELEASE_BACKUP_REQUIRED")
    record = json.loads(journal.read_text(encoding="utf-8"))
    path = regular(project / "UPGRADE_MANIFEST.json")
    require(record["schema"] == "direct_native_release_replacement_v1" and regular(record["project"]) == project
            and record["status"] in {"PREPARED_RELEASE_METADATA_REPLACEMENT", "APPLIED_RELEASE_METADATA_REPLACEMENT"}
            and regular(record["after"]["path"]) == path, "EXACT_INSTALLED_RELEASE_ROLLBACK_REQUIRED")
    current = pin(path) if path.exists() else None
    before = record["before"]
    if before is None:
        if current is None and record["status"] == "PREPARED_RELEASE_METADATA_REPLACEMENT":
            return {"status": "NO_SUCCESSOR_RUNTIME_MANIFEST_CREATED", "metadata_mutations": 0}
        require(current == record["after"], "EXACT_INSTALLED_RELEASE_ROLLBACK_REQUIRED")
        return {"status": "RETAINED_SUCCESSOR_RELEASE_NO_PREVIOUS_MANIFEST", "metadata_mutations": 0}
    previous = regular(record["before_backup"]["path"])
    require(previous == backup / "release-preimage.json" and regular(before["path"]) == path
            and pin(previous) == record["before_backup"]
            and all(record["before_backup"][key] == before[key] for key in ("bytes", "sha256")), "EXACT_RELEASE_ROLLBACK_PREIMAGE_REQUIRED")
    if current == before and record["status"] == "PREPARED_RELEASE_METADATA_REPLACEMENT":
        return {"status": "PREVIOUS_RUNTIME_RELEASE_MANIFEST_UNCHANGED", "metadata_mutations": 0, "restored": before}
    require(current == record["after"], "EXACT_INSTALLED_RELEASE_ROLLBACK_REQUIRED")
    if verify_only:
        return {"status": "PASS_PREVIOUS_RELEASE_ROLLBACK_PREFLIGHT", "metadata_mutations": 0}
    atomic_source(path, previous.read_bytes())
    require(pin(path) == before, "PREVIOUS_RELEASE_RESTORE_DRIFT")
    return {"status": "RESTORED_PREVIOUS_RUNTIME_RELEASE_MANIFEST", "metadata_mutations": 1, "restored": pin(path)}


def preflight(instance_plan, legacy_root):
    plan = json.loads(regular(instance_plan).read_text())
    require(plan["schema"] == "main201_direct_source_plan_v1", "EXACT_MAIN201_PLAN_REQUIRED")
    target = independent(legacy_root, plan["workspace_root"], plan["protected_roots"])
    require(str(target) == plan["target"], "EXACT_PLANNED_TARGET_REQUIRED")
    if plan["baseline_kind"] == "Main201":
        require(pin(target / "PACKAGE_MANIFEST.json")["sha256"] == plan["baseline_manifest_sha256"], "ORIGINAL_MAIN201_MANIFEST_CHANGED")
    if plan["baseline_kind"] == "installed":
        require(pin(regular(target / "UPGRADE_MANIFEST.json")) == plan["baseline_release"], "INSTALLED_RELEASE_CHANGED_AFTER_PLAN")
    else:
        require(not regular(target / "UPGRADE_MANIFEST.json").exists(), "UNOWNED_RUNTIME_MANIFEST_BEFORE_SOURCE_APPLY")
    for row in plan["baseline_rows"]:
        public_path(row["path"])
        actual = pin(regular(target / row["path"]))
        require(all(actual[k] == row[k] for k in ("bytes", "sha256")), "EXACT_MAIN201_BASELINE_REQUIRED")
    rows = plan["files"]
    for row in rows:
        public_path(row["path"])
        path = regular(target / row["path"])
        require(not path.exists() if row["before"] is None else pin(path)["sha256"] == row["before"]["sha256"], "EXACT_MAIN201_PREIMAGE_REQUIRED")
        source = next(item["source"] for item in plan["source_files"] if item["path"] == row["path"])
        actual = pin(regular(source))
        require(all(actual[k] == row["after"][k] for k in ("bytes", "sha256")), "PINNED_FINAL_PAYLOAD_CHANGED")
    return {"status": "PASS_EXACT_MAIN201_SOURCE_AND_PAYLOAD", "required_public_files": len(rows), "runtime_acceptance": False}, plan, rows


def verify(instance_plan, target):
    plan = json.loads(regular(instance_plan).read_text())
    require(str(regular(target)) == plan["target"], "EXACT_PLANNED_TARGET_REQUIRED")
    for row in plan["source_files"]:
        actual = pin(regular(Path(target) / row["path"]))
        require(all(actual[k] == row[k] for k in ("bytes", "sha256")), "FINAL_SOURCE_PROJECTION_DRIFT")
    return {"status": "PASS_FINAL_PUBLIC_SOURCE", "required_rows": len(plan["source_files"]), "runtime_acceptance": False}
