"""One projected full-checker diagnostic within new two-POST authority. Root executes only."""
from pathlib import Path
from decimal import Decimal, InvalidOperation
import argparse
import ast
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import secrets
import sys
import time
import types
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.parse import urlsplit, quote

sys.dont_write_bytecode = True
W = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
ROOT = W / '5703-week10-native-pair-20261009-01'
C = ROOT / 'continuous-preparation'
ANALYSIS = C / 'haiku-schema-analysis'
MAIN = Path(r'E:\5703\learning-assistant')
INTERFACE = W / '5703-current-native-checker26-20261008-01/serve_current_fixture_native_API_PREPARED08.py'
INTERFACE_SHA = 'd8d3ec29dc11cd4fa3d0b5ea636412d840dc4177300b77a3ee1703ac1b15d2b6'
KEY_REFERENCE = W / '5703-latency-backend-fixture-20261006-01/rw/config-keys/model-config.key'
CREDENTIAL_CONSUMER_PUBLIC_PIN = {'path': 'E:\\5703\\learning-assistant\\backend\\app\\modules\\model_settings\\service.py', 'bytes': 19093, 'sha256': 'e6e0a9d41846ff36a37bc1eef72892f9ddbc3f2c4648f36f2e9a714f07d5e39d'}
BASELINE_ID = '74c8201e-aca0-400d-bcc5-5785e24c1c11'
TARGET_DB = 'cs30_week10_pair_b_20261009_01'
WORKSPACE_ID = '5ef0e22c-45f2-4c72-9ff8-acfee1e6b655'
BASELINE_REVISION = 1
BASELINE_CONFIG_HASH = '703c94a357ddd4b826d8b5fe25d503198d3d56e1e9130f6a37ed9e9c3396aa4a'
BASELINE_PUBLIC_PIN = {'path': str(C / 'ROOT_CONTINUOUS_BINDER_B_ACTUAL05.json'), 'bytes': 92397,
    'sha256': 'fe88a271eb6203dc4d04fc0ef3263428a4b269d56057ee0eeee9f48ecf4ae471'}
HTTP_TIMEOUT_SECONDS = 180
ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'
MODEL = 'anthropic/claude-haiku-5.5'
SCHEMA_PIN = {'path': str(ANALYSIS / 'CHECKER_ACTUAL05_EXACT_SCHEMA01.json'), 'bytes': 6047,
              'sha256': '08195238e12de5a2e49a575625af7ecd8e4f1bed776ac57853c63a0c7bb80524'}
CONTROLS_PIN = {'path': str(ANALYSIS / 'CHECKER_ACTUAL05_EXACT_WIRE_CONTROLS01.json'), 'bytes': 6409,
                'sha256': 'bb9549c9baa74e085ea4b049ecf859a03e8945334f2bd9101670da8a519a73f7'}
MESSAGES_PIN = {'path': str(ANALYSIS / 'FABRICATED_DISTANCE_CHECKER_MESSAGES01.json'), 'bytes': 17237,
                'sha256': 'db61aee38b9fbecf314f5c4903f8b683804a2775ada41f0ffcbfbeedc2947718'}
OLD_UNKNOWN_PIN = {'path': str(ROOT / 'claims-continuous05/slot-02-finished01.json'), 'bytes': 595,
                   'sha256': '3eed26a59ec22ccf0139b5afd03c873a62f2f56ed203620080d1dd99859f1f85'}
OLD_STOP_PIN = {'path': str(ROOT / 'claims-continuous05/STOP-before-any-next-submission01.json'), 'bytes': 534,
                'sha256': '8a6e1592d803764293148367cb06fb2061c17c2846e6ae0c62dfccc9328d194a'}
MAX_POSTS = 2
UPPER = Decimal('0.03')
NEW_RESERVE = Decimal('0.06')
OLD_HOLD = Decimal('0.06')
PRIOR_FULL_UNKNOWN_PIN = {'path': str(ROOT / 'diagnostic-preparation/haiku-schema-diagnostic02/probe-02-finished01.json'), 'bytes': 1136,
    'sha256': '55627417be1aa349bb060cfd5e2534404e73f7aa63a2dfb5dbb191c215072588'}
