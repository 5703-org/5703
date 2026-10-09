# Week 9 memory controls and practice tutoring continuity

The 1 October successor adds per-entry memory controls and an owned bridge from saved practice to chat tutoring. The [source receipt](../../evidence/week09-continuation/20261001/memory-tutor-focused-freeze.json) records 26 affected source files and the additive migration head `f8e94fb071c0`. This report describes the bounded increment; the final integrated software gate and installed official-source journey have separate results.

## Memory controls

`PATCH /me/memories/{id}/controls` accepts the current entry version, `paused`, and `match_policy`. A paused entry retains its content, source and revision history while new snapshots and summaries exclude it. Resuming restores applicability subject to expiry and the existing relevance and verification checks. Controls are owner-scoped and version-checked. An unchanged control request returns the same revision. A stale revision produces a conflict.

The new `rules_only` default declines semantic scope supplementation. The learner can explicitly choose `calibrated_semantic` for an entry. That permission still requires an enabled, calibrated global selector; it never enables a model by itself. Saved snapshots without the field retain their pinned interpretation. Explicit current-turn instructions continue to take priority, and a relevant biology preference continues to override a general profile setting.

Changing controls invalidates affected memory snapshots and private derivatives and fences earlier writer events. Content edits and later explicit source updates retain a pause. Deletion removes entry/revision bodies, clears applicability controls, suppresses earlier source extraction and retains the original chat messages. Cross-session updates to the same typed field and scope continue to revise one canonical entry.

The memory page exposes pause/resume and a semantic-subject-match checkbox. State changes appear after a successful server response; conflicts leave the saved state visible for reload.

## Practice-to-chat bridge

`POST /learning/practice/{item_id}/tutor` checks the published question, current authorized source and saved practice version, then creates or reuses an owned session and `LearningTask`. Its receipt includes the task version and exact source locator. The practice page prepares a source-scoped chat draft and keeps graded submissions on the practice page. Published chat answers offer a return link to the originating practice item.

The task records the learner-visible problem, conditions, options, current step, actual recent attempts for that step, displayed authored hints and any full explanation already explicitly requested. This projection contains no hidden option key, expected numeric value, private knowledge-point terms or unshown hints. Generation and final checking both receive the same practice projection. Complete previously shown hint text joins the cumulative disclosure input.

A submitted practice attempt or displayed authored help refreshes the linked task, increments its version and exposure epoch, and makes earlier queued chat work fail its publication check. The final check also revalidates the live practice owner, item revision, progress version, link and source. Model feedback remains attributable chat feedback. Recorded practice progress advances through an actual practice submission.

Cumulative disclosure in this increment covers recorded practice hints, an explicitly displayed complete explanation, chat text and controlled chat citation displays. Independent access to the textbook reader remains available. Earlier library page views are outside this disclosure record. Teaching experiments must record complete-source-reveal conditions and this observation boundary.

## Current verification

| Check | Current outcome | Evidence |
| --- | --- | --- |
| Memory rules, owner controls, cross-session update, pause, current instruction, expiry and erasure | 65 tests passed in a disposable migrated PostgreSQL database | [Memory log](../../evidence/week09-continuation/20261001/memory-controls-focused-attempt2.log) |
| Practice bridge, retained practice, original learning tasks, prompt transport and guarded migration inverse | 50 tests passed in disposable migrated PostgreSQL databases and focused unit tests | [Tutoring log](../../evidence/week09-continuation/20261001/practice-tutor-focused-attempt5.log) |
| Memory controls, practice navigation and retained chat UI | 79 frontend tests passed | [Frontend log](../../evidence/week09-continuation/20261001/memory-tutor-frontend.log) |
| TypeScript | `npx tsc --noEmit` passed with regenerated runtime contracts | Current focused command |
| Python lint and formatting | Ruff checks passed; 19 owned Python files formatted | Current focused commands |
| Python type scope | Mypy passed for the matching engine, tutoring module and two public contract modules | Current focused command |

The test counts overlap; they are separate focused suites. Authored test sources establish state, permission, privacy and transport behavior. Human ratings are zero. Installed official-source operation, real multi-turn guidance quality, preference application in live wording and learning outcomes require their own runtime and independent observations.

The first memory run retained host temporary-directory permission errors; a workspace temporary directory resolved that environment problem. The first practice run had one failure because its test called an unsupported document DELETE route. The corrected test exercises the actual POST revoke route. The [retained failure log](../../evidence/week09-continuation/20261001/practice-tutor-focused-attempt1.log) redacts only ephemeral test JWTs; the exact original log hash remains in the source receipt.

