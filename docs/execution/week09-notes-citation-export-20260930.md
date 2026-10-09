# Week 09 saved-answer citation export

The personal-notes Markdown and DOCX exports now identify the textbook sources actually cited by a saved answer. Each currently visible citation includes its book title, edition, section, source page or physical PDF page, frozen corpus release, document/version/processing/chunk/evidence locator, original-file SHA-256, cited-chunk SHA-256, license, and source URL when the presentation permits it. Both export formats use the same backend text, so their source lists cannot diverge through separate formatting logic.

Export reads the published `Citation` rows and intersects them with the answer's published citation IDs. For controlled teaching presentations it further restricts the list to the currently visible citation views; hint presentations do not export a source URL that the presentation withheld. Before showing source metadata, export rechecks answer ownership and session visibility, document activity and revocation, workspace ownership, membership in the answer's pinned corpus release, document-version linkage, and the saved evidence's exact text and hash against the frozen chunk. Unavailable citations receive a generic marker while the user's own note remains available. It does not read or include `PrivateAnswerDraft` records or uncited retrieval candidates.

Validation on 30 September 2026:

- `tests/unit/test_learning_note_export.py`: 2 passed. The checks cover metadata line folding, actual citation identity, page/version metadata, revoked and cross-owner suppression, withheld hint URLs, and private payload omission.
- `tests/integration/test_learning_product.py`: 19 passed against a newly created and removed `cs30_test_*` PostgreSQL database on the established isolated test server. The added case checks Markdown and DOCX output, actual versus uncited evidence, owner isolation, saved private-draft exclusion, and revocation after export. The fixture uses an explicitly authored test document and mock answer model.
- Scoped Ruff check and format check passed for the changed service and tests.

This check establishes export behavior and source authorization for the tested application path. It does not claim a fresh OpenStax end-to-end export run or semantic correctness of the cited answer. Existing saved notes and answers were not rewritten.
