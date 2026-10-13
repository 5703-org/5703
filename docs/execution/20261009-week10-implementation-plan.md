# COMP5703 Week10 Implementation Plan

Personalised Learning Assistant | Proposed execution plan | Prepared 9 October 2026

## 1. Week10 outcome and scope

The minimum shipping milestone is a reproducible, source-grounded tutoring path with reliable checker contracts, a versioned contextual-retrieval pilot, measurable routing and latency improvements, and a private release evidence pack. Extend the working system after an audit; preserve E5-small-v2, BM25, RRF, MiniLM and historical Gemini experiments as controlled baselines. Week10 changes belong to new Week10 versions. This plan covers COMP5703 only.

The main research question remains the joint design of pedagogical text and source-control behaviour in the established tutoring A/B/C/D conditions. These infrastructure tasks enable that study. Preserve the exact existing A/B/C/D definitions, seven formal research tracks, 108 task identifiers and 60 acceptance identifiers. Week10 identifiers below are additional planning labels, not replacements.

P0 items W10-01 to W10-06 and W10-10 form the core path. W10-07 is a bounded comparison if the core is healthy. W10-08 and W10-09 are stretch prototypes or study specifications. A negative or inconclusive experiment is a valid deliverable. Finishing every new framework this week is not the release criterion.

## 2. Evidence baseline and present blockers

- Corpus baseline: approximately 10,594 OpenStax text chunks, E5-small-v2 384-dimensional vectors, BM25/RRF/MiniLM, PostgreSQL/pgvector and FastAPI. Query preparation, learning memory, eight learning modules, claim-level support/citation checking and repair already exist to varying degrees. Audit implementation and tests before labelling work as new.
- The 12 already-seen development questions gave E0 exact match 7/12 and token F1 0.6389; Dense 6/12 and 0.6111; Hybrid 6/12 and 0.7083 with the same Gemini teacher. Token F1 is overlap, not accuracy. This small development result does not establish general RAG benefit or harm.
- A separate 12-query test with one designated support item per query gave Recall@5 10/12 for R0 Dense and R2 Hybrid plus reranking. These labels are not exhaustive relevant-evidence gold, so the result cannot establish complete retrieval recall.
- The real single-pair Gemini prewarm comparison was 18.7143 to 12.1465 seconds for send-to-full-result and 30.2040 to 29.4479 seconds for launch-related end-to-end timing. Q1/Q2 from different workers were 9.0477 and 12.1468 seconds. These are observations, not p95, a same-worker paired estimate, or proof that all answers meet 5–10 seconds.
- Haiku teacher integration exists. Checker strict-schema grammar was too large; an isolated JSON-mode attempt passed, then a 4096-token run truncated and an 8192-token run had an invalid contract. A Haiku-teacher/Gemini-checker run failed because ordinary Q&A lacked `attempt_evaluation_ok`. Full Haiku operation is still blocked.
- Preserve the Week09 Source04 snapshot and its cumulative 1,489 historical files, full pack, eight owner packs and nine reports. Do not rewrite historical experiments or silently relabel them.

## 3. Planned owners and independent review

Assignments are proposed Week10 responsibilities, not assertions about completed contributions.

| Owner | Primary responsibility | Cross-review responsibility |
| --- | --- | --- |
| Xianshu Zhang | Integration, research protocol, gates and release | Dataset split and A/B/C/D consistency |
| Hongle Yang | Textbook parsing, contextual metadata, parent-child evidence, visual provenance | Retrieval bad cases and multimodal evidence |
| Chengzhou Liu | Retrieval comparisons, CPU/GPU profiling and reranking | Performance methodology and version isolation |
| Sijin Lu | Generation, checker contracts, repair and prompts | Router escalation and teacher adapters |
| Pengyuan Xia | Memory, goals, BKT and review feedback | Personalisation isolation and pedagogy |
| Zeping Liao | Backend, database, jobs, auth, migrations and caches | Checker API contracts and recovery |
| Baiqing Huang | Frontend learning flow, browser timing and evidence display | Cancellation and citation usability |
| Chong Zhang | Datasets, independent machine evaluation, security and reproducibility | Release evidence and regression failures |

