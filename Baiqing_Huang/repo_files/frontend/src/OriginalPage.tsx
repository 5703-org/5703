import { useEffect, useState } from 'react';
import { getToken } from './api';
import { Button, ErrorNotice, Loading, Modal } from './components';

export function OriginalPageImage({ documentId, page, versionId, sourceHash, regionId, bounds }: { documentId: string; page: number; versionId?: string; sourceHash?: string; regionId?: string; bounds?: number[] }) {
  const [url, setUrl] = useState<string | null>(null); const [error, setError] = useState<unknown>(null); const [revision, setRevision] = useState(0);
  const [zoomed, setZoomed] = useState(false); const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);
  useEffect(() => {
    const controller = new AbortController(); let objectUrl: string | null = null;
    setUrl(null); setError(null); setDimensions(null);
    const load = async () => {
      try {
        if (!regionId && (!versionId || !sourceHash)) throw new Error('The immutable original source identity is unavailable. Reload the textbook.');
        const endpoint = regionId ? `/api/v1/admin/source-quality/visual-regions/${encodeURIComponent(regionId)}/original-page` : `/api/v1/learning/library/${encodeURIComponent(documentId)}/original-page/${page}?document_version_id=${encodeURIComponent(versionId!)}&source_sha256=${encodeURIComponent(sourceHash!)}`;
        const response = await fetch(endpoint, { signal: controller.signal, headers: { Authorization: `Bearer ${getToken()}` } });
        if (!response.ok) { if (response.status === 401) window.dispatchEvent(new Event('cs30:session-expired')); throw new Error(`The original source page is unavailable (HTTP ${response.status}).`); }
        if (!response.headers.get('content-type')?.startsWith('image/png')) throw new Error('The server did not return the pinned source image.');
        if (sourceHash && response.headers.get('x-source-sha256') !== sourceHash) throw new Error('The returned page does not match the selected immutable source.');
        const width = Number(response.headers.get('x-pdf-page-width')); const height = Number(response.headers.get('x-pdf-page-height'));
        const blob = await response.blob(); if (controller.signal.aborted) return; objectUrl = URL.createObjectURL(blob); setUrl(objectUrl);
        if (width > 0 && height > 0) setDimensions({ width, height });
      } catch (caught) { if (!controller.signal.aborted) setError(caught); }
    };
    void load(); return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [documentId, page, versionId, sourceHash, regionId, revision]);
  const rectangle = bounds?.length === 4 && dimensions && bounds.every(Number.isFinite) && bounds[0] >= 0 && bounds[1] >= 0 && bounds[2] > bounds[0] && bounds[3] > bounds[1] && bounds[2] <= dimensions.width && bounds[3] <= dimensions.height ? { left: `${bounds[0] / dimensions.width * 100}%`, top: `${bounds[1] / dimensions.height * 100}%`, width: `${(bounds[2] - bounds[0]) / dimensions.width * 100}%`, height: `${(bounds[3] - bounds[1]) / dimensions.height * 100}%` } : null;
  return <div className="stack"><ErrorNotice error={error} action={<Button onClick={() => setRevision(value => value + 1)}>Reload original page</Button>} />{!url && !error && <Loading>Loading the original PDF page…</Loading>}{url && <><Button aria-pressed={zoomed} onClick={() => setZoomed(value => !value)}>{zoomed ? 'Fit source page' : 'Zoom source page'}</Button><div className={`original-page-image ${zoomed ? 'is-zoomed' : ''}`} tabIndex={0} aria-label="Original source page, scroll to inspect"><div className="original-page-canvas"><img src={url} alt={`Original textbook PDF, physical page ${page}`} onError={() => { setUrl(null); setError(new Error('The original page image could not be displayed.')); }} />{rectangle && <span aria-hidden="true" className="source-region-outline" style={rectangle} />}</div></div></>}<p className="secondary">PDF physical page {page}. The reading pane provides extracted text; this image preserves the page’s original layout.{bounds ? rectangle ? ' The outline marks the saved candidate geometry.' : ' Candidate geometry cannot be outlined without verified page dimensions.' : ''}</p></div>;
}

export function OriginalPageModal({ documentId, versionId, sourceHash, page, title, onClose }: { documentId: string; versionId?: string; sourceHash?: string; page: number; title: string; onClose: () => void }) {
  return <Modal title={`Original page · ${title}`} wide onClose={onClose}><OriginalPageImage documentId={documentId} versionId={versionId} sourceHash={sourceHash} page={page} /></Modal>;
}