## Migration and next gate

`f7d83ea960bf` adds the conservative match-policy column without changing saved bodies. Its inverse refuses to discard paused/semantic-permission controls. `f8e94fb071c0` adds the nullable practice-task link without changing existing attempts, answers or sources. Its inverse refuses to discard a populated link. Real PostgreSQL migration tests verify preservation on refusal and the explicit empty-control/empty-link inverse paths.

The next gate overlays the frozen successor in the isolated installed environment, exercises official-source practice and memory through HTTP, then records full software checks and current package/report identities. Independent scoring remains a separate evidence gate.

## Installed official-source observation and retrieval successor

The [first installed receipt](../../evidence/week09-continuation/20261001/memory-tutor-official-runtime-attempt2.json) records the CPU stage at migration `f8e94fb071c0`, using the published 10,594-vector release. The selected source is *Concepts of Biology*, physical PDF page 132, Chapter 5 / 5.1 Overview of Photosynthesis. Official source, exact unit hash, executed module hashes and before/after corpus/vector fingerprints are included. The fingerprints remained identical.

The learner saved an explicit biology preference through the message API, used it in a new session's frozen question snapshot, paused and edited it, resumed it, changed semantic permission, and deleted it. Owner and stale-version denials were exercised. A new post-deletion question excluded the entry, derived revision bodies were erased and the original source message remained. The official-source explanation was delivered using the live model with two consumed calls and six citations. Its wording has no independent preference-effect score.

The same run transferred an actual incorrect practice attempt and displayed authored hint into the tutor task and cumulative disclosure context. A later actual correct practice submission completed the item; model feedback did not advance the recorded practice. Ordinary textbook reading remained available during practice and was explicitly opened after the recorded tutor response.

The literal request `Help me with the current practice step without giving the answer.` returned a zero-call `NO_EVIDENCE` refusal. The query preparer retained only the generic instruction, and the relevance/coverage stages treated words such as `help`, `practice` and `step` as textbook knowledge requirements. This result failed tutor answer delivery despite successful task transport. The failure receipt remains part of the evidence.

The [retrieval successor receipt](../../evidence/week09-continuation/20261001/practice-query-successor-freeze.json) freezes `owned_public_practice_query_v1` for new linked-practice requests. An independent preparation helper uses the authorized public problem, current step, conditions and concepts as the reference, while retaining the literal learner request and its instruction constraints. Explicit teaching instructions are distinguished from factual knowledge points. Substantive learner questions remain in the requirements. The original message, hidden grading-key boundary, saved-source/version checks, ordinary question preparation and old commands without this marker retain their existing behavior.

This successor passed 41 focused unit/PostgreSQL cases, including actual retrieval for the generic instruction and explicit per-entry semantic consent in the existing owned-source reread tests. Ruff check/format passed for five changed files; the new helper passed its scoped Mypy check. An additional explicit Mypy invocation on the whole answer service produced 177 errors outside the configured five-module typing gate; that expanded scope has no passing claim. The same literal official-source question was retained for the installed successor checks below.

The initial sandbox attempt stopped before HTTP because the protected stage administrator credential was inaccessible. The exact local runner subsequently received escalated execution approval. Raw requests, responses and private derivatives remain outside distributable evidence. Observed waits of 29.480 and 12.121 seconds occurred while the full automated gate was running; they are not controlled performance measurements. Human ratings remain zero.

The [same-input installed successor](../../evidence/week09-continuation/20261001/memory-tutor-official-runtime-attempt3.json) verifies execution/source hash parity and correct retrieval for that literal generic hint: seven candidates, six submitted passages and four live model calls. The final teaching check rejected the generated hint with `TUTOR_ACTION_REPEATS_DISCLOSED_ANSWER`, `scope_ok=false` and `cumulative_ok=false`. The draft and its displayed excerpts named the required energy source, then asked the learner to choose it. The first repair retained the supported factual sentences and continued to disclose the result. This failure remains unpublished and retained; full tutor answer delivery remains incomplete at this checkpoint. The second live memory explanation succeeded with two calls and six citations.

The [new service policy receipt](../../evidence/week09-continuation/20261001/practice-hint-policy-service-freeze.json) pins `practice_hint_repair_v4` for newly submitted owned practice hints. Ordinary requests and an explicitly requested full practice explanation continue to freeze `claim_patch_repair_v3`; previously saved commands retain their policy. Forty-two focused unit/PostgreSQL cases passed after correcting a new test's ordinary-task assumption and canceling its queued request before assertions. The generation-side successor strengthens current-result withholding and allows a supported factual sentence to be revised when its teaching disclosure fails, followed by the full final check. Its generation receipt and same-input installed result are separate gates.

