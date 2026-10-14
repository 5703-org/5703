"""Free provenance tests; hand-written fixtures are not model quality measurements."""

from copy import deepcopy
import json
import unittest

from generation import atomic_support_v1 as support, atomic_quote_binding_v1 as binding


def fixture(citation_text="Valve Q remains closed.", quote=None, relative_start=0):
    quote = quote if quote is not None else citation_text
    prefix = "Local record \U0001f9ea: "
    source_text = prefix + citation_text + " Outside sentence."
    start = len(prefix)
    proposition = "Valve Q remains closed."
    packet = {
        "schema_version": "atomic_support_input_v1",
        "atom_id": "A1",
        "proposition": proposition,
        "required_conditions": [
            {"condition_id": "C0", "kind": "proposition", "description": proposition}
        ],
        "actual_citations": [
            {
                "fragment_id": "F1",
                "evidence_id": "E1",
                "source_id": "S1",
                "start": start,
                "end": start + len(citation_text),
                "exact_text": citation_text,
            }
        ],
    }
    sources = {"S1": {"evidence_id": "E1", "exact_text": source_text}}
    span = {
        "fragment_id": "F1",
        "start": start + relative_start,
        "end": start + relative_start + len(quote),
        "quote": quote,
    }
    judgment = {
        "schema_version": "atomic_support_judgment_v1",
        "atom_id": "A1",
        "verdict": "supported",
        "condition_judgments": [
            {
                "condition_id": "C0",
                "verdict": "supported",
                "evidence_spans": [span],
                "semantic_reason": "A hand-written development opinion about this exact clause.",
                "gap": None,
            }
        ],
        "additional_gaps": [],
    }
    return packet, sources, judgment


def raw(value):
    return json.dumps(value, ensure_ascii=False)


class AtomicQuoteBindingTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.sources, self.judgment = fixture()

    def prepared(self):
        return support.prepare_atomic_check(self.packet, self.sources)

    def bind(self):
        return binding.bind_atomic_quote_offsets(self.prepared(), raw(self.judgment))

    def assert_error(self, code, fn):
        with self.assertRaises(support.AtomicContractError) as caught:
            fn()
        self.assertEqual(code, caught.exception.code)

    def test_unique_wrong_offset_changes_coordinates_only_then_uses_original_strict_validator(self):
        span = self.judgment["condition_judgments"][0]["evidence_spans"][0]
        expected_end = span["end"]
        span["end"] += 2
        original = deepcopy((self.packet, self.sources, self.judgment))
        self.assert_error(
            "JUDGMENT_SLICE_MISMATCH",
            lambda: support.validate_atomic_judgment(self.prepared(), raw(self.judgment)),
        )
        result = self.bind()
        normalized = json.loads(result["corrected_raw"])
        self.assertTrue(result["normalization_applied"])
        self.assertEqual(
            expected_end, normalized["condition_judgments"][0]["evidence_spans"][0]["end"]
        )
        original_without_coordinates = binding._semantic_projection(self.judgment)
        self.assertEqual(original_without_coordinates, binding._semantic_projection(normalized))
        self.assertEqual(original, (self.packet, self.sources, self.judgment))
        self.assertEqual(1, len(result["audit"]["changes"]))
        self.assertFalse(result["audit"]["semantic_truth_verified"])
        self.assertFalse(result["audit"]["production_publication_authorized"])
        self.assertIsNone(result["audit"]["human_rating"])
        self.assertEqual(
            "supported", result["strict_validation_after_normalization"]["judgment"]["verdict"]
        )

    def test_valid_coordinates_retain_exact_raw_even_when_quote_repeats(self):
        self.packet, self.sources, self.judgment = fixture("aa aa", quote="aa", relative_start=3)
        original_raw = raw(self.judgment)
        result = self.bind()
        self.assertFalse(result["normalization_applied"])
        self.assertEqual([], result["audit"]["changes"])
        self.assertEqual(original_raw, result["corrected_raw"])
        self.assertEqual(
            result["audit"]["original_raw_sha256"], result["audit"]["normalized_raw_sha256"]
        )

    def test_no_match_never_searches_full_source_or_sibling_actually_cited_fragment(self):
        self.packet["actual_citations"].append(
            {
                "fragment_id": "F2",
                "evidence_id": "E2",
                "source_id": "S2",
                "start": 0,
                "end": len("Outside sentence."),
                "exact_text": "Outside sentence.",
            }
        )
        self.sources["S2"] = {"evidence_id": "E2", "exact_text": "Outside sentence."}
        span = self.judgment["condition_judgments"][0]["evidence_spans"][0]
        span["quote"] = "Outside sentence."
        # It occurs outside F1 in its full source and inside sibling F2; neither is eligible.
        self.assert_error("QUOTE_NOT_IN_ACTUAL_CITATION", self.bind)

    def test_overlapping_occurrences_are_ambiguous_and_never_guessed(self):
        self.packet, self.sources, self.judgment = fixture("aaa", quote="aa")
        self.judgment["condition_judgments"][0]["evidence_spans"][0]["end"] += 1
        self.assert_error("QUOTE_NOT_UNIQUE_IN_ACTUAL_CITATION", self.bind)

    def test_unknown_fragment_is_never_reassigned_to_matching_cited_quote(self):
        self.judgment["condition_judgments"][0]["evidence_spans"][0]["fragment_id"] = "FOREIGN"
        self.assert_error("UNBOUND_FRAGMENT", self.bind)

    def test_unicode_offsets_use_codepoints_and_preserve_literal_quote(self):
        citation_text = "\U0001f9ea Valve Q remains closed."
        quote = "Valve Q remains closed."
        self.packet, self.sources, self.judgment = fixture(
            citation_text, quote=quote, relative_start=2
        )
        span = self.judgment["condition_judgments"][0]["evidence_spans"][0]
        correct = {"start": span["start"], "end": span["end"]}
        byte_prefix = len("\U0001f9ea ".encode("utf-8"))
        span["start"] = self.packet["actual_citations"][0]["start"] + byte_prefix
        span["end"] = span["start"] + len(quote)
        result = self.bind()
        self.assertEqual(correct, result["audit"]["changes"][0]["after"])
        self.assertEqual(
            quote,
            json.loads(result["corrected_raw"])["condition_judgments"][0]["evidence_spans"][0][
                "quote"
            ],
        )

    def test_uncertain_verdict_reason_and_explicit_gap_are_not_repaired_as_semantics(self):
        self.judgment["verdict"] = "uncertain"
        item = self.judgment["condition_judgments"][0]
        item.update(
            verdict="uncertain",
            semantic_reason="A necessary condition remains unresolved.",
            gap={
                "kind": "missing_condition",
                "detail": "A necessary condition is not established.",
            },
        )
        item["evidence_spans"][0]["end"] += 1
        result = self.bind()
        normalized = json.loads(result["corrected_raw"])
        self.assertEqual("uncertain", normalized["verdict"])
        self.assertEqual(item["gap"], normalized["condition_judgments"][0]["gap"])
        self.assertEqual(
            item["semantic_reason"], normalized["condition_judgments"][0]["semantic_reason"]
        )

    def test_strict_json_unicode_schema_and_output_ceiling_remain_enforced(self):
        prepared = self.prepared()
        reason = self.judgment["condition_judgments"][0]["semantic_reason"]
        invalid_unicode = raw(self.judgment).replace(reason, "\\ud800")
        cases = [
            ('{"a":1,"a":2}', "DUPLICATE_JSON_KEY"),
            ('{"a":NaN}', "NONFINITE_JSON_NUMBER"),
            (invalid_unicode, "INVALID_JSON"),
            ("{}", "OUTPUT_SCHEMA"),
            (" " * (support.MAX_OUTPUT_UTF8_BYTES + 1), "OUTPUT_SIZE_OR_TYPE"),
        ]
        for text, code in cases:
            self.assert_error(code, lambda: binding.bind_atomic_quote_offsets(prepared, text))

    def test_coordinate_repair_cannot_hide_an_invalid_verdict_gap_contract(self):
        item = self.judgment["condition_judgments"][0]
        item["evidence_spans"][0]["end"] += 1
        item["gap"] = {"kind": "missing_condition", "detail": "Still missing."}
        self.assert_error("SUPPORTED_CONDITION_INVARIANT", self.bind)


if __name__ == "__main__":
    unittest.main()
