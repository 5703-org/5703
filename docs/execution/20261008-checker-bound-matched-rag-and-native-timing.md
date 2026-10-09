# CS30-1 checker repair, matched RAG and complete-answer HTTP evidence

Recorded 2026-10-07 UTC; the host-date run identifiers use 20261008. Scope: `E:\5703\learning-assistant` only. This checkpoint completes the bounded repair and experiments requested in this round. Whole-project and course acceptance remain partial.

## Implemented repair and free validation

The reviewed three-file change was adopted in the main repository. Compact checker instructions now request concise verdict and error reasons without restating answers or sources. Required rows, exact quotations, complete proofs, citation bindings and all eleven independently assessed semantic flags remain mandatory. The limit is eight evidence span IDs **per requirement**. It is not eight distinct IDs across the entire result. The compiler and scientific decoder were not relaxed.

Current focused validation: **62 passed**, comprising 42 compact transport tests and 20 activation-eligibility tests. The earlier Source22 full suite (backend 4207 passed / 20 skipped; frontend 233 passed) remains historical evidence. It is not a fresh full regression of these later three-file changes.

The repaired pending compact checker passed normal BASIC and simple STRUCTURED tests but failed full PROJECT with upstream HTTP400. An identical-wire diagnostic also returned Google `INVALID_ARGUMENT` without identifying a parameter. The minimal original five-nullable/anyOf proof subgroup returned HTTP200 with a locally valid subfeature shape; it requested a null derivation and does not qualify full proof decoding or scientific checking. The complete equivalent C nullable-array schema still returned HTTP400. No C schema or experimental AI Studio route was adopted. The pending compact checker remains unactivated.

See [current source adoption](evidence/20261008-checker-rag-native/current-three-file-adoption.json), [focused tests](evidence/20261008-checker-rag-native/focused-free-tests.json), [minimal subgroup](evidence/20261008-checker-rag-native/schema-mini.json) and [full C diagnostic](evidence/20261008-checker-rag-native/schema-full-C.json).

## Matched public DEV quality

The batch completed 19 POSTs without HTTP retries: three already exposed DEV questions x two tasks x three arms = 18 matched outputs, plus one reference-sufficient diagnostic outside the comparison. The 18 original serialized wire SHA/byte counts match the frozen protocol. Model, route, output cap768, scorer and permission to use relevant evidence and model knowledge were shared. Generation did not read Gold. Three references were scored locally only after all paid generation children were closed; no Gold text or labels were exported.

| Arm | MCQ | Original OpenQA EM/F1 | Preregistered whole-answer alias diagnostic |
| --- | --- | --- | --- |
| No retrieval | 3/3 | 2/3 | 3/3 |
| Dense | 3/3 | 2/3 | 3/3 |
| Current hybrid with MiniLM | 3/3 | 2/3 | 3/3 |

These exposed DEV results show no demonstrated RAG gain. Original lexical scores remain unchanged. The separate terminology alias is a supplementary diagnostic, not human grading or heldout evaluation. The reference diagnostic had original EM/F1 0 and alias match1 and is excluded from arm denominators. Adapter-only generation medians ranged from 1006 to1177 ms; they exclude retrieval, checking, persistence and HTTP answer retrieval.

See [actual scores](evidence/20261008-checker-rag-native/matched-DEV-scores.json) and [independent protocol review](evidence/20261008-checker-rag-native/matched-DEV-review.md).

## Genuine complete-answer HTTP timing

The application's unchanged current PROJECT eligibility checks admitted an existing baseline, with answer and checker configuration `74c8201e-aca0-400d-bcc5-5785e24c1c11`, public hash `703c94a357ddd4b826d8b5fe25d503198d3d56e1e9130f6a37ed9e9c3396aa4a`. Its two actual current PROJECT receipts passed all six fingerprint checks. One normal CAS activated this pair in the **owned synthetic fixture only**, version24 to25, with zero model calls. BASIC/STRUCTURED coverage is missing for this baseline; no three-tier acceptance was invented. This baseline retains Vertex/global LOW and saved `json_object` full V5 checking; it is distinct from the pending compact/schema candidate.

Four fresh sessions used textbook knowledge, direct teaching, `use_profile=false`, no prior history, the same released public corpus and the same frozen answer/checker configuration. Dense and hybrid policies were frozen through original HTTP submission. Local E5 and MiniLM factories loaded the existing CUDA models before timing, without precomputing the future questions. The original worker and scientific/citation/teaching gates ran; the controller only restricted queue selection to the actual owned jobs. The timer began immediately before each real message POST and ended after terminal success and the successful original Answer GET.

