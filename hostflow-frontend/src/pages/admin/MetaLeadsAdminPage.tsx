import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  createMetaAdsMap,
  createMetaLeadCredential,
  deleteMetaAdsMap,
  deleteMetaLeadCredential,
  getMetaLeadSettings,
  listMetaAdsMap,
  listMetaLeadCredentials,
  rerouteMetaLead,
  rotateMetaLeadCredential,
  updateMetaAdsMap,
  updateMetaLeadSettings,
} from '../../api/metaLeads'
import { listCompanies, listLeads } from '../../api/client'
import { listAdminUsers } from '../../api/users'
import type {
  Lead,
  MetaAdsMapEntry,
  MetaCredentialCreatePayload,
  MetaLeadCredential,
  MetaLeadSettings,
  MetaLeadSettingsPatch,
} from '../../api/types'
import { useI18n } from '../../i18n'

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
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [settings, setSettings] = useState<MetaLeadSettings | null>(null)
  const [credentials, setCredentials] = useState<MetaLeadCredential[]>([])
  const [mapping, setMapping] = useState<MetaAdsMapEntry[]>([])
  const [leads, setLeads] = useState<Lead[]>([])
  const [companyOptions, setCompanyOptions] = useState<Array<{ id: string; name: string }>>([])
  const [recruiterOptions, setRecruiterOptions] = useState<Array<{ id: string; name: string }>>([])

  const [settingsDraft, setSettingsDraft] = useState<MetaLeadSettingsPatch>({})
  const [credentialForm, setCredentialForm] = useState<CredentialFormState>(DEFAULT_CREDENTIAL_FORM)
  const [mappingForm, setMappingForm] = useState<MappingFormState>(DEFAULT_MAPPING_FORM)
  const [mappingSearch, setMappingSearch] = useState('')

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
      const [settingsData, credsData, mapData, leadsResp, companiesResp, adminUsers] = await Promise.all([
        getMetaLeadSettings(),
        listMetaLeadCredentials(),
        listMetaAdsMap({ limit: 200 }),
        listLeads({ status: 'needs_routing', limit: 100, offset: 0 }),
        listCompanies({ limit: 200 }),
        listAdminUsers(),
      ])
      setSettings(settingsData)
      setSettingsDraft({})
      setCredentials(credsData)
      setMapping(mapData)
      setLeads(Array.isArray(leadsResp.items) ? leadsResp.items : [])

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
      setError(err?.message || t('app.admin.meta_leads.errors.load'))
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
      const result = await updateMetaLeadSettings(payload)
      setSettings(result)
      setSettingsDraft({})
      setNotice(t('app.admin.meta_leads.notices.settings_saved'))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] update settings failed', err)
      setError(err?.message || t('app.admin.meta_leads.errors.settings_update'))
    }
  }, [settingsDraft, t])

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
      setError(t('app.admin.meta_leads.errors.credential_label'))
      return
    }
    try {
      const entry = await createMetaLeadCredential(payload)
      setCredentials((prev) => [entry, ...prev])
      setCredentialForm(DEFAULT_CREDENTIAL_FORM)
      setNotice(t('app.admin.meta_leads.notices.credential_created'))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] create credential failed', err)
      setError(err?.message || t('app.admin.meta_leads.errors.credential_create'))
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
      setError(err?.message || t('app.admin.meta_leads.errors.secret_rotate'))
    }
  }, [t])

  const handleCredentialDelete = useCallback(async (id: string) => {
    if (!window.confirm(t('app.admin.meta_leads.prompts.delete_credential'))) return
    try {
      await deleteMetaLeadCredential(id)
      setCredentials((prev) => prev.filter((item) => item.id !== id))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] delete credential failed', err)
      setError(err?.message || t('app.admin.meta_leads.errors.credential_delete'))
    }
  }, [t])

  const handleMappingCreate = useCallback(async () => {
    const adIdRaw = mappingForm.adId.trim()
    const vacancyIdRaw = mappingForm.vacancyId.trim()
    if (!adIdRaw || !vacancyIdRaw) {
      setError(t('app.admin.meta_leads.errors.mapping_required'))
      return
    }
    if (!/^\d+$/.test(adIdRaw)) {
      setError(t('app.admin.meta_leads.errors.mapping_ad_id'))
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
      setError(err?.message || t('app.admin.meta_leads.errors.mapping_create'))
    }
  }, [mappingForm, t])

  const handleMappingDelete = useCallback(async (adId: string) => {
    if (!window.confirm(t('app.admin.meta_leads.prompts.delete_mapping', { values: { adId } }))) return
    try {
      await deleteMetaAdsMap(adId)
      setMapping((prev) => prev.filter((item) => item.ad_id !== adId))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] delete mapping failed', err)
      setError(err?.message || t('app.admin.meta_leads.errors.mapping_delete'))
    }
  }, [])

  const handleReroute = useCallback(async (lead: Lead) => {
    const vacancyDefault = lead.vacancy_id ?? ''
    const vacancyId = window.prompt(t('app.admin.meta_leads.prompts.reroute_vacancy'), vacancyDefault || '')
    if (!vacancyId) return
    try {
      await rerouteMetaLead(lead.id, { vacancy_id: vacancyId as any, force_process: true })
      setNotice(t('app.admin.meta_leads.notices.lead_rerouted'))
      const refreshed = await listLeads({ status: 'needs_routing', limit: 100, offset: 0 })
      setLeads(Array.isArray(refreshed.items) ? refreshed.items : [])
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] reroute failed', err)
      setError(err?.message || t('app.admin.meta_leads.errors.reroute'))
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
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{t('app.admin.meta_leads.title')}</h1>
          <p className="text-sm text-gray-500">{t('app.admin.meta_leads.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void refreshAll()}
            disabled={loading}
            className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
          >
            {loading ? t('common.loading') : t('common.actions.refresh')}
          </button>
        </div>
      </header>

      {(error || notice) && (
        <div className="space-y-2">
          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>
          )}
          {notice && !error && (
            <div className="rounded border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{notice}</div>
          )}
        </div>
      )}

      <nav className="flex gap-3">
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'settings' ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-700'}`}
          onClick={() => setTab('settings')}
        >
          {t('app.admin.meta_leads.tabs.settings')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'credentials' ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-700'}`}
          onClick={() => setTab('credentials')}
        >
          {t('app.admin.meta_leads.tabs.credentials')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'mapping' ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-700'}`}
          onClick={() => setTab('mapping')}
        >
          {t('app.admin.meta_leads.tabs.mapping')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'logs' ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-700'}`}
          onClick={() => setTab('logs')}
        >
          {t('app.admin.meta_leads.tabs.logs')}
        </button>
      </nav>

      {tab === 'settings' && (
        <section className="rounded border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">{t('app.admin.meta_leads.settings.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('app.admin.meta_leads.settings.subtitle')}</p>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={(settingsDraft.auto_create_enabled ?? settings?.auto_create_enabled ?? true)}
                onChange={(event) => handleSettingsChange('auto_create_enabled', event.target.checked)}
              />
              {t('app.admin.meta_leads.settings.auto_create')}
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={(settingsDraft.mask_pii_in_logs ?? settings?.mask_pii_in_logs ?? true)}
                onChange={(event) => handleSettingsChange('mask_pii_in_logs', event.target.checked)}
              />
              {t('app.admin.meta_leads.settings.mask_pii')}
            </label>

            <label className="text-sm text-gray-700">
              {t('app.admin.meta_leads.settings.default_company')}
              <select
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                value={selectedCompanyId ?? ''}
                onChange={(event) => handleSettingsChange('default_company_id', event.target.value ? event.target.value : null)}
              >
                <option value="">{t('app.admin.meta_leads.placeholders.company_none')}</option>
                {companyOptions.map((company) => (
                  <option key={company.id} value={company.id}>{company.name}</option>
                ))}
              </select>
              {selectedCompanyName && (
                <div className="mt-1 text-xs text-gray-500">{t('app.admin.meta_leads.settings.current_company', { values: { name: selectedCompanyName } })}</div>
              )}
            </label>

            <label className="text-sm text-gray-700">
              {t('app.admin.meta_leads.settings.default_recruiter')}
              <select
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                value={selectedRecruiterId ?? ''}
                onChange={(event) => handleSettingsChange('fallback_recruiter_id', event.target.value ? event.target.value : null)}
              >
                <option value="">{t('app.admin.meta_leads.placeholders.recruiter_none')}</option>
                {recruiterOptions.map((option) => (
                  <option key={option.id} value={option.id}>{option.name}</option>
                ))}
              </select>
              {selectedRecruiterName && (
                <div className="mt-1 text-xs text-gray-500">{t('app.admin.meta_leads.settings.current_recruiter', { values: { name: selectedRecruiterName } })}</div>
              )}
            </label>

            <label className="text-sm text-gray-700">
              {t('app.admin.meta_leads.settings.sla_label')}
              <input
                type="number"
                min={0}
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                value={settingsDraft.reroute_after_hours ?? settings?.reroute_after_hours ?? ''}
                onChange={(event) => {
                  const value = event.target.value
                  handleSettingsChange('reroute_after_hours', value === '' ? null : Number(value))
                }}
              />
            </label>

            <label className="text-sm text-gray-700">
              {t('app.admin.meta_leads.settings.webhook_url')}
              <input
                type="text"
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                value={settingsDraft.webhook_url ?? settings?.webhook_url ?? ''}
                onChange={(event) => handleSettingsChange('webhook_url', event.target.value)}
              />
            </label>
            <label className="text-sm text-gray-700">
              {t('app.admin.meta_leads.settings.webhook_token')}
              <input
                type="text"
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                value={settingsDraft.webhook_verify_token ?? settings?.webhook_verify_token ?? ''}
                onChange={(event) => handleSettingsChange('webhook_verify_token', event.target.value)}
              />
            </label>
          </div>

          <div className="mt-4 flex items-center gap-3 text-sm text-gray-500">
            <div>{t('app.admin.meta_leads.settings.last_signature_check', { values: { date: formatDateTime(settings?.last_webhook_check_at) } })}</div>
            <div>{t('app.admin.meta_leads.settings.signature_status', { values: { status: settings?.last_signature_status ?? '—' } })}</div>
          </div>

          <button
            type="button"
            onClick={handleSettingsSubmit}
            className="mt-4 rounded bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {t('app.admin.meta_leads.settings.save')}
          </button>
        </section>
      )}

      {tab === 'credentials' && (
        <section className="space-y-4">
          <div className="rounded border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900">{t('app.admin.meta_leads.credentials.title')}</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <label className="text-sm text-gray-700">
                {t('app.admin.meta_leads.credentials.label')}
                <input
                  type="text"
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                  value={credentialForm.label}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, label: event.target.value }))}
                />
              </label>
              <label className="text-sm text-gray-700">
                {t('app.admin.meta_leads.credentials.status')}
                <select
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                  value={credentialForm.status}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, status: event.target.value as CredentialFormState['status'] }))}
                >
                  <option value="active">active</option>
                  <option value="disabled">disabled</option>
                  <option value="rotation_pending">rotation_pending</option>
                </select>
              </label>
              <label className="text-sm text-gray-700">
                {t('app.admin.meta_leads.credentials.webhook_secret')}
                <input
                  type="text"
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                  value={credentialForm.secret}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, secret: event.target.value }))}
                />
              </label>
              <label className="text-sm text-gray-700">
                {t('app.admin.meta_leads.credentials.access_token')}
                <input
                  type="text"
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                  value={credentialForm.accessToken}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, accessToken: event.target.value }))}
                />
              </label>
              <label className="text-sm text-gray-700">
                ad_account_id
                <input
                  type="text"
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                  value={credentialForm.adAccountId}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, adAccountId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-gray-700">
                page_id
                <input
                  type="text"
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                  value={credentialForm.pageId}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, pageId: event.target.value }))}
                />
              </label>
            </div>
            <button
              type="button"
              className="mt-4 rounded bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
              onClick={handleCredentialCreate}
            >
              {t('common.actions.save')}
            </button>
          </div>

          <div className="rounded border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.credentials.table.label')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.credentials.table.status')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">ad_id</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">page_id</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.credentials.table.signature')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('common.labels.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading && credentials.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-4 text-center text-gray-500">{t('common.loading')}</td>
                  </tr>
                )}
                {!loading && credentials.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-4 text-center text-gray-500">{t('app.admin.meta_leads.credentials.empty')}</td>
                  </tr>
                )}
                {credentials.map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-4 py-2 text-gray-900">{entry.label}</td>
                    <td className="px-4 py-2 text-gray-600">{entry.status}</td>
                    <td className="px-4 py-2 text-gray-600">{entry.ad_account_last4 ?? '—'}</td>
                    <td className="px-4 py-2 text-gray-600">{entry.page_id_masked ?? '—'}</td>
                    <td className="px-4 py-2 text-gray-600">{formatDateTime(entry.last_verified_at)}</td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="text-xs text-brand-600 hover:underline"
                          onClick={() => void handleCredentialRotate(entry.id)}
                        >
                          {t('app.admin.meta_leads.credentials.actions.rotate')}
                        </button>
                        <button
                          type="button"
                          className="text-xs text-red-600 hover:underline"
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
          <div className="rounded border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900">{t('app.admin.meta_leads.mapping.title')}</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <label className="text-sm text-gray-700">
                ad_id
                <input
                  type="text"
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                  value={mappingForm.adId}
                  onChange={(event) => setMappingForm((prev) => ({ ...prev, adId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-gray-700">
                vacancy_id
                <input
                  type="text"
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                  value={mappingForm.vacancyId}
                  onChange={(event) => setMappingForm((prev) => ({ ...prev, vacancyId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-gray-700">
                {t('app.admin.meta_leads.mapping.note')}
                <input
                  type="text"
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
                  value={mappingForm.note}
                  onChange={(event) => setMappingForm((prev) => ({ ...prev, note: event.target.value }))}
                />
              </label>
            </div>
            <button
              type="button"
              className="mt-4 rounded bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
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
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="rounded border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">ad_id</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">vacancy_id</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.mapping.note')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.mapping.created')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('common.labels.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading && filteredMapping.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-4 text-center text-gray-500">{t('common.loading')}</td>
                  </tr>
                )}
                {!loading && filteredMapping.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-4 text-center text-gray-500">{t('app.admin.meta_leads.mapping.empty')}</td>
                  </tr>
                )}
                {filteredMapping.map((entry) => (
                  <tr key={entry.ad_id}>
                    <td className="px-4 py-2 text-gray-900">{entry.ad_id}</td>
                    <td className="px-4 py-2 text-gray-600">{entry.vacancy_id}</td>
                    <td className="px-4 py-2 text-gray-600">{entry.note ?? '—'}</td>
                    <td className="px-4 py-2 text-gray-500">{entry.created_at}</td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="text-xs text-brand-600 hover:underline"
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
                              setError(err?.message || t('app.admin.meta_leads.errors.mapping_update'))
                            }
                          }}
                        >
                          {t('common.actions.edit')}
                        </button>
                        <button
                          type="button"
                          className="text-xs text-red-600 hover:underline"
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
        <section className="rounded border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">{t('app.admin.meta_leads.logs.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('app.admin.meta_leads.logs.subtitle')}</p>

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.logs.table.created')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.logs.table.status')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.logs.table.company')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.logs.table.vacancy')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.logs.table.contacts')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('app.admin.meta_leads.logs.table.error')}</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">{t('common.labels.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading && leads.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-4 text-center text-gray-500">{t('common.loading')}</td>
                  </tr>
                )}
                {!loading && leads.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-4 text-center text-gray-500">{t('app.admin.meta_leads.logs.empty')}</td>
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
                      <td className="px-4 py-2 text-gray-600">{formatDateTime(lead.created_at)}</td>
                      <td className="px-4 py-2 text-gray-700">{lead.status}</td>
                      <td className="px-4 py-2 text-gray-700">{lead.company_name ?? lead.company_id}</td>
                      <td className="px-4 py-2 text-gray-700">{lead.vacancy_title ?? lead.vacancy_id ?? '—'}</td>
                      <td className="px-4 py-2 text-gray-600">{contact || '—'}</td>
                      <td className="px-4 py-2 text-red-500">{lead.error ?? '—'}</td>
                      <td className="px-4 py-2">
                        <button
                          type="button"
                          className="text-xs text-brand-600 hover:underline"
                          onClick={() => void handleReroute(lead)}
                        >
                          {t('app.admin.meta_leads.logs.actions.reroute')}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
