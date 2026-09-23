# Week 8 enhancement protocol

Protocol identifier: `w8-enhancement-v1`. Frozen before enhancement implementation and before new live outputs. The exact user brief is retained privately outside distribution; its hash is recorded with this protocol. This protocol governs the three integrated modules and their separate evaluations. Amendments receive new dated identifiers, reasons and hashes; original schedules and outcomes remain preserved.

## Product and research questions

The product continues to answer ordinary textbook questions fully by default. `answer_mode=textbook/general_knowledge` controls source provenance. Independent `teaching_mode=direct/hint` controls requested help. Hint requests persist within one problem, explicit complete explanations take effect immediately, and new topics or new problems reset the task. Biology and chemistry are the primary experiment subjects. The other two textbooks retain ordinary question answering. All user-facing text is English.

The primary research question is whether joint control of answer content and source disclosure under a persistent teaching task increases valid hints compared with a strong body-checking condition. Citation selection and learning memory have separate experiments. A faster human verification time or improved learning outcome requires actual human measurements and will not be inferred from software or model checks.

## Preserved baseline

`evidence/week08-enhancement/20260920/baseline.json` binds 365 executable/configuration files and 495 preserved source/document files to a source archive. They match all 365 hashes from the final 16 September gate. The dated 16 September full package and all its evidence remain preserved. Current execution is recorded separately. The four-book corpus, learned vectors, original processing versions, accounts, historical answers and source references are retained. New source fragments map to exact cleaned SourceUnit characters with their processing/version/hash identity; this does not assert PDF glyph coordinates.

The first implementation and judging model is the configured real DeepSeek model. Record its immutable public configuration, provider-reported identity when available, purpose, prompt/rubric hash and timestamp. Other provider adapters remain available. Do not relabel an alias as a pinned upstream checkpoint. Corpus and source identities are independently read and frozen before migration or experiment execution. Initial Docker startup/connectivity problems remain operational evidence.

## Data and development separation

Use twelve development tasks: two subjects by three task types by two tasks. The task types are concept comparison, process reasoning and simple textbook calculations. Each task has three sequential hint requests followed by separate explicit full-answer/source transitions for product checks. Development runs may tune prompts and policies, with all failed attempts retained.

After development, author and freeze sixty formal tasks, ten per subject/type cell. Group related concepts and numerical variants so development and formal tasks do not share the same specific problem family. Formal tasks are developer-authored evaluation material, not an independently sampled benchmark. Freeze task IDs, user turns, conditions, source anchors, allowed-help rubric and critical answers before any formal output. Keep evaluator references and allowed-help labels outside generation inputs. The online teaching controller derives task-specific help constraints from the actual question and exposed state; it cannot read private annotations.

The main schedule is sixty tasks by three hint turns by five conditions: 900 planned hint requests. Use all planned requests as denominators, including errors, timeouts, refusals and missing responses. No success-only replacement or post-result task removal. If a systemic execution interruption occurs, preserve terminal results and resume only unexecuted items; ambiguous paid calls require explicit durable outcome handling. Formal tuning requires a new explicitly labelled experiment, not overwriting this run.

## Main teaching conditions

| Condition | Intervention |
| --- | --- |
| T0 | Explicit, task-specific hint instructions and conventional source display; no online content check |
| T1 | T0 plus a strong body and short-answer check and bounded repair; clear teaching constraints and the same maximum request budget |
| T2 | Teaching-state control of body, short answer, suggestions, source titles, local passages, previews and cumulative delivered/rendered/expanded information |
| T3 | T2 with cumulative information checking disabled |
| T4 | T2 with evidence disclosure control disabled; body and cumulative checks retained |

Primary contrast: T2 minus T1. Mechanism contrasts: T2 minus T3 and T2 minus T4. T0 is descriptive context. Freeze condition policy objects separately from model identity. Each matched task starts with identical user information, immutable memory/profile snapshot and initial real CPU retrieval candidates. Subsequent generation uses its condition's actually delivered prior turns. Every condition records exposure events, including ablations; only the declared controller components differ. Ordinary citation opening must use the same product projection policy as HTTP answer/history/source responses. A UI comparison keeps answer and evidence fixed and changes only paragraph versus precise-highlight presentation.

## Citation and memory comparisons

Citation comparison: paragraph citations, post-generation span association, and locally preselected spans followed by generation. Use the sixty frozen task questions with direct answers, the same initial retrieved candidates and the 3,000-token evidence cap: 180 planned answers. Record exact source-unit positions/hashes, claim links, unsupported/coarse mappings, selected text length, citation completeness and model-assessed support. Preselection is a bounded reference inspired by Attribute First, then Generate; it is not claimed as an exact reproduction of its original experimental system.

Highlight interface comparison: export paired, blinded whole-passage and highlighted presentations of the same answer/evidence, with an interactive timing recorder and independent correctness questions. Automated checks verify content identity, escaped text nodes, keyboard operation and source permissions. Actual reviewer timing and correctness remain blank until collected.

