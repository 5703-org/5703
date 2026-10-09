# Week 9 supported answer delivery and teaching study

The Week 9 work extends the verified Week 8 teaching and CPU package. It focuses on checking actual citation bindings, reducing unnecessary checker retries, planning progressive hints and their displayed sources together, and testing optional semantic memory reading. The eight original workstreams and the original four-book knowledge base remain in use. Codex performed the recorded implementation and automated execution; the group owns independent review and submission.

## Preserved baseline and scope

The pre-change source archive contains 789 files and has SHA-256 `ea41a00b977624f74d6e5e15574ab8e01b649c4d163eb7a96312cde9d33037f3`. The previous complete package has SHA-256 `a2e7f1111db45b29356046f1daa6ee56485fde8890b9e83ca62f93ae6366817e`. Both remain preserved. Current delivery is cumulative from the Week 7 final archive through the preceding iteration and Week 9, using complete current files and the original eight-owner allocation.

The [registered protocol](week09-generation-protocol-20260926.md) precedes implementation. The [research record](week09-literature-20260926.md) maps primary literature to the proposed changes. Existing E0 no-retrieval and E1 basic-dense-retrieval definitions remain unchanged. Ordinary textbook questions continue to request complete answers. Explicit hints use teaching progress, source visibility and cumulative disclosure controls. The active corpus retains four official books and 10,594 real 384-dimensional E5 vectors.

## Implemented changes

- The v4 generator and checker use typed claim variants, actual citation assessments and bounded local revisions. Historical v3 execution is retained. Raw drafts, checks, attempt usage and final display hashes are recorded.
- Each hint can carry a deterministic action plan specifying the current step, disclosure allowance, source needs and expected learner reply. Source-display selection is a separate experimental factor. Exact source text and final semantic checks remain publication conditions.
- Candidate coverage, packed-context coverage and draft support have separate records. Interactive requests can make one targeted local retrieval for a named missing requirement. Lexical estimates carry no independent semantic label.
- Actual answer and checker schemas are tested through provider probe v3. API and administrator activation controls recognize that version; old results remain historical records. Strict empty-output handling remains the default, with an explicitly experimental one-example recovery policy.
- Optional semantic memory selection uses the pinned local E5 model, scoped preference rules and attributable source rereading. Selection errors keep this feature optional. Current explicit instructions and applicable subject preferences preserve their priority.
- Independent review exports accepted and rejected drafts, validates their display hashes, distinguishes retrieved candidates from submitted evidence and keeps actual human judgments blank. Packet integrity and distinct reviewer attribution are checked during import.

Module details are in the [generation contract](week09-generation-contracts-20260926.md), [teaching and coverage record](week09-progress-coverage-20260926.md) and [memory record](week09-memory-20260926.md).

## Baseline diagnosis and source preparation

The historical diagnosis includes 128 requests, 92 published outputs, 36 failures and 168 available draft revisions. Two reviewer forms provide 336 blank rows. A checker rejection supplies a review stratum; it does not establish that a draft was factually wrong. [The current export receipt](../../evidence/week09-generation/20260926/baseline-failure-diagnosis-v4.json) preserves these denominators.

The new catalogue contains eight pilot groups and twenty reserved groups, with distinct knowledge objectives across four textbooks. Sixteen reserved groups were prepared before the pilot. Four further groups were added before any reserved model output after the pilot precision calculation, producing five reserved groups per book. Previously inspected questions remain development material. Related textbook chapters and prerequisite vocabulary can occur across groups; partitioning concerns the specific knowledge relationship being evaluated. Reference points are authored and await independent verification.

All 28 questions were retrieved against the real corpus using E5 on CPU, PostgreSQL/pgvector, hybrid ranking and the existing reranker. Source text, hash and identity were checked in read-only transactions. The corpus fingerprints remained unchanged. Retrieved counts range from one to twenty; low-count cases remain scheduled. [Preparation receipt](../../evidence/week09-generation/20260926/source-preparation-summary.json).

## Completed pilot

The frozen pilot ran eight groups, two authored teaching conditions and five arms, for 80 outcomes. A through D share the new engineering; W8 retains v3. The two teaching stages are distinct conditions with fixed authored prior context, not stochastic repetitions or generated longitudinal conversations. Each arm uses the same corpus, role configurations, four-call limit and 180-second budget. The 84-file runtime snapshot stayed unchanged.

