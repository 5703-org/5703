"""Primitive decisions and full offline execution, never model-quality scores."""

from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from generation.qualification_v1 import ReliableQualificationWire, decision_derivative
from generation.requirement_axes_v1 import (
    DERIVED_FIELDS,
    RequirementJudgmentV2,
    derive_requirement_summary,
    assess_qualification_requirements,
)
from scripts.dev import checker_fixture_runner as runner
from test_context_qualification_v1 import request, verdict
from test_enhancement_generation import answer
from test_source_relation_units_v2 import unit_checker


def primitive(**changes):
    row = dict(
        requirement_id="r1",
        relevance="related",
        sufficiency="sufficient",
        evidence=[dict(evidence_id="ev_001", fragment_id="F001", quote="Direction is left.")],
        conditions_preserved=True,
        response_coverage="covered",
        missing_information="",
        response_missing_information="",
        reason="Authored direction and delivery judgment.",
    )
    row.update(changes)
    return row


def summary(row, *, limits=False, mode="direct"):
    return derive_requirement_summary([row], limitations_explicit=limits, teaching_mode=mode)


def test_wire_has_no_independent_model_summary_fields_and_requires_separate_axes():
    schema = ReliableQualificationWire.model_json_schema()
    assert not set(DERIVED_FIELDS) & set(schema["properties"])
    assert "response_missing_information" in schema["$defs"]["RequirementJudgmentV2"]["required"]


@pytest.mark.parametrize("source", ["partial", "absent", "conflicting"])
@pytest.mark.parametrize("named", [True, False])
def test_negative_source_status_requires_named_source_point_in_both_directions(source, named):
    row = primitive(
        sufficiency=source,
        missing_information="Requested rate unavailable." if named else "",
        response_coverage="limitation",
    )
    result = summary(row, limits=True)
    assert (result["state"] == "derived") is named
    assert row["sufficiency"] == source
    if named:
        assert result["missing_facets"] == [row["missing_information"]]
        assert result["coverage"] != "full"
    else:
        assert result["coverage"] == "unknown" and result["complete_answer"] is None


@pytest.mark.parametrize("source", ["sufficient", "not_applicable"])
@pytest.mark.parametrize("gap", ["", "Purported missing direction."])
def test_complete_source_status_and_empty_source_point_are_equivalent(source, gap):
    result = summary(primitive(sufficiency=source, missing_information=gap))
    assert (result["state"] == "derived") is (gap == "")
    if not gap:
        assert result["coverage"] == "full" and result["complete_answer"] is True


@pytest.mark.parametrize("delivery", ["partial", "not_addressed"])
@pytest.mark.parametrize("omission", ["", "Requested direction is omitted."])
def test_incomplete_delivery_requires_its_own_named_omission(delivery, omission):
    row = primitive(response_coverage=delivery, response_missing_information=omission)
    result = summary(row)
    assert (result["state"] == "derived") is bool(omission)
    assert row["missing_information"] == ""  # Never turn an omission into a source gap.
    if omission:
        assert result["complete_answer"] is False and result["missing_facets"] == [omission]


@pytest.mark.parametrize("delivery,mode", [("covered", "direct"), ("deferred_for_hint", "hint")])
@pytest.mark.parametrize("omission", ["", "Invented omitted part."])
def test_complete_current_help_and_empty_omission_are_equivalent(delivery, mode, omission):
    result = summary(
        primitive(response_coverage=delivery, response_missing_information=omission), mode=mode
    )
    assert (result["complete_answer"] is True) is (omission == "")
    assert (result["state"] == "derived") is (omission == "")


@pytest.mark.parametrize("limits", [True, False])
def test_honest_partial_limitation_completes_only_with_explicit_limits(limits):
    result = summary(
        primitive(
            sufficiency="partial",
            missing_information="Requested rate unavailable.",
            response_coverage="limitation",
        ),
        limits=limits,
    )
    assert result["coverage"] == "supported_partial"
    assert result["complete_answer"] is limits


def test_limitation_without_any_named_gap_stays_unknown_and_empty_does_not_invent_point():
    result = summary(primitive(response_coverage="limitation"), limits=True)
    assert result["state"] == "invalid_unknown" and result["missing_facets"] == []


@pytest.mark.parametrize("axis", ["sufficiency", "response_coverage"])
def test_explicit_unknown_is_not_guessed_into_a_gap_or_positive_summary(axis):
    row = primitive(**{axis: "unknown"})
    before = deepcopy(row)
    result = summary(row)
    assert result["coverage"] == "unknown" and result["complete_answer"] is None
    assert result["missing_facets"] == [] and row == before


