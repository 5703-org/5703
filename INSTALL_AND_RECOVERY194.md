# Candidate194: Windows installation and recovery

15 October 2026 UTC. SOURCE CANDIDATE with optional ordinary-answer checking. Preserve Candidate182 and every existing installation, key, database and historical result. This ZIP has source/setup/locked dependency declarations; complete official runtime resources and dependencies are separate.

## Verify and extract

Use `Get-FileHash -LiteralPath '<archive path>' -Algorithm SHA256` and compare with the delivered `.sha256` file. Extract `CS30-1_Week11_Source_Candidate194_20261015.zip` into a newly named empty directory. Its `learning-assistant` folder already has the feature and current manifest. Do not apply an older repair or install over an existing environment.

The previous Candidate182 ZIP remains valid historical delivery: SHA256 `b0505045c533e04c77eab52dcedc764b64b6294199ef703f3a4c35eb626ddc20`. Its earlier installation guide and same-PC measurements are retained; those measurements do not certify Candidate194.

## Dependencies and official resources

Use PowerShell 5.1/7, Python 3.13.x, Node 22.x >=22.12, 24.x or >=26, and Docker Desktop/Compose for managed PostgreSQL. From this release's source root:

```powershell
& .\scripts\release\install_windows_dependencies.ps1 -Plan
& .\scripts\release\install_windows_dependencies.ps1 -Install
```

Plan is offline and does not execute Python/npm, download, build or launch services. Install is a separate intended download/install/build action and refuses an existing .venv or frontend/node_modules. Keep a failed/partial installation; use another fresh extraction for a later installation attempt.

Supply the approved matching official corpus/manifests, pinned model snapshots/tokenizer cache and original visual catalog/PDFs at the exact paths in WINDOWS_SOURCE_INSTALL.md. Do not replace missing resources with mock or empty assets. The full-resource start_local launcher checks resources before its own Install branch, so use the separate dependency installer first. Never copy another installation's .env, .secrets, managed keys or learner database. The public .env.example is an example, not a deployment credential.

## Start and use

After prerequisites are ready, choose free ports that do not collide with an existing instance:

```powershell
& .\scripts\release\start_local.ps1 -Device cpu -DatabasePort 15532 -ApiPort 18000 -FrontendPort 15173
```

These are the launcher's documented defaults; change all relevant ports when another instance uses them. In particular current Main already uses API18000/frontend15173, so choose a separate pair before starting this candidate beside Main. Managed startup provisions/migrates/imports its selected database and starts API, interactive/background workers and Vite. Existing-database mode also mutates the selected database; do not target a historical or Main database for a trial. Verify /live, /ready, frontend and artifacts/runtime/processes.json with owned process identities. A source-only minimum mock startup is separate from full official-corpus/RAG readiness.

A new ordinary draft leaves Check answer unchecked. Select it before submitting when semantic checking is wanted. The saved choice persists through Retry/recovery/regeneration/history; protected tasks retain mandatory checks. Skipped checking is not passed checking. Model configuration is installation-local and explicit; this package does not replace the existing provider/window/key. Use the existing DeepSeek configuration for routine tests and other models only for an explicit comparison.

## Verification and recovery

The companion archive verification receipt lists the actual extracted-package software checks and their bounds. It does not establish real-answer speed/quality, a ten-second target, physical-device acceptance or a fresh dependency installation. No full suite or paid test is implied. Current Main and this package share the accepted checkbox behavior; the candidate also preserves182goal-review/portability changes and therefore has documented whole-source differences.

No automatic rollback is provided. Preserve the previous source/archive and all failed targets/logs. Recover by extracting a verified prior source archive into another newly named empty directory; never mix partial files, databases or keys. The raw phase189 patch is not a general applier for arbitrary installed versions. See CHANGELOG_CHECK_ANSWER194.md for the integration boundary.
