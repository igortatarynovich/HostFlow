/**
 * Backend `GET /settings/communications` enforces `assert_comm_feature_access(..., communicationsAdmin)`.
 * Allowed: administrator and team-lead lane (legacy supervisor/manager/lead, or employee + team_lead).
 * Do not use JOB_PROXY allowlists that expand to canonical `employee` — that would make every recruiter hit a 403.
 * Platform superadmin bypass exists only on the server.
 */
import { canUseTeamOverviewLane } from '../auth/trustRoles'

export const ROLES_CAN_LOAD_FULL_COMMUNICATIONS_SETTINGS = new Set([
  'administrator',
  'supervisor',
  'manager',
  'lead',
])

export function roleMayLoadFullCommunicationsSettings(
  role: string | undefined,
  opts?: { accessContext?: string | null; presetId?: string | null },
): boolean {
  const ur = String(role || '').trim().toLowerCase()
  if (ROLES_CAN_LOAD_FULL_COMMUNICATIONS_SETTINGS.has(ur)) return true
  return canUseTeamOverviewLane({ role, presetId: opts?.presetId })
}
