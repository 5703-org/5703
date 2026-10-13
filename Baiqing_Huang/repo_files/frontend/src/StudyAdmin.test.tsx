import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ApiError, post, request } from './api';
import { PracticeAdminPage, type AdminPractice } from './StudyAdmin';

vi.mock('./api', async original => ({ ...await original<typeof import('./api')>(), request: vi.fn(), post: vi.fn() }));
const row: AdminPractice = { item: { id: 'draft', title: 'Authored application fixture', kind: 'mcq', prompt: 'Select A.', options: [{ id: 'A', text: 'A' }, { id: 'B', text: 'B' }], concepts: ['fixture'], conditions: [], source: { release_id: 'r', document_id: 'b', processing_id: 'p', source_unit_id: 'u', text_hash: 'h', start: 0, end: null }, item_revision: 2, validation: { status: 'passed' } }, state: 'validated', version: 4, rubric: { correct_option_ids: ['A'], required_points: [], forbidden_terms: [], acceptable_answers: [], numeric: null, steps: [], hints: [], explanation: 'Private A rule.', common_errors: {} } };
beforeEach(() => { vi.resetAllMocks(); sessionStorage.clear(); vi.mocked(request).mockResolvedValue([row]); HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); }; HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); }; });
afterEach(cleanup);
describe('practice publication permissions and receipts', () => {
  it('keeps model proposal retries idempotent and requires an explicit fresh paid attempt', async () => {
    vi.mocked(request).mockImplementation(async path => path === '/admin/learning/practice' ? [row] : path.endsWith('/units?offset=0&limit=20') ? { items: [], offset: 0, next_offset: null, total: 0 } : []);
    vi.mocked(post).mockRejectedValue(new ApiError('CONNECTION_ERROR', 'Proposal receipt unavailable.'));
    render(<PracticeAdminPage />); fireEvent.click(await screen.findByRole('button', { name: 'Create new revision' })); fireEvent.click(screen.getByRole('button', { name: 'Generate model draft' })); await screen.findByText('Proposal receipt unavailable.');
    expect(vi.mocked(post).mock.calls[0][1]).toEqual({ source: row.item.source, kind: row.item.kind, concepts: row.item.concepts, conditions: row.item.conditions });
    fireEvent.click(screen.getByRole('button', { name: 'Generate model draft' })); await waitFor(() => expect(post).toHaveBeenCalledTimes(2)); expect(vi.mocked(post).mock.calls[1]).toEqual(vi.mocked(post).mock.calls[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Start a fresh generation attempt' })); await waitFor(() => expect(post).toHaveBeenCalledTimes(3)); expect(vi.mocked(post).mock.calls[2][2]).not.toBe(vi.mocked(post).mock.calls[0][2]); expect((screen.getByLabelText('Question') as HTMLTextAreaElement).value).toBe(row.item.prompt); expect(post).not.toHaveBeenCalledWith(expect.stringContaining('/publish'), expect.anything());
  });
  it('requires explicit confirmation and sends the saved version before publication', async () => {
    vi.mocked(post).mockResolvedValue({ ...row, state: 'published', version: 5 }); render(<PracticeAdminPage />); fireEvent.click(await screen.findByRole('button', { name: 'Publish validated revision' })); const button = screen.getByRole('button', { name: 'Confirm publication' }); expect((button as HTMLButtonElement).disabled).toBe(true); expect(post).not.toHaveBeenCalled(); fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(button); await screen.findByText('Authored application fixture: Published. Revision 2.'); expect(post).toHaveBeenCalledExactlyOnceWith('/admin/learning/practice/draft/publish', { expected_version: 4, confirm_source_and_solvability: true });
  });
  it('keeps failed validation visible and never unlocks an unvalidated draft', async () => {
    vi.mocked(request).mockResolvedValue([{ ...row, state: 'draft' }]); vi.mocked(post).mockRejectedValue(new ApiError('INVALID_PRACTICE', 'The question lacks an answer rule.')); render(<PracticeAdminPage />); fireEvent.click(await screen.findByRole('button', { name: 'Validate saved draft' })); await screen.findByText('The question lacks an answer rule.'); expect((screen.getByRole('button', { name: 'Publish validated revision' }) as HTMLButtonElement).disabled).toBe(true); expect(post).toHaveBeenCalledExactlyOnceWith('/admin/learning/practice/draft/validate', undefined);
  });
  it('preserves the confirmation after a publication conflict without a success claim', async () => {
    vi.mocked(post).mockRejectedValue(new ApiError('VERSION_CONFLICT', 'The saved revision changed.')); render(<PracticeAdminPage />); fireEvent.click(await screen.findByRole('button', { name: 'Publish validated revision' })); fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Confirm publication' })); await waitFor(() => expect(screen.getAllByText('The saved revision changed.').length).toBeGreaterThan(0)); expect(screen.getByRole('dialog')).toBeTruthy(); expect(screen.queryByRole('status')).toBeNull();
  });
});
