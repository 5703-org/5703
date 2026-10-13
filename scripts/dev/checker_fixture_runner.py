"""Offline checker runner with the normal serializer, parser and publication gates.

There is one execution path, including for saved real responses. No authored
accept boolean bypasses the application. Paid dispatch and credential loading
are deliberately unavailable until this runner has completed offline review.
"""

from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
import hashlib
import io
import json
import os
import re
from pathlib import Path
import socket
import stat
import time
from unittest.mock import patch

from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget, adapters
from generation.types import ProviderResult

DUMMY_KEY = "dummy-119-no-credential"
URL = "https://api.deepseek.com/v1/chat/completions"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, code):
    if not value:
        raise RuntimeError(code)


def safe(path):
    require(path.is_absolute(), "ABSOLUTE_OUTPUT_REQUIRED")
    for parent in [path, *path.parents]:
        if parent.exists():
            info = parent.lstat()
            require(
                not parent.is_symlink()
                and not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT,
                "OUTPUT_REPARSE_FORBIDDEN",
            )


def save(path, value):
    safe(path)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())


def artifact(output, name):
    path = output / name
    require(path.resolve().parent == output.resolve(), "ARTIFACT_OUTSIDE_OUTPUT")
    safe(path)
    return path


@contextmanager
def network_fence():
    def denied(*args, **kwargs):
        raise RuntimeError("OFFLINE_RUNNER_NETWORK_AND_DNS_FORBIDDEN")

    with (
        patch.object(socket, "socket", denied),
        patch.object(socket, "create_connection", denied),
        patch.object(socket, "getaddrinfo", denied),
        patch.object(socket, "gethostbyname", denied),
        patch.object(socket, "gethostbyname_ex", denied),
        patch.object(socket, "gethostbyaddr", denied),
    ):
        yield


class Response(io.BytesIO):
    def __init__(self, raw, *, status=200, headers=None):
        super().__init__(raw)
        self.status = status
        self.headers = headers if headers is not None else {"Content-Length": str(len(raw))}


def framed_read(response):
    length = response.headers.get("Content-Length")
    transfer = response.headers.get("Transfer-Encoding")
    if hasattr(response.headers, "get_all"):
        require(len(response.headers.get_all("Content-Length", [])) <= 1, "AMBIGUOUS_FRAMING")
    require(not (length is not None and transfer is not None), "AMBIGUOUS_FRAMING")
    raw = response.read(1048577)
    require(len(raw) <= 1048576, "RESPONSE_SIZE_INVALID")
    if length is not None:
        require(length.isdigit() and len(raw) == int(length), "PARTIAL_RESPONSE_UNKNOWN_RETAINED")
    else:
        require(response.isclosed(), "PARTIAL_RESPONSE_UNKNOWN_RETAINED")
    return raw


def strict_outer(raw, secret=DUMMY_KEY):
    def unique(items):
        result = {}
        for name, value in items:
            require(name not in result, "DUPLICATE_RESPONSE_JSON_KEYS")
            result[name] = value
        return result

    def no_constant(value):
        raise RuntimeError("NONFINITE_RESPONSE_JSON")

    value = json.loads(raw, object_pairs_hook=unique, parse_constant=no_constant)
    require(type(value) is dict, "OUTER_RESPONSE_NOT_OBJECT")

    # The runner loads no real credentials. Withhold literal and decoded echoes
    # of its dummy credential too, exercising the ordinary privacy boundary.
    def echo(item, depth=0):
        if isinstance(item, dict):
            return any(echo(key, depth) or echo(val, depth) for key, val in item.items())
        if isinstance(item, list):
            return any(echo(val, depth) for val in item)
        if isinstance(item, str):
            if secret in item:
                return True
            expanded = item
            for _ in range(8):
                collapsed = expanded.replace("\\\\", "\\")
                if collapsed == expanded:
                    break
                expanded = collapsed
            require("\\\\" not in expanded, "PRIVACY_DECODE_LIMIT_WITHHELD")
            expanded = re.sub(
                r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match[1], 16)), expanded
            )
            if expanded != item:
                require(depth < 8, "PRIVACY_DECODE_LIMIT_WITHHELD")
                if echo(expanded, depth + 1):
                    return True
            try:
                decoded = json.loads(item)
            except (ValueError, TypeError):
                return False
            if decoded != item:
                require(depth < 8, "PRIVACY_DECODE_LIMIT_WITHHELD")
                return echo(decoded, depth + 1)
        return False

    require(secret.encode() not in raw and not echo(value), "KEY_ECHO_WITHHELD")
    return value


