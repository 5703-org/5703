# Local project handover

Start with [PRD.md](PRD.md) for the required product, [SPEC.md](SPEC.md) for the implemented system and [PLANS.md](PLANS.md) for the original 108 tasks and their evidence. The source requirements retain all 60 acceptance checks and 12 responsive subchecks. The actual original architecture diagram is identified by source file, Figure 1 and physical/printed page 1 in [the source architecture audit](docs/execution/source-architecture-audit.md).

## Working application

The Windows host application uses the project virtual environment, API at `http://127.0.0.1:8000`, frontend at `http://127.0.0.1:5173` and PostgreSQL at `127.0.0.1:55432`. Restart instructions are in [README.md](README.md); detailed account, worker, corpus and recovery commands are in [the runbook](docs/runbook.md). Preserve the configured `.env` and existing Docker data volume. Start only one worker.

The ordinary learner flow is login, a new conversation, a question such as “What is photosynthesis?”, a dependent follow-up, simpler wording, source inspection, preferences and history after login again. Responses display their mock-answering mode. The source corpus and embeddings are real. The evaluator is not required for chat, and its private inputs are absent from the application runtime.

## Real knowledge and reproducibility

[The per-book report](docs/execution/openstax-corpus-report.md) is the authority for current source URLs, editions, acquisition dates, licensing, SHA-256 values, original file locations, actual processing coverage, exclusions, OCR recovery, chunk/vector counts, model revision, database publication and original-page retrieval examples. Exact historical originals, processing versions, releases, answers and citations remain preserved.

The real E5 model uses a fixed revision and tokenizer. The optional Linux/CUDA runtime and its actual read-only restored-corpus query proof are documented in [development checks](docs/development_checks.md). Base Compose is a smaller independently tested mock-capable installation. [Data rebuild](docs/data_rebuild.md), [source recovery](docs/source_ocr.md) and [real embeddings](docs/real_embeddings.md) explain the actual processing route and its limits.

Complete backup-v2 data is kept locally under `evidence/recovery/backup-real-openstax-20260908/`, separate from distributable source packages. A portable restore into `cs30_restore_openstax_portable_20260908` verified all original and supplementary files, corpus vectors, identity/profile records and historical evidence against the exported snapshot. This is a point-in-time recovery proof; later conversations and releases are not falsely described as included in that earlier snapshot.

The earlier post-v5 backup-v2 is `evidence/recovery/backup-final-v5-20260908/manifest.json`, created at 2026-09-08T09:07:43Z after the v5 publication and technical workloads. It restored successfully into the new database `cs30_restore_final_v5_20260908` and `artifacts/restore-final-v5-20260908`. All seven original files, 44 supplemental files, complete identity/profile/corpus/vector/history fingerprints and the v5 active pointer match. [Restore evidence](evidence/recovery/backup-final-v5-20260908/restore-cs30_restore_final_v5_20260908.json). Earlier v4 snapshots and the separate visibility drill remain preserved.

The latest complete snapshot is `evidence/recovery/backup-final-comparisons-20260908/manifest.json` (2026-09-08T09:33:08Z). It includes the active v5 release, the unactivated fixed-window comparison and all nine retained releases. A new restore into `cs30_restore_final_all_20260908` and `artifacts/restore-final-all-20260908` passed all complete identity/profile/corpus/vector/history fingerprints and seven-original/44-supplement file hashes. [Final restore](evidence/recovery/backup-final-comparisons-20260908/restore-cs30_restore_final_all_20260908.json). Earlier snapshots remain preserved and retain their earlier point-in-time scope.

## Source package boundaries

`python -m scripts.release.package --output artifacts/deliverables/NEW_NAME.zip` creates a new archive without overwriting an earlier handover. Its embedded manifest identifies every file by size and SHA-256. `python -m scripts.release.package --verify PATH_TO_ZIP` checks membership, paths and all hashes. Source notices are in [SOURCE_NOTICES.md](SOURCE_NOTICES.md).

The source package contains implementation, tests, English documents, configuration examples and permitted execution evidence. It excludes actual environment files, database dumps, original textbook PDF bytes, model weights, evaluator-private SciQ data/labels, private experiment exports and dependency caches. These remain at their documented local paths. Original user attachments and the untouched extracted source archive also remain outside the source ZIP. A source ZIP is not a complete database/model/textbook backup.

## Evidence and remaining acceptance

Current software checks, original numbered acceptance records, actual browser journeys and per-book data proof have distinct scopes. Failed attempts remain inspectable. Source snapshots bind the aggregate gate to the executable files tested; an otherwise passing run with changing source files is not recorded as a final stable pass.

[Performance](docs/performance.md) distinguishes actual worker/queue/retrieval timings from mock provider fields and separate evaluation observations. [Retrieval diagnostics](docs/retrieval_diagnostics.md) retain every scheduled condition and do not infer relevance quality from rank changes. [SciQ acquisition](docs/sciq_acquisition.md) records the actual full dataset, source hashes and duplicate-option anomalies without silently excluding them from a formal denominator.

Live answering configuration was explicitly deferred by the user. Real answer effectiveness, formal semantic/relevance judgments, independent blind ratings and physical-device/native-IME/screen-reader review remain pending where named in the ledgers. Full-book image, equation and reading-order fidelity has not been independently certified. Mock answers may refuse supported questions or provide limited explanations; their test outputs do not establish scientific correctness or learning gains.

## Delivered local verification

The current unchanged-source gate passes 236 Python and 25 frontend checks plus formatting/lint/typing/contracts/build. [Candidate installation proof](evidence/handovers/candidate-20260908T093208Z/verification.json) verifies its exact earlier runtime from fresh no-cache base images and empty volumes. Since that installation, one application file changed: `frontend/src/Chat.tsx` now reveals new error/terminal status when following the latest content, while preserving deliberate older reading positions. Current component and actual browser checks cover that change; the new package is not labelled as a repeated clean installation. Runtime source continuity and the separately verified build retain these limits. `scripts.verify.chat_journeys` is the authored-fixture smoke used by the clean installation: three cited mock answers and one known practical-example refusal. Use the separate real-corpus checks for the official knowledge flow.

[The continuation report](docs/execution/local-audit-continuation.md) records the required [owner/week delivery views](docs/delivery/README.md), configurable adapter drill, actual keyboard/suggestion/rejection checks and the three-level presentation matrix. The latter retained three long-request refusals and unchanged short/simplified excerpts; software verification does not establish presentation quality. The latest complete backup remains the recorded 09:33 snapshot and does not include these later verification conversations.

Current package: `artifacts/deliverables/CS30-1_local_project_2026-09-08_documentation_update2.zip`. The original `CS30-1_local_project_2026-09-08.zip` is preserved with its original manifest and evidence. [Current numbered-scope audit](evidence/source_audit/documentation-review-ledger-reconciliation.json) binds the amended ledgers; [prior audit](evidence/source_audit/final-ledger-reconciliation.json) retains its earlier scope.

[Final document consistency review](docs/execution/final-document-review.md) clarifies historical migration notes and the missing compatible-qrel boundary. The earlier verification-update1 package remains preserved; application code and the236/25-test evidence are unchanged.