Memory comparison: current saved profile plus session summary, cross-session rolling summary, and structured entries with update rules. Freeze scripted multi-session cases before execution, covering durable preferences, goals, one-turn requests, correction, duplicate statements, expiry, deletion, global-off, turn-profile-off and ownership isolation. The same utterances are supplied to all three conditions. Evaluate extraction/update correctness, appropriate use and stale/deleted use separately. Ground truth is evaluator-private. Memory affects presentation and task continuity, never source-mode selection.

Memory is opt-in. Auto-save only explicit durable preferences and goals. Observed difficulty stays within the current task until the user confirms it. Precedence is current instruction, explicit saved settings, relevant active memory, then confirmed observation. Versioned edits, expiry, content-free suppression records and revocation prevent stale jobs from recreating deleted entries. Delete purges memory-derived summaries, snapshots and background payloads; chat history has its own deletion operation. Undo of a save and deletion must have explicit, coherent semantics without retaining a deleted body in a hidden tombstone.

## Budgets and publication

Existing per-request limits remain four external model calls and 180 seconds. Standard checked flow is generate once and batch-check once; a repair requires a further repair and recheck. Counting, transient retries, format repair, planning and semantic calls all consume the same request budget. No repaired response is published without the condition's required final check. Drafts stay private. Generation/checking/repair purposes and their independent frozen configurations are recorded. Memory extraction uses a separate bounded durable job, initially at most two calls and 90 seconds, with cancellation and revision fencing. Offline automatic judging uses a separate bounded budget and separate accounting.

Record generated drafts, delivered projections, DOM-render acknowledgements and explicit full-source/full-explanation requests as distinct events. DOM events establish display, not reading or understanding. Joint controls apply to every answer, history, citation and source entry point. Full-source access follows a deliberate recorded request and rechecks current source visibility. Historical answers retain their original versions and compatible behavior.

## Automatic and human evaluation

Program checks cover exact text/offset/hash relationships, ownership, source revocation, memory versions and deletion, task/mode transitions, budgets, cancellation, timeout and immutable historical records. Model judging is a separate fixed rubric with per-item reasons: textbook support, concrete useful help, permitted help scope, factual correctness, citation completeness and memory misuse. The judge sees evaluator references; generation never does. Start with DeepSeek and disclose shared-model judging bias. A second model can later examine random and disagreement samples as a separately dated analysis.

Primary metric is valid hint requests divided by all planned hint requests. A valid hint must simultaneously be textbook-supported, provide concrete useful help and respect the allowed help scope. Failed generation or judging remains in the denominator; report judging missingness and both conservative pass counts and evaluable-case descriptions. Also report excessive-help rate, vague-hint rate, factual errors, support/completeness, normal-answer correctness/coverage/false refusal, memory use/misuse, calls, tokens, latency and execution failures.

Bootstrap paired differences by task, preserving all three correlated turns, with a fixed seed and 10,000 resamples. Report 95% intervals, counts and subject/type strata. Multiple secondary contrasts are descriptive and identified as such. Separate program results, model-assisted judgments and independent human ratings in all tables. Do not call schema/state/hash checks scientific correctness.

Human materials hide condition names, randomize stable item IDs/orders and provide separate forms for two reviewers. The codebook defines supported/useful/within-scope and citation/memory scores with examples. Imports require reviewer identity, item/rubric version, valid score ranges and duplicate/conflict checks. Preserve original independent ratings, calculate agreement and disagreement, and import adjudication as a separate record. Compare human and automatic judgments on paired rated items only. Blank forms are delivered; human counts remain zero until the group submits actual scores.

## Cost, regression and delivery

Record provider attempts, consumed reservations, reported prompt/completion/cache tokens and elapsed time by generation, online check, repair, memory and offline judging. Estimate currency cost only from a dated official price schedule matched to the actual provider/model and available usage fields. Distinguish estimates from bills; missing tariff/usage produces explicit unavailable monetary totals, never zero cost. Preserve all failure cases and their stage.

Run the existing 120-case reliability catalogue as regression material plus software checks, actual CPU/source identity validation, general/direct modes, provider adapters, privacy and source-revocation tests. Complete desktop/narrow-browser interaction checks. Physical-device and learning-gain claims require their own evidence.

Update PRD, SPEC, PLANS, architecture, data model, API, answering flow, operations and original 108-task/60-check/12-responsive ledgers with scoped evidence and history retained. Deliver one complete runnable package, eight non-overlapping member change packages, eight English DOCX reports and an English overall report covering methods, automatic results, costs, failures and human-review workflow. Preserve the earlier Week 8 release and keep secrets/private learner history outside distributions.

## Research references

- Slobodkin et al., Attribute First, then Generate, ACL 2024: https://aclanthology.org/2024.acl-long.182/ . Motivates source selection before generation and concise attribution.
- Chhikara et al., Mem0, arXiv 2504.19413v1: https://arxiv.org/abs/2504.19413 . Motivates extraction, consolidation and retrieval of persistent information. This project adds its own explicit-consent and deletion rules.
- Gao et al., ALCE, EMNLP 2023: https://aclanthology.org/2023.emnlp-main.398/ . Motivates separate correctness and citation-quality evaluation.

Primary pages checked on 20 September 2026. Their published results are not measurements of this project.
