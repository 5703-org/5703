'use strict';
// Metadata admission only. The installed product/browser lifecycle stays unchanged.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const authorization = 'parent_dev89_independent32posts_2USD_quality_pages_20261012';
const pageIds = ['case10', 'case10b', 'case10c'];
const baseIds = ['case01', 'case03', 'case04', 'case05', 'case06', 'case07', 'case08', 'case09',
  'case01r', 'case03r', 'case04r', 'case05r'];
const descriptorKeys = ['schema', 'authorization', 'instance_id', 'kind', 'base_case_id', 'protocol_sha256',
  'question_id', 'question_sha256', 'base_scope_sha256', 'base_source_version_sha256',
  'instance_source_version_sha256', 'base_final_receipt_sha256', 'base_api_closure_sha256',
  'qa_receipt_path', 'qa_receipt_sha256', 'actual_answer_sha256', 'root_selected_authorized',
  'automatic_replay_or_reclaim', 'repair_review_path', 'repair_review_sha256', 'base_journey_receipt_sha256'].sort();
const qaKeys = ['schema', 'status', 'independent_answer_QA', 'case_id', 'question_sha256', 'scope_sha256',
  'source_version_sha256', 'teacher_config_sha256', 'checker_config_sha256', 'output_policy', 'actual_ids',
  'actual_journey_sha256', 'raw_public_DTO_sha256', 'answer_text_sha256_UTF8', 'clock', 'flags',
  'actual_page_response_requires_independent_review_again', 'actual_page_latency_sample_qualified'].sort();
const flagKeys = ['scientific_correctness', 'coverage_complete', 'citations_valid', 'own_parent_sources_valid',
  'full_source_packet_reviewed', 'no_scientific_critical_error'].sort();
const oldMetadataGroups = ['sessions', 'jobs', 'answer_requests', 'answers', 'active_model_configurations'].sort();
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const sameKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
  && JSON.stringify(Object.keys(value).sort()) === JSON.stringify(keys);
function need(ok, code) { if (!ok) throw new Error(code); }

