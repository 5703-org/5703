"""Real PostgreSQL/API checks using authored disposable catalog fixtures only."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from app.core.security import hash_password
from app.modules.identity.models import User, Workspace
from app.modules.knowledge.models import Document, DocumentVersion
from app.modules.learning_product import visual_catalog_versions as service
from app.modules.learning_product import visual_catalog_router
from tests.integration.test_visual_catalog_versions import _count
from tests.integration.test_visual_catalog_versions import bundle  # noqa: F401

PREFIX = "/api/v1/admin/source-quality/catalog-versions"
CHECKS = {name: True for name in service.REVIEW_CHECKS}


@pytest.fixture
def catalog_api(runtime, bundle):  # noqa: F811 - pytest injects the imported fixture
    runtime.settings.visual_catalog_staging_root = str(bundle["directory"].parent)
    runtime.settings.storage_root = str(bundle["storage_root"])
    with runtime.db() as db:
        reviewer = db.get(User, bundle["reviewer_id"])
        reviewer.email = f"catalog-review-{uuid4().hex}@example.com"
        reviewer.hashed_password = hash_password("Passw0rd!")
        reviewer_email = reviewer.email
        workspace = Workspace(name="Authored other workspace", slug=uuid4().hex)
        db.add(workspace)
        db.flush()
        outsider = User(
            email=f"other-admin-{uuid4().hex}@example.com",
            hashed_password=hash_password("Passw0rd!"),
            role_id=reviewer.role_id,
            workspace_id=workspace.id,
        )
        db.add(outsider)
        db.commit()
        outsider_email = outsider.email
    return {
        "runtime": runtime,
        "bundle": bundle,
        "admin": runtime.headers("admin@example.com"),
        "reviewer": runtime.headers(reviewer_email),
        "outsider": runtime.headers(outsider_email),
    }


def _import(context, **changes):
    return context["runtime"].client.post(
        PREFIX + "/imports",
        headers=context["admin"],
        json={
            "bundle_name": context["bundle"]["directory"].name,
            "expected_manifest_sha256": context["bundle"]["manifest_hash"],
            **changes,
        },
    )


def _staged(context):
    response = _import(context)
    assert response.status_code == 200, response.text
    return response.json()["data"]["items"]


def _state(context, catalog, expected, state, actor="admin"):
    return context["runtime"].client.post(
        PREFIX + f"/{catalog}/state",
        headers=context[actor],
        json={"expected_version": expected, "state": state},
    )


def _review(context, catalog, region, **changes):
    return context["runtime"].client.post(
        PREFIX + f"/{catalog}/candidates/{region}/reviews",
        headers=context["reviewer"],
        json={
            "previous_review_id": None,
            "decision": "needs_more",
            "checks": CHECKS,
            "evidence": "Authored disposable fixture review; no actual human approval.",
            **changes,
        },
    )


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("get", "", None),
        ("post", "/imports", {"bundle_name": "catalogs", "expected_manifest_sha256": "a" * 64}),
        ("get", "/unavailable", None),
        ("get", "/unavailable/candidates", None),
        ("get", "/unavailable/candidates/" + "a" * 64, None),
        ("post", "/unavailable/state", {"expected_version": 1, "state": "under_review"}),
        (
            "post",
            "/unavailable/candidates/" + "a" * 64 + "/reviews",
            {
                "previous_review_id": None,
                "decision": "needs_more",
                "checks": CHECKS,
                "evidence": "Authored disposable fixture review.",
            },
        ),
    ],
)
def test_every_route_requires_admin(runtime, method, suffix, body):
    args = {"json": body} if body is not None else {}
    response = runtime.client.request(method, PREFIX + suffix, **args)
    assert response.status_code == 401
    response = runtime.client.request(method, PREFIX + suffix, headers=runtime.headers(), **args)
    assert response.status_code == 403


def test_import_idempotence_listing_raw_payload_and_legacy_preservation(catalog_api):
    context, runtime = catalog_api, catalog_api["runtime"]
    with runtime.db() as db:
        legacy = (
            db.execute(text("SELECT to_jsonb(v) FROM visual_regions v ORDER BY id")).scalars().all()
        )
    imported = _staged(context)
    assert len(imported) == 4 and sum(item["added"] for item in imported) == 12
    assert all(item["state"] == "staged" for item in imported)
    assert all(item["counts"]["formula_candidate"] == 0 for item in imported)
    assert all(
        item["review_history_counts"] == {"accepted": 0, "rejected": 0, "needs_more": 0}
        for item in imported
    )
    assert all(
        item["published"] is False and item["answer_evidence_eligible"] is False
        for item in imported
    )
    assert _import(context).json()["data"]["added_candidates"] == 0
    listed = runtime.client.get(PREFIX + "?limit=2", headers=context["admin"])
    assert listed.status_code == 200 and listed.json()["data"]["next_offset"] == 2
    catalog = imported[0]
    assert catalog["book"] == catalog["document_title"] == "Authored fixture 0"
    assert (
        catalog["source_active"] is True and catalog["importer_id"] == context["bundle"]["admin_id"]
    )
    candidate_page = runtime.client.get(
        PREFIX + f"/{catalog['id']}/candidates?limit=2", headers=context["admin"]
    )
    assert candidate_page.status_code == 200
    assert len(candidate_page.json()["data"]["items"]) == 2
    assert candidate_page.json()["data"]["next_offset"] == 2
    region = candidate_page.json()["data"]["items"][0]
    detail = runtime.client.get(
        PREFIX + f"/{catalog['id']}/candidates/{region['region_id']}", headers=context["admin"]
    )
    assert detail.status_code == 200
    payload = detail.json()["data"]
    assert payload["latest_review"] is None
    assert payload["raw_payload"]["source_sha256"] == catalog["source_sha256"]
    assert payload["raw_payload"]["details"]["previous_region_id"] == region["previous_region_id"]
    assert payload["raw_payload"]["details"]["raw_native_glyphs"][0]["baseline"] == 10.25
    with runtime.db() as db:
        assert (
            legacy
            == db.execute(text("SELECT to_jsonb(v) FROM visual_regions v ORDER BY id"))
            .scalars()
            .all()
        )
        assert _count(db, service.VisualCatalogReview, context["bundle"]) == 0


@pytest.mark.parametrize(
    "name",
    ["../catalogs", "a..b", "/catalogs", "C:\\catalogs", "a/b", "a\\b", ".", "catalogs\n", "目录"],
)
def test_import_rejects_paths_and_non_basename_names(catalog_api, name):
    assert _import(catalog_api, bundle_name=name).status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"expected_manifest_sha256": "A" * 64},
        {"expected_manifest_sha256": "a" * 63},
        {"actor_id": "arbitrary"},
    ],
)
def test_import_strict_body(catalog_api, changes):
    assert _import(catalog_api, **changes).status_code == 422


def test_manifest_hash_mismatch_is_atomic(catalog_api):
    context, runtime = catalog_api, catalog_api["runtime"]
    assert _import(context, expected_manifest_sha256="0" * 64).status_code == 422
    with runtime.db() as db:
        assert _count(db, service.VisualCatalogVersion, context["bundle"]) == 0


def test_oversized_manifest_is_rejected_before_decoding(catalog_api):
    path = catalog_api["bundle"]["directory"] / "SOURCE_MANIFEST.json"
    path.write_bytes(b" " * 1_048_577)
    assert _import(catalog_api).status_code == 422


def test_source_failure_after_prior_books_rolls_back_complete_import(catalog_api):
    context, runtime = catalog_api, catalog_api["runtime"]
    original = context["bundle"]["storage_root"] / "fixture-3.pdf"
    original.write_bytes(original.read_bytes() + b"authored corruption fixture")
    response = _import(context)
    assert response.status_code == 503
    with runtime.db() as db:
        assert _count(db, service.VisualCatalogVersion, context["bundle"]) == 0
        assert _count(db, service.VisualCatalogCandidate, context["bundle"]) == 0


@pytest.mark.parametrize("part", ["bundle", "manifest"])
def test_resolved_link_escape_is_rejected(catalog_api, monkeypatch, tmp_path, part):
    """Inject the filesystem resolution a link escape produces on either OS."""
    context = catalog_api
    target = context["bundle"]["directory"]
    checked = target if part == "bundle" else target / "SOURCE_MANIFEST.json"
    outside = tmp_path / "outside" / checked.name
    resolve = Path.resolve

    def resolved(path, *args, **kwargs):
        if path == checked:
            return outside
        return resolve(path, *args, **kwargs)

    monkeypatch.setattr(visual_catalog_router.Path, "resolve", resolved)
    assert _import(context).status_code == 422


def test_workspace_scope_hides_existing_sources_and_candidates(catalog_api):
    context, runtime = catalog_api, catalog_api["runtime"]
    catalog = _staged(context)[0]
    region = context["bundle"]["v3_ids"][0]
    assert runtime.client.get(PREFIX, headers=context["outsider"]).json()["data"]["items"] == []
    for suffix in ("", "/candidates", f"/candidates/{region}"):
        assert (
            runtime.client.get(
                PREFIX + f"/{catalog['id']}" + suffix, headers=context["outsider"]
            ).status_code
            == 404
        )
    assert _state(context, catalog["id"], 1, "under_review", "outsider").status_code == 404
    response = runtime.client.post(
        PREFIX + "/imports",
        headers=context["outsider"],
        json={
            "bundle_name": context["bundle"]["directory"].name,
            "expected_manifest_sha256": context["bundle"]["manifest_hash"],
        },
    )
    assert response.status_code == 404


def test_state_cas_self_review_and_unapproved_activation(catalog_api):
    context = catalog_api
    catalog = _staged(context)[0]
    assert _state(context, catalog["id"], 2, "under_review").status_code == 409
    assert _state(context, catalog["id"], 1, "active").status_code == 422
    under_review = _state(context, catalog["id"], 1, "under_review")
    assert under_review.status_code == 200 and under_review.json()["data"]["version"] == 2
    assert _state(context, catalog["id"], 2, "active").status_code == 422
    response = context["runtime"].client.post(
        PREFIX + f"/{catalog['id']}/candidates/{context['bundle']['v3_ids'][0]}/reviews",
        headers=context["admin"],
        json={
            "previous_review_id": None,
            "decision": "accepted",
            "checks": CHECKS,
            "evidence": "Authored disposable fixture; importer cannot independently review.",
        },
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "changes", [{"expected_version": True}, {"expected_version": "1"}, {"actor_id": "arbitrary"}]
)
def test_state_transition_strict_body(catalog_api, changes):
    context = catalog_api
    catalog = _staged(context)[0]
    response = context["runtime"].client.post(
        PREFIX + f"/{catalog['id']}/state",
        headers=context["admin"],
        json={"expected_version": 1, "state": "under_review", **changes},
    )
    assert response.status_code == 422


def test_independent_append_only_review_cas_and_active_remains_unpublished(catalog_api):
    context, runtime = catalog_api, catalog_api["runtime"]
    catalog = _staged(context)[0]
    region = context["bundle"]["v3_ids"][0]
    assert _state(context, catalog["id"], 1, "under_review").status_code == 200
    first = _review(context, catalog["id"], region)
    assert first.status_code == 200, first.text
    first_id = first.json()["data"]["review_id"]
    assert first.json()["data"]["catalog_version"]["version"] == 3
    assert _review(context, catalog["id"], region).status_code == 409
    detail = runtime.client.get(
        PREFIX + f"/{catalog['id']}/candidates/{region}", headers=context["reviewer"]
    )
    assert detail.json()["data"]["latest_review"]["id"] == first_id
    accepted = _review(
        context, catalog["id"], region, previous_review_id=first_id, decision="accepted"
    )
    assert accepted.status_code == 200, accepted.text
    current = accepted.json()["data"]["catalog_version"]
    assert current["review_history_counts"] == {"accepted": 1, "needs_more": 1, "rejected": 0}
    active = _state(context, catalog["id"], current["version"], "active")
    assert active.status_code == 200
    assert active.json()["data"]["published"] is False
    assert active.json()["data"]["answer_evidence_eligible"] is False
    with runtime.db() as db:
        candidate = db.scalar(
            select(service.VisualCatalogCandidate).where(
                service.VisualCatalogCandidate.region_id == region
            )
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(service.VisualCatalogReview)
                .where(service.VisualCatalogReview.candidate_id == candidate.id)
            )
            == 2
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"checks": {**CHECKS, "content_correct": "true"}},
        {"checks": {key: value for key, value in CHECKS.items() if key != "content_correct"}},
        {"reviewer_id": "arbitrary"},
        {"evidence": "short"},
        {"previous_review_id": "not-a-review"},
    ],
)
def test_review_strict_checks_and_no_actor_spoof(catalog_api, changes):
    context = catalog_api
    catalog = _staged(context)[0]
    assert _state(context, catalog["id"], 1, "under_review").status_code == 200
    assert (
        _review(context, catalog["id"], context["bundle"]["v3_ids"][0], **changes).status_code
        == 422
    )


def test_incomplete_structure_cannot_receive_acceptance(catalog_api):
    context = catalog_api
    catalog = _staged(context)[0]
    assert _state(context, catalog["id"], 1, "under_review").status_code == 200
    assert (
        _review(
            context, catalog["id"], context["bundle"]["v3_ids"][1], decision="accepted"
        ).status_code
        == 422
    )


def test_withdrawn_source_metadata_remains_but_raw_review_and_activation_stop(catalog_api):
    context, runtime = catalog_api, catalog_api["runtime"]
    catalog = _staged(context)[0]
    region = context["bundle"]["v3_ids"][0]
    assert _state(context, catalog["id"], 1, "under_review").status_code == 200
    with runtime.db() as db:
        version = db.get(DocumentVersion, catalog["document_version_id"])
        document = db.get(Document, version.document_id)
        document.revoked = True
        db.commit()
    metadata = runtime.client.get(PREFIX + f"/{catalog['id']}", headers=context["admin"])
    assert metadata.status_code == 200 and metadata.json()["data"]["source_active"] is False
    for suffix in ("/candidates", f"/candidates/{region}"):
        assert (
            runtime.client.get(
                PREFIX + f"/{catalog['id']}" + suffix, headers=context["admin"]
            ).status_code
            == 503
        )
    assert _review(context, catalog["id"], region).status_code == 503
    assert _state(context, catalog["id"], 2, "active").status_code == 503
    assert _state(context, catalog["id"], 2, "withdrawn").status_code == 200


@pytest.mark.parametrize("query", ["offset=-1", "limit=0", "limit=101", "offset=1.5"])
def test_pagination_validation(catalog_api, query):
    assert (
        catalog_api["runtime"]
        .client.get(PREFIX + "?" + query, headers=catalog_api["admin"])
        .status_code
        == 422
    )
