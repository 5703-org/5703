# Development and CI checks

## Current public-distribution checkpoint

The [22 September local release gate](../evidence/week08-memory-v2/20260921/software-gate-release-final-20260922/software_gate.json) passed 828 Python and 86 frontend checks, all eight stages and zero skips. All 487 source/configuration files remained unchanged during the gate. This includes the earlier public-fixture successor (five revised tests and two new helpers) and the later release packager/resource regression correction. Product and evaluator behavior are unchanged. The original 485-file formal-study version remains exact in the verified separate private research archive. Public tests require no held-out catalogue or reference labels. Earlier recorded gates below retain their dates and scopes.

[Portable parity](../evidence/week08-memory-v2/20260921/portable/source-parity-release-final-20260922.json) matches 514 public source/configuration files and all 80 preserved runtime resources. It supplements the existing fresh CPU installation and browser execution; it does not rerun dependencies or establish a new physical-machine result. [Current study outcomes](execution/memory-v2-results-20260921.md) keep semantic and human evaluation separate from software checks.

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

## Week 8 reliability and CPU checks

The [05:10 pre-expansion software gate](../evidence/week08-delivery/20260916/software-gate-final/software_gate.json) passed 331 Python/51 frontend checks and all eight quality/contracts/build stages with unchanged source snapshots. The retained 312/51 gate belongs to13 September. New focused regressions are `tests/unit/test_query_reliability.py`, `tests/unit/test_runtime_device.py` and `tests/integration/test_query_reliability.py`; PostgreSQL integration uses a disposable database, not the learner database.

CPU optional dependencies use `requirements-embeddings-cpu.lock`; keep the CUDA lock for explicit compatible GPU installations. `scripts/verify/retrieval_reliability.py` performs real local embedding/reranking and read-only corpus retrieval; it does not invoke an answering model. Its actual reports are [CPU with installed wheel (public summary)](../evidence/week08-memory-v2/20260921/privacy-relocations/public/5086e949cdec-real-cpu-retrieval.json) and [isolated CPU-only wheel (public summary)](../evidence/week08-memory-v2/20260921/privacy-relocations/public/b4cb151c6b12-cpu-only-wheel-retrieval.json): the same 8 development+8 holdout cases pass, with unchanged release fingerprints. They are developer-authored topic checks, not 32 independent cases or a calibrated scientific benchmark.

The [Week 8 delivery record](execution/week08-delivery-20260916.md) separates these executions from the separately passed fresh Windows CPU installation and still-pending final package sidecars. Physical MPS, full CPU/GPU parity, concurrency/stress and independent semantic/teaching review require separate checks. The existing optional Linux/CUDA container instructions retain their original distinct environment scope.

The historical 05:10 Week 8 checkpoint completed 2026-09-16T05:10:44Z with 343 captured files unchanged; the earlier04:10 reliability gate retains its342-file source snapshot and historical scope.

## Week 8 pre-expansion CPU installation evidence

[Fresh Windows CPU installation](../evidence/week08-delivery/20260916/cpu-install/summary.json) passed new dependencies, migrations/import of 48 source files and 10,594 real vectors, four HTTP diagnostics plus cancellation/history, and a separate two-turn 1440/390 browser check. Answers were explicitly mock, paid calls zero, and no original key/private history was copied. [Source parity](../evidence/week08-delivery/20260916/cpu-install/source-parity.json) covers 385 non-Markdown source/configuration files; all 80 public corpus/model resources were also verified. Physical new-laptop/MPS and broader performance/semantic/human acceptance remain separate. Final Week 8 ZIP sidecars/reconstruction are pending the archive phase.

## Expanded Week 8 verification interfaces

New interactive commands freeze v9 understanding and the bounded evidence-union policy. Historical commands retain v6 and formal E0/E1 remains unchanged. Inspect Administration > Response diagnostics > Processing trace for structured intent/constraints, candidate filtering, source reuse, lexical/citation/teaching observations and timing. Missing old fields remain unrecorded. Scores and automated flags are not semantic acceptance.

Run focused software checks from the repository environment:

```text
python -m pytest tests/unit/test_structured_understanding.py tests/unit/test_generation_evidence_budget.py
python -m pytest tests/integration/test_evidence_union.py tests/integration/test_query_reliability.py
python -m evaluation.reliability.calibration --help
```

