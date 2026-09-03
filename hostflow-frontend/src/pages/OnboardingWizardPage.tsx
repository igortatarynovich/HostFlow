import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  IconArrowLeft,
  IconArrowRight,
  IconBolt,
  IconBrandFacebook,
  IconCheck,
  IconExternalLink,
  IconHome,
  IconLink,
  IconRoute,
  IconSparkles,
} from '@tabler/icons-react'

import { useI18n } from '../i18n'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { ACTIVATION_PATHS } from '../app/activationRoutes'
import {
  createClientCompany,
  getOnboardingStatus,
  getOnboardingWizard,
  getOnboardingWizardFirstLead,
  listCompanies,
  listOwnCompanies,
  postOnboardingWizardStep,
  seedOnboardingDemo,
  type OnboardingStatus,
  type OnboardingWizardChannel,
  type OnboardingWizardFirstLead,
  type OnboardingWizardState,
  type OnboardingWizardStepKey,
} from '../api/client'
import { createVacancy } from '../api/vacancies'
import { resolveOperatingCompanyId } from '../services/createLaunchSearch'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { useSeoMeta } from '../hooks/useSeoMeta'

type StepKey = OnboardingWizardStepKey

type StepDef = {
  key: StepKey
  num: number
  title: string
  hint: string
  optional: boolean
}

const STEP_ORDER: StepKey[] = ['type', 'client', 'vacancy', 'channel', 'first_lead']

function nextStepFor(current: StepKey, businessType: OnboardingStatus['business_type']): StepKey {
  const idx = STEP_ORDER.indexOf(current)
  for (let i = idx + 1; i < STEP_ORDER.length; i += 1) {
    const cand = STEP_ORDER[i]
    if (cand === 'client' && businessType === 'employer') continue
    if (cand === 'vacancy' && businessType === 'services') continue
    return cand
  }
  return 'first_lead'
}

function prevStepFor(current: StepKey, businessType: OnboardingStatus['business_type']): StepKey | null {
  const idx = STEP_ORDER.indexOf(current)
  for (let i = idx - 1; i >= 0; i -= 1) {
    const cand = STEP_ORDER[i]
    if (cand === 'client' && businessType === 'employer') continue
    if (cand === 'vacancy' && businessType === 'services') continue
    return cand
  }
  return null
}

