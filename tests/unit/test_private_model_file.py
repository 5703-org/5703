"""Fictitious file/policy validation, strict privacy and no-effect regressions."""

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import inspect
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

HERE = Path(__file__).resolve().parents[2]
SUBJECT = HERE / "scripts/model_configs/private_file.py"
SPEC = spec_from_file_location("private_model_file_subject", SUBJECT)
subject = module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)

FIXTURE_KEY = "AUTHORED_PRIVATE_TOKEN_81e209"


def configuration(
    name="OpenAI",
    provider="openai",
    *,
    model="authored-model-v1",
    base_url="https://api.openai.com/v1",
    api_key=FIXTURE_KEY,
):
    return {
        "name": name,
        "config": {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "window_tokens": 16384,
            "max_tokens": 1024,
            "timeout_seconds": 60,
            "temperature": 0,
            "tokenizer_provider": "estimate",
            "token_count_fallback": "estimate",
            "token_limit_parameter": "max_tokens",
            "structured_output_mode": "json_schema",
        },
        "api_key": api_key,
    }


def route(row):
    config = row["config"]
    provider = config["provider"]
    destination = []
    if provider != "mock":
        scheme, host, port, path = subject._destination(config["base_url"], "fixture")
        destination = [{"scheme": scheme, "host": host, "port": port, "path": path}]
    if provider == "mock":
        header, api_version = None, None
    else:
        from generation.providers import headers
        from generation.types import ModelConfig

        wire = headers(ModelConfig.from_dict(config), row.get("api_key"))
        header = next((name for name in subject.AUTH_HEADERS if name in wire), None)
        api_version = (
            wire.get("anthropic-version")
            if provider == "anthropic"
            else (config.get("api_version") or None)
            if provider == "azure_openai"
            else None
        )
    style = {"anthropic": "anthropic_messages", "gemini": "gemini_generate"}.get(
        provider, "chat_completions"
    )
    return {
        "name": row["name"],
        "provider": provider,
        "models": [config["model"]],
        "destinations": destination,
        "destination_reviewed": True,
        "auth_headers": [header],
        "api_versions": [api_version],
        "api_styles": [style],
        "token_limit_parameters": [config["token_limit_parameter"]],
    }


def policy(*rows):
    return {
        "format": subject.POLICY_FORMAT,
        "reviewed": True,
        "routes": [route(row) for row in rows],
    }


def document(*rows, primary=None):
    return {
        "format": subject.INPUT_FORMAT,
        "consumer_status": subject.INPUT_STATUS,
        "primary_provider": primary or rows[0]["name"],
        "configurations": list(rows),
    }


def report(row, approved=None):
    result = subject.validate_document(document(row), approved or policy(configuration()))
    value = result.public()
    assert FIXTURE_KEY not in json.dumps(value) + repr(result)
    return value


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "provider,name,base",
    [
        ("openai", "OpenAI", "https://api.openai.com/v1"),
        ("azure_openai", "Azure OpenAI", "https://authored-resource.openai.azure.com/openai/v1"),
        ("anthropic", "Anthropic", "https://api.anthropic.com/v1"),
        ("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta"),
        ("ollama", "Ollama", "http://127.0.0.1:11434/v1"),
        ("local", "Local OpenAI-compatible server", "http://localhost:8910/v1"),
        ("openai_compatible", "DeepSeek compatible endpoint", "https://api.deepseek.com/v1"),
        ("mock", "Explicit authored mock", None),
    ],
)
def test_all_eight_protocols_validate_only_against_independent_fictitious_policy(
    provider, name, base
):
    row = configuration(
        name,
        provider,
        base_url=base,
        api_key="" if provider in {"mock", "ollama", "local"} else FIXTURE_KEY,
    )
    original = deepcopy(row)
    result = subject.validate_document(document(row), policy(row))
    assert result.valid and result.public()["providers"] == [provider]
    assert result.public()["status"] == "validated_parse_only"
    saved = result.entries[0].configuration
    assert saved.api_key is None if row["api_key"] == "" else isinstance(saved.api_key, SecretStr)
    assert FIXTURE_KEY not in repr(result) + repr(result.entries[0]) + json.dumps(result.public())
    assert row == original


