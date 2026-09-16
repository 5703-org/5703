# Owner and course-week reporting view

Imported allocation is a reporting view only. No row is an actual completion, authorization gate or date deadline. Week 3 is project week 1; no project work is fabricated for weeks 1–2. Week 13 is optional real follow-up only.

Canonical plan: `reporting_plan.json`; actual task state: `tasks.json`. The same implementation will be exported to `docs/delivery/by_owner/` and `docs/delivery/by_week/` during INT-10/CHAT-12/QA-14. Actual executor, completion timestamp, commands and evidence remain separate from suggested weeks.

## Course week 6 / project week 4 — Xianshu Zhang

Tasks: INT-01, INT-02, CHAT-01, INT-03, INT-04, INT-05.

Audit archives/git state; publish chat scope and migration mapping, reconcile foundations and coordinate the first thin slice.

Deliverables: docs/foundation/, AGENTS.md, PLANS.md, docs/execution/.

Acceptance: Contracts, IDs and dependency checks pass; every existing-work claim has a source; continue coding after FOUNDATION_READY.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 6 / project week 4 — Hongle Yang

Tasks: DAT-01, DAT-03, DAT-02, DAT-04, DAT-05, DAT-06, DAT-07, DAT-08.

Reuse parsing, inspect available originals/quarantine, produce stable chunks/spans and a first release from ready sources.

Deliverables: pipelines/, configs/corpus/, artifacts/manifests/.

Acceptance: Chunks trace to source; missing originals are not approved; ready-source releases need not wait for every book.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 6 / project week 4 — Chengzhou Liu

Tasks: RET-01, RET-02, RET-03, RET-04, RET-05.

Receive stable chunks and implement E5/pgvector/R0, actual-context evidence and budget interfaces.

Deliverables: retrieval/, contracts/fixtures/evidence/.

Acceptance: Numeric fixtures rank correctly; normal/empty retrieval is callable; citation IDs match text hashes.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 6 / project week 4 — Sijin Lu

Tasks: GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-08.

Reproduce in a copy, port complete assets, and fix bias/oracle/strict parsing/truncation/empty output while establishing shared chat types.

Deliverables: generation/, contracts/schemas/, tests/contract/.

Acceptance: Relevant HC-01–07 checks run; chat input needs no options; historical failure records remain.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 6 / project week 4 — Pengyuan Xia

Tasks: PER-01, PER-02, PER-03, PER-04.

Locate/verify compiler source; freeze profile mapping/defaults and provide deterministic English policies for all three levels.

Deliverables: personalisation/, contracts/fixtures/profiles/.

Acceptance: Repeated compilation is hash-stable; invalid explicit values fail; defaults and temporary presentation requests are defined.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 6 / project week 4 — Zeping Liao

Tasks: BE-01, BE-02, BE-03, BE-07, BE-09, BE-04, BE-05, BE-06, CHAT-02.

Reverify backend foundations; migrate messages/snapshots/answers/evidence/jobs incrementally and prepare the real POST messages orchestration.

Deliverables: backend/app/, backend/alembic/, contracts/openapi.yaml.

Acceptance: Fresh and legacy-fixture upgrades pass; one request persists messages and citations with an explicitly mock model if needed.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 6 / project week 4 — Baiqing Huang

Tasks: FE-01, FE-02, FE-03, FE-04, FE-05.

Retain useful wireframe semantics, build login and /chat, and connect typed message APIs for full responses and errors.

Deliverables: frontend/src/features/auth/, frontend/src/features/chat/.

Acceptance: No mandatory A–D fields; send has a real database effect; unfinished features cannot claim success.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 6 / project week 4 — Chong Zhang

Tasks: QA-01, QA-03, QA-05, CHAT-10.

Create 12 conversation families and register 60 scenarios; prioritise generation-migration negatives and thin-slice checks independent of SciQ files.

Deliverables: tests/fixtures/, tests/contract/, docs/execution/acceptance.json.

Acceptance: Expected versus executed checks are separate; the legacy 39-test scope is explicit, not full-project acceptance.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 7 / project week 5 — Xianshu Zhang

Tasks: CHAT-01, INT-06, INT-07.

Coordinate consumer-side seam tests and accept the chat product, not isolated modules; maintain the end-of-week defect list.

Deliverables: docs/execution/week_07.md, docs/traceability.md.