export default function OnboardingWizardPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  useSeoMeta({
    title: t('app.onboarding.wizard.seo_title', { defaultValue: 'Setup wizard — HostFlow' }),
    description: t('app.onboarding.wizard.seo_description', {
      defaultValue: 'Five-minute setup wizard: business type, first client, vacancy, lead channel, and demo lead with NBA.',
    }),
    canonicalPath: CRM_APP_PATHS.onboardingWizard,
  })

  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [wizard, setWizard] = useState<OnboardingWizardState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const refreshStatus = useCallback(async () => {
    const fresh = await getOnboardingStatus()
    setStatus(fresh)
    return fresh
  }, [])

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [s, w] = await Promise.all([getOnboardingStatus(), getOnboardingWizard()])
      setStatus(s)
      setWizard(w)
    } catch (err) {
      setError(getFriendlyErrorInfo(err, t('app.onboarding.wizard.errors.load', { defaultValue: 'Failed to load wizard state' }), t))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void reload()
  }, [reload])

  const businessType = status?.business_type ?? 'agency'

  const stepsDef = useMemo<StepDef[]>(
    () => [
      {
        key: 'type',
        num: 1,
        title: t('app.onboarding.wizard.steps.type.title', { defaultValue: 'Business type' }),
        hint: t('app.onboarding.wizard.steps.type.hint', { defaultValue: 'Choose how HostFlow should shape your pipeline.' }),
        optional: false,
      },
      {
        key: 'client',
        num: 2,
        title: t('app.onboarding.wizard.steps.client.title', { defaultValue: 'First client' }),
        hint: t('app.onboarding.wizard.steps.client.hint', { defaultValue: 'Add the client you hire for (or skip if you only hire to your own company).' }),
        optional: true,
      },
      {
        key: 'vacancy',
        num: 3,
        title: t('app.onboarding.wizard.steps.vacancy.title', { defaultValue: 'First vacancy' }),
        hint: t('app.onboarding.wizard.steps.vacancy.hint', { defaultValue: 'Add a vacancy to route incoming candidates.' }),
        optional: false,
      },
      {
        key: 'channel',
        num: 4,
        title: t('app.onboarding.wizard.steps.channel.title', { defaultValue: 'Lead channel' }),
        hint: t('app.onboarding.wizard.steps.channel.hint', { defaultValue: 'Connect a source after the vacancy exists so leads have somewhere to land.' }),
        optional: true,
      },
      {
        key: 'first_lead',
        num: 5,
        title: t('app.onboarding.wizard.steps.first_lead.title', { defaultValue: 'First lead with NBA' }),
        hint: t('app.onboarding.wizard.steps.first_lead.hint', { defaultValue: 'See the next-best-action HostFlow recommends.' }),
        optional: false,
      },
    ],
    [t],
  )

  const visibleSteps = useMemo(
    () =>
      stepsDef.filter((step) => {
        if (step.key === 'client' && businessType === 'employer') return false
        if (step.key === 'vacancy' && businessType === 'services') return false
        return true
      }),
    [stepsDef, businessType],
  )

  // If user hasn't created an own_company yet, the wizard cannot run — bounce
  // to the dedicated company creation page (which auto-returns here on success).
  useEffect(() => {
    if (loading) return
    if (status && status.onboarding_required) {
      navigate(`${CRM_APP_PATHS.onboardingCompany}?return=wizard`, { replace: true })
    }
  }, [loading, status, navigate])

  const currentStep: StepKey = wizard?.current_step ?? 'type'
  const currentDef = stepsDef.find((s) => s.key === currentStep) ?? stepsDef[0]
  const currentVisibleIdx = visibleSteps.findIndex((s) => s.key === currentStep)
  const isLast = currentVisibleIdx === visibleSteps.length - 1

  const persistStep = useCallback(
    async (input: {
      step: StepKey
      completed?: boolean
      skipped?: boolean
      data?: Record<string, unknown>
      channel?: OnboardingWizardChannel
      finished?: boolean
      goToNext?: boolean
    }) => {
      const next = input.goToNext === false
        ? null
        : nextStepFor(input.step, businessType)
      const updated = await postOnboardingWizardStep({
        step: input.step,
        completed: input.completed ?? true,
        skipped: input.skipped ?? false,
        data: input.data ?? null,
        channel: input.channel ?? null,
        next_step: next,
        finished: input.finished ?? false,
      })
      setWizard(updated)
      return updated
    },
    [businessType],
  )

  const handleSkip = useCallback(
    async (step: StepKey) => {
      try {
        await persistStep({ step, completed: true, skipped: true })
      } catch (err) {
        setError(getFriendlyErrorInfo(err, t('app.onboarding.wizard.errors.save', { defaultValue: 'Failed to save progress' }), t))
      }
    },
    [persistStep, t],
  )

  const handleBack = useCallback(async () => {
    if (!wizard) return
    const prev = prevStepFor(currentStep, businessType)
    if (!prev) return
    try {
      const updated = await postOnboardingWizardStep({
        step: currentStep,
        completed: false,
        next_step: prev,
      })
      setWizard(updated)
    } catch (err) {
      setError(getFriendlyErrorInfo(err, t('app.onboarding.wizard.errors.save', { defaultValue: 'Failed to save progress' }), t))
    }
  }, [wizard, currentStep, businessType, t])

  const handleFinish = useCallback(async () => {
    try {
      await persistStep({ step: 'first_lead', completed: true, finished: true, goToNext: false })
      navigate(ACTIVATION_PATHS.overview)
    } catch (err) {
      setError(getFriendlyErrorInfo(err, t('app.onboarding.wizard.errors.save', { defaultValue: 'Failed to save progress' }), t))
    }
  }, [persistStep, navigate, t])

  const stepBody = useMemo<ReactNode>(() => {
    if (loading || !wizard || !status) {
      return <div className="text-sm text-slate-500">{t('common.loading')}</div>
    }
    switch (currentStep) {
      case 'type':
        return (
          <StepType
            status={status}
            onContinue={async () => {
              await persistStep({ step: 'type' })
            }}
          />
        )
      case 'channel':
        return (
          <StepChannel
            wizard={wizard}
            onChoose={async (channel) => {
              await persistStep({ step: 'channel', channel, data: { channel } })
            }}
            onSkip={() => handleSkip('channel')}
          />
        )
      case 'client':
        return (
          <StepClient
            onCreated={async (companyId, name) => {
              await persistStep({ step: 'client', data: { company_id: companyId, name } })
              await refreshStatus()
            }}
            onSkip={() => handleSkip('client')}
          />
        )
      case 'vacancy':
        return (
          <StepVacancy
            onCreated={async (vacancyId, title) => {
              await persistStep({ step: 'vacancy', data: { vacancy_id: vacancyId, title } })
              await refreshStatus()
            }}
            onSkip={() => handleSkip('vacancy')}
          />
        )
      case 'first_lead':
      default:
        return (
          <StepFirstLead
            onFinish={handleFinish}
          />
        )
    }
  }, [loading, wizard, status, currentStep, persistStep, handleSkip, refreshStatus, handleFinish, t])

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={currentDef?.title}
          subtitle={currentDef?.hint}
          kind="browse"
          secondaryActions={
            <>
              <span className="text-xs text-slate-500">
                {t('app.onboarding.wizard.step_counter', {
                  defaultValue: 'Step {n} of {total}',
                  values: { n: currentVisibleIdx + 1, total: visibleSteps.length },
                })}
              </span>
              <Link
                to={CRM_APP_PATHS.overview}
                className="btn-secondary btn-sm inline-flex items-center gap-1"
              >
                <IconHome size={14} aria-hidden />
                {t('app.onboarding.wizard.exit', { defaultValue: 'Exit to dashboard' })}
              </Link>
            </>
          }
        />
      </PageShellHeader>
      <div className="mx-auto flex min-h-0 w-full max-w-5xl flex-1 gap-6 overflow-y-auto px-4 pb-4">
      <aside className="hidden w-64 shrink-0 lg:block">
        <ProgressRail
          steps={visibleSteps}
          completed={new Set(wizard?.completed_steps ?? [])}
          skipped={new Set(wizard?.skipped_steps ?? [])}
          currentStep={currentStep}
        />
      </aside>
      <main className="min-w-0 flex-1 space-y-4">
        {error ? (
          <ErrorRecoveryBanner info={error} onRetry={() => setError(null)} retryLabel={t('common.actions.close')} compact />
        ) : null}
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-end gap-3">
            <p className="mr-auto text-xs font-medium uppercase tracking-wide text-brand-700">
              {t('app.onboarding.wizard.kicker', {
                defaultValue: 'First value in 5 minutes',
              })}
            </p>
            {currentDef?.optional ? (
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">
                {t('app.onboarding.wizard.optional', { defaultValue: 'Optional' })}
              </span>
            ) : null}
          </div>
          {stepBody}
        </section>
        <footer className="flex items-center justify-between text-xs text-slate-500">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 transition hover:bg-slate-100 disabled:opacity-40"
            onClick={() => void handleBack()}
            disabled={!prevStepFor(currentStep, businessType)}
          >
            <IconArrowLeft size={14} aria-hidden />
            {t('app.onboarding.wizard.back', { defaultValue: 'Back' })}
          </button>
          {currentDef?.optional && !isLast ? (
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-slate-600 transition hover:bg-slate-100"
              onClick={() => void handleSkip(currentStep)}
            >
              {t('app.onboarding.wizard.skip', { defaultValue: 'Skip for now' })}
              <IconArrowRight size={14} aria-hidden />
            </button>
          ) : null}
        </footer>
      </main>
      </div>
    </PageShell>
  )
}

