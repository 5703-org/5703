# Local reader mock compatibility repair — 4 October 2026

The source now contains a narrow successor to the recorded current883 checkpoint. No release number, installed runtime, saved request, historical gate, model setting or protected staging tree was changed. Current880 remains the retained delivery baseline. This patch is not an installed or full-project acceptance claim.

## Defect and change

The retained current883 diagnostic recorded `What is photosynthesis?` as a refused mock request with `question_requirements_v7`. Its retrieval query appended `Textbook section: Chapter 8 Photosynthesis / 8.1 Overview of Photosynthesis`, while its frozen understanding retained the clean science question. `generation/adapters.py` accepted this separation only for V4. The narrow change accepts the existing V4–V7 producers when their reader-resolution record is present. It does not relax lexical support, numeric/negation conditions, source provenance, citations or semantic publication gates.

Changed executable: `generation/adapters.py`. Added regressions: `tests/unit/test_reader_mock_requirements.py` (20 controls) and `tests/integration/test_reader_mock_current_runtime.py` (two API/worker/SQL cases). The native definitions now persist an answered mock response with citations under the current V21/V7 producer in a disposable database. These authored sources and deterministic mock outputs are software evidence, not measured learning or model quality.

## Fresh verification

| Check | Actual result |
| --- | --- |
| Pre-fix reproduction on the enhanced current generation path | 6 failed, 14 passed; V5–V7 definitions were incorrectly refused |
| Related unit regression after the patch | 342 passed in 3.06 seconds, including 20 new controls |
| PostgreSQL integration, reading, V21, practice assessment and pending tutor paths | 54 passed in 52.15 seconds, including two new current-reader cases; two dependency deprecation warnings |
| Owned Ruff correctness/format checks | Passed for the adapter and unit regression |
| Isolated foundation verification | 108 tasks, 60 checks, 27 schemas; design consistency only |
| Isolated runtime contract comparison | 124 API paths, 228 schemas passed |
| Isolated chat boundary verification | 225 runtime Python files passed; no evaluator dependency/private data mount |

The initial standalone legacy-path reproduction is retained separately (8 failed/12 passed); it did not represent the enhanced current path. The corrected reproduction is the six-failure result above. A first direct contract invocation reached its output write and failed on permission for `evidence/contracts/verification.json`; that historical file was not overwritten. The existing foundation/contracts/chat verifiers were then run against a small independent snapshot with only their `ROOT` redirected; all outputs were written in the task workspace.

The integration runner created one labelled, randomly named PostgreSQL/pgvector container on a random localhost port, used the existing disposable-database fixture, and removed only its verified owned container. Existing Main/CPU databases and protected staging trees were not used. No provider run or source installation occurred.

Reproduction commands and logs are retained at `C:\Users\PC\Documents\Codex\2026-10-04\task`: `5703-reader-current-path-before.log`, `5703-repair-tests.log`, `5703-postgres-tests.log`, `5703-postgres-junit.xml`, `5703-postgres-receipt.json`, `5703-verifiers.log`, `verify_5703_isolated.py`, and `run_5703_postgres.py`. The unit command names the new test plus `test_mock_evidence_coverage`, `test_answer_core_v5`, `test_practice_model_assessment`, `test_pending_tutor_question`, requirements V4/V5/V7, teaching V8 and enhanced generation tests. All pytest runs disabled cache and bytecode output; temporary data remained in the task workspace.

## Remaining acceptance

The original selected explanation still asks for unsupported lexical variants/presentation content. This patch does not claim to fix it or to establish semantic quality. Current installed eight-module journeys, real grading/teaching, independent quality labels, formal seven-family studies, physical-device/new-host observations and successor report/archive acceptance remain open. The full 3,269-case/196-frontend current883 record is historical and was not rerun for this successor. Installing into the two protected staging directories requires a separately agreed action; this task explicitly protected them.
