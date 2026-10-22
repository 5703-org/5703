# Candidate201 fixed new-question results — 15 October 2026

**The fixed experiment completed; the quality and usability target is not fully met.** Default OFF delivered four of five answers, all four within ten seconds. Independent review found only two of five both scientifically clean and complete within that time. ON delivered two of five and neither within ten seconds. Failures were preserved rather than repaired, retried or presented as success.

## Scope and source

Five original questions were frozen before any model answer: isotopes with an example; mitosis versus meiosis; three RNA roles; molarity with units and three significant figures; and explicit general knowledge about lunar phases without retrieval. Each mode used fresh sessions, profile off, no history and a fresh worker. The frozen reviewer rubric was never sent to generation or Checker. Native query preflight exposed an example-directive parser error before any provider request; the original setup stop is retained in phase200. Candidate201 fixes that grammar and the native zero-call fallback/guard compatibility. All five questions remain verbatim. These are fixed fresh inference observations, not a claim that the full pipeline remained unseen during engineering preflight.

The two measured cohorts used identical Candidate201 runtime source (483 pinned paths). Normal full retrieval cache was enabled, the index-only variant disabled, and public CPU model/release preparation completed before request measurement. No query was prefetched. Actual configured and returned model was `deepseek-flash` at the official DeepSeek endpoint. Working window 32768, GEN maximum 1024, CHECK reserve 4096 and saved non-thinking choice were unchanged. The prior 5.381-second result was not rerun.

## Observed delivery and scientific quality

| Question | OFF complete seconds | ON complete seconds | Observed limitation |
| --- | ---: | ---: | --- |
| N1 isotopes | 6.061 | 11.613 | Core definition/example correct; both bodies repeat the source's overbroad “chemically identical” claim. |
| N2 comparison | NULL | NULL | Both drafts rejected by `ASSERTION_COMPLETE_CLAIM_REQUIRED`; no published answer. |
| N3 RNA roles | 4.981 | NULL | OFF core roles complete, but an added codon statement omits the sense/stop distinction. ON Checker returned 9 evidence entries against maximum 8. |
| N4 molarity | 4.963 | NULL | OFF conversions and 0.200 mol/L at 3 significant figures correct. ON failed the derivation/body publication gate. |
| N5 lunar phases, no retrieval | 3.431 | 10.363 | Both correct and complete; native evidence/citations empty and retrieval/reranking absent. General-knowledge provenance remains unverified. |

| Fixed denominator | OFF | ON |
| --- | ---: | ---: |
| Core correct and complete delivery | 4/5 | 2/5 |
| Complete delivery within 10 seconds | 4/5 | 0/5 |
| Scientifically clean complete delivery | 2/5 | 1/5 |
| Scientifically clean complete delivery within 10 seconds | **2/5** | **0/5** |

“Core” means the explicit requested task was answered correctly and completely. “Scientifically clean” additionally excludes inaccurate extra absolute claims. The N1/N3 precision findings are limited-scope issues, not missing core answers. They were faithful to the selected textbook excerpts; citation faithfulness does not establish scientific truth. All four published textbook answers had actual evidence/fragment/citation bindings independently checked; the two explicit general-knowledge answers have citation support marked not applicable. No failed raw draft was counted as delivered or independently scored as a product answer. Q6's earlier source-review flags remain byte-identical and pending.

Browser complete time includes native publication, polling and stable full-body rendering, not first-token time. Failed answers retain NULL successful latency. Observed failure times were 5.515s/4.732s for N2 OFF/ON, 14.747s for N3 ON and 11.697s for N4 ON. Successful-only means (OFF 4.859s on 4 cases, ON 10.988s on 2) exclude failures and are not failure-aware service targets. The small sequential cohorts do not establish production p95 or a causal speedup.

## Checker work and stage evidence

The opt-in lossless assertion-table codec removes repeated proof/source metadata only when the complete local native-request count is strictly smaller. It preserves every assertion, selected source, fragment, schema and output reserve, with exact decode/hash controls. Native producer fallback keeps non-assertion calculation and general-knowledge routes on the prior encoding. Six separate historical CHECK packets showed local input estimates reduced 652–2005tokens (3.67–9.05%); those are not provider-exact savings or a randomized latency result. Prior CHECK responses were already compact JSON, so no unmeasured whitespace-output instruction was added.

