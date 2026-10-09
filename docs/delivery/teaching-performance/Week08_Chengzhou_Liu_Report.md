# Week 8 Work Report

Chengzhou Liu | 540931958 | 26 September 2026

Real embeddings, retrieval and contextual query preparation

## Week 8 scope

This workstream covers all development after the verified Week 7 final release through the current teaching and performance continuation. Real E5 retrieval, hybrid/reranking support, conversation-aware retrieval and the real corpus were already present; original E0 no-retrieval and E1 dense-retrieval results remain historical.

Original allocation: RET-01, RET-02, RET-03, RET-04, RET-05, RET-06, RET-07, RET-08, RET-09, RET-10, RET-11, CHAT-04.

## Completed work across the week

Implemented structured query requirements that preserve comparison, negation, numbers, conditions and current local referents, with explicit clarification for ambiguous turns.

Added current-query rescoring of eligible prior evidence, relevance screening, complementary packing and bounded per-facet fallback for mixed supported/unsupported requests.

Made build identity independent of query device and verified CPU-only installation and limited CPU/CUDA retrieval parity without claiming bit-identical vectors or performance equivalence.

Added exact-fragment/preselected-source strategies and complementary generation context under the existing evidence budget; repaired declarative problem references and preserved historical query versions.

A transactional release cache and precomputed BM25 index reuse validated work while preserving exact reference scores and ranking. Owner-scoped query-vector reuse keeps the original E5 identity, runtime device and full preprocessing configuration in its key.

CPU experiments compare the pinned MiniLM model under PyTorch, ONNX FP32 and ONNX INT8. A development-only adaptive rule proposes 5, 10 or 20 candidates, with shadow operation and model-specific calibration boundaries. The original PyTorch backend and full budget remain the default.

## Verification and findings

Warm local retrieval plus reranking p95 falls from 5,235.96 to 455.14 ms with 48 of 48 exact result pairs. The small complete HTTP comparison has one failure per arm and no p95 improvement. The fastest measured backend on this host remains 16-thread PyTorch; INT8 changes ranking and scores. Adaptive development selects the full budget of 20.

## Personal code package

The package contains the complete current versions of this workstream's cumulative changed files, with repository paths and a baseline/current hash inventory. The personal DOCX matches the standalone report byte-for-byte. The shared implementation and automated verification were performed through Codex; the named member owns the review, explanation and submission of this workstream.

Selected current file areas:

retrieval/lexical.py

retrieval/query_cache.py

retrieval/cpu_backend.py

retrieval/adaptive.py

scripts/verify/pg_retrieval_performance.py

## Week 9 goals

- Expand grouped development and untouched test cases before recalibrating relevance or reducing candidate budgets.

- Measure complete user-visible latency and memory on separate CPU hardware.

- Evaluate answer support and citation coverage for backend or budget changes before enabling them by default.

## Evidence

docs/execution/teaching-performance-20260926.md

evidence/teaching-performance/20260926/http-timing-final/summary.json
