# CS-30-1 implementation specification

This is the actual-system entry point, reconciled with the user's latest priority correction. Product intent is in [PRD.md](PRD.md); full task status and next work are in [PLANS.md](PLANS.md). Detailed contracts remain in `docs/foundation/`, the executable DTOs in `contracts/` and the actual migrations in `backend/alembic/versions/`. A design, mock test or historical report is never a substitute for an executed real-data stage.

## Original architecture and implementation map

The original overall-system diagram is Figure1 on physical/printed page1 of [CS30-1_Project_Framework_and_Delivery_Workflow.pdf](../development_inputs/sources/COMP5703/CS30-1_Project_Framework_and_Delivery_Workflow.pdf), visually checked against [the rendered page](evidence/source_audit/original-framework-page-1.png). Another original baseline image is [architecture-en-preview.png](../development_inputs/sources/COMP5703/tut5/xianshu/architecture-en-preview.png), which has no pagination. Exact module/connection verification is in [source-architecture-audit.md](docs/execution/source-architecture-audit.md). The v5 DOCX files reference historical architecture and contain no embedded figures. Newly authored Mermaid diagrams explain the implementation and are not claimed as original figures. The old SciQ-first experimental flow does not replace the required free-text product flow.

| Actual boundary | Producer → consumer | Implementation | Current evidence boundary |
| --- | --- | --- | --- |
| Browser → API | React forms/chat → authenticated FastAPI routes | `frontend/src`, `backend/app/main.py` | Real browser/API journeys with mock answering, including actual official-source provenance; current evidence is linked in the UI audit |
| API → durable storage | Identity/session/command validation → PostgreSQL records | identity, learning, answering and experiment modules | Real PostgreSQL ownership, concurrency, lifecycle and migration tests |
| Job claim → execution | One worker → parser/release/answer/teaching services | `backend/app/worker.py` | Real worker fencing, cancellation and recovery tests |
| Original → cleaned units | Official PDF bytes → page/section units and quality evidence | `pipelines/parse.py`, knowledge service | All four official full PDFs processed; 4,638 pages accounted, 73 reviewed exclusions and 15 recovered originals; source semantics remain bounded |
| Units → chunks | Source spans → bounded structure-aware chunks | `pipelines/chunk.py` | All 10,594 full-corpus chunks pass source/span/hash/token checks; 50 deterministic samples checked against 63 original pages |
| Chunks → embeddings | Pinned local E5 tokenizer/model → normalized 384-dimensional vectors | `retrieval/embedding.py` | 10,594 genuine normalized 384-dimensional vectors, using fixed-revision E5 CUDA and validated identical-input caches |
| Vectors → retrieval | pgvector cosine ordering → selected source snapshots | knowledge service, `retrieval/ranking.py` | Real E5/pgvector retrieval: all 15 scheduled queries and source-unavailability filtering verified; no formal relevance score claimed |
| Context/profile/evidence → answer | Frozen inputs → single answer-generation service | conversation, personalisation, generation modules | Mock and controlled-error tests; live answer quality unverified |
| Answer → citations/history | Strict response → atomic answer/message/evidence publication | answering service | Real PostgreSQL and browser source-snapshot checks, including official OpenStax passages |
| Evaluation → shared service | Public frozen command → same worker → private scoring | experiment module, separate `evaluation/` | Actual mock software execution in both protocols; real research results absent |

## Runtime and module ownership

The runtime contains one React/TypeScript/Vite frontend, FastAPI API, one synchronous durable worker and PostgreSQL16 with pgvector. There is no distributed broker or second answer engine. Python3.13.2 is the locally tested environment; backend/frontend dependencies are locked. Compose provides independent API/worker/frontend images and database/source volumes. The evaluator image/process is optional; its private dataset and output mounts are absent from the API/answer worker.

Routes perform authentication and input validation. Domain services own transactions and lifecycle rules. Parser, embedding, retrieval, language-model and profile adapters carry no evaluator gold labels. The learner input is exactly `{content,use_profile}`. The answer provider remains explicitly mock while the active formal corpus uses real OpenStax data and real local E5 embeddings.

