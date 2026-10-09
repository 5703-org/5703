# Week 8 Overall Report

CS-30-1 | Cumulative Week 8 delivery | 26 September 2026

## Current outcome

Week 8 now combines reliable question handling, CPU operation, precise source highlighting, editable learning memory and persistent teaching progress with checked learner feedback and reusable retrieval computation. Ordinary textbook questions receive a complete answer by default. Learners can select progressive hints or general-knowledge explanations explicitly.

This report covers all changes after the verified Week 7 final release of 13 September. The original four-book knowledge base, account and conversation services, model management and historical citations remain preserved. The eight original workstreams retain their ownership; Codex performed the recorded shared implementation and automated checks. Independent human scoring is assigned to the group.

## Development across Week 8

| Checkpoint | Integrated outcome |
| --- | --- |
| 16 September | Question understanding, evidence selection, source modes, CPU operation and diagnostics |
| 20 September | Exact citation highlighting, editable memory and persistent teaching controls |
| 21 and 22 September | Typed memory, conditioned reading, provider compatibility and cumulative delivery |
| 26 September | Checked procedural hints, general-knowledge assessment, pending tutor questions, cache reuse and CPU experiments |

## Teaching and checking

The v3 contract distinguishes procedural guidance, textbook scientific assertions, learner givens and explicitly selected general knowledge. Procedural hints receive an independent check. Scientific textbook statements need exact supporting sources. General-knowledge facts receive their own model assessment; textbook support is marked not applicable.

Each checked tutor question is bound to a task and revision. A learner response continues the original problem and help level. The checker evaluates the attempted answer and visible feedback. Explicit requests for a new problem or full explanation take priority. Proposed tutor questions are included in the visible draft before the claim and teaching checks, and source display remains subject to the cumulative disclosure allowance.

The earlier source-highlighting and memory modules remain integrated. Exact cited spans retain source identity and current visibility. Memory changes remain opt-in and editable, with current instructions and specific saved subject preferences applied in the recorded order.

## Retrieval and CPU results

The real PostgreSQL study pairs reference retrieval with cached release validation, exact BM25 computation and owner-scoped E5 query vectors. Both arms use the same official corpus and pinned MiniLM reranker. All 98 observations completed; all 48 warm pairs returned identical candidate and reranked content and scores. Four PDF hashes and database/vector fingerprints remained unchanged.

| Warm local stage | Reference | Validated cache |
| --- | --- | --- |
| Median retrieval plus reranking | 4,787.05 ms | 341.29 ms |
| p95 retrieval plus reranking | 5,235.96 ms | 455.14 ms |
| Median release validation | 3,870.05 ms | 3.28 ms |
| Median lexical retrieval | 443.38 ms | 9.15 ms |

The local p95 reduction is 91.31%. This interval covers retrieval and reranking; queueing, remote generation, checking, publication and browser display have separate timing. A transactional invalidation token, actual-hit validation and the publication fence remain active.

Across 24 real-corpus CPU cases, the original 16-thread PyTorch arm had a warm reranking p95 of 229.59 ms. Two-thread PyTorch measured 802.51 ms, ONNX FP32 521.83 ms and ONNX INT8 286.20 ms. FP32 preserved all 24 ordered top-five results. INT8 preserved 11 and crossed the provisional PyTorch cutoff five times. The original backend remains the default.

The adaptive development fit selected 20 candidates for every held-out case. Fixed budgets of five and ten retained the complete reference top-five in 1 of 12 and 5 of 12 held-out groups. The full budget retained it in all 12. Smaller budgets and ONNX remain explicit experimental options, with model-specific calibration and quality checks required for activation.

## Real model comparison and later fixes

The frozen 128-condition comparison published 92 outcomes and retained 36 failures. V2 published 51 of 64; v3 published 41 of 64. The comparison measures delivery under each policy. V2 lacks the typed learner-attempt contract, which is reported as a separate capability difference. The online checker forms part of the product and supplies no independent correctness label. All 45 frozen source files remain recoverable.

After the frozen comparison, the final successor added tutor-question omission checks, precheck question materialization and clearer feedback instructions. Its separate eight-case check published five outcomes. The three textbook failures involved excessive disclosure, conflicting claim classification or an invalid derivation schema. Four general-knowledge hint/attempt cases passed. The original 128 outcomes remain unchanged.

## Runtime and regression

