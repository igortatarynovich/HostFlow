import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { enUS, pl as plLocale, ru as ruLocale } from 'date-fns/locale'
import { listNotifications, markNotificationsRead, reconcileNotifications } from '../api/client'
import {
  executeWorkspaceCommand,
  listCommunicationThreads,
  type CommunicationThread,
} from '../api/communications'
import type { NotificationItem, NotificationListResponse } from '../api/types'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useI18n } from '../i18n'
import {
  incidentGroupOf,
  notificationThreadId,
  opsModeFromNotificationPayload,
  opsModeFromThread,
  type CommunicationIncidentGroup,
  type CommunicationOpsMode,
} from '../utils/communicationsOpsMode'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { buildInboxThreadPath } from '../utils/inboxDeepLinks'

const DATE_LOCALES = { en: enUS, ru: ruLocale, pl: plLocale }
type OpsMode = CommunicationOpsMode
type IncidentGroup = CommunicationIncidentGroup

function toTs(value?: string | null): number {
  if (!value) return 0
  const ts = Date.parse(value)
  return Number.isFinite(ts) ? ts : 0
}

function hasFalseSlaSignal(item: NotificationItem): boolean {
  const payload = (item.payload || {}) as Record<string, any>
  if (payload.false_positive === true) return true
  if (payload.no_reply_needed === true) return true
  if (payload.sla_muted === true) return true
  const reason = String(payload.resolution_reason || payload.close_reason || payload.reason || '')
    .trim()
    .toLowerCase()
  return ['no_reply_needed', 'muted', 'snoozed', 'cancelled'].some((token) => reason.includes(token))
}

const modeFromPayload = opsModeFromNotificationPayload
const modeFromThread = opsModeFromThread
const groupOf = incidentGroupOf

