import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowRight } from '@tabler/icons-react'

import { listReminders } from '../../api/client'
import type { ReminderRecord } from '../../api/types'
import { listCommunicationPlannerEvents, type CommunicationPlannerEvent } from '../../api/communications'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { EntityDeepLink } from '../../platform/EntityDeepLink'
import { buildEntityDeepLink } from '../../platform/entityDeepLinks'
import { useI18n } from '../../i18n'
import { useAuth } from '../../store/useAuth'

/**
 * G-6 Stage 2 — "My tasks" live preview on `/app/work`.
 *
 * The Work Hub was missing a surface answering the recruiter-level
 * question "what's on my plate today?". `/app/tasks` has this view
 * already, but it's a dedicated page and operators land on the hub
 * first. This panel is the bridge: a compact rollup of active
 * assignee-scoped reminders, bucketed as overdue / today / tomorrow.
 *
 * Scope decisions:
 *   - Always assignee-scoped (`assignee_scope=mine`), regardless of
 *     the role's `defaultCounterScope`. Team-scope ops numbers go
 *     into the "Needs attention" critical block; this panel is
 *     specifically "my plate" — mixing them here would erode the
 *     "what do _I_ do right now?" framing the hub is built on.
 *   - `due_to` is clamped to end-of-tomorrow-local so the fetch stays
 *     small even when a recruiter has hundreds of future reminders.
 *     Anything further out belongs in `/app/tasks`, not here.
 *   - No status filter on the API call (server-side `status_filter`
 *     accepts a multi-value list, but we also need to pick up rows
 *     with `status=overdue` which the backend auto-flips — easier to
 *     fetch everything in-range and gate client-side via
 *     `isClosedReminderStatus`, mirroring `RemindersPage`).
 *   - Deep-link goes to `/app/tasks?t_id=<id>` so `RemindersPage` can
 *     scroll the row into view via its existing focus-by-id handler.
 *
 * Data freshness: listens for `reminder-updated` window events (same
 * pump used by `CommunicationsCalendarPage` drag-and-drop + G-8 Next
 * Action badge bumpers) so completing/snoozing a task anywhere in
 * the app refreshes the hub preview without a hard reload.
 */

const DEFAULT_LIMIT = 50
const MAX_ROWS_PER_BUCKET = 3

type BucketKey = 'overdue' | 'today' | 'tomorrow'

function startOfDay(d: Date): Date {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}

function addDays(d: Date, days: number): Date {
  const x = new Date(d)
  x.setDate(x.getDate() + days)
  return x
}

function isClosedStatus(status?: string | null): boolean {
  const s = String(status || '').trim().toLowerCase()
  return s === 'done' || s === 'completed' || s === 'cancelled'
}

function bucketOf(due: Date, now: Date): BucketKey | null {
  const today = startOfDay(now)
  const tomorrow = addDays(today, 1)
  const dayAfterTomorrow = addDays(today, 2)
  if (due.getTime() < today.getTime()) return 'overdue'
  if (due.getTime() < tomorrow.getTime()) return 'today'
  if (due.getTime() < dayAfterTomorrow.getTime()) return 'tomorrow'
  return null
}

function formatDueTime(due: Date, bucket: BucketKey): string {
  const hh = String(due.getHours()).padStart(2, '0')
  const mm = String(due.getMinutes()).padStart(2, '0')
  if (bucket === 'overdue') {
    const now = new Date()
    const diffMs = now.getTime() - due.getTime()
    const minutes = Math.floor(diffMs / 60000)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }
  return `${hh}:${mm}`
}

type RowTone = 'rose' | 'amber' | 'slate'

const TONE_BAR: Record<RowTone, string> = {
  rose: 'bg-rose-500',
  amber: 'bg-amber-500',
  slate: 'bg-slate-400',
}

const BUCKET_TONE: Record<BucketKey, RowTone> = {
  overdue: 'rose',
  today: 'amber',
  tomorrow: 'slate',
}

type PreviewRow = {
  id: string
  title: string
  due: Date
  bucket: BucketKey
  entityLabel: string
  href: string
}

function reminderActionHref(r: ReminderRecord): string {
  const entityType = String(r.entity_type || '').trim().toLowerCase()
  const entityId = String(r.entity_id || '').trim()
  if (entityType && entityId) {
    const deep = buildEntityDeepLink(entityType, entityId, { query: { focus: 'tasks' } })
    if (deep) return deep
  }
  if (entityType === 'planner_event' && entityId) {
    return `${CRM_APP_PATHS.calendar}?event_id=${encodeURIComponent(entityId)}`
  }
  return `${CRM_APP_PATHS.tasks}?t_id=${encodeURIComponent(String(r.id))}`
}