## Actual persistent model

The runtime tables are established by retained migration `0001_initial` and additive migrations `3ae1ba39fe7f`, `a410a277e3a6`, `79f9729b3eae`.

| Tables | Actual representation/invariant |
| --- | --- |
| users, roles, workspaces, student_profiles | Existing identity foundation; password hash, token_version, ownership, saved profile revision |
| sessions, messages | Ordered per-session messages; unique(session_id,sequence); only an active validated answer revision enters history |
| snapshots, session_summaries | Profile and conversation snapshots share `snapshots.kind`; bounded attributable summaries have source IDs, hash, cutoff and invalidation |
| documents, document_versions | Source metadata and visibility; immutable original bytes identified by unique SHA256 and storage-root-relative path |
| processing_runs, source_units, chunks | Immutable processing configuration/lineage; raw and cleaned unit text, quality issues; chunk text/hash/pages and character spans |
| configurations, corpus_releases, release_chunks, active_corpus | Immutable configuration and release manifests; actual learned vectors belong in `release_chunks.embedding` (pgvector); one active release pointer |
| answer_requests, jobs, attempts | Logical request, persistent cumulative budget, independent job attempts/execution tokens and provider events |
| answers, evidence_snapshots, citations, feedback | One published answer per request; exact submitted passages and source identity; feedback stays with the original revision |
| experiment_runs, experiment_items, teaching_study_records | Frozen public workloads and all terminal outcomes; independent teaching-study budgets/results; no gold-label columns |
| outbox_events | Retained identity/session event evidence; not a new message-bus prerequisite |

Conceptual names such as `profile_snapshots`, `embeddings`, `quality_issues` and `teaching_outputs` in older design text are represented by the shared/JSON-bearing tables above; they are not separate implemented tables. See [data_model.md](docs/foundation/data_model.md) for constraints and transaction detail.

## Source-to-answer processing

1. **Acquisition:** use the four official books named in PRD. Save requested/final URLs, retrieval timestamp, exact edition/revision, PDF license text, byte count and SHA256; preserve originals. Record historical/current hash differences rather than overwriting referenced bytes.
2. **Registration:** validate file signature/type/path/size and supplied manifest hashes. Equal bytes reuse a version; changed originals receive new immutable identity. Store originals under `STORAGE_ROOT/originals/`.
3. **Parsing and cleaning:** inspect every physical page, preserve actual book/section/page locators and raw text, conservatively normalize text and remove only identified repeated furniture. Persist raw/clean hashes and warnings. Empty, unreadable or malformed units stay in an explicit quarantine report.
4. **Chunking:** default structure-aware target320, cap448 and overlap48 use the actual pinned embedding tokenizer for real data. Preserve section boundaries, original source-unit spans and stable content hashes. No silent token truncation or unexplained missing pages.
5. **Quality decisions:** report successful/blocked/excluded counts and reasons. Any exclusion must identify the unit and a substantive inspected reason; hard pages are not discarded to force publication. Quality/diff exports retain changed and removed content and annotation-review implications.
6. **Real embeddings:** run `intfloat/e5-small-v2` revision `ffb93f3bd4047442299a41ebb6fa998a38507c52` locally,384 dimensions, `query: ` / `passage: ` prefixes, actual512-token window checks and normalized finite vectors. Record exact model/tokenizer files and processing configuration. A mock hash vector cannot pass this formal stage. Exact model files and current offline CUDA inference are verified in `evidence/corpus/e5_download.json` and `e5_verification.json`; all 10,594 full-book vectors have now been built, validated and activated with source checks in `evidence/openstax/v5/publication.json`.
7. **Storage/release:** store actual text and vectors in PostgreSQL/pgvector; validate counts, dimensions, content/config/model/vector hashes and source joins. Build before activating. Atomic activation preserves the previous pointer on failure. A legacy release missing a historical integrity baseline must be explicitly reprocessed/rebuilt, never silently backfilled.
8. **Retrieval:** prepare a standalone query from current intent and attributable session context; E5 query encoding and pgvector `<=>` ordering operate on the active release. R0 is dense; R1 is BM25; R2 is RRF(k60); R3 is a configured cross-encoder. E1 always means frozen R0 and E0 means no retrieval. Test meaningful questions, unrelated questions, unavailable sources and exact PDF provenance.
9. **Answering:** select current authorized evidence, freeze profile/history, respect combined context/output limits and call the answer adapter. Answer mock mode is explicitly labelled and is independent of real retrieval. Reused passages require current authorization and a relevant same-topic reference; assistant prose is never evidence.
10. **Publication/citations:** parse strict mode-specific JSON, check citations against actual submitted passages, recheck source visibility/job token and atomically save answer, evidence, citations and active message revision. Historical evidence returns exact retained text or explicit410; it never silently redirects to a new book version.
11. **Evaluation:** keep SciQ stems/options separate from private labels/support; freeze run/configuration/IDs and retain every scheduled outcome. OpenQA uses ChatResponseV1 and compact EM/F1; MCQ uses its own response/accuracy. Real scores and independent human ratings remain unverified until actual research runs/review occur.

