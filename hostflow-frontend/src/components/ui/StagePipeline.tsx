import clsx from 'clsx'

export type StagePipelineStep = {
  code: string
  label: string
  /** Short status under the stage name. Presentation only. */
  secondary?: string | null
}

export type StagePipelineProps = {
  stages: StagePipelineStep[]
  currentCode?: string | null
  /** Explicit completions. Stages before the current one are completed when omitted. */
  completedCodes?: ReadonlySet<string>
  blocked?: boolean
  ariaLabel?: string
  className?: string
}

/**
 * Shared horizontal stage track for recruitment funnels and employment preparation.
 * Callers supply the stage list. This widget does not own stage meaning or transitions.
 */
export function StagePipeline({
  stages,
  currentCode,
  completedCodes,
  blocked = false,
  ariaLabel,
  className,
}: StagePipelineProps) {
  if (!stages.length) return null

  const currentIdx = currentCode ? stages.findIndex((stage) => stage.code === currentCode) : -1
  const completedCount = stages.filter((stage, index) => {
    if (completedCodes?.has(stage.code)) return true
    return currentIdx >= 0 && index < currentIdx
  }).length

  return (
    <div className={clsx('flex min-w-0 items-start gap-3', className)}>
      <ol className="flex min-w-0 flex-1 items-start overflow-x-auto" aria-label={ariaLabel}>
        {stages.map((stage, index) => {
          const isCurrent = currentCode ? stage.code === currentCode : index === 0
          const isCompleted = completedCodes?.has(stage.code) || (currentIdx >= 0 && index < currentIdx)
          const isLast = index === stages.length - 1
          return (
            <li key={stage.code} className="flex min-w-0 flex-1 items-start">
              <div className="flex w-full min-w-0 flex-col items-center">
                <div className="flex w-full items-center">
                  <span
                    className={clsx('h-0.5 flex-1', index === 0 ? 'bg-transparent' : isCompleted || isCurrent ? 'bg-emerald-400' : 'bg-slate-200')}
                    aria-hidden
                  />
                  <span
                    className={clsx(
                      'flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold',
                      isCurrent && 'bg-white text-brand-700 ring-2 ring-brand-600',
                      !isCurrent && isCompleted && 'bg-emerald-500 text-white',
                      !isCurrent && !isCompleted && 'border border-slate-300 bg-white text-slate-300',
                    )}
                    aria-current={isCurrent ? 'step' : undefined}
                    aria-invalid={isCurrent && blocked ? true : undefined}
                  >
                    {isCompleted && !isCurrent ? '✓' : isCurrent ? '●' : ''}
                  </span>
                  <span
                    className={clsx('h-0.5 flex-1', isLast ? 'bg-transparent' : isCompleted ? 'bg-emerald-400' : 'bg-slate-200')}
                    aria-hidden
                  />
                </div>
                <span
                  title={stage.label}
                  className={clsx(
                    'mt-1 w-full truncate px-0.5 text-center text-[10px] leading-tight',
                    isCurrent ? 'font-semibold text-slate-900' : isCompleted ? 'font-medium text-slate-600' : 'font-medium text-slate-400',
                  )}
                >
                  {stage.label}
                </span>
                {stage.secondary ? (
                  <span className="px-1 text-center text-[10px] leading-snug text-slate-500">{stage.secondary}</span>
                ) : null}
              </div>
            </li>
          )
        })}
      </ol>
      <div className="shrink-0 pt-0.5 text-sm font-semibold tabular-nums text-slate-700">
        {currentIdx >= 0 ? currentIdx + 1 : completedCount} / {stages.length}
      </div>
    </div>
  )
}
