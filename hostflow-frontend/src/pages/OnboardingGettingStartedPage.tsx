import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconArrowRight, IconCheck, IconChecklist, IconUsers, IconUserPlus } from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { getOnboardingStatus, type OnboardingStatus } from '../api/client'
import { usePermissions, type Permission } from '../hooks/usePermissions'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'
import { ACTIVATION_PATHS } from '../app/activationRoutes'

type OnboardingStepCard = {
  key: string
  done: boolean
  title: string
  desc: string
  href: string
  permission?: Permission
  openLabel?: string
}

export default function OnboardingGettingStartedPage() {
  const { t } = useI18n()
  const { entitySingular, openEntityLabel } = useBusinessTerminology()
  const navigate = useNavigate()
  const { can } = usePermissions()
  const [status, setStatus] = useState<OnboardingStatus | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await getOnboardingStatus()
        if (!cancelled) setStatus(data)
      } catch {
        if (!cancelled) setStatus(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const steps = useMemo(
    () => {
      const businessType = status?.business_type ?? 'agency'
      const typeStep: OnboardingStepCard =
        businessType === 'employer'
          ? {
              key: 'vacancy',
              done: Boolean(status?.steps?.first_vacancy_created),
              title: t('app.onboarding.getting_started.step_employer.title', { defaultValue: 'Create first vacancy' }),
              desc: t('app.onboarding.getting_started.step_employer.desc', { defaultValue: 'Open your first position and set responsible recruiter.' }),
              href: ACTIVATION_PATHS.vacancies,
              permission: 'vacancies.view',
            }
          : businessType === 'services'
            ? {
                key: 'first_client',
                done: Boolean(status?.steps?.first_client_created),
                title: t('app.onboarding.getting_started.step_services.title_dynamic', {
                  defaultValue: 'Create first {entity}',
                  values: { entity: entitySingular.toLowerCase() },
                }),
                desc: t('app.onboarding.getting_started.step_services.desc_dynamic', {
                  defaultValue: 'Add your first {entity} to start service operations.',
                  values: { entity: entitySingular.toLowerCase() },
                }),
                href: ACTIVATION_PATHS.clients,
                permission: 'companies.view',
              }
            : {
                key: 'first_client',
                done: Boolean(status?.steps?.first_client_created),
                title: t('app.onboarding.getting_started.step_agency.title_dynamic', {
                  defaultValue: 'Create first {entity}',
                  values: { entity: entitySingular.toLowerCase() },
                }),
                desc: t('app.onboarding.getting_started.step_agency.desc_dynamic', {
                  defaultValue: 'Add your first {entity} manually to start working immediately.',
                  values: { entity: entitySingular.toLowerCase() },
                }),
                href: ACTIVATION_PATHS.clients,
                permission: 'companies.view',
              }
      const nextSteps: OnboardingStepCard[] = [
        {
          key: 'company',
          done: Boolean(status?.steps?.company_created),
          title: t('app.onboarding.getting_started.step0.title', { defaultValue: 'Company created' }),
          desc: t('app.onboarding.getting_started.step0.desc', { defaultValue: 'Workspace company setup is complete.' }),
          href: ACTIVATION_PATHS.clients,
          permission: 'companies.view',
        },
        typeStep,
        {
          key: 'action',
          done: Boolean(status?.steps?.next_action_created),
          title: t('app.onboarding.getting_started.step3.title', { defaultValue: 'Set next action' }),
          desc: t('app.onboarding.getting_started.step3.desc', { defaultValue: 'Add reminder/task so no lead is lost.' }),
          href: ACTIVATION_PATHS.reminders,
          permission: 'notifications.view',
        },
      ]
      return nextSteps.map((step) => {
        const accessible = !step.permission || can(step.permission)
        return {
          ...step,
          href: accessible ? step.href : ACTIVATION_PATHS.overview,
          openLabel: accessible
            ? step.href === ACTIVATION_PATHS.clients
              ? openEntityLabel
              : t('app.onboarding.getting_started.open', { defaultValue: 'Open' })
            : t('app.onboarding.getting_started.open_fallback', { defaultValue: 'Open dashboard' }),
        }
      })
    },
    [status, t, can, entitySingular, openEntityLabel],
  )
  const doneCount = steps.filter((step) => step.done).length
  const totalCount = steps.length
  const completed = doneCount >= totalCount
  const stepVisuals = [
    {
      pendingIcon: IconUsers,
      bgClass: 'bg-blue-50 text-blue-700',
    },
    {
      pendingIcon: IconUserPlus,
      bgClass: 'bg-emerald-50 text-emerald-700',
    },
    {
      pendingIcon: IconChecklist,
      bgClass: 'bg-amber-50 text-amber-700',
    },
  ] as const

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
          <IconChecklist size={14} stroke={1.9} />
          {t('app.onboarding.getting_started.badge', { defaultValue: 'Workspace ready' })}
        </div>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">
          {t('app.onboarding.getting_started.title', { defaultValue: 'Start working in 3 steps' })}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.onboarding.getting_started.subtitle', {
            defaultValue: 'Skip advanced settings for now. Create your first records and get value immediately.',
          })}
        </p>
        <p className="mt-2 text-xs font-medium text-brand-700">
          {t('app.onboarding.getting_started.progress', {
            defaultValue: 'Progress: {done}/{total}',
            values: { done: doneCount, total: totalCount },
          })}
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {steps.map((step, idx) => {
          const visual = stepVisuals[idx] ?? stepVisuals[0]
          const PendingIcon = visual.pendingIcon
          return (
            <article
              key={step.key}
              className={`cursor-pointer rounded-xl border bg-white p-5 shadow-sm transition hover:border-brand-300 ${step.done ? 'border-emerald-200' : 'border-slate-200'}`}
              role="link"
              tabIndex={0}
              onClick={() => navigate(step.href)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  navigate(step.href)
                }
              }}
            >
              <div className={`inline-flex rounded-lg p-2 ${visual.bgClass}`}>
                {step.done ? <IconCheck size={18} stroke={2} className="text-emerald-700" /> : <PendingIcon size={18} stroke={1.9} />}
              </div>
              <h2 className="mt-3 text-base font-semibold text-slate-900">
                {step.title}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {step.desc}
              </p>
              <Link
                to={step.href}
                className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline"
                onClick={(event) => event.stopPropagation()}
              >
                {step.openLabel}
                <IconArrowRight size={14} stroke={1.9} />
              </Link>
            </article>
          )
        })}
      </section>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => navigate(ACTIVATION_PATHS.overview, { replace: true })}
          className={`inline-flex items-center gap-1 rounded-lg px-4 py-2 text-sm font-medium text-white ${completed ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-brand-600 hover:bg-brand-700'}`}
        >
          {completed
            ? t('app.onboarding.getting_started.done', { defaultValue: 'Activation completed' })
            : t('app.onboarding.getting_started.go_dashboard', { defaultValue: 'Go to dashboard' })}
          <IconArrowRight size={14} stroke={1.9} />
        </button>
      </div>
    </div>
  )
}
