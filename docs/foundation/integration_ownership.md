# Integration and accountable ownership

The names below are original accountable domain owners. They are not claimed to have authored new Codex changes or reviewed this delivery. Historical receiver identities were not supplied and are not reconstructed.

| Accountable owner | Domain and task IDs | Producer boundary | Main consumers |
| --- | --- | --- | --- |
| Xianshu Zhang | Integration: INT-01–10; CHAT-01/11/12 | Canonical scope, contracts, task/check ledger and release evidence | Every workstream |
| Hongle Yang | Corpus: DAT-01–12 | Assets, source units, processing runs, chunks and manifests | Retrieval, backend corpus administration, evidence UI |
| Chengzhou Liu | Retrieval: RET-01–11; CHAT-04 | Embedding/retriever ports, prepared queries, selected evidence and traces | Shared answer service, evaluation |
| Sijin Lu | Generation: GEN-01–11; CHAT-05 | LLM transport, prompts, strict response validation and GenerationService | Worker answer service, evaluation runner |
| Pengyuan Xia | Personalisation: PER-01–09; CHAT-07 | Profile schema, compiler policy/hash and study rubric | Identity/profile persistence, main generation, independent study |
| Zeping Liao | Backend: BE-01–17; CHAT-02/03/08 | API, persistence, migration chain, jobs/attempts and atomic publication | Browser client, corpus tools and evaluation |
| Baiqing Huang | Frontend: FE-01–12; CHAT-06 | Typed client and real UI controls | Learners and administrators |
| Chong Zhang | QA: QA-01–14; CHAT-09/10 | Evaluator-only labels, metrics, frozen runs, annotations and acceptance | Research outputs and release audit |

## Actual execution lanes

Actual executor for new work is Codex. Root integrator owns shared contracts/OpenAPI, database architecture/migrations, integration and merges. Parallel lanes are bounded to avoid conflicting writers:

- Foundation lane: `AGENTS.md`, `README.md`, `PLANS.md`, `docs/execution/`, specified scope/source/decisions/ownership/test foundation files and initial runbook.
- Frontend lane: frontend implementation plus `ui_flows.md`, `ui_design.md` and `responsive_spec.md`; it consumes canonical contracts.
- Generation audit/implementation lane: historical source verification, generation adaptation and assigned AI/evaluation contracts.
- Root backend/integration lane: architecture, data model, canonical schemas, API contracts, backend/database/worker and cross-module integration.

These are current machine execution responsibilities, not assignment of the two historical receiving integrators. The root integrator must reconcile changed shared boundaries before a lane claims connected acceptance. No domain task waits for the original named person to approve routine implementation.

## Contract ownership rules

The root integrator approves design changes by updating the canonical schema, OpenAPI, affected Python/TypeScript consumers, fixtures and tests in one coordinated increment. The generation adapter owns transport, not DB transactions. Backend owns attempt counters, execution tokens and publication. Retrieval owns actual selected text/ranking metadata; source processing owns provenance. The profile compiler owns deterministic presentation rules; generation consumes them. Evaluator modules alone access gold/support and scoring references.

Task acceptance is linked as entry → producer service → persisted record/state → consuming view/runner → executable check. Source hashes and old evidence remain in the migration inventory. All human review remains `PENDING` until an actual review record exists. Cross-referencing a shared artifact in owner exports does not count it as multiple completed tasks.

## Week 8 domain preservation

The [member map](../delivery/week08/README.md) retains original accountable domains and all existing file owners. Chengzhou owns conversation/retrieval interfaces; Hongle retains source/knowledge service; Zeping retains answering/configuration and safe backend diagnostics; Sijin owns generation packing/audit/teaching implementation; Baiqing owns administrator UI; Chong owns tests/evaluation; Xianshu owns shared integration/delivery. Pengyuan's retained compiler/profile module supplies the presentation policy consumed by the new shared teaching plan. A cross-domain contribution does not invent a second file owner or member-authored commit. New path ownership is finalized once in the package inventory.

All eight tracks include implemented Week 8 changes and separately identified research judgments. Independent learning/claim/relevance/device checks remain follow-up work; current live/software runs receive their actual dates/results. [Integrated scope](../execution/week08-delivery-20260916.md).
