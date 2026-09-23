"""Exercise report input safeguards without constructing or rendering a DOCX."""

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("report_builder", HERE / "build_reports.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def fixture():
    data = json.loads((HERE / "report-data.template.json").read_text(encoding="utf-8"))
    data.pop("template_only")
    data["summary"] = ["Authored builder fixture only; no real study result is asserted."]
    data["studies"] = [
        {
            "id": "fixture",
            "label": "Builder fixture",
            "phase": "regression",
            "planned": 3,
            "accounted": 2,
            "missing": 1,
            "outcomes": {"completed": 1, "error": 1},
            "findings": ["Authored counts test reconciliation only."],
            "metrics": [],
            "limitations": ["No model or software quality result."],
            "evidence_refs": ["protocol"],
        }
    ]
    data["human_review"]["instructions"] = [
        "No actual human work is represented by this validation fixture."
    ]
    data["operations"][0]["instruction"] = "Validation reads local metadata only."
    data["failures"][0]["observed"] = "Authored failure-count fixture only."
    for item in data["members"].values():
        item["findings"] = ["Authored builder verification; no member execution inferred."]
        item["study_ids"] = ["fixture"]
    return data


def main():
    owners = json.loads((HERE / "ownership.json").read_text(encoding="utf-8"))
    data = fixture()
    evidence = builder.validate(data, owners, builder.ROOT)
    reports = builder.build_content(data, owners, evidence)
    assert len(reports) == len({r["filename"] for r in reports}) == 9
    assert all(
        "Independent" in builder.markdown(r) or "independent" in builder.markdown(r)
        for r in reports
    )
    checks = [
        "valid metadata only",
        "nine unique report plans",
        "independent review boundary in every report",
    ]

    def reject(label, mutate):
        candidate = deepcopy(data)
        mutate(candidate)
        try:
            builder.validate(candidate, owners, builder.ROOT)
        except (ValueError, KeyError):
            checks.append(label)
        else:
            raise AssertionError("Accepted invalid input: " + label)

    reject("unfinished template rejected", lambda d: d.update(template_only=True))
    reject("planned denominator mismatch rejected", lambda d: d["studies"][0].update(planned=4))
    reject("outcome mismatch rejected", lambda d: d["studies"][0]["outcomes"].update(completed=2))
    reject("boolean count rejected", lambda d: d["studies"][0].update(missing=True))
    reject("changed evidence rejected", lambda d: d["evidence"][0].update(sha256="0" * 64))
    reject(
        "private reference rejected",
        lambda d: d["evidence"][0].update(path="evaluation/private_runs/record.json"),
    )
    reject(
        "traversal reference rejected", lambda d: d["evidence"][0].update(path="docs/../README.md")
    )
    reject(
        "missing reference rejected",
        lambda d: d["evidence"][0].update(path="evidence/nonexistent-builder-fixture.json"),
    )
    reject("unknown evidence ID rejected", lambda d: d.update(checkpoint_evidence=["absent"]))
    reject(
        "ratings without reviewers rejected",
        lambda d: d["human_review"].update(completed_ratings=1),
    )
    reject("missing owner rejected", lambda d: d["members"].pop("Hongle_Yang"))
    reject(
        "unknown member study rejected",
        lambda d: d["members"]["Sijin_Lu"].update(study_ids=["absent"]),
    )
    reject(
        "unfilled instruction rejected",
        lambda d: d.update(summary=["Replace with actual results."]),
    )
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Authored metadata validation only; no DOCX created, no artifact marker, models or database access.",
        "checks": checks,
        "passed": len(checks),
        "docx_created": 0,
        "builder_sha256": builder.digest(HERE / "build_reports.py"),
        "ownership_sha256": builder.digest(HERE / "ownership.json"),
        "helper_sha256": builder.digest(__file__),
        "fixture_word_counts": {r["filename"]: len(builder.markdown(r).split()) for r in reports},
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
