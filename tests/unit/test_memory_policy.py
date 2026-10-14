"""Bounded real policy files and frozen default/legacy policy identities."""

import io
import json
from pathlib import Path

import pytest

from personalisation import memory_policy, memory_v3, memory_v4, memory_v5
from personalisation.memory_v2 import MemoryPreparationUnavailable


def policy_file(tmp_path, raw):
    path = tmp_path / "memory-policy.json"
    path.write_bytes(raw)
    return path


def unavailable(path):
    with pytest.raises(MemoryPreparationUnavailable) as caught:
        memory_policy.load_policy(path)
    assert caught.value.code == "MEMORY_POLICY_UNAVAILABLE"
    assert str(path) not in str(caught.value)


def test_unconfigured_policy_remains_semantic_off(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("An unconfigured policy must not read a file")

    monkeypatch.setattr(Path, "open", forbidden)
    for path in (None, ""):
        assert memory_policy.load_policy(path) == memory_v5.freeze_policy()


@pytest.mark.parametrize("size", [65536, 65537])
def test_actual_byte_limit_includes_trailing_whitespace(tmp_path, size):
    raw = json.dumps(memory_v3.freeze_policy()).encode()
    path = policy_file(tmp_path, raw + b" " * (size - len(raw)))
    if size == 65536:
        assert memory_policy.load_policy(path) == memory_v3.freeze_policy()
    else:
        unavailable(path)


def test_actual_read_is_bounded_without_relying_on_stat(tmp_path, monkeypatch):
    raw = json.dumps(memory_v3.freeze_policy()).encode()
    requested = []

    class Stream(io.BytesIO):
        def read(self, size=-1):
            requested.append(size)
            return super().read(size)

    monkeypatch.setattr(Path, "open", lambda *a, **k: Stream(raw))
    monkeypatch.setattr(Path, "stat", lambda *a, **k: pytest.fail("Stat is not a read bound"))
    assert memory_policy.load_policy(tmp_path / "changing-file") == memory_v3.freeze_policy()
    assert requested == [64 * 1024 + 1]


def test_growth_beyond_cap_is_rejected_before_json_parse(tmp_path, monkeypatch):
    requested = []

    class GrowingStream(io.BytesIO):
        def read(self, size=-1):
            requested.append(size)
            return super().read(size)

    monkeypatch.setattr(Path, "open", lambda *a, **k: GrowingStream(b"x" * 70000))
    unavailable(tmp_path / "grown-file")
    assert requested == [65537]


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"{invalid",
        b"\xff",
        b"null",
        b"[]",
        b"NaN",
        b"Infinity",
        b"[" * 1100 + b"0" + b"]" * 1100,
    ],
)
def test_malformed_config_is_explicitly_unavailable(tmp_path, raw):
    unavailable(policy_file(tmp_path, raw))


def test_duplicate_keys_cannot_hide_enabled_or_nested_identity(tmp_path):
    raw = json.dumps(memory_v3.freeze_policy()).replace(
        '"enabled": false', '"enabled": true, "enabled": false'
    )
    unavailable(policy_file(tmp_path, raw.encode()))
    raw = json.dumps(memory_v3.freeze_policy()).replace(
        '"dimension": 384', '"dimension": 768, "dimension": 384'
    )
    unavailable(policy_file(tmp_path, raw.encode()))


@pytest.mark.parametrize(
    "change", [{"enabled": "false"}, {"version": "unknown"}, {"max_scopes": 25}, {"enabled": True}]
)
def test_invalid_policy_identity_never_defaults_to_another_selector(tmp_path, change):
    policy = memory_v3.freeze_policy()
    policy.update(change)
    unavailable(policy_file(tmp_path, json.dumps(policy).encode()))


def test_missing_file_is_unavailable(tmp_path):
    unavailable(tmp_path / "absent-policy.json")


def test_explicit_legacy_policy_retains_recorded_identity(tmp_path):
    policy = memory_v3.freeze_policy()
    policy["version"] = memory_v3.LEGACY_POLICY_VERSION
    del policy["rule_scope_version"]
    assert memory_policy.load_policy(policy_file(tmp_path, json.dumps(policy).encode())) == policy
