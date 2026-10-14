"""Frozen, paired Week 9 memory-selection experiment.

The previous arm executes the preserved v2 query-conditioned reader. The
candidate arm executes the current v3 rules-only default. Both are real product
selectors; the rejected semantic supplement is deliberately outside this study.
Selection is measured independently of whether an eventual answer applies a
preference. Private authored cases and labels must live outside deliverables.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import random
from typing import Any

from generation.token_counting import TokenCounter
from generation.types import ModelConfig
from personalisation import memory_v2, memory_v3


VERSION = "week09_memory_paired_selection_v1"
ARMS = ("previous_v2", "candidate_v3_rules")
SOURCE_FILES = (
    Path("evaluation/week09_continuation/memory_formal.py"),
    Path("personalisation/memory_v2.py"),
    Path("personalisation/memory_v3.py"),
    Path("personalisation/compiler.py"),
)
SPLITS = ("pilot", "reserved")
TOKENIZER_DIR = Path(
    "artifacts/huggingface/deepseek-v4-flash-0731-tokenizer/"
    "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
)
TOKENIZER_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"


@lru_cache(maxsize=1)
def _counter() -> TokenCounter:
    config = ModelConfig(
        provider="openai_compatible",
        model="deepseek-flash",
        tokenizer_provider="huggingface",
        tokenizer_name="deepseek-ai/DeepSeek-V4-Flash-0731",
        tokenizer_revision=TOKENIZER_REVISION,
        tokenizer_local_path=str(TOKENIZER_DIR.resolve()),
        token_count_fallback="error",
    )
    counter = TokenCounter(config)
    if counter.metadata.get("is_estimate") is not False:
        raise ValueError("The frozen local tokenizer was not loaded exactly")
    return counter


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_once(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical(value))


def prior_groups(paths: tuple[Path, ...]) -> tuple[set[str], dict[str, str]]:
    groups: set[str] = set()
    hashes: dict[str, str] = {}
    for path in paths:
        raw = path.read_bytes()
        document = json.loads(raw)
        cases = document.get("cases")
        if not isinstance(cases, list):
            raise ValueError(f"Prior catalogue has no cases: {path}")
        groups.update(
            str(item["concept_group"] if "concept_group" in item else item["group"])
            for item in cases
        )
        hashes[str(path.resolve())] = digest(raw)
    return groups, hashes


def validate_catalogue(catalogue: dict, *, excluded_groups: set[str]) -> dict:
    if catalogue.get("schema") != VERSION or catalogue.get("label_provenance") != "program_derived":
        raise ValueError("The paired study requires program-derived, versioned private labels")
    cases = catalogue.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("A nonempty private case catalogue is required")
    identities: set[str] = set()
    groups: dict[str, str] = {}
    for case in cases:
        identity, group, split = (case.get(key) for key in ("id", "concept_group", "split"))
        if (
            not all(isinstance(value, str) and value for value in (identity, group))
            or split not in SPLITS
        ):
            raise ValueError("Every case needs an ID, concept group and declared split")
        if identity in identities or group in excluded_groups:
            raise ValueError("Duplicate identity or overlap with a prior concept group")
        identities.add(identity)
        if group in groups and groups[group] != split:
            raise ValueError("A concept group cannot cross pilot and reserved splits")
        groups[group] = split
        question, entries = case.get("question"), case.get("entries")
        if (
            not isinstance(question, str)
            or not question.strip()
            or not isinstance(entries, list)
            or not entries
        ):
            raise ValueError("A case needs a nonempty question and typed memory entries")
        entry_ids: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict) or not all(
                isinstance(entry.get(key), str) and entry[key]
                for key in ("id", "content", "scope", "field_key", "source_message_id")
            ):
                raise ValueError("Typed memory identity, content, scope and source are required")
            if entry["id"] in entry_ids or entry.get("field_key") not in memory_v2.FIELDS:
                raise ValueError("Duplicate memory ID or unknown memory field")
            if entry.get("category") != memory_v2.FIELDS[entry["field_key"]]:
                raise ValueError("Memory category and field disagree")
            if type(entry.get("version")) is not int or entry["version"] < 1:
                raise ValueError("Memory version must be positive")
            if entry.get("verification") not in {"user_explicit", "unsupported"}:
                raise ValueError(
                    "Only explicit or explicitly unsupported fixture records are allowed"
                )
            if len(canonical(entry)) > 700:
                raise ValueError("The fixture must avoid memory-budget truncation")
            entry_ids.add(entry["id"])
        expected, forbidden = case.get("expected_memory_ids"), case.get("forbidden_memory_ids")
        if not isinstance(expected, list) or not isinstance(forbidden, list):
            raise ValueError("Selection labels must be explicit lists")
        if len(set(expected)) != len(expected) or len(set(forbidden)) != len(forbidden):
            raise ValueError("Selection label IDs must be unique")
        if set(expected) & set(forbidden) or set(expected) | set(forbidden) != entry_ids:
            raise ValueError("Expected and forbidden labels must partition memory entries")
        if not isinstance(case.get("profile"), dict) or not isinstance(
            case.get("context", {}), dict
        ):
            raise ValueError("Profile and optional prior context must be objects")
        if any(
            not isinstance(message, dict)
            or message.get("role") not in {"user", "assistant"}
            or not isinstance(message.get("content"), str)
            for message in case.get("context", {}).get("recent_messages", [])
        ):
            raise ValueError("Prior conversation messages are invalid")
    if set(groups.values()) != set(SPLITS):
        raise ValueError("Both pilot and reserved concept groups are required")
    return {
        "case_count": len(cases),
        "group_count": len(groups),
        "splits": {split: sum(case["split"] == split for case in cases) for split in SPLITS},
        "groups": {
            split: sorted(group for group, value in groups.items() if value == split)
            for split in SPLITS
        },
    }


def freeze(
    catalogue_path: Path, output: Path, *, prior_paths: tuple[Path, ...], seed: int = 57030930
) -> dict:
    if output.exists():
        raise ValueError("Use a new private study directory; prior receipts are immutable")
    prior, prior_hashes = prior_groups(prior_paths)
    raw = catalogue_path.read_bytes()
    catalogue = json.loads(raw)
    inventory = validate_catalogue(catalogue, excluded_groups=prior)
    tokenizer_manifest = TOKENIZER_DIR / "SOURCE_MANIFEST.json"
    if not tokenizer_manifest.is_file():
        raise ValueError("The pinned local DeepSeek tokenizer manifest is unavailable")
    if _counter().metadata.get("revision") != TOKENIZER_REVISION:
        raise ValueError("The active local tokenizer revision changed")
    source_hashes = {str(path): digest(path.read_bytes()) for path in SOURCE_FILES}
    schedule = [
        {
            "id": f"{case['id']}::{arm}",
            "case_id": case["id"],
            "concept_group": case["concept_group"],
            "split": case["split"],
            "arm": arm,
        }
        for case in catalogue["cases"]
        for arm in ARMS
    ]
    random.Random(seed).shuffle(schedule)
    tasks = {
        case["id"]: {
            key: value
            for key, value in case.items()
            if key not in {"expected_memory_ids", "forbidden_memory_ids"}
        }
        for case in catalogue["cases"]
    }
    labels = {
        case["id"]: {
            "expected_memory_ids": case["expected_memory_ids"],
            "forbidden_memory_ids": case["forbidden_memory_ids"],
            "provenance": "program_derived",
        }
        for case in catalogue["cases"]
    }
    output.mkdir(parents=True)
    write_once(output / "private-catalogue.json", catalogue)
    write_once(output / "private-labels.json", labels)
    manifest = {
        "schema": VERSION + "_manifest",
        "catalogue_sha256": digest(raw),
        "inventory": inventory,
        "prior_catalogue_sha256": prior_hashes,
        "source_sha256": source_hashes,
        "label_provenance": "program_derived",
        "schedule": schedule,
        "tasks": tasks,
        "arm_policy": {
            "previous_v2": memory_v2.SELECTOR_VERSION,
            "candidate_v3_rules": memory_v3.freeze_policy(),
        },
        "seed": seed,
        "selection_token_counting": _counter().metadata,
        "tokenizer_manifest_path": str(tokenizer_manifest.resolve()),
        "tokenizer_manifest_sha256": digest(tokenizer_manifest.read_bytes()),
        "answer_application": "not_inferred_from_selection",
    }
    write_once(output / "manifest.json", manifest)
    write_once(
        output / "freeze-receipt.json",
        {
            "manifest_sha256": digest((output / "manifest.json").read_bytes()),
            "private_labels_sha256": digest((output / "private-labels.json").read_bytes()),
            "private_catalogue_sha256": digest((output / "private-catalogue.json").read_bytes()),
        },
    )
    return {"manifest_sha256": digest((output / "manifest.json").read_bytes()), **inventory}


def load_frozen(output: Path) -> tuple[dict, dict]:
    receipt = read(output / "freeze-receipt.json")
    for file, key in (
        ("manifest.json", "manifest_sha256"),
        ("private-labels.json", "private_labels_sha256"),
        ("private-catalogue.json", "private_catalogue_sha256"),
    ):
        if digest((output / file).read_bytes()) != receipt[key]:
            raise ValueError("Frozen memory study input changed")
    manifest = read(output / "manifest.json")
    if manifest.get("schema") != VERSION + "_manifest":
        raise ValueError("Unexpected memory study version")
    if any(
        digest(Path(path).read_bytes()) != value
        for path, value in manifest["source_sha256"].items()
    ):
        raise ValueError("The candidate or previous selector source changed after freeze")
    if any(
        digest(Path(path).read_bytes()) != value
        for path, value in manifest["prior_catalogue_sha256"].items()
    ):
        raise ValueError("A prior excluded catalogue changed after freeze")
    if (
        digest(Path(manifest["tokenizer_manifest_path"]).read_bytes())
        != manifest["tokenizer_manifest_sha256"]
        or _counter().metadata != manifest["selection_token_counting"]
    ):
        raise ValueError("The pinned memory-study tokenizer identity changed")
    return manifest, read(output / "private-labels.json")


def select(task: dict, arm: str) -> dict:
    entries = copy.deepcopy(task["entries"])
    question = task["question"]
    profile = copy.deepcopy(task["profile"])
    context = copy.deepcopy(task.get("context", {}))
    if arm == "previous_v2":
        state = memory_v2.learner_state(entries, question, profile, context, counter=_counter())
        selector_version = memory_v2.SELECTOR_VERSION
        semantic_calls = 0
    elif arm == "candidate_v3_rules":
        result = memory_v3.select(
            entries,
            question,
            profile,
            context,
            policy=memory_v3.freeze_policy(),
            counter=_counter(),
        )
        state = result.state
        selector_version = memory_v3.SELECTOR_VERSION
        semantic_calls = 0
        if result.trace["status"] != "disabled_rules_only":
            raise ValueError("The candidate unexpectedly enabled an uncalibrated semantic selector")
    else:
        raise ValueError("Unknown frozen memory arm")
    return {
        "selector_version": selector_version,
        "selected_memory_ids": [entry["id"] for entry in state["entries"]],
        "field_sources": [field["source"] for field in state["fields"]],
        "excluded_reasons": [entry["reason"] for entry in state["excluded"]],
        "memory_state_sha256": digest(canonical(state)),
        "memory_state_token_count": state["token_count"],
        "memory_state_token_limit": state["token_limit"],
        "semantic_model_calls": semantic_calls,
        "answer_model_calls": 0,
        "answer_preference_application": None,
    }


def run(output: Path, *, split: str) -> dict:
    if split not in SPLITS:
        raise ValueError("Unknown split")
    manifest, _ = load_frozen(output)
    if split == "reserved":
        decision = read(output / "pilot-decision.json")
        if decision.get("ready_for_reserved") is not True or decision.get(
            "manifest_sha256"
        ) != digest((output / "manifest.json").read_bytes()):
            raise ValueError("The frozen pilot execution gate did not pass")
    expected = [row for row in manifest["schedule"] if row["split"] == split]
    written = 0
    for item in expected:
        name = item["id"].replace("::", "--") + ".json"
        outcome = output / "outcomes" / name
        reservation = output / "reservations" / name
        if outcome.exists():
            continue
        if reservation.exists():
            raise ValueError("An interrupted reservation requires independent reconciliation")
        task = manifest["tasks"][item["case_id"]]
        reserved = {
            "schedule_id": item["id"],
            "task_sha256": digest(canonical(task)),
            "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_once(reservation, reserved)
        try:
            observation = select(task, item["arm"])
            terminal = {
                **reserved,
                **observation,
                "state": "diagnostic_observation",
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            terminal = {
                **reserved,
                "state": "execution_failure",
                "error_type": type(exc).__name__,
                "selected_memory_ids": None,
                "answer_preference_application": None,
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        write_once(outcome, terminal)
        written += 1
    return {
        "split": split,
        "planned": len(expected),
        "new_terminal": written,
        "total_terminal": sum(
            (output / "outcomes" / (row["id"].replace("::", "--") + ".json")).is_file()
            for row in expected
        ),
    }


def _partition_summary(manifest: dict, labels: dict, output: Path, split: str, arm: str) -> dict:
    rows = [row for row in manifest["schedule"] if row["split"] == split and row["arm"] == arm]
    result: dict[str, Any] = {
        "planned": len(rows),
        "terminal": 0,
        "correct_selection": 0,
        "false_selection": 0,
        "omitted_expected": 0,
        "correct_exclusion": 0,
        "exact_case_match": 0,
        "execution_failure": 0,
    }
    for item in rows:
        path = output / "outcomes" / (item["id"].replace("::", "--") + ".json")
        if not path.is_file():
            continue
        observed = read(path)
        if observed.get("schedule_id") != item["id"] or observed.get("task_sha256") != digest(
            canonical(manifest["tasks"][item["case_id"]])
        ):
            raise ValueError("A terminal memory outcome differs from its frozen task")
        result["terminal"] += 1
        if observed["state"] != "diagnostic_observation":
            result["execution_failure"] += 1
            continue
        expected = set(labels[item["case_id"]]["expected_memory_ids"])
        forbidden = set(labels[item["case_id"]]["forbidden_memory_ids"])
        selected = set(observed["selected_memory_ids"])
        result["correct_selection"] += len(selected & expected)
        result["false_selection"] += len(selected & forbidden)
        result["omitted_expected"] += len(expected - selected)
        result["correct_exclusion"] += len(forbidden - selected)
        result["exact_case_match"] += selected == expected
    result["unstarted"] = result["planned"] - result["terminal"]
    result["label_provenance"] = "program_derived"
    result["actual_answer_application_scored"] = 0
    return result


def summarize(output: Path) -> dict:
    manifest, labels = load_frozen(output)
    results = {
        split: {arm: _partition_summary(manifest, labels, output, split, arm) for arm in ARMS}
        for split in SPLITS
    }
    paired = {}
    for split in SPLITS:
        pairs = [item for item in manifest["tasks"].values() if item["split"] == split]
        improved = worsened = unchanged = incomplete = 0
        for task in pairs:
            observations: dict[str, dict | None] = {}
            for arm in ARMS:
                path = output / "outcomes" / (task["id"] + "--" + arm + ".json")
                observations[arm] = read(path) if path.is_file() else None
            if any(
                row is None or row["state"] != "diagnostic_observation"
                for row in observations.values()
            ):
                incomplete += 1
                continue
            expected = set(labels[task["id"]]["expected_memory_ids"])
            previous_row, candidate_row = observations[ARMS[0]], observations[ARMS[1]]
            assert previous_row is not None and candidate_row is not None
            previous = set(previous_row["selected_memory_ids"]) == expected
            candidate = set(candidate_row["selected_memory_ids"]) == expected
            improved += candidate and not previous
            worsened += previous and not candidate
            unchanged += previous == candidate
        paired[split] = {
            "improved_exact_selection": improved,
            "worsened_exact_selection": worsened,
            "unchanged_exact_selection": unchanged,
            "incomplete_pairs": incomplete,
            "planned_pairs": len(pairs),
        }
    return {
        "schema": VERSION + "_summary",
        "manifest_sha256": digest((output / "manifest.json").read_bytes()),
        "inventory": manifest["inventory"],
        "arms": manifest["arm_policy"],
        "selection": results,
        "paired": paired,
        "answer_model_calls": 0,
        "human_ratings": 0,
        "answer_preference_application": None,
        "claim_scope": "Paired product-code selection under program-derived labels; no real answer preference-use score or semantic-policy activation.",
    }


def pilot_decision(output: Path) -> dict:
    manifest, _ = load_frozen(output)
    if (output / "pilot-decision.json").exists():
        raise ValueError("The pilot decision is immutable")
    summary = summarize(output)
    counts = summary["selection"]["pilot"]
    ready = all(
        counts[arm]["terminal"] == counts[arm]["planned"] and counts[arm]["execution_failure"] == 0
        for arm in ARMS
    )
    decision = {
        "schema": VERSION + "_pilot_decision",
        "manifest_sha256": digest((output / "manifest.json").read_bytes()),
        "ready_for_reserved": ready,
        "criterion": "all pilot selector observations terminal and valid; no accuracy threshold tuning",
        "pilot_counts": counts,
        "policy_changed_after_pilot": False,
        "reference_label_provenance": "program_derived",
        "reserved_cases_inspected": False,
    }
    write_once(output / "pilot-decision.json", decision)
    return {
        "ready_for_reserved": ready,
        "pilot_terminal": {arm: counts[arm]["terminal"] for arm in ARMS},
        "planned": {arm: counts[arm]["planned"] for arm in ARMS},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("freeze", "run-pilot", "pilot-decision", "run-reserved", "summarize")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--catalogue", type=Path)
    parser.add_argument("--exclude-prior", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.action == "freeze":
        if args.catalogue is None or not args.exclude_prior:
            parser.error("Freeze requires --catalogue and at least one --exclude-prior")
        value = freeze(args.catalogue, args.output, prior_paths=tuple(args.exclude_prior))
    elif args.action == "run-pilot":
        value = run(args.output, split="pilot")
    elif args.action == "pilot-decision":
        value = pilot_decision(args.output)
    elif args.action == "run-reserved":
        value = run(args.output, split="reserved")
    else:
        value = summarize(args.output)
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
