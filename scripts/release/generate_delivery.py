"""Export owner/week reporting views from the canonical execution ledgers.

The export does not assign work, infer dates, or alter acceptance. Re-run after
ledger reconciliation; --check rejects a stale export without changing files.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "docs/delivery"
INPUTS = (
    "docs/execution/tasks.json",
    "docs/execution/reporting_plan.json",
    "docs/execution/acceptance.json",
)
CENTRAL = (
    "PRD.md",
    "SPEC.md",
    "PLANS.md",
    "HANDOVER.md",
    "docs/foundation/api_contract.md",
    "contracts/openapi.json",
    *INPUTS,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def code(value):
    return "`" + str(value).replace("`", "\\`") + "`"


def recorded(value):
    if value is None:
        return "Not recorded (null)."
    if value == [] or value == {} or value == "":
        return "None recorded."
    if isinstance(value, (list, dict, bool)):
        return code(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return str(value)


def link(page, target, label=None, anchor=""):
    relative = Path(os.path.relpath(ROOT / target, page.parent)).as_posix()
    return f"[{label or target}](<{quote(relative, safe='/.-_')}{anchor}>)"


def path_list(page, values):
    # Missing planned paths remain explicit text, never broken hyperlinks or
    # invented deliverables. Nothing is inferred about their acceptance.
    return (
        ", ".join(
            link(page, item) if (ROOT / item).exists() else f"{code(item)} (path absent)"
            for item in dict.fromkeys(values)
        )
        or "None recorded."
    )


def header(page, title, tasks_document):
    return [
        f"# {title}",
        "",
        "Generated reporting view. The canonical ledgers below remain authoritative; "
        "this file adds no product requirement or acceptance decision.",
        "",
        "Accountable owner and suggested course week are reporting metadata, never "
        "permissions, implementation eligibility, runtime flags or evidence of completion. "
        "Actual executor and recorded dates are shown separately. Cross-references do not "
        "count a task more than once. No calendar dates or completion percentages are inferred.",
        "",
        "Canonical requirements, shared interfaces and evidence: "
        + " · ".join(link(page, item) for item in CENTRAL),
        "",
        "Task-ledger reconciliation timestamp (not a completion date): "
        + recorded(tasks_document.get("reconciled_at")),
        "",
    ]


def task_reference(page, task, *, week=False):
    filename = (
        f"by_week/course-week-{task['reporting']['suggested_course_week']:02d}.md"
        if week
        else f"by_owner/{slug(task['accountable_owner'])}.md"
    )
    return link(page, f"docs/delivery/{filename}", task["task_id"], f"#{task['task_id'].lower()}")


def task_section(page, task, by_id, dependents):
    trace = task.get("implementation_trace") or {}
    upstream = [
        f"{task_reference(page, by_id[item])} — {by_id[item]['accountable_owner']}"
        for item in task["dependencies"]
    ]
    downstream = [
        f"{task_reference(page, by_id[item])} — {by_id[item]['accountable_owner']}"
        for item in dependents[task["task_id"]]
    ]
    rows = [
        f"## {task['task_id']}",
        "",
        task["implementation"],
        "",
        f"- Accountable owner (reporting): {task['accountable_owner']}",
        f"- Actual executor: {recorded(task.get('actual_executor'))}",
        "- Suggested allocation: " + recorded(task.get("reporting")),
        "- Actual start / completion / course week: "
        + " / ".join(
            recorded(task.get(field))
            for field in ("actual_started_at", "actual_completed_at", "actual_course_week")
        ),
        "- Execution checkpoint: " + recorded(task.get("execution_checkpoint")),
        "- Current status: " + code(task["status"]),
        "- Separate implementation / verification / research / human-review states: "
        + " / ".join(
            code(task.get(field))
            for field in (
                "implementation_status",
                "verification_status",
                "research_status",
                "human_review_status",
            )
        ),
        "- Completion claim recorded by the ledger: " + recorded(task.get("completion_claim")),
        "- Exact dependency IDs: " + recorded(task["dependencies"]),
        "- Required dependency artifacts: " + recorded(task.get("artifact_dependencies")),
        "- Upstream collaborators (derived from those dependencies): "
        + ("; ".join(upstream) or "None recorded."),
        "- Downstream collaborators (reverse dependency references): "
        + ("; ".join(downstream) or "None recorded."),
        "- Source files recorded for this implementation: "
        + path_list(page, trace.get("concrete_code_paths", [])),
        "- Changed files recorded by the ledger: " + path_list(page, task.get("changed_files", [])),
        "- Shared entry / interface boundary: "
        + recorded(trace.get("designed_entry"))
        + " / "
        + recorded(trace.get("service_boundary")),
        "- Persisted effect / consumer: "
        + recorded(trace.get("persisted_effect"))
        + " / "
        + recorded(trace.get("consumer")),
        "- Local acceptance clause: " + recorded(task.get("local_acceptance")),
        "- Executed commands recorded by the ledger: " + recorded(task.get("actual_commands")),
        "- Additional legacy command field: " + recorded(task.get("commands_run")),
        "- Check implementations (existence alone is not an executed result): "
        + path_list(page, trace.get("concrete_test_paths", [])),
        "- Recorded current check nodes: " + recorded(task.get("current_test_nodes")),
        "- Acceptance references: "
        + ", ".join(
            link(page, "docs/delivery/acceptance.md", item, f"#{item.lower()}")
            for item in task["acceptance_ids"]
        ),
        "- Actual task evidence: " + path_list(page, task.get("evidence_paths", [])),
        "- Additional current test evidence record: " + recorded(task.get("current_test_evidence")),
        "- Evidence scope: " + recorded(task.get("evidence_scope")),
        "- Current observation: " + recorded(task.get("reconciliation_note")),
        "- Unresolved scope: " + recorded(task.get("remaining_scope")),
        "- Blockers: " + recorded(task.get("blockers")),
        "- Mapping limitation: " + recorded(trace.get("limitation")),
        "",
    ]
    for key in ("handoff_consumers", "handover_actions", "handover_checks", "source_asset_state"):
        if key in task:
            rows.extend([f"{key.replace('_', ' ').capitalize()}: {recorded(task[key])}", ""])
    if task.get("component_statuses"):
        rows.extend(["Recorded component observations:", ""])
        for component in task["component_statuses"]:
            rows.append(
                f"- {component['component']}: {code(component['status'])}. "
                + recorded(component.get("detail"))
            )
            if component.get("evidence_paths"):
                rows.append("  Evidence: " + path_list(page, component["evidence_paths"]))
        rows.append("")
    rows.extend(
        [
            "Historical statuses and source-supported historical facts remain in the "
            + link(page, INPUTS[0], "canonical task record")
            + "; they are not replaced by this export.",
            "",
        ]
    )
    return rows


def render(raw):
    tasks_document, plan, acceptance_document = [json.loads(raw[name]) for name in INPUTS]
    tasks = tasks_document["tasks"]
    by_id = {task["task_id"]: task for task in tasks}
    check_rows = acceptance_document["checks"]
    check_ids = [item["check_id"] for item in check_rows]
    if len(check_rows) != 60 or len(set(check_ids)) != 60:
        raise ValueError("Expected exactly 60 acceptance rows with unique check IDs")
    checks = {item["check_id"]: item for item in check_rows}
    if len(tasks) != 108 or len(by_id) != 108:
        raise ValueError("Expected 108 unique canonical tasks and 60 unique acceptance references")
    dependents = defaultdict(list)
    owner_groups = defaultdict(list)
    week_groups = defaultdict(list)
    for task in tasks:
        if task["status"] not in tasks_document["status_definitions"]:
            raise ValueError(f"Unknown current task status: {task['task_id']}")
        if not set(task["acceptance_ids"]) <= checks.keys():
            raise ValueError(f"Unknown acceptance reference: {task['task_id']}")
        for dependency in task["dependencies"]:
            if dependency not in by_id:
                raise ValueError(f"Unknown dependency: {dependency}")
            dependents[dependency].append(task["task_id"])
        owner_groups[task["accountable_owner"]].append(task)
        week_groups[task["reporting"]["suggested_course_week"]].append(task)
    if set().union(*(set(task["acceptance_ids"]) for task in tasks)) != checks.keys():
        raise ValueError("Every acceptance check must be referenced by at least one task")
    packages = plan["weekly_work_packages"]
    if not set().union(*(set(item["task_ids"]) for item in packages)) <= by_id.keys():
        raise ValueError("Reporting plan references an unknown task")
    output = {}
    primary_groups = {}
    for owner, assigned in sorted(owner_groups.items()):
        name = f"by_owner/{slug(owner)}.md"
        page = DESTINATION / name
        lines = header(page, f"Delivery view: {owner}", tasks_document)
        lines.extend(
            [
                f"This owner view contains {len(assigned)} unique domain tasks. "
                "Shared interfaces remain in the central specifications linked above.",
                "",
                "Task index: " + ", ".join(task_reference(page, task) for task in assigned),
                "",
            ]
        )
        for task in assigned:
            lines.extend(task_section(page, task, by_id, dependents))
        output[name] = "\n".join(lines).encode("utf-8")
        primary_groups[name] = [task["task_id"] for task in assigned]
    for week, assigned in sorted(week_groups.items()):
        name = f"by_week/course-week-{week:02d}.md"
        page = DESTINATION / name
        lines = header(page, f"Delivery view: suggested course week {week}", tasks_document)
        lines.extend(
            [
                f"This primary reporting bucket contains {len(assigned)} unique tasks. "
                "A task's canonical suggested week chooses its one primary bucket. "
                "The planning packages below can mention it in other weeks as a cross-reference; "
                "these references add no completed tasks.",
                "",
                "## Suggested allocation only",
                "",
                plan["schedule_status"],
                "",
                "Week convention: " + plan["week_system"] + ". " + plan["week_13"],
                "",
            ]
        )
        for package in packages:
            if package["course_week"] != week:
                continue
            lines.extend(
                [
                    f"### {package['accountable_owner']} — suggested package",
                    "",
                    package["work"],
                    "",
                    "- Task cross-references: "
                    + ", ".join(task_reference(page, by_id[item]) for item in package["task_ids"]),
                    "- Suggested deliverable paths (not claims of delivery): "
                    + path_list(page, package["deliverables"]),
                    "- Suggested downstream consumers: " + package["downstream_consumers"],
                    "- Planned acceptance description: " + package["acceptance"],
                    "- Planning record status (not actual task status): " + code(package["status"]),
                    "- Planning record actual executor / completed at: "
                    + recorded(package.get("actual_executor"))
                    + " / "
                    + recorded(package.get("actual_completed_at")),
                    "- Planning record actual evidence: "
                    + path_list(page, package.get("actual_evidence", [])),
                    "",
                ]
            )
        lines.extend(
            [
                "## Actual evidence and demonstration material",
                "",
                "The task records below quote the current ledger, independently of the suggested "
                "package. Their actual evidence links are the available demonstration and check "
                "material; an empty or null field stays unrecorded. The export does not create "
                "a meeting, human demonstration or historical completion event.",
                "",
                "## Carry-over and unresolved work",
                "",
                "These are currently recorded unresolved items for this reporting bucket, not "
                "claims that a calendar week elapsed or work was late.",
                "",
            ]
        )
        unresolved = [
            task for task in assigned if task.get("remaining_scope") or task.get("blockers")
        ]
        for task in unresolved:
            lines.append(
                f"- {task_reference(page, task)} ({code(task['status'])}): "
                + recorded(task.get("remaining_scope"))
                + " Blockers: "
                + recorded(task.get("blockers"))
            )
        if not unresolved:
            lines.append("No remaining_scope or blockers are recorded for this primary bucket.")
        lines.append("")
        for task in assigned:
            lines.extend(task_section(page, task, by_id, dependents))
        output[name] = "\n".join(lines).encode("utf-8")
        primary_groups[name] = [task["task_id"] for task in assigned]
    page = DESTINATION / "acceptance.md"
    lines = header(page, "Delivery acceptance references", tasks_document)
    lines.extend(
        [
            "All 60 original check IDs are cross-referenced here once. Expected clauses, current "
            "statuses and actual observations are copied from the canonical acceptance ledger; "
            "this export does not execute or upgrade a check. Historical observations remain "
            "in that ledger.",
            "",
        ]
    )
    for check_id, check in checks.items():
        lines.extend(
            [
                f"## {check_id}",
                "",
                check["expected"],
                "",
                "- Current status: " + code(check["status"]),
                "- Current observation: " + recorded(check.get("actual")),
                "- Task references: "
                + ", ".join(task_reference(page, by_id[item]) for item in check["task_ids"]),
                "- Actual recorded commands: " + recorded(check.get("actual_commands")),
                "- Actual execution timestamp: " + recorded(check.get("executed_at")),
                "- Actual evidence: " + path_list(page, check.get("evidence_paths", [])),
                "- Remaining scope: " + recorded(check.get("remaining_scope")),
                "",
            ]
        )
    output["acceptance.md"] = "\n".join(lines).encode("utf-8")
    page = DESTINATION / "README.md"
    lines = header(page, "Generated delivery views", tasks_document)
    lines.extend(
        [
            "This export implements source section 20.6 (INT-10, CHAT-12, QA-14 and owner "
            "handovers). Eight owner files and seven course-week files each partition the same "
            "108 tasks exactly once. Repeated planning cross-references are not duplicate "
            "completion claims. The shared acceptance view retains all 60 check references.",
            "",
            "Regenerate from the repository root with:",
            "",
            "```text",
            "python -m scripts.release.generate_delivery",
            "python -m scripts.release.generate_delivery --check",
            "```",
            "",
            "Generation only writes this directory. The check mode compares bytes and reports "
            "stale/missing/extra generated files without writing. Regenerate after canonical "
            "ledger changes. The manifest records input and output hashes; the generated files "
            "contain no wall-clock generation timestamp.",
            "",
            "## Owner views",
            "",
        ]
    )
    for owner, assigned in sorted(owner_groups.items()):
        lines.append(
            f"- {link(page, f'docs/delivery/by_owner/{slug(owner)}.md', owner)}: {len(assigned)} tasks"
        )
    lines.extend(["", "## Suggested course-week views", ""])
    for week, assigned in sorted(week_groups.items()):
        lines.append(
            f"- {link(page, f'docs/delivery/by_week/course-week-{week:02d}.md', f'Course week {week}')}: "
            f"{len(assigned)} primary tasks"
        )
    lines.extend(
        [
            "",
            link(page, "docs/delivery/acceptance.md", "All 60 acceptance references"),
            "",
            "## Canonical current-status meanings",
            "",
        ]
    )
    lines.extend(
        f"- {code(key)}: {value}" for key, value in tasks_document["status_definitions"].items()
    )
    lines.extend(
        [
            "",
            "Secondary research/human fields and explicitly labelled planning states are copied "
            "unchanged even where they use a separate vocabulary. Answer-model, scientific, "
            "physical-device and human-review limitations remain those of each cited record.",
            "",
        ]
    )
    output["README.md"] = "\n".join(lines).encode("utf-8")
    for prefix in ("by_owner/", "by_week/"):
        counts = Counter(
            item for name, ids in primary_groups.items() if name.startswith(prefix) for item in ids
        )
        if set(counts) != by_id.keys() or any(count != 1 for count in counts.values()):
            raise ValueError(f"Each grouping must partition all 108 tasks once: {prefix}")
    manifest = {
        "schema": "delivery_views_v1",
        "source_requirement": "CODEX_MASTER_PROMPT_EN_v5.md section 20.6",
        "generator": "scripts/release/generate_delivery.py",
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "input_sha256": {name: digest(raw[name]) for name in INPUTS},
        "task_count": len(tasks),
        "acceptance_count": len(checks),
        "owner_view_count": len(owner_groups),
        "week_view_count": len(week_groups),
        "primary_groups": primary_groups,
        "acceptance_ids": list(checks),
        "output_sha256": {name: digest(data) for name, data in sorted(output.items())},
        "scope": "Reporting-only ledger export; no test execution or completion inference.",
    }
    output["manifest.json"] = json_text(manifest).encode("utf-8")
    return output, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Reject stale output without writing")
    args = parser.parse_args()
    raw = {name: (ROOT / name).read_bytes() for name in INPUTS}
    output, manifest = render(raw)
    existing = {
        path.relative_to(DESTINATION).as_posix()
        for path in DESTINATION.rglob("*")
        if path.is_file()
    }
    extra = existing - output.keys()
    if extra:
        raise SystemExit(
            f"Unexpected delivery files; preserve and review manually: {sorted(extra)}"
        )
    if any((ROOT / name).read_bytes() != data for name, data in raw.items()):
        raise SystemExit("Canonical inputs changed during generation; retry after reconciliation")
    changed = [
        name
        for name, data in output.items()
        if not (DESTINATION / name).exists() or (DESTINATION / name).read_bytes() != data
    ]
    if args.check and changed:
        raise SystemExit(f"Delivery export is stale or missing: {changed}")
    if not args.check:
        for name, data in output.items():
            target = DESTINATION / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    print(
        json_text(
            {
                "passed": True,
                "mode": "check" if args.check else "generate",
                "file_count": len(output),
                "changed_count": len(changed),
                "task_count_per_grouping": manifest["task_count"],
                "owner_views": manifest["owner_view_count"],
                "week_views": manifest["week_view_count"],
                "acceptance_references": manifest["acceptance_count"],
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
