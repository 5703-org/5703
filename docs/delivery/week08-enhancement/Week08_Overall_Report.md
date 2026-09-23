# Week 8 Learning Enhancement Report

CS 30 1 | Week 8 enhancement | 2026-09-20

## Checkpoint and scope

The Personalised AI Learning Assistant now integrates claim-specific source highlights, opt-in learning memory and explicit direct or hint teaching controls. The implementation joins saved answers, source permissions, memory versions and actual display events. Ordinary textbook questions still request a complete direct explanation, while the learner can deliberately enter or leave a hint sequence.

The research checkpoint retains 900 formal hint requests, 180 direct-answer citation requests and 36 memory conditions. T2 produced 100/180 valid hints (55.6%), compared with 110/180 (61.1%) for T1. The task-paired difference was -5.56 percentage points, with a 95% bootstrap interval from -13.33 to 2.22 points. The measured result gives the team a concrete reliability problem to investigate: increased rejection can outweigh the intended control benefit. Independent scientific and pedagogical ratings are the next evidence requirement.

The eight reports follow the original team responsibilities. Codex performed the shared implementation, scripted execution and document preparation. Named members remain the accountable module owners. Independent reviewers have supplied 0 ratings.

## Implemented workflow

Ordinary textbook requests use complete direct answers by default. Explicit hints persist within the current problem; requests for a full explanation and new problems change that task state. Textbook and general-knowledge modes retain separate provenance. Source selection, checked generation, learner presentation and memory snapshots are joined through versioned interfaces.

A checked request normally generates once and performs one batch check. A rejected draft may use one repair and one recheck within the same four-call and 180-second limit. Exact fragment identity is checked structurally; semantic support is a separately recorded model judgment. No unchecked repair is published. Memory updates have their own bounded jobs and deletion fences.

## Versions and comparison methods

Formal execution used protocol w8-enhancement-v1, source manifest 88431c514814f8a7454c73e1eb9d2031fd7c58cdb32582cb56c676249bca766c and the frozen runtime hashes listed in its public manifest. The active corpus remains 4f11bd70-a486-4d16-b216-78cfe499530a, with 10,594 vectors of dimension 384. The original four-book processing and earlier research artifacts remain preserved.

The external model was deepseek-flash through openai_compatible, configuration model-settings:fababaa3-e482-47c4-b973-d940453354a2. This is a provider alias. The local tokenizer revision is 7872f01b1d1fe23eabc4c98b48bffcef5a386062. Generation reserved 1024 output tokens and the checker reserved 4096; each checked request shared a four-call, 180-second maximum. Separate judges used their recorded budgets.

After the original live regression reached a terminal state, a separate HTTP task-resolution correction introduced learning_task_v2. It restricts implicit navigation to commands without a new named subject and removes an unserialisable regular-expression match from persisted state. Its isolated and portable verification is recorded separately. The frozen formal GenerationService outputs, prompts and comparison results remain unchanged.

Twelve development tasks informed the frozen implementation before the 60-task formal source set. Formal tasks span biology and chemistry, with comparison, process reasoning and calculation. Each task supplies the same three hint turns to T0 through T4. T0 uses prompt-only teaching; T1 checks the answer body; T2 additionally controls current source display and cumulative exposure. T3 and T4 remove those two components separately.

Generation receives the actual question and frozen textbook evidence. Private reference answers and per-turn help allowances are evaluator inputs. The formal runner calls the same generation service and preserves delivered projections; independent HTTP journeys verify durable product state. Source panels are opened on every formal hint turn, making ordinary source exposure part of the tested policy.

A separate direct-answer comparison keeps the question and initial source candidates fixed across full passages, post-generation spans and bounded preselected spans. Its corrected judge evaluates complete supported answers and citation coverage. The retained initial judge mixed in a hint allowance; its semantic scores are superseded by version 2 without replacing any generated result.

## Recorded results

### Formal teaching comparison

Phase: formal. Planned 900; accounted 900; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| published answer | 595 |
| SEMANTIC CHECK FAILED | 259 |
| nonanswer | 45 |
| ENHANCEMENT VALIDATION ERROR | 1 |

