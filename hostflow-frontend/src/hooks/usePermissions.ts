import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../store/useAuth'
import { useTenantInfo } from '../contexts/TenantInfo'
import { getTenantEffectiveRoleModules, getTenantModules } from '../api/tenants'
import type { EffectiveRoleModules, TenantModuleSettings } from '../api/types'
import {
  resolveActorTrustContext,
  resolvePermissionPersona,
  type AccessContext,
  type PermissionPresetId,
  type TrustRole,
} from '../auth/trustRoles'

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
  /** HR workspace (`/app/hr/*`) — employees, separate from recruitment. */
  | 'workforce.view'
  | 'workforce.manage'
  /** Alias used by some settings cards / sales surfaces. */
  | 'sales.view'

const ROLE_PERMISSIONS: Record<string, Permission[]> = {
  // Static checker reads this map directly; runtime maps superadmin → administrator.
  superadmin: ['*'],
  administrator: ['*'],
  employee: [
    'companies.view',
    'sales.view',
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
    'workforce.view',
    'workforce.manage',
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
  compliance_officer: [
    'companies.view',
    'leads.view',
    'notifications.view',
    'vacancies.view',
    'candidates.view',
    'candidates.manage',
    'candidates.pipeline',
    'documents.manage',
    'services.view',
    'services.orders.manage',
  ],
  hr_officer: ['notifications.view', 'workforce.view', 'workforce.manage'],
}

const MODULE_DEFAULTS: TenantModuleSettings = {
  candidates: true,
  companies: true,
  vacancies: true,
  documents: true,
  leads: true,
  services: true,
  client_portal: true,
  hr: true,
}

const VIEW_PERMISSION_TO_MODULE: Partial<Record<Permission, keyof TenantModuleSettings>> = {
  'companies.view': 'companies',
  'leads.view': 'leads',
  'vacancies.view': 'vacancies',
  'candidates.view': 'candidates',
  'candidates.pipeline': 'candidates',
  'services.view': 'services',
  'workforce.view': 'hr',
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
  'workforce.manage': 'hr',
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

  const value = useMemo(() => {
    const currentTenantId =
      (me as { tenant_id?: string; tenant?: { id?: string } } | null)?.tenant_id ||
      (me as { tenant?: { id?: string } } | null)?.tenant?.id ||
      '11111111-1111-1111-1111-111111111111'

    const isClientTenant = tenant?.type === 'company'
    const trust = resolveActorTrustContext(me)
    const persona = resolvePermissionPersona({
      role: trust.rawRole,
      accessContext: trust.accessContext,
      presetId: trust.presetId,
      isClientTenant,
    })
    const list = ROLE_PERMISSIONS[persona] || ROLE_PERMISSIONS.viewer
    const set = new Set<Permission>(list)

    const moduleAccess = (moduleKey: keyof TenantModuleSettings) => {
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

    return {
      tenantId: currentTenantId,
      /** @deprecated Prefer trustRole + presetId; persona kept for Work Hub / legacy checks. */
      role: persona,
      rawRole: trust.rawRole,
      trustRole: trust.trustRole as TrustRole,
      accessContext: trust.accessContext as AccessContext,
      presetId: trust.presetId as PermissionPresetId | null,
      permissions: Array.from(set),
      can,
      isClientTenant,
    }
  }, [me, tenant, effectiveModules, tenantModules])

  return value
}
