# Week 10 personalisation review package

This folder is the Week 10 owner review package for Pengyuan Xia's personalisation workstream. It preserves the frozen personalisation source and adds the four dated offline model-route evidence records from 10 October 2026.

## What changed this week

There is **no post-baseline change to the personalisation implementation or its assigned profile tests**. The Week 9 personalisation code is carried forward as a frozen foundation. The new material is evidence for opt-in Gemini reasoning profiles:

- `evidence/high-profile-frozen-review.json`
- `evidence/high-profile-offline-controls.json`
- `evidence/medium-profile-frozen-review.json`
- `evidence/medium-profile-offline-controls.json`

The records are offline control receipts. They validate route/payload encoding, preservation of the old low route, and rejection of fixed-policy or wrong-provider/model overrides. They record zero API requests, database access, credential access, main-branch writes and controller starts. They do not prove model answer quality or learning improvement, and they do not enable a new production default.

Local workstation paths in the supplied receipts were redacted to portable placeholders before upload; no credentials or private runtime files are included.

## Inherited personalisation foundation

The carried-forward code contains profile compilation, current-turn overrides, versioned memory selection, source ownership and revision checks, bounded context selection, memory operation proposals, study support and rating validation. The code is included for a complete review path; it should not be described as newly implemented in Week 10.

`memory_writer_v5.py` prepares candidate operations but does not itself persist them. `memory_v5.py` selects supplied memory records and validates their source. A backend storage/API remains an integration boundary outside this owner folder.

## Evidence boundary

The package depends on the complete project's shared runtime, contracts, model/tokenizer assets and four-book corpus. It is not an independently runnable application. The source report attributes shared implementation and review activity to the Codex workflow; owner assignment is reporting metadata, not proof of personal execution.

The release report records a final isolated unit run of 4,803 tests and 215 subtests, 28 skips and 40 warnings, plus 241 frontend tests and a scoped native-browser check. These are release-level results from the complete project, not a new personalisation-only Week 10 run. Clean dependency installation, full PostgreSQL/corpus launcher, live scientific/citation quality, formal warm-p95 and independent human learning ratings remain open.

## Suggested demonstration

1. Open `personalisation/compiler.py` to show that learner self-reports are mapped explicitly and current requests can override presentation for one turn.
2. Open `personalisation/memory_v5.py` to show source-backed memory selection and bounded conditions.
3. Open the four `evidence/*.json` files to explain the new Week 10 offline route controls.
4. Explain that the next step is a fresh two-session lifecycle with correction, pause/resume, TTL expiry, deletion, undo, revocation and stale-worker checks, followed by matched independent evaluation.
