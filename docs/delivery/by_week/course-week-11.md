# Delivery view: suggested course week 11

Generated reporting view. The canonical ledgers below remain authoritative; this file adds no product requirement or acceptance decision.

Accountable owner and suggested course week are reporting metadata, never permissions, implementation eligibility, runtime flags or evidence of completion. Actual executor and recorded dates are shown separately. Cross-references do not count a task more than once. No calendar dates or completion percentages are inferred.

Canonical requirements, shared interfaces and evidence: [PRD.md](<../../../PRD.md>) · [SPEC.md](<../../../SPEC.md>) · [PLANS.md](<../../../PLANS.md>) · [HANDOVER.md](<../../../HANDOVER.md>) · [docs/foundation/api_contract.md](<../../foundation/api_contract.md>) · [contracts/openapi.json](<../../../contracts/openapi.json>) · [docs/execution/tasks.json](<../../execution/tasks.json>) · [docs/execution/reporting_plan.json](<../../execution/reporting_plan.json>) · [docs/execution/acceptance.json](<../../execution/acceptance.json>)

Task-ledger reconciliation timestamp (not a completion date): 2026-09-08T10:09:00.459775+00:00

This primary reporting bucket contains 8 unique tasks. A task's canonical suggested week chooses its one primary bucket. The planning packages below can mention it in other weeks as a cross-reference; these references add no completed tasks.

## Suggested allocation only

Suggested team reporting allocation only, not execution schedule, deadline or actual completion evidence.

Week convention: Course/teaching week; project_week=course_week-2 from Week 3. Optional contingency only; official dates/deadlines not confirmed

### Xianshu Zhang — suggested package

Audit requirement-to-code mapping, obsolete MCQ-mainline assumptions and blockers; prepare a release candidate.

