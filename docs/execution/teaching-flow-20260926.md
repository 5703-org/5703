# Persisted tutor questions and learner attempts

Implementation date: 26 September 2026. Executor: Codex. Accountable domains: Zeping Liao (backend and task state), Baiqing Huang (chat interface), Sijin Lu (checked generation), Xianshu Zhang (integration), and Chong Zhang (verification). The [registered protocol](teaching-performance-protocol-20260926.md) defines BUG-03 and the preserved pre-change source identity.

## Product behavior

The assistant can ask a specific question within a hint task. A successful checked hint supplies a tutor question whose exact text appears in the visible answer. Publication assigns a question ID and revision and persists the expected response kind, current step and original learning problem. The composer displays the pending question and sends the task and question revisions with the next message.

For `Compare diffusion and osmosis.`, a tutor question such as `Which process specifically involves water?` accepts `Osmosis.`, a wrong answer, a negated answer or a longer explanation as a learner attempt. The original comparison remains the retrieval and teaching problem. The help level stays fixed. The normal generation and checking calls evaluate the attempted step and prepare feedback or the next question. A checked correct step advances the step counter. Incorrect, partial and unclear attempts retain that step. The public record labels this result as model feedback; independent human scoring retains its separate workflow.

An explicit new problem or full explanation takes priority. Ordinary factual questions and explicit topic changes follow the normal question route. Pending question identity and response form guide classification; message length alone never selects a learner attempt. Older clients can continue without bindings when an active pending question and substantive response cues match. Their unrelated standalone words use the ordinary question path.

## Data and API

Migration `f1b75d8e234c` follows `e0a64c7d123b`. It adds seven columns to `learning_tasks`: `pending_tutor_question_id`, `pending_tutor_question`, `pending_tutor_question_version`, `expected_response_kind`, `current_step`, `turn_role`, and `last_attempt_evaluation`. Existing task rows receive null pending questions, question revision zero, step one and `user_question`. Existing source, answer and exposure records retain their identities.

`POST /api/v1/sessions/{session_id}/messages` accepts four optional additions: `task_version`, `pending_tutor_question_id`, `pending_tutor_question_version`, and `turn_role` (`auto` or `learner_attempt`). A pending question binding requires its task ID, task revision and question revision. Explicit learner-attempt input requires this complete binding. An unknown or foreign task returns 404. A stale task or pending question returns 409. Validation occurs within the owned session submission transaction before a new request is committed.

`TaskOut` exposes the seven added fields. `AnswerOut.learning_task` supplies the current state of its owned task, allowing history reloads to recover the current pending question. Earlier response text, source displays and frozen request snapshots stay immutable. New request teaching snapshots use `learning_task_v3`; they preserve the original problem, pending question identity, response kind, current step and learner attempt. Retrieval preparation uses the original problem for attempts. The ordinary request text remains available for evaluating the learner's response.

The question and feedback metadata is accepted only after generation/checking succeeds and only when its text occurs exactly in the published response. Publication rechecks task revision, question revision and exposure epoch. Failed or cancelled requests retain the pending question. Regeneration keeps the original attempt input while refreshing the current publication fence. Repeated regeneration replaces that step's outcome without counting the same attempt twice.

The general-knowledge detail view also separates model factual assessment from textbook support. It displays `Textbook support: Not applicable` and provides no textbook citation control for a general-knowledge claim.

## Current focused verification

| Check | Current result | Evidence |
| --- | --- | --- |
| Task classification, ownership/revision guards, exact checked metadata, bounded progress, regeneration | 29 unit checks passed | [JUnit](../../evidence/teaching-performance/20260926/teaching/unit-final.xml) |
| Composer binding/reload revision refresh, stale-response preservation, explicit new/full actions, source display and general-knowledge assessment | 36 frontend checks passed | [Vitest](../../evidence/teaching-performance/20260926/teaching/frontend-reload-final.json) |
| Python correctness lint and frontend TypeScript | Passed in the focused command | Full release gate will provide the retained aggregate receipt |
| HTTP persistence and migrated PostgreSQL behavior | Nine cases passed on isolated PostgreSQL 16.15 / pgvector 0.8.6, including all migrations | [JUnit](../../evidence/teaching-performance/20260926/teaching/integration-attempt3.xml) |
| Real configured model conversation | 16 terminal steps: 13 published, three failed; all four first-hint/learner-attempt pairs published | [HTTP results](../../evidence/teaching-performance/20260926/live-http-final/results.json) |
| Actual browser task and assessment display | 12 automatic checks passed; all four screenshots visually inspected | [Browser result](../../evidence/teaching-performance/20260926/browser-final-02/verification.json) |

The first focused run completed 27 assertions but its sandbox denied the JUnit directory write and formatter writes. The subsequent authorized run wrote `unit-attempt2.xml` and passed all 27 checks. Two additional publication/regeneration checks produced the 29-check final receipt. Frontend checking uses controlled API fixtures; it does not establish real answer quality.

The first PostgreSQL test attempt completed migrations but the default Windows temporary-directory access failed for all nine setups. The second run used a new workspace temporary directory and exposed an invalid fixture assumption: its mock hint setup was correctly rejected with `SEMANTIC_CHECK_UNAVAILABLE`. The task-routing fixture now creates a direct mock answer and explicitly seeds the pending hint state. The third run passed all nine HTTP cases. These checks establish ownership, revision fencing, original-problem routing and durable snapshots; configured-provider hint correctness is tested separately. All three JUnit results remain preserved.

The [independent PostgreSQL installation receipt](../../evidence/teaching-performance/20260926/teaching/isolated-postgres-installation.json) records official PostgreSQL 16.15 packages and pinned pgvector 0.8.6 in Ubuntu 24.04 WSL. This new loopback-only server uses port 18532 and `/var/lib/cs30-validation-20260926/data`. Its generated credential remains in a restricted private local file outside the project. Original Docker volumes and the existing project database remain unchanged. The test fixture creates and removes only its uniquely named disposable databases.

The first complete integration run retained 122 passes and six failures in [its JUnit result](../../evidence/teaching-performance/20260926/teaching/integration-all-attempt2.xml). Four scripted checker fixtures needed the new checker contract. The historical-answer assertion now separately verifies the current task projection while checking all immutable saved fields unchanged. The run also exposed a same-process import defect: the Alembic environment put `backend/scripts` ahead of repository `scripts`. Repository-root precedence now preserves command imports after migration. [Four focused existing checks](../../evidence/teaching-performance/20260926/teaching/integration-followup2.xml) and [a fresh-interpreter migration/import regression](../../evidence/teaching-performance/20260926/teaching/migration-import.xml) passed. The [complete rerun](../../evidence/teaching-performance/20260926/teaching/integration-all-attempt3.xml) passed all 129 integration checks, with zero failures or skips, in 109.92 seconds. Earlier failure records remain retained.

## Files and next validation

Task behavior lives in `backend/app/modules/learning_state/tasks.py` and the additive task model/migration. The submission/worker integration is in `backend/app/modules/answering/service.py`. Public contracts are in `contracts/models.py` and `contracts/learning.py`; the generated OpenAPI and frontend types follow those declarations. `frontend/src/Chat.tsx` retains the pending-question context across transcript reloads and includes current revisions in the request. `ControlledEvidence.tsx` keeps general-knowledge assessment distinct from textbook support.

The [release execution record](teaching-performance-20260926.md) connects these scoped checks to current source, model, installation and package evidence. The three retained real HTTP failures and independent human judgment remain separate from the successful task-routing checks. Next validation expands the concept groups, examines the model/checker failures and tests physical input methods and assistive technology.
