# Delivery view: suggested course week 9

Generated reporting view. The canonical ledgers below remain authoritative; this file adds no product requirement or acceptance decision.

Accountable owner and suggested course week are reporting metadata, never permissions, implementation eligibility, runtime flags or evidence of completion. Actual executor and recorded dates are shown separately. Cross-references do not count a task more than once. No calendar dates or completion percentages are inferred.

Canonical requirements, shared interfaces and evidence: [PRD.md](<../../../PRD.md>) · [SPEC.md](<../../../SPEC.md>) · [PLANS.md](<../../../PLANS.md>) · [HANDOVER.md](<../../../HANDOVER.md>) · [docs/foundation/api_contract.md](<../../foundation/api_contract.md>) · [contracts/openapi.json](<../../../contracts/openapi.json>) · [docs/execution/tasks.json](<../../execution/tasks.json>) · [docs/execution/reporting_plan.json](<../../execution/reporting_plan.json>) · [docs/execution/acceptance.json](<../../execution/acceptance.json>)

Task-ledger reconciliation timestamp (not a completion date): 2026-09-08T10:09:00.459775+00:00

This primary reporting bucket contains 8 unique tasks. A task's canonical suggested week chooses its one primary bucket. The planning packages below can mention it in other weeks as a cross-reference; these references add no completed tasks.

## Suggested allocation only

Suggested team reporting allocation only, not execution schedule, deadline or actual completion evidence.

Week convention: Course/teaching week; project_week=course_week-2 from Week 3. Optional contingency only; official dates/deadlines not confirmed

### Xianshu Zhang — suggested package

Review variant controls and code diffs; integrate improvements without requiring unsupported positive gains.

