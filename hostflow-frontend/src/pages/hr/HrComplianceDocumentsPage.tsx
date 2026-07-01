import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { fetchHrDocumentsExpiring, fetchHrDocumentsMissing, type HrDocumentQueueItem } from '../../api/hrWorkspace'
import { useI18n } from '../../i18n'
import { humanizeToken } from '../../components/hr/hrEmployeeUiFormat'
import {
  IMPACT_LABEL,
  NEXT_ACTION_LABEL,
  SEVERITY_META,
  type OperationalImpact,
  type OperationalNextAction,
  type OperationalSeverity,
} from '../../constants/workforceOperationalTaxonomy'

import { hrEmployeeVerificationPath, hrHandoffPath } from '../../utils/hrEmployeeLinks'

function parseIso(value: string | null | undefined): number | null {
  if (!value) return null
  const ms = Date.parse(value)
  return Number.isFinite(ms) ? ms : null
}

function daysLeft(value: string | null | undefined): number | null {
  const ms = parseIso(value)
  if (ms == null) return null
  const diff = ms - Date.now()
  return Math.floor(diff / (24 * 60 * 60 * 1000))
}

function impactForRow(row: HrDocumentQueueItem): OperationalImpact {
  const d = String(row.document_type || '').toLowerCase()
  if (d.includes('permit') || d.includes('visa') || d.includes('residence')) return 'legal_blocker'
  if (d.includes('license') || d.includes('code_95') || d.includes('tachograph')) return 'dispatch_blocker'
  return 'document_missing'
}

function nextActionForRow(row: HrDocumentQueueItem): OperationalNextAction {
  const impact = impactForRow(row)
  if (impact === 'legal_blocker') return 'upload_document'
  if (impact === 'dispatch_blocker') return 'renew_document'
  return 'verify_document'
}

function severityForRow(row: HrDocumentQueueItem): OperationalSeverity {
  if (row.risk === 'high') return 'critical'
  const d = daysLeft(row.expires_at)
  if (d != null && d < 0) return 'high'
  if (d != null && d <= 7) return 'medium'
  return 'low'
}

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
      exp7: expItems.filter((r) => {
        const d = daysLeft(r.expires_at)
        return d != null && d >= 0 && d <= 7
      }).length,
      exp30: expItems.filter((r) => {
        const d = daysLeft(r.expires_at)
        return d != null && d >= 0 && d <= 30
      }).length,
    }),
    [expItems, expiring?.total, missItems, missing?.total],
  )

  const criticalBlockers = useMemo(
    () => [
      ...missItems.filter((r) => r.required && r.risk === 'high').map((r) => ({ ...r, source: 'missing' as const })),
      ...expItems.filter((r) => {
        const d = daysLeft(r.expires_at)
        return r.risk === 'high' && d != null && d < 0
      }).map((r) => ({ ...r, source: 'expiring' as const })),
    ],
    [expItems, missItems],
  )

  const highRiskSoon = useMemo(
    () => expItems.filter((r) => {
      const d = daysLeft(r.expires_at)
      return r.risk === 'high' || (d != null && d >= 0 && d <= 7)
    }),
    [expItems],
  )

  const readyEmployees = useMemo(() => {
    const touched = new Set<string>()
    ;[...missItems, ...expItems].forEach((r) => {
      if (r.workforce_employee_id) touched.add(r.workforce_employee_id)
    })
    const blocked = new Set<string>()
    criticalBlockers.forEach((r) => {
      if (r.workforce_employee_id) blocked.add(r.workforce_employee_id)
    })
    return Math.max(0, touched.size - blocked.size)
  }, [criticalBlockers, expItems, missItems])

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
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5 text-xs">
            <span className="badge border border-rose-100 bg-rose-50/90 font-medium tabular-nums text-rose-900">
              Critical blockers: {criticalBlockers.length}
            </span>
            <span className="badge border border-amber-100 bg-amber-50/90 font-medium tabular-nums text-amber-950">
              Missing required docs: {stats.miss}
            </span>
            <span className="badge border border-amber-100 bg-amber-50/90 font-medium tabular-nums text-amber-950">
              Expiring 7 days: {stats.exp7}
            </span>
            <span className="badge border border-brand-100 bg-brand-50/90 font-medium tabular-nums text-brand-900">
              Expiring 30 days: {stats.exp30}
            </span>
            <span className="badge border border-emerald-100 bg-emerald-50/90 font-medium tabular-nums text-emerald-900">
              Ready employees: {readyEmployees}
            </span>
          </div>
        ) : null}
      </div>

      {loading ? <p className="text-sm text-slate-600">{t('common.loading')}</p> : null}
      {err ? <div className="alert-error">{err}</div> : null}

      <ComplianceSection
        title="Critical blockers"
        rows={criticalBlockers}
        emptyText="No critical compliance risks"
      />

      <ComplianceSection
        title="High risk / expiring soon"
        rows={highRiskSoon}
        emptyText="No high-risk or near-expiry risks"
      />

      <ComplianceSection
        title="All clear"
        rows={[]}
        emptyText="No critical compliance risks. Workforce is operationally clear."
      />
    </div>
  )
}

function ComplianceSection({
  title,
  rows,
  emptyText,
}: {
  title: string
  rows: Array<(HrDocumentQueueItem & { source?: string })>
  emptyText: string
}) {
  const { t } = useI18n()
  return (
    <section className="card p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">{rows.length}</span>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-emerald-700">{emptyText}</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((row) => (
            <li key={`${row.handoff_id}-${row.document_type}-${row.expires_at || ''}`} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-medium text-slate-900">{humanizeToken(row.document_type)}</div>
                  <div className="mt-0.5 text-xs text-slate-600">
                    risk: {row.risk} · impact: {IMPACT_LABEL[impactForRow(row)]} · next: {NEXT_ACTION_LABEL[nextActionForRow(row)]}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    owner: team · status: {humanizeToken(row.current_status)} {row.expires_at ? `· expires ${row.expires_at}` : ''}
                  </div>
                  <div className={`mt-1 inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${SEVERITY_META[severityForRow(row)].tone}`}>
                    {severityForRow(row)}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {row.workforce_employee_id ? (
                    <>
                      <Link className="text-sm font-medium text-brand-700 hover:underline" to={hrEmployeeVerificationPath(row.workforce_employee_id)}>
                        {t('app.hr.verify_task.open_verification', { defaultValue: 'Verify documents' })}
                      </Link>
                      <Link className="text-xs font-medium text-brand-700 hover:underline" to={`${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(row.workforce_employee_id)}#hr-employee-linked-documents`}>
                        {t('app.hr.documents_hub.open_employee', { defaultValue: 'Open employee' })}
                      </Link>
                    </>
                  ) : null}
                  {row.handoff_id ? (
                    <Link className="text-xs font-medium text-brand-700 hover:underline" to={hrHandoffPath(row.handoff_id)}>
                      {t('app.hr.documents_hub.open_handoff', { defaultValue: 'Review' })}
                    </Link>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
