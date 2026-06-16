import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { createPublicIntake, listPublicIntakeLeadForms } from '../../api/publicIntake'
import { useI18n } from '../../i18n'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { PublicPageShell } from './components/PublicPageShell'
import { PREFERRED_CONTACT_VALUES } from '../../data/preferredContactChannels'
import { useSeoMeta } from '../../hooks/useSeoMeta'

const DEFAULT_FORM = {
  company_name: '',
  phone_country_code: '+48',
  phone: '',
  email: '',
  preferred_messenger: 'whatsapp',
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function pickIntakeCreateErrorMessage(err: unknown, t: (key: string) => string): string {
  const d = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof d === 'string' && d.trim()) return d
  if (d && typeof d === 'object' && !Array.isArray(d)) {
    const code = String((d as { code?: string }).code || '')
      .trim()
      .toLowerCase()
    if (code === 'lead_form_not_found') {
      const msg = t('public.start.errors.lead_form_not_found')
      if (msg && msg !== 'public.start.errors.lead_form_not_found') return msg
    }
    if (code === 'intake_vacancy_not_found') {
      const msg = t('public.start.errors.intake_vacancy_not_found')
      if (msg && msg !== 'public.start.errors.intake_vacancy_not_found') return msg
    }
    const message = (d as { message?: string }).message
    if (typeof message === 'string' && message.trim()) return message.trim()
  }
  return ''
}

