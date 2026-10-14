# Conversation design

This document specifies required chat behavior for CHAT-01–12 and the conversation portions of GEN/PER/BE/FE. Canonical JSON types live in `contracts/models.py` and exported schemas; generation rules and resource ceilings live in [ai_pipeline.md](ai_pipeline.md). This foundation is an implementation contract, not a claim that live model behavior has already passed review.

## Product path and ownership

The learner starts on `/chat`, creates/selects an owned conversation and sends a natural-language message. No four-choice form, SciQ record, answer label or benchmark setup is needed. Each accepted message persists before queued work begins; the browser polls real job status and renders only a final validated response. The same session supports explanation, comparison, examples, simplification, correction, clarification and topic changes. Saved profile preferences can cross sessions; dialogue and summaries do not.

`ChatMessageCreate` contains only content (nonblank, 1–4,000 characters) and use_profile (boolean, default true); Idempotency-Key is a header. Ownership, model, corpus, history and summary are server-selected. Responses are prose with citation links, optional useful follow-up suggestions, applied profile snapshot and visible mock/live status. A mock result is labelled as a demonstration and never presented as measured semantic quality.

## Immutable context selection

Submission validates ownership/session state, enforces one active generation per session, saves the user turn and fixes a sequence cutoff. A transaction also stores a conversation snapshot, profile/configuration/release references, logical answer request and durable job. Concurrent submission returns SESSION_BUSY (409) and the client preserves its draft. A database transaction is never held open during a provider call.

Select completed earlier exchanges from the same session at or before the cutoff. Include the answer revision active at that cutoff, valid social and clarification turns, and accepted user content needed for interpretation. Exclude future turns, another session, partial/error/cancelled assistant outputs and replaced revisions. Failed user turns remain visible to the learner but are not paired with imaginary completed answers. The recent window holds at most six completed exchanges and 2,000 generator tokens. Current message and necessary referents outrank unrelated history.

Each snapshot records session/cutoff, included message IDs, sequence/role/content hash, active answer revision IDs, excluded IDs/reasons, selected text, optional summary ID/hash/coverage, profile snapshot ID and final token-budget report. Retries reuse this immutable context even if current profile or corpus pointers change; evidence use still checks current availability. Do not trust a browser-supplied transcript, include the current user message twice, or include the answer being generated in its own context.

## Attributable summary

The initial summary is deterministic and extractive, with no model call. Summarize only the prefix older than the recent window: copy bounded earlier learner topics/goals, important explicitly referenced concepts and outstanding clarification wording with source message IDs. It is a set of conversational pointers, not an endorsed textbook explanation or inferred proficiency record.

Persist id, session_id, covered_until_sequence, source_message_ids, summary_text, method/version, token_count and SHA-256. Cap it at 512 generator tokens and do not duplicate a turn in both summary and recent history. Never include a source later than the snapshot cutoff. A revision affecting covered turns invalidates/rebuilds the summary; a failed summary rebuild falls back to bounded recent history with a recorded warning. If an omitted old referent cannot be recovered reliably, ask which concept the learner means.

## Standalone retrieval preparation

`PreparedQuery` preserves original_message and contains standalone_query or null, intent, topic_relation, referenced_message_ids, needs_clarification, preparation_version and fallback_reason. Intent is factual, follow_up, reexplain, comparison, source_request, social or clarification. Topic relation is same_topic, new_topic or unclear. These values select behavior, never a trusted external model/corpus/mode supplied by free text.

Obvious standalone questions use their original stem. A dependent question uses selected conversation to name the referent without appending an invented scientific answer. After photosynthesis, “Why does it need light?” becomes “Why does photosynthesis need light?” A clear new topic overrides the previous topic. Comparisons retain both requested subjects; a correction supersedes the corrected conversational assumption while leaving earlier transcript unchanged. Missing or multiple plausible referents produce a concrete clarification question.

Use deterministic rules for obvious cases, with at most one optional model preparation call for remaining bounded cases, charged to the same request budget. Model preparation returns only the typed query structure, not a draft answer. A failure can use an explicitly recorded context-inclusive fallback only if meaning is unambiguous and within the embedding budget. Otherwise choose clarification or a visible error. Frozen benchmark modes bypass preparation, use the unchanged stem and have empty history/summary/profile.

Deterministic fixtures prove wiring and isolation, not general language understanding. Live examples of pronouns, comparisons, corrections and topic changes require actual model execution and separate review.

## Evidence policy across turns

