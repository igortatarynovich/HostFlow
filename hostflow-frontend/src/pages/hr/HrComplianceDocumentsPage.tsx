import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { fetchHrDocumentsExpiring, fetchHrDocumentsMissing } from '../../api/hrWorkspace'
import { useI18n } from '../../i18n'

export default function HrComplianceDocumentsPage() {
  const { t } = useI18n()
  const [missing, setMissing] = useState<any>(null)
  const [expiring, setExpiring] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const [m, e] = await Promise.all([
        fetchHrDocumentsMissing({ assignee_scope: 'team', limit: 100, offset: 0 }),
        fetchHrDocumentsExpiring({ assignee_scope: 'team', horizon_days: 30, limit: 100, offset: 0 }),
      ])
      setMissing(m)
      setExpiring(e)
    } catch (ex: any) {
      setErr(ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const missItems = missing?.items ?? []
  const expItems = expiring?.items ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-slate-900">
          {t('app.nav.hr.compliance.heading', { defaultValue: 'Compliance documents' })}
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

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.nav.hr.compliance.missing', { defaultValue: 'Missing ({{n}})', n: missing?.total ?? 0 })}
          </h3>
        </div>
        <ul className="divide-y divide-slate-100">
          {missItems.map((row: any) => (
            <li key={`${row.handoff_id}-${row.document_type}`} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5">
              <div className="text-sm text-slate-800">
                <span className="font-medium">{row.document_type}</span>
                <span className="text-slate-500"> · {row.handoff_id}</span>
              </div>
              {row.handoff_id ? (
                <Link
                  to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(row.handoff_id)}`}
                  className="text-sm font-medium text-brand-700 hover:text-brand-900"
                >
                  {t('app.nav.hr.compliance.open_handoff', { defaultValue: 'Handoff' })}
                </Link>
              ) : null}
            </li>
          ))}
          {!missItems.length && !loading ? (
            <li className="px-4 py-6 text-center text-sm text-slate-500">
              {t('app.nav.hr.compliance.empty_missing', { defaultValue: 'No missing documents in queue.' })}
            </li>
          ) : null}
        </ul>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.nav.hr.compliance.expiring', { defaultValue: 'Expiring ({{n}})', n: expiring?.total ?? 0 })}
          </h3>
        </div>
        <ul className="divide-y divide-slate-100">
          {expItems.map((row: any) => (
            <li key={`${row.handoff_id}-${row.document_type}-${row.expires_at}`} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5">
              <div className="text-sm text-slate-800">
                <span className="font-medium">{row.document_type}</span>
                <span className="text-slate-500"> · {row.expires_at || row.handoff_id}</span>
              </div>
              {row.handoff_id ? (
                <Link
                  to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(row.handoff_id)}`}
                  className="text-sm font-medium text-brand-700 hover:text-brand-900"
                >
                  {t('app.nav.hr.compliance.open_handoff', { defaultValue: 'Handoff' })}
                </Link>
              ) : null}
            </li>
          ))}
          {!expItems.length && !loading ? (
            <li className="px-4 py-6 text-center text-sm text-slate-500">
              {t('app.nav.hr.compliance.empty_expiring', { defaultValue: 'No expiring documents in horizon.' })}
            </li>
          ) : null}
        </ul>
      </section>
    </div>
  )
}
