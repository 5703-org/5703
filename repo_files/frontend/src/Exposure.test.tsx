import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { webcrypto } from 'node:crypto';
import { api, ApiError } from './api';
import { ObservedPresentation } from './Exposure';

vi.mock('./api', async original => { const value = await original<typeof import('./api')>(); return { ...value, api: { ...value.api, exposure: vi.fn() } }; });
let observe: (visible: boolean) => void;
beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
  vi.stubGlobal('crypto', webcrypto);
  vi.stubGlobal('IntersectionObserver', class { constructor(callback: IntersectionObserverCallback) { observe = visible => callback([{ isIntersecting: visible } as IntersectionObserverEntry], this as unknown as IntersectionObserver); } observe() {} disconnect() {} });
  vi.mocked(api.exposure).mockResolvedValue({ id: 'render-one', kind: 'rendered', presentation_id: 'presentation-one', citation_view: null });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('records only a visible surface and preserves the expanded-source parent receipt', async () => {
  render(<ObservedPresentation answerId="answer-one" exposure={{ presentation_id: 'presentation-one', surface: 'full_source', evidence_id: 'ev_001', parent_exposure_id: 'expanded-one' }}><p>Approved expanded source</p></ObservedPresentation>);
  expect(api.exposure).not.toHaveBeenCalled();
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
  await act(async () => observe(true)); expect(api.exposure).not.toHaveBeenCalled();
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
  fireEvent(document, new Event('visibilitychange'));
  await waitFor(() => expect(api.exposure).toHaveBeenCalledTimes(1));
  expect(api.exposure).toHaveBeenCalledWith('answer-one', { kind: 'rendered', presentation_id: 'presentation-one', surface: 'full_source', evidence_id: 'ev_001', parent_exposure_id: 'expanded-one' }, expect.stringMatching(/^rendered-[0-9a-f]{64}$/));
  await act(async () => { observe(false); observe(true); }); expect(api.exposure).toHaveBeenCalledTimes(1);
});

it('retries a failed display record using the same event identity and keeps the approved answer visible', async () => {
  vi.mocked(api.exposure).mockRejectedValueOnce(new ApiError('CONNECTION_ERROR', 'Connection unavailable.')).mockResolvedValueOnce({ id: 'render-one', kind: 'rendered', presentation_id: 'presentation-one', citation_view: null });
  render(<ObservedPresentation answerId="answer-one" exposure={{ presentation_id: 'presentation-one', surface: 'answer' }}><p>Approved answer remains</p></ObservedPresentation>);
  await act(async () => observe(true)); await screen.findByText('This display could not be recorded.');
  expect(screen.getByText('Approved answer remains')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Retry display record' }));
  await act(async () => observe(true));
  await waitFor(() => expect(api.exposure).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.exposure).mock.calls[0][2]).toBe(vi.mocked(api.exposure).mock.calls[1][2]);
});
