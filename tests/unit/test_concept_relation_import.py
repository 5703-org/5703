"""A proposed-only import must reject quote tampering and record partial success."""

from copy import deepcopy
import json
from pathlib import Path

import httpx
import pytest

from scripts.release.import_concept_relations import (
    load_catalog,
    preflight,
    relation_key,
    sha256,
    submit,
)


CATALOG = (
    Path(__file__).resolve().parents[2]
    / "configs/knowledge/openstax_concept_relation_candidates_v1.json"
)


def saved_row(item, *, identity="labelled-import-fixture", state="proposed", version=1):
    row = deepcopy(item["proposal"])
    for field in ("from_concept", "to_concept", "reason"):
        row[field] = row[field].strip()
    row.update(
        id=identity,
        release_id=row["source"]["release_id"],
        source_quote_hash=sha256(row["source_quote"]),
        state=state,
        proposer_id="labelled-admin-fixture",
        reviewer_id=None if state == "proposed" else "labelled-reviewer-fixture",
        reviewed_at=None if state == "proposed" else "2026-10-03T00:00:00+00:00",
        review_note=None if state == "proposed" else "Explicitly authored software review fixture.",
        version=version,
    )
    return row


def catalog_fixture(count=1):
    catalog = deepcopy(load_catalog(CATALOG))
    catalog["items"] = catalog["items"][:count]
    return catalog


def source_preflight_fixture(catalog, rows, requests):
    # Authored transport units exercise exact-range checks, without database or network access.
    books, sections, units = {}, {}, {}
    for item in catalog["items"]:
        proposal = item["proposal"]
        source = proposal["source"]
        source.update(start=0, end=len(proposal["source_quote"]))
        source["text_hash"] = sha256(proposal["source_quote"])
        document_id = proposal["document_id"]
        books[document_id] = dict(
            id=document_id,
            release_id=source["release_id"],
            processing_id=source["processing_id"],
            source_sha256=item["evidence"]["original_pdf_sha256"],
        )
        sections.setdefault(document_id, set()).update(
            (proposal["from_section_id"], proposal["to_section_id"])
        )
        units[source["source_unit_id"]] = dict(
            id=source["source_unit_id"],
            locator={"text_hash": source["text_hash"]},
            text=proposal["source_quote"],
            page=item["evidence"]["physical_page"],
        )

    def handler(request):
        requests.append((request.method, request.url.path))
        assert request.method == "GET"
        if request.url.path == "/admin/learning/concept-relations":
            payload = rows
        elif request.url.path == "/learning/library":
            payload = list(books.values())
        elif request.url.path.endswith("/sections"):
            document_id = request.url.path.split("/")[-2]
            payload = [{"id": identity} for identity in sections[document_id]]
        else:
            assert request.url.path.endswith("/units")
            payload = {"items": [units[request.url.params["source_unit_id"]]]}
        return httpx.Response(200, json={"data": payload})

    return httpx.Client(base_url="http://offline-fixture", transport=httpx.MockTransport(handler))


def test_official_candidate_catalog_is_limited_source_pinned_and_pending():
    catalog = load_catalog(CATALOG)
    assert len(catalog["items"]) == 12
    assert {item["proposal"]["relation_type"] for item in catalog["items"]} == {
        "prerequisite",
        "related",
        "confusion",
    }
    assert len({item["evidence"]["book"] for item in catalog["items"]}) == 4
    assert catalog["independent_human_ratings"] == 0 and catalog["auto_approve"] is False
    assert all(item["evidence"]["chunk_fragments"] for item in catalog["items"])


@pytest.mark.parametrize(
    "mutation", ["quote", "auto_approve", "same_section", "human_rating", "pdf_mismatch"]
)
def test_catalog_validation_refuses_tampering_or_implied_approval(tmp_path, mutation):
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    item = catalog["items"][0]
    if mutation == "quote":
        item["proposal"]["source_quote"] += " A fabricated addition."
    elif mutation == "auto_approve":
        catalog["auto_approve"] = True
    elif mutation == "same_section":
        item["proposal"]["to_section_id"] = item["proposal"]["from_section_id"]
    elif mutation == "human_rating":
        item["curation"]["independent_human_ratings"] = 1
    else:
        item["evidence"]["original_pdf_normalized_quote_match"] = False
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(ValueError):
        load_catalog(path)


