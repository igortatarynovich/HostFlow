import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useI18n } from '../../i18n'
import { listManagers } from '../../api/client'
import { getMyWorkingHours, listCommunicationTimeOffRequests, type CommunicationTimeOffRequest, type WorkingHoursSchedule } from '../../api/communications'
import {
  assignCalendarItem,
  cancelCalendarItem,
  completeCalendarConnectionOAuth,
  completeCalendarOAuthQuick,
  createCalendarItem,
  deleteCalendarConnection,
  listCalendarItems,
  listCalendarConnections,
  patchCalendarItem,
  remindCalendarItem,
  queueCalendarReconcile,
  queueCalendarRenew,
  refreshCalendarConnection,
  startCalendarOAuthQuick,
  listCalendarConnectionCursors,
  type CalendarItem,
  type CalendarConnection,
  type CalendarSyncCursor,
  type CalendarProvider,
} from '../../api/calendarIntegrations'

type ConnectFormState = {
  provider: CalendarProvider
  code: string
  clientId: string
  clientSecret: string
  redirectUri: string
  accountRef: string
  scopes: string
}

const INITIAL_FORM: ConnectFormState = {
  provider: 'google',
  code: '',
  clientId: '',
  clientSecret: '',
  redirectUri: typeof window !== 'undefined' ? `${window.location.origin}${CRM_APP_PATHS.settingsIntegrationsGoogle}` : '',
  accountRef: '',
  scopes: 'calendar,calendar.events',
}
const CALENDAR_OAUTH_PROVIDER_STORAGE_KEY = 'hf_calendar_oauth_provider'

function toLocalInput(dt?: string | null): string {
  if (!dt) return ''
  const d = new Date(dt)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

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

function dateKeyLocal(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function extractSyncMeta(item: CalendarItem): {
  provider: string | null
  state: string
  lastSyncAt: string | null
  conflict: boolean
  connectionId: string | null
  version: string | null
} {
  const payload = (item.payload || {}) as Record<string, unknown>
  const provider =
    (typeof payload.provider === 'string' && payload.provider) ||
    (typeof payload.source_provider === 'string' && payload.source_provider) ||
    (item.source === 'google_webhook' ? 'google' : item.source === 'microsoft_webhook' ? 'microsoft' : null)
  const state =
    (typeof payload.sync_state === 'string' && payload.sync_state) ||
    (typeof payload.state === 'string' && payload.state) ||
    (item.status === 'cancelled' ? 'cancelled' : 'unknown')
  const lastSyncAt =
    (typeof payload.last_synced_at === 'string' && payload.last_synced_at) ||
    (typeof payload.synced_at === 'string' && payload.synced_at) ||
    null
  const conflict =
    Boolean(payload.conflict_skipped) ||
    Boolean(payload.sync_conflict) ||
    String(payload.sync_state || '').toLowerCase() === 'conflict_skipped'
  const connectionId = typeof payload.connection_id === 'string' ? payload.connection_id : null
  const version =
    (typeof payload.provider_version === 'string' && payload.provider_version) ||
    (typeof payload.etag === 'string' && payload.etag) ||
    null
  return { provider, state, lastSyncAt, conflict, connectionId, version }
}

function isInWorkingHours(schedule: WorkingHoursSchedule | null, start: Date, end: Date): boolean {
  if (!schedule || !Array.isArray(schedule.days) || schedule.days.length === 0) return true
  const weekday = ((start.getDay() + 6) % 7) + 1
  const day = schedule.days.find((d) => Number(d.weekday) === weekday)
  if (!day || !day.enabled || !Array.isArray(day.windows) || day.windows.length === 0) return false
  const startMinutes = start.getHours() * 60 + start.getMinutes()
  const endMinutes = end.getHours() * 60 + end.getMinutes()
  return day.windows.some((w) => {
    const [fh, fm] = String(w.from || '00:00').split(':').map((x) => Number(x))
    const [th, tm] = String(w.to || '00:00').split(':').map((x) => Number(x))
    if (!Number.isFinite(fh) || !Number.isFinite(fm) || !Number.isFinite(th) || !Number.isFinite(tm)) return false
    const from = fh * 60 + fm
    const to = th * 60 + tm
    return startMinutes >= from && endMinutes <= to
  })
}

function overlapsApprovedTimeOff(
  assigneeId: string | null | undefined,
  start: Date,
  end: Date,
  rows: CommunicationTimeOffRequest[],
): boolean {
  if (!assigneeId) return false
  const s = new Date(start)
  const e = new Date(end)
  return rows.some((r) => {
    if (String(r.requester_user_id || '') !== String(assigneeId)) return false
    if (String(r.status || '').toLowerCase() !== 'approved') return false
    const from = new Date(`${r.start_date}T00:00:00`)
    const to = new Date(`${r.end_date}T23:59:59`)
    return s <= to && e >= from
  })
}

function buildGoogleAuthorizeUrl({
  clientId,
  redirectUri,
  scopes,
  state,
}: {
  clientId: string
  redirectUri: string
  scopes: string[]
  state: string
}) {
  const sp = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    access_type: 'offline',
    prompt: 'consent',
    scope: scopes.join(' '),
    state,
  })
  return `https://accounts.google.com/o/oauth2/v2/auth?${sp.toString()}`
}

function buildMicrosoftAuthorizeUrl({
  clientId,
  redirectUri,
  scopes,
  state,
}: {
  clientId: string
  redirectUri: string
  scopes: string[]
  state: string
}) {
  const msScopes = Array.from(new Set(['offline_access', ...scopes]))
  const sp = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    response_mode: 'query',
    scope: msScopes.join(' '),
    state,
  })
  return `https://login.microsoftonline.com/common/oauth2/v2.0/authorize?${sp.toString()}`
}

