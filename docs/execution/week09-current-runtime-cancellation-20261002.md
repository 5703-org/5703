# Week 9 installed cancellation regression — 2 October 2026

The current 834-input candidate has an installed running-cancellation defect. An owner submitted a native Stop request after the worker acquired its execution lease. The API returned HTTP 500. PostgreSQL recorded `40P01 DeadlockDetected`. This outcome blocks the cancellation and recovery acceptance scope until a repaired candidate completes the same workload.

The isolated runtime used the current installed source, real CPU retrieval resources and a freshly restored PostgreSQL database on port 16549. Its model mode was explicitly `mock`; provider calls were zero. The existing Main and earlier installed services, environment files, official originals, embeddings and historical learner records remained protected. The installation and database-restore receipts retain their separate successful scope.

## Actual failed workload

| Operation | Observed outcome |
| --- | --- |
| Health, database readiness and frontend index | Actual local checks passed. |
| Queued Stop | Passed; no execution lease and no published answer. |
| Running Stop | Attempted and failed with HTTP 500 after an actual worker lease. |
| Controlled running Stop | Unexecuted after the preceding failure. |
| Crash, natural stale recovery and explicit retry | Unexecuted after the preceding failure. |
| Three concurrent requests | Unexecuted after the preceding failure. |
| Request accounting | All 19 attempted HTTP calls recorded. |
| Retained state | All original rows and columns in 65 tables preserved; the finite new-row audit passed. |
| Temporary accounts | Both new accounts deactivated; old accounts unchanged. |

The PostgreSQL server log at 01:37:23.411 UTC identifies the two waiting statements. The cancellation transaction waited on `SELECT jobs ... FOR UPDATE`. The worker transaction waited on `UPDATE answer_requests SET trace, updated_at ...`. These are the observed statements; the exact lock path must be confirmed by the source repair and a real PostgreSQL reproduction. A proposed session-before-job lock order is being tested. Existing commits before local embedding and reranking must continue to release locks, and every later write must recheck the durable execution token.

The first startup attempt stopped before HTTP because its process observer rejected a normal direct Windows console child. Its failed receipt remains. A narrowly reviewed observer successor admitted the exact console executable, hash, parent and command. The failed attempt's newly started API family was then observed fully exited; all twelve protected service roots remained unchanged. This operational correction supplies no cancellation pass.

Evidence: [actual running-Stop failure](../../evidence/week09-continuation/20261001/current834-running-cancel-deadlock-20261002.json), [first startup failure](../../evidence/week09-continuation/20261001/current834-mock-first-start-failure-20261002.json), [current installation and database restoration](week09-current834-installation-and-restore-20261002.md). Exact private terminals and the bounded PostgreSQL log are retained under `E:/5703/week09-private-db/current834-cpu-cancellation-preparation-20261002/`.

## Required successor

Reproduce the lock cycle on a disposable PostgreSQL database, review the smallest repair, run the unified software gate, and install the resulting source without changing resources or historical records. Repeat queued and running Stop, controlled process cancellation, the native 240-second stale recovery, explicit retry and the concurrent workload. Record all failure and successful scopes before updating the release pointer.
