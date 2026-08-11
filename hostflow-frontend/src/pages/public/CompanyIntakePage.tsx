import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { getCompanyIntakeConfig, submitCompanyIntake } from '../../api/companyIntake'
import { ConsentRow } from '../../components/public/ConsentRow'
import { InlineFieldError } from '../../components/forms/InlineFieldError'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { type LocaleCode, useI18n } from '../../i18n'
import { fieldControlClass, focusFirstInvalid } from '../../utils/formFieldValidation'
import { getLanguageDisplayName } from '../../utils/catalogLocale'
import { PublicPageShell } from './components/PublicPageShell'

type StepId =
  | 'language'
  | 'company'
  | 'need'
  | 'base'
  | 'transport'
  | 'fleet'
  | 'timing'
  | 'work'
  | 'trailer'
  | 'compensation'
  | 'contact'
  | 'review'

type CompanyForm = {
  language: LocaleCode
  company: {
    name: string
    tax_id: string
    country: string
    country_code: string
    city: string
    website: string
    fleet_size: string
    transport_type: '' | 'international' | 'domestic' | 'mixed'
  }
  contact: {
    full_name: string
    role: string
    email: string
    phone: string
    whatsapp: boolean
  }
  need: {
    what_needed: string
    people_count: string
    needed_when: string
    cooperation_type: string
    candidate_countries: string[]
    requirements: string
  }
  terms: {
    base_location: string
    schedule: string[]
    night_driving: string
    route_directions: string[]
    truck_brands: string[]
    body_types: string[]
    rate_amount: string
    rate_currency: string
    rate_period: string
    rate_tax_mode: string
    additional: string
  }
  consent: {
    terms_accepted: boolean
    privacy_accepted: boolean
    data_processing_accepted: boolean
    accuracy_confirmed: boolean
    marketing_contact_accepted: boolean
  }
}

type Option = { value: string; label: string }

const STEPS: StepId[] = [
  'language',
  'company',
  'need',
  'base',
  'transport',
  'fleet',
  'timing',
  'work',
  'trailer',
  'compensation',
  'contact',
  'review',
]

const ALL_LANGUAGE_OPTIONS: Array<{ value: LocaleCode; label: string }> = (
  ['pl', 'en', 'ru'] as const
).map((value) => {
  const raw = getLanguageDisplayName(value, value)
  const label = raw ? raw.charAt(0).toUpperCase() + raw.slice(1) : value
  return { value, label }
})

const INITIAL_FORM: CompanyForm = {
  language: 'pl',
  company: {
    name: '',
    tax_id: '',
    country: 'Poland',
    country_code: 'PL',
    city: '',
    website: '',
    fleet_size: '',
    transport_type: '',
  },
  contact: {
    full_name: '',
    role: '',
    email: '',
    phone: '',
    whatsapp: true,
  },
  need: {
    what_needed: '',
    people_count: '',
    needed_when: '',
    cooperation_type: '',
    candidate_countries: [],
    requirements: '',
  },
  terms: {
    base_location: '',
    schedule: [],
    night_driving: '',
    route_directions: [],
    truck_brands: [],
    body_types: [],
    rate_amount: '',
    rate_currency: 'EUR',
    rate_period: 'day',
    rate_tax_mode: 'netto',
    additional: '',
  },
  consent: {
    terms_accepted: false,
    privacy_accepted: false,
    data_processing_accepted: false,
    accuracy_confirmed: false,
    marketing_contact_accepted: false,
  },
}

function optionalText(value: string): string | undefined {
  const trimmed = value.trim()
  return trimmed || undefined
}

function numberFromChoice(value: string): number | undefined {
  const trimmed = value.trim()
  if (!trimmed) return undefined
  const match = trimmed.match(/\d+/g)
  if (!match?.length) return undefined
  const parsed = Number(match[match.length - 1])
  return Number.isFinite(parsed) ? parsed : undefined
}

function companyIntakeSourceFromContext(context: Record<string, unknown>): string {
  const raw = String(context.utm_source || '').trim().toLowerCase()
  if (['meta', 'facebook', 'instagram', 'fb', 'ig'].includes(raw)) return 'meta_ads'
  return 'company_intake_form'
}

function buildSourceContext(): Record<string, unknown> {
  if (typeof window === 'undefined') return { page: 'company_intake' }
  const params = new URLSearchParams(window.location.search)
  const context: Record<string, unknown> = {
    page: 'company_intake',
    landing_page: window.location.href,
    referrer: document.referrer || undefined,
    device: window.innerWidth < 768 ? 'mobile' : 'desktop',
  }
  ;['source', 'campaign', 'utm_source', 'utm_campaign', 'utm_adset', 'utm_ad', 'fbclid'].forEach((key) => {
    const value = params.get(key)?.trim()
    if (value) context[key] = value
  })
  return context
}

function toggleList(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value]
}

