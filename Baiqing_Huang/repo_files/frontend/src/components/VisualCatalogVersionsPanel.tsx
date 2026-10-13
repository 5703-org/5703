import { useState, type FormEvent } from 'react';
import { ApiError } from '../api';
import { Button, DataDetails, ErrorNotice, Loading, Modal, titleCase } from '../components';
import { useLearningResource } from '../learning-ui';
import { OriginalPageImage } from '../OriginalPage';
import {
  VISUAL_CATALOG_PATH, catalogCandidatePath, catalogPath, validManifestHash, validVisualBundleName,
  visualCatalogApi, type VisualCatalogCandidate, type VisualCatalogCandidateSummary, type VisualCatalogPage, type VisualCatalogState,
  type VisualCatalogVersion, type VisualContentChecks, type VisualReviewDecision,
} from '../visual-catalog-api';

const EMPTY_CHECKS: VisualContentChecks = {
  source_page_match: false, geometry_correct: false, native_text_correct: false,
  reading_order_correct: false, content_correct: false, notation_units_correct: false,
};
const NEXT_STATES: Record<VisualCatalogState, Exclude<VisualCatalogState, 'staged'>[]> = {
  staged: ['under_review', 'withdrawn'], under_review: ['active', 'withdrawn'],
  active: ['withdrawn'], withdrawn: [],
};
const STATE_ACTIONS = { under_review: 'Begin review', active: 'Activate reviewed catalog', withdrawn: 'Withdraw catalog' };

export function VisualCatalogVersionsPanel() {
  const [expanded, setExpanded] = useState(false);
  return <section className="record stack" aria-label="Visual catalog versions">
    <Button aria-expanded={expanded} aria-controls="visual-catalog-versions-content" onClick={() => setExpanded(value => !value)}>Visual catalog versions</Button>
    {expanded && <div id="visual-catalog-versions-content"><CatalogVersions /></div>}
  </section>;
}

function CatalogVersions() {
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [notice, setNotice] = useState('');
  const versions = useLearningResource<VisualCatalogPage<VisualCatalogVersion>>(`${VISUAL_CATALOG_PATH}?offset=${offset}&limit=30`);
  const user = useLearningResource<{ id: string }>('/users/me');
  const reload = (message = '') => { versions.reload(); setNotice(message); };
  return <div className="stack">
    <p className="secondary">Unreviewed visual candidates are excluded from retrieval. Catalog activity records the review workflow; answer evidence remains excluded.</p>
    <div className="section-heading"><h2>Catalog versions</h2><div className="form-actions"><Button onClick={() => reload()}>Refresh catalogs</Button><Button onClick={() => setImportOpen(true)}>Import prepared bundle</Button></div></div>
    <ErrorNotice error={versions.error || user.error} action={<Button onClick={() => { reload(); user.reload(); }}>Reload catalog records</Button>} />
    {notice && <p role="status">{notice}</p>}
    {versions.loading && <Loading>Loading visual catalogs…</Loading>}
    {versions.data?.items.length === 0 && <p>No catalog versions have been imported.</p>}
    {versions.data?.items.map(catalog => <article className="record stack" key={catalog.id}>
      <div className="record-header"><div><h3>{catalog.document_title || catalog.book}</h3><p className="secondary">{catalog.book} · Catalog revision {catalog.version}</p></div><span className="record-status">{titleCase(catalog.state)}</span></div>
      <p>{catalog.counts.total} candidates · {catalog.counts.figure_image} figures · {catalog.counts.table_candidate} table records · {catalog.counts.formula_candidate} formulas</p>
      <p className="secondary">{catalog.counts.rectangular_tables} {catalog.extractor_revision === 'pymupdf_visual_regions_v4' ? 'rectangular table bodies' : 'rectangular table records'} · {catalog.counts.unresolved_tables} {catalog.extractor_revision === 'pymupdf_visual_regions_v4' ? 'unresolved table bodies' : 'unresolved table records'}{catalog.counts.inline_table_references ? ` · ${catalog.counts.inline_table_references} table references` : ''}</p>
      <p className="secondary">Review history: {catalog.review_history_counts.accepted} accepted · {catalog.review_history_counts.rejected} rejected · {catalog.review_history_counts.needs_more} needing further review</p>
      <p className="secondary">Answer evidence: excluded</p>
      <Button onClick={() => setSelected(catalog.id)}>Inspect catalog version</Button>
    </article>)}
    {versions.data && <nav className="pagination" aria-label="Catalog version pages"><Button disabled={!offset} onClick={() => setOffset(value => Math.max(0, value - 30))}>Previous catalogs</Button><span>Showing {offset + (versions.data.items.length ? 1 : 0)}–{offset + versions.data.items.length}</span><Button disabled={versions.data.next_offset === null} onClick={() => setOffset(versions.data!.next_offset!)}>Next catalogs</Button></nav>}
    {selected && <CatalogInspector catalogId={selected} currentUserId={user.data?.id || null} onClose={() => setSelected(null)} onSaved={message => reload(message)} />}
    {importOpen && <ImportBundle onClose={() => setImportOpen(false)} onSaved={count => { setImportOpen(false); reload(`Prepared bundle imported with ${count} new candidates.`); }} />}
  </div>;
}

