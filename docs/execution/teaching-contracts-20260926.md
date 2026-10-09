# Teaching contract repair — 26 September 2026

The new interactive reliability policy is `evidence_reliability_v3`. The registered [teaching and performance protocol](teaching-performance-protocol-20260926.md) fixes the requirements and decision rules. Original `evidence_reliability_v2` requests dispatch to `generation/checked_v2.py` with preserved `generation/reliability_v2.py` and v2 prompts. Original `legacy_joint_v1` dispatch and benchmark E0/E1 retain their existing paths. Executor: Codex; generation domain owner: Sijin Lu; integration owner: Xianshu Zhang.

## Textbook hints

The generator may propose a citation-free procedural hint. Draft parsing permits this only when the hint requires an online checker. The checker receives every visible claim and independently assigns its basis. Scientific assertions require exact textbook support and claim-local citations; learner givens require an exact problem quote; procedural guidance has no textbook support status. A model-supplied `clarification` label also undergoes claim classification. A plain mock checker cannot authorize the exception.

Publication still requires the enabled teaching controls: useful task-specific help, help-level scope, suggestion restraint, exact ordinary source display and cumulative prior exposure. A correct source that reveals the complete solution can reject a hint. Deterministic source-binding repair changes only citation bindings and requires a fresh check. Direct textbook answers retain their citation requirement. T0 has no permission to publish an uncited textbook answer.

## General knowledge

Every factual general-knowledge claim uses `basis=general_knowledge`, no fragments or textbook citations, and a separate `general_knowledge_status`. Published textbook `status` is null and `check_state=general_knowledge_model_checked`. The status is an automatic model assessment; independent human rating remains null. The checker cannot classify a factual assertion as nonfactual or claim textbook support in this mode. Factual assessment, teaching specificity, scope and disclosure remain separate conditions. General knowledge remains an explicit user mode.

## Tutor questions and attempts

The internal `chat_response_teaching_v3` schema extends the existing public response with two optional fields. `tutor_question` contains an exact substring of the visible answer and an expected response kind (`concept`, `numeric`, `explanation`, or `choice`). `learner_attempt_evaluation` contains a model assessment (`correct`, `incorrect`, `partial`, or `unclear`) and exact visible feedback. The public response remains `chat_response_v1`.

For `turn_role=learner_attempt`, visible feedback is required. The checker receives the original problem, pending question, learner reply, proposed evaluation and actual delivery. Its required `attempt_evaluation_ok` verdict must approve the evaluation. Successful output exposes the checked metadata in `GenerationOutcome.teaching_context`; backend task persistence assigns identity/version and step transitions. Metadata alone never grants a higher help level or indicates mastery. The original finite four-call and 180-second allowances still apply.

## Timing and transport

`checking_ms` sums `joint_check`, `joint_recheck` and `checker_contract_repair` exactly once. `model_total_ms` sums every recorded transport attempt once; native token-count calls remain separately visible. A checker-contract retry can change its judgment only; it retains the same draft and source projection. A semantic answer repair remains a distinct generation/check pair within the same allowance.

The v3 fixed generation policy occupies its own first system message. Dynamic evidence, state and memory follow it without evidence truncation. This makes the stable prefix eligible for provider caching. Actual returned cache-hit/miss token counters remain the evidence for a cache hit; prompt layout alone proves no latency or cost saving.

## Verification and remaining measurement

Focused scripted tests cover BUG-01/02, hidden facts, unsafe source display, every enabled hint control, direct answers, both answer modes, visible tutor metadata, independently checked attempt feedback, contract-repair timing and frozen v2 dispatch. These are authored contract checks. Live-provider quality, latency, cache behavior and independent human scoring have separate evidence in the parent execution record. No semantic success rate or performance improvement is inferred from the scripted suite.

