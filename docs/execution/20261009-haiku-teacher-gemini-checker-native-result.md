# Haiku teacher / Gemini checker native Q2 result — 9 October 2026

The actual ordinary browser Q2 request reached both models but failed native publication. Gemini's checker object omitted the required `attempt_evaluation_ok` field. The saved native job records Pydantic `missing` at that field, `CHECKER_SCHEMA_INVALID`, and terminal `CHECKER_INCONSISTENT`. No answer ID was created. The strict local contract remains enforced.

| Role | Exact model | Protocol / output cap | HTTP | Adapter latency | Input / output tokens | Known cost |
|---|---|---|---|---:|---:|---:|
| Teacher | `anthropic/claude-haiku-5.5` | json_schema / 2048 | 200 | 6617 ms | 15696 / 599 | $0.0018691 |
| Checker | `google/gemini-3.5-flash-lite` | json_object / 4096 | 200 | 5204 ms | 10422 / 1573 | $0.0070591 |

The new mixed scope used exactly 2/2 physical POSTs and $0.0089282 known cost against its $0.06 limit. Both costs are recorded, with zero open claims, new UNKNOWN, pending cleanup or integrity errors. It is STOPPED and has no remaining call slots. Older campaign UNKNOWN protection remains $0.09; it is separate from this scope's cost and is not a confirmed billing total. Monetary headroom does not authorize another request.

## Observed product journey

The existing built Chat UI performed normal login, created a fresh ordinary chat and routed one Q2 message. Reading context was null, retrieval covered the active corpus without a chapter filter, and the existing native retrieval/default configuration remained bound. The question was the previously exercised light-dependent-reactions/Calvin-cycle Q2; this is a development regression, not unseen-question quality acceptance.

The browser observed the native failed job **14296.39990234375 ms after Send**. It did not wait the earlier 300-second timeout. First answer, full answer, TTFT and process-launch-to-complete-answer clocks are null. Citation and refresh checks did not pass because no answer was published. The failure clock is not complete-answer latency or a successful speed result.

The precise read-only diagnosis is [failed-job-safe-diagnosis01.json](evidence/20261009-haiku-teacher-gemini-checker-native01/failed-job-safe-diagnosis01.json). It reads only the new synthetic session/request/job's saved code and bounded public diagnostic fields, with transaction_read_only=on and zero database writes or model POSTs. The native parser had progressed to model validation; the observed blocker is a missing required schema field, not a demonstrated business citation inconsistency.

## Local changes and free validation

The main gateway already supports distinct teacher and checker configs and credential resolution. This experiment used a process-only Haiku teacher override and the existing Gemini checker config. It did not activate a model, change saved configurations, move production pointers or qualify Haiku checker. The exact original full checker schema remains `7988037e08d52662a1b232f049776a42b6d10ad5d896f1a26c8c912b3efd79d4`.

The browser observer now exits on a known failed/cancelled job or the current public STOP. Runtime shutdown allows at most three seconds for the matching terminal GET to be delivered while refusing new non-GET actions. The free actual UI regression passed: typed failure visible, draft restored, pending/spinner cleared, Send reenabled, and owned services closed. Its UI checks completed at 1318 ms and shutdown window was about 375 ms; these synthetic-failure checks are separate from the actual mixed-model failure clock.

Free role isolation passed 20 checks and 40 concurrent pairs; the final browser public preflight passed 28/28 strict synthetic checks and Node syntax validation. These checks add no remote-model or project-qualification evidence.

A first mixed startup failed before browser Send because its qualification assertion retained the old batch nonce. It made zero provider calls, and its closed resources, failed receipt and STOP were preserved. A minimal successor corrected that assertion and explicit role/protocol gates, then consumed the same wholly unused two-call authorization. No budget was added and no previously sent provider request was retried. Earlier preparation/test-helper failures also remain preserved in the workspace.

## Closure and limits

Browser/context, owned Windows jobs, collectors, runtime threads and database resources closed; cleanup error classes are empty and active pointers are unchanged. The native failed leg is not a successful CLOSED/PASS leg. Existing databases, protected staging areas, experiment data, old deliveries and all prior STOPs were retained. This batch wrote only append-only synthetic request/job/attempt data during the ordinary test and these public documents/evidence afterward.

The prior Haiku checker8192 experiment still failed strict JSON parsing. Its runner did not retain the precise parser subcode or raw response, so invalid JSON versus duplicate keys remains unobserved. This new Gemini missing-field result does not diagnose or qualify Haiku checker. No 16384 retry was made.

No unified Haiku/Luna/DeepSeek RAG quality comparison, independent semantic/source rating, complete-answer success or warm p95 is established. The next engineering task is to inspect the JSON-object checker prompt/producer's handling of all required fields while retaining strict validation. Any further live confirmation needs an explicit finite successor-call authorization; this scope has no remaining calls.

Canonical status remains 108 tasks (66 REAL / 31 MOCK / 9 unverified / 2 external), 60 checks (33 REAL / 26 MOCK / 1 unverified), and 53 matrix rows (5 verified / 38 pending / 8 incomplete / 2 external), with `project_complete=false`. Current880's earlier validation and incomplete whole-current883 verification are not promoted by this result.

[Exact public evidence index](evidence/20261009-haiku-teacher-gemini-checker-native01/index.json). Earlier results: [Haiku native JSON-object failure](20261009-haiku-native-json-object-regression-result.md), [saved-teacher cap result](20261009-saved-teacher-checker-cap-result.md).
