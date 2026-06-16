import { useState } from 'react'
import clsx from 'clsx'
import {
  rejectWorkforceHrReview,
  requestWorkforceHrReviewCorrections,
  returnWorkforceHrReviewToRecruitment,
  type HrReviewPanel,
} from '../../api/workforce'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'

const TERMINAL = new Set(['approved_for_employment', 'returned_to_recruitment', 'rejected_by_hr'])

type Props = {
  employeeId: string
  hrReview: HrReviewPanel
  manage: boolean
  allDocsConfirmed: boolean
  onPanelUpdated: (panel: HrReviewPanel) => void
  onScrollTo?: (anchor: string) => void
}

function ReasonForm({
  label,
  submitLabel,
  value,
  onChange,
  busy,
  onSubmit,
  onCancel,
  variant = 'default',
}: {
  label: string
  submitLabel: string
  value: string
  onChange: (v: string) => void
  busy: boolean
  onSubmit: () => void
  onCancel: () => void
  variant?: 'default' | 'danger'
}) {
  return (
    <div className="mt-3 space-y-2">
      <label className="block text-xs font-medium text-slate-700">{label}</label>
      <textarea
        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
        rows={3}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={busy}
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={clsx('btn-sm', variant === 'danger' ? 'rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-sm font-semibold text-rose-900 hover:bg-rose-100 disabled:opacity-50' : 'btn-primary')}
          disabled={busy || !value.trim()}
          onClick={onSubmit}
        >
          {submitLabel}
        </button>
        <button type="button" className="btn-secondary btn-sm" disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  )
}

export function EmployeeDossierHrActions({
  employeeId,
  hrReview,
  manage,
  allDocsConfirmed,
  onPanelUpdated,
  onScrollTo,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [showReturn, setShowReturn] = useState(false)
  const [showCorrections, setShowCorrections] = useState(false)
  const [showReject, setShowReject] = useState(false)
  const [returnReason, setReturnReason] = useState('')
  const [correctionsNote, setCorrectionsNote] = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [busy, setBusy] = useState(false)

  const terminal = TERMINAL.has(hrReview.status)
  const na = hrReview.next_action

  const scrollTo = (anchor?: string | null) => {
    if (!anchor) return
    const href = anchor.startsWith('#') ? anchor : `#${anchor}`
    if (onScrollTo) onScrollTo(href)
    else document.querySelector(href)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const runAction = async (fn: () => Promise<HrReviewPanel>, successTitle: string) => {
    setBusy(true)
    try {
      const next = await fn()
      onPanelUpdated(next)
      notify({ variant: 'success', title: successTitle })
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: e instanceof Error ? e.message : t('common.errors.request_failed'),
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      {hrReview.status === 'returned_to_recruitment' ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          {t('app.hr.decisions.frozen_returned', {
            defaultValue: 'Case returned to recruitment. Verification is read-only until the package is updated.',
          })}
          {hrReview.return_reason ? (
            <p className="mt-1 text-xs text-slate-600">{hrReview.return_reason}</p>
          ) : null}
        </div>
      ) : null}

      {hrReview.status === 'rejected_by_hr' ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {t('app.hr.decisions.frozen_rejected', {
            defaultValue: 'Candidate rejected. This review is closed.',
          })}
          {hrReview.reject_reason ? (
            <p className="mt-1 text-xs text-rose-800">{hrReview.reject_reason}</p>
          ) : null}
        </div>
      ) : null}

      {allDocsConfirmed && na ? (
        <section className="rounded-xl border border-brand-200 bg-gradient-to-b from-brand-50/80 to-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-900">
            {t('app.hr.dossier.next_step_title', { defaultValue: 'Next step' })}
          </p>
          <p className="mt-2 text-base font-semibold text-slate-900">{na.title}</p>
          {na.reason ? <p className="mt-1 text-sm text-slate-600">{na.reason}</p> : null}
          {na.primary_label ? (
            <button
              type="button"
              className="btn-primary btn-sm mt-4"
              onClick={() => scrollTo(na.primary_anchor)}
            >
              {na.primary_label}
            </button>
          ) : null}
          {na.secondary_label && na.secondary_anchor ? (
            <button
              type="button"
              className="btn-secondary btn-sm mt-2 block"
              onClick={() => scrollTo(na.secondary_anchor)}
            >
              {na.secondary_label}
            </button>
          ) : null}
        </section>
      ) : null}

      {manage && !terminal ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.hr.dossier.case_actions', { defaultValue: 'Case actions' })}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={busy}
              onClick={() => {
                setShowCorrections((x) => !x)
                setShowReturn(false)
                setShowReject(false)
              }}
            >
              {t('app.hr.review.request_corrections', { defaultValue: 'Request corrections' })}
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={busy}
              onClick={() => {
                setShowReturn((x) => !x)
                setShowCorrections(false)
                setShowReject(false)
              }}
            >
              {t('app.hr.review.return', { defaultValue: 'Return to recruitment' })}
            </button>
            <button
              type="button"
              className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-sm font-semibold text-rose-900 hover:bg-rose-100 disabled:opacity-50"
              disabled={busy}
              onClick={() => {
                setShowReject((x) => !x)
                setShowReturn(false)
                setShowCorrections(false)
              }}
            >
              {t('app.hr.review.reject', { defaultValue: 'Reject' })}
            </button>
          </div>
          {showCorrections ? (
            <ReasonForm
              label={t('app.hr.review.corrections_placeholder', { defaultValue: 'What must be fixed?' })}
              submitLabel={t('app.hr.review.send_corrections', { defaultValue: 'Send correction request' })}
              value={correctionsNote}
              onChange={setCorrectionsNote}
              busy={busy}
              onCancel={() => setShowCorrections(false)}
              onSubmit={() =>
                void runAction(async () => {
                  const next = await requestWorkforceHrReviewCorrections(employeeId, correctionsNote.trim())
                  setShowCorrections(false)
                  setCorrectionsNote('')
                  return next
                }, t('app.hr.review.corrections_sent', { defaultValue: 'Correction request sent' }))
              }
            />
          ) : null}
          {showReturn ? (
            <ReasonForm
              label={t('app.hr.review.return_reason', { defaultValue: 'Return reason' })}
              submitLabel={t('app.hr.review.confirm_return', { defaultValue: 'Confirm return' })}
              value={returnReason}
              onChange={setReturnReason}
              busy={busy}
              onCancel={() => setShowReturn(false)}
              onSubmit={() =>
                void runAction(async () => {
                  const next = await returnWorkforceHrReviewToRecruitment(employeeId, returnReason.trim())
                  setShowReturn(false)
                  setReturnReason('')
                  return next
                }, t('app.hr.decisions.return_done', { defaultValue: 'Returned to recruitment' }))
              }
            />
          ) : null}
          {showReject ? (
            <ReasonForm
              label={t('app.hr.review.reject_reason', { defaultValue: 'Rejection reason' })}
              submitLabel={t('app.hr.review.confirm_reject', { defaultValue: 'Confirm rejection' })}
              value={rejectReason}
              onChange={setRejectReason}
              busy={busy}
              variant="danger"
              onCancel={() => setShowReject(false)}
              onSubmit={() =>
                void runAction(async () => {
                  const next = await rejectWorkforceHrReview(employeeId, rejectReason.trim())
                  setShowReject(false)
                  setRejectReason('')
                  return next
                }, t('app.hr.decisions.reject_done', { defaultValue: 'Candidate rejected' }))
              }
            />
          ) : null}
        </section>
      ) : null}
    </div>
  )
}