The first focused run passed 117 tests and is retained at `evidence/teaching-performance/20260926/generation/attempt-01.xml`. The expanded second run passed 258 tests with one setup error when Windows denied pytest's shared temporary directory; that result remains in `attempt-02.xml`. Repeating the same suite with a new project-local temporary directory passed all 259 tests, zero failures/errors/skips, in `attempt-03.xml`. The last run before the live comparison passed the same 259 tests in `attempt-04.xml`. Ruff checks and focused type checking passed. `verification.json` preserves source hashes at that checkpoint and the v2 source/prompt lineage. These checks complement the complete project gate and registered study.

## Frozen live comparison

The evaluator `scripts/verify/teaching_contracts_live.py` froze eight authored task families, two from each official textbook, crossed with two answer modes, four interaction stages and v2/v3: 128 planned outcomes. The stages are direct answer, first hint, another hint and learner attempt. Fixed prior questions and learner replies provide identical contexts across policies. Each row is an independent request; the another-hint and attempt contexts are authored fixed inputs. They are not a longitudinal transcript of the preceding generated arm. The model is the configured DeepSeek `deepseek-flash`, with the same generator/checker configuration, four-call budget and 180-second budget in both arms. Concurrency is two. The pinned source archive and manifest precede execution of all 128 outcomes.

Actual evidence came from preserved real retrieval snapshots for cases `W8V2-Q01`, `Q03`, `Q07`, `Q08`, `Q13`, `Q16`, `Q19` and `Q22`. The runner verified 108 selected chunks against immutable official corpus text, hashes, source-unit offsets and page mappings. The corpus release is `4f11bd70-a486-4d16-b216-78cfe499530a`, containing 10,594 vectors of 384 dimensions. Textbook requests use identical selected evidence in both arms; general-knowledge requests use no textbook evidence. This comparison measures generation/checking on controlled evidence. CPU retrieval performance and HTTP persistence have their own records.

The frozen manifest SHA-256 is `e7132f8807218526f6c27a48b52db5bb14533475939d83cfd77726b5155d218d`. All 45 generation/evaluation source snapshots remain recoverable under `evidence/teaching-performance/20260926/private/live-contracts-corrected/frozen-source`. All 128 outcomes are terminal and each source check is unchanged. The public numeric record is [live-contracts-128-results.json](../../evidence/teaching-performance/20260926/generation/live-contracts-128-results.json).

| Mode and stage | v2 published / 8 | v3 published / 8 |
| --- | ---: | ---: |
| Textbook: direct | 5 | 5 |
| Textbook: first hint | 7 | 4 |
| Textbook: another hint | 4 | 5 |
| Textbook: learner attempt | 5 | 1 |
| General knowledge: direct | 7 | 7 |
| General knowledge: first hint | 8 | 7 |
| General knowledge: another hint | 8 | 8 |
| General knowledge: learner attempt | 7 | 4 |
| Total | 51 / 64 | 41 / 64 |

Publication was lower under this v3 snapshot. These are delivery counts under different contracts; they do not establish factual correctness or a quality improvement. The v2 path has no typed learner-attempt evaluation contract. Its 12 published attempt texts therefore have no validated typed attempt result. The v3 path publishes five of 16 attempt cases with this metadata. Independent human assessment remains empty.

The retained 36 failures comprise 21 `SEMANTIC_CHECK_FAILED`, 11 `CHECKER_INCONSISTENT`, three `TUTOR_QUESTION_NOT_VISIBLE` and one `ENHANCEMENT_VALIDATION_ERROR`. The last occurred before provider submission; the safe stored exception class does not establish its precise underlying cause. No failure was replaced by a retry selected for success. Published/failed latency distributions remain separate in the numeric record. Measured latency includes generation, prompt/tokenization, checking, repair and local source mapping; it excludes retrieval, queueing, database publication and browser rendering.

An earlier pilot used the same planned schedule but passed retrieval diagnostics into the strict evidence input schema and omitted `context_order`. Its textbook rows failed input validation before provider calls. The aborted pilot retains 70 terminal rows, 101 provider attempts and 58 unstarted rows. Correcting the runner projected the existing source text into the declared evidence fields; it did not alter generation policy. Pilot outcomes and charges remain separate from the corrected 128 comparison in [live-contracts-aborted-pilot.json](../../evidence/teaching-performance/20260926/generation/live-contracts-aborted-pilot.json).

