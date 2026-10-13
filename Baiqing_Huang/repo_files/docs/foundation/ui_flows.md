# Chat-first user flows

## Login and accounts

Open app → authenticate → `/chat` → load owned sessions, current profile and capabilities. Expired/disabled credentials return explicit errors and offer re-login. Logout/account switch clears account-specific in-memory state and credentials. Re-login retrieves server history and active jobs. Profile and password actions use real validated endpoints; admin navigation is role-aware and the server still enforces privileges.

## Conversation

New chat → empty transcript → optional saved-profile policy → enter free text → submit with a stable idempotency key → server commits user message and queued job → poll actual preparation/retrieval/generation/saving stages → show only the persisted validated assistant revision.

An answer shows complete prose and current-request citations. A clarification asks the missing detail. A grounded refusal explains evidence limits. A social response can omit sources. A failed/cancelled job remains visible as that state and may expose Retry only for the eligible latest user turn. Infrastructure errors never become refusal or success. Sending another message keeps this session and its server-selected context. Suggestions submit ordinary text, not benchmark records.

The composer disables duplicate submission while retaining editable drafts. SESSION_BUSY/validation/connection errors retain the draft. Stop cancels the actual job. Retry creates another job for the original request and snapshots. Latest completed answer regeneration creates a new revision while keeping the prior visible answer until success; failed/cancelled replacements retain the old answer and feedback. The backend remains authoritative if a stale action conflicts.

## History, sources and feedback

Select conversation → forward-paginated saved transcript → actual active revision and current jobs. Rename/archive/restore act on the selected owned session. Archived sessions are read-only until restored. A current citation records its opening against the answer/presentation/evidence and exact claim when available. The drawer displays the approved source projection and selected highlights; Details reveals permitted immutable provenance. Complete source access records a separate explicit request. Historical direct answers retain the original whole-passage endpoint. Revoked/missing evidence is explained, never replaced. Closing a drawer restores focus and reading position.

Copy copies actual displayed response text. Feedback loads existing helpfulness/comment, supports revision/update, preserves edits on failure, and shows saving/saved/error. Feedback stays attached to the answer revision. Administrators can read and review feedback through the connected API/CLI path.

## Profiles

Profile page → inspect current revision → choose Beginner/Intermediate/Advanced and supported style/language/topics → save with version → show saved state. Conflicts require refresh/reconcile rather than silent overwrite. Reset creates a new saved revision. Each next message snapshots the applicable profile; historical answer metadata stays unchanged. Turning profile application off affects the next turn's policy only and retains session history. A temporary simplification request does not rewrite saved preferences.

## Corpus administration

Admin opens corpus → inspect active release and document/version/quality state → upload permitted asset → process/reprocess → inspect blockers or validated result → activate release. Deactivate/restore controls affect future availability; historical evidence stays version-correct or explicitly unavailable. Rollback activates only an intact validated release. Failure retains last usable release and exposes the actual reason. Infrequent repair actions may use a tested documented CLI.

## Experiment administration

Admin opens experiments → inspect protocol/mode/model/readiness → create frozen-input run → freeze → start/cancel/resume through real service → inspect all scheduled outcomes, failures/refusals/cancellations and actual metrics → export server records. Protocols remain distinct: chat_scenarios, SciQ-derived openQA, MCQ and C0/C1/C2 teaching study. Missing ratings/measurements remain absent; mocks prove wiring only. Evaluator absence never disables chat.

## Error mapping

| Response | User behavior |
| --- | --- |
| 401 | Re-login, preserving server history and safe current-account drafts until transition |
| 403/404 | Explain unavailable or forbidden resource; do not leak another account's data |
| 409 | Explain busy/stale/revision/idempotency conflict and refresh authoritative state |
| 410 | Show evidence unavailable, original answer unchanged |
| 413/415/422 | Explain size/type/field errors next to actionable inputs |
| 503/504/network | Visible dependency/connection failure; preserve draft and offer eligible recovery |

All flows work from 320px upward and keep essential controls available by keyboard, pointer and touch. Full responsive rules and subcheck mappings are in `responsive_spec.md`.

## Persistent help and explicit disclosure — 20 September

Ordinary question → Textbook sources + Direct explanation → complete answer. Get a hint is a separate teaching choice. The server resolves the active problem and the saved help level. An ordinary follow-up omits a client-invented task identity so a genuine new question can reset to direct mode. Another hint explicitly references the current task; Show full explanation submits a new durable direct request with the full-explanation action. Start a new problem applies a direct/new-task command to the next message. Failed submission retains that command with the draft; retry and regeneration retain server-frozen choices.

Citation button → record `citation_opened` → approved claim-specific preview → render text/`mark` segments. Show complete source → record `full_source_requested` → receive the original permitted complete passage and source link → record visible full-source rendering with the expansion receipt as parent. Earlier preview fetches and history responses continue to use their approved projection. The UI never infers full-source permission from an earlier expansion elsewhere. Missing presentation on a hint record fails closed.

Approved answer enters the visible transcript → record `rendered` with surface `answer`. Citation and complete-source rendering use distinct surfaces and their actual preceding receipts. Hidden tabs/off-screen content produce no visible-render acknowledgment. A recording failure leaves the approved answer readable and offers an explicit retry using the same event identity. Display acknowledgment describes browser visibility, not learner reading.

## Learning memory management

Learning memory → load saved opt-in state and owned entries → enable only after successful versioned save. Explicit lasting preferences/goals may then be saved by the separate bounded job. Actual save notices offer removal of the saved revision. No notice is fabricated while extraction is pending.

An entry → View source message → owned message text; Edit → versioned content/scope/expiry update; Delete → explicit permanent-deletion confirmation → remove entry from local view after success. A stale edit retains the unsaved form and shows the conflict. User requests take priority over saved settings, relevant memory and confirmed observations. Temporary requests remain temporary. Disabling memory stops future use/extraction; profile-off disables both for its turn. Memory deletion and original-chat deletion are separate actions. Account exit unmounts all memory content.