## 4. Sequence and dependency gates

Day 1–5 is an example dependency-aware sequence, not a promised calendar or a claim that all work fits those dates.

- Day 1: W10-01 audit and protocol; W10-02 candidate pool and pilot; W10-03 contract fixtures; W10-06 stage tracing. Freeze budget, metrics, split rules and exact baseline versions before comparisons.
- Day 2: Resolve W10-03 blockers; W10-04 contextual metadata and parent-child pilot; W10-06 exact/HNSW and prewarm profiling. Dataset construction proceeds independently.
- Day 3: Compare W10-04 variants; implement W10-05 rule-based routing in shadow mode; start W10-07 only after contract and resource gates pass.
- Day 4: Integrate the best evidenced small change; run isolated browser, recovery and security checks. W10-08/W10-09 proceed only if core work has no blocking failure and approved budget remains.
- Day 5: W10-10 runs the preregistered held-out comparison and rollback drill; assemble the report, owner evidence and A/B/C/D study handoff. Unfinished stretch work is explicitly carried forward.

Critical path: W10-01 → W10-02 and W10-03 → W10-04/W10-05 with W10-06 → W10-10. Contextual retrieval can be piloted without changing the teacher. A checker failure blocks promotion of a new teacher and adaptive publishing, but does not block retrieval-only experiments.

## 5. Work items

### W10-01 Audit the baseline and preregister comparisons P0

**Owner:** Xianshu Zhang. **Contributors:** all owners supply code/test status; Chong Zhang independently reviews. **Depends on:** existing repository and Week09 evidence.

**Actions:** Record baseline commit, corpus hash, chunker/embedding/reranker versions, teacher/checker roles, prompts, database version, hardware and run commands. Audit existing features as implemented-and-tested, implemented-but-unverified, partial or absent. Read approved project configuration locally without exposing secrets. Record the remaining approved budget B and per-run estimates before paid calls. Link each Week10 item to existing task and acceptance IDs without renumbering. Reuse established tutoring A/B/C/D definitions and the original seven research tracks.

**Done evidence and acceptance:** A versioned manifest, current blocker list, traceability crosswalk and preregistration are reviewed before held-out tests. Each claim has a source/run identifier and each comparison isolates a named variable. Baseline can be reproduced in an isolated environment.

**Fallback:** If a baseline cannot be reproduced, ship a precise environment/code diagnosis and retrieval-only or contract-only results; do not claim a model win or alter a default.

### W10-02 Build a concept-separated evaluation pool P0

**Owner:** Chong Zhang. **Contributors:** Hongle Yang for source spans; Pengyuan Xia for learning cases. **Reviewer:** Xianshu Zhang. **Depends on:** W10-01.

**Actions:** Prepare a 200-question candidate pool covering factual definitions, explanations, multi-turn reference resolution, cross-section questions, numerical/formula cases, insufficient evidence and pedagogical interactions. Use public textbook content and synthetic learner records. Store question ID, concept family, book/section/page/source hash, answer rubric, expected evidence sets, answerability, error categories and label provenance. Keep all paraphrases and conversations from one concept family in one split; exclude the 12 seen development questions from held-out claims. First pilot 24 candidates across categories. After the pilot, freeze final validated N, split counts, model-call repetitions and cost from the approved budget; do not present 200 as an already verified test set.

Use independent AI review plus reference-grounded adjudication now, as requested. Mark labels `AI-reviewed`, `disputed`, `reference-checked` and `pending-human-review` accurately; preserve reviewer model/version and disagreements. AI agreement is not human gold. Separate partial designated-support labels from evidence sets that have been checked for completeness. Keep disputed cases for diagnosis but outside confirmatory aggregates. Seal test inputs and labels from prompt/threshold tuning.

