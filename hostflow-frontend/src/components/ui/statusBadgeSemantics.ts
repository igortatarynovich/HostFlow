/** STATUS_BADGE_V1 — semantic tokens (palette mapping lives here only). */

export type StatusBadgeSemantic =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral'
  | 'brand'

export type StatusBadgeSize = 'sm' | 'md'

export const STATUS_BADGE_SEMANTIC_CLASSES: Record<StatusBadgeSemantic, string> = {
  success: 'border border-emerald-200 bg-emerald-50 text-emerald-800',
  warning: 'border border-amber-200 bg-amber-50 text-amber-800',
  danger: 'border border-rose-200 bg-rose-50 text-rose-800',
  info: 'border border-blue-200 bg-blue-50 text-blue-800',
  neutral: 'border border-slate-200 bg-slate-100 text-slate-800',
  brand: 'border border-brand-200 bg-brand-50 text-brand-800',
}

/** Dark header / inverse surfaces (NextActionBadge migration). */
export const STATUS_BADGE_SEMANTIC_CLASSES_INVERSE: Record<StatusBadgeSemantic, string> = {
  success: 'border-emerald-300 bg-emerald-500 text-white',
  warning: 'border-amber-200 bg-amber-400 text-amber-950',
  danger: 'border-rose-300 bg-rose-500 text-white',
  info: 'border-blue-300 bg-blue-500 text-white',
  neutral: 'border-white/30 bg-white/15 text-white',
  brand: 'border-brand-300 bg-brand-600 text-white',
}

export const STATUS_BADGE_SIZE_CLASSES: Record<StatusBadgeSize, string> = {
  sm: 'px-1.5 py-0 text-[10px]',
  md: 'px-2 py-0.5 text-xs',
}

/** Candidate + vacancy stage codes → semantic (STATUS_BADGE_V1_DRAFT). */
export const STAGE_SEMANTIC_MAP: Record<string, StatusBadgeSemantic> = {
  new: 'neutral',
  no_answer: 'warning',
  contacted: 'brand',
  interview: 'brand',
  questionnaire_submitted: 'brand',
  docs_wait: 'info',
  docs_got: 'success',
  permit_ordered: 'warning',
  permit_received: 'success',
  visa: 'info',
  red_paper: 'danger',
  trip_plan: 'info',
  at_client: 'neutral',
  employment_pending: 'info',
  on_trip: 'success',
  hiring: 'warning',
  employed: 'success',
  probation: 'info',
  probation_ok: 'success',
  rejected: 'danger',
  declined: 'danger',
  ready_for_handoff: 'info',
  processing_by_client: 'info',
  docs_submitted_permit: 'warning',
  handoff_returned: 'danger',
  open: 'success',
  paused: 'warning',
  closed: 'neutral',
}

export function stageSemanticForCode(code?: string | null): StatusBadgeSemantic {
  const key = String(code || 'new')
    .trim()
    .toLowerCase()
  return STAGE_SEMANTIC_MAP[key] ?? 'neutral'
}

export function documentSeverityToSemantic(
  severity?: 'ok' | 'warn' | 'bad' | 'info' | string,
): StatusBadgeSemantic {
  if (severity === 'ok') return 'success'
  if (severity === 'warn') return 'warning'
  if (severity === 'bad') return 'danger'
  if (severity === 'info') return 'info'
  return 'info'
}

/** NextActionBadge priority → semantic (STATUS_BADGE_V1_DRAFT). */
export function nextActionPriorityToSemantic(
  priority?: 'critical' | 'high' | 'normal' | 'idle' | string | null,
): StatusBadgeSemantic {
  switch (priority) {
    case 'critical':
      return 'danger'
    case 'high':
      return 'warning'
    case 'normal':
      return 'info'
    case 'idle':
    default:
      return 'neutral'
  }
}
