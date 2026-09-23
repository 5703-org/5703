# Actual keyboard, suggestion and rejection verification

The final browser run is [2026-09-08T09-54-55-082Z](../../artifacts/reports/frontend/keyboard-suggestion/2026-09-08T09-54-55-082Z/verification.json). It uses a dedicated account and the actual application, worker and database. The answering model remains mock. There is no response interception or inserted answer fixture.

The browser presses Shift+Enter to insert a newline without a POST, then Enter to send the exact multiline question once. A saved socratic profile causes the existing mock adapter to emit a follow-up suggestion. Clicking that rendered suggestion sends its exact text once and retains the resulting refusal as a real terminal response. The test verifies the four persisted history rows and cited source text hashes. Submitted-request release/configuration binding is recorded separately in the companion evidence linked from the continuation report.

After archiving only its owned verification session through the API, the already-loaded browser sends a draft and receives the actual HTTP 409 `CONFLICT`. At both 1440 and 390 pixels the full error is visible without manual scrolling, the draft stays present, and no answer or history row is invented. Restoring the same session returns exactly the previous complete history; reloading retains the unsent draft. These are submission-rejection checks, not provider-execution fault injection.

Actual polled `queued`, `preparing` and `generating` stages are matched to visible status text. The record does not claim that every possible short-lived stage was observed. The final saved page-error list is empty. The subsequently added final observer guard ensures that late errors also fail future runs; it does not alter application behavior or this zero-error observation.

## Discovered display issue and preserved attempts

- [09:50:11 attempt](../../artifacts/reports/frontend/keyboard-suggestion/2026-09-08T09-50-11-759Z/verification.json) failed a helper comparison: archiving correctly changed dynamic `can_regenerate` eligibility. The comparison now checks durable fields while archived, explicitly verifies regeneration is disabled, and compares all fields after restore. The source and history were not changed to force a pass.
- [09:51:32 run](../../artifacts/reports/frontend/keyboard-suggestion/2026-09-08T09-51-32-137Z/verification.json) passed the interaction checks. Visual inspection found that its rejection alert was partly below the transcript fold. The content remained manually scrollable; the report is not a full automatic-visibility pass.
- The current `frontend/src/Chat.tsx` scroll effect now reacts to error, polling error and pending/terminal state changes while retaining its existing follow-latest guard. Two deferred-rejection component cases verify automatic reveal at the latest content and no jump when a reader scrolls upward while waiting.
- The final real-browser run adds full-alert viewport and transcript-boundary assertions at both widths. Its screenshots were visually inspected, including the narrow layout. All previous attempts, test users, sessions and original citations remain retained.

The reproducible helper is `frontend/scripts/verify-keyboard-suggestion.mjs`; supply a dedicated `ui-keyboard-` account through `TEST_LEARNER_EMAIL` and `TEST_ACCOUNT_PASSWORD`. It records no password or access token. Physical soft keyboards, native IME, assistive technology and independent human usability remain separate unverified responsive subchecks.
