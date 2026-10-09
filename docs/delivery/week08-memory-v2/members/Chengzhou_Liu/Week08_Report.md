# Week 8 Work Report

Chengzhou Liu | Retrieval and source selection | 2026-09-22

## Week 8 contribution

Provide complementary real textbook evidence within the existing bounded retrieval path. Learned E5 vectors, CPU support, local reranking and historical dense baselines remain intact while evidence packing and local source context become more inspectable.

Original task allocation: RET-01, RET-02, RET-03, RET-04, RET-05, RET-06, RET-07, RET-08, RET-09, RET-10, RET-11, CHAT-04.

## Completed implementation

Evidence selection balances requested facets, complementary passages, duplicate removal and complete conditions within the existing evidence and context budgets. Ranking scores remain relevance signals, separate from semantic support judgments.

The repaired path retains necessary nearby references and complete atomic content through exact source mappings. Actual submitted text is recorded so a missing qualification or unsuitable selection remains diagnosable.

New comparisons freeze the same real CPU pool for each question. A legacy-packing ablation isolates that component while other policies stay matched. Earlier E0/E1 protocols do not inherit the interactive hybrid policy.

## Interfaces and operation

Hongle supplies source identity and boundaries. Sijin consumes selected content with complete token accounting. Pengyuan supplies learner-state constraints without making memory factual evidence. Chong freezes paired inputs.

- Inspect the whole question and exact selected context for a retained failure.

- Check duplicates, local references and complete blocks against the token budget.

- Use the frozen pool and policy when comparing outcomes, including failures.

## Verification and findings

The installed CPU path used real E5 embeddings, the local reranker and pgvector over the preserved 10594-vector, 384-dimensional release. The two-turn journey asked about photosynthesis and why it requires light, retained sources and reloaded saved history. Answer generation in that installation was explicitly mock.

The reliability implementation records complementary source selection and complete-block context under fixed evidence and token budgets. The final source checkpoint captures the code supplying the frozen candidate pools. Ranking, lexical coverage and exact source identity are inspectable signals; final scientific support is evaluated separately.

Cold and subsequent turn observations were approximately 24.056 and 6.648 seconds on this host. These are two individual execution measurements with different cache states. They provide useful operational context without establishing a distribution, device comparison or latency guarantee.

The final public sync changed evaluator loaders, tests and packaging membership after the saved runtime proof. All 80 resources remained hash-identical, and the applications stayed stopped during the check. The installation proof and final source inventory therefore have distinct, explicit checkpoints.

The completed numerical report retains all planned outcomes for the assigned studies, including failures and human-dependent oracle cases. Domain accountability does not imply that the member personally executed the recorded automated work.

| Study | Recorded | Planned |
| --- | --- | --- |
| Study A Supplied Information Diagnosis | 72 | 72 |
| Study C Packing and Repair Ablations | 48 | 48 |

## Current limits

The experiments measure evidence coverage and the combined pipeline separately from the packing ablation. Device-wide performance comparisons need additional machines and measurements.

Use the fixed-result analysis to inspect omitted conditions, unnecessary passages and false relevance decisions. Extend device and workload measurements separately, and obtain independent relevance/support judgments before broader quality claims.

## Week 9 goals

- Analyze packing omissions and false relevance decisions from fixed results.

- Extend independent relevance/support judgments without tuning on final outputs.

- Measure additional devices and workloads separately from answer quality.

## Code and evidence

Module paths: retrieval/source_spans.py; retrieval/chat.py; generation/evidence_budget.py; evaluation/memory_v2/sources.py.

Codex performed the implementation, automated checks and recorded local browser verification through the shared project workflow. The eight reports follow the original accountable domains; member submissions and independent human reviews retain their own execution records.

Fresh isolated CPU installation. Fresh directory, virtual environment and dependencies on the existing Windows host; real CPU retrieval and mock answers. This earlier installation checkpoint contains 515 selected files.

evidence/week08-memory-v2/20260921/portable/summary.json

SHA256 3f0e5edb523bbae1e9fa7ea813928f125d76db843abe77fe2a9ed129faa33b02

Actual portable CPU HTTP workflow. Two persisted textbook turns, cancellation, source identities and history after sign-in on the separate database; explicit mock answering.

evidence/week08-memory-v2/20260921/portable/http-attempt1.json

SHA256 ee7c79530f7ebfcfed4f44322bffd8143b75a65219f2121f725820d69b7412f6

Final public source and resource parity. 514 selected source and configuration files match the portable public tree; all 80 resources match the preserved bundle, including 30 model and tokenizer files also compared with main paths

evidence/week08-memory-v2/20260921/portable/source-parity-release-final-20260922.json

SHA256 66cb3799d646b1b9d52dea9f442538f6ca9560b44db9d7ebcc9419c6705c0ccb

Versioned reliability implementation checkpoint. Exact policy/source hashes and focused software checks. Counts overlap the final gate; this record supplies no new formal or human-quality result.

evidence/week08-memory-v2/20260921/answering/implementation-final-verification.json

SHA256 a84f9e6365a181a10d4f10babdf9b298dac4464d42609bb1ff617aaa1cde74c3

Registered automatic study results. 552 scheduled requests across 18 arms; all generation and offline judgment outcomes retained; independent human ratings zero

evidence/week08-memory-v2/20260921/formal/public-results.json

SHA256 b470c9c5df020d3dd7dae9625fdfabc82afdf60569f33a3d62c84a5ea340e7f6

Actual blank blinded review export. Two randomized 552-row reviewer slots; zero completed or imported ratings

evidence/week08-memory-v2/20260921/formal/review-export-verification.json

SHA256 9f9f675f3f00a30b7e64745be7d9ef0f2d2786295fb2cbdbc5a6a43041a75b5a

Measured formal request and model attempt latency. All 552 scheduled identities; excludes prior CPU candidate preparation and memory preparation; no HTTP queue timing claim

evidence/week08-memory-v2/20260921/formal/public-latencies.json

SHA256 cd36c029d024ef39a64ab5ab3a734c608d7851896832cdb889618246eff77473
