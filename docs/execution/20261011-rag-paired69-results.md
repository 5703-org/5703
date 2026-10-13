# Matched RAG69 results — 11 October 2026

All **36/36 normal model requests** completed with valid compact answers: **12/12 per condition**, zero failures/refusals, reported known API charge **USD0.0185022**, and current-cohort financial UNKNOWN **0**. The scored conditions are E0 (no retrieval), E1 (frozen dense top5), and HYBRID_R2_MINILM (frozen hybrid/reranked top5). This is the final observed result for this exposed development cohort; native-page acceptance is separate and does not delay these results.

## Lexical scores and paired comparisons

The unchanged original `conservative-v1` scorer evaluates validated `response.short_answer` against one frozen reference per question. It applies NFKC, case folding and whitespace normalization, retains punctuation, and computes multiset token F1. There are no aliases, reference edits, full-prose extraction or answer-text fallback. Each arm's mean uses **all 12 scheduled, closed, valid answers**, with no excluded failures or pending rows in this cohort.

| Condition | Scheduled / closed / valid answers | Exact match | Mean token F1, n=12 |
| --- | ---: | ---: | ---: |
| E0 | 12 / 12 / 12 | 0/12 (0.0) | 0.4774556002 |
| E1 | 12 / 12 / 12 | 0/12 (0.0) | 0.5420380174 |
| HYBRID_R2_MINILM | 12 / 12 / 12 | 0/12 (0.0) | 0.5441463917 |

Each paired comparison uses the **same 12 question IDs**, one answer per condition/question. A win/tie/loss compares the first condition's token F1 with the second condition's token F1; these are descriptive counts, not independent trials or significance tests.

| First minus second condition | Paired n | Mean token-F1 change | Wins / ties / losses |
| --- | ---: | ---: | ---: |
| E1 − E0 | 12 | +0.0645824171 | 8 / 1 / 3 |
| HYBRID_R2_MINILM − E0 | 12 | +0.0666907915 | 8 / 0 / 4 |
| HYBRID_R2_MINILM − E1 | 12 | +0.0021083743 | 5 / 1 / 6 |

Every EM paired comparison is **0 wins / 12 ties / 0 losses**, since every arm has exact match 0/12. Strict EM zero is an exact-string finding, not a finding that all 36 answers are scientifically incorrect. Token F1 is a lexical diagnostic proxy, not answer accuracy.

## Descriptive frozen-fact review

An independent **unblinded AI review** inspected all 36 saved answers against **38 frozen source propositions per arm**. It checked 36 answer identities, 112 exact answer excerpts and 114 fact/quote links. Its categories below are descriptive coverage labels; inferred facts are excluded from explicit coverage. This review is not a preregistered calibrated semantic correctness metric or human Gold.

| Condition | Explicit facts / 38 | Inferred facts / 38 | Missing facts / 38 | Required-fact contradictions / 38 | All required facts explicit / 12 questions |
| --- | ---: | ---: | ---: | ---: | ---: |
| E0 | 27/38 | 5/38 | 6/38 | 0/38 | 7/12 |
| E1 | 32/38 | 4/38 | 2/38 | 0/38 | 7/12 |
| HYBRID_R2_MINILM | 32/38 | 3/38 | 3/38 | 0/38 | 7/12 |

The retrieval conditions state more frozen facts explicitly in aggregate, but the number of questions with every required fact explicit remains **7/12 in every arm**. Every arm omits explicit prophage excision in Q06 and surface-wide water uptake in Q07. Relevant context does not force a complete answer.

The single-predesignated-ID retrieval measure is **10/12 questions for E1** and **10/12 for HYBRID_R2_MINILM** at k5; it is inapplicable to E0, which submits no retrieval. This is designated-ID hit recall, **not answer accuracy or exhaustive corpus relevance recall**. Q12 misses the designated ID in both snapshots; E1 nevertheless has alternative full-definition support in chunks `0f7b24f23d7b5108fe8c115e6e28a87c0ed1` and `aaf8131212d4d5f42da3658d620ae51c8c85`. The hybrid answer states the full definition while its submitted context lacks the complete relative-abundance definition, so its content cannot be fully attributed to those passages.

