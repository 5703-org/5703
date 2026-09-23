# Week 8 Memory and Answer Reliability Report

CS 30 1 | Week 8 | 2026-09-22

## Project outcome

Week 8 integrates exact citation highlighting, editable learning memory and teaching progress constraints in the learning assistant. Ordinary textbook questions receive complete direct answers by default. Learners can explicitly ask for a hint, inspect a cited passage, and manage the preferences used for their next answer.

The final integrated checkpoint passed 828 Python tests, 86 frontend tests and all eight verification stages with zero skips. The public portable tree passed the same checks. Actual browser workflows covered memory management, source inspection and model activation on isolated data.

A fresh Windows CPU environment used the existing four-book corpus, real E5 encoding, reranking and pgvector. It completed two persisted chat turns, cancellation and history with explicitly mock answers. Final parity covers 514 public source/configuration files and 80 resources. Main services are available and the original 10594-vector corpus fingerprint is preserved.

The registered numerical report accounts for all 552 requests across 18 arms: 346 answers, 0 refusals, 5 clarifications, 177 failures, 0 recorded non-executions and 24 waiting for human oracle evidence. Automatic results and missing prerequisites remain distinct from human acceptance.

B2 minus B1: +25.00 percentage points (95% paired cluster interval +0.00 to +50.00); positive observed difference. Conservative successes 13/24 versus 7/24; 24 paired families/trajectories. T2 minus T1: -16.67 percentage points (95% paired cluster interval -36.11 to +2.78); negative observed difference. Conservative successes 19/36 versus 25/36; 12 paired families/trajectories. M4 minus M3: -2.78 percentage points (95% paired cluster interval -13.89 to +8.33); negative observed difference. Conservative successes 20/36 versus 21/36; 12 paired families/trajectories.

The positive B estimate has a 95% interval touching zero. Teaching and memory selection comparisons have negative point estimates with intervals spanning zero. These results guide the next repairs; an improvement in student learning requires separate student observations.

## Implemented workflow

Each claim can open its saved source fragment with exact highlighted text and original locator. Explicit hint tasks preserve their progress across turns and check the allowed information in both answer text and source display. A request for the full explanation changes that allowance. Full-source access is an explicit recorded action.

Memory entries now have stable field identities, typed categories, subject or global scope, source attribution, verification, revision and expiry. The categories cover preferences, learning goals, course context, self-reported observations and individual assessment performance. Exact-text or numeric assessment scoring retains the original question, response and rubric identity; a single result describes that assessment.

The effective preference order is current instruction, relevant subject preference, global profile setting, global memory preference and evidence-gated observations. Recognised current corrections are applied before the answer snapshot is frozen. Event sequences and erasure fences prevent older asynchronous extraction from replacing a newer correction or restoring deleted content. The selected state uses the configured token counter and a 768-token ceiling.

The Memory screen presents summary, source, scope, revision, verification and processing status. A question preview shows selected fields and exclusion reasons without generating an answer. Learners can correct, expire, delete or disable memory. Profile-off suppresses it for the current turn. Version conflicts and failed processing remain visible, and signing out removes the rendered private state.

Models now separates capability declarations, immutable configuration saves, role-specific compatibility tests and activation. Basic generation, structured output and the project contract have separate receipts. Activation requires current answer and checker project results with matching configuration, prompt and schema identities. Safe diagnostics identify connection, protocol and validation failures without returning credentials or raw private checker commentary.

The reliability path retains exact source identities while preserving bounded local context, complete conditions and machine-checkable arithmetic. Typed support distinguishes textbook evidence, exact learner-provided givens and conditional calculation. Cause-specific repair operates within the shared call and time ceiling. Historical requests retain their versioned policy, and semantic support remains separate from exact-span integrity.

## Experimental method

The preserved 20 September release remains the comparison baseline. This iteration adds the memory migration d9e53f6b012a followed by provider migration e0a64c7d123b. The migration proof found no change to existing-column contents across all 44 prior tables. The four official OpenStax books and active 10594-vector release retain their source identities.

The initial DeepSeek answer suite passed while the initial checker suite failed. A later checker project receipt passed after the authored compatibility probe communicated the production arithmetic grammar. The strict validator and saved model configuration remained in force; the paired activation record identifies the exact successful receipts.

The formal generation and judge checkpoint preserves 485 executable/configuration files and four protocols in the verified private archive. After archiving, five test modules were changed and two independent test helpers were added so public software checks can run without private research catalogues. Production and evaluator engine bytes remain identical to the formal checkpoint. The final public tree contains 514 selected source/configuration files.

Final archive reconstruction identified one packaging rule error: the verified official corpus.jsonl.gz resource was present in the full archive but excluded from the virtual baseline. The release utility now retains that exact resource, and its existing ZIP round-trip check uses a gzip corpus fixture. Other archives remain excluded. A fresh full software gate and source/resource parity passed after this release-only correction; the scientific generator, checker and evaluator engine remain unchanged.

Software tests, browser interaction, provider compatibility, state selection and scientific answer quality answer different questions. Test counts are reported at their recorded checkpoint. Focused suites overlap the full gate and are not added to it as independent observations.

The registered A/B/C/T/M design fixes matched questions, evidence, model/configuration identities and condition order before formal execution. M3 and M4 share the typed writer and evidence rules so their comparison concerns reader selection. Private expected fields, source-sufficiency labels and reviewer keys stay outside generation requests and public runtime packages.

Actual browser observations use authored records in separate local databases and inspect 1440- and 390-pixel viewports. The CPU installation used the existing Windows host and cached downloads where available. Human ratings, physical device tests, campus-network observations and broader learning effects have separate collection requirements.

An unchanged public-tree rerun exposed 42 fixture dependencies: 24 SciQ-related tests, 17 private question-catalogue tests and one private memory-catalogue test. The preserved correction uses four newly authored software records plus synthetic 24-question and 12-trajectory protocol shapes. Every existing assertion and test identity was retained. These are software checks with zero external provider calls.

Primary differences are left minus right: B2−B1, T2−T1 and M4−M3. All repeated turns remain within their family/trajectory; intervals use the frozen 10,000-resample paired cluster bootstrap. Positive, negative and zero differences are reported with the same rule.

