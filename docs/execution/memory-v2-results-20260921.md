# Memory V2 terminal results and limitations

This record reports the registered 21 September 2026 A/B/C/T/M study and the 22 September local delivery reconciliation. It preserves all planned outcomes and separates automatic judgments from independent human review. The product still defaults to complete textbook-grounded explanations; hint-only study conditions do not change that default.

## Evidence and scope

[Public results](../../evidence/week08-memory-v2/20260921/formal/public-results.json), [timings](../../evidence/week08-memory-v2/20260921/formal/public-latencies.json), [retained-attempt costs](../../evidence/week08-memory-v2/20260921/accounting/final.json) and [independent numerical reconciliation](../../evidence/week08-memory-v2/20260921/formal/numerical-review.json) are the source records. The reconciliation is a second-agent calculation/source audit; it supplies no human scientific ratings. The [protocol](week08-memory-v2-protocol-20260921.md) and three pre-formal amendments define the contrasts. The canonical study hash is `e5cdb78d332e8035422af20f718899cfff95fc0877ce04e6abdcd9f81cc31bcb`.

The 552 planned requests cover A=72, B=72, C=48, T=180 and M=180 across 18 arms. All generation and judgment receipts are terminal. Generation retains 346 answers, five clarifications, 177 failures and 24 human-dependent A2 waits. Offline judging retains 329 valid answer judgments, 22 judge-schema failures and 201 no-delivered-response records. Independent human ratings and A2 oracle confirmations are zero. The small authored families and same-family automatic judge limit generalisation.

## Every planned arm

A0 uses no retrieval, A1 current retrieval and A2 human-confirmed oracle evidence. B0 is schema-valid basic generation, B1 the frozen legacy checked pipeline and B2 the revised pipeline. C1 uses legacy generation-context selection under the same 3,000-token evidence cap; C2 uses generic answer repair under the same v2 source, semantic-support, derivation and citation gates; checker-contract inconsistency handling remains unchanged. T0 has no online disclosure check. T1 checks the body and short answer. T2 also checks follow-up suggestions, current source display and prior exposure; T3 checks those current surfaces without prior exposure. T4 checks the body, short answer, suggestions and prior exposure, while its current source display remains uncontrolled. M0 has no long-term memory, M1 rolling summary, M2 the legacy structured writer/reader, M3 typed state with the unconditioned reader and M4 the same writer with the query-conditioned reader.

“Success” below is the registered conservative all-planned composite. A failed, unjudged or externally waiting item cannot become a success. It is not an independent accuracy or learning-gain score. “Judged answers” makes the quality denominator explicit; clarifications and failures remain visible separately.

| Arm | Planned | Answers | Judged answers | Successes | Failures | Clarifications | External waits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A0 | 24 | 24 | 24 | 24 | 0 | 0 | 0 |
| A1 | 24 | 19 | 2 | 2 | 5 | 0 | 0 |
| A2 | 24 | 0 | 0 | 0 | 0 | 0 | 24 |
| B0 | 24 | 23 | 23 | 22 | 0 | 1 | 0 |
| B1 | 24 | 7 | 7 | 7 | 16 | 1 | 0 |
| B2 | 24 | 13 | 13 | 13 | 10 | 1 | 0 |
| C1 | 24 | 6 | 6 | 6 | 17 | 1 | 0 |
| C2 | 24 | 16 | 16 | 16 | 7 | 1 | 0 |
| T0 | 36 | 36 | 36 | 30 | 0 | 0 | 0 |
| T1 | 36 | 26 | 26 | 25 | 10 | 0 | 0 |
| T2 | 36 | 19 | 19 | 19 | 17 | 0 | 0 |
| T3 | 36 | 24 | 24 | 23 | 12 | 0 | 0 |
| T4 | 36 | 25 | 25 | 25 | 11 | 0 | 0 |
| M0 | 36 | 19 | 19 | 14 | 17 | 0 | 0 |
| M1 | 36 | 20 | 20 | 17 | 16 | 0 | 0 |
| M2 | 36 | 24 | 24 | 18 | 12 | 0 | 0 |
| M3 | 36 | 23 | 23 | 21 | 13 | 0 | 0 |
| M4 | 36 | 22 | 22 | 20 | 14 | 0 | 0 |

