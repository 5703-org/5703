# Main195 source correspondence - 15 October 2026

The installer, startup policy and dependency locks already match Candidate182 and194; no reinstall or launcher change is required by this source integration. Main now also contains their goal-review and portable-loader fixes, with its later checkbox/assertion work preserved. This is a source checkpoint, not a deployment or fresh-machine acceptance.

See [the English version correspondence](docs/execution/phase195-main-candidate-reconciliation-20261015.md) and the unchanged [Candidate194 installation/recovery guide](artifacts/deliverables/CS30-1_Candidate194_Windows_Install_Recovery194_20261015.md). Do not apply an older source overlay over Main195. No existing database or credential is migrated by this record. The installation/resource instructions below remain preserved.

---

# Windows source installation

This guide covers the combined phase182 source candidate and the alternative guarded repair of its immutable phase181 source base. These are small code deliveries, not complete resource bundles or offline installers. Phase181 verified reconstruction and native startup using already installed dependencies and a separate isolated database/assets. Neither that result nor the offline dependency Plan establishes a clean installation on another PC.

## Identify the files

Choose one source preparation path:

1. Extract the new `CS30-1_Week11_Source_Candidate182_20261015.zip` into a fresh directory. It already contains the integrated functional and portability changes. Its own updated `learning-assistant/PACKAGE_MANIFEST.json` describes those exact combined files; no repair application is needed.
2. Keep the original `CS30-1_Week11_Source_Candidate181_20261015.zip` unchanged. Its SHA-256 is `36afb4c43e4ffa7b12dc572e194325169ab92e85b2539b3c12024e9132b6d610`; it contains 709 manifest-listed source files plus the base manifest. Extract it into a fresh directory, extract `CS30-1_Combined_Repair182_20261015.zip` separately, and follow its `APPLY_REPAIR182.md`. The supplied Python applier defaults to a dry run, rejects any different base or pre-existing addition, and backs up the changed old source and original manifest before applying. It installs the combined source manifest last. Retain both the repair manifest and source backup.

Preserve the `learning-assistant` root and do not apply to an existing application, `.env`, `.secrets`, database or learner data. The earlier standalone portability overlay and its embedded guide remain unchanged historical artifacts; the combined delivery has its own guide, change inventory and updated source manifest.

The source includes the API/worker, generation/retrieval modules, contracts, Alembic migrations, frontend TSX/generated API types, four Python dependency locks, frontend package lock, Compose files and launcher. It excludes installed environments, `node_modules`, `dist`, private configuration, model weights, corpus bytes and database contents. Its selected tests are not the complete repository test/acceptance tree. Historical README references to omitted reports or resources do not supply those files.

## Install dependencies independently of runtime assets

Use Windows PowerShell 5.1 or PowerShell 7, Python **3.13.x**, and a Node version supported by all current locked tools: **22.x at least 22.12**, **24.x**, or **26.x and later**. Node 23/25 does not satisfy the locked Vitest range. `py -3.13` is convenient when the Windows Python launcher is installed; otherwise ensure `python` selects Python 3.13. Do not copy a virtual environment or another machine's `node_modules`.

Open a terminal in the extracted `learning-assistant` directory. Paths containing spaces are supported. First run the offline plan:

```powershell
& .\scripts\release\install_windows_dependencies.ps1 -Plan
```

Running the script without a switch also selects Plan. It checks source inputs, hashes the four locks, resolves local `-r`/`-c` includes, and checks the frontend build inputs. Plan does not run Python/npm, download anything, read deployment configuration, inspect assets, create environments, build or start services. It can pass before Python/Node or corpus resources are installed. Plan success is source-input validation, not installation success.

For an explicitly requested first installation into a fresh extraction:

```powershell
& .\scripts\release\install_windows_dependencies.ps1 -Install
```

This mode downloads dependencies, creates `.venv`, runs the locked CPU Python installation, installs frontend development dependencies with `npm ci --include=dev`, and runs the existing TypeScript/Vite build. It refuses existing `.venv` or `frontend/node_modules`; preserve and inspect a partial earlier installation instead of deleting it blindly. It does not create configuration, import data or start services.

The equivalent locked commands are:

```powershell
py -3.13 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock -r requirements-embeddings-cpu.lock
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Push-Location frontend
try {
    npm ci --include=dev
    if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
```

The Python locks pin versions; the Windows CPU lock uses the public PyTorch CPU wheel index. They are not a complete wheelhouse or a guarantee that every wheel remains available for every future platform. The frontend lock includes registry integrity values and platform-specific optional packages. Registry availability, local proxy/certificate settings, native wheels, disk space and the actual download/build result remain installation prerequisites. No dependency download or frontend build was executed while preparing this guide.

## Supply the separate official runtime assets

The portable launcher checks `resources/official-corpus/MANIFEST.json` **before** its own `-Install` branch. Therefore `start_local.ps1 -Install` cannot install dependencies from the source ZIP alone. Use the independent dependency step above; do not create an empty manifest, skip corpus checks or substitute mock assets to make startup appear successful.

