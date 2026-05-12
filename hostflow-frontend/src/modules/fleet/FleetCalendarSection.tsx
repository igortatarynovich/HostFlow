import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  listFleetAssignments,
  listFleetOperatingLines,
  type FleetAssignment,
  type FleetOperatingLine,
} from '../../api/fleet'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  utcAddCalendarMonths,
  utcDayKey,
  utcEnumerateInclusiveDays,
  utcFirstOfMonth,
  formatUtcDayMonth,
  formatUtcDayMonthYear,
  formatUtcMonthYearLong,
  formatUtcWeekdayDayMonth,
  isSameUtcMonth,
  isUtcToday,
  isUtcWeekend,
  utcLastOfMonth,
  utcMondayOfWeekContaining,
  utcNowFirstOfMonth,
  utcParseIsoDateMidnight,
  utcParseMonthParam,
  utcSundayFromMondayUtc,
} from './fleetCalendarUtc'
import {
  FLEET_ASSIGNMENT_STATUSES,
  isValidIsoCalendarDateUtc,
  ISO_DATE,
  ISO_MONTH,
  normalizeFleetAssignmentStatus,
  utcMondayOfWeekContainingIso,
  utcYyyyMm,
  utcYyyyMmDd,
} from './fleetQueryParams'

const STATUS_ACCENT: Record<string, string> = {
  planned: 'border-l-blue-500',
  active: 'border-l-emerald-600',
  completed: 'border-l-slate-400',
  cancelled: 'border-l-rose-500',
}

function assignmentCoversDay(a: FleetAssignment, day: Date): boolean {
  const dk = utcDayKey(day)
  const start = (a.service_start || '').slice(0, 10)
  const end = (a.service_end || a.service_start || '').slice(0, 10)
  if (!start) return false
  return dk >= start && dk <= end
}

type CalendarView = 'month' | 'week' | 'agenda'

type CalendarQueryKey = 'line_id' | 'status' | 'view' | 'month' | 'week'

