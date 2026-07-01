/**
 * Fleet calendar grid: UTC calendar days (aligned with backend overview / assignment date strings).
 */

import { ISO_DATE, ISO_MONTH } from './fleetQueryParams'

export function utcParseMonthParam(yyyyMm: string): { y: number; m0: number } | null {
  const t = yyyyMm.trim()
  if (!ISO_MONTH.test(t)) return null
  const y = Number(t.slice(0, 4))
  const mo = Number(t.slice(5, 7))
  if (y < 1970 || y > 2100 || mo < 1 || mo > 12) return null
  return { y, m0: mo - 1 }
}

export function utcFirstOfMonth(y: number, m0: number): Date {
  return new Date(Date.UTC(y, m0, 1, 0, 0, 0, 0))
}

/** Last calendar day of the month at 00:00 UTC. */
export function utcLastOfMonth(y: number, m0: number): Date {
  return new Date(Date.UTC(y, m0 + 1, 0, 0, 0, 0, 0))
}

export function utcParseIsoDateMidnight(iso: string): Date | null {
  const s = iso.trim()
  if (!ISO_DATE.test(s)) return null
  const y = Number(s.slice(0, 4))
  const m0 = Number(s.slice(5, 7)) - 1
  const d = Number(s.slice(8, 10))
  const t = Date.UTC(y, m0, d, 0, 0, 0, 0)
  if (Number.isNaN(t)) return null
  return new Date(t)
}

/** Monday 00:00 UTC of the week that contains the given UTC calendar day. */
export function utcMondayOfWeekContaining(d: Date): Date {
  const tick = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
  const dow = new Date(tick).getUTCDay()
  const diff = (dow + 6) % 7
  const monTick = tick - diff * 86400000
  const x = new Date(monTick)
  return new Date(Date.UTC(x.getUTCFullYear(), x.getUTCMonth(), x.getUTCDate(), 0, 0, 0, 0))
}

/** Sunday 00:00 UTC of the same ISO week as `mondayUtc` (Monday-based week). */
export function utcSundayFromMondayUtc(mondayUtc: Date): Date {
  return new Date(
    Date.UTC(
      mondayUtc.getUTCFullYear(),
      mondayUtc.getUTCMonth(),
      mondayUtc.getUTCDate() + 6,
      0,
      0,
      0,
      0,
    ),
  )
}

export function utcAddCalendarMonths(y: number, m0: number, delta: number): { y: number; m0: number } {
  const d = new Date(Date.UTC(y, m0 + delta, 1, 12, 0, 0, 0))
  return { y: d.getUTCFullYear(), m0: d.getUTCMonth() }
}

export function utcEnumerateInclusiveDays(start: Date, end: Date): Date[] {
  const out: Date[] = []
  let cur = new Date(
    Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), start.getUTCDate(), 0, 0, 0, 0),
  )
  const endT = Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate(), 0, 0, 0, 0)
  while (cur.getTime() <= endT) {
    out.push(new Date(cur.getTime()))
    cur = new Date(Date.UTC(cur.getUTCFullYear(), cur.getUTCMonth(), cur.getUTCDate() + 1, 0, 0, 0, 0))
  }
  return out
}

export function utcDayKey(d: Date): string {
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`
}

export function utcNowFirstOfMonth(): Date {
  const n = new Date()
  return utcFirstOfMonth(n.getUTCFullYear(), n.getUTCMonth())
}

export function isSameUtcMonth(a: Date, b: Date): boolean {
  return a.getUTCFullYear() === b.getUTCFullYear() && a.getUTCMonth() === b.getUTCMonth()
}

export function isUtcToday(d: Date, now: Date = new Date()): boolean {
  return utcDayKey(d) === utcDayKey(now)
}

export function isUtcWeekend(d: Date): boolean {
  const dow = d.getUTCDay()
  return dow === 0 || dow === 6
}

export function formatUtcMonthYearLong(d: Date, lang?: string): string {
  return d.toLocaleDateString(lang, { month: 'long', year: 'numeric', timeZone: 'UTC' })
}

export function formatUtcWeekdayDayMonth(d: Date, lang?: string): string {
  return d.toLocaleDateString(lang, { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })
}

export function formatUtcDayMonth(d: Date, lang?: string): string {
  return d.toLocaleDateString(lang, { day: 'numeric', month: 'short', timeZone: 'UTC' })
}

export function formatUtcDayMonthYear(d: Date, lang?: string): string {
  return d.toLocaleDateString(lang, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
}
