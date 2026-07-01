import { Link, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { WorkforceHrDocumentContextRow, WorkforceHrDocumentContextSummary } from '../../api/workforce'
import { formatShortDateIso, humanizeToken } from './hrEmployeeUiFormat'

function rowStatusLabel(row: WorkforceHrDocumentContextRow, t: ReturnType<typeof useI18n>['t']): string {
  const vs = (row.verification_status || '').trim()
  if (vs) return humanizeToken(vs)
  return row.verified
    ? t('app.hr.employee_operational.legal_ver_ok', { defaultValue: 'Verified' })
    : t('app.hr.employee_operational.legal_ver_pending', { defaultValue: 'Pending' })
}

type Props = {
  summary: WorkforceHrDocumentContextSummary
}

/**
 * CRM-style legal dossier checklist (replaces raw HR document context breakdown).
 */
export default function HrLegalDocumentChecklist({ summary }: Props) {
  const { t } = useI18n()
  const location = useLocation()
  const anchorHref = `${location.pathname}${location.search}#hr-employee-linked-documents`

  const items = summary.items ?? []

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-600">
        {t('app.hr.employee_operational.legal_docs_hint', {
          defaultValue: 'What HR must collect and verify — aligned with recruitment document patterns.',
        })}
      </p>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">
          {t('app.hr.employee_operational.legal_docs_empty', { defaultValue: 'No legal document requirements linked yet.' })}
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-slate-700">
              <span className="font-semibold tabular-nums">{summary.total}</span>{' '}
              {t('app.hr.employee_operational.legal_docs_count', { defaultValue: 'linked requirement(s)' })}
            </p>
            <Link to={anchorHref} className="btn-secondary btn-sm shrink-0">
              {t('app.hr.employee_operational.legal_docs_cta', { defaultValue: 'Open dossier documents' })}
            </Link>
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-600">
                <tr>
                  <th className="px-3 py-2">{t('app.hr.employee_operational.legal_col_document', { defaultValue: 'Document' })}</th>
                  <th className="px-3 py-2">{t('app.hr.employee_operational.legal_col_status', { defaultValue: 'Status' })}</th>
                  <th className="px-3 py-2">{t('app.hr.employee_operational.legal_col_required', { defaultValue: 'Requirement' })}</th>
                  <th className="px-3 py-2">{t('app.hr.employee_operational.legal_col_verified', { defaultValue: 'Verification' })}</th>
                  <th className="px-3 py-2">{t('app.hr.employee_operational.legal_col_expires', { defaultValue: 'Expires' })}</th>
                  <th className="px-3 py-2">{t('app.hr.employee_operational.legal_col_action', { defaultValue: 'Action' })}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-2.5 align-top">
                      <div className="font-medium text-slate-900">
                        {humanizeToken(row.document_group || row.legal_category || row.context_type)}
                      </div>
                      {row.document_group || row.legal_category ? (
                        <div className="text-xs text-slate-500 mt-0.5">{humanizeToken(row.context_type)}</div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2.5 align-top">
                      <span className="inline-flex rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-800">
                        {rowStatusLabel(row, t)}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 align-top">
                      <span
                        className={clsx(
                          'inline-flex rounded-full border px-2 py-0.5 text-xs font-medium',
                          row.required
                            ? 'border-amber-200 bg-amber-50 text-amber-950'
                            : 'border-slate-200 bg-slate-50 text-slate-600',
                        )}
                      >
                        {row.required
                          ? t('app.hr.employee_operational.legal_req_required', { defaultValue: 'Required' })
                          : t('app.hr.employee_operational.legal_req_optional', { defaultValue: 'Optional' })}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 align-top">
                      <span
                        className={clsx(
                          'inline-flex rounded-full border px-2 py-0.5 text-xs font-medium',
                          row.verified ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-slate-200 bg-white text-slate-600',
                        )}
                      >
                        {row.verified
                          ? t('app.hr.employee_operational.legal_ver_ok', { defaultValue: 'Verified' })
                          : t('app.hr.employee_operational.legal_ver_pending', { defaultValue: 'Pending' })}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 align-top text-slate-700 tabular-nums">{formatShortDateIso(row.expires_at)}</td>
                    <td className="px-3 py-2.5 align-top">
                      <Link to={anchorHref} className="text-sm text-indigo-700 underline-offset-2 hover:underline">
                        {t('app.hr.employee_operational.legal_action_review', { defaultValue: 'Review in dossier' })}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500">
            <Link to={CRM_APP_PATHS.documents} className="text-indigo-700 underline-offset-2 hover:underline" target="_blank" rel="noopener noreferrer">
              {t('app.hr.employee_operational.legal_docs_hub', { defaultValue: 'Open documents hub' })}
            </Link>
          </p>
        </>
      )}
    </div>
  )
}
