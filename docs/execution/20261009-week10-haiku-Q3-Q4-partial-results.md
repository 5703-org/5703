# Haiku Q3 stopped after a checker rejection; Q4 was not executed

The final Haiku attempt submitted two provider POSTs for Q3. The teacher returned HTTP 200, with a recorded fee of **USD0.00163590**. The checker returned HTTP 400 and its fee remains **UNKNOWN**; its full **USD0.03000000 protection hold** is retained. No checked answer was published. Q3 failed, Q4 was not submitted, and the two-question same-worker acceptance remains incomplete. The selected campaign now has **10 POSTs and a known fee subtotal of USD0.04150604**; its actual total fee is unknown. [Final financial receipt](evidence/20261009-week10-haiku-partial05/analysis-preparation/ACTUAL_CONTINUOUS05_HAIKU_Q3_Q4_FINANCIAL_RESULT01.json)

## The zero-call setup failure and the paid partial failure remain separate

| Attempt | Observed result | New provider POSTs | Fee disposition |
| --- | --- | ---: | --- |
| actual04 / nonce ending `-01` | First normal empty chat created; second New chat selector collided with a selected history entry. The free two-chat proof was absent. Q3/Q4 were not submitted. | 0 | USD0.00000000; no new UNKNOWN/open claims |
| actual05 / nonce ending `-02` | Both normal chats were ready on the same live worker before any POST. Q3 teacher completed; checker rejected the request. Browser answer wait failed. Q4 was not submitted. | 2 | Teacher USD0.00163590; checker UNKNOWN with USD0.03000000 hold |

The actual04 controller and native leg remain failed. Resource cleanup does not convert that attempt into acceptance. Its valid financial result is **RESULT02** (original SHA `e129653f86699cf16f34619411e7880019319699549dab08f3638703accd71b1`); the preserved six-byte RESULT01 contains JSON null and is excluded from valid evidence. The successor only repaired the browser creation-button locator and execution bindings. It used the original unconsumed **four-POST / USD0.12000000 allocation**, with **USD0 new funding**. Earlier eight submitted slots and all historical STOPs/protection holds were preserved. [actual04 review](evidence/20261009-week10-haiku-partial05/continuous-preparation/HAIKU_ACTUAL04_READONLY_REVIEW01.json); [actual04 valid financial receipt](evidence/20261009-week10-haiku-partial05/analysis-preparation/ACTUAL_CONTINUOUS04_HAIKU_Q3_Q4_FINANCIAL_RESULT02.json); [successor authorization snapshot](evidence/20261009-week10-haiku-partial05/continuous-preparation/CONTINUATION_AUTHORIZATION_SCOPE05.json)

## Q3 reached native retrieval and the full checker dispatch

Q3 asked: “How do enzymes lower activation energy without changing a reaction's equilibrium?” Its UTF-8 question SHA is `e76bbd2a087b7e7d08edb4ead1ff913c7401ca8354bbd5f97f18e5ece17c917b`; the normal submission input SHA is `0fddbff6ebaaaa902edcbb9a6c6c10bff523f0ec1a6b378f3085d86fa5cf69f9`. It used ordinary chat with no reading context or chapter filter and retrieval scope `all_active_corpus`. The request was `1e7fb2de-b48f-4fd9-b70e-8a19bb46fd58` and native job `bd094002-5cc1-4257-ac82-ed8f7afc5991`. These are synthetic measurement identifiers. [Q3 scope](evidence/20261009-week10-haiku-partial05/runtime-continuous05/scope-Q3-public01.json)

The actual05 free preflight established both normal chats on one live worker, PID **75500**, Engine identity **1919648521520**, **3391.366 ms before the first POST**. Q3 execution used that same worker and Engine, with the observed epoch unchanged. Only Q3 executed; this does not establish two-question cache reuse. [prepaid readiness proof](evidence/20261009-week10-haiku-partial05/browser-continuous05/normal-two-chat-prepaid-readiness-public01.json); [finite runtime review](evidence/20261009-week10-haiku-partial05/continuous-preparation/HAIKU_ACTUAL05_READONLY_REVIEW01.json)

| Q3 native stage | Observed value |
| --- | ---: |
| R2 validated release cache | Hit; validation 3.796200002398109 ms |
| Query-vector cache | Miss; query embedding 15.869599999859929 ms |
| Dense retrieval | 45.54389999975683 ms |
| Lexical retrieval | 4.9987999991572 ms |
| Retrieval total, as instrumented | 91.70860000085668 ms |
| CUDA reranking | 146.5213000010408 ms; 20 candidates |