function validatePageBundle(runtime, stage, readPublic, publicDigest) {
  need(path.basename(runtime) === '5703-dev89-runtime' && pageIds.includes(stage), 'NEW_FINITE_DEV89_PAGE_REQUIRED');
  const freeze = readPublic('runtime-freeze88.json').value;
  const protocol = readPublic('protocol88.json');
  const pin = readPublic(`scope88-${stage}-pin.json`).value;
  const scoped = readPublic(`scope88-${stage}.json`);
  const scope = scoped.value;
  const descriptor = readPublic(`supplement88-${stage}.json`);
  const d = descriptor.value;
  const claim = readPublic(`${stage}/api-claim77.json`).value;
  need(protocol.sha256 === freeze.protocol_sha256 && pin.protocol_sha256 === protocol.sha256
    && protocol.value.schema === 'dev89_bound_development_validation_v1'
    && protocol.value.authorization === authorization && protocol.value.maximum_physical_posts === 32
    && protocol.value.cost_cap_USD === '2.00' && protocol.value.per_request_provider_calls_maximum === 4
    && scoped.sha256 === pin.scope_sha256 && pin.case_id === stage && scope.case_id === stage
    && scope.phase88_authorization === authorization && scope.phase88_case_execution_authorized === true
    && scope.continuation_phase === 'dev89' && scope.phase89_planned_kind === 'page'
    && scope.page_answer_requires_independent_quality_review === true
    && scope.cohort_protocol_sha256 === protocol.sha256 && d.protocol_sha256 === protocol.sha256
    && scope.supplement_descriptor_sha256 === descriptor.sha256, 'EXACT_DEV89_PAGE_SCOPE_REQUIRED');
  const selected = protocol.value.planned_instances?.filter(row => row.instance_id === stage);
  need(Array.isArray(selected) && selected.length === 1
    && sameKeys(selected[0], ['base_case_id', 'instance_id', 'kind', 'maximum_posts'])
    && selected[0].kind === 'page' && selected[0].base_case_id === null && selected[0].maximum_posts === 4
    && sameKeys(d, descriptorKeys) && d.schema === 'dev89_planned_instance_descriptor_v1'
    && d.instance_id === stage && d.authorization === authorization && d.kind === 'quality_qualified_page'
    && baseIds.includes(d.base_case_id) && d.root_selected_authorized === true
    && d.automatic_replay_or_reclaim === false && d.repair_review_path === null && d.repair_review_sha256 === null,
    'STRICT_PLANNED_PAGE_DESCRIPTOR_REQUIRED');
  need(typeof scope.question_text === 'string' && scope.question_text.length > 0 && scope.question_text.length <= 7200
    && sha(scope.question_text) === scope.question_sha256 && scope.question_sha256 === d.question_sha256
    && scope.question_id === d.question_id && claim.case_id === stage && claim.scope_sha256 === scoped.sha256
    && claim.supplement_descriptor_sha256 === descriptor.sha256 && claim.question_id === scope.question_id
    && claim.question_sha256 === scope.question_sha256
    && !fs.existsSync(path.join(runtime, stage, 'api-closure77.json')), 'NEW_PUBLIC_QUESTION_AND_API_CLAIM_REQUIRED');
  const base = readPublic(`scope88-${d.base_case_id}.json`);
  const journey = readPublic(`${d.base_case_id}/journey-receipt88.json`);
  const final = readPublic(`${d.base_case_id}/native-provider70/final-receipt.json`);
  const closure = readPublic(`${d.base_case_id}/api-closure77.json`);
  const qa = readPublic(d.qa_receipt_path);
  const sourceVersion = publicDigest(scope.source_pins);
  const withoutStorage = value => Object.fromEntries(Object.entries(value).filter(([key]) =>
    !['storage_root', 'visual_catalog_staging_root'].includes(key)));
  need(base.sha256 === d.base_scope_sha256 && base.value.case_id === d.base_case_id
    && base.value.question_text === scope.question_text && base.value.question_sha256 === scope.question_sha256
    && publicDigest(base.value.source_pins) === sourceVersion
    && sourceVersion === d.base_source_version_sha256 && sourceVersion === d.instance_source_version_sha256
    && publicDigest(base.value.expected_model_config) === publicDigest(scope.expected_model_config)
    && publicDigest(base.value.expected_checker_config) === publicDigest(scope.expected_checker_config)
    && publicDigest(withoutStorage(base.value.expected_settings)) === publicDigest(withoutStorage(scope.expected_settings))
    && publicDigest(scope.expected_model_config) === publicDigest(protocol.value.expected_model_config)
    && publicDigest(scope.expected_checker_config) === publicDigest(protocol.value.expected_checker_config)
    && publicDigest(withoutStorage(scope.expected_settings)) === publicDigest(protocol.value.frozen_settings)
    && scope.phase89_frozen_profile_sha256 === protocol.value.base_config_sha256,
    'SAME_QUESTION_SOURCE_AND_FROZEN_PROFILE_REQUIRED');
  need(final.sha256 === d.base_final_receipt_sha256 && closure.sha256 === d.base_api_closure_sha256
    && journey.sha256 === d.base_journey_receipt_sha256 && final.value.case_id === d.base_case_id
    && final.value.closure_status === 'CLOSED_NUMERIC_NO_UNKNOWN'
    && Number.isInteger(final.value.actual_posts) && final.value.actual_posts >= 1 && final.value.actual_posts <= 4
    && Number.isInteger(final.value.settled_numeric_cost_observations)
    && final.value.settled_numeric_cost_observations === final.value.actual_posts
    && ['string', 'number'].includes(typeof final.value.native_settled_known_cost_USD)
    && ['string', 'number'].includes(typeof final.value.native_unresolved_full_protection_USD)
    && Number.isFinite(Number(final.value.native_settled_known_cost_USD))
    && Number(final.value.native_settled_known_cost_USD) >= 0
    && Number.isFinite(Number(final.value.native_unresolved_full_protection_USD))
    && Number(final.value.native_unresolved_full_protection_USD) === 0
    && closure.value.owned_threads_closed === true && sameKeys(closure.value.old_metadata_unchanged, oldMetadataGroups)
    && Object.values(closure.value.old_metadata_unchanged).every(value => value === true)
    && journey.value.status === 'API_COMPLETED' && journey.value.API_n === 1 && journey.value.completed_answer_n === 1
    && journey.value.case_id === d.base_case_id && journey.value.scope_sha256 === base.sha256
    && journey.value.question_sha256 === scope.question_sha256 && journey.value.response?.response_type === 'answer'
    && typeof journey.value.response.answer_text === 'string' && journey.value.response.answer_text.trim(),
    'EXACT_CLOSED_BASE_ANSWER_REQUIRED');
  const expectedIds = { session_id: journey.value.session_id, answer_id: journey.value.answer_id,
    request_id: journey.value.accepted?.request_id, job_id: journey.value.accepted?.job_id,
    user_message_id: journey.value.accepted?.user_message_id };
  const expectedClock = { started_utc: journey.value.started_utc, finished_utc: journey.value.finished_utc,
    api_send_to_complete_response_ms: journey.value.api_send_to_complete_response_ms };
  need(sameKeys(qa.value, qaKeys) && qa.sha256 === d.qa_receipt_sha256
    && qa.value.schema === 'dev89_independent_actual_answer_eligibility_v1'
    && qa.value.status === 'PASS' && qa.value.independent_answer_QA === 'PASS' && qa.value.case_id === d.base_case_id
    && qa.value.question_sha256 === scope.question_sha256 && qa.value.scope_sha256 === base.sha256
    && qa.value.source_version_sha256 === sourceVersion
    && qa.value.teacher_config_sha256 === scope.page_base_teacher_config_sha256
    && qa.value.checker_config_sha256 === scope.page_base_checker_config_sha256
    && qa.value.raw_public_DTO_sha256 === scope.page_base_public_DTO_sha256
    && qa.value.raw_public_DTO_sha256 === d.actual_answer_sha256
    && qa.value.answer_text_sha256_UTF8 === sha(journey.value.response.answer_text)
    && qa.value.output_policy === base.value.expected_settings.chat_checker_output_policy
    && qa.value.actual_journey_sha256 === journey.sha256
    && publicDigest(qa.value.actual_ids) === publicDigest(expectedIds)
    && publicDigest(qa.value.clock) === publicDigest(expectedClock)
    && Number.isFinite(expectedClock.api_send_to_complete_response_ms) && expectedClock.api_send_to_complete_response_ms > 0
    && sameKeys(qa.value.flags, flagKeys) && Object.values(qa.value.flags).every(value => value === true)
    && qa.value.actual_page_response_requires_independent_review_again === true
    && qa.value.actual_page_latency_sample_qualified === false, 'INDEPENDENT_EXACT_BASE_ANSWER_QA_REQUIRED');
  // Numeric-domain-sensitive Python hashes above are pinned in the exact scope;
  // Python admission and budget rederive them from the retained base JSON.
  for (const row of scope.source_pins) {
    const filename = path.resolve(row.path);
    const main = path.resolve('E:/5703/learning-assistant');
    need(filename.toLowerCase().startsWith(`${main}${path.sep}`.toLowerCase())
      && !fs.lstatSync(filename).isSymbolicLink()
      && fs.realpathSync(filename).toLowerCase() === filename.toLowerCase(), 'CURRENT_MAIN_PIN_PATH_REQUIRED');
    const bytes = fs.readFileSync(filename);
    need(bytes.length === row.bytes && sha(bytes) === row.sha256, 'CURRENT_MAIN_VERSION_CHANGED');
  }
  const journal = path.join(runtime, 'cohort-ledger');
  const names = fs.readdirSync(journal);
  need(!names.includes('cohort-stop.json'), 'COHORT_PERMANENTLY_STOPPED');
  let count = 0;
  for (const name of names) {
    need(!/^post-(0[1-9]|[12][0-9]|3[0-2])-exposure\.json$/.test(name), 'UNSETTLED_PROTECTION_BLOCKS_PAGE');
    if (!/^post-(0[1-9]|[12][0-9]|3[0-2])-claim\.json$/.test(name)) continue;
    count += 1;
    need(names.includes(name.replace('-claim.json', '-settlement.json')), 'UNSETTLED_PROTECTION_BLOCKS_PAGE');
  }
  need(count + 4 <= 32, 'SHARED_32_POST_PAGE_HEADROOM_REQUIRED');
  return { freeze, protocol, pin, scoped, scope, descriptor, claim, qa };
}

module.exports = { validatePageBundle };
