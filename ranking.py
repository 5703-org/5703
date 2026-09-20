"""Ranking components for the controlled R0--R3 retrieval experiment.

R1 uses BM25, R2 combines Dense and BM25 rankings with reciprocal-rank
fusion (RRF), and R3 reranks up to 20 fused candidates with a pinned MiniLM
Cross-Encoder.  Each returned row keeps its source metadata.
"""

from __future__ import annotations

from collections import Counter
import math
import re
import time
from typing import Iterable, Sequence


MINILM_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
MAX_RERANK_CANDIDATES = 20


def _tokens(text: str) -> list[str]:
    """Return simple lowercase tokens for the English textbook corpus."""
    return re.findall(r"[a-z0-9]+", text.casefold())


def bm25(
    query: str,
    chunks: Sequence[dict],
    top_k: int = 5,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[dict]:
    """Rank source-linked chunks with BM25."""
    if not query.strip():
        raise ValueError("query must not be blank")
    if top_k < 1 or k1 <= 0 or not 0 <= b <= 1:
        raise ValueError("top_k and k1 must be positive, and b must be in [0, 1]")
    if any("chunk_id" not in row or "text" not in row for row in chunks):
        raise ValueError("every chunk requires chunk_id and text")
    if not chunks:
        return []

    term_counts = [Counter(_tokens(row["text"])) for row in chunks]
    lengths = [sum(counts.values()) for counts in term_counts]
    average_length = sum(lengths) / len(lengths)
    query_terms = set(_tokens(query))
    document_frequency = {
        term: sum(term in counts for counts in term_counts)
        for term in query_terms
    }

    ranked = []
    for row, counts, length in zip(chunks, term_counts, lengths):
        score = 0.0
        for term in query_terms:
            frequency = counts.get(term, 0)
            if frequency == 0:
                continue
            frequency_in_corpus = document_frequency[term]
            idf = math.log(
                1 + (len(chunks) - frequency_in_corpus + 0.5)
                / (frequency_in_corpus + 0.5)
            )
            denominator = frequency + k1 * (
                1 - b + b * length / average_length
            )
            score += idf * frequency * (k1 + 1) / denominator

        ranked.append({**row, "score": score, "score_type": "bm25"})

    ranked.sort(key=lambda row: (-row["score"], str(row["chunk_id"])))
    return [
        {**row, "rank": rank}
        for rank, row in enumerate(ranked[:top_k], start=1)
    ]


def reciprocal_rank_fusion(
    rankings: Iterable[Sequence[dict]],
    top_k: int = 20,
    rrf_k: int = 60,
) -> list[dict]:
    """Fuse Dense and BM25 rankings without mixing incomparable scores."""
    if top_k < 1 or rrf_k < 1:
        raise ValueError("top_k and rrf_k must be positive")

    rows_by_id: dict[str, dict] = {}
    scores: Counter = Counter()
    methods: dict[str, list[dict]] = {}

    for ranking in rankings:
        seen = set()
        for position, row in enumerate(ranking, start=1):
            chunk_id = str(row["chunk_id"])
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            rows_by_id.setdefault(chunk_id, row)
            scores[chunk_id] += 1.0 / (rrf_k + position)
            methods.setdefault(chunk_id, []).append(
                {
                    "score_type": row.get("score_type", "unknown"),
                    "rank": int(row.get("rank", position)),
                }
            )

    ordered_ids = sorted(scores, key=lambda cid: (-scores[cid], cid))[:top_k]
    return [
        {
            **rows_by_id[chunk_id],
            "rank": rank,
            "score": float(scores[chunk_id]),
            "score_type": "rrf",
            "fusion_inputs": methods[chunk_id],
            "rrf_k": rrf_k,
        }
        for rank, chunk_id in enumerate(ordered_ids, start=1)
    ]


class MiniLMCrossEncoderReranker:
    """Rerank at most 20 candidates using a pinned MiniLM checkpoint."""

    def __init__(
        self,
        revision: str,
        model_name: str = MINILM_MODEL,
        device: str = "cpu",
        cache_folder: str | None = None,
    ) -> None:
        if not revision or revision in {"main", "latest"}:
            raise ValueError("a pinned MiniLM revision or commit hash is required")
        if device not in {"cpu", "cuda", "cuda:0"}:
            raise ValueError("device must be cpu, cuda, or cuda:0")

        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "Install sentence-transformers before using MiniLM reranking"
            ) from exc

        options = {"device": device}
        if cache_folder:
            options["cache_folder"] = cache_folder

        self.model = CrossEncoder(model_name, revision=revision, **options)
        self.model_name = model_name
        self.revision = revision
        self.device = device

    def rerank(
        self,
        query: str,
        candidates: Sequence[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """Score query-passage pairs and keep source fields unchanged."""
        if not query.strip():
            raise ValueError("query must not be blank")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if any("chunk_id" not in row or "text" not in row for row in candidates):
            raise ValueError("every candidate requires chunk_id and text")

        selected = list(candidates[:MAX_RERANK_CANDIDATES])
        if not selected:
            return []

        tokenizer = self.model.tokenizer
        token_limit = self.model.max_length or tokenizer.model_max_length
        token_counts = [
            len(tokenizer.encode(query, row["text"], add_special_tokens=True))
            for row in selected
        ]
        if any(count > token_limit for count in token_counts):
            raise ValueError("a query-passage pair exceeds the MiniLM token limit")

        started = time.perf_counter()
        scores = self.model.predict(
            [(query, row["text"]) for row in selected],
            show_progress_bar=False,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 3)

        if len(scores) != len(selected):
            raise RuntimeError("MiniLM returned an unexpected number of scores")
        if any(not math.isfinite(float(score)) for score in scores):
            raise RuntimeError("MiniLM returned a non-finite score")

        ranked = [
            {
                **row,
                "score": float(score),
                "score_type": "cross_encoder",
                "reranker_model": self.model_name,
                "reranker_revision": self.revision,
                "reranker_device": self.device,
                "reranker_candidate_count": len(selected),
                "rerank_latency_ms": latency_ms,
                "input_tokens": token_count,
                "input_truncated": False,
            }
            for row, score, token_count in zip(selected, scores, token_counts)
        ]
        ranked.sort(key=lambda row: (-row["score"], str(row["chunk_id"])))

        return [
            {**row, "rank": rank}
            for rank, row in enumerate(ranked[:top_k], start=1)
        ]

