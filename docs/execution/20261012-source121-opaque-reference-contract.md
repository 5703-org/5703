# Source121: opaque source-reference contract, offline only

The opt-in source interface now lets the model select one opaque source_id plus an exact quote. The program derives evidence ownership, fragment IDs, source-unit IDs and quote coordinates from the immutable submitted bank. A model cannot pair F048 with the wrong evidence origin because origin fields are absent from the V3 output schema; extra origin fields and incorrect ID/quote combinations are rejected, never ignored or searched elsewhere.

This is an explicit versioned source_refs_v3 transport under textbook_context_qualification_v1. Default legacy_origin_v2, existing default/A packets and legacy behavior remain unchanged. Unknown versions or V3 combined with another/no checker policy are rejected before any generation/checker stage. The modern parser requires its declared version and cannot fall back to the old parser.

## Independent decisions and binding rules

Claim citations are flat source_id/quote/relation references; canonical grouping and ownership are program consequences. Scientific claim/unit status, relation and condition judgments remain model decisions. Answer-unit unit_id identifies the assertion being checked and is retained; it is not the derived source_unit_id. Removing that target identity would require guessing which assertion a quote supports.

Positive original, unit and revision proof must belong to the actual claim citation allowlist. Original qualification support also passes the existing actually selected supporting-citation gate; supported units still require supporting relations. No source is silently added to a claim or moved across owners. Contextual limiting_quotes may select another supplied bank unit under that separate role; it never becomes original positive proof. Requirement source-availability evidence uses the full submitted bank as its independent axis. Repair hints use repair_sources with the same guarded references, restricted to the union of actual claim citations; the program derives repair_fragment_ids without activating a repair or certifying a claim.

Each quote must occur exactly once inside its chosen complete unit. Identical text in separate units is disambiguated by the opaque ID; multiple occurrences inside one unit are invalid. Citation/unit/requirement/repair selections cannot repeat an ID. Qualification roles may contain different unique quotes from one unit but cannot repeat an identical (source_id,quote) pair. All old unit, citation, context, requirement and teaching gates remain active. Provenance binding does not certify scientific entailment or repair model judgments.

Dedicated V3 prompts remove the contradictory old origin-field shape and repair-ID instructions. Legacy/default prompt files remain untouched. The shared runner changes only to forward the explicit source_transport selector into GenerationRequest; serialization, local transport, raw persistence, parsing, gates, scoring and terminal paths remain the same.

## Free verification and preserved failure

272 relevant tests passed in5.26s; Ruff passed. New tests cover correctly bound proof, forbidden/incorrect origin fields, wrong source ID without quote-search fallback, duplicate selections, repeated quote occurrences, duplicate bank text, all four out-of-scope positive roles, valid separately scoped contextual restriction, multiple distinct quotes from one unit, repair hints, invalid policy/version combinations before calls and missing-version refusal.

Six named full-runner controls in evidence121-reviewed.json: correctly-bound accepted; wrong-origin, duplicate-quote and outside-positive-scope invalid with null scores; valid-context-limitation technically valid but context-rejected; duplicate-bank-positive accepted under its exact selected origin. These are authored interface controls, not measured model quality.

The original120 S01-positive-B response was replayed explicitly with legacy_origin_v2 through the same runner. Compiled legacy payload hash exactly matches the original, copied raw bytes and raw_text are unchanged, and the same RELATION_ASSESSED_FRAGMENT_MISMATCH and QUALIFICATION_SOURCE_BINDING_INVALID errors remain with a null score. No owner reassignment, quote substitution or semantic correction occurred. Original raw SHA256: 44a2f4ec45fa71b7e7cc1f51c560178d2907571dc9d4b30e5d8a9684dc3bb735. Original/replayed wire SHA256: 6292a7c565bba0d747536669c2e6be878d6eae5f90f4a0a19f56ff81c750a112. Original120 result, terminal, costs, claims, failures and old holds remain sealed.

## Only two prepared positive controls

prepared-positive121-reviewed.json contains only S01-positive-B then S02-positive-B under V3. It preserves their original questions, saved answers, labels, claims, syntactic units, context coverage and source text; only the source_id input field and modern wire protocol are added. Unused S03 is omitted from the preparation envelope. Identity is121-preparation-only-source-refs-positive-controls, with no stale eight-slot pair declaration. offline_only=true, preparation_only=true, real_dispatch_enabled=false, maximum_future_requests=2.

Combined prospective protection at saved engineering input1/output4 CNY-per-million coefficients: CNY0.201460. This is not a paid reservation, refreshed price guarantee, new fee or invoice. No live caller/claim is activated, and no complete negative matrix is prepared. Prepared SHA256: b0a32bda795270bbeacd95c972a4810421c16ecb1c2f962f0a7211ced3ca973a. Two compiled payload hashes: ff9ca653545b77131ae0e5db9ff26a758154118b33183fb2b1b439747baed19e and137ea92213ff19d069a46cbcdfddf9ddd93b7a9543d3743e47b4ab2f639fcdce.

## Deliverables and remaining limit

Main source: generation/source_refs_v3.py; integration in qualification_v1.py, checked.py, types.py, source_relations_v2.py and scripts/dev/checker_fixture_runner.py; dedicated qualification_joint_v3.txt / qualification_check_v3.txt; tests/unit/test_source_refs121.py. Exact evidence root: C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-source121-offline. source-evidence121.json binds9source/7evidence files; preimages121.json retains5exact before-images; exercise121-reviewed.py reproduces offline controls/preparation into fresh output names. Separate contract-review121.json and runner-review121.json record actual independent RELEASE statements bound to final evidence.

This step made zero provider requests, credential reads, database operations or real spend. No installation, archive, remote publishing or course submission occurred. Only one Main report and prefix-preserving progress/migration appends are added. Actual positive model discrimination and full-answer latency remain unvalidated; the free interface controls do not close project acceptance. There is no automatic continuation of the stopped120 batch or real dispatch in this step.