A runnable resource delivery must preserve its existing manifests/hashes and package-relative layout, including:

| Relative location | Required contents |
| --- | --- |
| `resources/official-corpus/` | The verified `MANIFEST.json`, `corpus.jsonl.gz` and every listed source/storage object. |
| `artifacts/huggingface/` | Complete pinned E5-small-v2 and MiniLM reranker snapshots, including model/tokenizer/configuration sidecars. Existing optional provider tokenizer assets retain their own manifests. |
| `artifacts/tiktoken/` | The verified tokenizer cache required by the selected configuration. |
| `evidence/week09-continuation/20260930/visual-full-attempt2/` | The complete original visual-catalog manifest and its four catalog files, preserving their recorded paths and matching source PDFs. |

The source candidate does not contain these directories. Obtain the already approved public resource bundle separately and verify its supplied inventory; this guide does not download, rebuild or copy it. Do not transfer another installation's database, `.env`, private encryption key or account records as a resource bundle. For a fresh PC, install genuine local dependencies rather than borrowing junctions: phase181's same-host KaTeX junction produced font 403 responses and required a dependency-fixture adjustment. That fixture is not part of this source package.

## Configure and start a separately owned local instance

After dependencies and every required resource are present, use a fresh extraction with no `.env` for the normal managed-database path. The existing launcher generates fresh random local database/JWT values and keeps the persistent model-encryption key under this installation's `.secrets`. Do not copy the generic `.env.example` unchanged: its development database port is 55432, whereas the portable launcher's default is 15532, and its example secret/password strings are shared development values.

For example, after confirming these ports are free and Docker Desktop/Compose is available:

```powershell
& .\scripts\release\start_local.ps1 -Device cpu -DatabasePort 15532 -ApiPort 18000 -FrontendPort 15173
```

This is a future startup command, not a read-only check: it starts the installation-owned PostgreSQL Compose service, migrates/imports/verifies corpus and visual data, and starts the API, interactive worker, background worker and current-source Vite frontend. The API/worker must use the same `.env`, storage and persistent encryption key. `-Install` is unnecessary after the independent dependency installation. Choose other explicit free ports when those shown belong to another instance.

The `-UseExistingDatabase` option requires this installation's own `.env`, an explicit loopback PostgreSQL port matching `-DatabasePort`, and `STORAGE_ROOT=./artifacts/storage`. It still runs migration/import/verification and workers; it is not a read-only connection test. Use only a separately designated database with its matching corpus/storage identity. Existing learner databases are not installation fixtures.

The launcher uses `API_PROXY_URL` for the selected API port and serves current TSX through Vite. A built `dist` is not used by that launcher. Docker's frontend path builds its own assets separately. Startup readiness allows the configured worker preparation budget; its default 90-second/max-policy 210-second allowance begins after setup, not before dependency installation and not as an answer-latency guarantee.

After actual startup, verify the selected API `/live` and `/ready`, the frontend page, matching source identity and owned worker processes. The launcher records roles in `artifacts/runtime/processes.json`; it does not automatically stop those roles after a startup failure. Confirm process identity/ownership before stopping anything. Source-install Plan does not perform these checks. New model credentials and live provider tests are separate explicit actions; a successful login screen is not real-model or learning-quality acceptance.

## Repaired optional paths and verification scope

The base181 source contained two host-specific optional paths. The overlay changes `generation/experimental_fixed_id_checker_v1.py` to locate its project from its own `__file__`. It changes `generation/scoped_support_contract_v1.py` to require its packaged sibling `reliability_v3.py`; a missing sibling now fails closed with unresolved `CALCULATOR_SOURCE_MISSING`, instead of falling back to another installation. The original codec/calculator hashes and their validation gates remain unchanged. Neither optional research mechanism is activated by installation.

The small offline check copies exactly four public source files into a fresh path containing spaces. It exercises the real codec path/hash guard up to an intentional downstream import boundary, actual pinned calculator arithmetic, and changed/missing dependency failures. It blocks application/provider imports and networking and never calls `compile_saved`. For an optional independent check, with Python 3.13 already installed:

```powershell
$loaderCheckWork = Join-Path $env:TEMP ('Loader Check Space ' + [guid]::NewGuid().ToString('N'))
$loaderCheckReceipt = Join-Path $env:TEMP ('loader-check-' + [guid]::NewGuid().ToString('N') + '.json')
py -3.13 .\scripts\verify\portable_loaders182.py --source-root $PWD.Path --work $loaderCheckWork --output $loaderCheckReceipt
```

The portability evidence records offline source/plan validation, five relocated-loader cases and immutable base/overlay hashes. It does not qualify the complete experimental compiler or scientific output. Clean-PC downloads, wheel compatibility, frontend build, asset installation and another physical PC remain unexecuted by this dependency-install audit; any separately recorded native learning validation has its own database/process/source identity and scope. A later complete release needs its own common source/resource manifest and actual installation acceptance.
