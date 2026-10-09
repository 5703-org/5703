# Learning Workspace Backend

This is the Week 9 learning-product implementation record. It describes the new backend slice and its focused checks; it does not replace the integrated release gate or semantic evaluation.

## Sources and persistence

The library reads the active released corpus and filters documents by the authenticated workspace, active state and revocation state. It presents the retained cleaned source units with processing identity, physical page, Unicode offsets, exact text hash, original source link and license. It does not rebuild or replace the existing corpus.

A reading question freezes the current release, authorized chunk IDs, document and processing identity, optional chapter, and the exact selected text range. Selected chunks are admitted through their retained source spans, without a second embedding query. The answer orchestrator rechecks the frozen context at execution and publication. A changed active release does not silently replace an already frozen source. Revocation remains authoritative.

Migration `f3d97fa0456e`, following `f2c86e9f345d`, adds nine tables: `reading_positions`, `study_goals`, `study_goal_units`, `practice_items`, `practice_progress`, `practice_attempts`, `study_review_entries`, `study_notes` and `learning_records`. It changes no existing table or source row. The migration was exercised in a newly created disposable PostgreSQL database; the original application database was not migrated by this implementation task. The subsequent authorized main migration followed a verified backup and clone rehearsal; its [preservation receipt](../../evidence/week09-continuation/20260930/main-migration-preservation.json) confirms unchanged source/corpus identities and all compared historical answers/citations.

## Learner workflow

The `/learning/library` routes provide textbooks, chapter search and paginated source units. Supplying `source_unit_id` resumes at the containing page of units. Reading positions use an expected-version fence and persist across sessions. Section learning objectives are extracted only from explicit publisher objective headings when the words also occur in the retained cleaned source. Section titles provide the initial concept labels; adjacent sections provide navigation. These are not a validated semantic knowledge graph.

Goals select real sections and a learning depth. Their units retain suggested section-order prerequisites, explicit reading marks and actual linked practice counts. Recommendations distinguish reading, practice, review and related practice. Reading or disclosing an explanation does not establish mastery, and no mastery percentage is generated.

Published practice supports single choice, multiple choice, short explanation, numeric value and unit, and multi-step tasks. Numeric checks use an explicit unit table, dimension checks, finite conversion and saved tolerances. They execute no user expression, code or shell. Short explanations use saved acceptable expressions, knowledge-point alternatives and forbidden statements; their result explicitly leaves independent semantic correctness unverified. Structured numeric and textual feedback records missing points and error categories.

Step practice exposes only the current prompt, response type and optional unit. A correct current-step attempt can advance the task; partial, incorrect, insufficient or irrelevant attempts retain the step. Hints and full explanations are explicit disclosures with their own revision changes. Requesting an explanation does not mark the task completed.

Every attempt retains its item revision, response, deterministic feedback, idempotency key and progress revision. A duplicate key with the same body returns the original receipt; a changed body conflicts. Per-owner locks and expected versions serialize concurrent submissions. A question successor leaves previous items and attempts intact.

Review entries use transparent intervals: an unsuccessful attempt is due after one day; correct attempts increase the interval up to fourteen days. The queue includes the latest three attempts' error counts and can suggest a different published item with an overlapping concept. These are inspectable scheduling rules, not calibrated knowledge tracing.

When learning memory is enabled, an attempt can create an assessment-performance memory linked to the exact owned practice item and attempt. It contains the outcome and grading method, not the private answer key. It explicitly does not establish general mastery. The existing memory editor, deletion and opt-out controls remain authoritative.

Notes and bookmarks can reference an owned answer, a currently visible exact source range and an owned goal. They remain personal learning material. Markdown and text-only DOCX exports include available textbook provenance. If a source is revoked, the personal note remains while its source link is withheld and the export identifies the unavailable source. Note edits and deletion require the current version; note deletion events retain the identifier without copying the deleted body.

## Administration and answer-key boundary

`/admin/learning/practice` is administrator-only and workspace-scoped. Saving creates an immutable draft. Structural and source-identity validation produces issue codes. Publication requires that exact validated version and explicit publisher confirmation of source support, conditions and solvability. Structural validation is not an independent scientific review. Changes create a successor revision; retirement stops new learner access.

The internal `create_proposed_item` seam accepts a frozen `PracticeProposalInput`, a complete generated `PracticeDraft` and safe model provenance. It verifies unchanged source and requirements, then creates an unpublished, unreviewed draft. This seam itself makes no provider calls. The integrated proposal producer preserves the normal validation and publication boundary. Its separate real development observation retained two objective-only quality failures and one substantive-source validated draft, with publication still awaiting explicit review; see the [current continuation record](week09-learning-continuation-20260930.md).

Learner item, progress, attempt, review, note and record routes do not project `private_rubric`. Only explicit full-explanation disclosure returns the worked explanation. Private keys are not added to textbook source units, retrieval indexes, learner memories or exports. Administrator responses expose validation issues and private grading rules for review.

## API contracts and checks

The canonical HTTP DTOs are in [contracts/study.py](../../contracts/study.py). Implementation is in [learning_product](../../backend/app/modules/learning_product/). The additive routes are included in the generated OpenAPI specification. The scoped chat contract and worker enforcement are integrated by the answer-core module, rather than a second answer engine.

Focused evidence is recorded in [backend verification](../../evidence/week09-learning/20260930/backend/verification.json), with separate unit and actual PostgreSQL assertions in [test_learning_product_grading.py](../../tests/unit/test_learning_product_grading.py) and [test_learning_product.py](../../tests/integration/test_learning_product.py). Initial setup and lock-query failures remain in the dated attempt logs. Tests use an explicitly authored fixture corpus and mock answering; they do not certify educational effectiveness or independent correctness of published questions.

The current continuation has separate actual isolated-browser and real-provider development receipts in the [integration index](week09-learning-continuation-20260930.md). Deployment/recovery and aggregate release evidence remain separate. These later observations do not change the 35-check backend checkpoint or imply a main-database migration by its tests.
