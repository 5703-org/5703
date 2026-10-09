# Week 8 Module Report

Sijin Lu | Generation and semantic checking | 2026-09-20

## Domain outcome

The generation domain implements a checked answer path that assesses claims and the selected teaching surfaces before publication. Direct complete answers remain the default. Hint control is tied to the current problem and requested help rather than a global instruction to withhold all answers.

Original accountable task IDs: GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06, GEN-07, GEN-08, GEN-09, GEN-10, GEN-11, CHAT-05.

## Implemented changes

The usual checked path generates once and performs one batch semantic check. A rejected draft may be revised once and checked again. Generation, native token counting, retries, format repair, checking and rechecking share the same maximum of four external calls and 180 active seconds. Each stage counts its complete input and output reservation before transport.

The checker receives exact candidate fragments, actual answer claims and the enabled learner-visible surfaces. It reports model-assisted support and task-help judgments. Short per-request aliases remove repeated long identifiers while mapping every selected fragment back to its immutable identity; repeated previews are compacted without removing distinct visible content.

Strict citation markers, evidence IDs, source slices and schema validation remain in force. Learner-provided givens have an explicit exact-quote basis, distinct from textbook support. A proposed source-display repair is rechecked together with the repaired answer. Private drafts and checker explanations never become ordinary learner errors or alternate answers.

## Interfaces and dependencies

Chengzhou supplies source candidates and Hongle their immutable mappings. Pengyuan defines task and memory rules. Zeping freezes configurations, accounts for attempts and persists only approved delivery. Baiqing renders the saved projection, while Chong evaluates all scheduled outputs with separately recorded judge calls.

Implementation and dependency paths: generation/checked.py; generation/checked_schemas.py; generation/joint_policy.py; generation/providers.py; generation/enhancement_contract.md.

## Current verification

T2 produced 100/180 valid hints (55.6%), compared with 110/180 (61.1%) for T1. The task-paired difference was -5.56 percentage points, with a 95% bootstrap interval from -13.33 to 2.22 points.

The controlled study makes checker rejection a measurable product outcome. T2 adds current evidence-display and cumulative-exposure checking, yet its all-planned valid-hint result is lower than T1. The successful responses receive strong same-family support ratings, while many requests exhaust the bounded generate/check/repair/recheck flow. These findings make false rejection, task-help interpretation and the checker reference the next review priorities.

The direct-answer comparison received a corrected offline rubric after the first judge was found to apply hint restrictions. The generated answers, online checks and failures stay unchanged. This preserves the distinction between a product policy change and a measurement correction. The actual browser sequence separately confirms that first hint, next hint and explicit complete explanation persist with the correct task and help level; those state results complement the semantic evaluation.

| Matched record | Accounted | Planned |
| --- | --- | --- |
| Formal teaching comparison | 900 | 900 |
| Direct answers and attribution | 180 | 180 |

Independent human ratings recorded for this checkpoint: 0. Prepared review materials are ready for the group's two reviewers.

## Failures and limits

A semantic checker can make mistakes and share biases with the generator. Its judgment is not independent human certification. Plain mock direct answers retain null semantic support; checked hints with an unavailable checker fail explicitly. A bounded error may remain after four calls, and that failure is part of the result rather than a reason for unlimited retries.

Use two independent reviewers to inspect all major false-rejection and over-help disagreements, including cumulative ordinary source exposure. Freeze any revised prompt or checker as a later policy version, and report its availability, support and cost together with the existing baseline.

## Module operation

- Inspect the saved generation, checking and repair purposes for one completed request and verify the shared call and time budget.

- Compare its public answer and source projection with the final successful check; rejected drafts should remain private.

- For an error, inspect safe metadata and the retained private execution evidence through authorized tools, keeping missing usage and costs explicit.

## Week 9 actions

- Compare checker judgments with two independent human reviews and analyze both false rejection and unsupported publication.

- Review the observed failures before changing prompts, and freeze any new policy as a separate development experiment with preserved prior outputs.

- Calibrate another authorized provider or checker on disagreement cases, recording model identity, cost, token usage and unavailable results separately.

## Accountability and evidence

These are accountable project domains from the original team allocation. The implementation and verification cited in the reports were performed through the shared project workflow. Domain ownership does not establish a personal commit, individual execution, independent review or personal authorship. Actual execution record: Codex performed the shared implementation, scripted execution and document preparation. Named members remain the accountable module owners. Independent reviewers have supplied 0 ratings.

Formal hint comparison. All 900 requests and task-paired model-assisted analysis; human ratings remain separate.

evidence/week08-enhancement/20260920/formal-hints-analysis.json

SHA256 3037903e73ce1046dc7e50236f2e628034b3d1e42d4ee28125ae4dc6c8ea9cd3

Corrected direct-answer citation analysis. Same 180 generated outcomes with corrected direct-answer judging; the original judge is retained.

evidence/week08-enhancement/20260920/formal-citations-judge-v2-analysis.json

SHA256 6aec13d0175ce4f7be47d2f78bf125e405fb82bda94cdf6ac12edb3e4f4c2dd5

Teaching browser journey. Three saved hint/hint/full-answer requests and actual rendering receipts.

evidence/week08-enhancement/20260920/frontend/live-teaching-browser-summary.json

SHA256 29dc575d39d1476aeb0a87f5ee5c3a19f2bcdca9dc7805dc6ebd48524f235d2b
