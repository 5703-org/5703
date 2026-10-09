# Week 9 Generation and Teaching Report

CS30-1 team | 26 September 2026 | Project leader Xianshu Zhang

Week 9 improves the delivery of textbook-grounded answers and makes failures easier to inspect. The project now checks the citations attached to each claim, repairs specific defects, plans progressive hints before generation, and records missing evidence. This report combines the retained Week 8 work with the current implementation, experiments, costs, deployment checks and Week 10 priorities.

The reserved comparison produced 35 answers or hints out of 40 requests with the common engineering changes and 18 out of 40 with the preserved Week 8 reference. The joint teaching intervention produced 34 out of 40. These are automatic delivery results. Independent factual accuracy, checker error rates and teaching usefulness await the team’s blind ratings.

## Current application and retained work

The application supports accounts, model administration, saved conversations, follow-up questions, exact source highlighting, opt-in learning memory and persistent teaching tasks. Ordinary textbook questions request a complete explanation. A learner who asks for a hint enters a progress-aware flow with a tutor question, a bound learner reply, further help and an explicit full-explanation action. Administrators can test and activate provider roles and inspect safe request diagnostics.

Four official OpenStax books remain the knowledge source. Their released corpus contains 10,594 chunks and 10,594 real 384-dimensional E5 vectors in PostgreSQL/pgvector. Source identities, page anchors, original resources and historical answers are retained. Real CPU encoding, BM25, dense retrieval, reciprocal-rank fusion and MiniLM reranking remain available. The preceding iteration’s retrieval reuse, task-continuation fixes and optional CPU backends are included in the cumulative packages.

## Generation and evidence changes

The v4 checking contract separates textbook facts, learner givens, calculations, teaching guidance and general knowledge. Each claim is checked against its actual cited fragments. Repairs target unsupported wording or bindings and preserve approved content. Final publication still checks authentic sources, semantic support, the visible answer, the displayed source projection and cumulative disclosure. Historical v2 and v3 requests retain their recorded paths.

A hint plan names the current learning step, the intended teaching action, permitted information and expected next learner reply. A separate display intervention selects complete source blocks under that allowance. Context coverage is recorded for retrieved candidates, packed evidence and generated claims. A named missing requirement can trigger one bounded local lookup in the same released corpus. Lexical coverage remains an inspectable estimate; reviewers assess actual sufficiency.

Provider probe v3 exercises the actual answer and checking structures. Connection checks remain available. The current DeepSeek configuration uses the provider’s hosted deepseek-flash alias through the retained provider adapter architecture. Other configured providers keep their adapters. A four-call limit and 180-second active budget apply to each checked request. Strict empty-output handling remains the default. The optional one-example recovery branch has software coverage; no new empty response occurred to measure its live recovery value.

## Registered comparison and sampling

The pre-change archive freezes 789 files. The research protocol was registered before implementation. Eight development pilot knowledge groups and twenty reserved groups use actual CPU-retrieved textbook context. The reserved groups cover five objectives per book and were fixed before their model outputs were observed. Related chapters may share prerequisites; the split separates the specific knowledge relationship being tested. Authored reference points await independent review.

A through D share the common v4 engineering. A retains the preceding content and display behavior; B adds content planning; C adds display planning; D adds both. W8 preserves the earlier v3 generation path as an engineering reference. All conditions share the corpus, role configurations and budgets. Two fixed authored teaching stages are distinct conditions. Each group-stage-arm cell executes once. Original E0 without retrieval and E1 with basic dense retrieval keep their separate definitions.

The 80-request pilot delivered 60 responses and retained 20 failures. Counts were A 12/16, B 15/16, C 13/16, D 11/16 and W8 9/16. The paired pilot variability suggested eighteen groups for an approximate 95 percent delivery-difference half-width of 0.15; the reserved study used twenty for balance across books. Common fixes after the pilot clarified tutor-question input and sent optimistic aggregate verdicts with unsupported factual claims through bounded repair. Three separate development replays then published three outputs. All earlier records remain available.

## Reserved results

All 200 scheduled outcomes are terminal. Of 170 stored terminal responses, 160 are answers or hints and ten are programmed evidence-insufficiency refusals with no model calls. Each arm has two such refusals. Thirty requests ended with execution or publication-check failures. The table separates these outcomes. Median and p95 cover every scheduled request, including refusals and failures; successful and failed subsets have their own distributions in the evidence JSON.

