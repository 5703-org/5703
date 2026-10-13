# CS30-1 S01 native-page acceptance and bounded RAG comparison

Client checkpoint: 13 October 2026, Australia/Sydney. Actual browser events occurred on 12 October UTC. Scope: E:\5703\learning-assistant only.

Three genuine live checked answers were persisted, rendered with citations, retained after refresh and reopened through the Sources control. The primary same-question R0/R2 pair completed, but neither answer met the 5–10-second target and this single exposed question demonstrates no general quality winner.

## Observed outcomes

| Frame | Treatment | Result | Send to complete DOM | Sources submitted | Inline citation occurrences | POSTs | Peak-tariff upper CNY |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 101 | R2, initial 16K window | CONTEXT_LIMIT before model dispatch; browser wait censored at 210s | null | not submitted | 0 | 0 | 0 |
| 102 | R2, 64K, no explicit prewarm | Complete checked answer; refresh/source reopen PASS | 24.3501s | 8 | 7 | 2 | 0.083184 |
| 103 | R0, query-vector prewarm | Complete checked answer; refresh/source reopen PASS | 21.5363s | 5 | 9 | 2 | 0.090162 |
| 104 | R2, query-vector prewarm | Complete checked answer; refresh/source reopen PASS | 19.4613s | 8 | 7 | 2 | 0.079432 |

The actual denominator is four attempted browser journeys: one local configuration failure and three published answers. The primary comparison is frames103/104, one exposed S01 question per arm, not two independent questions. The failed initial API startup additionally violated native Settings limits before any API claim; the successor retained native limits instead of weakening Settings.

## Common conditions and verified differences

Both primary arms used the same question, four active OpenStax books, exact10594 released chunk identities, CPU, fresh empty synthetic sessions, disabled profile/history, current checked.py ce58, source-relation V2, typed joint V5, 65536-token window, official deepseek-flash for both roles, temperature0, non-thinking JSON-object mode, teacher2048/checker4096 output caps and two-call native budgets. R0 used the verified release's dense retriever/top5; R2 used its frozen20-candidate hybrid/pinned MiniLM policy. Those retrieval treatment differences are intentional. No Gold or actual learner history was sent.

Actual query joins match both prewarm queries; both measured query-vector cache hits are true. Both release-index hits are false, however. Readonly prewarm bound a Connection while the measured worker bound its Engine, yielding different existing cache keys. Describe these as query-vector-warm/release-index-cold observations, not fully warmed end-to-end arms. New processes and sequential R0→R2 order, single samples and differing generated lengths prevent a causal speed claim or p95 calculation.

## Quality evidence and limits

Both primary outputs satisfied the online checker's requested-help completeness, source binding and normal publication rules; each records no missing requirements and human_rating=null. A separate limited AI review found the definition and reaction-effect requirements covered and main claims faithful to actual sources. R0 supplies more explanation; R2 is shorter. Both repeat source-derived collision-force and absolute no-change simplifications that can mislead despite source fidelity. There is no independently demonstrated quality gain or formal quality acceptance. Stored R0 source/wire/answer notation is ∆G (U+2206), not a literal ?G; original text was not rewritten.

No paid answer required claim_patch_repair or a fresh repair recheck. These results therefore do not measure localrepair100's live repair efficacy or speed. Its43-test software evidence remains separately version-bound.

## Timing and free warmup correction

R0 worker retrieval6.668526s, teacher2.920s and checker10.710s; R2 retrieval7.604300s, teacher2.374s and checker7.928s. DOM latency includes queue/publication/poll/render overhead. First published prose is not streaming TTFT. None of the three successful DOM answers finished within10s; warm p95≥30% reduction and quality non-inferiority remain unmeasured.

The future experimental prewarm helper now uses clean Engine-bound sessions, first SQL SET TRANSACTION READ ONLY and explicit readonly assertions. Free verification against the original isolated public fixture produced cache miss→hit: first5.536688s, second11.1884ms (validation3.5371ms). Both release hashes join the frozen release proof; no database write or provider call occurred. Production cache.py remains byte-identical (85706e87b794b66a7c74a3f270d7ee77c68d3aa41602c9b6fc10374c605cf935), preserving connection/options/epoch isolation. This is cache reuse verification, not a new browser/LLM timing result. Existing credentials were read locally and discarded in memory; this was not zero credential reads.

## Accounting, preservation and delivery

Exactly6 provider responses committed HTTP200/stop and settled usage observations, without retries. The verified conservative peak rates are CNY2/million input and CNY8/million output; total upper CNY0.252778, new UNKNOWN0, within the shared6-request/CNY0.50 authorization. The request ceiling is exhausted; no additional model request is admitted. Prior97's entire CNY0.10 UNKNOWN protection remains retained and separate. These figures are not an invoice or account balance. Official specifications support a1M context;64K is an isolated test configuration, not a private-profile/default change. Reference: [DeepSeek official model/price specification](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/).

All owned browsers, API threads/engines and frontend processes closed. Old session/job/request/answer records and active model pointers passed before/after checks in every frame. The original PostgreSQL container was recovered and retained running; source inputs, old failures, protected staging, earlier delivery and user data remain preserved. Main production code/defaults were not modified during this phase. No other project, remote upload/push/deployment or course submission occurred.

The accompanying results JSON and ZIP preserve scopes, bounded callers, public input/response journals, failed101 records, closed102–104 browser/API receipts, joined public traces, and free105 warmup evidence. Credentials/auth files/private binders are excluded. This evidence archive is not a new application installation package. The older Source04 package remains dated; current common-package/clean-install and connected eight-module acceptance remain open. All seven formal study families and human review remain open; project_complete=false.

Next engineering work: use the corrected Engine-bound warmup in a newly scoped performance run; address misleading scientific simplifications with calibrated review; validate the current common runnable package and complete module journeys. This checkpoint makes no stable5–10s, formal scientific-quality, p95 or whole-course completion claim.