export default function CommunicationsSlaIncidentsPage() {
  const { t, locale } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<FriendlyErrorInfo | null>(null)
  const [items, setItems] = useState<NotificationItem[]>([])
  const [opsBusyId, setOpsBusyId] = useState<string | null>(null)
  const [opsModeOverrides, setOpsModeOverrides] = useState<Record<string, OpsMode>>({})
  const [threadModesById, setThreadModesById] = useState<Record<string, OpsMode>>({})
  const [query, setQuery] = useState('')
  const [includeRead, setIncludeRead] = useState(false)
  const [groupFilter, setGroupFilter] = useState<IncidentGroup>('open')

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      try {
        await reconcileNotifications()
      } catch {
        // Keep loading even when reconcile endpoint is temporarily unavailable.
      }
      const data = (await listNotifications({
        scope: 'direct',
        includeRead: true,
        limit: 200,
      })) as NotificationListResponse
      const rows = (Array.isArray(data?.items) ? data.items : [])
        .filter((x) => String(x.event_type || '').toLowerCase() === 'communications_sla_overdue')
        .sort((a, b) => {
          const ar = a.is_read ? 1 : 0
          const br = b.is_read ? 1 : 0
          if (ar !== br) return ar - br
          return toTs(b.created_at) - toTs(a.created_at)
        })
      setItems(rows)

      try {
        const threadIds = Array.from(new Set(rows.map((item) => notificationThreadId(item)).filter(Boolean)))
        if (!threadIds.length) {
          setThreadModesById({})
        } else {
          const threadsRes = await listCommunicationThreads({ limit: 1000, includeArchived: true })
          const idSet = new Set(threadIds)
          const next: Record<string, OpsMode> = {}
          ;(Array.isArray(threadsRes.items) ? threadsRes.items : []).forEach((thread) => {
            const threadId = String(thread.id || '')
            if (!idSet.has(threadId)) return
            const mode = modeFromThread(thread)
            if (mode) next[threadId] = mode
          })
          setThreadModesById(next)
        }
      } catch {
        // Do not block incidents list on thread state fetch errors.
      }
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.sla_incidents.errors.load'))) {
        setLoadError(getFriendlyErrorInfo(err, t('app.sla_incidents.errors.load'), t))
      }
    } finally {
      setLoading(false)
    }
  }, [planLimitModal, t])

  useEffect(() => {
    void load()
  }, [load])

  const baseFiltered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return items
      .filter((x) => (includeRead ? true : !x.is_read))
      .filter((x) => {
        if (!q) return true
        const payload = (x.payload || {}) as Record<string, any>
        const hay = [
          x.event_type,
          x.entity_type,
          x.entity_id,
          payload.title,
          payload.description,
          payload.channel,
          payload.thread_id,
        ]
          .map((v) => String(v || ''))
          .join(' ')
          .toLowerCase()
        return hay.includes(q)
      })
  }, [includeRead, items, query])

  const groupedCounts = useMemo(() => {
    const counts: Record<IncidentGroup, number> = {
      open: 0,
      in_work: 0,
      later: 0,
      escalated: 0,
      no_reply_needed: 0,
      closed: 0,
    }
    baseFiltered.forEach((item) => {
      const resolvedMode = opsModeOverrides[item.id] || threadModesById[notificationThreadId(item)] || modeFromPayload(item)
      const g = groupOf(item, resolvedMode)
      counts[g] += 1
    })
    return counts
  }, [baseFiltered, opsModeOverrides, threadModesById])

  const filtered = useMemo(
    () =>
      baseFiltered.filter((item) => {
        const resolvedMode = opsModeOverrides[item.id] || threadModesById[notificationThreadId(item)] || modeFromPayload(item)
        return groupOf(item, resolvedMode) === groupFilter
      }),
    [baseFiltered, groupFilter, opsModeOverrides, threadModesById],
  )

  const unreadCount = useMemo(() => items.filter((x) => !x.is_read).length, [items])
  const trustReport = useMemo(() => {
    const total = items.length
    const closed = items.filter((x) => x.is_read).length
    const open = Math.max(0, total - closed)
    const closureRatePct = total > 0 ? Math.round((closed / total) * 100) : 0
    const potentialFalseSla = items.filter((x) => hasFalseSlaSignal(x)).length

    const byKey = new Map<string, number>()
    items.forEach((item) => {
      const payload = (item.payload || {}) as Record<string, any>
      const dedupeKey = String(payload.dedupe_key || '').trim()
      const threadId = String(payload.thread_id || '').trim()
      const key = dedupeKey || (threadId ? `thread:${threadId}` : '')
      if (!key) return
      byKey.set(key, Number(byKey.get(key) || 0) + 1)
    })
    let duplicateGroups = 0
    let duplicateEvents = 0
    byKey.forEach((count) => {
      if (count > 1) {
        duplicateGroups += 1
        duplicateEvents += count - 1
      }
    })

    return {
      total,
      closed,
      open,
      closureRatePct,
      potentialFalseSla,
      duplicateGroups,
      duplicateEvents,
    }
  }, [items])

  const openThread = (item: NotificationItem) => {
    const threadId = notificationThreadId(item)
    if (threadId) {
      navigate(buildInboxThreadPath(threadId))
      return
    }
    navigate(CRM_APP_PATHS.inbox)
  }

  const markOneRead = async (item: NotificationItem) => {
    if (item.is_read) return
    try {
      await markNotificationsRead({ ids: [item.id] })
      setItems((prev) => prev.map((x) => (x.id === item.id ? { ...x, is_read: true, read_at: new Date().toISOString() } : x)))
    } catch {
      // ignore transient errors, user can retry
    }
  }

  const markAllRead = async () => {
    const ids = items.filter((x) => !x.is_read).map((x) => x.id)
    if (ids.length === 0) return
    try {
      await markNotificationsRead({ ids })
      setItems((prev) => prev.map((x) => ({ ...x, is_read: true, read_at: x.read_at || new Date().toISOString() })))
    } catch {
      // ignore transient errors, user can retry
    }
  }

  const applyOpsMode = async (item: NotificationItem, mode: OpsMode) => {
    const threadId = notificationThreadId(item)
    if (!threadId) return
    setOpsBusyId(item.id)
    try {
      const nowIso = new Date().toISOString()
      const noReply = mode === 'no_reply_needed'
      const shouldClose = mode === 'no_reply_needed'
      await executeWorkspaceCommand(threadId, 'UpdateThreadWorkflow', {
        thread_meta: {
          ops: {
            mode,
            updated_at: nowIso,
          },
          no_reply_needed: noReply,
          sla_policy: {
            no_reply_needed: noReply,
            ...(noReply ? { snoozed_until: null } : {}),
          },
        },
      })
      if (mode === 'escalated') {
        await executeWorkspaceCommand(threadId, 'SetThreadPriority', { priority: 'high' })
      }
      if (shouldClose && !item.is_read) {
        await markNotificationsRead({ ids: [item.id] })
      }
      setItems((prev) =>
        prev.map((x) =>
          x.id === item.id
            ? { ...x, is_read: shouldClose ? true : x.is_read, read_at: shouldClose ? (x.read_at || nowIso) : x.read_at }
            : x,
        ),
      )
      setOpsModeOverrides((prev) => ({ ...prev, [item.id]: mode }))
      setThreadModesById((prev) => ({ ...prev, [threadId]: mode }))
    } catch {
      // keep incident visible, user can retry
    } finally {
      setOpsBusyId(null)
    }
  }

  const dateLocale = DATE_LOCALES[locale as keyof typeof DATE_LOCALES] || enUS

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          kind="browse"
          title={t('app.sla_incidents.title')}
          subtitle={
            <>
              <p>
                {t('app.sla_incidents.subtitle', {
                  defaultValue: 'Overdue communication dialogs that require a manager response.',
                })}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                <span className="badge bg-rose-100 px-3 py-1 font-medium text-rose-700">
                  {t('app.sla_incidents.unread')}: {unreadCount}
                </span>
                <span className="badge bg-slate-100 px-3 py-1 font-medium text-slate-700">
                  {t('app.sla_incidents.total')}: {items.length}
                </span>
              </div>
            </>
          }
          secondaryActions={
            <>
              <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
                {t('app.reminders.actions.refresh', { defaultValue: 'Refresh' })}
              </button>
              <button type="button" className="btn-secondary btn-sm" onClick={() => void markAllRead()} disabled={unreadCount <= 0}>
                {t('app.reminders.actions.mark_all', { defaultValue: 'Mark all read' })}
              </button>
            </>
          }
        />
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-slate-900">
            {t('app.sla_incidents.trust.title')}
          </h2>
          <span className="badge bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
            {t('app.sla_incidents.trust.window')}
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">{t('app.sla_incidents.trust.closed')}</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">{trustReport.closed}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">{t('app.sla_incidents.trust.open')}</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">{trustReport.open}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">{t('app.sla_incidents.trust.false_sla')}</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">{trustReport.potentialFalseSla}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">{t('app.sla_incidents.trust.duplicates')}</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">{trustReport.duplicateEvents}</div>
          </div>
        </div>
        <div className="mt-2 text-xs text-slate-500">
          {t('app.sla_incidents.trust.summary', {
            defaultValue:
              'Closure rate: {rate}% · Total: {total} · Duplicate groups: {groups}. Metrics are heuristic and based on payload signals.',
            rate: trustReport.closureRatePct,
            total: trustReport.total,
            groups: trustReport.duplicateGroups,
          })}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('app.sla_incidents.search')}
            className="h-10 min-w-[260px] flex-1 input"
          />
          <label className="inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={includeRead}
              onChange={(e) => setIncludeRead(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            {t('app.sla_incidents.include_read')}
          </label>
        </div>

        <div className="mb-3 flex flex-wrap items-center gap-2">
          {(['open', 'in_work', 'later', 'escalated', 'no_reply_needed', 'closed'] as IncidentGroup[]).map((group) => (
            <button
              key={group}
              type="button"
              onClick={() => setGroupFilter(group)}
              className={`btn-secondary btn-xs ${groupFilter === group ? 'border-brand-600 bg-brand-50 text-brand-800' : ''}`}
            >
              {t(`app.sla_incidents.groups.${group}`)}: {groupedCounts[group]}
            </button>
          ))}
        </div>

        {loadError && (
          <ErrorRecoveryBanner
            info={loadError}
            onRetry={() => void load()}
            retryLabel={t('common.actions.refresh')}
            {...friendlyErrorBannerSecondary(
              loadError,
              CRM_APP_PATHS.settingsCommunicationsSla,
              t('admin.communications_sla.title', { defaultValue: 'SLA settings' }),
            )}
            compact
          />
        )}

        {!loadError && filtered.length === 0 && !loading && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-8 text-center text-sm text-slate-500">
            {t('app.sla_incidents.empty_group', {
              defaultValue: 'No incidents in "{group}" group.',
              group: t(`app.sla_incidents.groups.${groupFilter}`),
            })}
          </div>
        )}

        <div className="space-y-2">
          {filtered.map((item) => {
            const payload = (item.payload || {}) as Record<string, any>
            const when = item.created_at
              ? formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: dateLocale })
              : '—'
            const resolvedMode = opsModeOverrides[item.id] || threadModesById[notificationThreadId(item)] || modeFromPayload(item)
            const group = groupOf(item, resolvedMode)
            return (
              <div
                key={item.id}
                className={`rounded-xl border px-3 py-3 ${item.is_read ? 'border-slate-200 bg-white opacity-80' : 'border-rose-200 bg-rose-50/30'}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-[280px] flex-1 space-y-1">
                    <div className="text-sm font-semibold text-slate-900">{String(payload.title || t('app.notifications.communications_sla_overdue_title', { defaultValue: 'SLA overdue: reply required in dialog' }))}</div>
                    <div className="text-sm text-slate-600">{String(payload.description || '—')}</div>
                    <div className="text-xs text-slate-500">
                      {String(payload.channel || '').toUpperCase()} · {when}
                      {payload.sla_due_at ? ` · due ${String(payload.sla_due_at)}` : ''}
                    </div>
                    <div className="text-xs">
                      <span className="badge bg-slate-100 text-slate-700">{t(`app.sla_incidents.groups.${group}`)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => void applyOpsMode(item, 'in_work')}
                      disabled={opsBusyId === item.id}
                    >
                      {t('app.sla_incidents.actions.in_work')}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => void applyOpsMode(item, 'later')}
                      disabled={opsBusyId === item.id}
                    >
                      {t('app.sla_incidents.actions.later')}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => void applyOpsMode(item, 'escalated')}
                      disabled={opsBusyId === item.id}
                    >
                      {t('app.sla_incidents.actions.escalated')}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => void applyOpsMode(item, 'no_reply_needed')}
                      disabled={opsBusyId === item.id}
                    >
                      {t('app.sla_incidents.actions.no_reply_needed')}
                    </button>
                    <button type="button" className="btn-secondary btn-sm" onClick={() => openThread(item)}>
                      {t('app.sla_incidents.open_dialog')}
                    </button>
                    {!item.is_read && (
                      <button type="button" className="btn-secondary btn-sm" onClick={() => void markOneRead(item)}>
                        {t('app.sla_incidents.mark_read')}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
      </div>
    </PageShell>
  )
}
