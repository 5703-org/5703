# Week 8 Work Report

Baiqing Huang | Learner interface and inspectable sources | 2026-09-22

## Week 8 contribution

Expose typed memory and provider compatibility through the existing learner and administrator screens. The interface displays actual saved state, scope and safe errors while preserving the approved answer/source projection.

Original task allocation: FE-01, FE-02, FE-03, FE-04, FE-05, FE-06, FE-07, FE-08, FE-09, FE-10, FE-11, FE-12, CHAT-06.

## Completed implementation

Memory controls show categories, source/version information, summaries and processing status. Learners can edit, delete, disable and override preferences through authorized contracts. Revision conflicts preserve the draft instead of reporting a false successful save.

Models separates saving, declared profile selection, tier/role testing and activation. Answer and checker eligibility are visible independently. Lost receipts reuse the same idempotency key; mock checks are labelled, and plaintext credentials are cleared after saving.

Failures renders a strict allowlist of HTTP status, provider code/parameter/request ID, finish reason and network category. Memory status is distinct. Existing keyboard, responsive source inspection and explicit teaching disclosure controls remain integrated.

## Interfaces and operation

Zeping supplies authorized versioned DTOs, Pengyuan memory meaning, Sijin safe provider categories, Xianshu contract integration, and Chong actual browser and independent usability evidence.

- Inspect memory provenance and processing status, then exercise version-conflict feedback.

- Review each model tier and both roles before activation.

- Inspect failures without exposing prompts, credentials or private checker text.

## Verification and findings

The learner interface exposes typed memory through familiar controls: summary, current-question preview, source inspection, edit, expiry, disable and deletion. Revision and processing failures remain visible. The preview clears when its inputs or memory revision change so a late response cannot display stale learner state.

The actual memory browser run used a new migrated database with authored records. At 1440 and 390 pixels it exercised biology-to-ATP selection, current-instruction precedence, profile-off, the source modal and Escape, typed correction, disable and deletion. Five screenshots were reviewed individually. The App/Memory regression also verified that sign-out removes rendered private content and the session token.

The administrator Models journey saved and tested a local mock configuration for answer and checker roles, then enabled the eligible pair. A saved successor with insufficient context failed its actual checker project reservation and remained disabled. The previous active pair was preserved before restoring environment settings. Three desktop/mobile screenshots were inspected.

The final frontend gate passed 86 tests across 11 files, with generated-type verification and production build passing as separate stages. The portable source viewer rendered exact approved segments and saved history after reload. These observed flows use real endpoints; local mock probes and answer labels remain explicit.

The completed numerical report retains all planned outcomes for the assigned studies, including failures and human-dependent oracle cases. Domain accountability does not imply that the member personally executed the recorded automated work.

| Study | Recorded | Planned |
| --- | --- | --- |
| Study T Teaching Control | 180 | 180 |
| Study M Learning Memory | 180 | 180 |

## Current limits

Component and browser checks cover the recorded interactions. Live test receipts identify observed provider compatibility. Physical devices, assistive tools and campus-network access need additional measurements.

Physical mobile keyboards, IME, assistive technology and independent usability observations need their own sessions. Long native select values are clipped within the narrow control while the page remains within its viewport; additional device review can assess the usability of that presentation.

## Week 9 goals

- Collect independent usability/accessibility observations on additional devices.

- Refine confusing labels without hiding errors or missing results.

- Verify interrupted interactions against idempotent backend contracts.

## Code and evidence

Module paths: frontend/src/Memory.tsx; frontend/src/Models.tsx; frontend/src/Failures.tsx; frontend/src/api.ts; frontend/src/generated/api.ts.

Codex performed the implementation, automated checks and recorded local browser verification through the shared project workflow. The eight reports follow the original accountable domains; member submissions and independent human reviews retain their own execution records.

Final frontend results. 86 passing tests across 11 files; types and production build also passed

evidence/week08-memory-v2/20260921/software-gate-release-final-20260922/frontend_tests.log

SHA256 b82379564072e72962e56721868bda2bea5e0e29e45517cf91b509a60fe55004

Actual Memory V2 browser workflow. Owned authored data in a separate migrated database; preview, source, edit, disable and deletion through actual endpoints at 1440 and 390 pixels; zero provider calls.

evidence/week08-memory-v2/20260921/memory/browser-final/verification.json

SHA256 aff7e1263b4d2bd6fbbab2a69cba2fbb9c372fa80ea8862965875139a1495d8c

App and Memory route regression. 16 passing overlapping component/integration checks, including removal of rendered private memory and the session token on sign-out.

evidence/week08-memory-v2/20260921/memory/app-memory-current.json

SHA256 8a22bf5b297d405287776e7809b554642947384d82d2940f3467bf89f2ab66e4

Actual Models role and activation workflow. Local mock answer/checker suites, activation gating, actual context-reservation failure and restored environment settings; zero paid calls.

evidence/week08-memory-v2/20260921/portable/models-browser-attempt2/verification.json

SHA256 cf9b908c17046995446b9c0e967d4929b48bfa54cd01437e36ff9708a40d780e

Models desktop and mobile review. Three screenshots inspected; failed successor remained ineligible and the prior active pair was preserved before environment restoration.

evidence/week08-memory-v2/20260921/portable/models-browser-attempt2/visual-and-workflow-review.json

SHA256 abeacec6c2a82a5922b4a30798efb06d489306fc84f7a8c0096bb5f98fc063fa

Portable conversation and source browser. Saved answers and approved source segments inspected through actual browser endpoints at desktop and mobile viewport widths.

evidence/week08-memory-v2/20260921/portable/browser-attempt1/verification.json

SHA256 f47aacfaa0907cb391b668fe157e033a441a47c9102122e35fec98138957a4b9

Registered automatic study results. 552 scheduled requests across 18 arms; all generation and offline judgment outcomes retained; independent human ratings zero

evidence/week08-memory-v2/20260921/formal/public-results.json

SHA256 b470c9c5df020d3dd7dae9625fdfabc82afdf60569f33a3d62c84a5ea340e7f6

Actual blank blinded review export. Two randomized 552-row reviewer slots; zero completed or imported ratings

evidence/week08-memory-v2/20260921/formal/review-export-verification.json

SHA256 9f9f675f3f00a30b7e64745be7d9ef0f2d2786295fb2cbdbc5a6a43041a75b5a
