# Memory V2: implementation, operation and verification — 21 September 2026

Memory V2 stores typed, attributable learner state and selects relevant entries for the current question. The default learner flow remains textbook-based direct chat. Memory is opt-in, and turning the profile off suppresses memory for that turn. This record describes the implemented product and its software, browser and portable-installation evidence. Formal model-study outcomes are reported separately under the [registered protocol](week08-memory-v2-protocol-20260921.md).

The earlier [implementation checkpoint](memory-v2-implementation-20260921.md) and its evidence remain preserved. The frozen main-project software gate completed at **13:42:17 UTC on 21 September 2026**, with **828 Python tests, 86 frontend tests and all eight stages passed**. Its captured source files were unchanged during execution. See [the main gate](../../evidence/week08-memory-v2/20260921/software-gate-final/software_gate.json), [Python results](../../evidence/week08-memory-v2/20260921/software-gate-final/pytest.xml) and [frontend results](../../evidence/week08-memory-v2/20260921/software-gate-final/frontend_tests.log). A subsequent public-distribution gate passed the same test totals with zero skips in the isolated portable tree after a tests-only fixture correction. That correction remains outside the main project during the frozen studies; its exact scope is recorded below.

## What the application stores

The typed engine in [personalisation/memory_v2.py](../../personalisation/memory_v2.py) recognises preferences, learning goals, course context, self-reported observations and individual assessment performance. Entries carry a canonical field, scope, source identity, verification basis, revision and optional expiry. Global and subject-specific entries have separate identities. The versioned topic vocabulary supports scientific associations such as an ATP question using a relevant biology preference.

Preferences describe presentation choices such as detail, examples or terminology. An explicit difficulty statement remains a self-report. Assessment records describe the particular question and response that were scored. Broader mastery requires additional evidence and is not inferred from a single correct answer, a question alone or a model-generated impression.

The [typed extractor](../../personalisation/memory_extraction.py) validates exact quotations from the learner's owned messages. It has a maximum of two calls and 90 active seconds, including preparation and validation. A temporary instruction applies to the current request. Eligible lasting statements can produce a separate asynchronous memory job with a visible processing outcome. The frozen legacy reader and writer remain available for historical requests and the explicit M2 comparator.

The additive memory migration is [d9e53f6b012a](../../backend/alembic/versions/d9e53f6b012a_typed_learning_memory_v2.py), followed by the provider migration `e0a64c7d123b`. The main-database migration check found no changes to existing-column contents across the 44 pre-existing tables. That preservation check is scoped to the captured columns and rows; see [migration evidence](../../evidence/week08-memory-v2/20260921/migration/preservation-result.json).

## Preference precedence and current corrections

The effective order is:

1. The learner's current instruction.
2. A saved subject preference relevant to this question.
3. The saved global profile setting.
4. A global memory preference.
5. Relevant observations that satisfy their evidence rules.

For example, a saved request for detailed biology explanations can override a concise global setting on a relevant biology question. “Keep this answer brief” takes priority for the current response. It does not automatically replace the lasting biology preference.

Recognised explicit corrections are applied before the current request's learner-state snapshot is frozen. Current-turn instructions also mask conflicting older fields in the selected view. The owner-level event sequence orders manual changes, source statements and erasures. A delayed extraction from an earlier message cannot overwrite a later correction to the same canonical field. Repeated deletion advances the erasure fence, including when no visible entry remains.

The selected learner-state payload uses the configured token counter and a 768-token ceiling, including its reserved metadata allowance. It contains selected values, provenance references and exclusions. Full source-message bodies and scoring rubrics remain outside that prompt segment. A preparation failure has an explicit outcome; a revoked or expired frozen snapshot cannot be silently reused.

## Using the Memory page

Open **Learning memory** in the sidebar. **Use learning memory** controls the global opt-in setting. Turning it off preserves saved entries for inspection, editing or deletion, while preventing their use and further memory publication. Turning the profile off in chat independently suppresses memory for that answer.

