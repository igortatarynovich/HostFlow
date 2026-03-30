import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../store/useAuth'
import { useTenantInfo } from '../contexts/TenantInfo'
import { getTenantEffectiveRoleModules, getTenantModules } from '../api/tenants'
import type { EffectiveRoleModules, TenantModuleSettings } from '../api/types'

export type Permission =
  | '*'
  /** Leadership / supervisor analytics & reports — not granted to recruiter. */
  | 'manager.tools'
  | 'settings.view'
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
    'manager.tools',
    'settings.view',
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
  client_processor: [
    'companies.view',
    'candidates.view',
    'candidates.manage',
    'candidates.pipeline',
    'vacancies.view',
    'documents.manage',
  ],
  client_manager: [
    'manager.tools',
    'companies.view',
    'candidates.view',
    'candidates.manage',
    'candidates.pipeline',
    'vacancies.view',
    'documents.manage',
    'users.view',
    'users.manage',
    'notifications.view',
    'settings.view',
  ],
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
  client_processor: 'client_processor',
  processor: 'client_processor',
  client_manager: 'client_manager',
}

const MODULE_DEFAULTS: TenantModuleSettings = {
  candidates: true,
  companies: true,
  vacancies: true,
  documents: true,
  leads: true,
  services: true,
  client_portal: true,
}

const VIEW_PERMISSION_TO_MODULE: Partial<Record<Permission, keyof TenantModuleSettings>> = {
  'companies.view': 'companies',
  'leads.view': 'leads',
  'vacancies.view': 'vacancies',
  'candidates.view': 'candidates',
  'candidates.pipeline': 'candidates',
  'services.view': 'services',
}

const EDIT_PERMISSION_TO_MODULE: Partial<Record<Permission, keyof TenantModuleSettings>> = {
  'companies.manage': 'companies',
  'candidates.manage': 'candidates',
  'candidates.requestDelete': 'candidates',
  'candidates.deleteQueue': 'candidates',
  'documents.manage': 'documents',
  'services.orders.manage': 'services',
  'services.catalog.manage': 'services',
  'services.overrideRequirements': 'services',
}

export function usePermissions() {
  const { me } = useAuth()
  const tenant = useTenantInfo()
  const [effectiveModules, setEffectiveModules] = useState<EffectiveRoleModules | null>(null)
  const [tenantModules, setTenantModules] = useState<TenantModuleSettings | null>(null)

  useEffect(() => {
    if (!me?.tenant_id || !me?.role) {
      setEffectiveModules(null)
      setTenantModules(null)
      return
    }
    let mounted = true
    ;(async () => {
      try {
        const [data, mods] = await Promise.all([
          getTenantEffectiveRoleModules(),
          getTenantModules().catch(() => null),
        ])
        if (mounted) {
          setEffectiveModules(data)
          setTenantModules(mods)
        }
      } catch {
        if (mounted) {
          setEffectiveModules(null)
          setTenantModules(null)
        }
      }
    })()
    return () => {
      mounted = false
    }
  }, [me?.tenant_id, me?.role])

  const { tenantId, role, permissions, can, isClientTenant } = useMemo(() => {
    const currentTenantId =
      (me as any)?.tenant_id || (me as any)?.tenant?.id || '11111111-1111-1111-1111-111111111111'

    const membershipRole = Array.isArray((me as any)?.memberships)
      ? (me as any).memberships.find((m: any) => m?.tenant_id === currentTenantId)?.role
      : undefined

    const rawRole = (membershipRole as any) || (me as any)?.role || 'viewer'
    const norm = String(rawRole).toLowerCase().trim()
    let effectiveRole: string = ROLE_ALIAS[norm] || norm || 'viewer'

    // For client tenants, interpret "recruiter" as "client_processor" by default
    // so client-side recruiters see only client pipeline and have client permissions.
    if (tenant?.type === 'company' && effectiveRole === 'recruiter') {
      effectiveRole = 'client_processor'
    }
    const list = ROLE_PERMISSIONS[effectiveRole] || ROLE_PERMISSIONS.viewer
    const set = new Set<Permission>(list)

    const moduleAccess = (moduleKey: keyof TenantModuleSettings) => {
      // tenant-level module flags: if a module is disabled for the workspace,
      // it must be treated as not visible regardless of role matrix.
      const tenantVisible =
        tenantModules && Object.prototype.hasOwnProperty.call(tenantModules, moduleKey)
          ? Boolean(tenantModules[moduleKey])
          : Boolean(MODULE_DEFAULTS[moduleKey])
      const cell = effectiveModules?.modules?.[moduleKey]
      if (!cell) {
        return { visible: tenantVisible, editable: tenantVisible }
      }
      return {
        visible: tenantVisible && Boolean(cell.visible),
        editable: tenantVisible && Boolean(cell.visible) && Boolean(cell.editable),
      }
    }

    const can = (perm: Permission) => {
      if (set.has('*')) return true
      if (!set.has(perm)) return false
      const editModule = EDIT_PERMISSION_TO_MODULE[perm]
      if (editModule) {
        const mod = moduleAccess(editModule)
        return mod.visible && mod.editable
      }
      const viewModule = VIEW_PERMISSION_TO_MODULE[perm]
      if (viewModule) {
        return moduleAccess(viewModule).visible
      }
      return true
    }
    const isClientTenant = tenant?.type === 'company'

    return {
      tenantId: currentTenantId,
      role: effectiveRole,
      permissions: Array.from(set),
      can,
      isClientTenant,
    }
  }, [me, tenant, effectiveModules, tenantModules])

  return { tenantId, role, permissions, can, isClientTenant }
}
