import { useCallback, useEffect, useRef, useState } from 'react';
import { request } from './api';

/** Discard responses from an obsolete route or owner without hiding request failures. */
export function useLearningResource<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [revision, setRevision] = useState(0);
  const generation = useRef(0);
  const reload = useCallback(() => setRevision(value => value + 1), []);
  useEffect(() => {
    const current = ++generation.current;
    const controller = new AbortController();
    setData(null); setError(null); setLoading(Boolean(path));
    if (path) request<T>(path, { signal: controller.signal }).then(value => {
      if (generation.current === current) setData(value);
    }).catch(caught => {
      if (generation.current === current && !controller.signal.aborted) setError(caught);
    }).finally(() => { if (generation.current === current) setLoading(false); });
    return () => { generation.current++; controller.abort(); };
  }, [path, revision]);
  return { data, loading, error, reload };
}

export interface PassageSelection { text: string; start: number; end: number }

/** Offsets use Python/Unicode code points, matching immutable server source units. */
export function passageSelection(element: HTMLElement, selection: Selection | null): PassageSelection | null {
  if (!selection || selection.rangeCount !== 1 || selection.isCollapsed) return null;
  const range = selection.getRangeAt(0);
  if (!element.contains(range.startContainer) || !element.contains(range.endContainer)) return null;
  const before = range.cloneRange(); before.selectNodeContents(element); before.setEnd(range.startContainer, range.startOffset);
  const text = range.toString();
  if (!text.trim()) return null;
  const start = Array.from(before.toString()).length;
  return { text, start, end: start + Array.from(text).length };
}

export function sourceUrl(value?: string | null): string | null {
  if (!value) return null;
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; }
  catch { return null; }
}

export function downloadText(name: string, content: string, type = 'text/markdown;charset=utf-8') {
  const blob = new Blob([content], { type }); const url = URL.createObjectURL(blob);
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