New or extended factual questions retrieve current selected textbook evidence. Rephrase/simplify/summarize requests may reuse the previous answer's underlying passages after current availability checks. Reuse copies the actual source text into the current prompt, creates new request-local evidence IDs and records original request/evidence identity in inherited_from. A prior assistant sentence, its local ev_001 marker, or a summary alone cannot serve as evidence.

Historical markers in model history are removed or qualified so they cannot alias this turn's IDs. Source-request turns resolve the prior answer using its complete request identity. Revoked/unavailable sources are explained honestly; no similar newer passage silently replaces old evidence. Topic switches do not inherit irrelevant old citations. An active release pin is not permission to reuse deactivated material.

Greetings and acknowledgements may be brief social turns with no retrieval. A missing-detail question may be clarification with no citations. Neither type is a bypass for unsupported factual answers. A clear factual question with no useful evidence gets a useful grounded refusal. Nonempty retrieval still requires support assessment; invalid citation/JSON/provider output is an application error.

## Profile and turn override

Apply the frozen explicit profile in the main generation call. Beginner/intermediate/advanced affect presentation, not facts. The legacy API style values concise/detailed/socratic and self-reported topics compile deterministically to English policy. Current-turn presentation requests may temporarily override saved style/level guidance without changing the profile record. Store this temporary override separately so the answer can display what actually applied.

When use_profile=false, remove only profile policy. Keep the same owned history, summary, evidence and chat mode. A new session starts with no dialogue even if it uses the saved profile. Saved edits affect subsequent snapshots; historical answers retain prior applied revisions. Invalid explicit profile data fails; only missing legacy internal records use the recorded intermediate fallback.

## State, retry, stop and regeneration

| Situation | Persistent result and user behavior |
| --- | --- |
| Accepted turn | Queued request/job; one saved user message; composing/progress state |
| Valid answer or social | Request answered, job succeeded, immutable assistant revision and citations published |
| Valid clarification | Request clarification, job succeeded, concrete question appears as an assistant turn |
| Grounded refusal | Request refused, job succeeded, useful source limitation appears |
| Provider/validation/persistence failure | Request error, job failed; visible failure with trace/retry guidance; no partial assistant answer enters history |
| Stop | Durable cancellation and invalid execution token; late provider completion cannot publish |
| Manual retry | New job for the same logical request and immutable snapshot; prior job preserved; aggregate call/time allowance retained |
| Latest-answer regenerate | New logical request and revision for original user turn/pre-answer snapshot; previous answer remains visible until replacement succeeds |

Idempotency uses actor/route/key plus request-body hash: identical repeats return original references; changed bodies conflict. Retry is only valid for the latest accepted user turn without a successful answer. Retry cannot insert a late response before later accepted user turns. Exhausted budgets remain exhausted. Uncertain external calls after a crash are visible and are not blindly replayed.

Regeneration is only for the latest completed active answer with no later user turn and no active session job. It reuses the original pre-answer context, excludes the answer being replaced, rechecks source availability and records parent request/revision. On valid completion, atomically publish citations and switch the active revision. Failure/cancellation leaves the old revision active; if sources now prevent a grounded answer, regeneration fails explicitly instead of replacing the old answer with an unrelated refusal. Feedback remains attached to its original answer_id. Stale/non-tail targets return conflict.

Session archive/deletion blocks new turns and cancels active work by the backend policy. Restore recovers retained history. Pagination is server-backed by sequence; re-login and refresh show persisted messages and jobs. Arbitrary editing/branching of old turns is outside scope.

## Required scenario families and evidence

At least twelve scenario families must be authored under evaluation/conversations and exercised through integration/browser tests. Each records its authored source passages, expected context IDs, prepared query properties, response category, evidence identity and profile effects. Mock expected wording is never substituted for a live semantic score.

1. Standalone factual question followed by a pronoun-dependent question.
2. Explain the same concept more simply, retaining actual source evidence.
3. Request a concrete example, without adding unsupported claims.
4. Compare two concepts across the current and prior turn.
5. Ambiguous “it/that” without a recoverable referent, followed by clarification completion.
6. Learner correction of an earlier assumption and a relevant corrected answer.
7. Clear topic change that does not carry old citations or subject assumptions.
8. Long history beyond six exchanges/2,000 tokens, with attributable nonoverlapping summary.
9. New conversation with empty dialogue and retained explicit profile.
10. Save each level/style, temporarily simplify, then turn profile off while continuing a dependent follow-up.
11. Greeting/source request/no evidence/conflicting or irrelevant evidence with distinct states.
12. Stop, retry, refresh/re-login, and successful/failed/stale latest-answer regeneration with immutable earlier feedback/evidence.

