# Public quality19 read-only review

**PASS: public evidence is consistent; no factual blocker.** Main and delegated independent reviews accessed public metrics, frozen plans, wire proof, terminal receipt, current public reference evidence and pinned closures only. No Gold, scorer data, model, database, API or key was accessed; no files on E were written.

| Matched arm | MCQ | OpenQA original EM/F1 | Supplementary alias |
|---|---:|---:|---:|
| E0 none | 3/3 | 2/3 | 3/3 |
| E1 dense | 3/3 | 2/3 | 3/3 |
| Hybrid plus rerank | 3/3 | 2/3 | 3/3 |

The 18 matched records cover exactly three original exposed questions × two tasks × three arms, without duplicates or omissions. All actual wire SHA/byte counts and source IDs match their frozen plans and public reconstruction proof; that proof records 18/18 unchanged run02 wires. Each task uses one identical system prompt across arms, explicitly allowing own knowledge and relevant current evidence with the same confidence standard. Questions are unchanged; MCQ alone supplies options. History is empty and profile use is false. Model, JSON output mode, max768/window131072 and null temperature/seed are shared.

Slot19 is a separate Q0 OpenQA reference diagnostic, not part of the matched18. It uses only current-release public Chemistry 2e chunks `77803fef15a0c4f5b35a8ba5fdca2e05b081` and `9ce7b8e67e19e6d62ed2742078c3db8950f6`; both exact full-text hashes match. Original EM/F1 is 0, supplementary whole-answer alias is 1. Shared terminology equivalence does not establish a RAG gain, human semantic correctness or held-out accuracy.

All19 records completed with HTTP200 and one POST each. Row costs sum to **USD0.0092420**; unknown holds are zero; retries/unstarted records are zero. Current quality19 closure reports exit0, owned Job active-zero, closed handles and no cleanup errors; terminal receipt records disposed engine and cleared in-memory key references. Earlier exit1 closures are retained failure evidence. Launcher `physical_calls_claimed_by_launcher=0` is not the actual-call counter: use the worker's19 records/count.

Generation receipt says Gold_reads=0. Post-closure scoring explicitly read three Gold questions locally and exported no Gold text/labels. This review did not read them or independently recompute correctness against Gold; it validated exported scoring/aggregate consistency. Alias scoring remains a supplementary diagnostic.

P@5 measures frozen source relevance, not complete answer sufficiency. The quality19 durations cover adapter generation only, not retrieval/checker/native full HTTP response latency. Do not combine them with old cold/warm timings or present the previous free ranking worker runtime as answer latency. No production ranking-default adoption follows from these three DEV questions.

Primary public metrics SHA: `a2c63a9a8663059b267b2d0f21c8d06fb51a81dc921a3b58796cc8a6d83ae265`; frozen-input SHA: `a76304e5af9b4a86bb34b16f490930c3f9c0d90b22e39c69b85f09b085c76c74`; terminal-receipt SHA: `abdc5d49a3f6f1119ea29fe7f6c67fd1e7e85ed001b90314c8d7b9134df6eeb4`. Each primary pin was verified once; no repeated full-file hashing was needed.