**Done evidence and acceptance:** Versioned JSONL/CSV candidate pool, split manifest, leakage checks, source-span validation, label-provenance report and accepted/disputed/excluded counts. Retrieval and answer metrics expose their exact denominators and label coverage. Final sample sizes and noninferiority margins are fixed before the held-out run.

**Fallback:** Publish the validated subset and limitations if the full pool cannot be checked. Use the pilot for feasibility only; defer optimisation and strong conclusions rather than inflate sample counts.

### W10-03 Repair checker contracts and measure checker errors P0

**Owner:** Sijin Lu. **Contributors:** Zeping Liao for API validation; Pengyuan Xia for practice scope. **Reviewer:** Chong Zhang. **Depends on:** W10-01; W10-02 for measured error rates.

**Actions:** Extend existing claim-level checking. Separate minimal response schema from semantic validation. Define schema version, request scope and conditional required fields: ordinary textbook Q&A must not require practice-attempt evaluation fields; practice evaluation must require its own result contract. Explicitly model supported, contradicted, insufficient and citation-error outcomes, without forcing unrelated fields. Add fixtures for ordinary Q&A, practice feedback, no evidence, wrong citation, contradictory sources, empty claims, malformed JSON, missing fields, truncated output, provider refusal, timeout and repair exhaustion. Reproduce the Haiku strict-schema/JSON-mode/truncation failures and missing `attempt_evaluation_ok` hybrid failure. Compare bounded output-token budgets and prompt/schema sizes empirically rather than assuming 8192 solves correctness.

Measure false blocking of supportable correct answers, missed unsupported/contradicted claims, citation error detection, parser/contract failure, repair success, extra latency and total cost against source-grounded AI-reviewed surrogate labels. Make local repair and retrieval escalation error-specific, bounded and observable. Never convert parser failure into PASS. Any new NLI/RAGChecker component remains an offline diagnostic until validated; preserve the current checker baseline. RAGChecker and Reason and Verify offer evaluation ideas, not evidence of performance on this corpus [S6, S7].

**Done evidence and acceptance:** Contract fixtures all pass; no ordinary-Q&A/practice scope confusion; raw failure reproductions and corrected runs are retained. Error rates include denominators and intervals, with label limitations. New teacher promotion is blocked if integration contracts or safety-critical citation fixtures fail.

**Fallback:** Keep the historically working Gemini path or disable the experimental adapter privately. Return an explicit error/insufficient-evidence state when checking fails; do not bypass verification to improve latency.

### W10-04 Pilot contextual and parent-child retrieval P0

**Owner:** Hongle Yang. **Contributors:** Chengzhou Liu and Zeping Liao. **Reviewer:** Sijin Lu. **Depends on:** W10-01 and W10-02.

**Actions:** Audit headings and chunk boundaries on the existing corpus. Distinguish semantic book/chapter/section titles from generated page IDs and administrative labels; never insert generated page IDs into semantic query expansion. Preserve original chunk text and stable citation anchors. Create separate versioned contextual text and parent-child maps. Start with deterministic heading context; optionally test short AI-generated context only with source constraints, provenance and approved cost. Expand parents/adjacent passages within a measured token budget and deduplicate overlapping evidence.

Run sequential ablations on the same validated query set: original E5 hybrid baseline; headings-only contextual corpus using the same E5; then parent expansion. Hold retrieval model, teacher and prompts fixed initially. Record re-embedding cost/time, corpus coverage, Recall@5, MRR, nDCG@10 where relevance labels are sufficient, context tokens, supportability and latency. Anthropic Contextual Retrieval motivates this pilot; its reported gains do not become project targets [S1].

**Done evidence and acceptance:** Versioned chunk/context manifest, stable source anchors, successful rollback to the 384-D baseline, verified no-ID-query-pollution fixtures, and ablation results. Promotion requires preregistered quality noninferiority and a documented quality/latency advantage; a larger context alone is not success.

**Fallback:** Retain original vectors and only source-display improvements if contextualisation reduces recall, adds unsupported context or exceeds cost. Pilot a source-balanced subset before committing to full re-embedding.

