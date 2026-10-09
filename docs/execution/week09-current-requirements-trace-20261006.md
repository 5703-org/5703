# Current cumulative Week09 requirements trace

This trace reconciles the latest cumulative instruction of 6 October 2026 with the existing learning-assistant implementation. It describes one continuing project: the preserved main repository and isolated successor candidates feed the same contracts and application. It does not create a second product or replace earlier specifications, studies, reports or deliveries.

The 53 stable `REQ-W09-*` rows below reconstruct the current instruction into reviewable requirements. Their wording is a trace synthesis, not a verbatim quotation. Source **S** means the latest session instruction; other source keys identify existing public project documents. The earlier [requirements source index](week09-requirements-index-20261006.md) remains a dated provenance index. Its course-week-9/project-week-7 primary-task bucket is not the current project-week-9 scope.

## Status and evidence boundary

- `implemented_verified`: the implementation has actual evidence for the stated bounded component or software contract. Any semantic, population or device limit is stated in the row.
- `implemented_pending_verification`: implementation or a candidate exists, but the current requirement-matched operational or semantic observation remains open.
- `incomplete`: substantive implementation, design, measurement or current delivery is still missing.
- `external_condition`: an actual participant, independent human measurement or physical environment is required; independent engineering continues.

These are requirement-level observations, not a project-completion percentage. A passing software gate does not supply semantic labels, learning effects, a current runnable archive or new-device acceptance.

The verified 972-input baseline passed all eight original local Mock stages. The [public summary](../../evidence/current-fullmock-20261006-public-02/summary.json) records 4,107 passing base cases, including the 483 PostgreSQL cases as a subset; 102 additional passing subtest checks; one optional catalogue-dependent skip; and 204 frontend cases. Its source digest is `baa49e2a6348b6e6c083491797ac9a4ef02585874f713159fc1b2f602393af41`. The summary retains its separate resource-stop status and makes no paid/native/human/course acceptance claim. [Evidence fingerprints](../../evidence/current-fullmock-20261006-public-02/evidence-index.json) bind its underlying artifacts. These results remain bound to that version when a successor is adopted; a changed prompt or source does not inherit its verification.

The separate D07 native observations are narrower: S11 returned a response and recorded native PASS plus two same-DeepSeek review-role PASS results. Its inferred-pressure-change attribution and ask-versus-explain criterion concern remain unresolved. G01 executed a bound patch and full fresh joint check, then withheld the response with `REQUIREMENT_LIMITATION_MISSING` and `TUTOR_ACTION_REPEATS_DISCLOSED_ANSWER`. These original results remain unchanged. They establish neither independent-model grading nor a general teaching-quality rate. At this evidence cutoff, OR08's header correction and six-case preparation have no paid result. The two-file hint-prompt proposal has 40 offline controls and remains unadopted and live-unverified. The intended next comparison uses one adopted, frozen successor for both DeepSeek cases and all six OpenRouter cases; preparation is not an executed comparison.

## Source keys

| Key | Public source and precise scope |
| --- | --- |
| S | Latest cumulative session instruction, 6 October; twelve groups below, including human-review pause and continued engineering. Reconstructed here without attributing it to an older document. |
| B | [Effective requirements](../foundation/requirements.md), REQ-01-28 and UPD-REQ-01/02; [decisions](../foundation/decisions.md), L01-L09; [tasks](tasks.json), 108 original IDs; [acceptance](acceptance.json), 48 AC + 12 HC. |
| U | [Responsive specification](../foundation/responsive_spec.md), UI-01-12, lines 31-42. |
| G | [26 September generation protocol](week09-generation-protocol-20260926.md), fixed behavior, bounded repair, concept partitions, factorial teaching and release gates. |
| C | [30 September continuation protocol](week09-continuation-protocol-20260930.md), eight product areas at line 7, seven study families at lines 21-33, metrics at 37-39 and evidence/delivery gates at 43. |
| L | [Fourteen-area ledger](week09-current-fourteen-area-ledger-20261001.md), domains at 90-116, connected journeys at 128-142 and thirteen gates at 154-178. Its observations retain their original dates/source versions. |
| P | [26 September performance protocol](teaching-performance-protocol-20260926.md), arms/cache requirements at 29-33 and warm end-to-end target at 35. Its older numerical quality criterion is not automatically adopted by the latest instruction. |
| E | [Evaluation plan](../foundation/evaluation_plan.md), separate chat/OpenQA/MCQ suites, paired profiles, qrels, metrics, grouped uncertainty and review provenance. |
| M972 | Current [eight-stage Mock summary](../../evidence/current-fullmock-20261006-public-02/summary.json); software/fixture evidence only. |
| N07 | Actual terminal D07 case records, fingerprinted below; source-bound native/review observations, not Mock outcomes. |
| W | [Weekly plan](weekly_plan.md), project week 9/course week 11 at lines 487-579; [earlier source index](week09-requirements-index-20261006.md) preserves original and dated carry-over provenance. |

