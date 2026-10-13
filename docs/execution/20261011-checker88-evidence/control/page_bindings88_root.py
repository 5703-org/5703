"""Public-only exact bindings for the already closed case10b answer."""
from pathlib import Path
import hashlib
import json
import math

W=Path(__file__).resolve().parent
R=W/'5703-checker88-runtime'
def need(ok,code):
    if not ok:
        raise RuntimeError(code)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def read(path):
    return json.loads(path.read_bytes())

def closed_page_bindings():
    case=R/'case10b'
    scope=read(R/'scope88-case10b.json')
    descriptor=read(R/'supplement88-case10b.json')
    terminal=read(case/'root-page-terminal88.json')
    journey=read(case/'journey-receipt88.json')
    closure=read(case/'api-closure77.json')
    checker=read(case/'native-provider70/slot-02-normal-outcome.json')
    native=read(case/'native-provider70/final-receipt.json')
    raw=journey['answer_public_envelope_raw_utf8'].encode('utf-8')
    envelope=json.loads(raw)
    answer=envelope['data']
    response=answer['response']
    need(sha((R/'scope88-case10b.json').read_bytes()) ==
         '8a92770cffda58f62d9fa3bd444eda9267255fcd6359a4c6f3208b9a4e42cd24','EXACT_PAGE_SCOPE_CHANGED')
    need(terminal['journey_sha256']==sha((case/'journey-receipt88.json').read_bytes())
         and terminal['closure_sha256']==sha((case/'api-closure77.json').read_bytes())
         and terminal['financial_sha256']==sha((case/'native-provider70/final-receipt.json').read_bytes()),'CLOSURE_RECEIPT_PIN_CHANGED')
    need(terminal['status']=='TECHNICAL_JOURNEY_COMPLETE_QA_PENDING'
         and journey['status']=='NORMAL_PRODUCT_SINGLE_JOURNEY_PASS'
         and terminal['qualified_complete_answer_n']==journey['n']==0
         and terminal['independent_quality_status']==journey['independent_quality_status']=='PENDING',
         'PRESERVE_TECHNICAL_QA_PENDING_ORIGINALS')
    need(terminal['new_message_submissions']==journey['new_message_submissions']==1
         and terminal['actual_posts']==2 and terminal['automatic_retries']==0
         and terminal['numeric_closed'] is True and terminal['owned_threads_closed'] is True
         and terminal['five_old_metadata_groups_unchanged'] is True
         and terminal['native_unresolved_full_protection_USD']=='0E-7'
         and terminal['native_settled_known_cost_USD']=='0.0235195', 'CLOSED_SINGLE_JOURNEY_REQUIRED')
    need(all(row['closed'] and row['reader_closed'] for row in terminal['owned_process_cleanup'].values()),'OWNED_PROCESS_CLOSURE_REQUIRED')
    need(journey['browser_closed'] and journey['sources_reopened_after_reload']
         and journey['refreshed_answer_preserved'] and journey['refreshed_citations_preserved']
         and journey['complete_visible_prose_sha256_UTF8']==sha(journey['complete_visible_prose'].encode('utf-8'))
         and journey['answer_public_envelope_raw_sha256']==sha(raw)
         and journey['response']==response, 'VISIBLE_AND_RAW_ANSWER_BINDING_REQUIRED')
    need(terminal['observed_DOM_n']==journey['DOM_observation_n']==journey['completed_answer_n']==1,
         'ONE_COMPLETE_DOM_REQUIRED')
    clock=journey['send_to_complete_dom_ms']
    need(type(clock) in (float,int) and math.isfinite(clock) and clock>0
         and terminal['observed_send_to_complete_dom_ms']==clock,'FINITE_COMPLETE_DOM_CLOCK_REQUIRED')
    for field in ('request_id','job_id'):
        need(answer[field]==journey['accepted'][field]==closure['accepted'][field]==closure['worker'][field],
             'NEW_ANSWER_JOB_REQUEST_JOIN_REQUIRED')
    need(answer['id']==journey['answer_id']==closure['worker']['answer_id']
         and journey['session_id']==closure['session_id'] and answer['status']=='answered'
         and response['short_answer'] is None, 'NEW_FULL_BODY_JOIN_REQUIRED')
    need(scope['supplement_descriptor_sha256']==sha((R/'supplement88-case10b.json').read_bytes())
         and journey['question_sha256']==scope['question_sha256']
         and journey['source_version_sha256']==descriptor['instance_source_version_sha256']
         and checker['error'] is None and checker['finish_reason']=='stop', 'SOURCE_AND_COMPLETE_CHECKER_BINDING_REQUIRED')
    return {'case_id':'case10b','scope_sha256':sha((R/'scope88-case10b.json').read_bytes()),
            'question_sha256':journey['question_sha256'],'session_id':journey['session_id'],
            'request_id':answer['request_id'],'job_id':answer['job_id'],'answer_id':answer['id'],
            'response_body_sha256_UTF8':sha(response['answer_text'].encode('utf-8')),
            'response_DTO_sha256_python_canonical':sha(canonical(response)),
            'raw_envelope_sha256_UTF8':sha(raw),
            'complete_visible_prose_sha256_UTF8':sha(journey['complete_visible_prose'].encode('utf-8')),
            'source_version_sha256':journey['source_version_sha256'],
            'teacher_config_sha256_python_canonical':sha(canonical(scope['expected_model_config'])),
            'checker_config_sha256_python_canonical':sha(canonical(scope['expected_checker_config'])),
            'checker_output_policy':scope['expected_settings']['chat_checker_output_policy'],
            'checker_context_sha256':checker['diagnostic']['checker_transport']['context_sha256'],
            'observed_send_to_complete_dom_ms':clock,
            'technical_receipt_status':terminal['status'],'new_page_physical_POSTs':2,
            'new_page_known_cost_USD':'0.0235195'}
