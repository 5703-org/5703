# Independent read-only result review

Reviewer: delegated `offline_union31_review` agent. Status: **PASS, no factual blocker**. This review read only the actual result, English report and owned closure; no model/database reruns or writes to E.

- Independently recomputed all 12 P@5 values from top-five frozen labels: Q0 and Q30 all zero; Q13 dense/local BM25/local RRF/MiniLM = 0.2/0.8/0.4/0.6.
- Q13 pool recall = 1/13, 4/13, 2/13, 3/13. Q0 unresolved-label and Q30 zero-positive NULL rules and all full-corpus NULL values match.
- Aggregate confirmed P@5 and unknown upper bound = 1/15, 4/15, 2/15, 3/15; all top-five unknown counts zero.
- All 84 full query/passage pairs fit the actual 512-token window: range 107–341. Separately measured title/section prefixes reach at most 369; no prefix was scored and no pair was truncated.
- Q0 positive rankings, raw MiniLM scores and 340/341 token sizes agree with the report.
- Report distinguishes broad frozen source relevance from sufficient context and answer accuracy, and makes no global retrieval/production-default or title-causality claim.
- Actual result SHA `f386a2d161795d28d3a697efe174021809a08c3a43412a99bd89866791d15d5d` matches the terminal receipt. Owned closure confirms exit0, 5.507645s, no remaining Job processes, closed handles and no cleanup errors.
