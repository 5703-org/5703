# Personalisation handover - 13 September 2026

Responsible workstream: **Pengyuan Xia - Personalisation**.

This is the code from the supplied 13 September member handover, organised for review on 16 September. The supplied package attributes the shared implementation to Codex; the role assignment identifies responsibility and review scope, not sole manual authorship or sole execution of experiments.

**Repository status:** an isolated review module, not an integration into this repository's baseline application. Existing application files and team branches are not changed by this handover.

## What changed from the previous handover

Only `personalisation/study.py` changed among the five supplied Python files. The profile compiler, rubric, package initializer and `tests/unit/test_profiles.py` are unchanged. In particular, the supplied unit-test file is not a set of newly written tests.

The study update:

- uses the shared `generation.token_counting.TokenCounter` instead of the previous token-count helper;
- validates model configuration and checks the full request plus reserved output against the model context window;
- rejects a provider-count configuration with strict error fallback, which would conflict with the single-rewrite policy;
- records tokenizer metadata, reserved token counts and the no-extra-provider-count policy;
- includes preparation time in the active-time budget and returns a structured `TOKENIZER_UNAVAILABLE` failure when preparation cannot proceed.

These changes are visible in the source. Their runtime behaviour depends on the matching shared `TokenCounter` and application configuration; that integration was not executed for this publication.

## Code walkthrough

| File | Responsibility |
| --- | --- |
| `personalisation/compiler.py` | Three learner levels, three styles, temporary request overrides and deterministic policy hashes. |
| `personalisation/study.py` | Fixed-base C0/C1/C2 comparison across three levels, with the updated token-budget preflight. |
| `personalisation/rubric.py` | Six presentation dimensions, correctness/groundedness gates and explicit missing ratings. |
| `tests/unit/test_profiles.py` | Existing full-module test specifications for the matching shared environment. |
| `verify_local.py` | A newly added, standard-library-only publication check; not part of the original member package. |

Missing legacy profiles have an explicit fallback; invalid explicit profile values are rejected by the shared model. A temporary request override does not mutate the saved profile. A request rule describes the intended presentation policy, not proof that a model obeys it or improves learning.

## Run the bounded local check

From this directory, use Python 3.11+:

```text
python verify_local.py
```

The helper checks the five source hashes and Python syntax, extracts the original dependency-free `turn_override()` function, and runs the original rubric functions. It checks four request mappings and four synthetic rating cases. It does not replace missing contracts with dummy implementations, run the complete compiler or study, contact a model, or use an application/database.

`verification/local_checks.json` is the actual publication-time output. Its timestamp identifies a new isolated check, not a reproduction of the project's historical experiments. Synthetic rubric scores are not human evaluation results.

The full test suite needs the matching shared application, including `contracts.models`, `generation.adapters`, `generation.parser`, `generation.prompt_builder`, `generation.types`, `generation.token_counting`, the teaching prompt template, and their dependencies (including Pydantic and pytest). After integrating with that environment, the supplied tests can be run with `python -m pytest tests/unit/test_profiles.py`. They cannot be treated as runnable against this baseline alone.

The owner record also refers to dedicated `tests/unit/test_teaching_token_budget.py` checks, but that file is not in this member package. Obtain those tests and the shared token counter before claiming the new preflight behaviour is verified.

## Supplied records versus verified results

The updated owner record **reports** a 13 September live study with 27 outputs (three topics x three levels x C0/C1/C2), plus three neutral base answers, for 30 model calls. It reports zero independent ratings. The underlying live JSON and full shared application are not included in this member package, so those live results were not independently reproduced or verified during this upload.

This is newer reported progress than the earlier mock-only record, but neither successful generation nor different answer lengths establishes scientific correctness, semantic preservation, teaching quality or learning gains. The old 8 September mock-run note is unchanged historical evidence, not a new experiment.

## Provenance and next steps

All seven files declared in the supplied ownership manifest were verified locally against their byte counts and SHA-256 hashes. Only the five Python source/test files are published here, unchanged. `SOURCE_MANIFEST.json` records their supplied hashes without the student identifier. This README, `verify_local.py`, `.gitignore` and the publication-time check result are added handover aids.

The original personal README/ownership metadata, student number, large owner ledger and raw/private records are not uploaded. The previous handover's verification helper is not included because it is absent from this new member package.

Next: reconcile the shared dependencies with the team, verify the updated study in the integrated environment, obtain the underlying live-study artefacts, and organise independent blinded ratings of clarity, level fit, correctness and semantic preservation.
