"""Derive qualification from the immutable actual page and fresh independent QA."""
from datetime import datetime, timezone
import json
import page_bindings88_root as p

W,R=p.W,p.R
review_path=W/'5703-checker88-quality/page10b-review88.json'
review_raw=review_path.read_bytes()
p.need(p.sha(review_raw)=='127201e625481c6504b4785f698d6028dff83cf5f8cf5afb57b1191135270f61','EXACT_FRESH_INDEPENDENT_REVIEW_REQUIRED')
review=json.loads(review_raw)
bindings=p.closed_page_bindings()
p.need(review['schema']=='phase88_independent_fresh_page10b_quality_review_v1'
       and review['status']==review['independent_answer_QA']=='PASS'
       and review['reviewed_new_answer_independently_not_prior_case12_pass'] is True,
       'FRESH_ACTUAL_ANSWER_INDEPENDENT_QA_REQUIRED')
for key in ('all_four_required_facets_complete','all_claims_and_units_supported',
            'no_uncited_scientific_claim','no_scientific_critical_error_observed'):
    p.need(review[key] is True,'COMPLETE_SCIENTIFIC_AND_OWN_SOURCE_QA_REQUIRED')
for key,value in review['exact_answer'].items():
    if key in bindings:
        p.need(bindings[key]==value,'INDEPENDENT_EXACT_ANSWER_BINDING_MISMATCH')
p.need(review['question_sha256']==bindings['question_sha256']
       and review['source_bindings']['source_version_sha256']==bindings['source_version_sha256']
       and review['source_bindings']['scope_sha256']==bindings['scope_sha256']
       and review['config_bindings']['checker_config_canonical_sha256']==bindings['checker_config_sha256_python_canonical']
       and review['config_bindings']['context_sha256']==bindings['checker_context_sha256']
       and review['DOM_and_clock']['send_to_complete_DOM_ms']==bindings['observed_send_to_complete_dom_ms']
       and review['DOM_and_clock']['independent_review_supports_Root_deriving_one_qualified_complete_answer_sample'] is True,
       'INDEPENDENT_SOURCE_CONFIG_DOM_BINDING_MISMATCH')
evidence=[]
for row in review['inputs']:
    path=W/row['path']
    p.need(path.resolve().is_relative_to(W) and path.is_file() and not path.is_symlink()
           and p.sha(path.read_bytes())==row['sha256'],'INDEPENDENT_REVIEW_INPUT_CHANGED')
    evidence.append({'workspace_relative_path':row['path'],'bytes':row['bytes'],'sha256':row['sha256']})
for path in (review_path,R/'scope88-case10b.json',R/'supplement88-case10b.json',
             W/'page_bindings88_root.py',W/'qualify_page88_root.py'):
    raw=path.read_bytes()
    evidence.append({'workspace_relative_path':str(path.relative_to(W)).replace('\\','/'),
                     'bytes':len(raw),'sha256':p.sha(raw)})
result={'schema':'phase88_root_derived_page_qualification_v1','case_id':'case10b',
        'created_utc':datetime.now(timezone.utc).isoformat(),'independent_quality_status':'PASS',
        'n':1,'valid_page_latency_sample':True,
        'complete_answer_latency_ms':bindings['observed_send_to_complete_dom_ms'],
        'TTFT_ms':None,'stable_p95_ms':None,'meets_5_to_10_second_goal':False,
        'technical_receipt_status':bindings['technical_receipt_status'],
        'exact_actual_bindings':bindings,
        'independent_review_sha256':p.sha(review_raw),
        'original_technical_QA_PENDING_and_qualified_n0_preserved':True,
        'old_case10_promoted_or_retried':False,'evidence':evidence,
        'report_sentence':"Case10b's fresh answer passed independent scientific and own-source review (four claims, nine units and four requested facets); one qualified Send-to-complete-DOM sample is 20.4371 s. Refresh preserved all prose and nine citation labels, and Sources reopened. This exceeds the 5–10 s target; n=1 establishes no stable p95, LLM TTFT or speedup.",
        'project_or_course_acceptance_complete':False}
target=W/'phase88-page-qualification-root.json'
with target.open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2,ensure_ascii=False,allow_nan=False)
p.need(json.loads(target.read_bytes())==result,'DERIVED_QUALIFICATION_READBACK_FAILED')
print(json.dumps({'status':'PASS','qualified_page_n':1,'complete_answer_ms':result['complete_answer_latency_ms'],
                  'qualification_sha256':p.sha(target.read_bytes())}))
