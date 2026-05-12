import { useCallback, useEffect, useMemo, useState } from 'react'

import { confirmLeadVacancy, listVacancies, submitLeadIntakeDecision } from '../../api/client'
import type { Lead } from '../../api/types'
import { useToast } from '../Toast'
import { useI18n } from '../../i18n'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import {
  INTAKE_REJECT_REASON_CODES,
  leadStatusAllowsIntakeDecision,
  manualProcessBlockHint,
} from '../../utils/intakeResolution'
import { leadSupportsManualProcess } from '../../utils/leadCrm'
import LeadIntakeUnifiedDecisionHeader from './LeadIntakeUnifiedDecisionHeader'

type Props = {
  lead: Lead
  isServicesTenant: boolean
  onLeadUpdated: (lead: Lead) => void
  onRequestProcess?: () => void | Promise<void>
  className?: string
  /** Strip card chrome / titles — composed inside Lead Intake Workspace. */
  embedded?: boolean
  /** Hide normalized signal lines (workspace shows compact qualification separately). */
  hideQualificationLines?: boolean
  /** Only intake decisions (pool / duplicate / request info / reject) — vacancy block lives in workspace shell. */
  skipVacancyControls?: boolean
  /** Lead detail: one header + primary row above the form (no duplicate “Process” blocks). */
  composeUnifiedHeader?: boolean
  processBusy?: boolean
  routingBusy?: boolean
  poolBusy?: boolean
  onConfirmRouting?: (vacancyId: string, thenProcess: boolean) => void
  onPickVacancy?: () => void
  onPool?: () => void | Promise<void>
  /** When true, hide the vacancy dropdown block (detail: one-click confirm is enough until “change vacancy”). */
  collapseVacancySection?: boolean
}

