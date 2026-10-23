"""Portable authored contract tests, not model quality or semantic truth measurements."""

from copy import deepcopy
import json
import unittest

from generation import atomic_support_v1 as support, atomic_support_compact_v1 as compact


def fixture(citation_text="Valve Q stays closed when the pin is inserted."):
    prefix = "Local source \U0001f9ea: "
    source = prefix + citation_text + " Local-only footer."
    packet = {
        "schema_version": "atomic_support_input_v1",
        "atom_id": "A1",
        "proposition": "Valve Q stays closed when the pin is inserted.",
        "required_conditions": [
            {
                "condition_id": "C0",
                "kind": "proposition",
                "description": "Valve Q stays closed when the pin is inserted.",
            },
            {"condition_id": "C1", "kind": "identity", "description": "The device is Valve Q."},
            {
                "condition_id": "C2",
                "kind": "qualifier",
                "description": "The pin-inserted condition applies.",
            },
        ],
        "actual_citations": [
            {
                "fragment_id": "F1",
                "evidence_id": "E1",
                "source_id": "S1",
                "start": len(prefix),
                "end": len(prefix) + len(citation_text),
                "exact_text": citation_text,
            }
        ],
    }
    sources = {"S1": {"evidence_id": "E1", "exact_text": source}}
    judgment = {
        "schema_version": "atomic_support_compact_v1",
        "atom_id": "A1",
        "verdict": "supported",
        "conditions": [
            {
                "condition_id": condition["condition_id"],
                "verdict": "supported",
                "reason": "The source directly states this necessary condition.",
                "witnesses": [{"fragment_id": "F1", "quote": citation_text}],
                "gap": None,
            }
            for condition in packet["required_conditions"]
        ],
        "additional_gaps": [],
    }
    return packet, sources, judgment


def encode(value):
    return json.dumps(value, ensure_ascii=False)


class CompactAtomicTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.sources, self.judgment = fixture()

    def prepared(self):
        return compact.prepare_compact_atomic_check(self.packet, self.sources)

    def validate(self):
        return compact.validate_compact_atomic_judgment(self.prepared(), encode(self.judgment))

    def assert_error(self, code, fn):
        with self.assertRaises(support.AtomicContractError) as caught:
            fn()
        self.assertEqual(code, caught.exception.code)

    def test_small_projection_preserves_semantic_input_and_omits_full_sources_and_coordinates(self):
        prepared = self.prepared()
        projected = json.loads(prepared.messages[-1]["content"])
        self.assertEqual("atomic_support_compact_input_v1", projected["schema_version"])
        for field in ("atom_id", "proposition", "required_conditions"):
            self.assertEqual(self.packet[field], projected[field])
        self.assertEqual(
            [{"fragment_id": "F1", "exact_text": self.packet["actual_citations"][0]["exact_text"]}],
            projected["actual_citations"],
        )
        self.assertNotIn("Local source", prepared.messages[-1]["content"])
        self.assertNotIn("Local-only footer", prepared.messages[-1]["content"])
        self.assertEqual(self.packet, prepared.canonical.packet)
        self.assertLessEqual(
            prepared.receipt["messages_plus_schema_utf8_bytes"], support.MAX_INPUT_UTF8_BYTES
        )
        self.assertFalse(prepared.receipt["model_window_verified"])

        def assert_no_titles(value):
            if isinstance(value, dict):
                self.assertNotIn("title", value)
                for child in value.values():
                    assert_no_titles(child)
            elif isinstance(value, list):
                for child in value:
                    assert_no_titles(child)

        assert_no_titles(prepared.response_schema)

    def test_unique_witnesses_expand_to_original_strict_contract_without_semantic_upgrade(self):
        before = deepcopy((self.packet, self.sources, self.judgment))
        validated = self.validate()
        strict = validated["strict_validation"]
        self.assertEqual("supported", strict["judgment"]["verdict"])
        self.assertEqual(3, len(validated["binding_audit"]["resolved_witnesses"]))
        for index, condition in enumerate(strict["judgment"]["condition_judgments"]):
            self.assertEqual(
                self.judgment["conditions"][index]["reason"], condition["semantic_reason"]
            )
            self.assertEqual(self.judgment["conditions"][index]["gap"], condition["gap"])
            self.assertEqual(
                self.packet["actual_citations"][0]["start"], condition["evidence_spans"][0]["start"]
            )
        self.assertFalse(strict["semantic_truth_verified"])
        self.assertFalse(validated["binding_audit"]["production_publication_authorized"])
        self.assertIsNone(validated["binding_audit"]["human_rating"])
        self.assertEqual(before, (self.packet, self.sources, self.judgment))

    def test_missing_evidence_preserves_uncertain_gaps_and_does_not_become_false(self):
        self.packet["actual_citations"] = []
        self.judgment["verdict"] = "uncertain"
        for condition in self.judgment["conditions"]:
            condition.update(
                verdict="uncertain",
                witnesses=[],
                reason="No actual source was cited.",
                gap={"kind": "missing_evidence", "detail": "No cited support is available."},
            )
        result = self.validate()
        self.assertEqual("uncertain", result["strict_validation"]["judgment"]["verdict"])
        self.judgment["verdict"] = "unsupported"
        self.judgment["conditions"][0]["verdict"] = "unsupported"
        self.assert_error("UNSUPPORTED_REQUIRES_COUNTEREVIDENCE", self.validate)

    def test_counterevidence_and_missing_guard_opinions_keep_explicit_gaps(self):
        self.packet["proposition"] = "Valve Q stays closed regardless of the pin."
        self.packet["required_conditions"][0]["description"] = self.packet["proposition"]
        text = "With the pin removed, Valve Q opens."
        self.packet["required_conditions"][2]["description"] = (
            "No pin-inserted guard restricts the closure rule."
        )
        citation = self.packet["actual_citations"][0]
        citation["exact_text"] = text
        citation["end"] = citation["start"] + len(text)
        self.sources["S1"]["exact_text"] = (
            self.sources["S1"]["exact_text"][: citation["start"]] + text
        )
        self.judgment["verdict"] = "unsupported"
        for condition in self.judgment["conditions"]:
            condition["witnesses"][0]["quote"] = text
        self.judgment["conditions"][0].update(
            verdict="unsupported",
            reason="The source gives the pin-removed counterexample.",
            gap={"kind": "contradiction", "detail": "The omitted pin guard changes the outcome."},
        )
        self.judgment["conditions"][2].update(
            verdict="unsupported",
            reason="The pin-removed counterexample contradicts closure without that guard.",
            gap={"kind": "contradiction", "detail": "The assertion drops a necessary pin guard."},
        )
        result = self.validate()
        self.assertEqual("unsupported", result["strict_validation"]["judgment"]["verdict"])
        self.assertFalse(result["strict_validation"]["semantic_truth_verified"])

    def test_wrong_subject_reported_supported_opinion_is_never_locally_certified(self):
        self.packet["proposition"] = "Valve Z stays closed when the pin is inserted."
        self.packet["required_conditions"][0]["description"] = self.packet["proposition"]
        result = self.validate()
        self.assertEqual("supported", result["strict_validation"]["judgment"]["verdict"])
        self.assertFalse(result["strict_validation"]["semantic_truth_verified"])
        self.assertFalse(result["strict_validation"]["atomic_decomposition_verified"])

    def test_unknown_identity_and_conflict_reports_retain_uncertain(self):
        condition = self.judgment["conditions"][1]
        condition.update(
            verdict="uncertain",
            witnesses=[],
            reason="The referent is not linked to this device.",
            gap={"kind": "unresolved_identity", "detail": "The identity link is absent."},
        )
        self.judgment["verdict"] = "uncertain"
        result = self.validate()
        self.assertEqual(
            condition["gap"],
            result["strict_validation"]["judgment"]["condition_judgments"][1]["gap"],
        )
        condition["gap"] = {
            "kind": "conflicting_evidence",
            "detail": "The identity accounts conflict without resolution.",
        }
        self.judgment["verdict"] = "unsupported"
        self.assert_error("REPORTED_CONFLICT_REQUIRES_UNCERTAIN", self.validate)

    def test_overlap_ambiguity_no_match_and_foreign_fragment_are_rejected(self):
        self.packet, self.sources, self.judgment = fixture("aaa")
        self.judgment["conditions"][0]["witnesses"][0]["quote"] = "aa"
        self.assert_error("QUOTE_NOT_UNIQUE_IN_ACTUAL_CITATION", self.validate)
        self.judgment["conditions"][0]["witnesses"][0]["quote"] = "not here"
        self.assert_error("QUOTE_NOT_IN_ACTUAL_CITATION", self.validate)
        self.judgment["conditions"][0]["witnesses"][0].update(fragment_id="F_FOREIGN", quote="aaa")
        self.assert_error("UNBOUND_FRAGMENT", self.validate)

    def test_duplicate_conditions_json_unicode_short_fields_and_byte_limit_are_rejected(self):
        self.judgment["conditions"][1]["condition_id"] = "C0"
        self.assert_error("CONDITION_ID_SET", self.validate)
        prepared = self.prepared()
        self.assert_error(
            "DUPLICATE_JSON_KEY",
            lambda: compact.validate_compact_atomic_judgment(prepared, '{"a":1,"a":2}'),
        )
        self.assert_error(
            "INVALID_JSON",
            lambda: compact.validate_compact_atomic_judgment(prepared, '{"a":"\\ud800"}'),
        )
        self.packet, self.sources, self.judgment = fixture()
        self.judgment["conditions"][0]["reason"] = "x" * 121
        self.assert_error("COMPACT_OUTPUT_SCHEMA", self.validate)
        self.packet, self.sources, self.judgment = fixture()
        oversized = encode(self.judgment) + " " * compact.MAX_COMPACT_OUTPUT_UTF8_BYTES
        self.assert_error(
            "COMPACT_OUTPUT_BYTE_CEILING",
            lambda: compact.validate_compact_atomic_judgment(self.prepared(), oversized),
        )

    def test_unicode_witness_binding_uses_codepoint_coordinates(self):
        text = "\U0001f9ea Valve Q stays closed when the pin is inserted."
        self.packet, self.sources, self.judgment = fixture(text)
        quote = "Valve Q stays closed when the pin is inserted."
        for condition in self.judgment["conditions"]:
            condition["witnesses"][0]["quote"] = quote
        result = self.validate()
        expected = self.packet["actual_citations"][0]["start"] + 2
        for span in result["binding_audit"]["resolved_witnesses"]:
            self.assertEqual(expected, span["start"])
            self.assertEqual("Unicode_codepoints", span["offset_unit"])


if __name__ == "__main__":
    unittest.main()
