import clsx from 'clsx'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { IconChevronDown } from '@tabler/icons-react'

import { type ComboboxOption, menuBox, type MenuBox } from './comboboxShared'

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
  const [box, setBox] = useState<MenuBox | null>(null)
  const anchorRef = useRef<HTMLButtonElement | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)
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
      close()
    }
    function onEsc(event: KeyboardEvent) {
      if (event.key === 'Escape') close()
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
      {filtered.length === 0 && (
        <div className="px-3 py-2 text-sm text-slate-500">{noResultsLabel}</div>
      )}
      {filtered.map((option) => (
        <button
          key={option.value}
          type="button"
          className={clsx(
            'dropdown-item w-full text-left',
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
        <span className="min-w-0 truncate">{current || placeholder}</span>
        <IconChevronDown size={16} className="shrink-0 text-slate-400" />
      </button>
      {menu}
    </div>
  )
}
