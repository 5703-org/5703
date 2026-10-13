# Week10 continuous-worker RAG: actual partial result

The 2026-10-09 continuous02 run published and displayed a complete, cited answer for Q1. Q2 stopped before Send while the textbook chapter DOM was still loading. This is a partial observation, not a completed two-question acceptance run. The browser and controller retain their original failure statuses; the accepted Q1 is preserved.

The run used the existing owned synthetic B database and learner, one native worker and Engine, the current R2 retrieval profile, and the normal UI. Reading context was removed with the normal **Remove reading context** action before Q1 was sent. Retrieval therefore used **all active corpus**, with `reading_scope=null` and `chapter_filter_applied=false`. The glycolysis chapter and the planned photosynthesis chapter are navigation origins, not retrieval filters. Main application code and the existing budget were unchanged for this continuation.

| Observation | Actual result |
|---|---|
| Q1 | PASS; terminal `succeeded`; complete cited answer; source dialog opened; persisted after refresh |
| Q2 | `NOT_EXECUTED_PRE_SEND_FAILURE`; `SINGLE_NORMAL_CHAPTER_CONTROL_REQUIRED`; zero model POSTs |
| Browser | `ACTUAL_LIVE_UI_JOURNEY_FAILED_OR_BLOCKED` |
| Controller | `ACTUAL_CONTROLLER_BLOCKED_OR_FAILED_NO_RETRY` |
| Runtime | `CLEANUP_FAILED_OR_LEG_FAILED`; owned threads and database resources closed; normal native CLOSED not observed |

Q1 asked, “What are the net products of glycolysis per glucose molecule?” The published answer reported two pyruvate, net two ATP, and two NADH per glucose, with two citation controls. The opened Source 1 passage from **Biology 2e, 7.2 Glycolysis, PDF physical page 215** directly supports those core statements: four ATP are produced and two are consumed, giving net two. This was an assistant comparison with the displayed source, not a human rating or an independent scientific evaluation. Source 2's body was not individually reviewed. Model checking, citation visibility and refresh persistence do not establish general RAG quality.

[Q1 source screenshot](evidence/20261009-week10-continuous02/browser-continuous02/Q1-citation.png), [source text](evidence/20261009-week10-continuous02/browser-continuous02/Q1-citation.txt), [refreshed screenshot](evidence/20261009-week10-continuous02/browser-continuous02/Q1-refreshed.png), and [actual browser receipt](evidence/20261009-week10-continuous02/browser-continuous02/real-browser-live-qa-receipt01.json) preserve this observation.

| Timing or execution boundary | Q1 observation |
|---|---:|
| Send to complete answer DOM | 9047.7 ms |
| Send to first painted prose | 9013.2 ms; not provider TTFT |
| Runtime launch to worker ready | 14451.3 ms |
| Runtime launch to complete Q1 answer | 27735.1 ms |
| Native worker execution before answer insertion | 7633.954 ms |
| Outer retrieval timing | 166.264 ms |
| Release-cache validation on business load | 8.6338 ms; cache hit |
| Native reranking | 66.9957 ms; 20 candidates; CUDA |

The [native Q1 trace](evidence/20261009-week10-continuous02/runtime-continuous02/native-retrieval-0503d729-ea72-41a0-a2c3-486422cb2ba0-public01.json) confirms R2/MiniLM execution on CUDA, a release-cache hit, and **no query-vector cache hit**. Startup preparation took 6178.206 ms, including 6078.4192 ms of release validation; model warmup separately took 5585.0508 ms. These startup costs remain part of the full launch journey. Worker PID `66652` and Engine identity `2229621415552` bind the executed Q1; they cannot demonstrate reuse across two submitted questions because Q2 was not submitted. Release epoch remained stable; invalidation was not intentionally triggered.

RSS was not measured. CUDA maximum allocated/reserved values were `365905408`/`423624704` bytes with peak counters **not reset**. These are cumulative process peaks, not per-question memory increments. DOM timing includes observation and sampling overhead; this non-streaming UI did not measure provider TTFT. One Q1 result cannot establish p95, an SLA, a causal cache speedup, model superiority, cross-scope quality, or scientific/course completion.

