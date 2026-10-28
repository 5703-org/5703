"""Content and physical-span comparisons; processing UUID changes are not edits."""

from collections import defaultdict
import hashlib
import json


def text_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def quality_rows(units):
    return [
        {
            **unit,
            "raw_hash": text_hash(unit["raw_text"]),
            "cleaned_hash": text_hash(unit["cleaned_text"]),
            "raw_characters": len(unit["raw_text"]),
            "cleaned_characters": len(unit["cleaned_text"]),
            "text_changed": unit["raw_text"] != unit["cleaned_text"],
        }
        for unit in sorted(units, key=lambda unit: (unit["sequence"], unit["id"]))
    ]


def compare_processing(before_units, after_units, before_chunks, after_chunks):
    def unit_value(unit):
        return {
            key: unit[key]
            for key in (
                "id",
                "sequence",
                "page",
                "section",
                "quality",
                "raw_hash",
                "cleaned_hash",
                "issues",
            )
        }

    before_by_location = {(unit["page"], unit["sequence"]): unit for unit in before_units}
    after_by_location = {(unit["page"], unit["sequence"]): unit for unit in after_units}
    unit_changes = {"unchanged": [], "changed": [], "added": [], "removed": []}
    for location in sorted(set(before_by_location) | set(after_by_location)):
        before, after = before_by_location.get(location), after_by_location.get(location)
        if before is None or after is None:
            unit_changes["added" if before is None else "removed"].append(
                unit_value(after or before)
            )
        else:
            fields = [
                key
                for key in ("section", "quality", "raw_hash", "cleaned_hash", "issues")
                if before[key] != after[key]
            ]
            unit_changes["changed" if fields else "unchanged"].append(
                {"before": unit_value(before), "after": unit_value(after), "changed_fields": fields}
            )

    def chunk_values(chunks, units):
        lookup = {unit["id"]: unit for unit in units}
        values = []
        for chunk in chunks:
            spans = []
            for span in chunk["spans"]:
                unit = lookup[span["unit_id"]]
                spans.append(
                    {
                        "page": unit["page"],
                        "unit_sequence": unit["sequence"],
                        "raw_hash": unit["raw_hash"],
                        "cleaned_hash": unit["cleaned_hash"],
                        "start": span["start"],
                        "end": span["end"],
                    }
                )
            values.append(
                {
                    "id": chunk["id"],
                    "text_hash": chunk["text_hash"],
                    "section": chunk["section"],
                    "pages": chunk["pages"],
                    "spans": spans,
                }
            )
        return sorted(values, key=lambda value: value["id"])

    before = chunk_values(before_chunks, before_units)
    after = chunk_values(after_chunks, after_units)

    def identity(value):
        return json.dumps(
            {key: value[key] for key in ("text_hash", "section", "pages", "spans")}, sort_keys=True
        )

    by_identity = defaultdict(list)
    for value in after:
        by_identity[identity(value)].append(value)
    unchanged, remaining_before, paired_after = [], [], set()
    for value in before:
        matches = by_identity[identity(value)]
        if matches:
            other = matches.pop(0)
            paired_after.add(other["id"])
            unchanged.append({"before": value, "after": other})
        else:
            remaining_before.append(value)
    remaining_after = [value for value in after if value["id"] not in paired_after]
    # Match changed boundaries by overlap in the same source unit. If cleaning
    # changed, character offsets are not directly comparable; report that whole
    # unit as changed rather than pretending an exact offset alignment survived.
    inverted = defaultdict(list)
    for value in remaining_after:
        for span in value["spans"]:
            inverted[(span["page"], span["unit_sequence"])].append((value["id"], span))
    links = defaultdict(set)
    for value in remaining_before:
        for span in value["spans"]:
            for other_id, other in inverted[(span["page"], span["unit_sequence"])]:
                same_cleaned = span["cleaned_hash"] == other["cleaned_hash"]
                if not same_cleaned or max(span["start"], other["start"]) < min(
                    span["end"], other["end"]
                ):
                    left, right = ("before", value["id"]), ("after", other_id)
                    links[left].add(right)
                    links[right].add(left)
    lookup = {("before", value["id"]): value for value in remaining_before}
    lookup.update({("after", value["id"]): value for value in remaining_after})
    changed, visited = [], set()
    for node in sorted(links):
        if node in visited:
            continue
        pending, component = [node], set()
        while pending:
            current = pending.pop()
            if current in component:
                continue
            component.add(current)
            pending.extend(links[current] - component)
        visited.update(component)
        group = {
            side: [lookup[key] for key in sorted(component) if key[0] == side]
            for side in ("before", "after")
        }
        changed.append(
            {
                **group,
                "reason": "source_unit_or_span_overlap",
                "text_changed": sorted(value["text_hash"] for value in group["before"])
                != sorted(value["text_hash"] for value in group["after"]),
                "requires_qrel_review": True,
            }
        )
    chunk_changes = {
        "unchanged": unchanged,
        "changed": changed,
        "added": [value for value in remaining_after if ("after", value["id"]) not in visited],
        "removed": [value for value in remaining_before if ("before", value["id"]) not in visited],
    }
    return {
        "source_units": unit_changes,
        "chunks": chunk_changes,
        "counts": {
            name: {category: len(rows) for category, rows in groups.items()}
            for name, groups in (("source_units", unit_changes), ("chunks", chunk_changes))
        },
        "qrel_policy": "Unchanged exact text and source spans can be mapped; changed groups require review or reannotation. No relevance label is transferred automatically.",
    }
