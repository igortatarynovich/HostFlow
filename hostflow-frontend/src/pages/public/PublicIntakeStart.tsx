import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { createPublicIntake } from '../../api/publicIntake'
import { useI18n } from '../../i18n'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { PublicPageShell } from './components/PublicPageShell'
import { PREFERRED_CONTACT_VALUES } from '../../data/preferredContactChannels'

const DEFAULT_FORM = {
  phone_country_code: '+48',
  phone: '',
  email: '',
  preferred_messenger: 'whatsapp',
}

export default function PublicIntakeStart() {
  const { t, locale } = useI18n()
  const [form, setForm] = useState(DEFAULT_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ token: string; apply_url: string } | null>(null)
  const preferredContactOptions = useMemo(
    () =>
      PREFERRED_CONTACT_VALUES.map((value) => ({
        value,
        label: t(`app.candidate_card.contacts.options.${value || 'none'}`),
      })),
    [t]
  )

  const canSubmit = useMemo(() => {
    const hasPhone = Boolean(form.phone_country_code && form.phone)
    const hasEmail = Boolean(form.email)
    return hasPhone || hasEmail
  }, [form.phone_country_code, form.phone, form.email])

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
      const response = await createPublicIntake({
        contacts: {
          phone_country_code: form.phone_country_code || undefined,
          phone: form.phone || undefined,
          email: form.email || undefined,
          preferred_messenger: form.preferred_messenger || undefined,
        },
        source: 'public-intake-ui',
        locale: locale || 'en',
      })
      setResult({ token: response.token, apply_url: response.apply_url })
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || t('public.start.errors.create_failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <PublicPageShell maxWidth="3xl" headerExtra={<PublicLocaleSwitcher />}>
      <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card">
        <div className="mb-4">
          <Link to="/public/portal" className="text-sm font-medium text-brand-700 hover:text-brand-900">
            {t('public.start.header.back')}
          </Link>
        </div>
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-slate-900">{t('public.start.header.title')}</h1>
          <p className="mt-2 text-sm text-slate-600">{t('public.start.header.subtitle')}</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t('public.start.form.email')}</label>
            <input
              type="email"
              className="w-full rounded-xl border border-brand-100 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring"
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => handleChange('email', e.target.value)}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-[140px_1fr]">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">{t('public.start.form.country_code')}</label>
              <input
                type="text"
                className="w-full rounded-xl border border-brand-100 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring"
                placeholder="+48"
                value={form.phone_country_code}
                onChange={(e) => handleChange('phone_country_code', e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">{t('public.start.form.phone')}</label>
              <input
                type="tel"
                className="w-full rounded-xl border border-brand-100 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring"
                placeholder="123 456 789"
                value={form.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t('app.candidate_card.fields.preferred_contact')}</label>
            <select
              className="w-full rounded-xl border border-brand-100 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring"
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
