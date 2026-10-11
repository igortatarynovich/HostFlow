import clsx from 'clsx'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'link' | 'icon'
export type ButtonSize = 'md' | 'sm' | 'xs' | 'compact'

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'btn btn-primary',
  secondary: 'btn btn-secondary',
  danger: 'btn btn-danger',
  ghost: 'btn btn-ghost',
  link: 'inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:text-brand-800 hover:underline',
  icon: 'btn-icon',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  md: '',
  sm: 'btn-sm',
  xs: 'btn-xs',
  compact: 'btn-compact',
}

export type ButtonProps = {
  variant?: ButtonVariant
  size?: ButtonSize
  href?: string
  children: ReactNode
  className?: string
  type?: 'button' | 'submit' | 'reset'
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'type' | 'children' | 'className'>

function buttonClasses(variant: ButtonVariant, size: ButtonSize, className?: string) {
  if (variant === 'icon') {
    const iconSize = size === 'md' ? '' : 'btn-icon-sm'
    return clsx(VARIANT_CLASSES.icon, iconSize, className)
  }
  if (variant === 'link') return clsx(VARIANT_CLASSES.link, className)
  return clsx(VARIANT_CLASSES[variant], SIZE_CLASSES[size], className)
}

export function Button({
  variant = 'secondary',
  size = 'md',
  href,
  children,
  className,
  type = 'button',
  disabled,
  ...rest
}: ButtonProps) {
  const classes = buttonClasses(variant, size, className)

  if (variant === 'link' && href && !disabled) {
    const { onClick, 'aria-label': ariaLabel, title } = rest
    return (
      <Link to={href} className={classes} onClick={onClick} aria-label={ariaLabel} title={title}>
        {children}
      </Link>
    )
  }

  return (
    <button type={type} className={classes} disabled={disabled} {...rest}>
      {children}
    </button>
  )
}
