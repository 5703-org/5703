# Unified-condition answer return durations

All 36 scheduled requests completed and settled. No reference answers were read by this summary.

| Arm | Completed / scheduled | Median (s) | p95 (s) | Scientific quality |
| --- | ---: | ---: | ---: | --- |
| E0_none | 12 / 12 | 1.1362 | 1.5337 | Unscored: reference read blocked |
| E1_dense | 12 / 12 | 1.1897 | 1.8154 | Unscored: reference read blocked |
| hybrid_plus_rerank | 12 / 12 | 1.0770 | 1.3213 | Unscored: reference read blocked |

API-reported known cost: USD 0.0172570; new UNKNOWN holds: USD 0.

The timer covers adapter.generate through complete model return, before local validation. It excludes native HTTP, retrieval, checker, worker polling and UI rendering. These observations do not establish a warm native end-to-end p95 reduction or quality non-inferiority.

Inputs are 12 previously seen failure-strata development questions, with identical frozen policy/model/schema/output limits and rotated arm order. No held-out, human or learning-effect result is claimed. The failed checker baseline prevents a valid paired checker speed comparison.
