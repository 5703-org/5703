"""Bounded, owner-scoped query vectors; no answer or retrieved-text reuse."""

from collections import OrderedDict
import hashlib
import json
from threading import RLock
import time

from .embedding import make_embedding, validate_vector

VERSION = "query_vector_cache_v1"
_LOCK = RLock()
_ITEMS = OrderedDict()


def encode_query(config, query, *, runtime_device=None, scope=None, enabled=False):
    options = {"runtime_device": runtime_device} if runtime_device is not None else {}
    if not enabled or not scope or config.get("embedding_provider") != "e5":
        vectors = make_embedding(config, **options).encode([query], kind="query")
        if len(vectors) != 1:
            raise ValueError("Query embedding count is invalid")
        return validate_vector(vectors[0], config["dimension"]), False
    # Include the complete frozen identity/preprocessing and actual device.
    # Retain neither plaintext owner identifiers nor plaintext user questions.
    key = hashlib.sha256(
        json.dumps([VERSION, scope, config, runtime_device, query], sort_keys=True).encode()
    ).hexdigest()
    with _LOCK:
        item = _ITEMS.get(key)
        now = time.monotonic()
        if item and now - item[0] < 300:
            _ITEMS.move_to_end(key)
            return list(item[1]), True
        vectors = make_embedding(config, **options).encode([query], kind="query")
        if len(vectors) != 1:
            raise ValueError("Query embedding count is invalid")
        vector = validate_vector(vectors[0], config["dimension"])
        _ITEMS[key] = (now, tuple(vector))
        _ITEMS.move_to_end(key)
        while len(_ITEMS) > 256:
            _ITEMS.popitem(last=False)
        return vector, False
