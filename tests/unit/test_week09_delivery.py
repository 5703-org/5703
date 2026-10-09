"""Authored miniature archives exercise cumulative ownership and public boundaries."""

import hashlib
import json
import sys
import zipfile

import pytest

from scripts.release import week09_delivery as delivery


def checksum(value):
    return hashlib.sha256(value).hexdigest()


def create_archive(path, values):
    rows = []
    with zipfile.ZipFile(path, "w") as archive:
        for name, (value, extra) in values.items():
            archive.writestr(delivery.PREFIX + name, value)
            rows.append({"path": name, "sha256": checksum(value), "bytes": len(value), **extra})
        archive.writestr(delivery.PREFIX + "PACKAGE_MANIFEST.json", json.dumps({"files": rows}))
    return rows


@pytest.fixture
def package_inputs(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()

    def write(name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return path

    write("README.md", b"Retained authored public file\n")
    changed = write("generation/providers.py", b"# Latest complete Week 9 authored file\n")
    write("generation/week08_addition.py", b"# Retained Week 8 addition\n")
    public_name = "evidence/week09-generation/20260926/public/result.json"
    write(public_name, b'{"requests":4,"published":2,"failed":2,"human_ratings":null}')
    private_names = [
        "evaluation/week09/fixtures/cases.json",
        "evaluation/week09/gold/labels.json",
        "evidence/week09-generation/20260926/raw_provider/response.json",
        "evidence/week09-generation/20260926/review_packets/packet.json",
        "evidence/week09-generation/20260926/private/source.json",
    ]
    for name in private_names:
        write(name, b'{"question":"private fixture","answer_text":"private fixture"}')
    write(".env", b"LLM_API_KEY=authored-private-secret-123456789\n")
    write(".env.example", b"LLM_API_KEY=\n")
    report_hashes = {}
    names = ["Week09_Overall_Report.docx"] + [
        "Week09_" + member[0].replace(" ", "_") + "_Report.docx" for member in delivery.MEMBERS
    ]
    for name in names:
        path = root / delivery.REPORT_ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as document:
            document.writestr("word/document.xml", "<doc>Authored release test fixture.</doc>")
        report_hashes[name] = checksum(path.read_bytes())
    review = tmp_path / "report-verification.json"
    review.write_text(
        json.dumps(
            {
                "status": "passed",
                "every_page_inspected": True,
                "report_hashes": report_hashes,
                "scope": "Synthetic builder fixture; no actual document rendering claimed.",
            }
        )
    )
    baseline_values = {
        "README.md": (b"Retained authored public file\n", {"category": "project_file"}),
        "generation/providers.py": (
            b"# Week 7 authored file\n",
            {"category": "project_file", "owner_index": 5},
        ),
        "obsolete.py": (b"# Isolated baseline removal\n", {"category": "project_file"}),
    }
    for index in range(80):
        baseline_values[f"resources/official-corpus/fixture-{index}.txt"] = (
            f"Authored resource {index}".encode(),
            {"category": "verified_runtime_resource"},
        )
    baseline = tmp_path / "week07.zip"
    rows = create_archive(baseline, baseline_values)
    previous_values = dict(baseline_values)
    previous_values["generation/providers.py"] = (
        b"# Intermediate Week 8 file\n",
        {"category": "project_file", "owner_index": 5},
    )
    previous_values["generation/week08_addition.py"] = (
        b"# Retained Week 8 addition\n",
        {"category": "project_file", "owner_index": 3},
    )
    graphs = {
        "model.fp32.onnx": b"Authored FP32 graph fixture",
        "model.int8.onnx": b"Authored INT8 graph fixture",
    }
    model = {
        "model": "fixture-model",
        "revision": "fixture-revision",
        "files": {name: checksum(value) for name, value in graphs.items()},
    }
    metadata = json.dumps(model).encode()
    for leaf, value in {**graphs, "manifest.json": metadata}.items():
        previous_values[delivery.ONNX_ROOT + "/" + leaf] = (
            value,
            {"category": "experimental_runtime_resource", "owner_index": 2},
        )
    for backend in ("onnx_fp32", "onnx_int8"):
        write(
            f"configs/retrieval/chat_cpu_experimental_{backend}.json",
            json.dumps(
                {
                    "reranker_model": model["model"],
                    "reranker_revision": model["revision"],
                    "reranker_runtime": {
                        "artifact_path": delivery.ONNX_ROOT + "/manifest.json",
                        "artifact_sha256": checksum(metadata),
                    },
                }
            ).encode(),
        )
    previous = tmp_path / "week08.zip"
    create_archive(previous, previous_values)
    ownership = tmp_path / "owners.json"
    ownership.write_text(json.dumps({"files": [row for row in rows if "owner_index" in row]}))
    output = tmp_path / "output"
    monkeypatch.setattr(delivery, "ROOT", root)
    monkeypatch.setattr(
        delivery, "candidates", lambda: (path for path in root.rglob("*") if path.is_file())
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "week09_delivery",
            "--baseline",
            str(baseline),
            "--previous",
            str(previous),
            "--ownership",
            str(ownership),
            "--destination",
            str(output),
            "--report-verification",
            str(review),
        ],
    )
    return root, output, baseline, previous, review, changed, public_name, private_names


def test_nine_archives_preserve_latest_files_resource_bytes_and_report_identity(package_inputs):
    root, output, baseline, previous, _, changed, public_name, private_names = package_inputs
    delivery.main()
    proof = json.loads((output / "PACKAGE_VERIFICATION.json").read_text())
    assert proof["status"] == "passed" and proof["member_overlaps"] == 0
    assert proof["resources_preserved"] == 80 and proof["experimental_resources_preserved"] == 3
    assert proof["member_report_equality"] and proof["baseline_bytes_verified"]
    assert len(list(output.glob("*.zip"))) == 9
    with zipfile.ZipFile(output / delivery.FULL_NAME) as archive:
        assert archive.read(delivery.PREFIX + "generation/providers.py") == changed.read_bytes()
        assert (
            archive.read(delivery.PREFIX + "generation/week08_addition.py")
            == (root / "generation/week08_addition.py").read_bytes()
        )
        assert delivery.PREFIX + public_name in archive.namelist()
        assert not any(delivery.PREFIX + name in archive.namelist() for name in private_names)
        records = json.loads(archive.read(delivery.PREFIX + "PACKAGE_MANIFEST.json"))["files"]
        assert (
            next(row for row in records if row["path"] == "generation/providers.py")["owner_index"]
            == 5
        )
        with zipfile.ZipFile(previous) as old:
            for name in old.namelist():
                if "/resources/" in name or "/reranker-onnx/" in name:
                    assert archive.read(name) == old.read(name)
    for index, member in enumerate(delivery.MEMBERS):
        slug = member[0].replace(" ", "_")
        name = "Week09_" + slug + "_Report.docx"
        with zipfile.ZipFile(
            output / f"CS30-1_Week09_{index + 1:02}_{slug}_20260926.zip"
        ) as archive:
            assert archive.read(slug + "/" + name) == (output / "Reports" / name).read_bytes()
    assert baseline.exists() and all((root / name).exists() for name in private_names)
    with pytest.raises(ValueError, match="new destination"):
        delivery.main()


def test_raw_provider_payload_cannot_hide_in_numeric_public_report(package_inputs):
    root, _, _, _, _, _, public_name, _ = package_inputs
    (root / public_name).write_bytes(b'{"metrics":{"rows":[{"answer_text":"PRIVATE RAW OUTPUT"}]}}')
    with pytest.raises(ValueError, match="Private research content"):
        delivery.main()


def test_configured_secret_is_scanned_inside_compressed_docx(package_inputs):
    root, _, _, _, review, *_ = package_inputs
    name = "Week09_Overall_Report.docx"
    path = root / delivery.REPORT_ROOT / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as document:
        document.writestr("word/document.xml", "authored-private-secret-123456789")
    value = json.loads(review.read_text())
    value["report_hashes"][name] = checksum(path.read_bytes())
    review.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="Configured credential"):
        delivery.main()


def test_report_bytes_must_match_inspected_document_hashes(package_inputs):
    root, output, _, _, *_ = package_inputs
    (root / delivery.REPORT_ROOT / "Week09_Overall_Report.docx").write_bytes(
        b"Changed after inspection"
    )
    with pytest.raises(AssertionError):
        delivery.main()
    assert not output.exists()


def test_previous_optional_resource_corruption_stops_reconstruction(package_inputs):
    _, output, _, previous, *_ = package_inputs
    with zipfile.ZipFile(previous) as archive:
        values = {name: archive.read(name) for name in archive.namelist()}
    values[delivery.PREFIX + delivery.ONNX_ROOT + "/model.int8.onnx"] += b"corrupt"
    with zipfile.ZipFile(previous, "w") as archive:
        for name, value in values.items():
            archive.writestr(name, value)
    with pytest.raises(AssertionError):
        delivery.main()
    assert not (output / "PACKAGE_VERIFICATION.json").exists()