class FrozenGeneration:
    def __init__(self, draft):
        self.draft = draft
        self.calls = 0

    def generate(self, messages, **kwargs):
        require(
            kwargs["request_context"]["purpose"] == "generation" and self.calls == 0,
            "ONLY_ONE_FROZEN_DRAFT_NO_GENERATION_OR_REPAIR",
        )
        self.calls += 1
        return ProviderResult(
            raw_text=json.dumps(self.draft),
            finish_reason="stop",
            provider="saved-fixture",
            model="no-provider",
            request_submitted=False,
        )


def preflight(plan):
    require(
        type(plan) is dict and type(plan.get("config")) is dict,
        "FROZEN_CONFIG_REQUIRED_BEFORE_SEND",
    )
    config = ModelConfig.from_dict(plan["config"])
    require(
        config.base_url == "https://api.deepseek.com/v1"
        and config.model == "deepseek-flash"
        and config.max_tokens == 4096
        and config.temperature == 0
        and config.thinking_enabled is False
        and config.structured_output_mode == "json_object"
        and config.token_limit_parameter == "max_tokens",
        "EXACT_FROZEN_OFFICIAL_CONFIG_REQUIRED",
    )
    rows, labels = plan.get("rows"), plan.get("labels")
    require(type(rows) is list and 1 <= len(rows) <= 8, "FINITE_FIXTURE_SCOPE_REQUIRED")
    require(
        type(labels) is list and type(plan.get("source_bindings")) is dict, "FROZEN_INPUTS_REQUIRED"
    )
    require(
        all(
            type(row) is dict and {"id", "case", "control", "variant"} <= row.keys() for row in rows
        )
        and all(
            type(row["id"]) is str
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", row["id"])
            and ".." not in row["id"]
            for row in rows
        ),
        "UNIT_FIELDS_REQUIRED_BEFORE_SEND",
    )
    require(
        all(
            type(label) is dict
            and {"case", "control", "question", "draft", "expected_accept"} <= label.keys()
            for label in labels
        )
        and type(plan["source_bindings"].get("cases")) is dict,
        "FROZEN_LABEL_AND_SOURCE_FIELDS_REQUIRED",
    )
    require(len({row["id"].casefold() for row in rows}) == len(rows), "DUPLICATE_UNIT_ID")
    for row in rows:
        matches = [
            item
            for item in labels
            if (item["case"], item["control"]) == (row["case"], row["control"])
        ]
        require(
            len(matches) == 1 and type(matches[0]["expected_accept"]) is bool,
            "EXACT_FROZEN_LABEL_REQUIRED",
        )
        require(row["variant"] in {"A", "B"}, "FIXTURE_VARIANT_INVALID")
        require(row["case"] in plan["source_bindings"]["cases"], "ORIGINAL_SOURCE_CASE_MISSING")
        label = matches[0]
        require(
            type(label["question"]) is str
            and bool(label["question"].strip())
            and type(label["draft"]) is dict
            and bool(label["draft"]),
            "QUESTION_AND_DRAFT_REQUIRED",
        )
        source = plan["source_bindings"]["cases"][row["case"]]
        require(
            type(source) is dict
            and type(source.get("evidence")) is list
            and bool(source["evidence"])
            and type(source.get("original_mapping")) is dict
            and bool(source["original_mapping"]),
            "SOURCE_STRUCTURE_REQUIRED",
        )
        for evidence in source["evidence"]:
            require(
                type(evidence) is dict
                and type(evidence.get("pages")) is list
                and bool(evidence["pages"])
                and all(type(page) is int and page > 0 for page in evidence["pages"])
                and type(evidence.get("text")) is str
                and bool(evidence["text"].strip()),
                "SOURCE_EVIDENCE_FIELDS_REQUIRED",
            )
    return config


