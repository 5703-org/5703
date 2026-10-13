"""Finalize one result/report after all actual actions and independent review close."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import sys

sys.dont_write_bytecode = True
if sys.flags.optimize != 0:
    raise RuntimeError('FINALIZATION_REQUIRES_UNOPTIMIZED_GUARDS')
W = Path(__file__).resolve().parent
R = W/'5703-checker88-runtime'
M = Path('E:/5703/learning-assistant')
sys.path.insert(0, str(R))
import budget88
import prepare88
import page_bindings88_root

def need(ok, code):
    if not ok:
        raise RuntimeError(code)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def ref(path):
    raw = path.read_bytes()
    return {'workspace_relative_path':str(path.relative_to(W)).replace('\\','/'), 'bytes':len(raw), 'sha256':sha(raw)}

def replace_once(text, old, new):
    need(text.count(old) == 1, 'REPORT_REPLACEMENT_MUST_MATCH_ONCE')
    return text.replace(old, new, 1)

need(not (R/'results88.json').exists(), 'PRESERVE_EXISTING_UNIFIED_RESULTS')
state = budget88.snapshot(R/'cohort-ledger')
need(state['claimed_physical_posts'] <= 24 and Decimal(state['known_cost_USD']) <= Decimal('1.00'), 'BUDGET_EXCEEDED')
need(state['claimed_physical_posts'] == state['settled_posts'] and state['terminal_exposures'] == 0
     and state['unknown_full_hold_USD'] == '0' and state['cohort_stopped'] is False, 'FINANCIAL_CLOSURE_REQUIRED')
software = read(W/'software-verification88.json')
need(all((M/p).resolve().is_relative_to(M.resolve()) and not (M/p).is_symlink()
         and sha((M/p).read_bytes()) == pin for p,pin in software['production_and_test_source_pins'].items()), 'CURRENT_MAIN_SOURCE_DRIFT')
quality = read(W/'phase88-page-qualification-root.json')
need(quality['schema'] == 'phase88_root_derived_page_qualification_v1' and quality['case_id'] == 'case10b', 'ROOT_PAGE_REVIEW_REQUIRED')
need(type(quality['n']) is int and quality['n'] in (0,1)
     and quality['valid_page_latency_sample'] is (quality['n']==1), 'QUALIFICATION_COUNT_INVALID')
for row in quality['evidence']:
    p = W/row['workspace_relative_path']
    need(p.resolve().is_relative_to(W) and not p.is_symlink()
         and sha(p.read_bytes()) == row['sha256'], 'PAGE_REVIEW_EVIDENCE_CHANGED')
page_review_path = W/'5703-checker88-quality/page10b-review88.json'
page_review = read(page_review_path)
need(sha(page_review_path.read_bytes()) == quality['independent_review_sha256'] ==
     '127201e625481c6504b4785f698d6028dff83cf5f8cf5afb57b1191135270f61', 'EXACT_FRESH_PAGE_QA_PIN_REQUIRED')
if quality['n'] == 1:
    need(quality['independent_quality_status'] == page_review['status'] == page_review['independent_answer_QA'] == 'PASS'
         and page_review['reviewed_new_answer_independently_not_prior_case12_pass'] is True
         and all(page_review[k] is True for k in ('all_four_required_facets_complete','all_claims_and_units_supported',
                 'no_uncited_scientific_claim','no_scientific_critical_error_observed')), 'NEW_ANSWER_INDEPENDENT_QA_PASS_REQUIRED')
    actual = page_bindings88_root.closed_page_bindings()
    need(actual == quality['exact_actual_bindings'], 'ACTUAL_PAGE_BINDINGS_CHANGED')
    for k in ('session_id','request_id','job_id','answer_id','response_body_sha256_UTF8',
              'response_DTO_sha256_python_canonical','raw_envelope_sha256_UTF8','complete_visible_prose_sha256_UTF8'):
        need(page_review['exact_answer'][k] == actual[k], 'NEW_PAGE_ANSWER_QA_JOIN_REQUIRED')
    need(page_review['question_sha256'] == actual['question_sha256']
         and page_review['source_bindings']['source_version_sha256'] == actual['source_version_sha256']
         and page_review['source_bindings']['scope_sha256'] == actual['scope_sha256']
         and page_review['config_bindings']['checker_config_canonical_sha256'] == actual['checker_config_sha256_python_canonical']
         and page_review['config_bindings']['context_sha256'] == actual['checker_context_sha256']
         and quality['complete_answer_latency_ms'] == actual['observed_send_to_complete_dom_ms']
         == page_review['DOM_and_clock']['send_to_complete_DOM_ms'], 'NEW_PAGE_SOURCE_CONFIG_CLOCK_JOIN_REQUIRED')
else:
    need(quality['complete_answer_latency_ms'] is None, 'UNQUALIFIED_PAGE_CLOCK_MUST_BE_NULL')
need(quality['TTFT_ms'] is None and quality['stable_p95_ms'] is None, 'NO_TTFT_OR_P95_INFERENCE')
need(state['case_posts'].get('case10',0) == 0, 'ORIGINAL_PAGE_HAS_POSTS')
budget88.validate_page_successor_reconciliation(R/'cohort-ledger', admission=False)
reconciliation = R/'case10-no-send-reconciliation88.json'
need(sha(reconciliation.read_bytes()) == 'd4ced1b5be3a552fb7c48ceac2e302ca24619b39e419aecda2ea0882b16a2817', 'ORIGINAL_ZERO_POST_PIN_CHANGED')
need(not (R/'case10/api-closure77.json').exists()
     and not (R/'case10/native-provider70/final-receipt.json').exists(), 'PRESERVE_MISSING_ORIGINAL_RECEIPTS')
qa12 = read(W/'5703-checker88-quality/case12-eligibility88.json')
need(sha((W/'5703-checker88-quality/case12-eligibility88.json').read_bytes()) ==
     '4bdcd508e94a5ce99966c2cf4ec15a325b08f3bd71e6f87f889592edda493c7f'
     and qa12['status'] == 'PASS' and qa12['all_four_required_facets_complete'] is True
     and qa12['no_uncited_scientific_claim'] is True, 'SAVED_API_INDEPENDENT_QA_CHANGED')
low = read(W/'5703-checker88-quality/low-pair-review88.json')
need(low['full_application_boundaries']['LOW_pipeline_or_page_qualified'] is False, 'LOW_NOT_QUALIFIED')
need(sha((W/'5703-checker88-quality/low-pair-review88.json').read_bytes()) ==
     'f7ce9fd1b149b832918adf04d912d496790a63c73343c7e68127d9df0bb877e4', 'LOW_REVIEW_CHANGED')
low_final = read(R/'component07low/final-receipt.json')
low_financial = read(R/'component07low/financial.json')
need(low_final['physical_posts'] == 1 and low_final['publication_exercised'] is False
     and Decimal(low_financial['numeric_gateway_cost_USD']) == Decimal('0.0118001'), 'LOW_DIAGNOSTIC_ACCOUNTING_CHANGED')
# The reviewed runtime builder is evaluated in memory; no final file is created
# before all report text and output paths pass their checks.
captured = {}
original_create = prepare88.create
def capture_result(path, value):
    need(path == R/'results88.json' and not captured, 'ONLY_UNIFIED_RESULT_CAPTURE_ALLOWED')
    captured['result'] = value
prepare88.create = capture_result
try:
    result = prepare88.write_final_results()
finally:
    prepare88.create = original_create
need(captured.get('result') is result and not (R/'results88.json').exists(), 'PURE_RESULT_BUILD_REQUIRED')
need(result['cohort_financial'] == state, 'JOURNAL_CHANGED_DURING_FINALIZATION')
for case in result['cases']:
    if case['case_id'] == 'case10':
        case.update(status='STARTUP_STOP_BEFORE_SEND_ZERO_PHYSICAL_POSTS',
            original_API_closure_available=False, original_native_financial_receipt_available=False,
            missing_original_receipts_not_filled_or_certified=True,
            zero_physical_posts_verified_by_journal=True,
            separate_reconciliation=ref(R/'case10-no-send-reconciliation88.json'),
            original_outer_terminal=read(R/'case10/root-page-terminal88.json'))
result.update(finished_UTC=datetime.now(timezone.utc).isoformat(),
    current_software_verification=software,
    independent_quality_reviews=[ref(W/'5703-checker88-quality/independent-review88.json'),
                                 ref(W/'5703-checker88-quality/case12-eligibility88.json')],
    reasoning_support=ref(W/'phase88-reasoning-support.json'),
    one_LOW_component_diagnostic={
        'component_id':'component07low','physical_POSTs':1,'known_cost_USD':'0.0118001',
        'UNKNOWN_USD':'0','pipeline_or_page_qualified':False,
        'actual_result':read(R/'component07low/diagnostic-result.json'),
        'financial':read(R/'component07low/final-receipt.json'),
        'independent_review':ref(W/'5703-checker88-quality/low-pair-review88.json'),
        'evidence':[ref(p) for p in sorted((R/'component07low').glob('*.json'))]},
    derived_actual_page_qualification=quality,
    project_or_course_acceptance_complete=False,
    original_receipts_rewritten=False,
    no_automatic_retry_or_new_paid_batch=True)
raw = (json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8')
result_sha = sha(raw)
posts, cost = state['claimed_physical_posts'], state['known_cost_USD']
page_text = quality['report_sentence']
text = (W/'phase88-report-draft.md').read_text(encoding='utf-8')
text = replace_once(text, '11 October 2026. Working draft awaiting Root\'s final cases, accounting and publication.',
                    '11 October 2026. Final bounded Phase88 result; original failures and separate historical records retained.')
start = text.index('**Current software verification progressed;')
end = text.index('\n\n## Changes',start)
text = text[:start]+f'**Current unit verification passed; reliable scientific release and course acceptance remain incomplete.** The repaired source version passed 4,532 unit tests with 21 skips, 40 warnings and 215 additional subtests. Case12\'s complete API answer passed independent scientific and own-source review. {page_text} The LOW checker diagnostic failed conformance and missed a scientific negative. Final accounting is {posts} physical POSTs/USD{cost}/UNKNOWN0 within 24/USD1.00; project completion remains false.'+text[end:]
text = replace_once(text, 'Independent scientific/source review remains pending.',
    'Independent scientific/source review PASS for all four requested facets and all 12 units. R004\'s requirement-row evidence alone omits membrane support; the answer\'s own C004 selection includes it and was independently checked.')
text = replace_once(text, "\n\nCase12's terminal observation",
    f"\n| 10b: fresh native page answer | 2 /0.0235195 | {page_text} |\n| LOW: same saved case07 checker input | 1 /0.0118001 | Complete JSON rejected by the own-parent selection codec; recognizer-reversal negative missed. No accepted answer or page sample. |\n\nCase12's terminal observation")
text = replace_once(text, 'Independent quality PASS is required before a page timing attempt. Current DOM n=0; complete-page time, TTFT and stable p95 remain null. Failure durations and clarification time are excluded from completed-answer latency. **[ROOT TO FILL: case12 independent review and any separately qualified page result.]** Any later page result needs its own actual-answer quality review.',
    f'Independent quality PASS preceded the page attempt. Original case10 stopped before Send after 13.1383751 s because the listener PID did not match the launcher PID; its actual listener was not recorded. Two owned process trees closed, and the shared journal proves zero case10 POSTs. Original API/financial closing receipts remain absent; the separate reconciliation does not manufacture them. A synthetic installed-venv probe independently observed a direct launcher child with a different PID. One separately frozen case10b was admitted after the common runtime ownership repair. {page_text} Original technical receipts remain QA_PENDING/n0; any qualified n=1 is a separately bound independent-review result. TTFT and stable p95 remain null. Failure durations and clarification time are excluded from completed-answer latency.')
text = replace_once(text, 'The proposed LOW comparison remains **[ROOT TO FILL: actual paired results or explicitly NOT_RUN]**; no conformance, quality or speed benefit is inferred before it completes.',
    'The one LOW diagnostic used the same saved HIGH input; structural wire fields and messages match except effort. HIGH used 8,188 output/6,647 reasoning tokens, finished length and took 16,452 provider ms. LOW used 1,733 output/0 reported reasoning tokens, finished stop and took 5,151 provider ms (5,154 adapter ms), costing USD0.0118001. LOW still failed the full codec: C004/U04 selected F013 outside its parent\'s selected fragments. Raw output detected the uncited C001 negative but missed the C006 recognizer reversal (1/2 negatives), with additional positive proof gaps. There was no accepted hydrated judgment, semantic/publication execution, release or default enablement. This ordered n=1 failed-output pair supplies no success-quality speedup or p95 proof. Keep mandatory effort controls for a future controlled evaluation and repair complete own-parent selection and relation judgments before considering activation; do not keep increasing total output capacity or silently repair returned fields.')
old = 'Closed 18/USD0.1954720/UNKNOWN0 leaves six slots/USD0.8045280 before further execution. All owned runtime threads closed and five protected historical metadata groups stayed unchanged. **[ROOT TO FILL: final contiguous journal and accounting after any later pair/page execution.]**'
new = f'Final {posts} claims have {state["settled_posts"]} numeric settlements and zero exposures/UNKNOWN; known charge USD{cost}, leaving {24-posts} physical slots/USD{Decimal("1.00")-Decimal(cost)} arithmetically. Ordinary case entitlement remained eight; one distinct LOW component and one finite case10b entitlement were used. This result does not create another trial entitlement or automatically spend the remainder. Closed API cases retain five unchanged historical metadata groups and owned-thread closure. Case10\'s forced startup stop retains the narrower process/journal evidence and missing normal closure; it is not promoted to API or scientific acceptance.'
text = replace_once(text, old,new)
text = replace_once(text, 'Root will finalize one unified `5703-checker88-runtime/results88.json` and this compact report, retaining originals rather than creating micro-archives.',
    'One unified result and this compact report retain original observations and independent-review boundaries.')
text = replace_once(text, '**[ROOT TO FILL: final source/evidence index, results SHA256, publication path and independent readback.]**',
    f'Portable evidence: [unified results](20261011-checker88-evidence/results88.json) (SHA256 `{result_sha}`), [software verification](20261011-checker88-evidence/software-verification88.json), [independent answer review](20261011-checker88-evidence/independent-review88.json), [LOW pair review](20261011-checker88-evidence/quality/low-pair-review88.json), and `readback-manifest88.json` in the same evidence folder. Publication readback verifies exact copied bytes and preserved ledger prefixes. The 8 MB evidence bound covers payload files; report, manifest and small ledger appends are additional.')
text = replace_once(text, 'Authentication and sealed rubrics/Gold are excluded from the report and model payloads.',
    'Authentication remains memory-only and is excluded from evidence and model payloads; sealed rubrics/Gold are excluded from model payloads and full sealed files are not published.')
need('[ROOT TO FILL' not in text and 'Working draft' not in text, 'UNFILLED_REPORT')
need(quality['technical_receipt_status'] == read(R/'case10b/root-page-terminal88.json')['status'], 'TECHNICAL_STATUS_CHANGED')
if quality['technical_receipt_status'] != 'TECHNICAL_JOURNEY_COMPLETE_QA_PENDING':
    text = replace_once(text, 'Original technical receipts remain QA_PENDING/n0;',
                        f"Original case10b technical status is `{quality['technical_receipt_status']}` with qualified n0;")
text += '\n\nActual Phase88 teacher/checker: `anthropic/claude-haiku-5.5` / `google/gemini-3.5-flash-lite`, through OpenRouter with frozen profiles `haiku55_google_vertex_low_v1` / `gemini35_google_vertex_high_research_v1`. These profile names and wire controls do not independently certify provider routing beyond the recorded responses. Default V22/checker settings were not enabled by these opt-in experiments.\n'
if quality['n'] == 1:
    text = replace_once(text, 'quality-qualified full-page timing;', 'additional quality-qualified full-page timing samples;')
outputs = [(R/'results88.json',raw), (W/'phase88-final-report.md',text.encode('utf-8'))]
for leaf,heading in [('phase88-progress-append.md','Phase88 bounded common repair result'),
                     ('phase88-handover-append.md','Phase88 continuation and evidence')]:
    content = f'\n\n### 2026-10-11 — {heading}\n\nCurrent `generation/checked.py` SHA2b675807b299c2d802eda90ef6dfd10beaeac9a7737ec2dfe40279f66862515b; current unit suite 4,532 PASS/21 skips/40 warnings plus 215 subtests. Two fixture-only corrections retain production eligibility. Case12 independent answer QA PASS; {page_text} LOW component codec FAIL and recognizer negative missed; no LOW default activation. Final Phase88 {posts} POSTs/USD{cost}/UNKNOWN0; no retry or new trial entitlement. Old case10 startup-stop records and missing API/financial closure remain preserved with separate zero-POST reconciliation.\n\nReport: `docs/execution/20261011-checker88-common-contract-results.md`; one evidence folder `docs/execution/20261011-checker88-evidence/`, unified results SHA256 `{result_sha}`. Protected inputs/results, prior deliveries and existing document prefixes retained. Course/project completion remains false: scientific false-release/false-block reliability, heldout RAG and Human Gold, AC-44 warm-p95/quality margin, clean/full-workflow verification, physical-device and final owner deliveries remain open. Continue from these exact source/configuration/quality bindings; do not reuse old claims or promote historical DEV/API timings to heldout/page acceptance.\n'
    outputs.append((W/leaf,content.replace('2026-10-11 ��','2026-10-11 —').encode('utf-8')))
need(all(not path.exists() and path.resolve().is_relative_to(W) for path,_ in outputs), 'PRESERVE_PREVIOUS_FINAL_OUTPUTS')
need(budget88.snapshot(R/'cohort-ledger') == state, 'JOURNAL_CHANGED_BEFORE_FINAL_CREATE')
for path,data in outputs:
    with path.open('xb') as stream:
        stream.write(data)
    need(path.read_bytes() == data, 'FINAL_OUTPUT_READBACK_FAILED')
print(json.dumps({'status':'FINALIZED','posts':posts,'known_USD':cost,'UNKNOWN_USD':'0','results_sha256':result_sha,
                  'qualified_page_n':quality['n'],'report_bytes':(W/'phase88-final-report.md').stat().st_size}))
