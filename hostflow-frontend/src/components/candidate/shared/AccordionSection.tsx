import { useEffect, useState } from 'react'
import clsx from 'clsx'

export default function AccordionSection({
  title,
  subtitle,
  defaultOpen = false,
  children,
}: {
  title: string
  subtitle?: string | null
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  // If defaultOpen changes between renders, keep it stable (no surprise auto-open).
  useEffect(() => {
    // noop
  }, [])

  return (
    <section className="rounded-2xl border border-slate-200 bg-white">
      <button
        type="button"
        className="w-full px-3 py-2.5 flex items-start justify-between gap-3 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-800">{title}</div>
          {subtitle ? <div className="mt-0.5 text-[11px] text-slate-500">{subtitle}</div> : null}
        </div>
        <div className={clsx('shrink-0 text-[11px] text-slate-500 pt-0.5', open && 'text-slate-700')}>
          {open ? '−' : '+'}
        </div>
      </button>
      {open ? <div className="px-3 pb-3">{children}</div> : null}
    </section>
  )
}

