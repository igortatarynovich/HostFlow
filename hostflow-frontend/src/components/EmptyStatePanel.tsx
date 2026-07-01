import { IconArrowRight, IconBulb, IconSparkles } from '@tabler/icons-react'
import { Link } from 'react-router-dom'

type Action = {
  label: string
  to?: string
  onClick?: () => void
  variant?: 'primary' | 'secondary'
}

type EmptyStatePanelProps = {
  title: string
  description: string
  /**
   * Optional «зачем это» microcopy shown as a soft hint under the description.
   * Used during the first 7 days after signup to explain *why* a screen exists
   * even before the user has data — see Phase 2 #5 (HOSTFLOW_AUDIT_AND_PLAN.md).
   */
  whyHint?: string
  primaryAction?: Action
  secondaryAction?: Action
  compact?: boolean
}

function ActionButton({ action }: { action: Action }) {
  const className =
    action.variant === 'secondary'
      ? 'btn-secondary inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs'
      : 'btn-primary inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs'
  const content = (
    <>
      <span>{action.label}</span>
      <IconArrowRight size={14} stroke={1.9} />
    </>
  )
  if (action.to) {
    return (
      <Link to={action.to} className={className}>
        {content}
      </Link>
    )
  }
  return (
    <button type="button" onClick={action.onClick} className={className}>
      {content}
    </button>
  )
}

export default function EmptyStatePanel({
  title,
  description,
  whyHint,
  primaryAction,
  secondaryAction,
  compact = false,
}: EmptyStatePanelProps) {
  return (
    <div className={`mx-auto rounded-xl border border-dashed border-slate-300 bg-slate-50/60 text-center ${compact ? 'max-w-2xl p-5' : 'max-w-3xl p-8'}`}>
      <div className="mx-auto inline-flex h-10 w-10 items-center justify-center rounded-full bg-white text-brand-700 shadow-sm">
        <IconSparkles size={18} stroke={1.9} />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mx-auto mt-1 max-w-xl text-xs text-slate-600">{description}</p>
      {whyHint ? (
        <p className="mx-auto mt-3 inline-flex max-w-xl items-start gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-left text-[11px] text-amber-900">
          <IconBulb size={14} className="mt-0.5 shrink-0 text-amber-600" stroke={1.9} aria-hidden />
          <span>{whyHint}</span>
        </p>
      ) : null}
      {(primaryAction || secondaryAction) && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          {primaryAction && <ActionButton action={primaryAction} />}
          {secondaryAction && <ActionButton action={{ ...secondaryAction, variant: 'secondary' }} />}
        </div>
      )}
    </div>
  )
}
