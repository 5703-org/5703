# Frontend guide

The learner application starts at `/chat`. It accepts ordinary questions and follow-ups in the same conversation. The current local demonstration retrieves from four genuine OpenStax PDFs using real local E5 embeddings. Answer generation uses a deterministic mock adapter; the visible “Demo (mock model)” label identifies this mode. Earlier software checks use authored fixtures. SciQ and evaluation runs are separate from chat.

## Start and verify

Start the API, database and worker using the repository operations guide. In `frontend/`, install the locked dependencies with `npm ci`, then run `npm run dev`. The development address is `http://127.0.0.1:5173`; requests under `/api` reach the API at port 8000. Set `API_PROXY_URL` before starting Vite to use a different API origin. No response is fabricated when that API is unavailable.

`npm run build` checks TypeScript and produces `dist/`. The Docker build installs the same lockfile, builds the application and serves it with nginx. nginx preserves `/api/` paths when proxying to `api:8000`, supports direct navigation to nested routes, and applies the API's 250,000,000-byte request limit. It caches hashed assets while refreshing the HTML entry point.

`npm test` runs component regressions. `npm run test:e2e` exercises the real local API, database and worker using Playwright and installed Microsoft Edge. Set `PLAYWRIGHT_CHANNEL=chromium` to use a Playwright Chromium installation; `FRONTEND_URL` can target another running deployment. Browser tests create explicitly named test accounts, sessions, documents and experiments; use a development database. They require the repository development seed and the authored stress fixture described in `evidence/integration/ui_stress_fixture.json`.

Run `npm run types:generate` after the backend exports `contracts/openapi.json`. Commit `src/generated/api.ts` with the contract change. `npm run types:check` fails if generated types are stale. Learner DTOs in `src/types.ts` are aliases of that generated schema. Administrative records remain generic where the backend deliberately exports dictionary responses.

For genuine browser zoom checks, install full Playwright Chromium, set `PLAYWRIGHT_BROWSERS_PATH` to its location when necessary, and run `node scripts/verify-browser-zoom.mjs`. This script changes Chromium's native Page zoom setting at 125%, 150%, 200% and 400%, measures the resulting CSS viewport and pixel ratio, and removes its isolated profile after closing the browser. It does not substitute CSS zoom or device-scale emulation.

## Learner controls

- Sign in with a provisioned account. Tokens and private drafts are stored only in the current browser tab's session storage. Refresh preserves the session; sign-out, expiry and password change clear private state.
- Type a question and select Send, or press Enter. Shift+Enter adds a line. Composition events prevent Enter from sending unfinished IME text. Messages have a 4,000-character limit. A draft remains editable while a response is running.
- Use New chat for a separate conversation. The sidebar restores existing conversations. Conversation actions rename or archive the current chat; archived conversations can be restored to continue.
- The response shows the actual job stage. Stop asks the service to cancel the job. Retry repeats the failed logical turn using its request identity. Regenerate replaces only an eligible latest answer; the previous answer and its feedback remain available until the replacement succeeds.
- Select a citation or Sources to read the stored original passage, full source title and available locators. Unavailable or revoked passages produce an explicit error instead of a substituted passage. Escape closes the panel and restores focus.
- Saved evidence with an HTTPS OpenStax source URL displays “OpenStax / Rice University · Access for free at openstax.org” and a link to that original source. Older evidence without saved provenance and generic fixtures remain unbranded. Figure/formula limitations stay visible in the locator and wrap in narrow panels.
- Copy copies the complete response text. Feedback opens the stored helpfulness and comment, supports edits, and preserves typed text if saving fails.
- Learning preferences offers beginner, intermediate and advanced levels, explanation style, interests, save and reset. A revision conflict keeps the edit visible and provides Reload saved preferences. The per-turn profile switch affects later generation; it leaves conversation history intact. Earlier responses display the snapshot actually used.
- Your account supports changing a display name and password. A new password requires 10–128 characters. Changing it revokes existing credentials and returns to sign-in.

At narrow widths the sidebar and sources open as overlays. The transcript and composer remain separate scrolling regions. Long code, tables and formulas scroll within their own region; prose and long words wrap. When reading older messages, a completed answer does not force the transcript to the bottom; Jump to latest returns to the newest content.