@pytest.mark.parametrize("field", ["missing_information", "response_missing_information"])
@pytest.mark.parametrize("bad", [None, " \t\n", False, [], {}])
def test_malformed_gap_values_are_not_coerced_or_filled(field, bad):
    row = primitive(**{field: bad})
    before = deepcopy(row)
    with pytest.raises(ValidationError):
        RequirementJudgmentV2.model_validate(row)
    assert row == before


@pytest.mark.parametrize("field", ["missing_information", "response_missing_information"])
def test_absent_gap_field_is_not_explicit_empty(field):
    row = primitive()
    row.pop(field)
    with pytest.raises(ValidationError):
        RequirementJudgmentV2.model_validate(row)


def test_empty_requirements_unknown_and_exact_named_facets_deduplicate_without_prose_inference():
    result = derive_requirement_summary([], limitations_explicit=False, teaching_mode="direct")
    assert result["state"] == "invalid_unknown"
    row = primitive(
        sufficiency="partial",
        missing_information="Rate.",
        response_coverage="partial",
        response_missing_information="Direction.",
    )
    result = derive_requirement_summary(
        [row, {**row, "requirement_id": "r2"}], limitations_explicit=False, teaching_mode="direct"
    )
    assert result["missing_facets"] == ["Rate.", "Direction."]


@pytest.mark.parametrize("conditions", [True, False])
def test_conditions_control_completion_without_inventing_missing_knowledge(conditions):
    result = summary(primitive(conditions_preserved=conditions))
    assert result["coverage"] == "full" and result["missing_facets"] == []
    assert result["complete_answer"] is conditions


@pytest.mark.parametrize("case", ["nothing_delivered", "no_sources", "direct_deferral"])
def test_empty_delivery_or_sources_and_illegal_direct_deferral_never_complete(case):
    row = primitive()
    if case == "nothing_delivered":
        row.update(response_coverage="not_addressed", response_missing_information="Direction.")
    elif case == "no_sources":
        row.update(
            sufficiency="absent",
            evidence=[],
            missing_information="Direction.",
            response_coverage="limitation",
        )
    else:
        row["response_coverage"] = "deferred_for_hint"
    result = summary(row, limits=True)
    assert result["complete_answer"] is False
    if case != "direct_deferral":
        assert result["coverage"] == "none"


@pytest.mark.parametrize(
    "field,value",
    [("coverage", "none"), ("missing_facets", ["Invented point."]), ("complete_answer", False)],
)
def test_server_summary_cannot_be_changed_in_either_direction(field, value):
    row = primitive()
    computed = summary(row)
    judgment = dict(
        requirements=[row],
        limitations_explicit=False,
        non_repetitive_next_action=True,
        **{name: computed[name] for name in DERIVED_FIELDS},
    )
    coverage = dict(requirements=[dict(id="r1")])
    fragment = dict(
        fragment_id="F001",
        evidence_id="ev_001",
        exact_text="Direction is left.",
        complete_block=True,
    )
    assert not assess_qualification_requirements(
        judgment, coverage, [fragment], answer_mode="textbook", teaching_mode="direct"
    )[0]
    judgment[field] = value
    issues = assess_qualification_requirements(
        judgment, coverage, [fragment], answer_mode="textbook", teaching_mode="direct"
    )[0]
    assert "SERVER_REQUIREMENT_SUMMARY_CHANGED" in {issue["code"] for issue in issues}


def fixture_plan(count=8):
    value = request()
    config = value.config.to_dict()
    config.update(
        provider="openai_compatible",
        model="deepseek-flash",
        base_url="https://api.deepseek.com/v1",
        structured_output_mode="json_object",
        max_tokens=4096,
        thinking_enabled=False,
    )
    labels = [
        dict(
            case="tiny",
            control=control,
            question=value.question,
            draft=answer(),
            expected_accept=control == "positive",
        )
        for control in ("negative", "positive")
    ]
    plan = dict(
        config=config,
        rows=[
            dict(
                id=f"unit_{index}",
                case="tiny",
                control="negative" if index < count // 2 else "positive",
                variant="B" if index % 2 == 0 else "A",
            )
            for index in range(count)
        ],
        labels=labels,
        source_bindings=dict(
            cases=dict(tiny=dict(evidence=value.evidence, original_mapping=value.source_map))
        ),
    )
    return runner.prepare(plan)


