/**
 * Backend `GET /settings/communications` enforces `assert_comm_feature_access(..., communicationsAdmin)`.
 * Default allowed roles (unless overridden in tenant settings): administrator, supervisor (+ employee team_lead).
 * Platform superadmin bypass exists only on the server.
 */
import { actorSatisfiesRoleAllowlist, canUseTeamOverviewLane } from '../auth/trustRoles'

export const ROLES_CAN_LOAD_FULL_COMMUNICATIONS_SETTINGS = new Set([
  'administrator',
  'supervisor',
  'employee',
])

export function roleMayLoadFullCommunicationsSettings(
  role: string | undefined,
  opts?: { accessContext?: string | null; presetId?: string | null },
): boolean {
  if (canUseTeamOverviewLane({ role, presetId: opts?.presetId })) return true
  return actorSatisfiesRoleAllowlist({
    role,
    allowed: ROLES_CAN_LOAD_FULL_COMMUNICATIONS_SETTINGS,
    accessContext: opts?.accessContext,
  })
}
