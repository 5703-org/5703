"""Versioned, local-only CPU reranking backends with pinned export artifacts."""

from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from threading import RLock
import time

from .ranking import CrossEncoderReranker

VERSION = "cpu_reranker_runtime_v1"
BACKENDS = ("torch", "onnx_fp32", "onnx_int8")
_LOCK = RLock()


def validate_runtime(value):
    fields = {"version", "backend", "threads", "batch_size", "artifact_path", "artifact_sha256"}
    if not isinstance(value, dict) or set(value) != fields or value["version"] != VERSION:
        raise ValueError("CPU reranking requires an exact versioned runtime")
    if value["backend"] not in BACKENDS:
        raise ValueError("Unsupported CPU reranking backend")
    for name, limit in (("threads", 32), ("batch_size", 20)):
        if type(value[name]) is not int or not 1 <= value[name] <= limit:
            raise ValueError(f"CPU reranking {name} must be between 1 and {limit}")
    if value["backend"] == "torch":
        if value["artifact_path"] is not None or value["artifact_sha256"] is not None:
            raise ValueError("PyTorch uses its original pinned checkpoint")
    elif (
        not isinstance(value["artifact_path"], str)
        or not value["artifact_path"].strip()
        or not re.fullmatch(r"[0-9a-f]{64}", value["artifact_sha256"] or "")
    ):
        raise ValueError("ONNX execution requires a frozen local manifest hash")
    return dict(value)


def torch_runtime(threads=2, batch_size=20):
    return validate_runtime(
        dict(
            version=VERSION,
            backend="torch",
            threads=threads,
            batch_size=batch_size,
            artifact_path=None,
            artifact_sha256=None,
        )
    )


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@contextmanager
def torch_threads(count):
    """The application has one durable worker; restore global policy after each call."""
    import torch

    with _LOCK:
        previous = torch.get_num_threads()
        try:
            torch.set_num_threads(count)
            yield
        finally:
            torch.set_num_threads(previous)


def validate_artifact(runtime, model, revision):
    runtime = validate_runtime(runtime)
    manifest_path = Path(runtime["artifact_path"]).resolve()
    if file_hash(manifest_path) != runtime["artifact_sha256"]:
        raise ValueError("CPU reranking artifact manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("model"), manifest.get("revision"), manifest.get("activation")) != (
        model,
        revision,
        "identity",
    ):
        raise ValueError("CPU reranking export does not match its model identity")
    for relative, digest in manifest["files"].items():
        path = (manifest_path.parent / relative).resolve()
        if not path.is_relative_to(manifest_path.parent) or file_hash(path) != digest:
            raise ValueError("CPU reranking artifact content changed")
    filename = manifest["backends"][runtime["backend"]]
    if filename not in manifest["files"]:
        raise ValueError("CPU reranking graph has no frozen file hash")
    return manifest, manifest_path.parent / filename


class _TorchModel:
    def __init__(self, model, runtime):
        self.original = model
        self.tokenizer, self.max_length = model.tokenizer, model.max_length
        self.runtime = runtime

    def predict(self, pairs):
        with torch_threads(self.runtime["threads"]):
            return self.original.predict(
                pairs, batch_size=self.runtime["batch_size"], show_progress_bar=False
            )


class _OnnxModel:
    def __init__(self, snapshot, graph, runtime, window):
        import onnxruntime as ort
        from transformers import AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
        self.max_length = window
        options = ort.SessionOptions()
        options.intra_op_num_threads = runtime["threads"]
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.session = ort.InferenceSession(
            str(graph), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.runtime = runtime

    def predict(self, pairs):
        import numpy as np

        scores = []
        for start in range(0, len(pairs), self.runtime["batch_size"]):
            batch = pairs[start : start + self.runtime["batch_size"]]
            encoded = self.tokenizer(
                [q for q, _ in batch],
                [p for _, p in batch],
                padding=True,
                truncation=False,
                return_tensors="np",
            )
            inputs = {
                item.name: np.asarray(encoded[item.name], dtype=np.int64)
                for item in self.session.get_inputs()
            }
            logits = self.session.run(None, inputs)[0]
            if logits.shape != (len(batch), 1):
                raise ValueError("ONNX reranker must return one raw logit per pair")
            scores.extend(logits[:, 0].tolist())
        return scores


class CpuReranker(CrossEncoderReranker):
    def __init__(self, snapshot, model, revision, runtime):
        self.runtime = validate_runtime(runtime)
        self.revision, self.model_name = revision, model
        started = time.perf_counter()
        if runtime["backend"] == "torch":
            original = CrossEncoderReranker(snapshot, revision, device="cpu")
            self.model = _TorchModel(original.model, runtime)
        else:
            manifest, graph = validate_artifact(runtime, model, revision)
            # Check the tokenizer from the original immutable snapshot against export inputs.
            for relative, digest in manifest["source_files"].items():
                if file_hash(Path(snapshot) / relative) != digest:
                    raise ValueError("CPU export tokenizer or checkpoint identity changed")
            self.model = _OnnxModel(snapshot, graph, runtime, manifest["window"])
        self.load_ms = (time.perf_counter() - started) * 1000

    def rerank(self, query, rows, k=5):
        result = super().rerank(query, rows, k)
        for row in result:
            row["reranker_backend"] = self.runtime["backend"]
            row["reranker_runtime"] = dict(self.runtime)
        return result


@lru_cache(maxsize=4)
def _cached_cpu(model, revision, cache_folder, serialized_runtime):
    from huggingface_hub import snapshot_download

    snapshot = snapshot_download(
        model, revision=revision, cache_dir=cache_folder, local_files_only=True
    )
    return CpuReranker(snapshot, model, revision, json.loads(serialized_runtime))


def get_cpu_reranker(model, revision, cache_folder, runtime):
    runtime = validate_runtime(runtime)
    with _LOCK:
        return _cached_cpu(
            model,
            revision,
            cache_folder,
            json.dumps(runtime, sort_keys=True, separators=(",", ":")),
        )


def warmup(model, revision, cache_folder, runtime, query, rows):
    """Explicit startup/experiment warmup; never downloads or consumes a paid call."""
    started = time.perf_counter()
    ranker = get_cpu_reranker(model, revision, cache_folder, runtime)
    ranked = ranker.rerank(query, rows, k=len(rows)) if rows else []
    return {
        "runtime": dict(runtime),
        "model": model,
        "revision": revision,
        "load_ms": ranker.load_ms,
        "warmup_ms": (time.perf_counter() - started) * 1000,
        "pairs": len(ranked),
        "answer_model_calls": 0,
    }