Required-fact contradictions of 0/38 do not verify every additional assertion. The review retains source-unverified extras separately, including E0 Q11's thin-limb diffusion versus thick-limb active-transport caveat. Missing or inferred facts alone do not establish scientific falsehood.

## Component time and reported charge

The primary timing is saved `provider_latency_ms`, measured inside the unchanged Main `LLMAdapter.generate`. Each p50/p95 below has **n=12 observed calls per condition**. Quantiles use linear interpolation at `(n−1) × fraction`; p95 at n=12 lies at zero-based position 10.45. This empirical p95 is a small-sample descriptive component quantile, not a stable warm or native-page p95.

| Condition | Adapter timing n | Adapter p50 ms | Adapter p95 ms | Reported arm charge USD, 12 requests |
| --- | ---: | ---: | ---: | ---: |
| E0 | 12 | 1223.5 | 1750.90 | 0.0026398 |
| E1 | 12 | 1158.5 | 1293.95 | 0.0079143 |
| HYBRID_R2_MINILM | 12 | 1164.0 | 1457.40 | 0.0079481 |

The separate controller-inclusive `normal_adapter_wall_ms` also has n=12 per condition. It includes post-adapter financial fsync, decoding and safe local processing; it must not replace the adapter timing.

| Condition | Controller-inclusive n | p50 ms | p95 ms |
| --- | ---: | ---: | ---: |
| E0 | 12 | 1225.45210 | 1752.92744 |
| E1 | 12 | 1162.14895 | 1295.73653 |
| HYBRID_R2_MINILM | 12 | 1165.49150 | 1459.61465 |

Independent financial review matches all 36 transport claims, financial observations, settlements and saved results. Decimal reconciliation gives **USD0.0026398 + USD0.0079143 + USD0.0079481 = USD0.0185022**, with no unresolved current-cohort charge. The original lexical usage aggregate retains cost null because saved costs are Decimal strings and that aggregate accepts numeric JSON costs; its null is not financial UNKNOWN. These charges are provider-reported observations for this cohort, not total project spend, account cash or a release of older protections. There were zero retries and zero external judge calls.

Live retrieval time, total-pipeline time, TTFT and fresh browser Send-to-complete-display time are **null/unmeasured**, with **no native timing sample** in this score cohort. Current native startup attempts have submitted no model request and added zero provider calls; they do not establish zero answer latency or a model-quality failure. The only live calls represented here are the 36 normal compact-generation calls. A dated earlier native n=1 observation is not substituted for a fresh measurement. AC-44 and project completion remain unpromoted.

## Exact study scope and evidence

The same 12 **previously exposed, source-conditioned public synthetic DEV questions** are used in all arms. They are not blind, heldout, human-validated or a representative learner study. Thirty-eight required facts, 27 source anchors and lexical references were frozen before these answers; the standards are locally AI-authored/source-backed, with **human Gold null**. There is one observed answer per arm/question and no variance study.

All conditions use the same neutral own-knowledge policy, normal adapter, Gemini 3.5 Flash Lite, Vertex/global low route without fallback, compact JSON schema, 768-token output cap and 45-second timeout. Each condition occurs first/middle/last four times. E0 has no retrieved context; E1 and HYBRID_R2_MINILM submit retained top5 snapshots from the same 10,594-chunk release: 120 submitted evidence slots and 84 unique chunks. This experiment does not rerun live retrieval. References, required-fact labels and learner history/profile are absent from model payloads; this compact schema does not request model citations.

The small positive token-F1 changes do not establish general RAG superiority, scientific correctness, quality non-inferiority or a causal product-latency improvement. More explicit facts did not improve this cohort's all-facts-explicit question count. Earlier SciQ DEV and native studies remain separately dated and are not pooled into these denominators.

The [score JSON](evidence/20261011-rag-paired69-scores/score69-final.json) preserves unrounded values and explicit denominators. The new [evidence index](evidence/20261011-rag-paired69-scores/index.json) pins the closed receipt, [all 36 complete public answer records](evidence/20261011-rag-paired69-scores/public-paired69-results.json), unchanged inputs/standards, original scorer source pins, lexical/financial review and [semantic review](evidence/20261011-rag-paired69-scores/independent-semantic-review69.md). Existing status documents and their historical prefixes are unchanged by this independent result publication.
