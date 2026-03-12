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
import type {
  NotificationItem,
  NotificationListResponse,
  ReminderListResponse,
  ReminderRecord,
} from '../api/types'
import { useAuth } from '../store/useAuth'
import { useI18n } from '../i18n'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import EmptyStatePanel from '../components/EmptyStatePanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'

const DATE_LOCALES = { en: enUS, ru: ruLocale, pl: plLocale }
const DEFAULT_REMIND_OFFSET = 15
const STORAGE_KEY = 'hf:inbox:reminders:v2'

type LoadState = 'idle' | 'loading' | 'error'
type InboxTab = 'tasks' | 'events'
type TaskStatusFilter = 'active' | 'all' | 'done'
type NotificationsScopeFilter = 'all' | 'direct'
type NotificationsReadFilter = 'unread' | 'all'

type TaskFiltersState = {
  search: string
  status: TaskStatusFilter
  entityType: string
  priority: string
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
}

type TaskRow = ReminderRecord & {
  dueDate: Date | null
  remindDate: Date | null
  dueTs: number
  remindTs: number
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
      return `/app/candidates/${entityId}`
    case 'vacancy':
      return `/app/vacancies/${entityId}`
    case 'lead':
      return `/app/leads`
    case 'company':
      return `/app/companies/${entityId}`
    default:
      return null
  }
}

function notificationEntityHref(item: NotificationItem): string | null {
  const entityId = String(item.entity_id || '')
  const eventType = item.event_type || ''
  if (eventType === 'handoff_requested') return '/app/procesowani'
  if (!entityId) return null
  switch (item.entity_type) {
    case 'candidate':
      return `/app/candidates/${entityId}`
    case 'vacancy':
      return `/app/vacancies/${entityId}`
    case 'lead':
      return '/app/leads'
    case 'company':
      return `/app/companies/${entityId}`
    default:
      return null
  }
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
  let score = 0
  if (requiresAction) score += 100
  if (eventType === 'communications_sla_overdue') score += 90
  if (severity === 'high') score += 40
  else if (severity === 'medium') score += 20
  else if (severity === 'low') score += 5
  return score
}

