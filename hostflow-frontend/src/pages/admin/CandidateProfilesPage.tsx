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
  withoutLegacyRequirementConfig,
  type CandidateProfile,
  type CandidateProfileCreate,
} from '../../api/candidate_profiles'
import { listCanonicalFields, type CanonicalField } from '../../api/fieldRegistry'
import {
  createRecruitmentProfile,
  getRecruitmentProfileForCandidateProfile,
  listCurrentDocumentTypeVersions,
  publishRecruitmentProfileRevision,
  type CurrentDocumentTypeVersion,
  type RecruitmentProfileCreateInput,
  type RecruitmentProfileDocumentBinding,
  type RecruitmentProfileFieldBinding,
  type RecruitmentProfilePublication,
} from '../../api/recruitmentProfiles'
import ProfileFieldConstructor, { completeFieldBindings } from '../../components/profile/ProfileFieldConstructor'
import ProfileDocumentConstructor, { completeDocumentBindings } from '../../components/profile/ProfileDocumentConstructor'
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

type Translator = (key: string, opts?: { defaultValue?: string; values?: Record<string, string | number> }) => string

interface ProfileSubmission {
  shell: CandidateProfileCreate
  recruitment: RecruitmentProfileCreateInput
}

function canonicalConfig(
  candidateProfileCode: string,
  publication?: RecruitmentProfilePublication | null,
): Record<string, unknown> {
  return {
    ...withoutLegacyRequirementConfig(publication?.config as Record<string, unknown> | undefined),
    legacy_candidate_profile_code: candidateProfileCode,
  }
}

function TextField({ label, value, onChange, placeholder, disabled, className }: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <input className={`input w-full ${className || ''}`} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} disabled={disabled} />
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
      <textarea className="input min-h-[80px] w-full" rows={rows} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </label>
  )
}

