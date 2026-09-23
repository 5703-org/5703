"""Authored tiny archives exercise delivery boundaries without real private exports."""

import hashlib
import json
import sys
import zipfile

import pytest

from scripts.release import week08_enhancement_delivery as delivery


def record(path, value, **extra):
    return {"path": path, "bytes": len(value), "sha256": hashlib.sha256(value).hexdigest(), **extra}


def research(path, files, *, rows=None):
    manifest = {"files": rows if rows is not None else [record(k, v) for k, v in files.items()]}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, value in files.items():
            bundle.writestr(name, value)
        bundle.writestr("RESEARCH_MANIFEST.json", json.dumps(manifest))
    return path


def test_authorized_research_labels_allowed_but_secrets_and_path_attacks_rejected(tmp_path):
    path = research(tmp_path / "good.zip", {"private/labels/gold.json": b'{"answer": "authored"}'})
    assert delivery.validate_research(path, set())["verified_members"] == 1
    path = research(tmp_path / "bad-secret.zip", {"raw/events.json": b"authored-token-secret-123"})
    with pytest.raises(ValueError, match="Credential"):
        delivery.validate_research(path, {b"authored-token-secret-123"})
    for name in ("../outside.txt", ".env", "keys/deploy.pem"):
        path = research(tmp_path / "bad-path.zip", {name: b"fixture"})
        with pytest.raises(ValueError):
            delivery.validate_research(path, set())


def test_research_manifest_detects_modified_bytes_missing_rows_and_duplicate_rows(tmp_path):
    for rows in (
        [record("a.txt", b"different")],
        [record("other.txt", b"value")],
        [record("a.txt", b"value"), record("a.txt", b"value")],
    ):
        path = research(tmp_path / "bad.zip", {"a.txt": b"value"}, rows=rows)
        with pytest.raises(ValueError):
            delivery.validate_research(path, set())


def test_complete_package_keeps_baseline_and_research_out_of_eight_member_deltas(
    tmp_path, monkeypatch
):
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").write_bytes(b"Retained source\n")
    source_paths = [root / "README.md"]
    reports = [f"{delivery.REPORT_ROOT}/Week08_Overall_Report.docx"] + [
        f"{delivery.REPORT_ROOT}/members/{m[0].replace(' ', '_')}/Week08_Report.docx"
        for m in delivery.MEMBERS
    ]
    for name in reports + [
        "retrieval/source_spans.py",
        "generation/joint_policy.py",
        "retrieval/selection.py",
    ]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Authored packaging test fixture")
        source_paths.append(path)
    resource_root = tmp_path / "resources"
    values = {
        "README.md": b"Retained source\n",
        "WEEK08_CHANGESET.json": b'{"historical": true}',
    }
    rows = [record("README.md", values["README.md"], category="project_file")]
    rows.append(
        record(
            "WEEK08_CHANGESET.json", values["WEEK08_CHANGESET.json"], category="release_metadata"
        )
    )
    for i in range(80):
        path = resource_root / "official-corpus" / f"fixture-{i}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"Resource {i}".encode())
        target = f"resources/official-corpus/{path.name}"
        values[target] = path.read_bytes()
        rows.append(record(target, values[target], category="verified_runtime_resource"))
    baseline = tmp_path / "baseline.zip"
    with zipfile.ZipFile(baseline, "w") as bundle:
        for name, value in values.items():
            bundle.writestr("learning-assistant/" + name, value)
        bundle.writestr("learning-assistant/PACKAGE_MANIFEST.json", json.dumps({"files": rows}))
    ownership = tmp_path / "owners.json"
    ownership.write_text(json.dumps({"files": [{"path": "README.md", "owner_index": 0}]}))
    study = research(
        tmp_path / "research.zip", {"coordinator/conditions.json": b'{"fixture": true}'}
    )
    target = tmp_path / "delivery"
    monkeypatch.setattr(delivery, "ROOT", root)
    monkeypatch.setattr(delivery, "candidates", lambda: iter(source_paths))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "packager",
            "--destination",
            str(target),
            "--resources",
            str(resource_root),
            "--baseline",
            str(baseline),
            "--baseline-ownership",
            str(ownership),
            "--research",
            str(study),
        ],
    )
    delivery.main()
    inventory = json.loads((target / "EIGHT_MEMBER_INVENTORY.json").read_text())
    assigned = {row["path"]: row["owner_index"] for row in inventory["files"]}
    assert assigned["retrieval/source_spans.py"] == 1
    assert assigned["generation/joint_policy.py"] == 4
    assert assigned["retrieval/selection.py"] == 2
    with zipfile.ZipFile(target / delivery.FULL_NAME) as bundle:
        assert (
            bundle.read("learning-assistant/WEEK08_CHANGESET.json")
            == values["WEEK08_CHANGESET.json"]
        )
        assert (
            bundle.read("learning-assistant/resources/research/week08-enhancement-research.zip")
            == study.read_bytes()
        )
    union = []
    for path in target.glob("*.zip"):
        if path.name == delivery.FULL_NAME:
            continue
        with zipfile.ZipFile(path) as bundle:
            assert not any("research.zip" in name for name in bundle.namelist())
            union.extend(
                name.split("/repo_files/", 1)[1]
                for name in bundle.namelist()
                if "/repo_files/" in name
            )
    assert len(union) == len(set(union)) == len(inventory["files"])
    assert set(union) == set(assigned)
    assert "README.md" not in union
    proof = json.loads((target / "PACKAGE_VERIFICATION.json").read_text())
    assert len(proof["archives"]) == 9 and proof["verified_resources"] == 80
    assert proof["member_union_exact"] and proof["research_in_member_archives"] is False