These are distinct native stage measurements; they are not a completed-answer timer or an additive end-to-end speedup estimate. Existing cumulative CUDA peaks were **365905408 allocated bytes / 423624704 reserved bytes** on an NVIDIA GeForce RTX 5070 Ti, without resetting peak counters. RSS was unobserved. The worker used four CPU threads and one worker process. [native Q3 trace](evidence/20261009-week10-haiku-partial05/runtime-continuous05/native-retrieval-1e7fb2de-b48f-4fd9-b70e-8a19bb46fd58-public01.json)

The teacher's public adapter duration was **5909 ms**, with HTTP200 and no local error. The actual normal full checker dispatch followed, but returned **HTTP400 / PROVIDER_HTTP_ERROR** after **1104 ms**. Actual model-input hashes match the fresh native descriptors. Teacher completion alone does not establish checker schema compatibility or answer quality; the raw teacher output was not inspected for this report. [public adapter receipts](evidence/20261009-week10-haiku-partial05/runtime-continuous05/adapter-public01.jsonl); [actual model-input pins](evidence/20261009-week10-haiku-partial05/runtime-continuous05/actual-model-inputs-public01.jsonl)

Root subsequently performed one read-only SELECT restricted to this owned synthetic job and selected only sanitized existing finish fields, with zero new provider POSTs. The teacher finish row reports stop, 13474 input / 577 output tokens and the same recorded fee; its retained provider-request identifier is not assumed to be a generation identifier. The checker finish row has HTTP400, error code 400, null error type/parameter, and gateway category unknown_provider_failure based only on http_status. Its diagnostic message was redacted and not selected; finish reason, usage, fee and provider-request ID are null. The exact remote rejection cause remains **NOT_OBSERVED**, and no checker ID is available for billing reconciliation. No schema/parameter, balance or scientific quality cause is established. This is a failed checker without a published result, rather than a valid result with merely missing cost. [Finite existing-job diagnostic](evidence/20261009-week10-haiku-partial05/diagnostic-review/ACTUAL_HAIKU_Q3_EXISTING_DIAGNOSTIC01.json).

## Complete-answer time and citation acceptance are unobserved

The browser received the normal submission HTTP202 after **301.2001953125 ms**. It then recorded `ANSWER_RENDER_TIMEOUT_RIGHT_CENSORED` after **300022.20009765774 ms** from Send. This is a censored failure wait, not a successful answer duration or TTFT. First answer paint, complete answer DOM, published answer ID, native publication timing, launch-to-complete-answer timing, citation validation and refresh persistence were unavailable or not passed. The provider checker rejection and the browser wait failure are separate observations. The retained failure screenshot shows the final UI state rather than a published answer. [browser receipt](evidence/20261009-week10-haiku-partial05/browser-continuous05/real-browser-live-qa-receipt01.json); [masked final screenshot](evidence/20261009-week10-haiku-partial05/browser-continuous05/retained-failure.png); [final text](evidence/20261009-week10-haiku-partial05/browser-continuous05/retained-failure.txt)

Startup timing remains separate: process launch to worker ready **14993.90234375 ms**; runner main entry to ready **14070.136999998795 ms**; native model warm-up boundary **5672.613100003218 ms**; release preparation **6221.413499999471 ms**; worker ready to Send **6472.933837890625 ms**. The separate model-prewarm receipt reports **5672.6277000016125 ms** for its own total boundary, with a different query and no provider POST, corpus/DB retrieval or measured-question query-cache population. These observed startup/preparation numbers do not fill the missing completed-answer time. [startup receipt](evidence/20261009-week10-haiku-partial05/runtime-continuous05/worker-startup-preparation-public01.json); [model-prewarm receipt](evidence/20261009-week10-haiku-partial05/runtime-continuous05/native-prewarm-public01.json)

Q4, “How does a phospholipid bilayer's structure affect what can cross a cell membrane?”, was precreated as a normal chat but **not submitted**. Its original authorization was conditional on Q3 fully passing and at least two slots remaining. Q3 did not pass; the terminal UNKNOWN-cost STOP also prohibits automatic reuse of the two remaining slots. No retry, replacement, Q4 execution or additional model call is implied by this report. [immutable actual05 STOP](evidence/20261009-week10-haiku-partial05/claims-continuous05/STOP-before-any-next-submission01.json)

## Recorded fees, modeled bounds and protections use different meanings

| Cost or limit | USD | Meaning |
| --- | ---: | --- |
| Q3 teacher fee | 0.00163590 | Known recorded provider fee |
| Q3 checker fee | UNKNOWN | No exact fee in retained cost evidence |
| Checker protection hold | 0.03000000 | Retained full hold; not an amount spent |
| Prior selected eight-POST known subtotal | 0.03987014 | Previously settled selected campaign context |
| Selected ten-POST known subtotal | 0.04150604 | Known subtotal only; actual total remains null |
| Original new allocation protection | 0.12000000 | At most four POSTs; two consumed, two stopped |
| Metadata four-POST uniform-output modeled bound | 0.03239680 | Prepared tariff estimate, not actual fee |
| Retained guard four-POST strict bound | 0.11357440 | Conservative existing price-cap bound |
| Selected campaign maximum protection | 0.36000000 | Existing twelve-slot maximum; no increase |

