"""Validate and import source-pinned relation proposals through administrator APIs."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from contracts.study import ConceptRelationAdminOut, ConceptRelationProposal, SourceLocator


CATALOG_VERSION = "openstax_concept_relation_candidates_v1"


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_catalog(path: Path) -> dict:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog.get("version") != CATALOG_VERSION or catalog.get("auto_approve") is not False:
        raise ValueError("Use a supported proposed-only relation catalog.")
    items = catalog.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError("The relation catalog needs between one and 100 candidates.")
    identities = set()
    for item in items:
        proposal = ConceptRelationProposal.model_validate(item["proposal"])
        identity = (
            proposal.source.release_id,
            proposal.document_id,
            proposal.from_section_id,
            proposal.to_section_id,
            proposal.relation_type,
        )
        if identity in identities or proposal.from_section_id == proposal.to_section_id:
            raise ValueError("Each candidate must have distinct sections and a unique relation.")
        identities.add(identity)
        if (
            item["evidence"].get("quote_sha256") != sha256(proposal.source_quote)
            or item["evidence"].get("original_pdf_normalized_quote_match") is not True
            or item["evidence"].get("source_unit_hash_exact") is not True
            or item["evidence"].get("source_locator_exact") is not True
            or item["curation"].get("subject_review_status") != "pending"
            or item["curation"].get("recommended_registry_state") != "proposed"
            or item["curation"].get("independent_human_ratings") != 0
        ):
            raise ValueError("Candidate quotation or proposed-only provenance is invalid.")
        if proposal.source.release_id != catalog.get("release_id"):
            raise ValueError("Every candidate must use the pinned catalog release.")
    return catalog


def relation_key(proposal: dict) -> tuple:
    return (
        proposal.get("release_id") or proposal["source"]["release_id"],
        proposal["document_id"],
        proposal["from_section_id"],
        proposal["to_section_id"],
        proposal["relation_type"],
    )


def proposal_payload(proposal: dict) -> dict:
    value = ConceptRelationProposal.model_validate(proposal).model_dump()
    for field in ("from_concept", "to_concept", "reason"):
        value[field] = value[field].strip()
    return value


def admin_row(value: dict) -> dict:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("source"), dict)
        or set(value["source"]) != set(SourceLocator.model_fields)
    ):
        raise ValueError(
            "The administrator relation response needs all seven source locator fields."
        )
    try:
        row = ConceptRelationAdminOut.model_validate(value).model_dump()
    except ValidationError:
        raise ValueError("The administrator relation response is incomplete or invalid.") from None
    if (
        not row["id"]
        or not row["proposer_id"]
        or row["version"] < 1
        or row["release_id"] != row["source"]["release_id"]
        or row["document_id"] != row["source"]["document_id"]
        or row["source_quote_hash"] != sha256(row["source_quote"])
    ):
        raise ValueError("The administrator relation response has an inconsistent identity.")
    return row


def matching_row(item: dict, value: dict) -> dict:
    row = admin_row(value)
    payload = {field: row[field] for field in ConceptRelationProposal.model_fields}
    if (
        proposal_payload(payload) != proposal_payload(item["proposal"])
        or row["source_quote_hash"] != item["evidence"]["quote_sha256"]
    ):
        raise ValueError(
            "The relation response has a different proposal payload; review it explicitly."
        )
    return row


def existing_rows(values: list) -> dict:
    if not isinstance(values, list) or len(values) >= 200:
        raise ValueError("The administrator relation listing is invalid or may be incomplete.")
    existing = {}
    for value in values:
        row = admin_row(value)
        if row["state"] in {"proposed", "approved"}:
            key = relation_key(row)
            if key in existing:
                raise ValueError(
                    "The administrator relation listing contains duplicate active keys."
                )
            existing[key] = row
    return existing


def check_existing(catalog: dict, existing: dict) -> None:
    # Check every retry before the first create, including callers that skip preflight.
    for item in catalog["items"]:
        prior = existing.get(relation_key(item["proposal"]))
        if prior is not None:
            row = matching_row(item, prior)
            if row["state"] not in {"proposed", "approved"}:
                raise ValueError("An existing relation is not an active proposed or approved row.")


def response_data(response: httpx.Response):
    try:
        value = response.json()
    except ValueError:
        raise ValueError("The administrator/source response is not valid JSON.") from None
    if not isinstance(value, dict) or "data" not in value:
        raise ValueError("The administrator/source response has no data envelope.")
    return value["data"]


def data(client: httpx.Client, path: str, *, params: dict | None = None):
    response = client.get(path, params=params)
    if response.status_code != 200:
        raise ValueError(f"Administrator/source preflight returned HTTP {response.status_code}.")
    return response_data(response)


def preflight(client: httpx.Client, catalog: dict) -> dict:
    # This authenticated role check also supplies existing proposed/approved rows.
    existing = existing_rows(data(client, "/admin/learning/concept-relations"))
    check_existing(catalog, existing)
    books = {book["id"]: book for book in data(client, "/learning/library")}
    section_cache = {}
    unit_cache = {}
    for item in catalog["items"]:
        proposal, evidence = item["proposal"], item["evidence"]
        source = proposal["source"]
        book = books.get(proposal["document_id"])
        if (
            book is None
            or book["release_id"] != source["release_id"]
            or book["source_sha256"] != evidence["original_pdf_sha256"]
            or book["processing_id"] != source["processing_id"]
        ):
            raise ValueError("The pinned official book/release differs from this installation.")
        document_id = proposal["document_id"]
        if document_id not in section_cache:
            section_cache[document_id] = {
                section["id"]: section
                for section in data(client, f"/learning/library/{document_id}/sections")
            }
        sections = section_cache[document_id]
        if {proposal["from_section_id"], proposal["to_section_id"]} - sections.keys():
            raise ValueError("A proposed endpoint section is absent from the pinned book.")
        cache_key = (document_id, source["source_unit_id"])
        if cache_key not in unit_cache:
            page = data(
                client,
                f"/learning/library/{document_id}/units",
                params={"source_unit_id": source["source_unit_id"], "limit": 50},
            )
            unit_cache[cache_key] = next(
                (unit for unit in page["items"] if unit["id"] == source["source_unit_id"]), None
            )
        unit = unit_cache[cache_key]
        if unit is None:
            raise ValueError("The pinned source unit is unavailable.")
        start, end = source["start"], source["end"]
        if (
            unit["locator"]["text_hash"] != source["text_hash"]
            or sha256(unit["text"]) != source["text_hash"]
            or unit["page"] != evidence["physical_page"]
            or not 0 <= start < end <= len(unit["text"])
            or unit["text"][start:end] != proposal["source_quote"]
        ):
            raise ValueError("The exact pinned source quotation or physical page differs.")
    return existing


def submit(
    client: httpx.Client, catalog: dict, existing: dict, results: list[dict] | None = None
) -> list[dict]:
    results = results if results is not None else []
    check_existing(catalog, existing)
    for item in catalog["items"]:
        proposal = item["proposal"]
        key = relation_key(proposal)
        prior = existing.get(key)
        if prior is not None:
            prior = matching_row(item, prior)
            results.append(
                {
                    "candidate_id": item["candidate_id"],
                    "status": "existing",
                    "registry_id": prior["id"],
                    "registry_state": prior["state"],
                    "registry_version": prior["version"],
                }
            )
            continue
        response = client.post("/admin/learning/concept-relations", json=proposal)
        if response.status_code != 201:
            raise ValueError(f"Proposal import returned HTTP {response.status_code}.")
        row = matching_row(item, response_data(response))
        if (
            row["state"] != "proposed"
            or row["version"] != 1
            or any(
                row[field] is not None for field in ("reviewer_id", "reviewed_at", "review_note")
            )
        ):
            raise ValueError("The imported relation did not retain its proposed-only identity.")
        results.append(
            {
                "candidate_id": item["candidate_id"],
                "status": "created",
                "registry_id": row["id"],
                "registry_state": row["state"],
                "registry_version": row["version"],
            }
        )
        existing[key] = row
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--mode", choices=("validate", "preflight", "submit"), default="validate")
    parser.add_argument("--api-url", help="API root, for example http://127.0.0.1:8000/api/v1")
    parser.add_argument(
        "--token-env",
        default="CS30_ADMIN_TOKEN",
        help="Environment variable holding an administrator bearer token",
    )
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    catalog = load_catalog(args.catalog)
    receipt = {
        "version": "concept_relation_import_receipt_v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "catalog_sha256": hashlib.sha256(args.catalog.read_bytes()).hexdigest(),
        "scheduled_candidates": len(catalog["items"]),
        "by_type": dict(Counter(item["proposal"]["relation_type"] for item in catalog["items"])),
        "provider_calls": 0,
        "approval_calls": 0,
        "independent_human_ratings": 0,
        "results": [],
    }
    try:
        if args.mode != "validate":
            address = urlsplit(args.api_url or "")
            token = os.getenv(args.token_env)
            if (
                address.scheme not in {"http", "https"}
                or not address.hostname
                or address.username
                or address.password
                or address.query
                or address.fragment
                or not token
            ):
                raise ValueError(
                    "Provide a valid API URL and an administrator token through the named environment variable."
                )
            with httpx.Client(
                base_url=args.api_url.rstrip("/"),
                headers={"Authorization": "Bearer " + token},
                timeout=60,
            ) as client:
                existing = preflight(client, catalog)
                if args.mode == "submit":
                    submit(client, catalog, existing, receipt["results"])
        receipt["status"] = "passed"
    except (ValueError, httpx.HTTPError) as exc:
        receipt["status"] = "failed"
        receipt["error_type"] = type(exc).__name__
        # Exception details and response bodies may contain deployment data.
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(
            "Concept relation import failed; inspect the private runtime logs."
        ) from None
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "mode": args.mode,
                "scheduled_candidates": len(catalog["items"]),
                "created": sum(row["status"] == "created" for row in receipt["results"]),
                "approvals": 0,
                "receipt": str(args.receipt),
            }
        )
    )


if __name__ == "__main__":
    main()