def test_hosted_key_stays_secretstr_with_exact_unchanged_value_and_no_payload_repr():
    row = configuration(api_key="  " + FIXTURE_KEY + "  ")
    result = subject.validate_document(document(row), policy(row))
    assert result.valid
    assert result.entries[0].configuration.api_key.get_secret_value() == "  " + FIXTURE_KEY + "  "
    assert FIXTURE_KEY not in repr(result) + repr(result.entries[0])


def test_entire_public_twenty_entry_template_can_skip_untouched_secondary_drafts():
    drafts = subject.public_drafts()
    assert len(drafts) == 20
    mock = drafts["Explicit authored mock"]
    result = subject.validate_document(
        document(*drafts.values(), primary=mock["name"]), policy(mock)
    )
    assert result.valid and len(result.entries) == 1 and len(result.skipped) == 19
    assert result.public()["providers"] == ["mock"]


def test_primary_blank_template_never_skips_or_invents_model_key_or_endpoint():
    row = subject.public_drafts()["OpenAI"]
    value = report(row)
    assert value["status"] == "invalid" and value["skipped_count"] == 0
    assert value["validated_count"] == 0
    assert any(item["code"] == "PRIMARY_PROVIDER_INCOMPLETE" for item in value["errors"])


def test_changed_unfilled_secondary_entry_is_not_silently_skipped():
    mock = subject.public_drafts()["Explicit authored mock"]
    changed = subject.public_drafts()["OpenAI"]
    changed["config"]["base_url"] = "https://unreviewed.invalid/" + FIXTURE_KEY
    result = subject.validate_document(document(mock, changed), policy(mock))
    assert not result.valid and not result.skipped
    assert FIXTURE_KEY not in json.dumps(result.public())


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", FIXTURE_KEY),
        ("model", FIXTURE_KEY),
        ("provider", FIXTURE_KEY),
        ("base_url", "https://" + FIXTURE_KEY + ".invalid/v1"),
    ],
)
def test_private_values_echoed_in_identity_fields_never_enter_reports(field, value):
    row = configuration()
    (row if field == "name" else row["config"])[field] = value
    result = report(row)
    assert result["status"] == "invalid" and result["validated_count"] == 0


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_or_blank_hosted_key_has_safe_key_field_error(key):
    result = report(configuration(api_key=key))
    assert result["status"] == "invalid"
    assert any(item["path"].endswith(".api_key") for item in result["errors"])


@pytest.mark.parametrize("layer", ["root", "entry", "config", "capabilities"])
def test_unknown_fields_and_attacker_field_names_are_never_echoed(layer):
    row = configuration()
    value = document(row)
    target = {"root": value, "entry": row, "config": row["config"]}.get(layer)
    if layer == "capabilities":
        row["config"]["capabilities"] = {FIXTURE_KEY: FIXTURE_KEY}
    else:
        target[FIXTURE_KEY] = FIXTURE_KEY
    try:
        result = subject.validate_document(value, policy(configuration())).public()
    except subject.FileValidationFailure as error:
        result = error.issue.public()
    assert FIXTURE_KEY not in json.dumps(result)
    assert "UNKNOWN_FIELD" in json.dumps(result)


def test_duplicate_names_fail_and_primary_is_not_selected_ambiguously():
    row = configuration()
    result = subject.validate_document(document(row, deepcopy(row)), policy(row))
    assert not result.valid
    assert any(issue.code == "DUPLICATE_NAME" for issue in result.issues)


@pytest.mark.parametrize(
    "field,value",
    [
        ("format", "wrong"),
        ("consumer_status", "automatically_loaded"),
        ("primary_provider", FIXTURE_KEY),
    ],
)
def test_version_status_and_missing_primary_are_safe(field, value):
    row = configuration()
    data = document(row)
    data[field] = value
    try:
        result = subject.validate_document(data, policy(row)).public()
    except subject.FileValidationFailure as error:
        result = error.issue.public()
    assert FIXTURE_KEY not in json.dumps(result)