export default function RemindersPage() {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { me } = useAuth()
  const dateLocale = DATE_LOCALES[locale as keyof typeof DATE_LOCALES] || enUS
  const tenantId = (me as any)?.tenant_id || 'default'
  const storageKey = `${STORAGE_KEY}:${tenantId}`

  const [hydrated, setHydrated] = useState(false)
  const [activeTab, setActiveTab] = useState<InboxTab>('tasks')
  const [taskFilters, setTaskFilters] = useState<TaskFiltersState>(DEFAULT_TASK_FILTERS)
  const [eventsFilters, setEventsFilters] = useState<EventsFiltersState>(DEFAULT_EVENTS_FILTERS)

  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [remindersState, setRemindersState] = useState<LoadState>('idle')
  const [remindersError, setRemindersError] = useState<FriendlyErrorInfo | null>(null)
  const [taskBusyId, setTaskBusyId] = useState<string | null>(null)

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
  const [composerOpen, setComposerOpen] = useState(true)
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
    } catch {
      // ignore malformed storage
    }

    try {
      const urlTab = parseInboxTab(searchParams.get('tab'))
      const tStatus = parseTaskStatus(searchParams.get('t_status'))
      const tQ = searchParams.get('t_q')
      const tEntity = searchParams.get('t_entity')
      const tPriority = searchParams.get('t_priority')
      const eScope = parseNotifScope(searchParams.get('e_scope'))
      const eRead = parseNotifRead(searchParams.get('e_read'))
      const eQ = searchParams.get('e_q')

      if (urlTab) setActiveTab(urlTab)
      if (tStatus || tQ != null || tEntity != null || tPriority != null) {
        setTaskFilters((prev) => ({
          ...prev,
          ...(tStatus ? { status: tStatus } : {}),
          ...(tQ != null ? { search: tQ } : {}),
          ...(tEntity != null ? { entityType: tEntity } : {}),
          ...(tPriority != null ? { priority: tPriority } : {}),
        }))
      }
      if (eScope || eRead || eQ != null) {
        setEventsFilters((prev) => ({
          ...prev,
          ...(eScope ? { scope: eScope } : {}),
          ...(eRead ? { read: eRead } : {}),
          ...(eQ != null ? { search: eQ } : {}),
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
      }
      localStorage.setItem(storageKey, JSON.stringify(payload))
    } catch {
      // ignore storage errors
    }
  }, [activeTab, taskFilters, eventsFilters, hydrated, storageKey])

  useEffect(() => {
    if (!hydrated) return
    const next = new URLSearchParams(searchParams)

    next.set('tab', activeTab)

    if (taskFilters.status !== DEFAULT_TASK_FILTERS.status) next.set('t_status', taskFilters.status)
    else next.delete('t_status')
    if (taskFilters.search.trim()) next.set('t_q', taskFilters.search.trim())
    else next.delete('t_q')
    if (taskFilters.entityType) next.set('t_entity', taskFilters.entityType)
    else next.delete('t_entity')
    if (taskFilters.priority) next.set('t_priority', taskFilters.priority)
    else next.delete('t_priority')

    if (eventsFilters.scope !== DEFAULT_EVENTS_FILTERS.scope) next.set('e_scope', eventsFilters.scope)
    else next.delete('e_scope')
    if (eventsFilters.read !== DEFAULT_EVENTS_FILTERS.read) next.set('e_read', eventsFilters.read)
    else next.delete('e_read')
    if (eventsFilters.search.trim()) next.set('e_q', eventsFilters.search.trim())
    else next.delete('e_q')

    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true })
    }
  }, [activeTab, eventsFilters, hydrated, searchParams, setSearchParams, taskFilters])

  const loadReminders = useCallback(async () => {
    setRemindersState('loading')
    setRemindersError(null)
    try {
      const statusList =
        taskFilters.status === 'active'
          ? ['pending', 'new', 'overdue', 'sent']
          : taskFilters.status === 'done'
            ? ['done', 'cancelled']
            : undefined
      const data = (await listReminders({ status: statusList })) as ReminderListResponse
      setReminders(Array.isArray(data?.items) ? data.items : [])
      setRemindersState('idle')
    } catch (err: any) {
      setRemindersState('error')
      setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.load', { defaultValue: 'Failed to load reminders' })))
    }
  }, [t, taskFilters.status])

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
      })) as NotificationListResponse
      setNotifications(Array.isArray(data?.items) ? data.items : [])
      setNotificationsState('idle')
    } catch (err: any) {
      setNotificationsState('error')
      setNotificationsError(getFriendlyErrorInfo(err, t('app.reminders.errors.load', { defaultValue: 'Failed to load notifications' })))
    }
  }, [eventsFilters.read, eventsFilters.scope, t])

  const reconcileAndReloadNotificationsFeed = useCallback(async () => {
    setNotificationsState('loading')
    setNotificationsError(null)
    try {
      await reconcileNotifications()
      const data = (await listNotifications({
        limit: 100,
        includeRead: eventsFilters.read === 'all',
        scope: eventsFilters.scope,
      })) as NotificationListResponse
      setNotifications(Array.isArray(data?.items) ? data.items : [])
      setNotificationsState('idle')
    } catch (err: any) {
      setNotificationsState('error')
      setNotificationsError(getFriendlyErrorInfo(err, t('app.reminders.errors.load', { defaultValue: 'Failed to load notifications' })))
    }
  }, [eventsFilters.read, eventsFilters.scope, t])

  useEffect(() => {
    void loadReminders()
  }, [loadReminders])

  useEffect(() => {
    if (activeTab !== 'events') return
    void loadNotificationsFeed()
  }, [activeTab, loadNotificationsFeed])

  const reminderStatusLabel = useCallback(
    (status?: string) => {
      const key = status ? `app.candidate_card.reminders.statuses.${String(status).toLowerCase()}` : 'app.candidate_card.reminders.statuses.pending'
      return t(key, { defaultValue: status || '—' })
    },
    [t]
  )

  const notificationTitle = useCallback(
    (item: NotificationItem) => {
      if (item.event_type === 'handoff_requested') {
        return t('app.notifications.handoff_requested_title', { defaultValue: 'New candidate for processing' })
      }
      const key = `app.reminders.events.${item.event_type}`
      const translated = t(key, { defaultValue: '' })
      if (translated && translated !== key) return translated
      return (item.payload?.title as string) || item.event_type || t('app.reminders.events.unknown', { defaultValue: 'Event' })
    },
    [t]
  )

  const reminderRows = useMemo<TaskRow[]>(() => {
    return reminders.map((item) => {
      const dueDate = parseDate(item.due_at)
      const remindDate = parseDate(item.snoozed_until || item.remind_at)
      return {
        ...item,
        dueDate,
        remindDate,
        dueTs: dueDate?.getTime() || 0,
        remindTs: remindDate?.getTime() || 0,
      }
    })
  }, [reminders])

  const filteredReminderRows = useMemo(() => {
    const q = normalizeText(taskFilters.search)
    return reminderRows
      .filter((item) => {
        if (taskFilters.entityType && item.entity_type !== taskFilters.entityType) return false
        if (taskFilters.priority && (item.priority || '') !== taskFilters.priority) return false
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
      .sort((a, b) => {
        const aDone = isClosedReminderStatus(a.status)
        const bDone = isClosedReminderStatus(b.status)
        if (aDone !== bDone) return aDone ? 1 : -1
        const left = aDone ? (b.updated_at ? Date.parse(b.updated_at) : 0) : a.dueTs || a.remindTs || 0
        const right = bDone ? (a.updated_at ? Date.parse(a.updated_at) : 0) : b.dueTs || b.remindTs || 0
        if (left !== right) return left - right
        return (a.title || '').localeCompare(b.title || '')
      })
  }, [reminderRows, taskFilters.entityType, taskFilters.priority, taskFilters.search])

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
    return buckets
  }, [filteredReminderRows])

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
    return {
      total: reminders.length,
      active: reminders.filter((r) => !isClosedReminderStatus(r.status)).length,
      overdue: reminders.filter((r) => r.status === 'overdue').length,
      done: reminders.filter((r) => isClosedReminderStatus(r.status)).length,
    }
  }, [reminders])

  const notificationCounts = useMemo(() => {
    return {
      total: notifications.length,
      unread: notifications.filter((n) => !n.is_read).length,
    }
  }, [notifications])

  const entityTypeOptions = useMemo(() => {
    return Array.from(new Set(reminders.map((r) => r.entity_type).filter(Boolean))).sort()
  }, [reminders])

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
      setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.create', { defaultValue: 'Failed to create reminder' })))
    } finally {
      setCreateBusy(false)
    }
  }

  const handleComplete = async (id: string) => {
    setTaskBusyId(id)
    setRemindersError(null)
    try {
      const updated = await completeReminder(id)
      setReminders((prev) => prev.map((r) => (r.id === id ? (updated as ReminderRecord) : r)))
    } catch (err: any) {
      setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.complete', { defaultValue: 'Failed to complete reminder' })))
    } finally {
      setTaskBusyId(null)
    }
  }

  const handleSnooze = async (id: string, minutes: number) => {
    setTaskBusyId(id)
    setRemindersError(null)
    try {
      const updated = await snoozeReminder(id, { minutes })
      setReminders((prev) => prev.map((r) => (r.id === id ? (updated as ReminderRecord) : r)))
    } catch (err: any) {
      setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.snooze', { defaultValue: 'Failed to snooze reminder' })))
    } finally {
      setTaskBusyId(null)
    }
  }

  const submitEdit = async (e: FormEvent) => {
    e.preventDefault()
    if (!editState) return
    setEditBusy(true)
    setRemindersError(null)
    try {
      const payload: Record<string, unknown> = {
        title: editState.title.trim(),
        description: editState.description.trim(),
        priority: editState.priority || 'normal',
      }
      if (editState.dueAtLocal) payload.due_at = new Date(editState.dueAtLocal).toISOString()
      if (editState.remindAtLocal) payload.remind_at = new Date(editState.remindAtLocal).toISOString()
      const updated = await updateReminder(editState.id, payload)
      setReminders((prev) => prev.map((r) => (r.id === editState.id ? (updated as ReminderRecord) : r)))
      setEditState(null)
    } catch (err: any) {
      setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.create', { defaultValue: 'Failed to update reminder' })))
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
      setNotificationsError(getFriendlyErrorInfo(err, t('app.reminders.errors.mark_one', { defaultValue: 'Failed to mark notification as read' })))
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
      setNotificationsError(getFriendlyErrorInfo(err, t('app.reminders.errors.mark_all', { defaultValue: 'Failed to clear notifications' })))
    } finally {
      setMarkAllBusy(false)
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

  const taskGroupLabels: Array<{ key: keyof typeof reminderGroups; label: string }> = [
    { key: 'overdue', label: t('app.reminders.status.overdue', { defaultValue: 'Overdue' }) },
    { key: 'today', label: t('app.reminders.group.today', { defaultValue: 'Today' }) },
    { key: 'tomorrow', label: t('app.reminders.group.tomorrow', { defaultValue: 'Tomorrow' }) },
    { key: 'week', label: t('app.reminders.group.week', { defaultValue: 'This week' }) },
    { key: 'later', label: t('app.reminders.group.later', { defaultValue: 'Later' }) },
    { key: 'unscheduled', label: t('app.reminders.group.unscheduled', { defaultValue: 'No due date' }) },
    { key: 'done', label: t('app.reminders.group.done', { defaultValue: 'Completed / cancelled' }) },
  ]

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <WorkspaceTopNav active="reminders" />
      <header className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.reminders.title', { defaultValue: 'Reminders' })}
            </p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-900">
              {t('app.reminders.inbox_title', { defaultValue: 'Inbox: reminders and notifications' })}
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {activeTab === 'tasks'
                ? t('app.reminders.subtitle', {
                    values: { total: taskCounts.total, unread: taskCounts.active, scope: t('app.reminders.scope_labels.direct', { defaultValue: 'for you' }) },
                    defaultValue: 'Shown reminders: {total}',
                  })
                : t('app.reminders.subtitle', {
                    values: { total: notificationCounts.total, unread: notificationCounts.unread, scope: t('app.reminders.scope_labels.all', { defaultValue: 'all events' }) },
                    defaultValue: 'Shown events: {total}',
                  })}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={clsx(
                'rounded-lg border px-4 py-2 text-sm font-medium transition',
                activeTab === 'tasks' ? 'border-brand-600 bg-brand-600 text-white' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              )}
              onClick={() => setActiveTab('tasks')}
            >
              {t('app.reminders.tab.tasks', { defaultValue: 'Tasks' })} ({taskCounts.active})
            </button>
            <button
              type="button"
              className={clsx(
                'rounded-lg border px-4 py-2 text-sm font-medium transition',
                activeTab === 'events' ? 'border-brand-600 bg-brand-600 text-white' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              )}
              onClick={() => setActiveTab('events')}
            >
              {t('app.reminders.tab.events', { defaultValue: 'Events' })} ({notificationCounts.unread})
            </button>
          </div>
        </div>
      </header>

      {activeTab === 'tasks' && (
        <>
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                {t('app.reminders.quick_create', { defaultValue: 'Quick reminder' })}
              </h2>
              <button
                type="button"
                className="btn-ghost btn-xs"
                onClick={() => setComposerOpen((v) => !v)}
              >
                {composerOpen
                  ? t('common.actions.collapse', { defaultValue: 'Collapse' })
                  : t('common.actions.expand', { defaultValue: 'Expand' })}
              </button>
            </div>
            {composerOpen && (
              <form onSubmit={submitQuickReminder} className="mt-3 grid gap-3 lg:grid-cols-12">
                <div className="lg:col-span-4">
                  <label className="block text-xs font-medium text-slate-600">
                    {t('app.reminders.form.title', { defaultValue: 'Task' })}
                  </label>
                  <input
                    type="text"
                    className="input mt-1 w-full"
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    placeholder={t('app.reminders.form.title_placeholder', { defaultValue: 'Call candidate, send email...' })}
                    required
                  />
                </div>
                <div className="lg:col-span-3">
                  <label className="block text-xs font-medium text-slate-600">
                    {t('app.reminders.form.due', { defaultValue: 'Due date' })}
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
                    {t('app.reminders.form.remind_before', { defaultValue: 'Remind before' })}
                  </label>
                  <select className="input mt-1 w-full" value={remindOffset} onChange={(e) => setRemindOffset(Number(e.target.value))}>
                    <option value={5}>5m</option>
                    <option value={15}>15m</option>
                    <option value={30}>30m</option>
                    <option value={60}>1h</option>
                    <option value={180}>3h</option>
                    <option value={1440}>1d</option>
                  </select>
                </div>
                <div className="lg:col-span-2">
                  <label className="block text-xs font-medium text-slate-600">
                    {t('app.reminders.form.priority', { defaultValue: 'Priority' })}
                  </label>
                  <select className="input mt-1 w-full" value={formPriority} onChange={(e) => setFormPriority(e.target.value)}>
                    <option value="low">{t('app.reminders.priority.low', { defaultValue: 'Low' })}</option>
                    <option value="normal">{t('app.reminders.priority.normal', { defaultValue: 'Normal' })}</option>
                    <option value="high">{t('app.reminders.priority.high', { defaultValue: 'High' })}</option>
                  </select>
                </div>
                <div className="lg:col-span-1 flex items-end">
                  <button type="submit" className="btn-primary w-full" disabled={createBusy || !formTitle.trim()}>
                    {createBusy ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.reminders.create', { defaultValue: 'Create' })}
                  </button>
                </div>
                <div className="lg:col-span-12">
                  <label className="block text-xs font-medium text-slate-600">
                    {t('app.reminders.form.description', { defaultValue: 'Description' })}
                  </label>
                  <textarea
                    rows={2}
                    className="textarea mt-1 w-full"
                    value={formDescription}
                    onChange={(e) => setFormDescription(e.target.value)}
                    placeholder={t('app.reminders.form.description_placeholder', { defaultValue: 'Optional details...' })}
                  />
                </div>
              </form>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="min-w-[220px] flex-1">
                <input
                  className="input w-full"
                  value={taskFilters.search}
                  onChange={(e) => setTaskFilters((prev) => ({ ...prev, search: e.target.value }))}
                  placeholder={t('app.reminders.filters.search', { defaultValue: 'Search title, description, entity...' })}
                />
              </div>
              <select
                className="input"
                value={taskFilters.entityType}
                onChange={(e) => setTaskFilters((prev) => ({ ...prev, entityType: e.target.value }))}
              >
                <option value="">{t('app.reminders.filters.entity_all', { defaultValue: 'All sources' })}</option>
                {entityTypeOptions.map((entityType) => (
                  <option key={entityType} value={entityType}>{entityType}</option>
                ))}
              </select>
              <select
                className="input"
                value={taskFilters.priority}
                onChange={(e) => setTaskFilters((prev) => ({ ...prev, priority: e.target.value }))}
              >
                <option value="">{t('app.reminders.filters.priority_all', { defaultValue: 'All priorities' })}</option>
                <option value="low">{t('app.reminders.priority.low', { defaultValue: 'Low' })}</option>
                <option value="normal">{t('app.reminders.priority.normal', { defaultValue: 'Normal' })}</option>
                <option value="high">{t('app.reminders.priority.high', { defaultValue: 'High' })}</option>
              </select>
              <button type="button" className="btn-secondary btn-sm" onClick={() => void loadReminders()}>
                {t('app.reminders.actions.refresh', { defaultValue: 'Refresh' })}
              </button>
              <button
                type="button"
                className="btn-ghost btn-sm"
                onClick={() => setTaskFilters(DEFAULT_TASK_FILTERS)}
              >
                {t('common.actions.reset', { defaultValue: 'Reset' })}
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              {(['active', 'all', 'done'] as TaskStatusFilter[]).map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setTaskFilters((prev) => ({ ...prev, status }))}
                  className={clsx(
                    'rounded-md border px-3 py-1.5 text-xs font-medium transition',
                    taskFilters.status === status
                      ? 'border-brand-600 bg-brand-600 text-white'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  )}
                >
                  {status === 'active' && `${t('app.reminders.filter.active', { defaultValue: 'Active' })} (${taskCounts.active})`}
                  {status === 'all' && `${t('app.reminders.filter.all', { defaultValue: 'All' })} (${taskCounts.total})`}
                  {status === 'done' && `${t('app.reminders.filter.done', { defaultValue: 'Done' })} (${taskCounts.done})`}
                </button>
              ))}
              {taskCounts.overdue > 0 && (
                <span className="inline-flex items-center rounded-md bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700">
                  {t('app.reminders.status.overdue', { defaultValue: 'Overdue' })}: {taskCounts.overdue}
                </span>
              )}
            </div>

            {remindersState === 'loading' && <div className="text-sm text-slate-500">{t('common.loading')}</div>}
            {remindersState === 'error' && remindersError && (
              <ErrorRecoveryBanner
                compact
                info={remindersError}
                onRetry={() => void loadReminders()}
                retryLabel={t('common.retry', { defaultValue: 'Retry' })}
                secondaryTo="/app/leads"
                secondaryLabel={t('app.reminders.states.empty_cta_leads', { defaultValue: 'Open leads' })}
              />
            )}

            {remindersState !== 'loading' && filteredReminderRows.length === 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <EmptyStatePanel
                  compact
                  title={t('app.reminders.states.empty_title', { defaultValue: 'No reminders yet' })}
                  description={t('app.reminders.states.empty_desc', {
                    defaultValue: 'Create your first reminder to track follow-ups and never lose a lead.',
                  })}
                  primaryAction={{
                    label: t('app.reminders.states.empty_cta_create', { defaultValue: 'Create reminder' }),
                    onClick: openQuickReminderComposer,
                  }}
                  secondaryAction={{
                    label: t('app.reminders.states.empty_cta_leads', { defaultValue: 'Open leads' }),
                    to: '/app/leads',
                  }}
                />
              </div>
            )}

            {filteredReminderRows.length > 0 && (
              <div className="space-y-5">
                {taskGroupLabels.map(({ key, label }) => {
                  const groupItems = reminderGroups[key] || []
                  if (!groupItems.length) return null
                  return (
                    <section key={key} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-slate-900">{label}</h3>
                        <span className="text-xs text-slate-500">{groupItems.length}</span>
                      </div>
                      <div className="space-y-2">
                        {groupItems.map((item) => {
                          const href = reminderEntityHref(item)
                          const busy = taskBusyId === item.id
                          const statusPill = TASK_STATUS_COLORS[item.status] || 'bg-slate-100 text-slate-700'
                          const priorityPill = PRIORITY_COLORS[item.priority || 'normal'] || PRIORITY_COLORS.normal
                          return (
                            <div key={item.id} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                              <div className="flex flex-wrap items-start justify-between gap-3">
                                <div className="min-w-0 flex-1 space-y-1">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className={clsx('rounded-md px-2.5 py-1 text-[11px] font-semibold', statusPill)}>
                                      {reminderStatusLabel(item.status)}
                                    </span>
                                    <span className={clsx('rounded-md px-2 py-0.5 text-[11px] font-medium', priorityPill)}>
                                      {t(`app.reminders.priority.${item.priority || 'normal'}`, { defaultValue: item.priority || 'normal' })}
                                    </span>
                                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                                      {item.entity_type}
                                    </span>
                                  </div>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <h4 className="truncate text-sm font-semibold text-slate-900">{item.title || t('app.candidate_card.reminders.untitled', { defaultValue: 'Untitled' })}</h4>
                                    {href && (
                                      <Link to={href} className="text-xs font-medium text-brand-700 hover:underline">
                                        {t('app.reminders.actions.open_entity', { defaultValue: 'Open' })}
                                      </Link>
                                    )}
                                  </div>
                                  {item.description && <p className="text-xs text-slate-600 whitespace-pre-wrap">{item.description}</p>}
                                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                                    <span>{t('app.candidate_card.reminders.due', { defaultValue: 'Due' })}: {formatTs(item.dueDate)}</span>
                                    <span>{t('app.candidate_card.reminders.remind', { defaultValue: 'Remind' })}: {formatTs(item.remindDate)}</span>
                                    <span>{t('app.reminders.relative', { defaultValue: 'Relative' })}: {formatRelative(item.remindDate || item.dueDate)}</span>
                                  </div>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <button type="button" className="btn-ghost btn-xs" onClick={() => openEdit(item)} disabled={busy || editBusy}>
                                    {t('common.actions.edit', { defaultValue: 'Edit' })}
                                  </button>
                                  <button type="button" className="btn-secondary btn-xs" onClick={() => handleSnooze(item.id, 15)} disabled={busy || isClosedReminderStatus(item.status)}>
                                    +15m
                                  </button>
                                  <button type="button" className="btn-ghost btn-xs" onClick={() => handleSnooze(item.id, 60)} disabled={busy || isClosedReminderStatus(item.status)}>
                                    +1h
                                  </button>
                                  {!isClosedReminderStatus(item.status) && (
                                    <button type="button" className="btn-primary btn-xs" onClick={() => handleComplete(item.id)} disabled={busy}>
                                      {busy ? t('common.loading') : t('app.candidate_card.reminders.complete', { defaultValue: 'Complete' })}
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </section>
                  )
                })}
              </div>
            )}
          </section>
        </>
      )}

      {activeTab === 'events' && (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-[220px] flex-1">
              <input
                className="input w-full"
                value={eventsFilters.search}
                onChange={(e) => setEventsFilters((prev) => ({ ...prev, search: e.target.value }))}
                placeholder={t('app.reminders.filters.search', { defaultValue: 'Search events...' })}
              />
            </div>
            <select className="input" value={eventsFilters.scope} onChange={(e) => setEventsFilters((prev) => ({ ...prev, scope: e.target.value as NotificationsScopeFilter }))}>
              <option value="all">{t('app.reminders.scopes.all', { defaultValue: 'All' })}</option>
              <option value="direct">{t('app.reminders.scopes.direct', { defaultValue: 'Only mine' })}</option>
            </select>
            <select className="input" value={eventsFilters.read} onChange={(e) => setEventsFilters((prev) => ({ ...prev, read: e.target.value as NotificationsReadFilter }))}>
              <option value="unread">{t('app.reminders.filters.unread', { defaultValue: 'Unread' })}</option>
              <option value="all">{t('app.reminders.filters.all', { defaultValue: 'All' })}</option>
            </select>
            <button type="button" className="btn-secondary btn-sm" onClick={() => void loadNotificationsFeed()}>
              {t('app.reminders.actions.refresh', { defaultValue: 'Refresh' })}
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={() => void reconcileAndReloadNotificationsFeed()}>
              {t('app.reminders.actions.sync', { defaultValue: 'Sync' })}
            </button>
            <button type="button" className="btn-ghost btn-sm" onClick={markAllRead} disabled={markAllBusy || notificationCounts.unread === 0}>
              {markAllBusy ? t('common.loading') : t('app.reminders.actions.mark_all', { defaultValue: 'Mark all read' })}
            </button>
          </div>

          {notificationsState === 'loading' && <div className="text-sm text-slate-500">{t('common.loading')}</div>}
          {notificationsState === 'error' && notificationsError && (
            <ErrorRecoveryBanner
              compact
              info={notificationsError}
              onRetry={() => void reconcileAndReloadNotificationsFeed()}
              retryLabel={t('common.retry', { defaultValue: 'Retry' })}
              secondaryTo="/app/communications"
              secondaryLabel={t('app.reminders.actions.open_comm', { defaultValue: 'Open communications' })}
            />
          )}

          {notificationsState !== 'loading' && visibleNotifications.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
              {t('app.reminders.states.empty', { defaultValue: 'No reminders' })}
            </div>
          )}

          {visibleNotifications.length > 0 && (
            <div className="space-y-2">
              {visibleNotifications.map((item) => {
                const createdAt = parseDate(item.created_at)
                const href = notificationEntityHref(item)
                const busy = notifBusyId === item.id
                const desc = (item.payload?.description as string) || ''
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
                            <span className="rounded-md bg-brand-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                              {t('app.reminders.states.badge_new', { defaultValue: 'new' })}
                            </span>
                          )}
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
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
                            className="btn-ghost btn-xs"
                            onClick={() => navigate(href)}
                          >
                            {t('app.reminders.actions.open_page', { defaultValue: 'Open' })}
                          </button>
                        )}
                        {!item.is_read && (
                          <button
                            type="button"
                            className="btn-secondary btn-xs"
                            onClick={() => void markOneRead(item.id)}
                            disabled={busy}
                          >
                            {busy ? t('common.loading') : t('app.reminders.actions.mark_one', { defaultValue: 'Mark read' })}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>
      )}

      {editState && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => !editBusy && setEditState(null)}>
          <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-900">
              {t('app.reminders.edit.title', { defaultValue: 'Edit reminder' })}
            </h3>
            <form onSubmit={submitEdit} className="mt-3 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600">{t('app.reminders.form.title', { defaultValue: 'Task' })}</label>
                <input className="input mt-1 w-full" value={editState.title} onChange={(e) => setEditState((prev) => prev ? { ...prev, title: e.target.value } : prev)} required />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600">{t('app.reminders.form.description', { defaultValue: 'Description' })}</label>
                <textarea className="textarea mt-1 w-full" rows={3} value={editState.description} onChange={(e) => setEditState((prev) => prev ? { ...prev, description: e.target.value } : prev)} />
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-slate-600">{t('app.reminders.form.due', { defaultValue: 'Due date' })}</label>
                  <input type="datetime-local" className="input mt-1 w-full" value={editState.dueAtLocal} onChange={(e) => setEditState((prev) => prev ? { ...prev, dueAtLocal: e.target.value } : prev)} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600">{t('app.reminders.form.remind_at', { defaultValue: 'Remind at' })}</label>
                  <input type="datetime-local" className="input mt-1 w-full" value={editState.remindAtLocal} onChange={(e) => setEditState((prev) => prev ? { ...prev, remindAtLocal: e.target.value } : prev)} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600">{t('app.reminders.form.priority', { defaultValue: 'Priority' })}</label>
                <select className="input mt-1 w-full" value={editState.priority} onChange={(e) => setEditState((prev) => prev ? { ...prev, priority: e.target.value } : prev)}>
                  <option value="low">{t('app.reminders.priority.low', { defaultValue: 'Low' })}</option>
                  <option value="normal">{t('app.reminders.priority.normal', { defaultValue: 'Normal' })}</option>
                  <option value="high">{t('app.reminders.priority.high', { defaultValue: 'High' })}</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" className="btn-ghost" onClick={() => setEditState(null)} disabled={editBusy}>
                  {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                </button>
                <button type="submit" className="btn-primary" disabled={editBusy}>
                  {editBusy ? t('common.loading') : t('common.actions.save', { defaultValue: 'Save' })}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
