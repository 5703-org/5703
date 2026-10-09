# Personalised AI Learning Assistant Using Retrieval-Augmented Generation and Large Language Models

## Week 8 Module Report

Pengyuan Xia | SID 550267474 | Personalisation and Learning Policy

## Week 8 outcome

The personalisation workstream translated explanation-level, length, hint and misconception research into the interactive teaching policy. Existing profiles and versioned compilation remain the base, while new generation controls make instructional choices explicit in the request trace. The accountable scope is PER-01 through PER-09 and CHAT-07.

Saved preferences describe presentation needs. Scientific preservation, helpful guidance and later independent reasoning have separate evaluation criteria.

## Teaching implementation and integration

The new interactive teaching plan provides beginner, intermediate and advanced explanation guidance. Current-turn requests can shorten or simplify an explanation while preserving the saved profile. Hint mode supplies a next step and reserves the compact answer; misconception mode checks the premise against evidence before correcting it.

The generation validator routes a hint answer leak through the existing finite repair budget. The administrator trace exposes level, style and teaching mode alongside evidence and coverage observations. This makes the applied policy inspectable without revealing private prompts or credentials.

The assigned generation/teaching.py module compiles levels, preferences, turn overrides and hint guidance; Sijin integrates it with answer generation and validation.

## Pedagogy research and review design

The research separates factual preservation, complexity, length, hint usefulness and treatment of misconceptions. A shorter response can omit a necessary condition, while a longer response can add unsupported material. The review therefore uses source support and instructional usefulness as distinct dimensions.

The earlier three-question study retains its 27 C0/C1/C2 outputs and blank independent ratings. The new Week 8 teaching schedule exercises the integrated behaviours. Blinded ratings, an unaided transfer task and a delayed assessment provide the planned route from visible output differences to learning evidence.

The mixed-question correction preserves partial source support for teaching while keeping unsupported requests visible in the complete learner question.

## Verification and current limits

Teaching rules, turn overrides and hint-leak repair are covered by the expanded generation checks. The final software gate passed all eight stages: 427 Python tests and 56 frontend tests, with 365 captured source files unchanged. The broader v8 execution met 106 of 110 main-case expectations, 13 of 14 teaching expectations and all six robustness expectations. The final v9 targeted regression met 35 of 37 expectations; two clarification deviations remain recorded. These are workflow observations, with independent ratings still open.

The source-based AI review of 14 teaching outputs flagged seven cases for qualifications or completeness. One hint supplied the central answer despite a null compact field. The implemented field guard therefore has a narrower scope than semantic hint restraint. Independent human ratings remain pending.

## Week 9 measurable goals

- Apply a rubric separating scientific preservation, level, concision, hint usefulness and misconception correction to the fixed outputs with blinded independent reviewers.
- Record reviewer agreement, disagreements and missing ratings, keeping the condition key separate from review assignments.
- Prepare one source-backed transfer or delayed task with prespecified allocation, participant arrangements and a complete analysis denominator.

## Dependencies

Sijin supplies the answer and hint behaviours, Hongle the source coverage and Chong the blinded protocol. Baiqing must show the saved preference and support states clearly, while Zeping preserves profile versions and study outcomes. Actual reviewer availability and participant arrangements determine which studies can proceed. The implementation can retain these explicit limits while the review materials are prepared.

## Evidence references

Paths are relative to the delivered project root.

- Integrated Week 8 implementation and research: `docs/execution/week08-delivery-20260916.md`

- Fixed source-backed question bank: `evaluation/reliability/week08_cases_v3.json`

- Current checks and execution records: `evidence/week08-delivery/20260916/`