- Task cross-references: [INT-07](<../by_owner/xianshu-zhang.md#int-07>), [INT-08](<../by_owner/xianshu-zhang.md#int-08>)
- Suggested deliverable paths (not claims of delivery): `docs/research/variant_registry.md` (path absent)
- Suggested downstream consumers: Chengzhou Liu; Chong Zhang
- Planned acceptance description: Every comparison identifies changed/fixed factors; the prior baseline is not overwritten.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Hongle Yang — suggested package

Build fixed-window/structure-aware releases with span mappings and re-annotate qrels where necessary.

- Task cross-references: [DAT-07](<../by_owner/hongle-yang.md#dat-07>), [DAT-11](<../by_owner/hongle-yang.md#dat-11>)
- Suggested deliverable paths (not claims of delivery): `configs/variants/chunking/` (path absent), [evaluation/annotations/](<../../../evaluation/annotations>)
- Suggested downstream consumers: Chengzhou Liu; Chong Zhang
- Planned acceptance description: Incompatible chunk IDs are not reused; old answer text/hashes remain unchanged.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Chengzhou Liu — suggested package

Deliver BM25, RRF, re-ranking and chunk/embedding/k ablations; distinguish executable code from blocked measurements when models are unavailable.

- Task cross-references: [RET-07](<../by_owner/chengzhou-liu.md#ret-07>), [RET-08](<../by_owner/chengzhou-liu.md#ret-08>), [RET-09](<../by_owner/chengzhou-liu.md#ret-09>), [RET-10](<../by_owner/chengzhou-liu.md#ret-10>)
- Suggested deliverable paths (not claims of delivery): [retrieval/](<../../../retrieval>), `configs/variants/` (path absent), `artifacts/runs/ablations/` (path absent)
- Suggested downstream consumers: Chong Zhang; Sijin Lu; Zeping Liao
- Planned acceptance description: RRF matches hand calculations; changed embedding dimensions get compatible indexes; no hidden R3 fallback.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Sijin Lu — suggested package

Implement matched-policy controls and versioned prompts, recording timing/usage/errors without attributing multi-factor changes solely to retrieval.

- Task cross-references: [GEN-07](<../by_owner/sijin-lu.md#gen-07>), [GEN-10](<../by_owner/sijin-lu.md#gen-10>)
- Suggested deliverable paths (not claims of delivery): `configs/variants/matched_policy/` (path absent), `docs/research/generation_controls.md` (path absent)
- Suggested downstream consumers: Chong Zhang; Chengzhou Liu
- Planned acceptance description: Protocols remain distinct, reuse the shared engine and do not alter chat entry; a second live model remains optional.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Pengyuan Xia — suggested package

Prepare C0/C1/C2 inputs, frozen base responses/evidence and blinded rubrics for the next week.

- Task cross-references: [PER-08](<../by_owner/pengyuan-xia.md#per-08>), [PER-06](<../by_owner/pengyuan-xia.md#per-06>)
- Suggested deliverable paths (not claims of delivery): `configs/profiles/study.yaml` (path absent), `personalisation/rubric/` (path absent)
- Suggested downstream consumers: Chong Zhang; Sijin Lu
- Planned acceptance description: Study and product configurations are separate; gold never replaces the base response.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Zeping Liao — suggested package

Connect variant versions/run traces and embedding storage boundaries; verify backend/client schema synchronisation.

- Task cross-references: [BE-11](<../by_owner/zeping-liao.md#be-11>), [BE-14](<../by_owner/zeping-liao.md#be-14>), [BE-15](<../by_owner/zeping-liao.md#be-15>)
- Suggested deliverable paths (not claims of delivery): `backend/app/modules/experiments/` (path absent), [contracts/](<../../../contracts>)
- Suggested downstream consumers: Chengzhou Liu; Baiqing Huang
- Planned acceptance description: Switching retrievers does not rewrite login/history/evidence; legacy migration fixtures pass.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Baiqing Huang — suggested package

Complete comparison/configuration/failure-trace views and historical citation rendering after corpus changes.

- Task cross-references: [FE-10](<../by_owner/baiqing-huang.md#fe-10>), [FE-11](<../by_owner/baiqing-huang.md#fe-11>), [FE-06](<../by_owner/baiqing-huang.md#fe-06>)
- Suggested deliverable paths (not claims of delivery): `frontend/src/features/admin/experiments/` (path absent), `frontend/src/features/evidence/` (path absent)
- Suggested downstream consumers: Chong Zhang; Zeping Liao
- Planned acceptance description: Display actual denominators and missing metrics; old citations never silently target new content.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

### Chong Zhang — suggested package

Check single-factor comparisons, compatible qrels and paired samples; produce at least one real controlled finding when inputs permit.

- Task cross-references: [QA-04](<../by_owner/chong-zhang.md#qa-04>), [QA-08](<../by_owner/chong-zhang.md#qa-08>), [QA-09](<../by_owner/chong-zhang.md#qa-09>)
- Suggested deliverable paths (not claims of delivery): `evaluation/analysis/ablation.py` (path absent), [artifacts/reports/](<../../../artifacts/reports>)
- Suggested downstream consumers: Xianshu Zhang; Chengzhou Liu
- Planned acceptance description: Retain negative findings, keep missing labels null and identify exactly which comparisons were not executed.
- Planning record status (not actual task status): `PLANNED`
- Planning record actual executor / completed at: Not recorded (null). / Not recorded (null).
- Planning record actual evidence: None recorded.

## Actual evidence and demonstration material

The task records below quote the current ledger, independently of the suggested package. Their actual evidence links are the available demonstration and check material; an empty or null field stays unrecorded. The export does not create a meeting, human demonstration or historical completion event.

## Carry-over and unresolved work

These are currently recorded unresolved items for this reporting bucket, not claims that a calendar week elapsed or work was late.

- [DAT-11](<../by_owner/hongle-yang.md#dat-11>) (`REAL_FLOW_VERIFIED`): Changed chunks require a new reviewed qrel pool. No relevance grades or quality improvements are inferred from coverage/count/vector checks. Blockers: None recorded.
- [RET-07](<../by_owner/chengzhou-liu.md#ret-07>) (`REAL_FLOW_VERIFIED`): Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports. Blockers: None recorded.
- [RET-08](<../by_owner/chengzhou-liu.md#ret-08>) (`REAL_FLOW_VERIFIED`): Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports. Blockers: None recorded.
- [RET-09](<../by_owner/chengzhou-liu.md#ret-09>) (`REAL_FLOW_VERIFIED`): Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports. Blockers: None recorded.
- [RET-10](<../by_owner/chengzhou-liu.md#ret-10>) (`IMPLEMENTED_UNVERIFIED`): Configuration and paired-schedule preparation is verified; execution count is zero. Compatible judged qrels for v5/fixed are still missing, and the retained v4 null pool cannot be reused as compatible measurement evidence. The alternate model weights/release are unbuilt and user-deferred answering is mock. No unperformed embedding/k study or quality result is claimed. Blockers: None recorded.
- [GEN-10](<../by_owner/sijin-lu.md#gen-10>) (`MOCK_TEST_PASSED`): No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits. Blockers: None recorded.
- [FE-11](<../by_owner/baiqing-huang.md#fe-11>) (`REAL_FLOW_VERIFIED`): Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim. Blockers: None recorded.
- [QA-09](<../by_owner/chong-zhang.md#qa-09>) (`REAL_FLOW_VERIFIED`): Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports. Blockers: None recorded.

## DAT-11

Implement chunking comparison support. Build fixed-window and structure-aware releases from the same sources. Bind or review qrel mappings through source spans; incompatible labels cannot be reused as valid measurements.

- Accountable owner (reporting): Hongle Yang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 9, "suggested_project_week": 7, "suggested_start_course_week": 8, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G6
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["DAT-08", "QA-04"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "DAT-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-04"}]`
- Upstream collaborators (derived from those dependencies): [DAT-08](<../by_owner/hongle-yang.md#dat-08>) — Hongle Yang; [QA-04](<../by_owner/chong-zhang.md#qa-04>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [DAT-12](<../by_owner/hongle-yang.md#dat-12>) — Hongle Yang; [RET-10](<../by_owner/chengzhou-liu.md#ret-10>) — Chengzhou Liu
- Source files recorded for this implementation: [pipelines](<../../../pipelines>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>), [docs/data_rebuild.md](<../../data_rebuild.md>)
- Changed files recorded by the ledger: [pipelines](<../../../pipelines>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>), [docs/data_rebuild.md](<../../data_rebuild.md>)
- Shared entry / interface boundary: Administrator corpus routes and ingestion/build CLI / Corpus processing
- Persisted effect / consumer: Assets, versions, processing runs, source units, chunks, releases / Retrieval and source viewer
- Local acceptance clause: Implement chunking comparison support. Build fixed-window and structure-aware releases from the same sources. Bind or review qrel mappings through source spans; incompatible labels cannot be reused as valid measurements.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_pipeline.py](<../../../tests/unit/test_pipeline.py>), [tests/unit/test_evaluation_annotations.py](<../../../tests/unit/test_evaluation_annotations.py>)
- Recorded current check nodes: `["tests.unit.test_evaluation_annotations::test_qrels_require_actual_review_identity_and_frozen_sources", "tests.unit.test_evaluation_annotations::test_blinding_hides_conditions_and_retains_all_nine_items", "tests.unit.test_evaluation_annotations::test_missing_ratings_remain_null_and_pairs_use_questions", "tests.unit.test_evaluation_annotations::test_duplicate_and_failed_output_ratings_are_rejected", "tests.unit.test_evaluation_annotations::test_controlled_comparisons_reject_test_tuning_and_multiple_changes", "tests.unit.test_evaluation_annotations::test_twelve_authored_families_fit_composer_without_private_claims", "tests.unit.test_evaluation_annotations::test_conversation_profile_off_keeps_session_and_new_chat_is_distinct", "tests.unit.test_pipeline::test_clean_preserves_scientific_symbols_and_ambiguous_hard_hyphens", "tests.unit.test_pipeline::test_txt_heading_quality_and_original_text_remain_available", "tests.unit.test_pipeline::test_physical_pdf_pages_carry_real_sections_and_flag_removed_furniture", "tests.unit.test_pipeline::test_actual_pypdf_extracts_authored_bytes_with_physical_pages", "tests.unit.test_pipeline::test_pdf_page_extraction_failure_preserves_other_pages_and_blocks_publication", "tests.unit.test_pipeline::test_chunks_repeatable_unique_across_sections_and_reconstruct_exact_spans", "tests.unit.test_pipeline::test_exact_tokenizer_bounds_long_text_and_no_unmapped_character_loss", "tests.unit.test_pipeline::test_excluded_units_and_section_changes_never_merge", "tests.unit.test_pipeline::test_fixed_and_structure_strategies_preserve_source_coverage_with_distinct_boundaries", "tests.unit.test_pipeline::test_bookmarks_prevent_contents_false_sections_and_preserve_midpage_continuation", "tests.unit.test_pipeline::test_low_text_visual_page_blocks_while_prose_retains_visual_limitations", "tests.unit.test_pipeline::test_actual_unbookmarked_pdf_prefix_uses_page_local_labels_and_preserves_v4"]`
- Acceptance references: [AC-19](<../acceptance.md#ac-19>), [AC-28](<../acceptance.md#ac-28>), [AC-35](<../acceptance.md#ac-35>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/chunking/fixed-v5/comparison-summary.json](<../../../evidence/chunking/fixed-v5/comparison-summary.json>), [evidence/chunking/fixed-v5/formal-source-validation.json](<../../../evidence/chunking/fixed-v5/formal-source-validation.json>), [evidence/chunking/fixed-v5/release-build.json](<../../../evidence/chunking/fixed-v5/release-build.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Fixed-window and structure-aware releases were actually built from the same four official sources, v5 parsing/recovery and pinned E5 configuration. Complete source-span coverage, unchanged source-unit text/issues and real-vector relationships were checked; the fixed comparison release remains unactivated.
- Unresolved scope: Changed chunks require a new reviewed qrel pool. No relevance grades or quality improvements are inferred from coverage/count/vector checks.
- Blockers: None recorded.
- Mapping limitation: Changed chunks require a new reviewed qrel pool. No relevance grades or quality improvements are inferred from coverage/count/vector checks.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Fixed-window and structure-aware releases were actually built from the same four official sources, v5 parsing/recovery and pinned E5 configuration. Complete source-span coverage, unchanged source-unit text/issues and real-vector relationships were checked; the fixed comparison release remains unactivated.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/chunking/fixed-v5/comparison-summary.json](<../../../evidence/chunking/fixed-v5/comparison-summary.json>), [evidence/chunking/fixed-v5/formal-source-validation.json](<../../../evidence/chunking/fixed-v5/formal-source-validation.json>), [evidence/chunking/fixed-v5/release-build.json](<../../../evidence/chunking/fixed-v5/release-build.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Changed chunks require a new reviewed qrel pool. No relevance grades or quality improvements are inferred from coverage/count/vector checks.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## RET-07

Implement R1 BM25 over the same frozen chunk release as R0. Preserve lexical scoring/tokenisation and deterministic ties through the shared RetrieverPort. Its coding depends on usable R0 artifacts, not a completed live SciQ study; measured comparisons still require frozen run evidence.

- Accountable owner (reporting): Chengzhou Liu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 9, "suggested_project_week": 7, "suggested_start_course_week": 8, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G6
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["RET-05", "DAT-08"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-05"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "DAT-08"}]`
- Upstream collaborators (derived from those dependencies): [RET-05](<../by_owner/chengzhou-liu.md#ret-05>) — Chengzhou Liu; [DAT-08](<../by_owner/hongle-yang.md#dat-08>) — Hongle Yang
- Downstream collaborators (reverse dependency references): [RET-08](<../by_owner/chengzhou-liu.md#ret-08>) — Chengzhou Liu; [QA-09](<../by_owner/chong-zhang.md#qa-09>) — Chong Zhang
- Source files recorded for this implementation: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Changed files recorded by the ledger: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Shared entry / interface boundary: Shared answer service and evaluation runner / Retrieval and query preparation
- Persisted effect / consumer: Release vectors and immutable retrieval/evidence snapshots / Generation prompts and evidence viewer
- Local acceptance clause: Implement R1 BM25 over the same frozen chunk release as R0. Preserve lexical scoring/tokenisation and deterministic ties through the shared RetrieverPort. Its coding depends on usable R0 artifacts, not a completed live SciQ study; measured comparisons still require frozen run evidence.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_retrieval.py](<../../../tests/unit/test_retrieval.py>), [tests/integration/test_corpus_runtime.py](<../../../tests/integration/test_corpus_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_corpus_runtime::test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "tests.integration.test_corpus_runtime::test_quarantine_inspectable_exclusion_and_processing_lineage", "tests.integration.test_corpus_runtime::test_reprocessing_creates_new_chunks_while_old_evidence_survives", "tests.integration.test_corpus_runtime::test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "tests.integration.test_corpus_runtime::test_processing_diff_reports_split_groups_by_overlapping_source_spans", "tests.integration.test_corpus_runtime::test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "tests.integration.test_corpus_runtime::test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "tests.integration.test_corpus_runtime::test_source_deactivation_filters_current_retrieval_and_restore_recovers", "tests.integration.test_corpus_runtime::test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks", "tests.integration.test_corpus_runtime::test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "tests.integration.test_corpus_runtime::test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest", "tests.integration.test_corpus_runtime::test_legacy_release_without_saved_hashes_requires_explicit_new_build", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[cancel]", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[recover]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[cancel]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[recover]", "tests.unit.test_retrieval::test_mock_embedding_is_normalized_repeatable_and_content_sensitive", "tests.unit.test_retrieval::test_bm25_matches_hand_calculated_term_and_stable_ties", "tests.unit.test_retrieval::test_rrf_uses_one_based_ranks_and_never_raw_score_magnitudes", "tests.unit.test_retrieval::test_e5_actual_tokenizer_prefixes_dimension_and_no_silent_truncation", "tests.unit.test_retrieval::test_reranker_records_actual_spans_limits_candidate_count_and_validates_outputs"]`
- Acceptance references: [AC-19](<../acceptance.md#ac-19>), [AC-34](<../acceptance.md#ac-34>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [evidence/retrieval/post-recovery-comparison.json](<../../../evidence/retrieval/post-recovery-comparison.json>), [evidence/retrieval/post-recovery-summary.json](<../../../evidence/retrieval/post-recovery-summary.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: R0/R1/R2/R3 executed against the same frozen official four-book chunk/vector set with real E5 and pinned cross-encoder inference. Controlled diagnostics retain all scheduled successes/errors, ranked source text, token windows, timings and rank differences.
- Unresolved scope: Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.
- Blockers: None recorded.
- Mapping limitation: Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. R0/R1/R2/R3 executed against the same frozen official four-book chunk/vector set with real E5 and pinned cross-encoder inference. Controlled diagnostics retain all scheduled successes/errors, ranked source text, token windows, timings and rank differences.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [evidence/retrieval/post-recovery-comparison.json](<../../../evidence/retrieval/post-recovery-comparison.json>), [evidence/retrieval/post-recovery-summary.json](<../../../evidence/retrieval/post-recovery-summary.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## RET-08

Implement R2 RRF fusion. Fuse independently retrieved candidate lists by chunk ID using one-based reciprocal ranks and constant 60. Test missing entries, duplicates and ties against hand calculations.

- Accountable owner (reporting): Chengzhou Liu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 9, "suggested_project_week": 7, "suggested_start_course_week": 8, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G6
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["RET-07", "RET-03"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-03"}]`
- Upstream collaborators (derived from those dependencies): [RET-07](<../by_owner/chengzhou-liu.md#ret-07>) — Chengzhou Liu; [RET-03](<../by_owner/chengzhou-liu.md#ret-03>) — Chengzhou Liu
- Downstream collaborators (reverse dependency references): [RET-09](<../by_owner/chengzhou-liu.md#ret-09>) — Chengzhou Liu
- Source files recorded for this implementation: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Changed files recorded by the ledger: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Shared entry / interface boundary: Shared answer service and evaluation runner / Retrieval and query preparation
- Persisted effect / consumer: Release vectors and immutable retrieval/evidence snapshots / Generation prompts and evidence viewer
- Local acceptance clause: Implement R2 RRF fusion. Fuse independently retrieved candidate lists by chunk ID using one-based reciprocal ranks and constant 60. Test missing entries, duplicates and ties against hand calculations.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_retrieval.py](<../../../tests/unit/test_retrieval.py>), [tests/integration/test_corpus_runtime.py](<../../../tests/integration/test_corpus_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_corpus_runtime::test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "tests.integration.test_corpus_runtime::test_quarantine_inspectable_exclusion_and_processing_lineage", "tests.integration.test_corpus_runtime::test_reprocessing_creates_new_chunks_while_old_evidence_survives", "tests.integration.test_corpus_runtime::test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "tests.integration.test_corpus_runtime::test_processing_diff_reports_split_groups_by_overlapping_source_spans", "tests.integration.test_corpus_runtime::test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "tests.integration.test_corpus_runtime::test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "tests.integration.test_corpus_runtime::test_source_deactivation_filters_current_retrieval_and_restore_recovers", "tests.integration.test_corpus_runtime::test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks", "tests.integration.test_corpus_runtime::test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "tests.integration.test_corpus_runtime::test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest", "tests.integration.test_corpus_runtime::test_legacy_release_without_saved_hashes_requires_explicit_new_build", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[cancel]", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[recover]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[cancel]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[recover]", "tests.unit.test_retrieval::test_mock_embedding_is_normalized_repeatable_and_content_sensitive", "tests.unit.test_retrieval::test_bm25_matches_hand_calculated_term_and_stable_ties", "tests.unit.test_retrieval::test_rrf_uses_one_based_ranks_and_never_raw_score_magnitudes", "tests.unit.test_retrieval::test_e5_actual_tokenizer_prefixes_dimension_and_no_silent_truncation", "tests.unit.test_retrieval::test_reranker_records_actual_spans_limits_candidate_count_and_validates_outputs"]`
- Acceptance references: [AC-19](<../acceptance.md#ac-19>), [AC-34](<../acceptance.md#ac-34>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [evidence/retrieval/post-recovery-comparison.json](<../../../evidence/retrieval/post-recovery-comparison.json>), [evidence/retrieval/post-recovery-summary.json](<../../../evidence/retrieval/post-recovery-summary.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: R0/R1/R2/R3 executed against the same frozen official four-book chunk/vector set with real E5 and pinned cross-encoder inference. Controlled diagnostics retain all scheduled successes/errors, ranked source text, token windows, timings and rank differences.
- Unresolved scope: Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.
- Blockers: None recorded.
- Mapping limitation: Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. R0/R1/R2/R3 executed against the same frozen official four-book chunk/vector set with real E5 and pinned cross-encoder inference. Controlled diagnostics retain all scheduled successes/errors, ranked source text, token windows, timings and rank differences.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [evidence/retrieval/post-recovery-comparison.json](<../../../evidence/retrieval/post-recovery-comparison.json>), [evidence/retrieval/post-recovery-summary.json](<../../../evidence/retrieval/post-recovery-summary.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## RET-09

Implement R3 re-ranking. Re-rank the configured fused candidate pool through a real configurable cross-encoder adapter. Preserve candidate provenance and record timing/window policy; failures cannot masquerade as successful R3.

- Accountable owner (reporting): Chengzhou Liu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 9, "suggested_project_week": 7, "suggested_start_course_week": 8, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G6
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["RET-08", "GEN-02"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-02"}]`
- Upstream collaborators (derived from those dependencies): [RET-08](<../by_owner/chengzhou-liu.md#ret-08>) — Chengzhou Liu; [GEN-02](<../by_owner/sijin-lu.md#gen-02>) — Sijin Lu
- Downstream collaborators (reverse dependency references): [RET-10](<../by_owner/chengzhou-liu.md#ret-10>) — Chengzhou Liu
- Source files recorded for this implementation: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Changed files recorded by the ledger: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Shared entry / interface boundary: Shared answer service and evaluation runner / Retrieval and query preparation
- Persisted effect / consumer: Release vectors and immutable retrieval/evidence snapshots / Generation prompts and evidence viewer
- Local acceptance clause: Implement R3 re-ranking. Re-rank the configured fused candidate pool through a real configurable cross-encoder adapter. Preserve candidate provenance and record timing/window policy; failures cannot masquerade as successful R3.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_retrieval.py](<../../../tests/unit/test_retrieval.py>), [tests/integration/test_corpus_runtime.py](<../../../tests/integration/test_corpus_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_corpus_runtime::test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "tests.integration.test_corpus_runtime::test_quarantine_inspectable_exclusion_and_processing_lineage", "tests.integration.test_corpus_runtime::test_reprocessing_creates_new_chunks_while_old_evidence_survives", "tests.integration.test_corpus_runtime::test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "tests.integration.test_corpus_runtime::test_processing_diff_reports_split_groups_by_overlapping_source_spans", "tests.integration.test_corpus_runtime::test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "tests.integration.test_corpus_runtime::test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "tests.integration.test_corpus_runtime::test_source_deactivation_filters_current_retrieval_and_restore_recovers", "tests.integration.test_corpus_runtime::test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks", "tests.integration.test_corpus_runtime::test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "tests.integration.test_corpus_runtime::test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest", "tests.integration.test_corpus_runtime::test_legacy_release_without_saved_hashes_requires_explicit_new_build", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[cancel]", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[recover]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[cancel]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[recover]", "tests.unit.test_retrieval::test_mock_embedding_is_normalized_repeatable_and_content_sensitive", "tests.unit.test_retrieval::test_bm25_matches_hand_calculated_term_and_stable_ties", "tests.unit.test_retrieval::test_rrf_uses_one_based_ranks_and_never_raw_score_magnitudes", "tests.unit.test_retrieval::test_e5_actual_tokenizer_prefixes_dimension_and_no_silent_truncation", "tests.unit.test_retrieval::test_reranker_records_actual_spans_limits_candidate_count_and_validates_outputs"]`
- Acceptance references: [AC-11](<../acceptance.md#ac-11>), [AC-19](<../acceptance.md#ac-19>), [AC-34](<../acceptance.md#ac-34>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [evidence/retrieval/post-recovery-comparison.json](<../../../evidence/retrieval/post-recovery-comparison.json>), [evidence/retrieval/post-recovery-summary.json](<../../../evidence/retrieval/post-recovery-summary.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: R0/R1/R2/R3 executed against the same frozen official four-book chunk/vector set with real E5 and pinned cross-encoder inference. Controlled diagnostics retain all scheduled successes/errors, ranked source text, token windows, timings and rank differences.
- Unresolved scope: Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.
- Blockers: None recorded.
- Mapping limitation: Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. R0/R1/R2/R3 executed against the same frozen official four-book chunk/vector set with real E5 and pinned cross-encoder inference. Controlled diagnostics retain all scheduled successes/errors, ranked source text, token windows, timings and rank differences.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [evidence/retrieval/post-recovery-comparison.json](<../../../evidence/retrieval/post-recovery-comparison.json>), [evidence/retrieval/post-recovery-summary.json](<../../../evidence/retrieval/post-recovery-summary.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## RET-10

Implement isolated retrieval ablations. Run or prepare controlled chunking/embedding/k comparisons with immutable manifests and compatible qrels. Change one named factor per comparison and distinguish executable code from missing live runs.

- Accountable owner (reporting): Chengzhou Liu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 9, "suggested_project_week": 7, "suggested_start_course_week": 8, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G6
- Current status: `IMPLEMENTED_UNVERIFIED`
- Separate implementation / verification / research / human-review states: `IMPLEMENTED_UNVERIFIED` / `IMPLEMENTED_UNVERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["RET-09", "DAT-11", "QA-09"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-09"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "DAT-11"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-09"}]`
- Upstream collaborators (derived from those dependencies): [RET-09](<../by_owner/chengzhou-liu.md#ret-09>) — Chengzhou Liu; [DAT-11](<../by_owner/hongle-yang.md#dat-11>) — Hongle Yang; [QA-09](<../by_owner/chong-zhang.md#qa-09>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [RET-11](<../by_owner/chengzhou-liu.md#ret-11>) — Chengzhou Liu
- Source files recorded for this implementation: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Changed files recorded by the ledger: [retrieval/embedding.py](<../../../retrieval/embedding.py>), [retrieval/ranking.py](<../../../retrieval/ranking.py>), [backend/app/modules/knowledge/service.py](<../../../backend/app/modules/knowledge/service.py>)
- Shared entry / interface boundary: Shared answer service and evaluation runner / Retrieval and query preparation
- Persisted effect / consumer: Release vectors and immutable retrieval/evidence snapshots / Generation prompts and evidence viewer
- Local acceptance clause: Implement isolated retrieval ablations. Run or prepare controlled chunking/embedding/k comparisons with immutable manifests and compatible qrels. Change one named factor per comparison and distinguish executable code from missing live runs.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_retrieval.py](<../../../tests/unit/test_retrieval.py>), [tests/unit/test_evaluation_annotations.py](<../../../tests/unit/test_evaluation_annotations.py>)
- Recorded current check nodes: `["tests.unit.test_evaluation_annotations::test_qrels_require_actual_review_identity_and_frozen_sources", "tests.unit.test_evaluation_annotations::test_blinding_hides_conditions_and_retains_all_nine_items", "tests.unit.test_evaluation_annotations::test_missing_ratings_remain_null_and_pairs_use_questions", "tests.unit.test_evaluation_annotations::test_duplicate_and_failed_output_ratings_are_rejected", "tests.unit.test_evaluation_annotations::test_controlled_comparisons_reject_test_tuning_and_multiple_changes", "tests.unit.test_evaluation_annotations::test_twelve_authored_families_fit_composer_without_private_claims", "tests.unit.test_evaluation_annotations::test_conversation_profile_off_keeps_session_and_new_chat_is_distinct", "tests.unit.test_retrieval::test_mock_embedding_is_normalized_repeatable_and_content_sensitive", "tests.unit.test_retrieval::test_bm25_matches_hand_calculated_term_and_stable_ties", "tests.unit.test_retrieval::test_rrf_uses_one_based_ranks_and_never_raw_score_magnitudes", "tests.unit.test_retrieval::test_e5_actual_tokenizer_prefixes_dimension_and_no_silent_truncation", "tests.unit.test_retrieval::test_reranker_records_actual_spans_limits_candidate_count_and_validates_outputs"]`
- Acceptance references: [AC-19](<../acceptance.md#ac-19>), [AC-35](<../acceptance.md#ac-35>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/chunking/fixed-v5/comparison-summary.json](<../../../evidence/chunking/fixed-v5/comparison-summary.json>), [docs/r0_review_pool.md](<../../r0_review_pool.md>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [docs/controlled_study_designs.md](<../../controlled_study_designs.md>), [evidence/evaluation/ret10-design/preparation.json](<../../../evidence/evaluation/ret10-design/preparation.json>), [evidence/evaluation/ret10-design/integrity-review.json](<../../../evidence/evaluation/ret10-design/integrity-review.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: An actual one-factor fixed-versus-structure corpus comparison has immutable manifests and verified source coverage. Two actual immutable study designs retain all 1,000 official validation IDs and exact v5 settings: k5 versus3 and pinned E5-small versus E5-base. Official alternate-model metadata is verified; existing single-factor guards accept the designs and reject extra-factor/identity changes. No study calls or alternate embedding release are invented.
- Unresolved scope: Configuration and paired-schedule preparation is verified; execution count is zero. Compatible judged qrels for v5/fixed are still missing, and the retained v4 null pool cannot be reused as compatible measurement evidence. The alternate model weights/release are unbuilt and user-deferred answering is mock. No unperformed embedding/k study or quality result is claimed.
- Blockers: None recorded.
- Mapping limitation: Configuration and paired-schedule preparation is verified; execution count is zero. Compatible judged qrels for v5/fixed are still missing, and the retained v4 null pool cannot be reused as compatible measurement evidence. The alternate model weights/release are unbuilt and user-deferred answering is mock. No unperformed embedding/k study or quality result is claimed.

Recorded component observations:

- observed task scope: `IMPLEMENTED_UNVERIFIED`. An actual one-factor fixed-versus-structure corpus comparison has immutable manifests and verified source coverage. Two actual immutable study designs retain all 1,000 official validation IDs and exact v5 settings: k5 versus3 and pinned E5-small versus E5-base. Official alternate-model metadata is verified; existing single-factor guards accept the designs and reject extra-factor/identity changes. No study calls or alternate embedding release are invented.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [evidence/chunking/fixed-v5/comparison-summary.json](<../../../evidence/chunking/fixed-v5/comparison-summary.json>), [docs/r0_review_pool.md](<../../r0_review_pool.md>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [docs/controlled_study_designs.md](<../../controlled_study_designs.md>), [evidence/evaluation/ret10-design/preparation.json](<../../../evidence/evaluation/ret10-design/preparation.json>), [evidence/evaluation/ret10-design/integrity-review.json](<../../../evidence/evaluation/ret10-design/integrity-review.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Configuration and paired-schedule preparation is verified; execution count is zero. Compatible judged qrels for v5/fixed are still missing, and the retained v4 null pool cannot be reused as compatible measurement evidence. The alternate model weights/release are unbuilt and user-deferred answering is mock. No unperformed embedding/k study or quality result is claimed.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## GEN-10

Implement separately labelled evaluation controls. Use stem-only open-answer and MCQ prompts with fixed policies; retain legacy/matched-policy diagnostics under explicit protocol IDs. A second model remains optional and never becomes a chat dependency. Generation handover migration: Connect the separate OpenQA/MCQ protocols and the labelled matched-policy controls/variants. Freeze model settings and record differences; a second live model remains optional.

- Accountable owner (reporting): Sijin Lu
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 9, "suggested_project_week": 7, "suggested_start_course_week": 8, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G6
- Current status: `MOCK_TEST_PASSED`
- Separate implementation / verification / research / human-review states: `MOCK_TEST_PASSED` / `MOCK_TEST_PASSED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["GEN-08", "QA-07"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "GEN-08"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-07"}]`
- Upstream collaborators (derived from those dependencies): [GEN-08](<../by_owner/sijin-lu.md#gen-08>) — Sijin Lu; [QA-07](<../by_owner/chong-zhang.md#qa-07>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [GEN-11](<../by_owner/sijin-lu.md#gen-11>) — Sijin Lu
- Source files recorded for this implementation: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Changed files recorded by the ledger: [generation/service.py](<../../../generation/service.py>), [generation/adapters.py](<../../../generation/adapters.py>), [generation/parser.py](<../../../generation/parser.py>), [generation/prompt_builder.py](<../../../generation/prompt_builder.py>), [generation/prompts](<../../../generation/prompts>)
- Shared entry / interface boundary: Shared answer service through worker or offline runner / GenerationService
- Persisted effect / consumer: Attempts, prompt metadata and typed response/evidence snapshots / Chat renderer and evaluation scorer
- Local acceptance clause: Implement separately labelled evaluation controls. Use stem-only open-answer and MCQ prompts with fixed policies; retain legacy/matched-policy diagnostics under explicit protocol IDs. A second model remains optional and never becomes a chat dependency.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_generation_contracts.py](<../../../tests/unit/test_generation_contracts.py>), [tests/unit/test_generation_engine.py](<../../../tests/unit/test_generation_engine.py>), [tests/unit/test_mock_evidence_coverage.py](<../../../tests/unit/test_mock_evidence_coverage.py>), [tests/integration/test_runtime_faults.py](<../../../tests/integration/test_runtime_faults.py>)
- Recorded current check nodes: `["tests.integration.test_runtime_faults::test_simultaneous_duplicate_submit_and_optimistic_updates", "tests.integration.test_runtime_faults::test_provider_format_repair_counts_survive_retry", "tests.integration.test_runtime_faults::test_cancel_during_provider_call_fences_late_output", "tests.integration.test_runtime_faults::test_stop_during_retrieval_model_work_does_not_wait_for_job_lock", "tests.integration.test_runtime_faults::test_database_failure_publishes_no_partial_answer", "tests.integration.test_runtime_faults::test_stale_recovery_preserves_exhausted_budget", "tests.integration.test_runtime_faults::test_account_credential_revocation_and_admin_reset", "tests.integration.test_runtime_faults::test_long_context_summary_is_persisted_and_attributable", "tests.integration.test_runtime_faults::test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "tests.unit.test_generation_contracts::test_chat_message_never_requires_choices", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[gold_answer]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[history]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[summary]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[model]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[owner]", "tests.unit.test_generation_contracts::test_learner_cannot_supply_trusted_or_evaluator_fields[options]", "tests.unit.test_generation_contracts::test_chat_preserves_complete_prose_and_all_required_fields", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[True]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[False]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[nan]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[inf]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[-0.1]", "tests.unit.test_generation_contracts::test_chat_rejects_invalid_confidence[1.1]", "tests.unit.test_generation_contracts::test_refusal_has_distinct_empty_and_null_invariants", "tests.unit.test_generation_contracts::test_social_and_clarification_have_no_compact_factual_answer[social]", "tests.unit.test_generation_contracts::test_social_and_clarification_have_no_compact_factual_answer[clarification]", "tests.unit.test_generation_contracts::test_mcq_requires_exact_four_labels_and_normalized_distinct_options", "tests.unit.test_generation_contracts::test_mcq_preserves_original_option_text_for_exact_output_comparison", "tests.unit.test_generation_contracts::test_legacy_mcq_refusal_enum_is_separate_from_chat", "tests.unit.test_generation_engine::test_strict_json_negatives[\`\`\`json\\n{}\\n\`\`\`]", "tests.unit.test_generation_engine::test_strict_json_negatives[{} {}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{} trailing]", "tests.unit.test_generation_engine::test_strict_json_negatives[[]]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":NaN}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":Infinity}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"x\":1,\"x\":2}]", "tests.unit.test_generation_engine::test_strict_json_negatives[{\"nested\":{\"x\":1,\"x\":2}}]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates0]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates1]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates2]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates3]", "tests.unit.test_generation_engine::test_schema_and_selected_source_negatives[updates4]", "tests.unit.test_generation_engine::test_actual_role_order_profile_off_and_frozen_benchmark_boundary", "tests.unit.test_generation_engine::test_mock_changes_with_current_evidence_and_history_sensitive_query", "tests.unit.test_generation_engine::test_shared_four_call_budget_covers_transient_and_one_format_repair", "tests.unit.test_generation_engine::test_invalid_twice_is_error_not_refusal_and_retry_retains_budget", "tests.unit.test_generation_engine::test_complete_json_with_length_finish_never_publishes_or_repairs", "tests.unit.test_generation_engine::test_context_budget_includes_profile_schema_and_output_and_drops_whole_chunks", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload0-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload1-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload2-PROVIDER_RESPONSE_ERROR]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload3-EMPTY_RESPONSE]", "tests.unit.test_generation_engine::test_provider_empty_and_truncated_envelopes[payload4-OUTPUT_TRUNCATED]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[429-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[500-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[503-True]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[401-False]", "tests.unit.test_generation_engine::test_provider_http_metadata_and_retryability[403-False]", "tests.unit.test_generation_engine::test_http_adapter_sends_actual_roles_and_unknown_usage_remains_null", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[How do I configure Kubernetes ingress TLS certificates?]", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[Who won the 2026 Formula One world championship?]", "tests.unit.test_mock_evidence_coverage::test_actual_unrelated_candidates_never_become_factual_answers[What is the current exchange rate between the yen and the euro?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How does negative feedback maintain homeostasis?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What are the functions of erythrocytes, leukocytes and platelets?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How does glycolysis produce ATP from glucose?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[How do natural selection and genetic drift differ?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What is the difference between a food chain and a food web?]", "tests.unit.test_mock_evidence_coverage::test_actual_textbook_candidates_retain_supported_extractive_answers[What is the difference between prokaryotic and eukaryotic cells?]", "tests.unit.test_mock_evidence_coverage::test_actual_learning_objective_question_is_not_mistaken_for_an_answer", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Why does it need light?]", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Make it simpler]", "tests.unit.test_mock_evidence_coverage::test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up[Give an example]", "tests.unit.test_mock_evidence_coverage::test_numbers_and_negation_are_required_content[Explain nuclear fusion in 2031]", "tests.unit.test_mock_evidence_coverage::test_numbers_and_negation_are_required_content[Explain nuclear fusion without heat]", "tests.unit.test_mock_evidence_coverage::test_terms_scattered_over_unrelated_paragraphs_do_not_qualify_an_excerpt", "tests.unit.test_mock_evidence_coverage::test_provider_scores_are_not_used_to_qualify_mock_evidence", "tests.unit.test_mock_evidence_coverage::test_standard_inflections_do_not_require_unrelated_keyword_exceptions", "tests.unit.test_mock_evidence_coverage::test_grounded_teaching_base_retains_energy_form_answer", "tests.unit.test_mock_evidence_coverage::test_source_exercise_question_does_not_become_an_asserted_answer", "tests.unit.test_mock_evidence_coverage::test_learner_correction_completes_an_ambiguous_turn_with_the_named_topic"]`
- Acceptance references: [AC-07](<../acceptance.md#ac-07>), [AC-19](<../acceptance.md#ac-19>), [AC-46](<../acceptance.md#ac-46>), [HC-11](<../acceptance.md#hc-11>), [HC-12](<../acceptance.md#hc-12>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/mock-evidence-replay.md](<../../execution/mock-evidence-replay.md>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current strict chat/MCQ schemas, mode-specific prompts, no-gold boundary, simulated provider failures, finite shared retries/repair and deterministic response policies passed their executed tests. Actual-source mock replays retain unsupported/refused cases.
- Unresolved scope: No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.
- Blockers: None recorded.
- Mapping limitation: No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.

Handoff consumers: `["Chong Zhang", "Chengzhou Liu"]`

Handover actions: Connect the separate OpenQA/MCQ protocols and the labelled matched-policy controls/variants. Freeze model settings and record differences; a second live model remains optional.

Handover checks: `["HC-11", "HC-12"]`

Source asset state: Configurable models and two prompts are foundations, not formal comparable experiments.

Recorded component observations:

- observed task scope: `MOCK_TEST_PASSED`. Current strict chat/MCQ schemas, mode-specific prompts, no-gold boundary, simulated provider failures, finite shared retries/repair and deterministic response policies passed their executed tests. Actual-source mock replays retain unsupported/refused cases.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/mock-evidence-replay.md](<../../execution/mock-evidence-replay.md>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. No real answering-provider semantic or effectiveness result is claimed; the mock adapter has explicit topic/wording limits.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## FE-11

Implement secondary administrator evaluation pages. Distinguish chat_scenarios, sciq_openqa, sciq_mcq and profile studies; show protocols, denominators and all outcome states. These pages do not become the learner landing page or a prerequisite for chat.

- Accountable owner (reporting): Baiqing Huang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 9, "suggested_project_week": 7, "suggested_start_course_week": 8, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G6
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["FE-02", "BE-11", "BE-12", "QA-06"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "FE-02"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-11"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "BE-12"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-06"}]`
- Upstream collaborators (derived from those dependencies): [FE-02](<../by_owner/baiqing-huang.md#fe-02>) — Baiqing Huang; [BE-11](<../by_owner/zeping-liao.md#be-11>) — Zeping Liao; [BE-12](<../by_owner/zeping-liao.md#be-12>) — Zeping Liao; [QA-06](<../by_owner/chong-zhang.md#qa-06>) — Chong Zhang
- Downstream collaborators (reverse dependency references): [FE-12](<../by_owner/baiqing-huang.md#fe-12>) — Baiqing Huang; [QA-12](<../by_owner/chong-zhang.md#qa-12>) — Chong Zhang; [CHAT-11](<../by_owner/xianshu-zhang.md#chat-11>) — Xianshu Zhang
- Source files recorded for this implementation: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Changed files recorded by the ledger: [frontend/src](<../../../frontend/src>), [docs/frontend.md](<../../frontend.md>)
- Shared entry / interface boundary: Browser routes and accessible controls / Typed API client and feature views
- Persisted effect / consumer: Server-owned session/job/answer/profile/corpus/experiment records / Learner and administrator workflows
- Local acceptance clause: Implement secondary administrator evaluation pages. Distinguish chat_scenarios, sciq_openqa, sciq_mcq and profile studies; show protocols, denominators and all outcome states. These pages do not become the learner landing page or a prerequisite for chat.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [frontend/tests](<../../../frontend/tests>)
- Recorded current check nodes: None recorded.
- Acceptance references: [AC-18](<../acceptance.md#ac-18>), [AC-19](<../acceptance.md#ac-19>), [AC-37](<../acceptance.md#ac-37>), [AC-46](<../acceptance.md#ac-46>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
- Unresolved scope: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.
- Blockers: None recorded.
- Mapping limitation: Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. Current frontend types/components/build and real API browser journeys verify chat/account/profile/source/history/revision/feedback and admin consumers. Legacy MCQ answered/refused rows have isolated rendering tests; the learner composer stays natural-language.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/execution/audit-ui.md](<../../execution/audit-ui.md>), [evidence/ui/legacy-mcq-component-tests.json](<../../../evidence/ui/legacy-mcq-component-tests.json>), [evidence/openstax/real-corpus-chat.json](<../../../evidence/openstax/real-corpus-chat.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Answering remains mock. Component fixtures and browser/real-source runs have distinct scopes; no physical-device or semantic-quality claim.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.

## QA-09

Control variant studies. Register and verify one-factor changes, frozen question sets, qrel versions and real execution evidence. Produce at least one controlled improvement study when possible without redefining E1.

- Accountable owner (reporting): Chong Zhang
- Actual executor: Codex shared implementation; domain owner remains reporting metadata
- Suggested allocation: `{"suggested_course_week": 9, "suggested_project_week": 7, "suggested_start_course_week": 8, "view_only": true}`
- Actual start / completion / course week: Not recorded (null). / Not recorded (null). / Not recorded (null).
- Execution checkpoint: G6
- Current status: `REAL_FLOW_VERIFIED`
- Separate implementation / verification / research / human-review states: `REAL_FLOW_VERIFIED` / `REAL_FLOW_VERIFIED` / `NOT_ASSESSED` / `WAITING_EXTERNAL`
- Completion claim recorded by the ledger: `false`
- Exact dependency IDs: `["QA-07", "RET-07"]`
- Required dependency artifacts: `[{"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "QA-07"}, {"required": "Usable contract/implementation artifact and relevant producer checks; not a future reporting week or unperformed unrelated live/human study", "task_id": "RET-07"}]`
- Upstream collaborators (derived from those dependencies): [QA-07](<../by_owner/chong-zhang.md#qa-07>) — Chong Zhang; [RET-07](<../by_owner/chengzhou-liu.md#ret-07>) — Chengzhou Liu
- Downstream collaborators (reverse dependency references): [RET-10](<../by_owner/chengzhou-liu.md#ret-10>) — Chengzhou Liu; [QA-14](<../by_owner/chong-zhang.md#qa-14>) — Chong Zhang
- Source files recorded for this implementation: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Changed files recorded by the ledger: [evaluation](<../../../evaluation>), [configs/evaluation](<../../../configs/evaluation>)
- Shared entry / interface boundary: Verification commands, scenarios and evaluator runner / Acceptance and evaluation
- Persisted effect / consumer: Frozen run items, private references, observations and ratings / Technical audit and separate scientific reports
- Local acceptance clause: Control variant studies. Register and verify one-factor changes, frozen question sets, qrel versions and real execution evidence. Produce at least one controlled improvement study when possible without redefining E1.
- Executed commands recorded by the ledger: `["python -m scripts.verify.all --mode mock"]`
- Additional legacy command field: None recorded.
- Check implementations (existence alone is not an executed result): [tests/unit/test_retrieval.py](<../../../tests/unit/test_retrieval.py>), [tests/integration/test_corpus_runtime.py](<../../../tests/integration/test_corpus_runtime.py>)
- Recorded current check nodes: `["tests.integration.test_corpus_runtime::test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "tests.integration.test_corpus_runtime::test_quarantine_inspectable_exclusion_and_processing_lineage", "tests.integration.test_corpus_runtime::test_reprocessing_creates_new_chunks_while_old_evidence_survives", "tests.integration.test_corpus_runtime::test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "tests.integration.test_corpus_runtime::test_processing_diff_reports_split_groups_by_overlapping_source_spans", "tests.integration.test_corpus_runtime::test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "tests.integration.test_corpus_runtime::test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "tests.integration.test_corpus_runtime::test_source_deactivation_filters_current_retrieval_and_restore_recovers", "tests.integration.test_corpus_runtime::test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks", "tests.integration.test_corpus_runtime::test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "tests.integration.test_corpus_runtime::test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest", "tests.integration.test_corpus_runtime::test_legacy_release_without_saved_hashes_requires_explicit_new_build", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[cancel]", "tests.integration.test_corpus_runtime::test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun[recover]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[cancel]", "tests.integration.test_corpus_runtime::test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors[recover]", "tests.unit.test_retrieval::test_mock_embedding_is_normalized_repeatable_and_content_sensitive", "tests.unit.test_retrieval::test_bm25_matches_hand_calculated_term_and_stable_ties", "tests.unit.test_retrieval::test_rrf_uses_one_based_ranks_and_never_raw_score_magnitudes", "tests.unit.test_retrieval::test_e5_actual_tokenizer_prefixes_dimension_and_no_silent_truncation", "tests.unit.test_retrieval::test_reranker_records_actual_spans_limits_candidate_count_and_validates_outputs"]`
- Acceptance references: [AC-19](<../acceptance.md#ac-19>), [AC-35](<../acceptance.md#ac-35>)
- Actual task evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [evidence/retrieval/post-recovery-comparison.json](<../../../evidence/retrieval/post-recovery-comparison.json>), [evidence/retrieval/post-recovery-summary.json](<../../../evidence/retrieval/post-recovery-summary.json>)
- Additional current test evidence record: `{"path": "evidence/final/pytest.xml", "run_completed_at": "2026-09-08T09:57:46.673999+00:00", "sha256": "c250166edda4d5d09c984e613f16c98727fb3e9ede02e6c6d71bbd8a710ba390"}`
- Evidence scope: Specific observed component behavior; not blanket satisfaction of every task acceptance clause.
- Current observation: R0/R1/R2/R3 executed against the same frozen official four-book chunk/vector set with real E5 and pinned cross-encoder inference. Controlled diagnostics retain all scheduled successes/errors, ranked source text, token windows, timings and rank differences.
- Unresolved scope: Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.
- Blockers: None recorded.
- Mapping limitation: Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.

Recorded component observations:

- observed task scope: `REAL_FLOW_VERIFIED`. R0/R1/R2/R3 executed against the same frozen official four-book chunk/vector set with real E5 and pinned cross-encoder inference. Controlled diagnostics retain all scheduled successes/errors, ranked source text, token windows, timings and rank differences.
  Evidence: [evidence/final/software_gate.json](<../../../evidence/final/software_gate.json>), [evidence/final/pytest.xml](<../../../evidence/final/pytest.xml>), [docs/retrieval_diagnostics.md](<../../retrieval_diagnostics.md>), [evidence/retrieval/post-recovery-comparison.json](<../../../evidence/retrieval/post-recovery-comparison.json>), [evidence/retrieval/post-recovery-summary.json](<../../../evidence/retrieval/post-recovery-summary.json>)
- remaining acceptance scope: `IMPLEMENTED_UNVERIFIED`. Ranking differences and latency observations do not establish relevance improvement without independent qrels. Interrupted and repeated schedules remain distinct; see the terminal reports.

Historical statuses and source-supported historical facts remain in the [canonical task record](<../../execution/tasks.json>); they are not replaced by this export.
