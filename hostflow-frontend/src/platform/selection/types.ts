/**
 * Universal Selection Model — third platform primitive (with DataTable + DetailRail).
 * Owns focus, Detail Rail target, pin, bulk selection, and prev/next navigation order.
 */

export type SelectionBulkState = Record<string, boolean>

export type SelectionModelState = {
  /** Last row the user interacted with (table highlight). */
  activeId: string | null
  /** Whether Detail Rail is visible. */
  railOpen: boolean
  /** Entity id currently shown in Detail Rail (respects pin). */
  railEntityId: string | null
  pinned: boolean
  pinnedEntityId: string | null
  bulkIds: SelectionBulkState
}

export type SelectionModelConfig = {
  /** Ordered entity ids in the current view (table rows, kanban cards, …). */
  orderedIds: string[]
  /** When rail entity disappears from orderedIds (filter/sort), rail closes. */
  closeRailWhenEntityMissing?: boolean
}

export type SelectionModel = SelectionModelState & {
  /** Row click / keyboard — opens or updates rail unless pinned. */
  selectRow: (id: string) => void
  /** Explicit open from any surface (table, kanban, search, notification). */
  openDetailRail: (id: string) => void
  closeDetailRail: () => void
  togglePin: () => void
  setPinned: (pinned: boolean) => void
  selectPrevious: () => void
  selectNext: () => void
  hasPrevious: boolean
  hasNext: boolean
  /** Highlighted row id (active when not pinned, else pinned entity). */
  highlightedId: string | null
  isRowActive: (id: string) => boolean
  /** Bulk */
  setBulkIds: (next: SelectionBulkState | ((prev: SelectionBulkState) => SelectionBulkState)) => void
  toggleBulk: (id: string) => void
  clearBulk: () => void
}
