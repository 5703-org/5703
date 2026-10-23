"""Structural diagnostic privacy tests; all inputs are authored fixtures."""

import copy
import json
import unittest

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from generation.checker_contract import schema_issue
from generation.schema_diagnostic_observer_v1 import (
    MAX_RECORD_BYTES,
    REDACTED_CODE,
    REDACTED_FIELD,
    REDACTED_TYPE,
    project_schema_diagnostics,
    public_schema_diagnostics,
)
from generation.types import failure


class StructuralFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    claims: list[int] = Field(min_length=2, max_length=3)


class ParserFixture(ValueError):
    code = "INVALID_JSON"


def diagnostics(payload):
    try:
        StructuralFixture.model_validate(payload)
    except ValidationError as error:
        return public_schema_diagnostics(schema_issue(error), error=error)
    raise AssertionError("Authored fixture must be structurally invalid")


class TestSchemaDiagnosticObserver(unittest.TestCase):
    def test_default_on_missing_field(self):
        self.assertEqual(
            diagnostics({})["issues"][0]["field_errors"],
            [{"path": ["claims"], "error_type": "missing"}],
        )

    def test_disabled_does_not_read_input(self):
        class Poison:
            def __len__(self):
                raise AssertionError("Disabled input was read")

        self.assertIsNone(public_schema_diagnostics(Poison(), enabled=False))

    def test_non_boolean_enable_is_disabled(self):
        self.assertIsNone(public_schema_diagnostics(None, enabled=1))

    def test_extra_name_is_redacted(self):
        result = diagnostics({"claims": [1, 2], "SYNTHETIC_PRIVATE_EXTRA_NAME": "fixture"})
        self.assertEqual(
            result["issues"][0]["field_errors"],
            [{"path": [REDACTED_FIELD], "error_type": "extra_forbidden"}],
        )
        self.assertNotIn("SYNTHETIC_PRIVATE_EXTRA_NAME", json.dumps(result))

    def test_wrong_type_preserves_only_structural_location(self):
        result = diagnostics({"claims": [1, "SYNTHETIC_PRIVATE_VALUE"]})
        self.assertEqual(
            result["issues"][0]["field_errors"],
            [{"path": ["claims", 1], "error_type": "int_type"}],
        )
        self.assertNotIn("SYNTHETIC_PRIVATE_VALUE", json.dumps(result))

    def test_short_array_has_numeric_length_metadata(self):
        row = diagnostics({"claims": [1]})["issues"][0]["field_errors"][0]
        self.assertEqual(row["error_type"], "too_short")
        self.assertEqual(row["array_length"], {"actual_length": 1, "min_length": 2})

    def test_long_array_has_numeric_length_metadata(self):
        row = diagnostics({"claims": [1, 2, 3, 4]})["issues"][0]["field_errors"][0]
        self.assertEqual(row["error_type"], "too_long")
        self.assertEqual(row["array_length"], {"actual_length": 4, "max_length": 3})

    def test_other_context_and_input_are_never_exported(self):
        error = ValidationError.from_exception_data(
            "AuthoredFixture",
            [
                {
                    "type": "too_long",
                    "loc": ("claims",),
                    "input": "SYNTHETIC_PRIVATE_INPUT",
                    "ctx": {
                        "field_type": "List",
                        "max_length": 3,
                        "actual_length": 4,
                        "private": "SYNTHETIC_PRIVATE_CONTEXT",
                    },
                }
            ],
        )
        result = public_schema_diagnostics(schema_issue(error), error=error)
        self.assertNotIn("SYNTHETIC_PRIVATE", json.dumps(result))
        self.assertEqual(
            result["issues"][0]["field_errors"][0]["array_length"],
            {"actual_length": 4, "max_length": 3},
        )
        for field_type in ("Dict", "Set", "String"):
            non_array = ValidationError.from_exception_data(
                "AuthoredNonArrayFixture",
                [
                    {
                        "type": "too_long",
                        "loc": ("claims",),
                        "input": "private fixture",
                        "ctx": {"field_type": field_type, "max_length": 3, "actual_length": 4},
                    }
                ],
            )
            observed = public_schema_diagnostics(schema_issue(non_array), error=non_array)
            row = observed["issues"][0]["field_errors"][0]
            self.assertNotIn("array_length_validation", row)
            self.assertNotIn("array_length", row)

    def test_path_is_bounded_to_eight_tokens(self):
        result = project_schema_diagnostics(
            [
                {
                    "code": "CHECKER_SCHEMA_INVALID",
                    "field_errors": [{"path": ["claims"] * 10, "error_type": "missing"}],
                }
            ]
        )
        self.assertEqual(len(result["issues"][0]["field_errors"][0]["path"]), 8)
        self.assertEqual(result["redaction_counts"]["path_tokens_omitted"], 2)

    def test_field_rows_have_global_sixteen_bound(self):
        rows = [{"path": ["claims"], "error_type": "missing"}] * 12
        result = project_schema_diagnostics(
            [{"code": "CHECKER_SCHEMA_INVALID", "field_errors": rows}] * 2
        )
        self.assertEqual(sum(len(item["field_errors"]) for item in result["issues"]), 16)

    def test_issue_rows_have_sixteen_bound(self):
        result = project_schema_diagnostics([{"code": "CHECKER_SCHEMA_INVALID"}] * 20)
        self.assertEqual(len(result["issues"]), 16)
        self.assertEqual(result["redaction_counts"]["issue_rows_omitted"], 4)

    def test_existing_non_pydantic_parser_code_preserved(self):
        result = public_schema_diagnostics(schema_issue(ParserFixture("unexported")))
        self.assertEqual(result["issues"][0]["parse_code"], "INVALID_JSON")

    def test_unknown_parser_code_redacted(self):
        class PrivateParserFixture(ValueError):
            code = "SYNTHETIC_PRIVATE_CODE"

        result = public_schema_diagnostics(schema_issue(PrivateParserFixture("unexported")))
        self.assertEqual(result["issues"][0]["parse_code"], REDACTED_CODE)
        self.assertNotIn("SYNTHETIC_PRIVATE_CODE", json.dumps(result))

    def test_unknown_error_type_redacted(self):
        result = public_schema_diagnostics(
            [
                {
                    "code": "CHECKER_SCHEMA_INVALID",
                    "field_errors": [{"path": ["claims"], "error_type": "synthetic_private_type"}],
                }
            ]
        )
        self.assertEqual(result["issues"][0]["field_errors"][0]["error_type"], REDACTED_TYPE)

    def test_unknown_keys_and_raw_values_excluded(self):
        issue = {"code": "CHECKER_SCHEMA_INVALID", "parse_code": "INVALID_JSON"}
        for key in (
            "input",
            "context",
            "ctx",
            "msg",
            "exception",
            "response",
            "raw_text",
            "prompt",
        ):
            issue[key] = "SYNTHETIC_PRIVATE_CONTENT"
        self.assertNotIn(
            "SYNTHETIC_PRIVATE_CONTENT", json.dumps(public_schema_diagnostics([issue]))
        )

    def test_boolean_negative_and_large_indices_redacted(self):
        result = public_schema_diagnostics(
            [
                {
                    "code": "CHECKER_SCHEMA_INVALID",
                    "field_errors": [
                        {"path": ["claims", False, -1, 10001], "error_type": "missing"}
                    ],
                }
            ]
        )
        self.assertEqual(
            result["issues"][0]["field_errors"][0]["path"],
            ["claims", REDACTED_FIELD, REDACTED_FIELD, REDACTED_FIELD],
        )

    def test_source_issues_not_mutated(self):
        issues = [
            {
                "code": "CHECKER_SCHEMA_INVALID",
                "field_errors": [{"path": ["claims"], "error_type": "missing"}],
            }
        ]
        before = copy.deepcopy(issues)
        public_schema_diagnostics(issues)
        self.assertEqual(issues, before)

    def test_output_has_serialized_byte_bound(self):
        rows = [{"path": ["claims"] * 8, "error_type": "missing"}] * 16
        result = public_schema_diagnostics(
            [{"code": "CHECKER_SCHEMA_INVALID", "field_errors": rows}] * 16
        )
        self.assertLessEqual(len(json.dumps(result).encode()), MAX_RECORD_BYTES)

    def test_observer_failure_returns_only_unavailable_marker(self):
        class PoisonEquality:
            def __eq__(self, other):
                raise ValueError("SYNTHETIC_PRIVATE_ERROR")

        result = public_schema_diagnostics([{"code": PoisonEquality()}])
        self.assertTrue(result["diagnostic_unavailable"])
        self.assertNotIn("SYNTHETIC_PRIVATE_ERROR", json.dumps(result))

    def test_failure_details_are_additive_and_json_safe(self):
        observed = diagnostics({})
        result = failure(
            "CHECKER_INCONSISTENT",
            "fixed public failure message",
            issue_codes=["CHECKER_SCHEMA_INVALID"],
            schema_diagnostics=observed,
        )
        self.assertEqual(result["code"], "CHECKER_INCONSISTENT")
        self.assertEqual(result["details"]["issue_codes"], ["CHECKER_SCHEMA_INVALID"])
        self.assertEqual(result["details"]["schema_diagnostics"], observed)
        self.assertNotIn("input", json.dumps(result))
