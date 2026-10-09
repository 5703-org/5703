# Week 09 Real Answer Delivery and Repair Diagnosis

Recorded on 1 October 2026, Australia/Sydney. The measured calls occurred on 30 September 2026, 17:58–18:50 UTC. This report covers isolated development precursors and repeated exposed questions. The integrated release requires its own source snapshot and runtime verification.

## Runtime and data boundary

The installed Windows CPU stage used PostgreSQL/pgvector at port 16547, API port 18847 and the existing published four-book corpus: release `4f11bd70-a486-4d16-b216-78cfe499530a`, with 10,594 real E5 vectors. The main database, original material, saved answers and historical citations were preserved. Query encoding, retrieval and reranking used the existing CPU path. Source passage identity, original text hash, contained excerpt, excerpt hash and official OpenStax URL were verified for every delivered citation.

Managed answer and checker configurations were tested and activated in the isolated stage. The locally configured key was transferred to local encrypted managed storage; no plaintext key appears in the public report or receipts. Both roles used the configured and provider-returned alias `deepseek-flash`, temperature 0, non-thinking mode, JSON-object output, a 32,768-token configured window and the existing four-call request allowance. The answer output allowance was 1,024 tokens and the checker allowance was at least 4,096. Other provider adapters remain available.

The pinned local counting tokenizer was `deepseek-ai/DeepSeek-V4-Flash-0731`, revision `7872f01b1d1fe23eabc4c98b48bffcef5a386062`. This identifies the installed local counter. The current official mapping for the API alias is DeepSeek-V4.1-Flash; exact compatibility of this older local tokenizer with that cloud model has not been established. Provider-reported usage is the accounting source. The provider's mutable alias does not establish an immutable cloud model revision.

The three previously blocked historical internal draft packets were excluded from every external call in this work. Fresh official textbook questions and retrieved passages were used. Independent human ratings and formal independent AI semantic ratings both remain zero.

## Initial real runtime results

| Fresh case | Terminal result | Citations | Provider calls | End-to-end seconds |
| --- | --- | ---: | ---: | ---: |
| Define photosynthesis in the selected textbook passage | Answer delivered | 3 | 2 | 23.246 |
| Explain this paragraph, with the same selected passage | Answer delivered | 1 | 2 | 15.698 |
| Spoken question about a plant turning sunlight into usable food | `NO_EVIDENCE` refusal | 0 | 1 | 1.593 |
| Compare DNA/RNA sugars, bases, typical structure and roles | Answer delivered after repair | 9 | 4 | 21.151 |
| What light-dependent reactions contribute to the Calvin cycle | Answer delivered | 5 | 2 | 10.331 |
| Follow-up about carbon dioxide and its use | Answer delivered | 3 | 2 | 8.836 |

The selected definition and paragraph explanation used Concepts of Biology, Chapter 5 / Section 5.1, PDF physical page 131. Their source unit was `2eedd51e164140d374506b6c9ff7d77b405e`. Developer source reading found the central light-to-chemical-energy/carbohydrate points in the displayed official material. This is an AI development assessment rather than a formal correctness label.

The spoken question exposed a preprocessing error: the terminal object-relative clause “food it can use” was treated as a missing conversational referent. The system therefore discarded a complete current-turn science question before useful retrieval. A narrow versioned repair now recognizes a single explicit current subject and preserves the question verbatim. Historical V12 requests retain their earlier branch. Ambiguous competing subjects, bare pronouns, negation, quantities and conditions retain dedicated regression checks.

The DNA/RNA answer covered the four requested dimensions. The initial repair kept its body exactly and added the summary's missing citation markers. Follow-up delivery used the original conversation topic and performed additional retrieval. One ATP-related follow-up repeated the textbook's wording “terminal phosphate atom”; a subject expert should review that wording against the expected phosphate-group terminology. The original source was preserved.

## Real failure diagnosis and successor behavior