The answer model and automatic checker use the saved DeepSeek Flash configuration. Temperature is zero, the context reservation is 16384 tokens, answer output is 1024 tokens and checker output is 4096 tokens. Token counting uses deepseek-ai/DeepSeek-V4-Flash-0731 at revision 7872f01b1d1fe23eabc4c98b48bffcef5a386062. The provider model name remains an alias, so this local tokenizer identity does not certify a permanent remote model revision.

Study A compares A0 without retrieval, A1 with the frozen current retrieval, and A2 with human-confirmed sufficient evidence. All arms permit model background knowledge. Each arm schedules 24 questions. A2 remains waiting for actual source-sufficiency confirmation.

Study B compares B0 basic generation, B1 the previous complete checking pipeline and B2 the repaired pipeline on 24 matched questions per arm. C1 uses legacy generation-context selection under the same 3000-token evidence cap; C2 uses generic answer repair with the same strict source, arithmetic and citation gates. Each C arm has 24 questions and is an exploratory ablation.

Study T uses 12 teaching tasks with three turns each. T0 disables hint checking; T1 checks the answer body and short answer; T2 checks body, current source display and cumulative prior exposure; T3 checks body and current source display; T4 checks body and cumulative prior exposure. T2, T3 and T4 also check follow-up suggestions. The registered primary comparison is T2 minus T1.

Study M uses 12 authored learner trajectories with three probes each. M0 has no long-term memory; M1 uses rolling summary; M2 preserves the prior structured writer and reader; M3 uses typed memory with an unconditioned reader; M4 uses the same writer with question-conditioned selection. M4 minus M3 is the primary memory comparison.

The three primary comparisons use 10000 paired cluster bootstrap samples with seed 20260921. Question families and complete teaching or memory trajectories are the resampling units. Failed, unjudged and externally waiting records remain unsuccessful in the conservative composite; they retain their own error and missingness categories.

## Automatic results

### Study A Supplied Information Diagnosis

Phase: formal. Planned 72; accounted 72; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| answer | 43 |
| failed | 5 |
| waiting external | 24 |

All 72 scheduled A outcomes are accounted for, including explicit waiting, refusal, failure and recorded non-execution states.

A permits model background knowledge. The human-confirmed oracle arm remains visibly scheduled when sufficient-evidence confirmation is unavailable; retrieved evidence is not treated as a human oracle.

A1 automatic factual scores cover only 2 of 19 delivered answers. Seventeen judgments failed the applicability contract; both inspected examples supplied a score for a field that required null. This limited coverage prevents a reliable A0 versus A1 quality conclusion. The 17 failures remain unjudged.

| Metric | Result |
| --- | --- |
| A0 delivery and end-to-end outcome | Answered 24/24 (100.0%); judged answers 24/24; conservative successes 24/24. |
| A0 automatic applicable-answer dimensions | factual correctness 24/24 (100.0%); source support 0/0 (not applicable); required coverage 24/24 (100.0%); conditions/units 24/24 (100.0%); citation support 0/0 (not applicable); citation mapping 0/0 (not applicable) |
| A1 delivery and end-to-end outcome | Answered 19/24 (79.2%); judged answers 2/19; conservative successes 2/24. |
| A1 automatic applicable-answer dimensions | factual correctness 2/2 (100.0%); source support 0/0 (not applicable); required coverage 2/2 (100.0%); conditions/units 2/2 (100.0%); citation support 0/0 (not applicable); citation mapping 0/0 (not applicable) |
| A2 delivery and end-to-end outcome | Answered 0/24 (0.0%); judged answers 0/0; conservative successes 0/24. |
| A2 automatic applicable-answer dimensions | factual correctness 0/0 (not applicable); source support 0/0 (not applicable); required coverage 0/0 (not applicable); conditions/units 0/0 (not applicable); citation support 0/0 (not applicable); citation mapping 0/0 (not applicable) |
| Measured request duration | A0: median 3.058 s, p95 5.393 s, observed 24/24; A1: median 3.343 s, p95 5.052 s, observed 24/24. |

All planned arm requests remain in the delivery/composite denominator. Failed, refused and unjudged outcomes are not fabricated factual-error ratings.

Each fraction uses only applicable automatic judgments among judged answers; denominators can differ. Flagged memory dimensions count adverse observations, so lower is better. These are model ratings, not human grades.

Runner duration includes online generation, checking and repair. Frozen retrieval preparation, memory preparation, offline judging and HTTP queue time are outside this measure.

Limit: Automatic judgments can share the generator's model-family errors. Independent human ratings remain absent; the small authored study does not establish population-wide educational benefit.

Evidence IDs: formal_results, judge_scope, latencies.

### Study B Textbook Reliability

Phase: formal. Planned 72; accounted 72; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| answer | 43 |
| clarification | 3 |
| failed | 26 |

All 72 scheduled B outcomes are accounted for, including explicit waiting, refusal, failure and recorded non-execution states.

B2 minus B1: +25.00 percentage points (95% paired cluster interval +0.00 to +50.00); positive observed difference. Conservative successes 13/24 versus 7/24; 24 paired families/trajectories.

B2 versus B1 is the registered combined reliability-pipeline comparison; it does not isolate one repair, checker or context feature.

The basic B0 diagnostic delivered 23 answers and 22 conservative successes out of 24. The repaired checked B2 pipeline delivered 13 answers and 13 conservative successes. Reviewing rejected drafts and checker decisions is therefore a priority for answer availability. B0 remains an evaluation condition; the product retains its registered publication checks.

