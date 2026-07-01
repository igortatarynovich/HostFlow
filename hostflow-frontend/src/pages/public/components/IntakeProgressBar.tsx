import type { IntakeStep } from '../../../modules/public-intake/types'

const STEP_ORDER: IntakeStep[] = ['language', 'contacts', 'questions', 'employment', 'documents', 'review']
const STEP_INDEX: Record<IntakeStep, number> = STEP_ORDER.reduce((acc, s, i) => {
  acc[s] = i
  return acc
}, {} as Record<IntakeStep, number>)

type Props = {
  currentStep: IntakeStep
  className?: string
  timeEstimate?: string
}

export function IntakeProgressBar({ currentStep, className = '', timeEstimate }: Props) {
  const current = STEP_INDEX[currentStep] ?? 0
  const total = STEP_ORDER.length
  const percent = total > 1 ? Math.round((current / (total - 1)) * 100) : 0
  const showTimeEstimate = ['language', 'contacts'].includes(currentStep) && timeEstimate

  return (
    <div className={className}>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-brand-600 transition-all duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="mt-1 flex items-center justify-between gap-2 text-xs text-slate-500">
        <span>{current + 1} / {total}</span>
        {showTimeEstimate && (
          <span>{timeEstimate}</span>
        )}
      </div>
    </div>
  )
}
