import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { IconCheck } from '@tabler/icons-react'
import { createOwnCompany, setActiveOwnCompany, ownCompanySettings, type OwnCompanyRecord } from '../api/client'
import { getBillingSummary } from '../api/billing'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import {
  readSignupSuccessContextFromSearch,
  readSignupSuccessContextFromSessionStorage,
  SIGNUP_SUCCESS_CONTEXT_KEY,
} from '../constants/signupContext'
import { ACTIVATION_PATHS } from '../app/activationRoutes'
import { recordTtvStepCompleted } from '../api/analytics'
import { CANDIDATES_QUICK_VIEW_NAV_PATHS } from '../modules/candidates/constants'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { friendlyErrorBannerSecondary, friendlyFormHintError, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { PageBreadcrumb } from '../components/nav/PageBreadcrumb'
type CompanyType = 'agency' | 'employer' | 'services'

type IndustryKey =
  | 'transport_logistics'
  | 'construction'
  | 'horeca'
  | 'healthcare'
  | 'it'
  | 'manufacturing'
  | 'other'

type TeamSizeKey = 'solo' | '2_5' | '6_10' | '11_25' | '25_plus'

/** Must match backend `working_hours_presets.PRESET` ids */
type HoursPresetKey =
  | 'weekdays_9_17'
  | 'weekdays_8_18'
  | 'weekdays_10_18'
  | 'shift_mornings'
  | 'shift_afternoons'
  | 'seven_day_9_17'
  | 'always_available'

const DRAFT_KEY = 'hf-onboarding-company-draft-v3'

type Phase = 'form' | 'magic' | 'ready'

type DemoSummary = NonNullable<OwnCompanyRecord['onboarding_demo']>

export default function OnboardingCompanyPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [phase, setPhase] = useState<Phase>('form')
  const [magicStep, setMagicStep] = useState(0)
  const [companyName, setCompanyName] = useState('')
  const [companyType, setCompanyType] = useState<CompanyType>('agency')
  const [industry, setIndustry] = useState<IndustryKey | ''>('')
  const [teamSize, setTeamSize] = useState<TeamSizeKey | ''>('')
  const [hoursPreset, setHoursPreset] = useState<HoursPresetKey>('weekdays_9_17')
  const [demoSummary, setDemoSummary] = useState<DemoSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [limitReached, setLimitReached] = useState(false)
  const [recommendedExtraSlots, setRecommendedExtraSlots] = useState<number | null>(null)
  const [hasAvailableOperatingSlots, setHasAvailableOperatingSlots] = useState(true)
  const [slotGuardLoading, setSlotGuardLoading] = useState(true)
  const [precheckRecommendedExtraSlots, setPrecheckRecommendedExtraSlots] = useState(1)
  const [automationUpsellOpen, setAutomationUpsellOpen] = useState(false)

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
    try {
      const raw = window.sessionStorage.getItem(DRAFT_KEY)
      if (!raw) return
      const d = JSON.parse(raw) as Record<string, unknown>
      if (typeof d.companyName === 'string') setCompanyName(d.companyName)
      if (d.companyType === 'agency' || d.companyType === 'employer' || d.companyType === 'services') {
        setCompanyType(d.companyType)
      }
      if (d.industry) setIndustry(d.industry as IndustryKey)
      if (d.teamSize) setTeamSize(d.teamSize as TeamSizeKey)
      const hp = d.hoursPreset as HoursPresetKey | undefined
      if (
        hp === 'weekdays_9_17' ||
        hp === 'weekdays_8_18' ||
        hp === 'weekdays_10_18' ||
        hp === 'shift_mornings' ||
        hp === 'shift_afternoons' ||
        hp === 'seven_day_9_17' ||
        hp === 'always_available'
      ) {
        setHoursPreset(hp)
      }
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    const h = window.setTimeout(() => {
      try {
        window.sessionStorage.setItem(
          DRAFT_KEY,
          JSON.stringify({ companyName, companyType, industry, teamSize, hoursPreset }),
        )
      } catch {
        // ignore
      }
    }, 400)
    return () => window.clearTimeout(h)
  }, [companyName, companyType, industry, teamSize, hoursPreset])

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
    if (phase !== 'magic') return
    setMagicStep(0)
    const t1 = window.setTimeout(() => setMagicStep(1), 500)
    const t2 = window.setTimeout(() => setMagicStep(2), 1000)
    const t3 = window.setTimeout(() => setMagicStep(3), 1500)
    return () => {
      window.clearTimeout(t1)
      window.clearTimeout(t2)
      window.clearTimeout(t3)
    }
  }, [phase])

  const industryOptions: { value: IndustryKey; label: string }[] = useMemo(
    () => [
      { value: 'transport_logistics', label: t('app.onboarding.company.industry.transport_logistics') },
      { value: 'construction', label: t('app.onboarding.company.industry.construction') },
      { value: 'horeca', label: t('app.onboarding.company.industry.horeca') },
      { value: 'healthcare', label: t('app.onboarding.company.industry.healthcare') },
      { value: 'it', label: t('app.onboarding.company.industry.it') },
      { value: 'manufacturing', label: t('app.onboarding.company.industry.manufacturing') },
      { value: 'other', label: t('app.onboarding.company.industry.other') },
    ],
    [t],
  )

  const hoursPresetOptions: { value: HoursPresetKey; label: string }[] = useMemo(
    () => [
      {
        value: 'weekdays_9_17',
        label: t('app.onboarding.company.hours.weekdays_9_17'),
      },
      {
        value: 'weekdays_8_18',
        label: t('app.onboarding.company.hours.weekdays_8_18'),
      },
      {
        value: 'weekdays_10_18',
        label: t('app.onboarding.company.hours.weekdays_10_18'),
      },
      {
        value: 'shift_mornings',
        label: t('app.onboarding.company.hours.shift_mornings'),
      },
      {
        value: 'shift_afternoons',
        label: t('app.onboarding.company.hours.shift_afternoons'),
      },
      {
        value: 'seven_day_9_17',
        label: t('app.onboarding.company.hours.seven_day'),
      },
      {
        value: 'always_available',
        label: t('app.onboarding.company.hours.always'),
      },
    ],
    [t],
  )

  const teamChips: { value: TeamSizeKey; label: string }[] = useMemo(
    () => [
      { value: 'solo', label: t('app.onboarding.company.team_chip.solo') },
      { value: '2_5', label: t('app.onboarding.company.team_chip.2_5') },
      { value: '6_10', label: t('app.onboarding.company.team_chip.6_10') },
      { value: '11_25', label: t('app.onboarding.company.team_chip.11_25') },
      { value: '25_plus', label: t('app.onboarding.company.team_chip.25_plus') },
    ],
    [t],
  )

  const typeCards = useMemo(
    () =>
      [
        {
          value: 'agency' as const,
          title: t('app.onboarding.company.type_card.agency_title'),
          desc: t('app.onboarding.company.type_card.agency_desc'),
          accent: 'border-sky-400 bg-sky-50/80 ring-sky-200',
          idle: 'border-slate-200 hover:border-slate-300',
        },
        {
          value: 'employer' as const,
          title: t('app.onboarding.company.type_card.employer_title'),
          desc: t('app.onboarding.company.type_card.employer_desc'),
          accent: 'border-emerald-400 bg-emerald-50/80 ring-emerald-200',
          idle: 'border-slate-200 hover:border-slate-300',
        },
        {
          value: 'services' as const,
          title: t('app.onboarding.company.type_card.services_title'),
          desc: t('app.onboarding.company.type_card.services_desc'),
          accent: 'border-violet-400 bg-violet-50/80 ring-violet-200',
          idle: 'border-slate-200 hover:border-slate-300',
        },
      ] as const,
    [t],
  )

  const validateForm = useCallback(() => {
    const trimmed = companyName.trim()
    if (!trimmed) {
      setLimitReached(false)
      setError(friendlyFormHintError(t('app.onboarding.company.errors.name_required'), t))
      return false
    }
    if (!industry) {
      setLimitReached(false)
      setError(friendlyFormHintError(t('app.onboarding.company.errors.industry_required'), t))
      return false
    }
    if (!teamSize) {
      setLimitReached(false)
      setError(friendlyFormHintError(t('app.onboarding.company.errors.team_size_required'), t))
      return false
    }
    return true
  }, [companyName, industry, teamSize, t])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLimitReached(false)
    if (!validateForm()) return
    if (!hasAvailableOperatingSlots) {
      setLimitReached(true)
      setRecommendedExtraSlots(precheckRecommendedExtraSlots)
      setError({
        title: t('app.onboarding.company.errors.operating_limit'),
        hint: t('app.onboarding.company.errors.operating_limit_hint'),
      })
      return
    }

    setLoading(true)
    try {
      const trimmed = companyName.trim()
      const own = await createOwnCompany({
        name: trimmed,
        business_type: companyType,
        industry: industry || undefined,
        team_size: teamSize || undefined,
        workspace_name: trimmed,
        workspace_count: 1,
        working_hours_preset: hoursPreset,
        extra: { business_type: companyType },
      })
      try {
        await setActiveOwnCompany(own.id)
        ownCompanySettings.set(own.id)
      } catch {
        // best-effort
      }
      try {
        window.sessionStorage.removeItem(DRAFT_KEY)
      } catch {
        // ignore
      }
      void recordTtvStepCompleted({ event: 'ttv_step', action: 'completed', step_key: 'company_created' })
      setDemoSummary((own as OwnCompanyRecord).onboarding_demo ?? null)
      setPhase('magic')
      window.setTimeout(() => setPhase('ready'), 1800)
    } catch (err: any) {
      const detailPayload = err?.response?.data?.detail
      const detailCode = String(
        (typeof detailPayload === 'object' && detailPayload && (detailPayload.code || detailPayload.error_code)) ||
          detailPayload ||
          '',
      )
        .trim()
        .toUpperCase()
      if (detailCode === 'OPERATING-COMPANY-LIMIT' || detailCode === 'COMPANY LIMIT REACHED FOR CURRENT PLAN' || err?.response?.status === 402) {
        const rec =
          typeof detailPayload === 'object' && detailPayload
            ? Number((detailPayload as Record<string, any>).recommended_extra_slots || 0)
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
        const fb = t('app.onboarding.company.errors.generic')
        if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
          setError(getFriendlyErrorInfo(err, fb, t))
        }
      }
    } finally {
      setLoading(false)
    }
  }

  const entityWord =
    demoSummary?.entity === 'leads'
      ? t('app.onboarding.ready.leads')
      : t('app.onboarding.ready.candidates')

  const stuckLabel =
    companyType === 'services'
      ? t('app.onboarding.ready.stuck_negotiation')
      : companyType === 'employer'
        ? t('app.onboarding.ready.stuck_interview')
        : t('app.onboarding.ready.stuck_docs')

  if (phase === 'magic') {
    const lines = [
      { done: magicStep >= 1, text: t('app.onboarding.magic.line_pipeline') },
      { done: magicStep >= 2, text: t('app.onboarding.magic.line_stages') },
      { done: magicStep >= 3, text: t('app.onboarding.magic.line_dashboard') },
    ]
    return (
      <div className="mx-auto flex w-full max-w-md flex-col items-center justify-center space-y-4 px-4 py-12">
        <PageBreadcrumb className="w-full max-w-full self-stretch" />
        <img src="/logo_hf.svg" alt="" className="h-10 w-auto opacity-90" />
        <h1 className="mt-8 text-lg font-semibold text-slate-900">{t('app.onboarding.magic.title')}</h1>
        <ul className="mt-6 w-full space-y-3 text-sm text-slate-700">
          {lines.map((ln) => (
            <li key={ln.text} className="flex items-center gap-2 rounded-lg border border-slate-100 bg-white px-3 py-2 shadow-sm">
              {ln.done ? (
                <IconCheck size={18} className="text-emerald-600" stroke={2.2} />
              ) : (
                <span className="inline-block h-4 w-4 animate-pulse rounded-full bg-slate-200" />
              )}
              {ln.text}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  if (phase === 'ready') {
    const total = demoSummary?.pipeline_total ?? 12
    const need = demoSummary?.need_action ?? 3
    const stuck = demoSummary?.stuck ?? 2
    return (
      <div className="mx-auto max-w-lg space-y-4 px-4 py-12">
        <PageBreadcrumb className="max-w-full" />
        <img src="/logo_hf.svg" alt="" className="h-10 w-auto" />
        <h1 className="mt-6 text-2xl font-semibold text-slate-900">{t('app.onboarding.ready.page_title')}</h1>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.onboarding.ready.subtitle')}
        </p>
        <ul className="mt-6 space-y-2 rounded-xl border border-slate-200 bg-white p-5 text-sm shadow-sm">
          <li className="flex justify-between gap-4">
            <span className="text-slate-600">
              {t('app.onboarding.ready.in_pipeline')}
            </span>
            <span className="font-semibold text-slate-900">
              {total} {entityWord}
            </span>
          </li>
          <li className="flex justify-between gap-4">
            <span className="text-amber-800">{t('app.onboarding.ready.need_action')}</span>
            <span className="font-semibold text-amber-900">{need}</span>
          </li>
          <li className="flex justify-between gap-4">
            <span className="text-rose-800">{stuckLabel}</span>
            <span className="font-semibold text-rose-900">{stuck}</span>
          </li>
        </ul>
        <button
          type="button"
          className="btn-primary mt-8 w-full rounded-lg py-2.5 font-medium"
          onClick={() => navigate(`${ACTIVATION_PATHS.overview}?welcome=1`, { replace: true })}
        >
          {t('app.onboarding.ready.cta')}
        </button>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            className="btn-secondary flex-1 rounded-lg py-2 text-sm font-medium"
            onClick={() => {
              const href =
                companyType === 'services' ? ACTIVATION_PATHS.leads : CANDIDATES_QUICK_VIEW_NAV_PATHS.no_next_action
              navigate(href)
            }}
          >
            {t('app.onboarding.ready.assign_next')}
          </button>
          <button
            type="button"
            className="btn-secondary flex-1 rounded-lg py-2 text-sm font-medium"
            onClick={() => setAutomationUpsellOpen(true)}
          >
            {t('app.onboarding.ready.enable_automation')}
          </button>
        </div>

        {automationUpsellOpen ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog">
            <div className="max-w-sm rounded-2xl bg-white p-6 shadow-xl">
              <div className="text-lg font-semibold text-slate-900">
                {t('app.onboarding.upsell.automation_title')}
              </div>
              <p className="mt-2 text-sm text-slate-600">
                {t('app.onboarding.upsell.automation_body')}
              </p>
              <div className="mt-4 flex gap-2">
                <button type="button" className="btn-secondary flex-1" onClick={() => setAutomationUpsellOpen(false)}>
                  {t('common.actions.close')}
                </button>
                <Link to={`${ACTIVATION_PATHS.billing}?focus=plan`} className="btn-primary flex-1 text-center">
                  {t('app.onboarding.upsell.view_plans')}
                </Link>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <PageBreadcrumb className="max-w-full" />
      <div className="card rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex justify-center">
          <img src="/logo_hf.svg" alt="HostFlow" className="h-11 w-auto" />
        </div>
        <h1 className="mt-6 text-center text-xl font-semibold text-slate-900">
          {t('app.onboarding.workspace.title')}
        </h1>
        {signupSuccess && (
          <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-center text-xs text-emerald-900">
            {trialEndsText
              ? t('app.onboarding.company.signup_success_with_trial', { values: { date: trialEndsText } })
              : t('app.onboarding.company.signup_success')}
            {welcomeEmailStatus === 'not_sent' ? (
              <div className="mt-1 text-emerald-800/90">
                {t('app.onboarding.company.signup_success_email_not_sent')}
              </div>
            ) : null}
          </div>
        )}

        <form onSubmit={onSubmit} className="mt-6 space-y-6">
          {!slotGuardLoading && !hasAvailableOperatingSlots ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              <p className="font-medium">{t('app.onboarding.company.slot_guard.title')}</p>
              <Link
                to={`${ACTIVATION_PATHS.billing}?focus=company-slots&recommended_extra_slots=${precheckRecommendedExtraSlots}`}
                className="btn-secondary btn-sm mt-2 inline-block"
              >
                {t('app.onboarding.company.slot_guard.billing_link')}
              </Link>
            </div>
          ) : null}

          <div>
            <label htmlFor="oc-name" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.workspace.company_name')}
            </label>
            <input
              id="oc-name"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder={t('app.onboarding.company.name_placeholder')}
              autoFocus
            />
          </div>

          <div>
            <div className="text-sm font-medium text-slate-800">
              {t('app.onboarding.workspace.business_type')}
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {t('app.onboarding.workspace.pipeline_hint')}
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              {typeCards.map((card) => (
                <button
                  key={card.value}
                  type="button"
                  onClick={() => setCompanyType(card.value)}
                  className={`rounded-xl border-2 p-3 text-left text-sm transition ring-2 ring-transparent ${
                    companyType === card.value ? `${card.accent} ring-opacity-50` : card.idle
                  } `}
                >
                  <div className="font-semibold text-slate-900">{card.title}</div>
                  <p className="mt-1 text-xs leading-snug text-slate-600">{card.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="oc-industry" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.company.industry_label')}
            </label>
            <select
              id="oc-industry"
              value={industry}
              onChange={(e) => setIndustry(e.target.value as IndustryKey | '')}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">{t('app.onboarding.company.select_placeholder')}</option>
              {industryOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div className="block text-sm font-medium text-slate-800">{t('app.onboarding.company.team_size_label')}</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {teamChips.map((c) => (
                <label
                  key={c.value}
                  className={`inline-flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium ${
                    teamSize === c.value
                      ? 'border-brand-500 bg-brand-50 text-brand-900'
                      : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="team_size"
                    value={c.value}
                    checked={teamSize === c.value}
                    onChange={() => setTeamSize(c.value)}
                    className="sr-only"
                  />
                  {c.label}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="oc-hours-preset" className="block text-sm font-medium text-slate-800">
              {t('app.onboarding.company.hours.label')}
            </label>
            <p className="mt-0.5 text-xs text-slate-500">
              {t('app.onboarding.company.hours.hint')}
            </p>
            <select
              id="oc-hours-preset"
              value={hoursPreset}
              onChange={(e) => setHoursPreset(e.target.value as HoursPresetKey)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {hoursPresetOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          {error ? (
            <ErrorRecoveryBanner
              info={error}
              onRetry={() => setError(null)}
              retryLabel={t('common.actions.close')}
              {...friendlyErrorBannerSecondary(
                error,
                limitReached
                  ? `${ACTIVATION_PATHS.billing}?focus=company-slots&recommended_extra_slots=${recommendedExtraSlots ?? 1}`
                  : undefined,
                limitReached ? t('app.onboarding.company.slot_guard.billing_link') : undefined,
              )}
              compact
            />
          ) : null}

          <button
            type="submit"
            disabled={loading || (!slotGuardLoading && !hasAvailableOperatingSlots)}
            className="btn-primary w-full rounded-lg py-2.5 font-medium disabled:opacity-50"
          >
            {loading
              ? t('common.saving')
              : t('app.onboarding.workspace.continue')}
          </button>
        </form>
      </div>
    </div>
  )
}
