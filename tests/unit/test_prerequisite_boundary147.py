from copy import deepcopy
import unittest
from tests.unit.test_prerequisite_context_integration import fixture, keep_all
from retrieval.prerequisite_context_v1.integration import prepare_context
from retrieval.source_spans import map_fragments
from conversation import query_v22, query_v24


class BoundaryTests(unittest.TestCase):
    def test_native_packer_runtime_error_never_falls_back(self):
        request, mapping = fixture()
        calls = []

        def broken_build(current):
            raise RuntimeError("AUTHORED_NATIVE_PACKER_FAILURE")

        with self.assertRaisesRegex(RuntimeError, "AUTHORED_NATIVE_PACKER_FAILURE"):
            prepare_context(
                request,
                mapping,
                broken_build,
                map_fragments,
                lambda *a: calls.append(a),
                candidate_mapper=map_fragments,
                candidate_selector=keep_all,
            )
        self.assertEqual(calls, [])

    def test_permission_and_version_reject_before_candidate_runtime_failure(self):
        for field, value in (
            ("revoked", True),
            ("active", False),
            ("source_visibility_verified", False),
            ("document_version_id", "foreign"),
        ):
            with self.subTest(field=field):
                request, mapping = fixture()
                if field == "document_version_id":
                    request.evidence[0][field] = value
                else:
                    mapping[request.evidence[0]["chunk_id"]][field] = value
                calls = []

                def broken(*args):
                    calls.append(args)
                    raise RuntimeError("AUTHORED_CANDIDATE_FAILURE")

                with self.assertRaises(ValueError):
                    prepare_context(
                        request,
                        mapping,
                        lambda r: None,
                        map_fragments,
                        keep_all,
                        candidate_mapper=broken,
                        candidate_selector=keep_all,
                    )
                self.assertEqual(calls, [])

    def test_successful_candidate_cannot_mutate_mapping_authority(self):
        request, mapping = fixture()
        original = deepcopy(mapping)

        def mutated(evidence, current):
            result = map_fragments(evidence, current)
            current[evidence[0]["chunk_id"]]["document_version_id"] = "foreign"
            return result

        def build(current):
            return [], deepcopy(current.evidence), {}, current

        result = prepare_context(
            request,
            mapping,
            build,
            map_fragments,
            keep_all,
            candidate_mapper=mutated,
            candidate_selector=keep_all,
        )
        self.assertEqual(result["source_map"], original)
        self.assertEqual(mapping, original)

    def test_fresh_question_uses_generic_anchor_without_rewriting_science(self):
        question = "For a red blood cell, how does its volume change in a hypotonic solution?"
        native = query_v22.prepare_query(question).model_dump()
        prepared = query_v24.prepare_query(question).model_dump()
        self.assertTrue(native["needs_clarification"])
        self.assertFalse(prepared["needs_clarification"])
        self.assertEqual(prepared["preparation_version"], query_v24.VERSION)
        self.assertEqual(prepared["fallback_reason"], "current_named_noun_anchor_v1")
        self.assertEqual(prepared["standalone_query"], question)
        self.assertEqual(prepared["referenced_message_ids"], [])
        requirements = query_v24.describe_requirements(question, prepared)
        self.assertEqual(
            requirements["preparation_dependency"]["frozen_preparation_version"], query_v24.VERSION
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