Acceptance: J1/J2/J3/J4/J6 and no-SciQ chat pass; blockers have explicit owners.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 7 / project week 5 — Hongle Yang

Tasks: DAT-09, DAT-08, DAT-10.

Connect deactivation/restoration/reprocessing; separately prepare SciQ evaluation files without indexing support as textbook evidence.

Deliverables: pipelines/lifecycle.py, evaluation/datasets/.

Acceptance: New queries exclude deactivated sources; history is unchanged or explicitly unavailable; chat has no gold mounts.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 7 / project week 5 — Chengzhou Liu

Tasks: CHAT-04, RET-04, RET-06, RET-05.

Implement standalone follow-up queries, topic changes, clarification and underlying evidence reuse; record raw and prepared queries.

Deliverables: conversation/query.py, retrieval/context.py.

Acceptance: The light follow-up uses its real referent; topic changes drop irrelevant evidence; empty retrieval differs from an outage.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 7 / project week 5 — Sijin Lu

Tasks: GEN-06, GEN-07, GEN-08, GEN-09, CHAT-05.

Extract runtime generation service; connect messages/history/profile/evidence and one bounded retry policy; inspect actual model payloads.

Deliverables: generation/service.py, generation/tracing.py.

Acceptance: Executable HC-08–11 checks pass; profiles enter one main call, with no silent fallback or lost history.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 7 / project week 5 — Pengyuan Xia

Tasks: PER-03, PER-04, PER-05, CHAT-07.

Connect save/reset/snapshot/temporary simplification and verify that disabling profiles retains conversational context.

Deliverables: personalisation/service.py, tests/e2e/profile/.

Acceptance: All three policies enter actual requests; historical profile snapshots remain; temporary requests do not rewrite saved level.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 7 / project week 5 — Zeping Liao

Tasks: CHAT-03, BE-08, BE-10, BE-12, BE-13, BE-14, CHAT-08.

Complete shared orchestration, recent context/extractive summaries, transactional publication, retry and latest-answer revisions; sync client contracts.

Deliverables: backend/app/modules/answering/, conversation/, contracts/.

Acceptance: Duplicate send deduplicates; refresh restores; failed regeneration preserves old answer; summaries exclude future/other-session text.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 7 / project week 5 — Baiqing Huang

Tasks: FE-07, FE-04, FE-10, FE-05, FE-06, FE-08, FE-09, CHAT-06.

Connect the chat workspace, evidence drawer, profiles, feedback, stop/retry/regenerate, history and corpus status.

Deliverables: frontend/src/features/, tests/e2e/.

Acceptance: Natural multi-turn flow works; Enter/Shift+Enter, failed drafts and re-login behave correctly; controls have real effects.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 7 / project week 5 — Chong Zhang

Tasks: QA-02, QA-03, QA-05, CHAT-10.

Run 12 conversation families and recovery negatives; finish independent evaluation adapters and metric math tests; label live semantic checks separately.

Deliverables: evaluation/conversations/, tests/e2e/, evaluation/metrics/.

Acceptance: No-SciQ operation, reference/clarification/topic/summary/profile/revision checks inspect actual records.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 8 / project week 6 — Xianshu Zhang

Tasks: INT-07, INT-08.

Freeze protocols, manifests, configurations and reporting; continue fixing chat defects without replacing product acceptance with scores.

Deliverables: docs/baseline_freeze.md, docs/execution/week_08.md.

Acceptance: OpenQA/MCQ directories and denominators are separate; unrun studies remain blocked, not passed.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 8 / project week 6 — Hongle Yang

Tasks: DAT-09, DAT-08.

Verify available SciQ revision/splits/hashes and corpus manifests; provide source locators for annotation.

Deliverables: evaluation/datasets/, artifacts/manifests/.

Acceptance: System-visible exports contain only protocol fields; support is absent from the textbook index.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 8 / project week 6 — Chengzhou Liu

Tasks: RET-04, RET-05, RET-07.

Stabilise R0 traces and review source coverage; implement R1 in parallel without changing frozen E1.

Deliverables: retrieval/tracing.py, retrieval/bm25.py.

Acceptance: The same release reproduces candidate order; a retrieval miss alone does not prove absent source coverage.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 8 / project week 6 — Sijin Lu

Tasks: GEN-08, GEN-10, GEN-11.

Connect OpenQA/MCQ contracts and actual provider metadata to the formal runner; run a separate live smoke when configured and authorised.

Deliverables: generation/benchmark_context.py, configs/models/.

