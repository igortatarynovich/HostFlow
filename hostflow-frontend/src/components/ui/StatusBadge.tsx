import clsx from 'clsx'

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
  className?: string
}

export function StatusBadge({
  label,
  semantic,
  size = 'md',
  title,
  inverse = false,
  shape = 'default',
  className,
}: StatusBadgeProps) {
  const palette = inverse ? STATUS_BADGE_SEMANTIC_CLASSES_INVERSE : STATUS_BADGE_SEMANTIC_CLASSES
  return (
    <span
      className={clsx(
        'inline-flex max-w-full items-center truncate font-medium',
        shape === 'pill' ? 'rounded-full' : 'rounded-md',
        STATUS_BADGE_SIZE_CLASSES[size],
        palette[semantic],
        className,
      )}
      title={title ?? label}
    >
      {label}
    </span>
  )
}
