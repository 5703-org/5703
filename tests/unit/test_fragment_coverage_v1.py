"""Identity/complement controls; authored bundles are not semantic accuracy gold."""

import pytest

from evaluation.fragment_coverage_v1 import measure_fragment_coverage

KNOWN = ["F037", "F053", "F054", "F055", "F051"]
LINK = {
    "id": "carbohydrate_component",
    "kind": "claim_support",
    "complete_support_bundles": [["F054", "F055"]],
}


def measure(selected, requirements=None, known=None):
    return measure_fragment_coverage(
        selected,
        [LINK] if requirements is None else requirements,
        known_fragment_ids=KNOWN if known is None else known,
    )


@pytest.mark.parametrize(
    "selected,expected",
    [
        ([], False),
        (["F054"], False),
        (["F055"], False),
        (["F053"], False),
        (["F054", "F055"], True),
    ],
)
def test_complementary_fragments_are_jointly_required(selected, expected):
    result = measure(selected)
    assert result["requirements"][0]["covered"] is expected
    assert result["source_entailment_or_model_accuracy_judged"] is False


def test_available_but_unselected_fragment_does_not_complete_support():
    result = measure(["F054"])
    assert result["requirements"][0]["missing_fragment_ids_by_alternative"] == [["F055"]]
    assert result["covered"] == 0


def test_alternative_complete_bundles_are_or_and_each_bundle_is_and():
    requirement = dict(LINK, complete_support_bundles=[["F054", "F055"], ["F051", "F053"]])
    assert measure(["F051"], [requirement])["covered"] == 0
    assert measure(["F051", "F053"], [requirement])["covered"] == 1
    assert measure(["F054", "F055", "F051", "F053"], [requirement])["covered"] == 1


def test_claim_and_question_facet_counts_are_separate():
    facet = {"id": "location", "kind": "question_facet", "complete_support_bundles": [["F037"]]}
    result = measure(["F037"], [LINK, facet])
    assert result["by_kind"] == {
        "claim_support": {"covered": 0, "total": 1, "fraction": 0},
        "question_facet": {"covered": 1, "total": 1, "fraction": 1},
    }


def test_no_declared_support_is_never_vacuously_covered():
    requirement = dict(LINK, complete_support_bundles=[])
    result = measure(KNOWN, [requirement])
    assert result["covered"] == 0 and result["requirements"][0]["no_complete_support_declared"]
    assert measure([], [])["fraction"] is None


@pytest.mark.parametrize(
    "selected,requirements,known",
    [
        (["NOT_IN_POOL"], [LINK], KNOWN),
        (["F054", "F054"], [LINK], KNOWN),
        ([" F054"], [LINK], KNOWN),
        ([], [LINK], KNOWN + ["F037"]),
        ([], [LINK, LINK], KNOWN),
        ([], [dict(LINK, complete_support_bundles=[["NOT_IN_POOL"]])], KNOWN),
        ([], [dict(LINK, complete_support_bundles=[[]])], KNOWN),
        ([], [dict(LINK, complete_support_bundles=[["F054", "F054"]])], KNOWN),
        ([], [dict(LINK, complete_support_bundles=[["F054", "F055"], ["F055", "F054"]])], KNOWN),
        ([], [dict(LINK, kind="")], KNOWN),
    ],
)
def test_invalid_or_ambiguous_input_is_rejected(selected, requirements, known):
    with pytest.raises(ValueError):
        measure(selected, requirements, known)


def test_input_order_and_objects_are_preserved():
    selected = ["F055", "F054"]
    before = repr(LINK)
    result = measure(selected)
    assert result["selected_fragment_ids"] == selected and repr(LINK) == before
    assert LINK["complete_support_bundles"] == [["F054", "F055"]]
