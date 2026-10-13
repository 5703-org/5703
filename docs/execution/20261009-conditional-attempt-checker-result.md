# Conditional attempt verdict and saved-teacher checker regression

Actual execution: 2026-10-09. The missing `attempt_evaluation_ok` ordinary-question contract defect is repaired. A fresh Gemini checker now returns explicit `not_applicable`, and strict JSON plus the complete conditional Pydantic schema pass. Scientific/business validation still rejects this saved answer. This is a conditional-contract repair, not successful native publication, independent scientific acceptance, or project completion.

## Cause and exact scope

The earlier mixed native request was `interactive_chat` / `turn_role=user_question`, with no learner attempt, no attempt history, no pending tutor question and no proposed evaluation. The original full V5 schema and the normal JSON-object wire hint both required `attempt_evaluation_ok`; transport did not drop it. The saved Gemini output parsed successfully but omitted that field. Its failure remains in [the original mixed report](20261009-haiku-teacher-gemini-checker-native-result.md).

The original `ReliableCheckV5` and compact boolean contracts remain intact. Only a full V5, explicit ordinary question with no current or conflicting attempt metadata selects `OrdinaryQuestionCheckV5`. The field remains required on the wire. The server may normalize only its absence to the exact string `not_applicable`; an explicit false or invalid value is never rewritten. Auditing records `learner_evaluation_passed=null`, separating inapplicability from a successfully assessed learner answer.

Real learner attempts, unknown roles, non-null current attempt/evaluation/pending IDs and nonempty or untyped attempt history retain the strict boolean contract. All downstream gate consumers accept explicit inapplicability only for this server-bound attempt field. Scientific assertions, source conditions, quotes, requirement sufficiency and citations retain their existing checks. Independent compact-wire routes keep the original schema name and boolean contract; invalid configuration still produces the existing structured validation failure.

Eight runtime/prompt files and one authored unit-test file were adopted using exact baseline hashes, exclusive existing-file handles and original-byte backups. The exact mapping and test-only correction receipts are in the public evidence directory. No default model, release pointer, database, experimental input, Week09 archive or other project was changed.

## Free verification

The four focused unit files passed **198 tests**, with **0 failures / 0 skips**, in 1.58 seconds; affected Python files passed Ruff correctness checks. Tests cover ordinary missing-to-inapplicable success, explicit false rejection, actual attempt missing/false/inapplicable rejection, unknown/conflicting contexts, unchanged compact transport, missing scientific fields, unsupported/partial claims, citation defects and invented source quotes. They use authored data and isolated temporary files; no model POST or database access occurs. Test counts are not evidence of scientific model quality or a project completion percentage.

The first test iteration had 194 passes and four authored-fixture failures: three tests incorrectly passed an unsupported keyword to an existing fixture helper, and one expected the wrong existing error code. The test-only correction and original failure log are retained; no runtime implementation was changed to make those assertions pass.

The saved old checker response was replayed through the complete current `GenerationService` with the original saved teacher and retrieval, using zero model calls. Its omitted field normalized to `not_applicable`, with no learner assessment certified, while `CHECK_SUPPORT_WITHOUT_SOURCE` still rejected publication. This proves that resolving the unrelated applicability field does not bypass source checking.

## One fresh checker result

| Measurement | Actual value |
|---|---|
| Authorized physical-call limit | 1 checker POST; USD 0.03 maximum |
| Actual physical POSTs | 1 checker; 0 new teacher |
| Model / wire / output limit | `google/gemini-3.5-flash-lite` / JSON object / 4096 |
| Route | Google Vertex global only; low reasoning; no fallback |
| HTTP / finish | 200 / stop |
| Strict JSON / complete conditional Pydantic | PASS / PASS |
| Attempt verdict / normalization | `not_applicable` / unchanged |
| Learner evaluation passed | null |
| Scientific body gate | false |
| Full business validation | FAIL: `SEMANTIC_CHECK_FAILED` |
| Retained scientific issue codes | `CHECK_PROBLEM_QUOTE_MISMATCH`, `UNEXPECTED_CITATION_FOR_BASIS` |
| Input / output tokens | 10,606 / 1,123 |
| Checker adapter elapsed | 4,736 ms |
| Local replay elapsed | 5,146.255 ms |
| Known cost / new UNKNOWN | USD 0.0059893 / USD 0 |
| Unspent money / further physical slots | USD 0.0240107 / 0 |
| Database writes / native publication | 0 / not performed |

The unchanged 1,625-byte Haiku teacher has SHA256 `f843ea4e3ef7aea098eb327c85fe9da81d64f2fe2519c81b342375d00967a0ae`. The original 20 retrieval evidence records and source map were reused, with hashes recorded in both replay receipts. Teacher messages and teacher schema matched the saved request exactly. The new conditional checker schema has SHA256 `f259fd47e0156f8d526996b7ce1fddb71d246bec8cb6d79f789dfa898d6bc0e0`; the full old schema and all other required fields/definitions remain covered by free regressions.

