# Week 8 Module Report

Zeping Liao | Backend state permissions and lifecycle | 2026-09-20

## Domain outcome

The backend domain turns teaching, source projection and memory rules into durable request behavior. It records authoritative task state and immutable snapshots, keeps private drafts separate from learner content and validates that a delayed worker still has permission to publish.

Original accountable task IDs: BE-01, BE-02, BE-03, BE-04, BE-05, BE-06, BE-07, BE-08, BE-09, BE-10, BE-11, BE-12, BE-13, BE-14, BE-15, BE-16, BE-17, CHAT-02, CHAT-03, CHAT-08.

## Implemented changes

Additive learning-state models persist tasks, memory entries and revisions, snapshots, approved source views and exposure events. New request commands freeze the enhancement policy and effective model configuration. Old requests preserve their historical behavior, while a retry or worker continuation uses the original frozen identities.

The source service verifies fragment slices and ownership before persistence and inspection. Claim-specific access retains every approved segment and changes the highlight association only. Unchecked titles, previews, rejected drafts and raw checker explanations are excluded from ordinary answer and history responses.

Memory updates use optimistic versions and bounded jobs. Deletion and revocation fence stale execution, remove linked content from derivatives and suppress future use. Request publication, cancellation and task changes are checked transactionally. Credentials remain in their existing protected resolver and never enter public model snapshots.

## Interfaces and dependencies

Sijin supplies final checked outcomes and safe diagnostics. Hongle and Chengzhou provide immutable source identity. Pengyuan defines memory and task rules, Baiqing consumes the strict public DTOs, and Chong supplies durable failure and concurrent-state verification. Migration and preservation reports must bind the actual database checkpoint.

Implementation and dependency paths: backend/app/modules/learning_state/models.py; backend/app/modules/learning_state/memory.py; backend/app/modules/learning_state/tasks.py; backend/app/modules/learning_state/sources.py; backend/app/modules/answering/service.py; contracts/learning.py.

## Current verification

The additive migration preserved the measured aggregates of 33 pre-existing tables. New task, memory, projection and exposure records extend that state without replacing old answers or source versions. The real teaching journey joins three request IDs to three published presentations, three delivery events and three browser-render acknowledgements. Distinct identities let an audit identify what was generated privately, released to the learner and actually displayed.

The first five-request live lifecycle check retained four successful generations and one memory-enabled context-limit failure. Its permission, redaction, memory snapshot and erasure assertions remain useful, while the failed request remains a failure. Actual browser memory edits exercised compare-and-swap behavior through a 409 conflict, draft retention and a later successful correction; deletion finished with both verification entries removed and memory disabled.

The final software evidence records 605 Python passes, including lifecycle coverage, and the isolated fault mapping covers 10 catalogue IDs with 14 assertions. Fresh CPU installation verifies 243 exact deployed runtime files in a separate database. These records support the specific transaction and execution paths exercised, with independent scientific and large-concurrency review remaining distinct work.

After the original live regression ended, learning_task_v2 corrected a reproduced task-boundary issue: new named subjects now avoid implicit hint continuation, and navigation predicates remain serialisable. Its dedicated verification is separate from the earlier fixed formal generation study. Explicit full-explanation commands and historical frozen requests retain their intended behavior.

| Matched record | Accounted | Planned |
| --- | --- | --- |
| Existing live reliability catalogue | 110 | 110 |
| Final software verification | 8 | 8 |
| Actual learner control journeys | 3 | 3 |

Independent human ratings recorded for this checkpoint: 0. Prepared review materials are ready for the group's two reviewers.

## Failures and limits

A passing disposable-database scenario does not establish unlimited concurrency or a complete privacy audit. Actual migration, live lifecycle and deletion checks have their own evidence and dates. A failed generation with no approved projection remains a visible terminal error rather than an answer reconstructed from a draft.

Prioritise simultaneous new-topic and full-explanation transitions, memory edits and delayed worker completion in Week 9 concurrency review. Keep request, task and exposure versions visible in each reproduction, and preserve unsuccessful attempts when recovery behavior changes.

## Module operation

- Check the migrated schema and retained corpus and history fingerprints without replacing the existing database.

- Exercise task, memory and source endpoints as the owning learner and verify that unauthorized requests cannot inspect private state.

- Inspect a cancelled or stale job and confirm that its token cannot publish an answer or restore erased memory.

## Week 9 actions

- Extend measured concurrency cases around simultaneous memory edits, deletion and delayed publication while preserving each failed attempt.

- Review derived-data retention and operational recovery with explicit authorized scope, without exporting private histories or deployment secrets into public packages.

- Reproduce lifecycle failures on an isolated installation and reconcile request, job, task and exposure versions before changing recovery policy.

## Accountability and evidence

These are accountable project domains from the original team allocation. The implementation and verification cited in the reports were performed through the shared project workflow. Domain ownership does not establish a personal commit, individual execution, independent review or personal authorship. Actual execution record: Codex performed the shared implementation, scripted execution and document preparation. Named members remain the accountable module owners. Independent reviewers have supplied 0 ratings.

Additive migration preservation. Measured aggregates of 33 existing tables before and after the additive schema change.

evidence/week08-enhancement/20260920/backend/main-migration-preservation.json

SHA256 ddb6ffbbc53310707e2dbccab344f8a357f8995e206708b6c07ffdb507287d33

Retained live lifecycle scope. Five actual requests, including the recorded memory-enabled context-limit failure.

evidence/week08-enhancement/20260920/backend/live-lifecycle-attempt1-scope.json

SHA256 0f6725fbc4ca90e5ffc028c99236e5aca72ec0b86414b72efaa43ab364af316d

Teaching delivery and rendering. Three published presentations with separate delivered and rendered event identities.

evidence/week08-enhancement/20260920/backend/browser-teaching-exposures.json

SHA256 2e5c51be731fa96cd534a4a62cc3fbbf0a906e947da34dc69e3441ef7e26ffe3

Final software verification. Current gate stages with immutable before/after source snapshot; software behavior scope.

evidence/week08-enhancement/20260920/software-gate-final-attempt2/software_gate.json

SHA256 ff8283ac8302aa5441412ddc49a57f664d376504a5ce8f82ba52709863eb0acd

Post-study task boundary correction. Separate HTTP task-resolution fix and verification after the frozen formal generation study.

evidence/week08-enhancement/20260920/task-boundary/final-verification.json

SHA256 c8ed064ff810d4232224e96ee9ba01f4ae5a2048de724cd2744af8ed03830d4f
