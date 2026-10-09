"""Miniature real ZIPs verify the successor workflow without producing a release."""

import hashlib
import gzip
import json
import sys
import zipfile

import pytest
import test_week09_delivery as fixtures

from scripts.release import verify_week09_continuation as verifier
from scripts.release import week09_continuation_delivery as delivery


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, "delivery", delivery)
    values = fixtures.package_inputs.__wrapped__(tmp_path, monkeypatch)
    root, output, baseline, previous, *_ = values
    ownership = tmp_path / "owners.json"
    with zipfile.ZipFile(previous) as archive:
        records = json.loads(archive.read(delivery.PREFIX + "PACKAGE_MANIFEST.json"))["files"]
    source_hash = next(r["sha256"] for r in records if r["category"] == "verified_runtime_resource")
    visual = root / delivery.VISUAL_ROOT
    visual.mkdir(parents=True)
    books, hashes = [], {}
    for leaf in delivery.VISUAL_CATALOGS:
        value = gzip.compress(b'{"source_unit":"authored public source geometry"}\n', mtime=0)
        (visual / leaf).write_bytes(value)
        hashes[leaf] = hashlib.sha256(value).hexdigest()
        books.append(
            {
                "catalog_path": delivery.VISUAL_ROOT + "/" + leaf,
                "catalog_sha256": hashes[leaf],
                "source_sha256": source_hash,
            }
        )
    (visual / "manifest.json").write_text(json.dumps({"books": books}))
    monkeypatch.setattr(delivery, "VISUAL_CATALOGS", hashes)
    prior = root / delivery.VISUAL_PRIOR_ROOT
    prior.mkdir(parents=True)
    prior_books, prior_hashes = [], {}
    for leaf in delivery.VISUAL_PRIOR_CATALOGS:
        value = gzip.compress(b'{"source_unit":"authored prior source geometry"}\n', mtime=0)
        (prior / leaf).write_bytes(value)
        prior_hashes[leaf] = hashlib.sha256(value).hexdigest()
        prior_books.append(
            {
                "catalog_path": delivery.VISUAL_PRIOR_ROOT + "/" + leaf,
                "catalog_sha256": prior_hashes[leaf],
                "source_sha256": source_hash,
            }
        )
    (prior / "manifest.json").write_text(json.dumps({"books": prior_books}))
    monkeypatch.setattr(delivery, "VISUAL_PRIOR_CATALOGS", prior_hashes)
    review = root / delivery.VISUAL_REVIEW_SHEET
    review.parent.mkdir(parents=True)
    review.write_text(
        "region_id,reviewer_id,original_page_match,structure_correct,caption_or_symbol_correct,notes\nexample,,,,,\n"
    )
    monkeypatch.setattr(delivery, "VISUAL_REVIEW_SHEET_SHA256", delivery.file_hash(review))
    for module in (delivery, verifier):
        monkeypatch.setattr(module, "BASELINE_SHA256", delivery.file_hash(baseline))
        monkeypatch.setattr(module, "PREVIOUS_SHA256", delivery.file_hash(previous))
        monkeypatch.setattr(module, "OWNERSHIP_SHA256", delivery.file_hash(ownership))
    return (*values, ownership)


def test_actual_nine_archives_reconstruct_and_preserve_input_bytes(inputs):
    root, output, baseline, previous, _, _, _, private_names, ownership = inputs
    identities = {p: delivery.file_hash(p) for p in (baseline, previous, ownership)}
    delivery.main()
    proof = verifier.verify(output, baseline, previous, ownership)
    assert proof["status"] == "passed" and proof["member_overlaps"] == 0
    assert proof["official_resources"] == 80 and proof["optional_resources"] == 3
    assert proof["reports"] == 9 and len(proof["archives"]) == 9
    with zipfile.ZipFile(output / delivery.FULL_NAME) as archive:
        for leaf in delivery.VISUAL_CATALOGS:
            name = delivery.VISUAL_ROOT + "/" + leaf
            assert archive.read(delivery.PREFIX + name) == (root / name).read_bytes()
        for leaf in delivery.VISUAL_PRIOR_CATALOGS:
            name = delivery.VISUAL_PRIOR_ROOT + "/" + leaf
            assert archive.read(delivery.PREFIX + name) == (root / name).read_bytes()
        assert (
            archive.read(delivery.PREFIX + delivery.VISUAL_REVIEW_SHEET)
            == (root / delivery.VISUAL_REVIEW_SHEET).read_bytes()
        )
    assert all(delivery.file_hash(p) == value for p, value in identities.items())
    assert all((root / name).exists() for name in private_names)
    assert "never an instruction to delete" in (output / "README.md").read_text()
    with pytest.raises(ValueError, match="new destination"):
        delivery.main()