def full_reply(row, accept=True, *, unknown=False, bad_content=False, usage=True):
    messages = row["body"]["messages"]
    value = verdict(messages) if row["variant"] == "B" else unit_checker(messages)
    if row["variant"] == "B":
        for field in DERIVED_FIELDS:
            value.pop(field)
        for requirement in value["requirements"]:
            requirement["response_missing_information"] = ""
        for record in value["qualification_assessments"]:
            record.pop("citation_support_exists")
            for role in ("supporting_quotes", "limiting_quotes", "revision_supporting_quotes"):
                for quote in record[role]:
                    quote.pop("fragment_id")
        if unknown:
            value["requirements"][0]["sufficiency"] = "unknown"
    if not accept:
        value["body_ok"] = False
        for claim in value["claims"]:
            claim["status"] = "unsupported"
            for unit in claim["units"]:
                unit.update(
                    status="unsupported", relation_preserved=False, conditions_preserved=False
                )
    outer = dict(
        choices=[
            dict(
                finish_reason="stop",
                message=dict(content="{" if bad_content else json.dumps(value)),
            )
        ]
    )
    if usage:
        outer["usage"] = dict(prompt_tokens=100, completion_tokens=200, total_tokens=300)
    return runner.encoded(outer)


def test_eight_use_same_serializer_parser_score_receipt_terminal_path_and_keep_semantic_failures(
    tmp_path,
):
    plan = fixture_plan()
    accepts = [False, True, False, True, True, False, True, False]
    seen = []

    def transport(envelope, row):
        index = len(seen)
        seen.append(row["id"])
        assert runner.sha(envelope.data) == row["wire_sha256"]
        return runner.Response(full_reply(row, accepts[index]))

    final = runner.run(plan, transport=transport, output=tmp_path / "eight")
    assert final["status"] == "COMPLETED_ALL_UNITS" and len(seen) == 8
    assert [row["semantic_accept"] for row in final["results"]] == accepts
    assert sum(row["false_accept"] for row in final["results"]) == 2
    assert sum(row["false_reject"] for row in final["results"]) == 2
    for row in final["results"]:
        for suffix in (
            "-SEND_INTENT.json",
            "-raw-response.json",
            "-settlement.json",
            "-result.json",
        ):
            assert (tmp_path / "eight" / (row["id"] + suffix)).exists()
    assert final["real_requests"] == 0 and runner.Decimal(final["simulated_UNKNOWN_CNY"]) == 0


@pytest.mark.parametrize(
    "kind", ["unknown", "bad_content", "usage", "framing", "duplicate", "durable"]
)
def test_actual_failures_stop_with_seven_unrun_and_hold_release_only_after_durability(
    tmp_path, monkeypatch, kind
):
    plan = fixture_plan()
    original_save = runner.save

    def save(path, value):
        if kind == "durable" and path.name.endswith("-settlement.json"):
            raise RuntimeError("AUTHORED_SETTLEMENT_WRITE_FAILED")
        original_save(path, value)

    monkeypatch.setattr(runner, "save", save)

    def transport(envelope, row):
        raw = full_reply(
            row, unknown=kind == "unknown", bad_content=kind == "bad_content", usage=kind != "usage"
        )
        if kind == "duplicate":
            raw = b'{"choices":[],"choices":[]}'
        return runner.Response(
            raw, headers={"Content-Length": str(len(raw) + 1)} if kind == "framing" else None
        )

    output = tmp_path / kind
    final = runner.run(plan, transport=transport, output=output)
    assert final["status"] == "STOPPED_NO_RETRY"
    assert final["simulated_transport_attempts"] == 1
    assert sum(row["status"] == "NOT_RUN" for row in final["results"]) == 7
    assert final["results"][0]["correctness"] is None
    for row in final["results"][1:]:
        assert (output / (row["id"] + "-result.json")).exists()
        assert not (output / (row["id"] + "-SEND_INTENT.json")).exists()
    unknown = runner.Decimal(final["simulated_UNKNOWN_CNY"])
    assert (unknown == 0) is (kind in {"unknown", "bad_content"})


