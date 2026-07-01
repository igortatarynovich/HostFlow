import clsx from 'clsx'
import type { ReactNode } from 'react'

type InsightCard = {
  key: string
  label: string
  value: string | number
  hint: string
}

type CandidatesSummaryHeroProps = {
  title: string
  subtitle: string
  expandLabel: string
  collapseLabel: string
  expanded: boolean
  cards: InsightCard[]
  onToggleExpanded: () => void
  onCardClick: (key: string) => void
  /** e.g. Activities button opening a modal */
  headerActions?: ReactNode
}

export function CandidatesSummaryHero({
  title,
  subtitle,
  expandLabel,
  collapseLabel,
  expanded,
  cards,
  onToggleExpanded,
  onCardClick,
  headerActions,
}: CandidatesSummaryHeroProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-bold text-slate-900">{title}</h2>
          <div className="flex shrink-0 items-center gap-1.5">
            {headerActions}
            <button
              type="button"
              className="text-[10px] text-slate-500 underline hover:text-slate-800"
              onClick={onToggleExpanded}
            >
              {expanded ? collapseLabel : expandLabel}
            </button>
          </div>
        </div>
        <p className="text-[10px] text-slate-500 leading-tight">{subtitle}</p>
      </div>
      <div
        className={clsx(
          'mt-2 grid gap-1.5 transition-all duration-200',
          expanded ? 'grid-cols-2' : 'grid-cols-2',
        )}
      >
        {cards.map((card) => (
          <button
            key={card.key}
            type="button"
            onClick={() => onCardClick(card.key)}
            className={clsx(
              'rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-left transition hover:border-brand-300 hover:bg-brand-50/40',
              !expanded && 'py-1.5',
            )}
          >
            <div className="text-[9px] uppercase tracking-wide text-slate-500 leading-tight">{card.label}</div>
            <div className="text-lg font-semibold leading-tight text-slate-900">{card.value}</div>
            {expanded && <div className="text-[9px] text-slate-500 leading-tight mt-0.5">{card.hint}</div>}
          </button>
        ))}
      </div>
    </section>
  )
}
