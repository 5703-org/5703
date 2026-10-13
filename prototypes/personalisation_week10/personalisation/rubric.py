"""Anchored independent review; missing scores are never converted to zero."""

DIMENSIONS = (
    "level_fit",
    "clarity",
    "prerequisite_support",
    "usefulness",
    "guidance",
    "consistency",
)
GATES = ("correctness", "groundedness")
ANCHORS = {
    0: "Absent, incorrect, or fundamentally unsuitable for the target learner.",
    1: "Major problems materially obstruct understanding or safe use.",
    2: "Acceptable with minor limitations; meaning and source support are preserved.",
    3: "Clear, well matched and useful with no material issue found.",
}


def rating_template(item_id: str, rater_id: str):
    return {
        "item_id": item_id,
        "rater_id": rater_id,
        "ratings": {name: None for name in (*DIMENSIONS, *GATES)},
        "notes": "",
        "rubric_version": "profile_rating_v1",
    }


def validate_rating(record: dict):
    ratings = record.get("ratings", {})
    if set(ratings) != set((*DIMENSIONS, *GATES)):
        raise ValueError("All rating dimensions must be represented explicitly")
    if any(v is not None and (type(v) is not int or not 0 <= v <= 3) for v in ratings.values()):
        raise ValueError("Ratings must be null or integer 0-3")
    return {
        "complete": all(v is not None for v in ratings.values()),
        "gates_passed": None
        if any(ratings[g] is None for g in GATES)
        else all(ratings[g] >= 2 for g in GATES),
    }
