"""Public September 21 runtime and eight verified deltas; research stays separate."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import zipfile

from dotenv import dotenv_values
from scripts.release.package import ROOT, DIRECTORIES, EXCLUDED_PARTS
from scripts.release.upgrade_delivery import MEMBERS, owner
from scripts.release.week08_enhancement_delivery import (
    NEW_OWNERS,
    add_bytes,
    add_file,
    digest,
    encoded,
    safe_name,
    verify_zip,
)

FULL_NAME = "CS30-1_Week08_Memory_V2_Complete_Project_20260921.zip"
PREFIX = "CS30-1_Week08_Memory_V2"
REPORT_ROOT = "docs/delivery/week08-memory-v2"
CHANGESET = "WEEK08_MEMORY_V2_CHANGESET.json"
TEMPORARY = {"pytest-temp", "pytest-cache", ".pytest-temp", "_work"}
PRIVATE_PARTS = {
    "private",
    "private_runs",
    "private_fixture",
    "evaluator-private",
    "research",
    "imports",
    "adjudications",
}
PRIVATE_EVIDENCE_NAMES = {"new-catalogue-source-audit.json", "q24-replacement-native-anchors.json"}
PRIVATE_RESEARCH_FILES = {
    "evaluation/reliability/week08_cases.json",
    "evaluation/reliability/week08_cases_v2.json",
    "evaluation/reliability/week08_cases_v3.json",
    "evaluation/reliability/week08_v9_regression.json",
    "docs/delivery/week08/review/v8-independent-review.csv",
    "docs/delivery/week08/review/v9-independent-review.csv",
    "evidence/reliability-review/20260916/cpu-only-wheel-retrieval.json",
    "evidence/reliability-review/20260916/real-cpu-retrieval.json",
    "evidence/week08-delivery/20260916/integrated/ai-source-review-attempt1.json",
    "evidence/week08-delivery/20260916/integrated/live-suite-attempt1.json",
    "evidence/week08-delivery/20260916/integrated/live-suite-final.json",
    "evidence/week08-delivery/20260916/integrated/retrieval-pool-attempt1.json",
    "evidence/week08-delivery/20260916/integrated/retrieval-pool-final.json",
    "evidence/week08-delivery/20260916/integrated/v9-retrieval-trace-projection.json",
    "evidence/week08-delivery/20260916/integrated/v9-targeted-live.json",
    "evidence/week08-enhancement/20260920/formal-hints-analysis.json",
    "evidence/week08-enhancement/20260920/regression/original110-attempt1.json",
}
RELOCATION_ROOT = "evidence/week08-memory-v2/20260921/privacy-relocations"


def research_relocation(name):
    """Exact-byte private preservation plus a content-free public companion."""
    if name.casefold() not in PRIVATE_RESEARCH_FILES:
        return {}
    return {
        "private_relocation": "evaluation/reliability/private/" + Path(name).name
        if name.startswith("evaluation/reliability/")
        else "evidence/week08-memory-v2/20260921/private/legacy-evaluation/" + name,
        "public_companion": RELOCATION_ROOT
        + "/public/"
        + hashlib.sha256(name.encode()).hexdigest()[:12]
        + "-"
        + Path(name).stem
        + ".json",
    }


def exclusion(name):
    """Deny private artifacts by purpose/path; retain executable evaluator code."""
    safe_name(name)
    parts = [p.casefold() for p in name.split("/")]
    leaf = parts[-1]
    if name.casefold() in PRIVATE_RESEARCH_FILES:
        return "legacy_evaluator_reference_or_mixed_holdout_data"
    if any(
        p in EXCLUDED_PARTS | TEMPORARY or p.startswith(("pytest-temp", "pg-temp")) for p in parts
    ):
        return "temporary_or_installed_runtime"
    if any(
        p in PRIVATE_PARTS
        or p.startswith(("private-", "private_", "reviewer-", "coordinator-only"))
        for p in parts
    ):
        return "evaluator_private_or_coordinator_material"
    if (
        ".private." in leaf
        or leaf.endswith(".private")
        or any(s in leaf for s in ("review-material", "condition-key", "runtime-credentials"))
    ):
        return "private_account_or_review_material"
    if leaf in PRIVATE_EVIDENCE_NAMES:
        return "formal_private_question_or_source_anchors"
    if leaf.startswith(".env") and leaf != ".env.example":
        return "deployment_environment"
    if Path(leaf).suffix in {
        ".key",
        ".pem",
        ".pfx",
        ".p12",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".dump",
        ".pyc",
    }:
        return "credential_database_or_cache"
    if Path(leaf).suffix in {".zip", ".7z", ".tar", ".gz"} and name != (
        "resources/official-corpus/corpus.jsonl.gz"
    ):
        # The single corpus export is verified against its baseline resource
        # hash and size below. Other archives remain separate from the runtime.
        return "separate_archive_not_public_runtime"
    if parts[0] == "evidence" and (
        "sources" in parts or any(p.endswith("_verification_copy") for p in parts)
    ):
        return "untouched_source_or_legacy_copy"
    return None


def candidates():
    roots = [ROOT / name for name in sorted(DIRECTORIES)] + [
        ROOT / "evidence",
        ROOT / "artifacts/reports/frontend",
    ]
    for path in ROOT.iterdir():
        if (
            path.is_file()
            and path.name != "PACKAGE_MANIFEST.json"
            and path.suffix.lower()
            in {".md", ".json", ".yaml", ".toml", ".ini", ".lock", ".example", ""}
        ):
            if not exclusion(path.name):
                yield path
    for root in roots:
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root):
            allowed = []
            for name in dirs:
                path = Path(current) / name
                if not exclusion(path.relative_to(ROOT).as_posix()):
                    if path.is_symlink():
                        raise ValueError("Source directory symlinks are not portable")
                    allowed.append(name)
            dirs[:] = allowed
            for name in sorted(files):
                path = Path(current) / name
                relative = path.relative_to(ROOT).as_posix()
                if exclusion(relative):
                    continue
                if relative.startswith(("evidence/", "artifacts/")) and path.suffix.lower() not in {
                    ".json",
                    ".md",
                    ".txt",
                    ".log",
                    ".xml",
                    ".png",
                }:
                    continue
                if path.is_symlink():
                    raise ValueError("Source file symlinks are not portable")
                yield path


def _scan_stream(stream, secrets):
    overlap = max(100, max((len(s) for s in secrets), default=1) - 1)
    tail = b""
    while block := stream.read(1024 * 1024):
        value = tail + block
        if any(secret in value for secret in secrets) or re.search(
            rb"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----", value
        ):
            raise ValueError("Configured credential or private-key material detected")
        tail = value[-overlap:]


def scan(path, secrets):
    try:
        with path.open("rb") as stream:
            _scan_stream(stream, secrets)
        if path.suffix.casefold() == ".docx":
            with zipfile.ZipFile(path) as package:
                _safe_members(package)
                for info in package.infolist():
                    with package.open(info) as stream:
                        _scan_stream(stream, secrets)
    except ValueError as exc:
        raise ValueError("Secret scan failed for " + str(path)) from exc


def _safe_members(bundle):
    infos = bundle.infolist()
    names = [i.filename for i in infos]
    if len(names) != len({n.casefold() for n in names}):
        raise ValueError("Duplicate or case-aliased ZIP members")
    for info in infos:
        safe_name(info.filename)
        if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError("Regular ZIP file entries required")
    return names


def _indexed(rows):
    result = {}
    for row in rows:
        name = safe_name(row["path"])
        if (
            name.casefold() in {n.casefold() for n in result}
            or not re.fullmatch(r"[a-f0-9]{64}", row.get("sha256", ""))
            or type(row.get("bytes")) is not int
            or row["bytes"] < 0
        ):
            raise ValueError("Invalid or duplicated manifest file")
        result[name] = row
    return result


def _baseline(path):
    with zipfile.ZipFile(path) as bundle:
        names = _safe_members(bundle)
        manifest = json.loads(bundle.read("learning-assistant/PACKAGE_MANIFEST.json"))
        rows = _indexed(manifest["files"])
        if set(names) != {"learning-assistant/" + n for n in rows} | {
            "learning-assistant/PACKAGE_MANIFEST.json"
        }:
            raise ValueError("Baseline ZIP membership differs from its manifest")
        retained = {}
        for name, row in rows.items():
            if row.get("category") == "release_metadata" and not exclusion(name):
                value = bundle.read("learning-assistant/" + name)
                if len(value) != row["bytes"] or hashlib.sha256(value).hexdigest() != row["sha256"]:
                    raise ValueError("Historical metadata differs from its baseline hash")
                retained[name] = value
    return rows, retained


def _ownership(path, previous):
    value = json.loads(path.read_text(encoding="utf-8"))
    supplied = {}
    for row in value["files"]:
        name, number = safe_name(row["path"]), row["owner_index"]
        if name in supplied or type(number) is not int or not 0 <= number < 8:
            raise ValueError("Invalid or duplicate baseline ownership")
        if (
            name not in previous
            or row.get("sha256", previous[name]["sha256"]) != previous[name]["sha256"]
        ):
            raise ValueError("Baseline ownership does not identify baseline bytes")
        if "owner_index" in previous[name] and previous[name]["owner_index"] != number:
            raise ValueError("Supplied owner differs from embedded baseline owner")
        supplied[name] = number
    return {**{n: r["owner_index"] for n, r in previous.items() if "owner_index" in r}, **supplied}


def reconstruct(baseline, complete, member_paths, inventory):
    """Read actual ZIP bytes and prove the baseline plus disjoint deltas matches."""
    previous, _ = _baseline(baseline)
    with zipfile.ZipFile(complete) as full:
        _safe_members(full)
        final = _indexed(json.loads(full.read("learning-assistant/PACKAGE_MANIFEST.json"))["files"])
        expected = {"learning-assistant/" + k: v for k, v in final.items()}
        body = full.read("learning-assistant/PACKAGE_MANIFEST.json")
        expected["learning-assistant/PACKAGE_MANIFEST.json"] = {
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
    verify_zip(complete, expected)
    delta = _indexed(inventory["files"])
    union = {}
    if len(member_paths) != 8:
        raise ValueError("Exactly eight member archives are required")
    owners_seen = set()
    for path in member_paths:
        with zipfile.ZipFile(path) as bundle:
            names = _safe_members(bundle)
            manifests = [n for n in names if n.endswith("/OWNED_FILES.json")]
            if len(manifests) != 1:
                raise ValueError("One ownership manifest per member archive is required")
            metadata = json.loads(bundle.read(manifests[0]))
            number = next(i for i, m in enumerate(MEMBERS) if m[0] == metadata["owner"])
            if number in owners_seen:
                raise ValueError("Duplicate member archive owner")
            owners_seen.add(number)
            slug = MEMBERS[number][0].replace(" ", "_")
            rows = _indexed(metadata["files"])
            if not rows or any(r["owner_index"] != number for r in rows.values()):
                raise ValueError("Missing or conflicting member ownership")
            allowed = {
                slug + "/" + n
                for n in ("README.md", "OWNED_FILES.json", "COMMIT_MESSAGE.txt", "PR_BODY.md")
            } | {slug + "/repo_files/" + n for n in rows}
            if set(names) != allowed:
                raise ValueError("Member ZIP contains unassigned files")
            for name, row in rows.items():
                if name in union or name not in delta or row != delta[name] or exclusion(name):
                    raise ValueError("Member overlay differs from the exact public delta")
                checksum, size = hashlib.sha256(), 0
                with bundle.open(slug + "/repo_files/" + name) as stream:
                    while block := stream.read(1024 * 1024):
                        checksum.update(block)
                        size += len(block)
                if checksum.hexdigest() != row["sha256"] or size != row["bytes"]:
                    raise ValueError("Member source bytes differ")
                union[name] = row
    if set(union) != set(delta):
        raise ValueError("Eight-member union differs from the delta")
    excluded = {r["path"] for r in inventory["excluded_baseline_files"]}
    if excluded != {n for n in previous if exclusion(n)}:
        raise ValueError("Baseline exclusions are incomplete or broadened")
    for row in inventory["excluded_baseline_files"]:
        old = previous[row["path"]]
        if (
            row["sha256"] != old["sha256"]
            or row["bytes"] != old["bytes"]
            or row["reason"] != exclusion(row["path"])
        ):
            raise ValueError("Private relocation does not identify the preserved baseline bytes")
    virtual = {n: r for n, r in previous.items() if n not in excluded}
    virtual.update(union)
    projected = {n: r for n, r in final.items() if n != CHANGESET}
    if set(virtual) != set(projected) or any(
        (r["sha256"], r["bytes"]) != (projected[n]["sha256"], projected[n]["bytes"])
        for n, r in virtual.items()
    ):
        raise ValueError(
            "Baseline plus member overlay does not reconstruct the complete public project"
        )
    # Manifest equality alone cannot prove retained baseline bytes. Read them
    # from the actual ZIP used for reconstruction, including the 80 resources.
    with zipfile.ZipFile(baseline) as old:
        for name, row in virtual.items():
            if name in union:
                continue
            checksum, size = hashlib.sha256(), 0
            with old.open("learning-assistant/" + name) as stream:
                while block := stream.read(1024 * 1024):
                    checksum.update(block)
                    size += len(block)
            if checksum.hexdigest() != row["sha256"] or size != row["bytes"]:
                raise ValueError("Retained baseline bytes fail reconstruction: " + name)
    return {
        "status": "passed",
        "member_union_exact": True,
        "overlapping_paths": 0,
        "delta_files": len(union),
        "reconstructed_files": len(projected),
        "generated_release_metadata": [CHANGESET],
        "excluded_baseline_files": len(excluded),
        "research_in_public_archives": False,
        "verified_resources": len(inventory["resources"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("destination", "resources", "baseline", "baseline-ownership", "reports"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--private-env", type=Path, action="append", default=[])
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    destination, baseline = args.destination.resolve(), args.baseline.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    previous, metadata = _baseline(baseline)
    owners = _ownership(args.baseline_ownership, previous)
    public = dotenv_values(ROOT / ".env.example")
    secrets = set()
    for path in [ROOT / ".env", *args.private_env]:
        if path.is_file():
            for key, value in dotenv_values(path, encoding="utf-8-sig").items():
                if (
                    value
                    and len(value) >= 16
                    and any(s in key.upper() for s in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
                    and (key.upper() == "LLM_API_KEY" or value != public.get(key))
                ):
                    secrets.add(value.encode())
    sources = {safe_name(p.relative_to(ROOT).as_posix()): p for p in candidates()}
    if args.reports.exists():
        for path in sorted(args.reports.rglob("*")):
            if (
                path.is_file()
                and path.suffix.casefold() in {".docx", ".md"}
                and not any(p.startswith("_") for p in path.relative_to(args.reports).parts)
            ):
                if path.is_symlink():
                    raise ValueError("Report symlinks are not allowed")
                name = REPORT_ROOT + "/" + path.relative_to(args.reports).as_posix()
                if exclusion(name):
                    continue
                if name in sources and digest(sources[name]) != digest(path):
                    raise ValueError(
                        "Final report differs between project and supplied report directory"
                    )
                sources[name] = path
    records = []
    for name, path in sorted(sources.items()):
        if exclusion(name):
            raise ValueError("Private material reached public source selection")
        scan(path, secrets)
        before = previous.get(name)
        sha = digest(path)
        index = owners.get(name, NEW_OWNERS.get(name, owner(name)))
        if name not in owners:
            for number, member in enumerate(MEMBERS):
                if name.startswith(f"{REPORT_ROOT}/members/{member[0].replace(' ', '_')}/"):
                    index = number
            if name.startswith(("evidence/", "artifacts/reports/")):
                index = 7
        if before and before.get("category") == "release_metadata" and sha != before["sha256"]:
            raise ValueError("Historical release metadata must remain byte-identical")
        records.append(
            {
                "path": name,
                "sha256": sha,
                "bytes": path.stat().st_size,
                "owner_index": index,
                "owner": MEMBERS[index][0],
                "change": "added"
                if not before
                else "retained"
                if sha == before["sha256"]
                else "modified",
                "previous_sha256": before["sha256"] if before else None,
                "category": before["category"]
                if before and before.get("category") == "release_metadata"
                else "public_evidence"
                if name.startswith(("evidence/", "artifacts/"))
                else "project_file",
            }
        )
    resources = []
    for prefix, target in (
        ("official-corpus", "resources/official-corpus"),
        ("huggingface", "artifacts/huggingface"),
        ("tiktoken", "artifacts/tiktoken"),
    ):
        for path in sorted((args.resources / prefix).rglob("*")):
            if not path.is_file():
                continue
            if path.is_symlink():
                raise ValueError("Runtime resources must be regular files")
            name = safe_name(target + "/" + path.relative_to(args.resources / prefix).as_posix())
            before = previous.get(name)
            if (
                not before
                or before.get("category") != "verified_runtime_resource"
                or digest(path) != before["sha256"]
                or path.stat().st_size != before["bytes"]
            ):
                raise ValueError("Unverified or changed runtime resource: " + name)
            scan(path, secrets)
            resources.append(
                {
                    "path": name,
                    "sha256": before["sha256"],
                    "bytes": before["bytes"],
                    "category": "verified_runtime_resource",
                }
            )
            sources[name] = path
    if len(resources) != 80 or {r["path"] for r in resources} != {
        n for n, r in previous.items() if r.get("category") == "verified_runtime_resource"
    }:
        raise ValueError("Exactly the same 80 baseline runtime resources are required")
    _indexed(records + resources)
    excluded = [
        {
            **r,
            "reason": exclusion(n),
            "disposition": "Preserved in the September 20 baseline; excluded from current public distribution. Research must be a separate private deliverable.",
            **research_relocation(n),
        }
        for n, r in previous.items()
        if exclusion(n)
    ]
    missing = [n for n in previous if n not in sources and n not in metadata and not exclusion(n)]
    if missing:
        raise ValueError("Unexplained missing baseline public files: " + str(missing))
    delta = [r for r in records if r["change"] != "retained"]
    created = datetime.now(timezone.utc).isoformat()
    inventory = {
        "schema": "week08-memory-v2-public-deltas-v1",
        "created_at": created,
        "baseline": {"archive": baseline.name, "sha256": digest(baseline)},
        "baseline_ownership": {
            "file": args.baseline_ownership.name,
            "sha256": digest(args.baseline_ownership),
            "validation": "Supplied records checked against embedded baseline hashes and owners where present",
        },
        "scope": "September 21 typed memory, provider compatibility and evidence reliability. Existing ownership retained; Codex is the shared implementation executor.",
        "merge_order": [MEMBERS[i][0] for i in (0, 5, 1, 2, 4, 3, 6, 7)],
        "files": delta,
        "resources": resources,
        "excluded_baseline_files": excluded,
        "owner_counts": dict(Counter(r["owner"] for r in delta)),
        "retained_project_files": sum(r["change"] == "retained" for r in records),
        "research_distribution": "Separate private research archive only; never embedded in these nine public archives",
        "privacy_limit": "Path restrictions and configured-secret scanning supplement curator review; they cannot classify every unknown credential or private sentence.",
    }
    report_names = [REPORT_ROOT + "/Week08_Overall_Report.docx"] + [
        f"{REPORT_ROOT}/members/{m[0].replace(' ', '_')}/Week08_Report.docx" for m in MEMBERS
    ]
    inventory["pending_reports"] = [n for n in report_names if n not in sources]
    if args.plan_only:
        path = destination / "WEEK08_MEMORY_V2_PREPACKAGE_PLAN.json"
        if path.exists():
            raise ValueError("Choose a new destination for a new plan")
        path.write_bytes(encoded(inventory))
        print(
            json.dumps(
                {
                    "plan": str(path),
                    "delta_files": len(delta),
                    "pending_reports": len(inventory["pending_reports"]),
                    "resources": 80,
                }
            )
        )
        return
    if inventory["pending_reports"] or any(
        not any(r["owner_index"] == i for r in delta) for i in range(8)
    ):
        raise ValueError("All nine final reports and eight nonempty owned deltas are required")
    outputs = [destination / FULL_NAME] + [
        destination / f"{PREFIX}_{i + 1:02}_{m[0].replace(' ', '_')}_20260921.zip"
        for i, m in enumerate(MEMBERS)
    ]
    if any(p.exists() for p in outputs) or any(
        (destination / n).exists()
        for n in (
            "EIGHT_MEMBER_INVENTORY.json",
            "PACKAGE_VERIFICATION.json",
            "RECONSTRUCTION_VERIFICATION.json",
        )
    ):
        raise ValueError("Choose a new destination; prior releases are never overwritten")
    manifest = {
        "version": "cs30-week08-memory-v2-public-runtime-v1",
        "created_at": created,
        "startup": "powershell -ExecutionPolicy Bypass -File scripts/release/start_local.ps1 -Install -Device cpu",
        "scope": "Runnable English project, nine reports and the same verified four-book corpus/local-model resources. Fresh accounts and secrets; explicit mock until an administrator configures a live provider.",
        "research_distribution": inventory["research_distribution"],
        "files": records + resources,
    }
    archives, expected = [], {}
    with zipfile.ZipFile(
        outputs[0], "x", compression=zipfile.ZIP_DEFLATED, compresslevel=4
    ) as bundle:
        for row in records + resources:
            add_file(
                bundle,
                "learning-assistant/" + row["path"],
                sources[row["path"]],
                row,
                expected,
                row["category"] == "verified_runtime_resource",
            )
        for name, value in metadata.items():
            if name not in sources:
                _scan_stream(__import__("io").BytesIO(value), secrets)
                add_bytes(bundle, "learning-assistant/" + name, value, expected)
                manifest["files"].append(previous[name])
        add_bytes(bundle, "learning-assistant/" + CHANGESET, encoded(inventory), expected)
        manifest["files"].append(
            {
                "path": CHANGESET,
                **expected["learning-assistant/" + CHANGESET],
                "category": "release_metadata",
            }
        )
        add_bytes(bundle, "learning-assistant/PACKAGE_MANIFEST.json", encoded(manifest), expected)
    archives.append(
        {
            "path": outputs[0].name,
            "sha256": digest(outputs[0]),
            "bytes": outputs[0].stat().st_size,
            **verify_zip(outputs[0], expected),
        }
    )
    for i, member in enumerate(MEMBERS):
        name, sid, _, _, _, domain = member
        slug = name.replace(" ", "_")
        rows = [r for r in delta if r["owner_index"] == i]
        expected = {}
        readme = f"# Week 8 contribution — {name}\n\nStudent ID: {sid}. Assigned domain: {domain}.\n\nThese {len(rows)} changed files are relative to the verified 20 September complete baseline. Codex performed shared implementation; the file assignment records team responsibility. Review the member report under `{REPORT_ROOT}/members/{slug}/`.\n\nCreate a branch from the team's integrated baseline. Compare each `previous_sha256` before copying `repo_files/` with paths preserved. Resolve concurrent edits, inspect the complete diff, then use the supplied commit/PR text after personal review. The overall inventory gives the merge order. No upload or commit was performed by packaging.\n\nUse the public complete archive for the same 80 runtime resources. Credentials, user history, private references, reviewer keys and study outputs are not member contributions. The historical embedded research archive is explicitly excluded from current public distribution; the unchanged older delivery remains preserved.\n"
        pr = f"# Week 8 {domain}\n\nAssigned contribution for {name}: typed learning memory, evidence reliability and staged provider compatibility, with exact validation limits in the member report. OWNED_FILES.json records each baseline/current hash. Earlier study outcomes remain dated and no automatic judgment is called human review. Research materials are distributed separately through the team's private review process.\n"
        with zipfile.ZipFile(
            outputs[i + 1], "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as bundle:
            for leaf, body in (
                ("README.md", readme.encode()),
                (
                    "COMMIT_MESSAGE.txt",
                    f"Week 8 {name} memory and reliability contribution\n".encode(),
                ),
                ("PR_BODY.md", pr.encode()),
                (
                    "OWNED_FILES.json",
                    encoded(
                        {
                            "owner": name,
                            "student_id": sid,
                            "domain": domain,
                            "baseline": inventory["baseline"],
                            "files": rows,
                        }
                    ),
                ),
            ):
                add_bytes(bundle, slug + "/" + leaf, body, expected)
            for row in rows:
                add_file(
                    bundle, slug + "/repo_files/" + row["path"], sources[row["path"]], row, expected
                )
        archives.append(
            {
                "path": outputs[i + 1].name,
                "owner": name,
                "assigned_files": len(rows),
                "bytes": outputs[i + 1].stat().st_size,
                "sha256": digest(outputs[i + 1]),
                **verify_zip(outputs[i + 1], expected),
            }
        )
    reconstruction = reconstruct(baseline, outputs[0], outputs[1:], inventory)
    (destination / "EIGHT_MEMBER_INVENTORY.json").write_bytes(encoded(inventory))
    (destination / "RECONSTRUCTION_VERIFICATION.json").write_bytes(
        encoded({"created_at": created, **reconstruction, "archives": archives})
    )
    (destination / "PACKAGE_VERIFICATION.json").write_bytes(
        encoded({"created_at": created, "archives": archives, **reconstruction})
    )
    print(
        json.dumps(
            {
                "archives": 9,
                "delta_files": len(delta),
                "complete_bytes": outputs[0].stat().st_size,
                "destination": str(destination),
            }
        )
    )


if __name__ == "__main__":
    main()
