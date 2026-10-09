"""Offline shared-tokenizer/prediction races; no learned model or provider call."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from queue import Queue
import sys
from threading import Barrier, Event, Lock, Thread
from types import SimpleNamespace

import pytest

from retrieval.ranking import CrossEncoderReranker


class MutableTokenizer:
    model_max_length = 64

    def __init__(self, owner):
        self.owner = owner

    def encode(self, query, text, add_special_tokens=True):
        with self.owner.state_lock:
            if self.owner.prediction_active:
                self.owner.overlapping_tokenization.set()
                raise RuntimeError("Controlled shared-tokenizer overlap")
            if self.owner.fail_once == "tokenizer":
                self.owner.fail_once = None
                raise RuntimeError("Controlled tokenization failure")
            if self.owner.fail_once == "window":
                self.owner.fail_once = None
                return list(range(self.model_max_length + 1))
        return [1, 2, 3]


class ObservableCrossEncoder:
    def __init__(self, model, revision, **options):
        self.identity = model, revision, options
        self.max_length = None
        self.state_lock = Lock()
        self.tokenizer = MutableTokenizer(self)
        self.prediction_active = False
        self.prediction_entered = Event()
        self.release_prediction = Event()
        self.overlapping_tokenization = Event()
        self.block_first_prediction = False
        self.call_count = 0
        self.fail_once = None
        self.independent_barrier = None

    def predict(self, pairs):
        with self.state_lock:
            if self.prediction_active:
                raise RuntimeError("Controlled concurrent prediction")
            self.prediction_active = True
            self.call_count += 1
            call = self.call_count
        try:
            self.prediction_entered.set()
            if self.block_first_prediction and call == 1:
                assert self.release_prediction.wait(3), "Release controlled prediction"
            if self.independent_barrier is not None:
                self.independent_barrier.wait(timeout=3)
            if self.fail_once == "predict":
                self.fail_once = None
                raise RuntimeError("Controlled prediction failure")
            if self.fail_once == "score_count":
                self.fail_once = None
                return []
            if self.fail_once == "nonfinite":
                self.fail_once = None
                return [float("nan")] * len(pairs)
            return [float(len(text)) for _query, text in pairs]
        finally:
            with self.state_lock:
                self.prediction_active = False


class CpuStyleReranker(CrossEncoderReranker):
    """Match the existing CPU adapter's independent constructor boundary."""

    def __init__(self, model, revision, **options):
        self.model = ObservableCrossEncoder(model, revision, **options)
        self.revision, self.model_name = revision, model


@pytest.fixture
def port_factory(monkeypatch):
    # Import isolation supplies the exact dependency boundary without loading
    # sentence-transformers, Torch, tokenizer weights or any model cache.
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(CrossEncoder=ObservableCrossEncoder),
    )

    def create(kind=CrossEncoderReranker, device="cpu"):
        return kind(
            "cross-encoder/ms-marco-MiniLM-L6-v2",
            revision="233902d25c440f23af6f7d6e94d2946bac0bee0a",
            device=device,
            cache_folder="local-only-cache",
        )

    return create


ROWS = [
    {"chunk_id": "z", "text": "long", "source_title": "Official source Z"},
    {"chunk_id": "a", "text": "long", "source_title": "Official source A"},
    {"chunk_id": "b", "text": "x", "source_title": "Official source B"},
]


@pytest.mark.parametrize("kind", [CrossEncoderReranker, CpuStyleReranker])
def test_shared_prediction_keeps_other_request_out_of_mutable_tokenizer(port_factory, kind):
    port = port_factory(kind)
    original = deepcopy(ROWS)
    port.model.block_first_prediction = True
    second_started = Event()

    def second_request():
        second_started.set()
        return port.rerank("Second public question", ROWS, k=3)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(port.rerank, "First public question", ROWS, 3)
        assert port.model.prediction_entered.wait(3)
        second = pool.submit(second_request)
        try:
            assert second_started.wait(3)
            # The controlled first prediction is still active. The other
            # request must not mutate the same tokenizer before it finishes.
            assert not port.model.overlapping_tokenization.wait(0.2)
        finally:
            port.model.release_prediction.set()
        results = [first.result(timeout=3), second.result(timeout=3)]
    assert port.model.call_count == 2
    assert [row["chunk_id"] for row in results[0]] == ["a", "z", "b"]
    assert [row["chunk_id"] for row in results[1]] == ["a", "z", "b"]
    assert not port.model.overlapping_tokenization.is_set()
    assert ROWS == original


def test_different_model_instances_can_predict_at_the_same_time(port_factory):
    first, second = port_factory(), port_factory()
    rendezvous = Barrier(2)
    first.model.independent_barrier = second.model.independent_barrier = rendezvous
    with ThreadPoolExecutor(max_workers=2) as pool:
        left = pool.submit(first.rerank, "First public question", ROWS, 3)
        right = pool.submit(second.rerank, "Second public question", ROWS, 3)
        results = left.result(timeout=4), right.result(timeout=4)
    assert first.model.call_count == second.model.call_count == 1
    assert all([row["chunk_id"] for row in result] == ["a", "z", "b"] for result in results)


@pytest.mark.parametrize(
    "stage,error",
    [
        ("tokenizer", RuntimeError),
        ("window", ValueError),
        ("predict", RuntimeError),
        ("score_count", ValueError),
        ("nonfinite", ValueError),
    ],
)
def test_failed_tokenization_prediction_or_validation_releases_instance(port_factory, stage, error):
    port = port_factory()
    port.model.fail_once = stage
    with pytest.raises(error):
        port.rerank("Public question", ROWS, 3)
    observed = Queue()

    def next_request():
        try:
            observed.put(("passed", port.rerank("Next public question", ROWS, 3)))
        except BaseException as failure:
            observed.put(("failed", failure))

    # A leaked prediction lock must fail promptly, without hanging the test
    # executor's shutdown while a worker remains permanently blocked.
    worker = Thread(target=next_request, daemon=True)
    worker.start()
    worker.join(timeout=3)
    assert not worker.is_alive(), "A failed request retained the model lock"
    status, result = observed.get_nowait()
    assert status == "passed"
    assert [row["chunk_id"] for row in result] == ["a", "z", "b"]


@pytest.mark.parametrize("device", ["cpu", "cuda:0", "mps"])
def test_prediction_serialization_preserves_device_identity_scores_and_source_order(
    port_factory, device
):
    port = port_factory(device=device)
    original = deepcopy(ROWS)
    result = port.rerank("Public question", ROWS, 2)
    assert port.model.identity == (
        "cross-encoder/ms-marco-MiniLM-L6-v2",
        "233902d25c440f23af6f7d6e94d2946bac0bee0a",
        {"device": device, "cache_folder": "local-only-cache"},
    )
    assert [(row["chunk_id"], row["score"]) for row in result] == [("a", 4.0), ("z", 4.0)]
    assert [row["source_title"] for row in result] == ["Official source A", "Official source Z"]
    assert all(row["reranker_revision"] == port.revision for row in result)
    assert all(row["rerank_input"]["tokens"] == 3 for row in result)
    assert all(row["rerank_input"]["truncated"] is False for row in result)
    assert ROWS == original
