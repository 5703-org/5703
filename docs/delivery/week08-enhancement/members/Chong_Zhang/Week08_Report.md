# Week 8 Module Report

Chong Zhang | Evaluation and independent review | 2026-09-20

## Domain outcome

The evaluation domain converts the enhancement claims into matched experiments and auditable failure denominators. Program checks, model-assisted judgments and independent human ratings remain separate. The reports describe actual execution without treating a prepared schedule as completed research.

Original accountable task IDs: QA-01, QA-02, QA-03, QA-04, QA-05, QA-06, QA-07, QA-08, QA-09, QA-10, QA-11, QA-12, QA-13, QA-14, CHAT-09, CHAT-10.

## Implemented changes

The frozen protocol begins with twelve development tasks across biology and chemistry and three task types. The formal design uses sixty new tasks grouped away from development problem families. Three hint turns across five conditions define 900 planned requests; the independent three-method citation comparison defines 180 direct answers. Actual counts are supplied by the referenced run manifests.

The runner freezes task inputs, source candidates, policy and model metadata. Durable reservations precede external calls, and interrupted uncertain work is not silently replayed. Private critical answers and allowed-help annotations remain in evaluator inputs, outside generation. Every scheduled error, refusal and missing response stays in its declared denominator.

The main contrast is T2 against T1, with T3 and T4 testing the cumulative and source-display components. Analysis pairs by task because its three turns are correlated. Offline judge calls have separate usage and cost records. Blinded review materials support two independent reviewers, agreement analysis and recorded adjudication; uncollected ratings remain blank.

## Interfaces and dependencies

Every domain supplies versioned implementation and failure evidence. Hongle and Chengzhou bind the real source conditions, Sijin exposes call purposes and checked outcomes, Pengyuan defines teaching and memory criteria, Zeping preserves execution state, and Baiqing implements the paired display. Independent reviewers provide measurements that automated tools cannot supply.

Implementation and dependency paths: evaluation/enhancement/protocol.py; evaluation/enhancement/runner.py; evaluation/enhancement/judge.py; evaluation/enhancement/analysis.py; evaluation/enhancement/review.py; evaluation/enhancement/memory_study.py.

## Current verification

T2 produced 100/180 valid hints (55.6%), compared with 110/180 (61.1%) for T1. The task-paired difference was -5.56 percentage points, with a 95% bootstrap interval from -13.33 to 2.22 points.

All 900 formal hint requests and 180 citation requests remain in their original schedules. The analysis resamples whole tasks to preserve the correlation between three hint turns. The corrected citation judge addresses the direct-answer measurement error on unchanged generated outputs. The 36-condition memory study separately records automatic state screens, 16 model judgments and 20 answer errors, preventing a successful-output subset from becoming an overall method score.

The current 110-question HTTP regression has 62 expected-state passes and 48 deviations. Ten additional fault IDs map to 14 isolated assertions. The final gate separately records 605 Python and 78 frontend passes. These are different scopes, and their overlapping checks are reported without treating the sum as independent scientific cases.

Two-reviewer forms and the timed highlight tool are prepared from the actual frozen outputs. Item identity, rubric, reviewer identity and completion fields are checked on import; original independent scores remain distinct from adjudication. The purpose-level usage ledger includes retained failed attempts and separates online generation/checking from offline assessment. The remaining research task is to collect independent judgments and compare their disagreements with the automatic conclusions.

| Matched record | Accounted | Planned |
| --- | --- | --- |
| Formal teaching comparison | 900 | 900 |
| Direct answers and attribution | 180 | 180 |
| Learning memory comparison | 36 | 36 |
| Existing live reliability catalogue | 110 | 110 |

Independent human ratings recorded for this checkpoint: 0. Prepared review materials are ready for the group's two reviewers.

## Failures and limits

The tasks are developer-authored, and a generator and judge from the same model family can share biases. Model scores are not human ratings. A faster interface or educational benefit requires actual participant measurements. Development tuning and later formal testing must retain their separate chronology and source versions.

Week 9 reporting should publish actual review completion and missingness, task-paired human results, agreement and separately attributed adjudication. Register any second-model or learning-effect extension before its first outcome, with the original formal records retained as a fixed comparison.

## Module operation

- Verify frozen task, source, policy and runtime hashes before starting or resuming a scheduled run.

- Reconcile every planned item with its output, retained failure or uncertain reservation, including the separately measured judge calls.

- Export blinded materials, collect two independent ratings, validate their import and retain disagreements before computing human agreement or comparing it with automatic scores.

## Week 9 actions

- Collect and validate the pending independent reviews, reporting missingness, disagreements and adjudication alongside automatic results.

- Analyze false acceptance, false rejection and task-type differences using paired estimates and the complete frozen denominators.

- Prepare any additional model or learning-effect study as a separately frozen protocol rather than tuning on the completed formal outputs.

## Accountability and evidence

These are accountable project domains from the original team allocation. The implementation and verification cited in the reports were performed through the shared project workflow. Domain ownership does not establish a personal commit, individual execution, independent review or personal authorship. Actual execution record: Codex performed the shared implementation, scripted execution and document preparation. Named members remain the accountable module owners. Independent reviewers have supplied 0 ratings.

Formal hint comparison. All 900 requests and task-paired model-assisted analysis; human ratings remain separate.

evidence/week08-enhancement/20260920/formal-hints-analysis.json

SHA256 3037903e73ce1046dc7e50236f2e628034b3d1e42d4ee28125ae4dc6c8ea9cd3

Corrected direct-answer citation analysis. Same 180 generated outcomes with corrected direct-answer judging; the original judge is retained.

evidence/week08-enhancement/20260920/formal-citations-judge-v2-analysis.json

SHA256 6aec13d0175ce4f7be47d2f78bf125e405fb82bda94cdf6ac12edb3e4f4c2dd5

Memory comparison and separate judging. All 36 authored conditions, state screens and 16 answer judgments; zero human ratings.

evidence/week08-enhancement/20260920/memory-study-final-summary.json

SHA256 77dc2d3080f413728f556d52d692db553d87ae782fad5c99ca0f87fd1ca8c582

Blinded independent review materials. Actual exports for two reviewers; prepared forms do not constitute collected ratings.

evidence/week08-enhancement/20260920/human-materials.json

SHA256 ea79b669d5585d551ef17453a6db6c7620a5c7e48421d1c9560de519e4e8f90c
