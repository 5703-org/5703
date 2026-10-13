"""Root-only checker cap regression against one unchanged saved native teacher answer."""
from pathlib import Path
from decimal import Decimal
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import urlsplit
import ast
import copy
import hashlib
import importlib.util
import json
import sys
import time
import types

sys.dont_write_bytecode = True
W = Path(r'C:\Users\PC\Documents\Codex\2026-10-04\task-2')
MAIN = Path(r'E:\5703\learning-assistant')
D = W / '5703-week10-native-pair-20261009-01/diagnostic-preparation'
PREP = D / 'checker-cap-local-preparation01'
OUT = D / 'checker-cap-local-actual01'
REQ = 'ca4ccd11-0500-4a55-8eb1-c2a68b48d8fa'
JOB = '0e5c02b0-6dd1-4030-a9ea-e6a05538f3a3'
DB = 'cs30_week10_pair_b_20261009_01'
CONFIG = '74c8201e-aca0-400d-bcc5-5785e24c1c11'
WORKSPACE = '5ef0e22c-45f2-4c72-9ff8-acfee1e6b655'
TEACHER_SHA = 'f5fc06d9eabb5483997ce3a1bd0a86a413f3a9825598fa4560a7f334d46e655f'
SCHEMA_SHA = '7988037e08d52662a1b232f049776a42b6d10ad5d896f1a26c8c912b3efd79d4'

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                      separators=(',', ':')).encode()).hexdigest()

def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_node(node, scope):
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'existing-native-function', 'exec'), scope)

def source_node(path, name):
    return next(n for n in ast.parse(path.read_text(encoding='utf-8')).body
                if isinstance(n, ast.FunctionDef) and n.name == name)

def reconstruct():
    from sqlalchemy import create_engine, text
    from generation.types import GenerationRequest, ModelConfig
    from contracts.models import EvidenceSnapshot
    interface = W / '5703-current-native-checker26-20261008-01/serve_current_fixture_native_API_PREPARED08.py'
    assert hashlib.sha256(interface.read_bytes()).hexdigest() == 'd8d3ec29dc11cd4fa3d0b5ea636412d840dc4177300b77a3ee1703ac1b15d2b6'
    parsed = urlsplit(load_module('approved_memory_interface', interface).approved_memory_database())
    assert (parsed.scheme, parsed.hostname, parsed.port, parsed.path) == ('postgresql+psycopg', '127.0.0.1', 15433, '/cs30_fixture_20261006_01')
    engine = create_engine(parsed._replace(path='/' + DB).geturl(), hide_parameters=True,
                           connect_args={'connect_timeout': 5, 'options': '-c default_transaction_read_only=on -c statement_timeout=5000'})
    try:
        with engine.connect() as conn:
            assert conn.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
            assert conn.execute(text('SELECT current_database()')).scalar_one() == DB
            def row(table, cols, where, bindings):
                value = conn.execute(text('SELECT ' + cols + ' FROM ' + table + ' WHERE ' + where), bindings).mappings().one_or_none()
                return types.SimpleNamespace(**dict(value)) if value is not None else None
            req = row('answer_requests', 'id,owner_id,mode,session_id,context_snapshot_id,profile_snapshot_id,release_id,command,trace', 'id=:id', {'id': REQ})
            job = row('jobs', 'id,request_id,state,answer_id', 'id=:id', {'id': JOB})
            assert job.request_id == REQ and job.state == 'failed' and job.answer_id is None
            assert req.mode == 'interactive_chat' and req.command.get('memory_snapshot_id') is None
            assert row('users', 'workspace_id', 'id=:id', {'id': req.owner_id}).workspace_id == WORKSPACE
            assert req.command['model_config']['configuration_id'] == 'model-settings:' + CONFIG
            saved = [p for _, p in conn.execute(text('SELECT sequence,payload FROM attempts WHERE job_id=:job ORDER BY sequence'), {'job': JOB})]
            assert len(saved) == 4 and [p['phase'] for p in saved] == ['start', 'finish', 'start', 'finish']
            assert saved[1]['finish_reason'] == 'stop' and not saved[1]['error']
            teacher = saved[1]['raw_text']
            assert hashlib.sha256(teacher.encode()).hexdigest() == TEACHER_SHA
            context = row('snapshots', 'payload', 'id=:id', {'id': req.context_snapshot_id}).payload
            profile = row('snapshots', 'payload', 'id=:id', {'id': req.profile_snapshot_id}).payload if req.profile_snapshot_id else None
            specs = {'Chunk': ('chunks', 'id,processing_id,document_id,text,text_hash,spans'), 'Document': ('documents', 'id,active,revoked'), 'ProcessingRun': ('processing_runs', 'id,document_version_id,counts'), 'SourceUnit': ('source_units', 'id,processing_id,quality,page,raw_text,cleaned_text'), 'ReleaseChunk': ('release_chunks', 'release_id,chunk_id')}
            classes = {name: type(name, (), {}) for name in specs}
            class ReadonlySources:
                def get(self, model, identifier, **unused):
                    table, cols = specs[model.__name__]
                    if model.__name__ == 'ReleaseChunk':
                        return row(table, cols, 'release_id=:r AND chunk_id=:c', {'r': identifier[0], 'c': identifier[1]})
                    return row(table, cols, 'id=:id', {'id': identifier})
            scope = {'copy': copy, 'hashlib': hashlib, 'AppError': ValueError, **classes}
            run_node(source_node(MAIN / 'backend/app/modules/learning_state/sources.py', 'source_map'), scope)
            native = source_node(MAIN / 'backend/app/modules/answering/service.py', 'execute_answer')
            body = next(n.body for n in native.body if isinstance(n, ast.With))
            loop = next(n for n in body if isinstance(n, ast.For) and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and isinstance(x.func.value, ast.Name) and x.func.value.id == 'evidence' and x.func.attr == 'append' for x in ast.walk(n)))
            constructor = next(n for n in body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'generation_request' for t in n.targets))
            trace = req.trace
            args = {'req': req, 'GenerationRequest': GenerationRequest, 'ModelConfig': ModelConfig, 'EvidenceSnapshot': EvidenceSnapshot, 'candidates': copy.deepcopy(trace['retrieval_candidates']), 'evidence': [], 'condition': req.command.get('condition', 'E1'), 'question': req.command['question'], 'history': context.get('messages', []), 'context': context, 'policy': profile, 'prepared': trace['prepared_query'], 'understanding': trace['understanding'], 'answer_mode': req.command.get('answer_mode', 'textbook'), 'teaching_context': req.command.get('teaching_context'), 'memory_context': None, 'generation_policy': req.command.get('generation_policy'), 'progress_plan': trace.get('progress_plan'), 'context_coverage': trace.get('context_coverage'), 'frozen_coverage_query_policy': req.command.get('coverage_query_policy'), 'reading_context': req.command.get('reading_context')}
            run_node(loop, args)
            args['mapping'] = scope['source_map'](ReadonlySources(), req, args['evidence'])
            run_node(constructor, args)
            conn.rollback()
            return args['generation_request'], saved, teacher
    finally:
        engine.dispose()

