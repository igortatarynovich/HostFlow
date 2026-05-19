/**
 * Constants for dashboard module
 */

export const DAY_MS = 24 * 60 * 60 * 1000;

export const QUICK_RANGE_OPTIONS = ['7d', '30d', '90d', 'ytd', 'all'] as const;

export const DIMENSION_OPTIONS = ['stage', 'company', 'vacancy', 'source', 'manager', 'citizenship', 'country', 'reason'] as const;

import { RECRUITMENT_DEFAULT_STAGE_ORDER } from '../../constants/recruitmentStageSurface'

/** Default stage codes for recruitment dashboard filters when funnel table is empty. */
export const DEFAULT_STAGE_CODES = [...RECRUITMENT_DEFAULT_STAGE_ORDER] as const

