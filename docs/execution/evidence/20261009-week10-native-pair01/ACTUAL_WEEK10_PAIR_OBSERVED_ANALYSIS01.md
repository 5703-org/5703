# Actual Week10 paired diagnostic

Status: `ACTUAL_OBSERVED_MATCHED_PAIR_DIAGNOSTIC_ONLY`. All numbers below are observed; missing values stay pending/null.

| Metric | A baseline | B startup prewarm |
|---|---:|---:|
| Root launch → worker ready ms | 8428.32080078125 | 14096.634033203125 |
| Model warmup ms | 5099.632400000701 | 4987.674199999674 |
| Startup snapshot preparation ms | 0.003700000888784416 | 5760.193500000241 |
| Measured release validation ms | 5899.568599999839 | 3.619200000684941 |
| Measured query-vector cache hit | False | False |
| Send → complete DOM observed ms | 18714.299999998882 | 12146.5 |
| Send → accepted complete cited answer ms | 18714.299999998882 | 12146.5 |
| First visible UI ms; not TTFT | 18647.699999999255 | 12146.5 |
| Launch → complete answer ms | 30204.039746092632 | 29447.85595703125 |

| Gate | A | B |
|---|---|---|
| browser_followup_status | PASS | PASS |
| native_checked_completed | True | True |
| citation_checked | True | True |
| refresh_persisted | True | True |
| scientific_quality_acceptance | NOT_ASSERTED | NOT_ASSERTED |
| runtime_closed_status | CLOSED | CLOSED |

| Physical slot / leg / role | Adapter latency ms | Known cost USD | UNKNOWN/open full hold USD |
|---|---:|---:|---:|
| 1 / A_baseline / teacher | 6031 | 0.0065769 | 0.00000000 |
| 2 / A_baseline / checker | 3039 | 0.004279 | 0.00000000 |
| 3 / B_startup_prewarm / teacher | 4932 | 0.00305234 | 0.00000000 |
| 4 / B_startup_prewarm / checker | 4272 | 0.0054608 | 0.00000000 |

Initial complete generator inputs matched: **True**. Checker and repair complete hash differences are retained in JSON, including unequal or missing counterparts.

New observed claims: 4 of at most8; known subtotal USD0.01936904; new UNKNOWN/open holds USD0. Whole USD0.24 allocation and all old protections remain retained. Old project known USD0.58138393 and fourteen old UNKNOWN are unchanged; invoice/account balance and actual total remain null.

One fixed A→B pair cannot establish p95, SLA, model superiority or pure cache causality. OS pagecache is uncontrolled. Startup is separately accounted; first UI appearance is not TTFT. Failed/censored cases remain, with no fabricated full-answer completion.

JSON contains exact observed source pins, per-stage timings, quality status, complete wire/evidence/history/profile hashes and findings; no prompt, answer, raw wire, private authentication or URI is exported.
