"""Restrictive current scope is not a request to guess an absent antecedent."""
from copy import deepcopy
import pytest
from conversation import query_v25, reference_ownership as guard

POSITIVE = [
    "Compare a circuit at 3 V and 5 V. Limit the conclusion to these recorded conditions.",
    "Describe evaporation at 20 degrees Celsius and 30 degrees Celsius. Restrict the explanation to these measurements.",
    "Compare plant growth after 7 days and 14 days. Limit your comparison to these observations.",
    "Compare the quoted rates of 4% and 6%. Restrict the discussion to these stated values.",
    "Using Chemistry 2e Table 14.2 and both numbered notes, compare the HCl and CH3CO2H titrations after 20.0 mL of NaOH is added. State both pH values and which is higher, the initial volume and concentration of each acid, the NaOH concentration, and the added NaOH amount in mol. Limit the conclusion to these recorded conditions.",
]
NEGATIVE = [
    "Limit the conclusion to these recorded conditions.",
    "Compare rainfall. Limit the conclusion to these conditions.",
    "Using Table 14.2, compare rainfall. Limit the conclusion to these conditions.",
    "Compare it at 3 V and 5 V. Limit the conclusion to these recorded conditions.",
    "A motor and a generator run at 3 V. Why does it fail? Limit the conclusion to these conditions.",
    '"Compare a circuit at 3 V and 5 V." Limit the conclusion to these recorded conditions.',
    "No measurements were recorded at 3 V. Limit the conclusion to these conditions.",
    "Compare the previous experiment at 3 V. Limit the conclusion to these conditions.",
    "Compare a circuit at 3 V and 5 V. Explain why these conditions cause it.",
    "Compare a circuit at 3 V and 5 V. Limit the conclusion to these recorded conditions. Why does it fail?",
    "Compare a circuit at 3 V and 5 V. Limit the conclusion to those unknown conditions.",
]
HISTORY=[{'message_id':'old-u','role':'user','content':'Explain ocean tides.'},
         {'message_id':'old-a','role':'assistant','content':'Synthetic prior explanation about ocean tides.'}]

@pytest.mark.parametrize('question',POSITIVE)
@pytest.mark.parametrize('history',[[],HISTORY])
def test_complete_current_request_preserved(question,history):
    base=query_v25.prepare_query(question,history).model_dump();before=deepcopy(base)
    result,record=guard.apply(base,guard.POLICY)
    assert not result['needs_clarification']
    assert result['standalone_query']==question and result['referenced_message_ids']==[]
    assert record['eligible'] and record['history_consulted'] is False
    assert record['semantic_sufficiency'] is None and base==before
    span=record['complete_local_audits'][0]['reference_span']
    assert question[span['start']:span['end']].lower()=='these'

@pytest.mark.parametrize('question',NEGATIVE)
def test_scope_rule_does_not_license_ambiguous_or_unasserted_conditions(question):
    assert guard._restrictive_scope_audit(question) is None
    base=query_v25.prepare_query(question,[]).model_dump()
    expected=guard.apply(base,guard.LEGACY_POLICY)[0]
    assert guard.apply(base,guard.POLICY)[0]==expected

@pytest.mark.parametrize('question',POSITIVE+NEGATIVE)
def test_old_frozen_policy_retains_prior_behavior(question):
    base=query_v25.prepare_query(question,HISTORY).model_dump()
    old,audit=guard.apply(base,guard.LEGACY_POLICY)
    assert audit is None or audit['policy']=='current_message_ownership_v1'
    assert guard.audit(question,guard.LEGACY_POLICY)==guard._audit_v1(question)
    assert guard.apply(base,None)==(base,None)

def test_all_measurement_spans_match_the_original():
    q=POSITIVE[0];a=guard._restrictive_scope_audit(q)
    spans=a['complete_local_audits'][0]['quantity_spans']
    assert [q[x['start']:x['end']] for x in spans]==['3 V','5 V']