T2 produced 100/180 valid hints (55.6%), compared with 110/180 (61.1%) for T1. The task-paired difference was -5.56 percentage points, with a 95% bootstrap interval from -13.33 to 2.22 points.

The added joint controls did not improve the prespecified primary outcome in this run. Strict rejection reduced answer availability. Successful-answer support scores alone would hide this tradeoff.

By task type, valid hints among planned requests were as follows. Comparison: T0 44/60, T1 33/60, T2 28/60, T3 24/60, T4 36/60. Process: T0 58/60, T1 50/60, T2 49/60, T3 47/60, T4 45/60. Calculation: T0 51/60, T1 27/60, T2 23/60, T3 23/60, T4 25/60. Each cell includes unavailable answers in its denominator; these secondary strata are descriptive.

The separate judge rated published answers on four dimensions. T0: supported 171/171, concrete useful help 171/171, within permitted scope 153/171, factual error 0/171; T1: supported 115/115, concrete useful help 115/115, within permitted scope 110/115, factual error 0/115; T2: supported 104/104, concrete useful help 104/104, within permitted scope 100/104, factual error 0/104; T3: supported 97/97, concrete useful help 97/97, within permitted scope 94/97, factual error 0/97; T4: supported 108/108, concrete useful help 108/108, within permitted scope 106/108, factual error 0/108. Each fraction uses that condition's judged published answers, so it excludes failed generation. The factual-error numerator counts observed automatic flags, with independent scientific review pending.

| Metric | Value | Scope |
| --- | --- | --- |
| T0 | 153/180 | Valid supported useful within-scope hints among all planned requests |
| T1 | 110/180 | Valid supported useful within-scope hints among all planned requests |
| T2 | 100/180 | Valid supported useful within-scope hints among all planned requests |
| T3 | 94/180 | Valid supported useful within-scope hints among all planned requests |
| T4 | 106/180 | Valid supported useful within-scope hints among all planned requests |

Limit: The same DeepSeek family generated and judged outputs. Three turns share each task; the interval resamples 60 tasks with 10,000 fixed-seed repetitions. Independent human ratings remain 0.

Evidence IDs: hints, manifest.

### Direct answers and attribution

Phase: formal. Planned 180; accounted 180; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| published answer | 79 |
| SEMANTIC CHECK FAILED | 89 |
| nonanswer | 9 |
| CONTEXT LIMIT | 2 |
| CHECK CLAIM MISMATCH | 1 |

Whole passage: 28/60 published and 27/60 complete supported answers under the corrected automatic rubric. Post-generation spans: 22/60 published and 22/60 complete supported answers under the corrected automatic rubric. Preselected spans: 29/60 published and 27/60 complete supported answers under the corrected automatic rubric.

Published source previews averaged 4,253.6, 1,223.4 and 799.6 characters for whole passages, post-generation spans and preselected spans. These lengths describe each method's successful outputs; the methods published different subsets. Exact slicing and source identity passed for the published projections.

| Metric | Value | Scope |
| --- | --- | --- |
| Published answers | 79/180 | All three strategies combined; compare each 60-item condition separately |

Limit: The first direct-answer judge incorrectly received hint restrictions. Version 2 rejudged the same saved outputs; generation results and failures stayed unchanged. Shorter previews alone establish no verification-speed benefit.

Evidence IDs: citations, attribution.

### Learning memory comparison

Phase: memory. Planned 36; accounted 36; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| published answer | 16 |
| generation error | 20 |

profile session: 5/12 published answers; appropriate-use ratings 3/5 among those answers; state screens 26/34. rolling summary: 5/12 published answers; appropriate-use ratings 1/5 among those answers; state screens 31/34. structured memory: 6/12 published answers; appropriate-use ratings 2/6 among those answers; state screens 34/40.

Correction retained an earlier preference in the structured condition; extraction and question-scope screens also failed in retained cases. Expiry, global-off, turn-profile-off and deletion fencing have separate state evidence.

| Metric | Value | Scope |
| --- | --- | --- |
| Separate memory judgments | 16 answers | 20 generation errors remain ungraded in the 36-condition denominator |

