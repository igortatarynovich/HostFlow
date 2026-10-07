import { useEffect, useRef, useState, type ReactNode } from 'react'
import { IconDotsVertical } from '@tabler/icons-react'
import clsx from 'clsx'

export type ActionMenuItem = {
  id: string
  label: string
  onSelect: () => void
  disabled?: boolean
  danger?: boolean
}

export function ActionMenu({
  items,
  label,
  trigger,
  align = 'right',
}: {
  items: ActionMenuItem[]
  label: string
  trigger?: ReactNode
  align?: 'left' | 'right'
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', close)
    window.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', close)
      window.removeEventListener('keydown', closeOnEscape)
    }
  }, [open])

  if (items.length === 0) return null

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className="btn-icon"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {trigger ?? <IconDotsVertical size={20} aria-hidden />}
      </button>
      {open ? (
        <div
          role="menu"
          className={clsx(
            'absolute z-30 mt-1 min-w-56 rounded-lg border border-slate-200 bg-white p-1 shadow-lg',
            align === 'right' ? 'right-0' : 'left-0',
          )}
        >
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              className={clsx(
                'dropdown-item rounded-md text-sm disabled:cursor-not-allowed disabled:opacity-50',
                item.danger ? 'text-rose-700 hover:bg-rose-50' : 'text-slate-800',
              )}
              disabled={item.disabled}
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
