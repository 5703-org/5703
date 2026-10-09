"""Retrospective, source-anchored audit of the frozen Week 9 retrieval set.

This deliberately leaves semantic point support and context sufficiency unlabelled.
It verifies what official evidence was accepted, prepares private review packets,
and publishes aggregate provenance without turning inspected V8 data into a new
formal V10 result. Standard-library only; no database or model calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SCHEMA = "week09_source_sufficiency_development_audit_v1"
SOURCE_KIND = "official_openstax"
SOURCE_HOST = "assets.openstax.org"
FAMILIES = {"textbook_qa", "joint_tutoring"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def official_source(value: dict, *, raw_hashes: dict[str, str], release_id: str) -> None:
    require(value.get("source_kind") == SOURCE_KIND, "Reference is not an official source")
    require(value.get("release_id") == release_id, "Reference release differs")
    require(value.get("source_title") in raw_hashes, "Reference has an unknown book")
    require(
        value.get("original_sha256") == raw_hashes[value["source_title"]],
        "Reference original PDF hash differs",
    )
    require(
        urlparse(value.get("source_url", "")).hostname == SOURCE_HOST,
        "Reference URL differs",
    )
    require(
        sha256_text(value["text"]) == value.get("text_hash"),
        "Reference text hash differs",
    )
    require(
        isinstance(value.get("pages"), list)
        and value["pages"]
        and all(type(page) is int and page > 0 for page in value["pages"]),
        "Reference pages are invalid",
    )


def evidence_identity(value: dict) -> tuple[str, str, str, tuple[int, ...]]:
    return (
        value["chunk_id"],
        value["text_hash"],
        value["source_title"],
        tuple(value["pages"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue", type=Path, required=True)
    parser.add_argument("--qa-preparation", type=Path, required=True)
    parser.add_argument("--teaching-preparation", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--runtime-parity", type=Path, required=True)
    parser.add_argument("--originals-dir", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    args = parser.parse_args()
    require(args.private_output != args.public_output, "Outputs must differ")
    require(
        not args.private_output.exists(),
        "Private output already exists; preserve prior run",
    )
    require(
        not args.public_output.exists(),
        "Public output already exists; preserve prior run",
    )

    input_paths = {
        "catalogue": args.catalogue,
        "qa_preparation": args.qa_preparation,
        "teaching_preparation": args.teaching_preparation,
        "preflight": args.preflight,
        "runtime_parity": args.runtime_parity,
    }
    input_hashes = {name: sha256_file(path) for name, path in input_paths.items()}
    catalogue = load(args.catalogue)
    qa = load(args.qa_preparation)
    teaching = load(args.teaching_preparation)
    preflight = load(args.preflight)
    runtime = load(args.runtime_parity)
    require(
        catalogue.get("schema") == "week09_continuation_v1_catalogue",
        "Wrong catalogue schema",
    )
    require(
        catalogue.get("split") == "reserved",
        "Expected frozen reserved source catalogue",
    )
    require(
        catalogue.get("independent_human_reference_reviews") == 0,
        "Unexpected label state",
    )
    require(
        preflight.get("schema") == "week09_reserved_v3_selected_evidence_anchor_audit",
        "Wrong preflight schema",
    )
    require(
        preflight.get("catalogue_sha256") == input_hashes["catalogue"],
        "Preflight catalogue differs",
    )
    require(runtime.get("status") == "passed", "Runtime archive verification is not passed")
    raw_hashes = {item["title"]: item["raw_sha256"] for item in runtime["corpus"]["official_pdfs"]}
    require(len(raw_hashes) == 4, "Expected four distinct official PDFs")
    require(
        all(
            item.get("final_payload_hash_matches_official_record") is True
            for item in runtime["corpus"]["official_pdfs"]
        ),
        "Final archive does not verify every original PDF",
    )
    local_pdf_hashes = {}
    for title, expected in sorted(raw_hashes.items()):
        original = args.originals_dir / f"{expected}.pdf"
        require(original.is_file(), f"Original PDF unavailable: {title}")
        actual = sha256_file(original)
        require(actual == expected, f"Original PDF bytes differ: {title}")
        local_pdf_hashes[title] = actual

    release_id = catalogue["source_release_id"]
    require(release_id == runtime["corpus"]["active_release_id"], "Active release differs")
    require(len(catalogue["cases"]) == 104, "Expected 104 frozen source cases")
    for preparation in (qa, teaching):
        require(
            preparation.get("schema") == "week09_real_source_preparation_v1",
            "Wrong preparation schema",
        )
        require(
            preparation.get("corpus_unchanged") is True,
            "Preparation changed the corpus",
        )
        require(preparation.get("provider_calls") == 0, "Preparation had provider calls")
        require(preparation.get("runtime_device") == "cpu", "Preparation did not use CPU")
        corpus = preparation["corpus"]
        require(corpus["release_id"] == release_id, "Preparation release differs")
        require(
            corpus["vectors"] == runtime["corpus"]["active_vectors"],
            "Vector count differs",
        )
        require(
            corpus["dimension_min"] == corpus["dimension_max"] == runtime["corpus"]["dimension"],
            "Vector dimensions differ",
        )
    require(qa["corpus"] == teaching["corpus"], "QA/teaching corpus metadata differ")

    authored = catalogue["cases"]
    case_ids = [case["id"] for case in authored]
    require(len(set(case_ids)) == len(case_ids), "Repeated catalogue case")
    prepared = qa["cases"] + teaching["cases"]
    prepared_by_id = {case["id"]: case for case in prepared}
    require(
        len(prepared_by_id) == 104 and set(prepared_by_id) == set(case_ids),
        "Prepared case membership differs",
    )
    require(
        {case["id"] for case in qa["cases"]}
        == {case["id"] for case in authored if case["family"] == "textbook_qa"},
        "QA preparation membership differs",
    )
    require(
        {case["id"] for case in teaching["cases"]}
        == {case["id"] for case in authored if case["family"] == "joint_tutoring"},
        "Teaching preparation membership differs",
    )

    point_count = 0
    selected_evidence = 0
    unique_evidence = set()
    warning_codes = Counter()
    structural_case_pass = Counter()
    structural_point_bucket = Counter()
    by_book = defaultdict(lambda: Counter())
    groups = defaultdict(dict)
    private_cases = []
    anchor_count = 0
    matched_anchor_count = 0
    for case in authored:
        require(case["family"] in FAMILIES, "Unknown family")
        require(case["split"] == "reserved", "Case split changed")
        require(
            case.get("label_provenance") in {"ai_generated", "program_derived", "human_existing"},
            "Case label provenance absent",
        )
        points = case["required_points"]
        require(
            isinstance(points, list)
            and points
            and all(isinstance(point, str) and point.strip() for point in points),
            "Required points invalid",
        )
        require(case["source_anchors"], "Case lacks declared official anchor")
        preparation = prepared_by_id[case["id"]]
        require(preparation["id"] == case["id"], "Case identifier differs")
        require(preparation["source_anchors"], "Prepared reference source set empty")
        # QA uses the original question; tutoring prepared a subject-centred retrieval query.
        if case["family"] == "textbook_qa":
            require(preparation["question"] == case["task"]["question"], "QA query changed")
        selected = preparation["retrieval"]["evidence"]
        require(isinstance(selected, list), "Accepted evidence missing")
        identity_map = {}
        for passage in selected:
            require(
                sha256_text(passage["text"]) == passage["text_hash"],
                "Accepted passage text hash differs",
            )
            require(
                urlparse(passage["source_url"]).hostname == SOURCE_HOST,
                "Accepted passage URL differs",
            )
            require(passage["source_title"] in raw_hashes, "Accepted passage book differs")
            require(
                isinstance(passage["pages"], list) and passage["pages"],
                "Accepted passage pages absent",
            )
            key = evidence_identity(passage)
            require(key not in identity_map, "Duplicate accepted evidence identity")
            identity_map[key] = passage
            selected_evidence += 1
            unique_evidence.add(key)
            warning_codes.update(
                str(row.get("code", "unknown")) for row in passage.get("quality_warnings", [])
            )
        anchors = []
        all_present = True
        for anchor in case["source_anchors"]:
            official_source(anchor, raw_hashes=raw_hashes, release_id=release_id)
            anchor_count += 1
            key = evidence_identity(anchor)
            match = identity_map.get(key)
            if match is not None:
                require(
                    match["text"] == anchor["text"],
                    "Accepted source bytes differ from reference",
                )
                require(
                    match["source_url"] == anchor["source_url"],
                    "Accepted source URL differs from reference",
                )
                matched_anchor_count += 1
            else:
                all_present = False
            anchors.append(
                {
                    "chunk_id": anchor["chunk_id"],
                    "text_hash": anchor["text_hash"],
                    "official_pdf_sha256": anchor["original_sha256"],
                    "source_title": anchor["source_title"],
                    "section": anchor["section"],
                    "pages": anchor["pages"],
                    "source_url": anchor["source_url"],
                    "text": anchor["text"],
                    "selected_exact_source": match is not None,
                }
            )
        point_rows = []
        for index, point in enumerate(points, start=1):
            point_rows.append(
                {
                    "point_id": sha256_text(f"{case['id']}:{index}:{point}")[:20],
                    "order": index,
                    "authored_required_point": point,
                    "declared_anchor_set_present_in_accepted_evidence": all_present,
                    "semantic_point_supported_by_accepted_evidence": None,
                    "point_label_origin": case["label_provenance"],
                    "independent_semantic_review": None,
                }
            )
        point_count += len(point_rows)
        structural_point_bucket[
            "declared_anchor_set_present" if all_present else "declared_anchor_set_missing"
        ] += len(point_rows)
        structural_case_pass[
            "declared_anchor_set_present" if all_present else "declared_anchor_set_missing"
        ] += 1
        book = case["source_anchors"][0]["source_title"]
        require(
            all(anchor["source_title"] == book for anchor in case["source_anchors"]),
            "Case spans unexpected books",
        )
        by_book[book]["cases"] += 1
        by_book[book]["required_points"] += len(points)
        by_book[book][
            "declared_anchor_set_present" if all_present else "declared_anchor_set_missing"
        ] += 1
        groups[case["concept_group"]][case["family"]] = all_present
        private_cases.append(
            {
                "case_id": case["id"],
                "concept_group": case["concept_group"],
                "family": case["family"],
                "book": book,
                "task": case["task"],
                "actual_retrieval_question": preparation["question"],
                "authored_required_points": point_rows,
                "authored_unsupported_conclusions": case["unsupported_conclusions"],
                "declared_anchors": anchors,
                "accepted_evidence": [
                    {
                        "chunk_id": e["chunk_id"],
                        "text_hash": e["text_hash"],
                        "source_title": e["source_title"],
                        "section": e["section"],
                        "pages": e["pages"],
                        "source_url": e["source_url"],
                        "text": e["text"],
                        "quality_warnings": e.get("quality_warnings", []),
                    }
                    for e in selected
                ],
                "declared_anchor_set_present_in_accepted_evidence": all_present,
                "semantic_context_sufficient": None,
                "semantic_citation_support": None,
                "human_reviewer": None,
                "review_status": "unreviewed",
            }
        )

    require(len(groups) == 52, "Expected 52 paired concept groups")
    require(
        all(set(value) == FAMILIES for value in groups.values()),
        "Concept pairing incomplete",
    )
    paired_pass = sum(all(value.values()) for value in groups.values())
    require(
        paired_pass == preflight["paired_eligible_group_count"],
        "Paired anchor count differs from frozen preflight",
    )
    require(
        len(groups) == preflight["paired_group_count"],
        "Paired group denominator differs",
    )
    require(
        structural_case_pass["declared_anchor_set_missing"] == preflight["failed_case_count"],
        "Missed case count differs",
    )
    require(point_count == 257, "Authored required-point count differs")
    require(selected_evidence == 1166, "Selected-passage count differs")

    public = {
        "schema": SCHEMA,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "retrospective source-frozen development audit; not a new V10 formal outcome or learner answer-quality score",
        "inputs_sha256": input_hashes,
        "original_pdf_hashes_verified_against_local_bytes": local_pdf_hashes,
        "source_release_id": release_id,
        "frozen_corpus_vectors": qa["corpus"]["vectors"],
        "frozen_vector_dimension": qa["corpus"]["dimension_min"],
        "runtime_device_in_frozen_preparations": "cpu",
        "new_database_queries": 0,
        "new_embedding_or_answer_model_calls": 0,
        "catalogue_case_count": len(authored),
        "paired_concept_groups": len(groups),
        "paired_declared_anchor_set_present": paired_pass,
        "paired_declared_anchor_set_missing": len(groups) - paired_pass,
        "accepted_passages_observed": selected_evidence,
        "unique_accepted_passage_identities": len(unique_evidence),
        "declared_official_anchor_instances": anchor_count,
        "declared_official_anchor_instances_selected_exactly": matched_anchor_count,
        "structural_cases": dict(structural_case_pass),
        "authored_required_points": point_count,
        "required_points_grouped_by_anchor_set_presence": dict(structural_point_bucket),
        "selected_passage_quality_warnings": dict(warning_codes),
        "by_book": {book: dict(counts) for book, counts in sorted(by_book.items())},
        "semantic_point_support": {"evaluated": 0, "unknown": point_count},
        "semantic_context_sufficiency": {"evaluated": 0, "unknown": len(authored)},
        "independent_human_reference_reviews": 0,
        "existing_catalogue_label_origin": "authored; not independent human gold",
        "interpretation": "An exact official reference passage in accepted evidence is a source-identity and retrieval fact. It does not show that every required point is present, that the whole context is sufficient, or that a generated answer used it correctly. All semantic fields remain null until separate review.",
        "private_review_packet_sha256": None,
    }
    private = {
        "schema": SCHEMA + "_private_review_packets",
        "inputs_sha256": input_hashes,
        "label_scope": "authored reference points and actual frozen CPU accepted passages; unreviewed semantic fields are null",
        "cases": private_cases,
    }
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    with args.private_output.open("x", encoding="utf-8") as stream:
        json.dump(private, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
    public["private_review_packet_sha256"] = sha256_file(args.private_output)
    with args.public_output.open("x", encoding="utf-8") as stream:
        json.dump(public, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    print(
        json.dumps(
            {
                "status": "passed",
                "case_count": len(authored),
                "required_points": point_count,
                "paired_anchor_pass": paired_pass,
                "semantic_labels": 0,
                "public_output": str(args.public_output),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
