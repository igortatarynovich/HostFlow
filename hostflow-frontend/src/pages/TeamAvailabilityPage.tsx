import { useEffect, useMemo, useState } from 'react'
import { getCommunicationsSettings, listCommunicationTimeOffRequests, type CommunicationTimeOffRequest } from '../api/communications'
import { listManagers } from '../api/client'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useI18n } from '../i18n'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../utils/friendlyError'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function intersectsToday(row: CommunicationTimeOffRequest, dayIso: string): boolean {
  const status = String(row.status || '').toLowerCase()
  if (status !== 'approved') return false
  return String(row.start_date || '') <= dayIso && String(row.end_date || '') >= dayIso
}

function formatTimeOffLabel(row: CommunicationTimeOffRequest): string {
  const partial = row.partial_day ? ` · ${row.partial_day}` : ''
  const tw = row.payload?.time_window?.from && row.payload?.time_window?.to ? ` · ${row.payload.time_window.from}-${row.payload.time_window.to}` : ''
  return `${row.request_type} · ${row.start_date} → ${row.end_date}${partial}${tw}`
}

export default function TeamAvailabilityPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [items, setItems] = useState<any[]>([])
  const [labels, setLabels] = useState<Map<string, string>>(new Map())
  const [approvedTimeOff, setApprovedTimeOff] = useState<CommunicationTimeOffRequest[]>([])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const [cfg, managers] = await Promise.all([
          getCommunicationsSettings(),
          listManagers().catch(() => []),
        ])
        const timeOffRes = await listCommunicationTimeOffRequests({
          limit: 200,
          status_filter: ['approved'],
        }).catch(() => ({ items: [] as CommunicationTimeOffRequest[] }))
        if (!mounted) return
        setItems(cfg.managerQueue.items || [])
        setLabels(new Map((Array.isArray(managers) ? managers : []).map((m: any) => [String(m.id), String(m.label || m.full_name || m.email || m.id)])))
        setApprovedTimeOff(Array.isArray(timeOffRes.items) ? timeOffRes.items : [])
      } catch (err: any) {
        if (
          mounted &&
          planLimitModal?.showPlanLimitIfNeeded(
            err,
            t('app.communications.team_availability.errors.load', { defaultValue: 'Failed to load team availability' }),
          )
        ) {
          return
        }
        if (mounted) {
          setError(
            getFriendlyErrorInfo(
              err,
              t('app.communications.team_availability.errors.load', { defaultValue: 'Failed to load team availability' }),
              t,
            ),
          )
        }
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [planLimitModal, t])

  const today = todayIso()
  const activeTimeOffByUser = useMemo(() => {
    const map = new Map<string, CommunicationTimeOffRequest[]>()
    for (const row of approvedTimeOff) {
      if (!intersectsToday(row, today)) continue
      const key = String(row.requester_user_id || '')
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(row)
    }
    return map
  }, [approvedTimeOff, today])

  const upcomingTimeOff = useMemo(() => {
    return approvedTimeOff
      .filter((x) => String(x.end_date || '') >= today)
      .sort((a, b) => {
        const ak = `${a.start_date}|${a.requester_user_id}`
        const bk = `${b.start_date}|${b.requester_user_id}`
        return ak.localeCompare(bk)
      })
      .slice(0, 20)
  }, [approvedTimeOff, today])

  const summary = useMemo(() => ({
    total: items.length,
    available: items.filter((x) => x?.enabled && x?.availability?.state === 'available').length,
    busy: items.filter((x) => x?.enabled && ['busy', 'meeting', 'break'].includes(String(x?.availability?.state || ''))).length,
    onTimeOffToday: items.filter((x) => activeTimeOffByUser.has(String(x?.managerId || ''))).length,
  }), [activeTimeOffByUser, items])

  return (
    <div className="space-y-4">
      <WorkspaceTopNav active="calendar" />
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.communications.ia.team_availability_title', { defaultValue: 'Team Availability' })}</h1>
        <p className="text-sm text-slate-500">
          {t('app.communications.ia.team_availability_subtitle', { defaultValue: 'Supervisor/Admin view: manager schedules, occupancy, availability states, and queue readiness.' })}
        </p>
      </div>
      <div className="grid grid-cols-4 gap-3">
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{t('app.communications.team_availability.stats.available', { defaultValue: 'Available: {count}', values: { count: summary.available } })}</div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{t('app.communications.team_availability.stats.busy', { defaultValue: 'Busy: {count}', values: { count: summary.busy } })}</div>
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{t('app.communications.team_availability.stats.timeoff_today', { defaultValue: 'Time-off today: {count}', values: { count: summary.onTimeOffToday } })}</div>
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">{t('app.communications.team_availability.stats.total', { defaultValue: 'Total: {count}', values: { count: summary.total } })}</div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
            {t('app.communications.team_availability.timeoff_today', { defaultValue: 'Approved time-off active today' })}
          </div>
          <div className="divide-y divide-slate-100">
            {items
              .filter((item) => activeTimeOffByUser.has(String(item?.managerId || '')))
              .map((item) => {
                const managerId = String(item.managerId || '')
                const rows = activeTimeOffByUser.get(managerId) || []
                return (
                  <div key={`today:${managerId}`} className="px-4 py-3 text-sm">
                    <div className="font-medium text-slate-900">{labels.get(managerId) || managerId}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      state={String(item?.availability?.state || 'offline')} · note={String(item?.availability?.note || '—')}
                    </div>
                    <div className="mt-2 space-y-1">
                      {rows.map((row) => (
                        <div key={row.id} className="rounded border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-800">
                          {formatTimeOffLabel(row)}
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            {!items.some((item) => activeTimeOffByUser.has(String(item?.managerId || ''))) && (
              <div className="px-4 py-6 text-sm text-slate-500">{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</div>
            )}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
            {t('app.communications.team_availability.upcoming_timeoff', { defaultValue: 'Upcoming approved time-off' })}
          </div>
          <div className="divide-y divide-slate-100">
            {upcomingTimeOff.map((row) => (
              <div key={row.id} className="px-4 py-3 text-sm">
                <div className="font-medium text-slate-900">{labels.get(String(row.requester_user_id)) || row.requester_label || row.requester_user_id}</div>
                <div className="mt-1 text-xs text-slate-500">{formatTimeOffLabel(row)}</div>
                {row.reason && <div className="mt-1 text-xs text-slate-600 line-clamp-2">{row.reason}</div>}
              </div>
            ))}
            {!upcomingTimeOff.length && <div className="px-4 py-6 text-sm text-slate-500">{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</div>}
          </div>
        </div>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white">
        {loading && <div className="px-4 py-4 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>}
        {error && (
          <div className="px-4 py-4">
            <ErrorRecoveryBanner
              info={error}
              onRetry={() => window.location.reload()}
              retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
              {...friendlyErrorBannerSecondary(
                error,
                CRM_APP_PATHS.calendar,
                t('app.nav.items.calendar', { defaultValue: 'Calendar' }),
              )}
              compact
            />
          </div>
        )}
        {!loading && !error && (
          <div className="divide-y divide-slate-100">
            {items.map((item) => (
              <div key={String(item.managerId)} className="px-4 py-3 text-sm">
                <div className="font-medium text-slate-900">{labels.get(String(item.managerId)) || String(item.managerId)}</div>
                <div className="mt-1 text-xs text-slate-500">
                  state={String(item?.availability?.state || 'offline')} · load={Number(item?.availability?.currentLoad || 0)} · chats={Number(item?.availability?.maxConcurrentChats || 0)} · calls={Number(item?.availability?.maxConcurrentCalls || 0)}
                </div>
                {activeTimeOffByUser.has(String(item.managerId)) && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(activeTimeOffByUser.get(String(item.managerId)) || []).map((row) => (
                      <span key={row.id} className="inline-flex rounded-md bg-rose-100 px-2 py-0.5 text-xs text-rose-700">
                        {row.request_type}{row.partial_day ? ` (${row.partial_day})` : ''}{row.payload?.time_window?.from && row.payload?.time_window?.to ? ` ${row.payload.time_window.from}-${row.payload.time_window.to}` : ''}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {!items.length && <div className="px-4 py-6 text-sm text-slate-500">{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</div>}
          </div>
        )}
      </div>
    </div>
  )
}