function ImportBundle({ onClose, onSaved }: { onClose: () => void; onSaved: (count: number) => void }) {
  const [bundle, setBundle] = useState(''); const [hash, setHash] = useState('');
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const valid = validVisualBundleName(bundle.trim()) && validManifestHash(hash.trim());
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (busy || !valid) return;
    setBusy(true); setError(null);
    try { const result = await visualCatalogApi.import(bundle.trim(), hash.trim()); onSaved(result.added_candidates); }
    catch (caught) { setError(caught); } finally { setBusy(false); }
  };
  return <Modal title="Import visual catalog bundle" onClose={() => { if (!busy) onClose(); }}><form className="stack" onSubmit={submit}>
    <p>Import a prepared bundle from the server’s configured staging area.</p>
    <ErrorNotice error={error} />
    <label>Bundle name<input required maxLength={80} value={bundle} onChange={event => setBundle(event.target.value)} autoComplete="off" placeholder="prepared-catalog-bundle" /></label>
    <label>Manifest SHA-256<input required minLength={64} maxLength={64} pattern="[0-9a-f]{64}" value={hash} onChange={event => setHash(event.target.value)} autoComplete="off" spellCheck={false} /></label>
    <Button className="primary" type="submit" disabled={busy || !valid}>{busy ? 'Importing bundle…' : 'Import bundle'}</Button>
  </form></Modal>;
}