@pytest.mark.parametrize(
    "base",
    [
        "http://api.openai.com/v1",
        "https://api.openai.com:0/v1",
        "https://user:" + FIXTURE_KEY + "@api.openai.com/v1",
        "https://api.openai.com/v1?api_key=" + FIXTURE_KEY,
        "https://api.openai.com/v1#" + FIXTURE_KEY,
        "https://api.openai.com.evil.invalid/v1",
        "https://api.openai.com./v1",
        "https://api%2eopenai.com/v1",
        "https://api.openai.com\\evil.invalid/v1",
        "https://api.openai.com/v1/" + FIXTURE_KEY,
        "https://10.0.0.1/v1",
        "https://api.openai.com/\n" + FIXTURE_KEY,
    ],
)
def test_hosted_destination_tricks_and_secret_urls_are_blocked_without_echo(base):
    value = report(configuration(base_url=base))
    assert value["status"] == "invalid" and value["validated_count"] == 0


def test_local_protocol_requires_explicit_loopback_host_and_port_policy():
    row = configuration(
        "Local OpenAI-compatible server", "local", base_url="http://localhost:8910/v1", api_key=""
    )
    approved = policy(row)
    row["config"]["base_url"] = "http://localhost:8911/v1"
    assert report(row, approved)["status"] == "invalid"


def test_custom_destination_remains_blocked_until_explicit_public_review():
    row = configuration(
        "Custom compatible endpoint",
        "openai_compatible",
        base_url="https://authored-vendor.invalid/v1",
    )
    approved = policy(row)
    approved["routes"][0]["destination_reviewed"] = False
    value = report(row, approved)
    assert any(item["code"] == "DESTINATION_REVIEW_REQUIRED" for item in value["errors"])


@pytest.mark.parametrize(
    "host,valid",
    [
        ("authored-resource.openai.azure.com", True),
        ("other.openai.azure.com", False),
        ("nested.authored-resource.openai.azure.com", False),
        ("-bad.openai.azure.com", False),
        ("bad-.openai.azure.com", False),
        ("authored-resource.openai.azure.com.evil.invalid", False),
    ],
)
def test_azure_wildcard_only_accepts_exact_reviewed_single_resource_host(host, valid):
    row = configuration(
        "Azure OpenAI",
        "azure_openai",
        base_url="https://authored-resource.openai.azure.com/openai/v1",
    )
    approved = policy(row)
    approved["routes"][0]["destinations"][0].update(
        host="*.openai.azure.com", reviewed_hosts=["authored-resource.openai.azure.com"]
    )
    row["config"]["base_url"] = "https://" + host + "/openai/v1"
    assert (report(row, approved)["status"] == "validated_parse_only") is valid


def test_azure_wildcard_without_exact_reviewed_host_is_invalid_public_policy():
    row = configuration(
        "Azure OpenAI",
        "azure_openai",
        base_url="https://authored-resource.openai.azure.com/openai/v1",
    )
    approved = policy(row)
    approved["routes"][0]["destinations"][0]["host"] = "*.openai.azure.com"
    with pytest.raises(subject.FileValidationFailure) as caught:
        subject.validate_document(document(row), approved)
    assert caught.value.issue.code == "POLICY_AZURE_HOST_INVALID"


@pytest.mark.parametrize(
    "field,value",
    [
        ("auth_header", "x-api-key"),
        ("api_version", "unreviewed-version"),
        ("token_limit_parameter", "max_completion_tokens"),
    ],
)
def test_protocol_options_require_exact_public_policy(field, value):
    row = (
        configuration(
            "Azure OpenAI",
            "azure_openai",
            base_url="https://authored-resource.openai.azure.com/openai/v1",
        )
        if field == "api_version"
        else configuration()
    )
    approved = policy(row)
    row["config"][field] = value
    assert report(row, approved)["status"] == "invalid"


