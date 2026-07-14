// src/pages/Companies.tsx
import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api, getOnboardingStatus, getOwnCompany, patchOwnCompany } from '../api/client'
import { recordTtvStepCompleted } from '../api/analytics'
import type { Company, CompanyReadiness } from '../api/types'
import { listAdminUsers } from '../api/users'
import type { AdminUser } from '../api/types'
import { useI18n } from '../i18n'
import {
  listDocumentPolicies,
  createDocumentPolicy,
  updateDocumentPolicy,
  deleteDocumentPolicy,
  type DocumentPolicy,
  type DocumentPolicyCreate,
  type DocumentPolicyScope,
} from '../api/documents/policies'
import { getDocumentTypes, type DocType } from '../api/documents/catalog'
import {
  ENABLE_READINESS,
  READINESS_STATE_META,
  FIN_STATUS_LABELS,
  CURRENCY_OPTIONS,
  FIN_STATUS_OPTIONS,
  CONTACT_ROLE_OPTIONS,
  WORK_MODE_OPTIONS,
  TRAILER_TYPE_KEYS,
  type StatusTone,
} from '../modules/companies/constants'
import type {
  AnyRecord,
  AddressForm,
  RepresentativeForm,
  ContactForm,
  BankAccountForm,
  PortalUserForm,
  WebhookForm,
  ContractForm,
  OrderForm,
  EInvoiceForm,
  CompanyDetailForm,
  ContactInfo,
} from '../modules/companies/types'
import { ORDER_TYPE_OPTIONS } from '../modules/companies/types'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar, DataTable, type DataTableColumn } from '../components/layout'
import { IconChevronDown, IconLink } from '@tabler/icons-react'
import { servicesWorkspacePath } from '../modules/services/utils'
import {
  asRecord,
  asArray,
  mergeRecords,
  extractAddress,
  normalizeNumberString,
  normalizeStringArray,
  addressToPayload,
  normalizeContacts,
  normalizeContactRole,
  combinePhone,
} from '../modules/companies/utils'
import { ClientInvoicesBlock } from '../components/companies/ClientInvoicesBlock'
import { CompanyReceivablesOverview } from '../components/companies/CompanyReceivablesOverview'
import { CompanyServiceOrdersPanel } from '../components/companies/CompanyServiceOrdersPanel'
import { CompanyIntakeLinksPanel } from '../components/companies/CompanyIntakeLinksPanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { listVacancies } from '../api/vacancies'
import { listTenantLinks, getContactPolicy, type TenantLink } from '../api/tenantLinks'
import { AddClientModal } from '../components/clients/AddClientModal'
import { ClientAccessPanel } from '../components/clients/ClientAccessPanel'
import { ClientLeadOriginPanel } from '../components/clients/ClientLeadOriginPanel'
import { useCurrentTenantId } from '../contexts/CurrentTenant'
import { useAuth } from '../store/useAuth'
import { useToast } from '../components/Toast'

// Helper functions used only in this file
function parseBoolean(value: unknown, fallback = false): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') return ['true', '1', 'yes'].includes(value.toLowerCase())
  return fallback
}

function pruneEmpty(obj: AnyRecord): AnyRecord {
  const result: AnyRecord = {}
  Object.entries(obj).forEach(([key, value]) => {
    if (
      value === undefined ||
      value === null ||
      (typeof value === 'string' && value.trim().length === 0) ||
      (Array.isArray(value) && value.length === 0) ||
      (typeof value === 'object' && !Array.isArray(value) && Object.keys(value as AnyRecord).length === 0)
    ) {
      return
    }
    result[key] = value
  })
  return result
}

function normalizeCompanyKind(value: unknown): 'client' | 'counterparty' {
  const raw = String(value ?? '').trim().toLowerCase()
  if (raw === 'counterparty') return 'counterparty'
  return 'client'
}

function normalizeOperatingCompanyType(value: unknown): 'agency' | 'employer' | 'services' {
  const raw = String(value ?? '').trim().toLowerCase()
  if (raw === 'employer') return 'employer'
  if (raw === 'services') return 'services'
  return 'agency'
}

function getCompanyRoleFromAny(company: AnyRecord): 'operating' | 'client' {
  const extra = asRecord(company?.extra)
  const raw =
    extra.company_role ??
    extra.role ??
    extra.entity_role
  return String(raw ?? '').trim().toLowerCase() === 'operating' ? 'operating' : 'client'
}

function ownCompanyToCompany(own: AnyRecord): Company {
  const extra = asRecord(own?.extra)
  const businessType = normalizeOperatingCompanyType(extra.business_type)
  return {
    id: String(own?.id || '') as any,
    name: String(own?.name || '').trim(),
    legal_name: (own?.legal_name as string | null | undefined) ?? null,
    tax_id: (own?.tax_id as string | null | undefined) ?? null,
    phone: (own?.phone as string | null | undefined) ?? null,
    email: (own?.email as string | null | undefined) ?? null,
    website: (own?.website as string | null | undefined) ?? null,
    notes: (own?.notes as string | null | undefined) ?? null,
    is_archived: Boolean(own?.is_archived),
    country_code: (own?.country_code as string | null | undefined) ?? null,
    country: (own?.country as string | null | undefined) ?? null,
    city: (own?.city as string | null | undefined) ?? null,
    address: (own?.address as string | null | undefined) ?? null,
    contacts: asRecord(own?.contacts),
    extra: {
      ...extra,
      company_role: 'operating',
      company_kind: 'counterparty',
      company_type: businessType,
    },
    created_at: (own?.created_at as string | null | undefined) ?? null,
    updated_at: (own?.updated_at as string | null | undefined) ?? null,
  } as Company
}

function getCompanyKindFromAny(company: AnyRecord): 'client' | 'counterparty' {
  const extra = asRecord(company?.extra)
  const raw =
    extra.company_kind ??
    extra.company_type ??
    extra.kind ??
    extra.entity_type ??
    extra.segment ??
    extra.role
  return normalizeCompanyKind(raw)
}

/** Client pipeline (Party CRM) — codes match API `client_stage`; labels from `app.companies.client_stage.*`. */
const CLIENT_PIPELINE_STAGE_CODES = [
  'new_lead',
  'contacted',
  'qualified',
  'offer_sent',
  'negotiation',
  'contract_signed',
  'active',
  'lost',
] as const

function formatPartyBusinessRoleCell(
  tr: (key: string, opts?: { defaultValue?: string }) => string,
  raw: string | null | undefined,
): string {
  if (!raw) return '—'
  const defaults: Record<string, string> = {
    employer: 'Employer',
    service_client: 'Service client',
    both: 'Employer + client',
  }
  return tr(`app.companies.party.roles.${raw}`, { defaultValue: defaults[raw] ?? raw })
}

function formatClientStageCell(
  tr: (key: string, opts?: { defaultValue?: string }) => string,
  raw: string | null | undefined,
): string {
  if (!raw) return '—'
  return tr(`app.companies.client_stage.${raw}`, { defaultValue: raw.replace(/_/g, ' ') })
}

const CLIENT_WORKSPACE_TABS = ['overview', 'orders', 'invoices', 'activity', 'profile'] as const
type ClientWorkspaceTab = (typeof CLIENT_WORKSPACE_TABS)[number]