export default function FleetCalendarSection() {
  const { t, locale } = useI18n()
  const [searchParams, setSearchParams] = useSearchParams()
  const [copied, setCopied] = useState(false)
  const filterLineId = (searchParams.get('line_id') ?? '').trim()
  const filterStatus = normalizeFleetAssignmentStatus(searchParams.get('status') ?? '')

  const patchQuery = useCallback(
    (patch: Partial<Record<CalendarQueryKey, string>>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          ;(Object.keys(patch) as CalendarQueryKey[]).forEach((key) => {
            if (patch[key] === undefined) return
            const v = patch[key] ?? ''
            if (v) next.set(key, v)
            else next.delete(key)
          })
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const view: CalendarView = useMemo(() => {
    const v = (searchParams.get('view') ?? '').trim().toLowerCase()
    if (v === 'week' || v === 'agenda' || v === 'month') return v
    return 'month'
  }, [searchParams])

  const weekAnchor = useMemo(() => {
    const w = (searchParams.get('week') ?? '').trim()
    const d = utcParseIsoDateMidnight(w)
    if (d) return utcMondayOfWeekContaining(d)
    return utcMondayOfWeekContaining(new Date())
  }, [searchParams])

  const cursor = useMemo(() => {
    const m = (searchParams.get('month') ?? '').trim()
    const parsed = utcParseMonthParam(m)
    if (parsed) return utcFirstOfMonth(parsed.y, parsed.m0)
    if (view === 'week') return utcFirstOfMonth(weekAnchor.getUTCFullYear(), weekAnchor.getUTCMonth())
    return utcNowFirstOfMonth()
  }, [searchParams, view, weekAnchor])

  const [rows, setRows] = useState<FleetAssignment[]>([])
  const [lines, setLines] = useState<FleetOperatingLine[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  useEffect(() => {
    if (!copied) return
    const tid = window.setTimeout(() => setCopied(false), 2000)
    return () => window.clearTimeout(tid)
  }, [copied])

  useEffect(() => {
    const patch: Partial<Record<CalendarQueryKey, string>> = {}
    const st = (searchParams.get('status') ?? '').trim()
    if (st && !normalizeFleetAssignmentStatus(st)) patch.status = ''
    const vi = (searchParams.get('view') ?? '').trim().toLowerCase()
    if (vi && vi !== 'month' && vi !== 'week' && vi !== 'agenda') patch.view = ''
    const mo = (searchParams.get('month') ?? '').trim()
    if (mo) {
      if (!ISO_MONTH.test(mo)) patch.month = ''
      else {
        const monthNum = Number(mo.slice(5, 7))
        if (monthNum < 1 || monthNum > 12) patch.month = ''
      }
    }
    const wk = (searchParams.get('week') ?? '').trim()
    if (wk && !isValidIsoCalendarDateUtc(wk)) patch.week = ''
    if (Object.keys(patch).length) patchQuery(patch)
  }, [searchParams, patchQuery])

  const applyViewMode = useCallback(
    (next: CalendarView) => {
      if (next === 'week') {
        patchQuery({
          view: 'week',
          week: utcYyyyMmDd(weekAnchor),
          month: '',
        })
      } else if (next === 'month') {
        const m = view === 'week' ? utcFirstOfMonth(weekAnchor.getUTCFullYear(), weekAnchor.getUTCMonth()) : cursor
        patchQuery({
          view: 'month',
          month: utcYyyyMm(m),
          week: '',
        })
      } else {
        const m = view === 'week' ? utcFirstOfMonth(weekAnchor.getUTCFullYear(), weekAnchor.getUTCMonth()) : cursor
        patchQuery({
          view: 'agenda',
          month: utcYyyyMm(m),
          week: '',
        })
      }
    },
    [view, weekAnchor, cursor, patchQuery],
  )

  const goPrevMonth = useCallback(() => {
    const y = cursor.getUTCFullYear()
    const m0 = cursor.getUTCMonth()
    const prev = utcAddCalendarMonths(y, m0, -1)
    patchQuery({ month: utcYyyyMm(utcFirstOfMonth(prev.y, prev.m0)) })
  }, [cursor, patchQuery])

  const goNextMonth = useCallback(() => {
    const y = cursor.getUTCFullYear()
    const m0 = cursor.getUTCMonth()
    const nxt = utcAddCalendarMonths(y, m0, 1)
    patchQuery({ month: utcYyyyMm(utcFirstOfMonth(nxt.y, nxt.m0)) })
  }, [cursor, patchQuery])

  const goThisMonth = useCallback(() => patchQuery({ month: utcYyyyMm(new Date()) }), [patchQuery])

  const goPrevWeek = useCallback(() => {
    const d = new Date(weekAnchor.getTime() - 7 * 86400000)
    patchQuery({ week: utcMondayOfWeekContainingIso(d) })
  }, [weekAnchor, patchQuery])

  const goNextWeek = useCallback(() => {
    const d = new Date(weekAnchor.getTime() + 7 * 86400000)
    patchQuery({ week: utcMondayOfWeekContainingIso(d) })
  }, [weekAnchor, patchQuery])

  const goThisWeek = useCallback(() => patchQuery({ week: utcMondayOfWeekContainingIso(new Date()) }), [patchQuery])

  useEffect(() => {
    let cancelled = false
    listFleetOperatingLines()
      .then((res) => {
        if (!cancelled) setLines(res.items ?? [])
      })
      .catch(() => {
        if (!cancelled) setLines([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  const fetchWindow = useMemo(() => {
    if (view === 'week') {
      const w0 = weekAnchor
      const w1 = utcSundayFromMondayUtc(w0)
      return { from: utcDayKey(w0), to: utcDayKey(w1) }
    }
    const y = cursor.getUTCFullYear()
    const m0 = cursor.getUTCMonth()
    const monthStart = utcFirstOfMonth(y, m0)
    const monthEnd = utcLastOfMonth(y, m0)
    if (view === 'agenda') {
      return { from: utcDayKey(monthStart), to: utcDayKey(monthEnd) }
    }
    const gridStart = utcMondayOfWeekContaining(monthStart)
    const gridEnd = utcSundayFromMondayUtc(utcMondayOfWeekContaining(monthEnd))
    return { from: utcDayKey(gridStart), to: utcDayKey(gridEnd) }
  }, [view, cursor, weekAnchor])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const { items } = await listFleetAssignments({
          service_from: fetchWindow.from,
          service_to: fetchWindow.to,
          line_id: filterLineId || undefined,
          status: filterStatus || undefined,
        })
        if (!cancelled) setRows(items)
      } catch (err) {
        if (!cancelled) setError(getFriendlyErrorInfo(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [fetchWindow.from, fetchWindow.to, filterLineId, filterStatus])

  const { gridDays, agendaDays, weekDays } = useMemo(() => {
    const cy = cursor.getUTCFullYear()
    const cm0 = cursor.getUTCMonth()
    const monthStart = utcFirstOfMonth(cy, cm0)
    const monthEnd = utcLastOfMonth(cy, cm0)
    const gridStart = utcMondayOfWeekContaining(monthStart)
    const gridEnd = utcSundayFromMondayUtc(utcMondayOfWeekContaining(monthEnd))
    const w0 = weekAnchor
    const w1 = utcSundayFromMondayUtc(w0)
    return {
      gridDays: utcEnumerateInclusiveDays(gridStart, gridEnd),
      agendaDays: utcEnumerateInclusiveDays(monthStart, monthEnd),
      weekDays: utcEnumerateInclusiveDays(w0, w1),
    }
  }, [cursor, weekAnchor])

  const byDay = useMemo(() => {
    const dayList = view === 'week' ? weekDays : view === 'agenda' ? agendaDays : gridDays
    const map = new Map<string, FleetAssignment[]>()
    for (const day of dayList) {
      const key = utcDayKey(day)
      const list = rows.filter((a) => assignmentCoversDay(a, day))
      if (list.length) map.set(key, list)
    }
    return map
  }, [rows, view, weekDays, agendaDays, gridDays])

  const weekdayLabels = useMemo(
    () => [
      t('app.fleet.calendar.weekday_mon', { defaultValue: 'Mon' }),
      t('app.fleet.calendar.weekday_tue', { defaultValue: 'Tue' }),
      t('app.fleet.calendar.weekday_wed', { defaultValue: 'Wed' }),
      t('app.fleet.calendar.weekday_thu', { defaultValue: 'Thu' }),
      t('app.fleet.calendar.weekday_fri', { defaultValue: 'Fri' }),
      t('app.fleet.calendar.weekday_sat', { defaultValue: 'Sat' }),
      t('app.fleet.calendar.weekday_sun', { defaultValue: 'Sun' }),
    ],
    [t],
  )

  const STATUS_OPTIONS = FLEET_ASSIGNMENT_STATUSES

  const assignmentsListHref = useCallback(
    (assignmentId?: string) => {
      const p = new URLSearchParams()
      if (filterLineId) p.set('line_id', filterLineId)
      if (filterStatus) p.set('status', filterStatus)
      p.set('service_from', fetchWindow.from)
      p.set('service_to', fetchWindow.to)
      p.set('cal_view', view)
      if (view === 'month' || view === 'agenda') {
        p.set('cal_month', utcYyyyMm(cursor))
      }
      if (view === 'week') {
        p.set('cal_week', utcYyyyMmDd(weekAnchor))
      }
      const qs = p.toString()
      const base = CRM_APP_PATHS.fleetAssignments
      const withQuery = `${base}?${qs}`
      return assignmentId ? `${withQuery}#fleet-assignment-${assignmentId}` : withQuery
    },
    [filterLineId, filterStatus, fetchWindow.from, fetchWindow.to, view, cursor, weekAnchor],
  )

  function assignmentTitle(a: FleetAssignment) {
    const parts = [a.vehicle_label, a.line_name, a.status].filter(Boolean)
    return parts.join(' · ')
  }

  function renderAssignmentChips(list: FleetAssignment[], max: number) {
    const shown = list.slice(0, max)
    const rest = list.length - shown.length
    return (
      <ul className="mt-0.5 space-y-0.5">
        {shown.map((a) => (
          <li key={a.id}>
            <Link
              to={assignmentsListHref(a.id)}
              title={assignmentTitle(a)}
              className={[
                'block truncate rounded border border-slate-100 bg-slate-50/90 pl-1.5 text-[11px] leading-tight text-slate-800 transition hover:bg-white hover:ring-1 hover:ring-slate-200',
                STATUS_ACCENT[a.status] ?? 'border-l-slate-300',
              ].join(' ')}
            >
              <span className="font-medium">{a.vehicle_label}</span>
              <span className="text-slate-500"> · </span>
              <span className="text-slate-600">{a.line_name}</span>
            </Link>
          </li>
        ))}
        {rest > 0 ? (
          <li className="pl-0.5 text-[10px] font-medium text-slate-500">
            +{rest}{' '}
            {t('app.fleet.calendar.more_assignments', { defaultValue: 'more' })}
          </li>
        ) : null}
      </ul>
    )
  }

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900">
          {t('app.fleet.calendar.title', { defaultValue: 'Fleet calendar' })}
        </h1>
        <p className="text-slate-600">
          {t('app.fleet.calendar.subtitle', {
            defaultValue:
              'Calendar days are UTC (same as assignment date strings and fleet KPIs). Assignments show on each day they are active (inclusive). Click a row to open it on the assignments page.',
          })}
        </p>
      </header>

      {error ? (
        <ErrorRecoveryBanner info={error} onRetry={() => window.location.reload()} />
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {t('app.fleet.calendar.view', { defaultValue: 'View' })}
        </span>
        {(['month', 'week', 'agenda'] as const).map((v) => (
          <button
            key={v}
            type="button"
            className={view === v ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => applyViewMode(v)}
          >
            {t(`app.fleet.calendar.view_${v}`, {
              defaultValue: v === 'month' ? 'Month grid' : v === 'week' ? 'Week' : 'Agenda',
            })}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">
            {t('app.fleet.assignments.filter_line', { defaultValue: 'Line' })}
          </span>
          <select
            className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
            value={filterLineId}
            onChange={(ev) => patchQuery({ line_id: ev.target.value })}
          >
            <option value="">{t('app.fleet.assignments.filter_all_lines', { defaultValue: 'All lines' })}</option>
            {lines.map((ln) => (
              <option key={ln.id} value={ln.id}>
                {ln.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">
            {t('app.fleet.assignments.filter_status', { defaultValue: 'Status' })}
          </span>
          <select
            className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
            value={filterStatus}
            onChange={(ev) => patchQuery({ status: ev.target.value })}
          >
            <option value="">{t('app.fleet.assignments.filter_all_status', { defaultValue: 'All statuses' })}</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {t(`app.fleet.assignments.status_${s}`, { defaultValue: s })}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {view === 'month' || view === 'agenda' ? (
          <>
            <button type="button" className="btn-secondary btn-sm" onClick={goPrevMonth}>
              {t('app.fleet.calendar.prev', { defaultValue: 'Previous' })}
            </button>
            <span className="text-base font-semibold text-slate-900">{formatUtcMonthYearLong(cursor, locale)}</span>
            <button type="button" className="btn-secondary btn-sm" onClick={goNextMonth}>
              {t('app.fleet.calendar.next', { defaultValue: 'Next' })}
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={goThisMonth}>
              {t('app.fleet.calendar.today_month', { defaultValue: 'This month' })}
            </button>
          </>
        ) : (
          <>
            <button type="button" className="btn-secondary btn-sm" onClick={goPrevWeek}>
              {t('app.fleet.calendar.prev_week', { defaultValue: 'Previous week' })}
            </button>
            <span className="text-base font-semibold text-slate-900">
              {formatUtcDayMonth(weekAnchor, locale)}
              {' — '}
              {formatUtcDayMonthYear(utcSundayFromMondayUtc(weekAnchor), locale)}
            </span>
            <button type="button" className="btn-secondary btn-sm" onClick={goNextWeek}>
              {t('app.fleet.calendar.next_week', { defaultValue: 'Next week' })}
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={goThisWeek}>
              {t('app.fleet.calendar.this_week', { defaultValue: 'This week' })}
            </button>
          </>
        )}
        <Link
          to={assignmentsListHref()}
          className="text-sm font-medium text-blue-700 hover:underline"
        >
          {t('app.fleet.calendar.open_assignments', { defaultValue: 'Assignments →' })}
        </Link>
        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={() => {
            const href = window.location.href
            void navigator.clipboard.writeText(href).then(() => setCopied(true)).catch(() => {})
          }}
        >
          {t('app.fleet.calendar.copy_link', { defaultValue: 'Copy link' })}
        </button>
        {copied ? (
          <span className="text-xs font-medium text-emerald-700">
            {t('app.fleet.calendar.copied', { defaultValue: 'Copied' })}
          </span>
        ) : null}
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : view === 'month' ? (
        <div className="overflow-x-auto">
          <div className="grid min-w-hf-720 grid-cols-7 gap-px rounded-lg border border-slate-200 bg-slate-200 shadow-sm">
            {weekdayLabels.map((label) => (
              <div
                key={label}
                className="bg-slate-100 px-1 py-2 text-center text-xs font-semibold uppercase tracking-wide text-slate-600"
              >
                {label}
              </div>
            ))}
            {gridDays.map((day) => {
              const key = utcDayKey(day)
              const list = byDay.get(key) ?? []
              const inMonth = isSameUtcMonth(day, cursor)
              const isToday = isUtcToday(day)
              const title =
                list.length > 0
                  ? list.map((a) => assignmentTitle(a)).join('\n')
                  : undefined
              return (
                <div
                  key={key}
                  title={title}
                  className={[
                    'min-h-hf-100 bg-white p-1.5',
                    !inMonth ? 'opacity-50' : '',
                    isToday ? 'ring-2 ring-inset ring-blue-400' : '',
                  ].join(' ')}
                >
                  <div className="flex items-center justify-between gap-1">
                    <span
                      className={[
                        'text-xs font-semibold tabular-nums',
                        isToday ? 'text-blue-700' : 'text-slate-800',
                      ].join(' ')}
                    >
                      {day.getUTCDate()}
                    </span>
                    {list.length > 0 ? (
                      <span className="text-[10px] font-medium text-slate-500">{list.length}</span>
                    ) : null}
                  </div>
                  {list.length > 0 ? renderAssignmentChips(list, 3) : null}
                </div>
              )
            })}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            {t('app.fleet.calendar.month_hint', {
              defaultValue:
                'Days outside this UTC month are dimmed. Data is loaded for the full grid including those days.',
            })}
          </p>
        </div>
      ) : view === 'week' ? (
        <div className="grid gap-3 md:grid-cols-7">
          {weekDays.map((day) => {
            const key = utcDayKey(day)
            const list = byDay.get(key) ?? []
            const isToday = isUtcToday(day)
            const isWeekend = isUtcWeekend(day)
            return (
              <div
                key={key}
                className={[
                  'rounded-lg border border-slate-200 p-2',
                  isWeekend ? 'bg-slate-50/80' : 'bg-white',
                  isToday ? 'ring-2 ring-blue-400' : '',
                ].join(' ')}
              >
                <div className="text-xs font-semibold text-slate-900">{formatUtcWeekdayDayMonth(day, locale)}</div>
                {!list.length ? (
                  <p className="mt-2 text-xs text-slate-400">
                    {t('app.fleet.calendar.no_assignments', { defaultValue: 'No assignments' })}
                  </p>
                ) : (
                  <div className="mt-2 space-y-1">{renderAssignmentChips(list, 12)}</div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="space-y-3">
          {agendaDays.map((day) => {
            const key = utcDayKey(day)
            const list = byDay.get(key)
            const isWeekend = isUtcWeekend(day)
            const isToday = isUtcToday(day)
            return (
              <div
                key={key}
                className={[
                  'rounded-lg border border-slate-200 p-3',
                  isWeekend ? 'bg-slate-50/80' : 'bg-white',
                  list ? 'shadow-sm' : 'opacity-80',
                  isToday ? 'ring-2 ring-blue-300' : '',
                ].join(' ')}
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-900">{formatUtcWeekdayDayMonth(day, locale)}</span>
                  {!list?.length ? (
                    <span className="text-xs text-slate-400">
                      {t('app.fleet.calendar.no_assignments', { defaultValue: 'No assignments' })}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-500">
                      {list.length}{' '}
                      {t('app.fleet.calendar.assignments_count', { defaultValue: 'assignment(s)' })}
                    </span>
                  )}
                </div>
                {list?.length ? (
                  <ul className="mt-2 space-y-1 text-sm text-slate-700">
                    {list.map((a) => (
                      <li
                        key={a.id}
                        className="flex flex-wrap gap-x-2 gap-y-0.5 border-t border-slate-100 pt-1 first:border-t-0 first:pt-0"
                      >
                        <Link
                          to={assignmentsListHref(a.id)}
                          className="inline-flex flex-wrap items-center gap-x-2 gap-y-0.5 font-medium text-blue-800 hover:underline"
                        >
                          <span>{a.vehicle_label}</span>
                          <span className="text-slate-500">·</span>
                          <span>{a.line_name}</span>
                          <span className="text-slate-500">·</span>
                          <span className="rounded bg-slate-100 px-1.5 text-xs font-medium uppercase text-slate-700">
                            {t(`app.fleet.assignments.status_${a.status}`, { defaultValue: a.status })}
                          </span>
                          {a.primary_driver_label ? (
                            <>
                              <span className="text-slate-500">·</span>
                              <span className="font-normal text-slate-700">{a.primary_driver_label}</span>
                            </>
                          ) : null}
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