## 1. Question intent, evidence and answer outcomes

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-01-01 | Preserve original intent, negation, comparison axes, numbers, units, time qualifiers and pronoun/follow-up referents. | implemented_pending_verification | S; B REQ-03-05; L1/3. Current software controls exist; source-matched colloquial, multipart and natural multi-turn quality remains open. |
| REQ-W09-01-02 | Ordinary questions default to full answers; hint flow is explicit and independent of textbook/general-knowledge mode. | implemented_verified | S; G fixed behavior; B. M972 verifies the routing contract; N07 exercises explicit hint requests. This does not certify every generated answer. |
| REQ-W09-01-03 | Record relevance, supplied-context sufficiency and final claim support as separate decisions. | implemented_verified | S; C11; L3; N07 preserves distinct claim, requirement and coverage fields. Their semantic correctness is separately pending. |
| REQ-W09-01-04 | Cover necessary points with complementary evidence; diagnose packing/clipping gaps; permit at most one named-gap lookup within the same frozen release and shared budget. | implemented_pending_verification | S; C11; G; L3. Versioned coverage/packing/lookup exists; independently judged sufficient/partial/absent and misleading-overlap cases remain open. |
| REQ-W09-01-05 | Distinguish full answer, explicit partial answer/named gap, genuine ambiguity clarification, insufficient evidence and local/provider fault; preserve terminal failures. | implemented_verified | S; B REQ-06/08; M972/N07. Typed recording and fail-closed withholding are exercised; semantic appropriateness of each outcome still needs matched review. |

## 2. Claim checking, bounded repair and continuity

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-02-01 | Use stable claim identities and distinct textbook/given/derivation/guidance/general-knowledge types with actual source locators. | implemented_verified | S; G; N07. Typed records and stable IDs are observed. S11's compound given/derivation attribution remains a classification concern. |
| REQ-W09-02-02 | Check actual submitted/displayed citation bindings, authentic passages, locators and semantic support rather than a preferred replacement source set. | implemented_pending_verification | S; G; B REQ-07; L3. Exact N07 quotes are valid; quote containment alone does not establish full-claim entailment or sufficiency. |
| REQ-W09-02-03 | Repair only authorized defective spans, preserve unaffected/protected content, synchronize visible metadata and perform a full fresh final check before release. | implemented_verified | S; G; N07 G01. Actual bound splices preserve the protected givens and receive a fresh check; rejection correctly withholds. General mapping/repair quality remains scoped. |
| REQ-W09-02-04 | Independently review accepted and refused drafts for false blocks/releases and repaired-content quality; retain disagreements and negative results. | incomplete | S; G review; L2. Same-model S11 reviews do not resolve its provenance/explanation concerns or provide calibrated independent false-block/release labels. |
| REQ-W09-02-05 | Exercise real generation/checker schemas, contract versions and finite format recovery; separate connectivity, structured output and full project compatibility. | implemented_pending_verification | S; B UPD-REQ-01, HC-11; M972/N07. DeepSeek's exercised stages are real; complete route/model capability coverage is not established. |
| REQ-W09-02-06 | Permit genuinely nonfactual procedural guidance without fake citations; general-knowledge mode must not claim textbook certification. | implemented_pending_verification | S; P BUG-01/02; G. Controls exist. Classifying a leading scientific/operation cue as procedural still requires semantic judgment. |
| REQ-W09-02-07 | A short numeric/unit learner response continues the saved pending task; explicit topic change/full-help actions take priority, without silently deepening help. | implemented_pending_verification | S; P BUG-03; B REQ-03/08. Software continuity controls exist; current natural multi-turn and cumulative outcomes remain unverified. |

