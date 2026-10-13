# Week 10 Member Report
Baiqing Huang
Learner-facing interfaces, transcript recovery and browser verification
Prepared for the 13 October 2026 release
Source release: CS30-1_Week10_20261013_22ccbfa899ec
Assigned public source files: 118

## Workstream outcome
Week 10 improves transcript loading and strengthens evidence for composer and failure recovery. The production change starts the session lookup and first history page together, retaining authoritative session errors, ordered pagination and stale-response protection. Browser verification now has a stricter durable-answer and full-render observation boundary. These increments support specific interface contracts; they do not establish general scientific quality, physical-device acceptance or complete coursework acceptance.

## Week 9 foundation and comparison boundary
Week 9 already delivered reader selection and position recovery, learning goals, review, notes/bookmarks, memory controls and model-administration surfaces. Its eight Mock browser journeys and later real-model citation/persistence observations remain historical foundation evidence. They are not repeated Week 10 achievements.

The exact comparison is final_source04_with_reports_matched5_and_token_cache_20261009_01. The frozen Week 10 partition contains 118 complete current files, including application code, tests, scripts and documentation. There are three changed files and nine additions relative to that package; 106 files are unchanged. Packaging additions describe absence from the baseline archive, rather than proving that every added record was first implemented this week. Module ownership does not identify who personally executed a shared experiment [OWN].

## Actual changes after the baseline
In Chat.tsx, loadTranscript begins both authorized reads before awaiting either. The first-page promise captures early rejection while the session lookup is pending. Session errors retain priority; later pages remain sequential. Existing mounted/request guards prevent an old conversation or abandoned page from committing state. All-or-nothing transcript loading remains intact. This removes an avoidable dependency, but its latency saving is unmeasured [F51].

ChatTranscriptRace.test.tsx now verifies concurrent starts and stale/unmounted read pairs. ChatTranscriptRecovery.test.tsx verifies early history failure, subsequent authoritative session failure and successful reload without sending work. The first retained frontend attempt passed six recovery cases but failed to load three suites because a temporary transformed module was missing. The successor completed 57 tests with no source change between attempts; TypeScript no-emit also passed. Both attempts remain visible [F51].

The added checker-contract failure regression verifies that a published answer and edited unsent draft survive a failed source check, with no automatic retry. Its recorded component test passed. A separate Edge UI-only journey passed retention across reload using authored intercepted API responses; it performed no real backend, database or model operation. This confirms the exercised rendering/recovery behavior, without certifying backend checker correctness [F58].

The added composer-route-mock.spec.ts exercises Enter submission, duplicate suppression while awaiting a receipt, Shift+Enter, composition/key-code guards and a distinct follow-up turn with refreshed history. Six Playwright tests and strict no-emit TypeScript passed, with no retries, failures or skips. These are synthetic browser controls; AC-44 remains implemented pending real-flow acceptance, and physical IME behavior remains unverified [C44].

## Browser evidence and its boundaries
The shared Observer112 helpers repair a truthy asynchronous predicate that previously finished observation prematurely. They arm before Send, join receipt/job/request/answer/status identities, compare complete reference and visible DOM text plus ordered citation labels, reject hidden/truncated content and wait through two animation callbacks. Renderer drift fails before Send. Bounded exits dispose polling, observers, callbacks, listeners and temporary DOM; denial stops without retry. Fifteen intercepted browser controls passed. Source review confirms candidate reset and two-callback logic, while the restored-frame fixture does not separately assert absence after its first restored frame. Native111's invalid old elapsed value is not recovered into an answer time [O112].

Recorded Native105 journeys include one configuration failure and three published checked answers, with refresh and Sources reopening. The exposed same-question primary pair took 21.5363 and 19.4613 seconds; its release-index cache was cold. Native108's combined-version journey passed normal persistence/display/refresh/source reopening in 12.7217 seconds with measured cache reuse, but its intended scientific refinement remained NO_GO. These source-bound observations do not establish a current global acceptance gate or a causal speed improvement [N105, N108].

Task129 S01 has no live session, submission or dispatched request. Its workspace controller prototypes are unreleased and excluded from the product report scope. Seven isolated guard controls and fifteen mocked observer controls do not turn that unrun experiment into browser acceptance. The separate S02 checker-only recheck returned HTTP200/stop but failed actual-citation scope validation; no answer was published [N129].

## Limits and concrete Week 11 plans
Current evidence does not cover the full administrator role matrix, every failure replay, accessibility, physical mobile/IME or independent hardware. Display fidelity cannot certify educational correctness. Unified RAG quality, continuous current-version full-answer timing, formal warm p95, independent human ratings and global completion remain open.

Week 11 should run the released package's ordinary login, Send, follow-up, refresh and source-inspection journeys in a separately pinned isolated environment, retaining each failure and exact job/request/answer identity. Extend recovery to rapid navigation, expiry, cancellation and interruption, and verify real input devices. Resolve Task129 controller readiness and review before any new live observation. Use the strict full-DOM observer on repeated matched conditions, keeping startup, failure and answer clocks separate; retain semantic review alongside interface acceptance.

## Evidence references
Paths resolve from the complete project root. Recorded runs are shared workstream evidence, not personal executor attribution or independent human ratings.
OWN: Delivery SOURCE_FREEZE_FINAL.json and report-inputs/owner07-final.json; 118 current files, 12 baseline deltas.
F51: docs/execution/20261010-offline-provenance-performance51.md.
F58: docs/execution/evidence/20261011-checker-recovery58-59/software/frontend58.json and browser58/ui-results.json.
C44: docs/execution/20261009-week10-implementation-status.md, composer integration checkpoint.
O112: docs/execution/20261012-qualification112-observer-and-contract.md and its results JSON.
N105/N108: docs/execution/20261013-native105-s01-rag-and-page-timing.md; 20261013-native108-combined-version-real-result.md.
N129: docs/execution/20261013-native129-recheck-and-week10-release-handoff.md.

## Final release verification — 13 October 2026
The final source freeze is CS30-1_Week10_20261013_22ccbfa899ec. A release QA correction supplies the actual transport helper to an AST-based test harness; production behavior is unchanged. The original failed run is retained. After public tokenizer/DEV fixture preparation, the final unit run passed 4,803 tests and 215 subtests, with 28 skips and 40 warnings. Foundation, contracts, chat scope and targeted Ruff passed. TypeScript, all 241 frontend tests in 27 files, and the frontend build passed.
Actual native Edge checks passed login, New chat, complete cited mock prose, exact persisted answer/history identities, citation opening, refresh and desktop/mobile layouts. All 17 exercised runtime input hashes match the final freeze and all owned services closed. This used existing dependencies, fresh SQLite, an authored corpus and mock models. Clean dependency installation, the final full PostgreSQL/corpus launcher, live quality, formal p95 and human learning effects remain unverified. Public model hydration separately passed. Evidence: release/validation/ and RELEASE_MANIFEST.json in the complete project.