The test used normal approved credential/database consumers in memory and an explicitly read-only source reader. Raw teacher/checker bodies, credentials and DSNs were not exported. The create-only start marker precedes physical submission, and no retry, teacher regeneration, database rebuild, browser question or expanded guard was performed. The request budget contains two logical adapter invocations: one cached teacher plus one actual checker. All new cost is known; the old USD 0.09 UNKNOWN protection and historical STOPs remain unchanged. Remaining money does not authorize another physical request.

## Residual acceptance limits

The earlier 14,296.4 ms browser failure-detection result remains a failure-detection measurement. This local 4,736 ms checker duration is not full-answer DOM latency, TTFT, warm p95, a causal speedup or a unified-condition RAG quality comparison. No new browser request or atomic publication was attempted; the original failed native job remains failed. HTTP 200 and schema PASS do not establish business PASS.

Next work must address genuine factual-basis/quote/citation assessments under the unchanged source rules before a separately scoped native browser question can prove full-answer publication. Do not relabel these negative findings, change the saved teacher, or certify false gates. Reliable quality pools, independent source/human assessments, repeated complete-answer latency, same-worker reuse and new-device validation remain open. Canonical counts remain 108 tasks (66 REAL / 31 MOCK / 9 unverified / 2 external), 60 checks (33 REAL / 26 MOCK / 1 unverified), and Current53 (5 verified / 38 pending / 8 incomplete / 2 external). `project_complete=false`.

[Exact public evidence index](evidence/20261009-conditional-attempt-checker01/index.json). The Week10 implementation plan and its current status mapping are separate prospective documents; planned work is not recorded as completed acceptance.

## Offline factual-basis diagnosis and evidence limit

The actual saved question and `current_problem` are identical: "How do light-dependent reactions provide the energy carriers used by the Calvin cycle?" The saved Haiku output has response text, short answer and citations, but no `claims`, `basis`, `fact_type` or `problem_quote` classification. The factual-basis choice is made by the checker. A teacher classification defect therefore cannot be inferred from this run.

The earlier saved Gemini response selected `textbook` for all seven assertions. Its known uncited summary is `claim_1ad094406c5a0d4221904d72_1`, in `answer_text` [0,144): "The light-dependent reactions convert light energy into chemical energy stored in energy carrier molecules, which then move to the Calvin cycle." The old checker marked it supported with an empty citation-assessment list. Its `problem_quote` field was absent, not an original literal null. The other six old assertion spans have actual citation bindings, recorded in the diagnosis, and those bindings must remain protected.

For the fresh checker, specific failing assertion IDs, checker-selected basis values and original `problem_quote` strings are **UNKNOWN**: the local replay deliberately exported raw-output hashes and safe gate/error summaries, then exited without retaining those precise judgment entries. The 3,806-byte fresh output has SHA256 `b6365862aed25ef2df1f7ccb0c0f24a74cf24cc73c1e3f4d643c7187ecd9b537`. The old assertion table is not substituted for its missing fresh entries, and two error codes do not establish exactly two failed assertions.

`generation/checked.py:2390-2404` emits `CHECK_PROBLEM_QUOTE_MISMATCH` only in the checker-selected `problem_input` branch. It checks a nonempty exact substring of question/current_problem, numeric-given `given_matches` consistency, and the absence of fragment IDs or the draft's actual evidence IDs. Consequently the code can arise from an incompatible factual basis/citation binding even when a quote exactly matches the question; it is not unique evidence of normalization damage. `generation/reliability_v4.py:228-249` permits actual citation assessments for `textbook` or `derived_calculation` and emits `UNEXPECTED_CITATION_FOR_BASIS` when other selected bases retain actual citation bindings. The complete-claim semantic requirement remains in the independent checker prompt. Pure procedural or problem-input classifications must not hide a scientific assertion.

The available codes therefore prove that at least one fresh `problem_input` assessment failed a strict problem-given check. They do not identify its exact assertion or distinguish all failing conjuncts. Identical saved question/current_problem and the old textbook classifications provide no positive evidence that question normalization caused the fresh failure. An exact fresh taxonomy error remains unconfirmed without its judgment entries. The old uncited scientific summary is independently reproducible and remains a real source-binding defect.

The minimal next step is to retain structured per-assertion failure diagnostics (ID, immutable span, selected basis, original quote, exact quote positions and actual citation IDs) before any separately authorized unchanged-draft checker recheck. Then decide whether only checker classification needs correction or whether the uncited summary needs a narrowly scoped, source-verified repair. Reuse the existing unchanged-draft and protected-span repair mechanisms; preserve correctly cited scientific paragraphs. Never automatically relabel problem input, drop needed scientific citations, invent a quote/source or regenerate the whole teacher to conceal a negative result. The current physical-call slot is consumed; no additional POST belongs to this run.

The [offline factual-basis dossier](evidence/20261009-conditional-attempt-checker01/ACTUAL_SAVED_FACT_BASIS_DIAGNOSIS01.json) records seven actual old assertion IDs, original spans/bindings, exact rule locations and the fresh-data limitation. This diagnosis maps to W10-03, which remains in progress.
