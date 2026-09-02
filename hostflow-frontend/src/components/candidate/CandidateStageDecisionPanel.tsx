import { useMemo } from 'react'
import clsx from 'clsx'
import CandidateStageJourneyPanel from './CandidateStageJourneyPanel'
import { useI18n } from '../../i18n'
import { isCandidateOperationallyTerminal } from '../../utils/candidatePipelineCompleted'
import { canonicalStageKey } from '../../utils/stageLabels'
import { operationalHintForStageResolved } from '../../utils/stageOperationalHints'

type Stage = { code: string; label: string }

type DocsBlockers = {
  missing: string[]
  problematic: string[]
  inProgress?: string[]
}

type Props = {
  locale: string
  stageSinceAt: string | null
  /** Full funnel order for move buttons, current/next resolution, and operational hints (same for all agency users on this candidate). */
  stageJourneyStages: Stage[]
  /**
   * Optional narrowed list for the horizontal journey strip only (e.g. client-facing procesowani view).
   * When omitted, the strip uses `stageJourneyStages`.
   */
  journeyPanelStages?: Stage[]
  stageOutcomeStages: Stage[]
  stageJourneyDisplayStage: string | null | undefined
  stageJourneyOutcomeStage: string | null | undefined
  stageJourneySignals?: Array<{ key: string; label: string }>
  completedStageCodes: Set<string>
  currentStageCode: string | null | undefined
  /** Raw row status / display status for terminal detection when stage lags auto-reject, etc. */
  candidateRowStatus?: string | null
  candidateStatus?: string | null
  stageLabelIntl: (code: string) => string

  docsBlockers: DocsBlockers
  /** Label blockers as requirement names vs document type codes. */
  blockerLabelMode?: 'requirement' | 'document'
  /** When true, forward movement in the pipeline is blocked by documents. */
  docsPipelineBlocking: boolean
  /**
   * Tenant “soft” policy: documents would block, but forward move is still allowed server-side —
   * show advisory chips / copy only.
   */
  docsPipelineSoftWarn?: boolean
  /** When true, forward movement is blocked until a vacancy is assigned (contact / questionnaire phase). */
  vacancyPipelineBlocking?: boolean
  /** When true, forward movement from **new** requires ≥1 logged contact attempt (policy on). */
  contactAttemptPipelineBlocking?: boolean

  onMoveStage: (stageCode: string) => void
  canEdit?: boolean
  /** When false but this is true, only rejected/declined outcomes are allowed (handoff lock). */
  canCloseRecruitment?: boolean
  /** Opens contact-attempt register modal (same as Communication section). Used for “Contact candidate” next step. */
  onOpenContactAttempts?: () => void
}

