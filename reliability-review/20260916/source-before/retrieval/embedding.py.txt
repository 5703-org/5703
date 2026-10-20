"""Normalized fixture embeddings and a configured E5 model port."""

from functools import lru_cache
import hashlib
from threading import RLock
import math
import re
import numbers


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.casefold())


def validate_vector(vector, dimension):
    if type(dimension) is not int or dimension <= 0:
        raise ValueError("Embedding dimension must be a positive integer")
    if any(isinstance(x, bool) or not isinstance(x, numbers.Real) for x in vector):
        raise ValueError("Embedding entries must be numeric and cannot be booleans")
    values = [float(x) for x in vector]
    if len(values) != dimension or not values or any(not math.isfinite(x) for x in values):
        raise ValueError("Wrong-dimensional, empty or nonfinite embedding")
    scale = max(abs(x) for x in values)
    if not scale:
        raise ValueError("A zero vector is not an embedding")
    scaled = [x / scale for x in values]
    norm = math.sqrt(sum(x * x for x in scaled))
    return [x / norm for x in scaled]


class MockEmbedding:
    """A deterministic hashed lexical fixture; never labelled a learned embedding."""

    def __init__(self, dimension=384, revision="mock-hash-v1"):
        if type(dimension) is not int or dimension <= 0:
            raise ValueError("Embedding dimension must be positive")
        self.dimension, self.revision = dimension, revision

    def encode(self, texts, kind="passage"):
        if kind not in ("passage", "query") or any(
            not isinstance(t, str) or not t.strip() for t in texts
        ):
            raise ValueError("Embedding kind and nonblank text are required")
        result = []
        for text in texts:
            vector = [0.0] * self.dimension
            for token in tokens(text):
                digest = hashlib.sha256(token.encode()).digest()
                vector[int.from_bytes(digest[:4], "big") % self.dimension] += 1
            result.append(validate_vector(vector, self.dimension))
        return result


class E5Embedding:
    def __init__(
        self,
        model="intfloat/e5-small-v2",
        revision=None,
        dimension=384,
        device=None,
        cache_folder=None,
    ):
        if not revision or revision in ("main", "latest"):
            raise ValueError("A pinned embedding checkpoint revision is required")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional model dependencies before selecting E5"
            ) from exc
        if device is not None and device not in ("cpu", "cuda", "cuda:0"):
            raise ValueError("Embedding device must explicitly select cpu, cuda or cuda:0")
        options = {}
        if device is not None:
            options["device"] = device
        if cache_folder is not None:
            options["cache_folder"] = cache_folder
        self.model = SentenceTransformer(model, revision=revision, **options)
        self.dimension, self.revision = dimension, revision
        if self.model.get_sentence_embedding_dimension() != dimension:
            raise ValueError("Configured dimension differs from the pinned model dimension")
        self.tokenizer_revision = revision

    def count_input(self, text):
        return len(self.model.tokenizer.encode(text, add_special_tokens=True))

    def encode(self, texts, kind="passage"):
        if kind not in ("passage", "query") or any(
            not isinstance(t, str) or not t.strip() for t in texts
        ):
            raise ValueError("Embedding kind and nonblank text are required")
        inputs = [("query: " if kind == "query" else "passage: ") + t for t in texts]
        if any(self.count_input(t) > self.model.max_seq_length for t in inputs):
            raise ValueError(
                "Embedding input exceeds the actual tokenizer window; no silent truncation"
            )
        vectors = self.model.encode(inputs, normalize_embeddings=True)
        if len(vectors) != len(texts):
            raise ValueError("Embedding model returned an inconsistent batch count")
        return [validate_vector(v, self.dimension) for v in vectors]


# Cache model instances only. Query/passage outputs and corpus rows are never cached.
# Serialize cache lookup plus construction: functools.lru_cache alone can load
# duplicate models when concurrent first callers miss the same key.
E5_MODEL_CACHE_SIZE = 2
_E5_MODEL_LOCK = RLock()


@lru_cache(maxsize=E5_MODEL_CACHE_SIZE)
def _e5_model(model, revision, dimension, device, cache_folder):
    return E5Embedding(model, revision, dimension, device, cache_folder)


def make_embedding(config):
    if config.get("embedding_provider", "mock") == "mock":
        return MockEmbedding(
            config.get("dimension", 384), config.get("embedding_revision", "mock-hash-v1")
        )
    if config.get("embedding_provider") == "e5":
        with _E5_MODEL_LOCK:
            return _e5_model(
                config.get("embedding_model", "intfloat/e5-small-v2"),
                config.get("embedding_revision"),
                config.get("dimension", 384),
                config.get("embedding_device"),
                config.get("embedding_cache_folder"),
            )
    raise ValueError("Unsupported embedding adapter")