The V13 precursor retrieved actual sources for the previously rejected spoken question. It also tested ordinary questions from the four books and a scope-negative question.

| Case | V13 precursor result | Latest observed successor result |
| --- | --- | --- |
| Spoken photosynthesis question | Full repair changed an already approved sentence; `REPAIR_CHANGED_APPROVED_CONTENT`, 29.930 s / 3 calls | Answer delivered, 34.952 s / 4 calls / 4 citations; checker classified the selected context as partial |
| Ordinary photosynthesis definition | Answer, 9.857 s / 2 calls | Preserved as prior development evidence |
| Sea-star water vascular movement and gripping | Checker aggregate contradiction consumed a correction; `SEMANTIC_CHECK_FAILED`, 15.521 s / 3 calls | Answer delivered, 19.112 s / 4 calls / 3 citations; checker classified coverage as full |
| Buffer resisting added acid | Answer, 8.460 s / 2 calls | Preserved as prior development evidence |
| Kidney regulation of blood volume and pressure | Full repair reordered approved content; `REPAIR_CHANGED_APPROVED_CONTENT`, 14.996 s / 3 calls | Answer delivered, 23.217 s / 4 calls / 9 citations |
| Kubernetes configuration | Scope refusal, 1.115 s / 0 calls | Preserved as scope-negative evidence |

All three original scope failures were repeated with their original questions. The first typed-patch repeat still failed the spoken and sea-star cases, while the kidney case succeeded. Its complete receipt remains available. The spoken recheck returned an illegal `citations=[]` field on an `evidence_limitation` variant. The sea-star checker assigned partial factual statuses to uncited opening and closing summaries while returning inconsistent aggregate completeness. A schema correction then left insufficient calls for both answer repair and final checking.

The new policy `claim_patch_repair_v3` accepts edits to named defective original claim spans. The server applies those edits to the original body and summary, retaining every approved text span, citation marker and relative order. It rejects overlapping spans, unknown or duplicate claim IDs, changes to protected claims and unknown evidence IDs. Newly appended content receives a complete final check. Actual source identity, semantic support, question requirements and cumulative teaching disclosure checks remain active. Historical `cause_specific_repair_v2` behavior remains available for frozen old requests.

Under the new policy, the actual checked-generation prompt receives local citation reminders, and the checker receives the existing strict variant examples plus explicit separation of source sufficiency and draft citation defects. These additions are pinned to the new policy. The original single schema-correction allowance and four-call budget are unchanged. No checker verdict is rewritten and no redundant-field normalization was enabled.

The last two repeats delivered an answer through the complete final checker. The sea-star explanation's water entry, ring/radial canals, pressure/volume-driven extension, ampullae and gripping points were found in the actual cited complete source blocks during developer source reading. Its cited books were Biology 2e and Concepts of Biology.

## Remaining semantic defect and independent review

The latest spoken answer contains a useful supported explanation and an explicit selected-source limitation about carbon dioxide/water inputs. Its selected material supports leaves/mesophyll, light-to-chemical energy, carbohydrate production, plants producing their own food and photosynthates usually being sugars such as sucrose. It does not provide the complete light-reaction/Calvin-cycle input mechanism for that question.

A developer reread identified a possible local support defect that the online checker accepted: the concluding synthesis says the plant can “use or store as sucrose and other photosynthates.” The actual adjacent excerpt distinguishes stored starch in seeds/bulbs, conversion to sucrose, and photosynthates usually taking the form of sugars. That wording requires independent assessment of its exact entailment and citation binding. This case is retained as a suspected false acceptance. Successful publication alone cannot close the correctly supported complete-answer requirement.

One arm-blind local review packet was prepared for this fresh exposed answer, with two separate blank reviewer forms and the existing rating-import contract. Both blank imports remained unscored. The packet includes the actual visible answer, short answer and cited official excerpts, and hides the model/intervention and online verdict. Coordinator-only provenance retains the development observation. It excludes all three blocked historical packets and was never submitted to an external evaluator. The case is a development calibration sample, outside the formal heldout estimate.

