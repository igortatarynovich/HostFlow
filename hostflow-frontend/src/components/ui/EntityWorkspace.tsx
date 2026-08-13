import clsx from 'clsx'
import type { HTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { StatusBadge, type StatusBadgeSemantic } from './StatusBadge'
import { Tabs, type TabItem } from './Tabs'

export type EntityWorkspaceTab = TabItem

export type EntityWorkspaceSummaryCard = {
  id: string
  label: string
  value: ReactNode
  subValue?: ReactNode
  href?: string
  tone?: 'default' | 'brand' | 'warning' | 'muted' | 'success'
}

const SUMMARY_TONE: Record<NonNullable<EntityWorkspaceSummaryCard['tone']>, string> = {
  default: 'border-slate-200 bg-white',
  brand: 'border-brand-200 bg-brand-50/40',
  warning: 'border-amber-200 bg-amber-50/50',
  muted: 'border-slate-200 bg-slate-50/80',
  success: 'border-emerald-200 bg-emerald-50/50',
}

export type EntityWorkspaceHeaderProps = {
  resourceTypeLabel: string
  title: ReactNode
  status?: { label: string; semantic: StatusBadgeSemantic }
  backHref?: string
  backLabel?: string
  actions?: ReactNode
  meta?: ReactNode
}

/** Minimal entity header for new chrome. Candidate/HR headers stay module-owned. */
export function EntityWorkspaceHeader({
  resourceTypeLabel,
  title,
  status,
  backHref,
  backLabel = 'Back',
  actions,
  meta,
}: EntityWorkspaceHeaderProps) {
  return (
    <header className="shrink-0 border-b border-slate-200 bg-white px-6 py-4" data-entity-workspace-zone="header">
      {backHref ? (
        <Link to={backHref} className="mb-3 inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-brand-700">
          ← {backLabel}
        </Link>
      ) : null}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{resourceTypeLabel}</p>
          <div className="mt-0.5 flex flex-wrap items-center gap-2">
            <h1 className="truncate text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
            {status ? <StatusBadge label={status.label} semantic={status.semantic} size="sm" shape="pill" /> : null}
          </div>
          {meta ? <div className="mt-2 text-sm text-slate-500">{meta}</div> : null}
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </header>
  )
}

export type EntityWorkspaceSummaryProps = {
  cards: EntityWorkspaceSummaryCard[]
}

export function EntityWorkspaceSummary({ cards }: EntityWorkspaceSummaryProps) {
  if (cards.length === 0) return null
  return (
    <section className="shrink-0 border-b border-slate-200 bg-slate-50/70 px-6 py-4" data-entity-workspace-zone="summary">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {cards.map((card) => {
          const tone = card.tone ?? 'default'
          const body = (
            <>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{card.label}</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{card.value}</p>
              {card.subValue ? <p className="mt-0.5 text-xs text-slate-600">{card.subValue}</p> : null}
            </>
          )
          return card.href ? (
            <a key={card.id} href={card.href} className={clsx('rounded-xl border p-3 transition hover:shadow-sm', SUMMARY_TONE[tone])}>
              {body}
            </a>
          ) : (
            <div key={card.id} className={clsx('rounded-xl border p-3', SUMMARY_TONE[tone])}>
              {body}
            </div>
          )
        })}
      </div>
    </section>
  )
}

export type EntityWorkspaceRailProps = {
  children: ReactNode
  widthPx?: number
  className?: string
}

/** Context rail / drawer chrome. Timeline is a content slot, not this rail. */
export function EntityWorkspaceRail({ children, widthPx = 360, className }: EntityWorkspaceRailProps) {
  return (
    <aside
      className={clsx(
        'flex min-h-0 shrink-0 flex-col overflow-y-auto overscroll-contain border-l border-slate-200 bg-white',
        className,
      )}
      style={{ width: widthPx, minWidth: widthPx, maxWidth: widthPx }}
      data-entity-workspace-zone="context-rail"
    >
      {children}
    </aside>
  )
}

export type EntityWorkspaceProps = {
  header?: ReactNode
  summary?: ReactNode
  /** Section tabs. Timeline / documents / overview are content slots behind this nav. */
  navigation?: ReactNode
  tabs?: {
    items: EntityWorkspaceTab[]
    value: string
    onChange: (id: string) => void
    ariaLabel?: string
  }
  actionBar?: ReactNode
  rail?: ReactNode
  children: ReactNode
  ariaLabel?: string
  className?: string
} & Omit<HTMLAttributes<HTMLDivElement>, 'children'>

/**
 * Public entity chrome (Platform Extraction K3).
 * Not Candidate/HR Workspace and not ADR-045 page templates.
 */
export function EntityWorkspace({
  header,
  summary,
  navigation,
  tabs,
  actionBar,
  rail,
  children,
  ariaLabel,
  className,
  ...rest
}: EntityWorkspaceProps) {
  const nav =
    navigation ??
    (tabs ? (
      <nav
        className="shrink-0 border-b border-slate-200 bg-white px-4"
        data-entity-workspace-zone="navigation"
        aria-label={tabs.ariaLabel ?? 'Sections'}
      >
        <Tabs
          items={tabs.items}
          value={tabs.value}
          onChange={tabs.onChange}
          aria-label={tabs.ariaLabel ?? 'Sections'}
          className="py-1"
        />
      </nav>
    ) : null)

  return (
    <div
      {...rest}
      className={clsx('flex h-full min-h-0 flex-col overflow-hidden bg-slate-100', className)}
      data-entity-workspace="v1"
      aria-label={ariaLabel}
    >
      {header}
      {actionBar ? (
        <div className="shrink-0 border-b border-slate-200 bg-white px-6 py-2" data-entity-workspace-zone="action-bar">
          {actionBar}
        </div>
      ) : null}
      {summary}
      <div className="flex min-h-0 flex-1">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          {nav}
          <main
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-slate-100 p-4"
            data-entity-workspace-zone="content"
          >
            <div className="mx-auto max-w-5xl">{children}</div>
          </main>
        </div>
        {rail}
      </div>
    </div>
  )
}
