import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  createMetaAdsMap,
  createMetaLeadCredential,
  deleteMetaAdsMap,
  deleteMetaLeadCredential,
  getMetaLeadSettings,
  getUnmappedLeads,
  listMetaAdsMap,
  listMetaLeadCredentials,
  rerouteMetaLead,
  retryLeads,
  rotateMetaLeadCredential,
  updateMetaAdsMap,
  updateMetaLeadSettings,
} from '../../api/metaLeads'
import type { UnmappedAdGroup } from '../../api/metaLeads'
import { listCompanies, listLeads, listVacancies } from '../../api/client'
import { listAdminUsers } from '../../api/users'
import type {
  Lead,
  MetaAdsMapEntry,
  MetaCredentialCreatePayload,
  MetaLeadCredential,
  MetaLeadFieldMappingRule,
  MetaLeadSettings,
  MetaLeadSettingsPatch,
} from '../../api/types'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

type TabKey = 'settings' | 'credentials' | 'mapping' | 'logs'

interface CredentialFormState {
  label: string
  secret: string
  status: 'active' | 'disabled' | 'rotation_pending'
  adAccountId: string
  pageId: string
  accessToken: string
}

interface MappingFormState {
  adId: string
  vacancyId: string
  note: string
}

const DEFAULT_CREDENTIAL_FORM: CredentialFormState = {
  label: '',
  secret: '',
  status: 'active',
  adAccountId: '',
  pageId: '',
  accessToken: '',
}

const DEFAULT_MAPPING_FORM: MappingFormState = {
  adId: '',
  vacancyId: '',
  note: '',
}

const formatDateTime = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return String(value)
  return date.toLocaleString()
}

