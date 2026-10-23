"""Authored zero-network continuation controls, not measured semantic accuracy."""

from copy import deepcopy
from dataclasses import replace
import json
import pytest
from generation import GenerationService, RequestBudget
from generation import assertion_bounded_revision_v1 as revision
from generation import assertion_provenance_v1 as assertions
from generation.reliability_v5 import response_claims
from fixtures_generic163 import authored_parent, checker_labels, ScriptedTransport
from test_assertion_reselection163 import fresh_check


def prepared(kind="unsupported_assertion"):
    request, parent, fragments = authored_parent(source_ids=["F001", "F002"])
    request.config = replace(request.config, model="authored-offline-revision")
    raw = json.loads(parent["drafts"][0]["raw_model_output"])
    raw["answer_text"][0]["text"] = (
        "Pressure from chamber P moves piston T and lifts its attached load against gravity."
    )
    public, provenance = assertions.compile_draft(raw, fragments)
    public.pop("tutor_question")
    public.pop("learner_attempt_evaluation")
    draft = parent["drafts"][0]
    draft.update(response=public, assertion_provenance=provenance, raw_model_output=json.dumps(raw))
    typed = checker_labels(provenance, negative_target=kind == "unsupported_assertion")
    if kind == "missing_required_condition":
        typed["complete_answer"] = False
        typed["requirements"][0].update(response_coverage="partial", conditions_preserved=False)
    parent["checks"][0].update(
        typed_judgment_raw_aliases=typed,
        actual_citation_bindings=assertions.checker_bindings(
            response_claims(public), provenance, fragments
        ),
    )
    parent["token_budget"]["context_coverage"] = {
        "packed_coverage": {"requirements": [{"id": "requirement_01", "request": request.question}]}
    }
    row = provenance["assertions"][0]
    source = row["sources"][0]
    diagnosis = {
        "version": "assertion_revision_diagnosis_v1",
        "parent_outcome_sha256": revision.canonical_sha256(parent),
        "request_binding_sha256": revision.request_sha256(request),
        "source_bank_sha256": revision.canonical_sha256(
            assertions.source_bank(fragments, parent["evidence"])
        ),
        "targets": [
            {
                "claim_id": row["claim_id"],
                "prior_binding_sha256": revision.binding_sha256(row),
                "kind": kind,
                "requirement_ids": ["requirement_01"],
                "support_quotes": [
                    {
                        "source_id": source["source_id"],
                        "text_sha256": source["text_sha256"],
                        "quote": source["exact_text"],
                    }
                ],
                "reason": "Authored independent diagnosis: the valve-open condition is omitted.",
            }
        ],
    }
    envelope = revision.freeze_continuation(
        request,
        parent,
        diagnosis,
        parent_draft_id="saved-draft",
        parent_check_id="saved-check",
        source_admission={"release_id": "authored-release", "source_epoch": "authored-epoch"},
    )
    request.assertion_reselection = envelope
    return request, parent, fragments, envelope


def propose(messages):
    packet = json.loads(messages[-1]["content"])
    target = packet["targets"][0]
    original = next(
        r["assertion_text"] for r in packet["assertions"] if r["claim_id"] == target["claim_id"]
    )
    return {
        **packet["bindings"],
        "plan_sha256": packet["plan_sha256"],
        "edits": [
            {
                "claim_id": target["claim_id"],
                "prior_binding_sha256": target["prior_binding_sha256"],
                "replacement_text": "Only when valve A is open, " + original,
            }
        ],
    }


