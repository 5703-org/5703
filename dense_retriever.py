"""Query a FAISS dense-retrieval index and return traceable textbook evidence.

This module loads the files created by ``build_dense_index.py``:
    indexes/dense_index_v1/index.faiss
    indexes/dense_index_v1/chunks_metadata.jsonl

Example:
    python dense_retriever.py --query "What gas do plants absorb?" --top-k 5
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_INDEX_DIR = Path("indexes/dense_index_v1")


class DenseRetriever:
    """Retrieve Top-K textbook chunks using cosine similarity in FAISS."""

    def __init__(
        self,
        index_dir: str | Path = DEFAULT_INDEX_DIR,
        model_name: str | None = None,
    ) -> None:
        self.index_dir = Path(index_dir)
        self.index = self._load_index()
        self.metadata = self._load_metadata()
        self.model_name = model_name or self._load_config().get(
            "embedding_model", DEFAULT_MODEL
        )

        if self.index.ntotal != len(self.metadata):
            raise ValueError(
                "The FAISS index and chunk metadata have different numbers of items."
            )

        print(f"Loading query embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

    def _load_index(self) -> faiss.Index:
        index_path = self.index_dir / "index.faiss"
        if not index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {index_path}. Run build_dense_index.py first."
            )
        return faiss.read_index(str(index_path))

    def _load_metadata(self) -> list[dict[str, Any]]:
        metadata_path = self.index_dir / "chunks_metadata.jsonl"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Chunk metadata not found: {metadata_path}.")

        metadata: list[dict[str, Any]] = []
        with metadata_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    metadata.append(json.loads(line))
        return metadata

    def _load_config(self) -> dict[str, Any]:
        config_path = self.index_dir / "index_config.json"
        if not config_path.exists():
            return {}
        with config_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def retrieve(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Return ranked evidence chunks and the total query retrieval latency."""
        query = query.strip()
        if not query:
            raise ValueError("The query must not be empty.")
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        actual_k = min(top_k, self.index.ntotal)
        start_time = time.perf_counter()

        query_vector = self.model.encode(
            [query],
            normalize_embeddings=True,
        )
        query_vector = np.asarray(query_vector, dtype=np.float32)
        scores, indices = self.index.search(query_vector, actual_k)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        evidence: list[dict[str, Any]] = []

        for rank, (score, index_id) in enumerate(
            zip(scores[0], indices[0]), start=1
        ):
            if index_id < 0:
                continue

            chunk = self.metadata[int(index_id)]
            evidence.append(
                {
                    "rank": rank,
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "score": round(float(score), 6),
                    "document": chunk.get("document", chunk.get("source", "Unknown")),
                    "chapter": chunk.get("chapter", "Unknown"),
                    "page": chunk.get("page", "Unknown"),
                }
            )

        return {
            "query": query,
            "top_k": actual_k,
            "latency_ms": latency_ms,
            "evidence": evidence,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retrieve Top-K textbook chunks from a FAISS dense index."
    )
    parser.add_argument("--query", required=True, help="Question to retrieve evidence for.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to return.")
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help="Directory containing index.faiss and chunks_metadata.jsonl.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional embedding model override; normally read from index_config.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    retriever = DenseRetriever(args.index_dir, args.model)
    result = retriever.retrieve(args.query, args.top_k)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
