"""Build the current runnable release and eight cumulative complete-file owner packs."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from dotenv import dotenv_values
from scripts.release.common import file_hash
from scripts.release.package import ROOT
from scripts.release.upgrade_delivery import MEMBERS, owner
from scripts.release.week08_memory_v2_delivery import (
    candidates,
    exclusion,
    _indexed,
    _ownership,
    _safe_members,
    _scan_stream,
)

PREFIX = "learning-assistant/"
REPORT_ROOT = "docs/delivery/teaching-performance"
ONNX_ROOT = "artifacts/reranker-onnx/20260926"


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def manifest(archive):
    with zipfile.ZipFile(archive) as source:
        _safe_members(source)
        rows = json.loads(source.read(PREFIX + "PACKAGE_MANIFEST.json"))["files"]
        result = _indexed(rows)
        assert set(source.namelist()) == {PREFIX + p for p in result} | {
            PREFIX + "PACKAGE_MANIFEST.json"
        }
        return result


def temporary(name):
    return any(
        re.search(r"(?:^|[-_])temp(?:$|[-_])", part.casefold()) for part in Path(name).parts[:-1]
    )


def report_owner(name):
    for i, member in enumerate(MEMBERS):
        if member[0].replace(" ", "_") in Path(name).name:
            return i
    return None


def assigned_owner(name, owners, previous):
    number = owners.get(name, previous.get(name, {}).get("owner_index"))
    if number is None:
        number = 2 if name.startswith(ONNX_ROOT + "/") else report_owner(name)
        number = owner(name) if number is None else number
    if type(number) is not int or not 0 <= number < len(MEMBERS):
        raise ValueError("Invalid accountable owner for " + name)
    return number


def experimental_resources():
    folder = ROOT / ONNX_ROOT
    model_manifest = folder / "manifest.json"
    metadata = json.loads(model_manifest.read_text(encoding="utf-8"))
    expected_graphs = {"model.fp32.onnx", "model.int8.onnx"}
    if set(metadata["files"]) != expected_graphs:
        raise ValueError("Unexpected experimental graph inventory")
    for backend in ("onnx_fp32", "onnx_int8"):
        config = json.loads(
            (ROOT / f"configs/retrieval/chat_cpu_experimental_{backend}.json").read_text(
                encoding="utf-8"
            )
        )
        runtime = config["reranker_runtime"]
        if (
            runtime["artifact_path"] != ONNX_ROOT + "/manifest.json"
            or runtime["artifact_sha256"] != file_hash(model_manifest)
            or config["reranker_model"] != metadata["model"]
            or config["reranker_revision"] != metadata["revision"]
        ):
            raise ValueError("Experimental configuration differs from pinned export")
    result = {}
    for leaf in sorted(expected_graphs | {"manifest.json"}):
        path = folder / leaf
        if not path.is_file() or path.is_symlink():
            raise ValueError("Experimental runtime requires regular local files")
        if leaf in expected_graphs and file_hash(path) != metadata["files"][leaf]:
            raise ValueError("Experimental graph differs from pinned export")
        result[path.relative_to(ROOT).as_posix()] = path
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "previous", "ownership", "destination", "report-verification"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    previous, baseline = manifest(args.previous), manifest(args.baseline)
    owners = _ownership(args.ownership, baseline)
    for name, number in owners.items():
        if previous.get(name, {}).get("owner_index", number) != number:
            raise ValueError("Previous release changed original accountable ownership")
    review = json.loads(args.report_verification.read_text(encoding="utf-8"))
    assert review["status"] == "passed" and review["every_page_inspected"] is True
    report_paths = sorted((ROOT / REPORT_ROOT).glob("*.docx"))
    report_bytes = {p.name: p.read_bytes() for p in report_paths}
    expected_reports = {"Week08_Overall_Report.docx"} | {
        "Week08_" + member[0].replace(" ", "_") + "_Report.docx" for member in MEMBERS
    }
    assert set(report_bytes) == expected_reports
    report_hashes = {
        name: hashlib.sha256(value).hexdigest() for name, value in report_bytes.items()
    }
    assert report_hashes == review["report_hashes"]
    dest = args.destination.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        raise ValueError("Use a new destination; preserve existing releases")
    configured = set()
    public = dotenv_values(ROOT / ".env.example")
    for key, value in dotenv_values(ROOT / ".env").items():
        if (
            value
            and len(value) >= 16
            and any(x in key.upper() for x in ("KEY", "SECRET", "TOKEN", "PASSWORD"))
            and (key.upper() == "LLM_API_KEY" or value != public.get(key))
        ):
            configured.add(value.encode())
    sources = {
        p.relative_to(ROOT).as_posix(): p
        for p in candidates()
        if not temporary(p.relative_to(ROOT).as_posix())
    }
    # Experimental graphs are optional runtime resources, with exact pinned hashes.
    sources.update(experimental_resources())
    retained = {
        name: row
        for name, row in previous.items()
        if row["category"] in {"verified_runtime_resource", "release_metadata", "public_evidence"}
        and name not in sources
        and not exclusion(name)
        and not temporary(name)
    }
    resources = {n: r for n, r in previous.items() if r["category"] == "verified_runtime_resource"}
    # The exact official gzip path is permitted by exclusion(); all other private
    # and temporary exclusions still apply to previously packaged resources.
    for name, row in resources.items():
        if exclusion(name) or temporary(name):
            raise ValueError("A retained runtime resource has a forbidden path")
        if any(baseline.get(name, {}).get(key) != row[key] for key in ("sha256", "bytes")):
            raise ValueError("Changed runtime resources require a declared reconstruction extra")
    retained.update(resources)
    records = []
    for name in sorted(set(sources) | set(retained)):
        old = baseline.get(name)
        if name in sources:
            path = sources[name]
            digest, size = file_hash(path), path.stat().st_size
            category = (
                "experimental_runtime_resource"
                if name.startswith("artifacts/reranker-onnx/")
                else "public_evidence"
                if name.startswith("evidence/")
                else "project_file"
            )
        else:
            digest, size, category = (retained[name][k] for k in ("sha256", "bytes", "category"))
        number = assigned_owner(name, owners, previous)
        records.append(
            {
                "path": name,
                "sha256": digest,
                "bytes": size,
                "category": category,
                "owner_index": number,
                "owner": MEMBERS[number][0],
                "change": "unchanged"
                if old and old["sha256"] == digest
                else "modified"
                if old
                else "added",
                "previous_sha256": old["sha256"] if old else None,
            }
        )
    package = {
        "version": "teaching_performance_delivery_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "startup": "powershell -ExecutionPolicy Bypass -File scripts/release/start_local.ps1 -Install -Device cpu",
        "scope": "Cumulative current project since the verified Week 7 final; September 26 teaching and retrieval continuation included.",
        "research_distribution": "Private provider outputs and blank human forms remain separate from the public runnable archive.",
        "files": records,
    }
    full = dest / "CS30-1_Week08_Teaching_Performance_Complete_20260926.zip"
    with (
        zipfile.ZipFile(args.previous) as old_zip,
        zipfile.ZipFile(full, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as archive,
    ):
        for row in records:
            name = row["path"]
            if name in sources:
                value = sources[name].read_bytes()
            else:
                value = old_zip.read(PREFIX + name)
            assert hashlib.sha256(value).hexdigest() == row["sha256"] and len(value) == row["bytes"]
            _scan_stream(io.BytesIO(value), configured)
            if name.endswith(".docx"):
                with zipfile.ZipFile(io.BytesIO(value)) as docx:
                    _safe_members(docx)
                    for part in docx.infolist():
                        with docx.open(part) as stream:
                            _scan_stream(stream, configured)
            archive.writestr(PREFIX + name, value)
        manifest_bytes = encoded(package)
        archive.writestr(PREFIX + "PACKAGE_MANIFEST.json", manifest_bytes)
    delta = [
        r
        for r in records
        if r["change"] != "unchanged" and r["category"] != "verified_runtime_resource"
    ]
    # Graphs travel in the full archive; member packs retain their manifests and
    # download/export instructions to keep GitHub source contributions practical.
    graph_resources = [r for r in delta if r["path"].endswith(".onnx")]
    delta = [r for r in delta if not r["path"].endswith(".onnx")]
    root_manifest = {
        "path": "PACKAGE_MANIFEST.json",
        "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "bytes": len(manifest_bytes),
        "category": "release_metadata",
        "owner_index": 0,
        "owner": MEMBERS[0][0],
        "change": "modified",
    }
    delta.append(root_manifest)
    removed = [
        {"path": name, "sha256": row["sha256"]}
        for name, row in baseline.items()
        if name not in {r["path"] for r in records}
    ]
    archives = [{"path": full.name, "sha256": file_hash(full), "bytes": full.stat().st_size}]
    union = {}
    with zipfile.ZipFile(full) as complete:
        for i, member in enumerate(MEMBERS):
            slug = member[0].replace(" ", "_")
            rows = [r for r in delta if r["owner_index"] == i]
            report = ROOT / REPORT_ROOT / ("Week08_" + slug + "_Report.docx")
            assert rows and report.is_file()
            path = dest / f"CS30-1_Week08_{i + 1:02}_{slug}_20260926.zip"
            with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                intro = f"# Week 8 contribution for {member[0]}\n\nStudent ID: {member[1]}. Domain: {member[5]}.\n\nThis cumulative pack contains the latest complete assigned source files since the verified Week 7 final, including the teaching and performance continuation of 26 September. Original accountable owners are retained; Codex performed the recorded shared implementation and automated verification.\n\nReview OWNED_FILES.json and copy repo_files with paths unchanged onto an isolated team baseline. The complete project archive supplies original corpus/model resources and optional ONNX graphs. Keep local credentials and learner records in your installation.\n\nThe root DOCX is byte-identical to the standalone report. Its completed work, evidence and next-week goals cover the assigned domain.\n"
                archive.writestr(slug + "/README.md", intro)
                archive.writestr(
                    slug + "/OWNED_FILES.json",
                    encoded({"owner": member[0], "student_id": member[1], "files": rows}),
                )
                archive.writestr(
                    slug + "/COMMIT_MESSAGE.txt", f"Integrate Week 8 {member[5].lower()}\n"
                )
                archive.writestr(
                    slug + "/PR_BODY.md",
                    "Integrates the current complete assigned files and the September 26 continuation. See the English report and linked verification records for behavior, failures and remaining review.\n",
                )
                archive.writestr(slug + "/" + report.name, report_bytes[report.name])
                if i == 0:
                    archive.writestr(
                        slug + "/REMOVED_BASELINE_PATHS.json",
                        encoded(
                            {
                                "scope": "Isolated exact Week 7 baseline only; never apply to a live installation",
                                "files": removed,
                            }
                        ),
                    )
                for row in rows:
                    assert row["path"] not in union
                    value = complete.read(PREFIX + row["path"])
                    archive.writestr(slug + "/repo_files/" + row["path"], value)
                    union[row["path"]] = row["sha256"]
            with zipfile.ZipFile(path) as check:
                _safe_members(check)
                assert check.read(slug + "/" + report.name) == report_bytes[report.name]
                for row in rows:
                    assert (
                        hashlib.sha256(check.read(slug + "/repo_files/" + row["path"])).hexdigest()
                        == row["sha256"]
                    )
            archives.append(
                {
                    "path": path.name,
                    "owner": member[0],
                    "assigned_files": len(rows),
                    "sha256": file_hash(path),
                    "bytes": path.stat().st_size,
                }
            )
        for row in records + [root_manifest]:
            with complete.open(PREFIX + row["path"]) as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == row["sha256"]
        _safe_members(complete)
        virtual = {
            name: row["sha256"]
            for name, row in baseline.items()
            if name not in {r["path"] for r in removed}
        }
        virtual.update(union)
        virtual.update({r["path"]: r["sha256"] for r in graph_resources})
        assert virtual == {r["path"]: r["sha256"] for r in records + [root_manifest]}
        # The reconstruction proof includes actual unchanged baseline bytes,
        # not only the hashes asserted by its manifest.
        replaced = set(union) | {r["path"] for r in graph_resources}
        removed_names = {r["path"] for r in removed}
        with zipfile.ZipFile(args.baseline) as baseline_zip:
            for name, row in baseline.items():
                if name in removed_names or name in replaced:
                    continue
                info = baseline_zip.getinfo(PREFIX + name)
                assert info.file_size == row["bytes"]
                with baseline_zip.open(info) as stream:
                    assert hashlib.file_digest(stream, "sha256").hexdigest() == row["sha256"]
        for name, value in report_bytes.items():
            assert complete.read(PREFIX + REPORT_ROOT + "/" + name) == value
    for name, value in report_bytes.items():
        (dest / "Reports").mkdir(exist_ok=True)
        (dest / "Reports" / name).write_bytes(value)
        assert file_hash(dest / "Reports" / name) == report_hashes[name]
    verification = {
        "status": "passed",
        "archives": archives,
        "reconstruction": "Week7 baseline + eight disjoint overlays + two explicitly supplied optional graphs equals full archive",
        "resources_preserved": len(resources),
        "member_overlaps": 0,
        "member_report_equality": True,
        "report_hashes": report_hashes,
        "baseline_bytes_verified": True,
        "secret_scan": "passed",
        "files": len(records),
        "owner_counts": dict(Counter(r["owner"] for r in delta)),
    }
    (dest / "PACKAGE_VERIFICATION.json").write_bytes(encoded(verification))
    (dest / "CUMULATIVE_CHANGES.json").write_bytes(
        encoded(
            {
                "files": delta,
                "removed_baseline_paths": removed,
                "optional_graphs_from_complete_archive": graph_resources,
            }
        )
    )
    (dest / "CHECKSUMS.sha256").write_text(
        "".join(r["sha256"] + "  " + r["path"] + "\n" for r in archives)
        + "".join(digest + "  Reports/" + name + "\n" for name, digest in report_hashes.items()),
        encoding="utf-8",
    )
    print(json.dumps({"status": "passed", "archives": len(archives), "files": len(records)}))


if __name__ == "__main__":
    main()