@pytest.mark.parametrize("kind", ["unsupported_assertion", "missing_required_condition"])
def test_one_revision_and_whole_fresh_check_preserve_sources_and_parent(kind):
    request, parent, fragments, envelope = prepared(kind)
    before = deepcopy(parent)
    transport = ScriptedTransport([propose, fresh_check])
    events = []
    result = GenerationService(transport).generate(
        request, RequestBudget.from_dict(parent["budget"]), events.append
    )
    assert result.succeeded, result.error
    assert [x["stage"] for x in result.attempts] == ["assertion_prose_revision", "joint_recheck"]
    assert len(transport.calls) == 2 and result.budget["consumed_calls"] == 4
    assert result.budget["format_repairs"] == result.budget["transient_retries"] == 0
    assert len(events) == 4 and parent == before
    assert "when valve A is open" in result.response["answer_text"]
    assert result.response["citations"] == before["drafts"][0]["response"]["citations"]
    assert result.drafts[0]["assertion_reselection"]["source_bindings_changed"] is False
    assert result.drafts[0]["assertion_reselection"]["semantic_support_certified"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "conditions_preserved",
        "actor_identity_preserved",
        "causal_bridges_entailed",
        "duplicate_ID",
        "phantom_ID",
    ],
)
def test_recheck_rejection_never_publishes_or_tries_again(fault):
    request, parent, _, _ = prepared()
    transport = ScriptedTransport([propose, lambda messages: fresh_check(messages, defect=fault)])
    result = GenerationService(transport).generate(
        request, RequestBudget.from_dict(parent["budget"])
    )
    assert not result.succeeded and result.response is None and result.delivered_projection == {}
    assert len(transport.calls) == 2 and result.budget["consumed_calls"] == 4


@pytest.mark.parametrize(
    "fault",
    [
        "quote",
        "hash",
        "foreign_source",
        "requirement",
        "duplicate",
        "budget",
        "unknown",
        "source",
        "history",
        "request",
    ],
)
def test_admission_faults_stop_before_any_dispatch(fault):
    request, parent, fragments, envelope = prepared()
    if fault in {"quote", "hash", "foreign_source", "requirement", "duplicate", "unknown"}:
        target = envelope["diagnosis"]["targets"][0]
        if fault == "quote":
            target["support_quotes"][0]["quote"] = "Missing invented source text"
        elif fault == "hash":
            target["support_quotes"][0]["text_sha256"] = "0" * 64
        elif fault == "foreign_source":
            target["support_quotes"][0]["source_id"] = "F004"
        elif fault == "requirement":
            target["requirement_ids"] = ["unknown"]
        elif fault == "duplicate":
            envelope["diagnosis"]["targets"].append(deepcopy(target))
        else:
            envelope["parent_outcome"]["attempts"][0]["request_submitted"] = None
        if fault == "unknown":
            envelope["parent_outcome_sha256"] = revision.canonical_sha256(
                envelope["parent_outcome"]
            )
            envelope["diagnosis"]["parent_outcome_sha256"] = envelope["parent_outcome_sha256"]
        envelope["continuation_sha256"] = revision.canonical_sha256(
            {k: v for k, v in envelope.items() if k != "continuation_sha256"}
        )
    budget = RequestBudget.from_dict(parent["budget"])
    if fault == "budget":
        budget.max_calls = 5
    elif fault == "source":
        fragments[0]["exact_text"] += "changed"
    elif fault == "history":
        request.history = [{"role": "user", "content": "private prior question"}]
    elif fault == "request":
        request.question += " altered"
    with pytest.raises((ValueError, KeyError)):
        revision.prepare(request, envelope, fragments, parent["evidence"], budget)


def test_completeness_edit_cannot_remove_supported_text_or_change_sources():
    request, parent, fragments, envelope = prepared("missing_required_condition")
    plan = revision.prepare(
        request, envelope, fragments, parent["evidence"], RequestBudget.from_dict(parent["budget"])
    )
    proposal = propose([{"content": json.dumps(revision.selector_packet(plan))}])
    proposal["edits"][0]["replacement_text"] = "Valve A is open."
    with pytest.raises(ValueError, match="SUPPORTED_ORIGINAL_TEXT_REMOVED"):
        revision.bind_proposal(plan, proposal, fragments, parent["evidence"])


