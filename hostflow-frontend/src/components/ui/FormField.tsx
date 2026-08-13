import clsx from 'clsx'
import type { PropsWithChildren, ReactNode } from 'react'

export type FormFieldProps = PropsWithChildren<{
  label?: ReactNode
  htmlFor?: string
  required?: boolean
  error?: string
  hint?: string
  className?: string
}>

export function FormField({
  label,
  htmlFor,
  required,
  error,
  hint,
  className,
  children,
}: FormFieldProps) {
  return (
    <div className={clsx('space-y-1', className)}>
      {label ? (
        <label className="label" htmlFor={htmlFor}>
          {label}
          {required ? <span className="text-rose-700"> *</span> : null}
        </label>
      ) : null}
      {children}
      {error || hint ? (
        <div className={clsx('text-xs', error ? 'text-rose-700' : 'text-slate-500')}>{error || hint}</div>
      ) : null}
    </div>
  )
}
