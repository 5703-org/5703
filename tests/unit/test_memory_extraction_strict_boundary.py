"""Reject ambiguous provider JSON before attributable memory operations are admitted."""

import json
import pytest
from generation.types import ModelConfig, ProviderResult, RequestBudget
from personalisation import memory_extraction as extraction

SOURCE = "I prefer concise explanations."
OP = {
    "operation": "ADD",
    "category": "preference",
    "field_key": "detail_level",
    "content": SOURCE,
    "source_quote": SOURCE,
    "scope": "global",
    "expires_at": None,
}


@pytest.fixture(autouse=True)
def no_network_counter(monkeypatch):
    class Counter:
        def __init__(self, *args):
            pass

        def request_input(self, *args):
            return 200

    monkeypatch.setattr(extraction, "TokenCounter", Counter)
    monkeypatch.setattr(
        "generation.adapters.open_provider",
        lambda *a, **k: pytest.fail("Provider dispatch forbidden"),
    )


class RecordedTransport:
    def __init__(self, raw):
        self.raw = raw
        self.calls = 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        assert self.calls == 1
        return ProviderResult(raw_text=self.raw, usage={"total_tokens": 20})


@pytest.mark.parametrize(
    "raw",
    [
        '{"operations":[{"operation":"DELETE","operation":"ADD",'
        + json.dumps(OP)[1:].split(",", 1)[1]
        + "]}",
        '{"operations":[{"operation":"ADD","category":"preference","field_key":"detail_level","content":"other","content":'
        + json.dumps(SOURCE)
        + ',"source_quote":'
        + json.dumps(SOURCE)
        + ',"scope":"global","expires_at":null}]}',
        '{"operations":[],"operations":' + json.dumps([OP]) + "}",
        '{"operations":[],"operations":[]}',
    ],
)
def test_duplicate_keys_are_terminal_invalid_without_write_or_retry(raw):
    transport = RecordedTransport(raw)
    result = extraction.extract_operations(
        SOURCE, ModelConfig(), RequestBudget(max_calls=1, max_active_seconds=60), adapter=transport
    )
    assert result["error"] and result["error"]["code"] == "MEMORY_EXTRACTION_INVALID"
    assert result["operations"] == [] and transport.calls == 1


def test_valid_exact_operation_retains_original_unicode_and_source():
    transport = RecordedTransport(json.dumps({"operations": [OP]}))
    result = extraction.extract_operations(
        SOURCE, ModelConfig(), RequestBudget(max_calls=1, max_active_seconds=60), adapter=transport
    )
    assert result["error"] is None and result["operations"] == [OP]


def test_paraphrase_is_still_rejected():
    transport = RecordedTransport(
        json.dumps({"operations": [{**OP, "content": "The learner likes brief answers."}]})
    )
    result = extraction.extract_operations(
        SOURCE, ModelConfig(), RequestBudget(max_calls=1, max_active_seconds=60), adapter=transport
    )
    assert result["error"]["code"] == "MEMORY_EXTRACTION_INVALID" and not result["operations"]
