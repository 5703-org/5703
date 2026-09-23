import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { App } from './App';
import { api, request } from './api';

vi.mock('./api', async importOriginal => {
  const original = await importOriginal<typeof import('./api')>();
  return { ...original, request: vi.fn(), api: { ...original.api, me: vi.fn(), sessions: vi.fn(), profile: vi.fn(), capabilities: vi.fn() } };
});
beforeEach(() => {
  vi.clearAllMocks(); sessionStorage.clear(); sessionStorage.setItem('cs30.access-token', 'test-session');
  vi.mocked(api.me).mockResolvedValue({ id: 'learner', full_name: 'Learner', email: 'learner@example.test', role: 'student', status: 'active', version: 1 });
  vi.mocked(api.sessions).mockResolvedValue([]);
  vi.mocked(api.profile).mockResolvedValue({ level: 'intermediate', style: 'concise', language: 'en', topics: [], version: 1 });
  vi.mocked(api.capabilities).mockResolvedValue({ model_mode: 'mock', chat_ready: true, evaluation_ready: false, missing_reasons: { chat: [], evaluation: [] }, providers: [], feature_flags: {}, contract_versions: [] });
  Object.defineProperty(window, 'matchMedia', { configurable: true, value: vi.fn(() => ({ matches: true, addEventListener() {}, removeEventListener() {} })) });
});
afterEach(() => { cleanup(); sessionStorage.clear(); history.replaceState({}, '', '/'); });

describe('administration route permissions', () => {
  it('opens owned learning memory for a learner and clears its rendered content on sign-out', async () => {
    history.replaceState({}, '', '/chat');
    vi.mocked(request).mockImplementation(async path => {
      if (path === '/me/memory/settings') return { enabled: false, version: 1, revocation_epoch: 0 };
      if (path === '/me/memories') return [{ id: 'own-memory', category: 'goal', field_key: 'learning_goal', content: 'Private learning goal', scope: 'global', source_message_id: null, status: 'active', version: 1, verification: 'explicit_user_statement', writer_version: 'typed_memory_v2', updated_at: '2026-09-20T00:00:00Z', expires_at: null }];
      if (path === '/me/memory/summary') return { enabled: false, version: 'summary-v1', active_count: 1, summary: 'Memory is disabled.', items: [], limitations: [] };
      if (path === '/me/memory/processing') return [{ event_id: 'owned-event', source_message_id: null, sequence: 1, status: 'applied', operations: [{ operation: 'ADD', reason: 'explicit_user_statement' }], error: null, created_at: '2026-09-20T00:00:00Z' }];
      throw new Error(`Unexpected request in owned-memory route fixture: ${path}`);
    });
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Learning memory' }));
    await screen.findByText('Private learning goal');
    expect(location.pathname).toBe('/memory');
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    await screen.findByRole('button', { name: 'Sign in' });
    expect(document.body.innerHTML).not.toContain('Private learning goal');
    expect(sessionStorage.getItem('cs30.access-token')).toBeNull();
  });
  it('refreshes model status after focus without promoting an unavailable result to live', async () => {
    history.replaceState({}, '', '/admin/models');
    render(<App />);
    await screen.findByText('Demo (mock model)', { exact: true });
    vi.mocked(api.capabilities).mockResolvedValueOnce({ model_mode: 'live', chat_ready: true, evaluation_ready: false, missing_reasons: { chat: [], evaluation: [] }, providers: [], feature_flags: {}, contract_versions: [] });
    fireEvent.focus(window);
    await screen.findByText('Live model', { exact: true });
    vi.mocked(api.capabilities).mockRejectedValueOnce(new Error('Model status cannot be reached.'));
    fireEvent.focus(window);
    await screen.findByText('Model status unavailable');
    expect(screen.queryByText('Live model', { exact: true })).toBeNull();
  });
  it.each(['/admin/models', '/admin/accounts', '/admin/failures'])('does not mount privileged data consumers for a learner at %s', async path => {
    history.replaceState({}, '', path);
    render(<App />);
    await screen.findByRole('heading', { name: 'Administrator access required' });
    expect(screen.queryByRole('navigation', { name: 'Administration' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Administration' })).toBeNull();
    expect(request).not.toHaveBeenCalled();
  });
});