## 3. Eight connected product modules

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-03-01 | Reader: exact source highlights/version identity, scoped passage questions, reading position, mobile layout and restoration after reload/re-login. | implemented_pending_verification | S; C7; L reader journey; U. Existing paths and browser fixtures need the complete current connected learner journey. |
| REQ-W09-03-02 | Goals/concepts: versioned reviewed prerequisites and related concepts; learning state derives from actual attempts rather than ungrounded mastery assumptions. | implemented_pending_verification | S; C7; L6. Source-pinned proposals exist; review/publication/recommendation usefulness and calibration remain open. |
| REQ-W09-03-03 | Practice: MCQ, explanation, numeric/unit and step items use independent generation/validation/publication, private keys and pending assessment without advancement. | implemented_pending_verification | S; C7; L7. Rule/model assessment and state fences exist; current four-type solvability, semantic scoring/feedback and full key-isolation journey remain open. |
| REQ-W09-03-04 | Tutor: actual attempts feed feedback, hint/wait/progress/review actions under the same owned task and help allowance. | implemented_pending_verification | S; C7; L4. N07 has one accepted initial hint and one withheld repaired hint; no complete current real multi-turn progression is established. |
| REQ-W09-03-05 | Error/review: transparent error records and new same-concept transfer; self-report is distinct from objectively calibrated mastery. | implemented_pending_verification | S; C7; L8. Scheduling/records exist; current linked transfer and calibrated outcome evidence remain open. |
| REQ-W09-03-06 | Memory: preferences/goals/observations/tasks, current > subject > general > default precedence, attributable sources/TTL/revisions; edit/pause/resume/delete/undo/conflicts/cache invalidation and no uncertain application. | implemented_pending_verification | S; B W8V2-REQ-03-05; L5. Controls exist; current false/missed selection, stale-work suppression and actual explanation/practice/review effects need matched evidence. |
| REQ-W09-03-07 | Notes/bookmarks: owned source-linked notes, Markdown/DOCX export, review cards and revocation-aware historical citations. | implemented_pending_verification | S; C7; L8. Existing lifecycle/export evidence remains dated; current linked source-revocation/cache/export journey is required. |
| REQ-W09-03-08 | Administration: request-stage trace/replay, bounded draft review, recovery/retest/publication, accounts, models and studies with truthful health/usage displays. | implemented_pending_verification | S; C7; L9. Existing administration paths require matched current diagnosis/recovery and connected role-denial observations. |

## 4. Main generation-planning research mechanisms

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-04-01 | Before generation record saved goal, actual attempt/error, next action, disclosure allowance, learner-pending judgment, source-display plan and expected reply. | implemented_pending_verification | S; G factorial planning; C17. Current plans exist; G01's retained leading cue and S11's why-explanation concern remain unresolved. The separate 40-control prompt proposal is not adopted. |
| REQ-W09-04-02 | Enforce cumulative disclosure across answer/short answer/questions/citations/visual views and prior actual exposure; source support cannot override teaching limits. | implemented_pending_verification | S; B W8E-REQ-04; C11; L4. Finite notation/software guards and N07 projections are exercised; full semantic/cumulative safety is not certified. |
| REQ-W09-04-03 | Compare coverage/targeted patches and conditional memory within shared budgets, permitting negative findings and preserving older executable policies. | implemented_pending_verification | S; G memory/coverage; C15-17. Versioned mechanisms and retained failures exist; matched current effects remain unmeasured. |

## 5. Actual sources and structured material

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-05-01 | Retain the actual four OpenStax books and 10,594-vector release; authored fixtures cannot substitute for real corpus construction. | implemented_verified | S; B REQ-28/SCOPE-02; L10. The real release is a retained verified baseline. This status is not a fresh database audit or semantic approval of every source region. |
| REQ-W09-05-02 | Preserve source dates/licenses/hashes, exact text/span/page coordinates, units/indices and original version identity through reprocessing. | implemented_pending_verification | S; B REQ-10-12; L3/10. Provenance controls exist; current content/locator/notation review remains scoped. |
| REQ-W09-05-03 | Recover text, tables, formulas/glyphs and reading order with original page geometry; review semantic structure before publication/downstream use. | implemented_pending_verification | S; L10. Actual extraction/versioned review bundles exist; geometry counts do not certify cell/header/formula/figure meaning. |
| REQ-W09-05-04 | Parse the complete large 185-MB original in isolation with bounded failures and exception statistics; preserve originals and review concept relationships. | implemented_pending_verification | S; L6/10; source/parser records linked from L. Historical full parsing is retained; current semantic publication, exception coverage and relation decisions remain separate. |

