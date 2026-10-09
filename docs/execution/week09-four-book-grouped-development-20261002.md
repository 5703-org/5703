# Four-book grouped development pilot

The frozen V20/requirements V6 source ran ordinary complete-answer questions and first-stage teaching arms A/B/C/D against real CPU E5 retrieval, PostgreSQL/pgvector and MiniLM reranking. Generation and checking used `deepseek-flash` through the existing compatible provider adapter. The shared limits were four calls, 180 active seconds and 3,000 evidence tokens per request. These runs used the core service directly; native HTTP persistence and installed ownership have separate evidence.

| Group | Official book and section | Physical PDF pages | Latest executed slots | Delivered | Failed | Provider calls |
| --- | --- | --- | --- | --- | --- | --- |
| G005 | Anatomy and Physiology 2e, 23.3 | 1060 | 5 | 4 | 1 | 18 |
| G010 | Biology 2e, 45.7 | 1383 | 5 | 2 | 3 | 12 |
| G013 | Chemistry 2e, 11.3 | 557, 559 | 0 | 0 | 0 | 0 |
| G022 | Concepts of Biology, 20.2 | 550, 552 | 5 | 5 | 0 | 14 |

The twenty logical slots have fifteen executed outcomes, eleven deliveries, four failures and five unexecuted slots. All forty-four provider starts have recorded replies and finishes; unknown outcomes are zero. Recorded usage totals 405,229 input and 24,378 output tokens, or 429,607 tokens. Each total was checked against its recorded stage usage. Invoice cost is null because the actual calls remain unpriced.

The original first pass executed ten slots and delivered nine, with thirty-two calls. Both G010 and G013 stopped before model invocation because accepted retrieval did not contain their complete declared source anchors. G010's lead paragraph fell below the provisional relevance cutoff. Replaying the existing one-pass native supplementary lookup recovered its complete anchor without changing the cutoff or adding reference text. The subsequent five-slot G010 run delivered B and D. QA, A and C failed strict output validation after their one allowed format repair. Their generated fields conflicted: an answer contained a refusal reason, or a refusal retained answer-only fields. No checker correctness verdict exists for these three failed transports.

G005 D retained `CHECKER_INCONSISTENT`: the checker recorded sufficient context and simultaneously named deliberately withheld hint content as missing source information. This is an actual contract contradiction; the correctness of the rejected draft still requires independent review. The existing contradiction gate remained enforced.

G013's native supplementary lookup added three source chunks and still missed the complete conditions and reaction exception. A separately pinned generic applicability query added six chunks but also missed both anchors. It made zero provider calls and preserved the same source and all-table identities. The private applicability candidate remains unintegrated. The failed original preflight, native supplement and private probe remain retained. The chemistry slots are unexecuted rather than model-answer failures.

All original database rows across sixty-five tables, official files, corpus releases, vectors and frozen source inputs were preserved. Current source was frozen at 844 inputs for these runs. The original four-book publication contains 10,594 real 384-dimensional vectors.

Independent correctness labels and human scores are zero. Prior exposure is unconfirmed, so the cases are development observations. First-stage publication counts establish neither causal improvement nor the usefulness and disclosure quality of the teaching method. Later teaching stages, cumulative disclosure and independent source-support evaluation retain their own acceptance requirements.

[Actual outcome, usage, timing and receipt metadata](../../evidence/week09-continuation/20261001/four-book-v20-grouped-development-20261002.json) preserves all fifteen executed slots and their four failures. Audit elapsed time includes local preservation checks; model-stage timings are separately recorded. The earlier V20 gate remains the source identity for these outcomes.
