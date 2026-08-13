import clsx from 'clsx'
import type { InputHTMLAttributes } from 'react'

import { Input } from './Input'

export type SearchFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>

export function SearchField({ className, ...rest }: SearchFieldProps) {
  return <Input type="search" className={clsx(className)} {...rest} />
}
