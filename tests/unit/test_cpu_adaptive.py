"""Backends remain explicit and budget fitting cannot consume held-out concepts."""

from copy import deepcopy
import json
from unittest.mock import patch

import pytest

from retrieval.adaptive import choose_budget, fit_policy, verify_group_holdout
from retrieval.chat import load_policy, rerank_candidates, validate_policy
from retrieval.cpu_backend import file_hash, torch_runtime, validate_artifact, validate_runtime
from retrieval.relevance import freeze_policy, screen


def rows():
    return [
        {"chunk_id": str(i), "text": "A ribosome is a cellular structure.", "score": 1 / (i + 1)}
        for i in range(20)
    ]


def fitted():
    return fit_policy(
        [
            {
                "split": "development",
                "group": "ribosome",
                "query": "What is a ribosome?",
                "candidates": rows(),
                "reference_ids": ["0", "1", "2", "3", "4"],
            }
        ]
    )


def policy():
    result = load_policy("configs/retrieval/chat_hybrid_minilm.json")
    result.update(
        version="chat_hybrid_rerank_v2",
        reranker_device="cpu",
        reranker_runtime=torch_runtime(),
        adaptive_policy=fitted(),
    )
    return result


def test_fitting_uses_only_development_groups_and_preserves_conservative_queries():
    value = fitted()
    assert choose_budget("What is a ribosome?", rows(), value)[0] == 5
    assert choose_budget("Compare ribosomes and mitochondria.", rows(), value)[0] == 20
    assert choose_budget("What is Kubernetes?", rows(), value)[0] == 20
    assert choose_budget("What is a ribosome?", rows()[:10], value)[0] == 20
    with pytest.raises(ValueError, match="development"):
        fit_policy([{"split": "holdout"}])
    with pytest.raises(ValueError, match="overlap"):
        verify_group_holdout(value, [{"split": "holdout", "group": "ribosome"}])
    verify_group_holdout(value, [{"split": "holdout", "group": "lysosome"}])


def test_shadow_retains_all_candidates_and_experimental_records_removed_ids():
    class Ranker:
        def rerank(self, query, candidates, k):
            return [
                {**item, "score": 10 - i, "score_type": "cross_encoder"}
                for i, item in enumerate(candidates)
            ]

    value = policy()
    original = deepcopy(value)
    with patch("retrieval.cpu_backend.get_cpu_reranker", return_value=Ranker()):
        ranked, trace = rerank_candidates("What is a ribosome?", rows(), value)
        assert len(ranked) == 20
        assert trace["adaptive"]["proposed_budget"] == 5
        assert trace["adaptive"]["executed_budget"] == 20
        assert value == original
        value["adaptive_policy"]["mode"] = "experimental"
        ranked, trace = rerank_candidates("What is a ribosome?", rows(), value)
        assert len(ranked) == 5
        assert trace["adaptive"]["excluded_candidate_ids"] == [str(i) for i in range(5, 20)]
    with pytest.raises(ValueError, match="CPU"):
        rerank_candidates("question", rows(), value, runtime_device="cuda")


def test_int8_does_not_inherit_torch_relevance_threshold():
    value = policy()
    assert freeze_policy(value)["minimum_logit"] == -4.0
    for backend in ("onnx_fp32", "onnx_int8"):
        value["reranker_runtime"]["backend"] = backend
        gate = freeze_policy(value)
        assert gate["minimum_logit"] is None
        assert gate["calibration"] is None
        assert screen("a question", [], gate)[0] == []


def test_backend_manifest_hash_and_model_binding(tmp_path):
    graph = tmp_path / "model.onnx"
    graph.write_bytes(b"unit fixture, not a model")
    manifest = {
        "model": "model",
        "revision": "a" * 40,
        "activation": "identity",
        "files": {"model.onnx": file_hash(graph)},
        "backends": {"onnx_int8": "model.onnx"},
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    runtime = torch_runtime() | {
        "backend": "onnx_int8",
        "artifact_path": str(path),
        "artifact_sha256": file_hash(path),
    }
    assert validate_artifact(runtime, "model", "a" * 40)[1] == graph
    with pytest.raises(ValueError, match="model identity"):
        validate_artifact(runtime, "wrong", "a" * 40)
    graph.write_bytes(b"changed")
    with pytest.raises(ValueError, match="content changed"):
        validate_artifact(runtime, "model", "a" * 40)
    path.write_text("{}")
    with pytest.raises(ValueError, match="manifest changed"):
        validate_artifact(runtime, "model", "a" * 40)


@pytest.mark.parametrize(
    "field,value",
    [
        ("threads", True),
        ("threads", 0),
        ("batch_size", 21),
        ("backend", "auto"),
        ("artifact_path", "unexpected"),
    ],
)
def test_invalid_runtime_is_not_a_silent_fallback(field, value):
    runtime = torch_runtime()
    runtime[field] = value
    with pytest.raises(ValueError):
        validate_runtime(runtime)


def test_legacy_policy_and_frozen_copy_are_preserved():
    legacy = load_policy("configs/retrieval/chat_hybrid_minilm.json")
    assert validate_policy(legacy) == legacy
    value = policy()
    frozen = validate_policy(value)
    value["reranker_runtime"]["threads"] = 3
    assert frozen["reranker_runtime"]["threads"] == 2
