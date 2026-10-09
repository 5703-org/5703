# Week 9 Work Report

Chengzhou Liu | 540931958 | 26 September 2026

Real embeddings, retrieval and contextual query preparation

## Scope and retained work

The retrieval workstream retains real E5 query encoding, PostgreSQL vectors, BM25, reciprocal-rank fusion and MiniLM reranking on CPU. Week 8 introduced reusable release and query computation, experimental CPU backends and an offline candidate-budget comparison. Original E0 without retrieval and E1 with dense retrieval retain their benchmark definitions.

Original allocation: RET-01, RET-02, RET-03, RET-04, RET-05, RET-06, RET-07, RET-08, RET-09, RET-10, RET-11, CHAT-04.

## Week 9 changes

Week 9 uses the current hybrid retrieval path to freeze source context for the teaching and memory studies. Missing multi-part knowledge can trigger one targeted retrieval pass within the same release, runtime policy and active-time budget. Evidence already present in the candidate set is considered during packing before another lookup is needed.

The retrieval boundary continues to expose actual candidates, selected context, runtime identity and coverage losses. Semantic memory matching uses the pinned local E5 model as an explicitly configured experiment; the original corpus vectors and their identity remain unchanged. Existing PyTorch reranking and the full candidate budget remain the standard runtime configuration.

## Verification and findings

The fresh Windows CPU environment exercised real E5 query encoding and official PostgreSQL/pgvector retrieval with no CUDA runtime. All eighty official resources, two optional ONNX graphs and their manifest retained their verified identity. The reserved 200-request study uses frozen retrieved context, so its generation timings exclude live retrieval.

## Current source and responsibility

The personal archive contains complete current files for this workstream, including retained changes since the Week 7 final release. The package manifest records file ownership and hashes. Codex performed the shared implementation and automated execution; the named member is accountable for reviewing, explaining and submitting this workstream.

Selected assigned source areas

retrieval/chat.py

retrieval/query_cache.py

retrieval/embedding.py

retrieval/cpu_backend.py

retrieval/adaptive.py

## Week 10 goals

- Label missed and redundant evidence for multi-part questions and measure the value of the single supplementary pass.

- Broaden grouped CPU backend and budget comparisons before changing relevance thresholds or default candidate counts.

- Measure complete request latency and retrieval quality on a separate CPU computer with fixed corpus and model versions.

## Evidence

evidence/week09-generation/20260926/portable/runtime-verification.json

evidence/week09-generation/20260926/portable/runtime-verification-release-source.json