| Arm | Content plan | Source display plan | Published | First check accepted | Physical calls | All-request median ms | All-request p95 ms |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| A | Existing | Existing | 12/16 | 9/16 | 43 | 5300.24 | 8879.89 |
| B | New | Existing | 15/16 | 12/16 | 39 | 4514.13 | 11268.06 |
| C | Existing | New | 13/16 | 9/16 | 44 | 5057.58 | 11420.38 |
| D | New | New | 11/16 | 10/16 | 39 | 4303.79 | 9094.88 |
| W8 | Preserved v3 | Preserved v3 | 9/16 | 6/16 | 49 | 7484.75 | 11341.07 |

The pilot contains 20 terminal failures: twelve checker-consistency failures and eight semantic failures. D minus A is -6.25 percentage points, with a knowledge-group bootstrap interval from -25.00 to +12.50 points. This pilot supplies no established joint-method advantage. Conditional B minus A, C minus A, D minus A, their interaction and the separate A minus W8 engineering contrast retain their own reported intervals. [Complete pilot receipt](../../evidence/week09-generation/20260926/pilot-summary.json).

These times cover generation and checking on frozen retrieved context. They exclude live retrieval, HTTP queueing and browser display. All, successful and failed requests have separate distributions. Usage was complete for 214 attempts: 1,922,245 reported tokens. Applying the retrieved weekend tariff gives an estimated USD 0.16645263. The [official tariff reference](../../evidence/week09-generation/20260926/tariff-reference.json) records rates and date; an estimate does not reconcile the provider bill. The hosted `deepseek-flash` alias can change its served model; fixed request settings do not constitute an immutable hosted weight revision.

The pilot paired standard deviation of 0.320435 gives an estimated requirement of eighteen groups for an approximate 95 percent operational-delivery difference half-width of 0.15. The reserved allocation rounds to twenty groups to balance books. This estimates operational precision. Human quality effect size and power await actual ratings. [Frozen sample decision](../../evidence/week09-generation/20260926/reserved-sample-decision.json).

## Reserved comparison

The reserved study completed all 200 scheduled outcomes across twenty independent knowledge groups, five per book, two fixed authored teaching conditions and five arms. All 84 frozen runtime source hashes remained unchanged throughout execution. Common post-pilot corrections clarified the tutor-question field and routed contradictory optimistic body verdicts through bounded repair; the preserved v3 reference stayed unchanged. Three separate development replays published three outputs in ten calls before the reserved study began. These replays and their failures from the pilot retain separate records.

| Arm | Terminal responses | First check accepted | Calls | All median ms | All p95 ms | Response median ms | Failure median ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 37/40 | 26/40 | 99 | 4427.27 | 9015.05 | 4366.21 | 8971.92 |
| B | 40/40 | 30/40 | 93 | 3991.81 | 8459.22 | 3991.81 | N/A |
| C | 37/40 | 27/40 | 98 | 4218.99 | 9105.08 | 4135.55 | 7966.54 |
| D | 36/40 | 25/40 | 99 | 4049.23 | 9136.47 | 3972.47 | 8220.96 |
| W8 | 20/40 | 10/40 | 122 | 8439.22 | 11486.04 | 4783.52 | 9019.91 |

The raw operational summary counts a programmed refusal as a published terminal response. A read-only [outcome-type audit](../../evidence/week09-generation/20260926/derived-outcome-types.json) separates 160 answers or hints, ten programmed refusals and thirty execution failures. Each arm has two refusals. Actual answer/hint counts are A 35/40, B 38/40, C 35/40, D 34/40 and W8 18/40. All ten refusals share one frozen knowledge objective: retrieval yielded one chunk and two fragments, but neither fragment satisfied the complete-source-block admission rule. They remain in the scheduled denominator and require source-sufficiency review.

The common-engineering A arm delivered answers or hints for 87.5 percent versus 45.0 percent for W8, a paired difference of +42.5 percentage points with a knowledge-group bootstrap 95 percent interval of [+27.5, +57.5]. This measures automated answer/hint delivery under each recorded policy. Subtracting the two programmed refusals in each arm preserves the paired differences and intervals. Independent correctness remains unscored. Within the common-engineering factorial, B minus A is +7.5 points [0, +15], C minus A is 0 points [-10, +10], and D minus A is -2.5 points [-12.5, +5]. The joint intervention has no demonstrated delivery advantage in this run. B is a useful candidate for further independently scored work; the study does not select a new production default from held-out results.

Thirty failures remain visible: 24 semantic failures, four checker inconsistencies, one enhancement validation error and one repair that changed approved content. The four remaining checker-inconsistency terminal errors occurred in W8. Source-support, coverage, teaching disclosure and preserved-content checks continue to block output where their contracts fail. Reviewers must determine how often these blocks protected quality or rejected a usable draft.

