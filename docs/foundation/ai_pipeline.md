# AI pipeline and generation contracts

Status: foundation specification based on the supplied v5 assignment and inspected source. Implementation and live research remain separately evidenced. Accountable owners: Sijin Lu (generation), Chengzhou Liu (retrieval), Pengyuan Xia (personalisation), Hongle Yang (corpus), Zeping Liao (runtime), Chong Zhang (evaluation). The current implementation executor is Codex; no human review has been invented.

## Scope and shared execution

One answer service supports `interactive_chat`, `benchmark_openqa`, and `benchmark_mcq`. Chat and OpenQA use `ChatResponseV1`; MCQ alone uses the historical eight-field `MCQResponseV1`. In formal evaluation, E0 is no retrieval and E1 is the frozen basic dense RAG control. R1 BM25, R2 RRF and R3 reranking are separately named retrieval variants. Interactive requests retain their existing retrieval-enabled condition field while separately freezing an explicit `retrieval_policy` and hash; the configured current chat policy uses R2 candidates and fixed local MiniLM reranking. That policy never changes frozen E1 experiments or older requests. Profile studies are a separate research service, not a fourth answer mode or a mandatory second product call.

The shared flow is validated saved input → frozen conversation/profile/configuration references → query preparation or benchmark bypass → retrieval or E0 bypass → selected evidence and whole-window accounting → versioned role-separated prompt → provider call → strict parsing and semantic validation → atomic backend publication. A valid provider response is not yet a valid answer, and a valid answer schema does not prove factual correctness.

The five concrete ports are ParserPort, EmbeddingPort, RetrieverPort, LLMPort and ProfileCompiler. The backend owns jobs, attempts, persistent budgets, authorisation and publication transactions. The adapter owns one transport call. Generation owns prompts, response validation and bounded retry decisions. Evaluation owns labels and scoring; gold, support, coverage and `evidence_status` never enter the answer command or provider messages.

## Runtime contract

`GenerationService.generate(request: GenerationRequest, budget: RequestBudget, on_attempt) -> GenerationOutcome` is the target service boundary. Shared public DTOs are canonical in `contracts/models.py` and exported JSON Schema/OpenAPI; generation does not maintain divergent public copies. The request contains mode, condition, schema identity, trusted model configuration, request identity, role-separated messages, selected evidence snapshots and request context. A structured result contains a validated typed response or an explicit failure, raw output with controlled access, provider/model identity, usage, finish reason, provider request ID, attempts, timing and model mode.

The LLM adapter receives real messages in the order system instructions, selected prior user/assistant turns, current user message. Summary/profile/evidence are explicitly delimited within trusted scaffolding, with their contents treated as data. An earlier assistant answer or summary is not a knowledge source. Strip old request-local citation markers from history; only this request's evidence block defines citable IDs. The final current user input remains visible as the current user message. Test hooks must never appear in live prompts.

`on_attempt` permits backend persistence immediately before and after each external call. Starting an attempt consumes its call allowance before transport. The backend persists active elapsed time, attempt stage, execution token, usage, outcome and uncertainty. The service receives those existing totals on retry; it never initializes a fresh budget for an already attempted request. Synchronous calls execute in the single worker; the browser polls durable jobs.

The integration-facing dataclass request fields are `request_id`, `mode`, `condition`, `question`, optional `question_id`/`options`, selected `evidence`, owned `history`, optional `summary`, compiled `profile`, optional `prepared_query`, and trusted `config`. History entries use role/content plus persisted identity where available; evidence entries use the canonical EvidenceSnapshot shape. `GenerationOutcome` exposes JSON-compatible response/error/messages/evidence/usage/timing/provider/model/model_mode/budget fields. `RequestBudget.from_dict()` and `to_dict()` allow backend retry persistence without provider-specific objects. An attempt callback receives an event dictionary with start/finish phase, attempt index/stage and current budget. This interface accepts no gold/support/evidence-status argument.