Private review directory: `E:/5703/week09-private-db/real-answer-actual-binding-human-review-v1-20261001`. Public preparation receipt: [review preparation](../../evidence/week09-continuation/20261001/real-answer-human-review-preparation-20261001.json).

## Prompt probe and timing interpretation

The one-question DNA/RNA before/after probe used the same source IDs, model roles and budgets. Both runs delivered with three calls and no answer repair. The edited `chat_v1.txt` prompt was superseded by `checked_generation_v5.txt` on this checked path, so that probe's edit was unused. It provides no treatment-effect evidence. The actual generation-chain reminder was added later under the new claim-patch policy. Both probe receipts remain available. The after-run included cold retrieval/model startup and had longer end-to-end time, so its latency cannot establish an improvement.

Across all 19 question executions, including repeated exposed questions, 12 runs delivered a cited answer, five failed before publication and two returned a refusal. These counts describe runtime outcomes; they are not answer accuracy or a formal success estimate. One refusal was the initial erroneous spoken-question refusal; the other was the scope-negative Kubernetes question.

| Runtime population | Runs | Median seconds | Empirical p95 seconds |
| --- | ---: | ---: | ---: |
| All question executions | 19 | 15.698 | 35.575 |
| Delivered cited answers | 12 | 17.405 | 37.754 |
| Failed publications | 5 | 16.525 | 32.039 |
| Refusals | 2 | 1.354 | 1.569 |

The p95 uses linear interpolation at rank `0.95 × (n−1)`. These mixed cold/warm development timings include different questions, repair routes and provider variation. They are insufficient for a release performance claim. Generation/checker per-call latency and stage timing are retained in the individual receipts, including failures.

## Recorded usage and estimated cost

There were 53 completed provider calls: 51 question-processing calls and two managed-role probes. Provider usage totals were 504,828 input tokens, 52,850 output tokens and 557,678 total tokens. Input cache hits were 233,344 tokens and misses were 271,484 tokens. Counts include failed and corrective calls.

