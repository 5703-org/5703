# Fixed five-question OFF/ON engineering observations

These are saved-run measurements, not an independent factual-quality or causal evaluation.

| Mode | Complete / 5 | ≤10s / 5 | Successful mean (s) | Known conservative CNY | Unknown protected CNY |
| --- | ---: | ---: | ---: | ---: | ---: |
| OFF | 4/5 | 4/5 | 4.859 | 0.220566 | 0 |
| ON | 2/5 | 0/5 | 10.988 | 0.382396 | 0 |

| Cell | Browser state | Native error | Complete seconds | Retrieval ms | GEN in/out | CHECK in/out | Check requested/executed/status |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| N1-OFF | COMPLETE_PUBLISHED_ANSWER_RENDERED |  | 6.061 | 467.859 | 29151/343 | None/None | False/False/not_requested |
| N2-OFF | FAILED_KNOWN_FUNCTIONAL | ENHANCEMENT_VALIDATION_ERROR | null | 658.921 | 28596/426 | None/None | False/False/not_requested |
| N3-OFF | COMPLETE_PUBLISHED_ANSWER_RENDERED |  | 4.981 | 410.554 | 28460/484 | None/None | False/False/not_requested |
| N4-OFF | COMPLETE_PUBLISHED_ANSWER_RENDERED |  | 4.963 | 792.047 | 11858/309 | None/None | False/False/not_requested |
| N5-OFF | COMPLETE_PUBLISHED_ANSWER_RENDERED |  | 3.431 | 0.0 | 4886/271 | None/None | False/False/not_requested |
| N1-ON | COMPLETE_PUBLISHED_ANSWER_RENDERED |  | 11.613 | 431.989 | 29151/346 | 16354/1324 | True/True/passed |
| N2-ON | FAILED_KNOWN_FUNCTIONAL | ENHANCEMENT_VALIDATION_ERROR | null | 650.678 | 28596/430 | None/None | True/False/not_performed |
| N3-ON | FAILED_KNOWN_FUNCTIONAL | CHECKER_INCONSISTENT | null | 369.238 | 28460/536 | 18127/2179 | True/True/failed |
| N4-ON | FAILED_KNOWN_FUNCTIONAL | SEMANTIC_CHECK_FAILED | null | 697.917 | 11858/249 | 12842/1532 | True/True/failed |
| N5-ON | COMPLETE_PUBLISHED_ANSWER_RENDERED |  | 10.363 | 0.0 | 4886/373 | 8904/1036 | True/True/passed |

Failed, incomplete and unrun cells retain null successful latency. Their observed stages and spent tokens remain in JSON. Means use only complete cases; the fixed denominators remain five per mode.

GEN/CHECK tokens and transport durations come from the physical ledger. Codec input reductions are separately labelled local tokenizer estimates, not measured provider savings. Conservative usage costs and protected holds are not invoices.

Query preparation is nested within preparation; CHECK is nested within generation wall time. Provider and nested stage durations must not be added together. Browser completion includes native polling and stable full-body rendering, not first-token latency.

Fence audit findings remain distinct from process closure: OFF clean=False, audit_failure=True; ON clean=False, audit_failure=True

The saved network-boundary source-inspection note identifies a blocked local urllib3 IPv6 capability probe (::1, port 0). Original fence denials and audit failures remain recorded; lifecycle closure is not a clean-fence claim.

N5 no-RAG proof: N5-OFF ESTABLISHED_FROM_NATIVE_TRACE; N5-ON ESTABLISHED_FROM_NATIVE_TRACE
