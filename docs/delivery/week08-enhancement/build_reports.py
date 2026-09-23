"""Build nine dated English reports from explicitly supplied public results.

Validation is read-only. Creation requires --create and a new output directory.
The caller runs the document skill artifact marker once before creation, then
renders and visually inspects every page; this builder never claims visual QA.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCHEMA = "week08_enhancement_report_data_v1"
FORBIDDEN = re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,})")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strings(value, name, minimum=1):
    require(isinstance(value, list) and len(value) >= minimum, f"{name}: expected text list")
    for item in value:
        require(isinstance(item, str) and item.strip(), f"{name}: empty text")
        require(
            not re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b", item), f"{name}: unresolved placeholder"
        )
        require(not item.startswith("Replace with "), f"{name}: unfilled template instruction")
        require(not FORBIDDEN.search(item), f"{name}: possible credential material")


def public_path(root, value):
    path = PurePosixPath(value)
    require(
        not path.is_absolute() and ".." not in path.parts and "\\" not in value,
        f"Unsafe relative path: {value}",
    )
    require(path.parts and path.parts[0] in {"docs", "evidence"}, f"Public evidence only: {value}")
    require(
        not any(p.startswith(".") or "private" in p.lower() for p in path.parts),
        f"Private input is not a report reference: {value}",
    )
    resolved = (root / path).resolve()
    require(
        resolved.is_relative_to(root.resolve()) and resolved.is_file(), f"Missing evidence: {value}"
    )
    return resolved


def integer(value, name, nullable=False):
    require(
        (nullable and value is None) or (type(value) is int and value >= 0),
        f"{name}: expected nonnegative integer" + (" or null" if nullable else ""),
    )


def validate(data, owners, root):
    require(
        data.get("schema") == SCHEMA and not data.get("template_only"),
        "Supply final public report data",
    )
    date.fromisoformat(data["as_of"])
    require(re.fullmatch(r"[A-Za-z0-9_-]+", data["checkpoint"]), "Invalid checkpoint name")
    for field in ("summary", "version_notes", "method_notes", "limitations", "week9_actions"):
        strings(data[field], field)
    strings([data["actual_executor"]], "actual_executor")
    require(len(owners["members"]) == 8, "Exactly eight domain owners are required")
    names = {m["slug"] for m in owners["members"]}
    require(
        len(names) == 8 and set(data["members"]) == names,
        "Member set differs from original ownership",
    )
    manifest = json.loads((root / "docs/delivery/manifest.json").read_text(encoding="utf-8"))
    for owner in owners["members"]:
        key = "by_owner/" + owner["name"].lower().replace(" ", "-") + ".md"
        require(
            owner["task_ids"] == manifest["primary_groups"][key],
            f"Original task allocation changed: {key}",
        )
        for path in owner["files"]:
            require((root / path).is_file(), f"Missing module dependency: {path}")
    evidence = {}
    for entry in data["evidence"]:
        require(entry["id"] not in evidence, "Duplicate evidence ID")
        require(re.fullmatch(r"[A-Za-z0-9_-]+", entry["id"]), "Unsafe evidence ID")
        require(re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]), "Require full SHA256")
        require(
            digest(public_path(root, entry["path"])) == entry["sha256"],
            f"Evidence changed: {entry['id']}",
        )
        strings([entry["title"], entry["scope"]], "evidence title and scope")
        evidence[entry["id"]] = entry
    require(evidence, "At least one actual evidence reference is required")

    def refs(ids):
        require(
            isinstance(ids, list) and ids and all(i in evidence for i in ids),
            "Unknown or missing evidence reference",
        )

    refs(data["checkpoint_evidence"])
    require(data["studies"], "Supply at least one actual scoped result set")
    study_ids = set()
    for study in data["studies"]:
        require(study["id"] not in study_ids, "Duplicate study ID")
        study_ids.add(study["id"])
        require(
            study["phase"]
            in {"development", "formal", "regression", "product", "memory", "interface", "package"},
            "Unknown study phase",
        )
        for key in ("planned", "accounted", "missing"):
            integer(study[key], "study " + key)
        require(
            study["accounted"] + study["missing"] == study["planned"],
            "Study denominator does not reconcile",
        )
        require(isinstance(study["outcomes"], dict), "Study outcomes must be named counts")
        for value in study["outcomes"].values():
            integer(value, "outcome count")
        require(
            sum(study["outcomes"].values()) == study["accounted"], "Outcome counts do not reconcile"
        )
        strings(study["findings"], "study findings")
        strings(study["limitations"], "study limitations")
        refs(study["evidence_refs"])
        for metric in study["metrics"]:
            strings([metric["name"], metric["value"], metric["scope"]], "metric")
    for row in data["costs"]["rows"]:
        for field in ("calls", "input_tokens", "output_tokens", "missing_usage_calls"):
            integer(row[field], "cost " + field, nullable=True)
        require(
            row["amount"] is None
            or (
                type(row["amount"]) in {int, float}
                and math.isfinite(row["amount"])
                and row["amount"] >= 0
            ),
            "Invalid cost amount",
        )
        strings([row["purpose"], row["basis"]], "cost purpose and basis")
        refs(row["evidence_refs"])
    strings(data["costs"]["limitations"], "cost limitations")
    human = data["human_review"]
    integer(human["completed_ratings"], "human rating count")
    integer(human["independent_reviewers"], "independent reviewer count")
    require(
        human["completed_ratings"] == 0 or human["independent_reviewers"] > 0,
        "Ratings require actual reviewers",
    )
    strings(human["instructions"], "human review instructions")
    strings(human["findings"], "human findings")
    refs(human["evidence_refs"])
    for item in data["failures"]:
        strings([item["label"], item["observed"], item["disposition"]], "retained failure")
        refs(item["evidence_refs"])
    require(data["failures"], "Retained development failures must be reported")
    for item in data["operations"]:
        strings([item["label"], item["instruction"], item["verification_scope"]], "operation")
        refs(item["evidence_refs"])
    strings(data["delivery"]["findings"], "delivery findings")
    refs(data["delivery"]["evidence_refs"])
    for slug, item in data["members"].items():
        strings(item["findings"], slug + " actual findings")
        strings(item["remaining"], slug + " remaining scope")
        refs(item["evidence_refs"])
        require(set(item["study_ids"]) <= study_ids, "Unknown member study")
    require(not FORBIDDEN.search(json.dumps(data)), "Possible credential material in report input")
    return evidence


def p(text):
    return {"type": "paragraph", "text": text}


def h(text):
    return {"type": "heading", "text": text}


def bullets(items):
    return [{"type": "bullet", "text": item} for item in items]


def evidence_blocks(ids, evidence):
    blocks = []
    for identity in dict.fromkeys(ids):
        item = evidence[identity]
        blocks += [
            {"type": "paragraph", "text": f"{item['title']}. {item['scope']}", "keep_next": True},
            {"type": "reference", "text": item["path"]},
            {"type": "reference", "text": "SHA256 " + item["sha256"]},
        ]
    return blocks


def study_blocks(studies):
    blocks = []
    for study in studies:
        blocks.append({"type": "subheading", "text": study["label"]})
        blocks.append(
            p(
                f"Phase: {study['phase']}. Planned {study['planned']}; accounted {study['accounted']}; missing {study['missing']}. All scheduled outcomes are included."
            )
        )
        blocks.append(
            {
                "type": "table",
                "headers": ["Recorded outcome", "Count"],
                "rows": [
                    [key.replace("_", " "), str(value)] for key, value in study["outcomes"].items()
                ],
                "widths": [5.6, 1.4],
            }
        )
        blocks.extend(p(v) for v in study["findings"])
        if study["metrics"]:
            blocks.append(
                {
                    "type": "table",
                    "headers": ["Metric", "Value", "Scope"],
                    "rows": [[m["name"], m["value"], m["scope"]] for m in study["metrics"]],
                    "widths": [2.0, 1.4, 3.6],
                }
            )
        blocks.extend(p("Limit: " + value) for value in study["limitations"])
        blocks.append(p("Evidence IDs: " + ", ".join(study["evidence_refs"]) + "."))
    return blocks


def build_content(data, owners, evidence):
    common = owners["attribution"] + " Actual execution record: " + data["actual_executor"]
    overall = [p("CS 30 1 | Week 8 enhancement | " + data["as_of"]), h("Checkpoint and scope")]
    overall.extend(p(v) for v in data["summary"])
    overall += [
        p("The eight reports follow the original team responsibilities. " + data["actual_executor"]),
        h("Implemented workflow"),
    ]
    overall += [
        p(
            "Ordinary textbook requests use complete direct answers by default. Explicit hints persist within the current problem; requests for a full explanation and new problems change that task state. Textbook and general-knowledge modes retain separate provenance. Source selection, checked generation, learner presentation and memory snapshots are joined through versioned interfaces."
        ),
        p(
            "A checked request normally generates once and performs one batch check. A rejected draft may use one repair and one recheck within the same four-call and 180-second limit. Exact fragment identity is checked structurally; semantic support is a separately recorded model judgment. No unchecked repair is published. Memory updates have their own bounded jobs and deletion fences."
        ),
        h("Versions and comparison methods"),
    ]
    overall.extend(p(v) for v in data["version_notes"] + data["method_notes"])
    overall += [h("Recorded results")]
    overall += study_blocks(data["studies"])
    overall += [h("Calls cost and retained failures")]
    rows = []
    for row in data["costs"]["rows"]:
        amount = (
            "Unknown"
            if row["amount"] is None
            else str(row["amount"]) + " " + data["costs"]["currency"]
        )
        rows.append(
            [
                row["purpose"],
                "Unknown" if row["calls"] is None else str(row["calls"]),
                "Unknown" if row["input_tokens"] is None else f"{row['input_tokens']:,}",
                "Unknown" if row["output_tokens"] is None else f"{row['output_tokens']:,}",
                amount,
            ]
        )
    if rows:
        overall.append(
            {
                "type": "table",
                "headers": ["Purpose", "Calls", "Input tokens", "Output tokens", "Estimated cost"],
                "rows": rows,
                "widths": [2.05, 0.65, 1.4, 1.35, 1.55],
            }
        )
    overall.append(p("The purpose-level cost ledger records the input, output and cache usage for each attempt. Estimates use the official 20 September CNY tariff. The connection probe's cache split is unavailable. Evidence ID: costs."))
    overall.extend(p(v) for v in data["costs"]["limitations"])
    for failure in data["failures"]:
        overall.append(
            p(
                f"{failure['label']}. {failure['observed']} {failure['disposition']} Evidence IDs: {', '.join(failure['evidence_refs'])}."
            )
        )
    human = data["human_review"]
    overall += [
        h("Independent human review"),
        p(
            f"Completed independent ratings: {human['completed_ratings']}. Actual independent reviewers: {human['independent_reviewers']}. The preceding results use automatic evaluation."
        ),
    ]
    overall.extend(p(v) for v in human["findings"])
    overall += bullets(human["instructions"])
    overall += [h("Operation and delivery")]
    for operation in data["operations"]:
        overall.append(
            p(
                f"{operation['label']}. {operation['instruction']} Verified scope: {operation['verification_scope']}. Evidence IDs: {', '.join(operation['evidence_refs'])}."
            )
        )
    overall.extend(p(v) for v in data["delivery"]["findings"])
    overall += [h("Limitations and Week 9 work")]
    overall.extend(p(v) for v in data["limitations"])
    overall += bullets(data["week9_actions"])
    overall += [
        h("Evidence references"),
        p(
            "Paths are relative to the delivered project root. Full hashes identify the dated records used for this report."
        ),
    ]
    overall += evidence_blocks(list(evidence), evidence)
    reports = [
        {
            "filename": "Week08_Enhancement_Overall_Report",
            "title": "Week 8 Learning Enhancement Report",
            "blocks": overall,
        }
    ]
    for owner in owners["members"]:
        member = data["members"][owner["slug"]]
        blocks = [
            p(owner["name"] + " | " + owner["domain"] + " | " + data["as_of"]),
            h("Domain outcome"),
            p(owner["outcome"]),
            p("Original accountable task IDs: " + ", ".join(owner["task_ids"]) + "."),
            h("Implemented changes"),
        ]
        blocks.extend(p(v) for v in owner["implementation"])
        blocks += [
            h("Interfaces and dependencies"),
            p(owner["dependencies"]),
            p("Implementation and dependency paths: " + "; ".join(owner["files"]) + "."),
            h("Current verification"),
        ]
        blocks.extend(p(v) for v in member["findings"])
        selected = [s for s in data["studies"] if s["id"] in member["study_ids"]]
        if selected:
            blocks.append(
                {
                    "type": "table",
                    "headers": ["Matched record", "Accounted", "Planned"],
                    "rows": [
                        [s["label"], str(s["accounted"]), str(s["planned"])] for s in selected
                    ],
                    "widths": [4.4, 1.3, 1.3],
                }
            )
        blocks.append(
            p(
                f"Independent human ratings recorded for this checkpoint: {human['completed_ratings']}. Prepared review materials are ready for the group's two reviewers."
            )
        )
        blocks += [h("Failures and limits"), p(owner["limits"])]
        blocks.extend(p(v) for v in member["remaining"])
        blocks += [h("Module operation")] + bullets(owner["workflow"])
        blocks += [h("Week 9 actions")] + bullets(owner["week9"])
        blocks += [h("Accountability and evidence"), p(common)]
        blocks += evidence_blocks(member["evidence_refs"], evidence)
        reports.append(
            {
                "filename": owner["slug"] + "_Week08_Enhancement_Report",
                "title": "Week 8 Module Report",
                "blocks": blocks,
            }
        )
    return reports


def markdown(report):
    lines = ["# " + report["title"], ""]
    for block in report["blocks"]:
        kind = block["type"]
        if kind == "table":
            clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
            lines += [
                "| " + " | ".join(map(clean, block["headers"])) + " |",
                "| " + " | ".join("---" for _ in block["headers"]) + " |",
            ]
            lines.extend("| " + " | ".join(map(clean, row)) + " |" for row in block["rows"])
        else:
            prefix = {"heading": "## ", "subheading": "### ", "bullet": "- "}.get(kind, "")
            lines.append(prefix + block["text"])
        lines.append("")
    return "\n".join(lines)


def document_bytes(report, data):
    # Artifact dependencies are imported only during explicitly requested creation.
    from docx import Document
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    def xml(tag, **attributes):
        element = OxmlElement("w:" + tag)
        for key, value in attributes.items():
            element.set(qn("w:" + key), str(value))
        return element

    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(0.72)
    section.left_margin = section.right_margin = Inches(0.75)
    section.header_distance = section.footer_distance = Inches(0.3)
    for name, size in (
        ("Normal", 11),
        ("Title", 23),
        ("Heading 1", 14),
        ("Heading 2", 12),
        ("Header", 9),
        ("Footer", 9),
        ("List Bullet", 11),
    ):
        style = document.styles[name]
        style.font.name, style.font.size, style.font.color.rgb = (
            "Arial",
            Pt(size),
            RGBColor(0, 0, 0),
        )
        style.paragraph_format.space_after = Pt(7)
        style.paragraph_format.line_spacing = 1.08
        style.paragraph_format.widow_control = True
        if name in {"Title", "Heading 1", "Heading 2"}:
            style.paragraph_format.keep_with_next = True
            style.paragraph_format.space_before = Pt(13 if name != "Title" else 0)
            style.font.bold = name != "Title"
        properties = style.element.find(qn("w:pPr"))
        if properties is not None:
            for border in list(properties.findall(qn("w:pBdr"))):
                properties.remove(border)
    section.header.paragraphs[0].text = "CS 30 1     Week 8 learning enhancement"
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run(
        "Personalised AI Learning Assistant Using Retrieval-Augmented Generation and Large Language Models\n"
    ).font.size = Pt(8)
    footer.add_run(data["as_of"] + "     Page ")
    footer._p.append(xml("fldSimple", instr="PAGE"))
    properties = document.core_properties
    properties.title, properties.subject = (
        report["title"],
        "Evidence-linked Week 8 enhancement report",
    )
    properties.author = "CS 30 1 shared project workflow"
    properties.last_modified_by = "CS 30 1 report builder"
    document.add_paragraph(report["title"], "Title")
    for block in report["blocks"]:
        kind = block["type"]
        if kind != "table":
            style = {
                "heading": "Heading 1",
                "subheading": "Heading 2",
                "bullet": "List Bullet",
            }.get(kind)
            paragraph = document.add_paragraph(block["text"], style)
            if block.get("keep_next"):
                paragraph.paragraph_format.keep_with_next = True
            if kind == "reference":
                paragraph.paragraph_format.space_after = Pt(4)
                paragraph.paragraph_format.keep_with_next = not block["text"].startswith("SHA256 ")
                for run in paragraph.runs:
                    run.font.size = Pt(9)
            continue
        table = document.add_table(rows=1, cols=len(block["headers"]))
        table.autofit = False
        for column, width in zip(table.columns, block["widths"]):
            column.width = Inches(width)
        props = table._tbl.tblPr
        borders = xml("tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            borders.append(xml(edge, val="single", sz=4, color="D9D9D9"))
        props.append(borders)
        margins = xml("tblCellMar")
        for edge in ("top", "bottom", "left", "right"):
            margins.append(xml(edge, w=100, type="dxa"))
        props.append(margins)
        table.rows[0]._tr.get_or_add_trPr().append(xml("tblHeader"))
        for index, values in enumerate([block["headers"], *block["rows"]]):
            row = table.rows[0] if index == 0 else table.add_row()
            row._tr.get_or_add_trPr().append(xml("cantSplit"))
            for column, (cell, value) in enumerate(zip(row.cells, values)):
                cell.width = Inches(block["widths"][column])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                cell.text = str(value)
                fill = "213B50" if index == 0 else "F2F5F7" if index % 2 == 0 else "FFFFFF"
                cell._tc.get_or_add_tcPr().append(xml("shd", fill=fill))
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_before = Pt(2)
                    paragraph.paragraph_format.space_after = Pt(2)
                    paragraph.paragraph_format.line_spacing = 1.05
                    paragraph.paragraph_format.keep_with_next = index == 0
                    paragraph.alignment = (
                        WD_ALIGN_PARAGRAPH.CENTER
                        if column and len(str(value)) < 25
                        else WD_ALIGN_PARAGRAPH.LEFT
                    )
                    for run in paragraph.runs:
                        run.font.size = Pt(10)
                        run.bold = index == 0
                        run.font.color.rgb = RGBColor.from_string(
                            "FFFFFF" if index == 0 else "000000"
                        )
        document.add_paragraph().paragraph_format.space_after = Pt(3)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    owners = json.loads((HERE / "ownership.json").read_text(encoding="utf-8"))
    evidence = validate(data, owners, args.root)
    reports = build_content(data, owners, evidence)
    if not args.create:
        print(
            json.dumps(
                {
                    "status": "validated_only",
                    "reports": len(reports),
                    "created": 0,
                    "words": {r["filename"]: len(markdown(r).split()) for r in reports},
                }
            )
        )
        return
    require(args.output is not None, "Creation requires a new output directory")
    require(not args.output.exists(), "Output exists; preserve it and select a new dated directory")
    # The skill runtime is mandatory for authoring, independent of the project venv.
    require(
        "codex-primary-runtime" in Path(sys.executable).as_posix(),
        "Use the bundled document runtime",
    )
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    for report in reports:
        for extension, content in (
            (".md", markdown(report).encode("utf-8")),
            (".docx", document_bytes(report, data)),
        ):
            path = args.output / (report["filename"] + extension)
            with path.open("xb") as stream:
                stream.write(content)
            records.append(
                {"path": path.name, "bytes": len(content), "sha256": sha256(content).hexdigest()}
            )
    manifest = {
        "schema": "week08_enhancement_reports_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": data["checkpoint"],
        "input_sha256": digest(args.data),
        "builder_sha256": digest(__file__),
        "ownership_sha256": digest(HERE / "ownership.json"),
        "docx_count": 9,
        "markdown_count": 9,
        "files": records,
        "visual_qa": "pending_render_and_every_page_inspection",
        "artifact_marker": "caller_owned",
    }
    with (args.output / "report-build.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "status": "created_requires_visual_qa",
                "docx": 9,
                "markdown": 9,
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
