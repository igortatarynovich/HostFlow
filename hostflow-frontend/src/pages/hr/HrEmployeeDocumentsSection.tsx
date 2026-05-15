import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { listWorkforceEmployeeDocuments, type WorkforceEmployeeDocumentRow } from '../../api/workforce'

type Props = {
  employeeId: string
  candidateId?: string | null
  /** When set, skip GET `/documents` and render this list (from operational-profile read-model). */
  prefetchedRows?: WorkforceEmployeeDocumentRow[] | null
  missingQueue?: Array<Record<string, unknown>>
  expiringQueue?: Array<Record<string, unknown>>
}

export function HrEmployeeDocumentsSection({
  employeeId,
  candidateId,
  prefetchedRows,
  missingQueue,
  expiringQueue,
}: Props) {
  const { t } = useI18n()
  const [rows, setRows] = useState<WorkforceEmployeeDocumentRow[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    if (prefetchedRows !== undefined) {
      setRows(prefetchedRows ?? [])
      setLoadError(null)
      setLoading(false)
      return
    }
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
          setLoadError(
            t('app.hr.employee_detail.documents_load_error', {
              defaultValue: 'Could not load documents',
            }),
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [employeeId, prefetchedRows, t])

  if (prefetchedRows === undefined && !candidateId) {
    return (
      <details id="hr-employee-linked-documents" open className="rounded-lg border border-slate-200 bg-white">
        <summary className="cursor-pointer select-none border-b border-slate-100 px-3 py-2 text-sm font-medium text-slate-900">
          {t('app.hr.employee_detail.section_documents', { defaultValue: 'HR documents' })}
        </summary>
        <div className="p-3 text-sm text-slate-600">
          {t('app.hr.employee_detail.documents_no_candidate', {
            defaultValue: 'No linked recruitment candidate — documents load when a candidate link exists.',
          })}
        </div>
      </details>
    )
  }

  const missing = missingQueue ?? []
  const expiring = expiringQueue ?? []

  return (
    <details id="hr-employee-linked-documents" open className="rounded-lg border border-slate-200 bg-white">
      <summary className="cursor-pointer select-none border-b border-slate-100 px-3 py-2 text-sm font-medium text-slate-900">
        {t('app.hr.employee_detail.section_documents', { defaultValue: 'HR documents' })}
      </summary>
      <div className="p-3 space-y-4">
        {missing.length > 0 ? (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-amber-800 mb-1">
              {t('app.hr.employee_operational.missing_queue', { defaultValue: 'Missing (queue)' })}
            </div>
            <ul className="list-disc pl-4 text-sm text-slate-700 space-y-0.5">
              {missing.slice(0, 12).map((r, i) => (
                <li key={i}>
                  {(r.document_type as string) || (r.doc_type as string) || (r.requirement as string) || '—'}
                </li>
              ))}
            </ul>
            {missing.length > 12 ? (
              <p className="text-xs text-slate-500 mt-1">
                {t('app.hr.employee_operational.queue_truncated', { defaultValue: 'Showing first 12 rows.' })}
              </p>
            ) : null}
          </div>
        ) : null}
        {expiring.length > 0 ? (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-orange-900 mb-1">
              {t('app.hr.employee_operational.expiring_queue', { defaultValue: 'Expiring (queue)' })}
            </div>
            <ul className="list-disc pl-4 text-sm text-slate-700 space-y-0.5">
              {expiring.slice(0, 12).map((r, i) => (
                <li key={i}>
                  {(r.document_type as string) || (r.doc_type as string) || '—'}
                  {r.days_left != null ? ` (${r.days_left}d)` : ''}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
        ) : loadError ? (
          <p className="text-sm text-red-600">{loadError}</p>
        ) : !rows || rows.length === 0 ? (
          <p className="text-sm text-slate-500">
            {t('app.hr.employee_detail.documents_empty', { defaultValue: 'No documents on file.' })}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <div className="text-xs font-semibold text-slate-600 mb-2">
              {t('app.hr.employee_operational.linked_documents', { defaultValue: 'Linked dossier documents' })}
            </div>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-600">
                  <th className="py-1.5 pr-2 font-medium">
                    {t('app.hr.employee_detail.doc_col_title', { defaultValue: 'Title' })}
                  </th>
                  <th className="py-1.5 pr-2 font-medium">
                    {t('app.hr.employee_detail.doc_col_type', { defaultValue: 'Type' })}
                  </th>
                  <th className="py-1.5 pr-2 font-medium">
                    {t('app.hr.employee_detail.doc_col_status', { defaultValue: 'Status' })}
                  </th>
                  <th className="py-1.5 pr-2 font-medium">
                    {t('app.hr.employee_detail.doc_col_expires', { defaultValue: 'Expires' })}
                  </th>
                  <th className="py-1.5 pr-2 font-medium">
                    {t('app.hr.employee_detail.doc_col_days_left', { defaultValue: 'Days left' })}
                  </th>
                  <th className="py-1.5 font-medium">
                    {t('app.hr.employee_detail.doc_col_file', { defaultValue: 'File' })}
                  </th>
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
                          {t('app.hr.employee_detail.doc_open', { defaultValue: 'Open' })}
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
