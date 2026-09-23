"""Execution-device policy never rewrites the stored corpus identity."""

from types import SimpleNamespace
from unittest.mock import patch
import pytest
from retrieval.runtime import resolve_device, query_execution_config
from retrieval.embedding import make_embedding, _e5_model
from app.core.config import Settings


def hardware(cuda=False, mps=False):
    return SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: cuda),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)),
    )


@pytest.mark.parametrize(
    "cuda,mps,expected", [(False, False, "cpu"), (True, True, "cuda"), (False, True, "mps")]
)
def test_auto_chooses_available_device(cuda, mps, expected):
    assert resolve_device("auto", torch_module=hardware(cuda, mps)) == expected


def test_explicit_cpu_and_strict_unavailable_device():
    assert resolve_device("cpu", torch_module=hardware(True, True)) == "cpu"
    for device in ("cuda", "cuda:0", "mps"):
        with pytest.raises(RuntimeError, match="unavailable"):
            resolve_device(device, torch_module=hardware())
    with pytest.raises(ValueError):
        resolve_device("other", torch_module=hardware())
    with pytest.raises(ValueError):
        Settings(_env_file=None, local_model_device="other")
    assert Settings(_env_file=None).local_model_device == "auto"


def test_cpu_query_preserves_cuda_build_identity_and_cache_separation():
    cfg = {
        "embedding_provider": "e5",
        "embedding_revision": "a" * 40,
        "embedding_device": "cuda",
        "dimension": 384,
    }
    original = dict(cfg)
    _e5_model.cache_clear()
    with patch("retrieval.embedding.E5Embedding") as constructor:
        cpu = make_embedding(cfg, runtime_device="cpu")
        assert constructor.call_args.args[3] == "cpu"
        assert make_embedding(cfg, runtime_device="cpu") is cpu
        make_embedding(cfg)
        assert constructor.call_args.args[3] == "cuda"
        assert constructor.call_count == 2
        assert cfg == original
    _e5_model.cache_clear()
    assert query_execution_config(cfg)["embedding_device"] == "cuda"
    with pytest.raises(ValueError):
        query_execution_config(cfg, "auto")
