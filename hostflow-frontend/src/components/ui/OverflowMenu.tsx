import { useEffect, useRef, useState } from 'react'
import clsx from 'clsx'

export type OverflowMenuItem = {
  id: string
  label: string
  onSelect: () => void
  disabled?: boolean
  tone?: 'default' | 'danger'
}

/**
 * Shared overflow menu for secondary record actions.
 * Callers supply items. This widget does not own the actions.
 */
export function OverflowMenu({
  label,
  items,
  appearance = 'default',
}: {
  label: string
  items: OverflowMenuItem[]
  appearance?: 'default' | 'inverse'
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointer = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (!items.length) return null

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className={clsx(
          'inline-flex h-8 w-8 items-center justify-center rounded-lg border text-base leading-none',
          appearance === 'inverse'
            ? 'border-white/30 bg-white/10 text-white hover:bg-white/20'
            : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
        )}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label}
        onClick={() => setOpen((value) => !value)}
      >
        ⋯
      </button>
      {open ? (
        <div role="menu" className="absolute right-0 z-30 mt-1 min-w-44 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              disabled={item.disabled}
              className={clsx(
                'block w-full px-3 py-1.5 text-left text-sm disabled:opacity-50',
                item.tone === 'danger' ? 'text-rose-700 hover:bg-rose-50' : 'text-slate-800 hover:bg-slate-50',
              )}
              onClick={() => {
                setOpen(false)
                item.onSelect()
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
