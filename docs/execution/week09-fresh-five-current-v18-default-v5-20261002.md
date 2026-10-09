# Fresh current-V18 textbook answer pilot — 2 October 2026

Five exposed development cases used fresh CPU-requested E5 query preparation, real PostgreSQL/pgvector textbook records, BM25/RRF and learned CPU reranking. Generation and checking used the configured DeepSeek model `deepseek-flash`, default `typed_joint_v5`, query preparation `conversation_preparer_v18` and requirements V5. The current software gate binds all 818 source inputs. Ordinary textbook questions use complete supported explanations. Each request retained the existing four-call, 180-active-second and 3,000-evidence-token limits.

| Case | Final publication | Calls | Published citations | Preparation / generation / audit-inclusive seconds |
|---|---|---:|---:|---|
| Selected passage: sunlight and chemical energy | Answer | 2 | 3 | 12.412 / 30.487 / 42.899 |
| Catalyst: activation energy and free-energy difference | Answer | 4 | 4 | 5.413 / 65.565 / 70.978 |
| DNA/RNA: sugars, bases and usual strand structure | Answer | 4 | 3 | 6.036 / 68.987 / 75.023 |
| Simpler explanation of the sugar difference | `SEMANTIC_CHECK_FAILED` | 4 | 0 | 6.466 / 61.833 / 68.299 |
| Ideal gas law: kelvin and consistent units | `SEMANTIC_CHECK_FAILED` | 4 | 0 | 5.170 / 65.040 / 70.210 |

Three requests published answers and two failed the final semantic check. A failed draft's proposed citations do not count as published citations. The table records publication behavior; correctness, sufficient coverage and useful learning support require independent evaluation. The generation boundary includes local preservation guards, generation/check/repair activity and schema processing. The audit-inclusive boundary adds fresh preparation. These guarded development measurements do not estimate ordinary production response latency.

## Source traceability and method

The selected reading context came from the official *Concepts of Biology*, Chapter 5 / 5.1, physical PDF page 131, with a complete bounded source unit preserved. The catalyst candidates included *Concepts of Biology* 4.1 (pages 111–112), *Chemistry 2e* 12.7 (633–635) and *Biology 2e* 6.5 (194–195). DNA/RNA candidates included *Biology 2e* 3.5 (108–110), *Concepts of Biology* 2.3 (64–66) and *Anatomy and Physiology 2e* material including page 142. The gas candidates included *Chemistry 2e* 9.2 (436–438). These locations describe submitted candidates; citation-support labels remain separate. The allowlisted receipt records each actual submitted source location and keeps missing section metadata explicit.

Each input was freshly prepared against the existing real four-book corpus. Query encoding requested CPU; its execution record has no separate query-device trace. The learned reranker recorded CPU as its actual device. The followup used this run's newly published DNA/RNA parent pair with the explicit sugar comparison axis. Its parent is ephemeral within this direct-service runner. Persisted HTTP ownership, worker orchestration and installed cancellation are covered by their separate workflows. This pilot does not exercise the HTTP worker's supplemental retrieval orchestration.

## Failure and accounting record

The first attempt stopped before every provider call because the runner's raw retrieval rows did not satisfy the complete evidence transport schema. One interrupted and four unexecuted requests remain in that attempt's five-case denominator. After a transport-only correction, the second attempt executed all five requests. No product source was changed between these attempts.

The current sequence reserved, entered and completed 18 provider calls. All 18 decoded valid, nonempty replies; unknown server outcomes were zero. Recorded usage was 183,649 input tokens, 14,590 output tokens and 198,239 total tokens, including 61,184 cache-hit and 122,465 cache-miss input tokens. All 18 calls are unpriced: recorded monetary cost is unavailable, and no invoice reconciliation or dated tariff is bound. Missing cost does not imply a free call.

The before/after audit preserved source, the existing corpus, all 65 table identities, original inputs, environment and model configuration records. No database write, HTTP authentication action or historical internal draft input occurred in this pilot. Independent human ratings and independent quality scores remain zero. These five cases are exposed development cases, with no held-out score or causal comparison claimed.

Evidence: [allowlisted terminal and retained zero-call failure](../../evidence/week09-continuation/20261001/fresh-five-current-v18-default-v5-20261002-sanitized.json). Current private terminal SHA-256: `fdc27afefb857132511559cd2351faaabc3bdae498e103a9172fd9034205efa0`; first zero-call terminal SHA-256: `196d262eb84bc11bde93ae860dee5a99a7815ae9815f1c49d536b0b012d33513`. Current software gate SHA-256: `343ce4e457286fa48b7282b1cff002a3689ee6b60b2706336b601703e86961d8`.