The integration fixture creates/migrates a disposable `cs30_test_` PostgreSQL database using `TEST_DATABASE_SERVER`, never the main application database. Calibration requires actual complete reviewed development/holdout judgments and a fixed model revision; blank labels fail and a proposal is never activated automatically. The canonical catalogue is `evaluation/reliability/week08_cases_v3.json`; v2 raw runs retain their initial split identity, with the RAG-family grouping correction explicit. Preserve failed attempts, unknown costs and blank independent ratings. The earlier 05:10 gate/fresh CPU installation is pre-expansion; use the [current implementation record](execution/week08-delivery-20260916.md) for final-run/package status.

## Historical v8 software checkpoint — 16 September

[The v8 software gate](../evidence/week08-delivery/20260916/software-gate-v8-final/software_gate.json) completed at 2026-09-16T05:57:32Z with **383 Python tests and 53 frontend tests**, all eight stages passed and **359 source files unchanged**. It covers the frozen v8 implementation and catalogue v3 grouping checks. Earlier 331/369/377 checkpoints remain dated. This software result does not certify answer science, new live/provider outcomes, independent labels or physical-device acceptance. The v8 runtime results are retained in the Week 8 record. V9 verification and final archive reconstruction have separate identities.

## V9 facet and answer-mode operation

The learner chooses Textbook (default) or explicit General knowledge for the next request. Saved answers retain their mode and provenance. General output is unverified model knowledge, contains no textbook citations and never activates after a textbook refusal automatically. A mock provider explicitly refuses independent general knowledge. Retry/regeneration preserve the original mode; a refused/failed replacement leaves the old answer active.

For textbook diagnostics, whole-query and fallback counts are separate. An all-rejected multi-part query may run two facet queries with at most 20 additional ranking slots, using the same local model/release/device and active-time budget. `final_selection` counts distinct screened/admitted passages, while submitted/cited reflect the actual model input/output. The 3,000-token evidence cap is unchanged. A partial lexical estimate is not scientific entailment.

Focused verification: `python -m pytest tests/unit/test_facet_fallback.py tests/integration/test_facet_fallback_runtime.py tests/integration/test_general_mode_runtime.py`. Integration uses only the disposable PostgreSQL fixture. [The 81-check scoped result](../evidence/week08-delivery/20260916/understanding-v9-implementation.json) includes these boundaries and existing formal-protocol regressions. Use the [Week 8 execution record](execution/week08-delivery-20260916.md) for current aggregate/live/CPU/browser/package evidence; the earlier 383/53 v8 gate remains dated.

## Current v9 software and live checkpoint — 16 September

[Final current gate](../evidence/week08-delivery/20260916/software-gate-release-final/software_gate.json): **427 Python tests, 56 frontend tests**, eight stages passed, **365 source files unchanged**, completed 2026-09-16T06:33:30Z. [Actual v9 regression (public summary)](../evidence/week08-memory-v2/20260921/privacy-relocations/public/4d11c5fec1e1-v9-targeted-live.json): all 37 fixed post hoc cases terminal, 35 automated expectations met and W8-055/W8-082 retained as deviations. [All 127 citation identities](../evidence/week08-delivery/20260916/integrated/v9-source-verification/source-verification.json) matched persisted source text and locators. These structural/state/source checks do not certify claim entailment or learning quality; independent ratings remain blank. Current CPU-only continuation, explicit live general-mode continuation and 1440/390 general/fallback browsers passed their scoped checks; the exact mixed-question mock refusal and prior live/helper failures remain retained. Final package sidecars record archive hashes and isolated reconstruction separately.


Public delivery note — 21 September 2026: links labelled **public summary** open numeric summaries of retained historical records. Exact raw record hashes and restoration paths are listed in the [private relocation manifest](../evidence/week08-memory-v2/20260921/privacy-relocations/legacy-relocations.json). Full questions, reference labels, model text and blank review forms are distributed only in the separate authorized research bundle. These link changes do not alter any historical execution result or provide new semantic or human validation.

Before running historical catalogue or calibration commands that read `evaluation/reliability/week08_cases_v3.json`, an authorized research operator must restore the exact catalogue from the private bundle. Public application startup and the synthetic software tests do not require the held-out labels. The private lazy loaders verify their recorded hashes.

The [retained packaging failure and bounded correction](../evidence/week08-memory-v2/20260921/packaging/release-fix-verification.json) record a reconstruction mismatch for the verified `resources/official-corpus/corpus.jsonl.gz` asset. The exact resource-path exception preserves its required category, size and hash checks; other archive paths remain excluded. The first nine ZIPs are retained as failed artifacts. Five focused checks and the final full gate passed after changing only the packager and its existing regression test. Scientific outputs, study code and the private research archive are unchanged. New archive hashes and reconstruction are recorded in adjacent release sidecars.
