"""First-use serialization, shared caching, and fail-closed tokenizer errors."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import sys, threading
import pytest
from generation import token_counting as counting


@pytest.fixture(autouse=True)
def clean_cache():
    counting._huggingface.cache_clear()
    yield
    counting._huggingface.cache_clear()


def test_concurrent_first_use_constructs_one_cached_tokenizer(monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    start = threading.Barrier(3)
    calls = []
    sentinel = object()

    def load(*args, **kwargs):
        calls.append(kwargs)
        entered.set()
        assert release.wait(3)
        return sentinel

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=load)),
    )

    def call():
        start.wait(3)
        return counting._huggingface("", "authored/local-tokenizer", "pinned-fixture-revision")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(call)
        second = pool.submit(call)
        start.wait(3)
        try:
            assert entered.wait(3)
        finally:
            release.set()
        assert first.result(3) == second.result(3) == (sentinel, {})
    assert len(calls) == 1
    assert calls[0]["local_files_only"] is True and calls[0]["trust_remote_code"] is False


def test_failed_initialization_is_not_cached_or_silently_replaced(monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise ImportError("authored missing dependency")

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=fail)),
    )
    for _ in range(2):
        with pytest.raises(ImportError, match="authored missing dependency"):
            counting._huggingface("", "authored/local-tokenizer", "pinned-fixture-revision")
    assert len(calls) == 2 and counting._huggingface.cache_info().currsize == 0