## Successor contract and targeted live checks

After the 128 outcomes were terminal, revision `teaching_turn_contract_v3_1` added the required `tutor_question_ok` verdict to the same online checker call. It covers both metadata accuracy and an actionable question whose metadata is missing. A false verdict enters bounded repair. The exact checker schema hash and prompt hashes identify this successor independently of the unreleased v3 policy name.

When a model proposes a tutor question separately from its body, the server may append that exact question before claim extraction, attribution, source projection and every teaching check. This is permitted only for checked hints. The original model draft and `visible_tutor_question_v1` transformation are retained privately. The resulting full visible body must pass the independent checker. The public text is unchanged after acceptance. T0 cannot use this materialization route. Feedback about the learner's own completed step may be procedural; an added scientific assertion still needs the relevant factual basis and support.

The successor focused suite passed 263 tests in `generation/posthoc-01.xml`; Ruff and focused mypy checks passed. New negative cases cover an unsafe appended question, omitted metadata, scientific facts hidden in feedback and the unchecked T0 boundary. The human-review importer separately passed 13 tests in `generation/review-import.xml`, including zero-versus-missing scores, invalid ratings, applicability, exact row identity and preservation of prior imports.

Eight further provider checks were frozen separately by `scripts/verify/teaching_contracts_posthoc.py`: two case families, both modes, first hint and learner attempt, current v3 only. The cases were selected after observed failures and establish targeted engineering evidence. They provide no held-out estimate of improved quality. [live-contracts-posthoc-results.json](../../evidence/teaching-performance/20260926/generation/live-contracts-posthoc-results.json) preserves all eight results and the successor manifest hash.

Five of eight outcomes published with checked visible tutor-question metadata: four general-knowledge outcomes and the textbook tissue-comparison first hint. Both general-knowledge attempt outcomes carried checked visible feedback. Three textbook outcomes failed:

- Tissue-comparison attempt: the draft and repair disclosed both distinguishing tissue values at a hint level that permitted identifying the comparison dimension. Scope and cumulative checks rejected publication.
- Isotope first hint: the checker first assigned contradictory factual/nonfactual metadata, then used a general-knowledge factual basis in textbook mode. Publication remained blocked.
- Isotope attempt: the draft disclosed the complete numerical solution. The checker additionally generated derivation variable names outside the existing schema, including on its contract retry. The failure is retained.

The final snapshot therefore has working tutor-turn metadata and preserved disclosure checks, with continuing model reliability failures for these textbook tasks. Automated delivery and independent semantic quality remain separate outcomes.

## Usage and independent review

| Cohort | Provider attempts | Input tokens | Output tokens | Cached input tokens | Uncached input tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| Aborted runner pilot | 101 | 310,488 | 23,872 | 234,624 | 75,864 |
| Frozen 128 comparison | 363 | 2,109,408 | 128,117 | 1,231,741 | 877,667 |
| Eight post-hoc checks | 21 | 151,627 | 9,223 | 75,264 | 76,363 |
| These three cohorts combined | 485 | 2,571,523 | 161,212 | 1,541,629 | 1,029,894 |

The provider returned the listed counters. Combined tokens are 2,732,735. No invoice or verified applicable tariff was available, so monetary cost remains null. These totals include failed attempts and exclude separate administrator connection probes and HTTP workflow checks. Cache-hit tokens show provider caching occurred; the experiment does not isolate the causal effect of prompt-prefix layout.

The corrected comparison exports 128 blinded rows for each of two reviewers. All 256 rows are blank. The reviewer package contains the actual responses, selected source anchors, task expectations and scoring guide; the condition mapping remains coordinator-private. Missing responses retain blank semantic scores and remain in delivery denominators. General-knowledge textbook-support scores are inapplicable. The tested import command preserves missing values and validates actual submitted ratings; see [teaching-contract-review.md](teaching-contract-review.md). Online checker decisions and model attempt feedback are not independent human ratings. Learning gain has not been measured.