The final complete software gate passed 936 Python tests and 87 frontend tests, with zero failures or skips. All eight stages passed, including static checks, negative controls, contracts, frontend types and build. The 523 executable/configuration file hashes stayed unchanged during the gate. A queue-timing regression exposed timezone-offset replacement; the final code preserves the offset and passes four equivalent-time tests. Original requirement IDs and historical records remain intact.

A new same-host Windows environment installed Python 3.13.2 and PyTorch 2.8.0+cpu with no CUDA runtime. A separate PostgreSQL 16.15/pgvector 0.8.6 database imported four books and 10,594 real vectors. The launcher, two real CPU retrieval/mock-answer turns, exact source checks, cancellation and history reload passed. Docker Desktop on the original installation remains blocked by an inaccessible IPC entry; its database and volumes are preserved. The package supports normal Docker startup and an explicit existing-database option.

The final teaching HTTP flow completed 16 requests: 13 published and three failed. All four first-hint/learner-attempt pairs published. A separate alternating-order cache comparison measured eight requests per arm; each arm published seven. HTTP median changed from 10.78 s to 6.58 s, while all-request p95 changed from 15.06 s to 15.92 s. The small study does not establish the registered p95 improvement target. All eight paired retrieval candidate and ranking lists matched.

The actual Chrome journey passed 12 checks and four screenshot inspections. The current tutor question remained readable and keyboard-focusable at desktop, 390 by 844 and 390 by 500 CSS pixels; reload retained the question and hint mode. General-knowledge assessment displayed textbook support as not applicable. One submit-to-pending-display observation was 4.88 s. Physical mobile keyboards, input methods and assistive technology need separate checks.

## Cost and failures

This continuation recorded 573 distinct provider calls and 3,369,750 total tokens, including the setup pilot, failed requests, model configuration probes and timing warmups. Input comprised 1,929,725 cache-hit and 1,240,664 cache-miss tokens; output comprised 199,361 tokens. At the official Saturday tariff checked on 26 September, the calculated estimate is CNY 2.07670. Actual account billing, credits and discounts were not observed. The cost receipt gives separate cohorts and the price-source URL.

The initial generation pilot failed strict evidence projection and was stopped with all records retained. The final HTTP teaching flow retained one citation-binding rejection after the checker changed its selected source set, and two provider responses consisting entirely of whitespace after bounded retries. The small timing comparison retained one semantic-check failure and one checker inconsistency. The timing recorder originally zeroed queue delay by overwriting a database timezone; corrected values are stored separately and the software fix has its own regression. A launcher-PID memory sample was excluded from inference-memory claims.

## Independent review and research limits

Independent human ratings remain blank. The 128-condition study provides randomized reviewer materials and a coordinator mapping. Reviewers assess correctness, support, useful task-specific guidance, permitted hint depth and cumulative leakage. The supplied import tools validate completed records. Automatic model checks and operational delivery counts are reported separately from human judgments.

The new live comparison covers eight concept families across four books, two answer modes, four teaching stages and two policy versions. Its successor repairs were developed after observing failures and have separate post-hoc evidence. The registered supported-answer noninferiority gate and the browser p95 target require their own sufficient independent measurements. Learning transfer and delayed independent performance remain future evaluation work.

## Delivery and Week 9 goals

The full runnable archive contains current public source, the verified official corpus and model resources, optional CPU graphs and all nine reports. The eight personal archives contain cumulative assigned changes from the Week 7 final release as complete files. Each personal report is byte-identical to its standalone copy. The manifests record ownership, baseline/current hashes and reconstruction. Private credentials, user histories and unblinded research records remain local.

Next week focuses on independent blind scoring, the remaining model/checker failures, a preregistered final-version comparison and physical deployment checks. CPU alternatives require broader quality evidence before activation. Diagram and formula coverage, assistive technology, input methods and delayed learning outcomes retain separate acceptance work.

## Evidence and methods

docs/execution/teaching-performance-protocol-20260926.md

docs/execution/teaching-performance-20260926.md

docs/execution/teaching-contract-review.md

evidence/teaching-performance/20260926/software-gate-final-02/software_gate.json

evidence/teaching-performance/20260926/pg-retrieval-paired-final/summary.json

evidence/teaching-performance/20260926/generation/live-contracts-128-results.json

evidence/teaching-performance/20260926/generation/live-contracts-posthoc-results.json

evidence/teaching-performance/20260926/live-http-final/failure-review.json

evidence/teaching-performance/20260926/http-timing-final/summary.json

evidence/teaching-performance/20260926/portable/runtime-verification.json

evidence/teaching-performance/20260926/cost-estimate.json

https://api-docs.deepseek.com/zh-cn/quick_start/pricing/
