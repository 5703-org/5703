"""Activation projections against disposable SQLite and explicit mock receipts.

These tests never call an external provider. Stored fixture receipts exercise
the same API, persisted contract fingerprints and activation gates as history.
"""

from copy import deepcopy
from pathlib import Path
import re

import pytest
from sqlalchemy import select

from app.db.base import new_uuid, utcnow
from app.modules.identity.models import User
from app.modules.model_settings import compatibility
from app.modules.model_settings.models import (
    ModelCompatibilityRun,
    ModelCompatibilityStage,
    ModelConfiguration,
    ModelConnectionTest,
)
from app.modules.model_settings.schemas import ConnectionTestOut
from app.modules.model_settings.service import as_model_config
from generation import probes
from tests.unit.test_model_settings import (
    ROOT,
    body,
    model_runtime as model_runtime,
    probe_result,
    saved,
)


def _history(runtime, row):
    response = runtime.client.get(f"{ROOT}/{row['id']}/tests", headers=runtime.headers())
    assert response.status_code == 200, response.text
    return {item["id"]: item for item in response.json()["data"]}


def _activate(runtime, row, answer_id, checker_id):
    return runtime.client.post(
        f"{ROOT}/{row['id']}/activate",
        headers=runtime.headers(),
        json={
            "test_id": answer_id,
            "checker_test_id": checker_id,
            "expected_active_version": 0,
        },
    )


def _stored_receipt(
    runtime, row, *, role="answer", changes=None, metadata_change=None, stage_status="passed"
):
    """Create a labelled test receipt without invoking provider transport."""
    with runtime.db() as db:
        config = db.get(ModelConfiguration, row["id"])
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        values = {
            "configuration_id": config.id,
            "tested_by": actor.id,
            "idempotency_key": new_uuid(),
            "input_hash": probes.digest({"fixture": "stored activation receipt"}),
            "role": role,
            "tier": "project",
            "network_label": "authored_local_test_fixture",
            "config_hash": config.config_hash,
            "test_version": probes.VERSION,
            "status": "passed",
            "diagnostic_code": "MOCK_OK",
            "completed_at": utcnow(),
        }
        values.update(changes or {})
        if values["status"] == "running":
            values["completed_at"] = None
        run = ModelCompatibilityRun(**values)
        db.add(run)
        db.flush()
        metadata = deepcopy(
            probes.description(as_model_config(config), "project", role)["metadata"]
        )
        if metadata_change:
            key, value = metadata_change
            metadata[key] = value
        db.add(
            ModelCompatibilityStage(
                run_id=run.id,
                tier="project",
                status=stage_status,
                completed_at=utcnow(),
                metadata_json=metadata,
                result_json={
                    "latency_ms": 0,
                    "usage": {},
                    "diagnostic_code": "MOCK_OK",
                    "request_submitted": False,
                },
            )
        )
        db.commit()
        return run.id


def test_current_role_receipts_enable_existing_pair_without_retest(model_runtime, monkeypatch):
    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    answer = probe_result(runtime, row, tier="project", key="answer-original-once")
    checker = probe_result(
        runtime, row, role="checker", tier="project", key="checker-original-once"
    )
    assert answer["test_version"] == checker["test_version"] == probes.VERSION
    assert answer["activation_eligible"] is checker["activation_eligible"] is True
    # These two hashes have different inputs, including a prefixed model identity.
    assert row["config_hash"] != answer["stages"][0]["metadata"]["configuration_hash"]

    def no_retest(*_args, **_kwargs):
        pytest.fail("Eligibility reads and activation must reuse the saved receipts")

    monkeypatch.setattr(probes, "run", no_retest)
    replay = probe_result(runtime, row, tier="project", key="answer-original-once")
    assert replay["id"] == answer["id"] and replay["activation_eligible"] is True
    history = _history(runtime, row)
    assert history[answer["id"]]["activation_eligible"] is True
    assert history[checker["id"]]["activation_eligible"] is True
    state = runtime.client.get(ROOT, headers=runtime.headers()).json()["data"]
    current = next(item for item in state["items"] if item["id"] == row["id"])
    assert current["latest_answer_test"]["activation_eligible"] is True
    assert current["latest_checker_test"]["activation_eligible"] is True
    response = _activate(runtime, row, answer["id"], checker["id"])
    assert response.status_code == 200, response.text
    assert response.json()["data"]["active_configuration_id"] == row["id"]
    assert response.json()["data"]["active_version"] == 1
    assert len(_history(runtime, row)) == 2


@pytest.mark.parametrize("status", ["failed", "uncertain", "running"])
def test_nonpassing_run_never_has_activation_eligibility(model_runtime, status):
    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    answer_id = _stored_receipt(runtime, row, changes={"status": status})
    checker_id = _stored_receipt(runtime, row, role="checker")
    assert _history(runtime, row)[answer_id]["activation_eligible"] is False
    assert _activate(runtime, row, answer_id, checker_id).status_code == 409


@pytest.mark.parametrize("stage_status", ["failed", "not_run"])
def test_passed_run_without_passed_project_stage_remains_ineligible(model_runtime, stage_status):
    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    answer_id = _stored_receipt(runtime, row, stage_status=stage_status)
    checker_id = _stored_receipt(runtime, row, role="checker")
    receipt = _history(runtime, row)[answer_id]
    assert receipt["project_passed"] is receipt["activation_eligible"] is False
    assert _activate(runtime, row, answer_id, checker_id).status_code == 409