| Metric | Result |
| --- | --- |
| B0 delivery and end-to-end outcome | Answered 23/24 (95.8%); judged answers 23/23; conservative successes 22/24. |
| B0 automatic applicable-answer dimensions | factual correctness 23/23 (100.0%); source support 23/23 (100.0%); required coverage 23/23 (100.0%); conditions/units 23/23 (100.0%); citation support 22/23 (95.7%); citation mapping 22/23 (95.7%) |
| B1 delivery and end-to-end outcome | Answered 7/24 (29.2%); judged answers 7/7; conservative successes 7/24. |
| B1 automatic applicable-answer dimensions | factual correctness 7/7 (100.0%); source support 7/7 (100.0%); required coverage 7/7 (100.0%); conditions/units 7/7 (100.0%); citation support 7/7 (100.0%); citation mapping 7/7 (100.0%) |
| B2 delivery and end-to-end outcome | Answered 13/24 (54.2%); judged answers 13/13; conservative successes 13/24. |
| B2 automatic applicable-answer dimensions | factual correctness 13/13 (100.0%); source support 13/13 (100.0%); required coverage 13/13 (100.0%); conditions/units 13/13 (100.0%); citation support 13/13 (100.0%); citation mapping 13/13 (100.0%) |
| Measured request duration | B0: median 2.429 s, p95 3.596 s, observed 24/24; B1: median 11.424 s, p95 15.088 s, observed 24/24; B2: median 9.045 s, p95 16.530 s, observed 24/24. |

All planned arm requests remain in the delivery/composite denominator. Failed, refused and unjudged outcomes are not fabricated factual-error ratings.

Each fraction uses only applicable automatic judgments among judged answers; denominators can differ. Flagged memory dimensions count adverse observations, so lower is better. These are model ratings, not human grades.

Runner duration includes online generation, checking and repair. Frozen retrieval preparation, memory preparation, offline judging and HTTP queue time are outside this measure.

Limit: Automatic judgments can share the generator's model-family errors. Independent human ratings remain absent; the small authored study does not establish population-wide educational benefit.

Evidence IDs: formal_results, latencies.

### Study C Packing and Repair Ablations

Phase: formal. Planned 48; accounted 48; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| answer | 22 |
| clarification | 2 |
| failed | 24 |

All 48 scheduled C outcomes are accounted for, including explicit waiting, refusal, failure and recorded non-execution states.

C1 retains legacy context packing and C2 uses generic answer repair on the current strict contract. Comparisons with B2 are diagnostic/exploratory; they are not additional registered primary effects.

The full B2 condition has 13 conservative successes out of 24, legacy-packing C1 has 6 out of 24, and generic-repair C2 has 16 out of 24. These exploratory results support further inspection of context packing and show no observed advantage for the complete repair policy over C2 in this set.

| Metric | Result |
| --- | --- |
| C1 delivery and end-to-end outcome | Answered 6/24 (25.0%); judged answers 6/6; conservative successes 6/24. |
| C1 automatic applicable-answer dimensions | factual correctness 6/6 (100.0%); source support 6/6 (100.0%); required coverage 6/6 (100.0%); conditions/units 6/6 (100.0%); citation support 6/6 (100.0%); citation mapping 6/6 (100.0%) |
| C2 delivery and end-to-end outcome | Answered 16/24 (66.7%); judged answers 16/16; conservative successes 16/24. |
| C2 automatic applicable-answer dimensions | factual correctness 16/16 (100.0%); source support 16/16 (100.0%); required coverage 16/16 (100.0%); conditions/units 16/16 (100.0%); citation support 16/16 (100.0%); citation mapping 16/16 (100.0%) |
| Measured request duration | C1: median 11.752 s, p95 19.002 s, observed 24/24; C2: median 10.259 s, p95 16.586 s, observed 24/24. |

All planned arm requests remain in the delivery/composite denominator. Failed, refused and unjudged outcomes are not fabricated factual-error ratings.

Each fraction uses only applicable automatic judgments among judged answers; denominators can differ. Flagged memory dimensions count adverse observations, so lower is better. These are model ratings, not human grades.

Runner duration includes online generation, checking and repair. Frozen retrieval preparation, memory preparation, offline judging and HTTP queue time are outside this measure.

Limit: Automatic judgments can share the generator's model-family errors. Independent human ratings remain absent; the small authored study does not establish population-wide educational benefit.

Evidence IDs: formal_results, latencies.

### Study T Teaching Control

Phase: formal. Planned 180; accounted 180; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| answer | 130 |
| failed | 50 |

All 180 scheduled T outcomes are accounted for, including explicit waiting, refusal, failure and recorded non-execution states.

T2 minus T1: -16.67 percentage points (95% paired cluster interval -36.11 to +2.78); negative observed difference. Conservative successes 19/36 versus 25/36; 12 paired families/trajectories.

The five teaching conditions retain three turns within each task. Model-rated useful hints and allowed disclosure are distinct from actual student learning or comprehension.

| Metric | Result |
| --- | --- |
| T0 delivery and end-to-end outcome | Answered 36/36 (100.0%); judged answers 36/36; conservative successes 30/36. |
| T0 automatic applicable-answer dimensions | factual correctness 36/36 (100.0%); source support 36/36 (100.0%); required coverage 34/36 (94.4%); conditions/units 36/36 (100.0%); citation support 33/36 (91.7%); citation mapping 33/36 (91.7%); useful hint 34/36 (94.4%); allowed disclosure 33/36 (91.7%) |
| T1 delivery and end-to-end outcome | Answered 26/36 (72.2%); judged answers 26/26; conservative successes 25/36. |
| T1 automatic applicable-answer dimensions | factual correctness 26/26 (100.0%); source support 26/26 (100.0%); required coverage 26/26 (100.0%); conditions/units 26/26 (100.0%); citation support 26/26 (100.0%); citation mapping 26/26 (100.0%); useful hint 26/26 (100.0%); allowed disclosure 25/26 (96.2%) |
| T2 delivery and end-to-end outcome | Answered 19/36 (52.8%); judged answers 19/19; conservative successes 19/36. |
| T2 automatic applicable-answer dimensions | factual correctness 19/19 (100.0%); source support 19/19 (100.0%); required coverage 19/19 (100.0%); conditions/units 19/19 (100.0%); citation support 19/19 (100.0%); citation mapping 19/19 (100.0%); useful hint 19/19 (100.0%); allowed disclosure 19/19 (100.0%) |
| T3 delivery and end-to-end outcome | Answered 24/36 (66.7%); judged answers 24/24; conservative successes 23/36. |
| T3 automatic applicable-answer dimensions | factual correctness 24/24 (100.0%); source support 24/24 (100.0%); required coverage 23/24 (95.8%); conditions/units 24/24 (100.0%); citation support 24/24 (100.0%); citation mapping 24/24 (100.0%); useful hint 23/24 (95.8%); allowed disclosure 23/24 (95.8%) |
| T4 delivery and end-to-end outcome | Answered 25/36 (69.4%); judged answers 25/25; conservative successes 25/36. |
| T4 automatic applicable-answer dimensions | factual correctness 25/25 (100.0%); source support 25/25 (100.0%); required coverage 25/25 (100.0%); conditions/units 25/25 (100.0%); citation support 25/25 (100.0%); citation mapping 25/25 (100.0%); useful hint 25/25 (100.0%); allowed disclosure 25/25 (100.0%) |
| Measured request duration | T0: median 1.685 s, p95 3.321 s, observed 36/36; T1: median 4.392 s, p95 9.015 s, observed 36/36; T2: median 7.766 s, p95 10.013 s, observed 36/36; T3: median 6.538 s, p95 9.840 s, observed 36/36; T4: median 5.950 s, p95 9.133 s, observed 36/36. |