PRIOR_RESULT_PIN = {'path': str(ROOT / 'diagnostic-preparation/haiku-schema-diagnostic02/diagnostic-result-public01.json'), 'bytes': 2510,
    'sha256': '1142746d5f3136c4153b5857153cec3179303b22c1ccfe67c181f7b3feac8811'}
ADOPTION_RECEIPT_PIN = {'path': str(W / '5703-haiku-wire-schema-preparation-20261009-01/ACTUAL_HAIKU_WIRE_SCHEMA_MAIN_ADOPTION01.json'), 'bytes': 2558,
    'sha256': '9d15b848fabfbb7d741409baee6d5b4f9270443f80bf8b29fdf5ce5188260b27'}
ADOPTED_SOURCE_PINS = (
    {'path': str(MAIN / 'generation/adapters.py'), 'bytes': 29552, 'sha256': '99075cb07f4faf861119c5fa5113da6951408c02323c14452d090661fd0c3ddb'},
    {'path': str(MAIN / 'generation/openrouter_routes.py'), 'bytes': 11703, 'sha256': 'eb2471e712bc92e5c04495b5353017dbcbc7aa8cdec5451b0ead9f05050588ee'},
    {'path': str(MAIN / 'generation/probes.py'), 'bytes': 25431, 'sha256': 'b9cccc3ae40886da1c327c9721d5d1e1511d200ec72e0e8fbd100c037c12923e'},
)
PROJECTED_SCHEMA_SHA = '70355e166c78f69ccd65927c425ff3ba93daf18e7e0bd1d9490c7ea6c1746c9b'

def preserved_inputs():
    old = fixed(OLD_UNKNOWN_PIN)
    prior = fixed(PRIOR_FULL_UNKNOWN_PIN)
    result = fixed(PRIOR_RESULT_PIN)
    fixed(OLD_STOP_PIN)
    adoption = fixed(ADOPTION_RECEIPT_PIN)
    if (old['known_API_cost_USD'] is not None or old['UNKNOWN_full_hold_USD'] != '0.03000000'
            or prior['reported_cost_USD'] is not None or prior['UNKNOWN_full_hold_USD'] != '0.03000000'
            or prior['http_status'] != 400 or prior['case'] != 'exact_native_checker'
            or result['physical_POST_count'] != 2 or result['new_UNKNOWN_full_holds_USD'] != '0.03'
            or adoption['status'] != 'ACTUAL_EXACT_SIX_FILE_HAIKU_WIRE_REPAIR_ADOPTED'
            or len(adoption['committed']) != 6):
        raise ValueError('PRIOR_HOLDS_OR_ACTUAL_SOURCE_ADOPTION_CHANGED')
    for pin in ADOPTED_SOURCE_PINS:
        data = Path(pin['path']).read_bytes()
        if len(data) != pin['bytes'] or hashlib.sha256(data).hexdigest() != pin['sha256']:
            raise ValueError('ADOPTED_PUBLIC_SOURCE_CHANGED')

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()

def fixed(pin):
    raw = Path(pin['path']).read_bytes()
    if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('PUBLIC_PIN_CHANGED')
    return json.loads(raw)

