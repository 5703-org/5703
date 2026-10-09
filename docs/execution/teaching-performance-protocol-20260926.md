# Teaching reliability and CPU performance protocol

Registered on 26 September 2026 before implementation. Executor: Codex. Accountable domains follow the original eight-member allocation. The pre-change source is frozen in `evidence/teaching-performance/20260926/baseline-source.zip`; its SHA-256 is `ed82095d37f39224a7726260c8c0cffaa38b19aa44c620c47b3a672a697943f5`. The manifest records 686 source, configuration, contract and document files. Existing experiments retain their source and protocol identities.

## Fixed product requirements

Ordinary textbook questions default to full answers. Teaching mode and answer mode remain independent. Factual textbook claims need exact supporting sources; verified procedural guidance can omit citations. General-knowledge facts are explicitly labelled and never certified as textbook-supported. Learner attempts answer a persisted tutor question, retain the original task and help level, and are evaluated before the next hint. Explicit new tasks and full explanations take priority. Existing sources, vectors, release manifests, saved answers and citations remain intact.

## Registered defect regressions

| ID | Input or condition | Required result |
| --- | --- | --- |
| BUG-01A | Textbook / first hint containing only procedural guidance | A checker-approved response may publish with zero citations |
| BUG-01B | A scientific claim disguised as procedural guidance | Cannot bypass factual source checking |
| BUG-01C | Accurate source whose visible text reveals the full solution | Teaching display/cumulative check prevents publication |
| BUG-01D | Ordinary textbook question | Full answer with supported citations |
| BUG-02A | General knowledge / another hint containing a fact | Explicit general-knowledge basis; textbook support not applicable |
| BUG-02B | General knowledge response containing textbook certification or citations | Reject inconsistent checker/publication records |
| BUG-03A | Compare diffusion and osmosis → Which process specifically involves water? → Osmosis. | Same owned task and question; learner-attempt role; unchanged hint depth |
| BUG-03B | Pending numeric question → number with units; negation; incorrect or multi-sentence attempt | Retain task and evaluate attempt; no automatic deeper help |
| BUG-03C | Pending question plus explicit new problem or full explanation | Execute the explicit action |
| BUG-03D | Foreign/stale task or question identity | Reject; no cross-owner or stale mutation |
| CACHE-01 | Revoked/deactivated/restored source or changed visibility | Rebuild the matching lexical statistics; current visibility at retrieval and publication |
| CACHE-02 | Changed released source text, vectors, metadata or manifest | Invalidated cache or explicit integrity failure; no stale trusted answer |
| TIMING-01 | Checker contract repair | Included in checking time and model total exactly once |

## Experimental arms and decision rules

Compare separate arms: frozen reference; repaired contracts/task flow; validated release and exact lexical caches; ONNX FP32 reranking; ONNX INT8 reranking; adaptive rerank budgets 5/10/20. E5 model/tokenizer/preprocessing and original corpus vectors stay fixed. Formal E0/E1 definitions stay fixed. Any unavailable runtime/backend is recorded as unavailable, never simulated.

The lexical optimization must match reference scores and ordered IDs, including zero-score ties, repeated query words, empty results and source visibility changes. Whole-release validation occurs before a cached index becomes usable; reliable database invalidation and hit/publication validation are required before the optimization becomes default. Final answer caching is excluded.

Backend and budget candidates use grouped development and held-out queries. Before examining held-out outcomes, freeze query groups, expected behavior, reference evidence and fitted policy/calibration identities. Default enablement requires no fixed-regression failures, no observed additional false refusal, wrong citation or hint leakage, and a one-sided 95% paired lower bound above -5 percentage points for complete supported-answer success. Report retrieval evidence retention and score/rank changes separately. If the available sample cannot establish this bound, retain the strategy as an explicit experimental option. The -4.0 PyTorch score threshold is not transferable calibration for INT8.

Warm end-to-end p95 reduction of 30% is an engineering target. Measure cold/first/warm observations separately. Report successful, failed and all requests with scheduled denominators; queue, query preparation, release validation, dense/lexical retrieval, reranking, generation, checking/repair, publication and browser observation are distinct stages. Record calls, token/cache usage, elapsed time, failure stage and process memory. Model-stage latency alone is not end-to-end latency. Preserve failed attempts. Human ratings remain blank until actual reviewers submit them.

## Delivery gates

Run focused regressions, foundation/contract/chat-scope checks and the complete software gate, current real CPU/database/provider checks and archive integrity/reconstruction. Synchronize PRD, SPEC, PLANS, API/data/generation contracts and all original 108 task / 60 acceptance / 12 responsive identifiers without replacing historical evidence. Deliver one complete runnable archive and eight owner-assigned archives containing current complete files. Preserve the September Week 7 and final Week 8 deliveries and scientific records.