All planned arm requests remain in the delivery/composite denominator. Failed, refused and unjudged outcomes are not fabricated factual-error ratings.

Each fraction uses only applicable automatic judgments among judged answers; denominators can differ. Flagged memory dimensions count adverse observations, so lower is better. These are model ratings, not human grades.

Runner duration includes online generation, checking and repair. Frozen retrieval preparation, memory preparation, offline judging and HTTP queue time are outside this measure.

Limit: Automatic judgments can share the generator's model-family errors. Independent human ratings remain absent; the small authored study does not establish population-wide educational benefit.

Evidence IDs: formal_results, latencies.

### Study M Learning Memory

Phase: memory. Planned 180; accounted 180; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| answer | 108 |
| failed | 72 |

All 180 scheduled M outcomes are accounted for, including explicit waiting, refusal, failure and recorded non-execution states.

M4 minus M3: -2.78 percentage points (95% paired cluster interval -13.89 to +8.33); negative observed difference. Conservative successes 20/36 versus 21/36; 12 paired families/trajectories.

Separate extraction: 24/24 valid outputs and 16/24 exact authored operation sets. Invalid outputs remain recorded. Observation gates match 12/12 authored expectations, with zero model calls or ungated writes.

M3 and M4 share the typed writer, extracted candidates and evidence; their primary difference concerns reader selection and its final-answer effects. Extraction and the 12 gate cases are additional diagnostics outside the 552 answer requests.

| Metric | Result |
| --- | --- |
| M0 delivery and end-to-end outcome | Answered 19/36 (52.8%); judged answers 19/19; conservative successes 14/36. |
| M0 automatic applicable-answer dimensions | factual correctness 19/19 (100.0%); source support 19/19 (100.0%); required coverage 19/19 (100.0%); conditions/units 19/19 (100.0%); citation support 19/19 (100.0%); citation mapping 19/19 (100.0%); appropriate memory use 14/19 (73.7%); current instruction followed 16/19 (84.2%); stale reuse flagged 0/19 (0.0%); scope violation flagged 0/19 (0.0%); unsupported learner inference flagged 0/19 (0.0%) |
| M1 delivery and end-to-end outcome | Answered 20/36 (55.6%); judged answers 20/20; conservative successes 17/36. |
| M1 automatic applicable-answer dimensions | factual correctness 20/20 (100.0%); source support 20/20 (100.0%); required coverage 20/20 (100.0%); conditions/units 20/20 (100.0%); citation support 20/20 (100.0%); citation mapping 20/20 (100.0%); appropriate memory use 17/20 (85.0%); current instruction followed 17/20 (85.0%); stale reuse flagged 0/20 (0.0%); scope violation flagged 0/20 (0.0%); unsupported learner inference flagged 0/20 (0.0%) |
| M2 delivery and end-to-end outcome | Answered 24/36 (66.7%); judged answers 24/24; conservative successes 18/36. |
| M2 automatic applicable-answer dimensions | factual correctness 24/24 (100.0%); source support 24/24 (100.0%); required coverage 24/24 (100.0%); conditions/units 24/24 (100.0%); citation support 24/24 (100.0%); citation mapping 24/24 (100.0%); appropriate memory use 18/24 (75.0%); current instruction followed 20/24 (83.3%); stale reuse flagged 0/24 (0.0%); scope violation flagged 0/24 (0.0%); unsupported learner inference flagged 0/24 (0.0%) |
| M3 delivery and end-to-end outcome | Answered 23/36 (63.9%); judged answers 23/23; conservative successes 21/36. |
| M3 automatic applicable-answer dimensions | factual correctness 23/23 (100.0%); source support 23/23 (100.0%); required coverage 23/23 (100.0%); conditions/units 23/23 (100.0%); citation support 23/23 (100.0%); citation mapping 23/23 (100.0%); appropriate memory use 21/23 (91.3%); current instruction followed 21/23 (91.3%); stale reuse flagged 0/23 (0.0%); scope violation flagged 0/23 (0.0%); unsupported learner inference flagged 0/23 (0.0%) |
| M4 delivery and end-to-end outcome | Answered 22/36 (61.1%); judged answers 22/22; conservative successes 20/36. |
| M4 automatic applicable-answer dimensions | factual correctness 22/22 (100.0%); source support 22/22 (100.0%); required coverage 22/22 (100.0%); conditions/units 22/22 (100.0%); citation support 22/22 (100.0%); citation mapping 22/22 (100.0%); appropriate memory use 20/22 (90.9%); current instruction followed 21/22 (95.5%); stale reuse flagged 0/22 (0.0%); scope violation flagged 0/22 (0.0%); unsupported learner inference flagged 0/22 (0.0%) |
| M3 typed-state selection | Required-label recall 22/26 (84.6%); 36/36 selection records; 7 explicitly excluded selections. |
| M4 typed-state selection | Required-label recall 21/26 (80.8%); 36/36 selection records; 2 explicitly excluded selections. |
| Measured request duration | M0: median 10.335 s, p95 12.895 s, observed 36/36; M1: median 10.440 s, p95 13.845 s, observed 36/36; M2: median 10.738 s, p95 13.461 s, observed 36/36; M3: median 7.263 s, p95 13.818 s, observed 36/36; M4: median 6.789 s, p95 14.598 s, observed 36/36. |

