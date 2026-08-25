import type { ReactNode } from 'react'
import {
  ENTITY_WORKSPACE_SLOT_KIND,
  isEntityWorkspaceSlotEnabled,
  type EntityWorkspaceEnabledSlotId,
  type EntityWorkspaceSlotId,
} from './compositionSlots'

type CompositionHostProps = {
  consumerId: string
  enabledSlots: readonly EntityWorkspaceEnabledSlotId[]
  renderers: Partial<Record<EntityWorkspaceEnabledSlotId, () => ReactNode>>
}

/**
 * Renders D2 content/platform slots for one consumer.
 * Chrome slots (`context-rail`) are wrappers — not inner content.
 */
export function EntityWorkspaceCompositionHost({
  consumerId,
  enabledSlots,
  renderers,
}: CompositionHostProps) {
  for (const id of enabledSlots) {
    if (!isEntityWorkspaceSlotEnabled(id)) {
      throw new Error(`D3: slot '${id}' cannot be enabled`)
    }
  }

  const contentSlots = enabledSlots.filter((id) => ENTITY_WORKSPACE_SLOT_KIND[id] !== 'chrome')

  return (
    <div data-entity-workspace-consumer={consumerId}>
      {contentSlots.map((id) => (
        <div key={id} data-entity-workspace-slot={id as EntityWorkspaceSlotId}>
          {renderers[id]?.() ?? null}
        </div>
      ))}
    </div>
  )
}
