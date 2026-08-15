export type {
  EntityWorkspaceEnabledSlotId,
  EntityWorkspaceReservedSlotId,
  EntityWorkspaceSlotId,
} from './compositionSlots'

export {
  ENTITY_WORKSPACE_ENABLED_SLOT_IDS,
  ENTITY_WORKSPACE_RESERVED_SLOT_IDS,
  ENTITY_WORKSPACE_SLOT_CATALOG,
  ENTITY_WORKSPACE_SLOT_KIND,
  isEntityWorkspaceSlotEnabled,
} from './compositionSlots'

export {
  SALES_INQUIRY_COMPOSITION_CONSUMER_ID,
  SALES_INQUIRY_COMPOSITION_SLOTS,
  assertSalesInquiryCompositionSlots,
} from './salesInquiryConsumer'
export type { SalesInquiryCompositionSlotId } from './salesInquiryConsumer'

export {
  CANDIDATE_COMPOSITION_CONSUMER_ID,
  CANDIDATE_COMPOSITION_SLOTS,
  assertCandidateCompositionSlots,
} from './candidateConsumer'
export type { CandidateCompositionSlotId } from './candidateConsumer'

export { EntityWorkspaceCompositionHost } from './compositionHost'

export type {
  ContextRailBlockId,
  ContextRailConfig,
  ContextRailEventItem,
  ContextRailModel,
  ContextRailTaskItem,
  EntityContextRailBlockId,
  EntityContextRailContactAction,
  EntityContextRailEventItem,
  EntityContextRailModel,
  EntityContextRailTaskItem,
  EntityWorkspaceActionConfig,
  EntityWorkspaceBreadcrumb,
  EntityWorkspaceConfig,
  EntityWorkspaceHeaderChip,
  EntityWorkspaceHeaderExtension,
  EntityWorkspaceHeaderMetaItem,
  EntityWorkspaceHeaderModel,
  EntityWorkspaceNavigationConfig,
  EntityWorkspaceSectionDescriptor,
  EntityWorkspaceSectionId,
  EntityWorkspaceSectionRenderer,
  EntityWorkspaceSectionSlot,
  EntityWorkspaceShellLabels,
  EntityWorkspaceShellProps,
  EntityWorkspaceSummaryCard,
  EntityWorkspaceSummaryCardTone,
  EntityWorkspaceSummaryField,
  EntityWorkspaceSummaryModel,
} from './types'

export {
  CONTEXT_RAIL_BLOCK_ORDER,
  DEFAULT_CONTEXT_RAIL_WIDTH_PX,
  DEFAULT_ENTITY_CONTEXT_RAIL_WIDTH_PX,
  DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS,
  ENTITY_CONTEXT_RAIL_BLOCK_ORDER,
  ENTITY_WORKSPACE_SECTION_ORDER,
} from './types'

export { EntityWorkspaceShell } from './EntityWorkspaceShell'
export { EntityWorkspaceShellHarness } from './EntityWorkspaceShellHarness'
export { EntityWorkspaceContextRail } from './EntityWorkspaceContextRail'
export { EntityWorkspaceDefaultSectionContent } from './EntityWorkspaceDefaultSectionContent'
export {
  projectEntityContextRail,
  projectEntityWorkspaceHeader,
  projectEntityWorkspaceSummary,
  resolveEnabledWorkspaceSections,
} from './projectEntityWorkspaceView'

export { ENTITY_WORKSPACE_MOCKS, type EntityWorkspaceMockKey } from './mocks/entityWorkspaceMocks'
