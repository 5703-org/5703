"""Build a reusable FAISS dense-retrieval index from textbook chunks.

Expected input: JSONL with at least ``chunk_id`` and ``text`` in every row.
Optional metadata, such as ``document``, ``chapter`` and ``page``, is kept in
the output metadata file for later evidence citation.

Example:
    python build_dense_index.py \
        --input data/processed/chunks_v1.jsonl \
        --output indexes/dense_index_v1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a FAISS dense vector index from JSONL textbook chunks."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/chunks_v1.jsonl"),
        help="Path to the processed chunks JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("indexes/dense_index_v1"),
        help="Directory in which the FAISS index and metadata will be saved.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Sentence-Transformers embedding model name.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of chunks encoded in one embedding batch.",
    )
    return parser.parse_args()


def load_chunks(path: Path) -> list[dict[str, Any]]:
    """Load and validate chunks while preserving their source metadata."""
    if not path.exists():
        raise FileNotFoundError(f"Chunk file not found: {path}")

    chunks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}."
                ) from error

            if not isinstance(chunk, dict):
                raise ValueError(f"Line {line_number} must contain a JSON object.")

            missing = {"chunk_id", "text"} - set(chunk)
            if missing:
                raise ValueError(
                    f"Line {line_number} is missing required field(s): "
                    f"{', '.join(sorted(missing))}."
                )

            if not str(chunk["text"]).strip():
                raise ValueError(f"Line {line_number} has an empty text field.")

            chunks.append(chunk)

    if not chunks:
        raise ValueError(f"No usable chunks were found in {path}.")

    return chunks


def build_index(
    chunks: list[dict[str, Any]], model_name: str, batch_size: int
) -> faiss.Index:
    """Encode chunks and add normalised embeddings to an inner-product index."""
    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)

    texts = [str(chunk["text"]) for chunk in chunks]
    print(f"Encoding {len(texts)} chunks...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    vectors = np.asarray(embeddings, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise RuntimeError("Unexpected embedding shape returned by the model.")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def save_artifacts(
    index: faiss.Index,
    chunks: list[dict[str, Any]],
    output_dir: Path,
    model_name: str,
) -> None:
    """Save the index, source metadata and reproducibility configuration."""
    output_dir.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(output_dir / "index.faiss"))

    metadata_path = output_dir / "chunks_metadata.jsonl"
    with metadata_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    config = {
        "embedding_model": model_name,
        "index_type": "IndexFlatIP",
        "num_chunks": len(chunks),
        "dimension": index.d,
        "normalise_embeddings": True,
        "required_chunk_fields": ["chunk_id", "text"],
    }
    with (output_dir / "index_config.json").open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def main() -> None:
    args = parse_args()
    chunks = load_chunks(args.input)
    index = build_index(chunks, args.model, args.batch_size)
    save_artifacts(index, chunks, args.output, args.model)

    print("Dense index built successfully.")
    print(f"Indexed chunks: {index.ntotal}")
    print(f"Saved artifacts to: {args.output}")


if __name__ == "__main__":
    main()
