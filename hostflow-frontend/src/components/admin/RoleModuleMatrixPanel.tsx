import type { RoleModuleMatrixRole, RoleModulePermissions, TenantModuleSettings, TenantRoleModuleMatrix } from '../../api/types'
import { MODULE_LABELS } from '../../modules/tenants/constants'

/** ADR-036 canonical columns shown first; legacy kept for migration. */
export const CANONICAL_MATRIX_ROLES: RoleModuleMatrixRole[] = ['administrator', 'employee', 'viewer']

export const LEGACY_MATRIX_ROLES: RoleModuleMatrixRole[] = [
  'supervisor',
  'recruiter',
  'client_manager',
  'client_processor',
  'compliance_officer',
  'hr_officer',
]

/** Tenant admin may not edit administrator column (trust ceiling). */
export function isMatrixRoleLocked(role: RoleModuleMatrixRole, actorIsSuperadmin: boolean): boolean {
  if (actorIsSuperadmin) return false
  return role === 'administrator'
}

type Props = {
  matrix: TenantRoleModuleMatrix
  moduleSettings: TenantModuleSettings
  roleOrder: RoleModuleMatrixRole[]
  saving?: boolean
  t: (key: string, opts?: Record<string, unknown>) => string
  onToggle: (role: RoleModuleMatrixRole, module: keyof TenantModuleSettings, field: 'visible' | 'editable') => void
  actorIsSuperadmin?: boolean
  /** When true, show only canonical trust columns */
  canonicalOnly?: boolean
}

export function RoleModuleMatrixPanel({
  matrix,
  moduleSettings,
  roleOrder,
  saving,
  t,
  onToggle,
  actorIsSuperadmin = false,
  canonicalOnly = false,
}: Props) {
  const roles = canonicalOnly
    ? roleOrder.filter((r) => CANONICAL_MATRIX_ROLES.includes(r))
    : roleOrder

  const moduleKeys = Object.keys(moduleSettings) as Array<keyof TenantModuleSettings>

  return (
    <div className="mt-3 overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-xs">
        <thead>
          <tr className="bg-slate-50 text-left text-slate-600">
            <th className="px-2 py-2">{t('app.platform.tenants.modules.matrix_module')}</th>
            {roles.map((roleKey) => (
              <th key={roleKey} className="px-2 py-2">
                {t(`app.admin.users.roles.${roleKey}`, { defaultValue: roleKey })}
                {isMatrixRoleLocked(roleKey, actorIsSuperadmin) ? (
                  <span className="ml-1 text-[10px] text-slate-400">
                    {t('admin.settings.roles_access.ceiling_locked', { defaultValue: '(locked)' })}
                  </span>
                ) : null}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {moduleKeys.map((moduleKey) => (
            <tr key={moduleKey}>
              <td className="px-2 py-2 font-medium text-slate-700">
                {t(MODULE_LABELS[moduleKey] || moduleKey, { defaultValue: String(moduleKey) })}
              </td>
              {roles.map((roleKey) => {
                const cell: RoleModulePermissions | undefined = matrix[roleKey]?.[moduleKey]
                const moduleEnabled = Boolean(moduleSettings[moduleKey])
                const locked = isMatrixRoleLocked(roleKey, actorIsSuperadmin)
                const viewerMute =
                  roleKey === 'viewer' &&
                  moduleKey !== 'documents' &&
                  moduleKey !== 'client_portal'
                return (
                  <td key={`${roleKey}:${moduleKey}`} className="px-2 py-2">
                    <div className="flex items-center gap-2">
                      <label className="inline-flex items-center gap-1 text-[11px] text-slate-600">
                        <input
                          type="checkbox"
                          className="h-3.5 w-3.5 accent-brand-600"
                          checked={Boolean(cell?.visible)}
                          disabled={saving || !moduleEnabled || locked}
                          onChange={() => onToggle(roleKey, moduleKey, 'visible')}
                        />
                        V
                      </label>
                      <label className="inline-flex items-center gap-1 text-[11px] text-slate-600">
                        <input
                          type="checkbox"
                          className="h-3.5 w-3.5 accent-brand-600"
                          checked={Boolean(cell?.editable)}
                          disabled={
                            saving || !moduleEnabled || !cell?.visible || locked || viewerMute
                          }
                          onChange={() => onToggle(roleKey, moduleKey, 'editable')}
                        />
                        E
                      </label>
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-2 text-[11px] text-slate-500">{t('app.platform.tenants.modules.matrix_hint')}</div>
    </div>
  )
}
