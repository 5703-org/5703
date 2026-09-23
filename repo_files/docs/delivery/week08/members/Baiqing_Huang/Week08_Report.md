# Personalised AI Learning Assistant Using Retrieval-Augmented Generation and Large Language Models

## Week 8 Module Report

Baiqing Huang | SID 540976443 | Frontend and User Experience

## Week 8 outcome

The frontend workstream implemented a compact expandable administrator processing trace while preserving the concise learner conversation. A request can be found by ID or by its recorded outcome, including successful answers. The accountable scope is FE-01 through FE-12 and CHAT-06.

The new view follows the original question through understanding, evidence selection and the saved response. Its purpose is to make cases such as the RAG and ragweed failure diagnosable using actual persisted observations.

## Interface implementation

Failures.tsx now displays the standalone question, intent, topic relationship, clarification and correction details. The expandable panel also shows the frozen source release and model, resolved device, excluded passages, source reuse, teaching mode and measured timings. Missing historical values remain visible as unrecorded.

Four count boundaries distinguish candidates before relevance, passages surviving the filter, passages submitted to the model and sources actually cited. Candidate admission may combine fresh retrieval and verified earlier passages. Request lookup preserves actual loading, failure and permission responses.

The keyboard-accessible source selector defaults to Textbook sources. General knowledge displays a saved model-origin label, suppresses textbook sources and retains its mode with a failed draft.

## Research translated into interaction

The learner flow keeps clarification, insufficient support and operational errors readable, with cited sources available for inspection. The administrator view exposes the detail needed for investigation inside a collapsed section, using wrapping identifiers and a narrow-layout grid.

Lexical coverage and citation-locality flags are labelled as automated observations. Independent support and teaching review remain separate. The underlying API projects safe fields, and existing administrator and workspace restrictions protect access to other records and private evaluator content.

The trace now includes optional per-part fallback details, separating whole-question rejection from each part’s query, scores and final evidence counts.

## Verification and current limits

The final software gate passed all eight stages: 427 Python tests and 56 frontend tests, with 365 captured source files unchanged. Real saved-request browser checks passed at 1440 and 390 pixels for expandable traces, per-part fallback, source-mode selection, saved provenance and reload. Keyboard expansion, focus containment and Escape passed; all saved histories stayed unchanged.

The earlier CPU browser proof covers saved sources, Escape, reload and 390-pixel navigation. The new real administrator trace check records desktop and narrow-layout behaviour. Physical soft keyboards, native composition, assistive technology and independent usability review remain explicit device-based work.

## Week 9 measurable goals

- Review real partial, conflicting, clarification and failed responses with representative users, recording comprehension and the next action they choose.
- Complete physical keyboard, composition, mobile resize and assistive-technology checks with named devices and reproducible interaction conditions.
- Refine trace wording and learner support states from observed usability issues while preserving endpoint behaviour, focus return, source inspection and draft recovery.

## Dependencies

Sijin defines the answer-support modes, Zeping the safe trace and error contract, and Chengzhou the prepared-query and evidence-selection fields. Pengyuan supplies the teaching and preference requirements. Chong helps select failure cases and acceptance evidence. Xianshu coordinates implementation order so the interface can reflect stable server behaviour and the delivered package's actual runtime.

## Evidence references

Paths are relative to the delivered project root.

- Integrated Week 8 implementation and research: `docs/execution/week08-delivery-20260916.md`

- Fixed source-backed question bank: `evaluation/reliability/week08_cases_v3.json`

- Current checks and execution records: `evidence/week08-delivery/20260916/`
