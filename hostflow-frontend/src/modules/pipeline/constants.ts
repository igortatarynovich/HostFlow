/**
 * Constants for pipeline module
 */

// Canonical Kanban columns (backend constants/stages.py)
export const KANBAN_ORDER = ['new', 'interview', 'hiring', 'outcomes'] as const;

/** Recruitment kanban fallback (no HR / post-employment columns). */
export const DEFAULT_COLUMN_STAGES: Record<string, string[]> = {
  new: ['new', 'no_answer'],
  interview: ['contacted', 'questionnaire_submitted', 'docs_wait', 'docs_got'],
  hiring: ['permit_ordered', 'ready_for_handoff', 'processing_by_client', 'docs_submitted_permit'],
  outcomes: ['rejected', 'declined', 'handoff_returned'],
};

export const DEFAULT_COLUMN_ORDER = Object.keys(DEFAULT_COLUMN_STAGES);
export const DEFAULT_STAGE_SEQUENCE = DEFAULT_COLUMN_ORDER.flatMap(
  (column) => DEFAULT_COLUMN_STAGES[column] || [],
);
export const DEFAULT_STAGE_BY_COLUMN: Record<string, string> = Object.fromEntries(
  DEFAULT_COLUMN_ORDER.map((column) => [column, (DEFAULT_COLUMN_STAGES[column] || [column])[0]]),
);

export const TERMINAL_STAGE_CODES = new Set(['rejected', 'declined', 'handoff_returned']);

