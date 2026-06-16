import { FormEvent, useMemo, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { submitCompanyIntake } from '../../api/companyIntake'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { type LocaleCode, useI18n } from '../../i18n'
import { PublicPageShell } from './components/PublicPageShell'

type StepId =
  | 'language'
  | 'need'
  | 'count'
  | 'base'
  | 'transport'
  | 'fleet'
  | 'timing'
  | 'contact'
  | 'company'
  | 'additional'
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
    route_directions: string[]
    cargo_types: string[]
    work_conditions: string[]
    truck_brands: string[]
    body_type: string
    rate_amount: string
    rate_currency: string
    rate_period: string
    rate_tax_mode: string
    bonus: string
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
  'need',
  'count',
  'base',
  'transport',
  'fleet',
  'timing',
  'contact',
  'company',
  'additional',
  'review',
]

const LANGUAGE_OPTIONS: Array<{ value: LocaleCode; label: string }> = [
  { value: 'pl', label: 'Polski' },
  { value: 'en', label: 'English' },
  { value: 'ru', label: 'Русский' },
]

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
    route_directions: [],
    cargo_types: [],
    work_conditions: [],
    truck_brands: [],
    body_type: '',
    rate_amount: '',
    rate_currency: 'EUR',
    rate_period: 'day',
    rate_tax_mode: 'netto',
    bonus: '',
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

