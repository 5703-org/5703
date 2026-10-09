"""Independently read nine actual archives and verify cumulative reconstruction."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from scripts.release.common import file_hash
from scripts.release.upgrade_delivery import MEMBERS
from scripts.release.week08_memory_v2_delivery import _indexed, _ownership, _safe_members
from scripts.release.week09_continuation_delivery import (
    BASELINE_SHA256,
    ONNX_ROOT,
    OWNERSHIP_SHA256,
    PREFIX,
    PREVIOUS_SHA256,
    REPORT_ROOT,
    exclusion,
    archive_names,
)


def require(value, message):
    if not value:
        raise ValueError(message)


def content(archive, name, row):
    info = archive.getinfo(name)
    require(info.file_size == row["bytes"], "Unexpected ZIP entry size: " + name)
    with archive.open(info) as stream:
        require(
            hashlib.file_digest(stream, "sha256").hexdigest() == row["sha256"],
            "Unexpected ZIP entry bytes: " + name,
        )


def inventory(archive):
    names = _safe_members(archive)
    value = archive.read(PREFIX + "PACKAGE_MANIFEST.json")
    rows = _indexed(json.loads(value)["files"])
    require(
        set(names) == {PREFIX + name for name in rows} | {PREFIX + "PACKAGE_MANIFEST.json"},
        "Archive membership differs from its manifest",
    )
    return rows, {
        "sha256": hashlib.sha256(value).hexdigest(),
        "bytes": len(value),
    }


def verify(destination, baseline_path, previous_path, ownership_path):
    for path, expected in (
        (baseline_path, BASELINE_SHA256),
        (previous_path, PREVIOUS_SHA256),
        (ownership_path, OWNERSHIP_SHA256),
    ):
        require(file_hash(path) == expected, "Immutable input identity differs")
    sidecar = json.loads((destination / "PACKAGE_VERIFICATION.json").read_text())
    listed = sidecar["archives"]
    require(
        len(listed) == 9 and len({row["path"] for row in listed}) == 9,
        "Need nine distinct archives",
    )
    full_name, member_names = archive_names(sidecar.get("release_date", "20260930"))
    expected_archives = {full_name, *member_names}
    require({row["path"] for row in listed} == expected_archives, "Unexpected archive identities")
    require(
        {p.name for p in destination.glob("*.zip")} == expected_archives, "Unlisted archive present"
    )
    for row in listed:
        path = destination / row["path"]
        require(
            path.stat().st_size == row["bytes"] and file_hash(path) == row["sha256"],
            "Archive checksum differs",
        )
    change = json.loads((destination / "CUMULATIVE_CHANGES.json").read_text())
    delta = _indexed(change["files"])
    removed = change["removed_baseline_paths"]
    require(len(removed) == len({row["path"] for row in removed}), "Duplicate baseline removals")
    extras = _indexed(change["optional_graphs_from_complete_archive"])
    union = {}
    with (
        zipfile.ZipFile(baseline_path) as base,
        zipfile.ZipFile(previous_path) as previous,
        zipfile.ZipFile(destination / full_name) as complete,
    ):
        baseline, _ = inventory(base)
        inherited, _ = inventory(previous)
        final, root_manifest = inventory(complete)
        require(
            json.loads(complete.read(PREFIX + "PACKAGE_MANIFEST.json")).get(
                "release_date", "20260930"
            )
            == sidecar.get("release_date", "20260930"),
            "Manifest and sidecar release dates differ",
        )
        owners = _ownership(ownership_path, baseline)
        complete_index = {**final, "PACKAGE_MANIFEST.json": root_manifest}
        expected_delta = {
            name
            for name, row in final.items()
            if baseline.get(name, {}).get("sha256") != row["sha256"]
            and row["category"] != "verified_runtime_resource"
            and not name.endswith(".onnx")
        } | {"PACKAGE_MANIFEST.json"}
        require(set(delta) == expected_delta, "Cumulative delta is not the exact changed-file set")
        for name, row in complete_index.items():
            require(not exclusion(name), "Excluded path in complete archive: " + name)
            content(complete, PREFIX + name, row)
        for name, row in final.items():
            require(
                type(row["owner_index"]) is int
                and 0 <= row["owner_index"] < len(MEMBERS)
                and row["owner"] == MEMBERS[row["owner_index"]][0],
                "Invalid complete-archive owner",
            )
            prior_owner = owners.get(name, inherited.get(name, {}).get("owner_index"))
            if prior_owner is not None:
                require(row["owner_index"] == prior_owner, "Original owner changed: " + name)
        resources = {
            name: row
            for name, row in final.items()
            if row["category"] == "verified_runtime_resource"
        }
        require(len(resources) == 80, "Expected all 80 official runtime resources")
        optional = {
            name: row
            for name, row in final.items()
            if row["category"] == "experimental_runtime_resource"
        }
        require(
            set(optional)
            == {
                ONNX_ROOT + "/" + leaf
                for leaf in ("manifest.json", "model.fp32.onnx", "model.int8.onnx")
            },
            "Unexpected optional resources",
        )
        for name, row in resources.items():
            require(
                all(
                    baseline.get(name, {}).get(key) == row[key] == inherited.get(name, {}).get(key)
                    for key in ("sha256", "bytes")
                ),
                "Original resource changed",
            )
            content(base, PREFIX + name, row)
            content(previous, PREFIX + name, row)
        for name, row in optional.items():
            require(
                all(inherited.get(name, {}).get(key) == row[key] for key in ("sha256", "bytes")),
                "Optional resource changed",
            )
            content(previous, PREFIX + name, row)
        graph_meta = json.loads(complete.read(PREFIX + ONNX_ROOT + "/manifest.json"))
        for backend in ("onnx_fp32", "onnx_int8"):
            config = json.loads(
                complete.read(
                    PREFIX + "configs/retrieval/chat_cpu_experimental_" + backend + ".json"
                )
            )
            require(
                config["reranker_runtime"]["artifact_sha256"]
                == optional[ONNX_ROOT + "/manifest.json"]["sha256"]
                and config["reranker_model"] == graph_meta["model"]
                and config["reranker_revision"] == graph_meta["revision"],
                "Optional runtime configuration differs",
            )
        for name in ("model.fp32.onnx", "model.int8.onnx"):
            require(
                graph_meta["files"][name] == optional[ONNX_ROOT + "/" + name]["sha256"],
                "Optional graph metadata differs",
            )
        reports = {"Week09_Overall_Report.docx"} | {
            "Week09_" + m[0].replace(" ", "_") + "_Report.docx" for m in MEMBERS
        }
        require(set(sidecar["report_hashes"]) == reports, "Nine exact report hashes required")
        for report in reports:
            row = final[REPORT_ROOT + "/" + report]
            require(
                file_hash(destination / "Reports" / report)
                == sidecar["report_hashes"][report]
                == row["sha256"],
                "Standalone/full report mismatch",
            )
        for i, member in enumerate(MEMBERS):
            slug = member[0].replace(" ", "_")
            filename = member_names[i]
            with zipfile.ZipFile(destination / filename) as archive:
                names = _safe_members(archive)
                metadata = json.loads(archive.read(slug + "/OWNED_FILES.json"))
                require(
                    metadata["owner"] == member[0] and metadata["student_id"] == member[1],
                    "Member identity mismatch",
                )
                rows = _indexed(metadata["files"])
                require(bool(rows), "Empty member delta")
                report = "Week09_" + slug + "_Report.docx"
                expected = {
                    slug + "/" + x
                    for x in (
                        "README.md",
                        "OWNED_FILES.json",
                        "COMMIT_MESSAGE.txt",
                        "PR_BODY.md",
                        report,
                    )
                } | {slug + "/repo_files/" + n for n in rows}
                if i == 0:
                    expected.add(slug + "/REMOVED_BASELINE_PATHS.json")
                    require(
                        json.loads(archive.read(slug + "/REMOVED_BASELINE_PATHS.json"))["files"]
                        == removed,
                        "Removal receipt mismatch",
                    )
                require(set(names) == expected, "Unassigned file in member archive")
                require(
                    hashlib.sha256(archive.read(slug + "/" + report)).hexdigest()
                    == sidecar["report_hashes"][report],
                    "Member report differs",
                )
                for name, row in rows.items():
                    require(
                        name not in union
                        and name in delta
                        and row == delta[name]
                        and row["owner_index"] == i
                        and row["owner"] == member[0],
                        "Duplicate or changed member ownership",
                    )
                    require(
                        name in complete_index
                        and all(row[k] == complete_index[name][k] for k in ("sha256", "bytes")),
                        "Member bytes do not belong to full archive",
                    )
                    require(not exclusion(name), "Private path in member delta")
                    content(archive, slug + "/repo_files/" + name, row)
                    union[name] = row["sha256"]
        require(set(union) == set(delta), "Eight-member delta union differs")
        removed_names = {row["path"] for row in removed}
        require(removed_names == set(baseline) - set(final), "Virtual removal set differs")
        require(
            all(baseline[row["path"]]["sha256"] == row["sha256"] for row in removed),
            "Removed baseline identity differs",
        )
        require(
            set(extras)
            == {
                n
                for n in optional
                if n.endswith(".onnx")
                and baseline.get(n, {}).get("sha256") != optional[n]["sha256"]
            },
            "Extra reconstruction resources differ",
        )
        virtual = {
            name: row["sha256"] for name, row in baseline.items() if name not in removed_names
        }
        for name in set(virtual) - set(union) - set(extras):
            content(base, PREFIX + name, baseline[name])
        virtual.update(union)
        virtual.update({name: row["sha256"] for name, row in extras.items()})
        require(
            virtual == {name: row["sha256"] for name, row in complete_index.items()},
            "Cumulative reconstruction differs",
        )
    return {
        "version": "week09_continuation_independent_archive_verification_v1",
        "status": "passed",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "archives": listed,
        "baseline_sha256": BASELINE_SHA256,
        "previous_sha256": PREVIOUS_SHA256,
        "ownership_sha256": OWNERSHIP_SHA256,
        "files_including_manifest": len(complete_index),
        "delta_files": len(union),
        "virtual_removed_files": len(removed),
        "member_overlaps": 0,
        "official_resources": 80,
        "optional_resources": 3,
        "reports": 9,
        "scope": "Actual archive bytes, membership, historical ownership, report copies and virtual reconstruction verified. No files restored/deleted; no scientific quality or runtime execution inferred. Privacy classification still depends on curated public inputs and the separate configured-secret scan.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("destination", "baseline", "previous", "ownership"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.destination / "INDEPENDENT_VERIFICATION.json"
    require(not output.exists(), "Preserve the existing verification receipt")
    result = verify(args.destination, args.baseline, args.previous, args.ownership)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "archives": 9, "reports": 9}))


if __name__ == "__main__":
    main()
