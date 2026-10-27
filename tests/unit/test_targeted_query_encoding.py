import pytest

from generation.targeted_query_encoding import POLICY, prepare


@pytest.mark.parametrize(
    "original,requirement",
    [
        ("Compare both velocities with units. State the uncertainty.", "State the uncertainty"),
        ("Give both concentrations. Do not assume equal volumes.", "Do not assume equal volumes"),
        (
            "Explain pressure at 20 degrees, with its units.",
            "Explain pressure at 20 degrees, with its units.",
        ),
    ],
)
def test_exact_duplication_preserves_all_original_conditions(original, requirement):
    query = original + "\nRequired knowledge: " + requirement
    effective, audit = prepare(query, original, POLICY)
    assert effective == original and audit["requested_query"] == query
    assert not audit["source_text_modified"] and audit["removed_duplicate_characters"] > 0
    assert prepare(query, original, None) == (query, None)


@pytest.mark.parametrize(
    "suffix",
    [
        "",
        "State the uncertainty in kelvin",
        "different",
        "state the uncertainty",
        "State  the uncertainty",
    ],
)
def test_nonidentical_or_additional_requirements_are_not_discarded(suffix):
    original = "State the uncertainty."
    query = original + "\nRequired knowledge: " + suffix
    assert prepare(query, original, POLICY)[0] == query


def test_wrong_prefix_unknown_policy_and_source_objects_are_not_repaired():
    assert (
        prepare("Different\nRequired knowledge: Original", "Original", POLICY)[0]
        == "Different\nRequired knowledge: Original"
    )
    with pytest.raises(ValueError):
        prepare("question", "question", "future")
