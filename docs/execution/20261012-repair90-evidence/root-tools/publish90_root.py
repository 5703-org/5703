"""Publish the reviewed final local report with exclusive copies and append-only ledgers."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

W = Path(__file__).resolve().parent
M = Path(r"E:\5703\learning-assistant")
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def read(path):
    return json.loads(Path(path).read_bytes())
def checked_raw(record):
    path = Path(record["path"])
    assert path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    assert len(raw) == record["bytes"] and sha(raw) == record["sha256"], str(path)
    return raw
def pin(path):
    raw = Path(path).read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}
def exclusive(path, raw):
    with Path(path).open("xb") as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())
def safe_target(path):
    assert path.is_relative_to(M / "docs")
    for parent in [path, *path.parents]:
        if parent == M.parent:
            break
        assert not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)()
    assert path.resolve(strict=False) == path

ready = read(W / "phase90-publication-ready.json")
assert ready["status"] == "READY_FOR_READ_ONLY_REVIEW" and ready["publication_authorized_in_session"]
selection = json.loads(checked_raw(ready["selection"]))
assert len(selection) == ready["selected_payload_count"] and 0 < len(selection) < 500
assert sum(row["bytes"] for row in selection) == ready["selected_payload_bytes"] < 15 * 1024 * 1024
for record in ready["current_source_pins"]:
    checked_raw(record)
checked_raw(ready["old_report_preserved_pin"])
for record in ready["append_preimages"]:
    checked_raw(record)
report_target = Path(ready["Main_target_report"])
evidence_target = Path(ready["Main_target_evidence"])
assert report_target == M / "docs/execution/20261012-repair90-checker-retest.md"
assert evidence_target == M / "docs/execution/20261012-repair90-evidence"
safe_target(report_target)
safe_target(evidence_target)
assert not report_target.exists() and not evidence_target.exists()
prepared = []
for record in selection:
    source = Path(record["path"])
    assert source.is_relative_to(W)
    relative = Path(record["destination"])
    assert not relative.is_absolute() and not relative.drive and ".." not in relative.parts
    target = evidence_target / relative
    safe_target(target)
    prepared.append((record, target, checked_raw(record)))
report_raw = checked_raw(ready["report"])
append_records = [
    (ready["append_preimages"][0], ready["progress_append"]),
    (ready["append_preimages"][1], ready["handover_append"]),
]
append_values = [(original, addition, checked_raw(original), checked_raw(addition)) for original, addition in append_records]
evidence_target.mkdir(parents=False, exist_ok=False)
entries = []
for source_record, target, raw in prepared:
    target.parent.mkdir(parents=True, exist_ok=True)
    exclusive(target, raw)
    assert target.read_bytes() == raw
    entries.append({"relative_path": target.relative_to(evidence_target).as_posix(),
        "source": source_record, "bytes": len(raw), "sha256": sha(raw)})
exclusive(report_target, report_raw)
assert report_target.read_bytes() == report_raw
appends = []
for original_record, addition_record, original, addition in append_values:
    path = Path(original_record["path"])
    safe_target(path)
    assert path.read_bytes() == original, "CONCURRENT_USER_DOCUMENT_CHANGE_PRESERVED"
    with path.open("ab") as out:
        out.write(addition)
        out.flush()
        os.fsync(out.fileno())
    after = path.read_bytes()
    assert after == original + addition and after[:len(original)] == original
    appends.append({"before": original_record, "addition": addition_record, "after": pin(path),
        "old_prefix_bytes": len(original), "old_prefix_preserved": True})
for record in ready["current_source_pins"]:
    checked_raw(record)
checked_raw(ready["old_report_preserved_pin"])
manifest = {"schema": "repair90_final_local_publication_readback_v1", "status": "PUBLISHED_AND_READBACK_PASS",
    "finished_utc": datetime.now(timezone.utc).isoformat(), "report": pin(report_target),
    "evidence_payload_count": len(entries), "evidence_payload_bytes": sum(row["bytes"] for row in entries),
    "evidence": entries, "append_only_ledgers": appends, "current_B_source_pins": ready["current_source_pins"],
    "old_DEV89_report_preserved": ready["old_report_preserved_pin"],
    "private_auth_or_sealed_rubric_payload_copied": False, "old_delivery_or_experiment_deleted": False,
    "remote_push_upload_deploy_or_course_submission": False, "new_quality_complete_DOM_n": 0,
    "writer_source_sha256": sha(Path(__file__).read_bytes())}
raw = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
exclusive(evidence_target / "readback-manifest90.json", raw)
exclusive(W / "phase90-publication-receipt.json", raw)
assert (evidence_target / "readback-manifest90.json").read_bytes() == (W / "phase90-publication-receipt.json").read_bytes()
print(json.dumps({"status": manifest["status"], "report": str(report_target), "report_sha256": manifest["report"]["sha256"],
    "evidence_payload_count": len(entries), "evidence_payload_bytes": manifest["evidence_payload_bytes"],
    "old_ledger_prefixes_preserved": True, "qualified_new_pages": 0}))
