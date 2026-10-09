# Personalised AI Learning Assistant Using Retrieval-Augmented Generation and Large Language Models

## Week 8 Module Report

Hongle Yang | SID 540252369 | Data Processing and Knowledge Base

## Week 8 outcome

The data workstream connected the immutable OpenStax corpus to question-level coverage and the new evaluation bank. Four books remain represented by 10,594 chunks and real 384-dimensional E5 vectors. The new bank binds 60 immutable passages across 30 topics and four books, with exact source positions available for review. The accountable domain remains DAT-01 through DAT-12.

Source availability and answer coverage now have separate records. A passage can identify a topic while leaving a requested mechanism, qualification or comparison unresolved.

## Corpus and source integration

The reliability changes operate at query time, preserving the original files, processing decisions and release identity. Source snapshots keep passage text and hashes unchanged when evidence is selected or packed. Earlier citations remain traceable to their saved source records.

Earlier passages can enter a new candidate set only after current visibility, frozen-release membership and exact source identity checks. Accepted candidates are rescored against the current question. Exclusions record unavailable sources, release mismatch or identity mismatch, making retrieval decisions inspectable. The delivery manifest records the exact assigned paths and file hashes for this report's accountable domain.

General-knowledge responses carry an explicit unverified model origin and empty textbook citations, preserving the boundary around the immutable source collection.

## Coverage research made inspectable

The 120-case bank includes standard science, conditional and partial support, cross-chapter relationships, formulae, units and figures. Developer expectations and blank independent judgement fields are separate. Knowledge-related variants stay in one split, allowing later source review without contaminating calibration.

The generation pipeline now records lexical requirement coverage and preserves source qualifications during complementary packing. Original PDF positions and extraction warnings remain essential for diagrams and equations. Independent reviewers can compare the exact page, extracted passage and response before marking scientific support complete.

The per-part fallback preserves source identity and the complete question, allowing source-backed portions to remain distinguishable from unsupported requests.

## Verification and current limits

The v8 source check matched all 486 citations across 130 main, teaching and robustness cases to persisted text, hashes and source locations. The separate v9 regression matched all 127 citation identities. These checks preserve provenance; independent reviewers still need to assess whether each cited passage supports the scientific claim.

The broader v8 execution met 106 of 110 main-case expectations, 13 of 14 teaching expectations and all six robustness expectations. The final v9 targeted regression met 35 of 37 expectations; two clarification deviations remain recorded. These are workflow observations, with independent ratings still open. Source review still requires scientific judgement, especially for graphical relationships and conflicting or incomplete passages. Automated lexical coverage supplies a review aid.

## Week 9 measurable goals

- Independently review the source bindings for the 30 standard cases and the partial, conditional and visually dependent categories; record exact page-based judgements.
- Resolve disagreements about complete, partial, absent and conflicting support with a documented reason and a retained source snapshot.
- Use observed failures to propose one versioned extraction or chunk-eligibility change, with a controlled comparison and preservation checks before a new release.

## Dependencies

Chong supplies the grouped evaluation schema and reviewer procedure. Chengzhou needs the same source positions to judge retrieval coverage, and Sijin needs them to assess claim support. Baiqing's source view must continue to expose the original page and extraction warning. Teacher availability and the actual source-review results will determine which visually dependent cases can enter a scored evaluation.

## Evidence references

Paths are relative to the delivered project root.

- Integrated Week 8 implementation and research: `docs/execution/week08-delivery-20260916.md`

- Fixed source-backed question bank: `evaluation/reliability/week08_cases_v3.json`

- Current checks and execution records: `evidence/week08-delivery/20260916/`
