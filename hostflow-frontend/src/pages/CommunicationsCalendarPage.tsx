import clsx from 'clsx'
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import { completeReminder, createReminder, listManagers, listReminders, snoozeReminder } from '../api/client'
import {
  createCommunicationPlannerEvent,
  listCommunicationPlannerEvents,
  listCommunicationTimeOffRequests,
  patchCommunicationPlannerEvent,
  type CommunicationPlannerEvent,
  type CommunicationTimeOffRequest,
} from '../api/communications'
import { useI18n } from '../i18n'

type CalendarSourceFilter = 'all' | 'timeoff' | 'reminders' | 'planner'
type TimeOffStatusFilter = 'approved' | 'pending' | 'all'
type ViewMode = 'month' | 'week' | 'day'
type PlannerRepeatMode = 'none' | 'daily' | 'weekdays'
type BatchSelectStatusFilter = '' | 'planned' | 'in_progress' | 'done' | 'cancelled'
type WeekSlotMinutes = 15 | 30 | 60

const CALENDAR_BATCH_STORAGE_KEY = 'hf:calendar:batch:v1'

type UnifiedCalendarEvent = {
  id: string
  dateKey: string
  source: 'timeoff' | 'reminder' | 'planner'
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

function weekSlotIndex(dt: Date, slotMinutes: WeekSlotMinutes): number {
  const total = dt.getHours() * 60 + dt.getMinutes()
  return Math.floor(total / slotMinutes)
}

function weekSlotStart(slotIndex: number, slotMinutes: WeekSlotMinutes): { hour: number; minute: number } {
  const total = slotIndex * slotMinutes
  const hour = Math.floor(total / 60)
  const minute = total % 60
  return { hour, minute }
}

function errorTextFrom(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    return detail.map((x) => (typeof x?.msg === 'string' ? x.msg : JSON.stringify(x))).join('; ')
  }
  if (detail && typeof detail === 'object') return JSON.stringify(detail)
  if (typeof err?.message === 'string' && err.message.trim()) return err.message
  return fallback
}

function sourceBadgeClass(source: UnifiedCalendarEvent['source']): string {
  if (source === 'timeoff') return 'bg-rose-100 text-rose-800'
  if (source === 'reminder') return 'bg-amber-100 text-amber-800'
  return 'bg-violet-100 text-violet-800'
}

function statusBadgeClass(status: UnifiedCalendarEvent['status']): string {
  if (status === 'approved') return 'bg-emerald-100 text-emerald-800'
  if (status === 'pending') return 'bg-amber-100 text-amber-800'
  if (status === 'overdue') return 'bg-rose-100 text-rose-800'
  if (status === 'due') return 'bg-blue-100 text-blue-800'
  return 'bg-slate-100 text-slate-700'
}

function reminderLink(rem: any): string | null {
  if (rem?.entity_type === 'candidate' && rem?.entity_id) return `/app/candidates/${rem.entity_id}`
  if (rem?.entity_type === 'company' && rem?.entity_id) return `/app/clients/${rem.entity_id}`
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
  if (k === 'meeting') return 'bg-indigo-50 text-indigo-700 border-indigo-200'
  if (k === 'call') return 'bg-sky-50 text-sky-700 border-sky-200'
  if (k === 'task' || k === 'followup') return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  return 'bg-slate-50 text-slate-700 border-slate-200'
}

