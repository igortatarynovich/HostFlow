import { useCallback, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { createClientCompany, listOwnCompanies } from '../../api/client'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useCompanySetupCatalogs } from '../../hooks/useCompanySetupCatalogs'
import { useCityOptions } from '../../hooks/useCityOptions'
import { catalogCountryLabel, catalogOptionLabel } from '../../utils/catalogOptions'
import { SetupFlowChrome } from '../../components/setup/SetupFlowChrome'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import {
  friendlyFormHintError,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'

type HiringTarget = 'client' | 'own' | ''
type Step = 'audience' | 'details'

export default function SetupFirstClientPage() {
  const { t, locale } = useI18n()
  const navigate = useNavigate()

  const [step, setStep] = useState<Step>('audience')
  const [hiringTarget, setHiringTarget] = useState<HiringTarget>('')
  const [name, setName] = useState('')
  const [countryCode, setCountryCode] = useState('PL')
  const [city, setCity] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const { catalogs } = useCompanySetupCatalogs(locale)
  const { labels: cityOptions } = useCityOptions(countryCode, locale)

  const goToVacancy = useCallback(
    (companyId: string, companyName: string, target: HiringTarget) => {
      const params = new URLSearchParams({
        companyId,
        companyName,
        hiringTarget: target,
      })
      navigate(`${CRM_APP_PATHS.setupVacancy}?${params.toString()}`)
    },
    [navigate],
  )

  async function onAudienceContinue() {
    setError(null)
    if (!hiringTarget) {
      setError(
        friendlyFormHintError(
          t('app.onboarding.setup.client.errors.target_required', {
            defaultValue: 'Choose who you are hiring for.',
          }),
          t,
        ),
      )
      return
    }
    if (hiringTarget === 'client') {
      setStep('details')
      return
    }
    setLoading(true)
    try {
      const own = await listOwnCompanies()
      const ownCompany = own.items?.[0]
      if (!ownCompany?.id) {
        setError(
          friendlyFormHintError(
            t('app.onboarding.setup.client.errors.own_company_missing', {
              defaultValue: 'Set up your own company first.',
            }),
            t,
          ),
        )
        return
      }
      goToVacancy(String(ownCompany.id), String(ownCompany.name ?? ''), 'own')
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.onboarding.setup.client.errors.generic', {
            defaultValue: 'Could not continue setup.',
          }),
          t,
        ),
      )
    } finally {
      setLoading(false)
    }
  }

  async function onClientSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    const trimmed = name.trim()
    if (!trimmed) {
      setError(
        friendlyFormHintError(
          t('app.onboarding.setup.client.errors.name_required', {
            defaultValue: 'Enter the client company name.',
          }),
          t,
        ),
      )
      return
    }
    const countryOpt = catalogs.countries.find((c) => c.value === countryCode)
    const country = catalogCountryLabel(
      countryOpt ?? { value: countryCode, label: countryCode },
      locale,
      countryCode,
    )

    setLoading(true)
    try {
      const created = await createClientCompany({
        name: trimmed,
        country_code: countryCode === 'OTHER' ? undefined : countryCode,
        country: countryCode === 'OTHER' ? undefined : country,
        city: city.trim() || undefined,
        extra: {
          company_role: 'client',
          setup_source: 'setup_first_client',
        },
      })
      goToVacancy(String(created?.id ?? ''), trimmed, 'client')
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.onboarding.setup.client.errors.create_failed', {
            defaultValue: 'Could not create the client.',
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
      testId="m1-setup-client-flow"
      stepLabel={t('app.onboarding.setup.client.badge', { defaultValue: 'Setup · First client' })}
      title={
        step === 'audience'
          ? t('app.onboarding.setup.client.audience_title', {
              defaultValue: 'Who do you want to hire for?',
            })
          : t('app.onboarding.setup.client.details_title', {
              defaultValue: 'Tell us a bit about the client',
            })
      }
      subtitle={
        step === 'audience'
          ? t('app.onboarding.setup.client.audience_subtitle', {
              defaultValue:
                'One answer — and we show only the fields you need. No client registry or extra settings.',
            })
          : t('app.onboarding.setup.client.details_subtitle', {
              defaultValue: 'Minimum data to create the first vacancy.',
            })
      }
    >
      {step === 'audience' ? (
        <div className="space-y-4">
          <div className="grid gap-3" role="radiogroup">
            <button
              type="button"
              role="radio"
              aria-checked={hiringTarget === 'client'}
              data-testid="m1-setup-hiring-client"
              onClick={() => setHiringTarget('client')}
              className={`rounded-xl border-2 p-4 text-left text-sm transition ${
                hiringTarget === 'client'
                  ? 'border-brand-400 bg-brand-50/80 ring-2 ring-brand-200'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              {t('app.onboarding.setup.client.target_client', {
                defaultValue: 'For a client company',
              })}
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={hiringTarget === 'own'}
              data-testid="m1-setup-hiring-own"
              onClick={() => setHiringTarget('own')}
              className={`rounded-xl border-2 p-4 text-left text-sm transition ${
                hiringTarget === 'own'
                  ? 'border-brand-400 bg-brand-50/80 ring-2 ring-brand-200'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              {t('app.onboarding.setup.client.target_own', {
                defaultValue: 'For my own company',
              })}
            </button>
          </div>
          {error ? <ErrorRecoveryBanner info={error} compact /> : null}
          <button
            type="button"
            data-testid="m1-setup-client-continue"
            disabled={loading}
            onClick={() => void onAudienceContinue()}
            className="btn-primary w-full rounded-lg py-3 font-medium disabled:opacity-50"
          >
            {loading ? t('common.loading') : t('common.continue', { defaultValue: 'Continue' })}
          </button>
        </div>
      ) : (
        <form onSubmit={onClientSubmit} className="space-y-4">
          <div>
            <label htmlFor="setup-client-name" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.setup.client.name_label', { defaultValue: 'Company name' })}
            </label>
            <input
              id="setup-client-name"
              data-testid="m1-client-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder={t('app.onboarding.setup.client.name_placeholder', {
                defaultValue: 'e.g. North Logistics Sp. z o.o.',
              })}
              autoFocus
              required
            />
          </div>
          <div>
            <label htmlFor="setup-client-country" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.setup.client.country_label', { defaultValue: 'Country' })}
            </label>
            <select
              id="setup-client-country"
              data-testid="m1-client-country"
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
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
            <label htmlFor="setup-client-city" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.setup.client.city_label', { defaultValue: 'City' })}
            </label>
            {cityOptions.length > 0 ? (
              <select
                id="setup-client-city"
                data-testid="m1-client-city"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="">
                  {t('app.onboarding.setup.client.city_placeholder', {
                    defaultValue: 'Select a city…',
                  })}
                </option>
                {cityOptions.map((opt) => (
                  <option key={opt.value} value={opt.label}>
                    {opt.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id="setup-client-city"
                data-testid="m1-client-city"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder={t('app.onboarding.setup.client.city_placeholder_free', {
                  defaultValue: 'Warsaw',
                })}
              />
            )}
          </div>
          {error ? <ErrorRecoveryBanner info={error} compact /> : null}
          <div className="flex gap-2">
            <button
              type="button"
              className="btn-secondary rounded-lg px-4 py-3 text-sm"
              onClick={() => setStep('audience')}
              disabled={loading}
            >
              {t('common.back', { defaultValue: 'Back' })}
            </button>
            <button
              type="submit"
              data-testid="m1-client-save"
              disabled={loading}
              className="btn-primary flex-1 rounded-lg py-3 font-medium disabled:opacity-50"
            >
              {loading
                ? t('common.saving')
                : t('app.onboarding.setup.client.save_continue', { defaultValue: 'Continue' })}
            </button>
          </div>
        </form>
      )}
    </SetupFlowChrome>
  )
}