def test_partial_import_records_created_proposals_and_never_calls_review():
    catalog = deepcopy(load_catalog(CATALOG))
    catalog["items"] = catalog["items"][:2]
    paths = []

    def handler(request):
        paths.append(request.url.path)
        assert request.method == "POST"
        if len(paths) == 2:
            return httpx.Response(409, json={"error": {"code": "CONFLICT"}})
        proposal = json.loads(request.content)
        item = {"proposal": proposal}
        return httpx.Response(
            201,
            json={"data": saved_row(item)},
        )

    results = []
    with httpx.Client(
        base_url="http://localhost/api/v1", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ValueError, match="HTTP 409"):
            submit(client, catalog, {}, results)
    assert len(results) == 1 and results[0]["registry_state"] == "proposed"
    assert results[0]["registry_version"] == 1
    assert paths == ["/api/v1/admin/learning/concept-relations"] * 2
    assert all("review" not in path for path in paths)


@pytest.mark.parametrize("state,version", [("proposed", 1), ("approved", 2)])
def test_exact_existing_retry_matches_production_trim_without_post_or_mutation(state, version):
    catalog = catalog_fixture()
    item = catalog["items"][0]
    row = saved_row(item, state=state, version=version)
    before = deepcopy(row)
    for field in ("from_concept", "to_concept", "reason"):
        item["proposal"][field] = "  " + item["proposal"][field] + "  "
    requests = []

    def forbidden(request):
        requests.append(request)
        pytest.fail("An unchanged retry must not create or review a row.")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        results = submit(client, catalog, {relation_key(row): row})
    assert results == [
        dict(
            candidate_id=item["candidate_id"],
            status="existing",
            registry_id=row["id"],
            registry_state=state,
            registry_version=version,
        )
    ]
    assert requests == [] and row == before


@pytest.mark.parametrize(
    "field",
    [
        "reason",
        "from_concept",
        "to_concept",
        "source.release_id",
        "source.document_id",
        "source.processing_id",
        "source.source_unit_id",
        "source.text_hash",
        "source.start",
        "source.end",
    ],
)
def test_same_quote_different_payload_conflicts_before_any_create(field):
    catalog = catalog_fixture(2)
    item = catalog["items"][1]
    row = saved_row(item)
    key = relation_key(row)
    if field.startswith("source."):
        name = field.split(".")[1]
        value = row["source"][name]
        row["source"][name] = value + 1 if isinstance(value, int) else value + "-changed"
    else:
        row[field] += " Deliberately changed fixture content."
    requests = []

    def forbidden(request):
        requests.append(request)
        pytest.fail("Every existing payload must be checked before the first create.")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        with pytest.raises(ValueError):
            submit(client, catalog, {key: row})
    assert requests == []


@pytest.mark.parametrize("problem", ["duplicate", "capped", "over_cap", "invalid_row"])
def test_preflight_rejects_duplicate_capped_or_invalid_registry_before_other_requests(problem):
    catalog = catalog_fixture()
    requests, rows = [], []
    with source_preflight_fixture(catalog, rows, requests) as client:
        row = saved_row(catalog["items"][0])
        if problem == "duplicate":
            rows.extend([row, dict(row, id="second-active-fixture")])
        elif problem in {"capped", "over_cap"}:
            rows.extend(
                dict(row, id=f"fixture-{i}") for i in range(200 if problem == "capped" else 201)
            )
        else:
            rows.append({"id": "incomplete-fixture"})
        with pytest.raises(ValueError):
            preflight(client, catalog)
    assert requests == [("GET", "/admin/learning/concept-relations")]


def test_preflight_checks_later_existing_payload_before_submission():
    catalog = catalog_fixture(2)
    requests, rows = [], []
    with source_preflight_fixture(catalog, rows, requests) as client:
        row = saved_row(catalog["items"][1])
        row["reason"] += " A different saved reason."
        rows.append(row)
        with pytest.raises(ValueError, match="different proposal payload"):
            preflight(client, catalog)
    assert requests == [("GET", "/admin/learning/concept-relations")]


def test_preflight_retains_exact_current_source_checks_and_unchanged_existing_row():
    catalog = catalog_fixture()
    requests, rows = [], []
    with source_preflight_fixture(catalog, rows, requests) as client:
        row = saved_row(catalog["items"][0])
        rows.append(row)
        existing = preflight(client, catalog)
    assert existing == {relation_key(row): row}
    assert len(requests) == 4 and all(method == "GET" for method, _ in requests)


