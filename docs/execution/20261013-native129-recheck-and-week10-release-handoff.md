# Task129 closure and Week10 release handoff — 13 October 2026

## Actual S02 checker-only recheck

One official DeepSeek request completed, with HTTP 200 and finish_reason=stop. All seven citation groups were assessed, but the qualification contract rejected SOURCE_REFERENCE_OUTSIDE_ACTUAL_CITATIONS. The outcome is TECHNICAL_STOP; technical_valid=false and semantic_accept, correctness and false_reject remain null. No answer was published and no retry was made.

The response used 8,023 prompt tokens (1,664 cached) and 439 completion tokens, 8,462 total. API elapsed time was 2,223.083 ms. The saved protective tariff upper is CNY0.019558, UNKNOWN hold zero; this is not an invoice or an end-to-end browser time. The response model was deepseek-flash. Raw response SHA256: 8a053e36066b02c3c410016a6d1045874533bf2a3767cfe1d70f50716f6bdcbd. Original receipts are preserved in the task workspace's 5703-citation129-real directory. Earlier results and fee protections remain unchanged.

## Native transport implementation and free verification

The current source adds a session/question-bound ordinary_qa_compact_v2 transport opt-in. Normal API submission freezes the transport and binding into the queued command; the worker consumes that command independently of subsequent Settings changes. A binding without a transport raises CONFLICT. Legacy defaults apply only when both fields are absent.

Source-to-target files: backend/app/core/config.py; backend/app/modules/answering/service.py; new backend/app/modules/answering/qualification_transport.py; new tests/unit/test_native_compact_transport129.py. Defaults remain unset; this opt-in is not enabled by packaging. A normal authenticated API/isolated SQLite/queued-command/worker/GenerationRequest free control reaches the engine guard and deliberately stops at FREE_CONTROL_STOP. It is not a model call or successful delivered answer. The affected suite passed 202 tests in 9.67 seconds; Ruff passed. Independently reviewed source evidence SHA256: f7684342815f0b32fafc81740102f7ca03948101458d13ad1d33c120e140f9a5, at 5703-native129-free/source-evidence129-native-reviewed.json in the task workspace.

## S01 browser experiment not run

The S01 browser experiment has no live session, submission or dispatched model request. Its workspace-only controller prototypes are not released product code. Remaining readiness issues include rebinding the API dependency's original Settings object and final review of usage settlement, close-failure handling, censored failure timing and origin restrictions. Seven isolated guard controls and fifteen mocked terminal-observer controls passed; they made no real HTTP, provider or database requests and do not establish browser acceptance. The saved browser plan predates subsequent prototype edits and must not authorize execution.

## Week10 delivery boundary

Today's release takes priority over additional experiments. The deadline is 13 October 2026 17:00 Sydney AEDT / 06:00 UTC. Staging is E:/5703/Week10-delivery-20261013. The comparison baseline is final_source04_with_reports_matched5_and_token_cache_20261009_01, not the earlier annexes cutoff. Its complete archive includes public model/corpus resources and two tokenizer caches; preserve those runtime resources while updating source. It is approximately 1.87 GB compressed. E: had 17,500,807,168 free bytes at the read-only preflight.

Deliver one complete project ZIP plus eight owner ZIPs, eight matching English Week10 DOCX reports and an overall summary where practical. Owner reports use module responsibility, not invented executor attribution. Each owner package includes complete current files in its responsibility partition; it depends on the complete project's shared runtime resources. Compare against the final baseline and clearly identify unchanged modules. Include manifests, SHA256, CRC/integrity checks, secret exclusions, startup/install instructions and honest current verification limits. Do not package credentials, live databases, dependency environments or experimental controller prototypes. Preserve all prior deliveries and protected data. New work after the frozen Week10 snapshot belongs to Week11.

Unified RAG quality, native full-answer browser timing, formal warm p95, independent human ratings and complete coursework acceptance remain open. No global project completion is claimed. No paid request is in flight at this checkpoint.