### W10-05 Add low-cost adaptive routing around existing query preparation P0

**Owner:** Chengzhou Liu. **Contributors:** Sijin Lu and Baiqing Huang. **Reviewer:** Pengyuan Xia. **Depends on:** W10-03/W10-04; initial shadow work may use the baseline.

**Actions:** Audit query preparation first. Add an explainable rule/score router in shadow mode: simple source-grounded definitions use a measured lightweight retrieval path; explanation/cross-section requests use hybrid plus reranking; multi-turn ambiguity requests clarification or reference resolution. Insufficient evidence escalates retrieval or returns uncertainty. Avoid an extra LLM call at every decision. Treat multi-query expansion as a separate experiment. Keep minimum source checks on every textbook claim. Sweep TopK, rerank depth, support thresholds and context/token budgets on development data; log the chosen route and reason. Freeze chosen settings before the held-out test.

**Done evidence and acceptance:** Route decision log, boundary-case fixtures, offline cost/quality comparison and a feature flag. Report route-level answer quality, unsupported claims, false blocking, escalation frequency, model-call count and p95. Promotion requires quality gates and documented latency/cost benefit; evaluate disagreements with the full baseline path.

**Fallback:** Route uncertain cases to the established hybrid path. If routing is unreliable, keep shadow-only telemetry and postpone serving it.

### W10-06 Profile latency and strengthen recovery without database replacement P0

**Owner:** Zeping Liao. **Contributors:** Chengzhou Liu for CPU/GPU; Baiqing Huang for browser timing. **Reviewer:** Chong Zhang. **Depends on:** W10-01; joint quality review uses W10-02/W10-03.

**Actions:** Instrument browser submit, job admission, query prep, dense/BM25, fusion, rerank, generation first token, full generation, checker/repair, persistence and final browser publication. Preserve request/job/attempt IDs. Compare exact pgvector retrieval and HNSW with execution plans, filter behaviour, index build cost and approximate-neighbour overlap versus exact results; separately report source relevance metrics. Check installed pgvector support before using iterative scans. Official pgvector documentation notes filter/ANN interactions and dimension limits; do not assume an index improves this 10k-chunk corpus [S8].

Measure dense/BM25 concurrency, encoder/MiniLM prewarm, connection reuse, bounded retries and evidence caches separately. Cache keys must include corpus/model/prompt/schema versions and correct user/course scope; do not globally cache personalised answers. CUDA experiments apply to non-LLM local embedding/reranking only, with CPU fallback and startup/memory measurements. External teacher API latency is not a CUDA speedup. Preserve timeout cancellation, idempotency, retry deduplication and job recovery; test browser refresh/retry and process interruption with synthetic records in isolation.

**Done evidence and acceptance:** Stage traces and raw browser timings, cold/warm groups, all-attempt and successful-attempt p50/p95, timeout/failure counts, cache hit/miss results, concurrency/resource measures and cost per successful answer. No duplicate chargeable model job from a duplicate client retry in deterministic integration tests. Apply the latency and quality gates in Section 6.

**Fallback:** Keep exact retrieval/CPU execution if HNSW/GPU gains disappear after warm/cold and quality controls. If 5–10 seconds is not achieved, release the reliable smaller improvement with a measured bottleneck report; do not hide checker time or failed attempts.

### W10-07 Run bounded teacher and retrieval-model comparisons P1

**Owner:** Sijin Lu for teachers; Chengzhou Liu for embedding/reranker. **Contributors:** Zeping Liao for adapters and Hongle Yang for corpus versions. **Reviewer:** Chong Zhang. **Depends on:** W10-02/W10-03 and an approved budget/resource gate.

