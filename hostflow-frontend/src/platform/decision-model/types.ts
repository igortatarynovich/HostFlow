import type { DetailRailContactAction } from '../detail-rail/detailRailTypes'

/**
 * Platform Decision Model — one structure for every object in Decision Flow.
 *
 * Modules resolve ObjectDecision from entity/process state.
 * Detail Rail / Context Rail compose UI from this object — never the reverse.
 *
 * Spec: docs/specs/architecture/hostflow-decision-model-v1.md
 */

export type DecisionAction = {
  id: string
  label: string
  onClick?: () => void
  href?: string
  variant?: 'primary' | 'secondary' | 'danger' | 'link'
  disabled?: boolean
}

/** Context blocks shown in scroll zone — set per state, not fixed globally. */
export type DecisionContextBlockId =
  | 'contacts'
  | 'documents'
  | 'history'
  | 'handoff'
  | 'relations'
  | 'summary'
  | 'workflow'
  | 'vacancy'
  | 'assignee'
  | 'outcome'

export type DecisionOutcome = {
  title: string
  body?: string
  why?: string
  variant?: 'default' | 'terminal' | 'success'
}

/**
 * Single decision surface for any platform object.
 *
 * Answers: «Что мне сейчас нужно сделать?» — not a container of unrelated blocks.
 */
export type ObjectDecision = {
  /** Machine-readable state key (e.g. `candidate.awaiting_documents`). */
  stateId: string
  /** Product-language answer — «Связаться с кандидатом», «Передать в HR». */
  currentState: string
  /** Decision rationale — «Первый контакт ещё не выполнен». */
  why?: string
  /** One dominant action — always visible in Fixed Decision Zone. */
  primaryAction: DecisionAction | null
  /** Secondary / dismiss actions — Fixed Decision Zone, never buried in scroll. */
  secondaryActions?: DecisionAction[]
  /** Icon-only comms — part of decision, not Entity duplication. */
  contactActions?: DetailRailContactAction[]
  /** Ordered scroll blocks for this state only. */
  requiredContext: readonly DecisionContextBlockId[]
  /** Process closed — show outcome instead of next step. */
  terminal?: boolean
  outcome?: DecisionOutcome
  /** Optional preview after primary action completes. */
  afterActionHint?: string
  variant?: 'default' | 'blocker' | 'terminal' | 'success'
}
