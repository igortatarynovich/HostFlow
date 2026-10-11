import clsx from 'clsx'
import { IconAlertTriangle, IconCheck, IconCircle, IconPointFilled } from '@tabler/icons-react'

export type ProgressStep = {
  id: string
  label: string
  state: 'completed' | 'current' | 'pending' | 'blocked' | 'not_applicable'
  detail?: string | null
  onOpen?: (() => void) | null
}

function StepMark({ state }: { state: ProgressStep['state'] }) {
  if (state === 'completed') return <IconCheck size={17} aria-hidden />
  if (state === 'current') return <IconPointFilled size={18} aria-hidden />
  if (state === 'blocked') return <IconAlertTriangle size={17} aria-hidden />
  return <IconCircle size={16} aria-hidden />
}

export function ProgressStepper({ steps, label }: { steps: ProgressStep[]; label: string }) {
  return (
    <ol aria-label={label} className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
      {steps.map((step) => {
        const content = (
          <>
            <span
              className={clsx(
                'flex size-7 shrink-0 items-center justify-center rounded-full border',
                step.state === 'completed' && 'border-emerald-600 bg-emerald-600 text-white',
                step.state === 'current' && 'border-brand-600 bg-brand-50 text-brand-700',
                step.state === 'blocked' && 'border-amber-500 bg-amber-50 text-amber-700',
                (step.state === 'pending' || step.state === 'not_applicable') && 'border-slate-300 bg-white text-slate-400',
              )}
            >
              <StepMark state={step.state} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-medium text-slate-900">{step.label}</span>
              {step.detail ? <span className="mt-0.5 block text-xs text-slate-500">{step.detail}</span> : null}
            </span>
          </>
        )
        return (
          <li key={step.id} className="min-w-0">
            {step.onOpen ? (
              <button type="button" className="flex w-full items-start gap-2 rounded-lg p-2 text-left hover:bg-slate-50" onClick={step.onOpen}>
                {content}
              </button>
            ) : (
              <div className="flex items-start gap-2 p-2">{content}</div>
            )}
          </li>
        )
      })}
    </ol>
  )
}
