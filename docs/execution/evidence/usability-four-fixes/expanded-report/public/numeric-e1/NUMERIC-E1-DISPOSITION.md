# Numeric publication and E1 current-source disposition

Result: **no product patch justified by this targeted investigation**. Five current-source numeric service controls passed on the first isolated run. E1 received a separate read-only source review; its unchanged tests were not rerun. No Main file, database, API, model, native service, active selection, credential, query candidate or window candidate was changed.

The input is the expanded Main201 report already pinned by Root: 71,492 bytes, SHA-256 `19dfacec8e1cee0dfe6601c658af6a3105742039920a4ea9af90bfd0a06ad83b`. Its original observations and missing data are preserved. This note supplements the current-source assessment, rather than replacing the original report with inferred causes or a new full-system acceptance.

## Numeric controls and practical result

`verify_numeric_publication.py` compiles the complete current production bodies of `validate_item`, `publish_item`, `cas`, the item lookup/output functions, and the source-locator hash/range checks. It executes the actual pure rubric validator and numeric grader. It uses explicit authored in-memory repository lookup, lock/flush and released-membership seams; no database engine, session or HTTP server is created. A process audit fence rejects connections, child processes, credential files and writes outside this scratch directory. Main bytecode writes are disabled.

| Control | Actual result |
| --- | --- |
| Supported numeric key `2 mol`, authored source directly states `2 mol` | Validation returns `validated`, version 2, status `passed`, no issues. Publication using that returned version and explicit confirmation succeeds at version 3. The authored response `2 mol` grades correct. |
| Validate the same supported revision twice | Versions advance 1 to 2 to 3. Publishing with stale version 2 conflicts without mutation; publishing with the second returned version 3 succeeds at version 4. |
| Unsupported numeric key `2 mmol`, matching authored source | Draft schema accepts the string, but structural validation returns version 2, status `failed`, issue `missing_or_unsupported_numeric_key`, and state `draft`. Publication at the correctly returned version still conflicts and preserves the draft. |
| Skip validation or omit publisher confirmation | Publication conflicts without changing the row. |
| Alter the source hash or use a foreign workspace | Actual source/lookup checks reject validation and preserve the row. |

The command ran from `E:/5703/isolated/expanded-report-numeric-e1-20261019`:

```powershell
E:\5703\learning-assistant\.venv\Scripts\python.exe -B E:\5703\isolated\expanded-report-numeric-e1-20261019\verify_numeric_publication.py
```

The retained log reports five test methods PASS in 0.001 seconds. `NUMERIC-CONTROLS-RESULT.json` records source pins and the actual version/status observations. This is current service logic evidence, not a claim about PostgreSQL atomicity, concurrent writers, HTTP routing, live proposal quality or the tester's omitted item data. The source-membership seam is authored and is not presented as a newly verified production corpus.

## Numeric finding dispositions

- **DESIGN RETAINED:** Each validation attempt increments the item version, including failed validation. HTTP 200 means the validation operation returned a result; inspect `validation_details.status` and `issues`. `version=2` is not evidence of a passing rubric. Publication requires the current version, validated/passed state and explicit source/solvability confirmation.
- **VERIFY, counterexample obtained:** The alleged unavoidable numeric validate/publish version loop does not reproduce for a supported, valid authored numeric item. The supported `mol` path publishes successfully with the returned revision. No gate removal, version reset, timing workaround or publication retry is appropriate.
- **ACCEPTED authoring/UX limitation; DESIGN RETAINED unreviewed draft:** `NumericKey.unit` accepts a bounded string, while deterministic structural validation uses the finite `grading.UNITS` catalog. The proposal prompt does not enumerate that catalog. An unsupported draft can therefore exist successfully as an explicitly unpublished, unvalidated proposal. This is a producer guidance/validation explanation improvement candidate, not proof that valid supported items cannot publish. This task intentionally makes no producer/schema change or new unit conversion promise.
- **VERIFY:** Eight incorrect responses do not establish an incorrect grader. Exact private rubric keys, units, item revisions and submitted responses are needed to assess those outcomes; a single response cannot be assumed correct for eight distinct items. The one authored correct-response control here makes no aggregate accuracy claim.

To locate the old conflict precisely, the minimum remaining evidence is one approved/redacted item transaction: item kind and numeric rubric unit/value/tolerance, source locator, validation returned version plus full status/issues, publication `expected_version` and confirmation flag, and whether another validation or writer intervened. No new private-data query or old request replay is authorized by this note.

## E1 and experiment model selection

**DESIGN RETAINED:** `experiment/bridge.py:113-168` uses an explicit managed configuration when one is selected. Otherwise its documented legacy path keeps the environment-selected experiment model. Activating a chat model does not silently change an evaluation condition. The authored `test_managed_evaluation.py:219-225` explicitly checks that chat activation leaves an unconfigured experiment mock and an explicitly configured experiment on its frozen earlier model. Chat's active workspace model is resolved separately by `answering/service.py`.

**DESIGN RETAINED:** E0 performs no retrieval. E1 is the frozen basic R0 dense-retrieval condition. `benchmark_query_runtime_v1` can freeze an explicit CPU/device declaration and its configuration identity; a missing declaration retains recorded historical behavior. `retrieval/runtime.py` modifies only a copied execution device view. It does not replace corpus identity or retry an unavailable device silently. Existing unit/integration test source covers E1 CPU/R0 with unchanged corpus/vectors, E0 zero retrieval, legacy behavior and policy tamper rejection. Those source files match the assessment pins. No unchanged E1 rerun was needed for this numeric investigation.

**ACCEPTED observation/diagnostic concern; NEEDS VERIFY cause:** Preserve the report's E1 `AssertionError` as a failure with cause **UNKNOWN**. A stack-safe exact assertion, frozen experiment configuration and declared device/resource identity are absent. Do not infer CUDA failure, automatically select CPU, turn E0 into retrieval, expose evaluator gold to runtime, or substitute the active chat model. The dated 2026-10-02 native CPU evidence belongs to an older 858-source installation; it does not reproduce the report's assertion or establish new current acceptance.

No E1 patch is justified. A later exact-cause investigation needs a separately scoped authored reproduction bound to the failing configuration/device. A fresh pure runtime-policy unit run, if separately requested, could verify that contract but would not establish the old assertion's cause.

## Integration handoff

Root may integrate this note and the pinned isolated evidence into the final package. There is no product diff from this lane. Keep the numeric publication and source/CAS/confirmation boundaries intact, label the fixture seams and E1 historical limits, and preserve the original report. The manifest binds the input, current reviewed source, script, log and result. This investigation adds no paid call or physical ledger entry.
