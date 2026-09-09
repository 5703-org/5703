"""Render all original task/check IDs from the canonical evidence ledgers."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]


def cell(value):
    return str(value).replace('|','/').replace('\n',' ')


def evidence_links(item):
    paths=item.get('evidence_paths') or item.get('evidence') or []
    return '; '.join(f'[{cell(Path(path).name)}]({path})' for path in paths if isinstance(path,str)) or 'No current acceptance evidence attached'


def main():
    tasks=json.loads((ROOT/'docs/execution/tasks.json').read_text(encoding='utf-8'))['tasks']
    checks=json.loads((ROOT/'docs/execution/acceptance.json').read_text(encoding='utf-8'))['checks']
    corpus=json.loads((ROOT/'evidence/openstax/corpus-report.json').read_text(encoding='utf-8'))
    vector_count=sum(book['database_vectors']['vectors'] for book in corpus['books'])
    assert len({t['task_id'] for t in tasks})==len(tasks)==108
    assert len({c['check_id'] for c in checks})==len(checks)==60
    text='''# Full-project execution plan

Priority updated by the user on8September2026. Scope remains all108 original tasks,60 original AC/HC checks and12 responsive subchecks. Reporting owners/weeks never restrict execution. [PRD.md](PRD.md) defines product requirements; [SPEC.md](SPEC.md) maps the actual architecture/pipeline. Canonical status and evidence live in [tasks.json](docs/execution/tasks.json), [acceptance.json](docs/execution/acceptance.json) and [ui_acceptance.json](docs/execution/ui_acceptance.json); the tables below are generated from those records.

## Execution order now

1. **First documentation reconciliation:** reread original taskbook/prompt/UI requirements and actual source scope; substantively reconcile PRD/SPEC/foundation documents, original Figure1/page1 architecture connections and every numbered ledger item. Record current evidence without percentages.
2. **Real OpenStax corpus:** acquire the four official full books (Biology2e,Chemistry2e,Anatomy&Physiology2e,Concepts of Biology), preserve provenance/license/hash, process every page, inspect and record quarantine, generate real fixed-revision local E5 embeddings, validate pgvector relationships/counts/hashes, publish a new immutable release and execute attributable retrieval. Only the answer LLM stays mock. Do not wait for its credentials.
3. **Corpus verification/reporting:** report per-book source/version/scope/paths/hash, successful and isolated counts/reasons, chunks/vectors/dimension, model/tokenizer revision, DB/release/storage, actual question hits/PDF locators and unresolved portions. Update the same documents/ledgers from actual results.
4. **Remaining full development:** address remaining backend/query/recovery/static/CI/ops issues, current contract/client checks and all connected browser/API/DB journeys; update English guides and final packaging. Real answering quality, formal research scores and independent human ratings remain separate pending evidence.

The real full corpus is now active: four official PDFs,4,638 physical pages,5,541 retained source units and10,584 real384-dimensional E5 vectors. Model intfloat/e5-small-v2 is pinned at ffb93f3bd4047442299a41ebb6fa998a38507c52. All page/source/chunk/vector checks passed, followed by15 actual pgvector queries and a reversible unavailable-source check. Release `39483e7f-efbe-42e7-855e-469fd924383e` was activated without changing original records, saved answers or evidence. The [per-book report](docs/execution/openstax-corpus-report.md) gives exact sources, revisions, licences, paths, counts, exclusions and original excerpts. Seventy-three cover/blank/furniture units are explicitly excluded;15 original units are retained with source recovery linked (14 real OCR transcripts,one official portrait description). No blocking units remain; visual/equation semantics and independent scientific review remain limited. A full backup was restored into a distinct database, including all7 originals,44 recovery artifacts and complete corpus/identity fingerprints.

## Status semantics

| Status | Meaning |
| --- | --- |
| NOT_IMPLEMENTED | Required implementation/artifact is absent |
| IMPLEMENTED_UNVERIFIED | Code/artifact exists but the required current run has not established acceptance |
| MOCK_TEST_PASSED | Current simulated/authored-fixture tests passed; this does not certify real OpenStax or learned vectors |
| REAL_FLOW_VERIFIED | The specified component actually ran with its required real dependencies/data; record exactly which component and whether answer generation still mocked |
| WAITING_EXTERNAL | A specific unavailable external condition prevents this exact check; record cause/scope and continue independent work |

Current implemented API/worker/DB/UI tests often combine real infrastructure with authored data and mock answers. The ledger retains that scope explicitly. No aggregate completion percentage is used. Official downloads are now complete; they were never an external blocker. Concepts matches the historical pilot SHA256 exactly; its original physical pages 1 and 2 were inspected as cover and blank respectively. The original pilot records remain untouched.

## Original checkpoint dependencies retained

G0 foundation/inventory → G1 environment/contracts/identity → G2 sessions/jobs/source processing → G3 real knowledge/retrieval/context/generation → G4 connected chat → G5 frozen evaluation → G6 retrieval comparisons → G7 independent teaching study → G8 regression/recovery → G9 handover. Existing compatible work remains intact. The new real-corpus priority is inserted immediately after the bounded documentation reconciliation; it does not discard completed code or narrow later checkpoints.

## All108 tasks, dependencies, current status and evidence

Full unchanged task acceptance text and owner/reporting fields remain in the canonical JSON. A technical test cannot close a required research or human measurement.

| Task | Required work | Dependencies | Current status | Evidence |
| --- | --- | --- | --- | --- |
'''
    text=text.replace('10,584', f'{vector_count:,}').replace('39483e7f-efbe-42e7-855e-469fd924383e', corpus['release_id'])
    text=text.replace('on8September2026', 'on 8 September 2026').replace('all108', 'all 108').replace('tasks,60', 'tasks, 60').replace('and12', 'and 12').replace('All108', 'All 108')
    text=text.replace('PDFs,4,638', 'PDFs, 4,638').replace('pages,5,541', 'pages, 5,541').replace('and10,', 'and 10,').replace('real384', 'real 384').replace('by15', 'by 15').replace(';15', '; 15').replace('all7', 'all 7').replace('originals,44', 'originals, 44')
    for task in tasks:
        summary=task['implementation'].split('. ')[0]
        text+=f"| {task['task_id']} | {cell(summary)} | {', '.join(task.get('dependencies',[])) or 'None'} | {cell(task.get('status','NOT_IMPLEMENTED'))} | {evidence_links(task)} |\n"
    text+='\n## Next executable action and resumption\n\nCurrent source/version proof and remaining local delivery checks are recorded in [progress.md](docs/execution/progress.md). The [local audit continuation](docs/execution/local-audit-continuation.md) adds verified adapter switching, profile request outcomes and keyboard/error-display checks. Required [owner/week delivery views](docs/delivery/README.md) are generated from the same ledgers, with each grouping containing all108 tasks exactly once. Actual SciQ acquisition, real E5 storage/retrieval and optional Linux inference have separate evidence; their completion does not establish real answering quality. Configure the user-deferred answering provider before any paid/live baseline, supply independent relevance/teaching judgments for formal studies, and perform outstanding physical-device/human checks. Any still-actionable local verification listed in the canonical rows must continue without a new permission gate. Preserve all historical processing, releases and failed verification attempts. Original60 checks remain in [acceptance_report.md](docs/execution/acceptance_report.md), and12 responsive checks remain in [audit-ui.md](docs/execution/audit-ui.md).\n'
    (ROOT/'PLANS.md').write_text(text,encoding='utf-8')
    text='# All 60 original acceptance checks\n\nGenerated from acceptance.json; no check IDs are added or removed. Status applies only to the documented actual evidence scope.\n\n| Check | Required observation | Status | Current evidence |\n| --- | --- | --- | --- |\n'
    for check in checks:
        paths=check.get('evidence_paths') or []
        links='; '.join(f'[{cell(Path(path).name)}](../../{path})' for path in paths if isinstance(path,str)) or 'No current acceptance evidence attached'
        text+=f"| {check['check_id']} | {cell(check['expected'])} | {cell(check['status'])} | {links} |\n"
    (ROOT/'docs/execution/acceptance_report.md').write_text(text,encoding='utf-8')
    print('Rendered108task rows and60acceptance rows from canonical ledgers.')


if __name__=='__main__':
    main()
