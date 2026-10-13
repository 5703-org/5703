import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ApiError, post, put, request } from './api';
import { StudyLibrary } from './StudyLibrary';
import type { Book, ReadingPage, ReadingPosition, ReadingUnit } from './study-types';

vi.mock('./api', async original => ({ ...await original<typeof import('./api')>(), request: vi.fn(), post: vi.fn(), put: vi.fn() }));
const book: Book = { id: 'book', title: 'Authored reader fixture', edition: 'Edition 1', release_id: 'release', document_version_id: 'version', source_sha256: 'raw-pdf-hash', processing_id: 'process', source_url: 'https://example.test/book.pdf', license: 'Authored software fixture', section_count: 1, unit_count: 60 };
const unit: ReadingUnit = { representation: 'cleaned_source_unit', id: 'unit', sequence: 22, page: 8, section_id: 'section', section: 'Chapter one', text: '🧬 cell, cell with distinct positions.', locator: { release_id: 'release', document_id: 'book', processing_id: 'process', source_unit_id: 'unit', text_hash: 'hash', start: 0, end: null }, source_url: book.source_url, license: book.license };
const page: ReadingPage = { items: [unit], offset: 20, next_offset: 40, total: 60 };
const position: ReadingPosition = { id: 'position', source: unit.locator, char_offset: 8, version: 3, updated_at: '2026-09-29T01:00:00Z' };
beforeEach(() => { vi.resetAllMocks(); Element.prototype.scrollIntoView = vi.fn(); vi.mocked(request).mockImplementation(async path => path === '/learning/library' ? [book] : path === '/learning/reading-position' ? [position] : path.endsWith('/sections') ? [{ id: 'section', title: 'Chapter one', first_page: 7, last_page: 9, unit_count: 60, concepts: ['cell'], learning_objectives: ['Understand the fixture.'], related_section_ids: [] }] : page); });
afterEach(() => { cleanup(); window.getSelection()?.removeAllRanges(); });
describe('textbook reader source and draft boundaries', () => {
  it('hands the exact selected occurrence to an editable scoped question and bookmark', async () => {
    const onAsk = vi.fn(async () => {}); render(<StudyLibrary bookId="book" go={vi.fn()} onAsk={onAsk} />); const passage = await screen.findByText(unit.text);
    const range = document.createRange(); range.setStart(passage.firstChild!, 9); range.setEnd(passage.firstChild!, 13); window.getSelection()!.addRange(range); fireEvent.mouseUp(passage);
    expect(passage.querySelector('mark')?.textContent).toBe('cell'); expect(passage.textContent).toBe(unit.text);
    fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'Explain this selected occurrence.' } }); fireEvent.change(screen.getByLabelText('Search within'), { target: { value: 'textbook' } }); fireEvent.click(screen.getByRole('button', { name: 'Continue in chat' }));
    await waitFor(() => expect(onAsk).toHaveBeenCalledExactlyOnceWith('Explain this selected occurrence.', { scope: 'textbook', document_id: 'book', source_unit_id: 'unit', selection: { text: 'cell', start: 8, end: 12 } })); expect(post).not.toHaveBeenCalled();
    vi.mocked(post).mockResolvedValue({}); fireEvent.click(screen.getByRole('button', { name: 'Bookmark selected passage' })); await screen.findByText('Passage saved in your notes and bookmarks.'); expect(post).toHaveBeenCalledWith('/learning/notes', expect.objectContaining({ content: 'cell', kind: 'bookmark', source: { ...unit.locator, start: 8, end: 12 } }));
  });
  it('uses the returned containing-page offset when resuming and paging back', async () => {
    render(<StudyLibrary bookId="book" unitId="unit" go={vi.fn()} onAsk={vi.fn(async () => {})} />); await screen.findByText((_text, element) => element?.matches('.source-passage') === true && element.textContent === unit.text); expect(request).toHaveBeenCalledWith('/learning/library/book/units?offset=0&limit=20&source_unit_id=unit', expect.any(Object)); fireEvent.click(screen.getByRole('button', { name: 'Previous passages' })); await waitFor(() => expect(request).toHaveBeenCalledWith('/learning/library/book/units?offset=0&limit=20', expect.any(Object))); expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });
  it('retains the question and selected source when opening a new chat fails', async () => {
    const onAsk = vi.fn(async () => { throw new ApiError('CONNECTION_ERROR', 'Unable to create the conversation.'); }); render(<StudyLibrary bookId="book" go={vi.fn()} onAsk={onAsk} />); fireEvent.click(await screen.findByRole('button', { name: 'Ask about this passage' })); fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'Preserve this draft.' } }); fireEvent.click(screen.getByRole('button', { name: 'Continue in chat' })); await screen.findByText('Unable to create the conversation.'); expect((screen.getByLabelText('Your question') as HTMLTextAreaElement).value).toBe('Preserve this draft.'); expect(screen.getByRole('button', { name: 'Bookmark selected passage' }).hasAttribute('disabled')).toBe(false);
  });
  it('uses the actual position version and reports a conflict without saved success', async () => {
    vi.mocked(put).mockRejectedValue(new ApiError('VERSION_CONFLICT', 'Reading position changed.')); render(<StudyLibrary bookId="book" go={vi.fn()} onAsk={vi.fn(async () => {})} />); fireEvent.click(await screen.findByRole('button', { name: 'Save reading place' })); await screen.findByText('Reading position changed.'); expect(put).toHaveBeenCalledExactlyOnceWith('/learning/reading-position', { source: unit.locator, char_offset: 0, expected_version: 3 }); expect(screen.queryByText('Reading place saved.')).toBeNull();
  });
  it('updates a previous release reading position with its real version', async () => {
    const previous = vi.mocked(request).getMockImplementation()!;
    vi.mocked(request).mockImplementation(async (path, options) => path === '/learning/reading-position' ? [{ ...position, source: { ...position.source, release_id: 'older-release' } }] : previous(path, options));
    vi.mocked(put).mockResolvedValue({ ...position, version: 4 }); render(<StudyLibrary bookId="book" go={vi.fn()} onAsk={vi.fn(async () => {})} />); fireEvent.click(await screen.findByRole('button', { name: 'Save reading place' })); await screen.findByText('Reading place saved.'); expect(put).toHaveBeenCalledExactlyOnceWith('/learning/reading-position', { source: unit.locator, char_offset: 0, expected_version: 3 });
  });
});