## 6. Performance and operational correctness

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-06-01 | Improve in order: contract correctness, duplicate-work elimination, CPU optimization, then calibrated adaptive policies; preserve answer quality. | implemented_pending_verification | S; P27-35. Existing repairs/candidates are versioned; current G01 withholding and S11 concerns prevent a general quality-improvement claim. |
| REQ-W09-06-02 | Validate full corpus at build/load/invalidation; version BM25/token/tie semantics and visibility/revocation cache keys, with current publication checks. | implemented_pending_verification | S; P CACHE-01/02 and31. Exact/cache controls exist; complete current matched lifecycle/workload proof remains open. |
| REQ-W09-06-03 | Reuse warmed model instances, threads/batches and eligible prompt/provider caches; account for deduplication without hidden source/policy changes. | implemented_pending_verification | S; P29-35; B ENG-11. Retained optimization evidence is bounded; no current end-to-end effect is established. |
| REQ-W09-06-04 | Compare PyTorch, ONNX FP32 and INT8 with rank/quality evidence and backend-specific calibrated thresholds. | implemented_pending_verification | S; P29/33. Candidate configurations exist; thresholds/ranking quality cannot be transferred or inferred from speed alone. |
| REQ-W09-06-05 | Adaptive budgets progress through offline, shadow and quality-gated stages; prioritize interactive/parser/study resources and handle cancellation/timeout/reconnect/refresh/resume. | implemented_pending_verification | S; P; L11/12. Bounded operational controls exist; current sustained-load/recovery and policy-quality evidence remains open. |
| REQ-W09-06-06 | Target at least 30% reduction in warm end-to-end p95 with preregistered quality non-inferiority; measure submit-to-page stages and cold/first/warm/all/success/failure populations. | incomplete | S; P35. Current target is UNMEASURED; the quality endpoint, sampling design, non-inferiority margin and confidence method are UNFROZEN and require preregistration before formal comparison. The latest instruction supplies no numerical quality margin. P33's older criterion is not automatically adopted. Model-stage timing alone cannot satisfy this row. |

## 7. Installation, restoration and devices

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-07-01 | Install the latest candidate on CPU; migrate, query real sources, run practice/concurrency/cancellation and recover the application. | implemented_pending_verification | S; C43; L12; HC-02. M972's isolated PostgreSQL regression is not a complete current installed learner/runtime journey. |
| REQ-W09-07-02 | Back up, independently restore and exercise rollback/restart/faults while preserving original data and source identities. | implemented_pending_verification | S; C43; L12. Dated restore evidence remains valid for its version; latest matched workload/recovery proof remains open. |
| REQ-W09-07-03 | Report Windows CPU, Windows CUDA, another machine, Mac and physical-device input/accessibility observations separately. | external_condition | S; U; L12. Same-machine/emulated observations cannot supply unavailable physical/new-machine/Mac evidence; software work continues. |

## 8. Security, robustness and teaching safety

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-08-01 | Enforce object/role/disabled-account/reset/old-credential controls and paired authorized actions. | implemented_pending_verification | S; B REQ-01; L11; M972. Current software regressions pass; the complete matched native role/object matrix remains separate. |
| REQ-W09-08-02 | Bound Markdown/link/formula/file handling, corrupt/oversized inputs, redirects/DNS/special addresses and exhaustion; encrypt/mask secrets and scan delivery contents. | implemented_pending_verification | S; B REQ-10/20; C43; L11. Implemented guards require current combined adversarial/legitimate evidence and current-package scan. |
| REQ-W09-08-03 | Resist source/memory/multi-turn injection and preserve revocation/history/ownership boundaries through recovery. | implemented_pending_verification | S; C safety family; L11. Fixed controls exist; adaptive/model-mediated current scenarios remain open. |
| REQ-W09-08-04 | Evaluate wrong-feedback misconceptions and excessive cumulative help; report attack success together with safe legitimate-task completion. | incomplete | S; C30/37; L4/7/11. N07 observations are development cases, not a calibrated broad attack/legitimate teaching study. |

