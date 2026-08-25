import { useCallback, useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import {
  applyPermissionPresetToEmployeeMatrix,
  getTenantModules,
  getTenantRoleModuleMatrix,
  updateTenantRoleModuleMatrix,
} from '../../api/tenants'
import {
  PRESET_LABEL_KEYS,
  type PermissionPresetId,
} from '../../modules/users/roleOptions'
import type {
  RoleModuleMatrixRole,
  TenantModuleSettings,
  TenantRoleModuleMatrix,
} from '../../api/types'
import { usePermissions } from '../../hooks/usePermissions'
import { useI18n } from '../../i18n'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import {
  CANONICAL_MATRIX_ROLES,
  LEGACY_MATRIX_ROLES,
  RoleModuleMatrixPanel,
} from '../../components/admin/RoleModuleMatrixPanel'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { formatErrorMessage } from '../../modules/tenants/utils'

export default function RolesAccessPage() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const [matrix, setMatrix] = useState<TenantRoleModuleMatrix | null>(null)
  const [modules, setModules] = useState<TenantModuleSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showLegacy, setShowLegacy] = useState(false)

  const roleOrder = useMemo(
    () => [...CANONICAL_MATRIX_ROLES, ...LEGACY_MATRIX_ROLES] as RoleModuleMatrixRole[],
    [],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [m, mods] = await Promise.all([getTenantRoleModuleMatrix(), getTenantModules()])
      setMatrix(m)
      setModules(mods)
    } catch (err) {
      setError(formatErrorMessage(err, t('admin.settings.roles_access.load_failed', { defaultValue: 'Failed to load roles matrix' })))
      setMatrix(null)
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  if (!can('admin.users') && !can('*')) {
    return <Navigate to={CRM_APP_PATHS.settings} replace />
  }

  const handleToggle = async (
    roleKey: RoleModuleMatrixRole,
    moduleKey: keyof TenantModuleSettings,
    field: 'visible' | 'editable',
  ) => {
    if (!matrix) return
    const currentCell = matrix[roleKey]?.[moduleKey]
    if (!currentCell) return
    let nextVisible = currentCell.visible
    let nextEditable = currentCell.editable
    if (field === 'visible') {
      nextVisible = !nextVisible
      if (!nextVisible) nextEditable = false
    } else {
      nextEditable = !nextEditable
      if (nextEditable) nextVisible = true
    }
    setSaving(true)
    setError(null)
    try {
      const updated = await updateTenantRoleModuleMatrix({
        [roleKey]: { [moduleKey]: { visible: nextVisible, editable: nextEditable } },
      })
      setMatrix(updated)
    } catch (err) {
      setError(formatErrorMessage(err, t('admin.settings.roles_access.save_failed', { defaultValue: 'Failed to save' })))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <SettingsSubpageHeader
        title={t('admin.settings.roles_access.title', { defaultValue: 'Roles & access' })}
        description={t('admin.settings.roles_access.description', {
          defaultValue:
            'Trust roles and module visibility. Job titles are presets — not separate security roles (ADR-036).',
        })}
      />

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.settings.roles_access.matrix_heading', { defaultValue: 'Role × module matrix' })}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {t('admin.settings.roles_access.matrix_help', {
                defaultValue: 'V = visible, E = editable. Administrator column is locked (trust ceiling).',
              })}
            </p>
          </div>
          <label className="inline-flex items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              className="h-3.5 w-3.5 accent-brand-600"
              checked={showLegacy}
              onChange={(e) => setShowLegacy(e.target.checked)}
            />
            {t('admin.settings.roles_access.show_legacy', { defaultValue: 'Show legacy role columns' })}
          </label>
        </div>

        {error ? (
          <div className="mt-3">
            <ErrorRecoveryBanner info={{ title: error, hint: t('app.common.retry_hint') }} compact />
          </div>
        ) : null}

        {loading ? (
          <div className="mt-3 text-xs text-slate-500">{t('common.loading')}</div>
        ) : matrix && modules ? (
          <RoleModuleMatrixPanel
            matrix={matrix}
            moduleSettings={modules}
            roleOrder={roleOrder}
            saving={saving}
            t={t}
            onToggle={handleToggle}
            actorIsSuperadmin={false}
            canonicalOnly={!showLegacy}
          />
        ) : (
          <div className="mt-3 text-xs text-slate-500">{t('app.platform.tenants.modules.empty')}</div>
        )}
      </div>

      <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">
        <p className="font-medium text-slate-800">
          {t('admin.settings.roles_access.presets_title', { defaultValue: 'Presets (not roles)' })}
        </p>
        <p className="mt-1">
          {t('admin.settings.roles_access.presets_body', {
            defaultValue:
              'Recruiter, Team lead, HR, Compliance are starter packs applied to the Employee matrix column. They do not create a system role. Portal guest applies to Viewer defaults via Users form (user overrides).',
          })}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {(['recruiter', 'team_lead', 'hr', 'compliance'] as PermissionPresetId[]).map((presetId) => (
            <button
              key={presetId}
              type="button"
              className="btn-secondary btn-xs"
              disabled={saving || loading}
              onClick={async () => {
                setSaving(true)
                setError(null)
                try {
                  const updated = await applyPermissionPresetToEmployeeMatrix(presetId)
                  setMatrix(updated)
                } catch (err) {
                  setError(
                    formatErrorMessage(
                      err,
                      t('admin.settings.roles_access.preset_apply_failed', {
                        defaultValue: 'Failed to apply preset',
                      }),
                    ),
                  )
                } finally {
                  setSaving(false)
                }
              }}
            >
              {t(PRESET_LABEL_KEYS[presetId], { defaultValue: presetId })}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[11px] text-slate-500">
          {t('admin.settings.roles_access.presets_apply_help', {
            defaultValue: 'Applies the pack onto the Employee column of the matrix above.',
          })}
        </p>
      </div>
    </div>
  )
}
