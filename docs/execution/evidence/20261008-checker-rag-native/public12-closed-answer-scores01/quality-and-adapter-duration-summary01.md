Local matched OpenQA36 result

Twelve previously seen diagnostic questions, three fixed arms. Every quality and schema denominator is 12. References and raw answers are omitted from this summary.

| Arm | Schema valid | Answer valid | EM | Token F1 | EM or registered equivalence | Adapter min ms | Median ms | p95 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0_none | 12/12 | 12/12 | 0.5833 | 0.6389 | 0.6667 | 934.75 | 1136.16 | 1533.74 | 1813.02 |
| E1_dense | 12/12 | 12/12 | 0.5000 | 0.6111 | 0.5000 | 1000.92 | 1189.73 | 1815.44 | 1891.83 |
| hybrid_plus_rerank | 12/12 | 12/12 | 0.5000 | 0.7083 | 0.6667 | 878.33 | 1077.04 | 1321.30 | 1334.27 |

| Matched comparison (B minus A) | EM mean delta | EM B wins / ties / losses | Token F1 mean delta | Token F1 B wins / ties / losses |
|---|---:|---:|---:|---:|
| E1_dense minus E0_none | -0.0833 | 0 / 11 / 1 | -0.0278 | 2 / 8 / 2 |
| hybrid_plus_rerank minus E0_none | -0.0833 | 0 / 11 / 1 | 0.0694 | 2 / 9 / 1 |
| hybrid_plus_rerank minus E1_dense | 0.0000 | 1 / 10 / 1 | 0.0972 | 2 / 9 / 1 |

Timing is adapter_only, measured around adapter.generate until its complete return. It excludes retrieval, checker, production HTTP and runner post-return schema validation. Each arm has n=12; p95 uses the original scorer's linear quantile and is descriptive.

Schema-valid refusals score zero for answer EM/F1. The supplementary metric permits only unchanged full-answer registered classes. Existing retrieval diagnostics are inherited by pin; no labels were recomputed. This DEV sample does not establish held-out performance.

