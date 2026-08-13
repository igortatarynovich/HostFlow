import clsx from 'clsx'
import { forwardRef, type InputHTMLAttributes } from 'react'

export type InputProps = InputHTMLAttributes<HTMLInputElement>

/** Kit public API over `.input` CSS (INPUT_V1 visual source). */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, type = 'text', ...rest },
  ref,
) {
  return <input ref={ref} type={type} className={clsx('input', className)} {...rest} />
})
