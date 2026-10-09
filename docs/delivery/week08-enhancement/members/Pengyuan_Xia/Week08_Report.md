# Week 8 Module Report

Pengyuan Xia | Learning memory and teaching policy | 2026-09-20

## Domain outcome

The personalisation domain separates durable learning preferences from temporary requests and binds hints to an explicit learning task. Current instructions and saved settings take precedence over remembered preferences. No mastery score or learning improvement is inferred from a single conversation.

Original accountable task IDs: PER-01, PER-02, PER-03, PER-04, PER-05, PER-06, PER-07, PER-08, PER-09, CHAT-07.

## Implemented changes

Opt-in memory extracts bounded structured candidates for durable preferences and goals. The production service applies update, correction, expiry and deletion rules, stores versions and freezes the entries actually used by a request. Memory appears in an ephemeral prompt segment; persistent prompt diagnostics retain metadata instead of duplicating its text.

Direct mode uses level zero and requests a complete answer. Hint levels one to three have different instructions for concept comparison, process reasoning and simple calculation. Explicit requests for a complete explanation change the task immediately. A new problem resets the task instead of inheriting a prior hint restriction.

T2 evaluates the answer, compact answer, suggestions, source titles, previews, ordinary source display and cumulative prior exposure. T3 removes cumulative checking; T4 removes current evidence-display control while retaining previous actual exposure. These components are explicit comparison conditions, and all delivered or expanded content remains recorded for evaluation.

## Interfaces and dependencies

Zeping owns durable state, permission checks and deletion fencing. Sijin implements the checked teaching policy. Baiqing exposes memory controls and explicit hint or full-answer actions. Chong compares profile/session, rolling-summary and structured-memory conditions using frozen cases and separate human judgments.

Implementation and dependency paths: personalisation/memory.py; personalisation/compiler.py; generation/joint_policy.py; backend/app/modules/learning_state/tasks.py; backend/app/modules/learning_state/memory.py.

## Current verification

profile session: 5/12 published answers; appropriate-use ratings 3/5 among those answers; state screens 26/34. rolling summary: 5/12 published answers; appropriate-use ratings 1/5 among those answers; state screens 31/34. structured memory: 6/12 published answers; appropriate-use ratings 2/6 among those answers; state screens 34/40.

The 36 authored conditions expose different memory failures: structured extraction and question-scope screens miss expected context, and correction can retain an earlier preference. The study uses the same two real textbook questions and frozen initial evidence across conditions, so retrieval variation is removed from this small comparison. Sixteen published answers receive separate model judgments; 20 generation errors remain ungraded. Appropriate-use scores differ from literal state checks and give no robust ranking of educational benefit.

The actual learner workflow supports opt-in settings, versioned correction, visible source context, deletion and Undo of a save. Browser testing created a real stale revision, received 409 and preserved the learner's draft before a refreshed save. Expiry, global-off, profile-off and stale-job deletion fencing have their own state evidence. Three live teaching requests also preserve a single problem through two hints and an explicit full explanation, establishing the operational route for later pedagogy review.

| Matched record | Accounted | Planned |
| --- | --- | --- |
| Learning memory comparison | 36 | 36 |
| Actual learner control journeys | 3 | 3 |

Independent human ratings recorded for this checkpoint: 0. Prepared review materials are ready for the group's two reviewers.

## Failures and limits

A remembered phrase does not demonstrate improved learning, and a literal retention screen can flag valid paraphrases. The rolling-summary comparator has a declared experimental control policy. Deletion and expiry require tests of derived snapshots and stale jobs as well as the visible memory list. Effective help and appropriate personalisation remain separate judgment questions.

Week 9 review should judge when a preference genuinely improves the answer and when stale context causes a material mismatch. Collect two independent memory ratings and analyse the correction failures before changing extraction rules. Transfer and delayed-learning outcomes require actual participants.

## Module operation

- Enable memory explicitly, save a durable preference, inspect its recorded source and version, then correct or delete it.

- Request hints for one explicit problem, ask for more help and then a complete explanation; inspect the saved task transitions.

- Switch the profile off or begin a new problem and verify which memory and teaching state the next request actually freezes.

## Week 9 actions

- Review all frozen memory conditions for appropriate use, corrections, expiry and deletion, keeping software state checks separate from response quality.

- Use independent ratings to examine whether each hint is useful without exceeding the requested help, including cumulative source exposure.

- Plan an unaided transfer or delayed-learning study with actual participants and consent arrangements before claiming educational benefit.

## Accountability and evidence

These are accountable project domains from the original team allocation. The implementation and verification cited in the reports were performed through the shared project workflow. Domain ownership does not establish a personal commit, individual execution, independent review or personal authorship. Actual execution record: Codex performed the shared implementation, scripted execution and document preparation. Named members remain the accountable module owners. Independent reviewers have supplied 0 ratings.

Memory comparison and separate judging. All 36 authored conditions, state screens and 16 answer judgments; zero human ratings.

evidence/week08-enhancement/20260920/memory-study-final-summary.json

SHA256 77dc2d3080f413728f556d52d692db553d87ae782fad5c99ca0f87fd1ca8c582

Memory browser journey. Actual opt-in, source, edit conflict, retained draft, deletion and save Undo.

evidence/week08-enhancement/20260920/frontend/live-memory-browser-summary.json

SHA256 4ca1b7d75ec5d4b4f0050d799251a1ba231dd4e6cb85062ace9a6bd02083a51b

Teaching browser journey. Three saved hint/hint/full-answer requests and actual rendering receipts.

evidence/week08-enhancement/20260920/frontend/live-teaching-browser-summary.json

SHA256 29dc575d39d1476aeb0a87f5ee5c3a19f2bcdca9dc7805dc6ebd48524f235d2b