The [financial receipt](evidence/20261009-week10-continuous02/analysis-preparation/ACTUAL_CONTINUOUS02_SUBBATCH_FINANCIAL_RESULT01.json) records two submitted and settled Q1 POSTs: teacher **$0.00443330** and checker **$0.00426870**, totaling **$0.00870200**. Q2 cost is **$0.00000000**. Including the earlier settled pair, the authorized campaign observed **6 POSTs / $0.02807104**, within the original **8 POST / $0.24** ceiling. New UNKNOWN and open claims are both zero. These are provider-reported settled costs, not invoice or account balances. Two unused continuation slots do not authorize automatic replay; the [STOP](evidence/20261009-week10-continuous02/claims-continuous02/STOP-before-any-next-submission01.json) remains immutable. The old fourteen UNKNOWN cases remain under their existing policy.

The retained Q2 [screenshot](evidence/20261009-week10-continuous02/browser-continuous02/retained-failure.png) and [text](evidence/20261009-week10-continuous02/browser-continuous02/retained-failure.txt) show **Loading contents**. The observer Map still held Q1 sections by book ID, so `has(bookID)` could pass before the reopened reader's current DOM was ready; the immediate chapter locator count then failed. The exact failed count was not retained. This supports an automation loading/wait race, not a proven product or API defect or duplicate chapter controls. The earlier scoped-combobox correction was exercised by Q1.

Browser05 replaces that immediate count with `await expect(chapterButton).toHaveCount(1, { timeout: 15000 })`. Only one line changed, and one local `node --check` passed. Its [diff](evidence/20261009-week10-continuous02/continuous-preparation/BROWSER_CHAPTER_DOM_WAIT_PREPARED05.diff), [parse receipt](evidence/20261009-week10-continuous02/continuous-preparation/BROWSER_CHAPTER_DOM_WAIT_LOCAL_PARSE_ACTUAL05.json), and [public candidate](evidence/20261009-week10-continuous02/continuous-preparation/real_browser_week10_continuous_scopes_PREPARED05.cjs) are retained. **No browser05 launch, API call, model POST, or live Q2 validation occurred.** The two-question same-worker goal remains open.

Owned process Jobs and stream collectors closed, as did the runtime's owned threads and database resources. Nevertheless, `browser_leg_passed`, `native_checked_completed`, and `leg_closed_after_advisory_unlock_connection_close_and_engine_dispose` are false. This is resource closure after a failed leg, not normal native PASS/CLOSED. See the [runtime closure](evidence/20261009-week10-continuous02/runtime-continuous02/runtime-closed-public01.json), [controller](evidence/20261009-week10-continuous02/continuous-preparation/ROOT_CONTINUOUS_CONTROLLER_ACTUAL02.json), and [final public budget](evidence/20261009-week10-continuous02/runtime-continuous02/budget-status-public01.json).

The frozen public source version is `42359d2d2cd2f8d28007173a20d20e994d5d767372acd597d5e3d495f552885f`. The evidence [index](evidence/20261009-week10-continuous02/index.json) records each original source path, bytes and SHA256, plus byte-identical public copies. It excludes auth, credentials, raw child logs, databases, model weights and the large source index. Preparing this report caused no Main writes, database connections, tests or API calls.

Root previously supplied an [existing Library evidence archive](https://chatgpt.com/api/library/files/libfile_3f052252ff808191abf55ac4b3efd56b/download): Library ID `libfile_3f052252ff808191abf55ac4b3efd56b`, file ID `file_0000000014a4820babffbe19963d5332`, version `0`, **154748 bytes**, SHA256 `ff2bb66e8fee9341a580ba3d461723ffd79a33d5f669dbcd495aaad25fe27f15`. Those supplied archive metadata refer to that earlier download, not a new upload of this report package.