export default function LeadIntakeResolutionPanel({
  lead,
  isServicesTenant,
  onLeadUpdated,
  onRequestProcess,
  className = '',
  embedded = false,
  hideQualificationLines = false,
  skipVacancyControls = false,
  composeUnifiedHeader = false,
  processBusy = false,
  routingBusy = false,
  poolBusy = false,
  onConfirmRouting,
  onPickVacancy,
  onPool,
  collapseVacancySection = false,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const [vacancies, setVacancies] = useState<Array<{ id: string; title: string }>>([])
  const [loadingVacancies, setLoadingVacancies] = useState(false)
  const [selectedVacancyId, setSelectedVacancyId] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [acting, setActing] = useState(false)
  const [rejectReason, setRejectReason] = useState<string>('')
  const [rejectNote, setRejectNote] = useState('')
  const [requestInfoNote, setRequestInfoNote] = useState('')
  const [confirmThenProcess, setConfirmThenProcess] = useState(true)

  const src = String(lead.source || '').toLowerCase()
  const blockHint = manualProcessBlockHint(lead)
  const srcOk =
    src === 'meta' ||
    src === 'csv_import' ||
    src === 'public-intake' ||
    lead.status === 'needs_routing' ||
    lead.status === 'duplicate_review'
  const hintOk =
    blockHint === 'VACANCY_NOT_CONFIRMED' ||
    blockHint === 'INTAKE_ROUTING_INCOMPLETE' ||
    blockHint === 'INTAKE_POOL_PATH_REQUIRED' ||
    blockHint === 'DUPLICATE_REVIEW_PENDING'
  /** Vacancy confirm + unified header: any manual-pipeline lead that still needs routing help. */
  const shellOk =
    !isServicesTenant &&
    !lead.candidate_id &&
    leadSupportsManualProcess(lead) &&
    (srcOk || hintOk)
  /** POST /intake-decision — backend only allows new | needs_routing | failed | duplicate_review */
  const showIntakeDecisions = shellOk && leadStatusAllowsIntakeDecision(lead)

  const suggestedId = lead.suggested_vacancy_id != null ? String(lead.suggested_vacancy_id) : ''
  const confirmed = Boolean(lead.vacancy_routing_confirmed)
  const currentVacancyId = lead.vacancy_id != null ? String(lead.vacancy_id) : ''

  const norm = lead.normalized && typeof lead.normalized === 'object' && !Array.isArray(lead.normalized) ? lead.normalized : {}
  const intakeRejected = useMemo(() => {
    const ir = (norm as Record<string, unknown>).intake_resolution_v1
    if (!ir || typeof ir !== 'object' || Array.isArray(ir)) return false
    return String((ir as { status?: string }).status || '')
      .trim()
      .toLowerCase() === 'rejected'
  }, [norm])

  useEffect(() => {
    if (!shellOk) return
    const initial = currentVacancyId || suggestedId
    setSelectedVacancyId(initial)
  }, [shellOk, lead.id, currentVacancyId, suggestedId])

  const loadVacancies = useCallback(async () => {
    setLoadingVacancies(true)
    try {
      const res = await listVacancies({ limit: 200, offset: 0 })
      const rows = Array.isArray(res?.items) ? res.items : Array.isArray(res) ? res : []
      setVacancies(
        rows.map((row: { id?: string; title?: string; vacancy_title?: string }) => ({
          id: String(row?.id ?? ''),
          title: String(row?.title ?? row?.vacancy_title ?? row?.id ?? ''),
        })).filter((x) => x.id),
      )
    } catch {
      setVacancies([])
    } finally {
      setLoadingVacancies(false)
    }
  }, [])

  useEffect(() => {
    if (shellOk && vacancies.length === 0 && !loadingVacancies) void loadVacancies()
  }, [shellOk, vacancies.length, loadingVacancies, loadVacancies])

  const qualificationLines = useMemo(() => {
    const lines: Array<{ label: string; value: string }> = []
    const eu = norm.experience_eu_years
    if (typeof eu === 'number') {
      lines.push({
        label: t('app.leads.detail.intake_resolution.experience_eu'),
        value: String(eu),
      })
    }
    if (typeof norm.in_poland === 'boolean') {
      lines.push({
        label: t('app.leads.detail.intake_resolution.in_poland'),
        value: norm.in_poland ? t('common.yes') : t('common.no'),
      })
    }
    if (typeof norm.country === 'string' && norm.country.trim()) {
      lines.push({
        label: t('app.leads.detail.intake_resolution.country'),
        value: norm.country.trim(),
      })
    }
    if (lead.ad_id != null) {
      lines.push({
        label: t('app.leads.detail.intake_resolution.source_ad'),
        value: `${lead.source} · ad ${lead.ad_id}`,
      })
    }
    return lines.filter((x) => x.value)
  }, [lead.ad_id, lead.source, norm, t])

  const handleConfirm = useCallback(async () => {
    const vid = selectedVacancyId.trim()
    if (!vid) {
      notify({ title: t('app.leads.detail.intake_resolution.pick_first'), variant: 'error' })
      return
    }
    setConfirming(true)
    try {
      const updated = await confirmLeadVacancy(lead.id, { vacancy_id: vid })
      onLeadUpdated(updated)
      notify({ title: t('app.leads.detail.intake_resolution.confirm_success'), variant: 'success' })
      if (confirmThenProcess && onRequestProcess) {
        await onRequestProcess()
      }
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.intake_resolution.confirm_failed'))) {
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.detail.intake_resolution.confirm_failed')
      const msg = typeof detail === 'string' ? detail : JSON.stringify(detail)
      notify({ title: msg, variant: 'error' })
    } finally {
      setConfirming(false)
    }
  }, [confirmThenProcess, lead.id, notify, onLeadUpdated, onRequestProcess, planLimitModal, selectedVacancyId, t])

  const runIntakeDecision = useCallback(
    async (body: Parameters<typeof submitLeadIntakeDecision>[1]) => {
      setActing(true)
      try {
        const updated = await submitLeadIntakeDecision(lead.id, body)
        onLeadUpdated(updated)
        notify({ title: t('app.leads.detail.intake_resolution.intake_actions.success'), variant: 'success' })
        setRejectNote('')
        setRequestInfoNote('')
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.intake_resolution.intake_actions.failed'))) {
          return
        }
        const detail =
          (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          t('app.leads.detail.intake_resolution.intake_actions.failed')
        const msg = typeof detail === 'string' ? detail : JSON.stringify(detail)
        notify({ title: msg, variant: 'error' })
      } finally {
        setActing(false)
      }
    },
    [lead.id, notify, onLeadUpdated, planLimitModal, t],
  )

  const handleReject = useCallback(async () => {
    const rc = rejectReason.trim()
    if (!rc) {
      notify({ title: t('app.leads.detail.intake_resolution.intake_actions.reject_pick_reason'), variant: 'error' })
      return
    }
    await runIntakeDecision({
      decision: 'reject',
      reason_code: rc,
      note: rejectNote.trim() || null,
    })
  }, [notify, rejectNote, rejectReason, runIntakeDecision, t])

  if (!shellOk) return null

  if (embedded && !showIntakeDecisions) return null

  const showUnified =
    composeUnifiedHeader &&
    typeof onRequestProcess === 'function' &&
    typeof onConfirmRouting === 'function' &&
    typeof onPickVacancy === 'function'

  const showVacancyBlock = !skipVacancyControls && !collapseVacancySection

  const vacancySection =
    !showVacancyBlock ? null : (
      <>
        {onRequestProcess && !confirmed && !intakeRejected ? (
          <label
            className={`flex cursor-pointer items-center gap-2.5 rounded-xl bg-slate-50 px-3 py-2.5 text-sm text-slate-700 ring-1 ring-slate-900/[0.04] ${embedded ? 'mt-0' : 'mt-4'}`}
          >
            <input
              type="checkbox"
              className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              checked={confirmThenProcess}
              disabled={confirming}
              onChange={(e) => setConfirmThenProcess(e.target.checked)}
            />
            <span>{t('app.leads.routing.confirm_then_process')}</span>
          </label>
        ) : null}

        <div className={`flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end ${embedded ? 'mt-4' : 'mt-5'}`}>
          <label className="flex min-w-[12rem] flex-1 flex-col gap-1.5 text-xs font-medium text-slate-600">
            <span>{t('app.leads.detail.intake_resolution.select_label')}</span>
            <select
              className="input h-10 rounded-xl border-slate-200 bg-white px-3 text-sm shadow-sm ring-0 focus:border-brand-400 focus:ring-2 focus:ring-brand-500/20"
              value={selectedVacancyId}
              disabled={confirming || loadingVacancies || confirmed || intakeRejected}
              onChange={(e) => setSelectedVacancyId(e.target.value)}
            >
              <option value="">{loadingVacancies ? t('common.loading') : t('app.leads.detail.intake_resolution.select_placeholder')}</option>
              {currentVacancyId && !vacancies.some((v) => v.id === currentVacancyId) ? (
                <option value={currentVacancyId}>{currentVacancyId}</option>
              ) : null}
              {vacancies.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.title || v.id}
                </option>
              ))}
            </select>
          </label>
          {suggestedId && suggestedId !== currentVacancyId ? (
            <p className="text-xs text-slate-500">
              {t('app.leads.detail.intake_resolution.suggested')}:{' '}
              <span className="font-mono text-slate-700">{suggestedId.slice(0, 8)}…</span>
            </p>
          ) : null}
          <button
            type="button"
            className="btn-primary h-10 shrink-0 rounded-xl px-4 text-sm font-semibold shadow-sm disabled:opacity-50"
            disabled={confirming || confirmed || !selectedVacancyId.trim() || intakeRejected}
            onClick={() => void handleConfirm()}
          >
            {confirming
              ? t('common.loading')
              : confirmed
                ? t('app.leads.detail.intake_resolution.confirmed_badge')
                : onRequestProcess && confirmThenProcess
                  ? t('app.leads.routing.confirm_and_process')
                  : t('app.leads.detail.intake_resolution.confirm')}
          </button>
        </div>

        {confirmed ? (
          <p className="mt-3 text-sm font-medium text-emerald-800">{t('app.leads.detail.intake_resolution.confirmed_hint')}</p>
        ) : (
          <p className="mt-3 text-sm text-slate-600">{t('app.leads.detail.intake_resolution.process_blocked_hint')}</p>
        )}
      </>
    )

  const intakeDecisionsSection = (
    <div
      className={
        embedded && skipVacancyControls
          ? 'mt-0'
          : showVacancyBlock
            ? 'mt-8 border-t border-slate-100 pt-6'
            : 'mt-6 border-t border-slate-100 pt-6'
      }
    >
      {!embedded ? (
        <>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            {t('app.leads.detail.intake_resolution.intake_actions.heading')}
          </h3>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
            {t('app.leads.detail.intake_resolution.intake_actions.hint')}
          </p>
        </>
      ) : (
        <p className="text-xs leading-relaxed text-slate-500">{t('app.leads.detail.intake_resolution.intake_actions.hint')}</p>
      )}

      {intakeRejected ? (
        <p className="mt-3 text-xs font-medium text-slate-700">{t('app.leads.detail.intake_resolution.intake_actions.rejected_banner')}</p>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className="inline-flex h-9 items-center rounded-lg bg-white px-3 text-xs font-medium text-slate-700 ring-1 ring-slate-200/90 hover:bg-slate-50 disabled:opacity-50"
              disabled={acting}
              onClick={() => void runIntakeDecision({ decision: 'qualify' })}
            >
              {acting ? t('common.loading') : t('app.leads.detail.intake_resolution.intake_actions.qualify')}
            </button>
            <button
              type="button"
              className="inline-flex h-9 items-center rounded-lg bg-white px-3 text-xs font-medium text-slate-700 ring-1 ring-slate-200/90 hover:bg-slate-50 disabled:opacity-50"
              disabled={acting}
              onClick={() => void runIntakeDecision({ decision: 'pool' })}
            >
              {acting ? t('common.loading') : t('app.leads.detail.intake_resolution.intake_actions.pool')}
            </button>
            <button
              type="button"
              className="inline-flex h-9 items-center rounded-lg bg-white px-3 text-xs font-medium text-slate-700 ring-1 ring-slate-200/90 hover:bg-slate-50 disabled:opacity-50"
              disabled={acting}
              onClick={() => void runIntakeDecision({ decision: 'duplicate_review' })}
            >
              {acting ? t('common.loading') : t('app.leads.detail.intake_resolution.intake_actions.duplicate_review')}
            </button>
          </div>

          <div className="mt-4 flex flex-col gap-2">
            <label className="text-xs text-slate-600">
              <span className="block">{t('app.leads.detail.intake_resolution.intake_actions.request_info_label')}</span>
              <textarea
                className="input mt-1 min-h-[4rem] w-full max-w-lg rounded-lg border-slate-300 bg-white px-2 py-1.5 text-sm"
                value={requestInfoNote}
                disabled={acting}
                placeholder={t('app.leads.detail.intake_resolution.intake_actions.note_placeholder')}
                onChange={(e) => setRequestInfoNote(e.target.value)}
              />
            </label>
            <button
              type="button"
              className="btn-secondary h-9 w-fit rounded-lg px-3 text-xs disabled:opacity-50"
              disabled={acting}
              onClick={() =>
                void runIntakeDecision({
                  decision: 'request_info',
                  note: requestInfoNote.trim() || null,
                })
              }
            >
              {acting ? t('common.loading') : t('app.leads.detail.intake_resolution.intake_actions.request_info')}
            </button>
          </div>

          <div className="mt-5 flex max-w-lg flex-col gap-2 rounded-xl bg-slate-50/80 p-4 ring-1 ring-slate-900/[0.04]">
            <p className="text-xs font-medium text-slate-800">{t('app.leads.detail.intake_resolution.intake_actions.reject_title')}</p>
            <label className="text-xs text-slate-600">
              <span className="block">{t('app.leads.detail.intake_resolution.intake_actions.reject_reason')}</span>
              <select
                className="input mt-1 h-9 w-full rounded-lg border-slate-300 bg-white px-2 text-sm"
                value={rejectReason}
                disabled={acting}
                onChange={(e) => setRejectReason(e.target.value)}
              >
                <option value="">{t('app.leads.detail.intake_resolution.intake_actions.reject_reason_placeholder')}</option>
                {INTAKE_REJECT_REASON_CODES.map((code) => (
                  <option key={code} value={code}>
                    {t(`app.leads.detail.intake_resolution.reject_reasons.${code}`)}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-slate-600">
              <span className="block">{t('app.leads.detail.intake_resolution.intake_actions.note_optional')}</span>
              <textarea
                className="input mt-1 min-h-[3rem] w-full rounded-lg border-slate-300 bg-white px-2 py-1.5 text-sm"
                value={rejectNote}
                disabled={acting}
                placeholder={t('app.leads.detail.intake_resolution.intake_actions.note_placeholder')}
                onChange={(e) => setRejectNote(e.target.value)}
              />
            </label>
            <button
              type="button"
              className="btn-secondary h-9 w-fit rounded-lg border-red-200 bg-red-50 px-3 text-xs text-red-900 hover:bg-red-100 disabled:opacity-50"
              disabled={acting || !rejectReason.trim()}
              onClick={() => void handleReject()}
            >
              {acting ? t('common.loading') : t('app.leads.detail.intake_resolution.intake_actions.reject_submit')}
            </button>
          </div>
        </>
      )}
    </div>
  )

  const qualificationSection =
    !hideQualificationLines && qualificationLines.length > 0 ? (
      <div className="mt-6 border-t border-slate-100 pt-5">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          {t('app.leads.detail.intake_resolution.qualification_title')}
        </h3>
        <dl className="mt-2 grid gap-1 text-xs sm:grid-cols-2">
          {qualificationLines.map((row) => (
            <div key={row.label} className="flex gap-2">
              <dt className="text-slate-500">{row.label}</dt>
              <dd className="text-slate-900">{row.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    ) : null

  const unifiedBlock =
    showUnified ? (
      <LeadIntakeUnifiedDecisionHeader
        lead={lead}
        isServicesTenant={isServicesTenant}
        processing={processBusy}
        routingBusy={routingBusy}
        poolBusy={poolBusy}
        onProcess={() => void onRequestProcess?.()}
        onPickVacancy={onPickVacancy}
        onConfirmRouting={onConfirmRouting}
        onPool={onPool}
        hideQuestionLine
        className="mb-6 border-b border-slate-100 pb-6"
      />
    ) : null

  const body = (
    <>
      {unifiedBlock}
      {vacancySection}
      {showIntakeDecisions ? intakeDecisionsSection : null}
      {qualificationSection}
    </>
  )

  if (embedded) {
    return <div className={className}>{body}</div>
  }

  return (
    <section
      className={`card relative overflow-hidden p-5 shadow-md shadow-slate-900/[0.04] sm:p-6 ${className}`}
      aria-label={t('app.leads.detail.intake_resolution.title')}
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-brand-500 via-brand-500 to-brand-600/90"
        aria-hidden
      />
      <div className="relative pt-1">
        {!composeUnifiedHeader ? (
          <>
            <h2 className="text-base font-semibold tracking-tight text-slate-900">{t('app.leads.detail.intake_resolution.title')}</h2>
            <p className="mt-1.5 max-w-prose text-sm leading-relaxed text-slate-500">
              {t('app.leads.detail.intake_resolution.subtitle')}
            </p>
          </>
        ) : showIntakeDecisions ? (
          <h2 className="mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.leads.intake_workspace.detail.decisions_heading')}
          </h2>
        ) : null}
        {body}
      </div>
    </section>
  )
}
