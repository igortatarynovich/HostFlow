import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  completeMetaOAuth,
  createMetaAdsMap,
  createMetaLeadCredential,
  createLeadMessageTemplate,
  deleteMetaAdsMap,
  deleteMetaLeadCredential,
  deleteLeadMessageTemplate,
  fetchMetaGraphFieldPreview,
  finalizeMetaOAuth,
  getMetaIncomingPreview,
  getMetaLeadFormMapping,
  getMetaFormRoute,
  getMetaLeadSelfServeOnboarding,
  getMetaLeadSettings,
  getUnmappedLeads,
  listMetaLeadForms,
  putMetaLeadFormMapping,
  putMetaFormRoute,
  listMetaAdsMap,
  listMetaLeadCredentials,
  listLeadMessageTemplates,
  rerouteMetaLead,
  retryLeads,
  rotateMetaLeadCredential,
  startMetaOAuth,
  updateMetaAdsMap,
  updateLeadMessageTemplate,
  updateMetaLeadSettings,
} from '../../api/metaLeads'
import type { UnmappedAdGroup } from '../../api/metaLeads'
import { listCompanies, listLeads, listOwnCompanies, listVacancies } from '../../api/client'
import { createCustomFieldDefinition, listCustomFieldDefinitions } from '../../api/custom_fields'
import { listAdminUsers } from '../../api/users'
import { isRecruitmentAssigneeRole } from '../../auth/trustRoles'
import type {
  Lead,
  LeadsProcessingModeV1,
  MetaAdsMapEntry,
  MetaCredentialCreatePayload,
  MetaFieldMappingFormat,
  MetaGraphFieldDataPreviewField,
  MetaIncomingLeadPreviewItem,
  MetaLeadCredential,
  MetaLeadFieldMappingRule,
  MetaLeadSelfServeOnboarding,
  LeadMessageTemplate,
  MetaLeadSettings,
  MetaLeadSettingsPatch,
} from '../../api/types'
import {
  META_FORM_TENANT_DEFAULT_KEY,
  type LeadTargetType,
  type MetaLeadFormSummary,
} from '../../api/types/lead'
import { IconBrandMeta, IconCircleCheck } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getLeadErrorSuggestion } from '../../utils/leadErrorSuggestion'
import { buildMetaFormFieldRows, mappingRowCoversSource } from '../../utils/metaFormFieldRows'
import {
  LEAD_INTAKE_QUALIFIED_PRESETS,
  legacyTargetFromQualified,
  qualifiedCodeFromLegacyTarget,
  resolveMappingLegacyTarget,
  isQualifiedFieldCode,
} from '../../utils/intakeMappingUtils'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useAuth } from '../../store/auth'
import {
  listLeadImportJobs,
  pollLeadImportJob,
  postLeadCsvImport,
  type LeadImportJobOut,
} from '../../api/leadCsvImport'

/** Post-connect tabs: simple path for most users; technical pieces live under Advanced / Debug. */
type MainTabKey = 'overview' | 'processing' | 'field_mapping' | 'advanced' | 'debug'

type LegacyMetaAdminTab =
  | 'settings'
  | 'credentials'
  | 'mapping'
  | 'field_mapping'
  | 'incoming'
  | 'csv_import'
  | 'logs'

const LEGACY_META_TAB_TO_MAIN: Record<LegacyMetaAdminTab, MainTabKey> = {
  settings: 'processing',
  credentials: 'advanced',
  mapping: 'advanced',
  field_mapping: 'field_mapping',
  incoming: 'debug',
  csv_import: 'debug',
  logs: 'debug',
}

function parseMainTabFromSearch(search: string): MainTabKey | null {
  const raw = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search).get('tab')
  if (!raw) return null
  if (raw in LEGACY_META_TAB_TO_MAIN) return LEGACY_META_TAB_TO_MAIN[raw as LegacyMetaAdminTab]
  if (['overview', 'processing', 'field_mapping', 'advanced', 'debug'].includes(raw)) return raw as MainTabKey
  return null
}

interface FieldMappingRowState {
  id: string
  sourceText: string
  target: string
  qualifiedFieldCode: string
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

function metaFormSelectionKey(item: Pick<MetaLeadFormSummary, 'source' | 'form_id' | 'page_id'>): string {
  return `${item.source}:${item.form_id}:${item.page_id ?? ''}`
}

function parseMetaFormSelectionKey(
  key: string,
): { source: 'meta' | 'webhook'; form_id: string; page_id: string } | null {
  if (key === META_FORM_TENANT_DEFAULT_KEY) return null
  const idx = key.indexOf(':')
  if (idx < 0) return null
  const source = key.slice(0, idx) === 'webhook' ? 'webhook' : 'meta'
  const rest = key.slice(idx + 1)
  const idx2 = rest.indexOf(':')
  if (idx2 < 0) return null
  return { source, form_id: rest.slice(0, idx2), page_id: rest.slice(idx2 + 1) }
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

function extractPageIdsFromMetaPayloadPreview(json: string): string[] {
  const s = new Set<string>()
  try {
    const root = JSON.parse(json) as Record<string, unknown>
    const entries = Array.isArray(root.entry) ? root.entry : []
    for (const ent of entries) {
      if (!ent || typeof ent !== 'object') continue
      const e = ent as Record<string, unknown>
      const top = e.id ?? e.page_id
      if (top != null && String(top).trim()) s.add(String(top).trim())
      const changes = Array.isArray(e.changes) ? e.changes : []
      for (const ch of changes) {
        if (!ch || typeof ch !== 'object') continue
        const val = (ch as Record<string, unknown>).value
        if (val && typeof val === 'object' && !Array.isArray(val)) {
          const v = val as Record<string, unknown>
          const inner = v.page_id ?? v.page
          if (inner != null && String(inner).trim()) s.add(String(inner).trim())
        }
      }
    }
  } catch {
    // ignore
  }
  return [...s].filter(Boolean)
}

/** Top-level keys on Meta `value` besides `field_data` (ad_id, form_id, …) — no nested `a.b` paths. */
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
      out.add(seg)
    }
  } catch {
    // ignore
  }
  return [...out].sort()
}

function leadPayloadJsonPreview(lead: Lead): string {
  try {
    return JSON.stringify(lead.payload ?? {})
  } catch {
    return ''
  }
}

function ruleToRowState(rule: MetaLeadFieldMappingRule, id: string): FieldMappingRowState {
  const st = Array.isArray(rule.source) ? rule.source.join(', ') : String(rule.source ?? '')
  const qualified =
    String(rule.qualified_field_code || '').trim() || qualifiedCodeFromLegacyTarget(rule.target ?? '')
  const legacyTarget = resolveMappingLegacyTarget(rule.target ?? '', rule.qualified_field_code)
  return {
    id,
    sourceText: st,
    target: legacyTarget || String(rule.target ?? '').trim(),
    qualifiedFieldCode: qualified,
    format: (rule.format ?? 'string') as MetaFieldMappingFormat,
    overwrite: rule.overwrite !== false,
  }
}

