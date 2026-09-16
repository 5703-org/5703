"""Publication checks only; no shared-app imports, model calls or fake contracts."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys

ROOT = Path(__file__).resolve().parent


def verify():
    manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    source_checks = []
    for item in manifest['files']:
        path = ROOT / item['path']
        raw = path.read_bytes()
        # Git may normalise line endings on Windows. Compare LF source content.
        normalized = raw.replace(b'\r\n', b'\n')
        digest = hashlib.sha256(normalized).hexdigest()
        if digest != item['sha256_lf']:
            raise ValueError('Source hash mismatch: ' + item['path'])
        compile(normalized.decode('utf-8'), item['path'], 'exec')
        source_checks.append({'path': item['path'], 'sha256_lf': digest,
                              'manifest_match': True, 'syntax': 'passed'})

    compiler_path = ROOT / 'personalisation/compiler.py'
    tree = ast.parse(compiler_path.read_text(encoding='utf-8'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'turn_override']
    if len(functions) != 1:
        raise ValueError('Exactly one source turn_override() is required')
    namespace = {'re': re}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(compiler_path), 'exec'), namespace)
    override = namespace['turn_override']
    rubric = runpy.run_path(str(ROOT / 'personalisation/rubric.py'))
    rows = []

    def record(name, sample, expected, actual):
        rows.append({'name': name, 'input': sample, 'expected': expected,
                     'actual': actual, 'passed': actual == expected})

    for question, expected in [
        ('Explain that more simply.', {'level': 'beginner', 'style': 'concise', 'reason': 'explicit_simplification'}),
        ('Make that shorter.', {'style': 'concise', 'reason': 'explicit_concision'}),
        ('Explain in more detail.', {'style': 'detailed', 'reason': 'explicit_detail'}),
        ('What is photosynthesis?', None),
    ]:
        record('request_mapping', question, expected, override(question))

    for name, fill, correctness, expected in [
        ('missing_ratings', None, None, {'complete': False, 'gates_passed': None}),
        ('synthetic_acceptable_scores', 2, 2, {'complete': True, 'gates_passed': True}),
        ('synthetic_failed_correctness', 2, 0, {'complete': True, 'gates_passed': False}),
    ]:
        sheet = rubric['rating_template']('synthetic_item', 'synthetic_rater')
        sheet['ratings'] = {key: fill for key in sheet['ratings']}
        sheet['ratings']['correctness'] = correctness
        record(name, sheet['ratings'], expected, rubric['validate_rating'](sheet))

    invalid = rubric['rating_template']('synthetic_item', 'synthetic_rater')
    invalid['ratings']['clarity'] = 4
    try:
        rubric['validate_rating'](invalid)
        rejected = 'not_rejected'
    except ValueError:
        rejected = 'ValueError'
    record('out_of_range_rating', invalid['ratings'], 'ValueError', rejected)

    return {
        'executed_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'runtime': sys.version.split()[0],
        'scope': 'Source hashes/syntax and eight isolated original-function checks with synthetic inputs.',
        'source_checks': source_checks,
        'cases': rows,
        'passed': sum(row['passed'] for row in rows), 'total': len(rows),
        'not_run': ['full profile compiler', 'TokenCounter/model configuration integration',
                    'TeachingStudyService and C0/C1/C2 matrix', 'full pytest suite',
                    'conversation/database persistence', 'RAG/model generation', 'human evaluation'],
        'interpretation': 'Publication-time software checks only; not new full-module tests, '
                          'not a reproduction of the reported live study, and not proof of personalisation quality.',
    }


if __name__ == '__main__':
    result = verify()
    output = ROOT / 'verification/local_checks.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Source hashes/syntax: ' + str(len(result['source_checks'])) + '/5 passed')
    print('Isolated rule checks: ' + str(result['passed']) + '/' + str(result['total']) + ' passed')
    print('Full application, updated token-budget integration and live study: NOT RUN')
    print('Saved: verification/local_checks.json')
    raise SystemExit(0 if result['passed'] == result['total'] == 8 else 1)
