# Provider compatibility implementation — 21 September 2026

The Models administration flow now separates saving an immutable configuration, testing its transport and contracts, and activating exact answer/checker versions. The software has local scripted, loopback and disposable PostgreSQL verification. The saved OpenAI configuration has **not** completed the new live diagnostic suite; no new OpenAI call or activation is claimed here.

## Storage and API

Migration `e0a64c7d123b`, following memory migration `d9e53f6b012a`, adds `model_compatibility_runs` and `model_compatibility_stages`. It adds a nullable checker configuration to `active_model_configurations` and exact answer/checker probe references to `model_activations`. Existing encrypted credential references and immutable `model_configurations` remain in use. The coordinator applied these additive migrations: [preservation-result.json](../../evidence/week08-memory-v2/20260921/migration/preservation-result.json) verifies unchanged original columns and counts in all 44 pre-existing tables. This is preservation evidence, not a new model activation.

All routes below use the existing authenticated, workspace-scoped administrator boundary under `/api/v1/admin/model-configurations`.

| Route | Behavior |
| --- | --- |
| `GET /` and existing save/successor routes | Return masked credential presence and immutable public versions; saving makes no provider call. |
| `POST /capability-profile` | Suggest a declared protocol profile without saving or claiming observed compatibility. |
| `POST /{id}/test` | Accept `tier=basic/structured/project/all`, `role=answer/checker`, and an operator-reported `network_label`. `Idempotency-Key` binds the exact body and version. |
| `GET /{id}/tests` | Return retained modern suites and explicitly labelled `legacy_connection_v1` receipts. |
| `POST /{id}/activate` | Require answer `test_id`, checker `checker_test_id`, optional separate `checker_configuration_id`, and `expected_active_version`. |
| `POST /use-environment` | Restore the compatible environment path using the existing compare-and-swap version. |

Suites persist `running` and each `started` stage before transport. Terminal states are `passed`, `failed` or `uncertain`; blocked later stages are `not_run`. Same-key replay returns the durable receipt. A conflicting body or concurrent suite is rejected. A stale started suite is exposed as uncertain and is never automatically replayed. Completed receipts are immutable.

Activation requires the latest project pass for **both roles**. The stored configuration, capability declaration, current project schema/prompt, effective parameters and output reservation must match. A basic success, a legacy receipt or an obsolete checker schema cannot satisfy this guard. Pointer updates retain compare-and-swap semantics. Newly submitted requests freeze both configurations; execution resolves each frozen credential reference without rereading the active pointer. The checker output reservation is at least 4,096 tokens and still must fit the declared context window.

## Capabilities and bounded probes

`provider_capabilities_v1` records API style, output-token parameter, supported structured modes, optional temperature/seed/reasoning/thinking flags, small-probe output reservation and output ceiling. Defaults are conservative runtime declarations; an operator may explicitly revise them. They are not universal vendor compatibility guarantees. Existing configurations with both capability fields absent retain the legacy wire behavior. New saves attach the versioned profile. Unsupported configured options fail before transport where the declaration permits that decision.

Implemented transports retain OpenAI-compatible/local/Ollama, Azure OpenAI, Anthropic and Gemini support, and add explicit OpenAI Responses request/response handling. New strict OpenAI schemas make every property required, retaining nullable alternatives. Model names are editable and are never silently substituted. Live failures never switch to mock.

`provider_probe_v2` uses public authored fixtures and one transport call per stage:

1. **Basic:** a minimal `OK` response, omitting optional controls and response schemas.
2. **Structured:** a small strict JSON object, with configured optional controls restored.
3. **Project:** the actual `ChatResponseV1` citation contract for answering, or current `ReliableCheck` / `joint_check_v2` for checking. The checker fixture exercises distinct textbook, exact problem-given and validated calculation bases.

An API suite is bounded to three calls and 180 active seconds, with no automatic retries. A wall deadline also bounds peers that keep sending bytes beyond an ordinary socket timeout; uncertain completion stops progression and retains the reservation. Small probes use the explicit capability floor rather than a large saved answer budget. Mock probes are labelled authored local checks and do not establish real provider or semantic compatibility.

Diagnostics retain allowlisted HTTP status, provider type/code/parameter/request ID, finish reason, network category, measured latency and numeric usage. Provider error messages are replaced with program-authored messages so partial prompt or memory echoes cannot enter diagnostics. Raw response bodies, prompts and secrets are not stored in compatibility receipts. Measured cache-hit/miss and reasoning counters are preserved where supplied; missing usage/cost remains unknown. The Failures UI also renders only typed fields and distinguishes memory-context availability from provider failure.

## Saved OpenAI diagnosis and pending live work

[saved-openai-before.json](../../evidence/week08-memory-v2/20260921/providers/saved-openai-before.json) records the existing `gpt-5.6-luna` configuration at `https://api.openai.com/v1`, 1,024 output tokens, `max_tokens`, temperature 0 and a generic historical HTTP failure. Its credential was available through the existing encrypted reference. The retained old receipt has insufficient detail to prove the failure's cause.

