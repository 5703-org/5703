# Development and CI checks

Install the pinned runtime and development tools into the project environment:

```text
python -m pip install -r requirements.lock -r requirements-dev.lock
python -m scripts.verify.python_quality
python -m scripts.verify.all --mode mock
```

The complete local gate requires PostgreSQL/pgvector at the server selected by
`TEST_DATABASE_SERVER` and an installed frontend (`npm ci --prefix frontend`).
Integration tests create disposable databases; they do not use the main
`learning` database. The new migration regression begins with the actual initial
revision, preserves its account/profile/session/event rows, then creates selected
and refused MCQ answers at the first revision that contains answer tables. It
checks later upgrades, a repeated upgrade, public MCQ/evidence reads and a new
chat request without choices.

`python_quality` checks Ruff formatting and executable-correctness rules across
`backend/app`, `contracts`, `conversation`, `evaluation`, `generation`,
`personalisation`, `pipelines`, `retrieval`, `scripts` and `tests`.
Original input packages, historical evidence copies and immutable migration
scripts are outside this formatting scope. It never reformats files itself.
Ruff checks undefined/local names, invalid control flow, duplicate definitions
and related correctness errors; unused-import cleanup is separate.

Mypy checks the canonical Pydantic models and HTTP envelopes, generation
dataclasses, evaluator protocol and typed consumer examples. Pydantic constructor
types are checked. This is a concrete boundary gate, not a claim that all backend
functions have strict typing. Deliberately invalid temporary fixtures must fail:
an undefined name, formatting drift, wrong constructor argument types, a wrong
protocol return and a modified OpenAPI contract. The original source and schema
files remain untouched by these rejection probes.

`.github/workflows/ci.yml` runs the local gate on Ubuntu with pinned Python and
Node versions and a disposable PostgreSQL/pgvector service. It then prepares an
authored mock corpus using `scripts.verify.ci_seed`, starts the real API/worker
and runs the login/responsive and multi-turn browser smoke tests. CI setup refuses
any database name that does not start with `cs30_ci_` and any non-test/non-mock
settings. These software fixtures are separate from the official four-book
OpenStax corpus and do not establish live model accuracy.

Current execution evidence is written under `evidence/devtools`; the complete
gate also writes `evidence/final`. CI uploads gate and browser evidence even when
a check fails. A locally parsed workflow or a local component pass does not
constitute a completed hosted GitHub Actions run.

## Optional E5 container

The base `compose.yaml` remains the small mock-capable installation. The separate
`compose.e5.yaml` enables `runtime-e5` through the `real-e5` profile and installs
`requirements-embeddings-linux.lock`. API and worker services are named `api-e5`
and `worker-e5`; they do not replace the running base services. The optional API
uses port 8100 by default. Answer generation remains explicitly mock.

Long-running `api-e5` and `worker-e5` services declare `restart: unless-stopped`,
as do the four ordinary services. The one-shot `e5-verify` and evaluator do not.
The policy is applied only when service containers are next created or updated;
the recorded configuration validation did not recreate the running deployment.
Follow [the recovery runbook](runbook.md#startup-and-health) after an interruption:
inspect stopped services and stale claims, then recover deliberately. Automatic
process restart does not authorize replay of an uncertain external model call.

An NVIDIA GPU with working Docker GPU access is required for the frozen CUDA
configuration. On Windows, Docker documents GPU support through its WSL2 backend;
the Compose device reservation must include `capabilities: [gpu]`.
See [Docker Desktop GPU prerequisites](https://docs.docker.com/desktop/features/gpu/)
and [Compose GPU reservations](https://docs.docker.com/compose/how-tos/gpu-support/).

The model/tokenizer revision remains
`intfloat/e5-small-v2@ffb93f3bd4047442299a41ebb6fa998a38507c52`.
The complete existing checkpoint cache is mounted read-only at
`/app/artifacts/huggingface`, preserving the frozen configuration's relative
`artifacts/huggingface` path. `HF_HUB_OFFLINE=1` requires cached files and avoids
Hub requests; see [Hugging Face offline behavior](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables#hfhuboffline).
The image contains no evaluator-private data, corpus originals or baked-in model
weights. Database and source-store paths must be supplied explicitly together.

The bounded verification uses the already restored database and sources. It runs
a disposable container, mounts originals read-only, sets PostgreSQL read-only
transactions, checks source/checkpoint hashes and performs actual CUDA query
embedding plus shared retrieval against the recorded four-book release:

```powershell
$env:E5_DATABASE_URL = 'postgresql+psycopg://learning:local-dev-database-only@host.docker.internal:55432/cs30_restore_openstax_portable_20260908'
$env:E5_STORAGE_PATH = './artifacts/restore-openstax-portable-20260908'
$env:E5_MODEL_CACHE_PATH = './artifacts/huggingface'
docker compose -f compose.e5.yaml --profile real-e5 build e5-verify
docker compose -f compose.e5.yaml --profile real-e5 run --rm --no-deps e5-verify
```

Run only the verifier for this recovery proof. Starting `worker-e5` is an explicit
deployment action: a worker can execute queued jobs in its configured database.
The verifier itself refuses database names outside `cs30_restore_`, never starts
a worker, and does not activate or reprocess any corpus. It writes actual results
under `evidence/e5-container`; image construction or visible GPU hardware alone
does not establish successful E5 inference. Host/container CUDA package locks are
separate because Linux includes additional NVIDIA and Triton dependencies.

The recorded container proof passed on Linux x86_64, Python 3.13.15,
Torch 2.8.0+cu128 and the RTX 5070 Ti. It checked the 10,584-vector restored
release, seven original-file hashes, ten checkpoint files and twenty ranked
hits across four diagnostic queries. Every ranked chunk ID and passage hash
matched the recorded host baseline; no answer model was called. The standard
runtime was separately rebuilt and confirmed to work without Torch.

See [the consolidated proof](../evidence/e5-container/verification.json) for exact
image and source hashes. The export command itself ended with a transport EOF
during a Docker restart; the retained image was subsequently tested successfully.
The successful probe does not turn that interrupted build command into a clean
build pass. The image contains an earlier application-code snapshot than some
later checkout changes. The frozen verifier is mounted read-only from the
checkout; its proof covers E5/container retrieval for the recorded image, not
fresh validation of every image API or answer-generation behavior.
