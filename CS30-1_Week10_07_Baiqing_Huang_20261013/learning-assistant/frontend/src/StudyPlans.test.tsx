import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ApiError, post, request } from './api';
import { StudyGoals, StudyNotes } from './StudyPlans';
import type { StudyNote } from './study-types';

vi.mock('./api', async original => ({ ...await original<typeof import('./api')>(), request: vi.fn(), post: vi.fn(), patch: vi.fn() }));
const note: StudyNote = { id: 'note', title: 'My source note', content: 'My own interpretation.', kind: 'bookmark', source: { release_id: 'release', document_id: 'book', processing_id: 'process', source_unit_id: 'unit', text_hash: 'hash', start: 2, end: 10 }, answer_id: null, goal_id: null, concepts: ['concept'], version: 2, created_at: '', updated_at: '', source_type: 'personal_note' };
beforeEach(() => { vi.resetAllMocks(); history.replaceState({}, '', '/learn/notes'); HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); }; HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); }; }); afterEach(cleanup);
describe('saved goals and personal notes', () => {
  it('counts only graded practice in correctness and keeps pending work separate', async () => {
    const goal = { id: 'goal', title: 'Review this chapter', document_id: 'book', release_id: 'release', depth: 'beginner', status: 'active', version: 1, units: [{ id: 'goal-unit', section_id: 'section', title: 'Chapter one', concepts: [], prerequisite_unit_ids: [], read: true, attempts: 5, correct_attempts: 2, graded_attempts: 2, pending_attempts: 3, needs_review: false, status: 'read', recommended_action: 'practise', prerequisite_origin: 'section_order_suggestion' }] };
    vi.mocked(request).mockImplementation(async path => path === '/learning/goals' ? [goal] : []);
    render(<StudyGoals go={vi.fn()} />);
    expect(await screen.findByText('2 correct of 2 graded attempts · 3 pending review')).toBeTruthy(); expect(screen.queryByText(/2 correct of 5/)).toBeNull();
  });
  it('keeps a note and its source when version-bound deletion is rejected', async () => {
    vi.mocked(request).mockImplementation(async (path, init) => { if (init?.method === 'DELETE') throw new ApiError('VERSION_CONFLICT', 'This note has a newer version.'); return path === '/learning/notes' ? [note] : []; }); render(<StudyNotes go={vi.fn()} />); fireEvent.click(await screen.findByRole('button', { name: 'Delete note' })); fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete note' })); await waitFor(() => expect(screen.getAllByText('This note has a newer version.').length).toBeGreaterThan(0)); expect(request).toHaveBeenCalledWith('/learning/notes/note?expected_version=2', { method: 'DELETE' }); expect(screen.getByRole('heading', { name: note.title })).toBeTruthy(); expect(screen.queryByText('Note deleted.')).toBeNull();
  });
  it('creates a review card with the original locator and explicit personal content', async () => {
    vi.mocked(request).mockImplementation(async path => path === '/learning/notes' ? [note] : []); vi.mocked(post).mockResolvedValue({}); render(<StudyNotes go={vi.fn()} />); fireEvent.click(await screen.findByRole('button', { name: 'Make a review card' })); await screen.findByText('Review card saved and due now. Edit its prompt and answer in your own words.'); expect(post).toHaveBeenCalledExactlyOnceWith('/learning/notes', { title: 'Review: My source note', content: note.content, kind: 'review_card', source: note.source, answer_id: null, goal_id: null, concepts: note.concepts });
  });
  it('disables card creation when the source note has no content', async () => {
    vi.mocked(request).mockImplementation(async path => path === '/learning/notes' ? [{ ...note, content: '  \n  ' }] : []); render(<StudyNotes go={vi.fn()} />);
    const button = await screen.findByRole('button', { name: 'Make a review card' }); expect((button as HTMLButtonElement).disabled).toBe(true); fireEvent.click(button); expect(post).not.toHaveBeenCalled();
  });
  it('opens a specific note from a review card link', async () => {
    history.replaceState({}, '', '/learn/notes/note%2Fwith%20space'); const selected = { ...note, id: 'note/with space' }; const other = { ...note, id: 'other', title: 'Another note' };
    vi.mocked(request).mockImplementation(async path => path === '/learning/notes' ? [selected, other] : []); const go = vi.fn(); render(<StudyNotes go={go} />);
    expect(await screen.findByRole('heading', { name: selected.title })).toBeTruthy(); expect(screen.queryByRole('heading', { name: other.title })).toBeNull(); fireEvent.click(screen.getByRole('button', { name: 'All notes' })); expect(go).toHaveBeenCalledWith('/learn/notes');
  });
  it('marks reading only after the saved goal version is accepted', async () => {
    vi.mocked(request).mockImplementation(async path => path === '/learning/goals' ? [{ id: 'goal', title: 'Learn the chapter', document_id: 'book', release_id: 'release', depth: 'beginner', status: 'active', version: 5, units: [{ id: 'goal-unit', section_id: 'section', title: 'Chapter one', concepts: [], prerequisite_unit_ids: [], read: false, attempts: 0, correct_attempts: 0, needs_review: false, status: 'not_started', recommended_action: 'read', prerequisite_origin: 'section_order_suggestion' }] }] : []); vi.mocked(post).mockRejectedValue(new ApiError('VERSION_CONFLICT', 'Reload this goal.')); render(<StudyGoals go={vi.fn()} />); fireEvent.click(await screen.findByRole('button', { name: 'Mark as read' })); await screen.findByText('Reload this goal.'); expect(post).toHaveBeenCalledExactlyOnceWith('/learning/goals/goal/units/goal-unit/read', { expected_version: 5 }); expect(screen.queryByText('Read recorded')).toBeNull(); expect(screen.getByText(/Reading marks activity/)).toBeTruthy();
  });
  it('separates reviewed concept evidence from section-order suggestions', async () => {
    const goal = { id: 'goal', title: 'Osmosis path', document_id: 'book', release_id: 'release', depth: 'beginner', status: 'active', version: 1, units: [
      { id: 'first', section_id: 'diffusion', title: 'Diffusion', concepts: ['diffusion'], prerequisite_unit_ids: [], read: false, attempts: 0, correct_attempts: 0, needs_review: false, status: 'not_started', recommended_action: 'read', prerequisite_origin: 'section_order_suggestion' },
      { id: 'second', section_id: 'osmosis', title: 'Osmosis', concepts: ['osmosis'], prerequisite_unit_ids: ['first'], read: false, attempts: 0, correct_attempts: 0, needs_review: false, status: 'not_started', recommended_action: 'read', prerequisite_origin: 'section_order_suggestion' },
    ], reviewed_relations: [{ id: 'relation', relation_type: 'prerequisite', from_unit_id: 'first', to_unit_id: 'second', from_concept: 'diffusion', to_concept: 'osmosis', reason: 'The cited textbook defines diffusion before the water-specific process.', source: { release_id: 'release', document_id: 'book', processing_id: 'process', source_unit_id: 'source-unit', text_hash: 'hash', start: 0, end: 20 }, source_quote: 'Diffusion helps explain osmosis.', source_quote_hash: 'abcdef1234567890', source_book: 'Biology 2e', source_edition: '2e', source_section: 'Diffusion', source_page: 42, source_url: 'https://openstax.org/', reviewed_at: '2026-09-30T00:00:00Z', provenance: 'administrator_reviewed_released_source' }] };
    vi.mocked(request).mockImplementation(async path => path === '/learning/goals' ? [goal] : []);
    const go = vi.fn(); render(<StudyGoals go={go} />);
    expect(await screen.findByRole('region', { name: 'Reviewed concept relationships' })).toBeTruthy();
    expect(screen.getByText('Diffusion helps explain osmosis.')).toBeTruthy();
    expect(screen.getByText(/Biology 2e.*Diffusion.*physical page 42/)).toBeTruthy();
    expect(screen.getByText(/earlier unit\(s\) suggested/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Read cited passage' }));
    expect(go).toHaveBeenCalledWith('/learn/library/book/unit/source-unit');
  });
});