All planned arm requests remain in the delivery/composite denominator. Failed, refused and unjudged outcomes are not fabricated factual-error ratings.

Each fraction uses only applicable automatic judgments among judged answers; denominators can differ. Flagged memory dimensions count adverse observations, so lower is better. These are model ratings, not human grades.

Required/excluded labels are partial. Semantic selection precision remains unavailable; no typed-field comparison is assigned to M0/M1/M2.

Runner duration includes online generation, checking and repair. Frozen retrieval preparation, memory preparation, offline judging and HTTP queue time are outside this measure.

Limit: Automatic judgments can share the generator's model-family errors. Independent human ratings remain absent; the small authored study does not establish population-wide educational benefit.

Evidence IDs: formal_results, latencies.

## Calls and cost

| Purpose | Calls | Input tokens | Output tokens | Estimate |
| --- | --- | --- | --- | --- |
| All purposes — total | 1,919 | 13,282,080 | 912,290 | 9.31490148 CNY |
| Checker contract repair | 75 | 753,463 | 95,846 | 0.4136854 CNY |
| Answer generation | 546 | 3,529,798 | 153,370 | 1.60474872 CNY |
| Other retained purpose | 7 | 50,734 | 1,366 | 0.00840536 CNY |
| Joint checking | 435 | 3,850,533 | 319,306 | 3.74841876 CNY |
| Joint rechecking | 178 | 1,545,003 | 122,648 | 1.48127564 CNY |
| Memory extraction | 13 | 4,578 | 601 | 0.00535128 CNY |
| Typed memory extraction | 24 | 11,339 | 1,301 | 0.01077276 CNY |
| Offline automatic judging | 450 | 2,051,885 | 168,233 | 1.36843624 CNY |
| Provider answer basic | 1 | 52 | 51 | 0.000256 CNY |
| Provider answer project | 1 | 453 | 80 | 0.000773 CNY |
| Provider answer structured | 1 | 138 | 5 | 0.000158 CNY |
| Provider checker basic | 1 | 52 | 92 | 0.00042 CNY |
| Provider checker project | 2 | 2,704 | 1,139 | 0.00613104 CNY |
| Provider checker project debug | 1 | 1,318 | 588 | 0.00254104 CNY |
| Provider checker structured | 1 | 138 | 5 | 0.000158 CNY |
| Rolling memory summary | 22 | 4,321 | 314 | 0.005577 CNY |
| Answer repair | 161 | 1,475,571 | 47,345 | 0.65779324 CNY |

All purposes — total. 1919 retained attempt records: 1799 submitted, 0 explicitly not submitted and 120 uncertain. Known estimated subtotal 9.31490148 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Checker contract repair. 75 retained attempt records: 75 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.41368540 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Answer generation. 546 retained attempt records: 523 submitted, 0 explicitly not submitted and 23 uncertain. Known estimated subtotal 1.60474872 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Other retained purpose. 7 retained attempt records: 7 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.00840536 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Joint checking. 435 retained attempt records: 412 submitted, 0 explicitly not submitted and 23 uncertain. Known estimated subtotal 3.74841876 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Joint rechecking. 178 retained attempt records: 159 submitted, 0 explicitly not submitted and 19 uncertain. Known estimated subtotal 1.48127564 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Memory extraction. 13 retained attempt records: 0 submitted, 0 explicitly not submitted and 13 uncertain. Known estimated subtotal 0.00535128 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Typed memory extraction. 24 retained attempt records: 24 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.01077276 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Offline automatic judging. 450 retained attempt records: 450 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 1.36843624 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Provider answer basic. 1 retained attempt records: 1 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.00025600 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Provider answer project. 1 retained attempt records: 1 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.00077300 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Provider answer structured. 1 retained attempt records: 1 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.00015800 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Provider checker basic. 1 retained attempt records: 1 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.00042000 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Provider checker project. 2 retained attempt records: 2 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.00613104 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Provider checker project debug. 1 retained attempt records: 1 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.00254104 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Provider checker structured. 1 retained attempt records: 1 submitted, 0 explicitly not submitted and 0 uncertain. Known estimated subtotal 0.00015800 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Rolling memory summary. 22 retained attempt records: 0 submitted, 0 explicitly not submitted and 22 uncertain. Known estimated subtotal 0.00557700 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

Answer repair. 161 retained attempt records: 141 submitted, 0 explicitly not submitted and 20 uncertain. Known estimated subtotal 0.65779324 CNY; 0 unpriced attempts. Input/output totals stay unknown when their receipts are incomplete.

The first row is the total; remaining rows are its purpose breakdown and must not be added to the total again. The Calls column counts retained attempt records, with submission states stated separately.

Estimates use the published DeepSeek tariff verified on 2026-09-21. They are not invoice reconciliation. Actual billing timestamps and provider alias behavior retain their recorded limitations.

The receipt ledger contains 0 completeness warnings. Unknown cost and incomplete token totals remain null; no unsubmitted or uncertain reservation is silently reported as a successful paid call.

All 1919 retained attempts have priced input/output usage. Submission-state fields are absent for 120 attempts, and 14 records use a retained timestamp proxy for tariff selection. These accounting limits remain visible alongside the 9.31490148 CNY estimate.

## Retained failures

Retained provider compatibility failure. The original checker project probe failed before the later corrected authored probe passed. Both receipts remain distinct; a compatibility pass does not certify answer accuracy. Evidence IDs: deepseek_initial.

A retained non-answer outcomes. 5 failed, 0 refused, 0 clarification, 0 recorded not-run and 24 human-dependent waiting requests remain in 72 planned outcomes. No outcome filtering, resampling or conversion of missing ratings into correctness labels is applied. Evidence IDs: formal_results.

