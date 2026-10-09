"""Synthetic loader tests run without any private study inventory."""

import hashlib
import importlib
import json
from pathlib import Path

import pytest

from evaluation.enhancement import formal_catalogue
from evaluation.reliability import catalogue


@pytest.fixture(params=["formal", "reliability"])
def fixture_catalogue(request, tmp_path, monkeypatch):
    if request.param == "formal":
        module, function = formal_catalogue, formal_catalogue.formal_tasks
        payload = {
            "schema": "enhancement_formal_catalogue_private_v1",
            "tasks": [
                {"id": f"synthetic-{i}", "critical_answer": "Authored fixture"} for i in range(60)
            ],
        }
    else:
        module, function = catalogue, catalogue.inventory
        payload = {
            "schema": "reliability_catalogue_private_v1",
            "catalogue": {
                "cases": [{"id": f"synthetic-{i}"} for i in range(120)],
                "topics": [[f"topic-{i}", "Authored fixture"] for i in range(30)],
                "sections": {"fixture": ["1"]},
                "outside": ["Authored fixture"],
            },
        }
    source = tmp_path / "catalogue.json"
    raw = json.dumps(payload).encode()
    source.write_bytes(raw)
    monkeypatch.setattr(module, "CATALOGUE_PATH", source)
    monkeypatch.setattr(module, "CATALOGUE_SHA256", hashlib.sha256(raw).hexdigest())
    return module, function, source, payload


def test_lazy_catalogue_returns_fresh_exact_fixture(fixture_catalogue):
    module, function, source, payload = fixture_catalogue
    expected = payload["tasks" if module is formal_catalogue else "catalogue"]
    first = function()
    assert first == expected
    assert function(source) == expected
    first.clear()
    assert function() == expected
    if module is catalogue:
        assert catalogue.cases() == expected["cases"]
        assert catalogue.TOPICS == [tuple(row) for row in expected["topics"]]
        assert catalogue.SECTIONS == expected["sections"]


def test_missing_private_catalogue_fails_without_substitute(fixture_catalogue):
    _, function, source, _ = fixture_catalogue
    with pytest.raises(ValueError, match="Restore the private"):
        function(source.with_name("not-distributed.json"))


def test_private_catalogue_modified_reference_is_rejected(fixture_catalogue):
    _, function, source, payload = fixture_catalogue
    payload["tampered"] = "changed private reference"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="preserved source identity"):
        function()


@pytest.mark.parametrize("change", ["schema", "duplicate", "count"])
def test_private_catalogue_structure_checked_independently_of_hash(
    fixture_catalogue, change, monkeypatch
):
    module, function, source, payload = fixture_catalogue
    rows = payload["tasks"] if module is formal_catalogue else payload["catalogue"]["cases"]
    if change == "schema":
        payload["schema"] = "unknown"
    elif change == "duplicate":
        rows[-1]["id"] = rows[0]["id"]
    else:
        rows.pop()
    raw = json.dumps(payload).encode()
    source.write_bytes(raw)
    monkeypatch.setattr(module, "CATALOGUE_SHA256", hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError):
        function()


def test_imports_do_not_read_private_catalogues(monkeypatch):
    read = Path.read_bytes

    def blocked(path):
        if "private" in path.parts:
            pytest.fail("Public imports read evaluator-private material")
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", blocked)
    importlib.reload(formal_catalogue)
    importlib.reload(catalogue)
    importlib.reload(importlib.import_module("scripts.verify.week08_reliability"))
    importlib.reload(importlib.import_module("scripts.verify.enhancement"))
