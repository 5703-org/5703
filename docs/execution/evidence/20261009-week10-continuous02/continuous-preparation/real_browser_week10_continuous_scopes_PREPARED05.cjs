// PREPARED continuation of verified browser08; Root exclusively executes.
// Two normal reader-to-chat questions on one continuing synthetic B worker.
// Four new physical POSTs remain inside the approved cumulative USD0.24 ceiling.
// No launch/API/model/DB operation is performed by node --check.
// Exact current role qualification may be reused with zero new provider POSTs.
// This uses the public default R2/RRF plus MiniLM profile without an executor override.
// Profile binding alone does not establish actual reranker execution or RAG quality.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const os = require('node:os');

const ROOT = 'C:/Users/PC/Documents/Codex/2026-10-04/task-2/5703-week10-native-pair-20261009-01';
let BASE;
const MAX_PROVIDER_POSTS = 4, MIN_PROVIDER_SLOTS = 2, MAX_REQUEST_POSTS = 4;
const BATCH_RESERVE_SCALED = 12000000n;
const DEFAULT_PROFILE_PATH = 'E:/5703/learning-assistant/configs/retrieval/chat_hybrid_minilm.json';
const DEFAULT_PROFILE_SHA = '23ca72ddb737045259a04cbfc81c71969440f11cc2fa1a77bc7f8e7fc4364e17';
const HEX = /^[0-9a-f]{64}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const FINGERPRINTS = ['schema_hash', 'prompt_hash', 'configuration_hash', 'capability_hash', 'reserved_output_tokens', 'effective_parameters'];
const QUESTION_DEADLINE_MS = 300000;
const TOTAL_DEADLINE_MS = 720000;
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function bounded(promise, milliseconds, code) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Boundary(code)), milliseconds); })]); }
  finally { clearTimeout(timer); }
}
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
class Boundary extends Error { constructor(code) { super(code); this.code = code; } }
const requireTrue = (value, code) => { if (!value) throw new Boundary(code); };

function args() {
  const result = {};
  const allowed = new Set(['--fixture', '--base', '--out', '--budget-status', '--resume-receipt', '--startup-driver-receipt']);
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i], value = process.argv[i + 1];
    requireTrue(allowed.has(key) && value && !result[key], 'INVALID_OR_DUPLICATE_CLI_ARGUMENT');
    result[key] = value;
  }
  requireTrue(Object.keys(result).length === 6, 'SIX_EXPLICIT_CLI_ARGUMENTS_REQUIRED');
  BASE = result['--base'].replace(/\/$/, '');
  requireTrue(['http://127.0.0.1:15196','http://127.0.0.1:15197'].includes(BASE), 'EXACT_OWNED_WEEK10_LOOPBACK_BASE_REQUIRED');
  return result;
}

function ownedPath(value, { absent = false, privateFixture = false, publicSeed = false } = {}) {
  requireTrue(typeof value === 'string' && path.isAbsolute(value), 'ABSOLUTE_OWNED_PATH_REQUIRED');
  const p = path.resolve(value), root = path.resolve(ROOT), rel = path.relative(root, p);
  requireTrue(rel && !rel.startsWith('..') && !path.isAbsolute(rel), 'PATH_OUTSIDE_NEW_OWNED_ROOT');
  const parts = rel.split(path.sep);
  requireTrue(parts.every(part => !['.git', '.codex', '.env', 'week09-private-db', 'node_modules', '.venv'].includes(part.toLowerCase())), 'FORBIDDEN_PATH_COMPONENT');
  if (privateFixture) requireTrue(/^owned-(?:actor-)?auth-private[0-9]{2}\.json$/.test(path.basename(p)), 'EXACT_OWNED_AUTH_FIXTURE_NAME_REQUIRED');
  else if (publicSeed) requireTrue(/^ACTUAL_.*SEED.*RECEIPT.*\.json$/.test(path.basename(p)), 'EXACT_ACTUAL_PUBLIC_SEED_RECEIPT_REQUIRED');
  else requireTrue(parts.every(part => !/private|profile|cookie|header|fixture/i.test(part)), 'PRIVATE_INPUT_NOT_ALLOWED_AS_PUBLIC_PATH');
  let current = root;
  for (const part of ['', ...parts]) {
    if (part) current = path.join(current, part);
    if (absent && current === p && !fs.existsSync(current)) continue;
    requireTrue(!fs.lstatSync(current).isSymbolicLink(), 'SYMLINK_PATH_REJECTED');
  }
  return p;
}

function readJSON(value, maxBytes, privateFixture = false, publicSeed = false) {
  const p = ownedPath(value, { privateFixture, publicSeed });
  requireTrue(fs.statSync(p).isFile() && fs.statSync(p).size <= maxBytes, 'JSON_INPUT_BOUND_EXCEEDED');
  const bytes = fs.readFileSync(p);
  let data;
  try { data = JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/, '')); }
  catch { throw new Boundary('INVALID_JSON_INPUT'); }
  requireTrue(data && typeof data === 'object' && !Array.isArray(data), 'JSON_OBJECT_REQUIRED');
  return { data, pin: { path: p, bytes: bytes.length, sha256: sha(bytes) } };
}

function currency(value) {
  requireTrue(typeof value === 'string' && value.length <= 256 && /^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value), 'EXACT_PUBLIC_COST_DECIMAL_REQUIRED');
  const [whole, fraction = ''] = value.split('.');
  // Guard preserves Decimal's original fixed-point string. Round only this
  // comparison upward at 1e-8 USD, retaining the unmodified cost in the receipt.
  const scaled = BigInt(whole) * 100000000n + BigInt(fraction.padEnd(8, '0').slice(0, 8));
  return scaled + (/[1-9]/.test(fraction.slice(8)) ? 1n : 0n);
}

function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  return JSON.stringify(value);
}

