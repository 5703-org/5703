from pathlib import Path
import hashlib, json, sys

if sys.flags.optimize != 0:
    raise RuntimeError('PUBLICATION_GUARDS_REQUIRE_UNOPTIMIZED_PYTHON')

W = Path(__file__).resolve().parent
M = Path('E:/5703/learning-assistant').resolve()
R = W/'5703-checker88-runtime'
report_source = W/'phase88-final-report.md'
report_target = M/'docs/execution/20261011-checker88-common-contract-results.md'
evidence = M/'docs/execution/20261011-checker88-evidence'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def bounded(root, relative):
    candidate = root/relative
    if Path(relative).is_absolute() or not candidate.resolve().is_relative_to(root) or candidate.is_symlink():
        raise RuntimeError('PUBLICATION_PATH_BOUNDARY')
    return candidate

if len(sys.argv) != 3 or sys.argv[1] != '--ready-sha256':
    raise RuntimeError('EXACT_REVIEWED_READY_PIN_REQUIRED')
ready_raw = (W/'phase88-publication-ready.json').read_bytes()
if sha(ready_raw) != sys.argv[2]:
    raise RuntimeError('PUBLICATION_READY_PIN_CHANGED')
ready = json.loads(ready_raw)
if ready['schema'] != 'phase88_root_frozen_publication_inputs_v1':
    raise RuntimeError('PUBLICATION_READY_SCHEMA_REQUIRED')
required = {'publish_phase88_root.py', 'phase88-final-report.md', 'phase88-progress-append.md',
            'phase88-handover-append.md', 'phase88-public-evidence-selection.json',
            '5703-checker88-runtime/results88.json', 'software-verification88.json',
            '5703-checker88-runtime/scope88-case10b.json',
            'phase88-page-qualification-root.json', '5703-checker88-quality/page10b-review88.json'}
if not required <= set(ready['frozen_workspace_inputs']):
    raise RuntimeError('PUBLICATION_REQUIRED_INPUT_MISSING')
for relative, pin in ready['frozen_workspace_inputs'].items():
    candidate = bounded(W, relative)
    if not candidate.is_file() or sha(candidate.read_bytes()) != pin:
        raise RuntimeError('PUBLICATION_INPUT_PIN_CHANGED')
actual_ledger = {p.name:sha(p.read_bytes()) for p in (R/'cohort-ledger').glob('*.json')}
if actual_ledger != ready['cohort_ledger_file_pins']:
    raise RuntimeError('PUBLICATION_COHORT_FILE_SET_CHANGED')
def frozen_bytes(candidate):
    relative = str(candidate.relative_to(W)).replace('\\','/')
    data = candidate.read_bytes()
    if sha(data) != ready['frozen_workspace_inputs'].get(relative):
        raise RuntimeError('PUBLICATION_READ_BYTES_CHANGED')
    return data

report = frozen_bytes(report_source)
assert b'[ROOT TO FILL' not in report and b'Working draft' not in report
result = json.loads(frozen_bytes(R/'results88.json'))
assert result['auth_exported'] is False
assert result['cohort_financial']['unknown_full_hold_USD'] == '0'
software = json.loads(frozen_bytes(W/'software-verification88.json'))
for relative, pin in software['production_and_test_source_pins'].items():
    source = bounded(M, relative)
    assert source.is_file() and not source.is_symlink()
    assert sha(source.read_bytes()) == pin
scope = json.loads(frozen_bytes(R/'scope88-case10b.json'))
for row in scope['source_pins']:
    source = Path(row['path'])
    if not source.resolve().is_relative_to(M) or source.is_symlink() or sha(source.read_bytes()) != row['sha256']:
        raise RuntimeError('PUBLICATION_ALL_CURRENT_MAIN_PINS_REQUIRED')
assert not report_target.exists() and not evidence.exists()
assert report_target.resolve().is_relative_to(M) and evidence.resolve().is_relative_to(M)
for parent in (M/'docs', M/'docs/execution', M/'docs/foundation'):
    assert parent.is_dir() and not parent.is_symlink()
append_targets = [
    (M/'docs/execution/progress.md', 'f0ddbfb600630a6886a9f30b262293fa607c3b15b5e465e004d04113a43c40e7', W/'phase88-progress-append.md'),
    (M/'docs/foundation/handover_migration.md', 'b089bceeb0e1e6c7d6804b1ca27b535749683512d72885d13acba837e06fabe5', W/'phase88-handover-append.md')]