**Memory summary** is derived from current eligible entries and has a revision identity. It is a management overview. The per-question reader chooses a smaller applicable state. An overview request failure displays an error and a refresh action while keeping entry-management controls available.

Open **Preview memory for a question**, enter a question and select **Preview learner state**. The response shows detected topics, selected fields, their scope and verification, and exclusion reasons. **Use profile for this preview** permits checking the profile-off outcome. The preview submits no answer and calls no answer model. Normal expiry maintenance may remove expired state. Changing the question, profile choice, enabled setting or summary revision clears the displayed result and prevents a late stale response from replacing it.

Each saved entry exposes its scope, revision, update time, expiry and verification basis. **View source message** opens the owned source text in a modal. **Edit** updates content, recognised field, scope or expiry using the displayed revision. A conflicting newer revision must be reloaded before saving. Editing an assessment changes it to an unconfirmed record; the earlier score cannot validate newly edited content.

**Delete** removes the saved memory and its derived content while keeping the original chat message under the chat retention lifecycle. The confirmation explains this distinction. **Undo memory save**, when offered beside a newly saved notice, removes that saved revision. It does not restore an erased body. **Recent memory processing** shows actual event status, operation/reason and safe error details; a failed extraction remains a failure.

## API, ownership and lifecycle boundaries

All routes below use the authenticated account under `/api/v1`. The [learning-state router](../../backend/app/modules/learning_state/router.py) and [memory service](../../backend/app/modules/learning_state/memory.py) enforce ownership. Source reads additionally verify the session owner, workspace and deletion state. Learners cannot use another account's memory identifiers to obtain its source messages.

| Operation | Endpoint and behaviour |
| --- | --- |
| Settings | `GET/PATCH /me/memory/settings`; updates carry the expected `version`. |
| Entry management | `GET /me/memories`, `PATCH/DELETE /me/memories/{id}`; mutations check the current revision. |
| Source inspection | `GET /me/memories/{id}/source`; returns an authorised original message. |
| Remove a recent save | `POST /me/memories/{id}/undo`; versioned erasure. |
| Overview and progress | `GET /me/memory/summary` and `GET /me/memory/processing`. |
| Current question preview | `POST /me/memory/preview` with `question` and `use_profile`. |
| Attributable statement | `POST /me/memories`; validates a typed exact statement against an owned source. |
| Assessment evidence | `POST /me/memory/assessments`; validates question/response identity, order, scoring basis and ownership. |

Automatic assessment confirmation requires the implemented exact-text or finite-numeric scorer, identified rubric and recorded result. Imported scores remain `recorded_unconfirmed`. Human confirmation requires explicit attestation from an identified signed-in reviewer; administrative role alone supplies no confirmation. There is no new practice interface in this change.

Disable, deletion, expiry and source invalidation affect future selection and frozen derivatives. Settings use a revocation epoch and compare-and-swap version. Deletion removes entry/revision payloads, suppresses re-extraction from erased sources and cancels stale work. Affected private drafts and diagnostic traces are redacted. Expired entries remain inspectable with their status but are excluded from new learner state. Re-enabling memory does not replay suppressed jobs.

The learner interface clears rendered memory on sign-out. Server ownership checks provide the access boundary; the UI's route and state cleanup provide additional separation. Public packages exclude evaluator-private catalogues, review keys, original learner histories and deployment credentials.

## Verified software and browser scope

