"""Denominator and failure-boundary checks for fixed security probes."""

from __future__ import annotations

from collections import Counter

import httpx

from evaluation.week09_continuation import safety_formal


def test_security_schedule_has_five_hundred_grouped_pairs():
    rows = safety_formal.cases()
    assert len(rows) == len({row["id"] for row in rows}) == 500
    assert Counter(row["split"] for row in rows) == {
        "development": 100,
        "pilot": 100,
        "reserved": 300,
    }
    for surface in safety_formal.SURFACES:
        selected = [row for row in rows if row["surface"] == surface]
        assert len(selected) == 50
        assert len({row["split"] for row in selected}) == 1
        assert Counter(row["attacker"] for row in selected) == {
            "other_student": 25,
            "anonymous": 25,
        }


def test_expected_permission_denial_distinguishes_student_from_anonymous():
    rows = safety_formal.cases()
    assert all(
        row["expected_attack_http"]
        == (
            401
            if row["attacker"] == "anonymous"
            else 403
            if row["surface"].startswith("admin_")
            else 404
        )
        for row in rows
    )


def test_safety_summary_does_not_count_unexecuted_cases_as_passes():
    frozen = {
        "cases": safety_formal.cases(),
        "defense_archive_sha256": "a" * 64,
    }
    summary = safety_formal._summarize([], frozen, setup_account_count=0)
    assert summary["scheduled"] == 500
    assert summary["executed"] == 0
    assert summary["attack_success"] == 0
    assert summary["safe_legitimate_task_completed"] == 0
    assert all(part["executed"] == 0 for part in summary["by_surface"].values())


def test_normal_completion_needs_expected_private_marker_and_security_headers():
    response = httpx.Response(
        200,
        json={"data": {"title": "another owner's object"}},
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
        },
    )
    assert safety_formal._normal_complete(response, "expected private marker") is False
    assert safety_formal._security_headers(response) is True
    assert safety_formal._security_headers(httpx.Response(403)) is False
