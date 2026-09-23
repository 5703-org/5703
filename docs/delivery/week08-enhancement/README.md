# Week 8 enhancement report builder

This directory contains the final English [overall report](Week08_Overall_Report.docx) and eight member reports under `members/`, with matching Markdown records. The overall report has 11 pages; each member report has three. All 35 pages passed visual review. The [final inventory](../../../evidence/week08-enhancement/20260920/reports/report-inventory.json) and [visual QA](../../../evidence/week08-enhancement/20260920/reports/visual-qa.json) identify the exact files. Earlier 16 September deliverables remain preserved. `ownership.json` retains the original module allocation and Week 9 goals.

Final report input is `evidence/week08-enhancement/20260920/report-data-final.json`. The complete archive includes all nine reports; each member contribution includes its own DOCX and Markdown. The following sections document the reproducible report-building workflow.

The builder requires current public results supplied in a separate JSON file. It does not run experiments, infer success from code, calculate unrecorded costs or invent human scores. The final data should be placed at `evidence/week08-enhancement/20260920/report-data.json`, or another explicitly dated public path. `report-data.template.json` is an incomplete authoring guide and deliberately fails validation while `template_only` is true.

## Input contract

Use schema `week08_enhancement_report_data_v1`. The template lists all required top-level fields. Replace every instruction with actual findings and remove `template_only` only after reconciliation.

- `as_of`, `checkpoint`, `actual_executor`: actual reporting date, filename-safe checkpoint identifier, and execution attribution. Keep domain owners separate from actual executors and independent reviewers.
- `summary`, `version_notes`, `method_notes`: complete English paragraphs stating the actual implementation and results. Include source/prompt/model/policy identities, provider aliases versus fixed model revisions, actual CPU retrieval, matched conditions, development/formal chronology and task-paired analysis. Include result changes and confidence intervals only when calculated and supported.
- `evidence`: records with unique `id`, `title`, project-relative public `path`, full lowercase `sha256` and specific `scope`. Every path must exist under `docs/` or `evidence/`; traversal, private directories and changed hashes are rejected. Copy only approved public summaries into these locations. Do not copy private answer keys, raw personal histories or credentials for reporting.
- `checkpoint_evidence`: evidence IDs binding the current checkpoint. References are required even when a verification is incomplete; their scope must state that limitation.
- `studies`: actual result sets, including distinct development attempts, formal runs, software regression and operational checks where appropriate. The schema below reconciles all planned outcomes and missing items. A refused answer, timeout or exhausted repair is not silently removed. Overlapping software suites should be described as overlapping rather than summed.
- `costs`: separate purposes, actual known usage, optional recorded monetary amount, tariff/time/configuration basis and explicit missing usage. Unknown fields are null. A known subtotal must be called a subtotal; an estimate must be labeled as such. Count reservations separately from verified provider submissions or billing. Generator, checker, memory and offline judge costs remain distinguishable.
- `failures`: retained failures with observed behavior, disposition and evidence IDs. Link both original and later verification when a correction was made; later success does not replace the original result.
- `human_review`: actual `completed_ratings`, actual `independent_reviewers`, findings, verified operation instructions and evidence IDs. Zero remains zero. Instructions must cover blinded assignment, two independent ratings, validation/import, disagreements/adjudication and the automatic-versus-human comparison. Prepared forms are not collected ratings.
- `operations`: verified startup/product/review workflows, with actual scope and evidence. Do not claim an installation, browser workflow or restore based on a prepared command.
- `delivery`: actual packaging and installation findings and references. Package generation may still be pending when reports are authored; say so explicitly. Never claim a blocked private backup ran.
- `limitations`, `week9_actions`: actual unresolved scope and measurable next work, including scientific judgments, review missingness and generalizability. Do not defer mechanisms already implemented this week or propose rebuilding preserved R0–R3 work from zero.
- `members`: exactly the eight slugs in the template. Each contains actual module-specific `findings`, `remaining` scope, `evidence_refs`, and IDs of relevant studies in `study_ids`. A member report quotes matched schedule counts but does not relabel them as that person's executions.

