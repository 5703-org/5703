# Fixed evidence IDs: checker output and native acceptance

Date: 11 October 2026. Scope: CS30-1 learning assistant only.

## Result

Main now includes the explicit, default-off fixed original-text ID output policy. Its normal product B journey published a complete answer using two requests, with Send-to-complete DOM **11.0384 s, n=1**; refresh retained the body and five citation buttons, and Sources reopened. Teacher and checker both finished with `stop`; checker output was 1386 tokens within the unchanged 4096 cap. Actual known cost was **USD 0.0121762, UNKNOWN 0**. This establishes this fresh case's publication and complete output, not general scientific acceptance or a causal speedup.

Independent exposed-case AI review confirms source support for the three core requested topics and literal 3-PGA support, while retaining local selected-evidence gaps and an omitted glucose/six-carbon-product qualifier. Independent overall scientific qualification remains false. The published answer and online checker verdict were preserved, without a local override or silent correction.

The previous stage was closed before submitting a question: zero model POSTs, USD 0, UNKNOWN 0. Its financial receipt, API closure, allocation marker and original source freeze remain immutable. The separately authorized B stage02 validated that actual zero-use closure and created its own one-time claim. No allocation marker was reclaimed, rewritten or reopened.

## Problem and change

The saved 83 checker ended with `finish_reason=length`: 4092 output tokens against its configured 4096 limit. Its partial response was not saved, so the precise truncated field and verbosity as the sole cause are unknown. The saved packet contains 71 public source fragments in 9 evidence-chunk rows, 12 claims and 25 source units. Increasing the output cap or weakening the publication gate was not adopted.

The new explicit, default-off output policy carries the original judgments under compact field names. The checker selects a fixed original-text ID instead of reproducing a source quotation or computing character offsets. A local immutable catalogue maps IDs back to the original evidence, fragment and exact text. Short fragments use their complete original text; longer fragments use predetermined overlapping consecutive sentence blocks within the original 1200-character quote bound. A sentence too long to register remains in the complete input and has no selectable quote ID. No online summary, semantic trimming or invented text is added. Catalogue boundaries use punctuation and blank-line heuristics; they do not certify semantic completeness.

The reference vocabulary is finite. Canonical quotes outside the catalogue are rejected, never widened to a whole fragment or replaced by a nearby quote. Therefore exact round trips apply to representable catalogue selections, not every arbitrary canonical substring. The context fingerprint binds the output codec and catalogue so an old coordinate response cannot silently reuse the new context.

All claim and unit judgments, separate model-authored requirement coverage and sufficiency, negative findings, conditions, reasons, joint citation combinations and source identity remain. Reference validity proves provenance only; canonical schema validation and the original semantic, teaching and publication checks still decide whether an answer can be published. Default requests and old queued requests retain their prior behavior. For the explicit direct-answer lane, the optional redundant `short_answer` may be null while the complete requested, cited explanation remains in `answer_text`.

The existing claim-patch repair path already permits at most one local repair followed by a complete fresh check. This experiment has only two remaining physical POSTs, for teacher and checker, so it does not spend an additional repair call. No parallel checker batches or new repair framework were added. Independent review also found that contract-correction feedback is appended after the original JSON packet; the codec's final-message assumption required a narrow packet-location correction that preserves the feedback and rejects missing or ambiguous packets.

## Research and competing interface constraints

