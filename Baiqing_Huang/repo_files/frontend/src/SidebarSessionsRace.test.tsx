import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App } from './App';
import { ApiError, api } from './api';
import type { Session } from './types';

const child = vi.hoisted(() => ({ refresh: undefined as undefined | (() => Promise<void>) }));
vi.mock('./Chat', () => ({ Chat: (props: { refreshSessions: () => Promise<void> }) => { child.refresh = props.refreshSessions; return <div>Offline chat fixture</div>; } }));
vi.mock('./api', async importOriginal => {
  const original = await importOriginal<typeof import('./api')>();
  return { ...original, request: vi.fn(() => { throw new Error('Unexpected offline request'); }), post: vi.fn(), api: { ...original.api, me: vi.fn(), sessions: vi.fn(), profile: vi.fn(), capabilities: vi.fn() } };
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}
const archived: Session = { id: 'archived-owned', title: 'Archived owned conversation', status: 'archived', version: 1, created_at: '2026-10-06T00:00:00Z', updated_at: '2026-10-06T00:00:00Z' };
const active: Session = { ...archived, id: 'active-owned', title: 'Active owned conversation', status: 'active' };
const connectionMessage = 'We could not connect to the server. Please check the connection and try again.';

beforeEach(() => {
  vi.clearAllMocks(); child.refresh = undefined;
  sessionStorage.clear(); sessionStorage.setItem('cs30.access-token', 'synthetic-offline-token');
  history.replaceState({}, '', '/chat');
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Network forbidden in this offline component regression'); }));
  vi.mocked(api.me).mockResolvedValue({ id: 'offline-learner', full_name: 'Offline learner', email: 'learner@example.test', role: 'student', status: 'active', version: 1 });
  vi.mocked(api.sessions).mockReset().mockResolvedValue([]);
  vi.mocked(api.profile).mockResolvedValue({ level: 'intermediate', style: 'concise', language: 'en', topics: [], version: 1 });
  vi.mocked(api.capabilities).mockResolvedValue({ model_mode: 'mock', chat_ready: true, evaluation_ready: false, missing_reasons: { chat: [], evaluation: [] }, providers: [], feature_flags: {}, contract_versions: [] });
  Object.defineProperty(window, 'matchMedia', { configurable: true, value: vi.fn(() => ({ matches: true, addEventListener() {}, removeEventListener() {} })) });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); sessionStorage.clear(); history.replaceState({}, '', '/'); });

async function mounted() {
  const view = render(<App />);
  await screen.findByRole('button', { name: 'New chat' });
  await waitFor(() => expect(api.sessions).toHaveBeenCalledExactlyOnceWith('active'));
  return view;
}

describe('sidebar session request ordering and owner lifetime', () => {
  it('keeps a newer successful archived list when the previous active request rejects', async () => {
    const previous = deferred<Session[]>(); const current = deferred<Session[]>();
    vi.mocked(api.sessions).mockImplementationOnce(() => previous.promise).mockImplementationOnce(() => current.promise);
    await mounted();
    fireEvent.click(screen.getByRole('button', { name: 'Show archived conversations' }));
    await waitFor(() => expect(api.sessions).toHaveBeenNthCalledWith(2, 'archived'));
    await act(async () => current.resolve([archived]));
    await screen.findByRole('button', { name: archived.title });
    await act(async () => previous.reject(new ApiError('CONNECTION_ERROR', connectionMessage)));
    expect(screen.queryByText(connectionMessage)).toBeNull();
    expect(screen.getByRole('button', { name: archived.title })).toBeTruthy();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('does not replace a newer archived list with an older active success', async () => {
    const previous = deferred<Session[]>(); const current = deferred<Session[]>();
    vi.mocked(api.sessions).mockImplementationOnce(() => previous.promise).mockImplementationOnce(() => current.promise);
    await mounted();
    fireEvent.click(screen.getByRole('button', { name: 'Show archived conversations' }));
    await waitFor(() => expect(api.sessions).toHaveBeenNthCalledWith(2, 'archived'));
    await act(async () => current.resolve([archived]));
    await screen.findByRole('button', { name: archived.title });
    await act(async () => previous.resolve([active]));
    expect(screen.getByRole('button', { name: archived.title })).toBeTruthy();
    expect(screen.queryByRole('button', { name: active.title })).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('an older child callback cannot restart its active scope after switching to archived', async () => {
    vi.mocked(api.sessions).mockResolvedValueOnce([active]).mockResolvedValueOnce([archived]);
    await mounted(); const previousScope = child.refresh!;
    await screen.findByRole('button', { name: active.title });
    fireEvent.click(screen.getByRole('button', { name: 'Show archived conversations' }));
    await screen.findByRole('button', { name: archived.title });
    await act(async () => { await previousScope(); });
    expect(api.sessions).toHaveBeenCalledTimes(2);
    expect(screen.getByRole('button', { name: archived.title })).toBeTruthy();
    expect(screen.queryByRole('button', { name: active.title })).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('still displays a current failure and clears it after an explicit successful retry', async () => {
    vi.mocked(api.sessions).mockRejectedValueOnce(new ApiError('CONNECTION_ERROR', connectionMessage)).mockResolvedValueOnce([active]);
    await mounted();
    await screen.findByText(connectionMessage);
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByRole('button', { name: active.title });
    expect(screen.queryByText(connectionMessage)).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('a late child refresh after sign-out cannot fetch the previous owner sessions', async () => {
    const pending = deferred<Session[]>();
    vi.mocked(api.sessions).mockImplementationOnce(() => pending.promise);
    await mounted(); const retained = child.refresh!;
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    await screen.findByRole('button', { name: 'Sign in' });
    await act(async () => { pending.resolve([active]); await retained(); });
    expect(api.sessions).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('button', { name: active.title })).toBeNull();
    expect(sessionStorage.getItem('cs30.access-token')).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('a retained child refresh after unmount does not start another owner request', async () => {
    const pending = deferred<Session[]>();
    vi.mocked(api.sessions).mockImplementationOnce(() => pending.promise);
    const view = await mounted(); const retained = child.refresh!; view.unmount();
    await act(async () => { pending.reject(new ApiError('CONNECTION_ERROR', connectionMessage)); await retained(); });
    expect(api.sessions).toHaveBeenCalledTimes(1);
    expect(fetch).not.toHaveBeenCalled();
  });
});
