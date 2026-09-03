import { useMemo } from 'react'
import clsx from 'clsx'
import { formatDistanceToNowStrict } from 'date-fns'
import { enUS, pl, ru } from 'date-fns/locale'
import { useI18n } from '../../i18n'
import { formatDateSafe } from '../../modules/candidates/candidateUtils'

type Stage = { code: string; label: string }

type Props = {
  locale: string
  variant?: 'vertical' | 'horizontal'
  tone?: 'default' | 'hero'
  compact?: boolean
  stages: Stage[]
  outcomeStages?: Stage[]
  currentStage: string | null | undefined
  currentOutcomeStage?: string | null | undefined
  signals?: Array<{ key: string; label: string }>
  stageSinceAt: string | null | undefined
  completedStageCodes?: Set<string>
  canEdit?: boolean
  onStageChange?: (stage: string) => void | Promise<void>
  onOpenStageHistory?: () => void
  onOpenChangeLog?: () => void
  blocked?: boolean
}

export default function CandidateStageJourneyPanel({
  locale,
  variant = 'vertical',
  tone = 'default',
  compact = false,
  stages,
  outcomeStages,
  currentStage,
  currentOutcomeStage,
  signals,
  stageSinceAt,
  completedStageCodes,
  canEdit = false,
  onStageChange,
  onOpenStageHistory,
  onOpenChangeLog,
  blocked = false,
}: Props) {
  const { t } = useI18n()
  const dateFnsLocale = useMemo(() => (locale === 'ru' ? ru : locale === 'pl' ? pl : enUS), [locale])

  const currentIdx = useMemo(() => {
    if (!currentStage) return -1
    return stages.findIndex((s) => s.code === currentStage)
  }, [currentStage, stages])

  const sinceLabel = useMemo(() => {
    if (!stageSinceAt) return null
    const rel = (() => {
      const ts = Date.parse(String(stageSinceAt))
      if (!Number.isFinite(ts)) return null
      try {
        return formatDistanceToNowStrict(new Date(ts), { addSuffix: true, locale: dateFnsLocale })
      } catch {
        return null
      }
    })()
    const abs = formatDateSafe(String(stageSinceAt), locale) || String(stageSinceAt)
    return { rel, abs }
  }, [dateFnsLocale, locale, stageSinceAt])

  const isHero = tone === 'hero'
  const titleClass = isHero ? 'text-white/90' : 'text-slate-700'
  const subClass = isHero ? 'text-white/75' : 'text-slate-500'
  const badgeClass = isHero ? 'border-white/20 bg-white/10 text-white/85' : 'border-slate-200 bg-slate-50 text-slate-700'

  return (
    <section
      className={clsx(
        'min-w-0 rounded-2xl border p-3',
        isHero ? 'border-white/20 bg-white/10' : 'border-slate-200 bg-white',
        compact && 'p-2',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className={clsx('text-xs font-semibold', titleClass)}>
            {t('app.candidate_card.stage_journey.title', { defaultValue: 'Stage journey' })}
          </div>
          {!compact ? (
            <>
              <div className={clsx('mt-0.5 text-[11px]', subClass)}>
                {currentStage
                  ? t('app.candidate_card.stage_journey.current', { defaultValue: 'Current' }) +
                    ': ' +
                    (stages.find((s) => s.code === currentStage)?.label || currentStage)
                  : t('common.labels.not_available')}
              </div>
              {signals && signals.length ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  {signals.slice(0, 4).map((s) => (
                    <span
                      key={s.key}
                      className={clsx('inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium', badgeClass)}
                    >
                      {s.label}
                    </span>
                  ))}
                </div>
              ) : null}
              {sinceLabel ? (
                <div className={clsx('mt-1 text-[11px]', subClass)} title={sinceLabel.abs}>
                  {t('app.candidate_card.stage_journey.since', { defaultValue: 'In stage' })}:{' '}
                  <span className={isHero ? 'text-white/90' : 'text-slate-700'}>{sinceLabel.rel || sinceLabel.abs}</span>
                </div>
              ) : null}
            </>
          ) : null}
        </div>
        <div className="shrink-0 flex flex-wrap items-center gap-2">
          {onOpenChangeLog ? (
            <button type="button" className={compact ? 'btn-secondary btn-xs' : 'btn-secondary btn-sm'} onClick={onOpenChangeLog}>
              {t('app.candidate_card.change_log.title', { defaultValue: 'Change log' })}
            </button>
          ) : null}
          {onOpenStageHistory ? (
            <button type="button" className={compact ? 'btn-secondary btn-xs' : 'btn-secondary btn-sm'} onClick={onOpenStageHistory}>
              {t('app.candidate_card.history.modal.title', { defaultValue: 'Stage history' })}
            </button>
          ) : null}
        </div>
      </div>

      {variant === 'horizontal' ? (
        <div className={clsx('mt-3', compact && 'mt-2')}>
          <div
            className={clsx(
              'relative min-w-0 overflow-x-auto rounded-xl border px-3 py-3',
              isHero ? 'border-white/20 bg-white/5' : 'border-slate-200 bg-white',
              compact && 'px-2 py-2',
            )}
          >
            <div className={clsx('min-w-[520px]', compact && 'min-w-[420px]')}>
              <div className={clsx('absolute left-6 right-6 top-[18px] h-px', isHero ? 'bg-white/20' : 'bg-slate-200')} />
              <div className="relative flex items-start justify-between gap-4">
                {stages.map((s, idx) => {
                  const isCurrent = currentStage ? s.code === currentStage : idx === 0
                  const isCompleted = completedStageCodes?.has(s.code) || (currentIdx >= 0 && idx < currentIdx)
                  const dotClass = isCurrent
                    ? (blocked ? 'bg-rose-600 ring-rose-200' : 'bg-brand-600 ring-brand-200')
                    : isCompleted
                      ? 'bg-emerald-500 ring-emerald-100'
                      : 'bg-slate-300 ring-slate-100'
                  const labelClass = isCurrent ? 'text-slate-900' : isCompleted ? 'text-slate-700' : 'text-slate-500'

                  return (
                    <div key={s.code} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                      <button
                        type="button"
                        disabled={!canEdit || !onStageChange || isCurrent}
                        onClick={() => onStageChange?.(s.code)}
                        className={clsx(
                          compact ? 'h-[18px] w-[18px] ring-[3px]' : 'h-[22px] w-[22px] ring-4',
                          'rounded-full transition-colors',
                          dotClass,
                          canEdit && onStageChange && !isCurrent ? 'hover:opacity-90' : 'cursor-default',
                        )}
                        title={
                          canEdit && onStageChange && !isCurrent
                            ? t('app.candidate_card.stage_journey.change_to', { defaultValue: 'Change stage to' }) + ` ${s.label}`
                            : s.label
                        }
                      />
                      <div className={clsx('text-[11px]', 'font-semibold text-center leading-snug', labelClass, isHero && 'text-white/85')}>
                        {s.label}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-3 relative">
          <div className="absolute left-[9px] top-2 bottom-2 w-px bg-slate-200" />
          <div className="space-y-2">
            {stages.map((s, idx) => {
              const isCurrent = currentStage ? s.code === currentStage : idx === 0
              const isCompleted = completedStageCodes?.has(s.code) || (currentIdx >= 0 && idx < currentIdx)
              const dotClass = isCurrent
                ? (blocked ? 'bg-rose-600 ring-rose-200' : 'bg-brand-600 ring-brand-200')
                : isCompleted
                  ? 'bg-emerald-500 ring-emerald-100'
                  : 'bg-slate-300 ring-slate-100'
              const labelClass = isCurrent ? 'text-slate-900' : isCompleted ? 'text-slate-700' : 'text-slate-500'

              return (
                <div key={s.code} className="flex items-start gap-3">
                  <div className={clsx('mt-1 h-[18px] w-[18px] rounded-full ring-4 transition-colors', dotClass)} />
                  <button
                    type="button"
                    disabled={!canEdit || !onStageChange || isCurrent}
                    onClick={() => onStageChange?.(s.code)}
                    className={clsx(
                      'min-w-0 flex-1 text-left rounded-lg px-2 py-1.5 transition',
                      canEdit && onStageChange && !isCurrent ? 'hover:bg-slate-50' : '',
                    )}
                    title={
                      canEdit && onStageChange && !isCurrent
                        ? t('app.candidate_card.stage_journey.change_to', { defaultValue: 'Change stage to' }) + ` ${s.label}`
                        : undefined
                    }
                  >
                    <div className={clsx('text-sm font-medium truncate', labelClass)}>{s.label}</div>
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {outcomeStages && outcomeStages.length && !compact ? (
        <div className="mt-4">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            {t('app.candidate_card.stage_journey.outcomes', { defaultValue: 'Outcomes' })}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {outcomeStages.map((s) => {
              const isCurrent = Boolean(currentOutcomeStage && s.code === currentOutcomeStage)
              return (
                <button
                  key={s.code}
                  type="button"
                  disabled={!canEdit || !onStageChange || isCurrent}
                  onClick={() => onStageChange?.(s.code)}
                  className={clsx(
                    'rounded-full border px-3 py-1 text-xs font-medium',
                    isCurrent
                      ? 'border-rose-200 bg-rose-50 text-rose-800'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
                    (!canEdit || !onStageChange) && 'opacity-60',
                  )}
                  title={canEdit && onStageChange && !isCurrent
                    ? t('app.candidate_card.stage_journey.change_to', { defaultValue: 'Change stage to' }) + ` ${s.label}`
                    : undefined}
                >
                  {s.label}
                </button>
              )
            })}
          </div>
        </div>
      ) : null}
    </section>
  )
}

