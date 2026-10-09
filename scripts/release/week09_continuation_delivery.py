"""Prepare a dated cumulative Week 9 continuation; retain earlier releases."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import gzip
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
    exclusion as legacy_exclusion,
    _indexed,
    _ownership,
    _safe_members,
    _scan_stream,
)

PREFIX = "learning-assistant/"
REPORT_ROOT = "docs/delivery/week09-continuation"
ONNX_ROOT = "artifacts/reranker-onnx/20260926"
FULL_NAME = "CS30-1_Week09_Continuation_Complete_Project_20260930.zip"


def archive_names(release_date="20260930"):
    if not re.fullmatch(r"[0-9]{8}", release_date):
        raise ValueError("Release date must use YYYYMMDD")
    datetime.strptime(release_date, "%Y%m%d")
    return (
        f"CS30-1_Week09_Continuation_Complete_Project_{release_date}.zip",
        [
            f"CS30-1_Week09_Continuation_{i + 1:02}_{m[0].replace(' ', '_')}_{release_date}.zip"
            for i, m in enumerate(MEMBERS)
        ],
    )


BASELINE_SHA256 = "a880978703f850bfdc514bd232c97f5dc999709634459173abfb6218679b8927"
PREVIOUS_SHA256 = "a3be2aae9a982d3850c5a87e8f7ab3851879b0ff6ff60e6a38cddef6c51ac4c1"
OWNERSHIP_SHA256 = "a1b4973e869772d85b6f5fe0c6e3fe342f627c6304abcf234f4d95c46dd3fe08"
VISUAL_ROOT = "evidence/week09-continuation/20260930/visual-full-attempt2"
VISUAL_CATALOGS = {
    "anatomy-and-physiology-2e-regions.jsonl.gz": "e70ba591c22f9b2ccecb924561f1f34176cbf415acac277567177ef4ce59e4d2",
    "biology-2e-regions.jsonl.gz": "6cebccc6811306e66ba707710abf93949bcba14825a5c31514d84365ce324f6c",
    "chemistry-2e-regions.jsonl.gz": "c9cf56d28c5d27551c135e0dea32dd7cba08a283739d1e8c334cc6addf4787f8",
    "concepts-biology-regions.jsonl.gz": "f96765c0f11a0399dff85dded8ba52a4a57d29eb2dbc3d50970f2028c6e16580",
}
VISUAL_PRIOR_ROOT = "evidence/week09-continuation/20260930/visual-full-attempt1"
VISUAL_PRIOR_CATALOGS = {
    "anatomy-and-physiology-2e-regions.jsonl.gz": "8105a2d7ee468541f6f1fcfc047534232487fe83ad8286d606b7788ad9b24577",
    "biology-2e-regions.jsonl.gz": "cb8e05f035f1441eabc623fd25351d57edd76bb3b74b2a28bcc130c2833bf451",
    "chemistry-2e-regions.jsonl.gz": "a35702a3ff337ebabafee2414b0977e78060947c1d751ae050cddf1d48d120af",
    "concepts-biology-regions.jsonl.gz": "412df694450bb76d718ab797c657db74aec450d5db8334e8afde6d1f771a4480",
}
VISUAL_REVIEW_SHEET = "evidence/week09-continuation/20260930/visual-review-v2/review-sheet.csv"
VISUAL_REVIEW_SHEET_SHA256 = "a4aa5d9c0b4a9f2519a5170e4ebbdf8c325e084e3d1d2b1ea5fc9c26547a23d9"
PRIVATE_CONTENT_KEYS = {
    "answer_text",
    "compact_answer",
    "expected_answer",
    "gold",
    "gold_answer",
    "gold_labels",
    "messages",
    "model_response",
    "prompt",
    "provider_payload",
    "question",
    "question_text",
    "raw_response",
    "source_text",
    "draft_text",
    "reference_answer",
    "learner_response",
    "raw_provider_response",
    "password",
    "access_token",
    "refresh_token",
    "api_key",
    "correct_options",
    "answer_key",
    "rubric",
    "pilot_labels",
    "judge_labels",
}


def exclusion(name):
    if name in {
        root + "/" + leaf
        for root, catalogues in (
            (VISUAL_ROOT, VISUAL_CATALOGS),
            (VISUAL_PRIOR_ROOT, VISUAL_PRIOR_CATALOGS),
        )
        for leaf in catalogues
    }:
        return None
    reason = legacy_exclusion(name)
    if reason:
        return reason
    if name == "tests/unit/test_portable_credentials.py":
        # Authored regression source; the normal content/secret scan still applies.
        return None
    parts = name.casefold().split("/")
    if any(
        part in {"credentials", "credential", "cookies", "browser-state", "storage-state"}
        or any(term in part for term in ("credentials.", "storage_state", "auth-session"))
        for part in parts
    ):
        return "local_test_credentials_or_authenticated_browser_state"
    if name.startswith("evaluation/week09_continuation/") and Path(name).suffix not in {
        ".py",
        ".md",
    }:
        return "continuation_private_study_input_or_output"
    if not (name.startswith("evaluation/week09/") or name.startswith("evidence/week09-")):
        return None
    if any(
        part
        in {
            "fixtures",
            "fixture_data",
            "gold",
            "references",
            "review_packets",
            "human-review",
            "raw_provider",
            "provider_payloads",
            "frozen-source",
            "pilot",
            "pilots",
            "labels",
            "judgments",
            "judge_outputs",
            "responses",
            "raw",
        }
        for part in parts
    ):
        return "week09_private_research_payload"
    if Path(name).suffix.lower() not in {".py", ".md"} and any(
        word in parts[-1]
        for word in ("catalogue", "gold", "raw-provider", "raw_provider", "reference-answers")
    ):
        return "week09_private_research_payload"
    return None


def visual_runtime_resources(resources):
    """Pin both unlabeled visual-extractor catalogues for paired mechanical replay."""
    official_hashes = {r["sha256"] for r in resources.values()}
    result = {}
    for root, catalogues in (
        (VISUAL_ROOT, VISUAL_CATALOGS),
        (VISUAL_PRIOR_ROOT, VISUAL_PRIOR_CATALOGS),
    ):
        path = ROOT / root / "manifest.json"
        books = json.loads(path.read_text(encoding="utf-8")).get("books", [])
        expected = {root + "/" + leaf: digest for leaf, digest in catalogues.items()}
        if len(books) != 4 or {b.get("catalog_path") for b in books} != set(expected):
            raise ValueError("Visual runtime manifest must bind four distinct exact catalogues")
        result[root + "/manifest.json"] = path
        for book in books:
            name = book["catalog_path"]
            catalog = ROOT / name
            if (
                book.get("catalog_sha256") != expected[name]
                or file_hash(catalog) != expected[name]
                or book.get("source_sha256") not in official_hashes
            ):
                raise ValueError(
                    "Visual runtime catalogue or original source differs from frozen identity"
                )
            result[name] = catalog
    review = ROOT / VISUAL_REVIEW_SHEET
    if file_hash(review) != VISUAL_REVIEW_SHEET_SHA256:
        raise ValueError("Blank visual-review sheet differs from frozen identity")
    result[VISUAL_REVIEW_SHEET] = review
    return result


def validate_public_content(name, value):
    """Public Week 9 reports expose measurements, not experiment response bodies."""
    if not name.startswith("evidence/week09-") or not name.endswith(".json"):
        return

    def inspect(node):
        if isinstance(node, dict):
            if PRIVATE_CONTENT_KEYS.intersection(str(key).casefold() for key in node):
                raise ValueError("Private research content in public evidence: " + name)
            if any(
                str(key).casefold() in {"answer", "response", "output"}
                and isinstance(child, str)
                and len(child) > 80
                for key, child in node.items()
            ):
                raise ValueError("Unreviewed response body in public evidence: " + name)
            for child in node.values():
                inspect(child)
        elif isinstance(node, list):
            for child in node:
                inspect(child)

    inspect(json.loads(value))


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


def experimental_resources(previous_path, previous):
    """Pin the inherited optional graphs to their previous release bytes."""
    name = ONNX_ROOT + "/manifest.json"
    with zipfile.ZipFile(previous_path) as archive:
        manifest_bytes = archive.read(PREFIX + name)
    metadata = json.loads(manifest_bytes)
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
            or runtime["artifact_sha256"] != hashlib.sha256(manifest_bytes).hexdigest()
            or config["reranker_model"] != metadata["model"]
            or config["reranker_revision"] != metadata["revision"]
        ):
            raise ValueError("Experimental configuration differs from pinned export")
    result = {}
    for leaf in sorted(expected_graphs | {"manifest.json"}):
        name = ONNX_ROOT + "/" + leaf
        row = previous.get(name)
        if not row or row["category"] != "experimental_runtime_resource":
            raise ValueError("Missing inherited experimental runtime resource")
        if leaf in expected_graphs and row["sha256"] != metadata["files"][leaf]:
            raise ValueError("Experimental graph differs from pinned export")
        result[name] = row
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "previous", "ownership", "destination"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--report-verification", type=Path)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--plan-output", type=Path)
    parser.add_argument("--release-date", default="20260930")
    args = parser.parse_args()
    full_name, member_names = archive_names(args.release_date)
    for path, expected in (
        (args.baseline, BASELINE_SHA256),
        (args.previous, PREVIOUS_SHA256),
        (args.ownership, OWNERSHIP_SHA256),
    ):
        if file_hash(path) != expected:
            raise ValueError("Input differs from the immutable declared baseline: " + path.name)
    dest = args.destination.resolve()
    if dest == ROOT.resolve() or ROOT.resolve() in dest.parents:
        raise ValueError("Delivery destination must be outside the project")
    if any(
        dest == p.resolve().parent or dest in p.resolve().parents
        for p in (args.baseline, args.previous, args.ownership)
    ):
        raise ValueError("Delivery destination must not contain or replace a retained baseline")
    if dest.exists() and any(dest.iterdir()):
        raise ValueError("Use a new destination; preserve existing releases")
    previous, baseline = manifest(args.previous), manifest(args.baseline)
    owners = _ownership(args.ownership, baseline)
    for name, number in owners.items():
        if previous.get(name, {}).get("owner_index", number) != number:
            raise ValueError("Previous release changed original accountable ownership")
    report_paths = sorted((ROOT / REPORT_ROOT).glob("*.docx"))
    report_bytes = {p.name: p.read_bytes() for p in report_paths}
    expected_reports = {"Week09_Overall_Report.docx"} | {
        "Week09_" + member[0].replace(" ", "_") + "_Report.docx" for member in MEMBERS
    }
    report_hashes = {
        name: hashlib.sha256(value).hexdigest() for name, value in report_bytes.items()
    }
    blockers = []
    if set(report_bytes) != expected_reports:
        blockers.append("Nine current English reports are not ready at " + REPORT_ROOT)
    review = None
    if args.report_verification is None or not args.report_verification.is_file():
        blockers.append("Exact report visual-verification receipt is not ready")
    else:
        review = json.loads(args.report_verification.read_text(encoding="utf-8"))
        if not (
            review.get("status") == "passed"
            and review.get("every_page_inspected") is True
            and report_hashes == review.get("report_hashes")
        ):
            blockers.append("Current report bytes do not match complete visual verification")
    if blockers and not args.plan_only:
        raise ValueError("; ".join(blockers))
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
    sources, excluded = {}, []
    for path in candidates():
        name = path.relative_to(ROOT).as_posix()
        reason = exclusion(name) or ("temporary_work_tree" if temporary(name) else None)
        if reason:
            excluded.append({"path": name, "reason": reason})
        else:
            sources[name] = path
    # Retain prior graph bytes; optional alignment configs are ordinary source
    # files, and no new model weights enter the default installation here.
    experimental = experimental_resources(args.previous, previous)
    if set(sources).intersection(experimental):
        raise ValueError("Experimental resources require the inherited release bytes")
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
    retained.update(experimental)
    if len(resources) != 80 or len(experimental) != 3:
        raise ValueError("Expected 80 verified resources and three optional graph resources")
    sources.update(visual_runtime_resources(resources))
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
    # Inspect current source bytes before opening any release archive. Retained
    # baseline payloads are verified again while writing and by the verifier.
    for name, path in sorted(sources.items()):
        value = path.read_bytes()
        validate_public_content(name, value)
        _scan_stream(io.BytesIO(value), configured)
        if name in {
            root + "/" + leaf
            for root, catalogues in (
                (VISUAL_ROOT, VISUAL_CATALOGS),
                (VISUAL_PRIOR_ROOT, VISUAL_PRIOR_CATALOGS),
            )
            for leaf in catalogues
        }:
            with gzip.open(path, "rb") as stream:
                _scan_stream(stream, configured)
        if name.endswith(".docx"):
            with zipfile.ZipFile(io.BytesIO(value)) as docx:
                _safe_members(docx)
                for part in docx.infolist():
                    with docx.open(part) as stream:
                        _scan_stream(stream, configured)
    plan = {
        "version": "week09_continuation_package_plan_v1",
        "status": "prepared_not_created",
        "baseline_sha256": BASELINE_SHA256,
        "previous_sha256": PREVIOUS_SHA256,
        "ownership_sha256": OWNERSHIP_SHA256,
        "destination": str(dest),
        "report_root": REPORT_ROOT,
        "report_hashes": report_hashes,
        "blockers": blockers,
        "files": records,
        "excluded_current_candidates": excluded,
        "virtual_removed_baseline_paths": sorted(set(baseline) - {r["path"] for r in records}),
        "resources": len(resources),
        "optional_resources": len(experimental),
        "privacy_scope": "Explicit private-path exclusions and known configured-secret scan; curator review is still required for unknown sensitive prose or images.",
    }
    if args.plan_output:
        if args.plan_output.exists():
            raise ValueError("Preserve the existing package plan; choose a new output")
        args.plan_output.parent.mkdir(parents=True, exist_ok=True)
        args.plan_output.write_bytes(encoded(plan))
    if args.plan_only:
        print(json.dumps({"status": plan["status"], "files": len(records), "blockers": blockers}))
        return
    dest.mkdir(parents=True, exist_ok=True)
    package = {
        "version": "week09_continuation_cumulative_delivery_v1",
        "release_date": args.release_date,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "startup": "powershell -ExecutionPolicy Bypass -File scripts/release/start_local.ps1 -Install -Device cpu",
        "scope": "Cumulative current project since the verified Week 7 final; Week 8 continuations and Week 9 learning-workspace and generation controls included.",
        "research_distribution": "Private provider outputs and blank human forms remain separate from the public runnable archive.",
        "baseline_sha256": BASELINE_SHA256,
        "previous_sha256": PREVIOUS_SHA256,
        "ownership_sha256": OWNERSHIP_SHA256,
        "files": records,
    }
    full = dest / full_name
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
            validate_public_content(name, value)
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
            report = ROOT / REPORT_ROOT / ("Week09_" + slug + "_Report.docx")
            assert rows and report.is_file()
            path = dest / member_names[i]
            with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                intro = f"# Week 9 continuation contribution for {member[0]}\n\nStudent ID: {member[1]}. Domain: {member[5]}.\n\nThis cumulative pack contains the latest complete assigned source files since the verified Week 7 final, including all Week 8 continuations and Week 9 learning-workspace and generation controls. Original accountable owners are retained; Codex performed the recorded shared implementation and automated verification.\n\nReview OWNED_FILES.json and copy repo_files with paths unchanged onto an isolated team baseline. The complete project archive supplies original corpus/model resources and optional ONNX graphs. Keep local credentials and learner records in your installation.\n\nThe root DOCX is byte-identical to the standalone report. Its completed work, evidence and next-week goals cover the assigned domain.\n"
                archive.writestr(slug + "/README.md", intro)
                archive.writestr(
                    slug + "/OWNED_FILES.json",
                    encoded({"owner": member[0], "student_id": member[1], "files": rows}),
                )
                archive.writestr(
                    slug + "/COMMIT_MESSAGE.txt",
                    f"Integrate Week 9 continuation {member[5].lower()}\n",
                )
                archive.writestr(
                    slug + "/PR_BODY.md",
                    "Integrates the current complete assigned files, Week 8 continuations and Week 9 learning-workspace and generation controls. See the English report and linked verification records for behavior, failures and remaining review.\n",
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
        "release_date": args.release_date,
        "archives": archives,
        "reconstruction": "Week7 baseline + eight disjoint overlays + two explicitly supplied optional graphs equals full archive",
        "resources_preserved": len(resources),
        "experimental_resources_preserved": len(experimental),
        "previous_archive_sha256": file_hash(args.previous),
        "baseline_archive_sha256": file_hash(args.baseline),
        "ownership_sha256": file_hash(args.ownership),
        "member_overlaps": 0,
        "member_report_equality": True,
        "report_hashes": report_hashes,
        "baseline_bytes_verified": True,
        "secret_scan": "passed",
        "privacy_scope": plan["privacy_scope"],
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
    (dest / "PACKAGE_PLAN.json").write_bytes(encoded(plan))
    (dest / "README.md").write_text(
        "# Week 9 continuation delivery\n\n"
        "Extract the complete archive into a new local directory. In its learning-assistant folder run `powershell -ExecutionPolicy Bypass -File scripts/release/start_local.ps1 -Install -Device cpu`. Docker Desktop and the documented supported Python/Node runtimes are required; see README.md and docs/runbook.md inside the project. The 80 original runtime resources and three pinned optional ONNX resources retain their exact bytes.\n\n"
        "Use a distinct project/ports for a fresh installation. Configure provider credentials locally through the documented model-settings workflow; no key, account history or deployment database is included. Default mock behavior and real provider/checker requirements remain explicitly labelled. Keep the original installation and database untouched.\n\n"
        "The eight member ZIPs contain disjoint complete-file changes since the verified Week 7 final, retaining every earlier owner assignment. Apply them only to an isolated copy of that exact baseline. REMOVED_BASELINE_PATHS.json is an inventory for isolated reconstruction, never an instruction to delete from a live project. Optional graph bytes come from the complete archive.\n\n"
        "Reports contains all nine English DOCX files. Each is byte-identical to the complete archive and its assigned member payload. Inspect PACKAGE_VERIFICATION.json and run the separate scripts.release.verify_week09_continuation verifier before distribution. Archive integrity does not establish scientific correctness, completed formal studies or learner benefit.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "passed", "archives": len(archives), "files": len(records)}))


if __name__ == "__main__":
    main()
