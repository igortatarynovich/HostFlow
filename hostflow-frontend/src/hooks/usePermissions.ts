import { useMemo } from 'react'
import { useAuth } from '../store/useAuth'

export type Permission =
  | '*'
  | 'users.view'
  | 'users.manage'
  | 'admin.users'
  | 'admin.ruleset'
  | 'admin.companyAcl'
  | 'admin.deletionQueue'
  | 'admin.metaLeads'
  | 'notifications.view'
  | 'companies.view'
  | 'companies.manage'
  | 'leads.view'
  | 'vacancies.view'
  | 'candidates.view'
  | 'candidates.requestDelete'
  | 'candidates.deleteQueue'
  | 'candidates.manage'
  | 'candidates.pipeline'
  | 'documents.manage'
  | 'services.view'
  | 'services.orders.manage'
  | 'services.catalog.manage'
  | 'services.overrideRequirements'

const ROLE_PERMISSIONS: Record<string, Permission[]> = {
  administrator: ['*'],
  supervisor: [
    'users.view',
    'companies.view',
    'companies.manage',
    'leads.view',
    'vacancies.view',
    'notifications.view',
    'candidates.view',
    'candidates.manage',
    'candidates.requestDelete',
    'candidates.deleteQueue',
    'candidates.pipeline',
    'documents.manage',
    'admin.companyAcl',
    'admin.deletionQueue',
    'admin.metaLeads',
    'services.view',
    'services.orders.manage',
  ],
  recruiter: [
    'companies.view',
    'leads.view',
    'notifications.view',
    'vacancies.view',
    'candidates.view',
    'candidates.manage',
    'candidates.requestDelete',
    'candidates.pipeline',
    'documents.manage',
    'services.view',
    'services.orders.manage',
  ],
  viewer: ['companies.view', 'leads.view', 'vacancies.view', 'candidates.view', 'services.view'],
}

const ROLE_ALIAS: Record<string, string> = {
  owner: 'administrator',
  admin: 'administrator',
  administrator: 'administrator',
  superadmin: 'administrator',
  super_admin: 'administrator',
  manager: 'supervisor',
  lead: 'supervisor',
  supervisor: 'supervisor',
  recruiter: 'recruiter',
  viewer: 'viewer',
  user: 'viewer',
}

export function usePermissions() {
  const { me } = useAuth()

  const { tenantId, role, permissions, can } = useMemo(() => {
    const currentTenantId =
      (me as any)?.tenant_id || (me as any)?.tenant?.id || '11111111-1111-1111-1111-111111111111'

    const membershipRole = Array.isArray((me as any)?.memberships)
      ? (me as any).memberships.find((m: any) => m?.tenant_id === currentTenantId)?.role
      : undefined

    const rawRole = (membershipRole as any) || (me as any)?.role || 'viewer'
    const norm = String(rawRole).toLowerCase().trim()
    const effectiveRole: string = ROLE_ALIAS[norm] || norm || 'viewer'
    const list = ROLE_PERMISSIONS[effectiveRole] || ROLE_PERMISSIONS.viewer
    const set = new Set<Permission>(list)

    const can = (perm: Permission) => set.has('*') || set.has(perm)

    return { tenantId: currentTenantId, role: effectiveRole, permissions: Array.from(set), can }
  }, [me])

  return { tenantId, role, permissions, can }
}
