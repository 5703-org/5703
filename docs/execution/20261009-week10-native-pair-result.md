# Actual Week10 native RAG and full-answer pair - 2026-10-09

Both normal native-worker and real-browser legs passed and closed. The same new follow-up, frozen synthetic learner context, active corpus, default R2 retrieval, model route and initial generator payload were used. Baseline Send-to-complete-answer display was **18.7143 seconds**; startup prewarm was **12.1465 seconds**. Four actual OpenRouter POSTs completed at known cost **USD 0.01936904**, with zero new UNKNOWN or open claims. This is one observed diagnostic pair, not whole-project or scientific acceptance.

## Actual conditions and quality comparison

The first stored exchange was verified by normal login and read-only browser resume; it was not regenerated or billed. The measured new question was `Why is light necessary for this process?`. Two owned PostgreSQL synthetic clones started from the same profile, history, memory and stored first answer. No production learner/database or protected staging data was used.

Both legs used `google/gemini-3.5-flash-lite` through OpenRouter with the fixed `google-vertex/global` route, existing normal answer/checker qualifications, a full checker and normal publication gates. The public default R2 hybrid profile, E5-small-v2 embedding revision, MiniLM reranker revision, four CPU threads and CUDA execution matched. Both local model instances were warmed with the same separate authored query. Neither measured query-vector cache was prepopulated. Only the worker release-cache startup flag was false for A and true for B; its product default remains false.

The complete initial teacher wire was identical: 41,988 bytes, SHA256 `62d38f263f4abc86d6d6f2d10269a76704e2d6d0f8101f4b580e3caec380a563`. Ordered evidence, history, profile, summary, question, resolved query, controls and schemas matched. All 20 candidate IDs, submitted candidate IDs and reranked IDs matched in order. The native R2/MiniLM CUDA trace proves execution beyond configuration binding.

| Observed operational quality gate | A baseline | B startup prewarm |
|---|---|---|
| Normal native checked publication / terminal job | Passed / succeeded | Passed / succeeded |
| Completed cited answer displayed | Passed | Passed |
| Citation source opened | Passed | Passed |
| Refresh retained the same published answer | Passed | Passed |
| Browser/context and worker/database resources closed | Passed | Passed |
| Independent semantic, scientific or learning quality | Not assessed | Not assessed |

Both new answers required one teacher and one full-checker POST; no repair, provider retry or replacement question occurred. Checker controls/schema/evidence matched, while its complete payload differed because the generated candidates differed (42,519 versus 43,214 bytes). Candidate differences are preserved in the evidence. Operational publication success does not establish semantic equivalence, superiority or statistical noninferiority.

## Time boundaries

| Observed interval | A baseline | B startup prewarm |
|---|---:|---:|
| Root process launch to worker ready | 8.4283 s | 14.0966 s |
| Startup release-cache preparation | 0.000004 s | 5.7602 s |
| Measured release-cache validation | 5.8996 s, miss | 0.0036 s, hit |
| Worker retrieval including rerank | 6.1982 s | 0.2202 s |
| Send to first visible answer | 18.6477 s | 12.1465 s |
| Send to complete cited-answer DOM | 18.7143 s | 12.1465 s |
| Root process launch to complete-answer DOM | 30.2040 s | 29.4479 s |

The observed Send interval decreased 6.5678 seconds (35.10%), while launch-to-completion decreased only 0.7562 seconds (2.50%). B performed its release validation at startup before Send; that cost remains part of the user journey. Provider/model and OS variation remain uncontrolled, so the whole difference is not attributed solely to cache. UI timings include normal HTTP admission, queueing, worker execution, persistence, polling and sampled paint. This UI does not stream tokens: first visible prose is not provider TTFT.

The pair is n=1, fixed A then B, with no OS pagecache reset or randomized order. No p95, SLA, cold-install performance, held-out benchmark accuracy, quality noninferiority or formal >=30% warm-p95 acceptance is claimed. Historical failed setup runs and historical original-first timing remain unchanged; the resumed first answer has no fabricated fresh Send time.

## Actual cost and closure

| Leg / role | Physical POST | Known cost USD |
|---|---:|---:|
| A teacher | 1 | 0.00657690 |
| A checker | 1 | 0.00427900 |
| B teacher | 1 | 0.00305234 |
| B checker | 1 | 0.00546080 |
| Total | 4 | 0.01936904 |