Limit: Literal state screens differ from model-rated appropriate use. The small published subsets and shared-family judge support no ranking of learning benefit.

Evidence IDs: memory, memory_usage.

### Existing live reliability catalogue

Phase: regression. Planned 110; accounted 110; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| expected checks passed | 62 |
| expected checks failed | 48 |

All 110 original non-fault questions ran through actual HTTP and the durable worker. 62 met their recorded structural and expected-response checks; 48 retained deviations. Terminal job counts: failed 41, succeeded 69.

| Metric | Value | Scope |
| --- | --- | --- |
| Remaining fault catalogue | 10 IDs /14 assertions | Current isolated tests cover provider errors, permissions, revocation, cancellation and timeout |

Limit: This reuses an existing development/regression catalogue. It measures software behavior and provenance; independent scientific correctness remains separate.

Evidence IDs: regression, faults.

### Final software verification

Phase: regression. Planned 8; accounted 8; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| passed stage | 8 |

The final gate completed at 2026-09-20T06:48:19.544659+00:00 with unchanged captured source. Its actual test artifacts record 605 Python passes and 78 frontend passes; these counts are reported by suite, while the table denominator is gate stages.

| Metric | Value | Scope |
| --- | --- | --- |
| Python tests | 605 | Passed cases in the final pytest XML |
| Frontend tests | 78 | Passed cases in the final frontend log |

Limit: Unit, integration and browser scenarios overlap in behavior. Their counts are never summed into a scientific accuracy denominator.

Evidence IDs: gate.

### Actual learner control journeys

Phase: interface. Planned 3; accounted 3; missing 0. All scheduled outcomes are included.

| Recorded outcome | Count |
| --- | --- |
| source journey passed | 1 |
| memory journey passed | 1 |
| teaching journey passed | 1 |

Desktop 1440 and narrow 390 views exercised claim-specific highlights, explicit full-source disclosure, source keyboard focus, saved-memory Undo, a real 409 edit conflict with draft retention, deletion and task controls. Three new teaching requests produced hint 1, hint 2 and a full explanation on the same task.

| Metric | Value | Scope |
| --- | --- | --- |
| Delivered and rendered | 3 and 3 | Separate persisted events for the teaching journey; rendering establishes visible DOM |

Limit: Physical keyboards, native IME, assistive technology, reading and comprehension require separate observation.

Evidence IDs: source_ui, memory_ui, teaching_ui, teaching_events.

## Calls cost and retained failures

| Purpose | Calls | Input tokens | Output tokens | Estimated cost |
| --- | --- | --- | --- | --- |
| connection probe | 1 | 116 | 5 | Unknown |
| generation | 1667 | 11,872,252 | 278,238 | 3.811403 CNY |
| generation format repair | 38 | 285,145 | 4,740 | 0.033029 CNY |
| joint check | 1374 | 11,740,527 | 546,372 | 11.816741 CNY |
| joint recheck | 897 | 7,625,323 | 358,547 | 6.844773 CNY |
| memory extraction | 14 | 5,019 | 767 | 0.006456 CNY |
| memory use judge | 16 | 17,490 | 3,474 | 0.022982 CNY |
| offline judge | 753 | 1,782,971 | 163,995 | 1.701115 CNY |
| rolling summary | 13 | 2,553 | 154 | 0.003169 CNY |
| semantic repair | 898 | 7,703,948 | 166,715 | 2.222743 CNY |

The purpose-level cost ledger records the input, output and cache usage for each attempt. Estimates use the official 20 September CNY tariff. The connection probe's cache split is unavailable. Evidence ID: costs.

The reconciled known-usage estimate is CNY 26.462411 across 5,671 recorded attempts. Usage is missing for 0 of these attempts; monetary estimates are unavailable for 1. These are dated tariff estimates; the provider invoice is a separate record.

Recorded provider attempts and supplied call-level usage are counted, including retained failures. Missing usage produces an unknown cost, not a zero charge.

Study completion timestamps are tariff-period proxies where individual call timestamps were unavailable. All current calls fall on the recorded off-peak Sunday.

