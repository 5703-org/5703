"""Authored provider outputs exercise the real proposal API and durable PostgreSQL audit."""

from copy import deepcopy
import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.knowledge.models import Document
from app.modules.learning_product.models import LearningRecord
from generation.types import ModelConfig, ProviderResult, failure
from .test_chat_runtime import call
from .test_learning_product import source, draft

TARGET = "app.modules.learning_product.proposals"
CONFIG = ModelConfig(
    provider="openai_compatible",
    model="authored-provider-fixture",
    base_url="https://example.com/v1",
    tokenizer_provider="estimate",
    max_tokens=1024,
)


def submit(rt, body, key=None, status=201):
    return call(
        rt,
        "POST",
        "/admin/learning/practice-proposals",
        body,
        {**rt.headers("admin@example.com"), "Idempotency-Key": key or str(uuid4())},
        status,
    )


def inputs(rt):
    doc, unit = source(rt)
    value = draft(rt, unit)
    body = {key: value[key] for key in ("source", "kind", "concepts", "conditions")}
    return doc, unit, value, body


def receipt(value):
    return ProviderResult(
        raw_text=json.dumps(value),
        provider=CONFIG.provider,
        model=CONFIG.model,
        request_submitted=True,
        usage={
            "input_tokens": 800,
            "output_tokens": 180,
            "total_tokens": 980,
            "cost": None,
            "authorization": "PRIVATE_SECRET_SENTINEL",
        },
    )


def test_proposal_one_call_unpublished_private_rubric_and_idempotent_replay(runtime):
    rt = runtime
    _, _, value, body = inputs(rt)
    key = str(uuid4())
    with (
        patch(TARGET + ".resolve_active_model_config", return_value=CONFIG),
        patch(TARGET + ".LLMAdapter.generate", return_value=receipt(value)) as generate,
    ):
        created = submit(rt, body, key)
        again = submit(rt, body, key, 200)
        assert again["item"]["id"] == created["item"]["id"]
        assert generate.call_count == 1
        changed = {**body, "conditions": ["changed"]}
        submit(rt, changed, key, 409)
    assert created["state"] == "draft"
    assert created["validation_details"]["status"] == "pending"
    assert created["validation_details"]["semantic_correctness_verified"] is None
    assert created["validation_details"]["unmentioned_requested_concepts"] == ["photosynthesis"]
    item_id = created["item"]["id"]
    assert all(row["id"] != item_id for row in call(rt, "GET", "/learning/practice"))
    call(rt, "GET", "/learning/practice/" + item_id, status=404)
    with rt.db() as db:
        audit = db.get(LearningRecord, created["validation_details"]["generation"]["request_id"])
        assert audit.details["status"] == "succeeded"
        assert audit.details["usage"]["total_tokens"] == 980
        assert audit.details["usage"]["cost"] is None
        assert "PRIVATE_SECRET_SENTINEL" not in json.dumps(audit.details)
    admin = rt.headers("admin@example.com")
    validated = call(rt, "POST", f"/admin/learning/practice/{item_id}/validate", headers=admin)
    assert validated["validation_details"]["unmentioned_requested_concepts"] == ["photosynthesis"]
    published = call(
        rt,
        "POST",
        f"/admin/learning/practice/{item_id}/publish",
        {"expected_version": validated["version"], "confirm_source_and_solvability": True},
        admin,
    )
    assert published["state"] == "published"
    public = call(rt, "GET", "/learning/practice/" + item_id)
    assert "PRIVATE_ANSWER_SENTINEL" not in json.dumps(public)
    assert "rubric" not in public


