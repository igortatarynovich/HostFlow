import { useMemo } from 'react'
import clsx from 'clsx'
import CandidateStageJourneyPanel from './CandidateStageJourneyPanel'
import { useI18n } from '../../i18n'

type Stage = { code: string; label: string }

type DocsBlockers = {
  missing: string[]
  problematic: string[]
}

type Props = {
  locale: string
  stageSinceAt: string | null
  stageJourneyStages: Stage[]
  stageOutcomeStages: Stage[]
  stageJourneyDisplayStage: string | null | undefined
  stageJourneyOutcomeStage: string | null | undefined
  stageJourneySignals?: Array<{ key: string; label: string }>
  completedStageCodes: Set<string>
  currentStageCode: string | null | undefined
  stageLabelIntl: (code: string) => string

  docsBlockers: DocsBlockers
  docsBlockersActive: boolean

  onMoveStage: (stageCode: string) => void
  canEdit?: boolean
}

export default function CandidateStageDecisionPanel({
  locale,
  stageSinceAt,
  stageJourneyStages,
  stageOutcomeStages,
  stageJourneyDisplayStage,
  stageJourneyOutcomeStage,
  stageJourneySignals,
  completedStageCodes,
  currentStageCode,
  stageLabelIntl,
  docsBlockers,
  docsBlockersActive,
  onMoveStage,
  canEdit = true,
}: Props) {
  const { t } = useI18n()

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
    return out
  }, [docsBlockers.missing, docsBlockers.problematic])

  const labelForDocType = (code: string) => {
    // Translation is available under admin.documents.types.* in the app.
    return t(`admin.documents.types.${code}`, { defaultValue: code })
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-700">
            {t('app.candidate_card.stage_decision.title', { defaultValue: 'Stage' })}
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-900 truncate">
            {currentCode ? stageLabelIntl(currentCode) : t('common.labels.not_available')}
          </div>
          {requiredCodes.length ? (
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="inline-flex items-center rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700 border border-rose-200">
                {t('app.candidate_card.stage_decision.required', { defaultValue: 'Required' })}
              </span>
              {requiredCodes.slice(0, 4).map((code) => (
                <span
                  key={code}
                  className={clsx(
                    'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold',
                    docsBlockers.missing.includes(code)
                      ? 'bg-rose-50 border-rose-200 text-rose-800'
                      : 'bg-amber-50 border-amber-200 text-amber-800',
                  )}
                >
                  {labelForDocType(code)}
                </span>
              ))}
              {requiredCodes.length > 4 ? (
                <span className="text-[11px] text-slate-500">{t('common.and_more', { defaultValue: 'and more…' })}</span>
              ) : null}
            </div>
          ) : (
            <div className="mt-2 text-xs text-emerald-700">
              {t('app.candidate_card.stage_decision.no_blockers', { defaultValue: 'No blockers detected.' })}
            </div>
          )}

          {docsBlockersActive ? (
            <div className="mt-2 text-xs text-amber-800 font-medium">
              {t('app.candidate_card.stage_decision.next_step_docs', { defaultValue: 'Next step: -> Request documents' })}
            </div>
          ) : null}
        </div>

        <div className="shrink-0 flex flex-col items-end gap-2">
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={!prevStage || !canEdit}
            onClick={() => prevStage && onMoveStage(prevStage.code)}
          >
            {t('app.candidate_card.stage_decision.move_back', { defaultValue: 'Move back' })}
          </button>
          <button
            type="button"
            className="btn-primary btn-sm"
            disabled={!nextStage || !canEdit || docsBlockersActive}
            onClick={() => nextStage && onMoveStage(nextStage.code)}
            title={
              docsBlockersActive
                ? t('app.candidate_card.stage_decision.blocked_title', { defaultValue: 'Blocked by required documents' })
                : undefined
            }
          >
            {t('app.candidate_card.stage_decision.move_forward', { defaultValue: 'Move forward' })}
          </button>
        </div>
      </div>

      <div className="mt-3">
        <CandidateStageJourneyPanel
          locale={locale}
          variant="horizontal"
          tone="default"
          compact
          stages={stageJourneyStages}
          outcomeStages={stageOutcomeStages}
          currentStage={stageJourneyDisplayStage}
          currentOutcomeStage={stageJourneyOutcomeStage}
          signals={stageJourneySignals}
          stageSinceAt={stageSinceAt}
          completedStageCodes={completedStageCodes}
          // Visualization only; movement is done via the buttons above.
          canEdit={false}
        />
      </div>
    </section>
  )
}

