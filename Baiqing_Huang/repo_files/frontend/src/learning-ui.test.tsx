import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { passageSelection, sourceUrl, useLearningResource } from './learning-ui';
import { request } from './api';

vi.mock('./api', () => ({ request: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); window.getSelection()?.removeAllRanges(); });

describe('learning reader boundaries', () => {
  it('records the selected occurrence with Unicode code-point offsets', () => {
    const { container } = render(<p>🧬 cell, cell &lt;script&gt;</p>);
    const p = container.querySelector('p')!; const text = p.firstChild!;
    const range = document.createRange(); range.setStart(text, 9); range.setEnd(text, 13);
    const selection = window.getSelection()!; selection.addRange(range);
    expect(passageSelection(p, selection)).toEqual({ text: 'cell', start: 8, end: 12 });
    expect(p.querySelector('script')).toBeNull();
  });
  it('does not treat a range spanning two source units as one unit', () => {
    const { container } = render(<div><p>First source</p><p>Second source</p></div>);
    const [a, b] = container.querySelectorAll('p');
    const range = document.createRange(); range.setStart(a.firstChild!, 0); range.setEnd(b.firstChild!, 4);
    const selection = window.getSelection()!; selection.addRange(range);
    expect(passageSelection(a, selection)).toBeNull();
  });
  it('rejects script and credential-bearing original-source links', () => {
    expect(sourceUrl('javascript:alert(1)')).toBeNull();
    expect(sourceUrl('https://token@example.test/source')).toBeNull();
    expect(sourceUrl('https://openstax.org/books/biology-2e')).toBe('https://openstax.org/books/biology-2e');
  });
  it('does not show an earlier owner or chapter response after navigation', async () => {
    let oldResolve!: (value: { text: string }) => void;
    vi.mocked(request).mockImplementation(path => path === '/old' ? new Promise(resolve => { oldResolve = resolve; }) : Promise.resolve({ text: 'Current chapter' }));
    function Reader({ path }: { path: string }) { const value = useLearningResource<{ text: string }>(path); return <p>{value.data?.text || 'Loading'}</p>; }
    const view = render(<Reader path="/old" />); view.rerender(<Reader path="/new" />);
    await screen.findByText('Current chapter'); oldResolve({ text: 'Previous private chapter' });
    await waitFor(() => expect(screen.queryByText('Previous private chapter')).toBeNull());
  });
});
