# Week 8 Module Report

Baiqing Huang | Learner interface and inspectable sources | 2026-09-20

## Domain outcome

The frontend domain makes approved source fragments, learning memory and teaching actions visible in the existing conversation flow. The learner sees the saved deliverable, while rejected drafts and private checker explanations remain outside the public interface.

Original accountable task IDs: FE-01, FE-02, FE-03, FE-04, FE-05, FE-06, FE-07, FE-08, FE-09, FE-10, FE-11, FE-12, CHAT-06.

## Implemented changes

Claim-aware citation rendering uses the supplied answer-text positions and exact claim text so repeated evidence markers can resolve to the appropriate claim. Source inspection renders the approved segments and their highlight associations. Legacy answers retain an explicitly coarser source display when exact attribution was not recorded.

Memory controls expose enablement, saved entries, source context, versioned edits, expiry and deletion. Task actions distinguish another hint from a full explanation. The interface records the content actually rendered or expanded, allowing cumulative teaching checks to use real exposure rather than an assumption about an unopened panel.

Controlled hints restrict ordinary source display to the approved projection. An explicit full-source or full-explanation action is a separate recorded transition. The paired highlight review presents identical answer and source content through two display methods and records actual review interaction without converting an automated timing check into a human result.

## Interfaces and dependencies

Zeping supplies strict authorized DTOs and persisted projection state. Sijin supplies exact claim ranges and checker-approved text. Hongle validates source positions, Pengyuan defines understandable teaching and memory actions, and Chong supplies blinded review materials and measurement instructions.

Implementation and dependency paths: frontend/src/SourceSegments.tsx; frontend/src/Memory.tsx; frontend/src/learning-types.ts; frontend/src/sources.ts; evaluation/enhancement/highlight_review.html.

## Current verification

Actual desktop 1440 and narrow 390 journeys exercised the new source and memory controls with the same retained interface style. Opening a claim showed 304 approved source codepoints and one associated highlight; the deliberate full-source action exposed 1,480 codepoints and its original link. Reload returned the approved restricted preview. Keyboard Escape restored focus, and the full-source render referenced the corresponding expansion receipt.

The memory journey used real extracted entries, source inspection, saved-notice Undo, editing and deletion. A concurrent server edit produced 409 and left the typed draft intact; refreshing the version allowed a subsequent save. The final state has the verification entries deleted and memory off. These transitions rely on actual successful responses and retain earlier verifier failures separately.

Three new browser requests progressed from hint level 1 to level 2 and then an explicit direct explanation on the same task. All three generated presentations have separate delivered and rendered events. Starting a new problem reset the next composer action to direct. The timed paragraph/highlight comparison is also ready with counterbalanced seeded order and downloadable judgments. Actual reviewers can now measure verification time and correctness on the paired displays.

| Matched record | Accounted | Planned |
| --- | --- | --- |
| Actual learner control journeys | 3 | 3 |

Independent human ratings recorded for this checkpoint: 0. Prepared review materials are ready for the group's two reviewers.

## Failures and limits

Component and browser checks establish defined interaction behavior, not faster verification or better learning. Actual reviewer timing, correctness, assistive-technology use and physical-device behavior require their own measurements. Missing historical attribution must not be presented as a new verified fragment.

Week 9 collection should pair verification correctness with actual completion time and keep order effects visible. Extend keyboard and disclosure checks to physical mobile devices, native IME and assistive technology. Rendering receipts describe displayed DOM; reading and comprehension remain separate observations.

## Module operation

- Open a saved answer, activate a claim citation and compare its highlighted fragment with the approved surrounding source text.

- Use keyboard navigation and a narrow viewport to inspect sources and memory controls, then reload the saved conversation.

- Request another hint and an explicit full explanation, checking the visible mode and recorded expansion behavior rather than hidden draft text.

## Week 9 actions

- Collect paired human verification time and correctness on the fixed paragraph and highlight displays, with condition labels hidden and order recorded.

- Review accessibility and narrow-screen behavior on additional actual devices and assistive tools; keep those observations separate from component tests.

- Resolve display misunderstandings found in the review without changing the checked source content after publication.

## Accountability and evidence

These are accountable project domains from the original team allocation. The implementation and verification cited in the reports were performed through the shared project workflow. Domain ownership does not establish a personal commit, individual execution, independent review or personal authorship. Actual execution record: Codex performed the shared implementation, scripted execution and document preparation. Named members remain the accountable module owners. Independent reviewers have supplied 0 ratings.

Claim source browser journey. Actual approved preview, explicit expansion, keyboard and 1440/390 viewport checks.

evidence/week08-enhancement/20260920/frontend/live-source-browser-summary.json

SHA256 33d81448493b3c9125b5b71d632626ad4c1f837b4a944b9d6044530a63ea9b14

Memory browser journey. Actual opt-in, source, edit conflict, retained draft, deletion and save Undo.

evidence/week08-enhancement/20260920/frontend/live-memory-browser-summary.json

SHA256 4ca1b7d75ec5d4b4f0050d799251a1ba231dd4e6cb85062ace9a6bd02083a51b

Teaching browser journey. Three saved hint/hint/full-answer requests and actual rendering receipts.

evidence/week08-enhancement/20260920/frontend/live-teaching-browser-summary.json

SHA256 29dc575d39d1476aeb0a87f5ee5c3a19f2bcdca9dc7805dc6ebd48524f235d2b

Actual paired highlight material load. 148 claims and 296 paired presentations loaded in the browser; text/Unicode checks only, zero timed responses.

evidence/week08-enhancement/20260920/human-highlight-load.json

SHA256 c087d011969305de6be5f3716b3c604b1c3b2cd2af40e43d3b8aafa61509bca2
