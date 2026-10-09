# Actual free fixed-pool ranking ablation

Status: **ACTUAL PASS, 12 cells**. Three original exposed DEV questions use unchanged frozen candidate unions of 31/25/28. All 84 question-specific candidate memberships were preserved; 83 distinct public released vectors were read in a read-only transaction. No provider, key, Gold, installation, download, database mutation, or production-default adoption occurred.

| Question | Union | Dense P@5 | Local BM25 P@5 | Local RRF P@5 | MiniLM P@5 | Pool recall |
|---|---:|---:|---:|---:|---:|---|
| sciq:test:000000 | 31 | 0.0% | 0.0% | 0.0% | 0.0% | NULL: unresolved judgment |
| sciq:test:000013 | 25 | 20.0% | 80.0% | 40.0% | 60.0% | Dense E5=0.076923, BM25 (local)=0.307692, RRF (local consensus)=0.153846, MiniLM=0.230769 |
| sciq:test:000030 | 28 | 0.0% | 0.0% | 0.0% | 0.0% | NULL: no pool positives |

| Arm | Confirmed positive positions / 15 | Aggregate P@5 | Unknown in top5 | Unknown upper bound |
|---|---:|---:|---:|---:|
| Dense E5 | 1/15 | 6.67% | 0 | 6.67% |
| BM25 (local) | 4/15 | 26.67% | 0 | 26.67% |
| RRF (local consensus) | 2/15 | 13.33% | 0 | 13.33% |
| MiniLM | 3/15 | 20.00% | 0 | 20.00% |

All full-corpus recall values are NULL. Q0 has 2 confirmed positives and 1 unresolved label in its frozen pool; Q13 has 13 broad source-relevance positives and no unresolved labels; Q30 has no positives within its frozen pool. The local BM25 advantage comes entirely from Q13 and is not a three-concept general gain or evidence of answer accuracy.

## Actual input policy and windows

Original query plus complete passage, without title prefixes: all 84 pairs fit the actual 512-token MiniLM window; range 107–341 tokens. No truncation occurred. Title plus section prefixes were measured separately and not used by any arm: maximum 369 tokens; 0 pairs would exceed the window.

Dense uses real E5 original `query: ` preprocessing and unchanged 384-dimensional released vectors. BM25 computes df/average length from each fixed candidate union. RRF combines the complete local dense and BM25 orders using constant 60. MiniLM scores every member of that same union in batches of at most 20, then merges unchanged raw scores. These are candidate-pool ordering experiments, not the original global 10,594-chunk BM25/RRF or native application request latency.

## Q0 positives: full-passage ranks and source sufficiency

| Frozen positive | Dense rank | BM25 rank | Local RRF rank | MiniLM rank (score) | Full pair tokens |
|---|---:|---:|---:|---:|---:|
| 8efc481e91b5eb09f5b600e88df6c5e2d5d7 | 8 | 29 | 23 | 31 (-9.732388) | 340 |
| 980cf9eb26835ac1280058e6e424eac52725 | 18 | 18 | 25 | 28 (-7.747611) | 341 |

The two Q0 positives overlap the same Chemistry 2e oxygen discussion. One names elemental oxygen as an oxidizing agent; the other says oxygen picks up electrons. They support an oxygen example, with weaker coverage of the general accepting-electrons category and no direct full O2/F2 definition. They are not two independent confirmations. The unresolved Q0 chunk mixes a reducing-agent/electron-acceptance statement; the unknown label remains unchanged.

Previously expanded union31 MiniLM P@5=0 remains a preserved negative result. Current four-arm Q0 P@5 is also zero. No full-passage window overflow explains the loss of these two passages; actual ordering failure and weaker candidate evidence are both visible, but no causal attribution to title absence or model architecture is established.

## Source review, without relabeling or adding candidates

Q13 chunk `2d35d25312f29f65e337e7343310193c8f8a` explicitly lists all three organs within the testicular/male reproductive system and is the strongest reviewed complete support. Other frozen relevant passages can mention only testes, a disorders heading, a sperm route, or a figure caption. Relevance and complete answer sufficiency therefore differ. Keep the published frozen P@5 values, but do not interpret local BM25 0.8 as 80% fully sufficient answers.

Two independently reviewed public current-release definition passages remain OUTSIDE all fixed unions: `77803fef15a0c4f5b35a8ba5fdca2e05b081` (Chemistry 2e, 4.2 Classifying Chemical Reactions, physical PDF pages 183–184) connects chlorine gaining electrons with oxidizing agent/oxidant; `9ce7b8e67e19e6d62ed2742078c3db8950f6` (Key Terms, page 206) links oxidizing agent becoming reduced with reduction gaining electrons. Both supply stronger category-definition support than the overlapping oxygen examples. They do not directly establish both O2/F2 examples. Their hashes match the existing public reference evidence. Long lead-in text and separated definitions could affect relevance scoring, but that explanation is only an inference: neither was tokenized or scored in this fixed-union experiment.

Q30 topic-only chunk `418b90deba1313869c2dfd814ac4cb3f5ed7` concerns crust and atmosphere together; its visible Al percentage has a different denominator from crust alone. Zero positives in this pool does not mean the whole public corpus lacks an adequate answer.

## Manifest convention, prior failures and closure

Attempts01/02 stopped before model scoring at a manifest-hash assertion and are retained. A bounded read-only diagnostic proved the old frozen receipt used compact JSON in insertion order (SHA `855b2bd12a5732a0c1cc5d2df5dafe687fcc848a4b7f0f495b220c38f878fdd7`); compact canonical sorted JSON is SHA `c7853256b3c5cc51e717ad86d25ba7e7d2c50244647027b7b0c6b2133bd72b16`. Current actual manifest and SHA-pinned original native public scope match under both conventions. Attempt03 preserves BOTH assertions and also requires complete manifest/configuration equality, unchanged epoch, four public documents, exact candidate full text/provenance and normalized E5 vectors.

Attempt03: owned child PID 50212 exited 0 in 5.507645s. The specific Job had no processes at cleanup; process and Job handles closed; cleanup errors empty. All 12 cell memberships and source/model-metadata pins were rechecked after scoring. This duration is the bounded diagnostic worker runtime, not complete checked-answer HTTP response latency.

Actual result SHA: `f386a2d161795d28d3a697efe174021809a08c3a43412a99bd89866791d15d5d`. Inputs03 SHA: `ef0baa5d5c6f6a9f875509ebd9bc9930c208099fdcc53a0dd98a46a3c68c81e7`. Worker03 SHA: `99cd18b2ac8e4dc25c32860d86187047c9d8c58d16dfcc76047b9b4dbcd33ce9`.

Evidence: `attempt03/fixed-pool-four-arm-results01.json` (all rankings/scores/top5/window checks); `attempt03/fixture-readonly-observations01.json`; three query batch receipts; `attempt03/terminal-receipt01.json`; `owned-run03/closure.json`; `manifest-hash-diagnostic03.json`; preserved `attempt01`, `attempt02` and their owned closures.

Next decision: do not adopt a production ranking default from these three exposed questions. Candidate coverage and source sufficiency, especially Q0/Q30, require separate evaluation; the native checked-answer path and its complete response latency remain a separate parent-owned task.
