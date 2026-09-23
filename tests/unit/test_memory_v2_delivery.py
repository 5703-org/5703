"""Tiny authored archives test public/private release boundaries and reconstruction."""

import gzip
import hashlib
import json
import sys
import zipfile

import pytest

from scripts.release import week08_memory_v2_delivery as delivery


def row(name, value, **extra):
    return {"path": name, "bytes": len(value), "sha256": hashlib.sha256(value).hexdigest(), **extra}


@pytest.fixture
def package_inputs(tmp_path, monkeypatch):
    root, reports, resources = [tmp_path / n for n in ("project", "reports", "resources")]
    root.mkdir()
    (root / "README.md").write_bytes(b"Retained public fixture\n")
    (root / "generation").mkdir()
    (root / "generation/providers.py").write_bytes(b"# Changed authored fixture\n")
    # Actual private files must not be distributed, even if present in the tree.
    for name in (
        "evaluation/memory_v2/private/question-catalogue.json",
        "evaluation/private_fixture/gold.json",
        "evidence/review/coordinator-only-condition-key.json",
        "evidence/pytest-temp-child/history.json",
        "evidence/pg-temp2/history.json",
        "evidence/answering/new-catalogue-source-audit.json",
        "evidence/answering/q24-replacement-native-anchors.json",
        "evaluation/reliability/week08_cases_v3.json",
        "evaluation/reliability/week08_v9_regression.json",
        "evidence/week08-enhancement/20260920/formal-hints-analysis.json",
        "docs/delivery/week08/review/v9-independent-review.csv",
        ".env",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Fixture private data never public")
    report_names = ["Week08_Overall_Report.docx"] + [
        f"members/{m[0].replace(' ', '_')}/Week08_Report.docx" for m in delivery.MEMBERS
    ]
    for name in report_names:
        p = reports / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(p, "w") as z:
            z.writestr(
                "word/document.xml", "<doc>Authored packager fixture; not a rendered report.</doc>"
            )
    values = {
        "README.md": b"Retained public fixture\n",
        "generation/providers.py": b"# Old authored fixture\n",
        "WEEK08_ENHANCEMENT_CHANGESET.json": b'{"historical":true}',
        "resources/research/week08-enhancement-research.zip": b"Preserved separate old research fixture",
        "evaluation/private_fixture/gold.json": b"Historical private fixture",
        "evaluation/reliability/week08_cases_v3.json": b'{"cases":[{"split":"holdout","expected_behavior":"reference fixture"}]}',
        "evidence/week08-enhancement/20260920/formal-hints-analysis.json": b'{"items":[{"automatic_judgment":{"explanation":"PRIVATE FORMAL REFERENCE"}}]}',
    }
    rows = [
        row(
            n,
            v,
            category="release_metadata"
            if n.endswith("CHANGESET.json")
            else "explicitly_curated_research_archive"
            if n.endswith(".zip")
            else "project_file",
            **({"owner_index": 5} if n == "generation/providers.py" else {}),
        )
        for n, v in values.items()
    ]
    for i in range(80):
        p = resources / "official-corpus" / ("corpus.jsonl.gz" if i == 0 else f"fixture-{i}.txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        value = f"Authored resource {i}".encode()
        if i == 0:
            value = gzip.compress(b'{"fixture":"authored corpus export"}\n', mtime=0)
        p.write_bytes(value)
        name = "resources/official-corpus/" + p.name
        values[name] = value
        rows.append(row(name, value, category="verified_runtime_resource"))
    baseline = tmp_path / "baseline.zip"
    with zipfile.ZipFile(baseline, "w") as z:
        for name, value in values.items():
            z.writestr("learning-assistant/" + name, value)
        z.writestr("learning-assistant/PACKAGE_MANIFEST.json", json.dumps({"files": rows}))
    ownership = tmp_path / "ownership.json"
    ownership.write_text(
        json.dumps(
            {
                "files": [
                    {**r, "owner_index": 5} for r in rows if r["path"] == "generation/providers.py"
                ]
            }
        )
    )
    monkeypatch.setattr(delivery, "ROOT", root)
    destination = tmp_path / "output"
    argv = [
        "packager",
        "--baseline",
        str(baseline),
        "--baseline-ownership",
        str(ownership),
        "--resources",
        str(resources),
        "--reports",
        str(reports),
        "--destination",
        str(destination),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    return root, reports, resources, baseline, ownership, destination, argv


def test_actual_nine_zips_reconstruct_public_project_without_private_research(package_inputs):
    root, _, resources, baseline, _, output, _ = package_inputs
    delivery.main()
    inventory = json.loads((output / "EIGHT_MEMBER_INVENTORY.json").read_text())
    delta = {r["path"]: r for r in inventory["files"]}
    assert "README.md" not in delta
    assert delta["generation/providers.py"]["owner_index"] == 5  # Historic owner wins.
    assert len(list(output.glob("*.zip"))) == 9
    proof = json.loads((output / "RECONSTRUCTION_VERIFICATION.json").read_text())
    assert proof["status"] == "passed" and proof["verified_resources"] == 80
    assert proof["research_in_public_archives"] is False and proof["excluded_baseline_files"] == 4
    assert delivery.exclusion("resources/official-corpus/corpus.jsonl.gz") is None
    for name in (
        "resources/official-corpus/other.jsonl.gz",
        "resources/official-corpus/corpus.jsonl.gz.zip",
        "resources/research/research.zip",
    ):
        assert delivery.exclusion(name)
    for archive in output.glob("*.zip"):
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            assert not any(
                "/private/" in n
                or "/private_fixture/" in n
                or n.endswith(".env")
                or "/research/" in n
                or "coordinator-only" in n
                or "pytest-temp" in n
                or n.endswith("week08_cases_v3.json")
                or n.endswith("week08_v9_regression.json")
                or n.endswith("formal-hints-analysis.json")
                or n.endswith("v9-independent-review.csv")
                for n in names
            )
    with zipfile.ZipFile(output / delivery.FULL_NAME) as z:
        corpus = z.read("learning-assistant/resources/official-corpus/corpus.jsonl.gz")
        assert corpus == (resources / "official-corpus/corpus.jsonl.gz").read_bytes()
        assert gzip.decompress(corpus) == b'{"fixture":"authored corpus export"}\n'
        assert (
            z.read("learning-assistant/WEEK08_ENHANCEMENT_CHANGESET.json") == b'{"historical":true}'
        )
    assert baseline.exists() and (root / "evaluation/private_fixture/gold.json").exists()
    relocated = next(
        r
        for r in inventory["excluded_baseline_files"]
        if r["path"].endswith("week08_cases_v3.json")
    )
    assert relocated["private_relocation"] == "evaluation/reliability/private/week08_cases_v3.json"
    assert relocated["public_companion"].startswith(delivery.RELOCATION_ROOT + "/public/")
    with pytest.raises(ValueError, match="previous|prior"):
        delivery.main()


def test_plan_only_never_creates_archives_and_reports_missing_word_inputs(
    package_inputs, monkeypatch
):
    _, _, _, _, _, output, argv = package_inputs
    monkeypatch.setattr(sys, "argv", argv + ["--plan-only"])
    delivery.main()
    assert list(output.glob("*.zip")) == []
    plan = json.loads((output / "WEEK08_MEMORY_V2_PREPACKAGE_PLAN.json").read_text())
    assert plan["pending_reports"] == [] and len(plan["resources"]) == 80
    assert len(plan["excluded_baseline_files"]) == 4


def test_actual_reconstruction_rejects_tampered_member_bytes(package_inputs):
    *_, baseline, ownership, output, argv = package_inputs
    delivery.main()
    inventory = json.loads((output / "EIGHT_MEMBER_INVENTORY.json").read_text())
    members = [p for p in output.glob("*.zip") if p.name != delivery.FULL_NAME]
    attacked = members[0]
    with zipfile.ZipFile(attacked) as z:
        values = {n: z.read(n) for n in z.namelist()}
    target = next(n for n in values if "/repo_files/" in n)
    values[target] += b"tampered"
    with zipfile.ZipFile(attacked, "w") as z:
        for name, value in values.items():
            z.writestr(name, value)
    with pytest.raises(ValueError, match="bytes differ"):
        delivery.reconstruct(baseline, output / delivery.FULL_NAME, members, inventory)


def test_secret_scan_checks_decompressed_docx_and_resource_identity(package_inputs):
    root, reports, resources, *_ = package_inputs
    (root / ".env").write_text("LLM_API_KEY=authored-secret-value-123456789\n")
    with zipfile.ZipFile(
        reports / "Week08_Overall_Report.docx", "w", compression=zipfile.ZIP_DEFLATED
    ) as z:
        z.writestr("word/document.xml", "authored-secret-value-123456789")
    with pytest.raises(ValueError, match="Secret scan"):
        delivery.main()


def test_retained_baseline_corruption_and_ownership_reassignment_rejected(package_inputs):
    _, _, _, baseline, ownership, output, _ = package_inputs
    value = json.loads(ownership.read_text())
    value["files"][0]["owner_index"] = 3
    ownership.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="embedded baseline owner"):
        delivery.main()
    value["files"][0]["owner_index"] = 5
    ownership.write_text(json.dumps(value))
    with zipfile.ZipFile(baseline) as z:
        values = {n: z.read(n) for n in z.namelist()}
    values["learning-assistant/README.md"] += b"damaged"
    with zipfile.ZipFile(baseline, "w") as z:
        for name, content in values.items():
            z.writestr(name, content)
    with pytest.raises(ValueError, match="Retained baseline bytes"):
        delivery.main()
    assert not (output / "RECONSTRUCTION_VERIFICATION.json").exists()
