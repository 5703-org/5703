# Personalised AI Learning Assistant Using Retrieval-Augmented Generation and Large Language Models

## Week 8 Module Report

Sijin Lu | SID 540627888 | LLM and Prompt Engineering

## Week 8 outcome

The generation workstream integrated complementary evidence, explicit support instructions and inspectable citation checks into the shared answer path. It also added teaching controls for explanation level, hints and misconceptions. The accountable scope is GEN-01 through GEN-11 and CHAT-05.

Unresolved ambiguity produces clarification. An all-rejected evidence set produces a grounded refusal with zero answering calls. A partial evidence set carries its recorded limitations into the answer prompt.

## Evidence and answer implementation

generation/evidence_budget.py retains complete passage text and source hashes under the 3,000-token evidence ceiling and whole-request budget. It removes exact or contained duplicates, keeps the top-ranked anchor and prioritises complementary request parts and qualifications. Each exclusion has a recorded reason.

generation/support_audit.py records lexical coverage and local citation review flags. Numeric, negation and condition checks highlight passages requiring attention. These observations remain distinct from independent entailment. Structural citation validation and saved evidence identities continue to protect the public response boundary.

General mode uses a separate prompt and provenance guard with empty textbook citations. Empty provider responses remain errors; a format reminder repaired the observed follow-up case.

## Teaching and failure decisions

Pengyuan’s generation/teaching.py compiles three explanation levels, turn-level length overrides, hints and misconception checks. The generation integration enforces a null compact answer in hint mode and uses the existing bounded repair for leakage. Source-conditioned instructions cover full, partial, absent and conflicting support.

The prompt states full, partial, absent and conflicting-support behaviour. Existing E0/E1 benchmark prompts and ranked packing remain frozen. An optional model-based understanding stage still requires a measured cost profile and an explicit timeout and invalid-format policy.

The bounded per-part retrieval correction retains the complete generation question, so a supported portion and an unavailable portion remain explicit in the response policy.

## Verification and current limits

The generation increment passed 118 focused unit checks, including 19 new evidence-budget cases, plus Ruff and mypy checks. The final software gate passed all eight stages: 427 Python tests and 56 frontend tests, with 365 captured source files unchanged. The broader v8 execution met 106 of 110 main-case expectations, 13 of 14 teaching expectations and all six robustness expectations. The final v9 targeted regression met 35 of 37 expectations; two clarification deviations remain recorded. These are workflow observations, with independent ratings still open.

The source-based AI review of 14 teaching outputs flagged seven cases for qualifications or completeness. One hint supplied the central answer despite a null compact field. The implemented field guard therefore has a narrower scope than semantic hint restraint. Independent human ratings remain pending.

## Week 9 measurable goals

- Review the fixed live outputs for claim support and citation completeness, retaining partial answers, refusals and failed requests in the denominator.
- Compare teaching levels, hints and misconception handling with blinded reviewers using the same source-backed question conditions.
- Use the recorded failures to prioritise one prompt or validation revision, then verify its benefits and false-refusal cost before a new held-out run.

## Dependencies

Chengzhou provides selected evidence and rejection reasons; Hongle supplies the source positions needed for claim review. Pengyuan defines instructional criteria and Chong manages blinded evaluation. Zeping must preserve failures and timing boundaries, while Baiqing maps agreed answer states into the learner interface. Independent reviewers and actual provider execution are required before claiming improved answer or teaching quality.

## Evidence references

Paths are relative to the delivered project root.

- Integrated Week 8 implementation and research: `docs/execution/week08-delivery-20260916.md`

- Fixed source-backed question bank: `evaluation/reliability/week08_cases_v3.json`

- Current checks and execution records: `evidence/week08-delivery/20260916/`
