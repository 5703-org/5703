"""Offline instance-lifetime checks; these are not learned-model memory measurements."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier, Event, Lock
from time import sleep
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from retrieval import embedding


BASE = {
    "embedding_provider": "e5",
    "embedding_model": "intfloat/e5-small-v2",
    "embedding_revision": "a" * 40,
    "dimension": 2,
    "embedding_device": "cpu",
    "embedding_cache_folder": "local-cache",
}


@pytest.fixture(autouse=True)
def empty_model_cache():
    with embedding._E5_MODEL_LOCK:
        embedding._e5_model.cache_clear()
    yield
    with embedding._E5_MODEL_LOCK:
        embedding._e5_model.cache_clear()


@dataclass
class Port:
    model: str
    revision: str
    dimension: int
    device: str | None
    cache_folder: str | None


def test_same_full_identity_reuses_model_without_changing_constructor_arguments(monkeypatch):
    loads = []

    def load(*args):
        loads.append(args)
        return Port(*args)

    monkeypatch.setattr(embedding, "E5Embedding", load)
    first = embedding.make_embedding(BASE)
    assert embedding.make_embedding(dict(BASE)) is first
    assert loads == [("intfloat/e5-small-v2", "a" * 40, 2, "cpu", "local-cache")]


@pytest.mark.parametrize(
    "change",
    [
        {"embedding_model": "intfloat/e5-base-v2"},
        {"embedding_revision": "b" * 40},
        {"dimension": 768},
        {"embedding_device": "cuda"},
        {"embedding_cache_folder": "another-cache"},
    ],
)
def test_each_model_identity_field_prevents_incompatible_reuse(monkeypatch, change):
    monkeypatch.setattr(embedding, "E5Embedding", Port)
    first = embedding.make_embedding(BASE)
    assert embedding.make_embedding({**BASE, **change}) is not first


def test_model_cache_is_bounded_and_lru_reloads_evicted_identity(monkeypatch):
    loads = []

    def load(*args):
        loads.append(args)
        return Port(*args)

    monkeypatch.setattr(embedding, "E5Embedding", load)
    a = embedding.make_embedding(BASE)
    b_config = {**BASE, "embedding_revision": "b" * 40}
    b = embedding.make_embedding(b_config)
    assert embedding.make_embedding(BASE) is a
    embedding.make_embedding({**BASE, "embedding_revision": "c" * 40})
    assert embedding._e5_model.cache_info().currsize == 2
    assert embedding.make_embedding(b_config) is not b
    assert len(loads) == 4
    assert embedding._e5_model.cache_info().currsize == embedding.E5_MODEL_CACHE_SIZE == 2


def test_concurrent_first_requests_do_not_construct_duplicate_models(monkeypatch):
    starts = Barrier(9)
    entered = Event()
    release = Event()
    counter_lock = Lock()
    loads = []

    def load(*args):
        with counter_lock:
            loads.append(args)
        entered.set()
        assert release.wait(3), "Test must release the blocked constructor"
        return Port(*args)

    def ask():
        starts.wait(timeout=3)
        return embedding.make_embedding(BASE)

    monkeypatch.setattr(embedding, "E5Embedding", load)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(ask) for _ in range(8)]
        starts.wait(timeout=3)
        assert entered.wait(3)
        # Keep first load incomplete while other simultaneously started callers
        # reach the cache. An lru_cache without the outer lock loads duplicates.
        sleep(0.05)
        release.set()
        values = [future.result(timeout=3) for future in futures]
    assert len(loads) == 1
    assert all(value is values[0] for value in values)


def test_failed_model_load_is_not_cached_or_replaced_by_mock_or_other_device(monkeypatch):
    loads = []

    def load(*args):
        loads.append(args)
        if len(loads) == 1:
            raise OSError("Recorded checkpoint unavailable")
        return Port(*args)

    monkeypatch.setattr(embedding, "E5Embedding", load)
    with pytest.raises(OSError, match="unavailable"):
        embedding.make_embedding(BASE)
    assert embedding._e5_model.cache_info().currsize == 0
    result = embedding.make_embedding(BASE)
    assert result.device == "cpu" and result.revision == "a" * 40
    assert loads[0] == loads[1]


class Tokenizer:
    def encode(self, text, add_special_tokens=True):
        return list(range(len(text.split()) + (2 if add_special_tokens else 0)))


class RecordingModel:
    loads = []

    def __init__(self, model, revision, **options):
        self.loads.append((model, revision, options))
        self.tokenizer = Tokenizer()
        self.max_seq_length = 12
        self.calls = []
        self.invalid = False

    def get_sentence_embedding_dimension(self):
        return 2

    def encode(self, inputs, normalize_embeddings=True):
        self.calls.append(list(inputs))
        if self.invalid:
            return [[float("nan"), 1.0] for _ in inputs]
        return [[3.0, 4.0] if "light" in text else [4.0, 3.0] for text in inputs]


def test_every_encode_runs_preserving_prefixes_vectors_and_failure_guards():
    RecordingModel.loads = []
    with patch.dict(
        "sys.modules",
        {"sentence_transformers": SimpleNamespace(SentenceTransformer=RecordingModel)},
    ):
        first = embedding.make_embedding(BASE)
        light = first.encode(["light energy"], kind="query")[0]
        again = embedding.make_embedding(dict(BASE))
        assert again is first
        assert again.encode(["light energy"], kind="query")[0] == light
        dark = again.encode(["dark reaction"], kind="passage")[0]
        assert dark != light
        uncached = embedding.E5Embedding(
            BASE["embedding_model"], BASE["embedding_revision"], 2, "cpu", "local-cache"
        )
        assert uncached.encode(["light energy"], kind="query")[0] == light
        assert len(RecordingModel.loads) == 2  # one cached and one explicit reference
        assert first.model.calls == [
            ["query: light energy"],
            ["query: light energy"],
            ["passage: dark reaction"],
        ]
        with pytest.raises(ValueError, match="window"):
            first.encode(["word " * 30])
        with pytest.raises(ValueError, match="nonblank"):
            first.encode([""])
        first.model.invalid = True
        with pytest.raises(ValueError, match="nonfinite"):
            first.encode(["light energy"])


def test_mock_is_not_model_cached_and_bad_revision_stays_a_hard_failure():
    a = embedding.make_embedding({"embedding_provider": "mock", "dimension": 4})
    b = embedding.make_embedding({"embedding_provider": "mock", "dimension": 4})
    assert a is not b
    assert a.encode(["source question"]) == b.encode(["source question"])
    assert embedding._e5_model.cache_info().currsize == 0
    for revision in (None, "main", "latest"):
        with pytest.raises(ValueError, match="pinned"):
            embedding.make_embedding({**BASE, "embedding_revision": revision})
    assert embedding._e5_model.cache_info().currsize == 0
