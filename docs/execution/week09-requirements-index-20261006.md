# Week09 development and experiment requirements: source index

This is an index of requirements and their provenance, not a completion report. Week09 includes the original taskbook, dated carry-over goals and later integrated-learning-assistant scope. The eight owner allocations alone do not contain all development or experimental requirements.

## Authority and week numbering

Effective precedence is the latest explicit user instruction, the supplied v5 specification with the responsive refinement, L01-L09, compatible integration rules, then older assets. See [repository instructions](../../AGENTS.md), [decisions](../foundation/decisions.md), [effective requirements](../foundation/requirements.md) and [source inventory](../foundation/source_inventory.md). The original supplied `CODEX_MASTER_PROMPT_EN_v5.md` is inventoried in [source_files.json](source_files.json); its Appendix A contains the 108-task catalogue, Appendix B the acceptance register and Appendix D the reporting allocations. Its original bytes were verified against the recorded SHA256 during this index audit.

There are two different week views:

| View | Meaning | Source |
| --- | --- | --- |
| Week09 project reports and owner goals | Project week 9 / course week 11; eight owner allocations referencing 20 distinct tasks | [weekly_plan.md](weekly_plan.md), lines 487-579; original v5 master Appendix D, lines 2388-2470 |
| `course-week-09.md` | Course week 9 / project week 7; eight unique tasks in that primary reporting bucket | [course-week-09.md](../delivery/by_week/course-week-09.md), lines 1-17 and 123-130 |
| Expanded Week09 continuation | Cumulative product, engineering and research requirements recorded on 30 September, extending the earlier 26 September increment | [continuation protocol](week09-continuation-protocol-20260930.md), lines 3-17 |

The eight primary course-week-9 tasks are DAT-11, RET-07, RET-08, RET-09, RET-10, GEN-10, FE-11 and QA-09. They concern chunk/qrel compatibility, retrieval variants and ablations, matched generation controls, comparison UI and controlled findings. That list must not be substituted for the project-week-9 owner goals below. The generated course view explicitly adds no product requirement or acceptance decision. Weeks and owners are reporting metadata; they do not restrict execution eligibility or establish dates, completion or member execution.

## Original eight responsibility domains and project-week-9 goals

The following work and acceptance intent are present in the original v5 master and reproduced in the current weekly plan. Deliverable paths in the plan express intended artifacts, not proof that those artifacts exist.

| Accountable owner / domain | Task references | Required work and acceptance | Weekly-plan section |
| --- | --- | --- | --- |
| Xianshu Zhang / integration | INT-09, INT-07, CHAT-11 | Audit requirement-to-code coverage, obsolete mandatory-MCQ assumptions and blockers; prepare a release candidate. Retain all IDs, avoid cycles and fix or explicitly record critical defects. | Lines 487-495 |
| Hongle Yang / data and corpus | DAT-10, DAT-12 | Check assets/chunks/vectors and historical hashes in an isolated restore environment. Preserve provenance and referenced evidence; record quality limitations. | Lines 499-507 |
| Chengzhou Liu / retrieval | RET-06, RET-11 | Execute retrieval/embedding replacement drills and diagnose measured bottlenecks. Keep shared consumers compatible; use explicit migrations/new indexes for dimension changes. | Lines 511-519 |
| Sijin Lu / generation | GEN-06, GEN-11 | Regress empty/truncated responses, HTTP errors, duplicate JSON keys, budgets and live configuration. Separate legacy 39 tests from new HC results; reconcile aggregate attempts and distinguish mock/live. | Lines 523-531 |
| Pengyuan Xia / personalisation | PER-07, PER-09 | Review available paired ratings, misleading analogies, negation and formulas; report findings and limitations. Trace examples to run/profile/rater and leave unrated items unavailable. | Lines 535-543 |
| Zeping Liao / backend and persistence | BE-15, BE-16 | Clean install, legacy upgrade, worker restart, transaction faults, backup/restore and rollback. Commands must rerun; partial failure cannot publish success; restore targets remain isolated. | Lines 547-555 |
| Baiqing Huang / frontend | FE-06, FE-08, FE-12 | Browser regression for stop/retry/latest-answer revision, account switching, re-login and historical evidence. UI must agree with persistence, with functioning controls and authentic lifecycle states. | Lines 559-567 |
| Chong Zhang / evaluation and QA | QA-13, QA-11, QA-10, QA-12 | Run the 48 AC and 12 HC scenarios plus replacement/restore/performance checks. Record environment, commands, exits, failures and skips; unexecuted checks are not passes. | Lines 571-579 |

For each exact task definition and its acceptance IDs use [tasks.json](tasks.json), keyed by `task_id`. This index verified that the supplied v5 and current registries retain the same 108 IDs. Some task references are cross-references into another primary reporting bucket; count a task only once.

