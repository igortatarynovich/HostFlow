/** ADR-046 Analytics View — URL encoding. Not a second reporting product. */

export const ANALYTICS_VIEW_KEYS = {
  range: 'range',
  from: 'from',
  to: 'to',
  companyId: 'company_id',
  vacancyId: 'vacancy_id',
  recruiterId: 'recruiter_id',
  present: 'present',
} as const

export type AnalyticsViewState = {
  range: string
  from: string
  to: string
  companyId: string
  vacancyId: string
  recruiterId: string
  present: boolean
}

export function emptyAnalyticsView(): AnalyticsViewState {
  return {
    range: '',
    from: '',
    to: '',
    companyId: '',
    vacancyId: '',
    recruiterId: '',
    present: false,
  }
}

export function readAnalyticsView(params: URLSearchParams): AnalyticsViewState {
  return {
    range: (params.get(ANALYTICS_VIEW_KEYS.range) || '').trim(),
    from: (params.get(ANALYTICS_VIEW_KEYS.from) || '').trim(),
    to: (params.get(ANALYTICS_VIEW_KEYS.to) || '').trim(),
    companyId: (params.get(ANALYTICS_VIEW_KEYS.companyId) || '').trim(),
    vacancyId: (params.get(ANALYTICS_VIEW_KEYS.vacancyId) || '').trim(),
    recruiterId: (params.get(ANALYTICS_VIEW_KEYS.recruiterId) || '').trim(),
    present: params.get(ANALYTICS_VIEW_KEYS.present) === '1',
  }
}

export function writeAnalyticsView(
  params: URLSearchParams,
  view: Partial<AnalyticsViewState>,
): URLSearchParams {
  const next = new URLSearchParams(params)
  const setOrDelete = (key: string, value: string | undefined) => {
    const v = String(value || '').trim()
    if (v) next.set(key, v)
    else next.delete(key)
  }
  if (view.range !== undefined) setOrDelete(ANALYTICS_VIEW_KEYS.range, view.range === 'custom' ? '' : view.range)
  if (view.from !== undefined) setOrDelete(ANALYTICS_VIEW_KEYS.from, view.from)
  if (view.to !== undefined) setOrDelete(ANALYTICS_VIEW_KEYS.to, view.to)
  if (view.companyId !== undefined) setOrDelete(ANALYTICS_VIEW_KEYS.companyId, view.companyId)
  if (view.vacancyId !== undefined) setOrDelete(ANALYTICS_VIEW_KEYS.vacancyId, view.vacancyId)
  if (view.recruiterId !== undefined) setOrDelete(ANALYTICS_VIEW_KEYS.recruiterId, view.recruiterId)
  if (view.present !== undefined) {
    if (view.present) next.set(ANALYTICS_VIEW_KEYS.present, '1')
    else next.delete(ANALYTICS_VIEW_KEYS.present)
  }
  return next
}

export function isAnalyticsPresentation(params: URLSearchParams): boolean {
  return params.get(ANALYTICS_VIEW_KEYS.present) === '1'
}
