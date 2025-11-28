// src/pages/Companies.tsx
import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Company, CompanyReadiness } from '../api/types'
import { useI18n } from '../i18n'

const ENABLE_READINESS = true; // readiness API enabled


type AnyRecord = Record<string, any>

function asRecord(value: unknown): AnyRecord {
  if (!value) return {}
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
      return {}
    }
    try {
      const parsed = JSON.parse(trimmed)
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as AnyRecord) : {}
    } catch (err) {
      console.warn('[Companies] failed to parse JSON record', err)
      return {}
    }
  }
  if (typeof value === 'object' && !Array.isArray(value)) {
    return value as AnyRecord
  }
  return {}
}

function asArray<T = any>(value: unknown): T[] {
  if (!value) return []
  if (Array.isArray(value)) return value as T[]
  if (typeof value === 'object') return Object.values(value as AnyRecord) as T[]
  return []
}

function mergeRecords(...records: Array<AnyRecord | null | undefined>): AnyRecord {
  const result: AnyRecord = {}
  for (const rec of records) {
    if (!rec) continue
    for (const [key, value] of Object.entries(rec)) {
      if (value !== undefined) {
        result[key] = value
      }
    }
  }
  return result
}

type StatusTone = 'info' | 'success' | 'warning' | 'danger'

const READINESS_STATE_META: Record<string, { labelKey: string; tone: StatusTone }> = {
  ready: { labelKey: 'app.companies.readiness.states.ready', tone: 'success' },
  legal_missing: { labelKey: 'app.companies.readiness.states.legal_missing', tone: 'warning' },
  contact_missing: { labelKey: 'app.companies.readiness.states.contact_missing', tone: 'warning' },
  bank_missing: { labelKey: 'app.companies.readiness.states.bank_missing', tone: 'warning' },
  billing_invalid: { labelKey: 'app.companies.readiness.states.billing_invalid', tone: 'warning' },
  compliance_expired: { labelKey: 'app.companies.readiness.states.compliance_expired', tone: 'danger' },
}

const FIN_STATUS_LABELS: Record<string, string> = {
  pending: 'app.companies.readiness.fin_status.pending',
  pass: 'app.companies.readiness.fin_status.pass',
  fail: 'app.companies.readiness.fin_status.fail',
  manual_review: 'app.companies.readiness.fin_status.manual_review',
}

const CURRENCY_OPTIONS = ['PLN', 'EUR', 'USD', 'GBP'];
const FIN_STATUS_OPTIONS = ['pending', 'pass', 'fail', 'manual_review'];
const CONTACT_ROLE_OPTIONS = ['OWNER', 'ACC', 'HR', 'FM', 'OPS', 'LEGAL', 'DISPATCH', 'SALES', 'SUPPORT', 'CEO'];
const CONTACT_ROLE_SET = new Set(CONTACT_ROLE_OPTIONS);
const CONTACT_ROLE_ALIASES: Record<string, string> = {
  ACCOUNTING: 'ACC',
  ACCOUNTANT: 'ACC',
  ACCOUNTS: 'ACC',
  MAIN: 'OWNER',
  OPERATIONS: 'OPS',
  OPERATION: 'OPS',
  DISPATCHER: 'DISPATCH',
  CUSTOMER_SUPPORT: 'SUPPORT',
  CUSTOMER_SERVICE: 'SUPPORT',
  SUPPORT_TEAM: 'SUPPORT',
  SALES_MANAGER: 'SALES',
  SALES_TEAM: 'SALES',
  FINANCE: 'FM',
  FINANCIAL: 'FM',
  FINANCIAL_MANAGER: 'FM',
  FINANCE_MANAGER: 'FM',
};
const WORK_MODE_OPTIONS = ['UOP', 'B2B', 'LEASE'];
const TRAILER_TYPE_KEYS = ['mega', 'standard', 'frigo', 'container'];

type AddressForm = {
  country?: string;
  city?: string;
  street?: string;
  zip?: string;
  house?: string;
  apartment?: string;
  region?: string;
};

interface RepresentativeForm {
  full_name: string;
  role?: string;
  email?: string;
  phone?: string;
}

interface ContactForm {
  role: string;
  full_name: string;
  email: string;
  phone: string;
  is_primary: boolean;
  is_portal_user: boolean;
}

interface BankAccountForm {
  bank_name: string;
  iban: string;
  swift_bic: string;
  country: string;
  label: string;
  is_primary: boolean;
}

interface PortalUserForm {
  full_name: string;
  email: string;
  role: string;
}

interface WebhookForm {
  event: string;
  target: string;
}

interface ContractForm {
  title: string;
  status: string;
  starts_at: string;
  ends_at: string;
  reference: string;
  code: string;
}

interface OrderForm {
  title: string;
  status: string;
  starts_at: string;
  ends_at: string;
  required_drivers: string;
  hired_drivers: string;
  client_reference: string;
  code: string;
}

interface EInvoiceForm {
  participant_id: string;
  scheme: string;
}

