# Week 8 Work Report

Hongle Yang | 540252369 | 26 September 2026

Official sources, processing, quality and corpus publication

## Week 8 scope

This workstream covers all development after the verified Week 7 final release through the current teaching and performance continuation. All four complete official OpenStax PDFs, recovery artifacts and the 10,594-vector 384-dimensional corpus predate Week 8. Week 8 preserves these resources and extends their use in source verification.

Original allocation: DAT-01, DAT-02, DAT-03, DAT-04, DAT-05, DAT-06, DAT-07, DAT-08, DAT-09, DAT-10, DAT-11, DAT-12.

## Completed work across the week

Maintained original source/processing hashes while CPU query execution and versioned evidence reuse were added.

Introduced exact cleaned-source-unit Unicode spans, stable fragment hashes and provenance for claim-level highlighting; preserved coarse/atomic limitations for formulas, tables and captions.

Added conservative raw-heading corroboration, complete-block boundaries and exact source/given checks used by the revised checked-answer path.

Kept corpus/source visibility and historical citation identity intact through migrations, isolated imports and all eighty-resource release checks.

The official corpus remains four complete OpenStax books, 10,594 released chunks and 10,594 real 384-dimensional E5 vectors. This continuation reimports the verified bundle into an isolated PostgreSQL instance and checks original-file, source-unit, chunk and vector identities.

Current selected sources are reloaded before answer publication. Transactional invalidation prevents reuse after source or release changes. The reference/cache comparison checks all four PDF hashes and database fingerprints before and after its complete schedule.

## Verification and findings

All 98 real PostgreSQL observations completed. The 48 warm reference/cache pairs return identical candidate and reranked content and scores. Database, chunk, vector and all four PDF fingerprints remain unchanged. Source invalidation, direct corruption, rollback and publication concurrency have passing checks. Diagram and formula sufficiency remain specific source-review tasks.

## Personal code package

The package contains the complete current versions of this workstream's cumulative changed files, with repository paths and a baseline/current hash inventory. The personal DOCX matches the standalone report byte-for-byte. The shared implementation and automated verification were performed through Codex; the named member owns the review, explanation and submission of this workstream.

Selected current file areas:

pipelines/

backend/app/modules/knowledge/cache.py

backend/app/modules/learning_state/sources.py

docs/execution/openstax-corpus-report.md

## Week 9 goals

- Review formula, diagram, table and caption questions against the original pages and record specific extraction losses.

- Prepare independent source-support labels for the retained teaching cases.

- Test source withdrawal and restoration under a second deployed environment while retaining historical citation access rules.

## Evidence

docs/execution/teaching-performance-20260926.md

evidence/teaching-performance/20260926/pg-retrieval-paired-final/summary.json
