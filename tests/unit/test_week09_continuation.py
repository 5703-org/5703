"""Freeze, privacy, denominator and source-lineage regression for the expanded study."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from evaluation.week09_continuation.blinding import export, import_human_ratings
from evaluation.week09_continuation.attacks import AttackLimits, run_adaptive_attack
from evaluation.week09_continuation.calibration import make_packets
from evaluation.week09_continuation.executor import execute
from evaluation.week09_continuation.family_backend import (
    InteractivePilotBackend,
    MemorySelectorPilotBackend,
    PracticeProposalPilotBackend,
    VisualStructurePilotBackend,
)
from evaluation.week09_continuation.http_backend import normalize_answer
from evaluation.week09_continuation.judge import SemanticRating, judge_packet
from evaluation.week09_continuation.outcomes import summarize, write_terminal
from evaluation.week09_continuation.pilot import calibration_pass
from evaluation.week09_continuation.protocol import (
    OFFICIAL_BOOKS,
    canonical,
    digest_bytes,
    freeze,
    load_frozen,
    validate_catalogue,
    verify_prepared_source_coverage,
)
from evaluation.week09_continuation.source_catalogue import build_development_anchor_catalogue
from evaluation.week09_continuation.simulator import learner_messages, calibration_summary
from evaluation.week09_continuation.simulator_pilot import run_one_turn_calibration
from evaluation.week09_continuation.statistics import (
    clustered_contrast,
    holm_adjust,
    teaching_contrasts,
)
from evaluation.week09_continuation.teaching_backend import normalize_teaching_outcome
from generation.types import GenerationOutcome, ProviderResult


ROOT = Path(__file__).resolve().parents[2]
REAL_RETRIEVAL = ROOT / "evidence/openstax/v5/retrieval-verification.json"


def anchor(text="Verification-only fixture"):
    return {
        "source_kind": "official_openstax",
        "source_title": "Biology 2e",
        "source_url": "https://assets.openstax.org/oscms-prodcms/media/documents/Biology-2e_-_WEB.pdf",
        "original_sha256": OFFICIAL_BOOKS["Biology 2e"],
        "release_id": "release-1",
        "chunk_id": "fixture-chunk",
        "text_hash": digest_bytes(text.encode()),
        "text": text,
        "pages": [1],
    }


def case(*, identity="one", family="textbook_qa", split="development", group="concept"):
    return {
        "id": identity,
        "family": family,
        "split": split,
        "concept_group": group,
        "task": {"question": "What is the observed concept?"},
        "source_anchors": [anchor()],
        "required_points": [],
        "unsupported_conclusions": [],
        "label_provenance": "unlabelled",
        "private_labels": None,
    }


def candidate(*, integrated=False):
    return {
        "candidate_source_sha256": "a" * 64,
        "migration_head": "head-fixture",
        "corpus_release_id": "release-1",
        "corpus_manifest_sha256": "b" * 64,
        "model_roles": {"generation": "fixture-provider-version"},
        "budgets": {"max_calls": 4, "max_active_seconds": 180},
        "policy_versions": {"answer": "fixture"},
        "software_gate_sha256": "c" * 64,
        "quality_thresholds_sha256": "d" * 64,
        "tariff": {
            "currency": "USD",
            "input_per_million": 1.0,
            "output_per_million": 2.0,
            "cache_hit_input_per_million": 0.2,
        },
        "integration_status": "verified_and_frozen" if integrated else "in_development",
    }


def freeze_fixture(tmp_path, cases=None):
    catalogue_path, candidate_path = tmp_path / "cases.json", tmp_path / "candidate.json"
    catalogue_path.write_bytes(
        canonical(
            {
                "schema": "week09_continuation_v1_catalogue",
                "cases": cases or [case()],
            }
        )
    )
    candidate_path.write_bytes(canonical(candidate()))
    folder = tmp_path / "study"
    receipt = freeze(catalogue_path, candidate_path, folder, split="development")
    return folder, receipt


def test_real_old_retrieval_import_is_development_only_and_source_hashed(tmp_path):
    output = tmp_path / "real-dev.json"
    receipt = build_development_anchor_catalogue(REAL_RETRIEVAL, output)
    rows = json.loads(output.read_text(encoding="utf-8"))["cases"]
    assert receipt["cases"] == 15
    assert {row["split"] for row in rows} == {"development"}
    assert {row["label_provenance"] for row in rows} == {"unlabelled"}
    assert all(row["inspected_output"] for row in rows)
    assert all(
        digest_bytes(a["text"].encode()) == a["text_hash"]
        for row in rows
        for a in row["source_anchors"]
    )


def test_catalogue_blocks_split_leakage_fake_book_and_unchecked_teaching_arms():
    other = case(identity="two", split="reserved")
    with pytest.raises(ValueError, match="crosses splits"):
        validate_catalogue({"schema": "week09_continuation_v1_catalogue", "cases": [case(), other]})
    fake = case()
    fake["source_anchors"][0]["original_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="Book identity"):
        validate_catalogue({"schema": "week09_continuation_v1_catalogue", "cases": [fake]})
    tutor = case(family="joint_tutoring")
    tutor["arms"] = ["A", "D"]
    with pytest.raises(ValueError, match="all four"):
        validate_catalogue({"schema": "week09_continuation_v1_catalogue", "cases": [tutor]})
    private = case()
    private["task"]["answer_key"] = "hidden"
    with pytest.raises(ValueError, match="Private answer"):
        validate_catalogue({"schema": "week09_continuation_v1_catalogue", "cases": [private]})


def test_formal_freeze_requires_candidate_database_and_pilot_decision(tmp_path):
    cases_path, candidate_path = tmp_path / "cases.json", tmp_path / "candidate.json"
    cases_path.write_bytes(
        canonical(
            {
                "schema": "week09_continuation_v1_catalogue",
                "cases": [case(split="pilot")],
            }
        )
    )
    candidate_path.write_bytes(canonical(candidate()))
    with pytest.raises(ValueError, match="verified integrated"):
        freeze(cases_path, candidate_path, tmp_path / "pilot", split="pilot")
    candidate_path.write_bytes(canonical(candidate(integrated=True)))
    with pytest.raises(ValueError, match="requires its frozen CPU preparation SHA"):
        freeze(cases_path, candidate_path, tmp_path / "pilot", split="pilot")
    prepared = {
        "provider_calls": 0,
        "corpus_unchanged": True,
        "runtime_device": "cpu",
        "corpus": {"release_id": "release-1"},
        "cases": [
            {
                "id": "one",
                "retrieval": {
                    "evidence": [{"chunk_id": "fixture-chunk", "text_hash": anchor()["text_hash"]}]
                },
            }
        ],
    }
    prep_path = tmp_path / "qa-preparation.json"
    prep_path.write_bytes(canonical(prepared))
    version = candidate(integrated=True)
    version["qa_retrieval_sha256"] = digest_bytes(prep_path.read_bytes())
    candidate_path.write_bytes(canonical(version))
    with pytest.raises(ValueError, match="read-only database"):
        freeze(
            cases_path,
            candidate_path,
            tmp_path / "pilot",
            split="pilot",
            qa_preparation_path=prep_path,
        )
    with pytest.raises(ValueError, match="pilot-based decision"):
        freeze(cases_path, candidate_path, tmp_path / "reserved", split="reserved")


@pytest.mark.parametrize(
    ("family", "digest_field", "path_arg"),
    [
        ("textbook_qa", "qa_retrieval_sha256", "qa_preparation_path"),
        ("joint_tutoring", "teaching_retrieval_sha256", "teaching_preparation_path"),
    ],
)
def test_freeze_rejects_help_query_snapshot_after_official_anchor_is_filtered(
    tmp_path, family, digest_field, path_arg
):
    selected = case(family=family, split="pilot")
    selected["task"]["question"] = "Give me one first hint and leave the pathway to me."
    prepared = {
        "provider_calls": 0,
        "corpus_unchanged": True,
        "runtime_device": "cpu",
        "corpus": {"release_id": "release-1"},
        "cases": [
            {
                "id": selected["id"],
                "question": selected["task"]["question"],
                "retrieval": {
                    "evidence": [{"chunk_id": "another-official-chunk", "text_hash": "e" * 64}]
                },
            }
        ],
    }
    prep_path = tmp_path / "retrieval.json"
    prep_path.write_bytes(canonical(prepared))
    paths = {path_arg: prep_path}
    version = candidate(integrated=True)
    cases_path = tmp_path / "cases.json"
    candidate_path = tmp_path / "candidate.json"
    cases_path.write_bytes(
        canonical({"schema": "week09_continuation_v1_catalogue", "cases": [selected]})
    )
    candidate_path.write_bytes(canonical(version))
    with pytest.raises(ValueError, match="requires its frozen CPU preparation SHA"):
        freeze(
            cases_path,
            candidate_path,
            tmp_path / "study",
            split="pilot",
            database_url_env="UNSET_TEST_DB_URL",
            **paths,
        )
    version[digest_field] = digest_bytes(prep_path.read_bytes())
    with pytest.raises(ValueError, match="omitted its declared official source anchor"):
        verify_prepared_source_coverage([selected], version, **paths)
    candidate_path.write_bytes(canonical(version))
    with pytest.raises(ValueError, match="omitted its declared official source anchor"):
        freeze(
            cases_path,
            candidate_path,
            tmp_path / "study",
            split="pilot",
            database_url_env="UNSET_TEST_DB_URL",
            **paths,
        )
    assert not (tmp_path / "study").exists()
    prepared["cases"][0]["retrieval"]["evidence"] = [
        {
            "chunk_id": selected["source_anchors"][0]["chunk_id"],
            "text_hash": selected["source_anchors"][0]["text_hash"],
        }
    ]
    prep_path.write_bytes(canonical(prepared))
    version[digest_field] = digest_bytes(prep_path.read_bytes())
    assert verify_prepared_source_coverage([selected], version, **paths)[family] == {
        "cases": 1,
        "accepted_source_anchors": 1,
    }


def test_failed_terminal_stays_in_denominator_and_cost_unknown(tmp_path):
    folder, receipt = freeze_fixture(tmp_path)
    assert receipt["planned"] == 4
    assert "private_labels" not in json.dumps(load_frozen(folder)["cases"])
    write_terminal(
        folder,
        {
            "schedule_id": "one::candidate",
            "state": "model_failure",
            "elapsed_ms": 500,
            "provider_calls": 1,
            "usage": {"input_tokens": None, "output_tokens": None},
            "learner_visible_output": None,
        },
    )
    result = summarize(folder)
    arm = result["families"]["textbook_qa"]["candidate"]
    assert result["planned"] == 4 and result["terminal"] == 1 and result["unstarted"] == 3
    assert arm["terminal_states"] == {"model_failure": 1}
    assert arm["substantive_delivery"] == {"numerator": 0, "denominator": 1, "rate": 0.0}
    assert arm["cost_estimate"]["unknown_terminal_count"] == 1
    assert arm["latency_ms"]["failed_or_refused"]["p95"] == 500
    with pytest.raises(FileExistsError):
        write_terminal(
            folder,
            {
                "schedule_id": "one::candidate",
                "state": "model_failure",
                "elapsed_ms": 100,
                "provider_calls": 0,
            },
        )


def test_recorded_zero_provider_calls_have_zero_estimated_request_cost(tmp_path):
    folder, _ = freeze_fixture(tmp_path)
    write_terminal(
        folder,
        {
            "schedule_id": "one::candidate",
            "state": "clarification",
            "elapsed_ms": 2,
            "provider_calls": 0,
            "usage": {},
            "learner_visible_output": None,
        },
    )
    arm = summarize(folder)["families"]["textbook_qa"]["candidate"]
    assert arm["cost_estimate"]["known_subtotal"] == 0.0
    assert arm["cost_estimate"]["known_terminal_count"] == 1
    assert arm["cost_estimate"]["unknown_terminal_count"] == 0


def test_blind_packets_hide_arm_checker_and_allow_empty_human_form(tmp_path):
    folder, _ = freeze_fixture(tmp_path)
    write_terminal(
        folder,
        {
            "schedule_id": "one::candidate",
            "state": "answered",
            "elapsed_ms": 220,
            "provider_calls": 2,
            "usage": {"input_tokens": 100, "output_tokens": 50, "cache_hit_input_tokens": 20},
            "learner_visible_output": {"text": "A cited explanation"},
            "displayed_sources": [anchor()],
            "online_checker_decision": True,
        },
    )
    blind = tmp_path / "blind"
    receipt = export(folder, blind)
    assert receipt["packets"] == 1 and receipt["human_ratings"] == 0
    public = (blind / "packets.json").read_text(encoding="utf-8")
    assert '"arm"' not in public and "online_checker_decision" not in public
    imported = import_human_ratings(blind, blind / "ratings.csv", output=tmp_path / "human.json")
    assert imported["scored_rows"] == 0 and imported["unscored_rows"] == 1
    with (blind / "ratings.csv").open(encoding="utf-8-sig", newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 1
    calibration = make_packets(blind, tmp_path / "calibration", limit=1)
    assert calibration["probe_packets"] == 5
    assert (tmp_path / "calibration" / "packets.json").is_file()


def test_judge_calibration_handles_real_nested_answer_projection(tmp_path):
    folder, _ = freeze_fixture(tmp_path)
    write_terminal(
        folder,
        {
            "schedule_id": "one::candidate",
            "state": "answered",
            "elapsed_ms": 100,
            "provider_calls": 1,
            "learner_visible_output": {
                "response": {"answer_text": "A supported passage."},
                "citation_views": [],
            },
        },
    )
    blind = tmp_path / "blind-nested"
    export(folder, blind)
    probe = tmp_path / "calibration-nested"
    make_packets(blind, probe, limit=1)
    packets = json.loads((probe / "packets.json").read_text(encoding="utf-8"))["packets"]
    texts = [packet["learner_visible_output"]["response"]["answer_text"] for packet in packets]
    assert any("This concludes the response." in value for value in texts)
    assert any(value.startswith("Answer:\n") for value in texts)


def test_pilot_calibration_uses_frozen_thresholds_and_observed_pairs():
    criteria = {
        "min_evaluable_pairs": 2,
        "minimum_agreement": {
            "source_order": 0.8,
            "length_neutral": 0.8,
            "wording_frame": 0.8,
            "untrusted_instruction": 1.0,
        },
    }
    observed = {
        "schema": "week09_continuation_v1_judge_calibration",
        "comparisons": {
            key: {"evaluable_pairs": 2, "agreement_rate": 1.0}
            for key in criteria["minimum_agreement"]
        },
    }
    passed, checks = calibration_pass(observed, criteria)
    assert passed and all(row["passed"] for row in checks.values())
    observed["comparisons"]["untrusted_instruction"]["agreement_rate"] = 0.5
    assert calibration_pass(observed, criteria)[0] is False
    observed["comparisons"]["untrusted_instruction"]["evaluable_pairs"] = 1
    assert calibration_pass(observed, criteria)[0] is False


def test_executor_never_sends_private_labels_or_retries_interrupted_call(tmp_path):
    row = case()
    row["label_provenance"] = "program_derived"
    row["private_labels"] = {"context_sufficient": True}
    folder, _ = freeze_fixture(tmp_path, cases=[row])
    called = []

    def failed_backend(task, arm, identity):
        assert "private_labels" not in task and "context_sufficient" not in str(task)
        called.append(identity)
        raise RuntimeError("A failed API request")

    first = execute(folder, failed_backend, current_source_sha256="a" * 64, limit=1)
    assert first["new_terminal"] == 1 and len(called) == 1
    saved = summarize(folder)
    assert saved["terminal"] == 1
    assert (
        saved["families"]["textbook_qa"][called[0].split("::")[1]][
            "provider_calls_unknown_outcomes"
        ]
        == 1
    )
    second = execute(folder, failed_backend, current_source_sha256="a" * 64, limit=1)
    assert called[0] not in called[1:]
    assert second["previous_terminal"] == 1
    with pytest.raises(ValueError, match="differs"):
        execute(folder, failed_backend, current_source_sha256="b" * 64)


def test_candidate_qa_runner_cannot_dispatch_other_candidate_families(tmp_path):
    qa = case(identity="qa", group="source-one")
    qa["arms"] = ["candidate"]
    memory = case(identity="memory", family="learning_memory", group="source-two")
    memory["arms"] = ["candidate"]
    memory["task"] = {"question": "A memory preview, not a textbook QA request"}
    folder, _ = freeze_fixture(tmp_path, cases=[qa, memory])
    called = []

    def backend(task, arm, identity):
        called.append(identity)
        return {
            "state": "answered",
            "provider_calls": 0,
            "usage": {},
            "learner_visible_output": {"text": "Observed answer"},
        }

    result = execute(
        folder,
        backend,
        current_source_sha256="a" * 64,
        allowed_arms={"candidate"},
        allowed_families={"textbook_qa"},
    )
    assert called == ["qa::candidate"]
    assert result["deferred_to_other_family_runner"] == 1
    assert not (folder / "reservations" / "memory--candidate.json").exists()


def test_factorial_outcome_preserves_visible_hint_and_observed_counters():
    outcome = GenerationOutcome(
        response={"response_type": "answer", "answer_text": "Consider the canal first."},
        model_mode="live",
        model="deepseek-flash",
        provider="openai_compatible",
        delivered_projection={
            "response": {"answer_text": "Consider the canal first."},
            "citation_views": [{"source_title": "Anatomy and Physiology 2e"}],
        },
        evidence=[anchor()],
        usage={
            "input_tokens": 100,
            "output_tokens": 30,
            "cache_hit_input_tokens": 20,
            "cache_miss_input_tokens": 80,
        },
        budget={"consumed_calls": 2},
        checks=[{"accepted": True}],
    )
    record = normalize_teaching_outcome(outcome)
    assert record["state"] == "hinted"
    assert record["displayed_sources"][0]["source_title"] == "Anatomy and Physiology 2e"
    assert record["usage"]["cache_hit_input_tokens"] == 20
    assert record["provider_calls"] == 2
    assert record["online_checker_decision"] is True
    outcome.model_mode = "mock"
    with pytest.raises(ValueError, match="real answer"):
        normalize_teaching_outcome(outcome)


def test_quality_reports_reference_provenance_and_unknown_semantic_labels(tmp_path):
    supported = case()
    supported["label_provenance"] = "ai_generated"
    supported["private_labels"] = {"context_sufficient": True}
    folder, _ = freeze_fixture(tmp_path, cases=[supported])
    write_terminal(
        folder,
        {
            "schedule_id": "one::candidate",
            "state": "evidence_refusal",
            "elapsed_ms": 90,
            "provider_calls": 0,
            "learner_visible_output": None,
        },
    )
    summary = summarize(folder)
    quality = summary["label_source_quality"]["by_reference_label_provenance"]["ai_generated"][
        "textbook_qa"
    ]
    assert quality["wrong_refusal"]["numerator"] == 1
    assert quality["wrong_refusal"]["denominator"] == 4
    assert quality["wrong_refusal"]["rate"] is None  # Three planned arms are unstarted.
    assert quality["label_provenance"] == {"ai_generated": 4}


def test_judge_packet_scores_only_visible_output_and_keeps_failures():
    class FakeAdapter:
        def __init__(self):
            self.calls = 0

        def generate(self, messages, **kwargs):
            self.calls += 1
            assert "online_checker_decision" not in str(messages)
            return ProviderResult(
                raw_text=SemanticRating(
                    correct=True,
                    context_sufficient=True,
                    useful=True,
                    within_help=True,
                    citation_support=True,
                    coverage=True,
                    cumulative_leak=False,
                    publication_appropriate=True,
                    unsupported_claim=False,
                    claim_total=1,
                    supported_claims=1,
                    reason="The source supports the visible explanation.",
                    source_location="Biology 2e p.1",
                ).model_dump_json(),
                request_submitted=True,
                usage={"input_tokens": 20, "output_tokens": 10},
            )

    adapter = FakeAdapter()
    no_output = judge_packet({"learner_visible_output": None}, adapter)
    assert no_output["state"] == "no_output" and adapter.calls == 0
    scored = judge_packet({"learner_visible_output": {"text": "Answer"}}, adapter)
    assert scored["state"] == "rated" and scored["rating"]["correct"] is True
    assert adapter.calls == 1


def test_judge_retries_duplicate_keys_and_missing_required_fields_without_accepting_them():
    valid = SemanticRating(
        correct=True,
        context_sufficient=True,
        useful=True,
        within_help=None,
        citation_support=True,
        coverage=True,
        cumulative_leak=None,
        publication_appropriate=True,
        unsupported_claim=False,
        claim_total=1,
        supported_claims=1,
        reason="The displayed source supports the answer.",
        source_location="Biology 2e p.1",
    ).model_dump_json()

    class Adapter:
        def __init__(self, first):
            self.responses = [first, valid]
            self.messages = []

        def generate(self, messages, **kwargs):
            self.messages.append(messages)
            return ProviderResult(
                raw_text=self.responses.pop(0),
                request_submitted=True,
                usage={
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "cache_hit_input_tokens": 4,
                    "cache_miss_input_tokens": 16,
                    "total_tokens": 30,
                },
            )

    for invalid, expected_type in [
        ('{"correct":true,"correct":false}', "duplicate_key"),
        ('{"correct":true}', "schema_validation"),
    ]:
        adapter = Adapter(invalid)
        scored = judge_packet({"learner_visible_output": {"text": "Answer"}}, adapter)
        assert scored["state"] == "rated"
        assert scored["rating"]["correct"] is True
        assert scored["provider_calls"] == 2
        assert scored["usage"]["input_tokens"] == 40
        assert scored["usage"]["cache_hit_input_tokens"] == 8
        assert scored["attempts"][0]["validation_issue"]["type"] == expected_type
        assert len(adapter.messages) == 2
        assert "each required field exactly once" in adapter.messages[1][-1]["content"]


def test_judge_exhausts_bounded_invalid_output_and_retains_both_attempts():
    class Adapter:
        def __init__(self):
            self.calls = 0

        def generate(self, messages, **kwargs):
            self.calls += 1
            return ProviderResult(
                raw_text='{"correct":true,"correct":false}',
                request_submitted=True,
                usage={"input_tokens": 10, "output_tokens": 5, "cache_hit_input_tokens": 0},
            )

    adapter = Adapter()
    rejected = judge_packet({"learner_visible_output": {"text": "Answer"}}, adapter)
    assert adapter.calls == 2
    assert rejected["state"] == "invalid_output"
    assert rejected["rating"] is None
    assert rejected["provider_calls"] == 2
    assert rejected["usage"]["input_tokens"] == 20
    assert rejected["error"]["type"] == "duplicate_key"
    assert len(rejected["attempts"]) == 2
    assert all(row["raw_output_sha256"] for row in rejected["attempts"])


def test_clustered_teaching_effect_averages_repeats_before_bootstrap():
    observations = [
        {"concept_group": "g1", "arm": arm, "value": score}
        for arm, score in (("A", 0), ("B", 1), ("C", 0), ("D", 1))
    ] + [
        {"concept_group": "g2", "arm": arm, "value": score}
        for arm, score in (("A", 1), ("B", 1), ("C", 1), ("D", 0))
    ]
    observations.append({"concept_group": "g1", "arm": "B", "value": 1})
    result = teaching_contrasts(observations)
    assert result["B_minus_A"]["estimate"] == 0.5
    assert result["interaction"]["estimate"] == -0.5
    assert result["D_minus_A"]["paired_concept_groups"] == 2
    missing = clustered_contrast(
        [{"concept_group": "g", "arm": "A", "value": 1}], {"B": 1, "A": -1}
    )
    assert missing["estimate"] is None and missing["incomplete_groups"] == ["g"]
    assert holm_adjust({"first": 0.01, "second": 0.04}) == {"first": 0.02, "second": 0.04}


def test_simulated_student_receives_visible_turns_only_and_unfilled_calibration_is_unknown():
    visible = [{"role": "tutor", "text": "Try comparing one dimension."}]
    messages = learner_messages("novice", visible)
    assert "hidden_solution" not in json.dumps(messages)
    with pytest.raises(ValueError, match="learner-visible"):
        learner_messages(
            "novice", visible + [{"role": "tutor", "text": "More", "answer_key": "secret"}]
        )
    report = calibration_summary([{"persona": "novice", "persona_consistent": True}])
    assert report["calibrated"] is False
    assert report["dimensions"]["hidden_answer_ignorant"]["rate"] is None


def test_adaptive_attack_budget_and_legitimate_task_are_both_recorded(tmp_path):
    scenario = {
        "environment": "isolated_evaluation",
        "frozen_defense_hash": "a" * 64,
        "public_task": {"question": "What is osmosis?"},
    }
    seen = []

    def attacker(task, public_history, remaining):
        assert "private_labels" not in str(public_history)
        seen.append(len(public_history))
        return {"payload": f"attempt {len(public_history) + 1}", "attacker_tokens": 3}

    def defender(task, payload):
        return {
            "attack_success": payload.endswith("2"),
            "safe_task_completed": payload.endswith("1"),
            "public_observation": "answer shown",
        }

    summary = run_adaptive_attack(
        scenario, AttackLimits(3, 9), attacker, defender, tmp_path / "attack"
    )
    assert seen == [0, 1]
    assert summary["attempts"] == 2 and summary["attacker_tokens_used"] == 6
    assert summary["attack_success_observed"] is True
    assert summary["safe_legitimate_tasks_completed"] == 1
    with pytest.raises(ValueError, match="bounded"):
        AttackLimits(0, 9)


def test_live_answer_normalization_uses_actual_displayed_sources_and_keeps_failures():
    answered = normalize_answer(
        {
            "status": "completed",
            "receipt": {"job_id": "job1"},
            "answer": {
                "id": "answer1",
                "model_mode": "live",
                "response": {
                    "response_type": "answer",
                    "answer_text": "Content",
                    "citations": ["ev_001"],
                },
                "evidence": [{"evidence_id": "ev_001", "text": "Full private source"}],
                "presentation": {
                    "citation_views": [{"evidence_id": "ev_001", "preview": "Visible excerpt"}]
                },
                "answer_completeness": {"status": "partial"},
            },
        },
        hint=False,
    )
    assert answered["state"] == "supported_partial"
    assert answered["learner_visible_output"]["response"]["answer_text"] == "Content"
    assert answered["displayed_sources"][0]["preview"] == "Visible excerpt"
    assert answered["provider_calls"] is None
    assert (
        answered["submitted_evidence_scope"] == "saved_answer_evidence_not_exact_generation_prompt"
    )
    refused = normalize_answer(
        {
            "status": "refused",
            "receipt": {"job_id": "job2"},
            "answer": {"id": "answer2", "response": {"answer_text": "Evidence is insufficient"}},
        },
        hint=False,
    )
    assert refused["state"] == "evidence_refusal" and refused["learner_visible_output"] is None
    failure = normalize_answer(
        {
            "status": "error",
            "receipt": {"job_id": "job3"},
            "error": {"code": "EMPTY_PROVIDER_OUTPUT", "message": "Empty"},
        },
        hint=False,
    )
    assert failure["state"] == "empty_output" and failure["provider_calls"] is None


def test_memory_pilot_reports_selector_only_with_current_turn_precedence():
    class Counter:
        def count(self, value):
            return len(value.split())

    task = {
        "question": "Please answer briefly: why are eg orbitals higher in an octahedral complex?",
        "memory_entries": [
            {
                "category": "preference",
                "field_key": "detail_level",
                "scope": "global",
                "content": "Keep explanations detailed.",
            },
            {
                "category": "preference",
                "field_key": "detail_level",
                "scope": "chemistry",
                "content": "For chemistry questions, give detailed explanations.",
            },
        ],
    }
    result = MemorySelectorPilotBackend(counter=Counter())(task, "candidate", "memory::candidate")
    assert result["state"] == "diagnostic_observation"
    assert result["learner_visible_output"] is None
    assert result["provider_calls"] == 0
    assert result["usage"]["input_tokens"] == 0
    assert result["selected_memory_ids"] == []
    assert any(
        field.get("verification") == "current_user_instruction"
        for field in result["admin_or_internal_observation"]["fields"]
    )


def test_memory_pilot_uses_model_counter_and_keeps_relevant_subject_preference():
    class Counter:
        def count(self, value):
            return len(value.split())

    task = {
        "question": "How do plasmodesmata connect plant cells?",
        "memory_entries": [
            {
                "category": "preference",
                "field_key": "detail_level",
                "scope": "global",
                "content": "Keep explanations concise.",
            },
            {
                "category": "preference",
                "field_key": "detail_level",
                "scope": "biology",
                "content": "For biology questions, give detailed explanations.",
            },
        ],
    }
    result = MemorySelectorPilotBackend(counter=Counter())(task, "candidate", "biology::candidate")
    observed = result["admin_or_internal_observation"]
    assert len(result["selected_memory_ids"]) == 1
    assert observed["selected_entries"][0]["scope"] == "biology"
    assert observed["token_counting"] == "configured_tokenizer"
    assert observed["token_count"] < 768


@pytest.mark.parametrize(
    ("command", "family", "extra"),
    [
        ("run-memory-selectors", "learning_memory", []),
        ("run-visual-structure", "visual_structure", ["--credentials", "accounts.json"]),
        (
            "run-practice-proposals",
            "practice_feedback",
            ["--credentials", "accounts.json", "--allow-live"],
        ),
        (
            "run-qa-candidate",
            "textbook_qa",
            [
                "--email",
                "fixture@example.test",
                "--trace-database-url-env",
                "WEEK09_TEST_TRACE_URL",
                "--allow-live",
            ],
        ),
        (
            "run-teaching-factorial",
            "joint_tutoring",
            ["--preparation", "retrieval.json", "--allow-live"],
        ),
        (
            "run-interactive-probes",
            "safety_robustness",
            [
                "--credentials",
                "accounts.json",
                "--trace-database-url-env",
                "WEEK09_TEST_TRACE_URL",
                "--allow-live",
            ],
        ),
    ],
)
def test_week09_cli_dispatch_constructs_each_runner_without_network(
    command, family, extra, monkeypatch, capsys
):
    import sys

    import generation.token_counting as token_counting
    import scripts.verify.week09_continuation as cli

    class Counter:
        def count(self, value):
            return len(value.split())

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    class Chat:
        def capabilities(self):
            return {"model_mode": "live"}

    class Trace:
        def __init__(self, **kwargs):
            pass

        def close(self):
            pass

    monkeypatch.setattr(token_counting, "TokenCounter", lambda model: Counter())
    monkeypatch.setattr(
        cli,
        "load_frozen",
        lambda path: {
            "candidate": {
                "model_roles": {"generation": {}},
                "corpus_release_id": "release",
                "candidate_source_sha256": "a" * 64,
            }
        },
    )
    monkeypatch.setattr(cli.httpx, "Client", Client)
    monkeypatch.setattr(cli, "HttpChatBackend", lambda *args, **kwargs: Chat())
    monkeypatch.setattr(cli, "_private_chat", lambda *args, **kwargs: Chat())
    monkeypatch.setattr(cli, "IsolatedTraceUsage", Trace)
    monkeypatch.setattr(cli, "TextbookQAHttpBackend", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "TeachingPreparedBackend", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "VisualStructurePilotBackend", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "InteractivePilotBackend", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        cli,
        "execute",
        lambda study, backend, **kwargs: {"allowed_families": sorted(kwargs["allowed_families"])},
    )
    monkeypatch.setenv("EVALUATION_ACCOUNT_PASSWORD", "unit-test-only")
    monkeypatch.setenv("WEEK09_TEST_TRACE_URL", "unit-test-only")
    monkeypatch.setenv("LLM_API_KEY", "unit-test-only")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "week09_continuation",
            command,
            "--study",
            "frozen-study",
            "--candidate-source-sha256",
            "a" * 64,
            *extra,
        ],
    )
    cli.main()
    output = json.loads(capsys.readouterr().out)
    assert family in output["result"]["allowed_families"]


def test_visual_pilot_uses_actual_admin_region_without_human_geometry_claim():
    class Admin:
        def _request(self, method, path):
            assert method == "GET" and path.endswith("/region-1")
            return {
                "id": "region-1",
                "document_id": "book-1",
                "physical_pdf_page": 225,
                "kind": "figure_image",
                "candidate_status": "needs_visual_review",
                "answer_evidence_eligible": False,
            }

    result = VisualStructurePilotBackend(Admin())(
        {
            "region_id": "region-1",
            "document_id": "book-1",
            "physical_page": 225,
            "kind": "figure_image",
        },
        "candidate",
        "visual::candidate",
    )
    assert result["state"] == "diagnostic_observation"
    assert result["admin_or_internal_observation"]["task_structural_match"] is True
    assert "visual_review" in result["admin_or_internal_observation"]["scope"]


def test_practice_pilot_stops_before_publication_or_student_attempt():
    seen = []

    class Admin:
        def _request(self, method, path, body=None, headers=None):
            seen.append((method, path, body, headers))
            if path.endswith("practice-proposals"):
                return {
                    "item": {"id": "draft-1"},
                    "validation_details": {"proposal_attempt_id": "p1"},
                }
            return {
                "item": {
                    "kind": "mcq",
                    "concepts": ["central canal"],
                    "prompt": "Question",
                    "options": [],
                },
                "state": "validated",
                "validation_details": {"status": "passed", "issues": []},
            }

    result = PracticeProposalPilotBackend(
        Admin(), frozen_manifest_sha256="a" * 64, candidate_source_sha256="b" * 64
    )(
        {
            "source_locator": {"release_id": "release-1"},
            "kind": "mcq",
            "concepts": ["central canal"],
        },
        "candidate",
        "practice::candidate",
    )
    assert result["state"] == "diagnostic_observation"
    assert result["provider_calls"] is None
    assert result["admin_or_internal_observation"]["practice_attempt_executed"] is False
    assert len(seen) == 2 and all("publish" not in row[1] for row in seen)


def test_practice_idempotency_is_stable_within_study_and_changes_across_freezes():
    class Admin:
        pass

    first = PracticeProposalPilotBackend(
        Admin(), frozen_manifest_sha256="a" * 64, candidate_source_sha256="b" * 64
    )
    same = PracticeProposalPilotBackend(
        Admin(), frozen_manifest_sha256="a" * 64, candidate_source_sha256="b" * 64
    )
    changed_manifest = PracticeProposalPilotBackend(
        Admin(), frozen_manifest_sha256="c" * 64, candidate_source_sha256="b" * 64
    )
    changed_source = PracticeProposalPilotBackend(
        Admin(), frozen_manifest_sha256="a" * 64, candidate_source_sha256="d" * 64
    )
    identity = "same-case::candidate"
    assert first.idempotency_key(identity) == same.idempotency_key(identity)
    assert first.idempotency_key(identity) != changed_manifest.idempotency_key(identity)
    assert first.idempotency_key(identity) != changed_source.idempotency_key(identity)


def test_cross_owner_probe_reads_completed_owner_answer_with_other_account(tmp_path):
    folder, _ = freeze_fixture(tmp_path)

    class Response:
        status_code = 404
        content = b'{"error":"NOT_FOUND"}'

    class Client:
        def get(self, path, headers):
            assert path == "/api/v1/answers/answer-1"
            assert headers == {"Authorization": "Bearer other"}
            return Response()

    class Chat:
        def __init__(self, email, headers):
            self.email = email
            self.headers = headers
            self.client = Client()

    owner = Chat("owner@example.edu", {})
    other = Chat("other@example.edu", {"Authorization": "Bearer other"})
    write_terminal(
        folder,
        {
            "schedule_id": "one::candidate",
            "state": "answered",
            "learner_visible_output": {"text": "A valid owned answer"},
            "elapsed_ms": 1,
            "evaluation_owner_fingerprint": hashlib.sha256(owner.email.encode()).hexdigest(),
            "application_receipt": {"answer_id": "answer-1"},
        },
    )
    backend = InteractivePilotBackend(folder, owner, other)
    assert backend._cross_owner()["state"] == "security_block"


def test_simulator_calibration_sends_only_visible_hint_and_retains_separate_ai_rating(
    tmp_path, monkeypatch
):
    import evaluation.week09_continuation.simulator_pilot as module

    study = tmp_path / "pilot"
    study.mkdir()
    (study / "manifest.json").write_bytes(b"frozen-manifest")
    preparation = tmp_path / "retrieval.json"
    preparation.write_bytes(
        canonical(
            {
                "model_config": {
                    "provider": "openai_compatible",
                    "model": "fixture-model",
                    "base_url": "https://api.example.com/v1",
                }
            }
        )
    )
    monkeypatch.setattr(
        module,
        "load_frozen",
        lambda _: {
            "split": "pilot",
            "candidate": {
                "candidate_source_sha256": "a" * 64,
                "teaching_retrieval_sha256": digest_bytes(preparation.read_bytes()),
                "tariff": {
                    "input_per_million": 1,
                    "output_per_million": 2,
                    "cache_hit_input_per_million": 0.2,
                },
            },
        },
    )
    monkeypatch.setattr(
        module,
        "_visible_hint",
        lambda _: (
            {"id": "hint::D"},
            {
                "task": {"question": "How does it work?"},
                "source_anchors": [{"text": "Hidden source detail"}],
                "required_points": ["Hidden required point"],
                "unsupported_conclusions": [],
            },
            {
                "learner_visible_output": {"response": {"answer_text": "Consider the first step."}},
                "displayed_sources": [],
            },
        ),
    )
    calls = []

    class Adapter:
        def __init__(self, config, api_key):
            assert api_key == "unit-test-only"
            assert config.max_tokens == module.SIMULATOR_OUTPUT_TOKEN_BUDGET

        def generate_basic(self, messages, **kwargs):
            return self.generate(messages, **kwargs)

        def generate(self, messages, **kwargs):
            from types import SimpleNamespace

            calls.append(messages)
            judged = "response_schema" in kwargs
            return SimpleNamespace(
                error=None,
                raw_text=(
                    json.dumps(
                        {
                            "persona_consistent": True,
                            "hidden_answer_ignorant": True,
                            "guidance_response_reasonable": True,
                            "stays_in_learner_role": True,
                            "reason": "The student follows only the displayed first step.",
                        }
                    )
                    if judged
                    else "I will try the first step."
                ),
                usage={
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "cache_hit_input_tokens": 0,
                },
                request_submitted=True,
            )

    summary = run_one_turn_calibration(
        study,
        preparation,
        tmp_path / "simulator",
        candidate_source_sha256="a" * 64,
        api_key="unit-test-only",
        adapter_factory=Adapter,
    )
    assert len(calls) == 10
    assert summary["calibrated"] is True
    assert summary["multi_turn_trajectory_executed"] is False
    assert summary["human_ratings"] == 0
    assert summary["cost_unknown_calls"] == 0
    student_inputs = [calls[index] for index in range(0, 10, 2)]
    assert all("Hidden required point" not in json.dumps(row) for row in student_inputs)
