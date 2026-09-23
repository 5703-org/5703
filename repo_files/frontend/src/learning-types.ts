import type { components } from './generated/api';
type Schema = components['schemas'];
export type TeachingMode = NonNullable<Schema['ChatMessageCreate']['teaching_mode']>;
export type TaskAction = Schema['ChatMessageCreate']['task_action'];
export type MemorySettings = Schema['MemorySettingsOut'];
export type MemoryEntry = Omit<Schema['MemoryOut'], 'category'> & {
  category: 'preference' | 'goal' | 'confirmed_observation' | 'course_context' | 'self_reported_observation' | 'assessment_performance';
  field_key?: string | null; scope_topics?: string[]; verification?: string; writer_version?: string;
  effective_at?: string | null; source_event_sequence?: number | null; provenance?: Record<string, unknown>;
};
export interface MemorySummary { enabled: boolean; version: string; active_count: number; summary: string; items: MemoryEntry[]; limitations: string[] }
export interface MemoryProcessing { event_id: string; source_message_id: string | null; sequence: number; status: string; operations: {operation?: string; reason?: string}[]; error: {code: string; message: string} | null; created_at: string }
export interface LearnerStatePreview { enabled: boolean; policy_version: string; fields: {field_key: string; content?: string; scope: string; verification: string; source: {memory_id?: string; version?: number; message_id?: string}}[]; entries: MemoryEntry[]; query_topics: string[]; excluded: {id: string; reason: string}[]; limitations: string[] }
export interface MemorySource { message_id: string; session_id: string; content: string }
export type TextSegment = Schema['TextSegment'];
export type CitationView = Schema['CitationView'];
export type Presentation = Schema['PresentationOut'];
export type LearningTask = Schema['TaskOut'];
// The backend exposes these two intentionally bounded objects through dict fields.
export interface ClaimRange {
  claim_id: string; answer_field: 'answer_text' | 'short_answer'; start: number; end: number; text: string;
  fragment_ids?: string[];
  support?: { status?: string; checker_configuration_id?: string; checker_model?: string; strategy?: string; checked_at?: string };
}
export interface MemoryNotice { memory_id: string; version: number; message: string; action: 'undo_save'; source_message_id?: string }
export type ExposureReceipt = Schema['ExposureOut'];
export type ExposureInput = Schema['ExposureInput'];
export type TeachingRequest = Partial<Pick<Schema['ChatMessageCreate'], 'teaching_mode' | 'task_id' | 'task_action'>>;
