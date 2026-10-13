# Citation128: S02 proof diagnosis and marker-only candidate

S02's scientific answer is supported under the stated water-permeable, solute-impermeable membrane assumptions. Its original displayed citations are less direct than an unconditional complete-support positive label implies. Independent AI source review supports a provisional three-marker candidate, preserving every original scientific byte. This does not reinterpret either127 S02 response as valid: their pointer and quote-role errors remain unscored.

## Exact returned proof and scope

Source numbers and quote pointers are different namespaces. All returned IDs resolve to real supplied sources and exact table spans; no invented ID or quotation was observed. The shared failure is not uniformly legitimate supporting evidence outside an overly narrow citation selection.

| Provider / claim | Returned quote pointer -> source | Original displayed scope / selected scope | Source assessment |
| --- | --- | --- | --- |
| DeepSeek C1 |Q17 -> S14, ev_003|Outside ev_004 / unselected|Orphan credit `Lathrop)`; no claim support.|
| DeepSeek C1 |Q18 -> S15, ev_003|Outside ev_004 / unselected|Figure11.27 caption directly supports normal isotonic volume, a valid component requiring citation addition.|
| DeepSeek C2/C3 |Q15 -> S12, ev_002|Outside ev_003 / unselected|Tonicity definition does not establish hyper/hypotonic water direction or cell-volume changes.|
| DeepSeek C4 |Q18 -> S15, ev_003|Outside ev_004 / unselected|The RBC-volume caption does not establish ongoing individual bidirectional water movement.|
| OpenAI C1/C4 |Q23 -> S17, ev_004|Inside actual ev_004 / outside selected S18|Isotonic osmolarity definition, not full net movement/normal-volume or continuing-movement proof.|
| OpenAI C2/C3 |Q19 -> S15, ev_003|Inside actual and selected scope|Caption supports volume effects; no explicit direction. Span0:1132 exceeds the600-character claim-role limit.|

DeepSeek's p values17/18/15 coincide with source selections while resolving to different sources in the quote table, making namespace confusion a plausible explanation. The model's internal reasoning is unknown. OpenAI selected source18 for isotonic units but quoted source17; this is a narrower selection/role mismatch inside the same displayed evidence group. Broadening scope alone would not make those quotes complete scientific proof. OpenAI's overlong C2/C3 pointers are an additional latent failure after the first scope failure, not a new model request or repaired result.

The complete unchanged source bank contains direct alternatives: S18/ev_004 states no net water movement while water still moves in and out; S15/ev_003 explicitly states normal isotonic volume and hyper/hypotonic RBC volume effects; S23/S24/ev_004 state hypertonic water-out and shriveling; S21/ev_004 states hypotonic water-in and lysis. C2/C3's original ev_003 caption directly supplies volume effects, but direction needs an additional mechanistic bridge or the explicit ev_004 passage. Keep the original full-citation positive label provisional in this new diagnosis. Historical labels, scores, raw responses and holds are unchanged.

## Minimal detached citation candidate

Add ev_003 to C1, ev_004 to C2 and ev_004 to C3; leave C4 unchanged. Preserve all old markers and append only the new marker plus separator within each target claim. The global cited-ID set/order stays unchanged because ev_003 and ev_004 already appear elsewhere. Complete actual citation groups increase from4 to7, requiring a fresh assessment of every placement.

New preparation-only code is generation/citation_only_repair_v1.py, with tests/unit/test_citation_only_repair128.py. It accepts explicit finite body-only additions and reviewed support for every changed unit, verifies exact original spans, retrieved complete source IDs and proof under resulting displayed citations, and rejects unsupported/partial/unknown, missing, stale or out-of-scope proposals. Inverse insertion checks prove retention of all original answer bytes; short_answer and other fields remain unchanged. Caller-supplied source review is not local semantic certification. Every receipt sets final_full_check_required=true, rederive_claims_and_bindings_required=true, old_verdict_reusable=false and publication_allowed=false. There is no automatic runtime repair or production integration.

The final prepared S02 candidate uses the existing ordinary_qa_compact_v2 output: concise decisions and pointers, no extra model explanations or verbose schema. All54 full source passages and60 quote pointers retain their exact text, IDs, ordering and spans. The wire is28,201 bytes; an authored plumbing-only verdict is901 bytes /414 cached o200k tokens. These are local size measurements, not provider usage. The output limit remains4096. Original127 outputs are never remapped, shortened, flag-corrected or reused as final judgments.

## OpenAI S01 rejection

