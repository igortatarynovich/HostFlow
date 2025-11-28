// src/pages/CandidateCard.tsx
import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import type { RefObject } from 'react'
import type { InputHTMLAttributes } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import clsx from 'clsx'
import { api } from '../api/client'
import { listCandidateEmployments, createCandidateEmployment, updateCandidateEmployment, deleteCandidateEmployment } from '../api/candidateEmployments'
import type {
  Candidate,
  CandidateExtra,
  CandidateEmploymentEntry,
  CandidateEmploymentRecord,
  ServiceItemStatus,
  ServiceOrderStatus,
  UUID,
  Vacancy,
} from '../api/types'
import { createDeleteRequest } from '../api/deletionRequests'
import StageTag from '../components/StageTag'
import { useMetaStages } from '../store/useMeta'
import CandidateDocuments from '../modules/documents/CandidateDocuments'
import { usePermissions } from '../hooks/usePermissions'
import { useServiceOrders } from '../hooks/useAdditionalServices'
import { useI18n } from '../i18n'
import { PREFERRED_CONTACT_VALUES } from '../data/preferredContactChannels'
import { translateReasonLabel, translateStageLabel } from '../utils/stageLabels'

type Tab = 'personal' | 'docs' | 'services'
type PreferredContact = 'viber' | 'whatsapp' | 'telegram' | 'phone' | ''
type Option = { value: string; label: string; extra?: any }
type AddressFields = {
  country: string;
  city: string;
  street: string;
  house: string;
  apt: string;
  zip: string;
};
type EmploymentEntry =
  NonNullable<CandidateExtra['employment_history']> extends Array<infer Item>
    ? Item
    : CandidateEmploymentEntry
type EmploymentRow = {
  id?: string;
  localId: string;
  employer_name: string;
  country: string;
  position: string;
  start_date: string;
  end_date: string;
}
type EmploymentSnapshot = {
  employer_name: string;
  country: string;
  position: string;
  start_date: string;
  end_date: string;
}

type CandidateNote = { id: string; text: string; visibility: 'internal'|'client'|'candidate'; author_id: string; created_at: string }
type StageHistoryEntry = {
  id: string;
  from_code: string | null;
  to_code: string | null;
  at: string | null;
  actor: string | null;
  reason: string | null;
}

const ADDRESS_KEYS: Array<keyof AddressFields> = ['country', 'city', 'street', 'house', 'apt', 'zip']
const UUID_RE = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/
const CREATE_FIELDS = new Set(['first_name', 'last_name', 'email', 'phone', 'phone_country_code', 'languages', 'stage', 'manager_id', 'company_id', 'vacancy_id', 'status_reason'])
const PATCH_AFTER_CREATE_FIELDS = new Set(['address', 'city', 'country_code', 'birth_date', 'note', 'extra', 'status_reason'])
const MAX_EMPLOYMENTS = 3
const SERVICE_ORDER_STATUSES: ServiceOrderStatus[] = [
  'draft',
  'quoted',
  'approved',
  'scheduled',
  'in_progress',
  'delivered',
  'cancelled',
  'refunded',
]
const SERVICE_ITEM_STATUSES: ServiceItemStatus[] = ['pending', 'scheduled', 'in_progress', 'delivered', 'cancelled']

