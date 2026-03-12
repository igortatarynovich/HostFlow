import { useState } from 'react'
import { createPublicIntake } from '../../api/publicIntake'
import { useToast } from '../../components/Toast'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'

export default function PublicLanding() {
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
        throw new Error('Не удалось получить ссылку')
      }
    } catch (err: any) {
      notify({
        title: err?.response?.data?.detail || err?.message || 'Ошибка получения ссылки',
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
      <div className="mx-auto w-full max-w-xl rounded-3xl border border-slate-200 bg-white/90 px-6 py-8 shadow-lg">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Начать анкету</h1>
        <p className="text-sm text-slate-600 mb-6">Введите контакты, мы откроем временную ссылку на анкету.</p>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="text-sm font-semibold text-slate-800">Email (необязательно)</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:outline-none"
              placeholder="you@example.com"
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
            {loading ? 'Отправляем…' : 'Получить ссылку'}
          </button>
        </form>
      </div>
    </PublicPageShell>
  )
}

