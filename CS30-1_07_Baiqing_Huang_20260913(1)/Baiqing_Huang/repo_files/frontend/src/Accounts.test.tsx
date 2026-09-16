import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { AccountsPage } from './Accounts';
import { ApiError, patch, post, request } from './api';
import type { User } from './types';

vi.mock('./api', async importOriginal => ({ ...await importOriginal<typeof import('./api')>(), request: vi.fn(), post: vi.fn(), patch: vi.fn() }));
const admin: User = { id: 'admin', email: 'admin@example.test', full_name: 'Local admin', role: 'admin', status: 'active', version: 3 };
const learner: User = { id: 'learner', email: 'learner@example.test', full_name: 'Test learner', role: 'student', status: 'active', version: 7 };
beforeEach(() => {
  vi.clearAllMocks(); sessionStorage.clear();
  vi.mocked(request).mockResolvedValue([admin, learner]);
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
});
afterEach(cleanup);

describe('administrator accounts', () => {
  it('keeps self-deactivation unavailable and preserves a stale account until the server accepts a change', async () => {
    vi.mocked(patch).mockRejectedValue(new ApiError('CONFLICT', 'This account changed elsewhere.', 409));
    render(<AccountsPage currentUserId="admin" />);
    await screen.findByText('Test learner');
    const own = screen.getByText('Local admin').closest('article')!;
    expect(within(own).queryByRole('button', { name: 'Deactivate' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Deactivate' }));
    expect(patch).not.toHaveBeenCalled();
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Deactivate account' }));
    await screen.findByText('This account changed elsewhere.');
    expect(patch).toHaveBeenCalledExactlyOnceWith('/admin/users/learner', { version: 7, status: 'deactivated' });
    expect(screen.queryByText('Access deactivated. Earlier sessions have been revoked.')).toBeNull();
    expect(screen.getAllByText('Active')).toHaveLength(2);
  });

  it('validates matching passwords and clears sensitive fields after a real request rejection', async () => {
    vi.mocked(patch).mockRejectedValue(new ApiError('FORBIDDEN', 'Administrator access was revoked.', 403));
    render(<AccountsPage currentUserId="admin" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Reset password' }));
    const dialog = screen.getByRole('dialog');
    const password = within(dialog).getByLabelText('New password') as HTMLInputElement;
    const confirmation = within(dialog).getByLabelText('Confirm new password') as HTMLInputElement;
    fireEvent.change(password, { target: { value: 'Test-secret-123' } });
    fireEvent.change(confirmation, { target: { value: 'Not-matching-123' } });
    fireEvent.submit(dialog.querySelector('form')!);
    await screen.findByText('The passwords do not match.');
    expect(patch).not.toHaveBeenCalled();
    fireEvent.change(confirmation, { target: { value: 'Test-secret-123' } });
    fireEvent.submit(dialog.querySelector('form')!);
    await screen.findByText('Administrator access was revoked.');
    expect(password.value).toBe(''); expect(confirmation.value).toBe('');
    expect(JSON.stringify(sessionStorage)).not.toContain('Test-secret');
    expect(screen.queryByText('Password reset. Earlier sessions have been revoked.')).toBeNull();
  });

  it('adds only the account returned by a completed create request', async () => {
    let complete: (value: User) => void = () => {};
    vi.mocked(post).mockImplementation(() => new Promise(resolve => { complete = resolve as (value: User) => void; }));
    render(<AccountsPage currentUserId="admin" />);
    await screen.findByText('Test learner');
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
    const dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('Full name'), { target: { value: 'New student' } });
    fireEvent.change(within(dialog).getByLabelText('Email'), { target: { value: 'new@example.test' } });
    fireEvent.change(within(dialog).getByLabelText(/Initial password/), { target: { value: 'Test-secret-123' } });
    fireEvent.submit(dialog.querySelector('form')!); fireEvent.submit(dialog.querySelector('form')!);
    expect(post).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('Account created.', { exact: false })).toBeNull();
    complete({ ...learner, id: 'new', full_name: 'New student', email: 'new@example.test', version: 1 });
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(screen.getByText('New student')).toBeTruthy();
  });
});