function rowStateToRule(row: FieldMappingRowState): MetaLeadFieldMappingRule | null | 'incomplete' {
  const srcParts = row.sourceText.split(',').map((s) => s.trim()).filter(Boolean)
  const qualified =
    row.qualifiedFieldCode.trim() ||
    (isQualifiedFieldCode(row.target.trim()) ? row.target.trim() : qualifiedCodeFromLegacyTarget(row.target.trim()))
  const legacyTarget = legacyTargetFromQualified(qualified) || row.target.trim()
  const tgt = qualified || legacyTarget
  if (!srcParts.length && !tgt) return null
  if (!srcParts.length || !tgt) return 'incomplete'
  return {
    source: srcParts.length === 1 ? srcParts[0]! : srcParts,
    target: legacyTarget || row.target.trim(),
    qualified_field_code: qualified || null,
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
  const { me } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tab, setTab] = useState<MainTabKey>('overview')
  const [disconnectedExpert, setDisconnectedExpert] = useState(false)
  const [connectSuccessCue, setConnectSuccessCue] = useState(false)
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
  const [messageTemplates, setMessageTemplates] = useState<LeadMessageTemplate[]>([])
  const [newTemplateName, setNewTemplateName] = useState('')
  const [newTemplateSubject, setNewTemplateSubject] = useState('')
  const [newTemplateBody, setNewTemplateBody] = useState('')

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
  const [graphPreviewFields, setGraphPreviewFields] = useState<MetaGraphFieldDataPreviewField[]>([])
  const [metaForms, setMetaForms] = useState<MetaLeadFormSummary[]>([])
  const [selectedFormKey, setSelectedFormKey] = useState<string>(META_FORM_TENANT_DEFAULT_KEY)
  const [mappingInheritsTenant, setMappingInheritsTenant] = useState(true)
  const [tenantFallbackRulesCount, setTenantFallbackRulesCount] = useState(0)
  const [formMappingLoading, setFormMappingLoading] = useState(false)
  const [formNameDraft, setFormNameDraft] = useState('')
  const [ownCompanyOptions, setOwnCompanyOptions] = useState<Array<{ id: string; name: string }>>([])
  const [intakeRouteOwnCompanyId, setIntakeRouteOwnCompanyId] = useState('')
  const [intakeRouteTarget, setIntakeRouteTarget] = useState<LeadTargetType>('candidate')
  const [intakeRouteActive, setIntakeRouteActive] = useState(true)
  const [intakeRouteConfigured, setIntakeRouteConfigured] = useState(false)
  const [intakeRouteSaving, setIntakeRouteSaving] = useState(false)
  const [graphLeadgenInput, setGraphLeadgenInput] = useState('')
  const [graphPageInput, setGraphPageInput] = useState('')
  const [graphHostflowLeadPick, setGraphHostflowLeadPick] = useState('')
  const [graphFetchLoading, setGraphFetchLoading] = useState(false)
  const [fitVacancyPick, setFitVacancyPick] = useState('')
  const [selfServe, setSelfServe] = useState<MetaLeadSelfServeOnboarding | null>(null)
  const oauthHandledRef = useRef<string | null>(null)
  const [oauthPick, setOauthPick] = useState<{ pending_id: string; pages: { id: string; name: string }[] } | null>(
    null,
  )
  const [oauthLabel, setOauthLabel] = useState('')
  const [oauthPageId, setOauthPageId] = useState('')
  const [oauthSubscribe, setOauthSubscribe] = useState(true)
  const [oauthBusy, setOauthBusy] = useState(false)
  const [metaAdvancedOpen, setMetaAdvancedOpen] = useState(false)
  const metaAdvancedBootstrapped = useRef(false)

  const [csvJobs, setCsvJobs] = useState<LeadImportJobOut[]>([])
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [csvBusy, setCsvBusy] = useState(false)
  const [csvPanelError, setCsvPanelError] = useState<FriendlyErrorInfo | null>(null)
  const [csvLastJob, setCsvLastJob] = useState<LeadImportJobOut | null>(null)

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

  const metaOperatorBlocked = Boolean(selfServe && !selfServe.public_api_base_configured)
  const metaVerifyDone = Boolean(selfServe?.webhook_verify_token_configured)
  const metaCredDone = credentials.length > 0
  const metaMapDone = mapping.length > 0
  const metaConnected = metaCredDone
  const metaGuidedNeeded = Boolean(
    !loading && selfServe && (metaOperatorBlocked || !metaVerifyDone || !metaCredDone || !metaMapDone),
  )

  const lastLeadActivityLabel = useMemo(() => {
    const a = leads[0]?.created_at
    if (a) return formatDateTime(a)
    const b = incomingRows[0]?.created_at
    if (b) return formatDateTime(b)
    return null
  }, [leads, incomingRows])

  const setTabWithUrl = useCallback(
    (next: MainTabKey) => {
      setTab(next)
      const n = new URLSearchParams(searchParams)
      n.set('tab', next)
      setSearchParams(n, { replace: true })
    },
    [searchParams, setSearchParams],
  )
  /** OAuth UI: tariff vs deployment (META_LEADS_APP_ID, secret, redirect). */
  const metaOauthBlockedReason = useMemo<'ready' | 'server' | 'plan'>(() => {
    if (!selfServe || selfServe.oauth_quick_connect_enabled) return 'ready'
    const pa = selfServe.meta_oauth_plan_allowed
    const sr = selfServe.meta_oauth_server_ready
    if (pa === true && sr === false) return 'server'
    if (pa === false) return 'plan'
    if (!(selfServe.meta_app_id || '').trim()) return 'server'
    return 'plan'
  }, [selfServe])
  const metaContextRedirected = Boolean(
    selfServe?.meta_leads_context_redirected || settings?.meta_leads_context_redirected,
  )
  const metaContextTenantLabel = String(
    selfServe?.meta_leads_data_tenant_name ||
      settings?.meta_leads_data_tenant_name ||
      selfServe?.meta_leads_data_tenant_id ||
      settings?.meta_leads_data_tenant_id ||
      '',
  )

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
        leadTemplatesData,
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
        listLeadMessageTemplates(),
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
      setMessageTemplates(Array.isArray(leadTemplatesData) ? leadTemplatesData : [])
      setSettingsDraft({})
      if (selectedFormKey === META_FORM_TENANT_DEFAULT_KEY) {
        setFieldMappingRows(
          (settingsData?.field_mapping ?? []).map((r) => ruleToRowState(r, newMappingRowId())),
        )
        setMappingInheritsTenant(true)
      }
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
        .filter((user) => isRecruitmentAssigneeRole(user.role))
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

      try {
        const ss = await getMetaLeadSelfServeOnboarding()
        setSelfServe(ss)
      } catch (ssErr: any) {
        console.warn('[MetaLeadsAdmin] self-serve onboarding load skipped', ssErr)
        setSelfServe(null)
      }
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

  const loadCsvJobs = useCallback(async () => {
    try {
      const items = await listLeadImportJobs(15)
      setCsvJobs(items)
    } catch {
      setCsvJobs([])
    }
  }, [])

  const handleCsvImport = useCallback(async () => {
    if (!csvFile || me?.role !== 'administrator') return
    setCsvBusy(true)
    setCsvPanelError(null)
    setCsvLastJob(null)
    try {
      const job = await postLeadCsvImport(csvFile, false)
      setCsvLastJob(job)
      const final = await pollLeadImportJob(job.id)
      setCsvLastJob(final)
      setCsvFile(null)
      await loadCsvJobs()
      setNotice(
        t('admin.meta_leads.csv_import.toast_done', {
          values: {
            ok: String(final.success_rows),
            dup: String(final.duplicate_rows),
            fail: String(final.failed_rows),
          },
        }),
      )
      void refreshAll()
    } catch (err: unknown) {
      setCsvPanelError(
        getFriendlyErrorInfo(
          err,
          t('admin.meta_leads.csv_import.error'),
          t,
        ),
      )
    } finally {
      setCsvBusy(false)
    }
  }, [csvFile, me?.role, loadCsvJobs, refreshAll, t])

  useEffect(() => {
    const parsed = parseMainTabFromSearch(location.search || '')
    if (parsed) setTab(parsed)
    void refreshAll()
  }, [refreshAll, location.search])

  useEffect(() => {
    if (tab !== 'debug') return
    void loadCsvJobs()
  }, [tab, loadCsvJobs])

  useEffect(() => {
    if (!selfServe || metaAdvancedBootstrapped.current) return
    metaAdvancedBootstrapped.current = true
    if (!selfServe.public_api_base_configured) setMetaAdvancedOpen(true)
    else if (credentials.length === 0 && !selfServe.oauth_quick_connect_enabled) setMetaAdvancedOpen(true)
  }, [selfServe, credentials.length])

  useEffect(() => {
    if (disconnectedExpert && !metaConnected) {
      setTab('advanced')
    }
  }, [disconnectedExpert, metaConnected])

  useEffect(() => {
    if (tab !== 'debug' && tab !== 'field_mapping') return
    const previewSource: 'meta' | 'webhook' =
      tab === 'debug' && searchParams.get('incoming_source') === 'webhook' ? 'webhook' : 'meta'
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

  useEffect(() => {
    if (tab !== 'field_mapping') return
    let cancelled = false
    ;(async () => {
      try {
        const res = await listOwnCompanies()
        const items = Array.isArray((res as any)?.items) ? (res as any).items : []
        if (!cancelled) {
          setOwnCompanyOptions(items.map((x: any) => ({ id: String(x.id), name: String(x.name || x.id) })))
        }
      } catch {
        if (!cancelled) setOwnCompanyOptions([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tab])

  const loadMetaFormsList = useCallback(async () => {
    try {
      const res = await listMetaLeadForms({ source: 'meta' })
      setMetaForms(Array.isArray(res?.items) ? res.items : [])
      setTenantFallbackRulesCount(res?.tenant_fallback_rules_count ?? 0)
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] list meta forms failed', err)
      setMetaForms([])
    }
  }, [])

  const loadMappingForSelection = useCallback(
    async (formKey: string) => {
      setFormMappingLoading(true)
      try {
        if (formKey === META_FORM_TENANT_DEFAULT_KEY) {
          const s = settings ?? (await getMetaLeadSettings())
          setFieldMappingRows((s?.field_mapping ?? []).map((r) => ruleToRowState(r, newMappingRowId())))
          setMappingInheritsTenant(true)
          setFormNameDraft('')
          setIntakeRouteConfigured(false)
          setIntakeRouteOwnCompanyId('')
          setIntakeRouteTarget('candidate')
          return
        }
        const parsed = parseMetaFormSelectionKey(formKey)
        if (!parsed) return
        const detail = await getMetaLeadFormMapping(parsed.form_id, {
          page_id: parsed.page_id || undefined,
          source: parsed.source,
        })
        setFieldMappingRows((detail.mapping_rules ?? []).map((r) => ruleToRowState(r, newMappingRowId())))
        setMappingInheritsTenant(Boolean(detail.inherits_tenant_fallback))
        setFormNameDraft(detail.form_name?.trim() ?? '')
        setTenantFallbackRulesCount(detail.tenant_fallback_rules?.length ?? tenantFallbackRulesCount)
        try {
          const route = await getMetaFormRoute(parsed.form_id, {
            page_id: parsed.page_id || undefined,
            source: parsed.source,
          })
          setIntakeRouteConfigured(true)
          setIntakeRouteOwnCompanyId(route.own_company_id)
          setIntakeRouteTarget(route.lead_target_type)
          setIntakeRouteActive(route.is_active)
        } catch (err: any) {
          const status = err?.response?.status
          if (status === 404) {
            setIntakeRouteConfigured(false)
            setIntakeRouteOwnCompanyId('')
            setIntakeRouteTarget('candidate')
            setIntakeRouteActive(true)
          } else {
            throw err
          }
        }
      } catch (err: any) {
        console.error('[MetaLeadsAdmin] load form mapping failed', err)
        setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.load_form_mapping'), t))
      } finally {
        setFormMappingLoading(false)
      }
    },
    [settings, t, tenantFallbackRulesCount],
  )

  useEffect(() => {
    if (tab !== 'field_mapping') return
    void loadMetaFormsList()
  }, [tab, loadMetaFormsList])

  useEffect(() => {
    if (tab !== 'field_mapping') return
    void loadMappingForSelection(selectedFormKey)
  }, [tab, selectedFormKey, loadMappingForSelection])

  const handleSettingsChange = useCallback(<K extends keyof MetaLeadSettingsPatch>(key: K, value: MetaLeadSettingsPatch[K]) => {
    setSettingsDraft((prev) => ({ ...prev, [key]: value }))
  }, [])

  const copySelfServeValue = useCallback(async (text: string) => {
    const trimmed = (text || '').trim()
    if (!trimmed) return
    try {
      await navigator.clipboard.writeText(trimmed)
      setNotice(t('admin.meta_leads.self_serve.copied'))
    } catch {
      setNotice(t('admin.meta_leads.self_serve.copy_failed'))
    }
  }, [t])

  const handleGenerateVerifyToken = useCallback(async () => {
    const token =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? `hf_${crypto.randomUUID().replace(/-/g, '')}`
        : `hf_${Date.now()}`
    setSubmitting(true)
    try {
      await updateMetaLeadSettings({ webhook_verify_token: token })
      setNotice(t('admin.meta_leads.self_serve.verify_generated'))
      await refreshAll()
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.settings_update'))) {
        setError(null)
      } else {
        setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.settings_update'), t))
      }
    } finally {
      setSubmitting(false)
    }
  }, [planLimitModal, refreshAll, t])

  const handleStartMetaOAuth = useCallback(async () => {
    setOauthBusy(true)
    setError(null)
    try {
      const { authorize_url } = await startMetaOAuth()
      window.location.assign(authorize_url)
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.self_serve.oauth_error_title'))) {
        setError(null)
      } else {
        setError(getFriendlyErrorInfo(err, t('admin.meta_leads.self_serve.oauth_error_title'), t))
      }
    } finally {
      setOauthBusy(false)
    }
  }, [planLimitModal, t])

  const handleFinalizeMetaOAuth = useCallback(async () => {
    if (!oauthPick || !oauthPageId.trim() || !oauthLabel.trim()) return
    setOauthBusy(true)
    setError(null)
    try {
      const res = await finalizeMetaOAuth({
        pending_id: oauthPick.pending_id,
        page_id: oauthPageId.trim(),
        label: oauthLabel.trim(),
        subscribe_leadgen: oauthSubscribe,
      })
      setOauthPick(null)
      let msg = t('admin.meta_leads.self_serve.oauth_done')
      if (res.warning) {
        msg = `${msg} ${t('admin.meta_leads.self_serve.oauth_warning', { values: { message: res.warning } })}`
      }
      setNotice(msg)
      setConnectSuccessCue(true)
      setDisconnectedExpert(false)
      setTabWithUrl('overview')
      await refreshAll()
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.self_serve.oauth_error_title'))) {
        setError(null)
      } else {
        setError(getFriendlyErrorInfo(err, t('admin.meta_leads.self_serve.oauth_error_title'), t))
      }
    } finally {
      setOauthBusy(false)
    }
  }, [oauthLabel, oauthPageId, oauthPick, oauthSubscribe, planLimitModal, refreshAll, setTabWithUrl, t])

  useEffect(() => {
    const sp = new URLSearchParams(location.search || '')
    const code = sp.get('code')?.trim()
    const state = sp.get('state')?.trim()
    if (!code || !state) return
    if (!me || me.role !== 'administrator') return
    const key = `${code}:${state}`
    if (oauthHandledRef.current === key) return
    oauthHandledRef.current = key
    navigate(CRM_APP_PATHS.settingsIntegrationsMeta, { replace: true })
    setOauthBusy(true)
    setError(null)
    void (async () => {
      try {
        const res = await completeMetaOAuth({ code, state })
        setOauthPick({ pending_id: res.pending_id, pages: res.pages })
        const first = res.pages[0]
        setOauthPageId(first?.id ?? '')
        setOauthLabel(first ? `Meta · ${first.name}` : 'Meta Page')
        setOauthSubscribe(true)
        setNotice(t('admin.meta_leads.self_serve.oauth_pages_ready'))
      } catch (err: any) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.self_serve.oauth_error_title'))) {
          setError(null)
        } else {
          setError(getFriendlyErrorInfo(err, t('admin.meta_leads.self_serve.oauth_error_title'), t))
        }
      } finally {
        setOauthBusy(false)
      }
    })()
  }, [location.search, me, navigate, planLimitModal, t])

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
      const result = await updateMetaLeadSettings(payload)
      setSettings(result)
      setSettingsDraft({})
      setNotice(t('admin.meta_leads.notices.settings_saved'))
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] update settings failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.settings_update'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.settings_update'), t))
    }
  }, [settings, settingsDraft, t])

  const handleCreateLeadMessageTemplate = useCallback(async () => {
    const name = newTemplateName.trim()
    if (!name) return
    try {
      const created = await createLeadMessageTemplate({
        name,
        subject: newTemplateSubject,
        body: newTemplateBody,
        is_active: true,
      })
      setMessageTemplates((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)))
      setNewTemplateName('')
      setNewTemplateSubject('')
      setNewTemplateBody('')
      setNotice(
        t('admin.meta_leads.templates.saved_notice', {
          defaultValue: 'Template saved.',
        }),
      )
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.save'))) {
        setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.save'), t))
      }
    }
  }, [newTemplateBody, newTemplateName, newTemplateSubject, planLimitModal, t])

  const handleUpdateLeadMessageTemplate = useCallback(
    async (templateId: string, patch: Partial<LeadMessageTemplate>) => {
      const current = messageTemplates.find((tpl) => tpl.id === templateId)
      if (!current) return
      const payload = {
        name: (patch.name ?? current.name) || current.name,
        subject: patch.subject ?? current.subject ?? '',
        body: patch.body ?? current.body ?? '',
        is_active: patch.is_active ?? current.is_active ?? true,
      }
      try {
        const updated = await updateLeadMessageTemplate(templateId, payload)
        setMessageTemplates((prev) => prev.map((tpl) => (tpl.id === templateId ? updated : tpl)))
      } catch (err: any) {
        if (!planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.save'))) {
          setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.save'), t))
        }
      }
    },
    [messageTemplates, planLimitModal, t],
  )

  const handleDeleteLeadMessageTemplate = useCallback(
    async (templateId: string) => {
      try {
        await deleteLeadMessageTemplate(templateId)
        setMessageTemplates((prev) => prev.filter((tpl) => tpl.id !== templateId))
      } catch (err: any) {
        if (!planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.save'))) {
          setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.save'), t))
        }
      }
    },
    [planLimitModal, t],
  )

  const handleSaveFieldMapping = useCallback(async () => {
    const built = rulesFromRowStates(fieldMappingRows)
    if (built === 'incomplete') {
      setError({
        title: t('admin.meta_leads.errors.field_mapping_row_incomplete'),
        hint: t('admin.meta_leads.errors.field_mapping_row_incomplete_hint'),
      })
      return
    }
    try {
      if (selectedFormKey === META_FORM_TENANT_DEFAULT_KEY) {
        const result = await updateMetaLeadSettings({ field_mapping: built })
        setSettings(result)
        setMappingInheritsTenant(true)
        setFieldMappingRows((result?.field_mapping ?? []).map((r) => ruleToRowState(r, newMappingRowId())))
        setNotice(t('admin.meta_leads.notices.tenant_mapping_saved'))
      } else {
        const parsed = parseMetaFormSelectionKey(selectedFormKey)
        if (!parsed) return
        const detail = await putMetaLeadFormMapping(parsed.form_id, {
          source: parsed.source,
          page_id: parsed.page_id || null,
          form_name: formNameDraft.trim() || null,
          mapping_rules: built,
          last_sample_lead_id: graphHostflowLeadPick.trim() || null,
        })
        setFieldMappingRows((detail.mapping_rules ?? []).map((r) => ruleToRowState(r, newMappingRowId())))
        setMappingInheritsTenant(Boolean(detail.inherits_tenant_fallback))
        setNotice(t('admin.meta_leads.notices.form_mapping_saved'))
        await loadMetaFormsList()
      }
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] save field mapping failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.settings_update'))) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.settings_update'), t))
    }
  }, [
    fieldMappingRows,
    formNameDraft,
    graphHostflowLeadPick,
    loadMetaFormsList,
    mappingRulesLimit,
    planLimitModal,
    selectedFormKey,
    t,
  ])

  const handleSaveIntakeRoute = useCallback(async () => {
    const parsed = parseMetaFormSelectionKey(selectedFormKey)
    if (!parsed) return
    if (!intakeRouteOwnCompanyId.trim()) {
      setError({
        title: t('admin.meta_leads.errors.intake_route_own_company', { defaultValue: 'Select a company profile' }),
      })
      return
    }
    setIntakeRouteSaving(true)
    try {
      await putMetaFormRoute(parsed.form_id, {
        source: parsed.source,
        page_id: parsed.page_id || null,
        own_company_id: intakeRouteOwnCompanyId.trim(),
        lead_target_type: intakeRouteTarget,
        is_active: intakeRouteActive,
      })
      setIntakeRouteConfigured(true)
      setNotice(
        t('admin.meta_leads.notices.intake_route_saved', { defaultValue: 'Intake route saved for this form.' }),
      )
      await loadMetaFormsList()
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] save intake route failed', err)
      setError(
        getFriendlyErrorInfo(err, t('admin.meta_leads.errors.intake_route_save', { defaultValue: 'Could not save intake route' }), t),
      )
    } finally {
      setIntakeRouteSaving(false)
    }
  }, [
    intakeRouteActive,
    intakeRouteOwnCompanyId,
    intakeRouteTarget,
    loadMetaFormsList,
    selectedFormKey,
    t,
  ])

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
        hint: t('admin.meta_leads.hints.fill_fields_retry'),
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
        hint: t('admin.meta_leads.hints.fill_fields_retry'),
      })
      return
    }
    if (!/^\d+$/.test(adIdRaw)) {
      setError({
        title: t('admin.meta_leads.errors.mapping_ad_id'),
        hint: t('admin.meta_leads.hints.ad_id_numeric_retry'),
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
      setNotice(t('admin.meta_leads.notices.unmapped_attached'))
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
      t('admin.meta_leads.prompts.reroute_vacancy_id'),
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
        setNotice(t('admin.meta_leads.notices.lead_retried'))
      } else if (item?.message) {
        setError({
          title: item.message,
          hint: t('admin.meta_leads.errors.retry_hint'),
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
          t('admin.meta_leads.errors.retry'),
        )
      ) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('admin.meta_leads.errors.retry'), t))
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

  /** Recent Meta leads: incoming preview rows plus operational list (needs_routing / failed) for Graph pick + autofill. */
  const graphLeadSelectOptions = useMemo(() => {
    const rows: Array<{ id: string; label: string; payloadJson: string; externalId?: string }> = []
    const seen = new Set<string>()
    for (const r of incomingRows) {
      if (!r.lead_id || seen.has(r.lead_id)) continue
      seen.add(r.lead_id)
      const ext = (r.external_id ?? '').trim()
      rows.push({
        id: r.lead_id,
        label: ext ? `${ext} · ${r.status}` : `${r.lead_id.slice(0, 8)}… · ${r.status}`,
        payloadJson: r.payload_json_preview ?? '',
        externalId: ext || undefined,
      })
    }
    for (const l of leads) {
      if (!l?.id || l.source !== 'meta' || seen.has(l.id)) continue
      seen.add(l.id)
      const extId = (l.external_id ?? '').trim()
      rows.push({
        id: l.id,
        label: extId ? `${extId} · ${l.status}` : `${l.id.slice(0, 8)}… · ${l.status}`,
        payloadJson: leadPayloadJsonPreview(l),
        externalId: extId || undefined,
      })
    }
    rows.sort((a, b) => a.label.localeCompare(b.label))
    return rows
  }, [incomingRows, leads])

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
      for (const k of collectRawFieldNamesFromNormalizedPreview(norm)) {
        s.add(k)
      }
    }
    for (const f of graphPreviewFields) {
      const nk = f.name.trim().toLowerCase()
      if (nk) s.add(nk)
    }
    return [...s].sort()
  }, [incomingRows, graphPreviewFields])

  const metaFormFieldRows = useMemo(
    () =>
      buildMetaFormFieldRows({
        graphFields: graphPreviewFields,
        incomingPayloads: incomingRows.map((r) => r.payload_json_preview ?? ''),
        incomingNormalized: incomingRows
          .map((r) => r.normalized_json_preview ?? '')
          .filter(Boolean),
        mappingRows: fieldMappingRows,
      }),
    [graphPreviewFields, incomingRows, fieldMappingRows],
  )

  const mappingTargetSuggestions = useMemo(() => {
    const s = new Set<string>([
      ...LEAD_INTAKE_QUALIFIED_PRESETS,
      ...META_MAPPING_TARGET_PRESETS,
      ...META_MAPPING_TARGET_EXTENDED,
      ...leadCustomFieldKeys.map((k) => k.trim().toLowerCase()).filter(Boolean),
    ])
    for (const row of fieldMappingRows) {
      const qualified = row.qualifiedFieldCode.trim()
      if (qualified) s.add(qualified)
      const legacy = row.target.trim().toLowerCase()
      if (legacy) s.add(legacy)
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

  const handleFetchGraphFields = useCallback(async () => {
    const pick = graphHostflowLeadPick.trim()
    const lg = graphLeadgenInput.trim()
    const pg = graphPageInput.trim()
    if (!pick && (!lg || !pg)) {
      setError({
        title: t('admin.meta_leads.field_mapping.graph_fetch_validation_title'),
        hint: t('admin.meta_leads.field_mapping.graph_fetch_validation_hint'),
      })
      return
    }
    setGraphFetchLoading(true)
    setError(null)
    try {
      const res = await fetchMetaGraphFieldPreview(
        pick ? { hostflow_lead_id: pick, ...(pg ? { page_id: pg } : {}) } : { leadgen_id: lg, page_id: pg },
      )
      setGraphPreviewFields(Array.isArray(res.fields) ? res.fields : [])
      setGraphLeadgenInput(res.leadgen_id)
      setGraphPageInput(res.page_id)
      if (res.form_id?.trim()) {
        const fid = res.form_id.trim()
        const pid = res.page_id?.trim() ?? ''
        const key = metaFormSelectionKey({ source: 'meta', form_id: fid, page_id: pid })
        setMetaForms((prev) => {
          if (prev.some((f) => metaFormSelectionKey(f) === key)) return prev
          return [
            ...prev,
            {
              form_id: fid,
              page_id: pid || null,
              source: 'meta',
              has_form_mapping: false,
              mapping_rules_count: 0,
              inherits_tenant_fallback: true,
            },
          ]
        })
        setSelectedFormKey(key)
      }
      setNotice(
        t('admin.meta_leads.field_mapping.graph_fetch_notice', {
          values: { count: res.field_names.length, form_id: res.form_id ?? '—' },
        }),
      )
    } catch (err: any) {
      console.error('[MetaLeadsAdmin] graph field preview failed', err)
      if (
        planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.field_mapping.graph_fetch_error_title'))
      ) {
        return
      }
      const detail = err?.response?.data?.detail
      if (detail && typeof detail === 'object' && !Array.isArray(detail) && detail.message) {
        setError({
          title: t('admin.meta_leads.field_mapping.graph_fetch_error_title'),
          hint: String(detail.message),
        })
      } else {
        setError(
          getFriendlyErrorInfo(err, t('admin.meta_leads.field_mapping.graph_fetch_error_title'), t),
        )
      }
    } finally {
      setGraphFetchLoading(false)
    }
  }, [graphHostflowLeadPick, graphLeadgenInput, graphPageInput, planLimitModal, t])

  const fieldMappingRuleCount = useMemo(() => {
    let n = 0
    for (const row of fieldMappingRows) {
      const conv = rowStateToRule(row)
      if (conv && conv !== 'incomplete') n += 1
    }
    return n
  }, [fieldMappingRows])

  const metaSelfServeDocsPanel = selfServe ? (
    <div className="border-t border-slate-100 px-4 pb-4 pt-3">
      <p className="text-sm text-slate-600">{t('admin.meta_leads.self_serve.intro')}</p>
      {!selfServe.public_api_base_configured && (
        <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {t('admin.meta_leads.self_serve.warn_api_base')}
        </p>
      )}
      {selfServe.public_api_base_configured && !selfServe.webhook_verify_token_configured && (
        <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {t('admin.meta_leads.self_serve.warn_no_verify')}
        </p>
      )}
      {!selfServe.oauth_quick_connect_enabled ? (
        <p className="mt-2 text-sm text-slate-600">
          {metaOauthBlockedReason === 'server'
            ? t('admin.meta_leads.self_serve.oauth_server_env_hint')
            : t('admin.meta_leads.self_serve.oauth_team_plan_hint')}
        </p>
      ) : null}
      <ol className="mt-3 list-decimal space-y-1 pl-4 text-sm text-slate-700">
        <li>{t('admin.meta_leads.self_serve.step_invite')}</li>
        <li>{t('admin.meta_leads.self_serve.step_webhook')}</li>
        <li>{t('admin.meta_leads.self_serve.step_token')}</li>
      </ol>
      <div className="mt-4 flex flex-wrap gap-2">
        {selfServe.developers_console_app_url && (
          <a
            href={selfServe.developers_console_app_url}
            target="_blank"
            rel="noreferrer"
            className="btn-secondary btn-sm"
          >
            {t('admin.meta_leads.self_serve.link_developers')}
          </a>
        )}
        <a
          href={selfServe.graph_api_explorer_url}
          target="_blank"
          rel="noreferrer"
          className="btn-secondary btn-sm"
        >
          {t('admin.meta_leads.self_serve.link_explorer')}
        </a>
        {selfServe.documentation_url && (
          <a href={selfServe.documentation_url} target="_blank" rel="noreferrer" className="btn-secondary btn-sm">
            {t('admin.meta_leads.self_serve.link_docs')}
          </a>
        )}
        <button
          type="button"
          className="btn-primary btn-sm"
          disabled={submitting}
          onClick={() => void handleGenerateVerifyToken()}
        >
          {submitting ? t('common.loading') : t('admin.meta_leads.self_serve.generate_verify')}
        </button>
      </div>
      <dl className="mt-4 space-y-3 text-sm">
        <div>
          <dt className="font-medium text-slate-700">{t('admin.meta_leads.self_serve.label_app_id')}</dt>
          <dd className="mt-1 flex flex-wrap items-center gap-2">
            <code className="break-all rounded bg-slate-100 px-2 py-1 text-xs text-slate-900">
              {selfServe.meta_app_id?.trim() || '—'}
            </code>
            {selfServe.meta_app_id?.trim() ? (
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => void copySelfServeValue(selfServe.meta_app_id!)}
              >
                {t('admin.meta_leads.self_serve.copy')}
              </button>
            ) : null}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-slate-700">{t('admin.meta_leads.self_serve.label_callback')}</dt>
          <dd className="mt-1 flex flex-wrap items-center gap-2">
            <code className="max-w-full break-all rounded bg-slate-100 px-2 py-1 text-xs text-slate-900">
              {selfServe.webhook_callback_url?.trim() || '—'}
            </code>
            {selfServe.webhook_callback_url?.trim() ? (
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => void copySelfServeValue(selfServe.webhook_callback_url!)}
              >
                {t('admin.meta_leads.self_serve.copy')}
              </button>
            ) : null}
          </dd>
        </div>
        {selfServe.oauth_redirect_uri?.trim() ? (
          <div>
            <dt className="font-medium text-slate-700">{t('admin.meta_leads.self_serve.oauth_redirect_label')}</dt>
            <dd className="mt-1 flex flex-wrap items-center gap-2">
              <code className="max-w-full break-all rounded bg-slate-100 px-2 py-1 text-xs text-slate-900">
                {selfServe.oauth_redirect_uri.trim()}
              </code>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => void copySelfServeValue(selfServe.oauth_redirect_uri!)}
              >
                {t('admin.meta_leads.self_serve.copy')}
              </button>
            </dd>
          </div>
        ) : null}
        {selfServe.shared_meta_app_secret?.trim() ? (
          <div>
            <dt className="font-medium text-slate-700">{t('admin.meta_leads.self_serve.label_secret')}</dt>
            <dd className="mt-1 space-y-1">
              <p className="text-xs text-slate-500">{t('admin.meta_leads.self_serve.secret_hint')}</p>
              <div className="flex flex-wrap items-center gap-2">
                <code className="break-all rounded bg-slate-100 px-2 py-1 text-xs text-slate-900">
                  {selfServe.shared_meta_app_secret}
                </code>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => void copySelfServeValue(selfServe.shared_meta_app_secret!)}
                >
                  {t('admin.meta_leads.self_serve.copy')}
                </button>
              </div>
            </dd>
          </div>
        ) : null}
        <div>
          <dt className="font-medium text-slate-700">
            {t('admin.meta_leads.self_serve.label_permissions')} ({selfServe.graph_api_version})
          </dt>
          <dd className="mt-1">
            <ul className="list-inside list-disc text-slate-700">
              {selfServe.graph_permission_names.map((name) => (
                <li key={name}>
                  <code className="text-xs">{name}</code>
                </li>
              ))}
            </ul>
          </dd>
        </div>
      </dl>
    </div>
  ) : null

  return (
    <SettingsSubpageHeader
      backHref={CRM_APP_PATHS.settingsIntegrations}
      backLabel={t('admin.integrations_hub.back_to_hub')}
      kicker={t('admin.integrations_hub.integration_kicker')}
      title={
        <span className="inline-flex items-center gap-2">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-[#0081FB]"
            aria-hidden
          >
            <IconBrandMeta size={22} stroke={1.75} />
          </span>
          {t('admin.meta_leads.title')}
        </span>
      }
      subtitle={t('admin.meta_leads.subtitle')}
      actions={
        <button
          type="button"
          onClick={() => void refreshAll()}
          disabled={loading}
          className="btn-secondary btn-sm disabled:opacity-50"
        >
          {loading ? t('common.loading') : t('common.actions.refresh')}
        </button>
      }
      contentClassName="mx-auto w-full max-w-6xl"
    >

      {metaContextRedirected && metaContextTenantLabel ? (
        <div
          role="status"
          className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-950"
        >
          {t('admin.meta_leads.context_redirect_banner', {
            values: { name: metaContextTenantLabel },
          })}
        </div>
      ) : null}

      {/* Show after OAuth even when already connected (Reconnect Facebook). */}
      {oauthPick ? (
        <section
          className="rounded-xl border border-brand-200 bg-white p-6 shadow-sm sm:p-8"
          aria-labelledby="meta-oauth-pick-title"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {t('admin.meta_leads.simple_wizard.step2_kicker')}
          </p>
          <h2 id="meta-oauth-pick-title" className="mt-2 text-xl font-semibold text-slate-900">
            {t('admin.meta_leads.self_serve.oauth_pick_title')}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('admin.meta_leads.simple_wizard.select_page_hint')}
          </p>
          <div className="mt-6 max-w-md space-y-4 text-sm">
            <label className="flex flex-col gap-1">
              <span className="font-medium text-slate-700">{t('admin.meta_leads.self_serve.oauth_pick_page')}</span>
              <select
                className="input w-full"
                value={oauthPageId}
                onChange={(e) => setOauthPageId(e.target.value)}
              >
                {oauthPick.pages.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium text-slate-700">{t('admin.meta_leads.self_serve.oauth_pick_label')}</span>
              <input className="input w-full" value={oauthLabel} onChange={(e) => setOauthLabel(e.target.value)} />
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-slate-700">
              <input
                type="checkbox"
                checked={oauthSubscribe}
                onChange={(e) => setOauthSubscribe(e.target.checked)}
              />
              {t('admin.meta_leads.self_serve.oauth_subscribe_leadgen')}
            </label>
            <div className="flex flex-wrap gap-2 pt-2">
              <button
                type="button"
                className="btn-primary"
                disabled={oauthBusy || !oauthPageId.trim() || !oauthLabel.trim()}
                onClick={() => void handleFinalizeMetaOAuth()}
              >
                {oauthBusy ? t('common.loading') : t('admin.meta_leads.self_serve.oauth_confirm')}
              </button>
              <button type="button" className="btn-secondary" disabled={oauthBusy} onClick={() => setOauthPick(null)}>
                {t('common.actions.cancel')}
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {!metaConnected && !oauthPick && selfServe && !loading ? (
        <>
          {metaOperatorBlocked && !disconnectedExpert ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-950">
                {t('admin.meta_leads.guided.operator_hint')}
              </div>
              <button
                type="button"
                className="text-sm font-medium text-brand-700 underline decoration-brand-400 underline-offset-2"
                onClick={() => setDisconnectedExpert(true)}
              >
                {t('admin.meta_leads.simple_wizard.expert_link')}
              </button>
            </div>
          ) : null}
          {!metaOperatorBlocked && !disconnectedExpert ? (
            <section
              className="mx-auto max-w-md rounded-xl border border-slate-200 bg-white px-6 py-10 text-center shadow-sm sm:px-10"
              aria-labelledby="meta-simple-connect-title"
            >
              <h2 id="meta-simple-connect-title" className="text-xl font-semibold text-slate-900">
                {t('admin.meta_leads.simple_wizard.connect_title')}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                {t('admin.meta_leads.simple_wizard.connect_body')}
              </p>
              <div className="mt-8 flex flex-col items-center gap-3">
                {selfServe.oauth_quick_connect_enabled && me?.role === 'administrator' && !credentialsAtCap ? (
                  <button
                    type="button"
                    className="btn-primary px-8 py-3 text-base"
                    disabled={oauthBusy || submitting}
                    onClick={() => void handleStartMetaOAuth()}
                  >
                    {oauthBusy
                      ? t('common.loading')
                      : t('admin.meta_leads.simple_wizard.connect_cta')}
                  </button>
                ) : null}
                {selfServe.oauth_quick_connect_enabled && me?.role === 'administrator' && credentialsAtCap ? (
                  <p className="text-sm text-amber-900">{t('admin.meta_leads.oauth_strip.at_credential_cap')}</p>
                ) : null}
                {selfServe.oauth_quick_connect_enabled && me?.role !== 'administrator' ? (
                  <p className="text-sm text-slate-600">{t('admin.meta_leads.oauth_strip.admin_only')}</p>
                ) : null}
                {!selfServe.oauth_quick_connect_enabled && me?.role === 'administrator' ? (
                  <>
                    <button
                      type="button"
                      className="btn-primary cursor-not-allowed px-8 py-3 text-base opacity-60"
                      disabled
                      aria-disabled
                    >
                      {t('admin.meta_leads.simple_wizard.connect_cta')}
                    </button>
                    {metaOauthBlockedReason === 'plan' ? (
                      <Link
                        to={CRM_APP_PATHS.settingsBilling}
                        className="text-sm font-semibold text-brand-700 underline decoration-brand-400 underline-offset-2"
                      >
                        {t('admin.meta_leads.oauth_strip.upgrade_plan_cta')}
                      </Link>
                    ) : (
                      <p className="text-sm text-slate-600">{t('admin.meta_leads.oauth_strip.server_env_hint')}</p>
                    )}
                  </>
                ) : null}
                {!selfServe.oauth_quick_connect_enabled && me?.role !== 'administrator' ? (
                  <p className="text-sm text-slate-600">
                    {metaOauthBlockedReason === 'server'
                      ? t('admin.meta_leads.oauth_strip.ask_operator_oauth_env')
                      : t('admin.meta_leads.oauth_strip.ask_admin_upgrade')}
                  </p>
                ) : null}
              </div>
              <p className="mt-6 text-xs text-slate-500">
                {t('admin.meta_leads.simple_wizard.footnote')}
              </p>
              <button
                type="button"
                className="mt-6 text-sm font-medium text-brand-700 underline decoration-brand-400 underline-offset-2 hover:text-brand-800"
                onClick={() => setDisconnectedExpert(true)}
              >
                {t('admin.meta_leads.simple_wizard.expert_link')}
              </button>
            </section>
          ) : null}
        </>
      ) : null}

      {disconnectedExpert && !metaConnected && !oauthPick && selfServe && !loading ? (
        <div className="space-y-6">
          <button
            type="button"
            className="text-sm font-medium text-slate-600 underline hover:text-slate-900"
            onClick={() => setDisconnectedExpert(false)}
          >
            {t('admin.meta_leads.simple_wizard.back_simple')}
          </button>
          {metaGuidedNeeded ? (
        <section
          className="rounded-xl border-2 border-brand-500 bg-gradient-to-b from-brand-50/90 to-white p-4 shadow-md"
          aria-labelledby="meta-guided-title"
        >
          <h2 id="meta-guided-title" className="text-xl font-semibold text-slate-900">
            {metaOperatorBlocked
              ? t('admin.meta_leads.guided.title_blocked')
              : t('admin.meta_leads.guided.title_setup')}
          </h2>
          {!metaOperatorBlocked ? (
            <p className="mt-1 text-sm text-slate-600">{t('admin.meta_leads.guided.subtitle')}</p>
          ) : null}

          {metaOperatorBlocked ? (
            <p className="mt-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              {t('admin.meta_leads.guided.operator_hint')}
            </p>
          ) : (
            <ol className="mt-4 list-none space-y-3 p-0">
              <li
                className={`rounded-lg border p-4 ${
                  !metaVerifyDone
                    ? 'border-brand-400 bg-white shadow-sm ring-2 ring-brand-200'
                    : 'border-slate-200 bg-slate-50/80'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 gap-3">
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                        metaVerifyDone ? 'bg-emerald-100 text-emerald-800' : 'bg-brand-600 text-white'
                      }`}
                      aria-hidden
                    >
                      {metaVerifyDone ? <IconCircleCheck size={22} stroke={1.75} /> : '1'}
                    </span>
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-900">{t('admin.meta_leads.guided.step_verify_title')}</p>
                      <p className="mt-1 text-sm text-slate-600">{t('admin.meta_leads.guided.step_verify_hint')}</p>
                    </div>
                  </div>
                  {!metaVerifyDone ? (
                    <button
                      type="button"
                      className="btn-primary shrink-0"
                      disabled={submitting}
                      onClick={() => void handleGenerateVerifyToken()}
                    >
                      {submitting ? t('common.loading') : t('admin.meta_leads.guided.step_verify_cta')}
                    </button>
                  ) : (
                    <span className="flex shrink-0 items-center gap-1 text-sm font-medium text-emerald-700">
                      <IconCircleCheck size={18} stroke={1.75} aria-hidden />
                      {t('admin.meta_leads.guided.badge_done')}
                    </span>
                  )}
                </div>
              </li>

              <li
                className={`rounded-lg border p-4 ${
                  metaVerifyDone && !metaCredDone
                    ? 'border-brand-400 bg-white shadow-sm ring-2 ring-brand-200'
                    : metaCredDone
                      ? 'border-slate-200 bg-slate-50/80'
                      : 'border-slate-200 bg-slate-50 opacity-80'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 gap-3">
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                        metaCredDone ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'
                      }`}
                      aria-hidden
                    >
                      {metaCredDone ? <IconCircleCheck size={22} stroke={1.75} /> : '2'}
                    </span>
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-900">{t('admin.meta_leads.guided.step_cred_title')}</p>
                      <p className="mt-1 text-sm text-slate-600">{t('admin.meta_leads.guided.step_cred_hint')}</p>
                      {metaVerifyDone && me?.role === 'administrator' && selfServe.oauth_quick_connect_enabled ? (
                        <button
                          type="button"
                          className="btn-primary btn-sm mt-3"
                          disabled={oauthBusy || loading || submitting}
                          onClick={() => void handleStartMetaOAuth()}
                        >
                          {oauthBusy ? t('common.loading') : t('admin.meta_leads.guided.step_cred_cta_oauth')}
                        </button>
                      ) : null}
                      {metaVerifyDone && !metaCredDone && !selfServe.oauth_quick_connect_enabled ? (
                        <div className="mt-3 space-y-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full bg-brand-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                              {t('admin.meta_leads.oauth_strip.badge_recommended')}
                            </span>
                            <span className="text-xs font-semibold text-slate-800">
                              {t('admin.meta_leads.oauth_strip.title')}
                            </span>
                          </div>
                          <p className="text-sm text-slate-600">
                            {metaOauthBlockedReason === 'server'
                              ? t('admin.meta_leads.oauth_strip.body_server_not_configured')
                              : t('admin.meta_leads.oauth_strip.body_recommended_locked')}
                          </p>
                          {me?.role === 'administrator' ? (
                            <div className="flex flex-wrap items-center gap-2">
                              <button
                                type="button"
                                className="btn-primary btn-sm cursor-not-allowed opacity-60"
                                disabled
                                aria-disabled
                              >
                                {t('admin.meta_leads.guided.step_cred_cta_oauth')}
                              </button>
                              {metaOauthBlockedReason === 'plan' ? (
                                <Link
                                  to={CRM_APP_PATHS.settingsBilling}
                                  className="text-sm font-semibold text-brand-700 underline decoration-brand-400 underline-offset-2"
                                >
                                  {t('admin.meta_leads.oauth_strip.upgrade_plan_cta')}
                                </Link>
                              ) : (
                                <p className="text-sm text-slate-700">{t('admin.meta_leads.oauth_strip.server_env_hint')}</p>
                              )}
                            </div>
                          ) : (
                            <p className="text-sm text-slate-600">
                              {metaOauthBlockedReason === 'server'
                                ? t('admin.meta_leads.oauth_strip.ask_operator_oauth_env')
                                : t('admin.meta_leads.oauth_strip.ask_admin_upgrade')}
                            </p>
                          )}
                          <button
                            type="button"
                            className="btn-primary btn-sm w-full sm:w-auto"
                            onClick={() => setTabWithUrl('advanced')}
                          >
                            {t('admin.meta_leads.guided.step_cred_cta_credentials_tab')}
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-col items-stretch gap-2 sm:items-end">
                    {!metaCredDone && metaVerifyDone && selfServe.oauth_quick_connect_enabled ? (
                      <button type="button" className="btn-secondary btn-sm" onClick={() => setTabWithUrl('advanced')}>
                        {t('admin.meta_leads.guided.step_cred_cta_manual')}
                      </button>
                    ) : null}
                    {metaCredDone ? (
                      <span className="flex items-center gap-1 text-sm font-medium text-emerald-700">
                        <IconCircleCheck size={18} stroke={1.75} aria-hidden />
                        {t('admin.meta_leads.guided.badge_done')}
                      </span>
                    ) : null}
                  </div>
                </div>
                {!metaVerifyDone ? (
                  <p className="mt-3 text-xs text-slate-500">{t('admin.meta_leads.guided.step_cred_locked')}</p>
                ) : null}
              </li>

              <li
                className={`rounded-lg border p-4 ${
                  metaCredDone && !metaMapDone
                    ? 'border-brand-400 bg-white shadow-sm ring-2 ring-brand-200'
                    : metaMapDone
                      ? 'border-slate-200 bg-slate-50/80'
                      : 'border-slate-200 bg-slate-50 opacity-80'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 gap-3">
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                        metaMapDone ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'
                      }`}
                      aria-hidden
                    >
                      {metaMapDone ? <IconCircleCheck size={22} stroke={1.75} /> : '3'}
                    </span>
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-900">{t('admin.meta_leads.guided.step_map_title')}</p>
                      <p className="mt-1 text-sm text-slate-600">{t('admin.meta_leads.guided.step_map_hint')}</p>
                    </div>
                  </div>
                  {!metaMapDone && metaCredDone ? (
                    <button type="button" className="btn-primary shrink-0" onClick={() => setTabWithUrl('advanced')}>
                      {t('admin.meta_leads.guided.step_map_cta')}
                    </button>
                  ) : null}
                  {metaMapDone ? (
                    <span className="flex shrink-0 items-center gap-1 text-sm font-medium text-emerald-700">
                      <IconCircleCheck size={18} stroke={1.75} aria-hidden />
                      {t('admin.meta_leads.guided.badge_done')}
                    </span>
                  ) : null}
                </div>
                {!metaCredDone ? (
                  <p className="mt-3 text-xs text-slate-500">{t('admin.meta_leads.guided.step_map_locked')}</p>
                ) : null}
              </li>
            </ol>
          )}
        </section>
          ) : null}
          <details
            className="rounded-lg border border-slate-200 bg-white shadow-sm"
            open={metaAdvancedOpen}
            onToggle={(e) => setMetaAdvancedOpen((e.target as HTMLDetailsElement).open)}
          >
            <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-slate-800 [&::-webkit-details-marker]:hidden">
              <span className="inline-flex items-center gap-2">
                <span className="text-slate-400" aria-hidden>
                  {metaAdvancedOpen ? '▼' : '▶'}
                </span>
                {t('admin.meta_leads.guided.advanced_summary')}
              </span>
            </summary>
            {metaSelfServeDocsPanel}
          </details>
        </div>
      ) : null}

      {metaConnected && connectSuccessCue ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-950 shadow-sm">
          <p className="font-semibold text-emerald-900">
            {t('admin.meta_leads.simple_wizard.done_title')}
          </p>
          <button
            type="button"
            className="btn-primary mt-3"
            onClick={() => {
              setConnectSuccessCue(false)
              setTabWithUrl('processing')
            }}
          >
            {t('admin.meta_leads.simple_wizard.done_cta')}
          </button>
        </div>
      ) : null}

      {(error || notice) && (
        <div className="space-y-2">
          {error && (
            <ErrorRecoveryBanner
              info={error}
              onRetry={() => void refreshAll()}
              retryLabel={t('common.actions.refresh')}
              {...friendlyErrorBannerSecondary(error, CRM_APP_PATHS.settingsIntegrationsMeta, t('admin.meta_leads.title'))}
              compact
            />
          )}
          {notice && !error && (
            <div className="alert-success">{notice}</div>
          )}
        </div>
      )}

      {(metaConnected || disconnectedExpert) && (
        <nav className="flex flex-wrap items-center gap-2 sm:gap-3" aria-label={t('admin.meta_leads.tabs.nav_aria')}>
          {metaConnected ? (
            <>
              <button
                type="button"
                className={`rounded px-3 py-2 text-sm ${tab === 'overview' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                onClick={() => setTabWithUrl('overview')}
              >
                {t('admin.meta_leads.tabs.overview')}
              </button>
              <button
                type="button"
                className={`rounded px-3 py-2 text-sm ${tab === 'processing' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                onClick={() => setTabWithUrl('processing')}
              >
                {t('admin.meta_leads.tabs.processing')}
              </button>
              <button
                type="button"
                className={`rounded px-3 py-2 text-sm ${tab === 'field_mapping' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                onClick={() => setTabWithUrl('field_mapping')}
              >
                {t('admin.meta_leads.tabs.field_mapping')}
              </button>
              <button
                type="button"
                className={`rounded px-3 py-2 text-sm ${tab === 'debug' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                onClick={() => setTabWithUrl('debug')}
              >
                {t('admin.meta_leads.tabs.debug')}
              </button>
              <button
                type="button"
                className={`rounded px-3 py-2 text-sm ${tab === 'advanced' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                onClick={() => setTabWithUrl('advanced')}
              >
                {t('admin.meta_leads.tabs.advanced')}
              </button>
            </>
          ) : (
            <button
              type="button"
              className="rounded px-3 py-2 text-sm bg-brand-600 text-white"
              onClick={() => setTabWithUrl('advanced')}
            >
              {t('admin.meta_leads.tabs.advanced')}
            </button>
          )}
          <span className="w-full text-xs text-slate-400 sm:ml-auto sm:w-auto">
            {t('admin.meta_leads.other_platforms')}
          </span>
        </nav>
      )}

      {tab === 'advanced' && unmappedGroups.length > 0 && (
        <section className="rounded border border-amber-200 bg-amber-50 p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-amber-900">
            {t('admin.meta_leads.unmapped.title')}
          </h2>
          <p className="mt-1 text-sm text-amber-800">
            {t('admin.meta_leads.unmapped.subtitle')}
          </p>
          <div className="mt-3 space-y-2">
            {unmappedGroups.map((group) => (
              <div
                key={group.ad_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-amber-200 bg-white px-3 py-2 text-sm"
              >
                <span>
                  ad_id: <strong>{group.ad_id}</strong> — {group.count}{' '}
                  {t('admin.meta_leads.unmapped.leads')}
                </span>
                <button
                  type="button"
                  className="btn-primary btn-xs"
                  onClick={() => setAttachModal({ group, vacancyId: '' })}
                  disabled={submitting}
                >
                  {t('admin.meta_leads.unmapped.attach_btn')}
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === 'overview' && metaConnected && (
        <section className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('admin.meta_leads.overview.title')}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('admin.meta_leads.overview.status_connected')}
          </p>
          <ul className="mt-4 list-inside list-disc space-y-1 text-sm text-slate-700">
            <li>
              {t('admin.meta_leads.overview.pages', {
                values: { count: String(credentials.length) },
              })}
            </li>
            <li>
              {lastLeadActivityLabel
                ? t('admin.meta_leads.overview.last_lead', {
                    values: { time: lastLeadActivityLabel },
                  })
                : t('admin.meta_leads.overview.last_lead_none')}
            </li>
          </ul>
          <div className="mt-6 flex flex-wrap gap-2">
            {selfServe?.oauth_quick_connect_enabled && me?.role === 'administrator' && !credentialsAtCap ? (
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={oauthBusy}
                onClick={() => void handleStartMetaOAuth()}
              >
                {oauthBusy ? t('common.loading') : t('admin.meta_leads.overview.reconnect')}
              </button>
            ) : null}
            <Link className="btn-secondary btn-sm inline-flex items-center" to={CRM_APP_PATHS.leads}>
              {t('admin.meta_leads.overview.open_leads')}
            </Link>
            <button type="button" className="btn-secondary btn-sm" onClick={() => setTabWithUrl('advanced')}>
              {t('admin.meta_leads.overview.manage_advanced')}
            </button>
          </div>
          <p className="mt-4 text-xs text-slate-500">
            {t('admin.meta_leads.overview.disconnect_hint')}
          </p>
        </section>
      )}

      {tab === 'processing' && metaConnected && (
        <section className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('admin.meta_leads.processing.title')}
          </h2>
          <p className="mt-1 text-sm text-slate-500">{t('admin.meta_leads.settings.subtitle')}</p>

          <div className="mt-4 space-y-4">
            <div className="rounded-lg border border-emerald-200/80 bg-emerald-50/60 p-4">
              <div className="text-sm font-semibold text-slate-900">
                {t('admin.meta_leads.settings.simple_path_title')}
              </div>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">
                {t('admin.meta_leads.settings.simple_path_body')}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">
                {t('admin.meta_leads.settings.simple_path_automations_prefix')}{' '}
                <Link className="font-medium text-brand-700 underline-offset-2 hover:underline" to={CRM_APP_PATHS.automations}>
                  {t('admin.meta_leads.settings.simple_path_automations_link')}
                </Link>
                {t('admin.meta_leads.settings.simple_path_automations_suffix')}
              </p>
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
            <label className="text-sm text-slate-700 md:col-span-2">
              <span className="block font-medium text-slate-800">
                {t('admin.meta_leads.settings.lead_rodo_send_mode_label')}
              </span>
              <div className="mt-2 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
                <p className="font-medium">
                  {t('admin.meta_leads.settings.lifecycle_email_moved_title', {
                    defaultValue: 'Lead lifecycle email moved to Communications Control Center',
                  })}
                </p>
                <p className="mt-1 text-xs text-sky-900/80">
                  {t('admin.meta_leads.settings.lifecycle_email_moved_body', {
                    defaultValue:
                      'RODO send mode, ops emails, and templates are configured per company under Settings → Communications. Meta Integrations is deep-link only for this policy.',
                  })}
                </p>
                <Link
                  className="mt-2 inline-flex text-sm font-medium text-brand-700 underline-offset-2 hover:underline"
                  to={CRM_APP_PATHS.settingsCommunicationsLeadLifecycleEmail}
                >
                  {t('admin.meta_leads.settings.open_lifecycle_email_control_center', {
                    defaultValue: 'Open Lead lifecycle email Control Center',
                  })}
                </Link>
              </div>
            </label>
            <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50/80 p-4 md:col-span-2">
              <div className="mt-0 rounded-lg border border-slate-200 bg-white p-3">
                <p className="text-sm font-semibold text-slate-900">
                  {t('admin.meta_leads.settings.template_hub_title', { defaultValue: 'Lead Email Template Hub' })}
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  {t('admin.meta_leads.settings.template_hub_hint', {
                    defaultValue: 'Create shared templates once and bind them in the Lead lifecycle email Control Center.',
                  })}
                </p>
                <Link
                  className="mt-2 inline-flex text-xs font-medium text-brand-700 hover:underline"
                  to={CRM_APP_PATHS.settingsMessageTemplates}
                >
                  {t('admin.meta_leads.settings.open_template_hub', { defaultValue: 'Open full template hub' })}
                </Link>
                <div className="mt-2 grid gap-2 md:grid-cols-3">
                  <input
                    className="input"
                    value={newTemplateName}
                    onChange={(event) => setNewTemplateName(event.target.value)}
                    placeholder={t('admin.meta_leads.settings.template_name', { defaultValue: 'Template name' })}
                  />
                  <input
                    className="input md:col-span-2"
                    value={newTemplateSubject}
                    onChange={(event) => setNewTemplateSubject(event.target.value)}
                    placeholder={t('admin.meta_leads.settings.email_template_subject', { defaultValue: 'Email subject' })}
                  />
                  <textarea
                    className="input md:col-span-3 min-h-[88px]"
                    value={newTemplateBody}
                    onChange={(event) => setNewTemplateBody(event.target.value)}
                    placeholder={t('admin.meta_leads.settings.email_template_body', { defaultValue: 'Email body' })}
                  />
                </div>
                <button type="button" className="btn-secondary mt-2" onClick={() => void handleCreateLeadMessageTemplate()}>
                  {t('admin.meta_leads.settings.template_create', { defaultValue: 'Create template' })}
                </button>
                <div className="mt-3 space-y-2">
                  {messageTemplates.map((tpl) => (
                    <div key={tpl.id} className="rounded border border-slate-200 p-2">
                      <div className="flex items-center gap-2">
                        <input
                          className="input w-full"
                          value={tpl.name}
                          onChange={(event) => {
                            const value = event.target.value
                            setMessageTemplates((prev) => prev.map((x) => (x.id === tpl.id ? { ...x, name: value } : x)))
                          }}
                          onBlur={() => void handleUpdateLeadMessageTemplate(tpl.id, { name: tpl.name })}
                        />
                        <button type="button" className="btn-danger btn-xs" onClick={() => void handleDeleteLeadMessageTemplate(tpl.id)}>
                          {t('common.actions.delete', { defaultValue: 'Delete' })}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
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
              <p className="mt-1 text-xs text-slate-500">{t('admin.meta_leads.settings.default_company_public_client_intake_hint')}</p>
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
            </div>
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

      {tab === 'advanced' && (metaConnected || disconnectedExpert) && (
        <div className="space-y-6">
          {metaConnected && selfServe ? (
            <details
              className="rounded-lg border border-slate-200 bg-white shadow-sm"
              open={metaAdvancedOpen}
              onToggle={(e) => setMetaAdvancedOpen((e.target as HTMLDetailsElement).open)}
            >
              <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-slate-800 [&::-webkit-details-marker]:hidden">
                <span className="inline-flex items-center gap-2">
                  <span className="text-slate-400" aria-hidden>
                    {metaAdvancedOpen ? '▼' : '▶'}
                  </span>
                  {t('admin.meta_leads.guided.advanced_summary')}
                </span>
              </summary>
              {metaSelfServeDocsPanel}
            </details>
          ) : null}
          {metaConnected ? (
            <section className="rounded border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">
                {t('admin.meta_leads.advanced.ingest_title')}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {t('admin.meta_leads.advanced.ingest_subtitle')}
              </p>
              <div className="mt-4 space-y-4">
                <details className="rounded-lg border border-slate-200 bg-slate-50/90 p-3 open:bg-white">
                  <summary className="cursor-pointer list-none text-sm font-medium text-slate-800 [&::-webkit-details-marker]:hidden">
                    <span className="inline-flex items-center gap-2">
                      <span aria-hidden>▸</span>
                      {t('admin.meta_leads.settings.advanced_ingest_title')}
                    </span>
                  </summary>
                  <p className="mt-2 text-xs text-slate-600">{t('admin.meta_leads.settings.advanced_ingest_intro')}</p>
                  <div className="mt-4 rounded-lg border border-slate-200 bg-white p-3">
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
                    <ol className="mt-3 list-decimal space-y-1 pl-4 text-sm text-slate-800">
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
                            className="btn-secondary btn-xs text-rose-700"
                            onClick={() => removeLeadFitVacancy(idx)}
                          >
                            ×
                          </button>
                        </li>
                      ))}
                    </ol>
                  </div>
                  <label
                    className={`mt-4 flex flex-col gap-1 text-sm ${autoCreateAppliesToMode ? 'text-slate-700' : 'text-slate-500'}`}
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
                </details>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={(settingsDraft.mask_pii_in_logs ?? settings?.mask_pii_in_logs ?? true)}
                    onChange={(event) => handleSettingsChange('mask_pii_in_logs', event.target.checked)}
                  />
                  {t('admin.meta_leads.settings.mask_pii')}
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
                <div className="text-sm text-slate-700">
                  <span className="block font-medium text-slate-800">
                    {t('admin.meta_leads.settings.field_mapping_card_title')}
                  </span>
                  <p className="mt-1 text-slate-600">
                    {t('admin.meta_leads.settings.field_mapping_card_body', { values: { count: fieldMappingRuleCount } })}
                  </p>
                  <button
                    type="button"
                    className="btn-secondary btn-sm mt-2"
                    onClick={() => setTabWithUrl('field_mapping')}
                  >
                    {t('admin.meta_leads.settings.open_field_mapping')}
                  </button>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-sm text-slate-500">
                  <div>
                    {t('admin.meta_leads.settings.last_signature_check', {
                      values: { date: formatDateTime(settings?.last_webhook_check_at) },
                    })}
                  </div>
                  <div>
                    {t('admin.meta_leads.settings.signature_status', {
                      values: { status: settings?.last_signature_status ?? '—' },
                    })}
                  </div>
                </div>
                <button type="button" onClick={handleSettingsSubmit} className="btn-primary">
                  {t('admin.meta_leads.advanced.save_technical')}
                </button>
              </div>
            </section>
          ) : null}
        <section className="space-y-4">
          <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">{t('admin.meta_leads.credentials.title')}</h2>
            {credentialsAtCap && (
              <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
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
                  <option value="active">{t('admin.meta_leads.credentials.statuses.active')}</option>
                  <option value="disabled">{t('admin.meta_leads.credentials.statuses.disabled')}</option>
                  <option value="rotation_pending">{t('admin.meta_leads.credentials.statuses.rotation_pending')}</option>
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
                {t('admin.meta_leads.credentials.fields.ad_account_id')}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={credentialForm.adAccountId}
                  onChange={(event) => setCredentialForm((prev) => ({ ...prev, adAccountId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.credentials.fields.page_id')}
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
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.credentials.table.ad_id')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.credentials.table.page_id')}</th>
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

        <section className="space-y-4">
          <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">{t('admin.meta_leads.mapping.title')}</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.mapping.fields.ad_id')}
                <input
                  type="text"
                  className="input mt-1 w-full"
                  value={mappingForm.adId}
                  onChange={(event) => setMappingForm((prev) => ({ ...prev, adId: event.target.value }))}
                />
              </label>
              <label className="text-sm text-slate-700">
                {t('admin.meta_leads.mapping.fields.vacancy_id')}
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
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.mapping.table.ad_id')}</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600">{t('admin.meta_leads.mapping.table.vacancy_id')}</th>
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
        </div>
      )}

      {tab === 'field_mapping' && metaConnected && (
        <section className="space-y-4">
          <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
            <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
              {t('admin.meta_leads.field_mapping.form_select_label')}
              <select
                className="input max-w-xl text-sm"
                value={selectedFormKey}
                disabled={formMappingLoading}
                onChange={(e) => setSelectedFormKey(e.target.value)}
              >
                <option value={META_FORM_TENANT_DEFAULT_KEY}>
                  {t('admin.meta_leads.field_mapping.form_select_tenant_default', {
                    values: { count: tenantFallbackRulesCount },
                  })}
                </option>
                {metaForms.map((f) => (
                  <option key={metaFormSelectionKey(f)} value={metaFormSelectionKey(f)}>
                    {f.form_name?.trim() ||
                      t('admin.meta_leads.field_mapping.form_select_option', {
                        values: { form_id: f.form_id, page_id: f.page_id || '—' },
                      })}
                    {f.has_form_mapping
                      ? ` · ${t('admin.meta_leads.field_mapping.form_fields.status_mapped')}`
                      : ''}
                  </option>
                ))}
              </select>
            </label>
            {selectedFormKey !== META_FORM_TENANT_DEFAULT_KEY && (
              <label className="mt-3 flex max-w-md flex-col gap-1 text-xs font-medium text-slate-700">
                {t('admin.meta_leads.field_mapping.form_name_label')}
                <input
                  type="text"
                  className="input text-sm"
                  value={formNameDraft}
                  onChange={(e) => setFormNameDraft(e.target.value)}
                  placeholder={t('admin.meta_leads.field_mapping.form_name_placeholder')}
                />
              </label>
            )}
            {selectedFormKey !== META_FORM_TENANT_DEFAULT_KEY && (
              <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50/60 p-4">
                <h3 className="text-sm font-semibold text-slate-900">
                  {t('admin.meta_leads.intake_route.title', { defaultValue: 'Intake route' })}
                </h3>
                <p className="mt-1 text-xs text-slate-600">
                  {t('admin.meta_leads.intake_route.body', {
                    defaultValue:
                      'Bind this Meta form to a company profile and lead target. Ingest uses this before creating candidates or clients.',
                  })}
                </p>
                {!intakeRouteConfigured && (
                  <p className="mt-2 text-xs text-amber-800">
                    {t('admin.meta_leads.intake_route.fallback_warning', {
                      defaultValue:
                        'No route configured — ingest falls back to tenant business type (may create wrong entity type).',
                    })}
                  </p>
                )}
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
                    {t('admin.meta_leads.intake_route.own_company', { defaultValue: 'Company profile' })}
                    <select
                      className="input text-sm"
                      value={intakeRouteOwnCompanyId}
                      onChange={(e) => setIntakeRouteOwnCompanyId(e.target.value)}
                    >
                      <option value="">
                        {t('admin.meta_leads.intake_route.own_company_placeholder', { defaultValue: 'Select profile…' })}
                      </option>
                      {ownCompanyOptions.map((oc) => (
                        <option key={oc.id} value={oc.id}>
                          {oc.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
                    {t('admin.meta_leads.intake_route.lead_target', { defaultValue: 'Lead target type' })}
                    <select
                      className="input text-sm"
                      value={intakeRouteTarget}
                      onChange={(e) => setIntakeRouteTarget(e.target.value as LeadTargetType)}
                    >
                      <option value="candidate">
                        {t('admin.meta_leads.intake_route.targets.candidate', { defaultValue: 'Candidate (driver)' })}
                      </option>
                      <option value="client_lead">
                        {t('admin.meta_leads.intake_route.targets.client_lead', { defaultValue: 'Client lead (B2B)' })}
                      </option>
                      <option value="service_order_lead">
                        {t('admin.meta_leads.intake_route.targets.service_order_lead', {
                          defaultValue: 'Service order lead',
                        })}
                      </option>
                      <option value="partner_lead">
                        {t('admin.meta_leads.intake_route.targets.partner_lead', { defaultValue: 'Partner lead' })}
                      </option>
                    </select>
                  </label>
                </div>
                <label className="mt-3 flex items-center gap-2 text-xs text-slate-700">
                  <input
                    type="checkbox"
                    checked={intakeRouteActive}
                    onChange={(e) => setIntakeRouteActive(e.target.checked)}
                  />
                  {t('admin.meta_leads.intake_route.active', { defaultValue: 'Route active' })}
                </label>
                <button
                  type="button"
                  className="btn-primary btn-sm mt-3"
                  disabled={intakeRouteSaving || formMappingLoading}
                  onClick={() => void handleSaveIntakeRoute()}
                >
                  {intakeRouteSaving
                    ? t('common.saving')
                    : t('admin.meta_leads.intake_route.save', { defaultValue: 'Save intake route' })}
                </button>
              </div>
            )}
            {mappingInheritsTenant && selectedFormKey !== META_FORM_TENANT_DEFAULT_KEY && (
              <p className="mt-2 rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                {t('admin.meta_leads.field_mapping.inherits_tenant_banner')}
              </p>
            )}
          </div>
          <div className="rounded border border-slate-200 bg-slate-50/80 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('admin.meta_leads.field_mapping.graph_fetch_title')}
            </h3>
            <p className="mt-1 text-xs text-slate-600">{t('admin.meta_leads.field_mapping.graph_fetch_body')}</p>
            {incomingLoading && (
              <p className="mt-2 text-xs text-slate-500">{t('common.loading')}</p>
            )}
            <div className="mt-3 flex flex-wrap items-end gap-3">
              <label className="flex min-w-[220px] flex-col gap-1 text-xs font-medium text-slate-700">
                {t('admin.meta_leads.field_mapping.graph_pick_lead')}
                <select
                  className="input text-xs"
                  value={graphHostflowLeadPick}
                  onChange={(e) => {
                    const v = e.target.value
                    setGraphHostflowLeadPick(v)
                    if (!v) return
                    const opt = graphLeadSelectOptions.find((o) => o.id === v)
                    if (!opt) return
                    const pj = opt.payloadJson ?? ''
                    if (pj) {
                      const pids = extractPageIdsFromMetaPayloadPreview(pj)
                      if (pids.length === 1) setGraphPageInput(pids[0])
                    }
                    const ext = opt.externalId?.trim()
                    if (ext) {
                      setGraphLeadgenInput(ext)
                      return
                    }
                    try {
                      const root = JSON.parse(pj) as Record<string, unknown>
                      const entry = (Array.isArray(root.entry) ? root.entry[0] : null) as Record<string, unknown> | null
                      const changes = entry && Array.isArray(entry.changes) ? (entry.changes[0] as Record<string, unknown>) : null
                      const value = (changes?.value ?? root) as Record<string, unknown>
                      const lid = value?.leadgen_id ?? value?.id
                      if (lid != null && String(lid).trim()) setGraphLeadgenInput(String(lid).trim())
                    } catch {
                      // ignore
                    }
                  }}
                >
                  <option value="">{t('admin.meta_leads.field_mapping.graph_pick_lead_placeholder')}</option>
                  {graphLeadSelectOptions.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex min-w-[160px] flex-col gap-1 text-xs font-medium text-slate-700">
                {t('admin.meta_leads.field_mapping.graph_leadgen_id')}
                <input
                  type="text"
                  className="input text-xs"
                  value={graphLeadgenInput}
                  onChange={(e) => setGraphLeadgenInput(e.target.value)}
                  placeholder={t('admin.meta_leads.field_mapping.graph_leadgen_placeholder')}
                />
              </label>
              <label className="flex min-w-[160px] flex-col gap-1 text-xs font-medium text-slate-700">
                {t('admin.meta_leads.field_mapping.graph_page_id')}
                <input
                  type="text"
                  className="input text-xs"
                  value={graphPageInput}
                  onChange={(e) => setGraphPageInput(e.target.value)}
                  placeholder={t('admin.meta_leads.field_mapping.graph_page_placeholder')}
                />
              </label>
              <button
                type="button"
                className="btn-primary btn-sm disabled:opacity-50"
                disabled={
                  graphFetchLoading ||
                  (!graphHostflowLeadPick.trim() &&
                    (!graphLeadgenInput.trim() || !graphPageInput.trim()))
                }
                onClick={() => void handleFetchGraphFields()}
              >
                {graphFetchLoading ? t('common.loading') : t('admin.meta_leads.field_mapping.graph_fetch_cta')}
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-500">{t('admin.meta_leads.field_mapping.graph_fetch_footer')}</p>
          </div>

          <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">
              {t('admin.meta_leads.field_mapping.form_fields.title')}
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              {t('admin.meta_leads.field_mapping.form_fields.subtitle')}
            </p>
            {metaFormFieldRows.length === 0 ? (
              <p className="mt-4 text-sm text-slate-500">
                {t('admin.meta_leads.field_mapping.form_fields.empty')}
              </p>
            ) : (
              <div className="mt-4 overflow-x-auto rounded border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-slate-600">
                        {t('admin.meta_leads.field_mapping.form_fields.col_field')}
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-slate-600">
                        {t('admin.meta_leads.field_mapping.form_fields.col_sample')}
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-slate-600">
                        {t('admin.meta_leads.field_mapping.form_fields.col_status')}
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-slate-600">
                        {t('admin.meta_leads.field_mapping.form_fields.col_target')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {metaFormFieldRows.map((row) => (
                      <tr key={row.name}>
                        <td className="px-3 py-2 align-top font-medium text-slate-900">{row.displayName}</td>
                        <td className="px-3 py-2 align-top text-slate-700">
                          {row.sampleValue ? (
                            <span className="break-words">{row.sampleValue}</span>
                          ) : (
                            <span className="text-slate-400 italic">
                              {t('admin.meta_leads.field_mapping.form_fields.no_sample')}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 align-top">
                          {row.mapped ? (
                            <span className="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-emerald-200">
                              {t('admin.meta_leads.field_mapping.form_fields.status_mapped')}
                            </span>
                          ) : (
                            <span className="inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900 ring-1 ring-amber-200">
                              {t('admin.meta_leads.field_mapping.form_fields.status_unmapped')}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 align-top text-slate-700">
                          {row.mapped && row.target ? (
                            <span className="font-mono text-xs text-slate-800">{row.target}</span>
                          ) : (
                            <span className="text-slate-500">
                              {t('admin.meta_leads.field_mapping.form_fields.pick_target')}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

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
            <div className="rounded border border-blue-100 bg-blue-50/90 p-4 text-sm text-slate-800 shadow-sm">
              <h3 className="font-semibold text-blue-950">
                {t('admin.meta_leads.field_mapping.unknown_fields_title')}
              </h3>
              <p className="mt-1 text-xs text-blue-900/90">
                {t('admin.meta_leads.field_mapping.unknown_fields_subtitle')}
              </p>
              <ul className="mt-3 flex flex-wrap gap-2">
                {unknownKeysForLeadField.map((k) => (
                  <li
                    key={k}
                    className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-white px-2 py-1 text-xs shadow-sm"
                  >
                    <code className="font-mono text-blue-950">{k}</code>
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
            <h2 className="text-lg font-semibold text-slate-900">
              {t('admin.meta_leads.field_mapping.rules_title')}
            </h2>
            <p className="mt-1 text-sm text-slate-500">{t('admin.meta_leads.field_mapping.rules_subtitle')}</p>
            {mappingRulesLimit != null && (
              <p className="mt-2 text-xs text-slate-600">
                {t('admin.meta_leads.field_mapping.plan_limit_status', {
                  values: { count: fieldMappingRows.length, limit: mappingRulesLimit },
                })}
              </p>
            )}
            <p className="mt-2 text-xs text-slate-500">{t('admin.meta_leads.field_mapping.rules_hint')}</p>
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
                          className="input w-full min-w-[180px] text-xs font-mono"
                          list="meta-mapping-target-presets"
                          value={row.qualifiedFieldCode || row.target}
                          onChange={(event) => {
                            const v = event.target.value.trim()
                            const qualified = isQualifiedFieldCode(v)
                              ? v
                              : qualifiedCodeFromLegacyTarget(v)
                            const legacy = qualified
                              ? legacyTargetFromQualified(qualified)
                              : v
                            setFieldMappingRows((prev) =>
                              prev.map((r) =>
                                r.id === row.id
                                  ? {
                                      ...r,
                                      qualifiedFieldCode: qualified,
                                      target: legacy,
                                    }
                                  : r,
                              ),
                            )
                          }}
                          placeholder="recruitment.candidate.contacts.email"
                          aria-label={t('admin.meta_leads.field_mapping.col_target')}
                        />
                        {row.qualifiedFieldCode && row.target && row.qualifiedFieldCode !== row.target ? (
                          <p className="mt-1 text-[10px] text-slate-500">
                            legacy: <code>{row.target}</code>
                          </p>
                        ) : null}
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
            <button type="button" onClick={() => void handleSaveFieldMapping()} className="btn-primary mt-4">
              {selectedFormKey === META_FORM_TENANT_DEFAULT_KEY
                ? t('admin.meta_leads.field_mapping.save_tenant')
                : t('admin.meta_leads.field_mapping.save_form')}
            </button>
          </div>
        </section>
      )}

      {tab === 'debug' && metaConnected && (
        <div className="space-y-10">
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
                  className={`rounded-lg px-3 py-1 text-xs font-medium ${
                    active ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                  onClick={() => {
                    const n = new URLSearchParams(searchParams)
                    n.set('tab', 'debug')
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
                retryLabel={t('common.actions.refresh')}
                {...friendlyErrorBannerSecondary(incomingError, CRM_APP_PATHS.settingsIntegrationsMeta, t('admin.meta_leads.title'))}
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

        <section className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('admin.meta_leads.csv_import.title')}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('admin.meta_leads.csv_import.subtitle')}
          </p>
          {csvPanelError && (
            <div className="mt-3">
              <ErrorRecoveryBanner
                info={csvPanelError}
                onRetry={() => {
                  setCsvPanelError(null)
                  void handleCsvImport()
                }}
                retryLabel={t('common.actions.retry')}
                compact
              />
            </div>
          )}
          {me?.role !== 'administrator' ? (
            <p className="mt-4 text-sm text-amber-800">
              {t('admin.meta_leads.csv_import.admin_only')}
            </p>
          ) : (
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
              <label className="block text-sm text-slate-700">
                <span className="font-medium text-slate-800">
                  {t('admin.meta_leads.csv_import.file_label')}
                </span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="input mt-1 block w-full max-w-md"
                  disabled={csvBusy}
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    setCsvFile(f ?? null)
                    setCsvPanelError(null)
                  }}
                />
              </label>
              <button
                type="button"
                className="btn-primary shrink-0 disabled:opacity-50"
                disabled={csvBusy || !csvFile}
                onClick={() => void handleCsvImport()}
              >
                {csvBusy
                  ? t('admin.meta_leads.csv_import.uploading')
                  : t('admin.meta_leads.csv_import.upload_btn')}
              </button>
            </div>
          )}
          {csvLastJob && (
            <div className="mt-4 rounded border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800">
              <div className="font-medium">
                {t('admin.meta_leads.csv_import.last_job')}: {csvLastJob.filename}
              </div>
              <div className="mt-1">
                {t('admin.meta_leads.csv_import.last_job_status')}: <code>{csvLastJob.status}</code> ·{' '}
                {t('admin.meta_leads.csv_import.rows_ok')}: {csvLastJob.success_rows},{' '}
                {t('admin.meta_leads.csv_import.rows_dup')}: {csvLastJob.duplicate_rows},{' '}
                {t('admin.meta_leads.csv_import.rows_fail')}:{' '}
                {csvLastJob.failed_rows}
              </div>
              {csvLastJob.error_report && csvLastJob.error_report.length > 0 ? (
                <pre className="mt-2 max-h-40 overflow-auto rounded bg-slate-900 p-2 text-xs text-slate-100">
                  {JSON.stringify(csvLastJob.error_report, null, 2)}
                </pre>
              ) : null}
            </div>
          )}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-800">
              {t('admin.meta_leads.csv_import.recent')}
            </h3>
            <div className="mt-2 overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">
                      {t('admin.meta_leads.logs.table.created')}
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">
                      {t('admin.meta_leads.csv_import.col_file')}
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">
                      {t('admin.meta_leads.logs.table.status')}
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">
                      {t('admin.meta_leads.csv_import.col_counts')}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {csvJobs.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-3 py-3 text-slate-500">
                        {t('admin.meta_leads.csv_import.no_jobs')}
                      </td>
                    </tr>
                  ) : (
                    csvJobs.map((j) => (
                      <tr key={j.id}>
                        <td className="px-3 py-2 text-slate-600">{formatDateTime(j.created_at)}</td>
                        <td className="px-3 py-2 text-slate-800">{j.filename}</td>
                        <td className="px-3 py-2">{j.status}</td>
                        <td className="px-3 py-2">
                          {j.success_rows} / {j.duplicate_rows} / {j.failed_rows}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
          <p className="mt-4 text-sm">
            <Link className="text-brand-700 hover:underline" to={CRM_APP_PATHS.leads}>
              {t('admin.meta_leads.csv_import.open_leads')}
            </Link>
          </p>
        </section>

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
                        <div className="text-rose-500">{lead.error ?? '—'}</div>
                        {suggestion && (
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                            <span>{suggestion.hint}</span>
                            <button
                              type="button"
                              className="btn-secondary btn-xs"
                              onClick={() => setTabWithUrl(suggestion.tab)}
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
                            {t('admin.meta_leads.logs.actions.retry')}
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
        </div>
      )}

      {attachModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => !submitting && setAttachModal(null)}
        >
          <div
            className="rounded border border-slate-200 bg-white p-6 shadow-md"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-slate-900">
              {t('admin.meta_leads.unmapped.attach_modal_title', {
                values: { adId: attachModal.group.ad_id },
              })}
            </h3>
            <label className="mt-3 block text-sm text-slate-700">
              {t('admin.meta_leads.unmapped.select_vacancy')}
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
                {t('common.cancel')}
              </button>
              <button
                type="button"
                className="btn-primary disabled:opacity-50"
                onClick={() => void handleAttachUnmapped()}
                disabled={submitting || !attachModal.vacancyId.trim()}
              >
                {submitting ? t('common.loading') : t('admin.meta_leads.unmapped.attach_submit')}
              </button>
            </div>
          </div>
        </div>
      )}
    </SettingsSubpageHeader>
  )
}
