"""Parse explicit private drafts against independent public policy, without effects.

This module never saves credentials, activates models, calls a provider, resolves
DNS, opens a database, watches files or discovers an input path automatically.
Only fixed diagnostic codes and canonical field paths may leave this boundary.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any
import unicodedata
from urllib.parse import urlsplit

from pydantic import ValidationError

from app.modules.model_settings.schemas import ConfigurationSave, ModelValues
from generation.capabilities import ProviderCapabilities, validate as validate_capabilities
from generation.network_policy import UnsafeProviderDestination, validate_url
from generation.providers import headers as provider_headers
from generation.types import ModelConfig

INPUT_FORMAT = "5703_local_private_configuration_draft_v1"
INPUT_STATUS = "draft_only_no_current_bulk_file_consumer"
POLICY_FORMAT = "5703_private_configuration_public_policy_v1"
MAX_BYTES = 262144
MAX_ENTRIES = 64
MAX_DEPTH = 16
PROVIDERS = frozenset(
    {
        "mock",
        "openai",
        "azure_openai",
        "anthropic",
        "gemini",
        "ollama",
        "local",
        "openai_compatible",
    }
)
LOCAL_PROVIDERS = frozenset({"local", "ollama"})
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
AUTH_HEADERS = frozenset({"Authorization", "api-key", "x-api-key", "x-goog-api-key"})
API_STYLES = frozenset({"chat_completions", "responses", "anthropic_messages", "gemini_generate"})
TOKEN_PARAMETERS = frozenset({"max_tokens", "max_completion_tokens"})
CONFIG_FIELDS = frozenset(ModelValues.model_fields)
ENTRY_FIELDS = frozenset(ConfigurationSave.model_fields)
CAPABILITY_FIELDS = frozenset(ProviderCapabilities.model_fields)
SAFE_FIELDS = CONFIG_FIELDS | ENTRY_FIELDS | CAPABILITY_FIELDS
CAPABILITY_BOOLEANS = frozenset({"temperature", "seed", "reasoning_effort", "thinking_toggle"})
CAPABILITY_INTEGERS = frozenset({"probe_output_tokens", "output_token_ceiling"})
ROUTE_FIELDS = frozenset(
    {
        "name",
        "provider",
        "models",
        "destinations",
        "destination_reviewed",
        "auth_headers",
        "api_versions",
        "api_styles",
        "token_limit_parameters",
    }
)
DESTINATION_FIELDS = frozenset({"scheme", "host", "port", "path", "reviewed_hosts"})
DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    index: int | None = None

    def public(self):
        value = {"code": self.code, "path": self.path}
        if self.index is not None:
            value["index"] = self.index
        return value


class FileValidationFailure(Exception):
    """Safe fixed diagnostics; never retain private input or exception objects."""

    def __init__(self, issue: Issue):
        self.issue = issue
        super().__init__(issue.code)


@dataclass(frozen=True)
class ValidatedEntry:
    index: int
    provider: str
    configuration: ConfigurationSave = field(repr=False)


@dataclass(frozen=True)
class ValidatedBatch:
    total: int
    entries: tuple[ValidatedEntry, ...] = field(default=(), repr=False)
    skipped: tuple[int, ...] = ()
    issues: tuple[Issue, ...] = ()

    @property
    def valid(self):
        return not self.issues

    def public(self):
        return {
            "status": "validated_parse_only" if self.valid else "invalid",
            "configuration_count": self.total,
            "validated_count": len(self.entries),
            "skipped_count": len(self.skipped),
            "providers": sorted({entry.provider for entry in self.entries}),
            "errors": [issue.public() for issue in self.issues],
        }


def _fail(code, path, index=None):
    raise FileValidationFailure(Issue(code, path, index)) from None


def _clean_text(value, *, nonempty=True, maximum=2048):
    return (
        isinstance(value, str)
        and len(value) <= maximum
        and (not nonempty or bool(value))
        and not any(unicodedata.category(char) in {"Cc", "Cf"} for char in value)
    )


def _shape(value, allowed, path, index=None, required=()):
    if not isinstance(value, dict):
        _fail("OBJECT_REQUIRED", path, index)
    if set(value) - allowed:
        _fail("UNKNOWN_FIELD", path + "._unknown_field", index)
    if any(key not in value for key in required):
        _fail("REQUIRED_FIELD", path, index)


def _depth(value, level=0):
    if level > MAX_DEPTH:
        _fail("JSON_DEPTH_LIMIT", "input")
    if isinstance(value, dict):
        for nested in value.values():
            _depth(nested, level + 1)
    elif isinstance(value, list):
        for nested in value:
            _depth(nested, level + 1)


def _pairs(items):
    value = {}
    for key, nested in items:
        if key in value:
            _fail("DUPLICATE_JSON_KEY", "input")
        value[key] = nested
    return value


def _constant(_value):
    _fail("JSON_NUMBER_INVALID", "input")


def read_json(path: str | os.PathLike, *, kind="input"):
    """Bound a read of an explicitly supplied regular file, without path echoes."""
    try:
        candidate = Path(path)
        if not candidate.is_absolute():
            _fail("ABSOLUTE_PATH_REQUIRED", kind)
        spelling = os.fspath(candidate)
        if os.name == "nt" and (spelling.startswith(("\\\\", "//")) or ":" in spelling[2:]):
            _fail("FILE_PATH_INVALID", kind)
        if any(unicodedata.category(char) in {"Cc", "Cf"} for char in spelling):
            _fail("FILE_PATH_INVALID", kind)
        # Checking parent components also rejects a directory junction/symlink.
        for part in (*reversed(candidate.parents), candidate):
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
            ):
                _fail("FILE_LINK_REJECTED", kind)
        before = candidate.lstat()
        if not stat.S_ISREG(before.st_mode):
            _fail("REGULAR_FILE_REQUIRED", kind)
        if before.st_size > MAX_BYTES:
            _fail("FILE_SIZE_LIMIT", kind)
        descriptor = os.open(
            candidate, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        )
        with os.fdopen(descriptor, "rb") as source:
            opened = os.fstat(source.fileno())
            if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (
                opened.st_dev,
                opened.st_ino,
            ):
                _fail("FILE_CHANGED", kind)
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            _fail("FILE_SIZE_LIMIT", kind)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
        _depth(value)
        return value
    except FileValidationFailure as error:
        # Parser helpers use fixed input paths; distinguish the public policy.
        if kind == "policy" and error.issue.path == "input":
            _fail(error.issue.code, "policy")
        raise
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        _fail("FILE_READ_OR_JSON_INVALID", kind)


def _valid_host(host):
    if not isinstance(host, str):
        return False
    if host in LOCAL_HOSTS:
        return True
    return bool(
        _clean_text(host, maximum=253)
        and host == host.lower()
        and "." in host
        and all(DNS_LABEL.fullmatch(label) for label in host.split("."))
    )


def _azure_host(host):
    suffix = ".openai.azure.com"
    return host.endswith(suffix) and bool(DNS_LABEL.fullmatch(host[: -len(suffix)]))


def _destination(raw, path, index=None):
    if not _clean_text(raw) or any(char.isspace() for char in raw) or "\\" in raw:
        _fail("DESTINATION_INVALID", path, index)
    try:
        url = urlsplit(raw)
        # Preserve explicit port 0: the runtime static helper uses `port or default`.
        port = (443 if url.scheme == "https" else 80) if url.port is None else url.port
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or "%" in url.netloc
            or not 1 <= port <= 65535
            or not _valid_host(url.hostname)
            or any(ord(char) > 127 for char in url.netloc)
            or url.hostname.endswith(".")
        ):
            _fail("DESTINATION_INVALID", path, index)
        validate_url(raw)  # Static syntax/address policy only; never resolve DNS.
        return url.scheme, url.hostname, port, url.path.rstrip("/")
    except (ValueError, UnsafeProviderDestination):
        _fail("DESTINATION_INVALID", path, index)


def validate_policy(value: Any):
    _shape(
        value, {"format", "reviewed", "routes"}, "policy", required={"format", "reviewed", "routes"}
    )
    if value["format"] != POLICY_FORMAT:
        _fail("POLICY_VERSION_UNSUPPORTED", "policy.format")
    if value["reviewed"] is not True:
        _fail("POLICY_REVIEW_REQUIRED", "policy.reviewed")
    routes = value["routes"]
    if not isinstance(routes, list) or not 1 <= len(routes) <= MAX_ENTRIES:
        _fail("POLICY_ROUTES_INVALID", "policy.routes")
    names = set()
    for index, route in enumerate(routes):
        prefix = f"policy.routes[{index}]"
        _shape(route, ROUTE_FIELDS, prefix, index, ROUTE_FIELDS)
        if not _clean_text(route["name"], maximum=120) or route["name"] in names:
            _fail("POLICY_NAME_INVALID", prefix + ".name", index)
        names.add(route["name"])
        provider = route["provider"]
        if (
            not isinstance(provider, str)
            or provider not in PROVIDERS
            or type(route["destination_reviewed"]) is not bool
        ):
            _fail("POLICY_ROUTE_INVALID", prefix, index)
        models = route["models"]
        if (
            not isinstance(models, list)
            or not 1 <= len(models) <= MAX_ENTRIES
            or not all(
                _clean_text(model, maximum=200) and model == model.strip() for model in models
            )
            or len(set(models)) != len(models)
        ):
            _fail("POLICY_MODELS_INVALID", prefix + ".models", index)
        for key, allowed in (
            ("auth_headers", AUTH_HEADERS | {None}),
            ("api_styles", API_STYLES),
            ("token_limit_parameters", TOKEN_PARAMETERS),
        ):
            if (
                not isinstance(route[key], list)
                or not route[key]
                or any(
                    (item is not None and not isinstance(item, str)) or item not in allowed
                    for item in route[key]
                )
                or len(route[key]) != len(set(route[key]))
            ):
                _fail("POLICY_ROUTE_INVALID", prefix + "." + key, index)
        versions = route["api_versions"]
        if (
            not isinstance(versions, list)
            or not versions
            or any(item is not None and not _clean_text(item, maximum=50) for item in versions)
        ):
            _fail("POLICY_ROUTE_INVALID", prefix + ".api_versions", index)
        destinations = route["destinations"]
        if (
            not isinstance(destinations, list)
            or len(destinations) > MAX_ENTRIES
            or (provider != "mock" and not destinations)
            or (provider == "mock" and destinations)
        ):
            _fail("POLICY_DESTINATIONS_INVALID", prefix + ".destinations", index)
        for destination in destinations:
            _shape(
                destination,
                DESTINATION_FIELDS,
                prefix + ".destinations",
                index,
                {"scheme", "host", "port", "path"},
            )
            scheme, host, port, base_path = (
                destination[field_name] for field_name in ("scheme", "host", "port", "path")
            )
            if (
                type(port) is not int
                or not 1 <= port <= 65535
                or not isinstance(scheme, str)
                or scheme not in {"http", "https"}
                or not _clean_text(base_path, nonempty=False)
                or (
                    base_path
                    and (
                        not base_path.startswith("/")
                        or base_path.endswith("/")
                        or any(char in base_path for char in "?#\\")
                        or any(char.isspace() for char in base_path)
                    )
                )
            ):
                _fail("POLICY_DESTINATIONS_INVALID", prefix + ".destinations", index)
            if host == "*.openai.azure.com":
                reviewed = destination.get("reviewed_hosts")
                if (
                    provider != "azure_openai"
                    or scheme != "https"
                    or port != 443
                    or not isinstance(reviewed, list)
                    or not reviewed
                    or not all(isinstance(item, str) and _azure_host(item) for item in reviewed)
                ):
                    _fail("POLICY_AZURE_HOST_INVALID", prefix + ".destinations", index)
            elif not _valid_host(host):
                _fail("POLICY_DESTINATIONS_INVALID", prefix + ".destinations", index)
            if provider in LOCAL_PROVIDERS:
                if host not in LOCAL_HOSTS:
                    _fail("POLICY_LOCAL_HOST_INVALID", prefix + ".destinations", index)
            elif scheme != "https" or port != 443 or host in LOCAL_HOSTS:
                _fail("POLICY_HOSTED_ROUTE_INVALID", prefix + ".destinations", index)
    return {route["name"]: route for route in routes}


def public_drafts():
    """Public blank template identities; they never authorize a ready model."""
    common = {
        "window_tokens": 16384,
        "max_tokens": 1024,
        "timeout_seconds": 60,
        "temperature": 0,
        "tokenizer_provider": "estimate",
        "token_count_fallback": "estimate",
        "token_limit_parameter": "max_tokens",
    }
    rows = [
        ("OpenAI", "openai", "", "https://api.openai.com/v1", "json_schema"),
        ("Azure OpenAI", "azure_openai", "", "", "json_schema"),
        ("Anthropic", "anthropic", "", "https://api.anthropic.com/v1", "prompt"),
        (
            "Google Gemini",
            "gemini",
            "",
            "https://generativelanguage.googleapis.com/v1beta",
            "json_schema",
        ),
        ("Ollama", "ollama", "", "http://127.0.0.1:11434/v1", "json_schema"),
        (
            "DeepSeek compatible endpoint",
            "openai_compatible",
            "deepseek-flash",
            "https://api.deepseek.com/v1",
            "json_object",
        ),
        ("Custom compatible endpoint", "openai_compatible", "", "", "json_schema"),
        ("Explicit authored mock", "mock", "authored-extractive-v1", None, "json_schema"),
        ("Local OpenAI-compatible server", "local", "", "", "json_schema"),
    ]
    rows.extend(
        (name, "openai_compatible", "", "", "json_object")
        for name in (
            "xAI",
            "Meta-compatible endpoint",
            "Qwen",
            "GLM",
            "Kimi",
            "MiniMax",
            "Doubao",
            "ERNIE",
            "Tencent Hunyuan",
            "iFlytek Spark",
            "MiMo",
        )
    )
    result = {}
    for name, provider, model, base, mode in rows:
        config = {
            "provider": provider,
            "model": model,
            "base_url": base,
            **common,
            "structured_output_mode": mode,
        }
        if provider == "anthropic":
            config["api_version"] = "2023-06-01"
        if name == "DeepSeek compatible endpoint":
            config["thinking_enabled"] = False
        if provider == "azure_openai":
            config["api_version"] = None
        result[name] = {"name": name, "config": config, "api_key": ""}
    return result


def _safe_schema_issues(error: ValidationError, prefix, index):
    issues = []
    for detail in error.errors(include_input=False, include_context=False, include_url=False):
        parts = []
        for part in detail["loc"]:
            if isinstance(part, str) and part in SAFE_FIELDS:
                parts.append("." + part)
            elif type(part) is int and 0 <= part <= MAX_ENTRIES:
                parts.append(f"[{part}]")
            else:
                parts.append("._unknown_field")
        issue = Issue("SCHEMA_INVALID", prefix + "".join(parts), index)
        if issue not in issues:
            issues.append(issue)
    return issues or [Issue("SCHEMA_INVALID", prefix, index)]


def _strict_text_and_capabilities(config, prefix, index):
    for name, value in config.items():
        if isinstance(value, str) and not _clean_text(value, nonempty=False):
            _fail("TEXT_INVALID", prefix + "." + name, index)
    capabilities = config.get("capabilities")
    if capabilities is not None:
        _shape(capabilities, CAPABILITY_FIELDS, prefix + ".capabilities", index)
        for name, value in capabilities.items():
            if name in CAPABILITY_BOOLEANS and type(value) is not bool:
                _fail("CAPABILITY_TYPE_INVALID", prefix + ".capabilities." + name, index)
            if name in CAPABILITY_INTEGERS and type(value) is not int:
                _fail("CAPABILITY_TYPE_INVALID", prefix + ".capabilities." + name, index)
            if isinstance(value, str) and not _clean_text(value, maximum=200):
                _fail("TEXT_INVALID", prefix + ".capabilities." + name, index)
        if "structured_modes" in capabilities and (
            not isinstance(capabilities["structured_modes"], list)
            or not all(isinstance(item, str) for item in capabilities["structured_modes"])
        ):
            _fail("CAPABILITY_TYPE_INVALID", prefix + ".capabilities.structured_modes", index)
    if (config.get("capability_version") is None) != (capabilities is None):
        _fail("CAPABILITY_PAIR_REQUIRED", prefix + ".capabilities", index)


def _policy_match(configuration, route, prefix, index):
    config = configuration.config
    if config.provider != route["provider"]:
        _fail("PROVIDER_NOT_APPROVED", prefix + ".config.provider", index)
    if config.model not in route["models"]:
        _fail("MODEL_NOT_APPROVED", prefix + ".config.model", index)
    if config.provider == "mock":
        if (
            configuration.api_key is not None
            or config.base_url is not None
            or config.auth_header is not None
        ):
            _fail("MOCK_CONFIGURATION_INVALID", prefix + ".config", index)
    else:
        if config.provider not in LOCAL_PROVIDERS and configuration.api_key is None:
            _fail("KEY_REQUIRED", prefix + ".api_key", index)
        if route["destination_reviewed"] is not True:
            _fail("DESTINATION_REVIEW_REQUIRED", prefix + ".config.base_url", index)
        scheme, host, port, base_path = _destination(
            config.base_url, prefix + ".config.base_url", index
        )
        if config.provider in LOCAL_PROVIDERS:
            if host not in LOCAL_HOSTS:
                _fail("LOCAL_DESTINATION_REQUIRED", prefix + ".config.base_url", index)
        elif scheme != "https" or port != 443 or host in LOCAL_HOSTS:
            _fail("HOSTED_HTTPS_REQUIRED", prefix + ".config.base_url", index)
        matched = any(
            destination["scheme"] == scheme
            and destination["port"] == port
            and destination["path"] == base_path
            and (
                destination["host"] == host
                or (
                    destination["host"] == "*.openai.azure.com"
                    and _azure_host(host)
                    and host in destination["reviewed_hosts"]
                )
            )
            for destination in route["destinations"]
        )
        if not matched:
            _fail("DESTINATION_NOT_APPROVED", prefix + ".config.base_url", index)
    header, api_version = _effective_protocol(config, has_key=configuration.api_key is not None)
    style = (
        config.capabilities.api_style
        if config.capabilities
        else {"anthropic": "anthropic_messages", "gemini": "gemini_generate"}.get(
            config.provider, "chat_completions"
        )
    )
    for value, allowed, label in (
        (header, route["auth_headers"], "auth_header"),
        (api_version, route["api_versions"], "api_version"),
        (style, route["api_styles"], "capabilities"),
        (config.token_limit_parameter, route["token_limit_parameters"], "token_limit_parameter"),
    ):
        if value not in allowed:
            _fail("PROTOCOL_POLICY_MISMATCH", prefix + ".config." + label, index)


def _effective_protocol(config, *, has_key):
    """Use the actual pure wire helper without exposing credential bytes."""
    if config.provider == "mock":
        return None, None
    runtime = ModelConfig.from_dict(config.model_dump())
    wire = provider_headers(runtime, "authored-key-presence-only" if has_key else None)
    header = next((name for name in AUTH_HEADERS if name in wire), None)
    api_version = (
        wire.get("anthropic-version")
        if config.provider == "anthropic"
        else (config.api_version or None)
        if config.provider == "azure_openai"
        else None
    )
    return header, api_version


def validate_document(document: Any, policy: Any):
    """Validate in memory; returned credentials remain SecretStr and repr-hidden."""
    routes = validate_policy(policy)
    _depth(document)
    _shape(
        document,
        {"format", "consumer_status", "primary_provider", "configurations"},
        "input",
        required={"format", "consumer_status", "primary_provider", "configurations"},
    )
    if document["format"] != INPUT_FORMAT:
        _fail("INPUT_VERSION_UNSUPPORTED", "input.format")
    if document["consumer_status"] != INPUT_STATUS:
        _fail("INPUT_STATUS_UNSUPPORTED", "input.consumer_status")
    if not _clean_text(document["primary_provider"], maximum=120):
        _fail("PRIMARY_PROVIDER_INVALID", "input.primary_provider")
    rows = document["configurations"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ENTRIES:
        _fail("CONFIGURATIONS_INVALID", "input.configurations")
    entries, skipped, issues, names = [], [], [], set()
    drafts = public_drafts()
    primary_indices = []
    for index, row in enumerate(rows):
        prefix = f"input.configurations[{index}]"
        try:
            _shape(row, ENTRY_FIELDS, prefix, index, {"name", "config"})
            name = row["name"]
            if not _clean_text(name, maximum=120):
                _fail("NAME_INVALID", prefix + ".name", index)
            if name in names:
                _fail("DUPLICATE_NAME", prefix + ".name", index)
            names.add(name)
            primary = name == document["primary_provider"]
            if primary:
                primary_indices.append(index)
            _shape(row["config"], CONFIG_FIELDS, prefix + ".config", index, {"provider", "model"})
            key = row.get("api_key")
            if key is not None and (
                not isinstance(key, str)
                or len(key) > 8192
                or (key != "" and (not key.strip() or not _clean_text(key, maximum=8192)))
            ):
                _fail("KEY_INVALID", prefix + ".api_key", index)
            if not primary and row == drafts.get(name) and row["config"]["provider"] != "mock":
                skipped.append(index)
                continue
            if name not in routes:
                _fail("NAME_NOT_APPROVED", prefix + ".name", index)
            _strict_text_and_capabilities(row["config"], prefix + ".config", index)
            body = dict(row)
            if key == "" or key is None:
                body["api_key"] = None
            try:
                configuration = ConfigurationSave.model_validate(body)
                runtime = ModelConfig.from_dict(configuration.config.model_dump())
                runtime.validate()
                validate_capabilities(runtime)
            except ValidationError as error:
                issues.extend(_safe_schema_issues(error, prefix, index))
                continue
            except (ValueError, TypeError):
                _fail("CAPABILITY_OR_CONFIGURATION_INVALID", prefix + ".config", index)
            _policy_match(configuration, routes[name], prefix, index)
            entries.append(ValidatedEntry(index, configuration.config.provider, configuration))
        except FileValidationFailure as error:
            issues.append(error.issue)
    if len(primary_indices) != 1:
        issues.append(Issue("PRIMARY_PROVIDER_NOT_UNIQUE", "input.primary_provider"))
    elif not any(entry.index == primary_indices[0] for entry in entries):
        issues.append(Issue("PRIMARY_PROVIDER_INCOMPLETE", "input.primary_provider"))
    return ValidatedBatch(len(rows), tuple(entries), tuple(skipped), tuple(issues))


def validate_files(input_path, policy_path):
    policy = read_json(policy_path, kind="policy")
    validate_policy(policy)  # A bad public policy stops before private input reads.
    return validate_document(read_json(input_path), policy)


class _SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        _fail("CLI_ARGUMENTS_INVALID", "arguments")


def main(argv=None):
    parser = _SafeParser(
        description="Explicit offline parse and public-policy validation only; no save, activation or provider call."
    )
    parser.add_argument(
        "--input", required=True, help="Explicit absolute path to a local JSON draft"
    )
    parser.add_argument(
        "--policy",
        required=True,
        help="Explicit absolute path to an independently reviewed public JSON policy",
    )
    try:
        args = parser.parse_args(argv)
        result = validate_files(args.input, args.policy)
        print(json.dumps(result.public(), sort_keys=True))
        return 0 if result.valid else 2
    except FileValidationFailure as error:
        print(json.dumps({"status": "invalid", "errors": [error.issue.public()]}, sort_keys=True))
        return 2
    except Exception:
        # Unexpected dependency/parser faults must not expose private exception text.
        print(
            json.dumps(
                {
                    "status": "invalid",
                    "errors": [{"code": "VALIDATION_INTERNAL_ERROR", "path": "input"}],
                },
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
