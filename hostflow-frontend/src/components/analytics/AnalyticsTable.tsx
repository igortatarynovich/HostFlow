import type { ReactNode } from 'react'

export type AnalyticsTableColumn<T> = {
  id: string
  header: string
  align?: 'left' | 'right'
  cell: (row: T) => ReactNode
}

export type AnalyticsTableProps<T> = {
  columns: AnalyticsTableColumn<T>[]
  rows: T[]
  rowKey: (row: T) => string
  totals?: ReactNode
  empty?: ReactNode
}

export function AnalyticsTable<T>({ columns, rows, rowKey, totals, empty }: AnalyticsTableProps<T>) {
  if (rows.length === 0) return <>{empty}</>

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-500">
            {columns.map((col) => (
              <th
                key={col.id}
                className={`py-2 font-medium ${col.align === 'right' ? 'text-right' : 'pr-3'}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-b border-slate-50">
              {columns.map((col) => (
                <td
                  key={col.id}
                  className={`py-2 ${col.align === 'right' ? 'text-right tabular-nums' : 'pr-3 text-slate-800'}`}
                >
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {totals ? <div className="mt-2 text-xs text-slate-500">{totals}</div> : null}
    </div>
  )
}
