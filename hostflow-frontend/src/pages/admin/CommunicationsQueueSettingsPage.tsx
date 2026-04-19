import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getCommunicationsSettings,
  patchCommunicationsSettings,
  previewCommunicationAllocation,
  listCommunicationAllocatorAudit,
  getCommunicationSchedulerStatus,
  runCommunicationSchedulerNow,
  type CommunicationAllocationAudit,
  type CommunicationSchedulerStatus,
  type QueueStrategy,
} from '../../api/communications'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'

export default function CommunicationsQueueSettingsPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [saveNotice, setSaveNotice] = useState<string | null>(null)
  const [saveBusy, setSaveBusy] = useState(false)
  const [settings, setSettings] = useState<any | null>(null)

  const [allocatorTestChannel, setAllocatorTestChannel] = useState<string>('email')
  const [allocatorTestAt, setAllocatorTestAt] = useState<string>('')
  const [allocatorPreviewBusy, setAllocatorPreviewBusy] = useState(false)
  const [allocatorPreview, setAllocatorPreview] = useState<any | null>(null)
  const [allocatorAudit, setAllocatorAudit] = useState<CommunicationAllocationAudit[]>([])
  const [schedulerStatus, setSchedulerStatus] = useState<CommunicationSchedulerStatus | null>(null)
  const [schedulerBusy, setSchedulerBusy] = useState<'refresh' | 'run' | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const [cfg, sched, audit] = await Promise.all([
          getCommunicationsSettings(),
          getCommunicationSchedulerStatus().catch(() => null),
          listCommunicationAllocatorAudit({ limit: 20 }).catch(() => ({ items: [] as CommunicationAllocationAudit[] })),
        ])
        if (mounted) {
          setSettings(cfg)
          setSchedulerStatus(sched)
          setAllocatorAudit(Array.isArray(audit?.items) ? audit.items : [])
        }
      } catch (err: any) {
        if (mounted) {
          if (
            !planLimitModal?.showPlanLimitIfNeeded(
              err,
              t('admin.communications_queue.errors.load_failed', { defaultValue: 'Failed to load queue settings' }),
            )
          ) {
            setError(
              getFriendlyErrorInfo(
                err,
                t('admin.communications_queue.errors.load_failed', { defaultValue: 'Failed to load queue settings' }),
                t,
              ),
            )
          }
        }
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [planLimitModal, t])

  const queue = settings?.managerQueue || null
  const sla = settings?.sla || null

  const saveQueueSettings = useCallback(async (nextQueue: any) => {
    setSaveBusy(true)
    setSaveNotice(null)
    setError(null)
    try {
      const patched = await patchCommunicationsSettings({ managerQueue: nextQueue })
      setSettings(patched)
      setSaveNotice(t('common.saved', { defaultValue: 'Saved' }))
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.communications_queue.errors.save_failed', { defaultValue: 'Failed to save queue settings' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('admin.communications_queue.errors.save_failed', { defaultValue: 'Failed to save queue settings' }),
            t,
          ),
        )
      }
    } finally {
      setSaveBusy(false)
    }
  }, [planLimitModal, t])

  const patchQueue = useCallback((partial: Record<string, any>) => {
    if (!queue) return
    void saveQueueSettings({ ...queue, ...partial })
  }, [queue, saveQueueSettings])

  const runAllocatorPreview = useCallback(async () => {
    setAllocatorPreviewBusy(true)
    setError(null)
    try {
      const result = await previewCommunicationAllocation({
        channel: allocatorTestChannel,
        at: allocatorTestAt ? new Date(allocatorTestAt).toISOString() : undefined,
      })
      setAllocatorPreview(result)
      const audit = await listCommunicationAllocatorAudit({ limit: 20 }).catch(() => ({ items: [] as CommunicationAllocationAudit[] }))
      setAllocatorAudit(Array.isArray(audit?.items) ? audit.items : [])
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.communications_queue.errors.preview_failed', { defaultValue: 'Allocator preview failed' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('admin.communications_queue.errors.preview_failed', { defaultValue: 'Allocator preview failed' }),
            t,
          ),
        )
      }
    } finally {
      setAllocatorPreviewBusy(false)
    }
  }, [allocatorTestAt, allocatorTestChannel, planLimitModal, t])

  const handleSchedulerAction = useCallback(async (mode: 'refresh' | 'run') => {
    setSchedulerBusy(mode)
    setError(null)
    try {
      if (mode === 'run') {
        const resp = await runCommunicationSchedulerNow()
        setSchedulerStatus(resp.status)
      } else {
        const resp = await getCommunicationSchedulerStatus()
        setSchedulerStatus(resp)
      }
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.communications_queue.errors.scheduler_action_failed', { defaultValue: 'Scheduler action failed' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('admin.communications_queue.errors.scheduler_action_failed', { defaultValue: 'Scheduler action failed' }),
            t,
          ),
        )
      }
    } finally {
      setSchedulerBusy(null)
    }
  }, [planLimitModal, t])

  return (
    <div className="space-y-4">
      <SettingsSubpageHeader
        backHref={CRM_APP_PATHS.settingsCommunications}
        backLabel={t('admin.communications_queue.actions.all_settings', { defaultValue: 'All communication settings' })}
        kicker={t('admin.communications_queue.header_kicker')}
        title={t('admin.communications_queue.title', { defaultValue: 'Queue settings' })}
        subtitle={t('admin.communications_queue.subtitle', {
          defaultValue: 'Manager allocation strategy, queue flags and diagnostics.',
        })}
        actions={
          <Link to={CRM_APP_PATHS.messages} className="btn-secondary">
            {t('admin.communications_queue.actions.open_messages', { defaultValue: 'Open messages' })}
          </Link>
        }
      />

      {loading && <div className="text-sm text-slate-500">{t('common.loading')}</div>}
      {error && (
        <ErrorRecoveryBanner
          info={error}
          onRetry={() => window.location.reload()}
          retryLabel={t('common.actions.refresh')}
          {...friendlyErrorBannerSecondary(
            error,
            CRM_APP_PATHS.settingsCommunications,
            t('admin.communications_sla.actions.all', { defaultValue: 'All communication settings' }),
          )}
          compact
        />
      )}
      {saveNotice && <div className="alert-success">{saveNotice}</div>}

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">
          {t('admin.communications_queue.sections.queue_allocation', { defaultValue: 'Queue & allocation' })}
        </h2>
        {queue ? (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1">
                <span className="text-xs font-medium text-slate-600">{t('app.communications.queue.strategy', { defaultValue: 'Strategy' })}</span>
                <select
                  value={queue.strategy || 'round_robin'}
                  onChange={(e) => patchQueue({ strategy: e.target.value as QueueStrategy })}
                  disabled={saveBusy}
                  className="input"
                >
                  <option value="manual">{t('admin.communications_queue.strategy_options.manual', { defaultValue: 'manual' })}</option>
                  <option value="round_robin">{t('admin.communications_queue.strategy_options.round_robin', { defaultValue: 'round_robin' })}</option>
                  <option value="weighted_round_robin">{t('admin.communications_queue.strategy_options.weighted_round_robin', { defaultValue: 'weighted_round_robin' })}</option>
                  <option value="least_busy">{t('admin.communications_queue.strategy_options.least_busy', { defaultValue: 'least_busy' })}</option>
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-medium text-slate-600">{t('app.communications.queue.items_count', { defaultValue: 'Managers in queue' })}</span>
                <div className="rounded border border-slate-200 px-3 py-2 text-slate-700">
                  {Array.isArray(queue.items) ? queue.items.length : 0}
                </div>
              </label>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {[
                ['enabled', t('common.enabled', { defaultValue: 'Enabled' })],
                ['respectSchedules', t('app.communications.queue.respect_schedules', { defaultValue: 'Respect schedules' })],
                ['respectAvailability', t('app.communications.queue.respect_availability', { defaultValue: 'Respect availability' })],
                ['fallbackToManual', t('app.communications.queue.fallback_to_manual', { defaultValue: 'Fallback to manual' })],
                ['rebalanceOnStatusChange', t('app.communications.queue.rebalance_status', { defaultValue: 'Rebalance on status change' })],
              ].map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 rounded border border-slate-200 px-3 py-2">
                  <input
                    type="checkbox"
                    checked={Boolean(queue[key])}
                    onChange={(e) => patchQueue({ [key]: e.target.checked })}
                    disabled={saveBusy}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-500">{t('common.loading')}</div>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">
          {t('admin.communications_queue.sections.sla_policy', { defaultValue: 'SLA escalation policy' })}
        </h2>
        {sla ? (
          <div className="space-y-3 text-sm">
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded border border-slate-200 px-3 py-2 text-slate-700">
                {t('common.enabled', { defaultValue: 'Enabled' })}: <span className="font-medium">
                  {sla.enabled ? t('common.words.yes', { defaultValue: 'yes' }) : t('common.words.no', { defaultValue: 'no' })}
                </span>
              </div>
              <div className="rounded border border-slate-200 px-3 py-2 text-slate-700">
                {t('admin.communications_queue.labels.recipient_mode', { defaultValue: 'Recipient mode' })}:{' '}
                <span className="font-medium">{String(sla.recipientMode || 'assignee_or_owner')}</span>
              </div>
              <div className="rounded border border-slate-200 px-3 py-2 text-slate-700">
                {t('admin.communications_queue.labels.in_app_notifications', { defaultValue: 'In-app notifications' })}:{' '}
                <span className="font-medium">
                  {sla.createNotifications ? t('admin.communications_queue.states.on', { defaultValue: 'on' }) : t('admin.communications_queue.states.off', { defaultValue: 'off' })}
                </span>
              </div>
              <div className="rounded border border-slate-200 px-3 py-2 text-slate-700">
                {t('admin.communications_queue.labels.reminder_tasks', { defaultValue: 'Reminder tasks' })}:{' '}
                <span className="font-medium">
                  {sla.createReminders ? t('admin.communications_queue.states.on', { defaultValue: 'on' }) : t('admin.communications_queue.states.off', { defaultValue: 'off' })}
                </span>
              </div>
            </div>
            <div>
              <Link to={CRM_APP_PATHS.settingsCommunicationsSla} className="btn-secondary">
                {t('admin.communications_settings.open_sla', { defaultValue: 'Open SLA settings' })}
              </Link>
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-500">{t('common.loading')}</div>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('admin.communications_queue.sections.preview', { defaultValue: 'Queue preview (dry-run)' })}
          </h2>
          <button
            type="button"
            onClick={() => void runAllocatorPreview()}
            disabled={allocatorPreviewBusy}
            className="btn-secondary btn-sm disabled:opacity-60"
          >
            {allocatorPreviewBusy
              ? t('common.loading')
              : t('admin.communications_queue.actions.run_preview', { defaultValue: 'Run preview' })}
          </button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="text-xs font-medium text-slate-600">{t('app.communications.labels.channel', { defaultValue: 'Channel' })}</span>
            <select value={allocatorTestChannel} onChange={(e) => setAllocatorTestChannel(e.target.value)} className="input">
              {['email', 'telegram', 'whatsapp', 'viber', 'messenger', 'instagram', 'sms'].map((c) => (
                <option key={c} value={c}>
                  {t(`admin.communications_queue.channels.${c}` as any, { defaultValue: c })}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-xs font-medium text-slate-600">{t('app.communications.labels.at_time', { defaultValue: 'At time (optional)' })}</span>
            <input
              type="datetime-local"
              value={allocatorTestAt}
              onChange={(e) => setAllocatorTestAt(e.target.value)}
              className="input"
            />
          </label>
        </div>
        {allocatorPreview && (
          <div className="mt-3 space-y-2 text-sm">
            <div className="rounded border border-slate-200 px-3 py-2">
              {t('app.communications.queue.preview_result', { defaultValue: 'Result' })}:{' '}
              {allocatorPreview.assigned
                ? t('admin.communications_queue.states.assigned', { defaultValue: 'assigned' })
                : t('admin.communications_queue.states.not_assigned', { defaultValue: 'not assigned' })}
              {' · '}
              {t('app.communications.queue.strategy', { defaultValue: 'Strategy' })}: {allocatorPreview.strategy || '—'}
              {' · '}
              {t('app.communications.queue.assignee', { defaultValue: 'Assignee' })}: {allocatorPreview.assignee_id || '—'}
              {' · '}
              {t('app.communications.labels.reason', { defaultValue: 'Reason' })}: {allocatorPreview.reason || '—'}
            </div>
          </div>
        )}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.communications_queue.sections.scheduler_status', { defaultValue: 'Scheduler status' })}
            </h2>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void handleSchedulerAction('refresh')}
                disabled={schedulerBusy !== null}
                className="btn-secondary btn-sm disabled:opacity-60"
              >
                {t('common.refresh', { defaultValue: 'Refresh' })}
              </button>
              <button
                type="button"
                onClick={() => void handleSchedulerAction('run')}
                disabled={schedulerBusy !== null}
                className="btn-primary btn-sm disabled:opacity-60"
              >
                {t('app.communications.scheduler.run_now', { defaultValue: 'Run now' })}
              </button>
            </div>
          </div>
          {schedulerStatus ? (
            <div className="space-y-2 text-sm">
              <div className="rounded border border-slate-200 px-3 py-2">
                {t('admin.communications_queue.labels.enabled', { defaultValue: 'enabled' })}={String(Boolean(schedulerStatus.enabled))}
                {' · '}
                {t('admin.communications_queue.labels.active', { defaultValue: 'active' })}={String(Boolean(schedulerStatus.active))}
                {' · '}
                {t('admin.communications_queue.labels.tick_seconds', { defaultValue: 'tick' })}={schedulerStatus.tick_seconds}s
              </div>
              <div className="rounded border border-slate-200 px-3 py-2 text-xs text-slate-600">
                {t('admin.communications_queue.labels.last_tick', { defaultValue: 'lastTick' })}: {schedulerStatus.last_tick_started_at || '—'} → {schedulerStatus.last_tick_finished_at || '—'} · {schedulerStatus.last_tick_duration_ms ?? '—'}ms
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</div>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.communications_queue.sections.allocator_audit', { defaultValue: 'Allocator audit (recent)' })}
            </h2>
            <button
              type="button"
              onClick={() =>
                void listCommunicationAllocatorAudit({ limit: 20 })
                  .then((r) => setAllocatorAudit(r.items || []))
                  .catch((e) => {
                    if (
                      !planLimitModal?.showPlanLimitIfNeeded(
                        e,
                        t('admin.communications_queue.errors.audit_reload_failed', {
                          defaultValue: 'Failed to reload allocator audit',
                        }),
                      )
                    ) {
                      setError(
                        getFriendlyErrorInfo(
                          e,
                          t('admin.communications_queue.errors.audit_reload_failed', {
                            defaultValue: 'Failed to reload allocator audit',
                          }),
                          t,
                        ),
                      )
                    }
                  })
              }
              className="btn-secondary btn-sm"
            >
              {t('common.refresh', { defaultValue: 'Refresh' })}
            </button>
          </div>
          <div className="max-h-80 overflow-auto rounded border border-slate-200">
            <table className="min-w-full text-xs">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-2 py-1 text-left">{t('admin.communications_queue.table.at', { defaultValue: 'At' })}</th>
                  <th className="px-2 py-1 text-left">{t('admin.communications_queue.table.mode', { defaultValue: 'Mode' })}</th>
                  <th className="px-2 py-1 text-left">{t('admin.communications_queue.table.channel', { defaultValue: 'Channel' })}</th>
                  <th className="px-2 py-1 text-left">{t('admin.communications_queue.table.assigned', { defaultValue: 'Assigned' })}</th>
                  <th className="px-2 py-1 text-left">{t('admin.communications_queue.table.assignee', { defaultValue: 'Assignee' })}</th>
                </tr>
              </thead>
              <tbody>
                {allocatorAudit.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-2 py-1">{row.evaluated_at || row.created_at || '—'}</td>
                    <td className="px-2 py-1">{row.mode}</td>
                    <td className="px-2 py-1">{row.channel}</td>
                    <td className="px-2 py-1">{String(Boolean(row.assigned))}</td>
                    <td className="px-2 py-1">{row.assignee_id || '—'}</td>
                  </tr>
                ))}
                {!allocatorAudit.length && (
                  <tr>
                    <td className="px-2 py-3 text-slate-500" colSpan={5}>{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
