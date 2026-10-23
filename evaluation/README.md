# Independent evaluation tooling

This package evaluates the shared learning assistant. It contains no replacement answer engine. SciQ labels/support and review keys remain evaluator-only; the product does not import this package or need its datasets.

`sciq_openqa` is a project-defined stem-only diagnostic using ChatResponseV1. `sciq_mcq` is the separate four-choice selection diagnostic. `chat_scenarios` captures actual conversations and rates behaviour independently. `profile_study` orchestrates the shared TeachingStudyService on matched frozen base answers. These protocols never share an unexplained headline accuracy.

## Running the application-backed rehearsal

From the project root, with the real API/database/worker configured and the backend import path available:

```text
python -m evaluation.runner --config configs/evaluation/mock_openqa.json
python -m evaluation.runner --config configs/evaluation/mock_mcq.json
python -m evaluation.runner --resume RUN_ID --root evaluation/private_runs
```

The configs use `app.modules.experiment.bridge:create_backend`; the implementation belongs to the application integration. See `BACKEND_PROTOCOL.md` for the exact interface. Set the normal backend import environment used by Compose (project root plus backend on PYTHONPATH). Missing application integration is an explicit error, never a fallback to a canned answering adapter. `--once` performs one nonblocking submit/poll pass; an unfinished run exits 2 and is resumable. `--cancel` preserves all scheduled rows. Real model execution requires prior authorization plus `--allow-live`; all supplied defaults are mock-only.

Private immutable manifest/command/reference files are in `evaluation/private_runs/RUN_ID/`. References never appear in public registered manifests or answer commands. All items are preregistered before the first call. Submission receipts are persisted before polling. Resume polls existing receipts and never repeats terminal items. An interrupted submission is looked up by its stable key; no found receipt means uncertain, requiring reconciliation. Do not remove `runner.lock` without verifying its recorded process is gone.

In one-off containers, use mounted `EVALUATION_PRIVATE_ROOT` and `EVALUATION_EXPORT_ROOT` directories. The runner honors these environment variables for both new and resumed runs. Terminal scorer values may be published through the backend's strict `record_scores` hook for administrator results; labels/support still stay private.

Exports are under `evaluation/exports/PROTOCOL/RUN_ID/`: public immutable manifest, all scheduled JSONL/CSV outcomes, aggregates, missingness and a full-response review subset selected before execution. Costs remain null when unknown. Do not overwrite historical generation `results/week5/`. A mock rehearsal is software evidence only.

## Private data acquisition boundary

`datasets/sciq.py` reads provided JSON/JSONL official-shaped records, validates question IDs/four normalized-distinct candidates, and records actual split count/revision/SHA-256. Source file identity and declared expected count/hash must match when configured. Invalid references reject the freeze; no post-result item is removed from a denominator. The bundled four rows are explicitly authored software fixtures, not actual SciQ data or an approved OpenStax release.

OpenQA projects only question identity and the exact stem; changing private references/support/distractors leaves its command unchanged. MCQ sorts candidates then applies a per-question seeded shuffle, so changing the correct label among the same four candidate texts does not change their presentation. Only the private result contains the correct label. Neither adapter indexes SciQ support as textbook content.

## Metrics and comparisons

`metrics/scoring.py` freezes `conservative-v1`: NFKC, casefold and whitespace collapse, preserving negation/signs/numbers/units. EM requires equal nonempty compact answers. Token F1 uses multiset overlap of words, signed numbers and mathematical symbols. Full-explanation substring search is never used. Failed/refused/cancelled/incomplete/missing-answer items contribute zero to scheduled lexical denominators. Legitimate paraphrases may score poorly; full-response correctness/support review remains separate.

Retrieval uses relevant/actual-returned precision, judged-positive recall, first-relevant reciprocal rank and graded nDCG. Missing qrels and zero IDCG remain unavailable as applicable; unjudged results are counted visibly. Citation identifier/text-hash validity is distinct from factual support. Binary paired scores use exact McNemar discordants and paired bootstrap intervals; continuous scores use paired differences. Repeated turns are clustered by scenario and do not receive an invalid per-turn McNemar test.

`analysis/ablations.py` requires one declared factor, fixed question/source/model/prompt/scorer identities and validation-only setting selection. R1/R2/R3 cannot be relabelled E1. Changed chunks require compatible source-span judgements or reannotation. A compatible experiment design is not an executed scientific finding.

## Source review and blind ratings

