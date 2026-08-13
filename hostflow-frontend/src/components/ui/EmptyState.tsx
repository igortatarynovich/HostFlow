import clsx from 'clsx'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { Button } from './Button'

export type EmptyStateAction = {
  label: string
  to?: string
  onClick?: () => void
}

function EmptyStateActionControl({
  action,
  variant,
}: {
  action: EmptyStateAction
  variant: 'primary' | 'secondary'
}) {
  if (action.to) {
    return (
      <Link to={action.to} className={`${variant === 'primary' ? 'btn-primary' : 'btn-secondary'} inline-flex items-center gap-1.5 px-3 py-1.5 text-xs`}>
        {action.label}
      </Link>
    )
  }
  return (
    <Button variant={variant} size="xs" onClick={action.onClick}>
      {action.label}
    </Button>
  )
}

export type EmptyStateProps = {
  title: string
  description: string
  whyHint?: string
  primaryAction?: EmptyStateAction
  secondaryAction?: EmptyStateAction
  compact?: boolean
  className?: string
  children?: ReactNode
}

export function EmptyState({
  title,
  description,
  whyHint,
  primaryAction,
  secondaryAction,
  compact = false,
  className,
  children,
}: EmptyStateProps) {
  return (
    <div
      className={clsx(
        'mx-auto border border-dashed border-slate-300 bg-slate-50/60 text-center',
        compact ? 'max-w-2xl p-5' : 'max-w-3xl p-8',
        className,
      )}
    >
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mx-auto mt-1 max-w-xl text-xs text-slate-600">{description}</p>
      {whyHint ? (
        <p className="mx-auto mt-3 max-w-xl bg-amber-50 px-3 py-2 text-left text-[11px] text-amber-900">
          {whyHint}
        </p>
      ) : null}
      {children}
      {(primaryAction || secondaryAction) && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          {primaryAction ? <EmptyStateActionControl action={primaryAction} variant="primary" /> : null}
          {secondaryAction ? <EmptyStateActionControl action={secondaryAction} variant="secondary" /> : null}
        </div>
      )}
    </div>
  )
}
