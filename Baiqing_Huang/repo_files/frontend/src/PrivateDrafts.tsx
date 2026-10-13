import { useEffect, useRef, useState } from 'react';
import { request } from './api';
import { Button, ErrorNotice, Loading, titleCase } from './components';
import type { components } from './generated/api';

type DraftPage = components['schemas']['DraftReviewPage'];

export function PrivateDrafts({ requestId }: { requestId: string }) {
  const [page, setPage] = useState<DraftPage | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    setPage(null); setError(null); setLoading(false);
    return () => controller.current?.abort();
  }, [requestId]);
  async function load() {
    controller.current?.abort();
    const pending = new AbortController(); controller.current = pending;
    setLoading(true); setError(null); setPage(null);
    try {
      const value = await request<DraftPage>(`/admin/failures/${encodeURIComponent(requestId)}/drafts`, { signal: pending.signal });
      if (!pending.signal.aborted) setPage(value);
    } catch (caught) { if (!pending.signal.aborted) setError(caught); }
    finally { if (!pending.signal.aborted) setLoading(false); }
  }
  return <section aria-label="Private draft review">
    <h3>Private draft review</h3>
    <p className="secondary">Inspect saved draft text and currently available source excerpts. Inspection keeps the publication decision unchanged.</p>
    <Button onClick={load} disabled={loading}>{page ? 'Reload private drafts' : 'Load private drafts'}</Button>
    <ErrorNotice error={error} />
    {loading && <Loading>Loading private drafts…</Loading>}
    {page && <div className="stack">
      {page.items.length === 0 && <p>No generated drafts were saved for this request.</p>}
      {page.items.map(item => <article className="record" key={item.id}>
        <h4>Unpublished draft{item.revision == null ? '' : ` · revision ${item.revision}`}</h4>
        <p className="secondary">{item.recorded_at} · Sources: {titleCase(item.source_status)}</p>
        <p className="preserve-lines">{item.answer_text || 'Draft text was not recorded.'}</p>
        {item.truncated && <p className="secondary">Showing the first 12,000 characters.</p>}
        {item.withheld_source_count > 0 && <p className="secondary">{item.withheld_source_count} source view(s) unavailable under current provenance checks.</p>}
        {(item.sources || []).map(source => <details className="data-details" key={source.evidence_id}>
          <summary>{source.title} · {source.section} · page {source.pages.join(', ')}</summary>
          {source.excerpts.map((text, index) => <blockquote className="preserve-lines" key={index}>{text}</blockquote>)}
          <p className="secondary">Evidence {source.evidence_id} · Passage {source.chunk_id} · SHA-256 {source.text_hash}</p>
        </details>)}
      </article>)}
      {page.truncated && <p className="secondary">Showing the first 50 saved generated drafts.</p>}
    </div>}
  </section>;
}
