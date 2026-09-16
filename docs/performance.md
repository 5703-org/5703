# Local performance measurements

The product uses one durable answer worker. Concurrent browser sessions queue independent requests; the implementation does not claim parallel answer generation. Retrieval and answering measurements are separate. The 13 September installation uses real OpenStax/E5/MiniLM retrieval and real DeepSeek answering; the earlier mock observations below retain their dated scope.

## 13 September actual chat observation

The final fixed 20-case real suite records queue-inclusive HTTP observation from submission to terminal result. Median was **13.0335 seconds**, nearest-rank p95 **20.901 seconds**, minimum **3.414 seconds** and maximum **89.360 seconds**. The suite made 24 actual provider attempts within each request's shared limits; it retained 16 answers, two expected refusals, one clarification and one social response. Provider-reported usage totals 163,834 input and 8,667 output tokens. Price was not supplied by the API and cost remains null.

Evidence: [complete observations](../evidence/answering-upgrade/20260913/live-suite-attempt3.json), [source/budget review](../evidence/answering-upgrade/20260913/live-suite-attempt3-ai-review-20260913T041313Z.json). The same worker also processed research/profile work during part of this suite, including queue contention. These are measured results for this workload, with 20 observations, not an isolated provider benchmark or an SLA. The formal OpenQA/MCQ studies record their own queue/runtime/usage observations. Run large administrator studies when their additional queue load is acceptable.

## Recorded timing definitions

The later E5 instance-reuse change has a separate [resource/equivalence observation](../evidence/generation/embedding-cache-20260913/verification-report.md): eight direct reference encodes and 32 cached CUDA encodes retain identical vectors and database hits. Across the cached samples, working set increased by 8 KiB and CUDA allocation/reservation stayed constant. Reference-related allocation remained after its phase. This short process observation is not a single-model footprint, a long-duration stability test or a speed comparison; the earlier chat/research timings describe the pre-cache runtime.

Current responses include `timing_scope=worker_execution_before_answer_insert_v1`. Values are measured milliseconds, with the following boundaries:

| Field | Measured interval |
| --- | --- |
| `preparation_ms` | Worker request loading, query preparation and source assembly before generation, excluding the actual retriever call |
| `query_preparation_ms` | The deterministic query-preparation subset of `preparation_ms` |
| `retrieval_ms` | Actual retriever call, including release/source integrity checks, query encoding and database search; zero for an intentional bypass or valid evidence reuse |
| `generation_wall_ms` | Generation-service wall time including configured mock delay, prompt construction, attempt callbacks, provider work and response validation |
| `generation_ms` | Sum of adapter-measured attempt computation durations; the local mock observations are 0–1 ms. Generation-service work outside the adapter is excluded |
| `total_ms` | Worker execution through the start of answer insertion; final database commit, queue time and HTTP polling are excluded |

The older request trace field `preparation_ms` retains its original aggregate meaning (all input preparation including retrieval). New `trace.stage_timing` gives the separately measured stages. Existing response/trace records are immutable and are not backfilled with invented measurements. Application stages and provider-reported token usage must not be confused.

## Scheduled local chat workload

Run `python -m scripts.verify.chat_performance --output evidence/performance/NEW_NAME.json` against the configured host API and worker. The script preregisters eight turns in two distinct owned sessions, submits two concurrent requests per round, and keeps every scheduled response or error. The conversations include a real dependent follow-up, evidence reuse and unrelated topic changes. It records the active corpus, actual vector count, environment and GPU observations before and after the run. Those two resource observations are not peak usage measurements.

The reported p50/p95 use linear interpolation over actual observations. End-to-end values start before submission and end after terminal-job observation and answer fetch; they include queue wait and the 200 ms polling interval. Refusals remain in the software-success denominator and are separately labelled by response type. They are not factual successes. A small local workload cannot establish a deployment SLA, scalability or answer-model latency. Cost remains null because paid inference is not invoked and local hardware cost is not measured.

## Separate evaluation and retrieval evidence

[Retrieval diagnostics](retrieval_diagnostics.md) describe real R0/R1/R2/R3 execution on a frozen four-book release, including cold observations, complete schedules, source/window verification and preserved infrastructure failures. Ranking changes are not relevance improvements without judgments. The database interruption on 8 September is recorded in `evidence/recovery/docker-interruption-20260908.json`; interrupted and repeated runs have separate files and denominators.

The [SciQ technical rehearsal](sciq_technical_rehearsal.md) completed all four scheduled conditions using exactly the first two official validation rows in both OpenQA and MCQ modes. Actual E5/PostgreSQL retrieval ran on the published v5 corpus; answers remained mock. All four jobs succeeded, with two refusal responses and two completed MCQ responses. Retrieval took 4,397.410–4,910.240 ms and worker execution took 4,798.639–5,251.587 ms. The queue-inclusive observer interval was 5.374–10.317 seconds. Provider usage and formal quality/human metrics remain null; source labels/support never entered the backend command or chat. The full dataset's native MCQ rejections remain retained and strict full-split preflight is unchanged.

[Per-mode p50/p95 values](../evidence/sciq/technical-timing-summary.json) are derived from the unchanged correct `Answer.timing` observations with n=2 per protocol and linear interpolation. An older evaluator export path was found to overwrite preparation with its aggregate including retrieval; the original four private states remain preserved. The public rehearsal report reads the stored answer's separate stages directly and is unaffected. The technical rehearsal document names that limitation and distinguishes the corrected interpretation from historical export values.

The separate unchanged post-recovery R0/R1/R2/R3 schedule succeeded in all 60 conditions on its explicitly pinned historical v4 comparison release. Median whole-query seconds were 4.430, 4.739, 4.869 and 5.218 respectively; all 300 actual R3 paired inputs fit the 512-token window, with maximum 338. Full source/vector integrity checking accounts for approximately 4.1–4.2 seconds at the median. The first interrupted 56/60 schedule remains preserved separately. These retrieval-only timings, the v5 SciQ rehearsal and the concurrent-session chat workload are different protocols and are not pooled. Formal answer effectiveness, real provider usage/cost and human scoring still require actual execution.

## Observed two-session chat result

The recorded [eight-turn workload](../evidence/performance/chat-two-sessions.json) completed all eight scheduled turns without software errors on release `4f11bd70-a486-4d16-b216-78cfe499530a` (10,594 real vectors). Both sessions shared one worker and the answering adapter was mock. Refusal responses remain in the denominator.

| Measured milliseconds | p50 | p95 |
| --- | ---: | ---: |
| Preparation excluding retrieval | 12.394 | 39.972 |
| Deterministic query preparation (subset) | 0.051 | 0.067 |
| Real retrieval, including intentional reuse zeros | 4,483.008 | 4,919.018 |
| Generation-service wall time | 271.867 | 290.363 |
| Adapter computation only | 1 | 1 |
| Worker execution before answer insertion | 4,811.846 | 5,242.878 |
| Submission to observed answer, including queue/polling | 5,883.128 | 10,189.212 |

The result metadata originally described mock adapter time as always zero. The adapter actually measures its computation, and these rows contain values from zero to one millisecond. The original report is retained as `chat-two-sessions-original-description.json`; the current report records this description-only amendment with the original file hash. Every measured row and percentile is unchanged. No workload was rerun or filtered to correct wording.
