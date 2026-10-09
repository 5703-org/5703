"""A learning objective alone cannot ground a generated practice answer."""

from app.modules.learning_product.proposals import objective_only_concepts


def test_objective_only_concept_is_identified_before_model_call():
    text = (
        "Learning objectives: Understand osmosis. "
        "The following text describes passive transport in general."
    )
    assert objective_only_concepts(text, ["Understand osmosis"], ["osmosis"]) == ["osmosis"]


def test_explanatory_occurrence_is_not_rejected():
    text = (
        "Learning objectives: Understand osmosis. "
        "Osmosis is water movement across a semipermeable membrane."
    )
    assert objective_only_concepts(text, ["Understand osmosis"], ["osmosis"]) == []


def test_single_body_occurrence_without_objective_is_not_rejected():
    text = "Osmosis is water movement across a semipermeable membrane."
    assert objective_only_concepts(text, [], ["osmosis"]) == []