const createLocalId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `tmp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

const makeEmploymentRow = (seed?: Partial<EmploymentRow>): EmploymentRow => ({
  id: seed?.id,
  localId: seed?.localId ?? createLocalId(),
  employer_name: seed?.employer_name ?? '',
  country: seed?.country ?? '',
  position: seed?.position ?? '',
  start_date: seed?.start_date ?? '',
  end_date: seed?.end_date ?? '',
})

/* ----------------------------- helpers ----------------------------- */
const ccToFlag = (cc: string) =>
  cc.replace(/./g, ch => String.fromCodePoint(127397 + ch.toUpperCase().charCodeAt(0)))

const makeAddress = (value?: Partial<AddressFields> | null): AddressFields => {
  const base: AddressFields = { country: '', city: '', street: '', house: '', apt: '', zip: '' }
  if (!value || typeof value !== 'object') return { ...base }
  const next: AddressFields = { ...base }
  for (const key of ADDRESS_KEYS) {
    const val = (value as any)[key]
    next[key] = val != null ? String(val) : ''
  }
  return next
}

const sanitizeEmploymentEntry = (value: any): EmploymentEntry => {
  const entry: CandidateEmploymentEntry = {
    employer: '',
    country: '',
    position: '',
    date_from: '',
    date_to: '',
  }
  if (value && typeof value === 'object') {
    if ('employer' in value) entry.employer = value.employer ? String(value.employer) : ''
    if ('country' in value) entry.country = value.country ? String(value.country) : ''
    if ('position' in value) entry.position = value.position ? String(value.position) : ''
    if ('date_from' in value) entry.date_from = value.date_from ? String(value.date_from).slice(0, 10) : ''
    if ('date_to' in value) entry.date_to = value.date_to ? String(value.date_to).slice(0, 10) : ''
  } else if (typeof value === 'string' && value.trim()) {
    entry.employer = value.trim()
  }
  return entry as EmploymentEntry
}

const sanitizeEmploymentHistory = (value: any): EmploymentEntry[] => {
  if (!value) return []
  if (Array.isArray(value)) return value.map(sanitizeEmploymentEntry)
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return sanitizeEmploymentHistory(parsed)
    } catch {
      return value
        .split('\n')
        .map((line: string) => sanitizeEmploymentEntry(line))
        .filter((item: EmploymentEntry) => item.employer || item.country || item.position)
    }
  }
  return []
}

const splitFullName = (value?: string | null): { first: string; last: string } => {
  if (!value || typeof value !== 'string') return { first: '', last: '' }
  const parts = value
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
  if (parts.length === 0) return { first: '', last: '' }
  if (parts.length === 1) return { first: parts[0], last: '' }
  return { first: parts.shift() || '', last: parts.join(' ') }
}

const employmentSnapshot = (row: EmploymentRow): EmploymentSnapshot => ({
  employer_name: row.employer_name.trim(),
  country: row.country.trim().toUpperCase(),
  position: row.position.trim(),
  start_date: row.start_date ? row.start_date.slice(0, 10) : '',
  end_date: row.end_date ? row.end_date.slice(0, 10) : '',
})

const employmentRowHasData = (snapshot: EmploymentSnapshot): boolean => {
  return Boolean(
    snapshot.employer_name ||
    snapshot.country ||
    snapshot.position ||
    snapshot.start_date ||
    snapshot.end_date
  )
}

const employmentPayloadFromSnapshot = (snapshot: EmploymentSnapshot) => ({
  employer_name: snapshot.employer_name,
  country: snapshot.country || null,
  position: snapshot.position || null,
  start_date: snapshot.start_date,
  end_date: snapshot.end_date || null,
})

const candidateEmploymentToRow = (record: CandidateEmploymentRecord): EmploymentRow => makeEmploymentRow({
  id: record.id,
  employer_name: record.employer_name ?? '',
  country: record.country ?? '',
  position: record.position ?? '',
  start_date: record.start_date ? String(record.start_date).slice(0, 10) : '',
  end_date: record.end_date ? String(record.end_date).slice(0, 10) : '',
})

const legacyEmploymentEntryToRow = (entry: EmploymentEntry): EmploymentRow => makeEmploymentRow({
  employer_name: entry?.employer || '',
  country: entry?.country || '',
  position: entry?.position || '',
  start_date: entry?.date_from || '',
  end_date: entry?.date_to || '',
})

const sanitizeExtra = (extra?: Partial<CandidateExtra> | null, fallback?: CandidateExtra | null): CandidateExtra => {
  const merged: Record<string, any> = {
    phone_country: '',
    phone_prefix: '',
    address: makeAddress(),
    reg_address_diff: false,
    reg_address: makeAddress(),
    birth_date: '',
    citizenship: '',
    license_number: '',
    license_categories: [],
    previous_employers: [],
    experience_years: null,
    experience_eu_years: null,
    experience_non_eu_years: null,
    experience_ce_total: null,
    in_poland: null,
    poland_stay_basis: '',
    preferred_contact: '',
    first_contact_at: '',
    employment_history: [],
    trailer_types: [],
    route_types: [],
    intl_experience: null,
    eu_routes: null,
    documents: {},
    ...(fallback || {}),
    ...(extra || {}),
  }

  const result: Record<string, any> = { ...merged }
  result.address = makeAddress({
    ...(fallback?.address || {}),
    ...((extra as any)?.address || {}),
  })
  result.reg_address = makeAddress({
    ...(fallback?.reg_address || {}),
    ...((extra as any)?.reg_address || {}),
  })
  result.phone_country = merged.phone_country ? String(merged.phone_country) : ''
  result.phone_prefix = merged.phone_prefix ? String(merged.phone_prefix) : ''
  result.birth_date = merged.birth_date ? String(merged.birth_date).slice(0, 10) : ''
  result.citizenship = merged.citizenship ? String(merged.citizenship) : ''
  result.license_number = merged.license_number ? String(merged.license_number) : ''
  result.reg_address_diff = Boolean(merged.reg_address_diff)
  result.license_categories = Array.isArray(merged.license_categories)
    ? merged.license_categories.map(String).filter(Boolean)
    : []
  result.previous_employers = Array.isArray(merged.previous_employers)
    ? merged.previous_employers.map(String).filter(Boolean)
    : []
  result.preferred_contact = merged.preferred_contact ? String(merged.preferred_contact) : ''
  result.first_contact_at = merged.first_contact_at ? String(merged.first_contact_at) : ''
  const euYearsRaw = merged.experience_eu_years ?? merged.experience_years ?? null
  const nonEuYearsRaw = merged.experience_non_eu_years ?? null
  const euYears = typeof euYearsRaw === 'number' && !Number.isNaN(euYearsRaw) ? euYearsRaw : null
  const nonEuYears = typeof nonEuYearsRaw === 'number' && !Number.isNaN(nonEuYearsRaw) ? nonEuYearsRaw : null
  const totalYears = merged.experience_ce_total ?? (
    (euYears ?? 0) + (nonEuYears ?? 0)
  )
  result.experience_eu_years = euYears
  result.experience_non_eu_years = nonEuYears
  result.experience_ce_total = typeof totalYears === 'number' && !Number.isNaN(totalYears) ? Number(totalYears) : null
  result.employment_history = sanitizeEmploymentHistory(
    merged.employment_history && Array.isArray(merged.employment_history)
      ? merged.employment_history
      : merged.previous_employers
  )
  result.in_poland = typeof merged.in_poland === 'boolean'
    ? merged.in_poland
    : (merged.in_poland === null ? null : Boolean(merged.in_poland))
  result.poland_stay_basis = merged.poland_stay_basis ? String(merged.poland_stay_basis) : ''
  result.trailer_types = Array.isArray(merged.trailer_types)
    ? merged.trailer_types.map((item: any) => String(item)).filter(Boolean)
    : []
  result.route_types = Array.isArray(merged.route_types)
    ? merged.route_types.map((item: any) => String(item)).filter(Boolean)
    : []
  if (merged.intl_experience === true || merged.intl_experience === false) {
    result.intl_experience = merged.intl_experience
  } else {
    result.intl_experience = null
  }
  if (merged.eu_routes === true || merged.eu_routes === false) {
    result.eu_routes = merged.eu_routes
  } else {
    result.eu_routes = null
  }
  delete (result as any).documents
  return result as CandidateExtra
}

const sanitizeDocsProgress = (value: any, fallback?: Record<string, any> | null): Record<string, any> => {
  const base = { ...(fallback || {}) }
  if (value == null) return { ...base }
  let source = value
  if (typeof source === 'string') {
    try {
      source = JSON.parse(source)
    } catch {
      return { ...base }
    }
  }
  if (typeof source === 'object' && !Array.isArray(source)) {
    return { ...base, ...source }
  }
  return { ...base }
}

const normalizeLanguages = (value: any, fallback: string[] = []): string[] => {
  if (Array.isArray(value)) {
    return value.map(v => String(v).trim()).filter(Boolean)
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return [...fallback]
    if (trimmed.startsWith('[')) {
      try {
        return normalizeLanguages(JSON.parse(trimmed), fallback)
      } catch {
        // fallthrough to CSV split
      }
    }
    return trimmed.split(',').map(s => s.trim()).filter(Boolean)
  }
  return [...fallback]
}

const currencyFmt = new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' })
const formatAmount = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return '-'
  try {
    return currencyFmt.format(value)
  } catch {
    return value.toFixed(2)
  }
}

const isUuidLike = (value: unknown): value is string =>
  typeof value === 'string' && UUID_RE.test(value)

const POLAND_BASIS_VALUES = ['', 'visa_d', 'visa_c', 'karta_pobytu', 'eu_citizen', 'other']

const mapResidencyStatusToPolandBasis = (value?: string): string => {
  if (!value) return ''
  const normalized = value.toLowerCase()
  if (normalized === 'eu_citizen') return 'eu_citizen'
  if (normalized === 'visa_c') return 'visa_c'
  if (normalized === 'visa_d' || normalized === 'visa') return 'visa_d'
  if (normalized === 'card' || normalized === 'karta_pobytu') return 'karta_pobytu'
  if (normalized === 'other' || normalized === 'none') return 'other'
  return ''
}
const TRAILER_TYPE_KEYS = [
  'mega',
  'standard',
  'platform',
  'frigo',
  'tent',
  'container',
  'tandem',
  'car_transporter',
] as const
const ROUTE_TYPE_KEYS = ['eu', 'cis', 'uk', 'scandi', 'local'] as const

const pickKeys = (source: Record<string, any>, allowed: Set<string>): Record<string, any> => {
  const result: Record<string, any> = {}
  for (const [key, val] of Object.entries(source)) {
    if (!allowed.has(key)) continue
    if (val === undefined) continue
    result[key] = val
  }
  return result
}

const createEmptyCandidate = (stage?: string | null): Candidate => {
  const extra = sanitizeExtra()
  return {
    id: '' as UUID,
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    languages: [],
    stage: stage || '',
    manager: '',
    short_id: null,
    company_id: null,
    vacancy_id: null,
    docs_progress: {},
    status_reason: [],
    extra,
    note: '',
  } as Candidate
}

const formatDateTime = (value?: string | null): string => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString()
}

const parseJSONSafe = <T,>(value: unknown, fallback: T): T => {
  if (value == null) return fallback
  if (typeof value === 'object') return value as T
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return (parsed ?? fallback) as T
    } catch {
      return fallback
    }
  }
  return fallback
}

function normalizeCandidate(raw: any, prev?: Candidate | null): Candidate {
  const previous = prev ?? null
  const prevExtra = previous?.extra ? sanitizeExtra(previous.extra) : sanitizeExtra()
  const personalData = parseJSONSafe<Record<string, any>>(raw?.personal_data, previous?.personal_data || {})
  const contactsData = parseJSONSafe<Record<string, any>>(raw?.contacts, previous?.contacts || {})
  const intakeContacts = parseJSONSafe<Record<string, any>>(raw?.intake_contacts, previous?.intake_contacts || contactsData)
  const intakePersonal = parseJSONSafe<Record<string, any>>(raw?.intake_personal, previous?.intake_personal || personalData)
  const intakeExperience = parseJSONSafe<Record<string, any>>(raw?.intake_experience, previous?.intake_experience || intakePersonal?.experience || {})
  const intakeAgreements = parseJSONSafe<Record<string, any>>(raw?.intake_agreements, previous?.intake_agreements || {})
  const extraFromRaw = parseJSONSafe<Partial<CandidateExtra>>(raw?.extra, {})
  const intakeFullName =
    typeof intakePersonal?.full_name === 'string'
      ? intakePersonal.full_name
      : ''
  const intakeNameParts = splitFullName(intakeFullName)
  const intakeCitizenship = typeof intakePersonal?.citizenship === 'string' ? intakePersonal.citizenship : ''
  const intakeResidencyStatus = typeof intakePersonal?.residency_status === 'string' ? intakePersonal.residency_status : ''
  const intakeResidencyBasis = mapResidencyStatusToPolandBasis(intakeResidencyStatus)
  const intakeEmail = typeof intakeContacts?.email === 'string' ? intakeContacts.email.trim() : ''
  const intakePhone = typeof intakeContacts?.phone === 'string' ? intakeContacts.phone.trim() : ''
  const intakePhoneCode =
    typeof intakeContacts?.phone_country_code === 'string'
      ? intakeContacts.phone_country_code.trim()
      : ''

  const extraFallback = { ...prevExtra }
  if (!extraFallback.citizenship) {
    if (typeof personalData?.citizenship === 'string') {
      extraFallback.citizenship = personalData.citizenship
    } else if (intakeCitizenship) {
      extraFallback.citizenship = intakeCitizenship
    }
  }
  if (!extraFallback.preferred_contact && typeof intakeContacts?.preferred_messenger === 'string') {
    extraFallback.preferred_contact = intakeContacts.preferred_messenger
  }
  if (!extraFallback.phone_prefix && intakePhoneCode.startsWith('+')) {
    extraFallback.phone_prefix = intakePhoneCode
  }
  if (!extraFallback.phone_country && intakePhoneCode && !intakePhoneCode.startsWith('+')) {
    extraFallback.phone_country = intakePhoneCode
  }
  if (extraFallback.experience_ce_total == null || Number.isNaN(extraFallback.experience_ce_total)) {
    const rawYears = intakeExperience?.years_ce
    const yearsCe = typeof rawYears === 'number'
      ? rawYears
      : rawYears != null && `${rawYears}`.trim()
        ? Number.parseFloat(String(rawYears))
        : null
    if (typeof yearsCe === 'number' && !Number.isNaN(yearsCe)) {
      extraFallback.experience_ce_total = yearsCe
    }
  }
  if (!extraFallback.poland_stay_basis && intakeResidencyBasis) {
    extraFallback.poland_stay_basis = intakeResidencyBasis
  }
  if ((!extraFallback.trailer_types || extraFallback.trailer_types.length === 0) && Array.isArray(intakeExperience?.trailer_types)) {
    extraFallback.trailer_types = intakeExperience.trailer_types.map((item: any) => String(item)).filter(Boolean)
  }
  if ((!extraFallback.route_types || extraFallback.route_types.length === 0) && Array.isArray(intakeExperience?.route_types)) {
    extraFallback.route_types = intakeExperience.route_types.map((item: any) => String(item)).filter(Boolean)
  }
  if (extraFallback.intl_experience == null && typeof intakeExperience?.intl_experience === 'boolean') {
    extraFallback.intl_experience = intakeExperience.intl_experience
  }
  if (extraFallback.eu_routes == null && typeof intakeExperience?.eu_routes === 'boolean') {
    extraFallback.eu_routes = intakeExperience.eu_routes
  }

  const mergedExtra = sanitizeExtra(extraFromRaw, extraFallback)
  if (!mergedExtra.preferred_contact && typeof intakeContacts?.preferred_messenger === 'string') {
    mergedExtra.preferred_contact = intakeContacts.preferred_messenger
  }
  if (!mergedExtra.citizenship) {
    if (typeof personalData?.citizenship === 'string') {
      mergedExtra.citizenship = personalData.citizenship
    } else if (intakeCitizenship) {
      mergedExtra.citizenship = intakeCitizenship
    }
  }
  if (!mergedExtra.poland_stay_basis && intakeResidencyBasis) {
    mergedExtra.poland_stay_basis = intakeResidencyBasis
  }
  if (!mergedExtra.phone_prefix && intakePhoneCode.startsWith('+')) {
    mergedExtra.phone_prefix = intakePhoneCode
  }
  if (!mergedExtra.phone_country && intakePhoneCode && !intakePhoneCode.startsWith('+')) {
    mergedExtra.phone_country = intakePhoneCode
  }
  if ((!mergedExtra.trailer_types || mergedExtra.trailer_types.length === 0) && Array.isArray(intakeExperience?.trailer_types)) {
    mergedExtra.trailer_types = intakeExperience.trailer_types.map((item: any) => String(item)).filter(Boolean)
  }
  if ((!mergedExtra.route_types || mergedExtra.route_types.length === 0) && Array.isArray(intakeExperience?.route_types)) {
    mergedExtra.route_types = intakeExperience.route_types.map((item: any) => String(item)).filter(Boolean)
  }

  const existingAddress =
    mergedExtra && typeof mergedExtra.address === 'object' && mergedExtra.address
      ? mergedExtra.address
      : undefined
  const backendAddress =
    raw?.address && typeof raw.address === 'object' ? (raw.address as Partial<AddressFields>) : undefined
  const mergedAddress = makeAddress({
    ...(existingAddress || {}),
    ...(backendAddress || {}),
  })
  if (raw?.country_code) mergedAddress.country = String(raw.country_code)
  if (raw?.city) mergedAddress.city = String(raw.city)
  mergedExtra.address = mergedAddress
  if (raw?.birth_date) mergedExtra.birth_date = String(raw.birth_date).slice(0, 10)
  if (raw?.phone_country_code) mergedExtra.phone_prefix = String(raw.phone_country_code)

  const docsProgress = sanitizeDocsProgress(
    raw?.docs_progress,
    previous?.docs_progress && typeof previous.docs_progress === 'object' ? previous.docs_progress : {}
  )

  const languages = normalizeLanguages(raw?.languages, previous?.languages || [])
  const note = raw?.note ?? raw?.notes ?? previous?.note ?? null
  const statusReason =
    Array.isArray(raw?.status_reason)
      ? raw.status_reason.filter((code: any) => typeof code === 'string' && code.trim()).map((code: string) => code.trim())
      : Array.isArray(previous?.status_reason)
        ? previous.status_reason.filter(code => typeof code === 'string' && code.trim())
        : []

  const managerId =
    (raw?.manager_id && isUuidLike(raw.manager_id) && String(raw.manager_id))
    || (isUuidLike(raw?.manager) ? String(raw.manager) : undefined)
    || (isUuidLike((previous as any)?.manager_id) ? String((previous as any).manager_id) : undefined)
    || (isUuidLike(previous?.manager) ? String(previous?.manager) : null)

  const managerDisplayName =
    raw?.manager_name ??
    (managerId ? (raw?.manager_name ?? previous?.manager_name ?? null) : null) ??
    (typeof raw?.manager === 'string' && !isUuidLike(raw.manager) ? raw.manager : previous?.manager_name ?? null)

  const result: Candidate = {
    ...(previous ?? {} as Candidate),
    ...raw,
    id: String(raw?.id ?? previous?.id ?? ''),
    first_name: raw?.first_name ?? previous?.first_name ?? intakeNameParts.first ?? '',
    last_name: raw?.last_name ?? previous?.last_name ?? intakeNameParts.last ?? '',
    email: raw?.email ?? previous?.email ?? intakeEmail ?? '',
    phone: raw?.phone ?? previous?.phone ?? intakePhone ?? '',
    stage: raw?.stage ?? previous?.stage ?? '',
    manager: managerId ?? '',
    manager_name: managerDisplayName ?? null,
    company_id: raw?.company_id ?? previous?.company_id ?? null,
    vacancy_id: raw?.vacancy_id ?? previous?.vacancy_id ?? null,
    company_name: raw?.company_name ?? previous?.company_name ?? '',
    vacancy_name: raw?.vacancy_name ?? previous?.vacancy_name ?? '',
    short_id: raw?.short_id ?? previous?.short_id ?? null,
    phone_country_code:
      raw?.phone_country_code ??
      previous?.phone_country_code ??
      (intakePhoneCode || ''),
    languages,
    docs_progress: docsProgress,
    status_reason: statusReason,
    extra: mergedExtra,
    note,
    personal_data: personalData,
    contacts: contactsData,
    intake_status: raw?.intake_status ?? previous?.intake_status ?? null,
    intake_submitted_at: raw?.intake_submitted_at ?? previous?.intake_submitted_at ?? null,
    intake_contacts: intakeContacts,
    intake_personal: intakePersonal,
    intake_experience: intakeExperience,
    intake_agreements: intakeAgreements,
  } as Candidate

  if (!managerId && typeof raw?.manager === 'string' && !isUuidLike(raw.manager)) {
    (result as any).manager_display = raw.manager
  }
  if (managerId) {
    (result as any).manager_id = managerId
  }

  return result
}

const toArray = (value: any) =>
  Array.isArray(value)
    ? value
    : Array.isArray(value?.items)
      ? value.items
      : Array.isArray(value?.data)
        ? value.data
        : []

function useClickOutside<T extends HTMLElement>(onOutside: () => void) {
  const ref = useRef<T | null>(null)
  useEffect(() => {
    function handler(e: MouseEvent) {
      const el = ref.current
      if (!el) return
      if (!el.contains(e.target as Node)) onOutside()
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') onOutside()
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', onEsc)
    }
  }, [onOutside])
  return ref
}

/* ---------- searchable select ---------- */
function SearchableSelect({
  options,
  value,
  onChange,
  placeholder,
  className,
  searchPlaceholder,
  noResultsLabel,
}: {
  options: Option[];
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
  searchPlaceholder?: string;
  noResultsLabel?: string;
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const current = useMemo(() => options.find(o => o.value === value)?.label || '', [options, value])
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return options
    return options.filter((option: Option) => option.label.toLowerCase().includes(s) || option.value.toLowerCase().includes(s))
  }, [q, options])
  const close = () => setOpen(false)
  const boxRef = useClickOutside<HTMLDivElement>(close)

  return (
    <div className={clsx('relative', className)} ref={boxRef}>
      <button
        type="button"
        className="input w-full text-left"
        onClick={() => { setOpen(o => !o); setQ('') }}
      >
        {current || (placeholder || '— select —')}
      </button>
      {open && (
        <div className="absolute z-20 mt-2 w-full rounded-xl border bg-white shadow-xl">
          <div className="p-2">
            <input
              autoFocus
              className="input"
              placeholder={searchPlaceholder || 'Search…'}
              value={q}
              onChange={e => setQ(e.target.value)}
            />
          </div>
          <div className="max-h-64 overflow-auto">
            {filtered.length === 0 && <div className="px-3 py-2 text-gray-500">{noResultsLabel || 'No matches'}</div>}
            {filtered.map((o: Option) => (
              <button
                key={o.value}
                type="button"
                className={clsx('w-full px-3 py-2 text-left hover:bg-gray-50', o.value === value && 'bg-gray-50')}
                onClick={() => { onChange(o.value); close() }}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ---------- checkbox multiselect ---------- */
function CheckboxMultiSelect({
  options,
  values,
  onChange,
  placeholder,
  className,
  searchPlaceholder,
  noResultsLabel,
  multiSelectedLabel,
}: {
  options: Option[];
  values: string[];
  onChange: (vals: string[]) => void;
  placeholder?: string;
  className?: string;
  searchPlaceholder?: string;
  noResultsLabel?: string;
  multiSelectedLabel?: (count: number) => string;
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const boxRef = useClickOutside<HTMLDivElement>(() => setOpen(false))
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return options
    return options.filter((option: Option) => option.label.toLowerCase().includes(s) || option.value.toLowerCase().includes(s))
  }, [q, options])
  const toggle = (v: string) => {
    const set = new Set(values)
    set.has(v) ? set.delete(v) : set.add(v)
    onChange(Array.from(set))
  }
  const caption = values.length === 0
    ? (placeholder || 'Not selected')
    : (values.length <= 3
        ? values
            .map((v) => {
              const found = options.find((option: Option) => option.value === v)
              return found?.label || v
            })
            .join(', ')
        : multiSelectedLabel
          ? multiSelectedLabel(values.length)
          : `${values.length} selected`)

  return (
    <div className={clsx('relative', className)} ref={boxRef}>
      <button type="button" className="input w-full text-left" onClick={() => { setOpen(o=>!o); setQ('') }}>
        {caption}
      </button>
      {open && (
        <div className="absolute z-20 mt-2 w-full rounded-xl border bg-white shadow-xl">
          <div className="p-2">
            <input
              autoFocus
              className="input"
              placeholder={searchPlaceholder || 'Search…'}
              value={q}
              onChange={e => setQ(e.target.value)}
            />
          </div>
          <div className="max-h-72 overflow-auto">
            {filtered.length === 0 && <div className="px-3 py-2 text-gray-500">{noResultsLabel || 'No matches'}</div>}
            {filtered.map((o: Option) => {
              const checked = values.includes(o.value)
              return (
                <label
                  key={o.value}
                  className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer"
                  onClick={() => toggle(o.value)}
                >
                  <input type="checkbox" readOnly checked={checked} />
                  <span>{o.label}</span>
                </label>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

/* --------------------------------- инпуты --------------------------------- */
type InputProps = InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string; containerClassName?: string }
const Input = (props: InputProps) => {
  const { label, hint, className, containerClassName, ...rest } = props
  const isReadOnly = rest.readOnly || rest.disabled
  return (
    <label className={clsx('block', containerClassName)}>
      {label && <div className="label">{label}</div>}
      <input
        {...rest}
        className={clsx(
          'input',
          isReadOnly && 'bg-gray-100 text-gray-600 cursor-not-allowed',
          className,
        )}
      />
      {hint && <p className="mt-1 text-xs text-gray-500">{hint}</p>}
    </label>
  )
}

const Checkbox = ({ label, checked, onChange }:{
  label: string; checked?: boolean; onChange?: (v:boolean)=>void
}) => (
  <label className="flex items-center gap-2">
    <input type="checkbox" checked={!!checked} onChange={e=>onChange?.(e.currentTarget.checked)} />
    <span>{label}</span>
  </label>
)

/* ------------------------------- основная страница ------------------------------- */
export default function CandidateCard(){
  const { t } = useI18n()
  const unknownErrorLabel = t('common.errors.unknown')
  const { id } = useParams<{id: UUID | 'new'}>()
  const isNew = id === 'new'
  const nav = useNavigate()
  const { can } = usePermissions()
  const canRequestDelete = can('candidates.requestDelete')
  const canDeleteDirect = can('admin.deletionQueue') || can('admin.users')

  const meta = useMetaStages()
  const stageOptions = useMemo(() => (meta?.order || meta?.codes || []), [meta])
  const stageLabelIntl = useCallback((code: string) => {
    const fallback = meta?.labels?.[code] || code
    return translateStageLabel(t, code, fallback)
  }, [meta?.labels, t])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savedOk, setSavedOk] = useState(false)
  const [tab, setTab] = useState<Tab>('personal')
  const [model, setModel] = useState<Candidate | null>(null)
  const [deleteRequestLoading, setDeleteRequestLoading] = useState(false)
  const [deleteRequestMessage, setDeleteRequestMessage] = useState<string | null>(null)
  const [deleteRequestError, setDeleteRequestError] = useState<string | null>(null)

  // каталоги
  const [countries, setCountries] = useState<Option[]>([])
  const [languages, setLanguages] = useState<Option[]>([])
  const [dialCodes, setDialCodes] = useState<Option[]>([])
  const [managers, setManagers] = useState<Option[]>([])
  const [vacancyOpts, setVacancyOpts] = useState<Option[]>([])
  const [notes, setNotes] = useState<CandidateNote[]>([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [newNote, setNewNote] = useState('')
  const [noteSending, setNoteSending] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [stageHistory, setStageHistory] = useState<StageHistoryEntry[]>([])
  const [historyInfo, setHistoryInfo] = useState<string | null>(null)
  const [employmentRows, setEmploymentRows] = useState<EmploymentRow[]>([])
  const [employmentBaseline, setEmploymentBaseline] = useState<Record<string, EmploymentSnapshot>>({})
  const [employmentLoading, setEmploymentLoading] = useState(false)
  const [employmentError, setEmploymentError] = useState<string | null>(null)
  const basicRef = useRef<HTMLDivElement | null>(null)
  const personalRef = useRef<HTMLDivElement | null>(null)
  const statusRef = useRef<HTMLDivElement | null>(null)
  const experienceRef = useRef<HTMLDivElement | null>(null)
  const employerRef = useRef<HTMLDivElement | null>(null)
  const notesRef = useRef<HTMLDivElement | null>(null)
  const employmentInitRef = useRef(false)
  const dialCodeIndex = useMemo(() => {
    return dialCodes
      .map((opt) => {
        const prefix = typeof opt.extra?.prefix === 'string' ? opt.extra.prefix.trim() : ''
        if (!prefix) return null
        const digits = prefix.replace(/\D/g, '')
        if (!digits) return null
        return {
          country: opt.value,
          prefix,
          normalized: `+${digits}`,
        }
      })
      .filter((entry): entry is { country: string; prefix: string; normalized: string } => Boolean(entry))
      .sort((a, b) => b.normalized.length - a.normalized.length)
  }, [dialCodes])
  const preferredContactOptions = useMemo(
    () =>
      PREFERRED_CONTACT_VALUES.map((value) => ({
        value,
        label: t(`app.candidate_card.contacts.options.${value || 'none'}`),
      })),
    [t]
  )
  const polandBasisOptions = useMemo(
    () =>
      POLAND_BASIS_VALUES.map((value) => ({
        value,
        label: t(`app.candidate_card.status.poland_basis.${value || 'none'}`),
      })),
    [t]
  )
  const trailerTypeLabels = useMemo(() => {
    const map: Record<string, string> = {}
    TRAILER_TYPE_KEYS.forEach((key) => {
      map[key] = t(`app.candidate_card.intake.trailers.${key}`)
    })
    return map
  }, [t])
  const trailerTypeOptions = useMemo(
    () => TRAILER_TYPE_KEYS.map((key) => ({ value: key, label: trailerTypeLabels[key] })),
    [trailerTypeLabels]
  )
  const routeTypeLabels = useMemo(() => {
    const map: Record<string, string> = {}
    ROUTE_TYPE_KEYS.forEach((key) => {
      map[key] = t(`app.candidate_card.intake.routes.${key}`)
    })
    return map
  }, [t])
  const routeTypeOptions = useMemo(
    () => ROUTE_TYPE_KEYS.map((key) => ({ value: key, label: routeTypeLabels[key] })),
    [routeTypeLabels]
  )
  const detectPhoneParts = useCallback((rawValue: string) => {
    if (!rawValue || !dialCodeIndex.length) return null
    const trimmed = rawValue.trim()
    if (!trimmed) return null
    let normalized = trimmed.replace(/[^\d+]/g, '')
    if (!normalized) return null
    normalized = normalized.replace(/(?!^)\+/g, '')
    while (normalized.startsWith('00')) {
      normalized = `+${normalized.slice(2)}`
    }
    if (!normalized.startsWith('+') || normalized === '+') return null
    const match = dialCodeIndex.find((entry) => normalized.startsWith(entry.normalized))
    if (!match) return null
    const localNumber = normalized.slice(match.normalized.length)
    return {
      country: match.country,
      prefix: match.prefix,
      number: localNumber,
    }
  }, [dialCodeIndex])
  const selectTexts = useMemo(
    () => ({
      empty: t('app.candidate_card.select.empty'),
      search: t('app.candidate_card.select.search'),
      noResults: t('app.candidate_card.select.no_results'),
      multiNone: t('app.candidate_card.select.multi_none'),
      multiSelected: (count: number) => t('app.candidate_card.select.multi_selected', { values: { count } }),
    }),
    [t]
  )
  const validateEmploymentRows = useCallback(
    (rows: EmploymentRow[]): string | null => {
      for (const row of rows) {
        const snapshot = employmentSnapshot(row)
        if (!employmentRowHasData(snapshot)) continue
        if (!snapshot.employer_name) {
          return t('app.candidate_card.errors.employment.missing_employer')
        }
        if (!snapshot.start_date) {
          return t('app.candidate_card.errors.employment.missing_start')
        }
        if (snapshot.end_date && snapshot.end_date < snapshot.start_date) {
          return t('app.candidate_card.errors.employment.end_before_start')
        }
      }
      return null
    },
    [t]
  )

  // загрузка каталогов (один раз)
  useEffect(() => {
    (async () => {
      try{
        const [c, l, d, m, v] = await Promise.all([
          api.get('/catalogs/countries'),
          api.get('/catalogs/languages'),
          api.get('/catalogs/dial-codes'),
          api.get('/catalogs/managers').catch(()=>({ data: [] })),
          api.get('/vacancies/').catch(()=>({ data: [] })),
        ])

        // countries / languages
        const countriesArr: Option[] = toArray(c.data).map((x: any) => ({
          value: String(x.code ?? x.id ?? ''),
          label: String(x.name ?? x.label ?? x.code ?? ''),
        })).filter((o: Option) => o.value && o.label)
        setCountries(countriesArr)
        setLanguages(
          toArray(l.data)
            .map((x: any) => ({ value: String(x.code ?? x.id ?? ''), label: String(x.name ?? x.label ?? x.code ?? '') }))
            .filter((o: Option) => o.value && o.label)
        )

        // dial-codes: поддерживаем и [{country,dial_code}], и {CC:"+XXX"}
        const dcMap = new Map<string,string>()
        if (Array.isArray(d.data)) {
          (d.data as any[]).forEach((x: any) => {
            if (x?.country && x?.dial_code) dcMap.set(String(x.country), String(x.dial_code))
          })
        } else if (d.data && typeof d.data === 'object') {
          Object.entries(d.data).forEach(([k, v]) => {
            const value = (v as any)
            const dial = value?.dial_code ?? value
            if (dial) dcMap.set(String(k), String(dial))
          })
        }

        const dcList: Option[] = countriesArr
          .map((cn: Option) => {
            const prefix = dcMap.get(cn.value) || ''
            const flag = /^[A-Z]{2}$/.test(cn.value) ? `${ccToFlag(cn.value)} ` : ''
            return {
              value: cn.value,
              label: `${flag}${cn.label}${prefix ? ` (${prefix})` : ''}`,
              extra: { prefix }
            } as Option
          })
          .filter((o: Option) => !!o.extra?.prefix)
          .sort((a: Option, b: Option) => a.label.localeCompare(b.label, 'ru'))
        setDialCodes(dcList)

        // managers
        const mgrList: Option[] = toArray(m.data).map((x:any)=>({
          value: String(x.id ?? x.user_id ?? x.uuid ?? ''),
          label: x.label || x.full_name || x.email || x.name || String(x.id ?? ''),
        })).filter((o: Option) => o.value && o.label)
        // добавляем текущего пользователя (рекрутер) если его нет в списке
        try {
          const meResp = await api.get('/users/me').catch(()=>null)
          const meId = meResp?.data?.id || meResp?.data?.user_id || meResp?.data?.sub
          const meName = meResp?.data?.full_name || meResp?.data?.email || meId
          if (meId && !mgrList.some(opt => opt.value === String(meId))) {
            mgrList.push({ value: String(meId), label: String(meName || meId) })
          }
        } catch {/* ignore */}
        setManagers(mgrList)

        // vacancies
        const vacs: Vacancy[] = toArray(v.data)
        setVacancyOpts(
          vacs.map((item: Vacancy) => ({
            value: String(item.id),
            label: item.title,
            extra: {
              company_id: (item as any).company_id,
              company_name: (item as any).company?.name || (item as any).company_name || '',
            },
          }))
        )
      } finally {
        // no-op
      }
    })()
  }, [])

  useEffect(() => {
    if (!model?.manager) return
    if (!isUuidLike(model.manager)) return
    const managerId = model.manager as string
    setManagers(prev => {
      if (prev.some(opt => opt.value === managerId)) return prev
      const label = model.manager_name || managerId
      const option: Option = { value: managerId, label }
      return [...prev, option]
    })
  }, [model?.manager, model?.manager_name])

  useEffect(() => {
    if (!model?.vacancy_id) return
    const vacancyId = String(model.vacancy_id)
    setVacancyOpts(prev => {
      if (prev.some(opt => opt.value === vacancyId)) return prev
      const option: Option = {
        value: vacancyId,
        label: model.vacancy_name || t('app.candidate_card.labels.current_vacancy'),
        extra: { company_id: model.company_id, company_name: model.company_name },
      }
      return [...prev, option]
    })
  }, [model?.vacancy_id, model?.vacancy_name, model?.company_id, model?.company_name, t])

  useEffect(() => {
    if (!isNew) return
    const nextStage = meta?.order?.[0] || meta?.codes?.[0]
    if (!nextStage) return
    setModel(m => {
      if (!m) return m
      if ((m.stage || '').trim()) return m
      return { ...m, stage: nextStage }
    })
  }, [isNew, meta])

  // загрузка кандидата / инициализация нового
  useEffect(() => {
    (async () => {
      setLoading(true)
      try{
        if (isNew) {
          const defaultStage = meta?.order?.[0] || meta?.codes?.[0] || 'new'
          setModel(createEmptyCandidate(defaultStage))
        } else {
          const { data } = await api.get(`/candidates/${id}`)
          const normalized = normalizeCandidate(data, model)
          setModel(normalized)
        }
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, isNew])

  const applyEmploymentRecords = useCallback((records: CandidateEmploymentRecord[]) => {
    const nextRows = records.map(candidateEmploymentToRow)
    setEmploymentRows(nextRows)
    const baseline: Record<string, EmploymentSnapshot> = {}
    nextRows.forEach(row => {
      if (row.id) {
        baseline[row.id] = employmentSnapshot(row)
      }
    })
    setEmploymentBaseline(baseline)
  }, [])

  const reloadCandidateEmployments = useCallback(async (candidateId: string, opts: { withSpinner?: boolean } = {}) => {
    if (!candidateId) return
    if (opts.withSpinner !== false) setEmploymentLoading(true)
    setEmploymentError(null)
    try {
      const records = await listCandidateEmployments(candidateId)
      applyEmploymentRecords(records)
    } catch (err: any) {
      console.error('[CandidateCard] employment list error', err)
      const r = err?.response?.data
      const detail = typeof r?.detail === 'string'
        ? r.detail
        : (r ? JSON.stringify(r) : err?.message || t('app.candidate_card.errors.employment.load_failed'))
      setEmploymentError(detail)
    } finally {
      if (opts.withSpinner !== false) setEmploymentLoading(false)
    }
  }, [applyEmploymentRecords, t])

  const syncEmploymentRows = useCallback(async (candidateId: string) => {
    if (!candidateId) return
    const validationError = validateEmploymentRows(employmentRows)
    if (validationError) {
      setEmploymentError(validationError)
      throw new Error(validationError)
    }
    setEmploymentError(null)
    const current = employmentRows
      .map(row => ({ row, snapshot: employmentSnapshot(row) }))
      .filter(({ snapshot }) => employmentRowHasData(snapshot))

    const currentIds = new Set(
      current
        .map(({ row }) => row.id)
        .filter((value): value is string => typeof value === 'string' && value.length > 0),
    )

    const toCreate = current.filter(({ row }) => !row.id)
    const toUpdate = current.filter(({ row, snapshot }) => {
      if (!row.id) return false
      const baseline = employmentBaseline[row.id]
      if (!baseline) return true
      return (
        baseline.employer_name !== snapshot.employer_name ||
        baseline.country !== snapshot.country ||
        baseline.position !== snapshot.position ||
        baseline.start_date !== snapshot.start_date ||
        baseline.end_date !== snapshot.end_date
      )
    })
    const toDelete = Object.keys(employmentBaseline).filter((id) => !currentIds.has(id))

    if (!toCreate.length && !toUpdate.length && !toDelete.length) {
      return
    }

    for (const id of toDelete) {
      await deleteCandidateEmployment(candidateId, id)
    }
    for (const { row, snapshot } of toUpdate) {
      if (!row.id) continue
      await updateCandidateEmployment(candidateId, row.id, employmentPayloadFromSnapshot(snapshot))
    }
    for (const { snapshot } of toCreate) {
      await createCandidateEmployment(candidateId, employmentPayloadFromSnapshot(snapshot))
    }
    await reloadCandidateEmployments(candidateId, { withSpinner: false })
  }, [employmentRows, employmentBaseline, reloadCandidateEmployments, validateEmploymentRows])

  // --- payload helpers (normalize to API contract) ---
  function buildCandidatePayload(
    m: Candidate,
    reasonChoices: Record<string, { code: string; label: string }[]> = {}
  ) {
    const extraData = sanitizeExtra(m.extra as CandidateExtra | undefined)
    const docsState = sanitizeDocsProgress(m.docs_progress)
    const languages = normalizeLanguages(m.languages, [])

    const extraForPayload = JSON.parse(JSON.stringify(extraData)) as Record<string, any>

    const euYears =
      typeof extraData.experience_eu_years === 'number' && !Number.isNaN(extraData.experience_eu_years)
        ? extraData.experience_eu_years
        : null
    const nonEuYears =
      typeof extraData.experience_non_eu_years === 'number' && !Number.isNaN(extraData.experience_non_eu_years)
        ? extraData.experience_non_eu_years
        : null
    if (euYears !== null || nonEuYears !== null) {
      extraForPayload.experience_eu_years = euYears
      extraForPayload.experience_non_eu_years = nonEuYears
      extraForPayload.experience_ce_total = (euYears ?? 0) + (nonEuYears ?? 0)
    } else {
      extraForPayload.experience_ce_total = null
    }

    if (Array.isArray(extraForPayload.employment_history)) {
      extraForPayload.employment_history = extraForPayload.employment_history
        .map((entry: any) => sanitizeEmploymentEntry(entry))
        .filter((entry: EmploymentEntry) =>
          Boolean(entry?.employer || entry?.country || entry?.position || entry?.date_from || entry?.date_to)
        )
    }
    delete extraForPayload.previous_employers
    delete extraForPayload.documents

    if (!extraForPayload.first_contact_at) {
      extraForPayload.first_contact_at = null
    }
    if (!extraForPayload.preferred_contact) {
      extraForPayload.preferred_contact = null
    }

    const payload: Record<string, any> = {
      first_name: (m.first_name || '').trim(),
      last_name: (m.last_name || '').trim(),
      languages,
      extra: extraForPayload,
      docs_progress: docsState,
    }

    if (m.email) {
      const emailVal = (m.email || '').trim()
      if (emailVal) payload.email = emailVal
    }

    const phoneVal = (m.phone || '').trim()
    if (phoneVal) payload.phone = phoneVal

    const phonePrefix = (extraData.phone_prefix || '').trim()
    if (phonePrefix) payload.phone_country_code = phonePrefix

    const stageVal = (m.stage || '').trim()
    if (stageVal) payload.stage = stageVal
    const stageReasonOptions = reasonChoices[stageVal] ?? []
    let statusReasonList: string[] = []
    if (Array.isArray(m.status_reason)) {
      const normalized = m.status_reason
        .map(code => (typeof code === 'string' ? code.trim() : ''))
        .filter(code => Boolean(code))
      if (stageReasonOptions.length > 0) {
        statusReasonList = normalized.filter(code =>
          stageReasonOptions.some(opt => opt.code === code)
        )
        payload.status_reason = statusReasonList
      } else if (normalized.length > 0) {
        // если этап больше не поддерживает причины — обнулим их
        payload.status_reason = []
      }
    } else if (stageReasonOptions.length > 0) {
      payload.status_reason = []
    }

    if (m.vacancy_id) payload.vacancy_id = String(m.vacancy_id)
    if (m.company_id) payload.company_id = String(m.company_id)

    const managerFromSelect = isUuidLike(m.manager) ? String(m.manager) : undefined
    const managerFromModel = (m as any).manager_id && isUuidLike((m as any).manager_id) ? String((m as any).manager_id) : undefined
    const managerId = managerFromSelect || managerFromModel
    if (managerId) {
      payload.manager = managerId
      payload.manager_id = managerId
    }

    const noteRaw = typeof m.note === 'string' ? m.note : ''
    const noteTrimmed = noteRaw.trim()
    if (m.note === null) {
      payload.note = null
    } else if (noteTrimmed) {
      payload.note = noteTrimmed
    }

    const candidateCountry = (m.country_code || '').trim()
    if (candidateCountry) {
      payload.country_code = candidateCountry
    }

    const addressPayload = extraData.address || makeAddress()
    const hasAddressData = Object.values(addressPayload).some(Boolean)
    if (hasAddressData) {
      payload.address = addressPayload
      if (addressPayload.city) payload.city = addressPayload.city
      if (!payload.country_code && addressPayload.country) payload.country_code = addressPayload.country
    }

    if (extraData.birth_date) {
      payload.birth_date = extraData.birth_date
    }

    return {
      payload,
      extraForState: extraData,
      docsProgressForState: docsState,
      managerId: managerId ?? null,
      noteForState: typeof m.note === 'string' ? m.note : (m.note ?? ''),
      statusReasonForState: stageReasonOptions.length > 0 ? statusReasonList : (Array.isArray(m.status_reason) ? m.status_reason : []),
    }
  }

  const fetchCandidate = useCallback(async (candidateId: string, prev?: Candidate | null) => {
    const { data } = await api.get(`/candidates/${candidateId}`)
    return normalizeCandidate(data, prev || model)
  }, [model])

  const fetchNotes = useCallback(async (candidateId: string) => {
    setNotesLoading(true)
    try{
      const { data } = await api.get(`/candidates/${candidateId}/notes`)
      if (Array.isArray(data)) setNotes(data as CandidateNote[])
    } finally {
      setNotesLoading(false)
    }
  }, [])

  const loadStageHistory = useCallback(async (candidateId: string) => {
    setHistoryLoading(true)
    setHistoryError(null)
    setHistoryInfo(null)
    try{
      const { data } = await api.get(`/candidates/${candidateId}/stage-history`)
      const entries = Array.isArray(data) ? data : []
      const normalized: StageHistoryEntry[] = entries.map((item: any, idx: number) => ({
        id: String(item?.id ?? `${item?.to_code ?? 'stage'}-${item?.at ?? idx}`),
        from_code: item?.from_code ?? null,
        to_code: item?.to_code ?? null,
        at: item?.at ?? null,
        actor: item?.actor ?? item?.actor_name ?? null,
        reason: item?.reason ?? null,
      }))
      setStageHistory(normalized)
      if (!normalized.length) {
        setHistoryInfo(t('app.candidate_card.history.empty'))
      }
    } catch (err: any) {
      console.error('[CandidateCard] stage history error', err)
      const r = err?.response?.data
      const status = err?.response?.status
      if (status === 404) {
        setStageHistory([])
        setHistoryInfo(t('app.candidate_card.history.unavailable'))
        setHistoryError(null)
      } else {
        const detail = typeof r?.detail === 'string'
          ? r.detail
          : (r ? JSON.stringify(r) : err?.message || unknownErrorLabel)
        setHistoryError(detail)
      }
    } finally {
      setHistoryLoading(false)
    }
  }, [t, unknownErrorLabel])

  const openHistoryModal = useCallback(() => {
    if (!model?.id) return
    setHistoryOpen(true)
    void loadStageHistory(String(model.id))
  }, [model?.id, loadStageHistory])

  const closeHistoryModal = useCallback(() => {
    setHistoryOpen(false)
    setHistoryError(null)
    setHistoryInfo(null)
  }, [])

  const reloadStageHistory = useCallback(() => {
    if (!model?.id) return
    void loadStageHistory(String(model.id))
  }, [model?.id, loadStageHistory])

  const handleScrollTo = useCallback((ref: RefObject<HTMLDivElement>) => {
    return () => {
      ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [])

  const candidateTitle = useMemo(() => {
    if (!model) return ''
    const parts = [model.first_name, model.last_name]
      .map((part) => (typeof part === 'string' ? part.trim() : ''))
      .filter((part) => part.length > 0)
    return parts.length ? parts.join(' ') : t('app.candidate_card.header.new_label')
  }, [model?.first_name, model?.last_name, t])

  const sectionNavItems = useMemo(() => {
    const items = [
      { key: 'basic', label: t('app.candidate_card.nav.basic'), emoji: '👤', ref: basicRef },
      ...(!isNew ? [{ key: 'notes', label: t('app.candidate_card.nav.notes'), emoji: '🗒️', ref: notesRef }] : []),
      { key: 'personal', label: t('app.candidate_card.nav.personal'), emoji: '🧍', ref: personalRef },
      { key: 'status', label: t('app.candidate_card.nav.status'), emoji: '🛂', ref: statusRef },
      { key: 'experience', label: t('app.candidate_card.nav.experience'), emoji: '🧾', ref: experienceRef },
      { key: 'employer', label: t('app.candidate_card.nav.employer'), emoji: '🏢', ref: employerRef },
    ]
    return items
  }, [isNew, t])

  const isMetaLead = useMemo(() => {
    const source = (model?.origin && (model.origin as any)?.source) || model?.source || ''
    return typeof source === 'string' && source.toLowerCase().includes('meta')
  }, [model?.origin, model?.source])

  const addNote = useCallback(async () => {
    if (!model?.id) return
    const text = (newNote || '').trim()
    if (!text) return
    setNoteSending(true)
    try{
      await api.post(`/candidates/${model.id}/notes`, { text, visibility: 'internal' })
      setNewNote('')
      await fetchNotes(String(model.id))
      setSavedOk(true); setTimeout(()=>setSavedOk(false), 1500)
    } catch (err:any) {
      const r = err?.response?.data
      const detail = typeof r?.detail === 'string' ? r.detail : (r ? JSON.stringify(r) : err?.message || unknownErrorLabel)
      alert(t('app.candidate_card.messages.note_add_failed', { values: { detail } }))
      throw err
    } finally {
      setNoteSending(false)
    }
  }, [model?.id, newNote, fetchNotes, t, unknownErrorLabel])
  useEffect(() => {
    if (isNew) { setNotes([]); return }
    if (!id || typeof id !== 'string') return
    void fetchNotes(id)
  }, [id, isNew, fetchNotes])

  const save = useCallback(async () => {
    if (!model) return
    setSaving(true)
    try{
      const {
        payload,
        extraForState,
        docsProgressForState,
        managerId,
        noteForState,
        statusReasonForState,
      } = buildCandidatePayload(model, meta?.reason_choices ?? {})
      const createPayload = pickKeys(payload, CREATE_FIELDS)
      const patchAfterCreate = pickKeys(payload, PATCH_AFTER_CREATE_FIELDS)
      const stageForValidation = payload.stage || model.stage || ''
      const requiresReason = Boolean(meta?.reason_choices?.[stageForValidation]?.length)
      if (requiresReason && (!statusReasonForState || statusReasonForState.length === 0)) {
        alert(t('app.candidate_card.messages.stage_reason_required'))
        setSaving(false)
        return
      }
      if (isNew) {
        const { data } = await api.post('/candidates', createPayload)
        const createdId = data?.id
        if (createdId && Object.keys(patchAfterCreate).length > 0) {
          await api.patch(`/candidates/${createdId}`, patchAfterCreate)
        }
        if (createdId) {
          await syncEmploymentRows(String(createdId))
        }
        const targetId = createdId || model.id
        const refreshed = targetId ? await fetchCandidate(String(targetId), model) : normalizeCandidate({
          ...data,
          ...patchAfterCreate,
          extra: extraForState,
          docs_progress: docsProgressForState,
          manager_id: managerId ?? data?.manager_id,
          note: noteForState,
        }, model)
        setModel(refreshed)
        setSavedOk(true); setTimeout(()=>setSavedOk(false), 2000)
        if (createdId) {
          nav(`/app/candidates/${createdId}`, { replace: true })
        }
      } else {
        if (model.id) {
          await syncEmploymentRows(String(model.id))
        }
        const { data } = await api.patch(`/candidates/${model.id}`, payload)
        const refreshed = await fetchCandidate(String(data?.id ?? model.id), model)
        setModel(refreshed)
        setSavedOk(true); setTimeout(()=>setSavedOk(false), 2000)
      }
    } catch (err: any) {
      const r = err?.response?.data
      const detail = (typeof r?.detail === 'string')
        ? r.detail
        : (Array.isArray(r?.detail) ? JSON.stringify(r.detail) : (r ? JSON.stringify(r) : err?.message || unknownErrorLabel))
      alert(t('app.candidate_card.messages.save_failed', { values: { detail } }))
      throw err
    } finally {
      setSaving(false)
    }
  }, [model, isNew, nav, fetchCandidate, syncEmploymentRows, t, unknownErrorLabel])

  const extra = useMemo<CandidateExtra>(
    () => sanitizeExtra(model?.extra as CandidateExtra | undefined),
    [model?.extra]
  )
  const setExtra = (patch: Partial<CandidateExtra>) =>
    setModel(m => {
      if (!m) return m
      const current = sanitizeExtra(m.extra as CandidateExtra | undefined)
      const merged = sanitizeExtra(patch, current)
      return {
        ...m,
        extra: merged,
        phone_country_code: merged.phone_prefix || '',
      }
    })
  useEffect(() => {
    if (!model?.phone) return
    const detection = detectPhoneParts(model.phone)
    if (!detection) return
    const normalizedPhone = model.phone.trim()
    const samePhone = normalizedPhone === detection.number
    const samePrefix = (extra.phone_prefix || '').trim() === detection.prefix
    const sameCountry = (extra.phone_country || '').trim() === detection.country
    if (samePhone && samePrefix && sameCountry) return
    setModel(prev => {
      if (!prev) return prev
      const currentExtra = sanitizeExtra(prev.extra as CandidateExtra | undefined)
      const mergedExtra = sanitizeExtra(
        { phone_country: detection.country, phone_prefix: detection.prefix },
        currentExtra
      )
      return {
        ...prev,
        phone: detection.number,
        extra: mergedExtra,
        phone_country_code: mergedExtra.phone_prefix || '',
      }
    })
  }, [model?.phone, extra.phone_prefix, extra.phone_country, detectPhoneParts])

  useEffect(() => {
    if (isNew) return
    if (!model?.id) {
      setEmploymentRows([])
      setEmploymentBaseline({})
      return
    }
    employmentInitRef.current = false
    setEmploymentRows([])
    setEmploymentBaseline({})
    setEmploymentError(null)
    void reloadCandidateEmployments(String(model.id))
  }, [isNew, model?.id, reloadCandidateEmployments])

  useEffect(() => {
    if (!isNew) return
    if (employmentInitRef.current) return
    employmentInitRef.current = true
    const legacyRows = sanitizeEmploymentHistory(extra.employment_history)
      .map(legacyEmploymentEntryToRow)
    setEmploymentRows(legacyRows)
    setEmploymentBaseline({})
    setEmploymentError(null)
  }, [isNew, extra.employment_history])
  useEffect(() => {
    if (!model) return
    setModel(m => {
      if (!m) return m
      const options = meta?.reason_choices?.[m.stage || '']
      if (!options) {
        return m
      }
      const current = Array.isArray(m.status_reason) ? m.status_reason : []
      const filtered = current.filter(code => options.some(opt => opt.code === code))
      if (filtered.length !== current.length) {
        return { ...m, status_reason: filtered }
      }
      return m
    })
  }, [meta?.reason_choices, model?.stage])

  const employmentHistory = employmentRows

  const updateEmploymentHistory = useCallback((
    localId: string,
    key: keyof Pick<EmploymentRow, 'employer_name' | 'country' | 'position' | 'start_date' | 'end_date'>,
    value: string
  ) => {
    setEmploymentError(null)
    setEmploymentRows(rows =>
      rows.map(row => row.localId === localId ? { ...row, [key]: value } : row),
    )
  }, [])

  const addEmploymentRow = useCallback(() => {
    setEmploymentError(null)
    setEmploymentRows(rows => {
      if (rows.length >= MAX_EMPLOYMENTS) return rows
      return [...rows, makeEmploymentRow()]
    })
  }, [])

  const removeEmploymentRow = useCallback((localId: string) => {
    setEmploymentError(null)
    setEmploymentRows(rows => rows.filter(row => row.localId !== localId))
  }, [])

  const firstContactChecked = Boolean(extra.first_contact_at)
  const firstContactDisplay = formatDateTime(extra.first_contact_at)
  const handleFirstContactToggle = useCallback((checked: boolean) => {
    if (checked) {
      if (!extra.first_contact_at) {
        setExtra({ first_contact_at: new Date().toISOString() })
      }
      setModel((prev) => {
        if (!prev) return prev
        if (prev.stage === 'contacted') return prev
        return { ...prev, stage: 'contacted' }
      })
    } else {
      setExtra({ first_contact_at: '' })
    }
  }, [extra.first_contact_at, setExtra, setModel])

  const inPolandValue = extra.in_poland === null || typeof extra.in_poland === 'undefined'
    ? ''
    : (extra.in_poland ? 'yes' : 'no')
  const handleInPolandChange = useCallback((value: string) => {
    if (value === '') {
      setExtra({ in_poland: null })
      return
    }
    setExtra({ in_poland: value === 'yes' })
  }, [setExtra])

  const handleExperienceChange = useCallback((field: 'experience_eu_years' | 'experience_non_eu_years', raw: string) => {
    let numeric: number | null = null
    if (raw.trim() !== '') {
      const parsed = Number(raw)
      if (!Number.isNaN(parsed)) numeric = parsed
    }
    const eu = field === 'experience_eu_years' ? numeric : (typeof extra.experience_eu_years === 'number' ? extra.experience_eu_years : null)
    const nonEu = field === 'experience_non_eu_years' ? numeric : (typeof extra.experience_non_eu_years === 'number' ? extra.experience_non_eu_years : null)
    const total = (eu ?? 0) + (nonEu ?? 0)
    setExtra({
      [field]: numeric,
      experience_ce_total: (eu === null && nonEu === null)
        ? null
        : (Number.isFinite(total) ? Number(total) : null),
    } as Partial<CandidateExtra>)
  }, [extra.experience_eu_years, extra.experience_non_eu_years, setExtra])

  const experienceTotalDisplay = (() => {
    if (typeof extra.experience_ce_total === 'number' && !Number.isNaN(extra.experience_ce_total)) {
      return extra.experience_ce_total
    }
    const eu = typeof extra.experience_eu_years === 'number' && !Number.isNaN(extra.experience_eu_years)
      ? extra.experience_eu_years
      : 0
    const nonEu = typeof extra.experience_non_eu_years === 'number' && !Number.isNaN(extra.experience_non_eu_years)
      ? extra.experience_non_eu_years
      : 0
    const sum = eu + nonEu
    return Number.isFinite(sum) ? Number(sum.toFixed(2)) : ''
  })()

  const createdAtDisplay = formatDateTime(model?.created_at)
  const resolveStageLabel = useCallback(
    (code: string | null | undefined) => {
      if (!code) return ''
      const fallback = meta?.labels?.[code] || code
      return translateStageLabel(t, code, fallback)
    },
    [meta, t]
  )

  // красивый телефон для шапки (код + номер), но не пишем в model.phone
  const phoneDisplay = useMemo(() => {
    const prefix = (extra?.phone_prefix || '').trim()
    const number = (model?.phone || '').trim()
    if (prefix && number) return `${prefix} ${number}`
    return number || prefix || ''
  }, [extra?.phone_prefix, model?.phone])

  // tel: без пробелов/скобок/дефисов
  const telHref = useMemo(() => {
    const raw = `${(extra?.phone_prefix || '')}${(model?.phone || '')}`
    const digits = raw.replace(/[\s()-]/g, '')
    return digits ? `tel:${digits}` : undefined
  }, [extra?.phone_prefix, model?.phone])
  const handlePhoneInputChange = useCallback((value: string) => {
    const detection = detectPhoneParts(value)
    const nextValue = detection ? detection.number : value
    setModel(m => m && ({ ...m, phone: nextValue }))
    if (detection) {
      setExtra({ phone_country: detection.country, phone_prefix: detection.prefix })
    }
  }, [detectPhoneParts, setExtra])

  useEffect(() => {
    if (!dialCodes.length) return
    if (!extra.phone_prefix) return
    if (extra.phone_country) return
    const prefix = extra.phone_prefix.trim()
    if (!prefix) return
    const found = dialCodes.find((opt) => {
      const optPrefix = typeof opt.extra?.prefix === 'string' ? opt.extra.prefix.trim() : ''
      return optPrefix === prefix
    })
    if (found) {
      setExtra({ phone_country: found.value })
    }
  }, [dialCodes, extra.phone_prefix, extra.phone_country, setExtra])

  const setAddressField = (
    which: 'address'|'reg_address',
    k: keyof NonNullable<CandidateExtra['address']>,
    v: string
  ) => setExtra({ [which]: { ...extra[which], [k]: v } } as Partial<CandidateExtra>)

  // Применяем поля документа к карточке кандидата (автозаполнение)
  function applyDocFieldsToCandidate(docType: string, fields: Record<string, any>) {
    setModel(m => {
      if (!m) return m;
      const next = { ...m } as Candidate;
      const extraAny: any = { ...sanitizeExtra(next.extra as CandidateExtra | undefined) };

      // Паспорт / нац. удостоверение — ФИО, дата рождения, гражданство
      if (docType === 'national_id' || docType === 'passport') {
        if (fields.surname && !next.last_name) next.last_name = String(fields.surname);
        if (fields.given_names && !next.first_name) next.first_name = String(fields.given_names);
        if (fields.date_of_birth) extraAny.birth_date = String(fields.date_of_birth).slice(0, 10);
        if (fields.nationality)  extraAny.citizenship = String(fields.nationality);
      }

      const mergedExtra = sanitizeExtra(extraAny, sanitizeExtra(next.extra as CandidateExtra | undefined))
      next.extra = mergedExtra;
      next.phone_country_code = mergedExtra.phone_prefix || next.phone_country_code || '';
      return next;
    });
  }

  const handleDeleteRequest = useCallback(async () => {
    if (!model?.id) return
    const reason = window.prompt(t('app.candidate_card.prompts.delete_reason')) || undefined
    setDeleteRequestLoading(true)
    setDeleteRequestMessage(null)
    setDeleteRequestError(null)
    try {
      await createDeleteRequest(model.id, reason)
      setDeleteRequestMessage(t('app.candidate_card.messages.delete_request_sent'))
    } catch (err: any) {
      console.error('[CandidateCard] delete request error', err)
      const detail = err?.response?.data?.detail
      setDeleteRequestError(detail || t('app.candidate_card.messages.delete_request_failed'))
    } finally {
      setDeleteRequestLoading(false)
    }
  }, [model])

if (loading || !model) return <div className="h-full w-full text-gray-500">{t('common.loading')}</div>

  return (
    <div className="h-full min-h-0 w-full flex flex-col gap-4">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-6 text-white shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <div className="text-xs text-white/80">
              <Link className="hover:underline text-white" to="/app/candidates">{t('app.candidate_card.header.back')}</Link>
            </div>
            <div>
              <h1 className="text-3xl font-semibold">{candidateTitle}</h1>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-white/90">
                <StageTag code={model.stage || 'new'} />
                {model.email && <a className="hover:underline text-white" href={`mailto:${model.email}`}>{model.email}</a>}
                {phoneDisplay && (
                  <a className="hover:underline text-white" href={telHref}>{phoneDisplay}</a>
                )}
                {model.short_id && (
                  <span className="text-xs rounded-full border border-white/40 px-2 py-0.5">
                    {t('app.candidate_card.labels.short_id_badge', { values: { id: model.short_id } })}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-2 text-sm">
          <div className="flex items-center gap-2">
            <button
              className="rounded-xl border border-white/40 bg-white/10 px-4 py-2 font-medium text-white transition hover:bg-white/20"
              onClick={()=>nav(-1)}
            >
              {t('common.actions.cancel')}
            </button>
            <button
              className="rounded-xl border border-white bg-white px-4 py-2 font-semibold text-brand-700 shadow-sm transition hover:bg-white/90 disabled:opacity-60"
              disabled={saving}
              onClick={save}
            >
              {saving ? t('common.saving') : (isNew ? t('common.actions.create') : t('common.actions.save'))}
            </button>
          </div>
          <div className="flex items-center gap-2">
            {!isNew && canDeleteDirect && (
              <button
                className="rounded-xl border border-white/40 bg-white/10 px-4 py-2 font-medium text-rose-50 transition hover:bg-white/20"
                onClick={async () => {
                  if (!confirm(t('app.candidate_card.confirm.delete'))) return
                  await api.delete(`/candidates/${model.id}`)
                  nav('/app/candidates')
                }}
              >
                {t('common.actions.delete')}
              </button>
            )}
            {!isNew && !canDeleteDirect && canRequestDelete && (
              <button
                type="button"
                className="rounded-xl border border-white/40 bg-white/10 px-4 py-2 font-medium text-white transition hover:bg-white/20"
                disabled={deleteRequestLoading}
                onClick={() => void handleDeleteRequest()}
              >
                {deleteRequestLoading ? t('app.candidate_card.actions.delete_request_loading') : t('app.candidate_card.actions.delete_request')}
              </button>
            )}
          </div>
        </div>
      </div>

      {deleteRequestMessage && (
        <div className="p-3 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200">
          {deleteRequestMessage}
        </div>
      )}
      {deleteRequestError && (
        <div className="p-3 rounded-lg bg-red-50 text-red-700 border border-red-200">
          {deleteRequestError}
        </div>
      )}

      {savedOk && (
        <div className="p-3 rounded-lg bg-green-50 text-green-800 border border-green-200">
          {t('app.candidate_card.messages.saved')}
        </div>
      )}

      {/* Tabs */}
      <div className="card p-3">
        <div className="mb-4 flex gap-2 border-b border-brand-100/70">
          {([
            ['personal', t('app.candidate_card.tabs.personal')],
            ['docs', t('app.candidate_card.tabs.docs')],
            ['services', t('app.candidate_card.tabs.services')],
          ] as [Tab,string][])
            .map(([tabKey,label]) => (
            <button key={tabKey}
              className={clsx('px-3 py-2 -mb-px border-b-2', tab===tabKey ? 'border-brand-500 text-brand-700' : 'border-transparent text-gray-500')}
              onClick={()=>setTab(tabKey)}>{label}</button>
          ))}
        </div>

        {/* PERSONAL */}
        {tab==='personal' && (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(280px,1fr)] lg:items-start lg:justify-between">
            <div className="space-y-8 lg:pr-6">
                  <div className="flex flex-wrap items-center gap-2 overflow-x-auto rounded-full bg-white/60 p-2">
                    {sectionNavItems.map(item => (
                      <button
                        key={item.key}
                        type="button"
                        className="flex items-center gap-2 rounded-full border border-brand-50 bg-white/95 px-3 py-1.5 text-sm text-gray-700 transition-all hover:border-brand-300 hover:text-brand-700"
                        onClick={handleScrollTo(item.ref)}
                      >
                        <span>{item.emoji}</span>
                        <span>{item.label}</span>
                      </button>
                    ))}
                  </div>
              <section
                ref={basicRef}
                id="section-basic"
                className="group app-surface p-6 scroll-mt-24 transition-all hover:-translate-y-0.5 hover:shadow-xl"
              >
              <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">👤</span>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{t('app.candidate_card.sections.basic.title')}</h2>
                    <p className="text-sm text-gray-500">{t('app.candidate_card.sections.basic.description')}</p>
                  </div>
                </div>
                {!isNew && (
                  <button
                    type="button"
                    className="btn-ghost text-sm self-start border border-transparent bg-white shadow-sm transition hover:border-brand-200 hover:shadow"
                    onClick={openHistoryModal}
                    disabled={historyLoading}
                  >
                    {historyLoading ? t('app.candidate_card.actions.history_loading') : t('app.candidate_card.actions.history')}
                  </button>
                )}
              </div>
              <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="space-y-4">
                  <Input label={t('app.candidate_card.fields.first_name')} value={model.first_name} onChange={e=>setModel(m=>m && ({...m, first_name: e.target.value}))}/>
                  <Input label={t('app.candidate_card.fields.last_name')} value={model.last_name} onChange={e=>setModel(m=>m && ({...m, last_name: e.target.value}))}/>
                  <Input
                    label={t('app.candidate_card.fields.email')}
                    type="email"
                    value={model.email || ''}
                    onChange={e=>setModel(m=>m && ({...m, email: e.target.value}))}
                  />

                  <div>
                    <div className="label">{t('app.candidate_card.fields.phone')}</div>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(160px,1fr)_12px_minmax(160px,1fr)] sm:items-center">
                      <SearchableSelect
                        options={dialCodes}
                        value={(extra as any).phone_country || ''}
                        onChange={(cc)=>{
                          const prefix = dialCodes.find(x => x.value === cc)?.extra?.prefix || ''
                          setExtra({ phone_country: cc, phone_prefix: prefix })
                        }}
                        placeholder={selectTexts.empty}
                        searchPlaceholder={t('app.candidate_card.select.search_country')}
                        noResultsLabel={selectTexts.noResults}
                        className="w-full"
                      />
                      <span className="hidden text-gray-400 text-center sm:block">—</span>
                      <Input
                        placeholder={t('app.candidate_card.placeholders.phone_number')}
                        value={model.phone || ''}
                        onChange={e=>handlePhoneInputChange(e.target.value)}
                      />
                    </div>
                  </div>

                  <label className="block">
                  <div className="label">{t('app.candidate_card.fields.preferred_contact')}</div>
                    <select
                      className="input"
                      value={(extra.preferred_contact as PreferredContact) || ''}
                      onChange={e=>setExtra({ preferred_contact: e.target.value as PreferredContact })}
                    >
                      {preferredContactOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="label flex items-center justify-between">
                      <span>{t('app.candidate_card.fields.short_id')}</span>
                      {!isNew && !model.short_id && (
                        <button
                          type="button"
                          className="btn-ghost text-xs"
                          onClick={async ()=>{
                            const { data } = await api.patch(`/candidates/${model.id}`, { extra: {} })
                            setModel(m => normalizeCandidate(data, m || model))
                            setSavedOk(true); setTimeout(()=>setSavedOk(false), 2000)
                          }}
                        >
                          {t('app.candidate_card.actions.generate_short_id')}
                        </button>
                      )}
                    </div>
                    <Input
                      value={model.short_id || ''}
                      readOnly
                      placeholder="—"
                      hint={t('app.candidate_card.fields.short_id_hint')}
                    />
                  </div>

                  <div>
                    <div className="label">{t('app.candidate_card.fields.stage')}</div>
                    <div className="flex items-center gap-2">
                      <select
                        className="input"
                        value={model.stage || ''}
                        onChange={e=>{
                          const nextStage = e.target.value
                          setModel(m => {
                            if (!m) return m
                            const options = meta?.reason_choices?.[nextStage] ?? []
                            const sanitized = Array.isArray(m.status_reason)
                              ? m.status_reason.filter(code => options.some(opt => opt.code === code))
                              : []
                            return {
                              ...m,
                              stage: nextStage,
                              status_reason: options.length ? sanitized : [],
                            }
                          })
                        }}
                      >
                        {stageOptions.map(code => (
                          <option key={code} value={code}>{stageLabelIntl(code)}</option>
                        ))}
                      </select>
                      <StageTag code={model.stage || 'new'} />
                    </div>
                  </div>
                  {(meta?.reason_choices?.[model.stage || '']?.length ?? 0) > 0 && (
                    <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
                      <div className="label mb-1">{t('app.candidate_card.fields.status_reasons')}</div>
                      <div className="space-y-1 text-sm">
                        {(meta?.reason_choices?.[model.stage || ''] ?? []).map(option => {
                          const checked = Array.isArray(model.status_reason) && model.status_reason.includes(option.code)
                          const label = translateReasonLabel(t, option.code, option.label || option.code)
                          return (
                            <label key={option.code} className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => {
                                  const nextChecked = e.target.checked
                                  setModel(m => {
                                    if (!m) return m
                                    const current = Array.isArray(m.status_reason) ? m.status_reason : []
                                    const updated = nextChecked
                                      ? Array.from(new Set([...current, option.code]))
                                      : current.filter(code => code !== option.code)
                                    return { ...m, status_reason: updated }
                                  })
                                }}
                              />
                              <span>{label}</span>
                            </label>
                          )
                        })}
                      </div>
                      {(!Array.isArray(model.status_reason) || model.status_reason.length === 0) && (
                        <div className="text-xs text-red-600">{t('app.candidate_card.messages.stage_reason_required')}</div>
                      )}
                    </div>
                  )}

                  <label className="block">
                  <div className="label">{t('app.candidate_card.fields.manager')}</div>
                    <SearchableSelect
                      options={managers}
                      value={model.manager || ''}
                      onChange={(v)=>setModel(m=>m && ({...m, manager: v || null, manager_id: v || null}))}
                      placeholder={selectTexts.empty}
                      searchPlaceholder={selectTexts.search}
                      noResultsLabel={selectTexts.noResults}
                    />
                  </label>

                  <Input
                    label={t('app.candidate_card.fields.created_at')}
                    value={createdAtDisplay}
                    readOnly
                    placeholder="—"
                    hint={t('app.candidate_card.fields.created_at_hint')}
                  />

                  <div>
                    <div className="label">{t('app.candidate_card.fields.first_contact')}</div>
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                      <Checkbox
                        label={t('app.candidate_card.fields.first_contact_done')}
                        checked={firstContactChecked}
                        onChange={handleFirstContactToggle}
                      />
                      <input className="input sm:max-w-xs" readOnly value={firstContactDisplay || '—'} />
                    </div>
                    <p className="mt-1 text-xs text-gray-500">{t('app.candidate_card.fields.first_contact_hint')}</p>
                  </div>

                  {isMetaLead && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                      {t('app.candidate_card.messages.meta_lead')}
                    </div>
                  )}
                </div>
              </div>
            </section>


            <section
              ref={personalRef}
              id="section-personal"
              className="group app-surface p-6 scroll-mt-24 transition-all hover:-translate-y-0.5 hover:shadow-xl"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">🧍</span>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">{t('app.candidate_card.sections.personal.title')}</h2>
                  <p className="text-sm text-gray-500">{t('app.candidate_card.sections.personal.description')}</p>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
                <Input label={t('app.candidate_card.fields.birth_date')} type="date"
                       value={(extra.birth_date as any) || ''}
                       onChange={e=>setExtra({ birth_date: e.target.value })}/>
                <label className="block">
                  <div className="label">{t('app.candidate_card.fields.citizenship')}</div>
                  <SearchableSelect
                    options={countries}
                    value={(extra.citizenship as any) || ''}
                    onChange={(v)=>setExtra({ citizenship: v })}
                    placeholder={selectTexts.empty}
                    searchPlaceholder={selectTexts.search}
                    noResultsLabel={selectTexts.noResults}
                  />
                </label>
                <label className="block">
                  <div className="label">{t('app.candidate_card.fields.country_code')}</div>
                  <SearchableSelect
                    options={countries}
                    value={(model.country_code as any) || ''}
                    onChange={(v)=>setModel(m => m && ({ ...m, country_code: v || null }))}
                    placeholder={selectTexts.empty}
                    searchPlaceholder={selectTexts.search}
                    noResultsLabel={selectTexts.noResults}
                  />
                </label>
                <div className="lg:col-span-2">
                  <div className="label">{t('app.candidate_card.fields.languages')}</div>
                  <CheckboxMultiSelect
                    options={languages}
                    values={model.languages || []}
                    onChange={(vals)=>setModel(m=>m && ({...m, languages: vals}))}
                    placeholder={selectTexts.multiNone}
                    searchPlaceholder={selectTexts.search}
                    noResultsLabel={selectTexts.noResults}
                    multiSelectedLabel={selectTexts.multiSelected}
                  />
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-dashed border-gray-300 bg-white/60 p-4">
                  <div className="font-semibold text-gray-800">{t('app.candidate_card.sections.personal.address_current')}</div>
                  <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                    <label className="block md:col-span-2">
                      <div className="label">{t('app.candidate_card.fields.address.country')}</div>
                      <SearchableSelect
                        options={countries}
                        value={extra.address?.country || ''}
                        onChange={(v)=>setAddressField('address','country', v)}
                        placeholder={selectTexts.empty}
                        searchPlaceholder={selectTexts.search}
                        noResultsLabel={selectTexts.noResults}
                      />
                    </label>
                    <Input label={t('app.candidate_card.fields.address.city')} value={extra.address?.city || ''} onChange={e=>setAddressField('address','city', e.target.value)} />
                    <Input label={t('app.candidate_card.fields.address.zip')} value={extra.address?.zip || ''} onChange={e=>setAddressField('address','zip', e.target.value)} />
                    <Input label={t('app.candidate_card.fields.address.street')} containerClassName="md:col-span-2" value={extra.address?.street || ''} onChange={e=>setAddressField('address','street', e.target.value)} />
                    <Input label={t('app.candidate_card.fields.address.house')} value={extra.address?.house || ''} onChange={e=>setAddressField('address','house', e.target.value)} />
                    <Input label={t('app.candidate_card.fields.address.apt')} value={extra.address?.apt || ''} onChange={e=>setAddressField('address','apt', e.target.value)} />
                  </div>

                  <div className="mt-3 rounded-lg bg-slate-50 px-3 py-2">
                    <Checkbox
                      label={t('app.candidate_card.fields.address.diff')}
                      checked={!!(extra as any).reg_address_diff}
                      onChange={(v)=>setExtra({ reg_address_diff: v })}
                    />
                  </div>
                </div>

                {(extra as any).reg_address_diff && (
                  <div className="rounded-xl border border-dashed border-gray-300 bg-white/60 p-4">
                    <div className="font-semibold text-gray-800">{t('app.candidate_card.sections.personal.address_registered')}</div>
                    <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                      <label className="block md:col-span-2">
                        <div className="label">{t('app.candidate_card.fields.address.country')}</div>
                      <SearchableSelect
                        options={countries}
                        value={extra.reg_address?.country || ''}
                        onChange={(v)=>setAddressField('reg_address','country', v)}
                        placeholder={selectTexts.empty}
                        searchPlaceholder={selectTexts.search}
                        noResultsLabel={selectTexts.noResults}
                      />
                      </label>
                      <Input label={t('app.candidate_card.fields.address.city')} value={extra.reg_address?.city || ''} onChange={e=>setAddressField('reg_address','city', e.target.value)} />
                      <Input label={t('app.candidate_card.fields.address.zip')} value={extra.reg_address?.zip || ''} onChange={e=>setAddressField('reg_address','zip', e.target.value)} />
                      <Input label={t('app.candidate_card.fields.address.street')} containerClassName="md:col-span-2" value={extra.reg_address?.street || ''} onChange={e=>setAddressField('reg_address','street', e.target.value)} />
                      <Input label={t('app.candidate_card.fields.address.house')} value={extra.reg_address?.house || ''} onChange={e=>setAddressField('reg_address','house', e.target.value)} />
                      <Input label={t('app.candidate_card.fields.address.apt')} value={extra.reg_address?.apt || ''} onChange={e=>setAddressField('reg_address','apt', e.target.value)} />
                    </div>
                  </div>
                )}
              </div>
            </section>

            <section
              ref={statusRef}
              id="section-status"
              className="group app-surface p-6 scroll-mt-24 transition-all hover:-translate-y-0.5 hover:shadow-xl"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">🛂</span>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">{t('app.candidate_card.sections.status.title')}</h2>
                  <p className="text-sm text-gray-500">{t('app.candidate_card.sections.status.description')}</p>
                </div>
              </div>
              <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
                <label className="block">
                  <div className="label">{t('app.candidate_card.fields.in_poland')}</div>
                  <select
                    className="input"
                    value={inPolandValue}
                    onChange={e=>handleInPolandChange(e.target.value)}
                  >
                    <option value="">{selectTexts.multiNone}</option>
                    <option value="yes">{t('common.words.yes')}</option>
                    <option value="no">{t('common.words.no')}</option>
                  </select>
                </label>
                <label className="block">
                  <div className="label">{t('app.candidate_card.fields.poland_basis')}</div>
                  <select
                    className="input"
                    value={extra.poland_stay_basis || ''}
                    onChange={e=>setExtra({ poland_stay_basis: e.target.value })}
                  >
                    {polandBasisOptions.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </label>
              </div>
            </section>

            <section
              ref={experienceRef}
              id="section-experience"
              className="group app-surface p-6 scroll-mt-24 transition-all hover:-translate-y-0.5 hover:shadow-xl"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">🧾</span>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">{t('app.candidate_card.sections.experience.title')}</h2>
                  <p className="text-sm text-gray-500">{t('app.candidate_card.sections.experience.description')}</p>
                </div>
              </div>
              <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
                <Input
                  label={t('app.candidate_card.fields.experience_eu')}
                  type="number"
                  value={
                    typeof extra.experience_eu_years === 'number' && !Number.isNaN(extra.experience_eu_years)
                      ? String(extra.experience_eu_years)
                      : ''
                  }
                  onChange={e=>handleExperienceChange('experience_eu_years', e.target.value)}
                />
                <Input
                  label={t('app.candidate_card.fields.experience_non_eu')}
                  type="number"
                  value={
                    typeof extra.experience_non_eu_years === 'number' && !Number.isNaN(extra.experience_non_eu_years)
                      ? String(extra.experience_non_eu_years)
                      : ''
                  }
                  onChange={e=>handleExperienceChange('experience_non_eu_years', e.target.value)}
                />
                <Input
                  label={t('app.candidate_card.fields.experience_total')}
                  type="number"
                  value={experienceTotalDisplay === '' ? '' : String(experienceTotalDisplay)}
                  readOnly
                  hint={t('app.candidate_card.fields.experience_total_hint')}
                />
              </div>

              <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="block">
                  <div className="label">{t('app.candidate_card.fields.intl_experience')}</div>
                  <select
                    className="input"
                    value={extra.intl_experience === true ? 'yes' : extra.intl_experience === false ? 'no' : ''}
                    onChange={(e) => {
                      const value = e.target.value
                      setExtra({ intl_experience: value === 'yes' ? true : value === 'no' ? false : null })
                    }}
                  >
                    <option value="">{t('app.candidate_card.fields.unset')}</option>
                    <option value="yes">{t('common.words.yes')}</option>
                    <option value="no">{t('common.words.no')}</option>
                  </select>
                </label>
                <label className="block">
                  <div className="label">{t('app.candidate_card.fields.eu_routes')}</div>
                  <select
                    className="input"
                    value={extra.eu_routes === true ? 'yes' : extra.eu_routes === false ? 'no' : ''}
                    onChange={(e) => {
                      const value = e.target.value
                      setExtra({ eu_routes: value === 'yes' ? true : value === 'no' ? false : null })
                    }}
                  >
                    <option value="">{t('app.candidate_card.fields.unset')}</option>
                    <option value="yes">{t('common.words.yes')}</option>
                    <option value="no">{t('common.words.no')}</option>
                  </select>
                </label>
              </div>

              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <div className="label">{t('app.candidate_card.intake.fields.trailer_types')}</div>
                  <CheckboxMultiSelect
                    options={trailerTypeOptions}
                    values={Array.isArray(extra.trailer_types) ? extra.trailer_types : []}
                    onChange={(vals) => setExtra({ trailer_types: vals })}
                    placeholder={selectTexts.multiNone}
                    searchPlaceholder={selectTexts.search}
                    noResultsLabel={selectTexts.noResults}
                    multiSelectedLabel={selectTexts.multiSelected}
                  />
                </div>
                <div>
                  <div className="label">{t('app.candidate_card.intake.fields.route_types')}</div>
                  <CheckboxMultiSelect
                    options={routeTypeOptions}
                    values={Array.isArray(extra.route_types) ? extra.route_types : []}
                    onChange={(vals) => setExtra({ route_types: vals })}
                    placeholder={selectTexts.multiNone}
                    searchPlaceholder={selectTexts.search}
                    noResultsLabel={selectTexts.noResults}
                    multiSelectedLabel={selectTexts.multiSelected}
                  />
                </div>
              </div>

              <div className="mt-6 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-gray-800">{t('app.candidate_card.employment.title')}</div>
                  <button
                    type="button"
                    className="btn-secondary text-sm shadow-sm transition hover:shadow disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={addEmploymentRow}
                    disabled={employmentHistory.length >= MAX_EMPLOYMENTS}
                  >
                    {t('app.candidate_card.employment.add')}
                  </button>
                </div>
                {employmentHistory.length >= MAX_EMPLOYMENTS && (
                  <p className="text-xs text-gray-500">{t('app.candidate_card.employment.limit', { values: { count: MAX_EMPLOYMENTS } })}</p>
                )}
                {employmentError && (
                  <div className="rounded border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                    {employmentError}
                  </div>
                )}
                {employmentLoading ? (
                  <div className="rounded-lg border border-dashed border-gray-300 bg-white/70 px-4 py-3 text-sm text-gray-500">
                    {t('app.candidate_card.employment.loading')}
                  </div>
                ) : employmentHistory.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-gray-300 bg-white/70 px-4 py-3 text-sm text-gray-500">
                    {t('app.candidate_card.employment.empty')}
                  </div>
                ) : (
                  <div className="overflow-x-auto rounded-2xl border border-brand-50 bg-white/95 shadow-card">
                    <table className="min-w-full divide-y divide-brand-100/70 text-sm">
                      <thead className="bg-brand-50/60">
                        <tr>
                          <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.employer')}</th>
                          <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.country')}</th>
                          <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.position')}</th>
                          <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.start')}</th>
                          <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.end')}</th>
                          <th className="px-3 py-2 text-right"></th>
                        </tr>
                          </thead>
                      <tbody className="divide-y divide-brand-100/70 bg-white/95">
                        {employmentHistory.map((entry) => (
                          <tr key={entry.id ?? entry.localId}>
                            <td className="px-3 py-2">
                              <input
                                className="input"
                                value={entry.employer_name || ''}
                                onChange={e=>updateEmploymentHistory(entry.localId, 'employer_name', e.target.value)}
                                placeholder={t('app.candidate_card.employment.placeholders.employer')}
                              />
                            </td>
                            <td className="px-3 py-2">
                              <input
                                className="input"
                                value={entry.country || ''}
                                onChange={e=>updateEmploymentHistory(entry.localId, 'country', e.target.value.toUpperCase())}
                                placeholder={t('app.candidate_card.employment.placeholders.country')}
                              />
                            </td>
                            <td className="px-3 py-2">
                              <input
                                className="input"
                                value={entry.position || ''}
                                onChange={e=>updateEmploymentHistory(entry.localId, 'position', e.target.value)}
                                placeholder={t('app.candidate_card.employment.placeholders.position')}
                              />
                            </td>
                            <td className="px-3 py-2">
                              <input
                                className="input"
                                type="date"
                                value={entry.start_date || ''}
                                onChange={e=>updateEmploymentHistory(entry.localId, 'start_date', e.target.value)}
                              />
                            </td>
                            <td className="px-3 py-2">
                              <input
                                className="input"
                                type="date"
                                value={entry.end_date || ''}
                                onChange={e=>updateEmploymentHistory(entry.localId, 'end_date', e.target.value)}
                              />
                            </td>
                            <td className="px-3 py-2 text-right">
                              <button
                                type="button"
                                className="btn-ghost text-sm text-gray-500 hover:text-rose-600"
                                onClick={()=>removeEmploymentRow(entry.localId)}
                              >
                                {t('common.actions.delete')}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </section>

            <section
              ref={employerRef}
              id="section-employer"
              className="group app-surface p-6 scroll-mt-24 transition-all hover:-translate-y-0.5 hover:shadow-xl"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">🏢</span>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">{t('app.candidate_card.sections.employer.title')}</h2>
                  <p className="text-sm text-gray-500">{t('app.candidate_card.sections.employer.description')}</p>
                </div>
              </div>
              <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="block md:col-span-2">
                  <div className="label">{t('app.candidate_card.fields.vacancy')}</div>
                  <SearchableSelect
                    options={vacancyOpts}
                    value={(model.vacancy_id as string) || ''}
                    onChange={(v) => {
                      if (!v) {
                        setModel(m => m && ({
                          ...m,
                          vacancy_id: null,
                          vacancy_name: '',
                          company_id: null,
                          company_name: '',
                        }))
                        return
                      }
                      const opt = vacancyOpts.find(o => o.value === v)
                      const company_id = opt?.extra?.company_id || null
                      const company_name = opt?.extra?.company_name || model.company_name || ''
                      const vacancy_label = opt?.label || ''
                      setModel(m => m && ({
                        ...m,
                        vacancy_id: v as any,
                        vacancy_name: vacancy_label,
                        company_id,
                        company_name: company_name || m.company_name || '',
                      }))
                    }}
                    placeholder={selectTexts.empty}
                    searchPlaceholder={selectTexts.search}
                    noResultsLabel={selectTexts.noResults}
                  />
                  <p className="mt-1 text-xs text-gray-500">{t('app.candidate_card.messages.vacancy_hint')}</p>
                </label>
                <Input
                  label={t('app.candidate_card.fields.company')}
                  value={model.company_name || ''}
                  readOnly
                  placeholder="—"
                  hint={t('app.candidate_card.fields.company_hint')}
                />
              </div>
            </section>

          </div>
            {!isNew && (
              <aside
                ref={notesRef}
                id="section-notes"
                className="app-surface sticky top-20 h-fit w-full max-w-sm space-y-3 self-start rounded-2xl p-5 shadow-lg lg:w-80 lg:justify-self-end lg:ml-auto"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">🗒️</span>
                    <div>
                      <h3 className="text-base font-semibold text-gray-900">{t('app.candidate_card.sections.notes.title')}</h3>
                      <p className="text-xs text-gray-500">{t('app.candidate_card.sections.notes.description')}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn-ghost text-xs"
                    onClick={()=> model?.id && fetchNotes(String(model.id))}
                    disabled={notesLoading}
                  >{notesLoading ? t('app.candidate_card.actions.refreshing') : t('app.candidate_card.actions.refresh')}</button>
                </div>
                <div className="flex items-start gap-2">
                  <textarea
                    className="input min-h-[72px] flex-1"
                    placeholder={t('app.candidate_card.notes.placeholder')}
                    value={newNote}
                    onChange={e=>setNewNote(e.target.value)}
                  />
                  <button type="button" className="btn-primary" onClick={addNote} disabled={noteSending || !newNote.trim()}>
                    {noteSending ? t('app.candidate_card.actions.saving_note') : t('common.actions.add')}
                  </button>
                </div>
                <div className="divide-y rounded-lg border bg-white">
                  {notes.length === 0 && (
                    <div className="p-3 text-gray-500">{t('app.candidate_card.notes.empty')}</div>
                  )}
                  {notes.map(n => (
                    <div key={n.id} className="p-3">
                      <div className="mb-1 text-sm text-gray-500">
                        <span className="mr-2">{new Date(n.created_at).toLocaleString()}</span>
                        <span className="rounded bg-gray-100 px-2 py-0.5">
                          {t(`app.candidate_card.notes.visibility.${n.visibility}`, { defaultValue: n.visibility })}
                        </span>
                      </div>
                      <div className="whitespace-pre-wrap break-words">{n.text}</div>
                    </div>
                  ))}
                </div>
              </aside>
            )}
          </div>
        )}
        {/* DOCS */}
        {tab==='docs' && (
          <div className="space-y-4">
            <div className="app-surface p-4">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-lg font-semibold text-gray-900">{t('app.candidate_card.tabs.docs')}</p>
                  <p className="text-sm text-gray-500">{t('app.candidate_card.docs.helper')}</p>
                </div>
              </div>
              {!isNew && model.id ? (
                <CandidateDocuments
                  key={String(model.id)}
                  candidateId={String(model.id)}
                  {...({
                    ownerContext: { citizenship: (extra as any)?.citizenship || '' },
                    onFieldsApplied: (doc: any, fields: Record<string, any>) =>
                      applyDocFieldsToCandidate(String(doc?.type_code || doc?.type || ''), fields),
                  } as any)}
                />
              ) : (
                <div className="text-gray-500">{t('app.candidate_card.docs.disabled')}</div>
              )}
            </div>
          </div>
        )}
        {/* SERVICES */}
        {tab === 'services' && (
          <div className="space-y-4">
            {!isNew && model.id ? (
              <CandidateServicesSection
                candidateId={String(model.id)}
                canManage={can('services.orders.manage')}
              />
            ) : (
              <div className="text-gray-500">{t('app.candidate_card.services.disabled')}</div>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-end gap-2">
        <button className="btn-ghost" onClick={()=>nav(-1)}>{t('common.actions.cancel')}</button>
        <button className="btn-primary disabled:opacity-60" disabled={saving} onClick={save}>
          {saving ? t('common.saving') : (isNew ? t('common.actions.create') : t('common.actions.save'))}
        </button>
      </div>
      <StageHistoryModal
        open={historyOpen}
        loading={historyLoading}
        error={historyError}
        infoMessage={historyInfo}
        entries={stageHistory}
        onClose={closeHistoryModal}
        onReload={reloadStageHistory}
        resolveStageLabel={resolveStageLabel}
      />
    </div>
  )
}

function CandidateServicesSection({ candidateId, canManage }: { candidateId: string; canManage: boolean }) {
  const query = useMemo(() => ({ candidateId }), [candidateId])
  const { orders, loading, reload } = useServiceOrders(query)
  const { t } = useI18n()
  const orderStatusLabels = useMemo(() => {
    const map: Record<string, string> = {}
    SERVICE_ORDER_STATUSES.forEach((status) => {
      map[status] = t(`app.services.status.order.${status}`)
    })
    return map
  }, [t])
  const itemStatusLabels = useMemo(() => {
    const map: Record<string, string> = {}
    SERVICE_ITEM_STATUSES.forEach((status) => {
      map[status] = t(`app.services.status.item.${status}`)
    })
    return map
  }, [t])
  const formatOrderStatus = (status: string) => orderStatusLabels[status] || status
  const formatItemStatus = (status: string) => itemStatusLabels[status] || status

  return (
    <div className="md:col-span-2 app-surface p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="font-semibold">{t('app.candidate_card.services.title')}</div>
        <div className="flex items-center gap-2">
          <button type="button" className="btn-ghost text-sm" onClick={reload} disabled={loading}>
            {loading ? t('app.candidate_card.actions.refreshing') : t('app.candidate_card.actions.refresh')}
          </button>
          {canManage && (
            <Link to="/app/services" className="btn-ghost text-sm">
              {t('app.candidate_card.services.open_module')}
            </Link>
          )}
        </div>
      </div>

      {loading ? (
        <div className="text-sm text-gray-500">{t('app.candidate_card.services.loading')}</div>
      ) : orders.length === 0 ? (
        <div className="text-sm text-gray-500">{t('app.candidate_card.services.empty')}</div>
      ) : (
        <div className="overflow-auto rounded-2xl border border-brand-50 bg-white/95 shadow-card">
          <table className="min-w-full divide-y divide-brand-100/70 text-sm">
            <thead className="bg-brand-50/60">
              <tr>
                <th className="px-3 py-2 text-left">{t('app.candidate_card.services.columns.order')}</th>
                <th className="px-3 py-2 text-left">{t('app.candidate_card.services.columns.status')}</th>
                <th className="px-3 py-2 text-left">{t('app.candidate_card.services.columns.items')}</th>
                <th className="px-3 py-2 text-right">{t('app.candidate_card.services.columns.total')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-100/70 bg-white/95">
              {orders.map((order) => (
                <tr key={order.id}>
                  <td className="px-3 py-2 font-mono text-xs">{order.id.slice(0, 12)}…</td>
                  <td className="px-3 py-2 uppercase text-xs text-gray-500">{formatOrderStatus(order.status)}</td>
                  <td className="px-3 py-2 text-xs">
                    <ul className="list-disc list-inside space-y-1">
                      {order.items.map((item) => (
                        <li key={item.id}>
                          <span className="font-medium text-gray-700">{item.service?.name || item.service_id}</span>
                          <span className="ml-2 text-gray-500">{formatItemStatus(item.status)}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td className="px-3 py-2 text-right text-sm text-gray-700">{formatAmount(order.total_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

type StageHistoryModalProps = {
  open: boolean
  loading: boolean
  error: string | null
  infoMessage: string | null
  entries: StageHistoryEntry[]
  onClose: () => void
  onReload: () => void
  resolveStageLabel: (code: string | null | undefined) => string
}

function StageHistoryModal({
  open,
  loading,
  error,
  infoMessage,
  entries,
  onClose,
  onReload,
  resolveStageLabel,
}: StageHistoryModalProps) {
  const { t } = useI18n()
  if (!open) return null

  const renderStage = (code: string | null | undefined) => {
    if (!code) return <span className="text-gray-400">—</span>
    const label = resolveStageLabel(code)
    return (
      <div className="flex items-center gap-2">
        <StageTag code={code} />
        <span>{label || code}</span>
      </div>
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl max-h-[80vh] overflow-hidden rounded-3xl bg-white/98 shadow-2xl ring-1 ring-black/10"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-brand-100/60 bg-brand-50/40 px-4 py-3">
          <div className="text-lg font-semibold">{t('app.candidate_card.history.modal.title')}</div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-ghost text-sm"
              onClick={onReload}
              disabled={loading}
            >
              {loading ? t('app.candidate_card.actions.refreshing') : t('app.candidate_card.actions.refresh')}
            </button>
            <button type="button" className="btn-ghost text-sm" onClick={onClose}>
              {t('common.actions.close')}
            </button>
          </div>
        </div>
        <div className="max-h-[calc(80vh-56px)] overflow-auto">
          {loading ? (
            <div className="px-4 py-6 text-sm text-gray-500">{t('common.loading')}</div>
          ) : error ? (
            <div className="px-4 py-6 text-sm text-rose-600">{error}</div>
          ) : entries.length === 0 ? (
            <div className="px-4 py-6 text-sm text-gray-500">
              {infoMessage || t('app.candidate_card.history.empty')}
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">{t('app.candidate_card.history.modal.columns.when')}</th>
                  <th className="px-3 py-2 text-left">{t('app.candidate_card.history.modal.columns.change')}</th>
                  <th className="px-3 py-2 text-left">{t('app.candidate_card.history.modal.columns.actor')}</th>
                  <th className="px-3 py-2 text-left">{t('app.candidate_card.history.modal.columns.comment')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-3 py-2 text-xs text-gray-500">
                      {entry.at ? formatDateTime(entry.at) : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span>{t('app.candidate_card.history.modal.previous')}</span>
                          {renderStage(entry.from_code)}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span>{t('app.candidate_card.history.modal.next')}</span>
                          {renderStage(entry.to_code)}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-600">{entry.actor || '—'}</td>
                    <td className="px-3 py-2 text-xs text-gray-600">
                      {entry.reason ? entry.reason : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