@pytest.mark.parametrize(
    "case",
    [
        "missing_config",
        "null_config",
        "empty_rows",
        "malformed_row",
        "missing_label",
        "wrong_wire",
        "wrong_hold",
        "low_cap",
        "paid",
    ],
)
def test_preflight_rejects_bad_inputs_before_claim_or_transport(tmp_path, case):
    plan = fixture_plan(2)
    if case == "missing_config":
        plan.pop("config")
    elif case == "null_config":
        plan["config"] = None
    elif case == "empty_rows":
        plan["rows"] = []
    elif case == "malformed_row":
        plan["rows"] = [{}]
    elif case == "missing_label":
        plan["labels"] = []
    elif case == "wrong_wire":
        plan["rows"][0]["wire_sha256"] = "0" * 64
    elif case == "wrong_hold":
        plan["rows"][0]["hold_CNY"] = "0"
    elif case == "paid":
        plan["offline_only"] = False
    output = tmp_path / case

    def forbidden(*args):
        pytest.fail("Preflight attempted transport")

    with pytest.raises(RuntimeError):
        runner.run(
            plan, transport=forbidden, output=output, cap="0.0001" if case == "low_cap" else "1.00"
        )
    assert not output.exists()


def test_new_model_returning_derived_fields_or_mixed_versions_is_invalid_not_repaired():
    plan = fixture_plan(2)
    raw = json.loads(json.loads(full_reply(plan["rows"][0]))["choices"][0]["message"]["content"])
    before = deepcopy(raw)
    raw["coverage"] = "full"
    with pytest.raises(ValueError, match="DERIVED_SUMMARY_FIELDS_RETURNED_BY_MODEL"):
        decision_derivative(raw)
    assert raw == {**before, "coverage": "full"}
    raw.pop("coverage")
    raw["requirements"].append({**raw["requirements"][0], "requirement_id": "r2"})
    raw["requirements"][-1].pop("response_missing_information")
    with pytest.raises(ValueError, match="REQUIREMENT_DECISION_VERSION_MIXED"):
        decision_derivative(raw)


def test_scoped_template_has_no_obsolete_request_for_model_summary_values():
    path = Path(__file__).parents[2] / "generation/prompts/qualification_joint_v2.txt"
    text = path.read_text()
    assert "Report full/supported_partial/none" not in text
    assert '"missing_facets"' not in text and '"complete_answer"' not in text


@pytest.mark.parametrize("value", [None, "false", 0, "absent"])
def test_required_limit_judgment_rejects_missing_and_wrong_types(value):
    raw = dict(requirements=[primitive()])
    if value != "absent":
        raw["limitations_explicit"] = value
    with pytest.raises(ValueError, match="LIMITATIONS_EXPLICIT_BOOLEAN_REQUIRED"):
        decision_derivative(raw)


@pytest.mark.parametrize(
    "field,value", [("coverage", "full"), ("missing_facets", []), ("complete_answer", True)]
)
def test_negative_summary_cannot_be_promoted_by_server_tampering(field, value):
    row = primitive(response_coverage="not_addressed", response_missing_information="Direction.")
    computed = summary(row)
    judgment = dict(
        requirements=[row],
        limitations_explicit=False,
        non_repetitive_next_action=True,
        **{name: computed[name] for name in DERIVED_FIELDS},
    )
    judgment[field] = value
    issues = assess_qualification_requirements(
        judgment,
        dict(requirements=[dict(id="r1")]),
        [],
        answer_mode="textbook",
        teaching_mode="direct",
    )[0]
    assert "SERVER_REQUIREMENT_SUMMARY_CHANGED" in {issue["code"] for issue in issues}


@pytest.mark.parametrize(
    "kind",
    ["source", "evidence", "pages", "mapping", "question", "draft", "id", "duplicate", "profile"],
)
def test_deep_preflight_blocks_before_claim(tmp_path, kind):
    plan = fixture_plan(2)
    source = plan["source_bindings"]["cases"]["tiny"]
    if kind == "source":
        plan["source_bindings"]["cases"]["tiny"] = None
    elif kind == "evidence":
        source["evidence"] = [{}]
    elif kind == "pages":
        source["evidence"][0]["pages"] = [True]
    elif kind == "mapping":
        source["original_mapping"] = None
    elif kind == "question":
        plan["labels"][0]["question"] = None
    elif kind == "draft":
        plan["labels"][0]["draft"] = []
    elif kind == "id":
        plan["rows"][0]["id"] = "../escaped"
    elif kind == "duplicate":
        plan["rows"][1]["id"] = plan["rows"][0]["id"].upper()
    else:
        plan["config"]["max_tokens"] = 3000
    output = tmp_path / kind
    with pytest.raises(RuntimeError):
        runner.run(plan, transport=lambda *args: pytest.fail("Transport forbidden"), output=output)
    assert not output.exists()