The 511 provider attempts reported 4,646,444 known tokens. Eleven outcome records have incomplete accounting metadata: ten zero-call programmed refusals and one zero-call validation failure. All 511 physical attempts are submitted and have known token counters. Raw accounting flags and this derived classification remain separate. The known-counter weekend tariff estimate is USD 0.403604463. All-request, successful-request and failed-request p95 values remain in the [complete reserved result](../../evidence/week09-generation/20260926/reserved-summary.json). One execution per group-stage-arm cell provides no estimate of within-cell model randomness. Human factual correctness, useful non-overreaching hint delivery, checker false-block and false-release rates remain null until independent forms are imported.

## Memory and optional CPU consistency model

The semantic-memory stress set contains 64 authored cases across eight development and eight reserved groups. A threshold of 0.8 was selected using development labels. In the reserved subset, semantic selection retained fourteen of sixteen applicable entries, omitted two and falsely selected two of sixteen inapplicable entries. The deliberately unresolved rule baseline retained none of the sixteen applicable entries. These counts describe the authored stress fixture, with independent labels still blank.

The separate sixteen-output memory application pilot published six of eight requests per selector arm, with forty provider calls and 444,264 reported tokens. Automatic length and delivery measurements do not establish preference compliance. The private reviewer materials contain sixteen cards and two blank forms. [Memory aggregate receipt](../../evidence/week09-generation/20260926/memory-summary.json).

An isolated Python 3.10 and PyTorch 1.13.1 CPU environment executed the official AlignScore base model against eight authored contrast pairs covering negation, conditions, formulae and units. All sixty-four scoring observations completed. Seven of eight contrasts had the expected ordering; one incorrect calculation claim ranked above its correct counterpart. Forty-eight warm context-claim scores had median 1519.84 ms and p95 1558.12 ms. The checkpoint remained unchanged and the main environment was preserved. AlignScore stays outside the online pipeline. [CPU receipt](../../evidence/week09-generation/20260926/alignscore-summary.json).

## Software verification and remaining evaluation

The first full software gate passed 1,054 Python tests and failed two older scripted provider-probe fixtures. Three files also required formatting. Foundation, API contracts, chat scope, frontend types, frontend tests and production build passed, and sources stayed unchanged during that gate. Its logs remain preserved. The integration-only successor passed all 138 tests. The [final aggregate gate](../../evidence/week09-generation/20260926/software-gate-final-attempt3/software_gate.json) passed 1,074 Python tests and 89 frontend tests, all static, format, contract, type and production-build checks, with unchanged executable sources. Earlier failing logs remain preserved. The [original registry review](week09-ledger-20260926.md) appends current scoped observations to all 108 tasks, 60 acceptance checks and 12 responsive checks, preserving their IDs, wording and earlier status history.

Human semantic ratings, checker false-block and false-release rates, useful non-overreaching hint quality, physical-device acceptance and delayed learning outcomes remain open. No project completion percentage is inferred from test counts. [PLANS.md](../../PLANS.md) records the current execution order and [SPEC.md](../../SPEC.md) describes the implemented boundaries.

## CPU installation and browser verification

A fresh environment on this Windows host installed Python 3.13.2, 77 locked packages and PyTorch 2.8.0+cpu with no CUDA runtime. Dependency checking passed. The isolated PostgreSQL database migrated to `f2c86e9f345d`, imported all four books and 10,594 active 384-dimensional vectors, and verified eighty official resources plus three retained ONNX resources. Real E5 retrieval, two mock-answer turns, source hashes, cancellation and history reload passed. This establishes a fresh same-host CPU environment; a separate physical computer and Mac remain additional deployment checks.

The portable browser run passed 27 scoped checks at desktop and mobile widths with sixteen inspected screenshots and no page errors. It exercised provider probe v3 and activation with the mock provider, exact sources and pages, dialog keyboard behavior, administrator traces and reload behavior. Its mock hint correctly reported semantic-check unavailability. [CPU receipt](../../evidence/week09-generation/20260926/portable/runtime-verification.json) and [browser receipt](../../evidence/week09-generation/20260926/browser-portable-01/verification.json) preserve this scope. Real hosted-model HTTP execution has its own receipt.

## Direct answers and current HTTP journey

A separate exploratory pairing used eight already observed pilot objectives in ordinary complete-answer mode. V4 delivered five of eight actual answers in 26 calls; W8 delivered three of eight in 19 calls. No delivered response in this pairing is a programmed refusal. All-request median/p95 were 11,302.59/16,261.11 ms for v4 and 8,924.14/13,563.74 ms for W8. The current path delivered more answers in this small set and took longer. The [direct receipt](../../evidence/week09-generation/20260926/generation/direct-paired-v1-concise.json) preserves proof, citation, checker and approved-content failures. All 45 submitted calls have usage; one W8 zero-call validation exit retains an incomplete raw accounting flag.

