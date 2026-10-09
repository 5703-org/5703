"""Authored report directories survive ledger regeneration; unrelated paths stay guarded."""

import json
import sys

import pytest

from scripts.release import generate_delivery


def test_known_weekly_reports_survive_regeneration(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_delivery, "DESTINATION", tmp_path)
    monkeypatch.setattr(sys, "argv", ["generate_delivery"])
    reports = []
    for folder in (
        "week08",
        "week08-enhancement",
        "week08-memory-v2",
        "teaching-performance",
        "week09",
        "week09-continuation",
    ):
        path = tmp_path / folder / "report.md"
        path.parent.mkdir()
        path.write_bytes(b"Retained authored report\n")
        reports.append(path)
    generate_delivery.main()
    assert all(path.read_bytes() == b"Retained authored report\n" for path in reports)
    assert (tmp_path / "manifest.json").is_file()
    monkeypatch.setattr(sys, "argv", ["generate_delivery", "--check"])
    generate_delivery.main()


def test_unexpected_supplement_stops_before_output_mutation(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_delivery, "DESTINATION", tmp_path)
    monkeypatch.setattr(sys, "argv", ["generate_delivery"])
    unexpected = tmp_path / "teaching-performance-old"
    unexpected.mkdir()
    retained = unexpected / "report.md"
    retained.write_bytes(b"Preserve this unknown report")
    with pytest.raises(SystemExit, match="Unexpected delivery files"):
        generate_delivery.main()
    assert retained.read_bytes() == b"Preserve this unknown report"
    assert not (tmp_path / "manifest.json").exists()


def test_continuation_observations_reach_both_groupings_and_acceptance_without_mutation():
    raw = {name: (generate_delivery.ROOT / name).read_bytes() for name in generate_delivery.INPUTS}
    tasks = json.loads(raw[generate_delivery.INPUTS[0]])
    checks = json.loads(raw[generate_delivery.INPUTS[2]])
    observation = {
        "checkpoint": "authored-continuation-proof",
        "observed_at": "2026-09-30T00:00:00Z",
        "status": "MOCK_TEST_PASSED",
        "scope": "Authored fixture only; complete clause unverified.",
        "component_verification": [{"suite": "authored", "passed": 2}],
        "evidence_paths": ["PRD.md", "absent-authored-proof.json"],
        "remaining_scope": "Actual browser flow remains pending.",
        "formal_study_status": "PENDING_INTEGRATION_FREEZE",
        "human_review_status": "WAITING_EXTERNAL",
    }
    tasks["tasks"][0]["week09_learning_observations"] = [observation]
    checks["checks"][0]["week09_learning_observations"] = [observation]
    raw[generate_delivery.INPUTS[0]] = json.dumps(tasks).encode()
    raw[generate_delivery.INPUTS[2]] = json.dumps(checks).encode()
    before = raw.copy()
    outputs, _ = generate_delivery.render(raw)
    task = tasks["tasks"][0]
    names = [
        f"by_owner/{generate_delivery.slug(task['accountable_owner'])}.md",
        f"by_week/course-week-{task['reporting']['suggested_course_week']:02d}.md",
        "acceptance.md",
    ]
    for name in names:
        text = outputs[name].decode()
        assert "authored-continuation-proof" in text
        assert "PENDING_INTEGRATION_FREEZE" in text
        assert "Actual browser flow remains pending." in text
        assert "absent-authored-proof.json` (path absent)" in text
        assert "do not replace the original clause or establish formal completion" in text
    assert raw == before
    assert f"- Current status: `{task['status']}`" in outputs[names[0]].decode()
