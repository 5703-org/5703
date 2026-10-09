# Current V20 CPU cancellation, recovery and load execution

The current installed project completed all seven acceptance cases on 2 October 2026. The run scheduled seven requests and eight jobs, completed 39 HTTP requests, and used the mock answer model with zero paid provider calls. The frozen software gate contains 844 inputs; the installed code and contract inventory contains 858 inputs and 54,491 file pins.

Queued cancellation, cancellation after an observed running lease, and cancellation of an explicitly paused owned worker all completed with zero saved answers. The controlled checks acquired Session, Job and AnswerRequest locks with NOWAIT and rolled back the probe. The running, controlled and recovery cases began with an observed empty model-instance cache in each newly started worker.

The recovery case stopped the owned worker at a verified unlocked preparation stage. The existing lease reached 240.074334 seconds before the normal stale-recovery command ran. One explicit retry succeeded; repeating its idempotency key returned the same job. The request saved one answer. The recovery case took 278.682 seconds, including the natural 240-second wait and process controls.

Three concurrently submitted load requests succeeded with observed real CPU query embedding and reranking. Their shared wall interval was 7.147 seconds. Answer content used the mock model. This run reports workflow execution and preservation; answer quality and speed improvement were not evaluated. HTTP transport p95 was 165.104 ms across all 39 requests, including expected ownership denials and deactivated-account responses. This measurement describes HTTP transport; answer latency p95 remains unmeasured.

The two temporary accounts were deactivated. All original rows and columns in 65 tables, covering 137,376 records, remained unchanged. The finite new graph spans 20 tables. Current source, installed files and 88 protected inputs remained unchanged. The four dedicated services remain available for the next acceptance journeys.

The earlier running-cancellation failure with PostgreSQL SQLSTATE 40P01 remains in its original receipt and database log. The current result has its own denominator and hash-bound evidence. Human evaluation remains pending.

Evidence: [current numeric receipt](../../evidence/week09-continuation/20261001/current-v20-cancel-recovery-load-20261002.json).
