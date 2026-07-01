import { useState } from 'react'
import { createPublicIntake } from '../../api/publicIntake'
import { useToast } from '../../components/Toast'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { useI18n } from '../../i18n'

export default function PublicLanding() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [countryCode, setCountryCode] = useState('+48')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const payload = {
        contacts: {
          email: email || undefined,
          phone: phone || undefined,
          phone_country_code: countryCode || undefined,
        },
      }
      const res = await createPublicIntake(payload)
      if (res?.apply_url) {
        window.location.href = res.apply_url
      } else {
        throw new Error(t('public.landing.errors.link_missing', { defaultValue: 'Не удалось получить ссылку' }))
      }
    } catch (err: any) {
      notify({
        title: err?.response?.data?.detail || err?.message || t('public.landing.errors.link_failed', { defaultValue: 'Ошибка получения ссылки' }),
        variant: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <PublicPageShell
      maxWidth="lg"
      headerExtra={<PublicLocaleSwitcher />}
    >
      <div className="card mx-auto w-full max-w-xl bg-white/90 px-6 py-8 shadow-lg">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">{t('public.landing.title', { defaultValue: 'Начать анкету' })}</h1>
        <p className="text-sm text-slate-600 mb-6">
          {t('public.landing.subtitle', { defaultValue: 'Введите контакты, мы откроем временную ссылку на анкету.' })}
        </p>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="text-sm font-semibold text-slate-800">
              {t('public.landing.fields.email_optional', { defaultValue: 'Email (необязательно)' })}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:outline-none"
              placeholder={t('public.landing.placeholders.email', { defaultValue: 'you@example.com' })}
            />
          </div>
          <div className="grid grid-cols-4 gap-2">
            <div>
              <label className="text-sm font-semibold text-slate-800">Код</label>
              <input
                type="text"
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:outline-none"
                placeholder="+48"
              />
            </div>
            <div className="col-span-3">
              <label className="text-sm font-semibold text-slate-800">Телефон</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:outline-none"
                placeholder="123456789"
                required={!email}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={loading || (!email && !phone)}
            className="w-full rounded-full bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {loading
              ? t('public.landing.actions.sending', { defaultValue: 'Отправляем…' })
              : t('public.landing.actions.get_link', { defaultValue: 'Получить ссылку' })}
          </button>
        </form>
      </div>
    </PublicPageShell>
  )
}