| Evidence | Actual result and scope |
| --- | --- |
| [Focused memory checks](../../evidence/week08-memory-v2/20260921/memory/focused-final-attempt2.xml) | 45 passing unit and disposable-PostgreSQL checks: typed selection, current correction, delayed jobs, erasure, assessment provenance, ownership, HTTP preview, legacy M2 and evaluator resume guards. |
| [Memory component checks](../../evidence/week08-memory-v2/20260921/memory/ui-attempt2.json) | 11 passing component checks at the implementation checkpoint. |
| [App and Memory integration checks](../../evidence/week08-memory-v2/20260921/memory/app-memory-current.json) | 16 passing checks, including the updated summary/processing fixture and removal of rendered private memory plus session token on sign-out. These overlap the component checks and are not an additional independent sample. |
| [Memory browser verification](../../evidence/week08-memory-v2/20260921/memory/browser-final/verification.json) | Actual Edge and HTTP endpoints on a separately migrated disposable database: ATP/biology selection, current-instruction override, profile-off suppression, source modal/Escape, edit, disable and deletion with original-message preservation. |
| [Memory visual/runtime review](../../evidence/week08-memory-v2/20260921/memory/browser-final/visual-and-runtime-review.json) | Five individually inspected screenshots at 1440 and 390 pixels; no page errors. The temporary API had no provider key or answer worker. Owned services were stopped. |
| [Final full gate](../../evidence/week08-memory-v2/20260921/software-gate-final/software_gate.json) | 828 Python tests, 86 frontend tests and all eight stages passed on an unchanged captured source snapshot. |
| [Public-distribution gate](../../evidence/week08-memory-v2/20260921/public-distribution-attempt3/summary.json) | 828 Python tests and 86 frontend tests passed, with all eight stages successful and zero skips, in the portable public tree containing an independently authored tests-only patch. Production and evaluation-engine files remained unchanged. |

The browser checks used authored learner statements and made zero paid model calls. They establish the exercised software behaviour. Physical keyboard/IME use, assistive-technology review and independent scientific or pedagogical ratings remain separate activities. Earlier fixture, selector and asynchronous-wait failures are preserved alongside their successful later attempts.

## Fresh CPU installation and final public parity

A new installation directory and virtual environment were created on the existing Windows host. The installation used Python 3.13.2, locked dependencies, Torch `2.8.0+cpu`, `npm ci` and a successful frontend build. `pip check` passed. Its separate PostgreSQL instance used port 15932, API 18300 and frontend 15473; the main database and existing installations were untouched.

The imported corpus contained 48 immutable source objects and 10,594 vectors of dimension 384 for release `4f11bd70-a486-4d16-b216-78cfe499530a`. E5, the reranker and pgvector retrieval ran on the real CPU path. Two textbook turns were persisted, cancellation and history after sign-in passed, and source hashes/locators remained consistent. Answers were explicitly mock. See [installation summary](../../evidence/week08-memory-v2/20260921/portable/summary.json), [actual HTTP proof](../../evidence/week08-memory-v2/20260921/portable/http-attempt1.json) and [browser proof](../../evidence/week08-memory-v2/20260921/portable/browser-attempt1/verification.json).

The final [public-source parity receipt](../../evidence/week08-memory-v2/20260921/portable/source-parity-frozen-public.json) verifies **512 selected public source/configuration files and all 80 corpus/model/tokenizer resources**. Its inventory SHA-256 is `9ee4143e0f65d918605bb93b8a9313346c8283640f7b9cd98c0a3ada95ba018d`. The earlier installation summary records 515 files at its own checkpoint. The final sync updated eight approved loader/test/packaging files and preserved four newly excluded legacy evaluator JSON files outside the portable project. It retained all earlier installation and runtime evidence. Hash parity itself adds no new answer execution result.

The final sync ran with the portable applications stopped, and they remain stopped. The database volume is preserved. This is a fresh installation on the existing Windows host with cached downloads available; physical new-machine, Mac/MPS and final archive reconstruction evidence are separate.

## Public tests and private research inputs

Public distribution excludes the formal question and memory catalogues, review keys and research records. The optional study loaders fail with an explicit missing-input message until authorised research inputs are restored separately. Software tests use their own authored fixture inputs and can run without those research files.