Acceptance: Inputs/settings are comparable; examples do not select a verified model; preserve the historical probe.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 8 / project week 6 — Pengyuan Xia

Tasks: PER-08, PER-05.

Recheck product profiles; prepare rating templates and fixed-level cases without delaying already-required chat features.

Deliverables: personalisation/rubric/, docs/user_profiles.md.

Acceptance: Baseline inputs exclude profiles while normal chat retains them; rating templates contain no fabricated scores.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 8 / project week 6 — Zeping Liao

Tasks: BE-11, BE-12.

Implement experiment runs/items, freeze/cancel/resume/export through shared AnswerExecutionService without fake learner sessions.

Deliverables: backend/app/modules/experiments/, evaluation/runner/.

Acceptance: All scheduled items retain outcomes; stopping the evaluator does not affect chat_ready.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 8 / project week 6 — Baiqing Huang

Tasks: FE-11, FE-08.

Build secondary admin evaluation/results views showing protocol, mock/live and failure counts; continue chat UX fixes.

Deliverables: frontend/src/features/admin/experiments/.

Acceptance: Learner landing remains /chat; exports use actual server records, not invented frontend metrics.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 8 / project week 6 — Chong Zhang

Tasks: QA-04, QA-06, CHAT-09, QA-07, QA-08.

Freeze coverage review and run manifests; execute E0/E1 or record blockers, separately calculating EM/F1, MCQ and semantic review.

Deliverables: evaluation/runner/, evaluation/analysis/, artifacts/runs/.

Acceptance: Failures/refusals remain in N; aliases/references never enter generation; HC-12 and denominator fixtures pass.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 9 / project week 7 — Xianshu Zhang

Tasks: INT-07, INT-08.

Review variant controls and code diffs; integrate improvements without requiring unsupported positive gains.

Deliverables: docs/research/variant_registry.md.

Acceptance: Every comparison identifies changed/fixed factors; the prior baseline is not overwritten.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 9 / project week 7 — Hongle Yang

Tasks: DAT-07, DAT-11.

Build fixed-window/structure-aware releases with span mappings and re-annotate qrels where necessary.

Deliverables: configs/variants/chunking/, evaluation/annotations/.

Acceptance: Incompatible chunk IDs are not reused; old answer text/hashes remain unchanged.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 9 / project week 7 — Chengzhou Liu

Tasks: RET-07, RET-08, RET-09, RET-10.

Deliver BM25, RRF, re-ranking and chunk/embedding/k ablations; distinguish executable code from blocked measurements when models are unavailable.

Deliverables: retrieval/, configs/variants/, artifacts/runs/ablations/.

Acceptance: RRF matches hand calculations; changed embedding dimensions get compatible indexes; no hidden R3 fallback.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 9 / project week 7 — Sijin Lu

Tasks: GEN-07, GEN-10.

Implement matched-policy controls and versioned prompts, recording timing/usage/errors without attributing multi-factor changes solely to retrieval.

Deliverables: configs/variants/matched_policy/, docs/research/generation_controls.md.

Acceptance: Protocols remain distinct, reuse the shared engine and do not alter chat entry; a second live model remains optional.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 9 / project week 7 — Pengyuan Xia

Tasks: PER-08, PER-06.

Prepare C0/C1/C2 inputs, frozen base responses/evidence and blinded rubrics for the next week.

Deliverables: configs/profiles/study.yaml, personalisation/rubric/.

Acceptance: Study and product configurations are separate; gold never replaces the base response.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 9 / project week 7 — Zeping Liao

Tasks: BE-11, BE-14, BE-15.

Connect variant versions/run traces and embedding storage boundaries; verify backend/client schema synchronisation.

Deliverables: backend/app/modules/experiments/, contracts/.

Acceptance: Switching retrievers does not rewrite login/history/evidence; legacy migration fixtures pass.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 9 / project week 7 — Baiqing Huang

Tasks: FE-10, FE-11, FE-06.

Complete comparison/configuration/failure-trace views and historical citation rendering after corpus changes.

Deliverables: frontend/src/features/admin/experiments/, frontend/src/features/evidence/.

Acceptance: Display actual denominators and missing metrics; old citations never silently target new content.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 9 / project week 7 — Chong Zhang

Tasks: QA-04, QA-08, QA-09.

Check single-factor comparisons, compatible qrels and paired samples; produce at least one real controlled finding when inputs permit.

