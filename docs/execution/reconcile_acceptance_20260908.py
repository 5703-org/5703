"""Evidence-backed acceptance observation; never changes IDs or expected text."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OBSERVATION = ROOT / "evidence/acceptance/observation-20260908-0825"
OBSERVATION.mkdir(parents=True, exist_ok=True)
for name in ("pytest.xml", "software_gate.json", "source_snapshot.json"):
    target = OBSERVATION / name
    if not target.exists():
        target.write_bytes((ROOT / "evidence/final" / name).read_bytes())
JUNIT = str((OBSERVATION / "pytest.xml").relative_to(ROOT)).replace("\\", "/")
GATE = str((OBSERVATION / "software_gate.json").relative_to(ROOT)).replace("\\", "/")
suite = ET.parse(OBSERVATION / "pytest.xml").getroot().find("testsuite")
assert suite is not None and suite.get("failures") == "0" and suite.get("errors") == "0"
passed_nodes = {}
for case in suite.findall("testcase"):
    if case.find("failure") is not None or case.find("error") is not None:
        continue
    name = case.attrib["name"].split("[")[0]
    passed_nodes[name] = case.attrib["classname"].replace(".", "/") + ".py::" + name

R = "REAL_FLOW_VERIFIED"
M = "MOCK_TEST_PASSED"
U = "IMPLEMENTED_UNVERIFIED"
W = "WAITING_EXTERNAL"
BROWSER = "artifacts/reports/frontend/openstax/2026-09-08T08-27-08-234Z/verification.json"
UI = "evidence/ui/legacy-mcq-component-tests.json"
RESTORE = "evidence/recovery/backup-real-openstax-20260908/restore-cs30_restore_openstax_portable_20260908.json"
E5 = "evidence/e5-container/verification.json"
SOURCE = "evidence/openstax/formal-source-validation-summary.json"
SCIQ = "evidence/sciq/projection-verification.json"
LEGACY = "evidence/legacy/generation_verification_copy/results/handoff/verification.json"
MANIFEST = "evidence/legacy/generation_manifest_audit.json"
FOUNDATION = "evidence/foundation/verification.json"
ROLLBACK = "artifacts/reports/frontend/openstax-rollback/2026-09-08T08-36-19-078Z/verification.json"
DATA = {}


def row(identifier, status, actual, tests=(), evidence=(), remaining=(), complete=True):
    assert identifier not in DATA
    DATA[identifier] = {
        "status": status,
        "actual": actual,
        "test_nodes": [passed_nodes[name] for name in tests],
        "evidence_paths": list(evidence) + ([JUNIT] if tests else []),
        "remaining_scope": list(remaining),
        "completion_claim": complete and not remaining,
    }


row("AC-01", M,
    "The saved clean Compose installation and browser rehearsal start real API/worker/PostgreSQL with explicit mock answers and authored mock embeddings. The ordinary runtime was rebuilt after the Dockerfile layer split and still runs without Torch; the optional E5 image is separate.",
    evidence=("artifacts/reports/frontend/clean-install-browser.json", "evidence/recovery/clean-chat.json", "evidence/e5-container/base-runtime-preflight.log"))
row("AC-02", R,
    "Actual initial-to-head PostgreSQL migrations preserve seeded rows; repeated head upgrade and repeated development seeding preserve account identity. CI setup creates a dedicated database and rejects a non-CI/non-test target before mutation. Demo accounts require explicit dev/test/demo seeding.",
    tests=("test_initial_data_and_typed_mcq_survive_additive_migrations", "test_operator_cli_uses_real_database_and_secret_environment"),
    evidence=("evidence/devtools/ci_setup_verification.json", "evidence/devtools/legacy_mcq_migration.log"))
row("AC-03", R,
    "PostgreSQL upload tests reject disguised/unsupported media, unsafe names, oversized content and recursive secret-bearing configuration; same-byte valid uploads remain usable. Actual official PDF originals are separately hashed and retained.",
    tests=("test_upload_type_path_limits_recursive_secrets_and_raw_dedup",), evidence=(SOURCE,))
row("AC-04", U,
    "Real quarantine, inspectable blockers, explicit exclusions and original issue retention pass. The recorded v4 four-book release includes attributed OCR/publisher recovery rather than silently dropping science pages. A later audit found front-matter section-label errors in v4; v5 processing/validation is being tracked separately.",
    tests=("test_quarantine_inspectable_exclusion_and_processing_lineage", "test_pdf_page_extraction_failure_preserves_other_pages_and_blocks_publication", "test_page_review_retains_original_issues_and_only_resolves_its_verified_scope"),
    evidence=(SOURCE, "docs/execution/audit-ai.md"),
    remaining=("Close the newer v5 source-label/reprocessing validation before treating the latest corpus-quality clause as final.", "Independent full-book visual/scientific certification is absent; agent-reviewed OCR does not establish it."))
row("AC-05", R,
    "Raw upload deduplication, distinct processing identities after rule changes, exact source spans and unchanged historical answer/evidence records pass against PostgreSQL. Actual four-book immutable runs and preserved backup hashes provide additional real-source evidence.",
    tests=("test_upload_type_path_limits_recursive_secrets_and_raw_dedup", "test_reprocessing_creates_new_chunks_while_old_evidence_survives"), evidence=(SOURCE, RESTORE))
row("AC-06", R,
    "Known-vector pgvector rankings and rejection of invalid/mixed vectors pass. The recorded real release has 10,584 finite 384-dimensional E5 vectors; the Linux CUDA probe generated a normalized real query vector and matched twenty ranked source hits against the host baseline. This is vector/runtime correctness, not relevance accuracy.",
    tests=("test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest"), evidence=(E5, SOURCE))
row("AC-07", M,
    "Both benchmark schemas execute E0 through the actual shared PostgreSQL worker with a retriever spy that must not be called. Frozen policies omit history/profile/evidence/gold; OpenQA has no choices and MCQ retains its separate candidates. Model calls in these checks are explicitly mock.",
    tests=("test_postgres_e0_both_schemas_never_call_retriever", "test_actual_role_order_profile_off_and_frozen_benchmark_boundary"))
row("AC-08", R,
    "The real four-book/E5/pgvector browser flow submits natural text, stores chat_response_v1 and inspects exact source text/hash, physical locator, publisher URL and license. Shared PostgreSQL tests trace persisted messages/context/profile/query/evidence/attempt/publication without requiring A-D input. Answer generation is an explicit extractive mock.",
    tests=("test_atomic_chat_context_and_current_evidence", "test_chat_message_never_requires_choices"), evidence=(BROWSER, E5),
    remaining=("Live answering-model correctness and general semantic groundedness are not evaluated; the observed flow uses mock answers.",))
row("AC-09", M,
    "Three actual unrelated-query candidate replays produce explicit mock insufficiency refusals; numbers and negation remain required, and question-only source extracts do not become asserted answers. Social and missing-referent turns remain valid. Retrieval/publication failures remain errors in runtime fault checks.",
    tests=("test_actual_unrelated_candidates_never_become_factual_answers", "test_numbers_and_negation_are_required_content", "test_actual_learning_objective_question_is_not_mistaken_for_an_answer", "test_database_failure_publishes_no_partial_answer"), evidence=(BROWSER, "docs/execution/mock-evidence-replay.md"),
    remaining=("Lexical mock coverage can abstain on supported synonyms/distant evidence and is not semantic entailment; no live sufficiency evaluation or independent human judgment is recorded.",))
row("AC-10", M,
    "Strict mode-specific parsing rejects malformed chat objects/citations and enforces exact original option text only for MCQ. Invalid-twice generation remains a schema error after the finite repair allowance; no arbitrary chat A-D extraction occurs.",
    tests=("test_strict_json_negatives", "test_schema_and_selected_source_negatives", "test_mcq_preserves_original_option_text_for_exact_output_comparison", "test_invalid_twice_is_error_not_refusal_and_retry_retains_budget"))
row("AC-11", M,
    "Injected HTTP429/5xx/401/timeout and invalid-output cases obey the shared finite call/repair/time budget. The previously reported regeneration-default-budget defect is covered by a passing PostgreSQL regression preserving configured caps and blocking benchmark retry/regenerate through the chat path.",
    tests=("test_provider_http_metadata_and_retryability", "test_shared_four_call_budget_covers_transient_and_one_format_repair", "test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked"))
row("AC-12", R,
    "Actual concurrent PostgreSQL submissions with the same idempotency key produce one logical user turn/job; changed bodies conflict. Optimistic profile/session updates reject stale versions. UI components preserve the idempotency key after a lost response and deduplicate rapid submissions.",
    tests=("test_simultaneous_duplicate_submit_and_optimistic_updates", "test_idempotency_busy_and_forbidden_fields"), evidence=(UI,))
row("AC-13", U,
    "PostgreSQL stale-claim, cancellation, parser/index and teaching recovery tests fence late publication and retain consumed budgets. The Docker transport outage caused a real database/worker interruption and preserved failed diagnostics; it was not a controlled proof of every in-flight worker restart branch.",
    tests=("test_stale_recovery_preserves_exhausted_budget", "test_cancel_during_provider_call_fences_late_output", "test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun", "test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors", "test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result"),
    evidence=("evidence/e5-container/database-after-export-state.json", "docs/retrieval_diagnostics.md"),
    remaining=("Finish and retain the final controlled worker-process interruption/restart walkthrough with its terminal job outcomes; do not infer it from state-injection tests or the shared Docker outage.",))
row("AC-14", R,
    "Owned-session/account/admin boundaries and source deactivation/revocation pass in PostgreSQL. Real source-visibility diagnostics retain current retrieval filtering and historical source unavailability semantics; the browser shows attributed sources without granting administration to learners.",
    tests=("test_ownership_archive_and_new_session_isolation", "test_source_deactivation_filters_current_retrieval_and_restore_recovers", "test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment"), evidence=("evidence/openstax/retrieval-verification.json", BROWSER))
row("AC-15", R,
    "Actual PostgreSQL version conflicts, profile-off/history separation, immutable in-flight snapshots and failed replacement preservation pass. Real-browser profile-off and latest regeneration preserve the original answer/evidence/feedback; later snapshots are distinct.",
    tests=("test_profile_snapshot_conflict_and_profile_off_preserves_history", "test_latest_revision_preserves_feedback_and_failed_replacement"), evidence=(BROWSER,))
row("AC-16", R,
    "The recorded real-corpus browser flow restores ten messages after re-login and checks source keyboard interaction and feedback persistence. Separate lifecycle/browser and component tests cover Stop/retry, preserved drafts, lost responses and idempotent feedback; answer generation remains mock.",
    tests=("test_concurrent_first_feedback_save_reuses_one_record_and_keeps_review_editable",),
    evidence=(BROWSER, UI, "artifacts/reports/frontend/stop-retry.json", "artifacts/reports/frontend/no-sciq-journey.json"))
row("AC-17", R,
    "All 13,679 actual pinned official SciQ rows passed stem-only OpenQA projection and private-reference perturbation checks. Deterministic MCQ projection retains 13,631 valid rows and all 48 native normalized-duplicate-choice anomalies in the preflight denominator; no options are invented or silently dropped. Provider inputs and the corpus remain gold-free.",
    tests=("test_stem_projection_unchanged_when_private_labels_change", "test_mcq_shuffle_is_stable_symmetric_and_gold_stays_private", "test_duplicate_source_choices_do_not_block_stem_only_openqa_freeze", "test_lossless_parquet_unicode_and_all_item_public_preflight_boundary"), evidence=(SCIQ, "evidence/sciq/software-verification.json"))
row("AC-18", M,
    "Runner freeze/resume/cancel/ambiguous-receipt tests preserve every scheduled denominator. Hand-calculated EM/F1, MCQ, graded retrieval and paired-statistic fixtures pass, and conversation turns cluster by authored scenario. OpenQA compact answers are not replaced with whole explanations.",
    tests=("test_freeze_preregisters_and_resume_does_not_repeat_calls", "test_failed_cancelled_and_refused_rows_keep_scheduled_denominator", "test_retrieval_uses_actual_returned_denominator_and_graded_ndcg", "test_exact_binary_discordants_and_continuous_paired_intervals", "test_turns_cluster_by_scenario_without_invalid_per_turn_mcnemar"),
    remaining=("Formal live OpenQA/MCQ effectiveness runs and reviewed relevance qrels are absent; the passing fixtures validate calculations and denominator handling only.",))
row("AC-19", W,
    "Immutable manifests, private-reference tamper rejection, single-factor comparisons, blinded templates and null missing-rating handling pass locally. Actual R0-R3 diagnostic scheduling retains its interrupted run instead of cherry-picking; local diagnostic ranks are not relevance scores.",
    tests=("test_tampered_manifest_or_private_reference_rejected", "test_controlled_comparisons_reject_test_tuning_and_multiple_changes", "test_missing_ratings_remain_null_and_pairs_use_questions", "test_duplicate_and_failed_output_ratings_are_rejected"), evidence=("docs/retrieval_diagnostics.md", "docs/execution/audit-evaluation.md"),
    remaining=("Independent qrels and blinded human ratings have not been supplied or collected.", "User-deferred live-model experimental outputs and their paired research analysis remain absent."))
row("AC-20", U,
    "Actual backup-v2 restore into a distinct portable PostgreSQL database preserved identity/profile values, complete corpus fingerprints, active pointer, seven originals and 44 recovery artifacts. Linux independently resolved source paths/hashes and retrieved the same E5 release read-only. The prior absolute-Windows-path restore is retained as a diagnosed attempt.",
    evidence=(RESTORE, E5, "evidence/e5-container/absolute-source-path-attempt.json"),
    remaining=("The final distributable package has not yet been created and inspected for credentials, evaluator gold, allowed source content and complete install instructions.",))
row("AC-21", U,
    "The canonical registry retains all 108 task IDs/60 checks and validated dependency structure. G4 conversation/profile/evidence runs without a completed benchmark or ratings study. The latest recorded real-corpus browser journey passes, while the final administrator A-B-A rollback and stable aggregate source snapshot are still pending.",
    evidence=(FOUNDATION, BROWSER, GATE, ROLLBACK),
    remaining=("Close the final all-six-journey release regression, including the actual administrator rollback flow.", "Run the final aggregate gate on a stable source snapshot; the captured 222-test run passed tests but failed the source-drift guard."))
row("AC-22", M,
    "Actual PostgreSQL chat, OpenQA, MCQ and teaching orchestration use the shared answer/generation/retrieval/persistence implementation. Mode-specific frozen policies and typed outputs remain distinct; shared-backend tests verify the real model parameters and public receipts with mock generation.",
    tests=("test_postgres_frozen_runner_resume_preserves_receipts_and_actual_parameters", "test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold", "test_actual_role_order_profile_off_and_frozen_benchmark_boundary"))
row("AC-23", R,
    "A freshly built ordinary runtime image contains no evaluation package, evaluator-private dataset store, originals or model cache. Base API/worker mounts exclude SciQ private files; the evaluator profile alone mounts private references. PostgreSQL frozen-submit tests reject changed hashes/gold injection and public models contain no gold fields.",
    tests=("test_registered_hash_rejects_post_freeze_question_or_gold_injection", "test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment"), evidence=("evidence/e5-container/runtime-data-boundaries.log", "evidence/sciq/software-verification.json"))
row("AC-24", R,
    "Actual tail retry and late-publication fencing preserve one user message, prior terminal attempts and cumulative counters. The explicit regression now prevents generic chat retry/regeneration from bypassing frozen benchmark lifecycle rules; failed non-tail turns cannot replace later dialogue.",
    tests=("test_cancel_retry_and_stale_publication", "test_provider_format_repair_counts_survive_retry", "test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked"))
row("AC-25", M,
    "Reserve-before-call budgets persist across transient retries, one format repair, cancelled/stale work and regenerated chat. Configured initial caps are preserved instead of defaulted on regeneration. Independent teaching jobs retain charged budget and do not force a second ordinary chat call.",
    tests=("test_shared_four_call_budget_covers_transient_and_one_format_repair", "test_provider_format_repair_counts_survive_retry", "test_stale_recovery_preserves_exhausted_budget", "test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked", "test_postgres_teaching_stale_claim_retains_charged_budget_and_fences_late_result"))
row("AC-26", U,
    "PostgreSQL A-B-A pointer validation and rejection of failed/missing/invalid releases pass, including exact cached-float32 preservation. The real administrator browser rollback attempts are retained; the current recorded 08:36 attempt is not a completed pass and must not be promoted from backend coverage alone.",
    tests=("test_failed_index_preserves_pointer_cache_and_a_b_a_rollback", "test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest"), evidence=(ROLLBACK, "evidence/retrieval/cache-precision-verification.json"),
    remaining=("Complete the final real-browser A-to-validated-B-to-A flow and confirm exactly one final active pointer with old evidence preserved.",))
row("AC-27", M,
    "Frozen-run source/environment changes stop new calls while retaining prior success and all scheduled rows. PostgreSQL tests also revoke sources after teaching generation and reject late publication; changed prompt/rubric environments terminate remaining study calls without silent substitution.",
    tests=("test_environment_change_stops_new_calls_preserves_scheduled_set", "test_postgres_public_freeze_rejects_hash_and_stops_revoked_environment", "test_postgres_teaching_late_source_revocation_discards_publication", "test_study_prompt_or_rubric_environment_change_stops_remaining_calls"))
row("AC-28", R,
    "Repeated raw bytes reuse the original asset version, while revised chunking rules create new processing identities. Exact span-based processing diffs distinguish UUID-only changes, split/merged groups and exclusions; old answer/evidence remains unchanged. Qrel compatibility is checked rather than automatically transferring labels.",
    tests=("test_reprocessing_creates_new_chunks_while_old_evidence_survives", "test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids", "test_processing_diff_reports_split_groups_by_overlapping_source_spans", "test_qrels_require_actual_review_identity_and_frozen_sources"), evidence=(RESTORE,))
row("AC-29", M,
    "The main chat call receives the explicit profile policy once. Separate PostgreSQL teaching jobs freeze all nine C0-C2/level combinations and preserve the base answer, citations and scheduled denominator when a study job fails, cancels or is revoked. Mock study output is not a demonstrated pedagogical benefit.",
    tests=("test_postgres_teaching_api_nine_matched_jobs_and_blind_export_without_chat_mutation", "test_postgres_teaching_cancel_keeps_success_and_all_scheduled_outcomes", "test_three_by_three_study_freezes_base_and_evidence_and_c0_hides_level"),
    remaining=("Matched live teaching outputs and independent correctness/groundedness/level ratings remain deferred; no learning-gain claim is supported.",))
row("AC-30", R,
    "Actual profile-off chat keeps owned-session history and evidence context; benchmarks clear both by policy. Temporary simpler/example requests do not rewrite stored learner level. PostgreSQL snapshots, spy prompts and the real four-book browser profile-off journey all retain this separation.",
    tests=("test_profile_snapshot_conflict_and_profile_off_preserves_history", "test_actual_role_order_profile_off_and_frozen_benchmark_boundary", "test_temporary_override_does_not_mutate_saved_profile_and_off_keeps_no_profile_policy"), evidence=(BROWSER,))
row("AC-31", R,
    "Documented CLI and actual account endpoints provision/disable/reset accounts, enforce role/version constraints and revoke prior credential versions. Concurrent first account creation returns one success/one conflict without partial profile rows; browser password/token behavior is recorded.",
    tests=("test_operator_cli_uses_real_database_and_secret_environment", "test_account_credential_revocation_and_admin_reset", "test_concurrent_account_creation_returns_conflict_without_partial_profile"), evidence=("artifacts/reports/frontend/account-security.json",))
row("AC-32", R,
    "Actual browser feedback reaches the administrator review workflow and reloads saved notes/state. The two-thread PostgreSQL first-save regression preserves one feedback row and leaves it reviewable; model/profile state does not change automatically. The earlier unverified first-insert race is now specifically tested.",
    tests=("test_concurrent_first_feedback_save_reuses_one_record_and_keeps_review_editable",), evidence=(BROWSER, "artifacts/reports/frontend/admin-feedback.json"))
row("AC-33", U,
    "Real cleanup dry-run/apply rejects changed bytes and root escapes and preserves referenced originals. The operator CLI runs against a dedicated actual database; portable restore preserves source hashes. Worker stuck/cancelled recovery has separate integration coverage.",
    tests=("test_cleanup_dry_run_and_apply_preserve_referenced_bytes", "test_cleanup_rejects_changed_file_and_root_escape", "test_operator_cli_uses_real_database_and_secret_environment", "test_stale_recovery_preserves_exhausted_budget"), evidence=(RESTORE,),
    remaining=("Record the combined disposable operator walkthrough for an orphan, a stuck job, explicit retry/failure and unavailable restored evidence; separate component tests do not establish that whole scenario.",))
row("AC-34", U,
    "PDF/TXT parsing and behaviorally distinct mock/compatible-HTTP adapter branches are exercised through shared interfaces. Actual pgvector R0 and BM25 R1 dispatch plus real learned E5 image inference run without changing consumers. R0-R3 real diagnostics are separate from live answering-model replacement.",
    tests=("test_actual_pypdf_extracts_authored_bytes_with_physical_pages", "test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "test_http_adapter_sends_actual_roles_and_unknown_usage_remains_null"), evidence=(E5, "docs/retrieval_diagnostics.md"),
    remaining=("A configured real answer-provider end-to-end replacement drill is user-deferred; simulated HTTP responses do not establish current provider connectivity.",))
row("AC-35", R,
    "The application moved from its preserved authored mock-vector release to a separately built real E5 configuration/release while retaining old answer/evidence data. PostgreSQL tests reject mixed dimensions and finite corrupted cache values and preserve exact compatible float32 reuse. Linux executes the unchanged pinned E5 configuration against restored vectors.",
    tests=("test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors", "test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes", "test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest"), evidence=(E5, RESTORE, "evidence/corpus/e5_verification.json"))
row("AC-36", R,
    "Strict three-mode DTOs reject learner-supplied trusted/gold/context fields. Actual official SciQ projection emits only stems for OpenQA and four distinct candidates for valid MCQ rows; shared PostgreSQL benchmark execution stores typed outcomes without dialogue/profile/gold. Interactive chat remains natural text.",
    tests=("test_learner_cannot_supply_trusted_or_evaluator_fields", "test_mcq_requires_exact_four_labels_and_normalized_distinct_options", "test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold"), evidence=(SCIQ, BROWSER))
row("AC-37", R,
    "The recorded product browser journey runs login, natural-language chat, profile/history and sources with evaluator services absent. Actual real-book/E5 chat also works independently of official SciQ acquisition. Runtime image/mount inspection shows no evaluator gold path; readiness remains mode-specific.",
    evidence=(BROWSER, "artifacts/reports/frontend/no-sciq-journey.json", "evidence/e5-container/runtime-data-boundaries.log", "evidence/contracts/chat_scope.json"))
row("AC-38", R,
    "The real four-book browser flow asks photosynthesis then the dependent light question and inspects stored conversation/evidence. Prepared-query tests use actual prior user messages and expose no guessed answer; evidence-sensitive generation tests verify the resulting prompt/query and current citations. Answer generation is mock.",
    tests=("test_query_has_actual_referent_and_no_guessed_answer", "test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up", "test_actual_role_order_profile_off_and_frozen_benchmark_boundary"), evidence=(BROWSER,))
row("AC-39", R,
    "The latest real-browser new session asks an ambiguous question, supplies the named topic, requests its sources and greets the assistant. Clarification/social outputs use ChatResponseV1 without fake choices/citations; the subsequent clarification remains in the same saved conversation.",
    tests=("test_social_and_clarification_have_no_compact_factual_answer", "test_learner_correction_completes_an_ambiguous_turn_with_the_named_topic"), evidence=(BROWSER,))
row("AC-40", M,
    "Explicit new-topic requests retrieve new evidence, and their later resolved follow-up reuses that topic rather than an older one. Local-clause subject and correction tests pass; the real browser switches from photosynthesis to glycolysis. Prior assistant text is contextual history, not automatically verified source evidence.",
    tests=("test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic", "test_new_topic_comparison_correction_and_explicit_example", "test_local_clause_subject_is_not_replaced_with_an_old_session_topic"), evidence=(BROWSER,),
    remaining=("Arbitrary natural-language correction and scientific entailment outside the tested rules/mock cases are not established by these fixtures.",))
row("AC-41", R,
    "Actual simpler/example follow-ups retain the source-backed topic in the real browser. PostgreSQL evidence-reuse tests enforce actual source text/current local IDs and new-topic separation; revoked source checks stop reuse/publication rather than rebinding an old ev_001 to unrelated text.",
    tests=("test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic", "test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up", "test_postgres_teaching_late_source_revocation_discards_publication"), evidence=(BROWSER,))
row("AC-42", M,
    "Attributable non-overlapping older-prefix summaries persist in PostgreSQL, while revision changes invalidate summaries and deterministic failure retains bounded recent history with an explicit lost-prefix record. Generation budgets count history/profile/schema/output and drop whole evidence chunks. Useful long-range semantics are only sampled by authored fixtures.",
    tests=("test_long_context_summary_is_persisted_and_attributable", "test_long_history_summary_is_attributable_and_nonoverlapping", "test_summary_revision_or_content_change_invalidates", "test_summary_failure_keeps_bounded_recent_history_and_records_lost_prefix", "test_context_budget_includes_profile_schema_and_output_and_drops_whole_chunks"),
    remaining=("Independent long-conversation semantic/reference-retention assessment is absent; no general memory-quality claim is made.",))
row("AC-43", R,
    "Actual re-login restores the same real-corpus session and selected answer revisions. PostgreSQL rejects other-user sessions and keeps new sessions free of prior transcript/summary; explicit profile policy is separate. New-session ambiguity in the browser confirms no accidental old-topic resolution.",
    tests=("test_ownership_archive_and_new_session_isolation", "test_context_ownership_cutoff_revisions_and_completed_pairs"), evidence=(BROWSER, "artifacts/reports/frontend/session-controls.json"))
row("AC-44", U,
    "Real endpoint/browser evidence covers saved terminal answers, keyboard citations, copy, profile controls, stop/retry and re-login; 23 component tests cover Enter/Shift+Enter/IME event handling, lost responses, failure drafts, focus and legacy output. Eleven real-browser widths and earlier zoom/stress/touch probes are recorded separately.",
    evidence=(BROWSER, UI, "artifacts/reports/frontend/stop-retry.json", "artifacts/reports/frontend/keyboard-zoom-probe.json", "artifacts/reports/frontend/stress-layout.json", "artifacts/reports/frontend/touch-controls.json"),
    remaining=("Actual physical-mobile keyboard/orientation/native OS IME/screen-reader and independent human-usability checks remain external.", "The latest corpus browser run does not itself repeat every earlier native-zoom/stress/touch/UI arrival case; retain their separate dates and scopes."))
row("AC-45", R,
    "The latest real-corpus browser and PostgreSQL regressions preserve old answer/evidence/feedback through regeneration, retain the original on failed replacement, and select only the latest successful revision for later prompts. Concurrent request deduplication and non-tail restrictions are tested.",
    tests=("test_latest_revision_preserves_feedback_and_failed_replacement", "test_simultaneous_duplicate_submit_and_optimistic_updates", "test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked"), evidence=(BROWSER,))
row("AC-46", R,
    "All actual official SciQ stems have evaluator-private references separated from public commands; changing labels/support does not change projected inputs. Shared PostgreSQL OpenQA execution emits ChatResponseV1 without options/history/profile/gold, while MCQ uses its own candidate schema. The 48 native invalid MCQ rows stay explicit in preflight.",
    tests=("test_stem_projection_unchanged_when_private_labels_change", "test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold", "test_postgres_e0_both_schemas_never_call_retriever"), evidence=(SCIQ,),
    remaining=("A live SciQ answering-model effectiveness run has not been performed; source projection and mocked shared execution are the observed boundaries.",))
row("AC-47", M,
    "Metric tests preserve negation/signs/units/repetition, require a compact answer and reject whole-explanation scoring; MCQ exact option selection and conversation-cluster statistics remain separate. Missing qrels/ratings are null and lexical mock coverage is explicitly not semantic correctness.",
    tests=("test_multiset_f1_preserves_negation_signs_units_and_repetition", "test_full_explanation_is_never_used_as_compact_answer", "test_mcq_requires_selected_option_text_not_only_label", "test_unavailable_qrels_and_zero_idcg_are_not_fabricated_zeros", "test_missing_independent_ratings_are_not_zero_or_passed"),
    remaining=("Independent full-response semantic review and legitimate-paraphrase correctness judgments are absent; lexical scores alone do not close those research clauses.",))
row("AC-48", U,
    "The actual initial PostgreSQL schema preserves account/profile/session/outbox rows. Selected and refused MCQ records are inserted at the first real answer-table revision, then survive additive upgrades with exact options, citations and old history; new chat uses no choices. Twenty-three UI tests include selected/refused legacy MCQ rendering. Original diagrams and ledgers are explicitly source-audited.",
    tests=("test_initial_data_and_typed_mcq_survive_additive_migrations",),
    evidence=("evidence/devtools/legacy_mcq_migration.log", UI, "docs/execution/source-architecture-audit.md", "evidence/contracts/verification.json", GATE),
    remaining=("Final 108-task/spec/package reconciliation and stable-source aggregate gate are still being completed; this row does not certify an uncreated package or blanket project completion.",))

row("HC-01", M,
    "Fresh original-handover manifest checks validated 30 PACKAGE and 21 SOURCE entries. The untouched copied handover verifier ran under Python3.13.2 with -B -S:39 original tests and two valid mock rows passed, with zero live calls. This is a recorded fresh rerun, distinct from preserved historical logs.",
    evidence=(MANIFEST, LEGACY))
row("HC-02", M,
    "The adapted project includes versioned prompts, canonical schemas, authored fixtures, runner/annotation scripts and regression tests; legacy assets remain preserved separately. The clean Compose runtime and evaluator/shared-PostgreSQL tests use one generation service rather than a parallel answer engine.",
    tests=("test_actual_shared_worker_persists_typed_benchmark_without_dialogue_or_gold",), evidence=(MANIFEST, "evidence/recovery/clean-chat.json", "docs/foundation/handover_migration.md"))
row("HC-03", R,
    "Current prompts have no OPTION_A runtime hook; canonical DTO/spy tests reject private gold/evidence-status injection and preserve symmetric candidate formatting. Whole-official-SciQ projection checks perturb evaluator-only reference data without changing any public OpenQA/MCQ command.",
    tests=("test_stem_projection_unchanged_when_private_labels_change", "test_mcq_shuffle_is_stable_symmetric_and_gold_stays_private", "test_actual_role_order_profile_off_and_frozen_benchmark_boundary"), evidence=(SCIQ, "evidence/contracts/chat_scope.json"))
row("HC-04", M,
    "Natural-language chat requires no choices. MCQ alone enforces exactly four distinct normalized candidates while preserving the original option text for output equality. Stored selected/refused MCQ records remain mode-discriminated in API and component rendering.",
    tests=("test_chat_message_never_requires_choices", "test_mcq_requires_exact_four_labels_and_normalized_distinct_options", "test_mcq_preserves_original_option_text_for_exact_output_comparison", "test_initial_data_and_typed_mcq_survive_additive_migrations"), evidence=(UI,))
row("HC-05", M,
    "Parameterized strict-parser and canonical-model tests reject duplicate keys, fences, multiple/trailing objects, nonfinite constants, wrong null/types and extras while retaining valid prose objects and stable error categories.",
    tests=("test_strict_json_negatives", "test_schema_and_selected_source_negatives", "test_chat_rejects_invalid_confidence"))
row("HC-06", M,
    "Chat refusal and legacy MCQ refusal keep their separate enums and empty/null/citation invariants with confidence=null. Repeated schema failure is an error after bounded repair, not a fabricated refusal.",
    tests=("test_refusal_has_distinct_empty_and_null_invariants", "test_legacy_mcq_refusal_enum_is_separate_from_chat", "test_invalid_twice_is_error_not_refusal_and_retry_retains_budget"))
row("HC-07", M,
    "Complete-looking JSON with finish_reason=length is neither published nor repaired. Empty/malformed provider choices/message/content return typed provider errors instead of IndexError; these are controlled transport responses, not live calls.",
    tests=("test_complete_json_with_length_finish_never_publishes_or_repairs", "test_provider_empty_and_truncated_envelopes"))
row("HC-08", M,
    "Local injected429/Retry-After/5xx/auth/timeout responses preserve provider HTTP/request metadata and retryability. Shared aggregate call caps cover retries and one repair; persisted PostgreSQL counters survive retry/stale recovery without hidden provider switching.",
    tests=("test_provider_http_metadata_and_retryability", "test_shared_four_call_budget_covers_transient_and_one_format_repair", "test_provider_format_repair_counts_survive_retry", "test_stale_recovery_preserves_exhausted_budget"))
row("HC-09", M,
    "Spy prompts observe system, actual prior turns and current user in order; current citations point to exact supplied text/hash. Benchmark gold/evidence-status fields cannot decide runtime sufficiency. Profile-off keeps dialogue context, with additional real-browser evidence for the same policy.",
    tests=("test_actual_role_order_profile_off_and_frozen_benchmark_boundary", "test_http_adapter_sends_actual_roles_and_unknown_usage_remains_null", "test_profile_snapshot_conflict_and_profile_off_preserves_history"), evidence=(BROWSER,))
row("HC-10", M,
    "Invalid-then-valid and repeatedly invalid adapter outputs execute through the shared application/worker service. One repair and persistent cumulative counters are enforced, with one final publication or a terminal error; runtime repair does not invoke the legacy CLI run_case helper.",
    tests=("test_provider_format_repair_counts_survive_retry", "test_invalid_twice_is_error_not_refusal_and_retry_retains_budget", "test_database_failure_publishes_no_partial_answer"))
row("HC-11", M,
    "Configuration validation rejects missing/invalid live-provider settings without a mock fallback, while explicit mock operation remains separately labelled. Original provider probe records and example configurations are preserved as historical/examples, not current connectivity proof.",
    tests=("test_live_defaults_and_e1_redefinition_are_rejected", "test_provider_http_metadata_and_retryability"), evidence=("docs/foundation/handover_migration.md",),
    remaining=("Current live provider credentials/connectivity and paid or hosted model evaluation remain user-deferred.",))
row("HC-12", M,
    "Original authored20-item fixtures, two mock rows and forty failed diagnostics retain their handover identities. New evaluator runs use separate frozen directories and preserve scheduled, refused, cancelled, ambiguous and failed rows through resume/export; no historical week5 result is overwritten.",
    tests=("test_freeze_preregisters_and_resume_does_not_repeat_calls", "test_interrupted_submission_reconciles_receipt_without_new_call", "test_ambiguous_unrecorded_submission_never_automatically_repeats", "test_cancelled_export_retains_denominator_and_has_no_private_reference"), evidence=(MANIFEST, LEGACY, "docs/execution/audit-evaluation.md"))


def main():
    path = ROOT / "docs/execution/acceptance.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))
    original_identity = [(item["check_id"], item["expected"]) for item in ledger["checks"]]
    assert set(DATA) == {item[0] for item in original_identity} and len(DATA) == 60
    now = datetime.now(timezone.utc).isoformat()
    report = {"observed_at": now, "rows": [], "missing_paths": [], "baseline_test_count": int(suite.get("tests")), "aggregate_gate_status": "failed_source_drift", "project_complete": False}
    model_rows = {"AC-08", "AC-14", "AC-15", "AC-16", "AC-30", "AC-37", "AC-38", "AC-39", "AC-41", "AC-43", "AC-45"}
    for item in ledger["checks"]:
        identifier = item["check_id"]
        change = deepcopy(DATA[identifier])
        for evidence in change["evidence_paths"]:
            if not (ROOT / evidence).exists():
                report["missing_paths"].append(evidence)
        historical = {key: deepcopy(item[key]) for key in ("status", "actual", "evidence_paths", "actual_commands", "executed_at", "reconciled_at", "completion_claim", "remaining_scope", "component_statuses") if key in item}
        item.setdefault("reconciliation_history", []).append({"superseded_by": "20260908_final_local_evidence_observation", "observation": historical})
        item.update(change)
        item["reconciled_at"] = now
        item["executed_at"] = None  # Reconciliation itself does not rerun a scenario.
        item["actual_commands"] = (["python -m pytest tests -q --junitxml=evidence/final/pytest.xml"] if change["test_nodes"] else [])
        item["verification_note"] = "This audit reads the cited actual artifacts and named passing JUnit nodes; it does not relabel them as new executions. The 222-test observation passed every test but its aggregate gate failed only the source-drift guard. Final stable-source gate is pending."
        item["component_statuses"] = [{"component": "cited acceptance scope", "status": change["status"], "detail": change["actual"]}]
        if identifier in model_rows:
            item["component_statuses"].append({"component": "answer generation in the cited real product flow", "status": M, "detail": "Explicit mock answer provider; real sources/E5/PostgreSQL/browser do not imply a live answering model."})
        if identifier in {"AC-19", "AC-29", "AC-47"}:
            item["component_statuses"].append({"component": "independent human/research judgment", "status": W, "detail": "No independent relevance qrels, blind ratings or live answer-quality claim is supported."})
        report["rows"].append({"check_id": identifier, "status": item["status"], "test_nodes": item["test_nodes"], "remaining_scope": item["remaining_scope"]})
    assert not report["missing_paths"], report["missing_paths"]
    assert original_identity == [(item["check_id"], item["expected"]) for item in ledger["checks"]]
    ledger["reconciled_at"] = now
    ledger["reconciliation_phase"] = "final_local_evidence_observation_stable_gate_package_new_corpus_revision_pending"
    ledger["project_complete"] = False
    ledger["acceptance_observation"] = {
        "evidence": "evidence/acceptance/final-local-reconciliation.json",
        "tests": JUNIT,
        "aggregate_gate": GATE,
        "recorded_tests_passed": int(suite.get("tests")),
        "stable_source_gate": "pending; all captured commands passed but scripts/verify/e5_container.py changed during the captured aggregate run",
        "current_corpus_note": "The cited v4 real release and portable restore are recorded snapshots. New v5 front-matter labeling runs and final administrator rollback are tracked separately; their completion is not inferred here.",
        "external_absence": "No live answering-model effectiveness study, independent qrels/blind ratings, physical mobile keyboard/OS IME/screen-reader or human usability sign-off is claimed.",
        "package": "Not yet created/verified at this observation.",
    }
    report["ids_and_expected_sha256"] = hashlib.sha256(json.dumps(original_identity, ensure_ascii=False).encode()).hexdigest()
    (ROOT / "evidence/acceptance/final-local-reconciliation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"checks": len(DATA), "expected_and_ids_preserved": True, "all_evidence_paths_exist": True, "baseline_tests": int(suite.get("tests")), "project_complete": False}))


if __name__ == "__main__":
    main()