let fixture, credentials = [];
function safe(value, limit = 32000) {
  let text = String(value);
  for (const secret of credentials) if (secret) text = text.split(secret).join('[OWNED_AUTH_REDACTED]');
  return text.replace(/Bearer\s+\S+/gi, 'Bearer [REDACTED]')
    .replace(/\b(?:sk-[A-Za-z0-9_-]{12,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b/g, '[CREDENTIAL_SHAPED_VALUE_REDACTED]').slice(0, limit);
}

function identityMatch(value, sourceSHA) {
  requireTrue(value.batch_id === fixture.batch_id && value.source_version === sourceSHA, 'PUBLIC_BATCH_OR_SOURCE_INDEX_IDENTITY_MISMATCH');
  for (const key of ['configuration_id', 'config_revision', 'config_hash', 'provider', 'model', 'openrouter_route_profile']) {
    requireTrue(value[key] === fixture[key], 'PUBLIC_LIVE_CONFIGURATION_IDENTITY_MISMATCH');
  }
}

function readDefaultProfile(pin) {
  requireTrue(pin && path.resolve(pin.path) === path.resolve(DEFAULT_PROFILE_PATH) && pin.bytes === 294 && pin.sha256 === DEFAULT_PROFILE_SHA, 'EXACT_PUBLIC_DEFAULT_PROFILE_PIN_REQUIRED');
  const file = path.resolve(DEFAULT_PROFILE_PATH);
  requireTrue(!fs.lstatSync(file).isSymbolicLink() && fs.statSync(file).isFile(), 'PUBLIC_DEFAULT_PROFILE_LINK_OR_TYPE_REJECTED');
  const bytes = fs.readFileSync(file);
  requireTrue(bytes.length === pin.bytes && sha(bytes) === pin.sha256, 'PUBLIC_DEFAULT_PROFILE_CHANGED');
  // This sole exact public configuration is the exception to owned input paths.
  // No user/browser profile, credentials, .env or arbitrary Main file is read.
  return { path: file, bytes: bytes.length, sha256: sha(bytes), scope: 'Configuration binding only; native execution proof is separate' };
}

function qualification(sourceSHA) {
  const ready = readJSON(fixture.readiness_public_path, 256000);
  const r = ready.data;
  requireTrue(r.schema === '5703_week10_native_pair_readiness_v1' && r.status === 'READY_FOR_LEARNER_QA' && r.ready === true, 'PUBLIC_LEARNER_READINESS_REQUIRED');
  identityMatch(r, sourceSHA);
  requireTrue(r.base_url === BASE && r.model_mode === 'live' && r.owned_synthetic_workspace === true, 'OWNED_LIVE_READINESS_REQUIRED');
  requireTrue(r.worker_startup_preparation_complete === true && r.worker_prewarm_retrieval_cache === fixture.worker_prewarm_retrieval_cache, 'ACTUAL_WORKER_STARTUP_READINESS_REQUIRED');
  requireTrue(r.worker_startup_preparation_public_path === fixture.worker_startup_preparation_public_path, 'EXACT_STARTUP_REPORT_PATH_REQUIRED');
  const startup = readJSON(fixture.worker_startup_preparation_public_path, 128000);
  requireTrue(startup.data.schema === '5703_week10_worker_startup_preparation_v1' && startup.data.status === 'PASS' && startup.data.batch_id === fixture.batch_id && startup.data.paired_leg_id === fixture.paired_leg_id && startup.data.source_version === sourceSHA && startup.data.same_Engine_as_native_run_once === true && startup.data.worker_prewarm_retrieval_cache === fixture.worker_prewarm_retrieval_cache, 'ACTUAL_BOUND_WORKER_STARTUP_PASS_REQUIRED');
  requireTrue(r.book_id === fixture.book_id && r.book_title === fixture.book_title && r.release_id === fixture.release_id, 'PUBLIC_BOOK_RELEASE_IDENTITY_MISMATCH');
  requireTrue(r.normal_role_qualification_passed === true && r.active_configuration_pointer_unchanged === true && r.active_corpus_pointer_unchanged === true, 'CURRENT_NORMAL_ROLES_AND_UNCHANGED_POINTERS_REQUIRED');
  requireTrue(canonical(r.qualification_roles) === canonical(['answer', 'checker']) && r.retrieval_variant === 'R2' && r.retrieval_binding === 'current_public_default_hybrid_minilm_v1' && r.native_current_default_bound === true && r.executor_override === false, 'EXACT_CURRENT_NATIVE_DEFAULT_BINDING_REQUIRED');
  const defaultProfilePin = readDefaultProfile(r.default_retrieval_profile_pin);
  const rp = r.role_qualification_receipt_pin;
  requireTrue(rp && HEX.test(rp.sha256) && Number.isSafeInteger(rp.bytes), 'PINNED_PUBLIC_ROLE_RECEIPT_REQUIRED');
  const role = readJSON(rp.path, 512000);
  requireTrue(role.pin.bytes === rp.bytes && role.pin.sha256 === rp.sha256, 'PUBLIC_ROLE_RECEIPT_PIN_MISMATCH');
  const q = role.data;
  requireTrue(q.schema === '5703_week10_native_pair_role_qualification_v1' && q.status === 'PASS', 'ACTUAL_ROLE_QUALIFICATION_PASS_REQUIRED');
  identityMatch(q, sourceSHA);
  requireTrue(q.provider_route === r.provider_route && typeof r.provider_route === 'string' && r.provider_route.length > 0, 'ACTUAL_PROVIDER_ROUTE_BINDING_REQUIRED');
  requireTrue(typeof q.reused_existing === 'boolean' && Number.isSafeInteger(q.newly_submitted_provider_posts) && q.newly_submitted_provider_posts >= 0 && q.newly_submitted_provider_posts <= 2, 'ACTUAL_ROLE_CALL_COUNT_REQUIRED');
  requireTrue(!q.reused_existing || q.newly_submitted_provider_posts === 0, 'REUSED_ROLES_CANNOT_INVENT_NEW_CALLS');
  requireTrue(Array.isArray(q.roles) && q.roles.length === 2 && new Set(q.roles.map(item => item.role)).size === 2, 'TWO_DISTINCT_NORMAL_ROLES_REQUIRED');
  for (const role of q.roles) {
    requireTrue(['answer', 'checker'].includes(role.role) && typeof role.run_id === 'string' && role.run_id.length > 0 && role.require_project_pass === true, 'ACTUAL_CURRENT_PROJECT_PASS_REQUIRED');
    requireTrue(role.current_fingerprints && role.stored_fingerprints, 'CURRENT_AND_STORED_ROLE_FINGERPRINTS_REQUIRED');
    for (const key of FINGERPRINTS) requireTrue(Object.hasOwn(role.current_fingerprints, key) && Object.hasOwn(role.stored_fingerprints, key) && canonical(role.current_fingerprints[key]) === canonical(role.stored_fingerprints[key]), 'SIX_ROLE_FINGERPRINTS_MUST_MATCH');
  }
  return { ready_pin: ready.pin, role_pin: role.pin, worker_startup_pin: startup.pin, worker_startup: startup.data, default_retrieval_profile_pin: defaultProfilePin, native_current_default_bound: true, executor_override: false, provider_route: r.provider_route,
    reused_existing: q.reused_existing, newly_submitted_provider_posts: q.newly_submitted_provider_posts,
    role_run_ids: q.roles.map(item => ({ role: item.role, run_id: item.run_id })) };
}

function budgetTelemetry(value, sourceSHA, providerRoute) {
  try {
    const input = readJSON(value, 128000), g = input.data;
    requireTrue(g.schema === '5703_week10_native_pair_status_v1' && g.batch_id === fixture.batch_id && g.source_version === sourceSHA && g.model === fixture.model && g.provider_route === providerRoute, 'PUBLIC_TELEMETRY_BINDING_MISMATCH');
    const result = { pin: input.pin, observed_epoch_ms: Date.now(), scope: 'Read-only observed status; this snapshot does not authorize a submission' };
    for (const key of ['status', 'provider_post_count', 'maximum_provider_post_count', 'remaining_provider_slots', 'open_claims', 'unknown_cost_count', 'integrity_errors', 'cleanup_pending', 'fully_settled', 'stop_exists', 'known_API_cost_USD', 'full_unknown_hold_USD', 'max_possible_new_batch_reserve_USD']) {
      if (['string', 'number', 'boolean'].includes(typeof g[key])) result[key] = g[key];
    }
    return result;
  } catch { return { unavailable: true, code: 'PUBLIC_BUDGET_TELEMETRY_UNAVAILABLE' }; }
}

function gate(value, sourceSHA, providerRoute, settled = false, minimumSlots = 0) {
  const input = readJSON(value, 128000), g = input.data;
  requireTrue(g.schema === '5703_week10_native_pair_status_v1' && ['READY', 'STOPPED'].includes(g.status), 'EXACT_PUBLIC_BUDGET_SCHEMA_REQUIRED');
  requireTrue(g.batch_id === fixture.batch_id && g.source_version === sourceSHA && g.source_index_sha256 === sourceSHA && g.source_label === 'WEEK10_CONTINUOUS_SCOPES' && g.model === fixture.model && g.provider_route === providerRoute, 'PUBLIC_BUDGET_BINDING_MISMATCH');
  requireTrue(g.maximum_provider_post_count === MAX_PROVIDER_POSTS && Number.isSafeInteger(g.provider_post_count) && g.provider_post_count >= 0 && g.provider_post_count <= MAX_PROVIDER_POSTS, 'FOUR_NEW_SHARED_PHYSICAL_PROVIDER_POST_BOUND_REQUIRED');
  requireTrue(Number.isSafeInteger(g.remaining_provider_slots) && g.remaining_provider_slots === MAX_PROVIDER_POSTS - g.provider_post_count && Number.isSafeInteger(g.open_claims) && g.open_claims >= 0 && Number.isSafeInteger(g.unknown_cost_count) && g.unknown_cost_count >= 0, 'PUBLIC_BUDGET_COUNTERS_INVALID');
  requireTrue(typeof g.fully_settled === 'boolean' && typeof g.stop_exists === 'boolean', 'PUBLIC_SETTLEMENT_FLAGS_REQUIRED');
  requireTrue(Number.isSafeInteger(g.integrity_errors) && g.integrity_errors === 0 && Number.isSafeInteger(g.cleanup_pending) && g.cleanup_pending >= 0, 'PUBLIC_BUDGET_INTEGRITY_AND_CLEANUP_REQUIRED');
  requireTrue(currency(g.max_possible_new_batch_reserve_USD) === BATCH_RESERVE_SCALED && currency(g.known_API_cost_USD) + currency(g.full_unknown_hold_USD) <= BATCH_RESERVE_SCALED, 'TWELVE_CENT_NEW_PROTECTION_WITHIN_APPROVED_TOTAL');
  requireTrue(!g.stop_exists && g.unknown_cost_count === 0, 'BUDGET_STOP_OR_UNKNOWN_NO_NEXT_SUBMISSION');
  if (settled) requireTrue(g.status === 'READY' && g.fully_settled && g.open_claims === 0 && g.cleanup_pending === 0 && currency(g.full_unknown_hold_USD) === 0n, 'BUDGET_NOT_FULLY_SETTLED_NO_NEXT_SUBMISSION');
  const leg = fixture.paired_leg_id;
  requireTrue(Number.isSafeInteger(g.per_leg_provider_post_count?.[leg]) && g.per_leg_provider_post_count[leg] >= 0 && g.per_leg_provider_post_count[leg] <= MAX_REQUEST_POSTS && g.per_leg_remaining_provider_slots?.[leg] === MAX_REQUEST_POSTS-g.per_leg_provider_post_count[leg], 'EXACT_NATIVE_FOUR_POST_LEG_BOUND_REQUIRED');
  requireTrue(g.remaining_provider_slots >= minimumSlots && g.per_leg_remaining_provider_slots[leg] >= minimumSlots, 'INSUFFICIENT_PROVIDER_SLOTS_NO_NEXT_SUBMISSION');
  return { pin: input.pin, status: g.status, per_leg_provider_post_count: g.per_leg_provider_post_count, per_leg_remaining_provider_slots: g.per_leg_remaining_provider_slots, leg_completed: g.leg_completed, leg_runtime_closed: g.leg_runtime_closed, integrity_errors: g.integrity_errors, cleanup_pending: g.cleanup_pending, provider_post_count: g.provider_post_count, remaining_provider_slots: g.remaining_provider_slots,
    fully_settled: g.fully_settled, open_claims: g.open_claims, unknown_cost_count: g.unknown_cost_count,
    stop_exists: g.stop_exists, known_API_cost_USD: g.known_API_cost_USD, full_unknown_hold_USD: g.full_unknown_hold_USD };
}

// This observer changes no product DOM, application storage or server records.
// Double requestAnimationFrame samples follow a prior paint; full DOM availability
// does not claim that every character is simultaneously visible or read by a user.
async function armPaintObservation(page, oldIds) {
  await page.evaluate(ids => {
    const state = { oldIds: new Set(ids), entries: {}, t0: null, timeOrigin: performance.timeOrigin,
      expected: null, terminalSucceeded: false, actualAnswerResponse: false, disposed: false, queued: false };
    const intersection = new Map(), observed = new WeakSet();
    const normalize = text => text.replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/\[[0-9]+\]/g, '').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
    const visible = el => { const rect = el.getBoundingClientRect(), style = getComputedStyle(el);
      return document.visibilityState === 'visible' && style.display !== 'none' && style.visibility === 'visible' && Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.right > 0 && rect.top < innerHeight && rect.left < innerWidth; };
    const scan = () => {
      state.queued = false; if (state.disposed || state.t0 === null) return;
      for (const answer of document.querySelectorAll('[data-answer-id]')) {
        const id = answer.getAttribute('data-answer-id'); if (!id || state.oldIds.has(id)) continue;
        const prose = answer.querySelector('.prose'); if (!prose) continue;
        if (!observed.has(prose)) { observed.add(prose); viewport.observe(prose); }
        if (!prose.textContent.trim() || !visible(prose) || intersection.get(prose) !== true) continue;
        const entry = state.entries[id] ||= { first_ms: null, full_ms: null, visible: true, prose_length: prose.textContent.length,
          visibility_basis: 'IntersectionObserver >=0.01 including ancestor clipping; document visible; own style and viewport rectangle; sampled after prior paint' };
        if (entry.first_ms === null) entry.first_ms = performance.now() - state.t0;
        const expected = state.expected;
        if (!expected || expected.id !== id || !state.terminalSucceeded || !state.actualAnswerResponse || entry.full_ms !== null) continue;
        const buttons = [...answer.querySelectorAll('button')];
        const hasAction = name => buttons.some(button => button.textContent.trim() === name && !button.disabled);
        const inline = buttons.filter(button => /^Open source [0-9]+$/.test(button.getAttribute('aria-label') || ''));
        const actualIndices = new Set(inline.map(button => Number((button.getAttribute('aria-label') || '').slice('Open source '.length))));
        const cited = expected.citation_count === 0 ? inline.length === 0 : expected.citation_ids.every((_, index) => actualIndices.has(index + 1)) && [...actualIndices].every(index => index >= 1 && index <= expected.citation_count);
        const followups = [...answer.querySelectorAll('.followups button')];
        const suggestions = expected.followups.every(text => followups.some(button => button.textContent.trim() === text && !button.disabled));
        // Match the product Markdown.tsx transformation only for declared evidence IDs.
        // Unknown evidence markers remain in expected text and cannot disappear.
        const projected = expected.answer_text.replace(/\[(ev_\d{3,})\]/g, (marker, id) => expected.citation_ids.includes(id) ? '[' + (expected.citation_ids.indexOf(id) + 1) + ']' : marker);
        const bodyComplete = normalize(prose.textContent).includes(normalize(projected)) && normalize(projected).length > 0;
        if (bodyComplete && cited && hasAction('Copy') && hasAction('Bookmark answer') && hasAction('Feedback') && suggestions && !document.querySelector('[data-progress-state]')) {
          entry.full_ms = performance.now() - state.t0; entry.complete_body = true; entry.citation_controls = inline.length;
          entry.followup_controls = followups.length;
        }
      }
    };
    const schedule = () => { if (state.disposed || state.queued) return; state.queued = true; requestAnimationFrame(() => requestAnimationFrame(scan)); };
    const viewport = new IntersectionObserver(entries => { for (const entry of entries) intersection.set(entry.target, entry.isIntersecting && entry.intersectionRatio >= 0.01); schedule(); }, { threshold: 0.01 });
    const mutation = new MutationObserver(schedule); mutation.observe(document.getElementById('main-content') || document.body, { childList: true, subtree: true, attributes: true, characterData: true });
    document.addEventListener('visibilitychange', schedule); document.addEventListener('scroll', schedule, true);
    const button = document.querySelector('button[aria-label="Send message"]');
    if (!button) throw new Error('Send control is absent');
    const clicked = () => { if (state.t0 === null) { state.t0 = performance.now(); schedule(); } };
    button.addEventListener('click', clicked, { once: true, capture: true });
    state.schedule = schedule;
    state.dispose = () => { state.disposed = true; mutation.disconnect(); viewport.disconnect(); button.removeEventListener('click', clicked); document.removeEventListener('visibilitychange', schedule); document.removeEventListener('scroll', schedule, true); };
    window.__cs30LivePaint01 = state;
  }, oldIds);
}

async function main() {
  const cli = args();
  const loaded = readJSON(cli['--fixture'], 64000, true); fixture = loaded.data;
  const authPin = fixture.actor_auth_source_pin;
  requireTrue(authPin && typeof authPin.path === 'string' && HEX.test(authPin.sha256), 'EXACT_NEW_ACTOR_AUTH_SOURCE_PIN_REQUIRED');
  const originalAuthPath = ownedPath(authPin.path, { privateFixture: true });
  requireTrue(!fs.lstatSync(originalAuthPath).isSymbolicLink() && fs.statSync(originalAuthPath).isFile() && fs.statSync(originalAuthPath).size <= 64000, 'NEW_OWNED_SYNTHETIC_AUTH_SOURCE_REQUIRED');
  const authBytes = fs.readFileSync(originalAuthPath);
  requireTrue(authBytes.length === authPin.bytes && sha(authBytes) === authPin.sha256, 'NEW_OWNED_AUTH_SOURCE_PIN_CHANGED');
  const previousAuth = JSON.parse(authBytes.toString('utf8'));
  requireTrue(previousAuth.schema === 'cs30_week10_owned_actor_auth_v1' && previousAuth.synthetic_only === true && previousAuth.batch_id === (fixture.actor_auth_batch_id || fixture.batch_id) && previousAuth.learner_id === fixture.learner_id && typeof previousAuth.password === 'string' && previousAuth.password && previousAuth.learner_email === fixture.learner_email, 'EXACT_NEW_OWNED_SYNTHETIC_ACTOR_IDENTITY_REQUIRED');
  fixture.password = previousAuth.password;
  previousAuth.password = null;
  requireTrue(fixture.schema === '5703_week10_native_continuous_fixture_v1' && fixture.synthetic_only === true && fixture.model_mode === 'live' && fixture.base_url === BASE, 'NEW_OWNED_LIVE_SYNTHETIC_FIXTURE_REQUIRED');
  const fixedLegs = { B_startup_prewarm: { base: 'http://127.0.0.1:15197', prewarm: true } };
  requireTrue(fixedLegs[fixture.paired_leg_id]?.base === BASE && fixedLegs[fixture.paired_leg_id].prewarm === fixture.worker_prewarm_retrieval_cache, 'FIXED_PAIRED_LEG_AND_FLAG_REQUIRED');
  requireTrue(Object.keys(fixture).every(key => !/api.?key|token|db.?url|database|encryption/i.test(key)), 'PROVIDER_KEYS_OR_DB_CREDENTIALS_FORBIDDEN_IN_FIXTURE');
  for (const key of ['learner_email', 'password', 'book_title', 'book_id', 'release_id', 'batch_id', 'configuration_id', 'config_hash', 'provider', 'model', 'openrouter_route_profile', 'readiness_public_path', 'budget_status_public_path']) requireTrue(typeof fixture[key] === 'string' && fixture[key].length > 0, 'OWNED_FIXTURE_FIELD_MISSING');
  const expectedQuestions = [
    { question_id: 'Q1', question: 'What are the net products of glycolysis per glucose molecule?', scope_topic: 'glycolysis' },
    { question_id: 'Q2', question: 'How do light-dependent reactions provide the energy carriers used by the Calvin cycle?', scope_topic: 'light-dependent reactions' },
  ];
  requireTrue(canonical(fixture.continuous_questions) === canonical(expectedQuestions), 'EXACT_AUTHORIZED_TWO_QUESTIONS_REQUIRED');
  requireTrue(fixture.retrieval_variant === 'R2' && fixture.source_label === 'WEEK10_CONTINUOUS_SCOPES' && Number.isSafeInteger(fixture.config_revision) && HEX.test(fixture.config_hash), 'EXACT_CURRENT_LIVE_DEFAULT_CONFIGURATION_REQUIRED');
  const sourceSHA = fixture.source_index_sha256 || fixture.source_version;
  requireTrue(HEX.test(sourceSHA), 'SOURCE_INDEX_SHA_REQUIRED_NOT_HUMAN_LABEL');
  credentials = [fixture.password, fixture.learner_email, fixture.admin_email].filter(Boolean);
  requireTrue(!credentials.some(secret => expectedQuestions.some(item => item.question.includes(secret))), 'AUTH_VALUES_FORBIDDEN_IN_PUBLIC_QUESTIONS');
  requireTrue(ownedPath(cli['--budget-status']) === ownedPath(fixture.budget_status_public_path), 'EXACT_OWNED_BUDGET_PATH_REQUIRED');
  let qualified = qualification(sourceSHA);
  const initialGate = gate(cli['--budget-status'], sourceSHA, qualified.provider_route, true);
  const previous = readJSON(cli['--resume-receipt'], 512000, false, true);
  requireTrue(fixture.fixture_seed_receipt_pin && previous.pin.path === fixture.fixture_seed_receipt_pin.path && previous.pin.bytes === fixture.fixture_seed_receipt_pin.bytes && previous.pin.sha256 === fixture.fixture_seed_receipt_pin.sha256, 'ROOT_PINNED_ACTUAL_NEW_SEED_RECEIPT_REQUIRED');
  const prior = previous.data;
  requireTrue(prior.schema === 'cs30_week10_paired_synthetic_seed_v1' && prior.status === 'ACTUAL_SAME_ID_OWNED_PAIR_SEEDED_AND_VERIFIED' && prior.synthetic_only === true && prior.new_owned === true && prior.source_unchanged === true, 'ACTUAL_NEW_OWNED_SAME_ID_PAIR_REQUIRED');
  requireTrue(prior.same_ids_bindings?.learner_id === fixture.learner_id && prior.same_ids_bindings?.configuration_id === fixture.configuration_id, 'OWNED_SYNTHETIC_ACTOR_SOURCE_IDENTITY_REQUIRED');
  requireTrue(initialGate.provider_post_count === 0 && initialGate.per_leg_provider_post_count[fixture.paired_leg_id] === 0, 'FRESH_CONTINUATION_ZERO_PROVIDER_POSTS_REQUIRED');
  const startupDriver = readJSON(cli['--startup-driver-receipt'], 128000);
  const driver = startupDriver.data;
  requireTrue(driver.schema === '5703_week10_root_startup_driver_v1' && driver.batch_id === fixture.batch_id && driver.paired_leg_id === fixture.paired_leg_id && driver.source_version === sourceSHA && Number.isFinite(driver.process_launch_epoch_ms) && Number.isFinite(driver.worker_ready_observed_epoch_ms) && driver.worker_ready_observed_epoch_ms >= driver.process_launch_epoch_ms, 'ACTUAL_ROOT_PROCESS_START_AND_WORKER_READY_CLOCK_REQUIRED');
  const out = ownedPath(cli['--out'], { absent: true });
  requireTrue(!fs.existsSync(out) && fs.statSync(path.dirname(out)).isDirectory(), 'CREATE_ONLY_NEW_OUTPUT_DIRECTORY_REQUIRED');
  fs.mkdirSync(out, { recursive: false });
  os.setPriority(process.pid, os.constants.priority.PRIORITY_NORMAL);
  const { chromium, expect } = require('E:/5703/learning-assistant/frontend/node_modules/@playwright/test');
  const started = Date.now(), deadline = started + TOTAL_DEADLINE_MS;
  const record = { schema: '5703_week10_native_continuous_ui_receipt_v1', status: 'RUNNING', started_utc: new Date().toISOString(),
    batch_id: fixture.batch_id, paired_leg_id: fixture.paired_leg_id, worker_prewarm_retrieval_cache: fixture.worker_prewarm_retrieval_cache, source_index_sha256: sourceSHA, source_label: fixture.source_label || null,
    model_mode: 'live', exact_model_binding_basis: 'Root pinned current project qualification and guarded batch; AnswerOut itself exposes only model_mode',
    provider: fixture.provider, model: fixture.model, openrouter_route_profile: fixture.openrouter_route_profile,
    provider_route: qualified.provider_route, configuration_id: fixture.configuration_id, config_revision: fixture.config_revision, config_hash: fixture.config_hash,
    qualification: qualified, budget_initial: initialGate, retrieval_variant: 'R2', retrieval_binding: 'current_public_default_hybrid_minilm_v1', executor_override: false, native_retrieval_execution_proof: null, default_retrieval_acceptance: 'PENDING_ROOT_NATIVE_TRACE_AND_QUALITY_REVIEW',
    synthetic_learner_and_questions: true, existing_public_owned_book: { id: fixture.book_id, title: fixture.book_title, release_id: fixture.release_id },
    actual_headless_browser: true, browser_count: 1, page_count: 1, worker_count: 1, browser_gpu_disabled: true, chromium_sandbox: true,
    ignore_https_errors: false, process_priority: 'Normal; applied by this Node runner', cpu_affinity: 'Controlled by Root launcher; not asserted here',
    direct_http_acceptance_calls: 0, direct_database_accesses: 0, manual_provider_calls: 0, automatic_question_retries: 0,
    provider_physical_post_limit: MAX_PROVIDER_POSTS, native_per_question_post_bound: MAX_REQUEST_POSTS, new_batch_reserve_USD: '0.12000000', approved_cumulative_ceiling_USD: '0.24000000', timeTTFT_ms: null,
    TTFT_boundary: 'Current UI is not token-streaming; first painted prose is not provider TTFT',
    normal_reader_scopes: true, intended_retrieval_scope: 'all_active_corpus', chapter_filter_applied: false, new_question_submissions: 0, actual_seed_receipt_pin: previous.pin, seeded_first_provider_POSTs: 0,
    warm_execution_basis: 'Native offline model-instance prewarm used a distinct authored query; no measured question-result cache was populated', prewarm_public_path: fixture.prewarm_public_path,
    continuing_worker_basis: 'One native B worker and one Engine remain alive across Q1 and Q2; native traces separately establish identity/cache use',
    startup_driver_pin: startupDriver.pin, startup_driver: driver, process_launch_to_worker_ready_ms: driver.worker_ready_observed_epoch_ms-driver.process_launch_epoch_ms, worker_startup_report: qualified.worker_startup,
    questions: [], selected_scopes: [], scope_resolution_attempts: [], second_question: { status: 'NOT_YET_CONSIDERED' }, page_errors: [], denied_external_requests: [], console_type_counts: {},
    browser_closed: false, context_closed: false, project_complete: false,
    limits: ['Two different chapter-origin authored questions use normal whole-context removal and full active-corpus RAG; chapter IDs are navigation provenance, not retrieval filters; small functionality observations, no p95 or causal comparison', 'Public default profile binding does not itself prove native R2/reranker execution or retrieval quality', 'Complete DOM is not simultaneous visibility of every character or user reading', 'Paint clocks are double-RAF samples; full time also includes DTO observation and the 200 ms control-loop sampling delay', 'Normalized Markdown-to-DOM text comparison is approximate and may conservatively reject a valid formatted answer', 'Viewport intersection includes ancestor clipping but does not prove unobscured individual text glyphs', 'Published refusal or partial-reply rendering can have measured clocks while cited-answer quality remains FAIL', 'No guarantee of zero operating-system contention'] };
  let browser, context, page, active = null, capabilities = null, library = null, interrupted = false;
  const observedSections = new Map(), observedReadingPages = new Map();
  const pendingResponses = new Set();
  const retainObserverError = (phase, error) => {
    if (!phase) { record.unbound_observer_error_code ??= error instanceof Boundary ? error.code : 'PUBLIC_RESPONSE_CONTRACT_ERROR'; return; }
    phase.error ??= error instanceof Boundary ? error.code : 'PUBLIC_RESPONSE_CONTRACT_ERROR';
    phase.record.observer_error_code ??= phase.error;
  };
  const checkPhase = phase => { if (phase.error) throw new Boundary(phase.error); requireTrue(!record.unbound_observer_error_code, 'UNBOUND_PUBLIC_RESPONSE_CONTRACT_ERROR'); };
  async function drainObservers(phase) {
    const until = Math.min(deadline, Date.now() + 5000);
    while (pendingResponses.size) {
      await bounded(Promise.allSettled([...pendingResponses]), Math.max(1, until - Date.now()), 'PUBLIC_RESPONSE_OBSERVER_SETTLEMENT_TIMEOUT');
      requireTrue(Date.now() < until || pendingResponses.size === 0, 'PUBLIC_RESPONSE_OBSERVER_SETTLEMENT_TIMEOUT');
    }
    if (phase) checkPhase(phase);
  }
  const remaining = () => Math.max(1, deadline - Date.now());
  const checkDeadline = () => requireTrue(!interrupted && Date.now() < deadline, 'OWNED_BROWSER_DEADLINE_OR_INTERRUPTION');
  const timer = setTimeout(() => { interrupted = true; if (context) void context.close().catch(() => {}); }, TOTAL_DEADLINE_MS);
  const interrupt = () => { interrupted = true; if (context) void context.close().catch(() => {}); };
  process.on('SIGINT', interrupt); process.on('SIGTERM', interrupt);

  async function publicCapture(name) {
    requireTrue(!fs.existsSync(path.join(out, name + '.png')) && !fs.existsSync(path.join(out, name + '.txt')), 'PUBLIC_CAPTURE_ALREADY_EXISTS');
    const masks = [page.locator('input[type="password"], input[type="email"], .account-row')];
    for (const secret of credentials) masks.push(page.getByText(secret, { exact: true }));
    const bodyText = await page.locator('body').innerText({ timeout: 4000 });
    requireTrue(!/Bearer\s+\S+|\bsk-[A-Za-z0-9_-]{12,}\b|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/i.test(bodyText), 'CREDENTIAL_SHAPED_VISIBLE_TEXT_CAPTURE_REFUSED');
    await page.screenshot({ path: path.join(out, name + '.png'), mask: masks, timeout: 5000 });
    fs.writeFileSync(path.join(out, name + '.txt'), safe(bodyText) + '\n', { flag: 'wx' });
  }

  async function observeResponse(response) {
    const url = new URL(response.url()); if (url.origin !== BASE) return;
    const method = response.request().method(), route = url.pathname, observedEpoch = Date.now();
    if (method === 'GET' && route === '/api/v1/capabilities' && response.status() === 200) {
      const body = await response.json(); capabilities = { model_mode: body?.data?.model_mode, chat_ready: body?.data?.chat_ready }; return;
    }
    if (method === 'GET' && route === '/api/v1/learning/library' && response.status() === 200) {
      const body = await response.json(); library = body?.data; return;
    }
    const sectionsMatch = route.match(/^\/api\/v1\/learning\/library\/([^/]+)\/sections$/);
    if (method === 'GET' && sectionsMatch && response.status() === 200) {
      const d = (await response.json())?.data;
      requireTrue(Array.isArray(d), 'NORMAL_SECTIONS_RESPONSE_ARRAY_REQUIRED');
      observedSections.set(decodeURIComponent(sectionsMatch[1]), { items: d, method, route, http_status: 200, observed_epoch_ms: observedEpoch, sha256: sha(canonical(d)) }); return;
    }
    const unitsMatch = route.match(/^\/api\/v1\/learning\/library\/([^/]+)\/units$/);
    if (method === 'GET' && unitsMatch && response.status() === 200) {
      const d = (await response.json())?.data;
      requireTrue(d && Array.isArray(d.items), 'NORMAL_READING_PAGE_REQUIRED');
      const section = url.searchParams.get('section_id');
      observedReadingPages.set(decodeURIComponent(unitsMatch[1]) + ':' + (section || ''), { data: d, method, route: route + url.search, http_status: 200, observed_epoch_ms: observedEpoch, sha256: sha(canonical(d)) }); return;
    }
    const phase = active; if (!phase) return;
    if (method === 'POST' && route === '/api/v1/sessions/' + phase.record.session_id + '/messages') {
      requireTrue(response.status() === 202 && !phase.receipt, 'EXACT_SINGLE_202_REQUIRED');
      const body = await response.json(), d = body?.data;
      requireTrue(d && UUID.test(d.request_id) && UUID.test(d.job_id) && d.poll_url === '/api/v1/jobs/' + d.job_id, 'BOUND_202_RECEIPT_INVALID');
      phase.receipt = d; phase.record.request_id = d.request_id; phase.record.job_id = d.job_id;
      phase.record.accepted_202_observed_epoch_ms = observedEpoch;
      return;
    }
    if (method === 'GET' && /^\/api\/v1\/jobs\/[0-9a-f-]+$/i.test(route) && response.status() === 200) {
      const d = (await response.json())?.data;
      if (d && UUID.test(d.id)) {
        const previous = phase.jobs.get(d.id);
        if (previous && ['succeeded', 'failed', 'cancelled'].includes(previous.data.state)) {
          requireTrue(previous.data.state === d.state && previous.data.answer_id === d.answer_id, 'TERMINAL_JOB_CHANGED_WITHOUT_PLANNED_RETRY');
        } else if (!previous || observedEpoch >= previous.observedEpoch) phase.jobs.set(d.id, { data: d, observedEpoch });
      }
      return;
    }
    if (method === 'GET' && (route === '/api/v1/sessions/' + phase.record.session_id + '/messages' || /^\/api\/v1\/answers\/[0-9a-f-]+$/i.test(route)) && response.status() === 200) {
      const d = (await response.json())?.data;
      const answers = Array.isArray(d?.items) ? d.items.map(item => item.answer).filter(Boolean) : d?.id ? [d] : [];
      let requestStartEpoch = null;
      try { const value = response.request().timing().startTime; if (Number.isFinite(value) && value >= 0) requestStartEpoch = value; } catch {}
      for (const answer of answers) if (UUID.test(answer.id) && UUID.test(answer.request_id) && UUID.test(answer.job_id)) {
        const previous = phase.answers.get(answer.id);
        if (!previous || observedEpoch >= previous.observedEpoch) phase.answers.set(answer.id, { data: answer, observedEpoch, requestStartEpoch, method: 'GET', route, http_status: response.status() });
      }
    }
  }

  async function question(label, text, sessionId, selectedScope) {
    checkDeadline(); qualified = qualification(sourceSHA);
    const before = gate(cli['--budget-status'], sourceSHA, qualified.provider_route, true, MIN_PROVIDER_SLOTS);
    const oldIds = await page.locator('[data-answer-id]').evaluateAll(elements => elements.map(element => element.getAttribute('data-answer-id')));
    const q = { label, question_id: label, selected_scope: selectedScope, retrieval_scope: selectedScope.retrieval_scope, chapter_filter_applied: selectedScope.chapter_filter_applied, normal_UI_reading_context_removed: selectedScope.normal_UI_reading_context_removed, status: 'RUNNING', question: text, question_sha256: sha(text), session_id: sessionId,
      request_id: null, job_id: null, answer_id: null, terminal_state: null, terminal_error_code: null,
      t0_performance_ms: null, page_time_origin_ms: null, t202_ms: null, tterminal_ms: null,
      tfirst_ms: null, tfull_ms: null, tfailure_ms: null, timeTTFT_ms: null, server_worker_timing: null,
      budget_before: before, budget_after: null, physical_provider_posts: null, citation_checked: false, refresh_persisted: false,
      routed_message_posts: 0, observer_error_code: null, submitted_message_body: null, published_reply_rendered: false,
      completed_cited_answer: false, quality_failure_code: null, fresh_reload_response: null };
    record.questions.push(q);
    const phase = { record: q, receipt: null, jobs: new Map(), answers: new Map(), routedMessagePosts: 0, error: null };
    active = phase;
    try {
      await expect(page.getByText('Live model', { exact: true }).first()).toBeVisible();
      requireTrue(capabilities?.model_mode === 'live' && capabilities?.chat_ready === true, 'OBSERVED_LIVE_CHAT_CAPABILITY_REQUIRED');
      requireTrue(record.page_errors.length === 0 && record.denied_external_requests.length === 0, 'BROWSER_ERRORS_BLOCK_NEW_QUESTION');
      await page.getByRole('textbox', { name: 'Message Learning Assistant', exact: true }).fill(text);
      await armPaintObservation(page, oldIds);
      await page.getByRole('button', { name: 'Send message', exact: true }).click();
      const clickedClock = await page.evaluate(() => { const s = window.__cs30LivePaint01; return s ? { t0: s.t0, timeOrigin: s.timeOrigin } : null; });
      requireTrue(clickedClock && clickedClock.t0 !== null, 'ACTUAL_SEND_CLICK_CLOCK_MISSING');
      q.t0_performance_ms = clickedClock.t0; q.page_time_origin_ms = clickedClock.timeOrigin;
      const until = Math.min(deadline, Date.now() + QUESTION_DEADLINE_MS);
      while (Date.now() < until) {
        checkDeadline(); checkPhase(phase);
        // The provider guard owns in-flight reservations. Do not require a settled
        // READY snapshot while this admitted job is running; STOP/UNKNOWN/error
        // handling remains enforced by the guard and the actual job terminal state.
        const t = await page.evaluate(() => { const s = window.__cs30LivePaint01; return s ? { t0: s.t0, timeOrigin: s.timeOrigin } : null; });
        requireTrue(t && t.t0 !== null, 'ACTUAL_SEND_CLICK_CLOCK_MISSING');
        q.t0_performance_ms = t.t0; q.page_time_origin_ms = t.timeOrigin;
        const elapsed = epoch => Math.max(0, epoch - (t.timeOrigin + t.t0));
        if (phase.receipt) q.t202_ms = elapsed(q.accepted_202_observed_epoch_ms);
        const observedJob = phase.receipt && phase.jobs.get(phase.receipt.job_id);
        if (observedJob) {
          const job = observedJob.data;
          requireTrue(job.request_id === phase.receipt.request_id, 'JOB_REQUEST_ID_MISMATCH');
          if (['failed', 'cancelled'].includes(job.state)) {
            q.terminal_state = job.state; q.terminal_error_code = typeof job.error?.code === 'string' ? safe(job.error.code, 128) : null;
            q.tterminal_ms = elapsed(observedJob.observedEpoch); q.tfailure_ms = q.tterminal_ms;
            q.tfirst_ms = null; q.tfull_ms = null;
            throw new Boundary('CHECKED_TERMINAL_FAILURE_NO_PUBLISHED_ANSWER');
          }
          if (job.state === 'succeeded') {
            q.terminal_state = 'succeeded'; q.tterminal_ms ??= elapsed(observedJob.observedEpoch);
            requireTrue(UUID.test(job.answer_id) && !oldIds.includes(job.answer_id), 'TERMINAL_NEW_ANSWER_ID_REQUIRED');
            const observedAnswer = phase.answers.get(job.answer_id);
            if (observedAnswer) {
              const answer = observedAnswer.data;
              requireTrue(answer.request_id === phase.receipt.request_id && answer.job_id === phase.receipt.job_id && answer.model_mode === 'live' && answer.response_schema === 'chat_response_v1' && answer.answer_mode === 'textbook', 'ACTUAL_BOUND_LIVE_ANSWER_RESPONSE_REQUIRED');
              const response = answer.response;
              q.answer_id = answer.id;
              q.response_type = typeof response?.response_type === 'string' ? safe(response.response_type, 64) : null;
              requireTrue(response && typeof response.answer_text === 'string' && response.answer_text.trim() && Array.isArray(response.citations) && Array.isArray(response.follow_up_questions), 'ACTUAL_RENDERABLE_REPLY_SCHEMA_REQUIRED');
              q.completed_cited_answer = response.response_type === 'answer' && response.citations.length > 0 && answer.answer_completeness?.status === 'complete_at_requested_help';
              q.quality_failure_code = q.completed_cited_answer ? null : 'PUBLISHED_REPLY_NOT_A_COMPLETE_CITED_ANSWER';
              q.refusal_reason = typeof response.refusal_reason === 'string' ? safe(response.refusal_reason, 128) : null;
              q.answer_completeness_status = typeof answer.answer_completeness?.status === 'string' ? safe(answer.answer_completeness.status, 64) : null;
              q.published_response_sha256 = sha(canonical(response));
              requireTrue(response.citations.every(id => typeof id === 'string' && id.length > 0) && response.follow_up_questions.every(value => typeof value === 'string'), 'ANSWER_CITATION_OR_FOLLOWUP_SCHEMA_INVALID');
              const citations = [...new Set(response.citations)]; q.answer_id = answer.id; q.answer_text_sha256 = sha(response.answer_text);
              q.answer_text = safe(response.answer_text); q.citation_ids = citations; q.follow_up_questions = response.follow_up_questions.map(value => safe(value, 4000));
              q.native_retrieval_public_path = path.join(path.dirname(fixture.readiness_public_path), 'native-retrieval-' + q.request_id + '-public01.json');
              if (answer.timing?.timing_scope === 'worker_execution_before_answer_insert_v1') {
                q.server_worker_timing = { timing_scope: answer.timing.timing_scope, units: 'milliseconds', excludes: 'HTTP admission, queue wait, answer insertion/commit, browser loading/paint' };
                for (const [key, value] of Object.entries(answer.timing)) if (/_ms$/.test(key) && typeof value === 'number' && Number.isFinite(value) && value >= 0) q.server_worker_timing[key] = value;
              }
              await page.evaluate(expected => { const s = window.__cs30LivePaint01; s.expected = expected; s.terminalSucceeded = true; s.actualAnswerResponse = true; s.schedule(); }, { id: answer.id, answer_text: response.answer_text, citation_count: citations.length, citation_ids: citations, followups: response.follow_up_questions });
              const paint = await page.evaluate(id => { const s = window.__cs30LivePaint01, entry = s.entries[id]; return entry ? { ...entry } : null; }, answer.id);
              if (paint?.first_ms !== null && paint?.first_ms !== undefined) q.tfirst_ms = paint.first_ms;
              if (paint?.full_ms !== null && paint?.full_ms !== undefined) {
                q.tfirst_ms = paint.first_ms; q.tfull_ms = paint.full_ms; q.paint_observation = paint;
                requireTrue(q.tfirst_ms >= 0 && q.tfull_ms >= q.tfirst_ms, 'PAINT_TIMING_ORDER_INVALID');
                break;
              }
            }
          }
        }
        await wait(200);
      }
      requireTrue(q.answer_id && q.tfirst_ms !== null && q.tfull_ms !== null, 'ANSWER_RENDER_TIMEOUT_RIGHT_CENSORED');
      q.published_reply_rendered = true;
      checkPhase(phase);
      const answer = page.locator('[data-answer-id="' + q.answer_id + '"]');
      await expect(answer.getByText('Live model', { exact: true })).toBeVisible();
      q.pre_refresh_prose_sha256 = sha(await answer.locator('.prose').innerText());
      const published = phase.answers.get(q.answer_id).data;
      if (published.response.citations.length > 0) {
        await answer.getByRole('button', { name: /^Open source [0-9]+$/ }).first().click();
        const dialog = page.getByRole('dialog', { name: 'Sources', exact: true });
        await expect(dialog).toBeVisible(); const source = dialog.locator('.source-passage').first();
        await expect(source).toBeVisible(); const excerpt = await source.innerText();
        requireTrue(excerpt.trim().length > 0, 'ACTUAL_CITATION_EXCERPT_REQUIRED');
        q.citation_checked = true; q.source_excerpt_sha256 = sha(excerpt); q.source_excerpt_character_count = excerpt.length;
        q.source_excerpt = safe(excerpt); q.source_dialog_text = safe(await dialog.innerText());
        await publicCapture(label + '-citation');
        await page.keyboard.press('Escape'); await expect(dialog).toHaveCount(0);
      } else {
        // Retain actual rendered refusal/partial telemetry without asserting QA.
        await publicCapture(label + '-rendered-not-cited');
      }
      await page.evaluate(() => window.__cs30LivePaint01?.dispose());
      q.reload_started_epoch_ms = Date.now();
      await page.reload({ waitUntil: 'domcontentloaded', timeout: Math.min(15000, remaining()) });
      const refreshedProse = page.locator('[data-answer-id="' + q.answer_id + '"] .prose');
      await expect(refreshedProse).toBeVisible({ timeout: 15000 });
      requireTrue(new URL(page.url()).pathname === '/chat/' + sessionId, 'REFRESH_SESSION_ID_CHANGED');
      await expect.poll(() => {
        const value = phase.answers.get(q.answer_id);
        return value && value.requestStartEpoch !== null && value.requestStartEpoch >= q.reload_started_epoch_ms;
      }, { timeout: 15000 }).toBe(true);
      await drainObservers(phase);
      const fresh = phase.answers.get(q.answer_id), refreshed = fresh.data;
      requireTrue(Number.isFinite(fresh.requestStartEpoch) && fresh.requestStartEpoch >= q.reload_started_epoch_ms && fresh.method === 'GET' && fresh.http_status === 200 && refreshed.id === q.answer_id && refreshed.request_id === q.request_id && refreshed.job_id === q.job_id && refreshed.model_mode === 'live' && refreshed.response_schema === 'chat_response_v1' && refreshed.answer_mode === 'textbook' && sha(canonical(refreshed.response)) === q.published_response_sha256, 'FRESH_RELOAD_ANSWER_IDENTITY_OR_BODY_CHANGED');
      q.fresh_reload_response = { method: fresh.method, route: fresh.route, http_status: fresh.http_status, request_started_epoch_ms: fresh.requestStartEpoch, response_observed_epoch_ms: fresh.observedEpoch, answer_id: refreshed.id, request_id: refreshed.request_id, job_id: refreshed.job_id, published_response_sha256: sha(canonical(refreshed.response)), answer_text_sha256: sha(refreshed.response.answer_text) };
      q.refreshed_prose_sha256 = sha(await refreshedProse.innerText());
      requireTrue(q.refreshed_prose_sha256 === q.pre_refresh_prose_sha256, 'FRESH_RELOAD_RENDERED_BODY_CHANGED');
      q.refresh_persisted = true; await publicCapture(label + '-refreshed');
      const settlementUntil = Math.min(deadline, Date.now() + 30000);
      while (Date.now() < settlementUntil) {
        checkPhase(phase);
        const latest = gate(cli['--budget-status'], sourceSHA, qualified.provider_route);
        requireTrue(latest.provider_post_count >= before.provider_post_count, 'PHYSICAL_PROVIDER_COUNTER_DECREASED');
        if (latest.status === 'READY' && latest.fully_settled && latest.open_claims === 0 && latest.cleanup_pending === 0 && latest.provider_post_count > before.provider_post_count && currency(latest.full_unknown_hold_USD) === 0n) {
          q.budget_after = latest; q.physical_provider_posts = latest.provider_post_count - before.provider_post_count; break;
        }
        await wait(200);
      }
      requireTrue(q.budget_after && q.physical_provider_posts >= 1, 'PUBLIC_PROVIDER_SETTLEMENT_NOT_CONFIRMED');
      requireTrue(q.physical_provider_posts <= MAX_REQUEST_POSTS, 'NATIVE_PER_QUESTION_PROVIDER_POST_BOUND_EXCEEDED');
      await drainObservers(phase); checkPhase(phase);
      requireTrue(q.completed_cited_answer && q.citation_checked, q.quality_failure_code || 'COMPLETED_CITED_QA_REQUIRED');
      q.status = 'PASS'; return q;
    } catch (error) {
      q.status = 'FAIL'; q.failure_code = error instanceof Boundary ? error.code : 'BROWSER_OR_IO_FAILURE';
      q.budget_at_failure = budgetTelemetry(cli['--budget-status'], sourceSHA, qualified.provider_route);
      if (q.t0_performance_ms === null && !page.isClosed()) {
        const clock = await page.evaluate(() => { const s = window.__cs30LivePaint01; return s ? { t0: s.t0, timeOrigin: s.timeOrigin } : null; }).catch(() => null);
        if (clock?.t0 !== null && clock?.t0 !== undefined) { q.t0_performance_ms = clock.t0; q.page_time_origin_ms = clock.timeOrigin; }
      }
      if (!q.answer_id) { q.tfirst_ms = null; q.tfull_ms = null; }
      if (q.page_time_origin_ms !== null && q.t0_performance_ms !== null) q.tfailure_ms ??= Math.max(0, Date.now() - q.page_time_origin_ms - q.t0_performance_ms);
      throw error;
    } finally { if (page && !page.isClosed()) await page.evaluate(() => window.__cs30LivePaint01?.dispose()).catch(() => {}); active = null; }
  }



  async function prepareScopedSession(item) {
    checkDeadline();
    await page.getByRole('button', { name: 'Learning workspace', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Your textbook library', exact: true })).toBeVisible();
    await expect.poll(() => Array.isArray(library) && library.some(book => book.id === fixture.book_id && book.release_id === fixture.release_id), { timeout: 15000 }).toBe(true);
    const book = library.find(entry => entry.id === fixture.book_id);
    requireTrue(book.title === fixture.book_title && book.release_id === fixture.release_id, 'OBSERVED_NORMAL_LIBRARY_BOOK_RELEASE_REQUIRED');
    const card = page.locator('.book-card').filter({ has: page.getByRole('heading', { name: book.title, exact: true }) });
    await card.getByRole('button', { name: 'Open textbook', exact: true }).click();
    await expect(page.getByRole('navigation', { name: 'Textbook chapters', exact: true })).toBeVisible();
    await expect.poll(() => observedSections.has(book.id), { timeout: 15000 }).toBe(true);
    const sections = observedSections.get(book.id);
    const normalized = value => value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    const topic = normalized(item.scope_topic);
    const matches = sections.items.filter(section => typeof section.id === 'string' && typeof section.title === 'string' && normalized(section.title).includes(topic));
    record.scope_resolution_attempts.push({ question_id: item.question_id, method: sections.method, route: sections.route,
      required_field: 'data[].title', authored_topic: item.scope_topic, normalized_topic: topic, response_sha256: sections.sha256,
      observed_section_count: sections.items.length, matched_section_titles: matches.map(section => section.title),
      selected_document_id: book.id, selected_release_id: book.release_id, resolution_scope: 'Normal published chapter titles; no whole-book fallback' });
    requireTrue(matches.length > 0, 'ACTUAL_NORMAL_CHAPTER_TOPIC_NOT_FOUND');
    matches.sort((a,b) => a.title.length-b.title.length || a.title.localeCompare(b.title));
    const section = matches[0];
    requireTrue(!record.selected_scopes.some(scope => scope.section_id === section.id), 'DIFFERENT_ACTUAL_CHAPTER_SCOPES_REQUIRED');
    const chapters = page.getByRole('navigation', { name: 'Textbook chapters', exact: true });
    await chapters.getByLabel('Search chapters', { exact: true }).fill(section.title);
    const chapterButton = chapters.getByRole('button').filter({ hasText: section.title });
    await expect(chapterButton).toHaveCount(1, { timeout: 15000 });
    await chapterButton.click();
    await expect.poll(() => observedReadingPages.has(book.id + ':' + section.id), { timeout: 15000 }).toBe(true);
    const reading = observedReadingPages.get(book.id + ':' + section.id);
    const units = reading.data.items.filter(unit => typeof unit.id === 'string' && unit.section_id === section.id && typeof unit.text === 'string' && unit.text.trim());
    requireTrue(units.length > 0, 'ACTUAL_NORMAL_SCOPED_READING_UNIT_REQUIRED');
    const words = topic.split(' ');
    units.sort((a,b) => words.filter(word => normalized(b.text).includes(word)).length - words.filter(word => normalized(a.text).includes(word)).length);
    const unit = units[0];
    const passage = page.locator('[id="reading-' + unit.id + '"]');
    await expect(passage).toBeVisible();
    await passage.getByRole('button', { name: 'Ask about this passage', exact: true }).click();
    const readingQuestion = page.locator('aside.reader-question[aria-label="Ask about your reading"]');
    const scopeSelect = readingQuestion.getByRole('combobox');
    await expect(scopeSelect).toHaveCount(1);
    await scopeSelect.selectOption({ label: 'Current chapter' });
    await expect(scopeSelect).toHaveValue('chapter');
    await page.getByLabel('Your question', { exact: true }).fill(item.question);
    const [sessionResponse] = await Promise.all([
      page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/sessions' && response.request().method() === 'POST'),
      page.getByRole('button', { name: 'Continue in chat', exact: true }).click(),
    ]);
    requireTrue([200,201].includes(sessionResponse.status()), 'NORMAL_READER_NEW_SESSION_ACCEPTANCE_REQUIRED');
    const session = (await sessionResponse.json())?.data;
    requireTrue(UUID.test(session?.id), 'ACTUAL_NORMAL_NEW_SESSION_ID_REQUIRED');
    await expect(page.getByRole('textbox', { name: 'Message Learning Assistant', exact: true })).toHaveValue(item.question);
    requireTrue(new URL(page.url()).pathname === '/chat/' + session.id, 'NORMAL_READER_DRAFT_SESSION_NAVIGATION_REQUIRED');
    // Use the existing product control. This removes the whole reading context,
    // so the observed chapter remains navigation provenance, not a RAG filter.
    const contextPanel = page.locator('.composer .reading-context');
    await expect(contextPanel).toBeVisible();
    await contextPanel.getByRole('button', { name: 'Remove reading context', exact: true }).click();
    await expect(contextPanel).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Message Learning Assistant', exact: true })).toHaveValue(item.question);
    const scope = { schema: '5703_week10_continuous_scope_observation_v1', batch_id: fixture.batch_id, source_version: sourceSHA,
      paired_leg_id: fixture.paired_leg_id, question_id: item.question_id, question_sha256: sha(item.question), session_id: session.id,
      document_id: book.id, document_version_id: book.document_version_id, release_id: book.release_id, book_title: book.title,
      section_id: section.id, section_title: section.title, source_unit_id: unit.id, reading_scope: null,
      navigation_reading_scope: 'chapter', retrieval_scope: 'all_active_corpus', chapter_filter_applied: false,
      normal_UI_reading_context_removed: true, source_identity_scope: 'Reader origin/navigation only; submitted RAG has no chapter or document filter',
      selection_sha256: sha(unit.text), selection_character_count: Array.from(unit.text).length,
      normal_UI_navigation: true, direct_http_calls: 0, direct_database_accesses: 0,
      observed_sections_api: { method: sections.method, route: sections.route, http_status: sections.http_status, sha256: sections.sha256 },
      observed_units_api: { method: reading.method, route: reading.route, http_status: reading.http_status, sha256: reading.sha256 },
      observed_utc: new Date().toISOString() };
    const bytes = JSON.stringify(scope,null,2) + '\n';
    const receiptPath = path.join(out, 'scope-' + item.question_id + '-public01.json');
    fs.writeFileSync(receiptPath, bytes, { flag: 'wx' });
    scope.public_pin = { path: receiptPath, bytes: Buffer.byteLength(bytes), sha256: sha(bytes) };
    if (fixture.continuous_scope_public_path) {
      const snapshot = ownedPath(fixture.continuous_scope_public_path, { absent: true });
      const temp = snapshot + '.next'; requireTrue(!fs.existsSync(temp), 'SCOPE_SNAPSHOT_TEMP_ALREADY_EXISTS');
      fs.writeFileSync(temp, bytes, { flag: 'wx' }); fs.renameSync(temp, snapshot);
    }
    record.selected_scopes.push(scope);
    return { sessionId: session.id, scope };
  }

  try {
    browser = await chromium.launch({ channel: 'msedge', headless: true, chromiumSandbox: true, timeout: 10000,
      args: ['--disable-gpu', '--renderer-process-limit=1', '--disable-background-networking', '--disable-component-update', '--no-first-run'],
      env: Object.fromEntries(['SystemRoot', 'WINDIR', 'COMSPEC', 'PATH', 'TEMP', 'TMP', 'APPDATA', 'LOCALAPPDATA'].filter(key => process.env[key]).map(key => [key, process.env[key]])) });
    record.actual_browser_version = browser.version();
    context = await browser.newContext({ viewport: { width: 1440, height: 960 }, ignoreHTTPSErrors: false, acceptDownloads: false, serviceWorkers: 'block' });
    await context.route('**/*', async route => {
      try {
        const request = route.request(), url = new URL(request.url());
        if (url.origin !== BASE && !['about:', 'data:', 'blob:'].includes(url.protocol)) {
          record.denied_external_requests.push({ protocol: url.protocol, host: safe(url.hostname, 200) }); return await route.abort();
        }
        if (url.origin === BASE && request.method() === 'POST') {
          if (/\/regenerate$|\/retry$|\/admin\/model-configurations\/.*\/(test|activate)$/.test(url.pathname)) throw new Boundary('UNPLANNED_PROVIDER_TRIGGER_BLOCKED');
          if (/^\/api\/v1\/sessions\/[^/]+\/messages$/.test(url.pathname)) {
requireTrue(active && ['Q1','Q2'].includes(active.record.label) && url.pathname === '/api/v1/sessions/' + active.record.session_id + '/messages' && active.routedMessagePosts === 0, 'FIRST_RETRY_DUPLICATE_OR_UNBOUND_MESSAGE_SUBMISSION_BLOCKED');
            requireTrue(record.page_errors.length === 0 && record.denied_external_requests.length === 0, 'BROWSER_ERRORS_BLOCK_NEW_QUESTION');
            gate(cli['--budget-status'], sourceSHA, qualified.provider_route, true, MIN_PROVIDER_SLOTS);
            const bodyBytes = request.postDataBuffer();
            requireTrue(bodyBytes && bodyBytes.length > 0 && bodyBytes.length <= 65536, 'BOUND_SUBMITTED_MESSAGE_BODY_REQUIRED');
            let body; try { body = JSON.parse(bodyBytes.toString('utf8')); } catch { throw new Boundary('SUBMITTED_MESSAGE_BODY_JSON_INVALID'); }
requireTrue(body && typeof body.content === 'string' && body.content === active.record.question.trim(), 'OBSERVED_EXACT_AUTHORED_QUESTION_REQUIRED');
            const scope = active.record.selected_scope, reader = body.reading_context;
            requireTrue(reader == null && scope.normal_UI_reading_context_removed === true && scope.retrieval_scope === 'all_active_corpus' && scope.chapter_filter_applied === false, 'NORMAL_UI_CONTEXT_REMOVAL_AND_UNFILTERED_RAG_REQUIRED');
            active.record.submitted_message_body = { method: 'POST', route: url.pathname, bytes: bodyBytes.length, sha256: sha(bodyBytes), content_sha256: sha(body.content), reading_scope: typeof body.reading_context?.scope === 'string' ? safe(body.reading_context.scope, 32) : null, document_id: typeof body.reading_context?.document_id === 'string' ? body.reading_context.document_id : null, source_unit_id: body.reading_context?.source_unit_id || null, section_id: null, selection_sha256: null, retrieval_scope: 'all_active_corpus', chapter_filter_applied: false, normal_UI_reading_context_removed: true, navigation_section_id: scope.section_id, scope: 'Digest of observed message body; raw body, headers and credentials are not saved' };
            active.routedMessagePosts++;
            active.record.routed_message_posts = active.routedMessagePosts;
            record.new_question_submissions++; if (active.record.label === 'Q2') record.second_question.status = 'ACTUAL_MESSAGE_POST_ROUTED';
          }
        }
        await route.continue();
      } catch (error) { retainObserverError(active, error instanceof Boundary ? error : new Boundary('REQUEST_BOUNDARY_ERROR')); await route.abort().catch(() => {}); }
    });
    context.on('page', extra => { if (context.pages().length > 1) { interrupted = true; void extra.close().catch(() => {}); } });
    page = await context.newPage(); requireTrue(context.pages().length === 1, 'SINGLE_PAGE_BOUNDARY');
    page.setDefaultTimeout(15000); page.setDefaultNavigationTimeout(15000);
    page.on('console', message => { record.console_type_counts[message.type()] = (record.console_type_counts[message.type()] || 0) + 1; });
    page.on('pageerror', () => { record.page_errors.push({ code: 'ACTUAL_PAGE_JAVASCRIPT_ERROR' }); });
    page.on('response', response => { const owner = active; const promise = observeResponse(response).catch(error => retainObserverError(owner, error)); pendingResponses.add(promise); void promise.finally(() => pendingResponses.delete(promise)); });
    await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' });
    await page.getByLabel('Email', { exact: true }).fill(fixture.learner_email); await page.getByLabel('Password', { exact: true }).fill(fixture.password);
    const [loginResponse] = await Promise.all([
      page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/login' && response.request().method() === 'POST'),
      page.getByRole('button', { name: 'Sign in', exact: true }).click(),
    ]);
    record.login_response_status = loginResponse.status();
    requireTrue(record.login_response_status === 200, 'NATIVE_LOGIN_REQUEST_REJECTED');
    await expect(page.getByRole('textbox', { name: 'Message Learning Assistant', exact: true })).toBeVisible();
    await expect(page.getByText('Live model', { exact: true }).first()).toBeVisible();
    const firstSession = await prepareScopedSession(expectedQuestions[0]);
    const first = await question('Q1', expectedQuestions[0].question, firstSession.sessionId, firstSession.scope);
    const latest = gate(cli['--budget-status'], sourceSHA, qualified.provider_route, true);
    if (first.status === 'PASS' && latest.remaining_provider_slots >= MIN_PROVIDER_SLOTS) {
      record.second_question = { status: 'ELIGIBLE_PENDING_SUBMISSION' };
      const secondSession = await prepareScopedSession(expectedQuestions[1]);
      await question('Q2', expectedQuestions[1].question, secondSession.sessionId, secondSession.scope);
      record.second_question.status = 'PASS'; record.status = 'ACTUAL_CONTINUOUS_TWO_SCOPED_QUESTIONS_PASS';
    } else {
      record.second_question = { status: 'NOT_EXECUTED_CAP', remaining_provider_slots: latest.remaining_provider_slots, reason: 'FEWER_THAN_TWO_REMAINING_PHYSICAL_PROVIDER_SLOTS' };
      record.status = 'ACTUAL_CONTINUOUS_FIRST_PASS_SECOND_NOT_EXECUTED_BOUND';
    }
    await drainObservers(null);
    requireTrue(!record.unbound_observer_error_code && record.questions.every(q => !q.observer_error_code), 'PUBLIC_RESPONSE_OBSERVER_ERRORS_PREVENT_JOURNEY_PASS');
    requireTrue(record.page_errors.length === 0 && record.denied_external_requests.length === 0, 'BROWSER_ERRORS_PREVENT_JOURNEY_PASS');
  } catch (error) {
    record.status = 'ACTUAL_LIVE_UI_JOURNEY_FAILED_OR_BLOCKED'; record.failure_code = error instanceof Boundary ? error.code : 'BROWSER_OR_IO_FAILURE'; process.exitCode = 1;
    const exceptionClass = error?.constructor?.name;
    record.failure_exception_class = typeof exceptionClass === 'string' && /^[A-Za-z][A-Za-z0-9_]{0,79}$/.test(exceptionClass) ? exceptionClass : 'Error';
    const sourceFrame = String(error?.stack || '').match(/real_browser_week10_continuous_scopes_PREPARED04\.cjs:(\d+):\d+/);
    record.failure_local_source_line = sourceFrame ? Number(sourceFrame[1]) : null;
    record.raw_exception_text_exported = false;
    if (record.second_question.status === 'NOT_YET_CONSIDERED') record.second_question = { status: 'NOT_EXECUTED_PRIOR_FAILURE', reason: record.failure_code };
    else if (record.second_question.status === 'ELIGIBLE_PENDING_SUBMISSION') record.second_question = { ...record.second_question, status: 'NOT_EXECUTED_PRE_SEND_FAILURE', reason: record.failure_code };
    else if (record.second_question.status === 'ACTUAL_MESSAGE_POST_ROUTED') record.second_question.status = 'FAIL';
    if (page && !page.isClosed()) { try { await publicCapture('retained-failure'); } catch { record.failure_capture_error = 'SAFE_CAPTURE_UNAVAILABLE'; } }
  } finally {
    clearTimeout(timer); process.removeListener('SIGINT', interrupt); process.removeListener('SIGTERM', interrupt);
    if (context) { try { await bounded(context.close(), 5000, 'CONTEXT_CLOSE_TIMEOUT'); record.context_closed = true; } catch { record.cleanup_error = 'CONTEXT_CLOSE_FAILED_OR_TIMED_OUT'; } }
    if (browser) { try { await bounded(browser.close(), 5000, 'BROWSER_CLOSE_TIMEOUT'); record.browser_closed = true; } catch { record.cleanup_error = 'BROWSER_CLOSE_FAILED_OR_TIMED_OUT'; } }
    try { await drainObservers(null); } catch { record.cleanup_error ??= 'PUBLIC_RESPONSE_OBSERVER_SETTLEMENT_TIMEOUT'; }
    for (const q of record.questions) if (q.observer_error_code) { q.status = 'FAIL'; q.failure_code ??= q.observer_error_code; }
    if (record.questions.find(q => q.label === 'Q2')?.status === 'FAIL' && record.second_question.status === 'PASS') record.second_question.status = 'FAIL';
    if (record.cleanup_error || record.unbound_observer_error_code || record.questions.some(q => q.status !== 'PASS') || record.page_errors.length > 0 || record.denied_external_requests.length > 0) {
      record.status = 'ACTUAL_LIVE_UI_JOURNEY_FAILED_OR_BLOCKED'; process.exitCode = 1;
      record.failure_code ??= record.cleanup_error || record.unbound_observer_error_code || record.questions.find(q => q.status !== 'PASS')?.failure_code || (record.page_errors.length > 0 || record.denied_external_requests.length > 0 ? 'LATE_BROWSER_OR_EXTERNAL_REQUEST_ERROR' : 'QUESTION_NOT_PASS');
    }
    for (const q of record.questions) {
      if (Number.isFinite(q.page_time_origin_ms) && Number.isFinite(q.t0_performance_ms)) {
        const sendEpoch = q.page_time_origin_ms + q.t0_performance_ms;
        q.worker_ready_to_Send_ms = sendEpoch >= driver.worker_ready_observed_epoch_ms ? sendEpoch-driver.worker_ready_observed_epoch_ms : null;
        q.process_launch_to_complete_answer_ms = Number.isFinite(q.tfull_ms) && sendEpoch >= driver.process_launch_epoch_ms ? sendEpoch-driver.process_launch_epoch_ms+q.tfull_ms : null;
      }
    }
    record.final_budget_observation = budgetTelemetry(cli['--budget-status'], sourceSHA, qualified.provider_route);
    record.completed_utc = new Date().toISOString(); record.elapsed_ms = Date.now() - started;
    record.script_sha256 = sha(fs.readFileSync(__filename));
    fs.writeFileSync(path.join(out, 'real-browser-live-qa-receipt01.json'), JSON.stringify(record, null, 2) + '\n', { flag: 'wx' });
    process.stdout.write(JSON.stringify({ status: record.status, question_count: record.questions.length, context_closed: record.context_closed, browser_closed: record.browser_closed, elapsed_ms: record.elapsed_ms }) + '\n');
  }
}

main().catch(error => { process.stderr.write(JSON.stringify({ status: 'BLOCKED_BEFORE_BROWSER_OR_PUBLIC_RECEIPT', code: error instanceof Boundary ? error.code : 'INPUT_OR_RUNTIME_INITIALIZATION_ERROR' }) + '\n'); process.exitCode = 1; });