B retained non-answer outcomes. 26 failed, 0 refused, 3 clarification, 0 recorded not-run and 0 human-dependent waiting requests remain in 72 planned outcomes. No outcome filtering, resampling or conversion of missing ratings into correctness labels is applied. Evidence IDs: formal_results.

C retained non-answer outcomes. 24 failed, 0 refused, 2 clarification, 0 recorded not-run and 0 human-dependent waiting requests remain in 48 planned outcomes. No outcome filtering, resampling or conversion of missing ratings into correctness labels is applied. Evidence IDs: formal_results.

T retained non-answer outcomes. 50 failed, 0 refused, 0 clarification, 0 recorded not-run and 0 human-dependent waiting requests remain in 180 planned outcomes. No outcome filtering, resampling or conversion of missing ratings into correctness labels is applied. Evidence IDs: formal_results.

M retained non-answer outcomes. 72 failed, 0 refused, 0 clarification, 0 recorded not-run and 0 human-dependent waiting requests remain in 180 planned outcomes. No outcome filtering, resampling or conversion of missing ratings into correctness labels is applied. Evidence IDs: formal_results.

All recorded generation failures. The 177 failed requests comprise 91 SEMANTIC_CHECK_FAILED, 65 CHECKER_INCONSISTENT, eight CONTEXT_LIMIT, seven MISSING_CITATIONS, five SUPPLIED_ANSWER_CONTRACT_FAILED and one OUTPUT_TRUNCATED. The 72 memory-study failures comprise 49 inconsistent-checker results, 18 failed support checks and five context limits. These are execution and publication error categories. Independent review of rejected drafts is needed to establish which refusals were unnecessary. Separately, 22 offline judgments failed their schema: 17 A1 answers and five clarification outputs. Evidence IDs: numerical_review, formal_results.

Initial package reconstruction. The first complete archive and eight member archives were retained after reconstruction reported one extra official corpus gzip resource and no other path or hash differences. The exact runtime resource exception was corrected and covered by the actual ZIP regression. Final archive identities and the rerun reconstruction result are recorded in the adjacent delivery sidecars. Evidence IDs: release_fix, gate, public_parity.

## Independent human review

Completed ratings: 0. Independent reviewers with imported ratings: 0.

Two randomized reviewer slots each contain 552 blank rows. Slots are prepared forms, not two completed human reviewers. The public verification records no completed or imported ratings; condition keys remain private.

- Give each independent reviewer only their assigned blinded material and scoring guide.

- Keep reference labels, coordinator condition keys and automatic judgments separate from reviewer ratings.

- Import genuine named, timed ratings immutably, retain disagreements and record separate adjudication.

## Operation and delivery

Inspect and manage learning memory. Open Learning memory, opt in, inspect the summary and use Preview memory for a question. Check the source, scope and verification before editing or deleting an entry. Current instructions override saved preferences. Verified scope: Actual owned browser/HTTP preview, correction, source modal, profile-off, disable and deletion, plus sign-out privacy checks.

Configure answering and checking. Save a version, select its role and test stage, inspect the receipt, then enable an eligible answer/checker pair. A declaration or successful basic stage alone does not satisfy the project gate. Verified scope: Real live DeepSeek receipts and paired activation; separate actual mock-browser failure and activation controls.

Operate the isolated CPU installation. Use the documented local launcher with CPU mode and distinct database, API and frontend ports. Preserve resource hashes and confirm readiness before using the application. The verification instance used ports 15932, 18300 and 15473 and was stopped afterward. Verified scope: Fresh virtual environment and dependency installation on the existing Windows host, two persisted turns, cancellation and history, with final source/resource parity.

Retain ownership and evidence boundaries. Follow the original task allocation and the dated evidence references. Public application packages use the approved exclusions; authorised research inputs are restored separately when optional evaluator commands require them. Verified scope: Original 108 task, 60 acceptance and 12 responsive IDs preserved; final portable public membership checked.

Run software checks without private research inputs. Install the pinned requirements-dev.lock and requirements-sciq.lock alongside the CPU runtime locks, then run the documented mock software gate against an isolated PostgreSQL test server. Actual research catalogues are supplied separately for optional evaluator studies. Verified scope: Public portable tree passed all 828 Python checks, all 86 frontend checks and all eight gate stages; Torch stayed 2.8.0+cpu, CUDA unavailable, and pip check passed..

The delivery provides one runnable project archive, eight disjoint member contribution archives and nine English Word reports with matching Markdown. Original task allocations are retained. The full package supplies the same 80 corpus, vector, model and tokenizer resources; member archives contain changes relative to the preserved 20 September baseline.

The adjacent delivery index, package verification and reconstruction records identify the actual archive sizes and hashes. The reconstruction check compares the preserved public baseline plus all eight member contributions against the complete archive. Each member package includes owned file hashes, a README and proposed commit and pull request text for personal review.

The separately verified private research archive preserves frozen source, authored cases, original outputs, failed attempts, automatic judgments and coordinator keys. Reviewers receive only their assigned blank materials and scoring guide. The application and member packages exclude credentials, original learner histories and private research answers.

## Limitations and Week 9 goals

A1 automatic factual scores cover only 2 of 19 delivered answers. Seventeen judgments failed the applicability contract; both inspected examples supplied a score for a field that required null. This limited coverage prevents a reliable A0 versus A1 quality conclusion. The 17 failures remain unjudged.

The software gate verifies implemented contracts and the exercised fixtures. Scientific support, useful teaching and appropriate memory use require the separately recorded output evaluations.

The CPU run combines real E5, reranking and pgvector retrieval with mock answer generation. Its two observed turn times are individual local observations, not a service-level performance estimate or cross-device comparison.

Live DeepSeek receipts establish the tested role and protocol stages on the recorded network. A model alias and configured tokenizer do not establish a permanent remote checkpoint identity; provider and network changes require fresh observations.

The browser screenshots cover the recorded viewport portions and interactions. Physical mobile input, IME, assistive technology and independent usability reviews require additional measurements.

A recorded result includes failed, refused, unexecuted and human-dependent cases. Conservative end-to-end success counts missing or unjudged answers as unsuccessful without inventing factual-error grades. Same-family judge bias and zero independent human ratings remain explicit.

