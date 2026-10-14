"""Actual public U02 source reconstruction; no model or semantic acceptance claim."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.modules.learning_state import sources
from app.modules.learning_state.models import AnswerPresentation
from generation.types import GenerationOutcome
from retrieval import source_spans as legacy
from retrieval import source_spans_v2 as successor
from test_raw_definition_source_blocks_v2 import SourcePublicationDB

FIXTURE = Path(__file__).parents[1] / "fixtures/source_publication/u02_diffusion_20261006.json"


def actual_source_result():
    saved = json.loads(FIXTURE.read_text(encoding="utf-8"))
    evidence, mapping = saved["evidence"], saved["source_map"]
    for item in evidence:
        mapping[item["chunk_id"]].update(
            submitted_start=item["chunk_start"], submitted_end=item["chunk_end"]
        )
    fragments, issues = successor.map_fragments(evidence, mapping)
    columns = saved["checker_fragments"]["columns"]
    expected = [dict(zip(columns, row)) for row in saved["checker_fragments"]["rows"]]
    assert len(fragments) == len(expected) == 64
    for index, (actual, recorded) in enumerate(zip(fragments, expected), 1):
        assert recorded["fragment_id"] == f"F{index:03d}"
        assert {key: actual[key] for key in columns if key != "fragment_id"} == {
            key: recorded[key] for key in columns if key != "fragment_id"
        }
    aliases = {
        row["fragment_id"]: fragment["fragment_id"] for row, fragment in zip(expected, fragments)
    }
    projection = deepcopy(saved["proposed_delivery"])
    for view in projection.get("citation_views", []):
        for segment in view["segments"]:
            segment["fragment_ids"] = [aliases[identity] for identity in segment["fragment_ids"]]
    result = GenerationOutcome(
        response=deepcopy(projection["response"]),
        evidence=deepcopy(evidence),
        attribution={"fragments": fragments, "mapping_issues": issues, "claims": []},
        delivered_projection=projection,
        token_budget={"source_block_policy": saved["source_block_policy"]},
    )
    # Claims are deliberately outside this source-identity-only boundary control.
    request = SimpleNamespace(
        id=saved["original_request_id"],
        release_id="authored-release",
        owner_id="authored-learner",
        command={
            "enhancement_version": "learning_enhancement_v1",
            "source_block_policy": saved["source_block_policy"],
        },
    )
    return (
        SourcePublicationDB(evidence, mapping),
        request,
        SimpleNamespace(id="authored-answer"),
        result,
    )


def test_actual_u02_all_fragments_include_the_unused_raw_partition_missing_from_legacy():
    db, request, _answer, result = actual_source_result()
    old, _ = legacy.map_fragments(result.evidence, sources.source_map(db, request, result.evidence))
    assert len(old) == 61
    allowed = {(f["fragment_id"], f["evidence_id"]) for f in old}
    missing = [
        f
        for f in result.attribution["fragments"]
        if (f["fragment_id"], f["evidence_id"]) not in allowed
    ]
    assert len(missing) == 4 and all(f["evidence_id"] == "ev_010" for f in missing)
    first = missing[0]
    assert first["fragment_id"] == "span_6c486195c6056c906ccf75e2aee32d61"
    assert (first["start"], first["end"]) == (1476, 1530)
    assert first["exact_text"] == "Diffusion Diffusion is a passive process of transport."


def test_actual_u02_complete_fragment_attribution_persists_with_its_frozen_mapper():
    db, request, answer, result = actual_source_result()
    before = deepcopy(result.attribution)
    sources.persist_result(db, request, answer, result)
    assert result.attribution == before
    assert any(isinstance(row, AnswerPresentation) for row in db.rows)


@pytest.mark.parametrize("defect", ["fragment-id", "fragment-hash", "wrong-frozen-policy"])
def test_actual_u02_source_control_still_withholds_tampered_or_policy_mismatched_fragments(defect):
    db, request, answer, result = actual_source_result()
    if defect == "fragment-id":
        result.attribution["fragments"][0]["fragment_id"] = "span_foreign"
    elif defect == "fragment-hash":
        result.attribution["fragments"][0]["text_hash"] = "0" * 64
    else:
        request.command["source_block_policy"] = "legacy_source_blocks_v1"
    with pytest.raises(AppError, match="structural validation"):
        sources.persist_result(db, request, answer, result)
    assert not any(isinstance(row, AnswerPresentation) for row in db.rows)
