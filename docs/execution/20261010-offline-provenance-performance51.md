# Offline provenance and transcript checkpoint51

Two minimal production fixes are applied to the current learning assistant: persist canonical source IDs for every V2 unit, and start the session lookup and first transcript page together. Fresh actual-Main regressions pass215 Python cases/25 subtests and57 frontend cases. TypeScript and the two affected Python files' Ruff check pass. This checkpoint adds zero provider requests, fees, authentication operations, database access, service starts or dependency installations.

## Source diagnosis from retained responses

The [evidence table](evidence/20261010-offline-provenance-performance51/remaining-unit-evidence.md) and [exact spans and selections](evidence/20261010-offline-provenance-performance51/remaining-unit-evidence.json) compare the original10 claims/19 syntactic units/71 fragments with all8 retained proof46-50 responses. The root readback verifies15 input pins,6 review rows,15 source-span cards, source quotes, Unicode/UTF-8 offsets, original answer spans, allowed bindings and selected-versus-returned citation differences. This is a source-backed AI diagnosis, not human Gold or a local entailment certificate.

| Category | Finding |
|---|---|
| Original assertion has no basis in the71-fragment pool | Zero cases among the five previously partial unit IDs examined here. This does not establish general answer truth. |
| Candidate pool contains the proof, but the checker omits it | Five previously partial unit IDs have witness passages inside their existing claim bindings: full RuBP attributes/scope, long product identity, short product identity, short reduction classification, and export quantity/purpose. |
| Unit/claim/source binding mismatch | Actual47_01 and48_02 select export F011 but omit it from that claim's returned citations. Both remain ineligible for quality scoring. Separately, the production assessment stores unit FIDs in the wrong namespace; that generic defect is fixed below. |
| Review asks for more than the original assertion | ATP U03 (` which ATP`) is part of a joint subject. Allocation of the shared reduction predicate to this segment is ambiguous. Requiring ATP independently to donate electrons or duplicating the whole predicate without a defined ownership rule can exceed the assertion. Frozen counts are retained. |

For actual50, the definite short U04 selection needs F058 plus F059: conversion to G3P and its reduction classification. Its original statement does not separately assert an electron count or an ATP-only electron transfer. Export U02 needs F011 for one G3P per three turns and distinct F019/F020 for the leaving-G3P/carbohydrate continuation; no merged quote is invented. F001's purpose text is globally present but outside that short claim's binding.

All original supported labels, reasons and frozen aggregate counts remain preserved, including actual50's17 complete/2 partial units. No new same-case score, stability result or all-source PASS is substituted for those records.

## Production provenance repair

`generation/checked.py` already remaps judgment citations and assessment source quotes from transport aliases such as F001 to immutable span IDs. Its V2 stored obligation `fragment_ids` previously stayed aliased. Thus one persisted assessment and its next repair feedback contained two source-ID namespaces. The separate compact-joint path already performs the corresponding unit remap.

Five added lines at the existing cloned-assessment boundary now remap V2 obligation `fragment_ids` with the same alias map. Raw alias records and literal model reasons remain exact. Empty selections remain empty, and unknown aliases retain the existing explicit sentinel. No selection, verdict, prompt, schema, default, budget or publication gate changes.

The canonical ID reuses the existing `attribution.fragments` mapping to `source_unit_id`, start/end, exact text, hash and offset basis. Claim start/end and exact unit quotes are already retained. The same corrected assessment is persisted by the learning-state source consumer and reused by repair feedback, compact source text and the lossless claim-feedback codec. No additional provenance schema is needed.

Existing pipeline tests now verify joins to exact immutable source-unit slices and hashes, raw alias preservation, reworded and compound claims, short answers, missing conditions in either answer field, and partial/unsupported units. Negative labels and literal reasons stay unchanged; absent evidence is never filled automatically. The existing four-call repair regression additionally checks the feedback namespace while preserving passed text and requiring a complete fresh final check.

This fix makes existing mappings reusable; it does not resolve the retained model's semantic omissions. When a reliable negative verdict exists, the current bounded claim repair already targets defective claims and protects passed text. When every returned unit says supported, lexical overlap, candidate hints and shared claim citations do not identify a trustworthy missing semantic obligation. Automatically appending FIDs or rewriting those claims would need a new validated semantic decision mechanism. No such automatic correction is adopted here, and no biology-specific IDs or rules enter production.

## Historical41-second trace and local performance fix

The most recent retained native36 Send-to-full-paint observation is41144.9ms. It used historical checked/service/relation sources; it is not a measurement of this checkpoint.

| Retained clock | ms | Interpretation |
|---|---:|---|
| Initial generation POST | 5626 | Provider-stage interval |
| Initial joint checker POST | 10755 | Provider-stage interval |
| Repair POST | 9071 | Provider-stage interval |
| Full recheck POST | 7740 | Provider-stage interval |
| Four intervals together | 33192 | 80.671% of historical TFull |
| Repair plus recheck | 16811 | 40.858% of historical TFull |
| Retrieval wrapper | 463.534 | About1.13%; nested retrieval/rerank clocks overlap it |
| Terminal observation to full paint | 1302.6 | Includes polling, transcript fetch, rendering and paint |

