"""Free execution and CLI integration tests using isolated synthetic fixtures."""

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from generation import atomic_quote_binding_v1 as binding
from generation import atomic_support_v1 as support
from scripts.verify import atomic_support as cli


def fixture(text="Valve Q remains closed.", quote=None, relative_start=0):
    quote = text if quote is None else quote
    prefix = "Synthetic record \U0001f9ea: "
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
                "end": start + len(text),
                "exact_text": text,
            }
        ],
    }
    sources = {"S1": {"evidence_id": "E1", "exact_text": prefix + text + " Outside sentence."}}
    judgment = {
        "schema_version": "atomic_support_judgment_v1",
        "atom_id": "A1",
        "verdict": "supported",
        "condition_judgments": [
            {
                "condition_id": "C0",
                "verdict": "supported",
                "evidence_spans": [
                    {
                        "fragment_id": "F1",
                        "start": start + relative_start,
                        "end": start + relative_start + len(quote),
                        "quote": quote,
                    }
                ],
                "semantic_reason": "A synthetic model opinion, not independently certified.",
                "gap": None,
            }
        ],
        "additional_gaps": [],
    }
    return packet, sources, judgment


def encode(value):
    return json.dumps(value, ensure_ascii=False)


class LocalReplyProvider:
    def __init__(self, raw, *, finish_reason="stop", error=None, raises=False):
        self.raw = raw
        self.finish_reason = finish_reason
        self.error = error
        self.raises = raises
        self.calls = 0

    def generate(self, messages, **kwargs):
        self.calls += 1
        if self.raises:
            raise RuntimeError("private provider exception must not be reported")
        return SimpleNamespace(
            raw_text=self.raw, finish_reason=self.finish_reason, error=self.error
        )


class AtomicQuoteBindingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.sources, self.judgment = fixture()

    def execute(self, *, bind_quotes=False, provider=None):
        provider = provider or LocalReplyProvider(encode(self.judgment))
        return support.execute_atomic_check(
            self.packet, self.sources, provider=provider, bind_quotes=bind_quotes
        ), provider

    def test_default_strict_execution_still_rejects_unique_wrong_coordinates(self):
        self.judgment["condition_judgments"][0]["evidence_spans"][0]["end"] += 2
        with patch.object(binding, "bind_atomic_quote_offsets", side_effect=AssertionError):
            result, provider = self.execute()
        self.assertEqual("OUTPUT_REJECTED", result["status"])
        self.assertEqual("JUDGMENT_SLICE_MISMATCH", result["error"])
        self.assertIsNone(result["result"])
        self.assertEqual(1, provider.calls)

    def test_explicit_single_call_repairs_only_wrong_coordinates_and_keeps_correct_repeated_quote(
        self,
    ):
        self.packet["required_conditions"].append(
            {
                "condition_id": "C1",
                "kind": "identity",
                "description": "The selected record remains bound.",
            }
        )
        self.packet["actual_citations"].append(
            {
                "fragment_id": "F2",
                "evidence_id": "E2",
                "source_id": "S2",
                "start": 0,
                "end": 5,
                "exact_text": "aa aa",
            }
        )
        self.sources["S2"] = {"evidence_id": "E2", "exact_text": "aa aa"}
        self.judgment["condition_judgments"].append(
            {
                "condition_id": "C1",
                "verdict": "supported",
                "evidence_spans": [{"fragment_id": "F2", "start": 3, "end": 5, "quote": "aa"}],
                "semantic_reason": "A second unchanged synthetic model opinion.",
                "gap": None,
            }
        )
        expected = deepcopy(self.judgment)
        self.judgment["condition_judgments"][0]["evidence_spans"][0]["end"] += 2
        before = deepcopy((self.packet, self.sources, self.judgment))
        result, provider = self.execute(bind_quotes=True)
        self.assertEqual("REPORTED_JUDGMENT_VALIDATED_ONLY", result["status"])
        self.assertEqual(expected, result["result"]["judgment"])
        self.assertEqual(before, (self.packet, self.sources, self.judgment))
        self.assertEqual(1, provider.calls)
        self.assertEqual(1, result["provider_invocations"])
        audit = result["result"]["quote_binding"]
        self.assertEqual("JUDGMENT_SLICE_MISMATCH", audit["original_strict_validation_error"])
        self.assertEqual(1, len(audit["changes"]))
        self.assertEqual("C0", audit["changes"][0]["condition_id"])
        self.assertFalse(audit["original_provider_observation_qualification_upgraded"])
        self.assertFalse(result["result"]["semantic_truth_verified"])

    def test_valid_repeated_quote_skips_binding_even_when_explicitly_enabled(self):
        self.packet, self.sources, self.judgment = fixture("aa aa", quote="aa", relative_start=3)
        with patch.object(binding, "bind_atomic_quote_offsets", side_effect=AssertionError):
            result, provider = self.execute(bind_quotes=True)
        self.assertEqual(self.judgment, result["result"]["judgment"])
        self.assertNotIn("quote_binding", result["result"])
        self.assertEqual(1, provider.calls)

    def test_ambiguous_absent_and_foreign_quotes_fail_without_widening_source_scope(self):
        for kind, expected in (
            ("ambiguous", "QUOTE_NOT_UNIQUE_IN_ACTUAL_CITATION"),
            ("absent", "QUOTE_NOT_IN_ACTUAL_CITATION"),
            ("foreign", "UNBOUND_FRAGMENT"),
        ):
            with self.subTest(kind=kind):
                if kind == "ambiguous":
                    self.packet, self.sources, self.judgment = fixture("aaa", quote="aa")
                else:
                    self.packet, self.sources, self.judgment = fixture()
                span = self.judgment["condition_judgments"][0]["evidence_spans"][0]
                span["end"] += 1
                if kind == "absent":
                    span["quote"] = "Outside sentence."
                if kind == "foreign":
                    span["fragment_id"] = "UNSUBMITTED"
                result, provider = self.execute(bind_quotes=True)
                self.assertEqual("OUTPUT_REJECTED", result["status"])
                self.assertEqual(expected, result["error"])
                self.assertIsNone(result["result"])
                self.assertEqual(1, provider.calls)
                if kind == "foreign":
                    self.assertNotIn("quote_binding", result)
                else:
                    self.assertEqual(
                        "JUDGMENT_SLICE_MISMATCH",
                        result["quote_binding"]["original_strict_validation_error"],
                    )
                    self.assertEqual(expected, result["quote_binding"]["normalization_error"])
                    self.assertFalse(result["quote_binding"]["normalization_applied"])

    def test_uncertain_reason_and_gap_survive_normalization(self):
        self.judgment["verdict"] = "uncertain"
        item = self.judgment["condition_judgments"][0]
        item.update(
            verdict="uncertain",
            semantic_reason="Identity remains unresolved.",
            gap={
                "kind": "unresolved_identity",
                "detail": "The two records lack an identity bridge.",
            },
        )
        expected = deepcopy(self.judgment)
        item["evidence_spans"][0]["end"] += 2
        result, provider = self.execute(bind_quotes=True)
        self.assertEqual(expected, result["result"]["judgment"])
        self.assertFalse(result["result"]["semantic_truth_verified"])
        self.assertFalse(result["result"]["production_publication_authorized"])
        self.assertEqual(1, provider.calls)

    def test_invalid_boolean_option_fails_before_provider_and_without_provider_stays_not_run(self):
        for value in (1, "true", None):
            with self.subTest(value=value):
                result, provider = self.execute(bind_quotes=value)
                self.assertEqual("PREFLIGHT_FAILED", result["status"])
                self.assertEqual("INVALID_QUOTE_BINDING_OPTION", result["error"])
                self.assertEqual(0, provider.calls)
                prepared = support.prepare_atomic_check(self.packet, self.sources)
                with self.assertRaises(support.AtomicContractError) as caught:
                    support.validate_bound_atomic_judgment(
                        prepared, encode(self.judgment), bind_quotes=value
                    )
                self.assertEqual("INVALID_QUOTE_BINDING_OPTION", caught.exception.code)
        result = support.execute_atomic_check(self.packet, self.sources, bind_quotes=True)
        self.assertEqual("NOT_RUN", result["status"])
        self.assertEqual(0, result["provider_invocations"])
        self.assertEqual(0, result["physical_post_count"])

    def test_provider_errors_truncation_and_unconfirmed_completion_never_enter_binding(self):
        providers = [
            (LocalReplyProvider(encode(self.judgment), finish_reason="length"), "OUTPUT_TRUNCATED"),
            (
                LocalReplyProvider(encode(self.judgment), finish_reason=None),
                "UNCONFIRMED_COMPLETION",
            ),
            (
                LocalReplyProvider(encode(self.judgment), finish_reason="tool_calls"),
                "UNCONFIRMED_COMPLETION",
            ),
            (LocalReplyProvider("", error={"private": "secret"}), "PROVIDER_REPORTED_ERROR"),
            (LocalReplyProvider("", raises=True), "PROVIDER_EXCEPTION"),
        ]
        for provider, expected in providers:
            with self.subTest(expected=expected):
                with patch.object(binding, "bind_atomic_quote_offsets", side_effect=AssertionError):
                    result, _ = self.execute(bind_quotes=True, provider=provider)
                self.assertEqual("PROVIDER_FAILED", result["status"])
                self.assertEqual(expected, result["error"])
                self.assertIsNone(result["result"])
                self.assertEqual(1, provider.calls)
                self.assertNotIn("quote_binding", result)
                self.assertNotIn("secret", encode(result))
                self.assertNotIn("private provider", encode(result))

    def test_coordinate_binding_does_not_hide_invalid_gaps_or_duplicate_spans(self):
        for kind, expected in (
            ("gap", "SUPPORTED_CONDITION_INVARIANT"),
            ("duplicate", "DUPLICATE_JUDGMENT_SPAN"),
        ):
            with self.subTest(kind=kind):
                self.packet, self.sources, self.judgment = fixture()
                item = self.judgment["condition_judgments"][0]
                item["evidence_spans"][0]["end"] += 1
                if kind == "gap":
                    item["gap"] = {"kind": "missing_condition", "detail": "Unresolved."}
                else:
                    item["evidence_spans"].append(deepcopy(item["evidence_spans"][0]))
                result, provider = self.execute(bind_quotes=True)
                self.assertEqual("OUTPUT_REJECTED", result["status"])
                self.assertEqual(expected, result["error"])
                self.assertIsNone(result["result"])
                self.assertEqual(1, provider.calls)
                self.assertEqual(
                    "JUDGMENT_SLICE_MISMATCH",
                    result["quote_binding"]["original_strict_validation_error"],
                )
                self.assertEqual(expected, result["quote_binding"]["normalization_error"])

    def test_saved_judgment_cli_uses_same_explicit_contract_and_zero_provider_calls(self):
        self.judgment["condition_judgments"][0]["evidence_spans"][0]["end"] += 2
        saved = {
            "synthetic-cases.json": encode(
                {
                    "cases": [
                        {
                            "case_id": "synthetic",
                            "packet": self.packet,
                            "source_snapshots": self.sources,
                        }
                    ],
                    "provenance": "AI-synthetic local development fixture",
                }
            ),
            "synthetic-judgment.json": encode(self.judgment),
        }
        prompt = Path(support.__file__).with_name("prompts") / "atomic_support_v1.txt"
        saved[str(prompt)] = prompt.read_text(encoding="utf-8")

        def read_saved(path, *args, **kwargs):
            return saved[str(path)]

        # No filesystem access is needed to test the CLI's saved-input contract.
        with patch.object(Path, "read_text", autospec=True, side_effect=read_saved):
            argv = [
                "--cases",
                "synthetic-cases.json",
                "--case",
                "synthetic",
                "--judgment",
                "synthetic-judgment.json",
            ]
            output = StringIO()
            with redirect_stdout(output):
                code = cli.main(argv)
            strict = json.loads(output.getvalue())
            self.assertEqual(1, code)
            self.assertEqual("JUDGMENT_SLICE_MISMATCH", strict["error"])
            output = StringIO()
            with redirect_stdout(output):
                code = cli.main(argv + ["--bind-quotes"])
            bound = json.loads(output.getvalue())
            self.assertEqual(0, code)
            self.assertEqual("LOCAL_SAVED_REPORTED_JUDGMENT_VALIDATED_ONLY", bound["status"])
            self.assertEqual(0, bound["provider_invocations"])
            self.assertEqual(0, bound["physical_post_count"])
            self.assertFalse(bound["external_execution_available"])
            self.assertFalse(bound["result"]["semantic_truth_verified"])
            self.assertIn("quote_binding", bound["result"])
            output = StringIO()
            with redirect_stdout(output):
                code = cli.main(argv[:-2] + ["--bind-quotes"])
            prepared = json.loads(output.getvalue())
            self.assertEqual(0, code)
            self.assertEqual("NOT_RUN", prepared["status"])
            self.assertEqual(0, prepared["provider_invocations"])
            self.packet, self.sources, self.judgment = fixture("aaa", quote="aa")
            self.judgment["condition_judgments"][0]["evidence_spans"][0]["end"] += 1
            saved["synthetic-cases.json"] = encode(
                {
                    "cases": [
                        {
                            "case_id": "synthetic",
                            "packet": self.packet,
                            "source_snapshots": self.sources,
                        }
                    ]
                }
            )
            saved["synthetic-judgment.json"] = encode(self.judgment)
            output = StringIO()
            with redirect_stdout(output):
                code = cli.main(argv + ["--bind-quotes"])
            rejected = json.loads(output.getvalue())
            self.assertEqual(1, code)
            self.assertEqual("LOCAL_CONTRACT_REJECTED", rejected["status"])
            self.assertEqual("QUOTE_NOT_UNIQUE_IN_ACTUAL_CITATION", rejected["error"])
            self.assertEqual(
                "JUDGMENT_SLICE_MISMATCH",
                rejected["quote_binding"]["original_strict_validation_error"],
            )
            self.assertEqual(0, rejected["provider_invocations"])
            self.assertEqual(0, rejected["physical_post_count"])


if __name__ == "__main__":
    unittest.main()
