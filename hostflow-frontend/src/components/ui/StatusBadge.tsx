import clsx from 'clsx'
import type { ReactNode } from 'react'

import {
  STATUS_BADGE_SEMANTIC_CLASSES,
  STATUS_BADGE_SEMANTIC_CLASSES_INVERSE,
  STATUS_BADGE_SIZE_CLASSES,
  type StatusBadgeSemantic,
  type StatusBadgeSize,
} from './statusBadgeSemantics'

export type StatusBadgeProps = {
  label: string
  semantic: StatusBadgeSemantic
  size?: StatusBadgeSize
  title?: string
  /** Coloured pills on dark headers (e.g. entity header). */
  inverse?: boolean
  /** `pill` = fully rounded (document status). */
  shape?: 'default' | 'pill'
  icon?: ReactNode
  className?: string
}

export function StatusBadge({
  label,
  semantic,
  size = 'md',
  title,
  inverse = false,
  shape = 'default',
  icon,
  className,
}: StatusBadgeProps) {
  const palette = inverse ? STATUS_BADGE_SEMANTIC_CLASSES_INVERSE : STATUS_BADGE_SEMANTIC_CLASSES
  return (
    <span
      className={clsx(
        'inline-flex max-w-full items-center gap-1 truncate font-medium',
        shape === 'pill' ? 'rounded-full' : 'rounded-md',
        STATUS_BADGE_SIZE_CLASSES[size],
        palette[semantic],
        className,
      )}
      title={title ?? label}
    >
      {icon ? <span className="inline-flex shrink-0">{icon}</span> : null}
      {label}
    </span>
  )
}
