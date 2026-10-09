# Week 8 Work Report

Sijin Lu | 540627888 | 26 September 2026

Provider protocols, generation, token budgets and citation validation

## Week 8 scope

This workstream covers all development after the verified Week 7 final release through the current teaching and performance continuation. Live DeepSeek Flash answering, multi-protocol adapters, tokenizer budgeting and structural citations were established in Week 7; Week 8 extends their reliability and contracts.

Original allocation: GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06, GEN-07, GEN-08, GEN-09, GEN-10, GEN-11, CHAT-05.

## Completed work across the week

Added complementary evidence/coverage observations, explicit partial-support behavior and a separately labelled general-knowledge mode while keeping textbook answering the default.

Implemented checked generation, semantic batch checks, bounded repair/recheck and source/teaching projections within a shared four-call and 180-second budget; legacy paths remain frozen.

Separated textbook support, exact learner givens and conditional arithmetic proofs; repaired citation binding and checker inconsistencies through versioned cause-specific handling.

Introduced immutable provider capability profiles and separate basic, structured and current-project probes for answer/checker roles, with safe diagnostics and usage. Actual live receipts cover DeepSeek; OpenAI and other providers retain their stated unexecuted or fixture-only limits.

The v3 generation contract permits independently checked procedural hints without a textbook citation. Scientific assertions still require exact source support. General-knowledge facts receive a separate model assessment and a null textbook-support field.

The generator and independent checker exchange explicit tutor-question and learner-attempt metadata. Proposed tutor questions enter the visible draft before checking; the checker verifies their presence, appropriateness and disclosure. Stable policy text precedes dynamic context, and checker-contract repairs contribute to recorded checking time.

## Verification and findings

The frozen study publishes 51 of 64 v2 conditions and 41 of 64 v3 conditions. These are operational counts, with independent quality ratings blank. The successor publishes five of eight separate checks. Actual HTTP first-hint/learner-attempt flows publish all four pairs; later full/new turns retain three failures. The records preserve excessive-disclosure, checker-format, citation-selection drift and provider whitespace failures.

## Personal code package

The package contains the complete current versions of this workstream's cumulative changed files, with repository paths and a baseline/current hash inventory. The personal DOCX matches the standalone report byte-for-byte. The shared implementation and automated verification were performed through Codex; the named member owns the review, explanation and submission of this workstream.

Selected current file areas:

generation/checked.py

generation/reliability.py

generation/checked_v2.py

generation/reliability_v2.py

generation/prompts/

## Week 9 goals

- Review the retained semantic and checker-format failures and compare human judgments with automatic decisions.

- Improve learner-attempt feedback while preserving the original problem and allowed help level.

- Rerun a preregistered comparison for the final successor contract after the post-hoc fixes.

## Evidence

docs/execution/teaching-performance-20260926.md

evidence/teaching-performance/20260926/generation/live-contracts-posthoc-results.json