function countryCodeFor(country: string): string {
  const map: Record<string, string> = {
    Poland: 'PL',
    Germany: 'DE',
    'Czech Republic': 'CZ',
    Lithuania: 'LT',
  }
  return map[country] || ''
}

function Field({
  label,
  children,
  error,
}: {
  label: string
  children: JSX.Element
  error?: string | null
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <div className="mt-1">{children}</div>
      <InlineFieldError message={error} />
    </label>
  )
}

function ChoiceGrid({
  options,
  value,
  onChange,
  columns = 'sm:grid-cols-2',
}: {
  options: Option[]
  value: string
  onChange: (value: string) => void
  columns?: string
}) {
  return (
    <div className={`grid gap-3 ${columns}`}>
      {options.map((option) => {
        const active = value === option.value
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`min-h-12 rounded-md border px-4 py-3 text-left text-sm font-medium transition ${
              active
                ? 'border-brand-600 bg-brand-50 text-brand-900 shadow-sm'
                : 'border-slate-200 bg-white text-slate-800 hover:border-brand-300'
            }`}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

function MultiChoiceGrid({
  options,
  value,
  onChange,
}: {
  options: Option[]
  value: string[]
  onChange: (next: string[]) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const active = value.includes(option.value)
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(toggleList(value, option.value))}
            className={`rounded-full border px-4 py-2 text-sm font-medium ${
              active
                ? 'border-brand-600 bg-brand-50 text-brand-900'
                : 'border-slate-200 bg-white text-slate-700 hover:border-brand-300'
            }`}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

export default function CompanyIntakePage() {
  const { publicToken } = useParams()
  const { locale, setLocale, t } = useI18n()
  const [form, setForm] = useState<CompanyForm>({ ...INITIAL_FORM, language: locale })
  const [stepIndex, setStepIndex] = useState(0)
  const [loading, setLoading] = useState(false)
  const [configLoading, setConfigLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [showConsentErrors, setShowConsentErrors] = useState(false)
  const companyNameRef = useRef<HTMLInputElement>(null)
  const contactNameRef = useRef<HTMLInputElement>(null)
  const contactEmailRef = useRef<HTMLInputElement>(null)
  const contactPhoneRef = useRef<HTMLInputElement>(null)
  const consentTermsRef = useRef<HTMLInputElement>(null)
  const consentPrivacyRef = useRef<HTMLInputElement>(null)
  const consentDataRef = useRef<HTMLInputElement>(null)
  const consentAccuracyRef = useRef<HTMLInputElement>(null)
  const [submittedLeadId, setSubmittedLeadId] = useState<string | null>(null)
  const [supportedLanguages, setSupportedLanguages] = useState<LocaleCode[]>([])
  const [configuredSource, setConfiguredSource] = useState<string | null>(null)
  const sourceContext = useMemo(() => buildSourceContext(), [])
  const leadSource = useMemo(() => companyIntakeSourceFromContext(sourceContext), [sourceContext])
  const languageOptions = useMemo(
    () => ALL_LANGUAGE_OPTIONS.filter((option) => supportedLanguages.includes(option.value)),
    [supportedLanguages],
  )

  const currentStep = STEPS[stepIndex]
  const progress = Math.round(((stepIndex + 1) / STEPS.length) * 100)
  const inputClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100'
  const textareaClass = `${inputClass} min-h-28 resize-y`

  useSeoMeta({
    title: t('public.company_intake.seo.title', { defaultValue: 'Company intake — HostFlow' }),
    description: t('public.company_intake.seo.description', {
      defaultValue: 'Submit transport company details and hiring needs to HostFlow.',
    }),
    canonicalPath: publicToken ? `/forms/company-intake/${publicToken}` : '/forms/company-intake',
  })

  const setLanguage = useCallback((next: LocaleCode) => {
    setLocale(next)
    setForm((prev) => ({ ...prev, language: next }))
  }, [setLocale])

  useEffect(() => {
    if (!publicToken) return
    let cancelled = false
    setConfigLoading(true)
    getCompanyIntakeConfig(publicToken)
      .then((config) => {
        if (cancelled) return
        const allowed = (config.supported_languages || []).filter((code): code is LocaleCode => code === 'pl' || code === 'en' || code === 'ru')
        const nextSupported = allowed.length ? allowed : ['pl', 'en', 'ru']
        const nextDefault = nextSupported.includes(config.default_language) ? config.default_language : nextSupported[0]
        setSupportedLanguages(nextSupported)
        setConfiguredSource(config.source || null)
        setLanguage(nextDefault)
      })
      .catch(() => {
        if (cancelled) return
        setSupportedLanguages(['pl', 'en', 'ru'])
        setConfiguredSource(null)
        setError(t('public.company_intake.errors.config_failed', { defaultValue: 'Could not load intake link settings. Please refresh the page.' }))
      })
      .finally(() => {
        if (!cancelled) setConfigLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [publicToken, setLanguage, t])

  if (!publicToken) return <Navigate to="/public" replace />

  const needOptions: Option[] = [
    { value: 'drivers_ce', label: t('public.company_intake.quiz.need.drivers_ce', { defaultValue: 'C+E drivers' }) },
    { value: 'warehouse_workers', label: t('public.company_intake.quiz.need.warehouse', { defaultValue: 'Warehouse workers' }) },
    { value: 'mechanics', label: t('public.company_intake.quiz.need.mechanics', { defaultValue: 'Mechanics' }) },
    { value: 'other', label: t('public.company_intake.quiz.need.other', { defaultValue: 'Other' }) },
  ]
  const countOptions: Option[] = ['1-2', '3-5', '6-10', '10+'].map((value) => ({ value, label: value }))
  const timingOptions: Option[] = [
    { value: 'asap', label: t('public.company_intake.quiz.timing.asap', { defaultValue: 'ASAP' }) },
    { value: 'week', label: t('public.company_intake.quiz.timing.week', { defaultValue: 'Within a week' }) },
    { value: 'month', label: t('public.company_intake.quiz.timing.month', { defaultValue: 'Within a month' }) },
    { value: 'research', label: t('public.company_intake.quiz.timing.research', { defaultValue: 'Researching the market' }) },
  ]
  const transportOptions: Option[] = [
    { value: 'international', label: t('public.company_intake.transport.international', { defaultValue: 'International' }) },
    { value: 'domestic', label: t('public.company_intake.transport.domestic', { defaultValue: 'Domestic' }) },
    { value: 'mixed', label: t('public.company_intake.transport.mixed', { defaultValue: 'Mixed' }) },
  ]
  const fleetOptions: Option[] = ['1-5', '6-20', '21-50', '50+'].map((value) => ({ value, label: value }))
  const cooperationOptions: Option[] = [
    { value: 'recruitment', label: t('public.company_intake.quiz.cooperation.recruitment', { defaultValue: 'Recruitment' }) },
    { value: 'staff_rental', label: t('public.company_intake.quiz.cooperation.rental', { defaultValue: 'Staff rental' }) },
    { value: 'hr_support', label: t('public.company_intake.quiz.cooperation.hr', { defaultValue: 'HR support' }) },
  ]
  const countryOptions: Option[] = ['Poland', 'Germany', 'Czech Republic', 'Lithuania'].map((value) => ({ value, label: value }))
  const scheduleOptions: Option[] = ['2/1', '3/1', '4/1', '6/2', '8/2'].map((value) => ({ value, label: value })).concat([
    { value: 'monday_friday', label: t('public.company_intake.options.work_system.monday_friday', { defaultValue: 'Monday-Friday' }) },
    { value: 'weekends_home', label: t('public.company_intake.options.work_system.weekends_home', { defaultValue: 'Weekends at home' }) },
    { value: 'to_agree', label: t('public.company_intake.options.work_system.to_agree', { defaultValue: 'To be agreed' }) },
    { value: 'other', label: t('public.company_intake.options.work_system.other', { defaultValue: 'Other system' }) },
  ])
  const routeOptions: Option[] = [
    'poland',
    'germany',
    'france',
    'benelux',
    'scandinavia',
    'spain_portugal',
    'italy',
    'czech_slovakia',
    'baltics',
    'uk',
    'eu_international',
    'domestic',
    'other',
  ].map((value) => ({ value, label: t(`public.company_intake.options.routes.${value}`, { defaultValue: value }) }))
  const nightDrivingOptions: Option[] = [
    { value: 'yes', label: t('common.yes', { defaultValue: 'Yes' }) },
    { value: 'no', label: t('common.no', { defaultValue: 'No' }) },
    { value: 'occasional', label: t('public.company_intake.options.night_driving.occasional', { defaultValue: 'Occasionally' }) },
  ]
  const truckOptions: Option[] = ['MAN', 'Mercedes', 'Volvo', 'Scania', 'DAF', 'Iveco'].map((value) => ({ value, label: value }))
  const bodyOptions: Option[] = [
    { value: 'curtain', label: t('public.company_intake.quiz.body.curtain', { defaultValue: 'Curtain' }) },
    { value: 'frigo', label: t('public.company_intake.quiz.body.frigo', { defaultValue: 'Refrigerated' }) },
    { value: 'jumbo', label: 'Jumbo' },
    { value: 'container', label: t('public.company_intake.quiz.body.container', { defaultValue: 'Container' }) },
    { value: 'adr', label: 'ADR' },
    { value: 'tanker', label: t('public.company_intake.options.cargo.tanker', { defaultValue: 'Tanker' }) },
    { value: 'other', label: t('public.company_intake.options.cargo.other', { defaultValue: 'Other' }) },
  ]
  const ratePeriodOptions: Option[] = ['day', 'month', 'kilometer', 'hour'].map((value) => ({
    value,
    label: t(`public.company_intake.options.rate_period.${value}`, { defaultValue: value }),
  }))
  const rateTaxOptions: Option[] = [
    { value: 'netto', label: 'Netto' },
    { value: 'brutto', label: 'Brutto' },
    { value: 'b2b', label: 'B2B' },
  ]

  const allRequiredConsentsAccepted =
    form.consent.terms_accepted &&
    form.consent.privacy_accepted &&
    form.consent.data_processing_accepted &&
    form.consent.accuracy_confirmed

  const requiredMsg = t('public.company_intake.errors.field_required', {
    defaultValue: 'Заполните это поле',
  })
  const contactReachMsg = t('public.company_intake.errors.contact_reach', {
    defaultValue: 'Укажите email или телефон — хотя бы одно',
  })
  const consentMsg = t('public.company_intake.errors.consent_field', {
    defaultValue: 'Отметьте это согласие, чтобы отправить анкету',
  })

  const validateCurrentStep = (): boolean => {
    const next: Record<string, string> = {}
    if (currentStep === 'company') {
      if (!form.company.name.trim()) next.company_name = requiredMsg
    }
    if (currentStep === 'contact') {
      if (!form.contact.full_name.trim()) next.contact_name = requiredMsg
      if (!form.contact.email.trim() && !form.contact.phone.trim()) {
        next.contact_email = contactReachMsg
        next.contact_phone = contactReachMsg
      }
    }
    setFieldErrors(next)
    if (Object.keys(next).length === 0) return true
    focusFirstInvalid([
      next.company_name ? companyNameRef.current : null,
      next.contact_name ? contactNameRef.current : null,
      next.contact_email ? contactEmailRef.current : null,
      next.contact_phone ? contactPhoneRef.current : null,
    ])
    return false
  }

  const validateConsents = (): boolean => {
    setShowConsentErrors(true)
    if (allRequiredConsentsAccepted) return true
    focusFirstInvalid([
      !form.consent.terms_accepted ? consentTermsRef.current : null,
      !form.consent.privacy_accepted ? consentPrivacyRef.current : null,
      !form.consent.data_processing_accepted ? consentDataRef.current : null,
      !form.consent.accuracy_confirmed ? consentAccuracyRef.current : null,
    ])
    return false
  }

  const clearFieldError = (key: string) => {
    setFieldErrors((prev) => {
      if (!prev[key]) return prev
      const copy = { ...prev }
      delete copy[key]
      return copy
    })
  }

  const toggleAllRequiredConsents = (checked: boolean) => {
    setForm((prev) => ({
      ...prev,
      consent: {
        ...prev.consent,
        terms_accepted: checked,
        privacy_accepted: checked,
        data_processing_accepted: checked,
        accuracy_confirmed: checked,
      },
    }))
    if (checked) setShowConsentErrors(false)
  }

  const goNext = () => {
    if (!validateCurrentStep()) return
    setError(null)
    setStepIndex((idx) => Math.min(idx + 1, STEPS.length - 1))
  }

  const goBack = () => {
    setError(null)
    setFieldErrors({})
    setStepIndex((idx) => Math.max(idx - 1, 0))
  }

  const goToStep = (step: StepId) => {
    setError(null)
    setFieldErrors({})
    setStepIndex(STEPS.indexOf(step))
  }

  const update = <Group extends keyof Omit<CompanyForm, 'language'>, Field extends keyof CompanyForm[Group]>(
    group: Group,
    field: Field,
    value: CompanyForm[Group][Field],
  ) => {
    setForm((prev) => ({ ...prev, [group]: { ...prev[group], [field]: value } }))
  }

  const updateConsent = (field: keyof CompanyForm['consent'], value: boolean) => {
    setForm((prev) => ({ ...prev, consent: { ...prev.consent, [field]: value } }))
    if (value) setShowConsentErrors(false)
  }

  const updateBaseCountry = (country: string) => {
    setForm((prev) => ({
      ...prev,
      company: {
        ...prev.company,
        country,
        country_code: countryCodeFor(country),
      },
    }))
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    // Re-validate contact/company if user jumped to review via edit links.
    const contactOk =
      Boolean(form.contact.full_name.trim()) &&
      Boolean(form.contact.email.trim() || form.contact.phone.trim())
    const companyOk = Boolean(form.company.name.trim())
    if (!companyOk || !contactOk) {
      const next: Record<string, string> = {}
      if (!companyOk) next.company_name = requiredMsg
      if (!form.contact.full_name.trim()) next.contact_name = requiredMsg
      if (!form.contact.email.trim() && !form.contact.phone.trim()) {
        next.contact_email = contactReachMsg
        next.contact_phone = contactReachMsg
      }
      setFieldErrors(next)
      if (!companyOk) goToStep('company')
      else goToStep('contact')
      return
    }
    if (!validateConsents()) return
    setLoading(true)
    setError(null)
    try {
      const response = await submitCompanyIntake(publicToken, {
        company: {
          name: form.company.name.trim(),
          tax_id: optionalText(form.company.tax_id),
          country: optionalText(form.company.country),
          country_code: optionalText(form.company.country_code)?.toUpperCase(),
          city: optionalText(form.company.city),
          website: optionalText(form.company.website),
          fleet_size: numberFromChoice(form.company.fleet_size),
          transport_type: form.company.transport_type || undefined,
        },
        contact: {
          full_name: form.contact.full_name.trim(),
          role: optionalText(form.contact.role),
          email: optionalText(form.contact.email),
          phone: optionalText(form.contact.phone),
          whatsapp: form.contact.whatsapp,
        },
        need: {
          what_needed: optionalText(form.need.what_needed),
          people_count: numberFromChoice(form.need.people_count),
          needed_when: optionalText(form.need.needed_when),
          cooperation_type: optionalText(form.need.cooperation_type),
          candidate_countries: [],
          requirements: optionalText(form.need.requirements),
        },
        terms: {
          rate: optionalText(form.terms.rate_amount)
            ? optionalText([form.terms.rate_amount, form.terms.rate_currency, form.terms.rate_period, form.terms.rate_tax_mode].filter(Boolean).join(' '))
            : undefined,
          rate_amount: optionalText(form.terms.rate_amount),
          rate_currency: optionalText(form.terms.rate_currency),
          rate_period: optionalText(form.terms.rate_period),
          rate_tax_mode: optionalText(form.terms.rate_tax_mode),
          schedule: optionalText(form.terms.schedule.join(', ')),
          work_systems: form.terms.schedule,
          night_driving: optionalText(form.terms.night_driving),
          route_directions: form.terms.route_directions,
          cargo_types: form.terms.body_types,
          body_types: form.terms.body_types,
          work_conditions: form.terms.night_driving ? [`night_driving:${form.terms.night_driving}`] : [],
          base_location: optionalText(form.terms.base_location),
          truck_brands: form.terms.truck_brands,
          body_type: optionalText(form.terms.body_types.join(', ')),
          additional: optionalText(form.terms.additional),
        },
        consent: {
          ...form.consent,
          terms_version: '2026-06-16',
          privacy_version: '2026-06-16',
        },
        source: configuredSource || leadSource,
        service_intent: optionalText(form.need.cooperation_type),
        language: form.language,
        source_context: { ...sourceContext, language: form.language, form_id: `company-intake:${publicToken}` },
      })
      setSubmittedLeadId(response.lead_id)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setError(
        typeof detail === 'string' && detail.trim()
          ? detail
          : t('public.company_intake.errors.submit_failed', { defaultValue: 'Could not submit the intake form. Please try again.' }),
      )
    } finally {
      setLoading(false)
    }
  }

  const summaryRows = [
    { label: t('public.company_intake.summary.company', { defaultValue: 'Company' }), value: form.company.name || '-', step: 'company' as StepId },
    { label: t('public.company_intake.summary.contact', { defaultValue: 'Contact' }), value: form.contact.full_name || '-', step: 'contact' as StepId },
    { label: t('public.company_intake.summary.need', { defaultValue: 'Need' }), value: [form.need.people_count, needOptions.find((item) => item.value === form.need.what_needed)?.label || form.need.what_needed].filter(Boolean).join(' ') || '-', step: 'need' as StepId },
    { label: t('public.company_intake.summary.base', { defaultValue: 'Base' }), value: [form.company.country, form.company.city].filter(Boolean).join(', ') || '-', step: 'base' as StepId },
    { label: t('public.company_intake.summary.transport', { defaultValue: 'Transport' }), value: transportOptions.find((item) => item.value === form.company.transport_type)?.label || '-', step: 'transport' as StepId },
    { label: t('public.company_intake.summary.timing', { defaultValue: 'Timing' }), value: timingOptions.find((item) => item.value === form.need.needed_when)?.label || '-', step: 'timing' as StepId },
    { label: t('public.company_intake.quiz.steps.work', { defaultValue: 'Work' }), value: form.terms.schedule.join(', ') || '-', step: 'work' as StepId },
    { label: t('public.company_intake.quiz.steps.trailer', { defaultValue: 'Trailer / transport' }), value: form.terms.body_types.join(', ') || '-', step: 'trailer' as StepId },
  ]

  if (configLoading) {
    return (
      <PublicPageShell maxWidth="3xl" headerExtra={null}>
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm font-medium text-slate-600">{t('common.loading', { defaultValue: 'Loading...' })}</p>
        </div>
      </PublicPageShell>
    )
  }

  if (submittedLeadId) {
    return (
      <PublicPageShell maxWidth="xl" headerExtra={<PublicLocaleSwitcher options={supportedLanguages.length ? supportedLanguages : [form.language]} />}>
        <div className="rounded-lg border border-emerald-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm font-semibold uppercase text-emerald-700">
            {t('public.company_intake.success.kicker', { defaultValue: 'Submitted' })}
          </p>
          <h1 className="mt-3 text-2xl font-semibold text-slate-900">
            {t('public.company_intake.success.title')}
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            {t('public.company_intake.success.body')}
          </p>
          <p className="mt-5 rounded-md bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
            {t('public.company_intake.success.reference', { defaultValue: 'Request number' })}: {submittedLeadId}
          </p>
        </div>
      </PublicPageShell>
    )
  }

  const renderStep = () => {
    switch (currentStep) {
      case 'language':
        return (
          <ChoiceGrid
            columns="sm:grid-cols-3"
            options={languageOptions}
            value={form.language}
            onChange={(value) => setLanguage(value as LocaleCode)}
          />
        )
      case 'need':
        return (
          <div className="space-y-5">
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">{t('public.company_intake.fields.need_type', { defaultValue: 'Who are you looking for?' })}</p>
              <ChoiceGrid options={needOptions} value={form.need.what_needed} onChange={(value) => update('need', 'what_needed', value)} />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">{t('public.company_intake.fields.people_count', { defaultValue: 'How many people?' })}</p>
              <ChoiceGrid options={countOptions} value={form.need.people_count} onChange={(value) => update('need', 'people_count', value)} />
            </div>
          </div>
        )
      case 'base':
        return (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('public.company_intake.fields.country', { defaultValue: 'Country' })}>
              <select className={inputClass} value={form.company.country} onChange={(e) => updateBaseCountry(e.target.value)}>
                {countryOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </Field>
            <Field label={t('public.company_intake.fields.city', { defaultValue: 'City' })}>
              <input className={inputClass} value={form.company.city} onChange={(e) => update('company', 'city', e.target.value)} />
            </Field>
          </div>
        )
      case 'transport':
        return <ChoiceGrid options={transportOptions} value={form.company.transport_type} onChange={(value) => update('company', 'transport_type', value as CompanyForm['company']['transport_type'])} />
      case 'fleet':
        return <ChoiceGrid options={fleetOptions} value={form.company.fleet_size} onChange={(value) => update('company', 'fleet_size', value)} />
      case 'timing':
        return (
          <div className="space-y-5">
            <ChoiceGrid options={timingOptions} value={form.need.needed_when} onChange={(value) => update('need', 'needed_when', value)} />
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">{t('public.company_intake.fields.cooperation_type', { defaultValue: 'Cooperation type' })}</p>
              <ChoiceGrid options={cooperationOptions} value={form.need.cooperation_type} onChange={(value) => update('need', 'cooperation_type', value)} />
            </div>
          </div>
        )
      case 'contact':
        return (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label={t('public.company_intake.fields.contact_name', { defaultValue: 'Name' })}
              error={fieldErrors.contact_name}
            >
              <input
                ref={contactNameRef}
                className={fieldControlClass(inputClass, Boolean(fieldErrors.contact_name))}
                aria-invalid={fieldErrors.contact_name ? true : undefined}
                value={form.contact.full_name}
                onChange={(e) => {
                  update('contact', 'full_name', e.target.value)
                  clearFieldError('contact_name')
                }}
              />
            </Field>
            <Field label={t('public.company_intake.fields.role', { defaultValue: 'Role' })}>
              <input className={inputClass} value={form.contact.role} onChange={(e) => update('contact', 'role', e.target.value)} />
            </Field>
            <Field
              label={t('public.company_intake.fields.email', { defaultValue: 'Email' })}
              error={fieldErrors.contact_email}
            >
              <input
                ref={contactEmailRef}
                className={fieldControlClass(inputClass, Boolean(fieldErrors.contact_email))}
                type="email"
                aria-invalid={fieldErrors.contact_email ? true : undefined}
                value={form.contact.email}
                onChange={(e) => {
                  update('contact', 'email', e.target.value)
                  clearFieldError('contact_email')
                  clearFieldError('contact_phone')
                }}
              />
            </Field>
            <Field
              label={t('public.company_intake.fields.phone', { defaultValue: 'Phone' })}
              error={fieldErrors.contact_phone}
            >
              <input
                ref={contactPhoneRef}
                className={fieldControlClass(inputClass, Boolean(fieldErrors.contact_phone))}
                aria-invalid={fieldErrors.contact_phone ? true : undefined}
                value={form.contact.phone}
                onChange={(e) => {
                  update('contact', 'phone', e.target.value)
                  clearFieldError('contact_phone')
                  clearFieldError('contact_email')
                }}
              />
            </Field>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input type="checkbox" checked={form.contact.whatsapp} onChange={(e) => update('contact', 'whatsapp', e.target.checked)} />
              {t('public.company_intake.fields.whatsapp', { defaultValue: 'WhatsApp available' })}
            </label>
          </div>
        )
      case 'company':
        return (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label={t('public.company_intake.fields.company_name', { defaultValue: 'Company name' })}
              error={fieldErrors.company_name}
            >
              <input
                ref={companyNameRef}
                className={fieldControlClass(inputClass, Boolean(fieldErrors.company_name))}
                aria-invalid={fieldErrors.company_name ? true : undefined}
                value={form.company.name}
                onChange={(e) => {
                  update('company', 'name', e.target.value)
                  clearFieldError('company_name')
                }}
              />
            </Field>
            <Field label={t('public.company_intake.fields.tax_id', { defaultValue: 'NIP / VAT' })}>
              <input className={inputClass} value={form.company.tax_id} onChange={(e) => update('company', 'tax_id', e.target.value)} />
            </Field>
            <Field label={t('public.company_intake.fields.website', { defaultValue: 'Website' })}>
              <input className={inputClass} value={form.company.website} onChange={(e) => update('company', 'website', e.target.value)} />
            </Field>
          </div>
        )
      case 'work':
        return (
          <div className="space-y-5">
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">{t('public.company_intake.fields.work_system')}</p>
              <MultiChoiceGrid options={scheduleOptions} value={form.terms.schedule} onChange={(next) => update('terms', 'schedule', next)} />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">{t('public.company_intake.fields.route_directions')}</p>
              <MultiChoiceGrid options={routeOptions} value={form.terms.route_directions} onChange={(next) => update('terms', 'route_directions', next)} />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">{t('public.company_intake.fields.night_driving')}</p>
              <ChoiceGrid columns="sm:grid-cols-3" options={nightDrivingOptions} value={form.terms.night_driving} onChange={(value) => update('terms', 'night_driving', value)} />
            </div>
          </div>
        )
      case 'trailer':
        return (
          <div className="space-y-5">
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">{t('public.company_intake.fields.trailer_type')}</p>
              <MultiChoiceGrid options={bodyOptions} value={form.terms.body_types} onChange={(next) => update('terms', 'body_types', next)} />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">{t('public.company_intake.fields.truck_brands', { defaultValue: 'Truck brands' })}</p>
              <MultiChoiceGrid options={truckOptions} value={form.terms.truck_brands} onChange={(next) => update('terms', 'truck_brands', next)} />
            </div>
          </div>
        )
      case 'compensation':
        return (
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-4">
              <Field label={t('public.company_intake.fields.amount')}>
                <input className={inputClass} value={form.terms.rate_amount} onChange={(e) => update('terms', 'rate_amount', e.target.value)} placeholder="100" />
              </Field>
              <Field label={t('public.company_intake.fields.rate_currency', { defaultValue: 'Currency' })}>
                <select className={inputClass} value={form.terms.rate_currency} onChange={(e) => update('terms', 'rate_currency', e.target.value)}>
                  <option value="PLN">PLN</option>
                  <option value="EUR">EUR</option>
                </select>
              </Field>
              <Field label={t('public.company_intake.fields.rate_period', { defaultValue: 'Period' })}>
                <select className={inputClass} value={form.terms.rate_period} onChange={(e) => update('terms', 'rate_period', e.target.value)}>
                  {ratePeriodOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </Field>
              <Field label={t('public.company_intake.fields.rate_tax_mode', { defaultValue: 'Type' })}>
                <select className={inputClass} value={form.terms.rate_tax_mode} onChange={(e) => update('terms', 'rate_tax_mode', e.target.value)}>
                  {rateTaxOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </Field>
            </div>
            <Field label={t('public.company_intake.fields.additional', { defaultValue: 'Additional information' })}>
              <textarea className={textareaClass} value={form.terms.additional} onChange={(e) => update('terms', 'additional', e.target.value)} />
            </Field>
          </div>
        )
      case 'review':
        return (
          <div className="space-y-5">
            <div className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
              {summaryRows.map((row) => (
                <div key={row.label} className="flex items-center justify-between gap-4 px-4 py-3">
                  <div>
                    <p className="text-xs font-semibold uppercase text-slate-500">{row.label}</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{row.value}</p>
                  </div>
                  <button type="button" onClick={() => goToStep(row.step)} className="text-sm font-semibold text-brand-700 hover:text-brand-900">
                    {t('common.actions.edit', { defaultValue: 'Edit' })}
                  </button>
                </div>
              ))}
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">{t('public.company_intake.consents.title')}</p>
              <div className="mt-3 space-y-3">
                <label className="flex gap-3 border-b border-slate-200 pb-3 text-sm font-medium text-slate-900">
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 accent-brand-600"
                    checked={allRequiredConsentsAccepted}
                    onChange={(e) => toggleAllRequiredConsents(e.target.checked)}
                  />
                  <span>{t('public.company_intake.consents.select_all_required')}</span>
                </label>
                <ConsentRow
                  id="company-intake-terms"
                  ref={consentTermsRef}
                  checked={form.consent.terms_accepted}
                  showError={showConsentErrors && !form.consent.terms_accepted}
                  errorMessage={consentMsg}
                  onChange={(checked) => updateConsent('terms_accepted', checked)}
                >
                  {t('public.company_intake.consents.terms_prefix', { defaultValue: 'I accept the' })}{' '}
                  <a className="font-semibold text-brand-700 hover:text-brand-900" href="/legal/terms.html" target="_blank" rel="noreferrer">
                    {t('public.company_intake.consents.terms_link', { defaultValue: 'Terms of use' })}
                  </a>
                  .
                </ConsentRow>
                <ConsentRow
                  id="company-intake-privacy"
                  ref={consentPrivacyRef}
                  checked={form.consent.privacy_accepted}
                  showError={showConsentErrors && !form.consent.privacy_accepted}
                  errorMessage={consentMsg}
                  onChange={(checked) => updateConsent('privacy_accepted', checked)}
                >
                  {t('public.company_intake.consents.privacy_prefix', { defaultValue: 'I have read the' })}{' '}
                  <a className="font-semibold text-brand-700 hover:text-brand-900" href="/legal/privacy.html" target="_blank" rel="noreferrer">
                    {t('public.company_intake.consents.privacy_link', { defaultValue: 'Privacy Policy' })}
                  </a>
                  .
                </ConsentRow>
                <ConsentRow
                  id="company-intake-data"
                  ref={consentDataRef}
                  checked={form.consent.data_processing_accepted}
                  showError={showConsentErrors && !form.consent.data_processing_accepted}
                  errorMessage={consentMsg}
                  onChange={(checked) => updateConsent('data_processing_accepted', checked)}
                >
                  {t('public.company_intake.consents.data_processing_prefix', {
                    defaultValue: 'I consent to personal data processing according to',
                  })}{' '}
                  <a className="font-semibold text-brand-700 hover:text-brand-900" href="/legal/rodo.html" target="_blank" rel="noreferrer">
                    {t('public.company_intake.consents.rodo_link', { defaultValue: 'RODO information' })}
                  </a>
                  .
                </ConsentRow>
                <ConsentRow
                  id="company-intake-accuracy"
                  ref={consentAccuracyRef}
                  checked={form.consent.accuracy_confirmed}
                  showError={showConsentErrors && !form.consent.accuracy_confirmed}
                  errorMessage={consentMsg}
                  onChange={(checked) => updateConsent('accuracy_confirmed', checked)}
                >
                  {t('public.company_intake.consents.accuracy_prefix', {
                    defaultValue: 'I declare that the information is correct under the',
                  })}{' '}
                  <a className="font-semibold text-brand-700 hover:text-brand-900" href="/legal/terms.html" target="_blank" rel="noreferrer">
                    {t('public.company_intake.consents.terms_link', { defaultValue: 'Terms of use' })}
                  </a>
                  .
                </ConsentRow>
                <ConsentRow
                  id="company-intake-marketing"
                  checked={form.consent.marketing_contact_accepted}
                  onChange={(checked) => updateConsent('marketing_contact_accepted', checked)}
                >
                  {t('public.company_intake.consents.marketing_prefix', {
                    defaultValue: 'I consent to marketing contact as described in the',
                  })}{' '}
                  <a className="font-semibold text-brand-700 hover:text-brand-900" href="/legal/privacy.html" target="_blank" rel="noreferrer">
                    {t('public.company_intake.consents.privacy_link', { defaultValue: 'Privacy Policy' })}
                  </a>
                  .
                </ConsentRow>
              </div>
            </div>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <PublicPageShell maxWidth="3xl" headerExtra={<PublicLocaleSwitcher options={supportedLanguages.length ? supportedLanguages : [form.language]} />}>
      <form className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-7" onSubmit={handleSubmit}>
        <div>
          <p className="text-sm font-semibold uppercase text-brand-700">
            {t('public.company_intake.kicker', { defaultValue: 'B2B intake' })}
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">
            {t('public.company_intake.profile_title')}
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            {t('public.company_intake.intro')}
          </p>
          <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-700">
            {t('public.company_intake.intro_hint')}
          </p>
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} />
          </div>
          <p className="mt-2 text-xs font-medium text-slate-500">
            {stepIndex + 1}/{STEPS.length}
          </p>
        </div>

        <div className="mt-7">
          <h2 className="text-lg font-semibold text-slate-900">
            {t(`public.company_intake.quiz.steps.${currentStep}`, { defaultValue: currentStep })}
          </h2>
          <div className="mt-5">{renderStep()}</div>
        </div>

        {error ? <div className="mt-5 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

        <div className="mt-7 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={goBack}
            disabled={stepIndex === 0 || loading}
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t('common.actions.back', { defaultValue: 'Back' })}
          </button>
          {currentStep === 'review' ? (
            <button
              type="submit"
              disabled={loading}
              className="rounded-md bg-brand-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? t('common.saving', { defaultValue: 'Saving...' }) : t('public.company_intake.submit', { defaultValue: 'Submit questionnaire' })}
            </button>
          ) : (
            <button
              type="button"
              onClick={goNext}
              disabled={loading}
              className="rounded-md bg-brand-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {t('common.actions.next', { defaultValue: 'Next' })}
            </button>
          )}
        </div>
      </form>
    </PublicPageShell>
  )
}