All four returned HTTP 200 and known cost, with zero new UNKNOWN, open claims, integrity errors or pending cleanup. All four owned runtime/browser processes exited zero, their Windows Jobs closed and output collectors completed. The success STOP has reason `ROOT_NATIVE_PAIR_COMPLETED`: this finite paired batch is closed; unused slots are not automatically reused. Runtime budget snapshots were written before that success STOP and are cumulative, so A and B snapshot totals must not be added. The approved ceiling was eight physical POSTs and USD 0.24. All old STOPs, fourteen old UNKNOWN records and full protections remain preserved; no account balance or invoice total is inferred. The [final financial result](evidence/20261009-week10-native-pair01/ACTUAL_SIXTH_NEW_CLAIM_FINANCIAL_RESULT01.json) records the closure explicitly.

## Local repairs and retained scope

The authored fixture's `.test` email was rejected by the unchanged normal EmailStr login schema (HTTP 422). Only each already-owned learner's email was updated by a one-row compare-and-set to a valid `.com` address, keeping its ID, password, profile, history and memory. The real login/me precheck then passed HTTP 200 without model loading or retrieval-cache work. No production authentication rule was relaxed and no new persistent credential was created.

The browser harness now accepts the versioned owned private-auth fixture name and records the HTTP DTO response digest separately from the stored raw JSON digest. It retains exact answer-text and identity checks; the native runtime separately verifies raw stored response/history. The prior cross-representation hash equality was an unnecessary harness prerequisite. Zero-call setup failures remain retained and are not counted as actual model results. No new full test-suite run is claimed: the unchanged adopted prewarm delta retains its actual 48 affected free tests and Ruff checks.

Current source verification confirms `generation/compact_findings_v3.py` (37,169 bytes, SHA256 `1aba7601543d2b08c5331a0e139726191e13948a7dd6343eb7292262e1e2de8a`) has the per-requirement `span_ids` limit8 at line91 and matching prompt wording at line400. That limit already exists in the preserved pre-adoption backup (36,733 bytes, SHA256 `d1a67c3c74a3989de4001ac9d89c04b8d98282e2ac14b0fee5bff7d2b1487b87`); the [reviewed three-file adoption](evidence/20261008-checker-rag-native/current-three-file-adoption.json), timestamp2026-10-07T17:44:03.1244668Z, did not newly introduce or relax that schema cap. Its field/reasoning wording changes preceded the frozen pair. The existing grouped-prompt/schema boundary test remains present; no fresh test run is claimed.

Both actual A/B legs used the same qualified complete V5 route, with checker schema SHA256 `7988037e08d52662a1b232f049776a42b6d10ad5d896f1a26c8c912b3efd79d4` and controls SHA256 `9106c8c5dfd60ef22fdae09f3bb25db67e4bd6fb6cfbdf7eccea249b89960eff`. Its frozen public schema source, `generation/reliability_v5.py` (8,366 bytes, SHA256 `7260e47e6b51e45834f660f5d0fabb3c142b760f40a6c791fff733c08fd1261d`), limits each requirement to eight evidence entries at line74 and the response to eight requirements at line84. This is not a limit of eight total retrieved candidates or all source alternatives; all20 candidates/ranked IDs remained matched in the observed pair.

There was no checker-code, active configuration, schema, flag or verdict-rule change between the two legs. The compact candidate was not activated or live-qualified by this pair. Source presence is not proof of an active compact route; no independent claim about active prompt version42 content is made from these public receipts. Normal strict checker/publication quality decisions remain in force; no independent scientific quality judgment was replaced or relaxed.

## Evidence and remaining acceptance

[Observed analysis](evidence/20261009-week10-native-pair01/ACTUAL_WEEK10_PAIR_OBSERVED_ANALYSIS01.json), [controller](evidence/20261009-week10-native-pair01/ROOT_NATIVE_PAIR_CONTROLLER_ACTUAL06.json), [A browser](evidence/20261009-week10-native-pair01/browser-A_baseline-repair06/real-browser-live-qa-receipt01.json), [B browser](evidence/20261009-week10-native-pair01/browser-B_startup_prewarm-repair06/real-browser-live-qa-receipt01.json) and the local [evidence index](evidence/20261009-week10-native-pair01/index.json) contain exact source hashes and measured public receipts. Authentication files, raw provider headers/wires, keys, database dumps and private source data are excluded.

The tested source-index SHA256 is `26afaa44371533d9a77f0e8aa8a51570c6027011e1d0e9d01c60c3562edd3adb`; result documents are later additions, not part of that frozen execution source. This result supersedes the earlier prepared-only budget paragraph in the [prewarm adoption report](20261009-week10-worker-cache-prewarm.md). Current engineering-row counts remain 5 verified, 38 pending verification, 8 incomplete and 2 external; `project_complete=false`. Formal independent quality, the complete multi-module scientific acceptance, human/device conditions and the warm-p95 study remain open. Week09 archives/reports and all experimental inputs/results remain immutable. No remote push, deployment or course submission occurred.
