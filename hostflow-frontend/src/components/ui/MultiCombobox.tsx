import clsx from 'clsx'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { IconChevronDown } from '@tabler/icons-react'

import { type ComboboxOption } from './comboboxShared'

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

type MenuBox = { top: number; left: number; width: number; maxHeight: number }

function menuBox(anchor: HTMLElement): MenuBox {
  const rect = anchor.getBoundingClientRect()
  const roomBelow = window.innerHeight - rect.bottom - 8
  const roomAbove = rect.top - 8
  const openUp = roomBelow < 160 && roomAbove > roomBelow
  const maxHeight = Math.max(120, Math.min(288, openUp ? roomAbove : roomBelow))
  const top = openUp ? Math.max(8, rect.top - maxHeight - 8) : rect.bottom + 8
  return { top, left: rect.left, width: rect.width, maxHeight }
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
  const [box, setBox] = useState<MenuBox | null>(null)
  const anchorRef = useRef<HTMLButtonElement | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)

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

  useLayoutEffect(() => {
    if (!open || !anchorRef.current) return
    const place = () => {
      if (anchorRef.current) setBox(menuBox(anchorRef.current))
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => {
      window.removeEventListener('resize', place)
      window.removeEventListener('scroll', place, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    function onPointer(event: MouseEvent) {
      const target = event.target as Node
      if (anchorRef.current?.contains(target) || menuRef.current?.contains(target)) return
      setOpen(false)
    }
    function onEsc(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onEsc)
    }
  }, [open])

  const menu = open && box ? createPortal(
    <div
      ref={menuRef}
      className="fixed z-20 overflow-auto rounded-xl border border-gray-200 bg-white shadow-lg"
      style={{ top: box.top, left: box.left, width: box.width, maxHeight: box.maxHeight }}
    >
      <div className="p-2">
        <input
          autoFocus
          className="input w-full"
          placeholder={searchPlaceholder}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      <div>
        {filtered.length === 0 && (
          <div className="px-3 py-2 text-sm text-slate-500">{noResultsLabel}</div>
        )}
        {filtered.map((option) => {
          const checked = values.includes(option.value)
          return (
            <label
              key={option.value}
              className={clsx(
                'dropdown-item flex cursor-pointer items-center gap-3',
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
    </div>,
    document.body,
  ) : null

  return (
    <div className={clsx('relative', className)}>
      <button
        ref={anchorRef}
        type="button"
        className={clsx(
          'input flex w-full items-center justify-between gap-2 text-left',
          disabled && 'cursor-not-allowed bg-slate-100 text-slate-600',
        )}
        disabled={disabled}
        aria-expanded={open}
        onClick={() => {
          if (disabled) return
          setOpen((prev) => !prev)
          setQuery('')
        }}
      >
        <span className="min-w-0 truncate">{caption}</span>
        <IconChevronDown size={16} className="shrink-0 text-slate-400" />
      </button>
      {menu}
    </div>
  )
}