@pytest.mark.parametrize(
    "provider,field,allowed,expected",
    [
        ("local", "auth_headers", ["Authorization"], False),
        ("local", "auth_headers", [None], True),
        ("anthropic", "api_versions", [None], False),
        ("anthropic", "api_versions", ["2023-06-01"], True),
    ],
)
def test_policy_checks_effective_wire_header_and_default_version(
    provider, field, allowed, expected
):
    from generation.providers import headers
    from generation.types import ModelConfig

    local = provider == "local"
    row = configuration(
        "Local OpenAI-compatible server" if local else "Anthropic",
        provider,
        base_url="http://localhost:8910/v1" if local else "https://api.anthropic.com/v1",
        api_key="" if local else FIXTURE_KEY,
    )
    original = deepcopy(row)
    approved = policy(row)
    approved["routes"][0][field] = allowed
    wire = headers(ModelConfig.from_dict(row["config"]), row["api_key"] or None)
    effective = (
        next((name for name in subject.AUTH_HEADERS if name in wire), None)
        if field == "auth_headers"
        else wire.get("anthropic-version")
    )
    assert (effective in allowed) is expected
    result = subject.validate_document(document(row), approved)
    assert result.valid is expected
    assert row == original
    assert FIXTURE_KEY not in json.dumps(result.public()) + repr(result)
    if expected:
        saved = result.entries[0].configuration
        assert saved.config.api_version is None
        if local:
            assert saved.api_key is None
        else:
            assert saved.api_key.get_secret_value() == FIXTURE_KEY
    else:
        assert any(issue.code == "PROTOCOL_POLICY_MISMATCH" for issue in result.issues)


@pytest.mark.parametrize("allowed,expected", [([None], True), ([FIXTURE_KEY], False)])
@pytest.mark.parametrize(
    "provider,name,base",
    [
        ("openai", "OpenAI", "https://api.openai.com/v1"),
        ("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta"),
        ("local", "Local OpenAI-compatible server", "http://localhost:8910/v1"),
        ("ollama", "Ollama", "http://127.0.0.1:11434/v1"),
        ("openai_compatible", "DeepSeek compatible endpoint", "https://api.deepseek.com/v1"),
        ("mock", "Explicit authored mock", None),
    ],
)
def test_unused_declared_api_version_requires_effective_none_policy(
    provider, name, base, allowed, expected
):
    from generation.providers import endpoint, headers
    from generation.types import ModelConfig
    from urllib.parse import urlsplit

    row = configuration(
        name,
        provider,
        base_url=base,
        api_key="" if provider in {"mock", "local", "ollama"} else FIXTURE_KEY,
    )
    row["config"]["api_version"] = FIXTURE_KEY
    approved = policy(row)
    approved["routes"][0]["api_versions"] = allowed
    if provider != "mock":
        runtime = ModelConfig.from_dict(row["config"])
        assert "anthropic-version" not in headers(runtime, row["api_key"] or None)
        assert not urlsplit(endpoint(runtime)).query
    result = subject.validate_document(document(row), approved)
    assert result.valid is expected
    assert FIXTURE_KEY not in json.dumps(result.public()) + repr(result)
    if expected:
        assert result.entries[0].configuration.config.api_version == FIXTURE_KEY
    else:
        assert any(issue.code == "PROTOCOL_POLICY_MISMATCH" for issue in result.issues)


@pytest.mark.parametrize("version", ["", "authored-version-v1"])
def test_azure_version_policy_matches_actual_query_without_changing_dto(version):
    from generation.providers import endpoint
    from generation.types import ModelConfig
    from urllib.parse import parse_qs, urlsplit

    row = configuration(
        "Azure OpenAI",
        "azure_openai",
        base_url="https://authored-resource.openai.azure.com/openai/v1",
    )
    row["config"]["api_version"] = version
    effective = parse_qs(urlsplit(endpoint(ModelConfig.from_dict(row["config"]))).query).get(
        "api-version", [None]
    )[0]
    approved = policy(row)
    assert approved["routes"][0]["api_versions"] == [effective]
    dto = subject.ModelValues.model_validate(row["config"])
    assert subject._effective_protocol(dto, has_key=True) == ("api-key", effective)
    result = subject.validate_document(document(row), approved)
    if version:
        assert result.valid
        assert result.entries[0].configuration.config.api_version == version
    else:
        # Keep the existing runtime contract: it rejects blank optional metadata.
        assert not result.valid
        assert any(issue.code == "CAPABILITY_OR_CONFIGURATION_INVALID" for issue in result.issues)


