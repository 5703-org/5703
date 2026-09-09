# Delivery view: suggested course week 7

Generated reporting view. The canonical ledgers below remain authoritative; this file adds no product requirement or acceptance decision.

Accountable owner and suggested course week are reporting metadata, never permissions, implementation eligibility, runtime flags or evidence of completion. Actual executor and recorded dates are shown separately. Cross-references do not count a task more than once. No calendar dates or completion percentages are inferred.

Canonical requirements, shared interfaces and evidence: [PRD.md](<../../../PRD.md>) · [SPEC.md](<../../../SPEC.md>) · [PLANS.md](<../../../PLANS.md>) · [HANDOVER.md](<../../../HANDOVER.md>) · [docs/foundation/api_contract.md](<../../foundation/api_contract.md>) · [contracts/openapi.json](<../../../contracts/openapi.json>) · [docs/execution/tasks.json](<../../execution/tasks.json>) · [docs/execution/reporting_plan.json](<../../execution/reporting_plan.json>) · [docs/execution/acceptance.json](<../../execution/acceptance.json>)

Task-ledger reconciliation timestamp (not a completion date): 2026-09-08T10:09:00.459775+00:00

This primary reporting bucket contains 34 unique tasks. A task's canonical suggested week chooses its one primary bucket. The planning packages below can mention it in other weeks as a cross-reference; these references add no completed tasks.

## Suggested allocation only

Suggested team reporting allocation only, not execution schedule, deadline or actual completion evidence.

Week convention: Course/teaching week; project_week=course_week-2 from Week 3. Optional contingency only; official dates/deadlines not confirmed

### Xianshu Zhang — suggested package

Coordinate consumer-side seam tests and accept the chat product, not isolated modules; maintain the end-of-week defect list.

