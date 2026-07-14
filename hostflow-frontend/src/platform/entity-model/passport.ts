/**
 * Runtime passport slices — populated from API + process semantics.
 * UI surfaces project from these slices; they do not define layout.
 *
 * Spec: docs/specs/architecture/hostflow-entity-model-v1.md
 */

import type { EntitySectionId } from './types'

export type EntityProcessPhase = 'active' | 'terminal'

export type EntityIdentitySlice = {
  title: string
  subtitle?: string
  shortId?: string
  masked?: boolean
}

export type EntityStateSlice = {
  /** Stable key, e.g. `candidate.contact`, `candidate.rejected`. */
  phaseId: string
  processPhase: EntityProcessPhase
  /** Product-language headline for current process position. */
  processLabel: string
  stageCode?: string
  stageLabel?: string
  rowStatusCode?: string
  rowStatusLabel?: string
  pipelineStepIndex?: number
  pipelineStepLabels?: readonly string[]
  /** Why the object is in this state (decision context). */
  why?: string
  /** Recruiter role may still perform work actions. */
  recruiterWorkActive: boolean
}

export type EntityOutcomeSlice = {
  title: string
  body?: string
  why?: string
  ownerLabel?: string
  whenLabel?: string
  variant: 'terminal' | 'success' | 'default'
}

export type EntityOwnershipSlice = {
  managerId?: string
  managerLabel?: string
}

export type EntityContactChannelKind = 'phone' | 'email' | 'whatsapp' | 'other'

export type EntityContactChannel = {
  kind: EntityContactChannelKind
  value: string
  display?: string
  href?: string
  primary?: boolean
}

export type EntityContactsSlice = {
  displayName?: string
  channels: EntityContactChannel[]
  preferredChannel?: string
  citizenship?: string
}

export type EntityTaskItem = {
  id: string
  title: string
  dueAt?: string
  status?: string
  overdue?: boolean
}

export type EntityTasksSlice = {
  items: EntityTaskItem[]
  nextTaskId?: string
}

export type EntityDocumentItemStatus = 'missing' | 'problematic' | 'in_progress' | 'ready' | 'unknown'

export type EntityDocumentsSlice = {
  readinessState?: string
  readinessLabel?: string
  blockersSummary?: string | null
  missing: string[]
  problematic: string[]
  inProgress: string[]
  orderedAt?: string | null
  validFrom?: string | null
  hasFiles?: boolean
}

export type EntityTimelineEvent = {
  id: string
  at: string
  title: string
  description?: string
  kind?: string
}

export type EntityTimelineSlice = {
  items: EntityTimelineEvent[]
}

export type EntityRelationKind =
  | 'vacancy'
  | 'recruitment_search'
  | 'client'
  | 'company'
  | 'hr'
  | 'manager'
  | 'other'

export type EntityRelationItem = {
  id: string
  kind: EntityRelationKind
  label: string
  entityId?: string
  href?: string
}

export type EntityRelationsSlice = {
  items: EntityRelationItem[]
}

export type EntityActionCapabilityId =
  | 'call'
  | 'message_whatsapp'
  | 'message_email'
  | 'request_documents'
  | 'verify_documents'
  | 'assign_vacancy'
  | 'handoff'
  | 'complete_task'
  | 'create_task'
  | 'open_documents'

export type EntityActionCapability = {
  id: EntityActionCapabilityId
  allowed: boolean
  primary?: boolean
  reasonIfBlocked?: string
}

export type EntityActionsSlice = {
  workAllowed: boolean
  capabilities: EntityActionCapability[]
  primaryCapabilityId?: EntityActionCapabilityId | null
  /** Product-language next decision (not a UI block title). */
  decisionTitle?: string
  decisionWhy?: string
  afterActionHint?: string
}

/** Runtime passport — one resolved instance of an entity. */
export type EntityPassportSections = {
  identity: EntityIdentitySlice
  state: EntityStateSlice
  outcome: EntityOutcomeSlice | null
  ownership: EntityOwnershipSlice
  contacts: EntityContactsSlice
  tasks: EntityTasksSlice
  documents: EntityDocumentsSlice
  timeline: EntityTimelineSlice
  relations: EntityRelationsSlice
  actions: EntityActionsSlice
}

export type EntityPassport = {
  resourceId: string
  entityId: string
  sections: EntityPassportSections
}

export const ENTITY_PASSPORT_SECTION_IDS: readonly EntitySectionId[] = [
  'identity',
  'state',
  'ownership',
  'contacts',
  'actions',
  'documents',
  'timeline',
  'relations',
  'tasks',
  'outcome',
] as const

export function entityPassportHasTerminalOutcome(passport: EntityPassport): boolean {
  return passport.sections.state.processPhase === 'terminal' || passport.sections.outcome != null
}

export function entityPassportAllowsAction(
  passport: EntityPassport,
  capabilityId: EntityActionCapabilityId,
): boolean {
  if (!passport.sections.actions.workAllowed) return false
  const cap = passport.sections.actions.capabilities.find((c) => c.id === capabilityId)
  return Boolean(cap?.allowed)
}
