# CS30-1 Week10 delivery — 13 October 2026

Release: CS30-1_Week10_20261013_22ccbfa899ec. Open this document first. Older dated README/status documents in the source tree retain historical evidence. RELEASE_MANIFEST.json is the authority for this delivery's membership and source identity.

This is one integrated chat-first learning assistant. COMPLETE contains all current public source, shared model/tokenizer assets, the four-book official OpenStax corpus, candidate visual catalogs, and nine English Week10 reports. The eight owner archives contain complete assigned files and the matching member report. They depend on COMPLETE's shared source/runtime/dependencies and are not eight independently runnable applications. Owner assignment does not identify who personally executed the work.

## Windows startup

Use a normal new extraction directory. Install host Python 3.13, Node compatible with Vite's declared ^20.19.0 or >=22.12.0 requirement, and Docker Desktop with the Linux engine for PostgreSQL/pgvector. This release was checked with Python 3.13 and Node26.7.0 using existing dependencies; a clean dependency download was not repeated. Keep approximately6GiB free for extraction, dependencies, caches and a fresh database; optional CUDA/ONNX environments require more.

From the extracted learning-assistant directory run:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start_candidate.ps1 -Install -Device cpu -DatabasePort 15582 -ApiPort 18082 -FrontendPort 15182

The original public wrapper verifies/hydrates pinned local assets before invoking scripts/release/start_local.ps1. Installation uses requirements.lock, the CPU embedding lock and frontend/package-lock.json; dependency package downloads require internet access. Choose available ports. The launcher refuses unrelated occupied ports. It creates this installation's configuration, private model-key storage, fresh Compose database, schema and bundled corpus, then starts API, interactive/background workers and frontend. Runtime artifacts/processes.json records the owned process IDs. Previous development data is not part of this ZIP.

Open http://127.0.0.1:15182. The local admin address is admin@example.com; the launcher creates its initial password in this installation's restricted .secrets/initial-admin-password.txt. Read that private file locally and change the password through Your account. Runtime passwords/API credentials are generated or entered locally; none are shipped. Configure and test a real provider through Administration > Models when explicitly desired. The default teaching provider is the authored mock simulation, clearly labelled in the UI. The bundled corpus uses real E5 vectors; the release browser smoke used a tiny authored mock-embedding corpus instead.

Rerun without -Install after dependencies exist. Use -UseExistingDatabase only for an explicitly intended separate installation after reviewing its local configuration and target; do not point this release at preserved development databases. See docs/runbook.md for owned-process operation, recovery and backups. The wrapper retains finite checks and never repairs mismatching pre-existing public cache bytes silently.

## Configuration

.env.example contains development examples, blank provider credentials and opt-in defaults. start_candidate.ps1/start_local.ps1 generate installation-specific secrets and matching ports. See release/CONFIGURATION.md. Do not copy a development .env or credential store into the deliverable. Qualification transport, checker-schema/output experiments and V23/prewarm candidates remain opt-ins as documented; packaging does not activate unfinished compact acceptance.

## Offline unit preparation and checks

After dependencies exist, from the project root:

    .venv\Scripts\python.exe -I -B -S scriptselease\hydrate_public_model_assets.py --project-root .
    .venv\Scripts\python.exe -B release\prepare_public_dev_fixtures.py
    $env:PYTHONPATH='.;backend'
    $env:TIKTOKEN_CACHE_DIR=(Join-Path $PWD 'artifacts/tiktoken')
    .venv\Scripts\python.exe -B -m pytest tests/unit -q

The preparation helper restores an exposed public DEV retrieval record and a checked official PDF alias, preferring a hard link to avoid a duplicate book. It does not read or write a database, access the network, overwrite mismatching files or create human/gold labels. Optional exact visual-source fixture studies require their separate inputs. PostgreSQL integration must use explicitly isolated synthetic data, not an existing database.

## Verified results and limits

The final isolated unit run passed4803tests and215subtests, with28skips and40warnings. Foundation, contracts, chat scope and targeted Ruff passed. TypeScript,241frontendtests in27files and frontend build passed. Public asset hydration verified26immutableinputs and28selectedtargets. Native Windows Edge passed login, New chat, complete cited mock answer, exact answer/job/history identity, source opening, refresh, and1440/390layouts; all17active input pins match this final freeze. Owned services closed. The original eight-failure test run and the browser harness-wait timeout remain in release/validation as earlier scoped failures, followed by successful corrected checks.

These are current free software and authored-data runtime checks. This release did not repeat clean dependency installation, the full PostgreSQL/corpus launcher, live model quality, formal warm-p95 or human-learning studies. Existing real checker observations remain recorded: the latest S02 request was a technical citation-contract stop with null semantic scores; S01 browser129 never dispatched. No new model request was made for release assembly. Canonical project_complete remainsfalse. No deployment, remote push or coursework submission was performed.

Each DOCX in release/reports is byte-identical to its standalone final report; each owner ZIP carries that same member DOCX. All27rendered report pages were independently visually reviewed. RELEASE_MANIFEST.json lists members, SHA256 and source/runtime provenance; the separate RELEASE_VERIFICATION.json and SHA256SUMS.txt bind the nine final ZIPs.

The exact Week9 baseline is final_source04_with_reports_matched5_and_token_cache_20261009_01. Historical source evidence newly packaged is not relabelled as new Week10 work. This release is frozen: subsequent authorized development belongs to Week11. SOURCE_NOTICES.md, docs/licenses and resource-local licenses retain public textbook/model attribution.
