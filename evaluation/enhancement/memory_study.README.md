# Memory comparison

`memory_study.py` freezes 12 authored state-transition sequences and runs every sequence under three conditions (36 planned answer samples):

| Condition | Persisted context | Updates and controls |
| --- | --- | --- |
| `profile_session` | Fixed profile, zero earlier messages | No memory extraction or summary call |
| `rolling_summary` | A real model-updated summary | At most two calls/90 active seconds per update; explicit delete/expiry clear the summary; off suppresses updates/context |
| `structured_memory` | Actual production memory entries and frozen snapshots in a disposable database | Production extraction worker, canonical merge, CAS correction/expiry, off, deletion, erased derivatives and stale-job cancellation |

Each condition receives identical statements and the same frozen real textbook question/evidence (`W8E-D01` or `W8E-D12`) from `development-source-v3`. Answers use the product's checked direct explanation flow and a four-call/180-second budget, with the explicit 4,096-token checker output reservation. Current-turn wording overrides are identical across conditions. Conditions rotate first position equally across the 12 cases. Runs are sequential; timings describe this study's observed execution, with any concurrent workload recorded separately.

Cases cover enduring preferences, explicit goals, correction, a current-turn override, subject relevance, explicit expiry, global memory off, profile off, deletion with stale work, temporary preference/difficulty and saved-setting precedence. The expiry case uses an explicit user edit to a fixed past timestamp; it exercises actual expiry filtering without waiting or changing the clock. The summary control behavior is an explicit comparator policy. The product's existing extractive session summarizer remains unchanged.

Automatic checks inspect actual state/control results and literal retention flags. A flag can include a valid paraphrase or a negated old preference; those flags remain separate from the blank answer-support, memory-use and current-instruction ratings. A missing remembered preference is an expected limitation of the fixed-profile baseline. Completed execution and a passing semantic judgment have separate fields. No independent ratings are prefilled.

## Prepare and execute

Use the project virtual environment, `PYTHONPATH=backend;.` and `PYTHONDONTWRITEBYTECODE=1`. Freeze after the reviewed helper and its production dependencies are stable:

```powershell
.venv/Scripts/python.exe -m evaluation.enhancement.memory_study freeze --source evaluation/private_runs/week08-enhancement/development-source-v3 --plan evaluation/private_runs/week08-enhancement/memory-v1/plan.json
```

Execution requires an **already migrated empty PostgreSQL database** whose name begins `cs30_memory_study_`. An operator supplies its connection string through `MEMORY_STUDY_DATABASE_URL`; the helper neither creates nor drops a database. The first run rejects nonempty user tables, the main database and concurrent execution. The main model configuration is read-only; its resolved credential stays in process memory. The disposable worker records an explicit configuration alias linked to the original immutable public model configuration. No credential table or deployment key is copied.

After the coordinated live-run approval:

```powershell
.venv/Scripts/python.exe -m evaluation.enhancement.memory_study run --source evaluation/private_runs/week08-enhancement/development-source-v3 --plan evaluation/private_runs/week08-enhancement/memory-v1/plan.json --output evaluation/private_runs/week08-enhancement/memory-v1/run1 --summary evidence/week08-enhancement/20260920/memory-comparison-attempt1.json --allow-live
```

Keep the plan, authored conversations, model responses, updates and event logs in the private study directory. The summary exports counts, statuses, checks and hashes. Each case-condition is reserved before any model call. Existing completed results are read, and interrupted reservations remain blocked for explicit reconciliation; the helper never replays uncertain calls automatically. Source hashes cover generation prompts/schemas/providers, exact-source mapping, personalisation and conversation dependencies; they are checked before and after every condition. Any change stops further calls and retains the affected outcome. Repeated summaries require a new path. Event logs and structured production attempts recover call reservations and known token usage even after an exception; incomplete records are explicitly uncertain. Reserved calls can fail before transport, and provider billing remains unknown. All 36 planned rows remain in every summary, including errors, interrupted reservations and pending work.

Unit tests use scripted transports to verify harness controls and denominators. Actual memory extraction and answer behavior require the authorized live run. Independent review and longitudinal learning outcomes remain separate measurements.

## Separate output-use review

After all 36 outcomes are retained, `memory_review.py prepare --run RUN --plan PLAN --output NEW_PRIVATE_DIRECTORY` creates the versioned rubric, two separately ordered HTML/JSON review sets, blank CSV ratings and a coordinator-only condition key. Conditions, expected state flags and online checks are absent from reviewer inputs. Context shape can still suggest a method; this practical blinding limit is recorded. The strict importer preserves all scheduled IDs, both independent reviewer identities and original submissions; incomplete or fabricated placeholder ratings are rejected.

`memory_review.py judge --materials PRIVATE_DIRECTORY --report NEW_PUBLIC_SUMMARY --allow-live` performs separate model judging only after its prompt/rubric, inputs, source hashes and configuration are frozen. Each available answer gets at most two calls/90 active seconds, with purpose `memory_use_judge`, durable reservations and actual usage. Missing/error/refused answers stay in the denominator and receive no semantic grade. The managed generator model must remain unchanged. Public output contains scores, statuses, counts and hashes; quoted reasons remain private. The same provider/model family judges the outputs, so agreement can be correlated. Independent human ratings remain blank until actual reviewers submit them.
