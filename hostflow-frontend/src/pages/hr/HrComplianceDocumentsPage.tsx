import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { fetchHrDocumentsExpiring, fetchHrDocumentsMissing, type HrDocumentQueueItem } from '../../api/hrWorkspace'
import { useI18n } from '../../i18n'
import { humanizeToken } from '../../components/hr/hrEmployeeUiFormat'

const empDocsHash = (id: string) => `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(id)}#hr-employee-linked-documents`

export default function HrComplianceDocumentsPage() {
  const { t } = useI18n()
  const [missing, setMissing] = useState<{ total: number; items: HrDocumentQueueItem[] } | null>(null)
  const [expiring, setExpiring] = useState<{ total: number; items: HrDocumentQueueItem[] } | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const [m, e] = await Promise.all([
        fetchHrDocumentsMissing({ assignee_scope: 'team', limit: 200, offset: 0 }),
        fetchHrDocumentsExpiring({ assignee_scope: 'team', horizon_days: 30, limit: 200, offset: 0 }),
      ])
      setMissing(m)
      setExpiring(e)
    } catch (ex: unknown) {
      const e = ex as { response?: { data?: { detail?: string } }; message?: string }
      setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const missItems = missing?.items ?? []
  const expItems = expiring?.items ?? []

  const stats = useMemo(
    () => ({
      miss: missing?.total ?? 0,
      exp: expiring?.total ?? 0,
      missHigh: missItems.filter((r) => r.risk === 'high').length,
      expHigh: expItems.filter((r) => r.risk === 'high').length,
    }),
    [expItems, expiring?.total, missItems, missing?.total],
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-900">
            {t('app.nav.hr.compliance.heading', { defaultValue: 'Compliance documents' })}
          </h2>
          <p className="mt-1 max-w-4xl text-sm text-slate-600">
            {t('app.nav.hr.compliance.subtitle', {
              defaultValue: 'Team-scoped legal queues (missing + 30-day expiring). Use Documents hub for filters and merged views.',
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.hrDocuments}>
            {t('app.nav.hr.compliance.open_hub', { defaultValue: 'Documents hub' })}
          </Link>
          <button type="button" className="btn-secondary btn-sm" onClick={() => void load()}>
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
      </div>

      <div className="sticky top-0 z-20 -mx-1 space-y-3 border-b border-slate-200/90 bg-gradient-to-b from-brand-50/95 via-white/95 to-white pb-4 pt-1 backdrop-blur-sm">
        {!loading && !err ? (
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="badge border border-amber-100 bg-amber-50/90 font-medium tabular-nums text-amber-950">
              {t('app.nav.hr.compliance.stat_missing', { defaultValue: 'Missing (API): {n}', values: { n: stats.miss } })}
            </span>
            <span className="badge border border-brand-100 bg-brand-50/90 font-medium tabular-nums text-brand-900">
              {t('app.nav.hr.compliance.stat_expiring', { defaultValue: 'Expiring 30d (API): {n}', values: { n: stats.exp } })}
            </span>
            <span className="badge border border-rose-100 bg-rose-50/90 font-medium tabular-nums text-rose-900">
              {t('app.nav.hr.compliance.stat_high', {
                defaultValue: 'High risk rows (page): {m} missing / {e} expiring',
                values: { m: stats.missHigh, e: stats.expHigh },
              })}
            </span>
          </div>
        ) : null}
      </div>

      {loading ? <p className="text-sm text-slate-600">{t('common.loading')}</p> : null}
      {err ? <div className="alert-error">{err}</div> : null}

      <section className="card overflow-hidden">
        <div className="border-b border-slate-100 bg-brand-50/40 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.nav.hr.compliance.missing', { defaultValue: 'Missing ({{n}})', values: { n: missing?.total ?? 0 } })}
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="table w-full min-w-[960px] text-left text-sm">
            <thead>
              <tr>
                <th>{t('app.nav.hr.compliance.col_doc', { defaultValue: 'Document' })}</th>
                <th>{t('app.nav.hr.compliance.col_status', { defaultValue: 'Status' })}</th>
                <th>{t('app.nav.hr.compliance.col_risk', { defaultValue: 'Risk' })}</th>
                <th>{t('app.nav.hr.compliance.col_handoff', { defaultValue: 'Handoff' })}</th>
                <th>{t('app.nav.hr.compliance.col_employee', { defaultValue: 'Employee' })}</th>
                <th className="w-40">{t('app.nav.hr.compliance.col_actions', { defaultValue: 'Actions' })}</th>
              </tr>
            </thead>
            <tbody>
              {missItems.map((row) => (
                <tr key={`${row.handoff_id}-${row.document_type}`}>
                  <td className="font-medium text-slate-900">{humanizeToken(row.document_type)}</td>
                  <td className="text-slate-700">{humanizeToken(row.current_status)}</td>
                  <td className="text-slate-700">{row.risk}</td>
                  <td className="font-mono text-xs text-slate-600">{row.handoff_id}</td>
                  <td className="font-mono text-xs text-slate-600">{row.workforce_employee_id || '—'}</td>
                  <td>
                    <div className="flex flex-col gap-1">
                      {row.handoff_id ? (
                        <Link className="text-sm font-medium text-brand-700 hover:underline" to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(row.handoff_id)}`}>
                          {t('app.nav.hr.compliance.open_handoff', { defaultValue: 'Handoff' })}
                        </Link>
                      ) : null}
                      {row.workforce_employee_id ? (
                        <Link className="text-xs font-medium text-brand-700 hover:underline" to={empDocsHash(row.workforce_employee_id)}>
                          {t('app.nav.hr.compliance.open_employee', { defaultValue: 'Employee docs' })}
                        </Link>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
              {!missItems.length && !loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-600">
                    {t('app.nav.hr.compliance.empty_missing', { defaultValue: 'No missing documents in queue.' })}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card overflow-hidden">
        <div className="border-b border-slate-100 bg-brand-50/40 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.nav.hr.compliance.expiring', { defaultValue: 'Expiring ({{n}})', values: { n: expiring?.total ?? 0 } })}
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="table w-full min-w-[960px] text-left text-sm">
            <thead>
              <tr>
                <th>{t('app.nav.hr.compliance.col_doc', { defaultValue: 'Document' })}</th>
                <th>{t('app.nav.hr.compliance.col_status', { defaultValue: 'Status' })}</th>
                <th>{t('app.nav.hr.compliance.col_expires', { defaultValue: 'Expires' })}</th>
                <th>{t('app.nav.hr.compliance.col_risk', { defaultValue: 'Risk' })}</th>
                <th>{t('app.nav.hr.compliance.col_handoff', { defaultValue: 'Handoff' })}</th>
                <th>{t('app.nav.hr.compliance.col_employee', { defaultValue: 'Employee' })}</th>
                <th className="w-40">{t('app.nav.hr.compliance.col_actions', { defaultValue: 'Actions' })}</th>
              </tr>
            </thead>
            <tbody>
              {expItems.map((row) => (
                <tr key={`${row.handoff_id}-${row.document_type}-${row.expires_at || ''}`}>
                  <td className="font-medium text-slate-900">{humanizeToken(row.document_type)}</td>
                  <td className="text-slate-700">{humanizeToken(row.current_status)}</td>
                  <td className="whitespace-nowrap text-xs text-slate-600">{row.expires_at || '—'}</td>
                  <td className="text-slate-700">{row.risk}</td>
                  <td className="font-mono text-xs text-slate-600">{row.handoff_id}</td>
                  <td className="font-mono text-xs text-slate-600">{row.workforce_employee_id || '—'}</td>
                  <td>
                    <div className="flex flex-col gap-1">
                      {row.handoff_id ? (
                        <Link className="text-sm font-medium text-brand-700 hover:underline" to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(row.handoff_id)}`}>
                          {t('app.nav.hr.compliance.open_handoff', { defaultValue: 'Handoff' })}
                        </Link>
                      ) : null}
                      {row.workforce_employee_id ? (
                        <Link className="text-xs font-medium text-brand-700 hover:underline" to={empDocsHash(row.workforce_employee_id)}>
                          {t('app.nav.hr.compliance.open_employee', { defaultValue: 'Employee docs' })}
                        </Link>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
              {!expItems.length && !loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-600">
                    {t('app.nav.hr.compliance.empty_expiring', { defaultValue: 'No expiring documents in horizon.' })}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