def test_experiment_disabled_before_database_access():
    from app.core.config import Settings
    from app.core.exceptions import AppError
    from app.modules.answering.service import submit_assertion_revision

    assert Settings(_env_file=None).experimental_assertion_revision_enabled is False
    with pytest.raises(AppError, match="disabled"):
        submit_assertion_revision(
            None,
            Settings(_env_file=None),
            None,
            parent_request_id="unused",
            saved_failure_id="unused",
            diagnosis={},
        )


@pytest.mark.parametrize(
    "metadata,expected",
    [
        ({"verification_mode": "verified"}, True),
        ({"verification_mode": "fast"}, False),
        ({"verification_mode": "verified", "unknown": "private"}, False),
        ({"verification_mode": "verified", "profile": {"name": "Synthetic"}}, False),
    ],
)
def test_only_bound_verified_metadata_is_compatible(metadata, expected):
    from generation.assertion_reselection_v1 import context_free as legacy_context_free

    request, _, _, _ = prepared()
    request.teaching_context = {**request.teaching_context, **metadata}
    assert not legacy_context_free(request)
    assert revision.context_free(request) is expected
    request.verification_mode = "fast"
    assert not revision.context_free(request)


@pytest.mark.parametrize(
    "fault", ["insufficient_source", "checker_inconsistency", "derived_policy", "expired_budget"]
)
def test_semantic_or_budget_ineligibility_is_not_an_edit_license(fault):
    request, parent, fragments, envelope = prepared()
    check = envelope["parent_outcome"]["checks"][0]
    if fault == "insufficient_source":
        check["typed_judgment_raw_aliases"]["requirements"][0]["sufficiency"] = "insufficient"
    elif fault == "checker_inconsistency":
        check["repairable_verdict_inconsistencies"] = [{"code": "AUTHORED_CONTRADICTION"}]
    elif fault == "derived_policy":
        request.provider_output_policy = next(iter(revision.DERIVED_CITATION_POLICIES))
        envelope["request_binding_sha256"] = revision.request_sha256(request)
        envelope["diagnosis"]["request_binding_sha256"] = envelope["request_binding_sha256"]
    envelope["parent_outcome_sha256"] = revision.canonical_sha256(envelope["parent_outcome"])
    envelope["diagnosis"]["parent_outcome_sha256"] = envelope["parent_outcome_sha256"]
    envelope["continuation_sha256"] = revision.canonical_sha256(
        {k: v for k, v in envelope.items() if k != "continuation_sha256"}
    )
    budget = RequestBudget.from_dict(parent["budget"])
    if fault == "expired_budget":
        budget.active_seconds = budget.max_active_seconds
    with pytest.raises(ValueError):
        revision.prepare(request, envelope, fragments, parent["evidence"], budget)


@pytest.mark.parametrize(
    "fault", ["success_flag", "citation_injection", "wrong_plan", "unapproved_claim", "unchanged"]
)
def test_bad_revision_proposal_consumes_one_call_without_check_retry_or_publication(fault):
    request, parent, _, _ = prepared()

    def bad_proposal(messages):
        value = propose(messages)
        if fault == "success_flag":
            value["success"] = True
        elif fault == "citation_injection":
            value["edits"][0]["citations"] = ["ev999"]
        elif fault == "wrong_plan":
            value["plan_sha256"] = "0" * 64
        elif fault == "unapproved_claim":
            value["edits"][0]["claim_id"] = "unknown"
        else:
            value["edits"][0]["replacement_text"] = value["edits"][0][
                "replacement_text"
            ].removeprefix("Only when valve A is open, ")
        return value

    transport = ScriptedTransport([bad_proposal])
    result = GenerationService(transport).generate(
        request, RequestBudget.from_dict(parent["budget"])
    )
    assert not result.succeeded and result.response is None and result.delivered_projection == {}
    assert len(transport.calls) == 1 and result.budget["consumed_calls"] == 3
    assert result.budget["format_repairs"] == result.budget["transient_retries"] == 0