The [unchanged public-tree rerun](../../evidence/week08-memory-v2/20260921/public-distribution-attempt2/summary.json) exposed **42 fixture dependencies**: 24 SciQ-related tests, 17 question-catalogue tests and one memory-catalogue test. Of these, 31 were unit tests and 11 exercised PostgreSQL. The run passed 784 Python tests; two optional Parquet checks were skipped because the acquisition dependency was absent. All seven other gate stages passed. The initial [attempt](../../evidence/week08-memory-v2/20260921/public-distribution-attempt1/summary.json) also retains its development-dependency and isolated-database setup failures.

The correction modifies five test modules and adds two public test-helper files in the isolated portable tree. Four new SciQ-shaped software records use the existing public test passages. The judge tests receive 24 synthetic labelled-value questions and 12 synthetic preference trajectories. All **257 existing assertion expressions and all existing test function names** remain unchanged. No private catalogue or formal reference was copied into that tree. [The patch verification](../../evidence/week08-memory-v2/20260921/public-distribution-attempt3/test-patch-verification.json) records before/after hashes, the exact failed tests and the independent fixture provenance.

Install the existing [development lock](../../requirements-dev.lock) for the software-quality tools and the optional [SciQ acquisition lock](../../requirements-sciq.lock) to exercise the Parquet checks. The portable environment installed both pinned sets, retained Torch `2.8.0+cpu` with CUDA unavailable, and passed `pip check`. The [focused rerun](../../evidence/week08-memory-v2/20260921/public-distribution-focused1/summary.json) passed all 64 affected checks. The full public gate then completed at **14:26:13 UTC on 21 September 2026**: **828 Python tests, 86 frontend tests, eight passing stages and zero skips**.

This public test run used the existing portable virtual environment and disposable `cs30_test_*` databases on port 15932. It made no external provider calls and started no application services. The main project's 512 captured public source/configuration hashes remained unchanged. In the portable copy, 507 of those files remained byte-identical; five tests changed and two helpers were added, yielding 514 selected files. The tested patch is held outside the main project for integration after the frozen studies and their archival checks finish. The earlier 512-file/80-resource installation parity receipt retains its original checkpoint.

## Administrator Models workflow on the isolated installation

The [actual Models browser receipt](../../evidence/week08-memory-v2/20260921/portable/models-browser-attempt2/verification.json) covers saving a clearly labelled local mock configuration, testing the answer and checker roles, and enabling the saved pair. Both roles produced persisted basic, structured and project-stage results. Enablement remained disabled until both project tests passed.

A successor with a 2,048-token context window failed the checker project's 4,096-token output reservation with `CONFIGURATION_ERROR`. It could not be enabled, and the previous active pair remained unchanged. The isolated environment was then restored to its environment-based settings. These were local mock probes with zero provider reservations or paid calls.

Three desktop/390-pixel screenshots were individually inspected in the [visual and workflow review](../../evidence/week08-memory-v2/20260921/portable/models-browser-attempt2/visual-and-workflow-review.json). The preceding attempt's helper selector failure remains preserved. [Cleanup evidence](../../evidence/week08-memory-v2/20260921/portable/admin-workflow-owned-apps-stopped.json) records stopping only the owned portable API, worker and frontend processes. Main model settings and corpus pointers were unchanged.

## Reporting and research separation

Memory state checks, extraction accuracy, appropriate use in an answer and learning benefit are distinct outcomes. M3 and M4 share the same typed writer and evidence gates; their reader selection differs. The M0–M4 harness freezes histories, source/configuration identities, expected-state records and common retrieved evidence, and preserves errors and uncertain-call reservations. Expected labels remain evaluator-private and are excluded from generation requests.

Member reports can cite the implemented state model, lifecycle controls, exact software counts and exercised browser/install flows above. Formal comparison results and actual independent ratings require their own terminal evidence. The implementation and verification work was executed by Codex; module responsibilities remain the team's ownership assignments.