## Judged scientific dimensions

Cells are positive/applicable judgments among judged answers. A dash means the dimension is inapplicable or has no judged answer; it is not a zero score. These conditional rates exclude unjudged answers, so the planned-outcome table must be read alongside them. The public JSON also retains citation mapping/support, teaching usefulness/disclosure and all memory dimensions with their exact denominators.

| Arm | Factual correctness | Required coverage | Conditions and units | Source support |
| --- | ---: | ---: | ---: | ---: |
| A0 | 24/24 | 24/24 | 24/24 | — |
| A1 | 2/2 | 2/2 | 2/2 | — |
| A2 | — | — | — | — |
| B0 | 23/23 | 23/23 | 23/23 | 23/23 |
| B1 | 7/7 | 7/7 | 7/7 | 7/7 |
| B2 | 13/13 | 13/13 | 13/13 | 13/13 |
| C1 | 6/6 | 6/6 | 6/6 | 6/6 |
| C2 | 16/16 | 16/16 | 16/16 | 16/16 |
| T0 | 36/36 | 34/36 | 36/36 | 36/36 |
| T1 | 26/26 | 26/26 | 26/26 | 26/26 |
| T2 | 19/19 | 19/19 | 19/19 | 19/19 |
| T3 | 24/24 | 23/24 | 24/24 | 24/24 |
| T4 | 25/25 | 25/25 | 25/25 | 25/25 |
| M0 | 19/19 | 19/19 | 19/19 | 19/19 |
| M1 | 20/20 | 20/20 | 20/20 | 20/20 |
| M2 | 24/24 | 24/24 | 24/24 | 24/24 |
| M3 | 23/23 | 23/23 | 23/23 | 23/23 |
| M4 | 22/22 | 22/22 | 22/22 | 22/22 |

## Registered paired contrasts

| Contrast | Successes | Difference in percentage points | 95% paired interval | Paired families |
| --- | --- | ---: | --- | ---: |
| B2 − B1 | 13/24 versus 7/24 | +25.00 | [+0.00, +50.00] | 24 |
| T2 − T1 | 19/36 versus 25/36 | -16.67 | [-36.11, +2.78] | 12 |
| M4 − M3 | 20/36 versus 21/36 | -2.78 | [-13.89, +8.33] | 12 |

The intervals use 10,000 paired equal-weight family bootstrap resamples with seed 20260921. All three include zero. B is a combined pipeline comparison; its positive point estimate does not isolate one implementation feature, and B0 remains higher at 22/24 versus B2 13/24. T2 and M4 have negative primary point differences. C1/C2 are diagnostic ablations. No significant overall improvement or learning benefit is established.

## Failures and A1 judgment coverage

The 177 generation failures consist of 91 semantic-check failures, 65 checker-contract failures, eight context-limit failures, seven missing-citation failures, five supplied-answer-contract failures and one truncated response. These are retained automatic contract/publication outcomes, not 177 confirmed scientific errors. The 22 offline judgment failures are a separate stage.

A1 delivers 19/24 answers, but only 2/19 receive valid judgments; 17 are `JUDGE_SCHEMA_INVALID`. [The applicability observation](../../evidence/week08-memory-v2/20260921/formal/judge-applicability-observation.json) records two inspected failures where source support was scored instead of null as required by the A policy, including their bounded repair attempts. The sample does not prove the cause of all 17. The resulting 2/2 conditional scores cannot establish general A1 accuracy or a confident A comparison. No post hoc salvage, rejudging or outcome-based retuning changed these records.

## Learning-memory diagnostics

Separate from the 180 memory-answer requests, all 24 extraction outputs are valid and retain source-substring support; 16/24 exactly match the authored operation sets. Operation-tuple precision and recall are each 14/22 (63.64%), with eight false positives and eight false negatives. Those operation checks are not semantic memory-selection precision.

