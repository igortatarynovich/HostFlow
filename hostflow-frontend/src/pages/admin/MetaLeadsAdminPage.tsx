import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  createMetaAdsMap,
  createMetaLeadCredential,
  deleteMetaAdsMap,
  deleteMetaLeadCredential,
  getMetaIncomingPreview,
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
import { createCustomFieldDefinition, listCustomFieldDefinitions } from '../../api/custom_fields'
import { listAdminUsers } from '../../api/users'
import type {
  Lead,
  LeadsProcessingModeV1,
  MetaAdsMapEntry,
  MetaCredentialCreatePayload,
  MetaFieldMappingFormat,
  MetaIncomingLeadPreviewItem,
  MetaLeadCredential,
  MetaLeadFieldMappingRule,
  MetaLeadSettings,
  MetaLeadSettingsPatch,
} from '../../api/types'
import { IconBrandMeta } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getLeadErrorSuggestion } from '../../utils/leadErrorSuggestion'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

type TabKey = 'settings' | 'credentials' | 'mapping' | 'field_mapping' | 'incoming' | 'logs'

interface FieldMappingRowState {
  id: string
  sourceText: string
  target: string
  format: MetaFieldMappingFormat
  overwrite: boolean
}

const META_MAPPING_FORMATS: MetaFieldMappingFormat[] = [
  'string',
  'email',
  'phone',
  'bool',
  'int',
  'float',
  'uuid',
  'country',
  'geo_country',
  'contact_channel',
  'list',
  'csv',
  'lower',
  'upper',
]

const META_MAPPING_TARGET_PRESETS = [
  'first_name',
  'last_name',
  'full_name',
  'email',
  'phone',
  'phone_country_code',
  'country',
  'country_raw',
  'geo_country',
  'geo_country_raw',
  'location_country',
  'current_country',
  'preferred_contact',
  'vacancy_id_hint',
  'vacancy_hint',
  'company_id_hint',
  'company_name_hint',
  'in_poland',
  'poland_stay_basis',
  'driving_experience_in_europe',
  'experience_eu_years',
] as const

/** Typical normalized / Meta keys not in the short preset list (nested paths for custom mapping). */
const META_MAPPING_TARGET_EXTENDED = [
  'vacancy_id',
  'company_id',
  'raw_lead_id',
  'form_id',
  'created_time',
  'ad_id',
  'graph_error',
  'utm.source',
  'utm.medium',
  'utm.campaign',
  'utm.term',
  'utm.content',
  'company_hints',
  'raw_field_names',
  'poland_stay_basis_raw',
  'assignment_lock_v1',
  'assignment_lock_v1.locked',
  'assignment_lock_v1.reason',
] as const