The [official DeepSeek pricing page](https://api-docs.deepseek.com/quick_start/pricing/) was verified during execution. It explicitly maps `deepseek-flash` to DeepSeek-V4.1-Flash. Off-peak prices observed were USD 0.003 per million cache-hit input tokens, 0.15 per million cache-miss input tokens and 0.60 per million output tokens. All listed run intervals fell outside both peak UTC windows.

The estimate for calls with the returned alias recorded is USD **0.072599334**. The two probes add a conditional configured-alias estimate of **0.000533298**, giving **0.073132632** for this diagnostic work. Probe receipts recorded their configured alias rather than the raw returned model ID. The provider returned no billed-cost field. These are tariff estimates; invoices were not reconciled. Other agents' calls and provider adjustments are excluded. [Accounting receipt](../../evidence/week09-continuation/20261001/real-answer-development-accounting-20261001.json) and [tariff observation](../../evidence/week09-continuation/20261001/deepseek-official-price-observation-20261001.json) preserve the arithmetic inputs and model-identity boundary.

## Verification and evidence

The installed F8 stage also completed an owner-isolated note/review workflow without an answer-model call: create and edit a note from an actual saved official-source answer, reject a stale edit version, export actual citation-bearing Markdown and DOCX, create a review card, read its due queue, record two explicit self-reports and reschedule it. The DOCX passed ZIP/OOXML structural checks; its visual layout was not independently reviewed in this run. Self-reports were scripted operation checks and provide no learning-outcome evidence. Source-release and corpus fingerprints stayed unchanged. An earlier runner assertion expected a saved-answer state named `succeeded`; the actual product state was `answered`. That failed runner receipt was retained before the corrected workflow passed eleven steps. [Installed workflow receipt](../../evidence/week09-continuation/20261001/installed-note-review-flow-v2-20261001-sanitized.json). Source withdrawal was checked in disposable fixtures, without revoking the official corpus used by other runs.

The same installed workflow checked the new administrator-only local draft-review projection and anonymous denial. Fresh development drafts stayed local; none was sent to an independent external evaluator. Allowlisted draft inspection is an operational check and does not assign quality scores.

An installed linked-practice hint exposed a distinct teaching defect: source-supported sentences supplied the requested one-choice answer, then the tutor asked the learner to repeat that disclosed result. The first checker rejected its next action; the local repair retained those scientifically supported sentences and the old tutor-question metadata. The final scope and cumulative-disclosure checks blocked delivery within four calls. This failure remained recorded, with the original prompt, sources, attempts and checker outputs in the separate memory/practice receipts.

The successor `practice_hint_repair_v4` is frozen only for new owned linked-practice hint requests. Its generation instruction leaves the current step's result for the learner in the body, summary, question and source surfaces. If an applicable global teaching gate fails, there is no individual binding certifying prior factual spans as safe to disclose. Those spans are therefore available to a full teaching-draft repair that can also replace `tutor_question`. The existing requirement that hint `short_answer` be null supplies a separately recorded surface repair boundary. Every replacement receives the same final source-support, pedagogy and cumulative-disclosure checks, with no publication override and the same four-call cap. Source-only defects with passed teaching gates retain protected exact spans and use the local claim patch. Historical V3 requests retain their original prompts and protection behavior.

The V4 repair tests and surrounding claim, teaching and practice transport checks passed 100 authored cases. The first run's four new fixture mistakes and its subsequent corrections are recorded; they did not loosen a product release gate. [Focused repair receipt](../../evidence/week09-continuation/20261001/practice-hint-repair-v4-focused-20261001.json). Its exact original live practice repeat still failed after four calls, 47.613 seconds. The boundary released the unsafe content for full repair, but the model returned the same answer-revealing body and old question. The final next-action gate blocked delivery. Some final checker booleans also contradicted its explanation; those raw records remain retained. The accompanying direct memory request failed its separate semantic check after four calls; the subsequent actual memory deletion erased its private draft derivatives, which were preserved as redacted records.

The new frozen `practice_hint_repair_v5` removes the instruction to begin with a source-supported explanation for new linked hints and uses a dedicated hint-first prompt. Its full pedagogical repair instruction requires replacement of leaked results and obsolete question metadata. Historical V4 and ordinary V3 branches retain their original behavior. Source-only repairs still preserve approved exact spans, all final checks stay active and the four-call limit remains. The successor focused run passed 104 authored tests and Ruff. [V5 focused receipt](../../evidence/week09-continuation/20261001/practice-hint-repair-v5-focused-20261001.json).

The same generic learner request then delivered a live procedural hint with two calls, 23.514 seconds, no factual citations and no answer repair. Its checked body and published body were identical. The online checker classified all four claims as nonfactual guidance and accepted the active teaching gates without structural issues. The hint asks the learner to locate the relevant sentence and compare the options with the type of energy mentioned, leaving the decisive source term out of the response and source display. Developer reading found a comparison operation added to the previous locate-sentence hint; the value of that addition remains for independent reviewers. [Installed V5 runtime](../../evidence/week09-continuation/20261001/practice-tutor-official-runtime-attempt5.json).

This authored exercise has only two options and earlier grading marked one option incorrect. That feedback may already imply the remaining option. The observed successor therefore demonstrates delivery without an added explicit answer term or result-bearing citation in this case. It cannot establish zero cumulative leakage across the complete practice experience or a teaching-effect estimate. These practice calls have their own accounting and are excluded from the 53-call answer-development total above. [Separate practice accounting](../../evidence/week09-continuation/20261001/practice-tutor-runtime-accounting-attempt5.json).

Four local blind calibration packets are now available in `E:/5703/deliverables/CS30-1_Week09_Reviewer_Materials_20261001`: the suspected textbook support defect, the two actual failed V4 draft generations and the actual V5 delivered hint. They contain actual candidate bodies, displays, source extracts, prior shown hints and earlier attempts. Intervention and publication provenance stays private. Two reviewer forms are blank, and the delivered import tool verified four unscored rows with zero scores. Citation sets, displayed source text and official-reference hashes were checked. The guide asks reviewers to distinguish earlier two-option feedback from incremental candidate disclosure. [Preparation receipt](../../evidence/week09-continuation/20261001/week09-reviewer-materials-preparation-20261001.json). Authored checks and developer observations do not establish human agreement or formal heldout results.

The V13 query checks passed 57 focused cases. The claim-patch, answer-core, teaching-contract and practice-context generation checks passed 84 focused cases. Ruff static and formatting checks passed for the owned repair files. The earlier query-test failure and first repair-test fixture failure remain recorded. A later focused run emitted a pytest cache permission warning; all 84 tests passed. These checks are separate from the root-owned unified software gate.

The first unified gate completed with 1,454 tests passing and ten failing on an unchanged source snapshot. Six failures in historical generation fixtures resulted from mixing a manually downgraded V3/V4 reliability policy with the newly submitted V3 claim-patch repair policy. The historical engine correctly rejected that unsupported combination. Those fixtures now pin their actual historical `cause_specific_repair_v2` setting, while current-request tests explicitly assert `claim_patch_repair_v3`. The old-policy prompt-isolation assertion also remains active. The affected generation/reading/facet files and claim-patch regressions then passed 33 focused tests. [Focused log](../../evidence/week09-continuation/20261001/legacy-repair-focused-final2.log). An initial attempt on the restricted stage server could not create its temporary database because of `pg_hba` scope; its setup errors are retained separately and do not represent assertion results. The complete connection traceback is private and the public copy redacts its local database credential. The successful run used fixture-owned random temporary databases on the authorized server, preserving the main database schema.

| Development run | Sanitized receipt |
| --- | --- |
| Managed save, role tests and activation | [model configuration](../../evidence/week09-continuation/20261001/real-answer-model-config-v1-20261001-sanitized.json) |
| Initial selected passage, multipart and follow-up | [official smoke](../../evidence/week09-continuation/20261001/real-answer-official-smoke-v1-20261001-sanitized.json) |
| V13 four-book and scope precursor | [V13 extended](../../evidence/week09-continuation/20261001/real-answer-v13-extended-v1-20261001-sanitized.json) |
| DNA/RNA unused-edit probe, before | [before](../../evidence/week09-continuation/20261001/real-answer-dna-before-prompt-v1-20261001-sanitized.json) |
| DNA/RNA unused-edit probe, after | [after](../../evidence/week09-continuation/20261001/real-answer-dna-after-prompt-v1-20261001-sanitized.json) |
| Typed patch repeat, including two remaining failures | [claim-patch repeat](../../evidence/week09-continuation/20261001/real-answer-claim-patch-failed-repeat-v1-20261001-sanitized.json) |
| Actual prompt-chain repeat | [actual-binding repeat](../../evidence/week09-continuation/20261001/real-answer-actual-binding-failed-repeat-v1-20261001-sanitized.json) |

Full questions, exact answers, provider payloads, source excerpts, raw checker outputs, frozen request policies and attempt budgets remain in private receipts under `E:/5703/week09-private-db`. Public receipts contain allowlisted outcomes, hashes, source locations, timing and usage.

The integrated candidate still needs independent sufficiency/support labels, calibration of suspected false acceptance and false blocking, an isolated complete-answer quality check on new knowledge-point groups, exact tokenizer compatibility assessment and final installation/performance verification. The original E0/E1 and teaching A/B/C/D definitions remain unchanged. This development diagnosis does not replace those experiments or their required independent scoring.