function reminderRowFor(r: ReminderRecord, now: Date): PreviewRow | null {
  if (isClosedStatus(r.status)) return null
  const raw = r.due_at
  if (!raw) return null
  const due = new Date(raw)
  if (Number.isNaN(due.getTime())) return null
  const bucket = bucketOf(due, now)
  if (!bucket) return null
  const titleRaw = String(r.title || '').trim()
  const fallback = String(r.type || 'reminder').replace(/_/g, ' ')
  const title = titleRaw || fallback
  const entityLabel = r.entity_type ? String(r.entity_type).replace(/_/g, ' ') : ''
  return {
    id: String(r.id),
    title,
    due,
    bucket,
    entityLabel,
    href: reminderActionHref(r),
  }
}

function plannerTaskRowFor(ev: CommunicationPlannerEvent, now: Date): PreviewRow | null {
  const status = String(ev.status || '').trim().toLowerCase()
  if (status === 'done' || status === 'completed' || status === 'cancelled') return null
  const kind = String(ev.kind || '').trim().toLowerCase()
  if (!['task', 'followup', 'call'].includes(kind)) return null
  const due = new Date(ev.start_at)
  if (Number.isNaN(due.getTime())) return null
  const bucket = bucketOf(due, now)
  if (!bucket) return null
  const title = String(ev.title || '').trim() || (kind === 'followup' ? 'Follow-up' : 'Task')
  return {
    id: `planner:${String(ev.id)}`,
    title,
    due,
    bucket,
    entityLabel: 'planner',
    href: `${CRM_APP_PATHS.calendar}?event_id=${encodeURIComponent(String(ev.id))}`,
  }
}

export function MyTasksPanel() {
  const { t } = useI18n()
  const { me } = useAuth()
  const [rows, setRows] = useState<PreviewRow[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const now = new Date()
      const dueTo = addDays(startOfDay(now), 2)
      const [remindersData, plannerData] = await Promise.all([
        listReminders({
          assigneeScope: 'mine',
          dueTo: dueTo.toISOString(),
          limit: DEFAULT_LIMIT,
        }),
        listCommunicationPlannerEvents({
          assignee_id: String(me?.id || me?.sub || '').trim() || undefined,
          from_at: startOfDay(now).toISOString(),
          to_at: dueTo.toISOString(),
          limit: DEFAULT_LIMIT,
          include_completed_entities: true,
        }).catch(() => ({ items: [], total: 0 })),
      ])
      const items: ReminderRecord[] = Array.isArray(remindersData?.items)
        ? (remindersData.items as ReminderRecord[])
        : []
      const plannerItems: CommunicationPlannerEvent[] = Array.isArray(plannerData?.items)
        ? plannerData.items
        : []
      const reference = new Date()
      const mappedReminders = items
        .map((r) => reminderRowFor(r, reference))
        .filter((row): row is PreviewRow => row !== null)
      const mappedPlanner = plannerItems
        .map((r) => plannerTaskRowFor(r, reference))
        .filter((row): row is PreviewRow => row !== null)
      let merged = [...mappedReminders, ...mappedPlanner]
      if (merged.length === 0) {
        const [fallbackReminders, fallbackPlanner] = await Promise.all([
          listReminders({
            status: ['pending', 'new', 'overdue', 'sent'],
            dueTo: dueTo.toISOString(),
            limit: DEFAULT_LIMIT,
          }).catch(() => ({ items: [] })),
          listCommunicationPlannerEvents({
            from_at: startOfDay(now).toISOString(),
            to_at: dueTo.toISOString(),
            limit: DEFAULT_LIMIT,
            include_completed_entities: true,
          }).catch(() => ({ items: [], total: 0 })),
        ])
        const fallbackReminderRows = (Array.isArray(fallbackReminders?.items) ? fallbackReminders.items : [])
          .map((r) => reminderRowFor(r as ReminderRecord, reference))
          .filter((row): row is PreviewRow => row !== null)
        const fallbackPlannerRows = (Array.isArray(fallbackPlanner?.items) ? fallbackPlanner.items : [])
          .map((r) => plannerTaskRowFor(r as CommunicationPlannerEvent, reference))
          .filter((row): row is PreviewRow => row !== null)
        merged = [...fallbackReminderRows, ...fallbackPlannerRows]
      }
      setRows(merged)
    } catch {
      setRows(null)
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [me?.id, me?.sub])

  useEffect(() => {
    let cancelled = false
    void load().catch(() => {
      if (!cancelled) setError(true)
    })
    return () => {
      cancelled = true
    }
  }, [load])

  useEffect(() => {
    const handler = () => {
      void load()
    }
    window.addEventListener('reminder-updated', handler)
    return () => window.removeEventListener('reminder-updated', handler)
  }, [load])

  const buckets = useMemo(() => {
    const empty: Record<BucketKey, PreviewRow[]> = { overdue: [], today: [], tomorrow: [] }
    if (!rows) return empty
    const sorted = [...rows].sort((a, b) => a.due.getTime() - b.due.getTime())
    for (const row of sorted) empty[row.bucket].push(row)
    return empty
  }, [rows])

  const counts = useMemo(
    () => ({
      overdue: buckets.overdue.length,
      today: buckets.today.length,
      tomorrow: buckets.tomorrow.length,
    }),
    [buckets],
  )

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
            {t('app.work.hub.my_tasks.title', { defaultValue: 'My tasks' })}
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
          {t('app.work.hub.my_tasks.error', {
            defaultValue: 'Could not load your tasks. Try again.',
          })}
        </p>
      </section>
    )
  }

  const total = counts.overdue + counts.today + counts.tomorrow

  if (total === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.my_tasks.title', { defaultValue: 'My tasks' })}
          </h2>
          <Link
            to={CRM_APP_PATHS.tasks}
            className="inline-flex items-center text-sm font-semibold text-brand-700 hover:text-brand-800"
          >
            {t('app.work.hub.my_tasks.open_all', { defaultValue: 'Open all' })}
            <IconArrowRight size={16} className="ml-1 opacity-70" aria-hidden />
          </Link>
        </div>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.work.hub.my_tasks.empty', {
            defaultValue: 'Nothing scheduled for today or tomorrow. Good work.',
          })}
        </p>
      </section>
    )
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
        <div className="min-w-0">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.my_tasks.title', { defaultValue: 'My tasks' })}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('app.work.hub.my_tasks.counts', {
              defaultValue: '{overdue} overdue · {today} today · {tomorrow} tomorrow',
              values: counts,
            })}
          </p>
        </div>
        <Link
          to={CRM_APP_PATHS.tasks}
          className="inline-flex items-center text-sm font-semibold text-brand-700 hover:text-brand-800"
        >
          {t('app.work.hub.my_tasks.open_all', { defaultValue: 'Open all' })}
          <IconArrowRight size={16} className="ml-1 opacity-70" aria-hidden />
        </Link>
      </div>
      <ul className="divide-y divide-slate-100">
        {(['overdue', 'today', 'tomorrow'] as BucketKey[]).flatMap((bucket) => {
          const list = buckets[bucket]
          if (list.length === 0) return []
          const visible = list.slice(0, MAX_ROWS_PER_BUCKET)
          const overflow = list.length - visible.length
          const nodes = visible.map((row) => (
            <TaskRow key={row.id} row={row} t={t} />
          ))
          if (overflow > 0) {
            nodes.push(
              <OverflowRow
                key={`ovf-${bucket}`}
                bucket={bucket}
                count={overflow}
                t={t}
              />,
            )
          }
          return nodes
        })}
      </ul>
    </section>
  )
}

