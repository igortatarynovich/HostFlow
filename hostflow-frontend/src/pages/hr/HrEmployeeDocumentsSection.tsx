import { useEffect, useMemo, useState } from 'react'
import { useI18n } from '../../i18n'
import {
  getHrOperationalContext,
  listWorkforceEmployeeDocuments,
  patchWorkforceDocumentControlTask,
  type HrOperationalContext,
  type WorkforceDocumentControlTask,
  type WorkforceEmployeeDocumentRow,
} from '../../api/workforce'
import HrDocumentOpenButton from '../../components/hr/HrDocumentOpenButton'
import { HrEmployeeDocumentVerifyActions } from '../../components/hr/HrEmployeeDocumentVerifyActions'
import { findReviewDocumentForEmployeeDoc } from '../../components/hr/hrDocumentVerificationFields'
import type { HrReviewPanel } from '../../api/workforce'

/**
 * Local HR documents matrix. Not the D2 `documents` consume path (E3).
 * Proof surface is DocumentsCapability via Document Link + hub adapter.
 */
type Props = {
  employeeId: string
  manage?: boolean
  candidateId?: string | null
  ownerContext?: Record<string, unknown> | null
  hrReview?: HrReviewPanel | null
  onHrReviewUpdated?: (panel: HrReviewPanel) => void
  sectionOpen?: boolean
  /** When set, skip GET `/documents` and render this list (from operational-profile read-model). */
  prefetchedRows?: WorkforceEmployeeDocumentRow[] | null
  expectedDocs?: Array<Record<string, unknown>> | null
  controlTasks?: WorkforceDocumentControlTask[] | null
  missingQueue?: Array<Record<string, unknown>>
  expiringQueue?: Array<Record<string, unknown>>
}

type ExpectedDocDef = {
  key: string
  label: string
  group: string
  owner: string
  defaultNextAction: string
  aliases: string[]
}

function norm(s: unknown): string {
  return String(s || '')
    .trim()
    .toLowerCase()
}

function matchDoc(def: ExpectedDocDef, row: WorkforceEmployeeDocumentRow): boolean {
  const code = norm(row.document.doc_type)
  const title = norm(row.document.title)
  return def.aliases.some((a) => code.includes(a) || title.includes(a))
}

