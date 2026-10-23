"""Portable defaults can change without changing the source installation."""

from copy import deepcopy

import pytest

from scripts.release.corpus_bundle import select_export_release


def release_rows():
    return [
        {"id": "old", "state": "active", "manifest": {"chunk_ids": ["a"]}},
        {"id": "new", "state": "validated", "manifest": {"chunk_ids": ["b", "c"]}},
        {"id": "history", "state": "retired", "manifest": {"chunk_ids": ["d"]}},
    ]


def test_explicit_default_retains_history_and_source_state():
    rows = release_rows()
    before = deepcopy(rows)
    selected, exported = select_export_release(rows, "old", "new")
    assert selected == "new"
    assert [(r["id"], r["state"]) for r in exported] == [
        ("old", "retired"),
        ("new", "active"),
        ("history", "retired"),
    ]
    assert [r["manifest"] for r in exported] == [r["manifest"] for r in before]
    exported[1]["manifest"]["chunk_ids"].append("local-only")
    assert rows == before


def test_omitted_option_preserves_existing_default():
    rows = release_rows()
    selected, exported = select_export_release(rows, "old")
    assert selected == "old"
    assert exported == rows
    assert exported is not rows


def test_preserved_old_release_can_be_selected_for_rollback_bundle():
    rows = release_rows()
    rows[0]["state"] = "retired"
    rows[1]["state"] = "active"
    selected, exported = select_export_release(rows, "new", "old")
    assert selected == "old"
    assert exported[0]["state"] == "active"
    assert exported[1]["state"] == "retired"
    assert rows[1]["state"] == "active"


@pytest.mark.parametrize("state", ["building", "failed", "draft", "invalid", "withdrawn"])
def test_unvalidated_target_is_not_projected_as_active(state):
    rows = release_rows()
    rows[1]["state"] = state
    before = deepcopy(rows)
    with pytest.raises(ValueError, match="not validated"):
        select_export_release(rows, "old", "new")
    assert rows == before


@pytest.mark.parametrize("requested", ["absent", "", "foreign-private-release"])
def test_missing_target_does_not_silently_fall_back(requested):
    rows = release_rows()
    with pytest.raises(ValueError, match="not an exported"):
        select_export_release(rows, "old", requested)
    assert rows == release_rows()


def test_missing_default_fails_without_an_explicit_selection():
    with pytest.raises(ValueError, match="not an exported"):
        select_export_release(release_rows(), "unavailable")
