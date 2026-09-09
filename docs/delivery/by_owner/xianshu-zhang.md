# Delivery view: Xianshu Zhang

Generated reporting view. The canonical ledgers below remain authoritative; this file adds no product requirement or acceptance decision.

Accountable owner and suggested course week are reporting metadata, never permissions, implementation eligibility, runtime flags or evidence of completion. Actual executor and recorded dates are shown separately. Cross-references do not count a task more than once. No calendar dates or completion percentages are inferred.

Canonical requirements, shared interfaces and evidence: [PRD.md](<../../../PRD.md>) · [SPEC.md](<../../../SPEC.md>) · [PLANS.md](<../../../PLANS.md>) · [HANDOVER.md](<../../../HANDOVER.md>) · [docs/foundation/api_contract.md](<../../foundation/api_contract.md>) · [contracts/openapi.json](<../../../contracts/openapi.json>) · [docs/execution/tasks.json](<../../execution/tasks.json>) · [docs/execution/reporting_plan.json](<../../execution/reporting_plan.json>) · [docs/execution/acceptance.json](<../../execution/acceptance.json>)

Task-ledger reconciliation timestamp (not a completion date): 2026-09-08T10:09:00.459775+00:00

This owner view contains 13 unique domain tasks. Shared interfaces remain in the central specifications linked above.

