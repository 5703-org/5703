"""Frozen-source transport, independent of model semantic labels."""

import json
from copy import deepcopy
import pytest
from generation.types import ModelConfig, RequestBudget, ProviderResult
from personalisation import memory_extraction as old, memory_source_selection_v1 as selection
from personalisation import memory_writer_v6 as writer
from test_memory_extraction_strict_boundary import no_network_counter

SOURCE = "I prefer detailed biology explanations."


def operation(text=SOURCE):
    _, _, reference = selection.prepare(text, old.SCHEMA)
    return {
        "operation": "ADD",
        "category": "preference",
        "field_key": "detail_level",
        "source_ref": reference,
        "expires_at": None,
    }


class Adapter:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, messages, **options):
        self.calls.append((deepcopy(messages), deepcopy(options)))
        assert len(self.calls) == 1
        return ProviderResult(raw_text=json.dumps(self.response), usage={"total_tokens": 20})


def run(response, text=SOURCE):
    adapter = Adapter(response)
    result = writer.extract_operations(
        text, ModelConfig(), RequestBudget(max_calls=1, max_active_seconds=60), adapter=adapter
    )
    return result, adapter


def test_model_selects_bound_source_and_application_keeps_original():
    result, adapter = run({"operations": [operation()]})
    assert result["error"] is None
    assert result["operations"][0]["content"] == result["operations"][0]["source_quote"] == SOURCE
    assert result["operations"][0]["scope"] == "biology"
    messages, options = adapter.calls[0]
    assert json.loads(messages[1]["content"])["exact_statement"] == SOURCE
    assert options["response_schema_name"] == selection.VERSION
    properties = options["response_schema"]["properties"]["operations"]["items"]["properties"]
    assert not {"content", "source_quote", "scope"}.intersection(properties)


@pytest.mark.parametrize(
    "fault", ["foreign", "paraphrase", "scope", "duplicate", "category", "assessment", "delete"]
)
def test_invalid_selection_cannot_write_or_retry(fault):
    row = operation()
    rows = [row]
    if fault == "foreign":
        row["source_ref"] = "statement_another_message"
    if fault == "paraphrase":
        row["content"] = "The learner likes detailed explanations."
    if fault == "scope":
        row["scope"] = "global"
    if fault == "duplicate":
        rows.append(deepcopy(row))
    if fault == "category":
        row["category"] = "goal"
    if fault == "assessment":
        row["field_key"] = "assessment_result"
    if fault == "delete":
        row["operation"] = "DELETE"
    result, adapter = run({"operations": rows})
    assert result["error"]["code"] == "MEMORY_EXTRACTION_INVALID"
    assert result["operations"] == [] and len(adapter.calls) == 1


def test_source_binding_changes_when_any_original_character_changes():
    result, adapter = run({"operations": [operation()]}, text=SOURCE + " ")
    assert result["error"] and result["operations"] == [] and len(adapter.calls) == 1


@pytest.mark.parametrize(
    "source",
    [
        "I prefer concise biology explanations unless I ask about chemistry.",
        "My tutor said: I prefer concise biology explanations.",
        "I prefer concise economics explanations.",
    ],
)
def test_exact_origin_does_not_bypass_condition_or_attribution_guards(source):
    result, _ = run({"operations": [operation(source)]}, text=source)
    assert result["operations"] == []


def test_oversized_source_is_not_truncated_or_sent():
    result, adapter = run(
        {"operations": []}, text="I prefer detailed explanations. " + ("x" * 2100)
    )
    assert result["error"]["code"] == "MEMORY_SOURCE_SELECTION_SIZE"
    assert (
        result["operations"] == [] and not adapter.calls and result["budget"]["consumed_calls"] == 0
    )


def test_honest_empty_selection_remains_empty():
    result, adapter = run({"operations": []})
    assert result["error"] is None and not result["operations"] and len(adapter.calls) == 1
