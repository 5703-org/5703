import type { AnswerMode } from './types';
import type { TeachingRequest } from './learning-types';
import type { ReadingContext } from './reading-context';

export interface ChatSubmission {
  key: string; targetSession: string; content: string; useProfile: boolean;
  answerMode: AnswerMode; instruction: TeachingRequest; readingContext?: ReadingContext;
  intentSignature: string;
}
export const submissionKey = (userId: string, sessionId?: string) => `cs30.pending.submit.${userId}.${sessionId || 'new'}`;
export function readSubmission(key: string): ChatSubmission | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) || 'null') as ChatSubmission | null;
    if (!value || typeof value.key !== 'string' || !/^[\x21-\x7e]{1,128}$/.test(value.key) || typeof value.targetSession !== 'string' || !value.targetSession || typeof value.content !== 'string' || !value.content.trim() || value.content.length > 4000 || typeof value.useProfile !== 'boolean' || !['textbook', 'general_knowledge'].includes(value.answerMode) || typeof value.intentSignature !== 'string' || !value.instruction || typeof value.instruction !== 'object') return null;
    return value;
  } catch { return null; }
}
