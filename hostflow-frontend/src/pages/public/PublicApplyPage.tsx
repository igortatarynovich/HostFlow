import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import type {
  IntakeEmployment,
  PublicChecklist,
  PublicDocumentEntry,
  PublicDocumentType,
  PublicTimelineEntry,
} from '../../api/publicIntake'
import {
  presignPublicDocument,
  uploadPublicDocument,
  requestMagicLink,
  rotateStatusToken,
} from '../../api/publicIntake'
import { usePublicIntake } from '../../modules/public-intake/usePublicIntake'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { PublicTimeline, buildFallbackTimeline } from './components/PublicTimeline'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { PublicPageShell } from './components/PublicPageShell'
import { LegalLinksBlock } from './components/LegalLinksBlock'
import { PublicLogo } from '../../components/public/PublicLogo'
import {
  describeRequiredFiles,
  formatDocumentStatus,
  getDocumentTitle,
  requestedFromText,
} from './utils/documents'
import { CONSENT_DOCUMENT_VERSIONS, PUBLIC_TOKEN_STORAGE_KEY, PUBLIC_EMAIL_STORAGE_KEY } from './constants'
import Select from '../../components/controls/Select'
import { buildCountryOptions } from '../../data/countries'
import { PREFERRED_CONTACT_VALUES } from '../../data/preferredContactChannels'
import { isCookieConsentGranted, subscribeCookieConsent } from '../../components/public/cookieConsent'
import { useRobotsMeta } from '../../hooks/useRobotsMeta'

import type { StepKey, MultiSelectOption } from '../../modules/public-intake/types'

const STEP_KEYS = ['overview', 'contacts', 'personal', 'experience', 'employment', 'documents', 'agreements'] as const

const normalizeDocType = (code: string): string => String(code || '').trim().toLowerCase()

const DOCUMENT_EQUIVALENT_CODES: Record<string, string[]> = {
  driver_license_code95: ['driver_license', 'qualification_code95', 'code95', 'code_95'],
}
const GUIDED_DOC_ORDER = [
  'driver_license_code95',
  'driver_license',
  'qualification_code95',
  'code95',
  'tachograph_card',
  'passport',
  'id_card',
  'visa',
  'residence_permit',
  'residence_card',
  'karta_pobytu',
  'voivodeship_decision',
  'medical_certificate',
  'psych_tests',
]
const STAY_DOC_CODES = ['id_card', 'visa', 'residence_permit', 'residence_card', 'karta_pobytu']

const TRAILER_OPTIONS: MultiSelectOption[] = [
  { value: 'mega', labelKey: 'public.intake.forms.employment.trailer_labels.mega' },
  { value: 'standard', labelKey: 'public.intake.forms.employment.trailer_labels.standard' },
  { value: 'platform', labelKey: 'public.intake.forms.employment.trailer_labels.platform' },
  { value: 'frigo', labelKey: 'public.intake.forms.employment.trailer_labels.frigo' },
  { value: 'tent', labelKey: 'public.intake.forms.employment.trailer_labels.tent' },
  { value: 'container', labelKey: 'public.intake.forms.employment.trailer_labels.container' },
  { value: 'tandem', labelKey: 'public.intake.forms.employment.trailer_labels.tandem' },
  { value: 'car_transporter', labelKey: 'public.intake.forms.employment.trailer_labels.car_transporter' },
]
const ROUTE_OPTIONS: MultiSelectOption[] = [
  { value: 'eu', labelKey: 'public.intake.forms.employment.route_labels.eu' },
  { value: 'cis', labelKey: 'public.intake.forms.employment.route_labels.cis' },
  { value: 'uk', labelKey: 'public.intake.forms.employment.route_labels.uk' },
  { value: 'scandi', labelKey: 'public.intake.forms.employment.route_labels.scandi' },
  { value: 'local', labelKey: 'public.intake.forms.employment.route_labels.local' },
]
type DocCard = {
  code: string
  required: boolean
  meta?: PublicDocumentType
  entry?: PublicDocumentEntry
}

function RequiredBadge({ label, active = false }: { label: string; active?: boolean }) {
  const tone = active
    ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100'
    : 'bg-rose-50 text-rose-700 ring-1 ring-rose-100'
  return (
    <span className={`ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${tone}`}>
      {label}
    </span>
  )
}

function createEmploymentDraft(base?: Partial<IntakeEmployment>): IntakeEmployment {
  const today = new Date().toISOString().slice(0, 10)
  return {
    id: base?.id,
    employer_name: base?.employer_name ?? '',
    country: base?.country ?? '',
    position: base?.position ?? '',
    start_date: base?.start_date ?? today,
    end_date: base?.end_date ?? '',
    trailer_types: [...(base?.trailer_types ?? [])],
    route_types: [...(base?.route_types ?? [])],
    truck_brands: base?.truck_brands ?? null,
    eu_routes: base?.eu_routes ?? null,
    reason_for_leaving: base?.reason_for_leaving ?? null,
    reference_contact: base?.reference_contact ?? null,
  }
}

function toggleInArray(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value]
}

function statusTone(status?: string): string {
  if (!status) return 'bg-slate-100 text-slate-700'
  const normalized = status.toLowerCase()
  if (['approved', 'received', 'delivered', 'completed'].includes(normalized)) {
    return 'bg-green-50 text-green-700'
  }
  if (['requested', 'in_progress', 'submitted', 'ordered'].includes(normalized)) {
    return 'bg-amber-50 text-amber-800'
  }
  if (['rejected', 'expired', 'overdue'].includes(normalized)) {
    return 'bg-rose-50 text-rose-700'
  }
  return 'bg-slate-100 text-slate-700'
}

