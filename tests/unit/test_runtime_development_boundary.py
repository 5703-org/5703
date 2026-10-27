"""Formal archives cannot synthesize results when developer code is absent."""

import ast
from pathlib import Path

import pytest

from generation import development_boundary as boundary
from generation.adapters import LLMAdapter, test_connection as connection_probe
from generation.types import ModelConfig
from retrieval.embedding import make_embedding
from scripts.release.runtime_manifest import audit, runtime_member


@pytest.fixture
def without_development(monkeypatch):
    monkeypatch.setattr(boundary, "find_spec", lambda name: None)


@pytest.mark.parametrize("operation", ["structured", "basic", "connection"])
def test_missing_development_fails_without_submission(without_development, operation):
    config = ModelConfig()
    adapter = LLMAdapter(config)
    if operation == "structured":
        result = adapter.generate([], response_schema={}, response_schema_name="boundary")
    elif operation == "basic":
        result = adapter.generate_basic([])
    else:
        result = connection_probe(config)
    assert result.error["code"] == "MODEL_UNAVAILABLE"
    assert result.request_submitted is False
    assert not result.raw_text


def test_missing_development_cannot_create_hash_vectors(without_development):
    with pytest.raises(boundary.DevelopmentUnavailable):
        make_embedding({"embedding_provider": "mock"})


@pytest.mark.parametrize("component", ["answers", "embeddings", "seeding", "memory"])
def test_missing_development_has_no_silent_substitute(without_development, component):
    with pytest.raises(boundary.DevelopmentUnavailable):
        boundary.load(component)


def test_no_arbitrary_component_import():
    with pytest.raises(ValueError):
        boundary.load("os")


def test_formal_runtime_does_not_include_development_tree():
    root = Path(__file__).resolve().parents[2]
    result = audit(root)
    assert result["blockers"] == []
    assert not any("development_support" in item["path"] for item in result["files"])
    assert not runtime_member(Path("development_support/answers.py"))


@pytest.mark.parametrize(
    "path,symbols",
    [
        (
            "generation/adapters.py",
            {"mock_payload", "mock_terms", "mock_inflections", "mock_excerpt"},
        ),
        ("retrieval/embedding.py", {"MockEmbedding"}),
        ("backend/app/cli.py", {"seed", "initial_admin_password_matches"}),
    ],
)
def test_authored_implementations_not_defined_in_runtime(path, symbols):
    root = Path(__file__).resolve().parents[2]
    tree = ast.parse((root / path).read_text(encoding="utf-8"))
    assert not any(
        isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in symbols for n in ast.walk(tree)
    )