The [first real HTTP journey](../../evidence/week09-generation/20260926/http-final-01.json) completed all six steps. Both real provider-role probes passed and the configuration was activated. The ordinary answer, first hint, bound learner attempt and new problem published. The multi-part comparison hit the checker context-window boundary, and the explicit full explanation failed semantic checks. Both failures remain stored. The real hint browser checkpoint passed eighteen desktop/mobile checks; its screenshots were inspected. No successful full-explanation browser checkpoint is asserted. The [usage receipt](../../evidence/week09-generation/20260926/http-final-01-usage.json) contains nineteen calls and 87,677 tokens across probes and workflow.

The disjoint research and development phases used 840 submitted calls and 7,713,886 known tokens, estimated at USD 0.700097835 under the retrieved weekend tariff. The initial HTTP journey is an additional phase. [Research cost receipt](../../evidence/week09-generation/20260926/cost-summary-research.json). CPU-only work uses no paid answer-model calls. Actual invoices and independent human quality labels remain separate inputs.

## Final release successor

The first live comparison generated a draft but exceeded the fixed checker window. Initial generation reserved 11,336 input plus 1,024 output tokens. The checker needed 13,299 plus 4,096, exceeding 16,384 by 1,011 before submission. Its memory-bearing raw payload is intentionally not retained; this diagnosis uses recorded token accounting.

The final release adds `lossless_checker_tables_v1` for newly submitted commands. It measures three complete representations and selects the smallest. Shared citation allowlists and positional tables remove repeated encoding fields. Exact round-trip checks protect the new representation. Historical commands retain the previous policy. The independent small-input audit confirms that the selector avoids encoding expansion. Source bytes, citation identities, semantic checks, output reservation, call limits and the configured window remain intact.

The exact 84-file formal runtime was archived before this release-only change at SHA-256 `14690e4a44934fc3a850797b387a5ddde7e14afb5fd21b8d2b6107d73f35651e`. Original pilot, reserved and direct outcomes continue to describe their frozen versions. The final package is a documented transport successor. Offline recount of thirteen previously submitted checker inputs saved 469 to 2,579 tokens per input, 19,424 total; it involved zero provider calls and carries no semantic quality inference.

The frozen four-submission successor replay published four responses: the same DNA/RNA comparison with saved memory, a direct osmosis explanation, a fresh hint and its full-explanation action. The comparison used 12,094 checker input tokens versus 13,151 with the previous fragment table; the 12,288-token input allowance and 4,096-token output reservation stayed fixed. The full-explanation action produced a qualified partial answer, explicitly naming missing direction, concentration and pressure evidence. Its thirteen browser checks validate interaction and source presentation, while complete semantic coverage remains a review target. The four replay times were 25,034.20, 9,776.66, 4,139.90 and 10,069.80 ms; they include live processing and are separate from the frozen generation-only comparisons.

[Successor outcomes](../../evidence/week09-generation/20260926/http-successor-01.json), [usage and encoding](../../evidence/week09-generation/20260926/http-successor-01-usage.json), [independent transport audit](../../evidence/week09-generation/20260926/generation/checker-encoding-independent-audit.json), [offline recount](../../evidence/week09-generation/20260926/generation/checker-encoding-offline.json), [full-mode browser](../../evidence/week09-generation/20260926/browser-http-successor-01-explicit_full/verification.json) and [current CPU source execution](../../evidence/week09-generation/20260926/portable/runtime-verification-release-source.json) preserve their separate scopes.

The [final release gate](../../evidence/week09-generation/20260926/software-gate-release-final-02/software_gate.json) passed 1,089 Python and 89 frontend tests, with all eight stages and source consistency passing. The first release aggregate attempt retained three scripted integration failures caused by fixtures reading the preceding object payload shape; fixture corrections preserve their model-freeze, private-secret and stale-disclosure assertions. No production behavior changed in that fixture successor. The final original-registry reconciliation appends a separate release checkpoint.

The private human handover contains 559 cards and 1,118 blank rows in five sets. All strict imports passed, with zero human ratings. Pilot and reserved actual answers bind exactly to 60 and 160 reviewed final drafts respectively. [Handover verification](../../evidence/week09-generation/20260926/human-review-verification.json). Reviewer identities and independence are established by the team; the importer checks stable attributed names and their distinctness.