Official [model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [Chat Completions reference](https://developers.openai.com/api/reference/cli/resources/chat/subresources/completions/methods/create) and [structured-output guide](https://developers.openai.com/api/docs/guides/structured-outputs) were inspected. The prepared candidate keeps the exact saved model and endpoint, uses `max_completion_tokens`, omits temperature, selects low reasoning and explicitly reserves 2,048 generation / 4,096 project-checker output tokens. These are a testable candidate, not a proven fix.

The retained, unexecuted [v5 diagnostic plan](../../evidence/week08-memory-v2/20260921/providers/openai-diagnostic-plan-v5/plan.json) preserves the earlier v1–v4 prepared plans. It includes the required `formula_basis` field in the checker schema and authored proof. Its recorded limit is seven calls: one unchanged legacy reproduction and six answer/checker stages, with 4,353 estimated reserved input tokens, 14,464 reserved output tokens, 60 seconds per call and 420 seconds total. The subsequent DeepSeek probe grammar correction changed the probe prompt and executable hashes, so v5 is now a historical prepared plan and its source guard prevents execution. Any later authorized OpenAI diagnosis requires a fresh plan bound to current code and recalculated reservations. Plans make no database configuration changes and never activate anything. `python -m scripts.verify.provider_diagnostics` prepares only; `--execute` is the explicit execution switch. Any existing attempt file prevents replay.

Automatic approval review rejected the earlier proposed paid reproduction **before execution** because explicit authorization for this OpenAI call was unresolved. The coordinator has asked the user; execution remains pending. No rejected or merely prepared plan is counted as a provider call or successful compatibility result.

## Actual DeepSeek protocol checks

The coordinator executed the saved managed DeepSeek configuration against both three-stage suites. The [answer suite](../../evidence/week08-memory-v2/20260921/providers/deepseek-staged-live-01/answer.json) passed all three stages. The retained [checker suite](../../evidence/week08-memory-v2/20260921/providers/deepseek-staged-live-01/checker.json) passed basic and structured stages but failed project validation despite HTTP 200. One separately authorized authored diagnostic reproduced an arithmetic-expression contract mismatch: the model supplied human notation with units and an equality rather than the validator's named-input arithmetic expression.

The probe prompt now states the production expression grammar. Strict calculation validation is unchanged; schema and validation failures expose only finite program-authored codes and schema-owned field locations. A subsequent [single project-checker retest](../../evidence/week08-memory-v2/20260921/providers/deepseek-checker-project-live-02.json) passed. All prior failures and consumed usage remain retained. These are exact configuration/protocol checks, not evidence of general scientific correctness or a live OpenAI result. Activation remains a separate operation.

The new offline [cost collector](../../evaluation/memory_v2/costs.py) deduplicates outcome/journal receipts, retains uncertain reservations and distinguishes explicit non-submission from unknown completion. The [current development accounting](../../evidence/week08-memory-v2/20260921/accounting/development-http-probes-final.json) combines three development pilots, eight provider diagnostic calls and five calls from two authored HTTP requests: 68 submitted attempts, 615,518 measured input tokens and 41,438 output tokens. The estimated CNY 0.53866904 uses measured cache splits and the [official Chinese DeepSeek tariff](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/), rechecked on 21 September. It is a retained-attempt subtotal, not an invoice or the cost of the later formal study. Twenty-five parser/privacy/uncertainty tests passed in [unit-freeze.xml](../../evidence/week08-memory-v2/20260921/accounting/unit-freeze.xml).

## Actual verification

Evidence is under `evidence/week08-memory-v2/20260921/providers/`:

| Evidence | Actual scope |
| --- | --- |
| `unit-final.xml` / `.log` | 57 focused model-settings, protocol, capability, diagnostic and bounded-probe tests passed. Includes partial error-message echo suppression and DeepSeek error-response cache-miss counters. |
| `pg-attempt2.xml` / `.log` | Four disposable PostgreSQL tests passed: immutable successor race, pointer CAS, effective capability mode and durable started-stage/idempotency behavior. |
| `chat-freeze-final3.xml` / `.log` | Three disposable PostgreSQL chat tests passed. Scripted transports exercise all six actual probe stages before activation; queued answer and checker keep the original version after pointer changes and never inherit the environment secret. Current checker schema and cited short-answer fixture are used. |
| `evaluator-fixture-final.xml` / `.log` | Four disposable PostgreSQL evaluation tests passed after the authored activation fixtures adopted the exact staged answer/checker contract. Frozen evaluator credentials and model revisions remain independent of later active-pointer rotation. |
| `frontend-final.xml` / `.log` | 18 Models and Failures component checks passed. |
| `frontend-build-final.log` | TypeScript and production frontend build passed. |

Earlier failures remain retained, including a test-runner database URL construction mistake and an obsolete uncited short-answer fixture. They were repaired in the verification setup; production activation/support guards were not weakened. These focused checks establish software behavior. They do not establish vendor-wide compatibility, live OpenAI success, scientific accuracy or human educational benefit. Aggregate release gates are recorded separately by the coordinator.
