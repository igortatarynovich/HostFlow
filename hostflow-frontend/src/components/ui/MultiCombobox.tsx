import clsx from 'clsx'
import { useMemo, useState } from 'react'

import { type ComboboxOption, useClickOutside } from './comboboxShared'

export type MultiComboboxProps = {
  options: ComboboxOption[]
  values: string[]
  onChange: (values: string[]) => void
  disabled?: boolean
  placeholder?: string
  searchPlaceholder?: string
  noResultsLabel?: string
  multiSelectedLabel?: (count: number) => string
  className?: string
}

export function MultiCombobox({
  options,
  values,
  onChange,
  disabled,
  placeholder = 'Not selected',
  searchPlaceholder = 'Search…',
  noResultsLabel = 'No matches',
  multiSelectedLabel,
  className,
}: MultiComboboxProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const boxRef = useClickOutside<HTMLDivElement>(() => setOpen(false))

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return options
    return options.filter(
      (option) =>
        option.label.toLowerCase().includes(needle) ||
        option.value.toLowerCase().includes(needle),
    )
  }, [query, options])

  const toggle = (value: string) => {
    if (disabled) return
    const set = new Set(values)
    if (set.has(value)) set.delete(value)
    else set.add(value)
    onChange(Array.from(set))
  }

  const caption =
    values.length === 0
      ? placeholder
      : values.length <= 3
        ? values
            .map((value) => options.find((option) => option.value === value)?.label || value)
            .join(', ')
        : multiSelectedLabel
          ? multiSelectedLabel(values.length)
          : `${values.length} selected`

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
        {caption}
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
          <div className="max-h-72 overflow-auto">
            {filtered.length === 0 && (
              <div className="px-3 py-2 text-sm text-slate-500">{noResultsLabel}</div>
            )}
            {filtered.map((option) => {
              const checked = values.includes(option.value)
              return (
                <label
                  key={option.value}
                  className={clsx(
                    'flex cursor-pointer items-center gap-3 px-3 py-2',
                    disabled ? 'cursor-not-allowed text-slate-500' : 'hover:bg-slate-50',
                  )}
                  onClick={() => toggle(option.value)}
                >
                  <input type="checkbox" readOnly checked={checked} />
                  <span>{option.label}</span>
                </label>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