- Collect two genuine independent blinded reviews, inspect disagreements, and record adjudication separately. Obtain actual source-sufficiency confirmations before running the A2 oracle arm.

- Use the retained checking and mapping failures to register bounded repairs. Review why teaching checks reject useful drafts and why selected memory sometimes fails to improve answer delivery.

- Clarify the offline judge applicability prompt and preregister a new judge run with the original receipts retained. Evaluate cross-provider agreement with an authorised provider configuration.

- Repeat the clean installation and learner/admin journeys on another physical device, including keyboard, IME and assistive-technology checks. Plan student learning measurements separately.

## Responsibilities

Codex performed the implementation, automated checks and recorded local browser verification through the shared project workflow. The eight reports follow the original accountable domains; member submissions and independent human reviews retain their own execution records.

| Member | Accountable domain |
| --- | --- |
| Xianshu Zhang | Architecture and integration |
| Hongle Yang | Source provenance and exact unit mapping |
| Chengzhou Liu | Retrieval and source selection |
| Sijin Lu | Generation and semantic checking |
| Pengyuan Xia | Learning memory and teaching policy |
| Zeping Liao | Backend state permissions and lifecycle |
| Baiqing Huang | Learner interface and inspectable sources |
| Chong Zhang | Evaluation and independent review |

## Evidence references

Paths refer to public records in the project. Each hash identifies the exact record used here.

Final integrated public source software gate. 828 Python tests, 86 frontend tests, all eight stages passed with no skips and unchanged captured successor source

evidence/week08-memory-v2/20260921/software-gate-release-final-20260922/software_gate.json

SHA256 9d769c3006a8f7800678abcab474429895568d9834037ce4f2894d3f3bf01fd3

Final integrated Python results. 828 passing unit and isolated PostgreSQL checks; zero failures, errors or skips

evidence/week08-memory-v2/20260921/software-gate-release-final-20260922/pytest.xml

SHA256 4931f56a94e316368d999f884dc8b8d4b6834c464985b869a410b0464af4d015

Final frontend results. 86 passing tests across 11 files; types and production build also passed

evidence/week08-memory-v2/20260921/software-gate-release-final-20260922/frontend_tests.log

SHA256 b82379564072e72962e56721868bda2bea5e0e29e45517cf91b509a60fe55004

Additive migration preservation. Existing-column contents and counts in 44 prior tables remained unchanged through migration e0a64c7d123b, including the preceding memory revision.

evidence/week08-memory-v2/20260921/migration/preservation-result.json

SHA256 986740e61b25c75ca3b199409b295fa1f0bc572d9c7c66e98b41c25d4cc18413

Memory implementation checkpoint. 45 focused Python checks and the dated component/build/browser checkpoint; the recorded pre-formal status belongs to this earlier checkpoint.

evidence/week08-memory-v2/20260921/memory/implementation-checkpoint.json

SHA256 879a6ed51d67605fd9fad3a11388e689dad6198f5a6390e9ae49c09b6e9f0d43

Actual Memory V2 browser workflow. Owned authored data in a separate migrated database; preview, source, edit, disable and deletion through actual endpoints at 1440 and 390 pixels; zero provider calls.

evidence/week08-memory-v2/20260921/memory/browser-final/verification.json

SHA256 aff7e1263b4d2bd6fbbab2a69cba2fbb9c372fa80ea8862965875139a1495d8c

Memory visual and runtime review. Five screenshots inspected individually, no original-database mutations, and owned temporary services stopped.

evidence/week08-memory-v2/20260921/memory/browser-final/visual-and-runtime-review.json

SHA256 e93263266e6f28f922583ef84c7c46b44b1a164f4cc50829f9a1f01e582d6a87

App and Memory route regression. 16 passing overlapping component/integration checks, including removal of rendered private memory and the session token on sign-out.

evidence/week08-memory-v2/20260921/memory/app-memory-current.json

SHA256 8a22bf5b297d405287776e7809b554642947384d82d2940f3467bf89f2ab66e4

Fresh isolated CPU installation. Fresh directory, virtual environment and dependencies on the existing Windows host; real CPU retrieval and mock answers. This earlier installation checkpoint contains 515 selected files.

evidence/week08-memory-v2/20260921/portable/summary.json

SHA256 3f0e5edb523bbae1e9fa7ea813928f125d76db843abe77fe2a9ed129faa33b02

Actual portable CPU HTTP workflow. Two persisted textbook turns, cancellation, source identities and history after sign-in on the separate database; explicit mock answering.

evidence/week08-memory-v2/20260921/portable/http-attempt1.json

SHA256 ee7c79530f7ebfcfed4f44322bffd8143b75a65219f2121f725820d69b7412f6

Portable conversation and source browser. Saved answers and approved source segments inspected through actual browser endpoints at desktop and mobile viewport widths.

evidence/week08-memory-v2/20260921/portable/browser-attempt1/verification.json

SHA256 f47aacfaa0907cb391b668fe157e033a441a47c9102122e35fec98138957a4b9

Final public source and resource parity. 514 selected source and configuration files match the portable public tree; all 80 resources match the preserved bundle, including 30 model and tokenizer files also compared with main paths

evidence/week08-memory-v2/20260921/portable/source-parity-release-final-20260922.json

SHA256 66cb3799d646b1b9d52dea9f442538f6ca9560b44db9d7ebcc9419c6705c0ccb

Actual Models role and activation workflow. Local mock answer/checker suites, activation gating, actual context-reservation failure and restored environment settings; zero paid calls.

evidence/week08-memory-v2/20260921/portable/models-browser-attempt2/verification.json

SHA256 cf9b908c17046995446b9c0e967d4929b48bfa54cd01437e36ff9708a40d780e

Models desktop and mobile review. Three screenshots inspected; failed successor remained ineligible and the prior active pair was preserved before environment restoration.

evidence/week08-memory-v2/20260921/portable/models-browser-attempt2/visual-and-workflow-review.json

SHA256 abeacec6c2a82a5922b4a30798efb06d489306fc84f7a8c0096bb5f98fc063fa

Initial live DeepSeek role suites. Answer suite passed; initial checker suite failed. Both original outcomes are retained; physical network location was unverified.

