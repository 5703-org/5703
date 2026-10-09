# Installed CPU workflow verification

Current attempt: `installed-qa-root-06`. Actual status: `completed_with_retained_diagnostic_gaps`.

This finite study uses the installed CPU project, four real released textbooks and the mock answering model. Its five scheduled jobs are selected-passage explanation, DNA/RNA comparison, a follow-up, an ideal-gas question and one cancellation. Job execution, query preparation, evidence, citations and access checks have separate records. Independent answer-quality scores and human ratings are zero.

| Attempt | Actual status | HTTP attempts | Ordinary jobs succeeded | Cancellation state | Failure |
| --- | --- | ---: | ---: | --- | --- |
| installed-qa-root-01 | failed | 0 | 0/4 | not_executed | OWNED_PROCESS_IDENTITY_FAILED |
| installed-qa-root-02 | failed | 0 | 0/4 | not_executed | OWNED_PROCESS_IDENTITY_FAILED |
| installed-qa-root-03 | failed | 1 | 0/4 | not_executed | BOUNDED_LOCAL_FAILURE |
| installed-qa-root-04 | failed | 25 | 3/4 | not_executed | BOUNDED_LOCAL_FAILURE |
| installed-qa-root-05 | failed | 23 | 3/4 | not_executed | BOUNDED_LOCAL_FAILURE |
| installed-qa-root-06 | completed_with_retained_diagnostic_gaps | 45 | 4/4 | succeeded |  |

Every attempt retains all five scheduled job positions. Earlier failures remain separate from the current attempt. The accompanying metadata reports actual refusal/answer types, citation counts and incomplete checks; a succeeded mock job does not establish supported-answer accuracy.

The first two attempts stopped during runtime identity observation. The third stopped before its first local API connection because a preservation import replaced the approved socket fence. A separate hash-bound cleanup deactivated that attempt's two temporary accounts and preserved every other database row and column. The fourth reader expected a dictionary for an ordered-list trace; the fifth expected a string in a nullable query field. Each completed three jobs, retained two unexecuted jobs, deactivated its two temporary accounts and passed its all-table row audit.

The current verifier records nullable queries and checks each job's diagnostics. Missing follow-up or CPU-execution proof remains an explicit diagnostic failure while later safe jobs continue. A terminal status with retained diagnostic gaps preserves the original failed criterion. It does not receive a passed label. Citation gaps and the actual cancellation result remain visible in their own fields.

The current terminal receipt determines its cleanup, database, file/resource and MAIN-preservation checks. Null proof fields identify stages that did not complete. Provider-call proof uses mock configuration and persisted attempt metadata; it does not include external packet capture. All timings include finite verifier guards and durable receipt overhead.

Gate SHA-256: `483ad5fd5c7493c8712cceff2ed8147f16d1d38c3dc9baec926e985a3e10ed1e`. Source snapshot SHA-256: `f1068cbce9e4503532b81f1668ae44777147c72db135f1786ef18c10e29bb869`.

Current terminal SHA-256: `7db8dd7c062e6280a298cd5b5dc3c194a1bee05329ab0e4a949af4fddcd53102`.