**Actions:** Compare teacher candidates sequentially on the same controlled inputs: Claude Haiku 5.5, OpenAI GPT-6 Luna and the already successful direct DeepSeek `deepseek-flash` path. Use provider-specific IDs: the existing OpenRouter Haiku path uses `anthropic/claude-haiku-5.5`; Anthropic direct uses `claude-haiku-5-5`. OpenAI direct uses `gpt-6-luna`, while OpenRouter uses `openai/gpt-6-luna`. Reuse the authorised working provider routes. Snapshot actual requested/returned model IDs and capabilities for each run; an alias check must not gratuitously block the existing successful DeepSeek path [S10–S12]. Keep the historical Gemini teacher and a known-working checker as role-separated references; evaluate each teacher/checker combination only after its own contracts pass. Record provider/model, reasoning mode, output budget, tokens, retries, price snapshot, total cost and answer/checker quality. Do not silently switch a production default.

For retrieval, Qwen3 Embedding/Reranker 0.6B is the first optional new-model pilot; retain MiniLM as reranker control. Qwen3 models have Apache 2.0 licensing; the 0.6B embedding supports up to 1024 dimensions [S2]. Jina v5-text-nano (239M, up to 768-D) and reranker v3.5 (0.6B listwise) are research candidates under CC BY-NC 4.0; commercial deployment requires licence review [S3, S4]. Gemini Embedding 2 supports multimodal inputs and 128–3072-D outputs and is a later pilot, not a mandatory Week10 migration [S5]. Fix the corpus/context treatment while changing embedding; then fix embedding while changing reranker. Use a small compatibility/resource pilot before full re-embedding.

Every candidate needs its own corpus/vector version, matching document/query encoder, normalisation/task settings, dimension assertion and rollback pointer. Equal dimensions do not mean equal embedding spaces. Never cross-search E5 384-D documents with another encoder. For pgvector indexes, validate datatype/dimension limits: 3072-D is not a drop-in `vector` HNSW configuration [S8].

**Done evidence and acceptance:** At least a bounded compatibility report or one completed controlled comparison; explicit pass/fail/inconclusive decision. Promote only with contract success, quality gates, affordable measured latency/resource use and licence compatibility. Negative results stay in the evidence pack.

**Fallback:** If access, schema, hardware, licence or cost blocks a candidate, record the blocker and keep the current baseline. Do not create credentials, buy a licence or exceed budget to finish a comparison.

### W10-08 Prototype interpretable personalisation with BKT P1 stretch

**Owner:** Pengyuan Xia. **Contributors:** Zeping Liao and Baiqing Huang. **Reviewer:** Chong Zhang. **Depends on:** audited memory/practice event contracts and W10-03; core release must be unblocked.

**Actions:** Map existing practice events to concept IDs; deduplicate attempts and distinguish hints, skipped questions and correctness. Build a small BKT prototype with explicit prior/learn/guess/slip assumptions; label its mastery estimate as a model estimate. Feed one explainable recommendation into the existing goals/review flow with a link to the source concept. Use synthetic learners, sparse-history fallback and reset/version controls. BKT is a practical interpretable baseline; DKT training is deferred until adequate longitudinal data and an evaluation protocol exist [S9].

**Done evidence and acceptance:** Event-to-concept mapping, deterministic update fixtures, tenant isolation tests, a reproducible synthetic learning→practice→feedback→mastery→review demonstration and explanation of cold-start assumptions. No claim of improved learning outcomes from a demo.

**Fallback:** Keep rule-based review suggestions and existing memory if events are incomplete or the model is poorly calibrated. Deliver the event contract and study design rather than unvalidated mastery scores.

### W10-09 Scope multimodal and prompt-optimisation pilots P1 stretch

**Owner:** Hongle Yang for visual evidence; Sijin Lu for prompt optimisation. **Contributors:** Pengyuan Xia and Baiqing Huang. **Reviewer:** Xianshu Zhang. **Depends on:** W10-02/W10-04 and a healthy core release.

**Actions:** Select a small source-balanced set of diagram/formula questions with image/page anchors and text evidence. Specify a text-only control, caption/OCR control and one authorised multimodal candidate; report retrieval and answer errors separately. Gemini Embedding 2 is an available option, not proof of visual reasoning quality [S5]. No full-corpus multimodal rebuild is required.

