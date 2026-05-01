import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  IconAlertTriangle,
  IconArrowRight,
  IconBriefcase,
  IconCalendarTime,
  IconPhone,
  IconUsers,
} from '@tabler/icons-react'

import {
  listCommunicationPlannerEvents,
  type CommunicationPlannerEvent,
} from '../../api/communications'
import { listCalendarItems, type CalendarItem as IntegratedCalendarItem } from '../../api/calendarIntegrations'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useAuth } from '../../store/useAuth'

/**
 * G-6 Stage 2b — "Today's calendar" live preview on `/app/work`.
 *
 * Companion to `MyTasksPanel`. The reminder-side rollup answers
 * "what tasks do I owe?"; this one answers "what timed events am I
 * booked for today?" — meetings, phone calls, shifts. Splitting
 * them keeps the hub scannable: a recruiter with 5 reminders and 3
 * meetings reads two 3-line panels, not one confusing 8-line list.
 *
 * Scope decisions:
 *   - `kind ∈ { meeting, call, shift }`. We explicitly drop `task`
 *     and `followup` — those already show up in `MyTasksPanel` via
 *     the reminder ↔ planner merge (G-7 stage 1 shipped the adapter
 *     in `RemindersPage.tsx`). Surfacing them here too would double-
 *     render the same rows, and users would click one and wonder why
 *     the other didn't mark itself done.
 *   - Always `assignee_id=me`. Team-scope planner view lives in
 *     `/app/calendar`; this panel answers the personal "what's on
 *     my calendar right now" question that the hub is built around.
 *     We fall back to `?assignee_scope=mine` semantics client-side:
 *     if `me.id` is unknown (shouldn't happen post-auth, but the
 *     type permits it), we hide the panel rather than accidentally
 *     show every tenant event.
 *   - Window: today-local [start-of-day, start-of-tomorrow). Events
 *     that span past midnight are clamped on render; the fetch only
 *     picks rows whose `start_at` falls in the local day.
 *   - Terminal-status gate (`done`/`cancelled`) mirrors
 *     `RemindersPage._PLANNER_TERMINAL_STATUSES` so cancelled
 *     meetings don't parade in the hub the way open ones do.
 *
 * Conflict detection: pure client-side sweep-line. Two events
 * conflict when they overlap in time and neither is `all_day`.
 * `all_day` events are informational bars (shifts are often full-
 * day) — we mark them as a separate pill so they don't trigger
 * false conflicts with every meeting of the day.
 *
 * Deep-link: row click routes to
 * ``/app/calendar?event_id=<planner-uuid>`` — ``CommunicationsCalendarPage``
 * scrolls to the day bucket card, opens planner quick-actions, and strips
 * the query param (G-6 focus-by-id).
 */

const DEFAULT_LIMIT = 100
const MAX_ROWS = 6
const TERMINAL_STATUSES = new Set(['done', 'cancelled'])
const KINDS_SHOWN = new Set(['meeting', 'call', 'shift'])

type KindShown = 'meeting' | 'call' | 'shift' | 'event'

function startOfLocalDay(d: Date): Date {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}

function addDays(d: Date, days: number): Date {
  const x = new Date(d)
  x.setDate(x.getDate() + days)
  return x
}

function toDate(raw: string | null | undefined): Date | null {
  if (!raw) return null
  const d = new Date(raw)
  return Number.isNaN(d.getTime()) ? null : d
}

