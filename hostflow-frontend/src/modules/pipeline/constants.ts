/**
 * Constants for pipeline module
 */

// Canonical Kanban columns (backend constants/stages.py)
export const KANBAN_ORDER = [
  'new',
  'interview',
  'hiring',
  'employed',
  'probation',
  'rejected',
] as const;

export const DEFAULT_COLUMN_STAGES: Record<string, string[]> = {
  new: ['new'],
  interview: ['contacted', 'docs_wait', 'docs_got'],
  hiring: ['permit_ordered', 'permit_received', 'visa', 'red_paper', 'trip_plan', 'at_client', 'on_trip'],
  employed: ['employed'],
  probation: ['probation_ok'],
  rejected: ['rejected'],
};

export const DEFAULT_COLUMN_ORDER = Object.keys(DEFAULT_COLUMN_STAGES);
export const DEFAULT_STAGE_SEQUENCE = DEFAULT_COLUMN_ORDER.flatMap(
  (column) => DEFAULT_COLUMN_STAGES[column] || [],
);
export const DEFAULT_STAGE_BY_COLUMN: Record<string, string> = Object.fromEntries(
  DEFAULT_COLUMN_ORDER.map((column) => [column, (DEFAULT_COLUMN_STAGES[column] || [column])[0]]),
);

export const TERMINAL_STAGE_CODES = new Set(['probation_ok', 'rejected']);