Task index: [INT-01](<xianshu-zhang.md#int-01>), [INT-02](<xianshu-zhang.md#int-02>), [INT-03](<xianshu-zhang.md#int-03>), [INT-04](<xianshu-zhang.md#int-04>), [INT-05](<xianshu-zhang.md#int-05>), [INT-06](<xianshu-zhang.md#int-06>), [INT-07](<xianshu-zhang.md#int-07>), [INT-08](<xianshu-zhang.md#int-08>), [INT-09](<xianshu-zhang.md#int-09>), [INT-10](<xianshu-zhang.md#int-10>), [CHAT-01](<xianshu-zhang.md#chat-01>), [CHAT-11](<xianshu-zhang.md#chat-11>), [CHAT-12](<xianshu-zhang.md#chat-12>)

## INT-01

Inventory and reuse actual sources. Read all assets and the current checkout; record retain/adapt/rebuild, missing files and unexecuted tests. Verify inventory entries against real paths without discarding user changes.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 6, "suggested_project_week": 4, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G0
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: None recorded.
- Required dependency artifacts: None recorded.
- Upstream collaborators (derived from those dependencies): None recorded.
- Downstream collaborators (reverse dependency references): [INT-02](<xianshu-zhang.md#int-02>) — Xianshu Zhang
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Inventory and reuse actual sources. Read all assets and the current checkout; record retain/adapt/rebuild, missing files and unexecuted tests. Verify inventory entries against real paths without discarding user changes.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [scripts/verify/contracts.py](<../../../scripts/verify/contracts.py>), [scripts/verify/chat_scope.py](<../../../scripts/verify/chat_scope.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-48](<../acceptance.md#ac-48>), [HC-01](<../acceptance.md#hc-01>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/source-architecture-audit.md](<../../execution/source-architecture-audit.md>), [PRD.md](<../../../PRD.md>), [SPEC.md](<../../../SPEC.md>), [evidence/source_audit/source_read_manifest.json](<../../../evidence/source_audit/source_read_manifest.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Supplied Word/ZIP/UI sources, source precedence, original numbered scope and actual original Figure 1/page 1 were reconciled into substantive English PRD/SPEC/PLANS and linked detailed specifications.
- Unresolved scope: None recorded.
- Blockers: None recorded.
- Mapping limitation: None recorded.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Supplied Word/ZIP/UI sources, source precedence, original numbered scope and actual original Figure 1/page 1 were reconciled into substantive English PRD/SPEC/PLANS and linked detailed specifications.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/source-architecture-audit.md](<../../execution/source-architecture-audit.md>), [PRD.md](<../../../PRD.md>), [SPEC.md](<../../../SPEC.md>), [evidence/source_audit/source_read_manifest.json](<../../../evidence/source_audit/source_read_manifest.json>)
- remaining acceptance scope: `REAL_FLOW_VERIFIED`. No additional task-specific software gap identified; independent overall acceptance is not inferred.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## INT-02

Freeze chat-first requirements. Record the user correction and L01–L09 lean rules; explicitly replace MCQ-only interaction, display-only history and deferred free-form conversation. Distinguish user-confirmed scope from v3 engineering defaults.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 6, "suggested_project_week": 4, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G0
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["INT-01"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-01"}]`
- Upstream collaborators (derived from those dependencies): [INT-01](<xianshu-zhang.md#int-01>) — Xianshu Zhang
- Downstream collaborators (reverse dependency references): [INT-03](<xianshu-zhang.md#int-03>) — Xianshu Zhang; [DAT-01](<hongle-yang.md#dat-01>) — Hongle Yang; [CHAT-01](<xianshu-zhang.md#chat-01>) — Xianshu Zhang
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Freeze chat-first requirements. Record the user correction and L01–L09 lean rules; explicitly replace MCQ-only interaction, display-only history and deferred free-form conversation. Distinguish user-confirmed scope from v3 engineering defaults.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [scripts/verify/contracts.py](<../../../scripts/verify/contracts.py>), [scripts/verify/chat_scope.py](<../../../scripts/verify/chat_scope.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-21](<../acceptance.md#ac-21>), [AC-36](<../acceptance.md#ac-36>), [AC-48](<../acceptance.md#ac-48>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/source-architecture-audit.md](<../../execution/source-architecture-audit.md>), [PRD.md](<../../../PRD.md>), [SPEC.md](<../../../SPEC.md>), [evidence/source_audit/source_read_manifest.json](<../../../evidence/source_audit/source_read_manifest.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Supplied Word/ZIP/UI sources, source precedence, original numbered scope and actual original Figure 1/page 1 were reconciled into substantive English PRD/SPEC/PLANS and linked detailed specifications.
- Unresolved scope: None recorded.
- Blockers: None recorded.
- Mapping limitation: None recorded.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Supplied Word/ZIP/UI sources, source precedence, original numbered scope and actual original Figure 1/page 1 were reconciled into substantive English PRD/SPEC/PLANS and linked detailed specifications.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/source-architecture-audit.md](<../../execution/source-architecture-audit.md>), [PRD.md](<../../../PRD.md>), [SPEC.md](<../../../SPEC.md>), [evidence/source_audit/source_read_manifest.json](<../../../evidence/source_audit/source_read_manifest.json>)
- remaining acceptance scope: `REAL_FLOW_VERIFIED`. No additional task-specific software gap identified; independent overall acceptance is not inferred.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## INT-03

Establish canonical contracts. Define ChatMessageCreate, ConversationSnapshot, PreparedQuery, ChatResponseV1, evaluation-only MCQResponseV1, envelopes and OpenAPI before consumers. Validate distinct meanings, fixtures and mode boundaries.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 6, "suggested_project_week": 4, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G1
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["INT-02", "CHAT-01"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-01"}]`
- Upstream collaborators (derived from those dependencies): [INT-02](<xianshu-zhang.md#int-02>) — Xianshu Zhang; [CHAT-01](<xianshu-zhang.md#chat-01>) — Xianshu Zhang
- Downstream collaborators (reverse dependency references): [INT-04](<xianshu-zhang.md#int-04>) — Xianshu Zhang; [DAT-04](<hongle-yang.md#dat-04>) — Hongle Yang; [DAT-06](<hongle-yang.md#dat-06>) — Hongle Yang; [RET-03](<chengzhou-liu.md#ret-03>) — Chengzhou Liu; [GEN-01](<sijin-lu.md#gen-01>) — Sijin Lu; [PER-01](<pengyuan-xia.md#per-01>) — Pengyuan Xia; [BE-02](<zeping-liao.md#be-02>) — Zeping Liao; [BE-09](<zeping-liao.md#be-09>) — Zeping Liao; [FE-01](<baiqing-huang.md#fe-01>) — Baiqing Huang; [QA-01](<chong-zhang.md#qa-01>) — Chong Zhang; [QA-05](<chong-zhang.md#qa-05>) — Chong Zhang
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Establish canonical contracts. Define ChatMessageCreate, ConversationSnapshot, PreparedQuery, ChatResponseV1, evaluation-only MCQResponseV1, envelopes and OpenAPI before consumers. Validate distinct meanings, fixtures and mode boundaries.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_legacy_mcq_migration.py](<../../../tests/integration/test_legacy_mcq_migration.py>)
- Recorded current check nodes: `["tests.integration.test_legacy_mcq_migration::test_initial_data_and_typed_mcq_survive_additive_migrations"]`
- Acceptance references: [AC-10](<../acceptance.md#ac-10>), [AC-22](<../acceptance.md#ac-22>), [AC-36](<../acceptance.md#ac-36>), [AC-48](<../acceptance.md#ac-48>)
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

## INT-04

Bootstrap one reproducible repository. Reuse audited foundations; create locked backend/frontend environments, Compose services and real startup scripts. A new checkout must boot in mock mode with persistent data.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 6, "suggested_project_week": 4, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G1
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["INT-03"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-03"}]`
- Upstream collaborators (derived from those dependencies): [INT-03](<xianshu-zhang.md#int-03>) — Xianshu Zhang
- Downstream collaborators (reverse dependency references): [INT-05](<xianshu-zhang.md#int-05>) — Xianshu Zhang; [RET-01](<chengzhou-liu.md#ret-01>) — Chengzhou Liu; [GEN-02](<sijin-lu.md#gen-02>) — Sijin Lu; [BE-01](<zeping-liao.md#be-01>) — Zeping Liao; [FE-01](<baiqing-huang.md#fe-01>) — Baiqing Huang
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Bootstrap one reproducible repository. Reuse audited foundations; create locked backend/frontend environments, Compose services and real startup scripts. A new checkout must boot in mock mode with persistent data.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [scripts/verify/contracts.py](<../../../scripts/verify/contracts.py>), [scripts/verify/chat_scope.py](<../../../scripts/verify/chat_scope.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-01](<../acceptance.md#ac-01>), [AC-02](<../acceptance.md#ac-02>), [AC-37](<../acceptance.md#ac-37>), [HC-02](<../acceptance.md#hc-02>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/handovers/candidate-20260908T093208Z/verification.json](<../../../evidence/handovers/candidate-20260908T093208Z/verification.json>), [docs/development_checks.md](<../../development_checks.md>), [evidence/e5-container/runtime-verification.json](<../../../evidence/e5-container/runtime-verification.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Fresh base Compose migration, seeded login and persisted authored chat ran without model keys or SciQ. Final source/runtime checks passed; the real E5 container has separate restored-corpus proof.
- Unresolved scope: The small base image does not include real model weights; install/use the explicit E5 runtime for the formal corpus.
- Blockers: None recorded.
- Mapping limitation: The small base image does not include real model weights; install/use the explicit E5 runtime for the formal corpus.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Fresh base Compose migration, seeded login and persisted authored chat ran without model keys or SciQ. Final source/runtime checks passed; the real E5 container has separate restored-corpus proof.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/handovers/candidate-20260908T093208Z/verification.json](<../../../evidence/handovers/candidate-20260908T093208Z/verification.json>), [docs/development_checks.md](<../../development_checks.md>), [evidence/e5-container/runtime-verification.json](<../../../evidence/e5-container/runtime-verification.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. The small base image does not include real model weights; install/use the explicit E5 runtime for the formal corpus.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## INT-05

Automate the local and CI checks. Run format/lint/types, schemas, units, PostgreSQL integration, frontend build and browser smoke checks. A deliberately broken contract must fail; live tests remain separately labelled.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 6, "suggested_project_week": 4, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G1
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["INT-04", "QA-01"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-04"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-01"}]`
- Upstream collaborators (derived from those dependencies): [INT-04](<xianshu-zhang.md#int-04>) — Xianshu Zhang; [QA-01](<chong-zhang.md#qa-01>) — Chong Zhang
- Downstream collaborators (reverse dependency references): None recorded.
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Automate the local and CI checks. Run format/lint/types, schemas, units, PostgreSQL integration, frontend build and browser smoke checks. A deliberately broken contract must fail; live tests remain separately labelled.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [scripts/verify/contracts.py](<../../../scripts/verify/contracts.py>), [scripts/verify/chat_scope.py](<../../../scripts/verify/chat_scope.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-01](<../acceptance.md#ac-01>), [AC-02](<../acceptance.md#ac-02>), [AC-10](<../acceptance.md#ac-10>), [AC-21](<../acceptance.md#ac-21>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/development_checks.md](<../../development_checks.md>), [evidence/devtools/verification.json](<../../../evidence/devtools/verification.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current format/lint/boundary typing, contract/schema checks, Python/PostgreSQL tests and frontend type/tests/build passed. Deliberately broken contract/type probes were rejected; the CI workflow and guarded database setup are present.
- Unresolved scope: Hosted CI execution has not occurred; local equivalent checks are actual evidence.
- Blockers: None recorded.
- Mapping limitation: Hosted CI execution has not occurred; local equivalent checks are actual evidence.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current format/lint/boundary typing, contract/schema checks, Python/PostgreSQL tests and frontend type/tests/build passed. Deliberately broken contract/type probes were rejected; the CI workflow and guarded database setup are present.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/development_checks.md](<../../development_checks.md>), [evidence/devtools/verification.json](<../../../evidence/devtools/verification.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Hosted CI execution has not occurred; local equivalent checks are actual evidence.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## INT-06

Deliver the first real chat slice. Use authored sources through ingestion, retrieval, free-text conversation, persistence and evidence UI. Include a reference-dependent follow-up and demonstrate operation without SciQ. Capture normal, clarification, insufficient-evidence and failure outcomes.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["CHAT-06", "RET-05", "GEN-05"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-05"}]`
- Upstream collaborators (derived from those dependencies): [CHAT-06](<baiqing-huang.md#chat-06>) — Baiqing Huang; [RET-05](<chengzhou-liu.md#ret-05>) — Chengzhou Liu; [GEN-05](<sijin-lu.md#gen-05>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [INT-07](<xianshu-zhang.md#int-07>) — Xianshu Zhang; [QA-07](<chong-zhang.md#qa-07>) — Chong Zhang
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Deliver the first real chat slice. Use authored sources through ingestion, retrieval, free-text conversation, persistence and evidence UI. Include a reference-dependent follow-up and demonstrate operation without SciQ. Capture normal, clarification, insufficient-evidence and failure outcomes.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_chat_evidence_reuse.py](<../../../tests/integration/test_chat_evidence_reuse.py>)
- Recorded current check nodes: `["tests.integration.test_chat_evidence_reuse::test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic", "tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation"]`
- Acceptance references: [AC-08](<../acceptance.md#ac-08>), [AC-09](<../acceptance.md#ac-09>), [AC-37](<../acceptance.md#ac-37>), [AC-38](<../acceptance.md#ac-38>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Actual HTTP, durable worker, real official-source E5 retrieval, budgeted source selection, saved prompt/context/profile traces, request-local citations, feedback and revision history executed on the published corpus.
- Unresolved scope: Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.
- Blockers: None recorded.
- Mapping limitation: Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Actual HTTP, durable worker, real official-source E5 retrieval, budgeted source selection, saved prompt/context/profile traces, request-local citations, feedback and revision history executed on the published corpus.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## INT-07

Close whole-product seams. Trace J1–J4/J6 through UI/API, session context, profile policy, service and DB; later add J5 evaluation. Fix consumer mismatches and old MCQ assumptions rather than declaring isolated modules complete.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["INT-06", "BE-14", "CHAT-07", "CHAT-08"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-14"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-08"}]`
- Upstream collaborators (derived from those dependencies): [INT-06](<xianshu-zhang.md#int-06>) — Xianshu Zhang; [BE-14](<zeping-liao.md#be-14>) — Zeping Liao; [CHAT-07](<pengyuan-xia.md#chat-07>) — Pengyuan Xia; [CHAT-08](<zeping-liao.md#chat-08>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [INT-08](<xianshu-zhang.md#int-08>) — Xianshu Zhang
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Close whole-product seams. Trace J1–J4/J6 through UI/API, session context, profile policy, service and DB; later add J5 evaluation. Fix consumer mismatches and old MCQ assumptions rather than declaring isolated modules complete.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_chat_evidence_reuse.py](<../../../tests/integration/test_chat_evidence_reuse.py>)
- Recorded current check nodes: `["tests.integration.test_chat_evidence_reuse::test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic", "tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation"]`
- Acceptance references: [AC-16](<../acceptance.md#ac-16>), [AC-22](<../acceptance.md#ac-22>), [AC-30](<../acceptance.md#ac-30>), [AC-44](<../acceptance.md#ac-44>), [AC-45](<../acceptance.md#ac-45>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Actual HTTP, durable worker, real official-source E5 retrieval, budgeted source selection, saved prompt/context/profile traces, request-local citations, feedback and revision history executed on the published corpus.
- Unresolved scope: Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.
- Blockers: None recorded.
- Mapping limitation: Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Actual HTTP, durable worker, real official-source E5 retrieval, budgeted source selection, saved prompt/context/profile traces, request-local citations, feedback and revision history executed on the published corpus.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

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
- Upstream collaborators (derived from those dependencies): [QA-07](<chong-zhang.md#qa-07>) — Chong Zhang; [CHAT-09](<chong-zhang.md#chat-09>) — Chong Zhang; [INT-07](<xianshu-zhang.md#int-07>) — Xianshu Zhang
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
- Upstream collaborators (derived from those dependencies): [BE-16](<zeping-liao.md#be-16>) — Zeping Liao; [QA-11](<chong-zhang.md#qa-11>) — Chong Zhang
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

## INT-10

Deliver the integrated chat-first project. Provide runnable code, English foundation/user/operations guides, the 108-task and 60-scenario ledgers, a multi-turn demo and separate research reports. Verify clean rebuild; report technical completion separately from live evidence and human acceptance.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 12, "suggested_project_week": 10, "suggested_start_course_week": 11, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G9
- Current status: `IMPLEMENTED_UNVERIFIED`
- Separate implementation / verification / research / human-review states: `IMPLEMENTED_UNVERIFIED` / `IMPLEMENTED_UNVERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["QA-14", "BE-17", "FE-12", "PER-09", "RET-11", "GEN-11", "DAT-12", "CHAT-12"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-14"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-17"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-12"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-11"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-11"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "DAT-12"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-12"}]`
- Upstream collaborators (derived from those dependencies): [QA-14](<chong-zhang.md#qa-14>) — Chong Zhang; [BE-17](<zeping-liao.md#be-17>) — Zeping Liao; [FE-12](<baiqing-huang.md#fe-12>) — Baiqing Huang; [PER-09](<pengyuan-xia.md#per-09>) — Pengyuan Xia; [RET-11](<chengzhou-liu.md#ret-11>) — Chengzhou Liu; [GEN-11](<sijin-lu.md#gen-11>) — Sijin Lu; [DAT-12](<hongle-yang.md#dat-12>) — Hongle Yang; [CHAT-12](<xianshu-zhang.md#chat-12>) — Xianshu Zhang
- Downstream collaborators (reverse dependency references): None recorded.
- Source files recorded for this implementation: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Changed files recorded by the ledger: [docs/foundation/requirements.md](<../../foundation/requirements.md>), [docs/foundation/architecture.md](<../../foundation/architecture.md>), [scripts/verify/foundation.py](<../../../scripts/verify/foundation.py>), [compose.yaml](<../../../compose.yaml>)
- Shared entry / interface boundary: Foundation, verification and release commands / Integration
- Persisted effect / consumer: Configurations and execution ledgers / All module contracts and final delivery
- Local acceptance clause: Deliver the integrated chat-first project. Provide runnable code, English foundation/user/operations guides, the 108-task and 60-scenario ledgers, a multi-turn demo and separate research reports. Verify clean rebuild; report technical completion separately from live evidence and human acceptance.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [scripts/verify/contracts.py](<../../../scripts/verify/contracts.py>), [scripts/verify/chat_scope.py](<../../../scripts/verify/chat_scope.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-20](<../acceptance.md#ac-20>), [AC-21](<../acceptance.md#ac-21>), [AC-37](<../acceptance.md#ac-37>), [AC-48](<../acceptance.md#ac-48>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [HANDOVER.md](<../../../HANDOVER.md>), [docs/runbook.md](<../../runbook.md>), [docs/execution/acceptance_report.md](<../../execution/acceptance_report.md>), [docs/delivery/README.md](<../README.md>), [evidence/delivery/2026-09-08T09-52-01Z.json](<../../../evidence/delivery/2026-09-08T09-52-01Z.json>), [evidence/delivery/2026-09-08T09-56-03Z-input-validation.json](<../../../evidence/delivery/2026-09-08T09-56-03Z-input-validation.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Runnable local product, real corpus, current software evidence, English handover and all original numbered ledgers are delivered with separate research and human-review status. The required deterministic delivery exporter produces eight owner views, seven course-week views and all 60 acceptance references from the canonical ledgers; each grouping contains all 108 tasks exactly once.
- Unresolved scope: Integrated scientific/human acceptance remains open where the linked original tasks require real provider outputs or independent review.
- Blockers: None recorded.
- Mapping limitation: Integrated scientific/human acceptance remains open where the linked original tasks require real provider outputs or independent review.

Recorded component observations:

- observed task scope: `IMPLEMENTED_UNVERIFIED`. Runnable local product, real corpus, current software evidence, English handover and all original numbered ledgers are delivered with separate research and human-review status. The required deterministic delivery exporter produces eight owner views, seven course-week views and all 60 acceptance references from the canonical ledgers; each grouping contains all 108 tasks exactly once.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [HANDOVER.md](<../../../HANDOVER.md>), [docs/runbook.md](<../../runbook.md>), [docs/execution/acceptance_report.md](<../../execution/acceptance_report.md>), [docs/delivery/README.md](<../README.md>), [evidence/delivery/2026-09-08T09-52-01Z.json](<../../../evidence/delivery/2026-09-08T09-52-01Z.json>), [evidence/delivery/2026-09-08T09-56-03Z-input-validation.json](<../../../evidence/delivery/2026-09-08T09-56-03Z-input-validation.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Integrated scientific/human acceptance remains open where the linked original tasks require real provider outputs or independent review.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## CHAT-01

Write the chat-first migration decision in docs/foundation/scope_migration.md. Inventory old MCQ-only claims; define three modes and schema/API replacements. Accept when requirements, diagrams, task gates and scope explicitly make conversation required and SciQ secondary.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 6, "suggested_project_week": 4, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G0
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["INT-02"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-02"}]`
- Upstream collaborators (derived from those dependencies): [INT-02](<xianshu-zhang.md#int-02>) — Xianshu Zhang
- Downstream collaborators (reverse dependency references): [INT-03](<xianshu-zhang.md#int-03>) — Xianshu Zhang
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Write the chat-first migration decision in docs/foundation/scope_migration.md. Inventory old MCQ-only claims; define three modes and schema/API replacements. Accept when requirements, diagrams, task gates and scope explicitly make conversation required and SciQ secondary.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_conversation.py](<../../../tests/unit/test_conversation.py>), [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-21](<../acceptance.md#ac-21>), [AC-36](<../acceptance.md#ac-36>), [AC-48](<../acceptance.md#ac-48>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/source-architecture-audit.md](<../../execution/source-architecture-audit.md>), [PRD.md](<../../../PRD.md>), [SPEC.md](<../../../SPEC.md>), [evidence/source_audit/source_read_manifest.json](<../../../evidence/source_audit/source_read_manifest.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Supplied Word/ZIP/UI sources, source precedence, original numbered scope and actual original Figure 1/page 1 were reconciled into substantive English PRD/SPEC/PLANS and linked detailed specifications.
- Unresolved scope: None recorded.
- Blockers: None recorded.
- Mapping limitation: None recorded.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Supplied Word/ZIP/UI sources, source precedence, original numbered scope and actual original Figure 1/page 1 were reconciled into substantive English PRD/SPEC/PLANS and linked detailed specifications.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/source-architecture-audit.md](<../../execution/source-architecture-audit.md>), [PRD.md](<../../../PRD.md>), [SPEC.md](<../../../SPEC.md>), [evidence/source_audit/source_read_manifest.json](<../../../evidence/source_audit/source_read_manifest.json>)
- remaining acceptance scope: `REAL_FLOW_VERIFIED`. No additional task-specific software gap identified; independent overall acceptance is not inferred.

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
- Upstream collaborators (derived from those dependencies): [CHAT-09](<chong-zhang.md#chat-09>) — Chong Zhang; [CHAT-10](<chong-zhang.md#chat-10>) — Chong Zhang; [BE-14](<zeping-liao.md#be-14>) — Zeping Liao; [FE-11](<baiqing-huang.md#fe-11>) — Baiqing Huang
- Downstream collaborators (reverse dependency references): [QA-12](<chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-12](<xianshu-zhang.md#chat-12>) — Xianshu Zhang
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

## CHAT-12

Deliver English chat-first architecture, a reproducible multi-turn demo, migration notes and separate product/openQA/MCQ limitations. Fresh setup can chat without SciQ; later evaluation is a separate command. Verify all 108 tasks/60 scenarios are represented with actual completion evidence or explicit blockers.

- Accountable owner (reporting): Xianshu Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 12, "suggested_project_week": 10, "suggested_start_course_week": 11, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G9
- Current status: `IMPLEMENTED_UNVERIFIED`
- Separate implementation / verification / research / human-review states: `IMPLEMENTED_UNVERIFIED` / `IMPLEMENTED_UNVERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["CHAT-11", "QA-12", "BE-16"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-11"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-12"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-16"}]`
- Upstream collaborators (derived from those dependencies): [CHAT-11](<xianshu-zhang.md#chat-11>) — Xianshu Zhang; [QA-12](<chong-zhang.md#qa-12>) — Chong Zhang; [BE-16](<zeping-liao.md#be-16>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [INT-10](<xianshu-zhang.md#int-10>) — Xianshu Zhang
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Deliver English chat-first architecture, a reproducible multi-turn demo, migration notes and separate product/openQA/MCQ limitations. Fresh setup can chat without SciQ; later evaluation is a separate command. Verify all 108 tasks/60 scenarios are represented with actual completion evidence or explicit blockers.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_conversation.py](<../../../tests/unit/test_conversation.py>), [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-20](<../acceptance.md#ac-20>), [AC-37](<../acceptance.md#ac-37>), [AC-48](<../acceptance.md#ac-48>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [HANDOVER.md](<../../../HANDOVER.md>), [docs/runbook.md](<../../runbook.md>), [docs/execution/acceptance_report.md](<../../execution/acceptance_report.md>), [docs/delivery/README.md](<../README.md>), [evidence/delivery/2026-09-08T09-52-01Z.json](<../../../evidence/delivery/2026-09-08T09-52-01Z.json>), [evidence/delivery/2026-09-08T09-56-03Z-input-validation.json](<../../../evidence/delivery/2026-09-08T09-56-03Z-input-validation.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Runnable local product, real corpus, current software evidence, English handover and all original numbered ledgers are delivered with separate research and human-review status. The required deterministic delivery exporter produces eight owner views, seven course-week views and all 60 acceptance references from the canonical ledgers; each grouping contains all 108 tasks exactly once.
- Unresolved scope: Integrated scientific/human acceptance remains open where the linked original tasks require real provider outputs or independent review.
- Blockers: None recorded.
- Mapping limitation: Integrated scientific/human acceptance remains open where the linked original tasks require real provider outputs or independent review.

Recorded component observations:

- observed task scope: `IMPLEMENTED_UNVERIFIED`. Runnable local product, real corpus, current software evidence, English handover and all original numbered ledgers are delivered with separate research and human-review status. The required deterministic delivery exporter produces eight owner views, seven course-week views and all 60 acceptance references from the canonical ledgers; each grouping contains all 108 tasks exactly once.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [HANDOVER.md](<../../../HANDOVER.md>), [docs/runbook.md](<../../runbook.md>), [docs/execution/acceptance_report.md](<../../execution/acceptance_report.md>), [docs/delivery/README.md](<../README.md>), [evidence/delivery/2026-09-08T09-52-01Z.json](<../../../evidence/delivery/2026-09-08T09-52-01Z.json>), [evidence/delivery/2026-09-08T09-56-03Z-input-validation.json](<../../../evidence/delivery/2026-09-08T09-56-03Z-input-validation.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Integrated scientific/human acceptance remains open where the linked original tasks require real provider outputs or independent review.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.