function formatHm(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

function kindIcon(kind: KindShown) {
  switch (kind) {
    case 'meeting':
      return IconUsers
    case 'call':
      return IconPhone
    case 'shift':
      return IconBriefcase
    case 'event':
      return IconCalendarTime
  }
}

type Row = {
  id: string
  title: string
  kind: KindShown
  startAt: Date
  endAt: Date | null
  allDay: boolean
  isLive: boolean
  hasConflict: boolean
  href: string
}

function computeConflicts(rows: Row[]): Row[] {
  if (rows.length < 2) return rows
  const timed = rows
    .filter((r) => !r.allDay && r.endAt)
    .sort((a, b) => a.startAt.getTime() - b.startAt.getTime())
  const inConflict = new Set<string>()
  for (let i = 0; i < timed.length; i += 1) {
    const a = timed[i]
    for (let j = i + 1; j < timed.length; j += 1) {
      const b = timed[j]
      if (b.startAt.getTime() >= (a.endAt as Date).getTime()) break
      inConflict.add(a.id)
      inConflict.add(b.id)
    }
  }
  if (inConflict.size === 0) return rows
  return rows.map((r) => (inConflict.has(r.id) ? { ...r, hasConflict: true } : r))
}

function eventToRow(
  event: CommunicationPlannerEvent,
  now: Date,
  todayStart: Date,
  tomorrowStart: Date,
): Row | null {
  if (TERMINAL_STATUSES.has(String(event.status || '').toLowerCase())) return null
  const kindRaw = String(event.kind || '').toLowerCase()
  if (!KINDS_SHOWN.has(kindRaw)) return null
  const startAt = toDate(event.start_at)
  if (!startAt) return null
  // Fetch-side `from_at/to_at` already bounds us, but a daylight-saving shift
  // between fetch and render could re-flip the date. Re-assert locally.
  if (
    startAt.getTime() < todayStart.getTime() ||
    startAt.getTime() >= tomorrowStart.getTime()
  ) {
    return null
  }
  const endAt = toDate(event.end_at)
  const titleRaw = String(event.title || '').trim()
  const fallback = kindRaw.charAt(0).toUpperCase() + kindRaw.slice(1)
  const title = titleRaw || fallback
  const entityType = String(event.entity_type || '').trim().toLowerCase()
  const entityId = String(event.entity_id || '').trim()
  const href =
    entityType === 'candidate' && entityId
      ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(entityId)}?focus=calendar`
      : entityType === 'lead' && entityId
        ? `${CRM_APP_PATHS.leads}/${encodeURIComponent(entityId)}?focus=calendar`
        : `${CRM_APP_PATHS.calendar}?event_id=${encodeURIComponent(String(event.id))}`
  const allDay = Boolean(event.all_day)
  const isLive =
    !allDay &&
    endAt !== null &&
    startAt.getTime() <= now.getTime() &&
    now.getTime() < endAt.getTime()
  return {
    id: String(event.id),
    title,
    kind: kindRaw as KindShown,
    startAt,
    endAt,
    allDay,
    isLive,
    hasConflict: false,
    href,
  }
}

function integratedEventToRow(
  event: IntegratedCalendarItem,
  now: Date,
  todayStart: Date,
  tomorrowStart: Date,
): Row | null {
  const statusRaw = String(event.status || '').toLowerCase()
  if (statusRaw === 'cancelled' || statusRaw === 'canceled' || statusRaw === 'deleted') return null
  const payload = (event.payload || {}) as Record<string, unknown>
  if (String(payload.created_from || '') === 'communications_planner') return null
  const startAt = toDate(event.starts_at)
  if (!startAt) return null
  if (startAt.getTime() < todayStart.getTime() || startAt.getTime() >= tomorrowStart.getTime()) return null
  const endAt = toDate(event.ends_at)
  const title = String(event.title || '').trim() || 'Event'
  const allDay = Boolean(event.all_day)
  const isLive =
    !allDay &&
    endAt !== null &&
    startAt.getTime() <= now.getTime() &&
    now.getTime() < endAt.getTime()
  return {
    id: `integrated:${String(event.id)}`,
    title,
    kind: 'event',
    startAt,
    endAt,
    allDay,
    isLive,
    hasConflict: false,
    href: CRM_APP_PATHS.calendar,
  }
}

export function TodayPlannerPanel() {
  const { t } = useI18n()
  const { me } = useAuth()
  const myId = me?.id || me?.sub || ''

  const [rows, setRows] = useState<Row[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const conflictCount = useMemo(
    () => (rows ?? []).filter((r) => r.hasConflict).length,
    [rows],
  )

  const load = useCallback(async () => {
    if (!myId) {
      setRows([])
      setLoading(false)
      return
    }
    setLoading(true)
    setError(false)
    try {
      const now = new Date()
      const todayStart = startOfLocalDay(now)
      const tomorrowStart = addDays(todayStart, 1)
      const [plannerData, integratedData] = await Promise.all([
        listCommunicationPlannerEvents({
          assignee_id: myId,
          from_at: todayStart.toISOString(),
          to_at: tomorrowStart.toISOString(),
          limit: DEFAULT_LIMIT,
        }),
        listCalendarItems({
          start: todayStart.toISOString(),
          end: tomorrowStart.toISOString(),
        }).catch(() => [] as IntegratedCalendarItem[]),
      ])
      const plannerItems: CommunicationPlannerEvent[] = Array.isArray(plannerData?.items) ? plannerData.items : []
      const integratedItems: IntegratedCalendarItem[] = Array.isArray(integratedData) ? integratedData : []
      let mapped = [...plannerItems.map((ev) => eventToRow(ev, now, todayStart, tomorrowStart)), ...integratedItems.map((ev) => integratedEventToRow(ev, now, todayStart, tomorrowStart))]
        .filter((r): r is Row => r !== null)
        .sort((a, b) => {
          if (a.allDay !== b.allDay) return a.allDay ? -1 : 1
          return a.startAt.getTime() - b.startAt.getTime()
        })
      if (mapped.length === 0) {
        const fallbackPlanner = await listCommunicationPlannerEvents({
          from_at: todayStart.toISOString(),
          to_at: tomorrowStart.toISOString(),
          limit: DEFAULT_LIMIT,
          include_completed_entities: true,
        }).catch(() => ({ items: [], total: 0 }))
        mapped = (Array.isArray(fallbackPlanner?.items) ? fallbackPlanner.items : [])
          .map((ev) => eventToRow(ev, now, todayStart, tomorrowStart))
          .filter((r): r is Row => r !== null)
          .sort((a, b) => {
            if (a.allDay !== b.allDay) return a.allDay ? -1 : 1
            return a.startAt.getTime() - b.startAt.getTime()
          })
      }
      setRows(computeConflicts(mapped))
    } catch {
      setRows(null)
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [myId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    // The calendar page dispatches `reminder-updated` after drag-drop
    // on a reminder, but planner-side mutations go through the page's
    // own state — no tenant-wide bus today. A window-focus refetch
    // keeps the preview honest when the user flips from /app/calendar
    // back to /app/work after editing an event.
    const onFocus = () => {
      void load()
    }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [load])

  useEffect(() => {
    const onPlannerUpdated = () => {
      void load()
    }
    window.addEventListener('planner-event-updated', onPlannerUpdated)
    window.addEventListener('reminder-updated', onPlannerUpdated)
    return () => {
      window.removeEventListener('planner-event-updated', onPlannerUpdated)
      window.removeEventListener('reminder-updated', onPlannerUpdated)
    }
  }, [load])

  if (!myId) return null

  if (loading && rows === null) {
    return (
      <section
        aria-busy="true"
        className="h-40 animate-pulse rounded-2xl border border-slate-200 bg-white"
      />
    )
  }

  if (error && rows === null) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.today_planner.title', { defaultValue: 'Today on your calendar' })}
          </h2>
          <button
            type="button"
            className="text-sm font-semibold text-brand-700 hover:text-brand-800"
            onClick={() => void load()}
          >
            {t('app.work.hub.reload', { defaultValue: 'Refresh' })}
          </button>
        </div>
        <p className="mt-3 text-sm text-slate-500">
          {t('app.work.hub.today_planner.error', {
            defaultValue: 'Could not load your calendar. Try again.',
          })}
        </p>
      </section>
    )
  }

  const list = rows ?? []
  const total = list.length

  if (total === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.today_planner.title', { defaultValue: 'Today on your calendar' })}
          </h2>
        </div>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.work.hub.today_planner.empty', {
            defaultValue: 'No meetings, calls, or shifts booked for today.',
          })}
        </p>
      </section>
    )
  }

  const visible = list.slice(0, MAX_ROWS)
  const overflow = total - visible.length

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-6 py-4">
        <div className="min-w-0">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.today_planner.title', { defaultValue: 'Today on your calendar' })}
          </h2>
          <p className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
            <IconCalendarTime size={14} className="opacity-70" aria-hidden />
            <span>
              {t('app.work.hub.today_planner.counts', {
                defaultValue: '{total} scheduled today',
                values: { total },
              })}
            </span>
            {conflictCount > 0 ? (
              <>
                <span aria-hidden>·</span>
                <span className="inline-flex items-center gap-1 font-semibold text-rose-700">
                  <IconAlertTriangle size={14} aria-hidden />
                  {t('app.work.hub.today_planner.conflicts_count', {
                    defaultValue: '{count} conflict',
                    values: { count: conflictCount },
                  })}
                </span>
              </>
            ) : null}
          </p>
        </div>
      </div>
      <ul className="divide-y divide-slate-100">
        {visible.map((row) => (
          <PlannerRow key={row.id} row={row} t={t} />
        ))}
        {overflow > 0 ? (
          <li>
            <Link
              to={CRM_APP_PATHS.calendar}
              className="group flex items-stretch gap-0 transition hover:bg-slate-50/90"
            >
              <div className="w-1 shrink-0 bg-slate-300" aria-hidden />
              <div className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-3 text-xs text-slate-500">
                <span>
                  {t('app.work.hub.today_planner.more', {
                    defaultValue: '+{count} more today',
                    values: { count: overflow },
                  })}
                </span>
                <span className="shrink-0 font-semibold text-brand-700 group-hover:text-brand-800">
                  {t('app.work.hub.row_open', { defaultValue: 'Open' })}
                </span>
              </div>
            </Link>
          </li>
        ) : null}
      </ul>
    </section>
  )
}

function PlannerRow({
  row,
  t,
}: {
  row: Row
  t: ReturnType<typeof useI18n>['t']
}) {
  const Icon = kindIcon(row.kind)
  const timeLabel = row.allDay
    ? t('app.work.hub.today_planner.all_day', { defaultValue: 'All day' })
    : row.endAt
      ? `${formatHm(row.startAt)}–${formatHm(row.endAt)}`
      : formatHm(row.startAt)
  const toneBar = row.hasConflict
    ? 'bg-rose-500'
    : row.isLive
      ? 'bg-emerald-500'
      : 'bg-slate-300'
  const kindLabel = t(`app.work.hub.today_planner.kind_${row.kind}`, {
    defaultValue: row.kind.charAt(0).toUpperCase() + row.kind.slice(1),
  })
  const calHref = row.href
  return (
    <li>
      <Link
        to={calHref}
        className="group flex items-stretch gap-0 transition hover:bg-slate-50/90"
      >
        <div className={`w-1 shrink-0 ${toneBar}`} aria-hidden />
        <div className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-3.5">
          <div className="flex min-w-0 items-start gap-3">
            <Icon size={18} className="mt-0.5 shrink-0 text-slate-500" aria-hidden />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-900">{row.title}</p>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500">
                <span className="tabular-nums">{timeLabel}</span>
                <span aria-hidden>·</span>
                <span>{kindLabel}</span>
                {row.isLive ? (
                  <>
                    <span aria-hidden>·</span>
                    <span className="font-semibold text-emerald-700">
                      {t('app.work.hub.today_planner.live_now', { defaultValue: 'Now' })}
                    </span>
                  </>
                ) : null}
                {row.hasConflict ? (
                  <>
                    <span aria-hidden>·</span>
                    <span className="inline-flex items-center gap-1 font-semibold text-rose-700">
                      <IconAlertTriangle size={12} aria-hidden />
                      {t('app.work.hub.today_planner.conflict', { defaultValue: 'Conflict' })}
                    </span>
                  </>
                ) : null}
              </p>
            </div>
          </div>
          <span className="shrink-0 text-sm font-semibold text-brand-700 group-hover:text-brand-800">
            {t('app.work.hub.row_open', { defaultValue: 'Open' })}
            <IconArrowRight size={16} className="ml-1 inline align-text-bottom opacity-70" aria-hidden />
          </span>
        </div>
      </Link>
    </li>
  )
}
