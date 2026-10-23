"""Pure minimum-data CHECK contract tests; no model, HTTP, or database calls."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from generation import minimum_data_check_v1 as core
from generation.capabilities import CapabilityError, VERSION as CAPABILITY_VERSION, defaults
from generation.parser import ResponseValidationError
from generation.providers import payload as provider_payload, provider_schema
from generation.types import ModelConfig, ProviderResult


FIXTURE = Path(__file__).parents[1] / "fixtures/minimum_data_check172/duplicate-content171.txt"
FROZEN_CONTENT_SHA256 = "315e9765a67be01fdd4fdd84f44a485de519240d5f373d0e8b40f8c3d3bd5522"
ROW_FIELDS = {
    "statement_id",
    "verdict",
    "actor",
    "conditions",
    "quantities_directions",
    "causal_links",
    "quotation_ids",
    "reason",
}


@pytest.fixture
def config():
    # Construct a public protocol description, without loading any saved configuration.
    provider, model, base_url = "openai_compatible", "deepseek-flash", "https://api.deepseek.com"
    return ModelConfig(
        provider=provider,
        model=model,
        base_url=base_url,
        structured_output_mode="json_object",
        thinking_enabled=False,
        capability_version=CAPABILITY_VERSION,
        capabilities=defaults(provider, model, base_url),
    )


@pytest.fixture
def candidate():
    # These authored assertions exercise ownership only, not scientific model quality.
    return {
        "questions": [
            {
                "question": "Where do the three fictional colored markers move?",
                "statements": [
                    {
                        "statement_id": "assertion-alpha",
                        "assertion": "The amber marker moves outward.",
                        "assigned_quotation_ids": ["quote-amber"],
                    },
                    {
                        "statement_id": "assertion-beta",
                        "assertion": "The blue marker moves inward.",
                        "assigned_quotation_ids": ["quote-blue"],
                    },
                    {
                        "statement_id": "assertion-gamma",
                        "assertion": "The amber marker moves outward before the green marker stops.",
                        "assigned_quotation_ids": ["quote-amber", "quote-green"],
                    },
                ],
            },
            {
                "question": "What happens to the separate violet marker?",
                "statements": [
                    {
                        "statement_id": "assertion-elsewhere",
                        "assertion": "The violet marker stops.",
                        "assigned_quotation_ids": ["quote-violet"],
                    }
                ],
            },
        ],
        "quotations": [
            {
                "quotation_id": "quote-amber",
                "physical_PDF_page": 1,
                "text": "The amber marker moves outward.",
            },
            {
                "quotation_id": "quote-blue",
                "physical_PDF_page": 2,
                "text": "The blue marker moves inward.",
            },
            {
                "quotation_id": "quote-green",
                "physical_PDF_page": 3,
                "text": "After the amber marker moves outward, the green marker stops.",
            },
            {
                "quotation_id": "quote-violet",
                "physical_PDF_page": 4,
                "text": "The violet marker stops.",
            },
        ],
        "source": {
            "attribution": "Authored synthetic fixture; not a textbook excerpt.",
            # Public source URL fields exercise the transport whitelist only.
            "catalog_URL": "https://openstax.org/details/books/biology-2e",
            "license_URL": "https://creativecommons.org/publicdomain/zero/1.0/",
            "official_PDF_URL": "https://assets.openstax.org/fixture.pdf",
            "recorded_license": "CC0-1.0",
            "title": "Authored marker fixture",
        },
    }


@pytest.fixture
def prepared(config, candidate):
    return core.prepare(config, candidate, question_index=0)


@pytest.fixture
def valid(candidate):
    return {
        "results": [
            {
                "statement_id": statement["statement_id"],
                "verdict": "supported",
                "actor": "supported",
                "conditions": "not_applicable",
                "quantities_directions": "supported",
                "causal_links": "not_applicable",
                "quotation_ids": statement["assigned_quotation_ids"].copy(),
                "reason": "The assigned synthetic quotation supplies the complete assertion.",
            }
            for statement in candidate["questions"][0]["statements"]
        ]
    }


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def envelope(raw, **choice_changes):
    return {
        "id": "authored-envelope-172",
        "model": "authored-model-172",
        "choices": [{"message": {"content": raw}, "finish_reason": "stop", **choice_changes}],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 7,
            "total_tokens": 19,
            "prompt_cache_hit_tokens": 2,
            "prompt_cache_miss_tokens": 10,
        },
    }


def rejected(raw, prepared, code=None):
    with pytest.raises(ResponseValidationError) as caught:
        core.parse(raw, prepared)
    if code is not None:
        assert caught.value.code == code


def test_pure_wire_preserves_exact_selected_text_and_own_scope(config, candidate):
    original = deepcopy(candidate)
    prepared = core.prepare(config, candidate, question_index=0)
    assert candidate == original
    assert prepared.statement_ids == ("assertion-alpha", "assertion-beta", "assertion-gamma")
    assert prepared.assigned_quotation_ids == {
        "assertion-alpha": ("quote-amber",),
        "assertion-beta": ("quote-blue",),
        "assertion-gamma": ("quote-amber", "quote-green"),
    }
    assert [message["role"] for message in prepared.messages] == ["system", "user"]
    data = json.loads(prepared.messages[1]["content"])
    assert data == {
        **candidate["questions"][0],
        "source": candidate["source"],
        "quotations": candidate["quotations"][:3],
    }
    assert prepared.wire == provider_payload(
        config, prepared.messages, prepared.response_schema, core.VERSION
    )
    assert prepared.wire["response_format"] == {"type": "json_object"}
    assert prepared.wire["thinking"] == {"type": "disabled"}
    assert not any(key in data for key in ("profile", "history", "diagnostics", "api_key"))
    assert "assertion-elsewhere" not in encoded(prepared.wire)
    assert "quote-violet" not in encoded(prepared.wire)
    assert "expected_verdict" not in encoded(prepared.wire)


def test_existing_adapter_places_real_array_schema_in_json_object_wire(prepared):
    schema = prepared.response_schema
    assert schema["type"] == "object"
    assert schema["required"] == ["results"]
    assert schema["additionalProperties"] is False
    rows = schema["properties"]["results"]
    assert rows["type"] == "array"
    assert rows["minItems"] == rows["maxItems"] == 3
    item = rows["items"]
    assert item["type"] == "object" and item["additionalProperties"] is False
    assert set(item["required"]) == set(item["properties"]) == ROW_FIELDS
    assert item["properties"]["statement_id"]["enum"] == list(prepared.statement_ids)
    assert item["properties"]["quotation_ids"]["type"] == "array"
    assert set(item["properties"]["quotation_ids"]["items"]["enum"]) == {
        "quote-amber",
        "quote-blue",
        "quote-green",
    }
    system = prepared.wire["messages"][0]["content"]
    assert "separate" in system.lower() and "object" in system.lower()
    marker = "Match this JSON schema: "
    assert marker in system
    projected = json.loads(system.split(marker, 1)[1])
    assert projected == provider_schema(schema, "openai_compatible")
    assert projected["properties"]["results"]["minItems"] == 3
    assert projected["properties"]["results"]["maxItems"] == 3
    assert projected["properties"]["results"]["items"]["type"] == "object"
    assert (
        "uniqueItems"
        not in projected["properties"]["results"]["items"]["properties"]["quotation_ids"]
    )
    assert item["properties"]["quotation_ids"]["uniqueItems"] is True


def test_official_deepseek_profile_does_not_gain_json_schema_support(config, candidate):
    assert config.capabilities["structured_modes"] == ["json_object", "prompt"]
    with pytest.raises(ResponseValidationError) as caught:
        core.prepare(
            replace(config, structured_output_mode="json_schema"), candidate, question_index=0
        )
    assert caught.value.code == "MINIMUM_DATA_CONFIG_INVALID"
    with pytest.raises(CapabilityError) as caught:
        provider_payload(
            replace(config, structured_output_mode="json_schema"),
            [],
            {"type": "object"},
            core.VERSION,
        )
    assert caught.value.parameter == "structured_output_mode"


@pytest.mark.parametrize("field", ["profile", "history", "api_key", "diagnostics"])
def test_unapproved_candidate_root_field_is_rejected(config, candidate, field):
    candidate[field] = "unapproved authored sentinel"
    with pytest.raises((ResponseValidationError, ValueError)):
        core.prepare(config, candidate, question_index=0)


def test_valid_array_returns_all_rows_without_rewriting(prepared, valid):
    assert core.parse(encoded(valid), prepared) == valid


@pytest.mark.parametrize("root", [None, [], [1], True, "results"])
def test_nonobject_top_level_is_rejected(prepared, root):
    rejected(encoded(root), prepared)


@pytest.mark.parametrize("rows", [None, {}, "rows", 3, True])
def test_results_must_be_an_array(prepared, rows):
    rejected(encoded({"results": rows}), prepared, "MINIMUM_DATA_RESULT_SHAPE")


def test_missing_row_never_becomes_an_inferred_success(prepared, valid):
    valid["results"].pop()
    rejected(encoded(valid), prepared, "MINIMUM_DATA_STATEMENT_MISSING")


def test_duplicate_statement_id_is_not_complete_coverage(prepared, valid):
    valid["results"][1] = deepcopy(valid["results"][0])
    rejected(encoded(valid), prepared, "MINIMUM_DATA_STATEMENT_DUPLICATE")


def test_foreign_statement_id_is_rejected_even_with_correct_row_count(prepared, valid):
    valid["results"][1]["statement_id"] = "assertion-elsewhere"
    rejected(encoded(valid), prepared, "MINIMUM_DATA_STATEMENT_UNKNOWN")


def test_row_order_must_match_the_fixed_request(prepared, valid):
    valid["results"].reverse()
    rejected(encoded(valid), prepared, "MINIMUM_DATA_STATEMENT_ORDER")


@pytest.mark.parametrize("field", sorted(ROW_FIELDS))
def test_each_output_field_is_required(prepared, valid, field):
    del valid["results"][0][field]
    rejected(encoded(valid), prepared, "MINIMUM_DATA_RESULT_SHAPE")


@pytest.mark.parametrize("row", [None, [], "one row", True])
def test_each_result_item_must_be_a_separate_object(prepared, valid, row):
    valid["results"][0] = row
    rejected(encoded(valid), prepared, "MINIMUM_DATA_RESULT_SHAPE")


def test_missing_results_array_is_rejected(prepared):
    rejected("{}", prepared, "MINIMUM_DATA_RESULT_SHAPE")


@pytest.mark.parametrize(
    "field,value",
    [
        ("statement_id", 1),
        ("verdict", True),
        ("verdict", "approved"),
        ("actor", False),
        ("actor", "unknown"),
        ("conditions", []),
        ("quantities_directions", 4),
        ("causal_links", None),
        ("quotation_ids", "quote-amber"),
        ("quotation_ids", [1]),
        ("reason", 1),
        ("reason", ""),
        ("reason", "word " * 41),
    ],
)
def test_wrong_types_unknown_enums_and_unbounded_reason_are_rejected(prepared, valid, field, value):
    valid["results"][0][field] = value
    rejected(encoded(valid), prepared)


@pytest.mark.parametrize("location", ["root", "row"])
def test_extra_fields_are_rejected(prepared, valid, location):
    target = valid if location == "root" else valid["results"][0]
    target["unapproved"] = "must not be accepted"
    rejected(encoded(valid), prepared, "MINIMUM_DATA_RESULT_SHAPE")


@pytest.mark.parametrize("quotation_id", ["quote-blue", "quote-violet", "quote-unknown"])
def test_citations_cannot_be_borrowed_from_another_statement_or_question(
    prepared, valid, quotation_id
):
    valid["results"][0]["quotation_ids"] = [quotation_id]
    rejected(encoded(valid), prepared, "MINIMUM_DATA_QUOTATION_SCOPE")


def test_duplicate_quotation_id_is_rejected(prepared, valid):
    valid["results"][0]["quotation_ids"] *= 2
    rejected(encoded(valid), prepared, "MINIMUM_DATA_QUOTATION_DUPLICATE")


def test_supported_without_own_quotation_cannot_claim_complete_support(prepared, valid):
    valid["results"][0]["quotation_ids"] = []
    rejected(encoded(valid), prepared, "MINIMUM_DATA_SUPPORTED_INCONSISTENT")


@pytest.mark.parametrize(
    "dimension", ["actor", "conditions", "quantities_directions", "causal_links"]
)
@pytest.mark.parametrize("status", ["gap", "contradicted"])
def test_supported_conflicting_dimension_is_rejected_without_reading_reason(
    prepared, valid, dimension, status
):
    valid["results"][0][dimension] = status
    rejected(encoded(valid), prepared, "MINIMUM_DATA_SUPPORTED_INCONSISTENT")


def test_partial_with_a_genuine_declared_gap_remains_a_valid_diagnostic(prepared, valid):
    valid["results"][0]["verdict"] = "partial"
    valid["results"][0]["conditions"] = "gap"
    valid["results"][0]["reason"] = "The supplied quotation lacks the asserted condition."
    assert core.parse(encoded(valid), prepared) == valid


@pytest.mark.parametrize(
    "raw",
    [
        '{"results":[],"results":[]}',
        '{"results":[{"statement_id":"a","statement_id":"b"}]}',
        '{"results":[{"reason":{"nested":"first","nested":"last"}}]}',
    ],
)
def test_duplicate_json_keys_are_rejected_at_every_nesting(prepared, raw):
    rejected(raw, prepared, "DUPLICATE_JSON_KEY")


@pytest.mark.parametrize("key", sorted(ROW_FIELDS))
def test_duplicate_member_is_rejected_for_every_verdict_field(prepared, key):
    raw = '{"results":[{' + encoded(key) + ":0," + encoded(key) + ":1}]}"
    rejected(raw, prepared, "DUPLICATE_JSON_KEY")


def test_exact_saved_malformed_content_is_preserved_and_rejected(prepared):
    frozen = FIXTURE.read_bytes()
    assert hashlib.sha256(frozen).hexdigest() == FROZEN_CONTENT_SHA256
    raw = frozen.decode("utf-8")
    assert raw.count('"statement_id"') == 3
    rejected(raw, prepared, "DUPLICATE_JSON_KEY")
    assert FIXTURE.read_bytes() == frozen


@pytest.mark.parametrize("raw", ['{"results":[', "```json\n{}\n```", "{}{}", '{"results":NaN}'])
def test_incomplete_or_nonjson_text_is_not_salvaged(prepared, raw):
    rejected(raw, prepared, "INVALID_JSON")


def test_decode_reuses_native_usage_model_and_exact_text(prepared, valid):
    raw = encoded(valid)
    decoded = core.decode(envelope(raw), prepared)
    assert decoded.value == valid
    result = decoded.provider_result
    assert result.raw_text == raw and result.model == "authored-model-172"
    assert result.provider_request_id == "authored-envelope-172"
    assert result.usage["input_tokens"] == 12 and result.usage["output_tokens"] == 7
    assert result.usage["total_tokens"] == 19 and result.usage["cost"] is None
    assert result.usage["cache_hit_input_tokens"] == 2
    assert result.usage["cache_miss_input_tokens"] == 10


def test_decode_rejects_saved_duplicate_keys_without_last_key_wins(prepared):
    raw = FIXTURE.read_bytes().decode("utf-8")
    with pytest.raises(ResponseValidationError) as caught:
        core.decode(envelope(raw), prepared)
    assert caught.value.code == "DUPLICATE_JSON_KEY"
    assert caught.value.provider_result.raw_text == raw
    assert caught.value.provider_result.usage["input_tokens"] == 12


@pytest.mark.parametrize("missing_reason", [True, False])
def test_decode_requires_explicit_stop_even_for_complete_valid_json(
    prepared, valid, missing_reason
):
    supplied = envelope(encoded(valid), finish_reason=None)
    if missing_reason:
        del supplied["choices"][0]["finish_reason"]
    with pytest.raises(ResponseValidationError) as caught:
        core.decode(supplied, prepared)
    assert caught.value.code == "MINIMUM_DATA_PROVIDER_FINISH"
    assert caught.value.provider_result.raw_text == encoded(valid)


@pytest.mark.parametrize("invalid", [None, [], {}, {"choices": []}, {"choices": [{}]}])
def test_malformed_provider_envelope_cannot_produce_verdicts(prepared, invalid):
    with pytest.raises(ResponseValidationError) as caught:
        core.decode(invalid, prepared)
    assert caught.value.code == "MINIMUM_DATA_PROVIDER_ERROR"


@pytest.mark.parametrize("message", [None, []])
def test_malformed_message_object_returns_bounded_error_with_provider_result(prepared, message):
    supplied = envelope("unused")
    supplied["choices"][0]["message"] = message
    original = deepcopy(supplied)
    with pytest.raises(ResponseValidationError) as caught:
        core.decode(supplied, prepared)
    assert caught.value.code == "MINIMUM_DATA_PROVIDER_ERROR"
    result = caught.value.provider_result
    assert isinstance(result, ProviderResult)
    assert result.provider == "openai_compatible" and isinstance(result.raw_text, str)
    assert result.usage["cost"] is None
    assert supplied == original


def test_malformed_usage_object_returns_bounded_error_with_provider_result(prepared, valid):
    supplied = envelope(encoded(valid))
    supplied["usage"] = ["invalid"]
    original = deepcopy(supplied)
    with pytest.raises(ResponseValidationError) as caught:
        core.decode(supplied, prepared)
    assert caught.value.code == "MINIMUM_DATA_PROVIDER_ERROR"
    result = caught.value.provider_result
    assert isinstance(result, ProviderResult)
    assert result.provider == "openai_compatible" and isinstance(result.raw_text, str)
    assert result.usage["cost"] is None
    assert supplied == original


def test_multiple_provider_choices_cannot_silently_select_a_favorable_verdict(prepared, valid):
    supplied = envelope(encoded(valid))
    alternate = deepcopy(valid)
    alternate["results"][0]["verdict"] = "partial"
    alternate["results"][0]["conditions"] = "gap"
    supplied["choices"].append(envelope(encoded(alternate))["choices"][0])
    with pytest.raises(ResponseValidationError) as caught:
        core.decode(supplied, prepared)
    assert caught.value.code == "MINIMUM_DATA_PROVIDER_ERROR"


@pytest.mark.parametrize(
    "finish,content,expected",
    [
        ("length", '{"results":[', "OUTPUT_TRUNCATED"),
        ("content_filter", "", "PROVIDER_REFUSAL"),
        ("stop", "", "EMPTY_RESPONSE"),
        ("stop", None, "PROVIDER_RESPONSE_ERROR"),
    ],
)
def test_provider_failure_never_infers_missing_verdicts(prepared, finish, content, expected):
    with pytest.raises(ResponseValidationError) as caught:
        core.decode(envelope(content, finish_reason=finish), prepared)
    assert caught.value.code == expected
    assert caught.value.provider_result.raw_text == (content or "")


def test_nested_prepared_mutation_breaks_the_request_binding(prepared, valid):
    prepared.assigned_quotation_ids["assertion-alpha"] = ("quote-blue",)
    rejected(encoded(valid), prepared, "MINIMUM_DATA_PREPARED_CHANGED")


@pytest.mark.parametrize("question_index", [0, 1])
def test_frozen_public_candidate_compiles_without_changing_assertions_or_own_quotes(
    config, question_index
):
    source_path = (
        Path(__file__).parents[2]
        / "docs/execution/evidence/phase164/MINIMUM-DATA-CANDIDATE164.json"
    )
    frozen = source_path.read_bytes()
    assert hashlib.sha256(frozen).hexdigest() == (
        "0b5db84cee3630e2a8993d1fb320318fa0f276946ffddb7b5191391fccbc1156"
    )
    candidate = json.loads(frozen)
    original = deepcopy(candidate)
    selected = candidate["questions"][question_index]
    prepared = core.prepare(config, candidate, question_index=question_index)
    expected_ids = [statement["statement_id"] for statement in selected["statements"]]
    expected_assignments = {
        statement["statement_id"]: tuple(statement["assigned_quotation_ids"])
        for statement in selected["statements"]
    }
    own_union = {
        quotation_id
        for assigned_ids in expected_assignments.values()
        for quotation_id in assigned_ids
    }
    expected_quotes = [
        quote for quote in candidate["quotations"] if quote["quotation_id"] in own_union
    ]
    assert candidate == original
    assert prepared.statement_ids == tuple(expected_ids)
    assert prepared.assigned_quotation_ids == expected_assignments
    data = json.loads(prepared.messages[1]["content"])
    assert data == {
        "question": selected["question"],
        "statements": selected["statements"],
        "source": candidate["source"],
        "quotations": expected_quotes,
    }
    rows = prepared.response_schema["properties"]["results"]
    assert rows["type"] == "array"
    assert rows["minItems"] == rows["maxItems"] == len(expected_ids)
    assert rows["items"]["type"] == "object"
    assert rows["items"]["properties"]["statement_id"]["enum"] == expected_ids
    assert prepared.wire == provider_payload(
        config, prepared.messages, prepared.response_schema, core.VERSION
    )
    assert prepared.wire["response_format"] == {"type": "json_object"}
    system = prepared.wire["messages"][0]["content"]
    assert "separate objects" in system
    marker = "Match this JSON schema: "
    assert marker in system
    assert json.loads(system.split(marker, 1)[1]) == provider_schema(
        prepared.response_schema, "openai_compatible"
    )