| Question | Dense full HTTP time | Hybrid full HTTP time | Dense / hybrid model calls |
| --- | --- | --- | --- |
| What is homeostasis? | 14.118 s | 7.573 s | 2 / 2 |
| Simple versus facilitated diffusion | 32.933 s | 13.074 s | 3 / 2 |

All **4/4** jobs published normal live checked answers and were retrieved successfully. The balanced execution order was dense homeostasis, hybrid diffusion, hybrid homeostasis, dense diffusion. Nine physical model POSTs cost USD0.0470320; all costs were known, with zero native UNKNOWN holds and zero HTTP retries. The 32.933-second dense diffusion case included the original `checker_contract_repair` call; checking accounted for27.728 seconds. Dense homeostasis retrieval took6.287 seconds, while the other retrieval stages took0.109 to0.345 seconds. First-use and normal cache/order effects were not separately controlled, so these four observations establish actual outcomes, not a causal speed advantage for an arm.

The four-case planned denominator yielded one answer within10 seconds and none within5 seconds. Dense had0/2 within10 seconds; hybrid had1/2. There is no p95, TTFT, browser-visible latency or stable5-10-second claim. The same-policy no-retrieval native arm is unsupported by the current interactive contract and was not substituted with a different benchmark path. This test does not qualify the repaired compact candidate.

The first native harness stopped before any model POST because it misclassified the pre-existing budget-lock metadata. Its zero-call failure, sessions and closure were retained. The successor recognized that exact lock, held the original shared mutex through execution and retained every prior hold. Both API servers exited gracefully, their engines and memory keys were cleared, all owned processes/handles closed, all focused source pins matched, and the actual worker released both normal queue locks and the budget lock. Future helper hardening is separate from these completed results.

See [normal baseline CAS](evidence/20261008-checker-rag-native/baseline-normal-CAS.json), [full HTTP receipt](evidence/20261008-checker-rag-native/native-four-HTTP.json), [normal worker receipt](evidence/20261008-checker-rag-native/native-four-worker.json) and [owned closure](evidence/20261008-checker-rag-native/native-owned-closure.json).

## Free retrieval diagnostics

Real CUDA MiniLM reranking of the expanded31-candidate oxidant pool retained P@5=0; the two labelled relevant examples ranked28 and31. The negative result is preserved. The three-question fixed-pool/four-ordering ablation gave positive P@5 counts dense1/15, candidate-local BM254/15, candidate-local RRF2/15 and MiniLM3/15. BM25's difference was concentrated in one organ question; it does not establish global retrieval or answer-accuracy improvement. No production default was changed.

All84 full query/passage pairs were107-341 tokens against a512-token window; inspected title/section prefixes reached at most369 and were not used in scoring. Observed truncation does not explain these failures. Top-five label bounds coincide, but full-corpus recall remains NULL. AI exploratory relevance labels are not human gold or proof of full answer sufficiency. Public Chemistry2e definition chunks establish corpus support for the oxidant question outside the old candidate union; they appeared only in the separate reference diagnostic.

See [actual free ablation](evidence/20261008-checker-rag-native/free-ablation-report.md) and [independent review](evidence/20261008-checker-rag-native/free-ablation-review.md).

## Budget and preservation

Journal19 records164 cumulative physical requests:151 known-cost and13 UNKNOWN-cost, with known API-cost subtotal USD0.467741750. This followup has34 requests:31 known and3 UNKNOWN, known subtotal USD0.0567701 and retained UNKNOWN holds USD0.1486848. The native test added9 known requests/USD0.0470320. The schema HTTP400 costs remain UNKNOWN, not zero. These are reported costs and conservative holds, not an invoice or account balance.

All prior UNKNOWNs, original20-slot/STOP history and reserves remain intact. The followup retains USD1.94; combined protected allocation USD9.97128969 stays within the existing USD10 authorization, with USD0.02871031 unallocated. Started followup claims total USD1.5270144 submitted upper bound; frozen limits remain42 calls and USD1.9235072. No reserve was released. See [safe financial projection](evidence/20261008-checker-rag-native/finance-journal19-projection.json).

No real database, protected staging, experiment input/result or old delivery was reset or deleted. No dependency install, model download, remote push/upload, deployment or course submission occurred. Existing docs are appended with their original byte prefixes preserved. Git status remains blocked by repository ownership; no `safe.directory` exception or branch reset was applied.

## Remaining acceptance gaps

The repaired compact checker still lacks a passing full PROJECT result on its selected provider. The existing baseline's BASIC/STRUCTURED course coverage is missing. Stable tail latency, independent heldout/human quality, learning benefit, browser/device journeys and member/course approvals remain open. The existing whole-project matrix stays partial; focused tests, four checked answers and three exposed DEV questions do not establish full project completion. The accompanying [technical interview evidence Q&A](20261008-interview-evidence-qa.md) states the same boundaries.
