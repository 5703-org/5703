# Week 9 Work Report

This report records the member domain, cumulative retained work, verified 30 September changes and Week 10 priorities. Shared software, study and installation evidence is distinguished from independent human acceptance.

Zeping Liao | 540626434 | 30 September 2026

Accounts, model settings, durable chat, diagnostics and operations

## Scope and retained work

The backend workstream retains accounts, managed models, durable chat, task revisions, memory ownership and safe diagnostics. Existing saved answers, citations and provider configuration remain separate from the new learning records.

Original allocation: BE-01, BE-02, BE-03, BE-04, BE-05, BE-06, BE-07, BE-08, BE-09, BE-10, BE-11, BE-12, BE-13, BE-14, BE-15, BE-16, BE-17, CHAT-02, CHAT-03, CHAT-08.

## Continuation work

Nine additive tables store reading positions, goals and units, immutable practice items, progress, attempts, review entries, notes and learning records. Object-level workspace and owner checks protect every learner object. Expected-version fences and idempotency receipts serialize concurrent changes and return the original attempt after a lost response.

Practice supports single choice, multiple choice, short explanation, numeric/unit and multi-step tasks. Private rubrics remain server-side. Numeric grading uses a finite unit table and saved tolerance; textual rule feedback leaves independent semantic verification unclaimed. Hints and full explanations are explicit disclosures; completion depends on the recorded learner attempt.

Operational changes add worker lanes, persistent login throttling, controlled provider endpoints and administrator summaries. PowerShell 5.1 startup atomically saves a 24-byte CSPRNG password in an owner-only private file and reuses it on retry. The path hint requires an active-administrator credential match; existing accounts are preserved and the import secret is cleared. Exact-hash visual import runs before services and stops startup on failure.

## Verification and findings

The learning backend passed 35 focused checks, including 17 disposable-PostgreSQL cases for authorization, private keys, immutable revisions, source identity, concurrency, notes and review. Actual browser recovery made three POSTs while saving only two attempts and retained the original receipt after progress advanced.

The main additive migration followed a verified backup and clone rehearsal, preserving the original corpus and history. The integrated V9 checker candidate passed all eight software stages with 1,293 Python tests and 132 frontend tests, zero Python failures or skips, and 657 captured source files unchanged. Ordinary requests retain single_contract_correction_v1. The explicit schema_contract_corrections_v2 candidate allows a second correction for eligible structural checker defects under the same strict validation and four-call/180-active-second budget. The completed paired development probe retains the legacy default and an opt-in successor. Final CPU installation has passed its recorded runtime checks. The V8 automatic study keeps its original source, prompts and outcomes.

The V4 one-command CPU installation completed on its first launcher attempt within an observed upper bound of 237.688 seconds. It verified four original PDF hashes, 10,594 real 384-dimensional vectors, 5,543 unreviewed visual candidates, owner-only credentials and authenticated reader/practice flows. Its first cold-chat worker exited without a captured exception; the cause is unknown. After 211.659 seconds of polling, explicit recovery recorded WORKER_INTERRUPTED. Twelve verified superseded staging services were stopped and only the V4 interactive worker restarted; a separate real-CPU, mock-answer retry succeeded in 12.259 seconds with one citation. This checkpoint verifies explicit recovery. The exit may recur, and live answer quality was outside the installation test.

The separate V9 checker probe accepted three of four fixed drafts under each policy. Its 11 real checker calls and zero generation-model calls retain the ordinary legacy default; the successor remains opt-in. This shared integration decision leaves the frozen V8 study and independent human-review requirements unchanged.

## Final CPU installation

The final V9 installation passed runtime checks in a fresh virtual environment and isolated PostgreSQL database on the existing Windows host. All 1,051 installed runtime inputs retained their preinstall hashes. The installation verified all four original PDFs, 10,594 real 384-dimensional vectors and 5,543 unreviewed visual candidates. PyTorch 2.8.0+cpu has no CUDA, 78 distributions pass pip check, and migration head f4a18bc67d20 is present. Health, administrator login, the reader and isolated practice checks passed. No live provider key was copied.

