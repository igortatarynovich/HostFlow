/** Shared URL / query normalization for Fleet calendar and assignments. */

export const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/
export const ISO_MONTH = /^\d{4}-\d{2}$/

export const FLEET_ASSIGNMENT_STATUSES = ['planned', 'active', 'completed', 'cancelled'] as const

export type FleetAssignmentStatusFilter = (typeof FLEET_ASSIGNMENT_STATUSES)[number]

export function normalizeFleetAssignmentStatus(raw: string): FleetAssignmentStatusFilter | '' {
  const s = raw.trim().toLowerCase()
  return (FLEET_ASSIGNMENT_STATUSES as readonly string[]).includes(s) ? (s as FleetAssignmentStatusFilter) : ''
}

export function normalizeServiceDateParam(raw: string): string {
  const t = raw.trim()
  return ISO_DATE.test(t) ? t : ''
}

export type FleetCalendarViewParam = 'month' | 'week' | 'agenda'

export function normalizeFleetCalendarView(raw: string): FleetCalendarViewParam | '' {
  const v = raw.trim().toLowerCase()
  if (v === 'month' || v === 'week' || v === 'agenda') return v
  return ''
}

/**
 * Build `/app/fleet/calendar?...` from assignments list query when opened from the calendar
 * (`cal_view`, optional `cal_month` / `cal_week`, plus `line_id` / `status`).
 */
export function fleetCalendarHrefFromAssignmentsQuery(calendarBasePath: string, sp: URLSearchParams): string | null {
  const view = normalizeFleetCalendarView(sp.get('cal_view') ?? '')
  if (!view) return null
  const out = new URLSearchParams()
  out.set('view', view)
  const month = (sp.get('cal_month') ?? '').trim()
  if (month && ISO_MONTH.test(month)) {
    const mo = Number(month.slice(5, 7))
    if (mo >= 1 && mo <= 12) out.set('month', month)
  }
  const week = (sp.get('cal_week') ?? '').trim()
  if (week && isValidIsoCalendarDateUtc(week)) out.set('week', week)
  const lineId = (sp.get('line_id') ?? '').trim()
  if (lineId) out.set('line_id', lineId)
  const st = normalizeFleetAssignmentStatus(sp.get('status') ?? '')
  if (st) out.set('status', st)
  return `${calendarBasePath}?${out.toString()}`
}

// --- UTC drill-down links (align with fleet overview KPIs that use calendar day/month in UTC) ---

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

/** `YYYY-MM` in UTC for the given instant. */
export function utcYyyyMm(d: Date = new Date()): string {
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}`
}

/** `YYYY-MM-DD` in UTC for the given instant. */
export function utcYyyyMmDd(d: Date = new Date()): string {
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}`
}

/** True if `iso` is a real calendar day when interpreted in UTC (rejects e.g. 2026-02-31). */
export function isValidIsoCalendarDateUtc(iso: string): boolean {
  const t = iso.trim()
  if (!ISO_DATE.test(t)) return false
  const [y, m, d] = t.split('-').map(Number)
  const x = new Date(Date.UTC(y, m - 1, d, 12, 0, 0, 0))
  return x.getUTCFullYear() === y && x.getUTCMonth() === m - 1 && x.getUTCDate() === d
}

/** First and last calendar day of the UTC month containing `d`, as ISO dates. */
export function utcMonthRangeIso(d: Date = new Date()): { from: string; to: string } {
  const y = d.getUTCFullYear()
  const m = d.getUTCMonth()
  const from = `${y}-${pad2(m + 1)}-01`
  const last = new Date(Date.UTC(y, m + 1, 0))
  return {
    from,
    to: `${last.getUTCFullYear()}-${pad2(last.getUTCMonth() + 1)}-${pad2(last.getUTCDate())}`,
  }
}

/** Monday (UTC) of the week that contains the UTC calendar day of `d`, as `YYYY-MM-DD`. */
export function utcMondayOfWeekContainingIso(d: Date = new Date()): string {
  const tick = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
  const dow = new Date(tick).getUTCDay()
  const diff = (dow + 6) % 7
  const mon = new Date(tick - diff * 86400000)
  return utcYyyyMmDd(mon)
}

/**
 * After `service_from` / `service_to` change on the assignments page, align `cal_month` / `cal_week`
 * so «back to calendar» matches the active date filter. Mutates `params` in place.
 * Anchor: `service_from`, else `service_to`. If both empty or invalid, drops `cal_month` and `cal_week`.
 */
export function syncFleetCalParamsWithServiceRange(params: URLSearchParams): void {
  const view = normalizeFleetCalendarView(params.get('cal_view') ?? '')
  if (!view) return

  const sf = (params.get('service_from') ?? '').trim()
  const st = (params.get('service_to') ?? '').trim()
  const anchorRaw = sf || st

  if (!anchorRaw || !ISO_DATE.test(anchorRaw)) {
    params.delete('cal_month')
    params.delete('cal_week')
    return
  }

  const [py, pm, pd] = anchorRaw.split('-').map(Number)
  const anchorUtc = new Date(Date.UTC(py, pm - 1, pd, 12, 0, 0, 0))
  if (Number.isNaN(anchorUtc.getTime())) {
    params.delete('cal_month')
    params.delete('cal_week')
    return
  }

  if (view === 'month' || view === 'agenda') {
    params.set('cal_month', utcYyyyMm(anchorUtc))
    params.delete('cal_week')
  } else {
    params.set('cal_week', utcMondayOfWeekContainingIso(anchorUtc))
    params.delete('cal_month')
  }
}

export function fleetCalendarHrefUtcMonth(basePath: string, d: Date = new Date()): string {
  return `${basePath}?view=month&month=${utcYyyyMm(d)}`
}

export function fleetCalendarHrefUtcWeek(basePath: string, d: Date = new Date()): string {
  return `${basePath}?view=week&week=${utcMondayOfWeekContainingIso(d)}`
}

export function fleetAssignmentsHrefUtcRange(basePath: string, from: string, to: string): string {
  const p = new URLSearchParams({ service_from: from, service_to: to })
  return `${basePath}?${p}`
}

export function fleetAssignmentsHrefUtcMonthOverlap(basePath: string, d: Date = new Date()): string {
  const r = utcMonthRangeIso(d)
  return fleetAssignmentsHrefUtcRange(basePath, r.from, r.to)
}

export function fleetAssignmentsHrefUtcSingleDay(basePath: string, d: Date = new Date()): string {
  const day = utcYyyyMmDd(d)
  return fleetAssignmentsHrefUtcRange(basePath, day, day)
}