@pytest.mark.parametrize(
    "problem",
    [
        "missing_field",
        "extra_field",
        "reason",
        "concept",
        "locator",
        "release",
        "quote_hash",
        "approved",
        "reviewer",
        "review_time",
        "review_note",
        "version",
        "string_version",
        "empty_identity",
        "no_envelope",
        "invalid_json",
    ],
)
def test_created_response_must_match_complete_pending_payload(problem):
    catalog = catalog_fixture()
    row = saved_row(catalog["items"][0])
    if problem == "missing_field":
        del row["source"]
    elif problem == "extra_field":
        row["unexpected"] = "unexpected fixture field"
    elif problem == "reason":
        row["reason"] += " Different saved response."
    elif problem == "concept":
        row["to_concept"] += " changed"
    elif problem == "locator":
        row["source"]["start"] += 1
    elif problem == "release":
        row["release_id"] += "-changed"
    elif problem == "quote_hash":
        row["source_quote_hash"] = "0" * 64
    elif problem == "approved":
        row = saved_row(catalog["items"][0], state="approved", version=2)
    elif problem == "reviewer":
        row["reviewer_id"] = "unexpected-reviewer"
    elif problem == "review_time":
        row["reviewed_at"] = "2026-10-03T00:00:00+00:00"
    elif problem == "review_note":
        row["review_note"] = "Unexpected review metadata."
    elif problem == "version":
        row["version"] = 2
    elif problem == "string_version":
        row["version"] = "1"
    elif problem == "empty_identity":
        row["id"] = ""
    requests = []

    def handler(request):
        requests.append((request.method, request.url.path))
        if problem == "invalid_json":
            return httpx.Response(201, content=b"not JSON")
        payload = [] if problem == "no_envelope" else {"data": row}
        return httpx.Response(201, json=payload)

    receipts, existing = [], {}
    with httpx.Client(
        base_url="http://offline-fixture", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ValueError):
            submit(client, catalog, existing, receipts)
    assert receipts == [] and existing == {}
    assert requests == [("POST", "/admin/learning/concept-relations")]


@pytest.mark.parametrize("missing_field", ["start", "end"])
def test_created_response_cannot_fill_omitted_locator_fields_from_schema_defaults(missing_field):
    catalog = catalog_fixture()
    catalog["items"][0]["proposal"]["source"].update(start=0, end=None)
    row = saved_row(catalog["items"][0])
    del row["source"][missing_field]

    def handler(request):
        assert request.method == "POST" and request.url.path == "/admin/learning/concept-relations"
        return httpx.Response(201, json={"data": row})

    with httpx.Client(
        base_url="http://offline-fixture", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ValueError, match="all seven source locator fields"):
            submit(client, catalog, {})


def test_complete_default_valued_locator_response_is_valid():
    catalog = catalog_fixture()
    catalog["items"][0]["proposal"]["source"].update(start=0, end=None)
    row = saved_row(catalog["items"][0])

    def handler(request):
        assert request.method == "POST" and request.url.path == "/admin/learning/concept-relations"
        return httpx.Response(201, json={"data": row})

    with httpx.Client(
        base_url="http://offline-fixture", transport=httpx.MockTransport(handler)
    ) as client:
        results = submit(client, catalog, {})
    assert results[0]["status"] == "created" and results[0]["registry_version"] == 1


def test_six_related_successor_keys_are_distinct_from_all_twelve_originals():
    # This authored type-change matrix has no dependency on private curation files.
    catalog = load_catalog(CATALOG)
    originals = {relation_key(item["proposal"]) for item in catalog["items"]}
    selected = {"AP-01", "AP-03", "BIO-01", "BIO-03", "CHEM-03", "CON-03"}
    successors = []
    for item in catalog["items"]:
        if item["candidate_id"] in selected:
            proposal = deepcopy(item["proposal"])
            assert proposal["relation_type"] in {"prerequisite", "confusion"}
            proposal["relation_type"] = "related"
            successors.append(relation_key(proposal))
    assert len(originals) == 12 and len(successors) == len(set(successors)) == 6
    assert originals.isdisjoint(successors)
