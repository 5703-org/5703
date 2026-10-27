"""Versioned answer-delivery policy and immutable source/identity contracts."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from app.core.config import Settings
from generation import answer_delivery_v1 as legacy, answer_delivery_target_v1 as target
from generation.parser import ResponseValidationError
from test_answer_delivery_v1 import fixture, IDENTITY

def target_fixture():
    packet,base,*_=fixture()
    base['properties']['requirements']['items']={'type':'object','properties':{
        'requirement_id':{'type':'string'},'sufficiency':{'type':'string'},'response_coverage':{'type':'string'}}}
    frozen,schema,wire=target.prepare(packet,base,IDENTITY)
    reply={'requirements':[{'requirement_id':'R1','response_coverage':'covered'}],
           'answer_delivery_audit':{'version':target.POLICY,'binding_sha256':frozen['binding_sha256'],
               'requirements':[{'requirement_id':'R1','quotes':[{'surface':'answer_text','quote':packet['PROPOSED_DELIVERY']['response']['answer_text']}]}]}}
    return packet,base,frozen,schema,wire,reply

def test_saved_policy_resolver_preserves_explicit_versions():
    assert legacy.resolve(None) is legacy
    assert legacy.resolve(legacy.POLICY) is legacy
    assert legacy.resolve(target.POLICY) is target

@pytest.mark.parametrize('policy',['', 'latest', 'answer_delivery_target_v2',42])
def test_unknown_version_fails_closed(policy):
    with pytest.raises(ValueError,match='INCOMPATIBLE'):legacy.resolve(policy)

def test_settings_default_legacy_and_off_and_invalid_rejected():
    settings=Settings(_env_file=None)
    assert settings.experimental_answer_delivery_audit_policy==legacy.POLICY
    assert settings.experimental_answer_delivery_audit_enabled is False
    with pytest.raises(ValidationError):Settings(_env_file=None,experimental_answer_delivery_audit_policy='latest')

def test_new_schema_hash_and_binding_are_effective_and_deterministic():
    packet,base,frozen,schema,wire,reply=target_fixture()
    assert frozen['version']==target.POLICY
    assert frozen['base_schema_sha256']==target.digest(target.target_schema(base))
    assert frozen['packet_sha256']==target.digest(packet)
    assert (frozen,schema,wire)==target.prepare(deepcopy(packet),deepcopy(base),dict(IDENTITY))
    assert target.prepare(packet,base,IDENTITY)[0]!=legacy.prepare(packet,base,IDENTITY)[0]
    result,receipt=target.unwrap(reply,packet,base,IDENTITY,frozen,schema)
    assert result['requirements']==reply['requirements'] and not receipt['decisions_rewritten']

@pytest.mark.parametrize('change',['owner','session','job','request','source','schema','version','frozen','surface'])
def test_cross_identity_source_schema_or_policy_response_is_rejected(change):
    packet,base,frozen,schema,wire,reply=target_fixture(); identity=dict(IDENTITY)
    if change in identity:identity[change]='other'
    if change=='source':packet['SOURCE_FRAGMENTS'][0]['exact_text']='Different source'
    if change=='schema':base['properties']['requirements']['minItems']=1
    if change=='version':reply['answer_delivery_audit']['version']=legacy.POLICY
    if change=='frozen':frozen['version']=legacy.POLICY
    if change=='surface':packet['PROPOSED_DELIVERY']['response']['answer_text']='Other answer'
    with pytest.raises(ResponseValidationError):target.unwrap(reply,packet,base,identity,frozen,schema)

@pytest.mark.parametrize('count',[0,2])
def test_ambiguous_schema_is_rejected_in_product_path(count):
    _,base,*_=target_fixture()
    if count==0:base={'type':'object'}
    else:base['other']=deepcopy(base['properties']['requirements'])
    with pytest.raises(ValueError,match='NODE_COUNT'):target.target_schema(base)