[VeriCite](https://arxiv.org/html/2510.11394v1) checks concatenated cited passages and separates initial verification, evidence enhancement and answer refinement. This change retains joint passage support; it does not implement VeriCite's additional NLI pipeline or claim its measured gains. [Q-CARE](https://arxiv.org/html/2608.11238v3) separately considers query coverage, claim verification and joint sufficiency. Required mechanisms and steps therefore remain checked even when a shorter answer would be easier to verify.

[CiteFix](https://arxiv.org/html/2504.15629v2) evaluates post-generation citation correction, including an LLM that returns reference numbers, and warns about per-factual-point overhead. Fixed IDs borrow the short reference selection interface; lexical or semantic similarity is not substituted for entailment, and no repeated per-claim online requests are introduced. [REVA](https://arxiv.org/html/2609.11209v1) uses offline generator attention and document-keyed scores. That attention history is unavailable in this black-box OpenRouter lane, so this is not a REVA implementation.

[Anthropic Citations](https://platform.claude.com/docs/en/build-with-claude/citations) binds returned citations to supplied document locations, but its native citations are incompatible with strict structured outputs. Native Citations was not enabled on the existing JSON-schema teacher lane. Local exact source binding remains within the current provider contract.

## Verification and measurements

The final Main revision passed **24 targeted tests in 1.43 s**, with four-file Ruff and format checks under Main's explicit configuration. Before adoption, the fixed-ID revision passed 18 controls (14 new and 4 migrated representation fixtures) and 8 selected integrations; the packet-feedback correction passed 3 new controls and 3 selected prepare integrations. Twelve new synthetic admission controls passed, with zero database, network, authentication or real-ledger reads. These overlapping cohorts are kept separate, not added into a unique total or treated as unseen actual-model scientific accuracy. The first feedback fixture failure is retained: its missing ordinary-textbook scope fields were corrected without weakening a production guard or semantic assertion.

Four files were CAS-adopted for this revision: the codec, four migrations in the existing pure fixture file, and two new test files. The six earlier pipeline integration files and original gates remained byte-identical. Independent static review bound all candidate and predecessor pins. The earlier coordinate candidate's first Main adoption passed 105 tests in 3.62 s; it describes that earlier version. The previous 4286-unit checkpoint is retained without another whole-suite run.

Existing same-packet full-input v2 reduced saved 83 user-message UTF-8 bytes from 50781 to 43952, a 13.447943% reduction, while decoding to the exact original canonical packet. This is a byte measurement, not provider-token or latency improvement. Any fixed-ID synthetic output-size comparison likewise remains a representation measurement until actual provider usage is observed.

The fixed-ID same-saved 83 compiled-object sizing exercise increased input from 101143 to 105256 UTF-8 bytes (+4113), while a synthetic quoted negative output fell from 7097 to 3891 bytes. The finite codebook has input overhead. These are structural bytes, not token estimates or measured quality gains.

| Actual B measurement | Result | Boundary |
| --- | ---: | --- |
| Complete DOM; cohort median/max | 11.0384 s / 11.0384 s | One valid page sample; n=1 |
| Startup preparation | 9.172417 s | Before API listener and Send; CPU model/cache prepared, query not encoded |
| Queue | 0.118201 s | Submission to worker start |
| Inclusive retrieval | 1.529037 s | Includes rerank and coverage supplement |
| Teacher / checker | 3.984 s / 4.329 s | Provider-reported latency; no correction or repair |
| Generation wall | 8.704972 s | Includes the two provider calls |
| Worker before commit | 10.617794 s | Inclusive worker timer |
| Teacher input/output tokens | 16729 /546 | Actual provider usage; finish `stop` |
| Checker input/output tokens | 22551 /1386 | Actual provider usage; finish `stop` |

Exact original ordered71 fragments and the question equal saved 83. The fresh draft has 5 claims/15 units and no optional short answer, versus saved 83's12 claims/25 units; output policy, input v2 and fresh generation therefore cannot be isolated as single causal factors. The complete typed judgment validated at revision0 with no inconsistencies or missing requirements; those are online model results, not independent scientific proof. The saved compiled payload object is available, but actual serialized wire-byte equality is unverified because public JSON storage reorders object keys.

Native81 remains the previous qualified full-page observation: 35.8717 s, n=1. Its older prompt, draft and cold preparation are different, so it is not a matched speedup control. Inclusive cold retrieval was 13.505904 s; teacher/checker/contract correction were 5.646/9.075/6.440 s. Parent and nested timers must not be added twice. A failed worker duration is not completed-answer page latency. This small-sample work makes no p95 or 5-10 s acceptance claim; B's 11.0384 s does not meet the 5-10 s target.

Previous82/83 remains ten closed requests/USD 0.0963751/UNKNOWN 0. B's two requests settled at USD 0.0019459 teacher plus USD 0.0102303 checker. The original global envelope is now closed at **12 requests/USD 0.1085513/UNKNOWN 0**, within USD 1; B stayed within its local two-request/USD 0.15 limit. No third call, format repair, transient retry or automatic resubmission occurred. Every old STOP, unknown protection and closed budget remains separate and unchanged.

The earlier matched [RAG69 cohort](20261011-rag-paired69-results.md) remains 36 requests/USD 0.0185022 with 12 valid answers per arm. E0/E1/HYBRID_R2_MINILM token F1 remains 0.4774556002/0.5420380174/0.5441463917; strict EM is 0/12 per arm and all-required-facts explicit is 7/12 per arm. These exposed DEV results are not human Gold, heldout superiority or proof that hybrid improves correctness. Its costs and adapter timings are not pooled with B native costs or full-page timings.

## Independent source review

The core chain has available source support: RuBisCO/CO2/RuBP and six-to-three-carbon fixation, ATP/NADPH conversion of 3-PGA to G3P, and net export versus RuBP regeneration. F058 explicitly names3-PGA. Net one exported G3P per three turns is distinct from gross per-turn production. However, the independent review retains these issues:

- Claim 1/U01 selects F053/F054, which introduce stages and reactants; the catalytic predicate is in F056, selected elsewhere in its parent claim. Parent-chunk support does not prove that particular unit's selected evidence.
- Claim 3's selected passages do not fully establish its per-turn/regeneration wording, and its carbohydrate reference is explicit in ev001/F001 while that claim cites only ev002. Evidence elsewhere in the packet cannot be silently transferred to the claim.
- The extra six-turn sentence omits the common-glucose/six-carbon-product scope that F001 supplies before F002. It needs that object qualifier.

No explicit negation reversal was found. Additional ATP-regeneration or light-reaction detail is recorded as depth beyond the three explicit user topics, not invented required work. Overall scientific qualification is false; core-topic coverage and product publication are retained as narrower findings. Any future repair must use the existing bounded local path and a complete fresh check on a new version; the current published answer is untouched.

## Remaining acceptance

API, exact worker, browser and owned Vite 84088 closed; ports 18028/15198 have no listener, and original PostgreSQL 15433 remains running. Five tracked old metadata groups and six protected prior-stage files remain unchanged. Recovery was read-only. Its first invocation stopped at argparse because `--stage-dir` was missing; the corrected invocation made no database writes or model requests. Its top-level `provider_posts=0` means recovery-generated requests, not the live run's two requests; physical counts and cost come from the settled financial ledger.

The current 12-request envelope is exhausted; no further online test was attempted. Local source-selection/scope defects, unseen actual-model quality, human Gold, heldout RAG acceptance, common-version clean installation, formal warm latency qualification, AC-44 and global project completion remain open. The canonical registries are unchanged. Original Git metadata permission denial is retained; no bypass, reset, push, upload, deployment or course submission occurred. Protected Week09 databases, original PostgreSQL, experiment inputs/results and previous deliverables remain preserved.

[Portable evidence and exact source/test/runtime pins](evidence/20261011-checker84-fixed-evidence/index.json) include the published answer, original 71-fragment input, complete typed judgment, source review, separate financial ledger and runtime closure. Next work is a targeted citation/scope correction with full rechecking and a small frozen unseen cohort when a new bounded request scope exists, followed by common-version free verification and installation acceptance; no existing numeric scope is reopened.