export default function CandidateStageDecisionPanel({
  locale,
  stageSinceAt,
  stageJourneyStages,
  journeyPanelStages,
  stageOutcomeStages,
  stageJourneyDisplayStage,
  stageJourneyOutcomeStage,
  stageJourneySignals,
  completedStageCodes,
  currentStageCode,
  candidateRowStatus,
  candidateStatus,
  stageLabelIntl,
  docsBlockers,
  blockerLabelMode = 'document',
  docsPipelineBlocking,
  docsPipelineSoftWarn = false,
  vacancyPipelineBlocking = false,
  contactAttemptPipelineBlocking = false,
  onMoveStage,
  canEdit = true,
  canCloseRecruitment = true,
  onOpenContactAttempts,
}: Props) {
  const { t } = useI18n()

  const canMutatePipeline = canEdit
  const canUseOutcomes = canEdit || canCloseRecruitment

  const stripStages = journeyPanelStages ?? stageJourneyStages

  const pipelineCompleted = useMemo(
    () =>
      isCandidateOperationallyTerminal({
        stage: currentStageCode,
        row_status: candidateRowStatus,
        status: candidateStatus,
      }),
    [currentStageCode, candidateRowStatus, candidateStatus],
  )

  const pipelineForwardBlocked =
    !pipelineCompleted &&
    (docsPipelineBlocking || vacancyPipelineBlocking || contactAttemptPipelineBlocking)

  const docsSoftAdvisory = Boolean(docsPipelineSoftWarn && !docsPipelineBlocking)

  const pipelineSteps = useMemo(() => {
    const main = stageJourneyStages || []
    const outcomes = stageOutcomeStages || []
    return [...main, ...outcomes]
  }, [stageJourneyStages, stageOutcomeStages])

  const currentCode = useMemo(() => {
    const candidates = [
      currentStageCode,
      stageJourneyDisplayStage,
      stageJourneyOutcomeStage,
    ].filter(Boolean) as string[]
    return candidates.find((c) => pipelineSteps.some((s) => s.code === c)) ?? candidates[0] ?? null
  }, [currentStageCode, stageJourneyDisplayStage, stageJourneyOutcomeStage, pipelineSteps])

  const currentIdx = useMemo(() => {
    if (!currentCode) return -1
    return pipelineSteps.findIndex((s) => s.code === currentCode)
  }, [currentCode, pipelineSteps])

  const prevStage = currentIdx >= 1 ? pipelineSteps[currentIdx - 1] : null
  const nextStage = currentIdx >= 0 && currentIdx < pipelineSteps.length - 1 ? pipelineSteps[currentIdx + 1] : null
  const nextStageCode = nextStage?.code ?? null

  const requiredCodes = useMemo(() => {
    const out: string[] = []
    const seen = new Set<string>()
    const push = (c: string) => {
      const code = String(c || '').trim()
      if (!code || seen.has(code)) return
      seen.add(code)
      out.push(code)
    }
    docsBlockers.problematic.forEach(push)
    docsBlockers.missing.forEach(push)
    if (docsSoftAdvisory) {
      ;(docsBlockers.inProgress || []).forEach(push)
    }
    return out
  }, [docsBlockers.missing, docsBlockers.problematic, docsBlockers.inProgress, docsSoftAdvisory])

  const labelForBlocker = (code: string) => {
    if (blockerLabelMode === 'requirement') {
      const fromRequirements = t(`app.candidate_card.requirements_checklist.requirements.${code}`, {
        defaultValue: '',
      }).trim()
      if (fromRequirements) return fromRequirements
    }
    const fromTypeCodes = t(`admin.documents.type_codes.${code}`, { defaultValue: '' }).trim()
    if (fromTypeCodes) return fromTypeCodes
    const fromProcessTypes = t(`admin.documents.process_types.${code}`, { defaultValue: '' }).trim()
    if (fromProcessTypes) return fromProcessTypes
    const normalized = String(code || '').replace(/[_-]+/g, ' ').trim()
    return normalized || code
  }

  const earlyOperationalHint = useMemo(() => {
    if (pipelineCompleted) return null
    if (docsPipelineBlocking || contactAttemptPipelineBlocking) return null
    return operationalHintForStageResolved(currentCode, nextStageCode, {
      // Inside this branch contact gate is already satisfied for UI purposes.
      contactAttemptPipelineBlocking: false,
      vacancyPipelineBlocking,
    })
  }, [
    currentCode,
    docsPipelineBlocking,
    contactAttemptPipelineBlocking,
    vacancyPipelineBlocking,
    nextStageCode,
    pipelineCompleted,
  ])

  /** Plan: New → contact; Contact established → assign vacancy; docs not part of early gates. */
  const earlyStageNextStepLabel = useMemo(() => {
    if (pipelineCompleted) return null
    if (docsPipelineBlocking || docsSoftAdvisory || contactAttemptPipelineBlocking) return null
    const hint = earlyOperationalHint
    switch (hint?.kind) {
      case 'call_candidate':
        return t('app.candidate_card.stage_decision.next_step_contact_candidate', {
          defaultValue: 'Next step: → Contact candidate',
        })
      case 'assign_vacancy':
        return t('app.candidate_card.stage_decision.next_step_assign_vacancy', {
          defaultValue: 'Next step: → Assign vacancy / client',
        })
      case 'request_documents':
        return t('app.candidate_card.stage_decision.next_step_request_documents', {
          defaultValue: 'Next step: → Request documents',
        })
      case 'verify_documents':
        return t('app.candidate_card.stage_decision.next_step_verify_documents', {
          defaultValue: 'Next step: → Verify documents',
        })
      case 'handoff_prep':
        return t('app.candidate_card.stage_decision.next_step_handoff_prep', {
          defaultValue: 'Next step: → Prepare handoff',
        })
      case 'advance_pipeline':
        return t('app.candidate_card.stage_decision.next_step_advance', {
          defaultValue: 'Next step: → Move the case forward',
        })
      default:
        return t('app.candidate_card.stage_decision.next_step_contact_candidate', {
          defaultValue: 'Next step: → Contact candidate',
        })
    }
  }, [earlyOperationalHint, docsPipelineBlocking, docsSoftAdvisory, contactAttemptPipelineBlocking, pipelineCompleted, t])

  const contactNextStepOpensAttemptsModal =
    Boolean(onOpenContactAttempts) &&
    !docsPipelineBlocking &&
    !docsSoftAdvisory &&
    !vacancyPipelineBlocking &&
    !contactAttemptPipelineBlocking &&
    (earlyOperationalHint === null || earlyOperationalHint.kind === 'call_candidate')

  const contactAttemptNextStepLabel = t('app.candidate_card.stage_decision.next_step_contact_candidate', {
    defaultValue: 'Next step: → Contact candidate',
  })

  const hasAnyPipelineBarrier =
    !pipelineCompleted &&
    (docsPipelineBlocking || docsSoftAdvisory || vacancyPipelineBlocking || contactAttemptPipelineBlocking)

  return (
    <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-700">
            {t('app.candidate_card.stage_decision.title', { defaultValue: 'Stage' })}
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-900 truncate">
            {currentCode ? stageLabelIntl(currentCode) : t('common.labels.not_available')}
          </div>
          {!hasAnyPipelineBarrier ? (
            <div className="mt-2 text-xs font-medium text-emerald-700">
              {t('app.candidate_card.stage_decision.no_blockers', { defaultValue: 'No blockers' })}
            </div>
          ) : (
            <div className="mt-2 space-y-2">
              {docsSoftAdvisory && requiredCodes.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] font-semibold text-sky-900">
                    {t('app.candidate_card.stage_decision.advisory', { defaultValue: 'Advisory' })}
                  </span>
                  {requiredCodes.slice(0, 4).map((code) => (
                    <span
                      key={`soft-${code}`}
                      className="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] font-semibold text-sky-900"
                    >
                      {labelForBlocker(code)}
                    </span>
                  ))}
                  {requiredCodes.length > 4 ? (
                    <span className="text-[11px] text-slate-500">{t('common.and_more', { defaultValue: 'and more…' })}</span>
                  ) : null}
                </div>
              ) : null}
              {docsSoftAdvisory && !requiredCodes.length ? (
                <div className="text-xs font-medium text-sky-900">
                  {t('app.candidate_card.stage_decision.docs_soft_policy', {
                    defaultValue:
                      'Documents are recommended before advancing — tenant policy treats this stage as soft-only.',
                  })}
                </div>
              ) : null}
              {docsPipelineBlocking && requiredCodes.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700">
                    {t('app.candidate_card.stage_decision.required', { defaultValue: 'Required' })}
                  </span>
                  {requiredCodes.slice(0, 4).map((code) => (
                    <span
                      key={code}
                      className={clsx(
                        'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold',
                        docsBlockers.missing.includes(code)
                          ? 'border-rose-200 bg-rose-50 text-rose-800'
                          : 'border-amber-200 bg-amber-50 text-amber-800',
                      )}
                    >
                      {labelForBlocker(code)}
                    </span>
                  ))}
                  {requiredCodes.length > 4 ? (
                    <span className="text-[11px] text-slate-500">{t('common.and_more', { defaultValue: 'and more…' })}</span>
                  ) : null}
                </div>
              ) : docsPipelineBlocking ? (
                <div className="text-xs font-medium text-amber-800">
                  {t('app.candidate_card.stage_decision.docs_blocking_generic', {
                    defaultValue: 'Documents block moving forward — see checklist',
                  })}
                </div>
              ) : null}
              {contactAttemptPipelineBlocking ? (
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] font-semibold text-sky-900">
                    {t('app.candidate_card.stage_decision.required', { defaultValue: 'Required' })}
                  </span>
                  <span className="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] font-semibold text-sky-900">
                    {t('app.candidate_card.stage_decision.contact_attempt_required_chip', {
                      defaultValue: 'Contact attempt logged',
                    })}
                  </span>
                </div>
              ) : null}
              {vacancyPipelineBlocking ? (
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                    {t('app.candidate_card.stage_decision.required', { defaultValue: 'Required' })}
                  </span>
                  <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                    {t('app.candidate_card.stage_decision.vacancy_required_chip', { defaultValue: 'Vacancy / client' })}
                  </span>
                </div>
              ) : null}
            </div>
          )}

          {docsPipelineBlocking ? (
            <div className="mt-2 text-xs font-medium text-amber-800">
              {t('app.candidate_card.stage_decision.next_step_docs', { defaultValue: 'Next step: → Request documents' })}
            </div>
          ) : docsSoftAdvisory ? (
            <div className="mt-2 text-xs font-medium text-sky-900">
              {t('app.candidate_card.stage_decision.next_step_docs_soft', {
                defaultValue: 'Consider completing documents before moving forward (not required by policy).',
              })}
            </div>
          ) : contactAttemptPipelineBlocking ? (
            onOpenContactAttempts ? (
              <button
                type="button"
                className="mt-2 block w-full max-w-full text-left text-xs font-medium text-teal-800 underline decoration-teal-600/50 underline-offset-2 hover:text-teal-950 hover:decoration-teal-700"
                onClick={onOpenContactAttempts}
                title={t('app.candidate_card.stage_decision.open_contact_attempts_title', {
                  defaultValue: 'Open contact attempts — record channel and result',
                })}
              >
                {contactAttemptNextStepLabel}
              </button>
            ) : (
              <div className="mt-2 text-xs font-medium text-amber-800">{contactAttemptNextStepLabel}</div>
            )
          ) : vacancyPipelineBlocking ? (
            <div className="mt-2 text-xs font-medium text-amber-800">
              {t('app.candidate_card.stage_decision.next_step_assign_vacancy', {
                defaultValue: 'Next step: → Assign vacancy / client',
              })}
            </div>
          ) : earlyStageNextStepLabel ? (
            contactNextStepOpensAttemptsModal ? (
              <button
                type="button"
                className="mt-2 block w-full max-w-full text-left text-xs font-medium text-teal-800 underline decoration-teal-600/50 underline-offset-2 hover:text-teal-950 hover:decoration-teal-700"
                onClick={onOpenContactAttempts}
                title={t('app.candidate_card.stage_decision.open_contact_attempts_title', {
                  defaultValue: 'Open contact attempts — record channel and result',
                })}
              >
                {earlyStageNextStepLabel}
              </button>
            ) : (
              <div className="mt-2 text-xs font-medium text-slate-700">{earlyStageNextStepLabel}</div>
            )
          ) : null}
        </div>

        <div className="shrink-0 flex flex-col items-end gap-2">
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={!prevStage || !canMutatePipeline}
            onClick={() => prevStage && onMoveStage(prevStage.code)}
          >
            {t('app.candidate_card.stage_decision.move_back', { defaultValue: 'Move back' })}
          </button>
          <button
            type="button"
            className="btn-primary btn-sm"
            disabled={!nextStage || !canMutatePipeline || pipelineForwardBlocked}
            onClick={() => nextStage && onMoveStage(nextStage.code)}
            title={
              docsPipelineBlocking
                ? blockerLabelMode === 'requirement'
                  ? t('app.candidate_card.stage_decision.blocked_title_requirements', {
                      defaultValue: 'Blocked by unconfirmed requirements',
                    })
                  : t('app.candidate_card.stage_decision.blocked_title', { defaultValue: 'Blocked by required documents' })
                : docsSoftAdvisory
                  ? t('app.candidate_card.stage_decision.soft_docs_title', {
                      defaultValue: 'Documents recommended — forward move still allowed',
                    })
                  : contactAttemptPipelineBlocking
                  ? t('app.candidate_card.stage_decision.blocked_title_contact_attempt', {
                      defaultValue: 'Register a contact attempt before moving forward',
                    })
                  : vacancyPipelineBlocking
                    ? t('app.candidate_card.stage_decision.blocked_title_vacancy', {
                        defaultValue: 'Assign a vacancy before moving forward',
                      })
                    : undefined
            }
          >
            {t('app.candidate_card.stage_decision.move_forward', { defaultValue: 'Move forward' })}
          </button>
        </div>
      </div>

      {stageOutcomeStages && stageOutcomeStages.length > 0 && !pipelineCompleted ? (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            {t('app.candidate_card.stage_journey.outcomes', { defaultValue: 'Outcomes' })}
          </span>
          {stageOutcomeStages.map((s) => {
            const isCurrent = String(currentStageCode || '') === s.code
            return (
              <button
                key={s.code}
                type="button"
                className="btn-secondary btn-sm"
                disabled={!canUseOutcomes || isCurrent}
                onClick={() => onMoveStage(s.code)}
              >
                {s.label}
              </button>
            )
          })}
        </div>
      ) : null}

      <div className="mt-3 min-w-0">
        <CandidateStageJourneyPanel
          locale={locale}
          variant="horizontal"
          tone="default"
          compact
          stages={stripStages}
          outcomeStages={stageOutcomeStages}
          currentStage={stageJourneyDisplayStage}
          currentOutcomeStage={stageJourneyOutcomeStage}
          signals={stageJourneySignals}
          stageSinceAt={stageSinceAt}
          completedStageCodes={completedStageCodes}
          // Visualization only; movement is done via the buttons above.
          canEdit={false}
          blocked={pipelineForwardBlocked}
        />
      </div>
    </section>
  )
}
