"""Retain exact public selected-source and metadata projections; no execution rerun."""
import hashlib
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
MAIN = Path('E:/5703/learning-assistant')
Q = HERE.parent / 'component-rag-quality08'
ACTUAL = Q / 'actual08e'
sys.path[:0] = [str(MAIN), str(MAIN / '.venv/Lib/site-packages')]
from generation.checker_encoding import decode
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
def new(name, value):
    with (HERE / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return pin(HERE / name)
result = read(ACTUAL / 'RESULT08.json')
assert pin(ACTUAL / 'RESULT08.json')['sha256'] == 'e5a82ffa7056af68eb16c1de0b05877e2dc42ab01df7f72ad5c6fee22aeaa1a5'
manifest = read(Q / 'preflight08e/PREFLIGHT_MANIFEST08.json')
for relative, expected in manifest['main_source_and_prompt_fingerprints'].items():
    observed = pin(MAIN / relative)
    assert all(observed[key] == expected[key] for key in ('bytes', 'sha256'))
pack = {'status': 'ROOT_EXTRACTED_EXACT_ACTUAL_SELECTED_TEXT_NOT_ENTAILMENT_CERTIFICATION',
        'actual_result_pin': pin(ACTUAL / 'RESULT08.json'), 'arms': {},
        'child_read_approval_timeout_is_not_unsafe_judgment': True,
        'API_calls': 0, 'DB_access': False, 'native_or_credentials_read': False}
metadata = {'status': 'ROOT_PUBLIC_METADATA_EXTRACTION_PASS_NOT_INDEPENDENT_REVIEW',
            'actual_result_pin': pin(ACTUAL / 'RESULT08.json'),
            'production_source_count': len(manifest['main_source_and_prompt_fingerprints']),
            'all_production_source_pins_current': True, 'ledger': result['ledger'],
            'prior08d_UNKNOWN_hold_USD': '0.03', 'prior08d_UNKNOWN_not_cleared': True,
            'native_Send_to_DOM_ms': None, 'arms': [], 'API_calls': 0, 'DB_access': False}
for row in result['arms']:
    arm = row['arm']
    checks = row['outcome']['checks']
    assert row['status'] == 'COMPLETED' and len(checks) == 1 and checks[0]['accepted']
    wires = []
    for role in ('generation', 'joint_check'):
        actual_path = ACTUAL / (arm + '-' + role + '-actual-wire08.json')
        planned_path = ACTUAL / (arm + '-' + role + '-planned-wire08.json')
        actual, planned = read(actual_path), read(planned_path)
        assert actual['payload'] == planned['payload']
        assert actual['original_body_sha256'] == planned['body_sha256']
        raw_path = ACTUAL / (arm + '-' + role + '-raw-provider-read01.json')
        assert raw_path.is_file()
        wires.append({'role': role, 'actual_wire_pin': pin(actual_path),
                      'original_body_sha256': actual['original_body_sha256'],
                      'planned_equals_actual': True, 'raw_response_pin': pin(raw_path)})
    wire = read(ACTUAL / (arm + '-joint_check-actual-wire08.json'))
    data = decode(json.loads(wire['payload']['messages'][-1]['content']))
    claims = {item['claim_id']: item for item in data['CLAIMS']}
    fragments = {(f['evidence_id'], f['fragment_id']): f for f in data['SOURCE_FRAGMENTS']}
    raw_checker = json.loads(read(ACTUAL / (arm + '-joint_check-provider-result08.json'))['raw_text'])
    items = []
    for selection in raw_checker['claims']:
        claim = claims[selection['claim_id']]
        selected = []
        for citation in selection['citations']:
            for fragment_id in citation['fragment_ids']:
                selected.append(fragments[(citation['evidence_id'], fragment_id)])
        items.append({'actual_claim': claim, 'actual_checker_selection': selection,
                      'actual_selected_source_fragments': selected})
    pack['arms'][arm] = {'actual_response': row['outcome']['response'], 'claims': items,
                         'raw_attempt_evaluation_ok': raw_checker.get('attempt_evaluation_ok'),
                         'normalization': checks[0]['attempt_evaluation_assessment'],
                         'unselected_reference_F016_for_Dense_claim2_only': fragments.get(('ev_004', 'F016')) if arm == 'Dense5' else None}
    metadata['arms'].append({'arm': arm, 'status': row['status'],
                             'component_generation_elapsed_ms': row['component_generation_elapsed_ms'],
                             'wire_receipts': wires, 'actual_claim_count': len(items),
                             'attempt_evaluation_assessment': checks[0]['attempt_evaluation_assessment']})
context_path = HERE.parent / 'offline-rag-predicate-comparison06/review07/component-context-preparation07/ACTUAL_COMPONENT_CONTEXTS07.json'
context = read(context_path)
assert pin(context_path)['sha256'] == manifest['context_sha256']
metadata['retrieval_context_pin'] = pin(context_path)
metadata['retrieval_public_summary'] = {'status': context['status'], 'question': context['question'],
    'actual_execution_device': context['actual_execution_device'],
    'corpus': {key: value for key, value in context['corpus'].items() if not isinstance(value, list)},
    'arms': [{key: value for key, value in arm.items() if key not in ('evidence', 'source_map', 'candidates', 'candidate_projections', 'visible_chunks') and not isinstance(value, list)} for arm in context['arms']],
    'selected_IDs_by_arm': {arm['arm']: [e['chunk_id'] for e in arm['evidence']] for arm in context['arms']},
    'cold_warm_sequential_retrieval_not_causal_speed_comparison': True}
print(json.dumps({'selected_source_pack': new('ROOT_SELECTED_SOURCE_PACK08e.json', pack),
                  'metadata_readout': new('ROOT_ACTUAL_METADATA_READOUT08e.json', metadata),
                  'exact_selected_source_data': pack}, ensure_ascii=True))