Only after sufficient concept-separated labelled data exists, specify or run a bounded DSPy GEPA pilot for one prompt component. Preserve training/development/test isolation, optimiser traces, budget and unchanged held-out labels. Compare with the original prompt; do not optimise all generation, rewrite and checker prompts at once. Official DSPy documents GEPA as an optimiser; this establishes an implementation route, not a guaranteed improvement [S13].

**Done evidence and acceptance:** A pilot specification with source examples, split rules, metrics, cost cap and stopping condition; run results only if gates permit. Final prompt selection never uses the sealed test set.

**Fallback:** Defer both pilots with a precise entry checklist. ColBERT/late interaction, GraphRAG and a new graph database remain P2 research backlog, pending evidence that simpler retrieval fails on the required concept relationships.

### W10-10 Integrate the minimum milestone and release evidence P0

**Owner:** Xianshu Zhang. **Contributors:** all owners. **Independent machine review:** Chong Zhang; frontend sign-off evidence from Baiqing Huang. **Depends on:** core items or their documented safe fallbacks.

**Actions:** Integrate only evidence-supported changes behind reversible flags. Run held-out comparisons after configuration freeze; perform source-link browser checks, cancellation/retry/recovery, user isolation, practice/memory/admin regressions and rollback in an isolated environment. Carry forward Week09 unfinished security, recovery, practice, memory/admin and seven research tracks with original IDs, status, owner and evidence links. Do not mark them complete because Week10 has a new focus. The traceability crosswalk must name actual existing identifiers from the repository; do not invent missing IDs.

Preserve tutoring A/B/C/D conditions and show which Week10 changes are shared infrastructure and which become independently controlled research factors. Report pedagogical text quality, source-control behaviour and factual support separately. AI-assisted review is allowed; recruitment/human review is pending until separately requested.

**Done evidence and acceptance:** English repository plan and report, current owner packs, private demo/run instructions, test logs, raw metrics, experiment manifests, budget ledger, change/rollback notes and retained failure examples. Release status is explicit: ready, ready with limitations or blocked. The minimum milestone may ship with the original encoder/teacher if new candidates do not pass.

**Fallback:** Keep the last reproducible private build, deliver the blocker/failure diagnosis and assign the remaining work. No public deployment or default-model promotion is implied by this plan.

## 6. Measurement and release gates

### Quality and checker gates

Before seeing held-out results, preregister the primary source-grounded answer rubric, the acceptable noninferiority margin, critical-error rules, retrieval relevance definitions, checker false-block/miss definitions and denominators. Choose margins after the pilot using task importance and achievable precision, not after observing a candidate win. Separate token F1 and exact match from semantic correctness, citation validity and pedagogical quality. Report source-grounded answerability and refusals by category. Use paired, concept-family-aware comparisons and confidence intervals; unresolved label disputes or wide intervals mean inconclusive, not noninferior. Critical contract, citation fabrication and cross-user leakage fixtures must pass.

Checker false-block rate is the proportion of reference-supportable correct answers incorrectly blocked among such answers; missed-error rate is the proportion of labelled erroneous/unsupported cases accepted among such cases. Report claim-level and answer-level results separately and disclose that current labels are AI/reference-reviewed surrogate labels. Retrieval metrics use the exact label coverage: designated-support hit rate is not exhaustive Recall@K; nDCG requires explicit binary or graded relevance judgements and a stated gain definition.

### Latency gates

The product engineering target remains 5–10 seconds for a completed usable answer under an explicitly declared workload. It is a target until measured. The prewarm experiment aims at at least 30% lower warm browser-submit-to-final-publication p95 versus the locked same-teacher baseline, conditional on preregistered quality noninferiority and no unacceptable failure/cost increase. This is a prospective acceptance target, not an extrapolation from the earlier single pair.