```text
python -m evaluation.annotations.cli qrels-template --candidates CANDIDATES.json --output PRIVATE_QRELS.json
python -m evaluation.annotations.cli qrels-validate --input PRIVATE_QRELS.json --release RELEASE --processing PROCESSING_ID
python -m evaluation.annotations.cli blind-template --outputs STUDY_OUTPUTS.json --destination PRIVATE_REVIEW_DIR --seed 5703
python -m evaluation.annotations.cli ratings-analyze --package PRIVATE_REVIEW_DIR/private_package.json --ratings COMPLETED_RATINGS.csv --reviewers REVIEWER_A REVIEWER_B --output ANALYSIS.json
```

Qrel templates pin release, processing IDs, exact source spans and text hashes. Null grades stay present until a real reviewer/date is recorded. Changed pools need a new version; source overlap is a review aid, not automatic transferred relevance.

Blinded packages retain all C0/C1/C2 × beginner/intermediate/advanced items, including failed outputs. Base answer, evidence and model must match per question. The private key maps opaque IDs to conditions; the reviewer view omits those identities. Ratings use the canonical `personalisation.rubric` 0–3 anchors for six dimensions and correctness/groundedness gates (pass at ≥2). Empty ratings remain null, failed outputs cannot receive invented ratings, duplicate reviewer/item entries are rejected, and paired analysis aggregates independent reviewers by question. Output ratings do not measure student learning gains.

`python -m evaluation.study --config STUDY_CONFIG.json --blind-output PRIVATE_REVIEW_DIR` freezes and runs the nine-condition design through `personalisation.study.TeachingStudyService`. The config provides `questions_path`, `private_root`, optional `model_config` and seed. Each question supplies question_id/question/base_answer/evidence from real saved output. `--resume PRIVATE_STUDY_DIR` resumes pending items; uncertain paid execution never repeats automatically. These files do not write or mutate learner messages.

The application also persists this independent study in PostgreSQL: administrator `POST /teaching-studies` with saved neutral `base_answer_ids`, seed and optional configuration_id freezes all nine variants per question; start/cancel/results/export use the returned `/experiments/{id}` endpoints. Each worker job records its own budget and attempt history. Existing answers and citations remain immutable when a study fails or is cancelled. Download its JSON export and give it directly to `blind-template`. Actual independent ratings are still required; the API never fabricates them.

## Conversation fixtures and tests

`conversations/scenarios.json` contains 12 distinct 3–5-turn families. `source_requirements.json` describes matching authored corpus passages; private review claims are in `private_fixture/conversation_expectations.json`. A real browser or `ChatBackend` implementation supplies session/profile/re-login operations. The driver sends only ordinary content/use_profile and saves observed results. Completion rates are data-flow measures, with semantic review null until actual review occurs.

`python -m evaluation.conversations.http_backend --email REHEARSAL_ACCOUNT --output evaluation/exports/chat_scenarios/UNIQUE_CAPTURE` connects to the actual HTTP API and worker. Set `EVALUATION_ACCOUNT_PASSWORD` in the environment. Use a dedicated rehearsal account: the profile-continuity case updates its saved profile, and all conversations persist normally. The CLI freezes the scenario manifest before calls, saves each observed scenario, reports separate conversation timing p50/p95 and leaves unavailable phases/cost null. It is a capture tool, not an automatic replay/resume mechanism: an interrupted server job must be reconciled through its saved application state before a new capture. No credentials or private expected answers are exported.

Run the focused software suite:

```text
python -m pytest tests/unit/test_evaluation_metrics.py tests/unit/test_evaluation_runner.py tests/unit/test_evaluation_annotations.py tests/unit/test_evaluation_study.py tests/unit/test_evaluation_backend.py tests/integration/test_evaluation_postgres.py -q
```

These tests exercise hand calculations, leakage invariants, frozen/resumable state, uncertainty/cancellation, source-change halts, blinded missingness and the actual shared mock teaching service. The integration module creates a disposable PostgreSQL database, applies real migrations and drives real APIs/workers, including all twelve authored conversation families. Browser acceptance, actual SciQ/OpenStax acquisition, live research and human review remain distinct evidence. See `VERIFICATION.md` for the scope of the recorded run.


<!-- BEGIN CS30_OFFLINE_RAG_FRAGMENT_BUNDLES_20261009_06 -->

## Declared fragment-support availability

`fragment_coverage_v1.measure_fragment_coverage(selected_fragment_ids, requirements, known_fragment_ids=...)` evaluates caller-reviewed complete support bundles. Each bundle is an AND of immutable fragment identities; alternative bundles are OR options. Only actually selected identities count. Unknown/duplicate identities and empty individual bundles reject; a missing complete support declaration remains uncovered. Results separate requirement kinds and never infer source entailment, model use, answer accuracy, human Gold or permission to publish. Twenty unit controls validate these identity semantics.

