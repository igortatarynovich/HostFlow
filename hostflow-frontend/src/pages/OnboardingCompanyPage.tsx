import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { createCompany } from '../api/client'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import {
  readSignupSuccessContextFromSearch,
  readSignupSuccessContextFromSessionStorage,
  SIGNUP_SUCCESS_CONTEXT_KEY,
} from '../constants/signupContext'
import { ACTIVATION_PATHS, getBusinessHomePath } from '../app/activationRoutes'

type CompanyType = 'agency' | 'employer' | 'services'

export default function OnboardingCompanyPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [name, setName] = useState('')
  const [companyType, setCompanyType] = useState<CompanyType>('agency')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const signupContext = useMemo(
    () => readSignupSuccessContextFromSearch(searchParams) ?? readSignupSuccessContextFromSessionStorage(),
    [searchParams],
  )
  const signupSuccess = signupContext?.signup === 'success'
  const welcomeEmailStatus = signupContext?.welcome_email || ''
  const trialEndsAt = signupContext?.trial_ends_at || null
  const trialEndsText = useMemo(() => {
    if (!trialEndsAt) return null
    const dt = new Date(trialEndsAt)
    if (Number.isNaN(dt.getTime())) return null
    return dt.toLocaleDateString()
  }, [trialEndsAt])
  useEffect(() => {
    if (!signupSuccess || typeof window === 'undefined') return
    try {
      window.sessionStorage.removeItem(SIGNUP_SUCCESS_CONTEXT_KEY)
    } catch {
      // ignore storage errors
    }
  }, [signupSuccess])
  const typeCards: Array<{
    value: CompanyType
    label: string
    description: string
    profile: string
  }> = [
    {
      value: 'agency',
      label: t('app.onboarding.company.type_agency', { defaultValue: 'Агентство' }),
      description: t('app.onboarding.company.type_agency_desc', {
        defaultValue: 'Клиенты + кандидаты + вакансии + лиды в одном workspace.',
      }),
      profile: t('app.onboarding.company.type_agency_profile', {
        defaultValue: 'Модули: Clients, Candidates, Vacancies, Leads, Services',
      }),
    },
    {
      value: 'employer',
      label: t('app.onboarding.company.type_employer', { defaultValue: 'Прямой работодатель' }),
      description: t('app.onboarding.company.type_employer_desc', {
        defaultValue: 'Фокус на найме: вакансии, кандидаты и внутренняя команда.',
      }),
      profile: t('app.onboarding.company.type_employer_profile', {
        defaultValue: 'Модули: Candidates, Vacancies, Documents',
      }),
    },
    {
      value: 'services',
      label: t('app.onboarding.company.type_services', { defaultValue: 'Услуги' }),
      description: t('app.onboarding.company.type_services_desc', {
        defaultValue: 'Клиенты, сделки/лиды и сервисные задачи без HR-лишнего.',
      }),
      profile: t('app.onboarding.company.type_services_profile', {
        defaultValue: 'Модули: Clients, Leads, Services, Documents',
      }),
    },
  ]

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    const trimmed = name.trim()
    if (!trimmed) {
      setError(t('app.onboarding.company.errors.name_required', { defaultValue: 'Введите название компании' }))
      return
    }
    setLoading(true)
    try {
      await createCompany({ name: trimmed, company_type: companyType })
      navigate(getBusinessHomePath(companyType), { replace: true })
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? err?.message ?? t('app.onboarding.company.errors.generic', { defaultValue: 'Не удалось создать компанию' })
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <div className="card rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">
          {t('app.onboarding.company.title', { defaultValue: 'Создайте компанию' })}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('app.onboarding.company.subtitle', { defaultValue: 'После этого шага вы сразу перейдете к быстрому запуску CRM.' })}
        </p>
        {signupSuccess && (
          <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {trialEndsText
              ? t('app.onboarding.company.signup_success_with_trial', {
                  defaultValue: 'Регистрация успешна. Пробный период активирован до {date}. Подтверждение email сейчас не требуется.',
                  values: { date: trialEndsText },
                })
              : t('app.onboarding.company.signup_success', {
                  defaultValue: 'Регистрация успешна. Пробный период активирован. Подтверждение email сейчас не требуется.',
                })}
            <div className="mt-1 text-xs leading-relaxed text-emerald-900/90">
              {welcomeEmailStatus === 'sent' &&
                t('app.onboarding.company.signup_success_email_sent', {
                  defaultValue: 'Welcome email with trial details has been sent to your inbox.',
                })}
              {welcomeEmailStatus === 'not_sent' &&
                t('app.onboarding.company.signup_success_email_not_sent', {
                  defaultValue: 'We could not deliver welcome email right now. Trial details are available in Billing.',
                })}
            </div>
            <div className="mt-1 text-xs leading-relaxed text-emerald-900/90">
              {t('app.onboarding.company.signup_success_links_prefix', { defaultValue: 'Документы и условия:' })}{' '}
              <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                {t('app.onboarding.company.signup_success_terms', { defaultValue: 'Terms' })}
              </a>
              {', '}
              <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                {t('app.onboarding.company.signup_success_privacy', { defaultValue: 'Privacy' })}
              </a>
              {', '}
              <a href="/legal/cookies.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                {t('app.onboarding.company.signup_success_cookies', { defaultValue: 'Cookies' })}
              </a>
              {'. '}
              <Link to={ACTIVATION_PATHS.billing} className="underline hover:no-underline">
                {t('app.onboarding.company.signup_success_billing', { defaultValue: 'Open billing' })}
              </Link>
              .
            </div>
          </div>
        )}
        <form onSubmit={onSubmit} className="mt-6 space-y-5">
          <div>
            <label htmlFor="onboarding-company-name" className="block text-sm font-medium text-slate-700">
              {t('app.onboarding.company.name_label', { defaultValue: 'Название компании' })}
            </label>
            <input
              id="onboarding-company-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder={t('app.onboarding.company.name_placeholder', { defaultValue: 'ООО «Пример»' })}
              autoFocus
            />
          </div>
          <div>
            <span className="block text-sm font-medium text-slate-700">
              {t('app.onboarding.company.type_label', { defaultValue: 'Тип компании' })}
            </span>
            <div className="mt-2 grid gap-3">
              {typeCards.map((card) => (
                <label
                  key={card.value}
                  className={`cursor-pointer rounded-xl border p-3 transition ${
                    companyType === card.value
                      ? 'border-brand-400 bg-brand-50/60'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <input
                      type="radio"
                      name="company_type"
                      value={card.value}
                      checked={companyType === card.value}
                      onChange={() => setCompanyType(card.value)}
                      className="mt-0.5 h-4 w-4 border-slate-300 text-brand-600 focus:ring-brand-500"
                    />
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-slate-800">{card.label}</div>
                      <p className="mt-0.5 text-xs text-slate-600">{card.description}</p>
                      <p className="mt-1 text-xs text-slate-500">{card.profile}</p>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
          {error && (
            <ErrorRecoveryBanner
              info={{
                title: error,
                hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
              }}
              onRetry={() => setError(null)}
              retryLabel={t('common.actions.close', { defaultValue: 'Close' })}
              compact
            />
          )}
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full rounded-lg px-4 py-2 font-medium disabled:opacity-50"
          >
            {loading
              ? t('common.saving', { defaultValue: 'Сохранение…' })
              : t('app.onboarding.company.submit', { defaultValue: 'Создать компанию' })}
          </button>
        </form>
      </div>
    </div>
  )
}
