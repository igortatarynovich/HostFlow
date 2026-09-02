import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconX } from '@tabler/icons-react'
import type { ObjectDecision, DecisionContextBlockId } from '../decision-model/types'
import { ContextRailDecisionZone } from './ContextRailDecisionZone'

export type ContextRailHeader = {
  title: string
  titleHref?: string
  subtitle?: string
  meta?: string
  statusLabel?: string
  statusClassName?: string
  entityWorkspaceHref?: string
  entityWorkspaceLabel?: string
}

export type ContextRailProps = {
  header: ContextRailHeader
  decision: ObjectDecision
  onClose: () => void
  closeLabel?: string
  /** Module supplies only blocks referenced in `decision.requiredContext`. */
  contextSlots?: Partial<Record<DecisionContextBlockId, ReactNode>>
  contextTitles?: Partial<Record<DecisionContextBlockId, string>>
  /** Optional data attribute for analytics / tests */
  railKind?: string
}

const DEFAULT_CONTEXT_TITLES: Partial<Record<DecisionContextBlockId, string>> = {
  contacts: 'Контакт',
  documents: 'Документы',
  history: 'История',
  handoff: 'Handoff',
  relations: 'Связи',
  summary: 'Контекст',
  workflow: 'Этапы',
  vacancy: 'Подбор',
  assignee: 'Ответственный',
  outcome: 'Результат',
}

/**
 * Universal Context Rail shell — one scroll for the whole rail.
 * Header and decision scroll with context so short viewports can reach the bottom.
 * Parent must be height-bounded and overflow-hidden; this node owns the scrollbar.
 * Do not add overscroll-contain: Chromium latches wheel events after a fling.
 */
export function ContextRail({
  header,
  decision,
  onClose,
  closeLabel = 'Закрыть',
  contextSlots = {},
  contextTitles = {},
  railKind,
}: ContextRailProps) {
  const titles = { ...DEFAULT_CONTEXT_TITLES, ...contextTitles }

  return (
    <div
      className="flex h-full min-h-0 flex-col overflow-y-auto bg-white"
      data-context-rail={railKind ?? 'v1'}
      data-decision-state={decision.stateId}
    >
      <header className="border-b border-slate-100 px-3 py-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            {header.titleHref ? (
              <Link
                to={header.titleHref}
                className="text-sm font-semibold text-brand-700 hover:text-brand-800 hover:underline"
                data-entity-link="primary"
              >
                {header.title}
              </Link>
            ) : (
              <h2 className="text-sm font-semibold text-slate-900">{header.title}</h2>
            )}
            {header.subtitle ? <p className="mt-0.5 truncate text-xs text-slate-500">{header.subtitle}</p> : null}
            {header.meta ? <p className="mt-0.5 truncate text-[11px] text-slate-400">{header.meta}</p> : null}
            {header.entityWorkspaceHref ? (
              <Link
                to={header.entityWorkspaceHref}
                className="mt-1 inline-flex text-xs font-medium text-brand-700 hover:underline"
                data-entity-link="primary"
              >
                {header.entityWorkspaceLabel ?? 'Открыть полную карточку'}
              </Link>
            ) : null}
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              aria-label={closeLabel}
            >
              <IconX size={16} stroke={2} />
            </button>
            {header.statusLabel ? (
              <span className={header.statusClassName ?? 'rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600'}>
                {header.statusLabel}
              </span>
            ) : null}
          </div>
        </div>
      </header>

      <section className="border-b border-slate-100 px-3 py-2" data-context-rail-zone="decision">
        <ContextRailDecisionZone decision={decision} />
      </section>

      {decision.requiredContext.length > 0 ? (
        <div data-context-rail-zone="scroll">
          {decision.requiredContext.map((blockId) => {
            const slot = contextSlots[blockId]
            if (!slot) return null
            const title = titles[blockId]
            return (
              <section key={blockId} className="border-b border-slate-100 px-3 py-2 last:border-b-0">
                {title ? (
                  <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{title}</p>
                ) : null}
                {slot}
              </section>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}

export { ContextRailDecisionZone } from './ContextRailDecisionZone'
