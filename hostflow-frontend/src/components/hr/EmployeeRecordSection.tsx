import type { ReactNode } from 'react'

/**
 * Section surface aligned with candidate card blocks: white card, clear title rail.
 */
export function EmployeeRecordSection({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/60 md:p-5">
      <header className="mb-4 border-b border-slate-100 pb-3">
        <h2 className="text-sm font-semibold tracking-tight text-slate-900">{title}</h2>
        {description ? <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{description}</p> : null}
      </header>
      <div className="space-y-3">{children}</div>
    </section>
  )
}
