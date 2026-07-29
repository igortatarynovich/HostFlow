import clsx from 'clsx'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { IconAlertTriangle } from '@tabler/icons-react'

import {
  confirmLeadVacancy,
  getLead,
  listVacancies,
  markLeadRodoSourceProvided,
  sendLeadRodoCompliance,
  submitLeadDuplicateDecision,
  submitLeadIntakeDecision,
} from '../../api/client'
import type { Lead } from '../../api/types'
import { useToast } from '../Toast'
import { useI18n } from '../../i18n'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import {
  INTAKE_REJECT_REASON_CODES,
  leadCommunicationRailLine,
  leadEmailPolicyBlocked,
  leadRodoNoticeStatus,
  leadRodoSatisfied,
  leadRoutingTableAction,
  leadStatusAllowsIntakeDecision,
  manualProcessBlockHint,
} from '../../utils/intakeResolution'
import { leadSupportsManualProcess } from '../../utils/leadCrm'
import { intakeFitReviewSummary } from '../../utils/leadIntakeSnapshotGroups'
import LeadIntakePublicIntakeReadonlyNotice from './LeadIntakePublicIntakeReadonlyNotice'
import {
  intakeWorkspaceHeader,
  leadIntakeResolutionRejected,
  leadRecruitmentPublicIntakeReadonly,
} from '../../utils/leadIntakeWorkspace'

export type LeadIntakeDecisionRailLayout = 'panel' | 'embedded'

export type LeadIntakeDecisionRailProps = {
  lead: Lead
  processing: boolean
  routingBusy: boolean
  poolBusy: boolean
  onLeadUpdated: (l: Lead) => void
  onRequestProcess: () => void | Promise<void>
  onConfirmRouting: (vacancyId: string, thenProcess: boolean) => void
  onPool: () => void | Promise<void>
  /** `panel` = detail sidebar chrome; `embedded` = list/inbox rail, no outer card. */
  layout?: LeadIntakeDecisionRailLayout
}

const VACANCY_CARD_LIMIT = 10

function StepDivider() {
  return <div className="h-px w-full bg-gradient-to-r from-transparent via-slate-200 to-transparent" aria-hidden />
}