Deliverables: evaluation/analysis/ablation.py, artifacts/reports/.

Acceptance: Retain negative findings, keep missing labels null and identify exactly which comparisons were not executed.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 10 / project week 8 — Xianshu Zhang

Tasks: INT-09, INT-07.

Confirm study samples and real review arrangements; control remaining scope without adding large features.

Deliverables: docs/execution/week_10.md, docs/research/.

Acceptance: Research and engineering gaps are separate; naming reviewers is not evidence of performed ratings.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 10 / project week 8 — Hongle Yang

Tasks: DAT-11, DAT-12.

Freeze study source spans/releases, complete data dictionary/rebuild notes and address remaining source anomalies.

Deliverables: docs/data/, artifacts/reports/data_quality.json.

Acceptance: Study evidence is locatable; missing originals/use constraints are explicit, without expanding knowledge-source scope.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 10 / project week 8 — Chengzhou Liu

Tasks: RET-10, RET-11.

Finish retrieval ablations, analyse misses/context exclusions and freeze evidence for profile studies.

Deliverables: docs/research/retrieval_findings.md.

Acceptance: Matched profile items hold question/evidence fixed; comparison data remains traceable.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 10 / project week 8 — Sijin Lu

Tasks: GEN-09, GEN-10, GEN-11.

Implement separate TeachingStudyService/schema and generate C0/C1/C2 explanations; product chat still uses one main generation.

Deliverables: generation/teaching_study.py, contracts/schemas/teaching_study.json.

Acceptance: Study outputs do not append learner messages or mutate the base response; usage is per study item.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 10 / project week 8 — Pengyuan Xia

Tasks: PER-08, PER-06, PER-07.

Run the frozen level/condition matrix, check supported-meaning preservation and prepare randomised blinded review with anchored criteria.

Deliverables: evaluation/runner/personalisation.py, personalisation/invariants.py.

Acceptance: Report actual output count rather than assuming 270; missing ratings are null; structural checks are not semantic proof.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 10 / project week 8 — Zeping Liao

Tasks: BE-11, BE-15.

Persist separate study items/outputs/rating references; complete result reads and feedback review, checking transactions.

Deliverables: backend/app/modules/experiments/, backend/app/modules/learning/feedback/.

Acceptance: User chat and study identities are separate; feedback has an operator handling path.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 10 / project week 8 — Baiqing Huang

Tasks: FE-07, FE-11, FE-09, FE-12.

Polish applied-profile visibility, feedback review and result exports; test keyboard and narrow-screen behaviour.

Deliverables: frontend/src/features/, docs/frontend.md.

Acceptance: Current profiles differ clearly from historical snapshots; status does not depend on colour alone.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 10 / project week 8 — Chong Zhang

Tasks: QA-11, QA-10.

Collect actual independent ratings/disagreements, reconcile samples/pairs/missingness and start full negative/fault regression.

Deliverables: evaluation/analysis/personalisation.py, tests/integration/faults/.

Acceptance: Without actual ratings, claim no learning effect; cluster repeated outputs by question and retain failures.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 11 / project week 9 — Xianshu Zhang

Tasks: INT-09, INT-07, CHAT-11.

Audit requirement-to-code mapping, obsolete MCQ-mainline assumptions and blockers; prepare a release candidate.

Deliverables: docs/release_candidate.md, scripts/verify/chat_scope.py.

Acceptance: No missing IDs, cycles or mandatory-choice remnants; critical defects are fixed or explicitly blocking.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 11 / project week 9 — Hongle Yang

Tasks: DAT-10, DAT-12.

Check asset/chunk/vector counts and historical hashes in a separate restore environment; complete quality limitations.

Deliverables: docs/data/, artifacts/reports/restore/.

Acceptance: Restore preserves provenance; cleanup does not delete referenced evidence.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 11 / project week 9 — Chengzhou Liu

Tasks: RET-06, RET-11.

Execute R0/R1 and embedding replacement drills and diagnose measured bottlenecks; avoid speculative optimisation.

Deliverables: tests/integration/test_retrieval_replacement.py.

Acceptance: Shared consumers remain unchanged; dimension changes use explicit migrations/new indexes, never mixed writes.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 11 / project week 9 — Sijin Lu

Tasks: GEN-06, GEN-11.

Regress empty/truncated responses, HTTP errors, duplicate JSON keys, budgets and live configuration; reconcile actual generation evidence.

