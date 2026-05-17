import clsx from 'clsx'
import { useCallback, useState } from 'react'

import { approveHandoffHrReview, patchHandoffHrReviewChecklistItem } from '../../api/hrWorkspace'
import {
  approveWorkforceHrReview,
  patchWorkforceHrReviewChecklistItem,
  rejectWorkforceHrReview,
  requestWorkforceHrReviewCorrections,
  returnWorkforceHrReviewToRecruitment,
  type HrReviewDocumentRow,
  type HrReviewPanel,
} from '../../api/workforce'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import HrDocumentOpenButton from './HrDocumentOpenButton'

const TERMINAL = new Set(['approved_for_employment', 'returned_to_recruitment', 'rejected_by_hr'])

function statusLabel(t: ReturnType<typeof useI18n>['t'], status: string): string {
  const key = `app.hr.review.status.${status}`
  const tr = t(key, { defaultValue: '' })
  return tr && tr !== key ? tr : status.replace(/_/g, ' ')
}

type Props = {
  panel: HrReviewPanel
  manage: boolean
  onUpdated: (p: HrReviewPanel) => void
  employeeId?: string
  handoffId?: string
  hideDocuments?: boolean
}

function docStatusLabel(t: ReturnType<typeof useI18n>['t'], d: HrReviewDocumentRow): string {
  const raw = String(d.status || '').toLowerCase()
  if (d.verified || raw === 'verified') {
    return t('app.hr.review.doc_status.verified', { defaultValue: 'Verified' })
  }
  if (raw === 'missing') return t('app.hr.review.doc_status.missing', { defaultValue: 'Missing' })
  if (raw === 'needs_data') return t('app.hr.review.doc_status.needs_data', { defaultValue: 'Needs data' })
  if (raw === 'uploaded' || raw === 'pending') {
    return t('app.hr.review.doc_status.pending', { defaultValue: 'Awaiting verification' })
  }
  if (raw.includes('expir')) return t('app.hr.review.doc_status.expiring', { defaultValue: 'Expiring' })
  return raw.replace(/_/g, ' ') || '—'
}

function docPrimaryAction(
  t: ReturnType<typeof useI18n>['t'],
  d: HrReviewDocumentRow,
): { label: string; href: string } {
  const raw = String(d.status || '').toLowerCase()
  const base = '#hr-employee-linked-documents'
  if (d.verified || raw === 'verified') {
    return { label: t('app.hr.review.open_docs', { defaultValue: 'Open' }), href: base }
  }
  if (raw === 'missing') {
    return { label: t('app.hr.review.upload_docs', { defaultValue: 'Upload' }), href: base }
  }
  if (raw === 'uploaded' || raw === 'pending') {
    return { label: t('app.hr.review.verify_docs', { defaultValue: 'Verify' }), href: base }
  }
  return { label: t('app.hr.review.open_docs', { defaultValue: 'Open' }), href: base }
}

