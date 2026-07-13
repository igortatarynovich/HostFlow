/**
 * HostFlow Interaction Rules — platform behavior canon (Layer 2).
 * Spec: docs/specs/architecture/hostflow-interaction-rules-v1.md
 * Parent: docs/specs/architecture/hostflow-platform-canon-v1.md
 *
 * Modules import these constants — never redefine behavior locally.
 */

/** Double-click is forbidden platform-wide. */
export const INTERACTION_DOUBLE_CLICK_ALLOWED = false as const

export const INTERACTION_CLICK = {
  row: 'open_detail_rail',
  rowToggle: 'toggle_detail_rail_when_same_row',
  primaryEntityLink: 'open_entity_workspace',
  secondaryEntityLink: 'open_linked_entity_workspace',
  checkbox: 'toggle_bulk_only',
} as const

export const INTERACTION_KEYBOARD = {
  openDetailRail: { key: 'Enter', modifiers: [] as const },
  openEntityWorkspace: { key: 'Enter', modifiers: ['meta', 'ctrl'] as const },
  closeDetailRail: { key: 'Escape', modifiers: [] as const },
  navigatePrevious: { key: 'ArrowUp', modifiers: [] as const },
  navigateNext: { key: 'ArrowDown', modifiers: [] as const },
} as const

export type InteractionKeyboardRule = {
  key: string
  /** At least one modifier required when non-empty; meta OR ctrl satisfies openEntityWorkspace. */
  modifiers: readonly ('meta' | 'ctrl' | 'shift' | 'alt')[]
}

export const INTERACTION_SELECTION = {
  singleActiveRow: true,
  bulkViaCheckboxOnly: true,
  persistRailWhenEntityInView: true,
  closeRailWhenEntityMissing: true,
} as const

export const INTERACTION_EDITING = {
  dataTableInlineEdit: false,
  detailRailEditable: false,
  entityWorkspaceEditable: true,
  contextRailEditable: false,
} as const

export const INTERACTION_ACTION_TIERS = {
  maxPrimary: 1,
  maxSecondary: 4,
  overflowTier: 'more',
} as const

/** Returns true if the keyboard event matches a canon rule (meta OR ctrl for workspace open). */
export function matchesInteractionKeyboardRule(
  event: Pick<KeyboardEvent, 'key' | 'metaKey' | 'ctrlKey' | 'shiftKey' | 'altKey'>,
  rule: InteractionKeyboardRule,
): boolean {
  if (event.key !== rule.key) return false
  if (rule.modifiers.length === 0) {
    return !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey
  }
  if (rule.key === 'Enter' && rule.modifiers.includes('meta') && rule.modifiers.includes('ctrl')) {
    return event.metaKey || event.ctrlKey
  }
  const needsMeta = rule.modifiers.includes('meta') && event.metaKey
  const needsCtrl = rule.modifiers.includes('ctrl') && event.ctrlKey
  const needsShift = rule.modifiers.includes('shift') && event.shiftKey
  const needsAlt = rule.modifiers.includes('alt') && event.altKey
  return (
    (rule.modifiers.includes('meta') ? needsMeta : true) &&
    (rule.modifiers.includes('ctrl') ? needsCtrl : true) &&
    (rule.modifiers.includes('shift') ? needsShift : !event.shiftKey) &&
    (rule.modifiers.includes('alt') ? needsAlt : !event.altKey)
  )
}

export function isOpenEntityWorkspaceKeyboardEvent(
  event: Pick<KeyboardEvent, 'key' | 'metaKey' | 'ctrlKey' | 'shiftKey' | 'altKey'>,
): boolean {
  return matchesInteractionKeyboardRule(event, INTERACTION_KEYBOARD.openEntityWorkspace)
}

export function isOpenDetailRailKeyboardEvent(
  event: Pick<KeyboardEvent, 'key' | 'metaKey' | 'ctrlKey' | 'shiftKey' | 'altKey'>,
): boolean {
  return matchesInteractionKeyboardRule(event, INTERACTION_KEYBOARD.openDetailRail)
}

export function isCloseDetailRailKeyboardEvent(
  event: Pick<KeyboardEvent, 'key' | 'metaKey' | 'ctrlKey' | 'shiftKey' | 'altKey'>,
): boolean {
  return matchesInteractionKeyboardRule(event, INTERACTION_KEYBOARD.closeDetailRail)
}