preimages = []
for target, pin, addition in append_targets:
    original = target.read_bytes()
    assert sha(original) == pin and not target.is_symlink()
    extra = frozen_bytes(addition)
    assert extra.strip() and b'[ROOT TO FILL' not in extra
    preimages.append((target, original, extra))
files = [
    (R/'results88.json', 'results88.json'),
    (W/'software-verification88.json', 'software-verification88.json'),
    (W/'phase88-reasoning-support.json', 'reasoning-support88.json'),
    (W/'5703-checker88-quality/independent-review88.json', 'independent-review88.json'),
    (W/'5703-unit88-free-r4/receipt.json', 'unit/receipt.json'),
    (W/'5703-unit88-free-r4/pytest.xml', 'unit/pytest.xml'),
    (W/'5703-unit88-free-r4/pytest.log', 'unit/pytest.log'),
    (W/'5703-unit88-free-r4/tripwire.json', 'unit/tripwire.json'),
    (W/'5703-unit88-cwd-nul-controls05/controls.json', 'unit/guard-controls.json')]
selection = json.loads(frozen_bytes(W/'phase88-public-evidence-selection.json'))
for row in selection:
    p = W/row['workspace_relative_path']
    assert p.resolve().is_relative_to(W) and p.is_file() and not p.is_symlink()
    assert sha(p.read_bytes()) == row['sha256']
    files.append((p, row['evidence_relative_path']))
for p in sorted((R/'cohort-ledger').glob('*.json')):
    files.append((p, 'cohort-ledger/'+p.name))
assert len({relative for _, relative in files}) == len(files)
prepared = []
for source, relative in files:
    assert source.is_file() and not source.is_symlink()
    source_relative = str(source.relative_to(W)).replace('\\','/')
    if source_relative not in ready['frozen_workspace_inputs']:
        raise RuntimeError('PUBLICATION_PAYLOAD_NOT_FROZEN')
    target = bounded(evidence, relative)
    data = source.read_bytes()
    if sha(data) != ready['frozen_workspace_inputs'][source_relative]:
        raise RuntimeError('PUBLICATION_PREPARED_BYTES_CHANGED')
    prepared.append((source, target, data))
assert sum(len(data) for _, _, data in prepared) < 8_000_000
if {p.name:sha(p.read_bytes()) for p in (R/'cohort-ledger').glob('*.json')} != actual_ledger:
    raise RuntimeError('PUBLICATION_COHORT_CHANGED_BEFORE_WRITE')
evidence.mkdir()
manifest = []
for source, target, data in prepared:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as f:
        f.write(data)
    assert target.read_bytes() == data
    manifest.append({'path': str(target.relative_to(evidence)), 'bytes': len(data),
                     'sha256': sha(data), 'original_workspace_path': str(source)})
with report_target.open('xb') as f:
    f.write(report)
assert report_target.read_bytes() == report
appends = []
for target, original, extra in preimages:
    assert target.read_bytes() == original
    combined = original + extra
    with target.open('ab') as stream:
        stream.write(extra)
        stream.flush()
        import os
        os.fsync(stream.fileno())
    actual = target.read_bytes()
    assert actual == combined and actual[:len(original)] == original
    appends.append({'path': str(target), 'prefix_bytes_preserved': len(original),
                    'prefix_sha256': sha(original), 'after_sha256': sha(actual)})
record = {'schema': 'phase88_main_publication_readback_v1', 'status': 'PASS',
          'report': {'path': str(report_target), 'bytes': len(report), 'sha256': sha(report)},
          'evidence': manifest, 'total_evidence_bytes': sum(len(data) for _, _, data in prepared),
          'appended_existing_documents': appends, 'Main_source_or_real_database_writes': 0,
          'remote_push_upload_deploy_or_course_submission': False, 'auth_exported': False}
with (evidence/'readback-manifest88.json').open('x', encoding='utf-8') as f:
    json.dump(record, f, indent=2, ensure_ascii=False)
with (W/'phase88-publication-receipt.json').open('x', encoding='utf-8') as f:
    json.dump(record, f, indent=2, ensure_ascii=False)
print(json.dumps({'status': 'PASS', 'report': str(report_target), 'evidence_files': len(manifest),
                  'total_evidence_bytes': record['total_evidence_bytes'], 'report_sha256': sha(report)}))
