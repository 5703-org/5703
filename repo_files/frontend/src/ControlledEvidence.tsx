import { useEffect, useRef, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { api } from './api';
import { Button, DataDetails, ErrorNotice, Loading, Modal } from './components';
import { ObservedPresentation } from './Exposure';
import { SourceSegments } from './SourceSegments';
import { responseSources } from './sources';
import type { Answer } from './types';
import type { CitationView } from './learning-types';

function permittedUrl(value?: string | null): string | null {
  try { const url = new URL(value || ''); return url.protocol === 'https:' && !url.username && !url.password ? url.href : null; }
  catch { return null; }
}

export function ControlledEvidenceViewer({ answer, initialId, claimId, onClose }: { answer: Answer; initialId?: string; claimId?: string; onClose: () => void }) {
  const presentation = answer.presentation!;
  const { ids } = responseSources(answer);
  const claimViews = claimId ? presentation.citation_views.filter(view => view.claim_ids?.includes(claimId)) : [];
  const sourceIds = claimViews.length ? ids.filter(id => claimViews.some(view => view.evidence_id === id)) : ids;
  const [selected, setSelected] = useState(initialId && sourceIds.includes(initialId) ? initialId : sourceIds[0]);
  const [view, setView] = useState<CitationView | null>(null);
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [surface, setSurface] = useState<'citation' | 'full_source'>('citation');
  const [parentId, setParentId] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const generation = useRef(0);
  const actionKey = useRef<{ signature: string; key: string } | null>(null);
  const keys = useRef(new Map<string, string>());
  useEffect(() => {
    const current = ++generation.current; setLoading(true); setView(null); setError(null); setSurface('citation'); setParentId(null); setBusy(false);
    if (!selected) { setLoading(false); return; }
    const signature = `${presentation.id}:${selected}:${claimId || ''}`;
    if (!keys.current.has(signature)) keys.current.set(signature, crypto.randomUUID());
    api.exposure(answer.id, { kind: 'citation_opened', presentation_id: presentation.id, evidence_id: selected, claim_id: claimId || null, surface: 'citation' }, keys.current.get(signature)!).then(receipt => {
      if (current !== generation.current) return;
      if (!receipt.citation_view) throw new Error('The approved source preview is unavailable.');
      setView(receipt.citation_view); setParentId(receipt.id);
    }).catch(caught => { if (current === generation.current) setError(caught); }).finally(() => { if (current === generation.current) setLoading(false); });
    return () => { generation.current++; };
  }, [answer.id, presentation.id, selected, claimId, retry]);
  const expand = async () => {
    if (!selected || busy) return;
    setBusy(true); setError(null); const current = generation.current;
    const signature = `${presentation.id}:${selected}:${claimId || ''}:full_source`;
    if (actionKey.current?.signature !== signature) actionKey.current = { signature, key: crypto.randomUUID() };
    try {
      const receipt = await api.exposure(answer.id, { kind: 'full_source_requested', presentation_id: presentation.id, evidence_id: selected, claim_id: claimId || null, surface: 'full_source' }, actionKey.current.key);
      if (current !== generation.current) return;
      if (!receipt.citation_view) throw new Error('The complete source is unavailable.');
      setView(receipt.citation_view); setSurface('full_source'); setParentId(receipt.id); actionKey.current = null;
    } catch (caught) { if (current === generation.current) setError(caught); }
    finally { if (current === generation.current) setBusy(false); }
  };
  const originalUrl = presentation.teaching_mode === 'hint' && surface !== 'full_source' ? null : permittedUrl(view?.source_url);
  const isOpenStax = !!originalUrl && (new URL(originalUrl).hostname === 'openstax.org' || new URL(originalUrl).hostname.endsWith('.openstax.org'));
  const highlighted = view?.segments.some(segment => segment.highlight === true);
  const fragmentIds = new Set(view?.segments.flatMap(segment => segment.fragment_ids || []) || []);
  const fragments = Array.isArray(answer.attribution?.fragments) ? answer.attribution.fragments as Record<string, unknown>[] : [];
  const selectedFragments = fragments.filter(fragment => typeof fragment.fragment_id === 'string' && fragmentIds.has(fragment.fragment_id)).map(fragment => ({ fragment_id: fragment.fragment_id, source_unit_id: fragment.source_unit_id, processing_id: fragment.processing_id, document_version_id: fragment.document_version_id, start: fragment.start, end: fragment.end, text_hash: fragment.text_hash, block_kind: fragment.block_kind, mapping_quality: fragment.mapping_quality }));
  const support = claimId ? answer.attribution?.claims?.find(claim => claim.claim_id === claimId)?.support : undefined;
  return <Modal title="Sources" kind="evidence-modal" onClose={onClose}>
    <p className="secondary">{claimId ? 'Source passages linked to this claim.' : 'Sources cited in this response.'}</p>
    {sourceIds.length > 1 && <nav className="source-tabs" aria-label="Select source">{sourceIds.map((id, index) => <Button key={id} className={selected === id ? 'active' : ''} onClick={() => setSelected(id)}>Source {index + 1}</Button>)}</nav>}
    {loading ? <Loading>Loading the approved source passage…</Loading> : view ? <ObservedPresentation key={`${selected}:${surface}:${parentId}`} answerId={answer.id} exposure={{ presentation_id: presentation.id, evidence_id: selected, claim_id: claimId || null, surface, parent_exposure_id: parentId }}>
      <span className="eyebrow">{surface === 'full_source' ? 'Complete source requested' : presentation.teaching_mode === 'hint' ? 'Source preview for this hint' : 'Source passage'}</span>
      <h3 className="source-title">{view.title}</h3>
      {view.source_title && view.source_title !== view.title && <p>{view.source_title}</p>}
      <p className="source-locator">{[view.section, view.pages?.length ? `PDF physical pages ${view.pages.join(', ')}` : null].filter(Boolean).join(' · ')}</p>
      {highlighted && <p className="secondary">{claimId ? 'Highlighted text is linked to the selected claim.' : 'Highlighted text is linked to claims in this response.'}</p>}
      <SourceSegments segments={view.segments} />
      {surface !== 'full_source' && view.available_actions?.includes('full_source_requested') && <div className="stack source-expansion"><p className="secondary">The complete source may reveal the answer to this problem.</p><Button disabled={busy} onClick={expand}>{busy ? 'Opening complete source…' : 'Show complete source'}</Button></div>}
      {originalUrl && <div className="source-attribution">{isOpenStax && <p>OpenStax / Rice University · Access for free at openstax.org</p>}<a className="source-original-link" href={originalUrl} target="_blank" rel="noopener noreferrer">View original source<ExternalLink size={15} aria-hidden="true" /></a></div>}
      <DataDetails title="Source record" data={{ presentation_id: presentation.id, policy_version: presentation.policy_version, evidence_id: selected, claim_id: claimId || null, fragment_ids: [...new Set(view.segments.flatMap(segment => segment.fragment_ids || []))], license: view.license || null }} />
      {selectedFragments.length > 0 && <DataDetails title="Exact source positions" data={selectedFragments} />}
      {support && <><p className="secondary">Support assessment: model check. Independent review is separate.</p><DataDetails title="Model support check" data={{ status: support.status, checker_configuration_id: support.checker_configuration_id, checker_model: support.checker_model, strategy: support.strategy, checked_at: support.checked_at }} /></>}
    </ObservedPresentation> : !error && <p>No source preview is available.</p>}
    <ErrorNotice error={error} action={!view ? <Button onClick={() => setRetry(value => value + 1)}>Retry source preview</Button> : undefined} />
  </Modal>;
}
