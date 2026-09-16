"""Offline model tokenizers and explicitly labelled estimates for complete requests."""

from __future__ import annotations

from functools import lru_cache
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path

from .providers import payload
from .types import ModelConfig

CACHE = Path(__file__).resolve().parents[1] / "artifacts" / "tiktoken"
ENCODINGS = {
    "cl100k_base": "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7",
    "o200k_base": "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d",
}


def estimate_tokens(text: str) -> int:
    """Unicode character heuristic, never claimed as actual tokenizer output."""
    ascii_count = sum(ord(c) < 128 for c in text)
    return math.ceil(ascii_count / 3) + 2 * (len(text) - ascii_count)


@lru_cache(maxsize=8)
def _tiktoken(name):
    import tiktoken

    resource = "o200k_base" if name == "o200k_harmony" else name
    if resource not in ENCODINGS:
        raise ValueError("This encoding has not been provisioned for offline use")
    root = Path(os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(CACHE)))
    url = f"https://openaipublic.blob.core.windows.net/encodings/{resource}.tiktoken"
    cached = root / hashlib.sha1(url.encode()).hexdigest()
    if (
        not cached.is_file()
        or hashlib.sha256(cached.read_bytes()).hexdigest() != ENCODINGS[resource]
    ):
        raise ValueError("Verified offline tokenizer cache is unavailable")
    return tiktoken.get_encoding(name)


@lru_cache(maxsize=4)
def _huggingface(path, name, revision):
    from transformers import AutoTokenizer

    if not path and (not name or not revision):
        raise ValueError("A local tokenizer path or pinned tokenizer revision is required")
    files = {}
    if path:
        root = Path(path).resolve()
        manifest_path = root / "SOURCE_MANIFEST.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if revision and manifest.get("revision") != revision:
                raise ValueError("Tokenizer source revision differs from the configured revision")
            for item in manifest["files"]:
                file = (root / item["file"]).resolve()
                if not file.is_relative_to(root) or not file.is_file():
                    raise ValueError("Tokenizer source manifest path is unavailable")
                actual = hashlib.sha256(file.read_bytes()).hexdigest()
                if actual != item["sha256"]:
                    raise ValueError("Tokenizer source file hash changed")
                files[item["file"]] = actual
        else:
            files = {
                file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                for file in root.iterdir()
                if file.is_file()
                and file.name
                in {
                    "tokenizer.json",
                    "tokenizer_config.json",
                    "special_tokens_map.json",
                    "vocab.json",
                    "vocab.txt",
                    "merges.txt",
                    "tokenizer.model",
                }
            }
    tokenizer = AutoTokenizer.from_pretrained(
        path or name, revision=revision, local_files_only=True, trust_remote_code=False
    )
    return tokenizer, files


class TokenCounter:
    def __init__(self, config: ModelConfig):
        self.config = config
        self._count = estimate_tokens
        self.metadata = {
            "source": "unicode_character_estimate_v1",
            "is_estimate": True,
            "model": config.model,
            "fallback_reason": None,
        }
        kind = config.tokenizer_provider
        try:
            if kind in {"estimate", "provider"}:
                self.metadata["fallback_reason"] = (
                    "provider_preflight_pending" if kind == "provider" else "explicit_estimate"
                )
                return
            if kind == "huggingface" or (kind == "auto" and config.tokenizer_local_path):
                tokenizer, files = _huggingface(
                    config.tokenizer_local_path, config.tokenizer_name, config.tokenizer_revision
                )
                self._count = lambda text: len(tokenizer.encode(text, add_special_tokens=False))
                self.metadata.update(
                    source="huggingface",
                    name=config.tokenizer_name or tokenizer.name_or_path,
                    revision=config.tokenizer_revision,
                    library_version=version("transformers"),
                    is_estimate=False,
                    files_sha256=files,
                    model_mapping="configured_tokenizer; API alias checkpoint equivalence requires provider calibration",
                )
                return
            import tiktoken

            if (
                kind == "auto"
                and config.provider not in {"openai", "azure_openai", "mock"}
                and not config.tokenizer_name
            ):
                raise ValueError("No verified tokenizer mapping for this provider/model")
            name = config.tokenizer_name or (
                "cl100k_base"
                if config.provider == "mock"
                else tiktoken.model.encoding_name_for_model(config.model)
            )
            encoding = _tiktoken(name)
            self._count = lambda text: len(encoding.encode(text, disallowed_special=()))
            self.metadata.update(
                source="tiktoken",
                name=name,
                library_version=version("tiktoken"),
                is_estimate=config.provider == "mock",
                fallback_reason="mock_surrogate_tokenizer" if config.provider == "mock" else None,
            )
        except (ImportError, KeyError, ValueError, OSError) as exc:
            if config.token_count_fallback == "error":
                raise ValueError(
                    "TOKENIZER_UNAVAILABLE: configure a verified local tokenizer or allow an explicit estimate"
                ) from exc
            self.metadata["fallback_reason"] = (
                type(exc).__name__ + ": tokenizer unavailable locally"
            )

    def count(self, text: str) -> int:
        return self._count(text)

    def request_input(self, messages, schema, schema_name="chat_response_v1"):
        # Serialize the same protocol payload the adapter submits: system prompt,
        # roles, history, current turn, profile, complete evidence and schema all count.
        # JSON/role framing is conservatively included; server-side templates remain
        # unknown without provider countTokens. Local totals are therefore estimates.
        body = payload(self.config, messages, schema, schema_name)
        tokens = self.count(json.dumps(body, ensure_ascii=False, sort_keys=True))
        return tokens + 128

    def report(self):
        return {
            **self.metadata,
            "whole_request_is_estimate": True,
            "protocol_safety_tokens": 128,
            "scope": "complete_serialized_request_including_schema_and_roles",
        }
