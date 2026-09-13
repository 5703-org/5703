"""Backend-facing service that converts DenseRetriever output into one DTO."""

from __future__ import annotations

from dense_retriever import DenseRetriever


class RetrievalService:
    """Stable interface used by the backend and later Prompt Builder."""

    def __init__(self, retriever: DenseRetriever) -> None:
        self.retriever = retriever

    def search(self, question_id: str, question: str, top_k: int = 5) -> dict:
        result = self.retriever.retrieve(question, top_k)
        return {
            "question_id": question_id,
            "question": question,
            "retrieval": {
                "variant": result["variant"],
                "corpus_version": result["corpus_version"],
                "top_k": result["top_k"],
                "latency_ms": result["latency_ms"],
            },
            "evidence": [
                {
                    "chunk_id": item["chunk_id"],
                    "rank": item["rank"],
                    "score": item["score"],
                    "text": item["text"],
                    "citation": {
                        "document": item["document"],
                        "chapter": item["chapter"],
                        "page": item["page"],
                        "text_hash": item["text_hash"],
                    },
                }
                for item in result["evidence"]
            ],
        }
