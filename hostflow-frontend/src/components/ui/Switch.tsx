import clsx from 'clsx'
import type { InputHTMLAttributes } from 'react'

export type SwitchProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label?: string
}

export function Switch({ className, label, id, checked, ...rest }: SwitchProps) {
  const input = (
    <span className={clsx('relative inline-flex h-5 w-9 shrink-0 items-center', className)}>
      <input
        id={id}
        type="checkbox"
        role="switch"
        className="peer sr-only"
        checked={checked}
        {...rest}
      />
      <span
        aria-hidden
        className="h-5 w-9 border border-slate-300 bg-slate-200 transition-colors peer-checked:border-brand-600 peer-checked:bg-brand-600 peer-focus:ring-4 peer-focus:ring-brand-100 peer-disabled:opacity-50 rounded-full"
      />
      <span
        aria-hidden
        className="pointer-events-none absolute left-0.5 top-0.5 h-4 w-4 bg-white transition-transform peer-checked:translate-x-4 rounded-full"
      />
    </span>
  )
  if (!label) return input
  return (
    <label htmlFor={id} className="inline-flex items-center gap-2 text-sm text-slate-700">
      {input}
      <span>{label}</span>
    </label>
  )
}
