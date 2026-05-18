import { useMemo, useState } from 'react'
import clsx from 'clsx'
import type { HrDataVerificationItem, HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import {
  postHrDocumentOpened,
  postHrDocumentRequestCorrection,
  postHrDocumentReviewed,
  postHrVerifiedFieldOverride,
} from '../../api/workforce'
import HrDocumentVerificationCard from './HrDocumentVerificationCard'
import HrEmploymentIdentityCompact from './HrEmploymentIdentityCompact'
import { openHrDocumentInNewTab } from '../../utils/hrDocumentOpen'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'

type Props = {
  panel: HrReviewPanel
  employeeId?: string
  handoffId?: string
  manage?: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
}

const STATUS_CLASS: Record<string, string> = {
  verified: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  overridden: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  pending: 'bg-amber-50 text-amber-900 ring-amber-200',
  missing: 'bg-slate-100 text-slate-600 ring-slate-200',
  conflict: 'bg-rose-50 text-rose-900 ring-rose-200',
}

function statusLabel(status: string): string {
  return status.replace(/_/g, ' ')
}

export default function HrDataVerificationWorkspace({
  panel,
  employeeId,
  handoffId,
  manage = false,
  onPanelUpdated,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const items = panel.data_verification_items ?? []
  const summary = panel.data_verification_summary
  const docs = panel.documents_for_approval ?? []

  const [busy, setBusy] = useState<string | null>(null)
  const [correctItem, setCorrectItem] = useState<HrDataVerificationItem | null>(null)
  const [correctValue, setCorrectValue] = useState('')
  const [correctReason, setCorrectReason] = useState('')
  const [showDocSignoff, setShowDocSignoff] = useState(false)

  const docsByKey = useMemo(() => {
    const m = new Map<string, HrReviewDocumentRow>()
    for (const d of docs) m.set(d.document_key, d)
    return m
  }, [docs])

  const pendingDocSignoff = useMemo(
    () =>
      docs.filter(
        (d) =>
          d.document_id &&
          !['verified'].includes(String(d.verification_status || d.status).toLowerCase()),
      ),
    [docs],
  )

  const runPanel = async (key: string, fn: () => Promise<HrReviewPanel>) => {
    setBusy(key)
    try {
      const next = await fn()
      onPanelUpdated?.(next)
      notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: e instanceof Error ? e.message : t('common.errors.request_failed'),
      })
    } finally {
      setBusy(null)
    }
  }

  const confirmItem = async (item: HrDataVerificationItem) => {
    const docKey = item.source_document_type
    if (!docKey) return
    const doc = docsByKey.get(docKey)
    const value = (item.recruiter_value || item.current_verified_value || '').trim()
    const existing = (doc?.reviewed_fields?.[item.field_code] as Record<string, unknown> | undefined) || {}
    const reviewed_fields: Record<string, unknown> = {
      ...(doc?.reviewed_fields || {}),
      [item.field_code]: {
        ...existing,
        value,
        confirmed: true,
        comment: existing.comment ?? '',
      },
    }
    await runPanel(`confirm-${item.field_code}`, () =>
      postHrDocumentReviewed({
        employeeId,
        handoffId,
        documentKey: docKey,
        reviewed_fields,
      }),
    )
  }

  const submitCorrect = async () => {
    if (!correctItem) return
    const value = correctValue.trim()
    const reason = correctReason.trim()
    if (!value) return

    if (correctItem.status === 'verified' || correctItem.status === 'overridden') {
      if (!reason) return
      await runPanel(`override-${correctItem.field_code}`, () =>
        postHrVerifiedFieldOverride({
          employeeId,
          handoffId,
          fieldCode: correctItem.field_code,
          verified_value: value,
          override_reason: reason,
        }),
      )
    } else {
      const docKey = correctItem.source_document_type
      if (!docKey) return
      const doc = docsByKey.get(docKey)
      const existing = (doc?.reviewed_fields?.[correctItem.field_code] as Record<string, unknown> | undefined) || {}
      const reviewed_fields: Record<string, unknown> = {
        ...(doc?.reviewed_fields || {}),
        [correctItem.field_code]: {
          ...existing,
          value,
          confirmed: true,
          comment: reason || existing.comment || '',
        },
      }
      await runPanel(`correct-${correctItem.field_code}`, () =>
        postHrDocumentReviewed({
          employeeId,
          handoffId,
          documentKey: docKey,
          reviewed_fields,
        }),
      )
    }
    setCorrectItem(null)
    setCorrectValue('')
    setCorrectReason('')
  }

  const openDocument = async (item: HrDataVerificationItem) => {
    const url = item.document_open_url
    if (!url) return
    const docKey = item.source_document_type
    if (!manage || !docKey) {
      await openHrDocumentInNewTab({ openUrl: url })
      return
    }
    setBusy(`open-${item.field_code}`)
    try {
      await openHrDocumentInNewTab({ openUrl: url })
      const next = await postHrDocumentOpened({ employeeId, handoffId, documentKey: docKey })
      onPanelUpdated?.(next)
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: e instanceof Error ? e.message : t('common.errors.request_failed'),
      })
    } finally {
      setBusy(null)
    }
  }

  const requestCorrection = async (item: HrDataVerificationItem) => {
    const docKey = item.source_document_type
    if (!docKey) return
    const note = t('app.hr.data_verify.request_note', {
      defaultValue: 'Please provide or correct: {field}',
      values: { field: item.label },
    })
    await runPanel(`correction-${item.field_code}`, () =>
      postHrDocumentRequestCorrection({
        employeeId,
        handoffId,
        documentKey: docKey,
        note,
      }),
    )
  }

  if (items.length === 0 && docs.length === 0) return null

  return (
    <section id="hr-data-verification" className="scroll-mt-24 space-y-3">
      <div className="rounded-xl border border-brand-200 bg-white shadow-sm">
        <div className="border-b border-brand-100 bg-brand-50/60 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('app.hr.data_verify.title', { defaultValue: 'Data & document verification' })}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.hr.data_verify.hint', {
              defaultValue:
                'Confirm recruiter-provided values against documents. Verified data becomes the source for contracts, ZUS, and payroll.',
            })}
          </p>
          {summary ? (
            <p className="mt-2 text-xs text-slate-600">
              {t('app.hr.data_verify.progress', {
                defaultValue: 'Verified {verified}/{total} · critical {criticalVerified}/{criticalTotal}',
                values: {
                  verified: summary.verified_count,
                  total: summary.total,
                  criticalVerified: summary.critical_verified,
                  criticalTotal: summary.critical_total,
                },
              })}
              {summary.documents_missing > 0
                ? ` · ${t('app.hr.data_verify.docs_missing', { defaultValue: 'documents missing' })}: ${summary.documents_missing}`
                : ''}
            </p>
          ) : null}
        </div>

        <div className="px-4 py-3">
          <HrEmploymentIdentityCompact panel={panel} />
        </div>

        {items.length > 0 ? (
          <div className="overflow-x-auto px-2 pb-4">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">{t('app.hr.data_verify.col_field', { defaultValue: 'Field' })}</th>
                  <th className="px-3 py-2">
                    {t('app.hr.data_verify.col_recruiter', { defaultValue: 'Recruiter data' })}
                  </th>
                  <th className="px-3 py-2">{t('app.hr.data_verify.col_document', { defaultValue: 'Document' })}</th>
                  <th className="px-3 py-2">{t('app.hr.data_verify.col_status', { defaultValue: 'Status' })}</th>
                  <th className="px-3 py-2">{t('app.hr.data_verify.col_actions', { defaultValue: 'Actions' })}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {items.map((item) => (
                  <tr key={item.field_code} className="align-top">
                    <td className="px-3 py-3">
                      <span className="font-medium text-slate-900">{item.label}</span>
                      {item.required_for_approval ? (
                        <span className="ml-1 text-[10px] uppercase text-rose-600">required</span>
                      ) : null}
                      {(item.used_for?.length ?? 0) > 0 ? (
                        <p className="mt-0.5 text-[11px] text-slate-500">{item.used_for?.join(', ')}</p>
                      ) : null}
                    </td>
                    <td className="px-3 py-3 text-slate-800">
                      {item.recruiter_value ? (
                        item.recruiter_value
                      ) : (
                        <span className="italic text-slate-400">
                          {t('app.hr.data_verify.empty', { defaultValue: 'empty' })}
                        </span>
                      )}
                      {Object.entries(item.recruiter_profile_values || {}).length > 1 ? (
                        <ul className="mt-1 space-y-0.5 text-[11px] text-slate-500">
                          {Object.entries(item.recruiter_profile_values || {}).map(([k, v]) => (
                            <li key={k}>
                              <span className="text-slate-400">{k.replace(/^handoff\./, 'handoff · ')}: </span>
                              {String(v)}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                      {item.current_verified_value && item.current_verified_value !== item.recruiter_value ? (
                        <p className="mt-0.5 text-xs text-emerald-800">Verified: {item.current_verified_value}</p>
                      ) : null}
                    </td>
                    <td className="px-3 py-3 text-slate-600">
                      {item.source_document_label || item.source_document_type || '—'}
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={clsx(
                          'inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
                          STATUS_CLASS[item.status] ?? STATUS_CLASS.pending,
                        )}
                      >
                        {statusLabel(item.status)}
                      </span>
                      {item.conflict_reason ? (
                        <p className="mt-1 text-xs text-amber-800">{item.conflict_reason}</p>
                      ) : null}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {item.document_open_url ? (
                          <button
                            type="button"
                            className="rounded border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50"
                            disabled={!!busy}
                            onClick={() => void openDocument(item)}
                          >
                            {t('app.hr.data_verify.open_doc', { defaultValue: 'Open document' })}
                          </button>
                        ) : null}
                        {manage && item.can_confirm ? (
                          <button
                            type="button"
                            className="rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-900 hover:bg-emerald-100"
                            disabled={!!busy}
                            onClick={() => void confirmItem(item)}
                          >
                            {t('app.hr.data_verify.confirm', { defaultValue: 'Confirm' })}
                          </button>
                        ) : null}
                        {manage && item.can_correct ? (
                          <button
                            type="button"
                            className="rounded border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50"
                            disabled={!!busy}
                            onClick={() => {
                              setCorrectItem(item)
                              setCorrectValue(item.recruiter_value || item.current_verified_value || '')
                              setCorrectReason('')
                            }}
                          >
                            {t('app.hr.data_verify.correct', { defaultValue: 'Correct' })}
                          </button>
                        ) : null}
                        {manage && item.can_request_info ? (
                          <button
                            type="button"
                            className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900"
                            disabled={!!busy}
                            onClick={() => void requestCorrection(item)}
                          >
                            {t('app.hr.data_verify.request_info', { defaultValue: 'Request info' })}
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {pendingDocSignoff.length > 0 ? (
          <div className="border-t border-slate-100 px-4 py-3">
            <button
              type="button"
              className="text-sm font-medium text-brand-700 hover:underline"
              onClick={() => setShowDocSignoff((v) => !v)}
            >
              {showDocSignoff
                ? t('app.hr.data_verify.hide_doc_signoff', { defaultValue: 'Hide document sign-off' })
                : t('app.hr.data_verify.show_doc_signoff', {
                    defaultValue: 'Document sign-off ({count})',
                    values: { count: pendingDocSignoff.length },
                  })}
            </button>
            {showDocSignoff ? (
              <div className="mt-3 space-y-3">
                {pendingDocSignoff.map((d) => (
                  <HrDocumentVerificationCard
                    key={d.document_key}
                    doc={d}
                    employeeId={employeeId}
                    handoffId={handoffId}
                    manage={manage}
                    onPanelUpdated={onPanelUpdated}
                  />
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {correctItem ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-4 shadow-xl">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('app.hr.data_verify.correct_title', { defaultValue: 'Correct value' })}: {correctItem.label}
            </h3>
            <input
              className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={correctValue}
              onChange={(e) => setCorrectValue(e.target.value)}
            />
            <input
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder={t('app.hr.data_verify.reason', { defaultValue: 'Reason / comment' })}
              value={correctReason}
              onChange={(e) => setCorrectReason(e.target.value)}
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="btn-secondary btn-sm" onClick={() => setCorrectItem(null)}>
                {t('common.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={!!busy || !correctValue.trim()}
                onClick={() => void submitCorrect()}
              >
                {t('common.save', { defaultValue: 'Save' })}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
