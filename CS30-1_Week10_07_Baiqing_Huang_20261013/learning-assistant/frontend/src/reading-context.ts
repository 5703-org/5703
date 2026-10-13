export interface ReadingContext {
  scope: 'chapter' | 'textbook' | 'all';
  document_id?: string;
  source_unit_id?: string;
  selection?: { start: number; end: number; text: string };
}

export const readingContextKey = (userId: string, sessionId?: string) => `cs30.draft.${userId}.${sessionId || 'new'}.reading-context`;

export function readReadingContext(value: string | null): ReadingContext | undefined {
  if (!value) return undefined;
  try {
    const raw: unknown = JSON.parse(value);
    if (!raw || typeof raw !== 'object') return undefined;
    const data = raw as ReadingContext;
    if (!['chapter', 'textbook', 'all'].includes(data.scope)) return undefined;
    if (data.scope !== 'all' && typeof data.document_id !== 'string') return undefined;
    if (data.scope === 'chapter' && typeof data.source_unit_id !== 'string') return undefined;
    const selection = data.selection;
    if (selection && (typeof data.source_unit_id !== 'string' || typeof selection.text !== 'string' ||
      !Number.isInteger(selection.start) || !Number.isInteger(selection.end) || selection.start < 0 ||
      selection.end <= selection.start || Array.from(selection.text).length !== selection.end - selection.start)) return undefined;
    return { scope: data.scope,
      ...(typeof data.document_id === 'string' ? { document_id: data.document_id } : {}),
      ...(typeof data.source_unit_id === 'string' ? { source_unit_id: data.source_unit_id } : {}),
      ...(selection ? { selection: { start: selection.start, end: selection.end, text: selection.text } } : {}),
    };
  } catch { return undefined; }
}
