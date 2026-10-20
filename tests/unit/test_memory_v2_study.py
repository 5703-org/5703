"""Evaluator schedule, matched-factor and value-level state checks without models."""

from dataclasses import asdict

from evaluation.enhancement.protocol import digest
from evaluation.memory_v2 import memory_catalogue
from evaluation.memory_v2.memory_study import state_checks
from evaluation.memory_v2.protocol import schedule
from evaluation.memory_v2.runner import make_request
from generation.types import ModelConfig
from evaluation.enhancement.protocol import freeze
from evaluation.memory_v2 import memory_study


def tasks():
    return [
        {
            "id": f"TEST-Q{i:02d}",
            "family": f"authored-family-{i}",
            "task_type": "process",
            "question": "Explain the role of this authored test mechanism.",
            "critical_answer": "Private test expectation must stay out of the generation input.",
            "turns": ["One hint", "Another hint", "One step"],
            "teaching_task": i <= 12,
            "source_requirement": {"book": f"Authored book {(i - 1) // 6}"},
        }
        for i in range(1, 25)
    ]


def trajectories():
    return [
        {
            "id": f"TEST-M{i:02d}",
            "family": f"synthetic-history-{i}",
            "statements": ["I prefer analogies.", "Actually, avoid analogies."],
            "probes": [
                {
                    "question_id": "TEST-Q08",
                    "expected": {
                        "selected_fields": ["analogies"],
                        "exact_values": {
                            "analogies": "I prefer analogies."
                            if turn == 1
                            else "Actually, avoid analogies."
                        },
                    },
                }
                for turn in range(1, 4)
            ],
        }
        for i in range(1, 13)
    ]


def test_registered_memory_inventory_keeps_all_rows_and_evaluator_values():
    histories = trajectories()
    rows = [r for r in schedule(tasks(), histories) if r["study"] == "M"]
    assert len(rows) == len({r["id"] for r in rows}) == 180
    assert all(
        p["question_id"] in {t["id"] for t in tasks()} for h in histories for p in h["probes"]
    )
    assert (
        histories[0]["probes"][1]["expected"]["exact_values"]["analogies"]
        != histories[0]["probes"][0]["expected"]["exact_values"]["analogies"]
    )


def test_old_positive_preference_fails_even_when_its_field_is_present():
    expected = trajectories()[0]["probes"][1]["expected"]
    state = {
        "memory_context": {
            "entries": [
                {
                    "id": "x",
                    "version": 1,
                    "source_message_id": "s",
                    "field_key": "analogies",
                    "content": "I prefer analogies.",
                }
            ]
        }
    }
    checks = state_checks(state, expected)
    assert next(c for c in checks if c["name"] == "selected:analogies")["passed"]
    assert not next(c for c in checks if c["name"] == "exact_value:analogies")["passed"]


def test_memory_answer_request_keeps_common_complete_checker_and_no_evaluator_labels():
    task = tasks()[7]
    checkpoint = {
        "model_config": ModelConfig().to_dict(),
        "checker_config": ModelConfig(max_tokens=4096).to_dict(),
    }
    row = {"id": "W8V2-M01-M4-1", "study": "M", "arm": "M4", "turn": 1}
    request = make_request(row, task, {"evidence": [], "source_map": {}}, checkpoint, [], [])
    serialized = str(asdict(request))
    assert task["critical_answer"] not in serialized and "expected_operations" not in serialized
    assert request.reliability_policy == "evidence_reliability_v2"
    assert request.teaching_context["teaching_mode"] == "direct"
    assert digest(asdict(request))


def test_resume_preserves_uncertain_answer_and_replays_prior_authentication_stop(
    tmp_path, monkeypatch
):
    source, output = tmp_path / "source", tmp_path / "output"
    task = tasks()[7]
    trajectory = trajectories()[0]
    rows = [
        {
            "id": f"{trajectory['id']}-M4-{i}",
            "case_id": trajectory["id"],
            "family": trajectory["family"],
            "study": "M",
            "arm": "M4",
            "turn": i,
            "status": "planned",
        }
        for i in range(1, 4)
    ]
    material = {"evidence": [], "source_map": {}}
    manifest = {
        "checkpoint": {
            "model_config": ModelConfig().to_dict(),
            "checker_config": ModelConfig().to_dict(),
            "retrieval_hashes": {"TEST-Q08": digest(material)},
        },
        "schedule": rows,
    }
    freeze(source / "retrieval" / "TEST-Q08.json", material)
    freeze(
        output / "states" / f"{trajectory['id']}.json",
        {"status": "complete", "provider_outcomes": [], "probes": []},
    )
    freeze(output / "reservations" / f"{rows[0]['id']}.json", {"interrupted": True})
    freeze(
        output / "results" / f"{rows[1]['id']}.json",
        {
            **rows[1],
            "status": "failed",
            "outcome": {
                "error": {"code": "PROVIDER_HTTP_ERROR", "details": {"http_status": 401}},
                "provider": "fixture",
            },
        },
    )
    monkeypatch.setattr(
        memory_study, "read_inputs", lambda _: (manifest, [trajectory], {task["id"]: task})
    )
    monkeypatch.setattr(memory_study, "resolve_frozen_credentials", lambda _: None)
    monkeypatch.setattr(memory_study, "assert_sources", lambda _: None)

    def forbidden(*args, **kwargs):
        raise AssertionError("No new transport or generation is permitted")

    monkeypatch.setattr(memory_study, "GenerationService", forbidden)
    report = memory_study.run(source, output, allow_live=True)
    first = memory_study.load(output / "results" / f"{rows[0]['id']}.json")
    last = memory_study.load(output / "results" / f"{rows[2]['id']}.json")
    assert (
        first["status"] == "failed" and first["reason"] == "uncertain_external_completion_preserved"
    )
    assert (
        last["status"] == "not_run"
        and report["halted"] == "provider_authentication_or_billing_denial"
    )


