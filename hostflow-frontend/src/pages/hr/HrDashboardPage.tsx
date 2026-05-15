import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { fetchHrDashboardHighRisk, fetchHrDashboardSummary } from '../../api/hrWorkspace'
import { useI18n } from '../../i18n'

export default function HrDashboardPage() {
  const { t } = useI18n()
  const [summary, setSummary] = useState<any>(null)
  const [highRisk, setHighRisk] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const [s, h] = await Promise.all([
        fetchHrDashboardSummary({ assignee_scope: 'team' }),
        fetchHrDashboardHighRisk({ assignee_scope: 'team', horizon_days: 30, limit: 15, offset: 0 }),
      ])
      setSummary(s)
      setHighRisk(h)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const counts = summary?.counts

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-slate-900">
          {t('app.nav.hr.dashboard.heading', { defaultValue: 'Dashboard' })}
        </h2>
        <button
          type="button"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          onClick={() => void load()}
        >
          {t('common.actions.refresh', { defaultValue: 'Refresh' })}
        </button>
      </div>

      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>
      )}

      {counts && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['handoffs_pending', t('app.nav.hr.dashboard.counts.pending_handoffs', { defaultValue: 'Pending handoffs' })],
            ['handoffs_accepted', t('app.nav.hr.dashboard.counts.accepted_handoffs', { defaultValue: 'Accepted handoffs' })],
            ['hr_tasks_open', t('app.nav.hr.dashboard.counts.open_tasks', { defaultValue: 'Open HR tasks' })],
            ['documents_missing', t('app.nav.hr.dashboard.counts.missing_docs', { defaultValue: 'Missing documents' })],
            [
              'documents_high_risk_expiring',
              t('app.nav.hr.dashboard.counts.high_risk_expiring', { defaultValue: 'High-risk expiring' }),
            ],
          ].map(([key, label]) => (
            <div key={key} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{counts[key as keyof typeof counts] ?? '—'}</div>
            </div>
          ))}
        </div>
      )}

      {summary?.risk_summary && (
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.nav.hr.dashboard.risk_summary', { defaultValue: 'Risk summary' })}
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.nav.hr.dashboard.risk_total', {
              defaultValue: 'Total risk items: {{count}}',
              count: summary.risk_summary.total ?? 0,
            })}
          </p>
        </section>
      )}

      {highRisk?.items?.length > 0 && (
        <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('app.nav.hr.dashboard.high_risk_preview', { defaultValue: 'High-risk queue (preview)' })}
            </h3>
          </div>
          <ul className="divide-y divide-slate-100">
            {highRisk.items.map((row: any) => (
              <li key={`${row.risk_code}-${row.handoff_id}-${row.task_id}-${row.document_type}`} className="px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium text-slate-900">{row.reason}</div>
                    <div className="text-xs text-slate-500">
                      {row.risk_code} · {row.severity}
                      {row.handoff_id ? ` · handoff ${row.handoff_id}` : ''}
                    </div>
                  </div>
                  {row.handoff_id ? (
                    <Link
                      to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(row.handoff_id)}`}
                      className="text-sm font-medium text-brand-700 hover:text-brand-900"
                    >
                      {t('app.nav.hr.dashboard.open_handoff', { defaultValue: 'Open handoff' })}
                    </Link>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
