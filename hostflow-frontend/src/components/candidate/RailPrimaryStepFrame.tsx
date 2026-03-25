import type { ReactNode } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'

/**
 * Groups rail blocks (e.g. contact attempts + RODO) and highlights the single pipeline-priority step.
 */
export default function RailPrimaryStepFrame({
  active,
  className,
  children,
}: {
  active: boolean
  className?: string
  children: ReactNode
}) {
  const { t } = useI18n()
  return (
    <div
      className={clsx(
        'rounded-2xl transition-shadow duration-200',
        active && 'ring-2 ring-amber-400/95 ring-offset-2 ring-offset-white shadow-sm shadow-amber-500/10',
        className,
      )}
      data-rail-primary-step={active ? 'true' : undefined}
    >
      {active ? (
        <div className="mb-2 px-0.5">
          <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-950">
            {t('app.candidate_card.rail.primary_step_badge', { defaultValue: 'Next step' })}
          </span>
        </div>
      ) : null}
      {children}
    </div>
  )
}