def test_dated_nine_archives_reconstruct_with_current_report_parity(inputs, monkeypatch):
    _, output, baseline, previous, _, _, _, _, ownership = inputs
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--release-date", "20261001"])
    delivery.main()
    complete, members = delivery.archive_names("20261001")
    assert {p.name for p in output.glob("*.zip")} == {complete, *members}
    proof = verifier.verify(output, baseline, previous, ownership)
    assert proof["status"] == "passed"
    assert len(proof["archives"]) == 9 and proof["reports"] == 9
    assert proof["member_overlaps"] == 0


def test_plan_reports_missing_artifacts_without_creating_destination(inputs, monkeypatch, tmp_path):
    root, output, *rest = inputs
    report = root / delivery.REPORT_ROOT / "Week09_Overall_Report.docx"
    original = report.read_bytes()
    report.write_bytes(original + b"uninspected change")
    plan = tmp_path / "plan.json"
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--plan-only", "--plan-output", str(plan)])
    delivery.main()
    value = json.loads(plan.read_text())
    assert value["status"] == "prepared_not_created"
    assert value["blockers"] and value["resources"] == 80
    assert not output.exists()
    assert report.read_bytes() == original + b"uninspected change"


@pytest.mark.parametrize(
    "name",
    [
        "evaluation/week09_continuation/pilot-labels.json",
        "evidence/week09-continuation/20260930/pilots/response.json",
        "evidence/week09-learning/20260930/runtime-credentials.json",
        "artifacts/reports/frontend/session/storage_state.json",
        "evidence/week09-learning/20260930/local.private.json",
    ],
)
def test_private_inputs_excluded_even_when_candidates_supply_them(inputs, name):
    root, output, *_ = inputs
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"password":"private test account","answer_text":"private result"}')
    delivery.main()
    with zipfile.ZipFile(output / delivery.FULL_NAME) as archive:
        assert delivery.PREFIX + name not in archive.namelist()
    assert path.exists()


def test_nested_provider_body_rejected_before_archive_creation(inputs):
    root, output, _, _, _, _, public_name, *_ = inputs
    (root / public_name).write_text('{"metrics":[{"raw_provider_response":"private"}]}')
    with pytest.raises(ValueError, match="Private research content"):
        delivery.main()
    assert not output.exists()


def test_portable_credential_test_source_included_without_allowing_credentials(inputs):
    root, output, *_ = inputs
    name = "tests/unit/test_portable_credentials.py"
    source = root / name
    source.parent.mkdir(parents=True, exist_ok=True)
    payload = b'"""Authored credential lifecycle regression."""\n'
    source.write_bytes(payload)
    private_names = [
        "evidence/week09-learning/20260930/runtime-credentials.json",
        "credentials/local.json",
        "tests/unit/local_credentials.py",
        ".secrets/initial-admin-password.txt",
    ]
    for private_name in private_names:
        private = root / private_name
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_text("authored private fixture")
        assert delivery.exclusion(private_name) is not None
    delivery.main()
    with zipfile.ZipFile(output / delivery.FULL_NAME) as archive:
        assert archive.read(delivery.PREFIX + name) == payload
        assert all(delivery.PREFIX + n not in archive.namelist() for n in private_names)


def test_allowed_portable_credential_source_still_rejects_configured_secret(inputs):
    root, output, *_ = inputs
    source = root / "tests/unit/test_portable_credentials.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text('SECRET = "authored-private-secret-123456789"\n')
    with pytest.raises(ValueError, match="Configured credential"):
        delivery.main()
    assert not output.exists()


def test_configured_secret_inside_docx_rejected_before_archive_creation(inputs):
    root, output, _, _, review, *_ = inputs
    report = root / delivery.REPORT_ROOT / "Week09_Overall_Report.docx"
    with zipfile.ZipFile(report, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "authored-private-secret-123456789")
    value = json.loads(review.read_text())
    value["report_hashes"][report.name] = delivery.file_hash(report)
    review.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="Configured credential"):
        delivery.main()
    assert not output.exists()


def test_changed_baseline_rejected_without_writing_output(inputs):
    _, output, baseline, *_ = inputs
    baseline.write_bytes(baseline.read_bytes() + b"changed immutable input")
    with pytest.raises(ValueError, match="immutable declared baseline"):
        delivery.main()
    assert not output.exists()