The [separate runtime accounting](../../evidence/week09-continuation/20261001/memory-tutor-runtime-accounting-attempts2-3.json) reconciles eight request budgets with eight completed provider-usage rows. Four canceled requests and the original refusal consumed zero calls; the two memory explanations consumed four calls in total and the rejected tutor consumed four. Recorded totals are 66,424 input tokens, 5,778 output tokens and 27,264 cached input tokens. Applying the observed off-peak tariff gives an estimated USD 0.009422592. The [official pricing page](https://api-docs.deepseek.com/quick_start/pricing/) was rechecked for this calculation. Provider cost fields remain null and invoice reconciliation is pending. This scope is separate from the other development agent's 53-call budget.

## Same-input v4 observation and v5 candidate

The [fourth installed observation](../../evidence/week09-continuation/20261001/memory-tutor-official-runtime-attempt4.json) retains the same source, wrong practice submission, shown authored hint and literal student request. Execution parity, all state/permission/privacy assertions and the unchanged 10,594-vector fingerprint passed. The linked hint and the cross-session memory explanation each failed `SEMANTIC_CHECK_FAILED` after four calls. Their observed waits were 47.613 and 30.549 seconds while the integrated gate and fresh CPU installation were active.

The hint's repair boundary released the supported scientific sentences for a complete teaching repair. The model returned the same answer-disclosing wording and tutor question. The final checker rejected the next action as repetitive. The v4 execution reached the intended full-repair branch; this sample still failed delivery. Its final scope/cumulative flags also differed from its recorded reason, which remains available for checker calibration.

The memory deletion journey erased its private derivatives as specified. Retained operational metadata records twelve supported textbook claims, `INSUFFICIENT_CONTEXT_FULL_COVERAGE` and the `joint_recheck` failure stage. Exact draft adjudication is unavailable after deletion. Memory selection, cross-session snapshot use and control behavior have runtime evidence; wording quality and checker false-rejection rates remain independently unscored.

The [attempt-four accounting](../../evidence/week09-continuation/20261001/memory-tutor-runtime-accounting-attempt4.json) reconciles eight completed calls, 73,917 input tokens and 5,893 output tokens. The tariff estimate is USD 0.009053814. Attempts two through four therefore used sixteen calls with a combined estimate of USD 0.018476406; invoice reconciliation remains pending. Deleted memory derivative content is absent from this usage receipt.

The [v5 service freeze](../../evidence/week09-continuation/20261001/practice-hint-v5-service-freeze.json) pins `practice_hint_repair_v5` only for newly submitted linked practice hints. Forty-four focused unit/PostgreSQL tests passed, including execution of previously saved v3/v4 commands and unchanged ordinary/direct defaults. Ruff checks and formatting passed using `--no-cache` after the existing cache directory denied temporary-file creation. The installed successor below isolates the hint and adds no memory model call.

## Final installed hint observation

The [v5 installed receipt](../../evidence/week09-continuation/20261001/practice-tutor-official-runtime-attempt5.json) records successful live publication for the identical generic hint request after two calls. The response asks the learner to locate the textbook requirement sentence and compare it with the visible options. It leaves the option selection to the learner. The response contains zero factual citations; this turn supplies a learning action and a question. Independent usefulness, cumulative-disclosure quality and learning-gain labels remain pending.

All thirty-four executed-module hashes matched the frozen source. The task preserved the prior actual incorrect submission and shown authored hint. The model response left graded progress unchanged; a subsequent actual correct submission completed the saved practice and reused its task. Ordinary textbook reading remained available, and the official release and all 10,594 stored vectors retained their fingerprints. This single successful handoff supplies current installed-route evidence for the practice/chat integration. Earlier failed tutor and memory deliveries remain in their own receipts.

The [v5 accounting](../../evidence/week09-continuation/20261001/practice-tutor-runtime-accounting-attempt5.json) records 17,612 input tokens, 848 output tokens and an estimated USD 0.002247432 for two completed calls. The installed memory/practice observations through attempt five total eighteen calls, 157,953 input tokens, 12,519 output tokens and estimated USD 0.020723838. Provider invoice reconciliation remains pending. The final 23.514-second observed wait occurred during the integrated software gate; it supplies no controlled latency comparison. This practice-only successor issued zero memory model calls.
