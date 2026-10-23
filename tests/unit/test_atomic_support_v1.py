"""Authored offline contract fixtures, not model accuracy or gold measurements."""

from copy import deepcopy
import json
from types import SimpleNamespace
import unittest

from generation.atomic_support_v1 import (
    AtomicContractError,
    execute_atomic_check,
    prepare_atomic_check,
    validate_atomic_judgment,
)


def valve_fixture():
    text = "Header \U0001f9ea. At ambient pressure, valve V17 remains closed. End of excerpt."
    quote = "At ambient pressure, valve V17 remains closed."
    start = text.index(quote)
    packet = {
        "schema_version": "atomic_support_input_v1",
        "atom_id": "atom_valve",
        "proposition": "At ambient pressure, valve V17 remains closed.",
        "required_conditions": [
            {"condition_id": "main", "kind": "proposition", "description": quote},
            {
                "condition_id": "pressure",
                "kind": "applicability",
                "description": "Ambient pressure applies.",
            },
        ],
        "actual_citations": [
            {
                "fragment_id": "f_valve",
                "evidence_id": "e_valve",
                "source_id": "source_valve",
                "start": start,
                "end": start + len(quote),
                "exact_text": quote,
            }
        ],
    }
    sources = {"source_valve": {"evidence_id": "e_valve", "exact_text": text}}
    span = {"fragment_id": "f_valve", "start": start, "end": start + len(quote), "quote": quote}
    judgment = {
        "schema_version": "atomic_support_judgment_v1",
        "atom_id": "atom_valve",
        "verdict": "supported",
        "condition_judgments": [
            {
                "condition_id": "main",
                "verdict": "supported",
                "evidence_spans": [span],
                "semantic_reason": "The excerpt explicitly states this valve's state under the stated pressure.",
                "gap": None,
            },
            {
                "condition_id": "pressure",
                "verdict": "supported",
                "evidence_spans": [span],
                "semantic_reason": "The excerpt supplies the ambient-pressure qualifier.",
                "gap": None,
            },
        ],
        "additional_gaps": [],
    }
    return packet, sources, judgment


def encode(value):
    return json.dumps(value, ensure_ascii=False)


class ManualReplyProvider:
    """Returns hand-written output; performs no transport and measures no model."""

    def __init__(self, raw, *, finish_reason="stop", error=None, raises=False):
        self.raw = raw
        self.finish_reason = finish_reason
        self.error = error
        self.raises = raises
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if self.raises:
            raise RuntimeError("private auth details must never reach diagnostics")
        return SimpleNamespace(
            raw_text=self.raw, finish_reason=self.finish_reason, error=self.error
        )


class AtomicSupportContractTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.sources, self.judgment = valve_fixture()

    def prepared(self):
        return prepare_atomic_check(self.packet, self.sources)

    def validate(self):
        return validate_atomic_judgment(self.prepared(), encode(self.judgment))

    def assert_error(self, expected, fn):
        with self.assertRaises(AtomicContractError) as caught:
            fn()
        self.assertEqual(expected, caught.exception.code)

    def test_supported_fixture_keeps_semantics_unverified_and_only_sends_actual_excerpt(self):
        prepared = self.prepared()
        outcome = self.validate()
        self.assertEqual("supported", outcome["judgment"]["verdict"])
        for key in (
            "semantic_truth_verified",
            "atomic_decomposition_verified",
            "necessary_conditions_complete_verified",
            "production_publication_authorized",
        ):
            self.assertIs(False, outcome[key])
        self.assertIsNone(outcome["human_rating"])
        self.assertNotIn("Header", prepared.messages[1]["content"])
        self.assertNotIn("End of excerpt", prepared.messages[1]["content"])
        self.assertFalse(prepared.receipt["model_window_verified"])
        changed = prepared.packet
        changed["atom_id"] = "other"
        self.assertEqual("atom_valve", prepared.packet["atom_id"])

    def test_semantically_wrong_subject_exact_quote_stays_only_reported_not_certified(self):
        self.packet["proposition"] = "At ambient pressure, valve V99 remains closed."
        self.packet["required_conditions"][0]["description"] = self.packet["proposition"]
        # Intentionally wrong hand-written opinion: the quote remains about V17.
        self.judgment["condition_judgments"][0]["semantic_reason"] = "V17 establishes V99's state."
        result = self.validate()
        self.assertEqual("STRUCTURALLY_BOUND_REPORTED_JUDGMENT", result["status"])
        self.assertFalse(result["semantic_truth_verified"])

    def test_absent_citations_allow_uncertain_but_reject_supported(self):
        self.packet["actual_citations"] = []
        self.assert_error("UNBOUND_FRAGMENT", self.validate)
        self.judgment["verdict"] = "uncertain"
        for item in self.judgment["condition_judgments"]:
            item.update(
                verdict="uncertain",
                evidence_spans=[],
                semantic_reason="There is no cited text to assess.",
                gap={"kind": "missing_evidence", "detail": "No actual citations supplied."},
            )
        self.assertEqual("uncertain", self.validate()["judgment"]["verdict"])

    def test_missing_evidence_cannot_be_unsupported_fact(self):
        self.judgment["verdict"] = "unsupported"
        self.judgment["condition_judgments"][0].update(
            verdict="unsupported",
            evidence_spans=[],
            gap={"kind": "missing_evidence", "detail": "This necessary fact is not stated."},
        )
        self.assert_error("UNSUPPORTED_REQUIRES_COUNTEREVIDENCE", self.validate)

    def test_actual_counterevidence_fixture_is_a_reported_unsupported_judgment(self):
        self.packet["proposition"] = "At ambient pressure, valve V17 remains open."
        self.packet["required_conditions"][0]["description"] = self.packet["proposition"]
        self.judgment["verdict"] = "unsupported"
        self.judgment["condition_judgments"][0].update(
            verdict="unsupported",
            semantic_reason="Closed contradicts the stated open state under the same condition.",
            gap={
                "kind": "contradiction",
                "detail": "The excerpt explicitly states the opposite valve state.",
            },
        )
        result = self.validate()
        self.assertEqual("unsupported", result["judgment"]["verdict"])
        self.assertFalse(result["semantic_truth_verified"])

    def test_explicit_conflict_rejects_overall_unsupported_and_preserves_uncertain_gap(self):
        self.packet["proposition"] = "At ambient pressure, valve V17 remains open."
        self.packet["required_conditions"][0]["description"] = self.packet["proposition"]
        conflicting_text = self.packet["proposition"]
        self.packet["actual_citations"].append(
            {
                "fragment_id": "f_conflict",
                "evidence_id": "e_conflict",
                "source_id": "source_conflict",
                "start": 0,
                "end": len(conflicting_text),
                "exact_text": conflicting_text,
            }
        )
        self.sources["source_conflict"] = {
            "evidence_id": "e_conflict",
            "exact_text": conflicting_text,
        }
        self.judgment["verdict"] = "unsupported"
        self.judgment["condition_judgments"][0].update(
            verdict="unsupported",
            semantic_reason="The first excerpt states closed under the same pressure.",
            gap={"kind": "contradiction", "detail": "Closed contradicts the proposed open state."},
        )
        conflict = {
            "kind": "conflicting_evidence",
            "detail": "The second cited excerpt says open under the same pressure; the conflict is unresolved.",
        }
        self.judgment["additional_gaps"] = [conflict]
        self.assert_error("REPORTED_CONFLICT_REQUIRES_UNCERTAIN", self.validate)
        self.judgment["verdict"] = "uncertain"
        result = self.validate()
        self.assertEqual("uncertain", result["judgment"]["verdict"])
        self.assertEqual([conflict], result["judgment"]["additional_gaps"])
        self.assertEqual(
            "contradiction", result["judgment"]["condition_judgments"][0]["gap"]["kind"]
        )
        self.assertFalse(result["semantic_truth_verified"])

    def test_unknown_coreference_has_condition_gap_and_is_uncertain(self):
        self.packet["required_conditions"].append(
            {
                "condition_id": "identity",
                "kind": "identity",
                "description": "The unnamed device refers to V17.",
            }
        )
        self.judgment["verdict"] = "uncertain"
        self.judgment["condition_judgments"].append(
            {
                "condition_id": "identity",
                "verdict": "uncertain",
                "evidence_spans": [],
                "semantic_reason": "The cited text does not identify the unnamed device.",
                "gap": {
                    "kind": "unresolved_identity",
                    "detail": "The required referent cannot be linked.",
                },
            }
        )
        self.assertEqual("uncertain", self.validate()["judgment"]["verdict"])
        self.judgment["condition_judgments"][-1]["gap"] = None
        self.assert_error("NEGATIVE_CONDITION_GAP_REQUIRED", self.validate)

    def test_explicit_incompatible_conditions_are_not_programmatically_resolved(self):
        self.packet["required_conditions"].append(
            {
                "condition_id": "nonambient",
                "kind": "applicability",
                "description": "Nonambient pressure applies in the same circumstance.",
            }
        )
        self.judgment["verdict"] = "uncertain"
        self.judgment["condition_judgments"].append(
            {
                "condition_id": "nonambient",
                "verdict": "uncertain",
                "evidence_spans": [],
                "semantic_reason": "This is incompatible with the stated ambient condition; resolution is unavailable.",
                "gap": {
                    "kind": "conflicting_evidence",
                    "detail": "The caller supplied conflicting applicable conditions.",
                },
            }
        )
        self.assertEqual("uncertain", self.validate()["judgment"]["verdict"])
        self.assertFalse(self.validate()["necessary_conditions_complete_verified"])

    def test_model_detected_omitted_condition_prevents_supported(self):
        self.judgment["additional_gaps"] = [
            {
                "kind": "missing_condition",
                "detail": "The relevant operating temperature has not been established.",
            }
        ]
        self.assert_error("SUPPORTED_ATOM_INVARIANT", self.validate)
        self.judgment["verdict"] = "uncertain"
        self.assertEqual("uncertain", self.validate()["judgment"]["verdict"])

    def test_every_condition_required_and_atom_identity_is_bound(self):
        omitted = self.judgment["condition_judgments"].pop()
        self.assert_error("CONDITION_ID_SET", self.validate)
        self.judgment["condition_judgments"].append(omitted)
        self.judgment["atom_id"] = "another_atom"
        self.assert_error("ATOM_ID_MISMATCH", self.validate)

    def test_actual_source_offsets_and_ownership_fail_before_provider(self):
        provider = ManualReplyProvider(encode(self.judgment))
        self.packet["actual_citations"][0]["start"] += 1
        result = execute_atomic_check(self.packet, self.sources, provider=provider)
        self.assertEqual("CITATION_SLICE_MISMATCH", result["error"])
        self.assertEqual([], provider.calls)
        self.packet, self.sources, self.judgment = valve_fixture()
        self.sources["source_valve"]["evidence_id"] = "foreign_evidence"
        self.assert_error("SOURCE_OWNERSHIP", self.prepared)

    def test_output_cannot_substitute_fragment_or_clip_wrong_offset(self):
        span = self.judgment["condition_judgments"][0]["evidence_spans"][0]
        span["fragment_id"] = "retrieved_but_not_actually_cited"
        self.assert_error("UNBOUND_FRAGMENT", self.validate)
        span["fragment_id"] = "f_valve"
        span["start"] -= 1
        self.assert_error("JUDGMENT_SLICE_MISMATCH", self.validate)

    def test_supported_needs_nonempty_specific_spans_and_no_gap(self):
        self.judgment["condition_judgments"][0]["evidence_spans"] = []
        self.assert_error("SUPPORTED_CONDITION_INVARIANT", self.validate)

    def test_json_duplicates_trailing_objects_nonfinite_and_extra_fields_fail(self):
        prepared = self.prepared()
        raw = encode(self.judgment)
        self.assert_error(
            "DUPLICATE_JSON_KEY", lambda: validate_atomic_judgment(prepared, '{"a":1,"a":2}')
        )
        self.assert_error("INVALID_JSON", lambda: validate_atomic_judgment(prepared, raw + "{}"))
        self.assert_error(
            "NONFINITE_JSON_NUMBER", lambda: validate_atomic_judgment(prepared, '{"a":NaN}')
        )
        self.judgment["confidence"] = True
        self.assert_error("OUTPUT_SCHEMA", self.validate)

    def test_invalid_unicode_in_raw_escaped_output_input_and_source_is_a_contract_error(self):
        prepared = self.prepared()
        valid_raw = encode(self.judgment)
        reason = self.judgment["condition_judgments"][0]["semantic_reason"]
        for invalid_reason in ("\ud800", "\\ud800"):
            invalid_raw = valid_raw.replace(reason, invalid_reason)
            self.assert_error(
                "INVALID_JSON", lambda: validate_atomic_judgment(prepared, invalid_raw)
            )
            provider = ManualReplyProvider(invalid_raw)
            result = execute_atomic_check(self.packet, self.sources, provider=provider)
            self.assertEqual("OUTPUT_REJECTED", result["status"])
            self.assertEqual("INVALID_JSON", result["error"])
            self.assertIsNone(result["result"])
            self.assertEqual(1, len(provider.calls))
        self.packet["proposition"] += "\ud800"
        self.packet["required_conditions"][0]["description"] = self.packet["proposition"]
        # Pydantic rejects this packet before serialization; it remains a stable contract error.
        self.assert_error("INPUT_SCHEMA", self.prepared)
        result = execute_atomic_check(self.packet, self.sources)
        self.assertEqual("PREFLIGHT_FAILED", result["status"])
        self.assertEqual("INPUT_SCHEMA", result["error"])
        self.assertIsNone(result["result"])
        self.packet, self.sources, self.judgment = valve_fixture()
        self.sources["source_valve"]["exact_text"] += "\udc00"
        self.assert_error("INVALID_UNICODE", self.prepared)

    def test_input_has_one_proposition_condition_and_strict_integer_offsets(self):
        self.packet["required_conditions"] = []
        self.assert_error("INPUT_SCHEMA", self.prepared)
        self.packet, self.sources, self.judgment = valve_fixture()
        self.packet["required_conditions"][0]["description"] = "Different proposition"
        self.assert_error("ATOM_CONDITION_BINDING", self.prepared)
        self.packet, self.sources, self.judgment = valve_fixture()
        self.packet["actual_citations"][0]["start"] = True
        self.assert_error("INPUT_SCHEMA", self.prepared)

    def test_default_execution_does_not_construct_or_invoke_provider(self):
        result = execute_atomic_check(self.packet, self.sources)
        self.assertEqual("NOT_RUN", result["status"])
        self.assertEqual("PROVIDER_NOT_CONFIGURED", result["error"])
        self.assertEqual(0, result["provider_invocations"])
        self.assertEqual(0, result["physical_post_count"])
        self.assertIsNone(result["result"])

    def test_injected_manual_reply_runs_once_without_retry_or_mutating_inputs(self):
        original = deepcopy((self.packet, self.sources))
        provider = ManualReplyProvider(encode(self.judgment))
        result = execute_atomic_check(self.packet, self.sources, provider=provider)
        self.assertEqual("REPORTED_JUDGMENT_VALIDATED_ONLY", result["status"])
        self.assertEqual(1, len(provider.calls))
        self.assertEqual(1, result["provider_invocations"])
        self.assertIsNone(result["physical_post_count"])
        self.assertEqual(original, (self.packet, self.sources))
        self.assertEqual("atomic_support_judgment_v1", provider.calls[0][1]["response_schema_name"])

    def test_provider_truncation_errors_and_exceptions_have_no_domain_verdict(self):
        providers = [
            (
                ManualReplyProvider(encode(self.judgment), finish_reason="length"),
                "OUTPUT_TRUNCATED",
            ),
            (ManualReplyProvider("", error={"private": "secret"}), "PROVIDER_REPORTED_ERROR"),
            (ManualReplyProvider("", raises=True), "PROVIDER_EXCEPTION"),
        ]
        for provider, expected in providers:
            result = execute_atomic_check(self.packet, self.sources, provider=provider)
            self.assertEqual(expected, result["error"])
            self.assertIsNone(result["result"])
            self.assertEqual(1, len(provider.calls))
            self.assertNotIn("secret", encode(result))
            self.assertNotIn("private auth", encode(result))


if __name__ == "__main__":
    unittest.main()