def test_independent_verifier_rejects_duplicate_archive_rows(inputs):
    _, output, baseline, previous, *_, ownership = inputs
    delivery.main()
    path = output / "PACKAGE_VERIFICATION.json"
    value = json.loads(path.read_text())
    value["archives"][-1] = value["archives"][0]
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="nine distinct archives"):
        verifier.verify(output, baseline, previous, ownership)


def test_independent_verifier_rejects_unchanged_file_claimed_as_delta(inputs):
    _, output, baseline, previous, *_, ownership = inputs
    delivery.main()
    with zipfile.ZipFile(output / delivery.FULL_NAME) as archive:
        unchanged = next(
            row
            for row in json.loads(archive.read(delivery.PREFIX + "PACKAGE_MANIFEST.json"))["files"]
            if row["path"] == "README.md"
        )
    path = output / "CUMULATIVE_CHANGES.json"
    value = json.loads(path.read_text())
    value["files"].append(unchanged)
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="exact changed-file set"):
        verifier.verify(output, baseline, previous, ownership)


def test_independent_verifier_reads_payload_even_if_archive_sidecar_rehashed(inputs):
    _, output, baseline, previous, *_, ownership = inputs
    delivery.main()
    member = delivery.MEMBERS[5][0].replace(" ", "_")
    filename = f"CS30-1_Week09_Continuation_06_{member}_20260930.zip"
    path = output / filename
    with zipfile.ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    contents[member + "/repo_files/generation/providers.py"] += b"unexpected mutation"
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in contents.items():
            archive.writestr(name, value)
    receipt = output / "PACKAGE_VERIFICATION.json"
    value = json.loads(receipt.read_text())
    row = next(row for row in value["archives"] if row["path"] == filename)
    row.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
    receipt.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="Unexpected ZIP entry"):
        verifier.verify(output, baseline, previous, ownership)


def test_visual_report_receipt_is_required_for_creation(inputs):
    _, output, _, _, review, *_ = inputs
    value = json.loads(review.read_text())
    value["every_page_inspected"] = False
    review.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="visual verification"):
        delivery.main()
    assert not output.exists()


def test_visual_runtime_exception_is_exact_and_hash_bound(inputs):
    root, output, *_ = inputs
    leaf = next(iter(delivery.VISUAL_CATALOGS))
    name = delivery.VISUAL_ROOT + "/" + leaf
    assert delivery.exclusion(name) is None
    assert delivery.exclusion(name.replace("attempt2", "attempt3")) is not None
    assert delivery.exclusion(delivery.VISUAL_ROOT + "/private-other.jsonl.gz") is not None
    (root / name).write_bytes(gzip.compress(b"changed source catalogue"))
    with pytest.raises(ValueError, match="frozen identity"):
        delivery.main()
    assert not output.exists()


def test_prior_visual_catalogue_requires_exact_path_and_bytes(inputs):
    root, output, *_ = inputs
    leaf = next(iter(delivery.VISUAL_PRIOR_CATALOGS))
    name = delivery.VISUAL_PRIOR_ROOT + "/" + leaf
    assert delivery.exclusion(name) is None
    assert delivery.exclusion(delivery.VISUAL_PRIOR_ROOT + "/unknown-regions.jsonl.gz") is not None
    (root / name).write_bytes(gzip.compress(b"changed prior source catalogue"))
    with pytest.raises(ValueError, match="frozen identity"):
        delivery.main()
    assert not output.exists()


def test_blank_visual_review_sheet_cannot_be_replaced_with_scores(inputs):
    root, output, *_ = inputs
    review = root / delivery.VISUAL_REVIEW_SHEET
    review.write_text(review.read_text() + "example,researcher,true,true,true,scored\n")
    with pytest.raises(ValueError, match="Blank visual-review sheet differs"):
        delivery.main()
    assert not output.exists()


def test_visual_manifest_cannot_substitute_original_source(inputs):
    root, output, *_ = inputs
    path = root / delivery.VISUAL_ROOT / "manifest.json"
    value = json.loads(path.read_text())
    value["books"][0]["source_sha256"] = "0" * 64
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="original source"):
        delivery.main()
    assert not output.exists()


def test_visual_decompressed_content_is_scanned(inputs, monkeypatch):
    root, output, *_ = inputs
    leaf = next(iter(delivery.VISUAL_CATALOGS))
    payload = gzip.compress(b'{"text":"authored-private-secret-123456789"}', mtime=0)
    (root / delivery.VISUAL_ROOT / leaf).write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setitem(delivery.VISUAL_CATALOGS, leaf, digest)
    path = root / delivery.VISUAL_ROOT / "manifest.json"
    value = json.loads(path.read_text())
    value["books"][0]["catalog_sha256"] = digest
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="Configured credential"):
        delivery.main()
    assert not output.exists()