evidence/week08-memory-v2/20260921/providers/deepseek-staged-live-01/summary.json

SHA256 bab9efab92967fe380264fc24b21ece7b11edc2f20bbb6315fdf85d6e2c29e76

Live DeepSeek answering compatibility receipt. Saved deepseek-flash configuration passed basic, structured and project stages; provider usage and bounded reservations recorded.

evidence/week08-memory-v2/20260921/providers/deepseek-staged-live-01/answer.json

SHA256 20d53a265fafab061d466705218fd8f0530bfea368577a5bcf980f972d70c0e8

Live DeepSeek checker project receipt. Later project-stage test passed with a 4096-token reservation after the authored probe was aligned with the strict arithmetic grammar.

evidence/week08-memory-v2/20260921/providers/deepseek-checker-project-live-02.json

SHA256 94309ee6e1c0991bb3e634eeded55f6f43c8b6cc699dcfaf9023dd60fedea4ba

Separate role activation receipt. The existing answer revision was retained while the verified checker selection was added through the actual versioned activation route.

evidence/week08-memory-v2/20260921/providers/deepseek-paired-activation.json

SHA256 ca857c496eb48ca7f78ee71cd11b528c34de25715c91cfcd935ecc6b6aea58c9

Versioned reliability implementation checkpoint. Exact policy/source hashes and focused software checks. Counts overlap the final gate; this record supplies no new formal or human-quality result.

evidence/week08-memory-v2/20260921/answering/implementation-final-verification.json

SHA256 a84f9e6365a181a10d4f10babdf9b298dac4464d42609bb1ff617aaa1cde74c3

Original task and acceptance identifiers retained. 180 new scoped observations preserve 108 original tasks, 60 acceptance IDs, 12 responsive rows and their prior statuses and evidence history

evidence/week08-memory-v2/20260921/ledger-release-final-20260922/summary.json

SHA256 dece23c448b4b773a78fae3e002899cbeda07d3991f66c324285c4e5d30e3012

Public distribution software gate. Isolated public tree with tests-only successor: 828 Python, 86 frontend, eight stages passed and zero skips; main source unchanged.

evidence/week08-memory-v2/20260921/public-distribution-attempt3/summary.json

SHA256 c1dd7e35881e8b8d4a8586f7b2464f887def6dc129fb2a688796cba7cab5792a

Preserved private-fixture dependency failures. Unchanged public tests: 42 missing-input failures, 784 passing tests and two optional Parquet skips; seven other stages passed.

evidence/week08-memory-v2/20260921/public-distribution-attempt2/summary.json

SHA256 195d5683a2e4b7dee1690b63ccc49ca1423db6001c650e9bdcb52fb75a2b7398

Tests-only patch and invariant verification. Five public test modules and two independent helpers preserve all 257 assertion expressions and 54 test functions. The final successor gate captures the integrated bytes.

evidence/week08-memory-v2/20260921/public-distribution-attempt3/test-patch-verification.json

SHA256 cbd1453741144173c9be792053d50bde67c5b14c644c3d2a9dc62a1f8ba78fb8

Focused public fixture verification. 64 affected checks passed, including real isolated PostgreSQL and both Parquet acquisition checks; zero skips or external provider calls.

evidence/week08-memory-v2/20260921/public-distribution-focused1/summary.json

SHA256 cf48ba9a3933f8e59f0529b4b1fc6607e35d4ca02994305eded54c04b239a096

Registered automatic study results. 552 scheduled requests across 18 arms; all generation and offline judgment outcomes retained; independent human ratings zero

evidence/week08-memory-v2/20260921/formal/public-results.json

SHA256 b470c9c5df020d3dd7dae9625fdfabc82afdf60569f33a3d62c84a5ea340e7f6

Reconciled actual attempt accounting. Development, provider diagnosis, extraction, summary, formal answers and offline judging; dated tariff estimates including failures

evidence/week08-memory-v2/20260921/accounting/final.json

SHA256 eb79da9c78412c5ce5d7196d18ffea6df5aa53d97eca336e07cacde82def7559

Actual blank blinded review export. Two randomized 552-row reviewer slots; zero completed or imported ratings

evidence/week08-memory-v2/20260921/formal/review-export-verification.json

SHA256 9f9f675f3f00a30b7e64745be7d9ef0f2d2786295fb2cbdbc5a6a43041a75b5a

Measured formal request and model attempt latency. All 552 scheduled identities; excludes prior CPU candidate preparation and memory preparation; no HTTP queue timing claim

evidence/week08-memory-v2/20260921/formal/public-latencies.json

SHA256 cd36c029d024ef39a64ab5ab3a734c608d7851896832cdb889618246eff77473

Main service and corpus preservation check. Read-only original database: 10594 vectors, dimension 384, all captured corpus and vector hashes unchanged; frontend and API ready returned HTTP 200

evidence/week08-memory-v2/20260921/runtime-final-01.json

SHA256 9ef0d2d49d10f042c843d63621a34baf7f214c5004af36617ad0d4f9fcd41ac2

Independent numerical reconciliation. Independent recalculation of retained scalar outcomes, primary contrasts, failure counts, cost and latency scope

evidence/week08-memory-v2/20260921/formal/numerical-review.json

SHA256 3833b4899a8850cdd4c81368b84fafbf73e8b1d81774abed87adf46b8908b2ef

Retained automatic judge applicability failures. A1 has two judged answers out of 19 delivered answers and 17 schema failures; two sampled causes were checked against the frozen contract

evidence/week08-memory-v2/20260921/formal/judge-applicability-observation.json

SHA256 e3d8b046aaf63b38d2b7a3e61724b1323cf60d10c7dc1d519b21d5a424890b59

Official corpus archive reconstruction correction. One exact verified runtime gzip resource retained in baseline reconstruction; unrelated archives stay excluded; focused regression, full gate and preserved failed ZIP attempt

evidence/week08-memory-v2/20260921/packaging/release-fix-verification.json

SHA256 4f4f7b27c68510fcb8a31b9d5631b28b3ddf5bde1b034250b6d5495e2fcdd238