export default function CommunicationsCalendarPage() {
  const { t } = useI18n()

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [infoText, setInfoText] = useState<string | null>(null)
  const [nowTs, setNowTs] = useState<number>(() => Date.now())

  const [timeOffRows, setTimeOffRows] = useState<CommunicationTimeOffRequest[]>([])
  const [reminders, setReminders] = useState<any[]>([])
  const [plannerEvents, setPlannerEvents] = useState<CommunicationPlannerEvent[]>([])
  const [labels, setLabels] = useState<Map<string, string>>(new Map())
  const [managers, setManagers] = useState<Array<{ id: string; label: string }>>([])

  const [monthCursor, setMonthCursor] = useState<Date>(() => startOfMonth(new Date()))
  const [selectedDay, setSelectedDay] = useState<string>(() => dateIso(new Date()))
  const [weekCursor, setWeekCursor] = useState<Date>(() => startOfWeek(new Date()))
  const [statusFilter, setStatusFilter] = useState<TimeOffStatusFilter>('approved')
  const [sourceFilter, setSourceFilter] = useState<CalendarSourceFilter>('all')
  const [assigneeFilter, setAssigneeFilter] = useState('')
  const [plannerKindFilter, setPlannerKindFilter] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('month')
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
    dueAt: toLocalInput(new Date(Date.now() + 2 * 60 * 60_000).toISOString()),
    offsetMinutes: 30,
    assigneeId: '',
    priority: 'normal',
    description: '',
  })

  const load = useCallback(async () => {
    setLoading(true)
    setErrorText(null)
    try {
      const [timeOffRes, remRes, plannerRes, mgrs] = await Promise.all([
        listCommunicationTimeOffRequests({
          limit: 500,
          status_filter: statusFilter === 'all' ? undefined : [statusFilter],
        }),
        listReminders().catch(() => ({ items: [] })),
        listCommunicationPlannerEvents({ limit: 500 }).catch(() => ({ items: [] })),
        listManagers().catch(() => []),
      ])
      const normalizedManagers = (Array.isArray(mgrs) ? mgrs : []).map((m: any) => ({ id: String(m.id), label: String(m.label || m.full_name || m.email || m.id) }))
      setManagers(normalizedManagers)
      setLabels(new Map(normalizedManagers.map((m) => [m.id, m.label])))

      setTimeOffRows(Array.isArray(timeOffRes.items) ? timeOffRes.items : [])
      setReminders(Array.isArray((remRes as any)?.items) ? (remRes as any).items : [])
      setPlannerEvents(Array.isArray(plannerRes?.items) ? plannerRes.items : [])
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to load calendar data'))
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const timer = window.setInterval(() => setNowTs(Date.now()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

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

  const unifiedEvents = useMemo<UnifiedCalendarEvent[]>(() => {
    const nowTs = Date.now()
    const events: UnifiedCalendarEvent[] = []

    for (const row of timeOffRows) {
      if (!row.start_date || !row.end_date) continue
      let cur = parseDate(`${row.start_date}T00:00:00Z`)
      const end = parseDate(`${row.end_date}T00:00:00Z`)
      if (!cur || !end) continue
      while (cur <= end) {
        events.push({
          id: `timeoff:${row.id}:${dateIso(cur)}`,
          dateKey: dateIso(cur),
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

    for (const rem of reminders) {
      const dueAt = rem?.due_at || rem?.remind_at || null
      const dt = parseDate(dueAt)
      if (!dt) continue
      const status = String(rem?.status || '').toLowerCase()
      const sourceStatus: UnifiedCalendarEvent['status'] = status === 'overdue' || dt.getTime() < nowTs ? 'overdue' : 'due'
      events.push({
        id: `rem:${String(rem?.id || '')}:${String(dueAt)}`,
        reminderId: String(rem?.id || ''),
        reminderStatus: rem?.status ? String(rem.status) : null,
        dateKey: dateIso(dt),
        source: 'reminder',
        status: sourceStatus,
        title: String(rem?.title || t('app.candidate_card.reminders.untitled', { defaultValue: 'Untitled' })),
        subtitle: rem?.assignee_id ? `assignee: ${labels.get(String(rem.assignee_id)) || String(rem.assignee_id)}` : 'assignee: —',
        detail: rem?.description || undefined,
        at: dueAt,
        endAt: null,
        entityPath: reminderLink(rem),
        assigneeId: rem?.assignee_id ? String(rem.assignee_id) : null,
        priority: rem?.priority ? String(rem.priority) : 'normal',
      })
    }

    for (const pe of plannerEvents) {
      const dt = parseDate(pe.start_at)
      if (!dt) continue
      const s = String(pe.status || '').toLowerCase()
      events.push({
        id: `planner:${pe.id}:${pe.start_at}`,
        plannerId: pe.id,
        plannerStatus: String(pe.status || ''),
        dateKey: dateIso(dt),
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

    return events.sort((a, b) => {
      const ad = a.at || `${a.dateKey}T00:00:00`
      const bd = b.at || `${b.dateKey}T00:00:00`
      return ad.localeCompare(bd) || a.title.localeCompare(b.title)
    })
  }, [labels, plannerEvents, reminders, t, timeOffRows])

  const filteredEvents = useMemo(() => {
    return unifiedEvents.filter((e) => {
      if (sourceFilter === 'timeoff' && e.source !== 'timeoff') return false
      if (sourceFilter === 'reminders' && e.source !== 'reminder') return false
      if (sourceFilter === 'planner' && e.source !== 'planner') return false
      if (assigneeFilter && String(e.assigneeId || '') !== assigneeFilter) return false
      if (plannerKindFilter && e.source === 'planner' && String(e.kind || '') !== plannerKindFilter) return false
      return true
    })
  }, [assigneeFilter, plannerKindFilter, sourceFilter, unifiedEvents])

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
    return new Map(plannerEvents.map((x) => [x.id, x]))
  }, [plannerEvents])

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
    const rows = new Map<string, { label: string; total: number; meetings: number; tasks: number; overdue: number }>()
    for (const event of selectedEvents) {
      const key = String(event.assigneeId || '')
      if (!key) continue
      if (!rows.has(key)) {
        rows.set(key, { label: labels.get(key) || key, total: 0, meetings: 0, tasks: 0, overdue: 0 })
      }
      const row = rows.get(key)!
      row.total += 1
      if (String(event.kind || '').toLowerCase() === 'meeting') row.meetings += 1
      if (['task', 'followup', 'call'].includes(String(event.kind || '').toLowerCase())) row.tasks += 1
      if (event.status === 'overdue') row.overdue += 1
    }
    return Array.from(rows.values()).sort((a, b) => b.total - a.total || a.label.localeCompare(b.label))
  }, [labels, selectedEvents])

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
    return {
      timeOff: unifiedEvents.filter((e) => e.source === 'timeoff').length,
      reminders: unifiedEvents.filter((e) => e.source === 'reminder').length,
      planner: planner.length,
      meetings: planner.filter((e) => String(e.kind || '').toLowerCase() === 'meeting').length,
      tasks: planner.filter((e) => ['task', 'followup', 'call'].includes(String(e.kind || '').toLowerCase())).length,
      overdue: unifiedEvents.filter((e) => e.status === 'overdue').length,
      daysWithEvents: eventsByDay.size,
    }
  }, [eventsByDay.size, unifiedEvents])

  const upcoming = useMemo(() => {
    const today = dateIso(new Date())
    return filteredEvents.filter((e) => e.dateKey >= today).slice(0, 25)
  }, [filteredEvents])

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

    for (const pe of plannerEvents) {
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
  }, [plannerEvents, timeOffRows])

  const createPlanner = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (!plannerForm.title.trim() || !plannerForm.startAt) return
    const startBase = new Date(plannerForm.startAt)
    if (Number.isNaN(startBase.getTime())) {
      setErrorText('Invalid start datetime')
      return
    }
    const endBase = plannerForm.allDay || !plannerForm.endAt ? null : new Date(plannerForm.endAt)
    if (endBase && Number.isNaN(endBase.getTime())) {
      setErrorText('Invalid end datetime')
      return
    }
    const safeRepeatCount = Math.min(30, Math.max(1, Number(plannerForm.repeatCount || 1)))
    setBusy(true)
    setInfoText(null)
    try {
      let created = 0
      let skipped = 0

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
      }
      setPlannerForm((p) => ({ ...p, title: '', description: '', repeatMode: 'none', repeatCount: 1 }))
      await load()
      setErrorText(created > 0 ? null : 'No events created')
      if (skipped > 0) {
        setInfoText(`Created ${created} event(s). Skipped ${skipped} due to conflicts (time-off or planner overlap).`)
      } else if (created > 1) {
        setInfoText(`Created ${created} recurring events.`)
      } else {
        setInfoText(null)
      }
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to create planner event'))
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load, plannerForm])

  const createDayReminder = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (!reminderForm.title.trim() || !reminderForm.dueAt) return
    setBusy(true)
    try {
      const due = new Date(reminderForm.dueAt)
      const remindAt = new Date(due.getTime() - Math.max(1, Number(reminderForm.offsetMinutes || 30)) * 60_000)
      await createReminder({
        title: reminderForm.title.trim(),
        description: reminderForm.description.trim() || undefined,
        entity_type: 'calendar',
        entity_id: selectedDay,
        assignee_id: reminderForm.assigneeId || undefined,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        payload: {
          priority: reminderForm.priority,
          source: 'communications_calendar',
          selected_day: selectedDay,
        },
      })
      setReminderForm((p) => ({ ...p, title: '', description: '' }))
      await load()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to create reminder'))
    } finally {
      setBusy(false)
    }
  }, [load, reminderForm, selectedDay])

  const setPlannerStatus = useCallback(async (plannerId: string, status: string) => {
    setBusy(true)
    try {
      await patchCommunicationPlannerEvent(plannerId, { status })
      await load()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to update planner event'))
    } finally {
      setBusy(false)
    }
  }, [load])

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
        setErrorText(`Cannot reassign: ${conflictReason}.`)
        return
      }
    }
    setBusy(true)
    try {
      await patchCommunicationPlannerEvent(event.plannerId, patch)
      await load()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to update planner event'))
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load])

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
      setErrorText(null)
      setInfoText(`Batch done: updated ${updated}, skipped ${skipped}.`)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Batch action failed'))
    } finally {
      setBusy(false)
    }
  }, [load, selectedPlannerEvents])

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
    }, 'No selected planner events.')
  }, [applyBatchToSelected, batchAssigneeId, findSchedulingConflict])

  const runBatchPriority = useCallback(async (priority: 'low' | 'normal' | 'high') => {
    await applyBatchToSelected(async (event) => {
      if (!event.plannerId) return 'skipped'
      await patchCommunicationPlannerEvent(event.plannerId, { priority })
      return 'updated'
    }, 'No selected planner events.')
  }, [applyBatchToSelected])

  const runBatchArchive = useCallback(async () => {
    await applyBatchToSelected(async (event) => {
      if (!event.plannerId || event.plannerStatus === 'cancelled') return 'skipped'
      await patchCommunicationPlannerEvent(event.plannerId, { status: 'cancelled' })
      return 'updated'
    }, 'No selected planner events.')
  }, [applyBatchToSelected])

  const runBatchTag = useCallback(async (mode: 'add' | 'remove') => {
    const tag = batchTagValue.trim().replace(/^#/, '')
    if (!tag) {
      setInfoText('Enter tag value first.')
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
    }, 'No selected planner events.')
  }, [applyBatchToSelected, batchTagValue, plannerById])

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
    setInfoText(`Preset selected: ${ids.length} event(s).`)
  }, [dayPlannerEvents])

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
    setInfoText(`Selected ${ids.length} events by filter.`)
  }, [batchSelectKind, batchSelectPriority, batchSelectStatus, dayPlannerEvents])

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
      setErrorText(`Cannot move: ${conflictReason}.`)
      return
    }
    if (event.detail !== undefined) patch.description = event.detail
    setBusy(true)
    try {
      await patchCommunicationPlannerEvent(event.plannerId, patch)
      await load()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to move planner event'))
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load])

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
      setErrorText(`Cannot duplicate: ${conflictReason}.`)
      return
    }
    setBusy(true)
    try {
      await createCommunicationPlannerEvent({
        title: `${event.title} (copy)`,
        description: event.detail || undefined,
        kind: event.kind || 'task',
        priority: event.priority || 'normal',
        assignee_id: event.assigneeId || undefined,
        start_at: startShifted.toISOString(),
        end_at: endShifted?.toISOString() || undefined,
      })
      await load()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to duplicate planner event'))
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load])

  const completeDayReminder = useCallback(async (reminderId: string) => {
    setBusy(true)
    try {
      await completeReminder(reminderId)
      await load()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to complete reminder'))
    } finally {
      setBusy(false)
    }
  }, [load])

  const snoozeDayReminder = useCallback(async (reminderId: string, minutes: number) => {
    setBusy(true)
    try {
      await snoozeReminder(reminderId, { minutes })
      await load()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to snooze reminder'))
    } finally {
      setBusy(false)
    }
  }, [load])

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

  const movePlannerEventToDateTime = useCallback(async (event: UnifiedCalendarEvent, targetStart: Date, dayKeyAfterMove?: string) => {
    if (!event.plannerId || !event.at) return
    const start = parseDate(event.at)
    if (!start) return
    const movedStart = new Date(targetStart)

    const end = parseDate(event.endAt || null)
    const movedEnd = end ? new Date(movedStart.getTime() + (end.getTime() - start.getTime())) : null

    const conflictReason = findSchedulingConflict({
      assigneeId: event.assigneeId || null,
      startAt: movedStart,
      endAt: movedEnd,
      allDay: false,
      ignorePlannerId: event.plannerId,
    })
    if (conflictReason) {
      setErrorText(`Cannot move: ${conflictReason}.`)
      return
    }

    setBusy(true)
    try {
      await patchCommunicationPlannerEvent(event.plannerId, {
        start_at: movedStart.toISOString(),
        end_at: movedEnd?.toISOString() || null,
      })
      await load()
      if (dayKeyAfterMove) setSelectedDay(dayKeyAfterMove)
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to move planner event'))
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load])

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
      setErrorText(`Cannot resize: ${conflictReason}.`)
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
      setErrorText(null)
      setResizePlannerEvent(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to resize planner event'))
    } finally {
      setBusy(false)
    }
  }, [findSchedulingConflict, load])

  const movePlannerEventToDay = useCallback(async (event: UnifiedCalendarEvent, dayKey: string) => {
    if (!event.at) return
    const start = parseDate(event.at)
    if (!start) return
    const target = parseDate(`${dayKey}T00:00:00`)
    if (!target) return
    target.setHours(start.getHours(), start.getMinutes(), start.getSeconds(), start.getMilliseconds())
    await movePlannerEventToDateTime(event, target, dayKey)
  }, [movePlannerEventToDateTime])

  return (
    <div className="space-y-4">
      <WorkspaceTopNav active="calendar" />
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.communications.ia.calendar_title', { defaultValue: 'Calendar' })}</h1>
        <p className="text-sm text-slate-500">
          {t('app.communications.ia.calendar_subtitle', { defaultValue: 'Daily planning workspace: meetings, tasks, reminders, time-off and team load. Inbound email/messages are not shown here.' })}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-7">
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">Time-off: <strong>{stats.timeOff}</strong></div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Reminders: <strong>{stats.reminders}</strong></div>
        <div className="rounded-lg border border-violet-200 bg-violet-50 p-3 text-sm text-violet-800">Planner items: <strong>{stats.planner}</strong></div>
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-800">Meetings: <strong>{stats.meetings}</strong></div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">Tasks: <strong>{stats.tasks}</strong></div>
        <div className="rounded-lg border border-rose-200 bg-white p-3 text-sm text-rose-700">Overdue: <strong>{stats.overdue}</strong></div>
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">Days: <strong>{stats.daysWithEvents}</strong></div>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setViewMode('month')}
            className={clsx('btn-secondary', viewMode === 'month' && 'border-brand-600 bg-brand-50 text-brand-700')}
          >
            Month view
          </button>
          <button
            type="button"
            onClick={() => setViewMode('day')}
            className={clsx('btn-secondary', viewMode === 'day' && 'border-brand-600 bg-brand-50 text-brand-700')}
          >
            Day planner
          </button>
          <button
            type="button"
            onClick={() => setViewMode('week')}
            className={clsx('btn-secondary', viewMode === 'week' && 'border-brand-600 bg-brand-50 text-brand-700')}
          >
            Week view
          </button>

          <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value as CalendarSourceFilter)} className="input">
            <option value="all">All sources</option>
            <option value="timeoff">Time-off</option>
            <option value="reminders">Reminders</option>
            <option value="planner">Planner</option>
          </select>

          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as TimeOffStatusFilter)} className="input">
            <option value="approved">Time-off approved only</option>
            <option value="pending">Time-off pending only</option>
            <option value="all">Time-off approved + pending</option>
          </select>

          <select value={assigneeFilter} onChange={(e) => setAssigneeFilter(e.target.value)} className="input">
            <option value="">All managers</option>
            {managers.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
          <select value={plannerKindFilter} onChange={(e) => setPlannerKindFilter(e.target.value)} className="input">
            <option value="">All planner kinds</option>
            <option value="meeting">Meeting</option>
            <option value="task">Task</option>
            <option value="followup">Follow-up</option>
            <option value="call">Call</option>
            <option value="shift">Shift</option>
          </select>

          <button type="button" onClick={() => void load()} className="btn-secondary">
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
        {errorText && (
          <div className="mt-3">
            <ErrorRecoveryBanner
              info={{ title: errorText, hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }) }}
              onRetry={() => void load()}
              retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
              secondaryTo="/app/communications/setup"
              secondaryLabel={t('app.nav.items.setup', { defaultValue: 'Setup' })}
              compact
            />
          </div>
        )}
        {infoText && <div className="mt-3 alert-info text-sm">{infoText}</div>}
        {loading && <div className="mt-3 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>}
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="space-y-4">
          {viewMode === 'month' && (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <button type="button" className="btn-secondary" onClick={() => setMonthCursor((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))}>←</button>
                  <div className="min-w-40 text-sm font-semibold text-slate-900 capitalize">{monthMeta.title}</div>
                  <button type="button" className="btn-secondary" onClick={() => setMonthCursor((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))}>→</button>
                </div>
                <div className="text-xs text-slate-500">Click a day to open day planner.</div>
              </div>

              <div className="mt-3 grid grid-cols-7 gap-1 text-xs text-slate-500">
                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => <div key={d} className="px-2 py-1 text-center font-medium">{d}</div>)}
              </div>

              <div className="grid grid-cols-7 gap-1">
                {monthMeta.days.map((day) => {
                  const key = dateIso(day)
                  const inMonth = day.getMonth() === monthMeta.start.getMonth()
                  const dayEvents = eventsByDay.get(key) || []
                  const counts = {
                    overdue: dayEvents.filter((e) => e.status === 'overdue').length,
                    timeoff: dayEvents.filter((e) => e.source === 'timeoff').length,
                    reminders: dayEvents.filter((e) => e.source === 'reminder').length,
                    planner: dayEvents.filter((e) => e.source === 'planner').length,
                  }
                  const isSelected = key === selectedDay
                  const isToday = key === dateIso(new Date())
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => {
                        setSelectedDay(key)
                        setWeekCursor(startOfWeek(day))
                        setViewMode('day')
                      }}
                      className={clsx('min-h-[96px] overflow-hidden rounded-lg border px-2 py-2 text-left', isSelected ? 'border-brand-500 bg-brand-50' : 'border-slate-200 hover:bg-slate-50', !inMonth && 'opacity-45')}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className={clsx('text-sm', isToday ? 'font-semibold text-brand-700' : 'text-slate-700')}>{day.getDate()}</span>
                        {dayEvents.length > 0 && <span className="text-[10px] text-slate-500">{dayEvents.length}</span>}
                      </div>
                      <div className="mt-2 space-y-1">
                        {counts.overdue > 0 && <div className="badge max-w-full overflow-hidden bg-rose-100 text-rose-800">overdue {counts.overdue}</div>}
                        {counts.timeoff > 0 && <div className="badge max-w-full overflow-hidden bg-rose-50 text-rose-700">time-off {counts.timeoff}</div>}
                        {counts.reminders > 0 && <div className="badge max-w-full overflow-hidden bg-amber-100 text-amber-800">rem {counts.reminders}</div>}
                        {counts.planner > 0 && <div className="badge max-w-full overflow-hidden bg-violet-100 text-violet-800">planner {counts.planner}</div>}
                      </div>
                    </button>
                  )
                })}
              </div>

              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1"><span className="h-2 w-2 rounded-full bg-rose-500" />Time-off</span>
                <span className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1"><span className="h-2 w-2 rounded-full bg-amber-500" />Reminders</span>
                <span className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1"><span className="h-2 w-2 rounded-full bg-violet-500" />Planner</span>
              </div>
            </section>
          )}

          {viewMode === 'week' && (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <button type="button" className="btn-secondary" onClick={() => setWeekCursor((d) => addDays(d, -7))}>←</button>
                  <div className="text-sm font-semibold text-slate-900">
                    Week: {formatDayLabel(dateIso(weekDays[0]))} - {formatDayLabel(dateIso(weekDays[6]))}
                  </div>
                  <button type="button" className="btn-secondary" onClick={() => setWeekCursor((d) => addDays(d, 7))}>→</button>
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  <span className="text-[11px] text-slate-500">Slot:</span>
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
                    <div className="px-2 py-2 text-[10px] font-semibold uppercase text-slate-500">Time</div>
                    {weekDays.map((day) => {
                      const key = dateIso(day)
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
                          {key === nowMeta.dayKey && <span className="ml-1 badge bg-rose-100 text-rose-700">now</span>}
                        </div>
                      </button>
                    )
                  })}
                  </div>

                  <div className="grid grid-cols-[64px_repeat(7,minmax(0,1fr))] border-b border-slate-200">
                    <div className="px-2 py-2 text-[10px] font-semibold uppercase text-slate-500">All-day</div>
                    {weekDays.map((day) => {
                      const key = dateIso(day)
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
                    {Array.from({ length: Math.floor((24 * 60) / weekSlotMinutes) }).map((_, slotIndex) => {
                      const slot = weekSlotStart(slotIndex, weekSlotMinutes)
                      const hourLabel = `${String(slot.hour).padStart(2, '0')}:${String(slot.minute).padStart(2, '0')}`
                      const majorLine = slot.minute === 0
                      const slotStartMin = slot.hour * 60 + slot.minute
                      const slotEndMin = slotStartMin + weekSlotMinutes
                      const isCurrentSlot = nowMeta.totalMinutes >= slotStartMin && nowMeta.totalMinutes < slotEndMin
                      const nowOffsetPercent = ((nowMeta.totalMinutes - slotStartMin) / weekSlotMinutes) * 100
                      return (
                        <div key={`week-hour-${slotIndex}`} className={clsx('grid grid-cols-[64px_repeat(7,minmax(0,1fr))] border-b', majorLine ? 'border-slate-200' : 'border-slate-100')}>
                          <div className={clsx('px-2 py-2 text-[11px]', majorLine ? 'text-slate-500' : 'text-slate-400')}>{hourLabel}</div>
                          {weekDays.map((day) => {
                            const key = dateIso(day)
                            const cellEvents = (eventsByDay.get(key) || [])
                              .filter((event) => {
                                const dt = parseDate(event.at || null)
                                return dt ? weekSlotIndex(dt, weekSlotMinutes) === slotIndex : false
                              })
                              .slice(0, 4)
                            return (
                              <div
                                key={`week-cell-${key}-${slotIndex}`}
                                className={clsx(
                                  'relative min-h-[44px] border-l border-slate-100 px-1 py-1',
                                  dragPlannerEvent?.plannerId ? 'hover:bg-brand-50/40' : '',
                                )}
                                onDragOver={(e) => {
                                  if (dragPlannerEvent?.plannerId) e.preventDefault()
                                }}
                                onDrop={(e) => {
                                  e.preventDefault()
                                  if (!dragPlannerEvent?.plannerId) return
                                  const target = parseDate(`${key}T00:00:00`)
                                  if (!target) return
                                  target.setHours(slot.hour, slot.minute, 0, 0)
                                  void movePlannerEventToDateTime(dragPlannerEvent, target, key)
                                  setDragPlannerEvent(null)
                                }}
                              >
                                {key === nowMeta.dayKey && isCurrentSlot && (
                                  <div className="pointer-events-none absolute left-0 right-0" style={{ top: `${Math.max(0, Math.min(100, nowOffsetPercent))}%` }}>
                                    <div className="h-0.5 w-full bg-rose-500" />
                                  </div>
                                )}
                                <div className="space-y-1">
                                  {cellEvents.map((event) => (
                                    <div
                                      key={`week-item-${event.id}`}
                                      draggable={Boolean(event.plannerId)}
                                      onDragStart={() => {
                                        if (event.plannerId) setDragPlannerEvent(event)
                                      }}
                                      onDragEnd={() => setDragPlannerEvent(null)}
                                      className={clsx('badge border', plannerKindTone(event.kind), 'block w-full overflow-hidden', event.plannerId ? 'cursor-move' : '')}
                                      title={event.plannerId ? 'Drag to another slot' : undefined}
                                    >
                                      <div className="truncate font-medium">{event.title}</div>
                                      <div className="truncate text-slate-600">{formatDateTime(event.at)}</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </section>
          )}

          {viewMode === 'day' && (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-slate-900">Day planner: {formatDayLabel(selectedDay)}</div>
                  <div className="text-xs text-slate-500">Meetings, tasks, reminders, and absence context.</div>
                </div>
                <div className="flex flex-wrap gap-1">
                  <button type="button" onClick={() => setViewMode('week')} className="btn-secondary btn-xs">Week</button>
                  <button type="button" onClick={() => setViewMode('month')} className="btn-secondary btn-xs">Month</button>
                </div>
              </div>
              <div className="mb-3 flex flex-wrap gap-1">
                <button type="button" onClick={() => setPlannerSlot(selectedDay, 9)} className="btn-secondary btn-xs">+ 09:00 slot</button>
                <button type="button" onClick={() => setPlannerSlot(selectedDay, 12)} className="btn-secondary btn-xs">+ 12:00 slot</button>
                <button type="button" onClick={() => setPlannerSlot(selectedDay, 15)} className="btn-secondary btn-xs">+ 15:00 slot</button>
                <button type="button" onClick={() => setPlannerSlot(selectedDay, 18)} className="btn-secondary btn-xs">+ 18:00 slot</button>
              </div>
              <div className="mb-3 rounded border border-slate-200 p-3">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Batch actions for selected planner events ({selectedPlannerEvents.length})
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <button type="button" onClick={selectAllVisiblePlanner} className="btn-secondary btn-xs">Select all visible</button>
                    <button type="button" onClick={clearPlannerSelection} className="btn-secondary btn-xs">Clear</button>
                  </div>
                </div>
                <div className="mb-2 rounded border border-slate-200 p-2">
                  <div className="mb-1 text-[10px] font-semibold uppercase text-slate-500">Select by filter</div>
                  <div className="grid gap-1 md:grid-cols-4">
                    <select value={batchSelectKind} onChange={(e) => setBatchSelectKind(e.target.value)} className="input">
                      <option value="">Any kind</option>
                      <option value="meeting">Meeting</option>
                      <option value="task">Task</option>
                      <option value="followup">Follow-up</option>
                      <option value="call">Call</option>
                      <option value="shift">Shift</option>
                    </select>
                    <select value={batchSelectPriority} onChange={(e) => setBatchSelectPriority(e.target.value)} className="input">
                      <option value="">Any priority</option>
                      <option value="low">Low</option>
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                    </select>
                    <select value={batchSelectStatus} onChange={(e) => setBatchSelectStatus(e.target.value as BatchSelectStatusFilter)} className="input">
                      <option value="">Any status</option>
                      <option value="planned">Planned</option>
                      <option value="in_progress">In progress</option>
                      <option value="done">Done</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                    <button type="button" onClick={selectByCurrentBatchFilter} className="btn-secondary btn-xs">
                      Select by filter
                    </button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    <button type="button" onClick={() => applySelectionPreset('meetings')} className="btn-secondary btn-xs">Meetings</button>
                    <button type="button" onClick={() => applySelectionPreset('high')} className="btn-secondary btn-xs">High priority</button>
                    <button type="button" onClick={() => applySelectionPreset('unassigned')} className="btn-secondary btn-xs">Unassigned</button>
                    <button type="button" onClick={() => applySelectionPreset('in_progress')} className="btn-secondary btn-xs">In progress</button>
                    <button type="button" onClick={() => applySelectionPreset('due_soon')} className="btn-secondary btn-xs">Due soon (2h)</button>
                  </div>
                </div>
                <div className="grid gap-2 md:grid-cols-2">
                  <div className="rounded border border-slate-200 p-2">
                    <div className="mb-1 text-[10px] font-semibold uppercase text-slate-500">Assign</div>
                    <div className="flex gap-1">
                      <select value={batchAssigneeId} onChange={(e) => setBatchAssigneeId(e.target.value)} className="w-full input">
                        <option value="">Unassigned</option>
                        {managers.map((m) => <option key={`batch-assignee-${m.id}`} value={m.id}>{m.label}</option>)}
                      </select>
                      <button type="button" onClick={() => void runBatchAssign()} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">Apply</button>
                    </div>
                  </div>
                  <div className="rounded border border-slate-200 p-2">
                    <div className="mb-1 text-[10px] font-semibold uppercase text-slate-500">Priority</div>
                    <div className="flex flex-wrap gap-1">
                      <button type="button" onClick={() => void runBatchPriority('low')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">Low</button>
                      <button type="button" onClick={() => void runBatchPriority('normal')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">Normal</button>
                      <button type="button" onClick={() => void runBatchPriority('high')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">High</button>
                    </div>
                  </div>
                  <div className="rounded border border-slate-200 p-2 md:col-span-2">
                    <div className="mb-1 text-[10px] font-semibold uppercase text-slate-500">Tags</div>
                    <div className="flex flex-wrap gap-1">
                      <input value={batchTagValue} onChange={(e) => setBatchTagValue(e.target.value)} placeholder="tag" className="input" />
                      <button type="button" onClick={() => void runBatchTag('add')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">Add</button>
                      <button type="button" onClick={() => void runBatchTag('remove')} disabled={busy || !selectedPlannerEvents.length} className="btn-secondary btn-xs disabled:opacity-50">Remove</button>
                      <button type="button" onClick={() => void runBatchArchive()} disabled={busy || !selectedPlannerEvents.length} className="ml-auto btn-danger btn-xs disabled:opacity-50">Archive selected</button>
                    </div>
                  </div>
                </div>
              </div>
              <div className="mb-3 rounded border border-slate-200 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">Timeline drag & drop</div>
                  {selectedDay === nowMeta.dayKey && <span className="badge bg-rose-100 text-rose-700">Now {nowMeta.label}</span>}
                  {resizePlannerEvent?.plannerId && (
                    <button
                      type="button"
                      onClick={() => setResizePlannerEvent(null)}
                      className="btn-secondary btn-xs"
                    >
                      Exit resize
                    </button>
                  )}
                </div>
                <div className="max-h-56 space-y-1 overflow-auto">
                  {Array.from({ length: 24 }).map((_, hour) => {
                    const slotLabel = `${String(hour).padStart(2, '0')}:00`
                    const isCurrentHour = selectedDay === nowMeta.dayKey && nowMeta.hours === hour
                    const slotEvents = dayPlannerEvents.filter((event) => {
                      const dt = parseDate(event.at || null)
                      return dt ? dt.getHours() === hour : false
                    })
                    return (
                      <div
                        key={`slot-${hour}`}
                        className={clsx(
                          'relative rounded border border-slate-200 px-2 py-1 text-xs',
                          dragPlannerEvent?.plannerId ? 'hover:border-brand-300 hover:bg-brand-50/40' : '',
                          isCurrentHour ? 'border-rose-200 bg-rose-50/30' : '',
                        )}
                        onDragOver={(e) => {
                          if (dragPlannerEvent?.plannerId) e.preventDefault()
                        }}
                        onDrop={(e) => {
                          e.preventDefault()
                          if (resizePlannerEvent?.plannerId) {
                            void resizePlannerEventToHour(resizePlannerEvent, selectedDay, hour + 1)
                            return
                          }
                          if (dragPlannerEvent?.plannerId) {
                            const target = parseDate(`${selectedDay}T00:00:00`)
                            if (!target) return
                            target.setHours(hour, 0, 0, 0)
                            void movePlannerEventToDateTime(dragPlannerEvent, target, selectedDay)
                            setDragPlannerEvent(null)
                          }
                        }}
                      >
                        {isCurrentHour && (
                          <div className="pointer-events-none absolute left-0 right-0" style={{ top: `${(nowMeta.minutes / 60) * 100}%` }}>
                            <div className="h-0.5 w-full bg-rose-500" />
                          </div>
                        )}
                        <div className="font-medium text-slate-600">{slotLabel}</div>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {slotEvents.map((event) => (
                            <div
                              key={`slot-item-${event.id}`}
                              draggable={Boolean(event.plannerId)}
                              onDragStart={() => {
                                if (event.plannerId) setDragPlannerEvent(event)
                              }}
                              onDragEnd={() => setDragPlannerEvent(null)}
                              className={clsx('badge border', plannerKindTone(event.kind), 'cursor-move')}
                              title="Drag to another hour/day"
                            >
                              <span>{event.title}</span>
                              {event.plannerId && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setResizePlannerEvent(event)
                                  }}
                                  className={clsx('ml-1 btn-secondary btn-xs', resizePlannerEvent?.plannerId === event.plannerId && 'border-brand-400 bg-brand-50 text-brand-700')}
                                >
                                  resize
                                </button>
                              )}
                            </div>
                          ))}
                          {slotEvents.length === 0 && <span className="text-[10px] text-slate-400">drop here</span>}
                          {resizePlannerEvent?.plannerId && <span className="text-[10px] text-brand-700">set end here</span>}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                {[
                  { key: 'morning', label: 'Morning (00:00-11:59)', items: dayBoard.morning },
                  { key: 'midday', label: 'Day (12:00-16:59)', items: dayBoard.midday },
                  { key: 'evening', label: 'Evening (17:00-23:59)', items: dayBoard.evening },
                ].map((bucket) => (
                  <div key={bucket.key} className="rounded border border-slate-200 p-3">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">{bucket.label}</div>
                    <div className="space-y-2">
                      {bucket.items.map((event) => (
                        <div
                          key={event.id}
                          draggable={Boolean(event.plannerId)}
                          onDragStart={() => {
                            if (event.plannerId) setDragPlannerEvent(event)
                          }}
                          onDragEnd={() => setDragPlannerEvent(null)}
                          className={clsx('rounded-lg border px-2 py-2 text-xs', plannerKindTone(event.kind), event.plannerId ? 'cursor-move' : '')}
                          title={event.plannerId ? 'Drag to timeline or week days' : undefined}
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
                                <button type="button" onClick={() => void setPlannerStatus(event.plannerId!, 'in_progress')} disabled={busy || event.plannerStatus === 'in_progress'} className="btn-secondary btn-xs disabled:opacity-50">Start</button>
                                <button type="button" onClick={() => void setPlannerStatus(event.plannerId!, 'done')} disabled={busy || event.plannerStatus === 'done'} className="btn-primary btn-xs disabled:opacity-50">Done</button>
                                <button type="button" onClick={() => void setPlannerStatus(event.plannerId!, 'planned')} disabled={busy || event.plannerStatus === 'planned'} className="btn-secondary btn-xs disabled:opacity-50">Reopen</button>
                                <button type="button" onClick={() => void setPlannerStatus(event.plannerId!, 'cancelled')} disabled={busy || event.plannerStatus === 'cancelled'} className="btn-secondary btn-xs disabled:opacity-50">Cancel</button>
                                <button type="button" onClick={() => void movePlannerEvent(event, 60)} disabled={busy || !event.at} className="btn-secondary btn-xs disabled:opacity-50">+1h</button>
                                <button type="button" onClick={() => void movePlannerEvent(event, 1440)} disabled={busy || !event.at} className="btn-secondary btn-xs disabled:opacity-50">+1d</button>
                                <button type="button" onClick={() => void duplicatePlannerEvent(event)} disabled={busy || !event.at} className="btn-secondary btn-xs disabled:opacity-50">Duplicate</button>
                                <button
                                  type="button"
                                  onClick={() => setResizePlannerEvent(event)}
                                  disabled={busy}
                                  className={clsx('btn-secondary btn-xs disabled:opacity-50', resizePlannerEvent?.plannerId === event.plannerId && 'border-brand-400 bg-brand-50 text-brand-700')}
                                >
                                  Resize
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setActivePlannerMenuId((prev) => (prev === event.plannerId ? null : event.plannerId!))}
                                  className={clsx('btn-secondary btn-xs', activePlannerMenuId === event.plannerId && 'border-brand-400 bg-brand-50 text-brand-700')}
                                >
                                  Manage
                                </button>
                              </>
                            )}
                            {event.reminderId && (
                              <>
                                <button type="button" onClick={() => void completeDayReminder(event.reminderId!)} disabled={busy || ['done', 'completed', 'cancelled'].includes(String(event.reminderStatus || '').toLowerCase())} className="btn-primary btn-xs disabled:opacity-50">Complete</button>
                                <button type="button" onClick={() => void snoozeDayReminder(event.reminderId!, 30)} disabled={busy || ['done', 'completed', 'cancelled'].includes(String(event.reminderStatus || '').toLowerCase())} className="btn-secondary btn-xs disabled:opacity-50">Snooze 30m</button>
                              </>
                            )}
                            {event.entityPath && (
                              <Link to={event.entityPath} className="btn-secondary btn-xs">Open</Link>
                            )}
                          </div>
                          {event.plannerId && activePlannerMenuId === event.plannerId && (
                            <div className="mt-2 rounded border border-slate-200 bg-white p-2 text-[10px] text-slate-700">
                              <div className="mb-1 font-semibold text-slate-800">Quick actions</div>
                              <div className="mb-1 flex flex-wrap gap-1">
                                <button type="button" onClick={() => void setPlannerPriorityByEvent(event, 'low')} disabled={busy} className="btn-secondary btn-xs disabled:opacity-50">P:low</button>
                                <button type="button" onClick={() => void setPlannerPriorityByEvent(event, 'normal')} disabled={busy} className="btn-secondary btn-xs disabled:opacity-50">P:normal</button>
                                <button type="button" onClick={() => void setPlannerPriorityByEvent(event, 'high')} disabled={busy} className="btn-secondary btn-xs disabled:opacity-50">P:high</button>
                              </div>
                              <div className="mb-1">
                                <select
                                  value={String(event.assigneeId || '')}
                                  onChange={(e) => { void assignPlannerByEvent(event, e.target.value) }}
                                  disabled={busy}
                                  className="w-full input disabled:bg-slate-100"
                                >
                                  <option value="">Unassigned</option>
                                  {managers.map((m) => <option key={`${event.id}:mgr:${m.id}`} value={m.id}>{m.label}</option>)}
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
                                <button type="button" onClick={() => { void archivePlannerByEvent(event) }} disabled={busy || event.plannerStatus === 'cancelled'} className="btn-danger btn-xs disabled:opacity-50">Archive</button>
                                <button type="button" onClick={() => setActivePlannerMenuId(null)} className="btn-secondary btn-xs">Close</button>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                      {bucket.items.length === 0 && <div className="text-xs text-slate-500">No items</div>}
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3 rounded border border-slate-200 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">Team load for selected day</div>
                <div className="mt-2 space-y-1">
                  {loadByAssigneeToday.map((row) => (
                    <div key={row.label} className="flex items-center justify-between gap-2 rounded border border-slate-100 px-2 py-1 text-xs">
                      <span className="truncate text-slate-700">{row.label}</span>
                      <span className="text-slate-500">total {row.total} | mtg {row.meetings} | task {row.tasks} | overdue {row.overdue}</span>
                    </div>
                  ))}
                  {loadByAssigneeToday.length === 0 && <div className="text-xs text-slate-500">No assigned workload for this day.</div>}
                </div>
              </div>
            </section>
          )}
        </div>

        <div className="space-y-4">
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-2 text-sm font-semibold text-slate-900">Create meeting / task</div>
            <form className="space-y-2" onSubmit={createPlanner}>
              <input value={plannerForm.title} onChange={(e) => setPlannerForm((p) => ({ ...p, title: e.target.value }))} className="w-full input" placeholder="Title" />
              <div className="grid grid-cols-2 gap-2">
                <select value={plannerForm.kind} onChange={(e) => setPlannerForm((p) => ({ ...p, kind: e.target.value }))} className="input">
                  <option value="meeting">Meeting</option>
                  <option value="task">Task</option>
                  <option value="followup">Follow-up</option>
                  <option value="call">Call</option>
                  <option value="shift">Shift</option>
                </select>
                <select value={plannerForm.priority} onChange={(e) => setPlannerForm((p) => ({ ...p, priority: e.target.value }))} className="input">
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                </select>
              </div>
              <select value={plannerForm.assigneeId} onChange={(e) => setPlannerForm((p) => ({ ...p, assigneeId: e.target.value }))} className="w-full input">
                <option value="">Unassigned</option>
                {managers.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
              </select>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={plannerForm.allDay} onChange={(e) => setPlannerForm((p) => ({ ...p, allDay: e.target.checked }))} />
                All day
              </label>
              <div className="grid grid-cols-2 gap-2">
                <select value={plannerForm.repeatMode} onChange={(e) => setPlannerForm((p) => ({ ...p, repeatMode: e.target.value as PlannerRepeatMode }))} className="input">
                  <option value="none">No repeat</option>
                  <option value="daily">Repeat daily</option>
                  <option value="weekdays">Repeat weekdays</option>
                </select>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={String(plannerForm.repeatCount)}
                  onChange={(e) => setPlannerForm((p) => ({ ...p, repeatCount: Number(e.target.value || 1) }))}
                  disabled={plannerForm.repeatMode === 'none'}
                  className="input disabled:bg-slate-100"
                  placeholder="Occurrences"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input type={plannerForm.allDay ? 'date' : 'datetime-local'} value={plannerForm.startAt} onChange={(e) => setPlannerForm((p) => ({ ...p, startAt: e.target.value }))} className="input" />
                <input type={plannerForm.allDay ? 'date' : 'datetime-local'} value={plannerForm.endAt} onChange={(e) => setPlannerForm((p) => ({ ...p, endAt: e.target.value }))} className="input" />
              </div>
              <textarea rows={3} value={plannerForm.description} onChange={(e) => setPlannerForm((p) => ({ ...p, description: e.target.value }))} className="w-full textarea" placeholder="Description" />
              <button type="submit" disabled={busy || !plannerForm.title.trim() || !plannerForm.startAt} className="btn-primary disabled:opacity-50">
                {busy ? t('common.loading', { defaultValue: 'Loading...' }) : t('common.actions.create', { defaultValue: 'Create' })}
              </button>
            </form>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-2 text-sm font-semibold text-slate-900">Create reminder</div>
            <form className="space-y-2" onSubmit={createDayReminder}>
              <input value={reminderForm.title} onChange={(e) => setReminderForm((p) => ({ ...p, title: e.target.value }))} className="w-full input" placeholder="Reminder title" />
              <div className="grid grid-cols-2 gap-2">
                <input type="datetime-local" value={reminderForm.dueAt} onChange={(e) => setReminderForm((p) => ({ ...p, dueAt: e.target.value }))} className="input" />
                <input type="number" min={1} value={String(reminderForm.offsetMinutes)} onChange={(e) => setReminderForm((p) => ({ ...p, offsetMinutes: Number(e.target.value || 30) }))} className="input" placeholder="Offset min" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <select value={reminderForm.assigneeId} onChange={(e) => setReminderForm((p) => ({ ...p, assigneeId: e.target.value }))} className="input">
                  <option value="">Unassigned</option>
                  {managers.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                </select>
                <select value={reminderForm.priority} onChange={(e) => setReminderForm((p) => ({ ...p, priority: e.target.value }))} className="input">
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                </select>
              </div>
              <textarea rows={3} value={reminderForm.description} onChange={(e) => setReminderForm((p) => ({ ...p, description: e.target.value }))} className="w-full textarea" placeholder="Description" />
              <button type="submit" disabled={busy || !reminderForm.title.trim() || !reminderForm.dueAt} className="btn-primary disabled:opacity-50">
                {busy ? t('common.loading', { defaultValue: 'Loading...' }) : t('common.actions.create', { defaultValue: 'Create' })}
              </button>
            </form>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-sm font-semibold text-slate-900">Upcoming events</div>
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
              <Link to="/app/planner" className="btn-secondary">
                {t('app.nav.items.planner', { defaultValue: 'Planner' })}
              </Link>
              <Link to="/app/reminders" className="btn-secondary">
                {t('app.nav.items.reminders', { defaultValue: 'Reminders' })}
              </Link>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
