# Personalised AI Learning Assistant Using Retrieval-Augmented Generation and Large Language Models

## Week 8 Module Report

Chengzhou Liu | SID 540931958 | Retrieval and RAG

## Week 8 outcome

The retrieval workstream implemented bounded question understanding, explicit correction and relevance screening, then integrated complementary earlier evidence and CPU execution. Bare RAG requests clarification; explicit AI context resolves retrieval-augmented generation, while RAG1 and ragweed retain their biological meanings. The accountable scope is RET-01 through RET-11 and CHAT-04.

The prepared record now includes requested parts, comparison targets, numbers, conditions, negation and correction context. Ambiguous comparison corrections ask the learner for a complete question.

## Implementation and integration

conversation/understanding.py preserves bounded interpretation and emits a structured trace. retrieval/relevance.py merges eligible earlier passages with fresh candidates under a finite cap, then applies current-question scoring and a versioned topic screen. Old ranks never substitute for current scores. Source identity and release membership are checked before reuse.

retrieval/runtime.py resolves automatic or explicit local devices. CPU execution uses existing real vectors and pinned models; unavailable explicit devices fail visibly. New commands freeze the policy while historical commands keep their recorded behaviour.

An explicit general-knowledge request bypasses retrieval; textbook refusal retains its own source policy and never silently changes modes.

## Calibration and coverage research

The provisional -4.0 raw-logit threshold remains tied to the pinned MiniLM cross-encoder. The new calibration tool selects thresholds from reviewed development groups and evaluates a held-out split. It rejects blank reviewers, mixed model revisions and group leakage. Independent labels are still required before a newly calibrated policy can be claimed. The v3 split corrects a related RAG-family grouping after earlier diagnostic runs; those earlier outcomes keep their original bank identity and exposure history.

Complementary evidence packing now keeps the top-ranked anchor and prioritises uncovered request parts, new terms and qualifications inside the existing budget. Lexical coverage and topic relevance have distinct traces, providing concrete inputs for a controlled source-support comparison.

A bounded fallback searches up to two explicit parts after zero whole-question survivors, then records each query and its own relevance scores.

## Verification and current limits

The final software gate passed all eight stages: 427 Python tests and 56 frontend tests, with 365 captured source files unchanged. Focused unit and PostgreSQL checks cover source revalidation, current-query rescoring, correction semantics and historical request compatibility. The broader v8 execution met 106 of 110 main-case expectations, 13 of 14 teaching expectations and all six robustness expectations. The final v9 targeted regression met 35 of 37 expectations; two clarification deviations remain recorded. These are workflow observations, with independent ratings still open.

The fresh CPU installation retains 48 sources, 10,594 vectors and all 80 bundled resources. Final source parity matches 407 safe source/configuration files. Actual queued and active cancellation, a three-attempt timeout and three CPU/CUDA retrieval comparisons are recorded. The mixed-question CPU path admits ten passages within 2,548 evidence tokens; its conservative mock answer still refuses the whole question. Live partial answering has a separate provider record. The two earlier 16-case CPU retrieval runs preserve their exact scope. Physical MPS execution and independent source-completeness judgements remain open.

## Week 9 measurable goals

- Collect independent relevance and coverage labels for the fixed development groups, then freeze a model-bound threshold before held-out evaluation.
- Compare ranked filling and complementary packing on the fixed multi-part cases, reporting false refusals and missing support with all outcomes retained.
- Reproduce device selection and real model execution on another available machine, recording timing, memory and any unsupported accelerator.

## Dependencies

Hongle supplies original-page coverage records and Chong manages grouped labels. Sijin defines which evidence is sufficient for each response condition. Zeping records policy and device choices in persisted requests, and Baiqing exposes clarification and evidence outcomes. These shared contracts should remain stable across the CPU installation and the next controlled comparison.

## Evidence references

Paths are relative to the delivered project root.

- Integrated Week 8 implementation and research: `docs/execution/week08-delivery-20260916.md`

- Fixed source-backed question bank: `evaluation/reliability/week08_cases_v3.json`

- Current checks and execution records: `evidence/week08-delivery/20260916/`
