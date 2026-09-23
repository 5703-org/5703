"""Package the complete Week 8 runtime and disjoint GitHub contribution folders."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import zipfile

from dotenv import dotenv_values
from scripts.release.package import ROOT, DIRECTORIES, EXCLUDED_PARTS, included
from scripts.release.upgrade_delivery import MEMBERS, owner

FULL_NAME = "CS30-1_Week08_Complete_Project_20260916.zip"
MEMBER_PREFIX = "CS30-1_Week08"
REPORT_ROOT = "docs/delivery/week08"
TEMPORARY_PARTS = {"pytest-temp", "pytest-cache", ".pytest-temp"}
NEW_OWNERS = {
    "conversation/understanding.py": 2,
    "retrieval/runtime.py": 2,
    "retrieval/relevance.py": 2,
    "requirements-embeddings-cpu.lock": 2,
    "tests/unit/test_runtime_device.py": 7,
    "tests/unit/test_query_reliability.py": 7,
    "tests/integration/test_query_reliability.py": 7,
    "scripts/verify/retrieval_reliability.py": 2,
    "docs/execution/reliability-review-20260916.md": 0,
    "generation/teaching.py": 4,
}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def safe_name(name):
    parts = name.replace("\\", "/").split("/")
    if name.startswith(("/", "\\")) or any(p in {"..", ".", ""} for p in parts):
        raise ValueError("Unsafe archive member: " + name)
    if ":" in name or "\\" in name:
        raise ValueError("Nonportable archive member: " + name)
    return name


def candidates():
    roots = [ROOT / name for name in sorted(DIRECTORIES)]
    roots += [ROOT / "evidence", ROOT / "artifacts/reports/frontend"]
    for path in ROOT.iterdir():
        if path.is_file() and included(path):
            yield path
    for directory in roots:
        if not directory.exists():
            continue
        for current, dirs, files in os.walk(directory):
            dirs[:] = [name for name in dirs if name not in EXCLUDED_PARTS | TEMPORARY_PARTS]
            for name in sorted(files):
                path = Path(current) / name
                if included(path):
                    if path.is_symlink():
                        raise ValueError("Resolve source symlinks before delivery: " + str(path))
                    yield path


def scan(path, secrets):
    overlap = max((len(value) for value in secrets), default=1) - 1
    tail = b""
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            value = tail + block
            if any(secret in value for secret in secrets):
                raise ValueError("A configured secret was detected in: " + str(path))
            tail = value[-overlap:] if overlap else b""


def verify_zip(path, expected):
    with zipfile.ZipFile(path) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(name.casefold() for name in names)):
            raise ValueError("Duplicate or case-aliased archive members")
        if set(names) != set(expected):
            raise ValueError("Archive membership differs from its declared inventory")
        for name, row in expected.items():
            safe_name(name)
            checksum, size = hashlib.sha256(), 0
            with bundle.open(name) as stream:
                while block := stream.read(1024 * 1024):
                    checksum.update(block)
                    size += len(block)
            if size != row["bytes"] or checksum.hexdigest() != row["sha256"]:
                raise ValueError("Archive content differs: " + name)
    return {"files": len(expected), "status": "passed"}


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def add_bytes(bundle, name, value, inventory):
    safe_name(name)
    bundle.writestr(name, value)
    inventory[name] = {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def add_file(bundle, name, path, record, inventory, stored=False):
    safe_name(name)
    if digest(path) != record["sha256"] or path.stat().st_size != record["bytes"]:
        raise ValueError("Source changed during the release freeze: " + str(path))
    bundle.write(path, name, compress_type=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED)
    inventory[name] = {"bytes": record["bytes"], "sha256": record["sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--baseline-ownership", type=Path, required=True)
    parser.add_argument("--private-env", type=Path, action="append", default=[])
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    baseline = args.baseline.resolve()
    with zipfile.ZipFile(baseline) as old:
        previous = json.loads(old.read("learning-assistant/PACKAGE_MANIFEST.json"))
    previous_files = {row["path"]: row for row in previous["files"]}
    old_ownership = json.loads(args.baseline_ownership.read_text(encoding="utf-8"))
    old_owners = {row["path"]: row["owner_index"] for row in old_ownership["files"]}
    public = dotenv_values(ROOT / ".env.example")
    secrets = set()
    for env_path in [ROOT / ".env", *args.private_env]:
        if env_path.is_file():
            for key, value in dotenv_values(env_path, encoding="utf-8-sig").items():
                if (
                    value
                    and len(value) >= 16
                    and any(x in key.upper() for x in ("KEY", "TOKEN", "PASSWORD", "SECRET"))
                ):
                    if key.upper() == "LLM_API_KEY" or value != public.get(key):
                        secrets.add(value.encode())
    paths = sorted(candidates(), key=lambda path: path.relative_to(ROOT).as_posix())
    records, source_paths = [], {}
    for path in paths:
        name = safe_name(path.relative_to(ROOT).as_posix())
        scan(path, secrets)
        index = old_owners.get(name, NEW_OWNERS.get(name, owner(name)))
        for number, member in enumerate(MEMBERS):
            if name.startswith(f"{REPORT_ROOT}/members/{member[0].replace(' ', '_')}/"):
                index = number
        if name.startswith(("evidence/", "artifacts/reports/")):
            index = 7
        before = previous_files.get(name)
        sha = digest(path)
        change = (
            "added" if before is None else "modified" if before["sha256"] != sha else "retained"
        )
        row = {
            "path": name,
            "bytes": path.stat().st_size,
            "sha256": sha,
            "owner_index": index,
            "owner": MEMBERS[index][0],
            "change": change,
            "previous_sha256": before["sha256"] if before else None,
            "category": "public_evidence"
            if name.startswith(("evidence/", "artifacts/"))
            else "project_file",
        }
        records.append(row)
        source_paths[name] = path
    resources = []
    for prefix, target in [
        ("official-corpus", "resources/official-corpus"),
        ("huggingface", "artifacts/huggingface"),
        ("tiktoken", "artifacts/tiktoken"),
    ]:
        for path in sorted((args.resources / prefix).rglob("*")):
            if not path.is_file():
                continue
            name = safe_name(target + "/" + path.relative_to(args.resources / prefix).as_posix())
            before = previous_files.get(name)
            if (
                not before
                or digest(path) != before["sha256"]
                or path.stat().st_size != before["bytes"]
            ):
                raise ValueError("Unverified or changed baseline resource: " + name)
            scan(path, secrets)
            resources.append(
                {
                    "path": name,
                    "bytes": before["bytes"],
                    "sha256": before["sha256"],
                    "category": "verified_runtime_resource",
                }
            )
            source_paths[name] = path
    if len(resources) != 80:
        raise ValueError("The complete delivery requires the same 80 verified runtime resources")
    all_names = [row["path"].casefold() for row in records + resources]
    if len(all_names) != len(set(all_names)):
        raise ValueError("Repeated or case-aliased source paths")
    delta = [row for row in records if row["change"] != "retained"]
    # Historical public evidence stays preserved; new evidence accompanies this week's commits.
    missing = sorted(
        name
        for name, row in previous_files.items()
        if row.get("category") != "verified_runtime_resource"
        and name not in source_paths
        and not TEMPORARY_PARTS.intersection(Path(name).parts)
    )
    if missing:
        raise ValueError(
            "Baseline project files disappeared; review before delivery: " + str(missing)
        )
    created = datetime.now(timezone.utc).isoformat()
    inventory = {
        "schema": "week08-github-contributions-v1",
        "created_at": created,
        "baseline": {"archive": baseline.name, "sha256": digest(baseline)},
        "scope": "Week 8 research, integrated reliability and CPU changes, documentation, reports and verification. Existing source ownership is preserved. Codex is the shared implementation executor.",
        "merge_order": [MEMBERS[i][0] for i in (0, 5, 1, 2, 4, 3, 6, 7)],
        "files": delta,
        "retained_project_files": sum(row["change"] == "retained" for row in records),
        "owner_counts": dict(Counter(row["owner"] for row in delta)),
        "resources": resources,
        "temporary_test_directories": "Excluded from distribution; original local runs and fixtures remain preserved.",
    }
    if args.plan_only:
        target = destination / "WEEK08_PREPACKAGE_PLAN.json"
        target.write_bytes(encoded(inventory))
        print(
            json.dumps(
                {
                    "plan": str(target),
                    "delta_files": len(delta),
                    "owner_counts": inventory["owner_counts"],
                    "resources": len(resources),
                }
            )
        )
        return
    report_names = [f"{REPORT_ROOT}/Week08_Overall_Report.docx"] + [
        f"{REPORT_ROOT}/members/{member[0].replace(' ', '_')}/Week08_Report.docx"
        for member in MEMBERS
    ]
    if any(name not in source_paths for name in report_names):
        raise ValueError(
            "All nine final Word reports must be copied into the project before packaging"
        )
    full = destination / FULL_NAME
    outputs = [full] + [
        destination / f"{MEMBER_PREFIX}_{i + 1:02}_{m[0].replace(' ', '_')}_20260916.zip"
        for i, m in enumerate(MEMBERS)
    ]
    if any(path.exists() for path in outputs):
        raise ValueError("Choose a new destination; previous archives remain preserved")
    manifest = {
        "version": "cs30-week08-complete-runtime-v1",
        "created_at": created,
        "runtime": "Windows x64, Python 3.13, Node/npm and Docker. CPU installation is available; CUDA can be selected with compatible installed dependencies.",
        "startup": "powershell -ExecutionPolicy Bypass -File scripts/release/start_local.ps1 -Install -Device cpu",
        "scope": "Complete current English project, reports, verified four-book corpus, 10,594 active real vectors, pinned E5/MiniLM/tokenizer resources and retained public evidence.",
        "credentials": "A fresh installation creates its own accounts and secrets; answering starts in the explicitly labelled mock mode until an administrator saves, tests and enables a provider.",
        "exclusions": [
            "existing credentials, deployment keys and .env",
            "private user history",
            "private evaluator data and labels",
            "installed dependencies and browser profiles",
            "temporary pytest execution directories",
        ],
        "files": records + resources,
    }
    archives = []
    full_expected = {}
    with zipfile.ZipFile(full, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=4) as bundle:
        for row in records + resources:
            add_file(
                bundle,
                "learning-assistant/" + row["path"],
                source_paths[row["path"]],
                row,
                full_expected,
                row["category"] == "verified_runtime_resource",
            )
        add_bytes(
            bundle, "learning-assistant/WEEK08_CHANGESET.json", encoded(inventory), full_expected
        )
        # Include the generated changeset in the per-file manifest as well.
        changeset = full_expected["learning-assistant/WEEK08_CHANGESET.json"]
        manifest["files"].append(
            {"path": "WEEK08_CHANGESET.json", **changeset, "category": "release_metadata"}
        )
        add_bytes(
            bundle, "learning-assistant/PACKAGE_MANIFEST.json", encoded(manifest), full_expected
        )
    archives.append(
        {
            "path": full.name,
            "bytes": full.stat().st_size,
            "sha256": digest(full),
            **verify_zip(full, full_expected),
        }
    )
    seen = set()
    for i, member in enumerate(MEMBERS):
        name, sid, prefix, count, chats, domain = member
        slug = name.replace(" ", "_")
        selected = [row for row in delta if row["owner_index"] == i]
        if not selected:
            raise ValueError("Each owner needs their actual weekly research/report contribution")
        expected = {}
        package = outputs[i + 1]
        task_ids = [f"{prefix}-{n:02}" for n in range(1, count + 1)] + [
            f"CHAT-{n:02}" for n in chats
        ]
        readme = f"# Week 8 contribution for {name}\n\nStudent ID: {sid}. Workstream: {domain}.\n\nThis package contains {len(selected)} added or changed files relative to the verified 13 September complete delivery. `repo_files/` preserves their paths in the shared project. The Word report and Markdown record are in `repo_files/{REPORT_ROOT}/members/{slug}/`. They cover this week's implementation and research, verification and Week 9 goals.\n\n## Submit to GitHub\n\n1. Create your working branch from the team's current integrated repository.\n2. Compare `OWNED_FILES.json` with the checkout. For existing files, inspect any difference from `previous_sha256` before copying, and resolve other contributors' edits.\n3. Copy the contents of `repo_files/` into the repository while preserving relative paths. Review `git diff` and the listed new files.\n4. Use `COMMIT_MESSAGE.txt` and `PR_BODY.md` as the submission text after your review. Commit only these assigned paths.\n5. Link your pull request in the team integration record. The team integrates owners in the sequence recorded in the overall inventory.\n\nOriginal task scope: {', '.join(task_ids)}. The reports and file ownership describe assigned responsibility; Codex performed shared implementation. No GitHub commit or upload is performed by this package.\n\nUse the complete Week 8 archive for shared resources and startup. Checkpoint weights, textbooks, credentials and installed dependencies are outside these small GitHub contribution packages.\n"
        pr = f"# Week 8 {domain.lower()}\n\nThis contribution records the Week 8 reliability and CPU work assigned to {name}, including the relevant research/design findings and Week 9 goals.\n\nRead `{REPORT_ROOT}/members/{slug}/Week08_Report.md` for exact completed work and validation limits. `OWNED_FILES.json` identifies every submitted file and its baseline hash.\n\nValidation evidence and the current full software gate are linked from the Week 8 project report. Keep the earlier 331 Python/51 frontend gate and two real CPU diagnostic runs dated; use the final delivery evidence for any later installation or runtime checks.\n"
        with zipfile.ZipFile(
            package, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as bundle:
            add_bytes(bundle, slug + "/README.md", readme.encode(), expected)
            add_bytes(
                bundle,
                slug + "/OWNED_FILES.json",
                encoded(
                    {
                        "owner": name,
                        "student_id": sid,
                        "domain": domain,
                        "task_ids": task_ids,
                        "baseline": inventory["baseline"],
                        "files": selected,
                    }
                ),
                expected,
            )
            add_bytes(
                bundle,
                slug + "/COMMIT_MESSAGE.txt",
                f"Week 8 {name} reliability and CPU contribution\n".encode(),
                expected,
            )
            add_bytes(bundle, slug + "/PR_BODY.md", pr.encode(), expected)
            for row in selected:
                if row["path"] in seen:
                    raise ValueError("Overlapping member file ownership")
                seen.add(row["path"])
                add_file(
                    bundle,
                    slug + "/repo_files/" + row["path"],
                    source_paths[row["path"]],
                    row,
                    expected,
                )
        archives.append(
            {
                "path": package.name,
                "owner": name,
                "assigned_files": len(selected),
                "bytes": package.stat().st_size,
                "sha256": digest(package),
                **verify_zip(package, expected),
            }
        )
    if seen != {row["path"] for row in delta}:
        raise ValueError("Member union differs from the complete weekly change set")
    (destination / "EIGHT_MEMBER_INVENTORY.json").write_bytes(encoded(inventory))
    (destination / "PACKAGE_VERIFICATION.json").write_bytes(
        encoded(
            {
                "created_at": created,
                "archives": archives,
                "delta_files": len(delta),
                "member_union_exact": True,
                "overlapping_paths": 0,
                "verified_resources": len(resources),
            }
        )
    )
    print(
        json.dumps(
            {
                "archives": len(archives),
                "delta_files": len(delta),
                "complete_bytes": full.stat().st_size,
                "destination": str(destination),
            }
        )
    )


if __name__ == "__main__":
    main()
