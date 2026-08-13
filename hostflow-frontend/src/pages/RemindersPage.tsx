import clsx from 'clsx'
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { format, formatDistanceToNow } from 'date-fns'
import { enUS, ru as ruLocale, pl as plLocale } from 'date-fns/locale'
import {
  completeReminder,
  createReminder,
  listNotifications,
  listReminders,
  markNotificationsRead,
  reconcileNotifications,
  snoozeReminder,
  updateReminder,
} from '../api/client'
import {
  listCommunicationPlannerEvents,
  patchCommunicationPlannerEvent,
  type CommunicationPlannerEvent,
} from '../api/communications'
import type {
  NotificationItem,
  NotificationListResponse,
  ReminderListResponse,
  ReminderRecord,
} from '../api/types'
import { getNotificationAttentionTier } from '../utils/notificationUos'
import { resolveNotificationOpenPath } from '../utils/resolveNotificationOpenPath'
import { useAuth } from '../store/useAuth'
import { canUseTeamAssigneeScope as teamAssigneeScopeAllowed } from '../auth/trustRoles'
import { usePermissions } from '../hooks/usePermissions'
import { useI18n } from '../i18n'
import { activateClickOnSpaceEnter, runActionOnSpaceEnter } from '../utils/a11yClick'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import EmptyStatePanel from '../components/EmptyStatePanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import ReminderExplainabilityPopover from '../components/explainability/ReminderExplainabilityPopover'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar, DataTableFrame } from '../components/layout'
import { buildInboxThreadPath } from '../utils/inboxDeepLinks'

const DATE_LOCALES = { en: enUS, ru: ruLocale, pl: plLocale }
const DEFAULT_REMIND_OFFSET = 15
const STORAGE_KEY = 'hf:inbox:reminders:v3'

type LoadState = 'idle' | 'loading' | 'error'
type InboxTab = 'tasks' | 'events'
type TaskStatusFilter = 'active' | 'all' | 'done'
type NotificationsScopeFilter = 'all' | 'direct'
type NotificationsReadFilter = 'unread' | 'all'
type AssigneeScopeFilter = 'mine' | 'team'
type TaskListMode = 'by_due' | 'sla_queue' | 'by_candidate' | 'by_task_type' | 'by_due_day'

type TaskFiltersState = {
  search: string
  status: TaskStatusFilter
  entityType: string
  priority: string
  /** When overdue: client-side filter to due bucket overdue (NBA / deep links). */
  dueBucket: '' | 'overdue'
  /** Show only rows that have no navigable entity link (operational data debt queue). */
  unlinkedOnly: boolean
  /** Show tasks for candidates in terminal stages (rejected/employed/etc) or soft-deleted. */
  includeCompletedEntities: boolean
}

type EventsFiltersState = {
  search: string
  scope: NotificationsScopeFilter
  read: NotificationsReadFilter
}

type PersistedInboxState = {
  activeTab: InboxTab
  taskFilters: TaskFiltersState
  eventsFilters: EventsFiltersState
  assigneeScope?: AssigneeScopeFilter
  taskListMode?: TaskListMode
}

/**
 * G-7 stage 2: tasks page now sources rows from BOTH tables:
 *   - reminders (default `_source: 'reminder'`)
 *   - communication_planner_events with `kind in (task, followup)`
 *     (`_source: 'planner'`)
 *
 * The row keeps the same `ReminderRecord & {derived}` shape because the
 * downstream consumers (filters, group buckets, SLA layout, edit modal,
 * `<ReminderExplainabilityPopover>`) all operate on it. Planner events
 * are projected onto that shape via `plannerEventToTaskRow`. The
 * underscore-prefixed `_source` flag is the discriminator used by:
 *   - row UI (badge "📅" for planner-source);
 *   - mutation handlers (complete / snooze / edit branch by source).
 *
 * Field semantics on a planner-derived row:
 *   - `id` keeps the planner UUID (no prefix; reminder/planner UUIDs are
 *     globally unique by separate primary keys, no collision possible).
 *   - `due_at` ← `start_at`. Reminders have no `end_at`; planner does,
 *     but we deliberately drop it here — the tasks page doesn't render
 *     duration. Edit/move handlers preserve original duration via the
 *     planner patch path.
 *   - `status` is mapped: `planned`/`in_progress` → `pending`,
 *     `done` → `done`, `cancelled` → `cancelled`. This keeps
 *     `isClosedReminderStatus` and the bucketing logic intact.
 *   - `type` ← `'planner_' + kind` so the explainability popover can
 *     surface the original kind. SLA fields stay null (planner events
 *     don't carry SLA today).
 */
type TaskRowSource = 'reminder' | 'planner'

type TaskRow = ReminderRecord & {
  dueDate: Date | null
  remindDate: Date | null
  dueTs: number
  remindTs: number
  slaDate: Date | null
  slaTs: number
  _source: TaskRowSource
  /** Original planner kind ('task' | 'followup') when `_source === 'planner'`. */
  _plannerKind?: string | null
}

/** Statuses on a planner event that should hide the row from the
 *  active-tasks list (mirrors `isClosedReminderStatus` for the reminder
 *  table). Keep in sync with `compute_thread_next_action`-style ladder
 *  thinking — `done` and `cancelled` mean "no operator action expected". */
const _PLANNER_TERMINAL_STATUSES = new Set(['done', 'cancelled'])

function mapPlannerStatusToReminderStatus(status: string | null | undefined): string {
  const s = String(status || '').trim().toLowerCase()
  if (s === 'done') return 'done'
  if (s === 'cancelled') return 'cancelled'
  // 'planned' and 'in_progress' both map to active. Reminder-side
  // `TASK_STATUS_COLORS` already has a `'pending'` colour entry.
  return 'pending'
}

/** Convert a planner event into the same shape the reminder rows use,
 *  so the existing filter/bucket/sort/render pipeline accepts it. Only
 *  fields actually present on `ReminderRecord` are populated; planner-
 *  specific fields (kind, end_at, all_day) ride on `_plannerKind` /
 *  `payload`. */
function plannerEventToTaskRow(event: CommunicationPlannerEvent): TaskRow {
  const dueDate = parseDate(event.start_at)
  const synthesized: ReminderRecord = {
    id: event.id,
    type: `planner_${event.kind || 'task'}`,
    entity_type: event.entity_type || 'planner',
    // ReminderRecord.entity_id is typed `string` (required). Empty
    // string is the safest fallback — `reminderEntityHref` already
    // guards on `!entityId` and returns null.
    entity_id: event.entity_id || '',
    title: event.title || null,
    description: event.description || null,
    owner_id: event.owner_id || null,
    assignee_id: event.assignee_id || null,
    priority: event.priority || 'normal',
    channel: null,
    status: mapPlannerStatusToReminderStatus(event.status) as ReminderRecord['status'],
    due_at: event.start_at,
    remind_at: null,
    snoozed_until: null,
    completed_at: null,
    recurrence_json: null,
    payload: event.payload || {},
    created_at: event.created_at,
    updated_at: event.updated_at,
    sla_due_at: null,
    sla_status: null,
  }
  return {
    ...synthesized,
    dueDate,
    remindDate: null,
    dueTs: dueDate?.getTime() || 0,
    remindTs: 0,
    slaDate: null,
    slaTs: 0,
    _source: 'planner',
    _plannerKind: event.kind || 'task',
  }
}

type EditState = {
  id: string
  title: string
  description: string
  dueAtLocal: string
  remindAtLocal: string
  priority: string
} | null

function isClosedReminderStatus(status?: string | null): boolean {
  const normalized = String(status || '').trim().toLowerCase()
  return normalized === 'done' || normalized === 'completed' || normalized === 'cancelled'
}

const DEFAULT_TASK_FILTERS: TaskFiltersState = {
  search: '',
  status: 'active',
  entityType: '',
  priority: '',
  dueBucket: '',
  unlinkedOnly: false,
  includeCompletedEntities: false,
}

const DEFAULT_EVENTS_FILTERS: EventsFiltersState = {
  search: '',
  scope: 'all',
  read: 'unread',
}

const TASK_STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  new: 'bg-amber-100 text-amber-800',
  overdue: 'bg-rose-100 text-rose-700',
  done: 'bg-emerald-100 text-emerald-700',
  sent: 'bg-blue-100 text-blue-700',
  cancelled: 'bg-slate-200 text-slate-600',
}

const PRIORITY_COLORS: Record<string, string> = {
  high: 'bg-rose-100 text-rose-700',
  urgent: 'bg-rose-100 text-rose-700',
  normal: 'bg-slate-100 text-slate-700',
  low: 'bg-slate-100 text-slate-600',
}

function getDefaultDueAtLocal(): string {
  const dt = new Date(Date.now() + 60 * 60 * 1000)
  return toLocalInputValue(dt)
}

function normalizeText(value: string | null | undefined): string {
  return (value || '').trim().toLowerCase()
}

function parseDate(value?: string | null): Date | null {
  if (!value) return null
  const d = new Date(value)
  return Number.isFinite(d.getTime()) ? d : null
}

function toLocalInputValue(date: Date | null): string {
  if (!date) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function reminderEntityHref(item: ReminderRecord): string | null {
  const entityId = String(item.entity_id || '')
  if (!entityId) return null
  switch (item.entity_type) {
    case 'candidate':
      return `${CRM_APP_PATHS.candidates}/${entityId}`
    case 'vacancy':
      return `${CRM_APP_PATHS.vacancies}/${entityId}`
    case 'lead':
      return entityId ? `${CRM_APP_PATHS.leads}/${entityId}` : CRM_APP_PATHS.leads
    case 'company':
      return `${CRM_APP_PATHS.agencyClients}/${entityId}`
    case 'communication_thread':
      return buildInboxThreadPath(entityId)
    default:
      return null
  }
}

function pickPayloadString(payload: Record<string, unknown> | null | undefined, keys: string[]): string | null {
  if (!payload || typeof payload !== 'object') return null
  for (const k of keys) {
    const v = payload[k]
    if (v == null) continue
    const s = String(v).trim()
    if (s) return s
  }
  return null
}

/** Best-effort display name for the linked CRM entity (from reminder / planner payload). */
function linkedEntityDisplayName(item: ReminderRecord): string | null {
  return pickPayloadString(item.payload as Record<string, unknown>, [
    'candidate_name',
    'candidate_full_name',
    'display_name',
    'entity_display_name',
    'entity_name',
    'company_name',
    'vacancy_title',
    'vacancy_name',
    'lead_title',
    'thread_subject',
    'subject',
  ])
}

function normalizeTaskListMode(value: unknown): TaskListMode | null {
  if (value === 'by_due' || value === 'sla_queue' || value === 'by_candidate' || value === 'by_task_type' || value === 'by_due_day') {
    return value
  }
  return null
}

function dueDaySectionKey(item: TaskRow): string {
  if (isClosedReminderStatus(item.status)) return 'done'
  if (!item.dueDate) return 'unscheduled'
  const now = new Date()
  const today = startOfDay(now)
  const dueDay = startOfDay(item.dueDate)
  if (item.status === 'overdue' || dueDay.getTime() < today.getTime()) return 'overdue'
  const y = dueDay.getFullYear()
  const mo = String(dueDay.getMonth() + 1).padStart(2, '0')
  const da = String(dueDay.getDate()).padStart(2, '0')
  return `day:${y}-${mo}-${da}`
}

function parseCalendarDayKey(key: string): Date | null {
  if (!key.startsWith('day:')) return null
  const s = key.slice(4).trim()
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s)
  if (!m) return null
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return Number.isFinite(d.getTime()) ? d : null
}

