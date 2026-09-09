# CS-30-1 product requirements

Effective authority: the user's 8 September 2026 priority correction, the full v5 taskbook/master prompt, the responsive UI refinement and compatible recorded source decisions. This document is the product entry point; [SPEC.md](SPEC.md) describes the actual implementation and [PLANS.md](PLANS.md) records execution. Detailed requirement IDs remain in [requirements.md](docs/foundation/requirements.md). The original 108 task IDs, 60 acceptance IDs and 12 responsive subchecks are retained.

## Goal and users

Deliver an English conversational learning assistant grounded in a bounded, real OpenStax corpus. A learner asks an ordinary question, receives a readable explanation with inspectable textbook passages, and follows up in the same conversation. The application preserves that conversation and the learner's explicitly saved preferences. It does not infer mastery or claim improved learning without research evidence.

Learners can sign in, manage their account and preferences, create/rename/archive/restore conversations, send questions, stop work, retry an eligible failed latest turn, regenerate the latest answer, inspect/copy sources and give feedback. Administrators additionally manage accounts, immutable source versions, processing, corpus releases, configurations, experiments and feedback review. An independent evaluator holds private labels and ratings; those are not learner inputs or runtime prerequisites.

## Required knowledge corpus

The source owner's `WEEK4_SUMMARY_AND_WEEK5_PLAN.md`, section1.1, explicitly freezes these four first-release books under `cs30_openstax_v0.2`:

| Book | Required scope | Current evidence at this reconciliation |
| --- | --- | --- |
| Biology 2e | Entire official book; record the actual PDF revision/hash | Full official PDF processed; all blockers resolved with retained source evidence; real E5/pgvector release active (see per-book report) |
| Chemistry 2e | Entire official book; record the actual PDF revision/hash | Full official PDF processed; 2,373 chunks/real vectors in the active release; seven source pages recovered |
| Anatomy & Physiology 2e | Entire official book; record the actual PDF revision/hash | Full official PDF processed; all blockers resolved with retained source evidence; real E5/pgvector release active (see per-book report) |
| Concepts of Biology | Entire official book; compare with the historical pilot identity | Exact historical pilot SHA256; pilot cover/blank inspected; 1,406 chunks/real vectors active; two appendix pages recovered |

Source: [original scope record](../development_inputs/sources/COMP5703/tut5/HongleYang/WEEK4_SUMMARY_AND_WEEK5_PLAN.md). That record excludes retired College Physics from the first release. Its historical download claims are not current file verification. Newly fetched bytes that differ from a historical hash receive a new identity and do not retroactively approve the old pilot pages.

**Only the answering language model may remain simulated.** Official source acquisition, parsing, cleaning, chunking, learned local embeddings, PostgreSQL/pgvector storage and actual vector retrieval must execute on the real books. Authored notes and hashed lexical mock vectors remain labelled software fixtures and cannot satisfy formal corpus acceptance. Real knowledge processing does not wait for answer-provider credentials.

Current acquisition evidence is in [the four-book download record](evidence/openstax/acquisition-run.json), with immutable source paths, official URLs, timestamps, sizes and hashes. [Current processing observations](evidence/openstax/v5/processing-status.json) retain the actual database jobs and counts. The pinned E5 checkpoint has generated all 10,594 real vectors. The [per-book report](docs/execution/openstax-corpus-report.md) records current source counts, original PDF locations, actual questions and the activated release; [publication evidence](evidence/openstax/v5/publication.json) proves historical records stayed unchanged.

## Product flows and observable acceptance

| Flow | Required observable result | Original checks |
| --- | --- | --- |
| J1 Corpus publication | Official original bytes → attributable pages/units → quality decisions → chunks → real learned vectors → integrity-checked release → actual retrieval; a failed build leaves the previous release usable | AC-03–06,26,28,35 |
| J2 Contextual chat | Login → new session → free-text question → saved answer/citations → dependent follow-up → actual bounded history in model input → same history after re-login | AC-08,36–38,40–43 |
| J3 Failure and revision | Social/clarification/refusal/provider error remain distinct; Stop fences late output; finite retry keeps counters; failed regeneration preserves the previous answer and feedback | AC-09–13,24–25,39,45 |
| J4 Preferences | Save a versioned profile; the next request freezes and uses its compiled policy in one answer call; profile-off retains history; temporary simpler wording does not change the saved level | AC-15,29–30 |
| J5 Independent evaluation | Frozen stem-only OpenQA or gold-free MCQ → shared answer service → separate private scoring → all scheduled outcomes and mode-specific exports | AC-07,17–19,22–23,46–47 |
| J6 Source lifecycle | Deactivation/restoration/reprocessing/rollback affect new retrieval; historical citations keep their exact original snapshot or return explicit unavailability | AC-14,26–28,33–35 |

