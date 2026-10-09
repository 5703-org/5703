# Teaching contract review and result import

The 26 September controlled comparison has 128 terminal outcomes. Two independent reviewer forms contain 128 rows each. Every rating is blank. The online checker is part of the evaluated product and has supplied no independent human rating.

## Materials

The local coordinator directory is `evidence/teaching-performance/20260926/private/live-contracts-corrected/blind-review`.

Give each reviewer `review-packets.json`, `SCORING_GUIDE.md` and their assigned `reviewer-1.csv` or `reviewer-2.csv`. Retain `coordinator-mapping-private.json` separately until reviews are returned. Its condition labels map the blinded rows to policies and case identities. The source anchors refer to the preserved official corpus. Reviewers should receive access to those source records when checking support. Keep the reviewer IDs and row order intact.

The packet includes the original problem, current turn, fixed prior question when applicable, actual delivered response and citation projection, source anchors, required points and forbidden inferences. Fixed prior contexts are authored evaluator inputs. For absent responses, semantic ratings remain blank; the failed delivery already counts in automatic results.

## Scoring

Rate factual correctness, textbook-source support, help scope, task-specific usefulness and learner-attempt feedback on the integer scale 0–3: 0 incorrect/unusable, 1 major errors or omissions, 2 mostly adequate with a material limitation, 3 appropriate for this exact request. Write a brief reason for material limitations. Leave source support blank for general-knowledge responses and attempt feedback blank outside learner-attempt rows. Hint leakage is `yes` or `no` for hints and blank for direct answers. Evaluate the body and citation display together, including the provided prior content.

Zero is an actual adverse rating; blank means absent or inapplicable. The importer keeps this distinction. Each reviewer submits an independent file before discussion or reconciliation. Keep the original submitted files; any later adjudication belongs in a separate version. Neither an online checker acceptance nor a publication count establishes learning benefit.

## Import

Run from the project root with the virtual environment active and the project root and `backend` on `PYTHONPATH`. Replace the two submitted-file paths and choose a new result path:

```powershell
$env:PYTHONPATH = '.;backend'
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -m scripts.verify.teaching_contracts_live import-reviews `
  --output evidence/teaching-performance/20260926/private/live-contracts-corrected `
  --reviews path/to/submitted-reviewer-1.csv path/to/submitted-reviewer-2.csv `
  --result evidence/teaching-performance/20260926/private/live-contracts-corrected/human-import-01.json
```

The importer validates exact columns, every blinded ID once, allowed scores and mode/stage applicability. It refuses to overwrite an existing import. It records file hashes, supplied rows, actual scored-row counts and the frozen study hash. Importing does not revise automatic endpoints or fill missing ratings. Before interpretation, the coordinator joins blinded IDs to the private mapping and reports each reviewer's coverage and scores separately; disagreement and any adjudication remain visible.

The actual untouched forms were imported to `blank-import-validation.json` as a software check: two reviewers, 128 rows each, zero scored rows. This file is a validation artifact, not a completed human review. Thirteen targeted importer tests passed in `evidence/teaching-performance/20260926/generation/review-import.xml`.

Automatic results are published in `evidence/teaching-performance/20260926/generation/live-contracts-128-results.json`. The separately frozen eight post-hoc engineering checks have their own numeric file and are excluded from this review's 128-row denominator. The [contract execution record](teaching-contracts-20260926.md) gives methods, all failure counts and provider usage.
