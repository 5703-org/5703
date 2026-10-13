import type { components } from './generated/api';
import type { ClaimRange, LearningTask, MemoryNotice, Presentation, TeachingMode } from './learning-types';

type Schema = components['schemas'];
export type User = Schema['UserOut'];
export type Profile = Schema['Profile'];
export type Session = Schema['SessionOut'];
export type ApiErrorData = Schema['ErrorData'];
export type ChatResponse = Schema['ChatResponseV1'];
export type MCQResponse = Schema['MCQResponseV1'];
export type Evidence = Schema['EvidenceSnapshot'];
// Historical responses can predate task fields. Dictionary projections are narrowed
// to their public DTO shapes rather than passing arbitrary snapshots to components.
export type Answer = Omit<Schema['AnswerOut'], 'teaching_mode' | 'task_id' | 'help_level' | 'presentation' | 'attribution' | 'memory_notices' | 'learning_task' | 'answer_completeness' | 'reading_context'> & {
  teaching_mode?: TeachingMode; task_id?: string | null; help_level?: number;
  presentation?: Presentation | null; attribution?: { claims?: ClaimRange[]; [key: string]: unknown } | null;
  memory_notices?: MemoryNotice[];
  learning_task?: LearningTask | null;
  answer_completeness?: { status: 'partial' | 'complete_at_requested_help'; missing_requirements: string[]; basis: 'online_checker_model'; human_rating: null } | null;
  reading_context?: { scope: 'chapter' | 'textbook' | 'all'; document_id?: string; source_unit_id?: string; selection?: { start: number; end: number; text: string }; [key: string]: unknown } | null;
};
export type AnswerMode = NonNullable<Schema['ChatMessageCreate']['answer_mode']>;
export type Message = Omit<Schema['MessageOut'], 'answer'> & { answer: Answer | null };
export type MessagePage = Omit<Schema['MessagePage'], 'items'> & { items: Message[] };
export type Job = Schema['JobOut'];
export type JobReceipt = Schema['JobReceipt'];
export type Feedback = Pick<Schema['FeedbackOut'], 'helpful' | 'comment'> & Partial<Omit<Schema['FeedbackOut'], 'helpful' | 'comment'>>;
export type Capabilities = Schema['CapabilitiesOut'];
export type RecordData = Record<string, unknown>;