export default function PublicApplyPage() {
  useRobotsMeta({ index: false, follow: false })
  const { token } = useParams<{ token: string }>()
  const [activeStep, setActiveStep] = useState<StepKey>('overview')
  const initialStepChosen = useRef(false)
  const [employmentDraft, setEmploymentDraft] = useState<IntakeEmployment>(createEmploymentDraft())
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [docResponses, setDocResponses] = useState<Record<string, 'yes' | 'no' | null>>({})
  const [docFiles, setDocFiles] = useState<Record<string, File | null>>({})
  const [docUploading, setDocUploading] = useState<Record<string, boolean>>({})
  const [docUploadErrors, setDocUploadErrors] = useState<Record<string, string | null>>({})
  const [shareCopied, setShareCopied] = useState(false)
  const [resendState, setResendState] = useState<'idle' | 'pending' | 'sent' | 'error' | 'missing'>('idle')
  const [resendMessage, setResendMessage] = useState<string | null>(null)
  const [resendLimitInfo, setResendLimitInfo] = useState<{ cooldown: number; limit: number } | null>(null)
  const [rotatingShare, setRotatingShare] = useState(false)
  const [cookiesAccepted, setCookiesAccepted] = useState(() => isCookieConsentGranted())

  const {
    loading,
    saving,
    submitting,
    error,
    state,
    formData,
    refresh,
    updateContacts,
    updatePersonal,
    updateExperience,
    upsertEmployment,
    removeEmployment,
    updateAgreements,
    submit,
  } = usePublicIntake(token)
  const { t, locale } = useI18n()
  const steps = useMemo(() => STEP_KEYS.map((key) => ({ key, label: t(`public.intake.steps.${key}`) })), [t])
  const { notify } = useToast()

  useEffect(() => {
    const unsubscribe = subscribeCookieConsent(() => setCookiesAccepted(true))
    return unsubscribe
  }, [])

  useEffect(() => {
    if (cookiesAccepted && !formData.agreements.cookies_accepted) {
      updateAgreements({ cookies_accepted: true })
    }
  }, [cookiesAccepted, formData.agreements.cookies_accepted, updateAgreements])

  const rawChecklist = state?.checklist
  const docs: PublicDocumentEntry[] = state?.documents?.documents ?? []
  const docTypes = state?.documents?.doc_types
  const docTypeMap = useMemo<Record<string, PublicDocumentType>>(
    () => (docTypes ?? {}) as Record<string, PublicDocumentType>,
    [docTypes]
  )
  const countryOptions = useMemo(() => buildCountryOptions(locale), [locale])
  const summary = state?.documents?.summary
  const summaryChecklist = summary?.checklist as PublicChecklist | undefined
  const checklist = useMemo<PublicChecklist | undefined>(() => {
    if (
      (rawChecklist?.requiredTypes?.length ?? 0) > 0 ||
      (rawChecklist?.optionalTypes?.length ?? 0) > 0
    ) {
      return rawChecklist
    }
    return summaryChecklist ?? rawChecklist
  }, [rawChecklist, summaryChecklist])
  const hasChecklistTypes =
    (checklist?.requiredTypes?.length ?? 0) > 0 || (checklist?.optionalTypes?.length ?? 0) > 0
  const satisfiedDocTypes = useMemo(() => {
    const set = new Set<string>()
    docs.forEach((doc) => {
      const normalized = normalizeDocType(doc.doc_type || doc.type || '')
      if (!normalized) return
      if (!doc.has_files) return
      set.add(normalized)
      const equivalents = DOCUMENT_EQUIVALENT_CODES[normalized] || []
      equivalents.forEach((alias) => {
        const normalizedAlias = normalizeDocType(alias)
        if (normalizedAlias) set.add(normalizedAlias)
      })
    })
    return set
  }, [docs])

  const docCards = useMemo<DocCard[]>(() => {
    const entries: DocCard[] = []
    const byType = new Map<string, PublicDocumentEntry>()
    docs.forEach((doc) => {
      const normalized = normalizeDocType(doc.doc_type || doc.type || '')
      if (!normalized) return
      byType.set(normalized, doc)
      const equivalents = DOCUMENT_EQUIVALENT_CODES[normalized] || []
      equivalents.forEach((parent) => {
        const normalizedParent = normalizeDocType(parent)
        if (!normalizedParent) return
        if (!byType.has(normalizedParent)) {
          byType.set(normalizedParent, doc)
        }
      })
    })
    const seen = new Set<string>()
    const requiredSet = new Set<string>((checklist?.requiredTypes ?? []).map((code) => normalizeDocType(code)))
    const append = (codes: string[] | undefined, required: boolean) => {
      if (!codes) return
      codes.forEach((code) => {
        const trimmed = String(code).trim()
        const normalized = normalizeDocType(trimmed)
        if (!trimmed || seen.has(normalized)) return
        entries.push({
          code: trimmed,
          required,
          meta: docTypeMap[trimmed],
          entry: byType.get(normalized),
        })
        seen.add(normalized)
      })
    }
    append(checklist?.requiredTypes, true)
    append(checklist?.optionalTypes, false)
    docs.forEach((doc) => {
      const code = doc.doc_type || doc.type
      if (!code || seen.has(code)) return
      entries.push({
        code,
        required: false,
        meta: docTypeMap[code],
        entry: doc,
      })
      seen.add(code)
    })
    const combinedCode = 'driver_license_code95'
    if (
      docTypeMap[combinedCode] &&
      !seen.has(combinedCode) &&
      requiredSet.has('driver_license') &&
      requiredSet.has('code95')
    ) {
      entries.push({
        code: combinedCode,
        required: false,
        meta: docTypeMap[combinedCode],
        entry: byType.get(combinedCode),
      })
      seen.add(combinedCode)
    }
    if (entries.length === 0 && Object.keys(docTypeMap).length > 0) {
      Object.keys(docTypeMap).forEach((code) => {
        if (!code || seen.has(code)) return
        entries.push({
          code,
          required: false,
          meta: docTypeMap[code],
          entry: byType.get(code),
        })
        seen.add(code)
      })
    }
    const orderIndex = (code: string) => {
      const normalized = normalizeDocType(code)
      const idx = GUIDED_DOC_ORDER.findIndex((item) => normalizeDocType(item) === normalized)
      return idx === -1 ? GUIDED_DOC_ORDER.length + 1 : idx
    }
    return entries.sort((a, b) => orderIndex(a.code) - orderIndex(b.code))
  }, [checklist, docTypeMap, docs])

  const docRequirements = useMemo(() => {
    const titles: string[] = []
    const details: string[] = []
    docCards.forEach((card) => {
      const info = describeRequiredFiles(card.meta?.required_files, t)
      if (!info) return
      if (info.title) {
        titles.push(info.title)
      }
      if (info.details.length > 0) {
        info.details.forEach((line) => details.push(line))
      }
    })
    const uniqueTitles = Array.from(new Set(titles))
    const uniqueDetails = Array.from(new Set(details))
    if (uniqueTitles.length === 0 && uniqueDetails.length === 0) {
      return null
    }
    return { titles: uniqueTitles, details: uniqueDetails }
  }, [docCards, t])
  const preferredContactOptions = useMemo(
    () =>
      PREFERRED_CONTACT_VALUES.map((value) => ({
        value,
        label: t(`app.candidate_card.contacts.options.${value || 'none'}`),
      })),
    [t]
  )
  useEffect(() => {
    setDocResponses((prev) => {
      const next: Record<string, 'yes' | 'no' | null> = {}
      docCards.forEach((card) => {
        next[card.code] = prev[card.code] ?? (card.entry ? 'yes' : null)
      })
      return next
    })
    setDocFiles((prev) => {
      const next: Record<string, File | null> = {}
      docCards.forEach((card) => {
        if (prev[card.code]) {
          next[card.code] = prev[card.code]
        }
      })
      return next
    })
    setDocUploadErrors((prev) => {
      const next: Record<string, string | null> = {}
      docCards.forEach((card) => {
        if (prev[card.code]) {
          next[card.code] = prev[card.code]
        }
      })
      return next
    })
    setDocUploading((prev) => {
      const next: Record<string, boolean> = {}
      docCards.forEach((card) => {
        if (prev[card.code]) {
          next[card.code] = prev[card.code]
        }
      })
      return next
    })
  }, [docCards])
  const requiredDocCards = useMemo(() => docCards.filter((card) => card.required), [docCards])
  const readyRequiredCount = useMemo(
    () => requiredDocCards.filter((card) => satisfiedDocTypes.has(normalizeDocType(card.code))).length,
    [requiredDocCards, satisfiedDocTypes]
  )
  const missingRequiredCards = useMemo(
    () => requiredDocCards.filter((card) => !satisfiedDocTypes.has(normalizeDocType(card.code))),
    [requiredDocCards, satisfiedDocTypes]
  )
  const requiredSummary = summary?.required
  const summaryStats = {
    total: requiredSummary?.total ?? requiredDocCards.length,
    ready: requiredSummary?.ready ?? readyRequiredCount,
    inProgress: requiredSummary?.in_progress ?? 0,
    missing:
      requiredSummary?.missing_count ??
      Math.max(0, requiredDocCards.length - readyRequiredCount),
  }
  const readyOrUploadedCount = Math.min(
    summaryStats.total,
    Math.max(readyRequiredCount, summaryStats.ready + summaryStats.inProgress),
  )
  const checklistInitialized = hasChecklistTypes || docCards.length > 0 || summaryStats.total > 0
  const nextActions = useMemo(
    () =>
      missingRequiredCards.slice(0, 3).map((card) => ({
        code: card.code,
        title: getDocumentTitle(card.meta, card.code, locale),
        status: formatDocumentStatus(card.entry?.status, t, true),
      })),
    [locale, missingRequiredCards, t]
  )
  const generalConsent = Boolean(formData.agreements.general)
  const employerConsent = Boolean(formData.agreements.employer_share)
  const termsAccepted = Boolean(formData.agreements.terms_acceptance)
  const cookieReady = Boolean(formData.agreements.cookies_accepted || cookiesAccepted)
  const consentChecklistReady = generalConsent && employerConsent && termsAccepted
  const agreementsReady = consentChecklistReady && cookieReady
  const hasPhoneContact = Boolean(
    formData.contacts.phone_country_code?.trim() &&
      formData.contacts.phone?.trim()
  )
  const hasEmailContact = Boolean(formData.contacts.email?.trim())
  const contactComplete = hasPhoneContact || hasEmailContact
  const contactBadgeEmail = hasEmailContact
  const contactBadgePhone = hasPhoneContact
  const personalNameComplete = Boolean(formData.personal.full_name?.trim())
  const personalCitizenshipComplete = Boolean(formData.personal.citizenship)
  const personalResidencyComplete = Boolean(formData.personal.residency_status)
  const personalPolandComplete = formData.personal.in_poland === true || formData.personal.in_poland === false
  const personalComplete = Boolean(
    personalNameComplete &&
      personalCitizenshipComplete &&
      personalResidencyComplete &&
      personalPolandComplete
  )
  const experienceYears = formData.experience.years_ce
  const yearsComplete =
    experienceYears !== null &&
    experienceYears !== undefined &&
    Number.isFinite(experienceYears) &&
    experienceYears >= 0
  const intlAnswered = formData.experience.intl_experience === true || formData.experience.intl_experience === false
  const employmentEntriesValid = formData.employments.every(
    (entry) => entry?.employer_name?.trim() && entry?.start_date && entry.start_date.length > 0
  )
  const hasEmployment = formData.employments.length > 0
  const employmentRequired = formData.experience.intl_experience === true
  const employmentComplete = employmentEntriesValid && (!employmentRequired ? true : hasEmployment)
  const experienceComplete = yearsComplete && intlAnswered && employmentComplete
  const profileReady = contactComplete && personalComplete && experienceComplete
  const docUploadMap = useMemo(() => {
    const map = new Map<string, boolean>()
    docCards.forEach((card) => {
      map.set(card.code.toLowerCase(), Boolean(card.entry?.has_files))
    })
    return map
  }, [docCards])
  const hasAnyDoc = useCallback(
    (codes: string[]) => codes.some((code) => docUploadMap.get(code.toLowerCase())),
    [docUploadMap]
  )
  const licenseWith95Ready = hasAnyDoc(['driver_license_code95'])
  const docCardMap = useMemo(() => {
    const map = new Map<string, DocCard>()
    docCards.forEach((card) => map.set(normalizeDocType(card.code), card))
    return map
  }, [docCards])
  const licenseComboCard = docCardMap.get('driver_license_code95')
  const licenseSplitResponse = licenseComboCard ? docResponses[licenseComboCard.code] : null
  const hideSplitLicenseDocs = Boolean(licenseWith95Ready || licenseSplitResponse === 'yes')
  const driverLicenseReady =
    licenseWith95Ready ||
    hasAnyDoc(['driver_license', 'driving_license', 'driver_license_eu', 'driver_license_95'])
  const passportDocReady = hasAnyDoc(['passport'])
  const stayDocReady = hasAnyDoc(['visa', 'residence_card', 'residence_permit', 'karta_pobytu'])
  const code95DocReady = licenseWith95Ready || hasAnyDoc(['qualification_code95', 'code95'])
  const mandatoryDocsReady = driverLicenseReady && passportDocReady && stayDocReady && code95DocReady
  const baseDocumentsReady = summaryStats.total === 0 || readyOrUploadedCount >= summaryStats.total
  const documentsReady = baseDocumentsReady && mandatoryDocsReady
  const nextSuggestedStep: StepKey = useMemo(() => {
    if (!contactComplete) return 'contacts'
    if (!personalComplete) return 'personal'
    if (!experienceComplete) return 'experience'
    if (employmentRequired && !employmentComplete) return 'employment'
    if (!documentsReady) return 'documents'
    if (!agreementsReady) return 'agreements'
    return 'overview'
  }, [
    contactComplete,
    personalComplete,
    experienceComplete,
    employmentRequired,
    employmentComplete,
    documentsReady,
    agreementsReady,
  ])
  const profileChecklist = [
    {
      key: 'contacts',
      label: t('public.intake.checklist.contacts.label'),
      ready: contactComplete,
      description: contactComplete
        ? t('public.intake.checklist.contacts.ready')
        : t('public.intake.checklist.contacts.missing'),
    },
    {
      key: 'personal',
      label: t('public.intake.checklist.personal.label'),
      ready: personalComplete,
      description: personalComplete
        ? t('public.intake.checklist.personal.ready')
        : t('public.intake.checklist.personal.missing'),
    },
    {
      key: 'experience',
      label: t('public.intake.checklist.experience.label'),
      ready: experienceComplete,
      description: experienceComplete
        ? t('public.intake.checklist.experience.ready')
        : t('public.intake.checklist.experience.missing'),
    },
    {
      key: 'agreements',
      label: t('public.intake.checklist.agreements.label'),
      ready: agreementsReady,
      description: agreementsReady
        ? t('public.intake.checklist.agreements.ready')
        : t('public.intake.checklist.agreements.missing'),
    },
  ]
  const applicationStatusLabel =
    state?.status === 'submitted' ? t('public.intake.status.submitted') : t('public.intake.status.draft')
  const applicationStatusHint =
    state?.status === 'submitted'
      ? state?.submitted_at
        ? t('public.intake.status.submitted_hint_with_date', {
            values: { datetime: new Date(state.submitted_at).toLocaleString(locale) },
          })
        : t('public.intake.status.submitted_hint')
      : t('public.intake.status.draft_hint')
  const documentsProgressLabel =
    summaryStats.total > 0
      ? `${readyOrUploadedCount}/${summaryStats.total}`
      : t('public.intake.documents.optional_short')
  const documentsCardDescription = checklistInitialized
    ? summaryStats.total > 0
      ? t('public.intake.documents.progress', {
          values: { ready: readyOrUploadedCount, total: summaryStats.total },
        })
      : t('public.intake.documents.optional')
    : t('public.intake.documents.checklist_pending')
  const blockingReasons = useMemo(() => {
    if (state?.status === 'submitted') return []
    const reasons: string[] = []
    if (!contactComplete) reasons.push(t('public.intake.validations.contacts'))
    if (!personalComplete) reasons.push(t('public.intake.validations.personal'))
    if (!yearsComplete) reasons.push(t('public.intake.validations.experience_years'))
    if (!intlAnswered) reasons.push(t('public.intake.validations.experience_intl'))
    if (employmentRequired && !employmentComplete) reasons.push(t('public.intake.validations.employment_required'))
    if (!consentChecklistReady) reasons.push(t('public.intake.validations.consents'))
    if (!cookieReady) reasons.push(t('public.intake.validations.cookies'))
    return reasons
  }, [
    state?.status,
    contactComplete,
    personalComplete,
    yearsComplete,
    intlAnswered,
    employmentRequired,
    employmentComplete,
    consentChecklistReady,
    cookieReady,
    t,
  ])
  const docWarningReasons = useMemo(
    () =>
      missingRequiredCards.map((card) =>
        t('public.intake.validations.documents.missing', {
          values: { doc: getDocumentTitle(card.meta, card.code, locale) },
        })
      ),
    [missingRequiredCards, t, locale]
  )
  const canSubmitApplication = agreementsReady && contactComplete && personalComplete && experienceComplete && !submitting
  const stageLabel = useMemo(() => {
    if (!state?.stage) return applicationStatusLabel
    const normalized = state.stage.trim().toLowerCase().replace(/\s+/g, '_')
    const translated = t(`public.intake.stage.${normalized}`, { defaultValue: '' })
    if (translated) {
      return translated
    }
    return state.stage
  }, [state?.stage, applicationStatusLabel, t])
  const timelineEntries = useMemo<PublicTimelineEntry[]>(() => {
    if (state?.timeline && state.timeline.length > 0) {
      return state.timeline
    }
    return buildFallbackTimeline(
      {
        createdAt: state?.created_at,
        submittedAt: state?.submitted_at,
        profileReady,
        documentsReady,
        readyRequiredCount: readyOrUploadedCount,
        requiredTotal: requiredDocCards.length,
      },
      t,
    )
  }, [state?.timeline, state?.created_at, state?.submitted_at, profileReady, documentsReady, readyOrUploadedCount, requiredDocCards.length, t])
  const statusShareUrl = useMemo(() => {
    if (!state?.status_share_token) return null
    const origin = typeof window !== 'undefined' ? window.location.origin : ''
    return `${origin}/public/status/${state.status_share_token}`
  }, [state?.status_share_token])

  const handleCopyShareLink = useCallback(async () => {
    if (!statusShareUrl || typeof navigator === 'undefined' || !navigator.clipboard) return
    try {
      await navigator.clipboard.writeText(statusShareUrl)
      setShareCopied(true)
      notify({ title: t('public.intake.share.notifications.copied'), variant: 'success' })
      window.setTimeout(() => setShareCopied(false), 2000)
    } catch {
      setShareCopied(false)
      notify({ title: t('public.intake.share.notifications.copy_failed'), variant: 'error' })
    }
  }, [statusShareUrl, notify, t])

  const buildMagicLinkPayload = useCallback(() => {
    const email = formData.contacts.email?.trim()
    const phone = formData.contacts.phone?.trim()
    const phone_country_code = formData.contacts.phone_country_code?.trim()
    if (!email && !phone) {
      return null
    }
    return {
      email: email || undefined,
      phone: phone || undefined,
      phone_country_code: phone_country_code || undefined,
    }
  }, [formData.contacts])

  const handleResendMagicLink = useCallback(async () => {
    const payload = buildMagicLinkPayload()
    if (!payload) {
      setResendState('missing')
      setResendMessage(t('public.intake.forms.contacts.resend_missing'))
      return
    }
    setResendState('pending')
    setResendMessage(null)
    try {
      const response = await requestMagicLink(payload)
      setResendState('sent')
      const message = t('public.intake.share.notifications.magic_sent')
      setResendMessage(message)
      setResendLimitInfo({ cooldown: response.cooldown_seconds, limit: response.daily_limit })
      notify({ title: t('public.intake.share.sent'), description: message, variant: 'success' })
    } catch (err: any) {
      setResendState('error')
      const description = err?.response?.data?.detail || t('public.intake.share.notifications.magic_failed')
      setResendMessage(description)
      if (err?.response?.data?.cooldown_seconds && err?.response?.data?.daily_limit) {
        setResendLimitInfo({
          cooldown: err.response.data.cooldown_seconds,
          limit: err.response.data.daily_limit,
        })
      }
      notify({ title: t('public.intake.share.notifications.magic_failed'), description, variant: 'error' })
    }
  }, [buildMagicLinkPayload, notify, t])

  useEffect(() => {
    if (!token) return
    try {
      window.localStorage.setItem(PUBLIC_TOKEN_STORAGE_KEY, token)
    } catch {
      /* ignore */
    }
  }, [token])

  useEffect(() => {
    if (!token) return
    const email = formData.contacts.email
    if (!email) return
    try {
      window.localStorage.setItem(PUBLIC_EMAIL_STORAGE_KEY, email)
    } catch {
      /* ignore */
    }
  }, [token, formData.contacts.email])
  useEffect(() => {
    if (!state || initialStepChosen.current) return
    initialStepChosen.current = true
    setActiveStep(nextSuggestedStep)
  }, [state, nextSuggestedStep])

  const currentStepIndex = useMemo(() => steps.findIndex((step) => step.key === activeStep), [steps, activeStep])
  const normalizedStepIndex = currentStepIndex >= 0 ? currentStepIndex : 0
  const progressPercent = Math.round(
    (normalizedStepIndex / Math.max(steps.length - 1, 1)) * 100,
  )
  const employmentDraftReady = useMemo(
    () => Boolean((employmentDraft.employer_name || '').trim() && employmentDraft.start_date),
    [employmentDraft]
  )
  const persistEmploymentDraft = useCallback(() => {
    if (!employmentDraftReady) return false
    const index = editingIndex ?? formData.employments.length
    if (index >= 3) return false
    upsertEmployment(index, {
      ...employmentDraft,
      employer_name: employmentDraft.employer_name.trim(),
      country: employmentDraft.country?.toUpperCase() || null,
      position: employmentDraft.position || null,
      start_date: employmentDraft.start_date,
      end_date: employmentDraft.end_date || null,
      trailer_types: employmentDraft.trailer_types ?? [],
      route_types: employmentDraft.route_types ?? [],
      truck_brands: employmentDraft.truck_brands ?? null,
      eu_routes: employmentDraft.eu_routes ?? null,
      reason_for_leaving: employmentDraft.reason_for_leaving || null,
      reference_contact: employmentDraft.reference_contact || null,
    })
    setEmploymentDraft(createEmploymentDraft())
    setEditingIndex(null)
    return true
  }, [editingIndex, employmentDraft, employmentDraftReady, formData.employments.length, upsertEmployment])
  const statusCards = useMemo(() => {
    if (!steps.length) return []
    const cards: Array<{ type: 'done' | 'current' | 'next'; step: (typeof steps)[number] }> = []
    if (normalizedStepIndex > 0) {
      cards.push({ type: 'done', step: steps[normalizedStepIndex - 1] })
    }
    if (steps[normalizedStepIndex]) {
      cards.push({ type: 'current', step: steps[normalizedStepIndex] })
    }
    if (normalizedStepIndex < steps.length - 1) {
      cards.push({ type: 'next', step: steps[normalizedStepIndex + 1] })
    }
    return cards
  }, [steps, normalizedStepIndex])
  const nextStepLabel = useMemo(
    () => steps.find((step) => step.key === nextSuggestedStep)?.label || steps[0]?.label || '',
    [steps, nextSuggestedStep]
  )

  const goToStep = (target: StepKey) => {
    if (activeStep === 'employment') {
      persistEmploymentDraft()
    }
    setActiveStep(target)
  }
  const changeStep = (direction: 'prev' | 'next') => {
    const currentIdx = steps.findIndex((step) => step.key === activeStep)
    if (direction === 'prev') {
      goToStep(steps[Math.max(0, currentIdx - 1)].key)
      return
    }
    goToStep(steps[Math.min(steps.length - 1, currentIdx + 1)].key)
  }

  const handleEmploymentSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    persistEmploymentDraft()
  }

  const startEditEmployment = (index: number) => {
    const entry = formData.employments[index]
    if (!entry) return
    setEditingIndex(index)
    setEmploymentDraft(createEmploymentDraft(entry))
  }

  const cancelEmploymentEdit = () => {
    setEditingIndex(null)
    setEmploymentDraft(createEmploymentDraft())
  }

  const uploadDocumentForType = useCallback(
    async (docType: string) => {
      if (!token) return
      const file = docFiles[docType]
      if (!file) {
        setDocUploadErrors((prev) => ({ ...prev, [docType]: t('public.intake.notifications.upload_missing') }))
        return
      }
      setDocUploading((prev) => ({ ...prev, [docType]: true }))
      setDocUploadErrors((prev) => ({ ...prev, [docType]: null }))
      try {
        const presign = await presignPublicDocument(token, { doc_type: docType, filename: file.name })
        await fetch(presign.url, {
          method: presign.method,
          headers: { ...(presign.headers || {}), 'Content-Type': file.type || 'application/octet-stream' },
          body: file,
        })
        const formData = new FormData()
        formData.append('doc_type', docType)
        formData.append('storage_key', presign.key)
        await uploadPublicDocument(token, formData)
        setDocFiles((prev) => ({ ...prev, [docType]: null }))
        await refresh()
      } catch (err: any) {
        setDocUploadErrors((prev) => ({
          ...prev,
          [docType]: err?.response?.data?.detail || err?.message || t('public.intake.notifications.upload_failed'),
        }))
      } finally {
        setDocUploading((prev) => ({ ...prev, [docType]: false }))
      }
    },
    [docFiles, refresh, t, token]
  )
  const handleDocumentResponse = useCallback((code: string, response: 'yes' | 'no') => {
    setDocResponses((prev) => ({ ...prev, [code]: response }))
    if (response === 'no') {
      setDocFiles((prev) => {
        const next = { ...prev }
        delete next[code]
        return next
      })
      setDocUploadErrors((prev) => {
        const next = { ...prev }
        delete next[code]
        return next
      })
    }
  }, [])
  const handleDocumentFileChange = useCallback((code: string, file: File | null) => {
    setDocFiles((prev) => ({ ...prev, [code]: file }))
    if (file) {
      setDocUploadErrors((prev) => ({ ...prev, [code]: null }))
    }
  }, [])

  const shouldRenderUploadField = useCallback((required: boolean, response: 'yes' | 'no' | null) => {
    if (response === 'no') return false
    if (response === 'yes') return true
    return !required
  }, [])

  const handleOpenScanner = useCallback(
    async (docCode: string) => {
      if (!token) return
      try {
        const { createPublicScanSession } = await import('../../api/scanner')
        // Don't pass preset_code - let backend determine it from document_type
        const session = await createPublicScanSession({
          token,
          document_type: docCode,
        })
        // Open scanner in new window/tab
        const scanUrl = `/public/scan?token=${token}&doc=${docCode}&session=${session.id}&return_to=${encodeURIComponent(window.location.href)}`
        window.open(scanUrl, '_blank', 'noopener,noreferrer')
      } catch (err: any) {
        notify({
          title: t('public.intake.notifications.scanner_failed', { defaultValue: 'Failed to open scanner' }),
          description: err?.response?.data?.detail || err?.message,
          variant: 'error',
        })
      }
    },
    [token, notify, t]
  )

  const renderUploadField = useCallback(
    (code: string, currentFile: File | null) => {
      const inputId = `doc-upload-${code}`
      const uploading = Boolean(docUploading[code])
      const error = docUploadErrors[code]
      return (
        <div className="rounded-xl border border-dashed border-brand-100 bg-brand-50/50 p-3 text-sm text-slate-700">
          <div className="flex flex-wrap items-center gap-3">
            <input
              id={inputId}
              type="file"
              className="sr-only"
              accept="image/*,.pdf"
              onChange={(e) => handleDocumentFileChange(code, e.target.files?.[0] ?? null)}
            />
            <label
              htmlFor={inputId}
              className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-brand-700 shadow-sm ring-1 ring-brand-100 hover:bg-brand-50"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {t('documents.actions.upload')}
            </label>
            <span className="text-xs text-slate-500">
              {currentFile
                ? `${currentFile.name} (${Math.round(currentFile.size / 1024)} KB)`
                : t('public.intake.documents.no_file')}
            </span>
          </div>
          {error && <p className="mt-2 text-xs text-rose-600">{error}</p>}
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={() => uploadDocumentForType(code)}
              disabled={uploading || !currentFile}
              className="rounded-lg bg-brand-600 px-4 py-2 text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {uploading ? t('common.loading') : t('documents.actions.upload')}
            </button>
          </div>
        </div>
      )
    },
    [docUploading, docUploadErrors, handleDocumentFileChange, t, uploadDocumentForType, handleOpenScanner]
  )

  const handleRotateShareLink = useCallback(async () => {
    if (!state?.status_share_token || !token) return
    const confirm = window.confirm(t('public.intake.notifications.rotate_warning'))
    if (!confirm) return
    setRotatingShare(true)
    try {
      const rotated = await rotateStatusToken(state.status_share_token)
      await refresh()
      notify({
        title: t('public.intake.share.notifications.rotated'),
        description: t('public.intake.status.submitted_hint_with_date', {
          values: { datetime: new Date(rotated.expires_at).toLocaleDateString(locale) },
        }),
        variant: 'success',
      })
    } catch (err: any) {
      notify({
        title: t('public.intake.share.notifications.rotate_failed'),
        description: err?.response?.data?.detail || err?.message,
        variant: 'error',
      })
    } finally {
      setRotatingShare(false)
    }
  }, [state?.status_share_token, token, notify, refresh, locale, t])

  if (!token) return <Navigate to="/public/intake" replace />

  const stepContent: Record<StepKey, JSX.Element> = {
    overview: (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <OverviewStatCard
            title={t('public.intake.cards.status_title')}
            value={stageLabel}
            description={applicationStatusHint}
          />
          <OverviewStatCard
            title={t('public.intake.documents.card_title')}
            value={documentsProgressLabel}
            description={documentsCardDescription}
          />
          <OverviewStatCard
            title={t('public.intake.cards.profile_title')}
            value={`${profileChecklist.filter((item) => item.ready).length}/${profileChecklist.length}`}
            description={t('public.intake.checklist.hint')}
          />
        </div>
        <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
          <div className="space-y-4">
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white/80 p-5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-base font-semibold text-slate-900">{t('public.intake.documents.next_steps_title')}</h3>
                  <p className="text-sm text-slate-500">
                    {checklistInitialized
                      ? nextActions.length > 0
                        ? t('public.intake.documents.next_steps_missing')
                        : t('public.intake.documents.next_steps_all_done')
                      : t('public.intake.documents.next_steps_locked')}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveStep('documents')}
                  className="rounded-full border border-brand-200 px-4 py-2 text-sm text-brand-700 hover:border-brand-300"
                >
                  {t('public.intake.documents.cta')}
                </button>
              </div>
              {checklistInitialized && nextActions.length === 0 ? (
                <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
                  {t('public.intake.documents.ready_alert')}
                </div>
              ) : checklistInitialized ? (
                <ul className="space-y-3">
                  {nextActions.map((action) => (
                    <li key={action.code} className="rounded-xl border border-dashed border-slate-200 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">{action.title}</p>
                          <p className="text-xs text-slate-500">{action.status}</p>
                        </div>
                        <button
                          type="button"
                          className="text-sm text-brand-600 hover:text-brand-700 hover:underline"
                          onClick={() => setActiveStep('documents')}
                        >
                          {t('public.intake.documents.upload_cta')}
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white/80 p-5">
              <h3 className="text-base font-semibold text-slate-900">{t('public.intake.checklist.title')}</h3>
              <ul className="space-y-2">
                {profileChecklist.map((item) => (
                  <li key={item.key} className="flex items-start gap-3">
                    <span
                      className={`mt-1 inline-flex h-3 w-3 rounded-full ${
                        item.ready ? 'bg-green-500' : 'bg-slate-300'
                      }`}
                    />
                    <div>
                      <p className="text-sm font-medium text-slate-900">{item.label}</p>
                      <p className="text-xs text-slate-500">{item.description}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="space-y-3 rounded-2xl border border-slate-200 bg-white/80 p-5">
            <div>
              <h3 className="text-base font-semibold text-slate-900">{t('public.intake.timeline.title')}</h3>
              <p className="text-sm text-slate-500">{t('public.intake.timeline.subtitle')}</p>
            </div>
            <PublicTimeline entries={timelineEntries} />
          </div>
          {statusShareUrl && (
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white/80 p-5">
              <div className="flex flex-col gap-2">
                <h3 className="text-base font-semibold text-slate-900">{t('public.intake.share.title')}</h3>
                <p className="text-sm text-slate-500">{t('public.intake.share.description')}</p>
                <code className="block truncate rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                  {statusShareUrl}
                </code>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleCopyShareLink}
                  className="inline-flex items-center justify-center rounded-lg border border-brand-200 px-3 py-2 text-sm text-brand-700 hover:bg-brand-50"
                  >
                    {shareCopied ? t('public.intake.share.copied') : t('public.intake.share.copy')}
                  </button>
                  <button
                    type="button"
                    disabled={rotatingShare}
                    onClick={handleRotateShareLink}
                    className="inline-flex items-center justify-center rounded-lg border border-brand-200 px-3 py-2 text-sm text-brand-700 hover:bg-brand-50 disabled:opacity-60"
                  >
                    {rotatingShare ? t('public.intake.share.rotating') : t('public.intake.share.rotate')}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={handleResendMagicLink}
                  className="inline-flex items-center justify-center rounded-lg border border-brand-200 px-3 py-2 text-sm text-brand-700 hover:bg-brand-50"
                >
                  {resendState === 'pending'
                    ? t('public.intake.share.sending')
                    : resendState === 'sent'
                      ? t('public.intake.share.sent')
                      : resendState === 'missing'
                        ? t('public.intake.share.missing_contacts')
                        : t('public.intake.share.send_to_self')}
                </button>
                {resendState === 'error' && (
                  <p className="text-xs text-red-600">
                    {resendMessage ?? t('public.intake.share.notifications.magic_failed')}
                  </p>
                )}
                {resendState === 'sent' && resendMessage && (
                  <p className="text-xs text-green-600">{resendMessage}</p>
                )}
                {resendState === 'missing' && resendMessage && (
                  <p className="text-xs text-amber-600">{resendMessage}</p>
                )}
                {resendLimitInfo && (
                  <p className="text-xs text-slate-500">
                    {t('public.intake.share.rate_limit', {
                      values: { cooldown: resendLimitInfo.cooldown, limit: resendLimitInfo.limit },
                    })}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
        <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <h3 className="text-base font-semibold text-slate-900">{t('public.intake.contacts_card.title')}</h3>
          {formData.contacts.email && (
            <p className="text-sm text-slate-700">
              {t('public.intake.forms.contacts.email')}:&nbsp;
              <span className="font-medium text-slate-900">{formData.contacts.email}</span>
            </p>
          )}
          {formData.contacts.phone && (
            <p className="text-sm text-slate-700">
              {t('public.intake.forms.contacts.phone')}:&nbsp;
              <span className="font-medium text-slate-900">
                {formData.contacts.phone_country_code} {formData.contacts.phone}
              </span>
            </p>
          )}
          <p className="text-sm text-slate-600">
            {contactComplete
              ? t('public.intake.contacts_card.hint_ready')
              : t('public.intake.contacts_card.hint_missing')}
          </p>
          <button
            type="button"
            onClick={() => setActiveStep('contacts')}
            className="mt-2 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-white"
          >
            {t('public.intake.contacts_card.cta')}
          </button>
        </div>
      </div>
    ),
    contacts: (
        <div className="space-y-4">
          <div className="rounded-xl border border-brand-100 bg-brand-50/60 px-4 py-3 text-sm text-brand-900">
            {t('public.intake.forms.contacts.help')}
          </div>
          <div>
            <label className="flex items-center text-sm text-slate-700">
              {t('public.intake.forms.contacts.email')} <RequiredBadge label={t('public.intake.forms.required_one')} active={contactBadgeEmail} />
            </label>
            <input
              type="email"
              value={formData.contacts.email ?? ''}
              onChange={(e) => updateContacts({ email: e.target.value })}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            aria-required
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-[120px_1fr]">
          <div>
            <label className="text-sm text-slate-700">{t('public.intake.forms.contacts.country_code')}</label>
            <input
              type="text"
              value={formData.contacts.phone_country_code ?? ''}
              onChange={(e) => updateContacts({ phone_country_code: e.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </div>
          <div>
            <label className="flex items-center text-sm text-slate-700">
              {t('public.intake.forms.contacts.phone')} <RequiredBadge label={t('public.intake.forms.required_one')} active={contactBadgePhone} />
            </label>
            <input
              type="tel"
              value={formData.contacts.phone ?? ''}
              onChange={(e) => updateContacts({ phone: e.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              aria-required
            />
          </div>
        </div>
        <p className="text-xs text-slate-500">{t('public.intake.forms.contacts.required_hint')}</p>
        <div>
          <label className="text-sm text-slate-700">{t('app.candidate_card.fields.preferred_contact')}</label>
          <select
            value={formData.contacts.preferred_messenger ?? ''}
            onChange={(e) => updateContacts({ preferred_messenger: e.target.value })}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          >
            {preferredContactOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    ),
    personal: (
      <div className="space-y-4">
        <div className="rounded-xl border border-brand-100 bg-brand-50/60 px-4 py-3 text-sm text-brand-900">
          {t('public.intake.forms.personal.help')}
        </div>
        <div>
          <label className="flex items-center text-sm text-slate-700">
            {t('public.intake.forms.personal.full_name')} <RequiredBadge label={t('public.intake.forms.required')} active={personalNameComplete} />
          </label>
          <input
            type="text"
            value={formData.personal.full_name ?? ''}
            onChange={(e) => updatePersonal({ full_name: e.target.value })}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            aria-required
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="flex items-center text-sm text-slate-700">
              {t('public.intake.forms.personal.citizenship')} <RequiredBadge label={t('public.intake.forms.required')} active={personalCitizenshipComplete} />
            </label>
            <div className="mt-1 space-y-1">
              <Select
                options={countryOptions}
                value={formData.personal.citizenship ?? ''}
                onChange={(code) => updatePersonal({ citizenship: code || null })}
                placeholder={t('public.intake.forms.personal.citizenship_placeholder')}
                className="w-full"
              />
              {formData.personal.citizenship && (
                <button
                  type="button"
                  className="text-xs font-medium text-brand-600 hover:text-brand-700"
                  onClick={() => updatePersonal({ citizenship: null })}
                >
                  {t('common.actions.clear')}
                </button>
              )}
            </div>
          </div>
          <div>
            <label className="flex items-center text-sm text-slate-700">
              {t('public.intake.forms.personal.residency')} <RequiredBadge label={t('public.intake.forms.required')} active={personalResidencyComplete} />
            </label>
            <select
              value={formData.personal.residency_status ?? ''}
              onChange={(e) => updatePersonal({ residency_status: e.target.value || null })}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">{t('public.intake.forms.personal.residency_options.default')}</option>
              <option value="eu_citizen">{t('public.intake.forms.personal.residency_options.eu_citizen')}</option>
              <option value="visa">{t('public.intake.forms.personal.residency_options.visa')}</option>
              <option value="card">{t('public.intake.forms.personal.residency_options.card')}</option>
              <option value="none">{t('public.intake.forms.personal.residency_options.none')}</option>
            </select>
          </div>
          <div>
            <label className="flex items-center text-sm text-slate-700">
              {t('public.intake.forms.personal.in_poland')} <RequiredBadge label={t('public.intake.forms.required')} active={personalPolandComplete} />
            </label>
            <select
              value={
                formData.personal.in_poland === true
                  ? 'yes'
                  : formData.personal.in_poland === false
                    ? 'no'
                    : ''
              }
              onChange={(e) =>
                updatePersonal({
                  in_poland: e.target.value === 'yes' ? true : e.target.value === 'no' ? false : null,
                })
              }
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">{t('public.intake.forms.personal.in_poland_options.default')}</option>
              <option value="yes">{t('public.intake.forms.personal.in_poland_options.yes')}</option>
              <option value="no">{t('public.intake.forms.personal.in_poland_options.no')}</option>
            </select>
          </div>
        </div>
      </div>
    ),
    experience: (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="flex items-center text-sm text-slate-700">
              {t('public.intake.forms.personal.ce_experience_eu')} <RequiredBadge label={t('public.intake.forms.required')} active={yearsComplete} />
            </label>
            <input
              type="number"
              min={0}
              value={formData.experience.years_ce ?? ''}
              onChange={(e) =>
                updateExperience((current) => ({
                  ...current,
                  years_ce: e.target.value === '' ? null : Number(e.target.value),
                }))
              }
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              placeholder={t('public.intake.forms.personal.ce_experience_placeholder')}
            />
            <p className="mt-1 text-xs text-slate-500">{t('public.intake.forms.personal.ce_experience_eu_hint')}</p>
          </div>
          <div>
            <label className="flex items-center text-sm text-slate-700">
              {t('public.intake.forms.personal.intl_experience')} <RequiredBadge label={t('public.intake.forms.required')} active={intlAnswered} />
            </label>
            <select
              value={
                formData.experience.intl_experience === true
                  ? 'yes'
                  : formData.experience.intl_experience === false
                    ? 'no'
                    : ''
              }
              onChange={(e) =>
                updateExperience((current) => ({
                  ...current,
                  intl_experience: e.target.value === '' ? null : e.target.value === 'yes',
                }))
              }
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">{t('public.intake.forms.personal.intl_experience_options.default')}</option>
              <option value="yes">{t('public.intake.forms.personal.intl_experience_options.yes')}</option>
              <option value="no">{t('public.intake.forms.personal.intl_experience_options.no')}</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">{t('public.intake.forms.personal.intl_experience_hint')}</p>
          </div>
        </div>

        <MultiSelectChips
          label={t('public.intake.forms.experience.trailer_types')}
          options={TRAILER_OPTIONS}
          value={formData.experience.trailer_types ?? []}
          onChange={(val) =>
            updateExperience((current) => ({
              ...current,
              trailer_types: toggleInArray(current.trailer_types ?? [], val),
            }))
          }
        />

        <MultiSelectChips
          label={t('public.intake.forms.experience.route_types')}
          options={ROUTE_OPTIONS}
          value={formData.experience.route_types ?? []}
          onChange={(val) =>
            updateExperience((current) => ({
              ...current,
              route_types: toggleInArray(current.route_types ?? [], val),
            }))
          }
        />
      </div>
    ),
    employment: (
      <div className="space-y-4">
        <div className="space-y-4">
          {formData.employments.length === 0 && (
            <p className="text-sm text-slate-500">{t('public.intake.forms.employment.list_hint')}</p>
          )}
          <p className="text-xs text-slate-500">{t('public.intake.forms.employment.auto_save_hint')}</p>
          {formData.employments.map((emp, index) => (
            <div key={emp.id ?? index} className="rounded-xl border border-slate-200 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium text-slate-900">{emp.employer_name}</p>
                  <p className="text-sm text-slate-500">
                    {emp.position || 'Driver'} · {emp.country || '—'} · {emp.start_date} →{' '}
                    {emp.end_date || t('public.intake.forms.employment.current')}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button type="button" className="text-sm text-brand-600 hover:text-brand-700" onClick={() => startEditEmployment(index)}>
                    {t('public.intake.forms.employment.edit')}
                  </button>
                  <button type="button" className="text-sm text-red-500" onClick={() => removeEmployment(index)}>
                    {t('public.intake.forms.employment.delete')}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {formData.employments.length < 3 && (
          <form className="space-y-4 rounded-xl bg-slate-50 p-4" onSubmit={handleEmploymentSubmit}>
            <p className="text-sm font-medium text-slate-700">
              {editingIndex === null
                ? t('public.intake.forms.employment.form_title_add')
                : t('public.intake.forms.employment.form_title_edit', { values: { index: editingIndex + 1 } })}
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm text-slate-600">{t('public.intake.forms.employment.company')}</label>
                <input
                  type="text"
                  value={employmentDraft.employer_name}
                  onChange={(e) => setEmploymentDraft((prev) => ({ ...prev, employer_name: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="text-sm text-slate-600">{t('public.intake.forms.employment.country')}</label>
                <div className="mt-1 space-y-1">
                  <Select
                    options={countryOptions}
                    value={employmentDraft.country ?? ''}
                    onChange={(code) =>
                      setEmploymentDraft((prev) => ({ ...prev, country: code || '' }))
                    }
                    placeholder={t('public.intake.forms.employment.country_placeholder')}
                    className="w-full"
                  />
                  {employmentDraft.country && (
                    <button
                      type="button"
                      className="text-xs font-medium text-brand-600 hover:text-brand-700"
                      onClick={() => setEmploymentDraft((prev) => ({ ...prev, country: '' }))}
                    >
                      {t('common.actions.clear')}
                    </button>
                  )}
                </div>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm text-slate-600">{t('public.intake.forms.employment.position')}</label>
                <input
                  type="text"
                  value={employmentDraft.position ?? ''}
                  onChange={(e) => setEmploymentDraft((prev) => ({ ...prev, position: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                />
              </div>
              <div>
                <label className="text-sm text-slate-600">{t('public.intake.forms.employment.eu_routes')}</label>
                <select
                  value={employmentDraft.eu_routes ? 'yes' : 'no'}
                  onChange={(e) =>
                    setEmploymentDraft((prev) => ({ ...prev, eu_routes: e.target.value === 'yes' }))
                  }
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                >
                  <option value="yes">{t('public.intake.forms.employment.eu_routes_yes')}</option>
                  <option value="no">{t('public.intake.forms.employment.eu_routes_no')}</option>
                </select>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm text-slate-600">{t('public.intake.forms.employment.start')}</label>
                <input
                  type="date"
                  value={employmentDraft.start_date}
                  onChange={(e) => setEmploymentDraft((prev) => ({ ...prev, start_date: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="text-sm text-slate-600">{t('public.intake.forms.employment.end')}</label>
                <input
                  type="date"
                  value={employmentDraft.end_date ?? ''}
                  onChange={(e) => setEmploymentDraft((prev) => ({ ...prev, end_date: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                />
              </div>
            </div>

            <MultiSelectChips
              label={t('public.intake.forms.employment.trailers')}
              options={TRAILER_OPTIONS}
              value={employmentDraft.trailer_types ?? []}
              onChange={(val) =>
                setEmploymentDraft((prev) => ({
                  ...prev,
                  trailer_types: toggleInArray(prev.trailer_types ?? [], val),
                }))
              }
            />

            <MultiSelectChips
              label={t('public.intake.forms.employment.routes')}
              options={ROUTE_OPTIONS}
              value={employmentDraft.route_types ?? []}
              onChange={(val) =>
                setEmploymentDraft((prev) => ({
                  ...prev,
                  route_types: toggleInArray(prev.route_types ?? [], val),
                }))
              }
            />

            <div className="flex gap-2">
              <button type="submit" className="rounded-lg bg-brand-600 px-4 py-2 text-white shadow-sm transition hover:bg-brand-700">
                {editingIndex === null ? t('public.intake.forms.employment.add') : t('public.intake.forms.employment.save')}
              </button>
              {editingIndex !== null && (
                <button type="button" className="text-sm text-slate-500" onClick={cancelEmploymentEdit}>
                  {t('public.intake.forms.employment.cancel')}
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    ),
    documents: (
      <div className="space-y-4">
        <div className="rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-6 text-white shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <PublicLogo showWordmark={false} size={32} white />
            <p className="text-sm text-white/80">{t('public.intake.documents.upload_hint')}</p>
          </div>
          <div className="mt-4 grid gap-4 text-sm md:grid-cols-2">
            <div>
              <p className="text-lg font-semibold">{t('public.intake.documents.summary.title')}</p>
              <p className="text-white/80">{t('public.intake.documents.card_body')}</p>
            </div>
            <div className="rounded-2xl border border-white/30 bg-white/10 p-4">
              <p className="text-xs uppercase tracking-wide text-white/80">{t('public.intake.documents.summary.ready')}</p>
              <p className="text-2xl font-semibold">{readyOrUploadedCount}</p>
              <p className="text-xs text-white/80">
                {t('public.intake.documents.summary.subtitle', { values: { total: summaryStats.total || 0 } })}
              </p>
            </div>
          </div>
        </div>
        {summary && (
          <div className="rounded-2xl border border-brand-100 bg-white/95 p-5 shadow-sm">
            {checklistInitialized ? (
              <>
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold text-slate-900">
                    {t('public.intake.documents.summary.title')}
                  </p>
                  {summaryStats.total > 0 && (
                    <p className="text-xs text-slate-500">
                      {t('public.intake.documents.summary.subtitle', {
                        values: { total: summaryStats.total },
                      })}
                    </p>
                  )}
                </div>
                <div className="mt-3 grid gap-3 text-center sm:grid-cols-3">
                  <div className="rounded-xl bg-brand-50 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-700">
                      {t('public.intake.documents.summary.ready')}
                    </p>
                    <p className="text-lg font-semibold text-brand-900">{readyOrUploadedCount}</p>
                  </div>
                  <div className="rounded-xl bg-amber-50 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                      {t('public.intake.documents.summary.in_progress')}
                    </p>
                    <p className="text-lg font-semibold text-amber-900">{summaryStats.inProgress}</p>
                  </div>
                  <div className="rounded-xl bg-rose-50 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-rose-700">
                      {t('public.intake.documents.summary.missing')}
                    </p>
                    <p className="text-lg font-semibold text-rose-900">{summaryStats.missing}</p>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-slate-600">{t('public.intake.documents.checklist_pending')}</p>
            )}
          </div>
        )}
        <div className="space-y-4">
          {docCards.length === 0 && (
            <div className="rounded-2xl border border-dashed border-brand-100 bg-brand-50/60 p-4 text-sm text-brand-800">
              {t('public.intake.documents.checklist_pending')}
            </div>
          )}
          {docRequirements && docCards.length > 0 && (
            <div className="rounded-2xl border border-brand-100 bg-brand-50/70 p-4 text-sm text-brand-900">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-brand-700">
                {t('documents.requirements')}
              </div>
              {docRequirements.titles.map((title) => (
                <div key={title} className="font-semibold text-brand-900">
                  {title}
                </div>
              ))}
              {docRequirements.details.length > 0 && (
                <ul className="mt-2 list-disc pl-4 text-sm text-brand-900">
                  {docRequirements.details.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {docCards.map((card, idx) => {
            const normalizedCode = normalizeDocType(card.code)
            if (
              ['driver_license', 'qualification_code95', 'code95', 'code_95'].includes(normalizedCode) &&
              hideSplitLicenseDocs
            ) {
              return null
            }
            const requestedFrom = requestedFromText(card.meta, card.entry, t)
            const statusLabel = formatDocumentStatus(card.entry?.status, t, card.required)
            const title = getDocumentTitle(card.meta, card.code, locale)
            const response = docResponses[card.code] ?? (card.entry ? 'yes' : null)
            const currentFile = docFiles[card.code]
            const metaDescription = (card.meta as any)?.description as string | undefined
            const accent = card.required ? 'border-brand-200' : 'border-slate-200'
            const processType =
              (card.entry?.process_type as string | undefined) ||
              (card.meta as any)?.process_type ||
              (card.meta as any)?.processType
            const orderedAt = card.entry?.ordered_at || (card.meta as any)?.ordered_at
            const requestedFromOverride =
              processType && ['work_permit', 'red_paper'].includes(String(processType))
                ? t('public.intake.documents.process.employer_orderer')
                : requestedFrom
            const questionKey = (() => {
              if (normalizedCode === 'driver_license_code95') return 'public.intake.documents.questions.license_combo'
              if (['driver_license', 'qualification_code95', 'code95', 'code_95'].includes(normalizedCode)) {
                return 'public.intake.documents.questions.license_split'
              }
              if (normalizedCode === 'tachograph_card' || normalizedCode === 'tachograph') {
                return 'public.intake.documents.questions.tachograph'
              }
              if (normalizedCode === 'passport') return 'public.intake.documents.questions.passport'
              if (STAY_DOC_CODES.map((code) => normalizeDocType(code)).includes(normalizedCode)) {
                return 'public.intake.documents.questions.stay'
              }
              if (normalizedCode === 'voivodeship_decision' || normalizedCode === 'decyzja') {
                return 'public.intake.documents.questions.voivodeship'
              }
              if (normalizedCode === 'psych_tests' || normalizedCode === 'psychotest') {
                return 'public.intake.documents.questions.psych'
              }
              return null
            })()
            const question = questionKey ? t(questionKey) : null
            const showUploadField = question ? response === 'yes' : shouldRenderUploadField(card.required, response)
            return (
              <div
                key={`${card.code}-${idx}`}
                className={`space-y-3 rounded-2xl border bg-white/95 p-5 shadow-sm ${accent}`}
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-base font-semibold text-slate-900">{title}</p>
                    <p className="text-xs text-slate-500">
                      {card.required ? t('documents.required_tag') : t('documents.optional_tag')}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1 text-right text-xs text-slate-500">
                    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusTone(card.entry?.status)}`}>
                      {statusLabel}
                    </span>
                    {processType && ['work_permit', 'red_paper'].includes(String(processType)) && (
                      <span className="inline-flex rounded-full bg-blue-50 px-3 py-1 text-[11px] font-semibold text-blue-700">
                        {t(`public.intake.documents.process.${processType}.label`, { defaultValue: processType })}
                        {orderedAt
                          ? ` · ${t('public.intake.documents.process.ordered_at_short', {
                              values: { date: new Date(orderedAt).toLocaleDateString(locale) },
                            })}`
                          : ''}
                      </span>
                    )}
                    {card.entry?.download_url && (
                      <a
                        href={card.entry.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-brand-600 hover:text-brand-700 hover:underline"
                      >
                        {t('public.status_page.documents.open_file')}
                      </a>
                    )}
                  </div>
                </div>
                <div className="text-sm text-slate-600 space-y-1">
                  {question && <p className="font-semibold text-slate-800">{question}</p>}
                  {metaDescription && <p>{metaDescription}</p>}
                  {!card.required && <p className="text-xs text-slate-500">{t('public.intake.documents.optional_hint')}</p>}
                  {requestedFromOverride && (
                    <p className="text-xs text-slate-500">
                      {t('documents.labels.requested_from')}: <span className="font-semibold text-slate-700">{requestedFromOverride}</span>
                    </p>
                  )}
                  {processType && ['work_permit', 'red_paper'].includes(String(processType)) && (
                    <p className="text-xs text-slate-500">
                      {t(`public.intake.documents.process.activity.${processType}`, {
                        defaultValue: t('public.intake.documents.process.activity.default'),
                      })}
                    </p>
                  )}
                  {STAY_DOC_CODES.map((code) => normalizeDocType(code)).includes(normalizedCode) && (
                    <p className="text-xs text-slate-500">{t('public.intake.documents.stay_hint')}</p>
                  )}
                  {processType && ['work_permit', 'red_paper'].includes(String(processType)) && (
                    <p className="text-xs text-slate-500">
                      {t(`public.intake.documents.process.${processType}.label`, {
                        defaultValue: t('public.intake.documents.process.default'),
                      })}
                      {orderedAt
                        ? ` · ${t('public.intake.documents.process.ordered_at', {
                            values: { date: new Date(orderedAt).toLocaleDateString(locale) },
                          })}`
                        : ''}
                    </p>
                  )}
                </div>
                {(question || card.required) && response === null && (
                  <div className="rounded-xl border border-dashed border-brand-100 bg-brand-50/40 p-3 text-sm text-brand-900">
                    <p>{t('public.intake.documents.responses.waiting')}</p>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      <button
                        type="button"
                        onClick={() => handleDocumentResponse(card.code, 'yes')}
                        className="rounded-full border border-brand-200 px-3 py-1 text-brand-700 hover:bg-brand-50"
                      >
                        {t('public.intake.documents.responses.yes')}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDocumentResponse(card.code, 'no')}
                        className="rounded-full border border-brand-200 px-3 py-1 text-brand-700 hover:bg-brand-50"
                      >
                        {t('public.intake.documents.responses.no')}
                      </button>
                    </div>
                  </div>
                )}
                {card.required && response === 'no' && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                    <p className="font-medium">{t('public.intake.documents.responses.no_body')}</p>
                    <p>{t('public.intake.documents.responses.no_hint')}</p>
                  </div>
                )}
                {showUploadField && !card.meta?.orderable && renderUploadField(card.code, currentFile)}
                {card.meta?.orderable && (
                  <div className="rounded-xl border border-brand-100 bg-brand-50 p-3 text-xs text-brand-900">
                    {card.code === 'work_permit'
                      ? t('documents.work_permit.ordered')
                      : t('public.intake.documents.order_notice')}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    ),
    agreements: (
      <div className="space-y-4">
        <div className="space-y-5">
          <label className="flex items-start gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-brand-600"
              checked={generalConsent}
              onChange={(e) => updateAgreements({ general: e.target.checked })}
            />
            <span>
              {t('public.intake.forms.agreements.general')}{' '}
              <a href="/legal/rodo.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
                {t('public.portal.landing.footer.links.rodo', { defaultValue: 'RODO' })}
              </a>
              {' · '}
              <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
                {t('public.intake.forms.agreements.privacy_link')}
              </a>
              .
            </span>
          </label>
          <label className="flex items-start gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-brand-600"
              checked={employerConsent}
              onChange={(e) => updateAgreements({ employer_share: e.target.checked })}
            />
            <span>{t('public.intake.forms.agreements.employer_share')}</span>
          </label>
          <label className="flex items-start gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-brand-600"
              checked={termsAccepted}
              onChange={(e) => updateAgreements({ terms_acceptance: e.target.checked })}
            />
            <span>
              {t('public.intake.forms.agreements.terms')}{' '}
              <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
                {t('public.intake.forms.agreements.terms_link')}
              </a>{' '}
              ·{' '}
              <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
                {t('public.intake.forms.agreements.privacy_link')}
              </a>
            </span>
          </label>
          <p className="text-xs text-slate-500">{t('public.intake.forms.agreements.cookies_hint')}</p>
          <LegalLinksBlock className="mt-3" />
        </div>

        {!consentChecklistReady && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {t('public.intake.forms.agreements.validation')}
          </p>
        )}

        {state?.status === 'submitted' ? (
          <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            {state.submitted_at
              ? t('public.intake.forms.agreements.submitted', {
                  values: { datetime: new Date(state.submitted_at).toLocaleString(locale) },
                })
              : t('public.intake.forms.agreements.submit')}
          </div>
        ) : (
          <>
            {blockingReasons.length > 0 && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <p className="font-semibold">{t('public.intake.validations.blocked_title')}</p>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {blockingReasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
            {docWarningReasons.length > 0 && (
              <div className="rounded-xl border border-brand-100 bg-brand-50 p-4 text-sm text-brand-900">
                <p className="font-semibold">{t('public.intake.validations.documents.warning_title')}</p>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {docWarningReasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
            <button
              type="button"
              disabled={!canSubmitApplication}
              onClick={() =>
                submit({
                  consents: {
                    general: generalConsent,
                    employer_share: employerConsent,
                    terms_acceptance: termsAccepted,
                  },
                  documents_version: CONSENT_DOCUMENT_VERSIONS,
                  cookies_accepted: cookieReady,
                })
              }
              className="rounded-lg bg-brand-600 px-4 py-3 text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {submitting ? t('public.intake.forms.agreements.submitting') : t('public.intake.forms.agreements.submit')}
            </button>
          </>
        )}
      </div>
    ),
  }

  return (
    <PublicPageShell maxWidth="5xl" headerExtra={<PublicLocaleSwitcher />}>
      <div className="rounded-3xl border border-brand-50 bg-white/95 p-6 shadow-card">
        <div className="mb-6 rounded-2xl border border-brand-100 bg-brand-50/40 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <PublicLogo showWordmark={false} className="text-brand-700" size={28} />
              <div>
                <h1 className="text-xl font-semibold text-slate-900">{t('public.intake.title')}</h1>
                {state?.expires_at && (
                  <p className="text-xs text-slate-600">
                    {t('public.status_page.expires_at', {
                      values: { date: new Date(state.expires_at).toLocaleDateString(locale) },
                    })}
                  </p>
                )}
              </div>
            </div>
            <div className="text-right text-xs text-brand-700">
              {saving ? t('common.saving') : t('public.intake.autosave_hint')}
            </div>
          </div>
        </div>
        <div className="mb-6 flex flex-col gap-3 rounded-2xl bg-gradient-to-r from-brand-50 via-white to-brand-100/70 p-5 ring-1 ring-brand-100">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
                {t('public.intake.guided.next_step')}
              </p>
              <p className="text-lg font-semibold text-slate-900">{nextStepLabel}</p>
              <p className="text-sm text-slate-600">{t('public.intake.guided.next_step_hint')}</p>
            </div>
            <button
              type="button"
              onClick={() => goToStep(nextSuggestedStep)}
              className="rounded-full bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-lg transition hover:translate-y-[-1px] hover:bg-brand-700"
            >
              {t('public.intake.guided.start_step')}
            </button>
          </div>
        </div>

        {statusCards.length > 0 && (
          <div className="mb-6">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-brand-700">
              {t('public.intake.status_cards.subtitle')}
            </p>
            <div className="grid gap-3 md:grid-cols-3">
              {statusCards.map((card) => {
                const idx = steps.findIndex((step) => step.key === card.step.key) + 1
                const toneText =
                  card.type === 'done'
                    ? t('public.intake.status_cards.completed')
                    : card.type === 'next'
                      ? t('public.intake.status_cards.next')
                      : t('public.intake.status_cards.current')
                return (
                  <div
                    key={`${card.type}-${card.step.key}`}
                    className="rounded-2xl border border-brand-100 bg-brand-50/70 p-4"
                  >
                    <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">{toneText}</p>
                    <p className="text-base font-semibold text-slate-900">{card.step.label}</p>
                    <p className="text-xs text-slate-600">
                      {t('public.intake.status_cards.step_hint', {
                        values: { index: idx, total: steps.length },
                      })}
                    </p>
                  </div>
                )
              })}
            </div>
            <div className="mt-4 space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-600">
                <span>{t('public.intake.status_cards.progress_label')}</span>
                <span>{progressPercent}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-brand-500 transition-all"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          </div>
        )}

        <div className="mb-6 flex flex-wrap gap-2">
          {steps.map((step) => (
            <button
              key={step.key}
              className={`rounded-full px-4 py-2 text-sm ${
                step.key === activeStep ? 'bg-brand-600 text-white shadow-sm' : 'bg-slate-100 text-slate-600'
              }`}
              onClick={() => goToStep(step.key)}
            >
              {step.label}
            </button>
          ))}
        </div>

        {error && <p className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>}
        {loading && !state ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : state ? (
          <div>{stepContent[activeStep]}</div>
        ) : (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {t('public.intake.errors.invalid_link')}{' '}
            <Link className="underline" to="/public/intake">
              {t('public.intake.placeholder.resume_hint')}
            </Link>
          </div>
        )}

        <div className="mt-8 flex items-center justify-between">
          <button
            type="button"
            disabled={currentStepIndex === 0}
            onClick={() => changeStep('prev')}
            className="rounded-lg px-4 py-2 text-sm text-slate-600 disabled:opacity-50"
          >
            {t('public.intake.cta.prev')}
          </button>
          <button
            type="button"
            disabled={currentStepIndex === steps.length - 1}
            onClick={() => changeStep('next')}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm text-white shadow-sm transition hover:bg-brand-700 disabled:bg-slate-300"
          >
            {t('public.intake.cta.next')}
          </button>
        </div>
      </div>
    </PublicPageShell>
  )
}

type MultiSelectProps = {
  label: string
  options: MultiSelectOption[]
  value: string[]
  onChange: (value: string) => void
}

function MultiSelectChips({ label, options, value, onChange }: MultiSelectProps) {
  const { t } = useI18n()
  return (
    <div>
      <p className="text-sm text-slate-600">{label}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((opt) => {
          const active = value.includes(opt.value)
          return (
            <button
              type="button"
              key={opt.value}
              onClick={() => onChange(opt.value)}
              className={`rounded-full px-3 py-1 text-xs ${
                active ? 'bg-brand-600 text-white shadow-sm' : 'bg-slate-200 text-slate-700'
              }`}
            >
              {t(opt.labelKey)}
            </button>
          )
        })}
      </div>
    </div>
  )
}

type OverviewStatCardProps = {
  title: string
  value: string
  description?: string
  accent?: 'default' | 'success' | 'warning'
}

function OverviewStatCard({ title, value, description, accent = 'default' }: OverviewStatCardProps) {
  const accentClasses =
    accent === 'success'
      ? 'border-green-200 bg-green-50 text-green-900'
      : accent === 'warning'
        ? 'border-amber-200 bg-amber-50 text-amber-900'
        : 'border-brand-50 bg-white text-slate-900'
  return (
    <div className={`rounded-2xl border ${accentClasses} p-4`}>
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
    </div>
  )
}
