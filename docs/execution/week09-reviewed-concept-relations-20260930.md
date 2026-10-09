# Week 09 reviewed concept relationships in learning paths

## Delivered behavior

Learning goals continue to use the published textbook section sequence for their initial order. Their existing `prerequisite_unit_ids` are labelled `section_order_suggestion`. Adjacent entries from the section browser are also identified as `adjacent_section_order`; neither field asserts a semantic prerequisite.

Administrators can submit a proposed relationship of type `prerequisite`, `related`, or `confusion` for two sections in one released, workspace-visible textbook. A proposal includes concept names, a reason, an exact released source-unit locator, and a quotation that must match its selected character range. It remains quarantined from learner views. An administrator can review the proposal with an expected version and a written rationale. Approval requires an explicit source-support assertion and rechecks the released source and quotation hash. Rejected proposals remain recorded. The same administrator may propose and review; this is a traceable administrative review workflow, not independent scholarly validation.

An owned learning goal shows approved relationships only when both sections are present in that goal. Each learner-visible relationship identifies the type, concepts, reviewed reason, exact quote, SHA256, book, edition, section, physical source page, locator, source URL and review time. The administrator's review note and identity stay in the administrator response. At read time, the server rechecks workspace-visible release membership and the exact source unit. Revoking the document or changing the pinned text suppresses its relationship from learner projection while retaining the review record. These are advisory suggestions. Marking a section read records reading activity; it does not infer mastery.

Migration `f6c72db859ae` adds `study_concept_relations` after the personal review-card migration `f5b61c9247de`. It does not modify existing goals, practice attempts, notes, answers, citations, vectors, or corpus records. A downgrade refuses to remove populated relationship records. Generated OpenAPI and TypeScript API types reflect the new administrator routes and `GoalOut.reviewed_relations`.

## Verification boundary

- The dedicated relation integration tests passed **2/2** on a fresh, migrated disposable PostgreSQL database. They exercised quarantine, all three types, exact-quote rejection, approval confirmation, stale version rejection, owner/workspace isolation, review rejection, provenance in the learner projection, source revocation, and the reading-only status.
- The combined learning-product regression passed **25/25** Python tests on disposable PostgreSQL. The frontend suite passed **149/149** tests, including reviewed relationship display and original-source navigation. TypeScript checking, an isolated production build, scoped Ruff lint/format, scoped mypy, runtime OpenAPI parity and generated frontend type parity passed.
- The relation tests use an expressly authored, labelled biology fixture whose text contains the reviewed statements. They verify application controls; they do not validate an OpenStax concept map or learning effectiveness. No official OpenStax semantic relationship has been curated and approved by this increment. A real-source curation pass and independent subject review remain open before reporting any official relationship coverage.

The relation display has no effect on ordinary textbook chat, answer generation, E0/E1 retrieval definitions, or published source provenance. Historical student activity and frozen studies retain their earlier interpretation.
