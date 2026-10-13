import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { AlertCircle, LoaderCircle, X } from 'lucide-react';
import { ApiError, errorText } from './api';

export function Button({ children, className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={`button ${className}`} {...props}>{children}</button>;
}
export function IconButton({ label, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return <Button aria-label={label} title={label} {...props} className={`icon-button ${props.className || ''}`}>{children}</Button>;
}
export function Loading({ children = 'Loading…' }: { children?: ReactNode }) { return <div className="loading" role="status"><LoaderCircle size={18} className="spin" /><span>{children}</span></div>; }
export function ErrorNotice({ error, action }: { error: unknown; action?: ReactNode }) {
  if (!error) return null;
  return <div className="notice error" role="alert"><AlertCircle size={18} /><div><p>{errorText(error)}</p>{error instanceof ApiError && <details><summary>Error details</summary><p>{error.code}{error.traceId ? ` · Reference ${error.traceId}` : ''}</p></details>}{action}</div></div>;
}
export function Modal({ title, children, onClose, kind = '', wide = false }: { title: string; children: ReactNode; onClose: () => void; kind?: string; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  const close = useRef(onClose); close.current = onClose;
  useEffect(() => {
    const dialog = ref.current!;
    const trigger = document.activeElement as HTMLElement | null;
    dialog.showModal();
    const cancel = (event: Event) => { event.preventDefault(); close.current(); };
    const containTab = (event: KeyboardEvent) => {
      if (event.key !== 'Tab' || event.altKey || event.ctrlKey || event.metaKey) return;
      const controls = [...dialog.querySelectorAll<HTMLElement>('a[href],button,input,textarea,select,summary,[tabindex]')].filter(element => {
        if (element.tabIndex < 0 || element.matches(':disabled') || element.closest('[hidden],[inert]') || !element.getClientRects().length || getComputedStyle(element).visibility === 'hidden') return false;
        for (let ancestor = element.parentElement; ancestor && ancestor !== dialog; ancestor = ancestor.parentElement) {
          if (ancestor instanceof HTMLDetailsElement && !ancestor.open && !ancestor.querySelector(':scope > summary')?.contains(element)) return false;
        }
        return true;
      });
      const first = controls[0]; const last = controls.at(-1);
      if (!first || !last) { event.preventDefault(); dialog.focus(); return; }
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    dialog.addEventListener('cancel', cancel);
    dialog.addEventListener('keydown', containTab);
    return () => { dialog.removeEventListener('cancel', cancel); dialog.removeEventListener('keydown', containTab); dialog.close(); if (trigger?.isConnected) trigger.focus({ preventScroll: true }); };
  }, []);
  return <dialog ref={ref} className={`modal ${kind} ${wide ? 'wide' : ''}`} aria-label={title} onClick={event => { if (event.target === event.currentTarget) { const bounds = event.currentTarget.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose(); } }}>
    <div className="modal-shell"><header className="modal-header"><h2>{title}</h2><IconButton label={`Close ${title.toLowerCase()}`} onClick={onClose}><X size={20} /></IconButton></header><div className="modal-body">{children}</div></div>
  </dialog>;
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) { return <div className="empty"><h2>{title}</h2>{children && <p>{children}</p>}</div>; }
export function DataDetails({ data, title = 'Details' }: { data: unknown; title?: string }) { return <details className="data-details"><summary>{title}</summary><pre tabIndex={0} aria-label={title}>{JSON.stringify(data, null, 2)}</pre></details>; }
export const titleCase = (value: string) => value.charAt(0).toUpperCase() + value.slice(1).replaceAll('_', ' ');