export default function LeadIntakeDecisionRail({
  lead,
  processing,
  routingBusy,
  poolBusy,
  onLeadUpdated,
  onRequestProcess,
  onConfirmRouting,
  onPool,
  layout = 'panel',
}: LeadIntakeDecisionRailProps) {
  const { t } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()

  const [vacancies, setVacancies] = useState<Array<{ id: string; title: string }>>([])
  const [loadingVacancies, setLoadingVacancies] = useState(false)
  const [selectedVacancyId, setSelectedVacancyId] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [acting, setActing] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [rejectNote, setRejectNote] = useState('')
  const [requestInfoNote, setRequestInfoNote] = useState('')
  const [vacancyOverrideOpen, setVacancyOverrideOpen] = useState(false)
  const [rejectExpanded, setRejectExpanded] = useState(false)
  const [rodoBusy, setRodoBusy] = useState(false)

  const rodoOk = useMemo(() => leadRodoSatisfied(lead), [lead])
  const rodoStatus = useMemo(() => leadRodoNoticeStatus(lead), [lead])
  const policyBlocked = useMemo(() => leadEmailPolicyBlocked(lead), [lead])
  const commLine = useMemo(() => leadCommunicationRailLine(lead, t), [lead, t])

  const src = String(lead.source || '').toLowerCase()
  const blockHint = manualProcessBlockHint(lead)
  const routing = useMemo(() => leadRoutingTableAction(lead, false), [lead])
  const block = manualProcessBlockHint(lead)
  const st = String(lead.status || '')
    .trim()
    .toLowerCase()

  const srcOk =
    src === 'meta' ||
    src === 'csv_import' ||
    lead.status === 'needs_routing' ||
    lead.status === 'duplicate_review'
  const hintOk =
    blockHint === 'VACANCY_NOT_CONFIRMED' ||
    blockHint === 'INTAKE_ROUTING_INCOMPLETE' ||
    blockHint === 'INTAKE_POOL_PATH_REQUIRED' ||
    blockHint === 'DUPLICATE_REVIEW_PENDING'

  const intakeRejected = useMemo(() => leadIntakeResolutionRejected(lead), [lead])
  const shellOk =
    !lead.candidate_id && !intakeRejected && leadSupportsManualProcess(lead) && (srcOk || hintOk)
  const showIntakeDecisions = shellOk && leadStatusAllowsIntakeDecision(lead)

  const suggestedId = lead.suggested_vacancy_id != null ? String(lead.suggested_vacancy_id).trim() : ''
  const confirmed = Boolean(lead.vacancy_routing_confirmed)
  const currentVacancyId = lead.vacancy_id != null ? String(lead.vacancy_id).trim() : ''

  const norm = lead.normalized && typeof lead.normalized === 'object' && !Array.isArray(lead.normalized) ? lead.normalized : {}

  const tone = intakeWorkspaceHeader(lead, false)
  const routingNeedsPicker = routing.kind === 'pick_vacancy'
  const showVacancyStep =
    shellOk && !intakeRejected && (!confirmed || vacancyOverrideOpen || routingNeedsPicker)

  const duplicateReview = st === 'duplicate_review'
  const hideSecondaryWhileDuplicate = duplicateReview && showIntakeDecisions && !intakeRejected

  const fitSummary = shellOk && !intakeRejected ? intakeFitReviewSummary(lead, t) : null
  const fitErr = lead.error?.trim() || ''
  const fitHighlight =
    fitErr === 'LEAD_FIT_NO_MATCH' ? 'critical' : fitErr === 'LEAD_FIT_NEEDS_INFO' ? 'risk' : fitSummary ? 'neutral' : 'clear'

  useEffect(() => {
    if (routingNeedsPicker) setVacancyOverrideOpen(true)
  }, [routingNeedsPicker, lead.id])

  useEffect(() => {
    const initial = currentVacancyId || suggestedId
    setSelectedVacancyId(initial)
  }, [lead.id, currentVacancyId, suggestedId, vacancyOverrideOpen])

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
    if (shellOk && vacancyOverrideOpen && vacancies.length === 0 && !loadingVacancies) void loadVacancies()
  }, [shellOk, vacancyOverrideOpen, vacancies.length, loadingVacancies, loadVacancies])

  const sendRodoNotice = useCallback(async () => {
    setRodoBusy(true)
    try {
      await sendLeadRodoCompliance(lead.id)
      const updated = await getLead(lead.id)
      onLeadUpdated(updated)
      notify({ title: t('app.leads.intake_workspace.decision_rail.rodo_send_success', { defaultValue: 'RODO notice sent.' }), variant: 'success' })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.intake_workspace.decision_rail.rodo_send_failed', { defaultValue: 'Could not send RODO notice.' })
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setRodoBusy(false)
    }
  }, [lead.id, notify, onLeadUpdated, t])

  const markRodoSourceProvided = useCallback(async () => {
    setRodoBusy(true)
    try {
      await markLeadRodoSourceProvided(lead.id)
      const updated = await getLead(lead.id)
      onLeadUpdated(updated)
      notify({ title: t('app.leads.intake_workspace.decision_rail.rodo_source_marked', { defaultValue: 'Marked as covered at source.' }), variant: 'success' })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.intake_workspace.decision_rail.rodo_source_failed', { defaultValue: 'Could not update RODO status.' })
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setRodoBusy(false)
    }
  }, [lead.id, notify, onLeadUpdated, t])

  const sortedVacancies = useMemo(() => {
    const pin = suggestedId || currentVacancyId
    if (!pin) return vacancies
    const rest = vacancies.filter((v) => v.id !== pin)
    const head = vacancies.find((v) => v.id === pin)
    return head ? [head, ...rest] : vacancies
  }, [vacancies, suggestedId, currentVacancyId])

  const displayVacancyCards = sortedVacancies.slice(0, VACANCY_CARD_LIMIT)

  const showProcessPrimary =
    routing.kind === 'none' &&
    !block &&
    st !== 'duplicate_review' &&
    !intakeRejected &&
    leadSupportsManualProcess(lead)

  const busy = processing || routingBusy

  const handleConfirmSelection = useCallback(async () => {
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
      setVacancyOverrideOpen(false)
      if (rodoOk) await onRequestProcess()
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.intake_resolution.confirm_failed'))) {
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.detail.intake_resolution.confirm_failed')
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setConfirming(false)
    }
  }, [lead.id, notify, onLeadUpdated, onRequestProcess, planLimitModal, selectedVacancyId, t, rodoOk])

  const runIntakeDecision = useCallback(
    async (body: Parameters<typeof submitLeadIntakeDecision>[1]) => {
      setActing(true)
      try {
        const updated = await submitLeadIntakeDecision(lead.id, body)
        onLeadUpdated(updated)
        notify({ title: t('app.leads.detail.intake_resolution.intake_actions.success'), variant: 'success' })
        setRejectNote('')
        setRequestInfoNote('')
        setRejectExpanded(false)
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.intake_resolution.intake_actions.failed'))) {
          return
        }
        const detail =
          (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          t('app.leads.detail.intake_resolution.intake_actions.failed')
        notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
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

  const runDuplicateCreateNew = useCallback(async () => {
    setActing(true)
    try {
      const updated = await submitLeadDuplicateDecision(lead.id, { decision: 'create_new' })
      onLeadUpdated(updated)
      notify({ title: t('app.leads.detail.intake_resolution.intake_actions.success'), variant: 'success' })
      setRejectNote('')
      setRequestInfoNote('')
      setRejectExpanded(false)
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.intake_resolution.intake_actions.failed'))) {
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.detail.intake_resolution.intake_actions.failed')
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setActing(false)
    }
  }, [lead.id, notify, onLeadUpdated, planLimitModal, t])

  if (leadRecruitmentPublicIntakeReadonly(lead, false)) {
    return <LeadIntakePublicIntakeReadonlyNotice layout={layout} />
  }

  if (!shellOk) {
    return (
      <div
        className={
          layout === 'embedded'
            ? 'text-sm leading-relaxed text-slate-600'
            : 'rounded-xl px-4 py-3 text-sm leading-relaxed text-slate-600 ring-1 ring-slate-900/[0.06]'
        }
      >
        {t('app.leads.intake_workspace.decision_rail.unsupported')}
      </div>
    )
  }

  const vacTitle =
    lead.vacancy_title ||
    (suggestedId && vacancies.find((v) => v.id === suggestedId)?.title) ||
    suggestedId ||
    currentVacancyId

  const outerClass =
    layout === 'embedded'
      ? 'space-y-8'
      : 'space-y-8 rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-900/[0.06] sm:p-6'

  return (
    <div className={outerClass}>
      {!intakeRejected && !lead.candidate_id ? (
        <div
          className={clsx(
            'space-y-3 rounded-xl px-3 py-3 text-sm ring-1',
            rodoOk ? 'bg-emerald-500/[0.08] text-emerald-950 ring-emerald-900/10' : 'bg-amber-500/[0.1] text-amber-950 ring-amber-800/15',
          )}
          role="status"
        >
          <p className="text-[11px] font-bold uppercase tracking-wide text-slate-800">
            {t('app.leads.intake_workspace.decision_rail.rodo_required_title')}
          </p>
          {!rodoOk ? (
            <>
              <p className="text-xs leading-relaxed text-amber-900/95">
                {rodoStatus === 'pending_channel'
                  ? t('app.leads.intake_workspace.decision_rail.rodo_pending_channel')
                  : rodoStatus === 'pending_policy'
                    ? t('app.leads.intake_workspace.decision_rail.rodo_pending_policy', {
                        defaultValue:
                          'Email policy blocked RODO send (missing or invalid template). Configure Lead lifecycle email in Communications settings.',
                      })
                    : rodoStatus === 'failed'
                      ? t('app.leads.intake_workspace.decision_rail.rodo_failed')
                      : t('app.leads.intake_workspace.decision_rail.rodo_required_hint')}
              </p>
              {policyBlocked ? (
                <p className="inline-flex items-center gap-1 rounded-md bg-rose-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-rose-900 ring-1 ring-rose-900/10">
                  <IconAlertTriangle size={14} aria-hidden />
                  {t('app.leads.intake_workspace.decision_rail.email_policy_blocked_badge', {
                    defaultValue: 'Email policy blocked',
                  })}
                </p>
              ) : null}
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                <button
                  type="button"
                  className="btn-primary inline-flex justify-center rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50"
                  disabled={rodoBusy}
                  onClick={() => void sendRodoNotice()}
                >
                  {rodoBusy ? t('app.leads.intake_workspace.decision_rail.rodo_sending') : t('app.leads.intake_workspace.decision_rail.send_rodo_notice')}
                </button>
                <button
                  type="button"
                  className="btn-secondary inline-flex justify-center rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50"
                  disabled={rodoBusy}
                  onClick={() => void markRodoSourceProvided()}
                >
                  {t('app.leads.intake_workspace.decision_rail.mark_source_provided')}
                </button>
              </div>
            </>
          ) : (
            <p className="text-xs font-medium text-emerald-900">{t('app.leads.intake_workspace.decision_rail.rodo_ok_hint')}</p>
          )}
        </div>
      ) : null}

      {commLine ? (
        <div
          className={clsx(
            'rounded-lg px-3 py-2 text-xs ring-1',
            commLine.tone === 'warn'
              ? 'bg-rose-500/[0.08] text-rose-950 ring-rose-900/10'
              : 'bg-slate-500/[0.06] text-slate-800 ring-slate-900/10',
          )}
          role="status"
        >
          <p className="text-[11px] font-bold uppercase tracking-wide text-slate-700">
            {t('app.leads.intake_workspace.decision_rail.communication_title', { defaultValue: 'Operational emails' })}
          </p>
          <p className="mt-1 leading-relaxed">{commLine.text}</p>
        </div>
      ) : null}

      <header className="space-y-1">
        <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">{t('app.leads.intake_workspace.decision_rail.title')}</p>
        <p className="text-sm text-slate-600">{t('app.leads.intake_workspace.decision_rail.subtitle')}</p>
      </header>

      {duplicateReview ? (
        <div className="flex gap-3 rounded-xl bg-amber-500/[0.12] px-3 py-3 text-sm text-amber-950" role="status">
          <IconAlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" stroke={1.75} aria-hidden />
          <div>
            <p className="font-semibold">{t('app.leads.intake_workspace.header.duplicate_title')}</p>
            <p className="mt-1 text-xs leading-relaxed text-amber-900/90">{t('app.leads.intake_workspace.header.duplicate_hint')}</p>
          </div>
        </div>
      ) : null}

      {intakeRejected ? (
        <p className="rounded-lg bg-slate-500/[0.08] px-3 py-2 text-xs font-medium text-slate-800">{t('app.leads.detail.intake_resolution.intake_actions.rejected_banner')}</p>
      ) : null}

      {/* Step 1 — Vacancy */}
      <section className="space-y-4" aria-labelledby="decision-rail-vacancy">
        <h2 id="decision-rail-vacancy" className="text-[11px] font-bold uppercase tracking-wide text-slate-800">
          {t('app.leads.intake_workspace.decision_rail.block_vacancy')}
        </h2>

        {showVacancyStep ? (
          (routing.kind === 'confirm_suggested' || routing.kind === 'confirm_current') && !vacancyOverrideOpen ? (
            <div className="space-y-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{t('app.leads.intake_workspace.vacancy.suggested_label')}</p>
                <p className="mt-1 text-lg font-semibold leading-tight text-slate-900">{vacTitle || '—'}</p>
              </div>
              <button
                type="button"
                className="btn-primary w-full rounded-xl py-3.5 text-base font-semibold shadow-sm disabled:opacity-50"
                disabled={busy || poolBusy}
                onClick={() => onConfirmRouting(routing.vacancyId, rodoOk)}
              >
                {busy ? t('common.loading') : t('app.leads.intake_workspace.unified.confirm_and_create')}
              </button>
              <button
                type="button"
                className="w-full rounded-xl py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                disabled={busy}
                onClick={() => {
                  setVacancyOverrideOpen(true)
                  void loadVacancies()
                }}
              >
                {t('app.leads.intake_workspace.unified.change_vacancy')}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm font-medium text-slate-800">{t('app.leads.intake_workspace.decision_rail.pick_vacancy_prompt')}</p>
              {loadingVacancies && vacancies.length === 0 ? (
                <p className="text-sm text-slate-500">{t('common.loading')}</p>
              ) : (
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {displayVacancyCards.map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      disabled={confirming}
                      onClick={() => setSelectedVacancyId(v.id)}
                      className={clsx(
                        'rounded-xl px-3 py-3 text-left text-sm font-semibold transition-colors',
                        selectedVacancyId === v.id
                          ? 'bg-brand-500/[0.12] text-brand-950 ring-2 ring-brand-600'
                          : 'bg-slate-500/[0.06] text-slate-800 ring-1 ring-slate-900/[0.06] hover:bg-slate-500/[0.09]',
                        v.id === suggestedId && selectedVacancyId !== v.id && 'ring-1 ring-amber-400/50',
                      )}
                    >
                      <span className="line-clamp-2">{v.title || v.id}</span>
                      {v.id === suggestedId ? (
                        <span className="mt-1 block text-[10px] font-medium uppercase tracking-wide text-amber-800">{t('app.leads.detail.intake_resolution.suggested')}</span>
                      ) : null}
                    </button>
                  ))}
                </div>
              )}
              <label className="block text-xs font-medium text-slate-500">
                <span className="mb-2 block">{t('app.leads.intake_workspace.decision_rail.all_vacancies')}</span>
                <select
                  className="input h-11 w-full rounded-xl border-0 bg-slate-500/[0.06] px-3 text-sm font-medium ring-1 ring-slate-900/[0.06] focus:ring-2 focus:ring-brand-500/30"
                  value={selectedVacancyId}
                  disabled={confirming || loadingVacancies}
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
              <button
                type="button"
                className="btn-primary w-full rounded-xl py-3.5 text-base font-semibold shadow-sm disabled:opacity-50"
                disabled={confirming || !selectedVacancyId.trim()}
                onClick={() => void handleConfirmSelection()}
              >
                {confirming ? t('common.loading') : t('app.leads.intake_workspace.unified.confirm_and_create')}
              </button>
              {(routing.kind === 'confirm_suggested' || routing.kind === 'confirm_current') && vacancyOverrideOpen ? (
                <button type="button" className="w-full text-center text-xs font-medium text-slate-600 underline-offset-2 hover:underline" onClick={() => setVacancyOverrideOpen(false)}>
                  {t('app.leads.intake_workspace.decision_rail.back_suggested')}
                </button>
              ) : null}
            </div>
          )
        ) : confirmed && !vacancyOverrideOpen ? (
          <p className="text-sm font-medium text-emerald-900">{t('app.leads.detail.intake_resolution.confirmed_hint')}</p>
        ) : null}
      </section>

      <StepDivider />

      {/* Qualification context (read-only — not an action step) */}
      {!intakeRejected ? (
        <section className="space-y-2 rounded-xl bg-slate-500/[0.07] px-3 py-3 ring-1 ring-slate-900/[0.05]" aria-labelledby="decision-rail-qual">
          <div>
            <h2 id="decision-rail-qual" className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">
              {t('app.leads.intake_workspace.decision_rail.context_qualification')}
            </h2>
            <p className="mt-1 text-[11px] leading-tight text-slate-500">{t('app.leads.intake_workspace.decision_rail.context_qualification_hint')}</p>
          </div>
          <p
            className={clsx(
              'text-sm leading-relaxed',
              fitHighlight === 'critical' && 'font-semibold text-rose-900',
              fitHighlight === 'risk' && 'font-semibold text-amber-900',
              fitHighlight === 'neutral' && 'font-medium text-slate-800',
              fitHighlight === 'clear' && 'text-slate-500',
            )}
          >
            {fitSummary || t('app.leads.intake_workspace.decision_rail.fit_clear')}
          </p>
        </section>
      ) : null}

      {!intakeRejected ? <StepDivider /> : null}

      {/* Actions */}
      <section className="space-y-4" aria-labelledby="decision-rail-actions">
        <h2 id="decision-rail-actions" className="text-[11px] font-bold uppercase tracking-wide text-slate-800">
          {t('app.leads.intake_workspace.decision_rail.block_decision')}
        </h2>

        {duplicateReview && showIntakeDecisions && !intakeRejected ? (
          <button
            type="button"
            className="btn-primary w-full rounded-xl py-3.5 text-base font-semibold shadow-sm disabled:opacity-50"
            disabled={acting}
            onClick={() => void runDuplicateCreateNew()}
          >
            {acting ? t('common.loading') : t('app.leads.intake_workspace.decision_rail.qualify_not_duplicate')}
          </button>
        ) : null}

        {showProcessPrimary ? (
          <button
            type="button"
            className="btn-primary w-full rounded-xl py-3.5 text-base font-semibold shadow-sm disabled:opacity-50"
            disabled={processing || routingBusy}
            onClick={() => void onRequestProcess()}
          >
            {processing ? t('common.loading') : t('app.leads.intake_workspace.unified.create_candidate')}
          </button>
        ) : null}

        {showIntakeDecisions && !intakeRejected && !hideSecondaryWhileDuplicate ? (
          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-500">
              <span className="mb-2 block">{t('app.leads.detail.intake_resolution.intake_actions.request_info_label')}</span>
              <textarea
                className="input min-h-[4rem] w-full rounded-xl border-0 bg-slate-500/[0.06] px-3 py-2 text-sm ring-1 ring-slate-900/[0.06] focus:ring-2 focus:ring-brand-500/25"
                value={requestInfoNote}
                disabled={acting || !rodoOk}
                placeholder={t('app.leads.detail.intake_resolution.intake_actions.note_placeholder')}
                onChange={(e) => setRequestInfoNote(e.target.value)}
              />
            </label>
            <button
              type="button"
              className="w-full rounded-xl border border-slate-200 bg-white py-3 text-sm font-semibold text-slate-900 shadow-sm hover:bg-slate-50 disabled:opacity-50"
              disabled={acting || !rodoOk}
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
        ) : null}

        {showIntakeDecisions && !intakeRejected && !hideSecondaryWhileDuplicate ? (
          <button
            type="button"
            className="w-full rounded-lg py-3 text-sm font-medium text-slate-600 hover:bg-slate-500/[0.06] disabled:opacity-50"
            disabled={acting || poolBusy}
            onClick={() => void onPool()}
          >
            {poolBusy ? t('common.loading') : t('app.leads.detail.intake_resolution.intake_actions.pool')}
          </button>
        ) : null}

        {showIntakeDecisions && !intakeRejected && !hideSecondaryWhileDuplicate ? (
          <button type="button" className="text-left text-sm font-medium text-rose-700 underline-offset-2 hover:underline disabled:opacity-50" disabled={acting} onClick={() => setRejectExpanded((x) => !x)}>
            {rejectExpanded ? t('app.leads.intake_workspace.decision_rail.reject_cancel') : t('app.leads.intake_workspace.decision_rail.reject_open')}
          </button>
        ) : null}
      </section>

      {rejectExpanded && showIntakeDecisions && !intakeRejected && !hideSecondaryWhileDuplicate ? (
        <>
          <StepDivider />
          <section className="space-y-3 rounded-xl bg-rose-500/[0.06] px-3 py-4 sm:px-4" aria-labelledby="decision-rail-reject">
            <h2 id="decision-rail-reject" className="text-[11px] font-bold uppercase tracking-wide text-rose-900">
              {t('app.leads.detail.intake_resolution.intake_actions.reject_title')}
            </h2>
            <label className="block text-xs text-slate-700">
              <span className="mb-1 block">{t('app.leads.detail.intake_resolution.intake_actions.reject_reason')}</span>
              <select
                className="input h-10 w-full rounded-lg border-0 bg-white px-2 text-sm ring-1 ring-slate-900/[0.08]"
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
            <label className="block text-xs text-slate-700">
              <span className="mb-1 block">{t('app.leads.detail.intake_resolution.intake_actions.note_optional')}</span>
              <textarea
                className="input min-h-[3rem] w-full rounded-lg border-0 bg-white px-2 py-2 text-sm ring-1 ring-slate-900/[0.08]"
                value={rejectNote}
                disabled={acting}
                placeholder={t('app.leads.detail.intake_resolution.intake_actions.note_placeholder')}
                onChange={(e) => setRejectNote(e.target.value)}
              />
            </label>
            <button
              type="button"
              className="w-full rounded-xl bg-rose-600 py-3 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
              disabled={acting || !rejectReason.trim()}
              onClick={() => void handleReject()}
            >
              {acting ? t('common.loading') : t('app.leads.detail.intake_resolution.intake_actions.reject_submit')}
            </button>
          </section>
        </>
      ) : null}

      <details className="group pt-1">
        <summary className="cursor-pointer list-none rounded-lg px-2 py-2 text-xs font-medium text-slate-500 marker:content-none hover:bg-slate-500/[0.06] [&::-webkit-details-marker]:hidden">
          {t('app.leads.intake_workspace.decision_rail.optional_context')}
        </summary>
        <div className="mt-2 space-y-2 pl-2 text-xs leading-relaxed text-slate-600">
          <p className="font-medium text-slate-700">{t(`app.leads.intake_workspace.header.${tone.tone}_title`)}</p>
          {(() => {
            const hintKey = `app.leads.intake_workspace.header.${tone.tone}_hint`
            const hintRaw = t(hintKey)
            return hintRaw !== hintKey ? <p>{hintRaw}</p> : null
          })()}
          {showIntakeDecisions && !duplicateReview && !intakeRejected ? (
            <button
              type="button"
              className="font-semibold text-brand-800 underline-offset-2 hover:underline disabled:opacity-50"
              disabled={acting}
              onClick={() => void runIntakeDecision({ decision: 'duplicate_review' })}
            >
              {t('app.leads.detail.intake_resolution.intake_actions.duplicate_review')}
            </button>
          ) : null}
        </div>
      </details>
    </div>
  )
}
