import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconX } from '@tabler/icons-react'
import { useI18n, type TranslateFn } from '../../i18n'
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

function defaultContextTitles(t: TranslateFn): Partial<Record<DecisionContextBlockId, string>> {
  return {
    contacts: t('app.context_rail.blocks.contacts', { defaultValue: 'Contact' }),
    documents: t('app.context_rail.blocks.documents', { defaultValue: 'Documents' }),
    history: t('app.context_rail.blocks.history', { defaultValue: 'History' }),
    handoff: 'Handoff',
    relations: t('app.context_rail.blocks.relations', { defaultValue: 'Relations' }),
    summary: t('app.context_rail.blocks.summary', { defaultValue: 'Context' }),
    workflow: t('app.context_rail.blocks.workflow', { defaultValue: 'Stages' }),
    vacancy: t('app.context_rail.blocks.vacancy', { defaultValue: 'Vacancy' }),
    assignee: t('app.context_rail.blocks.assignee', { defaultValue: 'Assignee' }),
    outcome: t('app.context_rail.blocks.outcome', { defaultValue: 'Result' }),
  }
}

/**
 * Universal Context Rail shell — Fixed Header → Fixed Decision (state) → Scroll Context (adaptive).
 */
export function ContextRail({
  header,
  decision,
  onClose,
  closeLabel,
  contextSlots = {},
  contextTitles = {},
  railKind,
}: ContextRailProps) {
  const { t } = useI18n()
  const resolvedCloseLabel = closeLabel ?? t('app.context_rail.close', { defaultValue: 'Close' })
  const titles = { ...defaultContextTitles(t), ...contextTitles }

  return (
    <div
      className="flex h-full min-h-0 flex-col overflow-hidden bg-white"
      data-context-rail={railKind ?? 'v1'}
      data-decision-state={decision.stateId}
    >
      <header className="shrink-0 border-b border-slate-100 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            {header.titleHref ? (
              <Link
                to={header.titleHref}
                className="text-xl font-bold text-brand-700 hover:text-brand-800 hover:underline"
                data-entity-link="primary"
              >
                {header.title}
              </Link>
            ) : (
              <h2 className="text-xl font-bold text-slate-900">{header.title}</h2>
            )}
            {header.subtitle ? <p className="mt-0.5 text-sm text-slate-500">{header.subtitle}</p> : null}
            {header.meta ? <p className="mt-1 text-xs text-slate-400">{header.meta}</p> : null}
            {header.entityWorkspaceHref ? (
              <Link
                to={header.entityWorkspaceHref}
                className="mt-2 inline-flex text-sm font-medium text-brand-700 hover:underline"
                data-entity-link="primary"
              >
                {header.entityWorkspaceLabel ??
                  t('app.context_rail.open_full_card', { defaultValue: 'Open full card' })}
              </Link>
            ) : null}
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              aria-label={resolvedCloseLabel}
            >
              <IconX size={18} stroke={2} />
            </button>
            {header.statusLabel ? (
              <span className={header.statusClassName ?? 'rounded-full bg-slate-100 px-3 py-0.5 text-xs font-semibold text-slate-600'}>
                {header.statusLabel}
              </span>
            ) : null}
          </div>
        </div>
      </header>

      <section className="shrink-0 border-b border-slate-100 p-4" data-context-rail-zone="decision">
        <ContextRailDecisionZone decision={decision} />
      </section>

      {decision.requiredContext.length > 0 ? (
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain" data-context-rail-zone="scroll">
          {decision.requiredContext.map((blockId) => {
            const slot = contextSlots[blockId]
            if (!slot) return null
            const title = titles[blockId]
            return (
              <section key={blockId} className="border-b border-slate-100 p-4 last:border-b-0">
                {title ? (
                  <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
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
