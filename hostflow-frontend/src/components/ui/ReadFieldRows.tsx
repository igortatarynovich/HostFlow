/** Read-only label/value rows for entity workspace sections. */
export function ReadFieldRows({ rows }: { rows: Array<{ label: string; value: string }> }) {
  return (
    <dl>
      {rows.map((row) => (
        <div key={row.label} className="flex items-baseline justify-between gap-6 py-1">
          <dt className="text-sm text-slate-500">{row.label}</dt>
          <dd className="text-right text-sm font-medium text-slate-900">{row.value}</dd>
        </div>
      ))}
    </dl>
  )
}