interface CompanyDetailForm {
  base: {
    name: string;
    legal_name: string;
    tax_id: string;
    phone: string;
    email: string;
    website: string;
    notes: string;
    is_archived: boolean;
    country_code: string;
    city: string;
    address: string;
  };
  legal: {
    reg_no: string;
    vat_eu: string;
    established_at: string;
    transport_license_number: string;
    insurance_policy_no: string;
    registered_address: AddressForm;
    operational_address: AddressForm;
    authorized_representatives: RepresentativeForm[];
  };
  billing: {
    default_currency: string;
    payment_terms_days: string;
    invoice_email: string;
    billing_address: AddressForm;
    einvoice_peppol: EInvoiceForm;
    bank_accounts: BankAccountForm[];
  };
  contacts: ContactForm[];
  operations: {
    fleet_tractors: string;
    fleet_intl_perc: string;
    fleet_local_perc: string;
    drivers_total: string;
    has_adr_operations: boolean;
    work_modes: string[];
    trailer_types: Record<string, string>;
    lanes: { origins: string[]; destinations: string[] };
    cargo_types: string[];
    languages: string[];
    preferred_nationalities: string[];
  };
  compliance: {
    fin_check_status: string;
    aml_required: boolean;
    iso9001: boolean;
    doc_valid_until: string;
    last_compliance_check_at: string;
  };
  portal: {
    enabled: boolean;
    url: string;
    last_sync_at: string;
    portal_roles: PortalUserForm[];
    permissions: string;
  };
  integrations: {
    provider_ids: string[];
    webhooks: WebhookForm[];
    branding: { logo_url: string; primary_color: string };
  };
  contracts: ContractForm[];
  orders: OrderForm[];
  rawExtra: AnyRecord;
}

function extractAddress(raw: unknown): AddressForm {
  const data = asRecord(raw)
  return {
    country: (data.country ?? '') as string,
    city: (data.city ?? '') as string,
    street: (data.street ?? data.address ?? '') as string,
    zip: (data.zip ?? '') as string,
    house: (data.house ?? data.number ?? '') as string,
    apartment: (data.apartment ?? data.ap ?? '') as string,
    region: (data.region ?? '') as string,
  }
}

function normalizeNumberString(value: unknown): string {
  if (value === null || value === undefined) return ''
  const num = Number(value)
  if (Number.isNaN(num)) return ''
  return String(num)
}