export default function PublicIntakeStart() {
  const { t, locale } = useI18n()
  const [searchParams] = useSearchParams()

  const leadFormForRequest = useMemo(() => {
    const id = searchParams.get('lead_form_id')?.trim() ?? ''
    const slug = searchParams.get('lead_form_slug')?.trim() ?? ''
    if (id && UUID_RE.test(id)) {
      return { lead_form_id: id, lead_form_slug: undefined as string | undefined }
    }
    if (slug) {
      return { lead_form_id: undefined as string | undefined, lead_form_slug: slug }
    }
    return {}
  }, [searchParams])

  /** Optional: link from vacancy page → attach Candidate.vacancy_id on intake create (backend validates tenant). */
  const vacancyIdFromQuery = useMemo(() => {
    const raw = searchParams.get('vacancy_id')?.trim() ?? ''
    return UUID_RE.test(raw) ? raw : undefined
  }, [searchParams])

  /** B2B client inquiry → backend may create CRM Lead (`lead_type=client`) on successful submit. */
  const applicationKindFromQuery = useMemo(() => {
    const raw = (searchParams.get('application_kind') ?? '').trim().toLowerCase()
    return raw === 'client' ? ('client' as const) : undefined
  }, [searchParams])

  const canonicalPath = useMemo(() => {
    const slug = searchParams.get('lead_form_slug')?.trim()
    const id = searchParams.get('lead_form_id')?.trim()
    const vac = vacancyIdFromQuery
    const appKind = applicationKindFromQuery
    const parts: string[] = []
    if (slug) parts.push(`lead_form_slug=${encodeURIComponent(slug)}`)
    else if (id && UUID_RE.test(id)) parts.push(`lead_form_id=${encodeURIComponent(id)}`)
    if (vac) parts.push(`vacancy_id=${encodeURIComponent(vac)}`)
    if (appKind) parts.push(`application_kind=${encodeURIComponent(appKind)}`)
    if (!parts.length) return '/public/intake'
    return `/public/intake?${parts.join('&')}`
  }, [searchParams, vacancyIdFromQuery, applicationKindFromQuery])

  const isClientInquiry = applicationKindFromQuery === 'client'

  useSeoMeta({
    title: isClientInquiry
      ? t('app.seo.public_intake.client_title', { defaultValue: 'Client inquiry — HostFlow' })
      : t('app.seo.public_intake.title', { defaultValue: 'Candidate Intake Portal' }),
    description: isClientInquiry
      ? t('app.seo.public_intake.client_description', {
          defaultValue: 'Start a client inquiry. Your team may receive a CRM lead after you submit the form.',
        })
      : t('app.seo.public_intake.description', {
          defaultValue: 'Start candidate intake, submit contact details, and continue your application securely.',
        }),
    canonicalPath,
  })

  const [form, setForm] = useState(DEFAULT_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ token: string; apply_url: string } | null>(null)
  const [leadFormDisplay, setLeadFormDisplay] = useState<{ title?: string; slug?: string } | null>(null)

  const preferredContactOptions = useMemo(
    () =>
      PREFERRED_CONTACT_VALUES.map((value) => ({
        value,
        label: t(`app.candidate_card.contacts.options.${value || 'none'}`),
      })),
    [t],
  )

  useEffect(() => {
    let cancelled = false
    const id = leadFormForRequest.lead_form_id
    const slug = leadFormForRequest.lead_form_slug
    if (!id && !slug) {
      setLeadFormDisplay(null)
      return
    }
    void (async () => {
      try {
        const list = await listPublicIntakeLeadForms({
          publicSlug: slug || undefined,
          leadFormId: id || undefined,
        })
        if (cancelled) return
        const match = list.find((f) => (id && f.id === id) || (slug && f.public_slug === slug))
        if (match?.title?.trim()) {
          setLeadFormDisplay({ title: match.title.trim() })
        } else if (slug) {
          setLeadFormDisplay({ slug })
        } else if (id) {
          setLeadFormDisplay({ slug: id })
        } else {
          setLeadFormDisplay(null)
        }
      } catch {
        if (cancelled) return
        if (slug) setLeadFormDisplay({ slug })
        else if (id) setLeadFormDisplay({ slug: id })
        else setLeadFormDisplay(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [leadFormForRequest])

  const canSubmit = useMemo(() => {
    const hasPhone = Boolean(form.phone_country_code && form.phone)
    const hasEmail = Boolean(form.email)
    const hasCompany = !isClientInquiry || Boolean(form.company_name.trim())
    return hasCompany && (hasPhone || hasEmail)
  }, [form.phone_country_code, form.phone, form.email, form.company_name, isClientInquiry])

  const handleChange = (field: keyof typeof DEFAULT_FORM, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) {
      setError(t('public.start.errors.contacts_required'))
      return
    }
    setLoading(true)
    setError(null)
    try {
      const payload = {
        contacts: {
          phone_country_code: form.phone_country_code || undefined,
          phone: form.phone || undefined,
          email: form.email || undefined,
          preferred_messenger: form.preferred_messenger || undefined,
        },
        source: 'public-intake-ui',
        locale: locale || 'en',
        ...(vacancyIdFromQuery ? { vacancy_id: vacancyIdFromQuery } : {}),
        ...(applicationKindFromQuery ? { application_kind: applicationKindFromQuery } : {}),
        ...(isClientInquiry ? { client_company: { name: form.company_name.trim() || undefined } } : {}),
        ...(leadFormForRequest.lead_form_id
          ? { lead_form_id: leadFormForRequest.lead_form_id }
          : leadFormForRequest.lead_form_slug
            ? { lead_form_slug: leadFormForRequest.lead_form_slug }
            : {}),
      }
      const response = await createPublicIntake(payload)
      setResult({ token: response.token, apply_url: response.apply_url })
    } catch (err: unknown) {
      const fromApi = pickIntakeCreateErrorMessage(err, t)
      const fallback =
        (err as { message?: string })?.message ||
        t('public.start.errors.create_failed')
      setError(fromApi || fallback)
    } finally {
      setLoading(false)
    }
  }

  return (
    <PublicPageShell maxWidth="3xl" headerExtra={<PublicLocaleSwitcher />}>
      <div className="card p-8">
        <div className="mb-4">
          <Link to="/public/portal" className="text-sm font-medium text-brand-700 hover:text-brand-900">
            {t('public.start.header.back')}
          </Link>
        </div>
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-slate-900">
            {isClientInquiry ? t('public.start.header.title_client') : t('public.start.header.title')}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {isClientInquiry ? t('public.start.header.subtitle_client') : t('public.start.header.subtitle')}
          </p>
        </div>

        {isClientInquiry && (
          <div
            className="mb-6 rounded-xl border border-sky-200 bg-sky-50/80 px-4 py-3 text-left text-sm text-slate-800"
            role="status"
          >
            {t('public.start.client.banner')}
          </div>
        )}

        {leadFormDisplay && (leadFormDisplay.title || leadFormDisplay.slug) && (
          <div
            className="mb-6 rounded-xl border border-slate-200 bg-brand-50/60 px-4 py-3 text-left text-sm text-slate-700"
            role="status"
          >
            <span className="font-semibold text-brand-800">{t('public.start.lead_form.banner_title')}: </span>
            {leadFormDisplay.title
              ? t('public.start.lead_form.banner_named', { values: { title: leadFormDisplay.title } })
              : t('public.start.lead_form.banner_slug_only', { values: { slug: leadFormDisplay.slug || '' } })}
          </div>
        )}

        <form className="space-y-4" onSubmit={handleSubmit}>
          {isClientInquiry && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                {t('public.start.form.company_name', { defaultValue: 'Company name' })}
              </label>
              <input
                type="text"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring"
                placeholder={t('public.start.form.placeholders.company_name', { defaultValue: 'Transport company name' })}
                value={form.company_name}
                onChange={(e) => handleChange('company_name', e.target.value)}
                required={isClientInquiry}
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t('public.start.form.email')}</label>
            <input
              type="email"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring"
              placeholder={t('public.start.form.placeholders.email', { defaultValue: 'you@example.com' })}
              value={form.email}
              onChange={(e) => handleChange('email', e.target.value)}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-[140px_1fr]">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">{t('public.start.form.country_code')}</label>
              <input
                type="text"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring"
                placeholder="+48"
                value={form.phone_country_code}
                onChange={(e) => handleChange('phone_country_code', e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">{t('public.start.form.phone')}</label>
              <input
                type="tel"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring"
                placeholder="123 456 789"
                value={form.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t('app.candidate_card.fields.preferred_contact')}</label>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring"
              value={form.preferred_messenger}
              onChange={(e) => handleChange('preferred_messenger', e.target.value)}
            >
              {preferredContactOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {error && <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={!canSubmit || loading}
            className="w-full rounded-xl bg-brand-600 px-4 py-3 text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loading ? t('public.start.form.submitting') : t('public.start.form.submit')}
          </button>
        </form>

        {result && (
          <div className="mt-8 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            <p className="font-medium">{t('public.start.form.link_ready')}</p>
            <p className="mt-1 break-all text-xs text-green-700">
              {(typeof window !== 'undefined' ? window.location.origin : '')}
              {result.apply_url}
            </p>
            <Link to={result.apply_url} className="mt-4 inline-flex rounded-lg bg-green-600 px-4 py-2 text-white">
              {t('public.start.form.open')}
            </Link>
          </div>
        )}
      </div>
    </PublicPageShell>
  )
}