def test_request_construction_failure_after_claim_has_all_receipts_and_terminal(
    tmp_path, monkeypatch
):
    plan = fixture_plan()

    def fail(*args):
        raise RuntimeError("REQUEST_CONSTRUCTION_FAILED")

    monkeypatch.setattr(runner, "make_request", fail)
    output = tmp_path / "construction"
    final = runner.run(
        plan, transport=lambda *args: pytest.fail("Transport forbidden"), output=output
    )
    assert final["status"] == "STOPPED_NO_RETRY" and final["simulated_transport_attempts"] == 0
    assert sum(row["status"] == "NOT_RUN" for row in final["results"]) == 7
    assert (output / "terminal.json").exists()
    assert len(list(output.glob("*-result.json"))) == 8


@pytest.mark.parametrize(
    "resolver", ["getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"]
)
def test_all_dns_entrypoints_are_fenced(resolver):
    with runner.network_fence(), pytest.raises(RuntimeError, match="NETWORK_AND_DNS_FORBIDDEN"):
        getattr(runner.socket, resolver)("localhost")


def test_nested_escaped_dummy_echo_withheld_before_persistence(tmp_path):
    plan = fixture_plan(2)
    escaped = "".join("\\u%04x" % ord(char) for char in runner.DUMMY_KEY)
    raw = runner.encoded(dict(content=json.dumps(dict(nested='"' + escaped + '"'))))
    final = runner.run(plan, transport=lambda *args: runner.Response(raw), output=tmp_path / "echo")
    assert final["results"][0]["reason"] == "KEY_ECHO_WITHHELD"
    assert not list((tmp_path / "echo").glob("*-raw-response.json"))
    assert runner.Decimal(final["simulated_UNKNOWN_CNY"]) > 0


@pytest.mark.parametrize("kind", ["bare_unicode", "double_escaped_unicode", "decode_limit"])
def test_escaped_bare_text_and_excessive_decoding_are_withheld(kind):
    item = "".join("\\u%04x" % ord(char) for char in runner.DUMMY_KEY)
    if kind == "double_escaped_unicode":
        item = item.replace("\\", "\\\\")
    if kind == "decode_limit":
        item = "ordinary deeply nested text"
        for _ in range(12):
            item = json.dumps(item)
    with pytest.raises(RuntimeError, match="KEY_ECHO_WITHHELD|PRIVACY_DECODE_LIMIT_WITHHELD"):
        runner.strict_outer(runner.encoded(dict(content=item)))


@pytest.mark.parametrize("slashes", [3, 4, 1024])
def test_bare_unicode_backslash_layers_reach_fixed_point_or_fail_closed(slashes):
    item = "".join("\\" * slashes + "u%04x" % ord(char) for char in runner.DUMMY_KEY)
    with pytest.raises(RuntimeError, match="KEY_ECHO_WITHHELD|PRIVACY_DECODE_LIMIT_WITHHELD"):
        runner.strict_outer(runner.encoded(dict(content=item)))


def test_explicit_reviewed_boundary_uses_same_parser_scores_and_real_receipt_names(tmp_path):
    from contextlib import nullcontext

    class Boundary:
        secret = runner.DUMMY_KEY

        def preflight(self, plan, cap):
            assert cap == "1.00" and plan["offline_only"] is False

        def scope(self):
            return nullcontext()

        def authorize(self):
            pass

    plan = fixture_plan(2)
    plan["offline_only"] = False
    final = runner.run(
        plan,
        transport=lambda envelope, row: runner.Response(full_reply(row)),
        output=tmp_path / "reviewed-boundary",
        live_boundary=Boundary(),
    )
    assert final["status"] == "COMPLETED_ALL_UNITS"
    assert final["real_requests"] == 2 and final["UNKNOWN_protection_CNY"] == "0.000000"
    assert all(row["technical_valid"] for row in final["results"])
    assert all("API_elapsed_ms" in row["receipt"] for row in final["results"])
    receipt = json.loads((tmp_path / "reviewed-boundary/unit_0-settlement.json").read_bytes())
    assert receipt["offline_only"] is False and "known_upper_CNY" in receipt
    assert receipt["rates_are_saved_test_inputs"] is False
