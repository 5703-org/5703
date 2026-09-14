# Local operation and recovery

Use [SPEC.md](../SPEC.md) for actual modules, storage and limits; [PRD.md](../PRD.md) for source scope; [PLANS.md](../PLANS.md) and [progress.md](execution/progress.md) for current evidence. Commands below are implemented entry points. Each data/model claim still requires its recorded execution result.

The complete official Biology 2e, Chemistry 2e, Anatomy & Physiology 2e and Concepts of Biology corpus has executed with real local E5 embeddings; current release/count/provenance evidence is in [openstax-corpus-report.md](execution/openstax-corpus-report.md). Only answer generation may remain mock. The portable authored example is a software rehearsal and does not satisfy this full-book requirement. See [corpus-acquisition.md](execution/corpus-acquisition.md) and the current plan for acquisition/processing progress; do not infer completion from download initiation or installed model libraries.

## Startup and health

Tested host versions: Python 3.13.2, Node 26.7.0. Python packages are pinned in `requirements.lock`; npm packages in `frontend/package-lock.json`. Compose builds Python 3.13 and the frontend and uses PostgreSQL 16 with pgvector. Run from the repository root in PowerShell with Docker Engine running:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose build api worker frontend
docker compose up -d db
docker compose run --rm api python -m app.cli migrate
docker compose run --rm api python -m app.cli seed-demo --confirm-dev
docker compose up -d api worker frontend
```

Default frontend/API URLs are `http://127.0.0.1:5173` and `http://127.0.0.1:8000`; host PostgreSQL is port 55432. Compose environment variables may change these. Explicit development seed creates `admin@example.com`, `student@example.com` and `student2@example.com`, initially `Passw0rd!`, and is only permitted in dev/test/demo. Nondevelopment requires a private SECRET_KEY; do not use demo credentials as deployment accounts.

The database, API, worker and frontend declare `restart: unless-stopped`; the optional E5 API and worker use the same policy. Evaluator and verification containers remain one-shot. This policy takes effect when those service containers are next created or updated; editing the file does not update existing containers. A manually stopped service stays stopped until the operator starts it. After a Docker interruption, inspect `docker compose ps -a` and service logs, then use `docker compose up -d db api worker frontend` for the intended base deployment. The optional E5 deployment uses its own explicit database/source configuration and separate Compose file; do not start it merely to recover the base deployment.

Process restart does not requeue uncertain in-flight work. Review interrupted jobs and allow the configured stale threshold to elapse (default 240 seconds). With the normal worker stopped, the operator may start one foreground worker using `docker compose run --rm --no-deps worker python -m app.worker --recover-stale`; this marks stale claims failed before continuing to consume queued work and takes the project worker lock. Alternatively, `python -m app.cli jobs --recover-stale` performs recovery without starting a worker. Review retained call/time budgets and any uncertain external attempt before requesting an explicit retry. Recovery never automatically repeats a possibly completed paid call; do not add `--recover-stale` or retry loops to the normal service command.

`GET /live` (also `/api/v1/health/live`) checks the process. `GET /ready` (also `/api/v1/health/ready`) checks the database. Authenticated `GET /api/v1/capabilities` separately reports chat/evaluation readiness and actual missing prerequisites. Database readiness alone does not establish a validated corpus or model. Mock answer mode is visibly labelled in the UI. Missing live configuration fails explicitly without silently substituting mock.

For host-side scripts against the configured local database, use the project environment and make both packages importable:

```powershell
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock -r requirements-dev.lock
$env:PYTHONPATH = '.;backend'
python -m app.cli --help
```

Use an existing project environment instead of recreating it when already installed. `requirements-dev.lock` installs the format, lint and type tools required by the complete local gate; [development_checks.md](development_checks.md) documents those checks and the optional E5 container and its actual verification evidence. Host `DATABASE_URL` and `STORAGE_ROOT` must point to the actual database and matching accessible source store. A Docker named source volume is not automatically the host's `artifacts/storage`. Run source-dependent CLI commands inside the API container for its store, or use a deliberately configured host deployment. Full local E5/reranker dependencies, weights and mounted cache must be recorded by the real-corpus setup; the earlier mock image is not proof of those dependencies.

## Accounts and feedback

