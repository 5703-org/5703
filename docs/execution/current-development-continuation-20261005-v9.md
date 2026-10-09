# Current development continuation - bound repair prototype v9

Recorded UTC: 2026-10-05T23:37:17.430201+00:00. Project: CS30-1, `E:\5703\learning-assistant` only. Global `project_complete=false`. The current source was safely promoted and independently read back; this checkpoint completes the authorized local structured-repair work, not the outstanding teaching, deployment or course acceptance.

## Result and source

Ten files were promoted: two exact compare-and-swap updates and eight create-only additions. Both original files have retained workspace backups. Main readback verified the ten current paths plus 24 unchanged predecessor paths. Protected Week 9 databases, original experiment inputs/results, historical reports and deliveries were not accessed or modified. No branch reset, dependency install, remote push, upload, deployment or course submission occurred.

The V10 checked hint path with an explicit selection-task contract now asks for a typed bound claim patch rather than a whole TeachingDraft rewrite. The server binds original draft, public request, selection task, projection, claims, protected spans and original defect actions. The model supplies only target IDs and replacement text. Unknown, unlisted, protected, duplicate or stale targets, arbitrary append fields, whole-draft output and model-supplied metadata are rejected. Unlocatable teaching actions stop; global source actions remain deferred and do not authorize arbitrary text.

The compiler reuses `ClaimPatch`/`apply_claim_patch`. It composes the complete body, derives citations from actual markers, and synchronizes bounded visible tutor-question/feedback metadata. It then passes the original complete TeachingDraft parser and the original complete fresh checker. Existing claim preservation, source visibility, typed checker validation, release gates, scoring and the four-call/180-second ceiling remain unchanged. Format correction shares the original budget and cannot spend the reserved final checker call. The private draft retains the raw model patch separately from its compiled body and transformation receipt; no repair plan or receipt was added to public timing/completeness fields.

The patch confines the change to authorized spans; it does not prove the replacement scientifically correct or semantically minimal. A replacement may add content within its authorized span. Source entailment and teaching acceptance still require the full fresh checker. No blind gold label, arbitrary full rewrite fallback or score override was introduced.

| Changed runtime file | Current SHA-256 |
| --- | --- |
| `generation/checked.py` | `f1d61ec76e814e74bcd873092195db936040f91919d54082839dbbb761601015` |
| `generation/repair_patch_v1.py` | `0b92e47e0c1eb6c88caa5126a6342bcbba32e4c85ef25a1276229a16553fe7a7` |
| `generation/prompts/bound_repair_patch_v1.txt` | `9d03e9be2899dcc7e888bc149c92b2c0da2ec2db29cbd1a5e120e22e7d1977f6` |

Actual source promotion receipt SHA-256: `b821ae77848a0c0af6acd3e76de9b20b2a226d30ced17ad113c3bdafb8897aa2`. Final main-source readback SHA-256: `c91273a39c6f0728e028c37e66972d2cb07a5e6ec58a380a97623950feb0d015`. The fixed [source manifest](../../evidence/week09-continuation/20261005/task2-bound-repair-v9-01/Source/source-change-manifest-01.json), [reviewable diff](../../evidence/week09-continuation/20261005/task2-bound-repair-v9-01/Source/source-changes-01.diff) and 58,621-byte [ten-file source archive](../../evidence/week09-continuation/20261005/task2-bound-repair-v9-01/Source/bound-repair-source-v9-01.zip) accompany the actual receipts.

## Fresh free verification

| Gate | Current result | Scope |
| --- | --- | --- |
| Targeted Python regression | 671 passed; 90 subtests passed; 761 JUnit records; 16 warnings | 25 relevant test files, including all 97 new compiler/pipeline/public-projection cases and related legacy repairs |
| Frontend | 204 passed in 22 suites; TypeScript and generated types passed | Existing suite plus three real Chat/API polling/projection contract tests |
| Ruff check and format check | Passed, 24 selected files | Configured executable-correctness rules and formatting |
| Mypy | Passed, five configured files | Does not establish typing of the whole repository |
| Foundation standalone | Passed: 108 tasks, 60 checks, 27 schemas | Exact public static-input copy; design consistency |
| Contracts standalone | Passed: 124 paths, 234 schemas | Runtime OpenAPI construction; SQLite connections zero |
| Chat scope standalone | Passed: 233 runtime Python files, 11 canonical fields | No runtime evaluator prerequisite or private reference mount |
| Independent review | Passed; two findings corrected | Exact source diff, bindings, fresh gates, budgets and public projection |

Python tests use guarded fictional fixtures/isolated SQLite only. Node tests use the existing workspace dependency cache without copying or installing dependencies; its 11,861 file metadata entries remained unchanged, which is not a claim of bytewise cache identity. Source pins stayed fixed during each final run. Standalone repository gates used fresh workspace outputs because their default main functions generate evidence/schema files. They do not establish the complete current mock/PostgreSQL gate or an in-place runtime deployment.

