# Week 09 personalisation - source-preserving review package

This folder packages the personalisation code supplied in the 6 October 2026 member handover. It is **not the complete application** and has two reproduced local safety-expectation failures. It is for review, not a claim of deployment readiness.

## Source and attribution

- All 14 original Python files are byte-identical to the supplied manifest. `SOURCE_MANIFEST.json` records their hashes and comparison with the Week 08 review snapshot.
- The manifest's `source_snapshot_sha256` identifies an upstream source snapshot; it is **not a Git commit**.
- The supplied ownership record assigns a workstream, not proof of individual execution. The project report attributes implementation and validation to a shared Codex workflow.
- Reports, student details, private fixtures and account material are excluded. This wrapper, audit runner and results are newly prepared delivery material, separate from the original implementation.
- `memory.py` and `memory_extraction.py` are unchanged from the Week 08 review package. `memory_v2.py` has limited wording/topic changes. The other 11 files were absent from that small prior review snapshot; absence does not establish their creation date.

## What the code does

| Area | Files | Scope |
| --- | --- | --- |
| Profile and policy setup | `compiler.py`, `memory_policy.py`, `__init__.py` | Compile presentation settings and temporary overrides; validate and select a versioned memory policy. |
| Retained foundations | `memory.py`, `memory_extraction.py`, `memory_v2.py` | Earlier extraction adapters, typed operations, priorities and budgets; V2 now recognises `briefly` and `concisely`. |
| Question-conditioned selection | `memory_v3.py` | Rules for topic/follow-up matching. Optional pinned local E5 support needs explicit calibration/configuration and is off by default. |
| Source-backed preference conditions | `memory_v4.py`, `memory_v5.py` | Validate supplied owned-source records, quotes, revisions and preference expiry. V5 adds supported leading-topic statements such as `For biology, I prefer examples.` |
| Operation proposals | `memory_writer_v4.py`, `memory_writer_v5.py` | Prepare candidate operations and withheld reasons. They do not persist, edit or delete database records. |
| Study/review support | `study.py`, `rubric.py`, `tests/unit/test_profiles.py` | Controlled-study support and rating/profile tests; missing ratings are not treated as passes. |

V3/V4/V5 are selectable versions, not three mandatory sequential stages. V4/V5 reuse V3's rule/context assembly without running the optional semantic encoder. Their `enabled=False` policy value must not be described as disabling all learning memory. A withheld result does not establish a working confirmation UI.

## Reproduced local results

See `verification/local_checks.json` for individual results, source hashes and runtime timestamp.

- **14/14** original Python files passed syntax compilation.
- **58/60** explicitly scoped local checks passed; **2 failed expectations** remain visible below.
- Six supplementary observations are recorded separately, not counted as passes.
- The four-test supplied pytest file was **not collected/run as a suite**. One original rubric test function was executed via AST and is already included in the 60 checks.
- The selected runtime lacked pytest. The complete contracts, generation, retrieval, storage and application dependencies were not in this member package.

The audit imports delivered memory modules under an isolated namespace, bypassing `personalisation/__init__.py`. For the compiler it executes an AST subset only for `turn_override` and `compile_profile(use_profile=False)`, omitting the unavailable contracts import. No replacement `Profile`, model adapter, storage or retrieval implementation is introduced.

Selection fixtures use authored dictionaries and a synthetic character counter. They test rule branches, **not real account ownership, a production tokenizer or context-window accuracy**. The original byte-count fallback is also observed separately.

### Known local failures - source preserved, no patch applied

1. **Conditional preference broadened:** `I prefer detailed explanations if I am tired.` is treated as a global preference by the V5 condition parser and writer. The expectation that this unsupported condition should be withheld fails.
2. **Deletion proposal not bound to deletion intent:** a synthetic `DELETE` candidate can pass V5 preparation when the source says only `I prefer examples for biology.` No extraction model or actual database deletion was executed. The test demonstrates a proposal-validation gap, not an observed end-to-end deletion.

Additional integration questions: a raw V3 profile dictionary with `use_profile=False` can retain defaults, although the tested compiler-off path emits `profile=null`; V5's new expiry guard is preference-specific; and the byte fallback retained no preference in the single synthetic preference case. Inspect the six observations before generalising. Host call contracts or storage filters could change application-level behaviour.

## Re-run the bounded audit

From this folder, with Python 3.10 or newer:

```sh
python verify_local.py --source-root . --output verification/local_checks.json
```

This is an **audit-report generator**: a successful process exit means a report was written, not that every assertion passed. Read `passed`, `total` and `checks[].passed` in the JSON. It makes no model/API calls and uses temporary local policy fixtures. Re-running updates the result timestamp/environment.

## Not established by this package

No full package integration, live model/embedding run, database persistence, account isolation, front-end confirmation, end-to-end teaching study or human learning benefit was verified here. The enabled-profile schema path and the other three original test functions remain unexecuted. Large shared-system counts in the supplied report were not rerun and are not claimed as this audit's results.

## Demonstration and next work

1. Open `memory_v5.py` (`condition`, `select`): explain original source, topic, expiry and revision checks.
2. Open `memory_writer_v5.py` (`prepare_operations`): distinguish a proposal from a database update.
3. Open `verification/local_checks.json`: show supported cases, the `briefly` regression pass and both unresolved failures.
4. Next: bind deletion proposals to explicit intent, withhold unsupported conditions, add regression cases, then integrate with the real storage/permission layer and evaluate matched explanations. Keep independent human ratings and learning outcomes unclaimed until measured.