function CatalogInspector({ catalogId, currentUserId, onClose, onSaved }: { catalogId: string; currentUserId: string | null; onClose: () => void; onSaved: (message: string) => void }) {
  const catalog = useLearningResource<VisualCatalogVersion>(catalogPath(catalogId));
  const [offset, setOffset] = useState(0); const [region, setRegion] = useState<string | null>(null);
  const candidates = useLearningResource<VisualCatalogPage<VisualCatalogCandidateSummary>>(region ? null : `${catalogPath(catalogId)}/candidates?offset=${offset}&limit=30`);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const conflict = error instanceof ApiError && (error.status === 409 || error.code.includes('VERSION_CONFLICT'));
  const transition = async (state: Exclude<VisualCatalogState, 'staged'>) => {
    if (!catalog.data || busy || conflict) return; setBusy(true); setError(null); setNotice('');
    try { await visualCatalogApi.transition(catalog.data, state); catalog.reload(); setNotice('Catalog state updated. Answer evidence remains excluded.'); onSaved('Catalog state updated. Answer evidence remains excluded.'); }
    catch (caught) { setError(caught); } finally { setBusy(false); }
  };
  return <Modal title="Visual catalog version" wide onClose={() => { if (!busy && !reviewBusy) onClose(); }}><div className="stack">
    {notice && <p role="status">{notice}</p>}
    <ErrorNotice error={catalog.error || candidates.error || error} action={<Button onClick={() => { setError(null); catalog.reload(); candidates.reload(); }}>Reload saved catalog</Button>} />
    {catalog.loading && <Loading>Loading catalog identity…</Loading>}
    {catalog.data && <>
      <div className="record-header"><div><h3>{catalog.data.document_title || catalog.data.book}</h3><p className="secondary">Catalog revision {catalog.data.version}</p></div><span className="record-status">{titleCase(catalog.data.state)}</span></div>
      <p className="secondary">Answer evidence: excluded</p>
      <DataDetails title="Immutable catalog identity" data={{ book: catalog.data.book, document_version_id: catalog.data.document_version_id, source_sha256: catalog.data.source_sha256, catalog_sha256: catalog.data.catalog_sha256, manifest_sha256: catalog.data.manifest_sha256, previous_catalog_sha256: catalog.data.previous_catalog_sha256, extractor_revision: catalog.data.extractor_revision, catalog_schema: catalog.data.catalog_schema, configuration_sha256: catalog.data.configuration_sha256 }} />
      {!region && <div className="form-actions">{NEXT_STATES[catalog.data.state].map(state => <Button key={state} disabled={busy || conflict} onClick={() => { void transition(state); }}>{STATE_ACTIONS[state]}</Button>)}</div>}
      {region ? <CandidateInspector key={region} catalog={catalog.data} regionId={region} currentUserId={currentUserId} onBusyChange={setReviewBusy} onBack={() => { setRegion(null); candidates.reload(); }} onSaved={() => { catalog.reload(); setNotice('Source content review saved. Answer evidence remains excluded.'); onSaved('Source content review saved. Answer evidence remains excluded.'); }} /> : <>
        {candidates.loading && <Loading>Loading saved candidates…</Loading>}
        {candidates.data?.items.length === 0 && <p>No candidates are recorded for this version.</p>}
        {candidates.data?.items.map(candidate => <article className="record" key={candidate.region_id}><div className="record-header"><h4>{titleCase(candidate.kind)} · PDF page {candidate.physical_pdf_page}</h4><span>{titleCase(candidate.candidate_status)}</span></div><p className="secondary">Answer evidence: excluded</p><Button onClick={() => setRegion(candidate.region_id)}>Inspect candidate</Button></article>)}
        {candidates.data && <nav className="pagination" aria-label="Catalog candidate pages"><Button disabled={!offset} onClick={() => setOffset(value => Math.max(0, value - 30))}>Previous candidates</Button><span>Showing {offset + (candidates.data.items.length ? 1 : 0)}–{offset + candidates.data.items.length}</span><Button disabled={candidates.data.next_offset === null} onClick={() => setOffset(candidates.data!.next_offset!)}>Next candidates</Button></nav>}
      </>}
    </>}
  </div></Modal>;
}

function contentLabels(kind: string, reference = false): [keyof VisualContentChecks, string][] {
  const content = reference ? 'The source reference and distinct target locator match the original PDF link' : kind === 'table_candidate' ? 'Rows, columns and cell relationships match the original' : kind === 'formula_candidate' ? 'The formula and symbol relationships match the original' : 'Figure labels and caption relationships match the original';
  return [['source_page_match', 'The original PDF page matches'], ['geometry_correct', 'The region geometry matches the original'], ['native_text_correct', 'The native text matches the original'], ['reading_order_correct', 'The reading order is preserved'], ['content_correct', content], ['notation_units_correct', 'Signs, notation and units match the original']];
}