All 12 observation-gating pairs match the authored expectations: three admitted and nine rejected. The disabled-gate comparator exposes 12 candidates without persistence or model calls. This does not confirm learner mastery. M3 selects 22/26 required labels and seven explicitly excluded labels; M4 selects 21/26 required labels and two excluded labels. Both retain all 36 probe records. Required-label recall is partial selected-field recall; semantic selection precision remains null.

## Measured usage and latency

All 1,919 retained attempt records are included: 1,792 formal answer/check/repair and offline-judge attempts plus 127 development, preparation, extraction, summary, provider-diagnostic and authored HTTP attempts. There are 1,799 explicit submitted flags and 120 unknown submitted flags; the latter do not imply missing measured usage. Input/output usage is complete for these retained records: 13,282,080 input tokens and 912,290 output tokens, total 14,194,370. Cache-hit input is 7,771,774 and cache-miss input 5,510,306. Reasoning-token usage is incomplete. Fourteen attempt timestamps are explicitly proxy times.

The dated DeepSeek tariff estimate is CNY 9.31490148. All retained attempts have priceable usage and there are no unfinished accounting records; this remains an estimate without invoice reconciliation. Purpose subtotals partition this total and must not be added to it again. No OpenAI diagnostic call is included or claimed.

Of 552 planned request intervals, 528 are measured and 24 A2 waits have no execution interval. Median/p95 wall time is 6.32/13.74 seconds across measured requests, 5.05/11.68 seconds for 351 delivered responses (answers plus clarifications), and 11.10/15.67 seconds for 177 failures. Answer execution includes online checking/repair and immediate source/outcome validation; it excludes frozen retrieval preparation, memory writing/summary preparation, HTTP queueing and offline judging. The 1,342 online attempt latencies have median 2,534.5 ms; 450 offline-judge attempts have median 2,362.5 ms. Shared-host load and these boundaries prevent interpreting them as a production SLA or controlled speed comparison.

## Software, review and delivery boundaries

[The final release gate](../../evidence/week08-memory-v2/20260921/software-gate-release-final-20260922/software_gate.json) passes 828 Python/86 frontend checks, all eight stages, zero skips and unchanged hashes for 487 source/configuration files. It includes the earlier public-fixture successor (five changed tests and two new helpers) and the later release-only packager/resource regression correction. The original 485-file experiment and four protocol documents are exact in the [verified separate private archive](../../evidence/week08-memory-v2/20260921/formal/research-bundle-verification.json). No application/evaluator behavior changed after the formal freeze.

[Portable parity](../../evidence/week08-memory-v2/20260921/portable/source-parity-release-final-20260922.json) verifies 514 public source/configuration files and all 80 runtime resources. It supplements the earlier actual fresh Windows CPU install, HTTP and browser checks; it does not claim another fresh machine or Mac execution. [The final host check](../../evidence/week08-memory-v2/20260921/runtime-final-01.json) retains the original 10,594-vector/384-dimensional corpus fingerprints and healthy API/frontend.

[Two randomized review forms](../../evidence/week08-memory-v2/20260921/formal/review-export-verification.json) each contain all 552 rows with blank ratings. Independent scientific, evidence, pedagogy, learner benefit and physical-device acceptance remain open. All nine English reports and their Markdown copies are present; [visual verification](../../evidence/week08-memory-v2/20260921/reports-release-final/visual-verification.json) passed all 45 rendered pages and exact project/delivery copy equality. Archive hashes and reconstruction are recorded in adjacent release sidecars.

The [retained packaging failure and bounded correction](../../evidence/week08-memory-v2/20260921/packaging/release-fix-verification.json) record a reconstruction mismatch for the verified `resources/official-corpus/corpus.jsonl.gz` asset. The exact resource-path exception preserves its required category, size and hash checks; other archive paths remain excluded. The first nine ZIPs are retained as failed artifacts. Five focused checks and the final full gate passed after changing only the packager and its existing regression test. Scientific outputs, study code and the private research archive are unchanged. New archive hashes and reconstruction are recorded in adjacent release sidecars.