The pure helpers `compile_profile(profile, use_profile=True, turn_message="")`, `prepare_query(message, history)`, `select_context(session_id, messages, cutoff_sequence, profile_snapshot_id=None)`, and extractive `summarize(...)` supply deterministic JSON-compatible snapshots or the canonical PreparedQuery/ConversationSnapshot model. Canonical contracts retain ownership of public field definitions; helpers do not write database state.

## Evidence and retrieval

Evidence is selected only after release filtering and context budgeting. Each `EvidenceSnapshot` has a request-local `ev_001` style ID; request, chunk, document asset and processing IDs; source title, section and physical-page locators; exact submitted text and SHA-256; ordering; and optional `inherited_from` containing the original request/evidence pair. Store the exact text submitted, not a later document lookup. Every citation must resolve to one of these selected snapshots.

Initial dense retrieval is normalized `intfloat/e5-small-v2`, 384 dimensions, explicit query/passage prefixes and exact cosine over the active release. Chunk target is 320 tokens, body cap 448, same-section overlap 48; prefix and special tokens count toward the actual embedding window. R0 top-k is 5, with 3/5/10 as separate experiment settings. No correct answer may expand a retrieval query.

R1 BM25 uses the same released chunk set, versioned normalization, k1=1.5 and b=0.75. R2 takes up to 50 candidates from each retriever and sums `1/(60 + one_based_rank)` by chunk ID, never raw scores. R3 reranks the top 20 fused candidates with a configured cross-encoder and records model revision, spans, truncation and separate latency; unavailable models produce an explicit unsupported result, never a result silently relabelled R3. Changed embedding/chunk parameters require a compatible release and matching qrels.

For extended factual questions, retrieve against the pinned release with the standalone query. Re-explanation can reuse underlying source snapshots only after checking current availability, placing their text into the new prompt and assigning new local IDs. Current deactivation/revocation overrides an old pin for new model input. Historical citation resolution returns its original authorised snapshot or 410; it never substitutes a newer passage. Source text, including instructions embedded in it, remains untrusted evidence.

## Whole-window and execution budgets

| Component | Initial ceiling or rule |
| --- | --- |
| Current learner message | Nonblank string, 1–4,000 characters; reject rather than silently shorten |
| Recent conversation | Most recent six completed exchanges, at most 2,000 generator tokens |
| Extractive older summary | At most 512 generator tokens, with attributable source message IDs |
| Selected evidence | At most 3,000 generator tokens; drop complete trailing chunks |
| Output reservation | 1,024 tokens for chat/OpenQA; 768 for MCQ |
| Provider call | At most 60 seconds, bounded by remaining request execution time |
| Logical answer request | Four total provider calls and 180 seconds active execution, including preparation, generation, retries and repair |
| Optional model preparation | At most one call, charged to the same request budget |
| Transient retries | At most two, and only while the shared call/time budget permits |
| Format repair | At most one, also within the shared budget |

These ceilings are not additive guaranteed capacity. Count system instructions, current message, selected history, summary, profile, evidence, schema overhead, role overhead and output reservation against the configured generator window. Use the configured tokenizer; when unavailable use an explicitly labelled conservative UTF-8 byte upper bound plus message/schema overhead, never a silent character/4 estimate presented as exact. The actual configured provider window must be recorded and verified before claiming live support.

Prioritize current content, necessary recent referents, response/schema instructions and output space. Reduce irrelevant old history/summary, then excess whole evidence chunks. Record actual counts, estimator/version, window, reserved output and exclusions. If the necessary current message cannot fit, fail explicitly. If no sufficient usable evidence remains, produce a grounded limitation rather than an unsupported factual answer. Embedding has its own model-window check, including query/passsage prefixes; any query compression is explicit and traced.

Queue waiting is excluded from active execution. Local preparation/retrieval/validation and worker backoff count as active time. A request exhausted before a call fails with `BUDGET_EXHAUSTED`; manual retry retains consumed totals. A new budget requires an explicit new user action. On restart, an external call with uncertain completion is marked uncertain and is not automatically replayed. Offline teaching-study items have separate explicit budgets; they cannot borrow a chat request's allowance.

## Strict response rules

