/**
 * ADR-036 assignable trust roles + permission presets (not system roles).
 */

import type { UserRole } from '../../api/types'

/** Roles that may be assigned in Users admin UI / API. */
export const TRUST_ROLE_OPTIONS = ['administrator', 'employee', 'viewer'] as const
export type TrustRoleOption = (typeof TRUST_ROLE_OPTIONS)[number]

export const PERMISSION_PRESET_OPTIONS = [
  'recruiter',
  'team_lead',
  'hr',
  'compliance',
  'portal_guest',
] as const
export type PermissionPresetId = (typeof PERMISSION_PRESET_OPTIONS)[number]

export const TRUST_ROLE_LABEL_KEYS: Record<TrustRoleOption, string> = {
  administrator: 'app.admin.users.roles.administrator',
  employee: 'app.admin.users.roles.employee',
  viewer: 'app.admin.users.roles.viewer',
}

export const PRESET_LABEL_KEYS: Record<PermissionPresetId, string> = {
  recruiter: 'app.admin.users.presets.recruiter',
  team_lead: 'app.admin.users.presets.team_lead',
  hr: 'app.admin.users.presets.hr',
  compliance: 'app.admin.users.presets.compliance',
  portal_guest: 'app.admin.users.presets.portal_guest',
}

/** Map any stored role (incl. legacy) to a trust role for selects / badges. */
export function toTrustRole(role: string | null | undefined): TrustRoleOption {
  const r = String(role || '').trim().toLowerCase()
  if (r === 'administrator' || r === 'admin' || r === 'owner') return 'administrator'
  if (
    r === 'employee' ||
    r === 'recruiter' ||
    r === 'supervisor' ||
    r === 'manager' ||
    r === 'hr_officer' ||
    r === 'compliance_officer' ||
    r === 'hr' ||
    r === 'compliance'
  ) {
    return 'employee'
  }
  return 'viewer'
}

export function isTrustRoleOption(role: string): role is TrustRoleOption {
  return (TRUST_ROLE_OPTIONS as readonly string[]).includes(role)
}

export function presetsForTrustRole(role: TrustRoleOption): PermissionPresetId[] {
  if (role === 'employee') return ['recruiter', 'team_lead', 'hr', 'compliance']
  if (role === 'viewer') return ['portal_guest']
  return []
}

export function defaultPresetForTrustRole(role: TrustRoleOption): PermissionPresetId | '' {
  if (role === 'employee') return 'recruiter'
  if (role === 'viewer') return 'portal_guest'
  return ''
}

/** Narrow UserRole union for form state while API still types legacy. */
export function asAssignableUserRole(role: TrustRoleOption): UserRole {
  return role
}
