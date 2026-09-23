import type { Answer, AnswerMode, Capabilities, Evidence, Feedback, Job, JobReceipt, MessagePage, Profile, Session, User } from './types';
import type { ExposureInput, ExposureReceipt, TeachingRequest } from './learning-types';

const TOKEN_KEY = 'cs30.access-token';
export class ApiError extends Error {
  constructor(public code: string, message: string, public status = 0, public traceId?: string, public details?: Record<string, unknown>) { super(message); this.name = 'ApiError'; }
}
export function getToken() { return sessionStorage.getItem(TOKEN_KEY); }
export function saveToken(value: string) { sessionStorage.setItem(TOKEN_KEY, value); }
export function clearAccount() {
  sessionStorage.removeItem(TOKEN_KEY);
  for (const key of Object.keys(sessionStorage)) if (key.startsWith('cs30.draft.') || key.startsWith('cs30.pending.')) sessionStorage.removeItem(key);
}
export function errorText(error: unknown): string { return error instanceof Error ? error.message : 'Something went wrong. Please try again.'; }

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (getToken()) headers.set('Authorization', `Bearer ${getToken()}`);
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  let response: Response;
  try { response = await fetch(`/api/v1${path}`, { ...init, headers }); }
  catch (error) { if (error instanceof DOMException && error.name === 'AbortError') throw error; throw new ApiError('CONNECTION_ERROR', 'We could not connect to the server. Please check the connection and try again.'); }
  const envelope = await response.json().catch(() => null);
  if (!response.ok) {
    const failure = new ApiError(envelope?.error?.code || `HTTP_${response.status}`, envelope?.error?.message || 'The request could not be completed.', response.status, envelope?.meta?.trace_id, envelope?.error?.details);
    if (response.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('cs30:session-expired'));
    throw failure;
  }
  if (!envelope || !('data' in envelope)) throw new ApiError('INVALID_RESPONSE', 'The server returned an unexpected response. Please try again.');
  return envelope.data as T;
}
export const post = <T,>(path: string, body: unknown = {}, key?: string) => request<T>(path, { method: 'POST', body: JSON.stringify(body), headers: key ? { 'Idempotency-Key': key } : undefined });
export const put = <T,>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) });
export const patch = <T,>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
export const api = {
  me: () => request<User>('/users/me'),
  capabilities: () => request<Capabilities>('/capabilities'),
  profile: () => request<Profile>('/profiles/me'),
  sessions: (status = 'active') => request<Session[]>(`/sessions?status=${encodeURIComponent(status)}`),
  session: (id: string) => request<Session>(`/sessions/${id}`),
  messages: (id: string, after = 0) => request<MessagePage>(`/sessions/${id}/messages?after_sequence=${after}&limit=100`),
  job: (id: string) => request<Job>(`/jobs/${id}`),
  send: (id: string, content: string, useProfile: boolean, key: string, answerMode: AnswerMode = 'textbook', teaching: TeachingRequest = {}) => post<JobReceipt>(`/sessions/${id}/messages`, { content, use_profile: useProfile, answer_mode: answerMode, ...teaching }, key),
  answer: (id: string) => request<Answer>(`/answers/${id}`),
  evidence: (answerId: string, evidenceId: string) => request<Evidence>(`/answers/${answerId}/evidence/${evidenceId}`),
  exposure: (answerId: string, body: ExposureInput, key: string) => post<ExposureReceipt>(`/answers/${answerId}/exposures`, body, key),
  feedback: (id: string) => request<Feedback | null>(`/answers/${id}/feedback`),
};