The first cold CPU retrieval/mock-answer request succeeded in 22.424 seconds and cited Biology 2e, Chapter 8, physical PDF page 235; the displayed text and parent chunk hashes match. A separate read-only CPU query retrieved and reranked 20 candidates in 8.7203 seconds. Vector and release fingerprints were unchanged. These single-request smoke timings are not a load benchmark. The launcher success marker, child exit and live services were observed; an exact exit code was unavailable because the output-capture wrapper remained open. Current-user-only credentials were verified without manual ACL changes. Main data and existing services were untouched. Another physical machine, Mac and live-answer quality remain separate checks.

## V10 learning state and operations

Practice feedback V2 detects a narrow explicit negation of a required expression. A saved step stays current and returns an insufficient outcome with an ambiguity category. Old V1 grading provenance remains readable; new opt-in practice memories carry the method actually used. This is a rule-based guard, with independent semantic correctness still unscored.

The administrator operations view now observes PostgreSQL advisory locks for the interactive and background worker lanes. It distinguishes all, split, partial, none, unexpected and unavailable layouts while retaining queue counts. Lock ownership is an instant observation and does not establish worker responsiveness; interruption and stale-job recovery remain separate checks.

The selected V10 package plan passed an isolated Windows CPU installation. All 1,059 installed runtime files matched their preinstall hashes, including 80 official resources and four visual catalogs. The released corpus retained 10,594 real 384-dimensional E5 vectors; actual CPU retrieval and reranking produced a cited mock answer from Biology 2e physical page 235. Practice feedback V2 and the split worker-lock view passed. Read-only Edge screenshots at 390 and 1440 pixels showed no overflow. This is a same-host runtime smoke check with a mock answer; real-model quality and final archive byte parity remain separate.

## Week 10 goals

- Exercise worker interruption, simultaneous retries and revocation under realistic concurrent load.

- Verify fresh installation, backup restoration and credential recovery on a separate Windows machine.

- Expand failure and accounting review without exposing private answers, keys or provider request bodies.

## Source and responsibility

The named member retains the original workstream accountability. Shared implementation and automated execution were performed through Codex; this record does not claim individual human execution or completed independent review.

backend/app/modules/learning_product/

backend/app/worker.py

backend/app/modules/identity/login_limits.py

## Evidence

evidence/week09-learning/20260930/backend/verification.json

evidence/week09-continuation/20260930/main-migration-preservation.json

evidence/week09-learning/20260930/frontend/recovery-browser-attempt1/verification.json

evidence/week09-learning/20260930/answer-core/portable-credentials-receipt.json

evidence/week09-continuation/20260930/staging-installation-v4-summary.json

evidence/week09-continuation/20260930/software-gate-v5-candidate-1/software_gate.json

evidence/week09-continuation/20260930/pilot-v5-invalid-preparation.json

evidence/week09-continuation/20260930/software-gate-v8-release-1/software_gate.json

evidence/week09-continuation/20260930/pilot-v7-sanitized.json

evidence/week09-learning/20260930/packaging/v8-release-verification.json

evidence/week09-learning/20260930/packaging/external-reviewer-v7.json

evidence/week09-continuation/20260930/formal-v8-teaching-terminal.json

evidence/week09-continuation/20260930/software-gate-v9-release-1/software_gate.json

evidence/week09-continuation/20260930/v9-checker-development/results.json

evidence/week09-continuation/20260930/v9-checker-development/REPORT.md

evidence/week09-continuation/20260930/staging-installation-v9-summary.json

evidence/week09-learning/20260930/packaging/external-materials-final.json

docs/execution/week09-continuation-v10-20260930.md

docs/execution/week09-v10-ledger-20260930.md

evidence/week09-continuation/20260930/software-gate-v10-candidate-1/software_gate.json

evidence/week09-learning/20260930/answer-core/development_probe_v3.json

evidence/week09-continuation/20260930/memory-v3-scope-calibration-sanitized.json

evidence/week09-continuation/20260930/seven-family-scope-audit.json

evidence/week09-learning/20260930/documentation/v10-ledger-preservation.json

evidence/week09-continuation/20260930/staging-installation-v10-summary.json

evidence/week09-learning/20260930/answer-core/v2_v3_live_development_comparison.json