Actual input/output token pairs in this round were: N1 ON GEN29151/346 and CHECK16354/1324; N3 ON GEN28460/536 and CHECK18127/2179; N4 ON GEN11858/249 and CHECK12842/1532; N5 ON GEN4886/373 and CHECK8904/1036. N2 never reached CHECK. Per-cell retrieval and physical transport durations are in the metrics JSON. CHECK is nested within generation wall time; nested durations must not be added twice. The ON result still has substantial delay and publication failures. No assertion, output gate or user's Checker choice was removed to improve the score.

## Calls, permission and lifecycle

OFF made 5 GEN/0 CHECK for conservative usage-based CNY0.220566. ON made 5 GEN/4 CHECK for CNY0.382396. Total: **14 physical requests, 10 GEN/4 CHECK, CNY0.602962, zero new protected UNKNOWN holds**. These are conservative usage estimates, not a provider invoice. The original maximum was 10 GEN/5 CHECK and CNY7.50 nontransferable stage holds under CNY8.00. The unused CHECK does not authorize another request. No retry, repair, probe, remote token count or evaluator model ran. Older UNKNOWN charges and the stopped 48-unit pilot remain untouched.

All three real launcher invocations used the original reviewed `phase192/runtime/launch192.py` through `exec_command(require_escalated)`. The platform allowed each to start. Phase200 stopped before any provider stage; corrected201 OFF/ON closed normally. There was no new tool or automatic-approval rejection of the user's DeepSeek authorization.

The local experiment fence separately blocked an import-time `urllib3.util.connection._has_ipv6("::1")` capability check at `sock.bind((host,0))`. The fresh201 diagnostic identifies loopback::1/port0; the older200 label alone does not prove its exact callsite. No rule was broadened. Both saved fence audits retain this denial/audit exception, so this is **not a clean-fence-audit claim**. Owned Windows Jobs closed with no unknown process, browser/worker/engines closed, isolated PostgreSQL containers stopped with volumes retained, and ports19231–19233 were free. Process/billing closure is separate from fence audit and scientific acceptance.

## Main, candidate and current verification

Main198's 481-path baseline matched, and the validated Candidate199 13-path index/citation delta was integrated first. After both201 cohorts closed, six additional product paths and five test/fixture paths were copied into Main with exact before backups. Fresh Main regression: **441/441 PASS in 5.41s**; frozen Candidate201 regression: 441/441 PASS in 4.73s. Native five-question preparation and 16 native zero-call guard controls also passed. Earlier collection/fixture failures and the setup stop remain available. No full backend/foundation/contracts/chat-scope/mock-all run is being relabelled as current verification.

**Main source is updated. No Main service was explicitly restarted or deployed; its currently loaded source version is unconfirmed.** Existing `.env`, saved model configuration, databases and keys were not changed. The final complete candidate contains source, pinned public corpus/model assets, setup entrypoint, tests, manifests and this report; it uses canonical product Markdown rather than the isolated timing observer. An actual independent `-VerifyOnly` entry validates the declared files, while the measured isolated runtime uses existing installed dependencies. Neither proves a clean-machine installation or another-PC acceptance.

The candidate remains experimental: comparison-claim validation, ON schema/derivation failures, textbook precision, checked latency, clean install and broader science/human acceptance remain open. Canonical task/check owners and null human approval states are unchanged; project completion is not claimed.

## Inspectable local evidence

- [Metrics and physical stage accounting](evidence/phase201/METRICS201.md), [metrics JSON](evidence/phase201/METRICS201.json).
- [Independent science/citation review](evidence/phase201/quality/REVIEW201.md), [full review and source flags](evidence/phase201/quality/REVIEW201.json).
- [Source integration and exact rollback identities](evidence/phase201/MAIN-INTEGRATION201.json).
- [Actual local network-boundary diagnosis](evidence/phase201/NETWORK-BOUNDARY-IDENTIFIED201.json).
- [Native grammar/programmatic verification](evidence/phase201/query-preparation/RESULT201.json).
- [Earlier zero-dispatch setup stop](phase200-pre-dispatch-stop-20261015.md).

Full private request captures and browser profiles remain local operational evidence and are excluded from the distributable. No real user data was used.
