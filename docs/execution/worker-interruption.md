# Actual worker interruption drill

AC-13 passed on 2026-09-08 using a generated, separately migrated PostgreSQL
database and storage directory. The verifier stopped only its own worker process;
the main worker, official corpus, database, Docker daemon and volumes were untouched.

The first ordinary worker completed a baseline conversation turn. A second actual
worker invoked the shared answer service, persisted one charged generation-start
attempt and entered a 30-second delay in its process-local mock transport. The
verifier then terminated that owned PID before any answer publication. This delay
is verification instrumentation; the runtime worker and answer logic were unchanged.

Recovery waited actual wall time until the claim was 182.001 seconds old. It used
the real minimum supported `WORKER_STALE_SECONDS=181`; no job timestamp was edited.
A new worker started with `--recover-stale --once`, recovered one claim and exited.
The job failed with `WORKER_INTERRUPTED` and an uncertain-execution flag. The charged
call, start attempt, previous conversation and snapshots remained unchanged, and
the interrupted request had no answer.

An explicit retry through the actual API then ran in another ordinary worker.
It preserved the request identity and consumed budget, produced exactly one answer,
and ended with two total charged calls. The old failed job and incomplete start
attempt were retained. The disposable database was removed after the final row
snapshots and logs were saved.

- [Verification and exact identities](../../evidence/operations/worker-interruption/20260908T085003Z/verification.json)
- [Before interruption](../../evidence/operations/worker-interruption/20260908T085003Z/before_interruption.json)
- [After recovery](../../evidence/operations/worker-interruption/20260908T085003Z/after_recovery.json)
- [After explicit retry](../../evidence/operations/worker-interruption/20260908T085003Z/after_explicit_retry.json)
- [Reproducible verifier](../../scripts/verify/worker_interruption.py)

Run from the project environment with `python -m scripts.verify.worker_interruption`.
The verifier creates only a generated `cs30_drill_*` database and requires its output
inside the repository's evidence directory. Each run retains a distinct timestamped
evidence directory. Its optional server setting is `TEST_DATABASE_SERVER`, matching
the integration fixture convention.

This is real process/database recovery with an explicitly mocked transport, not a
live-provider or scientific-effectiveness result. It does not separately kill a
teaching or release worker; the existing PostgreSQL cancellation/recovery tests
cover those branches. The drill also executed actual job inspection and a cleanup
dry-run command for AC-33. That plan had zero candidates, so its scope excludes
orphan removal. The meaningful cleanup tests and subsequent restored-source API
check are recorded separately in [the completed local repair audit](local-repair-drill.md).