export default function HrReviewPanelCard({
  panel,
  manage,
  onUpdated,
  employeeId: employeeIdProp,
  handoffId,
  hideDocuments = false,
}: Props) {
  const employeeId = (employeeIdProp || panel.employee_id || '').trim()
  const useHandoffApi = Boolean(handoffId) && !employeeId
  const { t } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const [returnReason, setReturnReason] = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [correctionsNote, setCorrectionsNote] = useState('')
  const [showReturn, setShowReturn] = useState(false)
  const [showReject, setShowReject] = useState(false)
  const [showCorrections, setShowCorrections] = useState(false)

  const terminal = TERMINAL.has(panel.status)
  const canEmployeeActions = Boolean(employeeId)

  const patchChecklist = useCallback(
    (itemCode: string, satisfied: boolean) => {
      if (useHandoffApi && handoffId) {
        return patchHandoffHrReviewChecklistItem(handoffId, itemCode, satisfied)
      }
      return patchWorkforceHrReviewChecklistItem(employeeId, itemCode, satisfied)
    },
    [employeeId, handoffId, useHandoffApi],
  )

  const approveReview = useCallback(() => {
    if (useHandoffApi && handoffId) {
      return approveHandoffHrReview(handoffId)
    }
    return approveWorkforceHrReview(employeeId)
  }, [employeeId, handoffId, useHandoffApi])

  const run = useCallback(
    async (fn: () => Promise<HrReviewPanel>) => {
      setBusy(true)
      try {
        const next = await fn()
        onUpdated(next)
        notify({ title: t('app.hr.review.action_ok', { defaultValue: 'HR review updated' }), variant: 'success' })
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
        if (detail && typeof detail === 'object' && !Array.isArray(detail) && (detail as { code?: string }).code === 'HR_REVIEW_BLOCKED') {
          const d = detail as { blockers?: string[]; failed_checklist_items?: string[] }
          notify({
            title: t('app.hr.review.blocked_title', { defaultValue: 'Cannot approve yet' }),
            description: [...(d.failed_checklist_items || []), ...(d.blockers || [])].filter(Boolean).join(' — '),
            variant: 'error',
          })
        } else {
          const msg =
            typeof detail === 'string'
              ? detail
              : (err as Error)?.message || t('app.hr.review.action_failed', { defaultValue: 'Action failed' })
          notify({ title: String(msg), variant: 'error' })
        }
      } finally {
        setBusy(false)
      }
    },
    [notify, onUpdated, t],
  )

  return (
    <section
      id="hr-employee-review"
      tabIndex={-1}
      className="scroll-mt-24 rounded-2xl border-2 border-indigo-200 bg-gradient-to-b from-indigo-50/90 to-white p-4 shadow-sm sm:p-5 focus:outline-none"
      aria-labelledby="hr-review-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="hr-review-heading" className="text-lg font-semibold text-slate-900">
            {t('app.hr.review.title', { defaultValue: 'HR decision required' })}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.hr.review.subtitle', {
              defaultValue: 'Complete the checklist before approving this person for employment.',
            })}
          </p>
        </div>
        <span
          className={clsx(
            'rounded-full border px-3 py-1 text-xs font-semibold',
            panel.status === 'approved_for_employment' && 'border-emerald-300 bg-emerald-50 text-emerald-900',
            panel.status === 'rejected_by_hr' && 'border-rose-300 bg-rose-50 text-rose-900',
            panel.status === 'returned_to_recruitment' && 'border-slate-300 bg-slate-100 text-slate-800',
            !TERMINAL.has(panel.status) && 'border-indigo-300 bg-indigo-50 text-indigo-950',
          )}
        >
          {statusLabel(t, panel.status)}
        </span>
      </div>

      {panel.next_required_action && !terminal ? (
        <p className="mt-3 text-sm font-medium text-slate-800">
          {t('app.hr.review.next_action', { defaultValue: 'Next' })}: {panel.next_required_action}
        </p>
      ) : null}

      {panel.blockers.length > 0 && !terminal ? (
        <ul className="mt-2 list-inside list-disc text-xs text-rose-800">
          {panel.blockers.map((b) => (
            <li key={b}>{b.replace(/_/g, ' ')}</li>
          ))}
        </ul>
      ) : null}

      {panel.corrections_note ? (
        <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          {t('app.hr.review.corrections_note', { defaultValue: 'Corrections requested' })}: {panel.corrections_note}
        </p>
      ) : null}

      <ul className="mt-4 space-y-2">
        {panel.checklist.map((it) => {
          const ok = it.status === 'satisfied'
          return (
            <li
              key={it.item_code}
              className={clsx(
                'flex flex-wrap items-start gap-2 rounded-lg border px-3 py-2 text-sm',
                ok ? 'border-emerald-100 bg-emerald-50/50' : 'border-slate-200 bg-white',
              )}
            >
              <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-2">
                {manage && !terminal ? (
                  <input
                    type="checkbox"
                    className="mt-1 rounded border-slate-300"
                    checked={ok}
                    disabled={busy}
                    onChange={(e) => void run(() => patchChecklist(it.item_code, e.target.checked))}
                  />
                ) : (
                  <span className="mt-0.5 text-xs">{ok ? '✓' : '○'}</span>
                )}
                <span>
                  <span className="font-medium text-slate-900">{it.label}</span>
                  <span className="ml-2 text-[10px] uppercase text-slate-500">{it.source}</span>
                </span>
              </label>
            </li>
          )
        })}
      </ul>

      {!hideDocuments && panel.documents_for_approval.length > 0 ? (
        <div className="mt-4 rounded-xl border border-slate-200 bg-white/80 p-3">
          <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-600">
            {t('app.hr.review.docs_title', { defaultValue: 'Documents for approval' })}
          </h3>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-1 pr-2">{t('app.hr.review.doc_col', { defaultValue: 'Document' })}</th>
                  <th className="py-1 pr-2">{t('app.hr.review.status_col', { defaultValue: 'Status' })}</th>
                  <th className="py-1">{t('app.hr.review.action_col', { defaultValue: 'Action' })}</th>
                </tr>
              </thead>
              <tbody>
                {panel.documents_for_approval.map((d) => {
                  const action = docPrimaryAction(t, d)
                  return (
                    <tr key={d.document_key} className="border-b border-slate-50 last:border-0">
                      <td className="py-1.5 pr-2 font-medium text-slate-800">{d.label}</td>
                      <td className="py-1.5 pr-2">
                        <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium">
                          {docStatusLabel(t, d)}
                        </span>
                      </td>
                      <td className="py-1.5">
                        <div className="flex flex-wrap gap-2">
                          {d.document_id ? (
                            <HrDocumentOpenButton
                              documentId={d.document_id}
                              employeeId={employeeId}
                              label={action.label}
                            />
                          ) : (
                            <a href={action.href} className="font-medium text-brand-700 hover:underline">
                              {action.label}
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {manage && !terminal ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-primary btn-sm"
            disabled={busy || !panel.can_approve}
            onClick={() => void run(() => approveReview())}
          >
            {t('app.hr.review.approve', { defaultValue: 'Approve for employment' })}
          </button>
          {canEmployeeActions ? (
            <>
              <button type="button" className="btn-secondary btn-sm" disabled={busy} onClick={() => setShowCorrections((x) => !x)}>
                {t('app.hr.review.request_corrections', { defaultValue: 'Request corrections' })}
              </button>
              <button type="button" className="btn-secondary btn-sm" disabled={busy} onClick={() => setShowReturn((x) => !x)}>
                {t('app.hr.review.return', { defaultValue: 'Return to recruitment' })}
              </button>
              <button
                type="button"
                className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-sm font-semibold text-rose-900 hover:bg-rose-100 disabled:opacity-50"
                disabled={busy}
                onClick={() => setShowReject((x) => !x)}
              >
                {t('app.hr.review.reject', { defaultValue: 'Reject' })}
              </button>
            </>
          ) : null}
        </div>
      ) : null}

      {showCorrections && manage && !terminal && canEmployeeActions ? (
        <ReasonForm
          value={correctionsNote}
          onChange={setCorrectionsNote}
          busy={busy}
          label={t('app.hr.review.corrections_placeholder', { defaultValue: 'What must be fixed?' })}
          submitLabel={t('app.hr.review.send_corrections', { defaultValue: 'Send correction request' })}
          onSubmit={() =>
            void run(async () => {
              const p = await requestWorkforceHrReviewCorrections(employeeId, correctionsNote.trim())
              setShowCorrections(false)
              return p
            })
          }
        />
      ) : null}

      {showReturn && manage && !terminal && canEmployeeActions ? (
        <ReasonForm
          value={returnReason}
          onChange={setReturnReason}
          busy={busy}
          label={t('app.hr.review.return_reason', { defaultValue: 'Return reason' })}
          submitLabel={t('app.hr.review.confirm_return', { defaultValue: 'Confirm return' })}
          onSubmit={() =>
            void run(async () => {
              const p = await returnWorkforceHrReviewToRecruitment(employeeId, returnReason.trim())
              setShowReturn(false)
              return p
            })
          }
        />
      ) : null}

      {showReject && manage && !terminal && canEmployeeActions ? (
        <ReasonForm
          value={rejectReason}
          onChange={setRejectReason}
          busy={busy}
          label={t('app.hr.review.reject_reason', { defaultValue: 'Reject reason' })}
          submitLabel={t('app.hr.review.confirm_reject', { defaultValue: 'Confirm reject' })}
          onSubmit={() =>
            void run(async () => {
              const p = await rejectWorkforceHrReview(employeeId, rejectReason.trim())
              setShowReject(false)
              return p
            })
          }
        />
      ) : null}
    </section>
  )
}

function ReasonForm({
  value,
  onChange,
  busy,
  label,
  submitLabel,
  onSubmit,
}: {
  value: string
  onChange: (v: string) => void
  busy: boolean
  label: string
  submitLabel: string
  onSubmit: () => void
}) {
  return (
    <div className="mt-3 space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <label className="block text-xs font-medium text-slate-700">
        {label}
        <textarea className="input mt-1 min-h-[3rem] w-full text-sm" value={value} onChange={(e) => onChange(e.target.value)} />
      </label>
      <button type="button" className="btn-secondary btn-sm" disabled={busy || !value.trim()} onClick={onSubmit}>
        {submitLabel}
      </button>
    </div>
  )
}