Contract checks additionally spy on exact system/prior-user/prior-assistant/current-user order, verify evidence text hashes against actual prompt content, freeze input across retry, ensure no evaluator fields enter any mode, and enforce foreign-session and future-message exclusion. Browser checks verify actual text copy, suggestions as ordinary messages, citation inspection, keyboard compose behavior, narrow screens and preserved drafts. Running the evaluator is never a prerequisite to these product checks.

Live review and deterministic software verification remain separate evidence classes. Completion requires connected J2/J3/J4/J6 behavior; an attractive chat screen, a passing old 39-test suite, a two-field connectivity probe or a SciQ MCQ score cannot prove these journeys.

## Week 8 structured understanding and evidence reuse

New commands select `conversation_preparer_v9`; historical commands without a version use the preserved v6 path. `conversation.understanding.describe_question` emits `question_understanding_v2`: original/standalone question, intent, topic relation, clause facets, comparison targets, negation, numbers, conditions, correction provenance, clarification reason and source message IDs. It preserves unsupported wording and records its bounded deterministic scope; it does not call an extra model or certify semantic equivalence.

A unique explicit correction replaces the named prior subject while retaining its relationship and conditions. A comparison that would collapse operands, an unmatched replacement or an unresolved action clarifies with zero provider calls. A named subject can resolve one explicit pronoun without dropping why/how; multiple unresolved referents remain clarification. The alias catalogue retains the RAG ambiguity/AI context/biological-word boundaries.

For knowledge expansion, fresh and prior cited chunks enter a frozen bounded union only after pinned-release membership, exact text/processing identity and current source visibility pass. The same current query rescores every admitted passage before relevance screening; prior scores do not bypass it. Reuse-only turns retain available original sources and refuse when those become unavailable. The union has at most20 candidates and five inherited admissions. Whole-passage generation packing deduplicates and prioritizes complementary request facets within the unchanged evidence/window budget. Lexical coverage and citation review flags are operational estimates, not independently verified support. Formal E0/E1 bypasses these interactive policies. [Current evidence](../execution/week08-delivery-20260916.md).

V9 retains explicit sentence-request boundaries such as “. Also” without splitting decimal values. Whole-current-comparison references (“this topic/comparison”) preserve both operands; a bare ambiguous “it” still clarifies. Named-subject predicates can establish a possessive reference within a complete current problem. If old subject extraction yields only an interrogative word, v9 appends the entire prior learner question as context instead of substituting that word. Old v6/v7/v8 commands retain their earlier behavior.

The optional frozen facet fallback runs only after zero whole-query admissions and at least two explicit meaningful facets. It retrieves/reranks at most two subqueries under 20 additional total scoring slots and the same active-time budget; final generation admission is capped at 20 and 3,000 evidence tokens. It preserves the whole learner request and missing parts; candidate relevance is not semantic support. Explicit general-knowledge mode bypasses this textbook path, preserves the frozen mode across retry/regeneration, and marks its uncited output as unverified model knowledge. No automatic mode switch occurs. [V9 verification](../../evidence/week08-delivery/20260916/understanding-v9-implementation.json).

## V10 local problem context and versioned teaching state

`conversation_preparer_v10` retains v9's structured facets and bounded fallback, and recognizes a single explicit declarative problem statement before a later local pronoun. It preserves the entire original message, quantities, units and conditions. Earlier v9 requests retain their original behavior. Multiple possible subjects, a foreign named demonstrative and missing subjects still clarify. This corrects three retained development retrieval failures involving a microscope, population growth and gas compression; the original v9 failure records are not overwritten. Generic sample/train/seed and ambiguity controls guard against a rule tied only to those tasks.

Teaching task identity and explicit help changes are authoritative backend state, separate from profile level and textbook/general answer mode. The pure generation interface receives the current task/version, direct or hint mode, help level, original problem and actual prior delivery/disclosure events. New tasks default to direct complete explanations; explicit hint requests use task-specific comparison, causal-process or calculation policies. Ordinary direct level 0 is distinct from hint levels 1–3. Generation does not infer new permission from accidental prior disclosure.

For `learning_enhancement_v1`, only the final deliverable projection may enter ordinary history and source inspection. Private drafts/checks are not alternate learner answers. Citation claims include exact delivered-text offsets and markers, so repeated evidence markers can resolve to their own claim-linked source fragments. Controlled hints withhold full-source URLs until a separately recorded explicit expansion; actual delivered, rendered and expanded surfaces remain separate observations. The backend owns authorization, erasure fencing, task resolution and projection persistence; [the generation contract](../../generation/enhancement_contract.md) specifies its inputs and outputs.
