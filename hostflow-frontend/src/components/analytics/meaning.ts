import { stageSemanticForCode, type StatusBadgeSemantic } from '../ui/statusBadgeSemantics'
import { resolveSeriesFill, type UiSemanticTone } from './palette'

/** Closed meaning set — selects the family, not a Recharts component. */
export type AnalyticsMeaning =
  | 'kpi'
  | 'trend'
  | 'composition'
  | 'funnel'
  | 'distribution'
  | 'status'
  | 'progress'
  | 'table'
  | 'breakdown'
  | 'comparison'

export type AnalyticsChartKind =
  | 'kpi-card'
  | 'line-area'
  | 'bar'
  | 'funnel'
  | 'progress'
  | 'analytics-table'
  | 'grouped-bar'

export const MEANING_CHART: Record<AnalyticsMeaning, AnalyticsChartKind> = {
  kpi: 'kpi-card',
  trend: 'line-area',
  composition: 'bar',
  funnel: 'funnel',
  distribution: 'bar',
  status: 'bar',
  progress: 'progress',
  table: 'analytics-table',
  breakdown: 'bar',
  comparison: 'grouped-bar',
}

export function chartKindForMeaning(meaning: AnalyticsMeaning): AnalyticsChartKind {
  return MEANING_CHART[meaning]
}

export const ANALYTICS_STATUS_TONE: Record<string, UiSemanticTone> = {
  rejected: 'danger',
  lost: 'danger',
  overdue: 'danger',
  expired: 'danger',
  wrong_number: 'danger',
  handoff_rejected: 'danger',
  declined: 'warning',
  no_answer: 'warning',
  waiting: 'warning',
  requested: 'neutral',
  missing: 'neutral',
  new: 'neutral',
  unavailable: 'neutral',
  in_progress: 'info',
  attempted: 'info',
  submitted: 'info',
  received: 'info',
  uploaded: 'info',
  contacted: 'info',
  interested: 'info',
  callback_requested: 'info',
  answered: 'success',
  reached: 'success',
  approved: 'success',
  verified: 'success',
  complete: 'success',
  completed: 'success',
  delivered: 'success',
  employed: 'success',
  hired: 'success',
  accepted: 'success',
  not_interested: 'warning',
}

function asUiTone(semantic: StatusBadgeSemantic): UiSemanticTone {
  return semantic
}

/** Status meaning wins. Unknown keys fall back to categorical index. */
export function fillForStatusKey(key: string, index = 0): string {
  const k = String(key || '')
    .trim()
    .toLowerCase()
  const mapped = ANALYTICS_STATUS_TONE[k]
  if (mapped) return resolveSeriesFill({ space: 'semantic', tone: mapped })
  const stageTone = asUiTone(stageSemanticForCode(k))
  if (k && stageTone !== 'neutral' && stageTone !== 'brand') {
    return resolveSeriesFill({ space: 'semantic', tone: stageTone })
  }
  if (k && stageTone === 'brand') return resolveSeriesFill({ space: 'semantic', tone: 'info' })
  return resolveSeriesFill({ space: 'categorical', index })
}

export function toneForStatusKey(key: string): UiSemanticTone {
  const k = String(key || '')
    .trim()
    .toLowerCase()
  if (ANALYTICS_STATUS_TONE[k]) return ANALYTICS_STATUS_TONE[k]
  const stageTone = asUiTone(stageSemanticForCode(k))
  if (stageTone === 'brand') return 'info'
  return stageTone
}