export default function MetaLeadsAdminPage() {
  const { t } = useI18n()
  const [tab, setTab] = useState<TabKey>('settings')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [settings, setSettings] = useState<MetaLeadSettings | null>(null)
  const [credentials, setCredentials] = useState<MetaLeadCredential[]>([])
  const [mapping, setMapping] = useState<MetaAdsMapEntry[]>([])
  const [leads, setLeads] = useState<Lead[]>([])
  const [unmappedGroups, setUnmappedGroups] = useState<UnmappedAdGroup[]>([])
  const [vacancyOptions, setVacancyOptions] = useState<Array<{ id: string; title: string }>>([])
  const [companyOptions, setCompanyOptions] = useState<Array<{ id: string; name: string }>>([])
  const [recruiterOptions, setRecruiterOptions] = useState<Array<{ id: string; name: string }>>([])

  const [settingsDraft, setSettingsDraft] = useState<MetaLeadSettingsPatch>({})
  const [fieldMappingText, setFieldMappingText] = useState('[]')
  const [credentialForm, setCredentialForm] = useState<CredentialFormState>(DEFAULT_CREDENTIAL_FORM)
  const [mappingForm, setMappingForm] = useState<MappingFormState>(DEFAULT_MAPPING_FORM)
  const [mappingSearch, setMappingSearch] = useState('')
  const [attachModal, setAttachModal] = useState<{ group: UnmappedAdGroup; vacancyId: string } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const selectedCompanyId = settingsDraft.default_company_id ?? settings?.default_company_id ?? null
  const selectedCompanyName = useMemo(() => {
    if (!selectedCompanyId) return null
    return companyOptions.find((option) => option.id === selectedCompanyId)?.name ?? null
  }, [companyOptions, selectedCompanyId])

  const selectedRecruiterId = settingsDraft.fallback_recruiter_id ?? settings?.fallback_recruiter_id ?? null
  const selectedRecruiterName = useMemo(() => {
    if (!selectedRecruiterId) return null
    return recruiterOptions.find((option) => option.id === selectedRecruiterId)?.name ?? null
  }, [recruiterOptions, selectedRecruiterId])

  const refreshAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [settingsData, credsData, mapData, leadsResp, unmappedResp, companiesResp, vacanciesResp, adminUsers] = await Promise.all([
        getMetaLeadSettings(),
        listMetaLeadCredentials(),
        listMetaAdsMap({ limit: 200 }),
        listLeads({ status: 'needs_routing', limit: 100, offset: 0 }),
        getUnmappedLeads({ status: 'needs_routing', limit_per_ad: 5 }).catch(() => ({ groups: [] })),
        listCompanies({ limit: 200 }),
        listVacancies({ limit: 200 }).catch(() => ({ items: [] })),
        listAdminUsers(),
      ])
      setSettings(settingsData)
      setSettingsDraft({})
      setFieldMappingText(JSON.stringify(settingsData?.field_mapping ?? [], null, 2))
      setCredentials(credsData)
      setMapping(mapData)
      setLeads(Array.isArray(leadsResp.items) ? leadsResp.items : [])
      setUnmappedGroups(unmappedResp.groups || [])
      const vacList: any[] = Array.isArray(vacanciesResp?.items) ? vacanciesResp.items : Array.isArray(vacanciesResp) ? vacanciesResp : []
      setVacancyOptions(vacList.map((v: any) => ({ id: v?.id, title: v?.title || v?.vacancy_title || t('common.labels.unnamed') })).filter((v: any) => v.id))

      const companiesList: any[] = Array.isArray(companiesResp?.items)
        ? companiesResp.items
        : Array.isArray(companiesResp)
          ? companiesResp
          : []
      const companyOpts = companiesList
        .map((item) => ({
          id: item?.id,
          name: item?.name || item?.legal_name || item?.display_name || t('common.labels.unnamed'),
        }))
        .filter((opt) => typeof opt.id === 'string' && opt.id.length > 0)

      const currentCompanyId = settingsData?.default_company_id ?? null
      if (currentCompanyId && !companyOpts.some((opt) => opt.id === currentCompanyId)) {
        companyOpts.push({ id: currentCompanyId, name: t('app.admin.meta_leads.placeholders.selected_company') })
      }
      setCompanyOptions(companyOpts)

      const recruiterOpts = adminUsers
        .filter((user) => user.role === 'recruiter')
        .map((user) => ({
          id: user.user_id || (user as any).id || user.email || '',
          name: user.full_name || user.email || user.short_id || t('app.admin.meta_leads.placeholders.recruiter_fallback'),
        }))
        .filter((opt) => typeof opt.id === 'string' && opt.id.length > 0)

      const currentRecruiterId = settingsData?.fallback_recruiter_id ?? null
      if (currentRecruiterId && !recruiterOpts.some((opt) => opt.id === currentRecruiterId)) {
        const fallbackUser = adminUsers.find(
          (user) => (user.user_id || (user as any).id) === currentRecruiterId,
        )
        recruiterOpts.push({
          id: currentRecruiterId,
          name: fallbackUser?.full_name || fallbackUser?.email || fallbackUser?.short_id || t('app.admin.meta_leads.placeholders.selected_recruiter'),
        })
      }
      setRecruiterOptions(recruiterOpts)
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] refresh failed', err)
      setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.load')))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void refreshAll()
  }, [refreshAll])

  const handleSettingsChange = useCallback(<K extends keyof MetaLeadSettingsPatch>(key: K, value: MetaLeadSettingsPatch[K]) => {
    setSettingsDraft((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleSettingsSubmit = useCallback(async () => {
    try {
      const payload: MetaLeadSettingsPatch = { ...settingsDraft }
      const parsedFieldMapping = JSON.parse((fieldMappingText || '[]').trim() || '[]')
      if (!Array.isArray(parsedFieldMapping)) {
        setError({
          title: t('app.admin.meta_leads.errors.settings_update', { defaultValue: 'Field mapping must be an array' }),
          hint: t('app.admin.meta_leads.errors.settings_update', { defaultValue: 'Fix field mapping and retry.' }),
        })
        return
      }
      payload.field_mapping = parsedFieldMapping as MetaLeadFieldMappingRule[]
      const result = await updateMetaLeadSettings(payload)
      setSettings(result)
      setSettingsDraft({})
      setFieldMappingText(JSON.stringify(result?.field_mapping ?? [], null, 2))
      setNotice(t('app.admin.meta_leads.notices.settings_saved'))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] update settings failed', err)
      if (err instanceof SyntaxError) {
        setError({
          title: t('app.admin.meta_leads.errors.settings_update', { defaultValue: 'Field mapping JSON is invalid' }),
          hint: t('app.admin.meta_leads.errors.settings_update', { defaultValue: 'Fix JSON syntax and retry.' }),
        })
      } else {
        setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.settings_update')))
      }
    }
  }, [fieldMappingText, settingsDraft, t])

  const handleCredentialCreate = useCallback(async () => {
    const payload: MetaCredentialCreatePayload = {
      label: credentialForm.label.trim(),
      status: credentialForm.status,
      secret: credentialForm.secret ? credentialForm.secret.trim() : undefined,
      ad_account_id: credentialForm.adAccountId ? credentialForm.adAccountId.trim() : undefined,
      page_id: credentialForm.pageId ? credentialForm.pageId.trim() : undefined,
      access_token: credentialForm.accessToken ? credentialForm.accessToken.trim() : undefined,
    }
    if (!payload.label) {
      setError({
        title: t('app.admin.meta_leads.errors.credential_label'),
        hint: t('app.admin.meta_leads.errors.credential_label', { defaultValue: 'Fill required fields and retry.' }),
      })
      return
    }
    try {
      const entry = await createMetaLeadCredential(payload)
      setCredentials((prev) => [entry, ...prev])
      setCredentialForm(DEFAULT_CREDENTIAL_FORM)
      setNotice(t('app.admin.meta_leads.notices.credential_created'))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] create credential failed', err)
      setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.credential_create')))
    }
  }, [credentialForm, t])

  const handleCredentialRotate = useCallback(async (id: string) => {
    try {
      const { secret } = await rotateMetaLeadCredential(id)
      setNotice(t('app.admin.meta_leads.notices.secret_rotated', { values: { secret } }))
      const updated = await listMetaLeadCredentials()
      setCredentials(updated)
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] rotate credential failed', err)
      setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.secret_rotate')))
    }
  }, [t])

  const handleCredentialDelete = useCallback(async (id: string) => {
    if (!window.confirm(t('app.admin.meta_leads.prompts.delete_credential'))) return
    try {
      await deleteMetaLeadCredential(id)
      setCredentials((prev) => prev.filter((item) => item.id !== id))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] delete credential failed', err)
      setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.credential_delete')))
    }
  }, [t])

  const handleMappingCreate = useCallback(async () => {
    const adIdRaw = mappingForm.adId.trim()
    const vacancyIdRaw = mappingForm.vacancyId.trim()
    if (!adIdRaw || !vacancyIdRaw) {
      setError({
        title: t('app.admin.meta_leads.errors.mapping_required'),
        hint: t('app.admin.meta_leads.errors.mapping_required', { defaultValue: 'Fill required fields and retry.' }),
      })
      return
    }
    if (!/^\d+$/.test(adIdRaw)) {
      setError({
        title: t('app.admin.meta_leads.errors.mapping_ad_id'),
        hint: t('app.admin.meta_leads.errors.mapping_ad_id', { defaultValue: 'Use numeric ad id and retry.' }),
      })
      return
    }
    try {
      setError(null)
      const entry = await createMetaAdsMap({
        ad_id: adIdRaw,
        vacancy_id: vacancyIdRaw as any,
        note: mappingForm.note.trim() ? mappingForm.note.trim() : undefined,
      })
      setMapping((prev) => [entry, ...prev.filter((item) => item.ad_id !== entry.ad_id)])
      setMappingForm(DEFAULT_MAPPING_FORM)
      setNotice(t('app.admin.meta_leads.notices.mapping_saved'))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] create mapping failed', err)
      setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.mapping_create')))
    }
  }, [mappingForm, t])

  const handleMappingDelete = useCallback(async (adId: string) => {
    if (!window.confirm(t('app.admin.meta_leads.prompts.delete_mapping', { values: { adId } }))) return
    try {
      await deleteMetaAdsMap(adId)
      setMapping((prev) => prev.filter((item) => item.ad_id !== adId))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] delete mapping failed', err)
      setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.mapping_delete')))
    }
  }, [])

  const handleAttachUnmapped = useCallback(async () => {
    if (!attachModal || !attachModal.vacancyId.trim()) return
    const { group } = attachModal
    setSubmitting(true)
    try {
      await createMetaAdsMap({
        ad_id: group.ad_id,
        vacancy_id: attachModal.vacancyId as any,
      })
      for (const lead of group.leads) {
        await rerouteMetaLead(lead.id as string, {
          vacancy_id: attachModal.vacancyId as any,
          force_process: true,
        })
      }
      setAttachModal(null)
      setNotice(t('app.admin.meta_leads.notices.unmapped_attached', { defaultValue: 'Лиды привязаны к вакансии' }))
      await refreshAll()
    } catch (err: any) {
      setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.reroute')))
    } finally {
      setSubmitting(false)
    }
  }, [attachModal, t, refreshAll])

  const handleReroute = useCallback(async (lead: Lead) => {
    const vacancyDefault = lead.vacancy_id ?? ''
    const vacancyId = window.prompt(
      t('app.admin.meta_leads.prompts.reroute_vacancy', { defaultValue: 'Enter vacancy_id (or leave empty to create candidate with company only)' }),
      vacancyDefault || ''
    )
    if (vacancyId === null) return
    const payload: { vacancy_id?: string; company_id?: string; force_process: boolean } = { force_process: true }
    if (vacancyId?.trim()) payload.vacancy_id = vacancyId.trim() as any
    if (lead.company_id) payload.company_id = lead.company_id as any
    try {
      await rerouteMetaLead(lead.id, payload)
      setNotice(t('app.admin.meta_leads.notices.lead_rerouted'))
      const refreshed = await listLeads({ status: 'needs_routing', limit: 100, offset: 0 })
      setLeads(Array.isArray(refreshed.items) ? refreshed.items : [])
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] reroute failed', err)
      setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.reroute')))
    }
  }, [t])

  const handleRetry = useCallback(async (lead: Lead) => {
    try {
      const result = await retryLeads({ lead_ids: [String(lead.id)], refresh_graph: true })
      const item = result.items[0]
      if (item?.processed) {
        setNotice(t('app.admin.meta_leads.notices.lead_retried', { defaultValue: 'Лид успешно обработан' }))
      } else if (item?.message) {
        setError({
          title: item.message,
          hint: t('app.admin.meta_leads.errors.retry', { defaultValue: 'Retry failed. Check mapping and try again.' }),
        })
      }
      const refreshed = await listLeads({ status: 'needs_routing', limit: 100, offset: 0 })
      setLeads(Array.isArray(refreshed.items) ? refreshed.items : [])
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] retry failed', err)
      setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.retry', { defaultValue: 'Retry failed' })))
    }
  }, [t])

  useEffect(() => {
    if (notice) {
      const timer = setTimeout(() => setNotice(null), 4000)
      return () => clearTimeout(timer)
    }
    return undefined
  }, [notice])

  const filteredMapping = useMemo(() => {
    if (!mappingSearch.trim()) return mapping
    const needle = mappingSearch.trim().toLowerCase()
    return mapping.filter((item) => item.ad_id.includes(needle) || (item.note ?? '').toLowerCase().includes(needle))
  }, [mapping, mappingSearch])

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{t('app.admin.meta_leads.title')}</h1>
          <p className="text-sm text-slate-500">{t('app.admin.meta_leads.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void refreshAll()}
            disabled={loading}
            className="btn-secondary btn-sm disabled:opacity-50"
          >
            {loading ? t('common.loading') : t('common.actions.refresh')}
          </button>
        </div>
      </header>

      {credentials.length === 0 && !loading && (
        <div className="rounded border border-brand-200 bg-brand-50 p-4">
          <h3 className="font-semibold text-brand-900">
            {t('app.admin.meta_leads.quick_start.title', { defaultValue: 'Быстрый старт' })}
          </h3>
          <p className="mt-1 text-sm text-brand-800">
            {t('app.admin.meta_leads.quick_start.subtitle', {
              defaultValue: '1) Добавьте Credential (Webhook Secret, Access Token). 2) Настройте маппинг ad_id → вакансия. 3) Проверьте логи входящих лидов.',
            })}
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              className="btn-primary"
              onClick={() => setTab('credentials')}
            >
              {t('app.admin.meta_leads.tabs.credentials')} →
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setTab('mapping')}
            >
              {t('app.admin.meta_leads.tabs.mapping')} →
            </button>
          </div>
        </div>
      )}

      {(error || notice) && (
        <div className="space-y-2">
          {error && (
            <ErrorRecoveryBanner
              info={error}
              onRetry={() => void refreshAll()}
              retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
              secondaryTo="/app/settings/leads"
              secondaryLabel={t('app.admin.meta_leads.title')}
              compact
            />
          )}
          {notice && !error && (
            <div className="alert-success">{notice}</div>
          )}
        </div>
      )}

      <nav className="flex gap-3">
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'settings' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('settings')}
        >
          {t('app.admin.meta_leads.tabs.settings')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'credentials' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('credentials')}
        >
          {t('app.admin.meta_leads.tabs.credentials')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'mapping' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('mapping')}
        >
          {t('app.admin.meta_leads.tabs.mapping')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'logs' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('logs')}
        >
          {t('app.admin.meta_leads.tabs.logs')}
        </button>
        <span className="self-center text-xs text-slate-400">
          {t('app.admin.meta_leads.other_platforms', { defaultValue: 'TikTok, YouTube, Google — скоро' })}
        </span>
      </nav>

      {unmappedGroups.length > 0 && (
        <section className="rounded border border-amber-200 bg-amber-50 p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-amber-900">
            {t('app.admin.meta_leads.unmapped.title', { defaultValue: 'Непривязанные лиды' })}
          </h2>
          <p className="mt-1 text-sm text-amber-800">
            {t('app.admin.meta_leads.unmapped.subtitle', { defaultValue: 'Лиды с ad_id без маппинга на вакансию. Привяжите к вакансии и перезапустите маршрутизацию.' })}
          </p>
          <div className="mt-3 space-y-2">
            {unmappedGroups.map((group) => (
              <div
                key={group.ad_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-amber-200 bg-white px-3 py-2 text-sm"
              >
                <span>
                  ad_id: <strong>{group.ad_id}</strong> — {group.count}{' '}
                  {t('app.admin.meta_leads.unmapped.leads', { defaultValue: 'лидов' })}
                </span>
                <button
                  type="button"
                  className="btn-primary btn-xs"
                  onClick={() => setAttachModal({ group, vacancyId: '' })}
                  disabled={submitting}
                >
                  {t('app.admin.meta_leads.unmapped.attach_btn', { defaultValue: 'Привязать к вакансии' })}
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === 'settings' && (
        <section className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">{t('app.admin.meta_leads.settings.title')}</h2>
          <p className="mt-1 text-sm text-slate-500">{t('app.admin.meta_leads.settings.subtitle')}</p>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={(settingsDraft.auto_create_enabled ?? settings?.auto_create_enabled ?? true)}
                onChange={(event) => handleSettingsChange('auto_create_enabled', event.target.checked)}
              />
              {t('app.admin.meta_leads.settings.auto_create')}
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={(settingsDraft.mask_pii_in_logs ?? settings?.mask_pii_in_logs ?? true)}
                onChange={(event) => handleSettingsChange('mask_pii_in_logs', event.target.checked)}
              />
              {t('app.admin.meta_leads.settings.mask_pii')}
            </label>

            <label className="text-sm text-slate-700">
              {t('app.admin.meta_leads.settings.default_company')}
              <select
                className="input mt-1 w-full"
                value={selectedCompanyId ?? ''}
                onChange={(event) => handleSettingsChange('default_company_id', event.target.value ? event.target.value : null)}
              >
                <option value="">{t('app.admin.meta_leads.placeholders.company_none')}</option>
                {companyOptions.map((company) => (
                  <option key={company.id} value={company.id}>{company.name}</option>
                ))}
              </select>
              {selectedCompanyName && (
                <div className="mt-1 text-xs text-slate-500">{t('app.admin.meta_leads.settings.current_company', { values: { name: selectedCompanyName } })}</div>
              )}
            </label>

            <label className="text-sm text-slate-700">
              {t('app.admin.meta_leads.settings.default_recruiter')}
              <select
                className="input mt-1 w-full"
                value={selectedRecruiterId ?? ''}
                onChange={(event) => handleSettingsChange('fallback_recruiter_id', event.target.value ? event.target.value : null)}
              >
                <option value="">{t('app.admin.meta_leads.placeholders.recruiter_none')}</option>
                {recruiterOptions.map((option) => (
                  <option key={option.id} value={option.id}>{option.name}</option>
                ))}
              </select>
              {selectedRecruiterName && (
                <div className="mt-1 text-xs text-slate-500">{t('app.admin.meta_leads.settings.current_recruiter', { values: { name: selectedRecruiterName } })}</div>
              )}
            </label>

            <label className="text-sm text-slate-700">
              {t('app.admin.meta_leads.settings.sla_label')}
              <input
                type="number"
                min={0}
                className="input mt-1 w-full"
                value={settingsDraft.reroute_after_hours ?? settings?.reroute_after_hours ?? ''}
                onChange={(event) => {
                  const value = event.target.value
                  handleSettingsChange('reroute_after_hours', value === '' ? null : Number(value))
                }}
              />
            </label>

            <label className="text-sm text-slate-700">
              {t('app.admin.meta_leads.settings.webhook_url')}
              <input
                type="text"
                className="input mt-1 w-full"
                value={settingsDraft.webhook_url ?? settings?.webhook_url ?? ''}
                onChange={(event) => handleSettingsChange('webhook_url', event.target.value)}
              />
            </label>
            <label className="text-sm text-slate-700">
              {t('app.admin.meta_leads.settings.webhook_token')}
              <input
                type="text"
                className="input mt-1 w-full"
                value={settingsDraft.webhook_verify_token ?? settings?.webhook_verify_token ?? ''}
                onChange={(event) => handleSettingsChange('webhook_verify_token', event.target.value)}
              />
            </label>

            <label className="text-sm text-slate-700 md:col-span-2">
              {t('app.admin.meta_leads.settings.field_mapping', { defaultValue: 'Field mapping (source → target → format)' })}
              <textarea
                className="textarea mt-1 min-h-[180px] w-full font-mono text-xs"
                value={fieldMappingText}
                onChange={(event) => setFieldMappingText(event.target.value)}
                placeholder='[{"source":"phone_number","target":"phone","format":"phone","overwrite":true}]'
              />
              <div className="mt-1 text-xs text-slate-500">
                {t('app.admin.meta_leads.settings.field_mapping_hint', {
                  defaultValue:
                    'Formats: string, email, phone, bool, int, float, uuid, country, contact_channel, list, csv, lower, upper',
                })}
              </div>
            </label>
          </div>

          <div className="mt-4 flex items-center gap-3 text-sm text-slate-500">
            <div>{t('app.admin.meta_leads.settings.last_signature_check', { values: { date: formatDateTime(settings?.last_webhook_check_at) } })}</div>
            <div>{t('app.admin.meta_leads.settings.signature_status', { values: { status: settings?.last_signature_status ?? '—' } })}</div>
          </div>

          <button
            type="button"
            onClick={handleSettingsSubmit}
            className="btn-primary mt-4"
          >
            {t('app.admin.meta_leads.settings.save')}
          </button>
        </section>
      )}

      {tab === 'credentials' && (
        <section className="space-y-4">
          <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">{t('app.admin.meta_leads.credentials.title')}</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <label className="text-sm text-slate-700">
                {t('app.admin.meta_leads.credentials.label')}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.label}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, label: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('app.admin.meta_leads.credentials.status')}
                <select
                  className="input mt-1 w-full"
                  value={credentialForm.status}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, status: event.target.value as CredentialFormState['status'] }))}
                >
                  <option value="active">active</option>
                  <option value="disabled">disabled</option>
                  <option value="rotation_pending">rotation_pending</option>
                </select>
              </label>
              <label className="text-sm text-slate-700">
                {t('app.admin.meta_leads.credentials.webhook_secret')}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.secret}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, secret: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('app.admin.meta_leads.credentials.access_token')}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.accessToken}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, accessToken: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                ad_account_id
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.adAccountId}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, adAccountId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                page_id
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.pageId}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, pageId: event.target.value }))}
                />
              </label>
            </div>
            <button
              type="button"
              className="btn-primary mt-4"
              onClick={handleCredentialCreate}
            >
              {t('common.actions.save')}
            </button>
          </div>

          <div className="rounded border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.credentials.table.label')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.credentials.table.status')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">ad_id</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">page_id</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.credentials.table.signature')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('common.labels.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {loading && credentials.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-4 text-center text-slate-500">{t('common.loading')}</td>
                  </tr>
                )}
                {!loading && credentials.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-4 text-center text-slate-500">{t('app.admin.meta_leads.credentials.empty')}</td>
                  </tr>
                )}
                {credentials.map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-4 py-2 text-slate-900">{entry.label}</td>
                    <td className="px-4 py-2 text-slate-600">{entry.status}</td>
                    <td className="px-4 py-2 text-slate-600">{entry.ad_account_last4 ?? '—'}</td>
                    <td className="px-4 py-2 text-slate-600">{entry.page_id_masked ?? '—'}</td>
                    <td className="px-4 py-2 text-slate-600">{formatDateTime(entry.last_verified_at)}</td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="btn-secondary btn-xs"
                          onClick={() => void handleCredentialRotate(entry.id)}
                        >
                          {t('app.admin.meta_leads.credentials.actions.rotate')}
                        </button>
                        <button
                          type="button"
                          className="btn-danger btn-xs"
                          onClick={() => void handleCredentialDelete(entry.id)}
                        >
                          {t('common.actions.delete')}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === 'mapping' && (
        <section className="space-y-4">
          <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">{t('app.admin.meta_leads.mapping.title')}</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <label className="text-sm text-slate-700">
                ad_id
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={mappingForm.adId}
                  onChange={(event) => setMappingForm((prev) => ({ ...prev, adId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                vacancy_id
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={mappingForm.vacancyId}
                  onChange={(event) => setMappingForm((prev) => ({ ...prev, vacancyId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('app.admin.meta_leads.mapping.note')}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={mappingForm.note}
                  onChange={(event) => setMappingForm((prev) => ({ ...prev, note: event.target.value }))}
                />
              </label>
            </div>
            <button
              type="button"
              className="btn-primary mt-4"
              onClick={handleMappingCreate}
            >
              {t('app.admin.meta_leads.mapping.save')}
            </button>
          </div>

          <div className="flex items-center justify-between gap-4">
            <input
              type="text"
              placeholder={t('app.admin.meta_leads.mapping.search_placeholder')}
              value={mappingSearch}
              onChange={(event) => setMappingSearch(event.target.value)}
              className="input w-full"
            />
          </div>

          <div className="rounded border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">ad_id</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">vacancy_id</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.mapping.note')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.mapping.created')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('common.labels.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {loading && filteredMapping.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-4 text-center text-slate-500">{t('common.loading')}</td>
                  </tr>
                )}
                {!loading && filteredMapping.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-4 text-center text-slate-500">{t('app.admin.meta_leads.mapping.empty')}</td>
                  </tr>
                )}
                {filteredMapping.map((entry) => (
                  <tr key={entry.ad_id}>
                    <td className="px-4 py-2 text-slate-900">{entry.ad_id}</td>
                    <td className="px-4 py-2 text-slate-600">{entry.vacancy_id}</td>
                    <td className="px-4 py-2 text-slate-600">{entry.note ?? '—'}</td>
                    <td className="px-4 py-2 text-slate-500">{entry.created_at}</td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="btn-secondary btn-xs"
                          onClick={async () => {
                            const note = window.prompt(t('app.admin.meta_leads.prompts.edit_note'), entry.note ?? '') ?? undefined
                            const vacancy = window.prompt(t('app.admin.meta_leads.prompts.edit_vacancy'), entry.vacancy_id) ?? undefined
                            if (!vacancy) return
                            try {
                              const updated = await updateMetaAdsMap(entry.ad_id, {
                                note: note || undefined,
                                vacancy_id: vacancy as any,
                              })
                              setMapping((prev) => prev.map((item) => (item.ad_id === updated.ad_id ? updated : item)))
                            } catch (err: any) {
                              console.error('[MetaLeadsAdmin] update mapping failed', err)
                              setError(getFriendlyErrorInfo(err, t('app.admin.meta_leads.errors.mapping_update')))
                            }
                          }}
                        >
                          {t('common.actions.edit')}
                        </button>
                        <button
                          type="button"
                          className="btn-danger btn-xs"
                          onClick={() => void handleMappingDelete(entry.ad_id)}
                        >
                          {t('common.actions.delete')}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === 'logs' && (
        <section className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">{t('app.admin.meta_leads.logs.title')}</h2>
          <p className="mt-1 text-sm text-slate-500">{t('app.admin.meta_leads.logs.subtitle')}</p>

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.logs.table.created')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.logs.table.status')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.logs.table.company')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.logs.table.vacancy')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.logs.table.contacts')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('app.admin.meta_leads.logs.table.error')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('common.labels.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {loading && leads.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-4 text-center text-slate-500">{t('common.loading')}</td>
                  </tr>
                )}
                {!loading && leads.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-4 text-center text-slate-500">{t('app.admin.meta_leads.logs.empty')}</td>
                  </tr>
                )}
                {leads.map((lead) => {
                  const normalized = lead.normalized || {}
                  const contactName = normalized.full_name || `${normalized.first_name || ''} ${normalized.last_name || ''}`.trim()
                  const contactEmail = normalized.email
                  const contactPhone = normalized.phone
                  const contact = [contactName, contactEmail, contactPhone].filter(Boolean).join(' · ')
                  return (
                    <tr key={lead.id}>
                      <td className="px-4 py-2 text-slate-600">{formatDateTime(lead.created_at)}</td>
                      <td className="px-4 py-2 text-slate-700">{lead.status}</td>
                      <td className="px-4 py-2 text-slate-700">{lead.company_name ?? lead.company_id}</td>
                      <td className="px-4 py-2 text-slate-700">{lead.vacancy_title ?? lead.vacancy_id ?? '—'}</td>
                      <td className="px-4 py-2 text-slate-600">{contact || '—'}</td>
                      <td className="px-4 py-2 text-red-500">{lead.error ?? '—'}</td>
                      <td className="px-4 py-2">
                        <div className="flex gap-2">
                          <button
                            type="button"
                            className="btn-secondary btn-xs"
                            onClick={() => void handleRetry(lead)}
                          >
                            {t('app.admin.meta_leads.logs.actions.retry', { defaultValue: 'Retry' })}
                          </button>
                          <button
                            type="button"
                            className="btn-secondary btn-xs"
                            onClick={() => void handleReroute(lead)}
                          >
                            {t('app.admin.meta_leads.logs.actions.reroute')}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {attachModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => !submitting && setAttachModal(null)}
        >
          <div
            className="rounded border border-slate-200 bg-white p-6 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-slate-900">
              {t('app.admin.meta_leads.unmapped.attach_modal_title', {
                defaultValue: 'Привязать ad_id {adId} к вакансии',
                values: { adId: attachModal.group.ad_id },
              })}
            </h3>
            <label className="mt-3 block text-sm text-slate-700">
              {t('app.admin.meta_leads.unmapped.select_vacancy', { defaultValue: 'Вакансия' })}
              <select
                className="input mt-1 w-full"
                value={attachModal.vacancyId}
                onChange={(e) => setAttachModal((prev) => prev && { ...prev, vacancyId: e.target.value })}
              >
                <option value="">—</option>
                {vacancyOptions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.title}
                  </option>
                ))}
              </select>
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setAttachModal(null)}
                disabled={submitting}
              >
                {t('common.cancel', { defaultValue: 'Anuluj' })}
              </button>
              <button
                type="button"
                className="btn-primary disabled:opacity-50"
                onClick={() => void handleAttachUnmapped()}
                disabled={submitting || !attachModal.vacancyId.trim()}
              >
                {submitting ? t('common.loading') : t('app.admin.meta_leads.unmapped.attach_btn', { defaultValue: 'Привязать' })}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
