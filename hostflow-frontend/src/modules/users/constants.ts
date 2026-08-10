/**
 * Constants for users module
 */

import type { AdminUser, UserRole } from '../../api/types';
import { normalizeTrustRole, type TrustRole } from '../../auth/trustRoles';

export const ROLE_LABEL_KEYS: Record<UserRole, string> = {
  administrator: 'app.admin.users.roles.administrator',
  employee: 'app.admin.users.roles.employee',
  supervisor: 'app.admin.users.roles.supervisor',
  recruiter: 'app.admin.users.roles.recruiter',
  client_manager: 'app.admin.users.roles.client_manager',
  client_processor: 'app.admin.users.roles.client_processor',
  compliance_officer: 'app.admin.users.roles.compliance_officer',
  hr_officer: 'app.admin.users.roles.hr_officer',
  viewer: 'app.admin.users.roles.viewer',
};

export const ROLE_BADGE_CLASSES: Record<UserRole, string> = {
  administrator: 'bg-brand-50 text-brand-700 border border-brand-100',
  employee: 'bg-emerald-50 text-emerald-700 border border-emerald-100',
  supervisor: 'bg-purple-50 text-purple-700 border border-purple-100',
  recruiter: 'bg-emerald-50 text-emerald-700 border border-emerald-100',
  client_manager: 'bg-sky-50 text-sky-700 border border-sky-100',
  client_processor: 'bg-amber-50 text-amber-700 border border-amber-100',
  compliance_officer: 'bg-teal-50 text-teal-800 border border-teal-100',
  hr_officer: 'bg-indigo-50 text-indigo-800 border border-indigo-100',
  viewer: 'bg-slate-50 text-slate-700 border border-slate-200',
};

const TRUST_LABEL_KEYS: Record<Exclude<TrustRole, 'superadmin'>, string> = {
  administrator: ROLE_LABEL_KEYS.administrator,
  employee: ROLE_LABEL_KEYS.employee,
  viewer: ROLE_LABEL_KEYS.viewer,
};

const TRUST_BADGE_CLASSES: Record<Exclude<TrustRole, 'superadmin'>, string> = {
  administrator: ROLE_BADGE_CLASSES.administrator,
  employee: ROLE_BADGE_CLASSES.employee,
  viewer: ROLE_BADGE_CLASSES.viewer,
};

/** Prefer trust-bucket label for badges when showing migrated memberships. */
export function trustRoleLabelKey(role: string | null | undefined): string {
  const trust = normalizeTrustRole(role)
  if (trust === 'superadmin') return ROLE_LABEL_KEYS.administrator
  return TRUST_LABEL_KEYS[trust]
}

export function trustRoleBadgeClass(role: string | null | undefined): string {
  const trust = normalizeTrustRole(role)
  if (trust === 'superadmin') return ROLE_BADGE_CLASSES.administrator
  return TRUST_BADGE_CLASSES[trust]
}

export const USER_STATUS_BADGES: Record<AdminUser['status'], string> = {
  active: 'bg-emerald-100 text-emerald-700',
  inactive: 'bg-gray-100 text-gray-600',
  invited: 'bg-amber-100 text-amber-700',
};

export const USER_STATUS_LABELS: Record<AdminUser['status'], string> = {
  active: 'app.admin.users.table.status.active',
  inactive: 'app.admin.users.table.status.inactive',
  invited: 'app.admin.users.table.status.invited',
};

