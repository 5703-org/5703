# Week 06 Personalisation module — review copy

Role owner: Pengyuan Xia. This directory publishes the code in the supplied Week 06 role-delivery package for review. Ownership identifies the responsible workstream; it does not imply that every line or shared-system experiment was independently authored or executed by the role owner.

**Status: isolated module handoff, not integrated into this repository's baseline application.** The shared application expected by these files is not included here. This upload does not change the baseline RAG pipeline.

## Suggested code walkthrough

| File | What to inspect |
| --- | --- |
| `personalisation/compiler.py` | Beginner / Intermediate / Advanced presentation policies; concise, detailed and Socratic styles; temporary request overrides; deterministic policy hashes. |
| `personalisation/study.py` | Controlled C0 / C1 / C2 comparison across three levels, keeping the base answer and evidence fixed. |
| `personalisation/rubric.py` | Six presentation dimensions and separate correctness / groundedness gates. Missing ratings remain `None`, not zero or a pass. |
| `tests/unit/test_profiles.py` | Tests specifying expected profile, override, comparison and rubric behaviour. |
| `scripts/verify/profile_lengths.py` | Shared-system verification of saved profiles, request snapshots, evidence and mock-answer request handling. |

The compiler records a fallback for a missing legacy profile. Explicitly invalid profile values are rejected by the shared validation model; they are not all silently replaced with Intermediate. A temporary request override does not edit the saved profile. Turning the saved profile off can still allow an explicit request such as “make that shorter”. Presentation adaptation must preserve evidence constraints.

## Running and integration prerequisites

Python 3.11+ is needed by the verification helper (`hashlib.file_digest`). The module also relies on shared components absent from this baseline repository, including:

- `contracts.models`, including the validated profile and evidence contracts;
- `generation.adapters`, `generation.parser`, `generation.prompt_builder`, and `generation.types`;
- `conversation.summary`, shared prompt templates such as `teaching_v1.txt`, and `app.core.config.Settings`.

The corresponding shared environment needs Pydantic v2 and pytest. The verification helper additionally requires httpx, SQLAlchemy, the configured database driver, a running application API and worker, PostgreSQL, the matching v5 / E5 corpus publication and readable original PDF storage.

Do not run these files as if they were a complete standalone application. To integrate, first agree the contracts and module locations with the team, copy/reconcile the files into the matching shared application's package structure, then run its tests. Do not create dummy contracts merely to make a test appear to pass. The baseline repository's dependency files have deliberately not been changed.

After integration into that matching shared application, the intended unit-test entry point is:

```text
python -m pytest tests/unit/test_profiles.py
```

The verification helper must use an authorised disposable test environment, with `CS30_ADMIN_EMAIL` and `CS30_ADMIN_PASSWORD` supplied through environment variables. It requires an explicitly **mock** answer service. Its command-line options include `--output-dir`, `--api` and `--publication`.

**The helper has side effects:** it creates a test account, changes that account's profile, creates three conversations and submits twelve requests (three setup plus nine target requests). Read-only SQL checks do not make the entire helper read-only. Do not point it at production or a shared environment without the responsible owner's agreement.

Under this review directory, the helper's calculated `ROOT` is this prototype folder, not the Git repository root. Its default corpus-publication path is therefore not usable here. Integrate it first, or explicitly supply the publication path and configure the matching shared module search path. Generated results may contain account, session and request identifiers, answer/evidence text and absolute source-file paths; keep them out of public version control.

## Verification and evidence boundary

This publication is a source handoff, not a claim that the full application or pytest suite has run successfully in this baseline repository. The included tests describe executable checks for the matching shared environment.

The supplied Week 06 execution note describes twelve requests using mock answers. That historical record is not a fresh run performed for this upload, and its raw run artefacts are not included here. Request/persistence checks do **not** establish answer-length fidelity, semantic simplification, level fit, real-model quality or learning gains. Real-provider comparison and independent human ratings remain separate work.

## Publication changes and exclusions

- Five module/test files retain their supplied source content (line endings may be normalised by Git).
- The verification helper's hard-coded default administrator login fallbacks were removed. Both environment variables are now required, checked before output directories are created or API/database work begins. No credentials are included.
- This README and a local `.gitignore` were added for safe review and handoff.
- Personal reports, student identifiers, email/contact details, meeting notes, ownership logs, raw execution records, generated evidence and the original ZIP are intentionally not published.

Next step: reconcile the shared contracts with the team, integrate on an agreed branch, then reproduce software checks and collect separately labelled real-model and human-review evidence.