export default function CalendarIntegrationsPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [items, setItems] = useState<CalendarConnection[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [form, setForm] = useState<ConnectFormState>(INITIAL_FORM)
  const [refreshClientId, setRefreshClientId] = useState('')
  const [refreshClientSecret, setRefreshClientSecret] = useState('')
  const [refreshScope, setRefreshScope] = useState('')
  const [calendarItems, setCalendarItems] = useState<CalendarItem[]>([])
  const [calendarItemsLoading, setCalendarItemsLoading] = useState(true)
  const [managers, setManagers] = useState<Array<{ id: string; label: string }>>([])
  const [timeOffRows, setTimeOffRows] = useState<CommunicationTimeOffRequest[]>([])
  const [workingHours, setWorkingHours] = useState<WorkingHoursSchedule | null>(null)
  const [cursorByConnection, setCursorByConnection] = useState<Record<string, CalendarSyncCursor[]>>({})
  const [eventForm, setEventForm] = useState({
    title: '',
    description: '',
    kind: 'meeting',
    startsAt: toLocalInput(new Date(Date.now() + 30 * 60_000).toISOString()),
    endsAt: toLocalInput(new Date(Date.now() + 90 * 60_000).toISOString()),
    assigneeId: '',
  })
  const [quickRemindAt, setQuickRemindAt] = useState(toLocalInput(new Date(Date.now() + 20 * 60_000).toISOString()))
  const [assignByItem, setAssignByItem] = useState<Record<string, string>>({})
  const [boardMode, setBoardMode] = useState<'day' | 'week'>('day')
  const [boardDay, setBoardDay] = useState<string>(() => dateKeyLocal(new Date()))
  const [conflictEvent, setConflictEvent] = useState<CalendarItem | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await listCalendarConnections()
      setItems(rows)
    } catch {
      setError(t('admin.calendar_integrations.errors.load_connections'))
    } finally {
      setLoading(false)
    }
  }, [t])

  const loadCalendarItems = useCallback(async () => {
    setCalendarItemsLoading(true)
    try {
      const now = new Date()
      const in30d = new Date(Date.now() + 30 * 24 * 60 * 60_000)
      const rows = await listCalendarItems({ start: now.toISOString(), end: in30d.toISOString() })
      setCalendarItems(rows)
    } catch {
      setError(t('admin.calendar_integrations.errors.load_calendar_items', { defaultValue: 'Failed to load calendar events' }))
    } finally {
      setCalendarItemsLoading(false)
    }
  }, [t])

  const loadManagers = useCallback(async () => {
    try {
      const rows = await listManagers()
      const normalized = (Array.isArray(rows) ? rows : []).map((m: any) => ({
        id: String(m.id),
        label: String(m.label || m.full_name || m.email || m.id),
      }))
      setManagers(normalized)
    } catch {
      setManagers([])
    }
  }, [])

  const loadAvailability = useCallback(async () => {
    try {
      const [timeOffRes, wh] = await Promise.all([
        listCommunicationTimeOffRequests({ limit: 500, status_filter: ['approved'] }),
        getMyWorkingHours().catch(() => null),
      ])
      setTimeOffRows(Array.isArray(timeOffRes?.items) ? timeOffRes.items : [])
      if (wh) setWorkingHours(wh)
    } catch {
      setTimeOffRows([])
    }
  }, [])

  const loadConnectionCursors = useCallback(async (connections: CalendarConnection[]) => {
    const entries = await Promise.all(
      connections.map(async (conn) => {
        try {
          const rows = await listCalendarConnectionCursors(conn.id)
          return [conn.id, rows] as const
        } catch {
          return [conn.id, []] as const
        }
      }),
    )
    const map: Record<string, CalendarSyncCursor[]> = {}
    for (const [id, rows] of entries) map[id] = rows
    setCursorByConnection(map)
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    void loadCalendarItems()
    void loadManagers()
    void loadAvailability()
  }, [loadAvailability, loadCalendarItems, loadManagers])

  useEffect(() => {
    if (!items.length) {
      setCursorByConnection({})
      return
    }
    void loadConnectionCursors(items)
  }, [items, loadConnectionCursors])

  useEffect(() => {
    const code = (searchParams.get('code') || '').trim()
    const state = (searchParams.get('state') || '').trim()
    const providerRaw = (searchParams.get('provider') || '').trim().toLowerCase()
    const providerStored =
      typeof window !== 'undefined'
        ? ((window.sessionStorage.getItem(CALENDAR_OAUTH_PROVIDER_STORAGE_KEY) || '').trim().toLowerCase() as CalendarProvider | '')
        : ''
    const provider = (providerRaw || providerStored || 'google') === 'microsoft' ? 'microsoft' : 'google'
    const oauthError = (searchParams.get('error') || '').trim()
    if (!code && !oauthError) return

    if (oauthError) {
      setError(t('admin.calendar_integrations.errors.oauth_error', { error: oauthError }))
      return
    }
    if (!state) {
      setForm((prev) => ({ ...prev, provider, code }))
      setSuccess(t('admin.calendar_integrations.success.oauth_callback'))
      navigate(CRM_APP_PATHS.settingsIntegrationsGoogle, { replace: true })
      return
    }
    setBusyId('connect-quick')
    setError(null)
    setSuccess(null)
    void (async () => {
      try {
        await completeCalendarOAuthQuick({
          provider,
          code,
          state,
          account_ref: form.accountRef.trim() || undefined,
        })
        setSuccess(t('admin.calendar_integrations.success.connection_created'))
        await load()
      } catch {
        setError(t('admin.calendar_integrations.errors.oauth_complete'))
      } finally {
        setBusyId(null)
        try {
          if (typeof window !== 'undefined') {
            window.sessionStorage.removeItem(CALENDAR_OAUTH_PROVIDER_STORAGE_KEY)
          }
        } catch {
          // ignore
        }
        navigate(CRM_APP_PATHS.settingsIntegrationsGoogle, { replace: true })
      }
    })()
  }, [form.accountRef, load, navigate, searchParams, t])

  const onStartQuickConnect = useCallback(
    async (provider: CalendarProvider) => {
      setBusyId(`quick-start:${provider}`)
      setError(null)
      setSuccess(null)
      try {
        const res = await startCalendarOAuthQuick({ provider })
        if (typeof window !== 'undefined') {
          window.sessionStorage.setItem(CALENDAR_OAUTH_PROVIDER_STORAGE_KEY, provider)
          window.location.href = res.auth_url
        }
      } catch {
        setError(
          t('admin.calendar_integrations.errors.quick_start_not_configured', {
            defaultValue:
              'Quick connect is not configured on this server yet. Ask admin to set calendar OAuth env vars.',
          }),
        )
      } finally {
        setBusyId(null)
      }
    },
    [t],
  )

  const onConnect = useCallback(async () => {
    setBusyId('connect')
    setError(null)
    setSuccess(null)
    try {
      const scopes = form.scopes
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean)
      await completeCalendarConnectionOAuth({
        provider: form.provider,
        code: form.code.trim(),
        client_id: form.clientId.trim(),
        client_secret: form.clientSecret.trim() || undefined,
        redirect_uri: form.redirectUri.trim(),
        account_ref: form.accountRef.trim() || undefined,
        scopes,
      })
      setSuccess(t('admin.calendar_integrations.success.connection_created'))
      setForm((prev) => ({ ...prev, code: '' }))
      await load()
    } catch {
      setError(t('admin.calendar_integrations.errors.oauth_complete'))
    } finally {
      setBusyId(null)
    }
  }, [form, load, t])

  const onRefresh = useCallback(
    async (connectionId: string) => {
      setBusyId(`refresh:${connectionId}`)
      setError(null)
      setSuccess(null)
      try {
        await refreshCalendarConnection(connectionId, {
          client_id: refreshClientId.trim(),
          client_secret: refreshClientSecret.trim() || undefined,
          scope: refreshScope.trim() || undefined,
        })
        setSuccess(t('admin.calendar_integrations.success.token_refreshed'))
        await load()
      } catch {
        setError(t('admin.calendar_integrations.errors.refresh_token'))
      } finally {
        setBusyId(null)
      }
    },
    [load, refreshClientId, refreshClientSecret, refreshScope, t],
  )

  const onDelete = useCallback(
    async (connectionId: string) => {
      setBusyId(`delete:${connectionId}`)
      setError(null)
      setSuccess(null)
      try {
        await deleteCalendarConnection(connectionId)
        setSuccess(t('admin.calendar_integrations.success.connection_deleted'))
        await load()
      } catch {
        setError(t('admin.calendar_integrations.errors.delete_connection'))
      } finally {
        setBusyId(null)
      }
    },
    [load, t],
  )

  const onReconcile = useCallback(
    async (connectionId: string) => {
      setBusyId(`reconcile:${connectionId}`)
      setError(null)
      setSuccess(null)
      try {
        const result = await queueCalendarReconcile({ connection_id: connectionId })
        setSuccess(t('admin.calendar_integrations.success.reconcile_queued', { count: result.queued }))
      } catch {
        setError(t('admin.calendar_integrations.errors.reconcile_queue'))
      } finally {
        setBusyId(null)
      }
    },
    [t],
  )

  const onRenew = useCallback(
    async (connectionId: string) => {
      setBusyId(`renew:${connectionId}`)
      setError(null)
      setSuccess(null)
      try {
        const result = await queueCalendarRenew({ connection_id: connectionId })
        setSuccess(t('admin.calendar_integrations.success.renew_queued', { count: result.queued }))
      } catch {
        setError(t('admin.calendar_integrations.errors.renew_queue'))
      } finally {
        setBusyId(null)
      }
    },
    [t],
  )

  const canRefresh = useMemo(() => Boolean(refreshClientId.trim()), [refreshClientId])
  const managerLabelById = useMemo(() => {
    return new Map(managers.map((m) => [m.id, m.label]))
  }, [managers])
  const connectionHealthById = useMemo(() => {
    const out: Record<string, { lagMinutes: number | null; cursorCount: number; stale: boolean }> = {}
    const now = Date.now()
    for (const conn of items) {
      const cursors = cursorByConnection[conn.id] || []
      const lags = cursors
        .map((c) => {
          const ts = c.last_synced_at ? Date.parse(c.last_synced_at) : NaN
          return Number.isNaN(ts) ? null : Math.max(0, Math.round((now - ts) / 60000))
        })
        .filter((x): x is number => x !== null)
      const lagMinutes = lags.length ? Math.max(...lags) : null
      out[conn.id] = {
        lagMinutes,
        cursorCount: cursors.length,
        stale: lagMinutes !== null && lagMinutes > 60,
      }
    }
    return out
  }, [cursorByConnection, items])
  const parsedScopes = useMemo(
    () =>
      form.scopes
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean),
    [form.scopes],
  )

  const oauthStartUrl = useMemo(() => {
    const clientId = form.clientId.trim()
    const redirectUri = form.redirectUri.trim()
    if (!clientId || !redirectUri || parsedScopes.length === 0) return null
    const state = `hf_calendar_${form.provider}_${Date.now()}`
    if (form.provider === 'microsoft') {
      return buildMicrosoftAuthorizeUrl({ clientId, redirectUri, scopes: parsedScopes, state })
    }
    return buildGoogleAuthorizeUrl({ clientId, redirectUri, scopes: parsedScopes, state })
  }, [form.clientId, form.provider, form.redirectUri, parsedScopes])

  const onCreateCalendarEvent = useCallback(async () => {
    if (!eventForm.title.trim() || !eventForm.startsAt) return
    const start = new Date(eventForm.startsAt)
    const end = eventForm.endsAt ? new Date(eventForm.endsAt) : null
    if (Number.isNaN(start.getTime()) || (end && Number.isNaN(end.getTime()))) {
      setError(t('admin.calendar_integrations.errors.invalid_datetime', { defaultValue: 'Invalid event date/time' }))
      return
    }
    setBusyId('create-event')
    setError(null)
    setSuccess(null)
    try {
      await createCalendarItem({
        title: eventForm.title.trim(),
        description: eventForm.description.trim() || undefined,
        kind: eventForm.kind || 'meeting',
        starts_at: start.toISOString(),
        ends_at: end?.toISOString() || undefined,
        assignee_id: eventForm.assigneeId || undefined,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
        payload: { source: 'settings_calendar_integrations_ui' },
      })
      setSuccess(t('admin.calendar_integrations.success.event_created', { defaultValue: 'Calendar event created' }))
      setEventForm((prev) => ({ ...prev, title: '', description: '' }))
      await loadCalendarItems()
    } catch {
      setError(t('admin.calendar_integrations.errors.create_event', { defaultValue: 'Failed to create calendar event' }))
    } finally {
      setBusyId(null)
    }
  }, [eventForm, loadCalendarItems, t])

  const onCancelCalendarEvent = useCallback(
    async (itemId: string) => {
      setBusyId(`cancel-event:${itemId}`)
      setError(null)
      setSuccess(null)
      try {
        await cancelCalendarItem(itemId)
        setSuccess(t('admin.calendar_integrations.success.event_cancelled', { defaultValue: 'Calendar event cancelled' }))
        await loadCalendarItems()
      } catch {
        setError(t('admin.calendar_integrations.errors.cancel_event', { defaultValue: 'Failed to cancel event' }))
      } finally {
        setBusyId(null)
      }
    },
    [loadCalendarItems, t],
  )

  const onRemindCalendarEvent = useCallback(
    async (itemId: string) => {
      setBusyId(`remind-event:${itemId}`)
      setError(null)
      setSuccess(null)
      try {
        const remindAt = quickRemindAt ? new Date(quickRemindAt) : null
        await remindCalendarItem(itemId, {
          remind_at: remindAt && !Number.isNaN(remindAt.getTime()) ? remindAt.toISOString() : undefined,
          channel: 'in_app',
        })
        setSuccess(t('admin.calendar_integrations.success.reminder_created', { defaultValue: 'Reminder created for event' }))
        await loadCalendarItems()
      } catch {
        setError(t('admin.calendar_integrations.errors.remind_event', { defaultValue: 'Failed to create reminder for event' }))
      } finally {
        setBusyId(null)
      }
    },
    [loadCalendarItems, quickRemindAt, t],
  )

  const onAssignCalendarEvent = useCallback(
    async (itemId: string) => {
      const assigneeId = (assignByItem[itemId] || '').trim()
      if (!assigneeId) return
      const item = calendarItems.find((x) => x.id === itemId)
      const start = item ? new Date(item.starts_at) : null
      const end = item ? new Date(item.ends_at || new Date(new Date(item.starts_at).getTime() + 60 * 60_000).toISOString()) : null
      if (start && end && !Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime())) {
        if (overlapsApprovedTimeOff(assigneeId, start, end, timeOffRows)) {
          setError(
            t('admin.calendar_integrations.errors.assignee_timeoff_conflict', {
              defaultValue: 'Selected assignee is on approved time off for this interval',
            }),
          )
          return
        }
        if (!isInWorkingHours(workingHours, start, end)) {
          setError(
            t('admin.calendar_integrations.errors.outside_working_hours', {
              defaultValue: 'Selected event is outside configured working hours',
            }),
          )
          return
        }
      }
      setBusyId(`assign-event:${itemId}`)
      setError(null)
      setSuccess(null)
      try {
        await assignCalendarItem(itemId, { assignee_id: assigneeId })
        setSuccess(t('admin.calendar_integrations.success.event_assigned', { defaultValue: 'Event assignee updated' }))
        await loadCalendarItems()
      } catch {
        setError(t('admin.calendar_integrations.errors.assign_event', { defaultValue: 'Failed to assign event' }))
      } finally {
        setBusyId(null)
      }
    },
    [assignByItem, calendarItems, loadCalendarItems, t, timeOffRows, workingHours],
  )

  const onRetrySyncForEvent = useCallback(
    async (item: CalendarItem) => {
      const syncMeta = extractSyncMeta(item)
      setBusyId(`sync-event:${item.id}`)
      setError(null)
      setSuccess(null)
      try {
        const result = await queueCalendarReconcile({
          connection_id: syncMeta.connectionId || undefined,
          provider: (syncMeta.provider as CalendarProvider | null) || undefined,
        })
        setSuccess(
          t('admin.calendar_integrations.success.reconcile_queued', {
            count: result.queued,
            defaultValue: `Queued reconciliation jobs: ${result.queued}`,
          }),
        )
      } catch {
        setError(
          t('admin.calendar_integrations.errors.reconcile_queue', {
            defaultValue: 'Failed to queue reconciliation job',
          }),
        )
      } finally {
        setBusyId(null)
      }
    },
    [t],
  )

  const onMoveCalendarEvent = useCallback(
    async (item: CalendarItem, byMinutes: number) => {
      const start = new Date(item.starts_at)
      if (Number.isNaN(start.getTime())) return
      const end = item.ends_at ? new Date(item.ends_at) : null
      const movedStart = new Date(start.getTime() + byMinutes * 60_000)
      const movedEnd = end && !Number.isNaN(end.getTime()) ? new Date(end.getTime() + byMinutes * 60_000) : null
      const safeEnd = movedEnd || new Date(movedStart.getTime() + 60 * 60_000)
      if (overlapsApprovedTimeOff(item.assignee_id || null, movedStart, safeEnd, timeOffRows)) {
        setError(
          t('admin.calendar_integrations.errors.assignee_timeoff_conflict', {
            defaultValue: 'Selected assignee is on approved time off for this interval',
          }),
        )
        return
      }
      if (!isInWorkingHours(workingHours, movedStart, safeEnd)) {
        setError(
          t('admin.calendar_integrations.errors.outside_working_hours', {
            defaultValue: 'Selected event is outside configured working hours',
          }),
        )
        return
      }
      setBusyId(`move-event:${item.id}:${byMinutes}`)
      setError(null)
      setSuccess(null)
      try {
        await patchCalendarItem(item.id, {
          starts_at: movedStart.toISOString(),
          ends_at: movedEnd?.toISOString(),
          payload: {
            move_reason: 'calendar_integrations_operational_board',
            moved_by_minutes: byMinutes,
          },
        })
        setSuccess(t('admin.calendar_integrations.success.event_moved', { defaultValue: 'Event moved successfully' }))
        await loadCalendarItems()
      } catch {
        setError(t('admin.calendar_integrations.errors.move_event', { defaultValue: 'Failed to move event' }))
      } finally {
        setBusyId(null)
      }
    },
    [loadCalendarItems, t, timeOffRows, workingHours],
  )

  const boardEvents = useMemo(() => {
    const dayStart = startOfDay(new Date(`${boardDay}T00:00:00`))
    const dayEnd = addDays(dayStart, 1)
    const weekEnd = addDays(dayStart, 7)
    return calendarItems
      .filter((it) => {
        const start = new Date(it.starts_at)
        if (Number.isNaN(start.getTime())) return false
        if (boardMode === 'day') return start >= dayStart && start < dayEnd
        return start >= dayStart && start < weekEnd
      })
      .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
  }, [boardDay, boardMode, calendarItems])

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 py-6 sm:py-8">
      <SettingsSubpageHeader
        backHref={CRM_APP_PATHS.settingsIntegrations}
        backLabel={t('admin.calendar_integrations.header.back_to_hub')}
        kicker={t('admin.calendar_integrations.header.kicker')}
        title={t('admin.calendar_integrations.header.title')}
        subtitle={t('admin.calendar_integrations.header.subtitle')}
      />

      {error ? <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</div> : null}
      {success ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">{success}</div>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">{t('admin.calendar_integrations.connect.title')}</h2>
        <p className="mt-1 text-sm text-slate-600">
          {t('admin.calendar_integrations.connect.subtitle')}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            onClick={() => void onStartQuickConnect('google')}
            disabled={busyId === 'quick-start:google' || busyId === 'connect-quick'}
          >
            {busyId === 'quick-start:google'
              ? t('admin.calendar_integrations.actions.connecting')
              : t('admin.calendar_integrations.actions.quick_connect_google', { defaultValue: 'Connect Google (1 click)' })}
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50"
            onClick={() => void onStartQuickConnect('microsoft')}
            disabled={busyId === 'quick-start:microsoft' || busyId === 'connect-quick'}
          >
            {busyId === 'quick-start:microsoft'
              ? t('admin.calendar_integrations.actions.connecting')
              : t('admin.calendar_integrations.actions.quick_connect_microsoft', { defaultValue: 'Connect Microsoft (1 click)' })}
          </button>
        </div>
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
          <p>{t('admin.calendar_integrations.connect.quick_flow')}</p>
        </div>
        <details className="mt-3 rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2">
          <summary className="cursor-pointer text-sm font-medium text-slate-800">
            {t('admin.calendar_integrations.connect.manual_toggle', { defaultValue: 'Manual / advanced setup' })}
          </summary>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.fields.provider')}</span>
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.provider}
              onChange={(e) => setForm((p) => ({ ...p, provider: e.target.value as CalendarProvider }))}
            >
              <option value="google">{t('admin.calendar_integrations.providers.google')}</option>
              <option value="microsoft">{t('admin.calendar_integrations.providers.microsoft')}</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.fields.account_ref')}</span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.accountRef}
              onChange={(e) => setForm((p) => ({ ...p, accountRef: e.target.value }))}
              placeholder={t('admin.calendar_integrations.placeholders.account_ref')}
            />
          </label>
          <label className="text-sm md:col-span-2">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.fields.oauth_code')}</span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.code}
              onChange={(e) => setForm((p) => ({ ...p, code: e.target.value }))}
              placeholder={t('admin.calendar_integrations.placeholders.oauth_code')}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.fields.client_id')}</span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.clientId}
              onChange={(e) => setForm((p) => ({ ...p, clientId: e.target.value }))}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.fields.client_secret')}</span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.clientSecret}
              onChange={(e) => setForm((p) => ({ ...p, clientSecret: e.target.value }))}
            />
          </label>
          <label className="text-sm md:col-span-2">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.fields.redirect_uri')}</span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.redirectUri}
              onChange={(e) => setForm((p) => ({ ...p, redirectUri: e.target.value }))}
              placeholder={t('admin.calendar_integrations.placeholders.redirect_uri')}
            />
          </label>
          <label className="text-sm md:col-span-2">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.fields.scopes')}</span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.scopes}
              onChange={(e) => setForm((p) => ({ ...p, scopes: e.target.value }))}
              placeholder={t('admin.calendar_integrations.placeholders.scopes')}
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!oauthStartUrl}
            onClick={() => {
              if (!oauthStartUrl) return
              window.location.href = oauthStartUrl
            }}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t('admin.calendar_integrations.actions.open_oauth')}
          </button>
          <button
            type="button"
            onClick={() => void navigator.clipboard?.writeText(oauthStartUrl || '')}
            disabled={!oauthStartUrl}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t('admin.calendar_integrations.actions.copy_oauth_url')}
          </button>
        </div>
        <button
          type="button"
          onClick={() => void onConnect()}
          disabled={
            busyId === 'connect' ||
            !form.code.trim() ||
            !form.clientId.trim() ||
            !form.redirectUri.trim()
          }
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busyId === 'connect'
            ? t('admin.calendar_integrations.actions.connecting')
            : t('admin.calendar_integrations.actions.complete_oauth')}
        </button>
        </details>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <button
          type="button"
          className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          onClick={() => setShowAdvanced((v) => !v)}
        >
          {showAdvanced
            ? t('admin.calendar_integrations.connect.hide_advanced', { defaultValue: 'Hide advanced tools' })
            : t('admin.calendar_integrations.connect.show_advanced', { defaultValue: 'Show advanced tools' })}
        </button>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">{t('admin.calendar_integrations.refresh.title')}</h2>
        <p className="mt-1 text-sm text-slate-600">
          {t('admin.calendar_integrations.refresh.subtitle')}
        </p>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder={t('admin.calendar_integrations.fields.client_id')}
            value={refreshClientId}
            onChange={(e) => setRefreshClientId(e.target.value)}
          />
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder={t('admin.calendar_integrations.fields.client_secret')}
            value={refreshClientSecret}
            onChange={(e) => setRefreshClientSecret(e.target.value)}
          />
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder={t('admin.calendar_integrations.placeholders.refresh_scope')}
            value={refreshScope}
            onChange={(e) => setRefreshScope(e.target.value)}
          />
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">{t('admin.calendar_integrations.connections.title')}</h2>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {t('admin.calendar_integrations.actions.refresh_list')}
          </button>
        </div>
        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-slate-500">{t('admin.calendar_integrations.connections.empty')}</p>
        ) : (
          <ul className="space-y-3">
            {items.map((it) => (
              <li key={it.id} className="rounded-lg border border-slate-200 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {it.provider.toUpperCase()} {it.account_ref ? `· ${it.account_ref}` : ''}
                    </p>
                    <p className="text-xs text-slate-500">{t('admin.calendar_integrations.connections.status', { status: it.status })}</p>
                    {(() => {
                      const h = connectionHealthById[it.id]
                      if (!h) return null
                      return (
                        <p className={`text-xs ${h.stale ? 'text-amber-700' : 'text-slate-500'}`}>
                          {t('admin.calendar_integrations.connections.sync_health', {
                            defaultValue: 'Sync lag: {lag} min · cursors: {count}',
                            lag: h.lagMinutes == null ? 'n/a' : String(h.lagMinutes),
                            count: String(h.cursorCount),
                          })}
                        </p>
                      )
                    })()}
                    {it.last_error ? (
                      <p className="text-xs text-red-700">{t('admin.calendar_integrations.connections.error', { error: it.last_error })}</p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {!showAdvanced ? (
                      <button
                        type="button"
                        className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                        onClick={() => void onStartQuickConnect(it.provider)}
                        disabled={busyId === `quick-start:${it.provider}` || busyId === 'connect-quick'}
                      >
                        {t('admin.calendar_integrations.actions.reconnect', { defaultValue: 'Reconnect' })}
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                          onClick={() => void onReconcile(it.id)}
                          disabled={busyId === `reconcile:${it.id}`}
                        >
                          {busyId === `reconcile:${it.id}`
                            ? t('admin.calendar_integrations.actions.queueing')
                            : t('admin.calendar_integrations.actions.reconcile')}
                        </button>
                        <button
                          type="button"
                          className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                          onClick={() => void onRenew(it.id)}
                          disabled={busyId === `renew:${it.id}`}
                        >
                          {busyId === `renew:${it.id}`
                            ? t('admin.calendar_integrations.actions.queueing')
                            : t('admin.calendar_integrations.actions.renew_sub')}
                        </button>
                        <button
                          type="button"
                          className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                          onClick={() => void onRefresh(it.id)}
                          disabled={busyId === `refresh:${it.id}` || !canRefresh}
                          title={canRefresh ? '' : t('admin.calendar_integrations.hints.fill_client_id_first')}
                        >
                          {busyId === `refresh:${it.id}`
                            ? t('admin.calendar_integrations.actions.refreshing')
                            : t('admin.calendar_integrations.actions.refresh_token')}
                        </button>
                        <button
                          type="button"
                          className="rounded border border-red-300 px-2.5 py-1 text-xs text-red-700"
                          onClick={() => void onDelete(it.id)}
                          disabled={busyId === `delete:${it.id}`}
                        >
                          {busyId === `delete:${it.id}`
                            ? t('admin.calendar_integrations.actions.deleting')
                            : t('admin.calendar_integrations.actions.delete')}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {showAdvanced ? (
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('admin.calendar_integrations.events.title', { defaultValue: 'Calendar events and reminders' })}
          </h2>
          <button
            type="button"
            className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            onClick={() => void loadCalendarItems()}
            disabled={calendarItemsLoading}
          >
            {t('admin.calendar_integrations.actions.refresh_list')}
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.events.event_title', { defaultValue: 'Title' })}</span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={eventForm.title}
              onChange={(e) => setEventForm((p) => ({ ...p, title: e.target.value }))}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.events.event_kind', { defaultValue: 'Kind' })}</span>
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={eventForm.kind}
              onChange={(e) => setEventForm((p) => ({ ...p, kind: e.target.value }))}
            >
              <option value="meeting">{t('admin.calendar_integrations.events.kind_meeting', { defaultValue: 'Meeting' })}</option>
              <option value="call">{t('admin.calendar_integrations.events.kind_call', { defaultValue: 'Call' })}</option>
              <option value="task">{t('admin.calendar_integrations.events.kind_task', { defaultValue: 'Task' })}</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.events.starts_at', { defaultValue: 'Starts at' })}</span>
            <input
              type="datetime-local"
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={eventForm.startsAt}
              onChange={(e) => setEventForm((p) => ({ ...p, startsAt: e.target.value }))}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.events.ends_at', { defaultValue: 'Ends at' })}</span>
            <input
              type="datetime-local"
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={eventForm.endsAt}
              onChange={(e) => setEventForm((p) => ({ ...p, endsAt: e.target.value }))}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.events.assignee', { defaultValue: 'Assignee' })}</span>
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={eventForm.assigneeId}
              onChange={(e) => setEventForm((p) => ({ ...p, assigneeId: e.target.value }))}
            >
              <option value="">{t('admin.calendar_integrations.events.unassigned', { defaultValue: 'Unassigned' })}</option>
              {managers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.events.remind_at', { defaultValue: 'Default remind at' })}</span>
            <input
              type="datetime-local"
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              value={quickRemindAt}
              onChange={(e) => setQuickRemindAt(e.target.value)}
            />
          </label>
          <label className="text-sm md:col-span-2">
            <span className="mb-1 block text-slate-600">{t('admin.calendar_integrations.events.description', { defaultValue: 'Description' })}</span>
            <textarea
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              rows={2}
              value={eventForm.description}
              onChange={(e) => setEventForm((p) => ({ ...p, description: e.target.value }))}
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() => void onCreateCalendarEvent()}
          disabled={busyId === 'create-event' || !eventForm.title.trim() || !eventForm.startsAt}
          className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busyId === 'create-event'
            ? t('admin.calendar_integrations.events.creating', { defaultValue: 'Creating...' })
            : t('admin.calendar_integrations.events.create_event', { defaultValue: 'Create event' })}
        </button>

        <div className="mt-5">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={`rounded border px-3 py-1.5 text-xs ${boardMode === 'day' ? 'border-brand-600 text-brand-700' : 'border-slate-300 text-slate-700'}`}
              onClick={() => setBoardMode('day')}
            >
              {t('admin.calendar_integrations.events.day_mode', { defaultValue: 'Day' })}
            </button>
            <button
              type="button"
              className={`rounded border px-3 py-1.5 text-xs ${boardMode === 'week' ? 'border-brand-600 text-brand-700' : 'border-slate-300 text-slate-700'}`}
              onClick={() => setBoardMode('week')}
            >
              {t('admin.calendar_integrations.events.week_mode', { defaultValue: 'Week' })}
            </button>
            <input
              type="date"
              className="rounded border border-slate-300 px-2 py-1 text-xs"
              value={boardDay}
              onChange={(e) => setBoardDay(e.target.value)}
            />
            <button
              type="button"
              className="rounded border border-slate-300 px-2.5 py-1 text-xs text-slate-700"
              onClick={() => setBoardDay(dateKeyLocal(new Date()))}
            >
              {t('admin.calendar_integrations.events.today', { defaultValue: 'Today' })}
            </button>
          </div>
          {calendarItemsLoading ? (
            <p className="text-sm text-slate-500">{t('common.loading')}</p>
          ) : boardEvents.length === 0 ? (
            <p className="text-sm text-slate-500">
              {t('admin.calendar_integrations.events.empty', { defaultValue: 'No events in selected range.' })}
            </p>
          ) : (
            <ul className="space-y-2">
              {boardEvents.map((it) => (
                <li key={it.id} className="rounded-lg border border-slate-200 p-3">
                  {(() => {
                    const start = new Date(it.starts_at)
                    const end = it.ends_at ? new Date(it.ends_at) : new Date(start.getTime() + 60 * 60_000)
                    const onTimeOff = !Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime()) && overlapsApprovedTimeOff(it.assignee_id, start, end, timeOffRows)
                    const outsideHours = !Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime()) && !isInWorkingHours(workingHours, start, end)
                    return onTimeOff || outsideHours ? (
                      <div className="mb-2 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                        {onTimeOff
                          ? t('admin.calendar_integrations.events.availability_conflict_timeoff', {
                              defaultValue: 'Assignee has approved time off in this interval.',
                            })
                          : t('admin.calendar_integrations.events.availability_conflict_hours', {
                              defaultValue: 'Event is outside configured working hours.',
                            })}
                      </div>
                    ) : null
                  })()}
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{it.title}</p>
                      <p className="text-xs text-slate-600">
                        {it.kind} · {it.status} · {new Date(it.starts_at).toLocaleString()}
                        {it.ends_at ? ` - ${new Date(it.ends_at).toLocaleString()}` : ''}
                      </p>
                      {it.assignee_id ? (
                        <p className="text-xs text-slate-500">
                          {t('admin.calendar_integrations.events.assignee', { defaultValue: 'Assignee' })}:{' '}
                          {managerLabelById.get(it.assignee_id) || it.assignee_id}
                        </p>
                      ) : null}
                      {it.description ? <p className="mt-1 text-sm text-slate-700">{it.description}</p> : null}
                      {(() => {
                        const sync = extractSyncMeta(it)
                        return (
                          <p className="mt-1 text-xs text-slate-500">
                            {t('admin.calendar_integrations.events.sync_status', { defaultValue: 'Sync' })}: {sync.state}
                            {sync.provider ? ` · ${sync.provider}` : ''}
                            {sync.lastSyncAt ? ` · ${new Date(sync.lastSyncAt).toLocaleString()}` : ''}
                            {sync.conflict ? ` · ${t('admin.calendar_integrations.events.conflict', { defaultValue: 'conflict' })}` : ''}
                            {sync.version ? ` · v:${sync.version}` : ''}
                          </p>
                        )
                      })()}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                        onClick={() => void onRemindCalendarEvent(it.id)}
                        disabled={busyId === `remind-event:${it.id}`}
                      >
                        {busyId === `remind-event:${it.id}`
                          ? t('admin.calendar_integrations.actions.queueing')
                          : t('admin.calendar_integrations.events.remind', { defaultValue: 'Remind' })}
                      </button>
                      <button
                        type="button"
                        className="rounded border border-red-300 px-2.5 py-1 text-xs text-red-700"
                        onClick={() => void onCancelCalendarEvent(it.id)}
                        disabled={busyId === `cancel-event:${it.id}` || it.status === 'cancelled'}
                      >
                        {busyId === `cancel-event:${it.id}`
                          ? t('admin.calendar_integrations.actions.queueing')
                          : t('admin.calendar_integrations.events.cancel', { defaultValue: 'Cancel' })}
                      </button>
                      <button
                        type="button"
                        className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                        onClick={() => void onRetrySyncForEvent(it)}
                        disabled={busyId === `sync-event:${it.id}`}
                      >
                        {busyId === `sync-event:${it.id}`
                          ? t('admin.calendar_integrations.actions.queueing')
                          : t('admin.calendar_integrations.events.retry_sync', { defaultValue: 'Retry sync' })}
                      </button>
                      {extractSyncMeta(it).conflict ? (
                        <button
                          type="button"
                          className="rounded border border-amber-300 px-2.5 py-1 text-xs text-amber-800"
                          onClick={() => setConflictEvent(it)}
                        >
                          {t('admin.calendar_integrations.events.view_conflict', { defaultValue: 'View conflict' })}
                        </button>
                      ) : null}
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <select
                      className="rounded border border-slate-300 px-2 py-1 text-xs"
                      value={assignByItem[it.id] ?? it.assignee_id ?? ''}
                      onChange={(e) => setAssignByItem((prev) => ({ ...prev, [it.id]: e.target.value }))}
                    >
                      <option value="">{t('admin.calendar_integrations.events.unassigned', { defaultValue: 'Unassigned' })}</option>
                      {managers.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                      onClick={() => void onAssignCalendarEvent(it.id)}
                      disabled={busyId === `assign-event:${it.id}` || !(assignByItem[it.id] ?? it.assignee_id)}
                    >
                      {busyId === `assign-event:${it.id}`
                        ? t('admin.calendar_integrations.actions.queueing')
                        : t('admin.calendar_integrations.events.assign', { defaultValue: 'Assign' })}
                    </button>
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                      onClick={() => void onMoveCalendarEvent(it, 15)}
                      disabled={busyId === `move-event:${it.id}:15`}
                    >
                      +15m
                    </button>
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                      onClick={() => void onMoveCalendarEvent(it, 60)}
                      disabled={busyId === `move-event:${it.id}:60`}
                    >
                      +1h
                    </button>
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-2.5 py-1 text-xs"
                      onClick={() => void onMoveCalendarEvent(it, 24 * 60)}
                      disabled={busyId === `move-event:${it.id}:1440`}
                    >
                      +1d
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
      ) : null}

      {showAdvanced && conflictEvent ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50/40 p-5 shadow-sm">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-amber-900">
              {t('admin.calendar_integrations.events.conflict_details', { defaultValue: 'Sync conflict details' })}
            </h3>
            <button
              type="button"
              className="rounded border border-amber-300 px-2 py-1 text-xs text-amber-900"
              onClick={() => setConflictEvent(null)}
            >
              {t('admin.calendar_integrations.actions.close', { defaultValue: 'Close' })}
            </button>
          </div>
          <p className="mt-2 text-xs text-amber-900">
            {t('admin.calendar_integrations.events.conflict_hint', {
              defaultValue:
                'This event had a provider version conflict. Review payload/version and run Retry sync after resolving source state.',
            })}
          </p>
          <pre className="mt-3 max-h-64 overflow-auto rounded bg-white p-3 text-[11px] text-slate-700">
            {JSON.stringify(
              {
                id: conflictEvent.id,
                title: conflictEvent.title,
                status: conflictEvent.status,
                starts_at: conflictEvent.starts_at,
                ends_at: conflictEvent.ends_at,
                source: conflictEvent.source,
                payload: conflictEvent.payload || {},
              },
              null,
              2,
            )}
          </pre>
        </section>
      ) : null}
    </div>
  )
}
