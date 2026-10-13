"""Public native40 producer draft and offline preflight; native execution is blocked.

This draft derives only the reviewed public native36 code. It never reads fixture
authentication, private binders or checker-override contents, touches a database,
allocates provider slots, or writes Main/B. Root must finish current source and
fixture sealing after an independent full-source quality PASS before activation.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

W = Path(r'C:\Users\PC\Documents\Codex\2026-10-04\task-2')
OWN = W / '5703-native40-minimal-public-candidate'
B = W / '5703-week10-native-pair-20261009-01'
S36 = B / 'diagnostic-preparation/scientific-native-closure-preparation36'
MAIN = Path(r'E:\5703\learning-assistant')
RESULT39 = W / '5703-fixed-checker-pair39-candidate/actual-fixed-pair39/actual-fixed-checker-pair39-result01.json'
FREE39 = W / 'ACTUAL_SOURCE_ANCHOR39_CURRENT_FREE_VERIFICATION.json'
BUDGET36 = W / '5703-wire-budget36-candidate/wire_budget_contract36_CANDIDATE.py'
NEXT_SCOPE_ID = '5703-scientific-native-closure-20261010-40'
CAP = 2
HOLD = Decimal('0.04100000')
RESERVE = Decimal('0.08200000')
ORIGINAL_CASH_CAP = Decimal('0.24000000')
PRIOR_POSTS = 18
PRIOR_KNOWN = Decimal('0.14928810')

PUBLIC_SOURCES = {
    'guard': ('scientific_native_closure_guard_PREPARED09.py', 338976, '2194360c40cdb3431d23c53bfd22ddbab30edbba8dbeeac2a4e062af96e6969f'),
    'runtime': ('launch_week10_scientific_native_closure_PREPARED09.py', 113785, '77d2a5f990bd6e0434471f1bf191f5ab77ea055a31448723d843bf967a8d086f'),
    'controller': ('execute_week10_scientific_native_closure_ROOT_PREPARED09.py', 70242, 'ce8408afb77e666e3a8c0837c960c99f9eb52e8ca68579e9d365b314bf94ed5c'),
    'browser': ('real_browser_week10_scientific_native_closure_PREPARED01.cjs', 82844, '2c1a948acdddc7914d87d7cac0de268a553a025ca85a2ab0df613b0bcbd72c1b'),
}
BUSINESS39 = {
    'generation/checked.py': (155543, '5b62005af2263600d6c9485aedf73613acd825bade85f41fc33ba88b0b39994c'),
    'generation/source_relations_v2.py': (17079, '4e3ef844eff23b77d83e850c32fdfa47c9504b7cec9a8edd7db3328851ba5a55'),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def need(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def read_pinned(path: Path, size: int, digest: str) -> bytes:
    data = path.read_bytes()
    need(len(data) == size and sha(data) == digest, 'PUBLIC_SOURCE_PIN_CHANGED')
    return data


def assignment(source: str, name: str):
    matches = [n for n in ast.parse(source).body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    need(len(matches) == 1, 'EXACT_ONE_ASSIGNMENT_REQUIRED_' + name)
    return matches[0]


def replace_assignment(source: str, name: str, value) -> str:
    node = assignment(source, name)
    lines = source.splitlines(keepends=True)
    lines[node.lineno - 1:node.end_lineno] = [name + ' = ' + repr(value) + '\n']
    return ''.join(lines)


def replace_once(source: str, before: str, after: str, deltas: list[dict]) -> str:
    need(source.count(before) == 1, 'EXACT_CAP_ANCHOR_CHANGED')
    deltas.append({'before': before, 'after': after, 'occurrences': 1})
    return source.replace(before, after)


def derive_public_budget() -> dict:
    """Run only two public pure Decimal functions, never any prepared launcher."""
    data = read_pinned(BUDGET36, 6320, 'eafb18d2421583a37a5372a899b38e97347dcb007f1432bb2d9b0a91337aa055')
    tree = ast.parse(data.decode('utf-8-sig'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in {'_wire_budget_decimal', 'derive_wire_budget'}]
    need(len(functions) == 2, 'PUBLIC_PURE_BUDGET_FUNCTION_SET_CHANGED')
    namespace = {'Decimal': Decimal, 'ROUND_FLOOR': ROUND_FLOOR}
    exec(compile(ast.Module(body=functions, type_ignores=[]), '<public-pure-wire-budget>', 'exec'), namespace)
    bound = namespace['derive_wire_budget'](output_tokens=4096,
                                             per_post_reserve_USD='0.04100000',
                                             maximum_wire_bytes=98304)
    need(Decimal(bound['strict_upper_USD_at_max_wire']) == Decimal('0.03988480'), 'STRICT_BOUND_CHANGED')
    need(Decimal(bound['strict_upper_USD_at_max_wire']) + Decimal('0.00050000') < HOLD, 'HOLD_MARGIN_TOO_SMALL')
    need(CAP * HOLD == RESERVE and PRIOR_KNOWN + RESERVE <= ORIGINAL_CASH_CAP, 'FINITE_CASH_CAP_EXCEEDED')
    need(bound['input_tokens_bound_at_max_wire'] == 98816, 'INPUT_BYTE_BOUND_CHANGED')
    return {
        'POST_cap': CAP, 'per_POST_hold_USD': format(HOLD, '.8f'),
        'batch_reserve_USD': format(RESERVE, '.8f'),
        'strict_POST_upper_USD': '0.03988480', 'safety_margin_USD': '0.00050000',
        'strict_upper_plus_margin_USD': '0.04038480',
        'maximum_wire_UTF8_bytes': 98304, 'input_token_upper': 98816,
        'uniform_bound_output_tokens': 4096, 'teacher_output_cap': 2048,
        'checker_output_cap': 4096, 'prior_actual_group_POSTs': PRIOR_POSTS,
        'prior_actual_group_known_USD': format(PRIOR_KNOWN, '.8f'),
        'conditional_cumulative_maximum_POSTs': PRIOR_POSTS + CAP,
        'conditional_cumulative_maximum_USD': format(PRIOR_KNOWN + RESERVE, '.8f'),
        'provider_slot_or_financial_allocation_created': False,
    }


def replace_budget_derivation(source: str) -> str:
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
             and n.name == 'derive_native_guard_wire_contract']
    need(len(nodes) == 1, 'EXACT_BUDGET_DERIVATION_REQUIRED')
    node = nodes[0]
    lines = source.splitlines(keepends=True)
    old = ''.join(lines[node.lineno - 1:node.end_lineno])
    updated = old.replace('per_post_reserve_USD="0.04500000"', 'per_post_reserve_USD="0.04100000"')
    changes = [
        ('Decimal("0.04985240")', 'Decimal("0.14928810")'),
        ('new_scope = reserve * 4', 'new_scope = reserve * 2'),
        ('"maximum_new_physical_POSTs": 4', '"maximum_new_physical_POSTs": 2'),
        ('"previous_physical_POSTs_used": 8', '"previous_physical_POSTs_used": 18'),
        ('"cumulative_maximum_physical_POSTs": 12', '"cumulative_maximum_physical_POSTs": 20'),
        ('"manual_new_allocation_physical_POSTs": 4', '"manual_new_allocation_physical_POSTs": 2'),
    ]
    for before, after in changes:
        need(updated.count(before) == 1, 'EXACT_BUDGET_FIELD_CHANGED')
        updated = updated.replace(before, after)
    updated = updated.replace('manual four-POST allocation', 'manual two-POST allocation')
    lines[node.lineno - 1:node.end_lineno] = [updated]
    return ''.join(lines)


def public_source_draft(role: str, data: bytes) -> tuple[str, list[dict]]:
    source = data.decode('utf-8-sig')
    changes: list[dict] = []
    if role == 'guard':
        source = replace_budget_derivation(source)
        for before, after in [
            ('MAX_POSTS = 4', 'MAX_POSTS = 2'),
            ('MAX_POSTS_PER_LEG = 4', 'MAX_POSTS_PER_LEG = 2'),
            ("UPPER = Decimal('0.04500000')", "UPPER = Decimal('0.04100000')"),
            ("RESERVE = Decimal('0.18000000')", "RESERVE = Decimal('0.08200000')"),
            ('a["maximum_physical_POSTs"] == MAX_POSTS == 4', 'a["maximum_physical_POSTs"] == MAX_POSTS == 2'),
            ("RESERVE == Decimal('0.18')", "RESERVE == Decimal('0.082')"),
            ('"max_possible_new_batch_reserve_USD": \'0.18000000\'', '"max_possible_new_batch_reserve_USD": \'0.08200000\''),
        ]:
            source = replace_once(source, before, after, changes)
        money = ast.literal_eval(assignment(source, 'MONEY').value)
        money.update(new_separate_authorized_scope_USD='0.08200000', maximum_batch_reserve_USD='0.08200000',
                     upper_per_physical_POST_USD='0.04100000', each_leg_full_bound_USD='0.08200000',
                     previous_physical_POSTs_used=18, previous_spent_USD='0.14928810',
                     cumulative_maximum_physical_POSTs=20, cumulative_worst_case_USD='0.23128810')
        source = replace_assignment(source, 'MONEY', money)
        source = source.replace("'0.04500000'", "'0.04100000'")
        changes.append({'structured_MONEY_changes': {k: money[k] for k in ('new_separate_authorized_scope_USD', 'maximum_batch_reserve_USD', 'upper_per_physical_POST_USD', 'each_leg_full_bound_USD', 'previous_physical_POSTs_used', 'previous_spent_USD', 'cumulative_maximum_physical_POSTs', 'cumulative_worst_case_USD')}})
    elif role == 'runtime':
        for before, after in [
            ('release.get("max_provider_posts") != 4', 'release.get("max_provider_posts") != 2'),
            ('release.get("new_batch_reserve_USD") != "0.18000000"', 'release.get("new_batch_reserve_USD") != "0.08200000"'),
            ('max_provider_calls=4, provider_timeout_seconds=60', 'max_provider_calls=2, provider_timeout_seconds=60'),
            ('PREPARATION / "native_checker_json_object_override_PREPARED01.py"', 'Path(' + repr(str(S36 / 'native_checker_json_object_override_PREPARED01.py')) + ')'),
        ]:
            source = replace_once(source, before, after, changes)
    elif role == 'controller':
        source = replace_once(source, '2 <= budget["provider_post_count"] <= 4', 'budget["provider_post_count"] == 2', changes)
    elif role == 'browser':
        for before, after in [
            ('const MAX_PROVIDER_POSTS = 4, MIN_PROVIDER_SLOTS = 2, MAX_REQUEST_POSTS = 4;', 'const MAX_PROVIDER_POSTS = 2, MIN_PROVIDER_SLOTS = 2, MAX_REQUEST_POSTS = 2;'),
            ('const BATCH_RESERVE_SCALED = 18000000n;', 'const BATCH_RESERVE_SCALED = 8200000n;'),
            ("new_batch_reserve_USD: '0.18000000', maximum_authorized_new_batch_cost_USD: '0.18000000'", "new_batch_reserve_USD: '0.08200000', maximum_authorized_new_batch_cost_USD: '0.08200000'"),
        ]:
            source = replace_once(source, before, after, changes)
        source = source.replace('EIGHTEEN_CENT_FINITE_SCOPE_PROTECTION', 'EIGHT_POINT_TWO_CENT_FINITE_SCOPE_PROTECTION')
    # Public identity changes only. No scope is created by this draft.
    for before, after in [
        ('scientific-native-closure-preparation36', 'scientific-native-closure-preparation40'),
        ('scientific-native-closure36', 'scientific-native-closure40'),
        ('native-controller-source36', 'native-controller-source40'),
        ('CURRENT_NATIVE_EXECUTION_CONFIG36', 'CURRENT_NATIVE_EXECUTION_CONFIG40'),
        ('Q_NEW36', 'Q_NEW40'),
        ('FRESH_NATIVE_QUESTION36_DESCRIPTOR', 'FRESH_NATIVE_QUESTION40_DESCRIPTOR'),
        ('5703-scientific-native-closure-20261010-28', NEXT_SCOPE_ID),
    ]:
        source = source.replace(before, after)
    # Preserve the exact reviewed override path and hash; never open its file.
    if role == 'runtime':
        preview_path = str(S36 / 'native_checker_json_object_override_PREPARED01.py').replace('scientific-native-closure-preparation36', 'scientific-native-closure-preparation40')
        source = source.replace(repr(preview_path), repr(str(S36 / 'native_checker_json_object_override_PREPARED01.py')))
        need(source.count(repr(str(S36 / 'native_checker_json_object_override_PREPARED01.py'))) == 1,
             'EXACT_REUSED_OVERRIDE_PATH_LITERAL_REQUIRED')
    if role != 'browser':
        compile(source, '<native40-public-' + role + '>', 'exec')
    return source, changes


def audit(event: str, args: tuple) -> None:
    if event.startswith(('socket.', 'sqlite3.', 'subprocess.')) or event in {'os.system', 'os.spawn', 'os.exec'}:
        raise RuntimeError('OFFLINE_PREFLIGHT_FORBIDS_NETWORK_DB_OR_PROCESS')
    if event == 'open' and args and isinstance(args[0], (str, bytes, Path)):
        p = Path(args[0]).resolve()
        need(p.name != 'native_checker_json_object_override_PREPARED01.py', 'DENIED_OVERRIDE_CONTENT_READ_FORBIDDEN')
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and bool(flags & 0x243))
        if writing:
            need(p.is_relative_to(OWN), 'ONLY_OWN_W_OUTPUT_WRITES_ALLOWED')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-preflight', action='store_true')
    parser.add_argument('--emit-public-preview', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    need(not (args.prepare or args.execute), 'DRAFT_NATIVE_START_BLOCKED_ACTUAL39_SCHEMA_AND_SCIENCE_FAILED')
    need(args.public_preflight, 'EXPLICIT_PUBLIC_PREFLIGHT_REQUIRED')
    sys.addaudithook(audit)
    result = json.loads(read_pinned(RESULT39, 60931, 'c925836596a70379a8583f6154066a7a06c1a2e0c0b42386468ad7fd9722e613'))
    need(result['status'] == 'PAIRED_OBSERVATIONS_CLOSED' and result['physical_POSTs'] == 2
         and Decimal(result['known_cost_USD']) == Decimal('0.0244545')
         and Decimal(result['cumulative_known_group_cost_USD']) == PRIOR_KNOWN
         and Decimal(result['new_UNKNOWN_holds_USD']) == 0 and result['open_claims'] == 0
         and result['fully_settled'] is True, 'CLOSED_ACTUAL39_FINANCIAL_FACTS_REQUIRED')
    free = json.loads(read_pinned(FREE39, 1613, 'b57e80d1cc89375597af7db55fd3998fb103242db4ebeff691b532d09086117e'))
    need(free['status'] == 'CURRENT_MAIN_ANCHOR39_TARGETED_FREE_VERIFIED'
         and free['meaningful_affected_small_controls_passed'] == 22
         and free['Ruff']['exit_code'] == 0 and free['API_DB_calls'] == 0,
         'EXACT_SMALL_FREE39_PROOF_REQUIRED')
    budget = derive_public_budget()
    outputs = []
    for role, (name, size, digest) in PUBLIC_SOURCES.items():
        data = read_pinned(S36 / name, size, digest)
        transformed, changes = public_source_draft(role, data)
        if args.emit_public_preview:
            destination = OWN / ('UNRELEASED_' + name)
            need(not destination.exists(), 'PUBLIC_PREVIEW_ALREADY_EXISTS')
            destination.write_text(transformed, encoding='utf-8', newline='')
        outputs.append({'role': role, 'source_name': name, 'base_bytes': size, 'base_SHA256': digest,
                        'draft_bytes': len(transformed.encode('utf-8')), 'draft_SHA256': sha(transformed.encode('utf-8')),
                        'exact_public_delta': changes, 'Python_compile_PASS': role != 'browser',
                        'source_or_template_released': False})
    main_pins = []
    for relative, (size, digest) in BUSINESS39.items():
        data = (MAIN / relative).read_bytes()
        main_pins.append({'relative_path': relative, 'frozen39_bytes': size, 'frozen39_SHA256': digest,
                          'observed_bytes': len(data), 'observed_SHA256': sha(data),
                          'matches_frozen39': len(data) == size and sha(data) == digest})
    report = {
        'status': 'PUBLIC_CAP_PREFLIGHT_PASS_NATIVE_START_BLOCKED_BY_ACTUAL39_SCHEMA_AND_SCIENCE',
        'scope': 'W-only reviewable producer draft; no runtime, binder or financial slot created',
        'budget_math': budget, 'derived_public_sources': outputs, 'current39_business_pin_observation': main_pins,
        'current_small_free_proof_pin': {'path': str(FREE39), 'bytes': 1613, 'sha256': 'b57e80d1cc89375597af7db55fd3998fb103242db4ebeff691b532d09086117e'},
        'software_repair_policy': {'max_provider_calls': 2, 'Main_branch_line': 2898,
            'required_remaining_calls_for_repair_and_recheck': 2, 'stop_reason': 'insufficient_calls_for_repair_and_recheck',
            'repair_or_complete_quality_gates_disabled': False, 'successful_TFull_claimed': False},
        'override': {'existing_pinned_module_reused': True, 'contents_read': False, 'existing_SHA256_documented': 'c2e7287830825e95fdddc7a6656eae5af71ea864c10a3abbb853aa74b66e9d7d'},
        'pending_before_executable_source_sealing': [
            'Latest actual checker output must pass strict current schema and independent full-source assessment with 10 complete claims and 19 complete units; actual39 fails.',
            'Refresh final Main pins and latest small affected-code receipt after any subsequent generic prompt repair.',
            'After intervening component calls, recompute actual group cost plus 0.082 <= 0.24; do not reuse this predecessor subtotal.',
            'Root must refresh source-index/curated-manifest two executable delta rows and current helper hashes, nonce, authority, release-template, binder delta, configuration and exact controller PINS.',
            'Root alone uses the already-authorized ordinary fixture consumer and existing native36 preflight. No new provider qualification or full245 suite is required.',
            'Use a unique future native scope if component40 takes the next identifier. Do not alter native36 sources, STOPs, captures, data or the true/protected databases.'
        ],
        'future_scope_and_funds': {'this_native40_draft_only': True, 'actual_future_native_ID_minimum': 41,
            'component40_must_close_first': True, 'funds_after_component40_unverified_here': True,
            'future_known_group_cost_plus_0_082_must_not_exceed_0_24': True,
            'no_native_provider_slots_allocated_or_reserved': True},
        'free_next_serial_cost_plan': {
            'baseline36_ms': {'generation': 5626, 'joint_check': 10755,
                'semantic_repair': 9071, 'joint_recheck': 7740, 'TFull': 41144.90000000596},
            'baseline36_initial_checker_output': {'output_tokens': 3776, 'JSON_UTF8_bytes': 11770},
            'first_dependency': 'Fix strict output-schema compliance and full source selection before relying on repair avoidance.',
            'next_measured_target_if_no_repair_still_above_20_seconds': 'Mandatory initial checker interval and output serialization; its baseline36 10.755s exceeds teacher 5.626s.',
            'offline_work': [
                'Measure retained exact checker input/context-candidate tables, schema hints and response bytes without further model calls.',
                'Identify repeated identifiers or duplicated guidance for a generic lossless representation; prove canonical decoded payload equality and all condition/negation/no-evidence controls before adopting any compression.',
                'Retain complete original sources, strict schema, citations, all full predicates and final publication gates. No source truncation, skipped checker or unsupported quality claim.',
                'Do not prioritize the baseline36 retrieval CUDA rerank 213ms while the measured required checker stage is over 10 seconds.'
            ],
            'limits': 'No paid test or new latency result in this task; token counts do not alone establish causal latency or p95.'},
        'limitations': ['This is a public producer draft, not a released runnable native scope.', 'Python compile and numeric cap checks do not establish browser execution, model quality or TFull.'],
        'actions': {'API_POSTs': 0, 'database_calls': 0, 'credential_or_private_binder_reads': 0,
                    'override_content_reads': 0, 'Main_or_B_writes': 0, 'W_only_metadata_or_optional_public_preview': True},
    }
    output = OWN / 'NATIVE40_PUBLIC_CAP_PREFLIGHT_DRAFT.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'path': str(output), 'bytes': output.stat().st_size,
                      'sha256': sha(output.read_bytes()), 'native_start_allowed': False,
                      'API_POSTs': 0, 'DB_calls': 0, 'Main_or_B_writes': 0}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
