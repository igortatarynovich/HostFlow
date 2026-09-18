/**
 * Visible Meta close path on the Mapping workspace.
 * Buttons without this sequence are not the operator path.
 */
export const MAPPING_CLOSE_PATH_STEP_IDS = [
  'schema',
  'example',
  'map',
  'projection',
  'applied',
] as const

export type MappingClosePathStepId = (typeof MAPPING_CLOSE_PATH_STEP_IDS)[number]
export type MappingClosePathStepState = 'done' | 'current' | 'upcoming'

export type MappingClosePathStep = {
  id: MappingClosePathStepId
  state: MappingClosePathStepState
}

export type MappingClosePathInput = {
  has_schema?: boolean
  schema_fields?: unknown[] | null
  has_sample?: boolean
  sample_evidence?: { present?: boolean } | null
  summary?: { headline?: string } | null
  projection?: unknown[] | null
  applied_evidence?: { present?: boolean } | null
}

function stepDone(id: MappingClosePathStepId, mapping: MappingClosePathInput): boolean {
  switch (id) {
    case 'schema':
      return Boolean(mapping.has_schema) || (mapping.schema_fields || []).length > 0
    case 'example':
      return Boolean(mapping.has_sample) || Boolean(mapping.sample_evidence?.present)
    case 'map':
      return mapping.summary?.headline === 'all_set'
    case 'projection':
      return (mapping.projection || []).length > 0
    case 'applied':
      return Boolean(mapping.applied_evidence?.present)
  }
}

export function mappingClosePath(mapping: MappingClosePathInput): MappingClosePathStep[] {
  let foundCurrent = false
  return MAPPING_CLOSE_PATH_STEP_IDS.map((id) => {
    if (stepDone(id, mapping)) return { id, state: 'done' as const }
    if (!foundCurrent) {
      foundCurrent = true
      return { id, state: 'current' as const }
    }
    return { id, state: 'upcoming' as const }
  })
}

export function mappingClosePathCurrent(
  mapping: MappingClosePathInput,
): MappingClosePathStepId | null {
  const current = mappingClosePath(mapping).find((step) => step.state === 'current')
  return current?.id ?? null
}