function normalizeStringArray(value: unknown): string[] {
  return asArray(value)
    .map((item) => (item === null || item === undefined ? '' : String(item)))
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

function addressToPayload(address: AddressForm): AnyRecord | null {
  const cleaned: AnyRecord = {}
  if (address.country) cleaned.country = address.country
  if (address.city) cleaned.city = address.city
  if (address.street) cleaned.street = address.street
  if (address.zip) cleaned.zip = address.zip
  if (address.house) cleaned.house = address.house
  if (address.apartment) cleaned.apartment = address.apartment
  if (address.region) cleaned.region = address.region
  return Object.keys(cleaned).length ? cleaned : null
}

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

interface ContactInfo {
  role?: string
  full_name?: string
  email?: string
  phone?: string
  is_primary?: boolean
  is_portal_user?: boolean
}

function normalizeContactRole(value?: string | null): string | undefined {
  if (value === null || value === undefined) return undefined
  const normalized = String(value).trim().toUpperCase()
  if (!normalized) return undefined
  const canonical = normalized.replace(/[\s-]+/g, '_')
  if (CONTACT_ROLE_SET.has(canonical)) return canonical
  if (CONTACT_ROLE_SET.has(normalized)) return normalized
  const alias = CONTACT_ROLE_ALIASES[canonical] ?? CONTACT_ROLE_ALIASES[normalized]
  if (alias && CONTACT_ROLE_SET.has(alias)) return alias
  return undefined
}

function combinePhone(data: AnyRecord): string {
  const parts: string[] = []
  const prefixRaw = data.phone_prefix ?? data.phone_code
  if (prefixRaw) {
    const prefix = String(prefixRaw)
    parts.push(prefix.startsWith('+') ? prefix : `+${prefix}`)
  }
  if (data.phone_local) {
    parts.push(String(data.phone_local))
  }
  if (!parts.length && data.phone) {
    parts.push(String(data.phone))
  }
  return parts.join(' ').trim()
}

function normalizeContacts(raw: unknown): ContactInfo[] {
  if (!raw) return []
  if (Array.isArray(raw)) {
    return (raw as unknown[]).map((item, idx) => {
      const data = asRecord(item)
      const combinedPhone = combinePhone(data)
      const roleHint =
        (typeof data.role === 'string' && data.role) ||
        (typeof data.type === 'string' && data.type) ||
        (typeof data.position === 'string' && data.position) ||
        undefined
      const normalizedRole = normalizeContactRole(roleHint)
      const roleHintLower = roleHint ? String(roleHint).trim().toLowerCase() : ''
      const isPrimary =
        data.is_primary !== undefined ? Boolean(data.is_primary) : roleHintLower === 'main' || idx === 0
      return {
        role: normalizedRole,
        full_name: data.full_name ?? data.name ?? undefined,
        email: data.email ?? undefined,
        phone: combinedPhone || (data.phone ? String(data.phone) : undefined),
        is_primary: isPrimary,
        is_portal_user: data.is_portal_user ?? undefined,
      }
    })
  }
  const obj = asRecord(raw)
  return Object.entries(obj).map(([key, value], idx) => {
    const data = asRecord(value)
    const combinedPhone = combinePhone(data)
    const preferredRole =
      (typeof data.role === 'string' && data.role.trim()) ||
      (typeof data.type === 'string' && data.type.trim()) ||
      (typeof data.position === 'string' && data.position.trim()) ||
      key
    const roleHintValue = preferredRole ?? key
    const normalizedRole = normalizeContactRole(roleHintValue)
    const roleHintLower = String(roleHintValue ?? '').trim().toLowerCase()
    const isPrimary =
      data.is_primary !== undefined ? Boolean(data.is_primary) : roleHintLower === 'main' || idx === 0
    return {
      role: normalizedRole,
      full_name: data.full_name ?? data.name ?? undefined,
      email: data.email ?? undefined,
      phone: combinedPhone || (data.phone ? String(data.phone) : undefined),
      is_primary: isPrimary,
      is_portal_user: data.is_portal_user ?? undefined,
    }
  })
}

export default function Companies(){
  const { t } = useI18n()
  const untitledNameRef = useRef(t('app.companies.detail.defaults.untitled'))
  useEffect(() => {
    untitledNameRef.current = t('app.companies.detail.defaults.untitled')
  }, [t])
  // router
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const handleCreateCompany = useCallback(() => {
    navigate('/app/clients/new')
  }, [navigate])

  // list state
  const [items, setItems] = useState<Company[]>([])

  // detail state
  const [current, setCurrent] = useState<Company | null>(null)
  const [readiness, setReadiness] = useState<CompanyReadiness | null>(null)
  const [readinessLoading, setReadinessLoading] = useState(false)
  const [readinessError, setReadinessError] = useState<string | null>(null)
  const [readinessUnavailable, setReadinessUnavailable] = useState(false)

  // ui state
  const [loading, setLoading] = useState(false)
  const [detailForm, setDetailForm] = useState<CompanyDetailForm | null>(null)
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // list filters/sort
  const [query, setQuery] = useState('')
  const [showArchived, setShowArchived] = useState(false)
  const [sortBy, setSortBy] = useState<'name_asc' | 'name_desc' | 'city_asc' | 'city_desc'>('name_asc')

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
    if (!showArchived) arr = arr.filter((it:any) => !it.is_archived)
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
  }, [items, showArchived, query, sortBy])

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

  const companyVacancies = useMemo(
    () => asArray(extraData.company_vacancies ?? extraData.vacancies ?? extraData.open_vacancies).map((item) => asRecord(item)),
    [extraData]
  )

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
    const base = {
      name: (currentAny.name as string) ?? '',
      legal_name: (currentAny.legal_name as string) ?? '',
      tax_id: (currentAny.tax_id as string) ?? '',
      phone: (currentAny.phone as string) ?? '',
      email: (currentAny.email as string) ?? '',
      website: (currentAny.website as string) ?? '',
      notes: (currentAny.notes as string) ?? '',
      is_archived: Boolean(currentAny.is_archived),
      country_code: (currentAny.country_code ?? currentAny.country ?? '') as string,
      city: (currentAny.city as string) ?? '',
      address: (currentAny.address as string) ?? '',
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
          },
        ]

    let rawExtra: AnyRecord = {}
    try {
      rawExtra = JSON.parse(JSON.stringify(extraData ?? {}))
    } catch {
      rawExtra = asRecord(extraData)
    }

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

      const operationsPayload = pruneEmpty({
        fleet_tractors: detailForm.operations.fleet_tractors
          ? Number(detailForm.operations.fleet_tractors)
          : undefined,
        fleet_intl_perc: detailForm.operations.fleet_intl_perc
          ? Number(detailForm.operations.fleet_intl_perc)
          : undefined,
        fleet_local_perc: detailForm.operations.fleet_local_perc
          ? Number(detailForm.operations.fleet_local_perc)
          : undefined,
        drivers_total: detailForm.operations.drivers_total
          ? Number(detailForm.operations.drivers_total)
          : undefined,
        has_adr_operations: detailForm.operations.has_adr_operations || undefined,
        work_modes: detailForm.operations.work_modes,
        trailers: pruneEmpty(
          Object.fromEntries(
            Object.entries(detailForm.operations.trailer_types).map(([key, value]) => [
              key,
              value ? Number(value) : undefined,
            ])
          )
        ),
        lanes: pruneEmpty({
          origins: detailForm.operations.lanes.origins,
          destinations: detailForm.operations.lanes.destinations,
        }),
        cargo_types: detailForm.operations.cargo_types,
        languages: detailForm.operations.languages,
        preferred_nationalities: detailForm.operations.preferred_nationalities,
      })

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
        .map((order) =>
          pruneEmpty({
            title: order.title || undefined,
            code: order.code || undefined,
            status: order.status || undefined,
            starts_at: order.starts_at || undefined,
            ends_at: order.ends_at || undefined,
            required_drivers: order.required_drivers ? Number(order.required_drivers) : undefined,
            hired_drivers: order.hired_drivers ? Number(order.hired_drivers) : undefined,
            client_reference: order.client_reference || undefined,
          })
        )

      const extraPayload: AnyRecord = {
        ...detailForm.rawExtra,
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
        legal_name: normalizeString(detailForm.base.legal_name),
        tax_id: normalizeString(detailForm.base.tax_id),
        phone: normalizeString(detailForm.base.phone),
        email: normalizeString(detailForm.base.email),
        website: normalizeString(detailForm.base.website),
        notes: normalizeString(detailForm.base.notes),
        country_code: normalizeString(detailForm.base.country_code),
        city: normalizeString(detailForm.base.city),
        address: normalizeString(detailForm.base.address),
      }

      Object.keys(payload).forEach((key) => {
        if (payload[key] === undefined) {
          delete payload[key]
        }
      })

      payload.is_archived = detailForm.base.is_archived

      payload.contacts = contactsPayload
      payload.extra = extraPayload

      await api.put(`/companies/${currentAny.id}`, payload)
      await loadOne(currentAny.id as string)
      setIsDirty(false)
      setSaveSuccess(true)
    } catch (err: any) {
      console.error('[Companies] save failed', err)
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
  }, [currentAny, detailForm, loadOne, t])

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
  const loadReadiness = useCallback(async (companyId: string) => {
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
  }, [])

  async function loadList(){
    setLoading(true)
    try{
      const { data } = await api.get('/companies/')
      const arr = Array.isArray(data) ? data : (data?.items || [])
      setItems(arr)
    } finally { setLoading(false) }
  }

  async function loadOne(companyId: string){
    setLoading(true)
    setReadiness(null)
    setReadinessUnavailable(false)
    setReadinessError(null)
    try{
      const { data } = await api.get(`/companies/${companyId}`)
      setCurrent(data)
      if (ENABLE_READINESS) {
        void loadReadiness(companyId)
      }
    } finally { setLoading(false) }
  }

  // kick off initial data load
  useEffect(() => {
    if (id && id !== 'new') {
      void loadOne(id)
    } else if (!id) {
      void loadList()
    }
  }, [id])

  // auto-create draft on /companies/new and redirect to the real id
  useEffect(() => {
    let cancelled = false
    async function createDraft() {
      try {
        const { data } = await api.post('/companies/', {
          name: untitledNameRef.current,
        })
        if (cancelled) return
        navigate(`/app/clients/${data.id}`, { replace: true })
      } catch (err) {
        console.error('[Companies] failed to create draft', err)
      }
    }
    if (id === 'new') {
      void createDraft()
    }
    return () => {
      cancelled = true
    }
  }, [id, navigate])

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
        <div className="h-full w-full flex flex-col space-y-4">
          <div className="text-xs text-gray-500 mb-1">
            <Link className="hover:underline" to="/app/clients">{t('app.companies.actions.back_to_list')}</Link>
          </div>
          <div className="card p-4 text-sm text-gray-500">{t('common.loading')}</div>
        </div>
      )
    }

    const locationLine = [detailForm.base.country_code, detailForm.base.city].filter(Boolean).join(', ')

    const companyKpis = [
      {
        key: 'candidates_total',
        label: t('app.companies.detail.kpis.candidates_total'),
        value: currentAny?.candidates_total ?? 0,
        hint: t('app.companies.detail.kpis.candidates_total_hint'),
      },
      {
        key: 'candidates_pipeline',
        label: t('app.companies.detail.kpis.candidates_pipeline'),
        value: currentAny?.candidates_pipeline ?? 0,
        hint: t('app.companies.detail.kpis.candidates_pipeline_hint'),
      },
      {
        key: 'candidates_docs',
        label: t('app.companies.detail.kpis.candidates_docs'),
        value: currentAny?.candidates_docs ?? 0,
        hint: t('app.companies.detail.kpis.candidates_docs_hint'),
      },
      {
        key: 'vacancies',
        label: t('app.companies.detail.kpis.vacancies_active'),
        value: currentAny?.vacancies_active ?? 0,
        hint: t('app.companies.detail.kpis.vacancies_active_hint'),
      },
      {
        key: 'services',
        label: t('app.companies.detail.kpis.services_blocking'),
        value: currentAny?.services_blocking ?? 0,
        hint: t('app.companies.detail.kpis.services_blocking_hint'),
      },
    ]

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
            <p className="text-base font-semibold text-gray-900">
              {primaryContactEntry.full_name || t('common.labels.not_available')}
            </p>
            {primaryContactEntry.role && (
              <p className="text-xs uppercase tracking-wide text-gray-500">{primaryContactEntry.role}</p>
            )}
            {primaryContactEntry.phone && <p>{primaryContactEntry.phone}</p>}
            {primaryContactEntry.email && <p>{primaryContactEntry.email}</p>}
          </div>
        ) : (
          <p className="text-sm text-gray-500">{t('app.companies.detail.overview.primary_contact.empty')}</p>
        ),
      },
      {
        key: 'finance_contact',
        title: t('app.companies.detail.overview.finance_contact.title'),
        content: financeContactEntry ? (
          <div className="space-y-1">
            <p className="text-base font-semibold text-gray-900">
              {financeContactEntry.full_name || t('common.labels.not_available')}
            </p>
            {financeContactEntry.role && (
              <p className="text-xs uppercase tracking-wide text-gray-500">{financeContactEntry.role}</p>
            )}
            {financeContactEntry.phone && <p>{financeContactEntry.phone}</p>}
            {financeContactEntry.email && <p>{financeContactEntry.email}</p>}
            {invoiceEmail && (
              <p className="text-xs text-gray-500">
                {t('app.companies.detail.overview.finance_contact.invoice_label', { values: { email: invoiceEmail } })}
              </p>
            )}
          </div>
        ) : invoiceEmail ? (
          <div className="space-y-1">
            <p className="text-base font-semibold text-gray-900">{invoiceEmail}</p>
            <p className="text-xs text-gray-500">{t('app.companies.detail.overview.finance_contact.invoice_only')}</p>
          </div>
        ) : (
          <p className="text-sm text-gray-500">{t('app.companies.detail.overview.finance_contact.empty')}</p>
        ),
      },
      {
        key: 'contracts',
        title: t('app.companies.detail.overview.contracts.title'),
        content: upcomingContract ? (
          <div className="space-y-1">
            <p className="text-base font-semibold text-gray-900">
              {upcomingContract.contract.title || t('common.labels.unnamed')}
            </p>
            {upcomingContract.contract.status && (
              <p className="text-xs uppercase tracking-wide text-gray-500">
                {upcomingContract.contract.status}
              </p>
            )}
            <p className="text-sm text-gray-600">
              {t('app.companies.detail.overview.contracts.due', {
                values: { date: fmtDate(upcomingContract.dueDate) },
              })}
            </p>
          </div>
        ) : (
          <p className="text-sm text-gray-500">{t('app.companies.detail.overview.contracts.empty')}</p>
        ),
      },
      {
        key: 'driver_slots',
        title: t('app.companies.detail.overview.driver_slots.title'),
        content:
          detailForm.orders.length > 0 ? (
            <div className="space-y-1">
              <p className="text-3xl font-semibold text-gray-900">{openDriverSlots}</p>
              <p className="text-sm text-gray-600">
                {t('app.companies.detail.overview.driver_slots.subtitle')}
              </p>
              <p className="text-xs text-gray-500">
                {t('app.companies.detail.overview.driver_slots.assigned', {
                  values: { hired: driverStats.hired, required: driverStats.required },
                })}
              </p>
            </div>
          ) : (
            <p className="text-sm text-gray-500">{t('app.companies.detail.overview.driver_slots.empty')}</p>
          ),
      },
    ]

    return (
      <div className="h-full w-full flex flex-col space-y-4 pb-12">
        <section className="rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-6 text-white shadow-card">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <div className="text-xs text-white/80">
                <Link className="hover:underline" to="/app/clients">{t('app.companies.actions.back_to_list')}</Link>
              </div>
              <h1 className="text-3xl font-semibold">
                {detailForm.base.name || t('app.companies.detail.header.fallback_name')}
              </h1>
              {detailForm.base.legal_name && (
                <div className="text-sm text-white/80">{detailForm.base.legal_name}</div>
              )}
              {locationLine && <div className="text-sm text-white/70">{locationLine}</div>}
            </div>
            <div className="flex flex-col gap-2 text-sm text-white/80">
              <div className="flex flex-wrap gap-2">
                <button
                  className="btn-primary bg-white text-brand-700 hover:bg-white/90"
                  type="button"
                  onClick={handleSave}
                  disabled={!isDirty || saving}
                >
                  {saving ? t('common.saving') : t('common.actions.save')}
                </button>
                <button
                  className="btn-ghost bg-white/10 text-white hover:bg-white/20"
                  type="button"
                  onClick={handleResetDetail}
                  disabled={saving || !isDirty}
                >
                  {t('app.companies.detail.actions.reset')}
                </button>
              </div>
              {saveSuccess && <div className="text-emerald-50">{t('app.companies.messages.save_success')}</div>}
              {saveError && <div className="max-w-md text-rose-50">{saveError}</div>}
            </div>
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {companyKpis.map((card) => (
              <div key={card.key} className="rounded-2xl border border-white/30 bg-white/10 p-4">
                <div className="text-sm text-white/80">{card.label}</div>
                <div className="text-2xl font-semibold">{card.value}</div>
                <div className="text-xs text-white/70">{card.hint}</div>
              </div>
            ))}
          </div>
        </section>

        <SectionCard
          title={t('app.companies.detail.overview.title')}
          description={t('app.companies.detail.overview.subtitle')}
        >
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {overviewCards.map((card) => (
              <div
                key={card.key}
                className="rounded-2xl border border-gray-100 bg-white/80 p-4 shadow-sm shadow-brand-900/5"
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{card.title}</p>
                <div className="mt-2 text-sm text-gray-600">{card.content}</div>
              </div>
            ))}
          </div>
        </SectionCard>

        <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard title={t('app.companies.detail.widgets.vacancies.title')} description={t('app.companies.detail.widgets.vacancies.subtitle')}>
            <div className="flex items-baseline justify-between">
              <p className="text-sm text-gray-500">{t('app.companies.detail.widgets.vacancies.total')}</p>
              <p className="text-3xl font-semibold text-gray-900">{vacancyAnalytics.total}</p>
            </div>
            {vacancyAnalytics.statusRows.length ? (
              <ul className="divide-y divide-gray-100 text-sm text-gray-700">
                {vacancyAnalytics.statusRows.map((row) => (
                  <li key={row.status} className="flex items-center justify-between py-2">
                    <span>{humanizeStatus(row.status) || t('app.companies.detail.widgets.vacancies.status_unknown')}</span>
                    <span className="font-semibold">{row.count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">{t('app.companies.detail.widgets.vacancies.empty')}</p>
            )}
            {vacancyAnalytics.latest.length > 0 && (
              <div className="rounded-2xl bg-slate-50/60 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {t('app.companies.detail.widgets.vacancies.latest_title')}
                </div>
                <ul className="mt-2 space-y-2 text-sm">
                  {vacancyAnalytics.latest.map((vacancy, index) => (
                    <li key={(vacancy.id as string) ?? (vacancy.code as string) ?? `vacancy-${index}`} className="rounded-xl border border-gray-100 bg-white/80 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-gray-900">{(vacancy.title as string) ?? (vacancy.position as string) ?? t('common.labels.unnamed')}</span>
                        <span className="text-xs text-gray-500">
                          {fmtDateTime((vacancy.updated_at as string | undefined) ?? (vacancy.created_at as string | undefined))}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        {t('app.companies.detail.widgets.vacancies.status_label', {
                          values: {
                            status:
                              humanizeStatus((vacancy.status as string | undefined) ?? (vacancy.stage as string | undefined)) ||
                              t('app.companies.detail.widgets.vacancies.status_unknown'),
                          },
                        })}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </SectionCard>

          <SectionCard title={t('app.companies.detail.widgets.blockers.title')} description={t('app.companies.detail.widgets.blockers.subtitle')}>
            {blockingOrders.length ? (
              <ul className="space-y-3 text-sm">
                {blockingOrders.map((entry) => (
                  <li key={entry.key} className="rounded-2xl border border-amber-100 bg-amber-50/50 p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-gray-900">{entry.title}</span>
                      <span className="text-xs text-gray-500">{humanizeStatus(entry.status) || t('common.labels.not_available')}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {entry.reasons.map((reason) => (
                        <span
                          key={`${entry.key}-${reason}`}
                          className="inline-flex items-center rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-amber-700"
                        >
                          {t(`app.companies.detail.widgets.blockers.reason.${reason}`)}
                        </span>
                      ))}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {entry.updatedAt ? fmtDateTime(entry.updatedAt) : t('common.labels.not_available')}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">{t('app.companies.detail.widgets.blockers.empty')}</p>
            )}
          </SectionCard>
        </div>

        {ENABLE_READINESS && (
          <SectionCard title={t('app.companies.readiness.title')}>
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="space-y-2 text-sm text-gray-600">
                <p>{t('app.companies.readiness.description')}</p>
                {readinessUnavailable && (
                  <p className="text-gray-500">{t('app.companies.readiness.unavailable')}</p>
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

        <SectionCard title={t('app.companies.detail.sections.base.title')}>
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
            <TextField
              label={t('app.companies.detail.fields.country_code')}
              value={detailForm.base.country_code}
              onChange={(value) => updateField('base', 'country_code', value.toUpperCase())}
            />
            <TextField
              label={t('app.companies.detail.fields.city')}
              value={detailForm.base.city}
              onChange={(value) => updateField('base', 'city', value)}
            />
            <TextField
              label={t('app.companies.detail.fields.address')}
              value={detailForm.base.address}
              onChange={(value) => updateField('base', 'address', value)}
            />
            <CheckboxField
              label={t('app.companies.detail.fields.archived')}
              checked={detailForm.base.is_archived}
              onChange={(value) => updateField('base', 'is_archived', value)}
            />
          </FieldGrid>
          <TextareaField
            label={t('app.companies.detail.fields.notes')}
            value={detailForm.base.notes}
            onChange={(value) => updateField('base', 'notes', value)}
            rows={4}
          />
        </SectionCard>

        <SectionCard title={t('app.companies.detail.sections.legal.title')}>
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
              placeholder="YYYY-MM-DD"
            />
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
          </FieldGrid>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{t('app.companies.detail.groups.registered_address')}</div>
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
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{t('app.companies.detail.groups.operational_address')}</div>
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
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                {t('app.companies.detail.groups.representatives')}
              </div>
              <button className="btn-ghost" type="button" onClick={addRepresentative}>
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
                    <button className="btn-ghost" type="button" onClick={() => removeRepresentative(index)}>
                      {t('common.actions.delete')}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>

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
          <div className="space-y-3">
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
                  <button className="btn-ghost" type="button" onClick={() => removeBankAccount(index)}>
                    {t('common.actions.delete')}
                  </button>
                </div>
              </div>
            ))}
            <button className="btn-ghost" type="button" onClick={addBankAccount}>
              {t('app.companies.detail.actions.add_bank_account')}
            </button>
          </div>
        </SectionCard>

        <SectionCard title={t('app.companies.detail.sections.contacts.title')}>
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
                  <button className="btn-ghost" type="button" onClick={() => removeContact(index)}>
                    {t('common.actions.delete')}
                  </button>
                </div>
              </div>
            ))}
            <button className="btn-ghost" type="button" onClick={addContact}>
              {t('app.companies.detail.actions.add_contact')}
            </button>
          </div>
        </SectionCard>

        <SectionCard
          title={t('app.companies.detail.sections.operations.title')}
          collapsible
          defaultOpen={false}
        >
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
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{t('app.companies.detail.groups.trailer_types')}</div>
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
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{t('app.companies.detail.groups.lanes')}</div>
              <ArrayInputField
                label={t('app.companies.detail.fields.lanes_origins')}
                values={detailForm.operations.lanes.origins}
                onChange={(values) =>
                  updateFormState('operations', (prev) => ({
                    ...prev,
                    lanes: { ...prev.lanes, origins: values },
                  }))
                }
                placeholder="PL"
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
                placeholder="FR"
              />
            </div>
          </div>
          <ArrayInputField
            label={t('app.companies.detail.fields.cargo_types')}
            values={detailForm.operations.cargo_types}
            onChange={(values) => updateFormState('operations', (prev) => ({ ...prev, cargo_types: values }))}
            placeholder="ADR"
          />
          <ArrayInputField
            label={t('app.companies.detail.fields.languages')}
            values={detailForm.operations.languages}
            onChange={(values) => updateFormState('operations', (prev) => ({ ...prev, languages: values }))}
            placeholder="pl"
          />
          <ArrayInputField
            label={t('app.companies.detail.fields.preferred_nationalities')}
            values={detailForm.operations.preferred_nationalities}
            onChange={(values) =>
              updateFormState('operations', (prev) => ({ ...prev, preferred_nationalities: values }))
            }
            placeholder="PL"
          />
        </SectionCard>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <SectionCard
            title={t('app.companies.detail.sections.compliance.title')}
            collapsible
            defaultOpen={false}
          >
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
            <FieldGrid cols={2}>
              <TextField
                label={t('app.companies.detail.fields.docs_valid_until')}
                value={detailForm.compliance.doc_valid_until}
                onChange={(value) => updateFormState('compliance', (prev) => ({ ...prev, doc_valid_until: value }))}
                placeholder="YYYY-MM-DD"
              />
              <TextField
                label={t('app.companies.detail.fields.last_check')}
                value={detailForm.compliance.last_compliance_check_at}
                onChange={(value) =>
                  updateFormState('compliance', (prev) => ({ ...prev, last_compliance_check_at: value }))
                }
                placeholder="2025-01-01T00:00:00Z"
              />
            </FieldGrid>
          </SectionCard>

          <SectionCard
            title={t('app.companies.detail.sections.portal.title')}
            collapsible
            defaultOpen={false}
          >
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
              placeholder="2025-01-01T00:00:00Z"
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
                    <button className="btn-ghost" type="button" onClick={() => removePortalUser(index)}>
                      {t('common.actions.delete')}
                    </button>
                  </div>
                </div>
              ))}
              <button className="btn-ghost" type="button" onClick={addPortalUser}>
                {t('app.companies.detail.actions.add_portal_user')}
              </button>
            </div>
            <TextareaField
              label={t('app.companies.detail.fields.permissions')}
              value={detailForm.portal.permissions}
              onChange={(value) => updateFormState('portal', (prev) => ({ ...prev, permissions: value }))}
              rows={6}
              placeholder='{"contracts": {"view": true}}'
            />
          </SectionCard>
        </div>

        <SectionCard
          title={t('app.companies.detail.sections.integrations.title')}
          collapsible
          defaultOpen={false}
        >
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
              placeholder="#004b8d"
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
                  <button className="btn-ghost" type="button" onClick={() => removeWebhook(index)}>
                    {t('common.actions.delete')}
                  </button>
                </div>
              </div>
            ))}
            <button className="btn-ghost" type="button" onClick={addWebhook}>
              {t('app.companies.detail.actions.add_webhook')}
            </button>
          </div>
        </SectionCard>

        <SectionCard
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
                  <button className="btn-ghost" type="button" onClick={() => removeContract(index)}>
                    {t('common.actions.delete')}
                  </button>
                </div>
              </div>
            ))}
            <button className="btn-ghost" type="button" onClick={addContract}>
              {t('app.companies.detail.actions.add_contract')}
            </button>
          </div>
        </SectionCard>

        <SectionCard
          title={t('app.companies.detail.sections.orders.title')}
          collapsible
          defaultOpen={false}
        >
          <div className="space-y-3">
            {detailForm.orders.map((order, index) => (
              <div key={`order-${index}`} className="grid grid-cols-1 gap-2 lg:grid-cols-7">
                <TextField
                  label={t('app.companies.detail.fields.name')}
                  value={order.title}
                  onChange={(value) => setOrderField(index, { title: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.status')}
                  value={order.status}
                  onChange={(value) => setOrderField(index, { status: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.date_start')}
                  value={order.starts_at}
                  onChange={(value) => setOrderField(index, { starts_at: value })}
                />
                <TextField
                  label={t('app.companies.detail.fields.date_end')}
                  value={order.ends_at}
                  onChange={(value) => setOrderField(index, { ends_at: value })}
                />
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
                <div className="flex items-end gap-2">
                  <TextField
                    label={t('app.companies.detail.fields.reference')}
                    value={order.client_reference}
                    onChange={(value) => setOrderField(index, { client_reference: value })}
                  />
                  <button className="btn-ghost" type="button" onClick={() => removeOrder(index)}>
                    {t('common.actions.delete')}
                  </button>
                </div>
              </div>
            ))}
            <button className="btn-ghost" type="button" onClick={addOrder}>
              {t('app.companies.detail.actions.add_order')}
            </button>
          </div>
        </SectionCard>

        <SectionCard title={t('app.companies.detail.sections.system.title')}>
          <FieldGrid cols={3}>
            <InfoItem label={t('app.companies.detail.fields.id')} value={(currentAny?.id as string | undefined) || '—'} mono />
            <InfoItem label={t('app.companies.detail.fields.created_at')} value={fmtDateTime(currentAny?.created_at as string | undefined)} />
            <InfoItem label={t('app.companies.detail.fields.updated_at')} value={fmtDateTime(currentAny?.updated_at as string | undefined)} />
          </FieldGrid>
        </SectionCard>

      </div>
    )
  } else {
      setCurrent(null)
      setReadiness(null)
      setReadinessUnavailable(false)
      setReadinessError(null)
      void loadList()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, detailForm, isDirty, saving, saveError, saveSuccess, readiness, readinessLoading, readinessUnavailable, readinessError, t])

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
      alert(t('app.companies.messages.archive_error'))
    } finally {
      setLoading(false)
    }
  }


  const companyInsights = useMemo(() => {
    const visible = filteredItems.length
    const active = filteredItems.filter((item: any) => !item?.is_archived).length
    const archived = Math.max(visible - active, 0)
    const countries = new Set(
      filteredItems
        .map((item: any) => (item?.country_code || item?.country || '').trim().toUpperCase())
        .filter(Boolean)
    ).size
    const missingLocation = filteredItems.filter(
      (item: any) => !(item?.city && (item?.country_code || item?.country))
    ).length
    return { visible, active, archived, countries, missingLocation }
  }, [filteredItems])

  const companyHeroCards = [
    {
      key: 'visible',
      label: t('app.companies.list.insights.visible'),
      value: companyInsights.visible,
      hint: t('app.companies.list.insights.visible_hint', { values: { count: companyInsights.visible } }),
    },
    {
      key: 'active',
      label: t('app.companies.list.insights.active'),
      value: companyInsights.active,
      hint: t('app.companies.list.insights.active_hint', { values: { count: companyInsights.archived } }),
    },
    {
      key: 'countries',
      label: t('app.companies.list.insights.countries'),
      value: companyInsights.countries,
      hint: t('app.companies.list.insights.countries_hint'),
    },
    {
      key: 'location',
      label: t('app.companies.list.insights.missing_location'),
      value: companyInsights.missingLocation,
      hint: t('app.companies.list.insights.missing_location_hint'),
    },
  ]

  const companyHero = (
    <section className="rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-6 text-white shadow-card">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <p className="text-2xl font-semibold">{t('app.companies.list.title')}</p>
          <p className="text-sm text-white/80">{t('app.companies.list.insights.subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn-primary bg-white text-brand-700 hover:bg-white/90" onClick={handleCreateCompany}>
            {t('app.companies.actions.new')}
          </button>
        </div>
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {companyHeroCards.map((card) => (
          <div key={card.key} className="rounded-2xl border border-white/30 bg-white/10 p-4">
            <div className="text-sm text-white/80">{card.label}</div>
            <div className="text-3xl font-semibold">{card.value}</div>
            <div className="text-xs text-white/70">{card.hint}</div>
          </div>
        ))}
      </div>
    </section>
  )

  // ----- list view (без :id)
  const listView = (
    <div className="h-full w-full flex flex-col space-y-4">
      {companyHero}

      <section className="app-surface space-y-4 p-6">
        <div className="grid gap-4 md:grid-cols-[minmax(220px,1fr)_minmax(180px,200px)_auto]">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.companies.list.search_label')}
            </span>
            <input
              className="input w-full"
              placeholder={t('app.companies.list.search_placeholder')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.companies.list.sort_label')}
            </span>
            <select className="input" value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
              <option value="name_asc">{t('app.companies.list.sort_options.name_asc')}</option>
              <option value="name_desc">{t('app.companies.list.sort_options.name_desc')}</option>
              <option value="city_asc">{t('app.companies.list.sort_options.city_asc')}</option>
              <option value="city_desc">{t('app.companies.list.sort_options.city_desc')}</option>
            </select>
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
            {t('app.companies.list.show_archived')}
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
          <span>
            {t('app.companies.list.insights.visible_hint', { values: { count: filteredItems.length } })}
          </span>
          {(query || showArchived || sortBy !== 'name_asc') && (
            <button
              className="btn-ghost"
              onClick={() => {
                setQuery('')
                setShowArchived(false)
                setSortBy('name_asc')
              }}
            >
              {t('app.companies.list.reset')}
            </button>
          )}
        </div>
      </section>

      <section className="app-surface overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-white/80 text-left text-xs uppercase tracking-wide text-gray-500">
            <tr>
              <th className="px-4 py-3">{t('app.companies.list.table.headers.name')}</th>
              <th className="px-4 py-3">{t('app.companies.list.table.headers.legal_name')}</th>
              <th className="px-4 py-3">{t('app.companies.list.table.headers.country')}</th>
              <th className="px-4 py-3">{t('app.companies.list.table.headers.city')}</th>
              <th className="px-4 py-3">{t('app.companies.list.table.headers.archived')}</th>
              <th className="px-4 py-3 w-1">{t('app.companies.list.table.headers.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td className="px-4 py-6 text-center text-gray-500" colSpan={6}>
                  {t('app.companies.list.table.loading')}
                </td>
              </tr>
            )}
            {!loading &&
              filteredItems.map((it) => (
                <tr key={(it as any).id} className="border-t border-gray-100 hover:bg-gray-50/70 transition">
                  <td className="px-4 py-3 font-medium text-brand-700">
                    <Link className="hover:underline" to={`/app/clients/${(it as any).id}`}>
                      {(it as any).name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{(it as any).legal_name || '—'}</td>
                  <td className="px-4 py-3">{(it as any).country_code || (it as any).country || '—'}</td>
                  <td className="px-4 py-3">{(it as any).city || '—'}</td>
                  <td className="px-4 py-3">
                    {(it as any).is_archived ? t('common.words.yes') : t('common.words.no')}
                  </td>
                  <td className="px-4 py-3 space-x-2 text-right">
                    <button className="btn-ghost" onClick={() => navigate(`/app/clients/${(it as any).id}`)}>
                      {t('app.companies.list.table.actions.edit')}
                    </button>
                    <button className="btn-ghost" onClick={() => toggleArchive(it)}>
                      {(it as any).is_archived
                        ? t('app.companies.list.table.actions.restore')
                        : t('app.companies.list.table.actions.archive')}
                    </button>
                  </td>
                </tr>
              ))}
            {!loading && filteredItems.length === 0 && (
              <tr>
                <td className="px-4 py-8 text-center text-gray-500" colSpan={6}>
                  {t('app.companies.list.table.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  )

  /// единая точка возврата — порядок хуков стабилен
  return id ? (pageContent ?? <div className="card p-4">{t('common.loading')}</div>) : listView;
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
          <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
          {description && <p className="text-sm text-gray-500">{description}</p>}
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

function FieldGrid({ cols = 2, children }: { cols?: 1 | 2 | 3; children: React.ReactNode }) {
  if (cols === 1) return <div className="space-y-3">{children}</div>
  if (cols === 3) return <div className="grid grid-cols-1 gap-4 md:grid-cols-3">{children}</div>
  return <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
}

function InfoItem({ label, value, mono }: { label: string; value?: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</div>
      <div className={["text-sm text-gray-900", mono ? "font-mono break-all" : ""].filter(Boolean).join(" ")}>
        {value ?? '—'}
      </div>
    </div>
  )
}

const STATUS_TONE_CLASS: Record<StatusTone, string> = {
  info: 'bg-sky-100 text-sky-800',
  success: 'bg-emerald-100 text-emerald-800',
  warning: 'bg-amber-100 text-amber-800',
  danger: 'bg-rose-100 text-rose-800',
}

function StatusBadge({ tone = 'info', children }: { tone?: StatusTone; children: React.ReactNode }) {
  return (
    <span className={['inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', STATUS_TONE_CLASS[tone]].join(' ')}>
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
              : 'bg-gray-300'
        const textClass = item.ok === false ? 'text-rose-700' : 'text-gray-700'
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
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  mono?: boolean;
}) {
  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</div>
      <input
        className={['input', mono ? 'font-mono' : ''].filter(Boolean).join(' ')}
        type={type}
        value={value}
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
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</div>
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
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-sm text-gray-700">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
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
  value: string;
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
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</div>
      <select
        className="input"
        value={value}
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
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</div>
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
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</div>
      <div className="space-y-2">
        {values.map((value, index) => (
          <div key={`${label}-${index}`} className="flex items-center gap-2">
            <input
              className="input flex-1"
              value={value}
              placeholder={placeholder}
              onChange={(event) => handleChange(index, event.target.value)}
            />
            <button className="btn-ghost" onClick={() => handleRemove(index)} type="button">
              {t('common.actions.delete')}
            </button>
          </div>
        ))}
        <button className="btn-ghost" type="button" onClick={handleAdd}>
          {t('common.actions.add')}
        </button>
      </div>
    </div>
  )
}