Currency values are known-usage estimates at the dated published CNY tariff, not account invoices. Provider token usage differs from local context-window counting.

Only explicitly supplied HTTP/memory accounting files are included; original unrelated learner activity is excluded.

Rejected checked outputs. Only 595/900 formal hints and 79/180 direct citation requests published answers. Errors and nonanswers remain in every planned denominator. The frozen outputs stay available for false-rejection and support review. A revised policy requires a new dated development and evaluation record. Evidence IDs: hints, citations.

Source association limits. The structural audit found 64 published answer-text claims linked to source fragments without their own inline marker, and selected incomplete blocks in some whole-passage and post-generation outputs. Exact identity and public projection checks remain valid; independent reviewers must examine local citation usability, atomic context and scientific support. Evidence IDs: attribution.

Memory and request failures. The memory comparison retained 20 generation errors, a superseded preference after correction and extraction/scope failures. The early five-request lifecycle smoke retained one memory-enabled context-limit error. These cases remain visible beside successful UI control and deletion checks. No failed answer was counted as a completed learning interaction. Evidence IDs: memory, lifecycle.

Task boundary correction after the study. An isolated reproduction found that a new named topic could inherit the old hint task, and a navigation predicate could place a regular-expression match into JSON state. The separately verified learning_task_v2 correction narrows implicit continuation and preserves explicit task commands and historical frozen requests. The original live failures remain retained. Evidence IDs: task_boundary, regression.

Updated command verifier. The first aggregate run retained a chat-scope verifier failure because its input whitelist still expected the earlier three fields. The authorized teaching controls extend that contract to six fields. The verifier now checks the exact six fields and their defaults while retaining evaluator separation. The current second aggregate run records the complete rerun; the original failure remains available. Evidence IDs: gate_prior, gate.

## Independent human review

Completed independent ratings: 0. Actual independent reviewers: 0. The preceding results use automatic evaluation.

Blinded forms are prepared for all formal outputs and 36 memory conditions. The timed highlight tool presents identical answer and evidence content as paragraph or marked fragments, with counterbalanced seeded ordering and actual interaction timing. Participant responses remain uncollected.

The final highlight material contains 148 actual claim items and 296 paired presentations. Browser loading verified 344 source displays and exact Unicode ranges, including 70 non-ASCII answer claims. Timed Start was unused; completed ratings and imported observations remain zero.

- Assign the two reviewers different identities and provide their separate randomized material and blank CSV. Keep the coordinator condition key and automatic ratings separate.

- Each reviewer records support, useful help, permitted scope or the relevant citation/memory dimensions with a concrete reason. Preserve failed and missing outputs in the planned schedule.

- Run the supplied review importer with the actual reviewer identity. It validates item IDs, rubric versions, complete score sets and timestamps; retain original submissions and report paired agreement and disagreements.

- Record any adjudication separately from the two original ratings. Compare automatic and human judgments only on actually paired rated items. The highlight tool downloads observed judgment and elapsed-time data; analyse order effects and correctness alongside time.

## Operation and delivery

Fresh CPU installation. Use the documented locked installation and source-import workflow, apply migrations, and configure the local model through the administrator page. Start the API, durable worker and frontend using the packaged startup instructions. Verified scope: A fresh Windows environment with Python 3.13.2 and Torch 2.8.0+cpu completed actual CPU retrieval and separate mock/live checks. 243 deployed runtime files and 80 resources matched recorded hashes.. Evidence IDs: portable, portable_app.

Learner controls. Open a claim citation to inspect its approved highlight. Request complete source explicitly. Enable memory before saving a durable preference, inspect its source, then edit or delete it. Another hint preserves the current task; full explanation and new problem are deliberate controls. Verified scope: Actual saved API/browser flows include permitted projection, conflict handling, reload and event persistence.. Evidence IDs: source_ui, memory_ui, teaching_ui.

The portable proof verifies a fresh same-host CPU environment, an isolated new database, 10,594 preserved vectors and 80 original resources. Its explicitly enumerated runtime subset is version-bound; subsequent research/report files are reconciled separately.

