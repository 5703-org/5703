# Delivery view: suggested course week 8

Generated reporting view. The canonical ledgers below remain authoritative; this file adds no product requirement or acceptance decision.

Accountable owner and suggested course week are reporting metadata, never permissions, implementation eligibility, runtime flags or evidence of completion. Actual executor and recorded dates are shown separately. Cross-references do not count a task more than once. No calendar dates or completion percentages are inferred.

Canonical requirements, shared interfaces and evidence: [PRD.md](<../../../PRD.md>) · [SPEC.md](<../../../SPEC.md>) · [PLANS.md](<../../../PLANS.md>) · [HANDOVER.md](<../../../HANDOVER.md>) · [docs/foundation/api_contract.md](<../../foundation/api_contract.md>) · [contracts/openapi.json](<../../../contracts/openapi.json>) · [docs/execution/tasks.json](<../../execution/tasks.json>) · [docs/execution/reporting_plan.json](<../../execution/reporting_plan.json>) · [docs/execution/acceptance.json](<../../execution/acceptance.json>)

Task-ledger reconciliation timestamp (not a completion date): 2026-09-08T10:09:00.459775+00:00

This primary reporting bucket contains 7 unique tasks. A task's canonical suggested week chooses its one primary bucket. The planning packages below can mention it in other weeks as a cross-reference; these references add no completed tasks.

## Suggested allocation only

Suggested team reporting allocation only, not execution schedule, deadline or actual completion evidence.

Week convention: Course/teaching week; project_week=course_week-2 from Week 3. Optional contingency only; official dates/deadlines not confirmed

### Xianshu Zhang — suggested package

Freeze protocols, manifests, configurations and reporting; continue fixing chat defects without replacing product acceptance with scores.