Long saved conversations load automatically in ordered batches of 100 messages until the history is complete. There is no separate Load older action. The actual pagination check retained 104 saved messages, an older reading position and an unsent draft; its separate social-turn fixture is UI evidence only.

## Administrator controls

Corpus shows actual document versions, quality findings, processing runs and immutable releases. Upload a permitted text or PDF asset with its title and usage constraints. Process / reprocess submits a durable job; Refresh shows its current result. Documented exclusions use `unit sequence: reason`, one reviewed unit per line. Existing quality findings remain recorded.

Build release selects ready processing runs. A validated release can be activated. Rollback requests activation of a prior valid release. Integrity or source-availability errors remain visible and leave the server's actual state authoritative. Deactivate/restore controls source availability; permanently revoked sources cannot be restored through the interface.

Experiments remain a secondary administration page. It distinguishes chat scenarios, SciQ-derived open answers, SciQ-derived MCQ diagnostics and profile studies. Create run freezes the chosen dataset revision, split, condition, seed and immutable configuration. A configuration can supply public evaluation questions. Otherwise the complete public question list must be attached with the evaluator/import API before Freeze becomes available. Reference answers and private support stay in the evaluator.

Freeze records the actual manifest. Start dispatches the frozen workload; Refresh updates its outcomes. Cancelled outcomes remain final. Results & configuration and Export records include the scheduled denominator, completed, failed, cancelled and missing-input states, actual item records and manifest. Missing ratings and measurements remain missing. Existing profile-study runs are shown independently with their own mode and conditions. Creating and importing profile or conversation protocols uses the dedicated evaluation tools documented in the evaluation guide.

Feedback review displays saved learner feedback and supports a review state, note and linked issue. Saving a review changes the stored record without modifying learner preferences or earlier answers.

## Implementation map and evidence

`App.tsx` owns authentication, route selection and navigation. `Chat.tsx` owns durable job polling, drafts, history, evidence and feedback. `Markdown.tsx` handles safe Markdown and formula rendering. `Settings.tsx` and `admin.tsx` provide account, profile and operator pages. `components.tsx` contains accessible shared controls and native-dialog focus restoration. `styles/tokens.css` and `styles/app.css` define the responsive visual system.

Browser results and screenshots are under `artifacts/reports/frontend/`. Each run has its own result file and preserves failure screenshots/traces; successful reruns do not erase the earlier diagnosis. `docs/execution/audit-ui.md` maps the original frontend task IDs and UI subchecks to their implementation and evidence.

Historical checks use authored fixtures. The full official-source browser journey passed source attribution, follow-ups, a topic change, profile-off, regeneration, re-login, clarification completion and responsive layout at eleven widths; see `artifacts/reports/frontend/openstax/2026-09-08T08-27-08-234Z/verification.json`. Answer generation remains explicitly mock. The valid A→B→A browser rollback passed with completed HTTP200 responses, exactly one active pointer and unchanged saved history/answers/evidence in `artifacts/reports/frontend/openstax-rollback-roundtrip/2026-09-08T08-42-25-678Z/verification.json`. Both checks name their exact release and runtime. The later v5 release passed its focused new-conversation and current/historical citation check at `artifacts/reports/frontend/openstax-v5/2026-09-08T08-54-45-868Z/verification.json`. Default-size real pagination passed at `artifacts/reports/frontend/history-pagination/2026-09-08T08-55-45-630Z/verification.json`. Earlier integrity rejection, external Docker interruption and verifier assertion/timing failures remain preserved in the UI audit.

Physical mobile keyboards, native operating-system IME input, screen-reader review and human usability acceptance require their own device or reviewer session. Synthetic composition tests, automated focus checks and desktop browser zoom are recorded separately. Mock application checks do not establish live model quality or educational benefit.

The final component suite passes 23 tests, including answered and refused historical MCQ history rendered through the full Chat component with original evidence and no submission mutation. Evidence: `evidence/ui/legacy-mcq-final-component-tests.json`. These are read-only component fixtures, not additional historical answers inserted into the official corpus database. The production build passes. The source-attribution checkpoint's generated contract drift check is preserved in `evidence/ui/openstax-attribution-component-check.json`. The final real-release browser journey verified full source text/hash, the official link, exact saved license metadata, and physical-page/figure-formula notices at 1440px and 390px. The mock's conservative abstentions and semantic limits are documented in `docs/execution/mock-evidence-replay.md`.