The composer accepts only `content` and `use_profile`. Learners never supply choices, gold labels, owner IDs, arbitrary history or hidden evaluation fields. Supported profile levels are beginner/intermediate/advanced; styles are concise/detailed/socratic; the first language is English. Administrators can use the documented, tested CLI for infrequent operations.

PER-03 requires short answers, long explanations and requested simplification across all three levels. Verify frozen preferences, the submitted policy, cited evidence and call counts separately from the model's actual wording and response length. A request for a long explanation does not prove that the returned response is long or instructionally appropriate. PER-07's automatic checks cover structure, versions and allowed evidence; scientific meaning requires separate review.

## Interface and nonfunctional requirements

The learner lands at `/chat`. Use a restrained light interface with one readable conversation column, a desktop sidebar, overlay navigation at narrower widths and a fullscreen source view on small screens. Full answers and source titles remain readable. Technical IDs/hashes stay in expandable details. The application displays `Demo (mock model)` while its answering model is simulated, independently of whether the underlying corpus and embeddings are real.

Support continuous layout from 320 CSS px upward, the named widths and breakpoint edges, long prose/URLs/code/tables/formulas, real browser zoom through 200% and equivalent 320px reflow. Resizing preserves draft, session, job, revision and reading position without another answer submission. Keyboard, IME, touch and modal focus rules remain required; unavailable physical-device tests must remain unverified. Exact subchecks are in [responsive_spec.md](docs/foundation/responsive_spec.md) and [ui_acceptance.json](docs/execution/ui_acceptance.json).

Use one modular application, one durable worker and PostgreSQL16/pgvector. Enforce ownership, credential revocation, bounded uploads and input text, immutable source/evidence snapshots, atomic answer publication, strict response validation and finite cumulative call/time budgets. Recovery retains uncertain external-call state and never silently repeats successful experiment items. Backups restore to a different database/storage target and verify source and saved-evidence identity.

## Scope and evidence boundaries

Included: complete accounts/chat/context/preferences/citations/feedback/recovery/corpus/evaluation/operations work represented by all 108 original tasks. Excluded unless later requested: learner uploads, cross-session semantic memory, automatic mastery inference, voice/multimodal chat, web agents, an LMS, foundation-model training or distributed infrastructure.

Current tests exercise real API, worker, PostgreSQL and browser flows with explicitly mock answering. Authored fixture checks and [actual v5 official-source browser checks](artifacts/reports/frontend/openstax-v5/2026-09-08T08-54-45-868Z/verification.json) have distinct recorded scopes. The four-book OpenStax/E5/pgvector release, 15 actual retrieval queries and current connected chat have passed the linked source, publication and provenance checks. These observations do not establish live answer correctness, formal SciQ scores, independent ratings or physical mobile keyboard behavior. Current per-task evidence and status are maintained in the ledgers, without an aggregate completion percentage.

## Delivery and immediate order

1. Completed first pass: reconcile this PRD, the runtime SPEC, original diagram mapping and all task/check ledgers.
2. Completed with explicit visual/semantic limits: download the four official books and a fixed local embedding checkpoint; process, validate, publish and demonstrate actual retrieval, retaining every failure/quarantine decision.
3. Current publication evidence: update per-book acquisition/quality/chunk/vector/retrieval reports and the same ledgers.
4. Continue the remaining original implementation, current regression, static/CI checks, operations and English handover. Live answering-model quality and human review remain separately pending until actually performed.

The [local audit continuation](docs/execution/local-audit-continuation.md) closes the missing owner/week delivery export and additional keyboard, error-display and adapter-switch software checks. [Delivery views](docs/delivery/README.md) derive from the same ledgers. The profile matrix records three actual long-request refusals; requested wording and output quality remain distinct. These observations retain the original requirements and external review conditions.

The [final document review](docs/execution/final-document-review.md) clarifies that retrieval-study configuration and paired schedules are prepared, while compatible judged qrels remain missing. Historical migration/setup notes now link the actual completed local evidence.