## States, concurrency and limits

Job states: queued → running (or bounded retry_wait) → succeeded/failed/cancelled. Logical answer states: queued → processing → answered/clarification/refused/error/cancelled. Processing states expose registration/parsing/cleaning/validation and ready/quarantined/failed; `ready` means validated chunks, while vector creation belongs to release execution. Releases progress building → validated → active/retired, or failed. Experiments retain draft/frozen/running/completed/cancelled/environment_changed/failed states.

One active answer job is allowed per session. A matching actor/route/idempotency key/body returns the original receipt; changed content returns409. Retry is only for an eligible failed/cancelled latest interactive request, with the same snapshots and consumed budget; formal terminal benchmark outcomes require a new run. Regeneration creates a new request and preserves configured maximum budgets while resetting its own consumption; the previous active answer/feedback stays until a valid replacement commits.

Default bounds:4000-character chat input,20 profile topics of200characters, recent6 exchanges/2000 conservative tokens, extractive summary512, evidence3000, output1024 chat/768MCQ; actual combined model window is checked. A request has at most4 provider calls,180 active seconds and60 seconds per call, with at most one format repair shared with retries. Embedding/reranker/provider work must not hold a job row lock that blocks Stop. Cancelled/stale tokens cannot publish.

## API and operational interfaces

The actual route/schema authority is [contracts/openapi.json](contracts/openapi.json), generated from the running application definitions, with generated TypeScript at `frontend/src/generated/api.ts`. Success/error envelopes carry a safe matching trace ID. Identity/profile/session/chat/job/answer/evidence/feedback routes serve the product; documents/processing quality+diff/configurations/corpus releases/experiments/teaching studies serve administration. Detailed method/actor/payload mappings remain in [api_contract.md](docs/foundation/api_contract.md).

`python -m app.cli --help` lists implemented migrations, explicit development seed, account operations, ingest, process quality/diff export, corpus build/activate/rollback, job inspect/retry/recover, configuration creation, source visibility, feedback review and reviewed orphan cleanup. Backups/restores are in `scripts.release`; source originals and saved evidence are retained. Operational commands and current results are linked from [runbook.md](docs/runbook.md).

## Current verification and gaps

Presentation policy is compiled into the main generation call and frozen with each request. `generation/parser.py` validates structural and evidence constraints and records `semantic_preservation: null`; semantic-preservation instructions are not an automatic entailment check. Short/long/simplification verification must retain the actual output length and distinguish requested presentation from observed model behavior.

All four official complete PDFs (4,638 pages) were acquired, hash/license checked, parsed and reviewed. 5,541 source units retain 73 documented exclusions and 15 supplemented originals; no blocking units remain. 10,594 actual E5 vectors of 384 dimensions are published in PostgreSQL/pgvector release 4f11bd70-a486-4d16-b216-78cfe499530a. All 15 real queries and the reversible unavailable-source filter check passed; original/answer/evidence records are unchanged. Full-book visual/equation semantics and independent scientific review remain unverified. Only answer generation remains mock; formal answer/relevance/human research is not established.