@pytest.mark.parametrize("field", ["capabilities", "capability_version"])
def test_partial_capability_metadata_is_rejected(field):
    row = configuration()
    row["config"][field] = {} if field == "capabilities" else "provider_capabilities_v1"
    value = report(row)
    assert any(item["code"] == "CAPABILITY_PAIR_REQUIRED" for item in value["errors"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("temperature", "true"),
        ("seed", 1),
        ("probe_output_tokens", True),
        ("output_token_ceiling", "8192"),
    ],
)
def test_nested_capability_fields_do_not_coerce_primitive_types(field, value):
    from generation.capabilities import VERSION, defaults

    row = configuration()
    row["config"].update(
        capability_version=VERSION, capabilities=defaults("openai", "authored-model-v1")
    )
    row["config"]["capabilities"][field] = value
    result = report(row)
    assert any(item["code"] == "CAPABILITY_TYPE_INVALID" for item in result["errors"])


def test_explicit_capability_parameter_conflict_is_safe_and_has_no_transport(monkeypatch):
    from generation.capabilities import VERSION, defaults

    row = configuration()
    row["config"].update(
        capability_version=VERSION, capabilities=defaults("openai", "authored-model-v1")
    )
    row["config"]["capabilities"]["profile"] = FIXTURE_KEY
    value = report(row)
    assert value["status"] == "invalid"
    assert FIXTURE_KEY not in json.dumps(value)


@pytest.mark.parametrize(
    "text",
    [
        '{"format":"first","format":"' + FIXTURE_KEY + '"}',
        '{"nested":{"' + FIXTURE_KEY + '":1,"' + FIXTURE_KEY + '":2}}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":-Infinity}',
        "[",
        "\ufeff{}",
    ],
)
def test_file_json_errors_do_not_echo_keys_or_source_snippets(tmp_path, text):
    path = tmp_path / "authored-invalid.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(subject.FileValidationFailure) as caught:
        subject.read_json(path)
    assert FIXTURE_KEY not in str(caught.value) + repr(caught.value) + json.dumps(
        caught.value.issue.public()
    )


def test_oversize_file_and_deep_json_are_bounded(tmp_path):
    path = tmp_path / "authored-large.json"
    path.write_bytes(b"x" * (subject.MAX_BYTES + 1))
    with pytest.raises(subject.FileValidationFailure) as caught:
        subject.read_json(path)
    assert caught.value.issue.code == "FILE_SIZE_LIMIT"
    path.write_text("[" * 30 + "0" + "]" * 30, encoding="utf-8")
    with pytest.raises(subject.FileValidationFailure) as caught:
        subject.read_json(path)
    assert caught.value.issue.code == "JSON_DEPTH_LIMIT"


