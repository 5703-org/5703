import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { put, request } from './api';
import { StudyLibrary } from './StudyLibrary';
import { useLearningResource } from './learning-ui';
import type { Book, ReadingPage, ReadingPosition, ReadingUnit } from './study-types';

vi.mock('./api', async original => ({
  ...await original<typeof import('./api')>(), request: vi.fn(), put: vi.fn(), post: vi.fn(),
}));

const book: Book = {
  id: 'reader-book', title: 'Reader recovery fixture', edition: 'Edition 1', release_id: 'release',
  document_version_id: 'version', source_sha256: 'authored-pdf-hash', processing_id: 'process',
  source_url: 'https://example.test/reader.pdf', license: 'Authored software fixture', section_count: 1, unit_count: 1,
};
const unit: ReadingUnit = {
  representation: 'cleaned_source_unit', id: 'reader-unit', sequence: 0, page: 1,
  section_id: 'reader-section', section: 'Reader chapter',
  text: '\u{1F9EC} cell, \u{1F4D6} reader with an exact saved point.',
  locator: { release_id: 'release', document_id: book.id, processing_id: 'process', source_unit_id: 'reader-unit', text_hash: 'authored-text-hash', start: 0, end: null },
  source_url: book.source_url, license: book.license,
};
const page: ReadingPage = { items: [unit], offset: 0, next_offset: null, total: 1 };
const position: ReadingPosition = {
  id: 'reader-position', source: unit.locator, char_offset: 8, version: 3,
  updated_at: '2026-10-06T00:00:00Z',
};
const positionPath = '/learning/reading-position';

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function reader(resume = false) {
  return <StudyLibrary bookId={book.id} unitId={resume ? unit.id : undefined} go={vi.fn()} onAsk={vi.fn(async () => {})} />;
}

function withPositions(load: () => Promise<ReadingPosition[]>) {
  const original = vi.mocked(request).getMockImplementation()!;
  vi.mocked(request).mockImplementation(async (path, options) => path === positionPath ? load() : original(path, options));
}

function assertSavedAnchor() {
  const anchor = screen.getByLabelText('Saved reading place');
  expect(anchor.getAttribute('data-reading-offset')).toBe(String(position.char_offset));
  expect(anchor.textContent).toBe(Array.from(unit.text)[position.char_offset]);
  expect(anchor.closest('.source-passage')?.textContent).toBe(unit.text);
  expect(anchor.closest('.source-passage')?.querySelector('mark')).toBeNull();
  expect(vi.mocked(Element.prototype.scrollIntoView).mock.contexts).toContain(anchor);
  return anchor;
}

beforeEach(() => {
  vi.resetAllMocks();
  Element.prototype.scrollIntoView = vi.fn();
  vi.mocked(request).mockImplementation(async path => {
    if (path === '/learning/library') return [book];
    if (path === positionPath) return [position];
    if (path.endsWith('/sections')) return [{ id: 'reader-section', title: 'Reader chapter', first_page: 1, last_page: 1, unit_count: 1, concepts: [], learning_objectives: [], related_section_ids: [] }];
    return page;
  });
});
afterEach(() => { cleanup(); window.getSelection()?.removeAllRanges(); });