Generation wall37108.756ms already includes provider intervals. Its3916.756ms residual has not been isolated into named stages. The outer3143.648ms residual is also not a pure queue/commit/render measurement. Keep publication227.207ms and worker-clock delta223.602ms separate. Failed native35's37533.6ms is TFailure, with null TFull. Older native26 used different question/source conditions and is not a controlled speedup baseline.

`frontend/src/Chat.tsx::loadTranscript` now starts the authorized session read and first messages-page read before awaiting either. The first-page promise captures early rejection, so session errors retain their existing priority and no unhandled rejection occurs while the session read is pending. Subsequent pages remain ordered; existing stale/unmount guards and all-or-nothing transcript commits remain active. The race regression verifies concurrent starts plus stale/unmounted completions, and recovery verifies early history rejection followed by authoritative session failure and successful reload without submitting work.

The change removes one avoidable sequential dependency. Its saved latency is unmeasured. It does not reduce the four model stages or establish current TFull, p95, RAG quality, noninferiority or a5-10second target. The clock review's earlier Promise.all suggestion was only a proposal; the adopted implementation deliberately preserves session-error priority with a captured first-page outcome.

## Current verification

Tests execute current Main modules and fixtures through installed dependencies. Outputs, temporary directories and transform caches are isolated under the owned checkpoint workspace. There is no wrapper replacing production behavior.

| Check | Current observed result |
|---|---|
| Existing source relation, protection/audit, feedback codec, local claim patch and bound repair suites | 215 passed;25 subtests passed;4.14s;exit0;no failures/skips |
| Existing Chat, ChatRepairContract, ChatTranscriptRace and ChatTranscriptRecovery suites | 57 passed;zero pending/todo/failures;exit0 |
| `tsc --noEmit --incremental false` | Exit0 |
| `ruff check --no-cache generation/checked.py tests/unit/test_source_relation_units_v2.py` | All checks passed;exit0 |
| Root exact evidence-table readback |10 original claims/71 fragments;15 pinned inputs;6 rows/15 cards;PASS |
| Two guarded Main promotions | Exact predecessor hashes verified;old bytes retained;all5 files read back exactly |

The first frontend attempt passed the6 recovery cases but failed to load three other suites because a sandbox temporary transformed module was missing (`ENOENT`). It is retained as a failed harness attempt. A second run with explicit owned TEMP/TMP/TMPDIR and one worker completed all57 cases; no source change was made between runs. Neither attempt ignores unhandled errors. Python's launcher also emits its known real-location warning for D:\Python\python.exe; pytest and Ruff exit0 and execute successfully.

Reproduction from Main, with `PYTHONDONTWRITEBYTECODE=1`, disabled pytest plugin autoload and `PYTHONPATH` covering Main/backend/tests/unit:

```text
.venv\Scripts\python.exe -B -m pytest tests/unit/test_source_relation_units_v2.py tests/unit/test_source_relation_contract.py tests/unit/test_source_relation_protection27.py tests/unit/test_source_relation_audit27.py tests/unit/test_claim_feedback_transport_v1.py tests/unit/test_claim_feedback_transport_service_v1.py tests/unit/test_local_claim_patch.py tests/unit/test_bound_repair_patch.py tests/unit/test_bound_repair_pipeline.py tests/unit/test_bound_repair_public_projection.py -q -p no:cacheprovider --basetemp=<new-owned-temp> --junitxml=<new-owned-result.xml>
```

The frontend uses the installed Vitest5 CLI with `--configLoader runner --no-cache --maxWorkers 1 --no-file-parallelism --reporter json`; the retained temporary config imports the unchanged Main Vite configuration and only redirects root/cache location. Exact commands and current source pins are in [verification51.json](evidence/20261010-offline-provenance-performance51/verification51.json).

## Preserved state and independent acceptance

The canonical task/check registries remain byte-exact and `project_complete=false`. Human ratings remain zero/null. Historical proof46-50 report/evidence remain byte-exact; their8 requests/$0.13136218 closed scope has no remaining physical slots. This checkpoint spends nothing and does not release the historical41 $0.045 UNKNOWN hold.

Fresh whole-project foundation/contracts/chat-scope/all-mock qualification is not claimed. Those exact interfaces have fixed output paths, foundation regenerates schema/old evidence, and the full mock gate discovers local DB configuration and includes database tests. They are not run during this offline, no-auth/no-DB checkpoint. The affected tests above supply the current software evidence; prior whole-project records remain historical.

Git status/worktree inspection remains unavailable in this execution identity: ownership rejection followed by an explicit worktree error. `.git/HEAD` reads `refs/heads/master`; no Git mutation, reset, commit or branch change occurs. No protected private databases, experiment inputs/results, old deliveries or other projects are accessed or modified. E: has23.97GiB free at the15:14:51UTC read; no installation or large copy is performed.

Independent pending acceptance remains: reliable selected-source completeness on varied real model cases, unified-condition generation/RAG comparison, current native Send-to-full-answer measurement, full eight-stage qualification, formal p95/noninferiority, human evaluation, clean installation and course-final review. The next real-model/page run must be a separate explicitly scoped execution; this checkpoint continues only the offline repair and evidence work.

Public checkpoint index: [index.json](evidence/20261010-offline-provenance-performance51/index.json). Prior closed replay report: [proof46-50](20261010-proof46-50.md).