A study record has this shape. The example contains schema placeholders, not a result:

```json
{
  "id": "formal_hints",
  "label": "Formal teaching comparison",
  "phase": "formal",
  "planned": 900,
  "accounted": 0,
  "missing": 900,
  "outcomes": {},
  "findings": ["State the actual execution and its chronology."],
  "metrics": [
    {"name": "Metric name", "value": "Actual value or not measured", "scope": "Denominator method condition and uncertainty"}
  ],
  "limitations": ["State missing judgments and measurement limits."],
  "evidence_refs": ["actual_public_report_id"]
}
```

`accounted + missing` must equal `planned`; the named `outcomes` counts must sum to `accounted`. Allowed phases are `development`, `formal`, `regression`, `product`, `memory`, `interface` and `package`. A software study should define whether its denominator is tests or stages, and avoid mixing them. Metric values are explicit strings so a confidence interval, null observation or undefined ratio is preserved without silent conversion. The author is responsible for checking each value against its bound evidence; hashing alone does not validate a scientific claim.

A cost row contains `purpose`, `calls`, `input_tokens`, `output_tokens`, `missing_usage_calls`, `amount`, `basis` and `evidence_refs`. Counts and amount may be null. The containing `costs` object includes `currency`, `rows` and `limitations`. A failure contains `label`, `observed`, `disposition` and `evidence_refs`. An operation contains `label`, `instruction`, `verification_scope` and `evidence_refs`.

## Validate without creating documents

The bundled Python path is resolved from the installed primary runtime. This preparation does not install dependencies or use the project's virtual environment for Word authoring.

```powershell
Set-Location E:/5703/learning-assistant
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'C:/Users/PC/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B docs/delivery/week08-enhancement/build_reports.py --data evidence/week08-enhancement/20260920/report-data-final.json
```

This prints validation status and per-report word counts. It creates no directory, Markdown report or DOCX. It checks all eight original task allocations against `docs/delivery/manifest.json` and verifies the listed implementation paths exist. The static ownership text must still be editorially reviewed against the final implementation; the builder does not turn path existence into an implementation test.

## Create only after the artifact marker

The coordinating agent runs the documents skill marker successfully **exactly once immediately before the first creation command**, specifying nine DOCX outputs. This builder deliberately does not run the marker. Do not run it during preparation or validation. Then invoke the bundled Python with `--create` and a new output directory:

```powershell
& 'C:/Users/PC/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B docs/delivery/week08-enhancement/build_reports.py --data evidence/week08-enhancement/20260920/report-data-final.json --create --output E:/5703/deliverables/week08_enhancement_20260920/reports/final-attempt1
```

Creation refuses an existing output directory. If it fails partway through, retain that attempt and use a new directory. It writes nine DOCX, nine equivalent Markdown companions and `report-build.json` with exact hashes of the data, builder, ownership text and outputs. It never modifies a prior report. Report titles use plain black Word Title styles; Letter pages, readable body text, repeated table headers, deliberate widths and visible borders follow the document skill. Tables contain comparable records or numbers, while explanatory material stays in prose.

## Final visual and factual review

The manifest deliberately records visual QA as pending. Render every final DOCX and inspect every page PNG at readable resolution. Check title and heading hierarchy, table wrapping, orphaned headings, page gaps, black headings, header/footer positioning and every long path/hash. Fix layout, create a new attempt and repeat. Use the documents skill renderer and bundled tools; if the packaged LibreOffice executable is absent, preserve its failure and use the already authorized hidden Word COM read-only conversion with bundled Poppler. Do not launch an installed desktop LibreOffice as an unrecorded substitute.

After visual inspection, separately reconcile the eighteen report hashes, final data and public package contents. Keep the render PDFs/PNGs as QA intermediates; the requested deliverables are the nine DOCX. Full-package manifests and eight member deltas are generated by the separate delivery process, not by this report builder.
