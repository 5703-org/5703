# Week 8 Module Report

Hongle Yang | Source provenance and exact unit mapping | 2026-09-20

## Domain outcome

The data domain supplies the immutable source identity needed to verify a cited fragment. The enhancement maps selected text back to the already processed official OpenStax sources without replacing originals, rebuilding the corpus for an artificial result or changing historical references.

Original accountable task IDs: DAT-01, DAT-02, DAT-03, DAT-04, DAT-05, DAT-06, DAT-07, DAT-08, DAT-09, DAT-10, DAT-11, DAT-12.

## Implemented changes

A source map carries document version, processing run, source unit, chunk identity and hashes. Each fragment uses Unicode character offsets into the exact cleaned source-unit text. Validation checks the slice and its hash, together with chunk spans and evidence identity. These positions describe processed text; they are not PDF glyph coordinates.

The mapper preserves complete formula, table, caption and recovered-image blocks where sentence splitting would remove necessary context. A clipped atomic block cannot certify a claim. Ordinary prose can remain usable around a mathematical expression, rather than making an entire flattened page indivisible because it contains an equals sign.

The retained raw extraction and its hash provide a narrowly bounded heading seam for flattened source text. The seam is accepted only when the adjacent content matches the cleaned text exactly and uniquely. Ambiguous mappings retain a coarse fallback. This supplies traceability while preserving the original processing records and source warnings.

## Interfaces and dependencies

Chengzhou consumes the same immutable source map for all selection strategies. Sijin checks claims against validated fragment identities. Zeping repeats identity and visibility checks at persistence and source access, and Baiqing renders only the approved text. Shared source files are dependencies and do not imply separate duplicate implementations by each owner.

Implementation and dependency paths: retrieval/source_spans.py; backend/app/modules/learning_state/sources.py; backend/app/modules/knowledge/service.py; docs/execution/openstax-corpus-report.md.

## Current verification

Published source previews averaged 4,253.6, 1,223.4 and 799.6 characters for whole passages, post-generation spans and preselected spans. These lengths describe each method's successful outputs; the methods published different subsets. Exact slicing and source identity passed for the published projections.

The attribution audit reads the exact source units used by the frozen 180-request comparison. Published projections passed the structural checks, while rejected outcomes preserve source and citation mismatches for inspection. The audit also found 64 source-linked answer-text claims lacking a marker local to that claim, and incomplete selected blocks in some paragraph and post-generation results. These observations separate correct byte identity from the completeness of a scientific explanation.

The source investigation keeps five deterministic excerpts with book, chapter and physical PDF page identifiers, plus three concrete problem examples. The preserved corpus remains the reference for both full context and highlighted slices. In the user interface, a hint's ordinary source preview stays restricted until an explicit expansion event rechecks permission; this makes source preparation part of the teaching contract. Week 9 review can return directly to those positions to judge lost conditions, table structure or misleading local context.

| Matched record | Accounted | Planned |
| --- | --- | --- |
| Direct answers and attribution | 180 | 180 |

Independent human ratings recorded for this checkpoint: 0. Prepared review materials are ready for the group's two reviewers.

## Failures and limits

An exact processed-text slice proves identity, not scientific correctness or complete visual recovery of the PDF. Full equation and diagram fidelity, difficult recovered content and independent claim judgments retain their recorded limitations. A structural candidate remains unverified until its separate support assessment.

Prioritise the incomplete-block examples and formula/table context for two independent reviewers. Record whether each span supports its linked claim and whether necessary conditions remain visible. Preserve the current processing identities while any later parser revision is evaluated separately.

## Module operation

- Open a cited claim and compare the displayed fragment with its saved evidence and source-unit identity.

- Check a formula or caption boundary and confirm that an incomplete block is labeled or rejected rather than certified as complete support.

- Use the existing per-book report and retained original file hashes when tracing a historical answer; do not rebuild or rewrite its source record.

## Week 9 actions

- Review disagreement cases involving atomic boundaries, headings and recovered image text against the retained originals, recording exact positions and reasons.

- Measure fragment correctness and coverage using the frozen citation comparison and independent ratings, keeping coarse or unsupported cases in the denominator.

- Propose any additional parser change as a new processing version with a before-and-after provenance comparison; preserve all referenced historical versions.

## Accountability and evidence

These are accountable project domains from the original team allocation. The implementation and verification cited in the reports were performed through the shared project workflow. Domain ownership does not establish a personal commit, individual execution, independent review or personal authorship. Actual execution record: Codex performed the shared implementation, scripted execution and document preparation. Named members remain the accountable module owners. Independent reviewers have supplied 0 ratings.

Independent structural attribution audit. Exact source relationships and published-only length measurements. Semantic fields from its original judge are excluded here.

evidence/week08-enhancement/20260920/formal-attribution-audit.json

SHA256 aff7b205881e13565688ff455d70bf09abef738cd1722680fbcb7d102504c3e5

Corrected direct-answer citation analysis. Same 180 generated outcomes with corrected direct-answer judging; the original judge is retained.

evidence/week08-enhancement/20260920/formal-citations-judge-v2-analysis.json

SHA256 6aec13d0175ce4f7be47d2f78bf125e405fb82bda94cdf6ac12edb3e4f4c2dd5

Claim source browser journey. Actual approved preview, explicit expansion, keyboard and 1440/390 viewport checks.

evidence/week08-enhancement/20260920/frontend/live-source-browser-summary.json

SHA256 33d81448493b3c9125b5b71d632626ad4c1f837b4a944b9d6044530a63ea9b14
