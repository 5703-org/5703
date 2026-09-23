# Week 8 Memory V2 delivery records

This directory defines the English overall report and eight individual work reports for the current cumulative iteration. Each report describes the assigned domain, implemented changes, actual verification, remaining scope and Week 9 goals. The original task ownership remains unchanged; the execution record identifies the shared implementation workflow separately.

The current [implementation record](../../execution/week08-memory-v2-20260921.md) and [registered study protocol](../../execution/week08-memory-v2-protocol-20260921.md) supply the reporting scope. [All 552 generation records](../../../evidence/week08-memory-v2/20260921/formal/generation-terminal.json) are terminal, including failures and human-dependent waits. [Two blank reviewer forms](../../../evidence/week08-memory-v2/20260921/formal/review-export-verification.json) each retain 552 rows with zero completed ratings. All offline judgment receipts, numerical results and cost accounting are terminal and independently reconciled. The [results record](../../execution/memory-v2-results-20260921.md) preserves every denominator, negative comparison and A1 coverage limitation. The final release gate passes 828 Python/86 frontend tests; source parity verifies 514 files and 80 resources. All nine reports and matching Markdown copies are present. [Visual verification](../../../evidence/week08-memory-v2/20260921/reports-release-final/visual-verification.json) passed all 45 rendered pages and verified that delivery and project copies are identical. The older reports under `../week08-enhancement/` remain dated historical outputs.

Ordinary textbook questions default to full direct explanations. The integrated learner workflow supports claim-specific highlighted source fragments, opt-in learning memory with source/version/edit/disable/delete controls, and explicit hint tasks that progress through further hints or a full explanation. Teaching progress is independent of textbook/general-knowledge mode. Ordinary citation views respect the current hint allowance; access to the full source is an explicit recorded action. The current provider and Memory V2 changes extend these three retained product modules.

## Reports

- [Overall report](Week08_Overall_Report.docx)
- [Xianshu Zhang](members/Xianshu_Zhang/Week08_Report.docx)
- [Hongle Yang](members/Hongle_Yang/Week08_Report.docx)
- [Chengzhou Liu](members/Chengzhou_Liu/Week08_Report.docx)
- [Sijin Lu](members/Sijin_Lu/Week08_Report.docx)
- [Pengyuan Xia](members/Pengyuan_Xia/Week08_Report.docx)
- [Zeping Liao](members/Zeping_Liao/Week08_Report.docx)
- [Baiqing Huang](members/Baiqing_Huang/Week08_Report.docx)
- [Chong Zhang](members/Chong_Zhang/Week08_Report.docx)

## Building the reports

`build_reports.py` validates schema `week08_memory_v2_report_data_v1`, all eight original task allocations, existing module paths, public evidence hashes, study denominators and actual human-rating counts. It reuses the retained report library's document layout and checks while authoring this iteration's narrative. The input adds an `implementation` list of current workflow paragraphs to the earlier report-data contract. It never runs experiments or supplies scores.

Run validation first with the bundled document runtime and a reconciled data file:

```powershell
& 'C:/Users/PC/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B docs/delivery/week08-memory-v2/build_reports.py --data evidence/week08-memory-v2/20260921/report-data-release-final.json
```

Creation adds `--create --output <new-directory>` after the document artifact marker. The output paths are `Week08_Overall_Report.docx` and `members/<First_Last>/Week08_Report.docx`, plus matching Markdown records and a build manifest. Every rendered page must be inspected before delivery. The builder records visual review as pending until that separate verification is complete.

## Public and private artifacts

The public full package retains the real four-book corpus, vector data, model assets, application, tests, contracts and public summaries. Eight member packages contain disjoint changes relative to the verified 20 September baseline, original task IDs and contribution instructions. Packaging runs no GitHub uploads or commits.

The research bundle is a separate private deliverable. It contains the frozen question/reference catalogue, source anchors, raw experiment attempts, model judgments, blank reviewer materials and coordinator condition keys. Actual human ratings enter through the validated import workflow. Credentials and original users' conversation records are excluded from every delivery.

[Private archive verification](../../../evidence/week08-memory-v2/20260921/formal/research-bundle-verification.json) records the separately distributed research ZIP, exact file hashes and retained original study snapshot. Archive hashes and reconstruction are recorded in adjacent release sidecars. Project files do not embed their containing ZIP hash.

The [retained packaging failure and bounded correction](../../../evidence/week08-memory-v2/20260921/packaging/release-fix-verification.json) record a reconstruction mismatch for the verified `resources/official-corpus/corpus.jsonl.gz` asset. The exact resource-path exception preserves its required category, size and hash checks; other archive paths remain excluded. The first nine ZIPs are retained as failed artifacts. Five focused checks and the final full gate passed after changing only the packager and its existing regression test. Scientific outputs, study code and the private research archive are unchanged. New archive hashes and reconstruction are recorded in adjacent release sidecars.
