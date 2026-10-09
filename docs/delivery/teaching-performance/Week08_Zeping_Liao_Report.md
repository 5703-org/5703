# Week 8 Work Report

Zeping Liao | 540626434 | 26 September 2026

Accounts, model settings, durable chat, diagnostics and operations

## Week 8 scope

This workstream covers all development after the verified Week 7 final release through the current teaching and performance continuation. Accounts, model configuration encryption, conversation persistence, durable jobs, feedback and operator diagnostics were already implemented before Week 8.

Original allocation: BE-01, BE-02, BE-03, BE-04, BE-05, BE-06, BE-07, BE-08, BE-09, BE-10, BE-11, BE-12, BE-13, BE-14, BE-15, BE-16, BE-17, CHAT-02, CHAT-03, CHAT-08.

## Completed work across the week

Persisted structured processing traces and distinct answer-source modes while preserving idempotency, retries, cancellation and historical answer/source snapshots.

Added source presentations/fragments/claims, teaching tasks and actual exposure receipts, with the same hint-safe projection across detail, history and source APIs.

Implemented owner-isolated memory entries/revisions/settings/jobs, CAS/event-order/deletion fences and later typed Memory V2 APIs for summary, processing, preview and assessment provenance.

Added staged provider-test persistence, separately frozen checker configuration and exact-version activation gates; additive migrations preserved original table/corpus/history fingerprints.

Pending tutor questions have an identity, question revision, task revision, expected response kind and current step. Short learner replies carry these bindings through submission, execution and publication. Ownership and stale-state checks protect the persisted task.

Explicit new-problem and full-explanation actions take priority. New migrations add pending-question fields and rollback-safe corpus invalidation. The answer transaction holds a source-publication fence, and diagnostics record queueing, retrieval stages, checking, publication and failure locations.

## Verification and findings

All 129 isolated PostgreSQL integration checks passed before the final aggregate gate. The actual 16-step teaching HTTP flow publishes 13, including all four first-hint/attempt pairs. Seven cache tests cover current data, rollback, trigger state and publication fencing. The corrected timezone calculation preserves the 275.080 ms delay from the recorded Sydney/UTC example. Fresh CPU cancellation and history reload pass.

## Personal code package

The package contains the complete current versions of this workstream's cumulative changed files, with repository paths and a baseline/current hash inventory. The personal DOCX matches the standalone report byte-for-byte. The shared implementation and automated verification were performed through Codex; the named member owns the review, explanation and submission of this workstream.

Selected current file areas:

backend/app/modules/learning_state/tasks.py

backend/app/modules/answering/service.py

backend/app/modules/knowledge/cache.py

backend/alembic/versions/

contracts/models.py

## Week 9 goals

- Exercise concurrent retries, revocation and task updates under realistic load.

- Verify installation and recovery on a separate Windows machine with the production database service.

- Review operational traces with the team and add targeted failure explanations where needed.

## Evidence

docs/execution/teaching-performance-20260926.md

evidence/teaching-performance/20260926/live-http-final/summary.json