All JSON must be exactly one object. Reject duplicate keys at any nesting level, Markdown fences, trailing objects/garbage, NaN/Infinity, booleans used as numbers, missing required fields, extra fields and wrong/null types. Do not extract a convenient JSON substring or an A–D character from prose. Run both JSON Schema/Pydantic structure checks and context-dependent semantics. Stable error codes distinguish invalid JSON, schema mismatch, citation mismatch, option mismatch, unsupported response type and refusal-invariant violation.

`ChatResponseV1` has exactly eight required fields: `schema_version="chat_response_v1"`, `response_type`, `answer_text`, `short_answer`, `citations`, `refusal_reason`, `follow_up_questions`, `confidence`. `response_type` is answer, clarification, refusal or social. `answer_text` is nonblank prose; `short_answer` is a compact direct answer or null. Follow-up questions are zero to three nonblank strings. Confidence is null by default or a finite number in [0,1], never a fabricated gauge.

For factual RAG answers, at least one current selected evidence citation is mandatory. The set of `[ev_NNN]` markers in answer text and the unique citations array must agree; unknown IDs fail. E0 is an explicitly evidence-free evaluation policy with empty citations. Social and clarification have null short_answer and refusal_reason; they may have no citations and must not become factual fallback channels. Refusal requires useful nonblank text, null short_answer and confidence, empty citations and follow-up questions, and exactly one of NO_EVIDENCE, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE or OUT_OF_SCOPE. Other types require null refusal_reason.

`MCQResponseV1` retains exactly `question_id`, `answer`, `answer_text`, `citations`, `confidence`, `refused`, `refusal_reason`, `short_explanation`. It is discriminated by the envelope/schema identity, without inserting a ninth historical field. MCQ input requires exactly A/B/C/D, nonblank strings, and distinct options after Unicode NFKC normalization, whitespace collapsing and case-folding. Preserve original option text and order for the actual prompt; valid output answer_text must equal the selected original option byte-for-byte, including meaningful whitespace. E0 normal output chooses an option and has no citations; E1 normal output cites selected evidence. Refusal has null answer/answer_text/confidence and empty citations. Legacy refusal-reason enums remain confined to MCQ compatibility; they do not expand chat enums.

A clear factual request with no selected evidence can receive a locally constructed NO_EVIDENCE response with a recorded programmatic origin. A greeting receives social; a missing referent receives clarification. Nonempty retrieval never sets a trusted “sufficient” label: the model must judge support from actual text, and reviewers independently assess entailment. A provider refusal/error, invalid output, timeout or persistence failure is an application failure, not a manufactured domain refusal.

## Provider and retry semantics

Provide explicit mock, OpenAI-compatible/Azure/Ollama Chat Completions, native Anthropic Messages and native Gemini generateContent adapters through `generation/providers.py`. Use role-separated messages and explicit endpoint capability settings. Workspace model settings save/test/activate immutable revisions with separately encrypted credentials; requests retain their selected revision. The exact supported configuration fields, local tokenizer options and protocol references are in [model administration](../model-administration.md). Missing endpoint/model/key configuration returns unavailable; a live failure never falls back to mock.

Normalize `provider`, configured and returned model identifiers, raw text, input/output/total/reasoning tokens, latency, finish reason, provider request ID, HTTP status, Retry-After, retryable and error code. Unknown fields remain null. Cost is null without a frozen price record; unknown usage is not zero. Token sums retain completeness information if any attempt usage is unknown. Do not expose authorization headers, keys or arbitrary provider response bodies to the UI/logs; errors use bounded sanitized diagnostics and trace IDs.

Empty choices, missing message/content, non-string or blank content and malformed provider envelopes are handled explicitly. Any `finish_reason=length`, including nonempty text that happens to parse, is `OUTPUT_TRUNCATED` and cannot publish. No format repair repeats a truncation with an unchanged output budget. 429 and eligible transient 5xx are retryable with bounded Retry-After/backoff; 401/403 and configuration errors are permanent. Timeouts retain uncertainty and consumed allowance. Only GenerationService owns retry/repair decisions; adapter and worker do not each add retries.