| Arm | Answers /40 | Refusals | Calls | Median ms | p95 ms |
| --- | --- | --- | --- | --- | --- |
| A | 35/40 | 2 | 99 | 4427 | 9015 |
| B | 38/40 | 2 | 93 | 3992 | 8459 |
| C | 35/40 | 2 | 98 | 4219 | 9105 |
| D | 34/40 | 2 | 99 | 4049 | 9136 |
| W8 | 18/40 | 2 | 122 | 8439 | 11486 |

A minus W8 is +42.5 percentage points, with a knowledge-group bootstrap 95 percent interval of [+27.5, +57.5]. Within the factorial, B minus A is +7.5 points [0, +15], C minus A is 0 points [-10, +10], and D minus A is −2.5 points [-12.5, +5]. Removing the two programmed refusals per arm changes the absolute delivery rates while preserving these paired differences. The interaction estimate is −10 points [−27.5, +5]. This run establishes no joint-intervention delivery advantage.

Final errors comprise 24 semantic failures, four checker inconsistencies, one enhancement validation error and one repair that changed approved content. The checker inconsistencies occurred in W8. Rejected drafts are available for independent assessment. Automatic acceptance alone cannot establish factual correctness or teaching benefit. The timings exclude HTTP queueing, live retrieval and browser display. One execution per cell provides no estimate of within-cell model randomness.

## Ordinary answers and live workflow

A separate exploratory comparison used eight already observed pilot topics in complete-answer mode. The studied v4 arm delivered 5/8 actual answers in 26 calls; W8 delivered 3/8 in 19 calls. Its all-request median and p95 were 11,303 ms and 16,261 ms; W8 recorded 8,924 ms and 13,564 ms. The studied v4 path therefore delivered more answers in this small comparison while taking longer. Proof validation, citation support, preserved-content and checker failures remain in the records.

The six-step real HTTP journey passed both provider-role probes and activated the tested configuration. Photosynthesis, the first osmosis hint, the bound learner attempt and a new enzyme problem produced answers. The DNA/RNA comparison stopped at a context-window boundary, and the explicit full explanation stopped at semantic validation. Nineteen provider calls cover the six probes and thirteen workflow calls. The successful hint browser checkpoint passed eighteen checks at desktop and mobile widths. The failed full explanation has no successful browser checkpoint.

After the experiments, we added versioned, lossless checker-input encoding for new requests. It selects the smallest complete representation while preserving source text, actual citation bindings, support checks and the configured model window. In the DNA/RNA replay, checker input fell from 13,151 to 12,094 reserved tokens, within the 12,288-token allowance. Four scheduled workflow replays produced four responses using 10 calls and 74,821 tokens. The full-answer action completed, with the osmosis response explicitly identifying evidence gaps beyond its core definition. These are operational results; independent human quality ratings remain pending. The original experiments and their exact executable source archive remain preserved separately from this release successor.

## Learning memory and CPU consistency study

The optional memory selector uses the pinned local E5 model for scopes unresolved by rules and rereads attributable source conditions. Current explicit requests take priority, followed by applicable subject preferences and saved general defaults. Ownership, expiry, deletion and revision rules continue to apply. A 0.8 threshold was selected on development cases. In 32 reserved authored cases, the selector retained 14/16 applicable memories, missed two and selected two of sixteen inapplicable memories. It stays disabled by default.

The separate sixteen-output memory application comparison used the preserved Week 8 generator. Each selector delivered 6/8 answers, with forty calls overall. Word counts and delivery do not establish whether preferences were followed; the review forms leave that judgment to the team. The selection set deliberately stresses unresolved scopes, so the rule baseline’s omissions do not describe general memory performance.

The official AlignScore base model ran in an isolated CPU environment on eight authored contrast pairs and sixty-four scoring observations. Seven pairs had the expected score ordering; an incorrect formula result ranked above its correct counterpart. Forty-eight warm context-claim scores had a median of 1,520 ms and p95 of 1,558 ms. The main environment remains unchanged and AlignScore stays outside the online pipeline.

## Cost and failure accounting

The six disjoint research and development phases used 840 provider calls and 7,713,886 reported tokens. Initial HTTP verification adds nineteen calls, and the release replay adds ten. The combined 869 submitted calls reported 7,876,384 tokens, estimated at USD 0.720573. These estimates use the official Saturday off-peak tariff retrieved on 26 September 2026: USD 0.003 per million cache-hit input tokens, 0.15 for cache-miss input and 0.60 for output. They are separate from a reconciled invoice.

