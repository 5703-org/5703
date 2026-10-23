"""Lossless assertion proof transport controls; authored labels are not semantic evidence."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
from urllib import request as urllib_request

import pytest

from generation import checker_encoding as legacy
from generation import checker_encoding_assertions_v3 as codec
from generation.binding_repair import table_fragments


ROOT = Path(__file__).resolve().parents[2]
POLICY = "lossless_assertion_checker_tables_v3"


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempts = []

    def blocked(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Phase200 codec tests permit no external I/O")

    for target, name in (
        (socket, "create_connection"),
        (socket, "getaddrinfo"),
        (socket.socket, "connect"),
        (socket.socket, "connect_ex"),
        (urllib_request, "urlopen"),
    ):
        monkeypatch.setattr(target, name, blocked)
    from generation.adapters import LLMAdapter
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(LLMAdapter, "generate", blocked)
    monkeypatch.setattr(Engine, "connect", blocked)
    assert Path(codec.__file__).resolve() == ROOT / "generation/checker_encoding_assertions_v3.py"
    yield
    assert not attempts, "An external call was attempted and blocked"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def table(rows):
    columns = sorted(rows[0]) if rows else []
    return {"columns": columns, "rows": [[row[key] for key in columns] for row in rows]}


def rows(value):
    if isinstance(value, list):
        return value
    return [dict(zip(value["columns"], row, strict=True)) for row in value["rows"]]


def set_cell(value, index, field, replacement):
    if isinstance(value, list):
        value[index][field] = replacement
    else:
        value["rows"][index][value["columns"].index(field)] = replacement


def packet(*, repetitions=20):
    text = 'At −2.5 °C, 水 does not rise; e\u0301 is not é. "Quoted" \\ text.\n' * repetitions
    fragments = [
        {
            "fragment_id": f"F{n:03d}",
            "evidence_id": f"ev_{n:03d}",
            "exact_text": text + str(n),
            "block_kind": "paragraph",
            "complete_block": True,
        }
        for n in range(1, 4)
    ]
    # F003 remains available globally but belongs to neither assertion's own proof.
    sources = []
    for fragment in fragments:
        sources.append(
            {
                "fragment_id": fragment["fragment_id"],
                "evidence_id": fragment["evidence_id"],
                "exact_text": fragment["exact_text"],
                "text_sha256": sha(fragment["exact_text"]),
                "source_locator": {
                    "asset_id": "authored-asset",
                    "processing_id": "authored-processing",
                    "document_version_id": "authored-version",
                    "chunk_id": "authored-chunk",
                    "source_unit_id": "authored-unit",
                    "page": 7,
                    "start": 0,
                    "end": len(fragment["exact_text"]),
                    "chunk_start": 0,
                    "chunk_end": len(fragment["exact_text"]),
                    "offset_basis": "unicode",
                },
            }
        )
    assertions = []
    claims = []
    bindings = []
    for n, selected in enumerate(([sources[1], sources[0]], [sources[0]]), 1):
        assertion = f"Condition {n}: 水 remains fixed at −2.5 °C; e\u0301 is preserved."
        eids = [row["evidence_id"] for row in selected]
        rendered = assertion + "".join(f" [{eid}]" for eid in eids)
        claims.append(
            {
                "claim_id": f"c{n}",
                "text": rendered,
                "evidence_ids": eids,
                "answer_field": "answer_text",
                "start": 0,
                "end": len(rendered),
            }
        )
        assertions.append(
            {
                "assertion_id": f"A{n:03d}",
                "claim_id": f"c{n}",
                "answer_field": "answer_text",
                "full_assertion": assertion,
                "assertion_sha256": sha(assertion),
                "evidence_ids": eids,
                "selected_source_union": deepcopy(selected),
            }
        )
        bindings.append(
            {
                "claim_id": f"c{n}",
                "citations": [
                    {
                        "evidence_id": row["evidence_id"],
                        "allowed_fragment_ids": [row["fragment_id"]],
                    }
                    for row in selected
                ],
            }
        )
    return {
        "question": "Preserve the condition and source ownership.",
        "CLAIMS": claims,
        "SOURCE_FRAGMENTS": fragments,
        "ACTUAL_CITATION_BINDINGS": bindings,
        "ASSERTION_PROOFS": {
            "version": "assertion_source_v1",
            "semantic_support_certified": False,
            "assertions": assertions,
        },
        "POLICY": {"teaching_mode": "direct", "control_evidence": True},
        "PROPOSED_DELIVERY": {
            "answer_text": "\n\n".join(row["text"] for row in claims),
            "short_answer": None,
            "follow_up_questions": [],
        },
        "PRIOR_EXPOSURE": {"disabled": True, "snapshots": []},
        "CONTEXT_COVERAGE": {"requirements": [{"id": "r1", "text": "水 at −2.5 °C"}]},
        "UNRELATED_FUTURE_FIELD": {"nested": [None, False, 0, "e\u0301", {"exact": "\n"}]},
    }


@pytest.mark.parametrize("form", ["objects", "fragment_table", "legacy_tables"])
def test_round_trip_preserves_all_fields_unicode_locators_and_own_union_order(form):
    data = packet()
    base = (
        data
        if form == "objects"
        else table_fragments(data)
        if form == "fragment_table"
        else legacy.encode(data)
    )
    before = deepcopy(base)
    encoded = codec.encode(base)
    wire = json.loads(legacy.dumps(encoded))
    assert legacy.dumps(codec.decode(wire)) == legacy.dumps(before)
    assert base == before
    assert encoded["ASSERTION_PROOF_ENCODING"]["version"] == POLICY
    assert encoded.get("CHECKER_INPUT_ENCODING") == base.get("CHECKER_INPUT_ENCODING")
    proof_rows = rows(encoded["ASSERTION_PROOFS"]["assertions"])
    assert [row["selected_source_union"] for row in proof_rows] == [["F002", "F001"], ["F001"]]
    bank = rows(encoded[codec.SOURCES])
    assert {row["fragment_id"] for row in bank} == {"F001", "F002"}
    assert all(set(row) == {"fragment_id", "text_sha256", "locator_id"} for row in bank)
    assert all("exact_text" not in row and "evidence_id" not in row for row in bank)
    for key in (
        "POLICY",
        "CONTEXT_COVERAGE",
        "PROPOSED_DELIVERY",
        "PRIOR_EXPOSURE",
        "UNRELATED_FUTURE_FIELD",
    ):
        assert encoded[key] == before[key]


@pytest.mark.parametrize(
    "defect",
    [
        "unknown_f",
        "foreign_evidence",
        "text",
        "hash",
        "source_extra",
        "source_missing",
        "duplicate_f",
        "conflicting_same_f",
        "version",
        "strict_bool",
        "assertion_hash",
    ],
)
def test_encoder_rejects_invalid_original_source_proofs(defect):
    data = packet()
    proof = data["ASSERTION_PROOFS"]
    union = proof["assertions"][0]["selected_source_union"]
    if defect == "unknown_f":
        union[0]["fragment_id"] = "F999"
    elif defect == "foreign_evidence":
        union[0]["evidence_id"] = "ev_999"
    elif defect == "text":
        union[0]["exact_text"] += " changed"
    elif defect == "hash":
        union[0]["text_sha256"] = "0" * 64
    elif defect == "source_extra":
        union[0]["unrecognized"] = True
    elif defect == "source_missing":
        del union[0]["source_locator"]
    elif defect == "duplicate_f":
        union.append(deepcopy(union[0]))
    elif defect == "conflicting_same_f":
        proof["assertions"][1]["selected_source_union"][0]["source_locator"]["page"] += 1
    elif defect == "version":
        proof["version"] = "foreign_assertion_policy"
    elif defect == "strict_bool":
        proof["semantic_support_certified"] = 0
    else:
        proof["assertions"][0]["assertion_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        codec.encode(data)


@pytest.mark.parametrize("bank", [codec.SOURCES, codec.LOCATORS, "assertions"])
@pytest.mark.parametrize(
    "defect", ["duplicate_column", "missing_cell", "extra_cell", "unknown_column"]
)
def test_decoder_rejects_malformed_tables_before_zip_can_hide_information(bank, defect):
    encoded = codec.encode(packet())
    target = encoded["ASSERTION_PROOFS"][bank] if bank == "assertions" else encoded[bank]
    assert isinstance(target, dict) and target["rows"]
    if defect == "duplicate_column":
        target["columns"].append(target["columns"][0])
        for row in target["rows"]:
            row.append(row[0])
    elif defect == "missing_cell":
        target["rows"][0].pop()
    elif defect == "extra_cell":
        target["rows"][0].append("extra")
    else:
        target["columns"].append("foreign_field")
        for row in target["rows"]:
            row.append(True)
    with pytest.raises(ValueError):
        codec.decode(encoded)


@pytest.mark.parametrize(
    "defect",
    [
        "foreign_f",
        "borrow_available_f",
        "duplicate_union",
        "union_order",
        "drop_own_source",
        "source_hash",
        "foreign_locator",
        "locator_value",
        "duplicate_bank",
        "missing_metadata",
        "metadata_version",
        "metadata_hash",
        "metadata_extra",
        "packet_field",
        "strict_bool",
        "boolean_coordinate",
    ],
)
def test_decoder_rejects_proof_corruption_and_never_expands_own_source_union(defect):
    encoded = codec.encode(packet())
    proof = encoded["ASSERTION_PROOFS"]
    assertions = proof["assertions"]
    if defect in {
        "foreign_f",
        "borrow_available_f",
        "duplicate_union",
        "union_order",
        "drop_own_source",
    }:
        replacement = {
            "foreign_f": ["F999"],
            "borrow_available_f": ["F003"],
            "duplicate_union": ["F002", "F002"],
            "union_order": ["F001", "F002"],
            "drop_own_source": ["F002"],
        }[defect]
        set_cell(assertions, 0, "selected_source_union", replacement)
    elif defect == "source_hash":
        set_cell(encoded[codec.SOURCES], 0, "text_sha256", "0" * 64)
    elif defect == "foreign_locator":
        set_cell(encoded[codec.SOURCES], 0, "locator_id", "L999")
    elif defect == "locator_value":
        set_cell(encoded[codec.LOCATORS], 0, "page", 99)
    elif defect == "duplicate_bank":
        encoded[codec.SOURCES]["rows"].append(deepcopy(encoded[codec.SOURCES]["rows"][0]))
    elif defect == "missing_metadata":
        del encoded["ASSERTION_PROOF_ENCODING"]
    elif defect == "metadata_version":
        encoded["ASSERTION_PROOF_ENCODING"]["version"] = "unknown"
    elif defect == "metadata_hash":
        encoded["ASSERTION_PROOF_ENCODING"]["original_data_sha256"] = "0" * 64
    elif defect == "metadata_extra":
        encoded["ASSERTION_PROOF_ENCODING"]["unrecognized"] = True
    elif defect == "packet_field":
        encoded["POLICY"]["teaching_mode"] = "hint"
    elif defect == "boolean_coordinate":
        set_cell(encoded[codec.LOCATORS], 0, "start", False)
    else:
        proof["semantic_support_certified"] = 0
    with pytest.raises(ValueError):
        codec.decode(encoded)


class WireCounter:
    def __init__(self, tied=False):
        self.calls = []
        self.tied = tied

    def request_input(self, messages, schema, schema_name):
        self.calls.append((deepcopy(messages), deepcopy(schema), schema_name))
        return (
            100
            if self.tied
            else len(
                legacy.dumps({"messages": messages, "schema": schema, "name": schema_name}).encode(
                    "utf-8"
                )
            )
        )


@pytest.mark.parametrize("tied", [False, True])
def test_selector_uses_actual_complete_wire_counts_and_strictly_smaller_rule(tied):
    data = packet()
    messages = [
        {"role": "system", "content": "Keep all proof gates."},
        {"role": "user", "content": legacy.dumps(data)},
    ]
    schema = {
        "type": "object",
        "properties": {"claims": {"type": "array"}},
        "required": ["claims"],
        "additionalProperties": False,
    }
    before = deepcopy((data, messages, schema))
    old_counter = WireCounter(tied)
    old_messages, old_report = legacy.select_encoding(
        data, messages, old_counter, schema, "unchanged_full_schema"
    )
    counter = WireCounter(tied)
    selected, report = codec.select_encoding(
        data, messages, counter, schema, "unchanged_full_schema"
    )
    raw = json.loads(selected[-1]["content"])
    assert (data, messages, schema) == before
    assert selected[:-1] == messages[:-1]
    assert all(call[1:] == (schema, "unchanged_full_schema") for call in counter.calls)
    actual = counter.request_input(selected, schema, "unchanged_full_schema")
    assert report["encoded_input_tokens"] == actual
    assert actual <= old_report["encoded_input_tokens"]
    if tied:
        assert selected == old_messages
        assert "ASSERTION_PROOF_ENCODING" not in raw
    else:
        assert "ASSERTION_PROOF_ENCODING" in raw
        assert actual < old_report["encoded_input_tokens"]


def test_tiny_packet_prefers_legacy_when_proof_metadata_costs_more():
    data = packet(repetitions=1)
    data["ASSERTION_PROOFS"]["assertions"] = []
    data["CLAIMS"] = []
    data["ACTUAL_CITATION_BINDINGS"] = []
    messages = [{"role": "user", "content": legacy.dumps(data)}]
    old, _ = legacy.select_encoding(data, messages, WireCounter(), {}, "full")
    selected, _ = codec.select_encoding(data, messages, WireCounter(), {}, "full")
    assert selected == old


@pytest.mark.parametrize(
    "configured,fields,expected",
    [
        (POLICY, {"assertion_source_policy": "assertion_source_v1"}, POLICY),
        (POLICY, {}, legacy.VERSION),
        (POLICY, {"assertion_source_policy": None}, legacy.VERSION),
        (POLICY, {"assertion_source_policy": "assertion_source_v2"}, legacy.VERSION),
        (legacy.VERSION, {"assertion_source_policy": "assertion_source_v1"}, legacy.VERSION),
    ],
)
def test_submission_policy_is_exact_opt_in_and_preserves_legacy(configured, fields, expected):
    from generation import ModelConfig

    assert (
        codec.submission_policy(
            configured, fields, ModelConfig(provider="openai", model="gpt-6-luna")
        )
        == expected
    )


def load_assertion_helpers():
    path = ROOT / "tests/unit/test_assertion_provenance161.py"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "af26279f2cf1278f92ab81114f51997c00859d811335758afa3de852cf7a4b48"
    )
    fixture = ROOT / "tests/fixtures/assertion161/captured160-cases.json"
    assert (
        hashlib.sha256(fixture.read_bytes()).hexdigest()
        == "55379cd061120a82c537af32849edd975fbc8b5b18668b263ca847cac8539b9f"
    )
    spec = importlib.util.spec_from_file_location("phase200_assertion_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decoded_objects(messages):
    value = json.loads(messages[-1]["content"])
    if "ASSERTION_PROOF_ENCODING" in value:
        value = codec.decode(value)
    if "CHECKER_INPUT_ENCODING" in value:
        value = legacy.decode(value)
    if "SOURCE_FRAGMENT_TABLE" in value:
        value["SOURCE_FRAGMENTS"] = rows(value.pop("SOURCE_FRAGMENT_TABLE"))
    return value


@pytest.mark.parametrize("defect", [None, "conditions_preserved"])
def test_native_service_retains_full_output_schema_4096_and_negative_gate(monkeypatch, defect):
    from generation import GenerationService, RequestBudget

    helper = load_assertion_helpers()
    monkeypatch.setattr(helper, "decode_packet", decoded_objects)
    results = []
    for selected_policy in (legacy.VERSION, POLICY):
        request = helper.mapped_request(checker_payload_policy=selected_policy)
        request.checker_config = replace(request.config, max_tokens=4096)
        draft = helper.private_draft(extra=True, short=True)
        first, last = draft["answer_text"]
        draft["answer_text"] = [deepcopy(first) for _ in range(8)] + [last]
        for number, assertion in enumerate(draft["answer_text"], 1):
            assertion["assertion_id"] = f"A{number:03d}"
        adapter = helper.ScriptedTransport(
            [
                draft,
                lambda messages: helper.authored_full_checker(messages, defect),
            ]
        )
        output = GenerationService(adapter, checker_adapter=adapter).generate(
            request, RequestBudget(max_calls=2)
        )
        assert len(adapter.calls) == output.budget["consumed_calls"] == 2, (
            selected_policy,
            output.error,
            output.token_budget,
        )
        assert output.budget["format_repairs"] == output.budget["transient_retries"] == 0
        results.append((output, adapter))
    (old, old_adapter), (new, new_adapter) = results
    old_messages, old_kwargs = old_adapter.calls[1]
    new_messages, new_kwargs = new_adapter.calls[1]
    assert new_kwargs["response_schema"] == old_kwargs["response_schema"]
    assert new_kwargs["response_schema_name"] == old_kwargs["response_schema_name"]
    for output in (old, new):
        check_stages = [
            row
            for row in output.token_budget["stage_token_budgets"]
            if row["stage"] == "joint_check"
        ]
        assert len(check_stages) == 1 and check_stages[0]["output_reserved_tokens"] == 4096
    assert "attempt_evaluation_ok" in new_kwargs["response_schema"]["required"]
    assert decoded_objects(new_messages) == decoded_objects(old_messages)
    assert "ASSERTION_PROOF_ENCODING" in json.loads(new_messages[-1]["content"])
    assert new.response == old.response
    if defect is None:
        assert new.succeeded and old.succeeded, (new.error, old.error)
        assert (
            new.checks[0]["actual_citation_bindings"] == old.checks[0]["actual_citation_bindings"]
        )
    else:
        assert not new.succeeded and not old.succeeded
        assert new.error["code"] == old.error["code"]
        assert new.response is None and new.delivered_projection == {}
        assert all(not row["published"] for row in new.drafts)


def admission_config200(kind):
    from generation import ModelConfig

    if kind == "absent":
        return None
    if kind == "openai":
        return ModelConfig(provider="openai", model="gpt-6-luna", temperature=None)
    if kind == "deepseek":
        return ModelConfig(
            provider="openai_compatible",
            model="deepseek-flash",
            base_url="https://api.deepseek.com/v1",
            temperature=0.0,
        )
    return ModelConfig(
        provider="openai_compatible",
        model="google/gemini-3.5-flash-lite",
        base_url="https://openrouter.ai/api/v1",
        temperature=None,
        openrouter_route_profile=(
            "unknown_phase200_route"
            if kind == "invalid"
            else "gemini35_google_vertex_compact_checker_v3"
        ),
    )


@pytest.mark.parametrize(
    "kind,fields,expected",
    [
        ("compact", {"assertion_source_policy": "assertion_source_v1"}, legacy.VERSION),
        ("deepseek", {"assertion_source_policy": "assertion_source_v1"}, POLICY),
        ("openai", {"assertion_source_policy": "assertion_source_v1"}, POLICY),
        ("absent", {"assertion_source_policy": "assertion_source_v1"}, legacy.VERSION),
        ("openai", {}, legacy.VERSION),
        ("compact", {"assertion_source_policy": "assertion_source_v2"}, legacy.VERSION),
    ],
)
def test_admission200_requires_actual_noncompact_checker_configuration(kind, fields, expected):
    from generation.providers import checker_transport_enabled

    config = admission_config200(kind)
    if kind == "compact":
        assert checker_transport_enabled(config) is True
    assert codec.submission_policy(POLICY, fields, config) == expected


@pytest.mark.parametrize(
    "old_policy", [legacy.VERSION, legacy.LEGACY, "lossless_full_checker_tables_v2", None]
)
def test_admission200_old_values_return_unchanged_without_resolving_invalid_route(old_policy):
    from generation.providers import checker_transport_enabled

    invalid = admission_config200("invalid")
    with pytest.raises(ValueError):
        checker_transport_enabled(invalid)
    assert (
        codec.submission_policy(
            old_policy, {"assertion_source_policy": "assertion_source_v1"}, invalid
        )
        == old_policy
    )


@pytest.mark.parametrize(
    "checker_kind,selected_kind,expected",
    [
        ("compact", "openai", legacy.VERSION),
        ("absent", "compact", legacy.VERSION),
        ("deepseek", "compact", POLICY),
        ("absent", "openai", POLICY),
    ],
    ids=["verified_compact", "fast_selected_compact", "verified_supported", "fast_supported"],
)
def test_admission200_actual_answer_request_expression_uses_effective_checker(
    checker_kind, selected_kind, expected
):
    import ast
    from types import SimpleNamespace

    path = ROOT / "backend/app/modules/answering/service.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values = []
    for call in ast.walk(tree):
        if (
            not isinstance(call, ast.Call)
            or not isinstance(call.func, ast.Name)
            or call.func.id != "AnswerRequest"
        ):
            continue
        for keyword in call.keywords:
            if keyword.arg != "command" or not isinstance(keyword.value, ast.Dict):
                continue
            for key, value in zip(keyword.value.keys, keyword.value.values, strict=True):
                if isinstance(key, ast.Constant) and key.value == "checker_payload_policy":
                    values.append(value)
    assert len(values) == 1, "Extract the one actual new-request producer expression"
    expression = ast.Expression(body=values[0])
    ast.fix_missing_locations(expression)
    namespace = {
        "__builtins__": {},
        "assertion_checker_submission_policy": codec.submission_policy,
        "settings": SimpleNamespace(chat_checker_payload_policy=POLICY),
        "assertion_fields": {"assertion_source_policy": "assertion_source_v1"},
        "checker_config": admission_config200(checker_kind),
        "selected_config": admission_config200(selected_kind),
    }
    assert eval(compile(expression, str(path), "eval"), namespace) == expected


@pytest.mark.parametrize(
    "defect",
    [
        "compact_route",
        "protected_source_relation",
        "hint",
        "practice",
        "pending",
        "general",
        "reading",
        "E0",
        "reselection",
    ],
)
def test_admission200_forged_incompatible_v3_is_rejected_before_scripted_generation(defect):
    from generation import GenerationService, RequestBudget

    helper = load_assertion_helpers()
    request = helper.mapped_request(checker_payload_policy=POLICY)
    if defect == "compact_route":
        request.checker_config = admission_config200("compact")
    elif defect == "protected_source_relation":
        request.source_relation_policy = "source_relation_contract_v2"
    elif defect == "hint":
        request.teaching_context = {
            **request.teaching_context,
            "teaching_mode": "hint",
            "help_level": 1,
        }
    elif defect == "practice":
        request.teaching_context = {
            **request.teaching_context,
            "practice_context": {"question_id": "authored-practice"},
        }
    elif defect == "pending":
        request.teaching_context = {
            **request.teaching_context,
            "pending_tutor_question_id": "authored-pending",
        }
    elif defect == "general":
        request.answer_mode = "general"
    elif defect == "reading":
        request.reading_context = {"chapter_id": "authored-reading"}
    elif defect == "E0":
        request.condition = "E0"
    else:
        request.assertion_reselection = {"version": "assertion_source_reselection_v1"}
    with pytest.raises(ValueError):
        codec.validate_request(request)
    adapter = helper.ScriptedTransport([])
    output = GenerationService(adapter, checker_adapter=adapter).generate(
        request, RequestBudget(max_calls=2)
    )
    assert adapter.calls == [] and output.budget["consumed_calls"] == 0
    assert output.error["code"] == "CHECKER_PAYLOAD_POLICY_INCOMPATIBLE"
    assert output.response is None and output.delivered_projection == {}
