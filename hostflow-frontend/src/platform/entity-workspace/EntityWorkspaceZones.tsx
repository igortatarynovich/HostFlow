import clsx from 'clsx'
import { Link } from 'react-router-dom'
import { IconArrowLeft, IconChevronLeft, IconChevronRight } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { SemanticBadge } from '../data-table/SemanticBadge'
import type {
  EntityWorkspaceHeaderExtension,
  EntityWorkspaceHeaderModel,
  EntityWorkspaceSectionId,
  EntityWorkspaceShellLabels,
  EntityWorkspaceSummaryCard,
  EntityWorkspaceSummaryModel,
} from './types'

type EntityWorkspaceHeaderZoneProps = {
  header: EntityWorkspaceHeaderModel
  resourceTypeLabel: string
  extension?: EntityWorkspaceHeaderExtension
  navigationPeers?: {
    hasPrevious: boolean
    hasNext: boolean
    onPrevious?: () => void
    onNext?: () => void
  }
}

export function EntityWorkspaceHeaderZone({
  header,
  resourceTypeLabel,
  extension,
  navigationPeers,
}: EntityWorkspaceHeaderZoneProps) {
  const { t } = useI18n()
  const initials =
    extension?.avatarFallback ??
    header.title
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase()

  return (
    <header className="shrink-0 border-b border-slate-200 bg-white px-6 py-4" data-entity-workspace-zone="header">
      {extension?.backHref ? (
        <Link
          to={extension.backHref}
          className="mb-3 inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-brand-700"
        >
          <IconArrowLeft size={16} />
          {extension.backLabel ?? t('common.actions.back', { defaultValue: 'Back' })}
        </Link>
      ) : null}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-1 items-start gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-brand-100 to-brand-200 text-lg font-bold text-brand-800 ring-1 ring-brand-200">
            {extension?.avatarUrl ? (
              <img src={extension.avatarUrl} alt="" className="h-full w-full object-cover" />
            ) : (
              initials || '•'
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{resourceTypeLabel}</p>
            <div className="mt-0.5 flex flex-wrap items-center gap-2">
              <h1 className="truncate text-2xl font-bold tracking-tight text-slate-900">{header.title}</h1>
              {header.outcomeLabel ? (
                <SemanticBadge label={header.outcomeLabel} semanticRole={header.outcomeSemantic ?? 'status'} size="sm" shape="pill" />
              ) : header.statusLabel ? (
                <SemanticBadge label={header.statusLabel} semanticRole={header.statusSemantic ?? 'process_stage'} size="sm" shape="pill" />
              ) : null}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
              {extension?.entityRefLabel ? <span>{extension.entityRefLabel}</span> : null}
              {header.stageLabel && header.stageLabel !== header.statusLabel ? (
                <SemanticBadge label={header.stageLabel} semanticRole={header.stageSemantic ?? 'process_stage'} size="sm" shape="pill" />
              ) : null}
              {extension?.sourceLabel ? (
                <span>
                  {t('app.entity_workspace.source_prefix', {
                    defaultValue: 'Source: {value}',
                    values: { value: extension.sourceLabel },
                  })}
                </span>
              ) : null}
            </div>
            {extension?.chips?.length ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {extension.chips.map((chip) => (
                  <span
                    key={chip.id}
                    className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700"
                  >
                    {chip.label}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {navigationPeers ? (
            <div className="flex items-center gap-0.5 rounded-lg border border-slate-200 bg-white p-0.5">
              <button
                type="button"
                disabled={!navigationPeers.hasPrevious}
                onClick={navigationPeers.onPrevious}
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-50 disabled:opacity-30"
                aria-label="Previous"
              >
                <IconChevronLeft size={18} />
              </button>
              <button
                type="button"
                disabled={!navigationPeers.hasNext}
                onClick={navigationPeers.onNext}
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-50 disabled:opacity-30"
                aria-label="Next"
              >
                <IconChevronRight size={18} />
              </button>
            </div>
          ) : null}
          {extension?.actionsSlot}
          {header.quickActions?.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={action.onClick}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {extension?.footerMeta?.length ? (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-100 pt-3 text-xs text-slate-500">
          {extension.footerMeta.map((item) => (
            <span key={item.label}>
              {item.label}: <span className="font-medium text-slate-700">{item.value}</span>
            </span>
          ))}
        </div>
      ) : null}
    </header>
  )
}

const SUMMARY_TONE: Record<NonNullable<EntityWorkspaceSummaryCard['tone']>, string> = {
  default: 'border-slate-200 bg-white',
  brand: 'border-brand-200 bg-brand-50/40',
  warning: 'border-amber-200 bg-amber-50/50',
  muted: 'border-slate-200 bg-slate-50/80',
  success: 'border-emerald-200 bg-emerald-50/50',
}

export function EntityWorkspaceSummaryStrip({ summary }: { summary: EntityWorkspaceSummaryModel }) {
  const cards = summary.cards.length
    ? summary.cards
    : (summary.fields ?? []).map((field) => ({
        id: field.id,
        label: field.label,
        value: field.value,
        tone: 'default' as const,
      }))

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
              {typeof card.progressPercent === 'number' ? (
                <div className="mt-2">
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-brand-600"
                      style={{ width: `${Math.max(0, Math.min(100, card.progressPercent))}%` }}
                    />
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">{card.progressPercent}%</p>
                </div>
              ) : null}
            </>
          )
          return card.href ? (
            <a
              key={card.id}
              href={card.href}
              className={clsx('rounded-xl border p-3 transition hover:shadow-sm', SUMMARY_TONE[tone])}
            >
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

type EntityWorkspaceNavTabsProps = {
  sections: EntityWorkspaceSectionId[]
  activeSectionId: EntityWorkspaceSectionId
  onSectionChange: (id: EntityWorkspaceSectionId) => void
  sectionLabel: (id: EntityWorkspaceSectionId) => string
  ariaLabel: string
}

export function EntityWorkspaceNavTabs({
  sections,
  activeSectionId,
  onSectionChange,
  sectionLabel,
  ariaLabel,
}: EntityWorkspaceNavTabsProps) {
  return (
    <nav
      className="shrink-0 border-b border-slate-200 bg-white px-4"
      data-entity-workspace-zone="navigation"
      aria-label={ariaLabel}
    >
      <div className="flex gap-1 overflow-x-auto py-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {sections.map((sectionId) => (
          <button
            key={sectionId}
            type="button"
            onClick={() => onSectionChange(sectionId)}
            className={clsx(
              'shrink-0 rounded-lg px-3 py-2 text-sm font-medium transition',
              activeSectionId === sectionId
                ? 'bg-brand-700 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
            )}
          >
            {sectionLabel(sectionId)}
          </button>
        ))}
      </div>
    </nav>
  )
}
