import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { IconChecklist } from '@tabler/icons-react'
import { createOwnCompany, setActiveOwnCompany, ownCompanySettings, getOnboardingStatus } from '../../api/client'
import { getBillingSummary } from '../../api/billing'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import {
  readSignupSuccessContextFromSearch,
  readSignupSuccessContextFromSessionStorage,
  SIGNUP_SUCCESS_CONTEXT_KEY,
} from '../../constants/signupContext'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { recordTtvStepCompleted } from '../../api/analytics'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import {
  friendlyErrorBannerSecondary,
  friendlyFormHintError,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'
import {
  useCompanySetupCatalogs,
  resolvePlatformIdentityFromCatalog,
  resolveFirstModuleFromCatalog,
} from '../../hooks/useCompanySetupCatalogs'
import { catalogCountryLabel, catalogOptionLabel, catalogOptionDescription } from '../../utils/catalogOptions'
import type { CompanyActivityKey, FirstModuleKey, IndustryKey, TeamSizeKey } from '../../constants/companySetupCatalog'

const DRAFT_KEY = 'hf-platform-setup-draft-v1'

type SetupStep = 'identity' | 'intent' | 'details'

export default function PlatformSetupPage() {
  const { t, locale } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isRu = locale?.startsWith('ru')

  const [step, setStep] = useState<SetupStep>('identity')
  const [identity, setIdentity] = useState<CompanyActivityKey | ''>('')
  const [firstModule, setFirstModule] = useState<FirstModuleKey | ''>('')
  const [companyName, setCompanyName] = useState('')
  const [industry, setIndustry] = useState<IndustryKey | ''>('')
  const [teamSize, setTeamSize] = useState<TeamSizeKey | ''>('')
  const [countryCode, setCountryCode] = useState('PL')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [limitReached, setLimitReached] = useState(false)
  const [recommendedExtraSlots, setRecommendedExtraSlots] = useState<number | null>(null)
  const [hasAvailableOperatingSlots, setHasAvailableOperatingSlots] = useState(true)
  const [slotGuardLoading, setSlotGuardLoading] = useState(true)
  const { catalogs } = useCompanySetupCatalogs(locale)
  const industryOptions = catalogs.industries
  const teamSizeOptions = catalogs.team_sizes
  const countryOptions = catalogs.countries
  const platformIdentityOptions = catalogs.platform_identities
  const firstModuleOptions = catalogs.first_modules

  const signupContext = useMemo(
    () => readSignupSuccessContextFromSearch(searchParams) ?? readSignupSuccessContextFromSessionStorage(),
    [searchParams],
  )
  const signupSuccess = signupContext?.signup === 'success'

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(DRAFT_KEY)
      if (!raw) return
      const d = JSON.parse(raw) as Record<string, unknown>
      if (typeof d.identity === 'string') setIdentity(d.identity as CompanyActivityKey)
      if (typeof d.firstModule === 'string') setFirstModule(d.firstModule as FirstModuleKey)
      if (typeof d.companyName === 'string') setCompanyName(d.companyName)
      if (typeof d.industry === 'string') setIndustry(d.industry as IndustryKey)
      if (typeof d.teamSize === 'string') setTeamSize(d.teamSize as TeamSizeKey)
      if (typeof d.countryCode === 'string') setCountryCode(d.countryCode)
      if (typeof d.step === 'string') setStep(d.step as SetupStep)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    const h = window.setTimeout(() => {
      try {
        window.sessionStorage.setItem(
          DRAFT_KEY,
          JSON.stringify({ step, identity, firstModule, companyName, industry, teamSize, countryCode }),
        )
      } catch {
        // ignore
      }
    }, 400)
    return () => window.clearTimeout(h)
  }, [step, identity, firstModule, companyName, industry, teamSize, countryCode])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const billing = await getBillingSummary()
        if (!mounted) return
        const unlimited = Boolean(billing?.company_slots?.unlimited)
        const used = Number(billing?.company_slots?.used ?? 0)
        const effective = Number(billing?.company_slots?.effective_limit ?? 0)
        setPrecheckRecommendedExtraSlots(Math.max(1, used - effective + 1))
        const available = Number(billing?.company_slots?.available ?? 0)
        setHasAvailableOperatingSlots(unlimited || available > 0)
      } catch {
        if (mounted) setHasAvailableOperatingSlots(true)
      } finally {
        if (mounted) setSlotGuardLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (!signupSuccess) return
    try {
      window.sessionStorage.removeItem(SIGNUP_SUCCESS_CONTEXT_KEY)
    } catch {
      // ignore
    }
  }, [signupSuccess])

  useEffect(() => {
    let mounted = true
    void getOnboardingStatus()
      .then((status) => {
        if (!mounted) return
        if (status?.steps?.company_created) {
          navigate(CRM_APP_PATHS.launchpad, { replace: true })
        }
      })
      .catch(() => {
        /* stay on setup if status is unavailable */
      })
    return () => {
      mounted = false
    }
  }, [navigate])

  const onIdentityContinue = useCallback(() => {
    setError(null)
    if (!identity) {
      setError(
        friendlyFormHintError(
          t('app.platform_setup.errors.identity_required'),
          t,
        ),
      )
      return
    }
    const activity = resolvePlatformIdentityFromCatalog(identity, platformIdentityOptions)
    if (activity.industry_hint && !industry) {
      setIndustry(activity.industry_hint)
    }
    setStep('intent')
  }, [identity, industry, platformIdentityOptions, t])

  const onIntentContinue = useCallback(() => {
    setError(null)
    if (!firstModule) {
      setError(
        friendlyFormHintError(
          t('app.platform_setup.errors.module_required'),
          t,
        ),
      )
      return
    }
    const mod = resolveFirstModuleFromCatalog(firstModule, firstModuleOptions)
    if (!mod?.enabled) {
      setError(
        friendlyFormHintError(
          t('app.platform_setup.errors.module_unavailable'),
          t,
        ),
      )
      return
    }
    setStep('details')
  }, [firstModule, firstModuleOptions, t])

  async function onDetailsSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLimitReached(false)
    if (!companyName.trim()) {
      setError(friendlyFormHintError(t('app.platform_setup.errors.name_required'), t))
      return
    }
    if (!industry || !teamSize || !countryCode || !identity || !firstModule) {
      setError(friendlyFormHintError(t('app.platform_setup.errors.incomplete'), t))
      return
    }
    if (!hasAvailableOperatingSlots) {
      setLimitReached(true)
      setRecommendedExtraSlots(precheckRecommendedExtraSlots)
      setError({
        title: t('app.onboarding.company.errors.operating_limit'),
        hint: t('app.onboarding.company.errors.operating_limit_hint'),
      })
      return
    }

    const activity = resolvePlatformIdentityFromCatalog(identity, platformIdentityOptions)
    const businessType = activity.business_type
    const trimmed = companyName.trim()
    const countryOpt = countryOptions.find((c) => c.value === countryCode)
    const country = catalogCountryLabel(
      countryOpt ?? { value: countryCode, label: countryCode },
      locale,
      countryCode,
    )

    setLoading(true)
    try {
      await createOwnCompany({
        name: trimmed,
        business_type: businessType,
        industry,
        team_size: teamSize,
        workspace_name: trimmed,
        workspace_count: 1,
        country_code: countryCode === 'OTHER' ? undefined : countryCode,
        country: countryCode === 'OTHER' ? undefined : country,
        extra: {
          business_type: businessType,
          company_role: 'operating',
          company_type: businessType,
          industry,
          team_size: teamSize,
          platform_identity: activity.id,
          platform_first_module: firstModule,
          company_activity_profile: activity.id,
          business_model: activity.business_model,
          country_code: countryCode,
        },
      }).then(async (own) => {
        try {
          await setActiveOwnCompany(own.id)
          ownCompanySettings.set(own.id)
        } catch {
          // best-effort
        }
        return own
      })
      try {
        window.sessionStorage.removeItem(DRAFT_KEY)
      } catch {
        // ignore
      }
      void recordTtvStepCompleted({ event: 'ttv_step', action: 'completed', step_key: 'platform_configured' })
      navigate(CRM_APP_PATHS.launchpad, { replace: true })
    } catch (err: unknown) {
      const anyErr = err as { response?: { data?: { detail?: unknown }; status?: number } }
      const detailPayload = anyErr?.response?.data?.detail
      const detailCode = String(
        (typeof detailPayload === 'object' && detailPayload && ((detailPayload as Record<string, unknown>).code || (detailPayload as Record<string, unknown>).error_code)) ||
          detailPayload ||
          '',
      )
        .trim()
        .toUpperCase()
      if (
        detailCode === 'OPERATING-COMPANY-LIMIT' ||
        detailCode === 'COMPANY LIMIT REACHED FOR CURRENT PLAN' ||
        anyErr?.response?.status === 402
      ) {
        const rec =
          typeof detailPayload === 'object' && detailPayload
            ? Number((detailPayload as Record<string, unknown>).recommended_extra_slots || 0)
            : 0
        setLimitReached(true)
        setRecommendedExtraSlots(rec > 0 ? rec : 1)
        setError({
          title:
            rec > 0
              ? t('app.onboarding.company.errors.operating_limit_with_slots', { values: { count: rec } })
              : t('app.onboarding.company.errors.operating_limit'),
          hint: t('app.onboarding.company.errors.operating_limit_hint'),
        })
      } else {
        setLimitReached(false)
        const fb = t('app.platform_setup.errors.generic')
        if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
          setError(getFriendlyErrorInfo(err, fb, t))
        }
      }
    } finally {
      setLoading(false)
    }
  }

  const stepTitle = useMemo(() => {
    if (step === 'identity') {
      return t('app.platform_setup.identity_title')
    }
    if (step === 'intent') {
      return t('app.platform_setup.intent_title')
    }
    return t('app.platform_setup.details_title')
  }, [step, t])

  const stepSubtitle = useMemo(() => {
    if (step === 'identity') {
      return t('app.platform_setup.identity_subtitle')
    }
    if (step === 'intent') {
      return t('app.platform_setup.intent_subtitle')
    }
    return t('app.platform_setup.details_subtitle')
  }, [step, t])

  return (
    <div className="mx-auto max-w-3xl space-y-4" data-testid="m1-platform-setup">
      <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="inline-flex items-center gap-1 rounded-lg bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
          <IconChecklist size={14} stroke={1.9} />
          {t('app.platform_setup.badge')}
        </div>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">
          {t('app.platform_setup.welcome_title')}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.platform_setup.welcome_subtitle')}
        </p>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm" data-testid="m1-company-setup-step">
        <h2 className="text-lg font-semibold text-slate-900">{stepTitle}</h2>
        <p className="mt-1 text-sm text-slate-600">{stepSubtitle}</p>

        {step === 'identity' ? (
          <div className="mt-6 space-y-4">
            <div className="grid gap-2 sm:grid-cols-2" role="radiogroup">
              {platformIdentityOptions.map((opt) => {
                const selected = identity === opt.value
                const label = catalogOptionLabel(opt, locale)
                return (
                  <button
                    key={opt.value}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    data-testid={`m1-platform-identity-${opt.value}`}
                    onClick={() => setIdentity(opt.value as CompanyActivityKey)}
                    className={`rounded-xl border-2 p-3 text-left text-sm transition ${
                      selected
                        ? 'border-brand-400 bg-brand-50/80 ring-2 ring-brand-200'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <span className="mr-2" aria-hidden>
                      {opt.meta?.emoji}
                    </span>
                    {label}
                  </button>
                )
              })}
            </div>
            {error ? <ErrorRecoveryBanner info={error} compact /> : null}
            <button type="button" className="btn-primary w-full py-3" onClick={onIdentityContinue}>
              {t('common.continue')}
            </button>
          </div>
        ) : null}

        {step === 'intent' ? (
          <div className="mt-6 space-y-4">
            <div className="grid gap-2" role="radiogroup">
              {firstModuleOptions.map((opt) => {
                const selected = firstModule === opt.value
                const label = catalogOptionLabel(opt, locale)
                const desc = catalogOptionDescription(opt, locale)
                const enabled = Boolean(opt.meta?.enabled)
                return (
                  <button
                    key={opt.value}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    aria-disabled={!enabled}
                    data-testid={`m1-platform-module-${opt.value}`}
                    onClick={() => enabled && setFirstModule(opt.value as FirstModuleKey)}
                    className={`rounded-xl border-2 p-4 text-left text-sm transition ${
                      !enabled
                        ? 'cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400'
                        : selected
                          ? 'border-brand-400 bg-brand-50/80 ring-2 ring-brand-200'
                          : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <span className="mr-2" aria-hidden>
                      {opt.meta?.emoji}
                    </span>
                    <span className="font-medium">{label}</span>
                    {!enabled ? (
                      <span className="ml-2 text-xs text-slate-400">
                        {t('app.launchpad.coming_soon')}
                      </span>
                    ) : null}
                    <p className="mt-1 pl-6 text-xs text-slate-500">{desc}</p>
                  </button>
                )
              })}
            </div>
            {error ? <ErrorRecoveryBanner info={error} compact /> : null}
            <div className="flex gap-2">
              <button type="button" className="btn-secondary px-4 py-3" onClick={() => setStep('identity')}>
                {t('common.back')}
              </button>
              <button type="button" className="btn-primary flex-1 py-3" onClick={onIntentContinue}>
                {t('common.continue')}
              </button>
            </div>
          </div>
        ) : null}

        {step === 'details' ? (
          <form onSubmit={onDetailsSubmit} className="mt-6 space-y-4">
            {!slotGuardLoading && !hasAvailableOperatingSlots ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                <p className="font-medium">{t('app.onboarding.company.slot_guard.title')}</p>
                <Link
                  to={`${CRM_APP_PATHS.settingsBilling}?focus=company-slots&recommended_extra_slots=${precheckRecommendedExtraSlots}`}
                  className="btn-secondary btn-sm mt-2 inline-block"
                >
                  {t('app.onboarding.company.slot_guard.billing_link')}
                </Link>
              </div>
            ) : null}

            <div>
              <label htmlFor="platform-company-name" className="block text-sm font-medium text-slate-800">
                {t('app.platform_setup.name_label')}
              </label>
              <input
                id="platform-company-name"
                data-testid="m1-company-name"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                required
                minLength={2}
                autoFocus
              />
            </div>

            <div>
              <label htmlFor="platform-industry" className="block text-sm font-medium text-slate-800">
                {t('app.platform_setup.industry_label')}
              </label>
              <select
                id="platform-industry"
                data-testid="m1-company-industry-select"
                value={industry}
                onChange={(e) => setIndustry(e.target.value as IndustryKey)}
                className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm"
              >
                <option value="">{t('app.platform_setup.industry_placeholder')}</option>
                {industryOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {catalogOptionLabel(opt, locale)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="text-sm font-medium text-slate-800">
                {t('app.platform_setup.team_size_label')}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {teamSizeOptions.map((opt) => (
                  <label
                    key={opt.value}
                    className={`inline-flex cursor-pointer items-center rounded-full border px-3 py-2 text-xs font-medium ${
                      teamSize === opt.value
                        ? 'border-brand-500 bg-brand-50 text-brand-900'
                        : 'border-slate-200 bg-white text-slate-700'
                    }`}
                  >
                    <input
                      type="radio"
                      name="team_size"
                      value={opt.value}
                      data-testid={`m1-company-team-size-${opt.value}`}
                      checked={teamSize === opt.value}
                      onChange={() => setTeamSize(opt.value as TeamSizeKey)}
                      className="sr-only"
                    />
                    {catalogOptionLabel(opt, locale)}
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="platform-country" className="block text-sm font-medium text-slate-800">
                {t('app.platform_setup.country_label')}
              </label>
              <select
                id="platform-country"
                data-testid="m1-company-country"
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value)}
                className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm"
              >
                {countryOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {catalogOptionLabel(opt, locale)}
                  </option>
                ))}
              </select>
            </div>

            {error ? (
              <ErrorRecoveryBanner
                info={error}
                {...friendlyErrorBannerSecondary(
                  error,
                  limitReached
                    ? `${CRM_APP_PATHS.settingsBilling}?focus=company-slots&recommended_extra_slots=${recommendedExtraSlots ?? 1}`
                    : undefined,
                  limitReached ? t('app.onboarding.company.slot_guard.billing_link') : undefined,
                )}
                compact
              />
            ) : null}

            <div className="flex gap-2">
              <button type="button" className="btn-secondary px-4 py-3" onClick={() => setStep('intent')} disabled={loading}>
                {t('common.back')}
              </button>
              <button
                type="submit"
                data-testid="m1-company-save"
                disabled={loading || (!slotGuardLoading && !hasAvailableOperatingSlots)}
                className="btn-primary flex-1 py-3 disabled:opacity-50"
              >
                {loading ? t('common.saving') : t('app.platform_setup.finish')}
              </button>
            </div>
          </form>
        ) : null}
      </section>
    </div>
  )
}
