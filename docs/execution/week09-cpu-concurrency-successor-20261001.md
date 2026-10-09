# CPU concurrency repair: immutable-receipt comparison

The original run delivered 16 of 19 requests and recorded three reranking failures. The successor delivered all 19 requests using the same four public-textbook questions and schedule. Every previously successful ranking retained its ordered chunk IDs, source metadata and score comparisons as recorded below.

| Population | Before passed / failed | After passed / failed | Before median observed seconds: all / passed / failed | After median observed seconds: all / passed / failed |
| --- | --- | --- | --- | --- |
| first_query_after_cold_model_setup_c1 | 1 / 0 | 1 / 0 | 6.095532 / 6.095532 / n/a | 6.095879 / 6.095879 / n/a |
| warm_forced_encoding_c1 | 8 / 0 | 8 / 0 | 0.843325 / 0.843325 / n/a | 0.833580 / 0.833580 / n/a |
| warm_forced_encoding_c2 | 5 / 3 | 8 / 0 | 0.842517 / 0.847444 / 0.116149 | 1.227371 / 1.227371 / n/a |
| normal_cache_control_c1 | 2 / 0 | 2 / 0 | 0.893737 / 0.893737 / n/a | 0.928904 / 0.928904 / n/a |

The actual MiniLM instance reports a product RLock and CPU execution. Prediction is serialized per shared instance. Two-concurrent warm latency increased after failures were removed; old failures ended quickly and lower the old all-request median. Request timing includes local retrieval, reranking, filtering and local connection overhead, and excludes model loading and postflight hashing. It does not measure the complete chat API, answer generation or checking.

All 65 public database tables and schemas, 4 original PDFs, 44 registered source supplements, 80 official packaged resources, 3 optional ONNX resources, resource/data/model-cache/staging trees, environment bytes and modification time, and idle queue/worker-lock observations remained equal within each run and between runs. Owned process and approved source versions changed between runs; each recorded runtime identity is bound to its own manifest.

Four top-source checks are identical between the pilots and match registered pypdf_bookmarks_v5 replay and the independent native decoder on those selected pages. Earlier operational provenance retains two affected cases, four false native span comparisons and three distinct PDF pages (64, 111 and 112). Those extractor-specific differences remain unresolved and were not retested by these four different pilot source checks.

The normal-cache control records one miss followed by one hit. The successor hit avoided query encoding but had a larger observed retrieval time; two observations cannot establish a total latency gain. Cold loading and the first subsequent query remain separate populations. Human and scientific quality labels are zero. No provider calls, authentication, database writes, source changes, process changes or protected credential reads occurred in either retrieval pilot or this receipt-only comparison.

All per-request timings, failed attempts, batch denominators, source-check hashes and population calculations are retained in the adjacent CSV and JSON. The previous failed receipt remains unchanged.