export default function Companies(){
  const { t } = useI18n()
  const { me } = useAuth()
  const { notify } = useToast()
  const currentTenantId = useCurrentTenantId()
  const tenantIdForLinks = (currentTenantId ?? (me as { tenant_id?: string } | null)?.tenant_id ?? '').trim()
  const planLimitModal = usePlanLimitModal()
  const location = useLocation()
  const untitledNameRef = useRef(t('app.companies.detail.defaults.untitled'))
  useEffect(() => {
    untitledNameRef.current = t('app.companies.detail.defaults.untitled')
  }, [t])
  // router
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isOperatingProfileRoute = location.pathname.startsWith(CRM_APP_PATHS.myCompany)
  const sectionFocus = String(searchParams.get('section') || '').trim().toLowerCase()
  const showExtendedSections = String(searchParams.get('extended') || '').trim() === '1'
  const toggleExtendedSections = useCallback(() => {
    const next = new URLSearchParams(searchParams)
    if (showExtendedSections) next.delete('extended')
    else next.set('extended', '1')
    navigate(`${location.pathname}?${next.toString()}`, { replace: true })
  }, [location.pathname, navigate, searchParams, showExtendedSections])
  const handleCreateClientCompany = useCallback(() => {
    setAddClientOpen(true)
  }, [])
  const handleCreateOperatingCompany = useCallback(() => {
    navigate(CRM_APP_PATHS.onboardingCompany)
  }, [navigate])

  const rawClientWorkspaceTab = String(searchParams.get('ctab') || 'overview').trim().toLowerCase()
  const clientWorkspaceTab: ClientWorkspaceTab = CLIENT_WORKSPACE_TABS.includes(rawClientWorkspaceTab as ClientWorkspaceTab)
    ? (rawClientWorkspaceTab as ClientWorkspaceTab)
    : 'overview'

  const navigateClientWorkspaceTab = useCallback(
    (next: ClientWorkspaceTab) => {
      const nextParams = new URLSearchParams(searchParams)
      if (next === 'overview') nextParams.delete('ctab')
      else nextParams.set('ctab', next)
      const q = nextParams.toString()
      navigate(q ? `${location.pathname}?${q}` : location.pathname, { replace: true })
    },
    [navigate, location.pathname, searchParams],
  )

  // list state
  const [items, setItems] = useState<Company[]>([])
  const [companyUsers, setCompanyUsers] = useState<AdminUser[]>([])

  // detail state
  const [current, setCurrent] = useState<Company | null>(null)
  const [readiness, setReadiness] = useState<CompanyReadiness | null>(null)
  const [readinessLoading, setReadinessLoading] = useState(false)
  const [readinessError, setReadinessError] = useState<string | null>(null)
  const [readinessUnavailable, setReadinessUnavailable] = useState(false)

  // company vacancies (from API)
  const [companyVacanciesFromApi, setCompanyVacanciesFromApi] = useState<any[]>([])
  const [companyVacanciesLoading, setCompanyVacanciesLoading] = useState(false)
  // document policies state
  const [documentPolicies, setDocumentPolicies] = useState<DocumentPolicy[]>([])
  const [documentTypes, setDocumentTypes] = useState<DocType[]>([])
  const [policiesLoading, setPoliciesLoading] = useState(false)
  const [policiesError, setPoliciesError] = useState<FriendlyErrorInfo | null>(null)
  const [editingPolicy, setEditingPolicy] = useState<DocumentPolicy | null>(null)
  const [newPolicyMode, setNewPolicyMode] = useState(false)

  // ui state
  const [loading, setLoading] = useState(false)
  const [detailForm, setDetailForm] = useState<CompanyDetailForm | null>(null)
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [clientAccessLink, setClientAccessLink] = useState<TenantLink | null>(null)
  const [clientAccessLoading, setClientAccessLoading] = useState(false)
  const [addClientOpen, setAddClientOpen] = useState(false)
  const [tenantLinksByCompanyId, setTenantLinksByCompanyId] = useState<Map<string, TenantLink>>(new Map())

  // list filters/sort
  const [query, setQuery] = useState('')
  const [showArchived, setShowArchived] = useState(false)
  const [companyKindFilter, setCompanyKindFilter] = useState<'all' | 'client' | 'counterparty'>('all')
  const [sortBy, setSortBy] = useState<'name_asc' | 'name_desc' | 'city_asc' | 'city_desc'>('name_asc')
  const [partyRoleListFilter, setPartyRoleListFilter] = useState<'all' | 'employer' | 'service_client' | 'both' | 'unset'>(
    'all',
  )
  const [clientStageListFilter, setClientStageListFilter] = useState<string>('all')
  const [ownerListFilter, setOwnerListFilter] = useState<string>('all')

  const ownerUserLabelMap = useMemo(() => {
    const m = new Map<string, string>()
    companyUsers.forEach((u) => {
      const id = u.user_id
      if (!id) return
      const label = (u.full_name || '').trim() || u.email || id.slice(0, 8)
      m.set(id, label)
    })
    return m
  }, [companyUsers])

  const clientPipelineStageOptions = useMemo(
    () =>
      CLIENT_PIPELINE_STAGE_CODES.map((code) => ({
        value: code,
        label: t(`app.companies.client_stage.${code}`),
      })),
    [t],
  )

  const updateField = useCallback(
    <K extends keyof CompanyDetailForm, F extends keyof CompanyDetailForm[K]>(
      section: K,
      field: F,
      value: CompanyDetailForm[K][F]
    ) => {
      setDetailForm((prev) => {
        if (!prev) return prev
        setIsDirty(true)
        setSaveSuccess(false)
        return {
          ...prev,
          [section]: {
            ...prev[section],
            [field]: value,
          },
        }
      })
    },
    []
  )

  const updateFormState = useCallback(
    <K extends keyof CompanyDetailForm>(section: K, updater: (prev: CompanyDetailForm[K]) => CompanyDetailForm[K]) => {
      setDetailForm((prev) => {
        if (!prev) return prev
        setIsDirty(true)
        setSaveSuccess(false)
        return {
          ...prev,
          [section]: updater(prev[section]),
        }
      })
    },
    []
  )

  const filteredItems = useMemo(() => {
    let arr: any[] = Array.isArray(items) ? items : []
    arr = arr.filter((it: any) => getCompanyRoleFromAny(it) !== 'operating')
    if (!showArchived) arr = arr.filter((it:any) => !it.is_archived)
    if (companyKindFilter !== 'all') {
      arr = arr.filter((it: any) => getCompanyKindFromAny(it) === companyKindFilter)
    }
    if (partyRoleListFilter !== 'all') {
      if (partyRoleListFilter === 'unset') {
        arr = arr.filter((it: any) => !it.party_business_roles)
      } else {
        arr = arr.filter((it: any) => String(it.party_business_roles || '') === partyRoleListFilter)
      }
    }
    if (clientStageListFilter !== 'all') {
      arr = arr.filter((it: any) => String(it.client_stage || '') === clientStageListFilter)
    }
    if (ownerListFilter !== 'all') {
      arr = arr.filter((it: any) => String(it.owner_user_id || '') === ownerListFilter)
    }
    if (query.trim()){
      const q = query.trim().toLowerCase()
      arr = arr.filter((it:any) => (
        ((it.name || '') + ' ' + (it.legal_name || '') + ' ' + (it.city || '') + ' ' + (it.country_code || it.country || '')).toLowerCase().includes(q)
      ))
    }
    const get = (it:any, key:string) => (it?.[key] || '').toString().toLowerCase()
    if (sortBy === 'name_asc') arr = [...arr].sort((a,b)=> get(a,'name').localeCompare(get(b,'name')))
    if (sortBy === 'name_desc') arr = [...arr].sort((a,b)=> get(b,'name').localeCompare(get(a,'name')))
    if (sortBy === 'city_asc') arr = [...arr].sort((a,b)=> get(a,'city').localeCompare(get(b,'city')))
    if (sortBy === 'city_desc') arr = [...arr].sort((a,b)=> get(b,'city').localeCompare(get(a,'city')))
    return arr
  }, [
    items,
    showArchived,
    companyKindFilter,
    partyRoleListFilter,
    clientStageListFilter,
    ownerListFilter,
    query,
    sortBy,
  ])

  const currentAny: AnyRecord | null = current ? (current as unknown as AnyRecord) : null

  const extraData = useMemo(() => (currentAny ? asRecord(currentAny.extra) : {}), [currentAny])
  const profileBlock = useMemo(() => asRecord(extraData.profile), [extraData])

  const legalBlock = useMemo(
    () =>
      mergeRecords(
        asRecord(currentAny?.legal),
        asRecord(currentAny?.legal_entity),
        asRecord(extraData.legal),
        asRecord(extraData.legal_entity),
        asRecord(extraData.legalEntity),
        asRecord(profileBlock.legal),
        asRecord(profileBlock.legal_entity)
      ),
    [currentAny, extraData, profileBlock]
  )

  const billingBlock = useMemo(
    () =>
      mergeRecords(
        asRecord(extraData.billing),
        asRecord(extraData.billing_profile),
        asRecord(extraData.billingInfo),
        asRecord(extraData.invoicing),
        asRecord(profileBlock.billing),
        asRecord(profileBlock.billing_profile)
      ),
    [extraData, profileBlock]
  )

  const operationsBlock = useMemo(
    () =>
      mergeRecords(
        asRecord(extraData.operations),
        asRecord(extraData.operational),
        asRecord(extraData.operational_profile),
        asRecord(extraData.operationalProfile),
        asRecord(profileBlock.operations),
        asRecord(profileBlock.operational)
      ),
    [extraData, profileBlock]
  )

  const complianceBlock = useMemo(
    () =>
      mergeRecords(
        asRecord(extraData.compliance),
        asRecord(profileBlock.compliance),
        operationsBlock
      ),
    [extraData, profileBlock, operationsBlock]
  )

  const portalBlock = useMemo(
    () =>
      mergeRecords(
        asRecord(extraData.client_portal),
        asRecord(extraData.portal),
        asRecord(profileBlock.portal),
        asRecord(profileBlock.client_portal)
      ),
    [extraData, profileBlock]
  )

  const integrationsBlock = useMemo(
    () =>
      mergeRecords(
        asRecord(extraData.integrations),
        asRecord(profileBlock.integrations)
      ),
    [extraData, profileBlock]
  )

  const contactsList = useMemo(() => {
    const primary = normalizeContacts(currentAny?.contacts)
    const fallback = primary.length ? [] : normalizeContacts(extraData.contacts)
    if (primary.length === 0 && fallback.length === 0) return []
    const combined = [...primary, ...fallback]
    const seen = new Set<string>()
    const result: ContactInfo[] = []
    combined.forEach((contact, idx) => {
      const key = (contact.email && contact.email.toLowerCase()) || `${contact.full_name || ''}-${idx}`
      if (seen.has(key)) return
      seen.add(key)
      result.push(contact)
    })
    return result
  }, [currentAny, extraData])

  const authorizedRepresentatives = useMemo(
    () =>
      asArray(extraData.authorized_representatives ?? legalBlock.authorized_representatives).map((item) =>
        asRecord(item)
      ),
    [extraData, legalBlock]
  )

  const bankAccounts = useMemo(() => {
    const candidates = [
      asArray(extraData.bank_accounts),
      asArray(billingBlock.bank_accounts),
      asArray(asRecord(extraData.banking).accounts),
      asArray(asRecord(profileBlock.banking).accounts),
    ]
    const firstNonEmpty = candidates.find((list) => list.length > 0)
    return (firstNonEmpty ?? []).map((item) => asRecord(item))
  }, [extraData, billingBlock, profileBlock])

  const portalUsers = useMemo(
    () =>
      asArray(portalBlock.portal_roles ?? portalBlock.users ?? portalBlock.accounts).map((item) =>
        asRecord(item)
      ),
    [portalBlock]
  )

  const providerIds = useMemo(
    () => asArray(integrationsBlock.provider_ids ?? extraData.provider_ids ?? extraData.providerIds),
    [integrationsBlock, extraData]
  )

  const webhooks = useMemo(
    () => asArray(integrationsBlock.webhooks ?? extraData.webhooks).map((item) => asRecord(item)),
    [integrationsBlock, extraData]
  )

  const contractsList = useMemo(
    () => asArray(extraData.contracts ?? extraData.contracts_history ?? extraData.contract_history).map((item) => asRecord(item)),
    [extraData]
  )

  const ordersList = useMemo(
    () => asArray(extraData.company_orders ?? extraData.orders ?? extraData.order_history).map((item) => asRecord(item)),
    [extraData]
  )

  const loadCompanyVacancies = useCallback(async (companyId: string) => {
    if (!companyId) return
    setCompanyVacanciesLoading(true)
    try {
      const list = await listVacancies({ company_id: companyId, limit: 100 })
      setCompanyVacanciesFromApi(Array.isArray(list) ? list : (list as any)?.items ?? [])
    } catch {
      setCompanyVacanciesFromApi([])
    } finally {
      setCompanyVacanciesLoading(false)
    }
  }, [])

  const companyVacancies = useMemo(() => {
    if (companyVacanciesFromApi.length > 0) {
      return companyVacanciesFromApi.map((item) => asRecord(item))
    }
    return asArray(extraData.company_vacancies ?? extraData.vacancies ?? extraData.open_vacancies).map((item) =>
      asRecord(item)
    )
  }, [companyVacanciesFromApi, extraData])

  const vacancyAnalytics = useMemo(() => {
    if (!companyVacancies.length) {
      return { total: 0, statusRows: [] as Array<{ status: string; count: number }>, latest: [] as AnyRecord[] }
    }
    const statusCounter = new Map<string, number>()
    companyVacancies.forEach((vacancy) => {
      const rawStatus = String(vacancy.status ?? vacancy.stage ?? 'unknown').toLowerCase()
      statusCounter.set(rawStatus, (statusCounter.get(rawStatus) ?? 0) + 1)
    })
    const statusRows = Array.from(statusCounter.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
      .map(([status, count]) => ({ status, count }))
    const latest = [...companyVacancies]
      .sort((a, b) => {
        const aTime = Date.parse(a.updated_at ?? a.created_at ?? '') || 0
        const bTime = Date.parse(b.updated_at ?? b.created_at ?? '') || 0
        return bTime - aTime
      })
      .slice(0, 4)
    return { total: companyVacancies.length, statusRows, latest }
  }, [companyVacancies])

  const blockingOrders = useMemo(() => {
    if (!ordersList.length) return []
    return ordersList
      .map((order, index) => {
        const reasons: string[] = []
        const startsAt = order.starts_at ?? order.start ?? order.date_start
        const endsAt = order.ends_at ?? order.end ?? order.date_end
        const required = Number(order.required_drivers ?? order.drivers_required ?? order.slots ?? 0) || 0
        const hired = Number(order.hired_drivers ?? order.drivers_assigned ?? order.assigned ?? 0) || 0
        if (!startsAt || !endsAt) reasons.push('schedule')
        if (required && hired < required) reasons.push('capacity')
        if (!order.status || ['draft', 'pending', 'requested'].includes(String(order.status).toLowerCase())) {
          reasons.push('status')
        }
        const docsRequired = Number(order.required_documents ?? order.docs_required ?? 0) || 0
        const docsReady = Number(order.attachments_count ?? order.docs_ready ?? order.documents_ready ?? 0) || 0
        if (docsRequired > docsReady) reasons.push('documents')
        if (!reasons.length) return null
        const updatedAt = order.updated_at ?? order.ends_at ?? order.starts_at ?? order.created_at ?? null
        return {
          key: String(order.id ?? order.code ?? `order-${index}`),
          title: order.title ?? order.code ?? t('common.labels.unnamed'),
          status: order.status ?? null,
          reasons,
          updatedAt,
        }
      })
      .filter((entry): entry is { key: string; title: string; status: string | null; reasons: string[]; updatedAt: string | null } => Boolean(entry))
      .sort((a, b) => {
        const aTime = Date.parse(a.updatedAt ?? '') || 0
        const bTime = Date.parse(b.updatedAt ?? '') || 0
        return bTime - aTime
      })
      .slice(0, 4)
  }, [ordersList, t])


  const buildDetailForm = useCallback((): CompanyDetailForm | null => {
    if (!currentAny) return null
    const base: CompanyDetailForm['base'] = {
      name: (currentAny.name as string) ?? '',
      owner_user_id: (currentAny.owner_user_id as string) ?? '',
      manager_user_id: (currentAny.manager_user_id as string) ?? '',
      legal_name: (currentAny.legal_name as string) ?? '',
      company_kind: normalizeCompanyKind(
        extraData.company_kind ??
          extraData.company_type ??
          extraData.kind ??
          extraData.entity_type ??
          extraData.segment ??
          extraData.role
      ),
      tax_id: (currentAny.tax_id as string) ?? '',
      phone: (currentAny.phone as string) ?? '',
      email: (currentAny.email as string) ?? '',
      website: (currentAny.website as string) ?? '',
      notes: (currentAny.notes as string) ?? '',
      is_archived: Boolean(currentAny.is_archived),
      country_code: (currentAny.country_code ?? currentAny.country ?? '') as string,
      city: (currentAny.city as string) ?? '',
      address: (currentAny.address as string) ?? '',
      party_entity_type: currentAny.party_entity_type === 'person' ? 'person' : 'company',
      party_business_roles: (['employer', 'service_client', 'both'].includes(
        String(currentAny.party_business_roles || ''),
      )
        ? (currentAny.party_business_roles as CompanyDetailForm['base']['party_business_roles'])
        : ''),
      client_stage: (currentAny.client_stage as string) ?? '',
      client_source: (currentAny.client_source as string) ?? '',
    }

    const legal: CompanyDetailForm['legal'] = {
      reg_no:
        (legalBlock.reg_no as string | undefined) ??
        (legalBlock.regon as string | undefined) ??
        (legalBlock.krs as string | undefined) ??
        '',
      vat_eu: (legalBlock.vat_eu as string | undefined) ?? (legalBlock.vat as string | undefined) ?? '',
      established_at: (legalBlock.established_at as string | undefined) ?? (legalBlock.founded_at as string | undefined) ?? '',
      transport_license_number:
        (legalBlock.transport_license_number as string | undefined) ??
        (legalBlock.transport_license as string | undefined) ??
        '',
      insurance_policy_no:
        (legalBlock.insurance_policy_no as string | undefined) ??
        (legalBlock.insurance_policy_number as string | undefined) ??
        '',
      registered_address: extractAddress(legalBlock.registered_address ?? extraData.registered_address),
      operational_address: extractAddress(
        legalBlock.operational_address ?? extraData.operational_address ?? currentAny.address
      ),
      authorized_representatives: authorizedRepresentatives.map((rep) => {
        const data = asRecord(rep)
        return {
          full_name: (data.full_name ?? data.name ?? '') as string,
          role: (data.role ?? '') as string,
          email: (data.email ?? '') as string,
          phone: (data.phone ?? '') as string,
        }
      }),
    }

    const billing: CompanyDetailForm['billing'] = {
      default_currency:
        (billingBlock.default_currency as string | undefined) ??
        (extraData.default_currency as string | undefined) ??
        '',
      payment_terms_days:
        normalizeNumberString(
          billingBlock.payment_terms_days ??
            extraData.payment_terms_days ??
            (currentAny.payment_terms_days as unknown)
        ) || '',
      invoice_email:
        (billingBlock.invoice_email as string | undefined) ??
        (extraData.invoice_email as string | undefined) ??
        (currentAny.invoice_email as string | undefined) ??
        '',
      billing_address: extractAddress(billingBlock.billing_address ?? extraData.billing_address),
      einvoice_peppol: {
        participant_id:
          (billingBlock.einvoice_peppol?.participant_id as string | undefined) ??
          (extraData.einvoice_peppol?.participant_id as string | undefined) ??
          '',
        scheme:
          (billingBlock.einvoice_peppol?.scheme as string | undefined) ??
          (extraData.einvoice_peppol?.scheme as string | undefined) ??
          '',
      },
      bank_accounts: bankAccounts.map((acc) => {
        const data = asRecord(acc)
        return {
          bank_name: (data.bank_name ?? '') as string,
          iban: (data.iban ?? '') as string,
          swift_bic: (data.swift_bic ?? data.swift ?? '') as string,
          country: (data.country ?? '') as string,
          label: (data.label ?? '') as string,
          is_primary: Boolean(data.is_primary),
        }
      }),
    }

    const contacts: ContactForm[] = contactsList.length
      ? contactsList.map((contact) => ({
          role: normalizeContactRole(contact.role) ?? '',
          full_name: contact.full_name ?? '',
          email: contact.email ?? '',
          phone: contact.phone ?? '',
          is_primary: Boolean(contact.is_primary),
          is_portal_user: Boolean(contact.is_portal_user),
        }))
      : [
          {
            role: '',
            full_name: '',
            email: '',
            phone: '',
            is_primary: false,
            is_portal_user: false,
          },
        ]

    const trailersRecord = operationsBlock.trailers ?? {}

    const customFieldsBlock = operationsBlock.custom_fields ?? {}
    const operations: CompanyDetailForm['operations'] = {
      fleet_tractors: normalizeNumberString(
        operationsBlock.fleet_tractors ?? operationsBlock.tractors ?? operationsBlock.fleet?.tractors
      ),
      fleet_intl_perc: normalizeNumberString(
        operationsBlock.fleet_intl_perc ?? operationsBlock.fleet?.intl_perc
      ),
      fleet_local_perc: normalizeNumberString(
        operationsBlock.fleet_local_perc ?? operationsBlock.fleet?.local_perc
      ),
      drivers_total: normalizeNumberString(
        operationsBlock.drivers_total ?? operationsBlock.drivers ?? operationsBlock.fleet?.drivers
      ),
      has_adr_operations: parseBoolean(
        operationsBlock.has_adr_operations ?? operationsBlock.hasAdrOperations,
        false
      ),
      work_modes: normalizeStringArray(
        operationsBlock.work_modes ?? operationsBlock.workModes ?? operationsBlock.work_modes_options
      ),
      trailer_types: TRAILER_TYPE_KEYS.reduce<Record<string, string>>((acc, key) => {
        const value = trailersRecord?.[key]
        acc[key] = normalizeNumberString(value)
        return acc
      }, {}),
      lanes: {
        origins: normalizeStringArray(operationsBlock.lanes?.origins),
        destinations: normalizeStringArray(operationsBlock.lanes?.destinations),
      },
      cargo_types: normalizeStringArray(operationsBlock.cargo_types ?? operationsBlock.cargoTypes),
      languages: normalizeStringArray(operationsBlock.languages),
      preferred_nationalities: normalizeStringArray(
        operationsBlock.preferred_nationalities ?? operationsBlock.preferredNationalities
      ),
      team_size: normalizeNumberString(operationsBlock.team_size ?? operationsBlock.teamSize ?? ''),
      roles: (operationsBlock.roles ?? operationsBlock.role ?? '') as string,
      tech_stack: (operationsBlock.tech_stack ?? operationsBlock.techStack ?? '') as string,
      custom_fields: ['capacity', 'equipment', 'certifications', 'regions'].reduce<Record<string, string>>(
        (acc, key) => {
          acc[key] = String(customFieldsBlock[key] ?? '')
          return acc
        },
        {}
      ),
    }

    const compliance: CompanyDetailForm['compliance'] = {
      fin_check_status:
        (readiness?.fin_check_status as string | undefined) ??
        (complianceBlock.fin_check_status as string | undefined) ??
        'pending',
      aml_required: parseBoolean(complianceBlock.aml_required ?? complianceBlock.amlRequired, false),
      iso9001: parseBoolean(complianceBlock.iso9001, false),
      doc_valid_until:
        (complianceBlock.doc_valid_until as string | undefined) ??
        (complianceBlock.documents_valid_until as string | undefined) ??
        '',
      last_compliance_check_at:
        (complianceBlock.last_compliance_check_at as string | undefined) ??
        (complianceBlock.updated_at as string | undefined) ??
        '',
    }

    const portal: CompanyDetailForm['portal'] = {
      enabled: parseBoolean(
        portalBlock.enabled ?? portalBlock.client_portal_enabled ?? readiness?.client_portal_enabled,
        false
      ),
      url:
        (portalBlock.url as string | undefined) ??
        (portalBlock.client_portal_url as string | undefined) ??
        (portalBlock.link as string | undefined) ??
        (currentAny.client_portal_url as string | undefined) ??
        '',
      last_sync_at:
        (portalBlock.last_sync_at as string | undefined) ??
        (portalBlock.portal_last_sync as string | undefined) ??
        (portalBlock.updated_at as string | undefined) ??
        '',
      portal_roles: portalUsers.length
        ? portalUsers.map((user) => {
            const data = asRecord(user)
            return {
              full_name: (data.full_name ?? data.name ?? '') as string,
              email: (data.email ?? '') as string,
              role: (data.role ?? '') as string,
            }
          })
        : [
            {
              full_name: '',
              email: '',
              role: '',
            },
          ],
      permissions: (() => {
        const permissions = portalBlock.permissions
        if (!permissions) return ''
        if (typeof permissions === 'string') return permissions
        try {
          return JSON.stringify(permissions, null, 2)
        } catch {
          return ''
        }
      })(),
    }

    const integrations: CompanyDetailForm['integrations'] = {
      provider_ids: providerIds.length ? providerIds : [''],
      webhooks: webhooks.length
        ? webhooks.map((hook) => {
            const data = asRecord(hook)
            return {
              event: (data.event ?? '') as string,
              target: (data.target ?? '') as string,
            }
          })
        : [
            {
              event: '',
              target: '',
            },
          ],
      branding: {
        logo_url: (integrationsBlock.branding?.logo_url as string | undefined) ?? '',
        primary_color: (integrationsBlock.branding?.primary_color as string | undefined) ?? '',
      },
    }

    const contracts: ContractForm[] = contractsList.length
      ? contractsList.map((contract) => {
          const data = asRecord(contract)
          return {
            title: (data.title ?? data.name ?? '') as string,
            status: (data.status ?? '') as string,
            starts_at: (data.starts_at ?? '') as string,
            ends_at: (data.ends_at ?? '') as string,
            reference: (data.reference ?? data.client_reference ?? '') as string,
            code: (data.code ?? '') as string,
          }
        })
      : [
          {
            title: '',
            status: '',
            starts_at: '',
            ends_at: '',
            reference: '',
            code: '',
          },
        ]

    const orders: OrderForm[] = ordersList.length
      ? ordersList.map((order) => {
          const data = asRecord(order)
          const orderTypeId = (data.order_type_id ?? 'transport') as string
          const customFields = (data.custom_fields ?? {}) as Record<string, string | number>
          return {
            title: (data.title ?? data.name ?? '') as string,
            status: (data.status ?? '') as string,
            starts_at: (data.starts_at ?? '') as string,
            ends_at: (data.ends_at ?? '') as string,
            required_drivers: normalizeNumberString(
              data.required_drivers ?? data.drivers_required ?? data.target_drivers
            ),
            hired_drivers: normalizeNumberString(
              data.hired_drivers ?? data.drivers_hired ?? data.assigned_drivers
            ),
            client_reference: (data.client_reference ?? '') as string,
            code: (data.code ?? '') as string,
            order_type_id: orderTypeId,
            custom_fields: Object.keys(customFields).length ? customFields : undefined,
          }
        })
      : [
          {
            title: '',
            status: '',
            starts_at: '',
            ends_at: '',
            required_drivers: '',
            hired_drivers: '',
            client_reference: '',
            code: '',
            order_type_id: 'transport' as const,
            custom_fields: undefined,
          },
        ]

    let rawExtra: AnyRecord = {}
    try {
      rawExtra = JSON.parse(JSON.stringify(extraData ?? {}))
    } catch {
      rawExtra = asRecord(extraData)
    }
    rawExtra.operational_profile_type =
      (rawExtra.operational_profile_type as string) || (extraData.operational_profile_type as string) || 'transport'

    return {
      base,
      legal,
      billing,
      contacts,
      operations,
      compliance,
      portal,
      integrations,
      contracts,
      orders,
      rawExtra,
    }
  }, [
    authorizedRepresentatives,
    bankAccounts,
    contactsList,
    contractsList,
    currentAny,
    extraData,
    integrationsBlock,
    legalBlock,
    billingBlock,
    operationsBlock,
    complianceBlock,
    portalBlock,
    portalUsers,
    providerIds,
    readiness?.client_portal_enabled,
    readiness?.fin_check_status,
    ordersList,
    webhooks,
  ])

  const handleResetDetail = useCallback(() => {
    const built = buildDetailForm()
    setDetailForm(built)
    setIsDirty(false)
    setSaveError(null)
    setSaveSuccess(false)
  }, [buildDetailForm])

  const handleSave = useCallback(async () => {
    if (!detailForm || !currentAny) return
    setSaving(true)
    setSaveError(null)
    setSaveSuccess(false)
    try {
      const contactsPayload = detailForm.contacts.reduce<AnyRecord>((acc, contact, index) => {
        if (!contact.full_name && !contact.email && !contact.phone) return acc
        const normalizedRole = normalizeContactRole(contact.role)
        const entry = pruneEmpty({
          role: normalizedRole,
          full_name: contact.full_name || undefined,
          email: contact.email || undefined,
          phone: contact.phone || undefined,
          is_primary: contact.is_primary || undefined,
          is_portal_user: contact.is_portal_user || undefined,
        })
        if (!Object.keys(entry).length) return acc
        const roleKey = normalizedRole ? normalizedRole.toLowerCase() : ''
        const baseKey = roleKey ? roleKey.replace(/\s+/g, '_') : `contact_${index + 1}`
        let key = baseKey
        let suffix = 1
        while (acc[key]) {
          const fallback = roleKey || 'contact'
          key = `${fallback}_${suffix++}`
        }
        acc[key] = entry
        return acc
      }, {})

      const legalPayload = pruneEmpty({
        reg_no: detailForm.legal.reg_no || undefined,
        vat_eu: detailForm.legal.vat_eu || undefined,
        established_at: detailForm.legal.established_at || undefined,
        transport_license_number: detailForm.legal.transport_license_number || undefined,
        insurance_policy_no: detailForm.legal.insurance_policy_no || undefined,
        registered_address: addressToPayload(detailForm.legal.registered_address) || undefined,
        operational_address: addressToPayload(detailForm.legal.operational_address) || undefined,
        authorized_representatives: detailForm.legal.authorized_representatives
          .filter((rep) => rep.full_name || rep.email || rep.role)
          .map((rep) =>
            pruneEmpty({
              full_name: rep.full_name || undefined,
              email: rep.email || undefined,
              phone: rep.phone || undefined,
              role: rep.role || undefined,
            })
          ),
      })

      const bankAccountsPayload = detailForm.billing.bank_accounts
        .filter((acc) => acc.iban || acc.bank_name)
        .map((acc) =>
          pruneEmpty({
            bank_name: acc.bank_name || undefined,
            iban: acc.iban || undefined,
            swift_bic: acc.swift_bic || undefined,
            country: acc.country || undefined,
            label: acc.label || undefined,
            is_primary: acc.is_primary || undefined,
          })
        )

      const billingPayload = pruneEmpty({
        default_currency: detailForm.billing.default_currency || undefined,
        payment_terms_days: detailForm.billing.payment_terms_days
          ? Number(detailForm.billing.payment_terms_days)
          : undefined,
        invoice_email: detailForm.billing.invoice_email || undefined,
        billing_address: addressToPayload(detailForm.billing.billing_address) || undefined,
        einvoice_peppol: pruneEmpty({
          participant_id: detailForm.billing.einvoice_peppol.participant_id || undefined,
          scheme: detailForm.billing.einvoice_peppol.scheme || undefined,
        }),
        bank_accounts: bankAccountsPayload,
      })

      const profileType = detailForm.rawExtra?.operational_profile_type ?? 'transport'
      const ops = detailForm.operations
      const baseOps: AnyRecord = {
        fleet_tractors: ops.fleet_tractors ? Number(ops.fleet_tractors) : undefined,
        fleet_intl_perc: ops.fleet_intl_perc ? Number(ops.fleet_intl_perc) : undefined,
        fleet_local_perc: ops.fleet_local_perc ? Number(ops.fleet_local_perc) : undefined,
        drivers_total: ops.drivers_total ? Number(ops.drivers_total) : undefined,
        has_adr_operations: ops.has_adr_operations || undefined,
        work_modes: ops.work_modes?.length ? ops.work_modes : undefined,
        trailer_types: pruneEmpty(
          Object.fromEntries(
            Object.entries(ops.trailer_types || {}).map(([key, value]) => [
              key,
              value ? Number(value) : undefined,
            ])
          )
        ),
        lanes: pruneEmpty({
          origins: ops.lanes?.origins,
          destinations: ops.lanes?.destinations,
        }),
        cargo_types: ops.cargo_types?.length ? ops.cargo_types : undefined,
        languages: ops.languages?.length ? ops.languages : undefined,
        preferred_nationalities: ops.preferred_nationalities?.length ? ops.preferred_nationalities : undefined,
      }
      if (profileType === 'office') {
        baseOps.team_size = ops.team_size ? Number(ops.team_size) : undefined
        baseOps.roles = ops.roles?.trim() || undefined
        baseOps.tech_stack = ops.tech_stack?.trim() || undefined
      }
      if (profileType === 'custom') {
        const cf = Object.fromEntries(
          Object.entries(ops.custom_fields || {}).filter(([, v]) => v != null && String(v).trim())
        )
        if (Object.keys(cf).length > 0) baseOps.custom_fields = cf
      }
      const operationsPayload = pruneEmpty(baseOps)

      const compliancePayload = pruneEmpty({
        fin_check_status: detailForm.compliance.fin_check_status || undefined,
        aml_required: detailForm.compliance.aml_required || undefined,
        iso9001: detailForm.compliance.iso9001 || undefined,
        doc_valid_until: detailForm.compliance.doc_valid_until || undefined,
        last_compliance_check_at: detailForm.compliance.last_compliance_check_at || undefined,
      })

      let parsedPermissions: AnyRecord | string | undefined
      if (detailForm.portal.permissions.trim()) {
        try {
          parsedPermissions = JSON.parse(detailForm.portal.permissions)
        } catch {
          parsedPermissions = detailForm.portal.permissions
        }
      }

      const portalPayload = pruneEmpty({
        enabled: detailForm.portal.enabled || undefined,
        url: detailForm.portal.url || undefined,
        last_sync_at: detailForm.portal.last_sync_at || undefined,
        portal_roles: detailForm.portal.portal_roles
          .filter((role) => role.full_name || role.email)
          .map((role) =>
            pruneEmpty({
              full_name: role.full_name || undefined,
              email: role.email || undefined,
              role: role.role || undefined,
            })
          ),
        permissions: parsedPermissions,
      })

      const integrationsPayload = pruneEmpty({
        provider_ids: detailForm.integrations.provider_ids
          .map((id) => id.trim())
          .filter((id) => id.length > 0),
        webhooks: detailForm.integrations.webhooks
          .filter((hook) => hook.event || hook.target)
          .map((hook) =>
            pruneEmpty({
              event: hook.event || undefined,
              target: hook.target || undefined,
            })
          ),
        branding: pruneEmpty({
          logo_url: detailForm.integrations.branding.logo_url || undefined,
          primary_color: detailForm.integrations.branding.primary_color || undefined,
        }),
      })

      const contractsPayload = detailForm.contracts
        .filter((c) => c.title || c.code || c.status)
        .map((contract) =>
          pruneEmpty({
            title: contract.title || undefined,
            code: contract.code || undefined,
            status: contract.status || undefined,
            starts_at: contract.starts_at || undefined,
            ends_at: contract.ends_at || undefined,
            reference: contract.reference || undefined,
          })
        )

      const ordersPayload = detailForm.orders
        .filter((order) => order.title || order.status)
        .map((order) => {
          const base: AnyRecord = {
            title: order.title || undefined,
            code: order.code || undefined,
            status: order.status || undefined,
            starts_at: order.starts_at || undefined,
            ends_at: order.ends_at || undefined,
            client_reference: order.client_reference || undefined,
            order_type_id: order.order_type_id || 'transport',
          }
          if (order.order_type_id === 'transport') {
            base.required_drivers = order.required_drivers ? Number(order.required_drivers) : undefined
            base.hired_drivers = order.hired_drivers ? Number(order.hired_drivers) : undefined
          }
          if (order.custom_fields && Object.keys(order.custom_fields).length > 0) {
            base.custom_fields = order.custom_fields
          }
          return pruneEmpty(base)
        })

      const extraPayload: AnyRecord = {
        ...detailForm.rawExtra,
        company_kind: detailForm.base.company_kind,
        legal: legalPayload,
        billing: billingPayload,
        operations: operationsPayload,
        compliance: compliancePayload,
        client_portal: portalPayload,
        integrations: integrationsPayload,
        contracts: contractsPayload,
        company_orders: ordersPayload,
      }

      if (!Object.keys(legalPayload).length) delete extraPayload.legal
      if (!Object.keys(billingPayload).length) delete extraPayload.billing
      if (!Object.keys(operationsPayload).length) delete extraPayload.operations
      if (!Object.keys(compliancePayload).length) delete extraPayload.compliance
      if (!Object.keys(portalPayload).length) delete extraPayload.client_portal
      if (!Object.keys(integrationsPayload).length) delete extraPayload.integrations
      if (!contractsPayload.length) delete extraPayload.contracts
      if (!ordersPayload.length) delete extraPayload.company_orders

      const normalizeString = (value: string | null | undefined) => {
        if (value === undefined || value === null) return undefined
        const trimmed = value.trim()
        return trimmed.length > 0 ? trimmed : null
      }

      const payload: AnyRecord = {
        name: detailForm.base.name?.trim() || detailForm.base.name || '',
        owner_user_id: normalizeString(detailForm.base.owner_user_id),
        manager_user_id: normalizeString(detailForm.base.manager_user_id),
        legal_name: normalizeString(detailForm.base.legal_name),
        tax_id: normalizeString(detailForm.base.tax_id),
        phone: normalizeString(detailForm.base.phone),
        email: normalizeString(detailForm.base.email),
        website: normalizeString(detailForm.base.website),
        notes: normalizeString(detailForm.base.notes),
        country_code: normalizeString(detailForm.base.country_code),
        city: normalizeString(detailForm.base.city),
        address: normalizeString(detailForm.base.address),
        party_entity_type: detailForm.base.party_entity_type,
        party_business_roles: detailForm.base.party_business_roles
          ? detailForm.base.party_business_roles
          : null,
        client_stage: detailForm.base.client_stage?.trim() ? detailForm.base.client_stage.trim() : null,
        client_source: detailForm.base.client_source?.trim() ? detailForm.base.client_source.trim() : null,
      }

      Object.keys(payload).forEach((key) => {
        if (payload[key] === undefined) {
          delete payload[key]
        }
      })

      payload.is_archived = detailForm.base.is_archived

      payload.contacts = contactsPayload
      payload.extra = extraPayload

      if (isOperatingProfileRoute) {
        const ownPayload: AnyRecord = {
          name: payload.name,
          legal_name: payload.legal_name,
          tax_id: payload.tax_id,
          phone: payload.phone,
          email: payload.email,
          website: payload.website,
          notes: payload.notes,
          country_code: payload.country_code,
          city: payload.city,
          address: payload.address,
          is_archived: payload.is_archived,
          contacts: payload.contacts,
          extra: payload.extra,
        }
        await patchOwnCompany(String(currentAny.id), ownPayload)
      } else {
        await api.put(`/companies/${currentAny.id}`, payload)
      }
      await loadOne(currentAny.id as string)
      setIsDirty(false)
      setSaveSuccess(true)
    } catch (err: any) {
      console.error('[Companies] save failed', err)
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.companies.messages.save_error'))) {
        return
      }
      const detail = err?.response?.data?.detail
      let message = err?.message || t('app.companies.messages.save_error')
      if (typeof detail === 'string') {
        message = detail
      } else if (Array.isArray(detail)) {
        message = detail
          .map((item: any) =>
            typeof item === 'string'
              ? item
              : item?.msg
                ? `${item.msg}${item?.loc ? ` (${item.loc.join(' › ')})` : ''}`
                : JSON.stringify(item)
          )
          .join('; ')
      }
      setSaveError(message)
    } finally {
      setSaving(false)
    }
  }, [currentAny, detailForm, isOperatingProfileRoute, loadOne, planLimitModal, t])

  const setContactField = useCallback(
    (index: number, patch: Partial<ContactForm>) => {
      updateFormState('contacts', (prev) => {
        const next = [...prev]
        const patchCopy: Partial<ContactForm> = { ...patch }
        if (Object.prototype.hasOwnProperty.call(patchCopy, 'role')) {
          patchCopy.role = normalizeContactRole(patchCopy.role) ?? ''
        }
        next[index] = { ...next[index], ...patchCopy }
        return next
      })
    },
    [updateFormState]
  )

  const addContact = useCallback(() => {
    updateFormState('contacts', (prev) => [
      ...prev,
      { role: '', full_name: '', email: '', phone: '', is_primary: false, is_portal_user: false },
    ])
  }, [updateFormState])

  const removeContact = useCallback(
    (index: number) => {
      updateFormState('contacts', (prev) => {
        const next = prev.filter((_, i) => i !== index)
        return next.length
          ? next
          : [{ role: '', full_name: '', email: '', phone: '', is_primary: false, is_portal_user: false }]
      })
    },
    [updateFormState]
  )

  const setBankAccountField = useCallback(
    (index: number, patch: Partial<BankAccountForm>) => {
      updateFormState('billing', (prev) => {
        const next = [...prev.bank_accounts]
        next[index] = { ...next[index], ...patch }
        return { ...prev, bank_accounts: next }
      })
    },
    [updateFormState]
  )

  const addBankAccount = useCallback(() => {
    updateFormState('billing', (prev) => ({
      ...prev,
      bank_accounts: [
        ...prev.bank_accounts,
        { bank_name: '', iban: '', swift_bic: '', country: '', label: '', is_primary: false },
      ],
    }))
  }, [updateFormState])

  const removeBankAccount = useCallback(
    (index: number) => {
      updateFormState('billing', (prev) => {
        const next = prev.bank_accounts.filter((_, i) => i !== index)
        return {
          ...prev,
          bank_accounts: next.length
            ? next
            : [{ bank_name: '', iban: '', swift_bic: '', country: '', label: '', is_primary: false }],
        }
      })
    },
    [updateFormState]
  )

  const setRepresentativeField = useCallback(
    (index: number, patch: Partial<RepresentativeForm>) => {
      updateFormState('legal', (prev) => {
        const next = [...prev.authorized_representatives]
        next[index] = { ...next[index], ...patch }
        return { ...prev, authorized_representatives: next }
      })
    },
    [updateFormState]
  )

  const addRepresentative = useCallback(() => {
    updateFormState('legal', (prev) => ({
      ...prev,
      authorized_representatives: [...prev.authorized_representatives, { full_name: '', role: '', email: '', phone: '' }],
    }))
  }, [updateFormState])

  const removeRepresentative = useCallback(
    (index: number) => {
      updateFormState('legal', (prev) => {
        const next = prev.authorized_representatives.filter((_, i) => i !== index)
        return {
          ...prev,
          authorized_representatives: next.length ? next : [{ full_name: '', role: '', email: '', phone: '' }],
        }
      })
    },
    [updateFormState]
  )

  const setPortalUserField = useCallback(
    (index: number, patch: Partial<PortalUserForm>) => {
      updateFormState('portal', (prev) => {
        const next = [...prev.portal_roles]
        next[index] = { ...next[index], ...patch }
        return { ...prev, portal_roles: next }
      })
    },
    [updateFormState]
  )

  const addPortalUser = useCallback(() => {
    updateFormState('portal', (prev) => ({
      ...prev,
      portal_roles: [...prev.portal_roles, { full_name: '', email: '', role: '' }],
    }))
  }, [updateFormState])

  const removePortalUser = useCallback(
    (index: number) => {
      updateFormState('portal', (prev) => {
        const next = prev.portal_roles.filter((_, i) => i !== index)
        return { ...prev, portal_roles: next.length ? next : [{ full_name: '', email: '', role: '' }] }
      })
    },
    [updateFormState]
  )

  const setWebhookField = useCallback(
    (index: number, patch: Partial<WebhookForm>) => {
      updateFormState('integrations', (prev) => {
        const next = [...prev.webhooks]
        next[index] = { ...next[index], ...patch }
        return { ...prev, webhooks: next }
      })
    },
    [updateFormState]
  )

  const addWebhook = useCallback(() => {
    updateFormState('integrations', (prev) => ({
      ...prev,
      webhooks: [...prev.webhooks, { event: '', target: '' }],
    }))
  }, [updateFormState])

  const removeWebhook = useCallback(
    (index: number) => {
      updateFormState('integrations', (prev) => {
        const next = prev.webhooks.filter((_, i) => i !== index)
        return { ...prev, webhooks: next.length ? next : [{ event: '', target: '' }] }
      })
    },
    [updateFormState]
  )

  const setContractField = useCallback(
    (index: number, patch: Partial<ContractForm>) => {
      updateFormState('contracts', (prev) => {
        const next = [...prev]
        next[index] = { ...next[index], ...patch }
        return next
      })
    },
    [updateFormState]
  )

  const addContract = useCallback(() => {
    updateFormState('contracts', (prev) => [
      ...prev,
      { title: '', status: '', starts_at: '', ends_at: '', reference: '', code: '' },
    ])
  }, [updateFormState])

  const removeContract = useCallback(
    (index: number) => {
      updateFormState('contracts', (prev) => {
        const next = prev.filter((_, i) => i !== index)
        return next.length ? next : [{ title: '', status: '', starts_at: '', ends_at: '', reference: '', code: '' }]
      })
    },
    [updateFormState]
  )

  const setOrderField = useCallback(
    (index: number, patch: Partial<OrderForm>) => {
      updateFormState('orders', (prev) => {
        const next = [...prev]
        next[index] = { ...next[index], ...patch }
        return next
      })
    },
    [updateFormState]
  )

  const setOrderCustomField = useCallback(
    (index: number, key: string, value: string | number) => {
      updateFormState('orders', (prev) => {
        const next = [...prev]
        const ord = next[index]
        const cf = { ...(ord.custom_fields ?? {}), [key]: value }
        next[index] = { ...ord, custom_fields: cf }
        return next
      })
    },
    [updateFormState]
  )

  const addOrder = useCallback(() => {
    updateFormState('orders', (prev) => [
      ...prev,
      {
        title: '',
        status: '',
        starts_at: '',
        ends_at: '',
        required_drivers: '',
        hired_drivers: '',
        client_reference: '',
        code: '',
        order_type_id: 'transport' as const,
        custom_fields: undefined,
      },
    ])
  }, [updateFormState])

  const removeOrder = useCallback(
    (index: number) => {
      updateFormState('orders', (prev) => {
        const next = prev.filter((_, i) => i !== index)
        return next.length
          ? next
          : [
              {
                title: '',
                status: '',
                starts_at: '',
                ends_at: '',
                required_drivers: '',
                hired_drivers: '',
                client_reference: '',
                code: '',
                order_type_id: 'transport' as const,
                custom_fields: undefined,
              },
            ]
      })
    },
    [updateFormState]
  )
  // Derived UI: readiness checks (safe against null readiness)
  const readinessChecks = useMemo(() => {
    const r = (readiness ?? {}) as Partial<CompanyReadiness>
    return [
      { label: t('app.companies.readiness.checks.legal'), ok: Boolean(r.has_legal) },
      { label: t('app.companies.readiness.checks.contact'), ok: Boolean(r.has_primary_contact) },
      { label: t('app.companies.readiness.checks.billing'), ok: Boolean(r.billing_ready && r.has_primary_bank) },
      { label: t('app.companies.readiness.checks.compliance'), ok: Boolean(r.compliance_valid) },
      { label: t('app.companies.readiness.checks.portal'), ok: Boolean(r.client_portal_enabled) },
    ]
  }, [readiness, t])
  // -------- data fetching
  const loadDocumentPolicies = useCallback(async (companyId: string | null) => {
    if (!companyId) {
      setDocumentPolicies([])
      return
    }
    setPoliciesLoading(true)
    setPoliciesError(null)
    try {
      const [policies, types] = await Promise.all([
        listDocumentPolicies({ scope: 'CLIENT', scope_id: companyId }),
        getDocumentTypes(),
      ])
      setDocumentPolicies(policies)
      setDocumentTypes(types)
    } catch (err: any) {
      console.error('[Companies] failed to load document policies', err)
      const fb = t('app.companies.errors.policies_load_failed', { defaultValue: 'Failed to load document policies' })
      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
        setPoliciesError(getFriendlyErrorInfo(err, fb, t))
      }
    } finally {
      setPoliciesLoading(false)
    }
  }, [planLimitModal, t])

  const loadReadiness = useCallback(async (companyId: string) => {
    if (isOperatingProfileRoute) {
      setReadiness(null)
      setReadinessUnavailable(true)
      setReadinessError(null)
      return
    }
    if (!companyId) return
    setReadinessLoading(true)
    setReadinessError(null)
    setReadinessUnavailable(false)
    try {
      const { data } = await api.get(`/companies/${companyId}/readiness`)
      setReadiness(data)
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 404) {
        setReadinessUnavailable(true)
      } else if (status !== 401) {
        console.error('[Companies] readiness load failed', err)
        setReadinessError('load_failed')
      }
      setReadiness(null)
    } finally {
      setReadinessLoading(false)
    }
  }, [isOperatingProfileRoute])

  async function loadList(){
    setLoading(true)
    try{
      const { data } = await api.get('/companies/', {
        params: { include_service_metrics: true, include_recruitment_metrics: true },
      })
      const arr = Array.isArray(data) ? data : (data?.items || [])
      setItems(arr)
    } finally { setLoading(false) }
  }

  async function loadOne(companyId: string){
    setLoading(true)
    setReadiness(null)
    setReadinessUnavailable(false)
    setReadinessError(null)
    setCompanyVacanciesFromApi([])
    try{
      if (isOperatingProfileRoute) {
        const own = await getOwnCompany(companyId)
        setCurrent(ownCompanyToCompany(asRecord(own)))
        setReadiness(null)
        setReadinessUnavailable(true)
        setReadinessError(null)
        return
      }
      const { data } = await api.get(`/companies/${companyId}`, {
        params: { include_service_metrics: true, include_recruitment_metrics: true },
      })
      const role = getCompanyRoleFromAny(asRecord(data))
      if (isOperatingProfileRoute && role !== 'operating') {
        navigate(`${CRM_APP_PATHS.agencyClients}/${companyId}`, { replace: true })
        return
      }
      if (!isOperatingProfileRoute && role === 'operating') {
        navigate(`${CRM_APP_PATHS.myCompany}/${companyId}`, { replace: true })
        return
      }
      setCurrent(data)
      if (ENABLE_READINESS) {
        void loadReadiness(companyId)
      }
      void loadDocumentPolicies(companyId)
      void loadCompanyVacancies(companyId)
    } finally { setLoading(false) }
  }

  // kick off initial data load
  useEffect(() => {
    if (id && id !== 'new') {
      void loadOne(id)
    } else if (!id) {
      void loadList()
    }
  }, [id, isOperatingProfileRoute, navigate])

  useEffect(() => {
    if (isOperatingProfileRoute || !id || id === 'new' || !tenantIdForLinks) {
      setClientAccessLink(null)
      return
    }
    let cancelled = false
    ;(async () => {
      setClientAccessLoading(true)
      try {
        const links = await listTenantLinks(tenantIdForLinks)
        if (cancelled) return
        const match = links.find(
          (link) =>
            String(link.client_company_id || '').trim() === String(id).trim() ||
            String(link.handoff_include_company_id || '').trim() === String(id).trim(),
        )
        setClientAccessLink(match || null)
      } catch {
        if (!cancelled) {
          setClientAccessLink(null)
        }
      } finally {
        if (!cancelled) setClientAccessLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, isOperatingProfileRoute, tenantIdForLinks])

  useEffect(() => {
    if (isOperatingProfileRoute || !tenantIdForLinks) {
      setTenantLinksByCompanyId(new Map())
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const links = await listTenantLinks(tenantIdForLinks)
        if (cancelled) return
        const map = new Map<string, TenantLink>()
        for (const link of links) {
          const companyKey = String(link.client_company_id || '').trim()
          if (companyKey) map.set(companyKey, link)
        }
        setTenantLinksByCompanyId(map)
      } catch {
        if (!cancelled) setTenantLinksByCompanyId(new Map())
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isOperatingProfileRoute, tenantIdForLinks])

  useEffect(() => {
    if (isOperatingProfileRoute || id) return
    if (searchParams.get('add') === '1') {
      setAddClientOpen(true)
      const next = new URLSearchParams(searchParams)
      next.delete('add')
      const q = next.toString()
      navigate(q ? `${location.pathname}?${q}` : location.pathname, { replace: true })
    }
  }, [id, isOperatingProfileRoute, location.pathname, navigate, searchParams])

  useEffect(() => {
    if (!isOperatingProfileRoute && id === 'new') {
      navigate(`${CRM_APP_PATHS.clientsDirectory}?add=1`, { replace: true })
    }
  }, [id, isOperatingProfileRoute, navigate])

  const handleClientCreated = useCallback(
    async (link: TenantLink) => {
      setAddClientOpen(false)
      notify({
        title: t('app.clients.created_dynamic', {
          defaultValue: '{entity} added',
          values: { entity: link.company_name || t('app.nav.items.clients') },
        }),
        variant: 'success',
      })
      try {
        const status = await getOnboardingStatus()
        if (!status.steps.first_client_created) {
          void recordTtvStepCompleted({
            event: 'ttv_step',
            action: 'completed',
            step_key: 'first_client_created',
          })
        }
      } catch {
        // ignore onboarding/TTV errors
      }
      if (tenantIdForLinks) {
        try {
          const links = await listTenantLinks(tenantIdForLinks)
          const map = new Map<string, TenantLink>()
          for (const row of links) {
            const companyKey = String(row.client_company_id || '').trim()
            if (companyKey) map.set(companyKey, row)
          }
          setTenantLinksByCompanyId(map)
        } catch {
          // ignore list refresh errors
        }
      }
      const companyId = String(link.client_company_id || link.handoff_include_company_id || '').trim()
      if (companyId) {
        navigate(`${CRM_APP_PATHS.agencyClients}/${companyId}`)
        return
      }
      void loadList()
    },
    [loadList, navigate, notify, t, tenantIdForLinks],
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await listAdminUsers()
        if (!cancelled) {
          setCompanyUsers(Array.isArray(data) ? data.filter((user) => user.user_id && user.status !== 'invited') : [])
        }
      } catch (err) {
        console.error('[Companies] failed to load tenant users', err)
        if (!cancelled) setCompanyUsers([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // build detail form whenever current changes
  useEffect(() => {
    if (currentAny && id && id !== 'new') {
      const built = buildDetailForm()
      setDetailForm(built)
      setIsDirty(false)
      setSaveError(null)
      setSaveSuccess(false)
    }
    if (!id) {
      // list mode — ensure detail form is cleared
      setDetailForm(null)
    }
  }, [id, currentAny, buildDetailForm])

  useEffect(() => {
    if (!id || id === 'new' || !detailForm || !sectionFocus || !current) return
    const sectionToNodeId: Record<string, string> = {
      legal: 'section-legal',
      billing: 'section-billing',
      bank_accounts: 'section-bank-accounts',
      branding: 'section-branding',
    }
    const nodeId = sectionToNodeId[sectionFocus]
    if (!nodeId) return

    if (getCompanyRoleFromAny(asRecord(current)) !== 'operating') {
      const nextParams = new URLSearchParams(searchParams)
      nextParams.set('ctab', 'profile')
      const q = nextParams.toString()
      navigate(`${location.pathname}?${q}`, { replace: true })
    }

    const timer = window.setTimeout(() => {
      const element = document.getElementById(nodeId)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }, 120)
    return () => window.clearTimeout(timer)
  }, [id, detailForm, sectionFocus, current, searchParams, navigate, location.pathname])


  const pageContent = useMemo(() => {
  if (id){
    const readinessMeta = readiness?.readiness_state
      ? READINESS_STATE_META[readiness?.readiness_state] ?? {
          labelKey: 'app.companies.readiness.states.unknown',
          tone: 'info' as StatusTone,
        }
      : null
    const readinessScoreLabel =
      typeof readiness?.readiness_score === 'number'
        ? `${Math.round(readiness?.readiness_score)}%`
        : null

    const readinessSummaryBadges: Array<{ key: string; labelKey: string; tone: StatusTone }> = []
    if (readinessMeta) {
      readinessSummaryBadges.push({
        key: 'readiness_state',
        labelKey: readinessMeta.labelKey,
        tone: readinessMeta.tone,
      })
    }
    if (readinessScoreLabel) {
      readinessSummaryBadges.push({
        key: 'readiness_score',
        labelKey: 'app.companies.readiness.score',
        tone: 'info',
      })
    }
    if (readiness?.fin_check_status) {
      readinessSummaryBadges.push({
        key: 'fin_check',
        labelKey: 'app.companies.readiness.fin_status.label',
        tone:
          readiness?.fin_check_status === 'pass'
            ? 'success'
            : readiness?.fin_check_status === 'fail'
              ? 'danger'
              : 'warning',
      })
    }
    if (readinessLoading) {
      readinessSummaryBadges.push({
        key: 'loading',
        labelKey: 'app.companies.readiness.loading',
        tone: 'info',
      })
    }

    const handleReloadReadiness = () => {
      void loadReadiness(currentAny?.id ?? id)
    }

    if (!detailForm) {
      return (
        <PageShell>
          <PageShellHeader>
            <PageHeader breadcrumbCurrentLabel={t('common.loading')} kind="browse" />
          </PageShellHeader>
          <div className="mx-4 text-sm text-slate-500">{t('common.loading')}</div>
        </PageShell>
      )
    }

    const locationLine = [detailForm.base.country_code, detailForm.base.city].filter(Boolean).join(', ')

    const isOperatingCompany = getCompanyRoleFromAny(currentAny ?? {}) === 'operating'
    const showClientProfileEditor =
      isOperatingCompany ||
      (Boolean(id && id !== 'new') && !isOperatingCompany && clientWorkspaceTab === 'profile')

    const clientContactsCount = detailForm.contacts.filter((contact) =>
      Boolean(((contact.full_name || contact.email || contact.phone) ?? '').trim()),
    ).length
    const clientOrdersCount = detailForm.orders.filter((order) =>
      Boolean(((order.title || order.client_reference || order.status) ?? '').trim()),
    ).length
    const clientContractsCount = detailForm.contracts.filter((contract) =>
      Boolean(((contract.title || contract.reference || contract.status) ?? '').trim()),
    ).length

    const operatingCompanyType = normalizeOperatingCompanyType(
      detailForm.rawExtra?.company_type ?? detailForm.rawExtra?.company_kind,
    )

    const numeric = (value: string | number | null | undefined) => {
      if (value === null || value === undefined) return 0
      const num = Number(value)
      return Number.isFinite(num) ? num : 0
    }

    const findContactByRole = (roles: string[]) =>
      detailForm.contacts.find((contact) => (contact.role ? roles.includes(contact.role.toUpperCase()) : false))

    const primaryContactEntry = detailForm.contacts.find((contact) => contact.is_primary) ?? detailForm.contacts[0]
    const financeContactEntry = findContactByRole(['ACC', 'FM']) ?? detailForm.contacts.find((contact) => contact.role === 'OWNER')
    const invoiceEmail = detailForm.billing.invoice_email || detailForm.base.email || (currentAny?.email as string | undefined) || ''
    const upcomingContract = detailForm.contracts
      .map((contract) => ({
        contract,
        dueDate: contract.ends_at || contract.starts_at || '',
      }))
      .filter((item) => item.dueDate)
      .sort((a, b) => {
        const aTime = Date.parse(a.dueDate)
        const bTime = Date.parse(b.dueDate)
        return aTime - bTime
      })[0]

    const hasTransportOrders = detailForm.orders.some(
      (o) => (numeric(o.required_drivers) || numeric(o.hired_drivers)) > 0
    )
    const driverStats = detailForm.orders.reduce(
      (acc, order) => {
        acc.required += numeric(order.required_drivers)
        acc.hired += numeric(order.hired_drivers)
        return acc
      },
      { required: 0, hired: 0 }
    )
    const openDriverSlots = Math.max(driverStats.required - driverStats.hired, 0)

    const overviewCards = [
      {
        key: 'primary_contact',
        title: t('app.companies.detail.overview.primary_contact.title'),
        content: primaryContactEntry ? (
          <div className="space-y-1">
            <p className="text-base font-semibold text-slate-900">
              {primaryContactEntry.full_name || t('common.labels.not_available')}
            </p>
            {primaryContactEntry.role && (
              <p className="text-xs uppercase tracking-wide text-slate-500">{primaryContactEntry.role}</p>
            )}
            {primaryContactEntry.phone && <p>{primaryContactEntry.phone}</p>}
            {primaryContactEntry.email && <p>{primaryContactEntry.email}</p>}
          </div>
        ) : (
          <p className="text-sm text-slate-500">{t('app.companies.detail.overview.primary_contact.empty')}</p>
        ),
      },
      {
        key: 'finance_contact',
        title: t('app.companies.detail.overview.finance_contact.title'),
        content: financeContactEntry ? (
          <div className="space-y-1">
            <p className="text-base font-semibold text-slate-900">
              {financeContactEntry.full_name || t('common.labels.not_available')}
            </p>
            {financeContactEntry.role && (
              <p className="text-xs uppercase tracking-wide text-slate-500">{financeContactEntry.role}</p>
            )}
            {financeContactEntry.phone && <p>{financeContactEntry.phone}</p>}
            {financeContactEntry.email && <p>{financeContactEntry.email}</p>}
            {invoiceEmail && (
              <p className="text-xs text-slate-500">
                {t('app.companies.detail.overview.finance_contact.invoice_label', { values: { email: invoiceEmail } })}
              </p>
            )}
          </div>
        ) : invoiceEmail ? (
          <div className="space-y-1">
            <p className="text-base font-semibold text-slate-900">{invoiceEmail}</p>
            <p className="text-xs text-slate-500">{t('app.companies.detail.overview.finance_contact.invoice_only')}</p>
          </div>
        ) : (
          <p className="text-sm text-slate-500">{t('app.companies.detail.overview.finance_contact.empty')}</p>
        ),
      },
      {
        key: 'contracts',
        title: t('app.companies.detail.overview.contracts.title'),
        content: upcomingContract ? (
          <div className="space-y-1">
            <p className="text-base font-semibold text-slate-900">
              {upcomingContract.contract.title || t('common.labels.unnamed')}
            </p>
            {upcomingContract.contract.status && (
              <p className="text-xs uppercase tracking-wide text-slate-500">
                {upcomingContract.contract.status}
              </p>
            )}
            <p className="text-sm text-slate-600">
              {t('app.companies.detail.overview.contracts.due', {
                values: { date: fmtDate(upcomingContract.dueDate) },
              })}
            </p>
          </div>
        ) : (
          <p className="text-sm text-slate-500">{t('app.companies.detail.overview.contracts.empty')}</p>
        ),
      },
      ...(isOperatingCompany
        ? [
            {
              key: 'invoice_workspace',
              title: t('app.companies.detail.overview.invoice_workspace.title', { defaultValue: 'Invoicing workspace' }),
              content: (
                <div className="space-y-1">
                  <p className="text-sm text-slate-600">
                    {t('app.companies.detail.overview.invoice_workspace.subtitle', {
                      defaultValue: 'Create and manage invoices issued from this operating profile.',
                    })}
                  </p>
                  <Link to={CRM_APP_PATHS.invoices} className="text-sm text-brand-600 hover:underline">
                    {t('app.my_company.open_invoices', { defaultValue: 'Open invoices' })}
                  </Link>
                </div>
              ),
            },
          ]
        : [
            {
              key: 'orders_workspace',
              title: t('app.companies.detail.overview.orders_workspace.title', { defaultValue: 'Orders workspace' }),
              content: clientOrdersCount > 0 ? (
                <div className="space-y-1">
                  <p className="text-2xl font-semibold text-slate-900">{clientOrdersCount}</p>
                  <p className="text-xs text-slate-500">
                    {t('app.companies.detail.overview.orders_workspace.subtitle', {
                      defaultValue: 'Orders, contracts and invoices are managed in this card.',
                    })}
                  </p>
                  <button
                    type="button"
                    className="text-sm text-brand-600 hover:underline"
                    onClick={() => navigateClientWorkspaceTab('orders')}
                  >
                    {t('app.companies.detail.overview.orders_workspace.link', { defaultValue: 'Open orders section' })}
                  </button>
                  <div>
                    <Link
                      to={`${CRM_APP_PATHS.invoiceNew}?company_id=${currentAny?.id ?? ''}`}
                      className="text-sm text-brand-600 hover:underline"
                    >
                      {t('app.invoices.create', { defaultValue: 'Create Invoice' })}
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-sm text-slate-500">
                    {t('app.companies.detail.overview.orders_workspace.empty', {
                      defaultValue: 'No orders yet. Add order details below and issue first invoice.',
                    })}
                  </p>
                  <button
                    type="button"
                    className="text-sm text-brand-600 hover:underline"
                    onClick={() => navigateClientWorkspaceTab('orders')}
                  >
                    {t('app.companies.detail.overview.orders_workspace.link', { defaultValue: 'Open orders section' })}
                  </button>
                </div>
              ),
            },
            {
              key: 'receivables',
              title: t('app.companies.detail.overview.receivables.title'),
              content:
                currentAny?.id && String(currentAny.id) !== 'new' ? (
                  <CompanyReceivablesOverview companyId={String(currentAny.id)} />
                ) : (
                  <p className="text-sm text-slate-500">{t('app.companies.detail.overview.receivables.empty')}</p>
                ),
            },
          ]),
      ...(hasTransportOrders
        ? [
            {
              key: 'driver_slots',
              title: t('app.companies.detail.overview.driver_slots.title'),
              content: (
                <div className="space-y-1">
                  <p className="text-2xl font-semibold text-slate-900">{openDriverSlots}</p>
                  <p className="text-xs text-slate-500">
                    {t('app.companies.detail.overview.driver_slots.assigned', {
                      values: { hired: driverStats.hired, required: driverStats.required },
                    })}
                  </p>
                </div>
              ),
            },
          ]
        : []),
    ]

    return (
      <PageShell>
        <PageShellHeader>
          <PageHeader
            breadcrumbCurrentLabel={
              detailForm.base.name || t('app.companies.detail.header.fallback_name')
            }
            subtitle={
              <div className="flex flex-wrap items-center gap-2">
                {detailForm.base.legal_name ? <span>{detailForm.base.legal_name}</span> : null}
                {locationLine ? (
                  <>
                    {detailForm.base.legal_name ? <span className="text-slate-300">·</span> : null}
                    <span>{locationLine}</span>
                  </>
                ) : null}
                {!isOperatingCompany ? (
                  <>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {formatPartyBusinessRoleCell(t, detailForm.base.party_business_roles)}
                    </span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {formatClientStageCell(t, detailForm.base.client_stage)}
                    </span>
                  </>
                ) : null}
              </div>
            }
            secondaryActions={
              <>
                {isOperatingCompany ? (
                  <>
                    <Link to={CRM_APP_PATHS.invoiceNew} className="btn-secondary btn-sm">
                      {t('app.invoices.create', { defaultValue: 'Create Invoice' })}
                    </Link>
                    <Link to={CRM_APP_PATHS.settingsBilling} className="btn-secondary btn-sm">
                      {t('app.my_company.open_billing', { defaultValue: 'Open billing' })}
                    </Link>
                  </>
                ) : (
                  <Link
                    to={`${CRM_APP_PATHS.invoiceNew}?company_id=${currentAny?.id ?? ''}`}
                    className="btn-secondary btn-sm"
                  >
                    {t('app.invoices.create', { defaultValue: 'Create Invoice' })}
                  </Link>
                )}
                <button
                  className="btn-secondary btn-sm"
                  type="button"
                  onClick={handleResetDetail}
                  disabled={saving || !isDirty}
                >
                  {t('app.companies.detail.actions.reset')}
                </button>
              </>
            }
            primaryAction={
              <button
                className="btn-primary btn-sm"
                type="button"
                onClick={handleSave}
                disabled={!isDirty || saving}
              >
                {saving ? t('common.saving') : t('common.actions.save')}
              </button>
            }
          />
          {saveSuccess ? (
            <div className="mt-2 text-sm text-emerald-700">{t('app.companies.messages.save_success')}</div>
          ) : null}
          {saveError ? <div className="mt-2 text-sm text-rose-600">{saveError}</div> : null}
        </PageShellHeader>

        {!isOperatingCompany && id && id !== 'new' ? (
          <Toolbar>
            <div className="flex flex-wrap gap-2">
              {CLIENT_WORKSPACE_TABS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={`rounded-lg px-3 py-2 text-sm font-medium ${
                    clientWorkspaceTab === key
                      ? 'bg-slate-900 text-white'
                      : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  }`}
                  onClick={() => navigateClientWorkspaceTab(key)}
                >
                  {t(`app.companies.detail.workspace.tabs.${key}`)}
                </button>
              ))}
            </div>
          </Toolbar>
        ) : null}

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto">
        {!isOperatingCompany && id && id !== 'new' ? (
          <>
            {clientWorkspaceTab === 'overview' && (
              <>
                <ClientLeadOriginPanel companyExtra={asRecord(currentAny ?? {}).extra as Record<string, unknown> | undefined} />

                <SectionCard
                  title={t('app.clients.settings', { defaultValue: 'Access settings' })}
                  description={t('app.clients.settings_desc', {
                    defaultValue: 'Handoff, client portal, and contact attempt rules for this client.',
                  })}
                >
                  {tenantIdForLinks && id ? (
                    <ClientAccessPanel
                      tenantId={tenantIdForLinks}
                      companyId={id}
                      link={clientAccessLink}
                      loading={clientAccessLoading}
                      onLinkUpdated={(next) => {
                        setClientAccessLink(next)
                        if (next?.client_company_id) {
                          setTenantLinksByCompanyId((prev) => {
                            const map = new Map(prev)
                            map.set(next.client_company_id as string, next)
                            return map
                          })
                        }
                      }}
                      onNotify={notify}
                    />
                  ) : (
                    <p className="text-sm text-slate-500">{t('common.loading')}</p>
                  )}
                </SectionCard>

                <SectionCard
                  title={t('app.companies.detail.overview.title')}
                  description={t('app.companies.detail.overview.subtitle')}
                >
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {overviewCards.map((card) => (
                      <div
                        key={card.key}
                        className="rounded-xl border border-slate-100 bg-white/80 p-4 shadow-sm shadow-brand-900/5"
                      >
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{card.title}</p>
                        <div className="mt-2 text-sm text-slate-600">{card.content}</div>
                      </div>
                    ))}
                  </div>
                </SectionCard>

                <div className="grid gap-4 lg:grid-cols-2">
                  <SectionCard
                    title={t('app.companies.detail.widgets.vacancies.title')}
                    description={t('app.companies.detail.widgets.vacancies.subtitle')}
                  >
                    <div className="flex items-baseline justify-between">
                      <p className="text-sm text-slate-500">{t('app.companies.detail.widgets.vacancies.total')}</p>
                      <p className="text-3xl font-semibold text-slate-900">{vacancyAnalytics.total}</p>
                    </div>
                    {vacancyAnalytics.statusRows.length ? (
                      <ul className="divide-y divide-slate-100 text-sm text-slate-700">
                        {vacancyAnalytics.statusRows.map((row) => (
                          <li key={row.status} className="flex items-center justify-between py-2">
                            <span>{humanizeStatus(row.status) || t('app.companies.detail.widgets.vacancies.status_unknown')}</span>
                            <span className="font-semibold">{row.count}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-slate-500">{t('app.companies.detail.widgets.vacancies.empty')}</p>
                    )}
                    {vacancyAnalytics.latest.length > 0 && (
                      <div className="rounded-xl bg-slate-50/60 p-3">
                        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('app.companies.detail.widgets.vacancies.latest_title')}
                        </div>
                        <ul className="mt-2 space-y-2 text-sm">
                          {vacancyAnalytics.latest.map((vacancy, index) => {
                            const vacId = (vacancy.id as string) ?? (vacancy.code as string)
                            return (
                              <li key={vacId ?? `vacancy-${index}`} className="rounded-xl border border-slate-100 bg-white/80 p-3">
                                <div className="flex items-center justify-between gap-2">
                                  <Link
                                    to={
                                      vacId
                                        ? `${CRM_APP_PATHS.vacancies}/${vacId}`
                                        : CRM_APP_PATHS.vacancies
                                    }
                                    className="font-semibold text-slate-900 hover:text-brand-600 hover:underline"
                                  >
                                    {(vacancy.title as string) ?? (vacancy.position as string) ?? t('common.labels.unnamed')}
                                  </Link>
                                  <span className="text-xs text-slate-500">
                                    {fmtDateTime((vacancy.updated_at as string | undefined) ?? (vacancy.created_at as string | undefined))}
                                  </span>
                                </div>
                                <div className="mt-1 flex items-center justify-between gap-2">
                                  <span className="text-xs text-slate-500">
                                    {t('app.companies.detail.widgets.vacancies.status_label', {
                                      values: {
                                        status:
                                          humanizeStatus((vacancy.status as string | undefined) ?? (vacancy.stage as string | undefined)) ||
                                          t('app.companies.detail.widgets.vacancies.status_unknown'),
                                      },
                                    })}
                                  </span>
                                  {vacId && (
                                    <Link
                                      to={`${CRM_APP_PATHS.candidates}?view=kanban&vacancy=${vacId}`}
                                      className="text-xs font-medium text-brand-600 hover:underline"
                                    >
                                      {t('app.companies.detail.widgets.vacancies.pipeline_link', { defaultValue: 'Пайплайн' })}
                                    </Link>
                                  )}
                                </div>
                              </li>
                            )
                          })}
                        </ul>
                      </div>
                    )}
                  </SectionCard>

                  {blockingOrders.length > 0 && (
                    <SectionCard
                      title={t('app.companies.detail.widgets.blockers.title')}
                      description={t('app.companies.detail.widgets.blockers.subtitle')}
                      collapsible
                      defaultOpen={true}
                    >
                      <ul className="space-y-3 text-sm">
                        {blockingOrders.map((entry) => (
                          <li key={entry.key} className="rounded-xl border border-amber-100 bg-amber-50/50 p-3">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-slate-900">{entry.title}</span>
                              <span className="text-xs text-slate-500">{humanizeStatus(entry.status) || t('common.labels.not_available')}</span>
                            </div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {entry.reasons.map((reason) => (
                                <span
                                  key={`${entry.key}-${reason}`}
                                  className="inline-flex items-center rounded-lg bg-white/80 px-3 py-1 text-xs font-medium text-amber-700"
                                >
                                  {t(`app.companies.detail.widgets.blockers.reason.${reason}`)}
                                </span>
                              ))}
                            </div>
                            <div className="mt-1 text-xs text-slate-500">
                              {entry.updatedAt ? fmtDateTime(entry.updatedAt) : t('common.labels.not_available')}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </SectionCard>
                  )}
                </div>

                <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
                  <button
                    type="button"
                    className="font-medium text-brand-600 hover:underline"
                    onClick={() => navigateClientWorkspaceTab('profile')}
                  >
                    {t('app.companies.detail.workspace.open_profile')}
                  </button>
                  <span className="text-slate-500"> — {t('app.companies.detail.workspace.open_profile_hint')}</span>
                </div>
              </>
            )}

            {clientWorkspaceTab === 'orders' && (
              <div id="section-orders" className="space-y-4">
                <section className="card p-4">
                  <CompanyServiceOrdersPanel companyId={String(currentAny?.id ?? '')} />
                </section>
                <SectionCard
                  title={t('app.companies.detail.sections.orders.title')}
                  description={t('app.companies.detail.workspace.orders.crm_subtitle')}
                  collapsible
                  defaultOpen={true}
                >
                  <div className="space-y-4">
                    {detailForm.orders.map((order, index) => {
                      const orderTypeId = (order.order_type_id ?? 'transport') as string
                      const orderType = ORDER_TYPE_OPTIONS.find((o) => o.id === orderTypeId) ?? ORDER_TYPE_OPTIONS[0]
                      const isTransport = orderTypeId === 'transport'
                      const customFields = order.custom_fields ?? {}
                      return (
                        <div key={`order-${index}`} className="rounded-lg border border-slate-100 bg-slate-50/50 p-4 space-y-3">
                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6">
                            <TextField
                              label={t('app.companies.detail.fields.name')}
                              value={order.title}
                              onChange={(value) => setOrderField(index, { title: value })}
                            />
                            <div>
                              <label className="label">{t('app.companies.detail.sections.order_type', { defaultValue: 'Тип заявки' })}</label>
                              <select
                                className="input w-full"
                                value={orderTypeId}
                                onChange={(e) => setOrderField(index, { order_type_id: e.target.value as string })}
                              >
                                {ORDER_TYPE_OPTIONS.map((opt) => (
                                  <option key={opt.id} value={opt.id}>
                                    {t(opt.labelKey)}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <TextField
                              label={t('app.companies.detail.fields.status')}
                              value={order.status}
                              onChange={(value) => setOrderField(index, { status: value })}
                            />
                            <TextField
                              label={t('app.companies.detail.fields.date_start')}
                              value={order.starts_at}
                              onChange={(value) => setOrderField(index, { starts_at: value })}
                              placeholder={t('app.companies.detail.placeholders.date_ymd', { defaultValue: 'YYYY-MM-DD' })}
                            />
                            <TextField
                              label={t('app.companies.detail.fields.date_end')}
                              value={order.ends_at}
                              onChange={(value) => setOrderField(index, { ends_at: value })}
                              placeholder={t('app.companies.detail.placeholders.date_ymd', { defaultValue: 'YYYY-MM-DD' })}
                            />
                            <div className="flex items-end gap-2">
                              <TextField
                                label={t('app.companies.detail.fields.reference')}
                                value={order.client_reference}
                                onChange={(value) => setOrderField(index, { client_reference: value })}
                              />
                              <button className="btn-danger shrink-0" type="button" onClick={() => removeOrder(index)}>
                                {t('common.actions.delete')}
                              </button>
                            </div>
                          </div>
                          {isTransport && (
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                              <TextField
                                label={t('app.companies.detail.fields.required_drivers')}
                                value={order.required_drivers}
                                onChange={(value) => setOrderField(index, { required_drivers: value })}
                                type="number"
                              />
                              <TextField
                                label={t('app.companies.detail.fields.hired_drivers')}
                                value={order.hired_drivers}
                                onChange={(value) => setOrderField(index, { hired_drivers: value })}
                                type="number"
                              />
                            </div>
                          )}
                          {!isTransport && orderType.schema.length > 0 && (
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3">
                              {orderType.schema.map((field) => (
                                <TextField
                                  key={field.key}
                                  label={t(field.labelKey)}
                                  value={String(customFields[field.key] ?? '')}
                                  onChange={(value) =>
                                    setOrderCustomField(index, field.key, field.type === 'number' ? (Number(value) || 0) : value)
                                  }
                                  type={field.type === 'number' ? 'number' : 'text'}
                                />
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })}
                    <button className="btn-secondary" type="button" onClick={addOrder}>
                      {t('app.companies.detail.actions.add_order')}
                    </button>
                  </div>
                </SectionCard>
              </div>
            )}

            {clientWorkspaceTab === 'invoices' && (
              <section className="card p-4">
                <ClientInvoicesBlock
                  companyId={currentAny?.id ?? ''}
                  companyName={detailForm.base.name || t('app.companies.detail.defaults.untitled')}
                />
              </section>
            )}

            {clientWorkspaceTab === 'activity' && (
              <SectionCard
                title={t('app.companies.detail.workspace.activity.title')}
                description={t('app.companies.detail.workspace.activity.subtitle')}
              >
                <div className="space-y-4 text-sm text-slate-600">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {t('app.companies.detail.workspace.activity.created')}
                      </p>
                      <p className="mt-1">{fmtDateTime(currentAny?.created_at as string | undefined)}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {t('app.companies.detail.workspace.activity.updated')}
                      </p>
                      <p className="mt-1">{fmtDateTime(currentAny?.updated_at as string | undefined)}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link
                      className="btn-secondary btn-sm"
                      to={`${CRM_APP_PATHS.invoices}?company_id=${encodeURIComponent(String(currentAny?.id ?? ''))}`}
                    >
                      {t('app.companies.detail.workspace.activity.link_invoices')}
                    </Link>
                    <Link
                      className="btn-secondary btn-sm"
                      to={servicesWorkspacePath('orders', { companyId: String(currentAny?.id ?? '') })}
                    >
                      {t('app.companies.detail.workspace.activity.link_services')}
                    </Link>
                    <Link
                      className="btn-secondary btn-sm"
                      to={`${CRM_APP_PATHS.vacancies}?company=${encodeURIComponent(String(currentAny?.id ?? ''))}&page=1`}
                    >
                      {t('app.companies.detail.workspace.activity.link_vacancies')}
                    </Link>
                  </div>
                </div>
              </SectionCard>
            )}
          </>
        ) : null}

        {ENABLE_READINESS && showExtendedSections && !isOperatingCompany && (
          <SectionCard title={t('app.companies.readiness.title')}>
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="space-y-2 text-sm text-slate-600">
                <p>{t('app.companies.readiness.description')}</p>
                {readinessUnavailable && (
                  <p className="text-slate-500">{t('app.companies.readiness.unavailable')}</p>
                )}
                {readinessError && (
                  <p className="text-rose-600">
                    {t('app.companies.readiness.error')}{' '}
                    <button className="underline hover:no-underline" onClick={handleReloadReadiness} type="button">
                      {t('common.actions.retry')}
                    </button>
                  </p>
                )}
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                {readinessSummaryBadges.map((badge) => (
                  <StatusBadge key={badge.key} tone={badge.tone}>
                    {badge.key === 'readiness_score'
                      ? t(badge.labelKey, { values: { score: readinessScoreLabel ?? '0%' } })
                      : badge.key === 'fin_check'
                        ? t(badge.labelKey, {
                            values: { status: t(FIN_STATUS_LABELS[readiness?.fin_check_status ?? ''] ?? '', { defaultValue: readiness?.fin_check_status ?? '' }) },
                          })
                        : t(badge.labelKey)}
                  </StatusBadge>
                ))}
              </div>
            </div>
            {readinessChecks.length > 0 && <IndicatorList items={readinessChecks} />}
          </SectionCard>
        )}

        {showClientProfileEditor && (
        <>
        <SectionCard title={t('app.companies.detail.sections.base.title')}>
          <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
            {isOperatingCompany
              ? t('app.my_company.compact_hint', {
                  defaultValue:
                    'Operating profile: only company type, invoice/legal data and bank/payment details. Leads, ads, team, clients and candidates belong to this company.',
                })
              : t('app.companies.detail.compact_hint', {
                  defaultValue:
                    'Только базовые данные для фактуры, договора и контактов. Дополнительные поля скрыты в расширенных разделах.',
                })}
          </div>
          <FieldGrid cols={2}>
            <TextField
              label={t('app.companies.detail.fields.name')}
              value={detailForm.base.name}
              onChange={(value) => updateField('base', 'name', value)}
            />
            <TextField
              label={t('app.companies.detail.fields.legal_name')}
              value={detailForm.base.legal_name}
              onChange={(value) => updateField('base', 'legal_name', value)}
            />
            {isOperatingCompany ? (
              <SelectField
                label={t('app.my_company.company_type', { defaultValue: 'Company type' })}
                value={normalizeOperatingCompanyType(detailForm.rawExtra?.company_type ?? detailForm.rawExtra?.company_kind)}
                onChange={(value) =>
                  updateFormState('rawExtra', (prev) => ({
                    ...prev,
                    company_type: normalizeOperatingCompanyType(value),
                  }))
                }
                options={[
                  { value: 'agency', label: t('app.onboarding.company_type.agency', { defaultValue: 'Agency' }) },
                  { value: 'employer', label: t('app.onboarding.company_type.employer', { defaultValue: 'Employer' }) },
                  { value: 'services', label: t('app.onboarding.company_type.services', { defaultValue: 'Services' }) },
                ]}
              />
            ) : (
              <SelectField
                label={t('app.companies.detail.fields.company_kind', { defaultValue: 'Company type' })}
                value={detailForm.base.company_kind}
                onChange={(value) => updateField('base', 'company_kind', normalizeCompanyKind(value))}
                options={[
                  { value: 'client', label: t('app.companies.list.kind_client', { defaultValue: 'Client' }) },
                  { value: 'counterparty', label: t('app.companies.list.kind_counterparty', { defaultValue: 'Counterparty' }) },
                ]}
              />
            )}
            <TextField
              label={t('app.companies.detail.fields.tax_id')}
              value={detailForm.base.tax_id}
              onChange={(value) => updateField('base', 'tax_id', value)}
              mono
            />
            <TextField
              label={t('app.companies.detail.fields.phone')}
              value={detailForm.base.phone}
              onChange={(value) => updateField('base', 'phone', value)}
            />
            <TextField
              label={t('app.companies.detail.fields.email')}
              value={detailForm.base.email}
              onChange={(value) => updateField('base', 'email', value)}
            />
            <TextField
              label={t('app.companies.detail.fields.website')}
              value={detailForm.base.website}
              onChange={(value) => updateField('base', 'website', value)}
            />
          </FieldGrid>
          <TextareaField
            label={t('app.companies.detail.fields.notes', { defaultValue: 'Описание компании' })}
            value={detailForm.base.notes}
            onChange={(value) => updateField('base', 'notes', value)}
            rows={4}
          />
          {!isOperatingCompany && (
            <div className="mt-4 border-t border-slate-200 pt-4">
              <p className="mb-3 text-sm font-semibold text-slate-800">
                {t('app.companies.detail.sections.party_crm.title', { defaultValue: 'Party & client pipeline' })}
              </p>
              <p className="mb-3 text-xs text-slate-500">
                {t('app.companies.detail.sections.party_crm.hint', {
                  defaultValue: 'Recruiting vs service revenue: one Party record; roles and client stage drive CRM views.',
                })}
              </p>
              <FieldGrid cols={2}>
                <SelectField
                  label={t('app.companies.detail.fields.party_entity_type', { defaultValue: 'Entity type' })}
                  value={detailForm.base.party_entity_type}
                  onChange={(value) => updateField('base', 'party_entity_type', value as 'company' | 'person')}
                  options={[
                    { value: 'company', label: t('app.companies.party.entity.company', { defaultValue: 'Company' }) },
                    { value: 'person', label: t('app.companies.party.entity.person', { defaultValue: 'Person' }) },
                  ]}
                />
                <SelectField
                  label={t('app.companies.detail.fields.party_business_roles', { defaultValue: 'Business roles' })}
                  value={detailForm.base.party_business_roles || ''}
                  onChange={(value) =>
                    updateField(
                      'base',
                      'party_business_roles',
                      (value || '') as CompanyDetailForm['base']['party_business_roles'],
                    )
                  }
                  options={[
                    { value: '', label: '—' },
                    { value: 'employer', label: t('app.companies.party.roles.employer', { defaultValue: 'Employer' }) },
                    {
                      value: 'service_client',
                      label: t('app.companies.party.roles.service_client', { defaultValue: 'Service client' }),
                    },
                    { value: 'both', label: t('app.companies.party.roles.both', { defaultValue: 'Both' }) },
                  ]}
                />
                <SelectField
                  label={t('app.companies.detail.fields.client_stage', { defaultValue: 'Client stage' })}
                  value={detailForm.base.client_stage || ''}
                  onChange={(value) => updateField('base', 'client_stage', value)}
                  options={[
                    { value: '', label: '—' },
                    ...clientPipelineStageOptions.map((o) => ({ value: o.value, label: o.label })),
                  ]}
                />
                <TextField
                  label={t('app.companies.detail.fields.client_source', { defaultValue: 'Acquisition source' })}
                  value={detailForm.base.client_source}
                  onChange={(value) => updateField('base', 'client_source', value)}
                  placeholder={t('app.companies.detail.placeholders.client_source', {
                    defaultValue: 'ads, referral, manual…',
                  })}
                />
              </FieldGrid>
            </div>
          )}
        </SectionCard>

        {!isOperatingCompany && (
          <SectionCard
            title={t('app.companies.detail.sections.advanced_toggle.title', { defaultValue: 'Расширенные разделы' })}
            description={t('app.companies.detail.sections.advanced_toggle.description', {
              defaultValue: 'Operations, compliance, portal, integrations, document policies и system fields.',
            })}
          >
            <button className="btn-secondary" type="button" onClick={toggleExtendedSections}>
              {showExtendedSections
                ? t('app.companies.detail.sections.advanced_toggle.hide', { defaultValue: 'Скрыть расширенные разделы' })
                : t('app.companies.detail.sections.advanced_toggle.show', { defaultValue: 'Показать расширенные разделы' })}
            </button>
          </SectionCard>
        )}

        <div id="section-billing">
        <SectionCard title={t('app.companies.detail.sections.billing.title')}>
          <FieldGrid cols={3}>
            <SelectField
              label={t('app.companies.detail.fields.default_currency')}
              value={detailForm.billing.default_currency}
              onChange={(value) => updateFormState('billing', (prev) => ({ ...prev, default_currency: value }))}
              options={CURRENCY_OPTIONS}
            />
            <TextField
              label={t('app.companies.detail.fields.payment_terms')}
              value={detailForm.billing.payment_terms_days}
              onChange={(value) => updateFormState('billing', (prev) => ({ ...prev, payment_terms_days: value }))}
              type="number"
              placeholder="30"
            />
            <TextField
              label={t('app.companies.detail.fields.invoice_email')}
              value={detailForm.billing.invoice_email}
              onChange={(value) => updateFormState('billing', (prev) => ({ ...prev, invoice_email: value }))}
            />
          </FieldGrid>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <TextField
              label={t('app.companies.detail.fields.country')}
              value={detailForm.billing.billing_address.country ?? ''}
              onChange={(value) =>
                updateFormState('billing', (prev) => ({
                  ...prev,
                  billing_address: { ...prev.billing_address, country: value },
                }))
              }
            />
            <TextField
              label={t('app.companies.detail.fields.city')}
              value={detailForm.billing.billing_address.city ?? ''}
              onChange={(value) =>
                updateFormState('billing', (prev) => ({
                  ...prev,
                  billing_address: { ...prev.billing_address, city: value },
                }))
              }
            />
            <TextField
              label={t('app.companies.detail.fields.street')}
              value={detailForm.billing.billing_address.street ?? ''}
              onChange={(value) =>
                updateFormState('billing', (prev) => ({
                  ...prev,
                  billing_address: { ...prev.billing_address, street: value },
                }))
              }
            />
            <TextField
              label={t('app.companies.detail.fields.zip')}
              value={detailForm.billing.billing_address.zip ?? ''}
              onChange={(value) =>
                updateFormState('billing', (prev) => ({
                  ...prev,
                  billing_address: { ...prev.billing_address, zip: value },
                }))
              }
            />
          </div>
          <FieldGrid cols={2}>
            <TextField
              label={t('app.companies.detail.fields.peppol_participant')}
              value={detailForm.billing.einvoice_peppol.participant_id}
              onChange={(value) =>
                updateFormState('billing', (prev) => ({
                  ...prev,
                  einvoice_peppol: { ...prev.einvoice_peppol, participant_id: value },
                }))
              }
              mono
            />
            <TextField
              label={t('app.companies.detail.fields.peppol_scheme')}
              value={detailForm.billing.einvoice_peppol.scheme}
              onChange={(value) =>
                updateFormState('billing', (prev) => ({
                  ...prev,
                  einvoice_peppol: { ...prev.einvoice_peppol, scheme: value },
                }))
              }
            />
          </FieldGrid>
          <div id="section-bank-accounts" className="space-y-3">
            {detailForm.billing.bank_accounts.map((account, index) => (
              <div key={`bank-${index}`} className="grid grid-cols-1 gap-2 md:grid-cols-6">
                <TextField
                  label={t('app.companies.detail.fields.bank_name')}
                  value={account.bank_name}
                  onChange={(value) => setBankAccountField(index, { bank_name: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.iban')}
                  value={account.iban}
                  onChange={(value) => setBankAccountField(index, { iban: value })}
                  mono
                />
                <TextField
                  label={t('app.companies.detail.fields.swift')}
                  value={account.swift_bic}
                  onChange={(value) => setBankAccountField(index, { swift_bic: value })}
                  mono
                />
                <TextField
                  label={t('app.companies.detail.fields.country')}
                  value={account.country}
                  onChange={(value) => setBankAccountField(index, { country: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.label')}
                  value={account.label}
                  onChange={(value) => setBankAccountField(index, { label: value })}
                />
                <div className="flex flex-col justify-end gap-2">
                  <CheckboxField
                    label={t('app.companies.detail.fields.primary')}
                    checked={account.is_primary}
                    onChange={(value) => setBankAccountField(index, { is_primary: value })}
                  />
                  <button className="btn-danger" type="button" onClick={() => removeBankAccount(index)}>
                    {t('common.actions.delete')}
                  </button>
                </div>
              </div>
            ))}
            <button className="btn-secondary" type="button" onClick={addBankAccount}>
              {t('app.companies.detail.actions.add_bank_account')}
            </button>
          </div>
        </SectionCard>
        </div>

        {!isOperatingCompany && <SectionCard title={t('app.companies.detail.sections.contacts.title')}>
          <div className="space-y-3">
            {detailForm.contacts.map((contact, index) => (
              <div key={`contact-${index}`} className="grid grid-cols-1 gap-2 lg:grid-cols-6">
                <SelectField
                  label={t('app.companies.detail.fields.role')}
                  value={contact.role}
                  onChange={(value) => setContactField(index, { role: value })}
                  options={CONTACT_ROLE_OPTIONS}
                />
                <TextField
                  label={t('app.companies.detail.fields.full_name')}
                  value={contact.full_name}
                  onChange={(value) => setContactField(index, { full_name: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.email')}
                  value={contact.email}
                  onChange={(value) => setContactField(index, { email: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.phone')}
                  value={contact.phone}
                  onChange={(value) => setContactField(index, { phone: value })}
                />
                <div className="flex flex-col justify-end gap-2">
                  <CheckboxField
                    label={t('app.companies.detail.fields.primary_contact')}
                    checked={contact.is_primary}
                    onChange={(value) => setContactField(index, { is_primary: value })}
                  />
                  <CheckboxField
                    label={t('app.companies.detail.fields.portal_user')}
                    checked={contact.is_portal_user}
                    onChange={(value) => setContactField(index, { is_portal_user: value })}
                  />
                </div>
                <div className="flex items-end">
                  <button className="btn-danger" type="button" onClick={() => removeContact(index)}>
                    {t('common.actions.delete')}
                  </button>
                </div>
              </div>
            ))}
            <button className="btn-secondary" type="button" onClick={addContact}>
              {t('app.companies.detail.actions.add_contact')}
            </button>
          </div>
        </SectionCard>}

        {!isOperatingCompany && <div id="section-legal">
        <SectionCard title={t('app.companies.detail.sections.legal.title')} collapsible defaultOpen={sectionFocus === 'legal'}>
          <FieldGrid cols={3}>
            <TextField
              label={t('app.companies.detail.fields.reg_no')}
              value={detailForm.legal.reg_no}
              onChange={(value) => updateFormState('legal', (prev) => ({ ...prev, reg_no: value }))}
            />
            <TextField
              label={t('app.companies.detail.fields.vat_eu')}
              value={detailForm.legal.vat_eu}
              onChange={(value) => updateFormState('legal', (prev) => ({ ...prev, vat_eu: value }))}
              mono
            />
            <TextField
              label={t('app.companies.detail.fields.established_at')}
              value={detailForm.legal.established_at}
              onChange={(value) => updateFormState('legal', (prev) => ({ ...prev, established_at: value }))}
              placeholder={t('app.companies.detail.placeholders.date_ymd', { defaultValue: 'YYYY-MM-DD' })}
            />
            {(detailForm.rawExtra?.operational_profile_type ?? 'transport') === 'transport' && (
              <>
                <TextField
                  label={t('app.companies.detail.fields.transport_license')}
                  value={detailForm.legal.transport_license_number}
                  onChange={(value) =>
                    updateFormState('legal', (prev) => ({ ...prev, transport_license_number: value }))
                  }
                />
                <TextField
                  label={t('app.companies.detail.fields.insurance_policy')}
                  value={detailForm.legal.insurance_policy_no}
                  onChange={(value) =>
                    updateFormState('legal', (prev) => ({ ...prev, insurance_policy_no: value }))
                  }
                />
              </>
            )}
          </FieldGrid>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.companies.detail.groups.registered_address')}</div>
              <TextField
                label={t('app.companies.detail.fields.country')}
                value={detailForm.legal.registered_address.country ?? ''}
                onChange={(value) =>
                  updateFormState('legal', (prev) => ({
                    ...prev,
                    registered_address: { ...prev.registered_address, country: value },
                  }))
                }
              />
              <TextField
                label={t('app.companies.detail.fields.city')}
                value={detailForm.legal.registered_address.city ?? ''}
                onChange={(value) =>
                  updateFormState('legal', (prev) => ({
                    ...prev,
                    registered_address: { ...prev.registered_address, city: value },
                  }))
                }
              />
              <TextField
                label={t('app.companies.detail.fields.street')}
                value={detailForm.legal.registered_address.street ?? ''}
                onChange={(value) =>
                  updateFormState('legal', (prev) => ({
                    ...prev,
                    registered_address: { ...prev.registered_address, street: value },
                  }))
                }
              />
              <TextField
                label={t('app.companies.detail.fields.zip')}
                value={detailForm.legal.registered_address.zip ?? ''}
                onChange={(value) =>
                  updateFormState('legal', (prev) => ({
                    ...prev,
                    registered_address: { ...prev.registered_address, zip: value },
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.companies.detail.groups.operational_address')}</div>
              <TextField
                label={t('app.companies.detail.fields.country')}
                value={detailForm.legal.operational_address.country ?? ''}
                onChange={(value) =>
                  updateFormState('legal', (prev) => ({
                    ...prev,
                    operational_address: { ...prev.operational_address, country: value },
                  }))
                }
              />
              <TextField
                label={t('app.companies.detail.fields.city')}
                value={detailForm.legal.operational_address.city ?? ''}
                onChange={(value) =>
                  updateFormState('legal', (prev) => ({
                    ...prev,
                    operational_address: { ...prev.operational_address, city: value },
                  }))
                }
              />
              <TextField
                label={t('app.companies.detail.fields.street')}
                value={detailForm.legal.operational_address.street ?? ''}
                onChange={(value) =>
                  updateFormState('legal', (prev) => ({
                    ...prev,
                    operational_address: { ...prev.operational_address, street: value },
                  }))
                }
              />
              <TextField
                label={t('app.companies.detail.fields.zip')}
                value={detailForm.legal.operational_address.zip ?? ''}
                onChange={(value) =>
                  updateFormState('legal', (prev) => ({
                    ...prev,
                    operational_address: { ...prev.operational_address, zip: value },
                  }))
                }
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.companies.detail.groups.representatives')}
              </div>
              <button className="btn-secondary" type="button" onClick={addRepresentative}>
                {t('app.companies.detail.actions.add_representative')}
              </button>
            </div>
            <div className="space-y-3">
              {detailForm.legal.authorized_representatives.map((rep, index) => (
                <div key={`representative-${index}`} className="grid grid-cols-1 gap-2 md:grid-cols-5">
                  <TextField
                    label={t('app.companies.detail.fields.full_name')}
                    value={rep.full_name}
                    onChange={(value) => setRepresentativeField(index, { full_name: value })}
                  />
                  <TextField
                    label={t('app.companies.detail.fields.role')}
                    value={rep.role ?? ''}
                    onChange={(value) => setRepresentativeField(index, { role: value })}
                  />
                  <TextField
                    label={t('app.companies.detail.fields.email')}
                    value={rep.email ?? ''}
                    onChange={(value) => setRepresentativeField(index, { email: value })}
                  />
                  <TextField
                    label={t('app.companies.detail.fields.phone')}
                    value={rep.phone ?? ''}
                    onChange={(value) => setRepresentativeField(index, { phone: value })}
                  />
                  <div className="flex items-end">
                    <button className="btn-danger" type="button" onClick={() => removeRepresentative(index)}>
                      {t('common.actions.delete')}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>
        </div>}

        {!isOperatingCompany && showExtendedSections && (detailForm.rawExtra?.operational_profile_type ?? 'transport') !== 'none' && (
        <SectionCard
          title={t('app.companies.detail.sections.operations.title')}
          collapsible
          defaultOpen={false}
        >
          {(detailForm.rawExtra?.operational_profile_type ?? 'transport') === 'transport' && (
            <>
          <FieldGrid cols={3}>
            <TextField
              label={t('app.companies.detail.fields.fleet_tractors')}
              value={detailForm.operations.fleet_tractors}
              onChange={(value) => updateFormState('operations', (prev) => ({ ...prev, fleet_tractors: value }))}
              type="number"
            />
            <TextField
              label={t('app.companies.detail.fields.fleet_intl')}
              value={detailForm.operations.fleet_intl_perc}
              onChange={(value) => updateFormState('operations', (prev) => ({ ...prev, fleet_intl_perc: value }))}
              type="number"
            />
            <TextField
              label={t('app.companies.detail.fields.fleet_local')}
              value={detailForm.operations.fleet_local_perc}
              onChange={(value) => updateFormState('operations', (prev) => ({ ...prev, fleet_local_perc: value }))}
              type="number"
            />
          </FieldGrid>
          <FieldGrid cols={3}>
            <TextField
              label={t('app.companies.detail.fields.drivers_total')}
              value={detailForm.operations.drivers_total}
              onChange={(value) => updateFormState('operations', (prev) => ({ ...prev, drivers_total: value }))}
              type="number"
            />
            <CheckboxField
              label={t('app.companies.detail.fields.adr_operations')}
              checked={detailForm.operations.has_adr_operations}
              onChange={(value) => updateFormState('operations', (prev) => ({ ...prev, has_adr_operations: value }))}
            />
            <MultiCheckboxField
              label={t('app.companies.detail.fields.work_modes')}
              options={WORK_MODE_OPTIONS}
              values={detailForm.operations.work_modes}
              onChange={(values) => updateFormState('operations', (prev) => ({ ...prev, work_modes: values }))}
            />
          </FieldGrid>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.companies.detail.groups.trailer_types')}</div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {TRAILER_TYPE_KEYS.map((key) => (
                  <TextField
                    key={key}
                    label={key}
                    value={detailForm.operations.trailer_types[key] ?? ''}
                    onChange={(value) =>
                      updateFormState('operations', (prev) => ({
                        ...prev,
                        trailer_types: { ...prev.trailer_types, [key]: value },
                      }))
                    }
                    type="number"
                  />
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.companies.detail.groups.lanes')}</div>
              <ArrayInputField
                label={t('app.companies.detail.fields.lanes_origins')}
                values={detailForm.operations.lanes.origins}
                onChange={(values) =>
                  updateFormState('operations', (prev) => ({
                    ...prev,
                    lanes: { ...prev.lanes, origins: values },
                  }))
                }
                placeholder={t('app.companies.detail.placeholders.country_code_pl', { defaultValue: 'PL' })}
              />
              <ArrayInputField
                label={t('app.companies.detail.fields.lanes_destinations')}
                values={detailForm.operations.lanes.destinations}
                onChange={(values) =>
                  updateFormState('operations', (prev) => ({
                    ...prev,
                    lanes: { ...prev.lanes, destinations: values },
                  }))
                }
                placeholder={t('app.companies.detail.placeholders.country_code_fr', { defaultValue: 'FR' })}
              />
            </div>
          </div>
          <ArrayInputField
            label={t('app.companies.detail.fields.cargo_types')}
            values={detailForm.operations.cargo_types}
            onChange={(values) => updateFormState('operations', (prev) => ({ ...prev, cargo_types: values }))}
            placeholder={t('app.companies.detail.placeholders.cargo_type_adr', { defaultValue: 'ADR' })}
          />
          <ArrayInputField
            label={t('app.companies.detail.fields.languages')}
            values={detailForm.operations.languages}
            onChange={(values) => updateFormState('operations', (prev) => ({ ...prev, languages: values }))}
            placeholder={t('app.companies.detail.placeholders.language_pl', { defaultValue: 'pl' })}
          />
          <ArrayInputField
            label={t('app.companies.detail.fields.preferred_nationalities')}
            values={detailForm.operations.preferred_nationalities}
            onChange={(values) =>
              updateFormState('operations', (prev) => ({ ...prev, preferred_nationalities: values }))
            }
            placeholder={t('app.companies.detail.placeholders.country_code_pl', { defaultValue: 'PL' })}
          />
            </>
          )}
          {(detailForm.rawExtra?.operational_profile_type ?? 'transport') === 'office' && (
            <FieldGrid cols={3}>
              <TextField
                label={t('app.companies.detail.sections.operations_profile.office_fields.team_size')}
                value={detailForm.operations.team_size}
                onChange={(value) => updateFormState('operations', (prev) => ({ ...prev, team_size: value }))}
                type="number"
              />
              <TextField
                label={t('app.companies.detail.sections.operations_profile.office_fields.roles')}
                value={detailForm.operations.roles}
                onChange={(value) => updateFormState('operations', (prev) => ({ ...prev, roles: value }))}
                placeholder={t('app.companies.detail.placeholders.roles_example', { defaultValue: 'developer, manager, …' })}
              />
              <TextField
                label={t('app.companies.detail.sections.operations_profile.office_fields.tech_stack')}
                value={detailForm.operations.tech_stack}
                onChange={(value) => updateFormState('operations', (prev) => ({ ...prev, tech_stack: value }))}
                placeholder={t('app.companies.detail.placeholders.tech_stack_example', { defaultValue: 'React, Node.js, …' })}
              />
            </FieldGrid>
          )}
          {(detailForm.rawExtra?.operational_profile_type ?? 'transport') === 'custom' && (
            <FieldGrid cols={2}>
              <TextField
                label={t('app.companies.detail.sections.operations_profile.custom_fields.capacity')}
                value={detailForm.operations.custom_fields?.capacity ?? ''}
                onChange={(value) =>
                  updateFormState('operations', (prev) => ({
                    ...prev,
                    custom_fields: { ...(prev.custom_fields ?? {}), capacity: value },
                  }))
                }
              />
              <TextField
                label={t('app.companies.detail.sections.operations_profile.custom_fields.equipment')}
                value={detailForm.operations.custom_fields?.equipment ?? ''}
                onChange={(value) =>
                  updateFormState('operations', (prev) => ({
                    ...prev,
                    custom_fields: { ...(prev.custom_fields ?? {}), equipment: value },
                  }))
                }
              />
              <TextField
                label={t('app.companies.detail.sections.operations_profile.custom_fields.certifications')}
                value={detailForm.operations.custom_fields?.certifications ?? ''}
                onChange={(value) =>
                  updateFormState('operations', (prev) => ({
                    ...prev,
                    custom_fields: { ...(prev.custom_fields ?? {}), certifications: value },
                  }))
                }
              />
              <TextField
                label={t('app.companies.detail.sections.operations_profile.custom_fields.regions')}
                value={detailForm.operations.custom_fields?.regions ?? ''}
                onChange={(value) =>
                  updateFormState('operations', (prev) => ({
                    ...prev,
                    custom_fields: { ...(prev.custom_fields ?? {}), regions: value },
                  }))
                }
              />
            </FieldGrid>
          )}
        </SectionCard>
        )}

        {!isOperatingCompany && showExtendedSections && <SectionCard
          title={t('app.companies.detail.sections.advanced.title', { defaultValue: 'Расширенные настройки' })}
          description={t('app.companies.detail.sections.advanced.description', { defaultValue: 'Комплаенс, портал клиента, интеграции' })}
          collapsible
          defaultOpen={sectionFocus === 'branding'}
        >
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-3">{t('app.companies.detail.sections.compliance.title')}</h3>
              <FieldGrid cols={3}>
                <SelectField
                  label={t('app.companies.detail.fields.fin_check_status')}
                  value={detailForm.compliance.fin_check_status}
                  onChange={(value) => updateFormState('compliance', (prev) => ({ ...prev, fin_check_status: value }))}
                  options={FIN_STATUS_OPTIONS.map((status) => {
                    const statusKey = FIN_STATUS_LABELS[status]
                    return {
                      value: status,
                      label: statusKey ? t(statusKey) : status,
                    }
                  })}
                />
                <CheckboxField
                  label={t('app.companies.detail.fields.aml_required')}
                  checked={detailForm.compliance.aml_required}
                  onChange={(value) => updateFormState('compliance', (prev) => ({ ...prev, aml_required: value }))}
                />
                <CheckboxField
                  label={t('app.companies.detail.fields.iso9001')}
                  checked={detailForm.compliance.iso9001}
                  onChange={(value) => updateFormState('compliance', (prev) => ({ ...prev, iso9001: value }))}
                />
              </FieldGrid>
              <FieldGrid cols={2} className="mt-3">
                <TextField
                  label={t('app.companies.detail.fields.docs_valid_until')}
                  value={detailForm.compliance.doc_valid_until}
                  onChange={(value) => updateFormState('compliance', (prev) => ({ ...prev, doc_valid_until: value }))}
                  placeholder={t('app.companies.detail.placeholders.date_ymd', { defaultValue: 'YYYY-MM-DD' })}
                />
                <TextField
                  label={t('app.companies.detail.fields.last_check')}
                  value={detailForm.compliance.last_compliance_check_at}
                  onChange={(value) =>
                    updateFormState('compliance', (prev) => ({ ...prev, last_compliance_check_at: value }))
                  }
                  placeholder={t('app.companies.detail.placeholders.iso_datetime', { defaultValue: '2025-01-01T00:00:00Z' })}
                />
              </FieldGrid>
            </div>

            <div className="pt-4 border-t border-slate-100">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">{t('app.companies.detail.sections.portal.title')}</h3>
              <div className="space-y-3">
                <CheckboxField
                  label={t('app.companies.detail.fields.portal_enabled')}
                  checked={detailForm.portal.enabled}
                  onChange={(value) => updateFormState('portal', (prev) => ({ ...prev, enabled: value }))}
                />
                <TextField
                  label={t('app.companies.detail.fields.url')}
                  value={detailForm.portal.url}
                  onChange={(value) => updateFormState('portal', (prev) => ({ ...prev, url: value }))}
                  placeholder="https://portal.example.com"
                />
                <TextField
                  label={t('app.companies.detail.fields.last_sync')}
                  value={detailForm.portal.last_sync_at}
                  onChange={(value) => updateFormState('portal', (prev) => ({ ...prev, last_sync_at: value }))}
                  placeholder={t('app.companies.detail.placeholders.iso_datetime', { defaultValue: '2025-01-01T00:00:00Z' })}
                />
                <div className="space-y-3">
                  {detailForm.portal.portal_roles.map((user, index) => (
                    <div key={`portal-user-${index}`} className="grid grid-cols-1 gap-2 md:grid-cols-4">
                      <TextField
                        label={t('app.companies.detail.fields.full_name')}
                        value={user.full_name}
                        onChange={(value) => setPortalUserField(index, { full_name: value })}
                      />
                      <TextField
                        label={t('app.companies.detail.fields.email')}
                        value={user.email}
                        onChange={(value) => setPortalUserField(index, { email: value })}
                      />
                      <TextField
                        label={t('app.companies.detail.fields.role')}
                        value={user.role}
                        onChange={(value) => setPortalUserField(index, { role: value })}
                      />
                      <div className="flex items-end">
                        <button className="btn-danger" type="button" onClick={() => removePortalUser(index)}>
                          {t('common.actions.delete')}
                        </button>
                      </div>
                    </div>
                  ))}
                  <button className="btn-secondary" type="button" onClick={addPortalUser}>
                    {t('app.companies.detail.actions.add_portal_user')}
                  </button>
                </div>
                <TextareaField
                  label={t('app.companies.detail.fields.permissions')}
                  value={detailForm.portal.permissions}
                  onChange={(value) => updateFormState('portal', (prev) => ({ ...prev, permissions: value }))}
                  rows={4}
                  placeholder={t('app.companies.detail.placeholders.permissions_json', { defaultValue: '{"contracts": {"view": true}}' })}
                />
              </div>
            </div>

            <div id="section-branding" className="pt-4 border-t border-slate-100">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">{t('app.companies.detail.sections.integrations.title')}</h3>
          <ArrayInputField
            label={t('app.companies.detail.fields.provider_ids')}
            values={detailForm.integrations.provider_ids}
            onChange={(values) => updateFormState('integrations', (prev) => ({ ...prev, provider_ids: values }))}
            placeholder="11111111-2222-3333-4444-555555555555"
          />
          <FieldGrid cols={2}>
            <TextField
              label={t('app.companies.detail.fields.logo')}
              value={detailForm.integrations.branding.logo_url}
              onChange={(value) =>
                updateFormState('integrations', (prev) => ({
                  ...prev,
                  branding: { ...prev.branding, logo_url: value },
                }))
              }
            />
            <TextField
              label={t('app.companies.detail.fields.primary_color')}
              value={detailForm.integrations.branding.primary_color}
              onChange={(value) =>
                updateFormState('integrations', (prev) => ({
                  ...prev,
                  branding: { ...prev.branding, primary_color: value },
                }))
              }
              placeholder={t('app.companies.detail.placeholders.hex_color', { defaultValue: '#004b8d' })}
            />
          </FieldGrid>
          <div className="space-y-3">
            {detailForm.integrations.webhooks.map((hook, index) => (
              <div key={`webhook-${index}`} className="grid grid-cols-1 gap-2 md:grid-cols-3">
                <TextField
                  label={t('app.companies.detail.fields.event')}
                  value={hook.event}
                  onChange={(value) => setWebhookField(index, { event: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.target_url')}
                  value={hook.target}
                  onChange={(value) => setWebhookField(index, { target: value })}
                  placeholder="https://api.example.com/hooks"
                />
                <div className="flex items-end">
                  <button className="btn-danger" type="button" onClick={() => removeWebhook(index)}>
                    {t('common.actions.delete')}
                  </button>
                </div>
              </div>
            ))}
            <button className="btn-secondary" type="button" onClick={addWebhook}>
              {t('app.companies.detail.actions.add_webhook')}
            </button>
          </div>
            </div>
          </div>
        </SectionCard>}

        {!isOperatingCompany && <SectionCard
          title={t('app.companies.detail.sections.contracts.title')}
          collapsible
          defaultOpen={false}
        >
          <div className="space-y-3">
            {detailForm.contracts.map((contract, index) => (
              <div key={`contract-${index}`} className="grid grid-cols-1 gap-2 lg:grid-cols-6">
                <TextField
                  label={t('app.companies.detail.fields.name')}
                  value={contract.title}
                  onChange={(value) => setContractField(index, { title: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.status')}
                  value={contract.status}
                  onChange={(value) => setContractField(index, { status: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.date_start')}
                  value={contract.starts_at}
                  onChange={(value) => setContractField(index, { starts_at: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.date_end')}
                  value={contract.ends_at}
                  onChange={(value) => setContractField(index, { ends_at: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.reference')}
                  value={contract.reference}
                  onChange={(value) => setContractField(index, { reference: value })}
                />
                <div className="flex items-end">
                  <button className="btn-danger" type="button" onClick={() => removeContract(index)}>
                    {t('common.actions.delete')}
                  </button>
                </div>
              </div>
            ))}
            <button className="btn-secondary" type="button" onClick={addContract}>
              {t('app.companies.detail.actions.add_contract')}
            </button>
          </div>
        </SectionCard>}

        {!isOperatingCompany && showExtendedSections && <SectionCard
          title={t('app.companies.detail.sections.document_policies.title', { defaultValue: 'Document Policies' })}
          description={t('app.companies.detail.sections.document_policies.description', { defaultValue: 'Configure document requirements for this client' })}
          collapsible
          defaultOpen={false}
        >
          {policiesError && (
            <ErrorRecoveryBanner
              info={policiesError}
              onRetry={() => void loadDocumentPolicies(current?.id ?? null)}
              retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
              {...friendlyErrorBannerSecondary(
                policiesError,
                CRM_APP_PATHS.documents,
                t('app.nav.items.documents', { defaultValue: 'Documents' }),
              )}
              compact
            />
          )}
          {policiesLoading ? (
            <div className="text-sm text-slate-500">{t('common.loading')}</div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-600">
                  {t('app.companies.detail.sections.document_policies.count', {
                    values: { count: documentPolicies.length },
                    defaultValue: `${documentPolicies.length} policy(ies) configured`,
                  })}
                </p>
                <button
                  className="btn-primary text-sm"
                  type="button"
                  onClick={() => {
                    setNewPolicyMode(true)
                    setEditingPolicy(null)
                  }}
                >
                  {t('app.companies.detail.actions.add_policy', { defaultValue: 'Add Policy' })}
                </button>
              </div>
              {newPolicyMode && (
                <PolicyForm
                  documentTypes={documentTypes}
                  onSave={async (payload) => {
                    if (!current?.id) return
                    try {
                      setPoliciesError(null)
                      await createDocumentPolicy({
                        ...payload,
                        scope: 'CLIENT',
                        scope_id: current.id,
                      })
                      await loadDocumentPolicies(current.id)
                      setNewPolicyMode(false)
                    } catch (err: any) {
                      const fb = t('app.companies.errors.policy_create_failed', { defaultValue: 'Failed to create policy' })
                      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
                        setPoliciesError(getFriendlyErrorInfo(err, fb, t))
                      }
                    }
                  }}
                  onCancel={() => setNewPolicyMode(false)}
                  t={t}
                />
              )}
              {editingPolicy && (
                <PolicyForm
                  documentTypes={documentTypes}
                  policy={editingPolicy}
                  onSave={async (payload) => {
                    if (!current?.id) return
                    try {
                      setPoliciesError(null)
                      await updateDocumentPolicy(editingPolicy.id, {
                        ...payload,
                        scope: editingPolicy.scope,
                        scope_id: editingPolicy.scope_id,
                      })
                      await loadDocumentPolicies(current.id)
                      setEditingPolicy(null)
                    } catch (err: any) {
                      const fb = t('app.companies.errors.policy_update_failed', { defaultValue: 'Failed to update policy' })
                      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
                        setPoliciesError(getFriendlyErrorInfo(err, fb, t))
                      }
                    }
                  }}
                  onCancel={() => setEditingPolicy(null)}
                  t={t}
                />
              )}
              {!newPolicyMode && !editingPolicy && documentPolicies.length === 0 ? (
                <p className="text-sm text-slate-500">
                  {t('app.companies.detail.sections.document_policies.empty', { defaultValue: 'No document policies configured. Click "Add Policy" to create one.' })}
                </p>
              ) : null}
              {!newPolicyMode && !editingPolicy && documentPolicies.length > 0 && (
                <div className="space-y-3">
                  {documentPolicies.map((policy) => {
                    const docType = documentTypes.find((dt) => (dt.id || dt.code) === policy.document_type_id)
                    const docTypeName = docType?.name || docType?.code || policy.document_type_id
                    return (
                      <div key={policy.id} className="rounded-lg border border-slate-200 bg-white p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 space-y-2">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-slate-900">{docTypeName}</span>
                              {policy.required && (
                                <span className="rounded-lg bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                                  {t('app.companies.detail.sections.document_policies.required', { defaultValue: 'Required' })}
                                </span>
                              )}
                              {!policy.enabled && (
                                <span className="rounded-lg bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                                  {t('app.companies.detail.sections.document_policies.disabled', { defaultValue: 'Disabled' })}
                                </span>
                              )}
                            </div>
                            {policy.alert_days_before_expiry && (
                              <p className="text-xs text-slate-500">
                                {t('app.companies.detail.sections.document_policies.alert_days', {
                                  values: { days: policy.alert_days_before_expiry },
                                  defaultValue: `Alert ${policy.alert_days_before_expiry} days before expiry`,
                                })}
                              </p>
                            )}
                            {policy.notes && (
                              <p className="text-xs text-slate-500">{policy.notes}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              className="btn-secondary text-sm"
                              type="button"
                              onClick={() => setEditingPolicy(policy)}
                            >
                              {t('common.actions.edit')}
                            </button>
                            <button
                              className="btn-danger btn-sm"
                              type="button"
                              onClick={async () => {
                                if (!current?.id || !confirm(t('app.companies.detail.actions.delete_confirm', { defaultValue: 'Delete this policy?' }))) return
                                try {
                                  setPoliciesError(null)
                                  await deleteDocumentPolicy(policy.id)
                                  await loadDocumentPolicies(current.id)
                                } catch (err: any) {
                                  const fb = t('app.companies.errors.policy_delete_failed', { defaultValue: 'Failed to delete policy' })
                                  if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
                                    setPoliciesError(getFriendlyErrorInfo(err, fb, t))
                                  }
                                }
                              }}
                            >
                              {t('common.actions.delete')}
                            </button>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </SectionCard>}

        {!isOperatingCompany && showExtendedSections && <SectionCard title={t('app.companies.detail.sections.system.title')}>
          <FieldGrid cols={3}>
            <InfoItem label={t('app.companies.detail.fields.id')} value={(currentAny?.id as string | undefined) || '—'} mono />
            <InfoItem label={t('app.companies.detail.fields.created_at')} value={fmtDateTime(currentAny?.created_at as string | undefined)} />
            <InfoItem label={t('app.companies.detail.fields.updated_at')} value={fmtDateTime(currentAny?.updated_at as string | undefined)} />
          </FieldGrid>
        </SectionCard>}
        </>
        )}

        </div>
      </PageShell>
    )
  } else {
      setCurrent(null)
      setReadiness(null)
      setReadinessUnavailable(false)
      setReadinessError(null)
      void loadList()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    id,
    current,
    detailForm,
    isDirty,
    saving,
    saveError,
    saveSuccess,
    readiness,
    readinessLoading,
    readinessUnavailable,
    readinessError,
    t,
    clientWorkspaceTab,
    navigateClientWorkspaceTab,
  ])

  useEffect(() => {
    const built = buildDetailForm()
    setDetailForm(built)
    setIsDirty(false)
    setSaveError(null)
    setSaveSuccess(false)
  }, [buildDetailForm])

  // small util to format ISO datetimes coming from API
  function fmtDateTime(v?: string){
    if (!v) return '—'
    const d = new Date(v)
    if (Number.isNaN(d.getTime())) return v
    return d.toLocaleString()
  }

  function fmtDate(v?: string){
    if (!v) return '—'
    const d = new Date(v)
    if (Number.isNaN(d.getTime())) return v
    return d.toLocaleDateString()
  }

  // -------- editing helpers
  async function toggleArchive(company: Company){
    try{
      setLoading(true)
      const cid = (company as any).id
      const { data } = await api.get(`/companies/${cid}`)
      const full = data || {}
      const isArchived = Boolean(full.is_archived)
      if (isArchived) {
        await api.put(`/companies/${cid}`, { is_archived: false })
      } else {
        await api.delete(`/companies/${cid}`)
      }
      // refresh list or detail
      if (id){
        await loadOne(cid)
      } else {
        await loadList()
      }
    } catch (err){
      console.error(err)
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.companies.messages.archive_error'))) {
        alert(t('app.companies.messages.archive_error'))
      }
    } finally {
      setLoading(false)
    }
  }


  const clientColumns: DataTableColumn<any>[] = [
    {
      key: 'name',
      header: t('app.companies.list.table.headers.name'),
      cellClassName: 'font-medium text-brand-700',
      render: (it) => (it as any).name,
    },
    {
      key: 'access',
      header: t('app.clients.access_column', { defaultValue: 'Access' }),
      render: (it) => {
        const rowId = String((it as any).id)
        const accessLink = tenantLinksByCompanyId.get(rowId)
        const contactPolicy = accessLink ? getContactPolicy(accessLink) : null
        if (!accessLink) {
          return (
            <span className="badge bg-amber-50 text-amber-800">
              {t('app.clients.access_needs_setup', { defaultValue: 'Needs setup' })}
            </span>
          )
        }
        return contactPolicy?.enabled ? (
          <span className="badge bg-emerald-50 text-emerald-800">
            {t('app.clients.access_contact_on', { defaultValue: 'Contact tracking' })}
          </span>
        ) : (
          <span className="badge bg-slate-100 text-slate-700">
            {t('app.clients.access_ready', { defaultValue: 'Configured' })}
          </span>
        )
      },
    },
    {
      key: 'legal_name',
      header: t('app.companies.list.table.headers.legal_name'),
      render: (it) => (it as any).legal_name || '—',
    },
    {
      key: 'kind',
      header: t('app.companies.list.table.headers.kind', { defaultValue: 'Type' }),
      render: (it) =>
        getCompanyKindFromAny(it) === 'counterparty'
          ? t('app.companies.list.kind_counterparty', { defaultValue: 'Counterparty' })
          : t('app.companies.list.kind_client', { defaultValue: 'Client' }),
    },
    {
      key: 'party_role',
      header: t('app.companies.list.table.headers.party_role', { defaultValue: 'Party role' }),
      render: (it) => formatPartyBusinessRoleCell(t, (it as any).party_business_roles),
    },
    {
      key: 'stage',
      header: t('app.companies.list.table.headers.stage', { defaultValue: 'Stage' }),
      render: (it) => formatClientStageCell(t, (it as any).client_stage),
    },
    {
      key: 'owner',
      header: t('app.companies.list.table.headers.owner', { defaultValue: 'Owner' }),
      render: (it) =>
        (it as any).owner_user_id
          ? ownerUserLabelMap.get(String((it as any).owner_user_id)) ||
            String((it as any).owner_user_id).slice(0, 8)
          : '—',
    },
    {
      key: 'active_orders',
      header: t('app.companies.list.table.headers.active_orders', { defaultValue: 'Active orders' }),
      align: 'right',
      tabularNums: true,
      render: (it) =>
        (it as any).service_active_orders != null ? Number((it as any).service_active_orders) : '—',
    },
    {
      key: 'revenue',
      header: t('app.companies.list.table.headers.revenue', { defaultValue: 'Revenue (completed)' }),
      align: 'right',
      tabularNums: true,
      render: (it) =>
        (it as any).service_revenue_completed != null
          ? Number((it as any).service_revenue_completed).toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })
          : '—',
    },
    {
      key: 'vacancies',
      header: t('app.companies.list.table.headers.recruitment_vacancies', { defaultValue: 'Active vacancies' }),
      align: 'right',
      tabularNums: true,
      render: (it) => (
        <Link
          className="font-medium text-brand-700 hover:underline"
          to={`${CRM_APP_PATHS.vacancies}?company=${(it as any).id}`}
          onClick={(e) => e.stopPropagation()}
        >
          {(it as any).recruitment_vacancies_active != null
            ? Number((it as any).recruitment_vacancies_active)
            : '—'}
        </Link>
      ),
    },
    {
      key: 'candidates',
      header: t('app.companies.list.table.headers.recruitment_candidates', { defaultValue: 'Candidates' }),
      align: 'right',
      tabularNums: true,
      render: (it) => (
        <Link
          className="font-medium text-brand-700 hover:underline"
          to={CRM_APP_PATHS.candidates}
          onClick={(e) => e.stopPropagation()}
        >
          {(it as any).recruitment_candidates_total != null
            ? Number((it as any).recruitment_candidates_total)
            : '—'}
        </Link>
      ),
    },
    {
      key: 'country',
      header: t('app.companies.list.table.headers.country'),
      render: (it) => (it as any).country_code || (it as any).country || '—',
    },
    {
      key: 'city',
      header: t('app.companies.list.table.headers.city'),
      render: (it) => (it as any).city || '—',
    },
    {
      key: 'archived',
      header: t('app.companies.list.table.headers.archived'),
      render: (it) => ((it as any).is_archived ? t('common.words.yes') : t('common.words.no')),
      compact: true,
    },
  ]

  // ----- list view (без :id)
  const listView = (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={
            isOperatingProfileRoute
              ? t('app.companies.list.title')
              : t('app.companies.list.clients_title', { defaultValue: 'Clients' })
          }
          secondaryActions={
            isOperatingProfileRoute ? (
              <button className="btn-secondary btn-sm" onClick={handleCreateOperatingCompany}>
                {t('app.companies.actions.new_operating_company', { defaultValue: 'Create my company' })}
              </button>
            ) : undefined
          }
          primaryAction={
            <button className="btn-primary btn-sm" onClick={handleCreateClientCompany}>
              {t('app.companies.actions.new_client_company', { defaultValue: 'Add client company' })}
            </button>
          }
        />
      </PageShellHeader>

      {!isOperatingProfileRoute ? (
        <details className="group mx-4 mb-2 shrink-0 rounded-xl border border-slate-200/90 bg-white shadow-sm">
          <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <IconLink size={16} className="text-brand-700" />
            {t('app.companies.intake_links.summary', { defaultValue: 'Public intake links' })}
            <IconChevronDown size={16} className="ml-auto text-slate-400 transition-transform group-open:rotate-180" />
          </summary>
          <div className="border-t border-slate-200/80">
            <CompanyIntakeLinksPanel embedded />
          </div>
        </details>
      ) : null}

      <Toolbar>
        <div className="flex flex-wrap items-center gap-2">
          <input
            className="input min-h-[40px] min-w-[220px] flex-1 rounded-lg border-slate-200/90 bg-white py-2 text-sm shadow-sm focus:border-brand-400 focus:ring-2 focus:ring-brand-500/15"
            placeholder={t('app.companies.list.search_placeholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label={t('app.companies.list.search_label')}
          />
          <select
            className="input w-auto min-h-[40px] py-2 text-sm"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            aria-label={t('app.companies.list.sort_label')}
          >
            <option value="name_asc">{t('app.companies.list.sort_options.name_asc')}</option>
            <option value="name_desc">{t('app.companies.list.sort_options.name_desc')}</option>
            <option value="city_asc">{t('app.companies.list.sort_options.city_asc')}</option>
            <option value="city_desc">{t('app.companies.list.sort_options.city_desc')}</option>
          </select>
          <select
            className="input w-auto min-h-[40px] py-2 text-sm"
            value={companyKindFilter}
            onChange={(e) => setCompanyKindFilter((e.target.value as any) || 'all')}
            aria-label={t('app.companies.list.kind_label', { defaultValue: 'Company type' })}
          >
            <option value="all">{t('app.companies.list.kind_label', { defaultValue: 'Company type' })}</option>
            <option value="client">{t('app.companies.list.kind_client', { defaultValue: 'Client' })}</option>
            <option value="counterparty">{t('app.companies.list.kind_counterparty', { defaultValue: 'Counterparty' })}</option>
          </select>
          <select
            className="input w-auto min-h-[40px] py-2 text-sm"
            value={partyRoleListFilter}
            onChange={(e) => setPartyRoleListFilter(e.target.value as typeof partyRoleListFilter)}
            aria-label={t('app.companies.list.filters.party_role', { defaultValue: 'Party role' })}
          >
            <option value="all">{t('app.companies.list.filters.party_role', { defaultValue: 'Party role' })}</option>
            <option value="unset">{t('app.companies.list.filters.party_role_unset', { defaultValue: 'Not set' })}</option>
            <option value="employer">{t('app.companies.party.roles.employer', { defaultValue: 'Employer' })}</option>
            <option value="service_client">{t('app.companies.party.roles.service_client', { defaultValue: 'Service client' })}</option>
            <option value="both">{t('app.companies.party.roles.both', { defaultValue: 'Both' })}</option>
          </select>
          <select
            className="input w-auto min-h-[40px] py-2 text-sm"
            value={clientStageListFilter}
            onChange={(e) => setClientStageListFilter(e.target.value)}
            aria-label={t('app.companies.list.filters.client_stage', { defaultValue: 'Client stage' })}
          >
            <option value="all">{t('app.companies.list.filters.client_stage', { defaultValue: 'Client stage' })}</option>
            {clientPipelineStageOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            className="input w-auto min-h-[40px] py-2 text-sm"
            value={ownerListFilter}
            onChange={(e) => setOwnerListFilter(e.target.value)}
            aria-label={t('app.companies.list.filters.owner', { defaultValue: 'Owner' })}
          >
            <option value="all">{t('app.companies.list.filters.owner', { defaultValue: 'Owner' })}</option>
            {companyUsers
              .filter((u) => u.user_id && u.status !== 'invited')
              .map((u) => (
                <option key={u.user_id!} value={u.user_id!}>
                  {(u.full_name || '').trim() || u.email}
                </option>
              ))}
          </select>
          <label className="inline-flex items-center gap-2 whitespace-nowrap text-sm text-slate-600">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
            {t('app.companies.list.show_archived')}
          </label>
          {(query ||
            showArchived ||
            companyKindFilter !== 'all' ||
            sortBy !== 'name_asc' ||
            partyRoleListFilter !== 'all' ||
            clientStageListFilter !== 'all' ||
            ownerListFilter !== 'all') && (
            <button
              className="btn-secondary btn-sm"
              onClick={() => {
                setQuery('')
                setShowArchived(false)
                setCompanyKindFilter('all')
                setSortBy('name_asc')
                setPartyRoleListFilter('all')
                setClientStageListFilter('all')
                setOwnerListFilter('all')
              }}
            >
              {t('app.companies.list.reset')}
            </button>
          )}
        </div>
      </Toolbar>

      <DataTable
        columns={clientColumns}
        rows={filteredItems as any[]}
        rowKey={(it) => String((it as any).id)}
        loading={loading}
        onRowClick={(it) => navigate(`${CRM_APP_PATHS.agencyClients}/${(it as any).id}`)}
        emptyState={t('app.companies.list.table.empty')}
        ariaLabel={t('app.companies.list.clients_title', { defaultValue: 'Clients' })}
        footer={t('app.companies.list.insights.visible_hint', { values: { count: filteredItems.length } })}
      />
    </PageShell>
  )

  /// единая точка возврата — порядок хуков стабилен
  const addClientModal =
    addClientOpen && tenantIdForLinks ? (
      <AddClientModal
        tenantId={tenantIdForLinks}
        onClose={() => setAddClientOpen(false)}
        onCreated={(link) => void handleClientCreated(link)}
        onError={(msg) => notify({ title: msg, variant: 'error' })}
      />
    ) : null

  return id ? (
    <>
      {pageContent ?? <div className="card p-4">{t('common.loading')}</div>}
      {addClientModal}
    </>
  ) : (
    <>
      {listView}
      {addClientModal}
    </>
  );
  }

// ----- Presentation helpers -----
function SectionCard({
  title,
  description,
  children,
  collapsible = false,
  defaultOpen = true,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen)
  const { t } = useI18n()
  const toggle = () => {
    if (!collapsible) return
    setOpen((prev) => !prev)
  }
  return (
    <section className="card p-4">
      <header className="flex flex-col gap-1 pb-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
          {description && <p className="text-sm text-slate-500">{description}</p>}
        </div>
        {collapsible && (
          <button
            type="button"
            onClick={toggle}
            className="text-sm font-medium text-brand-600 hover:text-brand-500"
            aria-expanded={open}
          >
            {open ? '−' : '+'} {open ? t('common.actions.collapse') : t('common.actions.expand')}
          </button>
        )}
      </header>
      {(!collapsible || open) && <div className="space-y-4">{children}</div>}
    </section>
  )
}

function FieldGrid({ cols = 2, children, className }: { cols?: 1 | 2 | 3; children: React.ReactNode; className?: string }) {
  const extra = className ? ` ${className}` : ''
  if (cols === 1) return <div className={`space-y-3${extra}`}>{children}</div>
  if (cols === 3) return <div className={`grid grid-cols-1 gap-4 md:grid-cols-3${extra}`}>{children}</div>
  return <div className={`grid grid-cols-1 gap-4 md:grid-cols-2${extra}`}>{children}</div>
}

function InfoItem({ label, value, mono }: { label: string; value?: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={["text-sm text-slate-900", mono ? "font-mono break-all" : ""].filter(Boolean).join(" ")}>
        {value ?? '—'}
      </div>
    </div>
  )
}

const STATUS_TONE_CLASS: Record<StatusTone, string> = {
  info: 'bg-blue-100 text-blue-800',
  success: 'bg-emerald-100 text-emerald-800',
  warning: 'bg-amber-100 text-amber-800',
  danger: 'bg-rose-100 text-rose-800',
}

function StatusBadge({ tone = 'info', children }: { tone?: StatusTone; children: React.ReactNode }) {
  return (
    <span className={['inline-flex items-center rounded-lg px-2 py-0.5 text-xs font-medium', STATUS_TONE_CLASS[tone]].join(' ')}>
      {children}
    </span>
  )
}

function IndicatorList({ items }: { items: Array<{ label: string; ok: boolean | null | undefined }> }) {
  if (!items.length) return null
  return (
    <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
      {items.map((item) => {
        const toneClass =
          item.ok === true
            ? 'bg-emerald-500'
            : item.ok === false
              ? 'bg-rose-500'
              : 'bg-slate-300'
        const textClass = item.ok === false ? 'text-rose-700' : 'text-slate-700'
        return (
          <li key={item.label} className={['flex items-center gap-2 text-sm', textClass].join(' ')}>
            <span className={['h-2.5 w-2.5 rounded-full', toneClass].join(' ')} />
            <span>{item.label}</span>
          </li>
        )
      })}
    </ul>
  )
}

function humanizeStatus(status?: string | null) {
  if (!status) return ''
  return String(status)
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

interface SelectOption {
  value: string;
  label: string;
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
  mono,
}: {
  label: string;
  value: string | undefined;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  mono?: boolean;
}) {
  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <input
        className={['input', mono ? 'font-mono' : ''].filter(Boolean).join(' ')}
        type={type}
        value={value ?? ''}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

function TextareaField({
  label,
  value,
  onChange,
  placeholder,
  rows = 4,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <textarea
        className="input min-h-[80px]"
        rows={rows}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

function CheckboxField({
  label,
  checked,
  onChange,
}: {
  label: string | React.ReactNode;
  checked: boolean | undefined;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-sm text-slate-700">
      <input type="checkbox" checked={Boolean(checked)} onChange={(event) => onChange(event.target.checked)} />
      <span>{label}</span>
    </label>
  )
}

function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder,
  allowEmpty = true,
}: {
  label: string;
  value: string | undefined;
  onChange: (value: string) => void;
  options: Array<string | SelectOption>;
  placeholder?: string;
  allowEmpty?: boolean;
}) {
  const normalized = options.map((option) =>
    typeof option === 'string' ? { value: option, label: option } : option
  )
  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <select
        className="input"
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
      >
        {allowEmpty && <option value="">{placeholder ?? '—'}</option>}
        {normalized.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function MultiCheckboxField({
  label,
  options,
  values,
  onChange,
}: {
  label: string;
  options: string[];
  values: string[];
  onChange: (values: string[]) => void;
}) {
  const toggle = (option: string, checked: boolean) => {
    if (checked) {
      if (!values.includes(option)) onChange([...values, option])
    } else {
      onChange(values.filter((value) => value !== option))
    }
  }
  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="flex flex-wrap gap-3">
        {options.map((option) => (
          <CheckboxField
            key={option}
            label={option}
            checked={values.includes(option)}
            onChange={(checked) => toggle(option, checked)}
          />
        ))}
      </div>
    </div>
  )
}

function ArrayInputField({
  label,
  values,
  onChange,
  placeholder,
}: {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
}) {
  const { t } = useI18n()
  const handleChange = (index: number, value: string) => {
    const next = [...values]
    next[index] = value
    onChange(next)
  }
  const handleAdd = () => onChange([...values, ''])
  const handleRemove = (index: number) => {
    const next = values.filter((_, i) => i !== index)
    onChange(next.length ? next : [''])
  }
  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="space-y-2">
        {values.map((value, index) => (
          <div key={`${label}-${index}`} className="flex items-center gap-2">
            <input
              className="input flex-1"
              value={value}
              placeholder={placeholder}
              onChange={(event) => handleChange(index, event.target.value)}
            />
            <button className="btn-danger" onClick={() => handleRemove(index)} type="button">
              {t('common.actions.delete')}
            </button>
          </div>
        ))}
        <button className="btn-secondary" type="button" onClick={handleAdd}>
          {t('common.actions.add')}
        </button>
      </div>
    </div>
  )
}

function PolicyForm({
  documentTypes,
  policy,
  onSave,
  onCancel,
  t,
}: {
  documentTypes: DocType[];
  policy?: DocumentPolicy | null;
  onSave: (payload: Omit<DocumentPolicyCreate, 'scope' | 'scope_id'>) => Promise<void>;
  onCancel: () => void;
  t: (key: string, opts?: { defaultValue?: string; values?: Record<string, any> }) => string;
}) {
  const [documentTypeId, setDocumentTypeId] = useState(policy?.document_type_id || '')
  const [enabled, setEnabled] = useState(policy?.enabled ?? true)
  const [required, setRequired] = useState(policy?.required ?? false)
  const [alertDays, setAlertDays] = useState(policy?.alert_days_before_expiry?.toString() || '')
  const [notes, setNotes] = useState(policy?.notes || '')

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">
        {policy
          ? t('app.companies.detail.sections.document_policies.edit_policy', { defaultValue: 'Edit Policy' })
          : t('app.companies.detail.sections.document_policies.create_policy', { defaultValue: 'Create Policy' })}
      </h3>
      <div className="space-y-3">
        <label className="block">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.companies.detail.sections.document_policies.document_type', { defaultValue: 'Document Type' })}
          </div>
          <select
            className="input w-full"
            value={documentTypeId}
            onChange={(e) => setDocumentTypeId(e.target.value)}
            disabled={!!policy}
          >
            <option value="">{t('app.companies.detail.sections.document_policies.select_document_type', { defaultValue: 'Select document type...' })}</option>
            {documentTypes.map((dt) => (
              <option key={dt.id || dt.code} value={dt.id || dt.code || ''}>
                {dt.name || dt.code || dt.id}
              </option>
            ))}
          </select>
        </label>
        <CheckboxField
          label={t('app.companies.detail.sections.document_policies.enabled', { defaultValue: 'Enabled' })}
          checked={enabled}
          onChange={setEnabled}
        />
        <CheckboxField
          label={t('app.companies.detail.sections.document_policies.required', { defaultValue: 'Required' })}
          checked={required}
          onChange={setRequired}
        />
        <TextField
          label={t('app.companies.detail.sections.document_policies.alert_days_label', { defaultValue: 'Alert Days Before Expiry' })}
          type="number"
          value={alertDays}
          onChange={setAlertDays}
          placeholder="30"
        />
        <TextareaField
          label={t('app.companies.detail.sections.document_policies.notes', { defaultValue: 'Notes' })}
          value={notes}
          onChange={setNotes}
          placeholder={t('app.companies.detail.sections.document_policies.notes_placeholder', { defaultValue: 'Internal notes...' })}
          rows={3}
        />
        <div className="flex items-center gap-2">
          <button
            className="btn-primary text-sm"
            type="button"
            onClick={async () => {
              if (!documentTypeId) return
              await onSave({
                document_type_id: documentTypeId,
                enabled,
                required,
                alert_days_before_expiry: alertDays ? parseInt(alertDays, 10) : null,
                notes: notes || null,
              })
            }}
            disabled={!documentTypeId}
          >
            {t('common.actions.save')}
          </button>
          <button className="btn-secondary text-sm" type="button" onClick={onCancel}>
            {t('common.actions.cancel')}
          </button>
        </div>
      </div>
    </div>
  )
}
