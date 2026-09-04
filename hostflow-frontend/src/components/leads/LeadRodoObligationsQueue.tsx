import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  exemptLeadRodoObligation,
  listLeadRodoObligationQueue,
  markLeadRodoSourceProvided,
  retryLeadRodoObligation,
  sendLeadRodoCompliance,
  type LeadRodoOpsQueueItem,
  type LeadRodoOpsQueueResponse,
  type LeadRodoOpsState,
} from '../../api/client'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'

const OPEN_STATES: Array<'' | LeadRodoOpsState> = [
  '',
  'delivery_required',
  'review_required',
  'delivery_failed',
]

const EXEMPT_CODES = [
  'art_14_5_a',
  'art_14_5_b',
  'art_14_5_c',
  'art_14_5_d',
  'already_has_information',
  'disproportionate_effort',
  'legal_secrecy',
  'legal_obligation',
] as const

function agingLabel(hours: number | null | undefined): string {
  if (hours == null || Number.isNaN(hours)) return '—'
  if (hours < 24) return `${Math.max(0, Math.round(hours))}h`
  return `${(hours / 24).toFixed(1)}d`
}

export default function LeadRodoObligationsQueue() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [stateFilter, setStateFilter] = useState<'' | LeadRodoOpsState>('')
  const [data, setData] = useState<LeadRodoOpsQueueResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [exemptFor, setExemptFor] = useState<string | null>(null)
  const [exemptCode, setExemptCode] = useState<string>('art_14_5_b')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listLeadRodoObligationQueue({
        state: stateFilter || undefined,
        limit: 50,
      })
      setData(res)
    } catch {
      setError(t('app.leads.compliance_ops.load_error'))
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [stateFilter, t])

  useEffect(() => {
    void load()
  }, [load])

  const runAction = async (item: LeadRodoOpsQueueItem, action: string) => {
    setBusyId(item.lead_id)
    try {
      if (action === 'retry') await retryLeadRodoObligation(item.lead_id)
      else if (action === 'send') await sendLeadRodoCompliance(item.lead_id)
      else if (action === 'covered_at_source') await markLeadRodoSourceProvided(item.lead_id)
      else if (action === 'exempt') {
        await exemptLeadRodoObligation(item.lead_id, { exemption_code: exemptCode })
        setExemptFor(null)
      }
      await load()
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      const message =
        typeof detail === 'string'
          ? detail
          : detail && typeof detail === 'object' && 'message' in detail
            ? String((detail as { message: string }).message)
            : t('app.leads.intake_workspace.decision_rail.rodo_send_failed')
      notify(message, 'error')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section className="mb-4 space-y-3 rounded-xl border border-amber-200 bg-amber-50/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{t('app.leads.compliance_ops.title')}</h2>
          <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-600">{t('app.leads.compliance_ops.hint')}</p>
          {data ? (
            <p className="mt-1 text-xs font-medium text-slate-700">
              {t('app.leads.compliance_ops.counts', {
                total: data.total,
                breached: data.sla_breached,
                escalated: data.escalated,
              })}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {OPEN_STATES.map((state) => {
            const active = stateFilter === state
            const label =
              state === ''
                ? t('app.leads.compliance_ops.filter_all')
                : t(`app.leads.compliance_ops.filter_${state}`)
            return (
              <button
                key={state || 'all'}
                type="button"
                className={
                  active
                    ? 'rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white'
                    : 'rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50'
                }
                aria-pressed={active}
                onClick={() => setStateFilter(state)}
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {loading ? <p className="text-sm text-slate-600">{t('common.loading')}</p> : null}
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      {!loading && !error && (data?.items.length ?? 0) === 0 ? (
        <p className="text-sm text-slate-600">{t('app.leads.compliance_ops.empty')}</p>
      ) : null}

      {(data?.items.length ?? 0) > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">{t('app.leads.compliance_ops.col_lead')}</th>
                <th className="px-3 py-2">{t('app.leads.compliance_ops.col_state')}</th>
                <th className="px-3 py-2">{t('app.leads.compliance_ops.col_article')}</th>
                <th className="px-3 py-2">{t('app.leads.compliance_ops.col_aging')}</th>
                <th className="px-3 py-2">{t('app.leads.compliance_ops.col_sla')}</th>
                <th className="px-3 py-2">{t('app.leads.compliance_ops.col_failure')}</th>
                <th className="px-3 py-2">{t('app.leads.compliance_ops.col_actions')}</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((item) => (
                <tr key={item.lead_id} className="border-t border-slate-100">
                  <td className="px-3 py-2">
                    <Link className="font-medium text-slate-900 underline-offset-2 hover:underline" to={`${CRM_APP_PATHS.leads}/${item.lead_id}`}>
                      {item.display_name || item.email || item.lead_id}
                    </Link>
                    {item.email ? <div className="text-xs text-slate-500">{item.email}</div> : null}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{item.compliance_state}</td>
                  <td className="px-3 py-2">{item.article || '—'}</td>
                  <td className="px-3 py-2 tabular-nums">{agingLabel(item.aging_hours)}</td>
                  <td className="px-3 py-2">
                    <span className={item.sla_breached ? 'font-semibold text-rose-700' : 'text-slate-600'}>
                      {item.sla_breached ? t('app.leads.compliance_ops.sla_breached') : t('app.leads.compliance_ops.sla_ok')}
                    </span>
                    {item.escalated ? (
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-rose-800">
                        {t('app.leads.compliance_ops.escalated')}
                      </div>
                    ) : null}
                  </td>
                  <td className="max-w-xs truncate px-3 py-2 text-xs text-slate-600" title={item.last_failure || ''}>
                    {item.last_failure || '—'}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {item.operator_actions.map((action) =>
                        action === 'exempt' ? (
                          <button
                            key={action}
                            type="button"
                            className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-800 disabled:opacity-50"
                            disabled={busyId === item.lead_id}
                            onClick={() => setExemptFor(item.lead_id)}
                          >
                            {t('app.leads.compliance_ops.exempt')}
                          </button>
                        ) : (
                          <button
                            key={action}
                            type="button"
                            className="rounded-md bg-slate-900 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50"
                            disabled={busyId === item.lead_id}
                            onClick={() => void runAction(item, action)}
                          >
                            {action === 'retry'
                              ? t('app.leads.compliance_ops.retry')
                              : action === 'send'
                                ? t('app.leads.compliance_ops.send')
                                : t('app.leads.compliance_ops.covered')}
                          </button>
                        ),
                      )}
                    </div>
                    {exemptFor === item.lead_id ? (
                      <div className="mt-2 flex flex-wrap items-center gap-1">
                        <label className="sr-only" htmlFor={`exempt-${item.lead_id}`}>
                          {t('app.leads.compliance_ops.exempt_code')}
                        </label>
                        <select
                          id={`exempt-${item.lead_id}`}
                          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
                          value={exemptCode}
                          onChange={(e) => setExemptCode(e.target.value)}
                        >
                          {EXEMPT_CODES.map((code) => (
                            <option key={code} value={code}>
                              {code}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className="rounded-md bg-slate-900 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50"
                          disabled={busyId === item.lead_id}
                          onClick={() => void runAction(item, 'exempt')}
                        >
                          {t('app.leads.compliance_ops.exempt')}
                        </button>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}
