# Practice source review and grading failure

## Retained review and current successor

This document preserves the earlier 864-source operating/review checkpoint. Its pending grading decision predates the user’s selected real-model free-text assessment. The integrated successor saves unresolved assessments for review and pauses learning advancement. Choice and numeric grading retain their deterministic rules. See the [practice assessment implementation](week09-practice-model-assessment-20261003.md) and [current 875-source component checkpoint](week09-current875-component-checkpoint-20261003.md) for the current decision, API behavior and verification. The historical results below retain their original source cohort and scope.

3 October 2026, Australia/Sydney.

The current deterministic free-text grader returned `correct` for all eight source-contradictory probes in this finite review. Source tracing shows that this outcome advances practice steps or completes an item, increases review correct counts and can enter an opt-in assessment-performance memory. This consequence was traced in current code; no database-backed attempt was submitted in this review.

An independent local AI reviewer derived answers from the retained official OpenStax passage exports before reading the saved private rubrics. Twelve authored items were selected in catalogue order across four books: four single-choice, four short-response, two numeric and two stepwise items. Input identities, the review schema and independent answers were frozen before key comparison. All twelve exported source/locator identities matched, and the saved keys agreed with those independently derived answers.

| Actual probe scope | Count | Recorded result |
| --- | --- | --- |
| Source and key review | 12 items | All 12 source checks and independent key comparisons passed within the inspected exports. |
| Source-correct responses | 14 responses | 12 `correct`, one `partial`, one `incorrect`. |
| Source-contradictory responses | 8 responses | All 8 returned `correct`. |
| Direct negation controls | 3 responses | None returned `correct`. |
| Numeric and unit controls | 6 controls | All 6 matched their expected rule outcomes. |
| Public item projection canaries | 12 items | All 12 omitted the private rubric canary. |

The current feedback identifies `deterministic_rules_v2` and retains null semantic verification. Existing source consumers still treat its lexical `correct` as sufficient to advance. The opt-in memory type is `assessment_performance`, with automatic rubric provenance and null semantic verification. The records retain each source-correct response that did not receive credit and each contradictory response that did.

Two inspected source exports contain formula formatting loss. Two retained generated public draft bundles lack exact submitted keys/source passages and receive no semantic success. Live API, export, cache and prompt disclosure checks were zero in this review; the pure public-projection canaries have their own finite scope. Current database membership and original PDF geometry were not rechecked by this file-only study.

The scoring workflow decision is pending: configured model checking or explicit review must distinguish an unassessed free-text attempt from a graded failure and prevent premature progress, review scheduling and memory claims. Provider execution belongs outside owner/progress locks, with durable request identity, source ownership, finite budgets, idempotent publication and preserved historical attempts. The repair and its successor replay remain required Week 9 work.

This purposeful adversarial sample supplies a concrete grading defect. It has zero human labels and no learning-gain measurement. Product code, current reports, database state, sources, model settings and earlier outputs stayed unchanged during the review.

[Aggregate results and exact source/code hashes](../../evidence/week09-continuation/20261001/current-practice-quality-independent-review-20261003.json).