def test_missing_file_directory_relative_path_and_reparse_point_are_safe(tmp_path, monkeypatch):
    for path in (tmp_path / (FIXTURE_KEY + ".json"), tmp_path, Path("relative.json")):
        with pytest.raises(subject.FileValidationFailure) as caught:
            subject.read_json(path)
        assert FIXTURE_KEY not in str(caught.value) + json.dumps(caught.value.issue.public())
    path = write_json(tmp_path / "authored-link.json", {})
    original = Path.lstat

    def linked(candidate, *args, **kwargs):
        if candidate == path:
            return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
        return original(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", linked)
    with pytest.raises(subject.FileValidationFailure) as caught:
        subject.read_json(path)
    assert caught.value.issue.code == "FILE_LINK_REJECTED"


def test_policy_failure_occurs_before_any_private_input_open(tmp_path, monkeypatch):
    approved = policy(configuration())
    approved["reviewed"] = False
    policy_path = write_json(tmp_path / "authored-policy.json", approved)
    input_path = tmp_path / "never-open-authored-input.json"
    opened = []
    original = subject.read_json

    def tracked(path, **kwargs):
        opened.append(path)
        return original(path, **kwargs)

    monkeypatch.setattr(subject, "read_json", tracked)
    with pytest.raises(subject.FileValidationFailure):
        subject.validate_files(input_path, policy_path)
    assert opened == [policy_path]


@pytest.mark.parametrize(
    "field,value",
    [
        ("scheme", {FIXTURE_KEY: FIXTURE_KEY}),
        ("host", [FIXTURE_KEY]),
        ("port", True),
        ("path", {FIXTURE_KEY: FIXTURE_KEY}),
    ],
)
def test_malformed_policy_destination_primitives_have_fixed_safe_errors(field, value):
    row = configuration()
    approved = policy(row)
    approved["routes"][0]["destinations"][0][field] = value
    with pytest.raises(subject.FileValidationFailure) as caught:
        subject.validate_document(document(row), approved)
    assert caught.value.issue.code == "POLICY_DESTINATIONS_INVALID"
    assert FIXTURE_KEY not in str(caught.value) + repr(caught.value) + json.dumps(
        caught.value.issue.public()
    )


def test_no_dns_transport_tokenizer_or_persistence_is_needed(tmp_path, monkeypatch):
    import socket
    from generation import adapters, token_counting

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Offline parser attempted a side effect")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(adapters, "open_provider", forbidden)
    monkeypatch.setattr(token_counting, "TokenCounter", forbidden)
    row = configuration()
    input_path = write_json(tmp_path / "authored-input.json", document(row))
    policy_path = write_json(tmp_path / "authored-policy.json", policy(row))
    assert subject.validate_files(input_path, policy_path).valid


def test_cli_requires_explicit_paths_and_never_echoes_exception_or_argument_values(capsys):
    assert subject.main(["--unexpected", FIXTURE_KEY]) == 2
    output = capsys.readouterr()
    assert FIXTURE_KEY not in output.out + output.err
    assert json.loads(output.out)["errors"][0]["code"] == "CLI_ARGUMENTS_INVALID"


def test_real_module_cli_on_authored_files_outputs_only_safe_aggregate_fields(tmp_path):
    mock = subject.public_drafts()["Explicit authored mock"]
    input_path = write_json(tmp_path / "authored-input.json", document(mock))
    policy_path = write_json(tmp_path / "authored-policy.json", policy(mock))
    snapshot = Path(inspect.getfile(subject.ModelValues)).resolve().parents[4]
    environment = {
        name: value
        for name, value in os.environ.items()
        if not any(
            part in name.upper()
            for part in (
                "API_KEY",
                "API_TOKEN",
                "DATABASE",
                "LLM_",
                "MODEL_CONFIG_KEY",
                "MODEL_CONFIG_ENCRYPTION",
            )
        )
    }
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(HERE), str(HERE / "tests"), str(snapshot), str(snapshot / "backend")]
    )
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "import private_file_subprocess_guard; import runpy; runpy.run_module('scripts.model_configs.private_file', run_name='__main__')",
            "--input",
            str(input_path),
            "--policy",
            str(policy_path),
        ],
        cwd=HERE,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output == {
        "status": "validated_parse_only",
        "configuration_count": 1,
        "validated_count": 1,
        "skipped_count": 0,
        "providers": ["mock"],
        "errors": [],
    }
    assert completed.stderr == ""
    # Exercise real CLI error formatting across the subprocess boundary too.
    approved = policy(configuration())
    write_json(policy_path, approved)
    for defect in ("name", "model", "base_url", "unknown_field", "schema_type"):
        row = configuration()
        if defect == "name":
            row["name"] = FIXTURE_KEY
        elif defect == "unknown_field":
            row["config"][FIXTURE_KEY] = FIXTURE_KEY
        elif defect == "schema_type":
            row["config"]["max_tokens"] = FIXTURE_KEY
        else:
            row["config"][defect] = FIXTURE_KEY
        write_json(input_path, document(row))
        denied = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "import private_file_subprocess_guard; import runpy; runpy.run_module('scripts.model_configs.private_file', run_name='__main__')",
                "--input",
                str(input_path),
                "--policy",
                str(policy_path),
            ],
            cwd=HERE,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert denied.returncode == 2
        assert FIXTURE_KEY not in denied.stdout + denied.stderr
        assert denied.stderr == "" and json.loads(denied.stdout)["status"] == "invalid"
