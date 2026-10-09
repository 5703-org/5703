# Source maintenance locks and administrator workspace scope

The source-management successor separates short maintenance transactions from long-lived worker lane locks and authorizes document management within the administrator's workspace. The new and related regressions passed **87 tests, zero failures, errors or skips** against fresh disposable PostgreSQL databases on 1 October 2026. The [safe evidence record](../../evidence/week09-continuation/20261001/source-maintenance-workspace-regression-20261001.json) binds the actual source hashes, retained failures and results. This is scoped engineering verification; installed-runtime and final unified-gate checks remain separate.

## Observed lock failure and fix

The frozen V17/V8 source used advisory key `5703002` for source registration, release activation, orphan cleanup and corpus import. The split interactive worker holds the same key for its lifetime. A new disposable database reproduced the conflict through actual `service.ingest` and `_register_staged`: with the split-layout shared key `5703001` and exclusive interactive key `5703002` held on a separate connection, a 600 ms lock limit returned SQLSTATE `55P03` after 0.606875 seconds. No document, version or remaining upload file was created. The original source remained exact throughout that probe.

All four maintenance callers now take the same transaction-scoped key, `5703101`, through `app.platform_core.source_locks`. Worker layout and lane keys remain `5703001`, `5703002` and `5703003`; worker execution and lock observation code is unchanged. Eight new PostgreSQL cases exercise actual ingestion, activation, cleanup and import under held worker keys and under a competing maintenance lock. Worker-key cases complete; maintenance-key cases stop at the bounded lock limit before changing source rows or files. Import uses a clearly labelled authored fixture with validated mock-corpus rows in a second migrated test database. Its outcome is an import/locking regression, with no official-corpus or embedding-quality claim.

## Administrator source access

Document listing joins the source owner to the verified administrator's workspace. Detail, processing-quality and processing-diff routes check that same relationship before returning source metadata or text. Processing, visibility changes and explicitly submitted release processing IDs receive the same guard. The existing CLI visibility command passes its verified administrator to the guarded operation.

Both raw-hash duplicate lookup branches check workspace ownership before returning the existing document/version. A same-workspace administrator still receives the original duplicate IDs. A foreign workspace receives neutral `NOT_FOUND`/HTTP 404 without private title, document ID or source content. The globally unique raw hash and database schema stay unchanged.

Thirteen new cases pair foreign-workspace denials with legitimate same-workspace peer administration, and cover list/detail/quality/diff, five mutation paths, early and protected duplicate rechecks, learner role denial, CLI compatibility and shared published-corpus retrieval. Denied paths preserve every table-row hash and the fixture's complete source-file hash map. The protected duplicate race is exercised through a deterministic initial-read seam; its under-lock recheck and authorization use the real migrated database.

Global corpus configuration, release listing, activation/rollback authority, released retrieval, stored vectors and E0/E1 definitions retain their existing policy. The immutable corpus models, worker code, worker-lock code and identity models remain byte exact. Global publication/retrieval validation functions remain AST exact. Trusted local processing-quality/replay functions retain their signatures, including the bulk `_loaded` path. This change does not establish a wider global-administrator policy.

## Actual verification and retained failures

| Observation | Result | Evidence identity |
| --- | --- | --- |
| Frozen legacy ingestion under interactive worker key | Expected lock failure reproduced; zero source rows/files added | `cd459ad5efd20bfb039b11b3b38d4368975847fe7edc7cee780bc18ca753ee00` |
| First new-suite run | Eight maintenance cases passed; thirteen workspace fixtures errored before product checks because `.test` email domains are rejected | `f921cc7181f83193b5ac6f1b58ee341b392b173771419767cb2c9c765516f973` |
| Corrected new-suite run | 21 passed, zero failed/errored/skipped | `f8eb6fd0ced437636c27a8a0dd970d245566c0adf8ba8469c373499c77ac8edc` |
| New and related existing suite | 87 passed; actual test time 79.64 s, runner time 82.886359 s | `3068ad87e4db0092b13db3736a7ba898acd90a5f5b31704db401ae674c8ef7e4` |
| Final scoped formatter/static checks | Nine files formatted; correctness rules passed | Current source hashes in the safe record |

The related suite includes corpus release/rollback, immutable history/source availability, legacy processing execution, streamed upload, cleanup, worker observations and frozen managed evaluation. All selected tests and eight related product files stayed byte exact during that run. The subsequent CLI print-line formatting is the sole byte change after regression; the complete seven-file approved candidate remains AST exact. The first seven-file application was refused by automatic approval review; the root verified the user's development scope, repository requirements and finite baseline proof, then the same reviewed patch was approved and applied. That rejection and its resolution remain separate records.

All database work used newly created disposable databases on localhost port 55432. No main/installed CPU database, official original, historical answer/citation, runtime process or cloud model was changed. Provider calls, human ratings and scientific quality labels for this scope are zero. The next checkpoint needs the final source-bound unified gate, installed-runtime acceptance and refreshed complete/eight-owner delivery. Broader upload, cancellation/recovery and independent semantic checks retain their original requirements.
