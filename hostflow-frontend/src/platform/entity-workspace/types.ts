import type { ReactNode } from 'react'
import type { SemanticRole } from '../data-table/types'
import type { DetailRailAction, DetailRailActionsTier } from '../detail-rail/detailRailTypes'
import type { EntityModel, EntityPassport } from '../entity-model'

/**
 * Universal Entity Workspace — Phase 2.2 platform primitive.
 * Shell owns geometry only; modules supply passport + renderers.
 */

/** Fixed navigation section order — modules enable subset, never reorder. */
export type EntityWorkspaceSectionId =
  | 'overview'
  | 'contacts'
  | 'documents'
  | 'timeline'
  | 'relations'
  | 'tasks'
  | 'outcome'
  | 'finance'
  | 'comments'
  | 'activity'

export const ENTITY_WORKSPACE_SECTION_ORDER: EntityWorkspaceSectionId[] = [
  'overview',
  'contacts',
  'documents',
  'timeline',
  'relations',
  'tasks',
  'outcome',
  'finance',
  'comments',
  'activity',
]

export type EntityWorkspaceBreadcrumb = {
  label: string
  href?: string
}

export type EntityWorkspaceHeaderChip = {
  id: string
  label: ReactNode
}

export type EntityWorkspaceHeaderMetaItem = {
  label: string
  value: ReactNode
}

/** Optional header enrichment — modules supply; Shell never branches on resource type. */
export type EntityWorkspaceHeaderExtension = {
  backHref?: string
  backLabel?: string
  avatarUrl?: string | null
  avatarFallback?: string
  entityRefLabel?: string
  sourceLabel?: string
  chips?: EntityWorkspaceHeaderChip[]
  footerMeta?: EntityWorkspaceHeaderMetaItem[]
  actionsSlot?: ReactNode
}

export type EntityWorkspaceHeaderModel = {
  title: string
  subtitle?: string
  resourceTypeLabel?: string
  statusLabel?: string
  statusSemantic?: SemanticRole
  stageLabel?: string
  stageSemantic?: SemanticRole
  outcomeLabel?: string
  outcomeSemantic?: SemanticRole
  breadcrumbs?: EntityWorkspaceBreadcrumb[]
  quickActions?: DetailRailAction[]
}

export type EntityWorkspaceSummaryCardTone = 'default' | 'brand' | 'warning' | 'muted' | 'success'

export type EntityWorkspaceSummaryCard = {
  id: string
  label: string
  value: ReactNode
  subValue?: ReactNode
  href?: string
  tone?: EntityWorkspaceSummaryCardTone
  progressPercent?: number
}

export type EntityWorkspaceSummaryField = {
  id: string
  label: string
  value: ReactNode
}

export type EntityWorkspaceSummaryModel = {
  cards: EntityWorkspaceSummaryCard[]
  /** @deprecated use cards */
  fields?: EntityWorkspaceSummaryField[]
  blockerHint?: string | null
}

export type EntityWorkspaceSectionDescriptor = {
  id: EntityWorkspaceSectionId
  label: string
  enabled?: boolean
}

export type EntityWorkspaceSectionRenderer = () => ReactNode

/** Context Rail — entity deep-work companion (Zone 5). Not Collection Detail Rail. */
export type EntityContextRailBlockId =
  | 'next_actions'
  | 'tasks'
  | 'reminders'
  | 'processes'
  | 'recent_events'

export const ENTITY_CONTEXT_RAIL_BLOCK_ORDER: EntityContextRailBlockId[] = [
  'next_actions',
  'tasks',
  'reminders',
  'processes',
  'recent_events',
]

export type EntityContextRailTaskItem = {
  id: string
  title: string
  dueAt?: string
  done?: boolean
  overdue?: boolean
}

export type EntityContextRailEventItem = {
  id: string
  at: string
  title: string
  description?: string
}

export type EntityContextRailContactAction = {
  id: string
  label: string
  href?: string
  onClick?: () => void
  icon: 'phone' | 'whatsapp' | 'email'
}

