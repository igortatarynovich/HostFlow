import type { StatusBadgeSemantic } from '../../components/ui/statusBadgeSemantics'
import type { SemanticRole } from './types'

/** Semantic role → StatusBadge palette (single mapping for entire platform). */
export const SEMANTIC_ROLE_PALETTE: Record<SemanticRole, StatusBadgeSemantic> = {
  process_stage: 'info',
  status: 'neutral',
  source: 'brand',
  priority: 'warning',
  blocker: 'danger',
  success: 'success',
  warning: 'warning',
  object_type: 'info',
  neutral: 'neutral',
}

export function semanticRoleToBadgeSemantic(role: SemanticRole | undefined): StatusBadgeSemantic {
  if (!role) return 'neutral'
  return SEMANTIC_ROLE_PALETTE[role] ?? 'neutral'
}
