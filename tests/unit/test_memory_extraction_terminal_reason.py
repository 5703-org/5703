"""Call exhaustion must preserve validation errors without relaxing attribution."""

import json
import pytest
from generation.types import ModelConfig, ProviderResult, RequestBudget
from personalisation import memory_extraction as extraction


@pytest.fixture(autouse=True)
def local_preparation(monkeypatch):
    class Counter:
        def __init__(self, *args):
            pass

        def request_input(self, *args):
            return 100

    monkeypatch.setattr(extraction, "TokenCounter", Counter)


class Replay:
    def __init__(self, payload):
        self.payload, self.calls = payload, 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        assert self.calls == 1
        return ProviderResult(raw_text=json.dumps(self.payload), usage={"total_tokens": 100})


@pytest.mark.parametrize(
    "payload",
    [
        {"operations": [{"operation": "ADD"}]},
        {
            "operations": [
                {
                    "operation": "ADD",
                    "category": "preference",
                    "field_key": "detail_level",
                    "content": "The learner wants short explanations.",
                    "source_quote": "I prefer concise explanations.",
                    "scope": "global",
                    "expires_at": None,
                }
            ]
        },
    ],
)
def test_single_invalid_response_preserves_cause_without_second_call(payload):
    transport = Replay(payload)
    result = extraction.extract_operations(
        "I prefer concise explanations.",
        ModelConfig(),
        RequestBudget(max_calls=1, max_active_seconds=60),
        adapter=transport,
    )
    assert result["operations"] == []
    assert result["error"]["code"] == "MEMORY_EXTRACTION_INVALID"
    assert transport.calls == 1 and len(result["usage"]) == 1


def test_zero_remaining_calls_is_not_reported_as_timeout():
    transport = Replay({"operations": []})
    result = extraction.extract_operations(
        "I prefer concise explanations.",
        ModelConfig(),
        RequestBudget(max_calls=1, consumed_calls=1, max_active_seconds=60),
        adapter=transport,
    )
    assert result["error"]["code"] == "MEMORY_CALL_LIMIT_EXCEEDED"
    assert result["operations"] == [] and transport.calls == 0