- Task cross-references: [INT-09](<../by_owner/xianshu-zhang.md#int-09>), [INT-07](<../by_owner/xianshu-zhang.md#int-07>), [CHAT-11](<../by_owner/xianshu-zhang.md#chat-11>)
- Suggested deliverable paths (not claims of delivery): `docs/release_candidate.md` (path absent), [scripts/verify/chat_scope.py](<../../../scripts/verify/chat_scope.py>)
- Suggested downstream consumers: all eight workstreams
- Planned acceptance description: No missing IDs, cycles or mandatory-choice remnants; critical defects are fixed or explicitly blocking.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Hongle Yang — suggested package

Check asset/chunk/vector counts and historical hashes in a separate restore environment; complete quality limitations.

- Task cross-references: [DAT-10](<../by_owner/hongle-yang.md#dat-10>), [DAT-12](<../by_owner/hongle-yang.md#dat-12>)
- Suggested deliverable paths (not claims of delivery): `docs/data/` (path absent), `artifacts/reports/restore/` (path absent)
- Suggested downstream consumers: Zeping Liao; Chong Zhang
- Planned acceptance description: Restore preserves provenance; cleanup does not delete referenced evidence.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Chengzhou Liu — suggested package

Execute R0/R1 and embedding replacement drills and diagnose measured bottlenecks; avoid speculative optimisation.

- Task cross-references: [RET-06](<../by_owner/chengzhou-liu.md#ret-06>), [RET-11](<../by_owner/chengzhou-liu.md#ret-11>)
- Suggested deliverable paths (not claims of delivery): `tests/integration/test_retrieval_replacement.py` (path absent)
- Suggested downstream consumers: Chong Zhang; Zeping Liao
- Planned acceptance description: Shared consumers remain unchanged; dimension changes use explicit migrations/new indexes, never mixed writes.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Sijin Lu — suggested package

Regress empty/truncated responses, HTTP errors, duplicate JSON keys, budgets and live configuration; reconcile actual generation evidence.

- Task cross-references: [GEN-06](<../by_owner/sijin-lu.md#gen-06>), [GEN-11](<../by_owner/sijin-lu.md#gen-11>)
- Suggested deliverable paths (not claims of delivery): `tests/contract/` (path absent), `docs/generation.md` (path absent)
- Suggested downstream consumers: Chong Zhang; Zeping Liao
- Planned acceptance description: Legacy 39 tests and new HC results remain separate; aggregate retry counts agree and mocks cannot masquerade as live.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Pengyuan Xia — suggested package

Complete available ratings and review misleading analogies, negation and formulas; write findings and limitations.

- Task cross-references: [PER-07](<../by_owner/pengyuan-xia.md#per-07>), [PER-09](<../by_owner/pengyuan-xia.md#per-09>)
- Suggested deliverable paths (not claims of delivery): `docs/research/personalisation.md` (path absent)
- Suggested downstream consumers: Chong Zhang; Xianshu Zhang
- Planned acceptance description: Examples trace to run/profile/rater; unrated items do not receive default high scores.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Zeping Liao — suggested package

Complete clean install, legacy upgrade, single-worker restart, transaction faults, backup/restore and rollback.

- Task cross-references: [BE-15](<../by_owner/zeping-liao.md#be-15>), [BE-16](<../by_owner/zeping-liao.md#be-16>)
- Suggested deliverable paths (not claims of delivery): [scripts/release/](<../../../scripts/release>), [compose.yaml](<../../../compose.yaml>), [docs/runbook.md](<../../runbook.md>)
- Suggested downstream consumers: Chong Zhang; all developers
- Planned acceptance description: Commands rerun; failures do not publish partial success; restore targets are isolated from user databases.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Baiqing Huang — suggested package

Run full browser regression for stop/retry/latest-answer revision/account switch/re-login/history evidence.

- Task cross-references: [FE-06](<../by_owner/baiqing-huang.md#fe-06>), [FE-08](<../by_owner/baiqing-huang.md#fe-08>), [FE-12](<../by_owner/baiqing-huang.md#fe-12>)
- Suggested deliverable paths (not claims of delivery): `tests/e2e/` (path absent), [artifacts/reports/frontend/](<../../../artifacts/reports/frontend>)
- Suggested downstream consumers: Chong Zhang; Zeping Liao
- Planned acceptance description: UI values match DB snapshots; no dead controls, fake streaming or hardcoded success.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Chong Zhang — suggested package

Execute all 48 AC plus 12 HC scenarios, replacement/restore/performance checks; record real environment, commands, exit codes, failures and skips.

- Task cross-references: [QA-13](<../by_owner/chong-zhang.md#qa-13>), [QA-11](<../by_owner/chong-zhang.md#qa-11>), [QA-10](<../by_owner/chong-zhang.md#qa-10>), [QA-12](<../by_owner/chong-zhang.md#qa-12>)
- Suggested deliverable paths (not claims of delivery): `artifacts/reports/acceptance/` (path absent), [docs/execution/acceptance.json](<../../execution/acceptance.json>)
- Suggested downstream consumers: Xianshu Zhang; all workstreams
- Planned acceptance description: Unexecuted checks are not passes; mocks prove wiring only, with live semantic evidence separate.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

## Actual evidence and demonstration material

The task records below quote the current ledger, independently of the suggested package. Their actual evidence links are the available demonstration and check material; an empty or null field stays unrecorded. The export does not create a meeting, human demonstration or historical completion event.

## Carry-over and unresolved work

These are currently recorded unresolved items for this reporting bucket, not claims that a calendar week elapsed or work was late.

- [BE-15](<../by_owner/zeping-liao.md#be-15>) (`REAL_FLOW_VERIFIED`): Provider execution is simulated where fault injection is required; actual external exactly-once execution is not promised. Blockers: None recorded.
- [BE-16](<../by_owner/zeping-liao.md#be-16>) (`REAL_FLOW_VERIFIED`): This is local point-in-time recovery, not a disaster-recovery or availability certification; final package checks are separate. Blockers: None recorded.
- [QA-10](<../by_owner/chong-zhang.md#qa-10>) (`WAITING_EXTERNAL`): Independent relevance/human judgments or user-deferred real answering outputs are missing. No real paired teaching findings or learning gains are claimed. Blockers: None recorded.
- [QA-11](<../by_owner/chong-zhang.md#qa-11>) (`MOCK_TEST_PASSED`): Provider failures are deliberately simulated. Current actual-corpus browser/API revision checks provide separate end-to-end evidence. Blockers: None recorded.
- [QA-12](<../by_owner/chong-zhang.md#qa-12>) (`REAL_FLOW_VERIFIED`): Mock answer semantic limits, live evaluation and physical-device review remain explicit. Blockers: None recorded.
- [QA-13](<../by_owner/chong-zhang.md#qa-13>) (`REAL_FLOW_VERIFIED`): Small-sample local descriptive timings are not an SLA or real-provider latency/cost estimate. Blockers: None recorded.

## INT-09

Track the few genuine external blockers. Record missing assets, permissions, credentials, run budget and host/reviewer inputs in one concise register. Continue independent coding without inventing approval or building a compliance platform.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 11, "suggested_project_week": 9, "suggested_start_course_week": 10, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G8
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-16", "QA-11"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-16"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-11"}]`
- Upstream collaborators (derived from those dependencies): [BE-16](<../by_owner/zeping-liao.md#be-16>) — Zeping Liao; [QA-11](<../by_owner/chong-zhang.md#qa-11>) — Chong Zhang
- Downstream collaborators (reverse dependency references): None recorded.
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Track the few genuine external blockers. Record missing assets, permissions, credentials, run budget and host/reviewer inputs in one concise register. Continue independent coding without inventing approval or building a compliance platform.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [scripts/verify/contracts.py](<../../../scripts/verify/contracts.py>), [scripts/verify/chat_scope.py](<../../../scripts/verify/chat_scope.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-19](<../acceptance.md#ac-19>), [AC-20](<../acceptance.md#ac-20>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/blockers.json](<../../execution/blockers.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: The blocker register distinguishes resolved actual source/model acquisition from user-deferred answering configuration, missing independent labels/ratings and physical-device review.
- Unresolved scope: None recorded.
- Blockers: None recorded.
- Mapping limitation: None recorded.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. The blocker register distinguishes resolved actual source/model acquisition from user-deferred answering configuration, missing independent labels/ratings and physical-device review.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/blockers.json](<../../execution/blockers.json>)
- remaining acceptance scope: `REAL_FLOW_VERIFIED`. No additional task-specific software gap identified; independent overall acceptance is not inferred.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## BE-15

Verify transaction and restart behaviour. Test duplicate requests, profile conflicts, stale job publication, release switches and DB failures on PostgreSQL. Confirm no half-published release, orphan success or overwritten answer.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 11, "suggested_project_week": 9, "suggested_start_course_week": 10, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G8
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-13", "BE-14", "QA-11"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-13"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-14"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-11"}]`
- Upstream collaborators (derived from those dependencies): [BE-13](<../by_owner/zeping-liao.md#be-13>) — Zeping Liao; [BE-14](<../by_owner/zeping-liao.md#be-14>) — Zeping Liao; [QA-11](<../by_owner/chong-zhang.md#qa-11>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [BE-16](<../by_owner/zeping-liao.md#be-16>) — Zeping Liao
- Source files recorded for this implementation: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Changed files recorded by the ledger: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Shared entry / interface boundary: Versioned API and operator CLI / Application services and worker
- Persisted effect / consumer: Relational entities and publication transactions / Typed frontend, admin CLI and evaluator
- Local acceptance clause: Verify transaction and restart behaviour. Test duplicate requests, profile conflicts, stale job publication, release switches and DB failures on PostgreSQL. Confirm no half-published release, orphan success or overwritten answer.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_account_feedback_contention.py](<../../../tests/integration/test_account_feedback_contention.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>), [tests/integration/test_operations.py](<../../../tests/integration/test_operations.py>), [tests/unit/test_error_log_safety.py](<../../../tests/unit/test_error_log_safety.py>)
- Recorded current check nodes: `["tests.integration.test_account_feedback_contention::test_concurrent_account_creation_returns_conflict_without_partial_profile", "tests.integration.test_account_feedback_contention::test_concurrent_first_feedback_save_reuses_one_record_and_keeps_review_editable", "tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.integration.test_operations::test_cleanup_dry_run_and_apply_preserve_referenced_bytes", "tests.integration.test_operations::test_cleanup_rejects_changed_file_and_root_escape", "tests.integration.test_operations::test_operator_cli_uses_real_database_and_secret_environment", "tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_error_log_safety::test_unexpected_database_error_omits_sql_parameters_and_exception_chain"]`
- Acceptance references: [AC-02](<../acceptance.md#ac-02>), [AC-12](<../acceptance.md#ac-12>), [AC-13](<../acceptance.md#ac-13>), [AC-24](<../acceptance.md#ac-24>), [AC-26](<../acceptance.md#ac-26>), [AC-45](<../acceptance.md#ac-45>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [evidence/recovery/docker-interruption-20260908.json](<../../../evidence/recovery/docker-interruption-20260908.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current PostgreSQL integration tests exercise owned accounts/sessions/profiles, credential revocation, optimistic conflicts, concurrent feedback/account creation, durable jobs/cancellation, safe error logging and atomic failure publication. Mock/live capabilities remain separate.
- Unresolved scope: Provider execution is simulated where fault injection is required; actual external exactly-once execution is not promised.
- Blockers: None recorded.
- Mapping limitation: Provider execution is simulated where fault injection is required; actual external exactly-once execution is not promised.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current PostgreSQL integration tests exercise owned accounts/sessions/profiles, credential revocation, optimistic conflicts, concurrent feedback/account creation, durable jobs/cancellation, safe error logging and atomic failure publication. Mock/live capabilities remain separate.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [evidence/recovery/docker-interruption-20260908.json](<../../../evidence/recovery/docker-interruption-20260908.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Provider execution is simulated where fault injection is required; actual external exactly-once execution is not promised.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## BE-16

Deliver local deployment and restore. Implement actual Compose setup, migrations and local DB/asset backup/restore with documented targets. Test recovery in a disposable environment; public hosting automation is not mandatory.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 11, "suggested_project_week": 9, "suggested_start_course_week": 10, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G8
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-15", "QA-13"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-15"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-13"}]`
- Upstream collaborators (derived from those dependencies): [BE-15](<../by_owner/zeping-liao.md#be-15>) — Zeping Liao; [QA-13](<../by_owner/chong-zhang.md#qa-13>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [INT-09](<../by_owner/xianshu-zhang.md#int-09>) — Xianshu Zhang; [BE-17](<../by_owner/zeping-liao.md#be-17>) — Zeping Liao; [QA-14](<../by_owner/chong-zhang.md#qa-14>) — Chong Zhang; [CHAT-12](<../by_owner/xianshu-zhang.md#chat-12>) — Xianshu Zhang
- Source files recorded for this implementation: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Changed files recorded by the ledger: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Shared entry / interface boundary: Versioned API and operator CLI / Application services and worker
- Persisted effect / consumer: Relational entities and publication transactions / Typed frontend, admin CLI and evaluator
- Local acceptance clause: Deliver local deployment and restore. Implement actual Compose setup, migrations and local DB/asset backup/restore with documented targets. Test recovery in a disposable environment; public hosting automation is not mandatory.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>), [tests/integration/test_operations.py](<../../../tests/integration/test_operations.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-01](<../acceptance.md#ac-01>), [AC-20](<../acceptance.md#ac-20>), [AC-26](<../acceptance.md#ac-26>), [AC-33](<../acceptance.md#ac-33>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/recovery/backup-final-comparisons-20260908/restore-cs30_restore_final_all_20260908.json](<../../../evidence/recovery/backup-final-comparisons-20260908/restore-cs30_restore_final_all_20260908.json>), [evidence/e5-container/runtime-verification.json](<../../../evidence/e5-container/runtime-verification.json>), [docs/runbook.md](<../../runbook.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Base Compose startup and a complete backup-v2 portable restore executed. Actual E5 Linux/CUDA queries on the restored database match Windows chunk IDs and passages; original files, supplement hashes and snapshot identities were verified.
- Unresolved scope: This is local point-in-time recovery, not a disaster-recovery or availability certification; final package checks are separate.
- Blockers: None recorded.
- Mapping limitation: This is local point-in-time recovery, not a disaster-recovery or availability certification; final package checks are separate.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Base Compose startup and a complete backup-v2 portable restore executed. Actual E5 Linux/CUDA queries on the restored database match Windows chunk IDs and passages; original files, supplement hashes and snapshot identities were verified.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/recovery/backup-final-comparisons-20260908/restore-cs30_restore_final_all_20260908.json](<../../../evidence/recovery/backup-final-comparisons-20260908/restore-cs30_restore_final_all_20260908.json>), [evidence/e5-container/runtime-verification.json](<../../../evidence/e5-container/runtime-verification.json>), [docs/runbook.md](<../../runbook.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. This is local point-in-time recovery, not a disaster-recovery or availability certification; final package checks are separate.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-10

Support and analyse blind profile review. Generate/reconcile C0–C2 outputs, randomised review sheets and actual independent ratings. Keep missing ratings unavailable and analyse by paired question, not independent repeated students.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 11, "suggested_project_week": 9, "suggested_start_course_week": 10, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G7
- Current status: `WAITING_EXTERNAL`
- Separate implementation / verification / research / human-review states: `WAITING_EXTERNAL` / `WAITING_EXTERNAL` / `WAITING_EXTERNAL` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["PER-06", "PER-08", "QA-04"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-04"}]`
- Upstream collaborators (derived from those dependencies): [PER-06](<../by_owner/pengyuan-xia.md#per-06>) — Pengyuan Xia; [PER-08](<../by_owner/pengyuan-xia.md#per-08>) — Pengyuan Xia; [QA-04](<../by_owner/chong-zhang.md#qa-04>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [PER-09](<../by_owner/pengyuan-xia.md#per-09>) — Pengyuan Xia; [QA-14](<../by_owner/chong-zhang.md#qa-14>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Support and analyse blind profile review. Generate/reconcile C0–C2 outputs, randomised review sheets and actual independent ratings. Keep missing ratings unavailable and analyse by paired question, not independent repeated students.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_evaluation_annotations.py](<../../../tests/unit/test_evaluation_annotations.py>), [tests/unit/test_evaluation_study.py](<../../../tests/unit/test_evaluation_study.py>)
- Recorded current check nodes: `["tests.unit.test_evaluation_annotations::test_qrels_require_actual_review_identity_and_frozen_sources", "tests.unit.test_evaluation_annotations::test_blinding_hides_conditions_and_retains_all_nine_items", "tests.unit.test_evaluation_annotations::test_missing_ratings_remain_null_and_pairs_use_questions", "tests.unit.test_evaluation_annotations::test_duplicate_and_failed_output_ratings_are_rejected", "tests.unit.test_evaluation_annotations::test_controlled_comparisons_reject_test_tuning_and_multiple_changes", "tests.unit.test_evaluation_annotations::test_twelve_authored_families_fit_composer_without_private_claims", "tests.unit.test_evaluation_annotations::test_conversation_profile_off_keeps_session_and_new_chat_is_distinct", "tests.unit.test_evaluation_study::test_shared_mock_study_freezes_nine_conditions_and_resumes_without_repeating", "tests.unit.test_evaluation_study::test_interrupted_study_call_is_not_silently_repeated", "tests.unit.test_evaluation_study::test_study_rejects_live_mode_and_mutated_frozen_inputs", "tests.unit.test_evaluation_study::test_study_prompt_or_rubric_environment_change_stops_remaining_calls"]`
- Acceptance references: [AC-19](<../acceptance.md#ac-19>), [AC-29](<../acceptance.md#ac-29>), [AC-47](<../acceptance.md#ac-47>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/blockers.json](<../../execution/blockers.json>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Required independent evaluation protocols, annotation/rating tooling and null-safe reports are implemented; input requirements and unavailable results are explicitly recorded.
- Unresolved scope: Independent relevance/human judgments or user-deferred real answering outputs are missing. No real paired teaching findings or learning gains are claimed.
- Blockers: None recorded.
- Mapping limitation: Independent relevance/human judgments or user-deferred real answering outputs are missing. No real paired teaching findings or learning gains are claimed.

Recorded component observations:

- observed task scope: `WAITING_EXTERNAL`. Required independent evaluation protocols, annotation/rating tooling and null-safe reports are implemented; input requirements and unavailable results are explicitly recorded.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/blockers.json](<../../execution/blockers.json>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Independent relevance/human judgments or user-deferred real answering outputs are missing. No real paired teaching findings or learning gains are claimed.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-11

Run focused negative and fault tests. Test ownership/input rejection, invalid output/citations, provider timeout, job interruption and DB failure. Stay within the local project; enterprise security or chaos platforms are not required.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 11, "suggested_project_week": 9, "suggested_start_course_week": 10, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G8
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-13", "GEN-06", "RET-06"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-13"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-06"}]`
- Upstream collaborators (derived from those dependencies): [BE-13](<../by_owner/zeping-liao.md#be-13>) — Zeping Liao; [GEN-06](<../by_owner/sijin-lu.md#gen-06>) — Sijin Lu; [RET-06](<../by_owner/chengzhou-liu.md#ret-06>) — Chengzhou Liu
- Downstream collaborators (reverse dependency references): [INT-09](<../by_owner/xianshu-zhang.md#int-09>) — Xianshu Zhang; [GEN-11](<../by_owner/sijin-lu.md#gen-11>) — Sijin Lu; [BE-15](<../by_owner/zeping-liao.md#be-15>) — Zeping Liao; [QA-14](<../by_owner/chong-zhang.md#qa-14>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Run focused negative and fault tests. Test ownership/input rejection, invalid output/citations, provider timeout, job interruption and DB failure. Stay within the local project; enterprise security or chaos platforms are not required.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>), [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_corpus_runtime.py](<../../../tests/integration/test_corpus_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.integration.test_corpus_runtime::test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "tests.integration.test_corpus_runtime::test_quarantine_inspectable_exclusion_and_processing_lineage", "tests.integration.test_corpus_runtime::test_reprocessing_creates_new_chunks_while_old_evidence_survives", "tests.integration.test_corpus_runtime::test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "tests.integration.test_corpus_runtime::test_processing_diff_reports_split_groups_by_overlapping_source_spans", "tests.integration.test_corpus_runtime::test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "tests.integration.test_corpus_runtime::test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "tests.integration.test_corpus_runtime::test_source_deactivation_filters_current_retrieval_and_restore_recovers", "tests.integration.test_corpus_runtime::test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks", "tests.integration.test_corpus_runtime::test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "tests.integration.test_corpus_runtime::test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest", "tests.integration.test_corpus_runtime::test_legacy_release_without_saved_hashes_requires_explicit_new_build", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[cancel]", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[recover]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[cancel]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[recover]", "tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked"]`
- Acceptance references: [AC-03](<../acceptance.md#ac-03>), [AC-10](<../acceptance.md#ac-10>), [AC-11](<../acceptance.md#ac-11>), [AC-12](<../acceptance.md#ac-12>), [AC-13](<../acceptance.md#ac-13>), [AC-14](<../acceptance.md#ac-14>), [AC-24](<../acceptance.md#ac-24>), [AC-25](<../acceptance.md#ac-25>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current PostgreSQL/provider fault tests verify persistent retry and regeneration budgets, late-result fencing, cancellation, atomic DB failure, latest-answer revision and original feedback/evidence preservation.
- Unresolved scope: Provider failures are deliberately simulated. Current actual-corpus browser/API revision checks provide separate end-to-end evidence.
- Blockers: None recorded.
- Mapping limitation: Provider failures are deliberately simulated. Current actual-corpus browser/API revision checks provide separate end-to-end evidence.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Current PostgreSQL/provider fault tests verify persistent retry and regeneration budgets, late-result fencing, cancellation, atomic DB failure, latest-answer revision and original feedback/evidence preservation.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Provider failures are deliberately simulated. Current actual-corpus browser/API revision checks provide separate end-to-end evidence.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-12

Accept all connected chat and evaluation journeys. Exercise J1–J6 with actual API/DB/worker/browser and labelled mock/live runs; assert message, active revision, conversation/profile/evidence snapshots and product operation without SciQ. Include the dedicated multi-turn scenarios and user recovery actions.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 11, "suggested_project_week": 9, "suggested_start_course_week": 10, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G8
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-06", "FE-08", "FE-09", "FE-10", "FE-11", "FE-07", "PER-05", "GEN-09", "CHAT-10", "CHAT-11"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-10"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-11"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-10"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-11"}]`
- Upstream collaborators (derived from those dependencies): [FE-06](<../by_owner/baiqing-huang.md#fe-06>) — Baiqing Huang; [FE-08](<../by_owner/baiqing-huang.md#fe-08>) — Baiqing Huang; [FE-09](<../by_owner/baiqing-huang.md#fe-09>) — Baiqing Huang; [FE-10](<../by_owner/baiqing-huang.md#fe-10>) — Baiqing Huang; [FE-11](<../by_owner/baiqing-huang.md#fe-11>) — Baiqing Huang; [FE-07](<../by_owner/baiqing-huang.md#fe-07>) — Baiqing Huang; [PER-05](<../by_owner/pengyuan-xia.md#per-05>) — Pengyuan Xia; [GEN-09](<../by_owner/sijin-lu.md#gen-09>) — Sijin Lu; [CHAT-10](<../by_owner/chong-zhang.md#chat-10>) — Chong Zhang; [CHAT-11](<../by_owner/xianshu-zhang.md#chat-11>) — Xianshu Zhang
- Downstream collaborators (reverse dependency references): [FE-12](<../by_owner/baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-14](<../by_owner/chong-zhang.md#qa-14>) — Chong Zhang; [CHAT-12](<../by_owner/xianshu-zhang.md#chat-12>) — Xianshu Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Accept all connected chat and evaluation journeys. Exercise J1–J6 with actual API/DB/worker/browser and labelled mock/live runs; assert message, active revision, conversation/profile/evidence snapshots and product operation without SciQ. Include the dedicated multi-turn scenarios and user recovery actions.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>), [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_teaching_api_nine_matched_jobs_and_blind_export_without_chat_mutation", "tests.integration.test_evaluation_postgres::test_postgres_teaching_cancel_keeps_success_and_all_scheduled_outcomes", "tests.integration.test_evaluation_postgres::test_postgres_teaching_late_source_revocation_discards_publication", "tests.integration.test_evaluation_postgres::test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result", "tests.integration.test_evaluation_postgres::test_postgres_all_twelve_authored_scenario_families_use_real_chat_api"]`
- Acceptance references: [AC-08](<../acceptance.md#ac-08>), [AC-16](<../acceptance.md#ac-16>), [AC-30](<../acceptance.md#ac-30>), [AC-37](<../acceptance.md#ac-37>), [AC-38](<../acceptance.md#ac-38>), [AC-39](<../acceptance.md#ac-39>), [AC-40](<../acceptance.md#ac-40>), [AC-41](<../acceptance.md#ac-41>), [AC-42](<../acceptance.md#ac-42>), [AC-43](<../acceptance.md#ac-43>), [AC-44](<../acceptance.md#ac-44>), [AC-45](<../acceptance.md#ac-45>), [AC-48](<../acceptance.md#ac-48>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Actual API/DB/worker/browser journeys and all 12 authored conversation families exercise the connected product; actual-source chat and separate benchmark software protocols use the shared service.
- Unresolved scope: Mock answer semantic limits, live evaluation and physical-device review remain explicit.
- Blockers: None recorded.
- Mapping limitation: Mock answer semantic limits, live evaluation and physical-device review remain explicit.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Actual API/DB/worker/browser journeys and all 12 authored conversation families exercise the connected product; actual-source chat and separate benchmark software protocols use the shared service.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Mock answer semantic limits, live evaluation and physical-device review remain explicit.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-13

Measure actual chat and evaluation performance separately. Record environment/corpus/concurrency, preparation/retrieval/generation/total p50/p95, failures and actual usage. Do not report a one-turn MCQ timing as multi-turn chat latency; unknown cost remains null.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 11, "suggested_project_week": 9, "suggested_start_course_week": 10, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G8
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-08", "QA-06"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-06"}]`
- Upstream collaborators (derived from those dependencies): [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao; [QA-06](<../by_owner/chong-zhang.md#qa-06>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [BE-16](<../by_owner/zeping-liao.md#be-16>) — Zeping Liao; [QA-14](<../by_owner/chong-zhang.md#qa-14>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Measure actual chat and evaluation performance separately. Record environment/corpus/concurrency, preparation/retrieval/generation/total p50/p95, failures and actual usage. Do not report a one-turn MCQ timing as multi-turn chat latency; unknown cost remains null.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_evaluation_metrics.py](<../../../tests/unit/test_evaluation_metrics.py>), [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-11](<../acceptance.md#ac-11>), [AC-25](<../acceptance.md#ac-25>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/performance.md](<../../performance.md>), [evidence/performance/chat-two-sessions.json](<../../../evidence/performance/chat-two-sessions.json>), [evidence/sciq/technical-rehearsal.json](<../../../evidence/sciq/technical-rehearsal.json>), [evidence/sciq/technical-timing-summary.json](<../../../evidence/sciq/technical-timing-summary.json>), [evidence/evaluation/preparation-timing-correction.json](<../../../evidence/evaluation/preparation-timing-correction.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Actual local chat and separate evaluation/retrieval workload timings retain environment, corpus, scheduled counts, failures, response types and unknown cost. Preparation/retrieval/generation wall time and adapter-measured latency are distinguished.
- Unresolved scope: Small-sample local descriptive timings are not an SLA or real-provider latency/cost estimate.
- Blockers: None recorded.
- Mapping limitation: Small-sample local descriptive timings are not an SLA or real-provider latency/cost estimate.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Actual local chat and separate evaluation/retrieval workload timings retain environment, corpus, scheduled counts, failures, response types and unknown cost. Preparation/retrieval/generation wall time and adapter-measured latency are distinguished.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/performance.md](<../../performance.md>), [evidence/performance/chat-two-sessions.json](<../../../evidence/performance/chat-two-sessions.json>), [evidence/sciq/technical-rehearsal.json](<../../../evidence/sciq/technical-rehearsal.json>), [evidence/sciq/technical-timing-summary.json](<../../../evidence/sciq/technical-timing-summary.json>), [evidence/evaluation/preparation-timing-correction.json](<../../../evidence/evaluation/preparation-timing-correction.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Small-sample local descriptive timings are not an SLA or real-provider latency/cost estimate.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## CHAT-11

Audit old-to-new compatibility and every active instruction. Implement scripts/verify/chat_scope.py; preserve legacy MCQ rows and response types while removing required choices and display-only history from chat. Confirm task/dependency/schema/UI/export consistency with the three-mode architecture.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 11, "suggested_project_week": 9, "suggested_start_course_week": 10, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G8
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["CHAT-09", "CHAT-10", "BE-14", "FE-11"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-10"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-14"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-11"}]`
- Upstream collaborators (derived from those dependencies): [CHAT-09](<../by_owner/chong-zhang.md#chat-09>) — Chong Zhang; [CHAT-10](<../by_owner/chong-zhang.md#chat-10>) — Chong Zhang; [BE-14](<../by_owner/zeping-liao.md#be-14>) — Zeping Liao; [FE-11](<../by_owner/baiqing-huang.md#fe-11>) — Baiqing Huang
- Downstream collaborators (reverse dependency references): [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-12](<../by_owner/xianshu-zhang.md#chat-12>) — Xianshu Zhang
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Audit old-to-new compatibility and every active instruction. Implement scripts/verify/chat_scope.py; preserve legacy MCQ rows and response types while removing required choices and display-only history from chat. Confirm task/dependency/schema/UI/export consistency with the three-mode architecture.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_legacy_mcq_migration.py](<../../../tests/integration/test_legacy_mcq_migration.py>)
- Recorded current check nodes: `["tests.integration.test_legacy_mcq_migration::test_initial_data_and_typed_mcq_survive_additive_migrations"]`
- Acceptance references: [AC-21](<../acceptance.md#ac-21>), [AC-36](<../acceptance.md#ac-36>), [AC-37](<../acceptance.md#ac-37>), [AC-48](<../acceptance.md#ac-48>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/contracts/verification.json](<../../../evidence/contracts/verification.json>), [evidence/contracts/chat_scope.json](<../../../evidence/contracts/chat_scope.json>), [evidence/integration/migration-logging-order.log](<../../../evidence/integration/migration-logging-order.log>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current contract/schema/client and chat-scope checks passed; the PostgreSQL upgrade preserved typed old MCQ history, citations and identity. Natural chat retains its two-field input and evaluator-independent context.
- Unresolved scope: None recorded.
- Blockers: None recorded.
- Mapping limitation: None recorded.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current contract/schema/client and chat-scope checks passed; the PostgreSQL upgrade preserved typed old MCQ history, citations and identity. Natural chat retains its two-field input and evaluator-independent context.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/contracts/verification.json](<../../../evidence/contracts/verification.json>), [evidence/contracts/chat_scope.json](<../../../evidence/contracts/chat_scope.json>), [evidence/integration/migration-logging-order.log](<../../../evidence/integration/migration-logging-order.log>)
- remaining acceptance scope: `REAL_FLOW_VERIFIED`. No additional task-specific software gap identified; independent overall acceptance is not inferred.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.
