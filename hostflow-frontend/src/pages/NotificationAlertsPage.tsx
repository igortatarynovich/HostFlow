import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { enUS, pl as plLocale, ru as ruLocale } from 'date-fns/locale'
import {
  getNotificationEvent,
  listNotificationEvents,
  patchNotificationEventStatus,
  syncDocumentExpiryNotificationEvents,
} from '../api/notificationEvents'
import type { NotificationEventOut } from '../api/types/notificationEvent'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar } from '../components/layout'
import { StatusBadge } from '../components/ui/StatusBadge'
import { useToast } from '../components/Toast'
import { useI18n } from '../i18n'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import {
  filterNotificationEventsByEventType,
  notificationEventDocumentLabel,
  notificationEventExpiresOn,
  notificationEventOwnerLabel,
  notificationEventSortTs,
} from '../utils/notificationEventPresentation'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'

const DATE_LOCALES = { en: enUS, ru: ruLocale, pl: plLocale }

type EventTypeFilter = 'all' | 'document_expired' | 'document_expiring_soon'
type StatusFilter = 'open' | 'resolved' | 'ignored'

function ownerOpenPath(event: NotificationEventOut): string | null {
  const ownerType = String(event.owner_type || '').toLowerCase()
  const ownerId = String(event.owner_id || '').trim()
  if (!ownerId) return null
  if (ownerType === 'candidate') return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(ownerId)}`
  return null
}

export default function NotificationAlertsPage() {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<FriendlyErrorInfo | null>(null)
  const [items, setItems] = useState<NotificationEventOut[]>([])
  const [selected, setSelected] = useState<NotificationEventOut | null>(null)
  const [statusBusy, setStatusBusy] = useState(false)
  const [syncBusy, setSyncBusy] = useState(false)
  const [lastSyncSummary, setLastSyncSummary] = useState<string | null>(null)

  const statusFilter = (searchParams.get('status') || 'open') as StatusFilter
  const eventTypeFilter = (searchParams.get('event_type') || 'all') as EventTypeFilter
  const sourceLayerFilter = searchParams.get('source_layer') || 'document_expiry_notifications'
  const selectedId = searchParams.get('event_id') || ''

  const setFilters = useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams)
      Object.entries(patch).forEach(([key, value]) => {
        if (value == null || value === '') next.delete(key)
        else next.set(key, value)
      })
      setSearchParams(next, { replace: true })
    },
    [searchParams, setSearchParams],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const rows = await listNotificationEvents({
        status: statusFilter,
        source_layer: sourceLayerFilter || undefined,
      })
      const sorted = [...rows].sort((a, b) => notificationEventSortTs(b) - notificationEventSortTs(a))
      setItems(sorted)

      if (selectedId) {
        const fromList = sorted.find((row) => row.id === selectedId)
        if (fromList) {
          setSelected(fromList)
        } else {
          try {
            setSelected(await getNotificationEvent(selectedId))
          } catch {
            setSelected(null)
          }
        }
      } else {
        setSelected(null)
      }
    } catch (err: unknown) {
      setLoadError(
        getFriendlyErrorInfo(err, t('app.notification_alerts.errors.load'), t),
      )
    } finally {
      setLoading(false)
    }
  }, [selectedId, sourceLayerFilter, statusFilter, t])

  useEffect(() => {
    void load()
  }, [load])

  const filteredItems = useMemo(
    () => filterNotificationEventsByEventType(items, eventTypeFilter),
    [eventTypeFilter, items],
  )

  const selectEvent = useCallback(
    (event: NotificationEventOut) => {
      setSelected(event)
      setFilters({ event_id: event.id })
    },
    [setFilters],
  )

  const clearSelection = useCallback(() => {
    setSelected(null)
    setFilters({ event_id: null })
  }, [setFilters])

  const updateStatus = useCallback(
    async (status: 'resolved' | 'ignored') => {
      if (!selected) return
      setStatusBusy(true)
      try {
        const updated = await patchNotificationEventStatus(selected.id, status)
        notify({
          title:
            status === 'resolved'
              ? t('app.notification_alerts.toast.resolved')
              : t('app.notification_alerts.toast.ignored'),
          variant: 'success',
        })
        if (statusFilter === 'open') {
          clearSelection()
        } else {
          setSelected(updated)
        }
        await load()
      } catch (err: unknown) {
        notify({
          title: getFriendlyErrorInfo(err, t('app.notification_alerts.errors.status'), t).title,
          variant: 'error',
        })
      } finally {
        setStatusBusy(false)
      }
    },
    [clearSelection, load, notify, selected, statusFilter, t],
  )

  const runSync = useCallback(async () => {
    setSyncBusy(true)
    setLastSyncSummary(null)
    try {
      const summary = await syncDocumentExpiryNotificationEvents()
      setLastSyncSummary(
        t('app.notification_alerts.sync.summary', {
          created: summary.created,
          updated: summary.updated,
          skipped: summary.skipped,
        }),
      )
      notify({
        title: t('app.notification_alerts.sync.success'),
        variant: 'success',
      })
      await load()
    } catch (err: unknown) {
      notify({
        title: getFriendlyErrorInfo(err, t('app.notification_alerts.errors.sync'), t).title,
        variant: 'error',
      })
    } finally {
      setSyncBusy(false)
    }
  }, [load, notify, t])

  const dateLocale = DATE_LOCALES[locale as keyof typeof DATE_LOCALES] || enUS

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          breadcrumbItems={[
            { label: t('app.nav.items.tasks'), to: CRM_APP_PATHS.tasks },
            { label: t('app.notification_alerts.title') },
          ]}
          title={t('app.notification_alerts.title')}
          subtitle={t('app.notification_alerts.subtitle')}
          kind="action"
          primaryAction={
            <button
              type="button"
              className="btn-primary btn-sm"
              onClick={() => void runSync()}
              disabled={syncBusy || loading}
            >
              {syncBusy ? t('common.saving') : t('app.notification_alerts.actions.sync_now')}
            </button>
          }
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
              {t('common.actions.refresh')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
      {lastSyncSummary ? (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          {lastSyncSummary}
        </div>
      ) : null}

      {loadError ? (
        <ErrorRecoveryBanner info={loadError} onRetry={() => void load()} />
      ) : null}

      <Toolbar>
        <div className="flex flex-wrap gap-3">
          <label className="flex min-w-[140px] flex-col gap-1 text-xs text-slate-600">
            {t('common.labels.status')}
            <select
              className="input"
              value={statusFilter}
              onChange={(e) => setFilters({ status: e.target.value, event_id: null })}
            >
              <option value="open">{t('app.notification_alerts.filters.status.open')}</option>
              <option value="resolved">{t('app.notification_alerts.filters.status.resolved')}</option>
              <option value="ignored">{t('app.notification_alerts.filters.status.ignored')}</option>
            </select>
          </label>

          <label className="flex min-w-[180px] flex-col gap-1 text-xs text-slate-600">
            {t('app.notification_alerts.filters.event_type')}
            <select
              className="input"
              value={eventTypeFilter}
              onChange={(e) => setFilters({ event_type: e.target.value, event_id: null })}
            >
              <option value="all">{t('app.notification_alerts.filters.event_type_all')}</option>
              <option value="document_expired">{t('app.notification_alerts.filters.event_type_expired')}</option>
              <option value="document_expiring_soon">
                {t('app.notification_alerts.filters.event_type_expiring_soon')}
              </option>
            </select>
          </label>

          <label className="flex min-w-[220px] flex-col gap-1 text-xs text-slate-600">
            {t('app.notification_alerts.filters.source_layer')}
            <select
              className="input"
              value={sourceLayerFilter}
              onChange={(e) => setFilters({ source_layer: e.target.value, event_id: null })}
            >
              <option value="document_expiry_notifications">
                {t('app.notification_alerts.filters.source_document_expiry')}
              </option>
              <option value="">{t('app.notification_alerts.filters.source_all')}</option>
            </select>
          </label>
        </div>
      </Toolbar>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <section className="card overflow-hidden">
          <div className="border-b border-slate-200 px-4 py-3 text-sm font-medium text-slate-800">
            {t('app.notification_alerts.list_title', { count: filteredItems.length })}
          </div>
          {loading && !filteredItems.length ? (
            <div className="p-4 text-sm text-slate-500">{t('common.loading')}</div>
          ) : null}
          {!loading && !filteredItems.length ? (
            <div className="p-6 text-sm text-slate-500">{t('app.notification_alerts.empty')}</div>
          ) : null}
          <ul className="divide-y divide-slate-100">
            {filteredItems.map((event) => {
              const isActive = selected?.id === event.id
              const expiresOn = notificationEventExpiresOn(event)
              return (
                <li key={event.id}>
                  <button
                    type="button"
                    className={`w-full px-4 py-3 text-left transition hover:bg-slate-50 ${isActive ? 'bg-brand-50/70' : ''}`}
                    onClick={() => selectEvent(event)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-slate-900">
                          {t(`app.notification_alerts.event_code.${event.event_code}`, {
                            defaultValue: event.event_code,
                          })}
                        </div>
                        <div className="mt-1 text-sm text-slate-600">
                          {notificationEventDocumentLabel(event)} · {notificationEventOwnerLabel(event)}
                        </div>
                        {expiresOn ? (
                          <div className="mt-1 text-xs text-slate-500">
                            {t('app.notification_alerts.expires_on', { date: expiresOn })}
                          </div>
                        ) : null}
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <StatusBadge
                          semantic={event.severity === 'critical' ? 'danger' : 'warning'}
                          label={t(`app.notification_alerts.severity.${event.severity}`, {
                            defaultValue: event.severity,
                          })}
                        />
                        {event.evaluated_at ? (
                          <span className="text-xs text-slate-400">
                            {formatDistanceToNow(new Date(event.evaluated_at), {
                              addSuffix: true,
                              locale: dateLocale,
                            })}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        </section>

        <section className="card p-4">
          {!selected ? (
            <div className="text-sm text-slate-500">{t('app.notification_alerts.detail_empty')}</div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">
                    {t(`app.notification_alerts.event_code.${selected.event_code}`, {
                      defaultValue: selected.event_code,
                    })}
                  </h2>
                  <p className="mt-1 text-sm text-slate-600">{selected.event_key}</p>
                </div>
                <StatusBadge
                  semantic={selected.severity === 'critical' ? 'danger' : 'warning'}
                  label={t(`app.notification_alerts.severity.${selected.severity}`, {
                    defaultValue: selected.severity,
                  })}
                />
              </div>

              <dl className="grid gap-3 text-sm">
                <div>
                  <dt className="text-slate-500">{t('app.notification_alerts.detail.document_type')}</dt>
                  <dd className="font-medium text-slate-900">{notificationEventDocumentLabel(selected)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t('app.notification_alerts.detail.owner')}</dt>
                  <dd className="font-medium text-slate-900">{notificationEventOwnerLabel(selected)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t('app.notification_alerts.detail.expires_on')}</dt>
                  <dd className="font-medium text-slate-900">
                    {notificationEventExpiresOn(selected) || t('common.labels.not_available')}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t('app.notification_alerts.detail.source_layer')}</dt>
                  <dd className="font-medium text-slate-900">{selected.source_layer}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t('common.labels.status')}</dt>
                  <dd className="font-medium text-slate-900">{selected.status}</dd>
                </div>
              </dl>

              <div className="flex flex-wrap gap-2">
                {ownerOpenPath(selected) ? (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => navigate(ownerOpenPath(selected)!)}
                  >
                    {t('app.notification_alerts.actions.open_owner')}
                  </button>
                ) : null}
                {selected.status === 'open' ? (
                  <>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={statusBusy}
                      onClick={() => void updateStatus('resolved')}
                    >
                      {t('app.notification_alerts.actions.mark_resolved')}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={statusBusy}
                      onClick={() => void updateStatus('ignored')}
                    >
                      {t('app.notification_alerts.actions.mark_ignored')}
                    </button>
                  </>
                ) : null}
              </div>
            </div>
          )}
        </section>
      </div>
      </div>
    </PageShell>
  )
}
