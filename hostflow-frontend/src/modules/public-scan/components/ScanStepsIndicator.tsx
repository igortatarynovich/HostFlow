import { memo } from 'react'
import type { TranslateFn } from '@i18n'

type WizardStep = {
  code: string
  index: number
  optional: boolean
  label: string
  page?: {
    status?: string | null
  } | null
}

type ScanStepsIndicatorProps = {
  steps: WizardStep[]
  activePageCode: string | null
  formatStepStatus: (statusKey?: string | null) => { key: string; text: string; tone: string }
  onStepClick: (code: string) => void
  translate: TranslateFn
}

export const ScanStepsIndicator = memo(function ScanStepsIndicator({
  steps,
  activePageCode,
  formatStepStatus,
  onStepClick,
  translate,
}: ScanStepsIndicatorProps) {
  return (
    <section className="mb-4 hidden md:block">
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {steps.map((step, idx) => {
          const status = formatStepStatus(step.page?.status)
          const isActive = activePageCode === step.code
          const isComplete = step.page && step.page.status !== 'pending'

          return (
            <div key={step.code} className="flex items-center gap-2 flex-shrink-0">
              <button
                type="button"
                onClick={() => onStepClick(step.code)}
                className={`relative flex items-center gap-3 rounded-xl border-2 px-4 py-3 transition-all ${
                  isActive
                    ? 'border-brand-500 bg-brand-50 shadow-md scale-105'
                    : isComplete
                    ? 'border-emerald-300 bg-emerald-50'
                    : 'border-slate-200 bg-white'
                } ${isActive ? 'ring-2 ring-brand-200' : ''}`}
              >
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
                    isComplete
                      ? 'bg-emerald-500 text-white'
                      : isActive
                      ? 'bg-brand-500 text-white'
                      : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  {isComplete ? '✓' : idx + 1}
                </div>
                <div className="text-left">
                  <p
                    className={`text-sm font-semibold ${
                      isActive ? 'text-brand-900' : isComplete ? 'text-emerald-900' : 'text-slate-700'
                    }`}
                  >
                    {step.label}
                  </p>
                  <p
                    className={`text-xs ${
                      isActive ? 'text-brand-600' : isComplete ? 'text-emerald-600' : 'text-slate-500'
                    }`}
                  >
                    {status.text}
                  </p>
                </div>
              </button>
              {idx < steps.length - 1 && (
                <div className={`h-0.5 w-8 ${isComplete ? 'bg-emerald-300' : 'bg-slate-200'}`} />
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
})

