"""Attributable V5 writes, separate from the historical typed V2 writer."""

from . import memory_v2 as legacy, memory_v5 as conditions

WRITER_VERSION = "typed_memory_v5"


def prepare_operations(text, candidates=None):
    """Keep exact source statements; never broaden a conditional preference."""
    plan = {
        "version": WRITER_VERSION,
        "source_hash": legacy.digest(text),
        "operations": [],
        "withheld": [],
    }
    if not isinstance(text, str) or len(text.encode("utf-8")) > conditions.MAX_SOURCE_BYTES:
        plan["withheld"].append({"operation": "NO_OP", "reason": "memory_source_unavailable"})
        return plan
    proposed = legacy.deterministic_operations(text) if candidates is None else candidates
    if not isinstance(proposed, list) or len(proposed) > 5:
        raise ValueError("V5 memory writes exceed the frozen five-operation contract")
    for candidate in proposed:
        try:
            item = legacy.validate_operation(candidate, text)
        except (KeyError, TypeError, ValueError):
            plan["withheld"].append(
                {"operation": "NO_OP", "reason": "memory_source_operation_invalid"}
            )
            continue
        if item["category"] == "preference":
            quote = item["source_quote"]
            explicit_command = bool(
                conditions.CONFIRMED_ACTION.search(quote) and legacy.DURABLE.search(quote)
            )
            scope, reason, span = conditions.condition(
                quote, text, confirmed=explicit_command, erasure=item["operation"] == "DELETE"
            )
            if scope is None:
                plan["withheld"].append(
                    {
                        "operation": "NO_OP",
                        "field_key": item["field_key"],
                        "reason": reason,
                        "source_quote_range": span,
                    }
                )
                continue
            item["scope"] = scope
        plan["operations"].append(item)
    return plan


def extract_operations(text, config, budget=None, on_attempt=None, *, api_key=None, adapter=None):
    """Retain the finite extraction wire schema and independently guard its writes."""
    from .memory_extraction import extract_operations as extract_legacy_schema

    def record(payload):
        if on_attempt:
            on_attempt(
                {
                    **payload,
                    "purpose": "memory_extraction_v5",
                    "writer_version": WRITER_VERSION,
                    "extraction_schema_version": legacy.WRITER_VERSION,
                }
            )

    result = extract_legacy_schema(
        text, config, budget, record if on_attempt else None, api_key=api_key, adapter=adapter
    )
    plan = prepare_operations(text, result["operations"])
    return {
        **result,
        "version": WRITER_VERSION,
        "extraction_schema_version": legacy.WRITER_VERSION,
        "condition_policy": conditions.freeze_policy(),
        "operations": plan["operations"],
        "withheld": plan["withheld"],
    }