Deliverables: tests/contract/, docs/generation.md.

Acceptance: Legacy 39 tests and new HC results remain separate; aggregate retry counts agree and mocks cannot masquerade as live.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 11 / project week 9 — Pengyuan Xia

Tasks: PER-07, PER-09.

Complete available ratings and review misleading analogies, negation and formulas; write findings and limitations.

Deliverables: docs/research/personalisation.md.

Acceptance: Examples trace to run/profile/rater; unrated items do not receive default high scores.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 11 / project week 9 — Zeping Liao

Tasks: BE-15, BE-16.

Complete clean install, legacy upgrade, single-worker restart, transaction faults, backup/restore and rollback.

Deliverables: scripts/release/, compose.yaml, docs/runbook.md.

Acceptance: Commands rerun; failures do not publish partial success; restore targets are isolated from user databases.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 11 / project week 9 — Baiqing Huang

Tasks: FE-06, FE-08, FE-12.

Run full browser regression for stop/retry/latest-answer revision/account switch/re-login/history evidence.

Deliverables: tests/e2e/, artifacts/reports/frontend/.

Acceptance: UI values match DB snapshots; no dead controls, fake streaming or hardcoded success.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 11 / project week 9 — Chong Zhang

Tasks: QA-13, QA-11, QA-10, QA-12.

Execute all 48 AC plus 12 HC scenarios, replacement/restore/performance checks; record real environment, commands, exit codes, failures and skips.

Deliverables: artifacts/reports/acceptance/, docs/execution/acceptance.json.

Acceptance: Unexecuted checks are not passes; mocks prove wiring only, with live semantic evidence separate.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 12 / project week 10 — Xianshu Zhang

Tasks: CHAT-12, INT-10.

Integrate final English ledgers, guides, architecture, actual contributions and demo; coordinate real human review without signing for others.

Deliverables: README.md, docs/handover.md, artifacts/release/.

Acceptance: All 108 tasks/60 scenarios have evidence or exact blockers; demonstrate chat before SciQ.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 12 / project week 10 — Hongle Yang

Tasks: DAT-12.

Deliver data dictionary, source manifests, quality report and rebuilding instructions.

Deliverables: docs/data/, artifacts/manifests/.

Acceptance: A permitted example rebuilds; incomplete books/quarantine remain explicit.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 12 / project week 10 — Chengzhou Liu

Tasks: RET-11.

Deliver retrieval configurations/comparisons, index rebuild/replacement instructions and actual findings.

Deliverables: docs/research/retrieval_findings.md, docs/retrieval.md.

Acceptance: Every result row has run/config provenance; negative and unrun results remain distinct.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 12 / project week 10 — Sijin Lu

Tasks: GEN-11.

Deliver English target-repository START_HERE/HANDOVER, adapter/prompt/schema guidance and all known-issue dispositions.

Deliverables: docs/handover/generation.md, docs/generation.md.

Acceptance: New English docs are not copies of the original Chinese handover; relocated commands are tested and history preserved.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 12 / project week 10 — Pengyuan Xia

Tasks: PER-09.

Deliver profile usage guidance, policy versions, study outputs and human-review limitations.

Deliverables: docs/user_profiles.md, docs/research/personalisation.md.

Acceptance: Self-selected level is not measured mastery; findings map to real review.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 12 / project week 10 — Zeping Liao

Tasks: BE-17.

Deliver runnable local deployment, migration, backup/restore, account/corpus/job commands and troubleshooting.

Deliverables: docs/runbook.md, docs/backend_handover.md.

Acceptance: A different environment follows the guide; absent live keys have setup steps, not fabricated results.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 12 / project week 10 — Baiqing Huang

Tasks: FE-12.

Deliver chat user guidance, UI walkthrough and browser test evidence; remove misleading placeholder entry points.

Deliverables: docs/user_guide.md, docs/frontend.md.

Acceptance: A user can ask/follow up/inspect sources/change profiles/recover history without the author.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.

## Course week 12 / project week 10 — Chong Zhang

Tasks: QA-14.

Audit final evidence and reproducible checks, separating implementation, technical validation, live research and human acceptance.

Deliverables: docs/release_checklist.md, artifacts/reports/acceptance.json.

Acceptance: Missing ratings/models/originals remain explicit; do not flatten every status into DONE.

Actual executor/completion/evidence: not recorded at initial import. Carry-over is determined from the current ledger, never assumed complete by the suggested week.
