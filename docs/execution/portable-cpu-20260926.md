# CPU deployment rehearsal — 26 September 2026

A fresh Windows dependency environment started the current application, imported the preserved official corpus, and completed two HTTP question turns using real CPU retrieval. The answer provider was explicitly `mock`. This rehearsal used the same physical Windows host as development and an independent local PostgreSQL server. Separate physical Windows and Mac hardware remain external validation work.

## Installation and isolation

The rehearsal directory is `E:/5703/teaching_performance_20260926/portable/learning-assistant`. Public project files were copied from the current workspace. Eighty runtime-resource files were recovered from the retained complete package and checked against their recorded hashes. Three optional ONNX experiment artifacts were copied separately. The [initial staging receipt](../../evidence/teaching-performance/20260926/portable/staging-initial.json) records this inventory; the [prelaunch source receipt](../../evidence/teaching-performance/20260926/portable/source-sync-prelaunch.json) fixes the installed source checkpoint.

A new Python 3.13.2 virtual environment installed `requirements.lock` and `requirements-embeddings-cpu.lock`. The installed PyTorch version was `2.8.0+cpu`; its CUDA runtime was null and CUDA availability was false. A CPU tensor operation and `pip check` passed. The [dependency receipt](../../evidence/teaching-performance/20260926/portable/dependencies.json) records all installed package versions and dependency-file hashes. Frontend `npm ci` and the production build also passed.

The independent database uses PostgreSQL 16.15 and pgvector 0.8.6 on loopback port 18532, with data under `/var/lib/cs30-validation-20260926/data` in Ubuntu 24.04 WSL. Its [installation receipt](../../evidence/teaching-performance/20260926/teaching/isolated-postgres-installation.json) records package and source identities. The new database `cs30_portable_20260926` received all migrations through `f2c86e9f345d`. Generated database and JWT credentials remain in restricted local files outside the public delivery. The preserved Docker database, original source materials and historical delivery archives remained unchanged.

The following command completed successfully from the rehearsal project directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/release/start_local.ps1 -Install -UseExistingDatabase -DatabasePort 18532 -ApiPort 18600 -FrontendPort 15673 -Device cpu
```

The [launcher log](../../evidence/teaching-performance/20260926/portable/launcher-attempt1.log) records dependency checking, migrations, corpus import and service readiness. `-UseExistingDatabase` connects to the database configured in the local environment file. The normal Docker-backed launcher path remains available.

## Corpus and runtime observations

The imported active release contains four books and 10,594 real 384-dimensional embeddings. Import verification checked resource hashes, vector dimensions, model/configuration identities, source associations and publication conditions. Historical corpus records in the bundle retain their release relationships; active-vector counts refer specifically to the published release.

The [HTTP verification receipt](../../evidence/teaching-performance/20260926/portable/runtime-verification.json) records the following observations:

| Operation | Result |
| --- | --- |
| API readiness and frontend response | HTTP 200 at ports 18600 and 15673 |
| `What is photosynthesis?` | Answer with real CPU retrieval; cited *Biology 2e*, Chapter 8, page 235; observed end-to-end time 21.915 seconds |
| `Why does it need light?` | Follow-up answer with real CPU retrieval; cited *Concepts of Biology*, Chapter 5 / section 5.1, pages 134–135; observed end-to-end time 1.506 seconds |
| Source integrity | Every cited excerpt matched the stored official chunk and recorded text hash |
| Cancellation | A subsequent submitted request was cancelled and published no answer |
| Fresh-login history reload | Both saved answers and the cancelled user message remained available |
| Answer-provider calls | Zero; both answers used the explicitly configured mock provider |

The first request included model loading; the second used the warmed process. These two timings are installation observations. Comparative performance results use the separate registered repeated-measures protocol. Private account, session and request identifiers are retained outside the public project.

## Scoped frontend dependency repair

The fresh installation reported two high-severity audit entries associated with the js-yaml empty-merge CPU-exhaustion issue, [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh). Two transitive lockfile entries were patched: `@redocly/openapi-core` 1.34.19 to 1.34.20, and its exact dependency `js-yaml` 4.3.1 to 4.3.2. Direct dependency declarations and package membership stayed fixed.

The [lockfile receipt](../../evidence/teaching-performance/20260926/portable/frontend-lock-patch.json) preserves the complete before/after identities. Both the original project and the rehearsal environment completed `npm ci` and production builds. The [subsequent npm audit](../../evidence/teaching-performance/20260926/portable/npm-audit-after.json) reported zero vulnerabilities. The first original-project install encountered a loaded native-module file lock; its failure log remains retained. Restarting the identified Vite process allowed the dependency installation to complete, while the API and worker continued running.

## Release integration

The [final aggregate gate](../../evidence/teaching-performance/20260926/software-gate-final-02/software_gate.json) passed all eight stages: 936 Python tests, 87 frontend tests, Python lint/format/types, foundation and API contracts, chat boundaries, frontend types and production build. No tests failed or skipped. All 523 tracked executable/configuration source hashes remained unchanged during that gate. The preceding 932-test gate is also retained; four queue-timestamp regression checks were added before the final run.

The [final runtime synchronization](../../evidence/teaching-performance/20260926/portable/source-sync-final-runtime.json) checked 753 public project files and copied the current implementation into the installed rehearsal. The positively identified portable API and worker process trees were [restarted](../../evidence/teaching-performance/20260926/portable/restart-final.json). The frontend process and original-project services remained running. All [80 official resource files and three experimental ONNX artifacts](../../evidence/teaching-performance/20260926/portable/resources-final.json) matched their preserved hashes.

The [post-synchronization HTTP check](../../evidence/teaching-performance/20260926/portable/runtime-verification-final.json) repeated both real CPU retrieval turns, source verification, cancellation and history reload successfully. Its observed question/follow-up times were 12.102 and 1.300 seconds. Queue measurements of 316.970 and 177.553 milliseconds exactly matched the difference between the stored Sydney-offset submission timestamps and UTC worker-start timestamps. The active corpus still contained four books and 10,594 real 384-dimensional vectors, with migrations at `f2c86e9f345d`. These requests made zero answer-provider calls.

The service endpoints remain available for local review. Final report files are synchronized again after document generation. The portable rehearsal provides CPU installation, official-corpus import and ordinary question-flow evidence. Configured-provider teaching sequences, experimental comparisons, source-disclosure checks and human scoring retain their own evidence records.