The complete archive contains the application, verified runtime resources, research archive and nine English reports. Eight member packages contain disjoint changes against the preserved 16 September release. The accompanying PACKAGE_VERIFICATION.json records final archive hashes and membership checks.

## Limitations and Week 9 work

The tasks are authored scientific cases, and the generator and automatic judge share a model family. The negative primary contrast and wide interval require scrutiny of false rejection, leakage and annotation consistency. Successful-only source lengths and model scores have a narrower scope than the planned-request outcomes.

The fresh installation runs on the same Windows host. Physical-device accessibility, independent review time, transfer learning and delayed retention still need measured data. Formal outputs remain frozen so the team can compare those observations with the current automatic conclusions.

- Collect two independent reviews of the frozen outputs, prioritising all disputed and rejected cases plus a prespecified random sample; report completion, agreement and adjudication counts.

- Investigate the negative T2-versus-T1 result and memory correction failures on development cases, then register any changed policy before another formal run.

- Collect paired highlight timing and correctness using actual participants and recorded order, and extend the verified installation and keyboard/accessibility checks to another available physical device.

## Evidence references

Paths are relative to the delivered project root. Full hashes identify the dated records used for this report.

Frozen enhancement protocol. Prespecified comparisons, budgets, provenance and review methods.

docs/execution/week08-enhancement-protocol-20260920.md

SHA256 40d3291b94273ed86fac7ff49f690db223ef0f84d2cdc90f638cd97ff6e0dca6

Formal hint comparison. All 900 requests and task-paired model-assisted analysis; human ratings remain separate.

evidence/week08-enhancement/20260920/formal-hints-analysis.json

SHA256 3037903e73ce1046dc7e50236f2e628034b3d1e42d4ee28125ae4dc6c8ea9cd3

Corrected direct-answer citation analysis. Same 180 generated outcomes with corrected direct-answer judging; the original judge is retained.

evidence/week08-enhancement/20260920/formal-citations-judge-v2-analysis.json

SHA256 6aec13d0175ce4f7be47d2f78bf125e405fb82bda94cdf6ac12edb3e4f4c2dd5

Frozen formal execution. Source, dataset, runtime, model, checker and call-budget identities.

evidence/week08-enhancement/20260920/formal-hints-run-manifest.json

SHA256 0de4189bad8fb3fdf63df695f162600b0bb17586e75d40d04947f1b994b7eff0

Independent structural attribution audit. Exact source relationships and published-only length measurements. Semantic fields from its original judge are excluded here.

evidence/week08-enhancement/20260920/formal-attribution-audit.json

SHA256 aff7b205881e13565688ff455d70bf09abef738cd1722680fbcb7d102504c3e5

Memory comparison and separate judging. All 36 authored conditions, state screens and 16 answer judgments; zero human ratings.

evidence/week08-enhancement/20260920/memory-study-final-summary.json

SHA256 77dc2d3080f413728f556d52d692db553d87ae782fad5c99ca0f87fd1ca8c582

Memory attempt accounting. 185 unique reservations with reported usage, including extraction, summaries and separate judging.

evidence/week08-enhancement/20260920/memory-usage.json

SHA256 6dafb1989f9f465b233010804f8f9da7279f6b1107133f39126aef7104abe7be

Memory independent review status. Actual reviewer and rating counts with agreement left unavailable until collection.

evidence/week08-enhancement/20260920/memory-human-review-status.json

SHA256 ef75f04ada157ca4c1a920084f17a23e9447f31e932820016d7848f9fe4bb106

Claim source browser journey. Actual approved preview, explicit expansion, keyboard and 1440/390 viewport checks.

evidence/week08-enhancement/20260920/frontend/live-source-browser-summary.json

SHA256 33d81448493b3c9125b5b71d632626ad4c1f837b4a944b9d6044530a63ea9b14

Memory browser journey. Actual opt-in, source, edit conflict, retained draft, deletion and save Undo.

evidence/week08-enhancement/20260920/frontend/live-memory-browser-summary.json

SHA256 4ca1b7d75ec5d4b4f0050d799251a1ba231dd4e6cb85062ace9a6bd02083a51b

Teaching browser journey. Three saved hint/hint/full-answer requests and actual rendering receipts.