All original failed attempts remain: frontend01 had a new-test nullable-ID TypeScript error; it was corrected and frontend02 passed. Two focused pipeline attempts contained incorrect new-test field/error-key expectations, subsequently corrected without changing product gates. Regression01 stopped before pytest because a small public SDK test was absent from the original clone; its exact test/fixture copies were separately receipted and regression02 passed. Contracts01 retained a guard FAIL for three dependency writes to the Windows null device; contracts02 maps `os.devnull` to a fresh workspace sink while retaining the exact write guard. No such original failure was relabelled PASS.

## Saved failure replay and limits

Saved S11 actual17 and G01 actual18 original drafts, claims, original failure flags and failed full-repair outputs are retained in small provenance-bound fixtures. Both old whole-repair outputs fail the original `unchanged_claims` check. The new claim-only permission replay preserves the exact approved S11 second question and the exact G01 sentence `The equation is 5x - 4 = 21.`, retains all text outside the authorized target, derives empty citations and synchronizes visible metadata. Fourteen existing protected/unknown/stale/append/duplicate attacks were rejected. Eleven input hashes remained unchanged.

That replay is explicitly `PERMISSION_REPLAY_ONLY`: it selects recorded concrete claim actions for a mechanical test, does not erase any failed checker flag and does not evaluate repaired teaching. Full original S11 plan construction rejects `BOUND_REPAIR_UNMAPPABLE` because its global incomplete-answer action crosses the protected question. Full original G01 plan can build three bounded targets but retains `REQUIREMENT_LIMITATION_MISSING` as a deferred source issue; buildability is not semantic acceptance. Fresh checker calls in this saved-case replay are zero; new teaching grade and human rating remain null. Separate authored orchestration tests prove full compiled-draft rechecking and non-publication on failed/invalid fresh checks or insufficient budget, not model quality.

See the [mechanical replay report](../../evidence/week09-continuation/20261005/task2-bound-repair-v9-01/Replay/README.md) and [independent review](../../evidence/week09-continuation/20261005/task2-bound-repair-v9-01/Review/independent-bound-repair-review-01.md).

## Preserved blockers and next minimal phase

The last actual DeepSeek pair remains 1/2 native acceptance and 0/2 strict combined teaching acceptance. Actual18 G01 was withheld because repair changed an approved exact span. Actual19 S11 passed its native gate, but both available legal reviews returned FAIL; their interpretation of formula disclosure and supplied givens remains disputed. The new prototype has not been tested with a paid provider. The same-provider role reviews, human-null fields, inconsistent old checker observations and all original grades remain recorded. Judge reliability and learning effectiveness are not established by these software tests.

Docker remains separately environment-blocked. The retained read-only command `docker version --format '{{json .Server}}'` exited 1: access to `C:\Users\PC\.docker\config.json` was denied and the Docker engine named pipe was denied. No retry, alternate configuration, escalation, container/volume action or real-database fallback occurred. Consequently full current mock/PostgreSQL integration, HC-02 clean installation, AC-25/AC-47 and PER-09/QA-10 remain open.

The source-promotion helper's first C-only Win32 control also stopped on `DIRECTORY_OPEN_FAILED_5` while reading an unnecessary ancestor. Its exact target was not serialized; retained-stack reconstruction identifies `C:\Users\PC` and is labelled reconstruction, not direct observation. That target was not retried or granted more access. The final helper starts at explicit authorized W/E anchors, validates those anchors and internal paths with retained no-follow handles, and leaves external ancestors unaccessed and uncertified. New C-only controls passed. Directory creation and writes are not crash-atomic; partial new files are retained, original-file restoration is receipted, and any existing intent stops replay.

No new paid calls, private credential reads or new model votes occurred. Earlier authorization and protected fee ceilings remain preserved, including DeepSeek protection CNY26.501372, direct USD0.22 and OpenRouter USD0.62; no hold was released and billing confirmation remains null. The existing 109-row model matrix and its independently verified costs/provenance were not edited.

The next minimal real test is the same two frozen public cases G01/S11 against these exact source hashes, at most four native calls per case including its full checker/recheck, followed by the existing original rubric and finite review-role budgets. Keep native acceptance, valid external FAIL, invalid review and human-null fields separate; stop on refusal, exhausted budget or source drift. First confirm the full request bound includes the new repair plan/schema. No large experiment or extra vote should be substituted for that two-case result. That paid phase is held under the current no-new-calls instruction; future Docker access and isolated PostgreSQL require a separately released environment path. No remote publication, deployment or course submission is included.

The [evidence index](../../evidence/week09-continuation/20261005/task2-bound-repair-v9-01/README.md) and `CURRENT_STATUS.json` identify this current checkpoint. All predecessor reports, delivery ZIPs, source histories and status-document bodies remain preserved.
