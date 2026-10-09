# Week 9 answer core and source-pinned practice proposals

This checkpoint implements the 30 September learning-workspace brief. It preserves the real corpus, stored vectors, CPU retrieval implementation, ordinary full-answer default, E0/E1 definitions and previous experiment outputs. The current checks below use authored provider responses in isolated tests. Real-provider behavior and independent quality results require the separately frozen development and evaluation runs.

## Request and evidence processing

New chat commands freeze `evidence_reliability_v5` and `generation_controls_v2`. Structured requirements preserve the original question, comparison relation, negation, quantities, units and condition spans. A rewrite that loses a protected element falls back to the original question. These checks are deterministic and do not establish general semantic equivalence.

`candidate_coverage`, `semantic_sufficiency` and `claim_support` are separate versioned diagnostics. Candidate and packed-context coverage use lexical signals and named requirements; the semantic value stays null until a structurally valid requirement judgment is returned by the online checker. The checker assesses relevance, sufficiency, conditions, response coverage and missing information for each requirement against exact submitted fragment IDs and quotes. Claim support remains tied to the actual immutable draft and citation bindings. The checker is part of the online generation pipeline; its decisions are not independent evaluation labels.

One bounded local supplementary lookup may address a named missing requirement. It admits at most ten new candidates through the existing source and scope checks. This pre-generation decision uses candidate-coverage signals, not a separate semantic planner call. The usual live path remains one generation call plus one joint checker call. Format and semantic repair share the existing limit of four provider calls and 180 active seconds.

The final checks reject omitted supported requirements, lost conditions, invalid source quotes, unsupported factual claims and unnecessary partial answers when context is judged sufficient. A qualified partial answer may publish when the checker identifies specific missing information and verifies the stated limitation. The answer carries `answer_completeness` separately from its terminal response state. Model judgments may still be wrong; no software pass is presented as a measured correctness result.

Stable V5 claim IDs depend on factual text and answer field, allowing an unchanged fact to retain identity across a neighboring insertion or citation correction. Repair preserves accepted factual content while allowing a rejected procedural next question to change. Every repaired final body, citation binding, source display and disclosure projection is checked again.

## Reading scope and adaptive teaching

`ChatMessageCreate.reading_context` accepts chapter, textbook or all accessible workspace sources, with optional exact Unicode code-point selection. The server freezes release, processing run, source unit, selection hashes and explicit authorized chunk IDs. Scope is applied before SQL vector ranking, BM25 admission, fallback and inherited-evidence admission. Selected passages enter the same answer engine. Source identity and access are checked again during execution and publication. Omitted and null reading context retain the previous idempotency identity.

A selected passage resolves a missing referent such as “this paragraph”; it does not override an unresolved domain ambiguity. Public historical answers retain the selection and source identity without exposing the private chunk allowlist.

The teaching plan uses the original problem, current step, current learner attempt, help depth and recent actually published feedback. Repeated difficulty reduces the next step; partial work focuses on missing reasoning; a correct attempt can move to explanation or transfer. The checker assesses whether the next action merely repeats information already disclosed. V5 adds an `unrelated` learner-attempt outcome without advancing progress. Recent feedback is an observation of recorded attempts, with no inferred mastery score.

## Administrator practice generation

`POST /api/v1/admin/learning/practice-proposals` accepts `PracticeProposalInput` and a required `Idempotency-Key`. It returns the existing `PracticeAdminOut`: HTTP 201 for a new draft and 200 for a successful replay. The source, item kind, concepts and conditions are frozen. The existing active answer configuration, provider adapter and local complete-request token counter are used. Mock mode rejects this operation explicitly.

One provider call is allowed, bounded by the configured timeout of at most 60 seconds and configured output/window limits. There is no automatic retry, fallback model, checker call or publication. The exact selected source is supplied without silent truncation. Source validity and administrator status are checked after the call. The generated draft must preserve the requested source and requirements and cannot select a previous item revision.

A durable administrator-owned `LearningRecord` of kind `practice_proposal` is committed before submission. It records source/configuration/prompt/schema/output hashes, token-counter metadata, provider submission status, safe diagnostics, latency and reported usage. Unknown usage and monetary cost remain null. A repeated key cannot submit another call, including concurrent requests and previously failed attempts. A process interruption can leave an explicit started/unknown record; a new attempt is an administrator action with a new key.

