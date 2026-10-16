# Delivery view: Baiqing Huang

Generated reporting view. The canonical ledgers below remain authoritative; this file adds no product requirement or acceptance decision.

Accountable owner and suggested course week are reporting metadata, never permissions, implementation eligibility, runtime flags or evidence of completion. Actual executor and recorded dates are shown separately. Cross-references do not count a task more than once. No calendar dates or completion percentages are inferred.

Canonical requirements, shared interfaces and evidence: [PRD.md](<../../../PRD.md>) · [SPEC.md](<../../../SPEC.md>) · [PLANS.md](<../../../PLANS.md>) · [HANDOVER.md](<../../../HANDOVER.md>) · [docs/foundation/api_contract.md](<../../foundation/api_contract.md>) · [contracts/openapi.json](<../../../contracts/openapi.json>) · [docs/execution/tasks.json](<../../execution/tasks.json>) · [docs/execution/reporting_plan.json](<../../execution/reporting_plan.json>) · [docs/execution/acceptance.json](<../../execution/acceptance.json>)

Task-ledger reconciliation timestamp (not a completion date): 2026-09-08T10:09:00.459775+00:00

This owner view contains 13 unique domain tasks. Shared interfaces remain in the central specifications linked above.

Task index: [FE-01](<baiqing-huang.md#fe-01>), [FE-02](<baiqing-huang.md#fe-02>), [FE-03](<baiqing-huang.md#fe-03>), [FE-04](<baiqing-huang.md#fe-04>), [FE-05](<baiqing-huang.md#fe-05>), [FE-06](<baiqing-huang.md#fe-06>), [FE-07](<baiqing-huang.md#fe-07>), [FE-08](<baiqing-huang.md#fe-08>), [FE-09](<baiqing-huang.md#fe-09>), [FE-10](<baiqing-huang.md#fe-10>), [FE-11](<baiqing-huang.md#fe-11>), [FE-12](<baiqing-huang.md#fe-12>), [CHAT-06](<baiqing-huang.md#chat-06>)

## FE-01

Create the typed frontend. Build one React/TypeScript application with routes, shared API types and ordinary error handling. Explicit mock transport is isolated; real API mode has no hidden mock fallback.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 6, "suggested_project_week": 4, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G1
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["INT-04", "INT-03"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-04"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "INT-03"}]`
- Upstream collaborators (derived from those dependencies): [INT-04](<xianshu-zhang.md#int-04>) — Xianshu Zhang; [INT-03](<xianshu-zhang.md#int-03>) — Xianshu Zhang
- Downstream collaborators (reverse dependency references): [FE-02](<baiqing-huang.md#fe-02>) — Baiqing Huang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Create the typed frontend. Build one React/TypeScript application with routes, shared API types and ordinary error handling. Explicit mock transport is isolated; real API mode has no hidden mock fallback.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-01](<../acceptance.md#ac-01>), [AC-36](<../acceptance.md#ac-36>)
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

## FE-02

Complete login and account transitions. Wire login, expiry/re-login, logout, role navigation and password change. Clear account-specific state on switch; disabling a user must be enforced by the server, not navigation alone.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 6, "suggested_project_week": 4, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G2
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-01", "BE-03"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-01"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-03"}]`
- Upstream collaborators (derived from those dependencies): [FE-01](<baiqing-huang.md#fe-01>) — Baiqing Huang; [BE-03](<zeping-liao.md#be-03>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-03](<baiqing-huang.md#fe-03>) — Baiqing Huang; [FE-07](<baiqing-huang.md#fe-07>) — Baiqing Huang; [FE-10](<baiqing-huang.md#fe-10>) — Baiqing Huang; [FE-11](<baiqing-huang.md#fe-11>) — Baiqing Huang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Complete login and account transitions. Wire login, expiry/re-login, logout, role navigation and password change. Clear account-specific state on switch; disabling a user must be enforced by the server, not navigation alone.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-14](<../acceptance.md#ac-14>), [AC-16](<../acceptance.md#ac-16>), [AC-31](<../acceptance.md#ac-31>), [AC-43](<../acceptance.md#ac-43>)
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

## FE-03

Implement a natural-language chat composer. One multiline text field, send/Enter/Shift+Enter, draft preservation, profile toggle and idempotency. No required A–D fields, gold controls or SciQ selection. Follow-up suggestions send ordinary text to the same session.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 6, "suggested_project_week": 4, "suggested_start_course_week": 6, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G3
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-02", "GEN-01"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-01"}]`
- Upstream collaborators (derived from those dependencies): [FE-02](<baiqing-huang.md#fe-02>) — Baiqing Huang; [GEN-01](<sijin-lu.md#gen-01>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [FE-04](<baiqing-huang.md#fe-04>) — Baiqing Huang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Implement a natural-language chat composer. One multiline text field, send/Enter/Shift+Enter, draft preservation, profile toggle and idempotency. No required A–D fields, gold controls or SciQ selection. Follow-up suggestions send ordinary text to the same session.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-08](<../acceptance.md#ac-08>), [AC-12](<../acceptance.md#ac-12>), [AC-36](<../acceptance.md#ac-36>), [AC-44](<../acceptance.md#ac-44>), [HC-04](<../acceptance.md#hc-04>)
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
- Upstream collaborators (derived from those dependencies): [FE-03](<baiqing-huang.md#fe-03>) — Baiqing Huang; [BE-08](<zeping-liao.md#be-08>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-05](<baiqing-huang.md#fe-05>) — Baiqing Huang; [CHAT-08](<zeping-liao.md#chat-08>) — Zeping Liao
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
- Upstream collaborators (derived from those dependencies): [FE-04](<baiqing-huang.md#fe-04>) — Baiqing Huang; [BE-08](<zeping-liao.md#be-08>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-06](<baiqing-huang.md#fe-06>) — Baiqing Huang; [FE-08](<baiqing-huang.md#fe-08>) — Baiqing Huang; [FE-09](<baiqing-huang.md#fe-09>) — Baiqing Huang; [CHAT-06](<baiqing-huang.md#chat-06>) — Baiqing Huang
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
- Upstream collaborators (derived from those dependencies): [FE-05](<baiqing-huang.md#fe-05>) — Baiqing Huang; [BE-09](<zeping-liao.md#be-09>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-12](<baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-06](<baiqing-huang.md#chat-06>) — Baiqing Huang
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
- Upstream collaborators (derived from those dependencies): [FE-02](<baiqing-huang.md#fe-02>) — Baiqing Huang; [BE-04](<zeping-liao.md#be-04>) — Zeping Liao; [PER-04](<pengyuan-xia.md#per-04>) — Pengyuan Xia
- Downstream collaborators (reverse dependency references): [PER-05](<pengyuan-xia.md#per-05>) — Pengyuan Xia; [FE-12](<baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<chong-zhang.md#qa-12>) — Chong Zhang
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
- Upstream collaborators (derived from those dependencies): [FE-05](<baiqing-huang.md#fe-05>) — Baiqing Huang; [BE-05](<zeping-liao.md#be-05>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-12](<baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-06](<baiqing-huang.md#chat-06>) — Baiqing Huang
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
- Upstream collaborators (derived from those dependencies): [FE-05](<baiqing-huang.md#fe-05>) — Baiqing Huang; [BE-10](<zeping-liao.md#be-10>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-12](<baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<chong-zhang.md#qa-12>) — Chong Zhang
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
- Upstream collaborators (derived from those dependencies): [FE-02](<baiqing-huang.md#fe-02>) — Baiqing Huang; [BE-06](<zeping-liao.md#be-06>) — Zeping Liao; [BE-12](<zeping-liao.md#be-12>) — Zeping Liao
- Downstream collaborators (reverse dependency references): [FE-12](<baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<chong-zhang.md#qa-12>) — Chong Zhang
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

## FE-11

Implement secondary administrator evaluation pages. Distinguish chat_scenarios, sciq_openqa, sciq_mcq and profile studies; show protocols, denominators and all outcome states. These pages do not become the learner landing page or a prerequisite for chat.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 9, "suggested_project_week": 7, "suggested_start_course_week": 8, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G6
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-02", "BE-11", "BE-12", "QA-06"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-11"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-12"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-06"}]`
- Upstream collaborators (derived from those dependencies): [FE-02](<baiqing-huang.md#fe-02>) — Baiqing Huang; [BE-11](<zeping-liao.md#be-11>) — Zeping Liao; [BE-12](<zeping-liao.md#be-12>) — Zeping Liao; [QA-06](<chong-zhang.md#qa-06>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [FE-12](<baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-11](<xianshu-zhang.md#chat-11>) — Xianshu Zhang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Implement secondary administrator evaluation pages. Distinguish chat_scenarios, sciq_openqa, sciq_mcq and profile studies; show protocols, denominators and all outcome states. These pages do not become the learner landing page or a prerequisite for chat.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-18](<../acceptance.md#ac-18>), [AC-19](<../acceptance.md#ac-19>), [AC-37](<../acceptance.md#ac-37>), [AC-46](<../acceptance.md#ac-46>)
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

## FE-12

Finish usability and frontend handover. Validate English labels, keyboard operation, narrow/desktop layouts and every control’s real effect. Run browser journeys against the real API; deliver startup and UI documentation.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 12, "suggested_project_week": 10, "suggested_start_course_week": 11, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G9
- Current status: `IMPLEMENTED_UNVERIFIED`
- Separate implementation / verification / research / human-review states: `IMPLEMENTED_UNVERIFIED` / `IMPLEMENTED_UNVERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-06", "FE-07", "FE-08", "FE-09", "FE-10", "FE-11", "QA-12"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-06"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-10"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-11"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-12"}]`
- Upstream collaborators (derived from those dependencies): [FE-06](<baiqing-huang.md#fe-06>) — Baiqing Huang; [FE-07](<baiqing-huang.md#fe-07>) — Baiqing Huang; [FE-08](<baiqing-huang.md#fe-08>) — Baiqing Huang; [FE-09](<baiqing-huang.md#fe-09>) — Baiqing Huang; [FE-10](<baiqing-huang.md#fe-10>) — Baiqing Huang; [FE-11](<baiqing-huang.md#fe-11>) — Baiqing Huang; [QA-12](<chong-zhang.md#qa-12>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [INT-10](<xianshu-zhang.md#int-10>) — Xianshu Zhang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Finish usability and frontend handover. Validate English labels, keyboard operation, narrow/desktop layouts and every control’s real effect. Run browser journeys against the real API; deliver startup and UI documentation.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-16](<../acceptance.md#ac-16>), [AC-37](<../acceptance.md#ac-37>), [AC-43](<../acceptance.md#ac-43>), [AC-44](<../acceptance.md#ac-44>), [AC-45](<../acceptance.md#ac-45>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [docs/execution/ui_acceptance.json](<../../execution/ui_acceptance.json>), [docs/frontend.md](<../../frontend.md>), [docs/execution/keyboard-suggestion-verification.md](<../../execution/keyboard-suggestion-verification.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Connected English browser journeys, keyboard/focus checks, responsive widths and native desktop zoom are recorded. Actual Enter/Shift+Enter, a persisted suggestion click, polled progress and rejection/draft/history checks now pass; failure alerts are fully visible at 1440/390 without losing intentional older reading positions.
- Unresolved scope: Physical mobile keyboard, native IME, assistive technology and independent human acceptance remain unverified where required by the responsive subchecks.
- Blockers: None recorded.
- Mapping limitation: Physical mobile keyboard, native IME, assistive technology and independent human acceptance remain unverified where required by the responsive subchecks.

Recorded component observations:

- observed task scope: `IMPLEMENTED_UNVERIFIED`. Connected English browser journeys, keyboard/focus checks, responsive widths and native desktop zoom are recorded. Actual Enter/Shift+Enter, a persisted suggestion click, polled progress and rejection/draft/history checks now pass; failure alerts are fully visible at 1440/390 without losing intentional older reading positions.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [docs/execution/ui_acceptance.json](<../../execution/ui_acceptance.json>), [docs/frontend.md](<../../frontend.md>), [docs/execution/keyboard-suggestion-verification.md](<../../execution/keyboard-suggestion-verification.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Physical mobile keyboard, native IME, assistive technology and independent human acceptance remain unverified where required by the responsive subchecks.

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
- Upstream collaborators (derived from those dependencies): [FE-05](<baiqing-huang.md#fe-05>) — Baiqing Huang; [FE-06](<baiqing-huang.md#fe-06>) — Baiqing Huang; [FE-08](<baiqing-huang.md#fe-08>) — Baiqing Huang; [CHAT-05](<sijin-lu.md#chat-05>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [INT-06](<xianshu-zhang.md#int-06>) — Xianshu Zhang; [CHAT-07](<pengyuan-xia.md#chat-07>) — Pengyuan Xia; [CHAT-10](<chong-zhang.md#chat-10>) — Chong Zhang
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