Format repair receives the same frozen mode/evidence/profile/history, a stable validation error and a bounded sanitized prior-output excerpt. It asks for format correction, not new facts or hidden reasoning. It cannot escape the model window or reset counters. After one unsuccessful repair, preserve an explicit terminal failure; do not publish partial output.

## Deterministic profile compilation

Keep existing API compatibility: `level` is beginner/intermediate/advanced; `style` is concise/detailed/socratic; `language` is `en` in the first tested contract; `topics` is a list of at most 20 nonblank strings, each at most 200 characters, treated as self-reported learning interests/goals. `version` is a positive integer optimistic-lock revision, distinct from the compiler/policy version string `profile_rules_v1`. Unknown explicit enum values or overlong data fail with 422; stale writes fail with 409. The compiler never infers mastery or personal traits from activity.

Existing valid legacy values are preserved. Missing internal legacy records fall back to intermediate/concise/en/empty topics with `fallback_reason=missing_legacy_profile`; explicit invalid user input never falls back. The saved default is intermediate. A reset creates a new numeric revision. A profile snapshot freezes source revision, normalized fields, compiler version, policy text/hash and fallback reason. Hash canonical sorted UTF-8 JSON plus compiler version and exact emitted English rules to make equivalent inputs deterministic.

The inspected eight-page Pengyuan Xia Week 5 PDF describes `profile_id`, `learner_level`, `profile_version="1.0"`, `known_prerequisites` and language, nine deterministic rules, seven passing checks and human-authored chemistry exemplars. No corresponding executable compiler was present in the archive. Page 2's validation figure is a report of those checks, not a fresh test log. Map API `level` to internal learner_level; derive profile identity from its immutable snapshot; map integer API version to source record revision, never to string compiler version. Do not claim topics are known prerequisites. The initial API accepts topics as self-reports and does not infer prerequisites; a future explicit prerequisite field requires its own schema revision. The v5 specification supersedes the report's invalid-explicit-input fallback and fixed step/learning-check counts, while preserving its useful presentation and evaluation intent.

Beginner defines essential terms and prerequisites, with short steps, labelled analogies or comprehension checks only when useful. Intermediate connects concepts and applications with moderate evidence-supported detail. Advanced uses precise terms, assumptions, limitations and compact supported derivations. Concise prioritizes direct wording; detailed allows a fuller supported explanation; socratic permits a relevant guiding question without withholding the answer by default. Self-reports guide topic relevance only and are quoted as data, never executable system policy. Evidence/correctness overrides style preferences.

Per-turn requests such as “more simply” or “more detail” compile a separately recorded temporary presentation override without changing the saved profile. `use_profile=false` produces no profile policy but retains the same conversation history and mode. Historical answers show their applied snapshots, not today's profile. No mandatory follow-up, step count, analogy or second generation stage is imposed on greetings or short answers.

## Independent C0/C1/C2 study

TeachingStudyService consumes frozen question, base free-form answer, allowed evidence snapshot IDs, target level, condition, model/prompt configuration and rule version. C0 omits level policy; C1 adds only one-line target level; C2 uses the deterministic structured compiler. Full matrix is three levels × three conditions per selected question. Each item has independent pending/running/succeeded/failed/cancelled state, output and usage. It neither creates learner messages nor mutates base answers or substitutes gold for an incorrect base answer.

TeachingStudyResponseV1 contains schema_version, explanation, citations, learning_check (string or null), and invariant_check with structural result and human-review status. Automated checks verify fields, permitted evidence IDs and frozen versions. Humans separately inspect supported meanings, changed facts, negation, formulas and misleading analogies. Independent blind 0–3 anchored ratings cover level fit, clarity, prerequisite support, usefulness, guidance and consistency, with separate correctness/groundedness gates. Missing ratings stay null. Output ratings are not measured learning gains.

## Inspected source and port plan