The [per-book report](docs/execution/openstax-corpus-report.md) and its machine-readable source enumerate editions, licenses, hashes, paths, recovery reasons, exact counts and source excerpts. Parser `pypdf_bookmarks_v5` follows actual PDF outline destinations. Fourteen agent-reviewed real OCR transcripts and one exact official portrait description supplement native text; all original issues and failed candidates remain preserved. Footers/blank/cover decisions are tied to exact PDF/page/native-text hashes. No complete diagram or equation understanding is claimed.

Actual full-corpus backup-v2 restored to the distinct `cs30_restore_openstax_20260908` database and independent storage. Seven originals, 44 supplementary source artifacts, complete user/profile values, all corpus/vector values, active pointer and historical answer/evidence fingerprints match the exported database snapshot. Evidence: `evidence/recovery/backup-real-openstax-20260908/restore-cs30_restore_openstax_20260908.json`.

Current v5 official-source browser/API journeys and long-history pagination passed with explicitly mock answering; earlier authored checks and v4 release switching retain their own scopes. Official SciQ acquisition and actual R0/R1/R2/R3 diagnostics have separate recorded evidence. The current stable-source regression passed 236 Python and 25 frontend checks plus type/format/contract/build stages; the earlier packaged installation is separately linked from the progress ledger. Hosted answering, formal semantic metrics, independent qrels/ratings and physical-device acceptance are not implied by corpus publication.

The [local audit continuation](docs/execution/local-audit-continuation.md) adds actual shared-service loopback adapter switching, three-level profile request verification and browser key/suggestion/error checks. The only application change since candidate 2 is guarded scrolling for newly rendered errors and terminal/pending states. [Generated delivery views](docs/delivery/README.md) are deterministic reports of the canonical ledgers and do not define alternative interfaces or requirements.

Worker responses now include measured preparation, deterministic query preparation, actual retrieval, generation-service wall time and adapter computation with the scope `worker_execution_before_answer_insert_v1`. Final commit and queue time are excluded from that worker total; the separate HTTP workload records queue-inclusive observation. Exact boundaries and actual results are in [performance.md](docs/performance.md). Historical traces are not backfilled.

The earlier post-v5 backup-v2 is `evidence/recovery/backup-final-v5-20260908/manifest.json`, created at 2026-09-08T09:07:43Z after the v5 publication and technical workloads. It restored successfully into the new database `cs30_restore_final_v5_20260908` and `artifacts/restore-final-v5-20260908`. All seven original files, 44 supplemental files, complete identity/profile/corpus/vector/history fingerprints and the v5 active pointer match. [Restore evidence](evidence/recovery/backup-final-v5-20260908/restore-cs30_restore_final_v5_20260908.json). Earlier v4 snapshots and the separate visibility drill remain preserved.

The real strategy-only fixed-window comparison has 11,461 vectors in a separate validated, unactivated release; the published structure release stays at 10,594. Full source coverage, source identity and shared-input vector equivalence are recorded in [chunking_comparison.md](docs/chunking_comparison.md). The actual nullable late R0 pool and prepared full-validation k/embedding studies are in [r0_review_pool.md](docs/r0_review_pool.md) and [controlled_study_designs.md](docs/controlled_study_designs.md). Prepared configurations are not scientific run results, and unavailable labels remain null.

The v4 nullable pool is not compatible with v5/fixed releases. Configuration and paired-schedule preparation is complete; compatible reviewed qrels remain a prerequisite for valid relevance measurements. [Final document review](docs/execution/final-document-review.md) retains this boundary and identifies superseded historical migration notes.

The latest complete snapshot is `evidence/recovery/backup-final-comparisons-20260908/manifest.json` (2026-09-08T09:33:08Z). It includes the active v5 release, the unactivated fixed-window comparison and all nine retained releases. A new restore into `cs30_restore_final_all_20260908` and `artifacts/restore-final-all-20260908` passed all complete identity/profile/corpus/vector/history fingerprints and seven-original/44-supplement file hashes. [Final restore](evidence/recovery/backup-final-comparisons-20260908/restore-cs30_restore_final_all_20260908.json). Earlier snapshots remain preserved and retain their earlier point-in-time scope.
