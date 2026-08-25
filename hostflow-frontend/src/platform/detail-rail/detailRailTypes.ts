import type { ReactNode } from 'react'
import type { SemanticRole } from '../data-table/types'
import type { ObjectDecision } from '../decision-model/types'

/** Fixed block order — modules supply content per block, never reorder. */
export type DetailRailBlockId =
  | 'header'
  | 'contacts'
  | 'next_action'
  | 'outcome'
  | 'actions'
  | 'summary'
  | 'history'
  | 'documents'
  | 'relations'
  | 'footer_actions'

export const DETAIL_RAIL_BLOCK_ORDER: DetailRailBlockId[] = [
  'header',
  'contacts',
  'next_action',
  'actions',
  'summary',
  'history',
  'documents',
  'relations',
  'footer_actions',
]

/** Fixed zone — always visible; never scrolls with table or rail body. */
export const DETAIL_RAIL_FIXED_BLOCK_IDS: readonly DetailRailBlockId[] = [
  'header',
  'contacts',
  'next_action',
  'outcome',
  'actions',
]

/** Scroll zone — contextual depth; Entity Workspace holds full record. */
export const DETAIL_RAIL_SCROLL_BLOCK_IDS: readonly DetailRailBlockId[] = [
  'summary',
  'history',
  'documents',
  'relations',
  'footer_actions',
]

const DETAIL_RAIL_FIXED_SET = new Set<DetailRailBlockId>(DETAIL_RAIL_FIXED_BLOCK_IDS)

export function isDetailRailFixedBlock(blockId: DetailRailBlockId): boolean {
  return DETAIL_RAIL_FIXED_SET.has(blockId)
}

export const DEFAULT_DETAIL_RAIL_WIDTH_PX = 380

export type DetailRailHeaderModel = {
  title: string
  /** Primary entity link — click opens Entity Workspace (Interaction Rules §primaryEntityLink). */
  titleHref?: string
  subtitle?: string
  meta?: string
  statusLabel?: string
  statusSemantic?: SemanticRole
  stageLabel?: string
  stageSemantic?: SemanticRole
  entityId?: string
  /** Fixed header link below title — «Открыть полную карточку». */
  entityWorkspaceHref?: string
  entityWorkspaceLabel?: string
}

export type DetailRailContactAction = {
  id: string
  label: string
  href?: string
  onClick?: () => void
  variant?: 'primary' | 'secondary'
  icon?: 'phone' | 'whatsapp' | 'email'
}

export type DetailRailAction = {
  id: string
  label: string
  onClick?: () => void
  href?: string
  variant?: 'primary' | 'secondary' | 'danger' | 'link'
}

export type DetailRailActionsTier = {
  /** One dominant action — large button. */
  primary?: DetailRailAction | null
  /** 2–4 frequent actions — compact buttons. */
  secondary?: DetailRailAction[]
  /** Overflow menu items. */
  more?: DetailRailAction[]
}

export type DetailRailSummaryField = {
  id: string
  label: string
  value: ReactNode
}

export type DetailRailTimelineItem = {
  id: string
  at: string
  title: string
  description?: string
}

export type DetailRailDocumentItem = {
  id: string
  name: string
  meta?: string
  href?: string
  onOpen?: () => void
}

export type DetailRailRelationItem = {
  id: string
  label: string
  href?: string
  onClick?: () => void
}

/** Structured model — read-only decision surface (§0.4). */
export type DetailRailModel = {
  resourceId: string
  /** When set, Fixed Decision Zone renders from platform ObjectDecision — preferred path. */
  decision?: ObjectDecision
  header?: DetailRailHeaderModel
  contacts?: {
    name?: string
    phone?: string
    email?: string
    actions?: DetailRailContactAction[]
    /** Icon buttons only — no repeating name/phone/email from the table. */
    compact?: boolean
  }
  nextAction?: {
    title: string
    body?: string
    /** «Почему именно это» — decision context, not table duplication. */
    whyTitle?: string
    whyBody?: string
    /** «Что будет дальше» after the primary action. */
    outcomeTitle?: string
    outcomeBody?: string
    stepLabels?: string[]
    activeStepIndex?: number
    primaryAction?: DetailRailAction | null
    variant?: 'default' | 'blocker' | 'terminal' | 'success'
    hideStepper?: boolean
  }
  /** Process closed — no recruiter action; product-language outcome (not next step). */
  processOutcome?: {
    title: string
    body?: string
    ownerLabel?: string
    whenLabel?: string
    whyLabel?: string
    variant?: 'default' | 'terminal' | 'success'
  }
  /** Per-state block order; default = DETAIL_RAIL_BLOCK_ORDER. */
  blockOrder?: DetailRailBlockId[]
  actions?: DetailRailActionsTier
  /** @deprecated use `actions.secondary` */
  quickActions?: DetailRailAction[]
  summaryFields?: DetailRailSummaryField[]
  summaryExpandLabel?: string
  onSummaryExpand?: () => void
  timeline?: DetailRailTimelineItem[]
  documents?: DetailRailDocumentItem[]
  relations?: DetailRailRelationItem[]
  /** @deprecated use `actions.more` or footer_actions block */
  moreActions?: DetailRailAction[]
  footerActions?: DetailRailAction[]
}

export type DetailRailNavigation = {
  hasPrevious: boolean
  hasNext: boolean
  onPrevious?: () => void
  onNext?: () => void
  previousLabel?: string
  nextLabel?: string
}

export type DetailRailPinState = {
  pinned: boolean
  onTogglePin: () => void
  pinLabel?: string
  unpinLabel?: string
}

export type DetailRailProps = {
  open: boolean
  model: DetailRailModel | null
  loading?: boolean
  onClose: () => void
  widthPx?: number
  navigation?: DetailRailNavigation
  pin?: DetailRailPinState
  blockOverrides?: Partial<Record<DetailRailBlockId, ReactNode>>
  emptyTitle?: string
  emptyDescription?: string
}
