# Chat-first user flows

## Login and accounts

Open app → authenticate → `/chat` → load owned sessions, current profile and capabilities. Expired/disabled credentials return explicit errors and offer re-login. Logout/account switch clears account-specific in-memory state and credentials. Re-login retrieves server history and active jobs. Profile and password actions use real validated endpoints; admin navigation is role-aware and the server still enforces privileges.

## Conversation

New chat → empty transcript → optional saved-profile policy → enter free text → submit with a stable idempotency key → server commits user message and queued job → poll actual preparation/retrieval/generation/saving stages → show only the persisted validated assistant revision.

An answer shows complete prose and current-request citations. A clarification asks the missing detail. A grounded refusal explains evidence limits. A social response can omit sources. A failed/cancelled job remains visible as that state and may expose Retry only for the eligible latest user turn. Infrastructure errors never become refusal or success. Sending another message keeps this session and its server-selected context. Suggestions submit ordinary text, not benchmark records.

The composer disables duplicate submission while retaining editable drafts. SESSION_BUSY/validation/connection errors retain the draft. Stop cancels the actual job. Retry creates another job for the original request and snapshots. Latest completed answer regeneration creates a new revision while keeping the prior visible answer until success; failed/cancelled replacements retain the old answer and feedback. The backend remains authoritative if a stale action conflicts.

## History, sources and feedback

Select conversation → forward-paginated saved transcript → actual active revision and current jobs. Rename/archive/restore act on the selected owned session. Archived sessions are read-only until restored. Opening a citation sends the answer ID and evidence ID to the evidence endpoint. The drawer displays the original permitted passage, source title, section and real locator; Details reveals immutable provenance. Revoked/missing evidence is explained, never replaced. Closing a drawer restores focus and reading position.

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