## 9. Formal experiments, reviewers and students

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-09-01 | Freeze the engineering candidate, concept-disjoint development/pilot/reserved partitions, anchors, configurations and calibrated evaluators; choose formal sample sizes statistically after the pilot. | implemented_pending_verification | S; G development/pilot; C15-21/33. The verified 972 baseline is frozen; any adopted successor needs a new identity and matched observations. Complete formal design/calibration remains open. Known bad/inspected cases remain development-only. |
| REQ-W09-09-02 | Prepare seven families at planning scales about 480 QA,60 tutoring concepts,240 memory scenarios,160 practice questions,120 visual regions,500 fixed safety cases plus bounded adaptive work, and repeated performance/recovery. | incomplete | S; C25-31. These are planning scales, not scheduled executions, achieved samples or a power guarantee. No large automatic launch follows from this trace. |
| REQ-W09-09-03 | Compare A/B/C/D old/new content planning × old/new source display with common corpus/models/budgets/final checks, fixed/multiturn states and separate earlier release; preserve E0/no retrieval and E1/basic dense definitions. | implemented_pending_verification | S; G factorial; C17/26/39; E. Retained runners/results and variants exist; current matched formal arms and hybrid/rerank-specific comparisons remain open. |
| REQ-W09-09-04 | Keep online checking separate from blinded evaluation; calibrate order/length/style/injection, retain invalid/disputed results and validate visible-only simulated students for consistent ability and hidden-answer isolation. | incomplete | S; C33; E. S11's same-model roles are executed reviews, not independently calibrated judges or a validated student trajectory. OR08 preparation has no terminal live result here. |
| REQ-W09-09-05 | Preserve human review materials/import tools and actual-rating provenance; keep paused human ratings/learning effects unavailable without inventing reviews or suspending engineering. | external_condition | S; E; W historical carry-over. Human measurement is paused and remains zero/null. Assistant execution cannot fill the human endpoint or establish learning gain. |

## 10. Metrics, identity and accounting

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-10-01 | Retain scheduled terminal denominators and separate substantive delivery, correctness, false refusal, unsupported content, coverage/citations, false blocks/releases, useful hints, disclosure and security outcomes. | implemented_verified | S; C37; E; M972/N07. Recording/failure retention is observed; unavailable semantic measurements remain unavailable rather than fabricated scores. |
| REQ-W09-10-02 | Use paired/grouped effects and confidence intervals, explicit repeats and factorial interactions; avoid treating turns as independent learners or tuning on reserved outcomes. | incomplete | S; C39; E. Statistical tooling/older results exist; the current final study design and executed grouped outcomes remain open. |
| REQ-W09-10-03 | Freeze code/data/model/prompt/config hashes; separate development/pilot/formal/judge/attack calls, tokens/cache usage, estimates and invoices, including failures/unknowns. | implemented_verified | S; C17/39; M972/N07. Current source/receipt identities and N07 known-use accounting are recorded; this does not confirm invoices or fill missing historical costs. |

## 11. Eight owners and actual execution

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-11-01 | Preserve the eight original accountable domains, separate actual executors/reviewers and avoid fabricated member contributions, approvals or dates. | implemented_verified | S; W; B L09. Domain metadata is retained; the current recorded implementation, tests and runs use the shared Codex workflow. Unrecorded member/human execution is not claimed. |

| Accountable owner | Current responsibility emphasis | Original project-week-9 task references |
| --- | --- | --- |
| Xianshu Zhang | Requirement trace, contracts/integration, candidate identity and cumulative release | INT-09, INT-07, CHAT-11 |
| Hongle Yang | Four-book provenance, parsing/structure/locators, corpus and source relationships | DAT-10, DAT-12 |
| Chengzhou Liu | Query/evidence/retrieval, compatible variants and CPU/performance comparisons | RET-06, RET-11 |
| Sijin Lu | Generation/checker schemas, bound repair, teaching plans and provider/model controls | GEN-06, GEN-11 |
| Pengyuan Xia | Profiles/memory, teaching/review criteria, learner-state and research limitations | PER-07, PER-09 |
| Zeping Liao | API/database/workers, operations, ownership/security, migration/restore/accounting | BE-15, BE-16 |
| Baiqing Huang | Connected eight-module frontend, responsive/input lifecycle and evidence display | FE-06, FE-08, FE-12 |
| Chong Zhang | Frozen experiments, evaluator/statistical methodology and complete acceptance/delivery QA | QA-13, QA-11, QA-10, QA-12 |

