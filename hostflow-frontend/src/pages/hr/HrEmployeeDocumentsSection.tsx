import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { listWorkforceEmployeeDocuments, type WorkforceEmployeeDocumentRow } from '../../api/workforce'

type Props = {
  employeeId: string
  candidateId?: string | null
}

export function HrEmployeeDocumentsSection({ employeeId, candidateId }: Props) {
  const { t } = useI18n()
  const [rows, setRows] = useState<WorkforceEmployeeDocumentRow[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setLoadError(null)
      try {
        const data = await listWorkforceEmployeeDocuments(employeeId)
        if (!cancelled) {
          setRows(data)
          setLoadError(null)
        }
      } catch {
        if (!cancelled) {
          setRows([])
          setLoadError(t('app.hr.employee_detail.documents_load_error'))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [employeeId, t])

  if (!candidateId) {
    return (
      <details open className="rounded-lg border border-slate-200 bg-white">
        <summary className="cursor-pointer select-none border-b border-slate-100 px-3 py-2 text-sm font-medium text-slate-900">
          {t('app.hr.employee_detail.section_documents')}
        </summary>
        <div className="p-3 text-sm text-slate-600">{t('app.hr.employee_detail.documents_no_candidate')}</div>
      </details>
    )
  }

  return (
    <details open className="rounded-lg border border-slate-200 bg-white">
      <summary className="cursor-pointer select-none border-b border-slate-100 px-3 py-2 text-sm font-medium text-slate-900">
        {t('app.hr.employee_detail.section_documents')}
      </summary>
      <div className="p-3">
        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : loadError ? (
          <p className="text-sm text-red-600">{loadError}</p>
        ) : !rows || rows.length === 0 ? (
          <p className="text-sm text-slate-500">{t('app.hr.employee_detail.documents_empty')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-600">
                  <th className="py-1.5 pr-2 font-medium">{t('app.hr.employee_detail.doc_col_title')}</th>
                  <th className="py-1.5 pr-2 font-medium">{t('app.hr.employee_detail.doc_col_type')}</th>
                  <th className="py-1.5 pr-2 font-medium">{t('app.hr.employee_detail.doc_col_status')}</th>
                  <th className="py-1.5 pr-2 font-medium">{t('app.hr.employee_detail.doc_col_expires')}</th>
                  <th className="py-1.5 pr-2 font-medium">{t('app.hr.employee_detail.doc_col_days_left')}</th>
                  <th className="py-1.5 font-medium">{t('app.hr.employee_detail.doc_col_file')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ document: d, downloadUrl, daysLeft }) => (
                  <tr key={d.id} className="border-b border-slate-100">
                    <td className="py-1.5 pr-2 text-slate-900">{d.title || d.doc_type}</td>
                    <td className="py-1.5 pr-2 font-mono text-xs text-slate-700">{d.doc_type}</td>
                    <td className="py-1.5 pr-2">{d.status}</td>
                    <td className="py-1.5 pr-2 text-slate-600">{d.expires_at || d.expire_date || '—'}</td>
                    <td className="py-1.5 pr-2 text-slate-600 tabular-nums">
                      {daysLeft != null ? daysLeft : '—'}
                    </td>
                    <td className="py-1.5">
                      {downloadUrl ? (
                        <a
                          href={downloadUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-brand-600 hover:underline"
                        >
                          {t('app.hr.employee_detail.doc_open')}
                        </a>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </details>
  )
}