def make_request(row, plan, config):
    label = next(
        item
        for item in plan["labels"]
        if (item["case"], item["control"]) == (row["case"], row["control"])
    )
    source = deepcopy(plan["source_bindings"]["cases"][row["case"]])
    for index, evidence in enumerate(source["evidence"], 1):
        evidence.update(
            context_order=index,
            locator="PDF physical pages " + ", ".join(str(page) for page in evidence["pages"]),
        )
    value = GenerationRequest(
        request_id="offline119-" + row["id"],
        mode="interactive_chat",
        condition="E1",
        question=label["question"],
        enhancement_version="learning_enhancement_v1",
        evidence=source["evidence"],
        source_map=source["original_mapping"],
        config=config,
        checker_config=config,
        prepared_query={"intent": "factual", "needs_clarification": False},
        teaching_context={"turn_role": "user_question", "teaching_mode": "direct", "help_level": 0},
        generation_context_policy="legacy_context_v1",
        reliability_policy="evidence_reliability_v5",
        source_block_policy="raw_definition_block_partition_v2",
        source_relation_policy="source_relation_contract_v2",
        checker_schema_policy="textbook_context_qualification_v1"
        if row["variant"] == "B"
        else None,
        qualification_source_transport=plan.get("source_transport", "legacy_origin_v2"),
    )
    return value, label


class Captured(BaseException):
    pass


def prepare(plan):
    """Freeze the actual LLMAdapter serialization before any receipt or transport."""
    config = preflight(plan)
    result = deepcopy(plan)
    with network_fence():
        for row in result["rows"]:
            value, label = make_request(row, result, config)
            captured = {}

            def compiler(envelope, **kwargs):
                require(not captured, "ONLY_ONE_COMPILED_CHECKER")
                captured["wire"] = envelope.data
                raise Captured()

            try:
                with patch.object(adapters, "open_provider", compiler):
                    GenerationService(
                        FrozenGeneration(label["draft"]),
                        checker_adapter=adapters.LLMAdapter(config, api_key=DUMMY_KEY),
                    ).generate(value, RequestBudget(max_calls=2))
            except Captured:
                pass
            require("wire" in captured, "FIXTURE_COMPILER_DID_NOT_REACH_CHECKER")
            wire = captured["wire"]
            row.update(
                body=json.loads(wire),
                wire_sha256=sha(wire),
                wire_bytes=len(wire),
                input_upper_tokens=len(wire) + 2048,
                output_limit=4096,
                hold_CNY=str((Decimal(len(wire) + 2048) + Decimal(4096) * 4) / 1000000),
            )
    result.update(offline_only=True, real_dispatch_enabled=False)
    return result


class Ledger:
    def __init__(self, rows, cap):
        self.cap = Decimal(cap)
        require(self.cap.is_finite() and self.cap > 0, "FINITE_POSITIVE_CAP_REQUIRED")
        self.known = Decimal(0)
        self.unknown = Decimal(0)
        self.reserved = sum(Decimal(row["hold_CNY"]) for row in rows)
        self.attempts = 0
        require(self.reserved <= self.cap, "SIMULATED_CAP_INSUFFICIENT_BEFORE_SEND")

    def dispatch(self, row):
        hold = Decimal(row["hold_CNY"])
        require(self.attempts < 8 and self.reserved >= hold, "FINITE_UNIT_RESERVATION_REQUIRED")
        require(self.known + self.unknown + self.reserved <= self.cap, "SIMULATED_CAP_EXCEEDED")
        self.reserved -= hold
        self.unknown += hold
        self.attempts += 1

    def settle(self, row, usage, commit):
        incoming, outgoing = usage.get("prompt_tokens"), usage.get("completion_tokens")
        require(
            type(incoming) is int and type(outgoing) is int and min(incoming, outgoing) >= 0,
            "USAGE_UNKNOWN_RETAINED",
        )
        upper = (Decimal(incoming) + Decimal(outgoing) * 4) / 1000000
        hold = Decimal(row["hold_CNY"])
        if upper > hold:
            self.unknown += upper - hold
            raise RuntimeError("OBSERVED_COST_OVER_HOLD_UNKNOWN_RETAINED")
        require(
            incoming <= row["input_upper_tokens"] and outgoing <= row["output_limit"],
            "USAGE_BOUND_INVALID_UNKNOWN_RETAINED",
        )
        commit(upper)  # A durable receipt is mandatory before a hold is released.
        self.known += upper
        self.unknown -= hold

    def view(self):
        return dict(
            simulated_known_upper_CNY=str(self.known),
            simulated_UNKNOWN_CNY=str(self.unknown),
            simulated_unused_reservation_CNY=str(self.reserved),
            simulated_transport_attempts=self.attempts,
        )


