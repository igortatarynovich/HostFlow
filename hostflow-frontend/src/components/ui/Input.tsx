import clsx from 'clsx'
import type { InputHTMLAttributes } from 'react'

export type InputProps = InputHTMLAttributes<HTMLInputElement>

/** Kit public API over `.input` CSS (INPUT_V1 visual source). */
export function Input({ className, type = 'text', ...rest }: InputProps) {
  return <input type={type} className={clsx('input', className)} {...rest} />
}
