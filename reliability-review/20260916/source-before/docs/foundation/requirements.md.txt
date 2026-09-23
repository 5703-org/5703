# Effective requirements

Version5.0 plus responsive refinement and the user's real-knowledge-base priority correction, reconciled2026-09-08. [PRD.md](../../PRD.md) is the substantive product entry point. Sources are listed in `source_inventory.md`. This is a design and acceptance contract; current implementation evidence belongs in `../execution/`.

## Actors and scope

Learners own accounts, profiles, sessions, messages and answer feedback. Administrators additionally manage accounts, corpus processing/releases and experiments, and review feedback. The single worker executes durable jobs. The offline evaluator holds references/labels and submits only gold-free commands. Accountable domain owners are reporting metadata, not user accounts or fabricated reviewers.

| ID | Requirement and observable acceptance | Primary task/check coverage |
| --- | --- | --- |
| REQ-01 | Sign in, change/reset passwords and disable accounts; ownership and learner/admin authorization apply to every resource. Disabled or old credential versions fail. | BE-03, FE-02; AC-14/31 |
| REQ-02 | `/chat` accepts one natural-language message, never mandatory choices or benchmark selection. A first response is saved as prose in ChatResponseV1. | CHAT-05/06, FE-03; AC-08/36/44 |
| REQ-03 | Owned completed active revisions before a sequence cutoff enter actual model input. No future, failed, other-session or other-user transcript enters it. | CHAT-02, BE-05; AC-38/43; HC-09 |
| REQ-04 | Bound history and extractive summaries with covered-message IDs, cutoff, policy version/hash and no duplicated prefix. Retries keep immutable snapshots; missing referents cause clarification. | CHAT-03; AC-42 |
| REQ-05 | Prepare standalone queries from current intent and attributable context, including topic changes and corrections; benchmarks use their unchanged stems. | CHAT-04, RET-03; AC-38/40 |
| REQ-06 | Distinguish supported answer, greeting/social response, clarification, insufficient-evidence refusal, invalid output and provider/system failure. No failure is disguised as successful refusal. | GEN-04/05; AC-09/10/39; HC-05/06/07 |
| REQ-07 | Exact submitted source passages receive request-local IDs and immutable provenance. Re-explanations may reuse authorized old text with newly assigned IDs; historical assistant prose is never a source. | GEN-07, RET-04/05; AC-08/41 |
| REQ-08 | Stop, retry and regenerate obey durable lifecycle and finite aggregate budgets. Only the latest completed answer may regenerate, retaining old active text/feedback until atomic success. | BE-07/15, CHAT-08; AC-12/13/24/25/45 |
| REQ-09 | Explicit Beginner/Intermediate/Advanced profiles save optimistic revisions; main generation consumes a per-turn frozen compiler policy. Profile off retains history; temporary wording requests do not mutate the saved level. | PER-01–05, CHAT-07; AC-15/29/30 |
| REQ-10 | Administrator PDF/TXT ingestion validates types/size/path/hash and stores immutable originals. Identical bytes reuse a version; failed/quarantined content cannot become retrievable. | DAT-01–05, BE-06; AC-03/04/05 |
| REQ-11 | Structure-aware chunks retain source-unit character spans, section/page locators and stable IDs. Changed processing preserves old units/chunks and creates new processing identity. | DAT-06/07; AC-28 |
| REQ-12 | Release validation checks embedding compatibility/counts/dimensions/locators before an atomic switch. Active source state governs new retrieval and old citation availability. Rollback rejects invalid targets without losing the current release. | DAT-08/10, RET-01/02/06; AC-06/14/26/35 |
| REQ-13 | R0 exact cosine, R1 BM25, R2 one-based RRF(k=60) and R3 cross-encoder ranking use the same released chunks and shared retriever contract. R3 unavailability is explicit. Frozen E1 stays R0. | RET-03/07–10; AC-19/34/35 |
| REQ-14 | Login, sessions, citations, profiles and contextual chat remain usable without evaluator services or SciQ mounts; capability readiness reports exact missing reasons separately. | BE-12, CHAT-06; AC-37 |
| REQ-15 | Feedback is editable by its author and reviewable by an administrator, with saved state/note/issue. It neither trains a model nor changes a profile automatically. | BE-10, FE-09; AC-32 |
| REQ-16 | Shared chat/OpenQA/MCQ execution enforces different typed inputs before provider calls. OpenQA excludes options/distractors/gold/support/history/profile; MCQ exposes candidates but never the correct label. | GEN-08, QA-02/03, CHAT-09; AC-07/17/22/23/36/46; HC-03/04 |
| REQ-17 | Frozen experiment items retain all outcomes and scheduled denominators. Resume does not repeat successful items; source/configuration changes are explicit, never silent baseline mutation. | QA-06/07, BE-11; AC-18/19/27 |
| REQ-18 | Score OpenQA compact answers with frozen conservative EM and multiset F1 rules; MCQ uses selection accuracy. Negation, signs, numeric units, missing answers and valid paraphrases expose lexical-proxy limitations. | QA-05/08, CHAT-09; AC-18/47 |
| REQ-19 | Separate C0/C1/C2 studies freeze question/evidence/base answer, retain independent output statuses, prepare blinded anchored rubrics and analyze paired ratings. Missing human ratings remain unavailable. | PER-06–09, QA-10; AC-19/29 |
| REQ-20 | API/worker/frontend share typed contracts, standard errors, redacted traces and bounded inputs; missing live configuration never falls back to mock. | INT-03/04, BE-13/14, GEN-02; AC-01/11/22; HC-02/08/10/11 |
| REQ-21 | Deliver actual installation, migrations, account bootstrap, ingestion/build/activation, evaluation/resume, backup/restore, jobs and targeted orphan cleanup commands. | BE-16/17, INT-10; AC-02/20/33 |
| REQ-22 | All new project output is English. Preserve historical source files/tests/results and old MCQ rows, and record actual authorship, run times and unresolved checks without invented approvals. | INT-01/09/10, CHAT-11/12, QA-14; AC-21/48; HC-01/12 |
| REQ-23 | Restrained light UI uses content-first chat, compact mock/live and profile information, safe Markdown, complete answer bodies and reachable source/action controls. | FE-01/05–08/12; AC-16/37/44; UI-04/11 |
| REQ-24 | From 320 px upward, ordinary content and controls fit without page overflow; tables/code scroll locally; sidebar overlays below 1024 px and evidence is full-screen below 640 px. | FE-12, QA-12; AC-44; UI-01/04/06/10 |
| REQ-25 | Resize/orientation preserves session, draft, active job/revision and reading position without extra submissions. Older-message reading does not force-scroll; Jump to latest is available. | FE-04/08, CHAT-08; AC-16/43/45; UI-02/07/08 |
| REQ-26 | Enter/Shift+Enter, IME composition, touch, visible keyboard focus and modal focus return work. Composer and close controls stay reachable in short viewports. | FE-03/12; AC-44; UI-05/06/09 |
| REQ-27 | Verify widths and boundary sizes, real text/browser zoom, long-content fixtures and actual persisted UI state. Unavailable physical soft-keyboard tests are recorded, never inferred from emulation. | QA-12, FE-12; AC-44; UI-01–12 |
| REQ-28 | Process the entire four-book official OpenStax scope (Biology2e, Chemistry2e, Anatomy&Physiology2e, Concepts of Biology) with real local pinned E5 embeddings and actual pgvector retrieval. Only answer generation may mock; authored/raw/vector fixtures cannot satisfy formal corpus acceptance. Preserve every quarantine reason and original version. | DAT-01–12, RET-01–06; AC-03–06/26/28/35 |
| UPD-REQ-01 | Administrators save a versioned provider/base URL/model/key configuration, make a real connection test and explicitly enable the tested revision; keys remain write-only and encrypted, and running work keeps its frozen revision. | User-authorized 13 September extension; UPD-01/02; GEN-02, BE-06/08/12/13, FE-09 |
| UPD-REQ-02 | Administrators manage accounts and inspect successful/failed question stages with separate candidate, submitted and cited counts. Learner source controls list actual citations. | UPD-05/06; BE-03/09/12/13, FE-02/05/07/09 |

