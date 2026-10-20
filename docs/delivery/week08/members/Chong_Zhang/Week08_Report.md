# Personalised AI Learning Assistant Using Retrieval-Augmented Generation and Large Language Models

## Week 8 Module Report

Chong Zhang | SID 530668840 | Evaluation and Quality Assurance

## Week 8 outcome

The evaluation workstream implemented the grouped 120-case bank, calibration safeguards and expanded regression checks. The accountable scope is QA-01 through QA-14 and CHAT-09 and CHAT-10. The bank binds exact source positions, developer expectations and separate independent review fields.

The evaluation design distinguishes topic relevance, complete support, answer quality, citations, teaching and operational failure. Each has an explicit outcome denominator and review method.

## Dataset and calibration implementation

week08_cases_v3.json contains 30 standard questions, 20 colloquial or synonym cases, 15 multi-turn or correction cases, 10 ambiguity cases, 15 out-of-corpus cases, 10 partial or conditional or conflict cases, 10 cross-chapter or formula or figure cases, and 10 attack or revocation or runtime cases.

Its 60 immutable passages span 30 topics and four books. Knowledge groups remain intact across 75 development and 45 held-out cases. The calibration tool requires nonblank independent reviewers, rejects model-revision mixing and group leakage, selects from development data and reports held-out behaviour. The v3 split corrects a related RAG-family grouping after earlier diagnostic runs; those earlier outcomes keep their original bank identity and exposure history.

Mode checks retain the first failed general follow-up and its three empty responses, followed by successful continuation and return-to-textbook source checks.

## Execution and analysis decisions

The new schedule preserves each first real-provider outcome and connects it to the fixed bank. Runtime faults and controlled source or instruction attacks have dedicated checks. The teaching schedule records the current integrated conditions. Human relevance and teaching ratings stay blank until completed by reviewers.

The earlier live OpenQA and MCQ studies remain bound to their original source snapshot, including their negative E1 results. The current interactive changes preserve formal E0/E1 prompts and conditions. New product evidence is reported with its own date, policy and denominator.

The mixed-question failure is retained as observed evidence, followed by separate bounded-fallback checks for mixed, wholly unsupported and ordinary questions.

## Verification and current limits

The final software gate passed all eight stages: 427 Python tests and 56 frontend tests, with 365 captured source files unchanged. The broader v8 execution met 106 of 110 main-case expectations, 13 of 14 teaching expectations and all six robustness expectations. The final v9 targeted regression met 35 of 37 expectations; two clarification deviations remain recorded. These are workflow observations, with independent ratings still open. The fresh CPU installation retains 48 sources, 10,594 vectors and all 80 bundled resources. Final source parity matches 407 safe source/configuration files. Actual queued and active cancellation, a three-attempt timeout and three CPU/CUDA retrieval comparisons are recorded. The mixed-question CPU path admits ten passages within 2,548 evidence tokens; its conservative mock answer still refuses the whole question. Live partial answering has a separate provider record.

Automated expected-behaviour checks can identify missing responses, invalid citations or incorrect workflow states. Independent scientific correctness, evidence entailment and learning benefit require additional judgement. Provisional topic screening keeps its original calibration scope until reviewed labels support a new threshold.

## Week 9 measurable goals

- Obtain independent relevance and source-coverage judgements for the frozen development groups, preserve disagreements and select a model-bound threshold.
- Freeze the resulting policy before held-out evaluation and publish complete denominators for false refusal, irrelevant acceptance, coverage and execution errors.
- Complete blinded teaching and claim-support reviews and physical-device acceptance, linking each observation to its source, request and actual test conditions.

## Dependencies

Hongle supplies source positions and difficult-page limits; Chengzhou supplies policy and retrieval traces; Sijin and Pengyuan define answer and teaching criteria. Zeping preserves failures and request identities, while Baiqing records visible recovery behaviour. Independent reviewers must complete the planned assessments before scored conclusions are drawn. Xianshu maintains the shared delivery sequence and evidence register.

## Evidence references

Paths are relative to the delivered project root.

- Integrated Week 8 implementation and research: `docs/execution/week08-delivery-20260916.md`

- Fixed source-backed question bank: `evaluation/reliability/week08_cases_v3.json`

- Current checks and execution records: `evidence/week08-delivery/20260916/`