def run(plan, *, transport, output, cap="1.00", live_boundary=None):
    """Run full application judgments; a local transport never supplies the score."""
    config = preflight(plan)  # The118 missing-config defect fails before claim or transport.
    if live_boundary is None:
        require(plan.get("offline_only") is True, "PAID_DISPATCH_PAUSED")
    else:
        live_boundary.preflight(plan, cap)
    offline = live_boundary is None
    for row in plan["rows"]:
        wire = encoded(row["body"])
        require(
            sha(wire) == row["wire_sha256"] and len(wire) == row["wire_bytes"],
            "FROZEN_WIRE_CHANGED",
        )
        require(
            row["input_upper_tokens"] == len(wire) + 2048
            and row["output_limit"] == 4096
            and Decimal(row["hold_CNY"])
            == (Decimal(len(wire) + 2048) + Decimal(4096) * 4) / 1000000,
            "FROZEN_METERING_BOUNDS_CHANGED",
        )
    output = Path(output).absolute()
    safe(output)
    require(not output.exists(), "EXCLUSIVE_OUTPUT_REQUIRED_NO_RETRY")
    ledger = Ledger(plan["rows"], cap)
    if not offline:
        live_boundary.authorize()
    output.mkdir()
    save(
        output / "claim.json",
        dict(
            offline_only=offline,
            cap_CNY=cap,
            units=[row["id"] for row in plan["rows"]],
            real_requests=0,
        ),
    )
    results, stop = [], None
    with network_fence() if offline else live_boundary.scope():
        for row in plan["rows"]:
            if stop:
                result = dict(id=row["id"], status="NOT_RUN", reason=stop, correctness=None)
            else:
                calls, receipt = [], {}
                start = time.perf_counter()

                def open_fixture(envelope, **kwargs):
                    require(not calls, "ONLY_ONE_CHECKER_NO_REPAIR_OR_RETRY")
                    require(
                        envelope.full_url == URL and envelope.get_method() == "POST",
                        "EXACT_CHECKER_ENDPOINT_REQUIRED",
                    )
                    require(
                        sha(envelope.data) == row["wire_sha256"], "ACTUAL_SERIALIZATION_CHANGED"
                    )
                    save(
                        output / (row["id"] + "-SEND_INTENT.json"),
                        dict(id=row["id"], wire_sha256=sha(envelope.data), offline_only=offline),
                    )
                    ledger.dispatch(row)
                    calls.append(1)
                    transport_start = time.perf_counter()
                    with transport(envelope, row) as response:
                        status = response.status
                        raw = framed_read(response)
                    receipt["API_elapsed_ms" if not offline else "fixture_transport_elapsed_ms"] = (
                        time.perf_counter() - transport_start
                    ) * 1000
                    outer = strict_outer(raw, DUMMY_KEY if offline else live_boundary.secret)
                    with artifact(output, row["id"] + "-raw-response.json").open("xb") as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    receipt.update(raw_sha256=sha(raw), HTTP_status=status)

                    def commit(upper):
                        save(
                            output / (row["id"] + "-settlement.json"),
                            dict(
                                offline_only=offline,
                                raw_sha256=sha(raw),
                                **{
                                    "simulated_upper_CNY" if offline else "known_upper_CNY": str(
                                        upper
                                    )
                                },
                                usage=outer.get("usage"),
                                rates_are_saved_test_inputs=offline,
                            ),
                        )

                    ledger.settle(row, outer.get("usage") or {}, commit)
                    require(status == 200, "PROVIDER_HTTP_CONTRACT_INVALID")
                    require(
                        len(outer.get("choices", [])) == 1
                        and outer["choices"][0]["finish_reason"] == "stop",
                        "PROVIDER_RESPONSE_CONTRACT_INVALID",
                    )
                    return Response(raw, status=status)

                try:
                    value, label = make_request(row, plan, config)
                    with patch.object(adapters, "open_provider", open_fixture):
                        outcome = GenerationService(
                            FrozenGeneration(label["draft"]),
                            checker_adapter=adapters.LLMAdapter(config, api_key=DUMMY_KEY),
                        ).generate(value, RequestBudget(max_calls=2))
                    check = outcome.checks[0] if outcome.checks else {}
                    incomplete_citations = (
                        plan.get("source_transport") in {"ordinary_qa_v1", "ordinary_qa_compact_v2"}
                        and any(issue.get("code") == "ACTUAL_CITATION_ASSESSMENT_MISSING"
                                for issue in check.get("structural_issues", []))
                    )
                    valid = bool(
                        len(calls) == 1
                        and check.get("validation_state") == "validated"
                        and not check.get("checker_inconsistencies")
                        and not incomplete_citations
                    )
                    acceptance = check.get("accepted") if valid else None
                    result = dict(
                        id=row["id"],
                        status="INCOMPLETE_VERIFICATION" if incomplete_citations else "VALID_SEMANTIC_RESULT" if valid else "TECHNICAL_STOP",
                        technical_valid=valid,
                        semantic_accept=acceptance,
                        semantic_assessment_state="verification_incomplete" if incomplete_citations else "assessed" if valid else "invalid_unknown",
                        expected_accept=label["expected_accept"],
                        correctness=acceptance == label["expected_accept"] if valid else None,
                        false_accept=acceptance is True and not label["expected_accept"]
                        if valid
                        else None,
                        false_reject=acceptance is False and label["expected_accept"]
                        if valid
                        else None,
                        checker=check,
                        pipeline_error=outcome.error,
                        receipt=receipt,
                        local_fixture_elapsed_ms=(time.perf_counter() - start) * 1000,
                        offline_only=offline,
                        real_requests=0 if offline else len(calls),
                    )
                    if not valid:
                        stop = "CHECKER_OR_TRANSPORT_INVALID_UNKNOWN_NO_RETRY"
                except Exception as error:
                    stop = (
                        str(error)
                        if type(error) is RuntimeError and str(error).replace("_", "").isalnum()
                        else type(error).__name__
                    )
                    result = dict(
                        id=row["id"],
                        status="TECHNICAL_STOP",
                        reason=stop,
                        correctness=None,
                        semantic_accept=None,
                        semantic_assessment_state="invalid_unknown",
                        receipt=receipt,
                    )
            results.append(result)
            save(output / (row["id"] + "-result.json"), result)
    final = dict(
        status="STOPPED_NO_RETRY" if stop else "COMPLETED_ALL_UNITS",
        results=results,
        **ledger.view(),
        real_requests=0 if offline else ledger.attempts,
        real_key_reads=0 if offline else 1,
        DB_operations=0,
        generation_requests=0,
        repair_requests=0,
        paid_retry_requests=0,
        scientific_quality_measurement=not offline,
        global_project_metric=False,
    )
    if not offline:
        for old, new in [
            ("simulated_known_upper_CNY", "known_upper_CNY"),
            ("simulated_UNKNOWN_CNY", "UNKNOWN_protection_CNY"),
            ("simulated_unused_reservation_CNY", "unused_new_reservation_CNY"),
            ("simulated_transport_attempts", "dispatch_intents"),
        ]:
            final[new] = final.pop(old)
    save(output / "terminal.json", final)
    return final


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument(
        "--responses", required=True, help="JSON mapping unit IDs to local raw outer-response paths"
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_bytes())
    paths = json.loads(Path(args.responses).read_bytes())

    def transport(envelope, row):
        return Response(Path(paths[row["id"]]).read_bytes())

    final = run(plan, transport=transport, output=args.output)
    print(json.dumps({name: value for name, value in final.items() if name != "results"}))


if __name__ == "__main__":
    main()