function sortDueDaySectionKeys(keys: string[]): string[] {
  const uniq = [...new Set(keys)]
  const dayKeys = uniq
    .filter((k) => k.startsWith('day:'))
    .sort((a, b) => {
      const da = parseCalendarDayKey(a)?.getTime() ?? 0
      const db = parseCalendarDayKey(b)?.getTime() ?? 0
      return da - db
    })
  const pick = (k: string) => (uniq.includes(k) ? [k] : [])
  return [...pick('overdue'), ...dayKeys, ...pick('unscheduled'), ...pick('done')]
}

function sortTaskRowsMixedOpenFirst(rows: TaskRow[]): TaskRow[] {
  const copy = [...rows]
  copy.sort((a, b) => {
    const ac = isClosedReminderStatus(a.status)
    const bc = isClosedReminderStatus(b.status)
    if (ac !== bc) return ac ? 1 : -1
    if (!ac) return compareOpenTasksBySlaThenDue(a, b)
    return compareDoneTasksByUpdated(a, b)
  })
  return copy
}

type TaskSection = {
  key: string
  label: string
  headerHref?: string | null
  items: TaskRow[]
}

function notificationEntityHref(item: NotificationItem): string | null {
  return resolveNotificationOpenPath(item, { canInboxDeepLink: true })
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

function startOfDay(date: Date): Date {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return d
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

/** Lower = more urgent for open tasks (UOS: SLA drives queue pressure). */
function slaTierRank(status?: string | null): number {
  const s = String(status || '').trim().toLowerCase()
  if (s === 'overdue') return 0
  if (s === 'at_risk') return 1
  if (s === 'on_track') return 2
  if (s === 'resolved') return 3
  return 4
}

function compareOpenTasksBySlaThenDue(a: TaskRow, b: TaskRow): number {
  const tra = slaTierRank(a.sla_status)
  const trb = slaTierRank(b.sla_status)
  if (tra !== trb) return tra - trb
  const slaA = a.slaTs > 0 ? a.slaTs : Number.MAX_SAFE_INTEGER
  const slaB = b.slaTs > 0 ? b.slaTs : Number.MAX_SAFE_INTEGER
  if (slaA !== slaB) return slaA - slaB
  const dueA = a.dueTs || a.remindTs || 0
  const dueB = b.dueTs || b.remindTs || 0
  if (dueA !== dueB) return dueA - dueB
  return (a.title || '').localeCompare(b.title || '')
}

function compareDoneTasksByUpdated(a: TaskRow, b: TaskRow): number {
  const ua = a.updated_at ? Date.parse(a.updated_at) : 0
  const ub = b.updated_at ? Date.parse(b.updated_at) : 0
  if (ua !== ub) return ub - ua
  return (a.title || '').localeCompare(b.title || '')
}

function taskRelatedCaption(item: ReminderRecord, t: (key: string, options?: Record<string, unknown>) => string): string {
  const named = linkedEntityDisplayName(item)
  if (named) return named
  const et = String(item.entity_type || '').trim().toLowerCase() || 'unknown'
  const id = String(item.entity_id || '').trim()
  const shortId = id.length > 14 ? `${id.slice(0, 12)}…` : id
  const etKey = `app.reminders.entity_types.${et}`
  const typeLabel = t(etKey, { defaultValue: et })
  if (et === 'candidate' && id) {
    return t('app.reminders.row.candidate_without_name', { defaultValue: 'Candidate ({id})', values: { id: shortId } })
  }
  if (id) {
    return t('app.reminders.row.entity_stub', { defaultValue: '{type} · {id}', values: { type: typeLabel, id: shortId } })
  }
  return t('app.reminders.row.unlinked_entity', { defaultValue: 'Not linked to a record' })
}

type ReminderTaskRowProps = {
  item: TaskRow
  t: (key: string, options?: Record<string, unknown>) => string
  reminderStatusLabel: (status?: string | null) => string
  formatTs: (date: Date | null) => string
  formatRelative: (date: Date | null) => string
  taskBusyId: string | null
  editBusy: boolean
  highlighted?: boolean
  selected?: boolean
  onToggleSelect?: (id: string, next: boolean) => void
  onEdit: (item: TaskRow) => void
  onSnooze: (id: string, minutes: number) => void
  onComplete: (id: string) => void
}

function ReminderTaskRow({
  item,
  t,
  reminderStatusLabel,
  formatTs,
  formatRelative,
  taskBusyId,
  editBusy,
  highlighted,
  selected,
  onToggleSelect,
  onEdit,
  onSnooze,
  onComplete,
}: ReminderTaskRowProps) {
  const href = reminderEntityHref(item)
  const etRaw = String(item.entity_type || 'unknown').trim() || 'unknown'
  const entityTypeLabel = t(`app.reminders.entity_types.${etRaw}`, { defaultValue: item.entity_type || '—' })
  const busy = taskBusyId === item.id
  const statusPill = TASK_STATUS_COLORS[item.status] || 'bg-slate-100 text-slate-700'
  const priorityPill = PRIORITY_COLORS[item.priority || 'normal'] || PRIORITY_COLORS.normal
  const slaSt = String(item.sla_status || '').toLowerCase()
  const slaPill =
    slaSt === 'overdue'
      ? 'bg-rose-100 text-rose-800'
      : slaSt === 'at_risk'
        ? 'bg-amber-100 text-amber-900'
        : slaSt === 'on_track'
          ? 'bg-emerald-50 text-emerald-800'
          : slaSt === 'resolved'
            ? 'bg-slate-100 text-slate-600'
            : ''
  return (
    <div
      id={`task-row-${item.id}`}
      className={clsx(
        'rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-shadow',
        highlighted && 'ring-2 ring-brand-500 ring-offset-2',
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        {onToggleSelect && (
          <label
            className="mt-1 inline-flex items-center"
            htmlFor={`hf-reminder-select-${item.id}`}
            aria-label={t('app.reminders.bulk.select_one', { defaultValue: 'Select reminder' })}
          >
            <input
              id={`hf-reminder-select-${item.id}`}
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              checked={Boolean(selected)}
              onChange={(e) => onToggleSelect(item.id, e.target.checked)}
            />
          </label>
        )}
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={clsx('rounded-lg px-3 py-1 text-[11px] font-semibold', statusPill)}>
              {reminderStatusLabel(item.status)}
            </span>
            <span className={clsx('rounded-lg px-2 py-0.5 text-[11px] font-medium', priorityPill)}>
              {t(`app.reminders.priority.${item.priority || 'normal'}`, { defaultValue: item.priority || 'normal' })}
            </span>
            <span className="rounded-lg bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{entityTypeLabel}</span>
            {item._source === 'planner' && (
              // G-7 stage 2: small visual differentiator for planner-derived
              // rows. Operators need to know this row mutates the planner
              // table (so it'll also appear on the calendar) — without the
              // badge it would feel like a phantom row.
              <span
                className="rounded-lg bg-blue-100 px-2 py-0.5 text-[11px] font-medium text-blue-700"
                title={t('app.reminders.source.planner_hint', {
                  defaultValue: 'From Calendar planner ({kind})',
                  values: { kind: item._plannerKind || 'task' },
                })}
              >
                {t('app.reminders.source.planner_label', { defaultValue: 'Calendar' })}
              </span>
            )}
            {item.sla_due_at && item.sla_status && slaPill && (
              <span className={clsx('rounded-lg px-2 py-0.5 text-[11px] font-semibold', slaPill)} title={formatTs(item.slaDate)}>
                {t(`app.reminders.sla.status.${slaSt}`, { defaultValue: item.sla_status })} · {formatTs(item.slaDate)}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="truncate text-sm font-semibold text-slate-900">
              {item.title || t('app.candidate_card.reminders.untitled')}
            </h4>
            <ReminderExplainabilityPopover reminder={item} entityHref={href} />
          </div>
          {href ? (
            <div className="text-xs text-slate-600">
              <span className="font-medium text-slate-500">{t('app.reminders.row.related', { defaultValue: 'Related' })}: </span>
              <Link to={href} className="font-medium text-brand-700 hover:underline">
                {taskRelatedCaption(item, t)}
              </Link>
            </div>
          ) : null}
          {item.description && <p className="text-xs text-slate-600 whitespace-pre-wrap">{item.description}</p>}
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
            <span>
              {t('app.candidate_card.reminders.due')}: {formatTs(item.dueDate)}
            </span>
            <span>
              {t('app.candidate_card.reminders.remind')}: {formatTs(item.remindDate)}
            </span>
            <span>
              {t('app.reminders.relative')}: {formatRelative(item.remindDate || item.dueDate)}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-secondary btn-xs" onClick={() => onEdit(item)} disabled={busy || editBusy}>
            {t('common.actions.edit')}
          </button>
          <button
            type="button"
            className="btn-secondary btn-xs"
            onClick={() => onSnooze(item.id, 15)}
            disabled={busy || isClosedReminderStatus(item.status)}
          >
            +15m
          </button>
          <button
            type="button"
            className="btn-secondary btn-xs"
            onClick={() => onSnooze(item.id, 60)}
            disabled={busy || isClosedReminderStatus(item.status)}
          >
            +1h
          </button>
          {!isClosedReminderStatus(item.status) && (
            <button type="button" className="btn-primary btn-xs" onClick={() => onComplete(item.id)} disabled={busy}>
              {busy ? t('common.loading') : t('app.candidate_card.reminders.complete')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function bucketReminderByDue(item: TaskRow): 'overdue' | 'today' | 'tomorrow' | 'week' | 'later' | 'done' | 'unscheduled' {
  if (isClosedReminderStatus(item.status)) return 'done'
  if (!item.dueDate) return 'unscheduled'

  const now = new Date()
  const today = startOfDay(now)
  const tomorrow = addDays(today, 1)
  const week = addDays(today, 7)
  const dueDay = startOfDay(item.dueDate)

  if (item.status === 'overdue' || dueDay.getTime() < today.getTime()) return 'overdue'
  if (sameDay(dueDay, today)) return 'today'
  if (sameDay(dueDay, tomorrow)) return 'tomorrow'
  if (dueDay.getTime() <= week.getTime()) return 'week'
  return 'later'
}

function notificationRank(item: NotificationItem): number {
  if (item.is_read) return 0
  const payload = (item.payload || {}) as Record<string, any>
  const eventType = String(item.event_type || '').toLowerCase()
  const severity = String(payload.severity || '').toLowerCase()
  const requiresAction = Boolean(payload.requires_action)
  const tier = getNotificationAttentionTier(item)
  let score = 0
  if (tier === 'critical') score += 120
  else if (tier === 'high') score += 60
  if (requiresAction) score += 100
  if (eventType === 'communications_sla_overdue') score += 90
  if (severity === 'high') score += 40
  else if (severity === 'medium') score += 20
  else if (severity === 'low') score += 5
  return score
}

export default function RemindersPage() {
  const { t, locale } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const focusTaskIdFromUrl = (searchParams.get('t_id') || '').trim() || null
  const [highlightTaskId, setHighlightTaskId] = useState<string | null>(null)
  const { me } = useAuth()
  const { rawRole, presetId } = usePermissions()
  const canUseTeamAssigneeScope = useMemo(() => {
    return teamAssigneeScopeAllowed({ role: rawRole || me?.role, presetId })
  }, [me?.role, presetId, rawRole])
  const dateLocale = DATE_LOCALES[locale as keyof typeof DATE_LOCALES] || enUS
  const tenantId = (me as any)?.tenant_id || 'default'
  const storageKey = `${STORAGE_KEY}:${tenantId}`

  const [hydrated, setHydrated] = useState(false)
  const [activeTab, setActiveTab] = useState<InboxTab>('tasks')
  const [taskFilters, setTaskFilters] = useState<TaskFiltersState>(DEFAULT_TASK_FILTERS)
  const [eventsFilters, setEventsFilters] = useState<EventsFiltersState>(DEFAULT_EVENTS_FILTERS)
  const [assigneeScope, setAssigneeScope] = useState<AssigneeScopeFilter>('mine')
  /** Default: group by due date; SLA flat queue is opt-in (persisted). */
  const [taskListMode, setTaskListMode] = useState<TaskListMode>('by_due')

  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [remindersState, setRemindersState] = useState<LoadState>('idle')
  const [remindersError, setRemindersError] = useState<FriendlyErrorInfo | null>(null)
  // G-7 stage 2: planner-task rows (kind ∈ {task, followup}) are merged
  // into the same list as reminders. Stored separately so the
  // independent loaders can refresh them without touching reminders.
  const [plannerTaskEvents, setPlannerTaskEvents] = useState<CommunicationPlannerEvent[]>([])
  const [taskBusyId, setTaskBusyId] = useState<string | null>(null)
  const [copiedSectionKey, setCopiedSectionKey] = useState<string | null>(null)
  const [bulkBusy, setBulkBusy] = useState(false)
  const [selectedTaskIds, setSelectedTaskIds] = useState<string[]>([])
  const [bulkRescheduleLocal, setBulkRescheduleLocal] = useState('')
  const [bulkAssigneeId, setBulkAssigneeId] = useState('')

  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [notificationsState, setNotificationsState] = useState<LoadState>('idle')
  const [notificationsError, setNotificationsError] = useState<FriendlyErrorInfo | null>(null)
  const [notifBusyId, setNotifBusyId] = useState<string | null>(null)
  const [markAllBusy, setMarkAllBusy] = useState(false)

  const [formTitle, setFormTitle] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formDueAt, setFormDueAt] = useState<string>(() => getDefaultDueAtLocal())
  const [remindOffset, setRemindOffset] = useState<number>(DEFAULT_REMIND_OFFSET)
  const [formPriority, setFormPriority] = useState<string>('normal')
  const [composerOpen, setComposerOpen] = useState(false)
  const [createBusy, setCreateBusy] = useState(false)

  const [editState, setEditState] = useState<EditState>(null)
  const [editBusy, setEditBusy] = useState(false)

  const openQuickReminderComposer = useCallback(() => {
    setComposerOpen(true)
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [])

  const parseTaskStatus = (value: string | null): TaskStatusFilter | null =>
    value === 'active' || value === 'all' || value === 'done' ? value : null
  const parseInboxTab = (value: string | null): InboxTab | null =>
    value === 'tasks' || value === 'events' ? value : null
  const parseNotifScope = (value: string | null): NotificationsScopeFilter | null =>
    value === 'all' || value === 'direct' ? value : null
  const parseNotifRead = (value: string | null): NotificationsReadFilter | null =>
    value === 'unread' || value === 'all' ? value : null
  const parseAssigneeScope = (value: string | null): AssigneeScopeFilter | null =>
    value === 'mine' || value === 'team' ? value : null
  const parseTaskListMode = (value: string | null): TaskListMode | null => normalizeTaskListMode(value)

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey)
      if (!raw) {
        setHydrated(true)
        return
      }
      const parsed = JSON.parse(raw) as PersistedInboxState
      if (parsed?.activeTab) setActiveTab(parsed.activeTab)
      if (parsed?.taskFilters) setTaskFilters({ ...DEFAULT_TASK_FILTERS, ...parsed.taskFilters })
      if (parsed?.eventsFilters) setEventsFilters({ ...DEFAULT_EVENTS_FILTERS, ...parsed.eventsFilters })
      if (parsed?.assigneeScope === 'mine' || parsed?.assigneeScope === 'team') setAssigneeScope(parsed.assigneeScope)
      if (parsed?.taskListMode) {
        const m = normalizeTaskListMode(parsed.taskListMode)
        if (m) setTaskListMode(m)
      } else if (raw) {
        setTaskListMode('by_due')
      }
    } catch {
      // ignore malformed storage
    }

    try {
      const urlTab = parseInboxTab(searchParams.get('tab'))
      const tStatus = parseTaskStatus(searchParams.get('t_status'))
      const tQ = searchParams.get('t_q')
      const tEntity = searchParams.get('t_entity')
      const tDueBucket = searchParams.get('t_due_bucket')
      const tUnlinked = searchParams.get('t_unlinked')
      const filterLegacy = (searchParams.get('filter') || '').trim().toLowerCase()
      const tPriority = searchParams.get('t_priority')
      const eScope = parseNotifScope(searchParams.get('e_scope'))
      const eRead = parseNotifRead(searchParams.get('e_read'))
      const eQ = searchParams.get('e_q')
      const tAssignee = parseAssigneeScope(searchParams.get('t_assignee'))
      const tLayout = parseTaskListMode(searchParams.get('t_layout'))

      if (urlTab) setActiveTab(urlTab)
      if (
        tStatus ||
        tQ != null ||
        tEntity != null ||
        tPriority != null ||
        tDueBucket === 'overdue' ||
        tUnlinked === '1' ||
        filterLegacy === 'overdue'
      ) {
        setTaskFilters((prev) => ({
          ...prev,
          ...(tStatus ? { status: tStatus } : {}),
          ...(tQ != null ? { search: tQ } : {}),
          ...(tEntity != null ? { entityType: tEntity } : {}),
          ...(tPriority != null ? { priority: tPriority } : {}),
          ...(tDueBucket === 'overdue' || filterLegacy === 'overdue' ? { dueBucket: 'overdue' as const } : {}),
          ...(tUnlinked === '1' ? { unlinkedOnly: true } : {}),
        }))
      }
      if (filterLegacy === 'overdue') {
        setActiveTab('tasks')
      }
      if (eScope || eRead || eQ != null) {
        setEventsFilters((prev) => ({
          ...prev,
          ...(eScope ? { scope: eScope } : {}),
          ...(eRead ? { read: eRead } : {}),
          ...(eQ != null ? { search: eQ } : {}),
        }))
      }
      if (tAssignee) setAssigneeScope(tAssignee)
      if (tLayout) setTaskListMode(tLayout)

      const legacyTaskType = (searchParams.get('type') || '').trim().toLowerCase()
      if (legacyTaskType === 'leads_no_next_action' && !searchParams.get('t_entity')) {
        setActiveTab('tasks')
        setTaskFilters((prev) => ({
          ...prev,
          entityType: 'lead',
          status: 'active',
        }))
      }
    } catch {
      // ignore malformed URL state
    } finally {
      setHydrated(true)
    }
  }, [searchParams, storageKey])

  useEffect(() => {
    if (!hydrated) return
    try {
      const payload: PersistedInboxState = {
        activeTab,
        taskFilters,
        eventsFilters,
        assigneeScope,
        taskListMode,
      }
      localStorage.setItem(storageKey, JSON.stringify(payload))
    } catch {
      // ignore storage errors
    }
  }, [activeTab, assigneeScope, taskFilters, eventsFilters, hydrated, storageKey, taskListMode])

  useEffect(() => {
    if (!hydrated) return
    const next = new URLSearchParams(searchParams)
    next.delete('type')

    next.set('tab', activeTab)

    if (taskFilters.status !== DEFAULT_TASK_FILTERS.status) next.set('t_status', taskFilters.status)
    else next.delete('t_status')
    if (taskFilters.search.trim()) next.set('t_q', taskFilters.search.trim())
    else next.delete('t_q')
    if (taskFilters.entityType) next.set('t_entity', taskFilters.entityType)
    else next.delete('t_entity')
    if (taskFilters.dueBucket === 'overdue') next.set('t_due_bucket', 'overdue')
    else next.delete('t_due_bucket')
    if (taskFilters.unlinkedOnly) next.set('t_unlinked', '1')
    else next.delete('t_unlinked')
    if (taskFilters.priority) next.set('t_priority', taskFilters.priority)
    else next.delete('t_priority')
    if (assigneeScope !== 'mine') next.set('t_assignee', assigneeScope)
    else next.delete('t_assignee')
    if (taskListMode !== 'by_due') next.set('t_layout', taskListMode)
    else next.delete('t_layout')

    if (eventsFilters.scope !== DEFAULT_EVENTS_FILTERS.scope) next.set('e_scope', eventsFilters.scope)
    else next.delete('e_scope')
    if (eventsFilters.read !== DEFAULT_EVENTS_FILTERS.read) next.set('e_read', eventsFilters.read)
    else next.delete('e_read')
    if (eventsFilters.search.trim()) next.set('e_q', eventsFilters.search.trim())
    else next.delete('e_q')

    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true })
    }
  }, [activeTab, assigneeScope, eventsFilters, hydrated, searchParams, setSearchParams, taskFilters, taskListMode])

  const reminderRows = useMemo<TaskRow[]>(() => {
    // G-7 stage 2: merge reminders + planner-task events into one
    // unified `TaskRow[]` stream. Reminders carry implicit
    // `_source: 'reminder'`; planner events go through
    // `plannerEventToTaskRow` which sets `_source: 'planner'`.
    const reminderRowList: TaskRow[] = reminders.map((item) => {
      const dueDate = parseDate(item.due_at)
      const remindDate = parseDate(item.snoozed_until || item.remind_at)
      const slaDate = parseDate(item.sla_due_at)
      return {
        ...item,
        dueDate,
        remindDate,
        dueTs: dueDate?.getTime() || 0,
        remindTs: remindDate?.getTime() || 0,
        slaDate,
        slaTs: slaDate?.getTime() || 0,
        _source: 'reminder',
      }
    })
    // Filter planner events by the active status filter on the page.
    // The reminder list endpoint already applies a server-side status
    // filter, but planner events come back unfiltered — apply the
    // equivalent status filter client-side so the two sources behave
    // consistently for the user.
    const statusGate = (row: TaskRow): boolean => {
      if (focusTaskIdFromUrl) return true
      if (taskFilters.status === 'active') return !isClosedReminderStatus(row.status)
      if (taskFilters.status === 'done') return isClosedReminderStatus(row.status)
      return true
    }
    const plannerRowList = plannerTaskEvents.map(plannerEventToTaskRow).filter(statusGate)
    return [...reminderRowList, ...plannerRowList]
  }, [reminders, plannerTaskEvents, focusTaskIdFromUrl, taskFilters.status])

  const filteredReminderRows = useMemo(() => {
    const q = normalizeText(taskFilters.search)
    return reminderRows.filter((item) => {
      if (focusTaskIdFromUrl && String(item.id) === focusTaskIdFromUrl) return true
      if (taskFilters.entityType && item.entity_type !== taskFilters.entityType) return false
      if (taskFilters.priority && (item.priority || '') !== taskFilters.priority) return false
      if (taskFilters.dueBucket === 'overdue' && bucketReminderByDue(item) !== 'overdue') return false
      if (taskFilters.unlinkedOnly && reminderEntityHref(item) != null) return false
      if (!q) return true
      const hay = [
        item.title,
        item.description,
        item.entity_type,
        item.entity_id,
        JSON.stringify(item.payload || {}),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return hay.includes(q)
    })
  }, [
    focusTaskIdFromUrl,
    reminderRows,
    taskFilters.dueBucket,
    taskFilters.entityType,
    taskFilters.unlinkedOnly,
    taskFilters.priority,
    taskFilters.search,
  ])

  useEffect(() => {
    if (!focusTaskIdFromUrl) return
    if (activeTab !== 'tasks') {
      setActiveTab('tasks')
      return
    }
    if (remindersState !== 'idle') return
    const target = reminderRows.find((r) => String(r.id) === focusTaskIdFromUrl)
    if (target && isClosedReminderStatus(target.status) && taskFilters.status === 'active') {
      setTaskFilters((p) => ({ ...p, status: 'all' }))
      return
    }
    let cancelled = false
    const raf = window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        if (cancelled) return
        const el = document.getElementById(`task-row-${focusTaskIdFromUrl}`)
        const stripFocusParam = () => {
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev)
            if (!next.has('t_id')) return prev
            next.delete('t_id')
            return next
          }, { replace: true })
        }
        if (!el) {
          stripFocusParam()
          return
        }
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        setHighlightTaskId(focusTaskIdFromUrl)
        stripFocusParam()
      })
    })
    return () => {
      cancelled = true
      cancelAnimationFrame(raf)
    }
  }, [
    activeTab,
    focusTaskIdFromUrl,
    reminderRows,
    remindersState,
    filteredReminderRows.length,
    setSearchParams,
    taskFilters.status,
  ])

  useEffect(() => {
    if (!highlightTaskId) return
    const timer = window.setTimeout(() => setHighlightTaskId(null), 3500)
    return () => clearTimeout(timer)
  }, [highlightTaskId])

  useEffect(() => {
    if (!canUseTeamAssigneeScope && assigneeScope === 'team') setAssigneeScope('mine')
  }, [assigneeScope, canUseTeamAssigneeScope])

  const loadReminders = useCallback(async () => {
    setRemindersState('loading')
    setRemindersError(null)
    try {
      const statusList =
        focusTaskIdFromUrl
          ? undefined
          : taskFilters.status === 'active'
            ? ['pending', 'new', 'overdue', 'sent']
            : taskFilters.status === 'done'
              ? ['done', 'cancelled']
              : undefined
      const scope = canUseTeamAssigneeScope ? assigneeScope : 'mine'
      // G-7 stage 2: parallelize reminder + planner-task fetches. The
      // planner endpoint's `kind` filter is single-valued, so we fetch
      // ALL planner events for the assignee scope (limit 200, plenty
      // for an operator-facing tasks page) and filter to
      // `kind ∈ {task, followup}` client-side. Two separate kind=task
      // / kind=followup calls would also work but double the round-trip
      // cost without much benefit.
      const plannerAssigneeId = scope === 'mine' && me?.id ? String(me.id) : undefined
      const [remindersData, plannerData] = await Promise.all([
        listReminders({
          status: statusList,
          assigneeScope: scope,
          includeCompletedEntities: taskFilters.includeCompletedEntities,
        }) as Promise<ReminderListResponse>,
        // Failure on planner side must NOT break reminders — wrap in a
        // try/catch via Promise.allSettled-style fallback below.
        listCommunicationPlannerEvents({
          limit: 200,
          assignee_id: plannerAssigneeId,
          include_completed_entities: taskFilters.includeCompletedEntities,
        }).catch((err) => {
          // Quiet fallback — planner events are an additive surface on
          // this page; if the planner endpoint fails we still want the
          // reminders list to render. Log for diagnostics.
          // eslint-disable-next-line no-console
          console.warn('[RemindersPage] planner events fetch failed; rendering reminders only', err)
          return { items: [] as CommunicationPlannerEvent[], total: 0 }
        }),
      ])
      setReminders(Array.isArray(remindersData?.items) ? remindersData.items : [])
      const plannerItems = Array.isArray((plannerData as any)?.items)
        ? ((plannerData as any).items as CommunicationPlannerEvent[])
        : []
      // Spec G-7: only `task` and `followup` kinds belong on the tasks
      // page. `meeting` / `call` / `shift` stay calendar-only.
      const tasksAndFollowups = plannerItems.filter((evt) => {
        const kind = String(evt.kind || '').trim().toLowerCase()
        return kind === 'task' || kind === 'followup'
      })
      setPlannerTaskEvents(tasksAndFollowups)
      setRemindersState('idle')
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.load'))) {
        setRemindersState('idle')
        return
      }
      setRemindersState('error')
      setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.load'), t))
    }
  }, [
    assigneeScope,
    canUseTeamAssigneeScope,
    focusTaskIdFromUrl,
    me?.id,
    planLimitModal,
    t,
    taskFilters.includeCompletedEntities,
    taskFilters.status,
  ])

  const loadNotificationsFeed = useCallback(async () => {
    setNotificationsState('loading')
    setNotificationsError(null)
    try {
      try {
        await reconcileNotifications()
      } catch {
        // ignore reconcile errors; normal loading still works
      }
      const data = (await listNotifications({
        limit: 100,
        includeRead: eventsFilters.read === 'all',
        scope: eventsFilters.scope,
        includeCompletedEntities: taskFilters.includeCompletedEntities,
      })) as NotificationListResponse
      setNotifications(Array.isArray(data?.items) ? data.items : [])
      setNotificationsState('idle')
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.notifications_load'))) {
        setNotificationsState('idle')
        return
      }
      setNotificationsState('error')
      setNotificationsError(getFriendlyErrorInfo(err, t('app.reminders.errors.notifications_load'), t))
    }
  }, [eventsFilters.read, eventsFilters.scope, planLimitModal, t, taskFilters.includeCompletedEntities])

  const reconcileAndReloadNotificationsFeed = useCallback(async () => {
    setNotificationsState('loading')
    setNotificationsError(null)
    try {
      await reconcileNotifications()
      const data = (await listNotifications({
        limit: 100,
        includeRead: eventsFilters.read === 'all',
        scope: eventsFilters.scope,
        includeCompletedEntities: taskFilters.includeCompletedEntities,
      })) as NotificationListResponse
      setNotifications(Array.isArray(data?.items) ? data.items : [])
      setNotificationsState('idle')
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.notifications_load'))) {
        setNotificationsState('idle')
        return
      }
      setNotificationsState('error')
      setNotificationsError(getFriendlyErrorInfo(err, t('app.reminders.errors.notifications_load'), t))
    }
  }, [eventsFilters.read, eventsFilters.scope, planLimitModal, t, taskFilters.includeCompletedEntities])

  useEffect(() => {
    void loadReminders()
  }, [loadReminders])

  useEffect(() => {
    if (activeTab !== 'events') return
    void loadNotificationsFeed()
  }, [activeTab, loadNotificationsFeed])

  const reminderStatusLabel = useCallback(
    (status?: string | null) => {
      const key = status ? `app.candidate_card.reminders.statuses.${String(status).toLowerCase()}` : 'app.candidate_card.reminders.statuses.pending'
      return t(key, { defaultValue: status || '—' })
    },
    [t]
  )

  const notificationTitle = useCallback(
    (item: NotificationItem) => {
      if (item.event_type === 'handoff_requested') {
        return t('app.notifications.handoff_requested_title')
      }
      const et = String(item.event_type || '').trim().toLowerCase()
      if (et === 'lead_public_intake_client') {
        return t('app.notifications.lead_public_intake_client_title')
      }
      if (et === 'intake_client_lead_skipped_no_company') {
        return t('app.notifications.intake_client_lead_skipped_no_company_title')
      }
      const key = `app.reminders.events.${item.event_type}`
      const translated = t(key, { defaultValue: '' })
      if (translated && translated !== key) return translated
      return (
        (item.payload?.title as string) ||
        item.event_type ||
        t('app.reminders.events.unknown', { values: { event: String(item.event_type || 'event') } })
      )
    },
    [t]
  )

  const notificationDescription = useCallback(
    (item: NotificationItem) => {
      const payload = (item.payload || {}) as Record<string, any>
      const et = String(item.event_type || '').trim().toLowerCase()
      if (et === 'lead_public_intake_client') {
        return t('app.notifications.lead_public_intake_client_desc', {
          values: { name: String(payload.candidate_name || '').trim() || '—' },
        })
      }
      if (et === 'intake_client_lead_skipped_no_company') {
        return t('app.notifications.intake_client_lead_skipped_no_company_desc', {
          values: { name: String(payload.candidate_name || '').trim() || '—' },
        })
      }
      return String(payload.description || '').trim()
    },
    [t]
  )

  const reminderGroups = useMemo(() => {
    const buckets: Record<string, TaskRow[]> = {
      overdue: [],
      today: [],
      tomorrow: [],
      week: [],
      later: [],
      unscheduled: [],
      done: [],
    }
    filteredReminderRows.forEach((item) => {
      buckets[bucketReminderByDue(item)].push(item)
    })
    const openKeys = ['overdue', 'today', 'tomorrow', 'week', 'later', 'unscheduled'] as const
    for (const k of openKeys) {
      buckets[k].sort(compareOpenTasksBySlaThenDue)
    }
    buckets.done.sort(compareDoneTasksByUpdated)
    return buckets
  }, [filteredReminderRows])

  const taskSections = useMemo((): TaskSection[] => {
    const rows = filteredReminderRows

    if (taskListMode === 'sla_queue') {
      const open = rows.filter((item) => !isClosedReminderStatus(item.status)).sort(compareOpenTasksBySlaThenDue)
      const done = rows.filter((item) => isClosedReminderStatus(item.status)).sort(compareDoneTasksByUpdated)
      const out: TaskSection[] = []
      if (taskFilters.status !== 'done' && open.length > 0) {
        out.push({ key: 'sla_open', label: t('app.reminders.group.sla_queue'), items: open })
      }
      if (taskFilters.status !== 'active' && done.length > 0) {
        out.push({ key: 'sla_done', label: t('app.reminders.group.done'), items: done })
      }
      return out
    }

    if (taskListMode === 'by_candidate') {
      const groups = new Map<string, TaskRow[]>()
      for (const item of rows) {
        const et = String(item.entity_type || '').trim().toLowerCase()
        const eid = String(item.entity_id || '').trim()
        const hasEntityLink = Boolean(reminderEntityHref(item))
        const key = et === 'candidate' && eid ? `cand:${eid}` : hasEntityLink ? '__other' : '__unlinked'
        const arr = groups.get(key) || []
        arr.push(item)
        groups.set(key, arr)
      }
      for (const [, arr] of groups) {
        const sorted = sortTaskRowsMixedOpenFirst(arr)
        arr.length = 0
        arr.push(...sorted)
      }
      const keys = [...groups.keys()].sort((a, b) => {
        if (a === '__other' || a === '__unlinked') return 1
        if (b === '__other' || b === '__unlinked') return -1
        const ga = groups.get(a)!
        const gb = groups.get(b)!
        const ar = ga.find((r) => !isClosedReminderStatus(r.status)) || ga[0]
        const br = gb.find((r) => !isClosedReminderStatus(r.status)) || gb[0]
        return compareOpenTasksBySlaThenDue(ar, br)
      })
      return keys
        .map((key): TaskSection => {
          const items = groups.get(key) || []
          if (key === '__other') {
            return { key, label: t('app.reminders.layout.groups_other_entities'), items }
          }
          if (key === '__unlinked') {
            return { key, label: t('app.reminders.layout.groups_unlinked_entities'), items }
          }
          const first = items[0]
          const name = linkedEntityDisplayName(first) || String(first.entity_id || '').trim()
          const headerHref = reminderEntityHref(first)
          return {
            key,
            label: t('app.reminders.layout.group_candidate', { defaultValue: 'Candidate: {name}', values: { name } }),
            headerHref,
            items,
          }
        })
        .filter((s) => s.items.length > 0)
    }

    if (taskListMode === 'by_task_type') {
      const groups = new Map<string, TaskRow[]>()
      for (const item of rows) {
        const ty = String(item.type || 'unknown').trim() || 'unknown'
        const arr = groups.get(ty) || []
        arr.push(item)
        groups.set(ty, arr)
      }
      for (const [, arr] of groups) {
        const sorted = sortTaskRowsMixedOpenFirst(arr)
        arr.length = 0
        arr.push(...sorted)
      }
      const keys = [...groups.keys()].sort((a, b) => (groups.get(b)!.length || 0) - (groups.get(a)!.length || 0))
      return keys
        .map((ty) => ({
          key: `type:${ty}`,
          label: t('app.reminders.task_type_label', { defaultValue: 'Task type: {type}', values: { type: ty } }),
          items: groups.get(ty) || [],
        }))
        .filter((s) => s.items.length > 0)
    }

    if (taskListMode === 'by_due_day') {
      const groups = new Map<string, TaskRow[]>()
      for (const item of rows) {
        const k = dueDaySectionKey(item)
        const arr = groups.get(k) || []
        arr.push(item)
        groups.set(k, arr)
      }
      for (const [, arr] of groups) {
        const sorted = sortTaskRowsMixedOpenFirst(arr)
        arr.length = 0
        arr.push(...sorted)
      }
      const orderedKeys = sortDueDaySectionKeys([...groups.keys()])
      return orderedKeys
        .map((key): TaskSection => {
          let label = key
          if (key === 'overdue') label = t('app.reminders.status.overdue')
          else if (key === 'unscheduled') label = t('app.reminders.group.unscheduled')
          else if (key === 'done') label = t('app.reminders.group.done')
          else if (key.startsWith('day:')) {
            const d = parseCalendarDayKey(key)
            label = d ? format(d, 'EEEE, d MMM yyyy', { locale: dateLocale }) : key
          }
          return { key, label, items: groups.get(key) || [] }
        })
        .filter((s) => s.items.length > 0)
    }

    const dueOrder = ['overdue', 'today', 'tomorrow', 'week', 'later', 'unscheduled', 'done'] as const
    const dueLabels: Record<(typeof dueOrder)[number], string> = {
      overdue: t('app.reminders.status.overdue'),
      today: t('app.reminders.group.today'),
      tomorrow: t('app.reminders.group.tomorrow'),
      week: t('app.reminders.group.week'),
      later: t('app.reminders.group.later'),
      unscheduled: t('app.reminders.group.unscheduled'),
      done: t('app.reminders.group.done'),
    }
    return dueOrder
      .map((key) => ({ key, label: dueLabels[key], items: reminderGroups[key] || [] }))
      .filter((s) => s.items.length > 0)
  }, [dateLocale, filteredReminderRows, format, reminderGroups, t, taskFilters.status, taskListMode])

  const visibleNotifications = useMemo(() => {
    const q = normalizeText(eventsFilters.search)
    return notifications
      .filter((item) => {
        if (eventsFilters.read === 'unread' && item.is_read) return false
        if (!q) return true
        const hay = [
          item.event_type,
          String(item.payload?.title || ''),
          String(item.payload?.description || ''),
          String(item.entity_type || ''),
          String(item.entity_id || ''),
        ]
          .join(' ')
          .toLowerCase()
        return hay.includes(q)
      })
      .sort((a, b) => {
        const rankDiff = notificationRank(b) - notificationRank(a)
        if (rankDiff !== 0) return rankDiff
        return Date.parse(b.created_at || '') - Date.parse(a.created_at || '')
      })
  }, [eventsFilters.read, eventsFilters.search, notifications])

  const taskCounts = useMemo(() => {
    // G-7 stage 2: count BOTH reminder + planner-task rows so the
    // badge totals match what the user actually sees in the list.
    return {
      total: reminderRows.length,
      active: reminderRows.filter((r) => !isClosedReminderStatus(r.status)).length,
      overdue: reminderRows.filter((r) => r.status === 'overdue').length,
      done: reminderRows.filter((r) => isClosedReminderStatus(r.status)).length,
    }
  }, [reminderRows])
  const selectedTaskSet = useMemo(() => new Set(selectedTaskIds), [selectedTaskIds])
  const selectedTaskRows = useMemo(
    () => filteredReminderRows.filter((r) => selectedTaskSet.has(r.id)),
    [filteredReminderRows, selectedTaskSet],
  )
  const unlinkedVisibleCount = useMemo(
    () => filteredReminderRows.filter((r) => reminderEntityHref(r) == null).length,
    [filteredReminderRows],
  )

  const notificationCounts = useMemo(() => {
    return {
      total: notifications.length,
      unread: notifications.filter((n) => !n.is_read).length,
    }
  }, [notifications])

  const entityTypeOptions = useMemo(() => {
    // G-7 stage 2: include planner-derived rows so the entity-type
    // dropdown lists every entity actually visible (e.g. 'planner'
    // appears for stand-alone planner tasks without an entity link).
    return Array.from(new Set(reminderRows.map((r) => r.entity_type).filter(Boolean))).sort()
  }, [reminderRows])

  useEffect(() => {
    const allowed = new Set(filteredReminderRows.map((r) => r.id))
    setSelectedTaskIds((prev) => prev.filter((id) => allowed.has(id)))
  }, [filteredReminderRows])

  const openEdit = (item: TaskRow) => {
    setEditState({
      id: item.id,
      title: item.title || '',
      description: item.description || '',
      dueAtLocal: toLocalInputValue(item.dueDate),
      remindAtLocal: toLocalInputValue(item.remindDate),
      priority: item.priority || 'normal',
    })
  }

  const submitQuickReminder = async (e: FormEvent) => {
    e.preventDefault()
    if (!formTitle.trim()) return
    setCreateBusy(true)
    setRemindersError(null)
    try {
      const dueDate = new Date(formDueAt || getDefaultDueAtLocal())
      const remindAt = new Date(dueDate.getTime() - remindOffset * 60 * 1000)
      await createReminder({
        title: formTitle.trim(),
        description: formDescription.trim(),
        type: 'custom',
        entity_type: 'custom',
        entity_id: 'manual',
        due_at: dueDate.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: formPriority,
      })
      setFormTitle('')
      setFormDescription('')
      setFormDueAt(getDefaultDueAtLocal())
      await loadReminders()
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.create'))) {
        setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.create'), t))
      }
    } finally {
      setCreateBusy(false)
    }
  }

  // G-7 stage 2 (Phase 2.1 ADR-012): every action handler must inspect
  // `_source` and route to the correct underlying API. Reminders use
  // /api/v1/activities directly; planner-derived rows go through the
  // CommunicationPlannerEvent shim in src/api/communications.ts (which
  // also targets /api/v1/activities under the hood with a field remap).
  const handleComplete = async (id: string) => {
    setTaskBusyId(id)
    setRemindersError(null)
    const row = reminderRows.find((r) => r.id === id)
    try {
      if (row?._source === 'planner') {
        const updated = await patchCommunicationPlannerEvent(id, { status: 'done' })
        setPlannerTaskEvents((prev) =>
          prev.map((e) => (e.id === id ? (updated as CommunicationPlannerEvent) : e)),
        )
      } else {
        const updated = await completeReminder(id)
        setReminders((prev) => prev.map((r) => (r.id === id ? (updated as ReminderRecord) : r)))
      }
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.complete'))) {
        setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.complete'), t))
      }
    } finally {
      setTaskBusyId(null)
    }
  }

  const handleSnooze = async (id: string, minutes: number) => {
    setTaskBusyId(id)
    setRemindersError(null)
    const row = reminderRows.find((r) => r.id === id)
    try {
      if (row?._source === 'planner') {
        // Planner events have no `snoozed_until` semantics — translate
        // "snooze by N minutes" into a `start_at` shift. The original
        // duration is preserved by also shifting `end_at` if present.
        const start = row.dueDate || new Date()
        const newStart = new Date(start.getTime() + minutes * 60_000)
        const originalEvent = plannerTaskEvents.find((e) => e.id === id)
        const originalEnd = originalEvent?.end_at ? parseDate(originalEvent.end_at) : null
        const newEndIso = originalEnd
          ? new Date(originalEnd.getTime() + minutes * 60_000).toISOString()
          : undefined
        const updated = await patchCommunicationPlannerEvent(id, {
          start_at: newStart.toISOString(),
          ...(newEndIso ? { end_at: newEndIso } : {}),
        })
        setPlannerTaskEvents((prev) =>
          prev.map((e) => (e.id === id ? (updated as CommunicationPlannerEvent) : e)),
        )
      } else {
        const updated = await snoozeReminder(id, { minutes })
        setReminders((prev) => prev.map((r) => (r.id === id ? (updated as ReminderRecord) : r)))
      }
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.snooze'))) {
        setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.snooze'), t))
      }
    } finally {
      setTaskBusyId(null)
    }
  }

  const toggleTaskSelection = (id: string, next: boolean) => {
    setSelectedTaskIds((prev) => {
      const has = prev.includes(id)
      if (next && !has) return [...prev, id]
      if (!next && has) return prev.filter((x) => x !== id)
      return prev
    })
  }

  const toggleSelectAllVisibleTasks = (next: boolean) => {
    const ids = filteredReminderRows.map((r) => r.id)
    setSelectedTaskIds((prev) => {
      if (next) return [...new Set([...prev, ...ids])]
      const remove = new Set(ids)
      return prev.filter((id) => !remove.has(id))
    })
  }

  const runBulkTaskAction = async (
    action: (row: TaskRow) => Promise<void>,
    errorMessageKey: string,
  ) => {
    if (bulkBusy || selectedTaskRows.length === 0) return
    setBulkBusy(true)
    setRemindersError(null)
    let ok = 0
    let failed = 0
    for (const row of selectedTaskRows) {
      try {
        await action(row)
        ok += 1
      } catch {
        failed += 1
      }
    }
    if (ok > 0) {
      await loadReminders()
      const selectedNow = new Set(selectedTaskRows.map((r) => r.id))
      setSelectedTaskIds((prev) => prev.filter((id) => !selectedNow.has(id)))
    }
    if (failed > 0) {
      setRemindersError(getFriendlyErrorInfo(new Error(t(errorMessageKey)), t(errorMessageKey), t))
    }
    setBulkBusy(false)
  }

  const bulkSnooze = async (minutes: number) => {
    await runBulkTaskAction(async (row) => {
      if (row._source === 'planner') {
        const start = row.dueDate || new Date()
        const newStart = new Date(start.getTime() + minutes * 60_000)
        const originalEvent = plannerTaskEvents.find((e) => e.id === row.id)
        const originalEnd = originalEvent?.end_at ? parseDate(originalEvent.end_at) : null
        const newEndIso = originalEnd ? new Date(originalEnd.getTime() + minutes * 60_000).toISOString() : undefined
        await patchCommunicationPlannerEvent(row.id, {
          start_at: newStart.toISOString(),
          ...(newEndIso ? { end_at: newEndIso } : {}),
        })
      } else {
        await snoozeReminder(row.id, { minutes })
      }
    }, 'app.reminders.errors.snooze')
  }

  const bulkReschedule = async () => {
    if (!bulkRescheduleLocal) return
    const dueIso = new Date(bulkRescheduleLocal).toISOString()
    await runBulkTaskAction(async (row) => {
      if (row._source === 'planner') {
        const plannerPayload: Record<string, unknown> = { start_at: dueIso }
        const originalEvent = plannerTaskEvents.find((evt) => evt.id === row.id)
        const originalStart = originalEvent ? parseDate(originalEvent.start_at) : null
        const originalEnd = originalEvent?.end_at ? parseDate(originalEvent.end_at) : null
        if (originalStart && originalEnd) {
          const durationMs = originalEnd.getTime() - originalStart.getTime()
          plannerPayload.end_at = new Date(new Date(dueIso).getTime() + durationMs).toISOString()
        }
        await patchCommunicationPlannerEvent(row.id, plannerPayload)
      } else {
        await updateReminder(row.id, { due_at: dueIso })
      }
    }, 'app.reminders.errors.update')
  }

  const bulkReassign = async () => {
    const assignee = bulkAssigneeId.trim() || null
    await runBulkTaskAction(async (row) => {
      if (row._source === 'planner') {
        await patchCommunicationPlannerEvent(row.id, { assignee_id: assignee })
      } else {
        await updateReminder(row.id, { assignee_id: assignee })
      }
    }, 'app.reminders.errors.update')
  }

  const submitEdit = async (e: FormEvent) => {
    e.preventDefault()
    if (!editState) return
    setEditBusy(true)
    setRemindersError(null)
    const editingRow = reminderRows.find((r) => r.id === editState.id)
    try {
      if (editingRow?._source === 'planner') {
        // G-7 stage 2: planner edit. Reminders carry both due_at and
        // remind_at — planner has only start_at (mapped to due_at on
        // the row). We honour `dueAtLocal` as the planner's new
        // start_at and ignore the remind_at field (planner has no
        // analogous concept). End_at duration is preserved as in
        // handleSnooze.
        const plannerPayload: Record<string, unknown> = {
          title: editState.title.trim(),
          description: editState.description.trim(),
          priority: editState.priority || 'normal',
        }
        if (editState.dueAtLocal) {
          const newStart = new Date(editState.dueAtLocal)
          plannerPayload.start_at = newStart.toISOString()
          const originalEvent = plannerTaskEvents.find((evt) => evt.id === editState.id)
          const originalStart = originalEvent ? parseDate(originalEvent.start_at) : null
          const originalEnd = originalEvent?.end_at ? parseDate(originalEvent.end_at) : null
          if (originalStart && originalEnd) {
            const durationMs = originalEnd.getTime() - originalStart.getTime()
            plannerPayload.end_at = new Date(newStart.getTime() + durationMs).toISOString()
          }
        }
        const updated = await patchCommunicationPlannerEvent(editState.id, plannerPayload)
        setPlannerTaskEvents((prev) =>
          prev.map((evt) => (evt.id === editState.id ? (updated as CommunicationPlannerEvent) : evt)),
        )
      } else {
        const payload: Record<string, unknown> = {
          title: editState.title.trim(),
          description: editState.description.trim(),
          priority: editState.priority || 'normal',
        }
        if (editState.dueAtLocal) payload.due_at = new Date(editState.dueAtLocal).toISOString()
        if (editState.remindAtLocal) payload.remind_at = new Date(editState.remindAtLocal).toISOString()
        const updated = await updateReminder(editState.id, payload)
        setReminders((prev) => prev.map((r) => (r.id === editState.id ? (updated as ReminderRecord) : r)))
      }
      setEditState(null)
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.update'))) {
        setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.update'), t))
      }
    } finally {
      setEditBusy(false)
    }
  }

  const markOneRead = async (id: string) => {
    setNotifBusyId(id)
    setNotificationsError(null)
    try {
      await markNotificationsRead({ ids: [id] })
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n)))
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.notification_mark_one'))) {
        setNotificationsError(getFriendlyErrorInfo(err, t('app.reminders.errors.notification_mark_one'), t))
      }
    } finally {
      setNotifBusyId(null)
    }
  }

  const markAllRead = async () => {
    setMarkAllBusy(true)
    setNotificationsError(null)
    try {
      await markNotificationsRead({ markAll: true })
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true, read_at: n.read_at || new Date().toISOString() })))
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.notification_mark_all'))) {
        setNotificationsError(getFriendlyErrorInfo(err, t('app.reminders.errors.notification_mark_all'), t))
      }
    } finally {
      setMarkAllBusy(false)
    }
  }

  const copyTaskIds = async (ids: string[], sectionKey: string) => {
    const lines = ids.map((id) => String(id).trim()).filter(Boolean)
    if (!lines.length) return
    const text = lines.join('\n')
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        throw new Error('clipboard-unavailable')
      }
      setCopiedSectionKey(sectionKey)
      window.setTimeout(() => setCopiedSectionKey((prev) => (prev === sectionKey ? null : prev)), 1800)
    } catch {
      // Fallback: open prompt so operator can copy IDs manually.
      window.prompt(t('app.reminders.layout.copy_ids_prompt', { defaultValue: 'Copy task IDs' }), text)
    }
  }

  const formatRelative = (date: Date | null): string => {
    if (!date) return '—'
    return formatDistanceToNow(date, { addSuffix: true, locale: dateLocale })
  }

  const formatTs = (date: Date | null): string => {
    if (!date) return '—'
    return format(date, 'dd MMM yyyy, HH:mm', { locale: dateLocale })
  }

  const tasksTabSubtitle =
    activeTab === 'tasks'
      ? t('app.reminders.subtitle', {
          values: { total: taskCounts.total, unread: taskCounts.active, scope: t('app.reminders.scope_labels.direct') },
        })
      : t('app.reminders.subtitle', {
          values: {
            total: notificationCounts.total,
            unread: notificationCounts.unread,
            scope: t('app.reminders.scope_labels.all'),
          },
        })

  return (
    <PageShell>
      <WorkspaceTopNav active="tasks" />
      <PageShellHeader>
        <PageHeader
          title={t('app.tasks.hub_title')}
          subtitle={tasksTabSubtitle}
          kind="browse"
          primaryAction={
            activeTab === 'tasks' ? (
              <button type="button" className="btn-primary btn-sm" onClick={openQuickReminderComposer}>
                {t('app.reminders.header.create_task', { defaultValue: 'Create task' })}
              </button>
            ) : undefined
          }
          secondaryActions={
            <>
              <button
                type="button"
                className={clsx('btn btn-sm rounded-lg border px-3 py-2 text-sm font-medium transition', activeTab === 'tasks' ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50')}
                onClick={() => setActiveTab('tasks')}
              >
                {t('app.reminders.tab.tasks')} ({taskCounts.active})
              </button>
              <button
                type="button"
                className={clsx('btn btn-sm rounded-lg border px-3 py-2 text-sm font-medium transition', activeTab === 'events' ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50')}
                onClick={() => setActiveTab('events')}
              >
                {t('app.reminders.tab.events')} ({notificationCounts.unread})
              </button>
            </>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 px-4 pb-4">
      {activeTab === 'tasks' && (
        <>
          <details className="group shrink-0 rounded-xl border border-slate-200/90 bg-white shadow-sm">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              {t('app.reminders.quick_create')}
              <span className="text-xs font-normal text-slate-500">{composerOpen ? t('common.actions.collapse') : t('common.actions.expand')}</span>
            </summary>
            <div className="border-t border-slate-200/80 p-4">
              <form onSubmit={submitQuickReminder} className="grid gap-3 lg:grid-cols-12">
                <div className="lg:col-span-4">
                  <label className="block text-xs font-medium text-slate-600">
                    {t('app.reminders.form.title')}
                  </label>
                  <input
                    type="text"
                    className="input mt-1 w-full"
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    placeholder={t('app.reminders.form.title_placeholder')}
                    required
                  />
                </div>
                <div className="lg:col-span-3">
                  <label className="block text-xs font-medium text-slate-600">
                    {t('app.reminders.form.due')}
                  </label>
                  <input
                    type="datetime-local"
                    className="input mt-1 w-full"
                    value={formDueAt}
                    onChange={(e) => setFormDueAt(e.target.value)}
                  />
                </div>
                <div className="lg:col-span-2">
                  <label className="block text-xs font-medium text-slate-600">
                    {t('app.reminders.form.remind_before')}
                  </label>
                  <select className="input mt-1 w-full" value={remindOffset} onChange={(e) => setRemindOffset(Number(e.target.value))}>
                    <option value={5}>{t('app.reminders.form.remind_offsets.5m')}</option>
                    <option value={15}>{t('app.reminders.form.remind_offsets.15m')}</option>
                    <option value={30}>{t('app.reminders.form.remind_offsets.30m')}</option>
                    <option value={60}>{t('app.reminders.form.remind_offsets.1h')}</option>
                    <option value={180}>{t('app.reminders.form.remind_offsets.3h')}</option>
                    <option value={1440}>{t('app.reminders.form.remind_offsets.1d')}</option>
                  </select>
                </div>
                <div className="lg:col-span-2">
                  <label className="block text-xs font-medium text-slate-600">
                    {t('app.reminders.form.priority')}
                  </label>
                  <select className="input mt-1 w-full" value={formPriority} onChange={(e) => setFormPriority(e.target.value)}>
                    <option value="low">{t('app.reminders.priority.low')}</option>
                    <option value="normal">{t('app.reminders.priority.normal')}</option>
                    <option value="high">{t('app.reminders.priority.high')}</option>
                  </select>
                </div>
                <div className="lg:col-span-1 flex items-end">
                  <button type="submit" className="btn-primary w-full" disabled={createBusy || !formTitle.trim()}>
                    {createBusy ? t('common.loading') : t('app.reminders.create')}
                  </button>
                </div>
                <div className="lg:col-span-12">
                  <label className="block text-xs font-medium text-slate-600">
                    {t('app.reminders.form.description')}
                  </label>
                  <textarea
                    rows={2}
                    className="textarea mt-1 w-full"
                    value={formDescription}
                    onChange={(e) => setFormDescription(e.target.value)}
                    placeholder={t('app.reminders.form.description_placeholder')}
                  />
                </div>
              </form>
            </div>
          </details>

          <Toolbar>
            <div className="flex flex-wrap items-center gap-2">
              <div className="min-w-hf-220 flex-1">
                <input
                  className="input w-full"
                  value={taskFilters.search}
                  onChange={(e) => setTaskFilters((prev) => ({ ...prev, search: e.target.value }))}
                  placeholder={t('app.reminders.filters.search_tasks')}
                />
              </div>
              <button type="button" className="btn-secondary btn-sm" onClick={() => void loadReminders()}>
                {t('app.reminders.actions.refresh')}
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => {
                  setTaskFilters(DEFAULT_TASK_FILTERS)
                  setAssigneeScope('mine')
                  setTaskListMode('by_due')
                }}
              >
                {t('common.actions.reset')}
              </button>
            </div>

            <details className="rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2">
              <summary className="cursor-pointer text-xs font-semibold text-slate-700">
                {t('app.reminders.filters.more', { defaultValue: 'More filters' })}
                {(taskFilters.entityType || taskFilters.priority || taskFilters.unlinkedOnly) && (
                  <span className="ml-2 font-normal text-slate-500">
                    ({[
                      taskFilters.entityType,
                      taskFilters.priority,
                      taskFilters.unlinkedOnly ? t('app.reminders.filters.unlinked_short', { defaultValue: 'unlinked' }) : '',
                    ]
                      .filter(Boolean)
                      .join(' · ')})
                  </span>
                )}
              </summary>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <select
                  className="input"
                  value={taskFilters.entityType}
                  onChange={(e) => setTaskFilters((prev) => ({ ...prev, entityType: e.target.value }))}
                  aria-label={t('app.reminders.filters.entity_all')}
                >
                  <option value="">{t('app.reminders.filters.entity_all')}</option>
                  {entityTypeOptions.map((entityType) => (
                    <option key={entityType} value={entityType}>{entityType}</option>
                  ))}
                </select>
                <select
                  className="input"
                  value={taskFilters.priority}
                  onChange={(e) => setTaskFilters((prev) => ({ ...prev, priority: e.target.value }))}
                  aria-label={t('app.reminders.filters.priority_all')}
                >
                  <option value="">{t('app.reminders.filters.priority_all')}</option>
                  <option value="low">{t('app.reminders.priority.low')}</option>
                  <option value="normal">{t('app.reminders.priority.normal')}</option>
                  <option value="high">{t('app.reminders.priority.high')}</option>
                </select>
                <label className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700">
                  <input
                    type="checkbox"
                    className="h-3.5 w-3.5"
                    checked={taskFilters.includeCompletedEntities}
                    onChange={(e) =>
                      setTaskFilters((prev) => ({
                        ...prev,
                        includeCompletedEntities: e.target.checked,
                      }))
                    }
                  />
                  {t('app.reminders.filters.include_completed_candidates', {
                    defaultValue: 'Show tasks for completed/rejected candidates',
                  })}
                </label>
              </div>
            </details>

            <div className="flex flex-wrap gap-2">
              {(['active', 'all', 'done'] as TaskStatusFilter[]).map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setTaskFilters((prev) => ({ ...prev, status }))}
                  className={clsx(
                    'btn rounded-lg border px-3 py-2 text-xs font-medium transition',
                    taskFilters.status === status
                      ? 'border-brand-600 bg-brand-600 text-white'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  )}
                >
                  {status === 'active' && `${t('app.reminders.filter.active')} (${taskCounts.active})`}
                  {status === 'all' && `${t('app.reminders.filter.all')} (${taskCounts.total})`}
                  {status === 'done' && `${t('app.reminders.filter.done')} (${taskCounts.done})`}
                </button>
              ))}
              {(taskCounts.overdue > 0 || taskFilters.dueBucket === 'overdue') && (
                <button
                  type="button"
                  onClick={() =>
                    setTaskFilters((prev) => ({
                      ...prev,
                      dueBucket: prev.dueBucket === 'overdue' ? '' : 'overdue',
                    }))
                  }
                  className={clsx(
                    'btn rounded-lg border px-3 py-2 text-xs font-semibold transition',
                    taskFilters.dueBucket === 'overdue'
                      ? 'border-rose-600 bg-rose-600 text-white shadow-sm'
                      : 'border-rose-200 bg-rose-50 text-rose-800 hover:bg-rose-100'
                  )}
                >
                  {taskFilters.dueBucket === 'overdue'
                    ? t('app.reminders.filters.overdue_clear', { defaultValue: 'Show all due dates' })
                    : t('app.reminders.filters.overdue_only', {
                        defaultValue: 'Overdue only ({count})',
                        values: { count: taskCounts.overdue },
                      })}
                </button>
              )}
              {(unlinkedVisibleCount > 0 || taskFilters.unlinkedOnly) && (
                <button
                  type="button"
                  onClick={() =>
                    setTaskFilters((prev) => ({
                      ...prev,
                      unlinkedOnly: !prev.unlinkedOnly,
                    }))
                  }
                  className={clsx(
                    'btn rounded-lg border px-3 py-2 text-xs font-semibold transition',
                    taskFilters.unlinkedOnly
                      ? 'border-amber-600 bg-amber-600 text-white shadow-sm'
                      : 'border-amber-200 bg-amber-50 text-amber-900 hover:bg-amber-100',
                  )}
                  title={t('app.reminders.layout.groups_unlinked_entities_hint')}
                >
                  {taskFilters.unlinkedOnly
                    ? t('app.reminders.filters.unlinked_clear', { defaultValue: 'Show linked + unlinked' })
                    : t('app.reminders.filters.unlinked_only', {
                        defaultValue: 'Unlinked only ({count})',
                        values: { count: unlinkedVisibleCount },
                      })}
                </button>
              )}
              {canUseTeamAssigneeScope && (
                <>
                  <button
                    type="button"
                    onClick={() => setAssigneeScope('mine')}
                    className={clsx(
                      'btn rounded-lg border px-3 py-2 text-xs font-medium transition',
                      assigneeScope === 'mine'
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                    )}
                  >
                    {t('app.reminders.assignee.mine')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setAssigneeScope('team')}
                    className={clsx(
                      'btn rounded-lg border px-3 py-2 text-xs font-medium transition',
                      assigneeScope === 'team'
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                    )}
                  >
                    {t('app.reminders.assignee.team')}
                  </button>
                </>
              )}
            </div>
            <details className="rounded-lg border border-dashed border-slate-200 px-3 py-2">
              <summary className="cursor-pointer text-xs font-medium text-slate-600">
                {t('app.reminders.layout.advanced_toggle', { defaultValue: 'List layout (advanced)' })}
              </summary>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <label htmlFor="hf-task-list-mode" className="text-xs font-medium text-slate-600">
                  {t('app.reminders.layout.label')}
                </label>
                <select
                  id="hf-task-list-mode"
                  className="input max-w-xs py-2 text-sm"
                  value={taskListMode}
                  onChange={(e) => setTaskListMode(e.target.value as TaskListMode)}
                >
                  <option value="by_due">{t('app.reminders.layout.by_due')}</option>
                  <option value="sla_queue">{t('app.reminders.layout.sla_queue')}</option>
                  <option value="by_due_day">{t('app.reminders.layout.by_due_day')}</option>
                  <option value="by_candidate">{t('app.reminders.layout.by_candidate')}</option>
                  <option value="by_task_type">{t('app.reminders.layout.by_task_type')}</option>
                </select>
              </div>
              <p className="mt-2 text-[11px] text-slate-500">
                {taskListMode === 'sla_queue'
                  ? t('app.reminders.sla_flat_hint')
                  : taskListMode === 'by_candidate'
                    ? t('app.reminders.layout_hint_by_candidate')
                    : taskListMode === 'by_task_type'
                      ? t('app.reminders.layout_hint_by_task_type')
                      : taskListMode === 'by_due_day'
                        ? t('app.reminders.layout_hint_by_due_day')
                        : t('app.reminders.sla_sort_hint')}
              </p>
            </details>
          </Toolbar>

          <DataTableFrame
            className="min-h-0 flex-1"
            header={
              filteredReminderRows.length > 0 ? (
                <div className="border-b border-slate-200/80 px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <label className="inline-flex items-center gap-2 text-xs text-slate-700">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                        checked={filteredReminderRows.length > 0 && selectedTaskRows.length === filteredReminderRows.length}
                        onChange={(e) => toggleSelectAllVisibleTasks(e.target.checked)}
                      />
                      {t('app.reminders.bulk.select_visible', { defaultValue: 'Select visible ({count})', values: { count: filteredReminderRows.length } })}
                    </label>
                    <span className="text-xs text-slate-500">
                      {t('app.reminders.bulk.selected', { defaultValue: 'Selected: {count}', values: { count: selectedTaskRows.length } })}
                    </span>
                    <button type="button" className="btn-secondary btn-xs" onClick={() => void bulkSnooze(15)} disabled={bulkBusy || selectedTaskRows.length === 0}>
                      {t('app.reminders.bulk.snooze_15', { defaultValue: 'Snooze +15m' })}
                    </button>
                    <button type="button" className="btn-secondary btn-xs" onClick={() => void bulkSnooze(60)} disabled={bulkBusy || selectedTaskRows.length === 0}>
                      {t('app.reminders.bulk.snooze_60', { defaultValue: 'Snooze +1h' })}
                    </button>
                    <input
                      type="datetime-local"
                      className="input py-1 text-xs"
                      value={bulkRescheduleLocal}
                      onChange={(e) => setBulkRescheduleLocal(e.target.value)}
                    />
                    <button type="button" className="btn-secondary btn-xs" onClick={() => void bulkReschedule()} disabled={bulkBusy || selectedTaskRows.length === 0 || !bulkRescheduleLocal}>
                      {t('app.reminders.bulk.reschedule', { defaultValue: 'Re-schedule' })}
                    </button>
                    <input
                      className="input max-w-[11rem] py-1 text-xs"
                      placeholder={t('app.reminders.bulk.assignee_placeholder', { defaultValue: 'Assignee user id' })}
                      value={bulkAssigneeId}
                      onChange={(e) => setBulkAssigneeId(e.target.value)}
                    />
                    <button type="button" className="btn-secondary btn-xs" onClick={() => void bulkReassign()} disabled={bulkBusy || selectedTaskRows.length === 0}>
                      {t('app.reminders.bulk.reassign', { defaultValue: 'Bulk reassign' })}
                    </button>
                    {selectedTaskRows.length > 0 ? (
                      <button type="button" className="btn-secondary btn-xs" onClick={() => setSelectedTaskIds([])}>
                        {t('app.reminders.bulk.clear', { defaultValue: 'Clear selection' })}
                      </button>
                    ) : null}
                  </div>
                </div>
              ) : undefined
            }
            preScroll={
              remindersState === 'error' && remindersError ? (
                <div className="border-b border-slate-200/80 px-4 py-3">
                  <ErrorRecoveryBanner
                    compact
                    info={remindersError}
                    onRetry={() => void loadReminders()}
                    retryLabel={t('common.retry')}
                    {...friendlyErrorBannerSecondary(remindersError, CRM_APP_PATHS.leads, t('app.reminders.states.empty_cta_leads'))}
                  />
                </div>
              ) : undefined
            }
            footer={t('app.reminders.list.count', {
              defaultValue: '{{count}} tasks',
              values: { count: filteredReminderRows.length },
            })}
          >
            {remindersState === 'loading' ? (
              <div className="px-4 py-6 text-sm text-slate-500">{t('common.loading')}</div>
            ) : null}

            {remindersState !== 'loading' && filteredReminderRows.length === 0 ? (
              <div className="p-4">
                <EmptyStatePanel
                  compact
                  title={t('app.reminders.states.empty_title')}
                  description={t('app.reminders.states.empty_desc')}
                  whyHint={t('app.reminders.states.empty_why', {
                    defaultValue:
                      'After you contact a lead, the next follow-up appears here — so nothing sits untouched.',
                  })}
                  primaryAction={{
                    label: t('app.reminders.states.empty_cta_leads'),
                    to: CRM_APP_PATHS.leads,
                  }}
                  secondaryAction={{
                    label: t('app.reminders.states.empty_cta_create'),
                    onClick: openQuickReminderComposer,
                  }}
                />
              </div>
            ) : null}

            {remindersState !== 'loading' && filteredReminderRows.length > 0 ? (
              <div className="space-y-5 p-4">
                {taskSections.map((section) => (
                  <section key={section.key} className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="min-w-0 text-sm font-semibold text-slate-900">
                        {section.headerHref ? (
                          <Link to={section.headerHref} className="text-brand-800 hover:underline">
                            {section.label}
                          </Link>
                        ) : (
                          <span className="inline-flex items-center gap-2 truncate">
                            <span className="truncate">{section.label}</span>
                            {section.key === '__unlinked' ? (
                              <span
                                className="shrink-0 rounded-lg border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800"
                                title={t('app.reminders.layout.groups_unlinked_entities_hint')}
                              >
                                {t('app.reminders.layout.unlinked_badge')}
                              </span>
                            ) : null}
                          </span>
                        )}
                      </h3>
                      <div className="shrink-0 flex items-center gap-2">
                        {section.key === '__unlinked' ? (
                          <button
                            type="button"
                            className="btn rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                            onClick={() => void copyTaskIds(section.items.map((i) => i.id), section.key)}
                          >
                            {copiedSectionKey === section.key
                              ? t('app.reminders.layout.copy_ids_done', { defaultValue: 'Copied' })
                              : t('app.reminders.layout.copy_ids', { defaultValue: 'Copy IDs' })}
                          </button>
                        ) : null}
                        <span className="text-xs text-slate-500">{section.items.length}</span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      {section.items.map((item) => (
                        <ReminderTaskRow
                          key={item.id}
                          item={item}
                          t={t}
                          reminderStatusLabel={reminderStatusLabel}
                          formatTs={formatTs}
                          formatRelative={formatRelative}
                          taskBusyId={taskBusyId}
                          editBusy={editBusy}
                          highlighted={highlightTaskId === String(item.id)}
                          selected={selectedTaskSet.has(item.id)}
                          onToggleSelect={toggleTaskSelection}
                          onEdit={openEdit}
                          onSnooze={handleSnooze}
                          onComplete={handleComplete}
                        />
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            ) : null}
          </DataTableFrame>
        </>
      )}

      {activeTab === 'events' && (
        <>
          <Toolbar>
            <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-hf-220 flex-1">
              <input
                className="input w-full"
                value={eventsFilters.search}
                onChange={(e) => setEventsFilters((prev) => ({ ...prev, search: e.target.value }))}
                placeholder={t('app.reminders.filters.search_events')}
              />
            </div>
            <select className="input" value={eventsFilters.scope} onChange={(e) => setEventsFilters((prev) => ({ ...prev, scope: e.target.value as NotificationsScopeFilter }))}>
              <option value="all">{t('app.reminders.scopes.all')}</option>
              <option value="direct">{t('app.reminders.scopes.direct')}</option>
            </select>
            <select className="input" value={eventsFilters.read} onChange={(e) => setEventsFilters((prev) => ({ ...prev, read: e.target.value as NotificationsReadFilter }))}>
              <option value="unread">{t('app.reminders.filters.unread')}</option>
              <option value="all">{t('app.reminders.filters.all')}</option>
            </select>
            <button type="button" className="btn-secondary btn-sm" onClick={() => void loadNotificationsFeed()}>
              {t('app.reminders.actions.refresh')}
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={() => void reconcileAndReloadNotificationsFeed()}>
              {t('app.reminders.actions.sync')}
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={markAllRead} disabled={markAllBusy || notificationCounts.unread === 0}>
              {markAllBusy ? t('common.loading') : t('app.reminders.actions.notifications_mark_all_read')}
            </button>
            </div>
          </Toolbar>

          <DataTableFrame
            className="min-h-0 flex-1"
            preScroll={
              notificationsState === 'error' && notificationsError ? (
                <div className="border-b border-slate-200/80 px-4 py-3">
                  <ErrorRecoveryBanner
                    compact
                    info={notificationsError}
                    onRetry={() => void reconcileAndReloadNotificationsFeed()}
                    retryLabel={t('common.retry')}
                    {...friendlyErrorBannerSecondary(
                      notificationsError,
                      CRM_APP_PATHS.inbox,
                      t('app.reminders.actions.open_comm'),
                    )}
                  />
                </div>
              ) : undefined
            }
            footer={t('app.reminders.events.count', {
              defaultValue: '{{count}} events',
              values: { count: visibleNotifications.length },
            })}
          >
            {notificationsState === 'loading' ? (
              <div className="px-4 py-6 text-sm text-slate-500">{t('common.loading')}</div>
            ) : null}

            {notificationsState !== 'loading' && visibleNotifications.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">
                {t('app.reminders.states.events_empty')}
              </div>
            ) : null}

            {visibleNotifications.length > 0 ? (
              <div className="space-y-2 p-4">
              {visibleNotifications.map((item) => {
                const createdAt = parseDate(item.created_at)
                const href = notificationEntityHref(item)
                const busy = notifBusyId === item.id
                const desc = notificationDescription(item)
                return (
                  <div
                    key={item.id}
                    className={clsx(
                      'rounded-xl border p-3 shadow-sm',
                      item.is_read ? 'border-slate-200 bg-white' : 'border-brand-200 bg-brand-50/30'
                    )}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          {!item.is_read && (
                            <span className="rounded-lg bg-brand-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                              {t('app.reminders.states.badge_new')}
                            </span>
                          )}
                          <span className="rounded-lg bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                            {item.event_type}
                          </span>
                        </div>
                        <p className="text-sm font-semibold text-slate-900">{notificationTitle(item)}</p>
                        {desc && <p className="text-xs text-slate-600">{desc}</p>}
                        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                          <span>{createdAt ? format(createdAt, 'dd MMM yyyy, HH:mm', { locale: dateLocale }) : '—'}</span>
                          <span>{createdAt ? formatDistanceToNow(createdAt, { addSuffix: true, locale: dateLocale }) : ''}</span>
                          {item.entity_type && <span>{item.entity_type}{item.entity_id ? `:${item.entity_id}` : ''}</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {href && (
                          <button
                            type="button"
                            className="btn-secondary btn-xs"
                            onClick={() => navigate(href)}
                          >
                            {t('app.reminders.actions.open_notification')}
                          </button>
                        )}
                        {!item.is_read && (
                          <button
                            type="button"
                            className="btn-secondary btn-xs"
                            onClick={() => void markOneRead(item.id)}
                            disabled={busy}
                          >
                            {busy ? t('common.loading') : t('app.reminders.actions.notifications_mark_read')}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
            ) : null}
          </DataTableFrame>
        </>
      )}
      </div>

      {editState && (() => {
        // G-7 stage 2: planner rows have no `remind_at` analogue.
        // Hide the remind-at input for them so the operator doesn't
        // think they can set a separate pre-event nudge.
        const editingSource = reminderRows.find((r) => r.id === editState.id)?._source ?? 'reminder'
        const isPlannerEdit = editingSource === 'planner'
        return (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="presentation"
          onClick={() => !editBusy && setEditState(null)}
          onKeyDown={(e) =>
            runActionOnSpaceEnter(e, () => {
              if (!editBusy) setEditState(null)
            })
          }
        >
          <div
            className="w-full max-w-xl rounded-xl border border-slate-200 bg-white p-4 shadow-xl"
            role="presentation"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => activateClickOnSpaceEnter(e, (ev) => ev.stopPropagation())}
          >
            <h3 className="text-lg font-semibold text-slate-900">
              {isPlannerEdit
                ? t('app.reminders.edit.title_planner', { defaultValue: 'Edit calendar event' })
                : t('app.reminders.edit.title')}
            </h3>
            <form onSubmit={submitEdit} className="mt-3 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600">{t('app.reminders.form.title')}</label>
                <input className="input mt-1 w-full" value={editState.title} onChange={(e) => setEditState((prev) => prev ? { ...prev, title: e.target.value } : prev)} required />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600">{t('app.reminders.form.description')}</label>
                <textarea className="textarea mt-1 w-full" rows={3} value={editState.description} onChange={(e) => setEditState((prev) => prev ? { ...prev, description: e.target.value } : prev)} />
              </div>
              <div className={isPlannerEdit ? 'grid gap-3' : 'grid gap-3 md:grid-cols-2'}>
                <div>
                  <label className="block text-xs font-medium text-slate-600">
                    {isPlannerEdit
                      ? t('app.reminders.form.due_planner', { defaultValue: 'Start' })
                      : t('app.reminders.form.due')}
                  </label>
                  <input type="datetime-local" className="input mt-1 w-full" value={editState.dueAtLocal} onChange={(e) => setEditState((prev) => prev ? { ...prev, dueAtLocal: e.target.value } : prev)} />
                </div>
                {!isPlannerEdit && (
                  <div>
                    <label className="block text-xs font-medium text-slate-600">{t('app.reminders.form.remind_at')}</label>
                    <input type="datetime-local" className="input mt-1 w-full" value={editState.remindAtLocal} onChange={(e) => setEditState((prev) => prev ? { ...prev, remindAtLocal: e.target.value } : prev)} />
                  </div>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600">{t('app.reminders.form.priority')}</label>
                <select className="input mt-1 w-full" value={editState.priority} onChange={(e) => setEditState((prev) => prev ? { ...prev, priority: e.target.value } : prev)}>
                  <option value="low">{t('app.reminders.priority.low')}</option>
                  <option value="normal">{t('app.reminders.priority.normal')}</option>
                  <option value="high">{t('app.reminders.priority.high')}</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setEditState(null)} disabled={editBusy}>
                  {t('common.actions.cancel')}
                </button>
                <button type="submit" className="btn-primary" disabled={editBusy}>
                  {editBusy ? t('common.loading') : t('common.actions.save')}
                </button>
              </div>
            </form>
          </div>
        </div>
        )
      })()}
    </PageShell>
  )
}