Administrators can now create accounts, deactivate/restore users and reset passwords in **Administration > Accounts**. **Models** provides saved configuration revisions, real connection tests and explicit activation; **Diagnostics** shows request failures and evidence counts. See [model administration](model-administration.md) for protocol examples, key provisioning, version semantics and token budgets. The existing CLI remains supported. On the current development host PostgreSQL is mapped to **15432**; **55432** below is the fresh base Compose default. The portable full-package launcher uses its own database/service ports.

Host CLI examples (the same arguments work after `docker compose exec api python -m app.cli`; pass password environment values explicitly into that process when using Docker):

```text
python -m app.cli account-create --email learner@example.com --name "Learner" --role student --password-env CS30_NEW_PASSWORD
python -m app.cli account-update --email learner@example.com --version 1 --status deactivated
python -m app.cli account-update --email learner@example.com --version 2 --password-env CS30_NEW_PASSWORD
python -m app.cli feedback-review --feedback FEEDBACK_ID --state reviewed --note "Checked the reported citation" --issue LOCAL-1
```

Set the named password environment variable privately before invoking the command; passwords are not command-line arguments or printed output. Account-update requires the current record version returned by the prior operation. `--admin EMAIL` selects an existing active administrator for supported operator commands. User password change is also in Settings and `POST /api/v1/users/me/password`; token versions invalidate old credentials. Concurrent duplicate account creation returns conflict without a partial profile. Feedback keeps one row per owner/answer and returns to pending review after a learner edit; a regenerated answer does not inherit old feedback silently.

## Corpus, quality and releases

The exact portable authored example and field definitions are in [data_rebuild.md](data_rebuild.md). Its manifest has source-relative asset paths, title/edition, source_url/licence, size/hash, processing configuration and explicit exclusions. For a new official run, retain actual official URLs/licence/edition, unchanged raw bytes, hashes and full page/section coverage. Do not apply authored exclusions or invented metadata to the textbooks.

```text
python -m app.cli ingest --manifest pipelines/examples/authored_manifest.json
python -m app.cli processing-quality --processing PROCESSING_ID --output artifacts/quality.json
python -m app.cli processing-diff --before OLD_PROCESSING_ID --after NEW_PROCESSING_ID --output artifacts/processing-diff.json
python -m app.cli configuration-create --file artifacts/configuration.json
python -m app.cli corpus-build --config artifacts/release-build.json
python -m app.cli corpus-activate --release RELEASE_ID
python -m app.cli corpus-rollback --release PREVIOUS_VALIDATED_RELEASE_ID
python -m app.cli source-visibility --document DOCUMENT_ID --action deactivate
python -m app.cli source-visibility --document DOCUMENT_ID --action restore
```

Ingest prints actual document/version/processing/job IDs. The running worker processes queued jobs; wait for the processing job to succeed and inspect its quality report before building. A build file contains `processing_run_ids`, optional `configuration_id` and `name`; use returned IDs from the same database. Configuration-create accepts `kind`, `name`, `values`. Build queues another job; activate only after it succeeds and the release is validated. See `app.cli --help` and the knowledge API for exact current fields. `source-visibility --action revoke` also makes retained evidence unavailable; use it only for the intended document.

To process one queued job manually, stop the normal worker first, then run `python -m app.worker --once` in the same environment/store. A second worker is rejected by the PostgreSQL advisory lock. Do not interpret that rejection as failed ingestion.

Repeated original bytes reuse their immutable version. Changed processing settings create a new run. Quarantine stays visible; exclusions require actual inspected reasons. Real-corpus releases must use the actual pinned embedding model/tokenizer, full vectors and verified counts/hashes. A failed build/activation leaves the current pointer intact. A legacy release without its original integrity baseline cannot be made valid by backfilling invented hashes; rebuild from preserved originals. Historical pilot pages require their exact original bytes, while a new edition is a separate asset.

## Jobs and bounded maintenance

```text
python -m app.cli jobs
python -m app.cli job-inspect --job JOB_ID
python -m app.cli jobs --recover-stale
python -m app.cli job-retry --request REQUEST_ID --key NEW_RETRY_KEY --owner student@example.com
python -m app.cli cleanup --plan artifacts/cleanup-review.json
python -m app.cli cleanup --apply-manifest artifacts/cleanup-review.json
```

Inspect the cleanup plan before applying the same file. It is age-bounded and rechecks exact root/path/hash/current references; referenced or changed originals are not deleted. Retry eligibility is for failed/cancelled latest interactive requests with remaining budget. It preserves original input and consumed calls/time. Regeneration is a separate answer route and keeps the previous answer active until replacement succeeds. Stale recovery marks uncertain execution explicitly; it does not promise a paid call can safely be repeated. Request/job/answer/trace identities connect diagnostics. Unexpected errors log only a safe event and exception class, not SQL parameters or exception tracebacks.

