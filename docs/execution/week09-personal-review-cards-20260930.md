# Week 09 personal review cards in the due queue

Personal notes with `kind=review_card` now enter the existing learner review queue at creation. Existing cards receive additive due-now queue entries when migration `f5b61c9247de` runs. That migration leaves the original note text and revision unchanged. Every review row has exactly one target: a published practice item or an owned personal card. The old practice-item queue behavior and saved attempt records remain in place.

The queue labels each target type. A card carries its own saved content and, when present, its frozen source locator. The learner can reveal their personal card content, then record `recalled` or `needs_review`. This is a self-report: the server creates no graded practice attempt or mastery claim. A first reported recall schedules another review in two days, subsequent recalls use four, eight and up to fourteen days, and reported difficulty schedules one day. The due date, counts and plain-English reason are returned with a version; stale repeats cannot count the same card twice. The existing manual rescheduling control remains available. Empty new cards are rejected because there is no content to reveal; older empty cards retain their saved records and can be edited.

Queue reads and review actions recheck note ownership and any pinned textbook locator. A revoked or unavailable source-bound card is omitted from the queue and cannot be recorded or rescheduled while unavailable. Deleting a card also deletes its linked queue entry in the same transaction. Cards derived from notes without an explicit textbook locator remain labelled personal material. A saved answer reference must still belong to the same learner and an undeleted session; it does not turn a personal card into verified textbook evidence.

Verification on 30 September 2026:

- The scoped unit and disposable PostgreSQL integration run passed **23 tests**: `tests/unit/test_learning_note_export.py` and all of `tests/integration/test_learning_product.py`. The new integration cases covered due-now registration, owner isolation, version conflicts, self-reported intervals, source revocation, card deletion, and independent migration backfill. A separate rerun confirmed the existing note's title, content and revision were unchanged after backfill.
- The frontend suite passed **148 tests**. TypeScript checking and a production Vite build passed with an isolated output directory. The queue UI reveals personal content only on request, closes it after a successful action, and preserves the published-practice path.
- Scoped Ruff lint/format, mypy on `contracts/study.py` and `backend/app/modules/learning_product`, runtime OpenAPI parity, and generated frontend type parity passed.
- The test source was an authored, labelled fixture with a mock answer model. The scheduling rule is an operational reminder rule; learning effectiveness and retention improvement require separate human study.

No historical practice attempt, answer, citation, source file, embedding or corpus release is rewritten. A deployed instance requires the additive migration before its updated API and frontend are started.
