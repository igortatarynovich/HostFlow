import type { DetailRailBlockId, DetailRailModel } from '../detail-rail/detailRailTypes'
import type { ObjectDecision } from './types'

const CONTEXT_TO_RAIL_BLOCK: Partial<Record<string, DetailRailBlockId>> = {
  contacts: 'contacts',
  documents: 'documents',
  history: 'history',
  handoff: 'summary',
  relations: 'relations',
  summary: 'summary',
  workflow: 'summary',
  vacancy: 'summary',
  assignee: 'summary',
  outcome: 'outcome',
}

/**
 * Derives Detail Rail projection from ObjectDecision.
 * Fixed zone: header + unified decision (via `model.decision`).
 * Scroll zone: only blocks listed in `requiredContext` that have content.
 */
export function composeDetailRailModelFromDecision(args: {
  resourceId: string
  decision: ObjectDecision
  header?: DetailRailModel['header']
  /** Populated context payloads keyed by DecisionContextBlockId. */
  contextAvailable?: Partial<Record<string, boolean>>
  /** Legacy block payloads — mapped when context slot is active. */
  legacy?: Pick<
    DetailRailModel,
    'contacts' | 'summaryFields' | 'timeline' | 'documents' | 'relations' | 'footerActions'
  >
}): DetailRailModel {
  const { resourceId, decision, header, contextAvailable, legacy } = args

  const scrollBlockIds: DetailRailBlockId[] = []
  for (const ctxId of decision.requiredContext) {
    const railId = CONTEXT_TO_RAIL_BLOCK[ctxId]
    if (!railId || scrollBlockIds.includes(railId)) continue
    if (contextAvailable && contextAvailable[ctxId] === false) continue
    scrollBlockIds.push(railId)
  }

  if (legacy?.footerActions?.length && !scrollBlockIds.includes('footer_actions')) {
    scrollBlockIds.push('footer_actions')
  }

  const blockOrder: DetailRailBlockId[] = ['header', ...scrollBlockIds]

  const model: DetailRailModel = {
    resourceId,
    header,
    decision,
    blockOrder,
    ...legacy,
  }

  if (decision.terminal && decision.outcome && !scrollBlockIds.includes('outcome')) {
    model.processOutcome = {
      title: decision.outcome.title,
      body: decision.outcome.body,
      whyLabel: decision.outcome.why,
      variant: decision.outcome.variant,
    }
  }

  return model
}
