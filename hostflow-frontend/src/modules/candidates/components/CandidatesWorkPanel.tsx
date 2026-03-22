import clsx from 'clsx'
import type { ReactNode } from 'react'

type CandidatesWorkPanelProps = {
  open: boolean
  summaryHero: ReactNode
  children: ReactNode
}

export function CandidatesWorkPanel({ open, summaryHero, children }: CandidatesWorkPanelProps) {
  return (
    <div className="pointer-events-none absolute inset-y-0 right-0 z-20 p-0">
      <aside
        className={clsx(
          'pointer-events-auto relative h-full w-[352px] min-h-0 flex flex-col overflow-y-auto rounded-l-lg border border-slate-200/90 bg-white/95 backdrop-blur-[1px] shadow-[0_8px_24px_rgba(15,23,42,0.08)] transition-all duration-300 ease-out',
          open ? 'translate-x-0 opacity-100' : 'translate-x-6 opacity-0 pointer-events-none',
        )}
      >
        <div className="pointer-events-none absolute -left-8 inset-y-0 w-8 bg-gradient-to-l from-slate-900/10 via-slate-900/4 to-transparent" />
        <div className="p-3.5 space-y-3.5 pt-4">
          <div className="mb-1">{summaryHero}</div>
          {children}
        </div>
      </aside>
    </div>
  )
}
