# Reader recovery and chat history: local increment, 2026-10-06

Current frontend software checks pass: **221 tests in 25 files, TypeScript, and production build**. This increment fixes reproduced reader and chat concurrency defects. Installed stop/retry, browser refresh, and relogin remain unexecuted because a legitimately known existing student login is unavailable. It does not close overall project, installation, model-quality, physical-device or course acceptance.

The reader keeps the highest known document reading-position version during reloads and rejects saves until its initial version is known. An obsolete GET cannot roll back a successful save. Resuming the matching published source unit targets the saved Unicode character offset once per route; it preserves the complete original passage and does not select text. Position-load failures are visible. Chat history uses a request sequence and mounted check: obsolete results and errors cannot replace a newer completed answer or revive an old job, and unmounted history cannot trigger a historical-job fetch.

Before fixes, the new reader suite had 3 PASS / 5 FAIL and chat history had 0 PASS / 3 FAIL. After fixes, all eight reader and three chat cases pass within the final 221; these subsets must not be added again to that total. One existing reader test now matches the complete paragraph text across the new anchor element, preserving its original source-text and paging assertions. A nullable authored test ID type was corrected and the final suite and TypeScript were rerun. Original failed and intermediate outcomes remain retained.

Validation reused the installed Node packages and the existing ordinary Vitest config in the isolated frontend copy. Of 66 current public baseline members, 63 matched main; only the reader, its existing test matcher, and chat were changed, with two new test files. No dependency install, browser runner, model call, service, Docker operation or database action occurred. The build retained its existing large-chunk warning (873.12 kB JS, 252.37 kB gzip); no latency result is claimed. Main remains an unborn master worktree, with no branch reset or commit.

The previous installation is bound to C9; its reader matches the inspected pre-fix source and its App remains the pre-sidebar source. Its prior owned jobs were closed. The earlier five installed cases used an explicitly generated learner/password, so they do not establish that the public helper's default account is available. Existing workspace helpers read a credential file and create a fresh learner. They were not run, no alternate account/token was used, and the historically denied `project/.secrets/initial-admin-password.txt` was not read, probed or retried. No new permission denial occurred in this phase. Ordinary authorized student login is the remaining prerequisite for installed validation.

The existing `frontend/tests/e2e/lifecycle.spec.ts` is the next browser entry for real cancellation, one logical user turn, the same request ID and a new retry job ID, plus completion preserving an older chat reading position. A reader journey still needs save → refresh → sign out → ordinary sign in → Resume reading, with the same document, release, unit and offset. Component remount evidence is not that installed journey. Use the existing Playwright entry/config, current frontend identity and isolated data; do not rerun account-creation helpers or the denied bootstrap launcher.

The frozen twelve-section matrix remains historical. The following priorities supplement it; they are not new completion labels.

| Section | Next non-model work | Priority |
| --- | --- | --- |
| 1. Question intent, evidence and outcomes | Reading selection → editable draft → submitted source-bound question, preserving the saved location | First learner journey |
| 2. Checking, repair and continuity | Real stop/retry and recovery identity; retain stopped Luna and immutable failed quality results | First learner journey |
| 3. Eight connected modules | Reader → chat → notes/bookmarks; then goal pause/resume/complete and authored practice/review | First learner journey |
| 4. Research mechanisms | Keep research variants labelled; evaluate saved evidence separately after the flow works | Later |
| 5. Sources and structured material | Exact published release/unit/Unicode offset restoration; source revoke and old-reference behavior | With reader journey |
| 6. Performance and operations | Current worker cancellation, retry and stale completion; measure E2E latency separately afterwards | Flow first, measurement later |
| 7. Installation, restore and devices | Legitimate existing student login; current-source browser refresh/relogin, then device visibility | Blocked prerequisite first |
| 8. Security, robustness and safety | Logout/session change during pending work; owner isolation and current source permissions | With learner journey |
| 9. Formal experiments and people | Preserve paused human/formal studies and existing data; no large experiment in this phase | External/later |
| 10. Metrics and accounting | Record actual fresh outcomes without double counting; held provider costs stay unchanged | Maintain alongside work |
| 11. Owners and execution | Keep learning-module responsibility attached to concrete results and remaining blockers | Maintain alongside work |
| 12. Delivery and preservation | Preserve old C9 and data; refresh complete/eight-owner/nine-report delivery at a functional milestone | After learner milestone |

After the first journey, prioritize goal/practice completion, note conflict/delete/relogin, review recall/lapse, memory expiry/undo, then four-role administration and source approval/revocation. Model semantics, formal studies, 30% p95 reduction and course sign-off keep their own open acceptance conditions. Luna strict-schema requests remain stopped and no backend G01 candidate was adopted.

See [machine evidence](../../evidence/week09-continuation/20261006-reader-chat-recovery-local-increment-01.json), [final frontend result](../../evidence/week09-continuation/20261006-frontend-recovery-final01.json), and retained [reader](../../evidence/week09-continuation/20261006-reader-recovery-negative01.json) / [chat](../../evidence/week09-continuation/20261006-chat-history-negative01.json) negative controls. Source identities, actual terminal results and local original backups are recorded in the machine evidence. Old C9 complete archives, owner parts and reports are preserved; no new full package was produced.