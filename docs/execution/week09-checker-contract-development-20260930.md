# Week 9 checker-contract development probe

The current V5 checker prompt remains active. A frozen compact-prompt experiment on previously exposed fixed drafts completed two paired cases. It did not reduce checker calls: each arm used three checker calls across two cases and required one schema correction. The compact arm delivered two drafts and the baseline arm delivered one, but one unchanged draft received a different `complete_answer` gate despite matching factual claim statuses and requirement sufficiency. No human adjudication is available, so this difference is not a verified quality gain.

The archived V8 sequence showed seven textbook failures after `generation → joint_check → checker_contract_repair` with one of four calls remaining. This is an inferred mechanism from stage records and code, not a proven raw V8 semantic verdict. The new exposed development pair directly demonstrated the same budget stop: a malformed checker result needed the third call for contract correction; the baseline then rejected `complete_answer`, leaving one call when semantic repair and final recheck required two. Publication stayed closed.

| Completed exposed pairs | Baseline V5 | Compact prompt |
| --- | ---: | ---: |
| Delivered fixed drafts | 1/2 | 2/2 |
| Checker calls | 3 | 3 |
| Schema-invalid checks | 1 | 1 |
| Input tokens | 21,364 | 21,116 |
| Output tokens | 2,914 | 3,284 |
| Total elapsed, two runs | 15.36 s | 13.68 s |
| Estimated off-peak cost, completed runs | $0.001905 | $0.003463 |

The first exploratory runner aborted after reaching three checker transports, before saving usage; its cost is unknown. A second frozen attempt in the default sandbox made 24 connection-failed transport attempts and received no provider usage; these were excluded from comparisons. The third frozen run used approved network access. Four runs completed. One additional run had two durable checker responses but aborted at a local replay-count assertion; its known usage was 15,554 input and 1,369 output tokens, with an estimated off-peak cost of $0.002101. It was excluded from paired results. The project source and formal reserved cases were unchanged.

Frozen manifest SHA-256: `b0cec4d5db8188713eaf7207606f1f59f52ad76edeb912224d0816f70885bb65`. Runner SHA-256: `d0afe64984c9892640092c4a4fe8c17e47e638047f61f528643784e5f3bcf129`. Original prompt SHA-256: `3c5a20178a72b3c33ac0e6e3e2f7f1d03fbe85d03e24bdae06cfb915f660c37f`. Compact prompt SHA-256: `fa131a2eebeaaf59789abde9316b5f780e6f9db9de88011a8b088f5befff614d`. Full sanitized counts, paired gates, outcome hashes and incident hashes are in `PUBLIC_DIAGNOSTIC_EN.json`. Raw drafts, textbook excerpts and checker responses remain only in the private probe files.

The sample is too small for an activation decision. It has no independent review of the disputed `complete_answer` gate, and the compact prompt did not save a checker call. The product keeps the existing prompt, four-call limit and final publication check.
