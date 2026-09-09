# CS-30-1 Learning Assistant

A conversational learning assistant that answers natural-language questions using a bounded OpenStax knowledge corpus, actual conversation context, explicit learner preferences and inspectable citations. The project also includes separate reproducible evaluation tools.

**Current local result:** all four complete official OpenStax PDFs (4,638 pages) have been processed into 10,594 real 384-dimensional E5 vectors and published in PostgreSQL/pgvector. Only the answer LLM remains explicitly mock. Exact source recovery, license/hash/version, vector and retrieval proof is in the [per-book report](docs/execution/openstax-corpus-report.md). Actual API/browser chat, restored full-corpus integrity and remaining verification are tracked in [PRD](PRD.md), [SPEC](SPEC.md), [PLANS](PLANS.md) and [current progress](docs/execution/progress.md). Live answer effectiveness, full graphical/equation fidelity and independent human review remain unverified; no whole-project research completion is claimed.

## Product and research modes

| Mode | Input | Output and purpose |
| --- | --- | --- |
| `interactive_chat` | A natural-language message in an owned session | Full prose, actual source citations, optional profile policy, saved history and contextual follow-ups |
| `benchmark_openqa` | SciQ-derived question stem only, without options, answer key or support | Same free-form answering engine; compact-answer EM/F1 and separate full-response review |
| `benchmark_mcq` | Question plus deterministically shuffled A–D candidates, without the correct label | Separate legacy-compatible MCQ response and selection accuracy |

Learners land at `/chat`. Included capabilities are accounts, sessions, bounded summaries, retrieval-query preparation, source inspection, profile revisions, feedback, stop/retry/latest-answer regeneration, corpus lifecycle and administrator experiments. SciQ is not required to log in or chat. Exclusions are cross-session semantic memory, automatic mastery inference, arbitrary learner uploads, voice, multimodal input, web agents, a full LMS and model training.

## Current host deployment

The existing Windows workspace uses its `.venv`, the persistent PostgreSQL container at port 55432, host API on 8000 and frontend on 5173. Its active release pins E5 and the local `artifacts/huggingface` cache; the answer model remains mock. The database and source store already contain the real corpus. To restart this host arrangement, keep Docker running and use separate terminals from the repository root:

```powershell
$env:PYTHONPATH = '.;backend'
$env:PYTHONUTF8 = '1'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Second terminal, with the same environment:
.\.venv\Scripts\python.exe -m app.worker
# Third terminal:
npm run dev --prefix frontend
```

Preserve `.env` and existing volumes/source paths. Start each service only once; the worker lock rejects duplicate workers. The optional real E5 container has its own `compose.e5.yaml` and Linux lock; see [development checks](docs/development_checks.md). The small base Compose recipe below is a separate fresh mock-capable installation and does not automatically mount the host's real model/source cache.

## Fresh base Compose setup

The tested local environment is Python 3.13.2 and Node 26.7.0. Runtime Python dependencies are pinned in `requirements.lock`, development checks in `requirements-dev.lock`, and frontend dependencies in `frontend/package-lock.json`. Install both Python locks when running the full development gate; [development_checks.md](docs/development_checks.md) gives its commands and limits. Compose uses PostgreSQL 16/pgvector and builds the Python 3.13 runtime plus the frontend. Docker Engine and Compose are required for this path. Mock answer mode needs no paid model key; real local embedding models are a separate dependency and must be configured for the formal corpus.

From the repository root in PowerShell, preserve any existing environment settings:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose build api worker frontend
docker compose up -d db
docker compose run --rm api python -m app.cli migrate
docker compose run --rm api python -m app.cli seed-demo --confirm-dev
docker compose up -d api worker frontend
```

The frontend opens at `http://127.0.0.1:5173`, API at `http://127.0.0.1:8000`, and local PostgreSQL at port 55432 by default. The explicitly seeded development users include `admin@example.com` and `student@example.com`, both initially `Passw0rd!`; development seeding is forbidden outside dev/test/demo. Start with an activated, inspected corpus for factual chat. [runbook.md](docs/runbook.md) gives actual account, corpus, worker, evaluation and recovery commands. The clean Compose rehearsal is recorded under `evidence/recovery/`; its authored/mock corpus is not the four-book release.

The required demo signs in, creates a chat, asks “What is photosynthesis?”, follows with “Why does it need light?”, asks for simpler wording and an example, opens a source, changes a profile, and verifies saved history after re-login. Sources must match the responses and model mode must be visible. The evaluator is stopped during this product demo.

## Project documents

| Document | Purpose |
| --- | --- |
| `PRD.md` | Current product intent and mandatory four-book source scope |
| `SPEC.md` | Actual modules, physical storage, contracts and source-to-answer behavior |
| `PLANS.md` | G0–G9 execution order and next dependency-ready action |
| `docs/foundation/requirements.md` | Observable product, research, operational and UI requirements |
| `docs/foundation/architecture.md` | Shared runtime, ports, ownership and sequences |
| `docs/foundation/data_model.md` | Persistence, state machines and transactions |
| `docs/foundation/api_contract.md` | API/CLI designs and frontend mappings |
| `docs/foundation/ai_pipeline.md` and `conversation_design.md` | Generation, evidence, profiles and real history rules |
| `docs/foundation/evaluation_plan.md` | Independent protocols, metrics and evidence limits |
| `docs/foundation/ui_design.md`, `responsive_spec.md`, `ui_flows.md` | Restrained responsive UI and control behaviour |
| `docs/foundation/test_plan.md` | All AC/HC scenarios and responsive subchecks |
| `docs/foundation/source_inventory.md`, `handover_migration.md`, `scope_migration.md` | Original evidence, reuse and compatibility decisions |
| `docs/foundation/decisions.md`, `integration_ownership.md` | Defaults, lean rules and actual executor lanes |
| `docs/execution/` | One canonical 108-task ledger, 60-check ledger, reporting view and current evidence |
| `docs/runbook.md` | Installation, operations, restore and demo commands |

Technical implementation, executed technical validation, real-model research and actual human review are tracked separately. Original contributor names identify accountable domains; new work records Codex as the actual executor.

## Local delivery and evidence

[Handover](HANDOVER.md) links the current 236-Python/25-frontend unchanged-source gate, earlier independent clean installation, real four-book corpus, fixed-window comparison and complete backup/restore. [Current scope reconciliation](evidence/source_audit/documentation-review-ledger-reconciliation.json) preserves all 108 tasks, 60 acceptance checks and 12 responsive checks. [Generated delivery views](docs/delivery/README.md) provide the required owner/week reporting from the same ledgers. The current source ZIP is `artifacts/deliverables/CS30-1_local_project_2026-09-08_documentation_update2.zip`; its adjacent verification JSON and embedded manifest record every included file hash. The earlier source ZIP and installation proof remain preserved. Real data/model/backup files remain at their documented local paths and are separate from these source packages.
