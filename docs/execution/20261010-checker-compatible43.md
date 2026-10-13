# Full-input checker compatibility43 checkpoint

Both original-input checker repeats completed successfully and are settled: **two requests, $0.0310396 known cost, zero new UNKNOWN holds, and no open claims**. The complete original schema and reference checks pass for both raw responses. Independent selected-source inspection still finds partial units in both, so **source completeness and project completion remain unproven**.

| Repeat | Checker component duration | Known cost | Independent complete / partial / unsupported units | All-unit-complete / partial claims |
|---|---:|---:|---:|---:|
| 43_01 | 7768.5613 ms | $0.0138473 | 14 / 5 / 0 | 6 / 4 |
| 43_02 | 10560.6593 ms | $0.0171923 | 15 / 4 / 0 | 7 / 3 |

Durations are measured from `LLMAdapter.generate` invocation to complete return. They are **not browser Send-to-complete-answer TFull**, first-token latency, or a p95 estimate. Both requests returned HTTP 200 with `finish_reason=stop` on `google/gemini-3.5-flash-lite`. The outgoing route requested only `google-vertex/global` and disabled fallbacks; the provider envelope alone does not establish the serving region. The [actual summary](evidence/20261010-checker-compatible43/ACTUAL_COMPATIBLE43_CHECKPOINT_SMALL_SUMMARY01.json) links to the full closed receipt.

## Exact input and validation

This independent batch repeats the same frozen original question, saved answer, trusted checker instructions, **10 claims, 19 units, and 71 source fragments**. Both actual request bodies are identical: 86938 bytes, SHA-256 `3ad513c0aef095fe34b2dbf737bdb48d922caa25277d20168c257c38ec5aca89`. All original41 messages and DATA are retained. Only the scoped remote response schema changes from the 7125-byte full canonical schema to the reviewed 3031-byte compatible textbook schema. This is an identical-condition repeat diagnostic, not a comparison of two RAG systems or evidence of a fresh question's quality.

Both unmodified raw responses include all 17 required root fields and pass the original full local `ReliableUnitCheck` schema, exact claim identities and unit coverage, owned citations and source references, source-relation contract, and local consistency checks. The [independent structural review](evidence/20261010-checker-compatible43/ACTUAL43_INDEPENDENT_STRUCTURAL_REVIEW.json) confirms both request bodies, original-input identity, raw-to-typed equality, and retained Main dependency pins. No automatic retry, JSON repair, teacher request, raw rewriting, citation insertion, or publication override occurred. The prior default-off Main integration remains unchanged.

## Selected-source completeness gap

The model labels all 10 claims and all 19 units `supported` in each repeat. These raw labels and reasons remain preserved. The [independent source review](evidence/20261010-checker-compatible43/ACTUAL_COMPATIBLE43_INDEPENDENT_SOURCE_REVIEW01.json) inspects only each unit's actual selected fragments within its own claim's allowed evidence scope. A claim is complete only when every declared unit is complete. Other available passages, sibling-unit citations, neutral anchor joins, and complete-block flags are not borrowed as proof.

The recurring gaps are the identity of three-carbon products as 3-PGA, describing the NADPH conversion as reduction, and the carbohydrate purpose of exported G3P. Repeat01 also lacks the full RuBP attributes and the three-turn qualifier in one selected source set. Repeat02 selects the RuBP attributes and the qualifier, but retains the other four partial units. The omitted supporting passages already exist in the allowed input; their availability does not repair the returned unit's selected-source proof. This is a source-selection completeness finding, **not a finding that the biological claims are false**. The variation between two same-condition outputs does not establish reliable improvement, quality noninferiority, or human Gold.

## Authorization, resource closure, and remaining work

The user explicitly approved the exact 71-fragment saved-answer disclosure before execution; the [approval receipt](evidence/20261010-checker-compatible43/USER_EXACT_71_SCOPE_APPROVAL43_RECEIPT01.json) preserves the original affirmative reply. The earlier two automatic approval stops are historical and resolved for this scope. Their original receipts remain unchanged. Fee authorization was already standing; no repeat fee question was required. The two-request $0.09 batch is closed and does not authorize additional requests inside that exhausted scope.

Credential preparation used one authorized read-only isolated-fixture consumer leg. Values stayed in memory and were cleared from the adapter; the checker experiment made no database accesses. Both requests are settled, the fresh lock is released, and no earlier stopped scope was reused. The previous schema41 **$0.045 UNKNOWN hold** remains protected.

Current Main's existing **245-case and 115-subtest PASS** remains scoped local regression evidence from the preserved [policy42 checkpoint](20261010-checker-schema-policy42.md). This replay adds real full-input checker compatibility evidence, but does not complete source quality, a unified RAG comparison, current native answer publication or full-answer timing, formal p95/noninferiority goals, human evaluation, the complete eight-stage qualification, clean installation, or the final course package. The preserved native36 41.1449-second TFull remains a historical single-case observation. Canonical task and acceptance registries are unchanged; `project_complete=false`.

The next reviewable work is to correct the remaining exact selected-source completeness gaps, verify the correction under frozen comparable inputs, and then complete native Send-to-full-answer timing and the remaining acceptance targets. The [curated evidence index](evidence/20261010-checker-compatible43/index.json) retains only public receipts and reviews; it excludes full71 prompt dumps, credentials, database content, and large execution logs. Existing phase42 and earlier deliveries remain immutable.

Root's [publication receipt](evidence/20261010-checker-compatible43/publication_receipt.json) establishes the Main archive and exact readback; the copied index preserves its historical W-only preparation status.
