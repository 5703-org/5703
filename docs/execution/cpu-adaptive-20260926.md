# CPU backend and retrieval-budget experiment

Date: 26 September 2026. Executor: Codex. Accountable retrieval owner: Chengzhou Liu. The [registered protocol](teaching-performance-protocol-20260926.md) defines the quality gate and keeps ordinary textbook answering and the original E0/E1 conditions intact.

## Primary-source review

The following pages were checked on 26 September 2026. Their reported speedups describe their own experiments. Local measurements below determine this project's decisions.

| Primary source | Relevant finding | Project decision |
| --- | --- | --- |
| [BM25S, arXiv:2407.03618v1](https://arxiv.org/abs/2407.03618v1) | The implementation moves lexical scoring work into an index and stores sparse contributions. | Build exact lexical statistics using the existing tokenizer, k1=1.5, b=0.75 and tie rule. Compare every score and ordered ID with the existing implementation. Visibility changes require new matching statistics. |
| [RAGO, arXiv:2503.14649v2](https://arxiv.org/abs/2503.14649v2) | Performance varies with the structure of the retrieval/generation workload; the paper models stages and serving choices. | Measure index construction, query encoding, candidate retrieval, reranking and online answer/check phases separately. Model-stage speed does not establish browser latency. |
| [SAGE, CoDIT 2026 author version](https://arxiv.org/html/2608.08237v1) | Offline retrieval features predict a query-specific budget without an online LLM policy call. Section IV describes RandomForest, while Section V specifies Adam optimization; those training descriptions need clarification for reproduction. | Use an independently specified deterministic threshold grid fitted on development groups. Compare 5, 10 and 20 rerank candidates. Preserve 20 candidates in shadow mode and for complex or weak-evidence queries. This implementation is not a reproduction of SAGE. |
| [SpecCache, ACL 2026](https://aclanthology.org/2026.acl-long.859/) | A speculative model's internal representations guide target-model KV recomputation. | Keep this as a research direction. The existing remote provider API exposes no internal target-model KV state. |
| [DeepSeek context caching](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/) | Reused prefix units may hit the provider's cache; cache-hit and cache-miss token counters are returned. Hits remain best effort. | Keep stable trusted prompt prefixes and record actual provider counters. Never infer a hit from repeated text or treat provider cache reuse as answer reuse. |
| [Sentence Transformers inference efficiency](https://sbert.net/docs/cross_encoder/usage/efficiency.html) | CPU backend speed and ranking quality depend on the model, data and batch size. Raw ONNX outputs must use the original activation to match CrossEncoder semantics. | Compare pinned MiniLM PyTorch, ONNX FP32 and dynamic INT8 locally. Preserve the checkpoint's identity activation, exact tokenizer and 512-token boundary. Do not silently truncate or transfer the PyTorch -4.0 relevance threshold. |

## Implemented execution contract

`chat_hybrid_rerank_v1` retains its original configuration and implementation. Explicit `chat_hybrid_rerank_v2` adds `reranker_runtime` and `adaptive_policy`. Runtime fields freeze `cpu_reranker_runtime_v1`, backend, thread count, batch size, artifact path and artifact SHA-256. Experimental backends require CPU. Model revision, tokenizer, E5 identity and corpus vectors remain unchanged.

The optional [ONNX dependency lock](../../requirements-reranker-onnx.lock) pins the exporter and runtime. [Export code](../../scripts/verify/export_cpu_reranker.py) consumes the already downloaded checkpoint, creates a new directory, records source/config/tokenizer hashes, checks both graphs and records export library versions. It exports FP32 with opset 17 and a separate dynamic QInt8 graph with per-channel weights and reduced range. Each exported artifact has a content hash; a changed manifest, graph, tokenizer or checkpoint fails loading.

[CPU execution](../../retrieval/cpu_backend.py) uses only `CPUExecutionProvider`, explicit intra-operation threads and one inter-operation thread. PyTorch thread changes are locked and restored after prediction. Models are cached by checkpoint, runtime and artifact identity. Explicit warmup records loading and initial execution without a paid model call. There is no answer cache or fallback to a different backend.

The original `-4.0` threshold remains provisional for its existing PyTorch checkpoint. ONNX FP32 and INT8 policies record unavailable threshold calibration. Their score crossings against -4.0 are diagnostic comparisons, not certification that this cutoff transfers to either backend. The default policy remains unchanged.

## Adaptive budget definition

[The frozen case catalogue](../../configs/retrieval/cpu_replay_cases_20260926.json) contains 12 development and 12 held-out concept groups. The cases are developer-authored probes for numerical/ranking stability. They contain no independent relevance or supported-answer labels.

The [policy fitter](../../retrieval/adaptive.py) enumerates declared relative RRF gap and lexical-overlap thresholds on development rows. It minimizes the summed rerank budget subject to retaining every development reference top-five chunk. Ties favor more conservative thresholds. Complex, multi-part or conditional questions and weak lexical matches keep budget 20. The fitted policy stores development groups, the exact development-data hash and `retrieval_proxy_only` quality status. Holdout evaluation rejects overlapping groups. Policy inference adds zero LLM calls.

Shadow mode records the proposed budget and keeps all 20 candidates. Explicit experimental mode records the candidate IDs removed by the budget before reranking. Neither mode declares source support, and textbook retrieval remains required. Supported-answer noninferiority, additional false refusals, wrong citations and hint leakage are evaluated separately before any default change.

## Reproduction

From the project root, with the optional CPU dependencies installed:

```powershell
$env:PYTHONPATH = '.;backend'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
python -m scripts.verify.export_cpu_reranker --output artifacts/reranker-onnx/NEW_EXPORT
python -m scripts.verify.cpu_backend_replay --bundle PATH_TO_OFFICIAL_CORPUS_BUNDLE --artifact artifacts/reranker-onnx/NEW_EXPORT/manifest.json --output evidence/teaching-performance/NEW_REPLAY
```

Both commands require new output directories, preserving prior attempts. The replay verifies the bundled data hash, every active chunk text hash, release membership and vector dimensions. It uses the original 10,594 vectors, fresh E5 CPU query vectors, exact lexical scores, RRF and the four declared rerank arms. Passage text, title, section and physical pages are recorded alongside ranked IDs and scores. It performs no PostgreSQL query and makes no answering-model calls. Runtime visibility and publication checks belong to the product regression.

## Current execution record

The first focused test run passed 28 checks and encountered one temporary-directory permission error. A new project-local temporary directory allowed all 29 focused checks to pass. Adding the existing interactive-reranking compatibility suite produced [33 passing checks](../../evidence/teaching-performance/20260926/cpu-focused-tests.txt). The first replay stopped before any retrieval because an optional process-memory library was absent; the replay now uses the native Windows working-set API.

The [fresh offline replay](../../evidence/teaching-performance/20260926/cpu-replay-02/summary.json) completed all 24 cases for all four backend/thread arms. Every query produced exactly the same lexical scores and ordered top-50 IDs as the original BM25 implementation. The corpus data hash remained unchanged. The first execution per backend is recorded separately; the table covers the remaining 71 observed warm executions per arm on this shared Windows host.

| CPU arm | Warm median / p95 rerank time | Reference ordered top-five matches | Mean top-five set retention | Crossings of the provisional PyTorch cutoff |
| --- | --- | --- | --- | --- |
| PyTorch, 16 threads | 217.59 / 229.59 ms | 24/24 | 100% | 0 |
| PyTorch, 2 threads | 752.10 / 802.51 ms | 24/24 | 100% | 0 |
| ONNX FP32, 2 threads | 472.93 / 521.83 ms | 24/24 | 100% | 0 |
| ONNX INT8, 2 threads | 266.44 / 286.20 ms | 11/24 | 95.83% | 5 |

These observations support retaining the existing backend on this host. Two-thread ONNX is faster than two-thread PyTorch in this replay; the existing 16-thread PyTorch arm is faster than both measured ONNX arms. INT8 changes scores and ranking, and its five cutoff crossings reinforce the requirement for its own relevance calibration. These are reranking measurements, with retrieval and model loading reported separately. They establish no browser p95 improvement or answer-quality gain.

The development fit selected the full budget of 20. The frozen policy then retained all five reference chunks for 12/12 held-out groups, proposing 20 for every case. It achieved no budget reduction. [The original development hash](../../evidence/teaching-performance/20260926/cpu-replay-02/frozen-adaptive-policy.json) was frozen before held-out scoring; a [post-run exact reconstruction](../../evidence/teaching-performance/20260926/cpu-replay-02/development-reconstruction.json) verifies and preserves the complete fit input at that same hash. Future replay runs write the input directly before fitting.

Explicit configurations are available in `configs/retrieval/chat_cpu_experimental_torch16.json`, `chat_cpu_experimental_onnx_fp32.json`, `chat_cpu_experimental_onnx_int8.json` and `chat_cpu_shadow_budget.json`. Use `LOCAL_MODEL_DEVICE=cpu` with these CPU-only configurations. The default configuration remains `chat_hybrid_minilm.json`. The exported model manifest is `artifacts/reranker-onnx/20260926/manifest.json`, SHA-256 `eabe2c69591be5a15baec13a5e0c535aa5f13c6ca2b20ecea627f0eb124465a4`.

The [fixed-budget replay](../../evidence/teaching-performance/20260926/budget-replay-02/summary.json) executed 24 cases at each of 5, 10 and 20 candidates using the two-thread PyTorch arm. All 72 case/arm outcomes completed. On the 12 held-out groups, the five-candidate arm retained the entire reference top-five set in 1/12 cases and retained 61.67% of reference chunks on average. Ten candidates retained the entire set in 5/12 cases and 85% of reference chunks on average. Twenty candidates retained the entire set in 12/12 cases. This explains the conservative fitted policy. The fixed-budget measurements are diagnostic observations on a shared host; short concurrent fit-input reconstruction occurred during this run. They are not used to certify a controlled latency target. The first budget replay stopped before scoring because Windows used its default text encoding; explicit UTF-8 decoding corrected that failure, and the fresh run has its own directory.

To select an explicit configuration for a local experiment, set `CHAT_RETRIEVAL_CONFIG` to its project-relative filename together with `LOCAL_MODEL_DEVICE=cpu`, then restart the API and worker. Existing requests retain their frozen policy. Installing the optional ONNX lock and preserving both graph files beside the pinned manifest is required for ONNX execution. The ordinary configuration remains the production default throughout this study.

Default activation remains gated by the registered supported-answer noninferiority bound. A small numerical replay can establish execution and quantify score/rank drift; independent human review and learning outcomes require their own observations.

## PostgreSQL reference/cache comparison method

[The read-only comparison runner](../../scripts/verify/pg_retrieval_performance.py) uses the same 24 frozen concept groups against the isolated PostgreSQL/pgvector copy. Each query runs twice through each arm, with arm order alternating: complete per-query validation and the new epoch-validated release/query-vector cache. Both arms use real E5 CPU encoding, R2 with 20 candidates and the unchanged v1 MiniLM CPU reranker. The 96 warm observations are separate from two initial model/cache-cold observations. Those cold observations clear process-local models and caches while retaining OS file-cache and previously imported-library state.

Each transaction explicitly enables and checks PostgreSQL READ ONLY. The runner verifies that no new, dirty or deleted ORM objects remain. Measurement wrappers observe existing validation, embedding and lexical operations without changing their inputs or outputs. SQL timing, dense-query timing, release/query cache hits, ranking time and Windows working-set memory are recorded. Full candidate and reranked records are compared exactly after removing only the measured `rerank_ms` field. This comparison includes content, identities, locators, warnings, token spans and scores.

Before and after the complete schedule, the runner fingerprints documents, source assets, active release, release configuration/manifest, chunks, vector values/dimensions and invalidation token. It also hashes the four original PDF files. Connection credentials remain in the local private connection file and are excluded from evidence. The final run retains its complete measured source snapshot and hashes. These measurements cover local retrieval and reranking; HTTP queueing, answer/check calls, publication and browser display require the separate product study.

## PostgreSQL results

The [final paired result](../../evidence/teaching-performance/20260926/pg-retrieval-paired-final/summary.json) completed all 96 warm and two cold observations, with zero failures. All 48 paired candidate records matched exactly, and all 48 full reranked records matched exactly. The eight measured source files remained unchanged during execution. Database/source fingerprints and all four original PDF hashes also remained unchanged: 10,594 real vectors, each 384-dimensional, and 10,594 released chunks.

| Local stage | Reference median / p95 | Validated-cache median / p95 |
| --- | --- | --- |
| Release validation | 3,870.05 / 4,190.09 ms | 3.28 / 3.92 ms |
| Lexical retrieval | 443.38 / 669.84 ms | 9.15 / 102.60 ms |
| Full retrieval | 4,566.09 / 5,002.32 ms | 122.65 / 222.43 ms |
| Unchanged learned reranker | 214.82 / 234.74 ms | 217.87 / 236.25 ms |
| Local retrieval plus reranking and transaction overhead | 4,787.05 / 5,235.96 ms | 341.29 / 455.14 ms |

Each table cell contains 48 observations. All scheduled warm observations succeeded, so the all-observation and successful-observation distributions coincide; failed latency has n=0 and null quantiles. Warm local p95 decreased by 91.31% in this paired schedule. The registered browser end-to-end target still needs its complete queue/generation/check/publication/display measurement.

The release cache hit on 48/48 warm optimized observations. The query-vector cache hit on 24/48: each concept's first query encoded a fresh vector, and its repeat reused the same scoped identity. The dense SQL stage remained similar (median 76.17 versus 76.05 ms). The main saving comes from reusing the validated release and exact lexical index. Source invalidation and actual-hit validation remain active.

Two sequential cold probes completed in 7,676.17 ms for the reference and 5,788.50 ms for the cache arm. Their individual reports preserve model loading and full release validation; library import and OS cache state are shared, so they are reported separately from warm distributions. All stage measurements and native Windows working-set samples remain in the per-observation JSON files.

The shared measurement process's warm working set ranged from 1,606,414,336 to 1,893,535,744 bytes; its observed peak working set was 2,176,217,088 bytes. These samples include shared models, the cached release and measurement data. They do not estimate separate fresh-process memory for each arm. The measured source archive SHA-256 is `fd353bb63fbee58726c45e0954f7985d57c9bc0679905e3a3c3d98b1ca314ff3`.

The first PG attempt stopped during source-file fingerprinting because the reporter initially treated storage-relative paths as working-directory-relative paths; no retrieval observation had started. The correction resolves them under the configured isolated storage root. An earlier complete paired run retained 98 successful observations and unchanged corpus fingerprints, while a concurrent Ruff formatting pass changed the on-disk service hash. Its `source_unchanged_during_run=false` result remains recorded. The complete final run above repeated the schedule after freezing the formatted source and saved the exact [source archive](../../evidence/teaching-performance/20260926/pg-retrieval-paired-final/source-snapshot.zip).