## Original acceptance and evaluation requirements

[acceptance.json](acceptance.json) contains 60 checks: AC-01 through AC-48 and HC-01 through HC-12. The additional twelve responsive checks are UI-01 through UI-12 in [responsive_spec.md](../foundation/responsive_spec.md), lines 31-42. These are separate namespaces; HC-01 through HC-12 are already included in the count of 60.

The effective product requirements are REQ-01 through REQ-28 in [requirements.md](../foundation/requirements.md), lines 54-81. They cover connected free-text multi-turn chat, context and profiles, authentic source processing/retrieval/citations, account and object ownership, durable publication/retry/restore, separate evaluation and responsive interactions. The later provider/account administration extensions are UPD-REQ-01/02, lines 82-83. Six original connected journeys are listed at lines 89-94.

The [evaluation plan](../foundation/evaluation_plan.md) preserves three separate suites:

- Authored multi-turn chat: at least twelve scenario families with 3-5 turns where appropriate, including pronouns, simplification, examples, comparison, topic changes, ambiguity, correction, missing evidence, long history and profile/re-login continuity.
- SciQ-derived stem-only open answers: E0 no retrieval versus E1 basic R0 dense RAG with matched non-retrieval settings and empty benchmark history/profile. Gold, support and distractors remain evaluator-only. EM/F1 apply to compact answers and preserve negation, signs, numbers and units; full explanations require separate review.
- SciQ MCQ diagnostics: seeded four-choice shuffling and separate selection accuracy. MCQ scores do not certify open-answer or conversational correctness.

Retrieval R1/BM25, R2/RRF and R3/reranking plus chunk/embedding/k ablations are explicitly named variants; E1 retains its basic dense meaning. Comparisons freeze one changed factor and compatible qrels. Missing qrels or zero IDCG are unavailable. C0/C1/C2 studies freeze question/evidence/base answer/model and compare paired outputs; they do not replace the product's one-pass profile application.

AC-19 requires immutable manifests, honest denominators and null missing ratings. AC-29 separates product personalisation from study outputs. AC-47 prohibits lexical proxies from masquerading as semantic correctness. QA-10 requires actual independent ratings for the original blinded profile study; PER-09 requires real sample counts and limits, without calling output ratings student learning gains. See the corresponding exact IDs in [tasks.json](tasks.json) and [acceptance.json](acceptance.json).

## Historical Week8 carry-over into Week09

These goals are dated authored report recommendations, not a newly discovered course rubric. The eight personal sources are under `docs/delivery/week08-memory-v2/members/<First_Last>/Week08_Report.md`, with matching DOCX files; [the Week8 README](../delivery/week08-memory-v2/README.md) links them.

| Owner | Historical Week9 carry-over | Personal-report heading line |
| --- | --- | ---: |
| Xianshu Zhang | Resolve cross-module failures; collect external reviews without rewriting the study; reproduce installation on another machine. | 61 |
| Hongle Yang | Review source boundaries against original pages; obtain actual source-sufficiency confirmation; version extraction without altering historical citations. | 52 |
| Chengzhou Liu | Analyze packing omissions/false relevance; extend independent support judgments without final-output tuning; measure devices/workloads separately from quality. | 52 |
| Sijin Lu | Provider/campus-network observations; compare independent review with checker acceptance/rejection; register prompt/provider successors separately. | 57 |
| Pengyuan Xia | Analyze stale reuse, scoped exceptions and instruction conflict; review observation provenance; register participant learning studies separately. | 54 |
| Zeping Liao | Investigate recovery without uncertain paid replay; verify derived-data erasure in defined scope; retain fingerprints in operational drills. | 51 |
| Baiqing Huang | Independent usability/accessibility on additional devices; clarify labels without hiding missing results; verify interrupted interactions. | 52 |
| Chong Zhang | Obtain missing oracle confirmation and independent reviews; analyze paired trajectories with full denominators/uncertainty; register further studies separately. | 61 |

The [overall Week8 report](../delivery/week08-memory-v2/Week08_Overall_Report.md), lines 388-394, explicitly calls for two genuine independent blinded reviews with separate adjudication, source-sufficiency confirmation before the A2 oracle arm, repairs for checking/mapping/teaching/memory failures, a separately registered judge successor/cross-provider comparison, another physical installation/device and separate learning measurements.

Later session steering on 4 October paused human review and directed continued assistant-executed development/review work. This subsequent instruction takes precedence for current execution; it is not attributed to the historical source. Human ratings and learning effects remain zero/null, and assistant observations cannot be relabelled as completed human or member reviews. The pause does not block independent engineering.

