# Week 8 Work Report

Pengyuan Xia | 550267474 | 26 September 2026

Learner preferences and independent presentation studies

## Week 8 scope

This workstream covers all development after the verified Week 7 final release through the current teaching and performance continuation. Saved profiles and level/style conditioning already existed, including the 27-output C0/C1/C2 study; persistent editable memory and task progression are Week 8 additions.

Original allocation: PER-01, PER-02, PER-03, PER-04, PER-05, PER-06, PER-07, PER-08, PER-09, CHAT-07.

## Completed work across the week

Separated direct explanation from persistent hint progression and recorded cumulative answer/source disclosure without inferring learner comprehension.

Added opt-in preference/goal extraction, source-linked revisions, edit/undo/disable/delete, expiry and derived-data erasure fences with separately bounded extraction jobs.

Upgraded to typed canonical fields, scoped preferences, ordered write events, current-turn corrections and query-conditioned 768-token learner state. Current instructions and applicable explicit subject preferences take precedence.

Added evidence-gated assessment observations and separate extraction, admission, selection and final-answer evaluation; no mastery or learning gain is inferred from a single interaction.

Week 8 retains editable, opt-in learning memory and its typed query-conditioned reader. Current-question instructions take priority; explicitly saved subject preferences take priority over general profile preferences. Saved decisions and memory revisions remain inspectable.

The current continuation keeps teaching state separate from long-term memory. A learner attempt continues its task and help level without declaring mastery or silently creating a preference. Independent model feedback and the current tutor question are persisted with the response.

## Verification and findings

The final 936-test Python gate includes current memory admission, preference precedence, revision/deletion and task-state regressions. The previous 21–22 September memory study remains version-specific: conditioned memory scored 20/36 conservative successes against 21/36 for the unconditioned reader, with an interval including zero. This continuation adds no independent learning or memory-effect claim.

## Personal code package

The package contains the complete current versions of this workstream's cumulative changed files, with repository paths and a baseline/current hash inventory. The personal DOCX matches the standalone report byte-for-byte. The shared implementation and automated verification were performed through Codex; the named member owns the review, explanation and submission of this workstream.

Selected current file areas:

personalisation/

backend/app/modules/learning_state/memory.py

docs/execution/memory-v2-operation-20260921.md

tests/integration/test_memory_v2.py

## Week 9 goals

- Collect independent judgments on memory admission, relevance and preference conflicts.

- Compare task-specific feedback with delayed independent problem solving.

- Review deletion, revision and cross-session behavior using the current complete deployment.

## Evidence

docs/execution/teaching-performance-20260926.md

evidence/teaching-performance/20260926/software-gate-final-02/pytest.xml