Generated keys and worked solutions remain in the private rubric. The item stays in draft with pending validation and null semantic correctness. The administrator reviews the draft, runs structural/source validation, then explicitly confirms source support and solvability before publishing. Learner item responses omit the rubric. The immutable generation request ID links the draft to its durable usage/failure record even after validation updates.

## Compatibility and focused evidence

Historical V4 execution dispatches to `generation/checked_v4.py`, an exact preserved predecessor with SHA-256 `9a9c6060ee66e758c30afa45529e7482c1e7e3d48ebe87d9d0834aff043d099f`. Historical provider probe V3 dispatches to `generation/probes_v3.py`, SHA-256 `8b677d61de32c29cafdc401f9c90e6eb538f7731d8310aaeba34d374bcebae8c`. Current provider probe V4 uses the actual V5 generation and checking schemas. V2/V3 paths, prior study outputs and the standard E0/E1 retrieval definitions retain their dispatch behavior.

Evidence is under `evidence/week09-learning/20260930/answer-core/`:

| Receipt | Result and scope |
| --- | --- |
| `unit-final-02.xml` | 105 passing focused unit checks for requirements, sufficiency separation, local repair, teaching adaptation, historical V4, token transport, provider compatibility and diagnostics. |
| `integration-final-02.xml` | 27 passing migrated-PostgreSQL checks for exact reading scope, retrieval admission, selected passage, source changes, inherited citations, idempotency, model/secret freezing and historical commands. |
| `proposal-integration-final.xml` | 9 passing migrated-PostgreSQL proposal checks, including concurrent same-key admission, durable failure usage, source revocation, private keys and explicit publication. |
| `typecheck-final-02.log`, `proposal-typecheck.log` | Mypy passed the changed typed core and proposal module. |

Earlier failures remain in the same evidence directory. They include a stale disposable-database connection, an unfinished authored fixture job, a missing new login-limit table in a selected-table test fixture, and proposal JSON audit dirty tracking. The fixes were rerun against fresh disposable PostgreSQL containers. Existing project and portable databases were untouched.

## Remaining verification

Earlier pilot requests retain their frozen 16,384-token window and original context-limit failures. The main installation now has a separately saved 32,768-token configuration with passing answer/checker compatibility probes; [the promotion receipt](../../evidence/week09-continuation/20260930/main-model-32k-promotion.json) records the active revision and preserved corpus/history. New candidate behavior requires its own real development observations. The V5 teaching preparation failures made zero model calls. The [V7 pilot](../../evidence/week09-continuation/20260930/pilot-v7-sanitized.json) now retains 21 terminal observations, including all eight delivered hints and one four-call QA checker-contract failure. The [formal V8 automatic study](../../evidence/week09-continuation/20260930/formal-v8-automatic-sanitized.json) is now terminal: QA delivered 32 answers and two clarifications with 14 failures; teaching delivered 179 hints with 13 failures. Same-family offline AI assessment rated 211 outputs and retained 29 no-output judgments, with saturated correctness and zero human ratings. The [V9 candidate software gate](../../evidence/week09-continuation/20260930/software-gate-v9-release-1/software_gate.json) passed 1,293 Python and 132 frontend tests with 657 unchanged source files. Ordinary requests retain `single_contract_correction_v1`; the explicit `schema_contract_corrections_v2` candidate remains opt-in after the [paired development probe](../../evidence/week09-continuation/20260930/v9-checker-development/results.json) accepted three of four fixed drafts under each policy. The successor used six checker calls versus five and had a higher delivered-run median latency; the ordinary default remains legacy. The [final V9 same-host CPU installation](../../evidence/week09-continuation/20260930/staging-installation-v9-summary.json) passed runtime, source, vector and mock-answer checks; archive byte parity remains separate. Real-provider draft quality, requirement judgments, teaching adaptation, proposal source support and latency remain development/evaluation work. The current proposal tests establish lifecycle, isolation and accounting behavior, using clearly authored provider output. Independent automated evaluation and human review must report their own results separately from the online checker and these software checks.
