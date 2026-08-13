import clsx from 'clsx'
import type { ReactNode } from 'react'

export type TabItem = {
  id: string
  label: ReactNode
  disabled?: boolean
}

export type TabsProps = {
  items: TabItem[]
  value: string
  onChange: (id: string) => void
  className?: string
  'aria-label'?: string
}

export function Tabs({ items, value, onChange, className, 'aria-label': ariaLabel }: TabsProps) {
  return (
    <div className={clsx('tabs', className)} role="tablist" aria-label={ariaLabel}>
      {items.map((item) => {
        const selected = item.id === value
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={selected}
            disabled={item.disabled}
            className={clsx('tab', selected && 'tab-active')}
            onClick={() => onChange(item.id)}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