## Required connected journeys

| Journey | Entry, state and final observable result |
| --- | --- |
| J1 | Admin ingestion → quality decisions → stable chunks/vectors → validated release → active retrieval. A failed build leaves the previous release usable. |
| J2 | Login → new chat → question → saved prose/citations → context-dependent follow-up → coherent contextual input → history after re-login. |
| J3 | Distinct clarification/refusal/invalid/provider failure → Stop or finite Retry → tail-only Regenerate → consistent persisted message and active revision. |
| J4 | Profile edit → saved revision → frozen snapshot/compiler → one main generation call → historically accurate applied-profile display. |
| J5 | Offline gold-free OpenQA/MCQ command → shared answering components → evaluator-only scoring → all-outcome results and exports. |
| J6 | Deactivate/restore/reprocess/rollback → changed future retrieval → historical citations retain original authorized content or become explicitly unavailable. |

## Out of scope and evidence limits

No cross-session semantic or episodic memory, automatic mastery inference, learner file uploads, voice/multimodal inputs, open-web agents, full LMS, foundation-model training, multi-tenancy platform or distributed orchestration is required. These exclusions never remove conversation history within a session.

Authored sources and deterministic mock adapters establish software behaviour only. A real OpenStax corpus release needs actual provenance and source review. Scientific conclusions need actual frozen runs and annotations/ratings. UI screenshots alone do not prove a connected journey. Performance figures must distinguish chat versus evaluation, include the environment and retain unknown cost as null.
