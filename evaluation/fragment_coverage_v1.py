"""Availability of declared fragment-support bundles; not an entailment judge."""

from collections import Counter

VERSION = "declared_fragment_bundle_coverage_v1"


def _ids(values, name, *, allow_empty=True):
    if not isinstance(values, (list, tuple, set, frozenset)):
        raise ValueError(f"{name} must be an explicit collection of fragment IDs")
    items = list(values)
    if not allow_empty and not items:
        raise ValueError(f"{name} cannot be empty")
    if any(not isinstance(value, str) or not value or value != value.strip() for value in items):
        raise ValueError(f"{name} requires exact nonblank string identities")
    if len(set(items)) != len(items):
        raise ValueError(f"{name} contains duplicate identities")
    return items


def measure_fragment_coverage(selected_fragment_ids, requirements, *, known_fragment_ids):
    """A bundle is an AND; bundles within one requirement are alternatives.

    The caller supplies reviewed support labels. This function checks only their
    availability in the selected subset. It cannot determine whether the labels
    are scientifically correct, whether text was truncated, or whether a model
    used those passages. No model check, relevance gold or publication gate is
    implied by a covered row. Empty alternatives explicitly mean no complete
    support bundle was declared and remain uncovered.
    """
    known = set(_ids(known_fragment_ids, "known_fragment_ids"))
    selected_items = _ids(selected_fragment_ids, "selected_fragment_ids")
    selected = set(selected_items)
    if not selected <= known:
        raise ValueError("Selected fragment IDs must belong to the declared frozen pool")
    if not isinstance(requirements, (list, tuple)):
        raise ValueError("Requirements must be an explicit sequence")
    rows, seen = [], set()
    for requirement in requirements:
        if not isinstance(requirement, dict):
            raise ValueError("Each requirement must be an object")
        identifier, kind = requirement.get("id"), requirement.get("kind")
        if any(
            not isinstance(value, str) or not value or value != value.strip()
            for value in (identifier, kind)
        ):
            raise ValueError("Requirement ID and kind must be exact nonblank strings")
        if identifier in seen:
            raise ValueError("Requirement IDs must be unique")
        seen.add(identifier)
        alternatives = requirement.get("complete_support_bundles")
        if not isinstance(alternatives, (list, tuple)):
            raise ValueError("Complete support bundles must be an explicit sequence")
        bundles, bundle_keys = [], set()
        for alternative in alternatives:
            bundle = _ids(alternative, "complete support bundle", allow_empty=False)
            if not set(bundle) <= known:
                raise ValueError("Support bundle IDs must belong to the declared frozen pool")
            key = frozenset(bundle)
            if key in bundle_keys:
                raise ValueError("Duplicate alternative support bundles are ambiguous")
            bundle_keys.add(key)
            bundles.append(bundle)
        complete = [bundle for bundle in bundles if set(bundle) <= selected]
        rows.append(
            {
                "id": identifier,
                "kind": kind,
                "covered": bool(complete),
                "complete_available_bundles": complete,
                "missing_fragment_ids_by_alternative": [
                    [fragment for fragment in bundle if fragment not in selected]
                    for bundle in bundles
                ],
                "no_complete_support_declared": not bundles,
            }
        )
    total_by_kind = Counter(row["kind"] for row in rows)
    covered_by_kind = Counter(row["kind"] for row in rows if row["covered"])
    summary = {
        kind: {
            "covered": covered_by_kind[kind],
            "total": total,
            "fraction": covered_by_kind[kind] / total,
        }
        for kind, total in sorted(total_by_kind.items())
    }
    count = sum(row["covered"] for row in rows)
    return {
        "version": VERSION,
        "selected_fragment_ids": selected_items,
        "selected_fragment_count": len(selected),
        "known_fragment_count": len(known),
        "requirements": rows,
        "covered": count,
        "total": len(rows),
        "fraction": count / len(rows) if rows else None,
        "by_kind": summary,
        "interpretation": "Availability of caller-declared complete fragment bundles only",
        "source_entailment_or_model_accuracy_judged": False,
        "human_gold_or_publication_gate": False,
    }
