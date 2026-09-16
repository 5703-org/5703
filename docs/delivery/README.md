# Generated delivery views

Generated reporting view. The canonical ledgers below remain authoritative; this file adds no product requirement or acceptance decision.

Accountable owner and suggested course week are reporting metadata, never permissions, implementation eligibility, runtime flags or evidence of completion. Actual executor and recorded dates are shown separately. Cross-references do not count a task more than once. No calendar dates or completion percentages are inferred.

Canonical requirements, shared interfaces and evidence: [PRD.md](<../../PRD.md>) · [SPEC.md](<../../SPEC.md>) · [PLANS.md](<../../PLANS.md>) · [HANDOVER.md](<../../HANDOVER.md>) · [docs/foundation/api_contract.md](<../foundation/api_contract.md>) · [contracts/openapi.json](<../../contracts/openapi.json>) · [docs/execution/tasks.json](<../execution/tasks.json>) · [docs/execution/reporting_plan.json](<../execution/reporting_plan.json>) · [docs/execution/acceptance.json](<../execution/acceptance.json>)

Task-ledger reconciliation timestamp (not a completion date): 2026-09-13T05:24:19.545152+00:00

This export implements source section 20.6 (INT-10, CHAT-12, QA-14 and owner handovers). Eight owner files and seven course-week files each partition the same 108 tasks exactly once. Repeated planning cross-references are not duplicate completion claims. The shared acceptance view retains all 60 check references.

Regenerate from the repository root with:

```text
python -m scripts.release.generate_delivery
python -m scripts.release.generate_delivery --check
```

Generation only writes this directory. The check mode compares bytes and reports stale/missing/extra generated files without writing. Regenerate after canonical ledger changes. The manifest records input and output hashes; the generated files contain no wall-clock generation timestamp.

## Owner views

- [Baiqing Huang](<by_owner/baiqing-huang.md>): 13 tasks
- [Chengzhou Liu](<by_owner/chengzhou-liu.md>): 12 tasks
- [Chong Zhang](<by_owner/chong-zhang.md>): 16 tasks
- [Hongle Yang](<by_owner/hongle-yang.md>): 12 tasks
- [Pengyuan Xia](<by_owner/pengyuan-xia.md>): 10 tasks
- [Sijin Lu](<by_owner/sijin-lu.md>): 12 tasks
- [Xianshu Zhang](<by_owner/xianshu-zhang.md>): 13 tasks
- [Zeping Liao](<by_owner/zeping-liao.md>): 20 tasks

## Suggested course-week views

- [Course week 6](<by_week/course-week-06.md>): 39 primary tasks
- [Course week 7](<by_week/course-week-07.md>): 34 primary tasks
- [Course week 8](<by_week/course-week-08.md>): 7 primary tasks
- [Course week 9](<by_week/course-week-09.md>): 8 primary tasks
- [Course week 10](<by_week/course-week-10.md>): 3 primary tasks
- [Course week 11](<by_week/course-week-11.md>): 8 primary tasks
- [Course week 12](<by_week/course-week-12.md>): 9 primary tasks

[All 60 acceptance references](<acceptance.md>)

## Canonical current-status meanings

- `NOT_IMPLEMENTED`: The named required artifact or result is absent.
- `IMPLEMENTED_UNVERIFIED`: Implementation exists, but required verification or a material part of acceptance remains open.
- `MOCK_TEST_PASSED`: The cited software scope passed with mock/simulated model or authored test inputs; no real-model quality claim.
- `REAL_FLOW_VERIFIED`: The cited real component flow ran (for example parser, PostgreSQL, HTTP or browser); read the explicit component boundary, not a whole-project claim.
- `WAITING_EXTERNAL`: The named remaining requirement needs a genuinely unavailable external input; independent work continues.

Secondary research/human fields and explicitly labelled planning states are copied unchanged even where they use a separate vocabulary. Answer-model, scientific, physical-device and human-review limitations remain those of each cited record.