evidence/week08-enhancement/20260920/frontend/live-teaching-browser-summary.json

SHA256 29dc575d39d1476aeb0a87f5ee5c3a19f2bcdca9dc7805dc6ebd48524f235d2b

Teaching delivery and rendering. Three published presentations with separate delivered and rendered event identities.

evidence/week08-enhancement/20260920/backend/browser-teaching-exposures.json

SHA256 2e5c51be731fa96cd534a4a62cc3fbbf0a906e947da34dc69e3441ef7e26ffe3

Fresh CPU runtime parity. Actual same-host fresh installation and explicitly enumerated deployed runtime subset.

evidence/week08-enhancement/20260920/portable/source-parity-final.json

SHA256 7e855c7a717d7421b8fcd90dbfeed76c4bf325ba7971115d696df0130f7cf0ac

Fresh CPU application checks. Actual isolated database, CPU retrieval, explicit mock/live paths and cancellation.

evidence/week08-enhancement/20260920/portable/app-attempt1.json

SHA256 db73f8c72410d724510b64beace18325972c9a5c92a3cbc16853d9092622584c

Final software verification. Current gate stages with immutable before/after source snapshot; software behavior scope.

evidence/week08-enhancement/20260920/software-gate-final-attempt2/software_gate.json

SHA256 ff8283ac8302aa5441412ddc49a57f664d376504a5ce8f82ba52709863eb0acd

Retained first aggregate verification. The old chat-input whitelist assertion failed; other stage results are retained beside the corrected verifier rerun.

evidence/week08-enhancement/20260920/software-gate-final/software_gate.json

SHA256 63a4000d62b624979f7f4cb5c9d19c5343f975978c6986e9da58960467cb86a1

Original live regression. All 110 scheduled actual HTTP cases; structural and expected-state checks.

evidence/week08-enhancement/20260920/regression/original110-attempt1.json

SHA256 9351050b94ba6305eb1277f09a0d747a85ff22f73f466fc4d564d2349e667277

Isolated failure checks. Ten remaining catalogue IDs mapped to 14 controlled assertions; separate from live requests.

evidence/week08-enhancement/20260920/regression/isolated-fault-mapping.json

SHA256 23c41b3ba0a81ee8e11038899708d22e30c19aa97bdccf3f783de15de4b97ca6

Dated purpose-specific cost reconciliation. Known provider usage at the dated CNY tariff, with missing usage and estimates identified.

evidence/week08-enhancement/20260920/costs-summary.json

SHA256 a7d58e1e1f84006d59902ad025efe8c9eebdf6ef8b45eb70e347c960f9cee90b

Blinded independent review materials. Actual exports for two reviewers; prepared forms do not constitute collected ratings.

evidence/week08-enhancement/20260920/human-materials.json

SHA256 ea79b669d5585d551ef17453a6db6c7620a5c7e48421d1c9560de519e4e8f90c

Actual paired highlight material load. 148 claims and 296 paired presentations loaded in the browser; text/Unicode checks only, zero timed responses.

evidence/week08-enhancement/20260920/human-highlight-load.json

SHA256 c087d011969305de6be5f3716b3c604b1c3b2cd2af40e43d3b8aafa61509bca2

Additive migration preservation. Measured aggregates of 33 existing tables before and after the additive schema change.

evidence/week08-enhancement/20260920/backend/main-migration-preservation.json

SHA256 ddb6ffbbc53310707e2dbccab344f8a357f8995e206708b6c07ffdb507287d33

Retained live lifecycle scope. Five actual requests, including the recorded memory-enabled context-limit failure.

evidence/week08-enhancement/20260920/backend/live-lifecycle-attempt1-scope.json

SHA256 0f6725fbc4ca90e5ffc028c99236e5aca72ec0b86414b72efaa43ab364af316d

Post-study task boundary correction. Separate HTTP task-resolution fix and verification after the frozen formal generation study.

evidence/week08-enhancement/20260920/task-boundary/final-verification.json

SHA256 c8ed064ff810d4232224e96ee9ba01f4ae5a2048de724cd2744af8ed03830d4f
