# CS30-1 technical review questions backed by actual evidence

Companion to existing interview material. Recorded2026-10-07 UTC; this is a local deliverable, not course submission. See the [current checkpoint](20261008-checker-bound-matched-rag-and-native-timing.md).

**Did RAG improve answer accuracy?** Three exposed DEV questions gave every arm MCQ3/3 and original OpenQA EM/F1 2/3. The preregistered terminology diagnostic gave every arm3/3. These results show no demonstrated RAG gain and cannot establish heldout accuracy or learning benefit.

**Why did exact OpenQA scoring differ from the terminology diagnostic?** Equivalent oxidant/oxidizing-agent wording differs under exact lexical matching. Original EM/F1 was retained; the separate whole-answer alias uses public Chemistry2e terminology. It does not discard negation, alternative-class phrases, signs or units, and is not human grading.

**Did a larger candidate pool solve retrieval?** Real CUDA reranking of all31 frozen candidates left P@5=0 and the labelled positives at ranks28/31. The original RRF top20 excluded both before reranking. The negative result remains evidence, not a reason to claim improved recall.

**Should BM25 replace the default?** Its fixed-pool result was4/15 against MiniLM3/15, concentrated in one organ question. This measures finite-pool ordering, not full-corpus recall, complete evidence sufficiency or answer accuracy. No default changed.

**Was sequence truncation the cause?** The84 actual full pairs were107-341 tokens below the512-token window. Inspected prefixes also fitted and were not used. The recorded failures do not support truncation as the explanation.

**What checker change was implemented?** Compact reasons were shortened while rows, quotations, proofs, citations, eleven semantic assessments and the eight-span limit per requirement stayed intact. All62 focused tests passed. The repaired compact candidate's full PROJECT request still returned400. A minimal nullable/proof subgroup returned200, but the equivalent full C schema returned400; neither diagnostic establishes scientific qualification. The candidate stayed pending.

**How was full-answer timing possible with that pending candidate?** An existing current PROJECT-qualified full-V5/json_object baseline passed the original eligibility checks and normal CAS in the synthetic fixture. Its missing BASIC/STRUCTURED coverage was explicitly recorded. Using it did not qualify the pending compact candidate or change real database defaults.

**What were actual complete-answer times?** The original message POST through checked Answer GET took14.118/7.573 seconds for dense/hybrid homeostasis and32.933/13.074 seconds for dense/hybrid diffusion. All4/4 were checked live answers. The slow dense diffusion case required a third call for checker contract correction. Nine model calls cost USD0.0470320, with no unknown native cost or HTTP retry.

**Can the project claim one-second or stable5-10-second answers?** The approximately one-second result covers adapter-only short generation. Only1/4 complete HTTP answers finished within10 seconds; none within5. Four observations, first-use/cache/order effects and one correction call do not establish p95, a causal arm-speed advantage or browser latency.

**Were records, credentials and budgets protected?** All processes and locks closed. Gold was absent from generation and scored locally only after closure; Gold content, tokens, keys and provider headers were not exported. All UNKNOWN holds, prior STOP records and the existing USD10 allocation remain preserved. Real databases, protected staging and old deliveries were untouched.

**Is the whole project complete?** This round completed its bounded repair and matched experiments. Full PROJECT qualification of the repaired compact candidate, three-tier course coverage, stable tail latency, heldout/human evaluation, browser/device acceptance and member/course approvals remain open. The project matrix remains partial.
