"""Attach current corpus execution evidence without claiming unfinished acceptance."""
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
now = datetime.now(timezone.utc).isoformat()
task_path = ROOT / 'docs/execution/tasks.json'
ledger = json.loads(task_path.read_text(encoding='utf-8'))
evidence = {
    'DAT-01': ['evidence/openstax/acquisition-run.json', 'evidence/openstax/pdf-source-inspection.json'],
    'DAT-02': ['evidence/openstax/processing-registry.json'],
    'DAT-03': ['evidence/openstax/concepts-biology-acquisition.json', 'evidence/openstax/pdf-low-text-decisions.json', 'evidence/openstax/concepts-biology-quality.json'],
    'DAT-04': ['evidence/openstax/processing-status.json', 'evidence/corpus/pdf_structure_v4_smoke.json'],
    'DAT-05': ['evidence/openstax/pdf-low-text-decisions.json', 'evidence/openstax/processing-status.json', 'evidence/openstax/ocr/run.json'],
    'DAT-07': ['evidence/openstax/initial-v3/processing-registry.json', 'evidence/openstax/processing-registry.json'],
    'RET-01': ['evidence/corpus/e5_download.json', 'evidence/corpus/e5_verification.json', 'requirements-embeddings.lock'],
}
details = {
    'DAT-01': ('REAL_FLOW_VERIFIED', 'All four official PDFs acquired, independently hash-checked and source/license pages inspected; official URLs, timestamp, exact current revision/hash and 4,638-page scope recorded. Corpus processing/publication remains a separate requirement.'),
    'DAT-03': ('REAL_FLOW_VERIFIED', 'Concepts original SHA256 exactly matches the historical pilot. Physical1 is the designed cover and physical2 is blank, visually reviewed and explicitly excluded in a new real processing run. Original pilot records and first-pass quarantine remain unchanged. Other newly identified visual pages are being processed separately.'),
    'DAT-04': ('REAL_FLOW_VERIFIED', 'All four full official PDFs passed through native parsing, cleaning and PostgreSQL source-unit persistence. New actual-bookmark processing removes TOC-as-section confusion. Current runs remain quarantined pending source-verified image text; parser completion is not corpus publication.'),
    'RET-01': ('REAL_FLOW_VERIFIED', 'Pinned E5 learned weights/tokenizer ran offline on CUDA: actual384 dimensions, normalized finite vectors, correct semantic smoke ranking and input-window rejection verified. Full-book embedding batches/cache/publication are still pending and must be verified separately.'),
}
for task in ledger['tasks']:
    identity = task['task_id']
    if identity in evidence:
        for path in evidence[identity]:
            assert (ROOT / path).exists(), path
            for field in ('evidence', 'evidence_paths'):
                if path not in task.setdefault(field, []):
                    task[field].append(path)
        task['reconciled_at'] = now
    if identity in details:
        status, detail = details[identity]
        task['status'] = task['verification_status'] = status
        task['reconciliation_note'] = detail
        task['evidence_scope'] = detail
        task['remaining_scope'] = 'Finish the remaining full-corpus OCR/source review, actual learned-vector build, validated publication and attributable query runs; independent human/live-answer research stays unverified.' if identity != 'DAT-03' else 'Historical pilot page decision is verified; full current corpus publication is separately unfinished.'
        task['component_statuses'].append({'component': 'current official-data checkpoint', 'status': status, 'detail': detail, 'observed_at': now})
        task['implementation_trace']['limitation'] = task['remaining_scope']
    for component in task.get('component_statuses', []):
        if component['component'] == 'full official four-book corpus':
            component.update(status='IMPLEMENTED_UNVERIFIED', detail='Official acquisition and initial full parsing are now real and recorded. Bookmarked processing is quarantined pending 15 visual/short-math source-page resolutions; full learned-vector publication/retrieval still pending.')
        elif component['component'] == 'learned local embedding/reranker inference':
            component.update(status='IMPLEMENTED_UNVERIFIED', detail='Actual pinned E5 CUDA inference passed, recorded in e5_verification.json. Full-book vectors and the separate learned cross-encoder are not yet verified.')
ledger['corpus_checkpoint'] = {'observed_at': now, 'official_pdf_count': 4, 'physical_pages': 4638,
    'official_downloads_verified': True, 'pinned_e5_inference_verified': True,
    'all_books_native_parsed': True, 'full_book_vectors_verified': False, 'official_release_published': False,
    'pending': 'Complete image OCR/source review, run final processing, construct/validate/publish learned vectors and exercise real retrieval.'}
task_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
checks_path = ROOT / 'docs/execution/acceptance.json'
checks = json.loads(checks_path.read_text(encoding='utf-8'))
for check in checks['checks']:
    if check['check_id'] in ('AC-03', 'AC-04', 'AC-05', 'AC-06', 'AC-26', 'AC-28', 'AC-35'):
        for path in ('evidence/openstax/acquisition-run.json', 'evidence/openstax/processing-status.json', 'evidence/corpus/e5_verification.json'):
            if path not in check['evidence_paths']:
                check['evidence_paths'].append(path)
        check['component_statuses'].append({'component': 'official corpus current stage', 'status': 'IMPLEMENTED_UNVERIFIED',
            'detail': 'Official acquisition, full native parsing and real E5 smoke executed. Formal full-book chunk/vector/release/query acceptance remains pending source-page resolution.', 'observed_at': now})
        check['reconciled_at'] = now
checks_path.write_text(json.dumps(checks, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('Attached current official-data/model evidence; no full-release acceptance claimed.')