describe('saved reader recovery and resource concurrency', () => {
  it('waits for the initial position version before allowing a save', async () => {
    const pending = deferred<ReadingPosition[]>();
    withPositions(() => pending.promise);
    vi.mocked(put).mockResolvedValue({ ...position, version: 4 });
    render(reader());
    const save = await screen.findByRole('button', { name: 'Save reading place' });
    expect(save.hasAttribute('disabled')).toBe(true);
    fireEvent.click(save);
    expect(put).not.toHaveBeenCalled();
    await act(async () => pending.resolve([position]));
    await waitFor(() => expect(save.hasAttribute('disabled')).toBe(false));
    fireEvent.click(save);
    await waitFor(() => expect(put).toHaveBeenCalledExactlyOnceWith(positionPath, { source: unit.locator, char_offset: 0, expected_version: 3 }));
  });

  it.each(['release', 'previous-release'])('does not replace a successful save version with stale %s position data', async releaseId => {
    const stale = deferred<ReadingPosition[]>();
    const old = { ...position, source: { ...position.source, release_id: releaseId } };
    let reads = 0;
    withPositions(() => ++reads === 1 ? Promise.resolve([old]) : reads === 2 ? stale.promise : Promise.resolve([{ ...position, version: 5 }]));
    vi.mocked(put).mockResolvedValueOnce({ ...position, version: 4 }).mockResolvedValueOnce({ ...position, version: 5 });
    render(reader());
    const save = await screen.findByRole('button', { name: 'Save reading place' });
    await waitFor(() => expect(save.hasAttribute('disabled')).toBe(false));
    fireEvent.click(save);
    await screen.findByText('Reading place saved.');
    await waitFor(() => expect(reads).toBe(2));
    await act(async () => stale.resolve([old]));
    await waitFor(() => expect(save.hasAttribute('disabled')).toBe(false));
    fireEvent.click(save);
    await waitFor(() => expect(put).toHaveBeenCalledTimes(2));
    expect(vi.mocked(put).mock.calls.map(([, body]) => body)).toEqual([
      { source: unit.locator, char_offset: 0, expected_version: 3 },
      { source: unit.locator, char_offset: 0, expected_version: 4 },
    ]);
  });

  it('never submits version zero during a pending positions refresh after saving', async () => {
    const pending = deferred<ReadingPosition[]>();
    let reads = 0;
    withPositions(() => ++reads === 1 ? Promise.resolve([position]) : reads === 2 ? pending.promise : Promise.resolve([{ ...position, version: 5 }]));
    vi.mocked(put).mockResolvedValueOnce({ ...position, version: 4 }).mockResolvedValueOnce({ ...position, version: 5 });
    render(reader());
    const save = await screen.findByRole('button', { name: 'Save reading place' });
    await waitFor(() => expect(save.hasAttribute('disabled')).toBe(false));
    fireEvent.click(save);
    await screen.findByText('Reading place saved.');
    await waitFor(() => expect(reads).toBe(2));
    if (save.hasAttribute('disabled')) {
      fireEvent.click(save);
      expect(put).toHaveBeenCalledTimes(1);
      await act(async () => pending.resolve([{ ...position, version: 4 }]));
      await waitFor(() => expect(save.hasAttribute('disabled')).toBe(false));
    }
    fireEvent.click(save);
    await waitFor(() => expect(put).toHaveBeenCalledTimes(2));
    expect(vi.mocked(put).mock.calls[1][1]).toEqual({ source: unit.locator, char_offset: 0, expected_version: 4 });
  });

  it('restores the exact Unicode saved anchor after position data arrives later than its passage', async () => {
    const pending = deferred<ReadingPosition[]>();
    withPositions(() => pending.promise);
    render(reader(true));
    await screen.findByText(unit.text);
    expect(screen.queryByLabelText('Saved reading place')).toBeNull();
    await act(async () => pending.resolve([position]));
    await screen.findByLabelText('Saved reading place');
    await waitFor(() => assertSavedAnchor());
    expect(put).not.toHaveBeenCalled();
  });

  it('reloads the saved anchor on component remount without claiming an installed refresh or relogin check', async () => {
    const first = render(reader(true));
    await screen.findByLabelText('Saved reading place');
    await waitFor(() => assertSavedAnchor());
    first.unmount();
    vi.mocked(Element.prototype.scrollIntoView).mockClear();
    render(reader(true));
    await screen.findByLabelText('Saved reading place');
    await waitFor(() => assertSavedAnchor());
    expect(vi.mocked(request).mock.calls.filter(([path]) => path === positionPath)).toHaveLength(2);
    expect(put).not.toHaveBeenCalled();
  });

  it.each(['response', 'error'])('discards an obsolete page %s after the current page has loaded', async outcome => {
    const old = deferred<{ text: string }>();
    vi.mocked(request).mockImplementation(async path => path === '/reader-old' ? old.promise : { text: 'Current page' });
    function Resource({ path }: { path: string }) {
      const resource = useLearningResource<{ text: string }>(path);
      return <div><p>{resource.data?.text || 'Loading page'}</p>{resource.error !== null && <p role="alert">{String(resource.error)}</p>}</div>;
    }
    const view = render(<Resource path="/reader-old" />);
    view.rerender(<Resource path="/reader-current" />);
    await screen.findByText('Current page');
    await act(async () => {
      if (outcome === 'response') old.resolve({ text: 'Obsolete page' });
      else old.reject(new Error('Obsolete page failure'));
    });
    expect(screen.getByText('Current page')).toBeTruthy();
    expect(screen.queryByText('Obsolete page')).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
