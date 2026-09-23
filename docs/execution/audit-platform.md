# Platform audit and current closure evidence

## Current local closures, 8 September 2026

The initial inspection below is retained as history. Its six findings now have concrete implementation and execution evidence:

| Original finding | Current change and observed validation |
| --- | --- |
| Regeneration budget | New revisions inherit configured call/time caps while resetting only consumed counters. `test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked` verifies a lower configured limit on actual PostgreSQL. |
| Generic benchmark retry | Product retry is limited to interactive requests; the same integration test rejects benchmark retry outside the frozen evaluator lifecycle. |
| Sensitive exception logging | Application errors record a safe class/event/trace identity without raw SQL/provider exception content. `test_error_log_safety.py` exercises representative sensitive payloads. A full-suite discovery also fixed Alembic disabling the existing application logger; the ordered migration/log check is retained in `evidence/integration/migration-logging-order.log`. |
| Concurrent account/feedback insertion | Actual concurrent requests now produce a deterministic account conflict or reuse the one feedback record. Two PostgreSQL contention tests cover both results and continued administrator review. |
| Missing static/CI path | Format, lint, boundary typing, contract checks and deliberate-error rejection probes execute in the aggregate gate. The guarded CI database setup and pinned workflow are present; hosted CI has not been run. See `docs/development_checks.md`. |
| Incomplete restore fingerprint | Backup-v2 fingerprints full user/profile values and complete corpus/vector records. Both Windows and portable distinct restores passed; actual Linux E5 retrieval against the portable restore matches Windows source hits. See `evidence/recovery/backup-real-openstax-20260908/` and `evidence/e5-container/runtime-verification.json`. |

Current exact test nodes, run dates and source snapshots are in the canonical task/check records and `evidence/final/`; a gate with source drift is not a final stable pass even when each check passes. The externally triggered Docker interruption and subsequent existing-volume recovery have their own evidence in `evidence/recovery/docker-interruption-20260908.json`. Compose restart policies now cover long-running services when deliberately updated; they do not silently repeat uncertain paid executions.

## Preserved first inspection

The user reprioritised source/document reconciliation and the complete official corpus before this broad platform audit finished. These are source-inspection findings reported to the integration owner, not reproduced exploit results or a complete platform acceptance report. Subsequent repairs require their own affected tests; do not silently treat this snapshot as a final exact-build audit.

| Finding at inspection | Affected scope | Required closure |
| --- | --- | --- |
| Latest-answer regeneration constructed a default `RequestBudget()` rather than applying the initial configured request bounds. A request originally limited below defaults could receive a larger allowance. | BE-13, GEN-06, CHAT-08, AC-11/25/45 | Reuse the configured budget policy for new revisions and prove lower configured call/time limits survive regeneration and retry. |
| Generic answer retry eligibility did not visibly restrict terminal benchmark requests to the frozen evaluator lifecycle. | BE-08/11, QA-06/11, AC-24 | Restrict product retry/regeneration to interactive requests or explicitly reconcile frozen evaluator outcomes; test no post-score rerun via generic answer controls. |
| Generic exception handling logged the raw exception string; the JSON formatter did not independently redact it. SQL/provider exception strings can include sensitive bound content. | BE-13 | Log a safe error class/event and trace ID, keep public envelopes generic, and test representative sensitive exception payloads. |
| Initial account/feedback existence checks followed by inserts may race on uniqueness; concurrent first insertion was not established by existing sequential successes. | BE-03/10/15, AC-12/32 | Use deterministic conflict/idempotency handling and targeted actual PostgreSQL concurrency verification. This is an inspection risk, not a reproduced failure. |
| Full format/lint/Python-type checks and a CI workflow were not present in the inspected aggregate verification path. | INT-05 | Add/run the intended lean checks or accurately identify their remaining implementation status. |
| Restore fingerprints checked every table's row count and selected content hashes, but did not demonstrate full-value equality of user/profile records. | BE-16, AC-20 | Preserve existing successful restore evidence and add explicit identity/profile-value comparison if claiming that stronger requirement. |

Observed safeguards: actual repeatable-read database snapshots and hash-verified raw copies; restore rejects existing/source database and nonempty/same storage targets; cleanup is a reviewed, age-bounded plan that validates paths, current references and content before deletion; ingest and cleanup share an advisory lock; cancellation/publication use row locks and persisted fences; development account seeding is explicit and environment guarded. These implementation observations do not replace recovery/fault tests.

Existing executed evidence: `evidence/integration/postgres_lifecycle.log` records six PostgreSQL chat checks; `runtime_faults.log` records nine fault checks; `operations.log` records three operational checks. `faults-operations.log` is another overlapping run and must not be added as independent coverage. `evidence/recovery/backup-20260908-verified/restore-cs30_restore_20260908.json` records a successful disposable restore of one authored release, three users, 29 answers and 73 evidence snapshots. Its scope is local recovery of that recorded fixture database, not full official-corpus restoration. `evidence/recovery/clean-chat.json` records the separate clean Compose chat rehearsal with mock providers.

No final task-completion claim is made. The current priority and first-pass ledger are in `source-architecture-audit.md`, `tasks.json`, and `acceptance.json`.

## Preserved 09:09 stable-source regression before final review

The complete gate executed from 09:08:54Z to 09:09:59Z on 8 September 2026 and passed all stages with no source changes: 223 Python checks, 23 frontend checks, Python formatting/lint/boundary typing and deliberate-error rejection probes, generated contracts/client checks, frontend types and production build. [Gate](../../evidence/final/software_gate.json), [source snapshot](../../evidence/final/source_snapshot.json), [JUnit](../../evidence/final/pytest.xml). The earlier 222-test run with an aggregate source-drift failure remains under `evidence/final/attempt-source-drift-0825`; it is not substituted for this final pass. Two dependency deprecation warnings remain in the Python log, without failed checks.

## Current final regression and installation

The final post-review gate completed at 2026-09-08T09:30:59Z with 231 Python checks and 23 frontend checks, all static/type/contract/build stages passed and no source changes. Added coverage exercises fixed chunking and authoritative evaluator stage timing. The second candidate source package then passed fresh no-cache Compose builds, an empty database, migration/seed/source lifecycle, four-turn software outcomes, feedback/history and actual 1440/390-pixel browser checks. [Candidate proof](../../evidence/handovers/candidate-20260908T093208Z/verification.json). It records three cited mock answers and one explicit practical-example mock refusal; that limitation is preserved. The first candidate's old four-answer assertion failure is not erased.
