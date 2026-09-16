# Entire-project execution policy

`execution_scope=ENTIRE_PROJECT`; `calendar_gates=false`; `owner_gates=false`. The single user instruction covers the complete v5 specification and responsive refinement. All 108 tasks and all 60 top-level scenarios remain in scope. UI-01–12 refine existing acceptance.

The canonical queue is `execution_order.json`; it includes every task and its artifact dependency order. Eligibility depends on usable predecessor contracts, implementation and relevant producer checks, not a suggested course week or the presence of a named human owner. Related live research or human review may remain pending while its usable code/contract unblocks downstream implementation. Scientific conclusions still require actual measurements.

Use `tasks.json` for task_id, accountable_owner, actual_executor, execution_checkpoint, artifact_dependencies, implementation_status, verification_status, research_status, human_review_status, changed_files, actual_commands, evidence_paths, actual_started_at, actual_completed_at and blockers. Original source_evidence is historical; reporting metadata remains in the separate reporting object. Do not change dates or authors to fit a reporting table.

At each connected increment, implement entry/service/persistence/consumer/failure handling, run relevant checks, repair defects, update actual evidence and continue. G0–G9 are dependency checkpoints, not weekly assignments or routine approval gates. FOUNDATION_READY means designed contracts are internally consistent; it is not application runtime acceptance and must be followed by G1.

Record exact blockers in `blockers.json`, explaining affected tasks/checks, missing input, independent work and the action that would resolve it. Missing original pilot pages, SciQ, model credentials or ratings cannot disable the independent chat product. A partial or mock-only result must not be described as the complete research or product outcome.

## Delivery export design

The final local export reads `tasks.json`, `acceptance.json`, `ui_acceptance.json` and `reporting_plan.json`. It deterministically generates one English file per accountable owner in `docs/delivery/by_owner/` and one per suggested course week in `docs/delivery/by_week/`. Each includes task IDs, feature explanation, source files/interfaces, producer/consumer collaborators, actual executor/completion/evidence, unresolved items and demonstration references. The weekly view distinguishes allocation from actual completion and carry-over.

All views link to one codebase, migration chain and canonical ledger. Shared artifacts may be referenced in multiple views but tasks count only once. These exports belong to INT-10, CHAT-12, QA-14 and owner delivery tasks; they create no new task IDs, product modules, fake commits or contributor signatures.

A final audit checks every written task acceptance and its full AC/HC/UI scope, not just whether files exist. Report IMPLEMENTATION, TECHNICAL VALIDATION, LIVE RESEARCH and HUMAN REVIEW separately. Before interruption, record current worktree state, changed files, last commands, active process handles, exact blockers and next three actions in progress.md. Resume the same project from authoritative files and processes.
