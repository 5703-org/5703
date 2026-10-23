"""Focused offline integration controls; authored sources are not semantic gold.

Staging draft for the Main owner to copy and run after integration.py is ready.
No provider, worker, API, database, model, browser or budget operations are used.
"""

from copy import deepcopy
from dataclasses import replace
import hashlib
import unittest
from unittest.mock import patch

from generation.prompt_builder import build_messages as native_build_messages
from generation.token_counting import TokenCounter
from generation.types import GenerationRequest, ModelConfig
from retrieval.prerequisite_context_v1.integration import (
    prepare_context,
    validate_selected_context,
)
from retrieval.source_spans import map_fragments as native_map_fragments

SOURCE_POLICY = "raw_corroborated_prose_context_candidate_v1"
CONTEXT_POLICY = "literal_coverage_complementary_context_candidate_v1"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fixture(count=1, body=None):
    body = body or "Water can cross a membrane. Cell volume can change."
    full = "Prefix 🙂. " + body + " Tail."
    start = full.index(body)
    end = start + len(body)
    rows, mapping = [], {}
    for index in range(1, count + 1):
        chunk = f"authored-c{index}"
        rows.append(
            {
                "evidence_id": f"ev_{index:03d}",
                "chunk_id": chunk,
                "asset_id": "authored-document",
                "processing_id": "authored-processing",
                "source_title": "Authored public mechanics fixture",
                "source_url": "https://assets.openstax.org/authored-control.pdf",
                "license": "Authored test fixture",
                "locator": "Authored unit",
                "section": "Authored section",
                "pages": [1],
                "context_order": index,
                "inherited_from": None,
                "text": body,
                "text_hash": digest(body),
            }
        )
        mapping[chunk] = {
            "asset_id": "authored-document",
            "processing_id": "authored-processing",
            "document_version_id": "authored-version",
            "chunk_text": full,
            "chunk_hash": digest(full),
            "submitted_start": start,
            "submitted_end": end,
            "units": [
                {
                    "id": f"authored-u{index}",
                    "page": 1,
                    "cleaned_text": full,
                    "text_hash": digest(full),
                }
            ],
            "spans": [
                {
                    "unit_id": f"authored-u{index}",
                    "page": 1,
                    "start": 0,
                    "end": len(full),
                    "chunk_start": 0,
                    "chunk_end": len(full),
                }
            ],
        }
    request = GenerationRequest(
        request_id="authored-request",
        mode="interactive_chat",
        condition="E1",
        question="How does water crossing a membrane change cell volume?",
        evidence=rows,
        source_map=deepcopy(mapping),
        config=ModelConfig(window_tokens=65536, tokenizer_provider="estimate"),
        source_block_policy=SOURCE_POLICY,
        generation_context_policy=CONTEXT_POLICY,
    )
    return request, mapping


def keep_all(evidence, fragments, question, understanding=None, source_map=None):
    """A transparent authored selector; the production packer remains unchanged."""
    ranges = {
        item["chunk_id"]: {
            "submitted_start": source_map[item["chunk_id"]]["submitted_start"],
            "submitted_end": source_map[item["chunk_id"]]["submitted_end"],
        }
        for item in evidence
    }
    return deepcopy(evidence), ranges, [], {"producer": "authored_keep_all"}


def cropped(request, mapping, excerpt="Cell volume can change."):
    original = request.evidence[0]
    item = deepcopy(original)
    item.update(text=excerpt, text_hash=digest(excerpt))
    start = mapping[item["chunk_id"]]["chunk_text"].index(excerpt)
    ranges = {item["chunk_id"]: {"submitted_start": start, "submitted_end": start + len(excerpt)}}
    return [item], ranges


