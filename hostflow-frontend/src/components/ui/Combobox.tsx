import clsx from 'clsx'
import { useMemo, useState } from 'react'

import { type ComboboxOption, useClickOutside } from './comboboxShared'

export type ComboboxProps = {
  options: ComboboxOption[]
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
  searchPlaceholder?: string
  noResultsLabel?: string
  className?: string
}

export function Combobox({
  options,
  value,
  onChange,
  disabled,
  placeholder = '— select —',
  searchPlaceholder = 'Search…',
  noResultsLabel = 'No matches',
  className,
}: ComboboxProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const current = useMemo(
    () => options.find((option) => option.value === value)?.label || '',
    [options, value],
  )
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return options
    return options.filter(
      (option) =>
        option.label.toLowerCase().includes(needle) ||
        option.value.toLowerCase().includes(needle),
    )
  }, [query, options])

  const close = () => setOpen(false)
  const boxRef = useClickOutside<HTMLDivElement>(close)

  return (
    <div className={clsx('relative', className)} ref={boxRef}>
      <button
        type="button"
        className={clsx(
          'input w-full text-left',
          disabled && 'cursor-not-allowed bg-slate-100 text-slate-600',
        )}
        disabled={disabled}
        onClick={() => {
          if (disabled) return
          setOpen((prev) => !prev)
          setQuery('')
        }}
      >
        {current || placeholder}
      </button>
      {open && (
        <div className="absolute z-50 mt-2 w-full rounded-xl border bg-white shadow-xl">
          <div className="p-2">
            <input
              autoFocus
              className="input w-full"
              placeholder={searchPlaceholder}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="max-h-64 overflow-auto">
            {filtered.length === 0 && (
              <div className="px-3 py-2 text-sm text-slate-500">{noResultsLabel}</div>
            )}
            {filtered.map((option) => (
              <button
                key={option.value}
                type="button"
                className={clsx(
                  'w-full px-3 py-2 text-left hover:bg-slate-50',
                  option.value === value && 'bg-slate-50',
                )}
                onClick={() => {
                  onChange(option.value)
                  close()
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
