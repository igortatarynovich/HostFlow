import clsx from 'clsx'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export type ChipBehavior = 'static' | 'dismissible' | 'selectable' | 'action'

export type ChipSize = 'sm' | 'md'

export type ChipSelectedAppearance = 'solid' | 'soft'

export type ChipProps = {
  label: ReactNode
  behavior: ChipBehavior
  selected?: boolean
  /** Selectable chips: solid fill (presets) vs soft tint (shortcuts). */
  selectedAppearance?: ChipSelectedAppearance
  onDismiss?: () => void
  onClick?: () => void
  href?: string
  disabled?: boolean
  size?: ChipSize
  title?: string
  className?: string
  dismissLabel?: string
  /** Action/selectable: accessible name when label is not plain text. */
  ariaLabel?: string
}

const SIZE_CLASSES: Record<ChipSize, string> = {
  sm: 'text-[11px] px-2 py-0.5',
  md: 'text-xs px-2.5 py-1',
}

function chipTitle(label: ReactNode, title?: string) {
  return title ?? (typeof label === 'string' ? label : undefined)
}

function chipSurface(selected: boolean, disabled: boolean, selectedAppearance: ChipSelectedAppearance) {
  if (disabled) {
    return 'cursor-not-allowed border-slate-300 bg-slate-100 text-slate-500'
  }
  if (selected) {
    if (selectedAppearance === 'soft') {
      return 'border-brand-400 bg-brand-50 text-brand-900 shadow-sm hover:bg-brand-100/80'
    }
    return 'border-brand-600 bg-brand-600 text-white shadow-sm hover:bg-brand-700'
  }
  return 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'
}

function ChipInner({
  label,
  behavior,
  selected = false,
  selectedAppearance = 'solid',
  onDismiss,
  disabled = false,
  size = 'sm',
  title,
  className,
  dismissLabel = 'Remove',
}: Omit<ChipProps, 'onClick' | 'href'>) {
  const resolvedTitle = chipTitle(label, title)
  const base = clsx(
    'inline-flex max-w-full shrink-0 items-center gap-1 rounded-md border font-medium transition-colors',
    SIZE_CLASSES[size],
    behavior === 'static' ? 'border-slate-200 bg-white text-slate-700' : chipSurface(selected, disabled, selectedAppearance),
    className,
  )

  if (behavior === 'dismissible') {
    return (
      <span className={base} title={resolvedTitle}>
        <span className="min-w-0">{label}</span>
        {onDismiss && (
          <button
            type="button"
            className="ml-0.5 shrink-0 text-xs leading-none text-slate-500 hover:text-slate-800"
            onClick={onDismiss}
            aria-label={dismissLabel}
          >
            {'\u00D7'}
          </button>
        )}
      </span>
    )
  }

  return (
    <span className={base} title={resolvedTitle}>
      <span className="min-w-0 truncate">{label}</span>
    </span>
  )
}

export function Chip({
  label,
  behavior,
  selected = false,
  selectedAppearance = 'solid',
  onDismiss,
  onClick,
  href,
  disabled = false,
  size = 'sm',
  title,
  className,
  dismissLabel,
  ariaLabel,
}: ChipProps) {
  if (behavior === 'static') {
    return (
      <ChipInner
        label={label}
        behavior={behavior}
        size={size}
        title={title}
        className={className}
        dismissLabel={dismissLabel}
      />
    )
  }

  if (behavior === 'dismissible') {
    return (
      <ChipInner
        label={label}
        behavior={behavior}
        onDismiss={onDismiss}
        size={size}
        title={title}
        className={className}
        dismissLabel={dismissLabel}
      />
    )
  }

  const resolvedTitle = chipTitle(label, title)
  const interactiveClasses = clsx(
    'inline-flex max-w-full shrink-0 items-center rounded-md border font-medium transition-colors whitespace-nowrap',
    SIZE_CLASSES[size],
    chipSurface(selected, disabled, selectedAppearance),
    disabled && 'pointer-events-none',
    className,
  )

  if (behavior === 'action' && href && !disabled) {
    return (
      <Link
        to={href}
        className={interactiveClasses}
        title={resolvedTitle}
        aria-label={ariaLabel}
        onClick={onClick}
      >
        <span className="inline-flex min-w-0 items-center gap-1 truncate">{label}</span>
      </Link>
    )
  }

  return (
    <button
      type="button"
      className={interactiveClasses}
      title={resolvedTitle}
      aria-label={ariaLabel}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={behavior === 'selectable' ? selected : undefined}
    >
      <span className="inline-flex min-w-0 items-center gap-1 truncate">{label}</span>
    </button>
  )
}
