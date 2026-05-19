// src/pages/CandidateCard.tsx
import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import type { InputHTMLAttributes } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import clsx from 'clsx'
import { IconBuilding } from '@tabler/icons-react'
import { recordPerfMeasurement } from '../api/analytics'
import { api, completeActivity, completeReminder, createActivity, createReminder, listReminders, snoozeActivity, snoozeReminder } from '../api/client'
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
import type { ReminderRecord } from '../api/types'
import { formatDistanceToNow } from 'date-fns'
import { enUS, pl, ru } from 'date-fns/locale'
import { createDeleteRequest } from '../api/deletionRequests'
import { sendRodo } from '../api/legalDocuments'
import { useMetaStages } from '../store/useMeta'
import CandidateDocuments from '../modules/documents/CandidateDocuments'
import { exportCandidateBundle } from '../api/documents'
import { createCandidateUploadLink, type CandidateUploadLinkResponse } from '../api/candidates'
import { useCandidateNextAction } from '../components/candidate/useCandidateNextAction'
import {
  approveCandidatePipelineOverride,
  createCandidatePipelineOverride,
  listCandidatePipelineOverrides,
  rejectCandidatePipelineOverride,
  type CandidatePipelineOverride,
} from '../api/candidatePipelineOverrides'
import { getVacancy } from '../api/vacancies'
import {
  getCandidateProfile,
  listCandidateProfiles,
  type CandidateProfile,
} from '../api/candidate_profiles'

const DEFAULT_PROFILE_CODE = 'driver_ce_default'

function translateDocTypeLabel(t: TranslateFn, docCode: string): string {
  const key = `admin.documents.types.${docCode}`
  const out = t(key)
  return out === key ? docCode : out
}

function translateCandidateFieldKey(t: TranslateFn, fieldKey: string, label: string): string {
  const key = `app.candidate_card.fields.${fieldKey}`
  const out = t(key)
  return out === key ? label || fieldKey : out
}

type CandidateEditPhase = 'idle' | 'picking_reason' | 'editing'
import { getFunnel } from '../api/funnels'
import { validateRequiredFields } from '../utils/profileUtils'
import { buildInboxHubPath } from '../utils/inboxDeepLinks'
import { isCandidateRecruiterIdCanonEnabled } from '../utils/featureFlags'
import { usePermissions } from '../hooks/usePermissions'
import { useServiceOrders } from '../hooks/useAdditionalServices'
import { servicesWorkspacePath } from '../modules/services/utils'
import { useI18n, type TranslateFn } from '../i18n'
import { PREFERRED_CONTACT_VALUES } from '../data/preferredContactChannels'
import { isCandidateOperationallyTerminal, isPipelineCompletedCanonicalStage } from '../utils/candidatePipelineCompleted'
import { canonicalStageKey, translateReasonLabel, translateStageLabel } from '../utils/stageLabels'
import { scoreMissingHintForStage } from '../utils/candidateMissingDataHints'
import {
  contactAttemptPipelineBlocksForward,
  docsIssuesPresent,
  docsPipelineBlocksForwardResolved,
  hiringPipelineGatesFromApi,
  pipelineRelaxedTypesFromOverrides,
  relaxDocBlockers,
  vacancyPipelineBlocksForward,
} from '../utils/candidateStageDocPolicy'
import { useHiringPipelineGates } from '../contexts/HiringPipelineGatesContext'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { getRegionDisplayName, getLanguageDisplayName } from '../utils/catalogLocale'
import { getCachedCandidate, setCachedCandidate } from '../api/candidateCache'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageBreadcrumb } from '../components/nav/PageBreadcrumb'
import { useToast } from '../components/Toast'
import { formatErrorForDisplay, getErrorMessage } from '../utils/errorHandling'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { getFriendlyErrorInfo } from '../utils/friendlyError'
import CandidateHeader from '../components/candidate/CandidateHeader'
import CandidateApplicationsSection from '../components/candidate/CandidateApplicationsSection'
import CandidateRemindersSection from '../components/candidate/CandidateRemindersSection'
import CandidateBasicSection from '../components/candidate/CandidateBasicSection'
import { CandidateWorkforceTerminationSection } from '../components/candidate/CandidateWorkforceTerminationSection'
import CandidatePersonalSection from '../components/candidate/CandidatePersonalSection'
import CandidateStatusSection from '../components/candidate/CandidateStatusSection'
import CandidateExperienceSection from '../components/candidate/CandidateExperienceSection'
import CandidateCustomFieldsSection from '../components/candidate/CandidateCustomFieldsSection'
import CandidateRodoSection from '../components/candidate/CandidateRodoSection'
import CandidateContactAttemptsSection from '../components/candidate/CandidateContactAttemptsSection'
import CandidateTimelinePanel from '../components/candidate/CandidateTimelinePanel'
import CandidateStageDecisionPanel from '../components/candidate/CandidateStageDecisionPanel'
import { Input, SearchableSelect } from '../components/candidate/shared/FormComponents'
// CandidateCard layout: Info (top) / Control (right) / Content (main)
// Documents are rendered as a single compact panel inside the rail.
import CandidateNextActionPanel from '../components/candidate/CandidateNextActionPanel'
import CandidateNotesRailSection from '../components/candidate/CandidateNotesRailSection'
import CandidateDocsRailPanel from '../components/candidate/CandidateDocsRailPanel'
import RailPrimaryStepFrame from '../components/candidate/RailPrimaryStepFrame'
import { railHasUrgentReminder, resolveRailPrimaryFocus } from '../utils/railPrimaryFocus'
import { createHandoff, getAvailableClients, getHandoffStatus, type AvailableClientOut, type HandoffStatusResponse } from '../api/handoffs'
import { listTenantLinks, resolvePrimaryHandoffDestination, type TenantLink } from '../api/tenantLinks'
import { isPostRecruitmentStageCode } from '../constants/recruitmentStageBoundary'
import { deriveDocsMeta } from '../modules/candidates/utils'
import {
  ADDRESS_KEYS,
  UUID_RE,
  CREATE_FIELDS,
  PATCH_AFTER_CREATE_FIELDS,
  MAX_EMPLOYMENTS,
  SERVICE_ORDER_STATUSES,
  SERVICE_ITEM_STATUSES,
  POLAND_BASIS_VALUES,
} from '../modules/candidate-card/constants'
import type { PreferredContact, Option, AddressFields, CandidateNote, StageHistoryEntry } from '../modules/candidate-card/types'
import {
  createLocalId,
  ccToFlag,
  makeAddress,
  isUuidLike,
  formatDateTime,
  parseJSONSafe,
  splitFullName,
  formatAmount,
  mapResidencyStatusToPolandBasis,
} from '../modules/candidate-card/utils'
import { formatDateSafe } from '../modules/candidates/candidateUtils'

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
// ccToFlag, makeAddress are now imported from modules/candidate-card/utils

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

const CANDIDATE_OVERRIDE_KEYS = new Set([
  'first_name',
  'last_name',
  'email',
  'phone',
  'phone_country_code',
  'languages',
  'country_code',
  'city',
  'birth_date',
  'address',
  'personal_data',
  'contacts',
])

function stripCandidateOverrideFields(payload: Record<string, any>): Record<string, any> {
  const out: Record<string, any> = {}
  for (const [key, value] of Object.entries(payload || {})) {
    if (CANDIDATE_OVERRIDE_KEYS.has(key)) continue
    out[key] = value
  }
  return out
}

function getCandidateOverrideFields(payload: Record<string, any>): string[] {
  return Object.keys(payload || {}).filter((key) => CANDIDATE_OVERRIDE_KEYS.has(key))
}

// splitFullName is now imported from modules/candidate-card/utils

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

