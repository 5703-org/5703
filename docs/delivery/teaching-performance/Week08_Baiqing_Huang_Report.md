# Week 8 Work Report

Baiqing Huang | 540976443 | 26 September 2026

Learner and administrator UI, sources and responsive interaction

## Week 8 scope

This workstream covers all development after the verified Week 7 final release through the current teaching and performance continuation. The chat, source panel, profile and administrator account/model/diagnostic pages existed by Week 7; Week 8 adds more precise learner controls and traceability.

Original allocation: FE-01, FE-02, FE-03, FE-04, FE-05, FE-06, FE-07, FE-08, FE-09, FE-10, FE-11, FE-12, CHAT-06.

## Completed work across the week

Added compact request-processing diagnostics and a per-request textbook/general-knowledge selector with frozen saved-answer provenance.

Added claim-aware highlighted source segments, explicit full-source expansion, parent-linked rendering acknowledgements and independent direct/hint/new-problem controls.

Implemented memory opt-in, summary/source/version/category views, typed correction, true CAS conflict recovery, preview, disable/delete and preserved source-message behavior.

Upgraded model administration to role-specific basic/structured/project tests, capability controls and safe provider errors; verified actual desktop/mobile browser workflows and the 86-test frontend checkpoint of 22 September.

The interface carries current task and pending-question revisions when a learner submits a reply. The selected hint state survives ordinary learner attempts and refresh, while explicit full explanations and new problems follow their own transitions.

The current tutor question remains available near the composer in short mobile layouts. General-knowledge assessment and textbook-support applicability use separate labels. Earlier exact citation highlights, memory controls, model administration and diagnostics remain in the cumulative interface.

## Verification and findings

The final frontend suite passes 87 tests. Twelve actual Chrome checks and four inspected screenshots confirm pending-question persistence, hint selection, keyboard focus and no horizontal overflow at the two mobile viewport heights. General-knowledge facts display their separate assessment. The two scoped transitive dependency patches result in a zero-vulnerability npm audit.

## Personal code package

The package contains the complete current versions of this workstream's cumulative changed files, with repository paths and a baseline/current hash inventory. The personal DOCX matches the standalone report byte-for-byte. The shared implementation and automated verification were performed through Codex; the named member owns the review, explanation and submission of this workstream.

Selected current file areas:

frontend/src/Chat.tsx

frontend/src/styles/app.css

frontend/src/api.ts

frontend/tests/

frontend/package-lock.json

## Week 9 goals

- Run physical-phone keyboard and orientation checks, input-method composition and screen-reader journeys.

- Use blind-review feedback to refine the visibility of hint progress and source restrictions.

- Measure first answer paint and source-opening time under real classroom network conditions.

## Evidence

docs/execution/teaching-performance-20260926.md

evidence/teaching-performance/20260926/browser-final-02/visual-review.json
