"""Create the current nine English reports from reconciled, hash-bound results.

The retained report library supplies validation and document layout. This file
authors the current narrative and paths. Creation needs the bundled document
runtime; the caller performs the artifact marker and every-page visual review.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LIBRARY_PATH = HERE.parent / "week08-enhancement/build_reports.py"
spec = importlib.util.spec_from_file_location("retained_report_library", LIBRARY_PATH)
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)
library.SCHEMA = "week08_memory_v2_report_data_v1"
p, h = library.p, library.h


def build_content(data, owners, evidence):
    overall = [p("CS 30 1 | Week 8 | " + data["as_of"]), h("Project outcome")]
    overall.extend(p(value) for value in data["summary"])
    overall += [h("Implemented workflow")]
    overall.extend(p(value) for value in data["implementation"])
    overall += [h("Experimental method")]
    overall.extend(p(value) for value in data["version_notes"] + data["method_notes"])
    overall += [h("Automatic results")]
    for block in library.study_blocks(data["studies"]):
        if block["type"] == "table" and block["headers"] == ["Metric", "Value", "Scope"]:
            scopes = list(dict.fromkeys(row[2] for row in block["rows"]))
            overall.append(
                {
                    **block,
                    "headers": ["Metric", "Result"],
                    "widths": [2, 5],
                    "rows": [row[:2] for row in block["rows"]],
                }
            )
            overall.extend(p(scope) for scope in scopes)
        else:
            overall.append(block)
    overall += [h("Calls and cost")]
    rows = []
    for row in data["costs"]["rows"]:
        shown = lambda value: "Unknown" if value is None else f"{value:,}"
        amount = (
            "Unknown" if row["amount"] is None else f"{row['amount']} {data['costs']['currency']}"
        )
        rows.append(
            [
                row["purpose"],
                shown(row["calls"]),
                shown(row["input_tokens"]),
                shown(row["output_tokens"]),
                amount,
            ]
        )
    overall.append(
        {
            "type": "table",
            "headers": ["Purpose", "Calls", "Input tokens", "Output tokens", "Estimate"],
            "rows": rows,
            "widths": [2.05, 0.65, 1.4, 1.35, 1.55],
        }
    )
    for row in data["costs"]["rows"]:
        overall.append(p(row["purpose"] + ". " + row["basis"]))
    overall.extend(p(value) for value in data["costs"]["limitations"])
    overall += [h("Retained failures")]
    for failure in data["failures"]:
        overall.append(
            p(
                f"{failure['label']}. {failure['observed']} {failure['disposition']} "
                f"Evidence IDs: {', '.join(failure['evidence_refs'])}."
            )
        )
    human = data["human_review"]
    overall += [
        h("Independent human review"),
        p(
            f"Completed ratings: {human['completed_ratings']}. "
            f"Independent reviewers with imported ratings: {human['independent_reviewers']}."
        ),
    ]
    overall.extend(p(value) for value in human["findings"])
    overall += library.bullets(human["instructions"])
    overall += [h("Operation and delivery")]
    for row in data["operations"]:
        overall.append(
            p(f"{row['label']}. {row['instruction']} Verified scope: {row['verification_scope']}.")
        )
    overall.extend(p(value) for value in data["delivery"]["findings"])
    overall += [h("Limitations and Week 9 goals")]
    overall.extend(p(value) for value in data["limitations"])
    overall += library.bullets(data["week9_actions"])
    overall += [h("Responsibilities"), p(data["actual_executor"])]
    overall.append(
        {
            "type": "table",
            "headers": ["Member", "Accountable domain"],
            "rows": [[owner["name"], owner["domain"]] for owner in owners["members"]],
            "widths": [2, 5],
        }
    )
    overall += [
        h("Evidence references"),
        p(
            "Paths refer to public records in the project. Each hash identifies the exact record used here."
        ),
    ]
    overall += library.evidence_blocks(list(evidence), evidence)
    reports = [
        {
            "filename": "Week08_Overall_Report",
            "title": "Week 8 Memory and Answer Reliability Report",
            "blocks": overall,
        }
    ]
    for owner in owners["members"]:
        member = data["members"][owner["slug"]]
        blocks = [
            p(owner["name"] + " | " + owner["domain"] + " | " + data["as_of"]),
            h("Week 8 contribution"),
            p(owner["outcome"]),
            p("Original task allocation: " + ", ".join(owner["task_ids"]) + "."),
            h("Completed implementation"),
        ]
        blocks.extend(p(value) for value in owner["implementation"])
        blocks += [h("Interfaces and operation"), p(owner["dependencies"])]
        blocks += library.bullets(owner["workflow"])
        blocks += [h("Verification and findings")]
        blocks.extend(p(value) for value in member["findings"])
        selected = [s for s in data["studies"] if s["id"] in member["study_ids"]]
        if selected:
            blocks.append(
                {
                    "type": "table",
                    "headers": ["Study", "Recorded", "Planned"],
                    "rows": [
                        [s["label"], str(s["accounted"]), str(s["planned"])] for s in selected
                    ],
                    "widths": [4.4, 1.3, 1.3],
                }
            )
        blocks += [h("Current limits"), p(owner["limits"])]
        blocks.extend(p(value) for value in member["remaining"])
        blocks += [h("Week 9 goals")] + library.bullets(owner["week9"])
        blocks += [
            h("Code and evidence"),
            p("Module paths: " + "; ".join(owner["files"]) + "."),
            p(data["actual_executor"]),
        ]
        blocks += library.evidence_blocks(member["evidence_refs"], evidence)
        reports.append(
            {
                "filename": f"members/{owner['slug']}/Week08_Report",
                "title": "Week 8 Work Report",
                "blocks": blocks,
            }
        )
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--root", default=ROOT, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    owners = json.loads((HERE / "ownership.json").read_text(encoding="utf-8"))
    library.strings(data["implementation"], "implemented workflow")
    evidence = library.validate(data, owners, args.root)
    reports = build_content(data, owners, evidence)
    if not args.create:
        print(
            json.dumps(
                {
                    "status": "validated_only",
                    "reports": len(reports),
                    "words": {r["filename"]: len(library.markdown(r).split()) for r in reports},
                }
            )
        )
        return
    library.require(
        args.output is not None and not args.output.exists(), "Use a new output directory"
    )
    library.require(
        "codex-primary-runtime" in Path(sys.executable).as_posix(), "Use bundled document runtime"
    )
    args.output.mkdir(parents=True, exist_ok=False)
    files = []
    for report in reports:
        for extension, content in (
            (".md", library.markdown(report).encode("utf-8")),
            (".docx", library.document_bytes(report, data)),
        ):
            path = args.output / (report["filename"] + extension)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(content)
            files.append(
                {
                    "path": path.relative_to(args.output).as_posix(),
                    "bytes": len(content),
                    "sha256": sha256(content).hexdigest(),
                }
            )
    manifest = {
        "schema": "week08_memory_v2_reports_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": data["checkpoint"],
        "input_sha256": library.digest(args.data),
        "builder_sha256": library.digest(__file__),
        "library_sha256": library.digest(LIBRARY_PATH),
        "ownership_sha256": library.digest(HERE / "ownership.json"),
        "docx_count": 9,
        "markdown_count": 9,
        "files": files,
        "visual_qa": "pending_render_and_every_page_inspection",
        "artifact_marker": "caller_owned",
    }
    with (args.output / "report-build.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps({"status": "created_requires_visual_qa", "docx": 9, "output": str(args.output)})
    )


if __name__ == "__main__":
    main()
