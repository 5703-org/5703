"""Bounded ranking windows retain every source character and the full query."""

from copy import deepcopy
from threading import RLock
from types import SimpleNamespace
import math
import pytest
from retrieval import chat
from retrieval.pair_windows import VERSION, rerank_complete_text


def test_windowed_maximum_does_not_claim_the_original_calibration():
    from retrieval import relevance

    value = policy()
    value.update(reranker_model=relevance.MODEL, reranker_revision=relevance.REVISION)
    windowed = relevance.freeze_policy(value)
    assert windowed["minimum_logit"] == -4.0
    assert windowed["calibration"] == "transferred_threshold_not_recalibrated_for_window_maximum_v1"
    assert relevance.screen("diffusion", [], windowed)[0] == []
    value.pop("pair_window_policy")
    value["version"] = chat.POLICY_VERSION
    assert (
        relevance.freeze_policy(value)["calibration"] == "20260916-openstax-development-provisional"
    )


class Tokens:
    model_max_length = 80

    def encode(self, query, text, add_special_tokens=True):
        return list(range(len(query) + len(text) + 3))


def ranker(*, scores=None):
    calls = []

    def predict(pairs):
        assert all(len(Tokens().encode(q, t)) <= 80 for q, t in pairs)
        calls.extend(pairs)
        return scores if scores is not None else [float("gold" in t) for q, t in pairs]

    value = SimpleNamespace(
        model=SimpleNamespace(max_length=80, tokenizer=Tokens(), predict=predict),
        _prediction_lock=RLock(),
        revision="a" * 40,
        model_name="fixture",
        calls=calls,
    )
    return value


def test_complete_source_and_query_are_preserved_with_tail_relevance():
    model = ranker()
    rows = [
        {"chunk_id": "a", "text": "x" * 150 + "gold", "text_hash": "immutable"},
        {"chunk_id": "b", "text": "short unrelated"},
    ]
    before = deepcopy(rows)
    result = rerank_complete_text(model, "query", rows, k=2, policy=VERSION)
    assert rows == before and result[0]["chunk_id"] == "a"
    assert result[0]["text"] == rows[0]["text"]
    for row in result:
        windows = row["rerank_input"]["windows"]
        assert 1 <= len(windows) <= 4
        assert windows[0]["start"] == 0 and windows[-1]["end"] == len(row["text"])
        assert all(a["end"] >= b["start"] for a, b in zip(windows, windows[1:]))
        assert row["rerank_input"]["full_text_covered"]
        assert row["rerank_input"]["truncated"] is False
        assert row["score"] == max(w["score"] for w in windows)
    assert all(q == "query" for q, t in model.calls)


@pytest.mark.parametrize("query,text", [("q" * 78, "x"), ("query", "x" * 500)])
def test_budget_excess_fails_before_any_prediction_without_partial_ranking(query, text):
    model = ranker()
    with pytest.raises(ValueError):
        rerank_complete_text(model, query, [{"chunk_id": "a", "text": text}], k=1, policy=VERSION)
    assert model.calls == []


@pytest.mark.parametrize("scores", [[], [math.nan], [math.inf]])
def test_corrupt_model_scores_never_publish(scores):
    with pytest.raises(ValueError, match="wrong-count or nonfinite"):
        rerank_complete_text(
            ranker(scores=scores),
            "query",
            [{"chunk_id": "a", "text": "short"}],
            k=1,
            policy=VERSION,
        )


def policy():
    return dict(
        version=chat.WINDOWED_VERSION,
        retriever="R2",
        candidate_count=20,
        reranker_model="fixture",
        reranker_revision="a" * 40,
        reranker_device="cpu",
        reranker_cache_folder="cache",
        pair_window_policy=VERSION,
    )


def test_frozen_dispatch_retains_membership_and_source_metadata(monkeypatch):
    value = policy()
    model = ranker()
    monkeypatch.setattr(chat, "_reranker", lambda *a: model)
    rows = [{"chunk_id": "a", "text": "x" * 150 + "gold", "pages": [4], "text_hash": "fixed"}]
    ranked, trace = chat.rerank_candidates("query", rows, value)
    assert ranked[0]["text"] == rows[0]["text"] and ranked[0]["pages"] == [4]
    assert trace["candidate_ids"] == trace["ranked_ids"] == ["a"]
    assert trace["policy"] == value
    assert chat.validate_policy(value) == value


@pytest.mark.parametrize(
    "change",
    [
        {"pair_window_policy": "unknown"},
        {"pair_window_policy": True},
        {"adaptive_policy": None},
        {"version": chat.POLICY_VERSION},
    ],
)
def test_unknown_or_mixed_policy_rejected(change):
    value = {**policy(), **change}
    with pytest.raises(ValueError):
        chat.validate_policy(value)


def test_legacy_dispatch_still_uses_whole_pair_reranker(monkeypatch):
    value = policy()
    value["version"] = chat.POLICY_VERSION
    value.pop("pair_window_policy")
    calls = []

    def legacy(query, rows, k):
        calls.append((query, rows, k))
        return deepcopy(rows)

    monkeypatch.setattr(chat, "_reranker", lambda *a: SimpleNamespace(rerank=legacy))
    rows = [{"chunk_id": "a", "text": "unchanged"}]
    result, trace = chat.rerank_candidates("query", rows, value)
    assert result == rows and calls == [("query", rows, 1)]
    assert "pair_window_policy" not in trace["policy"]
