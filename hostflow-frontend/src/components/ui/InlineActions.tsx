import type { ReactNode } from 'react'

/** Quiet action row: primary, secondary and destructive items separated by a middot. */
export function InlineActions({ items }: { items: Array<{ key: string; node: ReactNode }> }) {
  const visible = items.filter((item) => item.node)
  if (!visible.length) return null
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
      {visible.map((item, index) => (
        <span key={item.key} className="inline-flex items-center gap-2">
          {index > 0 ? <span className="text-slate-300" aria-hidden>·</span> : null}
          {item.node}
        </span>
      ))}
    </div>
  )
}