export default function CandidateProfilesPage() {
  const { t } = useI18n()
  const [profiles, setProfiles] = useState<CandidateProfile[]>([])
  const [publications, setPublications] = useState<Record<string, RecruitmentProfilePublication | null>>({})
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
      const profileRows = await listCandidateProfiles({ is_active: undefined })
      const resolved = await Promise.all(profileRows.map(async (profile) => [
        profile.code,
        await getRecruitmentProfileForCandidateProfile(profile.code),
      ] as const))
      setProfiles(profileRows)
      setPublications(Object.fromEntries(resolved))
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.errors.load'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { void loadProfiles() }, [loadProfiles])

  const validateShell = useCallback((payload: CandidateProfileCreate, isUpdate = false): string | null => {
    if (!payload.code?.trim()) return t('admin.candidate_profiles_page.validation.code_required')
    if (!payload.name?.trim()) return t('admin.candidate_profiles_page.validation.name_required')
    if (!isUpdate && profiles.some((profile) => profile.code === payload.code.trim())) {
      return t('admin.candidate_profiles_page.validation.code_exists', { values: { code: payload.code.trim() } })
    }
    if (!/^[a-z0-9_]+$/.test(payload.code.trim().toLowerCase())) {
      return t('admin.candidate_profiles_page.validation.code_format')
    }
    return null
  }, [profiles, t])

  const handleCreate = async ({ shell, recruitment }: ProfileSubmission) => {
    const validationError = validateShell(shell)
    if (validationError) throw new Error(validationError)
    setError(null)
    try {
      await createCandidateProfile(shell)
      await createRecruitmentProfile(recruitment)
      await loadProfiles()
      setNewProfileMode(false)
    } catch (err: any) {
      await loadProfiles()
      setError(err?.message || t('admin.candidate_profiles_page.errors.create'))
      throw err
    }
  }

  const handleUpdate = async (profile: CandidateProfile, submission: ProfileSubmission) => {
    const validationError = validateShell(submission.shell, true)
    if (validationError) throw new Error(validationError)
    setError(null)
    try {
      await updateCandidateProfile(profile.id, submission.shell)
      const current = publications[profile.code]
      if (current && !current.is_system) {
        await publishRecruitmentProfileRevision(current.entity_profile_id, {
          expected_published_version: current.version,
          name: submission.recruitment.name,
          description: submission.recruitment.description,
          default_layout_code: submission.recruitment.default_layout_code,
          config: submission.recruitment.config,
          fields: submission.recruitment.fields,
          documents: submission.recruitment.documents,
        })
      } else {
        await createRecruitmentProfile(submission.recruitment)
      }
      await loadProfiles()
      setEditingProfile(null)
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.errors.update'))
      throw err
    }
  }

  const handleDelete = async (profileId: string) => {
    if (!confirm(t('admin.candidate_profiles_page.confirm_delete'))) return
    try {
      await deleteCandidateProfile(profileId)
      await loadProfiles()
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.errors.delete'))
    }
  }

  const uniqueCopyCode = (baseCode: string, suffix: 'copy' | 'imported') => {
    let next = `${baseCode}_${suffix}`
    let counter = 1
    while (profiles.some((profile) => profile.code === next)) next = `${baseCode}_${suffix}_${counter++}`
    return next
  }

  const createShellAndCanonical = async (
    shell: CandidateProfileCreate,
    source: RecruitmentProfilePublication | null,
    fields = source?.fields || [],
    documents: RecruitmentProfileDocumentBinding[] = source?.documents || [],
  ) => {
    await createCandidateProfile(shell)
    await createRecruitmentProfile({
      name: shell.name,
      description: shell.description || null,
      default_layout_code: source?.default_layout_code || null,
      config: canonicalConfig(shell.code, source),
      fields: fields.map((field) => ({ ...field })),
      documents: documents.map((document) => ({
        document_type_version_id: document.document_type_version_id,
        requirement_level: document.requirement_level,
        sort_order: document.sort_order,
      })),
    })
  }

  const handleDuplicate = async (profile: CandidateProfile) => {
    try {
      const newCode = uniqueCopyCode(profile.code, 'copy')
      await createShellAndCanonical({
        code: newCode,
        name: `${profile.name}${t('admin.candidate_profiles_page.copy_suffix_name')}`,
        description: profile.description,
        client_id: profile.client_id,
        funnel_id: profile.funnel_id ?? undefined,
        config: withoutLegacyRequirementConfig(profile.config),
        notes: profile.notes,
      }, publications[profile.code] || null)
      await loadProfiles()
    } catch (err: any) {
      setError(err?.message || t('admin.candidate_profiles_page.errors.copy'))
    }
  }

  const handleExport = (profile: CandidateProfile) => {
    const publication = publications[profile.code]
    const exportData = {
      version: '2.0',
      exported_at: new Date().toISOString(),
      profile: {
        code: profile.code,
        name: profile.name,
        description: profile.description,
        notes: profile.notes,
        config: withoutLegacyRequirementConfig(profile.config),
      },
      recruitment_profile: publication ? {
        default_layout_code: publication.default_layout_code,
        config: canonicalConfig(profile.code, publication),
        fields: publication.fields,
        documents: publication.documents.map((document) => ({
          document_type_version_id: document.document_type_version_id,
          requirement_level: document.requirement_level,
          sort_order: document.sort_order,
        })),
      } : null,
    }
    const url = URL.createObjectURL(new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `profile_${profile.code}_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleImport = async (file: File) => {
    try {
      const importData = JSON.parse(await file.text())
      const imported = importData.profile
      if (!imported?.code || !imported?.name) throw new Error(t('admin.candidate_profiles_page.errors.import_missing_code_name'))
      if (imported.config?.field_configs || imported.config?.document_configs) {
        throw new Error('Legacy requirement JSON cannot be imported. Export a canonical v2 profile instead.')
      }
      const code = profiles.some((profile) => profile.code === imported.code)
        ? uniqueCopyCode(imported.code, 'imported')
        : imported.code
      const canonical = importData.recruitment_profile
      if (canonical && (!Array.isArray(canonical.fields) || !Array.isArray(canonical.documents))) {
        throw new Error('Canonical import requires complete fields and documents arrays.')
      }
      await createShellAndCanonical({
        code,
        name: code === imported.code ? imported.name : `${imported.name}${t('admin.candidate_profiles_page.import_suffix_name')}`,
        description: imported.description || null,
        client_id: imported.client_id || null,
        config: withoutLegacyRequirementConfig(imported.config),
        notes: imported.notes || null,
      }, null, canonical?.fields || [], canonical?.documents || [])
      await loadProfiles()
    } catch (err: any) {
      setError(err instanceof SyntaxError ? t('admin.candidate_profiles_page.errors.import_json') : err?.message || t('admin.candidate_profiles_page.errors.import'))
      throw err
    }
  }

  const visibleProfiles = useMemo(() => profiles.filter((profile) => {
    const query = searchQuery.toLowerCase()
    if (query && !profile.name.toLowerCase().includes(query) && !profile.code.toLowerCase().includes(query) && !profile.description?.toLowerCase().includes(query)) return false
    if (filterActive !== null && profile.is_active !== filterActive) return false
    return true
  }).sort((a, b) => {
    let comparison = 0
    if (sortBy === 'name') comparison = a.name.localeCompare(b.name)
    if (sortBy === 'code') comparison = a.code.localeCompare(b.code)
    if (sortBy === 'created_at') comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    if (sortBy === 'fields_count') comparison = (publications[a.code]?.fields.filter((field) => field.requirement_level !== 'hidden').length || 0) - (publications[b.code]?.fields.filter((field) => field.requirement_level !== 'hidden').length || 0)
    if (sortBy === 'stages_count') comparison = Number(Boolean(a.funnel_id)) - Number(Boolean(b.funnel_id))
    if (sortBy === 'usage_count') comparison = (a.usage_count || 0) - (b.usage_count || 0)
    return sortOrder === 'asc' ? comparison : -comparison
  }), [filterActive, profiles, publications, searchQuery, sortBy, sortOrder])

  const errorBanner = useMemo<FriendlyErrorInfo | null>(() => error ? { title: error, hint: t('app.common.retry_hint') } : null, [error, t])

  return (
    <SettingsSubpageHeader className="mb-2" backLabel={t('admin.settings.subpage.back_all')} kicker={t('admin.candidate_profiles_page.header_kicker')} title={t('admin.candidate_profiles_page.title')} subtitle={t('admin.candidate_profiles_page.subtitle')}>
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950" role="status">
        Recruitment requirements are authored from the canonical Field and Document Type registries.
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2 rounded-lg border border-slate-200 bg-white p-4">
        <button className="btn-secondary btn-sm" type="button" onClick={async () => { const { updated } = await fixOrphanedVacancies(); if (updated) await loadProfiles() }}>{t('admin.candidate_profiles_page.fix_orphan_vacancies')}</button>
        <button className="btn-secondary" type="button" onClick={() => setImportMode(true)}>{t('admin.candidate_profiles_page.import')}</button>
        <button className="btn-secondary" type="button" onClick={() => setBulkUpdateMode(true)}>{t('admin.candidate_profiles_page.bulk_update')}</button>
        <button className="btn-primary" type="button" onClick={() => { setNewProfileMode(true); setEditingProfile(null) }}>{t('admin.candidate_profiles_page.create_profile')}</button>
      </div>

      {!newProfileMode && !editingProfile && profiles.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex gap-3">
            <input className="input flex-1" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder={t('admin.candidate_profiles_page.search_placeholder')} />
            <select className="input" value={filterActive === null ? 'all' : filterActive ? 'active' : 'inactive'} onChange={(event) => setFilterActive(event.target.value === 'all' ? null : event.target.value === 'active')}>
              <option value="all">{t('admin.candidate_profiles_page.filter_all')}</option><option value="active">{t('admin.candidate_profiles_page.filter_active')}</option><option value="inactive">{t('admin.candidate_profiles_page.filter_inactive')}</option>
            </select>
            <select className="input" value={sortBy} onChange={(event) => setSortBy(event.target.value as typeof sortBy)}>
              <option value="name">{t('admin.candidate_profiles_page.sort_name')}</option><option value="code">{t('admin.candidate_profiles_page.sort_code')}</option><option value="created_at">{t('admin.candidate_profiles_page.sort_created')}</option><option value="fields_count">{t('admin.candidate_profiles_page.sort_fields')}</option><option value="stages_count">{t('admin.candidate_profiles_page.sort_stages')}</option><option value="usage_count">{t('admin.candidate_profiles_page.sort_usage')}</option>
            </select>
            <button type="button" className="btn-secondary btn-sm" onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}>{sortOrder === 'asc' ? '↑' : '↓'}</button>
          </div>
        </div>
      )}

      {errorBanner && <ErrorRecoveryBanner info={errorBanner} onRetry={() => void loadProfiles()} retryLabel={t('common.actions.refresh')} {...friendlyErrorBannerSecondary(errorBanner, CRM_APP_PATHS.settingsCandidateProfiles, t('common.navigation.settings'))} compact />}

      {loading ? <div className="text-sm text-slate-500">{t('admin.candidate_profiles_page.loading_list')}</div> : (
        <div className="space-y-4">
          {newProfileMode && <ProfileForm onSave={handleCreate} onCancel={() => setNewProfileMode(false)} t={t} profiles={profiles} />}
          {editingProfile && <ProfileForm profile={editingProfile} publication={publications[editingProfile.code]} onSave={(submission) => handleUpdate(editingProfile, submission)} onCancel={() => setEditingProfile(null)} t={t} profiles={profiles} />}
          {!newProfileMode && !editingProfile && (visibleProfiles.length === 0 ? <p className="text-sm text-slate-500">{t('admin.candidate_profiles_page.empty_filtered')}</p> : (
            <div className="space-y-3">{visibleProfiles.map((profile) => {
              const publication = publications[profile.code]
              const fieldCount = publication?.fields.filter((field) => field.requirement_level !== 'hidden').length || 0
              const requiredCount = publication?.fields.filter((field) => field.requirement_level === 'required').length || 0
              const documentCount = publication?.documents.filter((document) => document.requirement_level !== 'hidden').length || 0
              return (
                <div key={profile.id} className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2"><span className="font-medium text-slate-900">{profile.name}</span><span className="rounded-lg bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-600">{profile.code}</span>{profile.is_system && <span className="rounded-lg bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">{t('admin.candidate_profiles_page.badge_system')}</span>}</div>
                      {profile.description && <p className="text-sm text-slate-600">{profile.description}</p>}
                      <div className="flex gap-3 text-xs text-slate-500"><span>{t('admin.candidate_profiles_page.stats_fields', { values: { count: fieldCount } })}{requiredCount > 0 && ` (${requiredCount} required)`}</span><span>{t('admin.candidate_profiles_page.stats_documents', { values: { count: documentCount } })}</span></div>
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <button className="btn-secondary btn-sm" type="button" onClick={() => setPreviewProfile(profile)}>{t('admin.candidate_profiles_page.action_preview')}</button>
                      <button className="btn-secondary btn-sm" type="button" onClick={() => setUsageStatsProfile(profile)}>{t('admin.candidate_profiles_page.action_stats')}</button>
                      <button className="btn-secondary btn-sm" type="button" onClick={() => setHistoryProfile(profile)}>{t('admin.candidate_profiles_page.action_history')}</button>
                      {!profile.is_system && <button className="btn-secondary btn-sm" type="button" onClick={() => setApplyToVacanciesMode(profile)}>{t('admin.candidate_profiles_page.action_apply_vacancies')}</button>}
                      {!profile.is_system && <button className="btn-secondary btn-sm" type="button" onClick={() => handleExport(profile)}>{t('admin.candidate_profiles_page.action_export')}</button>}
                      <button className="btn-secondary btn-sm" type="button" onClick={() => void handleDuplicate(profile)}>{t('admin.candidate_profiles_page.action_duplicate')}</button>
                      {!profile.is_system && <button className="btn-secondary btn-sm" type="button" onClick={() => setEditingProfile(profile)}>{t('admin.candidate_profiles_page.action_edit')}</button>}
                      {!profile.is_system && <button className="btn-danger btn-sm" type="button" onClick={() => void handleDelete(profile.id)} disabled={(profile.usage_count || 0) > 0}>{t('admin.candidate_profiles_page.action_delete')}</button>}
                    </div>
                  </div>
                </div>
              )
            })}</div>
          ))}
        </div>
      )}

      {previewProfile && <ProfilePreviewModal profile={previewProfile} publication={publications[previewProfile.code] || null} onClose={() => setPreviewProfile(null)} onDuplicate={() => { setPreviewProfile(null); void handleDuplicate(previewProfile) }} onExport={() => handleExport(previewProfile)} />}
      {importMode && <ImportProfileModal onClose={() => setImportMode(false)} onImport={async (file) => { await handleImport(file); setImportMode(false) }} />}
      {applyToVacanciesMode && <ApplyProfileToVacanciesModal profile={applyToVacanciesMode} onClose={() => setApplyToVacanciesMode(null)} onSuccess={() => void loadProfiles()} />}
      {bulkUpdateMode && <BulkUpdateProfilesModal onClose={() => setBulkUpdateMode(false)} onSuccess={() => void loadProfiles()} />}
      {usageStatsProfile && <ProfileUsageStatsModal profile={usageStatsProfile} publication={publications[usageStatsProfile.code] || null} onClose={() => setUsageStatsProfile(null)} />}
      {historyProfile && <ProfileHistoryModal profile={historyProfile} onClose={() => setHistoryProfile(null)} />}
    </SettingsSubpageHeader>
  )
}

function ProfileForm({ profile, publication, onSave, onCancel, t, profiles }: {
  profile?: CandidateProfile | null
  publication?: RecruitmentProfilePublication | null
  onSave: (payload: ProfileSubmission) => Promise<void>
  onCancel: () => void
  t: Translator
  profiles?: CandidateProfile[]
}) {
  const [code, setCode] = useState(profile?.code || '')
  const [name, setName] = useState(profile?.name || publication?.name || '')
  const [description, setDescription] = useState(profile?.description || publication?.description || '')
  const [notes, setNotes] = useState(profile?.notes || '')
  const [fieldBindings, setFieldBindings] = useState<RecruitmentProfileFieldBinding[]>(publication?.fields || [])
  const [documentBindings, setDocumentBindings] = useState<RecruitmentProfileDocumentBinding[]>(publication?.documents || [])
  const [fieldCatalog, setFieldCatalog] = useState<CanonicalField[]>([])
  const [documentCatalog, setDocumentCatalog] = useState<CurrentDocumentTypeVersion[]>([])
  const [funnelId, setFunnelId] = useState<string | null>(profile?.funnel_id ?? null)
  const [saving, setSaving] = useState(false)
  const [loadingCatalogs, setLoadingCatalogs] = useState(true)
  const [formError, setFormError] = useState<string | null>(null)
  const [codeError, setCodeError] = useState<string | null>(null)
  const [nameError, setNameError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    Promise.all([
      listCanonicalFields({ entity_type: 'candidate', module: 'recruitment' }),
      listCurrentDocumentTypeVersions(),
    ]).then(([fields, documents]) => {
      if (!active) return
      setFieldCatalog(fields.items)
      setDocumentCatalog(documents)
    }).catch((err: any) => {
      if (active) setFormError(err?.message || 'Failed to load canonical catalogs.')
    }).finally(() => { if (active) setLoadingCatalogs(false) })
    return () => { active = false }
  }, [])

  const handleSubmit = async () => {
    setCodeError(null); setNameError(null); setFormError(null)
    const normalizedCode = code.trim().toLowerCase()
    if (!normalizedCode || !/^[a-z0-9_]+$/.test(normalizedCode)) {
      setCodeError(t('admin.candidate_profiles_page.validation.code_inline_format')); return
    }
    if (!profile && profiles?.some((item) => item.code === normalizedCode)) {
      setCodeError(t('admin.candidate_profiles_page.validation.code_inline_taken', { values: { code: normalizedCode } })); return
    }
    if (!name.trim()) { setNameError(t('admin.candidate_profiles_page.validation.name_inline_required')); return }

    const fields = completeFieldBindings(fieldCatalog, fieldBindings)
    const documents = completeDocumentBindings(documentCatalog, documentBindings)
    if (!fields.some((field) => field.requirement_level !== 'hidden') || !documents.some((document) => document.requirement_level !== 'hidden')) {
      if (!window.confirm(`${t('admin.candidate_profiles_page.warnings.save_prompt_title')}\n\n${t('admin.candidate_profiles_page.warnings.save_prompt_footer')}`)) return
    }

    setSaving(true)
    try {
      await onSave({
        shell: {
          code: normalizedCode,
          name: name.trim(),
          description: description || null,
          client_id: profile?.client_id || null,
          notes: notes || null,
          funnel_id: funnelId,
          config: withoutLegacyRequirementConfig(profile?.config),
        },
        recruitment: {
          name: name.trim(),
          description: description || null,
          default_layout_code: publication?.default_layout_code || null,
          config: canonicalConfig(normalizedCode, publication),
          fields,
          documents,
        },
      })
    } catch (err: any) {
      setFormError(err?.message || (profile ? t('admin.candidate_profiles_page.errors.update') : t('admin.candidate_profiles_page.errors.create')))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <h3 className="mb-3 text-base font-semibold text-blue-800">{profile ? t('admin.candidate_profiles_page.form.title_edit') : t('admin.candidate_profiles_page.form.title_create')}</h3>
      <div className="space-y-3">
        <TextField label={t('admin.candidate_profiles_page.form.code')} value={code} onChange={setCode} disabled={Boolean(profile) || saving} placeholder={t('admin.candidate_profiles_page.form.code_placeholder')} className={codeError ? 'border-rose-300' : ''} />
        {codeError && <div className="text-xs text-rose-600">{codeError}</div>}
        <TextField label={t('admin.candidate_profiles_page.form.name')} value={name} onChange={setName} disabled={saving} placeholder={t('admin.candidate_profiles_page.form.name_placeholder')} className={nameError ? 'border-rose-300' : ''} />
        {nameError && <div className="text-xs text-rose-600">{nameError}</div>}
        <TextareaField label={t('admin.candidate_profiles_page.form.description')} value={description} onChange={setDescription} placeholder={t('admin.candidate_profiles_page.form.description_placeholder')} />
        <TextareaField label={t('admin.candidate_profiles_page.form.notes')} value={notes} onChange={setNotes} rows={2} placeholder={t('admin.candidate_profiles_page.form.notes_placeholder')} />
        <div className="mt-4"><h3 className="mb-3 text-base font-semibold text-slate-900">{t('admin.candidate_profiles_page.form.section_fields')}</h3>{loadingCatalogs ? <div className="text-sm text-slate-500">{t('common.loading')}</div> : <ProfileFieldConstructor catalog={fieldCatalog} value={fieldBindings} onChange={setFieldBindings} disabled={saving} />}</div>
        <div className="mt-6"><h3 className="mb-3 text-base font-semibold text-slate-900">{t('admin.candidate_profiles_page.form.section_funnel')}</h3><FunnelSelector companyId={profile?.client_id} value={funnelId} onChange={setFunnelId} disabled={saving || Boolean(profile?.is_system)} /></div>
        <div className="mt-6"><h3 className="mb-3 text-base font-semibold text-slate-900">{t('admin.candidate_profiles_page.form.section_documents')}</h3>{loadingCatalogs ? <div className="text-sm text-slate-500">{t('common.loading')}</div> : <ProfileDocumentConstructor catalog={documentCatalog} value={documentBindings} onChange={setDocumentBindings} disabled={saving} />}</div>
        {formError && <div className="text-sm text-rose-700">{formError}</div>}
        <div className="flex justify-end gap-2"><button className="btn-secondary" type="button" onClick={onCancel} disabled={saving}>{t('admin.candidate_profiles_page.form.cancel')}</button><button className="btn-primary" type="button" onClick={() => void handleSubmit()} disabled={saving || loadingCatalogs}>{saving ? t('admin.candidate_profiles_page.form.saving') : t('admin.candidate_profiles_page.form.save')}</button></div>
      </div>
    </div>
  )
}