[Bounded actual comparison and limitations](../docs/execution/20261009-offline-rag-predicate-coverage-result.md); [exact sources, results and approval rejection](../docs/execution/evidence/20261009-offline-rag-predicate-coverage06/index.json).

<!-- END CS30_OFFLINE_RAG_FRAGMENT_BUNDLES_20261009_06 -->


<!-- BEGIN CS30_DIRECT_USER_CHECKER_VERIFIED_20261010_07 -->

## Direct authorization and actual checker acceptance - 10 October 2026

The user's latest direct instruction authorizes continued 5703 OpenRouter development and experiments without repeated fee confirmation. The unchanged prepared checker05A was formally approved and actually executed once: HTTP200/stop, strict JSON/full conditional schema/business PASS, ten textbook-supported claims, no actual issues, USD0.0082304 and zero new UNKNOWN. The related three calls total USD0.0212086. Actual repaired selections are F053, complementary F054/F055, and ev_007/F037; all seven other claims remain unchanged. Independent actual-selected-source review is retained. Earlier two-request STOP/denial wording is historical and superseded for this authorized additional check; old artifacts, older USD0.09 UNKNOWN and registries remain unchanged. The runner's older delegated authorization-origin label is historical; the direct-user receipt is the effective authority. This is a saved-answer development case, not fresh teacher generation, native publication, held-out accuracy or full-answer timing. Protected native metadata denials remain untouched; current new Dense/Hybrid generation and full native timing remain unrun, project_complete=false.

The archived06 producer runner requires its original workspace fixtures and helper path; the Main copied evidence is retained original-run evidence rather than a portable rerun package. [Current actual result and evidence](../docs/execution/20261010-compound-predicate-checker-verified.md).

<!-- END CS30_DIRECT_USER_CHECKER_VERIFIED_20261010_07 -->


<!-- BEGIN CS30_MATCHED_RAG_COMPONENT_RESULT_20261010_08 -->

## Matched component RAG experiment - 10 October 2026

Two real matched GenerationService arms completed for What is homeostasis?: Dense5 6437.308 ms and Hybrid5 7719.444 ms, one teacher and one checker each, USD0.0152063 known cost and zero new UNKNOWN in successor08e. Shared visible corpus10594/public documents4 and top5 inputs are frozen; five cropped teacher ranges differ from five full raw chunks. Required definition is covered by both. Exact provided-excerpt source assessment is Dense3 complete plus1 partial versus Hybrid4 complete; Dense claim2 selects only F014 and cannot borrow F016 from another claim for its added equilibrium-maintenance goal. Original four-supported/accepted model labels remain unchanged. The agent did not independently read/hash-verify files because its tool approvals timed out; Root separately verified actual wires and161 source/prompt pins. One earlier failed attempt08d retains UNKNOWN and USD0.03 hold; older USD0.09 protection remains unchanged. These are single-case component observations, not a benchmark winner, native Send-to-DOM time, human Gold or registry promotion. The latest user explicitly approved original-path native seed/auth binding reads and local controller preparation; same-path schema/reference projections passed without exporting authentication values. Native execution continues separately, whole-current883 remains unverified and project_complete=false. OpenRouter continuing fee authorization is retained without repeated fee questions.

[Actual results, exact inputs and retained evidence](../docs/execution/20261010-matched-rag-component-result.md).

<!-- END CS30_MATCHED_RAG_COMPONENT_RESULT_20261010_08 -->


<!-- BEGIN CS30_NATIVE_COMPLETE_ANSWER_RESULT_20261010_11 -->

## Native complete-answer acceptance - 9 October 2026 UTC

Native11 passed one fresh-chat Q2 whole UI/controller regression at 2026-10-09T21:57:41.528927+00:00: complete cited DOM 24.246 seconds, citation opening/refresh PASS, four settled POSTs/$0.0173608, zero new UNKNOWN and closed resources. Separate selected-source review is 5 complete/3 partial of 8; model support labels remain unchanged. The 5–10 second target, full latest-source/multimodule/same-worker qualification and human/course evidence remain open; project_complete=false. Native09/10 failures, exact prompt adoption, 19 units and 29 liveness controls are retained. No registry promotion or release-pointer change is implied.

[Actual results, exact inputs and retained evidence](../docs/execution/20261010-native-complete-answer-acceptance.md).

<!-- END CS30_NATIVE_COMPLETE_ANSWER_RESULT_20261010_11 -->
