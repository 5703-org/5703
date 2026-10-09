# Source-bound practice model assessment — 3 October 2026

New short responses and text-valued practice steps receive one real-model assessment against their exact saved OpenStax selection, question, conditions and current-step criteria. Choice, multiselect, numeric and numeric-step grading keep their exact rules. The active saved checker configuration supplies the service; the saved answer role is the configured fallback. Missing, simulated or failed services leave the work pending review.

## Saved work and progress

The submission commits its original response and immutable pending feedback before model transport. An append-only reservation records the source, item, response, progress and configuration identities. No owner or progress lock is held while the model runs. The single call has a locally counted context limit, a maximum of 4,096 output tokens and a maximum sixty-second deadline. The source excerpt and criteria cover the current question or step; future steps, authored hints and worked explanations stay outside this payload.

An applied result has a separate assessment receipt. It supplies effective feedback to practice, goals, tutor snapshots, review totals and optional practice memory. Late results are checked against ownership, source visibility, item revision, selected and linked goals, progress and disclosure state. Changed authority leaves the result superseded. Service, output-contract, cancellation and application failures retain pending work with the current learning step unchanged. Progress revisions record submissions separately from successful learning advancement.

The model judges meaning, contradictions, conditions and units. A correct contract requires supported criteria, source sufficiency, covered required points, preserved conditions and no reported contradiction. This contract validates the assessment structure; source-backed quality testing and independent scoring have their own results. User-visible messages come from the server. History projections omit raw prompts, model output and provider secrets. Model-assessed memory retains its assessment identity and explicit verification provenance.

## API and user interface

PracticeAttempt keeps immutable feedback and adds an optional assessment with id, status, method, feedback and applied_progress_version. Only status applied supplies the effective grade. Pending and superseded attempts keep the input available. Goal summaries expose graded_attempts and pending_attempts; review totals expose graded_count, pending_count, recent_graded_count and recent_pending_count. Recent errors use the latest three graded attempts. The recent pending count uses the latest three recorded attempts.

Practice, plans and the Memory attempt viewer show the effective result and its scoring basis. Historical keyword outcomes retain their recorded method. Pending work contributes to recorded activity and has no applied grade or new graded-performance memory. Current contracts and generated frontend types contain the new fields; the database uses existing attempt, progress and append-only learning-record tables.

## Current verification

The author passed 54 pure checks. Independent PostgreSQL/API verification passed 27 cases for reservation visibility, released locks, duplicate and concurrent submissions, late authority changes, rollback, safe history and effective-feedback consumers. A distinct V3 successor passed ten cases: seven changed legacy cases, one actual adapter CancelledError control and two grade-application Exception/CancelledError controls. Each database run created and removed its own random test database. These calls used scripted adapters. The frontend passed 32 practice/plan cases and 21 Memory cases with TypeScript validation.

Exact retained source/key material was also replayed through scripted-label and unavailable-service wiring controls. The original eight contradiction probes and their historical lexical false positives stay preserved. The real DeepSeek source-bound assessment trial and the current complete software gate are separate running work. Human scores remain zero.

The source implementation is in backend/app/modules/learning_product/practice_assessment.py, with submission and application consumers in service.py, router.py and tutoring.py. The exported payload contract is contracts/study.py. The related independent API suite is tests/integration/test_practice_model_assessment.py. The project retains its four real textbooks, original vectors, historical answers and citations.


## Real practice assessment observation — 3 October 2026

Sixteen real DeepSeek calls and six deterministic controls completed against the fixed official-source development population. Model outcomes were six correct, two incorrect, two partial and six pending reviews caused by invalid evidence coordinates. All eight contradictory responses avoided a correct grade. This direct preparation/validation trial used unpersisted learning objects; real API progression, independent human ratings and source-disjoint quality evaluation remain pending. [Actual results and usage](week09-real-practice-assessment-results-20261003.md).
