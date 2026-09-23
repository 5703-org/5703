# User interface design

Status: implementation contract; verification results belong in the evidence ledger.

## Basis and scope

This document applies v5 Sections 6–8, 10 and 17, FE-01–FE-12 and CHAT-06 together with `FRONTEND_UI_RESPONSIVE_REQUIREMENTS_EN.md`. The historical Week 5 interface note, UX v0.2 requirements, summary, user-flow PNG and wireframe PNG were inspected. Their success, refusal, evidence, profile and error interactions are retained as design intent; they are not evidence of an existing implementation. Clarification, durable jobs, multi-turn context and answer revisions follow v5. The current visual refinement supersedes the dark historical wireframe.

The learner enters `/chat`. One React/TypeScript application serves `/login`, `/chat`, `/chat/:sessionId`, `/profile`, `/admin/corpus` and `/admin/experiments`. Account settings remain available from the sidebar. Evaluation is secondary administration and never a prerequisite for chat. English text is used throughout the repository and UI.

## Visual tokens

Keep tokens in `frontend/src/styles/tokens.css`, without an additional styling framework.

| Token | Value / rule |
| --- | --- |
| Page / sidebar / user message | `#FFFFFF` / `#F7F7F8` / `#F3F4F6` |
| Text / secondary text / separator | `#1F2328` / `#59636E` / `#D8DDE3` |
| Primary action and focus | `#1F2328`; visible focus ring and text labels |
| Body | System sans-serif; `1rem`; unitless line height 1.6; browser root preferences retained |
| Secondary metadata | `0.875rem` |
| Reading column / composer | Shared maximum `50rem`, fluid below it |
| Sidebar | Approximately `16rem` |
| Evidence | Overlay, maximum `28rem`, viewport constrained; fullscreen under 640px |
| Padding / radius | Approximately 1rem mobile padding; 0.5–1rem modest radii |
| Toolbar and input targets | At least 44 × 44 CSS pixels |

Use dark primary actions, subtle borders and generous whitespace. Do not introduce decorative gradients, mascots, large banners, heavy shadows or dashboard tiles. The design follows a familiar conversational pattern without using OpenAI branding.

## Information hierarchy and component variants

- Sidebar: New chat, active and archived session lists, selected state, accessible full title, rename/archive/restore controls, account/profile navigation and role-appropriate administration.
- Header: compact product name and conversation title; sidebar control; accurate `Demo (mock model)` or live indicator from capabilities. Readiness errors are plain text, with evaluation readiness separate from chat readiness.
- Transcript: ordered server messages; subtle user surfaces; assistant prose remains unclamped. Loading stages use actual job state. A valid clarification is a question; refusal explains the grounded limitation; failed/cancelled requests have recovery controls and cannot appear as successful answers.
- Answer: safe Markdown, paragraphs/lists, local scrolling for code/tables/formulas, request-local citations, follow-up text actions, Sources, Copy, feedback and permitted latest-answer regeneration. Display historical applied profile and model mode in compact metadata. Expand detailed rules and traces on demand; no confidence gauge.
- Composer: one multiline natural-language field, profile application toggle, Send or Stop. Enter sends, Shift+Enter inserts a newline, and composing IME Enter does not submit. Limit accepted input to 4,000 characters with visible feedback. Retain drafts on submission errors.
- Evidence: full source title, original permitted passage, section and actual page/locator; details disclose IDs/hashes/request provenance. A 410 response explains unavailability. Never substitute a newer passage.
- Feedback: helpful/not helpful selection and editable comment, with loading/saving/saved/error states. Restore persisted values. Operator review remains connected through administration/API or tested CLI.
- Profile/account: labelled level/style/language/topics, explicit revision-aware save/reset, current profile clearly distinct from applied answer snapshots, password change with visible validation/errors. Canonical profile values are level `beginner/intermediate/advanced`, style `concise/detailed/socratic`, language `en`, topics and integer version.
- Corpus: upload permitted formats, list/inspect versions and quality, real processing status/actions, deactivate/restore, release activation/rollback. Failed operations retain last usable state.
- Experiments: protocol/mode, scheduled counts and every outcome, actual result metrics or `Not measured`, immutable configuration and actual export. Distinguish chat scenarios, SciQ openQA, MCQ and teaching studies, with mock/live labels.

All essential actions work through keyboard and touch, remain discoverable without hover, and have readable disabled/pending/error states. Raw HTML is never executed. External links permit safe protocols only.

## Contract mapping

| UI interaction | Authoritative contract |
| --- | --- |
| Login/account | Auth endpoint and `/users/me`; server ownership/role enforcement |
| Compose | `ChatMessageCreate` plus `Idempotency-Key`; 202 references |
| Progress/recovery | Job state, request state, tail retry and latest revision rules |
| Transcript | Forward-paginated server messages and active answer revision |
| Answer body | `ChatResponseV1`; namespaced legacy MCQ renderer only for MCQ |
| Citation | Answer ID plus current-request evidence ID; exact evidence endpoint |
| Profile | Current revision and immutable historical snapshot |
| Administration | Server documents/releases/experiment records, never invented frontend metrics |

Use one typed API client with standard `{data,meta}` and `{error,meta}` handling. The existing backend uses a bearer access token held in sessionStorage for refresh recovery; logout clears it. Roles are `student` and `admin`. Real API mode has no hidden mock transport. Reusable contract types are reconciled with backend OpenAPI before integration acceptance.
