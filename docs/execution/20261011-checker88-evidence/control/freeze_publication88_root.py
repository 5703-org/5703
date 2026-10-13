"""Freeze only public closed Phase88 evidence for the reviewed local publisher."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

W = Path(__file__).resolve().parent
R = W/'5703-checker88-runtime'
sys.dont_write_bytecode = True
sys.path.insert(0,str(R))
import budget88

def need(ok,code):
    if not ok:
        raise RuntimeError(code)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def add(source,destination):
    need(source.resolve().is_relative_to(W) and source.is_file() and not source.is_symlink(),'PUBLIC_SOURCE_BOUNDARY')
    raw = source.read_bytes()
    rows.append({'workspace_relative_path':str(source.relative_to(W)).replace('\\','/'),
                 'evidence_relative_path':destination,'sha256':sha(raw),'bytes':len(raw)})

need(not (W/'phase88-public-evidence-selection.json').exists()
     and not (W/'phase88-publication-ready.json').exists(),'PRESERVE_PREVIOUS_PUBLICATION_FREEZE')
state = budget88.snapshot(R/'cohort-ledger')
need(state['claimed_physical_posts']==state['settled_posts']==21 and state['known_cost_USD']=='0.2307916'
     and state['unknown_full_hold_USD']=='0' and not state['cohort_stopped'],'EXACT_CLOSED_COHORT_REQUIRED')
rows=[]
for leaf in ('case12-eligibility88.json','low-pair-review88.json','page10b-review88.json'):
    add(W/'5703-checker88-quality'/leaf,'quality/'+leaf)
for leaf in ('phase88-page-qualification-root.json','phase88-page10b-root-adoption.json',
             'phase88-venv-pid-probe.json','phase88-case10b-terminal-review.json'):
    # The independent terminal review is optional when delivered as a message.
    if leaf=='phase88-case10b-terminal-review.json' and not (W/leaf).exists():
        continue
    add(W/leaf,'control/'+leaf)
for leaf in ('page_bindings88_root.py','qualify_page88_root.py','finalize_phase88_root.py',
             'publish_phase88_root.py','freeze_publication88_root.py'):
    add(W/leaf,'control/'+leaf)
for directory in ('5703-unit88-contract-test-fixes',):
    for p in sorted((W/directory).glob('*.json')):
        add(p,'source-changes/'+p.name)
for p in sorted(R.glob('*.json')):
    if p.name=='results88.json':
        continue
    add(p,'runtime/'+p.name)
for case in ('case03','case04','case04r','case05','case07','case08','case09','case10','case10b','case11','case12'):
    for p in sorted((R/case).glob('*.json')):
        add(p,'runtime/'+case+'/'+p.name)
    for p in sorted((R/case/'native-provider70').glob('*.json')):
        add(p,'runtime/'+case+'/native-provider70/'+p.name)
for p in sorted((R/'component07low').glob('*.json')):
    add(p,'runtime/component07low/'+p.name)
for source,destination in (
    (W/'5703-page10b-runtime-candidate/release10b.json','control/runtime-release10b.json'),
    (W/'5703-page10b-outer-candidate/release-outer-server10b.json','control/outer-release10b.json'),
    (W/'5703-unit88-cwd-nul-controls05/controls.json','control/unit-guard-controls05.json'),
    (W/'5703-unit88-affected02/receipt.json','unit/affected-receipt.json'),
    (W/'5703-unit88-harness-release.json','control/unit-harness-release.json')):
    add(source,destination)
need(len({row['evidence_relative_path'] for row in rows})==len(rows),'DUPLICATE_EVIDENCE_TARGET')
fixed = [R/'results88.json', W/'software-verification88.json', W/'phase88-reasoning-support.json',
         W/'5703-checker88-quality/independent-review88.json',
         W/'5703-unit88-free-r4/receipt.json',W/'5703-unit88-free-r4/pytest.xml',
         W/'5703-unit88-free-r4/pytest.log',W/'5703-unit88-free-r4/tripwire.json',
         W/'5703-unit88-cwd-nul-controls05/controls.json']
ledger = sorted((R/'cohort-ledger').glob('*.json'))
payload = fixed+[W/row['workspace_relative_path'] for row in rows]+ledger
total = sum(p.stat().st_size for p in payload)
need(total < 8_000_000,'PUBLIC_EVIDENCE_BOUND')
selection_raw=(json.dumps(rows,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
with (W/'phase88-public-evidence-selection.json').open('xb') as stream:
    stream.write(selection_raw)
frozen = payload+[W/'phase88-public-evidence-selection.json',W/'phase88-final-report.md',
                 W/'phase88-progress-append.md',W/'phase88-handover-append.md',W/'publish_phase88_root.py',
                 W/'finalize_phase88_root.py',W/'freeze_publication88_root.py']
pins={str(p.relative_to(W)).replace('\\','/'):sha(p.read_bytes()) for p in frozen}
ready={'schema':'phase88_root_frozen_publication_inputs_v1','created_utc':datetime.now(timezone.utc).isoformat(),
       'cohort_financial':state,'frozen_workspace_inputs':pins,
       'cohort_ledger_file_pins':{p.name:sha(p.read_bytes()) for p in ledger},
       'selected_payload_files':len(payload),'selected_payload_bytes':total,
       'auth_binders_env_or_sealed_rubric_files_selected':False,
       'only_destination':'E:/5703/learning-assistant/docs/execution/20261011-checker88-evidence',
       'no_API_DB_model_remote_operations':True}
raw=(json.dumps(ready,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
with (W/'phase88-publication-ready.json').open('xb') as stream:
    stream.write(raw)
print(json.dumps({'status':'FROZEN','ready_sha256':sha(raw),'payload_files':len(payload),'payload_bytes':total}))
