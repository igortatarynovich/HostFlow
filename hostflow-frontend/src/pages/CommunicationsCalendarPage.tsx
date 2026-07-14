import clsx from 'clsx'
import { type ClipboardEvent, FormEvent, type KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import {
  completeActivity,
  createActivity,
  getActivity,
  listActivities,
  listManagers,
  snoozeActivity,
  updateActivity,
} from '../api/client'
import { ACTIVITY_TEMPLATES } from '../modules/candidates/activityTemplates'
import {
  createCommunicationPlannerEvent,
  getCommunicationPlannerEvent,
  getMyWorkingHours,
  getMyNotificationSettings,
  getCommunicationsSettings,
  listCommunicationPlannerEvents,
  listCommunicationTimeOffRequests,
  patchCommunicationPlannerEvent,
  upsertMyNotificationSettings,
  type CommunicationPlannerEvent,
  type NotificationSettings,
  type AvailabilityState,
  type CommunicationTimeOffRequest,
  type WorkingHoursSchedule,
} from '../api/communications'
import { cancelCalendarItem, listCalendarItems, patchCalendarItem, type CalendarItem as IntegratedCalendarItem } from '../api/calendarIntegrations'
import { useI18n } from '../i18n'
import { useCommunicationsAccess } from '../hooks/useCommunicationsAccess'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { useAuth } from '../store/useAuth'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { friendlyErrorBannerSecondary, friendlyFormHintError, getFriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'

type CalendarSourceFilter = 'all' | 'timeoff' | 'reminders' | 'planner' | 'integrated'
type TimeOffStatusFilter = 'approved' | 'pending' | 'all'
type ViewMode = 'month' | 'week' | 'day'
type PlannerRepeatMode = 'none' | 'daily' | 'weekdays'
type BatchSelectStatusFilter = '' | 'planned' | 'in_progress' | 'done' | 'cancelled'
type WeekSlotMinutes = 15 | 30 | 60
type TaskKind = 'task' | 'followup' | 'call'
type EventModalParticipant = { id: string; name: string; email: string; response_status: '' | 'accepted' | 'tentative' | 'declined' }

/**
 * Phase 2.1 canary calendar-worthy whitelist (FE-only, surgical).
 *
 * An Activity row appears in the calendar grid only if BOTH:
 *   - it has a parseable start (callers enforce this separately), AND
 *   - it carries explicit calendar intent:
 *       * type === 'meeting'                              (intrinsic calendar shape)
 *       * payload.planner.kind IN ('meeting', 'shift')    (planner UI semantic)
 *       * payload.calendar_visible === true               (explicit user opt-in)
 *
 * `type === 'call'` is intentionally NOT in this set — auto-generated lead/lifecycle
 * calls cannot be reliably distinguished from user-scheduled calls today. A user
 * who creates a call via the calendar UI still passes through because every
 * calendar-UI write path sets `payload.calendar_visible = true`.
 *
 * Excluded by design (these continue to surface in MyTasksPanel / WorkHub):
 *   - UOS auto-rows (type starts with `uos_*`)
 *   - scheduler SLA rows (leads_no_next_action / leads_stuck_stage / invoice_overdue_payment / communications_sla_overdue)
 *   - automation-rule rows (type='custom' without calendar markers)
 *   - document deadlines (document_expiry / document_workflow_step)
 *   - any auto-created operational activity without scheduled intent
 *
 * See plan: phase_2.1_calendar_worthy_filter.
 */
function isCalendarWorthyActivity(input: {
  type: unknown
  payload?: unknown
}): boolean {
  const type = String(input?.type || '').toLowerCase()
  const payload =
    input?.payload && typeof input.payload === 'object' && !Array.isArray(input.payload)
      ? (input.payload as Record<string, any>)
      : {}
  const plannerKind = String(payload?.planner?.kind || '').toLowerCase()
  const calendarVisible = payload?.calendar_visible === true
  if (calendarVisible) return true
  if (type === 'meeting') return true
  if (plannerKind === 'meeting' || plannerKind === 'shift') return true
  return false
}

function normalizeParticipantEmail(email: string): string {
  return String(email || '').trim().toLowerCase()
}

function isValidParticipantEmail(email: string): boolean {
  const s = String(email || '').trim()
  if (!s || s.length > 254) return false
  // Pragmatic RFC5322-ish check (good enough for UI validation)
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)
}

/** Extract likely emails from pasted text (handles comma / semicolon / newline lists). */
function extractEmailsFromClipboardText(text: string): string[] {
  const raw = String(text || '')
  const tokenRe = /[^\s,;<>\r\n]+@[^\s,;<>\r\n]+/g
  const tokens = raw.match(tokenRe) || []
  const seen = new Set<string>()
  const out: string[] = []
  for (let t of tokens) {
    t = t.replace(/^[<(]+/, '').replace(/[)>.,;:]+$/, '').trim()
    if (!isValidParticipantEmail(t)) continue
    const k = normalizeParticipantEmail(t)
    if (seen.has(k)) continue
    seen.add(k)
    out.push(t)
  }
  return out
}

function dedupeParticipants(rows: EventModalParticipant[]): EventModalParticipant[] {
  const seen = new Set<string>()
  const out: EventModalParticipant[] = []
  for (const row of rows) {
    const key = normalizeParticipantEmail(row.email)
    if (!key) {
      out.push(row)
      continue
    }
    if (seen.has(key)) continue
    seen.add(key)
    out.push(row)
  }
  return out
}

function mergeBulkEmailsAtRow(prev: EventModalParticipant[], rowId: string, emails: string[]): EventModalParticipant[] {
  const cleaned = emails.map((e) => e.trim()).filter((e) => isValidParticipantEmail(e))
  if (cleaned.length === 0) return prev
  const idx = prev.findIndex((r) => r.id === rowId)
  if (idx === -1) {
    const additions = cleaned.map((email, i) => ({
      id: `p-paste-${Date.now()}-${i}-${normalizeParticipantEmail(email)}`,
      name: '',
      email,
      response_status: '' as const,
    }))
    return dedupeParticipants([...prev, ...additions])
  }
  const row = prev[idx]
  const first = cleaned[0]
  const rest = cleaned.slice(1)
  const updatedFirst: EventModalParticipant = { ...row, email: first }
  const inserted = rest.map((email, i) => ({
    id: `p-paste-${Date.now()}-${idx}-${i}-${normalizeParticipantEmail(email)}`,
    name: '',
    email,
    response_status: '' as const,
  }))
  return dedupeParticipants([...prev.slice(0, idx), updatedFirst, ...inserted, ...prev.slice(idx + 1)])
}

const CALENDAR_BATCH_STORAGE_KEY = 'hf:calendar:batch:v1'
const CALENDAR_UI_STORAGE_KEY = 'hf:calendar:ui:v2'
const CALENDAR_TASK_PREFS_STORAGE_KEY = 'hf:calendar:task-prefs:v1'
const TASK_KIND_OPTIONS: Array<{ value: TaskKind; label: string }> = [
  { value: 'task', label: 'Task' },
  { value: 'followup', label: 'Follow-up' },
  { value: 'call', label: 'Call' },
]
const DEFAULT_NOTIFICATION_SETTINGS: NotificationSettings = {
  default_reminder_minutes: 30,
  channels: { in_app: true, push: true, email: false },
  quiet_hours_enabled: false,
  quiet_hours_start: '22:00',
  quiet_hours_end: '08:00',
  timezone: 'UTC',
}

function readTaskPrefs(): { defaultTaskKind: TaskKind; defaultRemindMinutes: number } {
  if (typeof window === 'undefined') return { defaultTaskKind: 'task', defaultRemindMinutes: 30 }
  try {
    const raw = window.localStorage.getItem(CALENDAR_TASK_PREFS_STORAGE_KEY)
    if (!raw) return { defaultTaskKind: 'task', defaultRemindMinutes: 30 }
    const p = JSON.parse(raw) as { defaultTaskKind?: string; defaultRemindMinutes?: number }
    const defaultTaskKind: TaskKind = ['task', 'followup', 'call'].includes(String(p.defaultTaskKind || ''))
      ? (p.defaultTaskKind as TaskKind)
      : 'task'
    const mins = Number(p.defaultRemindMinutes)
    const defaultRemindMinutes = [0, 5, 10, 15, 30, 60].includes(mins) ? mins : 30
    return { defaultTaskKind, defaultRemindMinutes }
  } catch {
    return { defaultTaskKind: 'task', defaultRemindMinutes: 30 }
  }
}

function readInitialCalendarUi(): { source: CalendarSourceFilter; view: ViewMode } {
  if (typeof window === 'undefined') return { source: 'all', view: 'month' }
  try {
    const raw = window.localStorage.getItem(CALENDAR_UI_STORAGE_KEY)
    if (!raw) return { source: 'all', view: 'month' }
    const p = JSON.parse(raw) as { sourceFilter?: string; viewMode?: string }
    const source: CalendarSourceFilter =
      p.sourceFilter === 'all' || p.sourceFilter === 'timeoff' || p.sourceFilter === 'reminders' || p.sourceFilter === 'planner' || p.sourceFilter === 'integrated'
        ? p.sourceFilter
        : 'all'
    const view: ViewMode =
      p.viewMode === 'month' || p.viewMode === 'week' || p.viewMode === 'day' ? p.viewMode : 'month'
    return { source, view }
  } catch {
    return { source: 'all', view: 'month' }
  }
}

type UnifiedCalendarEvent = {
  id: string
  dateKey: string
  source: 'timeoff' | 'reminder' | 'planner' | 'integrated'
  status: 'approved' | 'pending' | 'overdue' | 'due' | 'info'
  title: string
  subtitle?: string
  detail?: string
  at?: string | null
  endAt?: string | null
  entityPath?: string | null
  assigneeId?: string | null
  kind?: string | null
  priority?: string | null
  plannerId?: string | null
  reminderId?: string | null
  plannerStatus?: string | null
  reminderStatus?: string | null
  integratedItemId?: string | null
  tags?: string[]
}

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

function addDays(d: Date, days: number): Date {
  const x = new Date(d)
  x.setDate(x.getDate() + days)
  return x
}

function addWeekdays(base: Date, weekdaysToAdd: number): Date {
  const d = new Date(base)
  if (weekdaysToAdd <= 0) return d
  let left = weekdaysToAdd
  while (left > 0) {
    d.setDate(d.getDate() + 1)
    const wd = d.getDay()
    if (wd !== 0 && wd !== 6) left -= 1
  }
  return d
}

function startOfWeek(d: Date): Date {
  const base = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const weekday = (base.getDay() + 6) % 7
  return addDays(base, -weekday)
}

function dateIso(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function parseDate(value?: string | null): Date | null {
  if (!value) return null
  const ts = Date.parse(value)
  return Number.isNaN(ts) ? null : new Date(ts)
}

function formatDateTime(value?: string | null): string {
  const d = parseDate(value)
  if (!d) return '—'
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
}

function formatDayLabel(value: string): string {
  const d = parseDate(`${value}T00:00:00Z`)
  if (!d) return value
  return new Intl.DateTimeFormat(undefined, { year: 'numeric', month: '2-digit', day: '2-digit' }).format(d)
}

function toLocalInput(dt?: string | null): string {
  if (!dt) return ''
  const d = new Date(dt)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function localDayKeyFromDate(value: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
}

function parseClockMinutes(value?: string | null): number | null {
  if (!value || !/^\d{1,2}:\d{2}$/.test(value)) return null
  const [h, m] = value.split(':').map((x) => Number(x))
  if (!Number.isFinite(h) || !Number.isFinite(m) || h < 0 || h > 23 || m < 0 || m > 59) return null
  return h * 60 + m
}

function toDayBounds(dayKey: string): { start: Date; end: Date } {
  const start = new Date(`${dayKey}T00:00:00`)
  const end = new Date(`${dayKey}T23:59:59.999`)
  return { start, end }
}

function buildEventInterval(start: Date, end?: Date | null, allDay = false): { start: Date; end: Date } {
  if (allDay) {
    const dayStart = new Date(start)
    dayStart.setHours(0, 0, 0, 0)
    const dayEnd = new Date(dayStart)
    dayEnd.setHours(23, 59, 59, 999)
    return { start: dayStart, end: dayEnd }
  }
  const safeEnd = end && end > start ? end : new Date(start.getTime() + 60 * 60_000)
  return { start, end: safeEnd }
}

function rangesOverlap(startA: Date, endA: Date, startB: Date, endB: Date): boolean {
  return startA < endB && startB < endA
}

function enumerateDayKeys(start: Date, end: Date): string[] {
  const out: string[] = []
  const cur = new Date(start)
  cur.setHours(0, 0, 0, 0)
  const last = new Date(end)
  last.setHours(0, 0, 0, 0)
  while (cur <= last) {
    out.push(localDayKeyFromDate(cur))
    cur.setDate(cur.getDate() + 1)
  }
  return out
}

function weekSlotStart(slotIndex: number, slotMinutes: WeekSlotMinutes): { hour: number; minute: number } {
  const total = slotIndex * slotMinutes
  const hour = Math.floor(total / 60)
  const minute = total % 60
  return { hour, minute }
}

/** One day on the hour grid (0–24h) in local time. */
const CALENDAR_DAY_MINUTES = 24 * 60
/** Week / day timeline row height — must match column layout math. */
const CALENDAR_TIMELINE_SLOT_PX = 44

/**
 * Top + height as % of a single-day column (00:00–24:00 local).
 * When ``endAt`` is missing, default duration is 60m. Enforces ``minDurationMinutes``
 * for visible height. Returns null if times are unusable (never emits NaN %).
 */
function eventTimelinePercents(
  event: UnifiedCalendarEvent,
  minDurationMinutes: number,
): { topPct: number; heightPct: number } | null {
  const minDur =
    Number.isFinite(minDurationMinutes) && minDurationMinutes > 0 ? minDurationMinutes : 30

  const start = parseDate(event.at || null)
  if (!start || !Number.isFinite(start.getTime())) return null

  const dayStart = new Date(start.getFullYear(), start.getMonth(), start.getDate())
  const dayStartMs = dayStart.getTime()
  if (!Number.isFinite(dayStartMs)) return null

  const startMinRaw = (start.getTime() - dayStartMs) / 60_000
  if (!Number.isFinite(startMinRaw)) return null
  if (startMinRaw < 0 || startMinRaw >= CALENDAR_DAY_MINUTES) return null
  const startMin = startMinRaw

  let endMin: number
  const endParsed = parseDate(event.endAt || null)
  if (endParsed && Number.isFinite(endParsed.getTime())) {
    endMin = (endParsed.getTime() - dayStartMs) / 60_000
    if (!Number.isFinite(endMin)) {
      endMin = startMin + 60
    }
  } else {
    endMin = startMin + 60
  }
  if (!Number.isFinite(endMin) || endMin <= startMin) {
    endMin = startMin + 60
  }
  endMin = Math.min(Math.max(endMin, startMin + minDur), CALENDAR_DAY_MINUTES)
  const durMin = Math.max(endMin - startMin, minDur)

  const topPct = (startMin / CALENDAR_DAY_MINUTES) * 100
  const heightPct = (durMin / CALENDAR_DAY_MINUTES) * 100

  if (!Number.isFinite(topPct) || !Number.isFinite(heightPct) || heightPct <= 0) {
    return null
  }

  return { topPct, heightPct }
}

/** Pointer Y inside ``columnHeightPx`` → snapped start minute-of-day. */
function minuteFromTimelinePointer(
  clientY: number,
  columnTop: number,
  columnHeightPx: number,
  slotMinutes: WeekSlotMinutes,
): number {
  if (columnHeightPx <= 0) return 0
  const y = Math.max(0, Math.min(columnHeightPx - 1, clientY - columnTop))
  const raw = (y / columnHeightPx) * CALENDAR_DAY_MINUTES
  const snapped = Math.floor(raw / slotMinutes) * slotMinutes
  return Math.max(0, Math.min(CALENDAR_DAY_MINUTES - slotMinutes, snapped))
}

function sourceBadgeClass(source: UnifiedCalendarEvent['source']): string {
  if (source === 'timeoff') return 'bg-rose-100 text-rose-800'
  if (source === 'reminder') return 'bg-amber-100 text-amber-800'
  if (source === 'integrated') return 'bg-blue-100 text-blue-800'
  return 'bg-blue-100 text-blue-800'
}

function statusBadgeClass(status: UnifiedCalendarEvent['status']): string {
  if (status === 'approved') return 'bg-emerald-100 text-emerald-800'
  if (status === 'pending') return 'bg-amber-100 text-amber-800'
  if (status === 'overdue') return 'bg-rose-100 text-rose-800'
  if (status === 'due') return 'bg-blue-100 text-blue-800'
  return 'bg-slate-100 text-slate-700'
}

function reminderLink(rem: any): string | null {
  if (rem?.entity_type === 'candidate' && rem?.entity_id)
    return `${CRM_APP_PATHS.candidates}/${rem.entity_id}`
  if (rem?.entity_type === 'company' && rem?.entity_id)
    return `${CRM_APP_PATHS.agencyClients}/${rem.entity_id}`
  return null
}

function timeOffTimeWindowText(row: CommunicationTimeOffRequest): string {
  const from = row.payload?.time_window?.from
  const to = row.payload?.time_window?.to
  if (!from || !to) return ''
  return `${from}-${to}`
}

function plannerKindTone(kind?: string | null): string {
  const k = String(kind || '').toLowerCase()
  if (k === 'meeting') return 'bg-blue-50 text-blue-700 border-blue-200'
  if (k === 'call') return 'bg-blue-50 text-blue-700 border-blue-200'
  if (k === 'task' || k === 'followup') return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  return 'bg-slate-50 text-slate-700 border-slate-200'
}

export default function CommunicationsCalendarPage(props: { embedded?: boolean } = {}) {
  const embedded = Boolean(props.embedded)
  const { t } = useI18n()
  const { me } = useAuth()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const planLimitModal = usePlanLimitModal()

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [calendarError, setCalendarError] = useState<FriendlyErrorInfo | null>(null)
  const [infoText, setInfoText] = useState<string | null>(null)
  // Auto-clear transient toast banners (saved / cancelled / completed) after 4s so
  // they don't stick across navigation. Manually-cleared messages still work.
  useEffect(() => {
    if (!infoText) return
    const handle = window.setTimeout(() => setInfoText(null), 4000)
    return () => window.clearTimeout(handle)
  }, [infoText])
  const [nowTs, setNowTs] = useState<number>(() => Date.now())

  const [timeOffRows, setTimeOffRows] = useState<CommunicationTimeOffRequest[]>([])
  const [reminders, setReminders] = useState<any[]>([])
  const [plannerEvents, setPlannerEvents] = useState<CommunicationPlannerEvent[]>([])
  const [integratedCalendarItems, setIntegratedCalendarItems] = useState<IntegratedCalendarItem[]>([])
  /** When ``?event_id=`` points to a planner row outside the default list window, fetch merges here (G-6). */
  const [focusInjectPlanner, setFocusInjectPlanner] = useState<CommunicationPlannerEvent | null>(null)
  /** Same for reminders/activities resolved by UUID. */
  const [focusInjectReminder, setFocusInjectReminder] = useState<Record<string, unknown> | null>(null)
  const [labels, setLabels] = useState<Map<string, string>>(new Map())
  const [managers, setManagers] = useState<Array<{ id: string; label: string }>>([])

  const [monthCursor, setMonthCursor] = useState<Date>(() => startOfMonth(new Date()))
  const [selectedDay, setSelectedDay] = useState<string>(() => localDayKeyFromDate(new Date()))
  const [weekCursor, setWeekCursor] = useState<Date>(() => startOfWeek(new Date()))
  const [statusFilter, setStatusFilter] = useState<TimeOffStatusFilter>('approved')
  const [sourceFilter, setSourceFilter] = useState<CalendarSourceFilter>(() => readInitialCalendarUi().source)
  const [assigneeFilter, setAssigneeFilter] = useState('')
  const [activityTypeFilter, setActivityTypeFilter] = useState('')
  const [plannerKindFilter, setPlannerKindFilter] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>(() => readInitialCalendarUi().view)
  const [showAdvancedTools, setShowAdvancedTools] = useState(false)
  const [eventModalOpen, setEventModalOpen] = useState(false)
  const [eventModalEvent, setEventModalEvent] = useState<UnifiedCalendarEvent | null>(null)
  const [eventModalType, setEventModalType] = useState<'meeting' | 'task'>('task')
  const [eventModalTitle, setEventModalTitle] = useState('')
  const [eventModalKind, setEventModalKind] = useState('meeting')
  const [eventModalStartAt, setEventModalStartAt] = useState(toLocalInput(new Date(Date.now() + 30 * 60_000).toISOString()))
  const [eventModalEndAt, setEventModalEndAt] = useState(toLocalInput(new Date(Date.now() + 90 * 60_000).toISOString()))
  const [eventModalAllDay, setEventModalAllDay] = useState(false)
  const [eventModalDescription, setEventModalDescription] = useState('')
  const [eventModalLocation, setEventModalLocation] = useState('')
  const [eventModalParticipants, setEventModalParticipants] = useState<EventModalParticipant[]>([])
  const [eventModalParticipantErrors, setEventModalParticipantErrors] = useState<Record<string, string>>({})
  const [eventModalMeetingLink, setEventModalMeetingLink] = useState('')
  const [eventModalOnlineMeeting, setEventModalOnlineMeeting] = useState(false)
  const [eventModalAssigneeId, setEventModalAssigneeId] = useState('')
  const [taskPrefs, setTaskPrefs] = useState(() => readTaskPrefs())
  const [eventModalRemindMinutes, setEventModalRemindMinutes] = useState(() => readTaskPrefs().defaultRemindMinutes)
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>(DEFAULT_NOTIFICATION_SETTINGS)
  const [notificationSettingsSaving, setNotificationSettingsSaving] = useState(false)
  const [teamStateByManager, setTeamStateByManager] = useState<Record<string, AvailabilityState>>({})
  const [eventModalAllowUnavailableAssignee, setEventModalAllowUnavailableAssignee] = useState(false)
  const [dragPlannerEvent, setDragPlannerEvent] = useState<UnifiedCalendarEvent | null>(null)
  const [resizePlannerEvent, setResizePlannerEvent] = useState<UnifiedCalendarEvent | null>(null)
  const [activePlannerMenuId, setActivePlannerMenuId] = useState<string | null>(null)
  const [selectedPlannerIds, setSelectedPlannerIds] = useState<string[]>([])
  const [batchAssigneeId, setBatchAssigneeId] = useState('')
  const [batchTagValue, setBatchTagValue] = useState('')
  const [batchSelectKind, setBatchSelectKind] = useState('')
  const [batchSelectPriority, setBatchSelectPriority] = useState('')
  const [batchSelectStatus, setBatchSelectStatus] = useState<BatchSelectStatusFilter>('')
  const [weekSlotMinutes, setWeekSlotMinutes] = useState<WeekSlotMinutes>(30)
  const [workingHours, setWorkingHours] = useState<WorkingHoursSchedule | null>(null)
  const [allowOutsideHours, setAllowOutsideHours] = useState(false)

  const [searchParams, setSearchParams] = useSearchParams()
  const deepLinkHandledRef = useRef<string | null>(null)
  const deepLinkFetchAttemptRef = useRef<string | null>(null)
  const [highlightUnifiedId, setHighlightUnifiedId] = useState<string | null>(null)
  const managerLabelWithState = useCallback(
    (managerId: string, fallbackLabel: string) => {
      const state = teamStateByManager[String(managerId)] || 'available'
      return state === 'available' ? fallbackLabel : `${fallbackLabel} (${state})`
    },
    [teamStateByManager],
  )

  const [plannerForm, setPlannerForm] = useState({
    title: '',
    kind: 'meeting',
    priority: 'normal',
    assigneeId: '',
    startAt: toLocalInput(new Date(Date.now() + 30 * 60_000).toISOString()),
    endAt: toLocalInput(new Date(Date.now() + 90 * 60_000).toISOString()),
    allDay: false,
    repeatMode: 'none' as PlannerRepeatMode,
    repeatCount: 1,
    description: '',
  })

  const [reminderForm, setReminderForm] = useState({
    title: '',
    type: 'custom',
    dueAt: toLocalInput(new Date(Date.now() + 2 * 60 * 60_000).toISOString()),
    offsetMinutes: 30,
    assigneeId: '',
    priority: 'normal',
    description: '',
  })

  const load = useCallback(async () => {
    setLoading(true)
    setCalendarError(null)
    try {
      const needTimeoff = sourceFilter === 'all' || sourceFilter === 'timeoff'
      const needActivities = sourceFilter === 'all' || sourceFilter === 'reminders'
      const needPlanner = sourceFilter === 'all' || sourceFilter === 'planner'
      const needIntegrated = sourceFilter === 'all' || sourceFilter === 'integrated'

      const range =
        viewMode === 'day'
          ? toDayBounds(selectedDay)
          : viewMode === 'week'
            ? (() => {
                const start = new Date(weekCursor)
                start.setHours(0, 0, 0, 0)
                const end = addDays(start, 6)
                end.setHours(23, 59, 59, 999)
                return { start, end }
              })()
            : (() => {
                const start = monthMeta.days[0] ? new Date(monthMeta.days[0]) : new Date(monthCursor)
                const end = monthMeta.days[monthMeta.days.length - 1]
                  ? new Date(monthMeta.days[monthMeta.days.length - 1])
                  : addDays(start, 41)
                start.setHours(0, 0, 0, 0)
                end.setHours(23, 59, 59, 999)
                return { start, end }
              })()

      const [timeOffRes, remRes, plannerRes, integratedRes, mgrs, wh, notif, commSettings] = await Promise.all([
        needTimeoff
          ? listCommunicationTimeOffRequests({
              limit: 500,
              status_filter: statusFilter === 'all' ? undefined : [statusFilter],
            })
          : Promise.resolve({ items: [] } as any),
        needActivities
          ? listActivities({
              dueFrom: range.start.toISOString(),
              dueTo: range.end.toISOString(),
              assigneeId: assigneeFilter || undefined,
              types: activityTypeFilter ? [activityTypeFilter] : undefined,
            }).catch(() => ({ items: [] }))
          : Promise.resolve({ items: [] } as any),
        needPlanner
          ? listCommunicationPlannerEvents({ limit: 200 }).catch(() => ({ items: [] }))
          : Promise.resolve({ items: [] } as any),
        needIntegrated
          ? listCalendarItems({
              start: range.start.toISOString(),
              end: range.end.toISOString(),
            }).catch(() => [] as IntegratedCalendarItem[])
          : Promise.resolve([] as IntegratedCalendarItem[]),
        listManagers().catch(() => []),
        getMyWorkingHours().catch(() => null),
        getMyNotificationSettings().catch(() => DEFAULT_NOTIFICATION_SETTINGS),
        getCommunicationsSettings().catch(() => null),
      ])
      const normalizedManagers = (Array.isArray(mgrs) ? mgrs : []).map((m: any) => ({ id: String(m.id), label: String(m.label || m.full_name || m.email || m.id) }))
      setManagers(normalizedManagers)
      setLabels(new Map(normalizedManagers.map((m) => [m.id, m.label])))

      setTimeOffRows(Array.isArray(timeOffRes.items) ? timeOffRes.items : [])
      setReminders(Array.isArray((remRes as any)?.items) ? (remRes as any).items : [])
      setPlannerEvents(Array.isArray(plannerRes?.items) ? plannerRes.items : [])
      setIntegratedCalendarItems(Array.isArray(integratedRes) ? integratedRes : [])
      if (wh) setWorkingHours(wh)
      setNotificationSettings({ ...DEFAULT_NOTIFICATION_SETTINGS, ...(notif || {}) })
      const queueItems = Array.isArray((commSettings as any)?.managerQueue?.items) ? (commSettings as any).managerQueue.items : []
      const nextStateMap: Record<string, AvailabilityState> = {}
      for (const raw of queueItems) {
        if (!raw || typeof raw !== 'object') continue
        const mid = String((raw as any).managerId || '').trim()
        if (!mid) continue
        const st = String((raw as any)?.availability?.state || 'available').trim().toLowerCase()
        if (st === 'available' || st === 'busy' || st === 'offline' || st === 'break' || st === 'meeting') {
          nextStateMap[mid] = st as AvailabilityState
        }
      }
      setTeamStateByManager(nextStateMap)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.load_failed', { defaultValue: 'Failed to load calendar data' }),
        )
      ) {
        setCalendarError(getFriendlyErrorInfo(err, t('app.communications.calendar.errors.load_failed', { defaultValue: 'Failed to load calendar data' }), t))
      }
    } finally {
      setLoading(false)
    }
  }, [activityTypeFilter, assigneeFilter, monthCursor, planLimitModal, selectedDay, sourceFilter, statusFilter, t, viewMode, weekCursor])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const timer = window.setInterval(() => setNowTs(Date.now()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    // Keep calendar predictable: start from visible "all sources" state.
    setSourceFilter('all')
    setAssigneeFilter('')
    setStatusFilter('all')
  }, [])

  useEffect(() => {
    try {
      window.localStorage.setItem(
        CALENDAR_UI_STORAGE_KEY,
        JSON.stringify({ sourceFilter, viewMode }),
      )
    } catch {
      // ignore
    }
  }, [sourceFilter, viewMode])

  useEffect(() => {
    try {
      window.localStorage.setItem(CALENDAR_TASK_PREFS_STORAGE_KEY, JSON.stringify(taskPrefs))
    } catch {
      // ignore
    }
  }, [taskPrefs])

  useEffect(() => {
    const mins = Number(notificationSettings.default_reminder_minutes || 0)
    if (![0, 5, 10, 15, 30, 60].includes(mins)) return
    setTaskPrefs((prev) => ({ ...prev, defaultRemindMinutes: mins }))
  }, [notificationSettings.default_reminder_minutes])

  useEffect(() => {
    if (!embedded) return
    setSourceFilter('all')
  }, [embedded])

  const monthMeta = useMemo(() => {
    const start = startOfMonth(monthCursor)
    const firstWeekday = (start.getDay() + 6) % 7
    const gridStart = addDays(start, -firstWeekday)
    return {
      start,
      title: new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(start),
      days: Array.from({ length: 42 }).map((_, i) => addDays(gridStart, i)),
    }
  }, [monthCursor])

  const plannerEventsEffective = useMemo(() => {
    if (!focusInjectPlanner) return plannerEvents
    const byId = new Map(plannerEvents.map((e) => [e.id, e]))
    byId.set(focusInjectPlanner.id, focusInjectPlanner)
    return Array.from(byId.values())
  }, [plannerEvents, focusInjectPlanner])

  const remindersEffective = useMemo(() => {
    if (!focusInjectReminder) return reminders
    const byId = new Map(reminders.map((r: any) => [String(r.id), r]))
    byId.set(String(focusInjectReminder.id), focusInjectReminder as any)
    return Array.from(byId.values())
  }, [reminders, focusInjectReminder])

  const unifiedEvents = useMemo<UnifiedCalendarEvent[]>(() => {
    const nowTs = Date.now()
    const events: UnifiedCalendarEvent[] = []
    /** Same Activity rows are returned by ``listActivities`` and ``listCommunicationPlannerEvents`` when loading ``sourceFilter=all``. Prefer the planner projection so ``plannerId`` / duration stay canonical. */
    const plannerActivityIds = new Set(
      plannerEventsEffective.map((pe) => String(pe.id || '').trim()).filter(Boolean),
    )

    for (const row of timeOffRows) {
      if (!row.start_date || !row.end_date) continue
      let cur = parseDate(`${row.start_date}T00:00:00Z`)
      const end = parseDate(`${row.end_date}T00:00:00Z`)
      if (!cur || !end) continue
      while (cur <= end) {
        events.push({
          id: `timeoff:${row.id}:${localDayKeyFromDate(cur)}`,
          dateKey: localDayKeyFromDate(cur),
          source: 'timeoff',
          status: row.status === 'approved' ? 'approved' : 'pending',
          title: labels.get(String(row.requester_user_id)) || row.requester_label || row.requester_user_id,
          subtitle: `${row.request_type}${row.partial_day ? ` · ${row.partial_day}` : ''}${timeOffTimeWindowText(row) ? ` · ${timeOffTimeWindowText(row)}` : ''}`,
          detail: row.reason || undefined,
          at: null,
          assigneeId: row.requester_user_id,
        })
        cur = addDays(cur, 1)
      }
    }

    for (const rem of remindersEffective) {
      const rid = String(rem?.id || '').trim()
      if (rid && plannerActivityIds.has(rid)) continue
      const rawStart =
        (rem as any)?.starts_at ?? (rem as any)?.startsAt ?? rem?.due_at ?? rem?.remind_at ?? null
      const dueAt = rawStart
      const dt = parseDate(dueAt)
      if (!dt) continue
      const status = String(rem?.status || '').toLowerCase()
      // Hide terminal states from calendar view (matches integrated-source behaviour below).
      // Cancelled / completed events should leave the timeline once the action lands.
      if (['cancelled', 'canceled', 'deleted', 'done', 'completed'].includes(status)) continue
      // Phase 2.1 calendar-worthy whitelist: only show Activities with explicit
      // calendar intent (meeting / planner.kind / calendar_visible). System-suggested
      // operational tasks (UOS, SLA, automation, doc-deadlines) still appear in
      // MyTasksPanel / WorkHub but stay off the calendar grid.
      if (!isCalendarWorthyActivity({ type: (rem as any)?.type, payload: (rem as any)?.payload })) continue
      const sourceStatus: UnifiedCalendarEvent['status'] = status === 'overdue' || dt.getTime() < nowTs ? 'overdue' : 'due'
      events.push({
        id: `rem:${String(rem?.id || '')}:${String(dueAt)}`,
        reminderId: String(rem?.id || ''),
        reminderStatus: rem?.status ? String(rem.status) : null,
        dateKey: localDayKeyFromDate(dt),
        source: 'reminder',
        status: sourceStatus,
        title: String(rem?.title || t('app.candidate_card.reminders.untitled', { defaultValue: 'Untitled' })),
        subtitle: rem?.assignee_id
          ? t('app.communications.calendar.labels.assignee_with_value', {
              defaultValue: 'assignee: {value}',
              values: { value: labels.get(String(rem.assignee_id)) || String(rem.assignee_id) },
            })
          : t('app.communications.calendar.labels.assignee_empty', { defaultValue: 'assignee: —' }),
        detail: rem?.description || undefined,
        at: dueAt,
        endAt: null,
        entityPath: reminderLink(rem),
        assigneeId: rem?.assignee_id ? String(rem.assignee_id) : null,
        kind: rem?.type ? String(rem.type) : null,
        priority: rem?.priority ? String(rem.priority) : 'normal',
      })
    }

    for (const pe of plannerEventsEffective) {
      const dt = parseDate(pe.start_at)
      if (!dt) continue
      const s = String(pe.status || '').toLowerCase()
      // Hide terminal states from calendar view (matches integrated-source behaviour below).
      if (['cancelled', 'canceled', 'deleted', 'done', 'completed'].includes(s)) continue
      // Phase 2.1 calendar-worthy whitelist applied to planner-projected rows too:
      // the planner shim maps Activity.type -> pe.kind and forwards Activity.payload,
      // so the same gate keeps system-suggested rows out of the planner timeline.
      if (!isCalendarWorthyActivity({ type: pe.kind, payload: pe.payload })) continue
      events.push({
        id: `planner:${pe.id}:${pe.start_at}`,
        plannerId: pe.id,
        plannerStatus: String(pe.status || ''),
        dateKey: localDayKeyFromDate(dt),
        source: 'planner',
        status: s === 'done' || s === 'cancelled' ? 'info' : 'due',
        title: pe.title,
        subtitle: `${pe.kind} · ${pe.status}${pe.assignee_id ? ` · ${labels.get(String(pe.assignee_id)) || pe.assignee_id}` : ''}`,
        detail: pe.description || undefined,
        at: pe.start_at,
        endAt: pe.end_at,
        assigneeId: pe.assignee_id ? String(pe.assignee_id) : null,
        kind: pe.kind,
        priority: pe.priority,
        tags: Array.isArray(pe.payload?.tags) ? pe.payload.tags.filter((x: any) => typeof x === 'string') : [],
      })
    }

    for (const ci of integratedCalendarItems) {
      const fromPlannerBridge = String((ci.payload as any)?.created_from || '') === 'communications_planner'
      if (fromPlannerBridge) continue
      const dt = parseDate(ci.starts_at)
      if (!dt) continue
      const statusRaw = String(ci.status || '').toLowerCase()
      if (['cancelled', 'canceled', 'deleted', 'done', 'completed'].includes(statusRaw)) continue
      events.push({
        id: `integrated:${ci.id}:${ci.starts_at}`,
        integratedItemId: ci.id,
        dateKey: localDayKeyFromDate(dt),
        source: 'integrated',
        status: statusRaw === 'cancelled' ? 'info' : 'due',
        title: ci.title || t('app.candidate_card.reminders.untitled', { defaultValue: 'Untitled' }),
        subtitle: `${ci.kind || 'event'} · ${ci.source || 'calendar'}`,
        detail: ci.description || undefined,
        at: ci.starts_at,
        endAt: ci.ends_at || null,
        assigneeId: ci.assignee_id ? String(ci.assignee_id) : null,
        kind: ci.kind || 'event',
      })
    }

    return events.sort((a, b) => {
      const ad = a.at || `${a.dateKey}T00:00:00`
      const bd = b.at || `${b.dateKey}T00:00:00`
      return ad.localeCompare(bd) || a.title.localeCompare(b.title)
    })
  }, [integratedCalendarItems, labels, plannerEventsEffective, remindersEffective, t, timeOffRows])

  const filteredEvents = useMemo(() => {
    return unifiedEvents.filter((e) => {
      if (sourceFilter === 'timeoff' && e.source !== 'timeoff') return false
      if (sourceFilter === 'reminders' && e.source !== 'reminder') return false
      if (sourceFilter === 'planner' && e.source !== 'planner') return false
      if (sourceFilter === 'integrated' && e.source !== 'integrated') return false
      if (assigneeFilter && String(e.assigneeId || '') !== assigneeFilter) return false
      if (activityTypeFilter && e.source === 'reminder' && String(e.kind || '') !== activityTypeFilter) return false
      if (plannerKindFilter && e.source === 'planner' && String(e.kind || '') !== plannerKindFilter) return false
      return true
    })
  }, [activityTypeFilter, assigneeFilter, plannerKindFilter, sourceFilter, unifiedEvents])

  const eventsByDay = useMemo(() => {
    const map = new Map<string, UnifiedCalendarEvent[]>()
    for (const e of filteredEvents) {
      if (!map.has(e.dateKey)) map.set(e.dateKey, [])
      map.get(e.dateKey)!.push(e)
    }
    return map
  }, [filteredEvents])

  const selectedEvents = useMemo(
    () => (eventsByDay.get(selectedDay) || []).slice().sort((a, b) => String(a.at || '').localeCompare(String(b.at || ''))),
    [eventsByDay, selectedDay],
  )
  const plannerById = useMemo(() => {
    return new Map(plannerEventsEffective.map((x) => [x.id, x]))
  }, [plannerEventsEffective])

  const weekDays = useMemo(() => {
    return Array.from({ length: 7 }).map((_, i) => addDays(weekCursor, i))
  }, [weekCursor])
  const nowMeta = useMemo(() => {
    const now = new Date(nowTs)
    const dayKey = localDayKeyFromDate(now)
    const totalMinutes = now.getHours() * 60 + now.getMinutes()
    return {
      dayKey,
      hours: now.getHours(),
      minutes: now.getMinutes(),
      totalMinutes,
      label: `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`,
    }
  }, [nowTs])

  const loadByAssigneeToday = useMemo(() => {
    const rows = new Map<string, { id: string; label: string; total: number; meetings: number; tasks: number; overdue: number }>()
    for (const event of selectedEvents) {
      const key = String(event.assigneeId || '')
      if (!key) continue
      if (!rows.has(key)) {
        rows.set(key, { id: key, label: labels.get(key) || key, total: 0, meetings: 0, tasks: 0, overdue: 0 })
      }
      const row = rows.get(key)!
      row.total += 1
      if (String(event.kind || '').toLowerCase() === 'meeting') row.meetings += 1
      if (['task', 'followup', 'call'].includes(String(event.kind || '').toLowerCase())) row.tasks += 1
      if (event.status === 'overdue') row.overdue += 1
    }
    return Array.from(rows.values()).sort((a, b) => b.total - a.total || a.label.localeCompare(b.label))
  }, [labels, selectedEvents])
  const recommendedAssigneeId = useMemo(() => {
    if (!managers.length) return ''
    const loadMap = new Map<string, number>(loadByAssigneeToday.map((r) => [r.id, r.total]))
    const available = managers.filter((m) => (teamStateByManager[m.id] || 'available') === 'available')
    const pool = available.length ? available : managers
    return pool
      .slice()
      .sort((a, b) => {
        const la = Number(loadMap.get(a.id) || 0)
        const lb = Number(loadMap.get(b.id) || 0)
        if (la !== lb) return la - lb
        return a.label.localeCompare(b.label)
      })[0]?.id || ''
  }, [loadByAssigneeToday, managers, teamStateByManager])

  const dayPlannerEvents = useMemo(() => {
    return selectedEvents.filter((e) => e.source === 'planner' && e.plannerId && e.at)
  }, [selectedEvents])
  const selectedPlannerEvents = useMemo(() => {
    const selected = new Set(selectedPlannerIds)
    return dayPlannerEvents.filter((event) => event.plannerId && selected.has(event.plannerId))
  }, [dayPlannerEvents, selectedPlannerIds])

  const dayBoard = useMemo(() => {
    const morning: UnifiedCalendarEvent[] = []
    const midday: UnifiedCalendarEvent[] = []
    const evening: UnifiedCalendarEvent[] = []

    for (const event of selectedEvents) {
      const d = parseDate(event.at || `${event.dateKey}T12:00:00`)
      const hour = d ? d.getHours() : 12
      if (hour < 12) morning.push(event)
      else if (hour < 17) midday.push(event)
      else evening.push(event)
    }

    return { morning, midday, evening }
  }, [selectedEvents])

  const stats = useMemo(() => {
    const planner = unifiedEvents.filter((e) => e.source === 'planner')
    const integrated = unifiedEvents.filter((e) => e.source === 'integrated')
    return {
      timeOff: unifiedEvents.filter((e) => e.source === 'timeoff').length,
      reminders: unifiedEvents.filter((e) => e.source === 'reminder').length,
      planner: planner.length,
      integrated: integrated.length,
      meetings: planner.filter((e) => String(e.kind || '').toLowerCase() === 'meeting').length,
      tasks: planner.filter((e) => ['task', 'followup', 'call'].includes(String(e.kind || '').toLowerCase())).length,
      overdue: unifiedEvents.filter((e) => e.status === 'overdue').length,
      daysWithEvents: eventsByDay.size,
    }
  }, [eventsByDay.size, unifiedEvents])

  const upcoming = useMemo(() => {
    const today = localDayKeyFromDate(new Date())
    return filteredEvents.filter((e) => e.dateKey >= today).slice(0, 25)
  }, [filteredEvents])

  // G-6 — ``/app/calendar?event_id=<uuid>`` (planner event id or activity/reminder id).
  useEffect(() => {
    const raw = (searchParams.get('event_id') || searchParams.get('eventId') || '').trim()
    if (!raw || loading) return
    if (deepLinkHandledRef.current === raw) return

    const match = unifiedEvents.find((e) => e.plannerId === raw || e.reminderId === raw)
    if (match) {
      deepLinkFetchAttemptRef.current = null
      deepLinkHandledRef.current = raw
      const dayKey = match.dateKey
      const dayDate = parseDate(`${dayKey}T12:00:00`) || new Date()
      setSelectedDay(dayKey)
      setMonthCursor(startOfMonth(dayDate))
      setWeekCursor(startOfWeek(dayDate))
      setViewMode('day')
      setSourceFilter('all')
      setAssigneeFilter('')
      setActivityTypeFilter('')
      setPlannerKindFilter('')

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const el = document.getElementById(`hf-cal-ev-${match.id}`)
          el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
          if (match.plannerId) {
            setActivePlannerMenuId(match.plannerId)
          }
          setHighlightUnifiedId(match.id)
          window.setTimeout(() => setHighlightUnifiedId(null), 4500)
          setSearchParams(
            (prev) => {
              const next = new URLSearchParams(prev)
              next.delete('event_id')
              next.delete('eventId')
              return next
            },
            { replace: true },
          )
        })
      })
      return
    }

    // Wait for an in-flight fetch that will merge ``focusInject*`` into unifiedEvents.
    if (deepLinkFetchAttemptRef.current === raw) return
    deepLinkFetchAttemptRef.current = raw
    void (async () => {
      try {
        const pe = await getCommunicationPlannerEvent(raw)
        setFocusInjectPlanner(pe)
        deepLinkFetchAttemptRef.current = null
        return
      } catch {
        /* try activity */
      }
      try {
        const act = await getActivity(raw)
        setFocusInjectReminder(act as Record<string, unknown>)
        deepLinkFetchAttemptRef.current = null
      } catch {
        deepLinkHandledRef.current = raw
        deepLinkFetchAttemptRef.current = null
      }
    })()
  }, [
    loading,
    searchParams,
    unifiedEvents,
    setSearchParams,
  ])

  const findSchedulingConflict = useCallback((params: {
    assigneeId?: string | null
    startAt: Date
    endAt?: Date | null
    allDay?: boolean
    ignorePlannerId?: string | null
  }): string | null => {
    const assigneeId = String(params.assigneeId || '')
    if (!assigneeId) return null
    const interval = buildEventInterval(params.startAt, params.endAt || null, Boolean(params.allDay))
    const intervalDays = enumerateDayKeys(interval.start, interval.end)

    for (const row of timeOffRows) {
      if (row.status !== 'approved') continue
      if (String(row.requester_user_id || '') !== assigneeId) continue
      if (!row.start_date || !row.end_date) continue

      const hasDateOverlap = intervalDays.some((dayKey) => dayKey >= row.start_date && dayKey <= row.end_date)
      if (!hasDateOverlap) continue

      if (!row.partial_day) {
        return `approved time-off (${row.start_date}..${row.end_date})`
      }

      const fromMin = parseClockMinutes(row.payload?.time_window?.from)
      const toMin = parseClockMinutes(row.payload?.time_window?.to)
      if (fromMin == null || toMin == null) {
        return `approved partial-day time-off (${row.start_date}..${row.end_date})`
      }

      for (const dayKey of intervalDays) {
        if (dayKey < row.start_date || dayKey > row.end_date) continue
        const bounds = toDayBounds(dayKey)
        const segStart = interval.start > bounds.start ? interval.start : bounds.start
        const segEnd = interval.end < bounds.end ? interval.end : bounds.end
        if (segEnd <= segStart) continue
        const timeoffStart = new Date(bounds.start)
        timeoffStart.setMinutes(fromMin)
        const timeoffEnd = new Date(bounds.start)
        timeoffEnd.setMinutes(toMin)
        if (rangesOverlap(segStart, segEnd, timeoffStart, timeoffEnd)) {
          return `approved partial-day time-off (${dayKey} ${row.payload?.time_window?.from}-${row.payload?.time_window?.to})`
        }
      }
    }

    for (const pe of plannerEventsEffective) {
      if (String(pe.assignee_id || '') !== assigneeId) continue
      if (params.ignorePlannerId && pe.id === params.ignorePlannerId) continue
      const status = String(pe.status || '').toLowerCase()
      if (status === 'done' || status === 'cancelled') continue
      const peStart = parseDate(pe.start_at)
      if (!peStart) continue
      const peEndRaw = pe.end_at ? parseDate(pe.end_at) : null
      const peInterval = buildEventInterval(peStart, peEndRaw, Boolean((pe as any).all_day))
      if (rangesOverlap(interval.start, interval.end, peInterval.start, peInterval.end)) {
        return `planner overlap (${pe.title})`
      }
    }

    return null
  }, [plannerEventsEffective, timeOffRows])

  const createPlanner = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (!plannerForm.title.trim() || !plannerForm.startAt) {
      setCalendarError(friendlyFormHintError(t('app.communications.calendar.errors.fill_required', { defaultValue: 'Please fill title and start date/time' }), t))
      return
    }
    const startBase = new Date(plannerForm.startAt)
    if (Number.isNaN(startBase.getTime())) {
      setCalendarError(friendlyFormHintError(t('app.communications.calendar.errors.invalid_start_datetime', { defaultValue: 'Invalid start datetime' }), t))
      return
    }
    const endBase = plannerForm.allDay || !plannerForm.endAt ? null : new Date(plannerForm.endAt)
    if (endBase && Number.isNaN(endBase.getTime())) {
      setCalendarError(friendlyFormHintError(t('app.communications.calendar.errors.invalid_end_datetime', { defaultValue: 'Invalid end datetime' }), t))
      return
    }
    const safeRepeatCount = Math.min(30, Math.max(1, Number(plannerForm.repeatCount || 1)))
    setBusy(true)
    setInfoText(null)
    try {
      let created = 0
      let skipped = 0
      let firstCreatedAt: Date | null = null

      for (let i = 0; i < safeRepeatCount; i += 1) {
        if (plannerForm.repeatMode === 'none' && i > 0) break
        const startShifted =
          plannerForm.repeatMode === 'daily'
            ? addDays(startBase, i)
            : plannerForm.repeatMode === 'weekdays'
              ? addWeekdays(startBase, i)
              : startBase
        const endShifted =
          endBase == null
            ? null
            : plannerForm.repeatMode === 'daily'
              ? addDays(endBase, i)
              : plannerForm.repeatMode === 'weekdays'
                ? addWeekdays(endBase, i)
                : endBase
        if (!plannerForm.allDay && workingHours?.days?.length && !allowOutsideHours) {
          const jsDay = startShifted.getDay()
          const weekday = (jsDay + 6) % 7
          const day = workingHours.days.find((x) => x.weekday === weekday)
          if (day?.enabled && Array.isArray(day.windows) && day.windows.length) {
            const hhmm = `${String(startShifted.getHours()).padStart(2, '0')}:${String(startShifted.getMinutes()).padStart(2, '0')}`
            const toMin = (v: string) => {
              const [h, m] = v.split(':').map((x) => Number(x))
              return h * 60 + m
            }
            const mNow = toMin(hhmm)
            const inAny = day.windows.some((w) => mNow >= toMin(w.from) && mNow < toMin(w.to))
            if (!inAny) {
              skipped += 1
              continue
            }
          }
        }
        const conflictReason = findSchedulingConflict({
          assigneeId: plannerForm.assigneeId || null,
          startAt: startShifted,
          endAt: endShifted,
          allDay: plannerForm.allDay,
        })
        if (conflictReason) {
          skipped += 1
          continue
        }
        await createCommunicationPlannerEvent({
          title: plannerForm.title.trim(),
          kind: plannerForm.kind,
          priority: plannerForm.priority,
          assignee_id: plannerForm.assigneeId || undefined,
          start_at: startShifted.toISOString(),
          end_at: endShifted?.toISOString(),
          all_day: plannerForm.allDay,
          description: plannerForm.description.trim() || undefined,
          payload: {
            source: 'communications_calendar',
            recurrence: {
              mode: plannerForm.repeatMode,
              index: i,
              count: plannerForm.repeatMode === 'none' ? 1 : safeRepeatCount,
            },
          },
        })
        created += 1
        if (!firstCreatedAt) firstCreatedAt = new Date(startShifted)
      }
      setPlannerForm((p) => ({ ...p, title: '', description: '', repeatMode: 'none', repeatCount: 1 }))
      await load()
      setCalendarError(
        created > 0 ? null : friendlyFormHintError(t('app.communications.calendar.errors.no_events_created', { defaultValue: 'No events created' }), t),
      )
      if (skipped > 0) {
        setInfoText(`Created ${created} event(s). Skipped ${skipped} due to conflicts or working hours.`)
      } else if (created > 1) {
        setInfoText(`Created ${created} recurring events.`)
      } else if (created === 1) {
        setInfoText(t('app.communications.calendar.messages.created_one', { defaultValue: 'Event created.' }))
      } else {
        setInfoText(null)
      }
      if (firstCreatedAt) {
        const dayKey = localDayKeyFromDate(firstCreatedAt)
        setSelectedDay(dayKey)
        setMonthCursor(startOfMonth(firstCreatedAt))
        setWeekCursor(startOfWeek(firstCreatedAt))
        setViewMode('day')
      }
      setSourceFilter('all')
      setAssigneeFilter('')
      setStatusFilter('all')
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.create_planner_failed', { defaultValue: 'Failed to create planner event' }),
        )
      ) {
        setCalendarError(
          getFriendlyErrorInfo(err, t('app.communications.calendar.errors.create_planner_failed', { defaultValue: 'Failed to create planner event' }), t),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [allowOutsideHours, findSchedulingConflict, load, planLimitModal, plannerForm, t, workingHours])

  const openCreateEventModal = useCallback((dayKey: string, hour = 9, minute = 0) => {
    const base = parseDate(`${dayKey}T00:00:00`) || new Date()
    base.setHours(hour, minute, 0, 0)
    const end = new Date(base.getTime() + 60 * 60_000)
    setEventModalEvent(null)
    setEventModalType('task')
    setEventModalTitle('')
    setEventModalKind(taskPrefs.defaultTaskKind)
    setEventModalAssigneeId(String((me as any)?.id || (me as any)?.sub || '').trim())
    setEventModalStartAt(toLocalInput(base.toISOString()))
    setEventModalEndAt(toLocalInput(end.toISOString()))
    setEventModalAllDay(false)
    setEventModalDescription('')
    setEventModalLocation('')
    setEventModalParticipants([])
    setEventModalParticipantErrors({})
    setEventModalMeetingLink('')
    setEventModalOnlineMeeting(false)
    setEventModalAllowUnavailableAssignee(false)
    setEventModalRemindMinutes(taskPrefs.defaultRemindMinutes)
    setEventModalOpen(true)
  }, [me, taskPrefs.defaultRemindMinutes, taskPrefs.defaultTaskKind])

  const openEventDetailsModal = useCallback((event: UnifiedCalendarEvent) => {
    const start = parseDate(event.at || `${event.dateKey}T09:00:00`) || new Date()
    const end = parseDate(event.endAt || null) || new Date(start.getTime() + 60 * 60_000)
    setEventModalEvent(event)
    const inferredType: 'meeting' | 'task' =
      event.source === 'reminder' || ['task', 'followup'].includes(String(event.kind || '').toLowerCase())
        ? 'task'
        : 'meeting'
    setEventModalType(inferredType)
    setEventModalTitle(event.title || '')
    setEventModalKind(String(event.kind || (inferredType === 'task' ? 'task' : 'meeting')))
    setEventModalAssigneeId(String(event.assigneeId || ''))
    setEventModalStartAt(toLocalInput(start.toISOString()))
    setEventModalEndAt(toLocalInput(end.toISOString()))
    setEventModalAllDay(!event.at)
    setEventModalDescription(event.detail || '')
    let srcPayload: Record<string, any> = {}
    if (event.plannerId) {
      const planner = plannerById.get(event.plannerId)
      srcPayload = (planner?.payload || {}) as Record<string, any>
    } else if (event.integratedItemId) {
      const integrated = integratedCalendarItems.find((x) => String(x.id) === String(event.integratedItemId))
      srcPayload = (integrated?.payload || {}) as Record<string, any>
    }
    setEventModalLocation(String(srcPayload.location || srcPayload.meeting_location || ''))
    const attendeesRaw = Array.isArray(srcPayload.attendees) ? srcPayload.attendees : []
    setEventModalParticipants(
      dedupeParticipants(
        attendeesRaw
          .map((row: any, idx: number) => {
            if (typeof row === 'string') {
              const email = String(row || '').trim()
              if (!email) return null
              return { id: `p-${idx}-${email}`, name: '', email, response_status: '' as const }
            }
            if (!row || typeof row !== 'object') return null
            const email = String(row.email || row.address || '').trim()
            if (!email) return null
            const name = String(row.name || row.displayName || '').trim()
            const rsRaw = String(row.response_status || row.responseStatus || row.status || '').trim().toLowerCase()
            const response_status: '' | 'accepted' | 'tentative' | 'declined' =
              rsRaw === 'accepted' || rsRaw === 'tentative' || rsRaw === 'declined' ? (rsRaw as any) : ''
            return { id: `p-${idx}-${email}`, name, email, response_status }
          })
          .filter((x): x is EventModalParticipant => x !== null),
      ),
    )
    setEventModalParticipantErrors({})
    setEventModalMeetingLink(String(srcPayload.meeting_link || srcPayload.meetingLink || srcPayload.hangoutLink || ''))
    setEventModalOnlineMeeting(Boolean(srcPayload.is_online_meeting || srcPayload.online_meeting))
    setEventModalAllowUnavailableAssignee(false)
    setEventModalRemindMinutes(30)
    setEventModalOpen(true)
  }, [integratedCalendarItems, plannerById])

  const onParticipantEmailPaste = useCallback((rowId: string, e: ClipboardEvent<HTMLInputElement>) => {
    const text = e.clipboardData?.getData('text/plain') || ''
    const emails = extractEmailsFromClipboardText(text)
    const looksLikeList = text.includes('\n') || /[,;]/.test(text) || emails.length >= 2
    if (!looksLikeList || emails.length === 0) return
    e.preventDefault()
    setEventModalParticipantErrors((prev) => {
      const next = { ...prev }
      delete next[rowId]
      return next
    })
    setEventModalParticipants((prev) => mergeBulkEmailsAtRow(prev, rowId, emails))
  }, [])

  const onParticipantEmailKeyDown = useCallback((rowId: string, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== 'Enter') return
    e.preventDefault()
    const email = e.currentTarget.value.trim()
    if (email && !isValidParticipantEmail(email)) {
      setEventModalParticipantErrors((prev) => ({
        ...prev,
        [rowId]: t('app.communications.calendar.errors.invalid_attendee_email', { defaultValue: 'Invalid email address' }),
      }))
      return
    }
    setEventModalParticipantErrors((prev) => {
      const next = { ...prev }
      delete next[rowId]
      return next
    })
    const nu: EventModalParticipant = { id: `p-new-${Date.now()}`, name: '', email: '', response_status: '' }
    setEventModalParticipants((prev) => {
      const idx = prev.findIndex((x) => x.id === rowId)
      if (idx === -1) return [...prev, nu]
      return [...prev.slice(0, idx + 1), nu, ...prev.slice(idx + 1)]
    })
  }, [t])

  const submitEventModal = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (!eventModalTitle.trim() || !eventModalStartAt) {
      setCalendarError(friendlyFormHintError(t('app.communications.calendar.errors.fill_required', { defaultValue: 'Please fill title and start date/time' }), t))
      return
    }
    try {
      setBusy(true)
      const participantErrors: Record<string, string> = {}
      for (const p of eventModalParticipants) {
        const email = String(p.email || '').trim()
        if (email && !isValidParticipantEmail(email)) {
          participantErrors[p.id] = t('app.communications.calendar.errors.invalid_attendee_email', { defaultValue: 'Invalid email address' })
        }
      }
      if (Object.keys(participantErrors).length > 0) {
        setEventModalParticipantErrors(participantErrors)
        setCalendarError(
          friendlyFormHintError(
            t('app.communications.calendar.errors.attendees_invalid', { defaultValue: 'Fix invalid attendee emails before saving.' }),
            t,
          ),
        )
        return
      }
      setEventModalParticipantErrors({})

      const start = new Date(eventModalStartAt)
      const end = eventModalAllDay || !eventModalEndAt ? null : new Date(eventModalEndAt)
      const remindAt = new Date(start.getTime() - Math.max(0, Number(eventModalRemindMinutes || 0)) * 60_000)
      const assigneeId = String(eventModalAssigneeId || (me as any)?.id || (me as any)?.sub || '').trim() || undefined
      const attendeesPayload = dedupeParticipants(eventModalParticipants)
        .map((p) => ({
          email: String(p.email || '').trim(),
          name: String(p.name || '').trim() || undefined,
          response_status: String(p.response_status || '').trim() || undefined,
        }))
        .filter((p) => p.email)
      const taskKind: TaskKind = ['task', 'followup', 'call'].includes(String(eventModalKind || '').toLowerCase())
        ? (String(eventModalKind).toLowerCase() as TaskKind)
        : taskPrefs.defaultTaskKind
      if (eventModalEvent) {
        if (eventModalEvent.plannerId) {
          const planner = plannerById.get(eventModalEvent.plannerId)
          const nextPayload: Record<string, any> = { ...((planner?.payload || {}) as Record<string, any>) }
          nextPayload.location = eventModalLocation.trim() || undefined
          nextPayload.attendees = attendeesPayload
          nextPayload.meeting_link = eventModalMeetingLink.trim() || undefined
          nextPayload.is_online_meeting = Boolean(eventModalOnlineMeeting)
          nextPayload.online_meeting_provider = eventModalOnlineMeeting ? 'teamsForBusiness' : undefined
          nextPayload.reminder_minutes = eventModalRemindMinutes
          await patchCommunicationPlannerEvent(eventModalEvent.plannerId, {
            title: eventModalTitle.trim(),
            description: eventModalDescription.trim() || null,
            start_at: start.toISOString(),
            end_at: end?.toISOString() || null,
            all_day: eventModalAllDay,
            assignee_id: assigneeId || null,
            payload: nextPayload,
            allow_unavailable_assignee: eventModalAllowUnavailableAssignee,
          })
          window.dispatchEvent(new CustomEvent('planner-event-updated'))
        } else if (eventModalEvent.integratedItemId) {
          await patchCalendarItem(eventModalEvent.integratedItemId, {
            title: eventModalTitle.trim(),
            description: eventModalDescription.trim() || '',
            starts_at: start.toISOString(),
            ends_at: end?.toISOString(),
            all_day: eventModalAllDay,
            assignee_id: assigneeId || null,
            payload: {
              location: eventModalLocation.trim() || undefined,
              attendees: attendeesPayload,
              meeting_link: eventModalMeetingLink.trim() || undefined,
              is_online_meeting: Boolean(eventModalOnlineMeeting),
              online_meeting_provider: eventModalOnlineMeeting ? 'teamsForBusiness' : undefined,
              reminder_minutes: eventModalRemindMinutes,
            },
          })
        } else if (eventModalEvent.reminderId) {
          const patchBody: Record<string, any> = {
            title: eventModalTitle.trim(),
            description: eventModalDescription.trim() || undefined,
            due_at: start.toISOString(),
            assignee_id: assigneeId || undefined,
            allow_unavailable_assignee: eventModalAllowUnavailableAssignee,
          }
          if (!eventModalAllDay && end) {
            const dm = Math.round((end.getTime() - start.getTime()) / 60_000)
            if (dm > 0) patchBody.duration_minutes = dm
          }
          const kt = String(eventModalKind || '').toLowerCase()
          if (['task', 'followup', 'call', 'meeting'].includes(kt)) {
            patchBody.type = kt
          }
          await updateActivity(eventModalEvent.reminderId, patchBody)
          window.dispatchEvent(new CustomEvent('reminder-updated'))
        }
        setEventModalOpen(false)
        setInfoText(t('app.communications.calendar.messages.saved', { defaultValue: 'Event saved.' }))
        void load()
        return
      }
      if (eventModalType === 'task') {
        await createActivity({
          title: eventModalTitle.trim(),
          description: eventModalDescription.trim() || undefined,
          type: taskKind,
          entity_type: 'calendar',
          entity_id: localDayKeyFromDate(start),
          assignee_id: assigneeId,
          due_at: start.toISOString(),
          remind_at: eventModalRemindMinutes > 0 ? remindAt.toISOString() : undefined,
          source: 'communications_calendar_modal',
          allow_unavailable_assignee: eventModalAllowUnavailableAssignee,
          payload: {
            priority: 'normal',
            remind_minutes: eventModalRemindMinutes,
            task_kind: taskKind,
            // Phase 2.1 calendar-worthy marker — user explicitly used the calendar
            // create modal, so the row stays on the calendar regardless of taskKind.
            calendar_visible: true,
          },
        })
        window.dispatchEvent(new CustomEvent('reminder-updated'))
      } else {
        const createdPlanner = await createCommunicationPlannerEvent({
          title: eventModalTitle.trim(),
          kind: eventModalKind || 'meeting',
          priority: 'normal',
          assignee_id: assigneeId,
          start_at: start.toISOString(),
          end_at: end?.toISOString(),
          all_day: eventModalAllDay,
          allow_unavailable_assignee: eventModalAllowUnavailableAssignee,
          description: eventModalDescription.trim() || undefined,
          payload: {
            source: 'communications_calendar_modal',
            location: eventModalLocation.trim() || undefined,
            attendees: attendeesPayload,
            meeting_link: eventModalMeetingLink.trim() || undefined,
            is_online_meeting: eventModalOnlineMeeting,
            online_meeting_provider: eventModalOnlineMeeting ? 'teamsForBusiness' : undefined,
            visibility: 'private',
            reminder_minutes: eventModalRemindMinutes,
          },
        })
        setFocusInjectPlanner(createdPlanner)
        await createActivity({
          title: eventModalTitle.trim(),
          description: eventModalDescription.trim() || undefined,
          type: 'custom',
          entity_type: 'planner_event',
          entity_id: String((createdPlanner as any)?.id || ''),
          assignee_id: assigneeId,
          due_at: start.toISOString(),
          remind_at: eventModalRemindMinutes > 0 ? remindAt.toISOString() : undefined,
          source: 'communications_calendar_meeting_alert',
          payload: {
            priority: 'normal',
            planner_event_id: String((createdPlanner as any)?.id || ''),
            remind_minutes: eventModalRemindMinutes,
          },
        }).catch(() => undefined)
        window.dispatchEvent(new CustomEvent('planner-event-updated'))
        window.dispatchEvent(new CustomEvent('reminder-updated'))
      }
      setEventModalOpen(false)
      await load()
      setSelectedDay(localDayKeyFromDate(start))
      setViewMode('day')
    } catch (err: any) {
      setCalendarError(getFriendlyErrorInfo(err, t('app.communications.calendar.errors.create_planner_failed', { defaultValue: 'Failed to create planner event' }), t))
    } finally {
      setBusy(false)
    }
  }, [eventModalAllDay, eventModalAllowUnavailableAssignee, eventModalAssigneeId, eventModalDescription, eventModalEndAt, eventModalEvent, eventModalKind, eventModalLocation, eventModalMeetingLink, eventModalOnlineMeeting, eventModalParticipants, eventModalRemindMinutes, eventModalStartAt, eventModalTitle, eventModalType, load, me, plannerById, t, taskPrefs.defaultTaskKind])

  const cancelUnifiedEvent = useCallback(async (event: UnifiedCalendarEvent) => {
    // Snapshot for rollback if BE rejects the cancel.
    const snapshotPlanner = plannerEvents
    const snapshotReminders = reminders
    const snapshotIntegrated = integratedCalendarItems
    try {
      setBusy(true)
      // Optimistic removal — make the event disappear from the calendar instantly,
      // before the network round-trip. Backend is the source of truth and the
      // follow-up ``load()`` reconciles if anything diverged.
      if (event.plannerId) {
        setPlannerEvents((prev) => prev.map((pe) => (pe.id === event.plannerId ? { ...pe, status: 'cancelled' } : pe)))
      }
      if (event.reminderId) {
        setReminders((prev: any[]) =>
          prev.map((r: any) => (String(r?.id || '') === event.reminderId ? { ...r, status: 'cancelled' } : r)),
        )
      }
      if (event.integratedItemId) {
        setIntegratedCalendarItems((prev) =>
          prev.map((ci) => (ci.id === event.integratedItemId ? { ...ci, status: 'cancelled' } : ci)),
        )
      }
      setEventModalOpen(false)
      setInfoText(t('app.communications.calendar.messages.cancelled', { defaultValue: 'Event cancelled.' }))

      if (event.plannerId) {
        await patchCommunicationPlannerEvent(event.plannerId, { status: 'cancelled' })
        window.dispatchEvent(new CustomEvent('planner-event-updated'))
      } else if (event.reminderId) {
        await patchCommunicationPlannerEvent(event.reminderId, { status: 'cancelled' })
        window.dispatchEvent(new CustomEvent('planner-event-updated'))
        try {
          window.dispatchEvent(new CustomEvent('reminder-updated', { detail: { reminderId: event.reminderId } }))
        } catch {}
      } else if (event.integratedItemId) {
        await cancelCalendarItem(event.integratedItemId)
      } else {
        return
      }
      // Reconcile in the background — won't block the UI.
      void load()
    } catch (err: any) {
      // Rollback optimistic update on failure.
      setPlannerEvents(snapshotPlanner)
      setReminders(snapshotReminders)
      setIntegratedCalendarItems(snapshotIntegrated)
      setInfoText(null)
      setCalendarError(getFriendlyErrorInfo(err, t('app.communications.calendar.errors.update_planner_failed', { defaultValue: 'Failed to update planner event' }), t))
    } finally {
      setBusy(false)
    }
  }, [integratedCalendarItems, load, plannerEvents, reminders, t])

  const saveNotificationSettings = useCallback(async () => {
    try {
      setNotificationSettingsSaving(true)
      const saved = await upsertMyNotificationSettings(notificationSettings)
      setNotificationSettings({ ...DEFAULT_NOTIFICATION_SETTINGS, ...(saved || {}) })
      setInfoText(t('app.communications.calendar.messages.settings_saved', { defaultValue: 'Settings saved.' }))
    } catch (err: any) {
      setCalendarError(getFriendlyErrorInfo(err, t('app.communications.calendar.errors.save_failed', { defaultValue: 'Failed to save settings' }), t))
    } finally {
      setNotificationSettingsSaving(false)
    }
  }, [notificationSettings, t])

  const createDayReminder = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (!reminderForm.title.trim() || !reminderForm.dueAt) return
    setBusy(true)
    try {
      const due = new Date(reminderForm.dueAt)
      const remindAt = new Date(due.getTime() - Math.max(1, Number(reminderForm.offsetMinutes || 30)) * 60_000)
      await createActivity({
        title: reminderForm.title.trim(),
        description: reminderForm.description.trim() || undefined,
        type: reminderForm.type || 'custom',
        entity_type: 'calendar',
        entity_id: selectedDay,
        assignee_id: reminderForm.assigneeId || String((me as any)?.id || (me as any)?.sub || '').trim() || undefined,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        source: 'communications_calendar',
        payload: {
          priority: reminderForm.priority,
          selected_day: selectedDay,
          // Phase 2.1 calendar-worthy marker: user explicitly created this row
          // via the calendar side form, so it must stay on the calendar regardless
          // of its `type` (task / followup / custom). See isCalendarWorthyActivity.
          calendar_visible: true,
        },
      })
      setReminderForm((p) => ({ ...p, title: '', description: '' }))
      await load()
      setCalendarError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.create_activity_failed', { defaultValue: 'Failed to create activity' }),
        )
      ) {
        setCalendarError(
          getFriendlyErrorInfo(err, t('app.communications.calendar.errors.create_activity_failed', { defaultValue: 'Failed to create activity' }), t),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [load, planLimitModal, reminderForm, selectedDay, t])

  const setPlannerStatus = useCallback(async (plannerId: string, status: string) => {
    setBusy(true)
    const snapshotPlanner = plannerEvents
    const s = String(status || '').toLowerCase()
    try {
      // Optimistic: flip status locally so the calendar reflects the action instantly.
      setPlannerEvents((prev) => prev.map((pe) => (pe.id === plannerId ? { ...pe, status: s } : pe)))
      if (s === 'cancelled' || s === 'canceled') {
        setInfoText(t('app.communications.calendar.messages.cancelled', { defaultValue: 'Event cancelled.' }))
      } else if (s === 'done' || s === 'completed') {
        setInfoText(t('app.communications.calendar.messages.completed', { defaultValue: 'Event completed.' }))
      }
      await patchCommunicationPlannerEvent(plannerId, { status })
      setCalendarError(null)
      void load()
    } catch (err: any) {
      setPlannerEvents(snapshotPlanner)
      setInfoText(null)
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.update_planner_status_failed', { defaultValue: 'Failed to update planner event' }),
        )
      ) {
        setCalendarError(
          getFriendlyErrorInfo(err, t('app.communications.calendar.errors.update_planner_status_failed', { defaultValue: 'Failed to update planner event' }), t),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [load, plannerEvents, planLimitModal, t])

  const updatePlannerEvent = useCallback(async (
    event: UnifiedCalendarEvent,
    patch: Partial<{
      status: string
      priority: string
      assignee_id: string | null
      payload: Record<string, any>
    }>,
  ) => {
    if (!event.plannerId) return
    const start = parseDate(event.at || null)
    const end = parseDate(event.endAt || null)
    if ((patch.assignee_id ?? null) && start) {
      const conflictReason = findSchedulingConflict({
        assigneeId: patch.assignee_id ?? null,
        startAt: start,
        endAt: end,
        allDay: false,
        ignorePlannerId: event.plannerId,
      })
      if (conflictReason) {
        setCalendarError(
          friendlyFormHintError(
            t('app.communications.calendar.errors.cannot_reassign', {
              defaultValue: 'Cannot reassign: {reason}.',
              values: { reason: conflictReason },
            }),
            t,
          ),
        )
        return
      }
    }
    setBusy(true)
    try {
      await patchCommunicationPlannerEvent(event.plannerId, patch)
      await load()
      setCalendarError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.update_planner_failed', { defaultValue: 'Failed to update planner event' }),
        )
      ) {
        setCalendarError(
          getFriendlyErrorInfo(err, t('app.communications.calendar.errors.update_planner_failed', { defaultValue: 'Failed to update planner event' }), t),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load, planLimitModal, t])

  const setPlannerPriorityByEvent = useCallback(async (event: UnifiedCalendarEvent, priority: 'low' | 'normal' | 'high') => {
    await updatePlannerEvent(event, { priority })
  }, [updatePlannerEvent])

  const assignPlannerByEvent = useCallback(async (event: UnifiedCalendarEvent, assigneeId: string) => {
    await updatePlannerEvent(event, { assignee_id: assigneeId || null })
  }, [updatePlannerEvent])

  const togglePlannerTag = useCallback(async (event: UnifiedCalendarEvent, tag: string) => {
    if (!event.plannerId) return
    const row = plannerById.get(event.plannerId)
    if (!row) return
    const current = Array.isArray(row.payload?.tags) ? row.payload.tags.filter((x: any) => typeof x === 'string') : []
    const has = current.includes(tag)
    const next = has ? current.filter((x: string) => x !== tag) : [...current, tag]
    await updatePlannerEvent(event, {
      payload: {
        ...(row.payload || {}),
        tags: next,
      },
    })
  }, [plannerById, updatePlannerEvent])

  const archivePlannerByEvent = useCallback(async (event: UnifiedCalendarEvent) => {
    await updatePlannerEvent(event, { status: 'cancelled' })
  }, [updatePlannerEvent])

  useEffect(() => {
    const visible = new Set(dayPlannerEvents.map((event) => String(event.plannerId || '')))
    setSelectedPlannerIds((prev) => prev.filter((id) => visible.has(id)))
  }, [dayPlannerEvents])

  const togglePlannerSelection = useCallback((plannerId: string, checked: boolean) => {
    setSelectedPlannerIds((prev) => {
      if (checked) return Array.from(new Set([...prev, plannerId]))
      return prev.filter((id) => id !== plannerId)
    })
  }, [])

  const selectAllVisiblePlanner = useCallback(() => {
    setSelectedPlannerIds(dayPlannerEvents.map((event) => String(event.plannerId || '')).filter(Boolean))
  }, [dayPlannerEvents])

  const clearPlannerSelection = useCallback(() => {
    setSelectedPlannerIds([])
  }, [])

  const applyBatchToSelected = useCallback(async (
    worker: (event: UnifiedCalendarEvent) => Promise<'updated' | 'skipped'>,
    emptyMessage: string,
  ) => {
    if (!selectedPlannerEvents.length) {
      setInfoText(emptyMessage)
      return
    }
    setBusy(true)
    let updated = 0
    let skipped = 0
    try {
      for (const event of selectedPlannerEvents) {
        const res = await worker(event)
        if (res === 'updated') updated += 1
        else skipped += 1
      }
      await load()
      setCalendarError(null)
      setInfoText(
        t('app.communications.calendar.batch.done', {
          defaultValue: 'Batch done: updated {updated}, skipped {skipped}.',
          values: { updated, skipped },
        }),
      )
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.batch_failed', { defaultValue: 'Batch action failed' }),
        )
      ) {
        setCalendarError(getFriendlyErrorInfo(err, t('app.communications.calendar.errors.batch_failed', { defaultValue: 'Batch action failed' }), t))
      }
    } finally {
      setBusy(false)
    }
  }, [load, planLimitModal, selectedPlannerEvents, t])

  const runBatchAssign = useCallback(async () => {
    await applyBatchToSelected(async (event) => {
      if (!event.plannerId) return 'skipped'
      const start = parseDate(event.at || null)
      const end = parseDate(event.endAt || null)
      if (batchAssigneeId && start) {
        const conflictReason = findSchedulingConflict({
          assigneeId: batchAssigneeId,
          startAt: start,
          endAt: end,
          allDay: false,
          ignorePlannerId: event.plannerId,
        })
        if (conflictReason) return 'skipped'
      }
      await patchCommunicationPlannerEvent(event.plannerId, { assignee_id: batchAssigneeId || null })
      return 'updated'
    }, t('app.communications.calendar.batch.no_selected', { defaultValue: 'No selected planner events.' }))
  }, [applyBatchToSelected, batchAssigneeId, findSchedulingConflict, t])

  const runBatchPriority = useCallback(async (priority: 'low' | 'normal' | 'high') => {
    await applyBatchToSelected(async (event) => {
      if (!event.plannerId) return 'skipped'
      await patchCommunicationPlannerEvent(event.plannerId, { priority })
      return 'updated'
    }, t('app.communications.calendar.batch.no_selected', { defaultValue: 'No selected planner events.' }))
  }, [applyBatchToSelected, t])

  const runBatchArchive = useCallback(async () => {
    await applyBatchToSelected(async (event) => {
      if (!event.plannerId || event.plannerStatus === 'cancelled') return 'skipped'
      await patchCommunicationPlannerEvent(event.plannerId, { status: 'cancelled' })
      return 'updated'
    }, t('app.communications.calendar.batch.no_selected', { defaultValue: 'No selected planner events.' }))
  }, [applyBatchToSelected, t])

  const runBatchTag = useCallback(async (mode: 'add' | 'remove') => {
    const tag = batchTagValue.trim().replace(/^#/, '')
    if (!tag) {
      setInfoText(t('app.communications.calendar.batch.enter_tag_first', { defaultValue: 'Enter tag value first.' }))
      return
    }
    await applyBatchToSelected(async (event) => {
      if (!event.plannerId) return 'skipped'
      const row = plannerById.get(event.plannerId)
      if (!row) return 'skipped'
      const current = Array.isArray(row.payload?.tags) ? row.payload.tags.filter((x: any) => typeof x === 'string') : []
      const has = current.includes(tag)
      if (mode === 'add' && has) return 'skipped'
      if (mode === 'remove' && !has) return 'skipped'
      const next = mode === 'add' ? [...current, tag] : current.filter((x: string) => x !== tag)
      await patchCommunicationPlannerEvent(event.plannerId, {
        payload: {
          ...(row.payload || {}),
          tags: next,
        },
      })
      return 'updated'
    }, t('app.communications.calendar.batch.no_selected', { defaultValue: 'No selected planner events.' }))
  }, [applyBatchToSelected, batchTagValue, plannerById, t])

  const applySelectionPreset = useCallback((preset: 'meetings' | 'high' | 'unassigned' | 'in_progress' | 'due_soon') => {
    const now = new Date()
    const ids = dayPlannerEvents
      .filter((event) => {
        const status = String(event.plannerStatus || '').toLowerCase()
        const priority = String(event.priority || '').toLowerCase()
        const kind = String(event.kind || '').toLowerCase()
        const hasAssignee = Boolean(String(event.assigneeId || '').trim())
        const start = parseDate(event.at || null)
        if (preset === 'meetings') return kind === 'meeting'
        if (preset === 'high') return priority === 'high'
        if (preset === 'unassigned') return !hasAssignee && status !== 'cancelled' && status !== 'done'
        if (preset === 'in_progress') return status === 'in_progress'
        if (preset === 'due_soon') {
          if (!start) return false
          const diff = start.getTime() - now.getTime()
          return diff >= 0 && diff <= 2 * 60 * 60_000 && status !== 'cancelled' && status !== 'done'
        }
        return false
      })
      .map((event) => String(event.plannerId || ''))
      .filter(Boolean)
    setSelectedPlannerIds(ids)
    setInfoText(
      t('app.communications.calendar.batch.preset_selected', {
        defaultValue: 'Preset selected: {count} event(s).',
        values: { count: ids.length },
      }),
    )
  }, [dayPlannerEvents, t])

  const selectByCurrentBatchFilter = useCallback(() => {
    const ids = dayPlannerEvents
      .filter((event) => {
        if (batchSelectKind && String(event.kind || '') !== batchSelectKind) return false
        if (batchSelectPriority && String(event.priority || '') !== batchSelectPriority) return false
        if (batchSelectStatus && String(event.plannerStatus || '') !== batchSelectStatus) return false
        return true
      })
      .map((event) => String(event.plannerId || ''))
      .filter(Boolean)
    setSelectedPlannerIds(ids)
    setInfoText(
      t('app.communications.calendar.batch.selected_by_filter', {
        defaultValue: 'Selected {count} events by filter.',
        values: { count: ids.length },
      }),
    )
  }, [batchSelectKind, batchSelectPriority, batchSelectStatus, dayPlannerEvents, t])

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(CALENDAR_BATCH_STORAGE_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw || '{}')
      if (typeof parsed.batchAssigneeId === 'string') setBatchAssigneeId(parsed.batchAssigneeId)
      if (typeof parsed.batchTagValue === 'string') setBatchTagValue(parsed.batchTagValue)
      if (typeof parsed.batchSelectKind === 'string') setBatchSelectKind(parsed.batchSelectKind)
      if (typeof parsed.batchSelectPriority === 'string') setBatchSelectPriority(parsed.batchSelectPriority)
      if ([15, 30, 60].includes(Number(parsed.weekSlotMinutes || 0))) {
        setWeekSlotMinutes(Number(parsed.weekSlotMinutes) as WeekSlotMinutes)
      }
      if (['', 'planned', 'in_progress', 'done', 'cancelled'].includes(String(parsed.batchSelectStatus || ''))) {
        setBatchSelectStatus(String(parsed.batchSelectStatus || '') as BatchSelectStatusFilter)
      }
    } catch {
      // ignore invalid persisted state
    }
  }, [])

  useEffect(() => {
    try {
      window.localStorage.setItem(
        CALENDAR_BATCH_STORAGE_KEY,
        JSON.stringify({
          batchAssigneeId,
          batchTagValue,
          batchSelectKind,
          batchSelectPriority,
          batchSelectStatus,
          weekSlotMinutes,
        }),
      )
    } catch {
      // ignore storage failures
    }
  }, [batchAssigneeId, batchTagValue, batchSelectKind, batchSelectPriority, batchSelectStatus, weekSlotMinutes])

  const movePlannerEvent = useCallback(async (event: UnifiedCalendarEvent, byMinutes: number) => {
    if (!event.plannerId || !event.at) return
    const start = parseDate(event.at)
    if (!start) return
    const movedStart = new Date(start.getTime() + byMinutes * 60_000)
    const patch: Record<string, any> = { start_at: movedStart.toISOString() }
    const end = parseDate(event.endAt || null)
    let movedEnd: Date | null = null
    if (end) {
      movedEnd = new Date(end.getTime() + byMinutes * 60_000)
      patch.end_at = movedEnd.toISOString()
    }
    const conflictReason = findSchedulingConflict({
      assigneeId: event.assigneeId || null,
      startAt: movedStart,
      endAt: movedEnd,
      allDay: false,
      ignorePlannerId: event.plannerId || null,
    })
    if (conflictReason) {
      setCalendarError(
        friendlyFormHintError(
          t('app.communications.calendar.errors.cannot_move', {
            defaultValue: 'Cannot move: {reason}.',
            values: { reason: conflictReason },
          }),
          t,
        ),
      )
      return
    }
    if (event.detail !== undefined) patch.description = event.detail
    setBusy(true)
    try {
      await patchCommunicationPlannerEvent(event.plannerId, patch)
      await load()
      setCalendarError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.move_failed', { defaultValue: 'Failed to move planner event' }),
        )
      ) {
        setCalendarError(getFriendlyErrorInfo(err, t('app.communications.calendar.errors.move_failed', { defaultValue: 'Failed to move planner event' }), t))
      }
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load, planLimitModal, t])

  const duplicatePlannerEvent = useCallback(async (event: UnifiedCalendarEvent) => {
    if (!event.plannerId || !event.at) return
    const start = parseDate(event.at)
    if (!start) return
    const startShifted = new Date(start.getTime() + 24 * 60 * 60_000)
    const end = parseDate(event.endAt || null)
    const endShifted = end ? new Date(end.getTime() + 24 * 60 * 60_000) : null
    const conflictReason = findSchedulingConflict({
      assigneeId: event.assigneeId || null,
      startAt: startShifted,
      endAt: endShifted,
      allDay: false,
      ignorePlannerId: null,
    })
    if (conflictReason) {
      setCalendarError(
        friendlyFormHintError(
          t('app.communications.calendar.errors.cannot_duplicate', {
            defaultValue: 'Cannot duplicate: {reason}.',
            values: { reason: conflictReason },
          }),
          t,
        ),
      )
      return
    }
    setBusy(true)
    try {
      await createCommunicationPlannerEvent({
        title: t('app.communications.calendar.labels.copy_suffix', {
          defaultValue: '{title} (copy)',
          values: { title: event.title },
        }),
        description: event.detail || undefined,
        kind: event.kind || 'task',
        priority: event.priority || 'normal',
        assignee_id: event.assigneeId || undefined,
        start_at: startShifted.toISOString(),
        end_at: endShifted?.toISOString() || undefined,
      })
      await load()
      setCalendarError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.duplicate_failed', { defaultValue: 'Failed to duplicate planner event' }),
        )
      ) {
        setCalendarError(
          getFriendlyErrorInfo(err, t('app.communications.calendar.errors.duplicate_failed', { defaultValue: 'Failed to duplicate planner event' }), t),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load, planLimitModal, t])

  const completeDayReminder = useCallback(async (reminderId: string) => {
    setBusy(true)
    const snapshotReminders = reminders
    const snapshotPlanner = plannerEvents
    try {
      // Optimistic: mark the activity as done in both projections (reminder + planner
      // shim returns the same row through ``listActivities``).
      setReminders((prev: any[]) =>
        prev.map((r: any) => (String(r?.id || '') === reminderId ? { ...r, status: 'done' } : r)),
      )
      setPlannerEvents((prev) => prev.map((pe) => (pe.id === reminderId ? { ...pe, status: 'done' } : pe)))
      setInfoText(t('app.communications.calendar.messages.completed', { defaultValue: 'Event completed.' }))
      await completeActivity(reminderId)
      setCalendarError(null)
      void load()
    } catch (err: any) {
      setReminders(snapshotReminders)
      setPlannerEvents(snapshotPlanner)
      setInfoText(null)
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.complete_activity_failed', { defaultValue: 'Failed to complete activity' }),
        )
      ) {
        setCalendarError(
          getFriendlyErrorInfo(err, t('app.communications.calendar.errors.complete_activity_failed', { defaultValue: 'Failed to complete activity' }), t),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [load, planLimitModal, plannerEvents, reminders, t])

  const snoozeDayReminder = useCallback(async (reminderId: string, minutes: number) => {
    setBusy(true)
    try {
      await snoozeActivity(reminderId, { minutes })
      await load()
      setCalendarError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.snooze_activity_failed', { defaultValue: 'Failed to snooze activity' }),
        )
      ) {
        setCalendarError(
          getFriendlyErrorInfo(err, t('app.communications.calendar.errors.snooze_activity_failed', { defaultValue: 'Failed to snooze activity' }), t),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [load, planLimitModal, t])

  const setPlannerSlot = useCallback((day: string, hour: number, minute = 0) => {
    const base = parseDate(`${day}T00:00:00`)
    if (!base) return
    const start = new Date(base)
    start.setHours(hour, minute, 0, 0)
    const end = new Date(start.getTime() + 60 * 60_000)
    setPlannerForm((p) => ({
      ...p,
      startAt: toLocalInput(start.toISOString()),
      endAt: toLocalInput(end.toISOString()),
      allDay: false,
    }))
    setViewMode('day')
    setSelectedDay(day)
  }, [])

  // G-7 stage 1: drag-to-reschedule for both planner events AND reminders.
  // Planner rows use ``patchCommunicationPlannerEvent``; reminder-only rows
  // PATCH the same Activity via ``updateActivity`` (Phase 2.1 surface).
  const movePlannerEventToDateTime = useCallback(async (event: UnifiedCalendarEvent, targetStart: Date, dayKeyAfterMove?: string) => {
    const isReminderSource = event.source === 'reminder' && Boolean(event.reminderId)
    const isPlannerSource = event.source === 'planner' && Boolean(event.plannerId)
    if (!event.at || (!isReminderSource && !isPlannerSource)) return
    const start = parseDate(event.at)
    if (!start) return
    const movedStart = new Date(targetStart)

    const end = parseDate(event.endAt || null)
    const movedEnd = end ? new Date(movedStart.getTime() + (end.getTime() - start.getTime())) : null

    if (isPlannerSource) {
      // Conflict check only applies to planner-events because reminders
      // are zero-duration (a single point in time, no overlap surface).
      const conflictReason = findSchedulingConflict({
        assigneeId: event.assigneeId || null,
        startAt: movedStart,
        endAt: movedEnd,
        allDay: false,
        ignorePlannerId: event.plannerId,
      })
      if (conflictReason) {
        setCalendarError(
          friendlyFormHintError(
            t('app.communications.calendar.errors.cannot_move', {
              defaultValue: 'Cannot move: {reason}.',
              values: { reason: conflictReason },
            }),
            t,
          ),
        )
        return
      }
    }

    setBusy(true)
    try {
      if (isReminderSource && event.reminderId) {
        await updateActivity(event.reminderId, { due_at: movedStart.toISOString() })
        try {
          window.dispatchEvent(new CustomEvent('reminder-updated', { detail: { reminderId: event.reminderId } }))
        } catch {}
      } else if (isPlannerSource && event.plannerId) {
        await patchCommunicationPlannerEvent(event.plannerId, {
          start_at: movedStart.toISOString(),
          end_at: movedEnd?.toISOString() || null,
        })
      }
      await load()
      if (dayKeyAfterMove) setSelectedDay(dayKeyAfterMove)
      setCalendarError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.move_failed', { defaultValue: 'Failed to move planner event' }),
        )
      ) {
        setCalendarError(getFriendlyErrorInfo(err, t('app.communications.calendar.errors.move_failed', { defaultValue: 'Failed to move planner event' }), t))
      }
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load, planLimitModal, t])

  const resizePlannerEventToHour = useCallback(async (event: UnifiedCalendarEvent, dayKey: string, endHourExclusive: number) => {
    if (!event.plannerId || !event.at) return
    const start = parseDate(event.at)
    if (!start) return
    const end = parseDate(event.endAt || null)
    const targetDay = parseDate(`${dayKey}T00:00:00`)
    if (!targetDay) return

    const newEnd = new Date(targetDay)
    newEnd.setHours(Math.min(23, Math.max(0, endHourExclusive)), 0, 0, 0)
    if (newEnd <= start) {
      newEnd.setTime(start.getTime() + 60 * 60_000)
    }

    const conflictReason = findSchedulingConflict({
      assigneeId: event.assigneeId || null,
      startAt: start,
      endAt: newEnd,
      allDay: false,
      ignorePlannerId: event.plannerId,
    })
    if (conflictReason) {
      setCalendarError(
        friendlyFormHintError(
          t('app.communications.calendar.errors.cannot_resize', {
            defaultValue: 'Cannot resize: {reason}.',
            values: { reason: conflictReason },
          }),
          t,
        ),
      )
      return
    }

    setBusy(true)
    try {
      await patchCommunicationPlannerEvent(event.plannerId, {
        start_at: start.toISOString(),
        end_at: newEnd.toISOString(),
      })
      await load()
      setSelectedDay(dayKey)
      setCalendarError(null)
      setResizePlannerEvent(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.calendar.errors.resize_failed', { defaultValue: 'Failed to resize planner event' }),
        )
      ) {
        setCalendarError(
          getFriendlyErrorInfo(err, t('app.communications.calendar.errors.resize_failed', { defaultValue: 'Failed to resize planner event' }), t),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load, planLimitModal, t])

  const movePlannerEventToDay = useCallback(async (event: UnifiedCalendarEvent, dayKey: string) => {
    if (!event.at) return
    const start = parseDate(event.at)
    if (!start) return
    const target = parseDate(`${dayKey}T00:00:00`)
    if (!target) return
    target.setHours(start.getHours(), start.getMinutes(), start.getSeconds(), start.getMilliseconds())
    await movePlannerEventToDateTime(event, target, dayKey)
  }, [movePlannerEventToDateTime])

  // G-7 stage 1: drag-eligibility helper. Both planner events (have
  // `plannerId`) and reminders (have `reminderId`) can be dragged to a
  // new slot now. Resize stays planner-only because reminders are
  // zero-duration. The variable name keeps `dragPlannerEvent` for diff
  // size — semantically it now means "the dragged calendar item, of
  // either source".
  const isCalendarEventDraggable = useCallback(
    (event: UnifiedCalendarEvent | null | undefined): boolean =>
      Boolean(event && (event.plannerId || (event.source === 'reminder' && event.reminderId))),
    [],
  )
  const isDragActive = isCalendarEventDraggable(dragPlannerEvent)

  const calendarContent = (
    <>
      {!embedded ? (
        <PageShellHeader>
          <PageHeader
            title={t('app.communications.ia.calendar_title', { defaultValue: 'Calendar' })}
            kind="browse"
            secondaryActions={
              <button type="button" className="btn-secondary btn-sm" onClick={() => void load()}>
                {t('common.actions.refresh')}
              </button>
            }
          />
        </PageShellHeader>
      ) : null}

      <div className={embedded ? 'space-y-4' : 'flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4'}>

      {showAdvancedTools && (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-7">
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{t('app.communications.calendar.stats.time_off', { defaultValue: 'Time-off: {count}', values: { count: stats.timeOff } })}</div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{t('app.communications.calendar.stats.activities', { defaultValue: 'Activities: {count}', values: { count: stats.reminders } })}</div>
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">{t('app.communications.calendar.stats.planner_items', { defaultValue: 'Planner items: {count}', values: { count: stats.planner } })}</div>
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">{t('app.communications.calendar.stats.meetings', { defaultValue: 'Meetings: {count}', values: { count: stats.meetings } })}</div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{t('app.communications.calendar.stats.tasks', { defaultValue: 'Tasks: {count}', values: { count: stats.tasks } })}</div>
        <div className="rounded-lg border border-rose-200 bg-white p-3 text-sm text-rose-700">{t('app.communications.calendar.stats.overdue', { defaultValue: 'Overdue: {count}', values: { count: stats.overdue } })}</div>
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">{t('app.communications.calendar.stats.days', { defaultValue: 'Days: {count}', values: { count: stats.daysWithEvents } })}</div>
      </div>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setViewMode('month')}
            className={clsx('btn-secondary', viewMode === 'month' && 'border-brand-600 bg-brand-50 text-brand-700')}
          >
            {t('app.communications.calendar.views.month', { defaultValue: 'Month view' })}
          </button>
          <button
            type="button"
            onClick={() => setViewMode('day')}
            className={clsx('btn-secondary', viewMode === 'day' && 'border-brand-600 bg-brand-50 text-brand-700')}
          >
            {t('app.communications.calendar.views.day', { defaultValue: 'Day planner' })}
          </button>
          <button
            type="button"
            onClick={() => setViewMode('week')}
            className={clsx('btn-secondary', viewMode === 'week' && 'border-brand-600 bg-brand-50 text-brand-700')}
          >
            {t('app.communications.calendar.views.week', { defaultValue: 'Week view' })}
          </button>

          <button type="button" onClick={() => void load()} className="btn-secondary">
            {t('common.actions.refresh')}
          </button>
          <button
            type="button"
            onClick={() => setShowAdvancedTools((v) => !v)}
            className="btn-secondary"
          >
            {showAdvancedTools
              ? t('common.actions.hide', { defaultValue: 'Hide' })
              : t('common.actions.show', { defaultValue: 'Show' })}{' '}
            {t('app.communications.calendar.filters.advanced_panel', { defaultValue: 'Advanced filters' })}
          </button>
        </div>
        {showAdvancedTools && (
        <>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value as CalendarSourceFilter)} className="input">
            <option value="all">{t('app.communications.calendar.filters.sources.all', { defaultValue: 'All sources' })}</option>
            <option value="timeoff">{t('app.communications.calendar.filters.sources.timeoff', { defaultValue: 'Time-off' })}</option>
            <option value="reminders">
              {t('app.communications.calendar.filters.sources.activities', { defaultValue: 'Tasks & deadlines' })}
            </option>
            <option value="planner">{t('app.communications.calendar.filters.sources.planner', { defaultValue: 'Planner' })}</option>
            <option value="integrated">{t('app.communications.calendar.filters.sources.integrated', { defaultValue: 'Connected calendars' })}</option>
          </select>
          <select value={assigneeFilter} onChange={(e) => setAssigneeFilter(e.target.value)} className="input">
            <option value="">{t('app.communications.calendar.filters.managers.all', { defaultValue: 'All managers' })}</option>
            {managers.map((m) => <option key={m.id} value={m.id}>{managerLabelWithState(m.id, m.label)}</option>)}
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as TimeOffStatusFilter)} className="input">
            <option value="approved">{t('app.communications.calendar.filters.timeoff.approved_only', { defaultValue: 'Time-off approved only' })}</option>
            <option value="pending">{t('app.communications.calendar.filters.timeoff.pending_only', { defaultValue: 'Time-off pending only' })}</option>
            <option value="all">{t('app.communications.calendar.filters.timeoff.all', { defaultValue: 'Time-off approved + pending' })}</option>
          </select>
        </div>
        <details className="mt-3 rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2">
          <summary className="cursor-pointer text-sm font-medium text-slate-800">
            {t('app.communications.calendar.filters.advanced_panel', { defaultValue: 'Advanced filters' })}
          </summary>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <select value={activityTypeFilter} onChange={(e) => setActivityTypeFilter(e.target.value)} className="input">
              <option value="">{t('app.communications.calendar.filters.activity_types.all', { defaultValue: 'All activity types' })}</option>
              {Array.from(new Set(reminders.map((r) => String(r?.type || '')).filter(Boolean))).sort().map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
            <select value={plannerKindFilter} onChange={(e) => setPlannerKindFilter(e.target.value)} className="input">
              <option value="">{t('app.communications.calendar.filters.planner_kinds.all', { defaultValue: 'All planner kinds' })}</option>
              <option value="meeting">{t('app.communications.calendar.kinds.meeting', { defaultValue: 'Meeting' })}</option>
              <option value="task">{t('app.communications.calendar.kinds.task', { defaultValue: 'Task' })}</option>
              <option value="followup">{t('app.communications.calendar.kinds.followup', { defaultValue: 'Follow-up' })}</option>
              <option value="call">{t('app.communications.calendar.kinds.call', { defaultValue: 'Call' })}</option>
              <option value="shift">{t('app.communications.calendar.kinds.shift', { defaultValue: 'Shift' })}</option>
            </select>
          </div>
        </details>
        </>
        )}
        {calendarError && (
          <div className="mt-3">
            <ErrorRecoveryBanner
              info={calendarError}
              onRetry={() => void load()}
              retryLabel={t('common.actions.refresh')}
              {...friendlyErrorBannerSecondary(
                calendarError,
                CRM_APP_PATHS.settingsIntegrations,
                t('app.nav.items.settings_integrations', { defaultValue: 'Integrations' }),
              )}
              compact
            />
          </div>
        )}
        {infoText && <div className="mt-3 alert-info text-sm">{infoText}</div>}
        {loading && <div className="mt-3 text-sm text-slate-500">{t('common.loading')}</div>}
      </section>

      <div className={clsx('grid gap-4', showAdvancedTools && 'xl:grid-cols-[1.25fr_0.75fr]')}>
        <div className="space-y-4">
          {viewMode === 'month' && (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <button type="button" className="btn-secondary" onClick={() => setMonthCursor((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))}>
                    {t('app.communications.calendar.navigation.prev', { defaultValue: 'Prev' })}
                  </button>
                  <div className="min-w-40 text-sm font-semibold text-slate-900 capitalize">{monthMeta.title}</div>
                  <button type="button" className="btn-secondary" onClick={() => setMonthCursor((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))}>
                    {t('app.communications.calendar.navigation.next', { defaultValue: 'Next' })}
                  </button>
                </div>
                <div className="text-xs text-slate-500">
                  {t('app.communications.calendar.month.click_day_hint', { defaultValue: 'Click a day to open day planner.' })}
                </div>
              </div>

              <div className="mt-3 grid grid-cols-7 gap-1 text-xs text-slate-500">
                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
                  <div key={d} className="px-2 py-1 text-center font-medium">
                    {t(`app.communications.calendar.weekdays.${d.toLowerCase()}` as any, { defaultValue: d })}
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-7 gap-1">
                {monthMeta.days.map((day) => {
                  const key = localDayKeyFromDate(day)
                  const inMonth = day.getMonth() === monthMeta.start.getMonth()
                  const dayEvents = eventsByDay.get(key) || []
                  const counts = {
                    overdue: dayEvents.filter((e) => e.status === 'overdue').length,
                    timeoff: dayEvents.filter((e) => e.source === 'timeoff').length,
                    reminders: dayEvents.filter((e) => e.source === 'reminder').length,
                    planner: dayEvents.filter((e) => e.source === 'planner').length,
                  }
                  const isSelected = key === selectedDay
                  const isToday = key === localDayKeyFromDate(new Date())
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => {
                        setSelectedDay(key)
                        setWeekCursor(startOfWeek(day))
                        openCreateEventModal(key, 9, 0)
                      }}
                      className={clsx('min-h-[96px] overflow-hidden rounded-lg border px-2 py-2 text-left', isSelected ? 'border-brand-500 bg-brand-50' : 'border-slate-200 hover:bg-slate-50', !inMonth && 'opacity-45')}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className={clsx('text-sm', isToday ? 'font-semibold text-brand-700' : 'text-slate-700')}>{day.getDate()}</span>
                        {dayEvents.length > 0 && <span className="text-[10px] text-slate-500">{dayEvents.length}</span>}
                      </div>
                      <div className="mt-2 space-y-1">
                        {counts.overdue > 0 && <div className="badge max-w-full overflow-hidden bg-rose-100 text-rose-800">{t('app.communications.calendar.badges.overdue_count', { defaultValue: 'overdue {count}', values: { count: counts.overdue } })}</div>}
                        {counts.timeoff > 0 && <div className="badge max-w-full overflow-hidden bg-rose-50 text-rose-700">{t('app.communications.calendar.badges.timeoff_count', { defaultValue: 'time-off {count}', values: { count: counts.timeoff } })}</div>}
                        {counts.reminders > 0 && <div className="badge max-w-full overflow-hidden bg-amber-100 text-amber-800">{t('app.communications.calendar.badges.rem_count', { defaultValue: 'rem {count}', values: { count: counts.reminders } })}</div>}
                        {counts.planner > 0 && <div className="badge max-w-full overflow-hidden bg-blue-100 text-blue-800">{t('app.communications.calendar.badges.planner_count', { defaultValue: 'planner {count}', values: { count: counts.planner } })}</div>}
                      </div>
                    </button>
                  )
                })}
              </div>

              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1"><span className="h-2 w-2 rounded-full bg-rose-500" />{t('app.communications.calendar.legend.timeoff', { defaultValue: 'Time-off' })}</span>
                <span className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1"><span className="h-2 w-2 rounded-full bg-amber-500" />{t('app.communications.calendar.legend.reminders', { defaultValue: 'Reminders' })}</span>
                <span className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1"><span className="h-2 w-2 rounded-full bg-blue-500" />{t('app.communications.calendar.legend.planner', { defaultValue: 'Planner' })}</span>
              </div>
            </section>
          )}

          {viewMode === 'week' && (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <button type="button" className="btn-secondary" onClick={() => setWeekCursor((d) => addDays(d, -7))}>
                    {t('app.communications.calendar.navigation.prev', { defaultValue: 'Prev' })}
                  </button>
                  <div className="text-sm font-semibold text-slate-900">
                    {t('app.communications.calendar.week.range', {
                      defaultValue: 'Week: {from} - {to}',
                      values: { from: formatDayLabel(localDayKeyFromDate(weekDays[0])), to: formatDayLabel(localDayKeyFromDate(weekDays[6])) },
                    })}
                  </div>
                  <button type="button" className="btn-secondary" onClick={() => setWeekCursor((d) => addDays(d, 7))}>
                    {t('app.communications.calendar.navigation.next', { defaultValue: 'Next' })}
                  </button>
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  <span className="text-[11px] text-slate-500">{t('app.communications.calendar.week.slot', { defaultValue: 'Slot:' })}</span>
                  {[15, 30, 60].map((step) => (
                    <button
                      key={`week-step-${step}`}
                      type="button"
                      onClick={() => setWeekSlotMinutes(step as WeekSlotMinutes)}
                      className={clsx('btn-secondary btn-xs', weekSlotMinutes === step && 'border-brand-400 bg-brand-50 text-brand-700')}
                    >
                      {step}m
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-3 overflow-auto">
                <div className="min-w-[980px]">
                  <div className="grid grid-cols-[64px_repeat(7,minmax(0,1fr))] border-b border-slate-200">
                    <div className="px-2 py-2 text-[10px] font-semibold uppercase text-slate-500">{t('app.communications.calendar.week.time', { defaultValue: 'Time' })}</div>
                    {weekDays.map((day) => {
                      const key = localDayKeyFromDate(day)
                      return (
                        <button
                          key={`week-head-${key}`}
                          type="button"
                          onClick={() => {
                            setSelectedDay(key)
                            setViewMode('day')
                          }}
                          className={clsx('min-w-0 overflow-hidden border-l border-slate-200 px-2 py-2 text-left', key === selectedDay ? 'bg-brand-50' : 'bg-slate-50 hover:bg-slate-100')}
                        >
                        <div className="truncate text-xs font-semibold text-slate-900">{new Intl.DateTimeFormat(undefined, { weekday: 'short' }).format(day)}</div>
                        <div className="truncate text-[11px] text-slate-500">
                          {formatDayLabel(key)}
                          {key === nowMeta.dayKey && <span className="ml-1 badge bg-rose-100 text-rose-700">{t('app.communications.calendar.week.now', { defaultValue: 'now' })}</span>}
                        </div>
                      </button>
                    )
                  })}
                  </div>

                  <div className="grid grid-cols-[64px_repeat(7,minmax(0,1fr))] border-b border-slate-200">
                    <div className="px-2 py-2 text-[10px] font-semibold uppercase text-slate-500">{t('app.communications.calendar.week.all_day', { defaultValue: 'All-day' })}</div>
                    {weekDays.map((day) => {
                      const key = localDayKeyFromDate(day)
                      const allDayEvents = (eventsByDay.get(key) || []).filter((event) => !event.at).slice(0, 3)
                      return (
                        <div key={`week-all-${key}`} className="min-h-[46px] border-l border-slate-200 px-1 py-1">
                          <div className="space-y-1">
                            {allDayEvents.map((event) => (
                              <div key={`all-${event.id}`} className={clsx('badge border', plannerKindTone(event.kind), 'block w-full overflow-hidden')}>
                                <div className="truncate font-medium">{event.title}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  <div className="max-h-[62vh] overflow-auto">
                    {(() => {
                      const slotsTotal = Math.floor(CALENDAR_DAY_MINUTES / weekSlotMinutes)
                      const columnHeightPx = slotsTotal * CALENDAR_TIMELINE_SLOT_PX
                      return (
                        <div className="flex min-w-[980px]">
                          <div className="flex w-16 flex-shrink-0 flex-col border-r border-slate-200">
                            {Array.from({ length: slotsTotal }).map((_, slotIndex) => {
                              const slot = weekSlotStart(slotIndex, weekSlotMinutes)
                              const hourLabel = `${String(slot.hour).padStart(2, '0')}:${String(slot.minute).padStart(2, '0')}`
                              const majorLine = slot.minute === 0
                              return (
                                <div
                                  key={`week-ruler-${slotIndex}`}
                                  style={{ height: CALENDAR_TIMELINE_SLOT_PX }}
                                  className={clsx(
                                    'flex items-start border-b px-2 pt-0.5 text-[11px]',
                                    majorLine ? 'border-slate-200 text-slate-500' : 'border-slate-100 text-slate-400',
                                  )}
                                >
                                  {hourLabel}
                                </div>
                              )
                            })}
                          </div>
                          <div className="grid min-w-0 flex-1 grid-cols-7">
                            {weekDays.map((day) => {
                              const key = localDayKeyFromDate(day)
                              const timedEvents = (eventsByDay.get(key) || []).filter((ev) => Boolean(ev.at))
                              return (
                                <div
                                  key={`week-col-${key}`}
                                  className={clsx(
                                    'relative border-l border-slate-100',
                                    isDragActive ? 'hover:bg-brand-50/40' : '',
                                  )}
                                  style={{ minHeight: columnHeightPx }}
                                  onClick={(e) => {
                                    if ((e.target as HTMLElement).closest('[data-calendar-event-card]')) return
                                    if (isDragActive) return
                                    const rect = e.currentTarget.getBoundingClientRect()
                                    const minuteOfDay = minuteFromTimelinePointer(e.clientY, rect.top, rect.height, weekSlotMinutes)
                                    openCreateEventModal(key, Math.floor(minuteOfDay / 60), minuteOfDay % 60)
                                  }}
                                  onDragOver={(e) => {
                                    if (isDragActive) e.preventDefault()
                                  }}
                                  onDrop={(e) => {
                                    e.preventDefault()
                                    if (!isDragActive || !dragPlannerEvent) return
                                    const rect = e.currentTarget.getBoundingClientRect()
                                    const minuteOfDay = minuteFromTimelinePointer(e.clientY, rect.top, rect.height, weekSlotMinutes)
                                    const target = parseDate(`${key}T00:00:00`)
                                    if (!target) return
                                    target.setHours(Math.floor(minuteOfDay / 60), minuteOfDay % 60, 0, 0)
                                    void movePlannerEventToDateTime(dragPlannerEvent, target, key)
                                    setDragPlannerEvent(null)
                                  }}
                                >
                                  {Array.from({ length: slotsTotal }).map((_, i) => {
                                    const major = weekSlotStart(i, weekSlotMinutes).minute === 0
                                    return (
                                      <div
                                        key={`week-gridline-${key}-${i}`}
                                        className={clsx(
                                          'pointer-events-none absolute left-0 right-0 border-b',
                                          major ? 'border-slate-200' : 'border-slate-100',
                                        )}
                                        style={{
                                          top: `${(i * weekSlotMinutes * 100) / CALENDAR_DAY_MINUTES}%`,
                                          height: `${(weekSlotMinutes * 100) / CALENDAR_DAY_MINUTES}%`,
                                        }}
                                      />
                                    )
                                  })}
                                  {key === nowMeta.dayKey && (
                                    <div
                                      className="pointer-events-none absolute left-0 right-0 z-[8]"
                                      style={{ top: `${(nowMeta.totalMinutes / CALENDAR_DAY_MINUTES) * 100}%` }}
                                    >
                                      <div className="h-0.5 w-full bg-rose-500" />
                                    </div>
                                  )}
                                  {timedEvents.map((event) => {
                                    const pct = eventTimelinePercents(event, weekSlotMinutes)
                                    if (!pct) return null
                                    return (
                                      <div
                                        key={`week-item-${event.id}`}
                                        data-calendar-event-card
                                        draggable={isCalendarEventDraggable(event)}
                                        onPointerDown={(e) => {
                                          e.stopPropagation()
                                        }}
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          openEventDetailsModal(event)
                                        }}
                                        onDragStart={() => {
                                          if (isCalendarEventDraggable(event)) setDragPlannerEvent(event)
                                        }}
                                        onDragEnd={() => setDragPlannerEvent(null)}
                                        className={clsx(
                                          'badge absolute left-1 right-1 z-[5] overflow-hidden border py-0.5',
                                          plannerKindTone(event.kind),
                                          isCalendarEventDraggable(event) ? 'cursor-move' : '',
                                        )}
                                        style={{ top: `${pct.topPct}%`, height: `${pct.heightPct}%` }}
                                        title={
                                          isCalendarEventDraggable(event)
                                            ? t('app.communications.calendar.week.drag_to_slot', { defaultValue: 'Drag to another slot' })
                                            : undefined
                                        }
                                      >
                                        <div className="truncate text-[11px] font-medium leading-tight">{event.title}</div>
                                        <div className="truncate text-[10px] leading-tight text-slate-600">{formatDateTime(event.at)}</div>
                                      </div>
                                    )
                                  })}
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                </div>
              </div>
            </section>
          )}

          {viewMode === 'day' && (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-slate-900">
                    {t('app.communications.calendar.day.title', {
                      defaultValue: 'Day planner: {day}',
                      values: { day: formatDayLabel(selectedDay) },
                    })}
                  </div>
                  <div className="text-xs text-slate-500">{t('app.communications.calendar.day.subtitle', { defaultValue: 'Meetings, tasks, reminders, and absence context.' })}</div>
                </div>
                <div className="flex flex-wrap gap-1">
                  <button type="button" onClick={() => setViewMode('week')} className="btn-secondary btn-xs">{t('app.communications.calendar.views.week_short', { defaultValue: 'Week' })}</button>
                  <button type="button" onClick={() => setViewMode('month')} className="btn-secondary btn-xs">{t('app.communications.calendar.views.month_short', { defaultValue: 'Month' })}</button>
                </div>
              </div>
              <div className="mb-3 flex flex-wrap gap-1">
                <button type="button" onClick={() => setPlannerSlot(selectedDay, 9)} className="btn-secondary btn-xs">{t('app.communications.calendar.day.slot_9', { defaultValue: '+ 09:00 slot' })}</button>
                <button type="button" onClick={() => setPlannerSlot(selectedDay, 12)} className="btn-secondary btn-xs">{t('app.communications.calendar.day.slot_12', { defaultValue: '+ 12:00 slot' })}</button>
                <button type="button" onClick={() => setPlannerSlot(selectedDay, 15)} className="btn-secondary btn-xs">{t('app.communications.calendar.day.slot_15', { defaultValue: '+ 15:00 slot' })}</button>
                <button type="button" onClick={() => setPlannerSlot(selectedDay, 18)} className="btn-secondary btn-xs">{t('app.communications.calendar.day.slot_18', { defaultValue: '+ 18:00 slot' })}</button>
              </div>
              <details className="mb-3 rounded border border-slate-200">
                <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-slate-800">
                  {t('app.communications.calendar.day.batch_panel', {
                    defaultValue: 'Batch planner ({selected} selected)',
                    values: { selected: selectedPlannerEvents.length },
                  })}
                </summary>
                <div className="space-y-2 border-t border-slate-200 p-3">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                      {t('app.communications.calendar.batch.title', {
                        defaultValue: 'Batch actions for selected planner events ({count})',
                        values: { count: selectedPlannerEvents.length },
                      })}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <button type="button" onClick={selectAllVisiblePlanner} className="btn-secondary btn-xs">{t('app.communications.calendar.batch.select_all_visible', { defaultValue: 'Select all visible' })}</button>
                      <button type="button" onClick={clearPlannerSelection} className="btn-secondary btn-xs">{t('common.clear', { defaultValue: 'Clear' })}</button>
                    </div>
                  </div>
                  <div className="mb-2 rounded border border-slate-200 p-2">
                    <div className="mb-1 text-[10px] font-semibold uppercase text-slate-500">{t('app.communications.calendar.batch.select_by_filter', { defaultValue: 'Select by filter' })}</div>
                    <div className="grid gap-1 md:grid-cols-4">
                      <select value={batchSelectKind} onChange={(e) => setBatchSelectKind(e.target.value)} className="input">
                        <option value="">{t('app.communications.calendar.batch.any_kind', { defaultValue: 'Any kind' })}</option>
                        <option value="meeting">{t('app.communications.calendar.kinds.meeting', { defaultValue: 'Meeting' })}</option>
                        <option value="task">{t('app.communications.calendar.kinds.task', { defaultValue: 'Task' })}</option>
                        <option value="followup">{t('app.communications.calendar.kinds.followup', { defaultValue: 'Follow-up' })}</option>
                        <option value="call">{t('app.communications.calendar.kinds.call', { defaultValue: 'Call' })}</option>
                        <option value="shift">{t('app.communications.calendar.kinds.shift', { defaultValue: 'Shift' })}</option>
                      </select>
                      <select value={batchSelectPriority} onChange={(e) => setBatchSelectPriority(e.target.value)} className="input">
                        <option value="">{t('app.communications.calendar.batch.any_priority', { defaultValue: 'Any priority' })}</option>
                        <option value="low">{t('app.communications.calendar.priority.low', { defaultValue: 'Low' })}</option>
                        <option value="normal">{t('app.communications.calendar.priority.normal', { defaultValue: 'Normal' })}</option>
                        <option value="high">{t('app.communications.calendar.priority.high', { defaultValue: 'High' })}</option>
                      </select>
                      <select value={batchSelectStatus} onChange={(e) => setBatchSelectStatus(e.target.value as BatchSelectStatusFilter)} className="input">
                        <option value="">{t('app.communications.calendar.batch.any_status', { defaultValue: 'Any status' })}</option>
                        <option value="planned">{t('app.communications.calendar.status.planned', { defaultValue: 'Planned' })}</option>
                        <option value="in_progress">{t('app.communications.calendar.status.in_progress', { defaultValue: 'In progress' })}</option>
                        <option value="done">{t('app.communications.calendar.status.done', { defaultValue: 'Done' })}</option>
                        <option value="cancelled">{t('app.communications.calendar.status.cancelled', { defaultValue: 'Cancelled' })}</option>
                      </select>
                      <button type="button" onClick={selectByCurrentBatchFilter} className="btn-secondary btn-xs">
                        {t('app.communications.calendar.batch.select_by_filter_action', { defaultValue: 'Select by filter' })}
                      </button>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      <button type="button" onClick={() => applySelectionPreset('meetings')} className="btn-secondary btn-xs">{t('app.communications.calendar.batch.presets.meetings', { defaultValue: 'Meetings' })}</button>
                      <button type="button" onClick={() => applySelectionPreset('high')} className="btn-secondary btn-xs">{t('app.communications.calendar.batch.presets.high_priority', { defaultValue: 'High priority' })}</button>
                      <button type="button" onClick={() => applySelectionPreset('unassigned')} className="btn-secondary btn-xs">{t('app.communications.calendar.batch.presets.unassigned', { defaultValue: 'Unassigned' })}</button>
                      <button type="button" onClick={() => applySelectionPreset('in_progress')} className="btn-secondary btn-xs">{t('app.communications.calendar.batch.presets.in_progress', { defaultValue: 'In progress' })}</button>
                      <button type="button" onClick={() => applySelectionPreset('due_soon')} className="btn-secondary btn-xs">{t('app.communications.calendar.batch.presets.due_soon', { defaultValue: 'Due soon (2h)' })}</button>
                    </div>
                  </div>
                  <div className="grid gap-2 md:grid-cols-2">
                    <div className="rounded border border-slate-200 p-2">
                      <div className="mb-1 text-[10px] font-semibold uppercase text-slate-500">{t('app.communications.calendar.batch.assign', { defaultValue: 'Assign' })}</div>
                      <div className="flex gap-1">
                        <select value={batchAssigneeId} onChange={(e) => setBatchAssigneeId(e.target.value)} className="w-full input">
                          <option value="">{t('app.communications.calendar.labels.unassigned', { defaultValue: 'Unassigned' })}</option>
                          {managers.map((m) => <option key={`batch-assignee-${m.id}`} value={m.id}>{managerLabelWithState(m.id, m.label)}</option>)}
                        </select>
                        <button type="button" onClick={() => void runBatchAssign()} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">{t('common.apply', { defaultValue: 'Apply' })}</button>
                      </div>
                    </div>
                    <div className="rounded border border-slate-200 p-2">
                      <div className="mb-1 text-[10px] font-semibold uppercase text-slate-500">{t('app.communications.calendar.batch.priority', { defaultValue: 'Priority' })}</div>
                      <div className="flex flex-wrap gap-1">
                        <button type="button" onClick={() => void runBatchPriority('low')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">{t('app.communications.calendar.priority.low', { defaultValue: 'Low' })}</button>
                        <button type="button" onClick={() => void runBatchPriority('normal')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">{t('app.communications.calendar.priority.normal', { defaultValue: 'Normal' })}</button>
                        <button type="button" onClick={() => void runBatchPriority('high')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">{t('app.communications.calendar.priority.high', { defaultValue: 'High' })}</button>
                      </div>
                    </div>
                    <div className="rounded border border-slate-200 p-2 md:col-span-2">
                      <div className="mb-1 text-[10px] font-semibold uppercase text-slate-500">{t('app.communications.calendar.batch.tags', { defaultValue: 'Tags' })}</div>
                      <div className="flex flex-wrap gap-1">
                        <input value={batchTagValue} onChange={(e) => setBatchTagValue(e.target.value)} placeholder={t('app.communications.calendar.batch.tag_placeholder', { defaultValue: 'tag' })} className="input" />
                        <button type="button" onClick={() => void runBatchTag('add')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">{t('common.actions.add', { defaultValue: 'Add' })}</button>
                        <button type="button" onClick={() => void runBatchTag('remove')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">{t('common.actions.remove', { defaultValue: 'Remove' })}</button>
                        <button type="button" onClick={() => void runBatchArchive()} disabled={busy || !selectedPlannerEvents.length} className="ml-auto btn-danger btn-xs disabled:opacity-50">{t('app.communications.calendar.batch.archive_selected', { defaultValue: 'Archive selected' })}</button>
                      </div>
                    </div>
                  </div>
                </div>
              </details>
              <div className="mb-3 rounded border border-slate-200 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">{t('app.communications.calendar.timeline.title', { defaultValue: 'Timeline drag & drop' })}</div>
                  {selectedDay === nowMeta.dayKey && <span className="badge bg-rose-100 text-rose-700">{t('app.communications.calendar.timeline.now', { defaultValue: 'Now {time}', values: { time: nowMeta.label } })}</span>}
                  {resizePlannerEvent?.plannerId && (
                    <button
                      type="button"
                      onClick={() => setResizePlannerEvent(null)}
                      className="btn-secondary btn-xs"
                    >
                      {t('app.communications.calendar.timeline.exit_resize', { defaultValue: 'Exit resize' })}
                    </button>
                  )}
                </div>
                <div className="max-h-[62vh] overflow-auto">
                  {(() => {
                    const slotsTotal = Math.floor(CALENDAR_DAY_MINUTES / weekSlotMinutes)
                    const columnHeightPx = slotsTotal * CALENDAR_TIMELINE_SLOT_PX
                    const timedEvents = dayPlannerEvents.filter((e) => Boolean(e.at))
                    return (
                      <div className="flex">
                        <div className="flex w-16 flex-shrink-0 flex-col border-r border-slate-200">
                          {Array.from({ length: slotsTotal }).map((_, slotIndex) => {
                            const slot = weekSlotStart(slotIndex, weekSlotMinutes)
                            const hourLabel = `${String(slot.hour).padStart(2, '0')}:${String(slot.minute).padStart(2, '0')}`
                            const majorLine = slot.minute === 0
                            return (
                              <div
                                key={`day-ruler-${slotIndex}`}
                                style={{ height: CALENDAR_TIMELINE_SLOT_PX }}
                                className={clsx(
                                  'flex items-start border-b px-2 pt-0.5 text-[11px]',
                                  majorLine ? 'border-slate-200 text-slate-500' : 'border-slate-100 text-slate-400',
                                )}
                              >
                                {hourLabel}
                              </div>
                            )
                          })}
                        </div>
                        <div
                          className={clsx(
                            'relative min-h-0 flex-1 rounded border border-slate-200',
                            selectedDay === nowMeta.dayKey ? 'border-rose-200 bg-rose-50/30' : '',
                            isDragActive ? 'hover:border-brand-300 hover:bg-brand-50/40' : '',
                          )}
                          style={{ minHeight: columnHeightPx }}
                          onClick={(e) => {
                            if ((e.target as HTMLElement).closest('[data-calendar-event-card]')) return
                            if (isDragActive) return
                            const rect = e.currentTarget.getBoundingClientRect()
                            const minuteOfDay = minuteFromTimelinePointer(e.clientY, rect.top, rect.height, weekSlotMinutes)
                            openCreateEventModal(selectedDay, Math.floor(minuteOfDay / 60), minuteOfDay % 60)
                          }}
                          onDragOver={(e) => {
                            if (isDragActive || resizePlannerEvent?.plannerId) e.preventDefault()
                          }}
                          onDrop={(e) => {
                            e.preventDefault()
                            const rect = e.currentTarget.getBoundingClientRect()
                            const minuteOfDay = minuteFromTimelinePointer(e.clientY, rect.top, rect.height, weekSlotMinutes)
                            const hour = Math.floor(minuteOfDay / 60)
                            if (resizePlannerEvent?.plannerId) {
                              void resizePlannerEventToHour(resizePlannerEvent, selectedDay, hour + 1)
                              return
                            }
                            if (isDragActive && dragPlannerEvent) {
                              const target = parseDate(`${selectedDay}T00:00:00`)
                              if (!target) return
                              target.setHours(Math.floor(minuteOfDay / 60), minuteOfDay % 60, 0, 0)
                              void movePlannerEventToDateTime(dragPlannerEvent, target, selectedDay)
                              setDragPlannerEvent(null)
                            }
                          }}
                        >
                          {Array.from({ length: slotsTotal }).map((_, i) => {
                            const major = weekSlotStart(i, weekSlotMinutes).minute === 0
                            return (
                              <div
                                key={`day-gridline-${i}`}
                                className={clsx(
                                  'pointer-events-none absolute left-0 right-0 border-b',
                                  major ? 'border-slate-200' : 'border-slate-100',
                                )}
                                style={{
                                  top: `${(i * weekSlotMinutes * 100) / CALENDAR_DAY_MINUTES}%`,
                                  height: `${(weekSlotMinutes * 100) / CALENDAR_DAY_MINUTES}%`,
                                }}
                              />
                            )
                          })}
                          {selectedDay === nowMeta.dayKey && (
                            <div
                              className="pointer-events-none absolute left-0 right-0 z-[8]"
                              style={{ top: `${(nowMeta.totalMinutes / CALENDAR_DAY_MINUTES) * 100}%` }}
                            >
                              <div className="h-0.5 w-full bg-rose-500" />
                            </div>
                          )}
                          {timedEvents.map((event) => {
                            const pct = eventTimelinePercents(event, weekSlotMinutes)
                            if (!pct) return null
                            return (
                              <div
                                key={`slot-item-${event.id}`}
                                data-calendar-event-card
                                draggable={isCalendarEventDraggable(event)}
                                onPointerDown={(e) => {
                                  e.stopPropagation()
                                }}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  openEventDetailsModal(event)
                                }}
                                onDragStart={() => {
                                  if (isCalendarEventDraggable(event)) setDragPlannerEvent(event)
                                }}
                                onDragEnd={() => setDragPlannerEvent(null)}
                                className={clsx(
                                  'badge absolute left-2 right-2 z-[5] overflow-hidden border px-2 py-1 text-xs',
                                  plannerKindTone(event.kind),
                                  isCalendarEventDraggable(event) ? 'cursor-move' : '',
                                )}
                                style={{ top: `${pct.topPct}%`, height: `${pct.heightPct}%` }}
                                title={t('app.communications.calendar.timeline.drag_to_hour_or_day', {
                                  defaultValue: 'Drag to another hour/day',
                                })}
                              >
                                <div className="flex flex-wrap items-start gap-1">
                                  <span className="min-w-0 flex-1 truncate font-medium">{event.title}</span>
                                  {event.plannerId && (
                                    <button
                                      type="button"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        setResizePlannerEvent(event)
                                      }}
                                      className={clsx(
                                        'btn-secondary btn-xs shrink-0',
                                        resizePlannerEvent?.plannerId === event.plannerId && 'border-brand-400 bg-brand-50 text-brand-700',
                                      )}
                                    >
                                      {t('app.communications.calendar.timeline.resize', { defaultValue: 'resize' })}
                                    </button>
                                  )}
                                </div>
                              </div>
                            )
                          })}
                          {timedEvents.length === 0 && (
                            <span className="pointer-events-none absolute bottom-2 left-2 text-[10px] text-slate-400">
                              {t('app.communications.calendar.timeline.drop_here', { defaultValue: 'drop here' })}
                            </span>
                          )}
                          {resizePlannerEvent?.plannerId && (
                            <span className="pointer-events-none absolute bottom-2 right-2 text-[10px] text-brand-700">
                              {t('app.communications.calendar.timeline.set_end_here', { defaultValue: 'set end here' })}
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })()}
                </div>
              </div>

              <details className="mt-3 rounded border border-slate-200">
                <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-slate-700">
                  {t('app.communications.calendar.day.advanced_buckets', { defaultValue: 'Advanced buckets' })}
                </summary>
                <div className="grid gap-3 p-3 md:grid-cols-3">
                {[
                  { key: 'morning', label: t('app.communications.calendar.day_buckets.morning', { defaultValue: 'Morning (00:00-11:59)' }), items: dayBoard.morning },
                  { key: 'midday', label: t('app.communications.calendar.day_buckets.midday', { defaultValue: 'Day (12:00-16:59)' }), items: dayBoard.midday },
                  { key: 'evening', label: t('app.communications.calendar.day_buckets.evening', { defaultValue: 'Evening (17:00-23:59)' }), items: dayBoard.evening },
                ].map((bucket) => (
                  <div key={bucket.key} className="rounded border border-slate-200 p-3">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">{bucket.label}</div>
                    <div className="space-y-2">
                      {bucket.items.map((event) => (
                        <div
                          key={event.id}
                          id={`hf-cal-ev-${event.id}`}
                          draggable={isCalendarEventDraggable(event)}
                          onClick={() => openEventDetailsModal(event)}
                          onDragStart={() => {
                            if (isCalendarEventDraggable(event)) setDragPlannerEvent(event)
                          }}
                          onDragEnd={() => setDragPlannerEvent(null)}
                          className={clsx(
                            'rounded-lg border px-2 py-2 text-xs',
                            plannerKindTone(event.kind),
                            isCalendarEventDraggable(event) ? 'cursor-move' : '',
                            highlightUnifiedId === event.id ? 'ring-2 ring-brand-500 ring-offset-2' : '',
                          )}
                          title={isCalendarEventDraggable(event) ? t('app.communications.calendar.timeline.drag_to_timeline_or_week', { defaultValue: 'Drag to timeline or week days' }) : undefined}
                        >
                          <div className="flex items-center gap-2">
                            {event.plannerId && (
                              <input
                                type="checkbox"
                                checked={selectedPlannerIds.includes(event.plannerId)}
                                onChange={(e) => togglePlannerSelection(event.plannerId!, e.target.checked)}
                                onClick={(e) => e.stopPropagation()}
                              />
                            )}
                            <div className="font-medium text-slate-900">{event.title}</div>
                          </div>
                          <div className="mt-1 text-slate-600">{event.at ? formatDateTime(event.at) : formatDayLabel(event.dateKey)}</div>
                          {event.subtitle && <div className="mt-1 text-slate-600">{event.subtitle}</div>}
                          <div className="mt-2 flex flex-wrap gap-1">
                            {(event.plannerId || event.integratedItemId) && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  void cancelUnifiedEvent(event)
                                }}
                                disabled={busy}
                                className="btn-danger btn-xs disabled:opacity-50"
                              >
                                ×
                              </button>
                            )}
                            <span className={clsx('badge', sourceBadgeClass(event.source))}>{event.source}</span>
                            <span className={clsx('badge', statusBadgeClass(event.status))}>{event.status}</span>
                            {event.priority && <span className="badge bg-slate-100 text-slate-700">{event.priority}</span>}
                            {event.tags?.map((tag) => (
                              <span key={`${event.id}:tag:${tag}`} className="badge bg-brand-50 text-brand-700">#{tag}</span>
                            ))}
                          </div>
                          {event.detail && <div className="mt-1 whitespace-pre-wrap text-slate-600">{event.detail}</div>}
                          <div className="mt-2 flex flex-wrap gap-1">
                            {event.plannerId && (
                              <>
                                <button type="button" onClick={() => void setPlannerStatus(event.plannerId!, 'in_progress')} disabled={busy || event.plannerStatus === 'in_progress'} className="btn-secondary btn-xs disabled:opacity-50">{t('app.communications.calendar.actions.start', { defaultValue: 'Start' })}</button>
                                <button type="button" onClick={() => void setPlannerStatus(event.plannerId!, 'done')} disabled={busy || event.plannerStatus === 'done'} className="btn-primary btn-xs disabled:opacity-50">{t('app.communications.calendar.status.done', { defaultValue: 'Done' })}</button>
                                <button type="button" onClick={() => void setPlannerStatus(event.plannerId!, 'planned')} disabled={busy || event.plannerStatus === 'planned'} className="btn-secondary btn-xs disabled:opacity-50">{t('app.communications.calendar.actions.reopen', { defaultValue: 'Reopen' })}</button>
                                <button type="button" onClick={() => void setPlannerStatus(event.plannerId!, 'cancelled')} disabled={busy || event.plannerStatus === 'cancelled'} className="btn-secondary btn-xs disabled:opacity-50">{t('app.communications.calendar.actions.cancel', { defaultValue: 'Cancel' })}</button>
                                <button type="button" onClick={() => void movePlannerEvent(event, 60)} disabled={busy || !event.at} className="btn-secondary btn-xs disabled:opacity-50">
                                  {t('app.communications.calendar.actions.move_plus_1h', { defaultValue: '+1h' })}
                                </button>
                                <button type="button" onClick={() => void movePlannerEvent(event, 1440)} disabled={busy || !event.at} className="btn-secondary btn-xs disabled:opacity-50">
                                  {t('app.communications.calendar.actions.move_plus_1d', { defaultValue: '+1d' })}
                                </button>
                                <button type="button" onClick={() => void duplicatePlannerEvent(event)} disabled={busy || !event.at} className="btn-secondary btn-xs disabled:opacity-50">{t('app.communications.calendar.actions.duplicate', { defaultValue: 'Duplicate' })}</button>
                                <button
                                  type="button"
                                  onClick={() => setResizePlannerEvent(event)}
                                  disabled={busy}
                                  className={clsx('btn-secondary btn-xs disabled:opacity-50', resizePlannerEvent?.plannerId === event.plannerId && 'border-brand-400 bg-brand-50 text-brand-700')}
                                >
                                  {t('app.communications.calendar.timeline.resize', { defaultValue: 'resize' })}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setActivePlannerMenuId((prev) => (prev === event.plannerId ? null : event.plannerId!))}
                                  className={clsx('btn-secondary btn-xs', activePlannerMenuId === event.plannerId && 'border-brand-400 bg-brand-50 text-brand-700')}
                                >
                                  {t('app.communications.calendar.actions.manage', { defaultValue: 'Manage' })}
                                </button>
                              </>
                            )}
                            {event.reminderId && (
                              <>
                                <button type="button" onClick={() => void completeDayReminder(event.reminderId!)} disabled={busy || ['done', 'completed', 'cancelled'].includes(String(event.reminderStatus || '').toLowerCase())} className="btn-primary btn-xs disabled:opacity-50">{t('app.communications.calendar.actions.complete', { defaultValue: 'Complete' })}</button>
                                <button type="button" onClick={() => void snoozeDayReminder(event.reminderId!, 30)} disabled={busy || ['done', 'completed', 'cancelled'].includes(String(event.reminderStatus || '').toLowerCase())} className="btn-secondary btn-xs disabled:opacity-50">
                                  {t('app.communications.calendar.actions.snooze_30m', { defaultValue: 'Snooze 30m' })}
                                </button>
                              </>
                            )}
                            {event.entityPath && (
                              <Link to={event.entityPath} className="btn-secondary btn-xs">
                                {t('app.communications.calendar.actions.open', { defaultValue: 'Open' })}
                              </Link>
                            )}
                          </div>
                          {event.plannerId && activePlannerMenuId === event.plannerId && (
                            <div className="mt-2 rounded border border-slate-200 bg-white p-2 text-[10px] text-slate-700">
                              <div className="mb-1 font-semibold text-slate-800">{t('app.communications.calendar.actions.quick_actions', { defaultValue: 'Quick actions' })}</div>
                              <div className="mb-1 flex flex-wrap gap-1">
                                <button type="button" onClick={() => void setPlannerPriorityByEvent(event, 'low')} disabled={busy} className="btn-secondary btn-xs disabled:opacity-50">
                                  {t('app.communications.calendar.actions.priority_low', { defaultValue: 'P:low' })}
                                </button>
                                <button type="button" onClick={() => void setPlannerPriorityByEvent(event, 'normal')} disabled={busy} className="btn-secondary btn-xs disabled:opacity-50">
                                  {t('app.communications.calendar.actions.priority_normal', { defaultValue: 'P:normal' })}
                                </button>
                                <button type="button" onClick={() => void setPlannerPriorityByEvent(event, 'high')} disabled={busy} className="btn-secondary btn-xs disabled:opacity-50">
                                  {t('app.communications.calendar.actions.priority_high', { defaultValue: 'P:high' })}
                                </button>
                              </div>
                              <div className="mb-1">
                                <select
                                  value={String(event.assigneeId || '')}
                                  onChange={(e) => { void assignPlannerByEvent(event, e.target.value) }}
                                  disabled={busy}
                                  className="w-full input disabled:bg-slate-100"
                                >
                                  <option value="">{t('app.communications.calendar.labels.unassigned', { defaultValue: 'Unassigned' })}</option>
                                  {managers.map((m) => <option key={`${event.id}:mgr:${m.id}`} value={m.id}>{managerLabelWithState(m.id, m.label)}</option>)}
                                </select>
                              </div>
                              <div className="mb-1 flex flex-wrap gap-1">
                                {['urgent', 'client', 'followup'].map((tag) => (
                                  <button
                                    key={`${event.id}:toggle-tag:${tag}`}
                                    type="button"
                                    onClick={() => { void togglePlannerTag(event, tag) }}
                                    disabled={busy}
                                    className={clsx('btn-secondary btn-xs disabled:opacity-50', event.tags?.includes(tag) && 'border-brand-400 bg-brand-50 text-brand-700')}
                                  >
                                    #{tag}
                                  </button>
                                ))}
                              </div>
                              <div className="flex flex-wrap gap-1">
                                <button type="button" onClick={() => { void archivePlannerByEvent(event) }} disabled={busy || event.plannerStatus === 'cancelled'} className="btn-danger btn-xs disabled:opacity-50">{t('app.communications.calendar.actions.archive', { defaultValue: 'Archive' })}</button>
                                <button type="button" onClick={() => setActivePlannerMenuId(null)} className="btn-secondary btn-xs">{t('common.actions.close', { defaultValue: 'Close' })}</button>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                      {bucket.items.length === 0 && <div className="text-xs text-slate-500">{t('app.communications.calendar.labels.no_items', { defaultValue: 'No items' })}</div>}
                    </div>
                  </div>
                ))}
                </div>
              </details>
              <div className="mt-3 rounded border border-slate-200 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">{t('app.communications.calendar.team_load.title', { defaultValue: 'Team load for selected day' })}</div>
                <div className="mt-2 space-y-1">
                  {loadByAssigneeToday.map((row) => (
                    <div key={row.label} className="flex items-center justify-between gap-2 rounded border border-slate-100 px-2 py-1 text-xs">
                      <span className="truncate text-slate-700">{row.label}</span>
                      <span className="text-slate-500">
                        {t('app.communications.calendar.team_load.row', {
                          defaultValue: 'total {total} | mtg {meetings} | task {tasks} | overdue {overdue}',
                          values: { total: row.total, meetings: row.meetings, tasks: row.tasks, overdue: row.overdue },
                        })}
                      </span>
                    </div>
                  ))}
                  {loadByAssigneeToday.length === 0 && <div className="text-xs text-slate-500">{t('app.communications.calendar.team_load.empty', { defaultValue: 'No assigned workload for this day.' })}</div>}
                </div>
              </div>
            </section>
          )}
        </div>

        {showAdvancedTools && <div className="space-y-4">
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-2 text-sm font-semibold text-slate-900">
              {t('app.communications.calendar.forms.create_planner', { defaultValue: 'Create meeting / task' })}
            </div>
            <form className="space-y-2" onSubmit={createPlanner}>
              <input value={plannerForm.title} onChange={(e) => setPlannerForm((p) => ({ ...p, title: e.target.value }))} className="w-full input" placeholder={t('common.actions.title', { defaultValue: 'Title' })} />
              <div className="grid grid-cols-2 gap-2">
                <select value={plannerForm.kind} onChange={(e) => setPlannerForm((p) => ({ ...p, kind: e.target.value }))} className="input">
                  <option value="meeting">{t('app.communications.calendar.kinds.meeting', { defaultValue: 'Meeting' })}</option>
                  <option value="task">{t('app.communications.calendar.kinds.task', { defaultValue: 'Task' })}</option>
                  <option value="followup">{t('app.communications.calendar.kinds.followup', { defaultValue: 'Follow-up' })}</option>
                  <option value="call">{t('app.communications.calendar.kinds.call', { defaultValue: 'Call' })}</option>
                  <option value="shift">{t('app.communications.calendar.kinds.shift', { defaultValue: 'Shift' })}</option>
                </select>
                <select value={plannerForm.priority} onChange={(e) => setPlannerForm((p) => ({ ...p, priority: e.target.value }))} className="input">
                  <option value="low">{t('app.communications.calendar.priority.low', { defaultValue: 'Low' })}</option>
                  <option value="normal">{t('app.communications.calendar.priority.normal', { defaultValue: 'Normal' })}</option>
                  <option value="high">{t('app.communications.calendar.priority.high', { defaultValue: 'High' })}</option>
                </select>
              </div>
              <select value={plannerForm.assigneeId} onChange={(e) => setPlannerForm((p) => ({ ...p, assigneeId: e.target.value }))} className="w-full input">
                <option value="">{t('app.communications.calendar.labels.unassigned', { defaultValue: 'Unassigned' })}</option>
                {managers.map((m) => <option key={m.id} value={m.id}>{managerLabelWithState(m.id, m.label)}</option>)}
              </select>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={plannerForm.allDay} onChange={(e) => setPlannerForm((p) => ({ ...p, allDay: e.target.checked }))} />
                {t('app.communications.calendar.forms.all_day', { defaultValue: 'All day' })}
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={allowOutsideHours} onChange={(e) => setAllowOutsideHours(e.target.checked)} />
                {t('app.communications.calendar.forms.outside_working_hours', { defaultValue: 'Create outside working hours' })}
              </label>
              <div className="grid grid-cols-2 gap-2">
                <select value={plannerForm.repeatMode} onChange={(e) => setPlannerForm((p) => ({ ...p, repeatMode: e.target.value as PlannerRepeatMode }))} className="input">
                  <option value="none">{t('app.communications.calendar.repeat.none', { defaultValue: 'No repeat' })}</option>
                  <option value="daily">{t('app.communications.calendar.repeat.daily', { defaultValue: 'Repeat daily' })}</option>
                  <option value="weekdays">{t('app.communications.calendar.repeat.weekdays', { defaultValue: 'Repeat weekdays' })}</option>
                </select>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={String(plannerForm.repeatCount)}
                  onChange={(e) => setPlannerForm((p) => ({ ...p, repeatCount: Number(e.target.value || 1) }))}
                  disabled={plannerForm.repeatMode === 'none'}
                  className="input disabled:bg-slate-100"
                  placeholder={t('app.communications.calendar.forms.occurrences', { defaultValue: 'Occurrences' })}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input type={plannerForm.allDay ? 'date' : 'datetime-local'} value={plannerForm.startAt} onChange={(e) => setPlannerForm((p) => ({ ...p, startAt: e.target.value }))} className="input" />
                <input type={plannerForm.allDay ? 'date' : 'datetime-local'} value={plannerForm.endAt} onChange={(e) => setPlannerForm((p) => ({ ...p, endAt: e.target.value }))} className="input" />
              </div>
              <textarea rows={3} value={plannerForm.description} onChange={(e) => setPlannerForm((p) => ({ ...p, description: e.target.value }))} className="w-full textarea" placeholder={t('app.communications.calendar.forms.description', { defaultValue: 'Description' })} />
              <button type="submit" disabled={busy || !plannerForm.title.trim() || !plannerForm.startAt} className="btn-primary disabled:opacity-50">
                {busy ? t('common.loading') : t('common.actions.create', { defaultValue: 'Create' })}
              </button>
            </form>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-2 text-sm font-semibold text-slate-900">
              {t('app.communications.calendar.forms.create_activity', { defaultValue: 'Create activity' })}
            </div>
            <form className="space-y-2" onSubmit={createDayReminder}>
              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.communications.calendar.forms.quick_type', { defaultValue: 'Quick type' })}</div>
                <div className="flex flex-wrap gap-2">
                  {ACTIVITY_TEMPLATES.map((tmpl) => (
                    <button
                      key={tmpl.key}
                      type="button"
                      className={clsx(
                        'rounded-lg border px-3 py-2 text-xs font-medium transition',
                        reminderForm.type === tmpl.type
                          ? 'border-brand-500 bg-brand-100 text-brand-800'
                          : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
                      )}
                      disabled={busy}
                      onClick={() => {
                        setReminderForm((p) => ({
                          ...p,
                          type: tmpl.type,
                          title: p.title.trim() ? p.title : tmpl.defaultTitle,
                          offsetMinutes: tmpl.defaultOffsetMinutes,
                        }))
                      }}
                    >
                      {tmpl.defaultTitle}
                    </button>
                  ))}
                  <button
                    type="button"
                    className={clsx(
                      'rounded-lg border px-3 py-2 text-xs font-medium transition',
                      reminderForm.type === 'custom'
                        ? 'border-brand-500 bg-brand-100 text-brand-800'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
                    )}
                    disabled={busy}
                    onClick={() => setReminderForm((p) => ({ ...p, type: 'custom' }))}
                  >
                    {t('app.communications.calendar.forms.custom', { defaultValue: 'Custom' })}
                  </button>
                </div>
              </div>
              <input value={reminderForm.title} onChange={(e) => setReminderForm((p) => ({ ...p, title: e.target.value }))} className="w-full input" placeholder={t('app.communications.calendar.forms.activity_title', { defaultValue: 'Activity title' })} />
              <div className="grid grid-cols-2 gap-2">
                <input type="datetime-local" value={reminderForm.dueAt} onChange={(e) => setReminderForm((p) => ({ ...p, dueAt: e.target.value }))} className="input" />
                <input type="number" min={1} value={String(reminderForm.offsetMinutes)} onChange={(e) => setReminderForm((p) => ({ ...p, offsetMinutes: Number(e.target.value || 30) }))} className="input" placeholder={t('app.communications.calendar.forms.offset_min', { defaultValue: 'Offset min' })} />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <select value={reminderForm.assigneeId} onChange={(e) => setReminderForm((p) => ({ ...p, assigneeId: e.target.value }))} className="input">
                  <option value="">{t('app.communications.calendar.labels.unassigned', { defaultValue: 'Unassigned' })}</option>
                  {managers.map((m) => <option key={m.id} value={m.id}>{managerLabelWithState(m.id, m.label)}</option>)}
                </select>
                <select value={reminderForm.priority} onChange={(e) => setReminderForm((p) => ({ ...p, priority: e.target.value }))} className="input">
                  <option value="low">{t('app.communications.calendar.priority.low', { defaultValue: 'Low' })}</option>
                  <option value="normal">{t('app.communications.calendar.priority.normal', { defaultValue: 'Normal' })}</option>
                  <option value="high">{t('app.communications.calendar.priority.high', { defaultValue: 'High' })}</option>
                </select>
              </div>
              <textarea rows={3} value={reminderForm.description} onChange={(e) => setReminderForm((p) => ({ ...p, description: e.target.value }))} className="w-full textarea" placeholder={t('app.communications.calendar.forms.description', { defaultValue: 'Description' })} />
              <button type="submit" disabled={busy || !reminderForm.title.trim() || !reminderForm.dueAt} className="btn-primary disabled:opacity-50">
                {busy ? t('common.loading') : t('common.actions.create', { defaultValue: 'Create' })}
              </button>
            </form>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-2 text-sm font-semibold text-slate-900">
              {t('app.communications.calendar.settings.notifications', { defaultValue: 'Notification settings' })}
            </div>
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <label className="text-sm text-slate-700">
                  {t('app.communications.calendar.forms.default_reminder', { defaultValue: 'Default reminder' })}
                </label>
                <select
                  value={Number(notificationSettings.default_reminder_minutes || 30)}
                  onChange={(e) => setNotificationSettings((p) => ({ ...p, default_reminder_minutes: Number(e.target.value || 30) }))}
                  className="input"
                >
                  <option value={0}>{t('app.communications.calendar.forms.remind_none', { defaultValue: 'No reminder' })}</option>
                  <option value={5}>5 min</option>
                  <option value={10}>10 min</option>
                  <option value={15}>15 min</option>
                  <option value={30}>30 min</option>
                  <option value={60}>60 min</option>
                </select>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={Boolean(notificationSettings.channels?.in_app)}
                    onChange={(e) =>
                      setNotificationSettings((p) => ({ ...p, channels: { ...(p.channels || DEFAULT_NOTIFICATION_SETTINGS.channels), in_app: e.target.checked } }))
                    }
                  />
                  In-app
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={Boolean(notificationSettings.channels?.push)}
                    onChange={(e) =>
                      setNotificationSettings((p) => ({ ...p, channels: { ...(p.channels || DEFAULT_NOTIFICATION_SETTINGS.channels), push: e.target.checked } }))
                    }
                  />
                  Push
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={Boolean(notificationSettings.channels?.email)}
                    onChange={(e) =>
                      setNotificationSettings((p) => ({ ...p, channels: { ...(p.channels || DEFAULT_NOTIFICATION_SETTINGS.channels), email: e.target.checked } }))
                    }
                  />
                  Email
                </label>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={Boolean(notificationSettings.quiet_hours_enabled)}
                  onChange={(e) => setNotificationSettings((p) => ({ ...p, quiet_hours_enabled: e.target.checked }))}
                />
                {t('app.communications.calendar.settings.quiet_hours', { defaultValue: 'Quiet hours' })}
              </label>
              {notificationSettings.quiet_hours_enabled && (
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="time"
                    value={String(notificationSettings.quiet_hours_start || '22:00')}
                    onChange={(e) => setNotificationSettings((p) => ({ ...p, quiet_hours_start: e.target.value }))}
                    className="input"
                  />
                  <input
                    type="time"
                    value={String(notificationSettings.quiet_hours_end || '08:00')}
                    onChange={(e) => setNotificationSettings((p) => ({ ...p, quiet_hours_end: e.target.value }))}
                    className="input"
                  />
                </div>
              )}
              <button type="button" onClick={() => void saveNotificationSettings()} disabled={notificationSettingsSaving} className="btn-secondary disabled:opacity-50">
                {notificationSettingsSaving ? t('common.loading') : t('common.actions.save', { defaultValue: 'Save' })}
              </button>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-sm font-semibold text-slate-900">
              {t('app.communications.calendar.upcoming.title', { defaultValue: 'Upcoming events' })}
            </div>
            <div className="mt-3 max-h-[26rem] space-y-2 overflow-auto">
              {upcoming.map((event) => (
                <div key={`up:${event.id}`} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium text-slate-900">{event.title}</div>
                    <span className={clsx('badge', sourceBadgeClass(event.source))}>{event.source}</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{formatDayLabel(event.dateKey)}{event.at ? ` · ${formatDateTime(event.at)}` : ''}</div>
                  {event.subtitle && <div className="mt-1 text-xs text-slate-600">{event.subtitle}</div>}
                </div>
              ))}
              {!upcoming.length && <div className="text-sm text-slate-500">{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</div>}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to={CRM_APP_PATHS.tasks} className="btn-secondary">
                {t('app.nav.items.tasks', { defaultValue: 'Tasks' })}
              </Link>
            </div>
          </section>
        </div>}
      </div>

      {eventModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-lg rounded-xl bg-white p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-base font-semibold text-slate-900">
                {eventModalEvent
                  ? t('app.communications.calendar.modal.event_details', { defaultValue: 'Event details' })
                  : t('app.communications.calendar.modal.create_event', { defaultValue: 'Create event' })}
              </div>
              <button type="button" onClick={() => setEventModalOpen(false)} className="btn-secondary btn-xs">×</button>
            </div>
            <form className="space-y-2" onSubmit={submitEventModal}>
              {!eventModalEvent && (
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setEventModalType('task')
                      setEventModalKind(taskPrefs.defaultTaskKind)
                    }}
                    className={clsx('btn-secondary', eventModalType === 'task' && 'border-brand-500 bg-brand-50 text-brand-700')}
                  >
                    {t('app.communications.calendar.kinds.task', { defaultValue: 'Task' })}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEventModalType('meeting')
                      if (['task', 'followup'].includes(String(eventModalKind || '').toLowerCase())) {
                        setEventModalKind('meeting')
                      }
                    }}
                    className={clsx('btn-secondary', eventModalType === 'meeting' && 'border-brand-500 bg-brand-50 text-brand-700')}
                  >
                    {t('app.communications.calendar.kinds.meeting', { defaultValue: 'Meeting' })}
                  </button>
                </div>
              )}
              <input
                value={eventModalTitle}
                onChange={(e) => setEventModalTitle(e.target.value)}
                className="w-full input"
                placeholder={t('common.actions.title', { defaultValue: 'Title' })}
              />
              <div className="grid grid-cols-2 gap-2">
                {eventModalType === 'task' ? (
                  <select
                    value={eventModalKind}
                    onChange={(e) => setEventModalKind(e.target.value)}
                    className="input"
                  >
                    {TASK_KIND_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{t(`app.communications.calendar.kinds.${opt.value}` as any, { defaultValue: opt.label })}</option>
                    ))}
                  </select>
                ) : (
                  <select
                    value={eventModalKind}
                    onChange={(e) => setEventModalKind(e.target.value)}
                    className="input"
                  >
                    <option value="meeting">{t('app.communications.calendar.kinds.meeting', { defaultValue: 'Meeting' })}</option>
                    <option value="call">{t('app.communications.calendar.kinds.call', { defaultValue: 'Call' })}</option>
                  </select>
                )}
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={eventModalAllDay}
                    onChange={(e) => setEventModalAllDay(e.target.checked)}
                  />
                  {t('app.communications.calendar.forms.all_day', { defaultValue: 'All day' })}
                </label>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type={eventModalAllDay ? 'date' : 'datetime-local'}
                  value={eventModalStartAt}
                  onChange={(e) => setEventModalStartAt(e.target.value)}
                  className="input"
                />
                <input
                  type={eventModalAllDay ? 'date' : 'datetime-local'}
                  value={eventModalEndAt}
                  onChange={(e) => setEventModalEndAt(e.target.value)}
                  className="input"
                />
              </div>
              <div className="grid grid-cols-[1fr_auto] gap-2">
                <select
                  value={eventModalAssigneeId}
                  onChange={(e) => setEventModalAssigneeId(e.target.value)}
                  className="input"
                >
                  <option value="">{t('app.communications.calendar.labels.unassigned', { defaultValue: 'Unassigned' })}</option>
                  {managers.map((m) => <option key={`modal-assignee-${m.id}`} value={m.id}>{managerLabelWithState(m.id, m.label)}</option>)}
                </select>
                <button type="button" className="btn-secondary" onClick={() => setEventModalAssigneeId(recommendedAssigneeId || '')}>
                  {t('app.communications.calendar.actions.best_assignee', { defaultValue: 'Best available' })}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="text-sm text-slate-700">
                  {t('app.communications.calendar.forms.remind_before', { defaultValue: 'Remind before' })}
                </label>
                <select
                  value={eventModalRemindMinutes}
                  onChange={(e) => setEventModalRemindMinutes(Number(e.target.value || 0))}
                  className="input"
                >
                  <option value={0}>{t('app.communications.calendar.forms.remind_none', { defaultValue: 'No reminder' })}</option>
                  <option value={5}>5 min</option>
                  <option value={10}>10 min</option>
                  <option value={15}>15 min</option>
                  <option value={30}>30 min</option>
                  <option value={60}>60 min</option>
                </select>
              </div>
              {eventModalType === 'meeting' && (
                <div className="grid grid-cols-1 gap-2">
                  <input
                    value={eventModalLocation}
                    onChange={(e) => setEventModalLocation(e.target.value)}
                    className="w-full input"
                    placeholder={t('app.communications.calendar.forms.location', { defaultValue: 'Location / link' })}
                  />
                  <div className="space-y-2 rounded border border-slate-200 p-2">
                    {eventModalParticipants.map((p) => (
                      <div key={p.id} className="space-y-1">
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_1fr_auto_auto] sm:items-start">
                          <input
                            value={p.name}
                            onChange={(e) => setEventModalParticipants((prev) => prev.map((x) => (x.id === p.id ? { ...x, name: e.target.value } : x)))}
                            className="input"
                            placeholder={t('app.communications.calendar.forms.attendee_name', { defaultValue: 'Name' })}
                          />
                          <input
                            value={p.email}
                            onChange={(e) => {
                              setEventModalParticipants((prev) => prev.map((x) => (x.id === p.id ? { ...x, email: e.target.value } : x)))
                              setEventModalParticipantErrors((er) => {
                                if (!er[p.id]) return er
                                const n = { ...er }
                                delete n[p.id]
                                return n
                              })
                            }}
                            onPaste={(e) => onParticipantEmailPaste(p.id, e)}
                            onKeyDown={(e) => onParticipantEmailKeyDown(p.id, e)}
                            className={clsx('input', eventModalParticipantErrors[p.id] && 'border-rose-500 ring-1 ring-red-200')}
                            placeholder={t('app.communications.calendar.forms.attendee_email', { defaultValue: 'Email' })}
                          />
                          <select
                            value={p.response_status}
                            onChange={(e) =>
                              setEventModalParticipants((prev) =>
                                prev.map((x) => (x.id === p.id ? { ...x, response_status: e.target.value as EventModalParticipant['response_status'] } : x)),
                              )
                            }
                            className="input"
                          >
                            <option value="">{t('app.communications.calendar.rsvp.needs_action', { defaultValue: 'Needs action' })}</option>
                            <option value="accepted">{t('app.communications.calendar.rsvp.accepted', { defaultValue: 'Accepted' })}</option>
                            <option value="tentative">{t('app.communications.calendar.rsvp.tentative', { defaultValue: 'Tentative' })}</option>
                            <option value="declined">{t('app.communications.calendar.rsvp.declined', { defaultValue: 'Declined' })}</option>
                          </select>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => {
                              setEventModalParticipants((prev) => prev.filter((x) => x.id !== p.id))
                              setEventModalParticipantErrors((er) => {
                                if (!er[p.id]) return er
                                const n = { ...er }
                                delete n[p.id]
                                return n
                              })
                            }}
                          >
                            {t('common.actions.remove', { defaultValue: 'Remove' })}
                          </button>
                        </div>
                        {eventModalParticipantErrors[p.id] ? (
                          <p className="text-xs text-rose-600 sm:col-span-4">{eventModalParticipantErrors[p.id]}</p>
                        ) : null}
                      </div>
                    ))}
                    <button
                      type="button"
                      className="btn-secondary btn-xs"
                      onClick={() =>
                        setEventModalParticipants((prev) => [
                          ...prev,
                          { id: `p-new-${Date.now()}`, name: '', email: '', response_status: '' },
                        ])
                      }
                    >
                      {t('common.actions.add', { defaultValue: 'Add' })} attendee
                    </button>
                  </div>
                  <input
                    value={eventModalMeetingLink}
                    onChange={(e) => setEventModalMeetingLink(e.target.value)}
                    className="w-full input"
                    placeholder={t('app.communications.calendar.forms.meeting_link', { defaultValue: 'Meeting link (Google Meet / Teams)' })}
                  />
                  <label className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={eventModalOnlineMeeting}
                      onChange={(e) => setEventModalOnlineMeeting(e.target.checked)}
                    />
                    {t('app.communications.calendar.forms.online_meeting', { defaultValue: 'Online meeting' })}
                  </label>
                </div>
              )}
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={eventModalAllowUnavailableAssignee}
                  onChange={(e) => setEventModalAllowUnavailableAssignee(e.target.checked)}
                />
                {t('app.communications.calendar.forms.allow_unavailable_assignee', { defaultValue: 'Allow assignment if team member is unavailable' })}
              </label>
              {!eventModalEvent && (
                <div className="grid grid-cols-2 gap-2">
                  <label className="text-sm text-slate-700">
                    {t('app.communications.calendar.forms.default_task_type', { defaultValue: 'Default task type' })}
                  </label>
                  <select
                    value={taskPrefs.defaultTaskKind}
                    onChange={(e) => setTaskPrefs((p) => ({ ...p, defaultTaskKind: e.target.value as TaskKind }))}
                    className="input"
                  >
                    {TASK_KIND_OPTIONS.map((opt) => (
                      <option key={`pref-kind-${opt.value}`} value={opt.value}>{t(`app.communications.calendar.kinds.${opt.value}` as any, { defaultValue: opt.label })}</option>
                    ))}
                  </select>
                  <label className="text-sm text-slate-700">
                    {t('app.communications.calendar.forms.default_reminder', { defaultValue: 'Default reminder' })}
                  </label>
                  <select
                    value={taskPrefs.defaultRemindMinutes}
                    onChange={(e) => setTaskPrefs((p) => ({ ...p, defaultRemindMinutes: Number(e.target.value || 30) }))}
                    className="input"
                  >
                    <option value={0}>{t('app.communications.calendar.forms.remind_none', { defaultValue: 'No reminder' })}</option>
                    <option value={5}>5 min</option>
                    <option value={10}>10 min</option>
                    <option value={15}>15 min</option>
                    <option value={30}>30 min</option>
                    <option value={60}>60 min</option>
                  </select>
                </div>
              )}
              <textarea
                rows={3}
                value={eventModalDescription}
                onChange={(e) => setEventModalDescription(e.target.value)}
                className="w-full textarea"
                placeholder={t('app.communications.calendar.forms.description', { defaultValue: 'Description' })}
              />
              <div className="flex items-center justify-between gap-2 pt-1">
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => setEventModalOpen(false)} className="btn-secondary">
                    {t('common.actions.close', { defaultValue: 'Close' })}
                  </button>
                  {eventModalEvent && (eventModalEvent.plannerId || eventModalEvent.integratedItemId || eventModalEvent.reminderId) && (
                    <button
                      type="button"
                      onClick={() => void cancelUnifiedEvent(eventModalEvent)}
                      disabled={busy}
                      className="btn-danger disabled:opacity-50"
                    >
                      {t('app.communications.calendar.actions.cancel', { defaultValue: 'Cancel' })}
                    </button>
                  )}
                  {eventModalEvent?.plannerId && (
                    <button
                      type="button"
                      onClick={() => void setPlannerStatus(eventModalEvent.plannerId!, 'done')}
                      disabled={
                        busy ||
                        eventModalEvent.plannerStatus === 'done' ||
                        eventModalEvent.plannerStatus === 'cancelled'
                      }
                      className="btn-primary disabled:opacity-50"
                    >
                      {t('app.communications.calendar.actions.complete', { defaultValue: 'Complete' })}
                    </button>
                  )}
                  {eventModalEvent?.reminderId && !eventModalEvent.plannerId && (
                    <button
                      type="button"
                      onClick={() => void completeDayReminder(eventModalEvent.reminderId!)}
                      disabled={
                        busy ||
                        ['done', 'completed', 'cancelled'].includes(String(eventModalEvent.reminderStatus || '').toLowerCase())
                      }
                      className="btn-primary disabled:opacity-50"
                    >
                      {t('app.communications.calendar.actions.complete', { defaultValue: 'Complete' })}
                    </button>
                  )}
                </div>
                <button type="submit" disabled={busy} className="btn-primary disabled:opacity-50">
                  {busy
                    ? t('common.loading')
                    : eventModalEvent
                      ? t('common.actions.save', { defaultValue: 'Save' })
                      : t('common.actions.create', { defaultValue: 'Create' })}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      </div>
    </>
  )

  if (embedded) {
    return calendarContent
  }

  return (
    <PageShell>
      <WorkspaceTopNav active="calendar" />
      {calendarContent}
    </PageShell>
  )
}
