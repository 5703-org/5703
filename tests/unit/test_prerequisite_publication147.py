from copy import deepcopy
import pytest
from app.core.exceptions import AppError
from app.modules.knowledge.models import Document
from app.modules.learning_state import sources
from app.modules.learning_state.models import AnswerAttribution, AnswerPresentation
from retrieval.prerequisite_context_v1 import candidate, selector
from test_raw_definition_source_blocks_v2 import publication_fixture


def outcome(fallback=False):
    db, request, answer, result = publication_fixture()
    request.command.update(
        source_block_policy=candidate.VERSION, generation_context_policy=selector.VERSION
    )
    result.token_budget["prerequisite_context_pair"] = {
        "bundle_version": "raw_corroborated_literal_context_v1",
        "requested_source_version": candidate.VERSION,
        "requested_context_version": selector.VERSION,
        "actual_source_version": "raw_definition_block_partition_v2"
        if fallback
        else candidate.VERSION,
        "actual_context_version": "complementary_context_v2" if fallback else selector.VERSION,
        "fallback": "candidate_algorithm_runtime_error" if fallback else None,
        "fallback_error_type": "RuntimeError" if fallback else None,
    }
    if not fallback:
        fragments, issues = candidate.map_fragments(
            result.evidence, sources.source_map(db, request, result.evidence)
        )
        result.attribution["fragments"] = fragments
        result.attribution["mapping_issues"] = issues
        result.attribution["claims"][0]["fragment_ids"] = [fragments[0]["fragment_id"]]
    return db, request, answer, result


def test_actual_publication_reconstructs_candidate_and_whole_native_fallback_pairs():
    from retrieval.source_spans_v2 import map_fragments as raw_mapper

    for fallback in (False, True):
        db, request, answer, result = outcome(fallback)
        assert sources._publication_mapper(request, result) is (
            raw_mapper if fallback else candidate.map_fragments
        )
        before = deepcopy(result.attribution)
        sources.persist_result(db, request, answer, result)
        assert result.attribution == before
        assert next(row for row in db.rows if isinstance(row, AnswerAttribution)).payload == before
        assert (
            next(row for row in db.rows if isinstance(row, AnswerPresentation)).payload["response"]
            == result.response
        )


def test_publication_missing_half_or_mismatched_pair_stops_before_projection():
    for variant in ("missing", "half", "actual", "requested", "fake_fallback"):
        db, request, answer, result = outcome()
        if variant == "missing":
            result.token_budget.clear()
        elif variant == "half":
            request.command["generation_context_policy"] = "complementary_context_v2"
        elif variant == "actual":
            result.token_budget["prerequisite_context_pair"]["actual_context_version"] = (
                "complementary_context_v2"
            )
        elif variant == "requested":
            result.token_budget["prerequisite_context_pair"]["requested_source_version"] = "foreign"
        else:
            result.token_budget["prerequisite_context_pair"]["fallback"] = "ignored_integrity_error"
        with pytest.raises(AppError):
            sources.persist_result(db, request, answer, result)
        assert not db.rows


def test_candidate_publication_retains_live_revocation_and_exact_fragment_guards():
    assert sources._stored_mapping_quality(candidate.VERSION) == "raw_corroborated_prose_context_v1"
    with pytest.raises(AppError):
        sources._stored_mapping_quality("unknown_quality_" + "x" * 40)
    for variant in ("revoked", "forged_fragment"):
        db, request, answer, result = outcome()
        if variant == "revoked":
            db.records[Document, result.evidence[0]["asset_id"]].revoked = True
        else:
            result.attribution["fragments"][0]["exact_text"] += " forged"
        with pytest.raises(AppError):
            sources.persist_result(db, request, answer, result)
        assert not db.rows
