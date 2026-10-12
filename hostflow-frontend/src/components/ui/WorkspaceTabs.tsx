import clsx from 'clsx'
import type { ReactNode } from 'react'

export type WorkspaceTabItem = {
  id: string
  label: string
  badge?: ReactNode
}

export function WorkspaceTabs({
  items,
  value,
  onChange,
  ariaLabel,
}: {
  items: WorkspaceTabItem[]
  value: string
  onChange: (id: string) => void
  ariaLabel?: string
}) {
  return (
    <div className="flex gap-0.5 overflow-x-auto border-b border-slate-200" role="tablist" aria-label={ariaLabel}>
      {items.map((item) => {
        const selected = item.id === value
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={selected}
            className={clsx(
              '-mb-px inline-flex shrink-0 items-center gap-1.5 rounded-t-lg border-b-2 px-3 py-1.5 text-sm',
              selected
                ? 'border-brand-600 bg-brand-50 font-semibold text-brand-800'
                : 'border-transparent font-medium text-slate-500 hover:bg-slate-50 hover:text-slate-800',
            )}
            onClick={() => onChange(item.id)}
          >
            <span>{item.label}</span>
            {item.badge}
          </button>
        )
      })}
    </div>
  )
}
