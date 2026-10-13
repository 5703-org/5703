# Checker119: offline controller and requirement contract

The small controller now has one offline execution path through the actual GenerationService and LLMAdapter: serialization, local transport, framed raw response persistence, durable simulated settlement, native parser, all publication gates, score calculation, per-unit receipts and terminal closure. Eight intended units completed; all five saved real replies from114/116/118 were replayed through the same entry point. This checkpoint made zero real provider requests, credential reads or DB operations. Paid batches remain paused; project completion, RAG quality and native complete-answer latency remain unverified.

## Diagnosis and change

118's missing public config was a harness defect. The earlier fake shortcut did not exercise native parsing and scoring, so its passing result did not cover that failure. The new runner rejects absent/mismatched config before claim/transport, uses a fixed4096/T0/nonthinking/json_object profile, validates source/label structure and safe unit IDs, confines output paths, fences socket and DNS entry points, and records construction failures plus every remaining NOT_RUN slot. Nested escaped dummy-key echoes are withheld before raw persistence; settlement requires complete framing, valid bounded usage and a durable receipt before releasing simulated UNKNOWN. There is no paid/key-loading execution entry or retry.

The old checker interface also asked the model to emit three redundant summaries as independent judgments. In118, per-requirement sufficient/covered/empty gaps contradicted aggregate partial/incomplete/nonempty facets that actually described selected-citation proof defects. The opt-in wire now asks only independent requirement source decisions, a separate explicit answer-omission string, and existing claim/context/teaching decisions. The server derives coverage, missing_facets and complete_answer without prose interpretation or missing-point invention. Ambiguous decisions remain invalid/unknown; absence/null/whitespace is not empty. Returning obsolete aggregate fields in the new version is rejected. Existing source, unit, context, citation, teaching and V5 publication gates remain active. Default A's prompt and serialized packets remain unchanged. A dedicated opt-in base prompt removes the obsolete aggregate example rather than appending contradictory instructions.

Model output remains a limitation: deriving summaries removes redundant interface contradictions but does not certify source sufficiency, citation entailment or scientific truth. Actual old inconsistent replies remain invalid; old paid failures and raw/billing/controller records are immutable. A current local compatibility result never replaces an original live verdict.

## Verification

243 relevant unit/integration tests passed in3.87s; Ruff passed. Controls cover both directions of gap/status and delivery/omission invariants, positive-to-negative and negative-to-positive summary tampering, unknown/empty/malformed cases, missing typed limitations, eight full native-path units, semantic failures continuing mates, technical failures stopping without retry, seven NOT_RUN receipts, request construction failures, fixed bounds, all resolver fences, nested/bare Unicode secret echoes and decoding limits. Authored fixtures supplied full typed model responses, never a scorer's authored_accept bypass.

The exact fixed eight units completed with one authored false accept and two authored false rejects, demonstrating score branches and mate continuation. These are authored plumbing controls, not model-quality estimates. The same runner CLI also completed all eight. All thirteen primary offline executions retained original raw bytes and used native parsing/gates. Simulated costs are test accounting inputs, not new real spend or releases of old financial holds.

| Saved reply | Current offline full-check result | Preserved issue |
|---|---|---|
|114 S01 A|valid, reject|none|
|114 S01 B|invalid/unknown|LEGACY_RESPONSE_GAP_UNASSESSED|
|114 S02 B|valid, reject|existing compatibility normalization only; original live failure unchanged|
|116 S02 B|invalid/unknown|REQUIREMENT_GAP_UNSPECIFIED|
|118 S02 B|invalid/unknown|MISSING_FACETS_WITH_NO_REQUIREMENT_GAP|

Legacy incomplete delivery lacks the new independent omission field; it stays unknown rather than guessing an omission from prose. No historical source/claim/unit statuses were rewritten. The replay receipt includes original and current wire hashes to distinguish old real inputs from the new local contract.

## Reproduction and exact evidence

Run from E:\5703\learning-assistant using the existing .venv Python, with a fresh output path (exclusive creation; never reopen a stopped claim):

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m scripts.dev.checker_fixture_runner --plan C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-runner119-offline\prepared119.json --responses C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-runner119-offline\response-paths119.json --output C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-runner119-offline\new-exclusive-output
```

Relevant executable: scripts/dev/checker_fixture_runner.py. Evidence root: C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-runner119-offline. Exact file sizes/SHA256 are in source-evidence119-closed.json; closed-evidence/end-to-end119.json contains the eight/five assertions and original response/wire hashes; each closed-evidence run has claim/intent/raw/settlement/result/terminal receipts. pytest-closed119.txt, ruff-closed119.txt and exercise-closed119.txt retain actual command output. Original preimages are retained separately; no new ZIP or duplicate Main status bundle was produced.

The original118 raw hash remains63a888ce4c8a5476892ba01a407f223631f174ff58e52786fe9962626a184447; original118 terminal hash remainsbe37ca40421ed3aaf426d886a66ef4d96d20e37fb116d9ad826669309d1183d8. Historical Main reports and named runtime118 originals were checked against their previous manifest pins. Git status remains unavailable because repository ownership was rejected; no safe.directory exception or security bypass was applied.

## Remaining work

Independent source/controller review and documentary readback receipts are separate from measured test results. A fresh provider batch must use regenerated B packets under the new wire contract; all old paid prepared B packets are stale. No automatic118 continuation, price refresh, key read, generation/repair call or new batch was admitted here. Actual matched-condition model quality and send-to-complete native page latency require later real acceptance work. Protected staging databases, experiments, old holds and deliveries remain intact. This report does not close the whole project.
