# Week 08 Personalisation: isolated review package

This directory is a source-preserving review handover, **not an application integrated into `main`**. It adds no backend routes, database migrations, storage implementation, or deployed UI. The five original Python source files were copied byte-for-byte from the delivered Week 08 member bundle; no fixes were applied to those files. `SOURCE_MANIFEST.json` records their relative paths, byte sizes, and SHA-256 hashes.

## What the source implements

| File | Implemented scope |
| --- | --- |
| `generation/joint_policy.py` | Versioned T0-T4 teaching-policy flags; claim/citation spans; evidence-display projections and hashes; an untrusted-memory prompt segment and exact-segment metadata redaction. Policy flags are not a complete online checker, and lexical fragment selection is not proof of factual support. |
| `generation/teaching.py` | Rules for level/style presentation and recognized English current-turn requests, including hints and misconception checks. It constructs a plan, not a model answer or an assessment of learner mastery. |
| `personalisation/memory.py` | The v1 durable preference/goal extraction path, including source attribution, output shape checks, and finite-call budget logic. |
| `personalisation/memory_extraction.py` | Typed v2 extraction of proposed ADD/UPDATE/DELETE/NO_OP operations, with source validation and finite retry logic. Returning an operation is not applying it to a database. |
| `personalisation/memory_v2.py` | Typed fields, deterministic operation proposals, explicit-source validation, topic-alias selection, precedence/conflict rules, and bounded learner-state preparation. |

## Dependencies and integration boundary

The member bundle does **not** include `generation.adapters`, `generation.types`, or `generation.token_counting`. The two extraction modules cannot be exercised as a complete application from this directory alone. Their `api_key` parameters are interfaces, not supplied credentials.

Memory-state persistence, database schema/migrations, backend API wiring, account isolation, read-time expiry/revocation enforcement, and the application's integration tests are not included. Their absence is not a passing test result. A host application must provide and verify these dependencies before using the code with real learner data. This package has not demonstrated durable memory writes, deletion, model extraction, end-to-end profile-off behaviour, or production privacy guarantees.

Any shared-system tests, model outputs, or research results described in the accompanying project reports remain **reported results, not results rerun or independently verified by this package**. The narrow checks below are not replacements for those experiments, human reviews, or the team's full test suite.

## Reproduce the narrow local checks

From this directory, with Python 3.12 or a compatible standard-library environment:

```text
python verify_local.py --source-root . --output verification/local_checks.json
```

The `verification` directory is included. Both command arguments accept relative paths. The runner reads the five source files and writes only the requested result JSON. It does not call a model, access a database, make network requests, or import missing shared application modules. It directly loads the three standard-library-only modules; for the v1 extractor, it loads only the original `eligible` function and its two regex constants through AST selection. Syntax compilation of all five files is separate from executing their functions.

Selection/conflict checks inject `SyntheticCharacterCounter`, which returns `ceil(character_count / 4)`, solely to exercise deterministic branches without discarding every test entry. This is a **synthetic test double, not a real tokenizer or model context-window validation**. No fake shared module or storage layer is provided. Two separate observations execute the original default UTF-8-byte fallback without a counter. All learner entries and passages in the runner are synthetic.

### Recorded result

- Five source syntax checks passed: **5/5**.
- Narrow behaviour checks: **25/26 passed; one failed assertion remains**.
- Seven additional observations, including two budget-baseline observations, are preserved in `verification/local_checks.json`.
- These are bounded local function checks, not application integration, live generation, actual tokenizer verification, pedagogical evaluation, or proof of learning gains.

The runner deliberately records assertion failures and finishes writing the audit report. Its process exit status alone does not mean all checks passed: inspect `passed`, `total`, every item in `checks`, and `risk_observations` in the JSON.

## Known limits and reproduced observations

No issue below was fixed in the original source. Some package-level behaviours could be constrained by a host application's absent validation layer; that layer was not assumed or simulated.

1. **Saved style remains active in the teaching plan when profile use is off.** With `use_profile=False` and saved `style=detailed`, the plan returns `level=null` but `style=detailed`. See `generation/teaching.py:26-31`; JSON observation `profile_off_still_uses_saved_style`.
2. **The operation validator accepts DELETE without an explicit erasure request.** A proposed DELETE with the exact source quote `I prefer examples for biology.` passes the current validator. The operation value and attributable durable source are checked, but their action semantics are not matched. No actual deletion or database write was run. Downstream enforcement is unknown. See `personalisation/memory_v2.py:379-420`; `validator_accepts_delete_without_erasure_request`.
3. **The selector does not itself exclude expired entries.** A synthetic entry with an old `expires_at` can be selected when supplied directly. A host read layer may filter such entries, but that layer is absent and untested. Revocation enforcement is likewise not demonstrated. See `personalisation/memory_v2.py:459-511`; `selector_does_not_itself_filter_expired_entries`.
4. **Learner-state preparation also uses saved profile defaults despite `use_profile=False`.** The supplied saved level/style are still included, and a saved style can suppress global detail memory. See `personalisation/memory_v2.py:458,485-486,561-563`; `selector_uses_profile_defaults_when_use_profile_false`.
5. **Current-turn wording coverage differs between teaching and memory selection.** Teaching recognizes `briefly` as concise, while the typed-memory field recognizer does not. The check expecting `This time explain biology briefly` to override a relevant saved detail field fails. The corresponding recognized `brief` case passes. This is the one failed assertion, also recorded as `briefly_mismatch_between_teaching_and_memory_selection`. See `generation/teaching.py:35-36` and `personalisation/memory_v2.py:283-286`. No final model-answer behaviour was tested.
6. **Default byte-budget empty-context baseline.** With no entries, the original fallback returns no entries and a reported count of 501 against a 768 limit in the synthetic case (`default_byte_budget_empty`). This is a baseline observation, not an additional failed assertion.
7. **Default byte-budget trimming can remove the only ordinary entry.** With one synthetic preference, the default fallback removes that entry and returns a reported count of 501 (`default_byte_budget_one_entry`). The source reserves 96 units from the 768 limit. This demonstrates conservative byte-fallback trimming in this case, not a result for the real configured tokenizer. See `personalisation/memory_v2.py:572-598`.

Additional review boundaries: topic and request matching use finite English regex/alias rules, not semantic understanding or demonstrated mastery. `sanitized_messages` redacts an exactly matching constructed memory segment, not arbitrary logs or all copies of learner content. The source code alone does not guarantee prompt-injection resistance, factual accuracy, or privacy of a complete system.

## Package contents

The five original source files are accompanied by this README, `SOURCE_MANIFEST.json`, `.gitignore`, the portable `verify_local.py` audit runner, and its `verification/local_checks.json` output. Personal reports, meeting notes, student identifiers, emails, credentials, and live learner datasets are not included in this review package.
