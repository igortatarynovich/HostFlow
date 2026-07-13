import type { ReactNode } from 'react'
import { IconSettings } from '@tabler/icons-react'
import { DataTableSearchBar } from './ColumnManagerPanel'

export type ListWorkspaceToolbarProps = {
  searchValue: string
  onSearchChange: (value: string) => void
  searchPlaceholder?: string
  onConfigureTable?: () => void
  configureLabel?: string
  trailing?: ReactNode
}

/** Standard toolbar above Universal Data Table — search + configure columns. */
export function ListWorkspaceToolbar({
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Поиск по имени, email, телефону, компании…',
  onConfigureTable,
  configureLabel = 'Настроить таблицу',
  trailing,
}: ListWorkspaceToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="min-w-[12rem] flex-1">
        <DataTableSearchBar value={searchValue} onChange={onSearchChange} placeholder={searchPlaceholder} />
      </div>
      {onConfigureTable ? (
        <button
          type="button"
          onClick={onConfigureTable}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <IconSettings size={16} />
          {configureLabel}
        </button>
      ) : null}
      {trailing}
    </div>
  )
}

export type ListWorkspaceStatusTabsProps = {
  tabs: Array<{ id: string; label: string; count?: number }>
  activeId: string
  onChange: (id: string) => void
}

export function ListWorkspaceStatusTabs({ tabs, activeId, onChange }: ListWorkspaceStatusTabsProps) {
  return (
    <div className="flex flex-wrap gap-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={
            activeId === tab.id
              ? 'rounded-lg bg-brand-700 px-3 py-1.5 text-sm font-medium text-white'
              : 'rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'
          }
        >
          {tab.label}
          {tab.count != null ? ` ${tab.count}` : ''}
        </button>
      ))}
    </div>
  )
}
