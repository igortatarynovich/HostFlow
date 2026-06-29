import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { fetchHrDashboardHighRisk, fetchHrDashboardSummary } from '../../api/hrWorkspace'
import { HrTransferSummaryChips, type HrTransferSummary } from '../../components/hr/HrTransferSummaryChips'
import { HrVerificationProgressBadge } from '../../components/hr/HrVerificationProgressBadge'
import { useI18n } from '../../i18n'
import { hrEmployeeVerificationPath, hrHandoffPath, hrRiskRowPrimaryHref } from '../../utils/hrEmployeeLinks'

type DashboardCounts = {
  handoffs_pending?: number
  handoffs_accepted?: number
  hr_tasks_open?: number
  documents_missing?: number
  documents_high_risk_expiring?: number
}

const KPI_LINKS: Record<keyof DashboardCounts, string> = {
  handoffs_pending: CRM_APP_PATHS.hrInbox,
  handoffs_accepted: CRM_APP_PATHS.hrInbox,
  hr_tasks_open: CRM_APP_PATHS.hrTasks,
  documents_missing: CRM_APP_PATHS.hrDocumentsMissing,
  documents_high_risk_expiring: CRM_APP_PATHS.hrDocumentsExpiring,
}

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

  const counts = summary?.counts as DashboardCounts | undefined
  const previews = summary?.previews

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-slate-900">
          {t('app.nav.hr.dashboard.heading', { defaultValue: 'Dashboard' })}
        </h2>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.hrInbox}>
            {t('app.nav.hr.dashboard.open_inbox', { defaultValue: 'HR inbox' })}
          </Link>
          <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.hrDocuments}>
            {t('app.nav.hr.dashboard.open_hub', { defaultValue: 'Documents hub' })}
          </Link>
          <button
            type="button"
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            onClick={() => void load()}
          >
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
      </div>

      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>
      )}

      {counts && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(
            [
              ['handoffs_pending', t('app.nav.hr.dashboard.counts.pending_handoffs', { defaultValue: 'Pending handoffs' })],
              ['handoffs_accepted', t('app.nav.hr.dashboard.counts.accepted_handoffs', { defaultValue: 'Accepted handoffs' })],
              ['hr_tasks_open', t('app.nav.hr.dashboard.counts.open_tasks', { defaultValue: 'Open HR tasks' })],
              ['documents_missing', t('app.nav.hr.dashboard.counts.missing_docs', { defaultValue: 'Missing documents' })],
              [
                'documents_high_risk_expiring',
                t('app.nav.hr.dashboard.counts.high_risk_expiring', { defaultValue: 'High-risk expiring' }),
              ],
            ] as const
          ).map(([key, label]) => (
            <Link
              key={key}
              to={KPI_LINKS[key]}
              className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-200 hover:bg-brand-50/40"
            >
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{counts[key] ?? '—'}</div>
            </Link>
          ))}
        </div>
      )}

      {summary?.risk_summary && (
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('app.nav.hr.dashboard.risk_summary', { defaultValue: 'Risk summary' })}
            </h3>
            <Link className="text-sm font-medium text-brand-700 hover:underline" to={CRM_APP_PATHS.hrCompliance}>
              {t('app.nav.hr.dashboard.open_compliance', { defaultValue: 'Compliance queues' })}
            </Link>
          </div>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.nav.hr.dashboard.risk_total', {
              defaultValue: 'Total risk items: {{count}}',
              count: summary.risk_summary.total ?? 0,
            })}
          </p>
        </section>
      )}

      {Array.isArray(previews?.pending_handoffs) && previews.pending_handoffs.length > 0 ? (
        <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('app.nav.hr.dashboard.pending_preview', { defaultValue: 'Pending handoffs (preview)' })}
            </h3>
          </div>
          <ul className="divide-y divide-slate-100">
            {previews.pending_handoffs.map((row: any) => (
              <li key={row.handoff_id} className="px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm text-slate-700">
                    {t('app.nav.hr.dashboard.handoff_status', {
                      defaultValue: 'Handoff · {status}',
                      values: { status: String(row.status || 'pending') },
                    })}
                  </div>
                  {row.workforce_employee_id ? (
                    <Link className="text-sm font-medium text-brand-700 hover:underline" to={hrEmployeeVerificationPath(row.workforce_employee_id)}>
                      {t('app.hr.verify_task.open_verification', { defaultValue: 'Verify documents' })}
                    </Link>
                  ) : (
                    <Link className="text-sm font-medium text-brand-700 hover:underline" to={hrHandoffPath(row.handoff_id)}>
                      {t('app.nav.hr.dashboard.open_handoff', { defaultValue: 'Open handoff' })}
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {highRisk?.items?.length > 0 && (
        <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-4 py-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('app.nav.hr.dashboard.high_risk_preview', { defaultValue: 'High-risk queue (preview)' })}
            </h3>
            <Link className="text-sm font-medium text-brand-700 hover:underline" to={CRM_APP_PATHS.hrDocumentsVerification}>
              {t('app.hr.documents_hub.tab_verification', { defaultValue: 'Needs verification' })}
            </Link>
          </div>
          <ul className="divide-y divide-slate-100">
            {highRisk.items.map((row: any) => {
              const href = hrRiskRowPrimaryHref(row)
              const transfer = row.candidate_snapshot as HrTransferSummary | undefined
              return (
                <li key={`${row.risk_code}-${row.handoff_id}-${row.task_id}-${row.document_type}`} className="px-4 py-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-slate-900">{row.reason}</div>
                      <div className="mt-0.5 text-xs text-slate-500">
                        {row.risk_code} · {row.severity}
                        {row.document_type ? ` · ${row.document_type}` : ''}
                      </div>
                      <HrTransferSummaryChips className="mt-2" summary={transfer} />
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {href ? (
                        <Link className="text-sm font-medium text-brand-700 hover:underline" to={href}>
                          {row.workforce_employee_id
                            ? t('app.hr.verify_task.open_verification', { defaultValue: 'Verify documents' })
                            : t('app.nav.hr.dashboard.open_handoff', { defaultValue: 'Open handoff' })}
                        </Link>
                      ) : null}
                      {row.workforce_employee_id ? (
                        <HrVerificationProgressBadge hrReviewStatus="in_progress" />
                      ) : null}
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </div>
  )
}