const employmentRowsFingerprint = (rows: EmploymentRow[]): string => {
  const normalized = (rows || [])
    .map((row) => ({
      id: row.id || null,
      localId: row.localId,
      snapshot: employmentSnapshot(row),
    }))
    .filter(({ snapshot }) => employmentRowHasData(snapshot))
  return JSON.stringify(normalized)
}

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
    current_location: null,
    frigo_experience: null,
    has_adr: null,
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
  result.current_location = merged.current_location ? String(merged.current_location) : null
  if (merged.frigo_experience === true || merged.frigo_experience === false) {
    result.frigo_experience = merged.frigo_experience
  } else {
    result.frigo_experience = null
  }
  if (merged.has_adr === true || merged.has_adr === false) {
    result.has_adr = merged.has_adr
  } else {
    result.has_adr = null
  }
  const wt = (merged as { workforce_termination?: unknown }).workforce_termination
  if (wt && typeof wt === 'object' && !Array.isArray(wt)) {
    ;(result as CandidateExtra).workforce_termination = { ...(wt as Record<string, unknown>) } as NonNullable<
      CandidateExtra['workforce_termination']
    >
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

// formatAmount, isUuidLike, mapResidencyStatusToPolandBasis, POLAND_BASIS_VALUES are now imported from modules/candidate-card
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
    tags: [],
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

// formatDateTime, parseJSONSafe are now imported from modules/candidate-card/utils

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
    (raw?.recruiter_id && isUuidLike(raw.recruiter_id) && String(raw.recruiter_id))
    || (raw?.manager_id && isUuidLike(raw.manager_id) && String(raw.manager_id))
    || (isUuidLike(raw?.manager) ? String(raw.manager) : undefined)
    || ((previous as any)?.recruiter_id && isUuidLike((previous as any).recruiter_id) && String((previous as any).recruiter_id))
    || (isUuidLike((previous as any)?.manager_id) ? String((previous as any).manager_id) : undefined)
    || (isUuidLike(previous?.manager) ? String(previous?.manager) : null)

  const managerDisplayName =
    raw?.manager_name ??
    (managerId ? (raw?.manager_name ?? previous?.manager_name ?? null) : null) ??
    (typeof raw?.manager === 'string' && !isUuidLike(raw.manager) ? raw.manager : previous?.manager_name ?? null)

  // When API returns masked candidate, do not use previous/cache for PII (no substitution of cached name/email/phone)
  const isMasked = raw?.masked === true
  const result: Candidate = {
    ...(previous ?? {} as Candidate),
    ...raw,
    id: String(raw?.id ?? previous?.id ?? ''),
    first_name: isMasked ? (raw?.first_name ?? '') : (raw?.first_name ?? previous?.first_name ?? intakeNameParts.first ?? ''),
    last_name: isMasked ? (raw?.last_name ?? '') : (raw?.last_name ?? previous?.last_name ?? intakeNameParts.last ?? ''),
    email: isMasked ? (raw?.email ?? '') : (raw?.email ?? previous?.email ?? intakeEmail ?? ''),
    phone: isMasked ? (raw?.phone ?? '') : (raw?.phone ?? previous?.phone ?? intakePhone ?? ''),
    stage: raw?.stage ?? previous?.stage ?? '',
    manager: managerId ?? '',
    manager_name: managerDisplayName ?? null,
    company_id: raw?.company_id ?? previous?.company_id ?? null,
    vacancy_id: raw?.vacancy_id ?? previous?.vacancy_id ?? null,
    company_name: raw?.company_name ?? previous?.company_name ?? '',
    vacancy_name: raw?.vacancy_name ?? previous?.vacancy_name ?? '',
    short_id: raw?.short_id ?? previous?.short_id ?? null,
    phone_country_code: isMasked
      ? (raw?.phone_country_code ?? '')
      : (raw?.phone_country_code ?? previous?.phone_country_code ?? (intakePhoneCode || '')),
    languages,
    tags: Array.isArray(raw?.tags) ? raw.tags.filter((t: any) => t && String(t).trim()).map((t: any) => String(t).trim()) : (Array.isArray(previous?.tags) ? previous.tags : []),
    is_favorite: typeof raw?.is_favorite === 'boolean' ? raw.is_favorite : (previous?.is_favorite ?? false),
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
    masked: raw?.masked ?? previous?.masked ?? false,
    can_edit: raw?.can_edit ?? previous?.can_edit ?? true,
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


/* ------------------------------- основная страница ------------------------------- */
export default function CandidateCard(){
  const { t, locale } = useI18n()
  const unknownErrorLabel = t('common.errors.unknown')
  const { id } = useParams<{id: UUID | 'new'}>()
  const location = useLocation()
  const isNew = id === 'new'
  const nav = useNavigate()
  const { can, role: permissionsRole, isClientTenant, tenantId } = usePermissions()
  const { gates: hiringGatesApi } = useHiringPipelineGates()
  const hiringGatesRuntime = useMemo(() => hiringPipelineGatesFromApi(hiringGatesApi), [hiringGatesApi])
  const canRequestDelete = can('candidates.requestDelete')
  const canDeleteDirect = can('admin.deletionQueue') || can('admin.users')
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()

  const meta = useMetaStages()
  const originPath = useMemo(() => {
    const originFromState = (location.state as any)?.originPath
    if (
      typeof originFromState === 'string' &&
      originFromState.startsWith(`${CRM_APP_PATHS.appShellPrefix}/`)
    ) {
      return originFromState
    }
    return CRM_APP_PATHS.candidates
  }, [location.state])
  const [isHandoffEnabledForCurrentCompany, setIsHandoffEnabledForCurrentCompany] = useState(false)
  const [companyHandoffLink, setCompanyHandoffLink] = useState<TenantLink | null>(null)
  const [model, setModel] = useState<Candidate | null>(null)
  const [stageHistory, setStageHistory] = useState<StageHistoryEntry[]>([])
  const [stageSinceAt, setStageSinceAt] = useState<string | null>(null)
  useEffect(() => {
    if (isClientTenant) {
      setIsHandoffEnabledForCurrentCompany(false)
      setCompanyHandoffLink(null)
      return
    }
    const companyId = String(model?.company_id || '').trim()
    const agencyTenantId = String(tenantId || '').trim()
    if (!agencyTenantId || !companyId) {
      setIsHandoffEnabledForCurrentCompany(false)
      setCompanyHandoffLink(null)
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const links = await listTenantLinks(agencyTenantId)
        if (cancelled) return
        const matched =
          links.find(
            (link) =>
              String(link.client_company_id || '').trim() === companyId ||
              String(link.handoff_include_company_id || '').trim() === companyId,
          ) || null
        setCompanyHandoffLink(matched)
        setIsHandoffEnabledForCurrentCompany(Boolean(matched?.handoff_enabled))
      } catch {
        if (!cancelled) {
          setIsHandoffEnabledForCurrentCompany(false)
          setCompanyHandoffLink(null)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isClientTenant, tenantId, model?.company_id])
  
  const [candidateProfile, setCandidateProfile] = useState<CandidateProfile | null>(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileFunnelStages, setProfileFunnelStages] = useState<Array<{ code: string; label: string }>>([])

  useEffect(() => {
    if (!candidateProfile?.funnel_id) {
      setProfileFunnelStages([])
      return
    }
    getFunnel(candidateProfile.funnel_id)
      .then((f) => setProfileFunnelStages((f.stages || []).map((s) => ({ code: s.code, label: s.label }))))
      .catch(() => setProfileFunnelStages([]))
  }, [candidateProfile?.funnel_id])

  // Полный список этапов профиля (без фильтра по роли)
  const profileStageCodes = useMemo(() => {
    let codes: string[] = []
    if (profileFunnelStages.length > 0) {
      codes = profileFunnelStages.map((s) => s.code)
    } else if (candidateProfile?.config?.stage_configs && Array.isArray(candidateProfile.config.stage_configs)) {
      const profileStages = candidateProfile.config.stage_configs
        .filter((stage: any) => stage.active !== false)
        .map((stage: any) => stage.stage_code)
        .filter(Boolean)
      if (profileStages.length > 0) {
        codes = profileStages
      }
    }
    if (!codes.length) {
      codes = meta?.order || meta?.codes || []
    }
    return codes
  }, [candidateProfile, meta, profileFunnelStages])

  // Ограничиваем список для селекта с учетом роли клиента
  const stageOptions = useMemo(() => {
    const codes = profileStageCodes
    if (!meta?.meta) return codes
    if (isClientTenant) {
      return codes.filter((code) => meta.meta?.[code]?.visible_for_client)
    }
    if (isHandoffEnabledForCurrentCompany) {
      return codes.filter((code) => {
        const stageMeta = meta.meta?.[code]
        if (stageMeta?.visible_for_agency) return true
        const canonical = canonicalStageKey(code, null) || String(code).trim().toLowerCase()
        if (canonical === 'handoff_returned') return true
        return isPipelineCompletedCanonicalStage(canonical)
      })
    }
    return codes
  }, [profileStageCodes, meta, isClientTenant, isHandoffEnabledForCurrentCompany])

  const existingStageCodesSet = useMemo(
    () => new Set((profileStageCodes || []).map((code) => String(code).trim()).filter(Boolean)),
    [profileStageCodes],
  )

  const timelineStageHistory = useMemo(
    () =>
      stageHistory.filter((entry) => {
        const fromCode = String(entry?.from_code || '').trim()
        const toCode = String(entry?.to_code || '').trim()
        if (toCode && existingStageCodesSet.has(toCode)) return true
        if (fromCode && existingStageCodesSet.has(fromCode)) return true
        return false
      }),
    [stageHistory, existingStageCodesSet],
  )

  const stageLabelIntl = useCallback((code: string) => {
    const funnelStage = profileFunnelStages.find((s) => s.code === code)
    let profileLabel: string | null = null
    if (candidateProfile?.config?.stage_configs) {
      const profileStage = candidateProfile.config.stage_configs.find(
        (s: any) => s.stage_code === code
      )
      if (profileStage?.stage_label) profileLabel = String(profileStage.stage_label)
    }
    const fallback = profileLabel || funnelStage?.label || meta?.labels?.[code] || code
    // IMPORTANT: always translate via canonical stage key; do not render Polish labels directly.
    return translateStageLabel(t, code, fallback)
  }, [candidateProfile, meta?.labels, profileFunnelStages, t])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savedOk, setSavedOk] = useState(false)
  const [downloadingBundle, setDownloadingBundle] = useState(false)
  const [uploadLinkBusy, setUploadLinkBusy] = useState(false)
  const [uploadLink, setUploadLink] = useState<CandidateUploadLinkResponse | null>(null)
  const [, setUploadLinkCopied] = useState(false)
  const HEADER_STORAGE_KEY = 'hf:candidate:headerExpanded'
  const [headerExpanded, setHeaderExpanded] = useState(() => {
    try {
      return window.localStorage.getItem(HEADER_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })
  const [deleteRequestLoading, setDeleteRequestLoading] = useState(false)
  const [deleteRequestMessage, setDeleteRequestMessage] = useState<string | null>(null)
  const [deleteRequestError, setDeleteRequestError] = useState<string | null>(null)
  const [candidateEditPhase, setCandidateEditPhase] = useState<CandidateEditPhase>('idle')
  const [candidateOverrideReason, setCandidateOverrideReason] = useState('')
  const [activityModalOpen, setActivityModalOpen] = useState(false)

  useEffect(() => {
    setCandidateEditPhase('idle')
    setCandidateOverrideReason('')
    setActivityModalOpen(false)
  }, [id])

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
  const [rodoSentTrigger, setRodoSentTrigger] = useState(0)
  /** Bumped to open contact-attempt register modal from stage panel (“Contact candidate”). */
  const [contactAttemptOpenSignal, setContactAttemptOpenSignal] = useState(0)

  const lastSavedPayloadRef = useRef<string | null>(null)
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastSavedEmploymentRowsRef = useRef<string | null>(null)
  const employmentAutoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [employmentRows, setEmploymentRows] = useState<EmploymentRow[]>([])
  const [employmentBaseline, setEmploymentBaseline] = useState<Record<string, EmploymentSnapshot>>({})
  const [employmentLoading, setEmploymentLoading] = useState(false)
  const [employmentError, setEmploymentError] = useState<string | null>(null)
  const modelRef = useRef<Candidate | null>(null)
  const employmentRowsRef = useRef<EmploymentRow[]>([])
  const routeIdRef = useRef<string | null>(null)
  const candidateEditPhaseRef = useRef<CandidateEditPhase>('idle')
  const candidateOverrideReasonRef = useRef('')
  candidateEditPhaseRef.current = candidateEditPhase
  candidateOverrideReasonRef.current = candidateOverrideReason
  modelRef.current = model
  employmentRowsRef.current = employmentRows
  if (id !== routeIdRef.current) {
    routeIdRef.current = id ?? null
    lastSavedPayloadRef.current = null
    lastSavedEmploymentRowsRef.current = null
    if (employmentAutoSaveTimerRef.current) {
      clearTimeout(employmentAutoSaveTimerRef.current)
      employmentAutoSaveTimerRef.current = null
    }
  }
  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [remindersLoading, setRemindersLoading] = useState(false)
  const [remindersError, setRemindersError] = useState<FriendlyErrorInfo | null>(null)
  // G-8 stage 1b: tick bumped after mutations that change the next-action
  // signal (reminder create/complete/snooze, handoff create, contact attempt).
  // Stage transitions are picked up automatically via the `candidate-updated`
  // window event the hook listens to.
  const [nextActionTick, setNextActionTick] = useState(0)
  const bumpNextActionTick = useCallback(() => {
    setNextActionTick((n) => n + 1)
  }, [])
  const {
    data: nextActionDto,
    loading: nextActionLoading,
    error: nextActionError,
  } = useCandidateNextAction(model?.id ?? null, nextActionTick)
  const [reminderBusy, setReminderBusy] = useState<string | null>(null)
  const [reminderTitle, setReminderTitle] = useState('')
  const [reminderDueAt, setReminderDueAt] = useState(() => {
    const dt = new Date(Date.now() + 60 * 60 * 1000)
    return dt.toISOString().slice(0, 16)
  })
  const [reminderOffset, setReminderOffset] = useState(15)
  const [timelineReminders, setTimelineReminders] = useState<ReminderRecord[]>([])
  const [timelineRemindersLoading, setTimelineRemindersLoading] = useState(false)
  const [timelineStageHistoryLoading, setTimelineStageHistoryLoading] = useState(false)
  const [timelineError, setTimelineError] = useState<FriendlyErrorInfo | null>(null)
  const [docsBlockers, setDocsBlockers] = useState<{ missing: string[]; problematic: string[]; inProgress: string[] }>({
    missing: [],
    problematic: [],
    inProgress: [],
  })
  const [docsBlockersLoading, setDocsBlockersLoading] = useState(false)
  const [docsSummaryRefreshTrigger, setDocsSummaryRefreshTrigger] = useState(0)
  const [pipelineOverrides, setPipelineOverrides] = useState<CandidatePipelineOverride[]>([])
  const [pipelineOverrideBusy, setPipelineOverrideBusy] = useState(false)
  const [docsDrawerOpen, setDocsDrawerOpen] = useState(false)
  const [docsDrawerType, setDocsDrawerType] = useState<string | undefined>(undefined)
  const docsVerifyTaskSignatureRef = useRef<string | null>(null)
  const [handoffStatus, setHandoffStatus] = useState<HandoffStatusResponse | null>(null)
  const [handoffClients, setHandoffClients] = useState<AvailableClientOut[]>([])
  const [handoffLoading, setHandoffLoading] = useState(false)
  const [handoffModalOpen, setHandoffModalOpen] = useState(false)
  const [handoffSubmitting, setHandoffSubmitting] = useState(false)
  const [handoffClientLinkId, setHandoffClientLinkId] = useState('')
  const docsNeedsVerification = docsBlockers.inProgress.length > 0
  const docsNeedsRequest = docsBlockers.missing.length > 0 || docsBlockers.problematic.length > 0
  const dateFnsLocale = useMemo(() => (locale === 'ru' ? ru : locale === 'pl' ? pl : enUS), [locale])

  const nextAction = useMemo(() => {
    const parseTs = (value?: string | null): number => {
      if (!value) return 0
      const ts = Date.parse(String(value))
      return Number.isNaN(ts) ? 0 : ts
    }
    const active = (reminders || []).filter((r) => r && r.status !== 'done' && r.status !== 'cancelled')
    if (!active.length) return null
    const now = Date.now()
    active.sort((a, b) => {
      const aDue = parseTs(a.due_at)
      const bDue = parseTs(b.due_at)
      const aOver = a.status === 'overdue' || (aDue > 0 && aDue < now)
      const bOver = b.status === 'overdue' || (bDue > 0 && bDue < now)
      if (aOver !== bOver) return aOver ? -1 : 1
      if (aDue !== bDue) return (aDue || Number.MAX_SAFE_INTEGER) - (bDue || Number.MAX_SAFE_INTEGER)
      return String(a.id).localeCompare(String(b.id))
    })
    return active[0] ?? null
  }, [reminders])

  const nextActionDueLabel = useMemo(() => {
    if (!nextAction?.due_at) return '—'
    try {
      return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : undefined, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      }).format(new Date(nextAction.due_at))
    } catch {
      return String(nextAction.due_at)
    }
  }, [locale, nextAction?.due_at])

  const docsMetaSummary = useMemo(() => {
    try {
      return deriveDocsMeta(model as any)
    } catch {
      return null
    }
  }, [model])

  const docsCountsSummary = useMemo(() => {
    const p = sanitizeDocsProgress((model as any)?.docs_progress)
    const total = Number(p.total ?? p.count ?? 0) || 0
    const ready = Number(p.ready ?? p.verified ?? p.approved ?? 0) || 0
    const problem = Number(p.problem ?? p.invalid ?? p.expired ?? p.overdue ?? 0) || 0
    const inProgress = Number(p.in_progress ?? p.submitted ?? p.pending_validation ?? 0) || 0
    return { total, ready, problem, inProgress }
  }, [model])

  const docsPctSummary = useMemo(() => {
    const total = docsCountsSummary.total || 0
    if (!total) return 0
    return Math.max(0, Math.min(100, Math.round((docsCountsSummary.ready / total) * 100)))
  }, [docsCountsSummary.ready, docsCountsSummary.total])

  const isRodoStageBlockedError = useCallback((err: any): boolean => {
    const status = Number(err?.response?.status || 0)
    const detailRaw = err?.response?.data?.detail
    const detail = String(detailRaw || '').trim().toLowerCase()
    if (status !== 409) return false
    return detail.includes('rodo must be sent') || detail.includes('contact/screening stage')
  }, [])

  const parseHandoffDocsIncomplete = useCallback((err: any): { missingTypes: string[] } | null => {
    const detailRaw = err?.response?.data?.detail
    const toMissing = (val: any): string[] =>
      Array.isArray(val) ? val.map((x) => String(x || '').trim()).filter(Boolean) : []

    if (detailRaw && typeof detailRaw === 'object') {
      const code = String((detailRaw as any).code || '').trim()
      if (code === 'handoff_docs_incomplete') {
        return { missingTypes: toMissing((detailRaw as any).missing_types) }
      }
    }

    if (typeof detailRaw === 'string') {
      const trimmed = detailRaw.trim()
      if (trimmed.includes('handoff_docs_incomplete')) {
        try {
          const parsed = JSON.parse(trimmed)
          if (parsed && typeof parsed === 'object' && String((parsed as any).code || '') === 'handoff_docs_incomplete') {
            return { missingTypes: toMissing((parsed as any).missing_types) }
          }
        } catch {
          return { missingTypes: [] }
        }
      }
    }
    return null
  }, [])

  // Функция для загрузки профиля из вакансии
  const loadProfileFromVacancy = useCallback(async (vacancyId: string | null) => {
    if (!vacancyId) {
      setCandidateProfile(null)
      return
    }

    try {
      setProfileLoading(true)
      let vacancy: any = null
      try {
        vacancy = await getVacancy(vacancyId)
      } catch (vacancyErr: any) {
        const status = Number(vacancyErr?.response?.status || 0)
        // Client can legitimately get 404/403 for agency vacancy.
        // Keep card usable and fallback to default candidate profile.
        if (status === 404 || status === 403) {
          try {
            const profiles = await listCandidateProfiles()
            const defaultProfile = profiles.find((p) => p.code === DEFAULT_PROFILE_CODE)
            setCandidateProfile(defaultProfile ?? null)
          } catch {
            setCandidateProfile(null)
          }
          return
        }
        throw vacancyErr
      }
      if (!vacancy?.candidate_profile_id) {
        try {
          const profiles = await listCandidateProfiles()
          const defaultProfile = profiles.find((p) => p.code === DEFAULT_PROFILE_CODE)
          setCandidateProfile(defaultProfile ?? null)
        } catch {
          setCandidateProfile(null)
        }
        return
      }
      const profileId = vacancy.candidate_profile_id
      if (profile404Ref.current.has(profileId)) {
        const profiles = await listCandidateProfiles()
        const defaultProfile = profiles.find((p) => p.code === DEFAULT_PROFILE_CODE)
        if (defaultProfile) setCandidateProfile(defaultProfile)
        else setCandidateProfile(null)
        return
      }
      if (profilePendingRef.current.has(profileId)) {
        return
      }
      profilePendingRef.current.add(profileId)
      try {
        const profile = await getCandidateProfile(profileId)
        if (!profile.is_active) {
          console.warn('[CandidateCard] Profile is inactive', profile.id)
          notify({
            title: t('app.candidate_card.messages.profile_inactive', {
              values: { name: profile.name },
            }),
            variant: 'warning',
          })
        }
        setCandidateProfile(profile)
      } catch (profileErr: any) {
        const status = profileErr?.response?.status
        const useDefaultByDefault = status === 404 || status === 403
        if (useDefaultByDefault) {
          profile404Ref.current.add(profileId)
          try {
            const profiles = await listCandidateProfiles()
            const defaultProfile = profiles.find((p) => p.code === DEFAULT_PROFILE_CODE)
            if (defaultProfile) {
              setCandidateProfile(defaultProfile)
              if (!profile404ToastShownRef.current.has(profileId)) {
                profile404ToastShownRef.current.add(profileId)
                notify({
                  title: t('app.candidate_card.messages.profile_fallback_default'),
                  variant: 'warning',
                })
              }
              return
            }
          } catch (_) {
            /* ignore */
          }
          if (!profile404ToastShownRef.current.has(profileId)) {
            profile404ToastShownRef.current.add(profileId)
            notify({
              title: t('app.candidate_card.messages.profile_not_found'),
              variant: 'warning',
            })
          }
        } else {
          console.error('[CandidateCard] Failed to load profile', profileErr)
        }
        setCandidateProfile(null)
      } finally {
        profilePendingRef.current.delete(profileId)
      }
    } catch (err) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) {
        setCandidateProfile(null)
        return
      }
      console.error('[CandidateCard] Failed to load vacancy or profile', err)
      setCandidateProfile(null)
    } finally {
      setProfileLoading(false)
    }
  }, [notify, planLimitModal, t, unknownErrorLabel])
  useEffect(() => {
    try {
      window.localStorage.setItem(HEADER_STORAGE_KEY, headerExpanded ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [headerExpanded])
  const basicRef = useRef<HTMLDivElement | null>(null)
  const personalRef = useRef<HTMLDivElement | null>(null)
  const statusRef = useRef<HTMLDivElement | null>(null)
  const experienceRef = useRef<HTMLDivElement | null>(null)
  const customFieldsRef = useRef<HTMLDivElement | null>(null)
  const employerRef = useRef<HTMLDivElement | null>(null)
  const notesRef = useRef<HTMLDivElement | null>(null)
  const employmentInitRef = useRef(false)
  /** Profile IDs that returned 404 — skip refetch, use default profile. */
  const profile404Ref = useRef<Set<string>>(new Set())
  /** Profile IDs currently being fetched — avoid duplicate GET requests. */
  const profilePendingRef = useRef<Set<string>>(new Set())
  /** Profile IDs we already showed 404 toast for this mount — avoid spam. */
  const profile404ToastShownRef = useRef<Set<string>>(new Set())
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

  // загрузка каталогов (с локализацией названий стран и языков)
  useEffect(() => {
    (async () => {
      try{
        const [c, l, d, m, v] = await Promise.all([
          api.get('/catalogs/countries'),
          api.get('/catalogs/languages'),
          api.get('/catalogs/dial-codes'),
          api.get('/catalogs/managers', { params: { roles: 'recruiter' } }).catch(()=>({ data: [] })),
          api.get('/vacancies/').catch(()=>({ data: [] })),
        ])

        // countries / languages — localized via Intl.DisplayNames
        const countriesArr: Option[] = toArray(c.data)
          .map((x: any) => {
            const code = String(x.code ?? x.id ?? '')
            return { value: code, label: getRegionDisplayName(code, locale) || code }
          })
          .filter((o: Option) => o.value && o.label)
          .sort((a: Option, b: Option) => a.label.localeCompare(b.label, locale))
        setCountries(countriesArr)
        const langsArr: Option[] = toArray(l.data)
          .map((x: any) => {
            const code = String(x.code ?? x.id ?? '')
            return { value: code, label: getLanguageDisplayName(code, locale) || code }
          })
          .filter((o: Option) => o.value && o.label)
          .sort((a: Option, b: Option) => a.label.localeCompare(b.label, locale))
        setLanguages(langsArr)

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
          .sort((a: Option, b: Option) => a.label.localeCompare(b.label, locale))
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
  }, [locale])

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
    const loadReminders = async () => {
      if (!model?.id) return
      setRemindersLoading(true)
      setRemindersError(null)
      try {
        const res = await listReminders({
          entityType: 'candidate',
          entityId: model.id,
          status: ['pending', 'new', 'overdue'],
        })
        const items = Array.isArray(res?.items) ? res.items : []
        setReminders(items.slice(0, 5))
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.load'))) return
        setRemindersError(getFriendlyErrorInfo(err, t('app.reminders.errors.load'), t))
      } finally {
        setRemindersLoading(false)
      }
    }
    void loadReminders()
  }, [model?.id, planLimitModal, t])

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
    let cancelled = false
    const t0 = typeof performance !== 'undefined' ? performance.now() : 0

    void (async () => {
      setLoading(true)
      let outcome: 'ok' | 'not_found' | 'error' = 'ok'
      try {
        if (isNew) {
          const defaultStage = meta?.order?.[0] || meta?.codes?.[0] || 'new'
          setModel(createEmptyCandidate(defaultStage))
        } else {
          if (!id) return
          const cached = getCachedCandidate(id)
          if (cached) {
            setModel(normalizeCandidate(cached, model))
          }
          try {
            const { data } = await api.get(`/candidates/${id}`)
            if (cancelled) return
            const normalized = normalizeCandidate(data, model)
            setModel(normalized)
            setCachedCandidate(id, normalized)

            // Load candidate profile from vacancy
            if (normalized.vacancy_id) {
              await loadProfileFromVacancy(String(normalized.vacancy_id))
            } else {
              setCandidateProfile(null)
            }
          } catch (err: any) {
            if (cancelled) return
            if (err?.response?.status === 404) {
              outcome = 'not_found'
              nav(CRM_APP_PATHS.candidates)
              return
            }
            outcome = 'error'
            throw err
          }
        }
      } catch (loadErr: unknown) {
        if (!cancelled) {
          if (!planLimitModal?.showPlanLimitIfNeeded(loadErr, unknownErrorLabel)) {
            console.error('[CandidateCard] candidate load failed', loadErr)
          }
          outcome = 'error'
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
          if (typeof performance !== 'undefined') {
            const elapsed = Math.max(0, performance.now() - t0)
            void recordPerfMeasurement({
              metricKey: 'candidate.card.open',
              durationMs: Math.round(elapsed),
              route:
                typeof window !== 'undefined'
                  ? window.location.pathname
                  : CRM_APP_PATHS.candidates,
              meta: { candidateId: String(id), isNew, outcome },
            })
          }
        }
      }
    })()

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, isNew, loadProfileFromVacancy, nav, planLimitModal, unknownErrorLabel])

  // Отслеживаем изменение вакансии и перезагружаем профиль
  useEffect(() => {
    if (model?.vacancy_id) {
      void loadProfileFromVacancy(String(model.vacancy_id))
    } else {
      setCandidateProfile(null)
    }
  }, [model?.vacancy_id, loadProfileFromVacancy])

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
    lastSavedEmploymentRowsRef.current = employmentRowsFingerprint(nextRows)
  }, [])

  const reloadCandidateEmployments = useCallback(async (candidateId: string, opts: { withSpinner?: boolean } = {}) => {
    if (!candidateId) return
    if (opts.withSpinner !== false) setEmploymentLoading(true)
    setEmploymentError(null)
    try {
      const records = await listCandidateEmployments(candidateId)
      applyEmploymentRecords(records)
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.candidate_card.errors.employment.load_failed'))) return
      console.error('[CandidateCard] employment list error', err)
      const errorMessage = formatErrorForDisplay(err, { fallback: t('app.candidate_card.errors.employment.load_failed') })
      setEmploymentError(errorMessage)
    } finally {
      if (opts.withSpinner !== false) setEmploymentLoading(false)
    }
  }, [applyEmploymentRecords, planLimitModal, t])

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

    const tags = Array.isArray(m.tags) ? m.tags.filter((t: any) => t && String(t).trim()).map((t: any) => String(t).trim()) : []
    const isFavorite = typeof m.is_favorite === 'boolean' ? m.is_favorite : false

    const payload: Record<string, any> = {
      first_name: (m.first_name || '').trim(),
      last_name: (m.last_name || '').trim(),
      languages,
      tags,
      is_favorite: isFavorite,
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

    // Phase 2.6.G-5 Stage F — canonical assignee field on the PATCH body
    // is ``recruiter_id``. During the transition we keep ``manager`` /
    // ``manager_id`` alongside so (a) a Stage-F-disabled build can still
    // roll back, and (b) older backends that don't yet accept
    // ``recruiter_id`` in ``patch_candidate.allowed_fields`` still
    // receive the assignment via the legacy key. Both columns are kept
    // in lock-step by the backend shadow-write (Stage D).
    const managerFromSelect = isUuidLike(m.manager) ? String(m.manager) : undefined
    const managerFromModel = (m as any).manager_id && isUuidLike((m as any).manager_id) ? String((m as any).manager_id) : undefined
    const recruiterFromModel = (m as any).recruiter_id && isUuidLike((m as any).recruiter_id)
      ? String((m as any).recruiter_id)
      : undefined
    // Manual selection in the UI must override any existing assignee on the model.
    const assigneeId = managerFromSelect || recruiterFromModel || managerFromModel
    if (assigneeId) {
      if (isCandidateRecruiterIdCanonEnabled()) {
        payload.recruiter_id = assigneeId
      }
      // Legacy keys are kept unconditionally so rollback (flag OFF) stays
      // harmless and so that any older deployed backend still resolves
      // the assignee.
      payload.manager = assigneeId
      payload.manager_id = assigneeId
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
      managerId: assigneeId ?? null,
      noteForState: typeof m.note === 'string' ? m.note : (m.note ?? ''),
      statusReasonForState: stageReasonOptions.length > 0 ? statusReasonList : (Array.isArray(m.status_reason) ? m.status_reason : []),
    }
  }

  const computeAutosaveFingerprint = (m: Candidate | null, phase: CandidateEditPhase, reason: string) => {
    if (!m) return ''
    const { payload } = buildCandidatePayload(m, meta?.reason_choices ?? {})
    const stripped = stripCandidateOverrideFields(payload)
    const ov = getCandidateOverrideFields(payload)
    if (phase === 'editing' && ov.length > 0 && reason.trim()) {
      return JSON.stringify({ payload, override_reason: reason.trim() })
    }
    return JSON.stringify(stripped)
  }

  const AUTO_SAVE_DELAY_MS = 1500

  useEffect(() => {
    if (isNew || !model?.id || model.id !== id) return
    const fingerprint = computeAutosaveFingerprint(model, candidateEditPhase, candidateOverrideReason)
    if (lastSavedPayloadRef.current === null) {
      lastSavedPayloadRef.current = fingerprint
      return
    }
    if (lastSavedPayloadRef.current === fingerprint) return
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current)
    autoSaveTimerRef.current = setTimeout(async () => {
      autoSaveTimerRef.current = null
      const m = modelRef.current
      if (!m?.id) return
      const phase = candidateEditPhaseRef.current
      const reason = candidateOverrideReasonRef.current
      const { payload: p } = buildCandidatePayload(m, meta?.reason_choices ?? {})
      const overrideKeys = getCandidateOverrideFields(p)
      const currentStage = String(p.stage || m.stage || '').trim()
      const reasonOptions = (meta?.reason_choices?.[currentStage] ?? [])
      const reasonCodes = Array.isArray(p.status_reason) ? p.status_reason : []
      if (reasonOptions.length > 0 && reasonCodes.length === 0) {
        return
      }

      if (phase === 'editing' && overrideKeys.length > 0) {
        const trimmed = reason.trim()
        if (!trimmed) return
        const nextFp = computeAutosaveFingerprint(m, phase, trimmed)
        if (lastSavedPayloadRef.current === nextFp) return
        try {
          await api.patch(`/candidates/${m.id}`, { ...p, override_reason: trimmed })
          lastSavedPayloadRef.current = nextFp
          setRodoSentTrigger((x) => x + 1)
          setSavedOk(true)
          setTimeout(() => setSavedOk(false), 1500)
          try {
            window.dispatchEvent(new CustomEvent('candidate-updated', { detail: { candidateId: m.id } }))
            localStorage.setItem('hf:candidate-updated', JSON.stringify({ candidateId: m.id, timestamp: Date.now() }))
          } catch {
            /* ignore */
          }
        } catch (err: any) {
          if (!planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) {
            const errorMessage = formatErrorForDisplay(err, { fallback: unknownErrorLabel })
            notify({ title: errorMessage, variant: 'error' })
          }
        }
        return
      }

      const pAuto = stripCandidateOverrideFields(p)
      if (Object.keys(pAuto).length === 0) {
        return
      }
      const serializedAuto = JSON.stringify(pAuto)
      if (lastSavedPayloadRef.current === serializedAuto) {
        return
      }
      try {
        await api.patch(`/candidates/${m.id}`, pAuto)
        lastSavedPayloadRef.current = serializedAuto
        setRodoSentTrigger((x) => x + 1)
        setSavedOk(true)
        setTimeout(() => setSavedOk(false), 1500)
        try {
          window.dispatchEvent(new CustomEvent('candidate-updated', { detail: { candidateId: m.id } }))
          localStorage.setItem('hf:candidate-updated', JSON.stringify({ candidateId: m.id, timestamp: Date.now() }))
        } catch {
          /* ignore */
        }
      } catch (err: any) {
        if (!planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) {
          const errorMessage = formatErrorForDisplay(err, { fallback: unknownErrorLabel })
          notify({ title: errorMessage, variant: 'error' })
        }
      }
    }, AUTO_SAVE_DELAY_MS)
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
        autoSaveTimerRef.current = null
      }
    }
  }, [
    model,
    isNew,
    id,
    meta?.reason_choices,
    notify,
    planLimitModal,
    unknownErrorLabel,
    candidateEditPhase,
    candidateOverrideReason,
  ])

  const EMPLOYMENT_AUTO_SAVE_DELAY_MS = 1500
  useEffect(() => {
    if (isNew || !model?.id) return
    const validationError = validateEmploymentRows(employmentRows)
    if (validationError) return
    const fingerprint = employmentRowsFingerprint(employmentRows)
    if (lastSavedEmploymentRowsRef.current === null) {
      lastSavedEmploymentRowsRef.current = fingerprint
      return
    }
    if (lastSavedEmploymentRowsRef.current === fingerprint) return
    if (employmentAutoSaveTimerRef.current) {
      clearTimeout(employmentAutoSaveTimerRef.current)
    }
    const candidateId = String(model.id)
    employmentAutoSaveTimerRef.current = setTimeout(async () => {
      employmentAutoSaveTimerRef.current = null
      try {
        await syncEmploymentRows(candidateId)
        lastSavedEmploymentRowsRef.current = employmentRowsFingerprint(employmentRowsRef.current)
        setSavedOk(true)
        setTimeout(() => setSavedOk(false), 1200)
      } catch {
        // Validation/API errors are surfaced by syncEmploymentRows.
      }
    }, EMPLOYMENT_AUTO_SAVE_DELAY_MS)
    return () => {
      if (employmentAutoSaveTimerRef.current) {
        clearTimeout(employmentAutoSaveTimerRef.current)
        employmentAutoSaveTimerRef.current = null
      }
    }
  }, [employmentRows, isNew, model?.id, syncEmploymentRows, validateEmploymentRows])

  const fetchCandidate = useCallback(async (candidateId: string, prev?: Candidate | null) => {
    const { data } = await api.get(`/candidates/${candidateId}`)
    const normalized = normalizeCandidate(data, prev || model)
    setCachedCandidate(candidateId, normalized)
    return normalized
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

  const loadStageHistoryQuiet = useCallback(async (candidateId: string) => {
    try {
      const { data } = await api.get(`/candidates/${candidateId}/stage-history`)
      const entries = Array.isArray(data) ? data : []
      const last = entries.length ? entries[entries.length - 1] : null
      setStageSinceAt(last?.at ? String(last.at) : null)
    } catch {
      setStageSinceAt(null)
    }
  }, [])

  const loadStageHistoryForTimeline = useCallback(
    async (candidateId: string) => {
      setTimelineStageHistoryLoading(true)
      setTimelineError(null)
      try {
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
      } catch (err: any) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) return
        setTimelineError(getFriendlyErrorInfo(err, unknownErrorLabel, t))
      } finally {
        setTimelineStageHistoryLoading(false)
      }
    },
    [planLimitModal, unknownErrorLabel, t],
  )

  const loadTimelineReminders = useCallback(
    async (candidateId: string) => {
      setTimelineRemindersLoading(true)
      setTimelineError(null)
      try {
        const res = await listReminders({
          entityType: 'candidate',
          entityId: candidateId,
          status: ['pending', 'new', 'overdue', 'done', 'cancelled'],
        })
        const items = Array.isArray(res?.items) ? res.items : []
        setTimelineReminders(items)
      } catch (err: any) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) {
          setTimelineReminders([])
          return
        }
        setTimelineError(getFriendlyErrorInfo(err, unknownErrorLabel, t))
        setTimelineReminders([])
      } finally {
        setTimelineRemindersLoading(false)
      }
    },
    [planLimitModal, unknownErrorLabel, t],
  )

  const onStageChangePersist = useCallback(
    async (stage: string, statusReason: string[]) => {
      if (isNew || !model?.id) return
      const revertStageOptimistic = async () => {
        try {
          const refreshed = await fetchCandidate(String(model.id), model)
          setModel(refreshed)
        } catch {
          /* ignore */
        }
      }
      const persistStage = async () => {
        await api.patch(`/candidates/${model.id}`, { stage, status_reason: statusReason })
        setRodoSentTrigger((x) => x + 1)
        const m = modelRef.current
        if (m) {
          const merged = { ...m, stage, status_reason: statusReason } as Candidate
          lastSavedPayloadRef.current = computeAutosaveFingerprint(
            merged,
            candidateEditPhaseRef.current,
            candidateOverrideReasonRef.current,
          )
        }
        try {
          window.dispatchEvent(new CustomEvent('candidate-updated', { detail: { candidateId: model.id } }))
          localStorage.setItem('hf:candidate-updated', JSON.stringify({ candidateId: model.id, timestamp: Date.now() }))
        } catch {
          /* ignore */
        }
      }
      try {
        await persistStage()
      } catch (err: any) {
        if (isRodoStageBlockedError(err)) {
          const shouldSendRodo = window.confirm(t('app.candidate_card.messages.rodo_stage_blocked_confirm'))
          if (shouldSendRodo) {
            try {
              await sendRodo(model.id)
              setRodoSentTrigger((x) => x + 1)
              await persistStage()
              notify({
                title: t('app.candidate_card.messages.rodo_sent_retry_success'),
                variant: 'success',
              })
              return
            } catch (retryErr: any) {
              if (!planLimitModal?.showPlanLimitIfNeeded(retryErr, t('app.candidate_card.messages.rodo_send_or_retry_failed'))) {
                const retryMessage = formatErrorForDisplay(retryErr, {
                  fallback: t('app.candidate_card.messages.rodo_send_or_retry_failed'),
                })
                notify({ title: retryMessage, variant: 'error' })
              }
              await revertStageOptimistic()
              return
            }
          }
          notify({
            title: t('app.candidate_card.messages.rodo_stage_blocked'),
            variant: 'error',
          })
          await revertStageOptimistic()
          return
        }
        if (Number(err?.response?.status || 0) === 409) {
          const d = err?.response?.data?.detail
          if (d && typeof d === 'object') {
            const code = String((d as any).code || '')
            if (code === 'stage_blocked_by_risk_gate') {
              notify({
                title: t('app.candidate_card.stage_blocked_by_risk_gate.title'),
                description:
                  typeof (d as any).message === 'string' && (d as any).message
                    ? String((d as any).message)
                    : t('app.candidate_card.stage_blocked_by_risk_gate.description'),
                variant: 'error',
              })
              await revertStageOptimistic()
              return
            }
            if (code === 'stage_blocked_by_documents') {
              const missing = Array.isArray((d as any).missing_types) ? (d as any).missing_types : []
              const problematic = Array.isArray((d as any).problematic_types) ? (d as any).problematic_types : []
              const inProgress = Array.isArray((d as any).in_progress_types) ? (d as any).in_progress_types : []
              const firstHit = [missing[0], problematic[0], inProgress[0]].find(Boolean)
              const docHint = firstHit
                ? String(firstHit)
                : typeof (d as any).message === 'string'
                  ? String((d as any).message)
                  : ''
              notify({
                title: t('app.candidate_card.stage_blocked_by_docs.title'),
                description: docHint || t('app.candidate_card.stage_blocked_by_docs.description_generic'),
                variant: 'error',
              })
              await revertStageOptimistic()
              return
            }
            if (code === 'stage_blocked_by_vacancy') {
              notify({
                title: t('app.candidate_card.stage_blocked_by_vacancy.title'),
                description:
                  typeof (d as any).message === 'string' && (d as any).message
                    ? String((d as any).message)
                    : t('app.candidate_card.stage_blocked_by_vacancy.description'),
                variant: 'error',
              })
              await revertStageOptimistic()
              return
            }
            if (code === 'stage_blocked_by_contact_attempt') {
              notify({
                title: t('app.candidate_card.stage_blocked_by_contact_attempt.title'),
                description:
                  typeof (d as any).message === 'string' && (d as any).message
                    ? String((d as any).message)
                    : t('app.candidate_card.stage_blocked_by_contact_attempt.description'),
                variant: 'error',
              })
              await revertStageOptimistic()
              return
            }
          }
        }
        const handoffDocs = parseHandoffDocsIncomplete(err)
        if (handoffDocs) {
          const missingLabels = handoffDocs.missingTypes.length > 0
            ? handoffDocs.missingTypes.map((docCode) => translateDocTypeLabel(t, docCode)).join(', ')
            : ''
          notify({
            title: t('app.candidate_card.messages.handoff_docs_incomplete'),
            description: missingLabels || undefined,
            variant: 'error',
          })
          await revertStageOptimistic()
          return
        }
        if (!planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) {
          const errorMessage = formatErrorForDisplay(err, { fallback: unknownErrorLabel })
          notify({ title: errorMessage, variant: 'error' })
        }
        await revertStageOptimistic()
      }
    },
    [isNew, model?.id, model, fetchCandidate, notify, planLimitModal, unknownErrorLabel, meta?.reason_choices, isRodoStageBlockedError, parseHandoffDocsIncomplete, t]
  )

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
      notify({ title: t('app.candidate_card.messages.note_added'), variant: 'success' })
    } catch (err:any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) {
        throw err
      }
      const errorMessage = formatErrorForDisplay(err, { fallback: unknownErrorLabel })
      notify({ title: t('app.candidate_card.messages.note_add_failed', { values: { detail: errorMessage } }), variant: 'error' })
      throw err
    } finally {
      setNoteSending(false)
    }
  }, [model?.id, newNote, fetchNotes, planLimitModal, t, unknownErrorLabel, notify])
  useEffect(() => {
    if (isNew) { setNotes([]); return }
    if (!id || typeof id !== 'string') return
    void fetchNotes(id)
  }, [id, isNew, fetchNotes])

  // Определяем extra и setExtra до их использования в save и других функциях
  const extra = useMemo<CandidateExtra>(
    () => sanitizeExtra(model?.extra as CandidateExtra | undefined),
    [model?.extra]
  )
  const docsOwnerContext = useMemo(
    () => ({ citizenship: String(extra?.citizenship || '') }),
    [extra?.citizenship],
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

  const getOverrideFieldLabel = useCallback((raw: string) => {
    const key = String(raw || '').trim().toLowerCase()
    switch (key) {
      case 'first_name': return t('app.candidate_card.fields.first_name')
      case 'last_name': return t('app.candidate_card.fields.last_name')
      case 'email':
      case 'contacts.email': return t('app.candidate_card.fields.email')
      case 'phone':
      case 'contacts.phone':
      case 'contacts.phone_country_code': return t('app.candidate_card.fields.phone')
      case 'languages':
      case 'personal.languages': return t('app.candidate_card.fields.languages')
      case 'country_code':
      case 'personal.country_code': return t('app.candidate_card.fields.country_code')
      case 'city':
      case 'personal.city': return t('app.candidate_card.fields.address.city')
      case 'birth_date':
      case 'personal.birth_date': return t('app.candidate_card.fields.birth_date')
      case 'address':
      case 'personal.address': return t('app.candidate_card.sections.personal.address_current')
      case 'personal_data': return t('app.candidate_card.sections.personal.title')
      case 'contacts': return t('app.candidate_card.sections.basic.title')
      case 'contacts.preferred_messenger': return t('app.candidate_card.fields.preferred_contact')
      case 'personal.citizenship': return t('app.candidate_card.fields.citizenship')
      case 'personal.current_location': return t('app.candidate_card.fields.current_location')
      case 'personal.residency_status': return t('app.candidate_card.fields.residency_status')
      case 'personal.in_poland': return t('app.candidate_card.fields.in_poland')
      case 'experience.years_ce':
      case 'experience.intl_experience':
      case 'experience.trailer_types[]':
      case 'experience.route_types[]':
      case 'employments[]':
        return t('app.candidate_card.sections.experience.title')
      default:
        return raw
    }
  }, [t])

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
        notify({ title: t('app.candidate_card.messages.stage_reason_required'), variant: 'error' })
        setSaving(false)
        return
      }

      // Валидация poland_stay_basis при current_location = in_poland
      if (extra.current_location === 'in_poland' && !extra.poland_stay_basis) {
        notify({
          title: t('app.candidate_card.validation.poland_basis_required'),
          variant: 'error',
        })
        setSaving(false)
        return
      }
      // Валидация обязательных полей из профиля
      const missingFields = validateRequiredFields(candidateProfile, model, extra)
      if (missingFields.length > 0) {
        const fieldLabels = missingFields
          .map((f) => translateCandidateFieldKey(t, f.fieldKey, f.label))
          .join(', ')
        notify({
          title: t('app.candidate_card.messages.required_fields_missing', {
            values: { fields: fieldLabels },
          }),
          variant: 'error',
        })
        setSaving(false)
        return
      }
      if (isNew) {
        const { data } = await api.post('/candidates', createPayload)
        const createdId = data?.id
        const notifyPartialAfterCreate = (err: unknown) => {
          notify({
            title: t('app.candidate_card.messages.partial_save_after_create'),
            description: formatErrorForDisplay(err, { fallback: unknownErrorLabel }),
            variant: 'warning',
          })
        }
        if (createdId && Object.keys(patchAfterCreate).length > 0) {
          try {
            await api.patch(`/candidates/${createdId}`, patchAfterCreate)
          } catch (patchErr: unknown) {
            if (!planLimitModal?.showPlanLimitIfNeeded(patchErr, t('app.candidate_card.messages.partial_save_after_create'))) {
              notifyPartialAfterCreate(patchErr)
            }
          }
        }
        setRodoSentTrigger((x) => x + 1)
        if (createdId) {
          try {
            await syncEmploymentRows(String(createdId))
          } catch (empErr: unknown) {
            if (!planLimitModal?.showPlanLimitIfNeeded(empErr, t('app.candidate_card.messages.partial_save_after_create'))) {
              notifyPartialAfterCreate(empErr)
            }
          }
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
        notify({ title: t('app.candidate_card.messages.saved'), variant: 'success' })
        // Уведомляем страницу списка кандидатов об обновлении
        try {
          const updatedId = createdId || model.id
          if (updatedId) {
            window.dispatchEvent(new CustomEvent('candidate-updated', { detail: { candidateId: String(updatedId) } }))
            // Также используем localStorage для кросс-вкладок
            localStorage.setItem('hf:candidate-updated', JSON.stringify({ candidateId: String(updatedId), timestamp: Date.now() }))
          }
        } catch {
          /* ignore */
        }
        if (createdId) {
          nav(`${CRM_APP_PATHS.candidates}/${createdId}`, { replace: true })
        }
      } else {
        if (model.id) {
          await syncEmploymentRows(String(model.id))
        }
        const overrideFields = getCandidateOverrideFields(payload)
        const overrideReason = candidateOverrideReason.trim()
        if (overrideFields.length > 0 && candidateEditPhase !== 'editing') {
          const fieldLabels = overrideFields.map((f) => getOverrideFieldLabel(f)).filter(Boolean)
          notify({
            title: t('app.candidate_card.messages.override_mode_required'),
            description: fieldLabels.join(', '),
            variant: 'error',
          })
          setSaving(false)
          return
        }
        if (overrideFields.length > 0 && !overrideReason) {
          notify({
            title: t('app.candidate_card.messages.override_reason_missing'),
            variant: 'error',
          })
          setSaving(false)
          return
        }
        let patchResponse: any = null
        try {
          patchResponse = await api.patch(`/candidates/${model.id}`, overrideFields.length > 0
            ? {
                ...payload,
                override_reason: overrideReason,
              }
            : payload)
        } catch (err: any) {
          if (planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) {
            setSaving(false)
            throw err
          }
          const detail = err?.response?.data?.detail
          const code = typeof detail === 'object' && detail ? String((detail as any).code || '') : ''
          if (code === 'override_reason_required') {
            const fields = Array.isArray((detail as any).fields) ? (detail as any).fields : []
            const fieldLabels = fields.map((f: string) => getOverrideFieldLabel(f)).filter(Boolean)
            notify({
              title: t('app.candidate_card.messages.override_reason_missing'),
              description: fieldLabels.join(', '),
              variant: 'error',
            })
            setSaving(false)
            return
          }
          const handoffDocs = parseHandoffDocsIncomplete(err)
          if (handoffDocs) {
            const missingLabels = handoffDocs.missingTypes.length > 0
              ? handoffDocs.missingTypes.map((docCode) => translateDocTypeLabel(t, docCode)).join(', ')
              : ''
            notify({
              title: t('app.candidate_card.messages.handoff_docs_incomplete'),
              description: missingLabels || undefined,
              variant: 'error',
            })
            setSaving(false)
            return
          }
          throw err
        }
        const { data } = patchResponse
        setRodoSentTrigger((x) => x + 1)
        const refreshed = await fetchCandidate(String(data?.id ?? model.id), model)
        setModel(refreshed)
        lastSavedPayloadRef.current = computeAutosaveFingerprint(
          refreshed,
          candidateEditPhaseRef.current,
          candidateOverrideReasonRef.current,
        )
        setSavedOk(true); setTimeout(()=>setSavedOk(false), 2000)
        notify({ title: t('app.candidate_card.messages.saved'), variant: 'success' })
        // Уведомляем страницу списка кандидатов об обновлении
        try {
          window.dispatchEvent(new CustomEvent('candidate-updated', { detail: { candidateId: model.id } }))
          // Также используем localStorage для кросс-вкладок
          localStorage.setItem('hf:candidate-updated', JSON.stringify({ candidateId: model.id, timestamp: Date.now() }))
        } catch {
          /* ignore */
        }
      }
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) {
        throw err
      }
      const handoffDocs = parseHandoffDocsIncomplete(err)
      if (handoffDocs) {
        const missingLabels = handoffDocs.missingTypes.length > 0
          ? handoffDocs.missingTypes.map((docCode) => translateDocTypeLabel(t, docCode)).join(', ')
          : ''
        notify({
          title: t('app.candidate_card.messages.handoff_docs_incomplete'),
          description: missingLabels || undefined,
          variant: 'error',
        })
      } else {
        const errorMessage = formatErrorForDisplay(err, { fallback: unknownErrorLabel })
        notify({ title: t('app.candidate_card.messages.save_failed', { values: { detail: errorMessage } }), variant: 'error' })
      }
      throw err
    } finally {
      setSaving(false)
    }
  }, [model, isNew, nav, fetchCandidate, syncEmploymentRows, planLimitModal, t, unknownErrorLabel, notify, candidateProfile, extra, candidateEditPhase, candidateOverrideReason, getOverrideFieldLabel, parseHandoffDocsIncomplete])

  const downloadBundle = useCallback(async () => {
    if (!model?.id) return
    try {
      setDownloadingBundle(true)
      const blob = await exportCandidateBundle(String(model.id))
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `candidate_${model.id}_bundle.zip`
      a.click()
      URL.revokeObjectURL(url)
      notify({ title: t('app.candidate_card.messages.export_success'), variant: 'success' })
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.candidate_card.messages.export_failed'))) {
        const errorMessage = formatErrorForDisplay(err, { fallback: t('app.candidate_card.messages.export_failed') })
        notify({ title: errorMessage, variant: 'error' })
      }
    } finally {
      setDownloadingBundle(false)
    }
  }, [model?.id, planLimitModal, t, notify])

  const generateUploadLink = useCallback(async (opts?: { copyToClipboard?: boolean; notifyOnReady?: boolean }) => {
    if (!model?.id) return
    const copyToClipboard = opts?.copyToClipboard ?? true
    const notifyOnReady = opts?.notifyOnReady ?? true
    try {
      setUploadLinkBusy(true)
      const data = await createCandidateUploadLink(String(model.id))
      setUploadLink(data)
      setDocsSummaryRefreshTrigger((x) => x + 1)
      const linkPath = data.documents_url || data.apply_url
      const absoluteUrl = new URL(linkPath, window.location.origin).toString()
      if (copyToClipboard && navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(absoluteUrl)
        setUploadLinkCopied(true)
        window.setTimeout(() => setUploadLinkCopied(false), 2000)
        if (notifyOnReady) {
          notify({ title: t('app.candidate_card.actions.upload_link_copied'), variant: 'success' })
        }
      } else if (notifyOnReady) {
        notify({ title: t('app.candidate_card.actions.upload_link_ready'), description: absoluteUrl, variant: 'info' })
      }
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.candidate_card.messages.upload_link_failed'))) {
        const detail = err?.response?.data?.detail || err?.message || t('app.candidate_card.messages.upload_link_failed')
        notify({ title: t('app.candidate_card.messages.upload_link_failed'), description: detail, variant: 'error' })
      }
    } finally {
      setUploadLinkBusy(false)
    }
  }, [model?.id, notify, planLimitModal, t])

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

  const createdAtDisplay = formatDateTime(model?.created_at, locale)
  const resolveStageLabel = useCallback(
    (code: string | null | undefined) => {
      if (!code) return ''
      const fallback = meta?.labels?.[code] || code
      return translateStageLabel(t, code, fallback)
    },
    [meta, t]
  )

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
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.candidate_card.messages.delete_request_failed'))) return
      console.error('[CandidateCard] delete request error', err)
      const errorMessage = formatErrorForDisplay(err, { fallback: t('app.candidate_card.messages.delete_request_failed') })
      setDeleteRequestError(errorMessage)
    } finally {
      setDeleteRequestLoading(false)
    }
  }, [model, planLimitModal, t])

  const handleCreateReminder = useCallback(async () => {
    if (!model?.id || !reminderTitle || !reminderDueAt) return
    try {
      const due = new Date(reminderDueAt)
      const remindAt = new Date(due.getTime() - reminderOffset * 60 * 1000)
      await createActivity({
        title: reminderTitle,
        description: '',
        type: 'custom',
        entity_type: 'candidate',
        entity_id: model.id,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
        source: 'manual',
      })
      setReminderTitle('')
      setReminderDueAt(new Date(due.getTime() + 60 * 60 * 1000).toISOString().slice(0, 16))
      const res = await listReminders({
        entityType: 'candidate',
        entityId: model.id,
        status: ['pending', 'new', 'overdue'],
      })
      const items = Array.isArray(res?.items) ? res.items : []
      setReminders(items.slice(0, 5))
      void loadTimelineReminders(String(model.id))
      bumpNextActionTick()
      notify({ title: t('app.reminders.messages.created'), variant: 'success' })
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.create'))) return
      const info = getFriendlyErrorInfo(err, t('app.reminders.errors.create'), t)
      setRemindersError(info)
      notify({
        title: [info.title, info.detail].filter(Boolean).join(' — ') || info.title,
        variant: 'error',
      })
    }
  }, [model?.id, reminderTitle, reminderDueAt, reminderOffset, planLimitModal, t, notify, loadTimelineReminders, bumpNextActionTick])

  const handleDocsNextActionCreate = useCallback(() => {
    // Distinguish action by blocker type:
    // - missing/problematic -> request docs from candidate
    // - in_progress -> verify and approve/reject uploaded docs
    const dt = new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16)
    if (docsNeedsVerification) {
      setReminderTitle(t('app.candidate_card.next_action.docs_verify_title'))
      setReminderDueAt(dt)
      return
    }
    setReminderTitle(t('app.candidate_card.next_action.docs_request_title'))
    setReminderDueAt(dt)
    // Convenience only: pre-generate docs upload URL for recruiter, but keep
    // "Create task" semantic as task creation (no auto-copy/toast side effects).
    if (docsNeedsRequest) {
      void generateUploadLink({ copyToClipboard: false, notifyOnReady: false })
    }
  }, [docsNeedsRequest, docsNeedsVerification, generateUploadLink, t])

  useEffect(() => {
    if (!model?.id || docsBlockersLoading) return
    const pending = [...(docsBlockers.inProgress || [])].filter(Boolean).sort()
    if (!pending.length) return
    const signature = `${String(model.id)}::${pending.join('|')}`
    if (docsVerifyTaskSignatureRef.current === signature) return

    const hasActiveVerify = (reminders || []).some((r) => {
      if (!r || r.status === 'done' || r.status === 'cancelled') return false
      const type = String(r.type || '').toLowerCase()
      const title = String(r.title || '').toLowerCase()
      const description = String(r.description || '').toLowerCase()
      return type === 'document_review'
        || title.includes('verify uploaded documents')
        || description.includes('[auto:docs_verify]')
    })
    if (hasActiveVerify) {
      docsVerifyTaskSignatureRef.current = signature
      return
    }

    docsVerifyTaskSignatureRef.current = signature
    const dueIso = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString()
    void (async () => {
      try {
        await createActivity({
          title: t('app.candidate_card.next_action.docs_verify_title'),
          description: `[AUTO:DOCS_VERIFY] ${t('app.candidate_card.next_action.docs_verify_description')}`,
          type: 'document_review',
          entity_type: 'candidate',
          entity_id: model.id,
          due_at: dueIso,
          remind_at: dueIso,
          priority: 'high',
          source: 'documents_upload',
        })
        const res = await listReminders({
          entityType: 'candidate',
          entityId: model.id,
          status: ['pending', 'new', 'overdue'],
        })
        const items = Array.isArray(res?.items) ? res.items : []
        setReminders(items.slice(0, 5))
        void loadTimelineReminders(String(model.id))
      } catch {
        // Best-effort automation; user-facing docs flow should not break.
      }
    })()
  }, [docsBlockers.inProgress, docsBlockersLoading, model?.id, reminders, t, loadTimelineReminders])

  const overrideReasonOptions = useMemo(
    () => [
      t('app.candidate_card.override_reasons.data_correction'),
      t('app.candidate_card.override_reasons.docs_fix'),
      t('app.candidate_card.override_reasons.pipeline_fix'),
      t('app.candidate_card.override_reasons.manager_request'),
      t('app.candidate_card.override_reasons.legal_compliance'),
      t('app.candidate_card.override_reasons.other'),
    ],
    [t],
  )

  const scrollToCandidateData = useCallback(() => {
    const el = basicRef.current
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const scrollToEmployerData = useCallback(() => {
    const el = employerRef.current
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const scrollToPersonalData = useCallback(() => {
    const el = personalRef.current
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const toggleCandidateEditMode = useCallback(() => {
    setCandidateEditPhase((phase) => {
      if (phase === 'editing' || phase === 'picking_reason') {
        return 'idle'
      }
      window.setTimeout(() => scrollToCandidateData(), 40)
      return 'picking_reason'
    })
  }, [scrollToCandidateData])

  const confirmOverrideReasonStartEdit = useCallback(() => {
    if (!candidateOverrideReason.trim()) {
      notify({
        title: t('app.candidate_card.messages.override_reason_missing'),
        variant: 'error',
      })
      return
    }
    setCandidateEditPhase('editing')
  }, [candidateOverrideReason, notify, t])

  const handleFavoriteToggle = useCallback(async () => {
    if (!model?.id) return
    try {
      const newFavoriteValue = !model.is_favorite
      await api.patch(`/candidates/${model.id}`, { is_favorite: newFavoriteValue })
      setModel((prev) => {
        if (!prev) return prev
        return { ...prev, is_favorite: newFavoriteValue }
      })
      // Уведомляем страницу списка кандидатов об обновлении
      try {
        window.dispatchEvent(new CustomEvent('candidate-updated', { detail: { candidateId: model.id } }))
        localStorage.setItem('hf:candidate-updated', JSON.stringify({ candidateId: model.id, timestamp: Date.now() }))
      } catch {
        /* ignore */
      }
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, unknownErrorLabel)) {
        const errorMessage = formatErrorForDisplay(err, { fallback: unknownErrorLabel })
        notify({ title: t('app.candidate_card.messages.favorite_toggle_failed', { values: { detail: errorMessage } }), variant: 'error' })
      }
    }
  }, [model?.id, model?.is_favorite, planLimitModal, t, unknownErrorLabel, notify])

  const handleAttemptCreated = useCallback(async () => {
    if (!model?.id) return
    try {
      const refreshed = await fetchCandidate(String(model.id), model)
      setModel(refreshed)
    } catch {
      /* ignore, toast handled by child */
    }
    // Contact attempts and handoff submissions both flow through here and
    // both shift the next-action recommendation (e.g. 'no_contact_attempt'
    // → 'idle' or 'handoff_pending_client_decision').
    bumpNextActionTick()
  }, [model?.id, model, fetchCandidate, bumpNextActionTick])

  const refreshHandoffMeta = useCallback(async () => {
    if (!model?.id) return
    try {
      setHandoffLoading(true)
      const [statusResp, clientsResp] = await Promise.all([
        getHandoffStatus(model.id as UUID, (model.company_id as UUID) || undefined),
        getAvailableClients(),
      ])
      setHandoffStatus(statusResp)
      setHandoffClients(clientsResp)
    } catch {
      setHandoffStatus(null)
      setHandoffClients([])
    } finally {
      setHandoffLoading(false)
    }
  }, [model?.company_id, model?.id])

  useEffect(() => {
    if (isNew || !model?.id) {
      setHandoffStatus(null)
      setHandoffClients([])
      setHandoffClientLinkId('')
      setHandoffModalOpen(false)
      return
    }
    void refreshHandoffMeta()
  }, [isNew, model?.id, refreshHandoffMeta])

  const primaryHandoffDestination = useMemo(
    () => resolvePrimaryHandoffDestination(companyHandoffLink),
    [companyHandoffLink],
  )

  const handoffClientsForCompany = useMemo(() => {
    const cid = String(model?.company_id || '').trim()
    if (!cid) return handoffClients
    return handoffClients.filter((c) => String(c.client_company_id || '').trim() === cid)
  }, [handoffClients, model?.company_id])

  const showAgencyHandoffHeader = useMemo(() => {
    const masked = model?.masked === true
    if (isNew || masked || isClientTenant) return false
    if (!can('candidates.manage')) return false
    if (!isHandoffEnabledForCurrentCompany || !primaryHandoffDestination) return false
    if (primaryHandoffDestination === 'internal_hr') {
      return Boolean(String(model?.company_id || '').trim())
    }
    return handoffClientsForCompany.length > 0
  }, [
    can,
    handoffClientsForCompany.length,
    isClientTenant,
    isHandoffEnabledForCurrentCompany,
    isNew,
    model?.company_id,
    model?.masked,
    primaryHandoffDestination,
  ])

  const handleHandoffCreate = useCallback(async () => {
    if (!model?.id || !primaryHandoffDestination) return
    try {
      setHandoffSubmitting(true)
      if (primaryHandoffDestination === 'internal_hr') {
        const cid = String(model.company_id || '').trim()
        if (!cid) return
        await createHandoff(model.id as UUID, { client_company_id: cid, destination: 'internal_hr' })
      } else {
        if (!handoffClientLinkId) return
        const selectedClient = handoffClients.find((x) => x.link_id === handoffClientLinkId) || null
        if (!selectedClient) return
        const payload = selectedClient.client_company_id
          ? { client_company_id: selectedClient.client_company_id, destination: 'client_portal' as const }
          : selectedClient.client_tenant_id
            ? { client_tenant_id: selectedClient.client_tenant_id, destination: 'client_portal' as const }
            : null
        if (!payload) return
        await createHandoff(model.id as UUID, payload)
      }
      setHandoffModalOpen(false)
      setHandoffClientLinkId('')
      await refreshHandoffMeta()
      await handleAttemptCreated()
      notify({
        title:
          primaryHandoffDestination === 'internal_hr'
            ? t('app.candidate_card.handoff.created_internal')
            : t('app.candidate_card.handoff.created'),
        variant: 'success',
      })
    } catch (e: any) {
      const transferLabel =
        primaryHandoffDestination === 'internal_hr'
          ? t('app.candidate_card.handoff.transfer_internal_hr_btn')
          : t('app.candidate_card.handoff.transfer_client_btn')
      if (!planLimitModal?.showPlanLimitIfNeeded(e, transferLabel)) {
        notify({
          title: e?.response?.data?.detail || e?.message || t('app.common.messages.unexpected'),
          variant: 'error',
        })
      }
    } finally {
      setHandoffSubmitting(false)
    }
  }, [
    handoffClientLinkId,
    handoffClients,
    handleAttemptCreated,
    model?.company_id,
    model?.id,
    notify,
    planLimitModal,
    primaryHandoffDestination,
    refreshHandoffMeta,
    t,
  ])

  useEffect(() => {
    if (!handoffModalOpen || primaryHandoffDestination !== 'client_portal') return
    if (handoffClientLinkId) return
    const first = handoffClientsForCompany[0]
    if (first) setHandoffClientLinkId(first.link_id)
  }, [handoffModalOpen, primaryHandoffDestination, handoffClientsForCompany, handoffClientLinkId])

  const handleReminderComplete = useCallback(async (id: string) => {
    try {
      setReminderBusy(id)
      await completeActivity(id)
      const res = await listReminders({
        entityType: 'candidate',
        entityId: model?.id || '',
        status: ['pending', 'new', 'overdue'],
      })
      const items = Array.isArray(res?.items) ? res.items : []
      setReminders(items.slice(0, 5))
      if (model?.id) void loadTimelineReminders(String(model.id))
      bumpNextActionTick()
      notify({ title: t('app.reminders.messages.completed'), variant: 'success' })
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.complete'))) return
      const info = getFriendlyErrorInfo(err, t('app.reminders.errors.complete'), t)
      setRemindersError(info)
      notify({
        title: [info.title, info.detail].filter(Boolean).join(' — ') || info.title,
        variant: 'error',
      })
    } finally {
      setReminderBusy((prev) => (prev === id ? null : prev))
    }
  }, [model?.id, planLimitModal, t, notify, loadTimelineReminders, bumpNextActionTick])

  const handleReminderSnooze = useCallback(async (id: string, minutes: number) => {
    try {
      setReminderBusy(id)
      await snoozeActivity(id, { minutes })
      const res = await listReminders({
        entityType: 'candidate',
        entityId: model?.id || '',
        status: ['pending', 'new', 'overdue'],
      })
      const items = Array.isArray(res?.items) ? res.items : []
      setReminders(items.slice(0, 5))
      if (model?.id) void loadTimelineReminders(String(model.id))
      bumpNextActionTick()
      notify({ title: t('app.reminders.messages.snoozed'), variant: 'success' })
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.snooze'))) return
      const info = getFriendlyErrorInfo(err, t('app.reminders.errors.snooze'), t)
      setRemindersError(info)
      notify({
        title: [info.title, info.detail].filter(Boolean).join(' — ') || info.title,
        variant: 'error',
      })
    } finally {
      setReminderBusy((prev) => (prev === id ? null : prev))
    }
  }, [model?.id, planLimitModal, t, notify, loadTimelineReminders, bumpNextActionTick])

  const handleDelete = useCallback(async () => {
    if (!model?.id) return
    if (!window.confirm(t('app.candidate_card.confirm.delete'))) return
    try {
      await api.delete(`/candidates/${model.id}`)
      notify({ title: t('app.candidate_card.messages.deleted'), variant: 'success' })
      nav(CRM_APP_PATHS.candidates, { state: { returnFromCandidateId: model?.id } })
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.candidate_card.messages.delete_failed'))) {
        const errorMessage = formatErrorForDisplay(err, { fallback: t('app.candidate_card.messages.delete_failed') })
        notify({ title: errorMessage, variant: 'error' })
      }
    }
  }, [model?.id, nav, planLimitModal, t, notify])

  const handleGenerateShortId = useCallback(async () => {
    if (!model?.id) return
    try {
      const { data } = await api.patch(`/candidates/${model.id}`, { extra: {} })
      setModel((m) => normalizeCandidate(data, m || model))
      setSavedOk(true)
      setTimeout(() => setSavedOk(false), 2000)
      notify({ title: t('app.candidate_card.messages.short_id_generated'), variant: 'success' })
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.candidate_card.messages.short_id_failed'))) {
        notify({ title: t('app.candidate_card.messages.short_id_failed'), variant: 'error' })
      }
    }
  }, [model, planLimitModal, t, notify])

  const isMasked = model?.masked === true
  // Use the same role source as the rest of the app (memberships[].role can override me.role).
  const canRequestPipelineOverride = useMemo(() => {
    if (!model?.id) return false
    if (isClientTenant) return false
    return can('candidates.manage') || can('documents.manage') || can('candidates.pipeline')
  }, [model?.id, isClientTenant, can])

  const canApprovePipelineOverride = useMemo(() => {
    if (!model?.id || isMasked) return false
    if (isClientTenant) return false
    return permissionsRole === 'supervisor' || permissionsRole === 'administrator'
  }, [model?.id, isMasked, isClientTenant, permissionsRole])

  const bumpPipelineAndDocsRefresh = useCallback(() => {
    setDocsSummaryRefreshTrigger((x) => x + 1)
  }, [])

  const handleCreatePipelineOverride = useCallback(
    async (input: { doc_type_code: string; reason: string; requested_scope: 'pipeline' | 'both' }) => {
      if (!model?.id) return
      setPipelineOverrideBusy(true)
      try {
        await createCandidatePipelineOverride(String(model.id), input)
        notify({
          title: t('app.candidate_card.pipeline_override.requested'),
          variant: 'success',
        })
        bumpPipelineAndDocsRefresh()
      } catch (err: any) {
        if (!planLimitModal?.showPlanLimitIfNeeded(err, t('common.errors.request_failed'))) {
          notify({
            title: formatErrorForDisplay(err, { fallback: t('common.errors.request_failed') }),
            variant: 'error',
          })
        }
      } finally {
        setPipelineOverrideBusy(false)
      }
    },
    [model?.id, notify, planLimitModal, t, bumpPipelineAndDocsRefresh],
  )

  const handleApprovePipelineOverride = useCallback(
    async (overrideId: string, granted: 'pipeline' | 'both') => {
      if (!model?.id) return
      setPipelineOverrideBusy(true)
      try {
        await approveCandidatePipelineOverride(String(model.id), overrideId, { granted_scope: granted })
        notify({
          title: t('app.candidate_card.pipeline_override.approved'),
          variant: 'success',
        })
        bumpPipelineAndDocsRefresh()
      } catch (err: any) {
        if (!planLimitModal?.showPlanLimitIfNeeded(err, t('common.errors.request_failed'))) {
          notify({
            title: formatErrorForDisplay(err, { fallback: t('common.errors.request_failed') }),
            variant: 'error',
          })
        }
      } finally {
        setPipelineOverrideBusy(false)
      }
    },
    [model?.id, notify, planLimitModal, t, bumpPipelineAndDocsRefresh],
  )

  const handleRejectPipelineOverride = useCallback(
    async (overrideId: string) => {
      if (!model?.id) return
      setPipelineOverrideBusy(true)
      try {
        await rejectCandidatePipelineOverride(String(model.id), overrideId, {})
        notify({
          title: t('app.candidate_card.pipeline_override.rejected'),
          variant: 'success',
        })
        bumpPipelineAndDocsRefresh()
      } catch (err: any) {
        if (!planLimitModal?.showPlanLimitIfNeeded(err, t('common.errors.request_failed'))) {
          notify({
            title: formatErrorForDisplay(err, { fallback: t('common.errors.request_failed') }),
            variant: 'error',
          })
        }
      } finally {
        setPipelineOverrideBusy(false)
      }
    },
    [model?.id, notify, planLimitModal, t, bumpPipelineAndDocsRefresh],
  )

  const candidateDataReadOnly = !isNew && candidateEditPhase !== 'editing'
  const handoffActiveBlock = Boolean(handoffStatus?.pending || handoffStatus?.accepted)
  const handoffReadonlySummary = useMemo(() => {
    if (!handoffActiveBlock || handoffLoading) return null
    const pending = handoffStatus?.pending
    const accepted = handoffStatus?.accepted
    const row = pending || accepted
    if (!row) return null
    const dest = String(row.destination || 'client_portal').toLowerCase() === 'internal_hr' ? 'internal_hr' : 'client'
    const dateRaw = row.requested_at
    const date = dateRaw ? formatDateTime(dateRaw, locale) || dateRaw : '—'
    if (pending) {
      return dest === 'internal_hr'
        ? t('app.candidate_card.handoff.readonly_pending_internal', { values: { date } })
        : t('app.candidate_card.handoff.readonly_pending_client', { values: { date } })
    }
    return dest === 'internal_hr'
      ? t('app.candidate_card.handoff.readonly_accepted_internal', { values: { date } })
      : t('app.candidate_card.handoff.readonly_accepted_client', { values: { date } })
  }, [handoffActiveBlock, handoffLoading, handoffStatus, locale, t])

  const handoffPrimaryActionLabel = useMemo(() => {
    if (!primaryHandoffDestination) return t('app.candidate_card.handoff.transfer_btn')
    return primaryHandoffDestination === 'internal_hr'
      ? t('app.candidate_card.handoff.transfer_internal_hr_btn')
      : t('app.candidate_card.handoff.transfer_client_btn')
  }, [primaryHandoffDestination, t])

  // Pipedrive-style indicator: show how long candidate is in current stage.
  // Best-effort: uses stage history and loads quietly (does not block UI).
  useEffect(() => {
    if (!model?.id) {
      setStageSinceAt(null)
      return
    }
    void loadStageHistoryQuiet(String(model.id))
  }, [loadStageHistoryQuiet, model?.id, model?.stage])

  useEffect(() => {
    if (isNew || !model?.id) return
    void loadTimelineReminders(String(model.id))
    void loadStageHistoryForTimeline(String(model.id))
  }, [isNew, model?.id, model?.stage, loadTimelineReminders, loadStageHistoryForTimeline])

  const openDocsDrawer = useCallback((typeCode?: string) => {
    setDocsDrawerType(typeCode)
    setDocsDrawerOpen(true)
  }, [])

  const closeDocsDrawer = useCallback(() => {
    setDocsDrawerOpen(false)
    // Next docs summary poll should reflect any changes done in the drawer.
    setDocsSummaryRefreshTrigger((x) => x + 1)
    const currentId = modelRef.current?.id
    if (currentId && location.pathname.includes('/documents')) {
      nav(`${CRM_APP_PATHS.candidates}/${currentId}`)
    }
  }, [location.pathname, nav])

  // If user navigated directly to `/app/candidates/:id/documents`,
  // open the documents drawer automatically.
  useEffect(() => {
    if (isMasked) return
    if (!model?.id) return
    if (!location.pathname.includes('/documents')) return

    const sp = new URLSearchParams(location.search || '')
    const type = sp.get('type') || undefined
    openDocsDrawer(type)
  }, [isMasked, location.pathname, location.search, model?.id, openDocsDrawer])

  useEffect(() => {
    if (!model?.id || model.masked === true) {
      setPipelineOverrides([])
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const items = await listCandidatePipelineOverrides(String(model.id))
        if (!cancelled) setPipelineOverrides(items)
      } catch (err: unknown) {
        if (!cancelled) {
          void planLimitModal?.showPlanLimitIfNeeded(err, t('common.errors.request_failed'))
          setPipelineOverrides([])
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [model?.id, model?.masked, docsSummaryRefreshTrigger, planLimitModal, t])

  const {
    stageJourneyStagesPipeline,
    stageJourneyStagesDisplay,
    stageOutcomeStages,
    stageJourneyDisplayStage,
    stageJourneyOutcomeStage,
    stageJourneySignals,
  } = useMemo(() => {
    const codesForDisplay = profileFunnelStages.length > 0 ? profileFunnelStages.map((s) => s.code) : stageOptions
    const codesForPipeline = isClientTenant
      ? stageOptions
      : profileFunnelStages.length > 0
        ? profileFunnelStages.map((s) => s.code)
        : profileStageCodes

    const uniqDisplay = Array.from(new Set((codesForDisplay || []).filter(Boolean)))
    const journeyOrder = [
      'processing_by_client',
      'docs_submitted_permit',
      'ready_for_handoff',
      'ready_for_hr',
    ]
    const allowedJourneyStages = new Set(journeyOrder)
    const journeyOrderRank = new Map(journeyOrder.map((code, idx) => [code, idx] as const))

    function buildOrderedStages(
      codesInput: string[],
      narrowForClientFacingStrip: boolean,
      stripPostRecruitment: boolean,
    ) {
      const uniq = Array.from(new Set((codesInput || []).filter(Boolean)))
      const main: Array<{ code: string; label: string }> = []
      uniq.forEach((raw) => {
        const code = String(raw)
        const label = stageLabelIntl(code)
        const canonical = canonicalStageKey(code, label) || ''

        if (canonical === 'no_answer') return
        if (canonical === 'questionnaire_submitted') return
        if (canonical === 'handoff_returned' || canonical === 'rejected' || canonical === 'declined') {
          return
        }
        if (stripPostRecruitment && isPostRecruitmentStageCode(canonical)) return
        if (narrowForClientFacingStrip && isClientTenant && !allowedJourneyStages.has(canonical)) return
        main.push({ code, label })
      })
      if (narrowForClientFacingStrip && isClientTenant) {
        return [...main].sort((a, b) => {
          const aCanonical = canonicalStageKey(a.code, a.label) || ''
          const bCanonical = canonicalStageKey(b.code, b.label) || ''
          const aRank = journeyOrderRank.get(aCanonical)
          const bRank = journeyOrderRank.get(bCanonical)
          if (aRank === undefined && bRank === undefined) return 0
          if (aRank === undefined) return 1
          if (bRank === undefined) return -1
          return aRank - bRank
        })
      }
      return main
    }

    const stripRecruitmentBoundary = !isClientTenant
    const orderedPipeline = buildOrderedStages(codesForPipeline, false, stripRecruitmentBoundary)
    const orderedDisplay = buildOrderedStages(codesForDisplay, true, stripRecruitmentBoundary)

    const currentCode = String(model?.stage || '')
    const currentCanonical = canonicalStageKey(currentCode, null) || ''
    const journeySignals: Array<{ key: string; label: string }> = []

    if (currentCanonical === 'no_answer') {
      journeySignals.push({ key: 'no_answer', label: translateStageLabel(t, 'no_answer', 'no_answer') })
    }
    const intakeSubmitted = Boolean((model as any)?.intake_submitted_at || (model as any)?.intake_status === 'submitted')
    if (currentCanonical === 'questionnaire_submitted' || intakeSubmitted) {
      journeySignals.push({ key: 'questionnaire_submitted', label: translateStageLabel(t, 'questionnaire_submitted', 'questionnaire_submitted') })
    }

    let displayStage = currentCode || null
    if (currentCanonical === 'no_answer' || currentCanonical === 'questionnaire_submitted') {
      const contacted =
        uniqDisplay.find((c) => (canonicalStageKey(String(c), null) || '') === 'contacted') || 'contacted'
      displayStage = String(contacted)
    }

    const outcomeStage = null

    return {
      stageJourneyStagesPipeline: orderedPipeline,
      stageJourneyStagesDisplay: orderedDisplay,
      stageOutcomeStages: [],
      stageJourneyDisplayStage: displayStage,
      stageJourneyOutcomeStage: outcomeStage,
      stageJourneySignals: journeySignals,
    }
  }, [
    profileFunnelStages,
    profileStageCodes,
    stageLabelIntl,
    stageOptions,
    model?.stage,
    (model as any)?.intake_status,
    (model as any)?.intake_submitted_at,
    t,
    isClientTenant,
  ])

  const operationallyTerminal = useMemo(
    () =>
      isCandidateOperationallyTerminal({
        stage: model?.stage,
        row_status: model?.row_status,
        status: model?.status,
      }),
    [model?.stage, model?.row_status, model?.status],
  )

  /** Align doc policy with journey display (e.g. no_answer maps to contacted for gating). */
  const effectiveStageForDocPolicy = useMemo(() => {
    const stored =
      canonicalStageKey(model?.stage ?? null, null) || String(model?.stage || '').trim().toLowerCase() || null
    if (
      isCandidateOperationallyTerminal({
        stage: model?.stage,
        row_status: model?.row_status,
        status: model?.status,
      })
    )
      return stored
    return String(stageJourneyDisplayStage || model?.stage || '').trim() || null
  }, [stageJourneyDisplayStage, model?.stage, model?.row_status, model?.status])

  const pipelineRelaxedTypes = useMemo(
    () => pipelineRelaxedTypesFromOverrides(pipelineOverrides),
    [pipelineOverrides],
  )

  const effectiveDocsBlockersForPipeline = useMemo(
    () => relaxDocBlockers(docsBlockers, pipelineRelaxedTypes),
    [docsBlockers, pipelineRelaxedTypes],
  )

  const docsIssuesPresentValue = useMemo(
    () => docsIssuesPresent(docsBlockers, docsBlockersLoading),
    [docsBlockers, docsBlockersLoading],
  )

  const docPipelineResolved = useMemo(
    () =>
      docsPipelineBlocksForwardResolved(
        effectiveStageForDocPolicy,
        effectiveDocsBlockersForPipeline,
        docsBlockersLoading,
        hiringGatesRuntime,
      ),
    [effectiveStageForDocPolicy, effectiveDocsBlockersForPipeline, docsBlockersLoading, hiringGatesRuntime],
  )
  const docsPipelineBlockingValue = docPipelineResolved.hard
  const docsPipelineSoftWarnValue = docPipelineResolved.softWarnOnly

  /** Stored stage only — do not use journey display remap (e.g. no_answer → contacted). */
  const vacancyPipelineBlockingValue = useMemo(
    () => vacancyPipelineBlocksForward(model?.stage ?? null, model?.vacancy_id ?? null, hiringGatesRuntime),
    [model?.stage, model?.vacancy_id, hiringGatesRuntime],
  )

  const contactAttemptPipelineBlockingValue = useMemo(
    () =>
      contactAttemptPipelineBlocksForward(
        model?.stage ?? null,
        model?.contact_policy_enabled === true,
        Number(model?.contact_attempt_count ?? 0),
        hiringGatesRuntime,
      ),
    [model?.stage, model?.contact_policy_enabled, model?.contact_attempt_count, hiringGatesRuntime],
  )

  /**
   * While contact policy is on and the stored stage is still in the contact-attempt gate (e.g. `new`),
   * show attempts (+ RODO) at the top of the rail — same scope as the pipeline gate, not after docs/notes.
   * After leaving those stages (contacted, declined, etc.), the block is omitted.
   */
  const showContactAttemptsPriorityRail = useMemo(() => {
    if (!model?.id || isMasked || isNew || operationallyTerminal) return false
    if (model.contact_policy_enabled !== true) return false
    const raw = String(model?.stage ?? '').trim()
    if (!raw) return false
    const code = canonicalStageKey(raw, null) || raw.toLowerCase()
    return hiringGatesRuntime.contactAttemptGateStages.has(code)
  }, [
    model?.id,
    model?.stage,
    model?.contact_policy_enabled,
    isMasked,
    isNew,
    hiringGatesRuntime,
    operationallyTerminal,
  ])

  /** One highlighted block in the work rail — overdue reminder first, then same order as forward stage gates. */
  const railPrimaryFocus = useMemo(() => {
    if (!model?.id || isNew) return null
    if (operationallyTerminal) return null
    const now = Date.now()
    if (isMasked) {
      if (railHasUrgentReminder(reminders, now)) return 'next_action'
      if (vacancyPipelineBlockingValue) return 'vacancy'
      return null
    }
    return resolveRailPrimaryFocus({
      hasUrgentReminder: railHasUrgentReminder(reminders, now),
      docsHardBlocking: docsPipelineBlockingValue,
      docsSoftOnly: Boolean(docsPipelineSoftWarnValue && !docsPipelineBlockingValue),
      contactAttemptBlocking: contactAttemptPipelineBlockingValue,
      contactPriorityRailVisible: showContactAttemptsPriorityRail && !isMasked,
      vacancyBlocking: vacancyPipelineBlockingValue,
    })
  }, [
    model?.id,
    isNew,
    isMasked,
    reminders,
    docsPipelineBlockingValue,
    docsPipelineSoftWarnValue,
    contactAttemptPipelineBlockingValue,
    showContactAttemptsPriorityRail,
    vacancyPipelineBlockingValue,
    operationallyTerminal,
  ])

  /**
   * Waiver rail only when documents can block the pipeline or there is override state to show.
   * At early stages (e.g. New) recruiters do not need an empty waiver panel.
   */
  const showPipelineWaiverSection = useMemo(() => {
    if (!model?.id || isClientTenant) return false
    if (pipelineOverrides.length > 0) return true
    if (!docsPipelineBlockingValue && !docsPipelineSoftWarnValue) return false
    if (!can('candidates.pipeline')) return false
    return (
      canApprovePipelineOverride || can('candidates.manage') || can('documents.manage')
    )
  }, [
    model?.id,
    isClientTenant,
    pipelineOverrides.length,
    canApprovePipelineOverride,
    can,
    docsPipelineBlockingValue,
    docsPipelineSoftWarnValue,
  ])

  const pipelineWaiverReadOnlyCard = useMemo(
    () =>
      operationallyTerminal ||
      (showPipelineWaiverSection &&
        !canRequestPipelineOverride &&
        (can('candidates.manage') || can('documents.manage')) &&
        model?.can_edit === false),
    [
      operationallyTerminal,
      showPipelineWaiverSection,
      canRequestPipelineOverride,
      can,
      model?.can_edit,
    ],
  )

  /** Canonical stage for operational hints (next action) — prefer stored stage when pipeline is finished. */
  const canonicalStageForOps = useMemo(() => {
    const term = isCandidateOperationallyTerminal({
      stage: model?.stage,
      row_status: model?.row_status,
      status: model?.status,
    })
    const stored =
      canonicalStageKey(model?.stage ?? null, null) || String(model?.stage || '').trim().toLowerCase() || ''
    if (term) {
      if (stored && isPipelineCompletedCanonicalStage(stored)) return stored
      const rs = String(model?.row_status ?? model?.status ?? '').trim().toLowerCase()
      if (rs && isPipelineCompletedCanonicalStage(rs)) return rs
      return stored || rs || null
    }
    if (stored && isPipelineCompletedCanonicalStage(stored)) return stored
    const raw = String(stageJourneyDisplayStage || model?.stage || '').trim()
    if (!raw) return null
    return canonicalStageKey(raw, null) || raw.toLowerCase()
  }, [stageJourneyDisplayStage, model?.stage, model?.row_status, model?.status])

  const employerDataMissingForHint = useMemo(() => {
    const stage = canonicalStageForOps || ''
    if (
      isCandidateOperationallyTerminal({
        stage: model?.stage,
        row_status: model?.row_status,
        status: model?.status,
      }) ||
      isPipelineCompletedCanonicalStage(stage)
    )
      return false
    const companyId = String(model?.company_id || '').trim()
    const vacancyId = String(model?.vacancy_id || '').trim()
    return !companyId && !vacancyId
  }, [canonicalStageForOps, model?.company_id, model?.vacancy_id, model?.stage, model?.row_status, model?.status])

  const missingDataHints = useMemo(() => {
    if (!model?.id || isMasked) return []
    const hints: Array<{ id: string; label: string; ctaLabel?: string; onClick?: () => void; score: number }> = []
    const firstName = String(model?.first_name || '').trim()
    const lastName = String(model?.last_name || '').trim()
    const email = String(model?.email || '').trim()
    const phone = String(model?.phone || '').trim()
    const companyId = String(model?.company_id || '').trim()
    const vacancyId = String(model?.vacancy_id || '').trim()
    const citizenship = String((extra as any)?.citizenship || '').trim()
    const languagesValue = (extra as any)?.languages
    const hasLanguages =
      Array.isArray(model?.languages)
        ? model.languages.length > 0
        : Array.isArray(languagesValue)
          ? languagesValue.length > 0
          : false
    const stage = String(canonicalStageForOps || '').trim().toLowerCase()
    const isEarlyStage = !stage || ['new', 'no_answer', 'contacted', 'questionnaire_submitted'].includes(stage)
    const isDocsStage = ['docs_wait', 'docs_got', 'ready_for_handoff'].includes(stage)

    if (!firstName || !lastName) {
      hints.push({
        id: 'name',
        label: t('app.candidate_card.next_action.missing_data.name', {
          defaultValue: 'Candidate first and last name',
        }),
        ctaLabel: t('app.candidate_card.next_action.missing_data.open_profile', {
          defaultValue: 'Open profile',
        }),
        onClick: scrollToCandidateData,
        score: scoreMissingHintForStage('name', canonicalStageForOps),
      })
    }
    if (!email && !phone) {
      hints.push({
        id: 'contact',
        label: t('app.candidate_card.next_action.missing_data.contact', {
          defaultValue: 'At least one contact channel (phone or email)',
        }),
        ctaLabel: t('app.candidate_card.next_action.missing_data.open_profile', {
          defaultValue: 'Open profile',
        }),
        onClick: scrollToCandidateData,
        score: scoreMissingHintForStage('contact', canonicalStageForOps),
      })
    }
    if (!companyId && !vacancyId) {
      hints.push({
        id: 'employer',
        label: t('app.candidate_card.next_action.missing_data.employer', {
          defaultValue: 'Employer context (company or vacancy)',
        }),
        ctaLabel: t('app.candidate_card.next_action.open_employer_fields', {
          defaultValue: 'Open employer fields',
        }),
        onClick: scrollToEmployerData,
        score: scoreMissingHintForStage('employer', canonicalStageForOps),
      })
    }
    // Documents and relocation flows need citizenship to suggest the right checklist.
    if (!citizenship && isDocsStage) {
      hints.push({
        id: 'citizenship',
        label: t('app.candidate_card.next_action.missing_data.citizenship', {
          defaultValue: 'Citizenship / residency context',
        }),
        ctaLabel: t('app.candidate_card.next_action.missing_data.open_personal', {
          defaultValue: 'Open personal',
        }),
        onClick: scrollToPersonalData,
        score: scoreMissingHintForStage('citizenship', canonicalStageForOps),
      })
    }
    if (!hasLanguages && (isEarlyStage || isDocsStage)) {
      hints.push({
        id: 'languages',
        label: t('app.candidate_card.next_action.missing_data.languages', {
          defaultValue: 'Languages',
        }),
        ctaLabel: t('app.candidate_card.next_action.missing_data.open_personal', {
          defaultValue: 'Open personal',
        }),
        onClick: scrollToPersonalData,
        score: scoreMissingHintForStage('languages', canonicalStageForOps),
      })
    }
    // Keep UI lightweight: only the two most relevant hints for current stage.
    return hints
      .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
      .slice(0, 2)
      .map(({ score: _score, ...rest }) => rest)
  }, [
    model?.id,
    model?.first_name,
    model?.last_name,
    model?.email,
    model?.phone,
    model?.company_id,
    model?.vacancy_id,
    model?.languages,
    extra,
    canonicalStageForOps,
    isMasked,
    scrollToCandidateData,
    scrollToEmployerData,
    scrollToPersonalData,
    t,
    scoreMissingHintForStage,
  ])

  /** Same ordering as `CandidateStageDecisionPanel` pipeline list — for resolved operational hints. */
  const nextPipelineStageCodeForOps = useMemo(() => {
    const main = stageJourneyStagesPipeline || []
    const outcomes = stageOutcomeStages || []
    const pipelineSteps = [...main, ...outcomes]
    const candidates = [model?.stage, stageJourneyDisplayStage, stageJourneyOutcomeStage].filter(Boolean).map(String)
    const currentCode =
      candidates.find((c) => pipelineSteps.some((s) => s.code === c)) ?? candidates[0] ?? null
    if (!currentCode) return null
    const idx = pipelineSteps.findIndex((s) => s.code === currentCode)
    if (idx < 0 || idx >= pipelineSteps.length - 1) return null
    return pipelineSteps[idx + 1]?.code ?? null
  }, [stageJourneyStagesPipeline, stageOutcomeStages, stageJourneyDisplayStage, stageJourneyOutcomeStage, model?.stage])

  const pipelineWaiverBadgeCounts = useMemo(() => {
    let pending = 0
    let approved = 0
    for (const o of pipelineOverrides) {
      const s = String(o.status || '').toLowerCase()
      if (s === 'pending') pending += 1
      else if (s === 'approved') approved += 1
    }
    return { pending, approved }
  }, [pipelineOverrides])

  const completedStageCodes = useMemo(() => {
    const set = new Set<string>()
    stageHistory.forEach((h) => {
      if (h.from_code) set.add(String(h.from_code))
      if (h.to_code) set.add(String(h.to_code))
    })
    return set
  }, [stageHistory])

  const handleStageJourneyChange = useCallback(async (nextStage: string) => {
    // Documents + data gates: blockers stop forward movement in the current journey order.
    if (Array.isArray(stageJourneyStagesPipeline)) {
      const steps = [...(stageJourneyStagesPipeline || []), ...(stageOutcomeStages || [])]
      const curCode = stageJourneyDisplayStage || model?.stage
      const curIdx = steps.findIndex((s) => s.code === curCode)
      const nextIdx = steps.findIndex((s) => s.code === nextStage)
      const isForward = curIdx >= 0 && nextIdx > curIdx
      if (isForward) {
        if (docsPipelineBlockingValue) {
          const firstMissing =
            effectiveDocsBlockersForPipeline.missing[0] ||
            effectiveDocsBlockersForPipeline.problematic[0] ||
            effectiveDocsBlockersForPipeline.inProgress[0]
          notify({
            title: t('app.candidate_card.stage_blocked_by_docs.title'),
            description: firstMissing
              ? t('app.candidate_card.stage_blocked_by_docs.missing_type_detail', { values: { label: firstMissing } })
              : t('app.candidate_card.stage_blocked_by_docs.description_generic'),
            variant: 'info',
          })
          return
        }
        if (contactAttemptPipelineBlockingValue) {
          notify({
            title: t('app.candidate_card.stage_blocked_by_contact_attempt.title'),
            description: t('app.candidate_card.stage_blocked_by_contact_attempt.description'),
            variant: 'info',
          })
          return
        }
        if (vacancyPipelineBlockingValue) {
          notify({
            title: t('app.candidate_card.stage_blocked_by_vacancy.title'),
            description: t('app.candidate_card.stage_blocked_by_vacancy.description'),
            variant: 'info',
          })
          return
        }
      }
    }

    if (!model?.stage) {
      await onStageChangePersist(nextStage, model?.status_reason || [])
      setModel((m) => (m ? { ...m, stage: nextStage } : m))
      return
    }
    if (nextStage === model.stage) return
    await onStageChangePersist(nextStage, model?.status_reason || [])
    setModel((m) => (m ? { ...m, stage: nextStage } : m))
  }, [
    model?.stage,
    model?.status_reason,
    model?.id,
    onStageChangePersist,
    docsPipelineBlockingValue,
    vacancyPipelineBlockingValue,
    contactAttemptPipelineBlockingValue,
    effectiveDocsBlockersForPipeline.missing,
    effectiveDocsBlockersForPipeline.problematic,
    effectiveDocsBlockersForPipeline.inProgress,
    stageJourneyStagesPipeline,
    stageOutcomeStages,
    stageJourneyDisplayStage,
    notify,
    t,
  ])

  /** Same forward-move gates as the journey panel, applied to the stage dropdown in basic info. */
  const persistStageWithClientGates = useCallback(
    async (nextStage: string, statusReason: string[]) => {
      if (!model?.id) return
      const revertBasicStageUi = async () => {
        try {
          const refreshed = await fetchCandidate(String(model.id), model)
          setModel(refreshed)
        } catch {
          /* ignore */
        }
      }
      if (Array.isArray(stageJourneyStagesPipeline) && stageJourneyStagesPipeline.length > 0) {
        const steps = [...(stageJourneyStagesPipeline || []), ...(stageOutcomeStages || [])]
        const curCode = model?.stage
        const curIdx = steps.findIndex((s) => s.code === curCode)
        const nextIdx = steps.findIndex((s) => s.code === nextStage)
        const isForward = curIdx >= 0 && nextIdx > curIdx
        if (isForward) {
          if (docsPipelineBlockingValue) {
            const firstMissing =
              effectiveDocsBlockersForPipeline.missing[0] ||
              effectiveDocsBlockersForPipeline.problematic[0] ||
              effectiveDocsBlockersForPipeline.inProgress[0]
            notify({
              title: t('app.candidate_card.stage_blocked_by_docs.title'),
              description: firstMissing
                ? t('app.candidate_card.stage_blocked_by_docs.missing_type_detail', { values: { label: firstMissing } })
                : t('app.candidate_card.stage_blocked_by_docs.description_generic'),
              variant: 'info',
            })
            await revertBasicStageUi()
            return
          }
          if (contactAttemptPipelineBlockingValue) {
            notify({
              title: t('app.candidate_card.stage_blocked_by_contact_attempt.title'),
              description: t('app.candidate_card.stage_blocked_by_contact_attempt.description'),
              variant: 'info',
            })
            await revertBasicStageUi()
            return
          }
          if (vacancyPipelineBlockingValue) {
            notify({
              title: t('app.candidate_card.stage_blocked_by_vacancy.title'),
              description: t('app.candidate_card.stage_blocked_by_vacancy.description'),
              variant: 'info',
            })
            await revertBasicStageUi()
            return
          }
        }
      }
      await onStageChangePersist(nextStage, statusReason)
    },
    [
      model?.id,
      model?.stage,
      model,
      stageJourneyStagesPipeline,
      stageOutcomeStages,
      docsPipelineBlockingValue,
      contactAttemptPipelineBlockingValue,
      vacancyPipelineBlockingValue,
      effectiveDocsBlockersForPipeline.missing,
      effectiveDocsBlockersForPipeline.problematic,
      effectiveDocsBlockersForPipeline.inProgress,
      onStageChangePersist,
      fetchCandidate,
      notify,
      t,
    ],
  )

  if (loading || !model) {
    return <div className="h-full w-full text-slate-500">{t('common.loading')}</div>
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-1 flex-col gap-0">
      <CandidateHeader
        candidate={model}
        isNew={isNew}
        isMasked={isMasked}
        canEdit={model.can_edit !== false}
        saving={saving}
        canDeleteDirect={canDeleteDirect}
        canRequestDelete={canRequestDelete}
        deleteRequestLoading={deleteRequestLoading}
        deleteRequestMessage={deleteRequestMessage}
        deleteRequestError={deleteRequestError}
        savedOk={savedOk}
        headerExpanded={headerExpanded}
        onHeaderExpandedChange={setHeaderExpanded}
        onSave={save}
        onDelete={handleDelete}
        onEditToggle={toggleCandidateEditMode}
        editMode={candidateEditPhase !== 'idle'}
        onOpenHandoff={
          showAgencyHandoffHeader && !handoffActiveBlock ? () => setHandoffModalOpen(true) : undefined
        }
        handoffReadonlyText={showAgencyHandoffHeader ? handoffReadonlySummary : null}
        handoffDisabled={handoffLoading}
        handoffLabel={handoffPrimaryActionLabel}
        onDeleteRequest={handleDeleteRequest}
        onCancel={() => nav(originPath, { state: { returnFromCandidateId: model?.id } })}
        backPath={originPath}
        backLabel={
          originPath.startsWith(CRM_APP_PATHS.procesowani)
            ? t('app.candidate_card.header.back_to_procesowani')
            : undefined
        }
        onFavoriteToggle={handleFavoriteToggle}
        candidateProfile={candidateProfile}
        profileLoading={profileLoading}
        stageSinceAt={stageSinceAt}
        pipelineWaiverPendingCount={pipelineWaiverBadgeCounts.pending}
        pipelineWaiverApprovedCount={pipelineWaiverBadgeCounts.approved}
        onOpenActivity={!isNew && model?.id ? () => setActivityModalOpen(true) : undefined}
        nextAction={nextActionDto}
        nextActionLoading={nextActionLoading}
        nextActionError={nextActionError}
        focusContent={!isNew && model?.id ? (
          <div className="grid gap-2">
            <CandidateStageDecisionPanel
              locale={locale}
              stageSinceAt={stageSinceAt}
              stageJourneyStages={stageJourneyStagesPipeline}
              journeyPanelStages={stageJourneyStagesDisplay}
              stageOutcomeStages={stageOutcomeStages}
              stageJourneyDisplayStage={stageJourneyDisplayStage}
              stageJourneyOutcomeStage={stageJourneyOutcomeStage}
              stageJourneySignals={stageJourneySignals}
              completedStageCodes={completedStageCodes}
              currentStageCode={model.stage}
              candidateRowStatus={model.row_status}
              candidateStatus={model.status}
              stageLabelIntl={stageLabelIntl}
              docsBlockers={docsBlockers}
              docsPipelineBlocking={docsPipelineBlockingValue}
              docsPipelineSoftWarn={docsPipelineSoftWarnValue}
              vacancyPipelineBlocking={vacancyPipelineBlockingValue}
              contactAttemptPipelineBlocking={contactAttemptPipelineBlockingValue}
              canEdit={model.can_edit !== false}
              onMoveStage={handleStageJourneyChange}
              onOpenContactAttempts={() => setContactAttemptOpenSignal((n) => n + 1)}
            />
          </div>
        ) : null}
      />

      <div className="border-b border-slate-200 bg-slate-50/90 px-3 py-2">
        <PageBreadcrumb />
      </div>

      <div className="card p-3">
        <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(280px,3fr)] lg:items-start lg:justify-between">
            <div className="space-y-4 lg:pr-6">
                  {/* Основные данные */}
                  {!isMasked && (
                    <CandidateBasicSection
                      candidate={model}
                      extra={extra}
                      isNew={isNew}
                      locale={locale}
                      basicRef={basicRef}
                      stageOptions={stageOptions}
                      profileStageCodes={profileStageCodes}
                      meta={meta ?? undefined}
                      dialCodes={dialCodes}
                      managers={managers}
                      preferredContactOptions={preferredContactOptions}
                      selectTexts={selectTexts}
                      createdAtDisplay={createdAtDisplay}
                      isMetaLead={isMetaLead}
                      onModelChange={(updater) => setModel((prev) => (prev ? updater(prev) : prev))}
                      onExtraChange={setExtra}
                      onPhoneInputChange={handlePhoneInputChange}
                      onGenerateShortId={handleGenerateShortId}
                      candidateProfile={candidateProfile}
                      stageLabelIntl={stageLabelIntl}
                      candidateDataReadOnly={candidateDataReadOnly}
                      onStageChangePersist={persistStageWithClientGates}
                      embedded
                    />
                  )}

                  {/* Персональные данные */}
                  {!isMasked && (
                    <CandidatePersonalSection
                      candidate={model}
                      extra={extra}
                      personalRef={personalRef}
                      countries={countries}
                      languages={languages}
                      selectTexts={selectTexts}
                      onModelChange={(updater) => setModel((prev) => (prev ? updater(prev) : prev))}
                      onExtraChange={setExtra}
                      onAddressFieldChange={setAddressField}
                      candidateProfile={candidateProfile}
                      candidateDataReadOnly={candidateDataReadOnly}
                      embedded
                    />
                  )}

                  {/* Статус и соответствие требованиям (на всю ширину) */}
                  <div className="space-y-4">
                    <CandidateStatusSection
                      extra={extra}
                      statusRef={statusRef}
                      polandBasisOptions={polandBasisOptions}
                      selectTexts={selectTexts}
                      onExtraChange={setExtra}
                      candidateProfile={candidateProfile}
                      candidateDataReadOnly={candidateDataReadOnly}
                      embedded
                    />

                    <CandidateWorkforceTerminationSection extra={extra} />

                    <CandidateCustomFieldsSection
                      extra={extra}
                      customFieldsRef={customFieldsRef}
                      candidateProfile={candidateProfile}
                      selectTexts={selectTexts}
                      onExtraChange={setExtra}
                    />
                  </div>

                  {/* Опыт */}
                  <CandidateExperienceSection
                    extra={extra}
                    experienceRef={experienceRef}
                    experienceTotalDisplay={experienceTotalDisplay}
                    trailerTypeOptions={trailerTypeOptions}
                    routeTypeOptions={routeTypeOptions}
                    employmentHistory={employmentHistory}
                    employmentLoading={employmentLoading}
                    employmentError={employmentError}
                    selectTexts={selectTexts}
                    onExtraChange={setExtra}
                    onExperienceChange={handleExperienceChange}
                    onAddEmploymentRow={addEmploymentRow}
                    onUpdateEmploymentHistory={updateEmploymentHistory}
                    onRemoveEmploymentRow={removeEmploymentRow}
                    candidateProfile={candidateProfile}
                    candidateDataReadOnly={candidateDataReadOnly}
                    embedded
                  />

                  {/* Работодатель и вакансия */}
                  {!isMasked && (
                    <section
                      ref={employerRef}
                      id="section-employer"
                      className="group app-surface p-4 scroll-mt-24 transition-shadow hover:shadow-xl"
                    >
                      <div className="flex items-center gap-3">
                        <IconBuilding size={22} className="text-slate-600" />
                        <div>
                          <h2 className="text-lg font-semibold text-slate-900">
                            {t('app.candidate_card.sections.employer.title')}
                          </h2>
                          <p className="text-sm text-slate-500">
                            {t('app.candidate_card.sections.employer.description')}
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                        <label className="block md:col-span-2">
                          <div className="label">{t('app.candidate_card.fields.vacancy')}</div>
                          <SearchableSelect
                            options={vacancyOpts}
                            value={(model.vacancy_id as string) || ''}
                            onChange={async (v) => {
                              if (!v) {
                                setModel((m) => {
                                  if (!m) return m
                                  return {
                                    ...m,
                                    vacancy_id: null,
                                    vacancy_name: '',
                                    company_id: null,
                                    company_name: '',
                                  }
                                })
                                setCandidateProfile(null)
                                return
                              }
                              const opt = vacancyOpts.find((o) => o.value === v)
                              const company_id = opt?.extra?.company_id || null
                              const company_name = opt?.extra?.company_name || model.company_name || ''
                              const vacancy_label = opt?.label || ''
                              setModel((m) => {
                                if (!m) return m
                                return {
                                  ...m,
                                  vacancy_id: v as any,
                                  vacancy_name: vacancy_label,
                                  company_id,
                                  company_name: company_name || m.company_name || '',
                                }
                              })
                              // Загружаем профиль из новой вакансии
                              await loadProfileFromVacancy(v)
                            }}
                            placeholder={selectTexts.empty}
                            searchPlaceholder={selectTexts.search}
                            noResultsLabel={selectTexts.noResults}
                          />
                          <p className="mt-1 text-xs text-slate-500">
                            {t('app.candidate_card.messages.vacancy_hint')}
                          </p>
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
                  )}

                  {!isNew && model?.id && !isMasked ? (
                    <CandidateApplicationsSection
                      candidateId={String(model.id)}
                      locale={locale}
                      legacyVacancyId={model.vacancy_id ? String(model.vacancy_id) : null}
                    />
                  ) : null}

            </div>

          {/* Work panel (sticky): contact+RODO (gate stages) → next action → docs → notes → inbox → services → RODO if not above */}
          {!isNew && model?.id ? (
            <div
              className="flex w-full min-w-0 flex-col gap-4 overflow-hidden lg:sticky lg:top-4 lg:max-h-[calc(100vh-3.5rem)] lg:overflow-y-auto"
              data-candidate-control-rail
            >
              {showContactAttemptsPriorityRail && !isMasked ? (
                <RailPrimaryStepFrame active={railPrimaryFocus === 'contact_stack'}>
                  <div className="space-y-3">
                    <CandidateContactAttemptsSection
                      candidateId={String(model.id) as any}
                      refreshTrigger={rodoSentTrigger}
                      openRegisterSignal={contactAttemptOpenSignal}
                      onAttemptCreated={
                        model?.id ? () => void fetchCandidate(String(model.id), model) : undefined
                      }
                    />
                    <CandidateRodoSection
                      candidateId={String(model.id) as any}
                      onSent={() => setRodoSentTrigger((x) => x + 1)}
                      refreshTrigger={rodoSentTrigger}
                    />
                  </div>
                </RailPrimaryStepFrame>
              ) : null}

              <CandidateNextActionPanel
                candidateId={String(model.id)}
                reminders={reminders}
                remindersLoading={remindersLoading}
                remindersError={remindersError}
                reminderTitle={reminderTitle}
                reminderDueAt={reminderDueAt}
                reminderOffset={reminderOffset}
                reminderBusy={reminderBusy}
                docsIssuesPresent={docsIssuesPresentValue}
                docsPipelineBlocking={docsPipelineBlockingValue || docsPipelineSoftWarnValue}
                docsRequestTitle={docsNeedsVerification
                  ? t('app.candidate_card.next_action.docs_verify_title')
                  : t('app.candidate_card.next_action.docs_request_title')}
                docsRequestDueLabel={t('common.today')}
                docsBlockerKind={docsNeedsVerification ? 'review' : (docsNeedsRequest ? 'request' : null)}
                onDocsRequestCreate={handleDocsNextActionCreate}
                hideToggle
                hideRemindersList
                onReminderTitleChange={setReminderTitle}
                onReminderDueAtChange={setReminderDueAt}
                onReminderOffsetChange={setReminderOffset}
                onReminderCreate={handleCreateReminder}
                onReminderComplete={handleReminderComplete}
                onReminderSnooze={handleReminderSnooze}
                operationallyTerminal={operationallyTerminal}
                canonicalStageCode={canonicalStageForOps}
                nextPipelineStageCode={nextPipelineStageCodeForOps}
                employerDataMissing={employerDataMissingForHint}
                onOpenEmployerFields={scrollToEmployerData}
                missingDataHints={missingDataHints}
                vacancyPipelineBlocking={vacancyPipelineBlockingValue}
                contactAttemptPipelineBlocking={contactAttemptPipelineBlockingValue}
                primaryStepHighlight={
                  railPrimaryFocus === 'next_action' || railPrimaryFocus === 'vacancy'
                }
                documentsChecklistSibling
              />

              <CandidateDocsRailPanel
                candidateId={String(model.id)}
                ownerContext={docsOwnerContext}
                uploadBusy={false}
                onUpload={() => openDocsDrawer(undefined)}
                onOpenDocs={() => openDocsDrawer(undefined)}
                onLoadedBlockers={(b) => setDocsBlockers({ missing: b.missing, problematic: b.problematic, inProgress: b.inProgress })}
                onLoadingChange={setDocsBlockersLoading}
                refreshTrigger={docsSummaryRefreshTrigger}
                onSelectType={(typeCode) => openDocsDrawer(typeCode)}
                pollingEnabled={docsDrawerOpen}
                stageSummaryLabel={
                  model.stage ? stageLabelIntl(String(model.stage)) : null
                }
                docsPipelineBlocking={docsPipelineBlockingValue || docsPipelineSoftWarnValue}
                pipelineOverrides={pipelineOverrides}
                pipelineOverrideBusy={pipelineOverrideBusy}
                canRequestPipelineOverride={canRequestPipelineOverride}
                canApprovePipelineOverride={canApprovePipelineOverride}
                showPipelineWaiverSection={showPipelineWaiverSection}
                pipelineWaiverReadOnlyCard={pipelineWaiverReadOnlyCard}
                onCreatePipelineOverride={handleCreatePipelineOverride}
                onApprovePipelineOverride={handleApprovePipelineOverride}
                onRejectPipelineOverride={handleRejectPipelineOverride}
                primaryStepHighlight={railPrimaryFocus === 'docs'}
                blockersPresentation={operationallyTerminal ? 'historical' : 'operational'}
              />

              {!isMasked ? (
                <CandidateNotesRailSection
                  notes={notes}
                  notesLoading={notesLoading}
                  newNote={newNote}
                  noteSending={noteSending}
                  onNewNoteChange={setNewNote}
                  onAddNote={addNote}
                  onRefreshNotes={() => model?.id && fetchNotes(String(model.id))}
                />
              ) : null}

              <div className="rounded-2xl border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-semibold text-slate-800">
                    {t('app.candidate_card.control.inbox_title')}
                  </div>
                </div>
                <div className="mt-3">
                  <Link
                    to={buildInboxHubPath({ candidateId: String(model.id) })}
                    className="btn-secondary btn-sm w-full text-center"
                  >
                    {t('app.candidate_card.control.open_unified_inbox')}
                  </Link>
                </div>
              </div>

              {can('services.view') && !isMasked ? (
                <CandidateServicesSection
                  candidateId={String(model.id)}
                  canManage={can('services.orders.manage')}
                />
              ) : null}

              {!(showContactAttemptsPriorityRail && !isMasked) ? (
                <div className="space-y-3">
                  <CandidateRodoSection
                    candidateId={String(model.id) as any}
                    onSent={() => setRodoSentTrigger((x) => x + 1)}
                    refreshTrigger={rodoSentTrigger}
                  />
                </div>
              ) : null}
            </div>
          ) : null}
          </div>
          </div>
      </div>

      {!isNew && model?.id && handoffModalOpen ? (
        <div className="fixed inset-0 z-50 bg-black/50 p-4" onClick={() => setHandoffModalOpen(false)}>
          <div
            className="mx-auto mt-12 w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-semibold text-slate-900">{handoffPrimaryActionLabel}</div>
              <button type="button" className="btn-secondary btn-sm" onClick={() => setHandoffModalOpen(false)}>
                {t('common.actions.close')}
              </button>
            </div>

            {primaryHandoffDestination === 'internal_hr' ? (
              <>
                <p className="mt-3 text-sm text-slate-600">
                  {t('app.candidate_card.handoff.internal_hr_modal_hint')}
                </p>
                <div className="mt-4 flex items-center justify-end gap-2">
                  <button type="button" className="btn-secondary btn-sm" onClick={() => setHandoffModalOpen(false)}>
                    {t('common.actions.cancel')}
                  </button>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={handoffSubmitting}
                    onClick={() => void handleHandoffCreate()}
                  >
                    {handoffSubmitting ? t('common.saving') : handoffPrimaryActionLabel}
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="mt-3">
                  <label className="label">{t('app.candidate_card.handoff.client')}</label>
                  <select
                    className="input w-full"
                    value={handoffClientLinkId}
                    onChange={(e) => setHandoffClientLinkId(e.target.value)}
                  >
                    <option value="">—</option>
                    {handoffClientsForCompany.map((c) => (
                      <option key={c.link_id} value={c.link_id}>
                        {c.client_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="mt-4 flex items-center justify-end gap-2">
                  <button type="button" className="btn-secondary btn-sm" onClick={() => setHandoffModalOpen(false)}>
                    {t('common.actions.cancel')}
                  </button>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={!handoffClientLinkId || handoffSubmitting}
                    onClick={() => void handleHandoffCreate()}
                  >
                    {handoffSubmitting ? t('common.saving') : handoffPrimaryActionLabel}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}

      {!isNew && model?.id && activityModalOpen ? (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
          onClick={() => setActivityModalOpen(false)}
          role="presentation"
        >
          <div
            className="flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="candidate-activity-modal-title"
          >
            <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
              <div id="candidate-activity-modal-title" className="text-sm font-semibold text-slate-900">
                {t('app.candidate_card.activity_feed.title')}
              </div>
              <button type="button" className="btn-secondary btn-sm" onClick={() => setActivityModalOpen(false)}>
                {t('common.actions.close')}
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-3">
              <CandidateTimelinePanel
                locale={locale}
                stageHistory={timelineStageHistory}
                notes={notes}
                reminders={timelineReminders}
                loading={timelineStageHistoryLoading || timelineRemindersLoading}
                timelineError={timelineError}
                resolveStageLabel={stageLabelIntl}
                includeStageChanges
                variant="info"
                collapsedCount={15}
                hideToggle
                expanded
                itemsMaxHeightClass="max-h-[min(70vh,28rem)]"
                stageHistoryShortcut={Boolean(model?.id)}
              />
            </div>
          </div>
        </div>
      ) : null}

      {/* Manager override: reason once, then close — editing continues with autosave (portal → body). */}
      {typeof document !== 'undefined' &&
      !isNew &&
      model?.id &&
      candidateEditPhase === 'picking_reason' &&
      !isMasked
        ? createPortal(
            <>
              <button
                type="button"
                className="fixed inset-0 z-[10000] cursor-default bg-slate-900/40"
                aria-label={t('common.actions.close')}
                onClick={() => setCandidateEditPhase('idle')}
              />
              <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="candidate-override-save-title"
                className="fixed left-1/2 top-1/2 z-[10001] w-[calc(100%-1.5rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-amber-300 bg-white p-4 shadow-2xl ring-2 ring-amber-100"
              >
                <div id="candidate-override-save-title" className="text-sm font-semibold text-amber-950">
                  {t('app.candidate_card.override_modal.title')}
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">
                  {t('app.candidate_card.override_modal.hint')}
                </p>
                <label className="mt-3 block text-xs font-medium text-slate-700" htmlFor="candidate-override-reason">
                  {t('app.candidate_card.override_reason_label')}
                </label>
                <select
                  id="candidate-override-reason"
                  className="input mt-1 w-full"
                  value={candidateOverrideReason}
                  onChange={(e) => setCandidateOverrideReason(e.target.value)}
                >
                  <option value="">{t('app.candidate_card.override_reason_placeholder')}</option>
                  {overrideReasonOptions.map((reason) => (
                    <option key={reason} value={reason}>
                      {reason}
                    </option>
                  ))}
                </select>
                <div className="mt-4 flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 pt-3">
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => setCandidateEditPhase('idle')}
                  >
                    {t('app.candidate_card.override_modal.cancel_edit')}
                  </button>
                  <button type="button" className="btn-primary btn-sm" onClick={() => confirmOverrideReasonStartEdit()}>
                    {t('app.candidate_card.override_modal.continue_edit')}
                  </button>
                </div>
              </div>
            </>,
            document.body,
          )
        : null}

      {/* Documents side panel */}
      {!isMasked && docsDrawerOpen && model?.id ? (
        <div className="fixed inset-0 z-50 bg-black/50 p-4" onClick={closeDocsDrawer}>
          <div
            className="fixed right-0 top-0 h-full w-full max-w-6xl overflow-hidden rounded-l-2xl bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-slate-200 p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0 text-sm font-semibold text-slate-900 truncate">
                  {t('app.candidate_card.docs_panel.title')}
                </div>
                <button type="button" className="btn-secondary btn-sm" onClick={closeDocsDrawer}>
                  {t('common.actions.close')}
                </button>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  className="btn-primary btn-sm"
                  onClick={() => void generateUploadLink()}
                  disabled={uploadLinkBusy}
                >
                  {uploadLinkBusy
                    ? t('app.candidate_card.actions.upload_link_creating')
                    : t('app.candidate_card.actions.upload_link')}
                </button>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => void downloadBundle()}
                  disabled={downloadingBundle}
                >
                  {downloadingBundle
                    ? t('app.candidate_card.actions.exporting_bundle')
                    : t('app.candidate_card.actions.export_bundle')}
                </button>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => setDocsSummaryRefreshTrigger((x) => x + 1)}
                >
                  {t('app.candidate_card.actions.refresh')}
                </button>
              </div>
              {(uploadLink?.documents_url || uploadLink?.apply_url) ? (
                <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-xs text-slate-700">
                  <div className="font-medium text-slate-800">
                    {t('app.candidate_card.docs.upload_link_label')}
                  </div>
                  <div className="mt-1 break-all text-slate-600">
                    {new URL(uploadLink.documents_url || uploadLink.apply_url, window.location.origin).toString()}
                  </div>
                  {uploadLink.expires_at ? (
                    <div className="mt-1 text-[11px] text-slate-500">
                      {t('app.candidate_card.docs.upload_link_expires', {
                        values: { date: formatDateSafe(uploadLink.expires_at, locale) || uploadLink.expires_at },
                      })}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
            <div className="h-full overflow-auto p-3">
              <CandidateDocuments
                key={`${model.id}:${docsDrawerType || 'default'}`}
                candidateId={String(model.id)}
                hideHeader
                candidateProfile={candidateProfile}
                initialType={docsDrawerType}
                {...({
                  ownerContext: docsOwnerContext,
                  onFieldsApplied: (doc: any, fields: Record<string, any>) =>
                    applyDocFieldsToCandidate(String(doc?.type_code || doc?.type || ''), fields),
                } as any)}
              />
            </div>
          </div>
        </div>
      ) : null}

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
    <div className="min-w-0 space-y-2 rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs font-semibold text-slate-800">{t('app.candidate_card.services.title')}</div>
        <div className="flex flex-wrap items-center justify-end gap-1.5">
          <button type="button" className="btn-secondary btn-sm" onClick={reload} disabled={loading}>
            {loading ? t('app.candidate_card.actions.refreshing') : t('app.candidate_card.actions.refresh')}
          </button>
          {canManage && (
            <Link to={servicesWorkspacePath('orders', { candidateId })} className="btn-secondary btn-sm">
              {t('app.candidate_card.services.open_module')}
            </Link>
          )}
        </div>
      </div>

      {loading ? (
        <div className="text-sm text-slate-500">{t('app.candidate_card.services.loading')}</div>
      ) : orders.length === 0 ? (
        <div className="text-sm text-slate-500">{t('app.candidate_card.services.empty')}</div>
      ) : (
        <div className="max-h-56 overflow-auto rounded-xl border border-slate-200/90 bg-slate-50/40">
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
                  <td className="px-3 py-2 uppercase text-xs text-slate-500">{formatOrderStatus(order.status)}</td>
                  <td className="px-3 py-2 text-xs">
                    <ul className="list-disc list-inside space-y-1">
                      {order.items.map((item) => (
                        <li key={item.id}>
                          <span className="font-medium text-slate-700">{item.service?.name || item.service_id}</span>
                          <span className="ml-2 text-slate-500">{formatItemStatus(item.status)}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td className="px-3 py-2 text-right text-sm text-slate-700">{formatAmount(order.total_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