function TaskRow({
  row,
  t,
}: {
  row: PreviewRow
  t: ReturnType<typeof useI18n>['t']
}) {
  const timeLabel = formatDueTime(row.due, row.bucket)
  const tone = BUCKET_TONE[row.bucket]
  return (
    <li>
      <EntityDeepLink
        href={row.href}
        className="group flex items-stretch gap-0 transition hover:bg-slate-50/90"
      >
        <div className={`w-1 shrink-0 ${TONE_BAR[tone]}`} aria-hidden />
        <div className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-3.5">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">{row.title}</p>
            <p className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
              <span className="tabular-nums">{timeLabel}</span>
              {row.entityLabel ? (
                <>
                  <span aria-hidden>·</span>
                  <span className="truncate">{row.entityLabel}</span>
                </>
              ) : null}
            </p>
          </div>
          <span className="shrink-0 text-sm font-semibold text-brand-700 group-hover:text-brand-800">
            {t('app.work.hub.row_open', { defaultValue: 'Open' })}
            <IconArrowRight
              size={16}
              className="ml-1 inline align-text-bottom opacity-70"
              aria-hidden
            />
          </span>
        </div>
      </EntityDeepLink>
    </li>
  )
}

function OverflowRow({
  bucket,
  count,
  t,
}: {
  bucket: BucketKey
  count: number
  t: ReturnType<typeof useI18n>['t']
}) {
  const tone = BUCKET_TONE[bucket]
  const filter = bucket === 'overdue' ? 'overdue' : ''
  const href = filter
    ? `${CRM_APP_PATHS.tasks}?tab=tasks&filter=${filter}`
    : CRM_APP_PATHS.tasks
  return (
    <li>
      <Link
        to={href}
        className="group flex items-stretch gap-0 transition hover:bg-slate-50/90"
      >
        <div className={`w-1 shrink-0 ${TONE_BAR[tone]}`} aria-hidden />
        <div className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-3 text-xs text-slate-500">
          <span>
            {t('app.work.hub.my_tasks.more', {
              defaultValue: '+{count} more in this bucket',
              values: { count },
            })}
          </span>
          <span className="shrink-0 font-semibold text-brand-700 group-hover:text-brand-800">
            {t('app.work.hub.row_open', { defaultValue: 'Open' })}
          </span>
        </div>
      </Link>
    </li>
  )
}