def create(path, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def sanitized_message(value, secret):
    if not isinstance(value, str):
        return None
    value = value[:16384]
    if secret:
        for spelling in {secret, quote(secret, safe='')}:
            value = value.replace(spelling, '[REDACTED]')
    value = re.sub(r'(?i)\bBearer(?:\s+|%20)[A-Za-z0-9._~+/=%-]+', 'Bearer [REDACTED]', value)
    value = re.sub(r'\bsk-(?:or-[A-Za-z0-9]+-)?[A-Za-z0-9_-]{8,}', '[REDACTED]', value)
    value = re.sub(r'(?i)([?&](?:api[_-]?key|key|access_token|token|auth|signature)=)[^&#\s]+',
                   r'\1[REDACTED]', value)
    value = re.sub(r'(?i)([a-z][a-z0-9+.-]*://)[^/?#\s@]*@', r'\1[REDACTED]@', value)
    return re.sub(r'\s+', ' ', ''.join(ch for ch in value if ch.isprintable() or ch.isspace())).strip()[:600]

def schema_pointers(schema, prefix=''):
    result = {prefix}
    if isinstance(schema, dict):
        for key, value in schema.items():
            child = prefix + '/' + str(key).replace('~', '~0').replace('/', '~1')
            result.update(schema_pointers(value, child))
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            result.update(schema_pointers(value, prefix + '/' + str(index)))
    return result

def safe_error(body, secret, schema):
    result = {'body_retained_or_exported': False, 'body_within_bound': len(body) <= 65536,
              'vendor_messages': [], 'schema_pointers': [], 'message_features': []}
    if len(body) > 65536:
        return result
    try:
        decoded = json.loads(body)
    except (ValueError, UnicodeError):
        return result
    error = decoded.get('error') if isinstance(decoded, dict) else None
    if not isinstance(error, dict):
        return result
    candidates = [('error.message', error.get('message'))]
    metadata = error.get('metadata')
    nested = metadata.get('raw') if isinstance(metadata, dict) else None
    if isinstance(nested, str) and len(nested) <= 65536:
        try:
            nested = json.loads(nested)
        except (ValueError, UnicodeError):
            nested = None
    if isinstance(nested, dict) and isinstance(nested.get('error'), dict):
        candidates.append(('error.metadata.raw.error.message', nested['error'].get('message')))
    allowed = schema_pointers(schema)
    for source, text in candidates:
        message = sanitized_message(text, secret)
        if message is None:
            continue
        result['vendor_messages'].append({'source': source, 'sanitized_message': message})
        for pointer in re.findall(r'/[A-Za-z0-9_$~./-]{1,300}', message):
            pointer = pointer.rstrip('.')
            for prefix in ('/response_format/json_schema/schema', ''):
                candidate = pointer[len(prefix):] if prefix and pointer.startswith(prefix) else pointer
                if candidate in allowed:
                    result['schema_pointers'].append(candidate)
        for keyword in ('schema', '$ref', 'anyOf', 'oneOf', 'allOf', 'additionalProperties',
                        'minimum', 'maximum', 'minItems', 'maxItems', 'minLength', 'maxLength',
                        'pattern', 'format', 'reasoning', 'max_tokens'):
            if keyword.lower() in message.lower():
                result['message_features'].append('vendor_mentions_' + keyword)
    result['schema_pointers'] = sorted(set(result['schema_pointers']))[:12]
    result['message_features'] = sorted(set(result['message_features']))[:20]
    return result

def known_cost(value):
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None

class FiniteBudget:
    def __init__(self):
        self.posts, self.known, self.holds = 0, Decimal(0), Decimal(0)

    def admit(self):
        if self.posts >= MAX_POSTS or self.known + self.holds + UPPER > NEW_RESERVE:
            raise ValueError('DIAGNOSTIC_CAP_EXHAUSTED')
        self.posts += 1
        self.holds += UPPER
        return self.posts

    def settle(self, cost):
        if cost is not None:
            self.holds -= UPPER
            self.known += cost
        return cost is not None and cost > UPPER

def build_payload(controls, schema, messages):
    payload = json.loads(json.dumps(controls))
    payload['response_format']['json_schema']['schema'] = schema
    payload['messages'] = messages
    return payload

def approved_credential(workspace):
    # The existing approved PG consumer supplies only a URI. No URI or key is logged.
    binding = fixed(BASELINE_PUBLIC_PIN)
    if (workspace != WORKSPACE_ID or binding['workspace_id'] != WORKSPACE_ID
            or binding['configuration_id'] != BASELINE_ID or binding['config_revision'] != BASELINE_REVISION
            or binding['config_hash'] != BASELINE_CONFIG_HASH
            or binding['database_target'] != {'database_name': TARGET_DB, 'host': '127.0.0.1', 'port': 15433}):
        raise ValueError('EXACT_PUBLIC_BASELINE_BINDING_REQUIRED')
    spec = importlib.util.spec_from_file_location('haiku_diagnostic_approved_pg_consumer', INTERFACE)
    if hashlib.sha256(INTERFACE.read_bytes()).hexdigest() != INTERFACE_SHA:
        raise ValueError('APPROVED_CONSUMER_CHANGED')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    uri = module.approved_memory_database()
    parsed = urlsplit(uri)
    if (parsed.scheme != 'postgresql+psycopg' or parsed.hostname != '127.0.0.1' or parsed.port != 15433
            or parsed.path != '/cs30_fixture_20261006_01' or parsed.query or parsed.fragment):
        raise ValueError('APPROVED_PG_TARGET_CHANGED')
    uri = parsed._replace(path='/' + TARGET_DB).geturl()
    if KEY_REFERENCE.is_symlink() or not KEY_REFERENCE.is_file():
        raise ValueError('EXISTING_DEPLOYMENT_KEY_REQUIRED')
    from app.core import config as app_config
    settings = app_config.Settings(_env_file=None, env='test', database_url=uri,
        jwt_secret=secrets.token_urlsafe(48), model_config_encryption_key=None,
        model_config_key_file=str(KEY_REFERENCE), llm_api_key=None, model_mode='live')
    app_config.get_settings = lambda: settings
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool
    from app.modules.model_settings.models import ModelConfiguration, ModelCredential
    from app.modules.model_settings.secrets import decrypt
    from app.core.exceptions import AppError
    # Load only the exact approved public credential consumer; avoid service's unrelated providers import.
    consumer_bytes = Path(CREDENTIAL_CONSUMER_PUBLIC_PIN['path']).read_bytes()
    if len(consumer_bytes) != CREDENTIAL_CONSUMER_PUBLIC_PIN['bytes'] or hashlib.sha256(consumer_bytes).hexdigest() != CREDENTIAL_CONSUMER_PUBLIC_PIN['sha256']:
        raise ValueError('APPROVED_PUBLIC_CREDENTIAL_CONSUMER_CHANGED')
    source = consumer_bytes.decode('utf-8')
    tree = ast.parse(source)
    consumer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'resolve_secret')
    prefix = next(n for n in tree.body if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == 'PREFIX' for t in n.targets))
    namespace = {'ModelConfiguration': ModelConfiguration, 'ModelCredential': ModelCredential,
                 'decrypt': decrypt, 'AppError': AppError, 'PREFIX': ast.literal_eval(prefix.value)}
    exec(compile(ast.Module(body=[consumer], type_ignores=[]), 'approved-existing-resolve-secret', 'exec'), namespace)
    resolve_secret = namespace['resolve_secret']
    engine = create_engine(uri, poolclass=NullPool, connect_args={'options':
                          '-c default_transaction_read_only=on -c statement_timeout=5000'})
    try:
        with Session(engine) as db:
            if (db.execute(text('SHOW transaction_read_only')).scalar_one() != 'on'
                    or db.execute(text('SHOW default_transaction_read_only')).scalar_one() != 'on'):
                raise ValueError('READ_ONLY_CREDENTIAL_TRANSACTION_REQUIRED')
            if db.execute(text('SELECT current_database()')).scalar_one() != TARGET_DB:
                raise ValueError('OWNED_SYNTHETIC_DATABASE_REQUIRED')
            row = db.get(ModelConfiguration, BASELINE_ID)
            if (row is None or row.workspace_id != workspace or row.revision != BASELINE_REVISION
                    or row.config_hash != BASELINE_CONFIG_HASH):
                raise ValueError('EXACT_OWNED_BASELINE_REQUIRED')
            key = resolve_secret(db, settings, 'model-settings:' + BASELINE_ID)
            if not isinstance(key, str) or not key:
                raise ValueError('EXISTING_MEMORY_CREDENTIAL_UNAVAILABLE')
    finally:
        engine.dispose()
    # The credential transaction, session and Engine are closed before any POST.
    return key

