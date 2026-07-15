import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { createVacancy, EMPLOYMENT_TYPES, type EmploymentType } from '../../api/vacancies'
import { listCompanies, listOwnCompanies } from '../../api/client'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useCompanySetupCatalogs } from '../../hooks/useCompanySetupCatalogs'
import { catalogCountryLabel, catalogOptionLabel } from '../../utils/catalogOptions'
import { SetupFlowChrome } from '../../components/setup/SetupFlowChrome'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import {
  friendlyFormHintError,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'

type CompanyOption = { id: string; name: string; group: 'own' | 'client' }

function isClientCompany(extra: unknown): boolean {
  if (!extra || typeof extra !== 'object') return false
  const role = String(
    (extra as Record<string, unknown>).company_role ??
      (extra as Record<string, unknown>).company_kind ??
      '',
  )
    .trim()
    .toLowerCase()
  return role === 'client'
}

export default function SetupFirstVacancyPage() {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { catalogs } = useCompanySetupCatalogs(locale)

  const presetCompanyId = (searchParams.get('companyId') || '').trim()
  const presetCompanyName = (searchParams.get('companyName') || '').trim()
  const hiringTarget = (searchParams.get('hiringTarget') || '').trim()

  const [title, setTitle] = useState('')
  const [companyId, setCompanyId] = useState(presetCompanyId)
  const [workCountryCode, setWorkCountryCode] = useState('PL')
  const [employmentType, setEmploymentType] = useState<EmploymentType>('full_time')
  const [salary, setSalary] = useState('')
  const [companyOptions, setCompanyOptions] = useState<CompanyOption[]>([])
  const [loadingCompanies, setLoadingCompanies] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const [own, companiesRaw] = await Promise.all([
          listOwnCompanies().catch(() => ({ items: [] as Array<{ id: string; name?: string }> })),
          listCompanies({ limit: 100 }).catch(() => []),
        ])
        if (!alive) return

        const ownItems: CompanyOption[] = ((own?.items as Array<{ id: string; name?: string }>) ?? []).map(
          (c) => ({
            id: String(c.id),
            name: String(c.name ?? c.id),
            group: 'own' as const,
          }),
        )

        const companiesList = Array.isArray(companiesRaw)
          ? companiesRaw
          : ((companiesRaw as { items?: Array<Record<string, unknown>> })?.items ?? [])

        const clientItems: CompanyOption[] = companiesList
          .filter((c) => isClientCompany(c.extra))
          .map((c) => ({
            id: String(c.id),
            name: String(c.name ?? c.id),
            group: 'client' as const,
          }))

        const opts =
          hiringTarget === 'own' || clientItems.length === 0
            ? ownItems
            : [...clientItems, ...ownItems.filter((o) => !clientItems.some((c) => c.id === o.id))]

        setCompanyOptions(opts)
        if (presetCompanyId && opts.some((o) => o.id === presetCompanyId)) {
          setCompanyId(presetCompanyId)
        } else if (opts[0]) {
          setCompanyId(opts[0].id)
        }
      } finally {
        if (alive) setLoadingCompanies(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [hiringTarget, presetCompanyId])

  const selectedCompanyLabel = useMemo(() => {
    const found = companyOptions.find((o) => o.id === companyId)
    if (found) return found.name
    return presetCompanyName || ''
  }, [companyId, companyOptions, presetCompanyName])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    const trimmedTitle = title.trim()
    if (!trimmedTitle) {
      setError(
        friendlyFormHintError(
          t('app.onboarding.setup.vacancy.errors.title_required', {
            defaultValue: 'Укажите название вакансии.',
          }),
          t,
        ),
      )
      return
    }
    if (!companyId) {
      setError(
        friendlyFormHintError(
          t('app.onboarding.setup.vacancy.errors.company_required', {
            defaultValue: 'Выберите компанию.',
          }),
          t,
        ),
      )
      return
    }

    const countryOpt = catalogs.countries.find((c) => c.value === workCountryCode)
    const workCountry = catalogCountryLabel(
      countryOpt ?? { value: workCountryCode, label: workCountryCode },
      locale,
      workCountryCode,
    )

    setLoading(true)
    try {
      const created = await createVacancy({
        company_id: companyId,
        title: trimmedTitle,
        location: workCountryCode === 'OTHER' ? undefined : workCountry,
        employment_type: employmentType,
        salary_from: salary.trim() || undefined,
        currency: salary.trim() ? 'EUR' : undefined,
        extra: { setup_source: 'setup_first_vacancy' },
      })
      const vacancyId = String((created as { id?: string })?.id ?? '')
      const params = new URLSearchParams({ vacancyId, companyId })
      navigate(`${CRM_APP_PATHS.setupProcess}?${params.toString()}`)
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.onboarding.setup.vacancy.errors.generic', {
            defaultValue: 'Не удалось создать вакансию.',
          }),
          t,
        ),
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <SetupFlowChrome
      testId="m1-setup-vacancy-flow"
      stepLabel={t('app.onboarding.setup.vacancy.badge', { defaultValue: 'Настройка · Первая вакансия' })}
      title={t('app.onboarding.setup.vacancy.title', {
        defaultValue: 'Создадим первую вакансию',
      })}
      subtitle={t('app.onboarding.setup.vacancy.subtitle', {
        defaultValue:
          'Только несколько полей. Остальное HostFlow настроит по шаблону — воронку и требования можно изменить позже.',
      })}
    >
      {loadingCompanies ? (
        <p className="text-sm text-slate-500">{t('common.loading')}</p>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="setup-vacancy-title" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.setup.vacancy.title_label', { defaultValue: 'Название вакансии' })}
            </label>
            <input
              id="setup-vacancy-title"
              data-testid="m1-vacancy-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder={t('app.onboarding.setup.vacancy.title_placeholder', {
                defaultValue: 'Например, Водитель CE — международные',
              })}
              autoFocus
              required
            />
          </div>

          <div>
            <label htmlFor="setup-vacancy-client" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.setup.vacancy.client_label', { defaultValue: 'Клиент' })}
            </label>
            {companyOptions.length <= 1 && selectedCompanyLabel ? (
              <p
                className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800"
                data-testid="m1-vacancy-client-readonly"
              >
                {selectedCompanyLabel}
              </p>
            ) : (
              <select
                id="setup-vacancy-client"
                data-testid="m1-vacancy-client"
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
                className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                {companyOptions.map((opt) => (
                  <option key={`${opt.group}-${opt.id}`} value={opt.id}>
                    {opt.group === 'own'
                      ? t('app.onboarding.setup.vacancy.own_company_prefix', {
                          defaultValue: 'Своя компания: {name}',
                          values: { name: opt.name },
                        })
                      : opt.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label htmlFor="setup-vacancy-country" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.setup.vacancy.country_label', { defaultValue: 'Страна работы' })}
            </label>
            <select
              id="setup-vacancy-country"
              data-testid="m1-vacancy-country"
              value={workCountryCode}
              onChange={(e) => setWorkCountryCode(e.target.value)}
              className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {catalogs.countries.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {catalogOptionLabel(opt, locale)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="setup-vacancy-employment" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.setup.vacancy.employment_label', { defaultValue: 'Тип занятости' })}
            </label>
            <select
              id="setup-vacancy-employment"
              data-testid="m1-vacancy-employment"
              value={employmentType}
              onChange={(e) => setEmploymentType(e.target.value as EmploymentType)}
              className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {EMPLOYMENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`app.onboarding.setup.vacancy.employment.${type}`, {
                    defaultValue: type === 'full_time' ? 'Полная занятость' : type === 'part_time' ? 'Частичная' : 'B2B',
                  })}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="setup-vacancy-salary" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.setup.vacancy.salary_label', { defaultValue: 'Зарплата (необязательно)' })}
            </label>
            <input
              id="setup-vacancy-salary"
              data-testid="m1-vacancy-salary"
              value={salary}
              onChange={(e) => setSalary(e.target.value)}
              className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="4500"
              inputMode="decimal"
            />
          </div>

          {error ? <ErrorRecoveryBanner info={error} compact /> : null}

          <button
            type="submit"
            data-testid="m1-vacancy-save"
            disabled={loading}
            className="btn-primary w-full rounded-lg py-3 font-medium disabled:opacity-50"
          >
            {loading
              ? t('common.saving')
              : t('app.onboarding.setup.vacancy.submit', { defaultValue: 'Создать вакансию' })}
          </button>
        </form>
      )}
    </SetupFlowChrome>
  )
}