@pytest.mark.parametrize("latest_tier", ["basic", "structured"])
def test_newer_nonproject_receipt_invalidates_prior_pass(model_runtime, latest_tier):
    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    old = probe_result(runtime, row, tier="project")
    checker = probe_result(runtime, row, role="checker", tier="project")
    new = probe_result(runtime, row, tier=latest_tier)
    assert new["status"] == "passed" and new["activation_eligible"] is False
    history = _history(runtime, row)
    assert history[old["id"]]["project_passed"] is True
    assert history[old["id"]]["activation_eligible"] is False
    assert _activate(runtime, row, old["id"], checker["id"]).status_code == 409


@pytest.mark.parametrize(
    "changes",
    [{"config_hash": "0" * 64}, {"test_version": "provider_probe_v3"}],
    ids=["different-saved-hash", "old-protocol"],
)
def test_stale_hash_or_protocol_receipt_remains_visible_but_ineligible(model_runtime, changes):
    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    answer_id = _stored_receipt(runtime, row, changes=changes)
    checker_id = _stored_receipt(runtime, row, role="checker")
    receipt = _history(runtime, row)[answer_id]
    assert receipt["project_passed"] is True and receipt["activation_eligible"] is False
    assert _activate(runtime, row, answer_id, checker_id).status_code == 409


@pytest.mark.parametrize(
    "metadata_change",
    [
        ("schema_hash", "0" * 64),
        ("prompt_hash", "0" * 64),
        ("configuration_hash", "0" * 64),
        ("capability_hash", "0" * 64),
        ("reserved_output_tokens", 1),
        ("effective_parameters", {}),
    ],
    ids=["schema", "prompt", "configuration", "capability", "output", "parameters"],
)
def test_each_current_contract_fingerprint_gates_projection_and_activation(
    model_runtime, metadata_change
):
    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    answer_id = _stored_receipt(runtime, row, metadata_change=metadata_change)
    checker_id = _stored_receipt(runtime, row, role="checker")
    receipt = _history(runtime, row)[answer_id]
    assert receipt["project_passed"] is True and receipt["activation_eligible"] is False
    response = _activate(runtime, row, answer_id, checker_id)
    assert response.status_code == 409 and "schema or probe policy changed" in response.text


def test_different_model_configuration_and_role_do_not_share_eligibility(model_runtime):
    runtime = model_runtime
    first = saved(runtime, body(secret=None))
    different_body = body(secret=None)
    different_body["config"]["model"] = "different-authored-model"
    second = saved(runtime, different_body)
    answer_id = _stored_receipt(runtime, first)
    checker_id = _stored_receipt(runtime, second, role="checker")
    with runtime.db() as db:
        first_config = db.get(ModelConfiguration, first["id"])
        second_config = db.get(ModelConfiguration, second["id"])
        answer_run = db.get(ModelCompatibilityRun, answer_id)
        checker_run = db.get(ModelCompatibilityRun, checker_id)
        assert compatibility.output(db, answer_run, second_config)["activation_eligible"] is False
        assert (
            compatibility._project_pass_error(db, first_config, answer_run, "checker") is not None
        )
        assert (
            compatibility._project_pass_error(db, second_config, checker_run, "answer") is not None
        )
    assert _activate(runtime, second, answer_id, checker_id).status_code == 409
    assert _activate(runtime, first, checker_id, answer_id).status_code == 409


def test_legacy_connection_receipt_defaults_ineligible(model_runtime):
    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    with runtime.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        legacy = ModelConnectionTest(
            configuration_id=row["id"],
            status="passed",
            diagnostic_code="MOCK_OK",
            message="Historical authored connection fixture",
            latency_ms=0,
            usage={},
            tested_by=actor.id,
        )
        db.add(legacy)
        db.commit()
        legacy_id = legacy.id
    receipt = _history(runtime, row)[legacy_id]
    assert receipt["test_version"] == "legacy_connection_v1"
    assert receipt["project_passed"] is receipt["activation_eligible"] is False


def test_invalid_runtime_contract_projects_false_and_keeps_conflict(model_runtime, monkeypatch):
    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    answer_id = _stored_receipt(runtime, row)
    checker_id = _stored_receipt(runtime, row, role="checker")

    def unavailable_description(*_args, **_kwargs):
        raise ValueError("Authored local invalid-contract test")

    monkeypatch.setattr(probes, "description", unavailable_description)
    assert _history(runtime, row)[answer_id]["activation_eligible"] is False
    response = _activate(runtime, row, answer_id, checker_id)
    assert response.status_code == 409 and "current runtime contract" in response.text


def test_frontend_probe_version_tracks_actual_backend_protocol():
    project = Path(__file__).resolve().parents[2]
    models = (project / "frontend/src/Models.tsx").read_text(encoding="utf-8")
    declaration = re.findall(
        r"export const CURRENT_PROVIDER_PROBE_VERSION\s*=\s*['\"]([^'\"]+)['\"]", models
    )
    assert declaration == [probes.VERSION]
    field = ConnectionTestOut.model_json_schema()["properties"]["activation_eligible"]
    assert field == {"default": False, "title": "Activation Eligible", "type": "boolean"}
