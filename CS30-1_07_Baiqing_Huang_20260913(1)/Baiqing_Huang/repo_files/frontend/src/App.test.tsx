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
