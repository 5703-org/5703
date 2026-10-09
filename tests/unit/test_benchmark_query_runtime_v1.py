"""Authored software contracts; no official corpus or semantic ratings."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from generation import benchmark_query_runtime_v1 as policy
from retrieval.runtime import query_execution_config, resolve_device


def configuration(device="cpu", *, declared=True):
    values = {"top_k": 5}
    if declared:
        values[policy.CONFIGURATION_FIELD] = {"version": policy.VERSION, "device": device}
    return SimpleNamespace(
        id="immutable-configuration-one",
        kind="evaluation",
        values=values,
        content_hash=policy.digest({"kind": "evaluation", "values": values}),
    )


@pytest.mark.parametrize("device", sorted(policy.DEVICES))
def test_declared_device_is_frozen_with_exact_origin_and_round_trips(device):
    original = configuration(device)
    before = deepcopy(original.__dict__)
    frozen = policy.freeze(original)
    command = {"question": "A public question", policy.COMMAND_FIELD: frozen}
    assert policy.validate(command, original) == frozen
    assert policy.requested_device(command) == device
    assert original.__dict__ == before
    assert set(frozen) == {"version", "device", "configuration_id", "configuration_hash"}


def test_missing_old_configuration_and_command_retain_recorded_without_hash_rewrite():
    old = configuration(declared=False)
    old.content_hash = "a historical content identity"
    assert policy.freeze(old) is None
    assert policy.freeze(None) is None
    assert policy.validate({"question": "Legacy question"}, old) is None
    assert policy.requested_device({}) == "recorded"
    assert old.content_hash == "a historical content identity"


@pytest.mark.parametrize("value", [None, False, [], "CPU", "gpu", "cuda:1", {"device": "cpu"}])
def test_unknown_device_is_rejected(value):
    with pytest.raises(ValueError, match="Unsupported"):
        policy.freeze(configuration(value))


@pytest.mark.parametrize(
    "raw", [None, [], "cpu", {}, {"version": policy.VERSION, "device": "cpu", "extra": 1}]
)
def test_declaration_has_exact_shape(raw):
    cfg = configuration()
    cfg.values[policy.CONFIGURATION_FIELD] = raw
    with pytest.raises(ValueError, match="exact version/device"):
        policy.freeze(cfg)


def test_changed_device_or_configuration_content_cannot_keep_old_hash():
    cfg = configuration()
    cfg.values[policy.CONFIGURATION_FIELD]["device"] = "auto"
    with pytest.raises(ValueError, match="content hash changed"):
        policy.freeze(cfg)


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", "unknown"),
        ("device", "auto"),
        ("configuration_id", "foreign"),
        ("configuration_hash", "foreign"),
    ],
)
def test_replay_rejects_changed_frozen_identity(field, value):
    cfg = configuration()
    frozen = {**policy.freeze(cfg), field: value}
    with pytest.raises(ValueError, match="differs"):
        policy.validate({policy.COMMAND_FIELD: frozen}, cfg)


def test_missing_explicit_policy_or_unexpected_old_policy_fails_closed():
    cfg = configuration()
    with pytest.raises(ValueError, match="missing"):
        policy.validate({}, cfg)
    with pytest.raises(ValueError, match="differs"):
        policy.validate({policy.COMMAND_FIELD: policy.freeze(cfg)}, configuration(declared=False))


def test_cpu_query_execution_preserves_full_recorded_cuda_model_identity():
    recorded = {
        "embedding_provider": "e5",
        "embedding_model": "intfloat/e5-small-v2",
        "embedding_revision": "fixed-revision",
        "embedding_device": "cuda",
        "embedding_dimension": 384,
        "query_prefix": "query: ",
        "normalise": True,
    }
    before = deepcopy(recorded)
    resolved = resolve_device(
        policy.requested_device({policy.COMMAND_FIELD: policy.freeze(configuration())})
    )
    executed = query_execution_config(recorded, resolved)
    assert resolved == "cpu" and executed["embedding_device"] == "cpu"
    assert recorded == before
    assert {k: v for k, v in executed.items() if k != "embedding_device"} == {
        k: v for k, v in before.items() if k != "embedding_device"
    }
    assert query_execution_config(recorded) == before
