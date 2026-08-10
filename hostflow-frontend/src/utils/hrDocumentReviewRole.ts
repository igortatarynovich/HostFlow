/**
 * Mirrors backend HR document review gate (hr preset / hr_officer + admins).
 * Recruiters/supervisors may have `workforce.manage` in the UI matrix but must not see HR-only review actions.
 */
import { isHrWorkspaceActor, normalizeTrustRole } from '../auth/trustRoles'

export function userMayRecordHrDocumentReview(
  role: string | undefined | null,
  presetId?: string | null,
): boolean {
  const trust = normalizeTrustRole(role)
  if (trust === 'administrator' || trust === 'superadmin') return true
  return isHrWorkspaceActor(role, presetId)
}
