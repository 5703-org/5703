# Actual background browser journeys - 8 October 2026

Eight specified user journeys passed across retained runs on the explicit Mock, authored synthetic application. This is connected browser acceptance for these journeys, not live model quality, human assessment, an independent device or final archive startup acceptance. Recorded at 2026-10-08T13:12:06.119061+00:00.

The tested candidate is `CS30-1_Main_20261008_57e95a388684`; its original 1487-file public index SHA256 is `aed1829992f638a4cef4704ef6e650c0b83f2dce69135ce90b53f2298a99c440`. Actual runtime binding verified all 483 production-prefix files and 62 existing built frontend assets (2,004,414 bytes). The canonical frontend asset-row SHA256 is `1756593e0c8214348489e2d3837f68cdd32fe4b8cbb56257b12d83863f2c6d89`. No production file or built asset changed in this phase. This new report and the two appended ledgers are explicit post-gate documentation changes; the final source index must be captured afterwards.

| Actual journey | Result | Selected passing run | Elapsed milliseconds |
| --- | --- | --- | --- |
| 01-login-session-refresh | PASS | local-ui-eight01 | 3472 |
| 02-reader-selection-scope | PASS | local-ui-eight02 | 1790 |
| 03-normal-multi-turn-citations | PASS | local-ui-eight01 | 3905 |
| 04-practice-feedback-tutor | PASS | local-ui-eight01 | 2501 |
| 05-goals-review | PASS | local-ui-eight02 | 2415 |
| 06-memory-controls-undo | PASS | local-ui-eight05 | 6771 |
| 07-note-export | PASS | local-ui-eight02 | 1954 |
| 08-admin-mock-model-controls | PASS | local-ui-eight03 | 2509 |

Login included an invalid-password error, sign-out/re-login and saved-session refresh. Reading used real DOM selection, a bookmark, saved reading position, chapter/textbook/all scope controls and an editable chat draft. Chat covered multiple turns, actual submitted synthetic source text and persisted answers. Practice covered a real UI attempt, feedback, hints, explanation and tutor entry. Goals and review used UI-created records; recall is a self-report and does not establish mastery. Memory covered actual edits, pause/resume, deletion cancellation and confirmation, asynchronous global settings, a chat-origin saved preference and undo. Note exports downloaded Markdown and DOCX and checked that the UI-authored edited note exists in the exported content. Administrator checks used only explicit Mock configurations, project-role tests, activation/history and a rejected insufficient-context configuration.

## Retained outcomes and harness repairs

- `local-ui-eight01`: 3 PASS, 5 FAIL, 0 BLOCKED; receipt SHA256 `aa23e28d945883a87bb50609c3a935eade1ef0e679161d4a78b3972cb4101800`.
- `local-ui-eight02`: 3 PASS, 2 FAIL, 0 BLOCKED; receipt SHA256 `3926ac8e696d0744da1e8df9000e23e1241fee111b507fbac58e3bc64dd36598`.
- `local-ui-eight03`: 1 PASS, 1 FAIL, 0 BLOCKED; receipt SHA256 `38dc1e4993b443ca98aaafc3d2fe6e1184f15b3ec9eb583c7aae953a0b705580`.
- `local-ui-eight04`: 0 PASS, 1 FAIL, 0 BLOCKED; receipt SHA256 `a9841a0201c20d7d1c5aa564e171ea92378bbb1f7dcfdc408ac2351147aeb235`.
- `local-ui-eight05`: 1 PASS, 0 FAIL, 0 BLOCKED; receipt SHA256 `a7feb8291dfda42f920eda7fd325baad79d0728f264d0fbaff5c649c89777bae`.

Run04 displayed no save/undo control within45 seconds after an unqualified global preference statement. Source/history review links this to the retained deleted global `detail_level` key and the V5 `deleted_field_requires_confirmation` rule; the exact worker operation was not separately inspected. Run05 used an available biology scope and observed the actual UI Undo POST200. Its final zero-count assertion initially occurred while the list was loading. The separate loaded-state confirmation requires HTTP200, a visible Saved entries heading, disappearance of loading text and the existing assessment entry before checking absence; it repeats after browser reload. This confirmation passed both rounds in 5418 ms and is retained as `local-ui-memory-persistence06/memory-persistence-receipt06.json` (SHA256 `cec702ce9d98045f78823fd856d43121e7bcca9bfb1b57d4be706b49d994cc5a`). The original Run05 receipt and loading screenshot remain unchanged.

The first five failures were locator/cleanup errors: exact label matching included select options or prefilled textarea child text, and one failed note edit left its real modal open. The next memory failure occurred after a successful HTTP200 settings update because the immediate checkbox assertion preceded its asynchronous controlled-state update. The model numeric settings were inside a collapsed Advanced settings disclosure. A repeated memory edit also attempted to reuse the unique scope of its previously deleted synthetic record and returned HTTP409; the terminal journey uses a fresh subject scope and retains that conflict outcome. The successor scripts use scoped semantic controls, actual close/disclosure clicks and awaited visible state; no force click, DOM removal, authentication bypass or direct API acceptance shortcut was introduced. All earlier receipts, errors, screenshots and safe DOM records remain retained. After deleting the original synthetic preference through UI, a new explicit chat statement created a new preference record. No database reseed was performed.

Each run used one hidden headless Edge browser/page and one worker, with GPU disabled, a private new profile, BelowNormal priority and one-CPU affinity. Browser contexts closed; page errors and denied external request arrays were empty. The isolated PostgreSQL container and application used only this round's synthetic records. Three bounded application lifetimes ended, and the same database/configuration/source was restarted afterwards; earlier state was retained. No protected private staging database, paid provider, original Gold input, other project or user's foreground browser was accessed by these journeys. Low priority is a measured configuration, not a guarantee of zero operating-system contention.

The release's finite public UI evidence set contains the actual receipts, passing and failed screenshots, safe DOM text, note exports, runner versions and exact runtime/build binding. Synthetic credentials, runtime configuration, browser profiles, cookies, request headers and tokens are excluded. Final archive/report identities and extracted-package startup remain separate until actually verified.

The prior [current Main integration evidence](evidence/20261008-checker-rag-native/current-main-integration01/index.json) remains the complete free software gate: eight stages, 4250 Python passes, 129 passing subtests and 26 skips. These browser checks do not rerun or replace that gate. Current53 counts remain 5 implemented_verified, 38 implemented_pending_verification, 8 incomplete, 2 external_condition and 0 unknown; `project_complete=false`. All seven formal study families remain open, human measures remain null, retained native case04 remains failed, and the old STOP/UNKNOWN/budget reservations remain binding. No paid continuation, deployment, remote push or course submission is implied.
