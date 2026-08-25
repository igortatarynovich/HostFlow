import { useEffect, useMemo, useState } from 'react'
import {
  getCommunicationsSettings,
  listCommunicationCommandAudit,
  type CommunicationCommandAudit,
  type CommunicationCommandTemplate,
} from '../api/communications'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'

function formatDateTime(value?: string | null): string {
  if (!value) return '—'
  const ts = Date.parse(value)
  if (Number.isNaN(ts)) return String(value)
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(ts))
}

export default function CommunicationsCommandAuditPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [items, setItems] = useState<CommunicationCommandAudit[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [limit] = useState(50)
  const [templates, setTemplates] = useState<CommunicationCommandTemplate[]>([])

  const [channel, setChannel] = useState('')
  const [commandId, setCommandId] = useState('')
  const [threadId, setThreadId] = useState('')
  const [actorUserId, setActorUserId] = useState('')

  const canPrev = offset > 0
  const canNext = offset + limit < total

  const channels = useMemo(
    () => Array.from(new Set(items.map((x) => String(x.channel || '').trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b)),
    [items],
  )

  const load = async (nextOffset = offset) => {
    setLoading(true)
    setError(null)
    try {
      const [audit, settings] = await Promise.all([
        listCommunicationCommandAudit({
          limit,
          offset: nextOffset,
          channel: channel || undefined,
          command_id: commandId || undefined,
          thread_id: threadId.trim() || undefined,
          actor_user_id: actorUserId.trim() || undefined,
        }),
        getCommunicationsSettings().catch(() => null),
      ])
      setItems(Array.isArray(audit.items) ? audit.items : [])
      setTotal(Number(audit.total || 0))
      setOffset(nextOffset)
      const cmds = Array.isArray(settings?.commands?.items) ? settings!.commands.items : []
      setTemplates(cmds)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.command_audit.errors.load', { defaultValue: 'Failed to load command audit' }),
        )
      ) {
        setError(getFriendlyErrorInfo(err, t('app.communications.command_audit.errors.load', { defaultValue: 'Failed to load command audit' }), t))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load(0)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const applyFilters = () => void load(0)

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.nav.items.command_audit', { defaultValue: 'Command audit' })}
          subtitle={t('app.communications.command_audit.subtitle', {
            defaultValue: 'Execution log for workspace command templates.',
          })}
          kind="browse"
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void load(0)} disabled={loading}>
              {t('common.actions.refresh', { defaultValue: 'Refresh' })}
            </button>
          }
        />
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="grid gap-3 md:grid-cols-5">
          <label className="space-y-1">
            <span className="text-xs font-medium text-slate-600">{t('app.communications.command_audit.filters.channel', { defaultValue: 'Channel' })}</span>
            <select value={channel} onChange={(e) => setChannel(e.target.value)} className="input">
              <option value="">{t('app.communications.command_audit.filters.all', { defaultValue: 'All' })}</option>
              {channels.map((ch) => <option key={ch} value={ch}>{ch}</option>)}
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium text-slate-600">{t('app.communications.command_audit.filters.command', { defaultValue: 'Command' })}</span>
            <select value={commandId} onChange={(e) => setCommandId(e.target.value)} className="input">
              <option value="">{t('app.communications.command_audit.filters.all', { defaultValue: 'All' })}</option>
              {templates.map((cmd) => <option key={cmd.id} value={cmd.id}>{cmd.label}</option>)}
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium text-slate-600">{t('app.communications.command_audit.filters.thread_id', { defaultValue: 'Thread ID' })}</span>
            <input value={threadId} onChange={(e) => setThreadId(e.target.value)} className="input" />
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium text-slate-600">{t('app.communications.command_audit.filters.actor_user_id', { defaultValue: 'Actor user ID' })}</span>
            <input value={actorUserId} onChange={(e) => setActorUserId(e.target.value)} className="input" />
          </label>
          <div className="flex items-end gap-2">
            <button type="button" onClick={applyFilters} className="btn-secondary">{t('app.communications.command_audit.actions.apply', { defaultValue: 'Apply' })}</button>
            <button
              type="button"
              onClick={() => {
                setChannel('')
                setCommandId('')
                setThreadId('')
                setActorUserId('')
                void load(0)
              }}
              className="btn-secondary"
            >
              {t('app.communications.command_audit.actions.reset', { defaultValue: 'Reset' })}
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 text-sm">
          <span className="font-semibold text-slate-900">
            {t('app.communications.command_audit.records', { defaultValue: 'Records: {count}', values: { count: total } })}
          </span>
          <div className="flex items-center gap-2">
            <button type="button" disabled={!canPrev || loading} onClick={() => void load(Math.max(0, offset - limit))} className="btn-secondary btn-xs disabled:opacity-50">
              {t('app.communications.command_audit.pagination.prev', { defaultValue: 'Prev' })}
            </button>
            <button type="button" disabled={!canNext || loading} onClick={() => void load(offset + limit)} className="btn-secondary btn-xs disabled:opacity-50">
              {t('app.communications.command_audit.pagination.next', { defaultValue: 'Next' })}
            </button>
          </div>
        </div>
        {loading && <div className="px-4 py-4 text-sm text-slate-500">{t('common.loading')}</div>}
        {error && (
          <div className="p-4">
            <ErrorRecoveryBanner
              info={error}
              onRetry={() => void load(offset)}
              retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
              {...friendlyErrorBannerSecondary(
                error,
                CRM_APP_PATHS.settingsCommunications,
                t('app.nav.items.settings_communications', { defaultValue: 'Communications settings' }),
              )}
              compact
            />
          </div>
        )}
        {!loading && !error && (
          <div className="max-h-[70vh] overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left">{t('app.communications.command_audit.columns.executed', { defaultValue: 'Executed' })}</th>
                  <th className="px-3 py-2 text-left">{t('app.communications.command_audit.columns.channel', { defaultValue: 'Channel' })}</th>
                  <th className="px-3 py-2 text-left">{t('app.communications.command_audit.columns.command', { defaultValue: 'Command' })}</th>
                  <th className="px-3 py-2 text-left">{t('app.communications.command_audit.columns.actor', { defaultValue: 'Actor' })}</th>
                  <th className="px-3 py-2 text-left">{t('app.communications.command_audit.columns.thread', { defaultValue: 'Thread' })}</th>
                  <th className="px-3 py-2 text-left">{t('app.communications.command_audit.columns.actions', { defaultValue: 'Actions' })}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-3 py-2">{formatDateTime(row.executed_at || row.created_at)}</td>
                    <td className="px-3 py-2">{row.channel}</td>
                    <td className="px-3 py-2">{row.command_label || row.command_id}</td>
                    <td className="px-3 py-2">{row.actor_user_id || '—'}</td>
                    <td className="px-3 py-2 font-mono text-xs">{row.thread_id}</td>
                    <td className="px-3 py-2">{row.action_count}</td>
                  </tr>
                ))}
                {!items.length && (
                  <tr>
                    <td className="px-3 py-6 text-slate-500" colSpan={6}>{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
    </PageShell>
  )
}