S01 needs no citation patch. Its C3 states that an enzyme is not permanently consumed or changed overall, while allowing binding shape changes and temporary covalent bonds. G5 is the actual ev_002 citation. Its allowed source18 (src_c1b9be63e82dc1b2f5a3a6fc) explicitly describes structural change when an enzyme binds its substrate, directly supporting C3's shape-change clause. Source48/ev_006 gives alternate induced-fit support; that does not make ev_002 irrelevant. OpenAI's saved G5=I is an explicit negative assessment, unlike125's missing assessment.

All seven S01 units also retain f='-' despite d='S'. Exact claims, lossless unit substrings and chosen sources are in diagnosis128.json: C1 protein/RNA wording is supported by S6/S22, C2 activation-barrier wording by S7/S33, and C3 net versus temporary distinctions by S30/S48/S49 plus the independently relevant S18. Native ACTUAL_CITATION_IRRELEVANT, SOURCE_CONDITION_CHANGED and SOURCE_RELATION_CHANGED gates therefore remain negative. Do not infer corrected flags from plausibility or convert that output into PASS. The frozen positive fixture counts this valid negative as one false rejection; independent AI source spotreview is not formal human gold. Neither case establishes a model winner.

## Free validation and independent review

312 focused tests passed in9.66s; Ruff passed. Controls verify complete in-scope assessment, unsupported/partial/unknown repair refusal, unretrieved/out-of-result proof, stale spans, duplicate/existing markers, explicit body-only scope, exact retention, actual rederived citation groups, outside-scope unscored results and the600-character claim quote-role bound. Complete actual-S02 authored controls separately show: repaired-citation positive plumbing PASS; outside-scope proof remains unscored; deliberately wrong hypertonic water-in/expansion receives a technically valid negative judgment against source23/24. These authored controls validate plumbing and preservation, not live model quality.

Independent source review: phase95_binding_review. Final code/artifact review receipts record actual reviewer outcomes alongside this report's evidence; no reviewer test or API execution is implied. Existing126 checker/runner/prompt/default source and127 raw/results remain unchanged.

## Smallest proposed live work

The current step admits zero model calls. The final proposal is next-live-proposal128-final.json, bound to prepared-S02-citation128-final.json; max_future_requests=1 supersedes the inherited two-slot metadata in the preserved preliminary plan.

1. One DeepSeek deepseek-flash checker request for the detached S02 citation candidate; no generation, paid repair or retry. Same question and54 full passages, unchanged prose, new7 actual groups, T0/disabled thinking/4096 output. Proposed CNY0.10 cap; conservative peak-rate input byte/frame reservation gives CNY0.093266. Require fresh complete valid native acceptance; an invalid or negative result remains retained and stops. This tests repaired citations, not an automatic repair of the old pointer choices.
2. One native S01 browser submission in the existing isolated synthetic database127.0.0.1:15433/cs30_week10_pair_b_20261009_01. Proposed DeepSeek live generation plus compact checker, max2 provider calls, generation output1024 and checker4096, no repair/retry, CNY0.25 cap. With input upper limits24,576/50,000, peak protective worst case is CNY0.190112. Capture browser monotonic Send-click to complete cited-answer DOM, successful persisted job/answer/history join, reload preservation and reopened sources. Retain timeout/failure as censored; n=1, no p95 or causal speedup claim. Existing journey79 is a reference, not an already executed successor.

The browser proposal is not dispatch-ready. Read-only current source/service/owner/idle-isolation and configured model/budget checks remain necessary. In particular, backend/app/modules/answering/service.py currently constructs GenerationRequest without qualification_source_transport, so a normal native request keeps its existing transport default. Before dispatch, prepare and free-test a narrowly question/session-bound isolated compact override and freeze that actual path. Do not label a legacy checker run as compact, replay a frozen answer as live generation, change production activation, or access the real database. No service, private binder, credential or database was accessed in128.

## Evidence and preservation

Evidence directory: C:/Users/PC/Documents/Codex/2026-10-04/task-2/5703-citation128-offline. Final source-evidence128-final.json SHA256 c0ff37ab6cbd830cb7723bb39d54946f56e45f5418c4ebee7a11e2146e1327e6 binds54 source/artifact/log pins. diagnosis128.json carries every exact original selected span and source ID; citation-only-candidate128.json carries reviewed per-unit source declarations and retention receipt; final prepared/proposal, native controls and local-readback receipts are separate from old model results. Preliminary files remain preserved with explicit successors.

Only two new preparation/test files, this report and byte-preserving progress/handover appends are added to Main. No paid/free external model request, credential use, DB operation, install, broad archive, remote upload/deployment/submission or default change occurred. Protected staging, experimental inputs/results and old financial holds remain untouched. Live compact recheck, unified-condition RAG quality, full-browser answer timing and whole-project completion remain open.
