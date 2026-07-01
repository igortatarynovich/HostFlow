import { CRM_APP_PATHS } from '../app/crmAppPaths'
import type { Permission } from '../hooks/usePermissions'

/** Logo/branding: tenant admins → My company; platform operators → Tenants; else workspace settings hub. */
export function resolveBrandingSetupHref(can: (p: Permission) => boolean): string {
  if (can('admin.companyAcl')) return CRM_APP_PATHS.settingsTenants
  if (can('companies.view')) return CRM_APP_PATHS.myCompany
  return `${CRM_APP_PATHS.settings}?section=workspace`
}
