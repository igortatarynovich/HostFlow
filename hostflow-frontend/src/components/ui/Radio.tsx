import clsx from 'clsx'
import type { InputHTMLAttributes } from 'react'

export type RadioProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label?: string
}

export function Radio({ className, label, id, ...rest }: RadioProps) {
  const input = (
    <input id={id} type="radio" className={clsx('h-4 w-4 border-slate-300', className)} {...rest} />
  )
  if (!label) return input
  return (
    <label htmlFor={id} className="inline-flex items-center gap-2 text-sm text-slate-700">
      {input}
      <span>{label}</span>
    </label>
  )
}