def test_typed_extraction_rejects_wrong_frozen_catalogue_before_resolving_key(
    tmp_path, monkeypatch
):
    from evaluation.memory_v2.memory_catalogue import VERSION

    source = tmp_path / "source"
    freeze(
        source / "study.json",
        {"version": VERSION, "trajectories_sha256": "wrong", "tasks_sha256": digest(tasks())},
    )
    freeze(source / "private-trajectories.json", {"trajectories": trajectories()})
    freeze(source / "private-tasks.json", {"tasks": tasks()})
    import pytest

    with pytest.raises(ValueError, match="catalogue differs"):
        memory_study.typed_candidates(source, tmp_path / "output", allow_live=True)


def test_private_catalogue_requires_explicit_restored_input(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setattr(memory_catalogue, "PRIVATE_CATALOGUE", tmp_path / "absent.json")
    with pytest.raises(FileNotFoundError, match="approved research bundle"):
        memory_catalogue.trajectories()


def test_legacy_free_form_attribute_is_not_scored_as_a_missing_typed_field():
    checks = state_checks(
        {
            "memory_context": {
                "version": "explicit_learning_memory_v1",
                "entries": [
                    {
                        "id": "entry",
                        "version": 1,
                        "source_message_id": "source",
                        "attribute": "old-hash",
                        "content": "I prefer analogies.",
                    }
                ],
            }
        },
        {"selected_fields": ["analogies"]},
    )
    assert checks[0]["status"] == "not_applicable" and checks[0]["passed"] is None
    assert checks[1]["passed"] is True


def test_memory_expected_arrays_are_bound_before_any_extraction_call(tmp_path, monkeypatch):
    import pytest

    histories = trajectories()
    extraction = [{"id": f"fixture-E{i}"} for i in range(24)]
    gates = [{"id": f"fixture-G{i}"} for i in range(12)]
    freeze(
        tmp_path / "study.json",
        {
            "trajectories_sha256": digest(histories),
            "tasks_sha256": digest(tasks()),
            "checkpoint": {
                "memory_extraction_sha256": digest(extraction),
                "memory_gating_sha256": digest(gates),
            },
        },
    )
    extraction[0]["tampered_label"] = True
    freeze(
        tmp_path / "private-trajectories.json",
        {"trajectories": histories, "extraction_cases": extraction, "gating_pairs": gates},
    )
    freeze(tmp_path / "private-tasks.json", {"tasks": tasks()})
    with pytest.raises(ValueError, match="extraction_cases differ"):
        memory_study.read_inputs(tmp_path)


def test_extraction_errors_and_missing_inputs_remain_in_the_planned_denominator():
    cases = [
        {
            "id": f"test-{i}",
            "text": "I prefer analogies.",
            "expected_operations": [
                {"operation": "ADD", "field_key": "analogies", "scope": "global"}
            ],
        }
        for i in range(3)
    ]
    result = memory_study.extraction_metrics(
        [
            {
                "id": "test-0",
                "error": None,
                "operations": [
                    {
                        "operation": "ADD",
                        "field_key": "analogies",
                        "scope": "global",
                        "source_quote": "I prefer analogies.",
                        "content": "I prefer analogies.",
                    }
                ],
            },
            {"id": "test-1", "error": {"code": "MEMORY_EXTRACTION_INVALID"}, "operations": []},
        ],
        cases,
    )
    assert (result["planned"], result["recorded"], result["exact_operations"]) == (3, 2, 1)
    assert [r["false_negative"] for r in result["records"]] == [0, 1, 1]
    assert result["records"][0]["source_supported"] is True
    assert result["records"][2]["valid"] is False
