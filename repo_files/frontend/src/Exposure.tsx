import { useEffect, useRef, useState, type ReactNode } from 'react';
import { api } from './api';
import { Button, ErrorNotice } from './components';
import type { ExposureInput } from './learning-types';

/** An observation of visible DOM, never an assertion that a learner read it. */
export function ObservedPresentation({ answerId, exposure, children }: { answerId: string; exposure: Omit<ExposureInput, 'kind'> | null; children: ReactNode }) {
  const element = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<unknown>(null);
  const [retry, setRetry] = useState(0);
  const signature = JSON.stringify(exposure);
  useEffect(() => {
    if (!exposure || !element.current || typeof IntersectionObserver === 'undefined') return;
    let cancelled = false; let visible = false; let submitted = false;
    const current = JSON.parse(signature) as Omit<ExposureInput, 'kind'>;
    const record = async () => {
      if (!visible || document.visibilityState !== 'visible' || submitted || cancelled) return;
      submitted = true; setError(null);
      try {
        const bytes = new TextEncoder().encode(JSON.stringify([answerId, current, 'rendered']));
        const digest = await crypto.subtle.digest('SHA-256', bytes);
        const key = `rendered-${Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')}`;
        if (!cancelled) await api.exposure(answerId, { ...current, kind: 'rendered' }, key);
      } catch (caught) { if (!cancelled) setError(caught); }
    };
    const observer = new IntersectionObserver(entries => { visible = entries.some(entry => entry.isIntersecting); void record(); }, { threshold: 0.01 });
    observer.observe(element.current);
    const changed = () => { void record(); };
    document.addEventListener('visibilitychange', changed);
    return () => { cancelled = true; observer.disconnect(); document.removeEventListener('visibilitychange', changed); };
  }, [answerId, signature, retry]);
  return <div ref={element}>{children}{!!error && <div className="exposure-error"><p className="secondary">This display could not be recorded.</p><ErrorNotice error={error} action={<Button onClick={() => setRetry(value => value + 1)}>Retry display record</Button>} /></div>}</div>;
}
