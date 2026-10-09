# Week 9 lock ordering and current-message references — 2 October 2026

The current source contains two repairs identified by actual installed and source-grounded trials. Unified successor verification passed all eight stages with 2,776 Python tests and 182 frontend tests on 840 unchanged inputs. The previous 834-input source gate remains a dated passed baseline. Installation and runtime acceptance of the new source are in progress.

## Running cancellation and recovery

The installed Stop request returned HTTP 500 after a real worker lease. The [retained failure](week09-current-runtime-cancellation-20261002.md) binds the actual PostgreSQL deadlock log, all nineteen HTTP calls and successful preservation of every original row and column. Its queued Stop passed; later cancellation, recovery and concurrent cases were unexecuted.

An isolated PostgreSQL regression reproduced the waiting `UPDATE answer_requests SET trace ...` statement. The worker first flushed request state in the same transaction while holding the job. Native cancellation acquired the parent session and then waited for the job. The worker's later trace update formed the deadlock. A control with no preceding request update committed in both transactions.

The repair acquires the request's session before the job in initial preparation, post-retrieval preparation and provider-event persistence. Existing commits before embedding and reranking continue to release locks. The later stages recheck the execution token and running state before writing. Final answer publication retains its existing session/job fence.

Worker failure and interruption transactions use the same parent-first order. Stale recovery reads candidate identities, acquires available parent sessions in sorted order with `SKIP LOCKED`, then rechecks job state and the original cutoff before acquiring job locks. It keeps its single commit and native stale interval. Both memory invalidation paths acquire the affected session before changing request trace or cancelling a job. These changes introduce no database table or migration.

Twelve isolated real-PostgreSQL cases passed before integration. They include the reproduced old lock cycle, native owner Stop, retention of cancelled/retried history, recovery skipping an occupied session, one recovery after release, preservation of a fresh lease and the worker-exception/Stop race. The tests use labelled authored fixtures. The installed workload still needs its successor run, including the actual 240-second stale interval and concurrent requests.

## Complete current observations

The frozen development question described a breeding male stickleback attacking a red-bottomed object that did not resemble a fish, then asked what this illustrated about a fixed action pattern, its trigger and completion. Query V18 treated the relative-clause `that` as a missing discourse referent. The actual CPU preflight stopped with zero provider calls and preserved the Main database. The original question and failed preflight remain unchanged.

New `conversation_preparer_v19` delegates existing conversation handling to the unchanged V18 module. A bounded local rule retains a complete current observation followed by an explicit analytical request about a named subject. It records exact spans for the local relative clause, the observation reference and the named possessive referent. The full question, negation, conditions and comparison language remain verbatim. A supported current observation takes precedence over unrelated previous discussion.

Bare references, unnamed subjects, ambiguous possessives and uncovered forms retain the earlier handling. Clarification continues to require zero answer-model calls. New requests freeze V19; saved V18 requests keep their original dispatch. `question_requirements_v5` remains the requirement producer. Ordinary textbook answers, checker V5, memory V4, coverage-query off, source-relations off, four calls, 180 active seconds and the 3,000-token evidence budget remain the defaults and limits.

Twenty-seven pure reference cases passed before integration. Five new API/worker cases are part of the fresh unified gate. The rule establishes a retrieval input; source sufficiency, semantic correctness and citation support still have their separate checks.

## Integration and verification

The integrated change modifies nine existing files and adds six source/test files. The original query modules from V14 through V18 retain their exact bytes. Original source versions were saved before the cutover. The fresh gate used isolated PostgreSQL test databases and mock answer providers; quality checks, foundation and contract checks, all Python tests, frontend types, frontend tests and the production build passed. The 2,776 Python cases have zero failures, errors or skips; the two dependency warnings remain recorded.

[Actual software receipt](../../evidence/week09-continuation/20261001/software-gate-lock-v19-20261002-01/software_gate.json), SHA-256 `ad1857b9a89a66011a964bf00109c75fbea9bc5f2819bc082d1ad3f8b408dd49`; [exact source snapshot](../../evidence/week09-continuation/20261001/software-gate-lock-v19-20261002-01/source_snapshot.json), SHA-256 `59540f0dd19d2603326e3006169940a72260d43462a8429995a504563a36575f`. All 840 inputs remained unchanged during the run.

The next actual checks are the installed cancellation/recovery workload and the unchanged five-request G009 QA/A/B/C/D development trial under V19. The first-hint trial remains distinct from multi-turn tutoring and independent learning evaluation. Human scores and physical-device observations retain their separate required evidence.