class Captured(BaseException):
    pass

def main():
    resume_zero = sys.argv[1:] == ['--resume-zero-post']
    execute = sys.argv[1:] == ['--execute'] or resume_zero
    assert execute or sys.argv[1:] == ['--preflight']
    sys.path[:0] = [str(MAIN), str(MAIN / 'backend'), str(MAIN / '.venv/Lib/site-packages')]
    from generation.service import GenerationService
    from generation.types import ProviderResult, RequestBudget
    from generation import adapters
    from generation.reliability_v5 import ReliableCheckV5
    from generation.parser import strict_json
    request, saved, teacher = reconstruct()
    original_checker = request.checker_config or request.config
    assert original_checker.model == 'anthropic/claude-haiku-5.5'
    assert original_checker.openrouter_route_profile == 'haiku55_google_vertex_low_v1'
    captured = {}
    class CachedTeacher:
        def __init__(self):
            self.calls = 0
            self.config = request.config
        def generate(self, messages, *, response_schema, response_schema_name, **unused):
            assert self.calls == 0 and messages == saved[0]['messages']
            assert digest(response_schema) == '149a9433de28318e6c1d1174c06937762e7db073977ab125d48ae80232f4ae2b'
            self.calls += 1
            return ProviderResult(raw_text=teacher, provider=saved[1]['provider'], model=saved[1]['model'], finish_reason='stop', request_submitted=False, usage={}, latency_ms=0)
    class CaptureChecker:
        def generate(self, messages, *, response_schema, response_schema_name, **unused):
            assert not captured and messages == saved[2]['messages']
            assert digest(response_schema) == SCHEMA_SHA
            captured.update(messages=messages, schema=response_schema, name=response_schema_name)
            raise Captured()
    request = replace(request, checker_config=replace(original_checker, max_tokens=8192, structured_output_mode='json_object'))
    try:
        GenerationService(adapter=CachedTeacher(), checker_adapter=CaptureChecker()).generate(copy.deepcopy(request), RequestBudget(max_calls=2), on_attempt=None)
    except Captured:
        pass
    assert captured, 'PRECHECK_DID_NOT_REACH_ORIGINAL_CHECKER'
    report = {'status': 'ACTUAL_SAVED_TEACHER_REPLAY_PREFLIGHT_PASS', 'request_id': REQ, 'job_id': JOB, 'teacher_bytes': len(teacher.encode()), 'teacher_sha256': TEACHER_SHA, 'teacher_messages_exact': True, 'checker_messages_exact': True, 'checker_original_messages_sha256': digest(captured['messages']), 'full_local_schema_sha256': SCHEMA_SHA, 'selected_evidence_count': len(request.evidence), 'DB_writes': 0, 'provider_POSTs': 0, 'new_teacher_POSTs': 0, 'native_publication_verified': False}
    if not execute:
        save(PREP / 'ACTUAL_REPLAY_PREFLIGHT01.json', report)
        print(json.dumps(report))
        return
    if resume_zero:
        assert sorted(p.name for p in OUT.iterdir()) == ['authorization-scope-public01.json']
        authority = json.loads((OUT / 'authorization-scope-public01.json').read_text(encoding='utf-8'))
        assert authority['maximum_physical_POSTs'] == 2 and authority['maximum_USD'] == '0.06000000' and authority['teacher_sha256'] == TEACHER_SHA
        save(OUT / 'zero-post-correction-public01.json', {'status': 'CONTINUING_SAME_SCOPE_AFTER_ZERO_POST_LOCAL_BLOCK', 'physical_POSTs_before_correction': 0, 'reason': 'Changing the frozen checker timeout to 120 caused ENHANCEMENT_VALIDATION_ERROR before teacher/checker invocation. Retain the original timeout and cap only the outer transport deadline.', 'new_budget_allocation_USD': '0.00000000', 'old_authorization_unchanged': True})
    else:
        OUT.mkdir(exist_ok=False)
        save(OUT / 'authorization-scope-public01.json', {**report, 'status': 'ROOT_EXECUTING_NEW_CHECKER_ONLY_CAP_SCOPE', 'scope_id': '5703-saved-teacher-checker-cap-20261009-01', 'maximum_physical_POSTs': 2, 'maximum_USD': '0.06000000', 'output_caps': [8192, 16384], 'second_only_if_first_known_cost_and_truncated': True, 'new_initial_POSTs': 0, 'new_initial_known_USD': '0.00000000', 'old_UNKNOWN_hold_USD_unchanged': '0.09000000', 'per_POST_hold_USD': '0.03000000', 'price_cap_per_million': {'prompt': 0.1, 'completion': 0.5}, 'at_UTC': datetime.now(timezone.utc).isoformat()})
    # Reuse the exact existing normal credential interface; never read/export a key directly.
    probe = load_module('existing_approved_credential_consumer', D / 'haiku_json_object_full_checker_probe_PREPARED08.py')
    key = probe.approved_credential(WORKSPACE)
    original_open = adapters.open_provider
    posts, known, holds = 0, Decimal(0), Decimal(0)
    deadline = time.monotonic() + 180
    current = {}
    def observed_open(envelope, timeout):
        nonlocal posts, holds
        assert not current.get('submitted') and posts < 2 and known + holds + Decimal('.03') <= Decimal('.06')
        assert envelope.get_method() == 'POST' and envelope.full_url == 'https://openrouter.ai/api/v1/chat/completions'
        body = json.loads(envelope.data)
        assert body['model'] == original_checker.model and body['max_tokens'] == current['cap']
        assert body['response_format'] == {'type': 'json_object'} and body['reasoning'] == {'effort': 'low'}
        provider = body['provider']
        assert provider['only'] == ['google-vertex/global'] and provider['allow_fallbacks'] is False
        provider['max_price'] = {'prompt': 0.1, 'completion': 0.5}
        wire = json.dumps(body, ensure_ascii=False).encode()
        assert len(wire) <= 60000 and len(wire) + 512 < 100000
        upper = Decimal(len(wire) + 512) * Decimal('.0000001') + Decimal(current['cap']) * Decimal('.0000005')
        assert upper < Decimal('.03') and deadline - time.monotonic() > 5
        posts += 1
        holds += Decimal('.03')
        current.update(submitted=True, slot=posts, started=time.monotonic())
        save(OUT / f'checker-{posts:02d}-started01.json', {'slot': posts, 'output_cap': current['cap'], 'wire_bytes': len(wire), 'input_token_upper_bound': len(wire) + 512, 'conservative_cost_upper_USD': str(upper), 'hold_USD': '0.03000000', 'messages_sha256': digest(body['messages']), 'full_local_schema_sha256': SCHEMA_SHA, 'teacher_sha256': TEACHER_SHA, 'reasoning': body['reasoning'], 'provider': provider, 'at_UTC': datetime.now(timezone.utc).isoformat()})
        envelope.data = wire
        response = original_open(envelope, min(timeout, max(1, deadline - time.monotonic())))
        current['http_status'] = response.getcode()
        return response
    adapters.open_provider = observed_open
    trials = []
    try:
        for cap in (8192, 16384):
            current = {'cap': cap}
            cfg = replace(original_checker, structured_output_mode='json_object', max_tokens=cap)
            live = adapters.LLMAdapter(cfg, api_key=key, retain_invalid_output=True)
            result_holder = []
            class Checker:
                config = cfg
                def generate(self, messages, *, response_schema, response_schema_name, **kwargs):
                    assert not result_holder and messages == captured['messages'] and response_schema == captured['schema']
                    result = live.generate(messages, response_schema=response_schema, response_schema_name=response_schema_name, **kwargs)
                    result_holder.append(result)
                    return result
            started = time.monotonic()
            service_exception = None
            try:
                outcome = GenerationService(adapter=CachedTeacher(), checker_adapter=Checker()).generate(copy.deepcopy(replace(request, checker_config=cfg)), RequestBudget(max_calls=2, max_active_seconds=min(180, max(1, deadline - time.monotonic()))), on_attempt=None)
            except Exception as exc:
                service_exception = type(exc).__name__
                outcome = types.SimpleNamespace(response=None, error={'code': 'LOCAL_SERVICE_EXCEPTION_OR_EXTRA_CALL_BLOCKED'})
            assert len(result_holder) == 1
            result = result_holder[0]
            cost = probe.known_cost(result.usage.get('cost'))
            if current.get('submitted') and cost is not None:
                holds -= Decimal('.03')
                known += cost
            raw = result.raw_text
            schema_pass = False
            issues = []
            try:
                parsed = strict_json(raw)
                ReliableCheckV5.model_validate(parsed)
                schema_pass = True
            except Exception as exc:
                issues = [{'type': type(exc).__name__}]
                if hasattr(exc, 'errors'):
                    issues = [{'loc': list(e['loc']), 'type': e['type']} for e in exc.errors()]
                parsed = None
            trial = {'slot': current.get('slot'), 'output_cap': cap, 'http_status': current.get('http_status'), 'finish_reason': result.finish_reason, 'usage': result.usage, 'known_cost_USD': str(cost) if cost is not None else None, 'adapter_latency_ms': result.latency_ms, 'local_generation_elapsed_ms': round((time.monotonic() - started) * 1000, 3), 'raw_chars': len(raw), 'raw_bytes': len(raw.encode()), 'raw_sha256': hashlib.sha256(raw.encode()).hexdigest(), 'complete_full_Pydantic_PASS': schema_pass, 'schema_issues': issues, 'business_gate_error_code': (outcome.error or {}).get('code'), 'business_gate_PASS': outcome.response is not None and outcome.error is None, 'outcome_diagnostic_keys': sorted(outcome.diagnostic) if hasattr(outcome, 'diagnostic') else [], 'field_bytes': {k: len(json.dumps(v, ensure_ascii=False).encode()) for k, v in parsed.items()} if isinstance(parsed, dict) else None, 'new_teacher_POSTs': 0, 'DB_writes': 0, 'native_publication_verified': False}
            trials.append(trial)
            trial['service_exception_type'] = service_exception
            save(OUT / f'checker-{current.get("slot", 0):02d}-finished01.json', trial)
            print(json.dumps(trial), flush=True)
            if trial['business_gate_PASS'] or not (current.get('http_status') == 200 and result.finish_reason == 'length' and cost is not None and posts == 1 and known + holds + Decimal('.03') <= Decimal('.06') and deadline - time.monotonic() > 5):
                break
        save(OUT / 'result-public01.json', {'status': 'ACTUAL_CHECKER_CAP_BUSINESS_PASS' if any(t['business_gate_PASS'] for t in trials) else 'ACTUAL_CHECKER_CAP_FAILED_OR_BLOCKED', 'physical_POSTs': posts, 'known_cost_USD': str(known), 'UNKNOWN_hold_USD': str(holds), 'remaining_scope_USD': str(Decimal('.06') - known - holds), 'smallest_tested_passing_cap': next((t['output_cap'] for t in trials if t['business_gate_PASS']), None), 'trials': trials, 'teacher_sha256': TEACHER_SHA, 'old_UNKNOWN_hold_USD_unchanged': '0.09000000', 'new_teacher_POSTs': 0, 'DB_writes': 0, 'native_publication_verified': False, 'project_complete': False})
    finally:
        adapters.open_provider = original_open
        key = None

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'CHECKER_CAP_EXECUTION_BLOCKED', 'error_type': type(exc).__name__, 'exception_text_exported': False}), flush=True)
        raise SystemExit(1)
