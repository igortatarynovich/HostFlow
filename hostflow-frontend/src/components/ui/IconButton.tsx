import clsx from 'clsx'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { Button } from './Button'

export type IconButtonProps = {
  /** Required accessible name — icon-only control. */
  'aria-label': string
  children: ReactNode
  className?: string
  type?: 'button' | 'submit' | 'reset'
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'type' | 'children' | 'className' | 'aria-label'>

export function IconButton({ children, className, type = 'button', ...rest }: IconButtonProps) {
  return (
    <Button variant="icon" type={type} className={clsx(className)} {...rest}>
      {children}
    </Button>
  )
}
