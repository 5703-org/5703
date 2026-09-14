FROM python:3.13-slim AS runtime-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

FROM runtime-base AS runtime
COPY backend/app /app/app
COPY backend/alembic /app/alembic
COPY backend/alembic.ini /app/alembic.ini
COPY contracts /app/contracts
COPY generation /app/generation
COPY conversation /app/conversation
COPY personalisation /app/personalisation
COPY pipelines /app/pipelines
COPY retrieval /app/retrieval
COPY configs /app/configs

EXPOSE 8000

# Schema is owned by Alembic migrations, then the API starts.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS evaluator
COPY evaluation /app/evaluation

# Dependencies precede code so code edits do not reinstall the CUDA runtime.
FROM runtime-base AS e5-dependencies
COPY requirements-embeddings-linux.lock /app/requirements-embeddings-linux.lock
RUN --mount=type=cache,id=cs30-e5-pip,target=/root/.cache/pip \
    pip install --disable-pip-version-check -r /app/requirements-embeddings-linux.lock \
    && pip check

# Explicit optional target: the default runtime keeps its small mock install.
FROM e5-dependencies AS runtime-e5
COPY --from=runtime /app/ /app/
COPY scripts/verify/e5_container.py /app/e5_container_probe.py
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
