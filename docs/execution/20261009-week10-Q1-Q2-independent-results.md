# Week10 Q1 and Q2: independent native RAG results

Both original questions now have accepted, complete cited answers that persisted after refresh. They ran on **different workers**. Q1 passed inside continuous02, whose overall browser/controller/runtime leg failed before Q2 was sent. After that worker closed, the specifically authorized **first execution of Q2** passed on a new worker and ended in normal native CLOSED. Q1 was not repeated. The original [Q1 partial report](20261009-week10-continuous-worker-partial-result.md), failed receipts, screenshots and STOP remain unchanged; the later Q2 success does not convert that earlier leg into PASS.

| Identity and outcome | Q1 | Q2 |
|---|---|---|
| Question | Net products of glycolysis per glucose | How light-dependent reactions supply Calvin-cycle energy carriers |
| Execution | continuous02 | Q2 singleton03; first Q2 submission |
| Worker PID / Engine identity | `66652` / `2229621415552` | `13352` / `2757691235632` |
| Native answer | `succeeded`, complete, cited, refreshed | `succeeded`, complete, cited, refreshed |
| Overall leg | Failed after accepted Q1; Q2 not submitted | PASS; normal native CLOSED |
| Unique citation IDs | 2 | 6; 8 inline controls include repeated markers |

The same owned synthetic B learner/database current state, Google Gemini 3.5 Flash Lite through OpenRouter's Google Vertex/global route, R2/native E5 retrieval, MiniLM reranking on CUDA and four CPU threads were retained. No production-code change, database reset, old-job recovery, runtime retrieval override, new model qualification or old STOP clearing was used. Main's public source versions differ because documentation and public evidence were added: Q1 used `42359d2d2cd2f8d28007173a20d20e994d5d767372acd597d5e3d495f552885f` (1538 public files); Q2 used `1ada08eec0778fdf84dd1c2cdd2d9e946bafc9cddbef6bbbd85cf66ee04263c1` (1564). Root's declared freeze retained the same 394 production/assets pins. These are two finite functionality observations, not matched or randomized quality/speed benchmarks.

Both requests used normal chapter navigation, **Remove reading context**, and normal Send. The submitted body had no reading context, document filter or chapter filter: `reading_scope=null`, `retrieval_scope=all_active_corpus`, `chapter_filter_applied=false`. Biology 2e 7.2 and 8.2 identify the navigation origins only. Q2's opened citation came from **Concepts of Biology 5.2**, which is consistent with full-corpus retrieval and is not a chapter-scope defect. No strict chapter-filtered acceptance or cross-scope cache-reuse claim is made.

| Actual clock or stage, milliseconds | Q1 | Q2 |
|---|---:|---:|
| Send to complete answer DOM | 9047.7 | 12146.8 |
| Send to first painted prose | 9013.2 | 12146.3 |
| Send to observed HTTP 202 | 276.7 | 241.5 |
| Runtime launch to worker ready | 14451.3 | 15027.1 |
| Worker ready to Send | 4236.1 | 3614.2 |
| Runtime launch to complete answer | 27735.1 | 30788.1 |
| Runner main entry to worker ready | 13878.968 | 14003.232 |
| Native model warmup | 5585.051 | 5591.778 |
| Startup release-cache preparation | 6178.206 | 6232.533 |
| Startup release validation | 6078.4192 | 6147.8983 |
| Submission to worker start | 484.543 | 210.269 |
| Worker preparation / query preparation | 31.771 / 1.689 | 51.956 / 1.711 |
| Teaching plan | 0.245 | 0.237 |
| Business release-cache validation; hit | 8.6338 | 3.5575 |
| Query embedding; query-vector cache miss | 6.9619 | 7.1908 |
| Dense / lexical retrieval | 39.5023 / 6.3397 | 36.6025 / 6.4941 |
| Native retrieval stage total | 88.6884 | 72.8869 |
| Reranking; 20 candidates, CUDA | 66.9957 | 59.6788 |
| Outer retrieval timing | 166.264 | 142.356 |
| Teacher / checker provider latency | 3279 / 3105 | 5472 / 4186 |
| Model latency total | 6384 | 9658 |
| Generation wall time | 7213.506 | 10600.680 |
| Native worker execution before answer insertion | 7633.954 | 11006.370 |
| Publication before commit / worker before commit | 276.518 / 7908.170 | 256.216 / 11259.984 |

The clock boundaries overlap and must not be summed. In particular, **142.356 ms is Q2 outer retrieval time, not its total worker time**. Startup includes cold process model preparation and release validation; launch-to-ready additionally includes imports and artifact checks. Startup costs remain included in the launch-to-complete journey. Complete DOM means the complete published body was observed, not every character simultaneously visible or read by a learner. DOM clocks include sampling and DTO observation overhead. First painted prose is not provider TTFT; this non-streaming UI did not measure TTFT.

Each worker's own startup cache preparation was followed by a business release-cache hit in that worker/Engine. Both question-vector cache checks were misses. This proves those two individual cache observations, **not reuse from Q1 to Q2 across workers**. Release epochs stayed stable; no intentional invalidation was tested. Local model instances were prepared in their respective processes; operating-system file caches may have been warmed by integrity reads. There was no repeated-query control, p95 distribution, SLA test or causal speedup experiment.

