"""Build and verify a local source handover without runtime secrets or private data."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DIRECTORIES = {
    "backend",
    "contracts",
    "conversation",
    "evaluation",
    "generation",
    "personalisation",
    "pipelines",
    "retrieval",
    "scripts",
    "tests",
    "configs",
    "docs",
    "frontend",
    ".github",
}
EXCLUDED_PARTS = {
    ".git",
    ".secrets",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
    ".browser-profiles",
    "private_runs",
    "private",
    "exports",
    "results",
    "week5",
    "evaluator-private",
}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def included(path):
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.name.startswith(".env") and path.name != ".env.example":
        return False
    if path.suffix.lower() in {".pyc", ".db", ".dump", ".sqlite", ".sqlite3", ".key", ".pem"}:
        return False
    if len(relative.parts) == 1:
        return path.name not in {"PACKAGE_MANIFEST.json"} and path.suffix.lower() in {
            ".md",
            ".json",
            ".yaml",
            ".toml",
            ".ini",
            ".lock",
            ".example",
            "",
        }
    if relative.parts[0] in DIRECTORIES:
        return True
    if relative.parts[0] == "evidence":
        if "sources" in relative.parts or any(
            part.endswith("_verification_copy") for part in relative.parts
        ):
            return False
        return path.suffix.lower() in {".json", ".md", ".txt", ".log", ".xml", ".png"}
    if relative.parts[:3] == ("artifacts", "reports", "frontend"):
        return path.suffix.lower() in {".json", ".md", ".png", ".txt"}
    return False


def verify(archive):
    with zipfile.ZipFile(archive) as bundle:
        if len(bundle.namelist()) != len(set(bundle.namelist())):
            raise ValueError("Duplicate package member names are not permitted")
        manifest = json.loads(bundle.read("learning-assistant/PACKAGE_MANIFEST.json"))
        if len(manifest["files"]) != len({item["path"] for item in manifest["files"]}):
            raise ValueError("Duplicate manifest paths are not permitted")
        expected = {"learning-assistant/" + item["path"]: item for item in manifest["files"]}
        actual = set(bundle.namelist()) - {"learning-assistant/PACKAGE_MANIFEST.json"}
        if actual != set(expected):
            raise ValueError("Package membership differs from its manifest")
        for name, item in expected.items():
            parts = Path(name).parts
            if Path(name).is_absolute() or ".." in parts or name.startswith(("/", "\\")):
                raise ValueError("Unsafe package path")
            value = bundle.read(name)
            if len(value) != item["bytes"] or digest(value) != item["sha256"]:
                raise ValueError("Package member failed hash verification: " + name)
        return {
            "status": "passed",
            "verified_files": len(expected),
            "manifest_sha256": digest(bundle.read("learning-assistant/PACKAGE_MANIFEST.json")),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/deliverables/CS30-1_local_project_2026-09-08.zip",
    )
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify)))
        return
    target = args.output.resolve()
    if target.exists():
        raise ValueError("Choose a new package path; previous handovers are never overwritten")
    target.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(
        (path for path in ROOT.rglob("*") if path.is_file() and included(path)),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    manifest = {
        "version": "cs30-local-source-handover-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Local source, English project documents, tests, configuration examples and saved execution evidence. Runtime data is separately preserved at the documented workspace/storage/backup paths.",
        "answer_model_mode": "mock",
        "excluded": [
            "actual environment files and private keys",
            "database dumps and live/restored databases",
            "original textbook PDF bytes and model weights",
            "SciQ evaluator-private inputs/projections/labels",
            "private experiment exports",
            "dependency caches",
            "original user-supplied archives/documents and untouched source tree",
        ],
        "source_notice": "Original attachments and prior source evidence remain at their recorded local paths; see docs/foundation/source_inventory.md and docs/execution/source_files.json. OpenStax excerpts/review images in evidence retain the upstream terms in SOURCE_NOTICES.md.",
        "files": [],
    }
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in files:
            value = path.read_bytes()
            relative = path.relative_to(ROOT).as_posix()
            manifest["files"].append(
                {"path": relative, "bytes": len(value), "sha256": digest(value)}
            )
            bundle.writestr("learning-assistant/" + relative, value)
        bundle.writestr(
            "learning-assistant/PACKAGE_MANIFEST.json",
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        )
    result = {
        **verify(target),
        "archive": str(target),
        "archive_bytes": target.stat().st_size,
        "archive_sha256": digest(target.read_bytes()),
        "created_at": manifest["created_at"],
    }
    target.with_suffix(".verification.json").write_text(
        json.dumps(result, indent=2) + "\n", "utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