function CandidateInspector({ catalog, regionId, currentUserId, onBusyChange, onBack, onSaved }: { catalog: VisualCatalogVersion; regionId: string; currentUserId: string | null; onBusyChange: (value: boolean) => void; onBack: () => void; onSaved: () => void }) {
  const candidate = useLearningResource<VisualCatalogCandidate>(catalogCandidatePath(catalog.id, regionId));
  const [decision, setDecision] = useState<VisualReviewDecision>('needs_more');
  const [checks, setChecks] = useState<VisualContentChecks>({ ...EMPTY_CHECKS });
  const [evidence, setEvidence] = useState(''); const [showPage, setShowPage] = useState(false);
  const [showTarget, setShowTarget] = useState(false);
  const isReference = candidate.data?.raw_payload.details.record_role === 'inline_table_reference';
  const target = candidate.data?.raw_payload.details.reference_target_locator as { physical_pdf_page: number; source_sha256: string; bbox_points: number[]; target_previous_region_id: string } | null | undefined;
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null); const [saved, setSaved] = useState(false);
  const independent = Boolean(currentUserId && currentUserId !== catalog.importer_id && catalog.source_active);
  const conflict = error instanceof ApiError && (error.status === 409 || error.code.includes('REVIEW_CONFLICT'));
  const valid = evidence.trim().length >= 12 && evidence.trim().length <= 2000 && (decision !== 'accepted' || (!isReference && Object.values(checks).every(Boolean)));
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (!candidate.data || busy || conflict || !independent || !valid) return;
    setBusy(true); onBusyChange(true); setError(null); setSaved(false);
    try { await visualCatalogApi.review(catalog.id, candidate.data, decision, checks, evidence.trim()); candidate.reload(); setSaved(true); onSaved(); }
    catch (caught) { setError(caught); } finally { setBusy(false); onBusyChange(false); }
  };
  return <div className="stack"><Button disabled={busy} onClick={onBack}>Back to catalog candidates</Button>
    <ErrorNotice error={candidate.error || error} action={<Button disabled={busy} onClick={() => { setError(null); candidate.reload(); }}>Reload saved candidate</Button>} />
    {candidate.loading && <Loading>Loading exact candidate content…</Loading>}
    {candidate.data && <>
      <h4>{isReference ? 'Table reference' : titleCase(candidate.data.raw_payload.kind)} · PDF physical page {candidate.data.raw_payload.physical_pdf_page}</h4>
      <p className="secondary">{candidate.data.latest_review ? `Latest review: ${titleCase(candidate.data.latest_review.decision)}` : 'Unreviewed candidate'} · Answer evidence: excluded</p>
      <p className="source-passage">{candidate.data.raw_payload.native_text || 'No native text is recorded for this region.'}</p>
      <DataDetails title="Candidate geometry and extraction" data={{ bbox_points: candidate.data.raw_payload.bbox_points, payload_sha256: candidate.data.payload_sha256, details: candidate.data.raw_payload.details }} />
      {candidate.data.previous_region_id ? <><Button disabled={!catalog.source_active} onClick={() => setShowPage(value => !value)}>{showPage ? 'Hide original source page' : 'View original source page'}</Button>{showPage && catalog.source_active && <OriginalPageImage documentId={catalog.document_id} regionId={candidate.data.previous_region_id} sourceHash={catalog.source_sha256} page={candidate.data.raw_payload.physical_pdf_page} bounds={candidate.data.raw_payload.bbox_points} />}</> : <p className="secondary">No historical source-page binding is recorded for this candidate.</p>}
      {isReference && <p className="secondary">This record is a reference on PDF physical page {candidate.data.raw_payload.physical_pdf_page}. It contains no table body and cannot be accepted as a complete table.{target ? target.physical_pdf_page === candidate.data.raw_payload.physical_pdf_page ? ' Its linked table is a distinct region on the same PDF physical page.' : ` Its linked table is on distinct PDF physical page ${target.physical_pdf_page}.` : ' The target remains unresolved.'}</p>}
      {isReference && target && <><Button disabled={!catalog.source_active} onClick={() => setShowTarget(value => !value)}>{showTarget ? 'Hide linked target source page' : 'View linked target source page'}</Button>{showTarget && catalog.source_active && <OriginalPageImage documentId={catalog.document_id} regionId={target.target_previous_region_id} sourceHash={target.source_sha256} page={target.physical_pdf_page} bounds={target.bbox_points} />}</>}
      {candidate.data.latest_review && <DataDetails title="Latest independent content review" data={candidate.data.latest_review} />}
      {!catalog.source_active ? <p className="secondary">The source is unavailable for content review.</p> : !independent && <p className="secondary">This catalog requires a content review by another administrator.</p>}
      <form className="stack" onSubmit={submit}>
        <label>Content review decision<select value={decision} disabled={!independent || busy} onChange={event => setDecision(event.target.value as VisualReviewDecision)}><option value="needs_more">Needs further review</option><option value="rejected">Reject candidate</option><option value="accepted" disabled={isReference}>Accept reviewed extraction</option></select></label>
        {contentLabels(candidate.data.raw_payload.kind, isReference).map(([key, label]) => <label className="inline-check" key={key}><input type="checkbox" checked={checks[key]} disabled={!independent || busy} onChange={event => setChecks(previous => ({ ...previous, [key]: event.target.checked }))} />{label}</label>)}
        <label>Content review evidence<textarea required minLength={12} maxLength={2000} rows={4} value={evidence} disabled={!independent || busy} onChange={event => setEvidence(event.target.value)} /></label>
        <Button type="submit" className="primary" disabled={busy || conflict || !independent || !valid}>{busy ? 'Saving content review…' : 'Save content review'}</Button>
      </form>
      {saved && <p role="status">Content review saved. Answer evidence remains excluded.</p>}
    </>}
  </div>;
}
