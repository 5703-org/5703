# Decisions and evidence boundaries

Decisions dated 2026-09-08. User-confirmed scope and inherited engineering defaults are distinguished below. None is a claim of human sign-off or runtime verification.

| ID | Decision | Reason and affected contract/tasks |
| --- | --- | --- |
| SCOPE-01 | Deliver one free-text, multi-turn learning assistant with independent evaluation. | v5 and the responsive refinement define the product. Reopens old MCQ-only, display-only-history and deferred-personalisation assumptions; INT-02, CHAT-01–12, GEN-01/08/09. |
| SCOPE-02 | Formal knowledge uses the four official books in the actual cs30_openstax_v0.2 source scope: Biology2e, Chemistry2e, Anatomy&Physiology2e and Concepts of Biology. Authored fixtures remain software tests only. | User correction plus original HongleYang/WEEK4_SUMMARY_AND_WEEK5_PLAN.md section1.1; DAT-01/03/08. Retired CollegePhysics is excluded. No current real release or old-pilot approval is inferred. |
| SCOPE-04 | Reconcile substantive PRD/SPEC/PLANS and all ledgers first, then immediately acquire/process/embed/publish/retrieve the real four-book corpus, then finish remaining original scope. Only answering LLM may mock. | Explicit latest user correction. Real corpus construction does not wait for answer-model credentials and cannot be labelled externally blocked merely because raw assets were absent from the supplied archive. |
| SCOPE-03 | Repository output is English; original evidence remains immutable. | Explicit v5 instruction; all workstreams. User conversation language does not require bilingual application copy. |
| L01 | One modular Python application, PostgreSQL/pgvector, one worker, one frontend and local Compose volumes. | Replaces microservices, Kubernetes, Kafka, multi-region and multiple-vector-store obligations; INT-04, BE-01/16. |
| L02 | Learner/admin roles, ownership, single workspace and password/account operations. Retain legacy workspace IDs for compatibility. | Replaces multi-tenant policy/SSO/MFA/email-registration infrastructure; BE-02/03, FE-02. |
| L03 | Database jobs, attempts and execution tokens; publish each validated message/answer/citation set atomically. | Replaces new message bus, generic dead-letter service and exactly-once external-call promises; BE-07/15, CHAT-08; AC-13. Existing outbox is an asset, not a reason to expand it. |
| L04 | Configurable bounded uploads/tokens/time/calls and local concurrency; preserve unknown usage/cost. | Replaces distributed rate-limiting and accounting platforms; GEN-06, BE-13; AC-11/25. |
| L05 | No initial answer/query caches; optional embedding cache keys include content/model/preprocessing revisions. | Avoids stale-source data and cache broadcast work; RET-01/06, DAT-10. |
| L06 | Evaluator-only label files/private store, excluded from API/answer-worker mounts and DTOs. | Replaces mandatory dedicated DB gold roles/schemas while retaining no-gold-input invariant; QA-03, BE-11; AC-23. |
| L07 | One manifest per asset/release, immutable experiment configs and a short decision record. | Replaces compliance workflow and audit warehouse; DAT-01, INT-08/09; AC-19. |
| L08 | Tested local backup/restore, job inspection/retry, rollback and targeted dry-run cleanup. | Defers automated cross-backup erasure, public TLS automation, chaos platform and SLA claims; BE-16/17; AC-20/33. |
| L09 | Routine coding proceeds autonomously, recording actual executor and pending human review separately. | Domain ownership/reporting weeks are not approval gates; all 108 tasks. |
| ENG-01 | Actual tested local Python is3.13.2 with locked FastAPI, SQLAlchemy2, Alembic, PostgreSQL16/pgvector and React/TypeScript/Vite; the source suggested3.12 as an initial target. | Current installation/Compose evidence supersedes the proposed target without attributing that choice to the original diagram; INT-04. |
| ENG-02 | Default R0 uses normalized e5-small-v2 embeddings, 384 dimensions, query:/passage: prefixes and exact cosine search. | v5 defaults; validate actual tokenizer/model revisions and dimensions. Authored mock embeddings must be separately labelled; RET-01–04. |
| ENG-03 | Default chunk target/cap/overlap are 320/448/48; top-k=5 with validation alternatives 3/5/10. | Preserve section boundaries and exact source spans; DAT-06, RET-03/10. |
| ENG-04 | Token maxima: evidence 3000, recent history 2000, extractive summary 512, output 1024 chat/768 MCQ. | Combined real tokenizer/window check remains mandatory, not sum-of-maxima assumption; RET-04, CHAT-03. Drop whole evidence chunks before silent truncation. |
| ENG-05 | One request has a 4-call total, 180-second active execution budget and 60-second per-call timeout. At most one format repair shares those totals with preparation and transient retries. | Queue wait is not active time; counters survive manual retries/restart. Unknown interrupted external completion is explicit; GEN-06, BE-07. |
| ENG-06 | Durable worker plus polling; stop/retry/regenerate use server lifecycle, no simulated token stream. | Lightweight real asynchronous behaviour; FE-04, BE-07, CHAT-08. |
| ENG-07 | Profile policy enters the main answer call. Benchmark histories/profiles are empty; profile-off chat keeps real history. | Separates one-pass product personalisation from C0/C1/C2 studies; PER-02/05/06, GEN-08/09. |
| ENG-08 | Preserve prior response until a successful latest-answer replacement switches the active revision atomically. | Failed regeneration cannot erase prior text/citations/feedback; CHAT-08, BE-15. |
| UI-DEFAULTS | Light restrained layout, 50rem reading column, 16rem desktop sidebar, 28rem evidence overlay, breakpoints 640/1024 CSS px. | Responsive document values are project defaults, not OpenAI branding or WCAG certification; FE-12, QA-12. Full design lives in ui_design.md/responsive_spec.md. |

## Inputs that require real evidence

The source archive initially omitted the historical Concepts of Biology PDF. Official acquisition on8September2026 recovered the exact historical SHA256, and physical pages1–2 were inspected as cover/blank. The old pilot records remain unchanged; new reviewed processing and the complete four-book E5 release are documented in `docs/execution/openstax-corpus-report.md`. A different future PDF hash requires new identity/review and cannot inherit these decisions.

Live model/provider credentials, actual selected model/tokenizer checkpoints, approved research execution limits, SciQ revision/splits, qrels, independent ratings and physical-device keyboard observations are not established by configuration examples or source reports. Track exact current availability in `../execution/blockers.json`; continue all independent software work. Do not ask for routine signatures from named owners.