function newMappingRowId(): string {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `row-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function collectFieldNamesFromMetaPayloadPreview(json: string): string[] {
  const out = new Set<string>()
  try {
    const root = JSON.parse(json) as Record<string, unknown>
    const entry = (Array.isArray(root.entry) ? root.entry[0] : null) as Record<string, unknown> | null
    const changes = entry && Array.isArray(entry.changes) ? (entry.changes[0] as Record<string, unknown>) : null
    const value = (changes?.value ?? root) as Record<string, unknown>
    const fieldData = value?.field_data
    if (!Array.isArray(fieldData)) return []
    for (const item of fieldData) {
      if (!item || typeof item !== 'object') continue
      const name = String((item as Record<string, unknown>).name ?? '')
        .trim()
        .toLowerCase()
      if (name) out.add(name)
    }
  } catch {
    // ignore invalid preview JSON
  }
  return [...out].sort()
}

function collectTopLevelKeysFromJsonPreview(json: string): string[] {
  const out = new Set<string>()
  try {
    const o = JSON.parse(json) as unknown
    if (!o || typeof o !== 'object' || Array.isArray(o)) return []
    for (const k of Object.keys(o as Record<string, unknown>)) {
      const nk = k.trim().toLowerCase()
      if (nk) out.add(nk)
    }
  } catch {
    // ignore
  }
  return [...out].sort()
}

const MAX_NESTED_PATH_DEPTH = 5
const MAX_NESTED_PATHS_TOTAL = 220

function collectNestedDotPathsFromJson(json: string): string[] {
  const out = new Set<string>()
  const walk = (node: unknown, prefix: string, depthLeft: number) => {
    if (out.size >= MAX_NESTED_PATHS_TOTAL || depthLeft <= 0) return
    if (!node || typeof node !== 'object' || Array.isArray(node)) return
    const o = node as Record<string, unknown>
    for (const k of Object.keys(o)) {
      const seg = k.trim().toLowerCase()
      if (!seg) continue
      const path = prefix ? `${prefix}.${seg}` : seg
      out.add(path)
      if (out.size >= MAX_NESTED_PATHS_TOTAL) return
      const v = o[k]
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        walk(v, path, depthLeft - 1)
      }
    }
  }
  try {
    const o = JSON.parse(json) as unknown
    walk(o, '', MAX_NESTED_PATH_DEPTH)
  } catch {
    // ignore
  }
  return [...out].sort()
}

function collectRawFieldNamesFromNormalizedPreview(json: string): string[] {
  const out = new Set<string>()
  try {
    const o = JSON.parse(json) as unknown
    if (!o || typeof o !== 'object' || Array.isArray(o)) return []
    const raw = (o as Record<string, unknown>).raw_field_names
    if (!Array.isArray(raw)) return []
    for (const item of raw) {
      const s = String(item ?? '')
        .trim()
        .toLowerCase()
      if (s) out.add(s)
    }
  } catch {
    // ignore
  }
  return [...out].sort()
}

/** Keys on Meta `value` besides field_data (ad_id, form_id, …) plus one level `parent.child`. */
function collectShallowKeysFromMetaPayloadPreview(json: string): string[] {
  const out = new Set<string>()
  try {
    const root = JSON.parse(json) as Record<string, unknown>
    const entry = (Array.isArray(root.entry) ? root.entry[0] : null) as Record<string, unknown> | null
    const changes = entry && Array.isArray(entry.changes) ? (entry.changes[0] as Record<string, unknown>) : null
    const value = (changes?.value ?? root) as Record<string, unknown>
    if (!value || typeof value !== 'object') return []
    for (const k of Object.keys(value)) {
      const seg = k.trim().toLowerCase()
      if (!seg || seg === 'field_data') continue
      const v = value[k]
      if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
        out.add(seg)
        for (const sk of Object.keys(v as Record<string, unknown>)) {
          const ss = sk.trim().toLowerCase()
          if (ss) out.add(`${seg}.${ss}`)
        }
      } else {
        out.add(seg)
      }
    }
  } catch {
    // ignore
  }
  return [...out].sort()
}

function mappingRowCoversSource(row: FieldMappingRowState, key: string): boolean {
  const nk = key.trim().toLowerCase()
  if (!nk) return false
  const parts = row.sourceText
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean)
  return parts.includes(nk)
}

function ruleToRowState(rule: MetaLeadFieldMappingRule, id: string): FieldMappingRowState {
  const st = Array.isArray(rule.source) ? rule.source.join(', ') : String(rule.source ?? '')
  return {
    id,
    sourceText: st,
    target: rule.target ?? '',
    format: (rule.format ?? 'string') as MetaFieldMappingFormat,
    overwrite: rule.overwrite !== false,
  }
}

function rowStateToRule(row: FieldMappingRowState): MetaLeadFieldMappingRule | null | 'incomplete' {
  const srcParts = row.sourceText.split(',').map((s) => s.trim()).filter(Boolean)
  const tgt = row.target.trim()
  if (!srcParts.length && !tgt) return null
  if (!srcParts.length || !tgt) return 'incomplete'
  return {
    source: srcParts.length === 1 ? srcParts[0]! : srcParts,
    target: tgt,
    format: row.format,
    overwrite: row.overwrite,
  }
}

function rulesFromRowStates(rows: FieldMappingRowState[]): MetaLeadFieldMappingRule[] | 'incomplete' {
  const built: MetaLeadFieldMappingRule[] = []
  for (const row of rows) {
    const conv = rowStateToRule(row)
    if (conv === 'incomplete') return 'incomplete'
    if (conv) built.push(conv)
  }
  return built
}

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
  const planLimitModal = usePlanLimitModal()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
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
  const [fieldMappingRows, setFieldMappingRows] = useState<FieldMappingRowState[]>([])
  const [credentialForm, setCredentialForm] = useState<CredentialFormState>(DEFAULT_CREDENTIAL_FORM)
  const [mappingForm, setMappingForm] = useState<MappingFormState>(DEFAULT_MAPPING_FORM)
  const [mappingSearch, setMappingSearch] = useState('')
  const [attachModal, setAttachModal] = useState<{ group: UnmappedAdGroup; vacancyId: string } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [incomingRows, setIncomingRows] = useState<MetaIncomingLeadPreviewItem[]>([])
  const [incomingLoading, setIncomingLoading] = useState(false)
  const [incomingError, setIncomingError] = useState<FriendlyErrorInfo | null>(null)
  const [leadCustomFieldKeys, setLeadCustomFieldKeys] = useState<string[]>([])
  const [creatingLeadFieldKey, setCreatingLeadFieldKey] = useState<string | null>(null)
  const [fitVacancyPick, setFitVacancyPick] = useState('')

  const leadFitOrderIds = useMemo(() => {
    const fromDraft = settingsDraft.lead_fit_ordered_vacancy_ids
    if (fromDraft !== undefined) return fromDraft
    return settings?.lead_fit_ordered_vacancy_ids ?? []
  }, [settings?.lead_fit_ordered_vacancy_ids, settingsDraft.lead_fit_ordered_vacancy_ids])

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

  const effectiveProcessingMode = (settingsDraft.leads_processing_mode_v1 ??
    settings?.leads_processing_mode_v1 ??
    'assisted') as LeadsProcessingModeV1
  const autoCreateAppliesToMode = effectiveProcessingMode === 'automatic'

  const mappingRulesLimit = settings?.plan_field_mapping_rules_limit ?? null
  const credentialsPlanLimit = settings?.plan_meta_credentials_limit ?? null
  const mappingRowsAtCap =
    mappingRulesLimit != null && fieldMappingRows.length >= mappingRulesLimit
  const credentialsAtCap =
    credentialsPlanLimit != null && credentials.length >= credentialsPlanLimit

  const mergeLeadsForLogs = (leadsNeedsRoutingResp: any, leadsFailedResp: any): Lead[] => {
    const needsItems: Lead[] = Array.isArray(leadsNeedsRoutingResp?.items) ? leadsNeedsRoutingResp.items : []
    const failedItems: Lead[] = Array.isArray(leadsFailedResp?.items) ? leadsFailedResp.items : []

    // Meta Leads Admin should only operate on `source=meta` leads.
    const merged = [...needsItems, ...failedItems].filter((l) => l?.source === 'meta')

    // Dedupe by id (a lead can theoretically appear in both lists depending on pipeline transitions).
    const deduped = Array.from(new Map(merged.map((l) => [l.id, l])).values())

    deduped.sort((a, b) => {
      const ta = new Date(a.created_at).getTime()
      const tb = new Date(b.created_at).getTime()
      return (Number.isFinite(tb) ? tb : 0) - (Number.isFinite(ta) ? ta : 0)
    })

    return deduped
  }

  const refreshAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [
        settingsData,
        credsData,
        mapData,
        leadsNeedsRoutingResp,
        leadsFailedResp,
        unmappedResp,
        companiesResp,
        vacanciesResp,
        adminUsers,
      ] = await Promise.all([
        getMetaLeadSettings(),
        listMetaLeadCredentials(),
        listMetaAdsMap({ limit: 200 }),
        listLeads({ status: 'needs_routing', limit: 100, offset: 0 }),
        listLeads({ status: 'failed', limit: 100, offset: 0 }),
        getUnmappedLeads({ status: 'needs_routing', limit_per_ad: 5 }).catch(() => ({ groups: [] })),
        listCompanies({ limit: 200 }),
        listVacancies({ limit: 200 }).catch(() => ({ items: [] })),
        listAdminUsers(),
      ])
      setSettings(settingsData)
      setSettingsDraft({})
      setFieldMappingRows(
        (settingsData?.field_mapping ?? []).map((r) => ruleToRowState(r, newMappingRowId())),
      )
      setCredentials(credsData)
      setMapping(mapData)
      setLeads(mergeLeadsForLogs(leadsNeedsRoutingResp, leadsFailedResp))
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
        companyOpts.push({ id: currentCompanyId, name: t('admin.meta_leads.placeholders.selected_company') })
      }
      setCompanyOptions(companyOpts)

      const recruiterOpts = adminUsers
        .filter((user) => user.role === 'recruiter')
        .map((user) => ({
          id: user.user_id || (user as any).id || user.email || '',
          name: user.full_name || user.email || user.short_id || t('admin.meta_leads.placeholders.recruiter_fallback'),
        }))
        .filter((opt) => typeof opt.id === 'string' && opt.id.length > 0)

      const currentRecruiterId = settingsData?.fallback_recruiter_id ?? null
      if (currentRecruiterId && !recruiterOpts.some((opt) => opt.id === currentRecruiterId)) {
        const fallbackUser = adminUsers.find(
          (user) => (user.user_id || (user as any).id) === currentRecruiterId,
        )
        recruiterOpts.push({
          id: currentRecruiterId,
          name: fallbackUser?.full_name || fallbackUser?.email || fallbackUser?.short_id || t('admin.meta_leads.placeholders.selected_recruiter'),
        })
      }
      setRecruiterOptions(recruiterOpts)
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] refresh failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.load'))) {
        setError(null)
      } else {
        setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.load'), t))
      }
    } finally {
      setLoading(false)
    }
  }, [planLimitModal, t])

  useEffect(() => {
    // Deep-linking: /app/settings/integrations/meta?tab=settings|credentials|mapping|field_mapping|incoming|logs
    const sp = new URLSearchParams(location.search || '')
    const next = sp.get('tab')
    if (
      next &&
      ['settings', 'credentials', 'mapping', 'field_mapping', 'incoming', 'logs'].includes(next)
    ) {
      setTab(next as TabKey)
    }
    void refreshAll()
  }, [refreshAll, location.search])

  useEffect(() => {
    if (tab !== 'incoming' && tab !== 'field_mapping') return
    const previewSource: 'meta' | 'webhook' =
      tab === 'incoming' && searchParams.get('incoming_source') === 'webhook' ? 'webhook' : 'meta'
    let cancelled = false
    setIncomingLoading(true)
    setIncomingError(null)
    ;(async () => {
      try {
        const res = await getMetaIncomingPreview({ limit: 30, source: previewSource })
        if (!cancelled) setIncomingRows(Array.isArray(res?.items) ? res.items : [])
      } catch (err: any) {
        console.error('[MetaLeadsAdmin] incoming preview failed', err)
        if (!cancelled) {
          setIncomingRows([])
          if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.load_incoming'))) {
            setIncomingError(null)
          } else {
            setIncomingError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.load_incoming'), t))
          }
        }
      } finally {
        if (!cancelled) setIncomingLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [planLimitModal, tab, searchParams, t])

  useEffect(() => {
    if (tab !== 'field_mapping') return
    let cancelled = false
    ;(async () => {
      try {
        const defs = await listCustomFieldDefinitions({ scope: 'LEAD', is_active: true })
        if (!cancelled) {
          setLeadCustomFieldKeys(
            defs.map((d) => d.key.trim().toLowerCase()).filter((k) => k.length > 0),
          )
        }
      } catch (err) {
        console.error('[MetaLeadsAdmin] list LEAD custom field definitions failed', err)
        if (!cancelled) setLeadCustomFieldKeys([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tab])

  const handleSettingsChange = useCallback(<K extends keyof MetaLeadSettingsPatch>(key: K, value: MetaLeadSettingsPatch[K]) => {
    setSettingsDraft((prev) => ({ ...prev, [key]: value }))
  }, [])

  const addLeadFitVacancy = useCallback(
    (vacancyId: string) => {
      const id = String(vacancyId || '').trim()
      if (!id) return
      const cur = [...leadFitOrderIds]
      if (cur.includes(id)) return
      cur.push(id)
      handleSettingsChange('lead_fit_ordered_vacancy_ids', cur as MetaLeadSettingsPatch['lead_fit_ordered_vacancy_ids'])
    },
    [handleSettingsChange, leadFitOrderIds],
  )

  const removeLeadFitVacancy = useCallback(
    (index: number) => {
      const cur = [...leadFitOrderIds]
      cur.splice(index, 1)
      handleSettingsChange('lead_fit_ordered_vacancy_ids', cur as MetaLeadSettingsPatch['lead_fit_ordered_vacancy_ids'])
    },
    [handleSettingsChange, leadFitOrderIds],
  )

  const moveLeadFitVacancy = useCallback(
    (index: number, delta: number) => {
      const cur = [...leadFitOrderIds]
      const j = index + delta
      if (j < 0 || j >= cur.length) return
      const tmp = cur[index]
      cur[index] = cur[j]
      cur[j] = tmp
      handleSettingsChange('lead_fit_ordered_vacancy_ids', cur as MetaLeadSettingsPatch['lead_fit_ordered_vacancy_ids'])
    },
    [handleSettingsChange, leadFitOrderIds],
  )

  const handleSettingsSubmit = useCallback(async () => {
    try {
      const payload: MetaLeadSettingsPatch = { ...settingsDraft }
      const modeForSave = (payload.leads_processing_mode_v1 ??
        settings?.leads_processing_mode_v1 ??
        'assisted') as LeadsProcessingModeV1
      if (modeForSave !== 'automatic') {
        payload.auto_create_enabled = false
        payload.leads_auto_convert_on_fit_v1 = false
      }
      const built = rulesFromRowStates(fieldMappingRows)
      if (built === 'incomplete') {
        setError({
          title: t('admin.meta_leads.errors.field_mapping_row_incomplete'),
          hint: t('admin.meta_leads.errors.field_mapping_row_incomplete_hint'),
        })
        return
      }
      payload.field_mapping = built
      const result = await updateMetaLeadSettings(payload)
      setSettings(result)
      setSettingsDraft({})
      setFieldMappingRows((result?.field_mapping ?? []).map((r) => ruleToRowState(r, newMappingRowId())))
      setNotice(t('admin.meta_leads.notices.settings_saved'))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] update settings failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.settings_update'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.settings_update'), t))
    }
  }, [fieldMappingRows, mappingRulesLimit, planLimitModal, settings, settingsDraft, t])

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
        title: t('admin.meta_leads.errors.credential_label'),
        hint: t('admin.meta_leads.errors.credential_label', { defaultValue: 'Fill required fields and retry.' }),
      })
      return
    }
    try {
      const entry = await createMetaLeadCredential(payload)
      setCredentials((prev) => [entry, ...prev])
      setCredentialForm(DEFAULT_CREDENTIAL_FORM)
      setNotice(t('admin.meta_leads.notices.credential_created'))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] create credential failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.credential_create'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.credential_create'), t))
    }
  }, [credentialForm, credentialsPlanLimit, planLimitModal, t])

  const handleCredentialRotate = useCallback(async (id: string) => {
    try {
      const { secret } = await rotateMetaLeadCredential(id)
      setNotice(t('admin.meta_leads.notices.secret_rotated', { values: { secret } }))
      const updated = await listMetaLeadCredentials()
      setCredentials(updated)
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] rotate credential failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.secret_rotate'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.secret_rotate'), t))
    }
  }, [planLimitModal, t])

  const handleCredentialDelete = useCallback(async (id: string) => {
    if (!window.confirm(t('admin.meta_leads.prompts.delete_credential'))) return
    try {
      await deleteMetaLeadCredential(id)
      setCredentials((prev) => prev.filter((item) => item.id !== id))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] delete credential failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.credential_delete'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.credential_delete'), t))
    }
  }, [planLimitModal, t])

  const handleMappingCreate = useCallback(async () => {
    const adIdRaw = mappingForm.adId.trim()
    const vacancyIdRaw = mappingForm.vacancyId.trim()
    if (!adIdRaw || !vacancyIdRaw) {
      setError({
        title: t('admin.meta_leads.errors.mapping_required'),
        hint: t('admin.meta_leads.errors.mapping_required', { defaultValue: 'Fill required fields and retry.' }),
      })
      return
    }
    if (!/^\d+$/.test(adIdRaw)) {
      setError({
        title: t('admin.meta_leads.errors.mapping_ad_id'),
        hint: t('admin.meta_leads.errors.mapping_ad_id', { defaultValue: 'Use numeric ad id and retry.' }),
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
      setNotice(t('admin.meta_leads.notices.mapping_saved'))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] create mapping failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.mapping_create'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.mapping_create'), t))
    }
  }, [mappingForm, planLimitModal, t])

  const handleMappingDelete = useCallback(async (adId: string) => {
    if (!window.confirm(t('admin.meta_leads.prompts.delete_mapping', { values: { adId } }))) return
    try {
      await deleteMetaAdsMap(adId)
      setMapping((prev) => prev.filter((item) => item.ad_id !== adId))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] delete mapping failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.mapping_delete'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.mapping_delete'), t))
    }
  }, [planLimitModal, t])

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
      setNotice(t('admin.meta_leads.notices.unmapped_attached', { defaultValue: 'Лиды привязаны к вакансии' }))
      await refreshAll()
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.reroute'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.reroute'), t))
    } finally {
      setSubmitting(false)
    }
  }, [attachModal, planLimitModal, t, refreshAll])

  const handleReroute = useCallback(async (lead: Lead) => {
    const vacancyDefault = lead.vacancy_id ?? ''
    const vacancyId = window.prompt(
      t('admin.meta_leads.prompts.reroute_vacancy', { defaultValue: 'Enter vacancy_id (or leave empty to create candidate with company only)' }),
      vacancyDefault || ''
    )
    if (vacancyId === null) return
    const payload: { vacancy_id?: string; company_id?: string; force_process: boolean } = { force_process: true }
    if (vacancyId?.trim()) payload.vacancy_id = vacancyId.trim() as any
    if (lead.company_id) payload.company_id = lead.company_id as any
    try {
      await rerouteMetaLead(lead.id, payload)
      setNotice(t('admin.meta_leads.notices.lead_rerouted'))
      const [refreshedNeeds, refreshedFailed] = await Promise.all([
        listLeads({ status: 'needs_routing', limit: 100, offset: 0 }),
        listLeads({ status: 'failed', limit: 100, offset: 0 }),
      ])
      setLeads(mergeLeadsForLogs(refreshedNeeds, refreshedFailed))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] reroute failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.reroute'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.reroute'), t))
    }
  }, [planLimitModal, t])

  const handleRetry = useCallback(async (lead: Lead) => {
    try {
      const result = await retryLeads({ lead_ids: [String(lead.id)], refresh_graph: true })
      const item = result.items[0]
      if (item?.processed) {
        setNotice(t('admin.meta_leads.notices.lead_retried', { defaultValue: 'Лид успешно обработан' }))
      } else if (item?.message) {
        setError({
          title: item.message,
          hint: t('admin.meta_leads.errors.retry', { defaultValue: 'Retry failed. Check mapping and try again.' }),
        })
      }
      const [refreshedNeeds, refreshedFailed] = await Promise.all([
        listLeads({ status: 'needs_routing', limit: 100, offset: 0 }),
        listLeads({ status: 'failed', limit: 100, offset: 0 }),
      ])
      setLeads(mergeLeadsForLogs(refreshedNeeds, refreshedFailed))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] retry failed', err)
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.meta_leads.errors.retry', { defaultValue: 'Retry failed' }),
        )
      ) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.retry', { defaultValue: 'Retry failed' }), t))
    }
  }, [planLimitModal, t])

  // getLeadErrorSuggestion is extracted into shared util.

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

  const suggestedMetaFieldKeys = useMemo(() => {
    const s = new Set<string>()
    for (const row of incomingRows) {
      const payload = row.payload_json_preview ?? ''
      const norm = row.normalized_json_preview ?? ''
      for (const k of collectFieldNamesFromMetaPayloadPreview(payload)) {
        s.add(k)
      }
      for (const k of collectShallowKeysFromMetaPayloadPreview(payload)) {
        s.add(k)
      }
      for (const k of collectTopLevelKeysFromJsonPreview(norm)) {
        s.add(k)
      }
      for (const k of collectNestedDotPathsFromJson(norm)) {
        s.add(k)
      }
      for (const k of collectRawFieldNamesFromNormalizedPreview(norm)) {
        s.add(k)
      }
    }
    return [...s].sort()
  }, [incomingRows])

  const mappingTargetSuggestions = useMemo(() => {
    const s = new Set<string>([
      ...META_MAPPING_TARGET_PRESETS,
      ...META_MAPPING_TARGET_EXTENDED,
      ...leadCustomFieldKeys.map((k) => k.trim().toLowerCase()).filter(Boolean),
    ])
    for (const row of fieldMappingRows) {
      const t = row.target.trim().toLowerCase()
      if (t) s.add(t)
    }
    return [...s].sort((a, b) => a.localeCompare(b))
  }, [fieldMappingRows, leadCustomFieldKeys])

  const unknownKeysForLeadField = useMemo(() => {
    const have = new Set(leadCustomFieldKeys.map((k) => k.trim().toLowerCase()))
    return suggestedMetaFieldKeys.filter((k) => !have.has(k)).slice(0, 48)
  }, [suggestedMetaFieldKeys, leadCustomFieldKeys])

  const createLeadFieldFromIncomingKey = useCallback(
    async (fieldKey: string) => {
      const k = fieldKey.trim().toLowerCase()
      if (!k) return
      if (mappingRowsAtCap) {
        setError({
          title: t('common.errors.plan_meta_field_mapping_limit', { limit: mappingRulesLimit ?? 25 }),
          hint: t('common.errors.plan_upgrade_team_short'),
        })
        return
      }
      setCreatingLeadFieldKey(k)
      setError(null)
      try {
        await createCustomFieldDefinition({
          scope: 'LEAD',
          key: k,
          label: k.replace(/_/g, ' '),
          field_type: 'TEXT',
          document_type_id: null,
          is_active: true,
          order: 0,
        })
        setLeadCustomFieldKeys((prev) => [...new Set([...prev, k])].sort())
        setFieldMappingRows((prev) => {
          if (prev.some((row) => mappingRowCoversSource(row, k))) return prev
          return [
            ...prev,
            {
              id: newMappingRowId(),
              sourceText: k,
              target: k,
              format: 'string',
              overwrite: true,
            },
          ]
        })
        setNotice(t('admin.meta_leads.field_mapping.lead_field_created_notice', { values: { key: k } }))
      } catch (err: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(
            err,
            t('admin.meta_leads.errors.lead_field_definition_create'),
          )
        ) {
          return
        }
        const status = err?.response?.status
        if (status === 409) {
          setError({
            title: t('admin.meta_leads.errors.lead_field_definition_conflict'),
            hint: t('admin.meta_leads.errors.lead_field_definition_conflict_hint'),
          })
        } else {
          setError(
            getFriendlyErrorInfo(err, t('admin.meta_leads.errors.lead_field_definition_create'), t),
          )
        }
      } finally {
        setCreatingLeadFieldKey(null)
      }
    },
    [fieldMappingRows.length, mappingRowsAtCap, mappingRulesLimit, planLimitModal, t],
  )

  const fieldMappingRuleCount = useMemo(() => {
    let n = 0
    for (const row of fieldMappingRows) {
      const conv = rowStateToRule(row)
      if (conv && conv !== 'incomplete') n += 1
    }
    return n
  }, [fieldMappingRows])

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 py-1 sm:py-2">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to={CRM_APP_PATHS.settingsIntegrations} className="text-sm font-medium text-brand-600 hover:underline">
            {t('admin.integrations_hub.back_to_hub')}
          </Link>
          <div className="mt-1 flex items-center gap-2">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-[#0081FB]" aria-hidden>
              <IconBrandMeta size={22} stroke={1.75} />
            </span>
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">{t('admin.meta_leads.title')}</h1>
              <p className="text-sm text-slate-500">{t('admin.meta_leads.subtitle')}</p>
            </div>
          </div>
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
            {t('admin.meta_leads.quick_start.title', { defaultValue: 'Быстрый старт' })}
          </h3>
          <p className="mt-1 text-sm text-brand-800">
            {t('admin.meta_leads.quick_start.subtitle', {
              defaultValue: '1) Добавьте Credential (Webhook Secret, Access Token). 2) Настройте маппинг ad_id → вакансия. 3) Проверьте логи входящих лидов.',
            })}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary"
              onClick={() => setTab('credentials')}
            >
              {t('admin.meta_leads.tabs.credentials')} →
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setTab('mapping')}
            >
              {t('admin.meta_leads.tabs.mapping')} →
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
              {...friendlyErrorBannerSecondary(error, CRM_APP_PATHS.settingsLeads, t('admin.meta_leads.title'))}
              compact
            />
          )}
          {notice && !error && (
            <div className="alert-success">{notice}</div>
          )}
        </div>
      )}

      <nav className="flex flex-wrap items-center gap-2 sm:gap-3">
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'settings' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('settings')}
        >
          {t('admin.meta_leads.tabs.settings')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'credentials' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('credentials')}
        >
          {t('admin.meta_leads.tabs.credentials')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'mapping' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('mapping')}
        >
          {t('admin.meta_leads.tabs.mapping')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'field_mapping' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('field_mapping')}
        >
          {t('admin.meta_leads.tabs.field_mapping')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'incoming' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('incoming')}
        >
          {t('admin.meta_leads.tabs.incoming')}
        </button>
        <button
          type="button"
          className={`rounded px-3 py-2 text-sm ${tab === 'logs' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          onClick={() => setTab('logs')}
        >
          {t('admin.meta_leads.tabs.logs')}
        </button>
        <span className="w-full text-xs text-slate-400 sm:ml-auto sm:w-auto">
          {t('admin.meta_leads.other_platforms', { defaultValue: 'TikTok, YouTube, Google — скоро' })}
        </span>
      </nav>

      {unmappedGroups.length > 0 && (
        <section className="rounded border border-amber-200 bg-amber-50 p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-amber-900">
            {t('admin.meta_leads.unmapped.title', { defaultValue: 'Непривязанные лиды' })}
          </h2>
          <p className="mt-1 text-sm text-amber-800">
            {t('admin.meta_leads.unmapped.subtitle', { defaultValue: 'Лиды с ad_id без маппинга на вакансию. Привяжите к вакансии и перезапустите маршрутизацию.' })}
          </p>
          <div className="mt-3 space-y-2">
            {unmappedGroups.map((group) => (
              <div
                key={group.ad_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-amber-200 bg-white px-3 py-2 text-sm"
              >
                <span>
                  ad_id: <strong>{group.ad_id}</strong> — {group.count}{' '}
                  {t('admin.meta_leads.unmapped.leads', { defaultValue: 'лидов' })}
                </span>
                <button
                  type="button"
                  className="btn-primary btn-xs"
                  onClick={() => setAttachModal({ group, vacancyId: '' })}
                  disabled={submitting}
                >
                  {t('admin.meta_leads.unmapped.attach_btn', { defaultValue: 'Привязать к вакансии' })}
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === 'settings' && (
        <section className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">{t('admin.meta_leads.settings.title')}</h2>
          <p className="mt-1 text-sm text-slate-500">{t('admin.meta_leads.settings.subtitle')}</p>

          <div className="mt-4 space-y-4">
            <div className="rounded-lg border border-slate-200 bg-slate-50/90 p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                {t('admin.meta_leads.settings.automation_stack_title')}
              </div>
              <p className="mt-1 text-xs text-slate-600">{t('admin.meta_leads.settings.automation_stack_body')}</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm text-slate-700 md:col-span-2">
              <span className="block font-medium text-slate-800">
                {t('admin.meta_leads.settings.processing_mode_label')}
              </span>
              <select
                className="input mt-1 w-full max-w-md"
                value={effectiveProcessingMode}
                onChange={(event) =>
                  handleSettingsChange('leads_processing_mode_v1', event.target.value as LeadsProcessingModeV1)
                }
              >
                <option value="manual">{t('admin.meta_leads.settings.processing_mode_manual')}</option>
                <option value="assisted">{t('admin.meta_leads.settings.processing_mode_assisted')}</option>
                <option value="automatic">{t('admin.meta_leads.settings.processing_mode_automatic')}</option>
              </select>
              <p className="mt-1 text-xs text-slate-500">{t('admin.meta_leads.settings.processing_mode_hint')}</p>
            </label>
            <div className="md:col-span-2 rounded-lg border border-slate-200 bg-white p-3">
              <div className="text-sm font-medium text-slate-800">
                {t('admin.meta_leads.settings.lead_fit_order_title')}
              </div>
              <p className="mt-1 text-xs text-slate-500">{t('admin.meta_leads.settings.lead_fit_order_hint')}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <select
                  className="input max-w-md"
                  value={fitVacancyPick}
                  onChange={(e) => setFitVacancyPick(e.target.value)}
                >
                  <option value="">{t('admin.meta_leads.settings.lead_fit_order_pick')}</option>
                  {vacancyOptions
                    .filter((v) => !leadFitOrderIds.includes(v.id))
                    .map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.title}
                      </option>
                    ))}
                </select>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => {
                    if (fitVacancyPick) {
                      addLeadFitVacancy(fitVacancyPick)
                      setFitVacancyPick('')
                    }
                  }}
                >
                  {t('common.actions.add')}
                </button>
              </div>
              <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-800">
                {leadFitOrderIds.map((id, idx) => (
                  <li key={`${String(id)}-${idx}`} className="flex flex-wrap items-center gap-2">
                    <span className="min-w-0 flex-1">
                      {vacancyOptions.find((v) => v.id === id)?.title ?? String(id)}
                    </span>
                    <button
                      type="button"
                      className="btn-secondary btn-xs"
                      onClick={() => moveLeadFitVacancy(idx, -1)}
                      disabled={idx === 0}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-xs"
                      onClick={() => moveLeadFitVacancy(idx, 1)}
                      disabled={idx === leadFitOrderIds.length - 1}
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-xs text-red-700"
                      onClick={() => removeLeadFitVacancy(idx)}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ol>
            </div>
            <label
              className={`flex flex-col gap-1 text-sm md:col-span-2 ${autoCreateAppliesToMode ? 'text-slate-700' : 'text-slate-500'}`}
            >
              <span className="flex items-center gap-2">
                <input
                  type="checkbox"
                  disabled={!autoCreateAppliesToMode}
                  checked={
                    autoCreateAppliesToMode
                      ? (settingsDraft.auto_create_enabled ?? settings?.auto_create_enabled ?? true)
                      : false
                  }
                  onChange={(event) => handleSettingsChange('auto_create_enabled', event.target.checked)}
                />
                {t('admin.meta_leads.settings.auto_create')}
              </span>
              <p className={`text-xs pl-6 ${autoCreateAppliesToMode ? 'text-slate-500' : 'text-amber-800'}`}>
                {t('admin.meta_leads.settings.auto_create_automatic_only')}
              </p>
            </label>
            <label
              className={`flex flex-col gap-1 text-sm md:col-span-2 ${autoCreateAppliesToMode ? 'text-slate-700' : 'text-slate-500'}`}
            >
              <span className="flex items-center gap-2">
                <input
                  type="checkbox"
                  disabled={!autoCreateAppliesToMode}
                  checked={
                    autoCreateAppliesToMode
                      ? (settingsDraft.leads_auto_convert_on_fit_v1 ??
                          settings?.leads_auto_convert_on_fit_v1 ??
                          true)
                      : false
                  }
                  onChange={(event) =>
                    handleSettingsChange('leads_auto_convert_on_fit_v1', event.target.checked)
                  }
                />
                {t('admin.meta_leads.settings.leads_auto_convert_on_fit')}
              </span>
              <p className={`text-xs pl-6 ${autoCreateAppliesToMode ? 'text-slate-500' : 'text-amber-800'}`}>
                {t('admin.meta_leads.settings.leads_auto_convert_on_fit_hint')}
              </p>
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={(settingsDraft.mask_pii_in_logs ?? settings?.mask_pii_in_logs ?? true)}
                onChange={(event) => handleSettingsChange('mask_pii_in_logs', event.target.checked)}
              />
              {t('admin.meta_leads.settings.mask_pii')}
            </label>

            <label className="text-sm text-slate-700">
              {t('admin.meta_leads.settings.default_company')}
              <select
                className="input mt-1 w-full"
                value={selectedCompanyId ?? ''}
                onChange={(event) => handleSettingsChange('default_company_id', event.target.value ? event.target.value : null)}
              >
                <option value="">{t('admin.meta_leads.placeholders.company_none')}</option>
                {companyOptions.map((company) => (
                  <option key={company.id} value={company.id}>{company.name}</option>
                ))}
              </select>
              {selectedCompanyName && (
                <div className="mt-1 text-xs text-slate-500">{t('admin.meta_leads.settings.current_company', { values: { name: selectedCompanyName } })}</div>
              )}
            </label>

            <label className="text-sm text-slate-700">
              {t('admin.meta_leads.settings.default_recruiter')}
              <select
                className="input mt-1 w-full"
                value={selectedRecruiterId ?? ''}
                onChange={(event) => handleSettingsChange('fallback_recruiter_id', event.target.value ? event.target.value : null)}
              >
                <option value="">{t('admin.meta_leads.placeholders.recruiter_none')}</option>
                {recruiterOptions.map((option) => (
                  <option key={option.id} value={option.id}>{option.name}</option>
                ))}
              </select>
              {selectedRecruiterName && (
                <div className="mt-1 text-xs text-slate-500">{t('admin.meta_leads.settings.current_recruiter', { values: { name: selectedRecruiterName } })}</div>
              )}
            </label>

            <label className="text-sm text-slate-700">
              {t('admin.meta_leads.settings.sla_label')}
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
              {t('admin.meta_leads.settings.webhook_url')}
              <input
                type="text"
                className="input mt-1 w-full"
                value={settingsDraft.webhook_url ?? settings?.webhook_url ?? ''}
                onChange={(event) => handleSettingsChange('webhook_url', event.target.value)}
              />
            </label>
            <label className="text-sm text-slate-700">
              {t('admin.meta_leads.settings.webhook_token')}
              <input
                type="text"
                className="input mt-1 w-full"
                value={settingsDraft.webhook_verify_token ?? settings?.webhook_verify_token ?? ''}
                onChange={(event) => handleSettingsChange('webhook_verify_token', event.target.value)}
              />
            </label>

            <div className="text-sm text-slate-700 md:col-span-2">
              <span className="block font-medium text-slate-800">
                {t('admin.meta_leads.settings.field_mapping_card_title')}
              </span>
              <p className="mt-1 text-slate-600">
                {t('admin.meta_leads.settings.field_mapping_card_body', { values: { count: fieldMappingRuleCount } })}
              </p>
              <button
                type="button"
                className="btn-secondary btn-sm mt-2"
                onClick={() => setTab('field_mapping')}
              >
                {t('admin.meta_leads.settings.open_field_mapping')}
              </button>
            </div>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-3 text-sm text-slate-500">
            <div>{t('admin.meta_leads.settings.last_signature_check', { values: { date: formatDateTime(settings?.last_webhook_check_at) } })}</div>
            <div>{t('admin.meta_leads.settings.signature_status', { values: { status: settings?.last_signature_status ?? '—' } })}</div>
          </div>

          <button
            type="button"
            onClick={handleSettingsSubmit}
            className="btn-primary mt-4"
          >
            {t('admin.meta_leads.settings.save')}
          </button>
        </section>
      )}

      {tab === 'credentials' && (
        <section className="space-y-4">
          <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">{t('admin.meta_leads.credentials.title')}</h2>
            {credentialsAtCap && (
              <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                {t('admin.meta_leads.credentials.plan_limit_reached', {
                  values: { limit: credentialsPlanLimit ?? 1 },
                })}
              </p>
            )}
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.credentials.label')}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.label}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, label: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.credentials.status')}
                <select
                  className="input mt-1 w-full"
                  value={credentialForm.status}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, status: event.target.value as CredentialFormState['status'] }))}
                >
                  <option value="active">{t('admin.meta_leads.credentials.statuses.active', { defaultValue: 'active' })}</option>
                  <option value="disabled">{t('admin.meta_leads.credentials.statuses.disabled', { defaultValue: 'disabled' })}</option>
                  <option value="rotation_pending">{t('admin.meta_leads.credentials.statuses.rotation_pending', { defaultValue: 'rotation_pending' })}</option>
                </select>
              </label>
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.credentials.webhook_secret')}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.secret}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, secret: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.credentials.access_token')}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.accessToken}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, accessToken: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.credentials.fields.ad_account_id', { defaultValue: 'ad_account_id' })}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.adAccountId}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, adAccountId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.credentials.fields.page_id', { defaultValue: 'page_id' })}
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
              className="btn-primary mt-4 disabled:opacity-50"
              disabled={credentialsAtCap}
              onClick={handleCredentialCreate}
            >
              {t('common.actions.save')}
            </button>
          </div>

          <div className="rounded border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.credentials.table.label')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.credentials.table.status')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.credentials.table.ad_id', { defaultValue: 'ad_id' })}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.credentials.table.page_id', { defaultValue: 'page_id' })}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.credentials.table.signature')}</th>
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
                    <td colSpan={6} className="px-4 py-4 text-center text-slate-500">{t('admin.meta_leads.credentials.empty')}</td>
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
                          {t('admin.meta_leads.credentials.actions.rotate')}
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
            <h2 className="text-lg font-semibold text-slate-900">{t('admin.meta_leads.mapping.title')}</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.mapping.fields.ad_id', { defaultValue: 'ad_id' })}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={mappingForm.adId}
                  onChange={(event) => setMappingForm((prev) => ({ ...prev, adId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.mapping.fields.vacancy_id', { defaultValue: 'vacancy_id' })}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={mappingForm.vacancyId}
                  onChange={(event) => setMappingForm((prev) => ({ ...prev, vacancyId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.mapping.note')}
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
              {t('admin.meta_leads.mapping.save')}
            </button>
          </div>

          <div className="flex items-center justify-between gap-4">
            <input
              type="text"
              placeholder={t('admin.meta_leads.mapping.search_placeholder')}
              value={mappingSearch}
              onChange={(event) => setMappingSearch(event.target.value)}
              className="input w-full"
            />
          </div>

          <div className="rounded border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.mapping.table.ad_id', { defaultValue: 'ad_id' })}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.mapping.table.vacancy_id', { defaultValue: 'vacancy_id' })}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.mapping.note')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.mapping.created')}</th>
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
                    <td colSpan={5} className="px-4 py-4 text-center text-slate-500">{t('admin.meta_leads.mapping.empty')}</td>
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
                            const note = window.prompt(t('admin.meta_leads.prompts.edit_note'), entry.note ?? '') ?? undefined
                            const vacancy = window.prompt(t('admin.meta_leads.prompts.edit_vacancy'), entry.vacancy_id) ?? undefined
                            if (!vacancy) return
                            try {
                              const updated = await updateMetaAdsMap(entry.ad_id, {
                                note: note || undefined,
                                vacancy_id: vacancy as any,
                              })
                              setMapping((prev) => prev.map((item) => (item.ad_id === updated.ad_id ? updated : item)))
                            } catch (err: any) {
                              console.error('[MetaLeadsAdmin] update mapping failed', err)
                              if (
                                planLimitModal?.showPlanLimitIfNeeded(
                                  err,
                                  t('admin.meta_leads.errors.mapping_update'),
                                )
                              ) {
                                return
                              }
                              setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.mapping_update'), t))
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

      {tab === 'field_mapping' && (
        <section className="space-y-4">
          <datalist id="meta-mapping-source-suggestions">
            {suggestedMetaFieldKeys.map((key) => (
              <option key={key} value={key} />
            ))}
          </datalist>
          <datalist id="meta-mapping-target-presets">
            {mappingTargetSuggestions.map((key) => (
              <option key={key} value={key} />
            ))}
          </datalist>
          {unknownKeysForLeadField.length > 0 && (
            <div className="rounded border border-indigo-100 bg-indigo-50/90 p-4 text-sm text-slate-800 shadow-sm">
              <h3 className="font-semibold text-indigo-950">
                {t('admin.meta_leads.field_mapping.unknown_fields_title')}
              </h3>
              <p className="mt-1 text-xs text-indigo-900/90">
                {t('admin.meta_leads.field_mapping.unknown_fields_subtitle')}
              </p>
              <ul className="mt-3 flex flex-wrap gap-2">
                {unknownKeysForLeadField.map((k) => (
                  <li
                    key={k}
                    className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-white px-2 py-1 text-xs shadow-sm"
                  >
                    <code className="font-mono text-indigo-950">{k}</code>
                    <button
                      type="button"
                      className="btn-primary btn-xs disabled:opacity-50"
                      disabled={creatingLeadFieldKey === k}
                      onClick={() => void createLeadFieldFromIncomingKey(k)}
                    >
                      {creatingLeadFieldKey === k
                        ? t('common.loading')
                        : t('admin.meta_leads.field_mapping.add_lead_field_cta')}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-slate-600">
                <Link to={CRM_APP_PATHS.settingsCustomFields} className="font-medium text-brand-600 hover:underline">
                  {t('admin.meta_leads.field_mapping.manage_custom_fields_link')}
                </Link>
                <span className="mx-1">·</span>
                {t('admin.meta_leads.field_mapping.save_mapping_reminder')}
              </p>
            </div>
          )}
          <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">{t('admin.meta_leads.field_mapping.title')}</h2>
            <p className="mt-1 text-sm text-slate-500">{t('admin.meta_leads.field_mapping.subtitle')}</p>
            {mappingRulesLimit != null && (
              <p className="mt-2 text-xs text-slate-600">
                {t('admin.meta_leads.field_mapping.plan_limit_status', {
                  values: { count: fieldMappingRows.length, limit: mappingRulesLimit },
                })}
              </p>
            )}
            <p className="mt-2 text-xs text-slate-500">{t('admin.meta_leads.field_mapping.source_hint')}</p>
            <div className="mt-4 overflow-x-auto rounded border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">
                      {t('admin.meta_leads.field_mapping.col_source')}
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">
                      {t('admin.meta_leads.field_mapping.col_target')}
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">
                      {t('admin.meta_leads.field_mapping.col_format')}
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">
                      {t('admin.meta_leads.field_mapping.col_overwrite')}
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">{t('common.labels.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {fieldMappingRows.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-3 py-6 text-center text-slate-500">
                        {t('admin.meta_leads.field_mapping.empty')}
                      </td>
                    </tr>
                  )}
                  {fieldMappingRows.map((row) => (
                    <tr key={row.id}>
                      <td className="px-3 py-2 align-top">
                        <input
                          type="text"
                          className="input w-full min-w-[140px] text-xs"
                          list="meta-mapping-source-suggestions"
                          value={row.sourceText}
                          onChange={(event) => {
                            const v = event.target.value
                            setFieldMappingRows((prev) =>
                              prev.map((r) => (r.id === row.id ? { ...r, sourceText: v } : r)),
                            )
                          }}
                          placeholder={t('admin.meta_leads.field_mapping.source_placeholder')}
                          aria-label={t('admin.meta_leads.field_mapping.col_source')}
                        />
                      </td>
                      <td className="px-3 py-2 align-top">
                        <input
                          type="text"
                          className="input w-full min-w-[140px] text-xs"
                          list="meta-mapping-target-presets"
                          value={row.target}
                          onChange={(event) => {
                            const v = event.target.value
                            setFieldMappingRows((prev) =>
                              prev.map((r) => (r.id === row.id ? { ...r, target: v } : r)),
                            )
                          }}
                          placeholder={t('admin.meta_leads.field_mapping.target_placeholder')}
                          aria-label={t('admin.meta_leads.field_mapping.col_target')}
                        />
                      </td>
                      <td className="px-3 py-2 align-top">
                        <select
                          className="input w-full min-w-[120px] text-xs"
                          value={row.format}
                          onChange={(event) => {
                            const v = event.target.value as MetaFieldMappingFormat
                            setFieldMappingRows((prev) =>
                              prev.map((r) => (r.id === row.id ? { ...r, format: v } : r)),
                            )
                          }}
                          aria-label={t('admin.meta_leads.field_mapping.col_format')}
                        >
                          {META_MAPPING_FORMATS.map((fmt) => (
                            <option key={fmt} value={fmt}>
                              {fmt}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-3 py-2 align-top">
                        <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-700">
                          <input
                            type="checkbox"
                            checked={row.overwrite}
                            onChange={(event) => {
                              const v = event.target.checked
                              setFieldMappingRows((prev) =>
                                prev.map((r) => (r.id === row.id ? { ...r, overwrite: v } : r)),
                              )
                            }}
                          />
                          {t('admin.meta_leads.field_mapping.overwrite_yes')}
                        </label>
                      </td>
                      <td className="px-3 py-2 align-top">
                        <button
                          type="button"
                          className="btn-danger btn-xs"
                          onClick={() =>
                            setFieldMappingRows((prev) => prev.filter((r) => r.id !== row.id))
                          }
                        >
                          {t('common.actions.delete')}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="btn-secondary btn-sm disabled:opacity-50"
                disabled={mappingRowsAtCap}
                title={
                  mappingRowsAtCap
                    ? t('common.errors.plan_meta_field_mapping_limit', { limit: mappingRulesLimit ?? 25 })
                    : undefined
                }
                onClick={() =>
                  setFieldMappingRows((prev) => [
                    ...prev,
                    {
                      id: newMappingRowId(),
                      sourceText: '',
                      target: '',
                      format: 'string',
                      overwrite: true,
                    },
                  ])
                }
              >
                {t('admin.meta_leads.field_mapping.add_row')}
              </button>
              {suggestedMetaFieldKeys.length > 0 && (
                <span className="text-xs text-slate-500">
                  {t('admin.meta_leads.field_mapping.suggestions_ready', {
                    values: { count: suggestedMetaFieldKeys.length },
                  })}
                </span>
              )}
            </div>
            <button type="button" onClick={handleSettingsSubmit} className="btn-primary mt-4">
              {t('admin.meta_leads.field_mapping.save')}
            </button>
          </div>
        </section>
      )}

      {tab === 'incoming' && (
        <section className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">{t('admin.meta_leads.incoming.title')}</h2>
          <p className="mt-1 text-sm text-slate-500">{t('admin.meta_leads.incoming.subtitle')}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-600">{t('admin.meta_leads.incoming.source_label')}</span>
            {(['meta', 'webhook'] as const).map((src) => {
              const active =
                (searchParams.get('incoming_source') === 'webhook' ? 'webhook' : 'meta') === src
              return (
                <button
                  key={src}
                  type="button"
                  className={`rounded-md px-2.5 py-1 text-xs font-medium ${
                    active ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                  onClick={() => {
                    const n = new URLSearchParams(searchParams)
                    n.set('tab', 'incoming')
                    if (src === 'webhook') n.set('incoming_source', 'webhook')
                    else n.delete('incoming_source')
                    setSearchParams(n, { replace: true })
                  }}
                >
                  {src === 'meta'
                    ? t('admin.meta_leads.incoming.source_meta')
                    : t('admin.meta_leads.incoming.source_webhook')}
                </button>
              )
            })}
          </div>
          {incomingError && (
            <div className="mt-3">
              <ErrorRecoveryBanner
                info={incomingError}
                onRetry={() => {
                  void (async () => {
                    setIncomingLoading(true)
                    setIncomingError(null)
                    try {
                      const previewSource: 'meta' | 'webhook' =
                        searchParams.get('incoming_source') === 'webhook' ? 'webhook' : 'meta'
                      const res = await getMetaIncomingPreview({ limit: 30, source: previewSource })
                      setIncomingRows(Array.isArray(res?.items) ? res.items : [])
                    } catch (err: any) {
                      if (
                        planLimitModal?.showPlanLimitIfNeeded(
                          err,
                          t('admin.meta_leads.errors.load_incoming'),
                        )
                      ) {
                        setIncomingError(null)
                      } else {
                        setIncomingError(
                          getFriendlyErrorInfo(err, t('admin.meta_leads.errors.load_incoming'), t),
                        )
                      }
                    } finally {
                      setIncomingLoading(false)
                    }
                  })()
                }}
                retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
                {...friendlyErrorBannerSecondary(incomingError, CRM_APP_PATHS.settingsLeads, t('admin.meta_leads.title'))}
                compact
              />
            </div>
          )}
          <div className="mt-4 space-y-3">
            {incomingLoading && incomingRows.length === 0 && !incomingError && (
              <p className="text-sm text-slate-500">{t('common.loading')}</p>
            )}
            {!incomingLoading && !incomingError && incomingRows.length === 0 && (
              <p className="text-sm text-slate-500">
                {searchParams.get('incoming_source') === 'webhook'
                  ? t('admin.meta_leads.incoming.empty_webhook')
                  : t('admin.meta_leads.incoming.empty_meta')}
              </p>
            )}
            {incomingRows.map((row) => (
              <details
                key={row.lead_id}
                className="rounded border border-slate-200 bg-slate-50/80 open:bg-white"
              >
                <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800">
                  {formatDateTime(row.created_at)} · {row.status}
                  {row.ad_id != null ? ` · ad_id ${row.ad_id}` : ''}
                  <Link
                    to={`${CRM_APP_PATHS.leads}/${row.lead_id}`}
                    className="ml-2 text-brand-600 hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {t('admin.meta_leads.incoming.open_lead')}
                  </Link>
                </summary>
                <div className="space-y-2 border-t border-slate-200 px-3 py-3 text-xs">
                  <div>
                    <span className="font-semibold text-slate-700">{t('admin.meta_leads.incoming.payload')}</span>
                    {row.payload_truncated ? (
                      <span className="ml-2 text-amber-700">{t('admin.meta_leads.incoming.truncated')}</span>
                    ) : null}
                    <pre className="mt-1 max-h-64 overflow-auto rounded bg-slate-900 p-2 text-slate-100">{row.payload_json_preview}</pre>
                  </div>
                  {row.normalized_json_preview ? (
                    <div>
                      <span className="font-semibold text-slate-700">{t('admin.meta_leads.incoming.normalized')}</span>
                      {row.normalized_truncated ? (
                        <span className="ml-2 text-amber-700">{t('admin.meta_leads.incoming.truncated')}</span>
                      ) : null}
                      <pre className="mt-1 max-h-48 overflow-auto rounded bg-slate-800 p-2 text-slate-100">
                        {row.normalized_json_preview}
                      </pre>
                    </div>
                  ) : null}
                </div>
              </details>
            ))}
          </div>
        </section>
      )}

      {tab === 'logs' && (
        <section className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">{t('admin.meta_leads.logs.title')}</h2>
          <p className="mt-1 text-sm text-slate-500">{t('admin.meta_leads.logs.subtitle')}</p>

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.logs.table.created')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.logs.table.status')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.logs.table.company')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.logs.table.vacancy')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.logs.table.contacts')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.logs.table.error')}</th>
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
                    <td colSpan={7} className="px-4 py-4 text-center text-slate-500">{t('admin.meta_leads.logs.empty')}</td>
                  </tr>
                )}
                {leads.map((lead) => {
                  const normalized = lead.normalized || {}
                  const contactName = normalized.full_name || `${normalized.first_name || ''} ${normalized.last_name || ''}`.trim()
                  const contactEmail = normalized.email
                  const contactPhone = normalized.phone
                  const contact = [contactName, contactEmail, contactPhone].filter(Boolean).join(' · ')
                  const suggestion = getLeadErrorSuggestion(lead.error, t)
                  return (
                    <tr key={lead.id}>
                      <td className="px-4 py-2 text-slate-600">{formatDateTime(lead.created_at)}</td>
                      <td className="px-4 py-2 text-slate-700">{lead.status}</td>
                      <td className="px-4 py-2 text-slate-700">{lead.company_name ?? lead.company_id}</td>
                      <td className="px-4 py-2 text-slate-700">{lead.vacancy_title ?? lead.vacancy_id ?? '—'}</td>
                      <td className="px-4 py-2 text-slate-600">{contact || '—'}</td>
                      <td className="px-4 py-2">
                        <div className="text-red-500">{lead.error ?? '—'}</div>
                        {suggestion && (
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                            <span>{suggestion.hint}</span>
                            <button
                              type="button"
                              className="btn-secondary btn-xs"
                              onClick={() => setTab(suggestion.tab)}
                            >
                              {suggestion.actionLabel}
                            </button>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex gap-2">
                          <button
                            type="button"
                            className="btn-secondary btn-xs"
                            onClick={() => void handleRetry(lead)}
                          >
                            {t('admin.meta_leads.logs.actions.retry', { defaultValue: 'Retry' })}
                          </button>
                          <button
                            type="button"
                            className="btn-secondary btn-xs"
                            onClick={() => void handleReroute(lead)}
                          >
                            {t('admin.meta_leads.logs.actions.reroute')}
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
              {t('admin.meta_leads.unmapped.attach_modal_title', {
                defaultValue: 'Привязать ad_id {adId} к вакансии',
                values: { adId: attachModal.group.ad_id },
              })}
            </h3>
            <label className="mt-3 block text-sm text-slate-700">
              {t('admin.meta_leads.unmapped.select_vacancy', { defaultValue: 'Вакансия' })}
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
                {submitting ? t('common.loading') : t('admin.meta_leads.unmapped.attach_btn', { defaultValue: 'Привязать' })}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