The prepared bound uses a 60000-byte wire limit / 60512 input-token upper bound, teacher cap 2048 and checker cap 4096, without relying on cache discounts, explicit cache writes or web search. UNKNOWN is retained even for the HTTP400 response; this report does not assume the rejected request was free. Open claims are zero, UNKNOWN count is one, and the batch is **not fully settled**. Historical fourteen UNKNOWN holds are retained without reading or reconstructing their raw ledgers. [prepared cost mathematics](evidence/20261009-week10-haiku-partial05/analysis-preparation/HAIKU_Q3_Q4_COST_BOUND_PREPARED01.json); [final cost/STOP reconciliation](evidence/20261009-week10-haiku-partial05/analysis-preparation/ACTUAL_CONTINUOUS05_HAIKU_Q3_Q4_FINANCIAL_RESULT01.json)

## The route is experimental and project activation remains false

The finite scope used OpenRouter model **`anthropic/claude-haiku-5.5`**, route **`google-vertex/global`**, profile **`haiku55_google_vertex_low_v1`**, canonical reasoning **low**, adaptive thinking, and no temperature parameter. The production default model was not changed. The anonymous official model metadata was captured at **2026-10-09T06:25:45.747520Z**; catalog support for reasoning or structured output is configuration information, not an observed native compatibility PASS. [official public metadata snapshot](evidence/20261009-week10-haiku-partial05/continuous-preparation/PRIMARY_MODEL_PUBLIC_METADATA_ACTUAL01.json); [opt-in route adoption](evidence/20261009-week10-haiku-partial05/free-validation/ACTUAL_HAIKU_PUBLIC_ROUTE_ADOPTION07.json)

The affected isolated free validation recorded **101 passed / 20 optional SDK cases skipped in 0.21 s**, with Ruff PASS, no provider calls, no real database, no dotenv, and no network/socket access. It was a targeted free check, not a full-suite rerun or paid route qualification. [free validation receipt](evidence/20261009-week10-haiku-partial05/free-validation/ACTUAL_HAIKU_ROUTE_TARGETED_FREE_VALIDATION08.json); [exact summary](evidence/20261009-week10-haiku-partial05/free-validation/ACTUAL_HAIKU_ROUTE_FREE08.log)

`normal_project_activation_qualified=false` remains in force. The initial role receipt still says `PENDING_NOT_EXECUTED` and was not promoted after failure; that initial descriptor is not proof that actual05 sent zero requests. No six-role qualification, accepted semantic/citation quality, two-question same-worker completion, p95, quality superiority or cross-model controlled comparison was established. Previous Gem qualification and the separate earlier Q1/Q2 runs do not qualify Haiku. The requested GPT6Luna-on-existing-OpenAI and existing successful DeepSeek cases have no results in this four-POST Haiku scope. [initial role/activation disclosure](evidence/20261009-week10-haiku-partial05/runtime-continuous05/role-qualification-public01.json)

## Closure and evidence provenance

Both owned actual05 processes closed with exit code 1, collectors completed, and owned threads and database resources closed with no cleanup error classes. Eight cleanup-start records bind eight finishes, all handles closed. No forced owned abort was used. These resource facts preserve **`CLEANUP_FAILED_OR_LEG_FAILED`** and the controller's failed/no-retry result; native normal CLOSED, whole-leg PASS and fully settled billing are not claimed. [runtime closure](evidence/20261009-week10-haiku-partial05/runtime-continuous05/runtime-closed-public01.json); [controller result](evidence/20261009-week10-haiku-partial05/continuous-preparation/ROOT_CONTINUOUS_CONTROLLER_ACTUAL05.json)

The production source-version pin is **`8c6a6933f7af2ba4876913f752b16f0d661da2eaec8e9cf5dc302461f158d4b1`**. [The public evidence index](evidence/20261009-week10-haiku-partial05/index.json) lists original bytes and SHA256 for each exact local copy. Earlier review/financial receipts remain immutable even when the later finite diagnostic adds information. Mutable readiness observations may embed pins for earlier snapshots; their historical pins do not assert that a later snapshot has identical bytes.

The separate sanitized export preserves source SHA256 and adds the transformed-file SHA256 in its manifest; it removes machine-specific paths/usernames and excludes authentication, secrets, private fixtures, raw child logs/provider wires, databases, model weights, large source/guard indices and old raw UNKNOWN ledgers. Synthetic measurement IDs and public source attribution are retained. The packaging agent made no Main changes, Library upload, provider POST, API request, database connection or test run. Existing evidence and previous Library identities remain unchanged.