## Expanded eight product areas, fourteen domains and thirteen gates

The 30 September continuation is recorded as a later user brief in [week09-continuation-protocol-20260930.md](week09-continuation-protocol-20260930.md), line 3. [baseline.json](../../evidence/week09-continuation/20260930/baseline.json) records its source SHA256 `232c9ca1d9edfd0c4c8c07f503d61a9903b78c4713b1a6b1bfecfe0a42a30d39`. This index inspected those local records; it does not claim to have reopened the original external message.

The eight learner/operator areas are reader and scoped passage questions; goals/concept prerequisites; four-type practice; stepwise tutor; error book/revision; memory centre; notes/cited bookmarks; administration. Every area needs user-facing behavior, API, persistence, failures and permissions. See protocol line 7 and the eight connected journeys in [fourteen-area ledger](week09-current-fourteen-area-ledger-20261001.md), lines 128-142. These product areas differ from the eight responsibility domains above.

| Expanded domain | Required scope | Fourteen-area ledger row |
| --- | --- | ---: |
| 1. Supported textbook answers | Complete supported ordinary answers, selected passages, colloquial/multipart/follow-up cases; correctness, completeness and false-refusal review. | 90 |
| 2. Checker and repair | False blocks/releases, bounded defect-targeted repair, unaffected-content retention and exact final fresh checking. | 92 |
| 3. Evidence and citations | Separate relevance, context sufficiency and claim support; necessary points, conditions, negation, formulas/units and exact provenance. | 94 |
| 4. Continuous tutoring | Actual attempts/feedback/progress, useful multiround guidance and cumulative disclosure across all visible surfaces. | 96 |
| 5. Memory and controls | Attributable scope/precedence, revisions, pause/resume/deletion; true/false/missed selection and effects on later responses. | 98 |
| 6. Relationships/recommendations | Official source-pinned concept relations, qualified review, explicit administrative decisions and usefulness. | 100 |
| 7. Practice and feedback | Four question types, solvability, correct/incorrect/partial attempts, conditions, semantic feedback, private key isolation and safe pending assessment. | 102 |
| 8. Cards, notes and export | Linked reader/answer/note/review journey, source revocation/history, cited exports and objective transfer distinct from self-report. | 104 |
| 9. Administration | Diagnose/recover failed drafts and requests; observe providers, cache/workers, stage outcomes and usage/cost. | 106 |
| 10. Visual/large-PDF sources | Actual source/page/structure identity, tables/headers/reading order/formula/figure semantics, reviewed publication and downstream effect. | 108 |
| 11. Security and exceptions | Object/role isolation, hostile uploads, redirects/DNS, source/memory injection, bounded adaptive attacks and paired legitimate tasks. | 110 |
| 12. Installation/recovery/performance | Current isolated install, real retrieval, cancellation/reconnect, load, migration/backup/rollback; separate new-machine/Mac/physical-device observations. | 112 |
| 13. Research and scoring | Frozen concept-disjoint seven-family studies, calibrated evaluators, validated simulated students and separately attributable human/learning observations. | 114 |
| 14. Regression and delivery | Current unified gate, requirement-matched evidence, nine English reports with rendered QA, one complete runnable package and eight disjoint owner overlays. | 116 |

The same ledger's thirteen final gates are at lines 154-178: (1) eight-module frontend/backend/SQL; (2) official source identities; (3) four practice types/private keys; (4) object/role matrix; (5) provider redirect/IP/DNS; (6) payload/resource bounds; (7) retrieval/answer/hint safety; (8) CPU installation/retrieval/cancellation/recovery; (9) migration/backup/restore; (10) frozen terminal studies; (11) code/data/model identities; (12) updated specifications/plans/original ledgers; (13) package/eight owners/nine reports. Dated evidence in that ledger remains tied to its own source version; the requirements index does not refresh its old results.

## Week09 experiments and model-comparison scope

The earlier [26 September generation protocol](week09-generation-protocol-20260926.md) defines defect-specific checking/repair, pre-generation coverage, shared budgets, concept-separated development/pilot/reserved groups, tutoring factorial A/B/C/D, a separate frozen earlier-release reference and paired memory selection. Repaired text must receive a full fresh check; exact old executable policies and prior results remain immutable.

The later [30 September protocol](week09-continuation-protocol-20260930.md), lines 21-33, records seven study families. These are planning scales from the recorded brief, not performed samples or a statistical-power guarantee:

| Family | Recorded planning scale | Required comparisons/outcomes |
| --- | --- | --- |
| Textbook QA | About 480 reserved cases | Earlier release versus integrated candidate and compatible E0/E1; correctness, false refusal, sufficiency, conditions, citations and failures. |
| Joint tutoring | About 60 concept tasks with fixed/multiturn states | A/B/C/D plus earlier release; useful supported hints, current/cumulative limits, delivery/repair/calls/full latency. |
| Memory | About 240 continuing scenarios | Old/new selection; true/false/missed selection, conflicts/update/deletion and actual response effects. |
| Practice/feedback | About 160 questions with paired attempts | Four types/difficulties/correct and incorrect answers; solvability, keys, scores/conditions and supported feedback. |
| Visual extraction | About 120 official-source regions and related questions | Text versus versioned structure; location/structure, formulas, isolation and downstream QA. |
| Safety | About 500 fixed cases plus bounded adaptive budget | Injection, forged citations, key seeking, cross-owner access, hostile inputs/exhaustion and legitimate-task completion. |
| Performance/recovery | Fixed repeated load/restore scenarios | All/success/failure p50/p95, calls/tokens/resources, cancellation/isolation/restore/deployment and estimated cost. |

Before reserved execution freeze source, migrations, corpus/source/model roles and capabilities, prompts/policies/configurations, rubrics, sample manifests, dates and tariffs. Pilot results determine final sizes, gates and precision targets before the reserve is opened. Group paraphrases and related turns by concept. Independent judges use blinded order/common rubrics and calibration for order/length/style/injection; the online checker is not a reference label. Validate simulated students' visible-only information, consistency and responses before interpreting multiround outcomes.

Retain every scheduled terminal outcome. Report useful accurate supported hints over all planned requests, not only delivered responses. Use paired concept/task effects, grouped intervals and explicit repeats; retain B-A, C-A, D-A and D-B-C+A, with the earlier release separate. Keep all/success/failure latency and missing/invalid/disputed ratings separate. Record actual calls and token/cache counters for failures as well as successes; estimates are distinct from invoices. See protocol lines 37-39.

The original v5 GEN-10 and weekly-plan line 339 made a second live model optional. Later explicit scope expanded route/model comparison. [provider_matrix_v1/README.md](../../evaluation/provider_matrix_v1/README.md) and [manifest_template.json](../../evaluation/provider_matrix_v1/manifest_template.json) record all eight preset routes plus the explicit local protocol. The presets are OpenAI, Azure OpenAI, Anthropic, Gemini, Ollama, DeepSeek-compatible, custom-compatible and explicit mock. [The public configuration example](../../configs/model-file-input.example.json) also prepares eleven named custom vendor routes: xAI, Meta-compatible, Qwen, GLM, Kimi, MiniMax, Doubao, ERNIE, Tencent Hunyuan, iFlytek Spark and MiMo.

That reusable matrix contains twelve public synthetic development cases and staged capability/quality/review expansion. It is preparation, not the seven-family formal dataset or a live executor. Its full 3,404-transport ceiling is not a scheduled or completed study. Exact account-supported model identities/capabilities must be frozen for actual use; a configured route is not a distinct base model or an access/result claim. Deduplicate equivalent underlying models for model-quality comparisons, while retaining separate route/protocol compatibility results. Separate same-model review from independently executed model review in the underlying provenance. Later live scope and limits are separate phase decisions; old planning metadata does not establish execution.

## Preserved exclusions and delivery boundaries

L01-L09 simplify implementation while preserving functional acceptance: one modular application/local deployment, simple learner/admin ownership, durable database jobs, finite controls, small source/configuration records and tested essential operations. They replace enterprise obligations such as Kubernetes/Kafka, tenant/SSO platforms, distributed buses/accounting, audit warehouses, public-TLS automation and formal SLAs. See [decisions.md](../foundation/decisions.md), lines 15-23. Optional cross-session learning memory was later added; automatic mastery inference, arbitrary learner uploads, voice/multimodal input, open-web agents, full LMS and foundation-model training remain outside the recorded scope at [requirements.md](../foundation/requirements.md), line 98.

Software/mocks, actual provider/source execution, semantic review, physical-device observation and learning outcomes are different evidence. Human/physical observations remain unavailable until recorded; that does not suspend unrelated engineering. Named owners are accountable domains, not proof of member execution.

Expanded delivery requires the current complete runnable archive, eight disjoint cumulative owner overlays, one English overall report and eight matching personal DOCX reports, fresh rendered-page QA, source/resource parity and reconstruction. See continuation protocol line 43 and the earlier generation protocol's release gates. A source-review-only archive or historical same-host install cannot replace a current runnable package or prove a new machine's installation.

These are project-development and research sources. Generated week buckets and archived weekly reports do not establish current formal course dates, submission filenames, accepted formats, page limits, marking rubrics or assessment-specific AI rules. Those details require the current course assessment instructions. This index makes no claim that final LaTeX or final-report files are globally absent.