- Task cross-references: [INT-07](<../by_owner/xianshu-zhang.md#int-07>), [INT-08](<../by_owner/xianshu-zhang.md#int-08>)
- Suggested deliverable paths (not claims of delivery): `docs/baseline_freeze.md` (path absent), `docs/execution/week_08.md` (path absent)
- Suggested downstream consumers: Chong Zhang; Sijin Lu; Chengzhou Liu
- Planned acceptance description: OpenQA/MCQ directories and denominators are separate; unrun studies remain blocked, not passed.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Hongle Yang — suggested package

Verify available SciQ revision/splits/hashes and corpus manifests; provide source locators for annotation.

- Task cross-references: [DAT-09](<../by_owner/hongle-yang.md#dat-09>), [DAT-08](<../by_owner/hongle-yang.md#dat-08>)
- Suggested deliverable paths (not claims of delivery): [evaluation/datasets/](<../../../evaluation/datasets>), `artifacts/manifests/` (path absent)
- Suggested downstream consumers: Chong Zhang; Chengzhou Liu
- Planned acceptance description: System-visible exports contain only protocol fields; support is absent from the textbook index.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Chengzhou Liu — suggested package

Stabilise R0 traces and review source coverage; implement R1 in parallel without changing frozen E1.

- Task cross-references: [RET-04](<../by_owner/chengzhou-liu.md#ret-04>), [RET-05](<../by_owner/chengzhou-liu.md#ret-05>), [RET-07](<../by_owner/chengzhou-liu.md#ret-07>)
- Suggested deliverable paths (not claims of delivery): `retrieval/tracing.py` (path absent), `retrieval/bm25.py` (path absent)
- Suggested downstream consumers: Chong Zhang; Sijin Lu
- Planned acceptance description: The same release reproduces candidate order; a retrieval miss alone does not prove absent source coverage.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Sijin Lu — suggested package

Connect OpenQA/MCQ contracts and actual provider metadata to the formal runner; run a separate live smoke when configured and authorised.

- Task cross-references: [GEN-08](<../by_owner/sijin-lu.md#gen-08>), [GEN-10](<../by_owner/sijin-lu.md#gen-10>), [GEN-11](<../by_owner/sijin-lu.md#gen-11>)
- Suggested deliverable paths (not claims of delivery): `generation/benchmark_context.py` (path absent), `configs/models/` (path absent)
- Suggested downstream consumers: Chong Zhang; Zeping Liao
- Planned acceptance description: Inputs/settings are comparable; examples do not select a verified model; preserve the historical probe.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Pengyuan Xia — suggested package

Recheck product profiles; prepare rating templates and fixed-level cases without delaying already-required chat features.

- Task cross-references: [PER-08](<../by_owner/pengyuan-xia.md#per-08>), [PER-05](<../by_owner/pengyuan-xia.md#per-05>)
- Suggested deliverable paths (not claims of delivery): `personalisation/rubric/` (path absent), `docs/user_profiles.md` (path absent)
- Suggested downstream consumers: Chong Zhang; Sijin Lu
- Planned acceptance description: Baseline inputs exclude profiles while normal chat retains them; rating templates contain no fabricated scores.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Zeping Liao — suggested package

Implement experiment runs/items, freeze/cancel/resume/export through shared AnswerExecutionService without fake learner sessions.

- Task cross-references: [BE-11](<../by_owner/zeping-liao.md#be-11>), [BE-12](<../by_owner/zeping-liao.md#be-12>)
- Suggested deliverable paths (not claims of delivery): `backend/app/modules/experiments/` (path absent), `evaluation/runner/` (path absent)
- Suggested downstream consumers: Chong Zhang; Baiqing Huang
- Planned acceptance description: All scheduled items retain outcomes; stopping the evaluator does not affect chat_ready.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Baiqing Huang — suggested package

Build secondary admin evaluation/results views showing protocol, mock/live and failure counts; continue chat UX fixes.

- Task cross-references: [FE-11](<../by_owner/baiqing-huang.md#fe-11>), [FE-08](<../by_owner/baiqing-huang.md#fe-08>)
- Suggested deliverable paths (not claims of delivery): `frontend/src/features/admin/experiments/` (path absent)
- Suggested downstream consumers: Chong Zhang; Zeping Liao
- Planned acceptance description: Learner landing remains /chat; exports use actual server records, not invented frontend metrics.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Chong Zhang — suggested package

Freeze coverage review and run manifests; execute E0/E1 or record blockers, separately calculating EM/F1, MCQ and semantic review.

- Task cross-references: [QA-04](<../by_owner/chong-zhang.md#qa-04>), [QA-06](<../by_owner/chong-zhang.md#qa-06>), [CHAT-09](<../by_owner/chong-zhang.md#chat-09>), [QA-07](<../by_owner/chong-zhang.md#qa-07>), [QA-08](<../by_owner/chong-zhang.md#qa-08>)
- Suggested deliverable paths (not claims of delivery): `evaluation/runner/` (path absent), [evaluation/analysis/](<../../../evaluation/analysis>), [artifacts/runs/](<../../../artifacts/runs>)
- Suggested downstream consumers: Xianshu Zhang; all workstreams
- Planned acceptance description: Failures/refusals remain in N; aliases/references never enter generation; HC-12 and denominator fixtures pass.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

## Actual evidence and demonstration material

The task records below quote the current ledger, independently of the suggested package. Their actual evidence links are the available demonstration and check material; an empty or null field stays unrecorded. The export does not create a meeting, human demonstration or historical completion event.

## Carry-over and unresolved work

These are currently recorded unresolved items for this reporting bucket, not claims that a calendar week elapsed or work was late.

- [INT-08](<../by_owner/xianshu-zhang.md#int-08>) (`MOCK_TEST_PASSED`): Formal live baseline scores and independent ratings remain pending. Blockers: None recorded.
- [BE-11](<../by_owner/zeping-liao.md#be-11>) (`MOCK_TEST_PASSED`): Formal live baseline scores and independent ratings remain pending. Blockers: None recorded.
- [QA-04](<../by_owner/chong-zhang.md#qa-04>) (`IMPLEMENTED_UNVERIFIED`): Independent source judgments remain absent. R1/R2/R3 existed before this pool; the originally requested pre-R1 chronology was not achieved and is not backdated. The v4 pool cannot be reused for v5/fixed chunks without a new compatibility review. Blockers: None recorded.
- [QA-06](<../by_owner/chong-zhang.md#qa-06>) (`MOCK_TEST_PASSED`): The four-row technical prefix is not a formal benchmark. User-deferred live answering and the full-split MCQ input anomalies remain explicit; no successful calls or private historical outputs were rewritten. Blockers: None recorded.
- [QA-07](<../by_owner/chong-zhang.md#qa-07>) (`WAITING_EXTERNAL`): Independent relevance/human judgments or user-deferred real answering outputs are missing. No real paired teaching findings or learning gains are claimed. Blockers: None recorded.
- [QA-08](<../by_owner/chong-zhang.md#qa-08>) (`MOCK_TEST_PASSED`): Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings. Blockers: None recorded.
- [CHAT-09](<../by_owner/chong-zhang.md#chat-09>) (`MOCK_TEST_PASSED`): Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings. Blockers: None recorded.

## INT-08

Freeze evaluation protocols reproducibly. Record separate open-answer and MCQ manifests, model/prompt/corpus and scorer versions. Preserve a technical rehearsal separately from actual live results; no freeze gate may block the already independent chat product.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 8, "suggested_project_week": 6, "suggested_start_course_week": 7, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G5
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["QA-07", "CHAT-09", "INT-07"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-07"}]`
- Upstream collaborators (derived from those dependencies): [QA-07](<../by_owner/chong-zhang.md#qa-07>) — Chong Zhang; [CHAT-09](<../by_owner/chong-zhang.md#chat-09>) — Chong Zhang; [INT-07](<../by_owner/xianshu-zhang.md#int-07>) — Xianshu Zhang
- Downstream collaborators (reverse dependency references): None recorded.
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Freeze evaluation protocols reproducibly. Record separate open-answer and MCQ manifests, model/prompt/corpus and scorer versions. Preserve a technical rehearsal separately from actual live results; no freeze gate may block the already independent chat product.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: `["tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_teaching_api_nine_matched_jobs_and_blind_export_without_chat_mutation", "tests.integration.test_evaluation_postgres::test_postgres_teaching_cancel_keeps_success_and_all_scheduled_outcomes", "tests.integration.test_evaluation_postgres::test_postgres_teaching_late_source_revocation_discards_publication", "tests.integration.test_evaluation_postgres::test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result", "tests.integration.test_evaluation_postgres::test_postgres_all_twelve_authored_scenario_families_use_real_chat_api"]`
- Acceptance references: [AC-18](<../acceptance.md#ac-18>), [AC-19](<../acceptance.md#ac-19>), [AC-22](<../acceptance.md#ac-22>), [AC-46](<../acceptance.md#ac-46>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Frozen protocols, immutable public commands, evaluator-private references, all-outcome registration/resume and independent teaching jobs passed actual PostgreSQL integration checks.
- Unresolved scope: Formal live baseline scores and independent ratings remain pending.
- Blockers: None recorded.
- Mapping limitation: Formal live baseline scores and independent ratings remain pending.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Frozen protocols, immutable public commands, evaluator-private references, all-outcome registration/resume and independent teaching jobs passed actual PostgreSQL integration checks.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Formal live baseline scores and independent ratings remain pending.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## BE-11

Implement independent experiment persistence. Freeze protocol/mode/configuration and preregister items for open-answer, MCQ and profile studies. Isolate evaluator-only labels, submit through shared answer components, and export all outcomes; chat can run with the evaluator absent.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 8, "suggested_project_week": 6, "suggested_start_course_week": 7, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G5
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-07", "BE-09", "QA-02", "BE-08"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-08"}]`
- Upstream collaborators (derived from those dependencies): [BE-07](<../by_owner/zeping-liao.md#be-07>) — Zeping Liao; [BE-09](<../by_owner/zeping-liao.md#be-09>) — Zeping Liao; [QA-02](<../by_owner/chong-zhang.md#qa-02>) — Chong Zhang; [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-11](<../by_owner/baiqing-huang.md#fe-11>) — Baiqing Huang; [QA-06](<../by_owner/chong-zhang.md#qa-06>) — Chong Zhang
- Source files recorded for this implementation: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Changed files recorded by the ledger: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Shared entry / interface boundary: Versioned API and operator CLI / Application services and worker
- Persisted effect / consumer: Relational entities and publication transactions / Typed frontend, admin CLI and evaluator
- Local acceptance clause: Implement independent experiment persistence. Freeze protocol/mode/configuration and preregister items for open-answer, MCQ and profile studies. Isolate evaluator-only labels, submit through shared answer components, and export all outcomes; chat can run with the evaluator absent.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: `["tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_teaching_api_nine_matched_jobs_and_blind_export_without_chat_mutation", "tests.integration.test_evaluation_postgres::test_postgres_teaching_cancel_keeps_success_and_all_scheduled_outcomes", "tests.integration.test_evaluation_postgres::test_postgres_teaching_late_source_revocation_discards_publication", "tests.integration.test_evaluation_postgres::test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result", "tests.integration.test_evaluation_postgres::test_postgres_all_twelve_authored_scenario_families_use_real_chat_api"]`
- Acceptance references: [AC-18](<../acceptance.md#ac-18>), [AC-19](<../acceptance.md#ac-19>), [AC-22](<../acceptance.md#ac-22>), [AC-23](<../acceptance.md#ac-23>), [AC-27](<../acceptance.md#ac-27>), [AC-46](<../acceptance.md#ac-46>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Frozen protocols, immutable public commands, evaluator-private references, all-outcome registration/resume and independent teaching jobs passed actual PostgreSQL integration checks.
- Unresolved scope: Formal live baseline scores and independent ratings remain pending.
- Blockers: None recorded.
- Mapping limitation: Formal live baseline scores and independent ratings remain pending.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Frozen protocols, immutable public commands, evaluator-private references, all-outcome registration/resume and independent teaching jobs passed actual PostgreSQL integration checks.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Formal live baseline scores and independent ratings remain pending.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-04

Create versioned evidence annotations. Prepare source-coverage/qrel review using frozen R0 and manual source inspection before R1 exists. Keep unresolved labels null and version any later expanded judged pool.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 8, "suggested_project_week": 6, "suggested_start_course_week": 7, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G5
- Current status: `IMPLEMENTED_UNVERIFIED`
- Separate implementation / verification / research / human-review states: `IMPLEMENTED_UNVERIFIED` / `IMPLEMENTED_UNVERIFIED` / `WAITING_EXTERNAL` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["DAT-08", "RET-05", "QA-02"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "DAT-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-02"}]`
- Upstream collaborators (derived from those dependencies): [DAT-08](<../by_owner/hongle-yang.md#dat-08>) — Hongle Yang; [RET-05](<../by_owner/chengzhou-liu.md#ret-05>) — Chengzhou Liu; [QA-02](<../by_owner/chong-zhang.md#qa-02>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [DAT-11](<../by_owner/hongle-yang.md#dat-11>) — Hongle Yang; [QA-08](<../by_owner/chong-zhang.md#qa-08>) — Chong Zhang; [QA-10](<../by_owner/chong-zhang.md#qa-10>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Create versioned evidence annotations. Prepare source-coverage/qrel review using frozen R0 and manual source inspection before R1 exists. Keep unresolved labels null and version any later expanded judged pool.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_evaluation_annotations.py](<../../../tests/unit/test_evaluation_annotations.py>)
- Recorded current check nodes: `["tests.unit.test_evaluation_annotations::test_qrels_require_actual_review_identity_and_frozen_sources", "tests.unit.test_evaluation_annotations::test_blinding_hides_conditions_and_retains_all_nine_items", "tests.unit.test_evaluation_annotations::test_missing_ratings_remain_null_and_pairs_use_questions", "tests.unit.test_evaluation_annotations::test_duplicate_and_failed_output_ratings_are_rejected", "tests.unit.test_evaluation_annotations::test_controlled_comparisons_reject_test_tuning_and_multiple_changes", "tests.unit.test_evaluation_annotations::test_twelve_authored_families_fit_composer_without_private_claims", "tests.unit.test_evaluation_annotations::test_conversation_profile_off_keeps_session_and_new_chat_is_distinct"]`
- Acceptance references: [AC-18](<../acceptance.md#ac-18>), [AC-19](<../acceptance.md#ac-19>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/r0_review_pool.md](<../../r0_review_pool.md>), [evidence/retrieval/r0-late-review-pool.json](<../../../evidence/retrieval/r0-late-review-pool.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: An actual late versioned R0 pool contains all 75 question/chunk pairs from 15 saved questions, verified by exact PostgreSQL source spans/hash/release membership. All grades/reviewer fields remain null, with original PDF/book/section/page locators provided for review.
- Unresolved scope: Independent source judgments remain absent. R1/R2/R3 existed before this pool; the originally requested pre-R1 chronology was not achieved and is not backdated. The v4 pool cannot be reused for v5/fixed chunks without a new compatibility review.
- Blockers: None recorded.
- Mapping limitation: Independent source judgments remain absent. R1/R2/R3 existed before this pool; the originally requested pre-R1 chronology was not achieved and is not backdated. The v4 pool cannot be reused for v5/fixed chunks without a new compatibility review.

Recorded component observations:

- observed task scope: `IMPLEMENTED_UNVERIFIED`. An actual late versioned R0 pool contains all 75 question/chunk pairs from 15 saved questions, verified by exact PostgreSQL source spans/hash/release membership. All grades/reviewer fields remain null, with original PDF/book/section/page locators provided for review.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/r0_review_pool.md](<../../r0_review_pool.md>), [evidence/retrieval/r0-late-review-pool.json](<../../../evidence/retrieval/r0-late-review-pool.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Independent source judgments remain absent. R1/R2/R3 existed before this pool; the originally requested pre-R1 chronology was not achieved and is not backdated. The v4 pool cannot be reused for v5/fixed chunks without a new compatibility review.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-06

Build a resumable offline evaluation runner. Register full protocol-specific manifests and submit through the shared engine; save all terminal outcomes, usage and separate exports. Resume pending work without duplicating successful calls. It is not the application’s normal question-entry loop.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 8, "suggested_project_week": 6, "suggested_start_course_week": 7, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G5
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["QA-05", "BE-11", "GEN-06"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-11"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-06"}]`
- Upstream collaborators (derived from those dependencies): [QA-05](<../by_owner/chong-zhang.md#qa-05>) — Chong Zhang; [BE-11](<../by_owner/zeping-liao.md#be-11>) — Zeping Liao; [GEN-06](<../by_owner/sijin-lu.md#gen-06>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [PER-06](<../by_owner/pengyuan-xia.md#per-06>) — Pengyuan Xia; [FE-11](<../by_owner/baiqing-huang.md#fe-11>) — Baiqing Huang; [QA-07](<../by_owner/chong-zhang.md#qa-07>) — Chong Zhang; [QA-13](<../by_owner/chong-zhang.md#qa-13>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Build a resumable offline evaluation runner. Register full protocol-specific manifests and submit through the shared engine; save all terminal outcomes, usage and separate exports. Resume pending work without duplicating successful calls. It is not the application’s normal question-entry loop.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_evaluation_runner.py](<../../../tests/unit/test_evaluation_runner.py>), [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>), [tests/unit/test_evaluation_outcome_timing.py](<../../../tests/unit/test_evaluation_outcome_timing.py>)
- Recorded current check nodes: `["tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_teaching_api_nine_matched_jobs_and_blind_export_without_chat_mutation", "tests.integration.test_evaluation_postgres::test_postgres_teaching_cancel_keeps_success_and_all_scheduled_outcomes", "tests.integration.test_evaluation_postgres::test_postgres_teaching_late_source_revocation_discards_publication", "tests.integration.test_evaluation_postgres::test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result", "tests.integration.test_evaluation_postgres::test_postgres_all_twelve_authored_scenario_families_use_real_chat_api", "tests.unit.test_evaluation_outcome_timing::test_persisted_item_outcome_preserves_authoritative_timing[measured-preparation-excludes-retrieval]", "tests.unit.test_evaluation_outcome_timing::test_persisted_item_outcome_preserves_authoritative_timing[measured-zero-is-not-missing]", "tests.unit.test_evaluation_outcome_timing::test_persisted_item_outcome_preserves_authoritative_timing[existing-unscoped-answer-value-is-preserved]", "tests.unit.test_evaluation_outcome_timing::test_persisted_item_outcome_preserves_authoritative_timing[legacy-missing-answer-value-has-labelled-fallback]", "tests.unit.test_evaluation_outcome_timing::test_persisted_item_outcome_preserves_authoritative_timing[unmeasured-legacy-value-stays-null]", "tests.unit.test_evaluation_outcome_timing::test_persisted_item_outcome_preserves_authoritative_timing[scoped-missing-value-is-not-an-aggregate]", "tests.unit.test_evaluation_outcome_timing::test_persisted_item_outcome_preserves_authoritative_timing[unknown-scoped-measurement-is-not-legacy]", "tests.unit.test_evaluation_runner::test_stem_projection_unchanged_when_private_labels_change", "tests.unit.test_evaluation_runner::test_mcq_shuffle_is_stable_symmetric_and_gold_stays_private", "tests.unit.test_evaluation_runner::test_duplicate_candidates_and_split_counts", "tests.unit.test_evaluation_runner::test_duplicate_source_choices_do_not_block_stem_only_openqa_freeze", "tests.unit.test_evaluation_runner::test_freeze_preregisters_and_resume_does_not_repeat_calls", "tests.unit.test_evaluation_runner::test_interrupted_submission_reconciles_receipt_without_new_call", "tests.unit.test_evaluation_runner::test_ambiguous_unrecorded_submission_never_automatically_repeats", "tests.unit.test_evaluation_runner::test_environment_change_stops_new_calls_preserves_scheduled_set", "tests.unit.test_evaluation_runner::test_tampered_manifest_or_private_reference_rejected", "tests.unit.test_evaluation_runner::test_cancelled_export_retains_denominator_and_has_no_private_reference", "tests.unit.test_evaluation_runner::test_live_defaults_and_e1_redefinition_are_rejected", "tests.unit.test_evaluation_runner::test_repeat_export_preserves_existing_independent_review", "tests.unit.test_evaluation_runner::test_malformed_shared_response_is_retained_as_invalid"]`
- Acceptance references: [AC-18](<../acceptance.md#ac-18>), [AC-19](<../acceptance.md#ac-19>), [AC-22](<../acceptance.md#ac-22>), [AC-23](<../acceptance.md#ac-23>), [HC-12](<../acceptance.md#hc-12>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/evaluator-timing-correction.md](<../../execution/evaluator-timing-correction.md>), [evidence/evaluation/preparation-timing-correction.json](<../../../evidence/evaluation/preparation-timing-correction.json>), [evidence/evaluation/restarted-api-timing-projection.json](<../../../evidence/evaluation/restarted-api-timing-projection.json>), [evidence/sciq/technical-rehearsal.json](<../../../evidence/sciq/technical-rehearsal.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: The resumable protocol runner and actual PostgreSQL experiment bridge retain every scheduled outcome, shared-engine requests and private/public export boundaries. The actual four-row SciQ technical rehearsal completed with mock answering. Measured preparation timing now survives export; seven focused regressions and read-only projection of all four actual answers verify the correction while earlier private exports remain unchanged.
- Unresolved scope: The four-row technical prefix is not a formal benchmark. User-deferred live answering and the full-split MCQ input anomalies remain explicit; no successful calls or private historical outputs were rewritten.
- Blockers: None recorded.
- Mapping limitation: The four-row technical prefix is not a formal benchmark. User-deferred live answering and the full-split MCQ input anomalies remain explicit; no successful calls or private historical outputs were rewritten.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. The resumable protocol runner and actual PostgreSQL experiment bridge retain every scheduled outcome, shared-engine requests and private/public export boundaries. The actual four-row SciQ technical rehearsal completed with mock answering. Measured preparation timing now survives export; seven focused regressions and read-only projection of all four actual answers verify the correction while earlier private exports remain unchanged.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/evaluator-timing-correction.md](<../../execution/evaluator-timing-correction.md>), [evidence/evaluation/preparation-timing-correction.json](<../../../evidence/evaluation/preparation-timing-correction.json>), [evidence/evaluation/restarted-api-timing-projection.json](<../../../evidence/evaluation/restarted-api-timing-projection.json>), [evidence/sciq/technical-rehearsal.json](<../../../evidence/sciq/technical-rehearsal.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. The four-row technical prefix is not a formal benchmark. User-deferred live answering and the full-split MCQ input anomalies remain explicit; no successful calls or private historical outputs were rewritten.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-07

Execute separated real baselines when configured. Freeze validation-selected open-answer and MCQ protocols with actual corpus/model settings. Use the implemented stem-only path for open answers and label MCQ diagnostics clearly. Missing live inputs block measurements, never normal chat development.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 8, "suggested_project_week": 6, "suggested_start_course_week": 7, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G5
- Current status: `WAITING_EXTERNAL`
- Separate implementation / verification / research / human-review states: `WAITING_EXTERNAL` / `WAITING_EXTERNAL` / `WAITING_EXTERNAL` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["QA-06", "QA-03", "GEN-08", "INT-06", "DAT-08", "CHAT-09"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-03"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "DAT-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-09"}]`
- Upstream collaborators (derived from those dependencies): [QA-06](<../by_owner/chong-zhang.md#qa-06>) — Chong Zhang; [QA-03](<../by_owner/chong-zhang.md#qa-03>) — Chong Zhang; [GEN-08](<../by_owner/sijin-lu.md#gen-08>) — Sijin Lu; [INT-06](<../by_owner/xianshu-zhang.md#int-06>) — Xianshu Zhang; [DAT-08](<../by_owner/hongle-yang.md#dat-08>) — Hongle Yang; [CHAT-09](<../by_owner/chong-zhang.md#chat-09>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [INT-08](<../by_owner/xianshu-zhang.md#int-08>) — Xianshu Zhang; [GEN-10](<../by_owner/sijin-lu.md#gen-10>) — Sijin Lu; [QA-08](<../by_owner/chong-zhang.md#qa-08>) — Chong Zhang; [QA-09](<../by_owner/chong-zhang.md#qa-09>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Execute separated real baselines when configured. Freeze validation-selected open-answer and MCQ protocols with actual corpus/model settings. Use the implemented stem-only path for open answers and label MCQ diagnostics clearly. Missing live inputs block measurements, never normal chat development.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_evaluation_annotations.py](<../../../tests/unit/test_evaluation_annotations.py>), [tests/unit/test_evaluation_study.py](<../../../tests/unit/test_evaluation_study.py>)
- Recorded current check nodes: `["tests.unit.test_evaluation_annotations::test_qrels_require_actual_review_identity_and_frozen_sources", "tests.unit.test_evaluation_annotations::test_blinding_hides_conditions_and_retains_all_nine_items", "tests.unit.test_evaluation_annotations::test_missing_ratings_remain_null_and_pairs_use_questions", "tests.unit.test_evaluation_annotations::test_duplicate_and_failed_output_ratings_are_rejected", "tests.unit.test_evaluation_annotations::test_controlled_comparisons_reject_test_tuning_and_multiple_changes", "tests.unit.test_evaluation_annotations::test_twelve_authored_families_fit_composer_without_private_claims", "tests.unit.test_evaluation_annotations::test_conversation_profile_off_keeps_session_and_new_chat_is_distinct", "tests.unit.test_evaluation_study::test_shared_mock_study_freezes_nine_conditions_and_resumes_without_repeating", "tests.unit.test_evaluation_study::test_interrupted_study_call_is_not_silently_repeated", "tests.unit.test_evaluation_study::test_study_rejects_live_mode_and_mutated_frozen_inputs", "tests.unit.test_evaluation_study::test_study_prompt_or_rubric_environment_change_stops_remaining_calls"]`
- Acceptance references: [AC-07](<../acceptance.md#ac-07>), [AC-17](<../acceptance.md#ac-17>), [AC-18](<../acceptance.md#ac-18>), [AC-19](<../acceptance.md#ac-19>), [AC-46](<../acceptance.md#ac-46>), [HC-12](<../acceptance.md#hc-12>)
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

## QA-08

Analyse correct paired outcomes by protocol. Use binary discordant tests only for binary scores, paired intervals for token F1, and scenario clustering for multi-turn data. Keep full-response human correctness/grounding separate from lexical proxies and trace failures to actual contexts.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 8, "suggested_project_week": 6, "suggested_start_course_week": 7, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G5
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["QA-07", "QA-04"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-04"}]`
- Upstream collaborators (derived from those dependencies): [QA-07](<../by_owner/chong-zhang.md#qa-07>) — Chong Zhang; [QA-04](<../by_owner/chong-zhang.md#qa-04>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [RET-11](<../by_owner/chengzhou-liu.md#ret-11>) — Chengzhou Liu; [QA-14](<../by_owner/chong-zhang.md#qa-14>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Analyse correct paired outcomes by protocol. Use binary discordant tests only for binary scores, paired intervals for token F1, and scenario clustering for multi-turn data. Keep full-response human correctness/grounding separate from lexical proxies and trace failures to actual contexts.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_evaluation_metrics.py](<../../../tests/unit/test_evaluation_metrics.py>), [tests/unit/test_evaluation_runner.py](<../../../tests/unit/test_evaluation_runner.py>), [tests/unit/test_evaluation_backend.py](<../../../tests/unit/test_evaluation_backend.py>), [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: `["tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_teaching_api_nine_matched_jobs_and_blind_export_without_chat_mutation", "tests.integration.test_evaluation_postgres::test_postgres_teaching_cancel_keeps_success_and_all_scheduled_outcomes", "tests.integration.test_evaluation_postgres::test_postgres_teaching_late_source_revocation_discards_publication", "tests.integration.test_evaluation_postgres::test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result", "tests.integration.test_evaluation_postgres::test_postgres_all_twelve_authored_scenario_families_use_real_chat_api", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_openqa]", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_mcq]", "tests.unit.test_evaluation_backend::test_registered_hash_rejects_post_freeze_question_or_gold_injection", "tests.unit.test_evaluation_backend::test_server_cancellation_retains_all_scheduled_items", "tests.unit.test_evaluation_backend::test_admin_api_create_freeze_start_results_and_role_denial", "tests.unit.test_evaluation_metrics::test_conservative_em[ Oxygen  -oxygen-1]", "tests.unit.test_evaluation_metrics::test_conservative_em[\\uff2f\\uff38\\uff39\\uff27\\uff25\\uff2e-oxygen-1]", "tests.unit.test_evaluation_metrics::test_conservative_em[not oxygen-oxygen-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[-2 m-2 m-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[2 mg-2 g-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[--0]", "tests.unit.test_evaluation_metrics::test_conservative_em[None-oxygen-0]", "tests.unit.test_evaluation_metrics::test_multiset_f1_preserves_negation_signs_units_and_repetition", "tests.unit.test_evaluation_metrics::test_full_explanation_is_never_used_as_compact_answer", "tests.unit.test_evaluation_metrics::test_failed_cancelled_and_refused_rows_keep_scheduled_denominator", "tests.unit.test_evaluation_metrics::test_mcq_requires_selected_option_text_not_only_label", "tests.unit.test_evaluation_metrics::test_retrieval_uses_actual_returned_denominator_and_graded_ndcg", "tests.unit.test_evaluation_metrics::test_unavailable_qrels_and_zero_idcg_are_not_fabricated_zeros", "tests.unit.test_evaluation_metrics::test_citations_check_actual_text_hash_and_have_applicable_denominator", "tests.unit.test_evaluation_metrics::test_exact_binary_discordants_and_continuous_paired_intervals", "tests.unit.test_evaluation_metrics::test_turns_cluster_by_scenario_without_invalid_per_turn_mcnemar", "tests.unit.test_evaluation_runner::test_stem_projection_unchanged_when_private_labels_change", "tests.unit.test_evaluation_runner::test_mcq_shuffle_is_stable_symmetric_and_gold_stays_private", "tests.unit.test_evaluation_runner::test_duplicate_candidates_and_split_counts", "tests.unit.test_evaluation_runner::test_duplicate_source_choices_do_not_block_stem_only_openqa_freeze", "tests.unit.test_evaluation_runner::test_freeze_preregisters_and_resume_does_not_repeat_calls", "tests.unit.test_evaluation_runner::test_interrupted_submission_reconciles_receipt_without_new_call", "tests.unit.test_evaluation_runner::test_ambiguous_unrecorded_submission_never_automatically_repeats", "tests.unit.test_evaluation_runner::test_environment_change_stops_new_calls_preserves_scheduled_set", "tests.unit.test_evaluation_runner::test_tampered_manifest_or_private_reference_rejected", "tests.unit.test_evaluation_runner::test_cancelled_export_retains_denominator_and_has_no_private_reference", "tests.unit.test_evaluation_runner::test_live_defaults_and_e1_redefinition_are_rejected", "tests.unit.test_evaluation_runner::test_repeat_export_preserves_existing_independent_review", "tests.unit.test_evaluation_runner::test_malformed_shared_response_is_retained_as_invalid"]`
- Acceptance references: [AC-18](<../acceptance.md#ac-18>), [AC-19](<../acceptance.md#ac-19>), [AC-47](<../acceptance.md#ac-47>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>), [evidence/openstax/frontend-prompt-consolidation.json](<../../../evidence/openstax/frontend-prompt-consolidation.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current tests cover all 12 authored conversation families, gold-free mode adapters, conservative compact-answer metrics, hand-calculated statistical fixtures, frozen runner/resume and retained all-outcome denominators.
- Unresolved scope: Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings.
- Blockers: None recorded.
- Mapping limitation: Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Current tests cover all 12 authored conversation families, gold-free mode adapters, conservative compact-answer metrics, hand-calculated statistical fixtures, frozen runner/resume and retained all-outcome denominators.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>), [evidence/openstax/frontend-prompt-consolidation.json](<../../../evidence/openstax/frontend-prompt-consolidation.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## CHAT-09

Implement evaluation/datasets/sciq_openqa.py and the compact-answer scorer. Send stem only through the chat engine with empty benchmark context; keep references/distractors/support outside it. Version EM/F1 normalisation, negation/number/unit tests and full-response review exports. Label this SciQ-derived, not MCQ accuracy.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 8, "suggested_project_week": 6, "suggested_start_course_week": 7, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G5
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["QA-02", "QA-05", "CHAT-05", "GEN-08"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-08"}]`
- Upstream collaborators (derived from those dependencies): [QA-02](<../by_owner/chong-zhang.md#qa-02>) — Chong Zhang; [QA-05](<../by_owner/chong-zhang.md#qa-05>) — Chong Zhang; [CHAT-05](<../by_owner/sijin-lu.md#chat-05>) — Sijin Lu; [GEN-08](<../by_owner/sijin-lu.md#gen-08>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [INT-08](<../by_owner/xianshu-zhang.md#int-08>) — Xianshu Zhang; [QA-07](<../by_owner/chong-zhang.md#qa-07>) — Chong Zhang; [CHAT-11](<../by_owner/xianshu-zhang.md#chat-11>) — Xianshu Zhang
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Implement evaluation/datasets/sciq_openqa.py and the compact-answer scorer. Send stem only through the chat engine with empty benchmark context; keep references/distractors/support outside it. Version EM/F1 normalisation, negation/number/unit tests and full-response review exports. Label this SciQ-derived, not MCQ accuracy.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_evaluation_metrics.py](<../../../tests/unit/test_evaluation_metrics.py>), [tests/unit/test_evaluation_runner.py](<../../../tests/unit/test_evaluation_runner.py>), [tests/unit/test_evaluation_backend.py](<../../../tests/unit/test_evaluation_backend.py>), [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: `["tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_teaching_api_nine_matched_jobs_and_blind_export_without_chat_mutation", "tests.integration.test_evaluation_postgres::test_postgres_teaching_cancel_keeps_success_and_all_scheduled_outcomes", "tests.integration.test_evaluation_postgres::test_postgres_teaching_late_source_revocation_discards_publication", "tests.integration.test_evaluation_postgres::test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result", "tests.integration.test_evaluation_postgres::test_postgres_all_twelve_authored_scenario_families_use_real_chat_api", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_openqa]", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_mcq]", "tests.unit.test_evaluation_backend::test_registered_hash_rejects_post_freeze_question_or_gold_injection", "tests.unit.test_evaluation_backend::test_server_cancellation_retains_all_scheduled_items", "tests.unit.test_evaluation_backend::test_admin_api_create_freeze_start_results_and_role_denial", "tests.unit.test_evaluation_metrics::test_conservative_em[ Oxygen  -oxygen-1]", "tests.unit.test_evaluation_metrics::test_conservative_em[\\uff2f\\uff38\\uff39\\uff27\\uff25\\uff2e-oxygen-1]", "tests.unit.test_evaluation_metrics::test_conservative_em[not oxygen-oxygen-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[-2 m-2 m-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[2 mg-2 g-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[--0]", "tests.unit.test_evaluation_metrics::test_conservative_em[None-oxygen-0]", "tests.unit.test_evaluation_metrics::test_multiset_f1_preserves_negation_signs_units_and_repetition", "tests.unit.test_evaluation_metrics::test_full_explanation_is_never_used_as_compact_answer", "tests.unit.test_evaluation_metrics::test_failed_cancelled_and_refused_rows_keep_scheduled_denominator", "tests.unit.test_evaluation_metrics::test_mcq_requires_selected_option_text_not_only_label", "tests.unit.test_evaluation_metrics::test_retrieval_uses_actual_returned_denominator_and_graded_ndcg", "tests.unit.test_evaluation_metrics::test_unavailable_qrels_and_zero_idcg_are_not_fabricated_zeros", "tests.unit.test_evaluation_metrics::test_citations_check_actual_text_hash_and_have_applicable_denominator", "tests.unit.test_evaluation_metrics::test_exact_binary_discordants_and_continuous_paired_intervals", "tests.unit.test_evaluation_metrics::test_turns_cluster_by_scenario_without_invalid_per_turn_mcnemar", "tests.unit.test_evaluation_runner::test_stem_projection_unchanged_when_private_labels_change", "tests.unit.test_evaluation_runner::test_mcq_shuffle_is_stable_symmetric_and_gold_stays_private", "tests.unit.test_evaluation_runner::test_duplicate_candidates_and_split_counts", "tests.unit.test_evaluation_runner::test_duplicate_source_choices_do_not_block_stem_only_openqa_freeze", "tests.unit.test_evaluation_runner::test_freeze_preregisters_and_resume_does_not_repeat_calls", "tests.unit.test_evaluation_runner::test_interrupted_submission_reconciles_receipt_without_new_call", "tests.unit.test_evaluation_runner::test_ambiguous_unrecorded_submission_never_automatically_repeats", "tests.unit.test_evaluation_runner::test_environment_change_stops_new_calls_preserves_scheduled_set", "tests.unit.test_evaluation_runner::test_tampered_manifest_or_private_reference_rejected", "tests.unit.test_evaluation_runner::test_cancelled_export_retains_denominator_and_has_no_private_reference", "tests.unit.test_evaluation_runner::test_live_defaults_and_e1_redefinition_are_rejected", "tests.unit.test_evaluation_runner::test_repeat_export_preserves_existing_independent_review", "tests.unit.test_evaluation_runner::test_malformed_shared_response_is_retained_as_invalid"]`
- Acceptance references: [AC-17](<../acceptance.md#ac-17>), [AC-46](<../acceptance.md#ac-46>), [AC-47](<../acceptance.md#ac-47>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>), [evidence/openstax/frontend-prompt-consolidation.json](<../../../evidence/openstax/frontend-prompt-consolidation.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current tests cover all 12 authored conversation families, gold-free mode adapters, conservative compact-answer metrics, hand-calculated statistical fixtures, frozen runner/resume and retained all-outcome denominators.
- Unresolved scope: Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings.
- Blockers: None recorded.
- Mapping limitation: Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Current tests cover all 12 authored conversation families, gold-free mode adapters, conservative compact-answer metrics, hand-calculated statistical fixtures, frozen runner/resume and retained all-outcome denominators.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-evaluation.md](<../../execution/audit-evaluation.md>), [evidence/openstax/frontend-prompt-consolidation.json](<../../../evidence/openstax/frontend-prompt-consolidation.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.