class PrerequisiteIntegrationTests(unittest.TestCase):
    def setUp(self):
        def denied(*args, **kwargs):
            raise AssertionError("Focused context integration controls cannot use network or DNS")

        for name in ("socket", "create_connection", "getaddrinfo"):
            guard = patch("socket." + name, side_effect=denied)
            guard.start()
            self.addCleanup(guard.stop)

    def test_absolute_crop_is_relative_to_original_submitted_start(self):
        request, mapping = fixture()
        selected, ranges = cropped(request, mapping)
        before = deepcopy((selected, ranges, request.evidence, mapping))
        self.assertGreater(mapping[selected[0]["chunk_id"]]["submitted_start"], 0)
        validate_selected_context(selected, ranges, request.evidence, mapping)
        self.assertEqual((selected, ranges, request.evidence, mapping), before)

    def test_absolute_range_cannot_escape_already_admitted_excerpt(self):
        request, mapping = fixture()
        selected, ranges = cropped(request, mapping)
        chunk = selected[0]["chunk_id"]
        escaped = mapping[chunk]["chunk_text"][:6]
        selected[0].update(text=escaped, text_hash=digest(escaped))
        ranges[chunk] = {"submitted_start": 0, "submitted_end": 6}
        with self.assertRaises(ValueError):
            validate_selected_context(selected, ranges, request.evidence, mapping)

    def test_duplicate_original_chunk_ids_are_rejected(self):
        request, mapping = fixture()
        selected, ranges = cropped(request, mapping)
        duplicate = deepcopy(request.evidence[0])
        duplicate["evidence_id"] = "ev_002"
        with self.assertRaises(ValueError):
            validate_selected_context(selected, ranges, [*request.evidence, duplicate], mapping)

    def test_duplicate_original_evidence_ids_are_rejected(self):
        request, mapping = fixture(count=2)
        selected, ranges = cropped(request, mapping)
        admitted = deepcopy(request.evidence)
        admitted[1]["evidence_id"] = admitted[0]["evidence_id"]
        with self.assertRaises(ValueError):
            validate_selected_context(selected, ranges, admitted, mapping)

    def test_duplicate_selected_chunk_or_evidence_ids_are_rejected(self):
        request, mapping = fixture(count=2)
        selected, ranges = cropped(request, mapping)
        for duplicate in (
            deepcopy(selected[0]),
            {**deepcopy(request.evidence[1]), "evidence_id": selected[0]["evidence_id"]},
        ):
            with self.subTest(chunk=duplicate["chunk_id"]):
                with self.assertRaises(ValueError):
                    validate_selected_context(
                        [*selected, duplicate], ranges, request.evidence, mapping
                    )

    def test_all_existing_identity_metadata_is_immutable(self):
        request, mapping = fixture()
        selected, ranges = cropped(request, mapping)
        changes = {
            "evidence_id": "ev_999",
            "asset_id": "private-document",
            "processing_id": "foreign-processing",
            "source_title": "Changed title",
            "source_url": "https://private.invalid/source",
            "pages": [99],
            "section": "Changed section",
            "locator": "Changed location",
            "context_order": 99,
        }
        for key, value in changes.items():
            with self.subTest(field=key):
                changed = deepcopy(selected)
                changed[0][key] = value
                with self.assertRaises(ValueError):
                    validate_selected_context(changed, ranges, request.evidence, mapping)

    def test_future_unknown_immutable_fields_cannot_change_or_disappear(self):
        request, mapping = fixture()
        request.evidence[0]["future_source_identity"] = {"release": "authored-release", "epoch": 7}
        selected, ranges = cropped(request, mapping)
        validate_selected_context(selected, ranges, request.evidence, mapping)
        for operation in ("change", "remove", "add"):
            with self.subTest(operation=operation):
                changed = deepcopy(selected)
                if operation == "change":
                    changed[0]["future_source_identity"]["epoch"] = 8
                elif operation == "remove":
                    del changed[0]["future_source_identity"]
                else:
                    changed[0]["unadmitted_identity_field"] = "injected"
                with self.assertRaises(ValueError):
                    validate_selected_context(changed, ranges, request.evidence, mapping)

    def test_selected_hash_and_offset_types_are_integrity_failures(self):
        request, mapping = fixture()
        selected, ranges = cropped(request, mapping)
        bad = deepcopy(selected)
        bad[0]["text_hash"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_selected_context(bad, ranges, request.evidence, mapping)
        for start in (True, 1.0, -1):
            with self.subTest(start=start):
                invalid = deepcopy(ranges)
                invalid[selected[0]["chunk_id"]]["submitted_start"] = start
                with self.assertRaises(ValueError):
                    validate_selected_context(selected, invalid, request.evidence, mapping)

    def run_fallback_control(self, failing_stage):
        request, mapping = fixture()
        original = deepcopy((request, mapping))
        native_mapper_calls, native_selector_calls, build_inputs = [], [], []

        def native_mapper(evidence, current_map):
            native_mapper_calls.append(deepcopy((evidence, current_map)))
            fragments, issues = native_map_fragments(evidence, current_map)
            return [{**row, "test_producer": "native"} for row in fragments], issues

        def native_selector(evidence, fragments, question, understanding=None, source_map=None):
            native_selector_calls.append(deepcopy((evidence, fragments, source_map)))
            self.assertTrue(all(row["test_producer"] == "native" for row in fragments))
            selected, ranges, excluded, plan = keep_all(
                evidence, fragments, question, understanding, source_map
            )
            return selected, ranges, excluded, {**plan, "producer": "native"}

        def candidate_mapper(evidence, current_map):
            if failing_stage == "mapper":
                current_map[evidence[0]["chunk_id"]]["submitted_start"] = 0
                raise RuntimeError("AUTHORED_CANDIDATE_ALGORITHM_FAILURE")
            fragments, issues = native_map_fragments(evidence, current_map)
            return [{**row, "test_producer": "candidate"} for row in fragments], issues

        def candidate_selector(evidence, fragments, question, understanding=None, source_map=None):
            source_map[evidence[0]["chunk_id"]]["submitted_start"] = 0
            raise RuntimeError("AUTHORED_CANDIDATE_ALGORITHM_FAILURE")

        def observe_build(current):
            build_inputs.append(deepcopy(current.evidence))
            return (
                [{"role": "user", "content": "\n".join(row["text"] for row in current.evidence)}],
                deepcopy(current.evidence),
                {},
                current,
            )

        result = prepare_context(
            request,
            mapping,
            observe_build,
            native_mapper,
            native_selector,
            candidate_mapper=candidate_mapper,
            candidate_selector=candidate_selector,
        )
        self.assertEqual((request, mapping), original)
        self.assertTrue(native_mapper_calls)
        self.assertEqual(len(native_selector_calls), 1)
        self.assertEqual(native_selector_calls[0][0], original[0].evidence)
        self.assertEqual(native_selector_calls[0][2], original[1])
        self.assertEqual(build_inputs, [original[0].evidence])
        self.assertEqual(result["selected"], original[0].evidence)
        self.assertEqual(result["source_map"], original[1])
        self.assertEqual(result["context_plan"]["producer"], "native")
        self.assertTrue(all(row["test_producer"] == "native" for row in result["fragments"]))
        self.assertEqual(
            result["messages"][0]["content"], "\n".join(row["text"] for row in original[0].evidence)
        )

    def test_candidate_mapper_runtime_error_recomputes_whole_native_pair(self):
        self.run_fallback_control("mapper")

    def test_candidate_selector_runtime_error_discards_candidate_mapper_outputs(self):
        self.run_fallback_control("selector")

    def test_candidate_value_error_is_a_hard_stop_without_fallback(self):
        request, mapping = fixture()
        calls = {"native_selector": 0, "build": 0}

        def no_selector(*args, **kwargs):
            calls["native_selector"] += 1
            raise AssertionError("Integrity failure must not use native fallback")

        def no_build(*args, **kwargs):
            calls["build"] += 1
            raise AssertionError("Integrity failure must not produce messages")

        def broken(*args, **kwargs):
            raise ValueError("AUTHORED_INTEGRITY_FAILURE")

        with self.assertRaises(ValueError):
            prepare_context(
                request,
                mapping,
                no_build,
                native_map_fragments,
                no_selector,
                candidate_mapper=broken,
                candidate_selector=keep_all,
            )
        self.assertEqual(calls, {"native_selector": 0, "build": 0})

    def test_candidate_selected_metadata_failure_is_not_a_fallback_trigger(self):
        request, mapping = fixture()
        native_calls, build_calls = [], []

        def corrupt_selector(evidence, fragments, question, understanding=None, source_map=None):
            selected, ranges, excluded, plan = keep_all(
                evidence, fragments, question, understanding, source_map
            )
            selected[0]["source_title"] = "Foreign title"
            return selected, ranges, excluded, plan

        with self.assertRaises(ValueError):
            prepare_context(
                request,
                mapping,
                lambda current: build_calls.append(current),
                native_map_fragments,
                lambda *args: native_calls.append(args),
                candidate_mapper=native_map_fragments,
                candidate_selector=corrupt_selector,
            )
        self.assertEqual(native_calls, [])
        self.assertEqual(build_calls, [])

    def test_corrupt_original_hash_stops_before_candidate_or_build(self):
        request, mapping = fixture()
        request.evidence[0]["text_hash"] = "0" * 64
        candidate_calls, build_calls, selector_calls = [], [], []

        def candidate(*args, **kwargs):
            candidate_calls.append(args)
            raise RuntimeError("A corrupt original must not reach a candidate")

        with self.assertRaises(ValueError):
            prepare_context(
                request,
                mapping,
                lambda current: build_calls.append(current),
                native_map_fragments,
                lambda *args: selector_calls.append(args),
                candidate_mapper=candidate,
                candidate_selector=keep_all,
            )
        self.assertEqual(candidate_calls, [])
        self.assertEqual(build_calls, [])
        self.assertEqual(selector_calls, [])

    def test_partial_pair_is_rejected_without_any_selection(self):
        request, mapping = fixture()
        request.generation_context_policy = "complementary_context_v2"
        calls = []
        with self.assertRaises(ValueError):
            prepare_context(
                request,
                mapping,
                lambda current: calls.append("build"),
                native_map_fragments,
                lambda *args: calls.append("native_selector"),
                candidate_mapper=lambda *args: calls.append("candidate_mapper"),
                candidate_selector=keep_all,
            )
        self.assertEqual(calls, [])

    def test_real_native_packer_remains_within_3000_tokens_after_context_selection(self):
        body = "Water crosses a membrane and changes cell volume. " * 180
        request, mapping = fixture(count=2, body=body)
        counter = TokenCounter(request.config)
        self.assertGreater(sum(counter.count(row["text"]) for row in request.evidence), 3000)
        result = prepare_context(
            request,
            mapping,
            lambda current: native_build_messages(current, counter),
            native_map_fragments,
            keep_all,
            candidate_mapper=native_map_fragments,
            candidate_selector=keep_all,
        )
        selected = result["selected"]
        self.assertTrue(selected)
        self.assertEqual(len({row["evidence_id"] for row in selected}), len(selected))
        self.assertEqual(len({row["chunk_id"] for row in selected}), len(selected))
        self.assertLessEqual(sum(counter.count(row["text"]) for row in selected), 3000)
        self.assertEqual(
            result["report"]["evidence_tokens"], sum(counter.count(row["text"]) for row in selected)
        )
        originals = {row["chunk_id"]: row for row in request.evidence}
        for item in selected:
            self.assertEqual(digest(item["text"]), item["text_hash"])
            self.assertIn(item["text"], originals[item["chunk_id"]]["text"])
            self.assertEqual(item["asset_id"], originals[item["chunk_id"]]["asset_id"])
            self.assertEqual(item["processing_id"], originals[item["chunk_id"]]["processing_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