function Field({ label, children }: { label: string; children: JSX.Element }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <div className="mt-1">{children}</div>
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
  const [error, setError] = useState<string | null>(null)
  const [submittedLeadId, setSubmittedLeadId] = useState<string | null>(null)
  const sourceContext = useMemo(() => buildSourceContext(), [])
  const leadSource = useMemo(() => companyIntakeSourceFromContext(sourceContext), [sourceContext])

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
  const cityOptions: Option[] = ['Poznań', 'Warszawa', 'Wrocław', 'Łódź', 'Gdańsk', 'Katowice'].map((value) => ({ value, label: value }))
  const candidateCountryOptions: Option[] = [
    'Ukraina',
    'Białoruś',
    'Mołdawia',
    'Gruzja',
    'Armenia',
    'Azerbejdżan',
    'Kazachstan',
    'Uzbekistan',
    'Kirgistan',
    'Tadżykistan',
    'Indie',
    'Nepal',
    'Filipiny',
    'Sri Lanka',
    'Turcja',
    'Kraje UE',
    'Bez znaczenia',
    'Inne',
  ].map((value) => ({ value, label: value }))
  const scheduleOptions: Option[] = ['2/1', '3/1', '4/1', '6/2', '8/2'].map((value) => ({ value, label: value })).concat([
    { value: 'monday_friday', label: 'Poniedziałek-piątek' },
    { value: 'weekends_home', label: 'Weekendy w domu' },
    { value: 'to_agree', label: 'Do uzgodnienia' },
    { value: 'other', label: 'Inny system' },
  ])
  const routeOptions: Option[] = [
    'Polska',
    'Niemcy',
    'Francja',
    'Benelux',
    'Skandynawia',
    'Hiszpania / Portugalia',
    'Włochy',
    'Czechy / Słowacja',
    'Kraje bałtyckie',
    'Wielka Brytania',
    'Trasy międzynarodowe UE',
    'Trasy krajowe',
    'Inne',
  ].map((value) => ({ value, label: value }))
  const cargoOptions: Option[] = [
    'FTL',
    'LTL',
    'Chłodnia',
    'Firanka',
    'Jumbo',
    'Kontener',
    'Izoterma',
    'Cysterna',
    'ADR',
    'Żywność',
    'AGD / elektronika',
    'Materiały budowlane',
    'Palety',
    'Automotive',
    'Inne',
  ].map((value) => ({ value, label: value }))
  const workConditionOptions: Option[] = [
    'Jazda nocna',
    'Brak jazdy nocnej',
    'Załadunek / rozładunek po stronie kierowcy',
    'Brak załadunku / rozładunku',
    'Wymiana palet',
    'Brak wymiany palet',
    'Stałe trasy',
    'Zmienne trasy',
    'Praca w podwójnej obsadzie',
    'Praca solo',
  ].map((value) => ({ value, label: value }))
  const truckOptions: Option[] = ['MAN', 'Mercedes', 'Volvo', 'Scania', 'DAF', 'Iveco'].map((value) => ({ value, label: value }))
  const bodyOptions: Option[] = [
    { value: 'curtain', label: t('public.company_intake.quiz.body.curtain', { defaultValue: 'Curtain' }) },
    { value: 'frigo', label: t('public.company_intake.quiz.body.frigo', { defaultValue: 'Refrigerated' }) },
    { value: 'jumbo', label: 'Jumbo' },
    { value: 'container', label: t('public.company_intake.quiz.body.container', { defaultValue: 'Container' }) },
  ]

  const canContinue = () => {
    if (currentStep === 'contact') return Boolean(form.contact.full_name.trim() && (form.contact.email.trim() || form.contact.phone.trim()))
    if (currentStep === 'company') return Boolean(form.company.name.trim())
    return true
  }
  const canSubmit =
    form.consent.terms_accepted &&
    form.consent.privacy_accepted &&
    form.consent.data_processing_accepted &&
    form.consent.accuracy_confirmed

  const goNext = () => {
    if (!canContinue()) {
      setError(t('public.company_intake.errors.required', { defaultValue: 'Company name, contact name, and email or phone are required.' }))
      return
    }
    setError(null)
    setStepIndex((idx) => Math.min(idx + 1, STEPS.length - 1))
  }

  const goBack = () => {
    setError(null)
    setStepIndex((idx) => Math.max(idx - 1, 0))
  }

  const goToStep = (step: StepId) => {
    setError(null)
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
  }

  const setLanguage = (next: LocaleCode) => {
    setLocale(next)
    setForm((prev) => ({ ...prev, language: next }))
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!form.company.name.trim() || !form.contact.full_name.trim() || (!form.contact.email.trim() && !form.contact.phone.trim())) {
      setError(t('public.company_intake.errors.required', { defaultValue: 'Company name, contact name, and email or phone are required.' }))
      return
    }
    if (!canSubmit) {
      setError('Przed wysłaniem formularza wymagane jest zaakceptowanie regulaminu, polityki prywatności, zgody na przetwarzanie danych oraz potwierdzenie poprawności informacji.')
      return
    }
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
          candidate_countries: form.need.candidate_countries,
          requirements: optionalText(form.need.requirements),
        },
        terms: {
          rate: optionalText([form.terms.rate_amount, form.terms.rate_currency, form.terms.rate_period, form.terms.rate_tax_mode].filter(Boolean).join(' ')),
          rate_amount: optionalText(form.terms.rate_amount),
          rate_currency: optionalText(form.terms.rate_currency),
          rate_period: optionalText(form.terms.rate_period),
          rate_tax_mode: optionalText(form.terms.rate_tax_mode),
          bonus: optionalText(form.terms.bonus),
          schedule: optionalText(form.terms.schedule.join(', ')),
          work_systems: form.terms.schedule,
          route_directions: form.terms.route_directions,
          cargo_types: form.terms.cargo_types,
          work_conditions: form.terms.work_conditions,
          base_location: optionalText(form.terms.base_location),
          truck_brands: form.terms.truck_brands,
          body_type: optionalText(form.terms.body_type),
          additional: optionalText(form.terms.additional),
        },
        consent: {
          ...form.consent,
          terms_version: '2026-06-16',
          privacy_version: '2026-06-16',
        },
        source: leadSource,
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
  ]

  if (submittedLeadId) {
    return (
      <PublicPageShell maxWidth="xl" headerExtra={<PublicLocaleSwitcher />}>
        <div className="rounded-lg border border-emerald-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm font-semibold uppercase text-emerald-700">
            {t('public.company_intake.success.kicker', { defaultValue: 'Submitted' })}
          </p>
          <h1 className="mt-3 text-2xl font-semibold text-slate-900">
            Dziękujemy za przesłanie informacji.
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            Nasz zespół przeanalizuje profil firmy i skontaktuje się z Państwem w celu omówienia możliwych rozwiązań rekrutacyjnych.
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
            options={LANGUAGE_OPTIONS}
            value={form.language}
            onChange={(value) => setLanguage(value as LocaleCode)}
          />
        )
      case 'need':
        return <ChoiceGrid options={needOptions} value={form.need.what_needed} onChange={(value) => update('need', 'what_needed', value)} />
      case 'count':
        return <ChoiceGrid options={countOptions} value={form.need.people_count} onChange={(value) => update('need', 'people_count', value)} />
      case 'base':
        return (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('public.company_intake.fields.country', { defaultValue: 'Country' })}>
              <select className={inputClass} value={form.company.country} onChange={(e) => update('company', 'country', e.target.value)}>
                {countryOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </Field>
            <Field label={t('public.company_intake.fields.city', { defaultValue: 'City' })}>
              <select className={inputClass} value={form.company.city} onChange={(e) => update('company', 'city', e.target.value)}>
                <option value="">{t('common.select', { defaultValue: 'Select' })}</option>
                {cityOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
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
            <Field label={t('public.company_intake.fields.contact_name', { defaultValue: 'Name' })}>
              <input className={inputClass} value={form.contact.full_name} onChange={(e) => update('contact', 'full_name', e.target.value)} />
            </Field>
            <Field label={t('public.company_intake.fields.role', { defaultValue: 'Role' })}>
              <input className={inputClass} value={form.contact.role} onChange={(e) => update('contact', 'role', e.target.value)} />
            </Field>
            <Field label={t('public.company_intake.fields.email', { defaultValue: 'Email' })}>
              <input className={inputClass} type="email" value={form.contact.email} onChange={(e) => update('contact', 'email', e.target.value)} />
            </Field>
            <Field label={t('public.company_intake.fields.phone', { defaultValue: 'Phone' })}>
              <input className={inputClass} value={form.contact.phone} onChange={(e) => update('contact', 'phone', e.target.value)} />
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
            <Field label={t('public.company_intake.fields.company_name', { defaultValue: 'Company name' })}>
              <input className={inputClass} value={form.company.name} onChange={(e) => update('company', 'name', e.target.value)} />
            </Field>
            <Field label={t('public.company_intake.fields.tax_id', { defaultValue: 'NIP / VAT' })}>
              <input className={inputClass} value={form.company.tax_id} onChange={(e) => update('company', 'tax_id', e.target.value)} />
            </Field>
            <Field label={t('public.company_intake.fields.website', { defaultValue: 'Website' })}>
              <input className={inputClass} value={form.company.website} onChange={(e) => update('company', 'website', e.target.value)} />
            </Field>
          </div>
        )
      case 'additional':
        return (
          <div className="space-y-5">
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">Preferowane kraje pochodzenia kandydatów</p>
              <MultiChoiceGrid options={candidateCountryOptions} value={form.need.candidate_countries} onChange={(next) => update('need', 'candidate_countries', next)} />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">System pracy</p>
              <MultiChoiceGrid options={scheduleOptions} value={form.terms.schedule} onChange={(next) => update('terms', 'schedule', next)} />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">Kierunki tras</p>
              <MultiChoiceGrid options={routeOptions} value={form.terms.route_directions} onChange={(next) => update('terms', 'route_directions', next)} />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">Typ transportu / ładunku</p>
              <MultiChoiceGrid options={cargoOptions} value={form.terms.cargo_types} onChange={(next) => update('terms', 'cargo_types', next)} />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">Warunki dodatkowe</p>
              <MultiChoiceGrid options={workConditionOptions} value={form.terms.work_conditions} onChange={(next) => update('terms', 'work_conditions', next)} />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">{t('public.company_intake.fields.truck_brands', { defaultValue: 'Truck brands' })}</p>
              <MultiChoiceGrid options={truckOptions} value={form.terms.truck_brands} onChange={(next) => update('terms', 'truck_brands', next)} />
            </div>
            <ChoiceGrid options={bodyOptions} value={form.terms.body_type} onChange={(value) => update('terms', 'body_type', value)} />
            <div>
              <p className="mb-3 text-sm font-medium text-slate-700">Stawka / wynagrodzenie</p>
              <div className="grid gap-3 sm:grid-cols-4">
                <input className={inputClass} value={form.terms.rate_amount} onChange={(e) => update('terms', 'rate_amount', e.target.value)} placeholder="Kwota" />
                <select className={inputClass} value={form.terms.rate_currency} onChange={(e) => update('terms', 'rate_currency', e.target.value)}>
                  <option value="PLN">PLN</option>
                  <option value="EUR">EUR</option>
                </select>
                <select className={inputClass} value={form.terms.rate_period} onChange={(e) => update('terms', 'rate_period', e.target.value)}>
                  <option value="day">dzień</option>
                  <option value="month">miesiąc</option>
                  <option value="kilometer">kilometr</option>
                  <option value="hour">godzina</option>
                </select>
                <select className={inputClass} value={form.terms.rate_tax_mode} onChange={(e) => update('terms', 'rate_tax_mode', e.target.value)}>
                  <option value="netto">netto</option>
                  <option value="brutto">brutto</option>
                  <option value="b2b">B2B</option>
                </select>
              </div>
            </div>
            <Field label="Dodatkowe premie / bonusy">
              <textarea className={textareaClass} value={form.terms.bonus} onChange={(e) => update('terms', 'bonus', e.target.value)} />
            </Field>
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
              <p className="text-sm font-semibold text-slate-900">Zgody i oświadczenia</p>
              <div className="mt-3 space-y-3">
                <label className="flex gap-3 text-sm text-slate-700">
                  <input type="checkbox" checked={form.consent.terms_accepted} onChange={(e) => updateConsent('terms_accepted', e.target.checked)} />
                  <span>Akceptuję Regulamin korzystania z formularza.</span>
                </label>
                <label className="flex gap-3 text-sm text-slate-700">
                  <input type="checkbox" checked={form.consent.privacy_accepted} onChange={(e) => updateConsent('privacy_accepted', e.target.checked)} />
                  <span>Zapoznałem/am się z Polityką prywatności.</span>
                </label>
                <label className="flex gap-3 text-sm text-slate-700">
                  <input type="checkbox" checked={form.consent.data_processing_accepted} onChange={(e) => updateConsent('data_processing_accepted', e.target.checked)} />
                  <span>Wyrażam zgodę na przetwarzanie danych osobowych w celu obsługi zapytania i przygotowania oferty współpracy.</span>
                </label>
                <label className="flex gap-3 text-sm text-slate-700">
                  <input type="checkbox" checked={form.consent.accuracy_confirmed} onChange={(e) => updateConsent('accuracy_confirmed', e.target.checked)} />
                  <span>Oświadczam, że podane informacje są zgodne z moją wiedzą.</span>
                </label>
                <label className="flex gap-3 text-sm text-slate-700">
                  <input type="checkbox" checked={form.consent.marketing_contact_accepted} onChange={(e) => updateConsent('marketing_contact_accepted', e.target.checked)} />
                  <span>Wyrażam zgodę na kontakt marketingowy drogą elektroniczną i telefoniczną.</span>
                </label>
              </div>
            </div>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <PublicPageShell maxWidth="3xl" headerExtra={<PublicLocaleSwitcher />}>
      <form className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-7" onSubmit={handleSubmit}>
        <div>
          <p className="text-sm font-semibold uppercase text-brand-700">
            {t('public.company_intake.kicker', { defaultValue: 'B2B intake' })}
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">
            Company Recruitment Profile
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Informacje w tej ankiecie pomogą nam przygotować profil Państwa firmy oraz dopasować kandydatów do realnych warunków pracy. Dane są wykorzystywane wyłącznie w celu analizy zapotrzebowania rekrutacyjnego i przygotowania odpowiedniej oferty współpracy.
          </p>
          <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-700">
            Im dokładniej poznamy warunki pracy, tym lepiej dopasujemy kandydatów i unikniemy nietrafionych zgłoszeń.
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
              disabled={loading || !canSubmit}
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