## Separate evaluation

The evaluator uses its own private storage and exports. API and answer worker contain no gold/support mounts. The actual bridge is `app.modules.experiment.bridge:create_backend`; it creates shared AnswerRequest/Job rows, while private scoring stays in `evaluation/`. A normal worker must be running.

```text
python -m evaluation.runner --config configs/evaluation/mock_openqa.json
python -m evaluation.runner --config configs/evaluation/mock_mcq.json
python -m evaluation.runner --resume RUN_ID --root evaluation/private_runs --export-root evaluation/exports
```

Example configurations require their backend options and active release/environment to match the target database; read [evaluation/README.md](../evaluation/README.md) and [BACKEND_PROTOCOL.md](../evaluation/BACKEND_PROTOCOL.md) before a new freeze. Authored sample datasets are mock software evidence. Real SciQ needs an actual frozen revision/split/checksum in evaluator-only storage.

For Compose, build/run the optional evaluator image with a configuration inside its private mounted directory:

```text
docker compose --profile evaluation build evaluator
docker compose run --rm evaluator python -m evaluation.runner --config /data/evaluator-private/run-config.json
docker compose run --rm evaluator python -m evaluation.runner --resume RUN_ID --root /data/evaluator-private --export-root /data/runs
```

That directory maps to host `artifacts/evaluator-private`; exports map to `artifacts/runs`. The config's dataset and backend paths must be valid inside the container. The runner returns exit 0 only for completed runs; exit 2 can mean pending or reconciliation required, so inspect its saved state. OpenQA and MCQ exports, full-response review and C0–C2 studies remain distinct. All scheduled errors/refusals/cancellations are retained. The user authorized real DeepSeek tests on 13 September. Current studies pin an explicit managed model revision and retain their exact subset, schedule, protocol and source/configuration fingerprints; see the upgrade record. The single worker is shared with chat, so running studies may add queue time.

## Verification and distinct-target restore

```text
python -m scripts.verify.foundation
python -m scripts.verify.contracts
python -m scripts.verify.chat_scope
python -m scripts.verify.all --mode mock
python -m scripts.verify.chat_journeys --without-sciq
python -m scripts.release.backup --destination artifacts/backups/NEW_BACKUP --postgres-container cs30-learning-db-1
python -m scripts.release.restore --manifest artifacts/backups/NEW_BACKUP/manifest.json --confirm-target cs30_restore_review --storage artifacts/restored-review --postgres-container cs30-learning-db-1
```

The backup/restore commands above are **host scripts** and need the same configured database plus a matching host-accessible source store. `--postgres-container` obtains pg_dump/pg_restore from that actual container; omit it when suitable native tools are installed. Choose a new backup destination, a distinct nonexistent database and an empty distinct restored source directory. Existing databases/source storage are never overwritten. Manifest path/hash validation precedes restore; successful output records actual counts, active pointer and preserved-content fingerprint. Backup-v2 also fingerprints complete users/roles/workspaces/profile values and all configuration/processing/unit/chunk/release/vector values. It includes source-recovery HTML, reviewed transcripts, rendered PNGs and raw OCR artifacts referenced by every retained processing configuration. The actual full-corpus restore verified7originals and44supplements in `evidence/recovery/backup-real-openstax-20260908/restore-cs30_restore_openstax_20260908.json`. Older v1 manifests retain their original narrower checks.

The aggregate mock gate runs schemas, Python tests, TypeScript drift/components/build. Browser journeys, real zoom, clean Compose, restore, real-corpus/model execution and human reviews require their own evidence; they are not silently covered by that one command. Frontend commands are `npm ci`, `npm run types:check`, `npm test`, `npm run build` and `npm run test:e2e` from `frontend/`. Browser tests require the configured actual API/worker/database and prepared source fixtures.

The required demo uses `/chat` with evaluator stopped: sign in, ask a concept question, follow up using a referent, simplify, open exact sources, save feedback/profile changes, switch profile off while retaining context, cancel/retry/regenerate, resize with drafts, refresh/re-login, and verify source deactivation/restoration/rollback. The earlier authored/mock execution is saved evidence; repeat the appropriate flows against the full official corpus before claiming that real-data stage. Record actual commands/results, failed traces and unavailable physical/native IME/human checks separately.
