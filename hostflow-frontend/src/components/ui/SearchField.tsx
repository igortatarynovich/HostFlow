import clsx from 'clsx'
import { forwardRef, type InputHTMLAttributes } from 'react'

import { Input } from './Input'

export type SearchFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>

export const SearchField = forwardRef<HTMLInputElement, SearchFieldProps>(function SearchField(
  { className, ...rest },
  ref,
) {
  return <Input ref={ref} type="search" className={clsx(className)} {...rest} />
})
