"""Exact reference-BM25 statistics, built once for an immutable visible corpus."""

from collections import Counter
from copy import deepcopy
from heapq import nsmallest
import math

from .embedding import tokens

VERSION = "exact_bm25_index_v1"


class LexicalIndex:
    """Preserve the reference tokenizer, operation order and chunk-ID tie rule."""

    def __init__(self, rows, k1=1.5, b=0.75):
        if not math.isfinite(k1) or k1 <= 0 or not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("BM25 requires finite positive k1 and b in [0,1]")
        self.rows = deepcopy(rows)
        if len({r["chunk_id"] for r in rows}) != len(rows):
            raise ValueError("Lexical index requires unique chunk identities")
        counts = [Counter(tokens(r["text"])) for r in rows]
        lengths = [sum(c.values()) for c in counts]
        average = sum(lengths) / len(counts) if counts else 0
        postings = {}
        for i, count in enumerate(counts):
            for word, frequency in count.items():
                postings.setdefault(word, []).append((i, frequency))
        self.weights = {}
        for word, entries in postings.items():
            df = len(entries)
            self.weights[word] = {
                i: math.log(1 + (len(rows) - df + 0.5) / (df + 0.5))
                * frequency
                * (k1 + 1)
                / (frequency + k1 * (1 - b + b * lengths[i] / average))
                for i, frequency in entries
            }

    def search(self, query, k=5):
        if type(k) is not int or k < 1:
            raise ValueError("BM25 requires positive integer k")
        # Query set iteration matches bm25(). Summing per word in this order
        # preserves exact floats, including ties and zero-score rows.
        contributions = [[] for _ in self.rows]
        for word in set(tokens(query)):
            for i, contribution in self.weights.get(word, {}).items():
                contributions[i].append(contribution)
        # Python 3.12+ sum() uses compensated floating-point summation. Match
        # that reference behavior instead of an iterative += accumulator.
        scores = [sum(values) for values in contributions]
        # Accepted extreme k1 values can overflow to NaN, whose comparisons
        # are not a total order. Preserve the reference full sort in that case.
        if any(math.isnan(score) for score in scores):
            selected = sorted(
                range(len(self.rows)), key=lambda i: (-scores[i], self.rows[i]["chunk_id"])
            )[:k]
        else:
            selected = nsmallest(
                k, range(len(self.rows)), key=lambda i: (-scores[i], self.rows[i]["chunk_id"])
            )
        return [
            {**deepcopy(self.rows[i]), "score": scores[i], "score_type": "bm25"} for i in selected
        ]