These emphases reconstruct the cumulative work without reassigning original IDs or proving that named members performed it. Artifact readiness governs execution across domains.

## 12. Current reproducible delivery and preservation

| ID | Current requirement | Status | Evidence and remaining proof |
| --- | --- | --- | --- |
| REQ-W09-12-01 | Run current focused and full software/contract/frontend gates with exact source identities, failures/skips and independent evidence review preserved. | implemented_verified | S; B; M972. All eight stages passed for the verified 972 baseline with the explicitly optional skip retained. Adoption requires matched successor checks; native/semantic/physical acceptance remains separate. |
| REQ-W09-12-02 | Deliver one latest complete runnable package and eight disjoint latest-current-file owner packages; verify reconstruction, parity and direct retrieval paths. | incomplete | S; C43; G release. Existing current951 source-review packages and historical current880 complete package remain preserved; neither is a new runnable delivery of the validated final successor. |
| REQ-W09-12-03 | Produce one English overall and eight personal DOCX reports with exact copy equality, methods/controls/ablations/security/performance/cost/failures and every rendered page reviewed. | incomplete | S; C43; L14. Prior nine-report deliveries retain their checkpoints. The new package/report set must use one common, validated final successor; earlier report QA does not establish that set. |
| REQ-W09-12-04 | Include reproducible protocols/data/controls/blind tools/raw failed outcomes/install/backup/rollback/hash records; preserve Week7, old releases, original sources/data and required experiment histories. | implemented_pending_verification | S; C43; W. Preservation/versioned evidence exists; the current full package/report manifest and reconstruction closure remain pending. |

## Priority closure order

1. Resolve the demonstrated current hint/repair and reviewer-reliability gaps. G01 remains withheld; S11's recorded PASS does not settle source attribution or the explanation criterion. Review the unadopted prompt proposal, preserve current972 and require a successor identity before adoption. Do not relabel OR08 preparation as a live result.
2. Complete current connected learner/operator journeys and matched semantic checks for practice, tutoring, memory, sources and administrative recovery. Software gates and initial-turn components cannot replace these observations.
3. Preregister a warm submit-to-page performance comparison and quality non-inferiority design. Only the 30% warm p95 reduction target is specified; quality endpoint/margin/confidence rule and final sampling design remain unfrozen for current work. Measure the entire path and preserve unsuccessful outcomes.
4. Calibrate independent evaluation/student simulation and finalize concept-disjoint pilot/formal designs before large experiments. Retain the seven planning scales and negative findings without automatically scheduling those workloads. Human pause is a research boundary, not an engineering stop.
5. Close current installation/recovery/security/source-structure evidence, then build and verify the latest complete/owner packages and nine reports. Keep independently unavailable device/learning/course observations explicit.

Link README, PLANS and execution progress to this trace through additive, versioned headers once it is published; preserve their historical bodies, original IDs and results. Change canonical foundation documents only for an actual conflict or implementation decision, with separate provenance. Close a row only with a requirement-matched receipt, not by changing a planning label or copying a predecessor result.

## Native observation fingerprints

The N07 statements above refer to the already-terminal public fictional-case records, not the Mock summary. Their immutable case-result SHA256 values are:

- S11 D07, `live-02-deepseek-S11-07/case-result-01.json`: `2385c11ba8807f92e9265a200c4ed3c2387fc91849af825679d812444b111ed1`.
- G01 D07, `live-01-deepseek-G01-07/case-result-01.json`: `958f4455385e596ddc90d14ac8732ce6852d7911d454f1cb49212bbfc70c6a3b`.

Both cases retain their original raw judgments. Earlier D05 failures remain earlier failures; later D07 acceptance does not upgrade them. A public native-summary successor must record its own actual terminal scope before it is cited as published evidence. This trace makes no independent-model, human learning, final-course-submission or whole-project-completion claim.
