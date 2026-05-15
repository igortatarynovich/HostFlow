/**
 * HR work-eligibility pipeline: CRM-style step cards (no raw JSON / admin tables).
 * Visual patterns aligned with EmployeeWorkforceJourneyPanel + CandidateStageJourneyPanel.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactElement, type ReactNode } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import {
  getWorkEligibilityJourney,
  type WorkEligibilityJourney,
  type WorkEligibilityJourneyStep,
  type WorkforceHrDocumentContextSummary,
  type WorkforceHrDocumentContextRow,
  type WorkforceTimelineEvent,
  type WorkforceWorkEligibilityPaymentRequirement,
  type WorkforceWorkEligibilityProfile,
} from '../../api/workforce'

const ELIGIBILITY_STATUS_OPTIONS: { value: string; labelKey: string; defaultLabel: string }[] = [
  { value: 'not_evaluated', labelKey: 'app.hr.work_eligibility.opt.not_evaluated', defaultLabel: 'Not evaluated' },
  {
    value: 'missing_legal_stay',
    labelKey: 'app.hr.work_eligibility.opt.missing_legal_stay',
    defaultLabel: 'Missing legal stay',
  },
  {
    value: 'work_permit_required',
    labelKey: 'app.hr.work_eligibility.opt.work_permit_required',
    defaultLabel: 'Work permit required',
  },
  {
    value: 'work_permit_pending',
    labelKey: 'app.hr.work_eligibility.opt.work_permit_pending',
    defaultLabel: 'Work permit pending',
  },
  { value: 'ready_for_zus', labelKey: 'app.hr.work_eligibility.opt.ready_for_zus', defaultLabel: 'Ready for ZUS' },
  { value: 'eligible_to_work', labelKey: 'app.hr.work_eligibility.opt.eligible_to_work', defaultLabel: 'Eligible to work' },
  { value: 'blocked', labelKey: 'app.hr.work_eligibility.opt.blocked', defaultLabel: 'Blocked' },
]

function paymentRowForStep(
  step: WorkEligibilityJourneyStep,
  payments: WorkforceWorkEligibilityPaymentRequirement[],
): WorkforceWorkEligibilityPaymentRequirement | null {
  if (step.linked_payment_requirement_id) {
    return payments.find((p) => p.id === step.linked_payment_requirement_id) ?? null
  }
  if (step.step_code === 'work_permit_fee') {
    return payments.find((p) => p.requirement_type === 'work_permit_fee') ?? null
  }
  if (step.step_code === 'red_paper_fee') {
    return payments.find((p) => p.requirement_type === 'red_paper_fee') ?? null
  }
  return null
}

function docsForStep(
  stepCode: string,
  items: WorkforceHrDocumentContextRow[],
): { attached: WorkforceHrDocumentContextRow[]; suggested: string[] } {
  const s = stepCode.toLowerCase()
  const keys: string[] = []
  if (s.includes('legal')) keys.push('legal', 'stay', 'residence')
  if (s.includes('permit') && !s.includes('fee')) keys.push('permit', 'work_permit', 'zezwolenie')
  if (s.includes('red')) keys.push('red', 'niekar', 'criminal')
  if (s.includes('zus')) keys.push('zus', 'social')
  const attached = items.filter((it) => {
    const g = `${it.document_group || ''} ${it.context_type || ''} ${it.legal_category || ''}`.toLowerCase()
    return keys.some((k) => g.includes(k))
  })
  const suggested: string[] = []
  if (stepCode === 'legal_stay') suggested.push('Legal stay / residence proof')
  if (stepCode.includes('work_permit') && !stepCode.includes('fee')) suggested.push('Work permit decision / card')
  if (stepCode.includes('red')) suggested.push('Criminal record certificate (red paper)')
  return { attached, suggested }
}

function formatShortDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const ms = Date.parse(iso)
  if (!Number.isFinite(ms)) return ''
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'short' }).format(ms)
  } catch {
    return ''
  }
}

function paymentStatusLabel(t: ReturnType<typeof useI18n>['t'], raw: string | null | undefined): string {
  const k = (raw || '').trim().toLowerCase()
  if (!k) return '—'
  return t(`app.hr.work_eligibility.payment_status.${k}`, { defaultValue: raw || '—' })
}

function blockerMessage(t: ReturnType<typeof useI18n>['t'], code: string): string {
  const key = `app.hr.work_eligibility.blocker.${code}`
  const tr = t(key, { defaultValue: '' })
  if (tr && tr !== key) return tr
  return code.replace(/_/g, ' ')
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'done':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'current':
      return 'border-indigo-300 bg-indigo-50 text-indigo-900 ring-1 ring-indigo-200'
    case 'blocked':
      return 'border-rose-200 bg-rose-50 text-rose-900'
    case 'pending':
      return 'border-slate-200 bg-slate-50 text-slate-600'
    case 'not_required':
      return 'border-slate-100 bg-slate-50/80 text-slate-500'
    default:
      return 'border-slate-200 bg-slate-50 text-slate-700'
  }
}

function stepCardShell(status: string, children: ReactNode): ReactElement {
  const compact = status === 'not_required'
  return (
    <div
      className={clsx(
        'rounded-xl border transition-shadow',
        status === 'done' && 'border-emerald-100 bg-white shadow-sm',
        status === 'current' && 'border-indigo-200 bg-white shadow-md ring-1 ring-indigo-100',
        status === 'blocked' && 'border-rose-200 bg-white shadow-sm',
        status === 'pending' && 'border-slate-200 bg-slate-50/60',
        status === 'not_required' && 'border-transparent bg-transparent py-1',
      )}
    >
      <div className={clsx(!compact && 'p-3', compact && 'px-1 py-0.5')}>{children}</div>
    </div>
  )
}

function FeeStepActions({
  row,
  manage,
  saving,
  onSave,
  t,
}: {
  row: WorkforceWorkEligibilityPaymentRequirement
  manage: boolean
  saving: boolean
  onSave: (patch: Record<string, unknown>) => Promise<void>
  t: ReturnType<typeof useI18n>['t']
}) {
  const [reference, setReference] = useState(row.payment_reference || '')
  const [receiptId, setReceiptId] = useState(row.receipt_document_id || '')
  useEffect(() => {
    setReference(row.payment_reference || '')
    setReceiptId(row.receipt_document_id || '')
  }, [row.payment_reference, row.receipt_document_id, row.id])

  const paid = ['paid', 'waived', 'not_required'].includes((row.payment_status || '').toLowerCase())

  return (
    <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50/90 p-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium text-slate-700">{t('app.hr.work_eligibility.fee.state', { defaultValue: 'Fee status' })}</span>
        <span
          className={clsx(
            'inline-flex rounded-full border px-2 py-0.5 font-medium',
            paid ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-amber-200 bg-amber-50 text-amber-900',
          )}
        >
          {paymentStatusLabel(t, row.payment_status)}
        </span>
        {row.amount != null && row.amount !== '' ? (
          <span className="text-slate-600">
            {row.amount} {row.currency}
          </span>
        ) : null}
        {row.due_at ? (
          <span className="text-slate-500">
            {t('app.hr.work_eligibility.fee.due', { defaultValue: 'Due' })}: {formatShortDate(row.due_at)}
          </span>
        ) : null}
      </div>
      {row.blocks_step ? (
        <p className="text-xs text-slate-600">
          {t('app.hr.work_eligibility.fee.blocks_next', {
            defaultValue: 'Blocks next step: {step}',
            values: { step: row.blocks_step },
          })}
        </p>
      ) : null}
      {!paid && manage ? (
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-0.5 text-[11px] text-slate-600">
            {t('app.hr.work_eligibility.fee.reference', { defaultValue: 'Payment reference' })}
            <input
              className="rounded border border-slate-200 px-2 py-1 text-xs"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-0.5 text-[11px] text-slate-600">
            {t('app.hr.work_eligibility.fee.receipt_doc', { defaultValue: 'Confirmation document id' })}
            <input
              className="rounded border border-slate-200 px-2 py-1 text-xs"
              value={receiptId}
              onChange={(e) => setReceiptId(e.target.value)}
            />
          </label>
          <div className="sm:col-span-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={saving}
              className="btn-primary btn-sm"
              onClick={() =>
                void onSave({
                  payment_reference: reference.trim() || null,
                  receipt_document_id: receiptId.trim() || null,
                  payment_status: 'paid',
                })
              }
            >
              {t('app.hr.work_eligibility.mark_paid', { defaultValue: 'Mark paid' })}
            </button>
            <button type="button" disabled={saving} className="btn-secondary btn-sm" onClick={() => void onSave({ payment_status: 'waived' })}>
              {t('app.hr.work_eligibility.waive', { defaultValue: 'Waive' })}
            </button>
            <button
              type="button"
              disabled={saving}
              className="btn-secondary btn-sm"
              onClick={() =>
                void onSave({
                  payment_reference: reference.trim() || null,
                  receipt_document_id: receiptId.trim() || null,
                })
              }
            >
              {t('app.hr.work_eligibility.save_ref', { defaultValue: 'Save details' })}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

type Props = {
  employeeId: string
  profile: WorkforceWorkEligibilityProfile | null
  paymentRequirements: WorkforceWorkEligibilityPaymentRequirement[]
  docSummary: WorkforceHrDocumentContextSummary
  timeline: WorkforceTimelineEvent[]
  manage: boolean
  saving: string | null
  onSaveEligibility: (p: Record<string, unknown>) => Promise<void>
  onSavePayment: (rid: string, p: Record<string, unknown>) => Promise<void>
}

export default function WorkEligibilityJourneyWorkspace({
  employeeId,
  profile,
  paymentRequirements,
  docSummary,
  timeline,
  manage,
  saving,
  onSaveEligibility,
  onSavePayment,
}: Props) {
  const { t } = useI18n()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [journey, setJourney] = useState<WorkEligibilityJourney | null>(null)
  const [journeyLoading, setJourneyLoading] = useState(true)

  const paySig = paymentRequirements.map((r) => `${r.id}:${r.payment_status}:${r.updated_at}`).join('|')

  const reloadJourney = useCallback(async () => {
    setJourneyLoading(true)
    try {
      setJourney(await getWorkEligibilityJourney(employeeId))
    } catch {
      setJourney(null)
    } finally {
      setJourneyLoading(false)
    }
  }, [employeeId])

  useEffect(() => {
    void reloadJourney()
  }, [employeeId, profile?.updated_at, paySig, reloadJourney])

  const docItems = docSummary?.items ?? []

  const journeyEvents = useMemo(() => {
    const rx = /zus|permit|fee|eligib|document|red|work\s|legal|stay|insurance/i
    return (timeline || []).filter((e) => rx.test(`${e.title} ${e.kind} ${e.detail || ''}`)).slice(0, 6)
  }, [timeline])

  const [citizenship, setCitizenship] = useState(profile?.citizenship || '')
  const [positionCategory, setPositionCategory] = useState(profile?.position_category || '')
  const [eligibilityStatus, setEligibilityStatus] = useState(profile?.eligibility_status || 'not_evaluated')
  const [requiresPermit, setRequiresPermit] = useState<boolean>(profile?.requires_work_permit !== false)
  const [appStatus, setAppStatus] = useState(profile?.work_permit_application_status || '')
  const [redPaper, setRedPaper] = useState(profile?.red_paper_status || '')

  useEffect(() => {
    if (!profile) return
    setCitizenship(profile.citizenship || '')
    setPositionCategory(profile.position_category || '')
    setEligibilityStatus(profile.eligibility_status || 'not_evaluated')
    setRequiresPermit(profile.requires_work_permit !== false)
    setAppStatus(profile.work_permit_application_status || '')
    setRedPaper(profile.red_paper_status || '')
  }, [profile])

  const openEdit = () => dialogRef.current?.showModal()
  const closeEdit = () => dialogRef.current?.close()

  const persistProfile = async () => {
    await onSaveEligibility({
      citizenship: citizenship.trim() || null,
      position_category: positionCategory.trim() || null,
      eligibility_status: eligibilityStatus.trim() || null,
      requires_work_permit: requiresPermit,
      work_permit_application_status: appStatus.trim() || null,
      red_paper_status: redPaper.trim() || null,
    })
    await reloadJourney()
    closeEdit()
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-xs font-semibold text-slate-700">
            {t('app.hr.work_eligibility.workspace_title', { defaultValue: 'Right-to-work process' })}
          </div>
          <p className="mt-1 max-w-2xl text-[11px] text-slate-500">
            {t('app.hr.work_eligibility.workspace_hint', {
              defaultValue:
                'Operational pipeline for legal stay, permits, statutory fees, and ZUS — same card patterns as recruitment stages.',
            })}
          </p>
        </div>
        {manage && profile ? (
          <button type="button" className="btn-secondary btn-sm shrink-0" onClick={openEdit}>
            {t('app.hr.work_eligibility.edit_profile', { defaultValue: 'Edit profile' })}
          </button>
        ) : null}
      </div>

      {journeyLoading ? (
        <p className="mt-3 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : journey ? (
        <>
          <div className="mt-3 rounded-xl border border-indigo-100 bg-indigo-50/60 px-3 py-2.5 text-sm text-indigo-950">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-indigo-800">
              {t('app.hr.work_eligibility.next_action', { defaultValue: 'Recommended next' })}
            </span>
            <p className="mt-1 text-sm leading-snug">{journey.recommended_next_action}</p>
          </div>

          <div className="relative mt-4 space-y-2 pl-1">
            <div className="absolute left-[11px] top-2 bottom-2 w-px bg-slate-200" aria-hidden />
            <ol className="relative space-y-2">
              {journey.steps.map((step) => {
                const payRow = paymentRowForStep(step, paymentRequirements)
                const { attached, suggested } = docsForStep(step.step_code, docItems)
                const showDocs = step.status !== 'not_required' && (attached.length > 0 || suggested.length > 0)
                const isFee = payRow && (step.step_code === 'work_permit_fee' || step.step_code === 'red_paper_fee')

                if (step.status === 'not_required') {
                  return (
                    <li key={step.step_code} className="relative flex gap-3 pl-7">
                      <span
                        className="absolute left-0 top-1.5 flex h-[22px] w-[22px] items-center justify-center rounded-full border border-slate-200 bg-white text-[10px] text-slate-400"
                        aria-hidden
                      >
                        ○
                      </span>
                      {stepCardShell(
                        step.status,
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs text-slate-500">{step.label}</span>
                          <span className={clsx('rounded-full border px-2 py-0.5 text-[10px] font-medium', statusBadgeClass(step.status))}>
                            {t('app.hr.work_eligibility.status.not_required', { defaultValue: 'Not required' })}
                          </span>
                        </div>,
                      )}
                    </li>
                  )
                }

                return (
                  <li key={step.step_code} className="relative flex gap-3 pl-7">
                    <span
                      className={clsx(
                        'absolute left-0 top-2 flex h-[22px] w-[22px] items-center justify-center rounded-full border-2 bg-white text-[10px] font-bold',
                        step.status === 'done' && 'border-emerald-400 text-emerald-600',
                        step.status === 'current' && 'border-indigo-500 text-indigo-600',
                        step.status === 'blocked' && 'border-rose-400 text-rose-600',
                        step.status === 'pending' && 'border-slate-300 text-slate-500',
                      )}
                      aria-hidden
                    >
                      {step.status === 'done' ? '✓' : ''}
                    </span>
                    {stepCardShell(
                      step.status,
                      <>
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <div className="text-sm font-semibold text-slate-900">{step.label}</div>
                            {step.action_label ? <p className="mt-0.5 text-xs text-slate-600">{step.action_label}</p> : null}
                          </div>
                          <span className={clsx('shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] font-medium', statusBadgeClass(step.status))}>
                            {step.status === 'done' && t('app.hr.work_eligibility.status.done', { defaultValue: 'Completed' })}
                            {step.status === 'current' && t('app.hr.work_eligibility.status.current', { defaultValue: 'In focus' })}
                            {step.status === 'blocked' && t('app.hr.work_eligibility.status.blocked', { defaultValue: 'Blocked' })}
                            {step.status === 'pending' && t('app.hr.work_eligibility.status.pending', { defaultValue: 'Waiting' })}
                          </span>
                        </div>
                        {(step.blockers?.length ?? 0) > 0 ? (
                          <ul className="mt-2 list-inside list-disc text-xs text-rose-800">
                            {(step.blockers ?? []).map((b) => (
                              <li key={b}>{blockerMessage(t, b)}</li>
                            ))}
                          </ul>
                        ) : null}
                        {step.external_submission_url ? (
                          <div className="mt-2">
                            <a href={step.external_submission_url} target="_blank" rel="noreferrer" className="btn-secondary btn-sm inline-flex">
                              {t('app.hr.work_eligibility.open_portal', { defaultValue: 'Open submission portal' })}
                            </a>
                          </div>
                        ) : null}
                        {showDocs ? (
                          <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50/80 p-2">
                            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                              {t('app.hr.work_eligibility.docs.title', { defaultValue: 'Documents' })}
                            </div>
                            {attached.length ? (
                              <ul className="mt-1 space-y-1">
                                {attached.map((d) => (
                                  <li key={d.id} className="flex flex-wrap items-center gap-2 text-xs text-slate-800">
                                    <span
                                      className={clsx(
                                        'rounded-full border px-2 py-0.5 text-[10px] font-medium',
                                        d.verified ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-slate-200 bg-white text-slate-600',
                                      )}
                                    >
                                      {d.verified
                                        ? t('app.hr.work_eligibility.docs.verified', { defaultValue: 'Verified' })
                                        : t('app.hr.work_eligibility.docs.unverified', { defaultValue: 'Unverified' })}
                                    </span>
                                    <span>{d.context_type || d.document_group || 'Document'}</span>
                                    {d.expires_at ? (
                                      <span className="text-slate-500">
                                        {t('app.hr.work_eligibility.docs.expires', { defaultValue: 'Expires' })}:{' '}
                                        {formatShortDate(d.expires_at)}
                                      </span>
                                    ) : null}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="mt-1 text-xs text-amber-800">
                                {t('app.hr.work_eligibility.docs.missing_hint', {
                                  defaultValue: 'No matching documents linked yet — upload via the documents section.',
                                })}
                              </p>
                            )}
                            {suggested.length > 0 && !attached.length ? (
                              <ul className="mt-1 text-xs text-slate-600">
                                {suggested.map((s) => (
                                  <li key={s}>• {s}</li>
                                ))}
                              </ul>
                            ) : null}
                          </div>
                        ) : null}
                        {isFee && payRow ? (
                          <FeeStepActions
                            row={payRow}
                            manage={manage}
                            saving={saving === `wel_pay_${payRow.id}`}
                            onSave={async (patch) => {
                              await onSavePayment(payRow.id, patch)
                              await reloadJourney()
                            }}
                            t={t}
                          />
                        ) : null}
                      </>,
                    )}
                  </li>
                )
              })}
            </ol>
          </div>

          {journeyEvents.length > 0 ? (
            <div className="mt-5 border-t border-slate-100 pt-3">
              <div className="text-xs font-semibold text-slate-700">
                {t('app.hr.work_eligibility.related_activity', { defaultValue: 'Related activity' })}
              </div>
              <ul className="mt-2 space-y-1.5">
                {journeyEvents.map((ev) => (
                  <li key={ev.id} className="flex flex-wrap gap-2 text-xs text-slate-700">
                    <span className="text-slate-500">{formatShortDate(ev.occurred_at)}</span>
                    <span className="font-medium">{ev.title}</span>
                    {ev.detail ? <span className="text-slate-500">— {ev.detail}</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : (
        <p className="mt-3 text-sm text-rose-700">{t('app.hr.work_eligibility.journey_error', { defaultValue: 'Could not load journey.' })}</p>
      )}

      <dialog ref={dialogRef} className="max-w-lg rounded-xl border border-slate-200 bg-white p-0 shadow-xl backdrop:bg-slate-900/40">
        <div className="border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.hr.work_eligibility.edit_title', { defaultValue: 'Work eligibility profile' })}
          </h2>
          <p className="mt-0.5 text-[11px] text-slate-500">
            {t('app.hr.work_eligibility.edit_subtitle', {
              defaultValue: 'Citizenship, role, permit flags, and statuses used by the pipeline above.',
            })}
          </p>
        </div>
        <div className="max-h-[70vh] overflow-y-auto px-4 py-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-xs text-slate-600">
              {t('app.hr.work_eligibility.citizenship', { defaultValue: 'Citizenship (ISO2)' })}
              <input
                className="rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={citizenship}
                onChange={(e) => setCitizenship(e.target.value.toUpperCase())}
                maxLength={8}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-600">
              {t('app.hr.work_eligibility.position', { defaultValue: 'Position category' })}
              <input
                className="rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={positionCategory}
                onChange={(e) => setPositionCategory(e.target.value)}
                placeholder="driver"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
              {t('app.hr.work_eligibility.field_eligibility_status', { defaultValue: 'Eligibility status' })}
              <select
                className="rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={eligibilityStatus}
                onChange={(e) => setEligibilityStatus(e.target.value)}
              >
                {ELIGIBILITY_STATUS_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {t(o.labelKey, { defaultValue: o.defaultLabel })}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-600 sm:col-span-2">
              <input type="checkbox" checked={requiresPermit} onChange={(e) => setRequiresPermit(e.target.checked)} />
              {t('app.hr.work_eligibility.requires_permit', { defaultValue: 'Requires work permit' })}
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
              {t('app.hr.work_eligibility.permit_app', { defaultValue: 'Work permit application status' })}
              <input className="rounded border border-slate-200 px-2 py-1.5 text-sm" value={appStatus} onChange={(e) => setAppStatus(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
              {t('app.hr.work_eligibility.red_paper', { defaultValue: 'Red paper status' })}
              <input className="rounded border border-slate-200 px-2 py-1.5 text-sm" value={redPaper} onChange={(e) => setRedPaper(e.target.value)} />
            </label>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-4 py-3">
          <button type="button" className="btn-secondary btn-sm" onClick={closeEdit}>
            {t('common.actions.cancel', { defaultValue: 'Cancel' })}
          </button>
          <button type="button" className="btn-primary btn-sm" disabled={saving === 'work_eligibility'} onClick={() => void persistProfile()}>
            {t('app.hr.employee_detail.save', { defaultValue: 'Save' })}
          </button>
        </div>
      </dialog>
    </section>
  )
}