export function HrEmployeeDocumentsSection({
  employeeId,
  manage = false,
  candidateId,
  ownerContext,
  hrReview,
  onHrReviewUpdated,
  sectionOpen = false,
  prefetchedRows,
  expectedDocs,
  controlTasks,
  missingQueue,
  expiringQueue,
}: Props) {
  const { t } = useI18n()
  const [rows, setRows] = useState<WorkforceEmployeeDocumentRow[] | null>(null)
  const [operationalContext, setOperationalContext] = useState<HrOperationalContext | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [taskSavingKey, setTaskSavingKey] = useState<string | null>(null)
  const summaryContext = useMemo(() => ownerContext || null, [ownerContext])

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

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const ctx = await getHrOperationalContext(employeeId)
        if (!cancelled) setOperationalContext(ctx)
      } catch {
        if (!cancelled) setOperationalContext(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [employeeId])

  const linkedDocumentIds = useMemo(() => {
    const ids = new Set<string>()
    for (const link of operationalContext?.document_links || []) {
      const did = String(link.document_id || '').trim()
      if (did) ids.add(did)
    }
    return ids
  }, [operationalContext])

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
  const actionForRow = (row: WorkforceEmployeeDocumentRow): string => {
    const st = String(row.document.verification_status || row.document.status || '').toLowerCase()
    if (st.includes('reject') || st.includes('correction')) return 'Fix / re-upload'
    if (st.includes('pending') || st.includes('review')) return 'Verify'
    if (row.daysLeft != null && row.daysLeft < 0) return 'Renew'
    if (row.daysLeft != null && row.daysLeft <= 30) return 'Prepare renewal'
    return 'No action'
  }
  const verifiedForRow = (row: WorkforceEmployeeDocumentRow): string => {
    const st = String(row.document.verification_status || row.document.status || '').toLowerCase()
    if (st.includes('verified') || st.includes('approved')) return 'Yes'
    if (st.includes('reject') || st.includes('correction')) return 'No'
    return 'In review'
  }

  const defs: ExpectedDocDef[] = Array.isArray(expectedDocs)
    ? expectedDocs
        .map((x) => {
          const row = x as Record<string, unknown>
          return {
            key: String(row.document_code || '').trim(),
            label: String(row.label || '').trim(),
            group: String(row.group || 'other').trim(),
            owner: String(row.default_owner || 'HR').trim(),
            defaultNextAction: String(row.default_next_action || 'Request upload').trim(),
            aliases: Array.isArray(row.aliases) ? row.aliases.map((a) => String(a).toLowerCase()) : [],
          }
        })
        .filter((x) => x.key && x.label)
    : []
  const matrixRows = defs.map((def) => {
    const override = (controlTasks || []).find((t) => norm(t.document_code) === norm(def.key)) || null
    const src = (rows || []).find((r) => matchDoc(def, r)) || null
    const isMissing = !src
    const daysLeft = src?.daysLeft ?? null
    const expiresAt = src?.document.expires_at || src?.document.expire_date || null
    const verified = src ? verifiedForRow(src) : 'No'
    const status = isMissing
      ? 'Missing'
      : daysLeft != null && daysLeft < 0
      ? 'Expired'
      : daysLeft != null && daysLeft <= 30
      ? 'Expiring soon'
      : 'Available'
    const nextAction = isMissing
      ? def.defaultNextAction || 'Request upload'
      : actionForRow(src)
    const nextDueDate =
      isMissing ? null : daysLeft != null && daysLeft <= 30 ? expiresAt : null
    return {
      key: def.key,
      label: def.label,
      group: def.group,
      owner: def.owner,
      status,
      expiresAt,
      verified,
      nextAction: override?.next_action || nextAction,
      nextDueDate: override?.next_due_date || nextDueDate,
      ownerOverride: override?.owner || def.owner,
      statusOverride: override?.status || 'open',
      commentOverride: override?.comment || '',
      openUrl: src?.downloadUrl || null,
    }
  })

  return (
    <details
      id="hr-employee-linked-documents"
      open={sectionOpen}
      className="rounded-lg border border-slate-200 bg-white"
    >
      <summary className="cursor-pointer select-none border-b border-slate-100 px-3 py-2 text-sm font-medium text-slate-900">
        {t('app.hr.employee_detail.section_documents', { defaultValue: 'HR documents' })}
      </summary>
      <div className="p-3 space-y-4">
        {operationalContext?.hr_case ? (
          <p className="text-xs text-slate-600">
            {t('app.hr.employee_operational.hr_context_status', {
              defaultValue: 'Operational record: {status}',
              values: { status: operationalContext.hr_case.status || 'open' },
            })}
            {' · '}
            {t('app.hr.employee_operational.hr_context_links', {
              defaultValue: '{count} document(s) linked from recruitment',
              values: { count: operationalContext.document_links?.length ?? 0 },
            })}
          </p>
        ) : null}
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
        ) : (
          <div className="space-y-4">
            <div>
              <div className="text-xs font-semibold text-slate-600 mb-2">
                {t('app.hr.employee_operational.linked_documents', { defaultValue: 'Employee documents' })}
              </div>
              {rows && rows.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {rows.map((r) => {
                    const reviewDoc = hrReview ? findReviewDocumentForEmployeeDoc(hrReview, r.document) : null
                    return (
                    <div key={r.document.id} className="rounded border border-slate-200 bg-slate-50 p-3">
                      <div className="text-sm font-semibold text-slate-900">{r.document.title || r.document.doc_type || 'Document'}</div>
                      {linkedDocumentIds.has(String(r.document.id)) ? (
                        <div className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-brand-700">
                          {t('app.hr.employee_operational.reused_from_recruitment', {
                            defaultValue: 'Reused from recruitment',
                          })}
                        </div>
                      ) : null}
                      <div className="mt-1 text-xs text-slate-600">Type: {r.document.doc_type || '—'}</div>
                      <div className="text-xs text-slate-600">
                        Expiry: {r.document.expires_at || r.document.expire_date || '—'}
                      </div>
                      <div className="text-xs text-slate-600">Status: {r.document.verification_status || r.document.status || '—'}</div>
                      <div className="mt-2">
                        {r.downloadUrl && (r.downloadUrl.startsWith('http://') || r.downloadUrl.startsWith('https://')) ? (
                          <a href={r.downloadUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-brand-700 hover:underline">
                            {t('app.hr.employee_detail.doc_open', { defaultValue: 'Open' })}
                          </a>
                        ) : r.downloadUrl ? (
                          <HrDocumentOpenButton openUrl={r.downloadUrl} />
                        ) : (
                          <span className="text-xs text-slate-400">No file</span>
                        )}
                      </div>
                      {reviewDoc ? (
                        <HrEmployeeDocumentVerifyActions
                          employeeId={employeeId}
                          candidateId={candidateId}
                          reviewDoc={reviewDoc}
                          manage={manage}
                          onPanelUpdated={onHrReviewUpdated}
                        />
                      ) : null}
                    </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No uploaded documents yet.</p>
              )}
            </div>
            <details className="rounded border border-slate-200 bg-white">
              <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-slate-700">
                {t('app.hr.employee_operational.linked_documents', { defaultValue: 'Canonical HR documents matrix' })} (secondary)
              </summary>
              <div className="overflow-x-auto p-3">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-600">
                  <th className="py-1.5 pr-2 font-medium">Document</th>
                  <th className="py-1.5 pr-2 font-medium">Group</th>
                  <th className="py-1.5 pr-2 font-medium">Status</th>
                  <th className="py-1.5 pr-2 font-medium">Expires</th>
                  <th className="py-1.5 pr-2 font-medium">Verified</th>
                  <th className="py-1.5 pr-2 font-medium">Owner</th>
                  <th className="py-1.5 pr-2 font-medium">Next action</th>
                  <th className="py-1.5 pr-2 font-medium">Next due date</th>
                  <th className="py-1.5 pr-2 font-medium">
                    {t('app.hr.employee_detail.doc_col_file', { defaultValue: 'File' })}
                  </th>
                  <th className="py-1.5 font-medium">Task</th>
                </tr>
              </thead>
              <tbody>
                {matrixRows.map((r) => (
                  <tr key={r.key} className="border-b border-slate-100">
                    <td className="py-1.5 pr-2 text-slate-900">{r.label}</td>
                    <td className="py-1.5 pr-2 font-mono text-xs text-slate-700">{r.group}</td>
                    <td className="py-1.5 pr-2">{r.status}</td>
                    <td className="py-1.5 pr-2 text-slate-600">{r.expiresAt || '—'}</td>
                    <td className="py-1.5 pr-2">{r.verified}</td>
                    <td className="py-1.5 pr-2">{r.ownerOverride}</td>
                    <td className="py-1.5 pr-2">{r.nextAction}</td>
                    <td className="py-1.5 pr-2 text-slate-600">{r.nextDueDate || '—'}</td>
                    <td className="py-1.5">
                      {r.openUrl && (r.openUrl.startsWith('http://') || r.openUrl.startsWith('https://')) ? (
                        <a
                          href={r.openUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-brand-600 hover:underline"
                        >
                          {t('app.hr.employee_detail.doc_open', { defaultValue: 'Open' })}
                        </a>
                      ) : r.openUrl ? (
                        <HrDocumentOpenButton openUrl={r.openUrl} />
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-1.5 pl-2">
                      {manage ? (
                        <details>
                          <summary className="cursor-pointer text-xs text-brand-700">Edit task</summary>
                          <div className="mt-2 space-y-2 min-w-64">
                            <input
                              className="w-full border border-slate-200 rounded px-2 py-1 text-xs"
                              defaultValue={r.ownerOverride}
                              placeholder="Owner"
                              id={`owner-${r.key}`}
                            />
                            <input
                              className="w-full border border-slate-200 rounded px-2 py-1 text-xs"
                              defaultValue={r.nextAction}
                              placeholder="Next action"
                              id={`action-${r.key}`}
                            />
                            <input
                              type="date"
                              className="w-full border border-slate-200 rounded px-2 py-1 text-xs"
                              defaultValue={r.nextDueDate || ''}
                              id={`due-${r.key}`}
                            />
                            <input
                              className="w-full border border-slate-200 rounded px-2 py-1 text-xs"
                              defaultValue={r.statusOverride}
                              placeholder="Status"
                              id={`status-${r.key}`}
                            />
                            <textarea
                              className="w-full border border-slate-200 rounded px-2 py-1 text-xs"
                              defaultValue={r.commentOverride}
                              placeholder="Comment"
                              id={`comment-${r.key}`}
                            />
                            <button
                              type="button"
                              disabled={taskSavingKey === r.key}
                              className="px-2 py-1 rounded bg-slate-900 text-white text-xs disabled:opacity-50"
                              onClick={async () => {
                                const ownerEl = document.getElementById(`owner-${r.key}`) as HTMLInputElement | null
                                const actionEl = document.getElementById(`action-${r.key}`) as HTMLInputElement | null
                                const dueEl = document.getElementById(`due-${r.key}`) as HTMLInputElement | null
                                const statusEl = document.getElementById(`status-${r.key}`) as HTMLInputElement | null
                                const commentEl = document.getElementById(`comment-${r.key}`) as HTMLTextAreaElement | null
                                setTaskSavingKey(r.key)
                                try {
                                  await patchWorkforceDocumentControlTask(employeeId, r.key, {
                                    owner: ownerEl?.value?.trim() || null,
                                    next_action: actionEl?.value?.trim() || null,
                                    next_due_date: dueEl?.value?.trim() || null,
                                    status: statusEl?.value?.trim() || null,
                                    comment: commentEl?.value?.trim() || null,
                                  })
                                } finally {
                                  setTaskSavingKey(null)
                                }
                              }}
                            >
                              Save
                            </button>
                          </div>
                        </details>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
              </div>
            </details>
          </div>
        )}
      </div>
    </details>
  )
}
