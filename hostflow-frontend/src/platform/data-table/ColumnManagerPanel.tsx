import clsx from 'clsx'
import type { ResourceSchema } from './types'

export type ColumnManagerPanelProps = {
  schema: ResourceSchema
  fieldLabels: Record<string, string>
  visibility: Record<string, boolean>
  onVisibilityChange: (next: Record<string, boolean>) => void
  orderedVisibleFieldIds: string[]
  onMoveFieldRelative: (fieldId: string, delta: -1 | 1) => void
  onResetLayout: () => void
  layoutCustomize: boolean
  onLayoutCustomizeChange: (value: boolean) => void
  title?: string
  hint?: string
  customizeOnLabel?: string
  customizeOffLabel?: string
  resetLabel?: string
  columnsTitle?: string
  moveUpTitle?: string
  moveDownTitle?: string
}

export function ColumnManagerPanel({
  schema,
  fieldLabels,
  visibility,
  onVisibilityChange,
  orderedVisibleFieldIds,
  onMoveFieldRelative,
  onResetLayout,
  layoutCustomize,
  onLayoutCustomizeChange,
  title = 'Table view',
  hint = 'Choose visible columns and order.',
  customizeOnLabel = 'Done editing',
  customizeOffLabel = 'Edit order & width in table',
  resetLabel = 'Reset order & widths',
  columnsTitle = 'Columns',
  moveUpTitle = 'Move column up',
  moveDownTitle = 'Move column down',
}: ColumnManagerPanelProps) {
  const allFieldIds = schema.fields.map((f) => f.id)
  const orderedKeysForPicker = (() => {
    const vis = new Set(orderedVisibleFieldIds)
    const rest = allFieldIds.filter((k) => !vis.has(k))
    return [...orderedVisibleFieldIds, ...rest]
  })()

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white px-2.5 py-2.5 shadow-sm">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mb-2 text-[11px] leading-snug text-slate-600">{hint}</p>

      <div className="mb-2 flex flex-wrap gap-1.5">
        <button
          type="button"
          className={
            layoutCustomize
              ? 'inline-flex items-center gap-1.5 rounded-md border border-brand-500 bg-brand-50 px-2 py-1.5 text-[11px] font-semibold text-brand-900 hover:bg-brand-100'
              : 'inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50'
          }
          onClick={() => onLayoutCustomizeChange(!layoutCustomize)}
        >
          {layoutCustomize ? customizeOnLabel : customizeOffLabel}
        </button>
        <button
          type="button"
          className="inline-flex items-center rounded-md border border-slate-200 bg-white px-2 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
          onClick={onResetLayout}
        >
          {resetLabel}
        </button>
      </div>

      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{columnsTitle}</div>
      <ul className="space-y-1 pr-0.5">
        {orderedKeysForPicker.map((fieldId) => {
          const visible = !!visibility[fieldId]
          const orderIdx = orderedVisibleFieldIds.indexOf(fieldId)
          const canMoveUp = visible && orderIdx > 0
          const canMoveDown = visible && orderIdx >= 0 && orderIdx < orderedVisibleFieldIds.length - 1
          return (
            <li
              key={fieldId}
              className="flex items-center gap-1 rounded-md border border-transparent px-0.5 py-0.5 hover:border-slate-100 hover:bg-slate-50/80"
            >
              <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  className="shrink-0"
                  checked={visible}
                  onChange={(e) => onVisibilityChange({ ...visibility, [fieldId]: e.currentTarget.checked })}
                />
                <span className="min-w-0 truncate">{fieldLabels[fieldId] ?? schema.fields.find((f) => f.id === fieldId)?.label ?? fieldId}</span>
              </label>
              {visible ? (
                <span className="flex shrink-0 items-center gap-0.5">
                  <button
                    type="button"
                    className="rounded border border-slate-200 px-1 py-0.5 text-[10px] leading-none text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                    disabled={!canMoveUp}
                    title={moveUpTitle}
                    onClick={() => onMoveFieldRelative(fieldId, -1)}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="rounded border border-slate-200 px-1 py-0.5 text-[10px] leading-none text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                    disabled={!canMoveDown}
                    title={moveDownTitle}
                    onClick={() => onMoveFieldRelative(fieldId, 1)}
                  >
                    ↓
                  </button>
                </span>
              ) : null}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export type DataTableSearchBarProps = {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export function DataTableSearchBar({ value, onChange, placeholder, className }: DataTableSearchBarProps) {
  return (
    <input
      type="search"
      className={clsx('input w-full min-w-[12rem] text-sm', className)}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      autoComplete="off"
    />
  )
}