- Task cross-references: [CHAT-01](<../by_owner/xianshu-zhang.md#chat-01>), [INT-06](<../by_owner/xianshu-zhang.md#int-06>), [INT-07](<../by_owner/xianshu-zhang.md#int-07>)
- Suggested deliverable paths (not claims of delivery): `docs/execution/week_07.md` (path absent), `docs/traceability.md` (path absent)
- Suggested downstream consumers: all eight workstreams
- Planned acceptance description: J1/J2/J3/J4/J6 and no-SciQ chat pass; blockers have explicit owners.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Hongle Yang — suggested package

Connect deactivation/restoration/reprocessing; separately prepare SciQ evaluation files without indexing support as textbook evidence.

- Task cross-references: [DAT-09](<../by_owner/hongle-yang.md#dat-09>), [DAT-08](<../by_owner/hongle-yang.md#dat-08>), [DAT-10](<../by_owner/hongle-yang.md#dat-10>)
- Suggested deliverable paths (not claims of delivery): `pipelines/lifecycle.py` (path absent), [evaluation/datasets/](<../../../evaluation/datasets>)
- Suggested downstream consumers: Chengzhou Liu; Zeping Liao; Chong Zhang
- Planned acceptance description: New queries exclude deactivated sources; history is unchanged or explicitly unavailable; chat has no gold mounts.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Chengzhou Liu — suggested package

Implement standalone follow-up queries, topic changes, clarification and underlying evidence reuse; record raw and prepared queries.

- Task cross-references: [CHAT-04](<../by_owner/chengzhou-liu.md#chat-04>), [RET-04](<../by_owner/chengzhou-liu.md#ret-04>), [RET-06](<../by_owner/chengzhou-liu.md#ret-06>), [RET-05](<../by_owner/chengzhou-liu.md#ret-05>)
- Suggested deliverable paths (not claims of delivery): [conversation/query.py](<../../../conversation/query.py>), `retrieval/context.py` (path absent)
- Suggested downstream consumers: Sijin Lu; Zeping Liao; Chong Zhang
- Planned acceptance description: The light follow-up uses its real referent; topic changes drop irrelevant evidence; empty retrieval differs from an outage.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Sijin Lu — suggested package

Extract runtime generation service; connect messages/history/profile/evidence and one bounded retry policy; inspect actual model payloads.

- Task cross-references: [GEN-06](<../by_owner/sijin-lu.md#gen-06>), [GEN-07](<../by_owner/sijin-lu.md#gen-07>), [GEN-08](<../by_owner/sijin-lu.md#gen-08>), [GEN-09](<../by_owner/sijin-lu.md#gen-09>), [CHAT-05](<../by_owner/sijin-lu.md#chat-05>)
- Suggested deliverable paths (not claims of delivery): [generation/service.py](<../../../generation/service.py>), `generation/tracing.py` (path absent)
- Suggested downstream consumers: Zeping Liao; Pengyuan Xia; Baiqing Huang
- Planned acceptance description: Executable HC-08–11 checks pass; profiles enter one main call, with no silent fallback or lost history.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Pengyuan Xia — suggested package

Connect save/reset/snapshot/temporary simplification and verify that disabling profiles retains conversational context.

- Task cross-references: [PER-03](<../by_owner/pengyuan-xia.md#per-03>), [PER-04](<../by_owner/pengyuan-xia.md#per-04>), [PER-05](<../by_owner/pengyuan-xia.md#per-05>), [CHAT-07](<../by_owner/pengyuan-xia.md#chat-07>)
- Suggested deliverable paths (not claims of delivery): `personalisation/service.py` (path absent), `tests/e2e/profile/` (path absent)
- Suggested downstream consumers: Sijin Lu; Baiqing Huang; Zeping Liao
- Planned acceptance description: All three policies enter actual requests; historical profile snapshots remain; temporary requests do not rewrite saved level.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Zeping Liao — suggested package

Complete shared orchestration, recent context/extractive summaries, transactional publication, retry and latest-answer revisions; sync client contracts.

- Task cross-references: [CHAT-03](<../by_owner/zeping-liao.md#chat-03>), [BE-08](<../by_owner/zeping-liao.md#be-08>), [BE-10](<../by_owner/zeping-liao.md#be-10>), [BE-12](<../by_owner/zeping-liao.md#be-12>), [BE-13](<../by_owner/zeping-liao.md#be-13>), [BE-14](<../by_owner/zeping-liao.md#be-14>), [CHAT-08](<../by_owner/zeping-liao.md#chat-08>)
- Suggested deliverable paths (not claims of delivery): [backend/app/modules/answering/](<../../../backend/app/modules/answering>), [conversation/](<../../../conversation>), [contracts/](<../../../contracts>)
- Suggested downstream consumers: Baiqing Huang; Sijin Lu; Chong Zhang
- Planned acceptance description: Duplicate send deduplicates; refresh restores; failed regeneration preserves old answer; summaries exclude future/other-session text.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Baiqing Huang — suggested package

Connect the chat workspace, evidence drawer, profiles, feedback, stop/retry/regenerate, history and corpus status.

- Task cross-references: [FE-07](<../by_owner/baiqing-huang.md#fe-07>), [FE-04](<../by_owner/baiqing-huang.md#fe-04>), [FE-10](<../by_owner/baiqing-huang.md#fe-10>), [FE-05](<../by_owner/baiqing-huang.md#fe-05>), [FE-06](<../by_owner/baiqing-huang.md#fe-06>), [FE-08](<../by_owner/baiqing-huang.md#fe-08>), [FE-09](<../by_owner/baiqing-huang.md#fe-09>), [CHAT-06](<../by_owner/baiqing-huang.md#chat-06>)
- Suggested deliverable paths (not claims of delivery): `frontend/src/features/` (path absent), `tests/e2e/` (path absent)
- Suggested downstream consumers: Chong Zhang; Zeping Liao
- Planned acceptance description: Natural multi-turn flow works; Enter/Shift+Enter, failed drafts and re-login behave correctly; controls have real effects.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Chong Zhang — suggested package

Run 12 conversation families and recovery negatives; finish independent evaluation adapters and metric math tests; label live semantic checks separately.

- Task cross-references: [QA-02](<../by_owner/chong-zhang.md#qa-02>), [QA-03](<../by_owner/chong-zhang.md#qa-03>), [QA-05](<../by_owner/chong-zhang.md#qa-05>), [CHAT-10](<../by_owner/chong-zhang.md#chat-10>)
- Suggested deliverable paths (not claims of delivery): [evaluation/conversations/](<../../../evaluation/conversations>), `tests/e2e/` (path absent), [evaluation/metrics/](<../../../evaluation/metrics>)
- Suggested downstream consumers: Xianshu Zhang; all developers
- Planned acceptance description: No-SciQ operation, reference/clarification/topic/summary/profile/revision checks inspect actual records.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

## Actual evidence and demonstration material

The task records below quote the current ledger, independently of the suggested package. Their actual evidence links are the available demonstration and check material; an empty or null field stays unrecorded. The export does not create a meeting, human demonstration or historical completion event.

## Carry-over and unresolved work

These are currently recorded unresolved items for this reporting bucket, not claims that a calendar week elapsed or work was late.

- [INT-06](<../by_owner/xianshu-zhang.md#int-06>) (`REAL_FLOW_VERIFIED`): Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report. Blockers: None recorded.
- [INT-07](<../by_owner/xianshu-zhang.md#int-07>) (`REAL_FLOW_VERIFIED`): Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report. Blockers: None recorded.
- [DAT-09](<../by_owner/hongle-yang.md#dat-09>) (`REAL_FLOW_VERIFIED`): Formal answer-model runs remain separate; a prefix technical rehearsal is not a full dataset result. Blockers: None recorded.
- [DAT-10](<../by_owner/hongle-yang.md#dat-10>) (`REAL_FLOW_VERIFIED`): Check each browser attempt and its terminal pointer evidence; earlier interrupted attempts are preserved. Blockers: None recorded.
- [RET-06](<../by_owner/chengzhou-liu.md#ret-06>) (`REAL_FLOW_VERIFIED`): Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report. Blockers: None recorded.
- [GEN-06](<../by_owner/sijin-lu.md#gen-06>) (`MOCK_TEST_PASSED`): No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits. Blockers: None recorded.
- [GEN-07](<../by_owner/sijin-lu.md#gen-07>) (`REAL_FLOW_VERIFIED`): Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report. Blockers: None recorded.
- [GEN-08](<../by_owner/sijin-lu.md#gen-08>) (`MOCK_TEST_PASSED`): No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits. Blockers: None recorded.
- [GEN-09](<../by_owner/sijin-lu.md#gen-09>) (`MOCK_TEST_PASSED`): No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits. Blockers: None recorded.
- [PER-03](<../by_owner/pengyuan-xia.md#per-03>) (`IMPLEMENTED_UNVERIFIED`): Requested long explanations did not produce long answers in this mock matrix. Actual differentiated wording, supported meaning and independent scientific review remain unverified; software checks do not close presentation quality. Blockers: None recorded.
- [PER-04](<../by_owner/pengyuan-xia.md#per-04>) (`MOCK_TEST_PASSED`): Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots. Blockers: None recorded.
- [PER-05](<../by_owner/pengyuan-xia.md#per-05>) (`MOCK_TEST_PASSED`): Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots. Blockers: None recorded.
- [BE-08](<../by_owner/zeping-liao.md#be-08>) (`REAL_FLOW_VERIFIED`): Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report. Blockers: None recorded.
- [BE-10](<../by_owner/zeping-liao.md#be-10>) (`REAL_FLOW_VERIFIED`): Provider execution is simulated where fault injection is required; actual external exactly-once execution is not promised. Blockers: None recorded.
- [BE-12](<../by_owner/zeping-liao.md#be-12>) (`REAL_FLOW_VERIFIED`): Provider execution is simulated where fault injection is required; actual external exactly-once execution is not promised. Blockers: None recorded.
- [BE-13](<../by_owner/zeping-liao.md#be-13>) (`REAL_FLOW_VERIFIED`): Provider execution is simulated where fault injection is required; actual external exactly-once execution is not promised. Blockers: None recorded.
- [FE-04](<../by_owner/baiqing-huang.md#fe-04>) (`REAL_FLOW_VERIFIED`): Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim. Blockers: None recorded.
- [FE-05](<../by_owner/baiqing-huang.md#fe-05>) (`REAL_FLOW_VERIFIED`): Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim. Blockers: None recorded.
- [FE-06](<../by_owner/baiqing-huang.md#fe-06>) (`REAL_FLOW_VERIFIED`): Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim. Blockers: None recorded.
- [FE-07](<../by_owner/baiqing-huang.md#fe-07>) (`REAL_FLOW_VERIFIED`): Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim. Blockers: None recorded.
- [FE-08](<../by_owner/baiqing-huang.md#fe-08>) (`REAL_FLOW_VERIFIED`): Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim. Blockers: None recorded.
- [FE-09](<../by_owner/baiqing-huang.md#fe-09>) (`REAL_FLOW_VERIFIED`): Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim. Blockers: None recorded.
- [FE-10](<../by_owner/baiqing-huang.md#fe-10>) (`REAL_FLOW_VERIFIED`): Check each browser attempt and its terminal pointer evidence; earlier interrupted attempts are preserved. Blockers: None recorded.
- [QA-02](<../by_owner/chong-zhang.md#qa-02>) (`REAL_FLOW_VERIFIED`): Formal answer-model runs remain separate; a prefix technical rehearsal is not a full dataset result. Blockers: None recorded.
- [QA-03](<../by_owner/chong-zhang.md#qa-03>) (`MOCK_TEST_PASSED`): Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings. Blockers: None recorded.
- [QA-05](<../by_owner/chong-zhang.md#qa-05>) (`MOCK_TEST_PASSED`): Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings. Blockers: None recorded.
- [CHAT-03](<../by_owner/zeping-liao.md#chat-03>) (`MOCK_TEST_PASSED`): Broad real-answer semantic correctness is not established by deterministic query fixtures. Blockers: None recorded.
- [CHAT-04](<../by_owner/chengzhou-liu.md#chat-04>) (`MOCK_TEST_PASSED`): Broad real-answer semantic correctness is not established by deterministic query fixtures. Blockers: None recorded.
- [CHAT-05](<../by_owner/sijin-lu.md#chat-05>) (`REAL_FLOW_VERIFIED`): Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report. Blockers: None recorded.
- [CHAT-06](<../by_owner/baiqing-huang.md#chat-06>) (`REAL_FLOW_VERIFIED`): Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim. Blockers: None recorded.
- [CHAT-07](<../by_owner/pengyuan-xia.md#chat-07>) (`MOCK_TEST_PASSED`): Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots. Blockers: None recorded.
- [CHAT-08](<../by_owner/zeping-liao.md#chat-08>) (`MOCK_TEST_PASSED`): Provider failures are deliberately simulated. Current actual-corpus browser/API revision checks provide separate end-to-end evidence. Blockers: None recorded.
- [CHAT-10](<../by_owner/chong-zhang.md#chat-10>) (`MOCK_TEST_PASSED`): Software fixtures and lexical/statistical proxies do not substitute for live semantic outcomes, source judgments or human ratings. Blockers: None recorded.

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
- Upstream collaborators (derived from those dependencies): [CHAT-06](<../by_owner/baiqing-huang.md#chat-06>) — Baiqing Huang; [RET-05](<../by_owner/chengzhou-liu.md#ret-05>) — Chengzhou Liu; [GEN-05](<../by_owner/sijin-lu.md#gen-05>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [INT-07](<../by_owner/xianshu-zhang.md#int-07>) — Xianshu Zhang; [QA-07](<../by_owner/chong-zhang.md#qa-07>) — Chong Zhang
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
- Upstream collaborators (derived from those dependencies): [INT-06](<../by_owner/xianshu-zhang.md#int-06>) — Xianshu Zhang; [BE-14](<../by_owner/zeping-liao.md#be-14>) — Zeping Liao; [CHAT-07](<../by_owner/pengyuan-xia.md#chat-07>) — Pengyuan Xia; [CHAT-08](<../by_owner/zeping-liao.md#chat-08>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [INT-08](<../by_owner/xianshu-zhang.md#int-08>) — Xianshu Zhang
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

## DAT-09

Acquire SciQ for evaluation only. Record actual revision/splits/checksums. Export stem-only open-answer input and separately shuffled MCQ input; keep correct answer/support/distractors evaluator-only except MCQ candidate options. The chat runtime and textbook index have no SciQ dependency.

- Accountable owner (reporting): Hongle Yang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G2
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["DAT-01", "QA-01"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "DAT-01"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-01"}]`
- Upstream collaborators (derived from those dependencies): [DAT-01](<../by_owner/hongle-yang.md#dat-01>) — Hongle Yang; [QA-01](<../by_owner/chong-zhang.md#qa-01>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [QA-02](<../by_owner/chong-zhang.md#qa-02>) — Chong Zhang
- Source files recorded for this implementation: [pipelines](<../../../pipelines>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>), [docs/data_rebuild.md](<../../data_rebuild.md>)
- Changed files recorded by the ledger: [pipelines](<../../../pipelines>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>), [docs/data_rebuild.md](<../../data_rebuild.md>)
- Shared entry / interface boundary: Administrator corpus routes and ingestion/build CLI / Corpus processing
- Persisted effect / consumer: Assets, versions, processing runs, source units, chunks, releases / Retrieval and source viewer
- Local acceptance clause: Acquire SciQ for evaluation only. Record actual revision/splits/checksums. Export stem-only open-answer input and separately shuffled MCQ input; keep correct answer/support/distractors evaluator-only except MCQ candidate options. The chat runtime and textbook index have no SciQ dependency.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_sciq_acquisition.py](<../../../tests/unit/test_sciq_acquisition.py>), [tests/unit/test_evaluation_backend.py](<../../../tests/unit/test_evaluation_backend.py>)
- Recorded current check nodes: `["tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_openqa]", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_mcq]", "tests.unit.test_evaluation_backend::test_registered_hash_rejects_post_freeze_question_or_gold_injection", "tests.unit.test_evaluation_backend::test_server_cancellation_retains_all_scheduled_items", "tests.unit.test_evaluation_backend::test_admin_api_create_freeze_start_results_and_role_denial", "tests.unit.test_sciq_acquisition::test_lossless_parquet_unicode_and_all_item_public_preflight_boundary", "tests.unit.test_sciq_acquisition::test_official_byte_hash_mismatch_stops_before_raw_publication"]`
- Acceptance references: [AC-17](<../acceptance.md#ac-17>), [AC-23](<../acceptance.md#ac-23>), [AC-46](<../acceptance.md#ac-46>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/sciq/acquisition.json](<../../../evidence/sciq/acquisition.json>), [docs/sciq_acquisition.md](<../../sciq_acquisition.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Official pinned SciQ acquisition records all 13,679 rows and split/file hashes. Actual stem-only export and separate deterministic MCQ preflight ran. All 48 duplicate-option anomalies remain recorded; strict whole-split MCQ rejection is preserved.
- Unresolved scope: Formal answer-model runs remain separate; a prefix technical rehearsal is not a full dataset result.
- Blockers: None recorded.
- Mapping limitation: Formal answer-model runs remain separate; a prefix technical rehearsal is not a full dataset result.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Official pinned SciQ acquisition records all 13,679 rows and split/file hashes. Actual stem-only export and separate deterministic MCQ preflight ran. All 48 duplicate-option anomalies remain recorded; strict whole-split MCQ rejection is preserved.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/sciq/acquisition.json](<../../../evidence/sciq/acquisition.json>), [docs/sciq_acquisition.md](<../../sciq_acquisition.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Formal answer-model runs remain separate; a prefix technical rehearsal is not a full dataset result.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## DAT-10

Connect document lifecycle changes. Wire reprocessing, deactivation, restoration and release rollback to future retrieval. Failed replacements preserve the old release; historical evidence keeps original content or an unavailable state.

- Accountable owner (reporting): Hongle Yang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["DAT-08", "BE-06", "RET-06"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "DAT-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-06"}]`
- Upstream collaborators (derived from those dependencies): [DAT-08](<../by_owner/hongle-yang.md#dat-08>) — Hongle Yang; [BE-06](<../by_owner/zeping-liao.md#be-06>) — Zeping Liao; [RET-06](<../by_owner/chengzhou-liu.md#ret-06>) — Chengzhou Liu
- Downstream collaborators (reverse dependency references): [DAT-12](<../by_owner/hongle-yang.md#dat-12>) — Hongle Yang
- Source files recorded for this implementation: [pipelines](<../../../pipelines>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>), [docs/data_rebuild.md](<../../data_rebuild.md>)
- Changed files recorded by the ledger: [pipelines](<../../../pipelines>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>), [docs/data_rebuild.md](<../../data_rebuild.md>)
- Shared entry / interface boundary: Administrator corpus routes and ingestion/build CLI / Corpus processing
- Persisted effect / consumer: Assets, versions, processing runs, source units, chunks, releases / Retrieval and source viewer
- Local acceptance clause: Connect document lifecycle changes. Wire reprocessing, deactivation, restoration and release rollback to future retrieval. Failed replacements preserve the old release; historical evidence keeps original content or an unavailable state.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_corpus_runtime.py](<../../../tests/integration/test_corpus_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_corpus_runtime::test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "tests.integration.test_corpus_runtime::test_quarantine_inspectable_exclusion_and_processing_lineage", "tests.integration.test_corpus_runtime::test_reprocessing_creates_new_chunks_while_old_evidence_survives", "tests.integration.test_corpus_runtime::test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "tests.integration.test_corpus_runtime::test_processing_diff_reports_split_groups_by_overlapping_source_spans", "tests.integration.test_corpus_runtime::test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "tests.integration.test_corpus_runtime::test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "tests.integration.test_corpus_runtime::test_source_deactivation_filters_current_retrieval_and_restore_recovers", "tests.integration.test_corpus_runtime::test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks", "tests.integration.test_corpus_runtime::test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "tests.integration.test_corpus_runtime::test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest", "tests.integration.test_corpus_runtime::test_legacy_release_without_saved_hashes_requires_explicit_new_build", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[cancel]", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[recover]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[cancel]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[recover]"]`
- Acceptance references: [AC-14](<../acceptance.md#ac-14>), [AC-26](<../acceptance.md#ac-26>), [AC-27](<../acceptance.md#ac-27>), [AC-28](<../acceptance.md#ac-28>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/openstax/corpus-report.json](<../../../evidence/openstax/corpus-report.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Document/reprocessing/source-visibility and immutable release lifecycle are exercised in current PostgreSQL tests. Official-source administrator browser version switching has separate completed evidence in the frontend audit.
- Unresolved scope: Check each browser attempt and its terminal pointer evidence; earlier interrupted attempts are preserved.
- Blockers: None recorded.
- Mapping limitation: Check each browser attempt and its terminal pointer evidence; earlier interrupted attempts are preserved.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Document/reprocessing/source-visibility and immutable release lifecycle are exercised in current PostgreSQL tests. Official-source administrator browser version switching has separate completed evidence in the frontend audit.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/openstax/corpus-report.json](<../../../evidence/openstax/corpus-report.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Check each browser attempt and its terminal pointer evidence; earlier interrupted attempts are preserved.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## RET-06

Enforce current source visibility. Filter inactive/unavailable sources on every new request. Omit answer/query caches initially; if later added, implement versioned invalidation and prove cache hits cannot expose stale sources.

- Accountable owner (reporting): Chengzhou Liu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["RET-03", "BE-06"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-03"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-06"}]`
- Upstream collaborators (derived from those dependencies): [RET-03](<../by_owner/chengzhou-liu.md#ret-03>) — Chengzhou Liu; [BE-06](<../by_owner/zeping-liao.md#be-06>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [DAT-10](<../by_owner/hongle-yang.md#dat-10>) — Hongle Yang; [QA-11](<../by_owner/chong-zhang.md#qa-11>) — Chong Zhang
- Source files recorded for this implementation: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Changed files recorded by the ledger: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Shared entry / interface boundary: Shared answer service and evaluation runner / Retrieval and query preparation
- Persisted effect / consumer: Release vectors and immutable retrieval/evidence snapshots / Generation prompts and evidence viewer
- Local acceptance clause: Enforce current source visibility. Filter inactive/unavailable sources on every new request. Omit answer/query caches initially; if later added, implement versioned invalidation and prove cache hits cannot expose stale sources.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_pipeline.py](<../../../tests/unit/test_pipeline.py>), [tests/unit/test_retrieval.py](<../../../tests/unit/test_retrieval.py>), [tests/integration/test_corpus_runtime.py](<../../../tests/integration/test_corpus_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_corpus_runtime::test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "tests.integration.test_corpus_runtime::test_quarantine_inspectable_exclusion_and_processing_lineage", "tests.integration.test_corpus_runtime::test_reprocessing_creates_new_chunks_while_old_evidence_survives", "tests.integration.test_corpus_runtime::test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "tests.integration.test_corpus_runtime::test_processing_diff_reports_split_groups_by_overlapping_source_spans", "tests.integration.test_corpus_runtime::test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "tests.integration.test_corpus_runtime::test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "tests.integration.test_corpus_runtime::test_source_deactivation_filters_current_retrieval_and_restore_recovers", "tests.integration.test_corpus_runtime::test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks", "tests.integration.test_corpus_runtime::test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "tests.integration.test_corpus_runtime::test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest", "tests.integration.test_corpus_runtime::test_legacy_release_without_saved_hashes_requires_explicit_new_build", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[cancel]", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[recover]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[cancel]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[recover]", "tests.unit.test_pipeline::test_clean_preserves_scientific_symbols_and_ambiguous_hard_hyphens", "tests.unit.test_pipeline::test_txt_heading_quality_and_original_text_remain_available", "tests.unit.test_pipeline::test_physical_pdf_pages_carry_real_sections_and_flag_removed_furniture", "tests.unit.test_pipeline::test_actual_pypdf_extracts_authored_bytes_with_physical_pages", "tests.unit.test_pipeline::test_pdf_page_extraction_failure_preserves_other_pages_and_blocks_publication", "tests.unit.test_pipeline::test_chunks_repeatable_unique_across_sections_and_reconstruct_exact_spans", "tests.unit.test_pipeline::test_exact_tokenizer_bounds_long_text_and_no_unmapped_character_loss", "tests.unit.test_pipeline::test_excluded_units_and_section_changes_never_merge", "tests.unit.test_pipeline::test_fixed_and_structure_strategies_preserve_source_coverage_with_distinct_boundaries", "tests.unit.test_pipeline::test_bookmarks_prevent_contents_false_sections_and_preserve_midpage_continuation", "tests.unit.test_pipeline::test_low_text_visual_page_blocks_while_prose_retains_visual_limitations", "tests.unit.test_pipeline::test_actual_unbookmarked_pdf_prefix_uses_page_local_labels_and_preserves_v4", "tests.unit.test_retrieval::test_mock_embedding_is_normalized_repeatable_and_content_sensitive", "tests.unit.test_retrieval::test_bm25_matches_hand_calculated_term_and_stable_ties", "tests.unit.test_retrieval::test_rrf_uses_one_based_ranks_and_never_raw_score_magnitudes", "tests.unit.test_retrieval::test_e5_actual_tokenizer_prefixes_dimension_and_no_silent_truncation", "tests.unit.test_retrieval::test_reranker_records_actual_spans_limits_candidate_count_and_validates_outputs"]`
- Acceptance references: [AC-14](<../acceptance.md#ac-14>), [AC-27](<../acceptance.md#ac-27>), [AC-41](<../acceptance.md#ac-41>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/corpus-report.json](<../../../evidence/openstax/corpus-report.json>), [evidence/openstax/v5/publication.json](<../../../evidence/openstax/v5/publication.json>), [evidence/openstax/v5/formal-source-validation-summary.json](<../../../evidence/openstax/v5/formal-source-validation-summary.json>), [evidence/openstax/v5/retrieval-verification.json](<../../../evidence/openstax/v5/retrieval-verification.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Four actual official full books, 4,638 physical pages, pinned local E5 and PostgreSQL/pgvector. Current release 4f11bd70-a486-4d16-b216-78cfe499530a is documented per book in evidence/openstax/corpus-report.json; all retained source decisions, actual vector counts, original locators and retrieval outcomes are linked. Earlier corpus versions and answers remain immutable.
- Unresolved scope: Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.
- Blockers: None recorded.
- Mapping limitation: Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Four actual official full books, 4,638 physical pages, pinned local E5 and PostgreSQL/pgvector. Current release 4f11bd70-a486-4d16-b216-78cfe499530a is documented per book in evidence/openstax/corpus-report.json; all retained source decisions, actual vector counts, original locators and retrieval outcomes are linked. Earlier corpus versions and answers remain immutable.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/corpus-report.json](<../../../evidence/openstax/corpus-report.json>), [evidence/openstax/v5/publication.json](<../../../evidence/openstax/v5/publication.json>), [evidence/openstax/v5/formal-source-validation-summary.json](<../../../evidence/openstax/v5/formal-source-validation-summary.json>), [evidence/openstax/v5/retrieval-verification.json](<../../../evidence/openstax/v5/retrieval-verification.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## GEN-06

Bound preparation, generation and repair calls. Share finite request time/call counters across optional query preparation, main generation and transient retry/one format repair. Persist totals across retries and restart; offline study items have explicit separate budgets. Generation handover migration: Extract a reusable GenerationService. Preparation, generation, transient retries and one format repair share a four-call/180-second active-execution allowance with backend-persisted counters. Avoid multiplying retries across layers.

- Accountable owner (reporting): Sijin Lu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["GEN-05", "BE-07"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-07"}]`
- Upstream collaborators (derived from those dependencies): [GEN-05](<../by_owner/sijin-lu.md#gen-05>) — Sijin Lu; [BE-07](<../by_owner/zeping-liao.md#be-07>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [QA-06](<../by_owner/chong-zhang.md#qa-06>) — Chong Zhang; [QA-11](<../by_owner/chong-zhang.md#qa-11>) — Chong Zhang
- Source files recorded for this implementation: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Changed files recorded by the ledger: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Shared entry / interface boundary: Shared answer service through worker or offline runner / GenerationService
- Persisted effect / consumer: Attempts, prompt metadata and typed response/evidence snapshots / Chat renderer and evaluation scorer
- Local acceptance clause: Bound preparation, generation and repair calls. Share finite request time/call counters across optional query preparation, main generation and transient retry/one format repair. Persist totals across retries and restart; offline study items have explicit separate budgets.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_generation_contracts.py](<../../../tests/unit/test_generation_contracts.py>), [tests/unit/test_generation_engine.py](<../../../tests/unit/test_generation_engine.py>), [tests/unit/test_mock_evidence_coverage.py](<../../../tests/unit/test_mock_evidence_coverage.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>)
- Recorded current check nodes: `["tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_generation_contracts::test_chat_message_never_requires_choices", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[gold_answer]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[history]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[summary]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[model]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[owner]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[options]", "tests.unit.test_generation_contracts::test_chat_preserves_complete_prose_and_all_required_fields", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[True]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[False]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[nan]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[inf]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[-0.1]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[1.1]", "tests.unit.test_generation_contracts::test_refusal_has_distinct_empty_and_null_invariants", "tests.unit.test_generation_contracts::test_social_and_clarification_have_no_compact_factual_answer[social]", "tests.unit.test_generation_contracts::test_social_and_clarification_have_no_compact_factual_answer[clarification]", "tests.unit.test_generation_contracts::test_mcq_requires_exact_four_labels_and_normalized_distinct_options", "tests.unit.test_generation_contracts::test_mcq_preserves_original_option_text_for_exact_output_comparison", "tests.unit.test_generation_contracts::test_legacy_mcq_refusal_enum_is_separate_from_chat", "tests.unit.test_generation_engine::test_strict_json_negatives[\`\`\`json\\n{}\\n\`\`\`]", "tests.unit.test_generation_engine::test_strict_json_negatives[{} {}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{} trailing]", "tests.unit.test_generation_engine::test_strict_json_negatives[[]]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":NaN}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":Infinity}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":1,\"x\":2}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"nested\":{\"x\":1,\"x\":2}}]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates0]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates1]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates2]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates3]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates4]", "tests.unit.test_generation_engine::test_actual_role_order_profile_off_and_frozen_benchmark_boundary", "tests.unit.test_generation_engine::test_mock_changes_with_current_evidence_and_history_sensitive_query", "tests.unit.test_generation_engine::test_shared_four_call_budget_covers_transient_and_one_format_repair", "tests.unit.test_generation_engine::test_invalid_twice_is_error_not_refusal_and_retry_retains_budget", "tests.unit.test_generation_engine::test_complete_json_with_length_finish_never_publishes_or_repairs", "tests.unit.test_generation_engine::test_context_budget_includes_profile_schema_and_output_and_drops_whole_chunks", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload0-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload1-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload2-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload3-EMPTY_RESPONSE]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload4-OUTPUT_TRUNCATED]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[429-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[500-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[503-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[401-False]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[403-False]", "tests.unit.test_generation_engine::test_http_adapter_sends_actual_roles_and_unknown_usage_remains_null", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[How do I configure Kubernetes ingress TLS certificates?]", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[Who won the 2026 Formula One world championship?]", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[What is the current exchange rate between the yen and the euro?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How does negative feedback maintain homeostasis?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What are the functions of erythrocytes, leukocytes and platelets?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How does glycolysis produce ATP from glucose?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How do natural selection and genetic drift differ?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What is the difference between a food chain and a food web?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What is the difference between prokaryotic and eukaryotic cells?]", "tests.unit.test_mock_evidence_coverage::test_actual_learning_objective_question_is_not_mistaken_for_an_answer", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Why does it need light?]", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Make it simpler]", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Give an example]", "tests.unit.test_mock_evidence_coverage::test_numbers_and_negation_are_required_content[Explain nuclear fusion in 2031]", "tests.unit.test_mock_evidence_coverage::test_numbers_and_negation_are_required_content[Explain nuclear fusion without heat]", "tests.unit.test_mock_evidence_coverage::test_terms_scattered_over_unrelated_paragraphs_do_not_qualify_an_excerpt", "tests.unit.test_mock_evidence_coverage::test_provider_scores_are_not_used_to_qualify_mock_evidence", "tests.unit.test_mock_evidence_coverage::test_standard_inflections_do_not_require_unrelated_keyword_exceptions", "tests.unit.test_mock_evidence_coverage::test_grounded_teaching_base_retains_energy_form_answer", "tests.unit.test_mock_evidence_coverage::test_source_exercise_question_does_not_become_an_asserted_answer", "tests.unit.test_mock_evidence_coverage::test_learner_correction_completes_an_ambiguous_turn_with_the_named_topic"]`
- Acceptance references: [AC-11](<../acceptance.md#ac-11>), [AC-13](<../acceptance.md#ac-13>), [AC-24](<../acceptance.md#ac-24>), [AC-25](<../acceptance.md#ac-25>), [HC-08](<../acceptance.md#hc-08>), [HC-10](<../acceptance.md#hc-10>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/mock-evidence-replay.md](<../../execution/mock-evidence-replay.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current strict chat/MCQ schemas, mode-specific prompts, no-gold boundary, simulated provider failures, finite shared retries/repair and deterministic response policies passed their executed tests. Actual-source mock replays retain unsupported/refused cases.
- Unresolved scope: No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.
- Blockers: None recorded.
- Mapping limitation: No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.

Handoff consumers: `["Zeping Liao"]`

Handover actions: Extract a reusable GenerationService. Preparation, generation, transient retries and one format repair share a four-call/180-second active-execution allowance with backend-persisted counters. Avoid multiplying retries across layers.

Handover checks: `["HC-08", "HC-10"]`

Source asset state: One format repair lives in smoke run_case, not the adapter; telemetry is accumulated only there.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Current strict chat/MCQ schemas, mode-specific prompts, no-gold boundary, simulated provider failures, finite shared retries/repair and deterministic response policies passed their executed tests. Actual-source mock replays retain unsupported/refused cases.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/mock-evidence-replay.md](<../../execution/mock-evidence-replay.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## GEN-07

Connect generation and evidence traces. Link actual prompt, selected evidence, model/configuration and attempt to each saved answer. Resolving a citation returns its original authorised snapshot, never a newly guessed source. Generation handover migration: Map LegacyEvidence into request-local EvidenceSnapshot with chunk, asset, processing, pages, hash and request identity. Persist only actual prompt text and remap IDs when reusing historical evidence.

- Accountable owner (reporting): Sijin Lu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["GEN-05", "BE-09"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-09"}]`
- Upstream collaborators (derived from those dependencies): [GEN-05](<../by_owner/sijin-lu.md#gen-05>) — Sijin Lu; [BE-09](<../by_owner/zeping-liao.md#be-09>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [PER-07](<../by_owner/pengyuan-xia.md#per-07>) — Pengyuan Xia
- Source files recorded for this implementation: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Changed files recorded by the ledger: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Shared entry / interface boundary: Shared answer service through worker or offline runner / GenerationService
- Persisted effect / consumer: Attempts, prompt metadata and typed response/evidence snapshots / Chat renderer and evaluation scorer
- Local acceptance clause: Connect generation and evidence traces. Link actual prompt, selected evidence, model/configuration and attempt to each saved answer. Resolving a citation returns its original authorised snapshot, never a newly guessed source.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_chat_evidence_reuse.py](<../../../tests/integration/test_chat_evidence_reuse.py>)
- Recorded current check nodes: `["tests.integration.test_chat_evidence_reuse::test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic", "tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation"]`
- Acceptance references: [AC-08](<../acceptance.md#ac-08>), [AC-14](<../acceptance.md#ac-14>), [AC-41](<../acceptance.md#ac-41>), [HC-09](<../acceptance.md#hc-09>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Actual HTTP, durable worker, real official-source E5 retrieval, budgeted source selection, saved prompt/context/profile traces, request-local citations, feedback and revision history executed on the published corpus.
- Unresolved scope: Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.
- Blockers: None recorded.
- Mapping limitation: Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.

Handoff consumers: `["Hongle Yang", "Chengzhou Liu", "Zeping Liao"]`

Handover actions: Map LegacyEvidence into request-local EvidenceSnapshot with chunk, asset, processing, pages, hash and request identity. Persist only actual prompt text and remap IDs when reusing historical evidence.

Handover checks: `["HC-09"]`

Source asset state: Evidence has only evidence_id/text/source; responses have usage and latency but no complete citation persistence.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Actual HTTP, durable worker, real official-source E5 retrieval, budgeted source selection, saved prompt/context/profile traces, request-local citations, feedback and revision history executed on the published corpus.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Only answering is mock; these are software/provenance observations. Live answer correctness and independent scientific/relevance/teaching review are not established. Full visual/equation fidelity remains bounded by the source report.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## GEN-08

Isolate benchmark policy without disabling product context. benchmark_openqa/benchmark_mcq force empty history/summary/profile and no gold/support. Interactive chat still reads its real session. Test mode dispatch before provider calls and prohibit evaluator fields in generated requests. Generation handover migration: Add mode-boundary fixtures first, then enforce runtime isolation: benchmarks clear history/profile/summary, while chat retains them. Removing evaluator mounts does not disable chat. Connect the formal runner as soon as its implementation artifacts are ready.

- Accountable owner (reporting): Sijin Lu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G3
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["GEN-05", "QA-03"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-03"}]`
- Upstream collaborators (derived from those dependencies): [GEN-05](<../by_owner/sijin-lu.md#gen-05>) — Sijin Lu; [QA-03](<../by_owner/chong-zhang.md#qa-03>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [GEN-10](<../by_owner/sijin-lu.md#gen-10>) — Sijin Lu; [QA-07](<../by_owner/chong-zhang.md#qa-07>) — Chong Zhang; [CHAT-09](<../by_owner/chong-zhang.md#chat-09>) — Chong Zhang
- Source files recorded for this implementation: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Changed files recorded by the ledger: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Shared entry / interface boundary: Shared answer service through worker or offline runner / GenerationService
- Persisted effect / consumer: Attempts, prompt metadata and typed response/evidence snapshots / Chat renderer and evaluation scorer
- Local acceptance clause: Isolate benchmark policy without disabling product context. benchmark_openqa/benchmark_mcq force empty history/summary/profile and no gold/support. Interactive chat still reads its real session. Test mode dispatch before provider calls and prohibit evaluator fields in generated requests.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_generation_contracts.py](<../../../tests/unit/test_generation_contracts.py>), [tests/unit/test_generation_engine.py](<../../../tests/unit/test_generation_engine.py>), [tests/unit/test_mock_evidence_coverage.py](<../../../tests/unit/test_mock_evidence_coverage.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>)
- Recorded current check nodes: `["tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_generation_contracts::test_chat_message_never_requires_choices", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[gold_answer]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[history]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[summary]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[model]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[owner]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[options]", "tests.unit.test_generation_contracts::test_chat_preserves_complete_prose_and_all_required_fields", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[True]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[False]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[nan]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[inf]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[-0.1]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[1.1]", "tests.unit.test_generation_contracts::test_refusal_has_distinct_empty_and_null_invariants", "tests.unit.test_generation_contracts::test_social_and_clarification_have_no_compact_factual_answer[social]", "tests.unit.test_generation_contracts::test_social_and_clarification_have_no_compact_factual_answer[clarification]", "tests.unit.test_generation_contracts::test_mcq_requires_exact_four_labels_and_normalized_distinct_options", "tests.unit.test_generation_contracts::test_mcq_preserves_original_option_text_for_exact_output_comparison", "tests.unit.test_generation_contracts::test_legacy_mcq_refusal_enum_is_separate_from_chat", "tests.unit.test_generation_engine::test_strict_json_negatives[\`\`\`json\\n{}\\n\`\`\`]", "tests.unit.test_generation_engine::test_strict_json_negatives[{} {}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{} trailing]", "tests.unit.test_generation_engine::test_strict_json_negatives[[]]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":NaN}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":Infinity}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":1,\"x\":2}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"nested\":{\"x\":1,\"x\":2}}]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates0]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates1]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates2]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates3]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates4]", "tests.unit.test_generation_engine::test_actual_role_order_profile_off_and_frozen_benchmark_boundary", "tests.unit.test_generation_engine::test_mock_changes_with_current_evidence_and_history_sensitive_query", "tests.unit.test_generation_engine::test_shared_four_call_budget_covers_transient_and_one_format_repair", "tests.unit.test_generation_engine::test_invalid_twice_is_error_not_refusal_and_retry_retains_budget", "tests.unit.test_generation_engine::test_complete_json_with_length_finish_never_publishes_or_repairs", "tests.unit.test_generation_engine::test_context_budget_includes_profile_schema_and_output_and_drops_whole_chunks", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload0-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload1-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload2-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload3-EMPTY_RESPONSE]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload4-OUTPUT_TRUNCATED]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[429-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[500-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[503-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[401-False]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[403-False]", "tests.unit.test_generation_engine::test_http_adapter_sends_actual_roles_and_unknown_usage_remains_null", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[How do I configure Kubernetes ingress TLS certificates?]", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[Who won the 2026 Formula One world championship?]", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[What is the current exchange rate between the yen and the euro?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How does negative feedback maintain homeostasis?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What are the functions of erythrocytes, leukocytes and platelets?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How does glycolysis produce ATP from glucose?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How do natural selection and genetic drift differ?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What is the difference between a food chain and a food web?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What is the difference between prokaryotic and eukaryotic cells?]", "tests.unit.test_mock_evidence_coverage::test_actual_learning_objective_question_is_not_mistaken_for_an_answer", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Why does it need light?]", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Make it simpler]", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Give an example]", "tests.unit.test_mock_evidence_coverage::test_numbers_and_negation_are_required_content[Explain nuclear fusion in 2031]", "tests.unit.test_mock_evidence_coverage::test_numbers_and_negation_are_required_content[Explain nuclear fusion without heat]", "tests.unit.test_mock_evidence_coverage::test_terms_scattered_over_unrelated_paragraphs_do_not_qualify_an_excerpt", "tests.unit.test_mock_evidence_coverage::test_provider_scores_are_not_used_to_qualify_mock_evidence", "tests.unit.test_mock_evidence_coverage::test_standard_inflections_do_not_require_unrelated_keyword_exceptions", "tests.unit.test_mock_evidence_coverage::test_grounded_teaching_base_retains_energy_form_answer", "tests.unit.test_mock_evidence_coverage::test_source_exercise_question_does_not_become_an_asserted_answer", "tests.unit.test_mock_evidence_coverage::test_learner_correction_completes_an_ambiguous_turn_with_the_named_topic"]`
- Acceptance references: [AC-07](<../acceptance.md#ac-07>), [AC-17](<../acceptance.md#ac-17>), [AC-23](<../acceptance.md#ac-23>), [AC-30](<../acceptance.md#ac-30>), [AC-36](<../acceptance.md#ac-36>), [AC-37](<../acceptance.md#ac-37>), [AC-46](<../acceptance.md#ac-46>), [HC-03](<../acceptance.md#hc-03>), [HC-09](<../acceptance.md#hc-09>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/mock-evidence-replay.md](<../../execution/mock-evidence-replay.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current strict chat/MCQ schemas, mode-specific prompts, no-gold boundary, simulated provider failures, finite shared retries/repair and deterministic response policies passed their executed tests. Actual-source mock replays retain unsupported/refused cases.
- Unresolved scope: No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.
- Blockers: None recorded.
- Mapping limitation: No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.

Handoff consumers: `["Chong Zhang", "Zeping Liao"]`

Handover actions: Add mode-boundary fixtures first, then enforce runtime isolation: benchmarks clear history/profile/summary, while chat retains them. Removing evaluator mounts does not disable chat. Connect the formal runner as soon as its implementation artifacts are ready.

Handover checks: `["HC-03", "HC-09"]`

Source asset state: Omitting history in old prompts does not prove mode isolation; the old plan labels this G5.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Current strict chat/MCQ schemas, mode-specific prompts, no-gold boundary, simulated provider failures, finite shared retries/repair and deterministic response policies passed their executed tests. Actual-source mock replays retain unsupported/refused cases.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/mock-evidence-replay.md](<../../execution/mock-evidence-replay.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## GEN-09

Apply profile rules in main chat generation. Add compiled policy and per-turn style requests to the existing chat prompt with a frozen profile snapshot. No compulsory second child call. Failed new generation cannot erase previous successful turns; no-profile chat keeps history. Generation handover migration: Apply compiled profile and per-turn presentation requests in the main chat generation call, without a mandatory second call. Keep C0/C1/C2 studies in evaluation and independent of stored chat messages.

- Accountable owner (reporting): Sijin Lu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["PER-03", "GEN-05"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-03"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-05"}]`
- Upstream collaborators (derived from those dependencies): [PER-03](<../by_owner/pengyuan-xia.md#per-03>) — Pengyuan Xia; [GEN-05](<../by_owner/sijin-lu.md#gen-05>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [GEN-11](<../by_owner/sijin-lu.md#gen-11>) — Sijin Lu; [PER-05](<../by_owner/pengyuan-xia.md#per-05>) — Pengyuan Xia; [PER-06](<../by_owner/pengyuan-xia.md#per-06>) — Pengyuan Xia; [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-05](<../by_owner/sijin-lu.md#chat-05>) — Sijin Lu
- Source files recorded for this implementation: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Changed files recorded by the ledger: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Shared entry / interface boundary: Shared answer service through worker or offline runner / GenerationService
- Persisted effect / consumer: Attempts, prompt metadata and typed response/evidence snapshots / Chat renderer and evaluation scorer
- Local acceptance clause: Apply profile rules in main chat generation. Add compiled policy and per-turn style requests to the existing chat prompt with a frozen profile snapshot. No compulsory second child call. Failed new generation cannot erase previous successful turns; no-profile chat keeps history.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_generation_contracts.py](<../../../tests/unit/test_generation_contracts.py>), [tests/unit/test_generation_engine.py](<../../../tests/unit/test_generation_engine.py>), [tests/unit/test_mock_evidence_coverage.py](<../../../tests/unit/test_mock_evidence_coverage.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>)
- Recorded current check nodes: `["tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_generation_contracts::test_chat_message_never_requires_choices", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[gold_answer]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[history]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[summary]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[model]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[owner]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[options]", "tests.unit.test_generation_contracts::test_chat_preserves_complete_prose_and_all_required_fields", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[True]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[False]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[nan]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[inf]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[-0.1]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[1.1]", "tests.unit.test_generation_contracts::test_refusal_has_distinct_empty_and_null_invariants", "tests.unit.test_generation_contracts::test_social_and_clarification_have_no_compact_factual_answer[social]", "tests.unit.test_generation_contracts::test_social_and_clarification_have_no_compact_factual_answer[clarification]", "tests.unit.test_generation_contracts::test_mcq_requires_exact_four_labels_and_normalized_distinct_options", "tests.unit.test_generation_contracts::test_mcq_preserves_original_option_text_for_exact_output_comparison", "tests.unit.test_generation_contracts::test_legacy_mcq_refusal_enum_is_separate_from_chat", "tests.unit.test_generation_engine::test_strict_json_negatives[\`\`\`json\\n{}\\n\`\`\`]", "tests.unit.test_generation_engine::test_strict_json_negatives[{} {}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{} trailing]", "tests.unit.test_generation_engine::test_strict_json_negatives[[]]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":NaN}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":Infinity}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":1,\"x\":2}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"nested\":{\"x\":1,\"x\":2}}]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates0]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates1]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates2]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates3]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates4]", "tests.unit.test_generation_engine::test_actual_role_order_profile_off_and_frozen_benchmark_boundary", "tests.unit.test_generation_engine::test_mock_changes_with_current_evidence_and_history_sensitive_query", "tests.unit.test_generation_engine::test_shared_four_call_budget_covers_transient_and_one_format_repair", "tests.unit.test_generation_engine::test_invalid_twice_is_error_not_refusal_and_retry_retains_budget", "tests.unit.test_generation_engine::test_complete_json_with_length_finish_never_publishes_or_repairs", "tests.unit.test_generation_engine::test_context_budget_includes_profile_schema_and_output_and_drops_whole_chunks", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload0-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload1-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload2-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload3-EMPTY_RESPONSE]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload4-OUTPUT_TRUNCATED]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[429-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[500-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[503-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[401-False]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[403-False]", "tests.unit.test_generation_engine::test_http_adapter_sends_actual_roles_and_unknown_usage_remains_null", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[How do I configure Kubernetes ingress TLS certificates?]", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[Who won the 2026 Formula One world championship?]", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[What is the current exchange rate between the yen and the euro?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How does negative feedback maintain homeostasis?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What are the functions of erythrocytes, leukocytes and platelets?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How does glycolysis produce ATP from glucose?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How do natural selection and genetic drift differ?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What is the difference between a food chain and a food web?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What is the difference between prokaryotic and eukaryotic cells?]", "tests.unit.test_mock_evidence_coverage::test_actual_learning_objective_question_is_not_mistaken_for_an_answer", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Why does it need light?]", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Make it simpler]", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Give an example]", "tests.unit.test_mock_evidence_coverage::test_numbers_and_negation_are_required_content[Explain nuclear fusion in 2031]", "tests.unit.test_mock_evidence_coverage::test_numbers_and_negation_are_required_content[Explain nuclear fusion without heat]", "tests.unit.test_mock_evidence_coverage::test_terms_scattered_over_unrelated_paragraphs_do_not_qualify_an_excerpt", "tests.unit.test_mock_evidence_coverage::test_provider_scores_are_not_used_to_qualify_mock_evidence", "tests.unit.test_mock_evidence_coverage::test_standard_inflections_do_not_require_unrelated_keyword_exceptions", "tests.unit.test_mock_evidence_coverage::test_grounded_teaching_base_retains_energy_form_answer", "tests.unit.test_mock_evidence_coverage::test_source_exercise_question_does_not_become_an_asserted_answer", "tests.unit.test_mock_evidence_coverage::test_learner_correction_completes_an_ambiguous_turn_with_the_named_topic"]`
- Acceptance references: [AC-15](<../acceptance.md#ac-15>), [AC-29](<../acceptance.md#ac-29>), [AC-30](<../acceptance.md#ac-30>), [HC-09](<../acceptance.md#hc-09>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/mock-evidence-replay.md](<../../execution/mock-evidence-replay.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current strict chat/MCQ schemas, mode-specific prompts, no-gold boundary, simulated provider failures, finite shared retries/repair and deterministic response policies passed their executed tests. Actual-source mock replays retain unsupported/refused cases.
- Unresolved scope: No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.
- Blockers: None recorded.
- Mapping limitation: No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.

Handoff consumers: `["Pengyuan Xia", "Zeping Liao", "Baiqing Huang"]`

Handover actions: Apply compiled profile and per-turn presentation requests in the main chat generation call, without a mandatory second call. Keep C0/C1/C2 studies in evaluation and independent of stored chat messages.

Handover checks: `["HC-09"]`

Source asset state: The handover proposes a later teaching call after a base answer under the old scope.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Current strict chat/MCQ schemas, mode-specific prompts, no-gold boundary, simulated provider failures, finite shared retries/repair and deterministic response policies passed their executed tests. Actual-source mock replays retain unsupported/refused cases.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/mock-evidence-replay.md](<../../execution/mock-evidence-replay.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## PER-03

Implement all three chat presentation levels. Define term/prerequisite/detail/example policies without forced step counts. Supported meanings and sources remain consistent while wording changes. Test short answers, long explanations and user-requested simplification.

- Accountable owner (reporting): Pengyuan Xia
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G3
- Current status: `IMPLEMENTED_UNVERIFIED`
- Separate implementation / verification / research / human-review states: `IMPLEMENTED_UNVERIFIED` / `IMPLEMENTED_UNVERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["PER-02"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-02"}]`
- Upstream collaborators (derived from those dependencies): [PER-02](<../by_owner/pengyuan-xia.md#per-02>) — Pengyuan Xia
- Downstream collaborators (reverse dependency references): [GEN-09](<../by_owner/sijin-lu.md#gen-09>) — Sijin Lu; [PER-06](<../by_owner/pengyuan-xia.md#per-06>) — Pengyuan Xia; [PER-08](<../by_owner/pengyuan-xia.md#per-08>) — Pengyuan Xia
- Source files recorded for this implementation: [personalisation/compiler.py](<../../../personalisation/compiler.py>), [personalisation/study.py](<../../../personalisation/study.py>), [personalisation/rubric.py](<../../../personalisation/rubric.py>)
- Changed files recorded by the ledger: [personalisation/compiler.py](<../../../personalisation/compiler.py>), [personalisation/study.py](<../../../personalisation/study.py>), [personalisation/rubric.py](<../../../personalisation/rubric.py>)
- Shared entry / interface boundary: Profile API/UI and offline matched study runner / ProfileCompiler
- Persisted effect / consumer: Profile revisions, per-turn snapshots and separate study items / Main generation prompt and study reports
- Local acceptance clause: Implement all three chat presentation levels. Define term/prerequisite/detail/example policies without forced step counts. Supported meanings and sources remain consistent while wording changes. Test short answers, long explanations and user-requested simplification.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_profiles.py](<../../../tests/unit/test_profiles.py>), [tests/unit/test_evaluation_study.py](<../../../tests/unit/test_evaluation_study.py>)
- Recorded current check nodes: `["tests.unit.test_evaluation_study::test_shared_mock_study_freezes_nine_conditions_and_resumes_without_repeating", "tests.unit.test_evaluation_study::test_interrupted_study_call_is_not_silently_repeated", "tests.unit.test_evaluation_study::test_study_rejects_live_mode_and_mutated_frozen_inputs", "tests.unit.test_evaluation_study::test_study_prompt_or_rubric_environment_change_stops_remaining_calls", "tests.unit.test_profiles::test_profile_compiler_stable_distinct_and_explicit_invalid_values_fail", "tests.unit.test_profiles::test_temporary_override_does_not_mutate_saved_profile_and_off_keeps_no_profile_policy", "tests.unit.test_profiles::test_three_by_three_study_freezes_base_and_evidence_and_c0_hides_level", "tests.unit.test_profiles::test_missing_independent_ratings_are_not_zero_or_passed"]`
- Acceptance references: [AC-15](<../acceptance.md#ac-15>), [AC-29](<../acceptance.md#ac-29>), [AC-30](<../acceptance.md#ac-30>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/profile-lengths-20260908.md](<../../execution/profile-lengths-20260908.md>), [evidence/personalisation/profile-lengths-20260908T095207Z/results.json](<../../../evidence/personalisation/profile-lengths-20260908T095207Z/results.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: All three policies were exercised through 12 actual main-service turns: three source-establishing turns and nine short/long/simplification targets. Exact saved profile/policy/source/citation/history checks and one mock call per turn passed. Six target answers and three long-request refusals are retained; short and simplified excerpts were identical to their setup output.
- Unresolved scope: Requested long explanations did not produce long answers in this mock matrix. Actual differentiated wording, supported meaning and independent scientific review remain unverified; software checks do not close presentation quality.
- Blockers: None recorded.
- Mapping limitation: Requested long explanations did not produce long answers in this mock matrix. Actual differentiated wording, supported meaning and independent scientific review remain unverified; software checks do not close presentation quality.

Recorded component observations:

- observed task scope: `IMPLEMENTED_UNVERIFIED`. All three policies were exercised through 12 actual main-service turns: three source-establishing turns and nine short/long/simplification targets. Exact saved profile/policy/source/citation/history checks and one mock call per turn passed. Six target answers and three long-request refusals are retained; short and simplified excerpts were identical to their setup output.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/profile-lengths-20260908.md](<../../execution/profile-lengths-20260908.md>), [evidence/personalisation/profile-lengths-20260908T095207Z/results.json](<../../../evidence/personalisation/profile-lengths-20260908T095207Z/results.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Requested long explanations did not produce long answers in this mock matrix. Actual differentiated wording, supported meaning and independent scientific review remain unverified; software checks do not close presentation quality.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## PER-04

Implement missing-profile fallback and revision conflicts. Invalid explicit input fails; missing legacy internal data may use recorded Intermediate. Freeze applied policy at each turn; per-turn style requests do not silently update the saved profile.

- Accountable owner (reporting): Pengyuan Xia
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G3
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["PER-01", "BE-04"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-01"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-04"}]`
- Upstream collaborators (derived from those dependencies): [PER-01](<../by_owner/pengyuan-xia.md#per-01>) — Pengyuan Xia; [BE-04](<../by_owner/zeping-liao.md#be-04>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [PER-05](<../by_owner/pengyuan-xia.md#per-05>) — Pengyuan Xia; [FE-07](<../by_owner/baiqing-huang.md#fe-07>) — Baiqing Huang
- Source files recorded for this implementation: [personalisation/compiler.py](<../../../personalisation/compiler.py>), [personalisation/study.py](<../../../personalisation/study.py>), [personalisation/rubric.py](<../../../personalisation/rubric.py>)
- Changed files recorded by the ledger: [personalisation/compiler.py](<../../../personalisation/compiler.py>), [personalisation/study.py](<../../../personalisation/study.py>), [personalisation/rubric.py](<../../../personalisation/rubric.py>)
- Shared entry / interface boundary: Profile API/UI and offline matched study runner / ProfileCompiler
- Persisted effect / consumer: Profile revisions, per-turn snapshots and separate study items / Main generation prompt and study reports
- Local acceptance clause: Implement missing-profile fallback and revision conflicts. Invalid explicit input fails; missing legacy internal data may use recorded Intermediate. Freeze applied policy at each turn; per-turn style requests do not silently update the saved profile.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_profiles.py](<../../../tests/unit/test_profiles.py>), [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.unit.test_profiles::test_profile_compiler_stable_distinct_and_explicit_invalid_values_fail", "tests.unit.test_profiles::test_temporary_override_does_not_mutate_saved_profile_and_off_keeps_no_profile_policy", "tests.unit.test_profiles::test_three_by_three_study_freezes_base_and_evidence_and_c0_hides_level", "tests.unit.test_profiles::test_missing_independent_ratings_are_not_zero_or_passed"]`
- Acceptance references: [AC-15](<../acceptance.md#ac-15>), [AC-30](<../acceptance.md#ac-30>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Deterministic profile rules/hash, validation/fallback, optimistic versions and per-turn frozen snapshots passed current tests; actual UI/API follows profile-off without clearing session context.
- Unresolved scope: Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots.
- Blockers: None recorded.
- Mapping limitation: Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Deterministic profile rules/hash, validation/fallback, optimistic versions and per-turn frozen snapshots passed current tests; actual UI/API follows profile-off without clearing session context.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## PER-05

Connect profile editing to actual chat. Select/save/reset in the UI; verify next-turn model inputs contain the correct policy. Historical responses retain snapshots. Turning profile off keeps conversation context and does not route the user to an MCQ benchmark.

- Accountable owner (reporting): Pengyuan Xia
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["PER-04", "GEN-09", "FE-07"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-04"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-07"}]`
- Upstream collaborators (derived from those dependencies): [PER-04](<../by_owner/pengyuan-xia.md#per-04>) — Pengyuan Xia; [GEN-09](<../by_owner/sijin-lu.md#gen-09>) — Sijin Lu; [FE-07](<../by_owner/baiqing-huang.md#fe-07>) — Baiqing Huang
- Downstream collaborators (reverse dependency references): [PER-09](<../by_owner/pengyuan-xia.md#per-09>) — Pengyuan Xia; [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-07](<../by_owner/pengyuan-xia.md#chat-07>) — Pengyuan Xia
- Source files recorded for this implementation: [personalisation/compiler.py](<../../../personalisation/compiler.py>), [personalisation/study.py](<../../../personalisation/study.py>), [personalisation/rubric.py](<../../../personalisation/rubric.py>)
- Changed files recorded by the ledger: [personalisation/compiler.py](<../../../personalisation/compiler.py>), [personalisation/study.py](<../../../personalisation/study.py>), [personalisation/rubric.py](<../../../personalisation/rubric.py>)
- Shared entry / interface boundary: Profile API/UI and offline matched study runner / ProfileCompiler
- Persisted effect / consumer: Profile revisions, per-turn snapshots and separate study items / Main generation prompt and study reports
- Local acceptance clause: Connect profile editing to actual chat. Select/save/reset in the UI; verify next-turn model inputs contain the correct policy. Historical responses retain snapshots. Turning profile off keeps conversation context and does not route the user to an MCQ benchmark.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_profiles.py](<../../../tests/unit/test_profiles.py>), [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.unit.test_profiles::test_profile_compiler_stable_distinct_and_explicit_invalid_values_fail", "tests.unit.test_profiles::test_temporary_override_does_not_mutate_saved_profile_and_off_keeps_no_profile_policy", "tests.unit.test_profiles::test_three_by_three_study_freezes_base_and_evidence_and_c0_hides_level", "tests.unit.test_profiles::test_missing_independent_ratings_are_not_zero_or_passed"]`
- Acceptance references: [AC-15](<../acceptance.md#ac-15>), [AC-29](<../acceptance.md#ac-29>), [AC-30](<../acceptance.md#ac-30>), [AC-43](<../acceptance.md#ac-43>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Deterministic profile rules/hash, validation/fallback, optimistic versions and per-turn frozen snapshots passed current tests; actual UI/API follows profile-off without clearing session context.
- Unresolved scope: Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots.
- Blockers: None recorded.
- Mapping limitation: Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Deterministic profile rules/hash, validation/fallback, optimistic versions and per-turn frozen snapshots passed current tests; actual UI/API follows profile-off without clearing session context.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## BE-08

Build one typed answer service. Interactive chat: save message/context/profile → prepare query → retrieve/reuse evidence → generate prose → validate → persist. OpenQA/MCQ enter shared components through mode adapters. Core chat wiring must not import SciQ or require evaluator startup.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-05", "BE-07", "BE-09", "RET-04", "GEN-05", "CHAT-04"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-04"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-04"}]`
- Upstream collaborators (derived from those dependencies): [BE-05](<../by_owner/zeping-liao.md#be-05>) — Zeping Liao; [BE-07](<../by_owner/zeping-liao.md#be-07>) — Zeping Liao; [BE-09](<../by_owner/zeping-liao.md#be-09>) — Zeping Liao; [RET-04](<../by_owner/chengzhou-liu.md#ret-04>) — Chengzhou Liu; [GEN-05](<../by_owner/sijin-lu.md#gen-05>) — Sijin Lu; [CHAT-04](<../by_owner/chengzhou-liu.md#chat-04>) — Chengzhou Liu
- Downstream collaborators (reverse dependency references): [BE-10](<../by_owner/zeping-liao.md#be-10>) — Zeping Liao; [BE-11](<../by_owner/zeping-liao.md#be-11>) — Zeping Liao; [BE-12](<../by_owner/zeping-liao.md#be-12>) — Zeping Liao; [BE-13](<../by_owner/zeping-liao.md#be-13>) — Zeping Liao; [BE-14](<../by_owner/zeping-liao.md#be-14>) — Zeping Liao; [FE-04](<../by_owner/baiqing-huang.md#fe-04>) — Baiqing Huang; [FE-05](<../by_owner/baiqing-huang.md#fe-05>) — Baiqing Huang; [QA-13](<../by_owner/chong-zhang.md#qa-13>) — Chong Zhang; [CHAT-05](<../by_owner/sijin-lu.md#chat-05>) — Sijin Lu
- Source files recorded for this implementation: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Changed files recorded by the ledger: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Shared entry / interface boundary: Versioned API and operator CLI / Application services and worker
- Persisted effect / consumer: Relational entities and publication transactions / Typed frontend, admin CLI and evaluator
- Local acceptance clause: Build one typed answer service. Interactive chat: save message/context/profile → prepare query → retrieve/reuse evidence → generate prose → validate → persist. OpenQA/MCQ enter shared components through mode adapters. Core chat wiring must not import SciQ or require evaluator startup.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_chat_evidence_reuse.py](<../../../tests/integration/test_chat_evidence_reuse.py>)
- Recorded current check nodes: `["tests.integration.test_chat_evidence_reuse::test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic", "tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation"]`
- Acceptance references: [AC-08](<../acceptance.md#ac-08>), [AC-09](<../acceptance.md#ac-09>), [AC-12](<../acceptance.md#ac-12>), [AC-22](<../acceptance.md#ac-22>), [AC-24](<../acceptance.md#ac-24>), [AC-25](<../acceptance.md#ac-25>), [AC-37](<../acceptance.md#ac-37>), [HC-10](<../acceptance.md#hc-10>)
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

## BE-10

Complete the feedback loop. Persist one updateable helpfulness/comment record per owner/answer. Provide an admin review state and issue/note link via UI or CLI; feedback never silently trains models or changes profiles.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-08"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-08"}]`
- Upstream collaborators (derived from those dependencies): [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [BE-14](<../by_owner/zeping-liao.md#be-14>) — Zeping Liao; [FE-09](<../by_owner/baiqing-huang.md#fe-09>) — Baiqing Huang
- Source files recorded for this implementation: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Changed files recorded by the ledger: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Shared entry / interface boundary: Versioned API and operator CLI / Application services and worker
- Persisted effect / consumer: Relational entities and publication transactions / Typed frontend, admin CLI and evaluator
- Local acceptance clause: Complete the feedback loop. Persist one updateable helpfulness/comment record per owner/answer. Provide an admin review state and issue/note link via UI or CLI; feedback never silently trains models or changes profiles.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_account_feedback_contention.py](<../../../tests/integration/test_account_feedback_contention.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>), [tests/integration/test_operations.py](<../../../tests/integration/test_operations.py>), [tests/unit/test_error_log_safety.py](<../../../tests/unit/test_error_log_safety.py>)
- Recorded current check nodes: `["tests.integration.test_account_feedback_contention::test_concurrent_account_creation_returns_conflict_without_partial_profile", "tests.integration.test_account_feedback_contention::test_concurrent_first_feedback_save_reuses_one_record_and_keeps_review_editable", "tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.integration.test_operations::test_cleanup_dry_run_and_apply_preserve_referenced_bytes", "tests.integration.test_operations::test_cleanup_rejects_changed_file_and_root_escape", "tests.integration.test_operations::test_operator_cli_uses_real_database_and_secret_environment", "tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_error_log_safety::test_unexpected_database_error_omits_sql_parameters_and_exception_chain"]`
- Acceptance references: [AC-16](<../acceptance.md#ac-16>), [AC-32](<../acceptance.md#ac-32>)
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

## BE-12

Expose product and evaluation capabilities separately. Provide immutable configs and chat_ready/evaluation_ready with actual reasons. Chat health checks only its own DB/corpus/provider path; missing SciQ/scoring data cannot disable learner chat. Keep later experiment status accurate when added.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-06", "BE-08"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-08"}]`
- Upstream collaborators (derived from those dependencies): [BE-06](<../by_owner/zeping-liao.md#be-06>) — Zeping Liao; [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [BE-13](<../by_owner/zeping-liao.md#be-13>) — Zeping Liao; [BE-14](<../by_owner/zeping-liao.md#be-14>) — Zeping Liao; [FE-10](<../by_owner/baiqing-huang.md#fe-10>) — Baiqing Huang; [FE-11](<../by_owner/baiqing-huang.md#fe-11>) — Baiqing Huang
- Source files recorded for this implementation: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Changed files recorded by the ledger: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Shared entry / interface boundary: Versioned API and operator CLI / Application services and worker
- Persisted effect / consumer: Relational entities and publication transactions / Typed frontend, admin CLI and evaluator
- Local acceptance clause: Expose product and evaluation capabilities separately. Provide immutable configs and chat_ready/evaluation_ready with actual reasons. Chat health checks only its own DB/corpus/provider path; missing SciQ/scoring data cannot disable learner chat. Keep later experiment status accurate when added.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_account_feedback_contention.py](<../../../tests/integration/test_account_feedback_contention.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>), [tests/integration/test_operations.py](<../../../tests/integration/test_operations.py>), [tests/unit/test_error_log_safety.py](<../../../tests/unit/test_error_log_safety.py>)
- Recorded current check nodes: `["tests.integration.test_account_feedback_contention::test_concurrent_account_creation_returns_conflict_without_partial_profile", "tests.integration.test_account_feedback_contention::test_concurrent_first_feedback_save_reuses_one_record_and_keeps_review_editable", "tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.integration.test_operations::test_cleanup_dry_run_and_apply_preserve_referenced_bytes", "tests.integration.test_operations::test_cleanup_rejects_changed_file_and_root_escape", "tests.integration.test_operations::test_operator_cli_uses_real_database_and_secret_environment", "tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_error_log_safety::test_unexpected_database_error_omits_sql_parameters_and_exception_chain"]`
- Acceptance references: [AC-01](<../acceptance.md#ac-01>), [AC-19](<../acceptance.md#ac-19>), [AC-37](<../acceptance.md#ac-37>), [HC-11](<../acceptance.md#hc-11>)
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

## BE-13

Unify errors and basic limits. Implement consistent errors, trace IDs, redacted logs, bounded inputs and small configurable concurrency/time limits. Retain auth/input checks without adding distributed rate-limit or observability systems.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-08", "BE-12"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-12"}]`
- Upstream collaborators (derived from those dependencies): [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao; [BE-12](<../by_owner/zeping-liao.md#be-12>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [BE-15](<../by_owner/zeping-liao.md#be-15>) — Zeping Liao; [QA-11](<../by_owner/chong-zhang.md#qa-11>) — Chong Zhang
- Source files recorded for this implementation: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Changed files recorded by the ledger: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Shared entry / interface boundary: Versioned API and operator CLI / Application services and worker
- Persisted effect / consumer: Relational entities and publication transactions / Typed frontend, admin CLI and evaluator
- Local acceptance clause: Unify errors and basic limits. Implement consistent errors, trace IDs, redacted logs, bounded inputs and small configurable concurrency/time limits. Retain auth/input checks without adding distributed rate-limit or observability systems.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_account_feedback_contention.py](<../../../tests/integration/test_account_feedback_contention.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>), [tests/integration/test_operations.py](<../../../tests/integration/test_operations.py>), [tests/unit/test_error_log_safety.py](<../../../tests/unit/test_error_log_safety.py>)
- Recorded current check nodes: `["tests.integration.test_account_feedback_contention::test_concurrent_account_creation_returns_conflict_without_partial_profile", "tests.integration.test_account_feedback_contention::test_concurrent_first_feedback_save_reuses_one_record_and_keeps_review_editable", "tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.integration.test_operations::test_cleanup_dry_run_and_apply_preserve_referenced_bytes", "tests.integration.test_operations::test_cleanup_rejects_changed_file_and_root_escape", "tests.integration.test_operations::test_operator_cli_uses_real_database_and_secret_environment", "tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_error_log_safety::test_unexpected_database_error_omits_sql_parameters_and_exception_chain"]`
- Acceptance references: [AC-11](<../acceptance.md#ac-11>), [AC-14](<../acceptance.md#ac-14>), [AC-25](<../acceptance.md#ac-25>)
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

## BE-14

Synchronise all mode contracts and typed frontend clients. Export POST messages, typed chat/MCQ responses, context/profile references, job and revision states. Detect drift and update generated TypeScript with migration consumers; do not leave a hidden choices requirement in a shared client.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-08", "BE-10", "BE-12"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-10"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-12"}]`
- Upstream collaborators (derived from those dependencies): [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao; [BE-10](<../by_owner/zeping-liao.md#be-10>) — Zeping Liao; [BE-12](<../by_owner/zeping-liao.md#be-12>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [INT-07](<../by_owner/xianshu-zhang.md#int-07>) — Xianshu Zhang; [BE-15](<../by_owner/zeping-liao.md#be-15>) — Zeping Liao; [CHAT-11](<../by_owner/xianshu-zhang.md#chat-11>) — Xianshu Zhang
- Source files recorded for this implementation: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Changed files recorded by the ledger: [backend/app/modules](<../../../backend/app/modules>), [backend/app/worker.py](<../../../backend/app/worker.py>), [backend/app/core](<../../../backend/app/core>), [backend/alembic/versions](<../../../backend/alembic/versions>)
- Shared entry / interface boundary: Versioned API and operator CLI / Application services and worker
- Persisted effect / consumer: Relational entities and publication transactions / Typed frontend, admin CLI and evaluator
- Local acceptance clause: Synchronise all mode contracts and typed frontend clients. Export POST messages, typed chat/MCQ responses, context/profile references, job and revision states. Detect drift and update generated TypeScript with migration consumers; do not leave a hidden choices requirement in a shared client.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_legacy_mcq_migration.py](<../../../tests/integration/test_legacy_mcq_migration.py>)
- Recorded current check nodes: `["tests.integration.test_legacy_mcq_migration::test_initial_data_and_typed_mcq_survive_additive_migrations"]`
- Acceptance references: [AC-08](<../acceptance.md#ac-08>), [AC-10](<../acceptance.md#ac-10>), [AC-22](<../acceptance.md#ac-22>), [AC-36](<../acceptance.md#ac-36>), [AC-48](<../acceptance.md#ac-48>)
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

## FE-04

Connect real chat job states. Poll queued/preparing/retrieving/generating/saving and terminal results; stop, retry tail failures and recover on re-login. Preserve drafts/history and distinguish clarification/refusal from connection errors. No fake token streaming is required.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-03", "BE-08"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-03"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-08"}]`
- Upstream collaborators (derived from those dependencies): [FE-03](<../by_owner/baiqing-huang.md#fe-03>) — Baiqing Huang; [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-05](<../by_owner/baiqing-huang.md#fe-05>) — Baiqing Huang; [CHAT-08](<../by_owner/zeping-liao.md#chat-08>) — Zeping Liao
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Connect real chat job states. Poll queued/preparing/retrieving/generating/saving and terminal results; stop, retry tail failures and recover on re-login. Preserve drafts/history and distinguish clarification/refusal from connection errors. No fake token streaming is required.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-11](<../acceptance.md#ac-11>), [AC-12](<../acceptance.md#ac-12>), [AC-16](<../acceptance.md#ac-16>), [AC-24](<../acceptance.md#ac-24>), [AC-44](<../acceptance.md#ac-44>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
- Unresolved scope: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.
- Blockers: None recorded.
- Mapping limitation: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## FE-05

Render full conversational responses. Display user/assistant prose, citations, clarification, refusal and applied profile; safe Markdown, copy and mock/live labels. Render old MCQ records only through their explicit schema, not as the new chat response.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-04", "BE-08"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-04"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-08"}]`
- Upstream collaborators (derived from those dependencies): [FE-04](<../by_owner/baiqing-huang.md#fe-04>) — Baiqing Huang; [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-06](<../by_owner/baiqing-huang.md#fe-06>) — Baiqing Huang; [FE-08](<../by_owner/baiqing-huang.md#fe-08>) — Baiqing Huang; [FE-09](<../by_owner/baiqing-huang.md#fe-09>) — Baiqing Huang; [CHAT-06](<../by_owner/baiqing-huang.md#chat-06>) — Baiqing Huang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Render full conversational responses. Display user/assistant prose, citations, clarification, refusal and applied profile; safe Markdown, copy and mock/live labels. Render old MCQ records only through their explicit schema, not as the new chat response.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-08](<../acceptance.md#ac-08>), [AC-09](<../acceptance.md#ac-09>), [AC-10](<../acceptance.md#ac-10>), [AC-15](<../acceptance.md#ac-15>), [AC-44](<../acceptance.md#ac-44>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
- Unresolved scope: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.
- Blockers: None recorded.
- Mapping limitation: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## FE-06

Deliver the evidence viewer. Open original request snapshots with full source title, section and real page locators. Handle unavailable evidence and safe links/text; display content must match stored hashes.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-05", "BE-09"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-09"}]`
- Upstream collaborators (derived from those dependencies): [FE-05](<../by_owner/baiqing-huang.md#fe-05>) — Baiqing Huang; [BE-09](<../by_owner/zeping-liao.md#be-09>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-12](<../by_owner/baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-06](<../by_owner/baiqing-huang.md#chat-06>) — Baiqing Huang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Deliver the evidence viewer. Open original request snapshots with full source title, section and real page locators. Handle unavailable evidence and safe links/text; display content must match stored hashes.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-08](<../acceptance.md#ac-08>), [AC-14](<../acceptance.md#ac-14>), [AC-16](<../acceptance.md#ac-16>), [AC-41](<../acceptance.md#ac-41>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
- Unresolved scope: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.
- Blockers: None recorded.
- Mapping limitation: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## FE-07

Complete profile settings before chat acceptance. Provide three-level selection/save/reset and current versus applied snapshots. Test per-turn simplification separately from saved preferences; toggling profile off must not clear dialogue context.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-02", "BE-04", "PER-04"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-04"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-04"}]`
- Upstream collaborators (derived from those dependencies): [FE-02](<../by_owner/baiqing-huang.md#fe-02>) — Baiqing Huang; [BE-04](<../by_owner/zeping-liao.md#be-04>) — Zeping Liao; [PER-04](<../by_owner/pengyuan-xia.md#per-04>) — Pengyuan Xia
- Downstream collaborators (reverse dependency references): [PER-05](<../by_owner/pengyuan-xia.md#per-05>) — Pengyuan Xia; [FE-12](<../by_owner/baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Complete profile settings before chat acceptance. Provide three-level selection/save/reset and current versus applied snapshots. Test per-turn simplification separately from saved preferences; toggling profile off must not clear dialogue context.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-15](<../acceptance.md#ac-15>), [AC-29](<../acceptance.md#ac-29>), [AC-30](<../acceptance.md#ac-30>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
- Unresolved scope: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.
- Blockers: None recorded.
- Mapping limitation: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## FE-08

Complete the chat workspace and history. /chat is the learner landing page with session sidebar, new chat, ordered transcript and lifecycle controls. Correctly restore clarification/failed/successful turns, message revisions and citations after refresh or re-login.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-05", "BE-05"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-05"}]`
- Upstream collaborators (derived from those dependencies): [FE-05](<../by_owner/baiqing-huang.md#fe-05>) — Baiqing Huang; [BE-05](<../by_owner/zeping-liao.md#be-05>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-12](<../by_owner/baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-06](<../by_owner/baiqing-huang.md#chat-06>) — Baiqing Huang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Complete the chat workspace and history. /chat is the learner landing page with session sidebar, new chat, ordered transcript and lifecycle controls. Correctly restore clarification/failed/successful turns, message revisions and citations after refresh or re-login.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-16](<../acceptance.md#ac-16>), [AC-24](<../acceptance.md#ac-24>), [AC-43](<../acceptance.md#ac-43>), [AC-45](<../acceptance.md#ac-45>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
- Unresolved scope: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.
- Blockers: None recorded.
- Mapping limitation: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## FE-09

Complete feedback interaction. Provide helpfulness/comment create/update with saving, saved and error states. Preserve text on failure and expose its existing stored value; review handling is connected, not write-only.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-05", "BE-10"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-10"}]`
- Upstream collaborators (derived from those dependencies): [FE-05](<../by_owner/baiqing-huang.md#fe-05>) — Baiqing Huang; [BE-10](<../by_owner/zeping-liao.md#be-10>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-12](<../by_owner/baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Complete feedback interaction. Provide helpfulness/comment create/update with saving, saved and error states. Preserve text on failure and expose its existing stored value; review handling is connected, not write-only.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-16](<../acceptance.md#ac-16>), [AC-32](<../acceptance.md#ac-32>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
- Unresolved scope: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.
- Blockers: None recorded.
- Mapping limitation: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## FE-10

Complete administrator corpus pages. Connect upload, inspect versions/quality, process/reprocess, review, deactivate/restore and release activation/rollback. Show failures and missing prerequisites accurately; no dead controls.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-02", "BE-06", "BE-12"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-12"}]`
- Upstream collaborators (derived from those dependencies): [FE-02](<../by_owner/baiqing-huang.md#fe-02>) — Baiqing Huang; [BE-06](<../by_owner/zeping-liao.md#be-06>) — Zeping Liao; [BE-12](<../by_owner/zeping-liao.md#be-12>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-12](<../by_owner/baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Complete administrator corpus pages. Connect upload, inspect versions/quality, process/reprocess, review, deactivate/restore and release activation/rollback. Show failures and missing prerequisites accurately; no dead controls.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_corpus_runtime.py](<../../../tests/integration/test_corpus_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_corpus_runtime::test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "tests.integration.test_corpus_runtime::test_quarantine_inspectable_exclusion_and_processing_lineage", "tests.integration.test_corpus_runtime::test_reprocessing_creates_new_chunks_while_old_evidence_survives", "tests.integration.test_corpus_runtime::test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "tests.integration.test_corpus_runtime::test_processing_diff_reports_split_groups_by_overlapping_source_spans", "tests.integration.test_corpus_runtime::test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "tests.integration.test_corpus_runtime::test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "tests.integration.test_corpus_runtime::test_source_deactivation_filters_current_retrieval_and_restore_recovers", "tests.integration.test_corpus_runtime::test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks", "tests.integration.test_corpus_runtime::test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "tests.integration.test_corpus_runtime::test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest", "tests.integration.test_corpus_runtime::test_legacy_release_without_saved_hashes_requires_explicit_new_build", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[cancel]", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[recover]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[cancel]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[recover]"]`
- Acceptance references: [AC-04](<../acceptance.md#ac-04>), [AC-14](<../acceptance.md#ac-14>), [AC-26](<../acceptance.md#ac-26>), [AC-28](<../acceptance.md#ac-28>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/openstax/corpus-report.json](<../../../evidence/openstax/corpus-report.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Document/reprocessing/source-visibility and immutable release lifecycle are exercised in current PostgreSQL tests. Official-source administrator browser version switching has separate completed evidence in the frontend audit.
- Unresolved scope: Check each browser attempt and its terminal pointer evidence; earlier interrupted attempts are preserved.
- Blockers: None recorded.
- Mapping limitation: Check each browser attempt and its terminal pointer evidence; earlier interrupted attempts are preserved.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Document/reprocessing/source-visibility and immutable release lifecycle are exercised in current PostgreSQL tests. Official-source administrator browser version switching has separate completed evidence in the frontend audit.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/openstax/corpus-report.json](<../../../evidence/openstax/corpus-report.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Check each browser attempt and its terminal pointer evidence; earlier interrupted attempts are preserved.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-02

Implement deterministic evaluator input adapters. Export stem-only OpenQACommand and independently seeded A–D MCQCommand; preserve source question IDs and exact reference mapping. Validate actual splits/counts; no task in core chat depends on these dataset adapters.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G2
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["DAT-09"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "DAT-09"}]`
- Upstream collaborators (derived from those dependencies): [DAT-09](<../by_owner/hongle-yang.md#dat-09>) — Hongle Yang
- Downstream collaborators (reverse dependency references): [BE-11](<../by_owner/zeping-liao.md#be-11>) — Zeping Liao; [QA-03](<../by_owner/chong-zhang.md#qa-03>) — Chong Zhang; [QA-04](<../by_owner/chong-zhang.md#qa-04>) — Chong Zhang; [QA-05](<../by_owner/chong-zhang.md#qa-05>) — Chong Zhang; [CHAT-09](<../by_owner/chong-zhang.md#chat-09>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Implement deterministic evaluator input adapters. Export stem-only OpenQACommand and independently seeded A–D MCQCommand; preserve source question IDs and exact reference mapping. Validate actual splits/counts; no task in core chat depends on these dataset adapters.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_sciq_acquisition.py](<../../../tests/unit/test_sciq_acquisition.py>), [tests/unit/test_evaluation_backend.py](<../../../tests/unit/test_evaluation_backend.py>)
- Recorded current check nodes: `["tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_openqa]", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_mcq]", "tests.unit.test_evaluation_backend::test_registered_hash_rejects_post_freeze_question_or_gold_injection", "tests.unit.test_evaluation_backend::test_server_cancellation_retains_all_scheduled_items", "tests.unit.test_evaluation_backend::test_admin_api_create_freeze_start_results_and_role_denial", "tests.unit.test_sciq_acquisition::test_lossless_parquet_unicode_and_all_item_public_preflight_boundary", "tests.unit.test_sciq_acquisition::test_official_byte_hash_mismatch_stops_before_raw_publication"]`
- Acceptance references: [AC-17](<../acceptance.md#ac-17>), [AC-23](<../acceptance.md#ac-23>), [AC-46](<../acceptance.md#ac-46>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/sciq/acquisition.json](<../../../evidence/sciq/acquisition.json>), [docs/sciq_acquisition.md](<../../sciq_acquisition.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Official pinned SciQ acquisition records all 13,679 rows and split/file hashes. Actual stem-only export and separate deterministic MCQ preflight ran. All 48 duplicate-option anomalies remain recorded; strict whole-split MCQ rejection is preserved.
- Unresolved scope: Formal answer-model runs remain separate; a prefix technical rehearsal is not a full dataset result.
- Blockers: None recorded.
- Mapping limitation: Formal answer-model runs remain separate; a prefix technical rehearsal is not a full dataset result.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Official pinned SciQ acquisition records all 13,679 rows and split/file hashes. Actual stem-only export and separate deterministic MCQ preflight ran. All 48 duplicate-option anomalies remain recorded; strict whole-split MCQ rejection is preserved.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/sciq/acquisition.json](<../../../evidence/sciq/acquisition.json>), [docs/sciq_acquisition.md](<../../sciq_acquisition.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Formal answer-model runs remain separate; a prefix technical rehearsal is not a full dataset result.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-03

Verify no evaluation-label leakage. Inspect all mode DTOs, prompt construction, retrieval and runtime mounts. OpenQA excludes distractors as well as correct answers/support; MCQ exposes candidate text but not its label. Interactive history is legitimate context, not a field to erase globally.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G3
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["QA-02", "GEN-01"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-01"}]`
- Upstream collaborators (derived from those dependencies): [QA-02](<../by_owner/chong-zhang.md#qa-02>) — Chong Zhang; [GEN-01](<../by_owner/sijin-lu.md#gen-01>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [GEN-08](<../by_owner/sijin-lu.md#gen-08>) — Sijin Lu; [QA-07](<../by_owner/chong-zhang.md#qa-07>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Verify no evaluation-label leakage. Inspect all mode DTOs, prompt construction, retrieval and runtime mounts. OpenQA excludes distractors as well as correct answers/support; MCQ exposes candidate text but not its label. Interactive history is legitimate context, not a field to erase globally.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_evaluation_metrics.py](<../../../tests/unit/test_evaluation_metrics.py>), [tests/unit/test_evaluation_runner.py](<../../../tests/unit/test_evaluation_runner.py>), [tests/unit/test_evaluation_backend.py](<../../../tests/unit/test_evaluation_backend.py>), [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: `["tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_teaching_api_nine_matched_jobs_and_blind_export_without_chat_mutation", "tests.integration.test_evaluation_postgres::test_postgres_teaching_cancel_keeps_success_and_all_scheduled_outcomes", "tests.integration.test_evaluation_postgres::test_postgres_teaching_late_source_revocation_discards_publication", "tests.integration.test_evaluation_postgres::test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result", "tests.integration.test_evaluation_postgres::test_postgres_all_twelve_authored_scenario_families_use_real_chat_api", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_openqa]", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_mcq]", "tests.unit.test_evaluation_backend::test_registered_hash_rejects_post_freeze_question_or_gold_injection", "tests.unit.test_evaluation_backend::test_server_cancellation_retains_all_scheduled_items", "tests.unit.test_evaluation_backend::test_admin_api_create_freeze_start_results_and_role_denial", "tests.unit.test_evaluation_metrics::test_conservative_em[ Oxygen  -oxygen-1]", "tests.unit.test_evaluation_metrics::test_conservative_em[\\uff2f\\uff38\\uff39\\uff27\\uff25\\uff2e-oxygen-1]", "tests.unit.test_evaluation_metrics::test_conservative_em[not oxygen-oxygen-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[-2 m-2 m-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[2 mg-2 g-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[--0]", "tests.unit.test_evaluation_metrics::test_conservative_em[None-oxygen-0]", "tests.unit.test_evaluation_metrics::test_multiset_f1_preserves_negation_signs_units_and_repetition", "tests.unit.test_evaluation_metrics::test_full_explanation_is_never_used_as_compact_answer", "tests.unit.test_evaluation_metrics::test_failed_cancelled_and_refused_rows_keep_scheduled_denominator", "tests.unit.test_evaluation_metrics::test_mcq_requires_selected_option_text_not_only_label", "tests.unit.test_evaluation_metrics::test_retrieval_uses_actual_returned_denominator_and_graded_ndcg", "tests.unit.test_evaluation_metrics::test_unavailable_qrels_and_zero_idcg_are_not_fabricated_zeros", "tests.unit.test_evaluation_metrics::test_citations_check_actual_text_hash_and_have_applicable_denominator", "tests.unit.test_evaluation_metrics::test_exact_binary_discordants_and_continuous_paired_intervals", "tests.unit.test_evaluation_metrics::test_turns_cluster_by_scenario_without_invalid_per_turn_mcnemar", "tests.unit.test_evaluation_runner::test_stem_projection_unchanged_when_private_labels_change", "tests.unit.test_evaluation_runner::test_mcq_shuffle_is_stable_symmetric_and_gold_stays_private", "tests.unit.test_evaluation_runner::test_duplicate_candidates_and_split_counts", "tests.unit.test_evaluation_runner::test_duplicate_source_choices_do_not_block_stem_only_openqa_freeze", "tests.unit.test_evaluation_runner::test_freeze_preregisters_and_resume_does_not_repeat_calls", "tests.unit.test_evaluation_runner::test_interrupted_submission_reconciles_receipt_without_new_call", "tests.unit.test_evaluation_runner::test_ambiguous_unrecorded_submission_never_automatically_repeats", "tests.unit.test_evaluation_runner::test_environment_change_stops_new_calls_preserves_scheduled_set", "tests.unit.test_evaluation_runner::test_tampered_manifest_or_private_reference_rejected", "tests.unit.test_evaluation_runner::test_cancelled_export_retains_denominator_and_has_no_private_reference", "tests.unit.test_evaluation_runner::test_live_defaults_and_e1_redefinition_are_rejected", "tests.unit.test_evaluation_runner::test_repeat_export_preserves_existing_independent_review", "tests.unit.test_evaluation_runner::test_malformed_shared_response_is_retained_as_invalid"]`
- Acceptance references: [AC-07](<../acceptance.md#ac-07>), [AC-17](<../acceptance.md#ac-17>), [AC-23](<../acceptance.md#ac-23>), [AC-36](<../acceptance.md#ac-36>), [AC-46](<../acceptance.md#ac-46>), [HC-03](<../acceptance.md#hc-03>)
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

## QA-05

Implement mode-aware metrics. Test conservative normalised EM, multiset token F1, MCQ selection accuracy, dialogue/grounding review aggregation and existing retrieval statistics against hand fixtures. Keep proxies, semantic ratings and denominator scopes distinct.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G3
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["QA-02", "INT-03"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-03"}]`
- Upstream collaborators (derived from those dependencies): [QA-02](<../by_owner/chong-zhang.md#qa-02>) — Chong Zhang; [INT-03](<../by_owner/xianshu-zhang.md#int-03>) — Xianshu Zhang
- Downstream collaborators (reverse dependency references): [QA-06](<../by_owner/chong-zhang.md#qa-06>) — Chong Zhang; [CHAT-09](<../by_owner/chong-zhang.md#chat-09>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Implement mode-aware metrics. Test conservative normalised EM, multiset token F1, MCQ selection accuracy, dialogue/grounding review aggregation and existing retrieval statistics against hand fixtures. Keep proxies, semantic ratings and denominator scopes distinct.
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

## CHAT-03

Implement conversation/summary.py and the combined token budget. Persist extractive summaries with covered-until/message IDs, deterministic hashes and no overlap with recent history. Test long sessions, invalidation, fallback and missing-referent clarification without a mandatory extra model call.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G3
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["CHAT-02", "BE-09"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-09"}]`
- Upstream collaborators (derived from those dependencies): [CHAT-02](<../by_owner/zeping-liao.md#chat-02>) — Zeping Liao; [BE-09](<../by_owner/zeping-liao.md#be-09>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [CHAT-04](<../by_owner/chengzhou-liu.md#chat-04>) — Chengzhou Liu
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Implement conversation/summary.py and the combined token budget. Persist extractive summaries with covered-until/message IDs, deterministic hashes and no overlap with recent history. Test long sessions, invalidation, fallback and missing-referent clarification without a mandatory extra model call.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_conversation.py](<../../../tests/unit/test_conversation.py>), [tests/integration/test_chat_evidence_reuse.py](<../../../tests/integration/test_chat_evidence_reuse.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>)
- Recorded current check nodes: `["tests.integration.test_chat_evidence_reuse::test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic", "tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_conversation::test_context_ownership_cutoff_revisions_and_completed_pairs", "tests.unit.test_conversation::test_long_history_summary_is_attributable_and_nonoverlapping", "tests.unit.test_conversation::test_summary_revision_or_content_change_invalidates", "tests.unit.test_conversation::test_summary_failure_keeps_bounded_recent_history_and_records_lost_prefix", "tests.unit.test_conversation::test_query_has_actual_referent_and_no_guessed_answer", "tests.unit.test_conversation::test_new_topic_comparison_correction_and_explicit_example", "tests.unit.test_conversation::test_local_clause_subject_is_not_replaced_with_an_old_session_topic"]`
- Acceptance references: [AC-25](<../acceptance.md#ac-25>), [AC-42](<../acceptance.md#ac-42>), [AC-43](<../acceptance.md#ac-43>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current deterministic conversation tests verify bounded owned history, immutable snapshots, versioned extractive summaries, local referents, topic correction and reuse eligibility; real official-corpus requests retain the actual prepared queries.
- Unresolved scope: Broad real-answer semantic correctness is not established by deterministic query fixtures.
- Blockers: None recorded.
- Mapping limitation: Broad real-answer semantic correctness is not established by deterministic query fixtures.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Current deterministic conversation tests verify bounded owned history, immutable snapshots, versioned extractive summaries, local referents, topic correction and reuse eligibility; real official-corpus requests retain the actual prepared queries.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Broad real-answer semantic correctness is not established by deterministic query fixtures.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## CHAT-04

Implement conversation/query.py and typed preparation outputs. Resolve dependent references into standalone retrieval queries, detect obvious topic changes and ask when ambiguous. Save original/prepared text and referenced IDs; benchmark stems bypass rewriting. Test meaning, not only keyword presence.

- Accountable owner (reporting): Chengzhou Liu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G3
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["CHAT-03", "GEN-02"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-03"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-02"}]`
- Upstream collaborators (derived from those dependencies): [CHAT-03](<../by_owner/zeping-liao.md#chat-03>) — Zeping Liao; [GEN-02](<../by_owner/sijin-lu.md#gen-02>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Implement conversation/query.py and typed preparation outputs. Resolve dependent references into standalone retrieval queries, detect obvious topic changes and ask when ambiguous. Save original/prepared text and referenced IDs; benchmark stems bypass rewriting. Test meaning, not only keyword presence.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_conversation.py](<../../../tests/unit/test_conversation.py>), [tests/integration/test_chat_evidence_reuse.py](<../../../tests/integration/test_chat_evidence_reuse.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>)
- Recorded current check nodes: `["tests.integration.test_chat_evidence_reuse::test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic", "tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_conversation::test_context_ownership_cutoff_revisions_and_completed_pairs", "tests.unit.test_conversation::test_long_history_summary_is_attributable_and_nonoverlapping", "tests.unit.test_conversation::test_summary_revision_or_content_change_invalidates", "tests.unit.test_conversation::test_summary_failure_keeps_bounded_recent_history_and_records_lost_prefix", "tests.unit.test_conversation::test_query_has_actual_referent_and_no_guessed_answer", "tests.unit.test_conversation::test_new_topic_comparison_correction_and_explicit_example", "tests.unit.test_conversation::test_local_clause_subject_is_not_replaced_with_an_old_session_topic"]`
- Acceptance references: [AC-38](<../acceptance.md#ac-38>), [AC-39](<../acceptance.md#ac-39>), [AC-40](<../acceptance.md#ac-40>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current deterministic conversation tests verify bounded owned history, immutable snapshots, versioned extractive summaries, local referents, topic correction and reuse eligibility; real official-corpus requests retain the actual prepared queries.
- Unresolved scope: Broad real-answer semantic correctness is not established by deterministic query fixtures.
- Blockers: None recorded.
- Mapping limitation: Broad real-answer semantic correctness is not established by deterministic query fixtures.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Current deterministic conversation tests verify bounded owned history, immutable snapshots, versioned extractive summaries, local referents, topic correction and reuse eligibility; real official-corpus requests retain the actual prepared queries.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Broad real-answer semantic correctness is not established by deterministic query fixtures.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## CHAT-05

Wire free-form mode through preparation, evidence, profile, ChatResponseV1 validation and persistence. Test answers, clarifications, social responses and refusals with distinct schemas/states. A plain user string reaches the actual provider adapter without fake A–D options; no second parallel answer engine.

- Accountable owner (reporting): Sijin Lu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["BE-08", "GEN-09", "RET-05"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-05"}]`
- Upstream collaborators (derived from those dependencies): [BE-08](<../by_owner/zeping-liao.md#be-08>) — Zeping Liao; [GEN-09](<../by_owner/sijin-lu.md#gen-09>) — Sijin Lu; [RET-05](<../by_owner/chengzhou-liu.md#ret-05>) — Chengzhou Liu
- Downstream collaborators (reverse dependency references): [CHAT-06](<../by_owner/baiqing-huang.md#chat-06>) — Baiqing Huang; [CHAT-08](<../by_owner/zeping-liao.md#chat-08>) — Zeping Liao; [CHAT-09](<../by_owner/chong-zhang.md#chat-09>) — Chong Zhang
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Wire free-form mode through preparation, evidence, profile, ChatResponseV1 validation and persistence. Test answers, clarifications, social responses and refusals with distinct schemas/states. A plain user string reaches the actual provider adapter without fake A–D options; no second parallel answer engine.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_chat_evidence_reuse.py](<../../../tests/integration/test_chat_evidence_reuse.py>)
- Recorded current check nodes: `["tests.integration.test_chat_evidence_reuse::test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic", "tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation"]`
- Acceptance references: [AC-08](<../acceptance.md#ac-08>), [AC-09](<../acceptance.md#ac-09>), [AC-22](<../acceptance.md#ac-22>), [AC-36](<../acceptance.md#ac-36>), [HC-09](<../acceptance.md#hc-09>)
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

## CHAT-06

Deliver /chat as the default workspace with transcript, composer, citations and contextual follow-ups. Wire copy, suggestions, stop/retry and re-login continuity to real endpoints. Demonstrate a multi-turn authored conversation with evaluator services absent, not merely a chat-shaped MCQ form.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-05", "FE-06", "FE-08", "CHAT-05"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-05"}]`
- Upstream collaborators (derived from those dependencies): [FE-05](<../by_owner/baiqing-huang.md#fe-05>) — Baiqing Huang; [FE-06](<../by_owner/baiqing-huang.md#fe-06>) — Baiqing Huang; [FE-08](<../by_owner/baiqing-huang.md#fe-08>) — Baiqing Huang; [CHAT-05](<../by_owner/sijin-lu.md#chat-05>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [INT-06](<../by_owner/xianshu-zhang.md#int-06>) — Xianshu Zhang; [CHAT-07](<../by_owner/pengyuan-xia.md#chat-07>) — Pengyuan Xia; [CHAT-10](<../by_owner/chong-zhang.md#chat-10>) — Chong Zhang
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Deliver /chat as the default workspace with transcript, composer, citations and contextual follow-ups. Wire copy, suggestions, stop/retry and re-login continuity to real endpoints. Demonstrate a multi-turn authored conversation with evaluator services absent, not merely a chat-shaped MCQ form.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_conversation.py](<../../../tests/unit/test_conversation.py>), [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-37](<../acceptance.md#ac-37>), [AC-38](<../acceptance.md#ac-38>), [AC-39](<../acceptance.md#ac-39>), [AC-44](<../acceptance.md#ac-44>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
- Unresolved scope: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.
- Blockers: None recorded.
- Mapping limitation: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## CHAT-07

Verify per-turn personalised dialogue through the actual UI/model input. Save a level, ask a question, request simpler wording, switch profile off and continue a reference-dependent follow-up. Applied snapshots and temporary overrides are correct; history remains active throughout.

- Accountable owner (reporting): Pengyuan Xia
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["PER-05", "CHAT-06"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "PER-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-06"}]`
- Upstream collaborators (derived from those dependencies): [PER-05](<../by_owner/pengyuan-xia.md#per-05>) — Pengyuan Xia; [CHAT-06](<../by_owner/baiqing-huang.md#chat-06>) — Baiqing Huang
- Downstream collaborators (reverse dependency references): [INT-07](<../by_owner/xianshu-zhang.md#int-07>) — Xianshu Zhang; [CHAT-10](<../by_owner/chong-zhang.md#chat-10>) — Chong Zhang
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Verify per-turn personalised dialogue through the actual UI/model input. Save a level, ask a question, request simpler wording, switch profile off and continue a reference-dependent follow-up. Applied snapshots and temporary overrides are correct; history remains active throughout.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_profiles.py](<../../../tests/unit/test_profiles.py>), [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.unit.test_profiles::test_profile_compiler_stable_distinct_and_explicit_invalid_values_fail", "tests.unit.test_profiles::test_temporary_override_does_not_mutate_saved_profile_and_off_keeps_no_profile_policy", "tests.unit.test_profiles::test_three_by_three_study_freezes_base_and_evidence_and_c0_hides_level", "tests.unit.test_profiles::test_missing_independent_ratings_are_not_zero_or_passed"]`
- Acceptance references: [AC-15](<../acceptance.md#ac-15>), [AC-29](<../acceptance.md#ac-29>), [AC-30](<../acceptance.md#ac-30>), [AC-43](<../acceptance.md#ac-43>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Deterministic profile rules/hash, validation/fallback, optimistic versions and per-turn frozen snapshots passed current tests; actual UI/API follows profile-off without clearing session context.
- Unresolved scope: Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots.
- Blockers: None recorded.
- Mapping limitation: Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Deterministic profile rules/hash, validation/fallback, optimistic versions and per-turn frozen snapshots passed current tests; actual UI/API follows profile-off without clearing session context.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Model presentation/teaching quality is unverified beyond mock policy and actual input snapshots.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## CHAT-08

Implement latest-answer regeneration and revision UI hooks. Create a new request/revision for the original user turn, keep prior text active until success, preserve its feedback and reject stale/non-tail regeneration. Failure/retry must not duplicate user messages or overwrite historical evidence.

- Accountable owner (reporting): Zeping Liao
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["CHAT-05", "FE-04", "CHAT-02"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-04"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-02"}]`
- Upstream collaborators (derived from those dependencies): [CHAT-05](<../by_owner/sijin-lu.md#chat-05>) — Sijin Lu; [FE-04](<../by_owner/baiqing-huang.md#fe-04>) — Baiqing Huang; [CHAT-02](<../by_owner/zeping-liao.md#chat-02>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [INT-07](<../by_owner/xianshu-zhang.md#int-07>) — Xianshu Zhang; [CHAT-10](<../by_owner/chong-zhang.md#chat-10>) — Chong Zhang
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Implement latest-answer regeneration and revision UI hooks. Create a new request/revision for the original user turn, keep prior text active until success, preserve its feedback and reject stale/non-tail regeneration. Failure/retry must not duplicate user messages or overwrite historical evidence.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>), [tests/integration/test_chat_runtime.py](<../../../tests/integration/test_chat_runtime.py>), [tests/integration/test_corpus_runtime.py](<../../../tests/integration/test_corpus_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_chat_runtime::test_atomic_chat_context_and_current_evidence", "tests.integration.test_chat_runtime::test_idempotency_busy_and_forbidden_fields", "tests.integration.test_chat_runtime::test_profile_snapshot_conflict_and_profile_off_preserves_history", "tests.integration.test_chat_runtime::test_cancel_retry_and_stale_publication", "tests.integration.test_chat_runtime::test_latest_revision_preserves_feedback_and_failed_replacement", "tests.integration.test_chat_runtime::test_ownership_archive_and_new_session_isolation", "tests.integration.test_corpus_runtime::test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "tests.integration.test_corpus_runtime::test_quarantine_inspectable_exclusion_and_processing_lineage", "tests.integration.test_corpus_runtime::test_reprocessing_creates_new_chunks_while_old_evidence_survives", "tests.integration.test_corpus_runtime::test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "tests.integration.test_corpus_runtime::test_processing_diff_reports_split_groups_by_overlapping_source_spans", "tests.integration.test_corpus_runtime::test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "tests.integration.test_corpus_runtime::test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "tests.integration.test_corpus_runtime::test_source_deactivation_filters_current_retrieval_and_restore_recovers", "tests.integration.test_corpus_runtime::test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks", "tests.integration.test_corpus_runtime::test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "tests.integration.test_corpus_runtime::test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest", "tests.integration.test_corpus_runtime::test_legacy_release_without_saved_hashes_requires_explicit_new_build", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[cancel]", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[recover]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[cancel]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[recover]", "tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked"]`
- Acceptance references: [AC-12](<../acceptance.md#ac-12>), [AC-24](<../acceptance.md#ac-24>), [AC-45](<../acceptance.md#ac-45>)
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

## CHAT-10

Author at least 12 scenario families in evaluation/conversations/ and browser tests. Cover follow-up, rephrase/example/comparison, ambiguity, correction, topic change, long history, new chat and profile continuity. Separate deterministic integration assertions from actual live semantic review.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 7, "suggested_project_week": 5, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G4
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["CHAT-06", "CHAT-07", "CHAT-08", "QA-01"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "CHAT-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-01"}]`
- Upstream collaborators (derived from those dependencies): [CHAT-06](<../by_owner/baiqing-huang.md#chat-06>) — Baiqing Huang; [CHAT-07](<../by_owner/pengyuan-xia.md#chat-07>) — Pengyuan Xia; [CHAT-08](<../by_owner/zeping-liao.md#chat-08>) — Zeping Liao; [QA-01](<../by_owner/chong-zhang.md#qa-01>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-11](<../by_owner/xianshu-zhang.md#chat-11>) — Xianshu Zhang
- Source files recorded for this implementation: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Changed files recorded by the ledger: [conversation](<../../../conversation>), [backend/app/modules/answering/service.py](<../../../backend/app/modules/answering/service.py>), [frontend/src/Chat.tsx](<../../../frontend/src/Chat.tsx>)
- Shared entry / interface boundary: Chat routes, shared answering and conversation tests / Conversation services
- Persisted effect / consumer: Messages, active revisions, context/summary/profile/evidence snapshots / Real multi-turn chat and independent OpenQA protocol
- Local acceptance clause: Author at least 12 scenario families in evaluation/conversations/ and browser tests. Cover follow-up, rephrase/example/comparison, ambiguity, correction, topic change, long history, new chat and profile continuity. Separate deterministic integration assertions from actual live semantic review.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_evaluation_metrics.py](<../../../tests/unit/test_evaluation_metrics.py>), [tests/unit/test_evaluation_runner.py](<../../../tests/unit/test_evaluation_runner.py>), [tests/unit/test_evaluation_backend.py](<../../../tests/unit/test_evaluation_backend.py>), [tests/integration/test_evaluation_postgres.py](<../../../tests/integration/test_evaluation_postgres.py>)
- Recorded current check nodes: `["tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_openqa]", "tests.integration.test_evaluation_postgres::test_postgres_e0_both_schemas_never_call_retriever[sciq_mcq]", "tests.integration.test_evaluation_postgres::test_postgres_teaching_api_nine_matched_jobs_and_blind_export_without_chat_mutation", "tests.integration.test_evaluation_postgres::test_postgres_teaching_cancel_keeps_success_and_all_scheduled_outcomes", "tests.integration.test_evaluation_postgres::test_postgres_teaching_late_source_revocation_discards_publication", "tests.integration.test_evaluation_postgres::test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result", "tests.integration.test_evaluation_postgres::test_postgres_all_twelve_authored_scenario_families_use_real_chat_api", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_openqa]", "tests.unit.test_evaluation_backend::test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold[sciq_mcq]", "tests.unit.test_evaluation_backend::test_registered_hash_rejects_post_freeze_question_or_gold_injection", "tests.unit.test_evaluation_backend::test_server_cancellation_retains_all_scheduled_items", "tests.unit.test_evaluation_backend::test_admin_api_create_freeze_start_results_and_role_denial", "tests.unit.test_evaluation_metrics::test_conservative_em[ Oxygen  -oxygen-1]", "tests.unit.test_evaluation_metrics::test_conservative_em[\\uff2f\\uff38\\uff39\\uff27\\uff25\\uff2e-oxygen-1]", "tests.unit.test_evaluation_metrics::test_conservative_em[not oxygen-oxygen-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[-2 m-2 m-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[2 mg-2 g-0]", "tests.unit.test_evaluation_metrics::test_conservative_em[--0]", "tests.unit.test_evaluation_metrics::test_conservative_em[None-oxygen-0]", "tests.unit.test_evaluation_metrics::test_multiset_f1_preserves_negation_signs_units_and_repetition", "tests.unit.test_evaluation_metrics::test_full_explanation_is_never_used_as_compact_answer", "tests.unit.test_evaluation_metrics::test_failed_cancelled_and_refused_rows_keep_scheduled_denominator", "tests.unit.test_evaluation_metrics::test_mcq_requires_selected_option_text_not_only_label", "tests.unit.test_evaluation_metrics::test_retrieval_uses_actual_returned_denominator_and_graded_ndcg", "tests.unit.test_evaluation_metrics::test_unavailable_qrels_and_zero_idcg_are_not_fabricated_zeros", "tests.unit.test_evaluation_metrics::test_citations_check_actual_text_hash_and_have_applicable_denominator", "tests.unit.test_evaluation_metrics::test_exact_binary_discordants_and_continuous_paired_intervals", "tests.unit.test_evaluation_metrics::test_turns_cluster_by_scenario_without_invalid_per_turn_mcnemar", "tests.unit.test_evaluation_runner::test_stem_projection_unchanged_when_private_labels_change", "tests.unit.test_evaluation_runner::test_mcq_shuffle_is_stable_symmetric_and_gold_stays_private", "tests.unit.test_evaluation_runner::test_duplicate_candidates_and_split_counts", "tests.unit.test_evaluation_runner::test_duplicate_source_choices_do_not_block_stem_only_openqa_freeze", "tests.unit.test_evaluation_runner::test_freeze_preregisters_and_resume_does_not_repeat_calls", "tests.unit.test_evaluation_runner::test_interrupted_submission_reconciles_receipt_without_new_call", "tests.unit.test_evaluation_runner::test_ambiguous_unrecorded_submission_never_automatically_repeats", "tests.unit.test_evaluation_runner::test_environment_change_stops_new_calls_preserves_scheduled_set", "tests.unit.test_evaluation_runner::test_tampered_manifest_or_private_reference_rejected", "tests.unit.test_evaluation_runner::test_cancelled_export_retains_denominator_and_has_no_private_reference", "tests.unit.test_evaluation_runner::test_live_defaults_and_e1_redefinition_are_rejected", "tests.unit.test_evaluation_runner::test_repeat_export_preserves_existing_independent_review", "tests.unit.test_evaluation_runner::test_malformed_shared_response_is_retained_as_invalid"]`
- Acceptance references: [AC-38](<../acceptance.md#ac-38>), [AC-39](<../acceptance.md#ac-39>), [AC-40](<../acceptance.md#ac-40>), [AC-41](<../acceptance.md#ac-41>), [AC-42](<../acceptance.md#ac-42>), [AC-43](<../acceptance.md#ac-43>), [AC-44](<../acceptance.md#ac-44>), [AC-45](<../acceptance.md#ac-45>)
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
