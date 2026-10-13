"""Pure fragment-set coverage reference; it does not assess scientific truth."""

from itertools import product


def _unique_ids(values, *, name, allowed=None):
    if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
        raise ValueError(f"{name} requires nonempty string IDs")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} contains duplicate IDs")
    if allowed is not None and not set(values) <= allowed:
        raise ValueError(f"{name} contains unknown IDs")
    return set(values)


def flatten_groups(groups, *, allowed_fragment_ids, maximum_bundles=256):
    """AND across groups; OR among each group's complete fragment bundles."""
    allowed = _unique_ids(allowed_fragment_ids, name="allowed fragments")
    if not isinstance(groups, list) or not groups:
        raise ValueError("At least one support group is required")
    choices = []
    total = 1
    for group in groups:
        if not isinstance(group, list) or not group:
            raise ValueError("Each support group needs at least one complete bundle")
        for bundle in group:
            if not _unique_ids(bundle, name="complete bundle", allowed=allowed):
                raise ValueError("An empty bundle cannot certify a requirement")
        choices.append(group)
        total *= len(group)
        if total > maximum_bundles:
            raise ValueError("Explicit support combination bound exceeded")
    bundles = {tuple(sorted(set().union(*(set(b) for b in combination)))) for combination in product(*choices)}
    return [list(bundle) for bundle in sorted(bundles)]


def evaluate(requirements, *, selected_fragment_ids, allowed_fragment_ids):
    allowed = _unique_ids(allowed_fragment_ids, name="allowed fragments")
    selected = _unique_ids(selected_fragment_ids, name="selected fragments", allowed=allowed)
    if not isinstance(requirements, list):
        raise ValueError("Requirements must be a list")
    result = []
    seen = set()
    for requirement in requirements:
        if not isinstance(requirement, dict) or set(requirement) != {"id", "kind", "complete_support_bundles"}:
            raise ValueError("Requirement fields must match the frozen contract")
        identity = requirement["id"]
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("Requirement IDs must be nonempty and unique")
        if not isinstance(requirement["kind"], str) or not requirement["kind"]:
            raise ValueError("Requirement kind is required")
        seen.add(identity)
        bundles = requirement["complete_support_bundles"]
        if not isinstance(bundles, list):
            raise ValueError("A requirement needs complete support bundles")
        matched = []
        missing = []
        for index, bundle in enumerate(bundles):
            required = _unique_ids(bundle, name="complete bundle", allowed=allowed)
            if not required:
                raise ValueError("An empty bundle cannot certify a requirement")
            absent = sorted(required - selected)
            if not absent:
                matched.append(index)
            missing.append(absent)
        result.append({
            "id": identity, "kind": requirement["kind"], "covered": bool(matched),
            "matched_complete_bundle_indexes": matched,
            "missing_ids_per_complete_bundle": missing,
        })
    return result


def run_controls(evaluator=evaluate):
    allowed = ["F054", "F055", "F060", "F061", "F999"]
    rows = []
    def check(name, requirements, selected, expected):
        observed = evaluator(requirements, selected_fragment_ids=selected, allowed_fragment_ids=allowed)
        assert [r["covered"] for r in observed] == expected
        rows.append({"name": name, "PASS": True})
    compound = [{"id": "compound", "kind": "claim_support", "complete_support_bundles": [["F054", "F055"]]}]
    check("compound missing F055 fails", compound, ["F054"], [False])
    check("compound missing F054 fails", compound, ["F055"], [False])
    check("compound both fragments pass", compound, ["F054", "F055"], [True])
    check("available but unselected fragments do not count", compound, ["F999"], [False])
    alternatives = [{"id": "alternatives", "kind": "claim_support", "complete_support_bundles": [["F054", "F055"], ["F060"]]}]
    check("alternative complete bundle passes", alternatives, ["F060"], [True])
    check("incomplete alternative fails", alternatives, ["F054"], [False])
    bundles = flatten_groups([[["F054", "F055"], ["F060"]], [["F061"]]], allowed_fragment_ids=allowed)
    contributions = [{"id": "citation_contributions", "kind": "claim_support", "complete_support_bundles": bundles}]
    check("all actual citation contributors required", contributions, ["F060"], [False])
    check("every actual citation contributor present", contributions, ["F060", "F061"], [True])
    for name, kwargs in [
        ("unknown selected fragment rejected", {"selected_fragment_ids": ["UNKNOWN"]}),
        ("duplicate selected fragments rejected", {"selected_fragment_ids": ["F054", "F054"]}),
        ("unknown required fragment rejected", {"requirements": [{"id": "x", "kind": "claim_support", "complete_support_bundles": [["UNKNOWN"]]}]}),
        ("duplicate required fragments rejected", {"requirements": [{"id": "x", "kind": "claim_support", "complete_support_bundles": [["F054", "F054"]]}]}),
        ("empty bundle rejected", {"requirements": [{"id": "x", "kind": "claim_support", "complete_support_bundles": [[]]}]}),
        ("duplicate requirement IDs rejected", {"requirements": compound + compound}),
    ]:
        inputs = {"requirements": compound, "selected_fragment_ids": [], "allowed_fragment_ids": allowed} | kwargs
        try:
            evaluator(**inputs)
        except ValueError:
            rows.append({"name": name, "PASS": True})
        else:
            raise AssertionError(name)
    assert len(rows) == 14
    return rows