def execute(args):
    workspace = str(uuid.UUID(args.workspace_id))
    schema = fixed(SCHEMA_PIN)
    controls = fixed(CONTROLS_PIN)
    # Fixture documents are exact schema/control objects, not wrappers or learner inputs.
    if digest(schema) != '7988037e08d52662a1b232f049776a42b6d10ad5d896f1a26c8c912b3efd79d4':
        raise ValueError('EXACT_ACTUAL_CHECKER_SCHEMA_REQUIRED')
    if digest(controls) != '4e5b6ed97b6d71ed4bca1dffd22c07e82dc404c92de457cd340aaa61114eafe9':
        raise ValueError('EXACT_ACTUAL_CHECKER_CONTROLS_REQUIRED')
    preserved_inputs()
    messages = fixed(MESSAGES_PIN)
    if (not isinstance(messages, list) or not messages
            or [m.get('role') for m in messages] != ['system', 'user']):
        raise ValueError('EXACT_PUBLIC_SYNTHETIC_CHECKER_INPUT_REQUIRED')
    work = Path(args.output).absolute()
    if work != ROOT / 'diagnostic-preparation/haiku-schema-diagnostic03':
        raise ValueError('EXACT_FRESH_DIAGNOSTIC_OUTPUT_REQUIRED')
    work.mkdir(exist_ok=False)
    create(work / 'authorization-scope-public01.json', {'status': 'ROOT_EXECUTING_ONE_PROJECTED_FULL_CHECKER_WITHIN_NEW_TWO_POST_AUTHORITY',
        'maximum_new_POSTs': 2, 'execution_attempt_limit': 1, 'new_full_reserve_USD': '0.06000000', 'old_UNKNOWN_hold_USD': '0.06000000',
        'combined_old_hold_plus_new_full_reserve_USD': '0.12000000', 'old_UNKNOWN_pin': OLD_UNKNOWN_PIN,
        'prior_full_UNKNOWN_pin': PRIOR_FULL_UNKNOWN_PIN, 'prior_result_pin': PRIOR_RESULT_PIN,
        'old_STOP_pin': OLD_STOP_PIN, 'schema_pin': SCHEMA_PIN, 'controls_pin': CONTROLS_PIN,
        'synthetic_fixture_pin': MESSAGES_PIN, 'adopted_source_pins': ADOPTED_SOURCE_PINS,
        'adoption_receipt_pin': ADOPTION_RECEIPT_PIN, 'projected_schema_sha256': PROJECTED_SCHEMA_SHA,
        'Q3_or_Q4_replayed': False, 'at_UTC': now()})
    site = MAIN / '.venv/Lib/site-packages'
    if not site.is_dir():
        raise ValueError('EXISTING_DEPENDENCIES_REQUIRED_NO_INSTALL')
    sys.path[:0] = [str(MAIN), str(MAIN / 'backend'), str(site), str(W)]
    # Public schema namespace bypasses package convenience exports; it does not load denied providers.
    if 'generation' not in sys.modules:
        package = types.ModuleType('generation')
        package.__path__ = [str(MAIN / 'generation')]
        sys.modules['generation'] = package
    from generation.openrouter_routes import prepare_schema_wire, BASE_URL
    config = types.SimpleNamespace(openrouter_route_profile='haiku55_google_vertex_low_v1',
        provider='openai_compatible', model=MODEL, base_url=BASE_URL, capabilities=None,
        auth_header=None, api_version=None, temperature=None, thinking_enabled=None, reasoning_effort=None)
    projected_payload, projection_metadata = prepare_schema_wire(config, build_payload(controls, schema, messages), schema)
    projected_schema = projected_payload['response_format']['json_schema']['schema']
    if (digest(projected_schema) != PROJECTED_SCHEMA_SHA
            or projection_metadata['original_response_schema_sha256'] != digest(schema)
            or projection_metadata['provider_schema_before_projection_sha256'] != digest(schema)
            or projection_metadata['removed_bound_count'] != 42):
        raise ValueError('REVIEWED_PROJECTED_FULL_SCHEMA_REQUIRED')
    key = approved_credential(workspace)
    from generation.parser import strict_json
    from generation.reliability_v5 import ReliableCheckV5
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            return None
    opener = build_opener(ProxyHandler({}), NoRedirect())
    budget = FiniteBudget()
    current = {}
    def observed_open(shape):
        payload, wire_metadata = prepare_schema_wire(config, build_payload(controls, schema, messages), schema)
        if payload['response_format']['json_schema']['schema'] != shape or wire_metadata != projection_metadata:
            raise ValueError('PROJECTED_SCHEMA_HELPER_RESULT_CHANGED')
        wire = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        observed_controls = {k: v for k, v in payload.items() if k != 'messages'}
        expected = json.loads(json.dumps(controls))
        expected['response_format']['json_schema']['schema'] = shape
        if (len(wire) > 60000 or len(wire) + 512 >= 100000 or observed_controls != expected
                or payload['messages'] != messages or current.get('started')):
            raise ValueError('ACTUAL_DIAGNOSTIC_WIRE_CONTROLS_CHANGED')
        preserved_inputs()
        slot = budget.admit()
        current.update(started=True, slot=slot, start_UTC=now(), start_monotonic=time.monotonic())
        create(work / f'probe-{slot:02d}-started01.json', {'slot': slot, 'case': current['case'],
            'start_UTC': current['start_UTC'], 'wire_sha256': hashlib.sha256(wire).hexdigest(),
            'wire_bytes': len(wire), 'schema_sha256': digest(shape), 'schema_transport': wire_metadata,
            'controls_sha256': digest(observed_controls), 'messages_sha256': digest(messages),
            'output_cap': 4096, 'input_bound': len(wire) + 512, 'reserved_USD': '0.03000000',
            'no_raw_payload_or_credentials_exported': True})
        request = Request(ENDPOINT, data=wire, method='POST', headers={
            'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                current['http_status'] = response.getcode()
                current['request_id_header'] = response.headers.get('x-request-id') or response.headers.get('request-id')
                body = response.read(1048577)
                if len(body) > 1048576:
                    raise ValueError('PROVIDER_RESPONSE_BOUND_EXCEEDED')
        except HTTPError as error:
            current['http_status'] = error.code
            current['request_id_header'] = error.headers.get('x-request-id') or error.headers.get('request-id') if error.headers else None
            try:
                body = error.read(65537)
            finally:
                error.close()
            current['safe_vendor_error'] = safe_error(body, key, shape)
        try:
            decoded = json.loads(body)
        except (ValueError, UnicodeError):
            decoded = None
        return decoded if isinstance(decoded, dict) else {}
    outcomes = []
    try:
        for label, shape, validator in [('projected_full_native_checker', projected_schema, ReliableCheckV5)]:
            current.clear()
            current.update(case=label, schema=shape, started=False)
            decoded = observed_open(shape)
            if not current['started']:
                raise ValueError('DIAGNOSTIC_NOT_SUBMITTED')
            raw_usage = decoded.get('usage') if isinstance(decoded.get('usage'), dict) else {}
            cost = known_cost(raw_usage.get('cost'))
            valid, error_types = False, []
            choice = decoded.get('choices', [{}])[0] if isinstance(decoded.get('choices'), list) and decoded['choices'] else {}
            choice = choice if isinstance(choice, dict) else {}
            finish_reason = choice.get('finish_reason')
            message = choice.get('message') if isinstance(choice.get('message'), dict) else {}
            raw_text = message.get('content')
            error_code = None if current.get('http_status') == 200 and not decoded.get('error') else 'PROVIDER_HTTP_OR_EMBEDDED_ERROR'
            if decoded.get('error') and current.get('safe_vendor_error') is None:
                current['safe_vendor_error'] = safe_error(json.dumps(decoded).encode(), key, shape)
            if error_code is None and finish_reason == 'stop' and isinstance(raw_text, str) and not message.get('refusal'):
                try:
                    validator.model_validate(strict_json(raw_text))
                    valid = True
                except (ValueError, TypeError) as error:
                    error_types = [type(error).__name__]
            exceeded = budget.settle(cost)
            usage = {k: v for k, v in raw_usage.items() if k in {'prompt_tokens', 'completion_tokens', 'total_tokens'} and type(v) is int and v >= 0}
            request_id = decoded.get('id') or current.get('request_id_header')
            if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_.:/\[\]-]{1,160}', request_id) or sanitized_message(request_id, key) != request_id:
                request_id = None
            receipt = {'slot': current['slot'], 'case': label, 'finish_UTC': now(),
                'http_status': current.get('http_status'), 'latency_ms': int((time.monotonic() - current['start_monotonic']) * 1000),
                'request_submitted': True, 'finish_reason': finish_reason if finish_reason in {'stop', 'length', 'tool_calls', 'content_filter'} else None,
                'provider_request_id': request_id, 'provider_request_id_is_generation_id': bool(request_id and re.fullmatch(r'gen-[A-Za-z0-9_-]{1,150}', request_id)),
                'usage': usage, 'reported_cost_USD': None if cost is None else str(cost),
                'UNKNOWN_full_hold_USD': '0.03000000' if cost is None else '0.00000000',
                'valid_local_schema_result': valid, 'local_validation_error_types': error_types,
                'safe_vendor_error': current.get('safe_vendor_error'),
                'transport_error_category': error_code,
                'raw_body_messages_headers_or_credentials_exported': False}
            create(work / f"probe-{current['slot']:02d}-finished01.json", receipt)
            outcomes.append(receipt)
            if exceeded:
                raise ValueError('KNOWN_COST_EXCEEDS_RESERVED_BOUND')
            # This execution intentionally consumes only its first full-checker attempt.
            if not valid:
                create(work / 'STOP-no-retry-public01.json', {
                    'status': 'STOP_FIRST_PROJECTED_FULL_CHECKER_INVALID_OR_NON200',
                    'physical_POST_count': budget.posts, 'new_UNKNOWN_full_holds_USD': str(budget.holds),
                    'old_UNKNOWN_hold_preserved_USD': '0.06000000', 'unused_authorized_slots': MAX_POSTS - budget.posts})
            break
        create(work / 'diagnostic-result-public01.json', {'status': 'PROJECTED_FULL_CHECKER_LOCAL_STRICT_VALIDATION_PASS' if outcomes and outcomes[0]['valid_local_schema_result'] else 'PROJECTED_FULL_CHECKER_FAILED_STOP_NO_RETRY',
            'physical_POST_count': budget.posts, 'known_reported_cost_USD': str(budget.known),
            'new_UNKNOWN_full_holds_USD': str(budget.holds), 'old_UNKNOWN_hold_preserved_USD': '0.06000000',
            'maximum_new_reserve_USD': '0.06000000', 'maximum_authorized_new_POSTs': 2, 'execution_attempt_limit': 1,
            'unused_authorized_slots': MAX_POSTS - budget.posts, 'automatic_second_attempt': False,
            'remaining_scope_requires_changed_candidate_and_existing_single_scope_accounting': True,
            'original_local_validator': 'ReliableCheckV5', 'schema_transport': projection_metadata,
            'adopted_source_pins': ADOPTED_SOURCE_PINS, 'native_semantic_publication_verified': False,
            'cases': outcomes, 'old_STOP_modified': False, 'Q3_replayed': False, 'Q4_replayed': False,
            'DB_rebuilt_or_written': False, 'manual_retry_redirect_or_fallback': False})
    except BaseException as error:
        if current.get('started'):
            target = work / f"probe-{current['slot']:02d}-finished01.json"
            if not target.exists():
                create(target, {'slot': current['slot'], 'case': current['case'], 'finish_UTC': now(),
                    'status': 'LOCAL_OR_TRANSPORT_UNCERTAIN_FULL_HOLD', 'http_status': current.get('http_status'),
                    'error_class': type(error).__name__, 'reported_cost_USD': None, 'UNKNOWN_full_hold_USD': '0.03000000',
                    'safe_vendor_error': current.get('safe_vendor_error'), 'raw_body_or_credentials_exported': False})
        create(work / 'STOP-no-retry-public01.json', {'status': 'STOP_NO_RETRY', 'error_class': type(error).__name__,
            'physical_POST_count': budget.posts, 'known_reported_cost_USD': str(budget.known),
            'new_full_holds_USD': str(budget.holds), 'old_UNKNOWN_hold_preserved_USD': '0.06000000'})
        raise
    finally:
        key = None
        preserved_inputs()
    return bool(outcomes and outcomes[0]['valid_local_schema_result'])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-authorized-projected-checker', action='store_true')
    parser.add_argument('--workspace-id', required=True)
    parser.add_argument('--output', default=str(ROOT / 'diagnostic-preparation/haiku-schema-diagnostic03'))
    args = parser.parse_args()
    if not args.execute_authorized_projected_checker:
        parser.error('Root explicit execution flag required; preparation never submits a request')
    try:
        passed = execute(args)
    except BaseException as error:
        print(json.dumps({'status': 'BLOCKED_OR_STOPPED', 'error_class': type(error).__name__,
                          'raw_error_or_credentials_exported': False}))
        return 1
    print(json.dumps({'status': 'PROJECTED_CHECKER_DIAGNOSTIC_FINISHED', 'strict_local_schema_pass': passed, 'public_result': str(Path(args.output) / 'diagnostic-result-public01.json')}))
    return 0 if passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
