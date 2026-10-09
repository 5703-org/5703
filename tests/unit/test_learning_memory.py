"""Explicit memory extraction eligibility and finite provider budgets."""

import json
from generation.types import ModelConfig, ProviderResult, RequestBudget
from personalisation.memory import eligible, extract_memories


class Transport:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return ProviderResult(
            raw_text=json.dumps(next(self.rows)), usage={"total_tokens": 10, "cost": None}
        )


def entry(text="I prefer simple examples before formulas."):
    return {
        "category": "preference",
        "attribute": "explanation_order",
        "content": text,
        "scope": "global",
        "source_quote": text,
        "expires_at": None,
    }


def test_temporary_difficulty_and_one_turn_are_not_memory():
    for text in [
        "I don't understand this step.",
        "Explain this more simply.",
        "I prefer an example just this once.",
    ]:
        assert not eligible(text)
        transport = Transport([])
        result = extract_memories(text, ModelConfig(), adapter=transport)
        assert not transport.calls and result["budget"]["consumed_calls"] == 0
    assert eligible("From now on, give examples before equations.")


def test_exact_explicit_source_and_separate_purpose_accounting():
    row = entry()
    transport = Transport([{"entries": [row]}])
    events = []
    result = extract_memories(
        row["source_quote"], ModelConfig(), on_attempt=events.append, adapter=transport
    )
    assert result["entries"] == [row] and result["error"] is None
    assert result["budget"]["max_calls"] == 2 and result["budget"]["max_active_seconds"] == 90
    assert result["budget"]["consumed_calls"] == 1
    assert all(e["purpose"] == "memory_extraction" for e in events)
    assert row["source_quote"] not in json.dumps(events)


def test_unattributable_extraction_has_only_one_repair_then_fails():
    row = entry()
    row["source_quote"] = "I prefer something the user never said."
    transport = Transport([{"entries": [row]}, {"entries": [row]}])
    result = extract_memories(entry()["content"], ModelConfig(), adapter=transport)
    assert result["error"]["code"] == "MEMORY_EXTRACTION_INVALID"
    assert result["entries"] == [] and len(transport.calls) == 2
    assert result["budget"]["consumed_calls"] == 2


def test_exhausted_extraction_is_not_reissued():
    transport = Transport([])
    result = extract_memories(
        entry()["content"],
        ModelConfig(),
        RequestBudget(max_calls=2, max_active_seconds=90, consumed_calls=2),
        adapter=transport,
    )
    assert not transport.calls and result["error"]["code"] == "BUDGET_EXHAUSTED"