| Phase | Calls | Known tokens | Estimated USD |
| --- | --- | --- | --- |
| Provider development | 20 | 172,460 | 0.018759 |
| Postpilot development | 10 | 94,368 | 0.007337 |
| Teaching pilot | 214 | 1,922,245 | 0.166453 |
| Reserved teaching study | 511 | 4,646,444 | 0.403604 |
| Direct answer pairing | 45 | 434,105 | 0.050619 |
| Memory application pairing | 40 | 444,264 | 0.053326 |
| Initial live HTTP | 19 | 87,677 | 0.010697 |
| Release replay | 10 | 74,821 | 0.009778 |

Raw incomplete-accounting flags remain visible alongside the number of submitted calls lacking token counters. Zero-call refusals and validation exits retain their own category. Failures consume their observed calls and tokens in these totals. Optional local CPU experiments add no paid answer-model usage. The hosted model alias is provider-controlled and does not identify immutable model weights.

## Human review and release verification

Blinded packets include accepted and rejected drafts with attributable sources and the visible teaching boundary. Reviewers do not see the arm or checker decision. They score context sufficiency, correctness, usefulness, step compliance, citation support, coverage, cumulative leakage and overall publication appropriateness. Two reviewers complete separate forms. Imports validate packet hashes, stable attributed reviewer names, distinct names across forms, final-response bindings and allowed labels. Blank and unsure judgments remain unknown; automatic and human summaries are separate.

Historical review contains 168 drafts from 128 requests, with 336 blank reviewer rows. The new pilot adds 100 drafts and 200 rows; the reserved study adds 253 drafts and 506 rows; direct pairing adds 22 drafts and 44 rows. Memory application adds sixteen cards and thirty-two blank rows. Programmed refusals have no draft and remain explicit nondeliveries in the scheduled answer denominator. Human semantic correctness, false blocks, false releases and useful non-overreaching delivery remain unscored.

The final software gate passed 1,089 Python tests and 89 frontend tests, with static checks, format, types, contracts and production build passing. A fresh same-host Windows CPU environment installed 77 packages with PyTorch 2.8.0+cpu and no CUDA runtime. The isolated database reached migration f2c86e9f345d. Real retrieval, two mock answer turns, source hashes, cancellation and history reload passed. Twenty-seven portable browser checks and sixteen inspected screenshots cover the mock workflow. A separate physical computer, physical Mac and assistive-technology acceptance remain future checks.

The original 108 tasks, 60 acceptance checks and twelve responsive IDs retain their requirement text and historical observations. Current evidence is appended by scope. The complete archive includes current source and the eighty preserved official resources plus two optional ONNX graphs and their manifest. Eight disjoint personal overlays use the original allocation and current complete files, cumulatively compared with the Week 7 final archive. Each personal DOCX is identical in its individual package and the separate Reports folder. Configured keys and private research payloads remain outside the public packages.

## Week 10 priorities

Complete two independent reviews, resolve disagreements explicitly and examine rejected drafts before changing acceptance rules. Prioritize proof and citation repair failures, the programmed evidence refusals and remaining complete-answer failures. Evaluate content planning and display planning with the human scores; keep the current study as a fixed record. Expand memory applicability cases before enabling semantic selection. Repeat deployment and recovery on a separate classroom computer. Compare role-specific model settings only with quality, full latency and cost measured together.

## Evidence and research basis

docs/execution/week09-generation-20260926.md; week09-generation-protocol-20260926.md; week09-generation-contracts-20260926.md; week09-ledger-20260926.md

evidence/week09-generation/20260926: pilot-summary.json; reserved-summary.json; generation/direct-paired-v1.json; memory-summary.json; alignscore-summary.json; cost-summary-research.json; http-final-01.json

The linked literature record documents RAGChecker, Sufficient Context, RefChecker, ALCE, RARR, MathDial, the BEA teaching assessment, LongMemEval, JSONSchemaBench, RouteLLM, AlignScore and DeepSeek JSON guidance. Their diagnostic and design ideas inform bounded project changes; the project evaluates its own implementation and corpus. See docs/execution/week09-literature-20260926.md for primary-source links.
