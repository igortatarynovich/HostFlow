/**
 * Constants for dashboard module
 */

export const DAY_MS = 24 * 60 * 60 * 1000;

export const QUICK_RANGE_OPTIONS = ['7d', '30d', '90d', 'ytd', 'all'] as const;

export const DIMENSION_OPTIONS = ['stage', 'company', 'vacancy', 'source', 'manager', 'citizenship', 'country', 'reason'] as const;

/** Default stage codes when candidate_stages table is empty (matches backend constants.stages.ORDER) */
export const DEFAULT_STAGE_CODES = [
  'new',
  'no_answer',
  'contacted',
  'questionnaire_submitted',
  'docs_wait',
  'docs_got',
  'permit_ordered',
  'permit_received',
  'visa',
  'red_paper',
  'trip_plan',
  'at_client',
  'employment_pending',
  'on_trip',
  'probation_ok',
  'employed',
  'rejected',
  'declined',
] as const;

