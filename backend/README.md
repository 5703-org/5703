# AI Learning Assistant — Backend

**CS-30-1 · Backend & Database Engineering · Zeping Liao**

A modular-monolith FastAPI backend for the Personalised AI Learning Assistant.
The codebase ships the engineering foundation, the database layer with
migrations, and one **fully closed CRUD loop** (auth → sessions) that proves
every layer of the architecture end to end.

---

## 1. What is implemented

| Area | Status |
|---|---|
| Application factory, typed config, dev/test/demo environments | ✅ |
| Layered architecture (API / Service / Repository / Port / Adapter) | ✅ |
| `/api/v1` versioned API with OpenAPI docs at `/docs` | ✅ |
| Unified success envelope + stable error code catalog | ✅ |
| Trace-ID middleware + structured JSON logging | ✅ |
| SQLAlchemy engine/session, Unit of Work, audit columns, optimistic locking | ✅ |
| Alembic migrations (empty DB → latest in one command, re-runnable) | ✅ |
| Seed data: default workspace, roles, demo users | ✅ |
| JWT login, current-user dependency, RBAC, object-level authorisation | ✅ |
| Session closed loop: create / list / read / rename / archive / restore / soft-delete | ✅ |
| Student profile: read / update (new version) / reset | ✅ |
| Feature flags + capability discovery API (no hardcoded buttons) | ✅ |
| Provider registry, capability ports, pipeline executor, transactional outbox | ✅ (foundations) |
| 23 automated tests, Dockerfile, docker-compose | ✅ |
| Documents / retrieval / generation / experiments | ⏭ planned |

Demo accounts after seeding (password `Passw0rd!`):
`admin@example.com` (admin), `student@example.com` / `student2@example.com` (students).

## 2. Quick start (local, zero infrastructure)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

alembic upgrade head        # create schema
python -m scripts.seed      # default workspace + roles + demo users
uvicorn app.main:app --reload
```

Then open <http://localhost:8000/docs>.

## 3. Quick start (Docker, PostgreSQL)

```bash
docker compose up --build
```

The app container runs `alembic upgrade head` and the seed automatically,
then serves on <http://localhost:8000>.

## 4. Run the tests

```bash
python -m pytest
```

23 tests cover: health endpoints, auth + RBAC, cross-user isolation, the full
session lifecycle (including 409 on stale writes and idempotent archive),
error-envelope contract, trace propagation, the capability API, and clean
migration from an empty database.

## 5. Project layout

```
app/
  main.py                # application factory (importing it has no side effects)
  core/                  # config, logging, errors, exceptions, middleware, security, flags
  db/                    # engine/session, base + audit mixin, unit of work
  api/v1/                # router aggregation + shared dependencies
  modules/
    identity/            # workspace, roles, users, student profile (models/repo/service/router)
    learning/            # chat sessions - the closed CRUD loop
    knowledge/           # documents & indexes        (planned)
    answering/           # question pipeline          (planned)
    experiment/          # batch experiments          (planned)
    administration/      # capability discovery, outbox inspection
  platform_core/         # ports, provider registry, pipeline executor, outbox events
alembic/                 # migration environment + 0001_initial
scripts/seed.py          # idempotent seed
tests/                   # pytest suite (isolated app + isolated DB)
```

## 6. Conventions every module must follow

* **Success envelope:** `{"data": ..., "meta": {"trace_id": ...}}` via `core.responses.ok()`.
* **Errors:** raise `AppError("<CODE>")`; codes live in `core/errors.py` and map to
  stable HTTP statuses + safe messages. Internal details go to logs only.
* **Trace:** every response carries `X-Request-Id`; an inbound header is honoured.
* **AuthZ:** the current user always comes from the verified JWT. Other users'
  resources return **404**, never 403 (no existence leaks).
* **Writes:** mutating endpoints bump `version` and reject stale versions with 409.
* **Events:** business writes publish `OutboxEvent` rows in the *same* transaction.
* **Modules** never touch each other's tables — they call each other's services.