Before paid measurement, pilot the runtime/cost and freeze workload, concurrency, repetitions and timeout. A practical initial proposal is 100 attempts per compared configuration across 25 diverse queries with repeats if approved budget permits: 100 attempts provide only about five upper-tail observations, while diverse queries reduce the risk of one repeated question representing the whole workload. Repeated observations are correlated; adjust sample sizes and uncertainty estimates using the pilot, concept/query clustering and precision or power needs. These numbers are a feasibility starting point, not hard release thresholds or a claim of sufficient statistical power. If infeasible, preregister a smaller exploratory run and label p95/quality conclusions as uncertain. Randomise/interleave paired configurations to control provider load; separate cold start, warm runs, cache misses and hits. Report first-token and full-publication timing separately. Include all submitted attempts, successful-only latency, failure/timeout rate and time-to-terminal-state; do not compute success-only p95 as if it covers all user waits. Unfinished timed-out requests are censored or reported at timeout, never silently omitted. Launch/prewarm/startup time stays visible as a separate cost.

### Budget and preservation gates

All paid calls stay within the confirmed remaining budget B, including retries, checker, AI evaluation, optional context generation, re-embedding and optimiser calls. Record estimated and actual cost per run and stop before exceeding B. Resource or licence checks can block a candidate without blocking the core. Preserve real data, credentials and historical experiments. Use synthetic records and isolated test environments. No permanent deletion, credential creation/change, security-permission change, new persistent access, public deployment or budget expansion is part of the plan.

## 7. Deliverables and repository handoff

Suggested new locations are `docs/week10/implementation_plan.md`, `docs/week10/evaluation_protocol.md`, `docs/week10/release_report.md`, `artifacts/week10/manifests/`, `artifacts/week10/evaluation/` and `artifacts/week10/owner_packs/`. Resolve actual repository conventions during W10-01 and add new files without overwriting Week09 evidence.

The release report should lead with the shipping decision, measured changes and open blockers, followed by the fixed protocol, ablation results, error analysis, cost and rollback instructions. Each owner pack links code changes, commands, fixtures and raw evidence. Retain failed Haiku runs, failed/rejected candidates and label disagreements. A complete audit trail is more valuable than an unsupported claim that every advanced technique was built.

## 8. Verified external references

Checked against official documentation or author-maintained sources on 9 October 2026. Recheck model access, aliases, capabilities, licence and pricing at execution time.

- [S1] Anthropic, Contextual Retrieval: https://www.anthropic.com/engineering/contextual-retrieval
- [S2] Qwen3 Embedding/Reranker official repository and model details: https://github.com/QwenLM/Qwen3-Embedding
- [S3] Jina v5-text-nano model card: https://jina.ai/en-US/models/jina-embeddings-v5-text-nano/
- [S4] Jina reranker v3.5 model card: https://jina.ai/models/jina-reranker-v3.5
- [S5] Gemini Embedding 2 model documentation: https://ai.google.dev/gemini-api/docs/models/gemini-embedding-2
- [S6] RAGChecker author-maintained repository: https://github.com/awslabs/RAGChecker
- [S7] Khan, Rodriguez and Queudot, Reason and Verify, PMLR 318, 2026: https://proceedings.mlr.press/v318/khan26a.html
- [S8] pgvector official repository, indexes/filtering/dimensions: https://github.com/pgvector/pgvector
- [S9] pyBKT author-maintained implementation: https://github.com/pyBKT/pyBKT
- [S10] Anthropic Haiku 5.5 availability and API ID: https://www.anthropic.com/claude-haiku-5-5
- [S11] OpenAI GPT-6 Luna model documentation: https://developers.openai.com/api/docs/models/gpt-6-luna
- [S12] DeepSeek model-list API: https://api-docs.deepseek.com/api/list-models/
- [S13] DSPy official optimiser guide including GEPA: https://dspy.ai/learn/optimization/optimizers/
- Provider-specific IDs: https://openrouter.ai/anthropic/claude-haiku-5.5 and https://openrouter.ai/openai/gpt-6-luna