// ---------------------------------------------------------------------------
// Progress rail
// ---------------------------------------------------------------------------

function ProgressRail({
  steps,
  completed,
  skipped,
  currentStep,
}: {
  steps: StepDef[]
  completed: Set<StepKey>
  skipped: Set<StepKey>
  currentStep: StepKey
}) {
  const { t } = useI18n()
  return (
    <ol className="space-y-2">
      {steps.map((step) => {
        const isDone = completed.has(step.key)
        const isCurrent = step.key === currentStep
        const isSkipped = skipped.has(step.key)
        return (
          <li
            key={step.key}
            className={`rounded-xl border px-3 py-3 transition ${
              isCurrent
                ? 'border-brand-500 bg-brand-50/60 shadow-sm'
                : isDone
                  ? 'border-emerald-200 bg-white'
                  : 'border-slate-200 bg-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  isDone
                    ? 'bg-emerald-100 text-emerald-700'
                    : isCurrent
                      ? 'bg-brand-600 text-white'
                      : 'bg-slate-100 text-slate-500'
                }`}
              >
                {isDone ? <IconCheck size={14} stroke={2.5} /> : step.num}
              </span>
              <span
                className={`min-w-0 flex-1 truncate text-sm ${
                  isCurrent ? 'font-semibold text-slate-900' : 'text-slate-700'
                }`}
              >
                {step.title}
              </span>
            </div>
            {isSkipped ? (
              <p className="mt-1 pl-8 text-[11px] text-slate-500">
                {t('app.onboarding.wizard.skipped_label', { defaultValue: 'Skipped' })}
              </p>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}

// ---------------------------------------------------------------------------
// Step 1 — Type / company
// ---------------------------------------------------------------------------

function StepType({ status, onContinue }: { status: OnboardingStatus; onContinue: () => Promise<void> }) {
  const { t } = useI18n()
  const [busy, setBusy] = useState(false)
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 text-sm text-emerald-900">
        <div className="flex items-center gap-2 font-semibold">
          <IconCheck size={16} aria-hidden />
          {t('app.onboarding.wizard.steps.type.workspace_ready', { defaultValue: 'Workspace ready' })}
        </div>
        <p className="mt-1 text-emerald-800">
          {t('app.onboarding.wizard.steps.type.profile', {
            defaultValue: 'Profile: {profile} · Companies in workspace: {count}',
            values: {
              profile: t(`app.onboarding.company_type.${status.business_type}`, { defaultValue: status.business_type }),
              count: status.companies_count,
            },
          })}
        </p>
      </div>
      <p className="text-sm text-slate-600">
        {t('app.onboarding.wizard.steps.type.continue_hint', {
          defaultValue: 'Your business profile drives pipeline shape and lead routing. You can still change it later in Settings → My company.',
        })}
      </p>
      <button
        type="button"
        className="btn-primary"
        disabled={busy}
        onClick={async () => {
          setBusy(true)
          try {
            await onContinue()
          } finally {
            setBusy(false)
          }
        }}
      >
        {t('app.onboarding.wizard.steps.type.continue', { defaultValue: 'Continue →' })}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 2 — Lead channel
// ---------------------------------------------------------------------------

type ChannelOption = {
  key: OnboardingWizardChannel
  title: string
  description: string
  icon: ReactNode
  cta: string
  to?: string
}

function StepChannel({
  wizard,
  onChoose,
  onSkip,
}: {
  wizard: OnboardingWizardState
  onChoose: (channel: OnboardingWizardChannel) => Promise<void>
  onSkip: () => void
}) {
  const { t } = useI18n()
  const [picked, setPicked] = useState<OnboardingWizardChannel | null>(wizard.channel)
  const [busy, setBusy] = useState(false)

  const options = useMemo<ChannelOption[]>(
    () => [
      {
        key: 'meta',
        title: t('app.onboarding.wizard.steps.channel.meta_title', { defaultValue: 'Meta Lead Ads' }),
        description: t('app.onboarding.wizard.steps.channel.meta_desc', {
          defaultValue: 'Pull leads from Facebook and Instagram lead forms.',
        }),
        icon: <IconBrandFacebook size={20} aria-hidden />,
        cta: t('app.onboarding.wizard.steps.channel.meta_cta', { defaultValue: 'Open Meta integration' }),
        to: CRM_APP_PATHS.settingsIntegrationsMeta,
      },
      {
        key: 'public_intake',
        title: t('app.onboarding.wizard.steps.channel.public_title', { defaultValue: 'Public intake form' }),
        description: t('app.onboarding.wizard.steps.channel.public_desc', {
          defaultValue: 'Share a public link or QR code that fills your CRM directly.',
        }),
        icon: <IconLink size={20} aria-hidden />,
        cta: t('app.onboarding.wizard.steps.channel.public_cta', { defaultValue: 'Configure forms' }),
        to: CRM_APP_PATHS.settingsLeadForms ?? CRM_APP_PATHS.settings,
      },
      {
        key: 'webhook',
        title: t('app.onboarding.wizard.steps.channel.webhook_title', { defaultValue: 'Custom webhook' }),
        description: t('app.onboarding.wizard.steps.channel.webhook_desc', {
          defaultValue: 'Send leads from your landing page or another system.',
        }),
        icon: <IconRoute size={20} aria-hidden />,
        cta: t('app.onboarding.wizard.steps.channel.webhook_cta', { defaultValue: 'Open webhook setup' }),
        to: CRM_APP_PATHS.settingsIntegrationsWebhook,
      },
      {
        key: 'manual',
        title: t('app.onboarding.wizard.steps.channel.manual_title', { defaultValue: 'Add leads manually' }),
        description: t('app.onboarding.wizard.steps.channel.manual_desc', {
          defaultValue: 'No external source — you’ll add leads from inside HostFlow.',
        }),
        icon: <IconBolt size={20} aria-hidden />,
        cta: t('app.onboarding.wizard.steps.channel.manual_cta', { defaultValue: 'Continue' }),
      },
    ],
    [t],
  )

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        {options.map((opt) => {
          const active = picked === opt.key
          return (
            <button
              key={opt.key}
              type="button"
              onClick={() => setPicked(opt.key)}
              className={`flex h-full flex-col items-start rounded-xl border-2 p-4 text-left transition ${
                active
                  ? 'border-brand-500 bg-brand-50/40 ring-2 ring-brand-200'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <span
                aria-hidden
                className={`rounded-lg p-2 ${
                  active ? 'bg-brand-100 text-brand-700' : 'bg-slate-100 text-slate-700'
                }`}
              >
                {opt.icon}
              </span>
              <div className="mt-3 text-sm font-semibold text-slate-900">{opt.title}</div>
              <p className="mt-1 text-xs leading-tight text-slate-600">{opt.description}</p>
              {opt.to ? (
                <Link
                  to={opt.to}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  {opt.cta}
                  <IconExternalLink size={12} aria-hidden />
                </Link>
              ) : null}
            </button>
          )
        })}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="btn-primary"
          disabled={!picked || busy}
          onClick={async () => {
            if (!picked) return
            setBusy(true)
            try {
              await onChoose(picked)
            } finally {
              setBusy(false)
            }
          }}
        >
          {t('app.onboarding.wizard.steps.channel.save', { defaultValue: 'Save and continue' })}
        </button>
        <button type="button" className="btn-secondary" onClick={onSkip} disabled={busy}>
          {t('app.onboarding.wizard.skip', { defaultValue: 'Skip for now' })}
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 3 — First client
// ---------------------------------------------------------------------------

function StepClient({
  onCreated,
  onSkip,
}: {
  onCreated: (companyId: string, name: string) => Promise<void>
  onSkip: () => void
}) {
  const { t } = useI18n()
  const [name, setName] = useState('')
  const [vat, setVat] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<FriendlyErrorInfo | null>(null)

  const submit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault()
      const trimmed = name.trim()
      if (!trimmed) {
        setErr({
          title: t('app.onboarding.wizard.steps.client.errors.name_required', {
            defaultValue: 'Enter client name',
          }),
          hint: '',
        })
        return
      }
      setBusy(true)
      setErr(null)
      try {
        const created = await createClientCompany({
          name: trimmed,
          tax_id: vat.trim() || undefined,
          extra: { onboarding_source: 'wizard_step3' },
        })
        await onCreated(String(created?.id ?? ''), trimmed)
      } catch (error) {
        setErr(
          getFriendlyErrorInfo(
            error,
            t('app.onboarding.wizard.steps.client.errors.generic', {
              defaultValue: 'Could not create client',
            }),
            t,
          ),
        )
      } finally {
        setBusy(false)
      }
    },
    [name, vat, onCreated, t],
  )

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="space-y-1">
        <label htmlFor="wizard-client-name" className="text-sm font-medium text-slate-800">
          {t('app.onboarding.wizard.steps.client.name', { defaultValue: 'Client company name' })}
        </label>
        <input
          id="wizard-client-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input w-full"
          placeholder={t('app.onboarding.wizard.steps.client.name_placeholder', {
            defaultValue: 'e.g. North Logistics Sp. z o.o.',
          })}
          autoFocus
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="wizard-client-vat" className="text-sm font-medium text-slate-800">
          {t('app.onboarding.wizard.steps.client.vat', { defaultValue: 'Tax ID (optional)' })}
        </label>
        <input
          id="wizard-client-vat"
          type="text"
          value={vat}
          onChange={(e) => setVat(e.target.value)}
          className="input w-full"
          placeholder="PL1234567890"
        />
      </div>
      {err ? <ErrorRecoveryBanner info={err} compact /> : null}
      <div className="flex flex-wrap items-center gap-2">
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy
            ? t('common.saving')
            : t('app.onboarding.wizard.steps.client.submit', { defaultValue: 'Create client' })}
        </button>
        <button type="button" className="btn-secondary" onClick={onSkip} disabled={busy}>
          {t('app.onboarding.wizard.skip', { defaultValue: 'Skip for now' })}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Step 4 — First vacancy
// ---------------------------------------------------------------------------

type CompanyOption = { id: string; name: string; group: 'own' | 'client' }

function StepVacancy({
  onCreated,
  onSkip,
}: {
  onCreated: (vacancyId: string, title: string) => Promise<void>
  onSkip: () => void
}) {
  const { t } = useI18n()
  const [title, setTitle] = useState('')
  const [employmentType, setEmploymentType] = useState<'full_time' | 'part_time' | 'b2b'>('full_time')
  const [companyOptions, setCompanyOptions] = useState<CompanyOption[]>([])
  const [companyId, setCompanyId] = useState('')
  const [loadingCompanies, setLoadingCompanies] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<FriendlyErrorInfo | null>(null)

  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const [own, clients] = await Promise.all([
          listOwnCompanies().catch(() => ({ items: [] as Array<{ id: string; name?: string }> })),
          listCompanies({ limit: 50 }).catch(() => [] as Array<{ id: string; name?: string }>),
        ])
        if (!alive) return
        const ownItems: CompanyOption[] = ((own?.items as Array<{ id: string; name?: string }>) ?? []).map((c) => ({
          id: String(c.id),
          name: String(c.name ?? c.id),
          group: 'own' as const,
        }))
        const clientItemsRaw = Array.isArray(clients)
          ? (clients as Array<{ id: string; name?: string }>)
          : ((clients as { items?: Array<{ id: string; name?: string }> })?.items ?? [])
        const clientItems: CompanyOption[] = clientItemsRaw.map((c) => ({
          id: String(c.id),
          name: String(c.name ?? c.id),
          group: 'client' as const,
        }))
        const opts = [...ownItems, ...clientItems]
        setCompanyOptions(opts)
        if (opts[0]) setCompanyId(opts[0].id)
      } finally {
        if (alive) setLoadingCompanies(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  const submit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault()
      const trimmed = title.trim()
      if (!trimmed) {
        setErr({
          title: t('app.onboarding.wizard.steps.vacancy.errors.title_required', {
            defaultValue: 'Enter vacancy title',
          }),
          hint: '',
        })
        return
      }
      if (!companyId) {
        setErr({
          title: t('app.onboarding.wizard.steps.vacancy.errors.company_required', {
            defaultValue: 'Select a company for this vacancy',
          }),
          hint: '',
        })
        return
      }
      setBusy(true)
      setErr(null)
      try {
        const selected = companyOptions.find((c) => c.id === companyId)
        let vacancyCompanyId = companyId
        if (selected?.group === 'own') {
          const operating = await resolveOperatingCompanyId()
          vacancyCompanyId = operating.companyId
        }
        const created = await createVacancy({
          company_id: vacancyCompanyId,
          title: trimmed,
          employment_type: employmentType,
          extra: { onboarding_source: 'wizard_step4' },
        })
        await onCreated(String((created as { id?: string })?.id ?? ''), trimmed)
      } catch (error) {
        setErr(
          getFriendlyErrorInfo(
            error,
            t('app.onboarding.wizard.steps.vacancy.errors.generic', {
              defaultValue: 'Could not create vacancy',
            }),
            t,
          ),
        )
      } finally {
        setBusy(false)
      }
    },
    [title, companyId, companyOptions, employmentType, onCreated, t],
  )

  if (loadingCompanies) {
    return <div className="text-sm text-slate-500">{t('common.loading')}</div>
  }

  if (companyOptions.length === 0) {
    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-sm text-amber-900">
          {t('app.onboarding.wizard.steps.vacancy.no_companies', {
            defaultValue: 'You need a company before adding a vacancy. Add a client company in the previous step or open the company directory.',
          })}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link to={CRM_APP_PATHS.clientsDirectory} className="btn-primary">
            {t('app.onboarding.wizard.steps.vacancy.open_clients', {
              defaultValue: 'Open companies',
            })}
          </Link>
          <button type="button" className="btn-secondary" onClick={onSkip}>
            {t('app.onboarding.wizard.skip', { defaultValue: 'Skip for now' })}
          </button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="space-y-1">
        <label htmlFor="wizard-vac-title" className="text-sm font-medium text-slate-800">
          {t('app.onboarding.wizard.steps.vacancy.title_label', { defaultValue: 'Vacancy title' })}
        </label>
        <input
          id="wizard-vac-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="input w-full"
          placeholder={t('app.onboarding.wizard.steps.vacancy.title_placeholder', {
            defaultValue: 'e.g. CE driver — international',
          })}
          autoFocus
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="wizard-vac-company" className="text-sm font-medium text-slate-800">
            {t('app.onboarding.wizard.steps.vacancy.company', { defaultValue: 'Company' })}
          </label>
          <select
            id="wizard-vac-company"
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="input w-full"
          >
            {companyOptions.map((opt) => (
              <option key={`${opt.group}-${opt.id}`} value={opt.id}>
                {opt.group === 'own' ? '★ ' : ''}{opt.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="wizard-vac-emp" className="text-sm font-medium text-slate-800">
            {t('app.onboarding.wizard.steps.vacancy.employment_type', {
              defaultValue: 'Employment type',
            })}
          </label>
          <select
            id="wizard-vac-emp"
            value={employmentType}
            onChange={(e) =>
              setEmploymentType(e.target.value as 'full_time' | 'part_time' | 'b2b')
            }
            className="input w-full"
          >
            <option value="full_time">
              {t('app.onboarding.wizard.steps.vacancy.full_time', { defaultValue: 'Full-time' })}
            </option>
            <option value="part_time">
              {t('app.onboarding.wizard.steps.vacancy.part_time', { defaultValue: 'Part-time' })}
            </option>
            <option value="b2b">
              {t('app.onboarding.wizard.steps.vacancy.b2b', { defaultValue: 'B2B contract' })}
            </option>
          </select>
        </div>
      </div>
      {err ? <ErrorRecoveryBanner info={err} compact /> : null}
      <div className="flex flex-wrap items-center gap-2">
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy
            ? t('common.saving')
            : t('app.onboarding.wizard.steps.vacancy.submit', { defaultValue: 'Create vacancy' })}
        </button>
        <button type="button" className="btn-secondary" onClick={onSkip} disabled={busy}>
          {t('app.onboarding.wizard.skip', { defaultValue: 'Skip for now' })}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Step 5 — First lead with NBA
// ---------------------------------------------------------------------------

function StepFirstLead({ onFinish }: { onFinish: () => Promise<void> }) {
  const { t } = useI18n()
  const [snapshot, setSnapshot] = useState<OnboardingWizardFirstLead | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [seedBusy, setSeedBusy] = useState(false)
  const [seedError, setSeedError] = useState<FriendlyErrorInfo | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getOnboardingWizardFirstLead()
      setSnapshot(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const handleSeedDemo = useCallback(async () => {
    setSeedBusy(true)
    setSeedError(null)
    try {
      await seedOnboardingDemo()
      await reload()
    } catch (err) {
      setSeedError(
        getFriendlyErrorInfo(
          err,
          t('app.onboarding.wizard.steps.first_lead.seed_error', {
            defaultValue: 'Could not load demo data',
          }),
          t,
        ),
      )
    } finally {
      setSeedBusy(false)
    }
  }, [reload, t])

  if (loading) {
    return <div className="text-sm text-slate-500">{t('common.loading')}</div>
  }

  if (!snapshot || !snapshot.has_lead) {
    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-sm text-amber-900">
          <div className="flex items-center gap-2 font-semibold">
            <IconSparkles size={16} aria-hidden />
            {t('app.onboarding.wizard.steps.first_lead.no_leads_title', {
              defaultValue: 'No leads yet',
            })}
          </div>
          <p className="mt-1 text-amber-800">
            {t('app.onboarding.wizard.steps.first_lead.no_leads_hint', {
              defaultValue: 'Send a test lead through the channel you connected, or open Leads to add one manually.',
            })}
          </p>
          <p className="mt-2 text-xs text-amber-700">
            {t('app.onboarding.wizard.steps.first_lead.seed_hint', {
              defaultValue:
                'Want to learn the product first? Load a sample pack — 12 leads, candidates and tasks — and explore HostFlow. You can wipe it later in one click.',
            })}
          </p>
        </div>
        {seedError ? <ErrorRecoveryBanner info={seedError} compact /> : null}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="btn-primary"
            onClick={() => void handleSeedDemo()}
            disabled={seedBusy}
          >
            {seedBusy
              ? t('common.saving')
              : t('app.onboarding.wizard.steps.first_lead.seed_demo', {
                  defaultValue: 'Load demo data',
                })}
          </button>
          <Link to={CRM_APP_PATHS.leads} className="btn-secondary">
            {t('app.onboarding.wizard.steps.first_lead.open_leads', { defaultValue: 'Open Leads' })}
          </Link>
          <button type="button" className="btn-secondary" onClick={() => void reload()}>
            {t('app.onboarding.wizard.steps.first_lead.retry', { defaultValue: 'Refresh' })}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={async () => {
              setBusy(true)
              try {
                await onFinish()
              } finally {
                setBusy(false)
              }
            }}
            disabled={busy}
          >
            {t('app.onboarding.wizard.steps.first_lead.finish_anyway', {
              defaultValue: 'Finish setup anyway',
            })}
          </button>
        </div>
      </div>
    )
  }

  const dueIso = snapshot.nba_due_at
  const dueText = (() => {
    if (!dueIso) return null
    const dt = new Date(dueIso)
    if (Number.isNaN(dt.getTime())) return null
    return dt.toLocaleString()
  })()

  return (
    <div className="space-y-4">
      <article className="rounded-xl border border-brand-200 bg-brand-50/40 p-4 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-brand-700">
              {snapshot.is_demo
                ? t('app.onboarding.wizard.steps.first_lead.demo_label', { defaultValue: 'Demo lead' })
                : t('app.onboarding.wizard.steps.first_lead.real_label', { defaultValue: 'Your first lead' })}
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-900">{snapshot.title}</h3>
            <p className="mt-0.5 text-xs text-slate-500">
              {t('app.onboarding.wizard.steps.first_lead.source_stage', {
                defaultValue: 'Source: {source} · Stage: {stage}',
                values: {
                  source: snapshot.source ?? '—',
                  stage: snapshot.stage ?? '—',
                },
              })}
            </p>
          </div>
        </div>
        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <IconSparkles size={14} aria-hidden className="text-brand-600" />
            {t('app.onboarding.wizard.steps.first_lead.nba_label', { defaultValue: 'Next best action' })}
          </div>
          <p className="mt-1 text-sm font-medium text-slate-800">
            {snapshot.nba_title ??
              t('app.onboarding.wizard.steps.first_lead.nba_default', {
                defaultValue: 'Reach out and qualify the lead.',
              })}
          </p>
          {dueText ? (
            <p className="mt-0.5 text-xs text-slate-500">
              {t('app.onboarding.wizard.steps.first_lead.due_at', {
                defaultValue: 'Due: {when}',
                values: { when: dueText },
              })}
            </p>
          ) : null}
        </div>
      </article>
      <div className="flex flex-wrap items-center gap-2">
        {snapshot.lead_id ? (
          <Link to={`${CRM_APP_PATHS.leads}/${snapshot.lead_id}`} className="btn-primary">
            {t('app.onboarding.wizard.steps.first_lead.open_lead', { defaultValue: 'Open lead' })}
          </Link>
        ) : (
          <Link to={CRM_APP_PATHS.leads} className="btn-primary">
            {t('app.onboarding.wizard.steps.first_lead.open_leads', { defaultValue: 'Open Leads' })}
          </Link>
        )}
        <button
          type="button"
          className="btn-secondary"
          onClick={async () => {
            setBusy(true)
            try {
              await onFinish()
            } finally {
              setBusy(false)
            }
          }}
          disabled={busy}
        >
          {t('app.onboarding.wizard.steps.first_lead.finish', {
            defaultValue: 'Finish setup',
          })}
        </button>
      </div>
    </div>
  )
}
