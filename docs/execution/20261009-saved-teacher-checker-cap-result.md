Latest 5703 mixed-role result, 2026-10-09 UTC: actual ordinary Q2 used Haiku teacher plus Gemini checker, 2 POSTs/$0.0089282 known, new UNKNOWN0, fully settled. Gemini omitted required attempt_evaluation_ok (Pydantic missing -> CHECKER_SCHEMA_INVALID -> CHECKER_INCONSISTENT); no published answer/citation/refresh PASS. Browser observed failure after14296.39990234375ms, while complete-answer/TTFT clocks remain null. Free actual failed-terminal UI and28/28 public preflight passed. Owned resources closed and pointers unchanged. This two-call scope is exhausted; old .09 UNKNOWN and canonical counts/project_complete=false remain unchanged. See [mixed-role actual report](20261009-haiku-teacher-gemini-checker-native-result.md) and [public evidence](evidence/20261009-haiku-teacher-gemini-checker-native01/index.json). Earlier document bytes follow unchanged.

# Saved-teacher checker output-cap regression — 9 October 2026

Current result: **8192 ended without truncation, but strict JSON and the full business gate failed.** The actual generator returned `CHECKER_INCONSISTENT`; no answer was published. The conditional 16384 request was not executed because the first response ended with `stop`, rather than `length`. There is no passing output cap from this experiment.

The new, separately authorized scope permits at most two checker POSTs and USD0.06. It starts with zero new calls/charges/holds and preserves the older scopes and USD0.09 UNKNOWN protections. This execution used exactly **one physical POST**, cost **USD0.0042585**, and settled its USD0.03 hold with **zero new UNKNOWN**. The physical ceiling has one unused slot and the monetary ceiling has USD0.0557415 arithmetically remaining. Neither changes the unmet truncation condition for the second request.

The input was the exact saved teacher response for native request `ca4ccd11-0500-4a55-8eb1-c2a68b48d8fa`, job `0e5c02b0-6dd1-4030-a9ea-e6a05538f3a3`, from `cs30_week10_pair_b_20261009_01`. That response is 1345 bytes, SHA-256 `f5fc06d9eabb5483997ce3a1bd0a86a413f3a9825598fa4560a7f334d46e655f`. Only this existing synthetic database was read, in read-only transactions. There were no new teacher POSTs, DB writes, jobs, sessions, publications, dependency installations or database reconstruction.

Free preflight reconstructed the request through the existing native evidence packing and source-map functions. It reproduced the saved teacher messages/schema and checker messages exactly. The actual checker wire retained message hash `cfc2afafdc8f0789dc2dcb5884a786f34a7268190f184c2aba38d4aa1dfe3b1d` and full local schema hash `7988037e08d52662a1b232f049776a42b6d10ad5d896f1a26c8c912b3efd79d4`. GenerationService reused one cached teacher result and the ordinary LLMAdapter for one actual checker call. Full teacher, strict JSON, Pydantic, evidence/source, identity and publication checks remained in place; subsequent repair calls were blocked.

The model and route remained `anthropic/claude-haiku-5.5`, `haiku55_google_vertex_low_v1`, `google-vertex/global`, without fallback, using experimental `json_object`. `reasoning: {"effort":"low"}` was actually on, not disabled. OpenRouter documents that the output allowance normally includes reasoning and visible output together, and reasoning is charged as output. [Official reasoning-token documentation](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

| Observation | Previous native checker | New saved-teacher checker |
| --- | ---: | ---: |
| Output cap | 4096 | 8192 |
| HTTP status | 200 | 200 |
| Finish reason | length | stop |
| Input tokens | 15870 | 15870 |
| Output tokens, including reasoning | 4096 | 5343 |
| Reasoning tokens | 2885 | 3496 |
| Visible-output tokens by subtraction | 1211 | 1847 |
| Raw output bytes | 3148 | 4633 |
| Adapter elapsed time | 18723 ms | 22353 ms |
| Known checker cost | USD0.003635 | USD0.0042585 |
| Full schema/business PASS | false | false |

The new request tightened the existing provider price cap to USD0.10/M input and USD0.50/M output, matching the anonymous official endpoint metadata. [Official model endpoint metadata](https://openrouter.ai/api/v1/models/anthropic/claude-haiku-5.5/endpoints). Its 45364-byte wire has a conservative input bound of 45876 and maximum cost USD0.0086836 at 8192, below the admitted USD0.03 hold and the 100000-token high-price threshold. The identical message hash confirms the question, evidence and saved answer were unchanged; the output allowance and protective price ceiling were the intentional wire-control changes.

The new raw-output hash is `43cddb016929ba2e5faf4d75205a9d3d306b2e92168e74b07726e94d9d054e38`. The strict parser raised `ResponseValidationError`, and the ordinary generator returned `CHECKER_INCONSISTENT`. `finish_reason=stop` is not proof of complete valid JSON. The exact strict-JSON subcode and failing field were not retained by this runner, and raw text was not exported. Consequently, this evidence does not identify a particular duplicate key, malformed field or redundant repeated structure. It cannot justify removing required fields, relaxing the schema or truncating the teacher answer. Subsequent diagnostics should retain safe parser codes, business issue codes and structural metadata in memory before releasing the response, without another request solely to compensate for missing instrumentation.

A first local startup failed before any POST because changing the frozen checker timeout to 120 seconds caused `ENHANCEMENT_VALIDATION_ERROR`. A free comparison confirmed this. The same authorized scope then continued with the original timeout, an outer 180-second deadline and a copied immutable request. The original authorization receipt remains unchanged; the zero-POST correction allocated no additional budget.

The preflight receipt's `selected_evidence_count=20` is a labeling error: it counts frozen retrieval candidates before selection. The postcheck explicitly corrects that interpretation. Exact teacher/checker message and schema comparisons remain valid.

The earlier browser failure's approximately 300-second wait remains right-censored; no full-answer latency was observed. Main Chat already handles received failed/cancelled jobs. Runtime09 can shut services down on its 200-ms STOP poll before the page's next 750-ms job poll. Browser14 now has a nine-line public-STOP observation candidate with Node syntax and seven isolated synthetic cases passing. Runtime10 prepares a bounded, at-most-three-second GET terminal-delivery grace while denying new non-GET requests immediately. Runtime10 has only AST validation; neither candidate has a new live browser acceptance result. A STOP observation is not a fabricated job state or error code.

This is a local development regression, not a unified three-model RAG quality comparison, native publication PASS, full-answer timing sample or project completion. Production model/protocol/cap defaults and canonical completion counts remain unchanged. Remaining work is to diagnose and repair the strict checker-output contract using preserved structural evidence, then perform native complete-answer acceptance and the separately scoped unified comparison. The present 16384 truncation condition was not met; no automatic extra POST or teacher rerun was performed.

Public receipts, exact runner source, free preflight, accounting postcheck and observer preparation evidence are listed in `evidence/20261009-saved-teacher-checker-cap01/index.json`. Original reports, old STOPs, experiment data and protected staging directories remain intact.

Prepared instrumentation follow-up: a small error-code-only observer diff now retains strict parser codes and the existing safe business/schema issue codes. It has syntax validation only, made zero additional POSTs, and changes no acceptance contract. The exact source used for the actual request remains archived separately as runner-used01.py. The completed scope was not reexecuted.
