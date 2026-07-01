import { useMemo } from 'react'

type CandidatesTableViewRailSectionProps = {
  t: (key: string, options?: any) => string
  columnToggleKeys: readonly string[]
  visibleCols: Record<string, boolean>
  onVisibleColsChange: (next: Record<string, boolean>) => void
  visibleColsStorageKey: string
  columnLabelMap: Record<string, string>
  tableLayoutCustomize: boolean
  onTableLayoutCustomizeChange: (value: boolean) => void
  orderedVisibleColumns: string[]
  moveColumnRelative: (key: string, delta: -1 | 1) => void
  onResetColumnLayout: () => void
}

export function CandidatesTableViewRailSection({
  t,
  columnToggleKeys,
  visibleCols,
  onVisibleColsChange,
  visibleColsStorageKey,
  columnLabelMap,
  tableLayoutCustomize,
  onTableLayoutCustomizeChange,
  orderedVisibleColumns,
  moveColumnRelative,
  onResetColumnLayout,
}: CandidatesTableViewRailSectionProps) {
  const orderedKeysForPicker = useMemo(() => {
    const vis = new Set(orderedVisibleColumns)
    const rest = columnToggleKeys.filter((k) => !vis.has(k))
    return [...orderedVisibleColumns, ...rest]
  }, [columnToggleKeys, orderedVisibleColumns])

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white px-2.5 py-2.5 shadow-sm">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {t('app.candidates.rail.table_view_title', { defaultValue: 'Table view' })}
      </p>
      <p className="mb-2 text-[11px] leading-snug text-slate-600">
        {t('app.candidates.rail.table_view_hint', {
          defaultValue:
            'Choose visible columns and order. Turn on edit mode to drag columns in the table or resize widths. Saved list views can include this layout.',
        })}
      </p>

      <div className="mb-2 flex flex-wrap gap-1.5">
        <button
          type="button"
          className={
            tableLayoutCustomize
              ? 'inline-flex items-center gap-1.5 rounded-md border border-brand-500 bg-brand-50 px-2 py-1.5 text-[11px] font-semibold text-brand-900 hover:bg-brand-100'
              : 'inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50'
          }
          onClick={() => onTableLayoutCustomizeChange(!tableLayoutCustomize)}
        >
          {tableLayoutCustomize
            ? t('app.candidates.table.customize_layout_done', { defaultValue: 'Done editing' })
            : t('app.candidates.table.edit_order_width', { defaultValue: 'Edit order & width in table' })}
        </button>
        <button
          type="button"
          className="inline-flex items-center rounded-md border border-slate-200 bg-white px-2 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
          onClick={onResetColumnLayout}
        >
          {t('app.candidates.rail.reset_column_layout', { defaultValue: 'Reset order & widths' })}
        </button>
      </div>

      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
        {t('app.candidates.table.columns.title')}
      </div>
      <ul className="space-y-1 pr-0.5">
        {orderedKeysForPicker.map((key) => {
          const visible = !!visibleCols[key]
          const orderIdx = orderedVisibleColumns.indexOf(key)
          const canMoveUp = visible && orderIdx > 0
          const canMoveDown = visible && orderIdx >= 0 && orderIdx < orderedVisibleColumns.length - 1
          return (
            <li
              key={key}
              className="flex items-center gap-1 rounded-md border border-transparent px-0.5 py-0.5 hover:border-slate-100 hover:bg-slate-50/80"
            >
              <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  className="shrink-0"
                  checked={visible}
                  onChange={(e) => {
                    const next = { ...visibleCols, [key]: e.currentTarget.checked }
                    onVisibleColsChange(next)
                    try {
                      localStorage.setItem(visibleColsStorageKey, JSON.stringify(next))
                    } catch {
                      /* ignore */
                    }
                  }}
                />
                <span className="min-w-0 truncate">{columnLabelMap[key] ?? key}</span>
              </label>
              {visible ? (
                <span className="flex shrink-0 items-center gap-0.5">
                  <button
                    type="button"
                    className="rounded border border-slate-200 px-1 py-0.5 text-[10px] leading-none text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                    disabled={!canMoveUp}
                    title={t('app.candidates.rail.column_up', { defaultValue: 'Move column up' })}
                    onClick={() => moveColumnRelative(key, -1)}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="rounded border border-slate-200 px-1 py-0.5 text-[10px] leading-none text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                    disabled={!canMoveDown}
                    title={t('app.candidates.rail.column_down', { defaultValue: 'Move column down' })}
                    onClick={() => moveColumnRelative(key, 1)}
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