RSS was null in both traces. CUDA maximum allocated/reserved values were Q1 `365905408`/`423624704` bytes and Q2 `366198784`/`423624704` bytes. Peak counters were not reset; these are cumulative peaks for separate processes, not per-question memory increments. The shared CUDA model/device and candidate count do not establish uniform load or absence of system contention.

Q1 answered two pyruvate, net two ATP and two NADH per glucose. Its opened Source 1, **Biology 2e 7.2, PDF physical page 215**, directly supports the core answer, including four ATP produced minus two consumed. Source 2 was not independently opened and reviewed. The preserved [Q1 source screenshot](evidence/20261009-week10-continuous02/browser-continuous02/Q1-citation.png) and [browser receipt](evidence/20261009-week10-continuous02/browser-continuous02/real-browser-live-qa-receipt01.json) retain the actual observation.

Q2 explained conversion of light to chemical energy, ATP/NADPH formation through photosystems/electron transport, transfer to the stroma/Calvin cycle, and return of spent carriers. The opened Source 1, **Concepts of Biology 5.2, PDF physical page 138**, directly supports only the light-to-chemical-energy statement. Bodies supporting the remaining ATP/NADPH, photosystem, electron-chain, stroma and spent-carrier claims were not individually opened and independently assessed. Its six unique citations and normal full checker PASS remain model-supported publication evidence, not full independent scientific verification. Q2's finite review is **PARTIAL_SOURCE_BODY_REVIEW**, with no human rating or comprehensive independent evaluation. See its [source screenshot](evidence/20261009-week10-q2-singleton03/browser-continuous03/Q2-citation.png), [refreshed screenshot](evidence/20261009-week10-q2-singleton03/browser-continuous03/Q2-refreshed.png), and [finite review](evidence/20261009-week10-q2-singleton03/continuous-preparation/ACTUAL_Q2_FINITE_PUBLIC_SUPPORT_REVIEW01.json).

The earlier Q2 pre-Send failure showed Loading contents. Browser05's one-line awaited chapter-count correction replaced an immediate count against a potentially stale observer Map. Browser07's actual Q2 run exercised that normal awaited chapter-control, navigation, context-removal and Send path successfully. This is execution evidence for the corrected harness path; no Main product UI code changed, and it does not prove every loading race is resolved.

| Settled provider-reported cost, USD | Teacher | Checker | Subtotal | POSTs |
|---|---:|---:|---:|---:|
| Q1 | 0.00443330 | 0.00426870 | 0.00870200 | 2 |
| Q2 | 0.00660050 | 0.00519860 | 0.01179910 | 2 |
| Q1 and Q2 new requests | | | 0.02050110 | 4 |
| Earlier paired run | | | 0.01936904 | 4 |
| Authorized campaign total | | | **0.03987014** | **8** |

All new claims are settled, with zero new UNKNOWN/open claims. All eight authorized physical POST slots are consumed despite the cost being below the original $0.24 ceiling. The old fourteen UNKNOWN cases and their protections remain under the existing policy. These figures are settled provider-reported costs, not account or invoice balances. There is no automatic replay or remaining POST permission.

Q2 browser/runtime processes exited 0, Jobs and collectors closed, threads/database resources closed, native checked completion passed, and advisory-unlock/connection-close/Engine-dispose closure passed. Its [controller](evidence/20261009-week10-q2-singleton03/continuous-preparation/ROOT_CONTINUOUS_CONTROLLER_ACTUAL03.json) records `ACTUAL_Q2_FIRST_EXECUTION_NEW_WORKER_PASS_BATCH_CLOSED`; its [runtime](evidence/20261009-week10-q2-singleton03/runtime-continuous03/runtime-closed-public01.json) records `CLOSED`. The final runtime budget snapshot says READY/`stop_exists=false` because it preceded Root's success STOP; the retained [actual STOP](evidence/20261009-week10-q2-singleton03/claims-continuous03/STOP-before-any-next-submission01.json) exists and prohibits another submission. The [financial receipt](evidence/20261009-week10-q2-singleton03/analysis-preparation/ACTUAL_CONTINUOUS03_Q2_ONLY_FINANCIAL_RESULT01.json) reconciles both states. Q1's earlier overall failed-leg state is preserved separately.

The [Q2 public evidence index](evidence/20261009-week10-q2-singleton03/index.json) records original source paths, bytes and SHA256 with byte-identical copies. The preserved Q1 evidence index remains at `docs/execution/evidence/20261009-week10-continuous02/index.json`. This successor report does not establish the original two-question same-worker/Engine objective, chapter-filtered or cross-scope quality, p95, causal cache superiority, independent scientific acceptance, learning benefit or project/course completion. Preparing the report and copies caused no Main writes, service/API/DB execution, model calls, tests or changes to prior evidence/STOPs. A separate delivery process packages only the approved public evidence for a new Library item; earlier Library items remain unchanged.


[Q1/Q2 sanitized original evidence archive](https://chatgpt.com/api/library/files/libfile_8402191335588191be4702caab60e52f/download): Library ID `libfile_8402191335588191be4702caab60e52f`, version0, ZIP520174B/SHA256 `5379c7cc4c47ec0d81b1b3d3e5e2f569db0ce6e802526bc37cd7a0afa4c68c96`. The archive records two independent worker observations and preserves the earlier failed leg; it does not establish same-worker reuse or independent scientific acceptance.
