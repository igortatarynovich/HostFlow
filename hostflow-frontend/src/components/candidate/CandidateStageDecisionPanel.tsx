import { useMemo } from 'react'
import { IconChevronLeft, IconChevronRight } from '@tabler/icons-react'
import CandidateStageJourneyPanel from './CandidateStageJourneyPanel'
import { StatusBadge } from '../ui/StatusBadge'
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
  /** Localized names already resolved from the checklist. */
  blockerLabels?: Record<string, string>
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
  /** Horizontal track is rendered by the workspace. Sidebar keeps stage controls only. */
  showJourney?: boolean
  /** Drop the card frame when a parent already groups stage, manager and tags. */
  embedded?: boolean
  /** `journey` is the candidate-card line only. `status` is next step and blockers. */
  layout?: 'full' | 'journey' | 'status'
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
  blockerLabels,
  docsPipelineBlocking,
  docsPipelineSoftWarn = false,
  vacancyPipelineBlocking = false,
  contactAttemptPipelineBlocking = false,
  onMoveStage,
  canEdit = true,
  canCloseRecruitment = true,
  onOpenContactAttempts,
  showJourney = true,
  embedded = false,
  layout = 'full',
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

  const blockerLines = useMemo(() => {
    const out: Array<{ code: string; reason: 'missing' | 'approval' | 'rejected' }> = []
    const seen = new Set<string>()
    const push = (c: string, reason: 'missing' | 'approval' | 'rejected') => {
      const code = String(c || '').trim()
      if (!code || seen.has(code)) return
      seen.add(code)
      out.push({ code, reason })
    }
    docsBlockers.missing.forEach((code) => push(code, 'missing'))
    docsBlockers.problematic.forEach((code) => push(code, 'rejected'))
    if (docsPipelineBlocking || docsSoftAdvisory) {
      ;(docsBlockers.inProgress || []).forEach((code) => push(code, 'approval'))
    }
    return out
  }, [docsBlockers.missing, docsBlockers.problematic, docsBlockers.inProgress, docsPipelineBlocking, docsSoftAdvisory])

  const labelForBlocker = (code: string) => {
    const provided = String(blockerLabels?.[code] || '').trim()
    if (provided) return provided
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

  const reasonLabel = (reason: 'missing' | 'approval' | 'rejected') => {
    if (reason === 'approval') {
      return t('app.candidate_card.stage_decision.blocker_approval', { defaultValue: 'Needs approval' })
    }
    if (reason === 'rejected') {
      return t('app.candidate_card.stage_decision.blocker_rejected', { defaultValue: 'Rejected' })
    }
    return t('app.candidate_card.stage_decision.blocker_missing', { defaultValue: 'Missing' })
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

  const statusBody = (
    <div className="min-w-0">
      {!hasAnyPipelineBarrier ? (
        <div className="text-xs font-medium text-emerald-700">
          {t('app.candidate_card.stage_decision.no_blockers', { defaultValue: 'No blockers' })}
        </div>
      ) : (
        <div className="space-y-2">
          {docsSoftAdvisory && blockerLines.length > 0 ? (
            <div className="space-y-1">
              <div className="text-xs font-medium text-slate-700">
                {t('app.candidate_card.stage_decision.missing_for_transition', { defaultValue: 'Missing for the next stage:' })}
              </div>
              {blockerLines.map((line) => (
                <div key={`soft-${line.code}`} className="flex min-w-0 items-center gap-2 text-xs text-slate-800">
                  <span className="min-w-0 truncate">{labelForBlocker(line.code)}</span>
                  <StatusBadge size="sm" shape="pill" semantic="info" label={reasonLabel(line.reason)} />
                </div>
              ))}
            </div>
          ) : null}
          {docsSoftAdvisory && !blockerLines.length ? (
            <div className="text-xs font-medium text-sky-900">
              {t('app.candidate_card.stage_decision.docs_soft_policy', {
                defaultValue:
                  'Documents are recommended before advancing — tenant policy treats this stage as soft-only.',
              })}
            </div>
          ) : null}
          {docsPipelineBlocking && blockerLines.length > 0 ? (
            <div className="space-y-1">
              <div className="text-xs font-medium text-slate-700">
                {t('app.candidate_card.stage_decision.missing_for_transition', { defaultValue: 'Missing for the next stage:' })}
              </div>
              {blockerLines.map((line) => (
                <div key={line.code} className="flex min-w-0 items-center gap-2 text-xs text-slate-800">
                  <span className="min-w-0 truncate">{labelForBlocker(line.code)}</span>
                  <StatusBadge
                    size="sm"
                    shape="pill"
                    semantic={line.reason === 'rejected' ? 'danger' : line.reason === 'approval' ? 'warning' : 'neutral'}
                    label={reasonLabel(line.reason)}
                  />
                </div>
              ))}
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
  )

  if (layout === 'status') {
    return statusBody
  }

  if (layout === 'journey') {
    return (
      <CandidateStageJourneyPanel
        locale={locale}
        variant="horizontal"
        tone="default"
        compact
        heading={false}
        stages={stripStages}
        outcomeStages={[]}
        currentStage={stageJourneyDisplayStage}
        currentOutcomeStage={stageJourneyOutcomeStage}
        signals={stageJourneySignals}
        stageSinceAt={stageSinceAt}
        completedStageCodes={completedStageCodes}
        canEdit={false}
        blocked={pipelineForwardBlocked}
      />
    )
  }

  return (
    <section className={embedded ? 'min-w-0' : 'min-w-0 rounded-xl border border-slate-200 bg-white p-3'}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {embedded ? null : (
            <div className="text-xs font-semibold text-slate-700">
              {t('app.candidate_card.stage_decision.title', { defaultValue: 'Stage' })}
            </div>
          )}
          <div className="text-sm font-semibold leading-tight text-slate-900" title={currentCode ? stageLabelIntl(currentCode) : undefined}>
            {currentCode ? stageLabelIntl(currentCode) : t('common.labels.not_available')}
          </div>
          <div className="mt-1.5">{statusBody}</div>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            className="btn-icon btn-icon-sm border border-slate-200 bg-white text-slate-600 disabled:opacity-40"
            disabled={!prevStage || !canMutatePipeline}
            aria-label={t('app.candidate_card.stage_decision.move_back', { defaultValue: 'Move back' })}
            onClick={() => prevStage && onMoveStage(prevStage.code)}
          >
            <IconChevronLeft size={16} />
          </button>
          <button
            type="button"
            className="btn-icon btn-icon-sm border border-slate-200 bg-white text-slate-600 disabled:opacity-40"
            disabled={!nextStage || !canMutatePipeline || pipelineForwardBlocked}
            aria-label={t('app.candidate_card.ia.forward', { defaultValue: 'Forward' })}
            onClick={() => nextStage && onMoveStage(nextStage.code)}
          >
            <IconChevronRight size={16} />
          </button>
          <button
            type="button"
            className="btn-primary btn-compact"
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
            {embedded
              ? t('app.candidate_card.ia.forward', { defaultValue: 'Forward' })
              : t('app.candidate_card.stage_decision.move_forward', { defaultValue: 'Move forward' })}
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
                className="btn-secondary btn-compact"
                disabled={!canUseOutcomes || isCurrent}
                onClick={() => onMoveStage(s.code)}
              >
                {s.label}
              </button>
            )
          })}
        </div>
      ) : null}

      {showJourney ? (
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
      ) : null}
    </section>
  )
}

export function CandidatePipelineStatus(props: Omit<Props, 'layout'>) {
  return <CandidateStageDecisionPanel {...props} layout="status" />
}