export type EntityContextRailModel = {
  decisionTitle?: string
  decisionWhy?: string
  afterActionHint?: string
  actions?: DetailRailActionsTier
  tasks?: EntityContextRailTaskItem[]
  reminders?: EntityContextRailTaskItem[]
  processes?: { id: string; label: string; statusLabel?: string }[]
  recentEvents?: EntityContextRailEventItem[]
  quickContacts?: EntityContextRailContactAction[]
  /** When set, shows «Показать всю историю» under recent events. */
  onShowAllEvents?: () => void
  createTaskLabel?: string
  onCreateTask?: () => void
}

export type EntityWorkspaceActionConfig = {
  headerActions?: DetailRailAction[]
  contextActions?: DetailRailActionsTier
}

export type EntityWorkspaceShellLabels = {
  sections: Partial<Record<EntityWorkspaceSectionId, string>>
  contextRail: Partial<Record<EntityContextRailBlockId, string>>
  summaryHeading?: string
  navigationHeading?: string
}

export type EntityWorkspaceShellProps = {
  model: EntityModel
  passport: EntityPassport
  /** Human-readable resource type — «Кандидат», «Клиент», «Заказ». */
  resourceTypeLabel: string
  sectionRenderers?: Partial<Record<EntityWorkspaceSectionId, EntityWorkspaceSectionRenderer>>
  actionConfig?: EntityWorkspaceActionConfig
  /** Override projected context rail (optional). */
  contextRail?: EntityContextRailModel
  breadcrumbs?: EntityWorkspaceBreadcrumb[]
  headerExtension?: EntityWorkspaceHeaderExtension
  summaryOverride?: EntityWorkspaceSummaryModel
  labels?: EntityWorkspaceShellLabels
  activeSectionId?: EntityWorkspaceSectionId
  defaultSectionId?: EntityWorkspaceSectionId
  onSectionChange?: (id: EntityWorkspaceSectionId) => void
  navigationPeers?: {
    hasPrevious: boolean
    hasNext: boolean
    onPrevious?: () => void
    onNext?: () => void
  }
}

/** @deprecated Phase 2.2 — use EntityWorkspaceShellProps */
export type EntityWorkspaceConfig = {
  resourceId: string
  entityId: string
  header: EntityWorkspaceHeaderModel
  summary: EntityWorkspaceSummaryModel
  navigation: EntityWorkspaceNavigationConfig
  contextRail: ContextRailConfig
  sections: Partial<Record<EntityWorkspaceSectionId, EntityWorkspaceSectionSlot>>
  navigationPeers?: EntityWorkspaceShellProps['navigationPeers']
}

/** @deprecated */
export type EntityWorkspaceNavigationConfig = {
  sections: EntityWorkspaceSectionDescriptor[]
  activeSectionId: EntityWorkspaceSectionId
  onSectionChange: (id: EntityWorkspaceSectionId) => void
}

/** @deprecated */
export type EntityWorkspaceSectionSlot = {
  sectionId: EntityWorkspaceSectionId
  render: EntityWorkspaceSectionRenderer
}

/** @deprecated use EntityContextRailModel */
export type ContextRailModel = EntityContextRailModel

/** @deprecated */
export type ContextRailBlockId = EntityContextRailBlockId

/** @deprecated */
export type ContextRailConfig = {
  model: EntityContextRailModel
  widthPx?: number
}

/** @deprecated */
export type ContextRailTaskItem = EntityContextRailTaskItem

/** @deprecated */
export type ContextRailEventItem = EntityContextRailEventItem

export const DEFAULT_ENTITY_CONTEXT_RAIL_WIDTH_PX = 360

/** @deprecated */
export const DEFAULT_CONTEXT_RAIL_WIDTH_PX = DEFAULT_ENTITY_CONTEXT_RAIL_WIDTH_PX

/** @deprecated */
export const CONTEXT_RAIL_BLOCK_ORDER = ENTITY_CONTEXT_RAIL_BLOCK_ORDER

export const DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS: EntityWorkspaceShellLabels = {
  summaryHeading: 'Summary',
  navigationHeading: 'Sections',
  sections: {
    overview: 'Overview',
    contacts: 'Contacts',
    documents: 'Documents',
    timeline: 'Timeline',
    relations: 'Relations',
    tasks: 'Tasks',
    outcome: 'Outcome',
    finance: 'Finance',
    comments: 'Comments',
    activity: 'Activity',
  },
  contextRail: {
    next_actions: 'Next action',
    tasks: 'Tasks',
    reminders: 'Reminders',
    processes: 'Processes',
    recent_events: 'Recent events',
  },
}