The original generation package under development_inputs is immutable. All 30 PACKAGE manifest entries and 21 SOURCE manifest entries matched hashes and lengths before fresh execution. On 2026-09-08, a separate evidence copy ran 39 legacy unit tests and two mock smoke rows successfully under Python 3.13.2 with `-B -S`; requested live calls were zero. Evidence is `evidence/legacy/generation_manifest_audit.json` and `evidence/legacy/generation_verification_copy/results/handoff/verification.json`. This proves the historical scaffold is reproducible in that interpreter, not Python 3.12 deployment support, chat readiness or research accuracy.

| Source asset | Target / action |
| --- | --- |
| src/generation/llm_adapter.py | generation/adapters: retain transport/config concepts, add real messages, robust envelope checks, metadata and explicit capability configuration |
| src/generation/prompt_builder.py | generation/prompt_builder.py and versioned prompts: retain versioned loading, rebuild three-mode context; remove OPTION_A and oracle status |
| src/generation/response_parser.py | generation/parser.py + canonical contracts: retain useful semantic intent, replace fence/duplicate-key permissiveness and whitespace option comparison |
| schemas/generation_response_v1.json | Preserve historical schema in evidence; canonical MCQ alias and new chat schema in contracts |
| prompts/pure_llm_v1.txt and basic_rag_v1.txt | Preserve historical files; new chat/OpenQA/MCQ/preparation/study prompt versions contain no test hooks |
| scripts/run_generation_smoke_test.py | Preserve as historical smoke; port reusable one-repair flow into service, use a separate formal evaluator runner |
| scripts/run_llm_adapter_probe.py | New explicit-output probe tool, separate from scientific runs; never overwrite week5 records |
| config/*.example.json | Preserve as historical examples; new trusted config validates current endpoint/model/window/capabilities without claiming examples are verified |
| tests/test_generation.py and 20-item fixture | Preserve baseline and failure diagnostics; write new contract/negative/integration tests; obsolete two-choice/oracle assumptions do not constrain chat |

The historical adapter sends one user string, mock always selects A, builder accepts 2–4 options, parser strips fences/accepts duplicate keys, refusal confidence is not enforced, and nonempty length completion can appear successful. Repair lives only in CLI `run_case`. These defects are required migration work, not evidence that no reusable source exists. The old 2026-09-05 two-field live probe, two mock rows and forty failed diagnostics remain historical; no current configured provider or formal score is inferred.

Verification must cover HC-01–12, strict cross-mode fixtures, actual role order/evidence hashes, profile-off with history, invalid-then-valid versus repeated-invalid outputs through the application service, persistent budget exhaustion, redacted HTTP failures, a relocated execution directory and shared chat/evaluator entry. Live semantic conversation and blinded study evidence are separately pending until authorized configuration/data/ratings are actually available.

## Current implementation evidence, 2026-09-08

The specified generation, conversation and compiler ports are implemented in `generation/`, `conversation/` and `personalisation/`; actual source processing/retrieval is in `pipelines/`, `retrieval/` and `backend/app/modules/knowledge/service.py`. Focused verification is recorded in `evidence/ai/verification.json`; task-by-task limits and remaining evidence are in `docs/execution/audit-ai.md`. These records distinguish local software results from deferred live/human studies.

Release construction now validates recorded source quality hashes, exact chunk spans, compatible embedding signatures and float32-canonical embedding hashes. Cache entries come only from intact prior manifests; rejected cache releases are counted and inputs re-encoded. PostgreSQL retrieval executes the pgvector cosine-distance operator in SQL. Processing/release workers check the durable execution token at short stage/batch transactions and atomically publish final artifact plus Job success. Slow parser, tokenizer or embedding work holds no Job row lock; Stop and recovery invalidate late results. Independent teaching jobs dispatch to the separate study bridge and retain their own charged budgets during recovery.

Source quality and processing-difference exports, current field definitions, a portable authored fixture and rebuilding/recovery instructions are in `docs/data_rebuild.md`. A cancelled/stale run is distinct from a quarantined quality decision and from a validated release. Subsequent authorized official acquisition recovered the exact Concepts pilot bytes and real E5 runs on CUDA; `docs/execution/corpus-acquisition.md` and `docs/real_embeddings.md` link that evidence. Native PDF text still omits visual content, and no live-generator scientific result follows from the acquisition or embedding smoke.
