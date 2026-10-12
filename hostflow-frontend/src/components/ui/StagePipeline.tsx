import type { ReactNode } from 'react'
import clsx from 'clsx'

export type StagePipelineMark = 'completed' | 'current' | 'pending' | 'blocked' | 'not_applicable'

export type StagePipelineStep = {
  code: string
  label: string
  /** Short status under the stage name. Presentation only. */
  secondary?: string | null
  /** Explicit mark. When omitted, current and completed come from currentCode. */
  mark?: StagePipelineMark
  onSelect?: (() => void) | null
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

function resolveMark(
  stage: StagePipelineStep,
  index: number,
  currentIdx: number,
  currentCode: string | null | undefined,
  completedCodes: ReadonlySet<string> | undefined,
  blocked: boolean,
): StagePipelineMark {
  if (stage.mark === 'not_applicable' || stage.mark === 'blocked' || stage.mark === 'completed' || stage.mark === 'pending') {
    return stage.mark
  }
  const isCurrent = stage.mark === 'current' || (stage.mark == null && (currentCode ? stage.code === currentCode : index === 0))
  const isCompleted =
    stage.mark == null && (completedCodes?.has(stage.code) || (currentIdx >= 0 && index < currentIdx))
  if (isCurrent && blocked) return 'blocked'
  if (isCurrent) return 'current'
  if (isCompleted) return 'completed'
  return 'pending'
}

/**
 * Shared horizontal stage track.
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
  const marks = stages.map((stage, index) =>
    resolveMark(stage, index, currentIdx, currentCode, completedCodes, blocked),
  )
  const completedCount = marks.filter((mark) => mark === 'completed').length
  const activeIdx = marks.findIndex((mark) => mark === 'current' || mark === 'blocked')
  const counterAt = activeIdx >= 0 ? activeIdx : currentIdx

  return (
    <div className={clsx('flex min-w-0 items-start gap-3', className)}>
      <ol className="flex min-w-0 flex-1 items-start overflow-x-auto" aria-label={ariaLabel}>
        {stages.map((stage, index) => {
          const mark = marks[index]
          const isLast = index === stages.length - 1
          const leftDone = index > 0 && (marks[index - 1] === 'completed' || mark === 'current' || mark === 'blocked' || mark === 'completed')
          const rightDone = mark === 'completed'
          const body: ReactNode = (
            <>
              <div className="flex w-full items-center">
                <span
                  className={clsx('h-0.5 flex-1', index === 0 ? 'bg-transparent' : leftDone ? 'bg-emerald-400' : 'bg-slate-200')}
                  aria-hidden
                />
                <span
                  className={clsx(
                    'flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold',
                    mark === 'blocked' && 'bg-white text-rose-700 ring-2 ring-rose-500',
                    mark === 'current' && 'bg-white text-brand-700 ring-2 ring-brand-600',
                    mark === 'completed' && 'bg-emerald-500 text-white',
                    (mark === 'pending' || mark === 'not_applicable') && 'border border-slate-300 bg-white text-slate-300',
                  )}
                  aria-current={mark === 'current' || mark === 'blocked' ? 'step' : undefined}
                  aria-invalid={mark === 'blocked' ? true : undefined}
                >
                  {mark === 'completed' ? '✓' : mark === 'current' || mark === 'blocked' ? '●' : mark === 'not_applicable' ? '–' : ''}
                </span>
                <span
                  className={clsx('h-0.5 flex-1', isLast ? 'bg-transparent' : rightDone ? 'bg-emerald-400' : 'bg-slate-200')}
                  aria-hidden
                />
              </div>
              <span
                title={stage.label}
                className={clsx(
                  'mt-1 w-full truncate px-0.5 text-center text-[10px] leading-tight',
                  mark === 'current' || mark === 'blocked' ? 'font-semibold text-slate-900' : mark === 'completed' ? 'font-medium text-slate-600' : 'font-medium text-slate-400',
                )}
              >
                {stage.label}
              </span>
              {stage.secondary ? (
                <span className="w-full truncate px-0.5 text-center text-[10px] leading-snug text-slate-500">{stage.secondary}</span>
              ) : null}
            </>
          )
          return (
            <li key={stage.code} className="flex min-w-0 flex-1 items-start">
              {stage.onSelect ? (
                <button type="button" className="flex w-full min-w-0 flex-col items-center bg-transparent" onClick={stage.onSelect}>
                  {body}
                </button>
              ) : (
                <div className="flex w-full min-w-0 flex-col items-center">{body}</div>
              )}
            </li>
          )
        })}
      </ol>
      <div className="shrink-0 pt-0.5 text-sm font-semibold tabular-nums text-slate-700">
        {counterAt >= 0 ? counterAt + 1 : completedCount} / {stages.length}
      </div>
    </div>
  )
}
