# Responsive behavior and acceptance

This is the implementation contract for UI-01–UI-12, mapped to FE-03–FE-08, FE-10–FE-12, CHAT-06, CHAT-08, QA-12 and AC-16/37/43/44/45. It supplements the 108-task and 60-scenario registries without replacing or adding top-level scope.

## Layout continuity

| CSS width | Shell / evidence |
| --- | --- |
| 1024px and wider | Collapsible approximately 256px sidebar; flexible main area; centered 800px maximum reading column |
| 640–1023px | Sidebar collapsed by default; opens as an overlay; full available reading width |
| 320–639px | Single-column chat; sidebar on request; evidence fullscreen with reachable close/back |

Evidence uses a viewport-constrained overlay up to 28rem on larger screens; it never creates a permanent third column. Open only one competing overlay. Modals trap keyboard focus, close with Escape and visible controls, restore trigger focus and scroll internally with a reachable header.

The app uses one stateful React tree across all widths. Media queries change layout rather than remounting conversations. Resize must preserve selected session, draft, active request/job, active answer and meaningful reading position, with no extra answer POST.

## Overflow and available height

The shell is a flexible header/transcript/composer grid with `minmax(0, 1fr)`, `min-width: 0` and `min-height: 0` where required. The composer occupies actual layout space and does not cover messages. Use dynamic viewport height and bottom safe-area padding. The textarea grows to approximately 10rem before local scrolling, with a smaller cap in a short viewport. Preserve transcript, Send/Stop and modal close access.

Prose uses normal wrapping and `overflow-wrap: anywhere` for long tokens. Do not use global break-all, root horizontal hiding, whole-app scaling, shrinking body text or disabled zoom. Code blocks, wide tables and formulas scroll inside named width-constrained regions. Images render no wider than their message. Full source titles and instructions remain accessible. A modal's clipped viewport is allowed only where intended scrolling reaches all content.

Follow incoming output only while the reader is already near the transcript bottom. Otherwise expose Jump to latest. Drawer close returns to the same conversation and position. Browser refresh/re-login reloads actual server history/job state. Failed regeneration keeps the previous successful answer and its feedback.

## Verification matrix

Run the actual application through Playwright with a real API/worker. Use authored content only as labelled fixtures, never as fake production metrics or standalone acceptance pages.

| Check | Required evidence |
| --- | --- |
| UI-01 | Widths 320, 375, 390, 640, 768, 1024, 1280, 1440, 1920, 2560: screenshot, shell width, critical element bounds and reachable controls |
| UI-02 | One loaded chat resized 1440 → 900 → 390 → 768 → 1440; draft/session/job preserved; no duplicate POST; boundaries 639/640/641 and 1023/1024/1025 |
| UI-03 | Actual browser/text enlargement at 125%, 150%, 200%, plus equivalent 320px reflow. Device scale factor or CSS transform is not zoom evidence. Record unavailable manual checks. |
| UI-04 | Long answer/URL/unbroken token/session title/source title/list, wide table/code/formula, many history items and long draft wrap or remain locally scrollable |
| UI-05 | 844 × 390 landscape and orientation changes retain controls; available real-device keyboard open/close checked explicitly, unavailable physical checks recorded |
| UI-06 | Source/sidebar drawers: actual open/scroll/Escape/close, focus trap/return and readable mobile evidence |
| UI-07 | Resize during active generation, failure and re-login; persisted lifecycle correct; failed latest regeneration retains prior active revision |
| UI-08 | Older reading position retained while output arrives; Jump to latest works; panel closure preserves scroll |
| UI-09 | Enter/Shift+Enter, composing IME Enter, visible touch actions, keyboard citation/feedback controls and focus-visible |
| UI-10 | Login/profile/corpus/experiment forms, errors, required fields and pagination accessible at narrow widths |
| UI-11 | Correct sources, historical profile indicators, model-mode labels and explicit error states survive visual changes |
| UI-12 | Review screenshots alongside bounds, local-scroll reachability, actual clicks and persisted state. Run complete no-SciQ chat journey. |

Save screenshots and command results under `artifacts/reports/frontend/`. A page `scrollWidth` check alone is insufficient because clipping can conceal failures. Do not call unavailable physical-keyboard, real zoom, live model or semantic checks passed. This limited test set is not a full WCAG conformance claim.
