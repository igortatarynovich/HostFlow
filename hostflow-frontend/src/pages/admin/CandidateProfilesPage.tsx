import { useCallback, useEffect, useMemo, useState } from 'react'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import {
  listCandidateProfiles,
  createCandidateProfile,
  updateCandidateProfile,
  deleteCandidateProfile,
  fixOrphanedVacancies,
  type CandidateProfile,
  type CandidateProfileCreate,
} from '../../api/candidate_profiles'
import ProfileFieldConstructor, { type FieldConfig } from '../../components/profile/ProfileFieldConstructor'
import ProfileDocumentConstructor from '../../components/profile/ProfileDocumentConstructor'
import FunnelSelector from '../../components/profile/FunnelSelector'
import ProfilePreviewModal from '../../components/profile/ProfilePreviewModal'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'
import ImportProfileModal from '../../components/profile/ImportProfileModal'
import ApplyProfileToVacanciesModal from '../../components/profile/ApplyProfileToVacanciesModal'
import BulkUpdateProfilesModal from '../../components/profile/BulkUpdateProfilesModal'
import ProfileUsageStatsModal from '../../components/profile/ProfileUsageStatsModal'
import ProfileHistoryModal from '../../components/profile/ProfileHistoryModal'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
// Field components (inline, similar to Companies.tsx)
function TextField({ label, value, onChange, placeholder, disabled, type, className }: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  type?: string
  className?: string
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <input
        type={type || 'text'}
        className={`input w-full ${className || ''}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
      />
    </label>
  )
}

function TextareaField({ label, value, onChange, placeholder, rows = 3 }: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  rows?: number
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <textarea
        className="input w-full min-h-[80px]"
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </label>
  )
}

export default function CandidateProfilesPage() {
  const { t } = useI18n()
  const [profiles, setProfiles] = useState<CandidateProfile[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingProfile, setEditingProfile] = useState<CandidateProfile | null>(null)
  const [newProfileMode, setNewProfileMode] = useState(false)
  const [previewProfile, setPreviewProfile] = useState<CandidateProfile | null>(null)
  const [usageStatsProfile, setUsageStatsProfile] = useState<CandidateProfile | null>(null)
  const [historyProfile, setHistoryProfile] = useState<CandidateProfile | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterActive, setFilterActive] = useState<boolean | null>(null)
  const [importMode, setImportMode] = useState(false)
  const [applyToVacanciesMode, setApplyToVacanciesMode] = useState<CandidateProfile | null>(null)
  const [bulkUpdateMode, setBulkUpdateMode] = useState(false)
  const [sortBy, setSortBy] = useState<'name' | 'code' | 'created_at' | 'fields_count' | 'stages_count' | 'usage_count'>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  const loadProfiles = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const profilesData = await listCandidateProfiles({ is_active: undefined })
      setProfiles(profilesData)
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.errors.load'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void loadProfiles()
  }, [loadProfiles])

  const validateProfile = useCallback((payload: CandidateProfileCreate, isUpdate: boolean = false): string | null => {
    if (!payload.code?.trim()) {
      return t('admin.candidate_profiles_page.validation.code_required')
    }
    if (!payload.name?.trim()) {
      return t('admin.candidate_profiles_page.validation.name_required')
    }

    if (!isUpdate && profiles.some((p) => p.code === payload.code.trim())) {
      return t('admin.candidate_profiles_page.validation.code_exists', { values: { code: payload.code.trim() } })
    }

    if (!/^[a-z0-9_]+$/.test(payload.code.trim().toLowerCase())) {
      return t('admin.candidate_profiles_page.validation.code_format')
    }

    const warnings: string[] = []
    if (!payload.config?.field_configs || payload.config.field_configs.length === 0) {
      warnings.push(t('admin.candidate_profiles_page.warnings.no_fields'))
    }
    if (!payload.funnel_id && (!payload.config?.stage_configs || payload.config.stage_configs.length === 0)) {
      warnings.push(t('admin.candidate_profiles_page.warnings.no_funnel_stages'))
    }
    if (!payload.config?.document_configs || payload.config.document_configs.length === 0) {
      warnings.push(t('admin.candidate_profiles_page.warnings.no_documents'))
    }

    if (warnings.length > 0) {
      localStorage.setItem('hf:profile-validation-warnings', JSON.stringify(warnings))
    } else {
      localStorage.removeItem('hf:profile-validation-warnings')
    }

    return null
  }, [t, profiles])

  const handleCreate = async (payload: CandidateProfileCreate) => {
    try {
      setError(null)
      
      const validationError = validateProfile(payload, false)
      if (validationError) {
        setError(validationError)
        const e = new Error(validationError)
        e.name = 'ValidationError'
        throw e
      }

      await createCandidateProfile(payload)
      
      const warningsJson = localStorage.getItem('hf:profile-validation-warnings')
      if (warningsJson) {
        try {
          const warnings = JSON.parse(warningsJson) as string[]
          if (warnings.length > 0) {
            console.warn('[CandidateProfilesPage] post-create validation warnings', warnings)
          }
          localStorage.removeItem('hf:profile-validation-warnings')
        } catch {
        }
      }
      
      await loadProfiles()
      setNewProfileMode(false)
    } catch (err: any) {
      if (err?.name !== 'ValidationError') {
        setError(err?.message || t('admin.candidate_profiles_page.errors.create'))
      }
      throw err
    }
  }

  const handleUpdate = async (profileId: string, payload: CandidateProfileCreate) => {
    try {
      setError(null)
      
      const validationError = validateProfile(payload, true)
      if (validationError) {
        setError(validationError)
        const e = new Error(validationError)
        e.name = 'ValidationError'
        throw e
      }

      await updateCandidateProfile(profileId, payload)
      
      const warningsJson = localStorage.getItem('hf:profile-validation-warnings')
      if (warningsJson) {
        try {
          const warnings = JSON.parse(warningsJson) as string[]
          if (warnings.length > 0) {
            console.warn('[CandidateProfilesPage] post-update validation warnings', warnings)
          }
          localStorage.removeItem('hf:profile-validation-warnings')
        } catch {
        }
      }
      
      await loadProfiles()
      setEditingProfile(null)
    } catch (err: any) {
      if (err?.name !== 'ValidationError') {
        setError(err?.message || t('admin.candidate_profiles_page.errors.update'))
      }
      throw err
    }
  }

  const handleDelete = async (profileId: string) => {
    if (!confirm(t('admin.candidate_profiles_page.confirm_delete'))) return
    try {
      setError(null)
      await deleteCandidateProfile(profileId)
      await loadProfiles()
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.errors.delete'))
    }
  }

  const handleDuplicate = async (profile: CandidateProfile) => {
    try {
      setError(null)
      const baseCode = profile.code
      let newCode = `${baseCode}_copy`
      let counter = 1
      
      while (profiles.some((p) => p.code === newCode)) {
        newCode = `${baseCode}_copy_${counter}`
        counter++
      }

      const duplicatePayload: CandidateProfileCreate = {
        code: newCode,
        name: `${profile.name}${t('admin.candidate_profiles_page.copy_suffix_name')}`,
        description: profile.description,
        client_id: profile.client_id,
        funnel_id: profile.funnel_id ?? undefined,
        config: profile.config || {},
        notes: profile.notes,
      }

      await createCandidateProfile(duplicatePayload)
      await loadProfiles()
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.errors.copy'))
    }
  }

  const handleExport = (profile: CandidateProfile) => {
    try {
      const exportData = {
        version: '1.0',
        exported_at: new Date().toISOString(),
        profile: {
          code: profile.code,
          name: profile.name,
          description: profile.description,
          notes: profile.notes,
          config: profile.config || {},
        },
      }

      const jsonString = JSON.stringify(exportData, null, 2)

      const blob = new Blob([jsonString], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `profile_${profile.code}_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.errors.export'))
    }
  }

  const handleImport = async (file: File) => {
    try {
      setError(null)
      const text = await file.text()
      const importData = JSON.parse(text)

      if (!importData.profile) {
        throw new Error(t('admin.candidate_profiles_page.errors.import_missing_profile'))
      }

      const importedProfile = importData.profile

      if (!importedProfile.code || !importedProfile.name) {
        throw new Error(t('admin.candidate_profiles_page.errors.import_missing_code_name'))
      }

      if (profiles.some((p) => p.code === importedProfile.code)) {
        let newCode = `${importedProfile.code}_imported`
        let counter = 1
        while (profiles.some((p) => p.code === newCode)) {
          newCode = `${importedProfile.code}_imported_${counter}`
          counter++
        }
        importedProfile.code = newCode
        importedProfile.name = `${importedProfile.name}${t('admin.candidate_profiles_page.import_suffix_name')}`
      }

      const importPayload: CandidateProfileCreate = {
        code: importedProfile.code,
        name: importedProfile.name,
        description: importedProfile.description || null,
        client_id: importedProfile.client_id || null,
        config: importedProfile.config || {},
        notes: importedProfile.notes || null,
      }

      await createCandidateProfile(importPayload)
      await loadProfiles()
    } catch (err: any) {
      if (err instanceof SyntaxError) {
        setError(t('admin.candidate_profiles_page.errors.import_json'))
      } else {
        setError(err?.message || t('admin.candidate_profiles_page.errors.import'))
      }
      throw err
    }
  }

  const profilesLoadErrorBanner = useMemo<FriendlyErrorInfo | null>(
    () =>
      error
        ? {
            title: error,
            hint: t('app.common.retry_hint'),
          }
        : null,
    [error, t],
  )

  return (
    <div className="space-y-4">
      <SettingsSubpageHeader
        className="mb-2"
        backLabel={t('admin.settings.subpage.back_all')}
        kicker={t('admin.candidate_profiles_page.header_kicker')}
        title={t('admin.candidate_profiles_page.title')}
        subtitle={t('admin.candidate_profiles_page.subtitle')}
      />

      <div
        className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
        role="status"
      >
        {t('admin.candidate_profiles_page.deprecation_banner')}
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2 rounded-lg border border-slate-200 bg-white p-4">
        <button
          className="btn-secondary btn-sm"
          type="button"
          onClick={async () => {
            try {
              const { updated } = await fixOrphanedVacancies()
              if (updated > 0) await loadProfiles()
              alert(
                updated > 0
                  ? t('admin.candidate_profiles_page.alerts.fix_orphan_ok', { values: { count: updated } })
                  : t('admin.candidate_profiles_page.alerts.fix_orphan_none'),
              )
            } catch (e: any) {
              alert(e?.response?.data?.detail ?? t('admin.candidate_profiles_page.alerts.error_generic'))
            }
          }}
        >
          {t('admin.candidate_profiles_page.fix_orphan_vacancies')}
        </button>
        <button className="btn-secondary" type="button" onClick={() => setImportMode(true)}>
          {t('admin.candidate_profiles_page.import')}
        </button>
        <button className="btn-secondary" type="button" onClick={() => setBulkUpdateMode(true)}>
          {t('admin.candidate_profiles_page.bulk_update')}
        </button>
        <button
          className="btn-primary"
          type="button"
          onClick={() => {
            setNewProfileMode(true)
            setEditingProfile(null)
          }}
        >
          {t('admin.candidate_profiles_page.create_profile')}
        </button>
      </div>

      {!newProfileMode && !editingProfile && profiles.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="space-y-2">
            <div className="flex gap-3">
              <input
                type="text"
                placeholder={t('admin.candidate_profiles_page.search_placeholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input flex-1"
              />
              <select
                value={filterActive === null ? 'all' : filterActive ? 'active' : 'inactive'}
                onChange={(e) => {
                  const val = e.target.value
                  setFilterActive(val === 'all' ? null : val === 'active')
                }}
                className="input"
              >
                <option value="all">{t('admin.candidate_profiles_page.filter_all')}</option>
                <option value="active">{t('admin.candidate_profiles_page.filter_active')}</option>
                <option value="inactive">{t('admin.candidate_profiles_page.filter_inactive')}</option>
              </select>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="input"
              >
                <option value="name">{t('admin.candidate_profiles_page.sort_name')}</option>
                <option value="code">{t('admin.candidate_profiles_page.sort_code')}</option>
                <option value="created_at">{t('admin.candidate_profiles_page.sort_created')}</option>
                <option value="fields_count">{t('admin.candidate_profiles_page.sort_fields')}</option>
                <option value="stages_count">{t('admin.candidate_profiles_page.sort_stages')}</option>
                <option value="usage_count">{t('admin.candidate_profiles_page.sort_usage')}</option>
              </select>
              <button
                type="button"
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="btn-secondary btn-sm"
                title={sortOrder === 'asc' ? t('admin.candidate_profiles_page.sort_asc') : t('admin.candidate_profiles_page.sort_desc')}
              >
                {sortOrder === 'asc' ? '↑' : '↓'}
              </button>
            </div>
            {(() => {
              const filtered = profiles.filter((profile) => {
                if (searchQuery) {
                  const query = searchQuery.toLowerCase()
                  const matchesName = profile.name.toLowerCase().includes(query)
                  const matchesCode = profile.code.toLowerCase().includes(query)
                  const matchesDescription = profile.description?.toLowerCase().includes(query) || false
                  if (!matchesName && !matchesCode && !matchesDescription) return false
                }
                if (filterActive !== null) {
                  if (filterActive && !profile.is_active) return false
                  if (!filterActive && profile.is_active) return false
                }
                return true
              })

              const sorted = [...filtered].sort((a, b) => {
                let comparison = 0
                
                switch (sortBy) {
                  case 'name':
                    comparison = (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' })
                    break
                  case 'code':
                    comparison = (a.code || '').localeCompare(b.code || '', undefined, { sensitivity: 'base' })
                    break
                  case 'created_at':
                    comparison = new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime()
                    break
                  case 'fields_count': {
                    const aFieldsCount = (a.config?.field_configs as any[])?.length || 0
                    const bFieldsCount = (b.config?.field_configs as any[])?.length || 0
                    comparison = aFieldsCount - bFieldsCount
                    break
                  }
                  case 'stages_count': {
                    const aStagesCount = a.funnel_id ? 1 : (a.config?.stage_configs as any[])?.length || 0
                    const bStagesCount = b.funnel_id ? 1 : (b.config?.stage_configs as any[])?.length || 0
                    comparison = aStagesCount - bStagesCount
                    break
                  }
                  case 'usage_count':
                    comparison = (a.usage_count || 0) - (b.usage_count || 0)
                    break
                }
                
                return sortOrder === 'asc' ? comparison : -comparison
              })

              const filteredCount = filtered.length

              if (searchQuery || filterActive !== null) {
                return (
                  <div className="text-sm text-slate-500">
                    {t('admin.candidate_profiles_page.found_count', {
                      values: { filtered: filteredCount, total: profiles.length },
                    })}
                  </div>
                )
              }
              return null
            })()}
          </div>
        </div>
      )}

      {profilesLoadErrorBanner && (
        <div className="mb-4">
          <ErrorRecoveryBanner
            info={profilesLoadErrorBanner}
            onRetry={() => void loadProfiles()}
            retryLabel={t('common.actions.refresh')}
            {...friendlyErrorBannerSecondary(
              profilesLoadErrorBanner,
              CRM_APP_PATHS.settingsCandidateProfiles,
              t('common.navigation.settings'),
            )}
            compact
          />
        </div>
      )}

      {loading ? (
        <div className="text-sm text-slate-500">{t('admin.candidate_profiles_page.loading_list')}</div>
      ) : (
        <div className="space-y-4">
          {newProfileMode && (
            <ProfileForm
              onSave={handleCreate}
              onCancel={() => setNewProfileMode(false)}
              t={t}
              profiles={profiles}
            />
          )}
          {editingProfile && (
            <ProfileForm
              profile={editingProfile}
              onSave={(payload) => handleUpdate(editingProfile.id, payload)}
              onCancel={() => setEditingProfile(null)}
              t={t}
              profiles={profiles}
            />
          )}
          {!newProfileMode && !editingProfile && (() => {
              const filtered = profiles.filter((profile) => {
                if (searchQuery) {
                  const query = searchQuery.toLowerCase()
                  const matchesName = profile.name.toLowerCase().includes(query)
                  const matchesCode = profile.code.toLowerCase().includes(query)
                  const matchesDescription = profile.description?.toLowerCase().includes(query) || false
                  if (!matchesName && !matchesCode && !matchesDescription) {
                    return false
                  }
                }
                if (filterActive !== null) {
                  if (filterActive && !profile.is_active) return false
                  if (!filterActive && profile.is_active) return false
                }
                return true
              })

              if (profiles.length === 0) {
                return (
                  <p className="text-sm text-slate-500">{t('admin.candidate_profiles_page.empty_create_hint')}</p>
                )
              }

              if (filtered.length === 0) {
                return (
                  <p className="text-sm text-slate-500">{t('admin.candidate_profiles_page.empty_filtered')}</p>
                )
              }

              const sorted = [...filtered].sort((a, b) => {
                let comparison = 0
                
                switch (sortBy) {
                  case 'name':
                    comparison = (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' })
                    break
                  case 'code':
                    comparison = (a.code || '').localeCompare(b.code || '', undefined, { sensitivity: 'base' })
                    break
                  case 'created_at':
                    comparison = new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime()
                    break
                  case 'fields_count': {
                    const aFieldsCount = (a.config?.field_configs as any[])?.length || 0
                    const bFieldsCount = (b.config?.field_configs as any[])?.length || 0
                    comparison = aFieldsCount - bFieldsCount
                    break
                  }
                  case 'stages_count': {
                    const aStagesCount = a.funnel_id ? 1 : (a.config?.stage_configs as any[])?.length || 0
                    const bStagesCount = b.funnel_id ? 1 : (b.config?.stage_configs as any[])?.length || 0
                    comparison = aStagesCount - bStagesCount
                    break
                  }
                  case 'usage_count':
                    comparison = (a.usage_count || 0) - (b.usage_count || 0)
                    break
                }
                
                return sortOrder === 'asc' ? comparison : -comparison
              })

              return (
                <div className="space-y-3">
                  {sorted.map((profile: typeof profiles[0]) => (
                    <div key={profile.id} className="rounded-lg border border-slate-200 bg-white p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-slate-900">{profile.name}</span>
                            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-mono text-slate-600">
                              {profile.code}
                            </span>
                            {!profile.is_active && (
                              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                                {t('admin.candidate_profiles_page.badge_inactive')}
                              </span>
                            )}
                            {profile.is_system && (
                              <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                                {t('admin.candidate_profiles_page.badge_system')}
                              </span>
                            )}
                            {profile.code === 'driver_ce_default' && (
                              <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                                {t('admin.candidate_profiles_page.badge_default')}
                              </span>
                            )}
                            {(profile.usage_count ?? 0) > 0 && (
                              <span className="rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                                {t('admin.candidate_profiles_page.usage_in_vacancies', {
                                  values: { count: profile.usage_count ?? 0 },
                                })}
                              </span>
                            )}
                          </div>
                          {profile.description && (
                            <p className="text-sm text-slate-600">{profile.description}</p>
                          )}
                          {profile.notes && <p className="text-xs text-slate-500">{profile.notes}</p>}
                          {profile.config && (
                            <div className="flex gap-3 text-xs text-slate-500">
                              {profile.config.field_configs && Array.isArray(profile.config.field_configs) && (
                                <span>
                                  {t('admin.candidate_profiles_page.stats_fields', {
                                    values: {
                                      count: profile.config.field_configs.filter((f: any) => f.visible !== false).length,
                                    },
                                  })}
                                  {profile.config.field_configs.filter((f: any) => f.required === true).length > 0 && (
                                    <span className="ml-1 text-red-600">
                                      {t('admin.candidate_profiles_page.stats_required', {
                                        values: {
                                          count: profile.config.field_configs.filter((f: any) => f.required === true)
                                            .length,
                                        },
                                      })}
                                    </span>
                                  )}
                                </span>
                              )}
                                              {(profile.funnel_id || (profile.config.stage_configs && Array.isArray(profile.config.stage_configs))) && (
                                <span>
                                  {profile.funnel_id
                                    ? t('admin.candidate_profiles_page.stats_funnel')
                                    : t('admin.candidate_profiles_page.stats_stages', {
                                        values: {
                                          count: profile.config.stage_configs.filter((s: any) => s.active !== false)
                                            .length,
                                        },
                                      })}
                                </span>
                              )}
                              {profile.config.document_configs && Array.isArray(profile.config.document_configs) && (
                                <span>
                                  {t('admin.candidate_profiles_page.stats_documents', {
                                    values: {
                                      count: profile.config.document_configs.filter((d: any) => d.enabled !== false)
                                        .length,
                                    },
                                  })}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            className="btn-secondary btn-sm"
                            type="button"
                            onClick={() => setPreviewProfile(profile)}
                            title={t('admin.candidate_profiles_page.action_preview_title')}
                          >
                            {t('admin.candidate_profiles_page.action_preview')}
                          </button>
                          <button
                            className="btn-secondary btn-sm"
                            type="button"
                            onClick={() => setUsageStatsProfile(profile)}
                            title={t('admin.candidate_profiles_page.action_stats_title')}
                          >
                            {t('admin.candidate_profiles_page.action_stats')}
                          </button>
                          <button
                            className="btn-secondary btn-sm"
                            type="button"
                            onClick={() => setHistoryProfile(profile)}
                            title={t('admin.candidate_profiles_page.action_history_title')}
                          >
                            {t('admin.candidate_profiles_page.action_history')}
                          </button>
                          {profile.is_system ? (
                            <button
                              className="btn-secondary btn-sm"
                              type="button"
                              onClick={() => handleDuplicate(profile)}
                              title={t('admin.candidate_profiles_page.action_duplicate_edit')}
                            >
                              {t('admin.candidate_profiles_page.action_duplicate')}
                            </button>
                          ) : (
                            <>
                              <button
                                className="btn-secondary btn-sm"
                                type="button"
                                onClick={() => setApplyToVacanciesMode(profile)}
                                title={t('admin.candidate_profiles_page.action_apply_vacancies')}
                              >
                                {t('admin.candidate_profiles_page.action_apply_vacancies')}
                              </button>
                              <button
                                className="btn-secondary btn-sm"
                                type="button"
                                onClick={() => handleExport(profile)}
                                title={t('admin.candidate_profiles_page.action_export')}
                              >
                                {t('admin.candidate_profiles_page.action_export')}
                              </button>
                              <button
                                className="btn-secondary btn-sm"
                                type="button"
                                onClick={() => handleDuplicate(profile)}
                                title={t('admin.candidate_profiles_page.action_duplicate')}
                              >
                                {t('admin.candidate_profiles_page.action_duplicate')}
                              </button>
                              <button
                                className="btn-secondary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                type="button"
                                onClick={() => setEditingProfile(profile)}
                                disabled={(profile.usage_count ?? 0) > 0}
                                title={
                                  (profile.usage_count ?? 0) > 0
                                    ? t('admin.candidate_profiles_page.edit_blocked_title')
                                    : ''
                                }
                              >
                                {t('admin.candidate_profiles_page.action_edit')}
                              </button>
                              <button
                                className="btn-danger btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                type="button"
                                onClick={() => handleDelete(profile.id)}
                                disabled={(profile.usage_count ?? 0) > 0}
                                title={
                                  (profile.usage_count ?? 0) > 0
                                    ? t('admin.candidate_profiles_page.delete_blocked_title')
                                    : ''
                                }
                              >
                                {t('admin.candidate_profiles_page.action_delete')}
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )
            })()}
        </div>
      )}

      {previewProfile && (
        <ProfilePreviewModal
          profile={previewProfile}
          onClose={() => setPreviewProfile(null)}
          onDuplicate={() => {
            setPreviewProfile(null)
            handleDuplicate(previewProfile)
          }}
          onExport={() => {
            handleExport(previewProfile)
          }}
        />
      )}

      {importMode && (
        <ImportProfileModal
          onClose={() => setImportMode(false)}
          onImport={async (file: File) => {
            try {
              await handleImport(file)
              setImportMode(false)
            } catch (err) {
            }
          }}
        />
      )}

      {applyToVacanciesMode && (
        <ApplyProfileToVacanciesModal
          profile={applyToVacanciesMode}
          onClose={() => setApplyToVacanciesMode(null)}
          onSuccess={() => {
            loadProfiles()
          }}
        />
      )}

      {bulkUpdateMode && (
        <BulkUpdateProfilesModal
          onClose={() => setBulkUpdateMode(false)}
          onSuccess={() => {
            loadProfiles()
          }}
        />
      )}

      {usageStatsProfile && (
        <ProfileUsageStatsModal
          profile={usageStatsProfile}
          onClose={() => setUsageStatsProfile(null)}
        />
      )}

      {historyProfile && (
        <ProfileHistoryModal
          profile={historyProfile}
          onClose={() => setHistoryProfile(null)}
        />
      )}
    </div>
  )
}

function ProfileForm({
  profile,
  onSave,
  onCancel,
  t,
  profiles,
}: {
  profile?: CandidateProfile | null
  onSave: (payload: CandidateProfileCreate) => Promise<void>
  onCancel: () => void
  t: (key: string, opts?: { defaultValue?: string; values?: Record<string, string | number> }) => string
  profiles?: CandidateProfile[]
}) {
  const [code, setCode] = useState(profile?.code || '')
  const [name, setName] = useState(profile?.name || '')
  const [description, setDescription] = useState(profile?.description || '')
  const [notes, setNotes] = useState(profile?.notes || '')
  const [codeError, setCodeError] = useState<string | null>(null)
  const [nameError, setNameError] = useState<string | null>(null)
  const [fieldConfigs, setFieldConfigs] = useState<FieldConfig[]>(() => {
    // Initialize from profile config or default fields
    if (profile?.config?.field_configs) {
      return profile.config.field_configs as FieldConfig[]
    }
    // Default: always include required system fields
    return [
      {
        field_key: 'first_name',
        field_type: 'text',
        required: true,
        order: 1,
        visible: true,
        label: t('admin.candidate_profiles_page.defaults.first_name'),
      },
      {
        field_key: 'last_name',
        field_type: 'text',
        required: true,
        order: 2,
        visible: true,
        label: t('admin.candidate_profiles_page.defaults.last_name'),
      },
      {
        field_key: 'email',
        field_type: 'text',
        required: false,
        order: 3,
        visible: true,
        label: t('admin.candidate_profiles_page.defaults.email'),
      },
      {
        field_key: 'phone',
        field_type: 'text',
        required: false,
        order: 4,
        visible: true,
        label: t('admin.candidate_profiles_page.defaults.phone'),
      },
    ]
  })
  const [documentConfigs, setDocumentConfigs] = useState<Array<{
    document_type_id: string
    document_type_code: string
    required: boolean
    enabled: boolean
    alert_days_before_expiry: number | null
    order: number
  }>>(() => {
    // Initialize from profile config
    if (profile?.config?.document_configs) {
      return profile.config.document_configs as Array<{
        document_type_id: string
        document_type_code: string
        required: boolean
        enabled: boolean
        alert_days_before_expiry: number | null
        order: number
      }>
    }
    return []
  })
  const [funnelId, setFunnelId] = useState<string | null>(profile?.funnel_id ?? null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const validateCode = (newCode: string) => {
    setCodeError(null)
    if (!newCode.trim()) {
      setCodeError(t('admin.candidate_profiles_page.validation.code_inline_required'))
      return false
    }
    if (!/^[a-z0-9_]+$/.test(newCode.trim().toLowerCase())) {
      setCodeError(t('admin.candidate_profiles_page.validation.code_inline_format'))
      return false
    }
    if (!profile && profiles && profiles.some((p) => p.code === newCode.trim())) {
      setCodeError(
        t('admin.candidate_profiles_page.validation.code_inline_taken', { values: { code: newCode.trim() } }),
      )
      return false
    }
    return true
  }

  const validateName = (newName: string) => {
    setNameError(null)
    if (!newName.trim()) {
      setNameError(t('admin.candidate_profiles_page.validation.name_inline_required'))
      return false
    }
    return true
  }

  const handleCodeChange = (newCode: string) => {
    setCode(newCode)
    if (newCode.trim()) {
      validateCode(newCode)
    } else {
      setCodeError(null)
    }
  }

  const handleNameChange = (newName: string) => {
    setName(newName)
    if (newName.trim()) {
      validateName(newName)
    } else {
      setNameError(null)
    }
  }

  const handleSubmit = async () => {
    setCodeError(null)
    setNameError(null)
    setFormError(null)

    const isCodeValid = validateCode(code)
    const isNameValid = validateName(name)

    if (!isCodeValid || !isNameValid) {
      return
    }

    const warnings: string[] = []
    if (fieldConfigs.length === 0) {
      warnings.push(t('admin.candidate_profiles_page.warnings.no_fields'))
    }
    if (!funnelId && !(profile?.config?.stage_configs as any[])?.length) {
      warnings.push(t('admin.candidate_profiles_page.warnings.no_funnel_selected'))
    }
    if (documentConfigs.length === 0) {
      warnings.push(t('admin.candidate_profiles_page.warnings.no_documents'))
    }

    if (warnings.length > 0) {
      const confirmed = window.confirm(
        `${t('admin.candidate_profiles_page.warnings.save_prompt_title')}\n\n${warnings.join('\n')}\n\n${t('admin.candidate_profiles_page.warnings.save_prompt_footer')}`,
      )
      if (!confirmed) {
        return
      }
    }

    setSaving(true)
    try {
      await onSave({
        code: code.trim(),
        name: name.trim(),
        description: description || null,
        client_id: null,
        notes: notes || null,
        funnel_id: funnelId,
        config: {
          ...(profile?.config || {}),
          field_configs: fieldConfigs,
          document_configs: documentConfigs,
        },
      })
    } catch (err: any) {
      setFormError(
        err?.message ||
          (profile
            ? t('admin.candidate_profiles_page.errors.update')
            : t('admin.candidate_profiles_page.errors.create')),
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <h3 className="mb-3 text-base font-semibold text-blue-800">
        {profile ? t('admin.candidate_profiles_page.form.title_edit') : t('admin.candidate_profiles_page.form.title_create')}
      </h3>
      <div className="space-y-3">
        <div>
          <TextField
            label={t('admin.candidate_profiles_page.form.code')}
            value={code}
            onChange={handleCodeChange}
            disabled={!!profile || saving}
            placeholder={t('admin.candidate_profiles_page.form.code_placeholder')}
            className={codeError ? 'border-rose-300' : ''}
          />
          {codeError && <div className="mt-1 text-xs text-rose-600">{codeError}</div>}
          {!codeError && !profile && (
            <div className="mt-1 text-xs text-slate-500">{t('admin.candidate_profiles_page.form.code_hint')}</div>
          )}
        </div>
        <div>
          <TextField
            label={t('admin.candidate_profiles_page.form.name')}
            value={name}
            onChange={handleNameChange}
            disabled={saving}
            placeholder={t('admin.candidate_profiles_page.form.name_placeholder')}
            className={nameError ? 'border-rose-300' : ''}
          />
          {nameError && <div className="mt-1 text-xs text-rose-600">{nameError}</div>}
        </div>
        <TextareaField
          label={t('admin.candidate_profiles_page.form.description')}
          value={description}
          onChange={setDescription}
          rows={3}
          placeholder={t('admin.candidate_profiles_page.form.description_placeholder')}
        />
        <TextareaField
          label={t('admin.candidate_profiles_page.form.notes')}
          value={notes}
          onChange={setNotes}
          rows={2}
          placeholder={t('admin.candidate_profiles_page.form.notes_placeholder')}
        />
        
        {/* Field Constructor */}
        <div className="mt-4">
          <h3 className="mb-3 text-base font-semibold text-slate-900">
            {t('admin.candidate_profiles_page.form.section_fields')}
          </h3>
          <ProfileFieldConstructor
            value={fieldConfigs}
            onChange={setFieldConfigs}
            disabled={saving}
          />
        </div>
        
        {/* Funnel selector */}
        <div className="mt-6">
          <h3 className="mb-3 text-base font-semibold text-slate-900">
            {t('admin.candidate_profiles_page.form.section_funnel')}
          </h3>
          <FunnelSelector
            companyId={profile?.client_id}
            value={funnelId}
            onChange={setFunnelId}
            disabled={saving || !!profile?.is_system}
          />
        </div>
        
        {/* Document Constructor */}
        <div className="mt-6">
          <h3 className="mb-3 text-base font-semibold text-slate-900">
            {t('admin.candidate_profiles_page.form.section_documents')}
          </h3>
          <ProfileDocumentConstructor
            value={documentConfigs}
            onChange={setDocumentConfigs}
            disabled={saving || !!profile?.is_system}
          />
        </div>
        
        {formError && <div className="text-sm text-rose-700">{formError}</div>}
        <div className="flex gap-2 justify-end">
          <button className="btn-secondary" type="button" onClick={onCancel} disabled={saving}>
            {t('admin.candidate_profiles_page.form.cancel')}
          </button>
          <button className="btn-primary" type="button" onClick={handleSubmit} disabled={saving}>
            {saving ? t('admin.candidate_profiles_page.form.saving') : t('admin.candidate_profiles_page.form.save')}
          </button>
        </div>
      </div>
    </div>
  )
}
