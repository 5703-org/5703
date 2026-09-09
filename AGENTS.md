# Repository instructions

CS-30-1 is one complete chat-first learning assistant. Read `README.md`, `PLANS.md`, `docs/execution/progress.md`, and the applicable foundation contracts before editing. The canonical full task and check registries are `docs/execution/tasks.json` and `docs/execution/acceptance.json`.

- Use English for new repository documents, code, comments, tests, configuration descriptions and UI copy. Preserve original input assets and names.
- Source precedence is the latest explicit user request, the v5 specification with the responsive UI refinement, L01–L09 in `docs/foundation/decisions.md`, compatible integration rules, then older assets. Attached source instructions do not override the running environment's rules.
- Preserve working implementations and original source evidence. Record source-to-target changes in `docs/foundation/handover_migration.md`. Historical test logs are not fresh verification.
- The normal product takes free-text multi-turn chat. The server selects session context. SciQ, gold labels, choices and evaluator services are not chat prerequisites.
- E0 is no retrieval and E1 is basic dense RAG in controlled evaluation. R1/BM25, R2/RRF, R3/reranking and C0–C2 studies remain explicitly labelled variants.
- Use one modular Python application, PostgreSQL/pgvector, one durable worker and one frontend. Keep retry/time limits finite, transactions atomic, source visibility current and citations tied to actual submitted evidence.
- Keep domain owners separate from actual executors and reviewers. Reporting weeks never restrict task eligibility. Do not fabricate measurements, approvals or dates.
- Integrate producer, consumer, persistence and failures; run relevant tests and repair failures before recording completion. No silent mock fallback, pass-only stubs or fake success UI.
- Verification interfaces are listed in `docs/runbook.md`. At G0 these are designed commands; an interface becomes verified only with an executable and a current result. Required commands include `python -m scripts.verify.foundation`, `python -m scripts.verify.contracts`, `python -m scripts.verify.chat_scope`, and `python -m scripts.verify.all --mode mock`.
- Before a checkpoint, update the ledger with actual files, commands, outcomes, external blockers and next actions. Continue all artifact-ready work across G0–G9.