@pytest.mark.parametrize("corruption", ["source", "conditions", "schema", "provider"])
def test_failed_proposals_preserve_audit_and_never_retry_same_key(runtime, corruption):
    rt = runtime
    _, _, value, body = inputs(rt)
    bad = deepcopy(value)
    if corruption == "source":
        bad["source"]["text_hash"] = "0" * 64
    elif corruption == "conditions":
        bad["conditions"] = ["Omit all conditions"]
    elif corruption == "schema":
        bad = {"unable_to_propose": True}
    result = receipt(bad)
    if corruption == "provider":
        result.error = failure("PROVIDER_TIMEOUT", "PRIVATE_SECRET_SENTINEL")
    status = 504 if corruption == "provider" else 422
    key = str(uuid4())
    with (
        patch(TARGET + ".resolve_active_model_config", return_value=CONFIG),
        patch(TARGET + ".LLMAdapter.generate", return_value=result) as generate,
    ):
        submit(rt, body, key, status)
        submit(rt, body, key, status)
        assert generate.call_count == 1
    with rt.db() as db:
        rows = list(
            db.scalars(select(LearningRecord).where(LearningRecord.kind == "practice_proposal"))
        )
        audit = next(
            r for r in rows if r.details["source"]["document_id"] == body["source"]["document_id"]
        )
        assert audit.details["status"] == "failed" and "item_id" not in audit.details
        assert audit.details["usage"]["total_tokens"] == 980
        assert "PRIVATE_SECRET_SENTINEL" not in json.dumps(audit.details)


def test_source_revoked_during_call_prevents_draft_but_preserves_cost(runtime):
    rt = runtime
    doc, _, value, body = inputs(rt)

    def revoke(*args, **kwargs):
        with rt.db() as db:
            db.get(Document, doc["id"]).revoked = True
            db.commit()
        return receipt(value)

    with (
        patch(TARGET + ".resolve_active_model_config", return_value=CONFIG),
        patch(TARGET + ".LLMAdapter.generate", side_effect=revoke) as generate,
    ):
        submit(rt, body, status=410)
        assert generate.call_count == 1
    with rt.db() as db:
        row = next(
            r
            for r in db.scalars(
                select(LearningRecord).where(LearningRecord.kind == "practice_proposal")
            )
            if r.details["source"]["document_id"] == doc["id"]
        )
        assert row.details["status"] == "failed"
        assert row.details["usage"]["total_tokens"] == 980


def test_proposal_admin_permission_and_mock_do_not_call_provider(runtime):
    rt = runtime
    _, _, _, body = inputs(rt)
    with patch(TARGET + ".LLMAdapter.generate") as generate:
        call(
            rt,
            "POST",
            "/admin/learning/practice-proposals",
            body,
            {**rt.headers(), "Idempotency-Key": str(uuid4())},
            403,
        )
        submit(rt, body, status=503)
        assert generate.call_count == 0


def test_proposal_complete_window_overflow_rejected_before_call(runtime):
    from dataclasses import replace

    rt = runtime
    _, _, _, body = inputs(rt)
    with (
        patch(
            TARGET + ".resolve_active_model_config",
            return_value=replace(CONFIG, window_tokens=1024),
        ),
        patch(TARGET + ".LLMAdapter.generate") as generate,
    ):
        submit(rt, body, status=422)
        assert generate.call_count == 0


def test_concurrent_same_key_sees_started_receipt_without_another_paid_attempt(runtime):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    rt = runtime
    _, _, value, body = inputs(rt)
    entered, release = Event(), Event()
    headers = {**rt.headers("admin@example.com"), "Idempotency-Key": str(uuid4())}

    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return receipt(value)

    with (
        patch(TARGET + ".resolve_active_model_config", return_value=CONFIG),
        patch(TARGET + ".LLMAdapter.generate", side_effect=delayed) as generate,
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        pending = pool.submit(
            call, rt, "POST", "/admin/learning/practice-proposals", body, headers, 201
        )
        try:
            assert entered.wait(3)
            call(rt, "POST", "/admin/learning/practice-proposals", body, headers, 409)
        finally:
            release.set()
        assert pending.result()["state"] == "draft"
        assert generate.call_count == 1
