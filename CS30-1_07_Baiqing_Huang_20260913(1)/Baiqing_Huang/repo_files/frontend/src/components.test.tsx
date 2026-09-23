import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Modal } from './components';

beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); this.querySelector<HTMLButtonElement>('button')?.focus(); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
  // jsdom has no layout. The real source-panel browser check verifies visibility
  // and focus boundaries in Edge; this fixture isolates keyboard-cycle behavior.
  vi.spyOn(HTMLElement.prototype, 'getClientRects').mockReturnValue({ length: 1 } as DOMRectList);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe('modal keyboard boundaries', () => {
  it('excludes focusable content inside a collapsed disclosure at the actual tab boundary', () => {
    render(<Modal title="Source test" onClose={() => {}}><details><summary>Saved identities</summary><pre tabIndex={0}>Collapsed record</pre></details></Modal>);
    const last = screen.getByText('Saved identities');
    last.focus(); fireEvent.keyDown(last, { key: 'Tab' });
    const first = screen.getByRole('button', { name: 'Close source test' });
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(last);
  });
  it('wraps Tab and Shift+Tab within current enabled visible controls', () => {
    render(<Modal title="Source test" onClose={() => {}}><input aria-label="Note" /><button>Last enabled action</button><button disabled>Disabled action</button><button hidden>Hidden action</button></Modal>);
    const first = screen.getByRole('button', { name: 'Close source test' });
    const last = screen.getByRole('button', { name: 'Last enabled action' });
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true }); expect(document.activeElement).toBe(last);
    fireEvent.keyDown(last, { key: 'Tab' }); expect(document.activeElement).toBe(first);
    const middle = screen.getByRole('textbox', { name: 'Note' }); middle.focus();
    expect(fireEvent.keyDown(middle, { key: 'Tab' })).toBe(true);
    expect(document.activeElement).toBe(middle);
  });
});
